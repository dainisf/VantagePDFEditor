"""The browser build's bridge, exercised on CPython with threads forbidden."""

import asyncio
import json
import threading

import anyio.to_thread
import pymupdf
import pytest

from pdfscout import webbridge


@pytest.fixture
def bridge(monkeypatch):
    monkeypatch.setattr(anyio.to_thread, "run_sync", anyio.to_thread.run_sync)  # restored afterwards
    monkeypatch.setattr(webbridge, "_installed", False)
    from pdfscout.server import store

    monkeypatch.setattr(store, "max_history", store.max_history)
    webbridge.install()

    def no_threads(self):  # Pyodide cannot start threads
        raise AssertionError(f"thread started in browser mode: {self.name}")

    monkeypatch.setattr(threading.Thread, "start", no_threads)

    def call(method, url, body=b"", headers=None):
        return asyncio.run(webbridge.handle(method, url, json.dumps(headers or []), body))

    return call


def multipart(field, filename, data, ctype="application/pdf"):
    boundary = "----vantage"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return body, [["Content-Type", f"multipart/form-data; boundary={boundary}"]]


def test_full_session_without_threads(bridge):
    from pdfscout.server import store

    assert store.max_history == 15
    r = bridge("GET", "/api/capabilities")
    assert r["status"] == 200 and json.loads(r["body"])["brand"]["product"] == "Vantage PDF Editor"

    d = pymupdf.open()
    d.new_page().insert_text((72, 72), "Contact jane@example.com")
    body, headers = multipart("file", "t.pdf", d.tobytes())
    r = bridge("POST", "/api/documents", body, headers)
    assert r["status"] == 200, r["body"]
    sid = json.loads(r["body"])["id"]

    r = bridge("GET", f"/api/documents/{sid}/pages/0/image?scale=0.5&v=1")
    assert r["status"] == 200 and r["body"][:4] == b"\x89PNG"
    assert ["content-type", "image/png"] in r["headers"]

    r = bridge("POST", f"/api/documents/{sid}/ops/redact_search", json.dumps({"presets": ["email"]}).encode(), [["Content-Type", "application/json"]])
    assert json.loads(r["body"])["result"] == 1

    r = bridge("POST", f"/api/documents/{sid}/download", b"{}", [["Content-Type", "application/json"]])
    assert r["status"] == 200 and "example.com" not in pymupdf.open("pdf", r["body"])[0].get_text()


def test_errors_are_http_responses(bridge):
    assert bridge("GET", "/api/documents/nope")["status"] == 404
    body, headers = multipart("file", "x.pdf", b"not a pdf")
    r = bridge("POST", "/api/documents", body, headers)
    assert r["status"] == 400 and "Cannot open" in json.loads(r["body"])["detail"]
