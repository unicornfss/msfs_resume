#define AppName "MSFS Resume"
#define AppVersion "0.4.0"
#define AppPublisher "Ostroforge"
#define AppExeName "MSFSResume.exe"

[Setup]
AppId={{A7C4E91B-6D2F-4E11-9C8A-8B1C2D3E4F50}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=mailto:ostroforge@outlook.com
AppSupportURL=mailto:ostroforge@outlook.com
AppCopyright=Copyright (C) 2026 Ostroforge
DefaultDirName={localappdata}\Programs\MSFS Resume
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE.txt
OutputDir=..\dist
OutputBaseFilename=MSFSResumeSetup-{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=..\assets\msfs-resume.ico
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\MSFSResume\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
