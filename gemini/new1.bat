@echo off
REM Batch script per creare/aggiornare il database catasto_storico
REM Esegue gli script SQL assumendo che si trovino nella stessa cartella del .bat

SETLOCAL

REM --- Variabili Configurabili ---
SET PG_USER=postgres
REM Database a cui connettersi per creare/droppare catasto_storico (deve esistere)
SET PG_DB_ADMIN=postgres
SET PG_DB_TARGET=catasto_storico
SET PG_HOST=localhost
SET PG_PORT=5432
REM Imposta la password qui se non vuoi che venga chiesta ogni volta
REM ATTENZIONE: Salvare password in un file batch non è sicuro.
REM SET PGPASSWORD=Markus74
REM In alternativa, configura un file .pgpass

REM --- Ottieni percorso dello script ---
SET SCRIPT_DIR=%~dp0

REM --- Sequenza di Script SQL ---
REM (Assicurati che l'ordine sia corretto e che i file esistano in SCRIPT_DIR)
SET SQL_FILES=^
 01_creazione-database.sql^
 02_creazione-schema-tabelle.sql^
 03_funzioni-procedure.sql^
 07_user-management.sql^
 11_advanced-cadastral-features.sql^
 15_integration_audit_users.sql^
 12_procedure_crud.sql^
 08_advanced-reporting.sql^
 16_advanced_search.sql^
 10_performance-optimization.sql^
 09_backup-system.sql^
 13_workflow_integrati.sql^
 14_report_functions.sql^
 04_dati-esempio_modificato.sql^
 05_query-test.sql

REM --- Chiedi conferma per DROPARE il database ---
echo ATTENZIONE: Questo script TENTERA' di ELIMINARE e RICREARE il database '%PG_DB_TARGET%'.
set /p "conferma=Sei sicuro di voler continuare? (s/N): "
if /i not "%conferma%"=="s" (
    echo Operazione annullata dall'utente.
    goto EndScript
)

REM --- Drop Database (connesso a PG_DB_ADMIN) ---
echo Dropping database '%PG_DB_TARGET%' (se esiste)...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d "%PG_DB_ADMIN%" -c "DROP DATABASE IF EXISTS \"%PG_DB_TARGET%\";"
--IF ERRORLEVEL 1 (
  --  echo Errore durante il DROP del database. Controlla i log o i permessi.
  --  goto ErrorHandler
--) ELSE (
--    echo Database '%PG_DB_TARGET%' droppato (o non esisteva).
--)
echo ---------------------------------

REM --- Esecuzione Script ---
REM Il primo script (01) crea il database, quindi ci connettiamo a PG_DB_ADMIN per eseguirlo
echo Esecuzione di 01_creazione-database.sql...
psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d "%PG_DB_ADMIN%" -f "%SCRIPT_DIR%01_creazione-database.sql"
--IF ERRORLEVEL 1 (
  --  echo ERRORE durante l'esecuzione di 01_creazione-database.sql. Script interrotto.
  --  goto ErrorHandler
--) ELSE (
 --   echo Script 01_creazione-database.sql eseguito con successo
--)
--echo ---------------------------------

REM Tutti gli script successivi operano sul database target (PG_DB_TARGET)
FOR %%F IN (
 02_creazione-schema-tabelle.sql
 03_funzioni-procedure.sql
 07_user-management.sql
 11_advanced-cadastral-features.sql
 15_integration_audit_users.sql
 12_procedure_crud.sql
 08_advanced-reporting.sql
 16_advanced_search.sql
 10_performance-optimization.sql
 09_backup-system.sql
 13_workflow_integrati.sql
 14_report_functions.sql
 04_dati-esempio_modificato.sql
 05_query-test.sql
) DO (
    echo Esecuzione di %%F...
    REM Usa "%SCRIPT_DIR%%%F" per specificare il percorso completo del file SQL
    psql -h %PG_HOST% -p %PG_PORT% -U %PG_USER% -d "%PG_DB_ADMIN%" -c "DROP DATABASE IF EXISTS %PG_DB_TARGET%"
    IF ERRORLEVEL 1 (
        echo ERRORE durante l'esecuzione di %%F. Script interrotto.
        goto ErrorHandler
    ) ELSE (
        echo Script %%F eseguito con successo
    )
    echo ---------------------------------
)

echo.
echo Tutti gli script sono stati eseguiti con successo!
--goto EndScript

--:ErrorHandler
--echo.
--echo !!! SI E' VERIFICATO UN ERRORE DURANTE L'ESECUZIONE !!!
--echo Controlla l'output sopra per i dettagli.

--:EndScript
--echo.
--pause
--ENDLOCAL