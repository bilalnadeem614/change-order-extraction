"""Evidence grounding: is the model's quote really in the document, and is the extracted
value really in that quote?

A model can fail in two different ways that look identical in the JSON:
  * it invents or mangles the quote            -> evidence_status == "absent"
  * it quotes correctly but reports a wrong value -> value_in_evidence() is False
Both are caught here, with no second model call.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any, List, Optional, Set, Tuple

from .ingest import IngestResult

GAP = 80  # chars of interleaved text tolerated between words of a wrapped quote


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


# --------------------------------------------------------------------------- #
# Is the quote in the text?
# --------------------------------------------------------------------------- #
def _ordered_tokens_present(tokens: List[str], text: str, gap: int = GAP) -> bool:
    """All tokens occur in order with at most `gap` characters between neighbours.

    Handles a quote that wraps inside a table cell: text extraction then interleaves the
    neighbouring cell's words between its lines.
    """
    for m in re.finditer(re.escape(tokens[0]), text):
        pos, ok = m.end(), True
        for tok in tokens[1:]:
            i = text.find(tok, pos, pos + gap + len(tok))
            if i < 0:
                ok = False
                break
            pos = i + len(tok)
        if ok:
            return True
    return False


def evidence_status(evidence: Optional[str], text: str) -> str:
    """"exact" | "fuzzy" (wrapped / interleaved) | "missing" (no quote) | "absent" (quote not in text)."""
    if not evidence or not evidence.strip():
        return "missing"
    ne, nt = norm(evidence), norm(text)
    if ne in nt:
        return "exact"
    toks = ne.split()
    if toks and _ordered_tokens_present(toks, nt):
        return "fuzzy"
    return "absent"


# --------------------------------------------------------------------------- #
# Is the value in the quote?
# --------------------------------------------------------------------------- #
def number_forms(x: float) -> Set[str]:
    a = abs(float(x))
    us = f"{a:,.2f}"
    eu = us.replace(",", "\0").replace(".", ",").replace("\0", ".")
    plain = f"{a:.2f}"
    forms = {us, eu, plain, plain.replace(".", ",")}
    if a == int(a):
        n = int(a)
        forms |= {f"{n:,}", str(n), f"{n:,}".replace(",", ".")}
    else:
        forms |= {f"{a:g}"}
    return forms


def _has_number(evidence: str, x: float) -> bool:
    return any(re.search(rf"(?<![\d.,]){re.escape(f)}(?!\d)", evidence) for f in number_forms(x))


_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}


def _month(name: str) -> Optional[int]:
    n = name.lower().rstrip(".")
    if n in _MONTHS:
        return _MONTHS[n]
    for full, i in _MONTHS.items():
        if full.startswith(n) and len(n) >= 3:
            return i
    return None


def date_candidates(evidence: str) -> Tuple[Set[dt.date], bool]:
    """All dates the evidence could mean, and whether a numeric date is day/month ambiguous."""
    out: Set[dt.date] = set()
    ambiguous = False

    def add(y: int, m: int, d: int):
        try:
            out.add(dt.date(y, m, d))
        except ValueError:
            pass

    for y, m, d in re.findall(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", evidence):
        add(int(y), int(m), int(d))
    for mon, d, y in re.findall(r"\b([A-Za-z]{3,9})\.? (\d{1,2}),? (\d{4})\b", evidence):
        if _month(mon):
            add(int(y), _month(mon), int(d))
    for d, mon, y in re.findall(r"\b(\d{1,2})[ -]([A-Za-z]{3,9})\.?[ -](\d{4})\b", evidence):
        if _month(mon):
            add(int(y), _month(mon), int(d))
    for a, b, y in re.findall(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", evidence):
        a, b, y = int(a), int(b), int(y)
        add(y, a, b)          # month first
        add(y, b, a)          # day first
        if a <= 12 and b <= 12 and a != b:
            ambiguous = True
    return out, ambiguous


def is_ambiguous_date(evidence: Optional[str]) -> bool:
    return bool(evidence) and date_candidates(evidence)[1]


_CURRENCY = {"USD": ("$", "usd", "us$"), "EUR": ("€", "eur"), "GBP": ("£", "gbp")}


def value_in_evidence(field: str, value: Any, evidence: str) -> bool:
    """Does the evidence quote actually contain the reported value?"""
    if value is None or not evidence:
        return False
    ne = norm(evidence)
    if field == "co_date":
        return dt.date.fromisoformat(str(value)) in date_candidates(evidence)[0]
    if field == "currency":
        return any(sym in ne for sym in _CURRENCY.get(str(value).upper(), (str(value).lower(),)))
    if field == "schedule_impact_days":
        if int(value) == 0 and re.search(r"no change|\b0\b", ne):
            return True
        return re.search(rf"(?<![\d.,]){abs(int(value))}(?!\d)", ne) is not None
    if field == "signed":
        return ("/s/" in ne) if value else ("_" in ne or "signature" in ne or "unsigned" in ne)
    if field == "markup_percent":
        return re.search(rf"(?<![\d.,]){re.escape(f'{float(value):g}')}\s*%", ne) is not None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _has_number(evidence, value)
    v = norm(str(value))
    return v in ne or (bool(v.split()) and _ordered_tokens_present(v.split(), ne))


def drops_sentence(field: str, value: Any, evidence: Optional[str]) -> bool:
    """True if a prose value is a strict slice of its own evidence that leaves a sentence out.

    The value is "in the evidence", so grounding passes, but the model kept only part of it:
    evidence "Scope: The parties agreed to ... changes. Work covers X." with value "X" drops the
    first sentence. A label prefix ("Scope:", "Description of Change") has no sentence end, so it
    is fine; anything after the value other than closing punctuation is also dropped text.
    """
    if field != "description" or not isinstance(value, str) or not evidence:
        return False
    nv, ne = norm(value).rstrip(". "), norm(evidence)
    i = ne.find(nv)
    if i < 0 or not nv:
        return False
    before, after = ne[:i], ne[i + len(nv):]
    return ". " in before or bool(re.search(r"\w", after))


def may_continue_on_next_line(value: Any, evidence: Optional[str], text: str, orphans: List[str]) -> bool:
    """True if the line carrying a text value is directly followed by a stray fragment that
    ingest could not attach to any cell (see ingest.reflow).

    Catches the one grounding failure that cannot be seen from the quote alone: a form cell
    that wrapped ("Maple Ridge Elementary Gym" / "Addition"), where the model quotes the first
    line correctly and returns a prefix of the real value. Ingest repairs these when it can
    (position + font weight); this flags the rest. It cannot say WHICH cell the fragment
    belongs to, so any text value on that line is distrusted. Needs a text layer: for OCR'd
    scans there is no font or position information, so nothing is flagged.
    """
    if not isinstance(value, str) or not evidence or not orphans:
        return False
    nv, ne = norm(value), norm(evidence)
    orph = {norm(o) for o in orphans}
    lines = [norm(l) for l in text.splitlines()]
    for i, line in enumerate(lines):
        if ne in line and nv in line:
            nxt = next((l for l in lines[i + 1:i + 2] if l), "")
            if nxt in orph:
                return True
    return False


def value_in_text(value: Any, text: str) -> bool:
    """Is a text value anywhere in the document (allowing wrapped / interleaved lines)?"""
    nv, nt = norm(str(value)), norm(text)
    return nv in nt or (bool(nv.split()) and _ordered_tokens_present(nv.split(), nt))


# --------------------------------------------------------------------------- #
# OCR word confidence for an evidence span
# --------------------------------------------------------------------------- #
def ocr_conf_for_evidence(evidence: Optional[str], ingest: IngestResult) -> Optional[float]:
    """Tesseract confidence (0-100) of the words in the quote; None if the text did not come from OCR.

    Digit-bearing words dominate: a misread digit changes the value, a misread label does not.
    """
    pages = [p for p in ingest.pages if p.method == "ocr" and p.words]
    if not pages:
        return None
    if not evidence:
        return float(sum(p.mean_conf or 0 for p in pages) / len(pages))
    toks = set(evidence.split())
    matched = [(w, c) for p in pages for w, c in p.words if w in toks]
    digits = [c for w, c in matched if any(ch.isdigit() for ch in w)]
    if digits:
        return float(min(digits))
    if matched:
        return float(sum(c for _, c in matched) / len(matched))
    return float(sum(p.mean_conf or 0 for p in pages) / len(pages))


# --------------------------------------------------------------------------- #
# "The field is null - but does the text suggest it should not be?"
# --------------------------------------------------------------------------- #
ABSENCE_HINTS = {
    "co_date": r"\b(date|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b",
    "subtotal": r"\bsubtotal\b",
    "markup_amount": r"markup|overhead|profit",
    "markup_percent": r"markup|overhead|profit",
    "total": r"\btotal\b|net change",
    "currency": r"[$€£]|\busd\b|\beur\b",
    "schedule_impact_days": r"calendar days|contract time|schedule impact",
    "original_contract_sum": r"contract sum|original contract",
    "new_contract_sum": r"contract sum|revised contract|new contract",
    "status": r"\bstatus\b",
    "signed": r"signature|/s/",
    "owner": r"\bowner\b",
    "contractor": r"\bcontractor\b",
    "project_name": r"\bproject\b",
    "co_number": r"change order|\bco\b|\bpco\b",
    "reason": r"\breason\b",
    "description": r"description|scope",
}


def absence_hint(field: str, text: str) -> bool:
    pat = ABSENCE_HINTS.get(field)
    return bool(pat and re.search(pat, text, flags=re.IGNORECASE))
