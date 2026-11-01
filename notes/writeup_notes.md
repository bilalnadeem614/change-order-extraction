# Running notes for the write-up

Findings and failure modes as they are discovered, so the final write-up reports
measurements instead of guesses.

## Dataset (self-made, 20 documents)
- Sledge supplied no samples, so the set is synthetic: 11 form PDFs (3 multi-page), 4 emails,
  4 image-only scans, 1 narrative letter. Gold is hand-checkable and verified by
  `scripts/verify_dataset.py` (schema, arithmetic, every gold value printed in the document).
- Small and self-generated: results will look better than on real change orders. Say so.
- `currency` is inferred from the symbol ($ -> USD).

## OCR (ingest stage)
- Metric: share of gold money values found verbatim in the OCR text (strict: one wrong digit = miss).
- Raw Tesseract: good scans ~85-100%, poor scans 20-65%.
- Preprocessing is NOT a reliable win. Same documents, different settings:
  - deskew rescued co_15 (20% -> 47%) but wrecked co_20 (65% -> 6%) and co_14 (85% -> 38%)
  - binarize dropped everything to ~0-8%
  - 200 dpi vs 300 dpi: worse on average
  - My skew estimator was accurate (within 0.25 deg of the known rotation), so the swings are
    OCR instability on degraded images, not a bug in deskew.
- Chosen default: plain Tesseract, 300 dpi, psm 3, no deskew (best mean, 61%).
- Consequence for the design: OCR digits on poor scans cannot be trusted by themselves.
  Signals that must carry this: per-word OCR confidence, arithmetic cross-checks
  (qty x price = amount, items sum to subtotal), and agreement between two extraction passes.
- Open option for the write-up: send the page image to a vision-capable model instead of OCR.
- Tuned on the same 4 scans it is scored on. Mention this.

## Text-layer PDFs
- A wrapped cell in the two-column header interleaves with its neighbour in pdfplumber's text
  (e.g. a long project name next to the owner). Realistic; the LLM has to cope with it.
  Not fixed on purpose - watch whether it causes real extraction errors.

## Evidence grounding - what the plumbing check showed (affects the confidence step)
- `currency`: the code ("USD") is never printed, only "$". Grounding must map symbols to codes,
  otherwise every currency field looks unsupported.
- `description`: wraps across lines, so evidence must be matched on whitespace-normalised text,
  not line by line.
- `project_name` (co_01, co_06): wrapped header cell interleaved with its neighbour, so no single
  line contains the whole name. Same interleaving issue as noted above, now confirmed to matter.
- OCR mean confidence tracks quality (43 on the worst scan, 60-68 on the others), consistent
  with the digit hit rates. Only 4 scans, so treat as a hint, not a calibrated signal.

## Validation + confidence design (steps 4-5)
- Confidence is NOT the model's self-report. It is a product of: evidence grounding (quote is in the
  document AND the value is in the quote), failed arithmetic checks, agreement between two passes,
  OCR word confidence, and an "absence hint" (field reported null although the text mentions it).
- The two grounding failures are different and both matter: an invented/mangled quote (absent) vs a
  correct quote with a wrong value (value_not_in_evidence). Tests cover both.
- A "consistent lie" (value and quote both wrong) is invisible to grounding; only the arithmetic
  catches it. This is why the arithmetic checks matter more than they look.
- The validator never repairs. co_18's printed total is wrong; the output keeps the printed value and
  flags it (total confidence 0.30). A silently "corrected" total would be a worse failure.
- Arithmetic mismatches implicate every field in the equation: they cannot say which number is wrong
  (misread digit vs error in the source), so all are lowered.
- Ambiguous numeric dates (04/03/2026) are scored 0.55 so they always reach review. An early version
  used a mild 0.85 penalty and a swapped date slipped through as a silent error.
- Second pass: for scans it reads a differently-preprocessed OCR (deskew + psm 6), so OCR digit errors
  differ between passes; for text documents it is the same text at temperature 0.7. Costs 2x.
- Weights are hand-set priors, NOT fitted. They must be checked with scripts/evaluate.py on a real run.
- Known weak spot: if pass 2 errs and pass 1 is right, the right value still gets flagged. Acceptable
  (flagging disagreement is the point) but it raises the false-review rate.
- Wrapped values (long descriptions): "value spans lines" is a mild penalty (0.9), not the heavy one.

## What the simulated run does and does not show
- scripts/sim_client.py injects known errors. It proves the tooling reacts sensibly (errors are
  caught, clean documents pass, co_18 and the ambiguous dates are flagged). It says NOTHING about real
  accuracy and must never be quoted as a result.
- It cannot validate scan calibration: it replays gold values even where Tesseract garbled the digits,
  so the scorer correctly distrusts them while the "answer" is right. 120 of the 132 low-confidence
  cells in the sim were on the 4 scans for this reason.
- Real numbers need a real run: `python scripts/run_dataset.py --provider anthropic --run <name>`
  then `python scripts/evaluate.py --run <name>`.

## First real run (Groq openai/gpt-oss-120b, free tier) - what it showed
- 89% of cells correct, but 60 "silent errors" (wrong, confidence >= 0.7). The top ones were
  `project_name` and `item.description` at confidence 1.0.
- Root cause was NOT the model: a cell that wraps onto a second line was cut in two by the plain
  text read ("... Level 4, Zone" / "A"; "Maple Ridge Elementary Gym" / "Addition"). The model quoted the
  first line correctly, so the quote was exact and the (truncated) value was "in the evidence": grounding
  saw nothing wrong. Before the fix 26 of 181 gold text values were split across lines (item descriptions
  84% intact, project_name 88%).
- Fix at ingest: ruled tables are read from the table structure (`cell | cell | cell`, wrapped lines
  joined); for table-less two-column forms a stray, non-bold, label-free fragment is re-attached to the cell
  it is aligned under (same x, normal line spacing). After: 0 of 181 split. Every changed line was checked.
- Safety net: a stray fragment ingest cannot attach is recorded as an orphan, and any text value on the
  line above it is penalised (`may_be_truncated`, x0.5). Text-only version of this check was tried first and
  rejected: it fired on correct `status` values in almost every document, because a wrapped BOLD label
  ("Owner" / "signature:") looks like a wrapped value in plain text. Font weight is what separates them.
- Limits to state honestly: the reflow rules are tuned on this generator's layouts (6pt gap, 1.5pt
  alignment, 1.6x line spacing); real forms will break them in ways not seen here. Scans get no
  protection (no font/position info). The flag cannot tell which cell an unattached tail belongs to.
- Lesson for the write-up: an evidence quote proves the value is on the page, not that it is complete.
  A wrong answer at confidence 1.0 was a bug in the evidence check's assumptions, found only by a real run.

## LLM provider
- No API key was available in the build sandbox, so live extraction was not run there.
  Anthropic does not return token logprobs, so the confidence score cannot use them with that
  provider; it uses evidence grounding, validation and two-pass agreement instead.
