"""Sanity-check the generated dataset.

    python scripts/verify_dataset.py            # structure, arithmetic, grounding
    python scripts/verify_dataset.py --ocr      # also report how readable the scans are

Checks
  1. every gold file validates against ChangeOrder
  2. gold arithmetic is consistent - except docs flagged expect_inconsistent, which MUST fail
  3. text-layer docs really have text; scans really have none
  4. grounding: every non-null gold value is printed in the document text
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from co_extract.schema import ChangeOrder  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def read_text(path: Path) -> tuple[str, int]:
    if path.suffix == ".txt":
        return norm(path.read_text(encoding="utf-8")), 1
    with pdfplumber.open(path) as pdf:
        return norm(" ".join((p.extract_text() or "") for p in pdf.pages)), len(pdf.pages)


def money_forms(x: float) -> list[str]:
    us = f"{abs(x):,.2f}"
    eu = us.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return [us, eu]


def printed(value: str, text: str) -> bool:
    """True if the value is in the text, allowing for a wrapped table cell: when a value
    wraps inside a two-column header, text extraction interleaves its neighbour's words
    between the lines. That is realistic noise, so we allow a short gap between words."""
    if value in text:
        return True
    gap = r"\W+.{0,80}?"
    return re.search(gap.join(re.escape(t) for t in value.split()), text) is not None


def grounding_misses(co: ChangeOrder, text: str) -> list[str]:
    miss = []
    for f in ("co_number", "project_name", "owner", "contractor", "reason", "status"):
        v = getattr(co, f)
        if v and not printed(v, text):
            miss.append(f"{f}={v!r}")
    if co.description and not printed(norm(co.description), text):
        miss.append("description")
    nums = {"subtotal": co.subtotal, "markup_amount": co.markup_amount, "total": co.total,
            "original_contract_sum": co.original_contract_sum, "new_contract_sum": co.new_contract_sum}
    for i, li in enumerate(co.line_items):
        nums[f"item{i}.amount"] = li.amount
        nums[f"item{i}.unit_price"] = li.unit_price
    for k, v in nums.items():
        if v is not None and not any(f in text for f in money_forms(v)):
            miss.append(f"{k}={v}")
    return miss


def ocr_hit_rate(path: Path, co: ChangeOrder) -> float:
    import pytesseract
    from pdf2image import convert_from_path
    text = norm(" ".join(pytesseract.image_to_string(im) for im in convert_from_path(str(path), dpi=200)))
    vals = [co.subtotal, co.total] + [li.amount for li in co.line_items]
    vals = [v for v in vals if v is not None]
    hits = sum(any(f in text for f in money_forms(v)) for v in vals)
    return hits / len(vals)


def main() -> int:
    run_ocr = "--ocr" in sys.argv
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    problems: list[str] = []
    kinds, tags = Counter(), Counter()
    print(f"{'id':<6} {'kind':<11} {'pages':>5} {'items':>5}  notes")

    for m in manifest:
        doc_id, path = m["id"], ROOT / "data" / m["file"]
        kinds[m["kind"]] += 1
        tags.update(m["tags"])
        notes = []

        co = ChangeOrder.model_validate_json((ROOT / "data" / "gold" / f"{doc_id}.json").read_text())

        issues = co.consistency_issues()
        if m["expect_inconsistent"]:
            if not issues:
                problems.append(f"{doc_id}: expected an inconsistency but gold is consistent")
            notes.append(f"flagged ({len(issues)} issues) as intended")
        elif issues:
            problems.append(f"{doc_id}: unexpected inconsistency: {issues}")

        text, pages = read_text(path)
        has_text = len(text) > 200
        if has_text != m["has_text_layer"]:
            problems.append(f"{doc_id}: text layer expected={m['has_text_layer']} found={has_text}")

        if m["has_text_layer"]:
            miss = grounding_misses(co, text)
            if miss:
                problems.append(f"{doc_id}: gold values not found in document text: {miss}")
        elif run_ocr:
            notes.append(f"OCR finds {ocr_hit_rate(path, co):.0%} of key amounts")

        print(f"{doc_id:<6} {m['kind']:<11} {pages:>5} {len(co.line_items):>5}  {'; '.join(notes)}")

    print("\nformats:", dict(kinds))
    print("tags:   ", dict(tags))
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for p in problems:
            print("  -", p)
        return 1
    print("\nOK - gold validates, arithmetic holds, and every gold value is grounded in its document.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
