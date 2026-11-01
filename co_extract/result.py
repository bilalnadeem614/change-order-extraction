"""The pipeline's final, per-field-scored output."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .schema import SCALAR_FIELDS, ChangeOrder, LineItem


class ScoredField(BaseModel):
    value: Any = None
    confidence: float = Field(ge=0, le=1)
    evidence: Optional[str] = None
    flags: List[str] = Field(default_factory=list)


class ScoredLineItem(BaseModel):
    description: ScoredField
    quantity: ScoredField
    unit: ScoredField
    unit_price: ScoredField
    amount: ScoredField
    evidence: Optional[str] = None
    confidence: float = Field(ge=0, le=1)          # weakest sub-field


class IssueOut(BaseModel):
    code: str
    severity: str
    fields: List[str]
    message: str


class PipelineResult(BaseModel):
    source: str
    model: str
    passes: int
    fields: Dict[str, ScoredField]
    line_items: List[ScoredLineItem]
    issues: List[IssueOut]
    needs_review: bool
    review_reasons: List[str] = Field(default_factory=list)
    ingest: Dict[str, Any] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)

    def to_change_order(self) -> ChangeOrder:
        vals = {f: self.fields[f].value for f in SCALAR_FIELDS}
        if isinstance(vals.get("co_date"), str):
            vals["co_date"] = dt.date.fromisoformat(vals["co_date"])
        items = [LineItem(description=li.description.value, quantity=li.quantity.value, unit=li.unit.value,
                          unit_price=li.unit_price.value, amount=li.amount.value) for li in self.line_items]
        return ChangeOrder(**vals, line_items=items)
