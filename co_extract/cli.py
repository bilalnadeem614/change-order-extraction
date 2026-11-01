"""Command line entry point.

    python -m co_extract.cli data/raw/co_01_clean_form.pdf --provider anthropic
    python -m co_extract.cli data/raw/co_10_email.txt --provider openai --model <model>
    python -m co_extract.cli data/raw/co_01_clean_form.pdf --provider mock --gold data/gold/co_01.json

Prints the validated JSON: every field has a value, a confidence in [0, 1], the evidence
quote it came from, and flags explaining any penalty. `needs_review` is true when any field
falls below --threshold or a validation check failed.
"""
from __future__ import annotations

import argparse
import sys

from pydantic import ValidationError

from .ingest import ingest
from .llm import AnthropicClient, GroqClient, LLMError, MockClient, OpenAICompatClient
from .pipeline import REVIEW_THRESHOLD, run_pipeline


def make_client(args):
    if args.provider == "anthropic":
        return AnthropicClient(model=args.model)
    if args.provider == "groq":
        return GroqClient(model=args.model)
    if args.provider == "openai":
        return OpenAICompatClient(model=args.model)
    if args.provider == "mock":
        if not args.gold:
            raise LLMError("--provider mock needs --gold <gold.json> (plumbing tests only)")
        return MockClient(args.gold)
    raise LLMError(f"unknown provider {args.provider}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Extract a change order to validated JSON with per-field confidence")
    ap.add_argument("path")
    ap.add_argument("--provider", choices=["groq", "anthropic", "openai", "mock"], default="groq")
    ap.add_argument("--model")
    ap.add_argument("--gold", help="gold file, mock provider only")
    ap.add_argument("--passes", type=int, default=2, choices=[1, 2], help="2 = second pass for agreement (2x cost)")
    ap.add_argument("--threshold", type=float, default=REVIEW_THRESHOLD)
    ap.add_argument("--out", help="write JSON here instead of stdout")
    ap.add_argument("--show-text", action="store_true", help="print the ingested text and exit")
    args = ap.parse_args(argv)

    if args.show_text:
        print(ingest(args.path).text)
        return 0
    try:
        result = run_pipeline(args.path, make_client(args), passes=args.passes, threshold=args.threshold)
    except (LLMError, ValidationError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    out = result.model_dump_json(indent=2)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(out)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
