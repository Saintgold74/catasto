; ===================================================================
;  Script Inno Setup per l'applicazione Meridiana 1.0
;  Autore: Marco Santoro
;  Data: 18/06/2025
; ===================================================================

[Setup]
; Info base dell'applicazione e dell'installer
AppName=Meridiana
AppVersion=1.0
AppPublisher=Marco Santoro (per Archivio di Stato di Savona)
AppPublisherURL=https://archiviodistatosavona.cultura.gov.it/
AppSupportURL=https://archiviodistatosavona.cultura.gov.it/

; Directory di installazione di default in Program Files
DefaultDirName={autopf64}\Meridiana Catasto Storico
DefaultGroupName=Meridiana Catasto Storico
DisableProgramGroupPage=yes

; File di output dell'installer
OutputDir=installer
OutputBaseFilename=Setup_meridiana_1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

; Richiede privilegi di amministratore per l'installazione
PrivilegesRequired=admin

[Languages]
; Lingua dell'installer
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
; Aggiunge una checkbox per creare un'icona sul desktop
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Questa è la sezione più importante: copia TUTTO il contenuto della cartella
; generata da PyInstaller nella cartella di destinazione dell'applicazione.
; Il flag 'recursesubdirs' assicura che anche le cartelle 'resources', 'styles',
; e 'sql_scripts' vengano incluse.
Source: "dist\Meridiana\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Icona nel Menu Start che lancia l'applicazione
Name: "{group}\Meridiana"; Filename: "{app}\Meridiana.exe"

; Icona per disinstallare il programma
Name: "{group}\{cm:UninstallProgram,Meridiana}"; Filename: "{uninstallexe}"

; Icona sul Desktop (creata solo se l'utente spunta la casella relativa)
Name: "{autodesktop}\Meridiana"; Filename: "{app}\Meridiana.exe"; Tasks: desktopicon

[Run]
; Offre all'utente la possibilità di avviare il programma subito dopo la fine dell'installazione.
Filename: "{app}\Meridiana.exe"; Description: "{cm:LaunchProgram,Meridiana}"; Flags: nowait postinstall skipifsilent