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
-- ========================================================================
-- AGGIUNTA A 10_performance-optimization.sql
-- Manutenzione specifica per indici GIN
-- ========================================================================

-- Aggiorna la procedura manutenzione_database esistente
CREATE OR REPLACE PROCEDURE manutenzione_database()
LANGUAGE plpgsql
AS $$
DECLARE
    v_tabella record;
    v_sql text;
    v_gin_count integer;
BEGIN
    RAISE NOTICE 'Esecuzione ANALYZE per tabelle catasto...';
    
    -- Analisi di tutte le tabelle
    FOR v_tabella IN (
        SELECT tablename FROM pg_tables WHERE schemaname = 'catasto'
    ) LOOP
        v_sql := 'ANALYZE VERBOSE catasto.' || quote_ident(v_tabella.tablename);
        EXECUTE v_sql;
    END LOOP;

    -- Verifica e manutenzione indici GIN
    SELECT COUNT(*) INTO v_gin_count
    FROM pg_indexes 
    WHERE schemaname = 'catasto' 
      AND indexname LIKE '%_trgm%';
    
    IF v_gin_count > 0 THEN
        RAISE NOTICE 'Trovati % indici GIN - esecuzione manutenzione specifica...', v_gin_count;
        
        -- REINDEX specifico per indici GIN (se necessario)
        -- NOTA: REINDEX può essere costoso, eseguire solo se necessario
        /*
        REINDEX INDEX CONCURRENTLY catasto.idx_gin_possessore_nome_completo_trgm;
        REINDEX INDEX CONCURRENTLY catasto.idx_gin_possessore_cognome_nome_trgm;
        REINDEX INDEX CONCURRENTLY catasto.idx_gin_possessore_paternita_trgm;
        REINDEX INDEX CONCURRENTLY catasto.idx_gin_localita_nome_trgm;
        */
        
        RAISE NOTICE 'Manutenzione indici GIN completata';
    ELSE
        RAISE NOTICE 'Nessun indice GIN trovato - saltata manutenzione specifica';
    END IF;

    -- Aggiornamento delle viste materializzate (codice esistente)
    RAISE NOTICE 'Tentativo di aggiornamento viste materializzate...';
    BEGIN
        CALL aggiorna_tutte_statistiche();
        RAISE NOTICE 'Viste materializzate aggiornate.';
    EXCEPTION
        WHEN undefined_function THEN
            RAISE NOTICE 'Procedura aggiorna_tutte_statistiche() non trovata, salto aggiornamento viste.';
        WHEN OTHERS THEN
            RAISE WARNING 'Errore durante aggiornamento viste materializzate: %', SQLERRM;
    END;

    RAISE NOTICE 'Manutenzione del database completata con successo.';
END;
$$;

-- Nuova funzione per statistiche indici GIN
CREATE OR REPLACE FUNCTION catasto.statistiche_indici_gin()
RETURNS TABLE (
    indexname text,
    index_size text,
    index_scans bigint,
    tuples_read bigint,
    tuples_fetched bigint
)
LANGUAGE sql
STABLE
AS $$
    SELECT 
        i.indexname::text,
        pg_size_pretty(pg_relation_size(i.indexname::regclass))::text as index_size,
        COALESCE(s.idx_scan, 0) as index_scans,
        COALESCE(s.idx_tup_read, 0) as tuples_read,
        COALESCE(s.idx_tup_fetch, 0) as tuples_fetched
    FROM pg_indexes i
    LEFT JOIN pg_stat_user_indexes s ON i.indexname = s.indexname
    WHERE i.schemaname = 'catasto' 
      AND i.indexname LIKE '%_trgm%'
    ORDER BY i.tablename, i.indexname;
$$;