# Package Vantage PDF Editor as MSIX for the Microsoft Store.
#
# Run after packaging\build_windows.ps1 (needs dist\VantagePDFEditor\).
#   powershell -ExecutionPolicy Bypass -File packaging\build_msix.ps1 [-TestInstall]
#
# Output: dist\VantagePDFEditor-<version>-Store.msix   (unsigned: upload this to
#         Partner Center; the Store signs it)
# With -TestInstall: also signs a copy with a throwaway self-signed
# certificate, installs it like the Store would, opens the app window and checks
# the editor loaded, then removes it. (Needs admin to trust the test cert.)
param([switch]$TestInstall)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
function Step($msg) { Write-Host "`n=== $msg" -ForegroundColor Cyan }

$py = if (Test-Path .venv\Scripts\python.exe) { ".venv\Scripts\python.exe" } else { "python" }
$version = (Select-String -Path pyproject.toml -Pattern '^version\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
$exeName = & $py -c "from pdfscout import brand; print(brand.EXE_NAME)"
$id = Get-Content packaging\msix\store-identity.json -Raw | ConvertFrom-Json
$parts = ($version -split '[.-]')[0..2] | ForEach-Object { [int]$_ }
$msixVersion = "$($parts[0]).$($parts[1]).$($parts[2]).0"   # Store requires the 4th part to be 0
$app = "dist\$exeName"
if (-not (Test-Path "$app\$exeName.exe")) { throw "Build the app first: packaging\build_windows.ps1" }

# ---------------------------------------------------------------- tools
$kit = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Directory -ErrorAction SilentlyContinue |
  Where-Object { Test-Path "$($_.FullName)\x64\makeappx.exe" } | Sort-Object Name -Descending | Select-Object -First 1
if (-not $kit) { throw "Windows SDK (makeappx.exe) not found. Install the Windows 10/11 SDK." }
$makeappx = "$($kit.FullName)\x64\makeappx.exe"
$signtool = "$($kit.FullName)\x64\signtool.exe"
Write-Host "Windows SDK $($kit.Name); package $($id.IdentityName) $msixVersion"

# ---------------------------------------------------------------- layout
Step "Preparing package layout"
$layout = "build\msix-layout"
if (Test-Path $layout) { Remove-Item -Recurse -Force $layout }
New-Item -ItemType Directory -Force $layout | Out-Null
Copy-Item "$app\*" $layout -Recurse
Copy-Item packaging\msix\Assets "$layout\Assets" -Recurse
Copy-Item build\license.txt "$layout\LICENSE.txt" -ErrorAction SilentlyContinue
$manifest = (Get-Content packaging\msix\AppxManifest.template.xml -Raw).
  Replace("{{IdentityName}}", $id.IdentityName).
  Replace("{{Publisher}}", [Security.SecurityElement]::Escape($id.Publisher)).
  Replace("{{PublisherDisplayName}}", [Security.SecurityElement]::Escape($id.PublisherDisplayName)).
  Replace("{{Version}}", $msixVersion).
  Replace("{{Exe}}", "$exeName.exe")
Set-Content -Path "$layout\AppxManifest.xml" -Value $manifest -Encoding UTF8

# ---------------------------------------------------------------- pack
Step "Packing MSIX"
$msix = "dist\$exeName-$version-Store.msix"
if (Test-Path $msix) { Remove-Item $msix }
& $makeappx pack /o /d $layout /p $msix
if ($LASTEXITCODE) { throw "makeappx failed" }
Write-Host "Store package: $((Resolve-Path $msix).Path) ($([math]::Round((Get-Item $msix).Length / 1MB, 1)) MB)"

# ---------------------------------------------------------------- test install
if ($TestInstall) {
  Step "Test-signing and installing the package"
  $test = "build\$exeName-test.msix"
  Copy-Item $msix $test -Force
  $cert = New-SelfSignedCertificate -Type Custom -Subject $id.Publisher -KeyUsage DigitalSignature `
    -FriendlyName "Vantage PDF Editor MSIX test" -CertStoreLocation Cert:\CurrentUser\My `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
  $pfx = "build\msix-test.pfx"
  $pw = ConvertTo-SecureString -String "test" -Force -AsPlainText
  Export-PfxCertificate -Cert $cert -FilePath $pfx -Password $pw | Out-Null
  Import-PfxCertificate -FilePath $pfx -CertStoreLocation Cert:\LocalMachine\TrustedPeople -Password $pw | Out-Null
  & $signtool sign /fd SHA256 /a /f $pfx /p test $test
  if ($LASTEXITCODE) { throw "signtool failed" }

  Add-AppxPackage -Path $test
  $pkg = Get-AppxPackage -Name $id.IdentityName
  if (-not $pkg) { throw "Package did not install" }
  Write-Host "installed $($pkg.PackageFullName)"

  # Run through the app's execution alias, i.e. with its package identity.
  $alias = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\$exeName.exe"
  $report = "$PWD\build\selftest-msix.txt"
  $p = Start-Process -FilePath $alias -ArgumentList "--selftest", "`"$report`"" -Wait -PassThru
  Get-Content $report
  if ($p.ExitCode -ne 0) { throw "MSIX self-test failed" }

  $smoke = "$PWD\build\smoketest-msix.txt"
  $p = Start-Process -FilePath $alias -ArgumentList "--smoketest", "`"$smoke`"" -PassThru
  $finished = $p.WaitForExit(120000)
  if (-not $finished) { Stop-Process -Id $p.Id -Force }
  if (Test-Path $smoke) { Get-Content $smoke }
  if (-not $finished -or $p.ExitCode -ne 0) { throw "MSIX window test failed (exit $($p.ExitCode))" }

  Remove-AppxPackage -Package $pkg.PackageFullName
  Write-Host "ok  MSIX installs, opens its window and uninstalls"
}
