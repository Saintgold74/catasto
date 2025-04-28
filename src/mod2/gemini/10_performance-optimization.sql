-- Imposta lo schema
SET search_path TO catasto;

-- 1. Indici avanzati per migliorare le performance delle query
-- Indice per ricerca full-text su possessori
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- Estensione per indici trigram

-- Indice per ricerca full-text sui possessori
CREATE INDEX idx_trgm_possessore_nome ON possessore USING gin (nome_completo gin_trgm_ops);
CREATE INDEX idx_trgm_possessore_cognome ON possessore USING gin (cognome_nome gin_trgm_ops);

-- Indice per ricerca su immobili per natura
CREATE INDEX idx_trgm_immobile_natura ON immobile USING gin (natura gin_trgm_ops);

-- Indice per ricerca su località
CREATE INDEX idx_trgm_localita_nome ON localita USING gin (nome gin_trgm_ops);

-- 2. Funzione per la ricerca full-text avanzata sui possessori
CREATE OR REPLACE FUNCTION ricerca_avanzata_possessori(p_query TEXT)
RETURNS TABLE (
    id INTEGER,
    nome_completo VARCHAR(255),
    comune_nome VARCHAR(100),
    similarity FLOAT,
    num_partite BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.nome_completo,
        p.comune_nome,
        GREATEST(
            similarity(p.nome_completo, p_query),
            similarity(p.cognome_nome, p_query),
            similarity(p.paternita, p_query)
        ) AS similarity,
        COUNT(DISTINCT pp.partita_id) AS num_partite
    FROM possessore p
    LEFT JOIN partita_possessore pp ON p.id = pp.possessore_id
    WHERE 
        p.nome_completo ILIKE '%' || p_query || '%' OR
        p.cognome_nome ILIKE '%' || p_query || '%' OR
        p.paternita ILIKE '%' || p_query || '%'
    GROUP BY p.id, p.nome_completo, p.comune_nome
    ORDER BY similarity DESC, num_partite DESC;
END;
$$ LANGUAGE plpgsql;

-- 3. Funzione per la ricerca avanzata di immobili
CREATE OR REPLACE FUNCTION ricerca_avanzata_immobili(
    p_comune VARCHAR DEFAULT NULL,
    p_natura VARCHAR DEFAULT NULL,
    p_localita VARCHAR DEFAULT NULL,
    p_classificazione VARCHAR DEFAULT NULL,
    p_possessore VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    immobile_id INTEGER,
    natura VARCHAR(100),
    localita_nome VARCHAR(255),
    comune VARCHAR(100),
    classificazione VARCHAR(100),
    possessori TEXT,
    partita_numero INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.id AS immobile_id,
        i.natura,
        l.nome AS localita_nome,
        l.comune_nome AS comune,
        i.classificazione,
        string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
        p.numero_partita
    FROM immobile i
    JOIN localita l ON i.localita_id = l.id
    JOIN partita p ON i.partita_id = p.id
    LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
    LEFT JOIN possessore pos ON pp.possessore_id = pos.id
    WHERE 
        (p_comune IS NULL OR l.comune_nome = p_comune) AND
        (p_natura IS NULL OR i.natura ILIKE '%' || p_natura || '%') AND
        (p_localita IS NULL OR l.nome ILIKE '%' || p_localita || '%') AND
        (p_classificazione IS NULL OR i.classificazione = p_classificazione) AND
        (p_possessore IS NULL OR pos.nome_completo ILIKE '%' || p_possessore || '%')
    GROUP BY i.id, i.natura, l.nome, l.comune_nome, i.classificazione, p.numero_partita
    ORDER BY l.comune_nome, l.nome, i.natura;
END;
$$ LANGUAGE plpgsql;

-- 4. Funzione per la manutenzione automatica del database
CREATE OR REPLACE PROCEDURE manutenzione_database()
LANGUAGE plpgsql
AS $$
DECLARE
    v_tabella record;
    v_sql text;
BEGIN
    -- Vacuum e analisi di tutte le tabelle
    FOR v_tabella IN (
        SELECT tablename FROM pg_tables WHERE schemaname = 'catasto'
    ) LOOP
        v_sql := 'VACUUM ANALYZE catasto.' || quote_ident(v_tabella.tablename);
        EXECUTE v_sql;
        RAISE NOTICE 'Eseguito VACUUM ANALYZE su %', v_tabella.tablename;
    END LOOP;
    
    -- Aggiornamento delle statistiche
    ANALYZE VERBOSE;
    
    -- Aggiornamento delle viste materializzate
    CALL aggiorna_tutte_statistiche();
    
    RAISE NOTICE 'Manutenzione del database completata con successo';
END;
$$;

-- 5. Funzione per analizzare le query lente
CREATE OR REPLACE FUNCTION analizza_query_lente(p_min_duration_ms INTEGER DEFAULT 1000)
RETURNS TABLE (
    query_id TEXT,
    durata_ms FLOAT,
    chiamate BIGINT,
    righe_restituite BIGINT,
    query_text TEXT
) AS $$
BEGIN
    -- Questa funzione richiede l'estensione pg_stat_statements
    -- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
    
    RETURN QUERY
    SELECT 
        s.queryid::text,
        s.mean_exec_time AS durata_ms,
        s.calls AS chiamate,
        s.rows AS righe_restituite,
        s.query AS query_text
    FROM pg_stat_statements s
    WHERE s.dbid = (SELECT oid FROM pg_database WHERE datname = current_database())
    AND s.mean_exec_time > p_min_duration_ms
    ORDER BY s.mean_exec_time DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- 6. Procedura per verificare la frammentazione degli indici
CREATE OR REPLACE PROCEDURE controlla_frammentazione_indici()
LANGUAGE plpgsql
AS $$
DECLARE
    v_sql text;
    v_record record;
BEGIN
    v_sql := E'CREATE TEMPORARY TABLE index_stats (\n';
    v_sql := v_sql || E'    schema_name text,\n';
    v_sql := v_sql || E'    table_name text,\n';
    v_sql := v_sql || E'    index_name text,\n';
    v_sql := v_sql || E'    bloat_ratio numeric,\n';
    v_sql := v_sql || E'    bloat_size text\n';
    v_sql := v_sql || E');\n\n';
    
    v_sql := v_sql || E'INSERT INTO index_stats\n';
    v_sql := v_sql || E'SELECT\n';
    v_sql := v_sql || E'    schemaname AS schema_name,\n';
    v_sql := v_sql || E'    tablename AS table_name,\n';
    v_sql := v_sql || E'    indexrelname AS index_name,\n';
    v_sql := v_sql || E'    ROUND(100 * (pg_relation_size(indexrelid) - (reltuples * avg_width)) / pg_relation_size(indexrelid)) AS bloat_ratio,\n';
    v_sql := v_sql || E'    pg_size_pretty(pg_relation_size(indexrelid)) AS bloat_size\n';
    v_sql := v_sql || E'FROM pg_index\n';
    v_sql := v_sql || E'JOIN pg_stat_user_indexes ON indexrelid = index_oid\n';
    v_sql := v_sql || E'JOIN pg_class ON indexrelid = oid\n';
    v_sql := v_sql || E'WHERE schemaname = ''catasto''\n';
    v_sql := v_sql || E'ORDER BY bloat_ratio DESC;\n\n';
    
    v_sql := v_sql || E'SELECT * FROM index_stats WHERE bloat_ratio > 30;\n';
    
    EXECUTE v_sql;
    
    FOR v_record IN SELECT * FROM index_stats WHERE bloat_ratio > 30 LOOP
        RAISE NOTICE 'Indice frammentato: %.% (%.%). Frammentazione: %, Dimensione: %',
    		v_record.schema_name, v_record.index_name, v_record.schema_name, v_record.table_name,
    		v_record.bloat_ratio, v_record.bloat_size;
    END LOOP;
    
    DROP TABLE IF EXISTS index_stats;
END;
$$;

-- 7. Funzione per ottenere suggerimenti di ottimizzazione
CREATE OR REPLACE FUNCTION suggerimenti_ottimizzazione()
RETURNS TEXT AS $$
DECLARE
    v_result TEXT := '';
    v_sql TEXT;
    v_count INTEGER;
BEGIN
    -- Tabelle senza statistiche aggiornate
    v_sql := 'SELECT COUNT(*) FROM pg_stat_user_tables WHERE schemaname = ''catasto'' AND last_analyze IS NULL';
    EXECUTE v_sql INTO v_count;
    IF v_count > 0 THEN
        v_result := v_result || v_count || ' tabelle senza statistiche aggiornate. Esegui ANALYZE catasto.<table>.\n';
    END IF;
    
    -- Tabelle con molti update/delete (potenziale frammentazione)
    v_sql := 'SELECT COUNT(*) FROM pg_stat_user_tables WHERE schemaname = ''catasto'' AND (n_tup_upd + n_tup_del) > 10000';
    EXECUTE v_sql INTO v_count;
    IF v_count > 0 THEN
        v_result := v_result || v_count || ' tabelle con molti aggiornamenti/cancellazioni. Considera un VACUUM FULL.\n';
    END IF;
    
    -- Indici non utilizzati
    v_sql := 'SELECT COUNT(*) FROM pg_stat_user_indexes WHERE schemaname = ''catasto'' AND idx_scan = 0 AND idx_tup_read = 0 AND idx_tup_fetch = 0';
    EXECUTE v_sql INTO v_count;
    IF v_count > 0 THEN
        v_result := v_result || v_count || ' indici non utilizzati. Considera la rimozione per migliorare le performance.\n';
    END IF;
    
    -- Viste materializzate non aggiornate di recente
    v_sql := 'SELECT COUNT(*) FROM pg_matviews WHERE schemaname = ''catasto'' AND last_refresh < NOW() - INTERVAL ''1 day''';
    EXECUTE v_sql INTO v_count;
    IF v_count > 0 THEN
        v_result := v_result || v_count || ' viste materializzate non aggiornate di recente. Esegui REFRESH MATERIALIZED VIEW.\n';
    END IF;
    
    IF v_result = '' THEN
        v_result := 'Nessun suggerimento di ottimizzazione rilevato. Il sistema sembra ben configurato.';
    END IF;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;