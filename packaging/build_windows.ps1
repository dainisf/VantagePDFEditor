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
& $py packaging\make_version_info.py $version build\version_info.txt
& $py -m PyInstaller --noconfirm --clean --onedir --windowed `
  --name PDFScout `
  --paths . `
  --icon packaging\pdfscout.ico `
  --version-file build\version_info.txt `
  --splash packaging\splash.png `
  --add-data "pdfscout\static;pdfscout\static" `
  --collect-all pymupdf `
  --collect-all webview `
  --hidden-import clr `
  packaging\pdfscout_app.py
if ($LASTEXITCODE) { throw "PyInstaller failed" }

# Windows shows FileDescription as the app name ("Open with", Task Manager).
$vi = (Get-Item dist\PDFScout\PDFScout.exe).VersionInfo
Write-Host "exe name: '$($vi.FileDescription)', product: '$($vi.ProductName)', version: $($vi.FileVersion)"
if ($vi.FileDescription -ne "PDFScout") { throw "PDFScout.exe has no 'PDFScout' description; Windows would show 'PDFScout.exe'" }

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
  $dir = Join-Path ([IO.Path]::GetFullPath((Get-Item $env:TEMP).FullName)) "PDFScout-installtest"
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
  # Compare resolved long paths (TEMP may be an 8.3 short path like RUNNER~1).
  $expected = (Get-Item "$dir\PDFScout.exe").FullName
  foreach ($lnk in @($startMenu, $desktop)) {
    $target = (Get-Item (New-Object -ComObject WScript.Shell).CreateShortcut($lnk).TargetPath).FullName
    if ($target -ne $expected) { throw "Shortcut $lnk points to '$target', expected '$expected'" }
  }
  if (-not (Test-Path "HKCU:\Software\Classes\.pdf\OpenWithProgids")) { throw "PDF 'Open with' registration missing" }
  $friendly = (Get-ItemProperty "HKCU:\Software\Classes\Applications\PDFScout.exe" -Name FriendlyAppName).FriendlyAppName
  if ($friendly -ne "PDFScout") { throw "'Open with' name is '$friendly', expected 'PDFScout'" }
  $mui = Get-ItemProperty "HKCU:\Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache" -ErrorAction SilentlyContinue
  $cached = $mui.PSObject.Properties | Where-Object { $_.Name -like "*PDFScout.exe.FriendlyAppName" } | Select-Object -ExpandProperty Value
  if ($cached -and ($cached | Where-Object { $_ -ne "PDFScout" })) { throw "Cached 'Open with' name is '$cached'" }
  Write-Host "ok  'Open with' shows: $friendly"
  Write-Host "ok  shortcuts point to the app, PDF 'Open with' registered"

  Invoke-SelfTest "$dir\PDFScout.exe" "$PWD\build\selftest-installed.txt"

  # Open the real window (WebView2), check the UI booted, close it.
  Step "Opening the installed app's window (GUI smoke test)"
  $smoke = "$PWD\build\smoketest-gui.txt"
  if (Test-Path $smoke) { Remove-Item $smoke }
  $p = Start-Process -FilePath "$dir\PDFScout.exe" -ArgumentList "--smoketest", "`"$smoke`"" -PassThru
  $finished = $p.WaitForExit(120000)
  if (-not $finished) { Stop-Process -Id $p.Id -Force; Write-Warning "GUI smoke test hung (killed after 120 s)" }
  if (Test-Path $smoke) { Get-Content $smoke } else { Write-Warning "no smoke test report written" }
  $appLog = Join-Path $env:LOCALAPPDATA "PDFScout\pdfscout.log"
  if (Test-Path $appLog) { Copy-Item $appLog "$PWD\build\pdfscout-log.txt"; Write-Host "--- app log"; Get-Content $appLog -Tail 60 }
  if (-not $finished -or $p.ExitCode -ne 0) { throw "GUI smoke test failed (exit $($p.ExitCode))" }

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
