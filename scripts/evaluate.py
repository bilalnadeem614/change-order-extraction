"""Score a run against the gold files.

    python scripts/evaluate.py --run claude_sonnet [--threshold 0.7]

Reports
  * field accuracy (overall, per field, per difficulty tag, text vs OCR)
  * calibration: does a stated confidence of 0.9 mean ~90% of those fields are right?
  * review behaviour: how many WRONG fields still scored >= threshold ("silent errors"),
    and how many correct ones were flagged for nothing
  * document level: of documents containing >= 1 error, how many were flagged for review

Correctness rules: money within 1 cent; text compared after case/whitespace normalisation
(description: >= 95% token overlap); a null must match a null.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from co_extract.schema import SCALAR_FIELDS  # noqa: E402

ITEM_SUBS = ("description", "quantity", "unit", "unit_price", "amount")
BUCKETS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 1.0001)]


def norm(s) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().casefold()


def eq(field: str, p, g) -> bool:
    if p is None or g is None:
        return p is None and g is None
    if isinstance(g, bool) or isinstance(p, bool):
        return p == g
    if isinstance(g, (int, float)) and isinstance(p, (int, float)):
        return abs(p - g) <= 0.011
    if field == "description":
        a, b = set(norm(p).split()), set(norm(g).split())
        return norm(p) == norm(g) or (bool(a | b) and len(a & b) / len(a | b) >= 0.95)
    return norm(p) == norm(g)


def align_items(pred, gold):
    """Pair predicted and gold line items. Returns (pairs, missed_gold, extra_pred)."""
    if len(pred) == len(gold):
        return list(zip(pred, gold)), [], []
    used, pairs, missed = set(), [], []
    for g in gold:
        hit = next((i for i, p in enumerate(pred) if i not in used
                    and isinstance(p["amount"]["value"], (int, float))
                    and abs(p["amount"]["value"] - g["amount"]) <= 0.011), None)
        if hit is None:
            missed.append(g)
        else:
            used.add(hit)
            pairs.append((pred[hit], g))
    return pairs, missed, [p for i, p in enumerate(pred) if i not in used]


def pct(a, b) -> str:
    return f"{a / b:.0%}" if b else "n/a"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--threshold", type=float, default=0.70)
    args = ap.parse_args()
    run_dir = ROOT / "outputs" / args.run
    info = json.loads((run_dir / "run_info.json").read_text()) if (run_dir / "run_info.json").exists() else {}
    manifest = {m["id"]: m for m in json.loads((ROOT / "data" / "manifest.json").read_text())}

    rows, docs, failed = [], {}, []
    missed_items = extra_items = 0
    for doc_id, m in manifest.items():
        f = run_dir / f"{doc_id}.json"
        if not f.exists():
            failed.append(doc_id)
            continue
        pred = json.loads(f.read_text())
        gold = json.loads((ROOT / "data" / "gold" / f"{doc_id}.json").read_text())
        tags = m["tags"] + ["ocr_doc" if not m["has_text_layer"] else "text_doc"]
        drows = []
        for fld in SCALAR_FIELDS:
            sf = pred["fields"][fld]
            drows.append(dict(doc=doc_id, field=fld, ok=eq(fld, sf["value"], gold[fld]), conf=sf["confidence"], tags=tags,
                              pred=sf["value"], gold=gold[fld], flags=sf["flags"]))
        pairs, missed, extra = align_items(pred["line_items"], gold["line_items"])
        missed_items += len(missed)
        extra_items += len(extra)
        for p, g in pairs:
            for sub in ITEM_SUBS:
                drows.append(dict(doc=doc_id, field=f"item.{sub}", ok=eq(sub, p[sub]["value"], g[sub]),
                                  conf=p[sub]["confidence"], tags=tags,
                                  pred=p[sub]["value"], gold=g[sub], flags=p[sub]["flags"]))
        has_error = any(not r["ok"] for r in drows) or bool(missed) or bool(extra)
        docs[doc_id] = dict(has_error=has_error, review=pred["needs_review"], n_missed=len(missed),
                            n_extra=len(extra), tags=tags)
        rows += drows

    thr = args.threshold
    L = []
    if info.get("simulated"):
        L += ["> **SIMULATED RUN - tooling demo.** Errors were injected by a script, so none of these",
              "> numbers measure real extraction accuracy. They only show the pipeline reacts to errors.", ""]
    L += [f"# Evaluation: `{args.run}`", "",
          f"model: {info.get('model') or info.get('provider')} | passes: {info.get('passes')} | "
          f"documents scored: {len(docs)}/{len(manifest)} | failed: {failed or 'none'} | review threshold: {thr}", ""]

    n = len(rows)
    L += ["## Accuracy", "", f"- all scored cells: **{pct(sum(r['ok'] for r in rows), n)}** ({n} cells)",
          f"- scalar fields only: {pct(sum(r['ok'] for r in rows if not r['field'].startswith('item.')), sum(1 for r in rows if not r['field'].startswith('item.')))}",
          f"- line-item cells: {pct(sum(r['ok'] for r in rows if r['field'].startswith('item.')), sum(1 for r in rows if r['field'].startswith('item.')))}",
          f"- line items missed: {missed_items}, extra (invented): {extra_items}",
          f"- documents with every field and item correct: **{pct(sum(not d['has_error'] for d in docs.values()), len(docs))}**", ""]

    by_field = defaultdict(list)
    for r in rows:
        by_field[r["field"]].append(r)
    L += ["| field | accuracy | mean confidence |", "|---|---|---|"]
    for fld, rs in sorted(by_field.items(), key=lambda kv: sum(x["ok"] for x in kv[1]) / len(kv[1])):
        L.append(f"| {fld} | {pct(sum(x['ok'] for x in rs), len(rs))} | {sum(x['conf'] for x in rs) / len(rs):.2f} |")

    by_tag = defaultdict(list)
    for r in rows:
        for t in r["tags"]:
            by_tag[t].append(r)
    L += ["", "## By difficulty tag", "", "| tag | cells | accuracy | docs flagged / docs with errors |", "|---|---|---|---|"]
    for t, rs in sorted(by_tag.items()):
        td = [d for d in docs.values() if t in d["tags"]]
        err = [d for d in td if d["has_error"]]
        L.append(f"| {t} | {len(rs)} | {pct(sum(x['ok'] for x in rs), len(rs))} | "
                 f"{sum(d['review'] for d in err)}/{len(err)} |")

    L += ["", "## Calibration (stated confidence vs observed accuracy)", "",
          "| confidence | cells | mean stated | observed accuracy |", "|---|---|---|---|"]
    ece = 0.0
    for lo, hi in BUCKETS:
        b = [r for r in rows if lo <= r["conf"] < hi]
        if not b:
            continue
        acc, mc = sum(r["ok"] for r in b) / len(b), sum(r["conf"] for r in b) / len(b)
        ece += len(b) / n * abs(acc - mc)
        L.append(f"| {lo:.2f}-{min(hi, 1.0):.2f} | {len(b)} | {mc:.2f} | {acc:.0%} |")
    L += ["", f"expected calibration error (ECE): **{ece:.3f}** (0 = perfectly calibrated)", ""]

    wrong = [r for r in rows if not r["ok"]]
    silent = [r for r in wrong if r["conf"] >= thr]
    flagged_ok = [r for r in rows if r["ok"] and r["conf"] < thr]
    L += ["## Review behaviour", "",
          f"- wrong cells: {len(wrong)}; caught (confidence < {thr}): **{pct(len(wrong) - len(silent), len(wrong))}**",
          f"- **silent errors** (wrong but confidence >= {thr}): **{len(silent)}** ({pct(len(silent), n)} of all cells)",
          f"- correct cells flagged for nothing: {len(flagged_ok)} ({pct(len(flagged_ok), sum(r['ok'] for r in rows))} of correct)"]
    with_err = [d for d in docs.values() if d["has_error"]]
    clean = [d for d in docs.values() if not d["has_error"]]
    L += [f"- documents containing an error that were flagged for review: **{pct(sum(d['review'] for d in with_err), len(with_err))}**",
          f"- fully-correct documents flagged anyway: {pct(sum(d['review'] for d in clean), len(clean))}", ""]
    def short(v, n=60):
        t = repr(v)
        return t if len(t) <= n else t[:n - 1] + "..."

    from collections import Counter
    fa = Counter(fl for r in flagged_ok for fl in (r["flags"] or ["(low confidence, no flag)"]))
    if fa:
        L += ["Why correct cells were flagged (flag counts; one cell can carry several):", "",
              "| flag | cells |", "|---|---|"] + [f"| {k} | {v} |" for k, v in fa.most_common(10)] + [""]
    if silent:
        L += ["Silent errors, highest confidence first (read these first):", "",
              "| doc | field | conf | predicted | gold | flags |", "|---|---|---|---|---|---|"]
        for r in sorted(silent, key=lambda r: -r["conf"])[:40]:
            L.append(f"| {r['doc']} | {r['field']} | {r['conf']} | {short(r['pred'])} | {short(r['gold'])} | {', '.join(r['flags'])} |")
        if len(silent) > 40:
            L.append(f"\n... and {len(silent) - 40} more (see errors.md)")
        L.append("")

    err = ["# All wrong cells", "", f"run `{args.run}` - {len(wrong)} wrong cells, sorted by confidence (highest first)", "",
           "| doc | field | conf | predicted | gold | flags |", "|---|---|---|---|---|---|"]
    for r in sorted(wrong, key=lambda r: -r["conf"]):
        err.append(f"| {r['doc']} | {r['field']} | {r['conf']} | {short(r['pred'], 80)} | {short(r['gold'], 80)} | {', '.join(r['flags'])} |")
    (run_dir / "errors.md").write_text("\n".join(err))

    report = "\n".join(L)
    (run_dir / "report.md").write_text(report)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
