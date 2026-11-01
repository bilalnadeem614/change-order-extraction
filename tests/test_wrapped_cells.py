"""Wrapped table cells and wrapped form cells.

Found in the first real Groq run: `project_name` and multipage `item.description` were wrong
at confidence 1.0, because a cell that wrapped onto a second line was cut in two by the plain
text read, and the model's (correct) quote of the first line made the value look grounded.
"""
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from co_extract.confidence import PassResult
from co_extract.extract import extract
from co_extract.grounding import may_continue_on_next_line
from co_extract.ingest import ingest
from co_extract.llm import MockClient
from co_extract.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "data" / "manifest.json").read_text())
TEXT_PDFS = [m for m in MANIFEST if m["has_text_layer"] and m["file"].endswith(".pdf")]


def norm(s):
    return re.sub(r"\s+", " ", s).strip().casefold()


@pytest.mark.parametrize("m", TEXT_PDFS, ids=[m["id"] for m in TEXT_PDFS])
def test_every_gold_text_value_is_whole_on_one_line(m):
    """After ingest, no project name / owner / reason / item description is split across lines."""
    gold = json.loads((ROOT / "data" / "gold" / f"{m['id']}.json").read_text())
    lines = [norm(l) for l in ingest(ROOT / "data" / m["file"]).text.splitlines()]
    values = [li["description"] for li in gold["line_items"]] + [
        gold[f] for f in ("project_name", "owner", "reason") if gold[f]]
    for v in values:
        assert any(norm(v) in l for l in lines), f"split across lines: {v!r}"


def test_wrapped_table_cell_is_rejoined():
    text = ingest(ROOT / "data/raw/co_07_multipage.pdf").text
    assert "| Excavation for unforeseen rock - Level 4, Zone A |" in text
    assert text.count("\n") > 30 and "=== PAGE 2 ===" in text


def test_wrapped_header_cell_is_rejoined_without_losing_its_neighbour():
    text = ingest(ROOT / "data/raw/co_01_clean_form.pdf").text
    assert "Project: Maple Ridge Elementary Gym Addition Owner: Pinecrest Development Corp." in text


def test_bold_labels_and_headings_are_not_glued_to_values():
    """'Owner' / 'signature:' (a wrapped bold label) and 'Description of Change' must stay put."""
    r = ingest(ROOT / "data/raw/co_01_clean_form.pdf")
    assert "Description of Change" in r.text.splitlines()
    assert not any("Pending Owner" in l or "Executed Owner" in l or "Approved Owner" in l for l in r.text.splitlines())
    assert r.orphans == []


def test_gold_replay_is_still_fully_confident_on_wrapped_documents():
    for doc in ("co_01", "co_06", "co_07", "co_08", "co_09"):
        m = next(x for x in MANIFEST if x["id"] == doc)
        r = run_pipeline(ROOT / "data" / m["file"], MockClient(ROOT / "data" / "gold" / f"{doc}.json"))
        assert r.fields["project_name"].confidence >= 0.85, doc
        assert all(li.description.confidence >= 0.85 for li in r.line_items), doc


# --- the safety net: a tail ingest could NOT attach must make the value above it suspect -------------
TEXT = "Project: Maple Ridge Elementary Gym Owner: Pinecrest Corp.\nAddition\nContractor: Atlas"


def test_unattached_tail_flags_values_on_the_line_above():
    ev = "Project: Maple Ridge Elementary Gym Owner: Pinecrest Corp."
    assert may_continue_on_next_line("Maple Ridge Elementary Gym", ev, TEXT, ["Addition"])
    assert may_continue_on_next_line("Pinecrest Corp.", ev, TEXT, ["Addition"])   # known: cannot tell which cell
    assert not may_continue_on_next_line("Atlas", "Contractor: Atlas", TEXT, ["Addition"])
    assert not may_continue_on_next_line("Maple Ridge Elementary Gym", ev, TEXT, [])   # nothing orphaned


def test_unattached_tail_lowers_confidence_end_to_end():
    class Truncating(MockClient):
        def extract(self, system, document, schema, temperature=0.0):
            out = super().extract(system, document, schema, temperature)
            out["project_name"] = {"value": "Maple Ridge Elementary Gym",
                                   "evidence": "Project: Maple Ridge Elementary Gym Owner: Pinecrest Development Corp."}
            return out

    from co_extract import confidence as C
    doc = ingest(ROOT / "data/raw/co_01_clean_form.pdf")
    doc.pages[0].orphans = ["Addition"]                      # pretend ingest could not attach it
    doc.pages[0].text = doc.pages[0].text.replace(
        "Maple Ridge Elementary Gym Addition Owner: Pinecrest Development Corp.",
        "Maple Ridge Elementary Gym Owner: Pinecrest Development Corp.\nAddition")
    ex = extract(doc.text, Truncating(ROOT / "data/gold/co_01.json"))
    f = C.score_scalars([PassResult(ex, doc.text)], doc, [])["project_name"]
    assert "may_be_truncated" in f.flags and f.confidence < 0.7
