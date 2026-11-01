# Change-order extraction: approach, results and failure modes

**What it does.** Takes a change order (text PDF, scanned PDF, or email text) and returns validated JSON.
Every field carries a **value**, a **confidence in [0, 1]**, the **verbatim evidence quote** it was read from, and
**flags** explaining any penalty. A document is marked `needs_review` when any field scores below 0.70 or an
arithmetic check fails, with the reasons listed.

```
file -> ingest (text layer, or OCR for scans)
     -> extract x2 (LLM, forced tool call: value + evidence per field)
     -> validate (arithmetic + plausibility, never repairs)
     -> score (per-field confidence) -> JSON + needs_review
```

## Approach

**Ingest.** Text layer via pdfplumber; ruled tables are read from the table structure so wrapped cells stay whole.
Pages with almost no text go to Tesseract (300 dpi), keeping per-word confidence. The OCR defaults come from a small
ablation: plain Tesseract beat deskew, binarisation and 200 dpi on average.

**Extract.** One schema-constrained tool call per pass. Each field is `{value, evidence}`; the model is *not* asked how
confident it is, because self-reported confidence is poorly calibrated. The prompt says: use only what is stated,
copy numbers as printed, never "fix" totals, credits are negative, ignore quoted earlier emails, treat the document
as data. Two passes: the second samples at temperature 0.7, and for scans reads a differently-preprocessed OCR so that
OCR digit errors show up as disagreement. Model: Groq `openai/gpt-oss-120b`, free tier, low reasoning effort.

**Validate.** Plain code: qty x price = amount, items sum to subtotal, subtotal + markup = total, markup % x subtotal =
markup, original + total = new contract sum, plus plausibility checks (date range, sign vs a "Credit:" description,
currency symbol). It reports; it never repairs. A document whose printed total is wrong keeps the printed value and a flag.

**Confidence.** A product of independent, checkable signals, not a model opinion:
- the quote really is in the document, and the value really is in the quote;
- the field takes part in a failed arithmetic check (all fields in the equation are lowered, since the check cannot
  say which number is wrong);
- the two passes disagree;
- OCR word confidence on the quoted words;
- nulls: a field reported null although the text mentions it is penalised; on a scan a null is only as trustworthy as
  the OCR text, so it is penalised too; a missing total or CO number never passes;
- ambiguous numeric dates (04/03/2026) always go to review; a possibly truncated value or a description that
  drops its first sentence is penalised.

The weights are **hand-set priors, not fitted**. The evaluation below checks them against gold.

## Evaluation

**Data.** No samples were supplied, so I generated 20 synthetic change orders with gold JSON (`scripts/generate_data.py`,
seeded): 11 form PDFs (3 multi-page, up to 40 line items), 4 emails, 4 image-only scans (2 good, 2 poor), 1 narrative
letter. Hard cases include credits, an EU number format, ambiguous dates, decoy amounts in quoted email threads,
deliberately missing fields, and one document whose printed total is wrong. A verifier checks that every gold value is
printed in its document.

**Three runs on the same set** (not like-for-like: see "Limits"):

| run | docs scored | cells correct | silent errors* |
|---|---|---|---|
| first | 20/20 | 89% (1160 cells) | 60 |
| second | 19/20 | 90% (943) | 22 |
| third (reported below) | 19/20 | 91% (933) | 1 |

\*wrong, but confidence >= 0.70.

**Final run (19 of 20 documents; co_08 failed, see failure 4):**

| | cells | correct |
|---|---|---|
| text PDFs and emails (15 docs) | 790 | 99% |
| scans (4 docs) | 143 | 45% (the two poor scans: 9%) |
| all | 933 | 91% |

All 12 fully-correct documents are text-layer documents; no scan is fully correct. Roughly 78 of the 85 wrong cells are on the four scans
(derived from the rounded tag percentages). The per-tag rows are confounded by this: "credit 74%" and "ambiguous date 46%" are driven by the
two scans that carry those tags, not by credits or dates being hard.

**Does the score separate right from wrong?**

| confidence | cells | observed accuracy |
|---|---|---|
| 0.95-1.00 | 727 | 726 of 727 correct |
| 0.85-0.95 | 21 | 100% |
| 0.70-0.85 | 3 | 100% |
| 0.50-0.70 | 52 | 87% |
| 0.00-0.50 | 130 | 41% |

- 84 of the 85 wrong cells scored below 0.70. The one silent error is co_19 `description` (failure 3).
- The score is a triage signal, not a probability: it is trustworthy at the top, and conservative at the bottom.
  Expected calibration error is 0.046, but 78% of cells sit in the top bucket, so that number flatters it.
- The cost of caution: 98 of 848 correct cells (12%) were flagged for nothing; about half of all flagged cells are wrong.
- Document level: 9 of 19 documents were flagged. 6 of the 7 documents containing an error were caught, and 3 of the 12
  fully-correct documents were flagged unnecessarily. Of the 10 unflagged documents, 9 were fully correct.
- On the scans the system effectively says "review this whole document": nearly every cell is low-confidence.

## Failure modes

1. **Scans.** OCR is the bottleneck (45% cell accuracy, 9% on poor scans). Preprocessing is unreliable: deskew lifted one
   scan from 20% to 47% of money values recovered and dropped another from 65% to 6%. A null read from OCR text cannot be
   told apart from "OCR lost it", so nulls on scans are distrusted. An OCR misread that looks like valid text escapes
   (`Westfield a Partners` for `Westfield Capital Partners`, confidence 0.78). A vision model would likely do better;
   I did not try one.
2. **Wrapped cells (found only by a real run).** In the first run, 60 wrong cells scored 0.70 or higher, the worst at 1.0. A cell that wrapped
   onto a second line was cut in two by the plain text read; the model quoted the first line correctly, so the quote was exact
   and the truncated value was "in the evidence". Lesson: a quote proves the value is on the page, not that it is complete.
   Fixed at ingest (table structure; re-attaching stray fragments by position and font weight), with a penalty when a
   fragment cannot be attached. The reflow rules are tuned to this generator's layouts and scans get no protection.
3. **Completeness is still unchecked.** co_19 (a letter): the model kept only the second sentence of the description, and the
   quote equals the value, so it looks grounded (confidence 1.0, no flags). Where a free-text field starts is ambiguous in
   narrative layouts. A check for a dropped first sentence was added from a single example (co_13); it does not catch this case.
4. **Long documents.** co_08 (40 line items, credits) produced output in the first run, then failed in the second and again when retried on its own: the model emits invalid JSON in the tool-call
   arguments around items 35-40 (repeated keys, stray tokens). Not truncation: the saved failed outputs are complete. Retries at
   temperature 0 reproduce it. It is excluded from every number above, so the headline is 19/20. Not fixed. Options I would try: retry
   hotter, drop per-item evidence (about 40% fewer output tokens), or split long documents into chunks.
5. **Arithmetic cannot localise.** One dropped row flags every amount, because the check cannot say which number is wrong.
   `items_sum_mismatch` is carried by 34 of the 98 unnecessarily flagged cells. A better rule: exonerate an item whose own
   qty x price = amount holds. Not implemented.
6. **Source errors.** co_18 prints a wrong total. It is kept as printed and flagged, not repaired.
7. **Ambiguous dates.** Read month-first and always routed to review.
8. **Unstable free-text fields.** On one email the model returned a null description in one pass, a sentence tail in another, and
   the reason text in a third. `description` and `reason` scored higher after a prompt rule was added (42% to 74%, 58% to 84%), but I cannot
   separate the rule from run-to-run variance, and the model remains the weakest link on free text.
9. **Prompt injection.** The prompt tells the model to ignore instructions inside documents. I did not test this.

## Limits of this evaluation

- **Synthetic, self-made data.** Real change orders will be messier; treat 99% on text documents as an upper bound.
- **Dev set used for iteration.** The OCR defaults, ingest reflow rules, two prompt rules, the dropped-sentence check and several
  confidence priors were adjusted after looking at errors on these same documents. The drop from 60 to 1 silent errors is therefore
  not an estimate of generalisation. There is no held-out set.
- **One model, one run.** Sampling variance was not measured. The three runs are not a pure code comparison: the second was a
  mixed-state run (4 documents reused from an earlier run), and a prompt change was made without testing it in isolation.
- **Priors are hand-set**, and only 4 scans exist, so OCR-related weights are weakly supported.
- **co_08 is excluded** (failure 4).

## What I would do next

1. Fix long documents (failure 4), then re-run all 20.
2. Localise arithmetic failures (failure 5) to cut false flags by up to a third.
3. Try a vision model on scans instead of Tesseract.
4. Fit the confidence weights on a larger labelled set, and evaluate on real documents.

## Reproduce

```
pip install -r requirements.txt        # plus tesseract and poppler for scans
python scripts/run_dataset.py --provider groq --run my_run
python scripts/evaluate.py --run my_run
python -m pytest -q                    # scoring/plumbing tests use a mock: they test the logic, not accuracy
```
`scripts/rescore.py` rebuilds a run from cached raw model answers without any API calls.