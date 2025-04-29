@echo off
setlocal enabledelayedexpansion

REM --- Impostazioni Configurabili ---
set DB_NAME=catasto_storico
set DB_USER=postgres
set DB_MAINTENANCE_DB=postgres REM Database a cui connettersi per creare/eliminare DB_NAME
set PSQL_PATH="C:\Program Files\PostgreSQL\16\bin\psql.exe" REM Modifica se necessario
set SCRIPT_DIR=%~dp0 REM Directory contenente gli script SQL
set PGHOST=localhost
set PGPORT=5432

REM --- Password (Opzione 1: Imposta qui - Meno sicuro) ---
REM set PGPASSWORD=Markus74

REM --- Password (Opzione 2: Richiedi all'utente - Più sicuro) ---
if not defined PGPASSWORD (
    set /p PGPASSWORD=Inserisci la password per l'utente %DB_USER%: 
)

REM --- Ordine di esecuzione degli script SQL (basato sulla discussione precedente) ---
set SQL_SCRIPTS=( ^
    "02_creazione-schema-tabelle.sql" ^
    "11_advanced-cadastral-features.sql" ^
    "03_funzioni-procedure.sql" ^
    "07_user-management.sql" ^
    "06_audit-system.sql" ^
    "15_integration_audit_users.sql" ^
    "12_procedure_crud.sql" ^
    "08_advanced-reporting.sql" ^
    "10_performance-optimization.sql" ^
    "09_backup-system.sql" ^
    "13_workflow_integrati.sql" ^
    "14_report_functions.sql" ^
    "04_dati-esempio_modificato.sql" ^
    "05_query-test.sql" ^
)

REM --- Verifica esistenza psql ---
if not exist %PSQL_PATH% (
    echo ERRORE: psql non trovato al percorso: %PSQL_PATH%
    echo Modifica la variabile PSQL_PATH nello script.
    goto :eof
)

REM --- Verifica Esistenza Database ---
echo Verifico se il database '%DB_NAME%' esiste...
%PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -lqt | findstr /B /C:" %DB_NAME% " > nul
if %ERRORLEVEL% == 0 (
    echo Il database '%DB_NAME%' esiste gia'.
    set /p DELETE_DB=Vuoi eliminarlo e ricrearlo? (s/n): 
    if /i "!DELETE_DB!" == "s" (
        echo Tentativo di eliminazione del database '%DB_NAME%'...

        echo Terminazione connessioni esistenti a '%DB_NAME%'...
        %PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '%DB_NAME%' AND pid <> pg_backend_pid();"
        if !ERRORLEVEL! neq 0 ( 
            echo ATTENZIONE: Potrebbe esserci stato un errore nel terminare le connessioni.
        )
        
        echo Eliminazione database...
        %PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -c "DROP DATABASE %DB_NAME%;"
        if !ERRORLEVEL! neq 0 (
            echo ERRORE: Impossibile eliminare il database '%DB_NAME%'. Verifica permessi o connessioni attive.
            goto :eof
        )
        echo Database '%DB_NAME%' eliminato con successo.
        call :CreateDatabase
        if !ERRORLEVEL! neq 0 goto :eof
        call :RunSqlScripts
    ) else (
        echo Operazione annullata dall'utente. Nessuna modifica apportata.
        goto :eof
    )
) else (
    echo Il database '%DB_NAME%' non esiste. Procedo con la creazione...
    call :CreateDatabase
    if !ERRORLEVEL! neq 0 goto :eof
    call :RunSqlScripts
)

echo --- Configurazione Database Completata ---
goto :eof

REM --- Sottoprogramma per Creare il Database ---
:CreateDatabase
echo Esecuzione di 01_creazione-database.sql...
%PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -f "%SCRIPT_DIR%01_creazione-database.sql"
if !ERRORLEVEL! neq 0 (
    echo ERRORE durante l'esecuzione di 01_creazione-database.sql.
    exit /b 1
)
echo Script 01_creazione-database.sql eseguito con successo.
exit /b 0

REM --- Sottoprogramma per Eseguire gli Script SQL ---
:RunSqlScripts
echo Esecuzione script SQL sul database '%DB_NAME%'...
for %%s in %SQL_SCRIPTS% do (
    set SQL_FILE="%%~s"
    echo ---------------------------------
    echo Esecuzione di !SQL_FILE!...
    %PSQL_PATH% -U %DB_USER% -d %DB_NAME% -v ON_ERROR_STOP=1 -f "%SCRIPT_DIR%!SQL_FILE!"
    if !ERRORLEVEL! neq 0 (
        echo ERRORE durante l'esecuzione di !SQL_FILE!. Script interrotto.
        exit /b 1
    )
    echo Script !SQL_FILE! eseguito con successo.
)
exit /b 0

:eof
endlocal
echo.
pause