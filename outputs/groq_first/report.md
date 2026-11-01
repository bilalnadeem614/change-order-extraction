# Evaluation: `groq_first`

model: groq | passes: 2 | documents scored: 20/20 | failed: none | review threshold: 0.7

## Accuracy

- all scored cells: **89%** (1160 cells)
- scalar fields only: 86%
- line-item cells: 91%
- line items missed: 3, extra (invented): 2
- documents with every field and item correct: **15%**

| field | accuracy | mean confidence |
|---|---|---|
| reason | 60% | 0.74 |
| description | 65% | 0.76 |
| status | 70% | 0.92 |
| item.description | 77% | 0.93 |
| project_name | 80% | 0.96 |
| co_date | 85% | 0.90 |
| total | 85% | 0.84 |
| co_number | 90% | 0.91 |
| owner | 90% | 0.97 |
| contractor | 90% | 0.92 |
| currency | 90% | 0.86 |
| original_contract_sum | 90% | 0.84 |
| signed | 90% | 0.93 |
| item.quantity | 91% | 0.92 |
| item.unit | 95% | 0.96 |
| item.unit_price | 95% | 0.93 |
| subtotal | 95% | 0.86 |
| markup_percent | 95% | 0.89 |
| markup_amount | 95% | 0.87 |
| schedule_impact_days | 95% | 0.88 |
| item.amount | 96% | 0.92 |
| new_contract_sum | 100% | 0.79 |

## By difficulty tag

| tag | cells | accuracy | docs flagged / docs with errors |
|---|---|---|---|
| ambiguous_date | 84 | 49% | 2/2 |
| baseline | 74 | 97% | 1/2 |
| credit | 407 | 84% | 5/5 |
| deductive_total | 32 | 97% | 1/1 |
| distractor_numbers | 79 | 96% | 2/2 |
| email | 138 | 96% | 4/4 |
| eu_number_format | 37 | 95% | 1/1 |
| missing_fields | 64 | 94% | 2/2 |
| multipage | 551 | 94% | 3/3 |
| narrative_layout | 37 | 95% | 1/1 |
| no_markup | 194 | 94% | 1/1 |
| non_usd | 37 | 95% | 1/1 |
| ocr_doc | 143 | 48% | 4/4 |
| ocr_required | 143 | 48% | 4/4 |
| poor_quality | 74 | 15% | 2/2 |
| scan | 143 | 48% | 4/4 |
| source_inconsistent | 37 | 100% | 0/0 |
| text_doc | 1017 | 95% | 12/13 |

## Calibration (stated confidence vs observed accuracy)

| confidence | cells | mean stated | observed accuracy |
|---|---|---|---|
| 0.00-0.50 | 97 | 0.29 | 42% |
| 0.50-0.70 | 52 | 0.59 | 87% |
| 0.70-0.85 | 9 | 0.78 | 67% |
| 0.85-0.95 | 51 | 0.85 | 41% |
| 0.95-1.00 | 951 | 1.00 | 97% |

expected calibration error (ECE): **0.067** (0 = perfectly calibrated)

## Review behaviour

- wrong cells: 123; caught (confidence < 0.7): **51%**
- **silent errors** (wrong but confidence >= 0.7): **60** (5% of all cells)
- correct cells flagged for nothing: 86 (8% of correct)
- documents containing an error that were flagged for review: **94%**
- fully-correct documents flagged anyway: 100%

Silent errors (these are what to read first):

- co_01 `project_name` confidence 1.0
- co_06 `project_name` confidence 1.0
- co_07 `item.description` confidence 1.0
- co_07 `item.description` confidence 1.0
- co_07 `item.description` confidence 1.0
- co_07 `item.description` confidence 1.0
- co_07 `item.description` confidence 1.0
- co_07 `item.description` confidence 1.0
- co_08 `item.description` confidence 1.0
- co_08 `item.description` confidence 1.0
- co_08 `item.description` confidence 1.0
- co_08 `item.description` confidence 1.0
- co_08 `item.description` confidence 1.0
- co_08 `item.description` confidence 1.0
- co_08 `item.description` confidence 1.0
