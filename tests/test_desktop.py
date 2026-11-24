import json
import urllib.request

import pymupdf
import pytest

pytest.importorskip("webview")

from pdfscout import core, desktop  # noqa: E402


class _Events:
    def __init__(self):
        self.closing = _Hook()


class _Hook(list):
    def __iadd__(self, fn):
        self.append(fn)
        return self


class FakeWindow:
    def __init__(self, dialog_result=None, confirm=True):
        self.dialog_result = dialog_result
        self.confirm = confirm
        self.title = None
        self.events = _Events()

    def create_file_dialog(self, *a, **kw):
        return self.dialog_result

    def create_confirmation_dialog(self, *a):
        return self.confirm

    def set_title(self, t):
        self.title = t


@pytest.fixture(scope="module")
def base():
    url, _ = desktop.start_server()
    return url


def make(path, text="Hello bob@example.com", password=None):
    d = pymupdf.open()
    d.new_page().insert_text((72, 72), text)
    path.write_bytes(core.save_bytes(d, user_password=password) if password else d.tobytes())
    return str(path)


def test_open_and_save(base, tmp_path):
    api = desktop.DesktopApi(base, initial_file=make(tmp_path / "in.pdf"))
    target = tmp_path / "saved"
    api._attach(FakeWindow(dialog_result=[str(target)]))
    path = api.initial_file()
    assert api.initial_file() is None  # handed out once
    res = api.open_path(path)
    sid = res["snapshot"]["id"]
    assert res["snapshot"]["filename"] == "in.pdf"
    req = urllib.request.Request(f"{base}/api/documents/{sid}/ops/redact_search", data=json.dumps({"presets": ["email"]}).encode(), headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req).read()
    out = api.save_download(f"/api/documents/{sid}/download", {}, "in.pdf")
    assert out["path"].endswith("saved.pdf")  # extension added
    assert "example" not in pymupdf.open(out["path"])[0].get_text()


def test_password_flow(base, tmp_path):
    api = desktop.DesktopApi(base)
    p = make(tmp_path / "locked.pdf", password="pw")
    r = api.open_path(p)
    assert r["needs_password"] and r["name"] == "locked.pdf"
    assert api.open_path(p, "wrong")["needs_password"]
    assert "snapshot" in api.open_path(p, "pw")


def test_errors_and_cancel(base, tmp_path):
    api = desktop.DesktopApi(base)
    api._attach(FakeWindow(dialog_result=None))
    assert "error" in api.open_path(str(tmp_path / "missing.pdf"))
    assert api.save_download("/api/documents/x/download", {}, "a.pdf") is None  # cancelled
    api._attach(FakeWindow(dialog_result=[str(tmp_path / "x.pdf")]))
    assert "error" in api.save_download("/api/documents/nope/download", {}, "a.pdf")
    assert "error" in api.save_download("http://evil/", {}, "a.pdf")


def test_close_confirmation_and_title(base):
    api = desktop.DesktopApi(base)
    win = FakeWindow(confirm=False)
    api._attach(win)
    api.set_state("a.pdf", False)
    assert win.title == "a.pdf – PDFScout" and api._on_closing() is True
    api.set_state("a.pdf", True)
    assert win.title.startswith("• ") and api._on_closing() is False
    win.confirm = True
    assert api._on_closing() is True


def test_selftest(tmp_path):
    report = tmp_path / "r.txt"
    assert desktop.selftest(str(report)) == 0
    assert "SELFTEST PASSED" in report.read_text()


def test_startup_failure_is_reported_not_silent(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    shown = []
    monkeypatch.setattr(desktop, "show_error", shown.append)

    def boom(*a):
        raise RuntimeError("WebView2 runtime not found")

    monkeypatch.setattr(desktop, "_run_window", boom)
    assert desktop.main([]) == 1
    assert shown and "could not start" in shown[0] and "WebView2" in shown[0] and "pdfscout.log" in shown[0]
    log = (tmp_path / "PDFScout" / "pdfscout.log").read_text()
    assert "starting" in log and "startup failed" in log and "RuntimeError" in log


def test_no_png_window_icon_on_windows(monkeypatch):
    # System.Drawing.Icon rejects PNGs and crashes the process (seen on Windows 11).
    monkeypatch.setattr(desktop.sys, "platform", "win32")
    assert desktop._window_icon() is None
    monkeypatch.setattr(desktop.sys, "platform", "linux")
    assert desktop._window_icon().endswith("icon.png")
