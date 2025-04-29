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
    echo Nota: Se hai configurato l'autenticazione tramite .pgpass o variabile d'ambiente, puoi premere Invio.
    set /p PGPASSWORD=Inserisci la password per l'utente %DB_USER% (o lascia vuoto se gia' configurata): 
)

REM --- Ordine di esecuzione degli script SQL di STRUTTURA e FUNZIONI ---
set SQL_SCRIPTS_SETUP=02_creazione-schema-tabelle.sql 11_advanced-cadastral-features.sql 03_funzioni-procedure.sql 07_user-management.sql 06_audit-system.sql 15_integration_audit_users.sql 12_procedure_crud.sql 08_advanced-reporting.sql 10_performance-optimization.sql 09_backup-system.sql 13_workflow_integrati.sql 14_report_functions.sql

REM --- Nomi file dati e test ---
set SQL_SAMPLE_DATA_FILE="04_dati-esempio_modificato.sql"
set SQL_TEST_FILE="05_query-test.sql"

REM --- Verifica esistenza psql ---
if not exist %PSQL_PATH% (
    echo ERRORE: psql non trovato al percorso: %PSQL_PATH%
    echo Modifica la variabile PSQL_PATH nello script.
    goto :error_exit
)

REM --- Verifica Esistenza Database ---
echo Verifico se il database '%DB_NAME%' esiste...
%PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -lqt | findstr /B /C:" %DB_NAME% " > nul
if %ERRORLEVEL% == 0 (
    echo Il database '%DB_NAME%' esiste gia'.
    set /p DELETE_DB=Vuoi ELIMINARLO e ricrearlo? (s/n): 
    if /i "!DELETE_DB!" == "s" (
        echo Tentativo di eliminazione del database '%DB_NAME%'...

        echo Terminazione connessioni esistenti a '%DB_NAME%'...
        %PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -q -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '%DB_NAME%' AND pid <> pg_backend_pid();"
        REM Ignora errori qui, potrebbe non esserci nessuna connessione da terminare
        
        echo Eliminazione database...
        %PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -c "DROP DATABASE IF EXISTS %DB_NAME%;"
        if !ERRORLEVEL! neq 0 (
            echo ERRORE: Impossibile eliminare il database '%DB_NAME%'. Verifica permessi o connessioni attive.
            goto :error_exit
        )
        echo Database '%DB_NAME%' eliminato con successo.
        call :CreateDatabase
        if !ERRORLEVEL! neq 0 goto :error_exit
        call :RunSqlSetupScripts
        if !ERRORLEVEL! neq 0 goto :error_exit
        call :LoadSampleDataOptionally
    ) else (
        echo Operazione annullata dall'utente. Nessuna modifica apportata.
        goto :eof
    )
) else (
    echo Il database '%DB_NAME%' non esiste. Procedo con la creazione...
    call :CreateDatabase
    if !ERRORLEVEL! neq 0 goto :error_exit
    call :RunSqlSetupScripts
    if !ERRORLEVEL! neq 0 goto :error_exit
    call :LoadSampleDataOptionally
)

echo.
echo --- Configurazione Database Completata con Successo ---
goto :eof

REM --- Sottoprogramma per Creare il Database ---
:CreateDatabase
echo ---------------------------------
echo Esecuzione di 01_creazione-database.sql...
%PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -f "%SCRIPT_DIR%01_creazione-database.sql"
if !ERRORLEVEL! neq 0 (
    echo ERRORE durante l'esecuzione di 01_creazione-database.sql.
    exit /b 1
)
echo Script 01_creazione-database.sql eseguito con successo.
exit /b 0

REM --- Sottoprogramma per Eseguire gli Script SQL di Setup ---
:RunSqlSetupScripts
echo ---------------------------------
echo Esecuzione script SQL di setup sul database '%DB_NAME%'...
for %%s in (%SQL_SCRIPTS_SETUP%) do (
    echo ---------------------------------
    echo Esecuzione di %%s...
    %PSQL_PATH% -U %DB_USER% -d %DB_NAME% -v ON_ERROR_STOP=1 -f "%SCRIPT_DIR%%%s"
    if !ERRORLEVEL! neq 0 (
        echo ERRORE durante l'esecuzione di %%s. Script interrotto.
        exit /b 1
    )
    echo Script %%s eseguito con successo.
)
exit /b 0

REM --- Sottoprogramma per Caricare Dati Esempio (Opzionale) ---
:LoadSampleDataOptionally
echo ---------------------------------
set /p LOAD_SAMPLE_DATA=Vuoi caricare i dati di esempio (%SQL_SAMPLE_DATA_FILE%)? (s/n): 
if /i "!LOAD_SAMPLE_DATA!" == "s" (
    echo ---------------------------------
    echo Esecuzione di %SQL_SAMPLE_DATA_FILE%...
    %PSQL_PATH% -U %DB_USER% -d %DB_NAME% -v ON_ERROR_STOP=1 -f "%SCRIPT_DIR%%SQL_SAMPLE_DATA_FILE%"
    if !ERRORLEVEL! neq 0 (
        echo ERRORE durante l'esecuzione di %SQL_SAMPLE_DATA_FILE%. 
        echo Controlla l'output sopra per errori specifici (es. dati duplicati?).
        exit /b 1
    )
    echo Script %SQL_SAMPLE_DATA_FILE% eseguito con successo.
    
    REM --- Chiedi se eseguire test SOLO se i dati sono stati caricati ---
    echo ---------------------------------
    set /p RUN_TESTS=Vuoi eseguire lo script di test (%SQL_TEST_FILE%)? (s/n): 
    if /i "!RUN_TESTS!" == "s" (
         echo ---------------------------------
         echo Esecuzione di %SQL_TEST_FILE%...
        %PSQL_PATH% -U %DB_USER% -d %DB_NAME% -v ON_ERROR_STOP=1 -f "%SCRIPT_DIR%%SQL_TEST_FILE%"
        if !ERRORLEVEL! neq 0 (
            echo ERRORE durante l'esecuzione di %SQL_TEST_FILE%. Script interrotto.
             exit /b 1
        )
        echo Script %SQL_TEST_FILE% eseguito con successo.
    ) else (
        echo Script di test %SQL_TEST_FILE% non eseguito.
    )
    
) else (
    echo Dati di esempio %SQL_SAMPLE_DATA_FILE% non caricati.
    echo Script di test %SQL_TEST_FILE% non eseguito (richiede dati di esempio).
)
exit /b 0

:error_exit
echo.
echo *** Operazione Interrotta a causa di un Errore ***
goto :eof

:eof
endlocal
echo.
echo Contenuto di SQL_SCRIPTS_SETUP: %SQL_SCRIPTS_SETUP%
pause
echo Premere un tasto per uscire...
pause > nul