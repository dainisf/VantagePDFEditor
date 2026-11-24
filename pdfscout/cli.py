"""Command-line interface for scripted / batch PDF work.

Examples::

    pdfscout serve
    pdfscout redact in.pdf -o out.pdf --preset email --preset phone --term "Jane Doe"
    pdfscout merge a.pdf b.pdf c.pdf -o merged.pdf
    pdfscout split big.pdf --every 10 -o parts.zip
    pdfscout protect in.pdf -o locked.pdf --password secret --allow print
    pdfscout watermark in.pdf -o draft.pdf --text DRAFT
    pdfscout number in.pdf -o numbered.pdf --footer "Page {page} of {total}"
    pdfscout bates in.pdf -o bates.pdf --prefix ACME --start 1
    pdfscout compress in.pdf -o small.pdf --dpi 120
    pdfscout sanitize in.pdf -o clean.pdf
    pdfscout info in.pdf
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, core


def _open(path: str, password: str | None):
    return core.open_bytes(Path(path).read_bytes(), password)


def _write(path: str, data: bytes) -> None:
    Path(path).write_bytes(data)
    print(f"wrote {path} ({len(data) / 1024:.0f} KB)")


def _pages(doc, spec):
    return None if not spec else core.parse_page_ranges(spec, doc.page_count)


def cmd_serve(a):
    import uvicorn

    from .server import app

    print(f"PDFScout running at http://{a.host}:{a.port}")
    uvicorn.run(app, host=a.host, port=a.port)


def cmd_info(a):
    doc = _open(a.input, a.password)
    info = core.document_info(doc)
    info.pop("pages")
    info["fields"] = len(core.list_fields(doc))
    info["annotations"] = len(core.list_annotations(doc))
    print(json.dumps(info, indent=2, ensure_ascii=False))


def cmd_redact(a):
    doc = _open(a.input, a.password)
    pats = core.build_patterns(a.term or [], a.regex or [], a.preset or [], case_sensitive=a.case_sensitive, whole_word=a.whole_word)
    if a.dry_run:
        for m in core.find_matches(doc, pats, _pages(doc, a.pages)):
            print(f"page {m['page'] + 1}: {m['text']}")
        return
    n = core.redact_matches(doc, pats, _pages(doc, a.pages), fill=a.fill or None, overlay_text=a.overlay)
    if not a.keep_metadata:
        core.sanitize(doc)
    print(f"redacted {n} match(es)")
    _write(a.output, core.save_bytes(doc, compress=True))


def cmd_merge(a):
    doc = _open(a.inputs[0], a.password)
    for p in a.inputs[1:]:
        core.insert_pdf(doc, Path(p).read_bytes())
    _write(a.output, core.save_bytes(doc))


def cmd_split(a):
    doc = _open(a.input, a.password)
    _write(a.output, core.split(doc, every=a.every, ranges=a.ranges, basename=Path(a.input).stem))


def cmd_extract(a):
    doc = _open(a.input, a.password)
    _write(a.output, core.extract_pages(doc, core.parse_page_ranges(a.pages, doc.page_count)))


def cmd_rotate(a):
    doc = _open(a.input, a.password)
    core.rotate_pages(doc, core.parse_page_ranges(a.pages, doc.page_count), a.angle)
    _write(a.output, core.save_bytes(doc))


def cmd_delete(a):
    doc = _open(a.input, a.password)
    core.delete_pages(doc, core.parse_page_ranges(a.pages, doc.page_count))
    _write(a.output, core.save_bytes(doc))


def cmd_protect(a):
    doc = _open(a.input, a.password)
    _write(a.output, core.save_bytes(doc, user_password=a.new_password, owner_password=a.owner_password, permissions=a.allow or []))


def cmd_unlock(a):
    doc = _open(a.input, a.password)
    _write(a.output, core.save_bytes(doc))


def cmd_watermark(a):
    doc = _open(a.input, a.password)
    core.watermark(doc, a.text, pages=_pages(doc, a.pages), fontsize=a.size, color=a.color, opacity=a.opacity, angle=a.angle)
    _write(a.output, core.save_bytes(doc))


def cmd_number(a):
    doc = _open(a.input, a.password)
    core.stamp_header_footer(doc, pages=_pages(doc, a.pages), header_center=a.header or "", footer_center=a.footer, fontsize=a.size, filename=Path(a.input).name)
    _write(a.output, core.save_bytes(doc))


def cmd_bates(a):
    doc = _open(a.input, a.password)
    core.stamp_header_footer(doc, footer_right="{bates}", bates_prefix=a.prefix, bates_suffix=a.suffix, bates_start=a.start, bates_digits=a.digits, fontsize=a.size)
    _write(a.output, core.save_bytes(doc))


def cmd_compress(a):
    doc = _open(a.input, a.password)
    before = Path(a.input).stat().st_size
    core.optimize(doc, image_dpi=a.dpi or None, image_quality=a.quality)
    data = core.save_bytes(doc, compress=True)
    print(f"{before / 1024:.0f} KB -> {len(data) / 1024:.0f} KB")
    _write(a.output, data)


def cmd_sanitize(a):
    doc = _open(a.input, a.password)
    core.sanitize(doc, links=a.links)
    _write(a.output, core.save_bytes(doc))


def cmd_flatten(a):
    doc = _open(a.input, a.password)
    core.flatten(doc)
    _write(a.output, core.save_bytes(doc))


def cmd_fill(a):
    doc = _open(a.input, a.password)
    values = json.loads(Path(a.values).read_text()) if Path(a.values).exists() else json.loads(a.values)
    n = core.fill_fields(doc, values)
    if a.flatten:
        core.flatten(doc, annots=False)
    print(f"filled {n} field(s)")
    _write(a.output, core.save_bytes(doc))


def cmd_ocr(a):
    doc = _open(a.input, a.password)
    n = core.ocr(doc, _pages(doc, a.pages), language=a.lang)
    print(f"OCR'd {n} page(s)")
    _write(a.output, core.save_bytes(doc))


def cmd_images(a):
    images = [(p, Path(p).read_bytes()) for p in a.inputs]
    _write(a.output, core.images_to_pdf(images, a.page_size))


def cmd_text(a):
    doc = _open(a.input, a.password)
    out = core.export_text(doc, a.format)
    if a.output:
        Path(a.output).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)


def cmd_compare(a):
    r = core.compare(_open(a.a, None), _open(a.b, None))
    if r["identical"]:
        print("No text differences.")
        return
    for p in r["pages"]:
        print(f"--- page {p['page'] + 1}")
        for c in p["changes"]:
            for line in c["old"]:
                print(f"- {line}")
            for line in c["new"]:
                print(f"+ {line}")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="pdfscout", description="PDFScout PDF editor")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_, io=True, out=True):
        p = sub.add_parser(name, help=help_)
        if io:
            p.add_argument("input")
        if out:
            p.add_argument("-o", "--output", required=True)
        p.add_argument("--password", help="password of the input file")
        p.set_defaults(fn=fn)
        return p

    p = sub.add_parser("serve", help="run the web editor")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(fn=cmd_serve)

    add("info", cmd_info, "show document information", out=False)

    p = add("redact", cmd_redact, "find & permanently redact text")
    p.add_argument("--term", action="append", help="literal text (repeatable)")
    p.add_argument("--regex", action="append", help="regular expression (repeatable)")
    p.add_argument("--preset", action="append", choices=sorted(core.REDACTION_PRESETS))
    p.add_argument("--pages")
    p.add_argument("--case-sensitive", action="store_true")
    p.add_argument("--whole-word", action="store_true")
    p.add_argument("--fill", default="#000000", help="box color, '' for none")
    p.add_argument("--overlay", help="text printed on each box")
    p.add_argument("--keep-metadata", action="store_true", help="don't sanitize the document afterwards")
    p.add_argument("--dry-run", action="store_true", help="only list matches")
    p.set_defaults(output="-")
    for act in p._actions:
        if act.dest == "output":
            act.required = False

    p = sub.add_parser("merge", help="combine files")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--password")
    p.set_defaults(fn=cmd_merge)

    p = add("split", cmd_split, "split into a zip of PDFs")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--every", type=int)
    g.add_argument("--ranges", help="e.g. '1-3; 4-6; 7-'")

    p = add("extract", cmd_extract, "extract pages to a new PDF")
    p.add_argument("--pages", required=True)
    p = add("rotate", cmd_rotate, "rotate pages")
    p.add_argument("--pages", default="all")
    p.add_argument("--angle", type=int, default=90)
    p = add("delete", cmd_delete, "delete pages")
    p.add_argument("--pages", required=True)

    p = add("protect", cmd_protect, "encrypt with a password (AES-256)")
    p.add_argument("--new-password", "--set-password", dest="new_password", required=True)
    p.add_argument("--owner-password")
    p.add_argument("--allow", action="append", choices=sorted(core.PERMISSIONS))
    add("unlock", cmd_unlock, "remove password protection (needs --password)")

    p = add("watermark", cmd_watermark, "add a text watermark")
    p.add_argument("--text", required=True)
    p.add_argument("--size", type=float, default=60)
    p.add_argument("--color", default="#ff0000")
    p.add_argument("--opacity", type=float, default=0.25)
    p.add_argument("--angle", type=float, default=45)
    p.add_argument("--pages")

    p = add("number", cmd_number, "add page numbers / header & footer")
    p.add_argument("--footer", default="Page {page} of {total}")
    p.add_argument("--header")
    p.add_argument("--size", type=float, default=10)
    p.add_argument("--pages")

    p = add("bates", cmd_bates, "add Bates numbers")
    p.add_argument("--prefix", default="")
    p.add_argument("--suffix", default="")
    p.add_argument("--start", type=int, default=1)
    p.add_argument("--digits", type=int, default=6)
    p.add_argument("--size", type=float, default=10)

    p = add("compress", cmd_compress, "reduce file size")
    p.add_argument("--dpi", type=int, default=150, help="image target dpi, 0 to keep images")
    p.add_argument("--quality", type=int, default=75)

    p = add("sanitize", cmd_sanitize, "remove metadata, scripts, attachments, hidden text")
    p.add_argument("--links", action="store_true", help="also remove links")
    add("flatten", cmd_flatten, "burn annotations and form fields into the page")

    p = add("fill", cmd_fill, "fill form fields from JSON")
    p.add_argument("--values", required=True, help="JSON file or JSON string {field: value}")
    p.add_argument("--flatten", action="store_true")

    p = add("ocr", cmd_ocr, "add a searchable text layer (needs tesseract)")
    p.add_argument("--lang", default="eng")
    p.add_argument("--pages")

    p = sub.add_parser("images", help="create a PDF from images")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--page-size", help="e.g. a4, letter (default: image size)")
    p.set_defaults(fn=cmd_images)

    p = add("text", cmd_text, "extract text", out=False)
    p.add_argument("-o", "--output")
    p.add_argument("--format", choices=["txt", "html"], default="txt")

    p = sub.add_parser("compare", help="compare the text of two PDFs")
    p.add_argument("a")
    p.add_argument("b")
    p.set_defaults(fn=cmd_compare)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "redact" and not args.dry_run and args.output == "-":
        print("redact: -o/--output is required (or use --dry-run)", file=sys.stderr)
        return 2
    try:
        args.fn(args)
    except core.PDFScoutError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
