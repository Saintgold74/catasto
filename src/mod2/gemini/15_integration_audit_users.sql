-- Filename: 15_integration_audit_users.sql
-- =========================================================================
-- Integrazione sistema di audit con sistema utenti
-- Versione: 1.0
-- Data: 24/04/2025
-- =========================================================================

-- Imposta lo schema
SET search_path TO catasto;

-- =========================================================================
-- FASE 1: Modifica delle tabelle esistenti
-- =========================================================================

-- Aggiungi colonne per collegare audit_log con il sistema utenti
ALTER TABLE audit_log 
ADD COLUMN session_id VARCHAR(100),
ADD COLUMN app_user_id INTEGER;

-- Aggiungiamo un vincolo di chiave esterna posticipato per evitare problemi
-- con i dati esistenti
ALTER TABLE audit_log
ADD CONSTRAINT fk_audit_user 
  FOREIGN KEY (app_user_id) REFERENCES utente(id) 
  DEFERRABLE INITIALLY DEFERRED;

-- Aggiunta colonne alla tabella accesso_log
ALTER TABLE accesso_log 
ADD COLUMN session_id VARCHAR(100),
ADD COLUMN application_name VARCHAR(100);

-- =========================================================================
-- FASE 2: Funzioni di supporto
-- =========================================================================

-- Funzione per generare un session_id univoco
CREATE OR REPLACE FUNCTION genera_session_id() RETURNS VARCHAR AS $$
BEGIN
    RETURN md5(random()::text || clock_timestamp()::text);
END;
$$ LANGUAGE plpgsql;

-- Funzione per impostare le variabili di sessione
CREATE OR REPLACE FUNCTION imposta_utente_sessione(
    p_user_id INTEGER, 
    p_session_id VARCHAR, 
    p_ip_address VARCHAR
) RETURNS VOID AS $$
BEGIN
    -- Impostazione delle variabili di sessione (questi valori durano per la connessione corrente)
    PERFORM set_config('app.user_id', p_user_id::text, FALSE);
    PERFORM set_config('app.session_id', p_session_id, FALSE);
    PERFORM set_config('app.ip_address', p_ip_address, FALSE);
END;
$$ LANGUAGE plpgsql;

-- Funzione per ottenere informazioni sulla sessione corrente
CREATE OR REPLACE FUNCTION get_sessione_info()
RETURNS TABLE (
    app_user_id INTEGER,
    session_id VARCHAR,
    ip_address VARCHAR,
    is_active BOOLEAN
) AS $$
DECLARE
    v_app_user_id TEXT;
    v_session_id TEXT;
    v_ip_address TEXT;
BEGIN
    -- Prova a recuperare le variabili di sessione
    BEGIN
        v_app_user_id := current_setting('app.user_id', TRUE);
        v_session_id := current_setting('app.session_id', TRUE);
        v_ip_address := current_setting('app.ip_address', TRUE);
        
        app_user_id := v_app_user_id::INTEGER;
        session_id := v_session_id;
        ip_address := v_ip_address;
        is_active := v_app_user_id IS NOT NULL AND v_session_id IS NOT NULL;
        
        RETURN NEXT;
    EXCEPTION WHEN OTHERS THEN
        app_user_id := NULL;
        session_id := NULL;
        ip_address := NULL;
        is_active := FALSE;
        
        RETURN NEXT;
    END;
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
BEGIN
    -- Ottieni l'utente di database corrente
    v_db_user := CURRENT_USER;
    
    -- Tenta di recuperare le variabili di sessione
    -- TRUE come secondo parametro significa "restituisci NULL se non trovato"
    BEGIN
        v_app_user_id := NULLIF(current_setting('app.user_id', TRUE), '')::INTEGER;
        v_session_id := current_setting('app.session_id', TRUE);
        v_ip_address := current_setting('app.ip_address', TRUE);
    EXCEPTION WHEN OTHERS THEN
        -- In caso di errore, usa valori di default
        v_app_user_id := NULL;
        v_session_id := NULL;
        v_ip_address := NULL;
    END;
    
    -- Determina l'operazione (INSERT, UPDATE, DELETE)
    IF TG_OP = 'INSERT' THEN
        v_old_data := NULL;
        v_new_data := to_jsonb(NEW);
        INSERT INTO audit_log (
            tabella, operazione, record_id, dati_prima, dati_dopo, 
            utente, app_user_id, session_id, ip_address
        )
        VALUES (
            TG_TABLE_NAME, 'I', NEW.id, v_old_data, v_new_data, 
            v_db_user, v_app_user_id, v_session_id, v_ip_address
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        INSERT INTO audit_log (
            tabella, operazione, record_id, dati_prima, dati_dopo, 
            utente, app_user_id, session_id, ip_address
        )
        VALUES (
            TG_TABLE_NAME, 'U', NEW.id, v_old_data, v_new_data,
            v_db_user, v_app_user_id, v_session_id, v_ip_address
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        v_old_data := to_jsonb(OLD);
        v_new_data := NULL;
        INSERT INTO audit_log (
            tabella, operazione, record_id, dati_prima, dati_dopo, 
            utente, app_user_id, session_id, ip_address
        )
        VALUES (
            TG_TABLE_NAME, 'D', OLD.id, v_old_data, v_new_data,
            v_db_user, v_app_user_id, v_session_id, v_ip_address
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- =========================================================================
-- FASE 4: Aggiornamento procedure per registrazione accessi
-- =========================================================================

-- Aggiornamento della procedura di registrazione accesso per supportare session_id
CREATE OR REPLACE PROCEDURE registra_accesso(
    p_utente_id INTEGER,
    p_azione VARCHAR(50),
    p_indirizzo_ip VARCHAR(40) DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL,
    p_esito BOOLEAN DEFAULT TRUE,
    p_session_id VARCHAR(100) DEFAULT NULL,
    p_application_name VARCHAR(100) DEFAULT 'CatastoApp'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_session_id VARCHAR(100);
BEGIN
    -- Se non è fornito un session_id, ne generiamo uno
    IF p_session_id IS NULL THEN
        SELECT genera_session_id() INTO v_session_id;
    ELSE
        v_session_id := p_session_id;
    END IF;
    
    -- Registra l'accesso con il session_id
    INSERT INTO accesso_log (
        utente_id, timestamp, azione, 
        indirizzo_ip, user_agent, esito, 
        session_id, application_name
    )
    VALUES (
        p_utente_id, CURRENT_TIMESTAMP, p_azione, 
        p_indirizzo_ip, p_user_agent, p_esito, 
        v_session_id, p_application_name
    );
    
    -- Se è un login riuscito, aggiorna l'ultimo accesso e imposta il contesto di sessione
    IF p_azione = 'login' AND p_esito = TRUE THEN
        UPDATE utente SET ultimo_accesso = CURRENT_TIMESTAMP
        WHERE id = p_utente_id;
        
        -- Imposta il contesto di sessione
        PERFORM imposta_utente_sessione(p_utente_id, v_session_id, p_indirizzo_ip);
    END IF;
END;
$$;

-- Procedura per eseguire il logout di un utente e aggiornare lo stato di sessione
CREATE OR REPLACE PROCEDURE logout_utente(
    p_utente_id INTEGER,
    p_session_id VARCHAR(100),
    p_indirizzo_ip VARCHAR(40) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Registra il logout nell'audit log
    CALL registra_accesso(
        p_utente_id, 'logout', p_indirizzo_ip, NULL, 
        TRUE, p_session_id, 'CatastoApp'
    );
    
    -- Rimuovi le variabili di sessione
    -- In PostgreSQL, set_config con NULL cancella la variabile
    PERFORM set_config('app.user_id', NULL, FALSE);
    PERFORM set_config('app.session_id', NULL, FALSE);
    PERFORM set_config('app.ip_address', NULL, FALSE);
END;
$$;

-- =========================================================================
-- FASE 5: Creazione viste e funzioni per reportistica
-- =========================================================================

-- Creazione vista per visualizzare attività utente correlandole con audit
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
    COUNT(al.id) AS operazioni_totali,
    STRING_AGG(DISTINCT al.tabella, ', ') AS tabelle_modificate,
    MIN(al.timestamp) AS prima_operazione,
    MAX(al.timestamp) AS ultima_operazione
FROM 
    accesso_log a
JOIN 
    utente u ON a.utente_id = u.id
LEFT JOIN 
    audit_log al ON a.session_id = al.session_id
WHERE 
    a.session_id IS NOT NULL
GROUP BY 
    a.id, a.utente_id, u.username, u.nome_completo, a.timestamp, 
    a.azione, a.session_id, a.indirizzo_ip, a.user_agent, a.application_name;

-- Funzione per generare report di attività utente
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
            accesso_log a
        JOIN 
            utente u ON a.utente_id = u.id
        WHERE 
            a.azione = 'login' 
            AND a.esito = TRUE
            AND a.timestamp >= (CURRENT_DATE - p_days * INTERVAL '1 day')
            AND (p_user_id IS NULL OR a.utente_id = p_user_id)
    ),
    logout_events AS (
        SELECT 
            session_id,
            timestamp AS logout_time
        FROM 
            accesso_log
        WHERE 
            azione = 'logout'
    ),
    operation_counts AS (
        SELECT 
            session_id,
            COUNT(id) AS operations,
            STRING_AGG(DISTINCT tabella, ', ') AS tables_modified
        FROM 
            audit_log
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
        COALESCE(lo.logout_time - l.login_time, INTERVAL '0') AS durata_sessione,
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
CREATE OR REPLACE VIEW v_audit_dettagliato AS
SELECT 
    al.id AS audit_id,
    al.timestamp,
    al.tabella,
    al.operazione,
    al.record_id,
    al.utente AS db_user,
    u.username,
    u.nome_completo,
    al.session_id,
    al.ip_address,
    a.timestamp AS login_time,
    a.application_name
FROM 
    audit_log al
LEFT JOIN 
    utente u ON al.app_user_id = u.id
LEFT JOIN 
    accesso_log a ON al.session_id = a.session_id AND a.azione = 'login'
ORDER BY 
    al.timestamp DESC;

-- =========================================================================
-- FASE 6: Migrazione dati esistenti (opzionale)
-- =========================================================================

-- Questa sezione è opzionale e può essere eseguita per aggiornare
-- i record di audit esistenti con informazioni utente fittizie
DO $$
DECLARE
    v_admin_id INTEGER;
    v_session_id VARCHAR;
BEGIN
    -- Verifica se ci sono record di audit esistenti senza app_user_id
    IF (SELECT COUNT(*) FROM audit_log WHERE app_user_id IS NULL) > 0 THEN
        -- Ottieni l'ID dell'utente admin (assumiamo che esista)
        SELECT id INTO v_admin_id FROM utente WHERE username = 'admin' LIMIT 1;
        
        IF v_admin_id IS NULL THEN
            RAISE NOTICE 'Utente admin non trovato, utilizzo primo utente disponibile';
            SELECT id INTO v_admin_id FROM utente LIMIT 1;
        END IF;
        
        IF v_admin_id IS NOT NULL THEN
            -- Genera un session_id fittizio per i record esistenti
            SELECT genera_session_id() INTO v_session_id;
            
            -- Aggiorna i record esistenti
            UPDATE audit_log 
            SET app_user_id = v_admin_id, 
                session_id = v_session_id
            WHERE app_user_id IS NULL;
            
            RAISE NOTICE 'Aggiornati % record di audit esistenti', 
                         (SELECT COUNT(*) FROM audit_log WHERE session_id = v_session_id);
        ELSE
            RAISE NOTICE 'Nessun utente trovato nel sistema, impossibile migrare i dati esistenti';
        END IF;
    ELSE
        RAISE NOTICE 'Nessun record di audit esistente da migrare';
    END IF;
END;
$$;

-- =========================================================================
-- FASE 7: Test del sistema aggiornato
-- =========================================================================

-- Verifica che le nuove funzioni siano state create correttamente
DO $$
BEGIN
    -- Verifica le funzioni
    PERFORM genera_session_id();
    RAISE NOTICE 'Funzione genera_session_id verificata.';
    
    -- Verifica che la vista esista
    PERFORM 1 FROM information_schema.views 
    WHERE table_schema = 'catasto' AND table_name = 'v_attivita_utente';
    RAISE NOTICE 'Vista v_attivita_utente verificata.';
    
    -- Verifica che la vista esista
    PERFORM 1 FROM information_schema.views 
    WHERE table_schema = 'catasto' AND table_name = 'v_audit_dettagliato';
    RAISE NOTICE 'Vista v_audit_dettagliato verificata.';
    
    -- Verifica la funzione di report
    PERFORM * FROM report_attivita_utente(NULL, 30) LIMIT 0;
    RAISE NOTICE 'Funzione report_attivita_utente verificata.';
    
    RAISE NOTICE 'Tutte le verifiche completate con successo!';
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante il test del sistema aggiornato: %', SQLERRM;
END;
$$;

-- =========================================================================
-- COMPLETAMENTO
-- =========================================================================
COMMIT;
RAISE NOTICE '============================================================';
RAISE NOTICE 'Integrazione sistema di audit con sistema utenti completata!';
RAISE NOTICE '============================================================';