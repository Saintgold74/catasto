; Script di installazione per "Meridiana Catasto"
; Generato automaticamente dal Supporto definitivo per il tirocinio

; --- Sezione [Setup] ---
; Informazioni generali sull'installazione.
[Setup]
AppName=Meridiana 
AppVersion=1.2  ; <--- Aggiorna qui la versione dal tuo file version_info.txt
AppPublisher=Marco Santoro
DefaultDirName={autopf}\Meridiana Catasto  ; Installa in C:\Program Files\Meridiana Catasto
DefaultGroupName=Meridiana Catasto        ; Crea una cartella nel Menu Start
OutputBaseFilename=Meridiana_Catasto_Setup ; Nome del file installer finale
Compression=lzma                        ; Algoritmo di compressione (ottimo per la dimensione)
SolidCompression=yes                    ; Compressione solida per maggiore efficienza
PrivilegesRequired=admin                ; Richiede privilegi di amministratore per installare in Program Files
SetupIconFile=resources\app_icon.ico ; <--- Opzionale: Percorso a un'icona .ico per l'installer
                                        ; Assicurati che 'resources\app_icon.ico' esista o rimuovi/modifica questa riga.
LicenseFile=resources\EULA.rtf          ; Percorso al file EULA
UninstallDisplayIcon={app}\Meridiana Catasto.exe ; Icona per la disinstallazione nel Pannello di Controllo
WizardImageFile=resources\setup_wizard_image.bmp ; <--- Opzionale: Immagine laterale per la wizard (280x430 bmp)
WizardSmallImageFile=resources\setup_small_image.bmp ; <--- Opzionale: Immagine piccola per la wizard (96x96 bmp)
ChangesEnvironment=yes ; Indica che l'installer potrebbe modificare variabili d'ambiente (utile per PostgreSQL)

; --- Sezione [Languages] ---
; Definisce le lingue supportate dall'installer.
[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

; --- Sezione [Files] ---
; Specifica quali file e cartelle devono essere inclusi nell'installer.
; Source: percorso da cui prendere i file (relativo alla directory dello script .iss)
; DestDir: percorso di destinazione sul sistema dell'utente (variabili speciali)
; Flags: opzioni aggiuntive (es. ricorsivo, crea cartelle)

; Copia tutti i file dalla cartella di output di PyInstaller (dist/Meridiana Catasto)
; ASSICURATI CHE IL PERCORSO '..\dist\Meridiana Catasto\*' SIA CORRETTO.
; Se hai usato --onefile e l'eseguibile è direttamente in dist\, adatta questo Source.
Source: "..\dist\Meridiana Catasto\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

; --- Sezione [Icons] ---
; Definisce le scorciatoie (shortcut) sul desktop e nel menu Start.
[Icons]
Name: "{group}\Meridiana Catasto"; Filename: "{app}\Meridiana Catasto.exe"; Tasks: desktopicon,quicklaunchicon
Name: "{autodesktop}\Meridiana Catasto"; Filename: "{app}\Meridiana Catasto.exe"; Tasks: desktopicon

; --- Sezione [Run] ---
; Comandi da eseguire dopo l'installazione.
; Lancia l'applicazione dopo l'installazione.
[Run]
Filename: "{app}\Meridiana Catasto.exe"; Description: "{cm:LaunchProgram,Meridiana Catasto}"; Flags: shellexec postinstall nowait

; --- Sezione [Tasks] ---
; Definisce le opzioni che l'utente può spuntare durante l'installazione.
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked

; --- Sezione [Code] (Opzionale, per logica personalizzata) ---
; Questa sezione è utile per la logica di installazione avanzata,
; come la verifica della presenza di PostgreSQL o la creazione di file di configurazione iniziali.
; Per ora, la lascio vuota, ma è qui che si potrebbe aggiungere intelligenza.
[Code]
; function InitializeSetup(): Boolean;
; begin
;   Result := True;
;   // Esempio: Controllare se PostgreSQL è installato
;   // Potrebbe essere necessario un prompt all'utente o la possibilità di installare i driver.
; end;