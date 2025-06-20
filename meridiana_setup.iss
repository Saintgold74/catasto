; ====================================================================
;  Script per Inno Setup per "Meridiana"
;  Autore: Marco Santoro
; 
; ====================================================================

[Setup]
; Info base dell'applicazione
AppName=Meridiana
AppVersion=1.2
AppPublisher=Marco Santoro
DefaultDirName={autopf}\Meridiana
DisableProgramGroupPage=yes

; File di licenza (EULA) e icone
LicenseFile=resources\EULA.txt
SetupIconFile=resources\logo_meridiana.ico
UninstallDisplayIcon={app}\Meridiana.exe

; Impostazioni di output
OutputBaseFilename=Setup Meridiana 1.2
OutputDir=installer_output
Compression=lzma
SolidCompression=yes

; Stile, permessi e copyright
WizardStyle=modern
PrivilegesRequired=admin
;Copyright=Copyright © 2025 Marco Santoro

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";

[Files]
; Copia tutti i file e le sottocartelle dall'output di PyInstaller
; nella cartella di installazione finale.
Source: "dist\Meridiana\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Crea i collegamenti nel Menu Start e sul Desktop.
Name: "{autoprograms}\Meridiana"; Filename: "{app}\Meridiana.exe"
Name: "{autodesktop}\Meridiana"; Filename: "{app}\Meridiana.exe"; Tasks: desktopicon

[Run]
; Offre all'utente la possibilità di avviare "Meridiana" al termine dell'installazione.
Filename: "{app}\Meridiana.exe"; Description: "{cm:LaunchProgram,Meridiana}"; Flags: nowait postinstall skipifsilent