"""Schema for change-order extraction.

Two layers:

* ``ChangeOrder`` / ``LineItem``      - plain validated values. The gold files and the
                                        pipeline's final output both use this shape.
* ``ChangeOrderExtraction``           - the shape the LLM is asked to fill: every field is
                                        a value plus the verbatim evidence quote it came from.
                                        Confidence is NOT asked from the LLM; the pipeline
                                        computes it (see the confidence step).

Conventions
-----------
* Money is a float rounded to 2 dp. Credits / deducts are NEGATIVE.
* Dates are ISO (YYYY-MM-DD) once parsed.
* A field that is not in the document is ``None`` (never guessed).
* Values are what the document STATES, even when the document is internally
  inconsistent. Inconsistencies are surfaced by ``consistency_issues`` instead of
  being silently "fixed".
"""
from __future__ import annotations

import datetime as dt
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

TOLERANCE = 0.011  # money comparisons: one cent of rounding slack


# --------------------------------------------------------------------------- #
# Final / gold shape
# --------------------------------------------------------------------------- #
class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None          # SF, EA, LF, HR, ...
    unit_price: Optional[float] = None
    amount: float                       # negative for credits


class ChangeOrder(BaseModel):
    co_number: Optional[str] = None     # identifier exactly as printed, e.g. "CO-007"
    co_date: Optional[dt.date] = None
    project_name: Optional[str] = None
    owner: Optional[str] = None
    contractor: Optional[str] = None
    reason: Optional[str] = None
    description: Optional[str] = None

    line_items: List[LineItem] = Field(default_factory=list)

    subtotal: Optional[float] = None
    markup_percent: Optional[float] = None   # 10 means 10%
    markup_amount: Optional[float] = None
    total: Optional[float] = None            # net change; negative for a deductive CO
    currency: Optional[str] = None           # ISO code, e.g. "USD"

    schedule_impact_days: Optional[int] = None   # negative = schedule shortened
    original_contract_sum: Optional[float] = None
    new_contract_sum: Optional[float] = None

    status: Optional[str] = None             # Pending / Approved / Executed ...
    signed: Optional[bool] = None            # True only if the OWNER's signature is visible;
                                             # None when the format has no signature block (email)

    def consistency_issues(self) -> List[str]:
        """Deterministic arithmetic checks. Only runs a check when its inputs exist.

        Reused by the validation stage and by the dataset verifier.
        """
        issues: List[str] = []

        if self.line_items and self.subtotal is not None:
            s = round(sum(li.amount for li in self.line_items), 2)
            if abs(s - self.subtotal) > TOLERANCE:
                issues.append(f"line items sum {s} != subtotal {self.subtotal}")

        for li in self.line_items:
            if li.quantity is not None and li.unit_price is not None:
                calc = round(li.quantity * li.unit_price, 2)
                if abs(abs(calc) - abs(li.amount)) > TOLERANCE:
                    issues.append(
                        f"line '{li.description[:30]}': qty*price {calc} != amount {li.amount}"
                    )

        if self.subtotal is not None and self.markup_amount is not None and self.total is not None:
            if abs(self.subtotal + self.markup_amount - self.total) > TOLERANCE:
                issues.append(
                    f"subtotal {self.subtotal} + markup {self.markup_amount} != total {self.total}"
                )
        elif self.subtotal is not None and self.markup_amount is None and self.total is not None:
            if abs(self.subtotal - self.total) > TOLERANCE:
                issues.append(f"no markup but subtotal {self.subtotal} != total {self.total}")

        if self.subtotal is not None and self.markup_percent is not None and self.markup_amount is not None:
            calc = round(self.subtotal * self.markup_percent / 100, 2)
            if abs(calc - self.markup_amount) > 0.02:
                issues.append(f"markup {self.markup_percent}% of {self.subtotal} = {calc} != {self.markup_amount}")

        if None not in (self.original_contract_sum, self.total, self.new_contract_sum):
            if abs(self.original_contract_sum + self.total - self.new_contract_sum) > TOLERANCE:
                issues.append(
                    f"original {self.original_contract_sum} + total {self.total} != new {self.new_contract_sum}"
                )
        return issues


# --------------------------------------------------------------------------- #
# LLM-facing shape: value + verbatim evidence for every field
# --------------------------------------------------------------------------- #
class Extracted(BaseModel, Generic[T]):
    value: Optional[T] = None
    evidence: Optional[str] = Field(
        default=None,
        description="Exact text copied from the document that supports the value. "
        "Null if the value is absent from the document.",
    )


class LineItemExtraction(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    amount: float = Field(description="Negative for credits / deducts")
    evidence: Optional[str] = Field(
        default=None, description="The exact line (or row text) this item was read from."
    )


class ChangeOrderExtraction(BaseModel):
    co_number: Extracted[str] = Field(default_factory=Extracted)
    co_date: Extracted[dt.date] = Field(default_factory=Extracted)
    project_name: Extracted[str] = Field(default_factory=Extracted)
    owner: Extracted[str] = Field(default_factory=Extracted)
    contractor: Extracted[str] = Field(default_factory=Extracted)
    reason: Extracted[str] = Field(default_factory=Extracted)
    description: Extracted[str] = Field(default_factory=Extracted)

    line_items: List[LineItemExtraction] = Field(default_factory=list)

    subtotal: Extracted[float] = Field(default_factory=Extracted)
    markup_percent: Extracted[float] = Field(default_factory=Extracted)
    markup_amount: Extracted[float] = Field(default_factory=Extracted)
    total: Extracted[float] = Field(default_factory=Extracted)
    currency: Extracted[str] = Field(default_factory=Extracted)

    schedule_impact_days: Extracted[int] = Field(default_factory=Extracted)
    original_contract_sum: Extracted[float] = Field(default_factory=Extracted)
    new_contract_sum: Extracted[float] = Field(default_factory=Extracted)

    status: Extracted[str] = Field(default_factory=Extracted)
    signed: Extracted[bool] = Field(default_factory=Extracted)


# Scalar field names, in output order. Used for per-field scoring and evaluation.
SCALAR_FIELDS = [
    "co_number", "co_date", "project_name", "owner", "contractor", "reason",
    "description", "subtotal", "markup_percent", "markup_amount", "total",
    "currency", "schedule_impact_days", "original_contract_sum",
    "new_contract_sum", "status", "signed",
]
