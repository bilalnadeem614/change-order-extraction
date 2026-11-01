"""Stage 4 - per-field confidence.

Confidence is NOT the model's self-assessment (poorly calibrated). It is a product of
independent, checkable signals:

  1. grounding        the evidence quote is in the document, and the value is in the quote
  2. validation       the field takes part in an arithmetic / plausibility check that failed
  3. agreement        a second, differently-conditioned pass reports the same value
  4. OCR quality      Tesseract's confidence on the words the value was read from
  5. absence hints    a field reported as null although the text mentions it

The factors below are hand-set priors, chosen so that each signal can pull a field below
the review threshold on its own. They are NOT fitted: scripts/evaluate.py prints a
reliability table (stated confidence vs observed accuracy) to check them against gold, and
the write-up should report how far off they are.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .grounding import (absence_hint, drops_sentence, evidence_status, may_continue_on_next_line, norm, ocr_conf_for_evidence,
                        value_in_evidence, value_in_text)
from .ingest import IngestResult
from .result import ScoredField, ScoredLineItem
from .schema import SCALAR_FIELDS, ChangeOrderExtraction
from .validate import Issue

PRIORS = dict(
    grounding={"exact": 1.0, "fuzzy": 0.9, "missing": 0.5, "absent": 0.15},
    value_not_in_evidence=0.3,
    value_spans_lines=0.9,     # text value is in the document but not all inside the quoted line
    value_drops_sentence=0.5,  # prose value is a slice of its quote that leaves a sentence out
    may_be_truncated=0.5,      # value ends its line and the next line looks like its continuation
    null_base=0.85,            # absence is harder to confirm than presence
    missed_field_hint=0.5,
    disagree=0.45,
    issue={"error": 0.55, "warn": 0.85},
    # an ambiguous numeric date (04/03/2026) is a coin flip the document cannot resolve:
    # it must land below the review threshold, not just "slightly doubtful".
    # A missing total / co_number must never pass, whatever the null prior says.
    issue_code={"ambiguous_date": 0.55, "required_missing": 0.6},
    count_disagree=0.7,
    ocr=(0.2, 0.8),            # factor = a + b * conf/100
)

# which line-item sub-fields an issue implicates
ISSUE_SUBFIELDS = {
    "qty_price_mismatch": ("quantity", "unit_price", "amount"),
    "items_sum_mismatch": ("amount",),
    "sign_vs_description": ("amount",),
}
ITEM_SUBFIELDS = ("description", "quantity", "unit", "unit_price", "amount")


@dataclass
class PassResult:
    extraction: ChangeOrderExtraction
    text: str                     # the exact text this pass was shown (evidence is checked against it)


def same(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 0.005
    if isinstance(a, dt.date) and isinstance(b, dt.date):
        return a == b
    return norm(str(a)) == norm(str(b))


def _ocr_factor(conf: Optional[float]) -> float:
    a, b = PRIORS["ocr"]
    return 1.0 if conf is None else a + b * max(0.0, min(conf, 100.0)) / 100.0


def _clip(x: float) -> float:
    return round(max(0.0, min(1.0, x)), 3)


def _jsonable(v: Any) -> Any:
    return v.isoformat() if isinstance(v, dt.date) else v


def _agreement_factor(n_disagree: int, n_others: int) -> float:
    if n_others == 0 or n_disagree == 0:
        return 1.0
    return 1.0 - (1.0 - PRIORS["disagree"]) * n_disagree / n_others


# --------------------------------------------------------------------------- #
def _score_value(field: str, value: Any, evidence: Optional[str], text: str, ingest: IngestResult,
                 n_disagree: int, n_others: int, issue_flags: List[Tuple[str, str]],
                 line_item: bool = False) -> ScoredField:
    flags: List[str] = []
    f = 1.0

    if value is None:
        f = PRIORS["null_base"]
        if absence_hint(field, text):
            f *= PRIORS["missed_field_hint"]
            flags.append("possible_missed_field")
        if ingest.used_ocr:
            # OCR garbles the label words absence_hint looks for, so a null on a scan is unverifiable
            f *= _ocr_factor(ingest.mean_ocr_conf)
            flags.append("null_on_ocr_text")
    else:
        st = evidence_status(evidence, text)
        f *= PRIORS["grounding"][st]
        if st != "exact":
            flags.append(f"evidence_{st}")
        if st in ("exact", "fuzzy") and not value_in_evidence(field, value, evidence):
            if isinstance(value, str) and value_in_text(value, text):
                f *= PRIORS["value_spans_lines"]     # wrapped over two lines: benign
                flags.append("value_spans_lines")
            else:
                f *= PRIORS["value_not_in_evidence"]
                flags.append("value_not_in_evidence")
        if not line_item and drops_sentence(field, value, evidence):    # an item's quote is its whole row
            f *= PRIORS["value_drops_sentence"]
            flags.append("value_drops_sentence")
        if may_continue_on_next_line(value, evidence, text, ingest.orphans):
            f *= PRIORS["may_be_truncated"]
            flags.append("may_be_truncated")
        ocr = ocr_conf_for_evidence(evidence, ingest)
        if ocr is not None:
            f *= _ocr_factor(ocr)
            if ocr < 60:
                flags.append("low_ocr_confidence")

    if n_disagree:
        f *= _agreement_factor(n_disagree, n_others)
        flags.append("passes_disagree")

    for code, sev in issue_flags:
        f *= PRIORS["issue_code"].get(code, PRIORS["issue"][sev])
        flags.append(code)

    return ScoredField(value=_jsonable(value), confidence=_clip(f),
                       evidence=evidence if value is not None else None, flags=flags)


def score_scalars(passes: List[PassResult], ingest: IngestResult, issues: List[Issue]) -> Dict[str, ScoredField]:
    out: Dict[str, ScoredField] = {}
    for fld in SCALAR_FIELDS:
        vals = [getattr(p.extraction, fld).value for p in passes]
        agree = [sum(same(v, w) for w in vals) for v in vals]
        k = agree.index(max(agree))                       # majority value; ties go to pass 0
        n_dis = sum(not same(vals[k], w) for i, w in enumerate(vals) if i != k)
        flags = [(i.code, i.severity) for i in issues if fld in i.fields]
        ex = getattr(passes[k].extraction, fld)
        out[fld] = _score_value(fld, vals[k], ex.evidence, passes[k].text, ingest, n_dis, len(vals) - 1, flags)
    return out


# --------------------------------------------------------------------------- #
def _align(i: int, item, base_n: int, other: PassResult):
    """Find this pass-0 item in another pass: by index if the counts match, else by content."""
    items = other.extraction.line_items
    if len(items) == base_n:
        return items[i]
    for cand in items:
        if same(cand.amount, item.amount) and norm(cand.description) == norm(item.description):
            return cand
    return None


def score_line_items(passes: List[PassResult], ingest: IngestResult, issues: List[Issue]) -> List[ScoredLineItem]:
    base = passes[0]
    items = base.extraction.line_items
    others = passes[1:]
    result: List[ScoredLineItem] = []

    for i, li in enumerate(items):
        aligned = [_align(i, li, len(items), o) for o in others]
        subs: Dict[str, ScoredField] = {}
        for sub in ITEM_SUBFIELDS:
            value = getattr(li, sub)
            n_dis = sum(1 for a in aligned if a is None or not same(value, getattr(a, sub)))
            flags: List[Tuple[str, str]] = []
            for iss in issues:
                if f"line_items[{i}]" in iss.fields and sub in ISSUE_SUBFIELDS.get(iss.code, ("amount",)):
                    flags.append((iss.code, iss.severity))
                elif iss.code == "items_sum_mismatch" and sub == "amount":
                    flags.append((iss.code, iss.severity))
            # the same issue can be listed once per item and once for the sum - count each code once
            flags = list(dict.fromkeys(flags))
            subs[sub] = _score_value(sub, value, li.evidence, base.text, ingest, n_dis, len(others), flags, line_item=True)
        if any(a is None for a in aligned):
            for s in subs.values():
                s.flags.append("item_missing_in_other_pass")
        conf = min(s.confidence for s in subs.values())
        result.append(ScoredLineItem(**subs, evidence=li.evidence, confidence=conf))
    return result
