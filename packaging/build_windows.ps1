# Build the Vantage PDF Editor Windows installer (setup wizard) and test it.
#
# Run from the repository root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
#
# Output: dist\VantagePDFEditor-Setup-<version>.exe
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
$product = & $py -c "from pdfscout import brand; print(brand.PRODUCT_NAME)"
$exeName = & $py -c "from pdfscout import brand; print(brand.EXE_NAME)"
Write-Host "$product version $version ($exeName.exe)"

# ---------------------------------------------------------------- license
Step "Preparing license text"
New-Item -ItemType Directory -Force build | Out-Null
$lic = "build\license.txt"
# Wizard license page: copyright/third-party notice followed by the full AGPL.
Set-Content -Path $lic -Value ((Get-Content NOTICE -Raw) + "`r`n`r`n" + (Get-Content LICENSE -Raw)) -Encoding UTF8
if ((Get-Item $lic).Length -lt 30000) { throw "license text looks incomplete" }

# ---------------------------------------------------------------- app build
Step "Building the app with PyInstaller"
if (Test-Path "dist\$exeName") { Remove-Item -Recurse -Force "dist\$exeName" }
& $py packaging\make_version_info.py $version build\version_info.txt
& $py -m PyInstaller --noconfirm --clean --onedir --windowed `
  --name $exeName `
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
$vi = (Get-Item "dist\$exeName\$exeName.exe").VersionInfo
Write-Host "exe name: '$($vi.FileDescription)', product: '$($vi.ProductName)', version: $($vi.FileVersion)"
if ($vi.FileDescription -ne $product) { throw "$exeName.exe description is '$($vi.FileDescription)', expected '$product'" }
if ($vi.CompanyName -ne "DTR Networks, Inc.") { throw "Publisher is '$($vi.CompanyName)'" }

function Invoke-SelfTest($exe, $report) {
  $p = Start-Process -FilePath $exe -ArgumentList "--selftest", $report -Wait -PassThru
  Get-Content $report
  if ($p.ExitCode -ne 0) { throw "Self-test of $exe failed" }
}
Step "Self-testing the built app"
Invoke-SelfTest "dist\$exeName\$exeName.exe" "$PWD\build\selftest-build.txt"

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
$setup = "dist\$exeName-Setup-$version.exe"
if (-not (Test-Path $setup)) { throw "Installer not produced" }

# ---------------------------------------------------------------- install test
if (-not $SkipInstallTest) {
  Step "Testing silent install / shortcuts / uninstall"
  $dir = Join-Path ([IO.Path]::GetFullPath((Get-Item $env:TEMP).FullName)) "VantagePDFEditor-installtest"
  if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
  $log = "$PWD\build\install.log"
  $p = Start-Process -FilePath $setup -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", "/DIR=`"$dir`"", "/TASKS=desktopicon,pdfassoc", "/LOG=`"$log`"" -Wait -PassThru
  if ($p.ExitCode -ne 0) { Get-Content $log -Tail 40; throw "Install failed ($($p.ExitCode))" }

  $startMenu = Join-Path ([Environment]::GetFolderPath("Programs")) "Vantage\$product.lnk"
  $desktop = Join-Path ([Environment]::GetFolderPath("Desktop")) "$product.lnk"
  foreach ($f in @("$dir\$exeName.exe", "$dir\unins000.exe", "$dir\LICENSE.txt", $startMenu, $desktop)) {
    if (-not (Test-Path $f)) { throw "Missing after install: $f" }
    Write-Host "ok  $f"
  }
  # Compare resolved long paths (TEMP may be an 8.3 short path like RUNNER~1).
  $expected = (Get-Item "$dir\$exeName.exe").FullName
  foreach ($lnk in @($startMenu, $desktop)) {
    $target = (Get-Item (New-Object -ComObject WScript.Shell).CreateShortcut($lnk).TargetPath).FullName
    if ($target -ne $expected) { throw "Shortcut $lnk points to '$target', expected '$expected'" }
  }
  if (-not (Test-Path "HKCU:\Software\Classes\.pdf\OpenWithProgids")) { throw "PDF 'Open with' registration missing" }
  $friendly = (Get-ItemProperty "HKCU:\Software\Classes\Applications\$exeName.exe" -Name FriendlyAppName).FriendlyAppName
  if ($friendly -ne $product) { throw "'Open with' name is '$friendly', expected '$product'" }
  $mui = Get-ItemProperty "HKCU:\Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache" -ErrorAction SilentlyContinue
  $cached = $mui.PSObject.Properties | Where-Object { $_.Name -like "*$exeName.exe.FriendlyAppName" } | Select-Object -ExpandProperty Value
  if ($cached -and ($cached | Where-Object { $_ -ne $product })) { throw "Cached 'Open with' name is '$cached'" }
  Write-Host "ok  'Open with' shows: $friendly"
  Write-Host "ok  shortcuts point to the app, PDF 'Open with' registered"

  Invoke-SelfTest "$dir\$exeName.exe" "$PWD\build\selftest-installed.txt"

  # Open the real window (WebView2), check the UI booted, close it.
  Step "Opening the installed app's window (GUI smoke test)"
  $smoke = "$PWD\build\smoketest-gui.txt"
  if (Test-Path $smoke) { Remove-Item $smoke }
  $p = Start-Process -FilePath "$dir\$exeName.exe" -ArgumentList "--smoketest", "`"$smoke`"" -PassThru
  $finished = $p.WaitForExit(120000)
  if (-not $finished) { Stop-Process -Id $p.Id -Force; Write-Warning "GUI smoke test hung (killed after 120 s)" }
  if (Test-Path $smoke) { Get-Content $smoke } else { Write-Warning "no smoke test report written" }
  $appLog = Join-Path $env:LOCALAPPDATA "$product\pdfscout.log"
  if (Test-Path $appLog) { Copy-Item $appLog "$PWD\build\pdfscout-log.txt"; Write-Host "--- app log"; Get-Content $appLog -Tail 60 }
  if (-not $finished -or $p.ExitCode -ne 0) { throw "GUI smoke test failed (exit $($p.ExitCode))" }

  $p = Start-Process -FilePath "$dir\unins000.exe" -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "Uninstall failed ($($p.ExitCode))" }
  Start-Sleep -Seconds 3   # the uninstaller finishes removing itself asynchronously
  foreach ($f in @("$dir\$exeName.exe", $startMenu, $desktop)) {
    if (Test-Path $f) { throw "Still present after uninstall: $f" }
  }
  Write-Host "ok  uninstall removed the app and shortcuts"
}

Step "Done"
Write-Host "Installer: $((Resolve-Path $setup).Path)" -ForegroundColor Green
