# Build the PDFScout Windows installer (setup wizard) and test it.
#
# Run from the repository root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
#
# Output: dist\PDFScout-Setup-<version>.exe
# Steps: install deps -> PyInstaller app folder -> self-test -> Inno Setup
# wizard -> silent install, check shortcuts + app, uninstall, check cleanup.
param(
  [switch]$NoVenv,      # use the current Python instead of .venv (CI)
  [switch]$SkipInstallTest
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Step($msg) { Write-Host "`n=== $msg" -ForegroundColor Cyan }

# ---------------------------------------------------------------- python deps
if ($NoVenv) {
  $py = "python"
} else {
  if (-not (Test-Path .venv)) { python -m venv .venv }
  $py = ".\.venv\Scripts\python.exe"
}
Step "Installing dependencies"
& $py -m pip install --upgrade pip | Out-Null
& $py -m pip install -e ".[desktop,build,dev]"
if ($LASTEXITCODE) { throw "pip install failed" }

$version = (Select-String -Path pyproject.toml -Pattern '^version\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
Write-Host "PDFScout version $version"

# ---------------------------------------------------------------- license
Step "Fetching license text"
New-Item -ItemType Directory -Force build | Out-Null
$lic = "build\license.txt"
try {
  $agpl = (Invoke-WebRequest -UseBasicParsing https://www.gnu.org/licenses/agpl-3.0.txt).Content
  Set-Content -Path $lic -Value ((Get-Content LICENSE -Raw) + "`r`n`r`n" + $agpl) -Encoding UTF8
} catch {
  Write-Warning "Could not download the AGPL text ($_); using the short LICENSE notice."
  Copy-Item LICENSE $lic -Force
}

# ---------------------------------------------------------------- app build
Step "Building the app with PyInstaller"
if (Test-Path dist\PDFScout) { Remove-Item -Recurse -Force dist\PDFScout }
& $py -m PyInstaller --noconfirm --clean --onedir --windowed `
  --name PDFScout `
  --paths . `
  --icon packaging\pdfscout.ico `
  --splash packaging\splash.png `
  --add-data "pdfscout\static;pdfscout\static" `
  --collect-all pymupdf `
  --collect-all webview `
  --hidden-import clr `
  packaging\pdfscout_app.py
if ($LASTEXITCODE) { throw "PyInstaller failed" }

function Invoke-SelfTest($exe, $report) {
  $p = Start-Process -FilePath $exe -ArgumentList "--selftest", $report -Wait -PassThru
  Get-Content $report
  if ($p.ExitCode -ne 0) { throw "Self-test of $exe failed" }
}
Step "Self-testing the built app"
Invoke-SelfTest "dist\PDFScout\PDFScout.exe" "$PWD\build\selftest-build.txt"

# ---------------------------------------------------------------- installer
Step "Compiling the setup wizard (Inno Setup)"
$iscc = @(
  (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source,
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
  "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) {
  Write-Host "Inno Setup not found; installing it with winget/choco..."
  if (Get-Command choco -ErrorAction SilentlyContinue) { choco install innosetup -y --no-progress | Out-Null }
  elseif (Get-Command winget -ErrorAction SilentlyContinue) { winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements | Out-Null }
  $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $iscc) { throw "Inno Setup 6 is required: https://jrsoftware.org/isdl.php" }
}
& $iscc "/DAppVersion=$version" packaging\installer.iss
if ($LASTEXITCODE) { throw "Inno Setup failed" }
$setup = "dist\PDFScout-Setup-$version.exe"
if (-not (Test-Path $setup)) { throw "Installer not produced" }

# ---------------------------------------------------------------- install test
if (-not $SkipInstallTest) {
  Step "Testing silent install / shortcuts / uninstall"
  $dir = Join-Path $env:TEMP "PDFScout-installtest"
  if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
  $log = "$PWD\build\install.log"
  $p = Start-Process -FilePath $setup -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", "/DIR=`"$dir`"", "/TASKS=desktopicon,pdfassoc", "/LOG=`"$log`"" -Wait -PassThru
  if ($p.ExitCode -ne 0) { Get-Content $log -Tail 40; throw "Install failed ($($p.ExitCode))" }

  $startMenu = Join-Path ([Environment]::GetFolderPath("Programs")) "PDFScout\PDFScout.lnk"
  $desktop = Join-Path ([Environment]::GetFolderPath("Desktop")) "PDFScout.lnk"
  foreach ($f in @("$dir\PDFScout.exe", "$dir\unins000.exe", "$dir\LICENSE.txt", $startMenu, $desktop)) {
    if (-not (Test-Path $f)) { throw "Missing after install: $f" }
    Write-Host "ok  $f"
  }
  $target = (New-Object -ComObject WScript.Shell).CreateShortcut($desktop).TargetPath
  if ($target -ne "$dir\PDFScout.exe") { throw "Desktop shortcut points to '$target'" }
  if (-not (Test-Path "HKCU:\Software\Classes\.pdf\OpenWithProgids")) { throw "PDF 'Open with' registration missing" }
  Write-Host "ok  shortcuts point to the app, PDF 'Open with' registered"

  Invoke-SelfTest "$dir\PDFScout.exe" "$PWD\build\selftest-installed.txt"

  $p = Start-Process -FilePath "$dir\unins000.exe" -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "Uninstall failed ($($p.ExitCode))" }
  Start-Sleep -Seconds 3   # the uninstaller finishes removing itself asynchronously
  foreach ($f in @("$dir\PDFScout.exe", $startMenu, $desktop)) {
    if (Test-Path $f) { throw "Still present after uninstall: $f" }
  }
  Write-Host "ok  uninstall removed the app and shortcuts"
}

Step "Done"
Write-Host "Installer: $((Resolve-Path $setup).Path)" -ForegroundColor Green
