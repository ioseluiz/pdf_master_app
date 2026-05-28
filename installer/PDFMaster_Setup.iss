#define AppName        "PDF Master"
#define AppVersion     GetEnv("APP_VERSION")
#define AppPublisher   "Ing. Jose Luis Munoz"
#define AppExeName     "PDFMaster_App.exe"
#define AppDir         "..\dist\PDFMaster_App"
#define IconFile       "..\assets\icon.ico"
#define WizardSmall    "..\assets\wizard_small.bmp"

[Setup]
AppId={{F3A2C1B0-7E4D-4A8F-9C6B-2D5E8F0A1B3C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
; Sin UAC — instala en espacio del usuario
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
OutputDir=output
OutputBaseFilename=PDFMaster_Setup
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSmallImageFile={#WizardSmall}
DisableProgramGroupPage=yes
; Sin pantalla de bienvenida para instalación más rápida
DisableWelcomePage=no
; Mostrar acuerdo si existe
LicenseFile=
; Arquitectura
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "{#AppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Acceso directo en el menú Inicio del usuario (sin admin)
Name: "{userprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
; Acceso directo en el escritorio
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
