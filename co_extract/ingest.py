"""Stage 1 - turn a file into text, and remember how trustworthy that text is.

* .txt                      -> used as-is
* PDF page with a text layer -> pdfplumber text (no OCR, so no OCR errors)
* PDF page without one       -> OCR (render -> deskew -> Tesseract)

Besides the text, ingest keeps the signals the confidence stage needs later:
which pages were OCR'd, and Tesseract's per-word confidence, so a field read from a
blurry scan can be scored lower than one read from a clean text layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pdfplumber
from PIL import Image, ImageOps

MIN_TEXT_CHARS = 40  # fewer characters than this on a page => treat the page as a scan
MIN_TABLE_ROWS, MIN_TABLE_COLS = 2, 3   # smaller "tables" are layout artefacts: leave them alone
FRAGMENT_GAP = 6.0       # pt of empty space between characters that separates two cells on a line
LINE_TOL = 2.5           # pt: words whose tops differ by less than this are on one line
ALIGN_TOL = 1.5          # pt: a wrapped line starts at the same x as the cell it continues
SENTENCE_END = (".", ":", ";", "!", "?", ",")


def _word_lines(words: list) -> list:
    """Group pdfplumber words into text lines (same baseline), left to right."""
    lines: list = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if lines and abs(w["top"] - lines[-1]["top"]) <= LINE_TOL:
            lines[-1]["words"].append(w)
        else:
            lines.append(dict(top=w["top"], words=[w]))
    for ln in lines:
        ln["words"].sort(key=lambda w: w["x0"])
        ln["size"] = max(w.get("size") or 10 for w in ln["words"])
    return lines


def _fragments(line: dict) -> list:
    """Split one text line into 'cell' fragments at wide horizontal gaps."""
    groups: list = []
    for w in line["words"]:
        if groups and w["x0"] - groups[-1][-1]["x1"] <= FRAGMENT_GAP:
            groups[-1].append(w)
        else:
            groups.append([w])
    return [dict(text=" ".join(w["text"] for w in g), x0=g[0]["x0"],
                 bold=all("bold" in (w.get("fontname") or "").lower() for w in g)) for g in groups]


def reflow(lines: list) -> Tuple[str, List[str]]:
    """Re-attach wrapped cell text, using position and font weight.

    A table-less form puts two cells side by side; when one wraps, its tail lands on its own
    line ("Project: Maple Ridge Elementary Gym  Owner: X" / "Addition") and a plain read cuts the value
    in two. A short, non-bold, label-free fragment alone on a line that starts at the same x as a
    non-bold fragment on the line just above, at normal line spacing, continues that fragment.
    Anything that looks like such a tail but cannot be attached is returned as an orphan, so the
    confidence stage can distrust the value above it.
    """
    rows: list = []
    orphans: List[str] = []
    for ln in lines:
        frags = _fragments(ln)
        row = dict(frags=frags, top=ln["top"], size=ln["size"])
        f0 = frags[0]
        if len(frags) == 1 and not f0["bold"] and len(f0["text"].split()) <= 3 and ":" not in f0["text"] and rows:
            prev = rows[-1]
            near = row["top"] - prev["top"] <= 1.6 * prev["size"]
            targets = [f for f in prev["frags"]
                       if not f["bold"] and abs(f["x0"] - f0["x0"]) <= ALIGN_TOL and not f["text"].endswith(SENTENCE_END)]
            if near and targets:
                targets[0]["text"] += " " + f0["text"]
                continue
            if near:
                orphans.append(f0["text"])
        rows.append(row)
    return "\n".join(" ".join(f["text"] for f in r["frags"]) for r in rows), orphans


def _region_text(region) -> Tuple[str, List[str]]:
    try:
        words = region.extract_words(extra_attrs=["fontname", "size"])
        return reflow(_word_lines(words)) if words else ("", [])
    except Exception:
        return (region.extract_text() or "").strip(), []


def page_text(page) -> Tuple[str, List[str]]:
    """Text of one PDF page, with ruled tables kept as rows.

    Plain `extract_text()` reads line by line across the page, so a table cell that wraps
    ("... Level 4, Zone" / "A") is cut in two and interleaved with its neighbours. For ruled
    tables we instead take each row's cells from the table structure and render them as
    `cell | cell | cell` with wrapped lines joined. Text outside tables is read as before.
    """
    try:
        tables = [t for t in page.find_tables()
                  if len(t.rows) >= MIN_TABLE_ROWS and len(t.rows[0].cells) >= MIN_TABLE_COLS]
    except Exception:
        tables = []
    if not tables:
        return _region_text(page)

    tables.sort(key=lambda t: t.bbox[1])
    x0, top, x1, bottom = page.bbox
    parts: List[str] = []
    orphans: List[str] = []

    def add_region(y0: float, y1: float) -> None:
        if y1 - y0 > 1:
            text, orph = _region_text(page.crop((x0, y0, x1, y1)))
            parts.append(text)
            orphans.extend(orph)

    cursor = top
    for t in tables:
        add_region(cursor, t.bbox[1])
        for row in t.extract():
            cells = [" ".join((c or "").split()) for c in row]
            if any(cells):
                parts.append(" | ".join(cells))
        cursor = t.bbox[3]
    add_region(cursor, bottom)
    return "\n".join(p.strip() for p in parts if p and p.strip()), orphans


@dataclass
class OCRConfig:
    # Defaults chosen by scripts/ocr_ablation.py: plain Tesseract beat every preprocessing
    # variant on average. Deskew and binarize are kept as options because they help some
    # scans and wreck others (see notes/writeup_notes.md); they are not on by default.
    dpi: int = 300
    deskew: bool = False
    binarize: bool = False
    psm: int = 3


@dataclass
class PageText:
    page: int
    text: str
    method: str                                   # "plain" | "text_layer" | "ocr"
    mean_conf: Optional[float] = None             # OCR only, 0-100
    words: List[Tuple[str, float]] = field(default_factory=list)   # OCR only: (word, conf)
    skew_deg: Optional[float] = None
    orphans: List[str] = field(default_factory=list)   # stray line fragments ingest could not attach


@dataclass
class IngestResult:
    path: str
    pages: List[PageText]
    warnings: List[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        if len(self.pages) == 1:
            return self.pages[0].text
        return "\n".join(f"=== PAGE {p.page} ===\n{p.text}" for p in self.pages)

    @property
    def orphans(self) -> List[str]:
        return [o for p in self.pages for o in p.orphans]

    @property
    def used_ocr(self) -> bool:
        return any(p.method == "ocr" for p in self.pages)

    @property
    def mean_ocr_conf(self) -> Optional[float]:
        c = [p.mean_conf for p in self.pages if p.mean_conf is not None]
        return float(np.mean(c)) if c else None


# --------------------------------------------------------------------------- #
def _ink_mask(gray: Image.Image) -> np.ndarray:
    g = ImageOps.autocontrast(gray, cutoff=2)
    return np.asarray(g) < 128


def estimate_skew(img: Image.Image, max_angle: float = 4.0, step: float = 0.25) -> float:
    """Projection-profile deskew: the right angle makes text rows line up, which
    maximises the variance of the per-row ink counts."""
    small = img.convert("L").copy()
    small.thumbnail((900, 1100))
    best, best_score = 0.0, -1.0
    for a in np.arange(-max_angle, max_angle + step, step):
        rot = small.rotate(float(a), expand=False, fillcolor=255, resample=Image.BILINEAR)
        score = float(_ink_mask(rot).sum(axis=1).astype(np.float64).var())
        if score > best_score:
            best, best_score = float(a), score
    return best


def preprocess(img: Image.Image, cfg: OCRConfig) -> Tuple[Image.Image, float]:
    g = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    skew = 0.0
    if cfg.deskew:
        skew = estimate_skew(g)
        if abs(skew) > 0.1:
            g = g.rotate(skew, expand=True, fillcolor=255, resample=Image.BICUBIC)
    if cfg.binarize:
        thr = float(np.asarray(g).mean() - 0.6 * np.asarray(g).std())
        g = g.point(lambda p: 255 if p > thr else 0)
    return g, skew


def ocr_image(img: Image.Image, cfg: OCRConfig, page: int = 1) -> PageText:
    import pytesseract
    from pytesseract import Output

    g, skew = preprocess(img, cfg)
    d = pytesseract.image_to_data(g, config=f"--psm {cfg.psm}", output_type=Output.DICT)

    lines: dict = {}
    words: List[Tuple[str, float]] = []
    for i, w in enumerate(d["text"]):
        w = w.strip()
        conf = float(d["conf"][i])
        if not w or conf < 0:
            continue
        key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        lines.setdefault(key, []).append(w)
        words.append((w, conf))
    text = "\n".join(" ".join(ws) for ws in lines.values())
    mean = float(np.mean([c for _, c in words])) if words else 0.0
    return PageText(page=page, text=text, method="ocr", mean_conf=mean, words=words, skew_deg=skew)


def ingest(path: str | Path, cfg: Optional[OCRConfig] = None) -> IngestResult:
    cfg = cfg or OCRConfig()
    path = Path(path)
    res = IngestResult(path=str(path), pages=[])

    if path.suffix.lower() in {".txt", ".md", ".eml"}:
        res.pages.append(PageText(1, path.read_text(encoding="utf-8", errors="replace"), "plain"))
        return res
    if path.suffix.lower() != ".pdf":
        res.warnings.append(f"unsupported extension {path.suffix}; trying to read as text")
        res.pages.append(PageText(1, path.read_text(encoding="utf-8", errors="replace"), "plain"))
        return res

    scan_pages: List[int] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            t, orph = page_text(page)
            if len(t) >= MIN_TEXT_CHARS:
                res.pages.append(PageText(i, t, "text_layer", orphans=orph))
            else:
                res.pages.append(PageText(i, "", "ocr"))   # placeholder, filled below
                scan_pages.append(i)

    if scan_pages:
        from pdf2image import convert_from_path
        for i in scan_pages:
            img = convert_from_path(str(path), dpi=cfg.dpi, first_page=i, last_page=i)[0]
            res.pages[i - 1] = ocr_image(img, cfg, page=i)
        res.warnings.append(f"OCR used on page(s) {scan_pages}")
        if (res.mean_ocr_conf or 0) < 55:   # dev set: worst scan 43, others 60-68
            res.warnings.append(f"low OCR confidence ({res.mean_ocr_conf:.0f}/100)")
    if not any(p.text.strip() for p in res.pages):
        res.warnings.append("no text could be extracted")
    return res
