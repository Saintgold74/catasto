-- Filename: 15_integration_audit_users.sql
-- =========================================================================
-- Integrazione sistema di audit con sistema utenti
-- Versione: 1.1 (Corretta)
-- Data: 25/04/2025
-- =========================================================================

-- Imposta lo schema
SET search_path TO catasto;

-- =========================================================================
-- FASE 1: Modifica delle tabelle esistenti
-- =========================================================================

-- Aggiungi colonne per collegare audit_log con il sistema utenti
-- Aggiungi colonne solo se non esistono già per rendere lo script rieseguibile
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'catasto' AND table_name = 'audit_log' AND column_name = 'session_id') THEN
        ALTER TABLE catasto.audit_log ADD COLUMN session_id VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'catasto' AND table_name = 'audit_log' AND column_name = 'app_user_id') THEN
        ALTER TABLE catasto.audit_log ADD COLUMN app_user_id INTEGER;
    END IF;
END $$;

-- Aggiungiamo un vincolo di chiave esterna posticipato
-- Aggiungi vincolo solo se non esiste già
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_audit_user' AND conrelid = 'catasto.audit_log'::regclass) THEN
        ALTER TABLE catasto.audit_log
        ADD CONSTRAINT fk_audit_user
          FOREIGN KEY (app_user_id) REFERENCES catasto.utente(id)
          DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;

-- Aggiunta colonne alla tabella accesso_log
-- Aggiungi colonne solo se non esistono già
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'catasto' AND table_name = 'accesso_log' AND column_name = 'session_id') THEN
        ALTER TABLE catasto.accesso_log ADD COLUMN session_id VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'catasto' AND table_name = 'accesso_log' AND column_name = 'application_name') THEN
        ALTER TABLE catasto.accesso_log ADD COLUMN application_name VARCHAR(100);
    END IF;
END $$;


-- =========================================================================
-- FASE 2: Funzioni di supporto
-- =========================================================================

-- Funzione per generare un session_id univoco
-- Usiamo uuid-ossp se disponibile per ID più robusti, altrimenti fallback a md5
CREATE OR REPLACE FUNCTION genera_session_id() RETURNS VARCHAR AS $$
DECLARE
  v_uuid_ext_exists BOOLEAN;
BEGIN
  SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp') INTO v_uuid_ext_exists;
  IF v_uuid_ext_exists THEN
    RETURN uuid_generate_v4()::VARCHAR;
  ELSE
    -- Fallback a md5 (meno ideale per unicità globale ma funziona)
    RETURN md5(random()::text || clock_timestamp()::text);
  END IF;
END;
$$ LANGUAGE plpgsql VOLATILE; -- VOLATILE perché dipende da random() o uuid

-- Funzione per impostare le variabili di sessione (da chiamare DOPO il login nell'applicazione)
-- Nota: set_config imposta la variabile solo per la transazione corrente se is_local=TRUE
-- o per la sessione corrente se is_local=FALSE. Usiamo FALSE.
CREATE OR REPLACE FUNCTION imposta_utente_sessione(
    p_user_id INTEGER,
    p_session_id VARCHAR,
    p_ip_address VARCHAR
) RETURNS VOID AS $$
BEGIN
    -- Impostazione delle variabili di sessione
    PERFORM set_config('app.user_id', p_user_id::text, FALSE);
    PERFORM set_config('app.session_id', p_session_id, FALSE);
    PERFORM set_config('app.ip_address', p_ip_address, FALSE);
    RAISE NOTICE 'Variabili di sessione impostate: user_id=%, session_id=%, ip=%', p_user_id, p_session_id, p_ip_address;
END;
$$ LANGUAGE plpgsql;

-- Funzione per ottenere informazioni sulla sessione corrente (per debug o controllo)
CREATE OR REPLACE FUNCTION get_sessione_info()
RETURNS TABLE (
    app_user_id INTEGER,
    session_id VARCHAR,
    ip_address VARCHAR,
    db_user_name TEXT,
    is_active BOOLEAN
) AS $$
DECLARE
    v_app_user_id TEXT;
    v_session_id TEXT;
    v_ip_address TEXT;
BEGIN
    -- Prova a recuperare le variabili di sessione
    v_app_user_id := current_setting('app.user_id', TRUE); -- TRUE per non generare errore se non impostata
    v_session_id := current_setting('app.session_id', TRUE);
    v_ip_address := current_setting('app.ip_address', TRUE);

    app_user_id := NULLIF(v_app_user_id, '')::INTEGER; -- Converte in INTEGER, gestendo stringa vuota
    session_id := v_session_id;
    ip_address := v_ip_address;
    db_user_name := current_user;
    is_active := v_app_user_id IS NOT NULL AND v_session_id IS NOT NULL;

    RETURN NEXT;

END;
$$ LANGUAGE plpgsql;

-- =========================================================================
-- FASE 3: Aggiornamento funzione trigger di audit
-- =========================================================================

-- Aggiornamento della funzione di audit per utilizzare il contesto di sessione
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    v_old_data JSONB;
    v_new_data JSONB;
    v_db_user TEXT;
    v_app_user_id INTEGER;
    v_session_id TEXT;
    v_ip_address TEXT;
    v_record_id INTEGER;
BEGIN
    -- Ottieni l'utente di database corrente
    v_db_user := session_user; -- Usiamo session_user invece di current_user per l'utente originale della sessione

    -- Tenta di recuperare le variabili di sessione
    v_app_user_id := NULLIF(current_setting('app.user_id', TRUE), '')::INTEGER;
    v_session_id := current_setting('app.session_id', TRUE);
    v_ip_address := current_setting('app.ip_address', TRUE);

    -- Determina l'operazione e l'ID del record
    IF TG_OP = 'INSERT' THEN
        v_old_data := NULL;
        v_new_data := to_jsonb(NEW);
        v_record_id := NEW.id; -- Assumiamo che tutte le tabelle auditate abbiano una colonna 'id' come PK
        INSERT INTO catasto.audit_log (
            tabella, operazione, record_id, dati_prima, dati_dopo,
            utente, app_user_id, session_id, ip_address
        )
        VALUES (
            TG_TABLE_NAME, 'I', v_record_id, v_old_data, v_new_data,
            v_db_user, v_app_user_id, v_session_id, v_ip_address
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Non registrare se i dati JSON sono identici (evita log inutili)
        IF to_jsonb(OLD) IS NOT DISTINCT FROM to_jsonb(NEW) THEN
            RETURN NEW; -- Nessuna modifica effettiva
        END IF;
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        v_record_id := NEW.id;
        INSERT INTO catasto.audit_log (
            tabella, operazione, record_id, dati_prima, dati_dopo,
            utente, app_user_id, session_id, ip_address
        )
        VALUES (
            TG_TABLE_NAME, 'U', v_record_id, v_old_data, v_new_data,
            v_db_user, v_app_user_id, v_session_id, v_ip_address
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := NULL;
        v_record_id := OLD.id;
        INSERT INTO catasto.audit_log (
            tabella, operazione, record_id, dati_prima, dati_dopo,
            utente, app_user_id, session_id, ip_address
        )
        VALUES (
            TG_TABLE_NAME, 'D', v_record_id, v_old_data, v_new_data,
            v_db_user, v_app_user_id, v_session_id, v_ip_address
        );
        RETURN OLD;
    END IF;
    RETURN NULL; -- In caso di TG_OP non gestito
END;
$$ LANGUAGE plpgsql;

-- Assicurarsi che il trigger sia applicato (potrebbe essere già stato fatto)
-- Riapplicare i trigger per usare la nuova funzione aggiornata (se necessario)
DO $$
DECLARE
  tbl RECORD;
BEGIN
  FOR tbl IN SELECT table_name FROM information_schema.tables
             WHERE table_schema = 'catasto' AND table_type = 'BASE TABLE'
             AND table_name IN ('partita', 'possessore', 'immobile', 'variazione', 'contratto', 'consultazione', 'localita', 'comune') -- Elenca tabelle da auditare
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS audit_trigger_%I ON catasto.%I;', tbl.table_name, tbl.table_name);
    EXECUTE format('CREATE TRIGGER audit_trigger_%I AFTER INSERT OR UPDATE OR DELETE ON catasto.%I FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();', tbl.table_name, tbl.table_name);
    RAISE NOTICE 'Trigger di audit applicato a %.%', 'catasto', tbl.table_name;
  END LOOP;
END $$;


-- =========================================================================
-- FASE 4: Aggiornamento procedure per registrazione accessi
-- =========================================================================

-- Aggiornamento della procedura di registrazione accesso per usare session_id e application_name
CREATE OR REPLACE PROCEDURE registra_accesso(
    p_utente_id INTEGER,
    p_azione VARCHAR(50),
    p_indirizzo_ip VARCHAR(40) DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL,
    p_esito BOOLEAN DEFAULT TRUE,
    p_session_id VARCHAR(100) DEFAULT NULL, -- Rende session_id un parametro IN
    p_application_name VARCHAR(100) DEFAULT 'CatastoApp'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_generated_session_id VARCHAR(100);
BEGIN
    -- Usa il session_id fornito, altrimenti ne genera uno nuovo
    v_generated_session_id := COALESCE(p_session_id, genera_session_id());

    -- Registra l'accesso con il session_id
    INSERT INTO catasto.accesso_log (
        utente_id, timestamp, azione,
        indirizzo_ip, user_agent, esito,
        session_id, application_name
    )
    VALUES (
        p_utente_id, CURRENT_TIMESTAMP, p_azione,
        p_indirizzo_ip, p_user_agent, p_esito,
        v_generated_session_id, p_application_name
    );

    -- Se è un login riuscito, aggiorna l'ultimo accesso E imposta il contesto di sessione
    IF p_azione = 'login' AND p_esito = TRUE THEN
        UPDATE catasto.utente SET ultimo_accesso = CURRENT_TIMESTAMP
        WHERE id = p_utente_id;

        -- Imposta il contesto di sessione NEL DATABASE
        PERFORM catasto.imposta_utente_sessione(p_utente_id, v_generated_session_id, p_indirizzo_ip);
    END IF;
END;
$$;

-- Procedura per eseguire il logout di un utente e aggiornare lo stato di sessione
CREATE OR REPLACE PROCEDURE logout_utente(
    p_utente_id INTEGER,
    p_session_id VARCHAR(100), -- Session ID da terminare
    p_indirizzo_ip VARCHAR(40) DEFAULT NULL -- Opzionale, IP al momento del logout
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Registra il logout nell'accesso_log
    CALL catasto.registra_accesso(
        p_utente_id, 'logout', p_indirizzo_ip, NULL,
        TRUE, p_session_id, 'CatastoApp' -- Usa lo stesso session_id del login
    );

    -- Rimuovi le variabili di sessione PostgreSQL associate a questa connessione
    -- L'applicazione chiamante dovrebbe gestire la terminazione della sessione applicativa
    -- Questi comandi resettano le variabili per la *connessione corrente* che chiama questa procedura.
    -- Se l'applicazione usa un pool di connessioni, questo reset potrebbe non essere sufficiente
    -- per altre connessioni dello stesso utente.
    PERFORM set_config('app.user_id', NULL, FALSE);
    PERFORM set_config('app.session_id', NULL, FALSE);
    PERFORM set_config('app.ip_address', NULL, FALSE);
    RAISE NOTICE 'Variabili di sessione resettate per la connessione corrente.';
END;
$$;


-- =========================================================================
-- FASE 5: Creazione/Aggiornamento viste e funzioni per reportistica
-- =========================================================================

-- Vista per visualizzare attività utente correlandole con audit
-- CORREZIONE: usa al.utente per l'utente DB
CREATE OR REPLACE VIEW v_attivita_utente AS
SELECT
    a.id AS accesso_id,
    a.utente_id,
    u.username,
    u.nome_completo,
    a.timestamp AS accesso_timestamp,
    a.azione,
    a.session_id,
    a.indirizzo_ip,
    a.user_agent,
    a.application_name,
    COUNT(al.id) AS operazioni_totali_sessione,
    STRING_AGG(DISTINCT al.tabella, ', ') AS tabelle_modificate_sessione,
    MIN(al.timestamp) FILTER (WHERE al.id IS NOT NULL) AS prima_operazione_sessione,
    MAX(al.timestamp) FILTER (WHERE al.id IS NOT NULL) AS ultima_operazione_sessione
FROM
    catasto.accesso_log a
JOIN
    catasto.utente u ON a.utente_id = u.id
LEFT JOIN
    catasto.audit_log al ON a.session_id = al.session_id -- Join basato su session_id
WHERE
    a.session_id IS NOT NULL -- Considera solo accessi con session_id
GROUP BY
    a.id, a.utente_id, u.username, u.nome_completo, a.timestamp,
    a.azione, a.session_id, a.indirizzo_ip, a.user_agent, a.application_name
ORDER BY a.timestamp DESC;

-- Funzione per generare report di attività utente
-- (Nessuna modifica necessaria se la vista v_attivita_utente è corretta)
CREATE OR REPLACE FUNCTION report_attivita_utente(
    p_user_id INTEGER DEFAULT NULL,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    username VARCHAR,
    nome_completo VARCHAR,
    login_timestamp TIMESTAMP,
    logout_timestamp TIMESTAMP,
    durata_sessione INTERVAL,
    operazioni_totali BIGINT,
    tabelle_modificate TEXT,
    ip_address VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    WITH login_events AS (
        SELECT
            a.utente_id,
            a.session_id,
            a.timestamp AS login_time,
            a.indirizzo_ip,
            u.username,
            u.nome_completo
        FROM
            catasto.accesso_log a
        JOIN
            catasto.utente u ON a.utente_id = u.id
        WHERE
            a.azione = 'login'
            AND a.esito = TRUE
            AND a.timestamp >= (CURRENT_TIMESTAMP - p_days * INTERVAL '1 day') -- Usa CURRENT_TIMESTAMP
            AND (p_user_id IS NULL OR a.utente_id = p_user_id)
    ),
    logout_events AS (
        SELECT
            session_id,
            MAX(timestamp) AS logout_time -- Prende l'ultimo logout per quella sessione
        FROM
            catasto.accesso_log
        WHERE
            azione = 'logout'
        GROUP BY session_id
    ),
    operation_counts AS (
        SELECT
            session_id,
            COUNT(id) AS operations,
            STRING_AGG(DISTINCT tabella, ', ') AS tables_modified
        FROM
            catasto.audit_log
        WHERE
            session_id IS NOT NULL
        GROUP BY
            session_id
    )
    SELECT
        l.username,
        l.nome_completo,
        l.login_time AS login_timestamp,
        lo.logout_time AS logout_timestamp,
        COALESCE(lo.logout_time - l.login_time, '0 seconds'::INTERVAL) AS durata_sessione,
        COALESCE(op.operations, 0) AS operazioni_totali,
        COALESCE(op.tables_modified, '') AS tabelle_modificate,
        l.indirizzo_ip AS ip_address
    FROM
        login_events l
    LEFT JOIN
        logout_events lo ON l.session_id = lo.session_id
    LEFT JOIN
        operation_counts op ON l.session_id = op.session_id
    ORDER BY
        l.login_time DESC;
END;
$$ LANGUAGE plpgsql;

-- Vista dettagliata delle operazioni di audit
-- CORREZIONE: Seleziona al.utente (che contiene l'utente DB) e usa l'alias db_user
CREATE OR REPLACE VIEW v_audit_dettagliato AS
SELECT
    al.id AS audit_id,
    al.timestamp,
    al.tabella,
    al.operazione,
    al.record_id,
    al.utente AS db_user, -- Corretto: usa la colonna 'utente' dalla tabella audit_log
    u.username AS app_username,
    u.nome_completo AS app_user_nome_completo,
    al.session_id,
    al.ip_address,
    a.timestamp AS login_time,
    a.application_name
FROM
    catasto.audit_log al
LEFT JOIN
    catasto.utente u ON al.app_user_id = u.id -- Join con utente applicazione
LEFT JOIN
    catasto.accesso_log a ON al.session_id = a.session_id AND a.azione = 'login' -- Trova il login associato
ORDER BY
    al.timestamp DESC;

-- =========================================================================
-- FASE 6: Migrazione dati esistenti (opzionale)
-- =========================================================================

-- Questa sezione aggiorna i record di audit esistenti che potrebbero
-- non avere app_user_id o session_id impostati.
DO $$
DECLARE
    v_admin_id INTEGER;
    v_default_session_id VARCHAR := 'MIGRATED-' || genera_session_id();
    v_update_count INTEGER := 0;
BEGIN
    -- Verifica se ci sono record di audit esistenti senza app_user_id
    IF EXISTS (SELECT 1 FROM catasto.audit_log WHERE app_user_id IS NULL LIMIT 1) THEN
        -- Ottieni l'ID dell'utente 'admin' o il primo utente disponibile come fallback
        SELECT id INTO v_admin_id FROM catasto.utente WHERE username = 'admin' LIMIT 1;
        IF v_admin_id IS NULL THEN
            RAISE NOTICE 'Utente admin non trovato, utilizzo primo utente disponibile come fallback.';
            SELECT id INTO v_admin_id FROM catasto.utente ORDER BY id LIMIT 1;
        END IF;

        IF v_admin_id IS NOT NULL THEN
            RAISE NOTICE 'Migrazione record audit esistenti: app_user_id impostato a % e session_id a %', v_admin_id, v_default_session_id;
            -- Aggiorna i record esistenti
            UPDATE catasto.audit_log
            SET app_user_id = COALESCE(app_user_id, v_admin_id),
                session_id = COALESCE(session_id, v_default_session_id)
            WHERE app_user_id IS NULL OR session_id IS NULL;

            GET DIAGNOSTICS v_update_count = ROW_COUNT;
            RAISE NOTICE 'Aggiornati % record di audit esistenti.', v_update_count;
        ELSE
            RAISE WARNING 'Nessun utente trovato nel sistema, impossibile migrare i dati di audit esistenti.';
        END IF;
    ELSE
        RAISE NOTICE 'Nessun record di audit esistente da migrare (app_user_id già popolato).';
    END IF;
END;
$$;

-- =========================================================================
-- FASE 7: Test del sistema aggiornato
-- =========================================================================

DO $$
BEGIN
    -- Verifica funzioni base
    PERFORM catasto.genera_session_id();
    RAISE NOTICE 'Funzione genera_session_id verificata.';
    PERFORM catasto.get_sessione_info();
    RAISE NOTICE 'Funzione get_sessione_info verificata.';

    -- Verifica viste
    PERFORM 1 FROM information_schema.views WHERE table_schema = 'catasto' AND table_name = 'v_attivita_utente' LIMIT 1;
    RAISE NOTICE 'Vista v_attivita_utente verificata.';
    PERFORM 1 FROM information_schema.views WHERE table_schema = 'catasto' AND table_name = 'v_audit_dettagliato' LIMIT 1;
    RAISE NOTICE 'Vista v_audit_dettagliato verificata.';

    -- Verifica funzione di report (senza eseguire effettivamente)
    PERFORM * FROM catasto.report_attivita_utente(NULL, 1) LIMIT 0;
    RAISE NOTICE 'Funzione report_attivita_utente verificata.';

    RAISE NOTICE 'Verifiche delle nuove definizioni completate!';
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante il test del sistema aggiornato: %', SQLERRM;
END;
$$;

-- =========================================================================
-- COMPLETAMENTO
-- =========================================================================
COMMIT;

-- Messaggi finali racchiusi in un blocco DO
DO $$
BEGIN
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Integrazione sistema di audit con sistema utenti completata!';
    RAISE NOTICE '============================================================';
END $$;