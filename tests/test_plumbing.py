"""Plumbing tests - no API key needed.

These prove that ingest -> prompt -> parse -> map -> validate is wired correctly. They do NOT
measure extraction accuracy: the mock replays the answer key. Accuracy comes from the eval
step with a real model.
"""
import json
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from co_extract.extract import extract, to_change_order
from co_extract.grounding import evidence_status
from co_extract.ingest import ingest
from co_extract.llm import LLMError, MockClient, inline_refs
from co_extract.schema import SCALAR_FIELDS, ChangeOrder, ChangeOrderExtraction

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "data" / "manifest.json").read_text())
TEXT_DOCS = [m for m in MANIFEST if m["has_text_layer"]]


def gold(doc_id: str) -> ChangeOrder:
    return ChangeOrder.model_validate_json((ROOT / "data" / "gold" / f"{doc_id}.json").read_text())


def test_schema_is_flat_for_providers():
    flat = json.dumps(inline_refs(ChangeOrderExtraction.model_json_schema()))
    assert "$ref" not in flat and "$defs" not in flat
    for f in SCALAR_FIELDS:
        assert f in flat


@pytest.mark.parametrize("m", TEXT_DOCS, ids=[m["id"] for m in TEXT_DOCS])
def test_mock_roundtrip_returns_gold(m):
    doc = ingest(ROOT / "data" / m["file"])
    ex = extract(doc.text, MockClient(ROOT / "data" / "gold" / f"{m['id']}.json"))
    assert to_change_order(ex).model_dump() == gold(m["id"]).model_dump()


@pytest.mark.parametrize("m", TEXT_DOCS, ids=[m["id"] for m in TEXT_DOCS])
def test_evidence_comes_from_the_document(m):
    """Evidence the mock attaches must be copied from the text it was given."""
    doc = ingest(ROOT / "data" / m["file"])
    ex = extract(doc.text, MockClient(ROOT / "data" / "gold" / f"{m['id']}.json"))
    for f in SCALAR_FIELDS:
        e = getattr(ex, f).evidence
        if e:   # exact, or fuzzy when the value wraps across lines
            assert evidence_status(e, doc.text) in ("exact", "fuzzy"), f


def test_only_the_wrong_total_document_is_flagged():
    flagged = {m["id"] for m in MANIFEST if gold(m["id"]).consistency_issues()}
    assert flagged == {m["id"] for m in MANIFEST if m["expect_inconsistent"]} == {"co_18"}


def test_ingest_picks_the_right_method():
    assert ingest(ROOT / "data/raw/co_01_clean_form.pdf").pages[0].method == "text_layer"
    assert ingest(ROOT / "data/raw/co_10_email.txt").pages[0].method == "plain"
    multi = ingest(ROOT / "data/raw/co_07_multipage.pdf")
    assert len(multi.pages) == 2 and "=== PAGE 2 ===" in multi.text


@pytest.mark.slow
def test_scan_goes_through_ocr_with_word_confidences():
    r = ingest(ROOT / "data/raw/co_14_scan_good.pdf")
    assert r.used_ocr and r.pages[0].words and r.mean_ocr_conf > 50
    assert "CHANGE ORDER" in r.text.upper()


class _FlakyClient:
    """Returns an invalid answer first, then a valid one."""
    name = "flaky"

    def __init__(self, good: dict, fail_times: int):
        self.good, self.fail_times, self.calls = good, fail_times, 0

    def extract(self, system, document, schema, temperature=0.0):
        self.calls += 1
        return {"co_number": "oops"} if self.calls <= self.fail_times else self.good


def test_retry_then_success_and_exhaustion():
    mock = MockClient(ROOT / "data/gold/co_01.json")
    text = ingest(ROOT / "data/raw/co_01_clean_form.pdf").text
    good = mock.extract("", text, {})

    c = _FlakyClient(good, fail_times=1)
    extract(text, c, max_retries=1)
    assert c.calls == 2

    c = _FlakyClient(good, fail_times=5)
    with pytest.raises(ValidationError):
        extract(text, c, max_retries=1)
    assert c.calls == 2


def test_mock_requires_gold():
    from co_extract.cli import main
    assert main([str(ROOT / "data/raw/co_01_clean_form.pdf"), "--provider", "mock"]) == 2
