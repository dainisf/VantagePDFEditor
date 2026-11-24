"""Run the PDF editor API entirely inside the browser (Pyodide).

The browser build loads Python + PyMuPDF (WebAssembly) in a Web Worker and
imports this module. The page's HTTP-style requests ("/api/...") are posted to
the worker and dispatched here straight into the same FastAPI app the desktop
app uses, without any network: documents never leave the visitor's machine.

Pyodide has no threads, so FastAPI's thread pool for sync endpoints is replaced
with a direct call (:func:`install`).
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit

_installed = False


async def _run_sync_inline(func, *args, abandon_on_cancel=False, cancellable=None, limiter=None):  # noqa: ARG001
    return func(*args)


def install(max_history: int = 15) -> None:
    """Patch thread offloading and trim history for browser memory limits."""
    global _installed
    if _installed:
        return
    import anyio.to_thread

    anyio.to_thread.run_sync = _run_sync_inline
    from .server import store

    store.max_history = max_history
    _installed = True


async def handle(method: str, url: str, headers_json: str, body: bytes | None) -> dict:
    """Dispatch one request to the ASGI app and return the response.

    Returns ``{"status": int, "headers": [[name, value], ...], "body": bytes}``.
    """
    from .server import app

    parts = urlsplit(url)
    path = parts.path or "/"
    headers = [(k.lower().encode("latin-1"), str(v).encode("latin-1")) for k, v in json.loads(headers_json or "[]")]
    if body is not None and hasattr(body, "to_bytes"):  # JS Uint8Array proxy (Pyodide)
        body = body.to_bytes()
    body = bytes(body or b"")
    if body and not any(k == b"content-length" for k, _ in headers):
        headers.append((b"content-length", str(len(body)).encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": parts.query.encode(),
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 0),
        "server": ("browser", 80),
    }
    sent_body = False

    async def receive():
        nonlocal sent_body
        if not sent_body:
            sent_body = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    result: dict = {"status": 500, "headers": [], "body": b""}
    chunks: list[bytes] = []

    async def send(message):
        if message["type"] == "http.response.start":
            result["status"] = message["status"]
            result["headers"] = [[k.decode("latin-1"), v.decode("latin-1")] for k, v in message.get("headers", [])]
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    await app(scope, receive, send)
    result["body"] = b"".join(chunks)
    return result
