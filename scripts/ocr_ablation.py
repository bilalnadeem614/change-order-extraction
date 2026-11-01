"""Which OCR preprocessing settings recover the most numbers from the scans?

    python scripts/ocr_ablation.py

Metric: share of gold money values (line amounts, unit prices, subtotal, total, contract
sums) that appear verbatim in the OCR text. Strict but easy to read. This tunes ingest on
the dev set, so say so in the write-up: it is a small, self-made set.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from co_extract.ingest import OCRConfig, ingest  # noqa: E402
from co_extract.schema import ChangeOrder  # noqa: E402
from verify_dataset import money_forms, norm  # noqa: E402

VARIANTS = {
    "baseline (no deskew, psm 3)": OCRConfig(dpi=300, deskew=False, binarize=False, psm=3),
    "psm 6":                       OCRConfig(dpi=300, deskew=False, binarize=False, psm=6),
    "psm 6 + deskew":              OCRConfig(dpi=300, deskew=True, binarize=False, psm=6),
    "psm 6 + deskew + binarize":   OCRConfig(dpi=300, deskew=True, binarize=True, psm=6),
    "psm 4 + deskew":              OCRConfig(dpi=300, deskew=True, binarize=False, psm=4),
    "psm 6 + deskew @400dpi":      OCRConfig(dpi=400, deskew=True, binarize=False, psm=6),
}


def money_values(co: ChangeOrder):
    v = [co.subtotal, co.markup_amount, co.total, co.original_contract_sum, co.new_contract_sum]
    for li in co.line_items:
        v += [li.amount, li.unit_price]
    return [x for x in v if x is not None]


def main() -> None:
    manifest = [m for m in json.loads((ROOT / "data" / "manifest.json").read_text()) if not m["has_text_layer"]]
    print(f"{'variant':<30}" + "".join(f"{m['id']:>8}" for m in manifest) + f"{'mean':>8}")
    for name, cfg in VARIANTS.items():
        rates = []
        for m in manifest:
            co = ChangeOrder.model_validate_json((ROOT / "data" / "gold" / f"{m['id']}.json").read_text())
            text = norm(ingest(ROOT / "data" / m["file"], cfg).text)
            vals = money_values(co)
            rates.append(sum(any(f in text for f in money_forms(x)) for x in vals) / len(vals))
        print(f"{name:<30}" + "".join(f"{r:>8.0%}" for r in rates) + f"{sum(rates) / len(rates):>8.0%}")


if __name__ == "__main__":
    main()
