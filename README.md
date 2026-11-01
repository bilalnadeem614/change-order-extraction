# Change-order extraction pipeline

Turns messy change-order documents (text PDFs, scanned PDFs, emails) into validated JSON.
Every field comes back with a value, a **confidence score**, the **evidence quote** it was read
from, and flags explaining any penalty. Documents that need a human look are marked `needs_review`.

```
file -> ingest (text layer, or OCR for scans)
     -> LLM extraction (x2 passes)  : value + verbatim evidence per field
     -> validation                  : arithmetic + plausibility checks (never "fixes" numbers)
     -> confidence scoring          : grounding, failed checks, pass agreement, OCR quality
     -> JSON with per-field confidence + needs_review
```

## 1. Setup (once)

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

**OCR tools** are only needed for the 4 *scanned* test documents (co_14, co_15, co_16, co_20).
Everything else works without them.

| OS | install |
|---|---|
| Windows | Tesseract (UB Mannheim installer) + Poppler (oschwartz10612 build); add both `bin` folders to PATH |
| macOS | `brew install tesseract poppler` |
| Ubuntu/WSL | `sudo apt install tesseract-ocr poppler-utils` |

## 2. Set your Groq key

```powershell
# Windows PowerShell
$env:GROQ_API_KEY="gsk_your_key_here"
```
```cmd
:: Windows cmd
set GROQ_API_KEY=gsk_your_key_here
```
```bash
# macOS / Linux
export GROQ_API_KEY=gsk_your_key_here
```

## 3. Run it

**One document first** (a quick check that the key and model work):
```bash
python -m co_extract.cli data/raw/co_01_clean_form.pdf --provider groq
```

**The whole 20-document test set, then the evaluation report:**
```bash
python scripts/run_dataset.py --provider groq --run groq_first
python scripts/evaluate.py  --run groq_first
```
The report is saved to `outputs/groq_first/report.md` (accuracy per field and per difficulty tag,
a calibration table, and the "silent errors": wrong fields that still scored high).

**Your own file:** `python -m co_extract.cli path/to/anything.pdf --provider groq --out result.json`

### Options
| flag | meaning |
|---|---|
| `--model NAME` | default is `openai/gpt-oss-120b`; try `llama-3.3-70b-versatile` if it misbehaves |
| `--passes 1` | one LLM call per document instead of two (half the tokens; no agreement signal) |
| `--ids co_01 co_10` | (run_dataset) only these documents |
| `--threshold 0.7` | confidence below this means "review" |
| `--show-text` | print what ingest extracted and stop (debug OCR / text issues) |

Other providers: `--provider anthropic` (ANTHROPIC_API_KEY) or `--provider openai`
(OPENAI_API_KEY, optional OPENAI_BASE_URL, and `--model`).

## 4. Tests (no API key needed)

```bash
python -m pytest -q
```
These test the plumbing and scoring logic with a mock that replays the answer key. They prove
the wiring and the confidence behaviour, **not** model accuracy. Accuracy only comes from step 3.

## Troubleshooting
- **Rate limit / 429 / 413:** Groq's free tier caps tokens per minute. Use `--passes 1`, a smaller
  `--ids` batch, or wait a minute. The three multi-page documents (co_07, co_08, co_09) are the largest.
- **"tool_use_failed" / "malformed tool calls":** the model produced a broken tool call. The client
  retries 3 times; if it persists, switch `--model`.
- **"output truncated":** a long document needs more output tokens; raise `max_tokens` in `co_extract/llm.py`.
- **"tesseract is not installed" / poppler errors:** only the scans need them (see Setup).
- Failed documents are recorded as `outputs/<run>/<id>.error.txt`; the run continues.

## Layout
```
co_extract/   schema, ingest, llm (providers), extract (prompt), grounding, validate, confidence, pipeline, cli
scripts/      generate_data (synthetic test set), verify_dataset, run_dataset, evaluate, ocr_ablation, sim_client
data/         raw/ (20 test documents), gold/ (answer keys), manifest.json (difficulty tags)
tests/        plumbing + behaviour tests
notes/        writeup_notes.md - findings and failure modes collected while building
```

## About the test data
Sledge supplied no sample documents, so the 20 test documents are synthetic (`scripts/generate_data.py`,
seeded and reproducible). They are small and self-made, so scores will look better than on real change
orders. `currency` is inferred from the symbol ($ -> USD).
