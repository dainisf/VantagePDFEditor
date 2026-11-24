# Build PDFScout.exe (single file, no console window).
# Run from the repository root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
$ErrorActionPreference = "Stop"

if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[desktop,build,dev]"

.\.venv\Scripts\pyinstaller.exe `
  --noconfirm --clean --onefile --windowed `
  --name PDFScout `
  --paths . `
  --icon packaging\pdfscout.ico `
  --add-data "pdfscout\static;pdfscout\static" `
  --collect-all pymupdf `
  --collect-all webview `
  --hidden-import clr `
  packaging\pdfscout_app.py

# Packaging check: starts the engine inside the .exe and round-trips a document.
$p = Start-Process -FilePath dist\PDFScout.exe -ArgumentList "--selftest", "selftest.txt" -Wait -PassThru
Get-Content selftest.txt
if ($p.ExitCode -ne 0) { throw "Self-test failed" }
Write-Host "`nBuilt dist\PDFScout.exe"
