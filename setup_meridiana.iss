; Script Inno Setup per Meridiana 1.0

[Setup]
AppName=Meridiana
AppVersion=1.0
AppPublisher=Marco Santoro (per Archivio di Stato di Savona)
DefaultDirName={autopf64}\Meridiana Catasto Storico
DefaultGroupName=Meridiana Catasto Storico
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=setup_meridiana_1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copia TUTTO il contenuto della cartella generata da PyInstaller
Source: "dist\Meridiana\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Meridiana"; Filename: "{app}\Meridiana.exe"
Name: "{group}\{cm:UninstallProgram,Meridiana}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Meridiana"; Filename: "{app}\Meridiana.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Meridiana.exe"; Description: "{cm:LaunchProgram,Meridiana}"; Flags: nowait postinstall skipifsilent