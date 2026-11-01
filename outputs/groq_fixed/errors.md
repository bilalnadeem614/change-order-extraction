# All wrong cells

run `groq_fixed` - 97 wrong cells, sorted by confidence (highest first)

| doc | field | conf | predicted | gold | flags |
|---|---|---|---|---|---|
| co_10 | status | 1.0 | 'Executed - need your sign-off to proceed.' | 'Executed' |  |
| co_11 | status | 1.0 | 'Approved - need your sign-off to proceed.' | 'Approved' |  |
| co_12 | status | 1.0 | 'Approved - need your sign-off to proceed.' | 'Approved' |  |
| co_13 | description | 1.0 | 'Upgrade light fixtures to LED and waterproofing membrane' | 'The parties agreed to the following value-engineering changes. Work covers upg... |  |
| co_15 | co_date | 0.85 | None | '2026-03-13' |  |
| co_15 | project_name | 0.85 | None | 'Summit Peak Brewery Buildout' |  |
| co_15 | owner | 0.85 | None | 'Lakeshore Township' |  |
| co_15 | reason | 0.85 | None | 'Unforeseen site condition' |  |
| co_15 | description | 0.85 | None | 'Conditions found on site differ from the contract documents. Work covers crane... |  |
| co_15 | markup_percent | 0.85 | None | 15.0 |  |
| co_15 | markup_amount | 0.85 | None | 3826.78 |  |
| co_15 | status | 0.85 | None | 'Executed' |  |
| co_15 | signed | 0.85 | None | True |  |
| co_16 | description | 0.85 | None | 'Conditions found on site differ from the contract documents. Work covers crane... |  |
| co_20 | contractor | 0.85 | None | 'Blue Ridge Concrete Works' |  |
| co_20 | reason | 0.85 | None | 'Owner-requested scope change' |  |
| co_20 | subtotal | 0.85 | None | 14500.91 |  |
| co_20 | status | 0.85 | None | 'Executed' |  |
| co_20 | signed | 0.85 | None | True |  |
| co_16 | owner | 0.784 | 'Westfield a Partners' | 'Westfield Capital Partners' |  |
| co_15 | total | 0.722 | None | 29338.66 | required_missing |
| co_20 | total | 0.722 | None | 16676.05 | required_missing |
| co_16 | item.description | 0.533 | 'Credit: omit decorative wall: trim' | 'Credit: omit decorative wall trim' | value_spans_lines, low_ocr_confidence |
| co_13 | status | 0.45 | 'Pending - need your sign-off to proceed.' | 'Pending' | passes_disagree |
| co_19 | reason | 0.45 | "Owner-requested scope change. At the owner's request, additional scope was add... | 'Owner-requested scope change' | passes_disagree |
| co_19 | description | 0.45 | 'Maple Ridge Elementary Gym Addition' | "At the owner's request, additional scope was added. Work covers rebar, #5 grad... | passes_disagree |
| co_01 | reason | 0.425 | None | 'Code compliance requirement' | possible_missed_field |
| co_03 | reason | 0.425 | None | 'Design error / RFI response' | possible_missed_field |
| co_06 | reason | 0.425 | None | 'Owner-requested scope change' | possible_missed_field |
| co_07 | reason | 0.425 | None | 'Unforeseen site condition' | possible_missed_field |
| co_11 | description | 0.425 | None | 'The parties agreed to the following value-engineering changes. Work covers exc... | possible_missed_field |
| co_14 | co_date | 0.425 | None | '2025-08-30' | possible_missed_field |
| co_17 | reason | 0.425 | None | 'Owner-requested scope change' | possible_missed_field |
| co_19 | owner | 0.425 | None | 'City of Riverside' | possible_missed_field |
| co_20 | markup_amount | 0.425 | None | 2175.14 | possible_missed_field |
| co_20 | schedule_impact_days | 0.425 | None | 10 | possible_missed_field |
| co_20 | original_contract_sum | 0.425 | None | 4852000.0 | possible_missed_field |
| co_02 | description | 0.405 | 'Upgrade light fixtures to LED and supervision labor' | 'The parties agreed to the following value-engineering changes. Work covers upg... | value_spans_lines, passes_disagree |
| co_14 | description | 0.382 | None | 'This change responds to a design clarification. Work covers replace supply duc... | passes_disagree |
| co_14 | item.unit | 0.382 | None | 'LB' | passes_disagree, item_missing_in_other_pass |
| co_14 | item.unit_price | 0.382 | None | 0.94 | passes_disagree, item_missing_in_other_pass |
| co_15 | item.quantity | 0.382 | None | 23.0 | passes_disagree, item_missing_in_other_pass |
| co_15 | item.unit | 0.382 | None | 'HR' | passes_disagree, item_missing_in_other_pass |
| co_15 | item.unit_price | 0.382 | None | 70.35 | passes_disagree, item_missing_in_other_pass |
| co_15 | item.quantity | 0.382 | None | 38.0 | passes_disagree |
| co_15 | item.unit | 0.382 | None | 'EA' | passes_disagree |
| co_15 | item.unit_price | 0.382 | None | 182.09 | passes_disagree |
| co_20 | co_date | 0.382 | None | '2026-05-04' | passes_disagree |
| co_20 | description | 0.382 | None | "At the owner's request, additional scope was added. Work covers excavation for... | passes_disagree |
| co_20 | item.quantity | 0.382 | None | 39.0 | passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.382 | None | 'CY' | passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.382 | None | 'EA' | passes_disagree, item_missing_in_other_pass |
| co_20 | item.quantity | 0.382 | None | 15.0 | passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.382 | None | 'EA' | passes_disagree, item_missing_in_other_pass |
| co_20 | item.quantity | 0.382 | None | 3223.0 | passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.382 | None | 'LB' | passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.382 | None | 1.02 | passes_disagree, item_missing_in_other_pass |
| co_20 | item.quantity | 0.382 | None | 6.0 | passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.382 | None | 'EA' | passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.382 | None | 784.39 | passes_disagree, item_missing_in_other_pass |
| co_15 | co_number | 0.361 | None | '034' | possible_missed_field, required_missing |
| co_18 | total | 0.361 | None | 15488.41 | possible_missed_field, required_missing |
| co_20 | co_number | 0.361 | None | 'PCO-39' | possible_missed_field, required_missing |
| co_07 | item.description | 0.3 | 'Drywall patch ...' | 'Drywall patch and finish - Level 2, Zone B' | value_not_in_evidence |
| co_14 | item.description | 0.295 | 'Additional 4" concrete slab pour Nicaea' | 'Additional 4" concrete slab pour' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | project_name | 0.259 | '. Oaks Sar vg Wn 8' | 'Oakwood Senior Living Wing B' | low_ocr_confidence, passes_disagree |
| co_20 | item.description | 0.238 | 'Overhead & Profit (15%)' | 'Credit: delete interior doors' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.amount | 0.238 | 2175.14 | -4706.34 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_14 | item.description | 0.227 | 'supply duct section' | 'Replace supply duct section' | value_spans_lines, low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_10 | signed | 0.225 | False | None | evidence_missing, passes_disagree |
| co_20 | item.description | 0.212 | 'Frame adctional interior partion eee, WEL' | 'Excavation for unforeseen rock' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.212 | 29.66 | 133.93 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.amount | 0.212 | 5398.12 | 5223.27 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.description | 0.202 | 'Credit: delete interior doors ee (BS Meese' | 'Rebar, #5 grade 60' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.amount | 0.202 | -4706.34 | 3287.46 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_15 | contractor | 0.196 | 'Beghting Construction' | 'Brightline Construction Inc.' | low_ocr_confidence, passes_disagree |
| co_02 | currency | 0.191 | None | 'USD' | possible_missed_field, passes_disagree |
| co_04 | description | 0.191 | None | 'The inspector required changes for code compliance. Work covers credit: omit d... | possible_missed_field, passes_disagree |
| co_04 | currency | 0.191 | None | 'USD' | possible_missed_field, passes_disagree |
| co_10 | description | 0.191 | None | 'This change responds to a design clarification. Work covers upgrade light fixt... | possible_missed_field, passes_disagree |
| co_20 | item.description | 0.184 | 'Relocate 20A electrical circuits' | 'Frame additional interior partition' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.quantity | 0.184 | 10.0 | 182.0 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit | 0.184 | 'EA' | 'LF' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.184 | 219.13 | 29.66 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.amount | 0.184 | 2191.3 | 5398.12 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_05 | total | 0.163 | None | 46377.95 | possible_missed_field, passes_disagree, required_missing |
| co_07 | item.description | 0.15 | 'Upgrade ...' | 'Upgrade light fixtures to LED - Level 5, Zone B' | evidence_absent |
| co_09 | item.description | 0.135 | 'Rebar, #5 grade 60 - Level 4, Zone D' | 'Rebar, #5 grade 60 - Level 3, Zone D' | value_not_in_evidence, passes_disagree |
| co_12 | description | 0.135 | 'Upgrade light fixtures to LED and sprinkler head relocation. Interior paint, t... | 'The parties agreed to the following value-engineering changes. Work covers upg... | value_not_in_evidence, passes_disagree |
| co_20 | item.description | 0.115 | 'Sprinkier head relocation' | 'Relocate 20A electrical circuits' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_15 | original_contract_sum | 0.09 | 8107800.0 | 3107500.0 | low_ocr_confidence, passes_disagree |
| co_20 | item.description | 0.09 | 'Rebarsgrade6O' | 'Sprinkler head relocation' | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.09 | 102.0 | 207.14 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.amount | 0.09 | 9287.46 | 3107.1 | low_ocr_confidence, passes_disagree, item_missing_in_other_pass |
| co_20 | item.quantity | 0.063 | 18.0 | 10.0 | low_ocr_confidence, passes_disagree, qty_price_mismatch, item_missing_in_other_pass |
| co_20 | item.unit_price | 0.063 | 2074.0 | 219.13 | low_ocr_confidence, passes_disagree, qty_price_mismatch, item_missing_in_other_pass |
| co_20 | item.amount | 0.063 | 3107.1 | 2191.3 | low_ocr_confidence, passes_disagree, qty_price_mismatch, item_missing_in_other_pass |