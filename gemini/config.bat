@echo off
setlocal enabledelayedexpansion

REM --- Impostazioni Configurabili ---
set DB_NAME=catasto_storico
set DB_USER=postgres
set DB_MAINTENANCE_DB=postgres
set PSQL_PATH="C:\Program Files\PostgreSQL\16\bin\psql.exe" REM Modifica se necessario
set SCRIPT_DIR=%~dp0
set PGHOST=localhost
set PGPORT=5432

REM --- Flag per stato finale ---
set SCRIPT_ERROR=0
set SCRIPT_CANCELLED=0

REM --- Password ---
if not defined PGPASSWORD (
    echo Nota: Se hai configurato l'autenticazione tramite .pgpass o variabile d'ambiente, puoi premere Invio.
    set /p PGPASSWORD=Inserisci la password per l'utente %DB_USER% (o lascia vuoto se gia' configurata): 
)

REM --- Lista Script di Setup (Definizione più semplice, una riga per chiarezza) ---
set SQL_SCRIPTS_SETUP=^
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
 "14_report_functions.sql"

REM --- Nomi file dati e test ---
set SQL_SAMPLE_DATA_FILE="04_dati-esempio_modificato.sql"
set SQL_TEST_FILE="05_query-test.sql"

REM --- Verifica esistenza psql ---
if not exist %PSQL_PATH% (
    echo ERRORE: psql non trovato al percorso: %PSQL_PATH%
    set SCRIPT_ERROR=1
    goto Cleanup
)

REM --- Inizio Logica Principale ---
echo.
echo Verifico se il database '%DB_NAME%' esiste...
set ERRORLEVEL=0
%PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -lqt | findstr /B /C:" %DB_NAME% " > nul
if %ERRORLEVEL% == 0 (
    echo Il database '%DB_NAME%' esiste gia'.
    set /p DELETE_DB=Vuoi ELIMINARLO e ricrearlo? (s/n): 
    if /i "!DELETE_DB!"=="s" (
        call :DropDatabase || (set SCRIPT_ERROR=1 && goto Cleanup)
        call :CreateDatabase || (set SCRIPT_ERROR=1 && goto Cleanup)
        call :RunSqlScripts %SQL_SCRIPTS_SETUP% || (set SCRIPT_ERROR=1 && goto Cleanup)
        call :LoadSampleDataOptionally || (set SCRIPT_ERROR=1 && goto Cleanup)
    ) else (
        echo Operazione annullata.
        set SCRIPT_CANCELLED=1
    )
) else (
    echo Il database '%DB_NAME%' non esiste. Procedo con la creazione...
    call :CreateDatabase || (set SCRIPT_ERROR=1 && goto Cleanup)
    call :RunSqlScripts %SQL_SCRIPTS_SETUP% || (set SCRIPT_ERROR=1 && goto Cleanup)
    call :LoadSampleDataOptionally || (set SCRIPT_ERROR=1 && goto Cleanup)
)

goto Cleanup


REM ==================================================
REM ===          SOTTOPROGRAMMI                    ===
REM ==================================================

:DropDatabase
    echo ---------------------------------
    echo Tentativo di eliminazione del database '%DB_NAME%'...
    echo Terminazione connessioni esistenti a '%DB_NAME%' (ignora eventuali errori)...
    %PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -q -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '%DB_NAME%' AND pid <> pg_backend_pid();" > nul 2>&1
    echo Eliminazione database...
    %PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -c "DROP DATABASE IF EXISTS %DB_NAME%;"
    if %ERRORLEVEL% neq 0 ( echo ERRORE: Impossibile eliminare il database. && exit /b 1 )
    echo Database '%DB_NAME%' eliminato.
exit /b 0

:CreateDatabase
    echo ---------------------------------
    echo Esecuzione di 01_creazione-database.sql...
    %PSQL_PATH% -U %DB_USER% -d %DB_MAINTENANCE_DB% -f "%SCRIPT_DIR%01_creazione-database.sql"
    if %ERRORLEVEL% neq 0 ( echo ERRORE durante l'esecuzione di 01_creazione-database.sql. && exit /b 1 )
    echo Script 01_creazione-database.sql eseguito.
exit /b 0

:RunSqlScripts
    echo ---------------------------------
    echo Esecuzione script SQL %* sul database '%DB_NAME%'...
    for %%s in (%*) do (
        set SQL_FILE="%%~s"
        echo ---------------------------------
        echo Esecuzione di !SQL_FILE!...
        %PSQL_PATH% -U %DB_USER% -d %DB_NAME% -v ON_ERROR_STOP=1 -f "%SCRIPT_DIR%!SQL_FILE!"
        if !ERRORLEVEL! neq 0 ( echo ERRORE durante l'esecuzione di !SQL_FILE!. && exit /b 1 )
        echo Script !SQL_FILE! eseguito.
    )
exit /b 0

:LoadSampleDataOptionally
    echo ---------------------------------
    set LOAD_SAMPLE_DATA=n
    set /p LOAD_SAMPLE_DATA=Vuoi caricare i dati di esempio (%SQL_SAMPLE_DATA_FILE%)? (s/n): 
    if /i "!LOAD_SAMPLE_DATA!"=="s" (
        echo ---------------------------------
        echo Esecuzione di %SQL_SAMPLE_DATA_FILE%...
        %PSQL_PATH% -U %DB_USER% -d %DB_NAME% -v ON_ERROR_STOP=1 -f "%SCRIPT_DIR%%SQL_SAMPLE_DATA_FILE%"
        if !ERRORLEVEL! neq 0 ( echo ERRORE durante l'esecuzione di %SQL_SAMPLE_DATA_FILE%. && exit /b 1 )
        echo Script %SQL_SAMPLE_DATA_FILE% eseguito.
        
        echo ---------------------------------
        set RUN_TESTS=n
        set /p RUN_TESTS=Vuoi eseguire lo script di test (%SQL_TEST_FILE%)? (s/n): 
        if /i "!RUN_TESTS!" == "s" (
            call :RunSqlScripts %SQL_TEST_FILE% || exit /b 1
        ) else (
            echo Script di test %SQL_TEST_FILE% non eseguito.
        )
    ) else (
        echo Dati di esempio %SQL_SAMPLE_DATA_FILE% non caricati.
        echo Script di test %SQL_TEST_FILE% non eseguito.
    )
exit /b 0


REM ==================================================
REM ===          PULIZIA E USCITA                  ===
REM ==================================================

:Cleanup
    echo ---------------------------------
    if "!SCRIPT_CANCELLED!" == "1" (
        echo Script annullato dall'utente.
    ) else if %SCRIPT_ERROR% neq 0 (
        echo *** Operazione Interrotta a causa di un Errore ***
    ) else (
        echo --- Configurazione Database Completata con Successo ---
    )

:eof
endlocal
echo.
echo Premere un tasto per uscire...
pause > nul