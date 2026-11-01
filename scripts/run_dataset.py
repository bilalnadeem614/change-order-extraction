"""Run the pipeline over the dataset and save one JSON per document.

    python scripts/run_dataset.py --provider anthropic --run claude_sonnet
    python scripts/run_dataset.py --provider openai --model <model> --run my_model
    python scripts/run_dataset.py --provider sim --run sim_demo        # tooling demo, NOT accuracy

Outputs go to outputs/<run>/<doc_id>.json; then run scripts/evaluate.py --run <run>.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from co_extract.llm import AnthropicClient, GroqClient, OpenAICompatClient  # noqa: E402
from co_extract.pipeline import run_pipeline  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["groq", "anthropic", "openai", "sim"], required=True)
    ap.add_argument("--model")
    ap.add_argument("--run", required=True, help="name of the output folder under outputs/")
    ap.add_argument("--passes", type=int, default=2, choices=[1, 2])
    ap.add_argument("--force", action="store_true", help="re-process documents that already have output")
    ap.add_argument("--ids", nargs="*", help="only these document ids, e.g. co_01 co_14")
    args = ap.parse_args()

    out_dir = ROOT / "outputs" / args.run
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    done = failed = 0
    t0 = time.time()
    for m in manifest:
        if args.ids and m["id"] not in args.ids:
            continue
        out_file = out_dir / f"{m['id']}.json"
        if out_file.exists() and not args.force:
            print(f"{m['id']}  skipped (already done)")
            continue
        if args.provider == "groq":
            client = GroqClient(model=args.model)
        elif args.provider == "anthropic":
            client = AnthropicClient(model=args.model)
        elif args.provider == "openai":
            client = OpenAICompatClient(model=args.model)
        else:
            from sim_client import SimClient
            client = SimClient(ROOT / "data" / "gold" / f"{m['id']}.json", scan=not m["has_text_layer"])
        try:
            client.debug_dir = out_dir / "raw" / f"{m['id']}_failed"
            res = run_pipeline(ROOT / "data" / m["file"], client, passes=args.passes,
                               raw_path=out_dir / "raw" / f"{m['id']}.json")
            out_file.write_text(res.model_dump_json(indent=2))
            (out_dir / f"{m['id']}.error.txt").unlink(missing_ok=True)
            done += 1
            print(f"{m['id']}  ok   review={res.needs_review}")
        except Exception as e:  # keep going: one bad document should not stop the run
            failed += 1
            (out_dir / f"{m['id']}.error.txt").write_text(f"{type(e).__name__}: {e}")
            print(f"{m['id']}  FAILED {type(e).__name__}: {str(e)[:100]}")
    (out_dir / "run_info.json").write_text(json.dumps(
        {"provider": args.provider, "model": args.model, "passes": args.passes, "ok": done,
         "failed": failed, "seconds": round(time.time() - t0, 1),
         "simulated": args.provider == "sim"}, indent=2))
    print(f"\n{done} ok, {failed} failed -> {out_dir}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
