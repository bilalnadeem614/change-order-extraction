# Evaluation: `groq_v3`

model: groq | passes: 2 | documents scored: 19/20 | failed: ['co_08'] | review threshold: 0.7

## Accuracy

- all scored cells: **91%** (933 cells)
- scalar fields only: 89%
- line-item cells: 92%
- line items missed: 5, extra (invented): 1
- documents with every field and item correct: **63%**

| field | accuracy | mean confidence |
|---|---|---|
| description | 74% | 0.87 |
| co_date | 84% | 0.83 |
| reason | 84% | 0.84 |
| co_number | 89% | 0.89 |
| project_name | 89% | 0.92 |
| owner | 89% | 0.87 |
| contractor | 89% | 0.90 |
| markup_percent | 89% | 0.84 |
| markup_amount | 89% | 0.79 |
| total | 89% | 0.80 |
| currency | 89% | 0.82 |
| original_contract_sum | 89% | 0.79 |
| new_contract_sum | 89% | 0.74 |
| status | 89% | 0.91 |
| signed | 89% | 0.87 |
| item.description | 90% | 0.90 |
| item.quantity | 92% | 0.90 |
| item.unit | 92% | 0.90 |
| item.unit_price | 92% | 0.90 |
| subtotal | 95% | 0.79 |
| schedule_impact_days | 95% | 0.87 |
| item.amount | 95% | 0.78 |

## By difficulty tag

| tag | cells | accuracy | docs flagged / docs with errors |
|---|---|---|---|
| ambiguous_date | 84 | 46% | 1/1 |
| baseline | 74 | 100% | 0/0 |
| credit | 190 | 74% | 2/2 |
| deductive_total | 32 | 100% | 0/0 |
| distractor_numbers | 79 | 100% | 0/0 |
| email | 138 | 100% | 0/0 |
| eu_number_format | 37 | 97% | 1/1 |
| missing_fields | 64 | 98% | 0/1 |
| multipage | 324 | 98% | 1/1 |
| narrative_layout | 37 | 97% | 0/1 |
| no_markup | 194 | 100% | 0/0 |
| non_usd | 37 | 97% | 1/1 |
| ocr_doc | 143 | 45% | 4/4 |
| ocr_required | 143 | 45% | 4/4 |
| poor_quality | 74 | 9% | 2/2 |
| scan | 143 | 45% | 4/4 |
| source_inconsistent | 37 | 100% | 0/0 |
| text_doc | 790 | 99% | 2/3 |

## Calibration (stated confidence vs observed accuracy)

| confidence | cells | mean stated | observed accuracy |
|---|---|---|---|
| 0.00-0.50 | 130 | 0.24 | 41% |
| 0.50-0.70 | 52 | 0.56 | 87% |
| 0.70-0.85 | 3 | 0.78 | 100% |
| 0.85-0.95 | 21 | 0.86 | 100% |
| 0.95-1.00 | 727 | 1.00 | 100% |

expected calibration error (ECE): **0.046** (0 = perfectly calibrated)

## Review behaviour

- wrong cells: 85; caught (confidence < 0.7): **99%**
- **silent errors** (wrong but confidence >= 0.7): **1** (0% of all cells)
- correct cells flagged for nothing: 98 (12% of correct)
- documents containing an error that were flagged for review: **86%**
- fully-correct documents flagged anyway: 25%

Why correct cells were flagged (flag counts; one cell can carry several):

| flag | cells |
|---|---|
| low_ocr_confidence | 47 |
| passes_disagree | 40 |
| items_sum_mismatch | 34 |
| item_missing_in_other_pass | 10 |
| value_not_in_evidence | 10 |
| contract_sum_mismatch | 5 |
| value_spans_lines | 3 |
| total_mismatch | 3 |
| evidence_missing | 2 |
| (low confidence, no flag) | 2 |

Silent errors, highest confidence first (read these first):

| doc | field | conf | predicted | gold | flags |
|---|---|---|---|---|---|
| co_19 | description | 1.0 | 'Work covers rebar, #5 grade 60 and fire-rated door and har... | "At the owner's request, additional scope was added. Work c... |  |
