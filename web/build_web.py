"""Build the browser version of Vantage PDF Editor as a static folder.

    python web/build_web.py [--out dist-web]

The output is a self-contained static site: upload the folder's contents to
https://dtrvantage.com/tools/pdf-editor/ (any sub-path works; all links are
relative). Everything, including Python and the PDF engine, is served from
your own site; PDFs are processed in the visitor's browser and never uploaded.

Contents:
    index.html                the editor
    static/                   app.js, styles.css, icon, worker.js (engine thread)
    pyodide/                  Python runtime + PyMuPDF etc. (WebAssembly)
    wheels/                   the editor's Python package + python-multipart
    web.config, .htaccess     MIME types / caching for IIS or Apache
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pdfscout import __version__, brand  # noqa: E402

PYODIDE_VERSION = "0.29.0"
PYODIDE_URL = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"
PYODIDE_CORE = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"]
PACKAGES = ["pymupdf", "fastapi"]  # resolved with their dependencies from pyodide-lock.json


def fetch(url: str, dest: Path, sha256: str | None = None) -> Path:
    if dest.exists() and (sha256 is None or hashlib.sha256(dest.read_bytes()).hexdigest() == sha256):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}")
    with urllib.request.urlopen(url, timeout=300) as r:
        data = r.read()
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        raise SystemExit(f"checksum mismatch for {url}")
    dest.write_bytes(data)
    return dest


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def resolve(lock: dict, roots: list[str]) -> list[dict]:
    pkgs = lock["packages"]
    index = {norm(k): k for k in pkgs}
    seen: dict[str, dict] = {}
    stack = list(roots)
    while stack:
        key = index[norm(stack.pop())]
        if key in seen:
            continue
        seen[key] = pkgs[key]
        stack.extend(pkgs[key].get("depends", []))
    return list(seen.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "dist-web"))
    ap.add_argument("--cache", default=str(ROOT / "build" / "web-cache"))
    args = ap.parse_args()
    out, cache = Path(args.out), Path(args.cache)
    if out.exists():
        shutil.rmtree(out)
    (out / "static").mkdir(parents=True)
    (out / "pyodide").mkdir()
    (out / "wheels").mkdir()

    print(f"Pyodide {PYODIDE_VERSION}")
    for f in PYODIDE_CORE:
        shutil.copy(fetch(PYODIDE_URL + f, cache / "pyodide" / f), out / "pyodide" / f)
    lock = json.loads((out / "pyodide" / "pyodide-lock.json").read_text())
    for pkg in resolve(lock, PACKAGES):
        f = pkg["file_name"]
        shutil.copy(fetch(PYODIDE_URL + f, cache / "pyodide" / f, pkg.get("sha256")), out / "pyodide" / f)

    print("Python wheels")
    wheels_dir = cache / "wheels"
    wheels_dir.mkdir(parents=True, exist_ok=True)
    for old in wheels_dir.glob("pdfscout-*.whl"):
        old.unlink()
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "-q", "-w", str(wheels_dir), str(ROOT)], check=True)
    subprocess.run([sys.executable, "-m", "pip", "download", "--no-deps", "-q", "--only-binary", ":all:", "-d", str(wheels_dir), "python-multipart==0.0.20"], check=True)
    wheels = []
    for pattern in ("python_multipart-0.0.20-*.whl", f"pdfscout-{__version__}-*.whl"):
        whl = sorted(wheels_dir.glob(pattern))[-1]
        shutil.copy(whl, out / "wheels" / whl.name)
        wheels.append(whl.name)
    (out / "wheels" / "manifest.json").write_text(json.dumps({"version": __version__, "packages": PACKAGES, "wheels": wheels}, indent=2))

    print("Front end")
    static = ROOT / "pdfscout" / "static"
    for f in ("app.js", "styles.css", "icon.png"):
        shutil.copy(static / f, out / "static" / f)
    shutil.copy(ROOT / "web" / "worker.js", out / "static" / "worker.js")
    html = (static / "index.html").read_text(encoding="utf-8")
    v = __version__
    html = html.replace('href="static/styles.css"', f'href="static/styles.css?v={v}"')
    html = html.replace('<script src="static/app.js"></script>', f'<script>window.PDFSCOUT_WEB = true; window.PDFSCOUT_VERSION = "{v}";</script>\n  <script src="static/app.js?v={v}"></script>')
    html = html.replace("<head>", f'<head>\n  <link rel="canonical" href="{brand.WEBSITE}">', 1)
    (out / "index.html").write_text(html, encoding="utf-8")
    shutil.copy(ROOT / "web" / "web.config", out / "web.config")
    shutil.copy(ROOT / "web" / "htaccess", out / ".htaccess")

    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"\nBuilt {out} ({total / 1e6:.1f} MB). Upload its contents to {brand.WEBSITE}")


if __name__ == "__main__":
    main()
