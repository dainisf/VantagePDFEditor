"""PDFScout core: document operations built on PyMuPDF.

Every function here operates on a ``pymupdf.Document`` (mutating it in place)
or returns new bytes. Rectangles passed in by callers are in *display*
coordinates: PDF points, origin at the top-left of the page as it is shown
(i.e. after the page's /Rotate is applied). Before writing to a page we call
:func:`normalize_page`, which bakes any rotation into the content so that
display coordinates and PDF coordinates coincide.
"""

from __future__ import annotations

import difflib
import io
import re
import shutil
import zipfile
from dataclasses import dataclass
from typing import Iterable, Sequence

import pymupdf

Color = tuple[float, float, float]
RectLike = Sequence[float]

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


class PDFScoutError(ValueError):
    """Raised for invalid user input (bad page number, empty search, ...)."""


def hex_to_rgb(value: str | Sequence[float] | None, default: Color | None = (0, 0, 0)) -> Color | None:
    """Accept '#rrggbb', 'rrggbb', or a 0..1 float triple."""
    if value is None or value == "":
        return default
    if isinstance(value, str):
        v = value.lstrip("#")
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        if len(v) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", v):
            raise PDFScoutError(f"Invalid color: {value!r}")
        return tuple(int(v[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]
    if len(value) != 3:
        raise PDFScoutError(f"Invalid color: {value!r}")
    return tuple(float(c) for c in value)  # type: ignore[return-value]


def int_to_rgb(value: int) -> Color:
    return ((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255


def rgb_to_hex(rgb: Sequence[float] | None) -> str | None:
    if not rgb:
        return None
    return "#" + "".join(f"{round(c * 255):02x}" for c in rgb[:3])


def get_page(doc: pymupdf.Document, index: int) -> pymupdf.Page:
    if not 0 <= index < doc.page_count:
        raise PDFScoutError(f"Page {index + 1} does not exist (document has {doc.page_count} pages)")
    return doc[index]


def parse_page_ranges(spec: str | None, page_count: int) -> list[int]:
    """Parse '1-3,5,8-' (1-based, inclusive) into 0-based indexes.

    ``None``/'' / 'all' means every page. Order is preserved, duplicates removed.
    """
    if spec is None or spec.strip().lower() in ("", "all"):
        return list(range(page_count))
    out: list[int] = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        m = re.fullmatch(r"(\d*)-(\d*)|(\d+)", part)
        if not m:
            raise PDFScoutError(f"Invalid page range: {part!r}")
        if m.group(3):
            a = b = int(m.group(3))
        else:
            a = int(m.group(1)) if m.group(1) else 1
            b = int(m.group(2)) if m.group(2) else page_count
        if a < 1 or b > page_count or a > b:
            raise PDFScoutError(f"Page range {part!r} is outside 1-{page_count}")
        for p in range(a - 1, b):
            if p not in out:
                out.append(p)
    return out


def normalize_page(page: pymupdf.Page) -> None:
    """Bake /Rotate into the page so display coords == PDF coords."""
    if page.rotation:
        page.remove_rotation()


def to_display_rect(page: pymupdf.Page, rect: RectLike) -> pymupdf.Rect:
    """Convert an unrotated (content-space) rect into display coordinates."""
    return (pymupdf.Rect(rect) * page.rotation_matrix).normalize()


def _rect(rect: RectLike) -> pymupdf.Rect:
    r = pymupdf.Rect(rect).normalize()
    if r.is_empty or r.is_infinite:
        raise PDFScoutError(f"Invalid rectangle: {list(rect)}")
    return r


def _rect_list(r: pymupdf.Rect) -> list[float]:
    return [round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)]


# Base-14 font selection by style.
_BASE14 = {
    ("sans", False, False): "helv",
    ("sans", True, False): "hebo",
    ("sans", False, True): "heit",
    ("sans", True, True): "hebi",
    ("serif", False, False): "tiro",
    ("serif", True, False): "tibo",
    ("serif", False, True): "tiit",
    ("serif", True, True): "tibi",
    ("mono", False, False): "cour",
    ("mono", True, False): "cobo",
    ("mono", False, True): "coit",
    ("mono", True, True): "cobi",
}


def base14_font(family: str = "sans", bold: bool = False, italic: bool = False) -> str:
    family = family if family in ("sans", "serif", "mono") else "sans"
    return _BASE14[(family, bool(bold), bool(italic))]


def _guess_family(fontname: str, flags: int) -> str:
    n = fontname.lower()
    if flags & 8 or any(k in n for k in ("mono", "courier", "consol", "code")):
        return "mono"
    if flags & 4 or any(k in n for k in ("times", "serif", "roman", "georgia", "garamond", "cambria")):
        if "sans" not in n:
            return "serif"
    return "sans"


def _span_style(span: dict) -> dict:
    flags = span.get("flags", 0)
    font = span.get("font", "")
    bold = bool(flags & 16) or "bold" in font.lower() or "black" in font.lower()
    italic = bool(flags & 2) or "italic" in font.lower() or "oblique" in font.lower()
    return {
        "font": font,
        "family": _guess_family(font, flags),
        "bold": bold,
        "italic": italic,
        "size": round(span.get("size", 11), 2),
        "color": rgb_to_hex(int_to_rgb(span.get("color", 0))),
    }


# --------------------------------------------------------------------------
# document info
# --------------------------------------------------------------------------


def document_info(doc: pymupdf.Document) -> dict:
    pages = []
    for page in doc:
        pages.append({"width": round(page.rect.width, 2), "height": round(page.rect.height, 2), "rotation": page.rotation})
    return {
        "page_count": doc.page_count,
        "pages": pages,
        "metadata": {k: v for k, v in (doc.metadata or {}).items() if k in ("title", "author", "subject", "keywords", "creator", "producer")},
        "is_form": bool(doc.is_form_pdf),
        "toc": doc.get_toc(simple=True),
        "has_annotations": any(True for p in doc for _ in p.annots()),
    }


def render_page(doc: pymupdf.Document, index: int, scale: float = 1.5, fmt: str = "png", annots: bool = True) -> bytes:
    page = get_page(doc, index)
    scale = max(0.1, min(float(scale), 6.0))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), annots=annots, alpha=False)
    if fmt in ("jpg", "jpeg"):
        return pix.tobytes("jpeg", jpg_quality=85)
    return pix.tobytes("png")


# --------------------------------------------------------------------------
# text extraction & editing
# --------------------------------------------------------------------------


def text_lines(doc: pymupdf.Document, index: int) -> list[dict]:
    """Editable text lines on a page, in display coordinates."""
    page = get_page(doc, index)
    out = []
    data = page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)
    for b_i, block in enumerate(data["blocks"]):
        if block.get("type") != 0:
            continue
        for l_i, line in enumerate(block["lines"]):
            spans = [s for s in line["spans"] if s["text"]]
            if not spans:
                continue
            text = "".join(s["text"] for s in spans)
            if not text.strip():
                continue
            # dominant style = longest span
            main = max(spans, key=lambda s: len(s["text"].strip()))
            out.append(
                {
                    "id": f"{b_i}-{l_i}",
                    "text": text,
                    "bbox": _rect_list(to_display_rect(page, line["bbox"])),
                    "dir": _display_dir(page, line["dir"]),
                    **_span_style(main),
                }
            )
    return out


def _display_dir(page: pymupdf.Page, d: Sequence[float]) -> list[float]:
    m = page.rotation_matrix
    x, y = d[0] * m.a + d[1] * m.c, d[0] * m.b + d[1] * m.d
    return [round(x, 3) + 0.0, round(y, 3) + 0.0]


def _find_line(page: pymupdf.Page, rect: pymupdf.Rect) -> dict | None:
    """Locate the text line best matching ``rect`` (page must be normalized)."""
    best, best_score = None, 0.0
    for block in page.get_text("dict", flags=pymupdf.TEXTFLAGS_TEXT)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            lr = pymupdf.Rect(line["bbox"])
            inter = lr & rect
            if inter.is_empty:
                continue
            union_area = lr.get_area() + rect.get_area() - inter.get_area()
            score = inter.get_area() / union_area if union_area else 0
            if score > best_score:
                best, best_score = line, score
    return best if best_score > 0.3 else None


def edit_text(
    doc: pymupdf.Document,
    index: int,
    bbox: RectLike,
    new_text: str,
    *,
    fontsize: float | None = None,
    color: str | None = None,
    family: str | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
) -> dict:
    """Replace a line of existing page text (like Acrobat's *Edit Text*).

    The old glyphs are removed with a text-only redaction (images and vector
    graphics underneath are preserved) and the new text is written at the same
    baseline in the closest matching standard font.
    """
    page = get_page(doc, index)
    normalize_page(page)
    rect = _rect(bbox)
    line = _find_line(page, rect)
    if line is None:
        raise PDFScoutError("No text found at that location")
    spans = [s for s in line["spans"] if s["text"].strip()] or line["spans"]
    main = max(spans, key=lambda s: len(s["text"].strip()))
    style = _span_style(main)
    origin = pymupdf.Point(spans[0]["origin"])
    line_rect = pymupdf.Rect(line["bbox"])

    dx, dy = line["dir"]
    # Shrink across the line's thickness so neighbouring lines are not clipped.
    if abs(dx) >= abs(dy):
        t = line_rect.height * 0.15
        shrink = pymupdf.Rect(line_rect.x0 + 0.5, line_rect.y0 + t, line_rect.x1 - 0.5, line_rect.y1 - t)
    else:
        t = line_rect.width * 0.15
        shrink = pymupdf.Rect(line_rect.x0 + t, line_rect.y0 + 0.5, line_rect.x1 - t, line_rect.y1 - 0.5)
    page.add_redact_annot(shrink, fill=False)
    page.apply_redactions(
        images=pymupdf.PDF_REDACT_IMAGE_NONE,
        graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
        text=pymupdf.PDF_REDACT_TEXT_REMOVE,
    )

    size = float(fontsize or style["size"])
    fontname = base14_font(family or style["family"], style["bold"] if bold is None else bold, style["italic"] if italic is None else italic)
    rgb = hex_to_rgb(color or style["color"])
    rotate = 0
    if abs(dx) < 0.5:
        rotate = 90 if dy < 0 else 270
    elif dx < 0:
        rotate = 180
    if new_text:
        page.insert_text(origin, new_text, fontsize=size, fontname=fontname, color=rgb, rotate=rotate)
    return {"replaced": "".join(s["text"] for s in line["spans"]), "font": fontname, "size": size}


def _fit_textbox(page, rect, text, **kw) -> pymupdf.Rect:
    """Insert text into rect, growing the rect downward until it fits."""
    rect = pymupdf.Rect(rect)
    for _ in range(40):
        shape = page.new_shape()
        rc = shape.insert_textbox(rect, text, **kw)
        if rc >= 0:
            shape.commit()
            return rect
        rect.y1 += max(-rc, kw.get("fontsize", 11))
        if rect.y1 > page.rect.y1 + 2000:
            break
    raise PDFScoutError("Text does not fit on the page")


def add_text(
    doc: pymupdf.Document,
    index: int,
    rect: RectLike,
    text: str,
    *,
    fontsize: float = 12,
    color: str = "#000000",
    family: str = "sans",
    bold: bool = False,
    italic: bool = False,
    align: str = "left",
) -> list[float]:
    """Add new text to the page content (not an annotation)."""
    if not text:
        raise PDFScoutError("Text is empty")
    page = get_page(doc, index)
    normalize_page(page)
    r = _rect(rect)
    if r.width < fontsize:
        r.x1 = r.x0 + max(fontsize * 10, 100)
    if r.height < fontsize * 1.3:
        r.y1 = r.y0 + fontsize * 1.4
    aligns = {"left": 0, "center": 1, "right": 2, "justify": 3}
    used = _fit_textbox(
        page,
        r,
        text,
        fontsize=fontsize,
        fontname=base14_font(family, bold, italic),
        color=hex_to_rgb(color),
        align=aligns.get(align, 0),
    )
    return _rect_list(used)


def add_image(doc: pymupdf.Document, index: int, rect: RectLike, image: bytes, keep_proportion: bool = True, overlay: bool = True) -> None:
    page = get_page(doc, index)
    normalize_page(page)
    try:
        page.insert_image(_rect(rect), stream=image, keep_proportion=keep_proportion, overlay=overlay)
    except (RuntimeError, ValueError) as e:  # bad image data
        raise PDFScoutError(f"Could not insert image: {e}") from e


# --------------------------------------------------------------------------
# annotations / comments
# --------------------------------------------------------------------------

ANNOT_KINDS = ("highlight", "underline", "strikeout", "squiggly", "note", "rect", "ellipse", "line", "arrow", "ink", "freetext")


def _words_quads(page: pymupdf.Page, rect: pymupdf.Rect) -> list[pymupdf.Quad]:
    quads = []
    for w in page.get_text("words"):
        wr = pymupdf.Rect(w[:4])
        inter = wr & rect
        center = pymupdf.Point((wr.x0 + wr.x1) / 2, (wr.y0 + wr.y1) / 2)
        if not inter.is_empty and (center in rect or inter.get_area() >= 0.5 * wr.get_area()):
            quads.append(wr.quad)
    return quads


def add_annotation(doc: pymupdf.Document, index: int, kind: str, **kw) -> dict:
    """Add a comment/markup annotation.

    kinds: highlight, underline, strikeout, squiggly (``rect``),
    note (``point``, ``text``), rect/ellipse (``rect``), line/arrow
    (``start``, ``end``), ink (``strokes``: list of point lists),
    freetext (``rect``, ``text``, ``fontsize``).
    Common options: ``color``, ``fill``, ``width``, ``opacity``, ``author``.
    """
    if kind not in ANNOT_KINDS:
        raise PDFScoutError(f"Unknown annotation kind: {kind}")
    page = get_page(doc, index)
    normalize_page(page)
    color = hex_to_rgb(kw.get("color"), default=None)
    fill = hex_to_rgb(kw.get("fill"), default=None)
    width = float(kw.get("width") or 1.5)
    opacity = kw.get("opacity")

    if kind in ("highlight", "underline", "strikeout", "squiggly"):
        rect = _rect(kw["rect"])
        quads = _words_quads(page, rect) or [rect.quad]
        fn = {"highlight": page.add_highlight_annot, "underline": page.add_underline_annot, "strikeout": page.add_strikeout_annot, "squiggly": page.add_squiggly_annot}[kind]
        annot = fn(quads)
        if color is None:
            color = {"highlight": (1, 0.92, 0.23)}.get(kind, (0.9, 0.1, 0.1))
    elif kind == "note":
        annot = page.add_text_annot(pymupdf.Point(kw["point"]), kw.get("text", ""), icon=kw.get("icon", "Comment"))
        color = color or (1, 0.8, 0.0)
    elif kind in ("rect", "ellipse"):
        rect = _rect(kw["rect"])
        annot = page.add_rect_annot(rect) if kind == "rect" else page.add_circle_annot(rect)
        color = color or (0.9, 0.1, 0.1)
    elif kind in ("line", "arrow"):
        annot = page.add_line_annot(pymupdf.Point(kw["start"]), pymupdf.Point(kw["end"]))
        if kind == "arrow":
            annot.set_line_ends(pymupdf.PDF_ANNOT_LE_NONE, pymupdf.PDF_ANNOT_LE_OPEN_ARROW)
        color = color or (0.9, 0.1, 0.1)
    elif kind == "ink":
        strokes = [[tuple(p) for p in s] for s in kw.get("strokes", []) if len(s) >= 2]
        if not strokes:
            raise PDFScoutError("Ink annotation needs at least one stroke")
        annot = page.add_ink_annot(strokes)
        color = color or (0.1, 0.2, 0.8)
    else:  # freetext
        rect = _rect(kw["rect"])
        annot = page.add_freetext_annot(
            rect,
            kw.get("text", ""),
            fontsize=float(kw.get("fontsize") or 12),
            text_color=color or (0, 0, 0),
            fill_color=fill,
            border_width=0 if not kw.get("border") else 1,
        )
        color = None  # handled above

    if color is not None:
        if kind in ("rect", "ellipse"):
            annot.set_colors(stroke=color, fill=fill)
        else:
            annot.set_colors(stroke=color)
    if kind in ("rect", "ellipse", "line", "arrow", "ink"):
        annot.set_border(width=width)
    if opacity is not None:
        annot.set_opacity(float(opacity))
    info = {}
    if kw.get("author"):
        info["title"] = kw["author"]
    if kw.get("text") and kind not in ("note", "freetext"):
        info["content"] = kw["text"]
    if info:
        annot.set_info(**info)
    annot.update()
    return {"xref": annot.xref, "type": annot.type[1]}


def list_annotations(doc: pymupdf.Document) -> list[dict]:
    out = []
    for page in doc:
        for a in page.annots():
            out.append(
                {
                    "page": page.number,
                    "xref": a.xref,
                    "type": a.type[1],
                    "rect": _rect_list(to_display_rect(page, a.rect)),
                    "content": a.info.get("content", ""),
                    "author": a.info.get("title", ""),
                    "color": rgb_to_hex(a.colors.get("stroke")),
                }
            )
    return out


def delete_annotation(doc: pymupdf.Document, index: int, xref: int) -> None:
    page = get_page(doc, index)
    for a in page.annots():
        if a.xref == xref:
            page.delete_annot(a)
            return
    raise PDFScoutError(f"Annotation {xref} not found on page {index + 1}")


def flatten(doc: pymupdf.Document, annots: bool = True, widgets: bool = True) -> None:
    """Burn annotations and/or form fields into the page content."""
    doc.bake(annots=annots, widgets=widgets)


# --------------------------------------------------------------------------
# redaction
# --------------------------------------------------------------------------

REDACTION_PRESETS: dict[str, tuple[str, str]] = {
    "email": ("Email addresses", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": ("Phone numbers", r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s.-]?\d{3,4}[\s.-]?\d{3,4}(?!\d)"),
    "ssn": ("US Social Security numbers", r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    "credit_card": ("Credit card numbers", r"(?<!\d)(?:\d[ -]?){13,19}(?<![ -])(?!\d)"),
    "date": ("Dates", r"(?<!\d)(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4}-\d{2}-\d{2})(?!\d)"),
    "ip": ("IP addresses", r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)"),
    "url": ("Web addresses", r"https?://[^\s]+|www\.[^\s]+"),
    "iban": ("IBAN numbers", r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,3})?\b"),
}


_GRAPHICS_MODES = {
    "none": pymupdf.PDF_REDACT_LINE_ART_NONE,
    "covered": pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
    "touched": pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED,
}


@dataclass
class _CharMap:
    text: str
    boxes: list[pymupdf.Rect | None]  # parallel to text
    line_ids: list[int]


def _char_map(page: pymupdf.Page) -> _CharMap:
    chars: list[str] = []
    boxes: list[pymupdf.Rect | None] = []
    line_ids: list[int] = []
    line_no = 0
    raw = page.get_text("rawdict", flags=pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES)
    for block in raw["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                for ch in span["chars"]:
                    chars.append(ch["c"])
                    boxes.append(pymupdf.Rect(ch["bbox"]))
                    line_ids.append(line_no)
            chars.append("\n")
            boxes.append(None)
            line_ids.append(line_no)
            line_no += 1
    return _CharMap("".join(chars), boxes, line_ids)


def _match_rects(cm: _CharMap, start: int, end: int) -> list[pymupdf.Rect]:
    per_line: dict[int, pymupdf.Rect] = {}
    for i in range(start, end):
        box = cm.boxes[i]
        if box is None or box.is_empty:
            continue
        lid = cm.line_ids[i]
        per_line[lid] = per_line[lid] | box if lid in per_line else pymupdf.Rect(box)
    return list(per_line.values())


def build_patterns(terms: Iterable[str] = (), regexes: Iterable[str] = (), presets: Iterable[str] = (), *, case_sensitive: bool = False, whole_word: bool = False) -> list[re.Pattern]:
    flags = 0 if case_sensitive else re.IGNORECASE
    pats: list[re.Pattern] = []
    for t in terms:
        t = t.strip()
        if t:
            body = re.escape(t).replace(r"\ ", r"\s+")
            if whole_word:
                body = rf"(?<!\w){body}(?!\w)"
            pats.append(re.compile(body, flags))
    for r in regexes:
        if r.strip():
            try:
                pats.append(re.compile(r, flags))
            except re.error as e:
                raise PDFScoutError(f"Invalid regular expression {r!r}: {e}") from e
    for p in presets:
        if p not in REDACTION_PRESETS:
            raise PDFScoutError(f"Unknown preset: {p}")
        pats.append(re.compile(REDACTION_PRESETS[p][1]))
    if not pats:
        raise PDFScoutError("Nothing to search for")
    return pats


def find_matches(doc: pymupdf.Document, patterns: list[re.Pattern], pages: list[int] | None = None) -> list[dict]:
    """Find all pattern matches; returns [{page, text, rects(display)}]."""
    results = []
    for idx in pages if pages is not None else range(doc.page_count):
        page = doc[idx]
        cm = _char_map(page)
        seen: set[tuple[int, int]] = set()
        for pat in patterns:
            for m in pat.finditer(cm.text):
                if m.end() <= m.start() or (m.start(), m.end()) in seen:
                    continue
                seen.add((m.start(), m.end()))
                rects = _match_rects(cm, m.start(), m.end())
                if rects:
                    results.append({"page": idx, "text": m.group(0), "rects": [_rect_list(to_display_rect(page, r)) for r in rects]})
    return results


def search_text(doc: pymupdf.Document, query: str, case_sensitive: bool = False, whole_word: bool = False) -> list[dict]:
    return find_matches(doc, build_patterns([query], case_sensitive=case_sensitive, whole_word=whole_word))


def redact(
    doc: pymupdf.Document,
    areas: Iterable[dict],
    *,
    fill: str | None = "#000000",
    overlay_text: str | None = None,
    remove_images: str = "pixels",
    remove_graphics: bool | str = "covered",
) -> int:
    """Permanently remove everything under the given areas.

    ``areas`` is an iterable of ``{"page": int, "rect": [x0,y0,x1,y1]}`` in
    display coordinates. Text under the area is deleted from the content
    stream, image pixels are blanked (or the whole image removed with
    ``remove_images="remove"``). Vector graphics are removed when fully
    covered (``remove_graphics="covered"``, default), when touched at all
    (``"touched"``), or kept (``"none"``); the fill box hides what remains.
    """
    by_page: dict[int, list[pymupdf.Rect]] = {}
    for a in areas:
        by_page.setdefault(int(a["page"]), []).append(_rect(a["rect"]))
    if not by_page:
        raise PDFScoutError("No redaction areas given")
    img_mode = {
        "none": pymupdf.PDF_REDACT_IMAGE_NONE,
        "remove": pymupdf.PDF_REDACT_IMAGE_REMOVE,
        "pixels": pymupdf.PDF_REDACT_IMAGE_PIXELS,
    }.get(remove_images, pymupdf.PDF_REDACT_IMAGE_PIXELS)
    fill_rgb = hex_to_rgb(fill, default=None) if fill else False
    count = 0
    for idx, rects in by_page.items():
        page = get_page(doc, idx)
        normalize_page(page)  # afterwards display coords == content coords
        for r in rects:
            page.add_redact_annot(r, text=overlay_text or None, fill=fill_rgb, text_color=(1, 1, 1) if fill_rgb and sum(fill_rgb) < 1.5 else (0, 0, 0), fontsize=8)
            count += 1
        page.apply_redactions(
            images=img_mode,
            graphics=_GRAPHICS_MODES.get(remove_graphics if isinstance(remove_graphics, str) else ("covered" if remove_graphics else "none"), pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED),
            text=pymupdf.PDF_REDACT_TEXT_REMOVE,
        )
        # remove annotations sitting over redacted areas (comments could leak text)
        for annot in list(page.annots()):
            if annot.type[0] in (pymupdf.PDF_ANNOT_LINK,):
                continue
            if any(annot.rect.intersects(r) for r in rects):
                page.delete_annot(annot)
        for link in page.get_links():
            if any(pymupdf.Rect(link["from"]).intersects(r) for r in rects):
                page.delete_link(link)
    return count


def redact_matches(doc: pymupdf.Document, patterns: list[re.Pattern], pages: list[int] | None = None, **kw) -> int:
    matches = find_matches(doc, patterns, pages)
    areas = [{"page": m["page"], "rect": r} for m in matches for r in m["rects"]]
    if not areas:
        return 0
    redact(doc, areas, **kw)
    return len(matches)


def sanitize(doc: pymupdf.Document, *, metadata: bool = True, javascript: bool = True, attachments: bool = True, links: bool = False, hidden_text: bool = True, thumbnails: bool = True, reset_forms: bool = False) -> None:
    """Remove hidden information (Acrobat's *Sanitize document*)."""
    doc.scrub(
        attached_files=attachments,
        embedded_files=attachments,
        clean_pages=True,
        hidden_text=hidden_text,
        javascript=javascript,
        metadata=metadata,
        xml_metadata=metadata,
        redactions=False,
        remove_links=links,
        reset_fields=reset_forms,
        reset_responses=True,
        thumbnails=thumbnails,
    )
    if metadata:
        doc.set_metadata({})
        doc.del_xml_metadata()


# --------------------------------------------------------------------------
# page organisation
# --------------------------------------------------------------------------


def rotate_pages(doc: pymupdf.Document, pages: list[int], angle: int) -> None:
    if angle % 90:
        raise PDFScoutError("Rotation must be a multiple of 90")
    for i in pages:
        page = get_page(doc, i)
        page.set_rotation((page.rotation + angle) % 360)


def delete_pages(doc: pymupdf.Document, pages: list[int]) -> None:
    pages = sorted(set(pages))
    if len(pages) >= doc.page_count:
        raise PDFScoutError("Cannot delete every page")
    for i in pages:
        get_page(doc, i)
    doc.delete_pages(pages)


def reorder_pages(doc: pymupdf.Document, order: list[int]) -> None:
    """Re-arrange pages. ``order`` may repeat (duplicate) or omit (drop) pages."""
    if not order:
        raise PDFScoutError("Page order is empty")
    for i in order:
        get_page(doc, i)
    doc.select(order)


def move_page(doc: pymupdf.Document, src: int, dest: int) -> None:
    order = list(range(doc.page_count))
    get_page(doc, src)
    order.pop(src)
    dest = max(0, min(dest, len(order)))
    order.insert(dest, src)
    doc.select(order)


def insert_blank_page(doc: pymupdf.Document, at: int, width: float | None = None, height: float | None = None) -> None:
    at = max(0, min(at, doc.page_count))
    if width is None or height is None:
        ref = doc[min(at, doc.page_count - 1)] if doc.page_count else None
        width, height = (ref.rect.width, ref.rect.height) if ref else pymupdf.paper_size("a4")
    doc.new_page(pno=at, width=width, height=height)


def insert_pdf(doc: pymupdf.Document, other: bytes, at: int | None = None, password: str | None = None, pages: str | None = None) -> int:
    """Merge another PDF (or image) into this one. Returns pages added."""
    src = open_bytes(other, password)
    if not src.is_pdf:
        pdfbytes = src.convert_to_pdf()
        src.close()
        src = pymupdf.open("pdf", pdfbytes)
    sel = parse_page_ranges(pages, src.page_count)
    at = doc.page_count if at is None else max(0, min(at, doc.page_count))
    before = doc.page_count
    if sel == list(range(src.page_count)):
        doc.insert_pdf(src, start_at=at)
    else:
        for n, p in enumerate(sel):
            doc.insert_pdf(src, from_page=p, to_page=p, start_at=at + n)
    src.close()
    return doc.page_count - before


def extract_pages(doc: pymupdf.Document, pages: list[int]) -> bytes:
    out = pymupdf.open()
    for p in pages:
        get_page(doc, p)
        out.insert_pdf(doc, from_page=p, to_page=p)
    return out.tobytes(garbage=4, deflate=True)


def split(doc: pymupdf.Document, *, every: int | None = None, ranges: str | None = None, basename: str = "document") -> bytes:
    """Split into several PDFs, returned as a zip archive."""
    groups: list[list[int]] = []
    if ranges:
        for part in ranges.split(";"):
            if part.strip():
                groups.append(parse_page_ranges(part, doc.page_count))
    else:
        n = max(1, int(every or 1))
        groups = [list(range(i, min(i + n, doc.page_count))) for i in range(0, doc.page_count, n)]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for gi, g in enumerate(groups, 1):
            label = f"{g[0] + 1}" if len(g) == 1 else f"{g[0] + 1}-{g[-1] + 1}"
            zf.writestr(f"{basename}_part{gi:02d}_p{label}.pdf", extract_pages(doc, g))
    return buf.getvalue()


def crop_pages(doc: pymupdf.Document, pages: list[int], rect: RectLike) -> None:
    """Crop pages to ``rect`` (display coordinates of the first page)."""
    r = _rect(rect)
    for i in pages:
        page = get_page(doc, i)
        normalize_page(page)
        target = r & page.rect
        if target.is_empty:
            raise PDFScoutError("Crop area is outside the page")
        offset = page.cropbox_position
        page.set_cropbox(target + (offset.x, offset.y, offset.x, offset.y))


# --------------------------------------------------------------------------
# stamps: watermark, header/footer, page numbers, Bates
# --------------------------------------------------------------------------


def watermark(
    doc: pymupdf.Document,
    text: str,
    *,
    pages: list[int] | None = None,
    fontsize: float = 60,
    color: str = "#ff0000",
    opacity: float = 0.25,
    angle: float = 45,
    family: str = "sans",
    bold: bool = True,
    behind: bool = False,
) -> None:
    if not text:
        raise PDFScoutError("Watermark text is empty")
    fontname = base14_font(family, bold)
    font = pymupdf.Font(fontname)
    for i in pages if pages is not None else range(doc.page_count):
        page = get_page(doc, i)
        normalize_page(page)
        width = font.text_length(text, fontsize=fontsize)
        pr = page.rect
        center = pymupdf.Point((pr.x0 + pr.x1) / 2, (pr.y0 + pr.y1) / 2)
        start = pymupdf.Point(center.x - width / 2, center.y + fontsize * 0.35)
        page.insert_text(
            start,
            text,
            fontsize=fontsize,
            fontname=fontname,
            color=hex_to_rgb(color),
            fill_opacity=opacity,
            stroke_opacity=opacity,
            morph=(center, pymupdf.Matrix(angle)),
            overlay=not behind,
        )


def stamp_header_footer(
    doc: pymupdf.Document,
    *,
    pages: list[int] | None = None,
    header_left: str = "",
    header_center: str = "",
    header_right: str = "",
    footer_left: str = "",
    footer_center: str = "",
    footer_right: str = "",
    fontsize: float = 10,
    color: str = "#000000",
    family: str = "sans",
    margin: float = 28,
    start_number: int = 1,
    bates_prefix: str = "",
    bates_suffix: str = "",
    bates_digits: int = 6,
    bates_start: int = 1,
    filename: str = "",
) -> None:
    """Header/footer text with tokens.

    Tokens: ``{page}`` page number (starting at ``start_number``), ``{total}``,
    ``{bates}`` Bates number, ``{date}`` today's date, ``{filename}``.
    """
    import datetime as _dt

    targets = pages if pages is not None else list(range(doc.page_count))
    total = len(targets)
    fontname = base14_font(family)
    font = pymupdf.Font(fontname)
    rgb = hex_to_rgb(color)
    today = _dt.date.today().isoformat()
    for n, i in enumerate(targets):
        page = get_page(doc, i)
        normalize_page(page)
        tokens = {
            "page": str(start_number + n),
            "total": str(total + start_number - 1),
            "bates": f"{bates_prefix}{bates_start + n:0{max(1, bates_digits)}d}{bates_suffix}",
            "date": today,
            "filename": filename,
        }
        for slot, raw in (
            ("hl", header_left),
            ("hc", header_center),
            ("hr", header_right),
            ("fl", footer_left),
            ("fc", footer_center),
            ("fr", footer_right),
        ):
            if not raw:
                continue
            try:
                txt = raw.format(**tokens)
            except (KeyError, IndexError, ValueError) as e:
                raise PDFScoutError(f"Unknown token in {raw!r}: {e}") from e
            w = font.text_length(txt, fontsize=fontsize)
            pr = page.rect
            x = {"l": pr.x0 + margin, "c": pr.x0 + (pr.width - w) / 2, "r": pr.x1 - margin - w}[slot[1]]
            y = pr.y0 + margin + fontsize * 0.8 if slot[0] == "h" else pr.y1 - margin
            page.insert_text((x, y), txt, fontsize=fontsize, fontname=fontname, color=rgb)


# --------------------------------------------------------------------------
# forms
# --------------------------------------------------------------------------

_FIELD_TYPES = {
    "text": pymupdf.PDF_WIDGET_TYPE_TEXT,
    "checkbox": pymupdf.PDF_WIDGET_TYPE_CHECKBOX,
    "combobox": pymupdf.PDF_WIDGET_TYPE_COMBOBOX,
    "listbox": pymupdf.PDF_WIDGET_TYPE_LISTBOX,
    "radio": pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON,
    "signature": pymupdf.PDF_WIDGET_TYPE_SIGNATURE,
}


def list_fields(doc: pymupdf.Document) -> list[dict]:
    out = []
    for page in doc:
        for w in page.widgets():
            out.append(
                {
                    "page": page.number,
                    "name": w.field_name,
                    "type": w.field_type_string.lower(),
                    "value": w.field_value,
                    "options": list(w.choice_values or []),
                    "on_state": w.on_state() if w.field_type in (pymupdf.PDF_WIDGET_TYPE_CHECKBOX, pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON) else None,
                    "rect": _rect_list(to_display_rect(page, w.rect)),
                    "xref": w.xref,
                    "readonly": bool(w.field_flags & 1),
                }
            )
    return out


def fill_fields(doc: pymupdf.Document, values: dict[str, object]) -> int:
    """Fill form fields by name (or ``xref:<n>`` for a specific widget)."""
    filled = 0
    for page in doc:
        for w in page.widgets():
            key = w.field_name if w.field_name in values else f"xref:{w.xref}"
            if key not in values:
                continue
            v = values[key]
            if w.field_type in (pymupdf.PDF_WIDGET_TYPE_CHECKBOX, pymupdf.PDF_WIDGET_TYPE_RADIOBUTTON):
                on = w.on_state() or "Yes"
                if isinstance(v, str):
                    checked = v not in ("", "Off", "false", "0") and (w.field_type == pymupdf.PDF_WIDGET_TYPE_CHECKBOX or v == on or v in ("true", "1", "Yes"))
                else:
                    checked = bool(v)
                w.field_value = on if checked else "Off"
            else:
                w.field_value = "" if v is None else str(v)
            w.update()
            filled += 1
    return filled


def add_field(doc: pymupdf.Document, index: int, kind: str, rect: RectLike, name: str, *, value: str = "", options: list[str] | None = None, fontsize: float = 11) -> int:
    if kind not in _FIELD_TYPES:
        raise PDFScoutError(f"Unknown field type: {kind}")
    if not name:
        raise PDFScoutError("Field name is required")
    page = get_page(doc, index)
    normalize_page(page)
    w = pymupdf.Widget()
    w.field_type = _FIELD_TYPES[kind]
    w.field_name = name
    w.rect = _rect(rect)
    w.text_fontsize = fontsize
    w.border_color = (0.4, 0.4, 0.6)
    w.border_width = 1
    if kind in ("combobox", "listbox"):
        w.choice_values = options or []
        if value:
            w.field_value = value
    elif kind == "checkbox":
        w.field_value = value in ("1", "true", "Yes", True)
    elif value:
        w.field_value = value
    annot = page.add_widget(w)
    return annot.xref


# --------------------------------------------------------------------------
# metadata, bookmarks
# --------------------------------------------------------------------------


def set_metadata(doc: pymupdf.Document, values: dict[str, str]) -> None:
    md = dict(doc.metadata or {})
    for k in ("title", "author", "subject", "keywords", "creator", "producer"):
        if k in values:
            md[k] = values[k] or ""
    doc.set_metadata(md)


def set_bookmarks(doc: pymupdf.Document, toc: list[list]) -> None:
    """toc: [[level, title, page(1-based)], ...]"""
    clean = []
    for item in toc:
        level, title, page = int(item[0]), str(item[1]), int(item[2])
        if not 1 <= page <= doc.page_count:
            raise PDFScoutError(f"Bookmark '{title}' points to missing page {page}")
        clean.append([level, title, page])
    try:
        doc.set_toc(clean)
    except ValueError as e:
        raise PDFScoutError(f"Invalid bookmark hierarchy: {e}") from e


# --------------------------------------------------------------------------
# saving, security, optimisation
# --------------------------------------------------------------------------

PERMISSIONS = {
    "print": pymupdf.PDF_PERM_PRINT | pymupdf.PDF_PERM_PRINT_HQ,
    "modify": pymupdf.PDF_PERM_MODIFY | pymupdf.PDF_PERM_ASSEMBLE,
    "copy": pymupdf.PDF_PERM_COPY | pymupdf.PDF_PERM_ACCESSIBILITY,
    "annotate": pymupdf.PDF_PERM_ANNOTATE | pymupdf.PDF_PERM_FORM,
}


def open_bytes(data: bytes, password: str | None = None, filetype: str | None = None) -> pymupdf.Document:
    try:
        doc = pymupdf.open(stream=data, filetype=filetype) if filetype else pymupdf.open(stream=data)
    except (pymupdf.FileDataError, RuntimeError, ValueError) as e:
        raise PDFScoutError(f"Cannot open file: {e}") from e
    if doc.needs_pass:
        if not password or not doc.authenticate(password):
            doc.close()
            raise PDFScoutError("Password required" if not password else "Incorrect password")
    return doc


def save_bytes(
    doc: pymupdf.Document,
    *,
    user_password: str | None = None,
    owner_password: str | None = None,
    permissions: Iterable[str] | None = None,
    compress: bool = False,
    linearize: bool = False,
) -> bytes:
    kw: dict = {"garbage": 4 if compress else 3, "deflate": True, "clean": compress}
    if compress:
        kw.update(deflate_images=True, deflate_fonts=True, use_objstms=1)
    if user_password or owner_password:
        perm = 0
        for p in permissions if permissions is not None else PERMISSIONS:
            perm |= PERMISSIONS.get(p, 0)
        kw.update(
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw=user_password or "",
            owner_pw=owner_password or user_password,
            permissions=perm,
        )
    return doc.tobytes(**kw)


def optimize(doc: pymupdf.Document, *, image_dpi: int | None = 150, image_quality: int = 75, subset_fonts: bool = True) -> None:
    """Reduce file size: downsample images and subset fonts (save with compress=True)."""
    if image_dpi:
        doc.rewrite_images(dpi_threshold=int(image_dpi * 1.3), dpi_target=int(image_dpi), quality=int(image_quality))
    if subset_fonts:
        try:
            doc.subset_fonts()
        except Exception:  # noqa: BLE001 - font subsetting is best effort
            pass


# --------------------------------------------------------------------------
# conversion, OCR, compare
# --------------------------------------------------------------------------


def export_images(doc: pymupdf.Document, pages: list[int] | None = None, dpi: int = 150, fmt: str = "png", basename: str = "page") -> bytes:
    fmt = "jpg" if fmt in ("jpg", "jpeg") else "png"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in pages if pages is not None else range(doc.page_count):
            pix = get_page(doc, i).get_pixmap(dpi=dpi, alpha=False)
            data = pix.tobytes("jpeg", jpg_quality=90) if fmt == "jpg" else pix.tobytes("png")
            zf.writestr(f"{basename}-{i + 1:03d}.{fmt}", data)
    return buf.getvalue()


def export_text(doc: pymupdf.Document, fmt: str = "txt") -> str:
    if fmt == "html":
        return "\n".join(page.get_text("xhtml") for page in doc)
    parts = []
    for page in doc:
        parts.append(page.get_text("text", sort=True))
    return "\n\f".join(parts)


def images_to_pdf(images: list[tuple[str, bytes]], page_size: str | None = None) -> bytes:
    """Create a PDF from images; each image becomes a page."""
    out = pymupdf.open()
    for name, data in images:
        try:
            img = pymupdf.open(stream=data, filetype=name.rsplit(".", 1)[-1].lower() if "." in name else None)
        except Exception as e:  # noqa: BLE001
            raise PDFScoutError(f"Cannot read image {name}: {e}") from e
        if img.is_pdf:
            out.insert_pdf(img)
            continue
        rect = img[0].rect
        if page_size:
            pw, ph = pymupdf.paper_size(page_size)
            if rect.width > rect.height:
                pw, ph = ph, pw
            page = out.new_page(width=pw, height=ph)
            page.insert_image(page.rect + (24, 24, -24, -24), stream=data)
        else:
            page = out.new_page(width=rect.width, height=rect.height)
            page.insert_image(page.rect, stream=data)
        img.close()
    if not out.page_count:
        raise PDFScoutError("No images given")
    return out.tobytes(garbage=3, deflate=True)


def ocr_available() -> bool:
    return shutil.which("tesseract") is not None


def ocr(doc: pymupdf.Document, pages: list[int] | None = None, language: str = "eng", dpi: int = 300, skip_text_pages: bool = True) -> int:
    """Make scanned pages searchable by adding an invisible OCR text layer."""
    if not ocr_available():
        raise PDFScoutError("OCR needs Tesseract installed (e.g. `apt install tesseract-ocr`)")
    done = 0
    for i in pages if pages is not None else range(doc.page_count):
        page = get_page(doc, i)
        if skip_text_pages and page.get_text("text").strip():
            continue
        normalize_page(page)
        tp = page.get_textpage_ocr(language=language, dpi=dpi, full=True)
        for x0, y0, x1, y1, word, *_ in page.get_text("words", textpage=tp):
            h = y1 - y0
            if h <= 0:
                continue
            font = pymupdf.Font("helv")
            size = h * 0.9
            natural = font.text_length(word, fontsize=size) or 1
            page.insert_text(
                (x0, y1 - h * 0.2),
                word,
                fontsize=size,
                fontname="helv",
                render_mode=3,  # invisible
                morph=(pymupdf.Point(x0, y1), pymupdf.Matrix((x1 - x0) / natural, 1)),
            )
        done += 1
    return done


def compare(a: pymupdf.Document, b: pymupdf.Document) -> dict:
    """Text comparison of two documents, page by page."""
    pages = []
    n = max(a.page_count, b.page_count)
    for i in range(n):
        ta = a[i].get_text("text", sort=True).splitlines() if i < a.page_count else []
        tb = b[i].get_text("text", sort=True).splitlines() if i < b.page_count else []
        if ta == tb:
            continue
        changes = []
        sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            changes.append({"op": tag, "old": ta[i1:i2], "new": tb[j1:j2]})
        pages.append({"page": i, "changes": changes})
    return {"identical": not pages, "page_count": [a.page_count, b.page_count], "pages": pages}
