# All wrong cells

run `groq_v3` - 85 wrong cells, sorted by confidence (highest first)

| doc | field | conf | predicted | gold | flags |
|---|---|---|---|---|---|
| co_19 | description | 1.0 | 'Work covers rebar, #5 grade 60 and fire-rated door and hardware.' | "At the owner's request, additional scope was added. Work covers rebar, #5 grad... |  |
| co_14 | item.unit | 0.564 | None | 'LB' | null_on_ocr_text |
| co_14 | item.unit_price | 0.564 | None | 0.94 | null_on_ocr_text |
| co_20 | contractor | 0.526 | None | 'Blue Ridge Concrete Works' | null_on_ocr_text |
| co_20 | reason | 0.526 | None | 'Owner-requested scope change' | null_on_ocr_text |
| co_20 | subtotal | 0.526 | None | 14500.91 | null_on_ocr_text |
| co_20 | status | 0.526 | None | 'Executed' | null_on_ocr_text |
| co_20 | signed | 0.526 | None | True | null_on_ocr_text |
| co_15 | co_date | 0.459 | None | '2026-03-13' | null_on_ocr_text |
| co_15 | project_name | 0.459 | None | 'Summit Peak Brewery Buildout' | null_on_ocr_text |
| co_15 | owner | 0.459 | None | 'Lakeshore Township' | null_on_ocr_text |
| co_15 | reason | 0.459 | None | 'Unforeseen site condition' | null_on_ocr_text |
| co_15 | description | 0.459 | None | 'Conditions found on site differ from the contract documents. Work covers crane... | null_on_ocr_text |
| co_15 | markup_percent | 0.459 | None | 15.0 | null_on_ocr_text |
| co_15 | markup_amount | 0.459 | None | 3826.78 | null_on_ocr_text |
| co_15 | status | 0.459 | None | 'Executed' | null_on_ocr_text |
| co_15 | signed | 0.459 | None | True | null_on_ocr_text |
| co_14 | description | 0.436 | 'Z is change reponse to. — clarification. Work covers aia supply duct section a... | 'This change responds to a design clarification. Work covers replace supply duc... | passes_disagree |
| co_17 | reason | 0.425 | None | 'Owner-requested scope change' | possible_missed_field |
| co_16 | description | 0.384 | 'Conditions found on-site differ from the contract documents. Work covers crane... | 'Conditions found on site differ from the contract documents. Work covers crane... | passes_disagree |
| co_07 | item.quantity | 0.382 | None | 98.0 | passes_disagree, item_missing_in_other_pass |
| co_07 | item.unit | 0.382 | None | 'CY' | passes_disagree, item_missing_in_other_pass |
| co_07 | item.unit_price | 0.382 | None | 113.78 | passes_disagree, item_missing_in_other_pass |
| co_16 | owner | 0.353 | 'Westfield a Partners' | 'Westfield Capital Partners' | passes_disagree |
| co_20 | total | 0.315 | None | 16676.05 | null_on_ocr_text, required_missing |
| co_14 | item.description | 0.295 | 'Additional 4" concrete slab pour Nicaea' | 'Additional 4" concrete slab pour' | low_ocr_confidence, passes_disagree |
| co_16 | item.quantity | 0.286 | None | 4.0 | null_on_ocr_text, passes_disagree |
| co_14 | co_date | 0.282 | None | '2025-08-30' | possible_missed_field, null_on_ocr_text |
| co_15 | total | 0.275 | None | 29338.66 | null_on_ocr_text, required_missing |
| co_15 | item.description | 0.274 | 'Supervision labor PES ReION Saree i' | 'Supervision labor' | low_ocr_confidence, passes_disagree |
| co_20 | markup_percent | 0.263 | None | 15.0 | possible_missed_field, null_on_ocr_text |
| co_20 | markup_amount | 0.263 | None | 2175.14 | possible_missed_field, null_on_ocr_text |
| co_20 | schedule_impact_days | 0.263 | None | 10 | possible_missed_field, null_on_ocr_text |
| co_20 | project_name | 0.259 | '. Oaks Sar vg Wn 8' | 'Oakwood Senior Living Wing B' | low_ocr_confidence, passes_disagree |
| co_16 | item.description | 0.24 | 'Credit: omit decorative wall: trim' | 'Credit: omit decorative wall trim' | value_spans_lines, low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.description | 0.238 | 'Overhead & Profit (15%)' | 'Credit: delete interior doors' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.amount | 0.238 | 2175.14 | -4706.34 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | co_date | 0.237 | None | '2026-05-04' | null_on_ocr_text, passes_disagree |
| co_20 | description | 0.237 | None | "At the owner's request, additional scope was added. Work covers excavation for... | null_on_ocr_text, passes_disagree |
| co_20 | item.quantity | 0.237 | None | 39.0 | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.237 | None | 'CY' | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.237 | None | 'EA' | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_20 | item.quantity | 0.237 | None | 15.0 | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.237 | None | 'EA' | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_20 | item.quantity | 0.237 | None | 3223.0 | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.237 | None | 'LB' | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.237 | None | 1.02 | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_20 | item.quantity | 0.237 | None | 6.0 | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.237 | None | 'EA' | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.237 | None | 784.39 | null_on_ocr_text, passes_disagree, item_missing_in_other_pass |
| co_15 | new_contract_sum | 0.229 | None | 3136838.66 | possible_missed_field, null_on_ocr_text |
| co_14 | item.description | 0.227 | 'supply duct section' | 'Replace supply duct section' | value_spans_lines, low_ocr_confidence, passes_disagree |
| co_20 | item.description | 0.212 | 'Frame adctional interior partion eee, WEL' | 'Excavation for unforeseen rock' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.212 | 29.66 | 133.93 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.amount | 0.212 | 5398.12 | 5223.27 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_15 | item.quantity | 0.206 | None | 23.0 | null_on_ocr_text, passes_disagree |
| co_15 | item.unit | 0.206 | None | 'HR' | null_on_ocr_text, passes_disagree |
| co_15 | item.unit_price | 0.206 | None | 70.35 | null_on_ocr_text, passes_disagree |
| co_15 | item.quantity | 0.206 | None | 38.0 | null_on_ocr_text, passes_disagree |
| co_15 | item.unit | 0.206 | None | 'EA' | null_on_ocr_text, passes_disagree |
| co_15 | item.unit_price | 0.206 | None | 182.09 | null_on_ocr_text, passes_disagree |
| co_20 | item.description | 0.202 | 'Credit: delete interior doors ee (BS Meese' | 'Rebar, #5 grade 60' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.amount | 0.202 | -4706.34 | 3287.46 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_15 | contractor | 0.196 | 'Beghting Construction' | 'Brightline Construction Inc.' | low_ocr_confidence, passes_disagree |
| co_20 | item.description | 0.184 | 'Relocate 20A electrical circuits' | 'Frame additional interior partition' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.quantity | 0.184 | 10.0 | 182.0 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.184 | 'EA' | 'LF' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.184 | 219.13 | 29.66 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.amount | 0.184 | 2191.3 | 5398.12 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | co_number | 0.158 | None | 'PCO-39' | possible_missed_field, null_on_ocr_text, required_missing |
| co_15 | co_number | 0.138 | None | '034' | possible_missed_field, null_on_ocr_text, required_missing |
| co_14 | currency | 0.127 | None | 'USD' | possible_missed_field, null_on_ocr_text, passes_disagree |
| co_20 | currency | 0.118 | None | 'USD' | possible_missed_field, null_on_ocr_text, passes_disagree |
| co_20 | item.description | 0.115 | 'Sprinkier head relocation' | 'Relocate 20A electrical circuits' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_15 | original_contract_sum | 0.09 | 8107800.0 | 3107500.0 | low_ocr_confidence, passes_disagree |
| co_15 | item.description | 0.09 | 'Sprinkler head relocation Hae' | 'Sprinkler head relocation' | low_ocr_confidence, passes_disagree |
| co_20 | item.description | 0.09 | 'Rebarsgrade6O Ae y' | 'Sprinkler head relocation' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.09 | 102.0 | 207.14 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.amount | 0.09 | 9287.46 | 3107.1 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_07 | new_contract_sum | 0.074 | 5847391.41 | 5847939.41 | value_not_in_evidence, passes_disagree, contract_sum_mismatch |
| co_07 | item.description | 0.067 | 'Excavation for\xa0\xa0unforeseen\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\x... | 'Excavation for unforeseen rock - Level 4, Zone B' | evidence_absent, passes_disagree, item_missing_in_other_pass |
| co_20 | item.quantity | 0.063 | 18.0 | 10.0 | low_ocr_confidence, passes_disagree, qty_price_mismatch, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.063 | 2074.0 | 219.13 | low_ocr_confidence, passes_disagree, qty_price_mismatch, item_missing_in_other_pass |
| co_20 | item.amount | 0.063 | 3107.1 | 2191.3 | low_ocr_confidence, passes_disagree, qty_price_mismatch, item_missing_in_other_pass |
| co_20 | original_contract_sum | 0.044 | 48522000.0 | 4852000.0 | value_not_in_evidence, low_ocr_confidence, passes_disagree |