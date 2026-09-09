; Inno Setup Script for TalentOps Scout Desktop
; Creates a native single-file Windows installer: TalentOpsScoutSetup.exe
; Bundles both TalentOpsScout.exe (main companion) and TalentOpsScoutUpdater.exe (independent updater helper).
;
; Persistent user state (%LOCALAPPDATA%\TalentOpsAI\Scout\) is strictly preserved across updates and uninstalls.

#define MyAppName "TalentOps Scout"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "TalentOps AI"
#define MyAppURL "https://talentopsai-1.onrender.com"
#define MyAppExeName "TalentOpsScout.exe"
#define MyUpdaterExeName "TalentOpsScoutUpdater.exe"

[Setup]
AppId={{D37F291A-8B39-44F2-9C1D-8946E19E74A2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\TalentOpsScout
DisableProgramGroupPage=yes
OutputBaseFilename=TalentOpsScoutSetup
OutputDir=..\dist
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=..\assets\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Windows Setup
VersionInfoVersion=2.0.0.0
VersionInfoTextVersion={#MyAppVersion}
VersionInfoCopyright=© 2026 TalentOps AI
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion=2.0.0.0
SignedUninstaller=yes
SignTool=signtool sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 $f

[Languages]

Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Launch TalentOps Scout automatically when Windows starts"; GroupDescription: "Startup:"

[Files]
; Distribute all binaries, including TalentOpsScout.exe and TalentOpsScoutUpdater.exe
Source: "..\dist\TalentOpsScout\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Register custom protocol: talentopsscout://
Root: HKCU; Subkey: "Software\Classes\talentopsscout"; ValueType: string; ValueName: ""; ValueData: "URL:TalentOps Scout Protocol"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\talentopsscout"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\talentopsscout\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\talentopsscout\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

; Optional auto-start on Windows login
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "TalentOpsScout"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up app directory but NEVER touch persistent %LOCALAPPDATA%\TalentOpsAI\Scout
Type: filesandordirs; Name: "{app}"
