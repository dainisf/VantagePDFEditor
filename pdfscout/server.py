"""PDFScout HTTP API + web UI (FastAPI)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable

import pymupdf
from fastapi import Body, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__, brand, core
from .store import DocumentStore, Session

STATIC = Path(__file__).parent / "static"
MAX_BYTES = int(float(os.environ.get("PDFSCOUT_MAX_MB", "200")) * 1024 * 1024)

app = FastAPI(title=brand.PRODUCT_NAME, version=__version__)
store = DocumentStore()


# --------------------------------------------------------------------------
# plumbing
# --------------------------------------------------------------------------


@app.exception_handler(core.PDFScoutError)
async def _user_error(_: Request, exc: core.PDFScoutError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(KeyError)
async def _not_found(_: Request, exc: KeyError):
    return JSONResponse({"detail": f"Not found: {exc}"}, status_code=404)


def _session(sid: str) -> Session:
    try:
        return store.get(sid)
    except KeyError:
        raise HTTPException(404, "Document not found or expired. Please open it again.") from None


def _snapshot(sess: Session, result: Any = None) -> dict:
    with sess.lock:
        out = {**sess.state(), **core.document_info(sess.doc())}
    if result is not None:
        out["result"] = result
    return out


async def _read(upload: UploadFile) -> bytes:
    data = await upload.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"File is larger than {MAX_BYTES // (1024 * 1024)} MB")
    if not data:
        raise HTTPException(400, f"{upload.filename or 'File'} is empty")
    return data


def _safe_name(name: str, default: str = "document") -> str:
    stem = re.sub(r"[^\w.\- ]+", "_", Path(name or default).stem).strip() or default
    return stem[:120]


def _download(data: bytes, filename: str, media: str) -> Response:
    ascii_name = filename.encode("ascii", "replace").decode().replace('"', "")
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{ascii_name}"'})


def _pages(doc: pymupdf.Document, body: dict, key: str = "pages") -> list[int] | None:
    """Accept a list of 0-based indexes or a 1-based range string."""
    v = body.get(key)
    if v is None or v == "":
        return None
    if isinstance(v, list):
        for p in v:
            core.get_page(doc, int(p))
        return [int(p) for p in v]
    return core.parse_page_ranges(str(v), doc.page_count)


def _all_pages(doc, body, key="pages") -> list[int]:
    p = _pages(doc, body, key)
    return list(range(doc.page_count)) if p is None else p


def _patterns(body: dict):
    return core.build_patterns(
        terms=body.get("terms") or [],
        regexes=body.get("regexes") or [],
        presets=body.get("presets") or [],
        case_sensitive=bool(body.get("case_sensitive")),
        whole_word=bool(body.get("whole_word")),
    )


_REDACT_KW = ("fill", "overlay_text", "remove_images", "remove_graphics")


def _redact_kw(body: dict) -> dict:
    return {k: body[k] for k in _REDACT_KW if k in body}


# --------------------------------------------------------------------------
# operation table: name -> (history label, fn(doc, body) -> result)
# --------------------------------------------------------------------------

OPS: dict[str, tuple[str | Callable[[dict], str], Callable[[pymupdf.Document, dict], Any]]] = {
    "edit_text": (
        "Edit text",
        lambda d, b: core.edit_text(
            d, int(b["page"]), b["bbox"], b.get("text", ""),
            fontsize=b.get("fontsize"), color=b.get("color"), family=b.get("family"), bold=b.get("bold"), italic=b.get("italic"),
        ),
    ),
    "add_text": (
        "Add text",
        lambda d, b: core.add_text(
            d, int(b["page"]), b["rect"], b.get("text", ""),
            fontsize=float(b.get("fontsize") or 12), color=b.get("color") or "#000000", family=b.get("family") or "sans",
            bold=bool(b.get("bold")), italic=bool(b.get("italic")), align=b.get("align") or "left",
        ),
    ),
    "annotate": (
        lambda b: f"Add {b.get('kind', 'comment')}",
        lambda d, b: core.add_annotation(d, int(b["page"]), b["kind"], **{k: v for k, v in b.items() if k not in ("page", "kind")}),
    ),
    "delete_annotation": ("Delete comment", lambda d, b: core.delete_annotation(d, int(b["page"]), int(b["xref"]))),
    "flatten": ("Flatten", lambda d, b: core.flatten(d, annots=b.get("annots", True), widgets=b.get("widgets", True))),
    "redact_areas": ("Redact", lambda d, b: core.redact(d, b["areas"], **_redact_kw(b))),
    "redact_search": ("Redact matches", lambda d, b: core.redact_matches(d, _patterns(b), _pages(d, b), **_redact_kw(b))),
    "sanitize": (
        "Sanitize",
        lambda d, b: core.sanitize(d, **{k: bool(v) for k, v in b.items() if k in ("metadata", "javascript", "attachments", "links", "hidden_text", "thumbnails", "reset_forms")}),
    ),
    "rotate": ("Rotate pages", lambda d, b: core.rotate_pages(d, _all_pages(d, b), int(b.get("angle", 90)))),
    "delete_pages": ("Delete pages", lambda d, b: core.delete_pages(d, _all_pages(d, b))),
    "reorder": ("Reorder pages", lambda d, b: core.reorder_pages(d, [int(i) for i in b["order"]])),
    "move_page": ("Move page", lambda d, b: core.move_page(d, int(b["from"]), int(b["to"]))),
    "insert_blank": ("Insert page", lambda d, b: core.insert_blank_page(d, int(b.get("at", d.page_count)), b.get("width"), b.get("height"))),
    "crop": ("Crop", lambda d, b: core.crop_pages(d, _all_pages(d, b), b["rect"])),
    "watermark": (
        "Watermark",
        lambda d, b: core.watermark(
            d, b.get("text", ""), pages=_pages(d, b), fontsize=float(b.get("fontsize") or 60), color=b.get("color") or "#ff0000",
            opacity=float(b.get("opacity", 0.25)), angle=float(b.get("angle", 45)), family=b.get("family") or "sans", behind=bool(b.get("behind")),
        ),
    ),
    "header_footer": (
        "Header & footer",
        lambda d, b: core.stamp_header_footer(
            d, pages=_pages(d, b), **{k: v for k, v in b.items() if k not in ("pages",)}
        ),
    ),
    "fill_form": ("Fill form", lambda d, b: core.fill_fields(d, b.get("values") or {})),
    "add_field": (
        "Add form field",
        lambda d, b: core.add_field(d, int(b["page"]), b["kind"], b["rect"], b.get("name", ""), value=b.get("value", ""), options=b.get("options")),
    ),
    "metadata": ("Edit properties", lambda d, b: core.set_metadata(d, b)),
    "bookmarks": ("Edit bookmarks", lambda d, b: core.set_bookmarks(d, b.get("toc") or [])),
    "optimize": (
        "Optimize",
        lambda d, b: core.optimize(d, image_dpi=b.get("image_dpi", 150), image_quality=int(b.get("image_quality", 75)), subset_fonts=b.get("subset_fonts", True)),
    ),
    "ocr": ("OCR", lambda d, b: core.ocr(d, _pages(d, b), language=b.get("language") or "eng", skip_text_pages=b.get("skip_text_pages", True))),
}


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------


@app.get("/api/capabilities")
def capabilities():
    return {
        "version": __version__,
        "brand": brand.as_dict(),
        "ocr": core.ocr_available(),
        "presets": {k: v[0] for k, v in core.REDACTION_PRESETS.items()},
        "ops": sorted(OPS),
        "max_mb": MAX_BYTES // (1024 * 1024),
    }


@app.post("/api/documents")
async def open_document(file: UploadFile = File(...), password: str | None = Form(None)):
    data = await _read(file)
    sess = store.create(data, file.filename or "document.pdf", password)
    return _snapshot(sess)


@app.post("/api/documents/blank")
def new_blank(body: dict = Body(default={})):
    size = body.get("size", "a4")
    w, h = pymupdf.paper_size(size if size else "a4")
    doc = pymupdf.open()
    for _ in range(max(1, int(body.get("pages", 1)))):
        doc.new_page(width=w, height=h)
    sess = store.create(doc.tobytes(), body.get("filename") or "Untitled.pdf")
    return _snapshot(sess)


@app.post("/api/documents/from-images")
async def from_images(files: list[UploadFile] = File(...), page_size: str | None = Form(None)):
    images = [(f.filename or "image", await _read(f)) for f in files]
    pdf = core.images_to_pdf(images, page_size or None)
    sess = store.create(pdf, f"{_safe_name(images[0][0])}.pdf")
    return _snapshot(sess)


@app.get("/api/documents/{sid}")
def get_document(sid: str):
    return _snapshot(_session(sid))


@app.delete("/api/documents/{sid}")
def close_document(sid: str):
    store.delete(sid)
    return {"ok": True}


@app.get("/api/documents/{sid}/pages/{n}/image")
def page_image(sid: str, n: int, scale: float = Query(1.5, gt=0, le=6), annots: bool = True):
    sess = _session(sid)
    with sess.lock:
        png = core.render_page(sess.doc(), n, scale, annots=annots)
    # the version query param makes URLs unique per state, so cache aggressively
    return Response(png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/documents/{sid}/pages/{n}/text")
def page_text(sid: str, n: int):
    sess = _session(sid)
    with sess.lock:
        return {"page": n, "lines": core.text_lines(sess.doc(), n)}


@app.get("/api/documents/{sid}/annotations")
def annotations(sid: str):
    sess = _session(sid)
    with sess.lock:
        return {"annotations": core.list_annotations(sess.doc())}


@app.get("/api/documents/{sid}/fields")
def fields(sid: str):
    sess = _session(sid)
    with sess.lock:
        return {"fields": core.list_fields(sess.doc())}


@app.get("/api/documents/{sid}/search")
def search(sid: str, q: str, case_sensitive: bool = False, whole_word: bool = False):
    sess = _session(sid)
    with sess.lock:
        return {"matches": core.search_text(sess.doc(), q, case_sensitive, whole_word)}


@app.post("/api/documents/{sid}/redact/preview")
def redact_preview(sid: str, body: dict = Body(...)):
    sess = _session(sid)
    pats = _patterns(body)
    with sess.lock:
        doc = sess.doc()
        return {"matches": core.find_matches(doc, pats, _pages(doc, body))}


@app.post("/api/documents/{sid}/undo")
def undo(sid: str):
    _session(sid)
    return _snapshot(store.undo(sid))


@app.post("/api/documents/{sid}/redo")
def redo(sid: str):
    _session(sid)
    return _snapshot(store.redo(sid))


@app.post("/api/documents/{sid}/ops/{name}")
def run_op(sid: str, name: str, body: dict = Body(default={})):
    sess = _session(sid)
    if name not in OPS:
        raise HTTPException(404, f"Unknown operation: {name}")
    label, fn = OPS[name]
    label = label(body) if callable(label) else label
    try:
        result = store.apply(sid, label, lambda d: fn(d, body))
    except (KeyError, TypeError) as e:
        raise HTTPException(400, f"Missing or invalid parameter: {e}") from e
    return _snapshot(sess, result)


@app.post("/api/documents/{sid}/insert")
async def insert_document(sid: str, file: UploadFile = File(...), at: int | None = Form(None), password: str | None = Form(None), pages: str | None = Form(None)):
    sess = _session(sid)
    data = await _read(file)
    added = store.apply(sid, f"Insert {file.filename or 'file'}", lambda d: core.insert_pdf(d, data, at, password, pages))
    return _snapshot(sess, {"added": added})


@app.post("/api/documents/{sid}/image")
async def insert_image(sid: str, file: UploadFile = File(...), page: int = Form(...), rect: str = Form(...), keep_proportion: bool = Form(True)):
    sess = _session(sid)
    data = await _read(file)
    try:
        r = json.loads(rect)
    except json.JSONDecodeError as e:
        raise HTTPException(400, "rect must be a JSON array") from e
    store.apply(sid, "Add image", lambda d: core.add_image(d, page, r, data, keep_proportion))
    return _snapshot(sess)


@app.post("/api/documents/{sid}/compare")
async def compare_with(sid: str, file: UploadFile = File(...), password: str | None = Form(None)):
    sess = _session(sid)
    other = core.open_bytes(await _read(file), password)
    try:
        with sess.lock:
            return core.compare(sess.doc(), other)
    finally:
        other.close()


@app.api_route("/api/documents/{sid}/download", methods=["GET", "POST"])
def download(sid: str, body: dict | None = Body(default=None)):
    sess = _session(sid)
    body = body or {}
    with sess.lock:
        data = core.save_bytes(
            sess.doc(),
            user_password=body.get("user_password") or None,
            owner_password=body.get("owner_password") or None,
            permissions=body.get("permissions"),
            compress=bool(body.get("compress")),
        )
    name = _safe_name(body.get("filename") or sess.filename)
    return _download(data, f"{name}.pdf", "application/pdf")


@app.post("/api/documents/{sid}/export/{kind}")
def export(sid: str, kind: str, body: dict = Body(default={})):
    sess = _session(sid)
    name = _safe_name(sess.filename)
    with sess.lock:
        doc = sess.doc()
        if kind == "images":
            fmt = body.get("format", "png")
            data = core.export_images(doc, _pages(doc, body), int(body.get("dpi", 150)), fmt, name)
            return _download(data, f"{name}-images.zip", "application/zip")
        if kind == "text":
            return _download(core.export_text(doc, "txt").encode(), f"{name}.txt", "text/plain; charset=utf-8")
        if kind == "html":
            return _download(core.export_text(doc, "html").encode(), f"{name}.html", "text/html; charset=utf-8")
        if kind == "extract":
            pages = _pages(doc, body)
            if not pages:
                raise HTTPException(400, "Choose pages to extract")
            return _download(core.extract_pages(doc, pages), f"{name}-extract.pdf", "application/pdf")
        if kind == "split":
            data = core.split(doc, every=body.get("every"), ranges=body.get("ranges"), basename=name)
            return _download(data, f"{name}-split.zip", "application/zip")
    raise HTTPException(404, f"Unknown export: {kind}")


# --------------------------------------------------------------------------
# static UI
# --------------------------------------------------------------------------


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
