@echo off
setlocal

REM --- Impostazioni ---
set DB_NAME=catasto_storico
set DB_USER=postgres
set PG_BIN_PATH="C:\Program Files\PostgreSQL\17\bin" REM <-- MODIFICA SE NECESSARIO il percorso di PostgreSQL

REM Verifica se il percorso psql esiste
if not exist %PG_BIN_PATH%\dropdb.exe (
    echo ERRORE: dropdb.exe non trovato nel percorso: %PG_BIN_PATH%
    echo Modifica la variabile PG_BIN_PATH nello script.
    goto :eof
)
set PATH=%PG_BIN_PATH%;%PATH%

REM --- Avviso ---
echo ATTENZIONE: Stai per cancellare PERMANENTEMENTE il database '%DB_NAME%'.
echo Questa operazione NON PUO' ESSERE ANNULLATA.
echo Assicurati di avere un backup recente se necessario.
echo.

REM --- Conferma ---
set /p "confirm=Sei assolutamente sicuro di voler procedere? (s/n): "
if /i not "%confirm%"=="s" (
    echo Operazione annullata dall'utente.
    goto :end
)

REM --- Esecuzione ---
echo.
echo Tentativo di cancellare il database '%DB_NAME%' come utente '%DB_USER%'.
echo Assicurati che non ci siano altre connessioni attive al database.
echo Potrebbe esserti richiesta la password per l'utente '%DB_USER%'.
echo.

dropdb -U %DB_USER% %DB_NAME%

if errorlevel 1 (
    echo ERRORE: Impossibile cancellare il database '%DB_NAME%'.
    echo Controlla l'output sopra per dettagli (es. connessioni attive, permessi, password).
) else (
    echo SUCCESSO: Il database '%DB_NAME%' è stato cancellato.
)

:end
echo.
pause
endlocal