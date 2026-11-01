"""Stage 3 - deterministic checks on the extracted values. No model involved.

Each Issue names the fields it implicates. An arithmetic mismatch cannot say WHICH number is
wrong (a misread digit, or an error printed in the document itself), so every field that takes
part in the failed equation is implicated and the confidence stage lowers all of them.

The validator reports; it never repairs. A document whose printed total is wrong should come
out with the printed total and a flag, not a silently "corrected" number.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .grounding import is_ambiguous_date
from .schema import ChangeOrder, ChangeOrderExtraction

TOL = 0.011
CREDIT_WORDS = re.compile(r"\b(credit|deduct\w*|omit\w*|delete\w*|eliminat\w*|remov\w*|reduc\w*)\b", re.I)


@dataclass
class Issue:
    code: str
    severity: str                 # "error" | "warn"
    fields: Tuple[str, ...]       # "total", "line_items[2]", ...
    message: str


def validate(co: ChangeOrder, ex: Optional[ChangeOrderExtraction] = None) -> List[Issue]:
    issues: List[Issue] = []
    add = lambda code, sev, fields, msg: issues.append(Issue(code, sev, tuple(fields), msg))

    # ---- arithmetic (errors) ------------------------------------------------
    if co.line_items and co.subtotal is not None:
        s = round(sum(li.amount for li in co.line_items), 2)
        if abs(s - co.subtotal) > TOL:
            add("items_sum_mismatch", "error",
                ["subtotal"] + [f"line_items[{i}]" for i in range(len(co.line_items))],
                f"line items sum to {s} but subtotal is {co.subtotal}")

    for i, li in enumerate(co.line_items):
        if li.quantity is not None and li.unit_price is not None:
            calc = round(li.quantity * li.unit_price, 2)
            if abs(abs(calc) - abs(li.amount)) > TOL:
                add("qty_price_mismatch", "error", [f"line_items[{i}]"],
                    f"item {i + 1}: {li.quantity} x {li.unit_price} = {calc}, but amount is {li.amount}")

    if co.subtotal is not None and co.total is not None:
        markup = co.markup_amount or 0.0
        if abs(co.subtotal + markup - co.total) > TOL:
            add("total_mismatch", "error", ["subtotal", "markup_amount", "total"],
                f"subtotal {co.subtotal} + markup {markup} = {round(co.subtotal + markup, 2)}, but total is {co.total}")

    if None not in (co.subtotal, co.markup_percent, co.markup_amount):
        calc = round(co.subtotal * co.markup_percent / 100, 2)
        if abs(calc - co.markup_amount) > 0.02:
            add("markup_mismatch", "error", ["subtotal", "markup_percent", "markup_amount"],
                f"{co.markup_percent}% of {co.subtotal} is {calc}, but markup is {co.markup_amount}")

    if None not in (co.original_contract_sum, co.total, co.new_contract_sum):
        if abs(co.original_contract_sum + co.total - co.new_contract_sum) > TOL:
            add("contract_sum_mismatch", "error", ["original_contract_sum", "total", "new_contract_sum"],
                f"original {co.original_contract_sum} + total {co.total} != new {co.new_contract_sum}")

    # ---- plausibility (warnings) --------------------------------------------
    if not co.line_items:
        add("no_line_items", "warn", ["line_items"], "no line items were extracted")
    for f in ("co_number", "total"):
        if getattr(co, f) is None:
            add("required_missing", "warn", [f], f"{f} is missing")

    if co.co_date and not (2000 <= co.co_date.year <= 2035):
        add("date_out_of_range", "warn", ["co_date"], f"implausible year {co.co_date.year}")
    if ex is not None and is_ambiguous_date(ex.co_date.evidence):
        add("ambiguous_date", "warn", ["co_date"],
            f"'{ex.co_date.evidence}' could be month/day or day/month; read as month first")

    if co.markup_percent is not None and not (0 <= co.markup_percent <= 100):
        add("percent_out_of_range", "warn", ["markup_percent"], f"markup {co.markup_percent}% is implausible")
    if co.schedule_impact_days is not None and abs(co.schedule_impact_days) > 365:
        add("schedule_out_of_range", "warn", ["schedule_impact_days"], f"{co.schedule_impact_days} days is implausible")

    for i, li in enumerate(co.line_items):
        if li.amount > 0 and CREDIT_WORDS.search(li.description):
            add("sign_vs_description", "warn", [f"line_items[{i}]"],
                f"item {i + 1} reads like a credit but the amount is positive")

    if ex is not None and co.currency:
        quotes = " ".join(filter(None, [ex.total.evidence, ex.subtotal.evidence]))
        if ("€" in quotes and co.currency.upper() != "EUR") or ("$" in quotes and co.currency.upper() not in ("USD", "CAD", "AUD")):
            add("currency_mismatch", "warn", ["currency"], f"currency {co.currency} vs symbol in '{quotes[:40]}'")
    return issues
