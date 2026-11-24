import io
import json
import zipfile

import pymupdf
import pytest
from fastapi.testclient import TestClient

from pdfscout import core
from pdfscout.server import app


@pytest.fixture
def client():
    return TestClient(app)


def make_pdf(text="Hello john@acme.com", pages=2) -> bytes:
    d = pymupdf.open()
    for i in range(pages):
        d.new_page().insert_text((72, 100), f"{text} p{i + 1}", fontsize=12)
    return d.tobytes()


@pytest.fixture
def sid(client):
    r = client.post("/api/documents", files={"file": ("test.pdf", make_pdf(), "application/pdf")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["page_count"] == 2 and body["version"] == 0 and not body["can_undo"]
    return body["id"]


def download(client, sid, **body):
    r = client.post(f"/api/documents/{sid}/download", json=body)
    assert r.status_code == 200
    return r.content


def test_index_and_capabilities(client):
    assert "PDFScout" in client.get("/").text
    caps = client.get("/api/capabilities").json()
    assert "email" in caps["presets"] and "redact_areas" in caps["ops"]


def test_render_and_text(client, sid):
    r = client.get(f"/api/documents/{sid}/pages/0/image?scale=0.5")
    assert r.status_code == 200 and r.content[:4] == b"\x89PNG"
    lines = client.get(f"/api/documents/{sid}/pages/0/text").json()["lines"]
    assert lines[0]["text"].startswith("Hello")
    assert client.get(f"/api/documents/{sid}/pages/9/image").status_code == 400


def test_edit_undo_redo(client, sid):
    lines = client.get(f"/api/documents/{sid}/pages/0/text").json()["lines"]
    r = client.post(f"/api/documents/{sid}/ops/edit_text", json={"page": 0, "bbox": lines[0]["bbox"], "text": "Goodbye"})
    assert r.status_code == 200, r.text
    assert r.json()["can_undo"] and r.json()["undo_label"] == "Edit text"
    texts = [l["text"] for l in client.get(f"/api/documents/{sid}/pages/0/text").json()["lines"]]
    assert texts == ["Goodbye"]
    client.post(f"/api/documents/{sid}/undo")
    texts = [l["text"] for l in client.get(f"/api/documents/{sid}/pages/0/text").json()["lines"]]
    assert texts[0].startswith("Hello")
    r = client.post(f"/api/documents/{sid}/redo").json()
    assert r["version"] == 1 and not r["can_redo"]


def test_search_and_redact(client, sid):
    m = client.post(f"/api/documents/{sid}/redact/preview", json={"presets": ["email"]}).json()["matches"]
    assert len(m) == 2
    r = client.post(f"/api/documents/{sid}/ops/redact_search", json={"presets": ["email"]})
    assert r.json()["result"] == 2
    pdf = pymupdf.open("pdf", download(client, sid))
    assert all("acme" not in p.get_text() for p in pdf)
    assert client.get(f"/api/documents/{sid}/search", params={"q": "acme"}).json()["matches"] == []


def test_redact_areas(client, sid):
    lines = client.get(f"/api/documents/{sid}/pages/1/text").json()["lines"]
    r = client.post(f"/api/documents/{sid}/ops/redact_areas", json={"areas": [{"page": 1, "rect": lines[0]["bbox"]}]})
    assert r.status_code == 200
    pdf = pymupdf.open("pdf", download(client, sid))
    assert pdf[1].get_text().strip() == ""


def test_page_ops_and_merge(client, sid):
    assert client.post(f"/api/documents/{sid}/ops/rotate", json={"pages": [0], "angle": 90}).json()["pages"][0]["rotation"] == 90
    r = client.post(f"/api/documents/{sid}/insert", files={"file": ("b.pdf", make_pdf("Other", 3), "application/pdf")}, data={"at": "1"})
    assert r.json()["page_count"] == 5 and r.json()["result"]["added"] == 3
    r = client.post(f"/api/documents/{sid}/ops/delete_pages", json={"pages": "2-4"})
    assert r.json()["page_count"] == 2
    r = client.post(f"/api/documents/{sid}/ops/move_page", json={"from": 1, "to": 0})
    assert r.status_code == 200


def test_split_extract_export(client, sid):
    r = client.post(f"/api/documents/{sid}/export/split", json={"every": 1})
    assert len(zipfile.ZipFile(io.BytesIO(r.content)).namelist()) == 2
    r = client.post(f"/api/documents/{sid}/export/extract", json={"pages": "2"})
    assert pymupdf.open("pdf", r.content).page_count == 1
    r = client.post(f"/api/documents/{sid}/export/images", json={"dpi": 40})
    assert len(zipfile.ZipFile(io.BytesIO(r.content)).namelist()) == 2
    r = client.post(f"/api/documents/{sid}/export/text")
    assert "Hello" in r.text


def test_add_image(client, sid):
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 10, 10), False)
    r = client.post(
        f"/api/documents/{sid}/image",
        files={"file": ("x.png", pix.tobytes("png"), "image/png")},
        data={"page": "0", "rect": json.dumps([10, 10, 60, 60])},
    )
    assert r.status_code == 200, r.text
    pdf = pymupdf.open("pdf", download(client, sid))
    assert len(pdf[0].get_images()) == 1


def test_password_protect_and_open(client, sid):
    data = download(client, sid, user_password="pw", permissions=["print"])
    r = client.post("/api/documents", files={"file": ("p.pdf", data, "application/pdf")})
    assert r.status_code == 400 and "Password" in r.json()["detail"]
    r = client.post("/api/documents", files={"file": ("p.pdf", data, "application/pdf")}, data={"password": "pw"})
    assert r.status_code == 200
    # stored copy is decrypted so it can be edited and re-saved without a password
    sid2 = r.json()["id"]
    assert not pymupdf.open("pdf", download(client, sid2)).needs_pass


def test_forms_and_annotations(client, sid):
    r = client.post(f"/api/documents/{sid}/ops/add_field", json={"page": 0, "kind": "text", "rect": [72, 200, 300, 220], "name": "full_name"})
    assert r.status_code == 200, r.text
    client.post(f"/api/documents/{sid}/ops/fill_form", json={"values": {"full_name": "Ann"}})
    fields = client.get(f"/api/documents/{sid}/fields").json()["fields"]
    assert fields[0]["value"] == "Ann"
    client.post(f"/api/documents/{sid}/ops/annotate", json={"page": 0, "kind": "highlight", "rect": [60, 80, 300, 110]})
    ann = client.get(f"/api/documents/{sid}/annotations").json()["annotations"]
    hl = [a for a in ann if a["type"] == "Highlight"]
    assert hl
    client.post(f"/api/documents/{sid}/ops/delete_annotation", json={"page": 0, "xref": hl[0]["xref"]})
    ann = client.get(f"/api/documents/{sid}/annotations").json()["annotations"]
    assert not [a for a in ann if a["type"] == "Highlight"]


def test_errors(client, sid):
    assert client.post(f"/api/documents/{sid}/ops/nope", json={}).status_code == 404
    assert client.post(f"/api/documents/{sid}/ops/edit_text", json={}).status_code == 400
    assert client.post(f"/api/documents/{sid}/ops/delete_pages", json={"pages": "1-2"}).status_code == 400
    assert client.get("/api/documents/doesnotexist").status_code == 404
    r = client.post("/api/documents", files={"file": ("x.pdf", b"not a pdf", "application/pdf")})
    assert r.status_code == 400


def test_blank_and_from_images(client):
    assert client.post("/api/documents/blank", json={"pages": 3}).json()["page_count"] == 3
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 30, 30), False)
    r = client.post("/api/documents/from-images", files=[("files", ("a.png", pix.tobytes("png"), "image/png")), ("files", ("b.png", pix.tobytes("png"), "image/png"))])
    assert r.json()["page_count"] == 2


def test_history_limit():
    from pdfscout.store import DocumentStore

    s = DocumentStore(max_history=3)
    sess = s.create(make_pdf())
    for i in range(5):
        s.apply(sess.id, f"op{i}", lambda d: core.rotate_pages(d, [0], 90))
    assert len(sess.versions) == 3 and sess.index == 2
    assert sess.doc()[0].rotation == (5 * 90) % 360
