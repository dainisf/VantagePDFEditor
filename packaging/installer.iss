; Vantage PDF Editor Windows installer (Inno Setup 6)
; Built by packaging\build_windows.ps1 or the "Windows app" GitHub workflow:
;   iscc /DAppVersion=0.2.0 packaging\installer.iss
; Expects the PyInstaller one-folder build in dist\VantagePDFEditor\ and the
; license in build\license.txt.

#ifndef AppVersion
  #define AppVersion "0.2.0"
#endif
#define AppName "Vantage PDF Editor"
#define AppExeBase "VantagePDFEditor"
#define AppExe "VantagePDFEditor.exe"
#define ProgId "Vantage.PDFEditor.Document"
#define Publisher "DTR Networks, Inc."
#define AppUrl "https://dtrvantage.com/tools/pdf-editor/"
; AppId of the earlier "PDFScout" builds, removed on install.
#define OldAppId "{E02E04A0-AF28-4144-AA59-446B805FDBEA}"

[Setup]
AppId={{76A0CA9F-FDB5-40AB-B57F-F04E92985C05}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#Publisher}
AppPublisherURL=https://dtrvantage.com/
AppSupportURL={#AppUrl}
AppUpdatesURL={#AppUrl}
AppCopyright=(C) {#Publisher}
VersionInfoCompany={#Publisher}
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
DefaultDirName={autopf}\Vantage\PDF Editor
DefaultGroupName=Vantage
DisableProgramGroupPage=auto
; Lets the user pick "Install for me only" (no admin) or "for all users".
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\build\license.txt
SetupIconFile=pdfscout.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardSizePercent=110
Compression=lzma2/max
SolidCompression=yes
OutputDir=..\dist
OutputBaseFilename=VantagePDFEditor-Setup-{#AppVersion}
CloseApplications=yes
RestartApplications=no
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "pdfassoc"; Description: "Add {#AppName} to ""Open with"" for PDF files"; GroupDescription: "File types:"

[Files]
Source: "..\dist\{#AppExeBase}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\license.txt"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; File association: shows up under "Open with" and in Default apps; Windows
; doesn't let installers silently take over the default PDF app.
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueData: "PDF Document"; Flags: uninsdeletekey; Tasks: pdfassoc
Root: HKA; Subkey: "Software\Classes\{#ProgId}\DefaultIcon"; ValueType: string; ValueData: "{app}\{#AppExe},0"; Tasks: pdfassoc
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: pdfassoc
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "{#ProgId}"; ValueData: ""; Flags: uninsdeletevalue; Tasks: pdfassoc
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Flags: uninsdeletekey; Tasks: pdfassoc
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: pdfassoc
; Name shown in "Open with" (otherwise Windows falls back to the .exe file name).
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Tasks: pdfassoc
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Tasks: pdfassoc
; Windows caches app names; make sure the cached name is the product name.
Root: HKCU; Subkey: "Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache"; ValueType: string; ValueName: "{app}\{#AppExe}.FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache"; ValueType: string; ValueName: "{app}\{#AppExe}.ApplicationCompany"; ValueData: "{#AppName}"; Flags: uninsdeletevalue
; Registered application (listed in Settings > Default apps)
Root: HKA; Subkey: "Software\DTR Networks"; Flags: uninsdeletekeyifempty; Tasks: pdfassoc
Root: HKA; Subkey: "Software\DTR Networks\{#AppExeBase}"; Flags: uninsdeletekeyifempty; Tasks: pdfassoc
Root: HKA; Subkey: "Software\DTR Networks\{#AppExeBase}\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#AppName}"; Flags: uninsdeletekey; Tasks: pdfassoc
Root: HKA; Subkey: "Software\DTR Networks\{#AppExeBase}\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Edit, redact and organize PDF files"; Tasks: pdfassoc
Root: HKA; Subkey: "Software\DTR Networks\{#AppExeBase}\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "{#ProgId}"; Tasks: pdfassoc
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#AppExeBase}"; ValueData: "Software\DTR Networks\{#AppExeBase}\Capabilities"; Flags: uninsdeletevalue; Tasks: pdfassoc

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
const
  WebView2ClientKey = 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2ClientKey64 = 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2Url = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703';

var
  DownloadPage: TDownloadWizardPage;

function HasWebView2Key(RootKey: Integer; const Key: String): Boolean;
var
  Version: String;
begin
  Result := RegQueryStringValue(RootKey, Key, 'pv', Version) and (Version <> '') and (Version <> '0.0.0.0');
end;

{ The window is drawn by Microsoft Edge WebView2, preinstalled on current
  Windows 10/11. Install it only if it is missing. }
function WebView2Installed: Boolean;
begin
  Result := HasWebView2Key(HKLM, WebView2ClientKey) or HasWebView2Key(HKLM, WebView2ClientKey64) or HasWebView2Key(HKCU, WebView2ClientKey64);
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), 'Downloading the Microsoft Edge WebView2 component {#AppName} needs...', nil);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if (CurPageID = wpReady) and not WebView2Installed then
  begin
    DownloadPage.Clear;
    DownloadPage.Add(WebView2Url, 'MicrosoftEdgeWebview2Setup.exe', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
        DownloadPage.SetText('Installing Microsoft Edge WebView2...', '');
        if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'), '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
          MsgBox('Microsoft Edge WebView2 could not be installed (code ' + IntToStr(ResultCode) + '). {#AppName} will be installed, but you may need to install WebView2 from microsoft.com before it can open.', mbInformation, MB_OK);
      except
        if not WizardSilent then
          MsgBox('Could not download Microsoft Edge WebView2: ' + GetExceptionMessage + #13#10#13#10 + '{#AppName} will be installed, but you may need to install WebView2 from microsoft.com before it can open.', mbInformation, MB_OK);
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
end;

{ Earlier builds were called "PDFScout". Remove that install silently so the
  user doesn't end up with two copies. }
function OldUninstaller(var Cmd: String): Boolean;
var
  Key: String;
begin
  Key := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#OldAppId}_is1';
  Result := RegQueryStringValue(HKCU, Key, 'UninstallString', Cmd) or
            RegQueryStringValue(HKLM64, Key, 'UninstallString', Cmd) or
            RegQueryStringValue(HKLM32, Key, 'UninstallString', Cmd);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Cmd: String;
  ResultCode: Integer;
begin
  if (CurStep = ssInstall) and OldUninstaller(Cmd) then
  begin
    WizardForm.StatusLabel.Caption := 'Removing the previous version (PDFScout)...';
    Exec(RemoveQuotes(Cmd), '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

