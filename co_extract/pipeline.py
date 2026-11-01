"""Glue: ingest -> extract (x2) -> validate -> score -> PipelineResult."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError

from .confidence import PassResult, score_line_items, score_scalars
from .extract import extract, to_change_order
from .ingest import IngestResult, OCRConfig, ingest
from .llm import LLMClient, LLMError
from .normalize import normalize_extraction
from .result import IssueOut, PipelineResult
from .validate import validate

REVIEW_THRESHOLD = 0.70
SECOND_PASS_TEMPERATURE = 0.7
ALT_OCR = OCRConfig(dpi=300, deskew=True, psm=6)   # independent OCR errors for the 2nd pass


def run_pipeline(path: str | Path, client: LLMClient, passes: int = 2,
                 threshold: float = REVIEW_THRESHOLD, raw_path: Optional[Path] = None) -> PipelineResult:
    """Pass 1 is the answer. Pass 2 exists to expose disagreement:

    * scans: it reads a differently-preprocessed OCR of the same page, so OCR digit errors
      differ between the passes and show up as disagreement;
    * text documents: same text, sampled at temperature > 0 (catches unstable answers).

    If `raw_path` is given, each pass's raw (un-normalised) extraction and the text it was shown
    are saved there, so scoring can be redone offline (scripts/rescore.py) without calling the LLM.
    """
    notes: List[str] = []
    doc = ingest(path)
    text0 = doc.text
    raw = [(text0, extract(text0, client, temperature=0.0))]

    if passes > 1:
        alt_text = ingest(path, ALT_OCR).text if doc.used_ocr else text0
        for _ in range(passes - 1):
            try:
                raw.append((alt_text, extract(alt_text, client, temperature=SECOND_PASS_TEMPERATURE)))
            except (LLMError, ValidationError) as e:
                notes.append(f"second pass failed ({type(e).__name__}); scored on a single pass")

    if raw_path is not None:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps({"model": client.name, "notes": notes,
                                        "passes": [{"text": t, "extraction": ex.model_dump(mode="json")} for t, ex in raw]}))
    return score_passes(path, doc, raw, client.name, notes, threshold)


def score_passes(path: str | Path, doc: IngestResult, raw: List[tuple], model: str, notes: List[str],
                 threshold: float = REVIEW_THRESHOLD) -> PipelineResult:
    """Everything after the LLM calls. `raw` = [(text shown, raw extraction), ...]; pass 0 is the answer."""
    runs = [PassResult(normalize_extraction(ex), t) for t, ex in raw]    # every pass normalised identically
    ex0 = runs[0].extraction
    co = to_change_order(ex0)
    issues = validate(co, ex0)
    fields = score_scalars(runs, doc, issues)
    items = score_line_items(runs, doc, issues)

    reasons = [f"{n} ({f.confidence}): {', '.join(f.flags) or 'low confidence'}"
               for n, f in fields.items() if f.confidence < threshold]
    for i, li in enumerate(items):
        if li.confidence < threshold:
            weak = [n for n in ("description", "quantity", "unit", "unit_price", "amount")
                    if getattr(li, n).confidence < threshold]
            reasons.append(f"line_items[{i}] ({li.confidence}): {', '.join(weak)}")
    for iss in issues:
        if iss.severity == "error":
            reasons.append(f"validation: {iss.message}")

    return PipelineResult(
        source=str(path), model=model, passes=len(runs), fields=fields, line_items=items,
        issues=[IssueOut(code=i.code, severity=i.severity, fields=list(i.fields), message=i.message) for i in issues],
        needs_review=bool(reasons), review_reasons=reasons,
        ingest={"used_ocr": doc.used_ocr, "mean_ocr_conf": doc.mean_ocr_conf, "warnings": doc.warnings},
        notes=notes,
    )
