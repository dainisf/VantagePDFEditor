import io
import re
import zipfile

import pymupdf
import pytest

from pdfscout import core


@pytest.fixture
def doc():
    d = pymupdf.open()
    p = d.new_page()
    p.insert_text((72, 100), "Contact: john.doe@acme.com or 555-123-4567", fontsize=12)
    p.insert_text((72, 130), "Invoice total 1,200 USD", fontsize=14, fontname="tibo")
    p.insert_text((72, 160), "SSN 123-45-6789", fontsize=12)
    p2 = d.new_page()
    p2.insert_text((72, 100), "Second page text", fontsize=12)
    p3 = d.new_page()
    p3.insert_text((72, 100), "Rotated page", fontsize=12)
    p3.set_rotation(90)
    return d


def reopen(d):
    return pymupdf.open("pdf", core.save_bytes(d))


def raw_contains(d, needle: bytes) -> bool:
    """Search every decompressed stream in the saved file."""
    data = pymupdf.open("pdf", core.save_bytes(d)).tobytes(expand=255, garbage=4)
    return needle in data


def test_parse_page_ranges():
    assert core.parse_page_ranges("1-3,5", 6) == [0, 1, 2, 4]
    assert core.parse_page_ranges("4-", 6) == [3, 4, 5]
    assert core.parse_page_ranges("", 3) == [0, 1, 2]
    with pytest.raises(core.PDFScoutError):
        core.parse_page_ranges("7", 6)
    with pytest.raises(core.PDFScoutError):
        core.parse_page_ranges("abc", 6)


def test_redaction_removes_content_from_file(doc):
    pats = core.build_patterns(presets=["email", "phone", "ssn"])
    matches = core.find_matches(doc, pats)
    assert {m["text"] for m in matches} == {"john.doe@acme.com", "555-123-4567", "123-45-6789"}
    core.redact_matches(doc, pats)
    d = reopen(doc)
    text = d[0].get_text()
    assert "acme" not in text and "555" not in text and "6789" not in text
    assert "Invoice total" in text  # unrelated text kept
    assert not raw_contains(d, b"acme")


def test_area_redaction_and_overlay(doc):
    line = next(l for l in core.text_lines(doc, 0) if "Invoice" in l["text"])
    core.redact(doc, [{"page": 0, "rect": line["bbox"]}], overlay_text="REDACTED")
    text = reopen(doc)[0].get_text()
    assert "Invoice" not in text


def test_redaction_on_rotated_page(doc):
    line = core.text_lines(doc, 2)[0]
    core.redact(doc, [{"page": 2, "rect": line["bbox"]}])
    assert "Rotated" not in reopen(doc)[2].get_text()


def test_term_search_case_and_whole_word(doc):
    assert len(core.find_matches(doc, core.build_patterns(["invoice"]))) == 1
    assert len(core.find_matches(doc, core.build_patterns(["invoice"], case_sensitive=True))) == 0
    assert len(core.find_matches(doc, core.build_patterns(["Invo"], whole_word=True))) == 0
    with pytest.raises(core.PDFScoutError):
        core.build_patterns([])
    with pytest.raises(core.PDFScoutError):
        core.build_patterns(regexes=["("])


def test_edit_text_replaces_line(doc):
    line = next(l for l in core.text_lines(doc, 0) if "Invoice" in l["text"])
    assert line["family"] == "serif" and line["bold"]
    core.edit_text(doc, 0, line["bbox"], "Invoice total 9,999 EUR")
    texts = [l["text"] for l in core.text_lines(doc, 0)]
    assert "Invoice total 9,999 EUR" in texts
    assert not any("1,200" in t for t in texts)
    assert any("Contact" in t for t in texts)  # neighbouring lines intact


def test_edit_text_on_rotated_page(doc):
    line = core.text_lines(doc, 2)[0]
    core.edit_text(doc, 2, line["bbox"], "Changed")
    assert [l["text"] for l in core.text_lines(doc, 2)] == ["Changed"]


def test_add_text_rotated_page_is_upright(doc):
    core.add_text(doc, 2, [50, 50, 300, 80], "Upright")
    line = next(l for l in core.text_lines(doc, 2) if l["text"] == "Upright")
    assert line["dir"] == [1.0, 0.0]
    assert line["bbox"][0] == pytest.approx(50, abs=2)


def test_annotations_roundtrip(doc):
    core.add_annotation(doc, 0, "highlight", rect=[60, 115, 300, 140])
    core.add_annotation(doc, 0, "note", point=[300, 300], text="Check this")
    core.add_annotation(doc, 0, "arrow", start=[10, 10], end=[100, 100], color="#00ff00")
    core.add_annotation(doc, 0, "ink", strokes=[[[1, 1], [50, 50]]])
    core.add_annotation(doc, 0, "rect", rect=[10, 10, 40, 40], fill="#ff0000")
    core.add_annotation(doc, 0, "freetext", rect=[100, 400, 300, 440], text="Free")
    annots = core.list_annotations(doc)
    assert [a["type"] for a in annots] == ["Highlight", "Text", "Line", "Ink", "Square", "FreeText"]
    core.delete_annotation(doc, 0, annots[0]["xref"])
    assert len(core.list_annotations(doc)) == 5
    core.flatten(doc)
    assert core.list_annotations(doc) == []
    with pytest.raises(core.PDFScoutError):
        core.add_annotation(doc, 0, "bogus")


def test_page_operations(doc):
    core.rotate_pages(doc, [0], 90)
    assert doc[0].rotation == 90
    core.move_page(doc, 2, 0)
    assert "Rotated" in doc[0].get_text()
    core.reorder_pages(doc, [0, 0, 1, 2])
    assert doc.page_count == 4
    core.delete_pages(doc, [0])
    assert doc.page_count == 3
    core.insert_blank_page(doc, 1)
    assert doc.page_count == 4 and not doc[1].get_text().strip()
    with pytest.raises(core.PDFScoutError):
        core.delete_pages(doc, list(range(doc.page_count)))


def test_merge_split_extract(doc):
    other = pymupdf.open()
    other.new_page().insert_text((72, 72), "Other doc")
    added = core.insert_pdf(doc, other.tobytes(), at=1)
    assert added == 1 and "Other doc" in doc[1].get_text()
    z = zipfile.ZipFile(io.BytesIO(core.split(doc, every=2)))
    assert len(z.namelist()) == 2
    z = zipfile.ZipFile(io.BytesIO(core.split(doc, ranges="1; 2-4")))
    assert [pymupdf.open("pdf", z.read(n)).page_count for n in sorted(z.namelist())] == [1, 3]
    assert pymupdf.open("pdf", core.extract_pages(doc, [3])).page_count == 1


def test_crop(doc):
    core.crop_pages(doc, [0], [50, 50, 400, 500])
    assert doc[0].rect.width == pytest.approx(350)
    core.crop_pages(doc, [0], [10, 10, 100, 100])  # crop again, relative to current view
    assert doc[0].rect.width == pytest.approx(90)


def test_watermark_and_header_footer(doc):
    core.watermark(doc, "DRAFT", opacity=0.3)
    core.stamp_header_footer(doc, footer_center="Page {page} of {total}", header_right="{bates}", bates_prefix="ABC", bates_digits=4)
    texts = [l["text"] for l in core.text_lines(doc, 1)]
    assert "DRAFT" in texts and "Page 2 of 3" in texts and "ABC0002" in texts
    with pytest.raises(core.PDFScoutError):
        core.stamp_header_footer(doc, footer_center="{nope}")


def test_forms(doc):
    core.add_field(doc, 0, "text", [72, 500, 300, 520], "name")
    core.add_field(doc, 0, "checkbox", [72, 530, 90, 548], "agree")
    core.add_field(doc, 0, "combobox", [72, 560, 200, 580], "color", options=["red", "blue"])
    assert core.fill_fields(doc, {"name": "Alice", "agree": True, "color": "blue"}) == 3
    fields = {f["name"]: f for f in core.list_fields(reopen(doc))}
    assert fields["name"]["value"] == "Alice"
    assert fields["agree"]["value"] not in ("Off", "", False)
    assert fields["color"]["value"] == "blue"
    core.flatten(doc, annots=False)
    assert core.list_fields(doc) == []
    assert "Alice" in doc[0].get_text()


def test_encryption_roundtrip(doc):
    data = core.save_bytes(doc, user_password="secret", permissions=["print"])
    with pytest.raises(core.PDFScoutError, match="Password required"):
        core.open_bytes(data)
    with pytest.raises(core.PDFScoutError, match="Incorrect"):
        core.open_bytes(data, "wrong")
    assert core.open_bytes(data, "secret").page_count == 3


def test_sanitize_and_metadata(doc):
    core.set_metadata(doc, {"title": "Secret plan", "author": "Jane"})
    assert reopen(doc).metadata["author"] == "Jane"
    doc.embfile_add("a.txt", b"hidden")
    core.sanitize(doc)
    d = reopen(doc)
    assert d.metadata["author"] == "" and d.embfile_count() == 0


def test_bookmarks(doc):
    core.set_bookmarks(doc, [[1, "Intro", 1], [2, "Detail", 2]])
    assert doc.get_toc() == [[1, "Intro", 1], [2, "Detail", 2]]
    with pytest.raises(core.PDFScoutError):
        core.set_bookmarks(doc, [[1, "Bad", 99]])


def test_optimize_and_exports(doc):
    core.optimize(doc)
    assert core.save_bytes(doc, compress=True).startswith(b"%PDF")
    z = zipfile.ZipFile(io.BytesIO(core.export_images(doc, dpi=50)))
    assert len(z.namelist()) == 3
    assert "Second page text" in core.export_text(doc)
    assert core.render_page(doc, 0, 0.5)[:4] == b"\x89PNG"


def test_images_to_pdf():
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 20), False)
    pix.clear_with(200)
    pdf = core.images_to_pdf([("a.png", pix.tobytes("png")), ("b.png", pix.tobytes("png"))])
    d = pymupdf.open("pdf", pdf)
    assert d.page_count == 2 and d[0].rect.width == pytest.approx(30)  # 40px @ 96dpi


def test_compare(doc):
    other = pymupdf.open("pdf", core.save_bytes(doc))
    assert core.compare(doc, other)["identical"]
    line = core.text_lines(other, 1)[0]
    core.edit_text(other, 1, line["bbox"], "Second page CHANGED")
    res = core.compare(doc, other)
    assert not res["identical"] and res["pages"][0]["page"] == 1


def test_color_parsing():
    assert core.hex_to_rgb("#ff0000") == (1.0, 0.0, 0.0)
    assert core.hex_to_rgb("0f0") == (0.0, 1.0, 0.0)
    with pytest.raises(core.PDFScoutError):
        core.hex_to_rgb("nope")


def test_presets_compile():
    for key, (_, pattern) in core.REDACTION_PRESETS.items():
        re.compile(pattern)
