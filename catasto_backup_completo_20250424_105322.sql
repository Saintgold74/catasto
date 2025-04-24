--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: catasto; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA catasto;


ALTER SCHEMA catasto OWNER TO postgres;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA catasto;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA catasto;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: aggiorna_consultazione(integer, date, character varying, character varying, text, text, character varying); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.aggiorna_consultazione(IN p_id integer, IN p_data date DEFAULT NULL::date, IN p_richiedente character varying DEFAULT NULL::character varying, IN p_documento_identita character varying DEFAULT NULL::character varying, IN p_motivazione text DEFAULT NULL::text, IN p_materiale_consultato text DEFAULT NULL::text, IN p_funzionario_autorizzante character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE consultazione
    SET data = COALESCE(p_data, data),
        richiedente = COALESCE(p_richiedente, richiedente),
        documento_identita = COALESCE(p_documento_identita, documento_identita),
        motivazione = COALESCE(p_motivazione, motivazione),
        materiale_consultato = COALESCE(p_materiale_consultato, materiale_consultato),
        funzionario_autorizzante = COALESCE(p_funzionario_autorizzante, funzionario_autorizzante)
    WHERE id = p_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consultazione con ID % non trovata', p_id;
    END IF;
    
    RAISE NOTICE 'Consultazione con ID % aggiornata con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento della consultazione: %', SQLERRM;
END;
$$;


ALTER PROCEDURE catasto.aggiorna_consultazione(IN p_id integer, IN p_data date, IN p_richiedente character varying, IN p_documento_identita character varying, IN p_motivazione text, IN p_materiale_consultato text, IN p_funzionario_autorizzante character varying) OWNER TO postgres;

--
-- Name: aggiorna_contratto(integer, character varying, date, character varying, character varying, text); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.aggiorna_contratto(IN p_id integer, IN p_tipo character varying DEFAULT NULL::character varying, IN p_data_contratto date DEFAULT NULL::date, IN p_notaio character varying DEFAULT NULL::character varying, IN p_repertorio character varying DEFAULT NULL::character varying, IN p_note text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE contratto
    SET tipo = COALESCE(p_tipo, tipo),
        data_contratto = COALESCE(p_data_contratto, data_contratto),
        notaio = COALESCE(p_notaio, notaio),
        repertorio = COALESCE(p_repertorio, repertorio),
        note = COALESCE(p_note, note)
    WHERE id = p_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contratto con ID % non trovato', p_id;
    END IF;
    
    RAISE NOTICE 'Contratto con ID % aggiornato con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento del contratto: %', SQLERRM;
END;
$$;


ALTER PROCEDURE catasto.aggiorna_contratto(IN p_id integer, IN p_tipo character varying, IN p_data_contratto date, IN p_notaio character varying, IN p_repertorio character varying, IN p_note text) OWNER TO postgres;

--
-- Name: aggiorna_immobile(integer, character varying, integer, integer, character varying, character varying, integer); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.aggiorna_immobile(IN p_id integer, IN p_natura character varying DEFAULT NULL::character varying, IN p_numero_piani integer DEFAULT NULL::integer, IN p_numero_vani integer DEFAULT NULL::integer, IN p_consistenza character varying DEFAULT NULL::character varying, IN p_classificazione character varying DEFAULT NULL::character varying, IN p_localita_id integer DEFAULT NULL::integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE immobile
    SET natura = COALESCE(p_natura, natura),
        numero_piani = COALESCE(p_numero_piani, numero_piani),
        numero_vani = COALESCE(p_numero_vani, numero_vani),
        consistenza = COALESCE(p_consistenza, consistenza),
        classificazione = COALESCE(p_classificazione, classificazione),
        localita_id = COALESCE(p_localita_id, localita_id)
    WHERE id = p_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Immobile con ID % non trovato', p_id;
    END IF;
    
    RAISE NOTICE 'Immobile con ID % aggiornato con successo', p_id;
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE EXCEPTION 'La localitÃ  specificata non esiste';
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento dell''immobile: %', SQLERRM;
END;
$$;


ALTER PROCEDURE catasto.aggiorna_immobile(IN p_id integer, IN p_natura character varying, IN p_numero_piani integer, IN p_numero_vani integer, IN p_consistenza character varying, IN p_classificazione character varying, IN p_localita_id integer) OWNER TO postgres;

--
-- Name: aggiorna_statistiche_comune(); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.aggiorna_statistiche_comune()
    LANGUAGE plpgsql
    AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_statistiche_comune;
END;
$$;


ALTER PROCEDURE catasto.aggiorna_statistiche_comune() OWNER TO postgres;

--
-- Name: aggiorna_tutte_statistiche(); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.aggiorna_tutte_statistiche()
    LANGUAGE plpgsql
    AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_statistiche_comune;
    REFRESH MATERIALIZED VIEW mv_immobili_per_tipologia;
    REFRESH MATERIALIZED VIEW mv_partite_complete;
    REFRESH MATERIALIZED VIEW mv_cronologia_variazioni;
END;
$$;


ALTER PROCEDURE catasto.aggiorna_tutte_statistiche() OWNER TO postgres;

--
-- Name: PROCEDURE aggiorna_tutte_statistiche(); Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON PROCEDURE catasto.aggiorna_tutte_statistiche() IS 'Procedura da eseguire con pg_cron o job esterno giornaliero';


--
-- Name: aggiorna_variazione(integer, character varying, date, character varying, character varying); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.aggiorna_variazione(IN p_variazione_id integer, IN p_tipo character varying DEFAULT NULL::character varying, IN p_data_variazione date DEFAULT NULL::date, IN p_numero_riferimento character varying DEFAULT NULL::character varying, IN p_nominativo_riferimento character varying DEFAULT NULL::character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE variazione
    SET tipo = COALESCE(p_tipo, tipo),
        data_variazione = COALESCE(p_data_variazione, data_variazione),
        numero_riferimento = COALESCE(p_numero_riferimento, numero_riferimento),
        nominativo_riferimento = COALESCE(p_nominativo_riferimento, nominativo_riferimento)
    WHERE id = p_variazione_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Variazione con ID % non trovata', p_variazione_id;
    END IF;
    
    RAISE NOTICE 'Variazione con ID % aggiornata con successo', p_variazione_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento della variazione: %', SQLERRM;
END;
$$;


ALTER PROCEDURE catasto.aggiorna_variazione(IN p_variazione_id integer, IN p_tipo character varying, IN p_data_variazione date, IN p_numero_riferimento character varying, IN p_nominativo_riferimento character varying) OWNER TO postgres;

--
-- Name: albero_genealogico_proprieta(integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.albero_genealogico_proprieta(p_partita_id integer) RETURNS TABLE(livello integer, tipo_relazione character varying, partita_id integer, comune_nome character varying, numero_partita integer, tipo character varying, possessori text, data_variazione date)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Crea una tabella temporanea per archiviare i risultati
    CREATE TEMPORARY TABLE IF NOT EXISTS temp_albero (
        livello INTEGER,
        tipo_relazione VARCHAR,
        partita_id INTEGER,
        comune_nome VARCHAR,
        numero_partita INTEGER,
        tipo VARCHAR,
        possessori TEXT,
        data_variazione DATE
    ) ON COMMIT DROP;
    
    -- Pulisci la tabella temporanea
    DELETE FROM temp_albero;
    
    -- Inserisci la partita corrente (radice)
    INSERT INTO temp_albero
    SELECT 
        0 AS livello,
        'corrente'::VARCHAR AS tipo_relazione,
        p.id AS partita_id,
        p.comune_nome,
        p.numero_partita,
        p.tipo,
        string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
        NULL::DATE AS data_variazione
    FROM partita p
    LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
    LEFT JOIN possessore pos ON pp.possessore_id = pos.id
    WHERE p.id = p_partita_id
    GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo;
    
    -- Ricorsione manuale per i predecessori (livelli negativi)
    FOR i IN 1..5 LOOP
        -- Aggiungi i predecessori al livello corrente
        INSERT INTO temp_albero
        SELECT 
            -i AS livello,
            'predecessore'::VARCHAR,
            p.id,
            p.comune_nome,
            p.numero_partita,
            p.tipo,
            string_agg(DISTINCT pos.nome_completo, ', '),
            v.data_variazione
        FROM partita p
        JOIN variazione v ON p.id = v.partita_origine_id
        JOIN temp_albero a ON v.partita_destinazione_id = a.partita_id
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE a.livello = -(i-1)
        GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, v.data_variazione;
    END LOOP;
    
    -- Ricorsione manuale per i successori (livelli positivi)
    FOR i IN 1..5 LOOP
        -- Aggiungi i successori al livello corrente
        INSERT INTO temp_albero
        SELECT 
            i AS livello,
            'successore'::VARCHAR,
            p.id,
            p.comune_nome,
            p.numero_partita,
            p.tipo,
            string_agg(DISTINCT pos.nome_completo, ', '),
            v.data_variazione
        FROM partita p
        JOIN variazione v ON p.id = v.partita_destinazione_id
        JOIN temp_albero a ON v.partita_origine_id = a.partita_id
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE a.livello = (i-1)
        GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, v.data_variazione;
    END LOOP;
    
    -- Restituisci i risultati dalla tabella temporanea
    RETURN QUERY
    SELECT * FROM temp_albero
    ORDER BY livello, comune_nome, numero_partita;
END;
$$;


ALTER FUNCTION catasto.albero_genealogico_proprieta(p_partita_id integer) OWNER TO postgres;

--
-- Name: analizza_query_lente(integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.analizza_query_lente(p_min_duration_ms integer DEFAULT 1000) RETURNS TABLE(query_id text, durata_ms double precision, chiamate bigint, righe_restituite bigint, query_text text)
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION catasto.analizza_query_lente(p_min_duration_ms integer) OWNER TO postgres;

--
-- Name: audit_trigger_function(); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.audit_trigger_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_old_data JSONB;
    v_new_data JSONB;
    v_utente TEXT;
BEGIN
    -- Ottieni l'utente corrente
    v_utente := CURRENT_USER;
    
    -- Determina l'operazione (INSERT, UPDATE, DELETE)
    IF TG_OP = 'INSERT' THEN
        v_old_data := NULL;
        v_new_data := to_jsonb(NEW);
        INSERT INTO audit_log (tabella, operazione, record_id, dati_prima, dati_dopo, utente)
        VALUES (TG_TABLE_NAME, 'I', NEW.id, v_old_data, v_new_data, v_utente);
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        INSERT INTO audit_log (tabella, operazione, record_id, dati_prima, dati_dopo, utente)
        VALUES (TG_TABLE_NAME, 'U', NEW.id, v_old_data, v_new_data, v_utente);
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := NULL;
        INSERT INTO audit_log (tabella, operazione, record_id, dati_prima, dati_dopo, utente)
        VALUES (TG_TABLE_NAME, 'D', OLD.id, v_old_data, v_new_data, v_utente);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$;


ALTER FUNCTION catasto.audit_trigger_function() OWNER TO postgres;

--
-- Name: backup_logico_dati(character varying, character varying); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.backup_logico_dati(IN p_directory character varying DEFAULT '/tmp'::character varying, IN p_prefisso_file character varying DEFAULT 'catasto_backup'::character varying)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_timestamp VARCHAR := TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD_HH24MISS');
    v_filename VARCHAR;
    v_command VARCHAR;
    v_tabelle TEXT;
BEGIN
    -- Costruisci il nome del file
    v_filename := p_prefisso_file || '_' || v_timestamp || '.sql';
    v_tabelle := 'comune,registro_partite,registro_matricole,possessore,partita,partita_possessore,';
    v_tabelle := v_tabelle || 'localita,immobile,partita_relazione,variazione,contratto,consultazione';
    
    -- Costruisci il comando pg_dump
    v_command := 'pg_dump -U postgres -d catasto_storico -n catasto -t catasto.' || 
                 REPLACE(v_tabelle, ',', ' -t catasto.') || 
                 ' --data-only --column-inserts -f ' || p_directory || '/' || v_filename;
    
    -- Mostra il comando da eseguire
    RAISE NOTICE 'Per eseguire il backup, esegui il seguente comando da shell:';
    RAISE NOTICE '%', v_command;
    
    -- Registra il backup nella tabella backup_registro
    INSERT INTO backup_registro (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)
    VALUES (
        v_filename, 
        CURRENT_USER, 
        NULL, -- dimensione sconosciuta fino all'esecuzione effettiva
        'dati',
        FALSE, -- da aggiornare dopo l'esecuzione effettiva
        'Backup pianificato ma non ancora eseguito', 
        p_directory || '/' || v_filename
    );
    
    RAISE NOTICE 'Backup registrato nel sistema. Eseguire manualmente il comando sopra.';
    RAISE NOTICE 'Dopo l''esecuzione, aggiornare il registro con:';
    RAISE NOTICE 'UPDATE backup_registro SET esito = TRUE, dimensione_bytes = ... WHERE nome_file = ''%'';', v_filename;
END;
$$;


ALTER PROCEDURE catasto.backup_logico_dati(IN p_directory character varying, IN p_prefisso_file character varying) OWNER TO postgres;

--
-- Name: cerca_consultazioni(date, date, character varying, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.cerca_consultazioni(p_data_inizio date DEFAULT NULL::date, p_data_fine date DEFAULT NULL::date, p_richiedente character varying DEFAULT NULL::character varying, p_funzionario character varying DEFAULT NULL::character varying) RETURNS TABLE(id integer, data date, richiedente character varying, documento_identita character varying, motivazione text, materiale_consultato text, funzionario_autorizzante character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.data,
        c.richiedente,
        c.documento_identita,
        c.motivazione,
        c.materiale_consultato,
        c.funzionario_autorizzante
    FROM consultazione c
    WHERE (p_data_inizio IS NULL OR c.data >= p_data_inizio)
      AND (p_data_fine IS NULL OR c.data <= p_data_fine)
      AND (p_richiedente IS NULL OR c.richiedente ILIKE '%' || p_richiedente || '%')
      AND (p_funzionario IS NULL OR c.funzionario_autorizzante ILIKE '%' || p_funzionario || '%')
    ORDER BY c.data DESC, c.richiedente;
END;
$$;


ALTER FUNCTION catasto.cerca_consultazioni(p_data_inizio date, p_data_fine date, p_richiedente character varying, p_funzionario character varying) OWNER TO postgres;

--
-- Name: cerca_immobili(integer, character varying, integer, character varying, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.cerca_immobili(p_partita_id integer DEFAULT NULL::integer, p_comune_nome character varying DEFAULT NULL::character varying, p_localita_id integer DEFAULT NULL::integer, p_natura character varying DEFAULT NULL::character varying, p_classificazione character varying DEFAULT NULL::character varying) RETURNS TABLE(id integer, partita_id integer, numero_partita integer, comune_nome character varying, localita_nome character varying, natura character varying, numero_piani integer, numero_vani integer, consistenza character varying, classificazione character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.id,
        i.partita_id,
        p.numero_partita,
        p.comune_nome,
        l.nome AS localita_nome,
        i.natura,
        i.numero_piani,
        i.numero_vani,
        i.consistenza,
        i.classificazione
    FROM immobile i
    JOIN partita p ON i.partita_id = p.id
    JOIN localita l ON i.localita_id = l.id
    WHERE (p_partita_id IS NULL OR i.partita_id = p_partita_id)
      AND (p_comune_nome IS NULL OR p.comune_nome = p_comune_nome)
      AND (p_localita_id IS NULL OR i.localita_id = p_localita_id)
      AND (p_natura IS NULL OR i.natura ILIKE '%' || p_natura || '%')
      AND (p_classificazione IS NULL OR i.classificazione = p_classificazione)
    ORDER BY p.comune_nome, p.numero_partita, i.natura;
END;
$$;


ALTER FUNCTION catasto.cerca_immobili(p_partita_id integer, p_comune_nome character varying, p_localita_id integer, p_natura character varying, p_classificazione character varying) OWNER TO postgres;

--
-- Name: cerca_possessori(text); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.cerca_possessori(p_query text) RETURNS TABLE(id integer, nome_completo character varying, comune_nome character varying, num_partite bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.nome_completo,
        p.comune_nome,
        COUNT(DISTINCT pp.partita_id) AS num_partite
    FROM possessore p
    LEFT JOIN partita_possessore pp ON p.id = pp.possessore_id
    WHERE 
        p.nome_completo ILIKE '%' || p_query || '%' OR
        p.cognome_nome ILIKE '%' || p_query || '%' OR
        p.paternita ILIKE '%' || p_query || '%'
    GROUP BY p.id, p.nome_completo, p.comune_nome
    ORDER BY num_partite DESC;
END;
$$;


ALTER FUNCTION catasto.cerca_possessori(p_query text) OWNER TO postgres;

--
-- Name: cerca_variazioni(character varying, date, date, integer, integer, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.cerca_variazioni(p_tipo character varying DEFAULT NULL::character varying, p_data_inizio date DEFAULT NULL::date, p_data_fine date DEFAULT NULL::date, p_partita_origine_id integer DEFAULT NULL::integer, p_partita_destinazione_id integer DEFAULT NULL::integer, p_comune character varying DEFAULT NULL::character varying) RETURNS TABLE(id integer, tipo character varying, data_variazione date, partita_origine_id integer, partita_origine_numero integer, partita_destinazione_id integer, partita_destinazione_numero integer, comune_nome character varying, numero_riferimento character varying, nominativo_riferimento character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id,
        v.tipo,
        v.data_variazione,
        v.partita_origine_id,
        po.numero_partita AS partita_origine_numero,
        v.partita_destinazione_id,
        pd.numero_partita AS partita_destinazione_numero,
        po.comune_nome,
        v.numero_riferimento,
        v.nominativo_riferimento
    FROM variazione v
    JOIN partita po ON v.partita_origine_id = po.id
    LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
    WHERE (p_tipo IS NULL OR v.tipo = p_tipo)
      AND (p_data_inizio IS NULL OR v.data_variazione >= p_data_inizio)
      AND (p_data_fine IS NULL OR v.data_variazione <= p_data_fine)
      AND (p_partita_origine_id IS NULL OR v.partita_origine_id = p_partita_origine_id)
      AND (p_partita_destinazione_id IS NULL OR v.partita_destinazione_id = p_partita_destinazione_id)
      AND (p_comune IS NULL OR po.comune_nome = p_comune)
    ORDER BY v.data_variazione DESC, po.comune_nome, po.numero_partita;
END;
$$;


ALTER FUNCTION catasto.cerca_variazioni(p_tipo character varying, p_data_inizio date, p_data_fine date, p_partita_origine_id integer, p_partita_destinazione_id integer, p_comune character varying) OWNER TO postgres;

--
-- Name: collega_partita_possessore(integer, integer, character varying, character varying, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.collega_partita_possessore(p_partita_id integer, p_possessore_id integer, p_tipo_partita character varying, p_titolo character varying DEFAULT 'proprietÃ  esclusiva'::character varying, p_quota character varying DEFAULT NULL::character varying) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se il collegamento esiste giÃ 
    SELECT id INTO v_id FROM partita_possessore 
    WHERE partita_id = p_partita_id AND possessore_id = p_possessore_id;
    
    IF v_id IS NULL THEN
        -- Crea il nuovo collegamento
        INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) 
        VALUES (p_partita_id, p_possessore_id, p_tipo_partita, p_titolo, p_quota)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Collegamento partita-possessore creato con ID %', v_id;
    ELSE
        RAISE NOTICE 'Collegamento partita-possessore giÃ  esistente con ID %', v_id;
        -- Aggiorna i dati se necessario
        UPDATE partita_possessore 
        SET tipo_partita = p_tipo_partita,
            titolo = p_titolo, 
            quota = p_quota
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$;


ALTER FUNCTION catasto.collega_partita_possessore(p_partita_id integer, p_possessore_id integer, p_tipo_partita character varying, p_titolo character varying, p_quota character varying) OWNER TO postgres;

--
-- Name: controlla_frammentazione_indici(); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.controlla_frammentazione_indici()
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


ALTER PROCEDURE catasto.controlla_frammentazione_indici() OWNER TO postgres;

--
-- Name: crea_utente(character varying, character varying, character varying, character varying, character varying); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.crea_utente(IN p_username character varying, IN p_password character varying, IN p_nome_completo character varying, IN p_email character varying, IN p_ruolo character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO utente (username, password_hash, nome_completo, email, ruolo)
    VALUES (p_username, p_password, p_nome_completo, p_email, p_ruolo);
END;
$$;


ALTER PROCEDURE catasto.crea_utente(IN p_username character varying, IN p_password character varying, IN p_nome_completo character varying, IN p_email character varying, IN p_ruolo character varying) OWNER TO postgres;

--
-- Name: duplica_partita(integer, integer, boolean, boolean); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.duplica_partita(IN p_partita_id integer, IN p_nuovo_numero_partita integer, IN p_mantenere_possessori boolean DEFAULT true, IN p_mantenere_immobili boolean DEFAULT false)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_partita_record partita%ROWTYPE;
    v_nuova_partita_id INTEGER;
    v_possessore_record RECORD;
    v_immobile_record RECORD;
BEGIN
    -- Recupera la partita originale
    SELECT * INTO v_partita_record FROM partita WHERE id = p_partita_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita con ID % non trovata', p_partita_id;
    END IF;
    
    -- Verifica che il nuovo numero partita non esista giÃ 
    PERFORM 1 FROM partita 
    WHERE comune_nome = v_partita_record.comune_nome AND numero_partita = p_nuovo_numero_partita;
    
    IF FOUND THEN
        RAISE EXCEPTION 'Esiste giÃ  una partita con numero % nel comune %', 
                        p_nuovo_numero_partita, v_partita_record.comune_nome;
    END IF;
    
    -- Crea la nuova partita
    INSERT INTO partita(
        comune_nome, numero_partita, tipo, data_impianto, numero_provenienza, stato
    ) VALUES (
        v_partita_record.comune_nome, 
        p_nuovo_numero_partita, 
        v_partita_record.tipo, 
        CURRENT_DATE, 
        v_partita_record.numero_partita, 
        'attiva'
    )
    RETURNING id INTO v_nuova_partita_id;
    
    -- Duplica i possessori se richiesto
    IF p_mantenere_possessori THEN
        FOR v_possessore_record IN 
            SELECT * FROM partita_possessore WHERE partita_id = p_partita_id
        LOOP
            INSERT INTO partita_possessore(
                partita_id, possessore_id, tipo_partita, titolo, quota
            ) VALUES (
                v_nuova_partita_id,
                v_possessore_record.possessore_id,
                v_possessore_record.tipo_partita,
                v_possessore_record.titolo,
                v_possessore_record.quota
            );
        END LOOP;
    END IF;
    
    -- Duplica gli immobili se richiesto
    IF p_mantenere_immobili THEN
        FOR v_immobile_record IN 
            SELECT * FROM immobile WHERE partita_id = p_partita_id
        LOOP
            INSERT INTO immobile(
                partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione
            ) VALUES (
                v_nuova_partita_id,
                v_immobile_record.localita_id,
                v_immobile_record.natura,
                v_immobile_record.numero_piani,
                v_immobile_record.numero_vani,
                v_immobile_record.consistenza,
                v_immobile_record.classificazione
            );
        END LOOP;
    END IF;
    
    RAISE NOTICE 'Partita % duplicata con successo. Nuova partita numero % con ID %',
                v_partita_record.numero_partita, p_nuovo_numero_partita, v_nuova_partita_id;
END;
$$;


ALTER PROCEDURE catasto.duplica_partita(IN p_partita_id integer, IN p_nuovo_numero_partita integer, IN p_mantenere_possessori boolean, IN p_mantenere_immobili boolean) OWNER TO postgres;

--
-- Name: elimina_consultazione(integer); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.elimina_consultazione(IN p_id integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM consultazione WHERE id = p_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consultazione con ID % non trovata', p_id;
    END IF;
    
    RAISE NOTICE 'Consultazione con ID % eliminata con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione della consultazione: %', SQLERRM;
END;
$$;


ALTER PROCEDURE catasto.elimina_consultazione(IN p_id integer) OWNER TO postgres;

--
-- Name: elimina_contratto(integer); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.elimina_contratto(IN p_id integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM contratto WHERE id = p_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contratto con ID % non trovato', p_id;
    END IF;
    
    RAISE NOTICE 'Contratto con ID % eliminato con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione del contratto: %', SQLERRM;
END;
$$;


ALTER PROCEDURE catasto.elimina_contratto(IN p_id integer) OWNER TO postgres;

--
-- Name: elimina_immobile(integer); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.elimina_immobile(IN p_id integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
    DELETE FROM immobile WHERE id = p_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Immobile con ID % non trovato', p_id;
    END IF;
    
    RAISE NOTICE 'Immobile con ID % eliminato con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione dell''immobile: %', SQLERRM;
END;
$$;


ALTER PROCEDURE catasto.elimina_immobile(IN p_id integer) OWNER TO postgres;

--
-- Name: elimina_variazione(integer, boolean, boolean); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.elimina_variazione(IN p_id integer, IN p_forza boolean DEFAULT false, IN p_ripristina_partita boolean DEFAULT false)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_count INTEGER;
    v_partita_origine_id INTEGER;
    v_data_variazione DATE;
BEGIN
    -- Verifica l'esistenza di dipendenze
    IF NOT p_forza THEN
        SELECT COUNT(*) INTO v_count FROM contratto WHERE variazione_id = p_id;
        IF v_count > 0 THEN
            RAISE EXCEPTION 'La variazione con ID % ha % contratti associati. Usa p_forza=TRUE per eliminare comunque', p_id, v_count;
        END IF;
    END IF;
    
    -- Recupera informazioni sulla partita di origine
    SELECT partita_origine_id, data_variazione 
    INTO v_partita_origine_id, v_data_variazione
    FROM variazione 
    WHERE id = p_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Variazione con ID % non trovata', p_id;
    END IF;
    
    -- Elimina i contratti collegati se p_forza=TRUE
    IF p_forza THEN
        DELETE FROM contratto WHERE variazione_id = p_id;
    END IF;
    
    -- Elimina la variazione
    DELETE FROM variazione WHERE id = p_id;
    
    -- Ripristina la partita di origine se richiesto
    IF p_ripristina_partita AND v_partita_origine_id IS NOT NULL THEN
        UPDATE partita 
        SET stato = 'attiva', 
            data_chiusura = NULL
        WHERE id = v_partita_origine_id 
          AND data_chiusura = v_data_variazione;
        
        RAISE NOTICE 'La partita di origine con ID % Ã¨ stata ripristinata come attiva', v_partita_origine_id;
    END IF;
    
    RAISE NOTICE 'Variazione con ID % eliminata con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione della variazione: %', SQLERRM;
END;
$$;


ALTER PROCEDURE catasto.elimina_variazione(IN p_id integer, IN p_forza boolean, IN p_ripristina_partita boolean) OWNER TO postgres;

--
-- Name: esporta_partita_json(integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.esporta_partita_json(p_partita_id integer) RETURNS json
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_json JSON;
BEGIN
    SELECT json_build_object(
        'partita', row_to_json(p),
        'possessori', (
            SELECT json_agg(row_to_json(pos_data))
            FROM (
                SELECT pos.*, pp.titolo, pp.quota
                FROM possessore pos
                JOIN partita_possessore pp ON pos.id = pp.possessore_id
                WHERE pp.partita_id = p.id
            ) pos_data
        ),
        'immobili', (
            SELECT json_agg(row_to_json(imm_data))
            FROM (
                SELECT i.*, l.nome as localita_nome, l.comune_nome, l.tipo as localita_tipo
                FROM immobile i
                JOIN localita l ON i.localita_id = l.id
                WHERE i.partita_id = p.id
            ) imm_data
        ),
        'variazioni', (
            SELECT json_agg(row_to_json(var_data))
            FROM (
                SELECT v.*, c.tipo as contratto_tipo, c.data_contratto, c.notaio, c.repertorio
                FROM variazione v
                LEFT JOIN contratto c ON v.id = c.variazione_id
                WHERE v.partita_origine_id = p.id OR v.partita_destinazione_id = p.id
            ) var_data
        )
    ) INTO v_json
    FROM partita p
    WHERE p.id = p_partita_id;
    
    IF v_json IS NULL THEN
        RAISE EXCEPTION 'Partita con ID % non trovata', p_partita_id;
    END IF;
    
    RETURN v_json;
END;
$$;


ALTER FUNCTION catasto.esporta_partita_json(p_partita_id integer) OWNER TO postgres;

--
-- Name: esporta_possessore_json(integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.esporta_possessore_json(p_possessore_id integer) RETURNS json
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_json JSON;
BEGIN
    SELECT json_build_object(
        'possessore', row_to_json(pos),
        'partite', (
            SELECT json_agg(row_to_json(part_data))
            FROM (
                SELECT p.*, pp.titolo, pp.quota
                FROM partita p
                JOIN partita_possessore pp ON p.id = pp.partita_id
                WHERE pp.possessore_id = pos.id
            ) part_data
        ),
        'immobili', (
            SELECT json_agg(row_to_json(imm_data))
            FROM (
                SELECT i.*, l.nome as localita_nome, p.numero_partita, p.comune_nome
                FROM immobile i
                JOIN partita p ON i.partita_id = p.id
                JOIN localita l ON i.localita_id = l.id
                JOIN partita_possessore pp ON p.id = pp.partita_id
                WHERE pp.possessore_id = pos.id
            ) imm_data
        )
    ) INTO v_json
    FROM possessore pos
    WHERE pos.id = p_possessore_id;
    
    IF v_json IS NULL THEN
        RAISE EXCEPTION 'Possessore con ID % non trovato', p_possessore_id;
    END IF;
    
    RETURN v_json;
END;
$$;


ALTER FUNCTION catasto.esporta_possessore_json(p_possessore_id integer) OWNER TO postgres;

--
-- Name: genera_certificato_proprieta(integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.genera_certificato_proprieta(p_partita_id integer) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_certificato TEXT;
    v_possessori TEXT;
    v_immobili TEXT;
    v_immobile RECORD;
    v_record RECORD;
BEGIN
    -- Recupera i dati della partita
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    
    IF NOT FOUND THEN
        RETURN 'Partita con ID ' || p_partita_id || ' non trovata';
    END IF;
    
    -- Intestazione certificato
    v_certificato := '============================================================' || E'\n';
    v_certificato := v_certificato || '                CERTIFICATO DI PROPRIETA IMMOBILIARE' || E'\n';
    v_certificato := v_certificato || '                     CATASTO STORICO ANNI ''50' || E'\n';
    v_certificato := v_certificato || '============================================================' || E'\n\n';
    
    -- Dati generali della partita
    v_certificato := v_certificato || 'COMUNE: ' || v_partita.comune_nome || E'\n';
    v_certificato := v_certificato || 'PARTITA N.: ' || v_partita.numero_partita || E'\n';
    v_certificato := v_certificato || 'TIPO: ' || v_partita.tipo || E'\n';
    v_certificato := v_certificato || 'DATA IMPIANTO: ' || v_partita.data_impianto || E'\n';
    v_certificato := v_certificato || 'STATO: ' || v_partita.stato || E'\n';
    IF v_partita.data_chiusura IS NOT NULL THEN
        v_certificato := v_certificato || 'DATA CHIUSURA: ' || v_partita.data_chiusura || E'\n';
    END IF;
    IF v_partita.numero_provenienza IS NOT NULL THEN
        v_certificato := v_certificato || 'PROVENIENZA: Partita n. ' || v_partita.numero_provenienza || E'\n';
    END IF;
    v_certificato := v_certificato || E'\n';
    
    -- Possessori della partita
    v_certificato := v_certificato || '-------------------- INTESTATARI --------------------' || E'\n';
    FOR v_record IN 
        SELECT 
            pos.nome_completo, 
            pp.titolo, 
            pp.quota
        FROM partita_possessore pp
        JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE pp.partita_id = p_partita_id
        ORDER BY pos.nome_completo
    LOOP
        v_certificato := v_certificato || '- ' || v_record.nome_completo;
        IF v_record.titolo = 'comproprieta' AND v_record.quota IS NOT NULL THEN
            v_certificato := v_certificato || ' (quota: ' || v_record.quota || ')';
        END IF;
        v_certificato := v_certificato || E'\n';
    END LOOP;
    v_certificato := v_certificato || E'\n';
    
    -- Immobili della partita
    v_certificato := v_certificato || '-------------------- IMMOBILI --------------------' || E'\n';
    FOR v_immobile IN 
        SELECT 
            i.id,
            i.natura,
            i.numero_piani,
            i.numero_vani,
            i.consistenza,
            i.classificazione,
            l.tipo AS tipo_localita,
            l.nome AS nome_localita,
            l.civico
        FROM immobile i
        JOIN localita l ON i.localita_id = l.id
        WHERE i.partita_id = p_partita_id
        ORDER BY l.nome, i.natura
    LOOP
        v_certificato := v_certificato || 'Immobile ID: ' || v_immobile.id || E'\n';
        v_certificato := v_certificato || '  Natura: ' || v_immobile.natura || E'\n';
        v_certificato := v_certificato || '  Localita: ' || v_immobile.nome_localita;
        IF v_immobile.civico IS NOT NULL THEN
            v_certificato := v_certificato || ', ' || v_immobile.civico;
        END IF;
        v_certificato := v_certificato || ' (' || v_immobile.tipo_localita || ')' || E'\n';
        
        IF v_immobile.numero_piani IS NOT NULL THEN
            v_certificato := v_certificato || '  Piani: ' || v_immobile.numero_piani || E'\n';
        END IF;
        IF v_immobile.numero_vani IS NOT NULL THEN
            v_certificato := v_certificato || '  Vani: ' || v_immobile.numero_vani || E'\n';
        END IF;
        IF v_immobile.consistenza IS NOT NULL THEN
            v_certificato := v_certificato || '  Consistenza: ' || v_immobile.consistenza || E'\n';
        END IF;
        IF v_immobile.classificazione IS NOT NULL THEN
            v_certificato := v_certificato || '  Classificazione: ' || v_immobile.classificazione || E'\n';
        END IF;
        
        v_certificato := v_certificato || E'\n';
    END LOOP;
    
    -- Verificare eventuali variazioni
    v_certificato := v_certificato || '-------------------- VARIAZIONI --------------------' || E'\n';
    FOR v_record IN 
        SELECT 
            v.tipo,
            v.data_variazione,
            v.numero_riferimento,
            p2.numero_partita AS partita_destinazione_numero,
            p2.comune_nome AS partita_destinazione_comune,
            c.tipo AS tipo_contratto,
            c.data_contratto,
            c.notaio,
            c.repertorio
        FROM variazione v
        LEFT JOIN partita p2 ON v.partita_destinazione_id = p2.id
        LEFT JOIN contratto c ON v.id = c.variazione_id
        WHERE v.partita_origine_id = p_partita_id
        ORDER BY v.data_variazione DESC
    LOOP
        v_certificato := v_certificato || 'Variazione: ' || v_record.tipo || ' del ' || v_record.data_variazione || E'\n';
        IF v_record.partita_destinazione_numero IS NOT NULL THEN
            v_certificato := v_certificato || '  Nuova partita: ' || v_record.partita_destinazione_numero;
            IF v_record.partita_destinazione_comune != v_partita.comune_nome THEN
                v_certificato := v_certificato || ' (Comune: ' || v_record.partita_destinazione_comune || ')';
            END IF;
            v_certificato := v_certificato || E'\n';
        END IF;
        IF v_record.tipo_contratto IS NOT NULL THEN
            v_certificato := v_certificato || '  Contratto: ' || v_record.tipo_contratto || ' del ' || v_record.data_contratto || E'\n';
            IF v_record.notaio IS NOT NULL THEN
                v_certificato := v_certificato || '  Notaio: ' || v_record.notaio || E'\n';
            END IF;
            IF v_record.repertorio IS NOT NULL THEN
                v_certificato := v_certificato || '  Repertorio: ' || v_record.repertorio || E'\n';
            END IF;
        END IF;
        v_certificato := v_certificato || E'\n';
    END LOOP;
    
    -- PiÃ¨ di pagina certificato
    v_certificato := v_certificato || '============================================================' || E'\n';
    v_certificato := v_certificato || 'Certificato generato il: ' || CURRENT_DATE || E'\n';
    v_certificato := v_certificato || 'Il presente certificato ha valore puramente storico e documentale.' || E'\n';
    v_certificato := v_certificato || '============================================================' || E'\n';
    
    RETURN v_certificato;
END;
$$;


ALTER FUNCTION catasto.genera_certificato_proprieta(p_partita_id integer) OWNER TO postgres;

--
-- Name: genera_report_comune(character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.genera_report_comune(p_comune_nome character varying) RETURNS TABLE(comune character varying, totale_partite bigint, totale_possessori bigint, totale_immobili bigint, partite_attive bigint, partite_inattive bigint, immobili_per_classe json, possessori_per_partita numeric)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    WITH stats AS (
        SELECT
            p.comune_nome,
            COUNT(DISTINCT p.id) AS totale_partite,
            COUNT(DISTINCT pos.id) AS totale_possessori,
            COUNT(DISTINCT i.id) AS totale_immobili,
            COUNT(DISTINCT CASE WHEN p.stato = 'attiva' THEN p.id END) AS partite_attive,
            COUNT(DISTINCT CASE WHEN p.stato = 'inattiva' THEN p.id END) AS partite_inattive,
            (
                SELECT json_object_agg(classificazione, COUNT(*))
                FROM (
                    SELECT i.classificazione, COUNT(*) 
                    FROM immobile i
                    JOIN partita p2 ON i.partita_id = p2.id
                    WHERE p2.comune_nome = p_comune_nome
                    GROUP BY i.classificazione
                ) imm_class
            ) AS immobili_per_classe,
            CASE 
                WHEN COUNT(DISTINCT p.id) = 0 THEN 0
                ELSE COUNT(DISTINCT pos.id)::NUMERIC / COUNT(DISTINCT p.id)
            END AS possessori_per_partita
        FROM comune c
        LEFT JOIN partita p ON c.nome = p.comune_nome
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        LEFT JOIN immobile i ON p.id = i.partita_id
        WHERE c.nome = p_comune_nome
        GROUP BY c.nome
    )
    SELECT 
        s.comune_nome,
        s.totale_partite,
        s.totale_possessori,
        s.totale_immobili,
        s.partite_attive,
        s.partite_inattive,
        s.immobili_per_classe,
        s.possessori_per_partita
    FROM stats s;
END;
$$;


ALTER FUNCTION catasto.genera_report_comune(p_comune_nome character varying) OWNER TO postgres;

--
-- Name: genera_report_consultazioni(date, date, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.genera_report_consultazioni(p_data_inizio date DEFAULT NULL::date, p_data_fine date DEFAULT NULL::date, p_richiedente character varying DEFAULT NULL::character varying) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_report TEXT;
    v_record RECORD;
    v_count INTEGER := 0;
BEGIN
    -- Intestazione report
    v_report := '============================================================' || E'\n';
    v_report := v_report || '              REPORT DELLE CONSULTAZIONI' || E'\n';
    v_report := v_report || '                CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';
    
    -- Parametri di ricerca
    v_report := v_report || 'PARAMETRI DI RICERCA:' || E'\n';
    IF p_data_inizio IS NOT NULL THEN
        v_report := v_report || 'Data inizio: ' || p_data_inizio || E'\n';
    END IF;
    IF p_data_fine IS NOT NULL THEN
        v_report := v_report || 'Data fine: ' || p_data_fine || E'\n';
    END IF;
    IF p_richiedente IS NOT NULL THEN
        v_report := v_report || 'Richiedente: ' || p_richiedente || E'\n';
    END IF;
    v_report := v_report || E'\n';
    
    -- Elenco delle consultazioni
    v_report := v_report || '-------------------- CONSULTAZIONI --------------------' || E'\n';
    
    FOR v_record IN 
        SELECT 
            c.id,
            c.data,
            c.richiedente,
            c.documento_identita,
            c.motivazione,
            c.materiale_consultato,
            c.funzionario_autorizzante
        FROM consultazione c
        WHERE (p_data_inizio IS NULL OR c.data >= p_data_inizio)
          AND (p_data_fine IS NULL OR c.data <= p_data_fine)
          AND (p_richiedente IS NULL OR c.richiedente ILIKE '%' || p_richiedente || '%')
        ORDER BY c.data DESC, c.richiedente
    LOOP
        v_count := v_count + 1;
        v_report := v_report || 'Consultazione ID: ' || v_record.id || ' - ' || v_record.data || E'\n';
        v_report := v_report || '  Richiedente: ' || v_record.richiedente || E'\n';
        IF v_record.documento_identita IS NOT NULL THEN
            v_report := v_report || '  Documento: ' || v_record.documento_identita || E'\n';
        END IF;
        IF v_record.motivazione IS NOT NULL THEN
            v_report := v_report || '  Motivazione: ' || v_record.motivazione || E'\n';
        END IF;
        v_report := v_report || '  Materiale consultato: ' || v_record.materiale_consultato || E'\n';
        v_report := v_report || '  Funzionario autorizzante: ' || v_record.funzionario_autorizzante || E'\n';
        v_report := v_report || E'\n';
    END LOOP;
    
    IF v_count = 0 THEN
        v_report := v_report || 'Nessuna consultazione trovata per i parametri specificati.' || E'\n\n';
    ELSE
        v_report := v_report || 'Totale consultazioni: ' || v_count || E'\n\n';
    END IF;
    
    -- PiÃ¨ di pagina report
    v_report := v_report || '============================================================' || E'\n';
    v_report := v_report || 'Report generato il: ' || CURRENT_DATE || E'\n';
    v_report := v_report || '============================================================' || E'\n';
    
    RETURN v_report;
END;
$$;


ALTER FUNCTION catasto.genera_report_consultazioni(p_data_inizio date, p_data_fine date, p_richiedente character varying) OWNER TO postgres;

--
-- Name: genera_report_genealogico(integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.genera_report_genealogico(p_partita_id integer) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_report TEXT;
    v_record RECORD;
    v_predecessori_trovati BOOLEAN := FALSE;
    v_successori_trovati BOOLEAN := FALSE;
    v_possessori TEXT := '';
BEGIN
    -- Recupera i dati della partita
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    
    IF NOT FOUND THEN
        RETURN 'Partita con ID ' || p_partita_id || ' non trovata';
    END IF;
    
    -- Intestazione report
    v_report := '============================================================' || E'\n';
    v_report := v_report || '              REPORT GENEALOGICO DELLA PROPRIETA' || E'\n';
    v_report := v_report || '                   CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';
    
    -- Dati generali della partita
    v_report := v_report || 'COMUNE: ' || v_partita.comune_nome || E'\n';
    v_report := v_report || 'PARTITA N.: ' || v_partita.numero_partita || E'\n';
    v_report := v_report || 'TIPO: ' || v_partita.tipo || E'\n';
    v_report := v_report || 'DATA IMPIANTO: ' || v_partita.data_impianto || E'\n';
    v_report := v_report || 'STATO: ' || v_partita.stato || E'\n';
    IF v_partita.data_chiusura IS NOT NULL THEN
        v_report := v_report || 'DATA CHIUSURA: ' || v_partita.data_chiusura || E'\n';
    END IF;
    v_report := v_report || E'\n';
    
    -- Possessori della partita
    v_report := v_report || '-------------------- INTESTATARI --------------------' || E'\n';
    FOR v_record IN 
        SELECT 
            pos.nome_completo, 
            pp.titolo, 
            pp.quota
        FROM partita_possessore pp
        JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE pp.partita_id = p_partita_id
    LOOP
        v_report := v_report || '- ' || v_record.nome_completo;
        IF v_record.titolo = 'comproprieta' AND v_record.quota IS NOT NULL THEN
            v_report := v_report || ' (quota: ' || v_record.quota || ')';
        END IF;
        v_report := v_report || E'\n';
    END LOOP;
    v_report := v_report || E'\n';
    
    -- Predecessori (da dove proviene la partita)
    v_report := v_report || '-------------------- PREDECESSORI --------------------' || E'\n';
    
    -- Verifica se proviene da un'altra partita
    IF v_partita.numero_provenienza IS NOT NULL THEN
        FOR v_record IN 
            SELECT 
                p.id AS partita_id,
                p.comune_nome,
                p.numero_partita,
                p.data_impianto,
                p.data_chiusura,
                STRING_AGG(pos.nome_completo, ', ') AS possessori,
                v.tipo AS tipo_variazione,
                v.data_variazione
            FROM partita p
            JOIN variazione v ON p.id = v.partita_origine_id
            LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
            LEFT JOIN possessore pos ON pp.possessore_id = pos.id
            WHERE v.partita_destinazione_id = p_partita_id
            GROUP BY p.id, p.comune_nome, p.numero_partita, p.data_impianto, p.data_chiusura, v.tipo, v.data_variazione
        LOOP
            v_predecessori_trovati := TRUE;
            v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
            v_report := v_report || '  Periodo: ' || v_record.data_impianto || ' - ';
            IF v_record.data_chiusura IS NOT NULL THEN
                v_report := v_report || v_record.data_chiusura;
            ELSE
                v_report := v_report || 'attiva';
            END IF;
            v_report := v_report || E'\n';
            v_report := v_report || '  Intestatari: ' || v_record.possessori || E'\n';
            v_report := v_report || '  Variazione: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione || E'\n';
            v_report := v_report || E'\n';
        END LOOP;
    END IF;
    
    IF NOT v_predecessori_trovati THEN
        v_report := v_report || 'Nessun predecessore trovato. Partita originale.' || E'\n\n';
    END IF;
    
    -- Successori (dove Ã¨ confluita la partita)
    v_report := v_report || '-------------------- SUCCESSORI --------------------' || E'\n';
    
    FOR v_record IN 
        SELECT 
            p.id AS partita_id,
            p.comune_nome,
            p.numero_partita,
            p.data_impianto,
            p.data_chiusura,
            STRING_AGG(pos.nome_completo, ', ') AS possessori,
            v.tipo AS tipo_variazione,
            v.data_variazione
        FROM partita p
        JOIN variazione v ON p.id = v.partita_destinazione_id
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE v.partita_origine_id = p_partita_id
        GROUP BY p.id, p.comune_nome, p.numero_partita, p.data_impianto, p.data_chiusura, v.tipo, v.data_variazione
    LOOP
        v_successori_trovati := TRUE;
        v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
        v_report := v_report || '  Periodo: ' || v_record.data_impianto || ' - ';
        IF v_record.data_chiusura IS NOT NULL THEN
            v_report := v_report || v_record.data_chiusura;
        ELSE
            v_report := v_report || 'attiva';
        END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Intestatari: ' || v_record.possessori || E'\n';
        v_report := v_report || '  Variazione: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione || E'\n';
        v_report := v_report || E'\n';
    END LOOP;
    
    IF NOT v_successori_trovati THEN
        IF v_partita.stato = 'attiva' THEN
            v_report := v_report || 'Nessun successore trovato. La partita e'''' ancora attiva.' || E'\n\n';
        ELSE
            v_report := v_report || 'Nessun successore trovato nonostante la partita sia chiusa.' || E'\n\n';
        END IF;
    END IF;
    
    -- PiÃ¨ di pagina report
    v_report := v_report || '============================================================' || E'\n';
    v_report := v_report || 'Report generato il: ' || CURRENT_DATE || E'\n';
    v_report := v_report || '============================================================' || E'\n';
    
    RETURN v_report;
END;
$$;


ALTER FUNCTION catasto.genera_report_genealogico(p_partita_id integer) OWNER TO postgres;

--
-- Name: genera_report_possessore(integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.genera_report_possessore(p_possessore_id integer) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_possessore possessore%ROWTYPE;
    v_report TEXT;
    v_record RECORD;
    v_immobile RECORD;
BEGIN
    -- Recupera i dati del possessore
    SELECT * INTO v_possessore FROM possessore WHERE id = p_possessore_id;
    
    IF NOT FOUND THEN
        RETURN 'Possessore con ID ' || p_possessore_id || ' non trovato';
    END IF;
    
    -- Intestazione report
    v_report := '============================================================' || E'\n';
    v_report := v_report || '              REPORT STORICO DEL POSSESSORE' || E'\n';
    v_report := v_report || '                CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';
    
    -- Dati generali del possessore
    v_report := v_report || 'POSSESSORE: ' || v_possessore.nome_completo || E'\n';
    IF v_possessore.paternita IS NOT NULL THEN
        v_report := v_report || 'PATERNITA: ' || v_possessore.paternita || E'\n';
    END IF;
    v_report := v_report || 'COMUNE: ' || v_possessore.comune_nome || E'\n';
    v_report := v_report || 'STATO: ' || CASE WHEN v_possessore.attivo THEN 'Attivo' ELSE 'Non attivo' END || E'\n\n';
    
    -- Elenco delle partite possedute (attuali e passate)
    v_report := v_report || '-------------------- PARTITE INTESTATE --------------------' || E'\n';
    
    FOR v_record IN 
        SELECT 
            p.id AS partita_id,
            p.comune_nome,
            p.numero_partita,
            p.tipo,
            p.data_impianto,
            p.data_chiusura,
            p.stato,
            pp.titolo,
            pp.quota,
            COUNT(i.id) AS num_immobili
        FROM partita p
        JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN immobile i ON p.id = i.partita_id
        WHERE pp.possessore_id = p_possessore_id
        GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.data_impianto, p.data_chiusura, p.stato, pp.titolo, pp.quota
        ORDER BY p.data_impianto DESC
    LOOP
        v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
        v_report := v_report || '  Tipo: ' || v_record.tipo || E'\n';
        v_report := v_report || '  Periodo: ' || v_record.data_impianto || ' - ';
        IF v_record.data_chiusura IS NOT NULL THEN
            v_report := v_report || v_record.data_chiusura;
        ELSE
            v_report := v_report || 'attiva';
        END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Stato: ' || v_record.stato || E'\n';
        v_report := v_report || '  Titolo: ' || v_record.titolo;
        IF v_record.quota IS NOT NULL THEN
            v_report := v_report || ' (quota: ' || v_record.quota || ')';
        END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Immobili: ' || v_record.num_immobili || E'\n\n';
        
        -- Elenco degli immobili per questa partita
        FOR v_immobile IN 
            SELECT 
                i.natura,
                l.nome AS localita_nome,
                l.tipo AS tipo_localita,
                i.classificazione
            FROM immobile i
            JOIN localita l ON i.localita_id = l.id
            WHERE i.partita_id = v_record.partita_id
        LOOP
            v_report := v_report || '    - ' || v_immobile.natura || ' in ' || v_immobile.localita_nome;
            IF v_immobile.classificazione IS NOT NULL THEN
                v_report := v_report || ' (' || v_immobile.classificazione || ')';
            END IF;
            v_report := v_report || E'\n';
        END LOOP;
        v_report := v_report || E'\n';
    END LOOP;
    
    -- Storia delle variazioni che coinvolgono il possessore
    v_report := v_report || '-------------------- VARIAZIONI --------------------' || E'\n';
    
    FOR v_record IN 
        SELECT 
            v.tipo AS tipo_variazione,
            v.data_variazione,
            p_orig.comune_nome AS comune_origine,
            p_orig.numero_partita AS partita_origine,
            p_dest.comune_nome AS comune_destinazione,
            p_dest.numero_partita AS partita_destinazione,
            c.tipo AS tipo_contratto,
            c.data_contratto,
            c.notaio,
            c.repertorio
        FROM variazione v
        JOIN partita p_orig ON v.partita_origine_id = p_orig.id
        LEFT JOIN partita p_dest ON v.partita_destinazione_id = p_dest.id
        LEFT JOIN contratto c ON v.id = c.variazione_id
        WHERE EXISTS (
            SELECT 1 FROM partita_possessore pp
            WHERE pp.partita_id = p_orig.id AND pp.possessore_id = p_possessore_id
        ) OR EXISTS (
            SELECT 1 FROM partita_possessore pp
            WHERE pp.partita_id = p_dest.id AND pp.possessore_id = p_possessore_id
        )
        ORDER BY v.data_variazione DESC
    LOOP
        v_report := v_report || 'Variazione: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione || E'\n';
        v_report := v_report || '  Da: Partita n. ' || v_record.partita_origine || ' (' || v_record.comune_origine || ')' || E'\n';
        IF v_record.partita_destinazione IS NOT NULL THEN
            v_report := v_report || '  A: Partita n. ' || v_record.partita_destinazione || ' (' || v_record.comune_destinazione || ')' || E'\n';
        END IF;
        IF v_record.tipo_contratto IS NOT NULL THEN
            v_report := v_report || '  Contratto: ' || v_record.tipo_contratto || ' del ' || v_record.data_contratto || E'\n';
            IF v_record.notaio IS NOT NULL THEN
                v_report := v_report || '  Notaio: ' || v_record.notaio || E'\n';
            END IF;
            IF v_record.repertorio IS NOT NULL THEN
                v_report := v_report || '  Repertorio: ' || v_record.repertorio || E'\n';
            END IF;
        END IF;
        v_report := v_report || E'\n';
    END LOOP;
    
    -- PiÃ¨ di pagina report
    v_report := v_report || '============================================================' || E'\n';
    v_report := v_report || 'Report generato il: ' || CURRENT_DATE || E'\n';
    v_report := v_report || '============================================================' || E'\n';
    
    RETURN v_report;
END;
$$;


ALTER FUNCTION catasto.genera_report_possessore(p_possessore_id integer) OWNER TO postgres;

--
-- Name: genera_script_backup_automatico(text); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.genera_script_backup_automatico(p_backup_dir text) RETURNS text
    LANGUAGE plpgsql
    AS $_$
DECLARE
    v_script TEXT;
BEGIN
    v_script := E'#!/bin/bash\n\n';
    v_script := v_script || '# Script di backup automatico per Catasto Storico\n';
    v_script := v_script || '# Creato: ' || to_char(current_timestamp, 'YYYY-MM-DD HH24:MI:SS') || '\n\n';
    
    v_script := v_script || 'BACKUP_DIR="' || p_backup_dir || '"\n';
    v_script := v_script || 'TIMESTAMP=$(date +%Y%m%d_%H%M%S)\n';
    v_script := v_script || 'FILENAME="catasto_backup_completo_${TIMESTAMP}.sql"\n';
    v_script := v_script || 'LOGFILE="backup_${TIMESTAMP}.log"\n\n';
    
    v_script := v_script || '# Creazione della directory di backup se non esiste\n';
    v_script := v_script || 'mkdir -p ${BACKUP_DIR}\n\n';
    
    v_script := v_script || '# Esecuzione del backup\n';
    v_script := v_script || 'echo "Inizio backup: $(date)" > ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || 'pg_dump -U postgres -d catasto_storico -f ${BACKUP_DIR}/${FILENAME} 2>> ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || 'RESULT=$?\n\n';
    
    v_script := v_script || '# Registrazione del backup nel database\n';
    v_script := v_script || 'if [ $RESULT -eq 0 ]; then\n';
    v_script := v_script || '    echo "Backup completato con successo: $(date)" >> ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || '    FILESIZE=$(stat -c%s "${BACKUP_DIR}/${FILENAME}")\n';
    v_script := v_script || '    psql -U postgres -d catasto_storico -c "SELECT registra_backup(''${FILENAME}'', ''backup_automatico'', ${FILESIZE}, ''completo'', TRUE, ''Backup completato con successo'', ''${BACKUP_DIR}/${FILENAME}'');" >> ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || 'else\n';
    v_script := v_script || '    echo "Errore durante il backup: $(date)" >> ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || '    psql -U postgres -d catasto_storico -c "SELECT registra_backup(''${FILENAME}'', ''backup_automatico'', NULL, ''completo'', FALSE, ''Errore durante il backup'', ''${BACKUP_DIR}/${FILENAME}'');" >> ${BACKUP_DIR}/${LOGFILE}\n';
    v_script := v_script || 'fi\n\n';
    
    v_script := v_script || '# Rimozione backup vecchi (opzionale)\n';
    v_script := v_script || 'psql -U postgres -d catasto_storico -c "CALL pulizia_backup_vecchi(30);" >> ${BACKUP_DIR}/${LOGFILE}\n';
    
    v_script := v_script || '\necho "Processo di backup terminato: $(date)" >> ${BACKUP_DIR}/${LOGFILE}\n';
    
    RETURN v_script;
END;
$_$;


ALTER FUNCTION catasto.genera_script_backup_automatico(p_backup_dir text) OWNER TO postgres;

--
-- Name: get_backup_commands(character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.get_backup_commands(p_tipo character varying DEFAULT 'completo'::character varying) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_timestamp TEXT;
    v_comando TEXT;
    v_filename TEXT;
    v_backup_dir TEXT := '/path/to/backup/directory'; -- Personalizza questo percorso
BEGIN
    v_timestamp := to_char(current_timestamp, 'YYYYMMDD_HH24MISS');
    
    IF p_tipo = 'completo' THEN
        v_filename := 'catasto_backup_completo_' || v_timestamp || '.sql';
        v_comando := 'pg_dump -U postgres -d catasto_storico -f ' || v_backup_dir || '/' || v_filename;
    ELSIF p_tipo = 'schema' THEN
        v_filename := 'catasto_backup_schema_' || v_timestamp || '.sql';
        v_comando := 'pg_dump -U postgres -d catasto_storico --schema-only -f ' || v_backup_dir || '/' || v_filename;
    ELSIF p_tipo = 'dati' THEN
        v_filename := 'catasto_backup_dati_' || v_timestamp || '.sql';
        v_comando := 'pg_dump -U postgres -d catasto_storico --data-only -f ' || v_backup_dir || '/' || v_filename;
    ELSE
        RAISE EXCEPTION 'Tipo di backup sconosciuto: %', p_tipo;
    END IF;
    
    RETURN E'-- Esegui questo comando dalla riga di comando:\n' || v_comando || E'\n\n-- Quindi registra il backup con:\nSELECT registra_backup(''' 
           || v_filename || ''', current_user, NULL, ''' || p_tipo || ''', TRUE, ''Backup completato con successo'', ''' 
           || v_backup_dir || '/' || v_filename || ''');';
END;
$$;


ALTER FUNCTION catasto.get_backup_commands(p_tipo character varying) OWNER TO postgres;

--
-- Name: get_immobili_possessore(integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.get_immobili_possessore(p_possessore_id integer) RETURNS TABLE(immobile_id integer, natura character varying, localita_nome character varying, comune character varying, partita_numero integer, tipo_partita character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT i.id, i.natura, l.nome, l.comune_nome, p.numero_partita, pp.tipo_partita
    FROM immobile i
    JOIN localita l ON i.localita_id = l.id
    JOIN partita p ON i.partita_id = p.id
    JOIN partita_possessore pp ON p.id = pp.partita_id
    WHERE pp.possessore_id = p_possessore_id AND p.stato = 'attiva';
END;
$$;


ALTER FUNCTION catasto.get_immobili_possessore(p_possessore_id integer) OWNER TO postgres;

--
-- Name: get_nome_storico(character varying, integer, integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.get_nome_storico(p_entita_tipo character varying, p_entita_id integer, p_anno integer DEFAULT EXTRACT(year FROM CURRENT_DATE)) RETURNS TABLE(nome character varying, anno_inizio integer, anno_fine integer, periodo_nome character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    WITH nomi AS (
        -- Nome storico se esiste per il periodo specificato
        SELECT 
            ns.nome,
            ns.anno_inizio,
            ns.anno_fine,
            ps.nome AS periodo_nome
        FROM nome_storico ns
        JOIN periodo_storico ps ON ns.periodo_id = ps.id
        WHERE ns.entita_tipo = p_entita_tipo
          AND ns.entita_id = p_entita_id
          AND ns.anno_inizio <= p_anno
          AND (ns.anno_fine IS NULL OR ns.anno_fine >= p_anno)
        
        UNION ALL
        
        -- Nome attuale dal comune se non c'Ã¨ un nome storico
        SELECT 
            c.nome,
            ps.anno_inizio,
            ps.anno_fine,
            ps.nome AS periodo_nome
        FROM comune c
        JOIN periodo_storico ps ON c.periodo_id = ps.id
        WHERE p_entita_tipo = 'comune'
          AND c.id = p_entita_id
          AND NOT EXISTS (
              SELECT 1 FROM nome_storico ns
              WHERE ns.entita_tipo = 'comune'
                AND ns.entita_id = c.id
                AND ns.anno_inizio <= p_anno
                AND (ns.anno_fine IS NULL OR ns.anno_fine >= p_anno)
          )
          AND ps.anno_inizio <= p_anno
          AND (ps.anno_fine IS NULL OR ps.anno_fine >= p_anno)
        
        UNION ALL
        
        -- Nome attuale dalla localitÃ  se non c'Ã¨ un nome storico
        SELECT 
            l.nome,
            ps.anno_inizio,
            ps.anno_fine,
            ps.nome AS periodo_nome
        FROM localita l
        JOIN periodo_storico ps ON l.periodo_id = ps.id
        WHERE p_entita_tipo = 'localita'
          AND l.id = p_entita_id
          AND NOT EXISTS (
              SELECT 1 FROM nome_storico ns
              WHERE ns.entita_tipo = 'localita'
                AND ns.entita_id = l.id
                AND ns.anno_inizio <= p_anno
                AND (ns.anno_fine IS NULL OR ns.anno_fine >= p_anno)
          )
          AND ps.anno_inizio <= p_anno
          AND (ps.anno_fine IS NULL OR ps.anno_fine >= p_anno)
    )
    SELECT * FROM nomi
    LIMIT 1;
END;
$$;


ALTER FUNCTION catasto.get_nome_storico(p_entita_tipo character varying, p_entita_id integer, p_anno integer) OWNER TO postgres;

--
-- Name: get_record_history(character varying, integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.get_record_history(p_tabella character varying, p_record_id integer) RETURNS TABLE(operazione character, "timestamp" timestamp without time zone, utente character varying, dati_prima jsonb, dati_dopo jsonb)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT a.operazione, a.timestamp, a.utente, a.dati_prima, a.dati_dopo
    FROM audit_log a
    WHERE a.tabella = p_tabella AND a.record_id = p_record_id
    ORDER BY a.timestamp DESC;
END;
$$;


ALTER FUNCTION catasto.get_record_history(p_tabella character varying, p_record_id integer) OWNER TO postgres;

--
-- Name: get_restore_commands(integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.get_restore_commands(p_backup_id integer) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_backup_record backup_registro%ROWTYPE;
    v_comando TEXT;
BEGIN
    SELECT * INTO v_backup_record FROM backup_registro WHERE id = p_backup_id;
    
    IF v_backup_record.id IS NULL THEN
        RAISE EXCEPTION 'Backup ID % non trovato', p_backup_id;
    END IF;
    
    v_comando := 'psql -U postgres -d catasto_storico -f ' || v_backup_record.percorso_file;
    
    RETURN E'-- Esegui questo comando dalla riga di comando per ripristinare il backup:\n' || v_comando;
END;
$$;


ALTER FUNCTION catasto.get_restore_commands(p_backup_id integer) OWNER TO postgres;

--
-- Name: ha_permesso(integer, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.ha_permesso(p_utente_id integer, p_permesso_nome character varying) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_ruolo VARCHAR(20);
    v_permesso_count INTEGER;
BEGIN
    -- Verifica se l'utente Ã¨ attivo
    SELECT ruolo INTO v_ruolo FROM utente 
    WHERE id = p_utente_id AND attivo = TRUE;
    
    IF v_ruolo IS NULL THEN
        RETURN FALSE; -- Utente non trovato o non attivo
    END IF;
    
    -- Gli amministratori hanno tutti i permessi
    IF v_ruolo = 'admin' THEN
        RETURN TRUE;
    END IF;
    
    -- Verifica permessi specifici
    SELECT COUNT(*) INTO v_permesso_count
    FROM utente_permesso up
    JOIN permesso p ON up.permesso_id = p.id
    WHERE up.utente_id = p_utente_id AND p.nome = p_permesso_nome;
    
    RETURN v_permesso_count > 0;
END;
$$;


ALTER FUNCTION catasto.ha_permesso(p_utente_id integer, p_permesso_nome character varying) OWNER TO postgres;

--
-- Name: importa_backup(character varying, boolean); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.importa_backup(IN p_file_path character varying, IN p_solo_verifica boolean DEFAULT true)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_command VARCHAR;
BEGIN
    -- Controllo preliminare
    IF NOT p_file_path ~ '\.sql' THEN
        RAISE EXCEPTION 'Il file deve avere estensione .sql';
    END IF;
    
    -- Comando per l'importazione
    IF p_solo_verifica THEN
        -- Verifica senza eseguire realmente l'importazione
        v_command := 'psql -U postgres -d catasto_storico -f ' || p_file_path || ' -e --set ON_ERROR_STOP=on --set AUTOCOMMIT=off -c "BEGIN; ROLLBACK;"';
        
        RAISE NOTICE 'Verifica del backup senza importazione:';
        RAISE NOTICE '%', v_command;
    ELSE
        -- Importazione effettiva
        v_command := 'psql -U postgres -d catasto_storico -f ' || p_file_path || ' -e --set ON_ERROR_STOP=on';
        
        RAISE NOTICE 'Per importare il backup, esegui il comando:';
        RAISE NOTICE '%', v_command;
    END IF;
    
    RAISE NOTICE 'ATTENZIONE: L''importazione sovrascriverÃ  i dati esistenti!';
    RAISE NOTICE 'Si consiglia di eseguire un backup prima dell''importazione.';
END;
$$;


ALTER PROCEDURE catasto.importa_backup(IN p_file_path character varying, IN p_solo_verifica boolean) OWNER TO postgres;

--
-- Name: inserisci_comune_sicuro(character varying, character varying, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.inserisci_comune_sicuro(p_nome character varying, p_provincia character varying, p_regione character varying) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER;
    v_count INTEGER;
BEGIN
    -- Verifica se il comune esiste giÃ 
    SELECT COUNT(*) INTO v_count FROM comune WHERE nome = p_nome;
    
    IF v_count = 0 THEN
        -- Inserisci il nuovo comune
        INSERT INTO comune (nome, provincia, regione) 
        VALUES (p_nome, p_provincia, p_regione);
        RAISE NOTICE 'Comune % inserito con successo', p_nome;
    ELSE
        RAISE NOTICE 'Comune % giÃ  esistente, aggiornamento dati', p_nome;
        UPDATE comune SET provincia = p_provincia, regione = p_regione WHERE nome = p_nome;
    END IF;
    
    RETURN 1; -- Ritorna 1 per indicare successo
END;
$$;


ALTER FUNCTION catasto.inserisci_comune_sicuro(p_nome character varying, p_provincia character varying, p_regione character varying) OWNER TO postgres;

--
-- Name: inserisci_consultazione_sicura(date, character varying, character varying, text, text, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.inserisci_consultazione_sicura(p_data date, p_richiedente character varying, p_documento_identita character varying DEFAULT NULL::character varying, p_motivazione text DEFAULT NULL::text, p_materiale_consultato text DEFAULT NULL::text, p_funzionario_autorizzante character varying DEFAULT NULL::character varying) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se la consultazione esiste giÃ  (stessa data e richiedente)
    SELECT id INTO v_id FROM consultazione 
    WHERE data = p_data AND richiedente = p_richiedente AND materiale_consultato = p_materiale_consultato;
    
    IF v_id IS NULL THEN
        -- Inserisci la nuova consultazione
        INSERT INTO consultazione (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante) 
        VALUES (p_data, p_richiedente, p_documento_identita, p_motivazione, p_materiale_consultato, p_funzionario_autorizzante)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Consultazione inserita con ID %', v_id;
    ELSE
        RAISE NOTICE 'Consultazione giÃ  esistente con ID %', v_id;
        -- Non aggiorniamo i dati esistenti per mantenere l'integritÃ  storica
    END IF;
    
    RETURN v_id;
END;
$$;


ALTER FUNCTION catasto.inserisci_consultazione_sicura(p_data date, p_richiedente character varying, p_documento_identita character varying, p_motivazione text, p_materiale_consultato text, p_funzionario_autorizzante character varying) OWNER TO postgres;

--
-- Name: inserisci_contratto(integer, character varying, date, character varying, character varying, text); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.inserisci_contratto(IN p_variazione_id integer, IN p_tipo character varying, IN p_data_contratto date, IN p_notaio character varying DEFAULT NULL::character varying, IN p_repertorio character varying DEFAULT NULL::character varying, IN p_note text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Verifica se la variazione esiste
    PERFORM 1 FROM variazione WHERE id = p_variazione_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'La variazione con ID % non esiste', p_variazione_id;
    END IF;
    
    -- Verifica se esiste giÃ  un contratto per questa variazione
    PERFORM 1 FROM contratto WHERE variazione_id = p_variazione_id;
    
    IF FOUND THEN
        RAISE EXCEPTION 'Esiste giÃ  un contratto per la variazione con ID %', p_variazione_id;
    END IF;
    
    -- Inserisci il contratto
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (p_variazione_id, p_tipo, p_data_contratto, p_notaio, p_repertorio, p_note);
    
    RAISE NOTICE 'Contratto inserito con successo per la variazione con ID %', p_variazione_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''inserimento del contratto: %', SQLERRM;
END;
$$;


ALTER PROCEDURE catasto.inserisci_contratto(IN p_variazione_id integer, IN p_tipo character varying, IN p_data_contratto date, IN p_notaio character varying, IN p_repertorio character varying, IN p_note text) OWNER TO postgres;

--
-- Name: inserisci_contratto_sicuro(integer, character varying, date, character varying, character varying, text); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.inserisci_contratto_sicuro(p_variazione_id integer, p_tipo character varying, p_data_contratto date, p_notaio character varying DEFAULT NULL::character varying, p_repertorio character varying DEFAULT NULL::character varying, p_note text DEFAULT NULL::text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se il contratto esiste giÃ 
    SELECT id INTO v_id FROM contratto WHERE variazione_id = p_variazione_id;
    
    IF v_id IS NULL THEN
        -- Inserisci il nuovo contratto
        INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note) 
        VALUES (p_variazione_id, p_tipo, p_data_contratto, p_notaio, p_repertorio, p_note)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Contratto inserito con ID %', v_id;
    ELSE
        RAISE NOTICE 'Contratto giÃ  esistente con ID %', v_id;
        -- Aggiorna i dati se necessario
        UPDATE contratto 
        SET tipo = p_tipo,
            data_contratto = p_data_contratto,
            notaio = COALESCE(p_notaio, notaio),
            repertorio = COALESCE(p_repertorio, repertorio),
            note = COALESCE(p_note, note)
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$;


ALTER FUNCTION catasto.inserisci_contratto_sicuro(p_variazione_id integer, p_tipo character varying, p_data_contratto date, p_notaio character varying, p_repertorio character varying, p_note text) OWNER TO postgres;

--
-- Name: inserisci_immobile_sicuro(integer, integer, character varying, integer, integer, character varying, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.inserisci_immobile_sicuro(p_partita_id integer, p_localita_id integer, p_natura character varying, p_numero_piani integer DEFAULT NULL::integer, p_numero_vani integer DEFAULT NULL::integer, p_consistenza character varying DEFAULT NULL::character varying, p_classificazione character varying DEFAULT NULL::character varying) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se l'immobile esiste giÃ  (in base alla partita, localitÃ  e natura)
    SELECT id INTO v_id FROM immobile 
    WHERE partita_id = p_partita_id AND localita_id = p_localita_id AND natura = p_natura;
    
    IF v_id IS NULL THEN
        -- Inserisci il nuovo immobile
        INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) 
        VALUES (p_partita_id, p_localita_id, p_natura, p_numero_piani, p_numero_vani, p_consistenza, p_classificazione)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Immobile % inserito con ID %', p_natura, v_id;
    ELSE
        RAISE NOTICE 'Immobile % giÃ  esistente con ID %', p_natura, v_id;
        -- Aggiorna i dati se necessario
        UPDATE immobile 
        SET numero_piani = COALESCE(p_numero_piani, numero_piani),
            numero_vani = COALESCE(p_numero_vani, numero_vani),
            consistenza = COALESCE(p_consistenza, consistenza),
            classificazione = COALESCE(p_classificazione, classificazione)
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$;


ALTER FUNCTION catasto.inserisci_immobile_sicuro(p_partita_id integer, p_localita_id integer, p_natura character varying, p_numero_piani integer, p_numero_vani integer, p_consistenza character varying, p_classificazione character varying) OWNER TO postgres;

--
-- Name: inserisci_localita_sicura(character varying, character varying, character varying, integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.inserisci_localita_sicura(p_comune_nome character varying, p_nome character varying, p_tipo character varying, p_civico integer DEFAULT NULL::integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se la localitÃ  esiste giÃ 
    SELECT id INTO v_id FROM localita 
    WHERE comune_nome = p_comune_nome AND nome = p_nome AND (civico = p_civico OR (civico IS NULL AND p_civico IS NULL));
    
    IF v_id IS NULL THEN
        -- Inserisci la nuova localitÃ 
        INSERT INTO localita (comune_nome, nome, tipo, civico) 
        VALUES (p_comune_nome, p_nome, p_tipo, p_civico)
        RETURNING id INTO v_id;
        RAISE NOTICE 'LocalitÃ  % inserita con ID %', p_nome, v_id;
    ELSE
        RAISE NOTICE 'LocalitÃ  % giÃ  esistente con ID %', p_nome, v_id;
        -- Aggiorna i dati se necessario
        UPDATE localita SET tipo = p_tipo WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$;


ALTER FUNCTION catasto.inserisci_localita_sicura(p_comune_nome character varying, p_nome character varying, p_tipo character varying, p_civico integer) OWNER TO postgres;

--
-- Name: inserisci_partita_con_possessori(character varying, integer, character varying, date, integer[]); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.inserisci_partita_con_possessori(IN p_comune_nome character varying, IN p_numero_partita integer, IN p_tipo character varying, IN p_data_impianto date, IN p_possessore_ids integer[])
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_partita_id INTEGER;
    v_possessore_id INTEGER;
BEGIN
    -- Inserisci la partita
    INSERT INTO partita(comune_nome, numero_partita, tipo, data_impianto, stato)
    VALUES (p_comune_nome, p_numero_partita, p_tipo, p_data_impianto, 'attiva')
    RETURNING id INTO v_partita_id;
    
    -- Collega i possessori
    FOREACH v_possessore_id IN ARRAY p_possessore_ids
    LOOP
        INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita)
        VALUES (v_partita_id, v_possessore_id, p_tipo);
    END LOOP;
END;
$$;


ALTER PROCEDURE catasto.inserisci_partita_con_possessori(IN p_comune_nome character varying, IN p_numero_partita integer, IN p_tipo character varying, IN p_data_impianto date, IN p_possessore_ids integer[]) OWNER TO postgres;

--
-- Name: inserisci_partita_sicura(character varying, integer, character varying, date, character varying, integer, date); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.inserisci_partita_sicura(p_comune_nome character varying, p_numero_partita integer, p_tipo character varying, p_data_impianto date, p_stato character varying DEFAULT 'attiva'::character varying, p_numero_provenienza integer DEFAULT NULL::integer, p_data_chiusura date DEFAULT NULL::date) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se la partita esiste giÃ 
    SELECT id INTO v_id FROM partita 
    WHERE comune_nome = p_comune_nome AND numero_partita = p_numero_partita;
    
    IF v_id IS NULL THEN
        -- Inserisci la nuova partita
        INSERT INTO partita (comune_nome, numero_partita, tipo, data_impianto, stato, numero_provenienza, data_chiusura) 
        VALUES (p_comune_nome, p_numero_partita, p_tipo, p_data_impianto, p_stato, p_numero_provenienza, p_data_chiusura)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Partita % del comune % inserita con ID %', p_numero_partita, p_comune_nome, v_id;
    ELSE
        RAISE NOTICE 'Partita % del comune % giÃ  esistente con ID %', p_numero_partita, p_comune_nome, v_id;
        -- Aggiorna i dati se necessario
        UPDATE partita SET 
            tipo = p_tipo,
            data_impianto = p_data_impianto,
            stato = p_stato,
            numero_provenienza = p_numero_provenienza,
            data_chiusura = p_data_chiusura
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$;


ALTER FUNCTION catasto.inserisci_partita_sicura(p_comune_nome character varying, p_numero_partita integer, p_tipo character varying, p_data_impianto date, p_stato character varying, p_numero_provenienza integer, p_data_chiusura date) OWNER TO postgres;

--
-- Name: inserisci_possessore(character varying, character varying, character varying, character varying, boolean); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.inserisci_possessore(IN p_comune_nome character varying, IN p_cognome_nome character varying, IN p_paternita character varying, IN p_nome_completo character varying, IN p_attivo boolean DEFAULT true)
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO possessore(comune_nome, cognome_nome, paternita, nome_completo, attivo)
    VALUES (p_comune_nome, p_cognome_nome, p_paternita, p_nome_completo, p_attivo);
END;
$$;


ALTER PROCEDURE catasto.inserisci_possessore(IN p_comune_nome character varying, IN p_cognome_nome character varying, IN p_paternita character varying, IN p_nome_completo character varying, IN p_attivo boolean) OWNER TO postgres;

--
-- Name: inserisci_possessore_sicuro(character varying, character varying, character varying, character varying, boolean); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.inserisci_possessore_sicuro(p_comune_nome character varying, p_cognome_nome character varying, p_paternita character varying, p_nome_completo character varying, p_attivo boolean DEFAULT true) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se il possessore esiste giÃ 
    SELECT id INTO v_id FROM possessore 
    WHERE comune_nome = p_comune_nome AND nome_completo = p_nome_completo;
    
    IF v_id IS NULL THEN
        -- Inserisci il nuovo possessore
        INSERT INTO possessore (comune_nome, cognome_nome, paternita, nome_completo, attivo) 
        VALUES (p_comune_nome, p_cognome_nome, p_paternita, p_nome_completo, p_attivo)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Possessore % inserito con ID %', p_nome_completo, v_id;
    ELSE
        RAISE NOTICE 'Possessore % giÃ  esistente con ID %', p_nome_completo, v_id;
        -- Aggiorna i dati se necessario
        UPDATE possessore 
        SET cognome_nome = p_cognome_nome,
            paternita = p_paternita,
            attivo = p_attivo
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$;


ALTER FUNCTION catasto.inserisci_possessore_sicuro(p_comune_nome character varying, p_cognome_nome character varying, p_paternita character varying, p_nome_completo character varying, p_attivo boolean) OWNER TO postgres;

--
-- Name: inserisci_variazione_sicura(integer, integer, character varying, date, character varying, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.inserisci_variazione_sicura(p_partita_origine_id integer, p_partita_destinazione_id integer, p_tipo character varying, p_data_variazione date, p_numero_riferimento character varying DEFAULT NULL::character varying, p_nominativo_riferimento character varying DEFAULT NULL::character varying) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se la variazione esiste giÃ 
    SELECT id INTO v_id FROM variazione 
    WHERE partita_origine_id = p_partita_origine_id 
      AND (partita_destinazione_id = p_partita_destinazione_id OR 
           (partita_destinazione_id IS NULL AND p_partita_destinazione_id IS NULL))
      AND data_variazione = p_data_variazione;
    
    IF v_id IS NULL THEN
        -- Inserisci la nuova variazione
        INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento) 
        VALUES (p_partita_origine_id, p_partita_destinazione_id, p_tipo, p_data_variazione, p_numero_riferimento, p_nominativo_riferimento)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Variazione inserita con ID %', v_id;
    ELSE
        RAISE NOTICE 'Variazione giÃ  esistente con ID %', v_id;
        -- Aggiorna i dati se necessario
        UPDATE variazione 
        SET tipo = p_tipo,
            numero_riferimento = COALESCE(p_numero_riferimento, numero_riferimento),
            nominativo_riferimento = COALESCE(p_nominativo_riferimento, nominativo_riferimento)
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$;


ALTER FUNCTION catasto.inserisci_variazione_sicura(p_partita_origine_id integer, p_partita_destinazione_id integer, p_tipo character varying, p_data_variazione date, p_numero_riferimento character varying, p_nominativo_riferimento character varying) OWNER TO postgres;

--
-- Name: is_partita_attiva(integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.is_partita_attiva(p_partita_id integer) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_stato VARCHAR(20);
BEGIN
    SELECT stato INTO v_stato FROM partita WHERE id = p_partita_id;
    RETURN (v_stato = 'attiva');
END;
$$;


ALTER FUNCTION catasto.is_partita_attiva(p_partita_id integer) OWNER TO postgres;

--
-- Name: manutenzione_database(); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.manutenzione_database()
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


ALTER PROCEDURE catasto.manutenzione_database() OWNER TO postgres;

--
-- Name: pulizia_backup_vecchi(integer); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.pulizia_backup_vecchi(IN p_giorni_conservazione integer DEFAULT 30)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_data_limite TIMESTAMP;
    v_backup_record backup_registro%ROWTYPE;
BEGIN
    v_data_limite := current_timestamp - (p_giorni_conservazione || ' days')::INTERVAL;
    
    -- Identificare i backup da eliminare (nella pratica, qui dovremmo eliminare anche i file)
    FOR v_backup_record IN
        SELECT * FROM backup_registro
        WHERE timestamp < v_data_limite
    LOOP
        -- Qui in un sistema reale dovremmo eliminare il file fisico:
        -- PERFORM pg_catalog.pg_file_unlink(v_backup_record.percorso_file);
        
        -- Log dell'eliminazione
        RAISE NOTICE 'Backup % sarebbe stato eliminato in un sistema reale', v_backup_record.nome_file;
    END LOOP;
    
    -- Rimuovere le voci dal registro
    DELETE FROM backup_registro WHERE timestamp < v_data_limite;
END;
$$;


ALTER PROCEDURE catasto.pulizia_backup_vecchi(IN p_giorni_conservazione integer) OWNER TO postgres;

--
-- Name: registra_accesso(integer, character varying, character varying, text, boolean); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.registra_accesso(IN p_utente_id integer, IN p_azione character varying, IN p_indirizzo_ip character varying, IN p_user_agent text, IN p_esito boolean)
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Registra l'accesso
    INSERT INTO accesso_log (utente_id, azione, indirizzo_ip, user_agent, esito)
    VALUES (p_utente_id, p_azione, p_indirizzo_ip, p_user_agent, p_esito);
    
    -- Se Ã¨ un login riuscito, aggiorna l'ultimo accesso
    IF p_azione = 'login' AND p_esito = TRUE THEN
        UPDATE utente SET ultimo_accesso = CURRENT_TIMESTAMP
        WHERE id = p_utente_id;
    END IF;
END;
$$;


ALTER PROCEDURE catasto.registra_accesso(IN p_utente_id integer, IN p_azione character varying, IN p_indirizzo_ip character varying, IN p_user_agent text, IN p_esito boolean) OWNER TO postgres;

--
-- Name: registra_backup(character varying, character varying, bigint, character varying, boolean, text, text); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.registra_backup(p_nome_file character varying, p_utente character varying, p_dimensione_bytes bigint, p_tipo character varying, p_esito boolean, p_messaggio text, p_percorso_file text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_backup_id INTEGER;
BEGIN
    INSERT INTO backup_registro (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)
    VALUES (p_nome_file, p_utente, p_dimensione_bytes, p_tipo, p_esito, p_messaggio, p_percorso_file)
    RETURNING id INTO v_backup_id;
    
    RETURN v_backup_id;
END;
$$;


ALTER FUNCTION catasto.registra_backup(p_nome_file character varying, p_utente character varying, p_dimensione_bytes bigint, p_tipo character varying, p_esito boolean, p_messaggio text, p_percorso_file text) OWNER TO postgres;

--
-- Name: registra_consultazione(date, character varying, character varying, text, text, character varying); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.registra_consultazione(IN p_data date, IN p_richiedente character varying, IN p_documento_identita character varying, IN p_motivazione text, IN p_materiale_consultato text, IN p_funzionario_autorizzante character varying)
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO consultazione(data, richiedente, documento_identita, motivazione, 
                             materiale_consultato, funzionario_autorizzante)
    VALUES (p_data, p_richiedente, p_documento_identita, p_motivazione, 
           p_materiale_consultato, p_funzionario_autorizzante);
END;
$$;


ALTER PROCEDURE catasto.registra_consultazione(IN p_data date, IN p_richiedente character varying, IN p_documento_identita character varying, IN p_motivazione text, IN p_materiale_consultato text, IN p_funzionario_autorizzante character varying) OWNER TO postgres;

--
-- Name: registra_frazionamento(integer, date, character varying, date, json, character varying, character varying, text); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.registra_frazionamento(IN p_partita_origine_id integer, IN p_data_variazione date, IN p_tipo_contratto character varying, IN p_data_contratto date, IN p_nuove_partite json, IN p_notaio character varying DEFAULT NULL::character varying, IN p_repertorio character varying DEFAULT NULL::character varying, IN p_note text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_partita_origine partita%ROWTYPE;
    v_nuova_partita RECORD;
    v_nuova_partita_id INTEGER;
    v_variazione_id INTEGER;
    v_comune_nome VARCHAR(100);
    v_possessore_id INTEGER;
    v_immobile_id INTEGER;
BEGIN
    -- Recupera informazioni sulla partita di origine
    SELECT * INTO v_partita_origine FROM partita WHERE id = p_partita_origine_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita di origine con ID % non trovata', p_partita_origine_id;
    END IF;
    
    IF v_partita_origine.stato = 'inattiva' THEN
        RAISE EXCEPTION 'La partita di origine Ã¨ giÃ  inattiva';
    END IF;
    
    -- Registra la variazione principale di frazionamento
    INSERT INTO variazione(
        partita_origine_id, partita_destinazione_id, tipo, 
        data_variazione, numero_riferimento, nominativo_riferimento
    )
    VALUES (
        p_partita_origine_id, NULL, 'Frazionamento',
        p_data_variazione, 'FRAZ-' || p_partita_origine_id, 'Frazionamento partita ' || v_partita_origine.numero_partita
    )
    RETURNING id INTO v_variazione_id;
    
    -- Registra il contratto
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note);
    
    -- Processa ogni nuova partita
    FOR v_nuova_partita IN SELECT * FROM json_to_recordset(p_nuove_partite) 
        AS x(numero_partita INTEGER, comune TEXT, possessori JSON, immobili JSON)
    LOOP
        v_comune_nome := COALESCE(v_nuova_partita.comune, v_partita_origine.comune_nome);
        
        -- Verifica che la nuova partita non esista giÃ 
        IF EXISTS (SELECT 1 FROM partita WHERE comune_nome = v_comune_nome AND numero_partita = v_nuova_partita.numero_partita) THEN
            RAISE EXCEPTION 'La partita % giÃ  esiste nel comune %', v_nuova_partita.numero_partita, v_comune_nome;
        END IF;
        
        -- Crea la nuova partita
        INSERT INTO partita(comune_nome, numero_partita, tipo, data_impianto, numero_provenienza, stato)
        VALUES (v_comune_nome, v_nuova_partita.numero_partita, 'principale', p_data_variazione, v_partita_origine.numero_partita, 'attiva')
        RETURNING id INTO v_nuova_partita_id;
        
        -- Collega la nuova partita alla variazione
        UPDATE variazione 
        SET partita_destinazione_id = v_nuova_partita_id
        WHERE id = v_variazione_id;
        
        -- Collega i possessori alla nuova partita
        FOR v_possessore_id IN SELECT value::INTEGER FROM json_array_elements(v_nuova_partita.possessori)
        LOOP
            INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
            SELECT 
                v_nuova_partita_id,
                possessore_id,
                'principale',
                titolo,
                quota
            FROM partita_possessore
            WHERE partita_id = p_partita_origine_id AND possessore_id = v_possessore_id;
        END LOOP;
        
        -- Trasferisci gli immobili specificati
        FOR v_immobile_id IN SELECT value::INTEGER FROM json_array_elements(v_nuova_partita.immobili)
        LOOP
            UPDATE immobile SET partita_id = v_nuova_partita_id
            WHERE id = v_immobile_id AND partita_id = p_partita_origine_id;
            
            IF NOT FOUND THEN
                RAISE WARNING 'Immobile con ID % non trovato nella partita di origine', v_immobile_id;
            END IF;
        END LOOP;
    END LOOP;
    
    -- Verifica se tutti gli immobili sono stati trasferiti
    IF NOT EXISTS (SELECT 1 FROM immobile WHERE partita_id = p_partita_origine_id) THEN
        -- Chiudi la partita di origine se non ha piÃ¹ immobili
        UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione
        WHERE id = p_partita_origine_id;
    END IF;
    
    RAISE NOTICE 'Frazionamento della partita % registrato con successo', v_partita_origine.numero_partita;
END;
$$;


ALTER PROCEDURE catasto.registra_frazionamento(IN p_partita_origine_id integer, IN p_data_variazione date, IN p_tipo_contratto character varying, IN p_data_contratto date, IN p_nuove_partite json, IN p_notaio character varying, IN p_repertorio character varying, IN p_note text) OWNER TO postgres;

--
-- Name: registra_nome_storico(character varying, integer, character varying, integer, integer, integer, text); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.registra_nome_storico(IN p_entita_tipo character varying, IN p_entita_id integer, IN p_nome character varying, IN p_periodo_id integer, IN p_anno_inizio integer, IN p_anno_fine integer DEFAULT NULL::integer, IN p_note text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO nome_storico (entita_tipo, entita_id, nome, periodo_id, anno_inizio, anno_fine, note)
    VALUES (p_entita_tipo, p_entita_id, p_nome, p_periodo_id, p_anno_inizio, p_anno_fine, p_note);
END;
$$;


ALTER PROCEDURE catasto.registra_nome_storico(IN p_entita_tipo character varying, IN p_entita_id integer, IN p_nome character varying, IN p_periodo_id integer, IN p_anno_inizio integer, IN p_anno_fine integer, IN p_note text) OWNER TO postgres;

--
-- Name: registra_nuova_proprieta(character varying, integer, date, json, json); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.registra_nuova_proprieta(IN p_comune_nome character varying, IN p_numero_partita integer, IN p_data_impianto date, IN p_possessori json, IN p_immobili json)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_partita_id INTEGER;
    v_possessore_id INTEGER;
    v_localita_id INTEGER;
    v_possessore RECORD;
    v_immobile RECORD;
    v_possessore_ids INTEGER[] := '{}';
BEGIN
    -- Verifiche preliminari
    IF NOT EXISTS (SELECT 1 FROM comune WHERE nome = p_comune_nome) THEN
        RAISE EXCEPTION 'Il comune % non esiste', p_comune_nome;
    END IF;
    
    IF EXISTS (SELECT 1 FROM partita WHERE comune_nome = p_comune_nome AND numero_partita = p_numero_partita) THEN
        RAISE EXCEPTION 'La partita % giÃ  esiste nel comune %', p_numero_partita, p_comune_nome;
    END IF;
    
    -- Inserisci o recupera i possessori
    FOR v_possessore IN SELECT * FROM json_to_recordset(p_possessori) 
        AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT)
    LOOP
        -- Verifica se il possessore esiste giÃ 
        SELECT id INTO v_possessore_id 
        FROM possessore 
        WHERE comune_nome = p_comune_nome AND nome_completo = v_possessore.nome_completo;
        
        IF NOT FOUND THEN
            -- Crea un nuovo possessore
            INSERT INTO possessore(comune_nome, cognome_nome, paternita, nome_completo, attivo)
            VALUES (p_comune_nome, v_possessore.cognome_nome, v_possessore.paternita, v_possessore.nome_completo, TRUE)
            RETURNING id INTO v_possessore_id;
        END IF;
        
        -- Aggiungi all'array dei possessori
        v_possessore_ids := array_append(v_possessore_ids, v_possessore_id);
    END LOOP;
    
    -- Crea la partita
    INSERT INTO partita(comune_nome, numero_partita, tipo, data_impianto, stato)
    VALUES (p_comune_nome, p_numero_partita, 'principale', p_data_impianto, 'attiva')
    RETURNING id INTO v_partita_id;
    
    -- Collega i possessori alla partita
    FOR i IN 1..array_length(v_possessore_ids, 1)
    LOOP
        v_possessore_id := v_possessore_ids[i];
        
        -- Estrai la quota dal JSON originale
        SELECT quota INTO v_possessore FROM json_to_recordset(p_possessori) 
        AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT)
        OFFSET (i-1) LIMIT 1;
        
        -- Determina il titolo in base alla quota
        INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
        VALUES (
            v_partita_id, 
            v_possessore_id, 
            'principale',
            CASE WHEN v_possessore.quota IS NULL THEN 'proprietÃ  esclusiva' ELSE 'comproprietÃ ' END,
            v_possessore.quota
        );
    END LOOP;
    
    -- Crea gli immobili
    FOR v_immobile IN SELECT * FROM json_to_recordset(p_immobili) 
        AS x(natura TEXT, localita TEXT, tipo_localita TEXT, classificazione TEXT, numero_piani INTEGER, numero_vani INTEGER, consistenza TEXT)
    LOOP
        -- Verifica se la localitÃ  esiste
        SELECT id INTO v_localita_id 
        FROM localita 
        WHERE comune_nome = p_comune_nome AND nome = v_immobile.localita;
        
        IF NOT FOUND THEN
            -- Crea una nuova localitÃ 
            INSERT INTO localita(comune_nome, nome, tipo)
            VALUES (p_comune_nome, v_immobile.localita, COALESCE(v_immobile.tipo_localita, 'regione'))
            RETURNING id INTO v_localita_id;
        END IF;
        
        -- Crea l'immobile
        INSERT INTO immobile(partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
        VALUES (
            v_partita_id,
            v_localita_id,
            v_immobile.natura,
            v_immobile.numero_piani,
            v_immobile.numero_vani,
            v_immobile.consistenza,
            v_immobile.classificazione
        );
    END LOOP;
    
    RAISE NOTICE 'Registrazione completata con successo. Partita % creata con ID %', p_numero_partita, v_partita_id;
END;
$$;


ALTER PROCEDURE catasto.registra_nuova_proprieta(IN p_comune_nome character varying, IN p_numero_partita integer, IN p_data_impianto date, IN p_possessori json, IN p_immobili json) OWNER TO postgres;

--
-- Name: registra_passaggio_proprieta(integer, character varying, integer, character varying, date, character varying, date, character varying, character varying, json, integer[], text); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.registra_passaggio_proprieta(IN p_partita_origine_id integer, IN p_comune_nome character varying, IN p_numero_partita integer, IN p_tipo_variazione character varying, IN p_data_variazione date, IN p_tipo_contratto character varying, IN p_data_contratto date, IN p_notaio character varying DEFAULT NULL::character varying, IN p_repertorio character varying DEFAULT NULL::character varying, IN p_nuovi_possessori json DEFAULT NULL::json, IN p_immobili_da_trasferire integer[] DEFAULT NULL::integer[], IN p_note text DEFAULT NULL::text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_partita_origine partita%ROWTYPE;
    v_nuova_partita_id INTEGER;
    v_variazione_id INTEGER;
    v_possessore_id INTEGER;
    v_possessore RECORD;
    v_immobile_id INTEGER;
    v_possessore_ids INTEGER[] := '{}';
BEGIN
    -- Recupera informazioni sulla partita di origine
    SELECT * INTO v_partita_origine FROM partita WHERE id = p_partita_origine_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita di origine con ID % non trovata', p_partita_origine_id;
    END IF;
    
    IF v_partita_origine.stato = 'inattiva' THEN
        RAISE EXCEPTION 'La partita di origine Ã¨ giÃ  inattiva';
    END IF;
    
    -- Verifica che la nuova partita non esista giÃ 
    IF EXISTS (SELECT 1 FROM partita WHERE comune_nome = p_comune_nome AND numero_partita = p_numero_partita) THEN
        RAISE EXCEPTION 'La partita % giÃ  esiste nel comune %', p_numero_partita, p_comune_nome;
    END IF;
    
    -- Crea i nuovi possessori se necessario
    IF p_nuovi_possessori IS NOT NULL THEN
        FOR v_possessore IN SELECT * FROM json_to_recordset(p_nuovi_possessori) 
            AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT)
        LOOP
            -- Verifica se il possessore esiste giÃ 
            SELECT id INTO v_possessore_id 
            FROM possessore 
            WHERE comune_nome = p_comune_nome AND nome_completo = v_possessore.nome_completo;
            
            IF NOT FOUND THEN
                -- Crea un nuovo possessore
                INSERT INTO possessore(comune_nome, cognome_nome, paternita, nome_completo, attivo)
                VALUES (p_comune_nome, v_possessore.cognome_nome, v_possessore.paternita, v_possessore.nome_completo, TRUE)
                RETURNING id INTO v_possessore_id;
            END IF;
            
            -- Aggiungi all'array dei possessori
            v_possessore_ids := array_append(v_possessore_ids, v_possessore_id);
        END LOOP;
    END IF;
    
    -- Se non sono specificati nuovi possessori, usa gli stessi della partita di origine
    IF array_length(v_possessore_ids, 1) IS NULL THEN
        SELECT array_agg(possessore_id) INTO v_possessore_ids
        FROM partita_possessore
        WHERE partita_id = p_partita_origine_id;
    END IF;
    
    -- Crea la nuova partita
    INSERT INTO partita(comune_nome, numero_partita, tipo, data_impianto, numero_provenienza, stato)
    VALUES (p_comune_nome, p_numero_partita, 'principale', p_data_variazione, v_partita_origine.numero_partita, 'attiva')
    RETURNING id INTO v_nuova_partita_id;
    
    -- Collega i possessori alla nuova partita
    FOREACH v_possessore_id IN ARRAY v_possessore_ids
    LOOP
        INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
        SELECT 
            v_nuova_partita_id,
            v_possessore_id,
            'principale',
            titolo,
            quota
        FROM partita_possessore
        WHERE partita_id = p_partita_origine_id AND possessore_id = v_possessore_id
        LIMIT 1;
        
        -- Se non c'Ã¨ una quota esistente, imposta come proprietÃ  esclusiva
        IF NOT FOUND THEN
            INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo)
            VALUES (v_nuova_partita_id, v_possessore_id, 'principale', 'proprietÃ  esclusiva');
        END IF;
    END LOOP;
    
    -- Registra la variazione
    INSERT INTO variazione(
        partita_origine_id, partita_destinazione_id, tipo, 
        data_variazione, numero_riferimento, nominativo_riferimento
    )
    VALUES (
        p_partita_origine_id, v_nuova_partita_id, p_tipo_variazione,
        p_data_variazione, p_numero_partita::TEXT, 
        (SELECT string_agg(nome_completo, ', ') FROM possessore WHERE id = ANY(v_possessore_ids))
    )
    RETURNING id INTO v_variazione_id;
    
    -- Registra il contratto
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note);
    
    -- Trasferisci gli immobili
    IF p_immobili_da_trasferire IS NULL THEN
        -- Trasferisci tutti gli immobili
        UPDATE immobile SET partita_id = v_nuova_partita_id
        WHERE partita_id = p_partita_origine_id;
    ELSE
        -- Trasferisci solo gli immobili specificati
        FOREACH v_immobile_id IN ARRAY p_immobili_da_trasferire
        LOOP
            UPDATE immobile SET partita_id = v_nuova_partita_id
            WHERE id = v_immobile_id AND partita_id = p_partita_origine_id;
            
            IF NOT FOUND THEN
                RAISE WARNING 'Immobile con ID % non trovato nella partita di origine', v_immobile_id;
            END IF;
        END LOOP;
    END IF;
    
    -- Chiudi la partita di origine
    UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione
    WHERE id = p_partita_origine_id;
    
    RAISE NOTICE 'Passaggio di proprietÃ  registrato con successo. Nuova partita ID: %', v_nuova_partita_id;
END;
$$;


ALTER PROCEDURE catasto.registra_passaggio_proprieta(IN p_partita_origine_id integer, IN p_comune_nome character varying, IN p_numero_partita integer, IN p_tipo_variazione character varying, IN p_data_variazione date, IN p_tipo_contratto character varying, IN p_data_contratto date, IN p_notaio character varying, IN p_repertorio character varying, IN p_nuovi_possessori json, IN p_immobili_da_trasferire integer[], IN p_note text) OWNER TO postgres;

--
-- Name: registra_variazione(integer, integer, character varying, date, character varying, character varying, character varying, date, character varying, character varying, text); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.registra_variazione(IN p_partita_origine_id integer, IN p_partita_destinazione_id integer, IN p_tipo character varying, IN p_data_variazione date, IN p_numero_riferimento character varying, IN p_nominativo_riferimento character varying, IN p_tipo_contratto character varying, IN p_data_contratto date, IN p_notaio character varying, IN p_repertorio character varying, IN p_note text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_variazione_id INTEGER;
BEGIN
    -- Verifica che la partita origine sia attiva
    IF NOT is_partita_attiva(p_partita_origine_id) THEN
        RAISE EXCEPTION 'La partita di origine non Ã¨ attiva';
    END IF;
    
    -- Inserisci la variazione
    INSERT INTO variazione(partita_origine_id, partita_destinazione_id, tipo, data_variazione, 
                          numero_riferimento, nominativo_riferimento)
    VALUES (p_partita_origine_id, p_partita_destinazione_id, p_tipo, p_data_variazione, 
           p_numero_riferimento, p_nominativo_riferimento)
    RETURNING id INTO v_variazione_id;
    
    -- Inserisci il contratto associato
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note);
    
    -- Se Ã¨ una variazione che inattiva la partita di origine
    IF p_tipo IN ('Vendita', 'Successione', 'Frazionamento') THEN
        UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione
        WHERE id = p_partita_origine_id;
    END IF;
END;
$$;


ALTER PROCEDURE catasto.registra_variazione(IN p_partita_origine_id integer, IN p_partita_destinazione_id integer, IN p_tipo character varying, IN p_data_variazione date, IN p_numero_riferimento character varying, IN p_nominativo_riferimento character varying, IN p_tipo_contratto character varying, IN p_data_contratto date, IN p_notaio character varying, IN p_repertorio character varying, IN p_note text) OWNER TO postgres;

--
-- Name: report_annuale_partite(character varying, integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.report_annuale_partite(p_comune character varying, p_anno integer) RETURNS TABLE(numero_partita integer, tipo character varying, data_impianto date, stato character varying, possessori text, num_immobili bigint, variazioni_anno bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.numero_partita,
        p.tipo,
        p.data_impianto,
        p.stato,
        string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
        COUNT(DISTINCT i.id) AS num_immobili,
        (SELECT COUNT(*) FROM variazione v
         WHERE (v.partita_origine_id = p.id OR v.partita_destinazione_id = p.id)
         AND EXTRACT(YEAR FROM v.data_variazione) = p_anno) AS variazioni_anno
    FROM partita p
    LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
    LEFT JOIN possessore pos ON pp.possessore_id = pos.id
    LEFT JOIN immobile i ON p.id = i.partita_id
    WHERE p.comune_nome = p_comune 
    AND (EXTRACT(YEAR FROM p.data_impianto) <= p_anno)
    AND (p.data_chiusura IS NULL OR EXTRACT(YEAR FROM p.data_chiusura) >= p_anno)
    GROUP BY p.id, p.numero_partita, p.tipo, p.data_impianto, p.stato
    ORDER BY p.numero_partita;
END;
$$;


ALTER FUNCTION catasto.report_annuale_partite(p_comune character varying, p_anno integer) OWNER TO postgres;

--
-- Name: report_proprieta_possessore(integer, date, date); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.report_proprieta_possessore(p_possessore_id integer, p_data_inizio date, p_data_fine date) RETURNS TABLE(partita_id integer, comune_nome character varying, numero_partita integer, titolo character varying, quota character varying, data_inizio date, data_fine date, immobili_posseduti text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS partita_id,
        p.comune_nome,
        p.numero_partita,
        pp.titolo,
        pp.quota,
        GREATEST(p.data_impianto, p_data_inizio) AS data_inizio,
        LEAST(COALESCE(p.data_chiusura, p_data_fine), p_data_fine) AS data_fine,
        string_agg(i.natura || ' in ' || l.nome, ', ') AS immobili_posseduti
    FROM partita p
    JOIN partita_possessore pp ON p.id = pp.partita_id
    LEFT JOIN immobile i ON p.id = i.partita_id
    LEFT JOIN localita l ON i.localita_id = l.id
    WHERE pp.possessore_id = p_possessore_id
    AND p.data_impianto <= p_data_fine
    AND (p.data_chiusura IS NULL OR p.data_chiusura >= p_data_inizio)
    GROUP BY p.id, p.comune_nome, p.numero_partita, pp.titolo, pp.quota
    ORDER BY p.comune_nome, p.numero_partita;
END;
$$;


ALTER FUNCTION catasto.report_proprieta_possessore(p_possessore_id integer, p_data_inizio date, p_data_fine date) OWNER TO postgres;

--
-- Name: ricerca_avanzata_immobili(character varying, character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.ricerca_avanzata_immobili(p_comune character varying DEFAULT NULL::character varying, p_natura character varying DEFAULT NULL::character varying, p_localita character varying DEFAULT NULL::character varying, p_classificazione character varying DEFAULT NULL::character varying, p_possessore character varying DEFAULT NULL::character varying) RETURNS TABLE(immobile_id integer, natura character varying, localita_nome character varying, comune character varying, classificazione character varying, possessori text, partita_numero integer)
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION catasto.ricerca_avanzata_immobili(p_comune character varying, p_natura character varying, p_localita character varying, p_classificazione character varying, p_possessore character varying) OWNER TO postgres;

--
-- Name: ricerca_avanzata_possessori(text); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.ricerca_avanzata_possessori(p_query text) RETURNS TABLE(id integer, nome_completo character varying, comune_nome character varying, similarity double precision, num_partite bigint)
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION catasto.ricerca_avanzata_possessori(p_query text) OWNER TO postgres;

--
-- Name: ricerca_documenti_storici(character varying, character varying, integer, integer, integer, integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.ricerca_documenti_storici(p_titolo character varying DEFAULT NULL::character varying, p_tipo character varying DEFAULT NULL::character varying, p_periodo_id integer DEFAULT NULL::integer, p_anno_inizio integer DEFAULT NULL::integer, p_anno_fine integer DEFAULT NULL::integer, p_partita_id integer DEFAULT NULL::integer) RETURNS TABLE(documento_id integer, titolo character varying, descrizione text, anno integer, periodo_nome character varying, tipo_documento character varying, partite_correlate text)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id AS documento_id,
        d.titolo,
        d.descrizione,
        d.anno,
        ps.nome AS periodo_nome,
        d.tipo_documento,
        string_agg(DISTINCT p.comune_nome || ' - ' || p.numero_partita, ', ') AS partite_correlate
    FROM documento_storico d
    JOIN periodo_storico ps ON d.periodo_id = ps.id
    LEFT JOIN documento_partita dp ON d.id = dp.documento_id
    LEFT JOIN partita p ON dp.partita_id = p.id
    WHERE 
        (p_titolo IS NULL OR d.titolo ILIKE '%' || p_titolo || '%') AND
        (p_tipo IS NULL OR d.tipo_documento = p_tipo) AND
        (p_periodo_id IS NULL OR d.periodo_id = p_periodo_id) AND
        (p_anno_inizio IS NULL OR d.anno >= p_anno_inizio) AND
        (p_anno_fine IS NULL OR d.anno <= p_anno_fine) AND
        (p_partita_id IS NULL OR dp.partita_id = p_partita_id)
    GROUP BY d.id, d.titolo, d.descrizione, d.anno, ps.nome, d.tipo_documento
    ORDER BY d.anno DESC, d.titolo;
END;
$$;


ALTER FUNCTION catasto.ricerca_documenti_storici(p_titolo character varying, p_tipo character varying, p_periodo_id integer, p_anno_inizio integer, p_anno_fine integer, p_partita_id integer) OWNER TO postgres;

--
-- Name: ripara_problemi_database(boolean); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.ripara_problemi_database(IN p_correzione_automatica boolean DEFAULT false)
    LANGUAGE plpgsql
    AS $_$
DECLARE
    v_problemi_trovati BOOLEAN;
    v_partita_record RECORD;
    v_variazione_record RECORD;
    v_nuova_partita_id INTEGER;
    v_count INTEGER;
    v_sql TEXT;
BEGIN
    -- Prima esegue la verifica di integritÃ 
    CALL verifica_integrita_database(v_problemi_trovati);
    
    IF NOT v_problemi_trovati THEN
        RAISE NOTICE 'Nessun problema critico da correggere.';
        RETURN;
    END IF;
    
    IF NOT p_correzione_automatica THEN
        RAISE NOTICE 'Per eseguire le correzioni automatiche, impostare p_correzione_automatica=TRUE.';
        RETURN;
    END IF;
    
    RAISE NOTICE 'Avvio correzione automatica...';
    
    -- 1. Correggi partite inattive con immobili
    FOR v_partita_record IN 
        SELECT p.id, p.numero_partita, p.comune_nome
        FROM partita p
        WHERE p.stato = 'inattiva' AND EXISTS (
            SELECT 1 FROM immobile i WHERE i.partita_id = p.id
        )
    LOOP
        -- Crea una nuova partita temporanea per gli immobili orfani
        v_sql := 'INSERT INTO partita(comune_nome, numero_partita, tipo, data_impianto, numero_provenienza, stato) ' ||
                 'VALUES ($1, $2, ''principale'', CURRENT_DATE, $3, ''attiva'') RETURNING id';
        
        EXECUTE v_sql INTO v_nuova_partita_id 
        USING v_partita_record.comune_nome, 
              (SELECT MAX(numero_partita) + 1 FROM partita WHERE comune_nome = v_partita_record.comune_nome),
              v_partita_record.numero_partita;
        
        -- Sposta gli immobili nella nuova partita
        UPDATE immobile SET partita_id = v_nuova_partita_id WHERE partita_id = v_partita_record.id;
        
        RAISE NOTICE 'Corretti immobili della partita % (comune %), spostati nella nuova partita %',
                    v_partita_record.numero_partita, v_partita_record.comune_nome, v_nuova_partita_id;
    END LOOP;
    
    -- 2. Correggi partite inattive senza data di chiusura
    UPDATE partita 
    SET data_chiusura = CURRENT_DATE
    WHERE stato = 'inattiva' AND data_chiusura IS NULL;
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    IF v_count > 0 THEN
        RAISE NOTICE 'Corrette % partite inattive senza data di chiusura', v_count;
    END IF;
    
    -- 3. Rimuovi variazioni con partite destinazione non esistenti
    FOR v_variazione_record IN 
        SELECT v.id, v.partita_origine_id, v.partita_destinazione_id
        FROM variazione v
        WHERE v.partita_destinazione_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM partita p WHERE p.id = v.partita_destinazione_id
        )
    LOOP
        -- Elimina il contratto associato
        DELETE FROM contratto WHERE variazione_id = v_variazione_record.id;
        
        -- Ripristina la partita di origine se necessario
        UPDATE partita
        SET stato = 'attiva', data_chiusura = NULL
        WHERE id = v_variazione_record.partita_origine_id AND stato = 'inattiva';
        
        -- Elimina la variazione
        DELETE FROM variazione WHERE id = v_variazione_record.id;
        
        RAISE NOTICE 'Rimossa variazione invalida con ID %', v_variazione_record.id;
    END LOOP;
    
    -- Esegui di nuovo la verifica per controllare i progressi
    CALL verifica_integrita_database(v_problemi_trovati);
    
    IF NOT v_problemi_trovati THEN
        RAISE NOTICE 'Correzione automatica completata con successo.';
    ELSE
        RAISE WARNING 'Correzione automatica completata, ma alcuni problemi richiedono intervento manuale.';
    END IF;
END;
$_$;


ALTER PROCEDURE catasto.ripara_problemi_database(IN p_correzione_automatica boolean) OWNER TO postgres;

--
-- Name: sincronizza_con_archivio_stato(integer, character varying, date); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.sincronizza_con_archivio_stato(IN p_partita_id integer, IN p_riferimento_archivio character varying, IN p_data_sincronizzazione date DEFAULT CURRENT_DATE)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_partita_json JSON;
    v_log_message TEXT;
BEGIN
    -- Recupera i dati della partita
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita con ID % non trovata', p_partita_id;
    END IF;
    
    -- Genera il JSON con tutti i dati della partita
    --SELECT esporta_partita_json(p_partita_id) INTO v_partita_json;

    -- Genera un JSON semplice con dati base della partita
    SELECT json_build_object(
        'id', v_partita.id,
        'comune_nome', v_partita.comune_nome,
        'numero_partita', v_partita.numero_partita
    ) INTO v_partita_json;
        
    -- In una implementazione reale, qui ci sarebbe una chiamata API
    -- all'Archivio di Stato per inviare i dati. 
    -- Simuliamo il processo:
    v_log_message := 'SIMULAZIONE: ';
    v_log_message := v_log_message || 'Inviati dati della partita ' || v_partita.numero_partita;
    v_log_message := v_log_message || ' del comune ' || v_partita.comune_nome;
    v_log_message := v_log_message || ' all''Archivio di Stato con riferimento ' || p_riferimento_archivio;
    v_log_message := v_log_message || ' in data ' || p_data_sincronizzazione;
    
    -- Registriamo la sincronizzazione
    -- In un'implementazione reale si avrebbe una tabella apposita per tracciare le sincronizzazioni
    RAISE NOTICE '%', v_log_message;
    
    -- Esempio di come si potrebbe implementare con un campo aggiuntivo:
    -- UPDATE partita 
    -- SET ultima_sincronizzazione_archivio = p_data_sincronizzazione,
    --     riferimento_archivio = p_riferimento_archivio
    -- WHERE id = p_partita_id;
    
    RAISE NOTICE 'Sincronizzazione con l''Archivio di Stato completata simulando l''invio di % byte di dati.', 
                 LENGTH(v_partita_json::TEXT);
END;
$$;


ALTER PROCEDURE catasto.sincronizza_con_archivio_stato(IN p_partita_id integer, IN p_riferimento_archivio character varying, IN p_data_sincronizzazione date) OWNER TO postgres;

--
-- Name: statistiche_catastali_periodo(character varying, integer, integer); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.statistiche_catastali_periodo(p_comune character varying DEFAULT NULL::character varying, p_anno_inizio integer DEFAULT 1900, p_anno_fine integer DEFAULT (EXTRACT(year FROM CURRENT_DATE))::integer) RETURNS TABLE(anno integer, comune_nome character varying, nuove_partite bigint, partite_chiuse bigint, totale_partite_attive bigint, variazioni bigint, immobili_registrati bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    WITH anni AS (
        SELECT generate_series(p_anno_inizio, p_anno_fine) AS anno
    ),
    comuni AS (
        SELECT nome FROM comune
        WHERE p_comune IS NULL OR nome = p_comune
    ),
    anni_comuni AS (
        SELECT a.anno, c.nome AS comune_nome
        FROM anni a
        CROSS JOIN comuni c
    ),
    statistiche AS (
        SELECT 
            EXTRACT(YEAR FROM p.data_impianto)::INTEGER AS anno,
            p.comune_nome,
            COUNT(*) AS nuove_partite,
            0 AS partite_chiuse
        FROM partita p
        WHERE EXTRACT(YEAR FROM p.data_impianto) BETWEEN p_anno_inizio AND p_anno_fine
        AND (p_comune IS NULL OR p.comune_nome = p_comune)
        GROUP BY EXTRACT(YEAR FROM p.data_impianto), p.comune_nome
        
        UNION ALL
        
        SELECT 
            EXTRACT(YEAR FROM p.data_chiusura)::INTEGER AS anno,
            p.comune_nome,
            0 AS nuove_partite,
            COUNT(*) AS partite_chiuse
        FROM partita p
        WHERE p.data_chiusura IS NOT NULL
        AND EXTRACT(YEAR FROM p.data_chiusura) BETWEEN p_anno_inizio AND p_anno_fine
        AND (p_comune IS NULL OR p.comune_nome = p_comune)
        GROUP BY EXTRACT(YEAR FROM p.data_chiusura), p.comune_nome
    ),
    variazioni_anno AS (
        SELECT 
            EXTRACT(YEAR FROM v.data_variazione)::INTEGER AS anno,
            p.comune_nome,
            COUNT(*) AS variazioni
        FROM variazione v
        JOIN partita p ON v.partita_origine_id = p.id
        WHERE EXTRACT(YEAR FROM v.data_variazione) BETWEEN p_anno_inizio AND p_anno_fine
        AND (p_comune IS NULL OR p.comune_nome = p_comune)
        GROUP BY EXTRACT(YEAR FROM v.data_variazione), p.comune_nome
    ),
    immobili_anno AS (
        SELECT 
            EXTRACT(YEAR FROM i.data_creazione)::INTEGER AS anno,
            p.comune_nome,
            COUNT(*) AS immobili_registrati
        FROM immobile i
        JOIN partita p ON i.partita_id = p.id
        WHERE EXTRACT(YEAR FROM i.data_creazione) BETWEEN p_anno_inizio AND p_anno_fine
        AND (p_comune IS NULL OR p.comune_nome = p_comune)
        GROUP BY EXTRACT(YEAR FROM i.data_creazione), p.comune_nome
    ),
    partite_cumulative AS (
        SELECT
            ac.anno,
            ac.comune_nome,
            COALESCE(SUM(s.nuove_partite) FILTER (WHERE s.anno = ac.anno), 0) AS nuove_partite,
            COALESCE(SUM(s.partite_chiuse) FILTER (WHERE s.anno = ac.anno), 0) AS partite_chiuse,
            COALESCE(SUM(v.variazioni), 0) AS variazioni,
            COALESCE(SUM(i.immobili_registrati), 0) AS immobili_registrati,
            SUM(s.nuove_partite) FILTER (WHERE s.anno <= ac.anno) OVER (PARTITION BY ac.comune_nome ORDER BY ac.anno) -
            SUM(s.partite_chiuse) FILTER (WHERE s.anno <= ac.anno) OVER (PARTITION BY ac.comune_nome ORDER BY ac.anno) AS totale_partite_attive
        FROM anni_comuni ac
        LEFT JOIN statistiche s ON ac.anno = s.anno AND ac.comune_nome = s.comune_nome
        LEFT JOIN variazioni_anno v ON ac.anno = v.anno AND ac.comune_nome = v.comune_nome
        LEFT JOIN immobili_anno i ON ac.anno = i.anno AND ac.comune_nome = i.comune_nome
        GROUP BY ac.anno, ac.comune_nome
    )
    SELECT 
        pc.anno,
        pc.comune_nome,
        pc.nuove_partite,
        pc.partite_chiuse,
        CASE WHEN pc.totale_partite_attive < 0 THEN 0 ELSE pc.totale_partite_attive END AS totale_partite_attive,
        pc.variazioni,
        pc.immobili_registrati
    FROM partite_cumulative pc
    ORDER BY pc.anno, pc.comune_nome;
END;
$$;


ALTER FUNCTION catasto.statistiche_catastali_periodo(p_comune character varying, p_anno_inizio integer, p_anno_fine integer) OWNER TO postgres;

--
-- Name: suggerimenti_ottimizzazione(); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.suggerimenti_ottimizzazione() RETURNS text
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION catasto.suggerimenti_ottimizzazione() OWNER TO postgres;

--
-- Name: trasferisci_immobile(integer, integer, boolean); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.trasferisci_immobile(IN p_immobile_id integer, IN p_nuova_partita_id integer, IN p_registra_variazione boolean DEFAULT false)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_vecchia_partita_id INTEGER;
    v_variazione_id INTEGER;
BEGIN
    -- Verifica che l'immobile esista
    SELECT partita_id INTO v_vecchia_partita_id FROM immobile WHERE id = p_immobile_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Immobile con ID % non trovato', p_immobile_id;
    END IF;
    
    -- Verifica che la nuova partita esista ed Ã¨ attiva
    IF NOT is_partita_attiva(p_nuova_partita_id) THEN
        RAISE EXCEPTION 'La nuova partita con ID % non esiste o non Ã¨ attiva', p_nuova_partita_id;
    END IF;
    
    -- Registra una variazione se richiesto
    IF p_registra_variazione THEN
        INSERT INTO variazione(
            partita_origine_id, partita_destinazione_id, tipo, data_variazione,
            numero_riferimento, nominativo_riferimento
        ) VALUES (
            v_vecchia_partita_id, p_nuova_partita_id, 'Trasferimento', CURRENT_DATE,
            'TI-' || p_immobile_id, 'Trasferimento immobile'
        )
        RETURNING id INTO v_variazione_id;
        
        RAISE NOTICE 'Registrata variazione con ID % per il trasferimento dell''immobile', v_variazione_id;
    END IF;
    
    -- Trasferisce l'immobile
    UPDATE immobile SET partita_id = p_nuova_partita_id WHERE id = p_immobile_id;
    
    RAISE NOTICE 'Immobile con ID % trasferito con successo dalla partita % alla partita %',
                p_immobile_id, v_vecchia_partita_id, p_nuova_partita_id;
END;
$$;


ALTER PROCEDURE catasto.trasferisci_immobile(IN p_immobile_id integer, IN p_nuova_partita_id integer, IN p_registra_variazione boolean) OWNER TO postgres;

--
-- Name: update_modified_column(); Type: FUNCTION; Schema: catasto; Owner: postgres
--

CREATE FUNCTION catasto.update_modified_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.data_modifica = now();
    RETURN NEW;
END;
$$;


ALTER FUNCTION catasto.update_modified_column() OWNER TO postgres;

--
-- Name: verifica_integrita_database(); Type: PROCEDURE; Schema: catasto; Owner: postgres
--

CREATE PROCEDURE catasto.verifica_integrita_database(OUT p_problemi_trovati boolean)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_count INTEGER;
    v_problemi TEXT := '';
BEGIN
    p_problemi_trovati := FALSE;
    
    -- 1. Verifica partite senza possessori
    SELECT COUNT(*) INTO v_count FROM partita p
    WHERE NOT EXISTS (
        SELECT 1 FROM partita_possessore pp WHERE pp.partita_id = p.id
    );
    
    IF v_count > 0 THEN
        p_problemi_trovati := TRUE;
        v_problemi := v_problemi || '- Trovate ' || v_count || ' partite senza possessori' || E'\n';
    END IF;
    
    -- 2. Verifica possessori senza partite
    SELECT COUNT(*) INTO v_count FROM possessore pos
    WHERE pos.attivo = TRUE AND NOT EXISTS (
        SELECT 1 FROM partita_possessore pp WHERE pp.possessore_id = pos.id
    );
    
    IF v_count > 0 THEN
        v_problemi := v_problemi || '- Trovati ' || v_count || ' possessori attivi senza partite associate' || E'\n';
        -- Questo Ã¨ un avviso, non un errore di integritÃ 
    END IF;
    
    -- 3. Verifica partite inattive con immobili
    SELECT COUNT(*) INTO v_count FROM partita p
    WHERE p.stato = 'inattiva' AND EXISTS (
        SELECT 1 FROM immobile i WHERE i.partita_id = p.id
    );
    
    IF v_count > 0 THEN
        p_problemi_trovati := TRUE;
        v_problemi := v_problemi || '- Trovate ' || v_count || ' partite inattive con immobili associati' || E'\n';
    END IF;
    
    -- 4. Verifica variazioni con partite destinate non esistenti
    SELECT COUNT(*) INTO v_count FROM variazione v
    WHERE v.partita_destinazione_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM partita p WHERE p.id = v.partita_destinazione_id
    );
    
    IF v_count > 0 THEN
        p_problemi_trovati := TRUE;
        v_problemi := v_problemi || '- Trovate ' || v_count || ' variazioni con partite destinazione non esistenti' || E'\n';
    END IF;
    
    -- 5. Verifica partite chiuse senza data di chiusura
    SELECT COUNT(*) INTO v_count FROM partita p
    WHERE p.stato = 'inattiva' AND p.data_chiusura IS NULL;
    
    IF v_count > 0 THEN
        p_problemi_trovati := TRUE;
        v_problemi := v_problemi || '- Trovate ' || v_count || ' partite inattive senza data di chiusura' || E'\n';
    END IF;
    
    -- 6. Verifica variazioni senza contratti
    SELECT COUNT(*) INTO v_count FROM variazione v
    WHERE NOT EXISTS (
        SELECT 1 FROM contratto c WHERE c.variazione_id = v.id
    );
    
    IF v_count > 0 THEN
        v_problemi := v_problemi || '- Trovate ' || v_count || ' variazioni senza contratti associati' || E'\n';
        -- PuÃ² essere normale in alcuni casi, quindi Ã¨ solo un avviso
    END IF;
    
    -- 7. Verifica immobili senza localitÃ 
    SELECT COUNT(*) INTO v_count FROM immobile i
    WHERE NOT EXISTS (
        SELECT 1 FROM localita l WHERE l.id = i.localita_id
    );
    
    IF v_count > 0 THEN
        p_problemi_trovati := TRUE;
        v_problemi := v_problemi || '- Trovati ' || v_count || ' immobili con localitÃ  non esistente' || E'\n';
    END IF;
    
    -- Stampa risultati
    IF p_problemi_trovati THEN
        RAISE WARNING 'Problemi di integritÃ  rilevati:%', E'\n' || v_problemi;
    ELSE
        IF v_problemi != '' THEN
            RAISE NOTICE 'Nessun problema critico rilevato, ma ci sono alcuni avvisi:%', E'\n' || v_problemi;
        ELSE
            RAISE NOTICE 'Nessun problema di integritÃ  rilevato nel database.';
        END IF;
    END IF;
END;
$$;


ALTER PROCEDURE catasto.verifica_integrita_database(OUT p_problemi_trovati boolean) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: accesso_log; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.accesso_log (
    id integer NOT NULL,
    utente_id integer,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    azione character varying(50) NOT NULL,
    indirizzo_ip character varying(40),
    user_agent text,
    esito boolean
);


ALTER TABLE catasto.accesso_log OWNER TO postgres;

--
-- Name: accesso_log_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.accesso_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.accesso_log_id_seq OWNER TO postgres;

--
-- Name: accesso_log_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.accesso_log_id_seq OWNED BY catasto.accesso_log.id;


--
-- Name: audit_log; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.audit_log (
    id integer NOT NULL,
    tabella character varying(100) NOT NULL,
    operazione character(1) NOT NULL,
    record_id integer NOT NULL,
    dati_prima jsonb,
    dati_dopo jsonb,
    utente character varying(100) NOT NULL,
    ip_address character varying(40),
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT audit_log_operazione_check CHECK ((operazione = ANY (ARRAY['I'::bpchar, 'U'::bpchar, 'D'::bpchar])))
);


ALTER TABLE catasto.audit_log OWNER TO postgres;

--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.audit_log_id_seq OWNER TO postgres;

--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.audit_log_id_seq OWNED BY catasto.audit_log.id;


--
-- Name: backup_registro; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.backup_registro (
    id integer NOT NULL,
    nome_file character varying(255) NOT NULL,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    utente character varying(100) NOT NULL,
    dimensione_bytes bigint,
    tipo character varying(20) NOT NULL,
    esito boolean NOT NULL,
    messaggio text,
    percorso_file text NOT NULL,
    CONSTRAINT backup_registro_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['completo'::character varying, 'schema'::character varying, 'dati'::character varying])::text[])))
);


ALTER TABLE catasto.backup_registro OWNER TO postgres;

--
-- Name: backup_registro_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.backup_registro_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.backup_registro_id_seq OWNER TO postgres;

--
-- Name: backup_registro_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.backup_registro_id_seq OWNED BY catasto.backup_registro.id;


--
-- Name: comune; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.comune (
    nome character varying(100) NOT NULL,
    provincia character varying(100) NOT NULL,
    regione character varying(100) NOT NULL,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    periodo_id integer
);


ALTER TABLE catasto.comune OWNER TO postgres;

--
-- Name: TABLE comune; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.comune IS 'Tabella dei comuni catalogati nel catasto storico';


--
-- Name: consultazione; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.consultazione (
    id integer NOT NULL,
    data date NOT NULL,
    richiedente character varying(255) NOT NULL,
    documento_identita character varying(100),
    motivazione text,
    materiale_consultato text,
    funzionario_autorizzante character varying(255),
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE catasto.consultazione OWNER TO postgres;

--
-- Name: TABLE consultazione; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.consultazione IS 'Registro delle consultazioni dello archivio';


--
-- Name: consultazione_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.consultazione_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.consultazione_id_seq OWNER TO postgres;

--
-- Name: consultazione_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.consultazione_id_seq OWNED BY catasto.consultazione.id;


--
-- Name: contratto; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.contratto (
    id integer NOT NULL,
    variazione_id integer NOT NULL,
    tipo character varying(50) NOT NULL,
    data_contratto date NOT NULL,
    notaio character varying(255),
    repertorio character varying(100),
    note text,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT contratto_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['Vendita'::character varying, 'Divisione'::character varying, 'Successione'::character varying, 'Donazione'::character varying])::text[])))
);


ALTER TABLE catasto.contratto OWNER TO postgres;

--
-- Name: TABLE contratto; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.contratto IS 'Contratti che documentano le variazioni';


--
-- Name: contratto_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.contratto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.contratto_id_seq OWNER TO postgres;

--
-- Name: contratto_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.contratto_id_seq OWNED BY catasto.contratto.id;


--
-- Name: documento_partita; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.documento_partita (
    documento_id integer NOT NULL,
    partita_id integer NOT NULL,
    rilevanza character varying(20) NOT NULL,
    note text,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT documento_partita_rilevanza_check CHECK (((rilevanza)::text = ANY ((ARRAY['primaria'::character varying, 'secondaria'::character varying, 'correlata'::character varying])::text[])))
);


ALTER TABLE catasto.documento_partita OWNER TO postgres;

--
-- Name: documento_storico; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.documento_storico (
    id integer NOT NULL,
    titolo character varying(255) NOT NULL,
    descrizione text,
    anno integer,
    periodo_id integer,
    tipo_documento character varying(100) NOT NULL,
    percorso_file character varying(255),
    metadati jsonb,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE catasto.documento_storico OWNER TO postgres;

--
-- Name: documento_storico_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.documento_storico_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.documento_storico_id_seq OWNER TO postgres;

--
-- Name: documento_storico_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.documento_storico_id_seq OWNED BY catasto.documento_storico.id;


--
-- Name: immobile; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.immobile (
    id integer NOT NULL,
    partita_id integer NOT NULL,
    localita_id integer NOT NULL,
    natura character varying(100) NOT NULL,
    numero_piani integer,
    numero_vani integer,
    consistenza character varying(255),
    classificazione character varying(100),
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE catasto.immobile OWNER TO postgres;

--
-- Name: TABLE immobile; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.immobile IS 'Immobili registrati nel catasto';


--
-- Name: immobile_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.immobile_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.immobile_id_seq OWNER TO postgres;

--
-- Name: immobile_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.immobile_id_seq OWNED BY catasto.immobile.id;


--
-- Name: localita; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.localita (
    id integer NOT NULL,
    comune_nome character varying(100) NOT NULL,
    nome character varying(255) NOT NULL,
    tipo character varying(50) NOT NULL,
    civico integer,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    periodo_id integer,
    CONSTRAINT localita_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['regione'::character varying, 'via'::character varying, 'borgata'::character varying])::text[])))
);


ALTER TABLE catasto.localita OWNER TO postgres;

--
-- Name: TABLE localita; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.localita IS 'LocalitÃ  o indirizzi degli immobili';


--
-- Name: localita_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.localita_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.localita_id_seq OWNER TO postgres;

--
-- Name: localita_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.localita_id_seq OWNED BY catasto.localita.id;


--
-- Name: partita; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.partita (
    id integer NOT NULL,
    comune_nome character varying(100) NOT NULL,
    numero_partita integer NOT NULL,
    tipo character varying(20) NOT NULL,
    data_impianto date,
    data_chiusura date,
    numero_provenienza integer,
    stato character varying(20) DEFAULT 'attiva'::character varying NOT NULL,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT partita_stato_check CHECK (((stato)::text = ANY ((ARRAY['attiva'::character varying, 'inattiva'::character varying])::text[]))),
    CONSTRAINT partita_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['principale'::character varying, 'secondaria'::character varying])::text[])))
);


ALTER TABLE catasto.partita OWNER TO postgres;

--
-- Name: TABLE partita; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.partita IS 'Partite catastali che rappresentano proprietÃ  immobiliari';


--
-- Name: partita_possessore; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.partita_possessore (
    id integer NOT NULL,
    partita_id integer NOT NULL,
    possessore_id integer NOT NULL,
    tipo_partita character varying(20) NOT NULL,
    titolo character varying(50) DEFAULT 'proprietÃ  esclusiva'::character varying NOT NULL,
    quota character varying(20) DEFAULT NULL::character varying,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT partita_possessore_tipo_partita_check CHECK (((tipo_partita)::text = ANY ((ARRAY['principale'::character varying, 'secondaria'::character varying])::text[])))
);


ALTER TABLE catasto.partita_possessore OWNER TO postgres;

--
-- Name: TABLE partita_possessore; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.partita_possessore IS 'Relazione tra partite e possessori';


--
-- Name: possessore; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.possessore (
    id integer NOT NULL,
    comune_nome character varying(100) NOT NULL,
    cognome_nome character varying(255) NOT NULL,
    paternita character varying(255),
    nome_completo character varying(255) NOT NULL,
    attivo boolean DEFAULT true NOT NULL,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE catasto.possessore OWNER TO postgres;

--
-- Name: TABLE possessore; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.possessore IS 'Proprietari o possessori di immobili';


--
-- Name: variazione; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.variazione (
    id integer NOT NULL,
    partita_origine_id integer NOT NULL,
    partita_destinazione_id integer,
    tipo character varying(50) NOT NULL,
    data_variazione date NOT NULL,
    numero_riferimento character varying(50),
    nominativo_riferimento character varying(255),
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT variazione_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['Acquisto'::character varying, 'Successione'::character varying, 'Variazione'::character varying, 'Frazionamento'::character varying, 'Divisione'::character varying])::text[])))
);


ALTER TABLE catasto.variazione OWNER TO postgres;

--
-- Name: TABLE variazione; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.variazione IS 'Variazioni di proprietÃ  o modifiche alle partite';


--
-- Name: mv_cronologia_variazioni; Type: MATERIALIZED VIEW; Schema: catasto; Owner: postgres
--

CREATE MATERIALIZED VIEW catasto.mv_cronologia_variazioni AS
 SELECT v.id AS variazione_id,
    v.tipo AS tipo_variazione,
    v.data_variazione,
    p_orig.numero_partita AS partita_origine_numero,
    p_orig.comune_nome AS comune_origine,
    string_agg(DISTINCT (pos_orig.nome_completo)::text, ', '::text) AS possessori_origine,
    p_dest.numero_partita AS partita_dest_numero,
    p_dest.comune_nome AS comune_dest,
    string_agg(DISTINCT (pos_dest.nome_completo)::text, ', '::text) AS possessori_dest,
    c.tipo AS tipo_contratto,
    c.notaio,
    c.data_contratto
   FROM (((((((catasto.variazione v
     JOIN catasto.partita p_orig ON ((v.partita_origine_id = p_orig.id)))
     LEFT JOIN catasto.partita p_dest ON ((v.partita_destinazione_id = p_dest.id)))
     LEFT JOIN catasto.contratto c ON ((v.id = c.variazione_id)))
     LEFT JOIN catasto.partita_possessore pp_orig ON ((p_orig.id = pp_orig.partita_id)))
     LEFT JOIN catasto.possessore pos_orig ON ((pp_orig.possessore_id = pos_orig.id)))
     LEFT JOIN catasto.partita_possessore pp_dest ON ((p_dest.id = pp_dest.partita_id)))
     LEFT JOIN catasto.possessore pos_dest ON ((pp_dest.possessore_id = pos_dest.id)))
  GROUP BY v.id, v.tipo, v.data_variazione, p_orig.numero_partita, p_orig.comune_nome, p_dest.numero_partita, p_dest.comune_nome, c.tipo, c.notaio, c.data_contratto
  WITH NO DATA;


ALTER MATERIALIZED VIEW catasto.mv_cronologia_variazioni OWNER TO postgres;

--
-- Name: mv_immobili_per_tipologia; Type: MATERIALIZED VIEW; Schema: catasto; Owner: postgres
--

CREATE MATERIALIZED VIEW catasto.mv_immobili_per_tipologia AS
 SELECT p.comune_nome,
    i.classificazione,
    count(*) AS numero_immobili,
    sum(
        CASE
            WHEN (i.numero_piani IS NOT NULL) THEN i.numero_piani
            ELSE 0
        END) AS totale_piani,
    sum(
        CASE
            WHEN (i.numero_vani IS NOT NULL) THEN i.numero_vani
            ELSE 0
        END) AS totale_vani
   FROM (catasto.immobile i
     JOIN catasto.partita p ON ((i.partita_id = p.id)))
  WHERE ((p.stato)::text = 'attiva'::text)
  GROUP BY p.comune_nome, i.classificazione
  WITH NO DATA;


ALTER MATERIALIZED VIEW catasto.mv_immobili_per_tipologia OWNER TO postgres;

--
-- Name: mv_partite_complete; Type: MATERIALIZED VIEW; Schema: catasto; Owner: postgres
--

CREATE MATERIALIZED VIEW catasto.mv_partite_complete AS
 SELECT p.id AS partita_id,
    p.comune_nome,
    p.numero_partita,
    p.tipo,
    p.data_impianto,
    p.stato,
    string_agg(DISTINCT (pos.nome_completo)::text, ', '::text) AS possessori,
    count(DISTINCT i.id) AS num_immobili,
    string_agg(DISTINCT (i.natura)::text, ', '::text) AS tipi_immobili,
    string_agg(DISTINCT (l.nome)::text, ', '::text) AS localita
   FROM ((((catasto.partita p
     LEFT JOIN catasto.partita_possessore pp ON ((p.id = pp.partita_id)))
     LEFT JOIN catasto.possessore pos ON ((pp.possessore_id = pos.id)))
     LEFT JOIN catasto.immobile i ON ((p.id = i.partita_id)))
     LEFT JOIN catasto.localita l ON ((i.localita_id = l.id)))
  GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.data_impianto, p.stato
  WITH NO DATA;


ALTER MATERIALIZED VIEW catasto.mv_partite_complete OWNER TO postgres;

--
-- Name: mv_statistiche_comune; Type: MATERIALIZED VIEW; Schema: catasto; Owner: postgres
--

CREATE MATERIALIZED VIEW catasto.mv_statistiche_comune AS
 SELECT c.nome AS comune,
    c.provincia,
    count(DISTINCT p.id) AS totale_partite,
    count(DISTINCT
        CASE
            WHEN ((p.stato)::text = 'attiva'::text) THEN p.id
            ELSE NULL::integer
        END) AS partite_attive,
    count(DISTINCT
        CASE
            WHEN ((p.stato)::text = 'inattiva'::text) THEN p.id
            ELSE NULL::integer
        END) AS partite_inattive,
    count(DISTINCT pos.id) AS totale_possessori,
    count(DISTINCT i.id) AS totale_immobili
   FROM ((((catasto.comune c
     LEFT JOIN catasto.partita p ON (((c.nome)::text = (p.comune_nome)::text)))
     LEFT JOIN catasto.partita_possessore pp ON ((p.id = pp.partita_id)))
     LEFT JOIN catasto.possessore pos ON ((pp.possessore_id = pos.id)))
     LEFT JOIN catasto.immobile i ON ((p.id = i.partita_id)))
  GROUP BY c.nome, c.provincia
  WITH NO DATA;


ALTER MATERIALIZED VIEW catasto.mv_statistiche_comune OWNER TO postgres;

--
-- Name: nome_storico; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.nome_storico (
    id integer NOT NULL,
    entita_tipo character varying(20) NOT NULL,
    entita_id integer NOT NULL,
    nome character varying(100) NOT NULL,
    periodo_id integer,
    anno_inizio integer NOT NULL,
    anno_fine integer,
    note text,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT nome_storico_entita_tipo_check CHECK (((entita_tipo)::text = ANY ((ARRAY['comune'::character varying, 'localita'::character varying])::text[])))
);


ALTER TABLE catasto.nome_storico OWNER TO postgres;

--
-- Name: nome_storico_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.nome_storico_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.nome_storico_id_seq OWNER TO postgres;

--
-- Name: nome_storico_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.nome_storico_id_seq OWNED BY catasto.nome_storico.id;


--
-- Name: partita_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.partita_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.partita_id_seq OWNER TO postgres;

--
-- Name: partita_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.partita_id_seq OWNED BY catasto.partita.id;


--
-- Name: partita_possessore_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.partita_possessore_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.partita_possessore_id_seq OWNER TO postgres;

--
-- Name: partita_possessore_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.partita_possessore_id_seq OWNED BY catasto.partita_possessore.id;


--
-- Name: partita_relazione; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.partita_relazione (
    id integer NOT NULL,
    partita_principale_id integer NOT NULL,
    partita_secondaria_id integer NOT NULL,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT partita_relazione_check CHECK ((partita_principale_id <> partita_secondaria_id))
);


ALTER TABLE catasto.partita_relazione OWNER TO postgres;

--
-- Name: TABLE partita_relazione; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.partita_relazione IS 'Relazioni tra partite principali e secondarie';


--
-- Name: partita_relazione_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.partita_relazione_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.partita_relazione_id_seq OWNER TO postgres;

--
-- Name: partita_relazione_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.partita_relazione_id_seq OWNED BY catasto.partita_relazione.id;


--
-- Name: periodo_storico; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.periodo_storico (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    anno_inizio integer NOT NULL,
    anno_fine integer,
    descrizione text,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE catasto.periodo_storico OWNER TO postgres;

--
-- Name: periodo_storico_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.periodo_storico_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.periodo_storico_id_seq OWNER TO postgres;

--
-- Name: periodo_storico_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.periodo_storico_id_seq OWNED BY catasto.periodo_storico.id;


--
-- Name: permesso; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.permesso (
    id integer NOT NULL,
    nome character varying(50) NOT NULL,
    descrizione text
);


ALTER TABLE catasto.permesso OWNER TO postgres;

--
-- Name: permesso_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.permesso_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.permesso_id_seq OWNER TO postgres;

--
-- Name: permesso_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.permesso_id_seq OWNED BY catasto.permesso.id;


--
-- Name: possessore_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.possessore_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.possessore_id_seq OWNER TO postgres;

--
-- Name: possessore_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.possessore_id_seq OWNED BY catasto.possessore.id;


--
-- Name: registro_matricole; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.registro_matricole (
    id integer NOT NULL,
    comune_nome character varying(100) NOT NULL,
    anno_impianto integer NOT NULL,
    numero_volumi integer NOT NULL,
    stato_conservazione character varying(100),
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE catasto.registro_matricole OWNER TO postgres;

--
-- Name: TABLE registro_matricole; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.registro_matricole IS 'Registro delle matricole (possessori) per comune';


--
-- Name: registro_matricole_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.registro_matricole_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.registro_matricole_id_seq OWNER TO postgres;

--
-- Name: registro_matricole_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.registro_matricole_id_seq OWNED BY catasto.registro_matricole.id;


--
-- Name: registro_partite; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.registro_partite (
    id integer NOT NULL,
    comune_nome character varying(100) NOT NULL,
    anno_impianto integer NOT NULL,
    numero_volumi integer NOT NULL,
    stato_conservazione character varying(100),
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE catasto.registro_partite OWNER TO postgres;

--
-- Name: TABLE registro_partite; Type: COMMENT; Schema: catasto; Owner: postgres
--

COMMENT ON TABLE catasto.registro_partite IS 'Registro delle partite catastali per comune';


--
-- Name: registro_partite_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.registro_partite_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.registro_partite_id_seq OWNER TO postgres;

--
-- Name: registro_partite_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.registro_partite_id_seq OWNED BY catasto.registro_partite.id;


--
-- Name: utente; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.utente (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    nome_completo character varying(100) NOT NULL,
    email character varying(100) NOT NULL,
    ruolo character varying(20) NOT NULL,
    attivo boolean DEFAULT true,
    ultimo_accesso timestamp without time zone,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_modifica timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT utente_ruolo_check CHECK (((ruolo)::text = ANY ((ARRAY['admin'::character varying, 'archivista'::character varying, 'consultatore'::character varying])::text[])))
);


ALTER TABLE catasto.utente OWNER TO postgres;

--
-- Name: utente_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.utente_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.utente_id_seq OWNER TO postgres;

--
-- Name: utente_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.utente_id_seq OWNED BY catasto.utente.id;


--
-- Name: utente_permesso; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.utente_permesso (
    utente_id integer NOT NULL,
    permesso_id integer NOT NULL,
    data_assegnazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE catasto.utente_permesso OWNER TO postgres;

--
-- Name: v_count; Type: TABLE; Schema: catasto; Owner: postgres
--

CREATE TABLE catasto.v_count (
    count bigint
);


ALTER TABLE catasto.v_count OWNER TO postgres;

--
-- Name: v_partite_complete; Type: VIEW; Schema: catasto; Owner: postgres
--

CREATE VIEW catasto.v_partite_complete AS
 SELECT p.id AS partita_id,
    p.comune_nome,
    p.numero_partita,
    p.tipo,
    p.data_impianto,
    p.data_chiusura,
    p.stato,
    pos.id AS possessore_id,
    pos.cognome_nome,
    pos.paternita,
    pos.nome_completo,
    pp.titolo,
    pp.quota,
    count(i.id) AS num_immobili
   FROM (((catasto.partita p
     LEFT JOIN catasto.partita_possessore pp ON ((p.id = pp.partita_id)))
     LEFT JOIN catasto.possessore pos ON ((pp.possessore_id = pos.id)))
     LEFT JOIN catasto.immobile i ON ((p.id = i.partita_id)))
  GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.data_impianto, p.data_chiusura, p.stato, pos.id, pos.cognome_nome, pos.paternita, pos.nome_completo, pp.titolo, pp.quota;


ALTER VIEW catasto.v_partite_complete OWNER TO postgres;

--
-- Name: v_variazioni_complete; Type: VIEW; Schema: catasto; Owner: postgres
--

CREATE VIEW catasto.v_variazioni_complete AS
 SELECT v.id AS variazione_id,
    v.tipo AS tipo_variazione,
    v.data_variazione,
    p_orig.numero_partita AS partita_origine_numero,
    p_orig.comune_nome AS partita_origine_comune,
    p_dest.numero_partita AS partita_dest_numero,
    p_dest.comune_nome AS partita_dest_comune,
    c.tipo AS tipo_contratto,
    c.data_contratto,
    c.notaio,
    c.repertorio
   FROM (((catasto.variazione v
     JOIN catasto.partita p_orig ON ((v.partita_origine_id = p_orig.id)))
     LEFT JOIN catasto.partita p_dest ON ((v.partita_destinazione_id = p_dest.id)))
     LEFT JOIN catasto.contratto c ON ((v.id = c.variazione_id)));


ALTER VIEW catasto.v_variazioni_complete OWNER TO postgres;

--
-- Name: variazione_id_seq; Type: SEQUENCE; Schema: catasto; Owner: postgres
--

CREATE SEQUENCE catasto.variazione_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE catasto.variazione_id_seq OWNER TO postgres;

--
-- Name: variazione_id_seq; Type: SEQUENCE OWNED BY; Schema: catasto; Owner: postgres
--

ALTER SEQUENCE catasto.variazione_id_seq OWNED BY catasto.variazione.id;


--
-- Name: accesso_log id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.accesso_log ALTER COLUMN id SET DEFAULT nextval('catasto.accesso_log_id_seq'::regclass);


--
-- Name: audit_log id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.audit_log ALTER COLUMN id SET DEFAULT nextval('catasto.audit_log_id_seq'::regclass);


--
-- Name: backup_registro id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.backup_registro ALTER COLUMN id SET DEFAULT nextval('catasto.backup_registro_id_seq'::regclass);


--
-- Name: consultazione id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.consultazione ALTER COLUMN id SET DEFAULT nextval('catasto.consultazione_id_seq'::regclass);


--
-- Name: contratto id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.contratto ALTER COLUMN id SET DEFAULT nextval('catasto.contratto_id_seq'::regclass);


--
-- Name: documento_storico id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.documento_storico ALTER COLUMN id SET DEFAULT nextval('catasto.documento_storico_id_seq'::regclass);


--
-- Name: immobile id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.immobile ALTER COLUMN id SET DEFAULT nextval('catasto.immobile_id_seq'::regclass);


--
-- Name: localita id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.localita ALTER COLUMN id SET DEFAULT nextval('catasto.localita_id_seq'::regclass);


--
-- Name: nome_storico id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.nome_storico ALTER COLUMN id SET DEFAULT nextval('catasto.nome_storico_id_seq'::regclass);


--
-- Name: partita id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita ALTER COLUMN id SET DEFAULT nextval('catasto.partita_id_seq'::regclass);


--
-- Name: partita_possessore id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita_possessore ALTER COLUMN id SET DEFAULT nextval('catasto.partita_possessore_id_seq'::regclass);


--
-- Name: partita_relazione id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita_relazione ALTER COLUMN id SET DEFAULT nextval('catasto.partita_relazione_id_seq'::regclass);


--
-- Name: periodo_storico id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.periodo_storico ALTER COLUMN id SET DEFAULT nextval('catasto.periodo_storico_id_seq'::regclass);


--
-- Name: permesso id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.permesso ALTER COLUMN id SET DEFAULT nextval('catasto.permesso_id_seq'::regclass);


--
-- Name: possessore id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.possessore ALTER COLUMN id SET DEFAULT nextval('catasto.possessore_id_seq'::regclass);


--
-- Name: registro_matricole id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.registro_matricole ALTER COLUMN id SET DEFAULT nextval('catasto.registro_matricole_id_seq'::regclass);


--
-- Name: registro_partite id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.registro_partite ALTER COLUMN id SET DEFAULT nextval('catasto.registro_partite_id_seq'::regclass);


--
-- Name: utente id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.utente ALTER COLUMN id SET DEFAULT nextval('catasto.utente_id_seq'::regclass);


--
-- Name: variazione id; Type: DEFAULT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.variazione ALTER COLUMN id SET DEFAULT nextval('catasto.variazione_id_seq'::regclass);


--
-- Data for Name: accesso_log; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.accesso_log (id, utente_id, "timestamp", azione, indirizzo_ip, user_agent, esito) FROM stdin;
1	5	2025-04-24 10:32:57.042028	login	\N	\N	t
\.


--
-- Data for Name: audit_log; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.audit_log (id, tabella, operazione, record_id, dati_prima, dati_dopo, utente, ip_address, "timestamp") FROM stdin;
1	possessore	I	2	\N	{"id": 2, "attivo": true, "paternita": "fu Roberto", "comune_nome": "Carcare", "cognome_nome": "Fossati Angelo", "data_modifica": "2025-04-24T09:01:43.937988", "nome_completo": "Fossati Angelo fu Roberto", "data_creazione": "2025-04-24T09:01:43.937988"}	postgres	\N	2025-04-24 09:01:43.937988
2	possessore	I	3	\N	{"id": 3, "attivo": true, "paternita": "fu Giuseppe", "comune_nome": "Carcare", "cognome_nome": "Caviglia Maria", "data_modifica": "2025-04-24T09:01:43.937988", "nome_completo": "Caviglia Maria fu Giuseppe", "data_creazione": "2025-04-24T09:01:43.937988"}	postgres	\N	2025-04-24 09:01:43.937988
3	possessore	I	4	\N	{"id": 4, "attivo": true, "paternita": "fu Paolo", "comune_nome": "Carcare", "cognome_nome": "Barberis Giovanni", "data_modifica": "2025-04-24T09:01:43.937988", "nome_completo": "Barberis Giovanni fu Paolo", "data_creazione": "2025-04-24T09:01:43.937988"}	postgres	\N	2025-04-24 09:01:43.937988
4	possessore	I	5	\N	{"id": 5, "attivo": true, "paternita": "fu Luigi", "comune_nome": "Cairo Montenotte", "cognome_nome": "Berruti Antonio", "data_modifica": "2025-04-24T09:01:43.937988", "nome_completo": "Berruti Antonio fu Luigi", "data_creazione": "2025-04-24T09:01:43.937988"}	postgres	\N	2025-04-24 09:01:43.937988
5	possessore	I	6	\N	{"id": 6, "attivo": true, "paternita": "fu Marco", "comune_nome": "Cairo Montenotte", "cognome_nome": "Ferraro Caterina", "data_modifica": "2025-04-24T09:01:43.937988", "nome_completo": "Ferraro Caterina fu Marco", "data_creazione": "2025-04-24T09:01:43.937988"}	postgres	\N	2025-04-24 09:01:43.937988
6	possessore	I	7	\N	{"id": 7, "attivo": true, "paternita": "fu Carlo", "comune_nome": "Altare", "cognome_nome": "Bormioli Pietro", "data_modifica": "2025-04-24T09:01:43.937988", "nome_completo": "Bormioli Pietro fu Carlo", "data_creazione": "2025-04-24T09:01:43.937988"}	postgres	\N	2025-04-24 09:01:43.937988
7	partita	I	2	\N	{"id": 2, "tipo": "principale", "stato": "attiva", "comune_nome": "Carcare", "data_chiusura": null, "data_impianto": "1950-05-10", "data_modifica": "2025-04-24T09:01:43.955924", "data_creazione": "2025-04-24T09:01:43.955924", "numero_partita": 221, "numero_provenienza": null}	postgres	\N	2025-04-24 09:01:43.955924
8	partita	I	3	\N	{"id": 3, "tipo": "principale", "stato": "attiva", "comune_nome": "Carcare", "data_chiusura": null, "data_impianto": "1950-05-10", "data_modifica": "2025-04-24T09:01:43.955924", "data_creazione": "2025-04-24T09:01:43.955924", "numero_partita": 219, "numero_provenienza": null}	postgres	\N	2025-04-24 09:01:43.955924
9	partita	I	4	\N	{"id": 4, "tipo": "secondaria", "stato": "attiva", "comune_nome": "Carcare", "data_chiusura": null, "data_impianto": "1951-03-22", "data_modifica": "2025-04-24T09:01:43.955924", "data_creazione": "2025-04-24T09:01:43.955924", "numero_partita": 245, "numero_provenienza": null}	postgres	\N	2025-04-24 09:01:43.955924
10	partita	I	5	\N	{"id": 5, "tipo": "principale", "stato": "attiva", "comune_nome": "Cairo Montenotte", "data_chiusura": null, "data_impianto": "1948-11-05", "data_modifica": "2025-04-24T09:01:43.955924", "data_creazione": "2025-04-24T09:01:43.955924", "numero_partita": 112, "numero_provenienza": null}	postgres	\N	2025-04-24 09:01:43.955924
11	partita	I	6	\N	{"id": 6, "tipo": "principale", "stato": "inattiva", "comune_nome": "Cairo Montenotte", "data_chiusura": null, "data_impianto": "1949-01-15", "data_modifica": "2025-04-24T09:01:43.955924", "data_creazione": "2025-04-24T09:01:43.955924", "numero_partita": 118, "numero_provenienza": null}	postgres	\N	2025-04-24 09:01:43.955924
12	partita	I	7	\N	{"id": 7, "tipo": "principale", "stato": "attiva", "comune_nome": "Altare", "data_chiusura": null, "data_impianto": "1952-07-03", "data_modifica": "2025-04-24T09:01:43.955924", "data_creazione": "2025-04-24T09:01:43.955924", "numero_partita": 87, "numero_provenienza": null}	postgres	\N	2025-04-24 09:01:43.955924
13	immobile	I	1	\N	{"id": 1, "natura": "Molino da cereali", "partita_id": 1, "consistenza": "150 mq", "localita_id": 1, "numero_vani": null, "numero_piani": 2, "data_modifica": "2025-04-24T09:01:43.970222", "data_creazione": "2025-04-24T09:01:43.970222", "classificazione": "Artigianale"}	postgres	\N	2025-04-24 09:01:43.970222
14	immobile	I	2	\N	{"id": 2, "natura": "Casa", "partita_id": 2, "consistenza": "210 mq", "localita_id": 2, "numero_vani": 8, "numero_piani": 3, "data_modifica": "2025-04-24T09:01:43.970222", "data_creazione": "2025-04-24T09:01:43.970222", "classificazione": "Abitazione civile"}	postgres	\N	2025-04-24 09:01:43.970222
15	immobile	I	3	\N	{"id": 3, "natura": "Magazzino", "partita_id": 3, "consistenza": "80 mq", "localita_id": 3, "numero_vani": null, "numero_piani": 1, "data_modifica": "2025-04-24T09:01:43.970222", "data_creazione": "2025-04-24T09:01:43.970222", "classificazione": "Deposito"}	postgres	\N	2025-04-24 09:01:43.970222
16	immobile	I	4	\N	{"id": 4, "natura": "Fabbricato rurale", "partita_id": 4, "consistenza": "180 mq", "localita_id": 4, "numero_vani": 5, "numero_piani": 2, "data_modifica": "2025-04-24T09:01:43.970222", "data_creazione": "2025-04-24T09:01:43.970222", "classificazione": "Abitazione rurale"}	postgres	\N	2025-04-24 09:01:43.970222
17	immobile	I	5	\N	{"id": 5, "natura": "Casa", "partita_id": 5, "consistenza": "160 mq", "localita_id": 5, "numero_vani": 6, "numero_piani": 2, "data_modifica": "2025-04-24T09:01:43.970222", "data_creazione": "2025-04-24T09:01:43.970222", "classificazione": "Abitazione civile"}	postgres	\N	2025-04-24 09:01:43.970222
18	immobile	I	6	\N	{"id": 6, "natura": "Laboratorio", "partita_id": 6, "consistenza": "120 mq", "localita_id": 6, "numero_vani": null, "numero_piani": 1, "data_modifica": "2025-04-24T09:01:43.970222", "data_creazione": "2025-04-24T09:01:43.970222", "classificazione": "Artigianale"}	postgres	\N	2025-04-24 09:01:43.970222
19	variazione	I	1	\N	{"id": 1, "tipo": "Successione", "data_modifica": "2025-04-24T09:01:43.975491", "data_creazione": "2025-04-24T09:01:43.975491", "data_variazione": "1952-08-15", "numero_riferimento": "22/52", "partita_origine_id": 5, "nominativo_riferimento": "Ferraro Caterina", "partita_destinazione_id": null}	postgres	\N	2025-04-24 09:01:43.975491
20	possessore	I	8	\N	{"id": 8, "attivo": true, "paternita": "fu Roberto", "comune_nome": "Carcare", "cognome_nome": "Fossati Angelo", "data_modifica": "2025-04-24T09:10:19.919699", "nome_completo": "Fossati Angelo fu Roberto", "data_creazione": "2025-04-24T09:10:19.919699"}	postgres	\N	2025-04-24 09:10:19.919699
21	possessore	I	9	\N	{"id": 9, "attivo": true, "paternita": "fu Giuseppe", "comune_nome": "Carcare", "cognome_nome": "Caviglia Maria", "data_modifica": "2025-04-24T09:10:19.919699", "nome_completo": "Caviglia Maria fu Giuseppe", "data_creazione": "2025-04-24T09:10:19.919699"}	postgres	\N	2025-04-24 09:10:19.919699
22	possessore	I	10	\N	{"id": 10, "attivo": true, "paternita": "fu Paolo", "comune_nome": "Carcare", "cognome_nome": "Barberis Giovanni", "data_modifica": "2025-04-24T09:10:19.919699", "nome_completo": "Barberis Giovanni fu Paolo", "data_creazione": "2025-04-24T09:10:19.919699"}	postgres	\N	2025-04-24 09:10:19.919699
23	possessore	I	11	\N	{"id": 11, "attivo": true, "paternita": "fu Luigi", "comune_nome": "Cairo Montenotte", "cognome_nome": "Berruti Antonio", "data_modifica": "2025-04-24T09:10:19.919699", "nome_completo": "Berruti Antonio fu Luigi", "data_creazione": "2025-04-24T09:10:19.919699"}	postgres	\N	2025-04-24 09:10:19.919699
24	possessore	I	12	\N	{"id": 12, "attivo": true, "paternita": "fu Marco", "comune_nome": "Cairo Montenotte", "cognome_nome": "Ferraro Caterina", "data_modifica": "2025-04-24T09:10:19.919699", "nome_completo": "Ferraro Caterina fu Marco", "data_creazione": "2025-04-24T09:10:19.919699"}	postgres	\N	2025-04-24 09:10:19.919699
25	possessore	I	13	\N	{"id": 13, "attivo": true, "paternita": "fu Carlo", "comune_nome": "Altare", "cognome_nome": "Bormioli Pietro", "data_modifica": "2025-04-24T09:10:19.919699", "nome_completo": "Bormioli Pietro fu Carlo", "data_creazione": "2025-04-24T09:10:19.919699"}	postgres	\N	2025-04-24 09:10:19.919699
26	immobile	I	7	\N	{"id": 7, "natura": "Molino da cereali", "partita_id": 1, "consistenza": "150 mq", "localita_id": 1, "numero_vani": null, "numero_piani": 2, "data_modifica": "2025-04-24T09:10:19.943633", "data_creazione": "2025-04-24T09:10:19.943633", "classificazione": "Artigianale"}	postgres	\N	2025-04-24 09:10:19.943633
27	immobile	I	8	\N	{"id": 8, "natura": "Casa", "partita_id": 2, "consistenza": "210 mq", "localita_id": 2, "numero_vani": 8, "numero_piani": 3, "data_modifica": "2025-04-24T09:10:19.943633", "data_creazione": "2025-04-24T09:10:19.943633", "classificazione": "Abitazione civile"}	postgres	\N	2025-04-24 09:10:19.943633
28	immobile	I	9	\N	{"id": 9, "natura": "Magazzino", "partita_id": 3, "consistenza": "80 mq", "localita_id": 3, "numero_vani": null, "numero_piani": 1, "data_modifica": "2025-04-24T09:10:19.943633", "data_creazione": "2025-04-24T09:10:19.943633", "classificazione": "Deposito"}	postgres	\N	2025-04-24 09:10:19.943633
29	immobile	I	10	\N	{"id": 10, "natura": "Fabbricato rurale", "partita_id": 4, "consistenza": "180 mq", "localita_id": 4, "numero_vani": 5, "numero_piani": 2, "data_modifica": "2025-04-24T09:10:19.943633", "data_creazione": "2025-04-24T09:10:19.943633", "classificazione": "Abitazione rurale"}	postgres	\N	2025-04-24 09:10:19.943633
30	immobile	I	11	\N	{"id": 11, "natura": "Casa", "partita_id": 5, "consistenza": "160 mq", "localita_id": 5, "numero_vani": 6, "numero_piani": 2, "data_modifica": "2025-04-24T09:10:19.943633", "data_creazione": "2025-04-24T09:10:19.943633", "classificazione": "Abitazione civile"}	postgres	\N	2025-04-24 09:10:19.943633
31	immobile	I	12	\N	{"id": 12, "natura": "Laboratorio", "partita_id": 6, "consistenza": "120 mq", "localita_id": 6, "numero_vani": null, "numero_piani": 1, "data_modifica": "2025-04-24T09:10:19.943633", "data_creazione": "2025-04-24T09:10:19.943633", "classificazione": "Artigianale"}	postgres	\N	2025-04-24 09:10:19.943633
32	variazione	I	2	\N	{"id": 2, "tipo": "Successione", "data_modifica": "2025-04-24T09:10:19.948351", "data_creazione": "2025-04-24T09:10:19.948351", "data_variazione": "1952-08-15", "numero_riferimento": "22/52", "partita_origine_id": 5, "nominativo_riferimento": "Ferraro Caterina", "partita_destinazione_id": null}	postgres	\N	2025-04-24 09:10:19.948351
\.


--
-- Data for Name: backup_registro; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.backup_registro (id, nome_file, "timestamp", utente, dimensione_bytes, tipo, esito, messaggio, percorso_file) FROM stdin;
\.


--
-- Data for Name: comune; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.comune (nome, provincia, regione, data_creazione, data_modifica, periodo_id) FROM stdin;
Carcare	Savona	Liguria	2025-04-16 12:17:35.062104	2025-04-24 09:10:21.504433	3
Cairo Montenotte	Savona	Liguria	2025-04-16 12:17:35.463744	2025-04-24 09:10:21.504433	3
Altare	Savona	Liguria	2025-04-16 12:17:35.505129	2025-04-24 09:10:21.504433	3
Millesimo	Savona	Liguria	2025-04-16 12:17:35.554601	2025-04-24 09:10:21.504433	3
Cengio	Savona	Liguria	2025-04-16 12:17:35.599895	2025-04-24 09:10:21.504433	3
Cosseria	Savona	Liguria	2025-04-16 12:17:35.638648	2025-04-24 09:10:21.504433	3
Mallare	Savona	Liguria	2025-04-16 12:17:35.679833	2025-04-24 09:10:21.504433	3
TestPython	TestProv	TestReg	2025-04-17 09:33:34.260703	2025-04-24 09:10:21.504433	3
Vattelapesca	Savona	Liguria	2025-04-17 09:47:11.093638	2025-04-24 09:10:21.504433	3
\.


--
-- Data for Name: consultazione; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.consultazione (id, data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante, data_creazione, data_modifica) FROM stdin;
1	2025-04-16	Lucia Neri	CI XY9876543	Ricerca genealogica	Partite di Carcare	Dott. Bianchi	2025-04-16 12:17:36.962781	2025-04-16 12:17:36.962781
2	2025-04-17	Lucia Neri	CI XY9876543	Ricerca genealogica	Partite di Carcare	Dott. Bianchi	2025-04-17 09:04:57.40988	2025-04-17 09:04:57.40988
3	2025-04-01	Mario Bianchi	CI AB1234567	Ricerca storica	Registro partite Carcare 1950	Dott. Verdi	2025-04-24 09:01:43.982679	2025-04-24 09:01:43.982679
4	2025-04-05	Studio Legale Rossi	Tessera Ordine 55213	Verifica proprieta	Partite 221 e 219 Carcare	Dott. Verdi	2025-04-24 09:01:43.982679	2025-04-24 09:01:43.982679
5	2025-04-24	Lucia Neri	CI XY9876543	Ricerca genealogica	Partite di Carcare	Dott. Bianchi	2025-04-24 09:01:44.128562	2025-04-24 09:01:44.128562
6	2025-04-01	Mario Bianchi	CI AB1234567	Ricerca storica	Registro partite Carcare 1950	Dott. Verdi	2025-04-24 09:10:19.952375	2025-04-24 09:10:19.952375
7	2025-04-05	Studio Legale Rossi	Tessera Ordine 55213	Verifica proprieta	Partite 221 e 219 Carcare	Dott. Verdi	2025-04-24 09:10:19.952375	2025-04-24 09:10:19.952375
\.


--
-- Data for Name: contratto; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.contratto (id, variazione_id, tipo, data_contratto, notaio, repertorio, note, data_creazione, data_modifica) FROM stdin;
1	1	Successione	1952-08-10	Notaio Rossi	1234/52	Successione per morte del proprietario Luigi Ferraro	2025-04-24 09:01:43.97815	2025-04-24 09:01:43.97815
2	1	Successione	1952-08-10	Notaio Rossi	1234/52	Successione per morte del proprietario Luigi Ferraro	2025-04-24 09:10:19.950947	2025-04-24 09:10:19.950947
\.


--
-- Data for Name: documento_partita; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.documento_partita (documento_id, partita_id, rilevanza, note, data_creazione) FROM stdin;
\.


--
-- Data for Name: documento_storico; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.documento_storico (id, titolo, descrizione, anno, periodo_id, tipo_documento, percorso_file, metadati, data_creazione, data_modifica) FROM stdin;
\.


--
-- Data for Name: immobile; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.immobile (id, partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione, data_creazione, data_modifica) FROM stdin;
1	1	1	Molino da cereali	2	\N	150 mq	Artigianale	2025-04-24 09:01:43.970222	2025-04-24 09:01:43.970222
2	2	2	Casa	3	8	210 mq	Abitazione civile	2025-04-24 09:01:43.970222	2025-04-24 09:01:43.970222
3	3	3	Magazzino	1	\N	80 mq	Deposito	2025-04-24 09:01:43.970222	2025-04-24 09:01:43.970222
4	4	4	Fabbricato rurale	2	5	180 mq	Abitazione rurale	2025-04-24 09:01:43.970222	2025-04-24 09:01:43.970222
5	5	5	Casa	2	6	160 mq	Abitazione civile	2025-04-24 09:01:43.970222	2025-04-24 09:01:43.970222
6	6	6	Laboratorio	1	\N	120 mq	Artigianale	2025-04-24 09:01:43.970222	2025-04-24 09:01:43.970222
7	1	1	Molino da cereali	2	\N	150 mq	Artigianale	2025-04-24 09:10:19.943633	2025-04-24 09:10:19.943633
8	2	2	Casa	3	8	210 mq	Abitazione civile	2025-04-24 09:10:19.943633	2025-04-24 09:10:19.943633
9	3	3	Magazzino	1	\N	80 mq	Deposito	2025-04-24 09:10:19.943633	2025-04-24 09:10:19.943633
10	4	4	Fabbricato rurale	2	5	180 mq	Abitazione rurale	2025-04-24 09:10:19.943633	2025-04-24 09:10:19.943633
11	5	5	Casa	2	6	160 mq	Abitazione civile	2025-04-24 09:10:19.943633	2025-04-24 09:10:19.943633
12	6	6	Laboratorio	1	\N	120 mq	Artigianale	2025-04-24 09:10:19.943633	2025-04-24 09:10:19.943633
\.


--
-- Data for Name: localita; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.localita (id, comune_nome, nome, tipo, civico, data_creazione, data_modifica, periodo_id) FROM stdin;
1	Carcare	Regione Vista	regione	\N	2025-04-24 09:01:43.952224	2025-04-24 09:10:21.507923	3
2	Carcare	Via Giuseppe Verdi	via	12	2025-04-24 09:01:43.952224	2025-04-24 09:10:21.507923	3
3	Carcare	Via Roma	via	5	2025-04-24 09:01:43.952224	2025-04-24 09:10:21.507923	3
4	Cairo Montenotte	Borgata Ferrere	borgata	\N	2025-04-24 09:01:43.952224	2025-04-24 09:10:21.507923	3
5	Cairo Montenotte	Strada Provinciale	via	76	2025-04-24 09:01:43.952224	2025-04-24 09:10:21.507923	3
6	Altare	Via Palermo	via	22	2025-04-24 09:01:43.952224	2025-04-24 09:10:21.507923	3
7	Carcare	Regione Vista	regione	\N	2025-04-24 09:10:19.935974	2025-04-24 09:10:21.507923	3
10	Cairo Montenotte	Borgata Ferrere	borgata	\N	2025-04-24 09:10:19.935974	2025-04-24 09:10:21.507923	3
\.


--
-- Data for Name: nome_storico; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.nome_storico (id, entita_tipo, entita_id, nome, periodo_id, anno_inizio, anno_fine, note, data_creazione) FROM stdin;
\.


--
-- Data for Name: partita; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.partita (id, comune_nome, numero_partita, tipo, data_impianto, data_chiusura, numero_provenienza, stato, data_creazione, data_modifica) FROM stdin;
1	Carcare	302	principale	2025-04-16	\N	\N	attiva	2025-04-16 12:17:37.004166	2025-04-16 12:17:37.004166
2	Carcare	221	principale	1950-05-10	\N	\N	attiva	2025-04-24 09:01:43.955924	2025-04-24 09:01:43.955924
3	Carcare	219	principale	1950-05-10	\N	\N	attiva	2025-04-24 09:01:43.955924	2025-04-24 09:01:43.955924
4	Carcare	245	secondaria	1951-03-22	\N	\N	attiva	2025-04-24 09:01:43.955924	2025-04-24 09:01:43.955924
5	Cairo Montenotte	112	principale	1948-11-05	\N	\N	attiva	2025-04-24 09:01:43.955924	2025-04-24 09:01:43.955924
6	Cairo Montenotte	118	principale	1949-01-15	\N	\N	inattiva	2025-04-24 09:01:43.955924	2025-04-24 09:01:43.955924
7	Altare	87	principale	1952-07-03	\N	\N	attiva	2025-04-24 09:01:43.955924	2025-04-24 09:01:43.955924
\.


--
-- Data for Name: partita_possessore; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.partita_possessore (id, partita_id, possessore_id, tipo_partita, titolo, quota, data_creazione, data_modifica) FROM stdin;
1	1	1	principale	proprietÃ  esclusiva	\N	2025-04-16 12:17:37.004166	2025-04-16 12:17:37.004166
3	2	2	principale	proprieta esclusiva	\N	2025-04-24 09:01:43.960181	2025-04-24 09:01:43.960181
4	3	3	secondaria	comproprieta	1/2	2025-04-24 09:01:43.960181	2025-04-24 09:01:43.960181
5	3	2	secondaria	comproprieta	1/2	2025-04-24 09:01:43.960181	2025-04-24 09:01:43.960181
6	4	4	principale	proprieta esclusiva	\N	2025-04-24 09:01:43.960181	2025-04-24 09:01:43.960181
7	5	5	principale	proprieta esclusiva	\N	2025-04-24 09:01:43.960181	2025-04-24 09:01:43.960181
8	6	6	principale	proprieta esclusiva	\N	2025-04-24 09:01:43.960181	2025-04-24 09:01:43.960181
\.


--
-- Data for Name: partita_relazione; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.partita_relazione (id, partita_principale_id, partita_secondaria_id, data_creazione, data_modifica) FROM stdin;
1	2	3	2025-04-24 09:01:43.96691	2025-04-24 09:01:43.96691
\.


--
-- Data for Name: periodo_storico; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.periodo_storico (id, nome, anno_inizio, anno_fine, descrizione, data_creazione) FROM stdin;
1	Regno di Sardegna	1720	1861	Periodo del Regno di Sardegna prima dell'unitÃ  d'Italia	2025-04-16 12:17:38.486437
2	Regno d'Italia	1861	1946	Periodo del Regno d'Italia	2025-04-16 12:17:38.486437
3	Repubblica Italiana	1946	\N	Periodo della Repubblica Italiana	2025-04-16 12:17:38.486437
4	Regno di Sardegna	1720	1861	Periodo del Regno di Sardegna prima dell'unitÃ  d'Italia	2025-04-17 09:04:58.827348
5	Regno d'Italia	1861	1946	Periodo del Regno d'Italia	2025-04-17 09:04:58.827348
6	Repubblica Italiana	1946	\N	Periodo della Repubblica Italiana	2025-04-17 09:04:58.827348
7	Regno di Sardegna	1720	1861	Periodo del Regno di Sardegna prima dell'unitÃ  d'Italia	2025-04-24 09:01:45.496924
8	Regno d'Italia	1861	1946	Periodo del Regno d'Italia	2025-04-24 09:01:45.496924
9	Repubblica Italiana	1946	\N	Periodo della Repubblica Italiana	2025-04-24 09:01:45.496924
10	Regno di Sardegna	1720	1861	Periodo del Regno di Sardegna prima dell'unitÃ  d'Italia	2025-04-24 09:10:21.488439
11	Regno d'Italia	1861	1946	Periodo del Regno d'Italia	2025-04-24 09:10:21.488439
12	Repubblica Italiana	1946	\N	Periodo della Repubblica Italiana	2025-04-24 09:10:21.488439
\.


--
-- Data for Name: permesso; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.permesso (id, nome, descrizione) FROM stdin;
1	visualizza_partite	Permesso di visualizzare le partite catastali
2	modifica_partite	Permesso di modificare le partite catastali
3	visualizza_possessori	Permesso di visualizzare i possessori
4	modifica_possessori	Permesso di modificare i possessori
5	visualizza_immobili	Permesso di visualizzare gli immobili
6	modifica_immobili	Permesso di modificare gli immobili
7	registra_variazioni	Permesso di registrare variazioni di proprietÃ 
8	gestione_utenti	Permesso di gestire gli utenti
\.


--
-- Data for Name: possessore; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.possessore (id, comune_nome, cognome_nome, paternita, nome_completo, attivo, data_creazione, data_modifica) FROM stdin;
1	Carcare	Rossi Marco	fu Antonio	Rossi Marco fu Antonio	t	2025-04-16 12:17:36.912922	2025-04-16 12:17:36.912922
2	Carcare	Fossati Angelo	fu Roberto	Fossati Angelo fu Roberto	t	2025-04-24 09:01:43.937988	2025-04-24 09:01:43.937988
3	Carcare	Caviglia Maria	fu Giuseppe	Caviglia Maria fu Giuseppe	t	2025-04-24 09:01:43.937988	2025-04-24 09:01:43.937988
4	Carcare	Barberis Giovanni	fu Paolo	Barberis Giovanni fu Paolo	t	2025-04-24 09:01:43.937988	2025-04-24 09:01:43.937988
5	Cairo Montenotte	Berruti Antonio	fu Luigi	Berruti Antonio fu Luigi	t	2025-04-24 09:01:43.937988	2025-04-24 09:01:43.937988
6	Cairo Montenotte	Ferraro Caterina	fu Marco	Ferraro Caterina fu Marco	t	2025-04-24 09:01:43.937988	2025-04-24 09:01:43.937988
7	Altare	Bormioli Pietro	fu Carlo	Bormioli Pietro fu Carlo	t	2025-04-24 09:01:43.937988	2025-04-24 09:01:43.937988
8	Carcare	Fossati Angelo	fu Roberto	Fossati Angelo fu Roberto	t	2025-04-24 09:10:19.919699	2025-04-24 09:10:19.919699
9	Carcare	Caviglia Maria	fu Giuseppe	Caviglia Maria fu Giuseppe	t	2025-04-24 09:10:19.919699	2025-04-24 09:10:19.919699
10	Carcare	Barberis Giovanni	fu Paolo	Barberis Giovanni fu Paolo	t	2025-04-24 09:10:19.919699	2025-04-24 09:10:19.919699
11	Cairo Montenotte	Berruti Antonio	fu Luigi	Berruti Antonio fu Luigi	t	2025-04-24 09:10:19.919699	2025-04-24 09:10:19.919699
12	Cairo Montenotte	Ferraro Caterina	fu Marco	Ferraro Caterina fu Marco	t	2025-04-24 09:10:19.919699	2025-04-24 09:10:19.919699
13	Altare	Bormioli Pietro	fu Carlo	Bormioli Pietro fu Carlo	t	2025-04-24 09:10:19.919699	2025-04-24 09:10:19.919699
\.


--
-- Data for Name: registro_matricole; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.registro_matricole (id, comune_nome, anno_impianto, numero_volumi, stato_conservazione, data_creazione, data_modifica) FROM stdin;
1	Carcare	1950	2	Buono	2025-04-24 09:01:43.935845	2025-04-24 09:01:43.935845
2	Cairo Montenotte	1948	4	Discreto	2025-04-24 09:01:43.935845	2025-04-24 09:01:43.935845
3	Altare	1952	1	Ottimo	2025-04-24 09:01:43.935845	2025-04-24 09:01:43.935845
\.


--
-- Data for Name: registro_partite; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.registro_partite (id, comune_nome, anno_impianto, numero_volumi, stato_conservazione, data_creazione, data_modifica) FROM stdin;
1	Carcare	1950	3	Buono	2025-04-24 09:01:43.926852	2025-04-24 09:01:43.926852
2	Cairo Montenotte	1948	5	Discreto	2025-04-24 09:01:43.926852	2025-04-24 09:01:43.926852
3	Altare	1952	2	Ottimo	2025-04-24 09:01:43.926852	2025-04-24 09:01:43.926852
\.


--
-- Data for Name: utente; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.utente (id, username, password_hash, nome_completo, email, ruolo, attivo, ultimo_accesso, data_creazione, data_modifica) FROM stdin;
1	admin	password_hash_qui	Amministratore Sistema	admin@example.com	admin	t	\N	2025-04-16 12:17:37.738135	2025-04-16 12:17:37.738135
5	Cippalippa	5bff8298738960aa703dad31c86bfcfa75babf4fbc76e5a6e3d9bd1f54e6dbe5	Anton Giulio Cippalippa 	cippalippa@email.com	archivista	t	2025-04-24 10:32:57.042028	2025-04-24 10:31:49.596425	2025-04-24 10:32:57.042028
\.


--
-- Data for Name: utente_permesso; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.utente_permesso (utente_id, permesso_id, data_assegnazione) FROM stdin;
\.


--
-- Data for Name: v_count; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.v_count (count) FROM stdin;
0
\.


--
-- Data for Name: variazione; Type: TABLE DATA; Schema: catasto; Owner: postgres
--

COPY catasto.variazione (id, partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento, data_creazione, data_modifica) FROM stdin;
1	5	\N	Successione	1952-08-15	22/52	Ferraro Caterina	2025-04-24 09:01:43.975491	2025-04-24 09:01:43.975491
2	5	\N	Successione	1952-08-15	22/52	Ferraro Caterina	2025-04-24 09:10:19.948351	2025-04-24 09:10:19.948351
\.


--
-- Name: accesso_log_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.accesso_log_id_seq', 1, true);


--
-- Name: audit_log_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.audit_log_id_seq', 32, true);


--
-- Name: backup_registro_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.backup_registro_id_seq', 1, false);


--
-- Name: consultazione_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.consultazione_id_seq', 7, true);


--
-- Name: contratto_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.contratto_id_seq', 2, true);


--
-- Name: documento_storico_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.documento_storico_id_seq', 1, false);


--
-- Name: immobile_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.immobile_id_seq', 12, true);


--
-- Name: localita_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.localita_id_seq', 12, true);


--
-- Name: nome_storico_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.nome_storico_id_seq', 1, false);


--
-- Name: partita_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.partita_id_seq', 13, true);


--
-- Name: partita_possessore_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.partita_possessore_id_seq', 15, true);


--
-- Name: partita_relazione_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.partita_relazione_id_seq', 2, true);


--
-- Name: periodo_storico_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.periodo_storico_id_seq', 12, true);


--
-- Name: permesso_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.permesso_id_seq', 11, true);


--
-- Name: possessore_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.possessore_id_seq', 13, true);


--
-- Name: registro_matricole_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.registro_matricole_id_seq', 6, true);


--
-- Name: registro_partite_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.registro_partite_id_seq', 6, true);


--
-- Name: utente_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.utente_id_seq', 5, true);


--
-- Name: variazione_id_seq; Type: SEQUENCE SET; Schema: catasto; Owner: postgres
--

SELECT pg_catalog.setval('catasto.variazione_id_seq', 2, true);


--
-- Name: accesso_log accesso_log_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.accesso_log
    ADD CONSTRAINT accesso_log_pkey PRIMARY KEY (id);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: backup_registro backup_registro_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.backup_registro
    ADD CONSTRAINT backup_registro_pkey PRIMARY KEY (id);


--
-- Name: comune comune_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.comune
    ADD CONSTRAINT comune_pkey PRIMARY KEY (nome);


--
-- Name: consultazione consultazione_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.consultazione
    ADD CONSTRAINT consultazione_pkey PRIMARY KEY (id);


--
-- Name: contratto contratto_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.contratto
    ADD CONSTRAINT contratto_pkey PRIMARY KEY (id);


--
-- Name: documento_partita documento_partita_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.documento_partita
    ADD CONSTRAINT documento_partita_pkey PRIMARY KEY (documento_id, partita_id);


--
-- Name: documento_storico documento_storico_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.documento_storico
    ADD CONSTRAINT documento_storico_pkey PRIMARY KEY (id);


--
-- Name: immobile immobile_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.immobile
    ADD CONSTRAINT immobile_pkey PRIMARY KEY (id);


--
-- Name: localita localita_comune_nome_nome_civico_key; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.localita
    ADD CONSTRAINT localita_comune_nome_nome_civico_key UNIQUE (comune_nome, nome, civico);


--
-- Name: localita localita_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.localita
    ADD CONSTRAINT localita_pkey PRIMARY KEY (id);


--
-- Name: nome_storico nome_storico_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.nome_storico
    ADD CONSTRAINT nome_storico_pkey PRIMARY KEY (id);


--
-- Name: partita partita_comune_nome_numero_partita_key; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita
    ADD CONSTRAINT partita_comune_nome_numero_partita_key UNIQUE (comune_nome, numero_partita);


--
-- Name: partita partita_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita
    ADD CONSTRAINT partita_pkey PRIMARY KEY (id);


--
-- Name: partita_possessore partita_possessore_partita_id_possessore_id_key; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita_possessore
    ADD CONSTRAINT partita_possessore_partita_id_possessore_id_key UNIQUE (partita_id, possessore_id);


--
-- Name: partita_possessore partita_possessore_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita_possessore
    ADD CONSTRAINT partita_possessore_pkey PRIMARY KEY (id);


--
-- Name: partita_relazione partita_relazione_partita_principale_id_partita_secondaria__key; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita_relazione
    ADD CONSTRAINT partita_relazione_partita_principale_id_partita_secondaria__key UNIQUE (partita_principale_id, partita_secondaria_id);


--
-- Name: partita_relazione partita_relazione_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita_relazione
    ADD CONSTRAINT partita_relazione_pkey PRIMARY KEY (id);


--
-- Name: periodo_storico periodo_storico_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.periodo_storico
    ADD CONSTRAINT periodo_storico_pkey PRIMARY KEY (id);


--
-- Name: permesso permesso_nome_key; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.permesso
    ADD CONSTRAINT permesso_nome_key UNIQUE (nome);


--
-- Name: permesso permesso_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.permesso
    ADD CONSTRAINT permesso_pkey PRIMARY KEY (id);


--
-- Name: possessore possessore_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.possessore
    ADD CONSTRAINT possessore_pkey PRIMARY KEY (id);


--
-- Name: registro_matricole registro_matricole_comune_nome_anno_impianto_key; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.registro_matricole
    ADD CONSTRAINT registro_matricole_comune_nome_anno_impianto_key UNIQUE (comune_nome, anno_impianto);


--
-- Name: registro_matricole registro_matricole_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.registro_matricole
    ADD CONSTRAINT registro_matricole_pkey PRIMARY KEY (id);


--
-- Name: registro_partite registro_partite_comune_nome_anno_impianto_key; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.registro_partite
    ADD CONSTRAINT registro_partite_comune_nome_anno_impianto_key UNIQUE (comune_nome, anno_impianto);


--
-- Name: registro_partite registro_partite_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.registro_partite
    ADD CONSTRAINT registro_partite_pkey PRIMARY KEY (id);


--
-- Name: utente utente_email_key; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.utente
    ADD CONSTRAINT utente_email_key UNIQUE (email);


--
-- Name: utente_permesso utente_permesso_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.utente_permesso
    ADD CONSTRAINT utente_permesso_pkey PRIMARY KEY (utente_id, permesso_id);


--
-- Name: utente utente_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.utente
    ADD CONSTRAINT utente_pkey PRIMARY KEY (id);


--
-- Name: utente utente_username_key; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.utente
    ADD CONSTRAINT utente_username_key UNIQUE (username);


--
-- Name: variazione variazione_pkey; Type: CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.variazione
    ADD CONSTRAINT variazione_pkey PRIMARY KEY (id);


--
-- Name: idx_accesso_timestamp; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_accesso_timestamp ON catasto.accesso_log USING btree ("timestamp");


--
-- Name: idx_accesso_utente; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_accesso_utente ON catasto.accesso_log USING btree (utente_id);


--
-- Name: idx_audit_operazione; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_audit_operazione ON catasto.audit_log USING btree (operazione);


--
-- Name: idx_audit_tabella; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_audit_tabella ON catasto.audit_log USING btree (tabella);


--
-- Name: idx_audit_timestamp; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_audit_timestamp ON catasto.audit_log USING btree ("timestamp");


--
-- Name: idx_backup_timestamp; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_backup_timestamp ON catasto.backup_registro USING btree ("timestamp");


--
-- Name: idx_backup_tipo; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_backup_tipo ON catasto.backup_registro USING btree (tipo);


--
-- Name: idx_contratto_variazione; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_contratto_variazione ON catasto.contratto USING btree (variazione_id);


--
-- Name: idx_documento_anno; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_documento_anno ON catasto.documento_storico USING btree (anno);


--
-- Name: idx_documento_periodo; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_documento_periodo ON catasto.documento_storico USING btree (periodo_id);


--
-- Name: idx_documento_tipo; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_documento_tipo ON catasto.documento_storico USING btree (tipo_documento);


--
-- Name: idx_immobile_localita; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_immobile_localita ON catasto.immobile USING btree (localita_id);


--
-- Name: idx_immobile_natura; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_immobile_natura ON catasto.immobile USING btree (natura);


--
-- Name: idx_immobile_partita; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_immobile_partita ON catasto.immobile USING btree (partita_id);


--
-- Name: idx_localita_comune; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_localita_comune ON catasto.localita USING btree (comune_nome);


--
-- Name: idx_localita_nome; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_localita_nome ON catasto.localita USING btree (nome);


--
-- Name: idx_mv_immobili_tipologia_class; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_mv_immobili_tipologia_class ON catasto.mv_immobili_per_tipologia USING btree (classificazione);


--
-- Name: idx_mv_immobili_tipologia_comune; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_mv_immobili_tipologia_comune ON catasto.mv_immobili_per_tipologia USING btree (comune_nome);


--
-- Name: idx_mv_partite_complete_comune; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_mv_partite_complete_comune ON catasto.mv_partite_complete USING btree (comune_nome);


--
-- Name: idx_mv_partite_complete_numero; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_mv_partite_complete_numero ON catasto.mv_partite_complete USING btree (numero_partita);


--
-- Name: idx_mv_partite_complete_stato; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_mv_partite_complete_stato ON catasto.mv_partite_complete USING btree (stato);


--
-- Name: idx_mv_statistiche_comune; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE UNIQUE INDEX idx_mv_statistiche_comune ON catasto.mv_statistiche_comune USING btree (comune);


--
-- Name: idx_mv_variazioni_comune_orig; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_mv_variazioni_comune_orig ON catasto.mv_cronologia_variazioni USING btree (comune_origine);


--
-- Name: idx_mv_variazioni_data; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_mv_variazioni_data ON catasto.mv_cronologia_variazioni USING btree (data_variazione);


--
-- Name: idx_mv_variazioni_tipo; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_mv_variazioni_tipo ON catasto.mv_cronologia_variazioni USING btree (tipo_variazione);


--
-- Name: idx_nome_storico_entita; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_nome_storico_entita ON catasto.nome_storico USING btree (entita_tipo, entita_id);


--
-- Name: idx_nome_storico_periodo; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_nome_storico_periodo ON catasto.nome_storico USING btree (periodo_id);


--
-- Name: idx_partita_comune; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_partita_comune ON catasto.partita USING btree (comune_nome);


--
-- Name: idx_partita_numero; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_partita_numero ON catasto.partita USING btree (numero_partita);


--
-- Name: idx_partita_possessore_partita; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_partita_possessore_partita ON catasto.partita_possessore USING btree (partita_id);


--
-- Name: idx_partita_possessore_possessore; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_partita_possessore_possessore ON catasto.partita_possessore USING btree (possessore_id);


--
-- Name: idx_possessore_comune; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_possessore_comune ON catasto.possessore USING btree (comune_nome);


--
-- Name: idx_possessore_nome; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_possessore_nome ON catasto.possessore USING btree (nome_completo);


--
-- Name: idx_trgm_immobile_natura; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_trgm_immobile_natura ON catasto.immobile USING gin (natura catasto.gin_trgm_ops);


--
-- Name: idx_trgm_localita_nome; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_trgm_localita_nome ON catasto.localita USING gin (nome catasto.gin_trgm_ops);


--
-- Name: idx_trgm_possessore_cognome; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_trgm_possessore_cognome ON catasto.possessore USING gin (cognome_nome catasto.gin_trgm_ops);


--
-- Name: idx_trgm_possessore_nome; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_trgm_possessore_nome ON catasto.possessore USING gin (nome_completo catasto.gin_trgm_ops);


--
-- Name: idx_utente_ruolo; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_utente_ruolo ON catasto.utente USING btree (ruolo);


--
-- Name: idx_utente_username; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_utente_username ON catasto.utente USING btree (username);


--
-- Name: idx_variazione_partita_destinazione; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_variazione_partita_destinazione ON catasto.variazione USING btree (partita_destinazione_id);


--
-- Name: idx_variazione_partita_origine; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_variazione_partita_origine ON catasto.variazione USING btree (partita_origine_id);


--
-- Name: idx_variazione_tipo; Type: INDEX; Schema: catasto; Owner: postgres
--

CREATE INDEX idx_variazione_tipo ON catasto.variazione USING btree (tipo);


--
-- Name: immobile audit_trigger_immobile; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER audit_trigger_immobile AFTER INSERT OR DELETE OR UPDATE ON catasto.immobile FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();


--
-- Name: partita audit_trigger_partita; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER audit_trigger_partita AFTER INSERT OR DELETE OR UPDATE ON catasto.partita FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();


--
-- Name: possessore audit_trigger_possessore; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER audit_trigger_possessore AFTER INSERT OR DELETE OR UPDATE ON catasto.possessore FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();


--
-- Name: variazione audit_trigger_variazione; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER audit_trigger_variazione AFTER INSERT OR DELETE OR UPDATE ON catasto.variazione FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();


--
-- Name: comune update_comune_modifica; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER update_comune_modifica BEFORE UPDATE ON catasto.comune FOR EACH ROW EXECUTE FUNCTION catasto.update_modified_column();


--
-- Name: immobile update_immobile_modifica; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER update_immobile_modifica BEFORE UPDATE ON catasto.immobile FOR EACH ROW EXECUTE FUNCTION catasto.update_modified_column();


--
-- Name: localita update_localita_modifica; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER update_localita_modifica BEFORE UPDATE ON catasto.localita FOR EACH ROW EXECUTE FUNCTION catasto.update_modified_column();


--
-- Name: partita update_partita_modifica; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER update_partita_modifica BEFORE UPDATE ON catasto.partita FOR EACH ROW EXECUTE FUNCTION catasto.update_modified_column();


--
-- Name: possessore update_possessore_modifica; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER update_possessore_modifica BEFORE UPDATE ON catasto.possessore FOR EACH ROW EXECUTE FUNCTION catasto.update_modified_column();


--
-- Name: utente update_utente_modifica; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER update_utente_modifica BEFORE UPDATE ON catasto.utente FOR EACH ROW EXECUTE FUNCTION catasto.update_modified_column();


--
-- Name: variazione update_variazione_modifica; Type: TRIGGER; Schema: catasto; Owner: postgres
--

CREATE TRIGGER update_variazione_modifica BEFORE UPDATE ON catasto.variazione FOR EACH ROW EXECUTE FUNCTION catasto.update_modified_column();


--
-- Name: accesso_log accesso_log_utente_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.accesso_log
    ADD CONSTRAINT accesso_log_utente_id_fkey FOREIGN KEY (utente_id) REFERENCES catasto.utente(id);


--
-- Name: comune comune_periodo_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.comune
    ADD CONSTRAINT comune_periodo_id_fkey FOREIGN KEY (periodo_id) REFERENCES catasto.periodo_storico(id);


--
-- Name: contratto contratto_variazione_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.contratto
    ADD CONSTRAINT contratto_variazione_id_fkey FOREIGN KEY (variazione_id) REFERENCES catasto.variazione(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: documento_partita documento_partita_documento_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.documento_partita
    ADD CONSTRAINT documento_partita_documento_id_fkey FOREIGN KEY (documento_id) REFERENCES catasto.documento_storico(id) ON DELETE CASCADE;


--
-- Name: documento_partita documento_partita_partita_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.documento_partita
    ADD CONSTRAINT documento_partita_partita_id_fkey FOREIGN KEY (partita_id) REFERENCES catasto.partita(id) ON DELETE CASCADE;


--
-- Name: documento_storico documento_storico_periodo_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.documento_storico
    ADD CONSTRAINT documento_storico_periodo_id_fkey FOREIGN KEY (periodo_id) REFERENCES catasto.periodo_storico(id);


--
-- Name: immobile immobile_localita_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.immobile
    ADD CONSTRAINT immobile_localita_id_fkey FOREIGN KEY (localita_id) REFERENCES catasto.localita(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: immobile immobile_partita_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.immobile
    ADD CONSTRAINT immobile_partita_id_fkey FOREIGN KEY (partita_id) REFERENCES catasto.partita(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: localita localita_comune_nome_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.localita
    ADD CONSTRAINT localita_comune_nome_fkey FOREIGN KEY (comune_nome) REFERENCES catasto.comune(nome) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: localita localita_periodo_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.localita
    ADD CONSTRAINT localita_periodo_id_fkey FOREIGN KEY (periodo_id) REFERENCES catasto.periodo_storico(id);


--
-- Name: nome_storico nome_storico_periodo_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.nome_storico
    ADD CONSTRAINT nome_storico_periodo_id_fkey FOREIGN KEY (periodo_id) REFERENCES catasto.periodo_storico(id);


--
-- Name: partita partita_comune_nome_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita
    ADD CONSTRAINT partita_comune_nome_fkey FOREIGN KEY (comune_nome) REFERENCES catasto.comune(nome) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: partita_possessore partita_possessore_partita_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita_possessore
    ADD CONSTRAINT partita_possessore_partita_id_fkey FOREIGN KEY (partita_id) REFERENCES catasto.partita(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: partita_possessore partita_possessore_possessore_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita_possessore
    ADD CONSTRAINT partita_possessore_possessore_id_fkey FOREIGN KEY (possessore_id) REFERENCES catasto.possessore(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: partita_relazione partita_relazione_partita_principale_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita_relazione
    ADD CONSTRAINT partita_relazione_partita_principale_id_fkey FOREIGN KEY (partita_principale_id) REFERENCES catasto.partita(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: partita_relazione partita_relazione_partita_secondaria_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.partita_relazione
    ADD CONSTRAINT partita_relazione_partita_secondaria_id_fkey FOREIGN KEY (partita_secondaria_id) REFERENCES catasto.partita(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: possessore possessore_comune_nome_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.possessore
    ADD CONSTRAINT possessore_comune_nome_fkey FOREIGN KEY (comune_nome) REFERENCES catasto.comune(nome) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: registro_matricole registro_matricole_comune_nome_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.registro_matricole
    ADD CONSTRAINT registro_matricole_comune_nome_fkey FOREIGN KEY (comune_nome) REFERENCES catasto.comune(nome) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: registro_partite registro_partite_comune_nome_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.registro_partite
    ADD CONSTRAINT registro_partite_comune_nome_fkey FOREIGN KEY (comune_nome) REFERENCES catasto.comune(nome) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: utente_permesso utente_permesso_permesso_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.utente_permesso
    ADD CONSTRAINT utente_permesso_permesso_id_fkey FOREIGN KEY (permesso_id) REFERENCES catasto.permesso(id) ON DELETE CASCADE;


--
-- Name: utente_permesso utente_permesso_utente_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.utente_permesso
    ADD CONSTRAINT utente_permesso_utente_id_fkey FOREIGN KEY (utente_id) REFERENCES catasto.utente(id) ON DELETE CASCADE;


--
-- Name: variazione variazione_partita_destinazione_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.variazione
    ADD CONSTRAINT variazione_partita_destinazione_id_fkey FOREIGN KEY (partita_destinazione_id) REFERENCES catasto.partita(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: variazione variazione_partita_origine_id_fkey; Type: FK CONSTRAINT; Schema: catasto; Owner: postgres
--

ALTER TABLE ONLY catasto.variazione
    ADD CONSTRAINT variazione_partita_origine_id_fkey FOREIGN KEY (partita_origine_id) REFERENCES catasto.partita(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- Name: mv_cronologia_variazioni; Type: MATERIALIZED VIEW DATA; Schema: catasto; Owner: postgres
--

REFRESH MATERIALIZED VIEW catasto.mv_cronologia_variazioni;


--
-- Name: mv_immobili_per_tipologia; Type: MATERIALIZED VIEW DATA; Schema: catasto; Owner: postgres
--

REFRESH MATERIALIZED VIEW catasto.mv_immobili_per_tipologia;


--
-- Name: mv_partite_complete; Type: MATERIALIZED VIEW DATA; Schema: catasto; Owner: postgres
--

REFRESH MATERIALIZED VIEW catasto.mv_partite_complete;


--
-- Name: mv_statistiche_comune; Type: MATERIALIZED VIEW DATA; Schema: catasto; Owner: postgres
--

REFRESH MATERIALIZED VIEW catasto.mv_statistiche_comune;


--
-- PostgreSQL database dump complete
--

