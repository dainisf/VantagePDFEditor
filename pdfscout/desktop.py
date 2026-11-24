"""Vantage PDF Editor as a desktop application.

Runs the editor engine on a private localhost port inside this process and
shows the UI in a native window (Edge WebView2 on Windows, WebKit on macOS,
GTK/Qt on Linux) via pywebview. Opening and saving use the operating
system's own file dialogs.

    pdfscout-app [file.pdf]
    pdfscout-app --selftest report.txt     # headless packaging check
"""

from __future__ import annotations

import io
import json
import os
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

from . import __version__, brand, core

APP_NAME = brand.PRODUCT_NAME
PDF_TYPES = ("PDF files (*.pdf)", "Documents and images (*.pdf;*.xps;*.epub;*.png;*.jpg;*.jpeg;*.tif;*.tiff)", "All files (*.*)")


def _fix_std_streams() -> None:
    """Windowed (no-console) builds have sys.stdout/stderr = None."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))


def data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server() -> tuple[str, object]:
    """Start the API on a random localhost port in a daemon thread."""
    import uvicorn

    from .server import app

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_config=None, log_level="warning", loop="asyncio", http="h11", ws="none", lifespan="off")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, name="pdfscout-server", daemon=True).start()
    deadline = time.time() + 20
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError(f"{APP_NAME} engine did not start")
        time.sleep(0.05)
    return f"http://127.0.0.1:{port}", server


class DesktopApi:
    """Methods exposed to the page as ``window.pywebview.api.*``."""

    def __init__(self, base_url: str, initial_file: str | None = None):
        self._base = base_url
        self._initial = initial_file
        self._window = None
        self._dirty = False
        self._last_dir = str(Path.home() / "Documents") if (Path.home() / "Documents").is_dir() else str(Path.home())

    # -- wiring ----------------------------------------------------------
    def _attach(self, window) -> None:
        self._window = window
        window.events.closing += self._on_closing

    def _on_closing(self):
        if not self._dirty:
            return True
        return bool(self._window.create_confirmation_dialog(APP_NAME, "You have changes that haven't been saved. Close anyway?"))

    # -- called from JS --------------------------------------------------
    def info(self) -> dict:
        return {"version": __version__, "desktop": True}

    def initial_file(self) -> str | None:
        f, self._initial = self._initial, None
        return f

    def set_state(self, title: str, dirty: bool) -> None:
        self._dirty = bool(dirty)
        if self._window is not None:
            self._window.set_title(f"{'• ' if dirty else ''}{title} – {APP_NAME}" if title else APP_NAME)

    def choose_open(self) -> str | None:
        import webview

        res = self._window.create_file_dialog(webview.FileDialog.OPEN, directory=self._last_dir, file_types=PDF_TYPES)
        if not res:
            return None
        path = res[0] if isinstance(res, (list, tuple)) else res
        self._last_dir = str(Path(path).parent)
        return path

    def open_path(self, path: str, password: str | None = None) -> dict:
        """Open a file from disk into a new editing session."""
        from .server import _snapshot, store

        try:
            data = Path(path).read_bytes()
            sess = store.create(data, Path(path).name, password or None)
        except core.PDFScoutError as e:
            msg = str(e)
            return {"error": msg, "needs_password": "password" in msg.lower(), "path": path, "name": Path(path).name}
        except OSError as e:
            return {"error": f"Cannot read {path}: {e.strerror or e}"}
        return {"snapshot": _snapshot(sess), "path": path}

    def save_download(self, api_path: str, body: dict | None, suggested: str) -> dict | None:
        """Ask where to save, then write the server's response for api_path there."""
        import webview

        ext = Path(suggested).suffix.lower() or ".pdf"
        types = {".pdf": ("PDF files (*.pdf)",), ".zip": ("ZIP archives (*.zip)",), ".txt": ("Text files (*.txt)",), ".html": ("HTML files (*.html)",)}.get(ext, ())
        res = self._window.create_file_dialog(webview.FileDialog.SAVE, directory=self._last_dir, save_filename=suggested, file_types=types + ("All files (*.*)",))
        if not res:
            return None
        target = res[0] if isinstance(res, (list, tuple)) else res
        if not Path(target).suffix:
            target += ext
        if not api_path.startswith("/api/"):
            return {"error": "Invalid export path"}
        req = urllib.request.Request(self._base + api_path, data=json.dumps(body or {}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read()).get("detail", str(e))
            except Exception:  # noqa: BLE001
                detail = str(e)
            return {"error": detail}
        try:
            Path(target).write_bytes(data)
        except OSError as e:
            return {"error": f"Cannot write {target}: {e.strerror or e}"}
        self._last_dir = str(Path(target).parent)
        return {"path": target, "name": Path(target).name}

    def mark_saved(self) -> None:
        self._dirty = False


def selftest(report: str | None) -> int:
    """Start the engine, round-trip a document through the API, report."""
    out = io.StringIO()
    ok = True
    try:
        base, _ = start_server()
        out.write(f"{APP_NAME} {__version__} engine at {base}\n")
        caps = json.loads(urllib.request.urlopen(base + "/api/capabilities", timeout=20).read())
        out.write(f"capabilities: ocr={caps['ocr']} ops={len(caps['ops'])}\n")
        html = urllib.request.urlopen(base + "/", timeout=20).read().decode()
        assert "brand" in html and "app.js" in html, "UI not bundled"
        js = urllib.request.urlopen(base + "/static/app.js", timeout=20).read()
        assert len(js) > 10000, "app.js missing"
        import pymupdf

        d = pymupdf.open()
        d.new_page().insert_text((72, 72), "Self-test jane@example.com")
        tmp = data_dir() / "selftest.pdf"
        tmp.write_bytes(d.tobytes())
        api = DesktopApi(base)
        res = api.open_path(str(tmp))
        assert "snapshot" in res, res
        sid = res["snapshot"]["id"]
        req = urllib.request.Request(base + f"/api/documents/{sid}/ops/redact_search", data=b'{"presets":["email"]}', headers={"Content-Type": "application/json"}, method="POST")
        assert json.loads(urllib.request.urlopen(req, timeout=60).read())["result"] == 1
        png = urllib.request.urlopen(base + f"/api/documents/{sid}/pages/0/image?scale=1", timeout=60).read()
        assert png[:4] == b"\x89PNG"
        tmp.unlink(missing_ok=True)
        out.write("document round-trip: ok\n")
        if sys.platform == "win32":
            import webview.platforms.winforms  # noqa: F401  (pythonnet + WebView2 bindings bundled)

            out.write("webview backend: winforms ok\n")
    except Exception:  # noqa: BLE001
        ok = False
        out.write(traceback.format_exc())
    out.write("SELFTEST " + ("PASSED" if ok else "FAILED") + "\n")
    text = out.getvalue()
    if report:
        Path(report).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    _fix_std_streams()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        _close_splash()
        return selftest(argv[1] if len(argv) > 1 else None)
    if argv and argv[0] in ("--version", "-V"):
        print(__version__)
        return 0
    smoketest = None
    if argv and argv[0] == "--smoketest":
        smoketest = argv[1] if len(argv) > 1 else str(data_dir() / "smoketest.txt")
        argv = []
    initial = next((a for a in argv if not a.startswith("-") and Path(a).is_file()), None)
    log = _setup_logging()
    log.info(APP_NAME + " %s starting (frozen=%s, python=%s, windows=%s, args=%s)", __version__, getattr(sys, "frozen", False), sys.version.split()[0], _windows_version(), argv)
    try:
        return _run_window(initial, log, smoketest)
    except Exception as e:  # noqa: BLE001 - last-resort handler: never exit silently
        log.exception("startup failed")
        _close_splash()
        hint = ""
        if "webview2" in str(e).lower() or "edgechromium" in str(e).lower() or type(e).__name__ in ("WebViewException",):
            hint = f"\n\n{APP_NAME} needs the Microsoft Edge WebView2 runtime. Install it from https://go.microsoft.com/fwlink/p/?LinkId=2124703 and try again."
        show_error(f"{APP_NAME} could not start.\n\n{type(e).__name__}: {e}{hint}\n\nDetails were written to:\n{_log_path()}")
        return 1


def _window_icon() -> str | None:
    """Icon file for the window, or None to use the executable's own icon.

    On Windows, pywebview loads the icon with System.Drawing.Icon, which only
    accepts .ico files: passing a PNG throws an ArgumentException on a .NET
    thread and kills the process. The packaged .exe already embeds the .ico,
    which WinForms uses when no icon is given, so pass nothing there.
    """
    if sys.platform == "win32":
        return None
    icon = Path(__file__).parent / "static" / "icon.png"
    return str(icon) if icon.exists() else None


def _windows_version() -> str:
    if sys.platform != "win32":
        return "-"
    try:
        import platform

        return platform.platform()
    except Exception:  # noqa: BLE001
        return "?"


def _log_path() -> Path:
    return data_dir() / "pdfscout.log"


def _setup_logging():
    import logging
    from logging.handlers import RotatingFileHandler

    log = logging.getLogger("pdfscout")
    if not log.handlers:
        try:
            h = RotatingFileHandler(_log_path(), maxBytes=1_000_000, backupCount=2, encoding="utf-8")
            h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            log.addHandler(h)
        except OSError:
            pass
        log.setLevel(logging.INFO)
    return log


def show_error(message: str) -> None:
    """Show an error the user can actually see (windowed builds have no console)."""
    try:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10 | 0x40000)  # MB_ICONERROR | MB_TOPMOST
            return
    except Exception:  # noqa: BLE001
        pass
    sys.stderr.write(message + "\n")


def _close_splash() -> None:
    """Close the PyInstaller splash screen if the build has one."""
    try:
        import pyi_splash  # type: ignore[import-not-found]

        pyi_splash.close()
    except Exception:  # noqa: BLE001 - not a splash build
        pass


STARTUP_TIMEOUT = 45  # seconds until we tell the user something is wrong


def _run_window(initial: str | None, log, smoketest: str | None = None) -> int:
    import logging

    import webview

    # pywebview reports WebView2 failures through its own logger; keep them.
    wv_log = logging.getLogger("pywebview")
    for h in log.handlers:
        if h not in wv_log.handlers:
            wv_log.addHandler(h)
    wv_log.setLevel(logging.DEBUG if smoketest else logging.INFO)

    base, _ = start_server()
    log.info("engine listening at %s", base)
    api = DesktopApi(base, str(Path(initial).resolve()) if initial else None)
    window = webview.create_window(APP_NAME, base + "/", js_api=api, width=1400, height=900, min_size=(860, 560), text_select=True, background_color="#EEF0F3")
    api._attach(window)
    state = {"shown": False, "loaded": False, "exit": 0}
    loaded_evt = threading.Event()

    def _shown():
        state["shown"] = True
        log.info("window shown")

    def _loaded():
        state["loaded"] = True
        loaded_evt.set()
        log.info("page loaded (renderer=%s)", getattr(webview, "renderer", "?"))

    window.events.shown += _shown
    window.events.loaded += _loaded

    def _watchdog():
        if loaded_evt.wait(STARTUP_TIMEOUT):
            return
        log.error("window did not load within %ss (shown=%s)", STARTUP_TIMEOUT, state["shown"])
        if smoketest:
            Path(smoketest).write_text(f"SMOKETEST FAILED: window not loaded after {STARTUP_TIMEOUT}s (shown={state['shown']})\n", encoding="utf-8")
            os._exit(3)
        show_error(
            f"{APP_NAME} started but its window did not open.\n\n"
            "This usually means the Microsoft Edge WebView2 runtime is missing or damaged. "
            "Reinstall it from https://go.microsoft.com/fwlink/p/?LinkId=2124703 and try again.\n\n"
            f"Details were written to:\n{_log_path()}"
        )
        os._exit(2)

    threading.Thread(target=_watchdog, name="pdfscout-watchdog", daemon=True).start()

    def _after_start():
        if not smoketest:
            return
        if not loaded_evt.wait(STARTUP_TIMEOUT):
            return  # watchdog reports
        report = []
        try:
            for _ in range(40):  # wait for app.js to boot
                ok = window.evaluate_js("!!(document.querySelector('#toolstrip .tool') && window.pywebview && window.pywebview.api)")
                if ok:
                    break
                time.sleep(0.25)
            report.append(f"renderer: {getattr(webview, 'renderer', '?')}")
            report.append(f"ui booted: {bool(ok)}")
            report.append(f"title: {window.evaluate_js('document.title')}")
            state["exit"] = 0 if ok else 4
        except Exception as e:  # noqa: BLE001
            report.append(f"error: {e!r}")
            state["exit"] = 5
        report.append("SMOKETEST " + ("PASSED" if state["exit"] == 0 else "FAILED"))
        Path(smoketest).write_text("\n".join(report) + "\n", encoding="utf-8")
        log.info("smoketest: %s", report)
        window.destroy()

    log.info("opening window")
    _close_splash()  # never let the splash overlap or block the real window
    webview.start(_after_start, private_mode=False, storage_path=str(data_dir() / "webview"), icon=_window_icon(), debug=False)
    log.info("window closed")
    return state["exit"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
