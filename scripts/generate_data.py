"""Generate a synthetic change-order test set with gold JSON.

    python scripts/generate_data.py

Outputs (all deterministic, seeded):
    data/raw/<id>_<slug>.{pdf,txt}   the messy inputs
    data/gold/<id>.json              what the document STATES (see co_extract/schema.py)
    data/manifest.json               per-document format + difficulty tags

Design rules for the gold files
-------------------------------
* Every non-null gold value is actually printed in the document. If it is not printed
  it is null (we hide some fields on purpose to test "do not guess").
* Gold records what the document STATES, even when the document is wrong
  (``source_inconsistent`` doc): the extractor should report it and the validator should
  flag it, not silently repair it.
* Scans are real image-only PDFs (no text layer) so the OCR fallback is exercised.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from co_extract.schema import ChangeOrder, LineItem  # noqa: E402

RAW = ROOT / "data" / "raw"
GOLD = ROOT / "data" / "gold"
SEED = 20261031

# --------------------------------------------------------------------------- #
# Vocabulary (all fictional)
# --------------------------------------------------------------------------- #
PROJECTS = [
    "Harborview Medical Office Building", "Maple Ridge Elementary Gym Addition",
    "Cedar Point Apartments Phase 2", "Northgate Distribution Center",
    "Riverside Library Renovation", "Summit Peak Brewery Buildout",
    "Oakwood Senior Living Wing B", "Lakeshore Fire Station No. 7",
    "Pinecrest Retail Plaza", "Westfield Data Hall Fit-Out",
]
OWNERS = [
    "Harborview Health Partners", "Maple Ridge School District", "Cedar Point Holdings LLC",
    "Northgate Logistics Inc.", "City of Riverside", "Summit Peak Brewing Co.",
    "Oakwood Care Group", "Lakeshore Township", "Pinecrest Development Corp.",
    "Westfield Capital Partners",
]
CONTRACTORS = [
    "Ironclad Builders LLC", "Brightline Construction Inc.", "Keystone Mechanical Co.",
    "Redwood General Contractors", "Atlas Electric & Controls", "Blue Ridge Concrete Works",
]
PEOPLE = ["Dana Whitfield", "Marcus Ortega", "Priya Nambiar", "Tom Bellamy", "Ellen Frost", "Jorge Castillo"]

# (description, unit, (price lo, hi), (qty lo, hi))
ITEMS = [
    ("Additional 4\" concrete slab pour", "SF", (6, 12), (200, 1500)),
    ("Relocate 20A electrical circuits", "EA", (180, 450), (2, 20)),
    ("Rebar, #5 grade 60", "LB", (0.8, 1.6), (500, 4000)),
    ("Frame additional interior partition", "LF", (22, 48), (30, 200)),
    ("Drywall patch and finish", "SF", (3, 7), (100, 900)),
    ("Replace supply duct section", "LF", (35, 90), (20, 120)),
    ("Fire-rated door and hardware", "EA", (900, 2400), (1, 6)),
    ("Excavation for unforeseen rock", "CY", (65, 140), (20, 150)),
    ("Supervision labor", "HR", (55, 95), (8, 80)),
    ("Upgrade light fixtures to LED", "EA", (120, 320), (10, 80)),
    ("Waterproofing membrane", "SF", (4, 9), (300, 2000)),
    ("Sprinkler head relocation", "EA", (95, 210), (5, 40)),
    ("Interior paint, two coats", "SF", (1.2, 2.8), (500, 4000)),
    ("Crane rental", "DAY", (1400, 2600), (1, 4)),
]
CREDIT_ITEMS = [
    ("Credit: delete interior doors", "EA", (350, 900), (2, 8)),
    ("Credit: omit decorative wall trim", "LF", (6, 18), (60, 300)),
    ("Credit: substitute vinyl for tile flooring", "SF", (2, 5), (200, 1200)),
    ("Credit: eliminate planned landscaping", "LS", (1500, 6000), (1, 1)),
]
REASONS = {
    "Owner-requested scope change": "At the owner's request, additional scope was added.",
    "Unforeseen site condition": "Conditions found on site differ from the contract documents.",
    "Design error / RFI response": "This change responds to a design clarification.",
    "Code compliance requirement": "The inspector required changes for code compliance.",
    "Value engineering": "The parties agreed to the following value-engineering changes.",
}
STATUSES = ["Pending", "Approved", "Executed"]

LABELS = [
    {"co": "Change Order No.", "date": "Date", "project": "Project", "owner": "Owner",
     "contractor": "Contractor", "reason": "Reason for Change", "total": "TOTAL THIS CHANGE ORDER",
     "orig": "Original Contract Sum", "new": "Revised Contract Sum"},
    {"co": "CO #", "date": "Date Issued", "project": "Project Name", "owner": "Owner / Client",
     "contractor": "Contractor", "reason": "Reason", "total": "Net Change",
     "orig": "Contract Sum Prior to This CO", "new": "Contract Sum Including This CO"},
]

# --------------------------------------------------------------------------- #
# The 20 documents. Hard cases are tagged so the eval can report by tag.
# --------------------------------------------------------------------------- #
SPECS: List[dict] = [
    dict(id="co_01", slug="clean_form", kind="form_pdf", n_items=3, markup=10, date_style="long", tags=["baseline"]),
    dict(id="co_02", slug="clean_form", kind="form_pdf", n_items=5, markup=15, date_style="iso", tags=["baseline"]),
    dict(id="co_03", slug="credit_mixed", kind="form_pdf", n_items=4, markup=10, credit="mixed", neg="minus", date_style="long", tags=["credit"]),
    dict(id="co_04", slug="deductive", kind="form_pdf", n_items=3, markup=None, credit="all", neg="paren", date_style="dmy", tags=["credit", "deductive_total"]),
    dict(id="co_05", slug="no_markup", kind="form_pdf", n_items=4, markup=None, date_style="dmy", tags=["no_markup"]),
    dict(id="co_06", slug="us_date", kind="form_pdf", n_items=4, markup=10, date_style="us", ambiguous_date=True, tags=["ambiguous_date"]),
    dict(id="co_07", slug="multipage", kind="form_pdf", n_items=32, markup=10, date_style="long", tags=["multipage"]),
    dict(id="co_08", slug="multipage_credits", kind="form_pdf", n_items=40, markup=15, credit="mixed", neg="paren", date_style="iso", tags=["multipage", "credit"]),
    dict(id="co_09", slug="multipage_nomarkup", kind="form_pdf", n_items=28, markup=None, date_style="dmy", tags=["multipage", "no_markup"]),
    dict(id="co_10", slug="email", kind="email_txt", n_items=3, markup=10, date_style="long", tags=["email"]),
    dict(id="co_11", slug="email_credit", kind="email_txt", n_items=5, markup=None, credit="mixed", neg="minus", date_style="long", distractor=True, tags=["email", "credit", "distractor_numbers"]),
    dict(id="co_12", slug="email_thread", kind="email_txt", n_items=4, markup=15, date_style="long", distractor=True, tags=["email", "distractor_numbers"]),
    dict(id="co_13", slug="email_sparse", kind="email_txt", n_items=2, markup=10, date_style="long", hide=["original_contract_sum", "new_contract_sum", "schedule_impact_days"], tags=["email", "missing_fields"]),
    dict(id="co_14", slug="scan_good", kind="scan_pdf", n_items=4, markup=10, date_style="long", scan="good", tags=["scan", "ocr_required"]),
    dict(id="co_15", slug="scan_poor", kind="scan_pdf", n_items=5, markup=15, date_style="iso", scan="poor", tags=["scan", "ocr_required", "poor_quality"]),
    dict(id="co_16", slug="scan_credit", kind="scan_pdf", n_items=3, markup=10, credit="mixed", neg="paren", date_style="long", scan="good", tags=["scan", "ocr_required", "credit"]),
    dict(id="co_17", slug="eu_format", kind="form_pdf", n_items=4, markup=10, currency="EUR", money_style="eu", date_style="eu", tags=["eu_number_format", "non_usd"]),
    dict(id="co_18", slug="wrong_total", kind="form_pdf", n_items=4, markup=10, date_style="long", mismatch=True, tags=["source_inconsistent"]),
    dict(id="co_19", slug="letter", kind="letter_pdf", n_items=4, markup=10, date_style="long", hide=["original_contract_sum", "new_contract_sum"], tags=["narrative_layout", "missing_fields"]),
    dict(id="co_20", slug="scan_poor_credit", kind="scan_pdf", n_items=6, markup=15, credit="mixed", neg="paren", date_style="us", ambiguous_date=True, scan="poor", tags=["scan", "ocr_required", "poor_quality", "credit", "ambiguous_date"]),
]

SCAN_QUALITY = {
    "good": dict(rot=0.6, blur=0.7, noise=7, contrast=0.90, scale=1.0, jpeg=75),
    "poor": dict(rot=1.8, blur=1.0, noise=12, contrast=0.82, scale=0.85, jpeg=45),
}


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def fmt_date(d: dt.date, style: str) -> str:
    mon_long, mon_short = d.strftime("%B"), d.strftime("%b")
    return {
        "long": f"{mon_long} {d.day}, {d.year}",
        "iso": d.isoformat(),
        "us": f"{d.month:02d}/{d.day:02d}/{d.year}",
        "dmy": f"{d.day:02d}-{mon_short}-{d.year}",
        "eu": f"{d.day} {mon_long} {d.year}",
    }[style]


def _eu(s: str) -> str:
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def fmt_money(x: float, money_style: str, neg: str, cur: str) -> str:
    sym = {"USD": "$", "EUR": "€"}[cur]
    body = f"{abs(x):,.2f}"
    if money_style == "eu":
        s = f"{_eu(body)} {sym}"
    else:
        s = f"{sym}{body}"
    if x < 0:
        s = f"({s})" if neg == "paren" else f"-{s}"
    return s


def fmt_qty(q: float, money_style: str) -> str:
    s = f"{q:,.0f}" if float(q).is_integer() else f"{q:,.2f}"
    return _eu(s) if money_style == "eu" else s


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


# --------------------------------------------------------------------------- #
# Build one change order (gold) + its rendering style
# --------------------------------------------------------------------------- #
def make_co(rng: random.Random, spec: dict):
    n = spec["n_items"]
    credit = spec.get("credit", "none")
    cur = spec.get("currency", "USD")
    items: List[LineItem] = []
    adds, creds = ITEMS[:], CREDIT_ITEMS[:]   # cycle through shuffled pools: no repeats within a doc
    rng.shuffle(adds)
    rng.shuffle(creds)
    ai = ci = 0
    for i in range(n):
        is_credit = credit == "all" or (credit == "mixed" and (i == n - 1 or (n > 6 and rng.random() < 0.15)))
        if is_credit:
            desc, unit, (plo, phi), (qlo, qhi) = creds[ci % len(creds)]
            ci += 1
        else:
            desc, unit, (plo, phi), (qlo, qhi) = adds[ai % len(adds)]
            ai += 1
        if n > 8:
            desc = f"{desc} - Level {rng.randint(1, 6)}, Zone {rng.choice('ABCD')}"
        qty = float(rng.randint(qlo, qhi))
        price = round(rng.uniform(plo, phi), 2)
        amount = round(qty * price, 2) * (-1 if is_credit else 1)
        items.append(LineItem(description=desc, quantity=qty, unit=unit, unit_price=price, amount=round(amount, 2)))

    subtotal = round(sum(li.amount for li in items), 2)
    pct = spec.get("markup")
    markup_amount = round(subtotal * pct / 100, 2) if pct else None
    total = round(subtotal + (markup_amount or 0), 2)
    orig = float(rng.randrange(250_000, 6_000_000, 500))

    reason = rng.choice(list(REASONS))
    names = [li.description.split(" - ")[0] for li in items][:2]
    desc = REASONS[reason] + " Work covers " + " and ".join(x[0].lower() + x[1:] for x in names) + "."
    if credit != "none":
        desc += " Credits are applied for omitted work."

    # date
    while True:
        d = dt.date(2025, 3, 1) + dt.timedelta(days=rng.randint(0, 570))
        if not spec.get("ambiguous_date") or (d.day <= 12 and d.day != d.month):
            break

    status = rng.choice(STATUSES)
    co = ChangeOrder(
        co_number=rng.choice(["CO-%03d", "%03d", "PCO-%02d"]) % rng.randint(1, 48),
        co_date=d,
        project_name=rng.choice(PROJECTS),
        owner=rng.choice(OWNERS),
        contractor=rng.choice(CONTRACTORS),
        reason=reason,
        description=desc,
        line_items=items,
        subtotal=subtotal,
        markup_percent=float(pct) if pct else None,
        markup_amount=markup_amount,
        total=total,
        currency=cur,
        schedule_impact_days=rng.choice([0, 0, 3, 5, 7, 10, 14]),
        original_contract_sum=orig,
        new_contract_sum=round(orig + total, 2),
        status=status,
        signed=(status == "Executed"),
    )
    if spec["kind"] == "email_txt":
        co.signed = None  # an email has no owner signature block

    if spec.get("mismatch"):  # the document prints a wrong total; new_contract_sum stays "true"
        co.total = round(total + rng.choice([-1, 1]) * rng.choice([100.0, 250.0, 1000.0]), 2)

    for f in spec.get("hide", []):
        setattr(co, f, None)

    st = dict(
        labels=rng.choice(LABELS),
        money_style=spec.get("money_style", "us"),
        neg=spec.get("neg", "paren"),
        date_style=spec["date_style"],
        cur=cur,
        zero_text=rng.choice(["0 calendar days", "No change"]),
        title=rng.choice(["CHANGE ORDER", "CONTRACT CHANGE ORDER"]),
        owner_rep=rng.choice(PEOPLE),
        sender=rng.choice(PEOPLE),
        email_variant=rng.choice([0, 1]),
    )
    return co, st


def money_fn(co: ChangeOrder, st: dict):
    return lambda x: fmt_money(x, st["money_style"], st["neg"], co.currency)


def schedule_text(co: ChangeOrder, st: dict) -> Optional[str]:
    if co.schedule_impact_days is None:
        return None
    return st["zero_text"] if co.schedule_impact_days == 0 else f"{co.schedule_impact_days} calendar days"


# --------------------------------------------------------------------------- #
# Renderers
# --------------------------------------------------------------------------- #
def _styles():
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.5, leading=12)
    return dict(
        body=body,
        bold=ParagraphStyle("bold", parent=body, fontName="Helvetica-Bold"),
        right=ParagraphStyle("right", parent=body, alignment=TA_RIGHT),
        rbold=ParagraphStyle("rbold", parent=body, alignment=TA_RIGHT, fontName="Helvetica-Bold"),
        title=ParagraphStyle("title", parent=ss["Title"], fontSize=18, spaceAfter=10),
        h2=ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=11, spaceBefore=8, spaceAfter=3),
    )


def _P(t: str, s) -> Paragraph:
    return Paragraph(escape(str(t)), s)


def _footer(co: ChangeOrder):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(0.75 * inch, 0.5 * inch, f"{co.contractor or ''} - confidential")
        canvas.drawRightString(7.75 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()
    return draw


def _items_table(co, st, S, M):
    hdr = ["Item", "Description", "Qty", "Unit", "Unit Price", "Amount"]
    rows = [[_P(h, S["bold"]) for h in hdr]]
    for i, li in enumerate(co.line_items, 1):
        rows.append([
            _P(i, S["body"]), _P(li.description, S["body"]),
            _P(fmt_qty(li.quantity, st["money_style"]), S["right"]), _P(li.unit, S["body"]),
            _P(M(li.unit_price), S["right"]), _P(M(li.amount), S["right"]),
        ])
    t = Table(rows, colWidths=[0.4 * inch, 3.0 * inch, 0.7 * inch, 0.55 * inch, 1.1 * inch, 1.25 * inch], repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build_form_pdf(co: ChangeOrder, path: Path, st: dict) -> None:
    S, M, L = _styles(), money_fn(co, st), st["labels"]
    story = [_P(st["title"], S["title"])]

    pairs = [(L["co"], co.co_number), (L["date"], fmt_date(co.co_date, st["date_style"]) if co.co_date else None),
             (L["project"], co.project_name), (L["owner"], co.owner),
             (L["contractor"], co.contractor), (L["reason"], co.reason)]
    pairs = [(a, b) for a, b in pairs if b]
    rows = []
    for i in range(0, len(pairs), 2):
        chunk = pairs[i:i + 2]
        row = []
        for a, b in chunk:
            row += [_P(a + ":", S["bold"]), _P(b, S["body"])]
        while len(row) < 4:
            row.append("")
        rows.append(row)
    hdr = Table(rows, colWidths=[1.25 * inch, 2.25 * inch, 1.25 * inch, 2.25 * inch])
    hdr.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story += [hdr]
    if co.currency != "USD":
        story.append(_P(f"All amounts are stated in {co.currency}.", S["body"]))

    story += [_P("Description of Change", S["h2"]), _P(co.description or "", S["body"]), Spacer(1, 8)]
    story.append(_items_table(co, st, S, M))
    story.append(Spacer(1, 8))

    tot = []
    if co.subtotal is not None:
        tot.append(["Subtotal", M(co.subtotal)])
    if co.markup_amount is not None:
        tot.append([f"Overhead & Profit ({co.markup_percent:g}%)", M(co.markup_amount)])
    if co.total is not None:
        tot.append([L["total"], M(co.total)])
    t = Table([[_P(a, S["bold"]), _P(b, S["rbold"])] for a, b in tot], colWidths=[2.8 * inch, 1.4 * inch], hAlign="RIGHT")
    t.setStyle(TableStyle([("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black)]))
    story += [t, Spacer(1, 10)]

    info = []
    if co.original_contract_sum is not None:
        info.append((L["orig"], M(co.original_contract_sum)))
    if co.new_contract_sum is not None:
        info.append((L["new"], M(co.new_contract_sum)))
    if schedule_text(co, st):
        info.append(("Change in Contract Time", schedule_text(co, st)))
    if co.status:
        info.append(("Status", co.status))
    if info:
        it = Table([[_P(a + ":", S["bold"]), _P(b, S["body"])] for a, b in info], colWidths=[2.6 * inch, 2.4 * inch], hAlign="LEFT")
        story += [it, Spacer(1, 14)]

    sig = "/s/ " + st["owner_rep"] if co.signed else "______________________"
    sg = Table([[_P("Owner signature:", S["bold"]), _P(sig, S["body"]),
                 _P("Contractor signature:", S["bold"]), _P("______________________", S["body"])]],
               colWidths=[1.2 * inch, 2.0 * inch, 1.4 * inch, 2.4 * inch])
    story.append(sg)

    SimpleDocTemplate(str(path), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                      topMargin=0.75 * inch, bottomMargin=0.8 * inch).build(
        story, onFirstPage=_footer(co), onLaterPages=_footer(co))


def build_letter_pdf(co: ChangeOrder, path: Path, st: dict) -> None:
    """Narrative layout: the numbers live in sentences, not in labelled cells."""
    S, M = _styles(), money_fn(co, st)
    d = fmt_date(co.co_date, st["date_style"])
    story = [
        _P(co.contractor, S["h2"]), _P(d, S["body"]), Spacer(1, 8),
        _P(co.owner, S["body"]), Spacer(1, 8),
        _P(f"Re: {co.project_name} - Change Order {co.co_number}", S["bold"]), Spacer(1, 8),
        _P("Dear " + co.owner + ",", S["body"]), Spacer(1, 6),
        _P(f"Reason for change: {co.reason}. {co.description}", S["body"]), Spacer(1, 6),
        _P("The priced items are listed below.", S["body"]), Spacer(1, 6),
        _items_table(co, st, S, M), Spacer(1, 8),
    ]
    if co.markup_amount is not None:
        story.append(_P(
            f"The subtotal is {M(co.subtotal)}. With {co.markup_percent:g}% overhead and profit "
            f"({M(co.markup_amount)}), the total of this change order comes to {M(co.total)}.", S["body"]))
    else:
        story.append(_P(f"The total of this change order is {M(co.total)}.", S["body"]))
    if schedule_text(co, st):
        story += [Spacer(1, 4), _P(f"Change in contract time: {schedule_text(co, st)}.", S["body"])]
    story += [Spacer(1, 4), _P(f"Current status: {co.status}.", S["body"]), Spacer(1, 14)]
    sig = "/s/ " + st["owner_rep"] if co.signed else "______________________"
    story += [_P("Owner acceptance: " + sig, S["body"]), Spacer(1, 10), _P("Sincerely,", S["body"]), _P(co.contractor, S["body"])]
    SimpleDocTemplate(str(path), pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                      topMargin=0.75 * inch, bottomMargin=0.8 * inch).build(
        story, onFirstPage=_footer(co), onLaterPages=_footer(co))


def build_email(co: ChangeOrder, path: Path, st: dict, rng: random.Random, distractor: bool) -> None:
    M = money_fn(co, st)
    ms = st["money_style"]
    sender, rep = st["sender"], st["owner_rep"]
    dom = slugify(co.contractor) + ".example"
    L = [
        f"From: {sender} <{slugify(sender)}@{dom}>",
        f"To: {rep} <{slugify(rep)}@{slugify(co.owner)}.example>",
        f"Date: {fmt_date(co.co_date, st['date_style'])}, 9:{rng.randint(10, 59)} AM",
        f"Subject: Change order {co.co_number} - {co.project_name}",
        "",
        f"Hi {rep.split()[0]},",
        "",
        f"Pricing for change order {co.co_number} on {co.project_name} (owner: {co.owner}) is below.",
        f"Reason: {co.reason}",
        f"Scope: {co.description}",
        "",
    ]
    if st["email_variant"] == 0:
        L.append("Items:")
        for li in co.line_items:
            L.append(f"- {li.description}: {fmt_qty(li.quantity, ms)} {li.unit} @ {M(li.unit_price)} = {M(li.amount)}")
    else:
        L.append("Item | Qty | Unit | Unit price | Amount")
        for li in co.line_items:
            L.append(f"{li.description} | {fmt_qty(li.quantity, ms)} | {li.unit} | {M(li.unit_price)} | {M(li.amount)}")
    L.append("")
    L.append(f"Subtotal: {M(co.subtotal)}")
    if co.markup_amount is not None:
        L.append(f"Markup ({co.markup_percent:g}%): {M(co.markup_amount)}")
    L.append(f"Total change: {M(co.total)}")
    L.append("")
    if schedule_text(co, st):
        L.append(f"Schedule impact: {schedule_text(co, st)}.")
    if co.original_contract_sum is not None and co.new_contract_sum is not None:
        L.append(f"Contract sum moves from {M(co.original_contract_sum)} to {M(co.new_contract_sum)}.")
    L += [f"Status: {co.status} - need your sign-off to proceed.", "", "Thanks,", sender,
          f"Project Manager, {co.contractor}", ""]
    if distractor:
        fake = round(rng.uniform(12_000, 90_000), 2)
        earlier = co.co_date - dt.timedelta(days=rng.randint(9, 40))
        L += [f"On {fmt_date(earlier, 'long')}, {rep} wrote:",
              f"> Our allowance for this scope was capped at {M(fake)}. Please keep the change under that figure",
              f"> and confirm schedule by {fmt_date(co.co_date + dt.timedelta(days=5), 'long')}.", ""]
    path.write_text("\n".join(L), encoding="utf-8")


def _degrade(img: Image.Image, q: dict, np_rng: np.random.Generator, py_rng: random.Random) -> Image.Image:
    img = img.convert("L")
    if q["scale"] != 1.0:
        img = img.resize((int(img.width * q["scale"]), int(img.height * q["scale"])), Image.BILINEAR)
    img = ImageEnhance.Contrast(img).enhance(q["contrast"])
    img = img.rotate(q["rot"] * py_rng.choice([-1, 1]), expand=True, fillcolor=255, resample=Image.BICUBIC)
    img = img.filter(ImageFilter.GaussianBlur(q["blur"]))
    arr = np.asarray(img).astype(np.float32)
    arr += np_rng.normal(0, q["noise"], arr.shape)
    arr[np_rng.random(arr.shape) < 0.0008] = 0                      # speckles
    h = arr.shape[0]
    arr *= 1 - 0.10 * np.linspace(0, 1, h)[:, None]                  # uneven scanner lighting
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=q["jpeg"])                          # compression artifacts
    return Image.open(io.BytesIO(buf.getvalue())).convert("L")


def build_scan_pdf(co: ChangeOrder, path: Path, st: dict, quality: str, py_rng: random.Random,
                   np_rng: np.random.Generator) -> None:
    q = SCAN_QUALITY[quality]
    with tempfile.TemporaryDirectory() as td:
        clean = Path(td) / "clean.pdf"
        build_form_pdf(co, clean, st)
        subprocess.run(["pdftoppm", "-r", "150", "-png", str(clean), str(Path(td) / "pg")], check=True)
        pages = [_degrade(Image.open(p), q, np_rng, py_rng) for p in sorted(Path(td).glob("pg-*.png"))]
    pages[0].save(path, "PDF", resolution=150.0 * q["scale"], save_all=True, append_images=pages[1:])


# --------------------------------------------------------------------------- #
def main() -> None:
    for d in (RAW, GOLD):
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob("*"):
            f.unlink()

    manifest: List[Dict] = []
    for spec in SPECS:
        rng = random.Random(f"{SEED}-{spec['id']}")
        np_rng = np.random.default_rng(SEED + int(spec["id"].split("_")[1]))
        co, st = make_co(rng, spec)
        ext = "txt" if spec["kind"] == "email_txt" else "pdf"
        path = RAW / f"{spec['id']}_{spec['slug']}.{ext}"

        if spec["kind"] == "form_pdf":
            build_form_pdf(co, path, st)
        elif spec["kind"] == "letter_pdf":
            build_letter_pdf(co, path, st)
        elif spec["kind"] == "email_txt":
            build_email(co, path, st, rng, spec.get("distractor", False))
        elif spec["kind"] == "scan_pdf":
            build_scan_pdf(co, path, st, spec["scan"], rng, np_rng)

        (GOLD / f"{spec['id']}.json").write_text(
            json.dumps(co.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
        manifest.append(dict(
            id=spec["id"], file=f"raw/{path.name}", kind=spec["kind"], tags=spec["tags"],
            has_text_layer=spec["kind"] != "scan_pdf", expect_inconsistent=bool(spec.get("mismatch")),
            n_line_items=len(co.line_items),
        ))
        print(f"{spec['id']}  {spec['kind']:<11} {path.name}")

    (ROOT / "data" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{len(manifest)} documents written to {RAW}")


if __name__ == "__main__":
    main()
