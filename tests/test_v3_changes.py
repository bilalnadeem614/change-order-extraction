"""Tests for: null-on-OCR penalty, required_missing prior, status normalisation, dropped-sentence check."""
import pytest

from co_extract.grounding import drops_sentence
from co_extract.normalize import clean_status
from test_validate_confidence import run


def _null(*fields):
    def fn(out, t):
        for f in fields:
            out[f] = {"value": None, "evidence": None}
    return fn


@pytest.mark.slow
def test_null_on_scan_is_flagged_and_below_threshold():
    r = run("co_15", _null("project_name"), passes=1)
    f = r.fields["project_name"]
    assert "null_on_ocr_text" in f.flags and f.confidence < 0.7


def test_null_on_text_document_stays_unpenalised():
    r = run("co_13")                       # test_genuinely_absent covers this too; here we check the flag
    assert all("null_on_ocr_text" not in f.flags for f in r.fields.values())
    assert r.fields["schedule_impact_days"].confidence >= 0.8


def test_missing_total_and_co_number_never_pass():
    r = run("co_01", _null("total", "co_number"), passes=1)
    for f in ("total", "co_number"):
        assert "required_missing" in r.fields[f].flags and r.fields[f].confidence < 0.7


@pytest.mark.parametrize("raw,want", [
    ("Executed - need your sign-off to proceed.", "Executed"),
    ("Approved – pending", "Approved"),
    ("Pending; awaiting owner", "Pending"),
    ("Approved (as noted)", "Approved"),
    ("Executed.", "Executed"),
    ("Pending", "Pending"),
    ("Change-order approved", "Change-order approved"),     # hyphen without spaces is kept
    (None, None),
])
def test_clean_status(raw, want):
    assert clean_status(raw) == want


def test_status_normalised_on_every_pass_evidence_untouched():
    def noisy(out, t):
        out["status"] = {"value": "Executed - need your sign-off to proceed.",
                         "evidence": out["status"]["evidence"]}
    r = run("co_01", noisy)                # 2 passes: both must normalise or they would disagree
    s = r.fields["status"]
    assert s.value == "Executed" and "passes_disagree" not in s.flags


SCOPE = "Scope: The parties agreed to the following value-engineering changes. Work covers upgrade light fixtures to LED."


def test_drops_sentence_catches_co13_pattern():
    assert drops_sentence("description", "Upgrade light fixtures to LED", SCOPE)
    full = "The parties agreed to the following value-engineering changes. Work covers upgrade light fixtures to LED."
    assert not drops_sentence("description", full, SCOPE)                       # label prefix is fine
    assert not drops_sentence("description", "Same text.", "Description of Change\nSame text.")
    assert not drops_sentence("reason", "LED", SCOPE)                           # prose fields only


def test_dropped_sentence_description_is_below_threshold():
    def trunc(out, t):
        out["description"]["value"] = "Upgrade light fixtures to LED and waterproofing membrane"
    r = run("co_13", trunc, passes=1)
    d = r.fields["description"]
    assert "value_drops_sentence" in d.flags and d.confidence < 0.7


def test_correct_descriptions_not_flagged():
    for doc in ("co_01", "co_05", "co_12", "co_13"):
        assert "value_drops_sentence" not in run(doc, passes=1).fields["description"].flags
