-- Imposta lo schema di default per questa sessione/script
SET search_path TO catasto, public;

-- 0. Rimuovi eventuali vecchi oggetti se stai ricreando da zero (opzionale, usare con cautela)
-- DROP TRIGGER IF EXISTS audit_trigger_variazione ON catasto.variazione;
-- DROP TRIGGER IF EXISTS audit_trigger_immobile ON catasto.immobile;
-- DROP TRIGGER IF EXISTS audit_trigger_possessore ON catasto.possessore;
-- DROP TRIGGER IF EXISTS audit_trigger_partita ON catasto.partita;
-- DROP FUNCTION IF EXISTS catasto.get_record_history(VARCHAR, INTEGER);
-- DROP FUNCTION IF EXISTS catasto.audit_trigger_function();
-- DROP TABLE IF EXISTS catasto.audit_log CASCADE;

-- 1. Tabella per i log di audit
-- Questa definizione corrisponde alla struttura che mi hai mostrato con \d
-- e a ciò che audit_service.py (rivisto) si aspetta.
CREATE TABLE IF NOT EXISTS catasto.audit_log (
    id SERIAL PRIMARY KEY,
    tabella VARCHAR(100) NOT NULL,
    operazione CHAR(1) NOT NULL, -- Il CHECK constraint verrà aggiunto dopo
    record_id INTEGER, -- Permette NULL (es. per operazioni non legate a un record specifico)
    dati_prima JSONB,
    dati_dopo JSONB,    -- Usato per i dettagli dell'azione da audit_service.py
    utente VARCHAR(100), -- Per lo username testuale (es. current_user da PostgreSQL)
    ip_address VARCHAR(45), -- Aumentato leggermente per IPv6 mappato
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100),
    app_user_id INTEGER -- Per l'ID numerico dell'utente dell'applicazione, permette NULL
);

-- Indici (alcuni potrebbero già esistere se la tabella esiste)
CREATE INDEX IF NOT EXISTS idx_audit_log_tabella_record_id ON catasto.audit_log(tabella, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON catasto.audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_app_user_id ON catasto.audit_log(app_user_id) WHERE app_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_log_operazione ON catasto.audit_log(operazione);


-- 2. CHECK constraint esteso per la colonna 'operazione'
-- Rimuovi il vecchio constraint se esiste e ha un nome noto (es. audit_log_operazione_check)
DO $$
BEGIN
   IF EXISTS (SELECT 1 FROM information_schema.constraint_table_usage where table_schema = 'catasto' and table_name = 'audit_log' and constraint_name = 'audit_log_operazione_check') THEN
      ALTER TABLE catasto.audit_log DROP CONSTRAINT audit_log_operazione_check;
   END IF;
END $$;

-- Aggiungi il nuovo CHECK constraint esteso
ALTER TABLE catasto.audit_log 
ADD CONSTRAINT audit_log_operazione_check 
CHECK (operazione = ANY (ARRAY['I', -- Insert (da trigger)
                               'U', -- Update (da trigger)
                               'D', -- Delete (da trigger)
                               'L', -- Login (da audit_service)
                               'O', -- Logout (da audit_service)
                               'F', -- Fail/Fallimento (da audit_service)
                               'S', -- Select/Search/View (da audit_service)
                               'R', -- Register (da audit_service)
                               'P', -- Password Change/Reset (da audit_service)
                               'X'  -- Altro/Non specificato (da audit_service)
                              ]::BPCHAR[]));

-- 3. Funzione trigger per l'audit (leggermente adattata)
CREATE OR REPLACE FUNCTION catasto.audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    v_old_data JSONB;
    v_new_data JSONB;
    v_db_user VARCHAR;      -- Utente del database (PostgreSQL user)
    v_app_user_id INTEGER;  -- ID utente dell'applicazione (da GUC)
    v_app_username VARCHAR; -- Username dell'applicazione (da GUC, opzionale)
    v_session_id_guc VARCHAR;
    v_ip_address_guc VARCHAR;
    v_operation_char CHAR(1);
BEGIN
    -- Tentativo di recuperare informazioni dalla sessione dell'applicazione
    BEGIN
        v_app_user_id := current_setting('myapp.current_user_id', true)::INTEGER;
    EXCEPTION WHEN OTHERS THEN
        v_app_user_id := NULL; 
    END;

    BEGIN
        v_app_username := current_setting('myapp.current_username', true); -- Username dell'app
    EXCEPTION WHEN OTHERS THEN
        v_app_username := NULL;
    END;
    
    BEGIN
        v_session_id_guc := current_setting('myapp.current_session_id', true);
    EXCEPTION WHEN OTHERS THEN
        v_session_id_guc := NULL;
    END;

    BEGIN
        v_ip_address_guc := inet_client_addr()::VARCHAR; -- IP della connessione DB
    EXCEPTION WHEN OTHERS THEN
        v_ip_address_guc := NULL;
    END;

    v_db_user := session_user; -- Utente della sessione DB

    IF TG_OP = 'INSERT' THEN
        v_operation_char := 'I';
        v_old_data := NULL;
        v_new_data := to_jsonb(NEW);
        -- Se NEW ha un campo 'id' (comune per PK), usalo come record_id
        IF jsonb_typeof(v_new_data->'id') IS NOT NULL THEN
            INSERT INTO catasto.audit_log (tabella, operazione, record_id, dati_prima, dati_dopo, utente, app_user_id, ip_address, session_id)
            VALUES (TG_TABLE_NAME, v_operation_char, (v_new_data->>'id')::INTEGER, v_old_data, v_new_data, COALESCE(v_app_username, v_db_user), v_app_user_id, v_ip_address_guc, v_session_id_guc);
        ELSE
             INSERT INTO catasto.audit_log (tabella, operazione, dati_prima, dati_dopo, utente, app_user_id, ip_address, session_id)
            VALUES (TG_TABLE_NAME, v_operation_char, v_old_data, v_new_data, COALESCE(v_app_username, v_db_user), v_app_user_id, v_ip_address_guc, v_session_id_guc);       
        END IF;
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        v_operation_char := 'U';
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        IF jsonb_typeof(v_new_data->'id') IS NOT NULL THEN
            INSERT INTO catasto.audit_log (tabella, operazione, record_id, dati_prima, dati_dopo, utente, app_user_id, ip_address, session_id)
            VALUES (TG_TABLE_NAME, v_operation_char, (NEW.id)::INTEGER, v_old_data, v_new_data, COALESCE(v_app_username, v_db_user), v_app_user_id, v_ip_address_guc, v_session_id_guc);
        ELSE
            INSERT INTO catasto.audit_log (tabella, operazione, dati_prima, dati_dopo, utente, app_user_id, ip_address, session_id)
            VALUES (TG_TABLE_NAME, v_operation_char, v_old_data, v_new_data, COALESCE(v_app_username, v_db_user), v_app_user_id, v_ip_address_guc, v_session_id_guc);
        END IF;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        v_operation_char := 'D';
        v_old_data := to_jsonb(OLD);
        v_new_data := NULL;
        IF jsonb_typeof(v_old_data->'id') IS NOT NULL THEN
            INSERT INTO catasto.audit_log (tabella, operazione, record_id, dati_prima, dati_dopo, utente, app_user_id, ip_address, session_id)
            VALUES (TG_TABLE_NAME, v_operation_char, (OLD.id)::INTEGER, v_old_data, v_new_data, COALESCE(v_app_username, v_db_user), v_app_user_id, v_ip_address_guc, v_session_id_guc);
        ELSE
            INSERT INTO catasto.audit_log (tabella, operazione, dati_prima, dati_dopo, utente, app_user_id, ip_address, session_id)
            VALUES (TG_TABLE_NAME, v_operation_char, v_old_data, v_new_data, COALESCE(v_app_username, v_db_user), v_app_user_id, v_ip_address_guc, v_session_id_guc);
        END IF;
        RETURN OLD;
    END IF;
    RETURN NULL; -- In caso di TG_OP non gestito (improbabile per AFTER IUD)
END;
$$ LANGUAGE plpgsql;

-- 4. Applica il trigger alle tabelle principali (o a quelle che vuoi auditare)
-- Assicurati che queste tabelle esistano nello schema 'catasto'
-- e che abbiano una colonna 'id' se il trigger la usa per 'record_id'.

CREATE TRIGGER audit_trigger_partita
AFTER INSERT OR UPDATE OR DELETE ON catasto.partita
FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();

CREATE TRIGGER audit_trigger_possessore
AFTER INSERT OR UPDATE OR DELETE ON catasto.possessore
FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();

CREATE TRIGGER audit_trigger_immobile
AFTER INSERT OR UPDATE OR DELETE ON catasto.immobile
FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();

CREATE TRIGGER audit_trigger_variazione
AFTER INSERT OR UPDATE OR DELETE ON catasto.variazione
FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();

-- Potresti voler aggiungere trigger anche ad altre tabelle, come 'utenti' stessa
-- CREATE TRIGGER audit_trigger_utenti
-- AFTER INSERT OR UPDATE OR DELETE ON catasto.utenti
-- FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();


-- 5. Funzione per consultare lo storico di un record (leggermente adattata)
CREATE OR REPLACE FUNCTION catasto.get_record_history(
    p_tabella VARCHAR, 
    p_record_id INTEGER
)
RETURNS TABLE (
    id_audit INTEGER,
    operazione_audit CHAR(1),
    timestamp_audit TIMESTAMP WITHOUT TIME ZONE,
    username_audit VARCHAR, -- Colonna 'utente' dalla tabella audit_log
    app_user_id_audit INTEGER, -- Colonna 'app_user_id' dalla tabella audit_log
    dati_prima_audit JSONB,
    dati_dopo_audit JSONB,
    ip_address_audit VARCHAR,
    session_id_audit VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.operazione, 
        a.timestamp, 
        a.utente, 
        a.app_user_id,
        a.dati_prima, 
        a.dati_dopo,
        a.ip_address,
        a.session_id
    FROM catasto.audit_log a
    WHERE a.tabella = p_tabella AND a.record_id = p_record_id
    ORDER BY a.timestamp DESC, a.id DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION catasto.get_record_history IS 'Restituisce lo storico delle modifiche per un dato record da audit_log.';
COMMENT ON TABLE catasto.audit_log IS 'Tabella di log per registrare le modifiche (INSERT, UPDATE, DELETE) alle tabelle auditate e azioni applicative.';

SELECT 'Script 06_audit-system.sql eseguito con successo.' AS stato_esecuzione;