# Evaluation: `groq_fixed`

model: groq | passes: 2 | documents scored: 19/20 | failed: ['co_08'] | review threshold: 0.7

## Accuracy

- all scored cells: **90%** (943 cells)
- scalar fields only: 84%
- line-item cells: 93%
- line items missed: 3, extra (invented): 2
- documents with every field and item correct: **0%**

| field | accuracy | mean confidence |
|---|---|---|
| description | 42% | 0.67 |
| reason | 58% | 0.67 |
| status | 68% | 0.92 |
| total | 79% | 0.85 |
| co_date | 84% | 0.87 |
| owner | 84% | 0.89 |
| signed | 84% | 0.84 |
| co_number | 89% | 0.91 |
| project_name | 89% | 0.94 |
| contractor | 89% | 0.93 |
| markup_amount | 89% | 0.83 |
| currency | 89% | 0.81 |
| original_contract_sum | 89% | 0.85 |
| item.description | 90% | 0.89 |
| item.unit | 93% | 0.92 |
| item.unit_price | 93% | 0.91 |
| item.quantity | 94% | 0.91 |
| subtotal | 95% | 0.86 |
| markup_percent | 95% | 0.87 |
| schedule_impact_days | 95% | 0.88 |
| item.amount | 95% | 0.89 |
| new_contract_sum | 100% | 0.81 |

## By difficulty tag

| tag | cells | accuracy | docs flagged / docs with errors |
|---|---|---|---|
| ambiguous_date | 84 | 48% | 2/2 |
| baseline | 74 | 96% | 2/2 |
| credit | 190 | 73% | 5/5 |
| deductive_total | 32 | 94% | 1/1 |
| distractor_numbers | 79 | 95% | 2/2 |
| email | 138 | 93% | 4/4 |
| eu_number_format | 37 | 97% | 1/1 |
| missing_fields | 64 | 92% | 2/2 |
| multipage | 334 | 99% | 2/2 |
| narrative_layout | 37 | 92% | 1/1 |
| no_markup | 194 | 99% | 2/2 |
| non_usd | 37 | 97% | 1/1 |
| ocr_doc | 143 | 50% | 4/4 |
| ocr_required | 143 | 50% | 4/4 |
| poor_quality | 74 | 16% | 2/2 |
| scan | 143 | 50% | 4/4 |
| source_inconsistent | 37 | 97% | 1/1 |
| text_doc | 800 | 97% | 15/15 |

## Calibration (stated confidence vs observed accuracy)

| confidence | cells | mean stated | observed accuracy |
|---|---|---|---|
| 0.00-0.50 | 134 | 0.28 | 45% |
| 0.50-0.70 | 15 | 0.61 | 93% |
| 0.70-0.85 | 7 | 0.76 | 57% |
| 0.85-0.95 | 33 | 0.85 | 55% |
| 0.95-1.00 | 754 | 1.00 | 99% |

expected calibration error (ECE): **0.046** (0 = perfectly calibrated)

## Review behaviour

- wrong cells: 97; caught (confidence < 0.7): **77%**
- **silent errors** (wrong but confidence >= 0.7): **22** (2% of all cells)
- correct cells flagged for nothing: 74 (9% of correct)
- documents containing an error that were flagged for review: **100%**
- fully-correct documents flagged anyway: n/a

Why correct cells were flagged (flag counts; one cell can carry several):

| flag | cells |
|---|---|
| low_ocr_confidence | 55 |
| passes_disagree | 32 |
| item_missing_in_other_pass | 18 |
| value_not_in_evidence | 11 |
| evidence_absent | 6 |
| items_sum_mismatch | 3 |
| (low confidence, no flag) | 2 |
| value_spans_lines | 2 |
| ambiguous_date | 1 |
| evidence_fuzzy | 1 |

Silent errors, highest confidence first (read these first):

| doc | field | conf | predicted | gold | flags |
|---|---|---|---|---|---|
| co_10 | status | 1.0 | 'Executed - need your sign-off to proceed.' | 'Executed' |  |
| co_11 | status | 1.0 | 'Approved - need your sign-off to proceed.' | 'Approved' |  |
| co_12 | status | 1.0 | 'Approved - need your sign-off to proceed.' | 'Approved' |  |
| co_13 | description | 1.0 | 'Upgrade light fixtures to LED and waterproofing membrane' | 'The parties agreed to the following value-engineering chan... |  |
| co_15 | co_date | 0.85 | None | '2026-03-13' |  |
| co_15 | project_name | 0.85 | None | 'Summit Peak Brewery Buildout' |  |
| co_15 | owner | 0.85 | None | 'Lakeshore Township' |  |
| co_15 | reason | 0.85 | None | 'Unforeseen site condition' |  |
| co_15 | description | 0.85 | None | 'Conditions found on site differ from the contract document... |  |
| co_15 | markup_percent | 0.85 | None | 15.0 |  |
| co_15 | markup_amount | 0.85 | None | 3826.78 |  |
| co_15 | status | 0.85 | None | 'Executed' |  |
| co_15 | signed | 0.85 | None | True |  |
| co_16 | description | 0.85 | None | 'Conditions found on site differ from the contract document... |  |
| co_20 | contractor | 0.85 | None | 'Blue Ridge Concrete Works' |  |
| co_20 | reason | 0.85 | None | 'Owner-requested scope change' |  |
| co_20 | subtotal | 0.85 | None | 14500.91 |  |
| co_20 | status | 0.85 | None | 'Executed' |  |
| co_20 | signed | 0.85 | None | True |  |
| co_16 | owner | 0.784 | 'Westfield a Partners' | 'Westfield Capital Partners' |  |
| co_15 | total | 0.722 | None | 29338.66 | required_missing |
| co_20 | total | 0.722 | None | 16676.05 | required_missing |
