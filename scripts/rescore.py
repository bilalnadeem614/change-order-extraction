"""Rebuild outputs/<run>/*.json from the cached raw passes in outputs/<run>/raw/ - no LLM calls.

    python scripts/rescore.py --run groq_v3 [--out groq_v3_rescored]

Use it to evaluate changes to normalisation, grounding, validation or confidence offline.
Writes next to the original unless --out is given (so the original run stays comparable).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from co_extract.ingest import ingest  # noqa: E402
from co_extract.pipeline import score_passes  # noqa: E402
from co_extract.schema import ChangeOrderExtraction  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", help="output run name (default: overwrite --run)")
    args = ap.parse_args()
    src = ROOT / "outputs" / args.run
    out_dir = ROOT / "outputs" / (args.out or args.run)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {m["id"]: m for m in json.loads((ROOT / "data" / "manifest.json").read_text())}
    n = 0
    for f in sorted((src / "raw").glob("co_*.json")):
        m = manifest[f.stem]
        cache = json.loads(f.read_text())
        raw = [(p["text"], ChangeOrderExtraction.model_validate(p["extraction"])) for p in cache["passes"]]
        path = ROOT / "data" / m["file"]
        res = score_passes(path, ingest(path), raw, cache["model"], cache["notes"])
        (out_dir / f"{f.stem}.json").write_text(res.model_dump_json(indent=2))
        n += 1
    info = src / "run_info.json"
    if info.exists() and out_dir != src:
        (out_dir / "run_info.json").write_text(info.read_text())
    print(f"rescored {n} documents -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
