"""Behavioural tests for validation + confidence. Each injects one specific mistake into an
otherwise-correct (gold replay) answer and checks the pipeline reacts the way the design says.

No API key needed. These test the scoring logic, not any model's accuracy."""
import json
from pathlib import Path

import pytest

from co_extract.extract import extract, to_change_order
from co_extract.grounding import (date_candidates, evidence_status, is_ambiguous_date, ocr_conf_for_evidence,
                                  value_in_evidence)
from co_extract.ingest import ingest
from co_extract.llm import LLMError, MockClient
from co_extract.pipeline import run_pipeline
from co_extract.schema import ChangeOrder
from co_extract.validate import validate

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "data" / "manifest.json").read_text())
TEXT_DOCS = [m for m in MANIFEST if m["has_text_layer"]]
FILES = {m["id"]: ROOT / "data" / m["file"] for m in MANIFEST}


class Tamper(MockClient):
    """Gold replay, with `fn(out, temperature)` free to damage the answer."""

    def __init__(self, doc_id, fn=None):
        super().__init__(ROOT / "data" / "gold" / f"{doc_id}.json")
        self.fn = fn

    def extract(self, system, document, schema, temperature=0.0):
        out = super().extract(system, document, schema, temperature)
        if self.fn:
            self.fn(out, temperature)
        return out


def run(doc_id, fn=None, passes=2):
    return run_pipeline(FILES[doc_id], Tamper(doc_id, fn), passes=passes)


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("m", TEXT_DOCS, ids=[m["id"] for m in TEXT_DOCS])
def test_no_false_alarms_on_correct_answers(m):
    r = run(m["id"])
    errors = [i.code for i in r.issues if i.severity == "error"]
    if m["id"] == "co_18":
        assert set(errors) == {"total_mismatch", "contract_sum_mismatch"}   # the document's own mistake
    else:
        assert errors == []
    assert r.needs_review == (m["id"] in ("co_18", "co_06")), r.review_reasons


def test_wrong_total_is_flagged_not_repaired():
    r = run("co_18")
    gold = ChangeOrder.model_validate_json((ROOT / "data/gold/co_18.json").read_text())
    assert r.fields["total"].value == gold.total          # the printed (wrong) value is kept
    assert r.fields["total"].confidence < 0.5
    assert "total_mismatch" in r.fields["total"].flags


def test_sign_vs_description_warning():
    def positive_credit(out, t):
        for li in out["line_items"]:
            if li["description"].startswith("Credit"):
                li["amount"] = abs(li["amount"])
    r = run("co_03", positive_credit)
    assert any(i.code == "sign_vs_description" for i in r.issues)


# --------------------------------------------------------------------------- #
# confidence: each signal on its own
# --------------------------------------------------------------------------- #
def test_clean_document_is_confident():
    r = run("co_02")
    for f in ("co_number", "total", "subtotal", "markup_amount", "new_contract_sum", "owner"):
        assert r.fields[f].confidence >= 0.95, (f, r.fields[f])
    assert all(li.confidence >= 0.95 for li in r.line_items)
    assert not r.needs_review


def test_misread_value_with_original_quote_is_caught():
    """Model quotes the right line but reports a different number: value-not-in-evidence."""
    def misread(out, t):
        out["line_items"][1]["amount"] = out["line_items"][1]["amount"] + 100.0
    r = run("co_02", misread, passes=1)
    it = r.line_items[1].amount
    assert "value_not_in_evidence" in it.flags and it.confidence < 0.5
    assert r.needs_review


def test_consistent_lie_is_caught_by_arithmetic_only():
    """Value AND quote both changed: grounding cannot see it, the arithmetic can."""
    def lie(out, t):
        old = out["total"]["value"]
        out["total"]["value"] = old + 500.0
        out["total"]["evidence"] = out["total"]["evidence"].replace(f"{old:,.2f}", f"{old + 500:,.2f}")
    r = run("co_02", lie, passes=1)
    tot = r.fields["total"]
    assert "value_not_in_evidence" not in tot.flags          # grounding is fooled...
    assert "total_mismatch" in tot.flags and tot.confidence < 0.7   # ...arithmetic is not


def test_invented_quote_is_nearly_worthless():
    def invent(out, t):
        out["owner"]["evidence"] = "Owner: The Acme Corporation of Nowhere"
    r = run("co_01", invent, passes=1)
    assert "evidence_absent" in r.fields["owner"].flags and r.fields["owner"].confidence <= 0.15


def test_passes_disagreeing_lowers_confidence():
    def second_pass_differs(out, t):
        if t > 0:
            out["status"]["value"] = "Executed" if out["status"]["value"] != "Executed" else "Pending"
    r = run("co_02", second_pass_differs)
    assert "passes_disagree" in r.fields["status"].flags
    assert r.fields["status"].confidence < 0.6
    assert r.fields["total"].confidence >= 0.95               # untouched fields keep their score


def test_dropped_field_the_text_mentions_is_flagged():
    def drop(out, t):
        out["schedule_impact_days"] = {"value": None, "evidence": None}
    r = run("co_01", drop, passes=1)
    f = r.fields["schedule_impact_days"]
    assert "possible_missed_field" in f.flags and f.confidence < 0.5


def test_genuinely_absent_field_is_not_penalised():
    r = run("co_13")                      # contract sums + schedule are really not in this email
    for f in ("original_contract_sum", "new_contract_sum", "schedule_impact_days"):
        assert r.fields[f].value is None and r.fields[f].flags == [] and r.fields[f].confidence >= 0.8


def test_ambiguous_date_is_below_review_threshold():
    r = run("co_06")
    d = r.fields["co_date"]
    assert "ambiguous_date" in d.flags and d.confidence < 0.7 and r.needs_review


def test_dropped_line_item_shows_up_as_sum_mismatch():
    def drop_item(out, t):
        out["line_items"].pop(1)
    r = run("co_02", drop_item, passes=1)
    assert any(i.code == "items_sum_mismatch" for i in r.issues) and r.needs_review


def test_second_pass_failure_degrades_gracefully():
    class Dies(MockClient):
        def extract(self, system, document, schema, temperature=0.0):
            if temperature > 0:
                raise LLMError("rate limited")
            return super().extract(system, document, schema, temperature)
    r = run_pipeline(FILES["co_02"], Dies(ROOT / "data/gold/co_02.json"))
    assert r.passes == 1 and r.notes and not r.needs_review


# --------------------------------------------------------------------------- #
# grounding helpers
# --------------------------------------------------------------------------- #
def test_value_matching_handles_formats():
    assert value_in_evidence("total", 1234.5, "Total: $1,234.50")
    assert value_in_evidence("total", 1234.5, "Gesamt: 1.234,50 €")
    assert value_in_evidence("amount", -1200.0, "Credit ... (1,200.00)")
    assert not value_in_evidence("total", 11234.5, "Total: $1,234.50")      # no partial-number match
    assert value_in_evidence("currency", "EUR", "12,00 €")
    assert value_in_evidence("schedule_impact_days", 0, "Change in Contract Time: No change")
    assert value_in_evidence("markup_percent", 15.0, "Overhead & Profit (15%)")
    assert value_in_evidence("co_date", "2026-03-04", "Date: March 4, 2026")


def test_date_ambiguity_detection():
    assert is_ambiguous_date("Date: 04/03/2026")
    assert not is_ambiguous_date("Date: 25/03/2026")       # 25 cannot be a month
    assert not is_ambiguous_date("Date: 2026-03-04")
    assert not is_ambiguous_date("Date: 05/05/2026")       # same either way
    assert len(date_candidates("04/03/2026")[0]) == 2


def test_evidence_status_levels():
    text = "Project: Maple Ridge\nElementary Gym Owner: X\nAddition"
    assert evidence_status("Project: Maple Ridge", text) == "exact"
    assert evidence_status("Maple Ridge Elementary Gym Addition", text) == "fuzzy"   # interleaved wrap
    assert evidence_status("Totally invented", text) == "absent"
    assert evidence_status(None, text) == "missing"


@pytest.mark.slow
def test_ocr_confidence_only_exists_for_scans():
    scan = ingest(FILES["co_14"])
    assert ocr_conf_for_evidence("Subtotal $14,321.94", scan) is not None
    assert ocr_conf_for_evidence("Subtotal $14,321.94", ingest(FILES["co_01"])) is None


@pytest.mark.slow
def test_scan_pipeline_runs_and_second_pass_uses_alt_ocr():
    r = run("co_15")
    assert r.ingest["used_ocr"] and r.passes == 2
    assert any("low_ocr_confidence" in f.flags for f in r.fields.values())


def test_result_roundtrip_matches_gold():
    for m in TEXT_DOCS:
        r = run(m["id"])
        gold = ChangeOrder.model_validate_json((ROOT / "data" / "gold" / f"{m['id']}.json").read_text())
        assert r.to_change_order().model_dump() == gold.model_dump(), m["id"]
