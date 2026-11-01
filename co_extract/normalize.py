"""Post-extraction clean-up that is applied identically to every pass, before scoring."""
from __future__ import annotations

import re
from typing import Optional

from .schema import ChangeOrderExtraction

_STATUS_CUT = re.compile(r" - | – |;|:|,|\(")


def clean_status(value: Optional[str]) -> Optional[str]:
    """'Executed - need your sign-off to proceed.' -> 'Executed' (the schema wants the status word)."""
    if value is None:
        return None
    return _STATUS_CUT.split(value, maxsplit=1)[0].strip(" .").strip() or None


def normalize_extraction(ex: ChangeOrderExtraction) -> ChangeOrderExtraction:
    """Normalise values in place (evidence stays untouched, so grounding still sees the quote)."""
    ex.status.value = clean_status(ex.status.value)
    return ex
