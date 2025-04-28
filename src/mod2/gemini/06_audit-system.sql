-- Imposta lo schema
SET search_path TO catasto;

-- Tabella per i log di audit
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    tabella VARCHAR(100) NOT NULL,
    operazione CHAR(1) NOT NULL CHECK (operazione IN ('I', 'U', 'D')),
    record_id INTEGER NOT NULL,
    dati_prima JSONB,
    dati_dopo JSONB,
    utente VARCHAR(100) NOT NULL,
    ip_address VARCHAR(40),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_tabella ON audit_log(tabella);
CREATE INDEX idx_audit_operazione ON audit_log(operazione);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);

-- Funzioni trigger per l'audit
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
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
$$ LANGUAGE plpgsql;

-- Applica il trigger alle tabelle principali
CREATE TRIGGER audit_trigger_partita
AFTER INSERT OR UPDATE OR DELETE ON partita
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_trigger_possessore
AFTER INSERT OR UPDATE OR DELETE ON possessore
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_trigger_immobile
AFTER INSERT OR UPDATE OR DELETE ON immobile
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_trigger_variazione
AFTER INSERT OR UPDATE OR DELETE ON variazione
FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- Funzione per consultare lo storico di un record
CREATE OR REPLACE FUNCTION get_record_history(p_tabella VARCHAR, p_record_id INTEGER)
RETURNS TABLE (
    operazione CHAR(1),
    "timestamp" TIMESTAMP,
    utente VARCHAR,
    dati_prima JSONB,
    dati_dopo JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT a.operazione, a.timestamp, a.utente, a.dati_prima, a.dati_dopo
    FROM audit_log a
    WHERE a.tabella = p_tabella AND a.record_id = p_record_id
    ORDER BY a.timestamp DESC;
END;
$$ LANGUAGE plpgsql;