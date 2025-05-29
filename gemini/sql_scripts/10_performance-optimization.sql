-- In 10_performance-optimization.sql (e da eseguire sul DB)
SET search_path TO catasto; -- Assicurati che lo schema sia corretto

CREATE OR REPLACE PROCEDURE manutenzione_database()
LANGUAGE plpgsql
AS $$
DECLARE
    v_tabella record;
    v_sql text;
BEGIN
    -- NOTA: VACUUM è stato rimosso perché non può essere eseguito da una funzione.
    --       Deve essere eseguito esternamente (es. psql, script di manutenzione).

    RAISE NOTICE 'Esecuzione ANALYZE per tabelle catasto...';
    -- Analisi di tutte le tabelle
    FOR v_tabella IN (
        SELECT tablename FROM pg_tables WHERE schemaname = 'catasto'
    ) LOOP
        v_sql := 'ANALYZE VERBOSE catasto.' || quote_ident(v_tabella.tablename);
        EXECUTE v_sql;
        -- RAISE NOTICE '  ANALYZE eseguito su %', v_tabella.tablename; -- Commentato per ridurre output
    END LOOP;

    -- Aggiornamento delle viste materializzate (se la procedura esiste)
    RAISE NOTICE 'Tentativo di aggiornamento viste materializzate...';
    BEGIN
        CALL aggiorna_tutte_statistiche(); -- Questa procedura è definita in 08_advanced-reporting.sql
        RAISE NOTICE 'Viste materializzate aggiornate.';
    EXCEPTION
        WHEN undefined_function THEN
            RAISE NOTICE 'Procedura aggiorna_tutte_statistiche() non trovata, salto aggiornamento viste.';
        WHEN OTHERS THEN
            RAISE WARNING 'Errore durante aggiornamento viste materializzate: %', SQLERRM;
    END;


    RAISE NOTICE 'Manutenzione del database (ANALYZE e REFRESH VISTE) completata con successo.';
END;
$$;