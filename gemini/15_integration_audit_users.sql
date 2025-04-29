-- Filename: 15_integration_audit_users.sql
-- =========================================================================
-- Integrazione sistema di audit con sistema utenti (MODIFICATO)
-- Versione: 1.2 (Rimosso CREATE TABLE audit_log, aggiunto controllo FK)
-- Data: 29/04/2025
-- ASSUNZIONE: La tabella 'audit_log' è stata creata alla fine dello script 02.
-- =========================================================================

-- Imposta lo schema
SET search_path TO catasto, public; -- Assicurati che public sia incluso per le estensioni

-- =========================================================================
-- FASE 1: Modifica della tabella audit_log esistente
-- (La tabella è stata creata in script 02)
-- =========================================================================

-- Aggiungi colonne per collegare audit_log con il sistema utenti
-- Aggiungi colonne solo se non esistono già per rendere lo script rieseguibile
DO $$
BEGIN
   --RAISE NOTICE 'FASE 1: Modifica tabella audit_log (aggiunta colonne session/user)...';
    -- Verifica se la colonna session_id esiste già
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'catasto' AND table_name = 'audit_log' AND column_name = 'session_id') THEN
        ALTER TABLE catasto.audit_log ADD COLUMN session_id VARCHAR(100);
        RAISE NOTICE '  -> Colonna session_id aggiunta a audit_log.';
    ELSE
        RAISE NOTICE '  -> Colonna session_id già presente in audit_log.';
    END IF;

    -- Verifica se la colonna app_user_id esiste già
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'catasto' AND table_name = 'audit_log' AND column_name = 'app_user_id') THEN
        ALTER TABLE catasto.audit_log ADD COLUMN app_user_id INTEGER;
        RAISE NOTICE '  -> Colonna app_user_id aggiunta a audit_log.';
    ELSE
        RAISE NOTICE '  -> Colonna app_user_id già presente in audit_log.';
    END IF;
    RAISE NOTICE 'FASE 1: Modifica tabella audit_log completata.';
END $$;

-- Aggiungiamo un vincolo di chiave esterna (FOREIGN KEY) posticipato
-- Aggiungi vincolo solo se non esiste già
DO $$
BEGIN
    --RAISE NOTICE 'FASE 1.1: Aggiunta Foreign Key fk_audit_user a audit_log...';
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_audit_user' AND conrelid = 'catasto.audit_log'::regclass) THEN
        -- Verifica che la tabella utente esista prima di aggiungere il vincolo
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'catasto' AND table_name = 'utente') THEN
            ALTER TABLE catasto.audit_log
            ADD CONSTRAINT fk_audit_user
              FOREIGN KEY (app_user_id) REFERENCES catasto.utente(id)
              ON DELETE SET NULL -- O RESTRICT se preferisci impedire cancellazione utente con log
              ON UPDATE CASCADE
              DEFERRABLE INITIALLY DEFERRED; -- Utile se si inseriscono log prima dell'utente in transazioni complesse
            RAISE NOTICE '  -> Foreign Key fk_audit_user aggiunta.';
        ELSE
            RAISE WARNING '  -> Tabella utente non trovata, impossibile aggiungere Foreign Key fk_audit_user.';
        END IF;
    ELSE
        RAISE NOTICE '  -> Foreign Key fk_audit_user già presente.';
    END IF;
    RAISE NOTICE 'FASE 1.1: Controllo/Aggiunta Foreign Key completato.';
END $$;


-- Aggiunta colonne alla tabella accesso_log (se non già presenti)
DO $$
BEGIN
    --RAISE NOTICE 'FASE 1.2: Modifica tabella accesso_log (aggiunta colonne session/app)...';
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'catasto' AND table_name = 'accesso_log' AND column_name = 'session_id') THEN
        ALTER TABLE catasto.accesso_log ADD COLUMN session_id VARCHAR(100);
         RAISE NOTICE '  -> Colonna session_id aggiunta a accesso_log.';
    ELSE
        RAISE NOTICE '  -> Colonna session_id già presente in accesso_log.';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'catasto' AND table_name = 'accesso_log' AND column_name = 'application_name') THEN
        ALTER TABLE catasto.accesso_log ADD COLUMN application_name VARCHAR(100);
        RAISE NOTICE '  -> Colonna application_name aggiunta a accesso_log.';
    ELSE
        RAISE NOTICE '  -> Colonna application_name già presente in accesso_log.';
    END IF;
    RAISE NOTICE 'FASE 1.2: Modifica tabella accesso_log completata.';
END $$;


-- =========================================================================
-- FASE 2: Funzioni di supporto (UUID, Sessione)
-- =========================================================================
--RAISE NOTICE 'FASE 2: Creazione/Aggiornamento funzioni di supporto...';

-- Funzione per generare un session_id univoco
CREATE OR REPLACE FUNCTION genera_session_id() RETURNS VARCHAR AS $$
DECLARE
  v_uuid_ext_exists BOOLEAN;
BEGIN
  SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp') INTO v_uuid_ext_exists;
  IF v_uuid_ext_exists THEN
    RETURN uuid_generate_v4()::VARCHAR;
  ELSE
    RETURN md5(random()::text || clock_timestamp()::text);
  END IF;
END;
$$ LANGUAGE plpgsql VOLATILE;

-- Funzione per impostare le variabili di sessione
CREATE OR REPLACE FUNCTION imposta_utente_sessione(
    p_user_id INTEGER,
    p_session_id VARCHAR,
    p_ip_address VARCHAR
) RETURNS VOID AS $$
BEGIN
    PERFORM set_config('app.user_id', p_user_id::text, FALSE);
    PERFORM set_config('app.session_id', p_session_id, FALSE);
    PERFORM set_config('app.ip_address', COALESCE(p_ip_address, ''), FALSE); -- Usa stringa vuota se IP è NULL
    -- Rimosso RAISE NOTICE per ridurre verbosità
END;
$$ LANGUAGE plpgsql;

-- Funzione per ottenere informazioni sulla sessione corrente
CREATE OR REPLACE FUNCTION get_sessione_info()
RETURNS TABLE (app_user_id INTEGER, session_id VARCHAR, ip_address VARCHAR, db_user_name TEXT, is_active BOOLEAN) AS $$
DECLARE
    v_app_user_id TEXT; v_session_id TEXT; v_ip_address TEXT;
BEGIN
    v_app_user_id := current_setting('app.user_id', TRUE);
    v_session_id := current_setting('app.session_id', TRUE);
    v_ip_address := current_setting('app.ip_address', TRUE);
    app_user_id := NULLIF(v_app_user_id, '')::INTEGER;
    get_sessione_info.session_id := v_session_id; -- Qualifica nome colonna output
    get_sessione_info.ip_address := v_ip_address;
    get_sessione_info.db_user_name := current_user;
    get_sessione_info.is_active := v_app_user_id IS NOT NULL AND v_session_id IS NOT NULL;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

--RAISE NOTICE 'FASE 2: Funzioni di supporto create/aggiornate.';

-- =========================================================================
-- FASE 3: Aggiornamento funzione trigger di audit (Versione Corretta)
-- =========================================================================
--RAISE NOTICE 'FASE 3: Creazione/Aggiornamento funzione trigger audit...';

-- Aggiornamento della funzione di audit per usare contesto sessione e gestire PK 'comune'
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    v_old_data JSONB;
    v_new_data JSONB;
    v_db_user TEXT;
    v_app_user_id INTEGER;
    v_session_id TEXT;
    v_ip_address TEXT;
    v_record_id INTEGER := NULL; -- Default a NULL
    v_record_identifier TEXT := NULL; -- Identificatore alternativo per tabelle senza 'id' PK numerico
BEGIN
    -- Ottieni informazioni utente/sessione
    v_db_user := session_user;
    v_app_user_id := NULLIF(current_setting('app.user_id', TRUE), '')::INTEGER;
    v_session_id := current_setting('app.session_id', TRUE);
    v_ip_address := current_setting('app.ip_address', TRUE);

    -- Determina l'ID del record o un identificatore alternativo
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        BEGIN
            -- Prova a ottenere l'ID numerico (più comune)
            v_record_id := (to_jsonb(NEW)->>'id')::INTEGER;
        EXCEPTION
            WHEN OTHERS THEN -- Se 'id' non esiste o non è INTEGER
                IF TG_TABLE_NAME = 'comune' THEN
                    -- Per 'comune', usiamo 'nome' come identificatore testuale
                    -- Potremmo salvarlo in una colonna dedicata nell'audit_log se necessario
                    v_record_identifier := (to_jsonb(NEW)->>'nome');
                END IF;
                -- Lasciamo v_record_id a NULL
        END;
        v_new_data := to_jsonb(NEW);
    END IF;

    IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
        BEGIN
             -- Precedenza a NEW.id se esiste (per UPDATE), altrimenti prova OLD.id
            IF v_record_id IS NULL THEN
               v_record_id := (to_jsonb(OLD)->>'id')::INTEGER;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                IF TG_TABLE_NAME = 'comune' THEN
                    -- Precedenza a NEW.nome se esiste (per UPDATE), altrimenti OLD.nome
                     IF v_record_identifier IS NULL THEN
                        v_record_identifier := (to_jsonb(OLD)->>'nome');
                     END IF;
                 END IF;
                 -- Lasciamo v_record_id a NULL
        END;
        v_old_data := to_jsonb(OLD);
    END IF;

    -- Inserisci nel log (record_id sarà NULL per 'comune')
    BEGIN
        IF TG_OP = 'INSERT' THEN
            INSERT INTO catasto.audit_log (tabella, operazione, record_id, dati_prima, dati_dopo, utente, app_user_id, session_id, ip_address)
            VALUES (TG_TABLE_NAME, 'I', v_record_id, NULL, v_new_data, v_db_user, v_app_user_id, v_session_id, v_ip_address);
        ELSIF TG_OP = 'UPDATE' THEN
            IF v_old_data IS NOT DISTINCT FROM v_new_data THEN RETURN NEW; END IF; -- Salta se non ci sono modifiche
            INSERT INTO catasto.audit_log (tabella, operazione, record_id, dati_prima, dati_dopo, utente, app_user_id, session_id, ip_address)
            VALUES (TG_TABLE_NAME, 'U', v_record_id, v_old_data, v_new_data, v_db_user, v_app_user_id, v_session_id, v_ip_address);
        ELSIF TG_OP = 'DELETE' THEN
            INSERT INTO catasto.audit_log (tabella, operazione, record_id, dati_prima, dati_dopo, utente, app_user_id, session_id, ip_address)
            VALUES (TG_TABLE_NAME, 'D', v_record_id, v_old_data, NULL, v_db_user, v_app_user_id, v_session_id, v_ip_address);
        END IF;
    EXCEPTION
        WHEN OTHERS THEN
            -- Logga un errore se l'inserimento nell'audit fallisce, ma non bloccare l'operazione originale
            RAISE WARNING '[AUDIT TRIGGER] Impossibile registrare log per % su %.%: %', TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME, SQLERRM;
    END;

    -- Ritorna il record appropriato per l'operazione originale
    IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;

END;
$$ LANGUAGE plpgsql;

--RAISE NOTICE 'FASE 3: Funzione trigger audit creata/aggiornata.';

-- Applica il trigger aggiornato alle tabelle necessarie
DO $$
DECLARE
  tbl RECORD;
  trigger_name TEXT;
BEGIN
  RAISE NOTICE 'FASE 3.1: Applicazione trigger di audit...';
  FOR tbl IN SELECT table_name FROM information_schema.tables
             WHERE table_schema = 'catasto' AND table_type = 'BASE TABLE'
             AND table_name IN ('partita', 'possessore', 'immobile', 'variazione', 'contratto', 'consultazione', 'localita', 'comune') -- Elenco tabelle auditate
  LOOP
    trigger_name := 'audit_trigger_' || tbl.table_name;
    -- Controlla se il trigger esiste già prima di dropparlo
    IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = trigger_name AND tgrelid = ('catasto.' || quote_ident(tbl.table_name))::regclass) THEN
        EXECUTE format('DROP TRIGGER %I ON catasto.%I;', trigger_name, tbl.table_name);
        RAISE NOTICE '  -> Trigger % droppato da %.%', trigger_name, 'catasto', tbl.table_name;
    ELSE
        RAISE NOTICE '  -> Trigger % non esistente su %.%', trigger_name, 'catasto', tbl.table_name;
    END IF;
    -- Crea il trigger
    EXECUTE format('CREATE TRIGGER %I AFTER INSERT OR UPDATE OR DELETE ON catasto.%I FOR EACH ROW EXECUTE FUNCTION catasto.audit_trigger_function();', trigger_name, tbl.table_name);
    RAISE NOTICE '  -> Trigger % applicato a %.%', trigger_name, 'catasto', tbl.table_name;
  END LOOP;
  RAISE NOTICE 'FASE 3.1: Applicazione trigger completata.';
END $$;


-- =========================================================================
-- FASE 4: Aggiornamento procedure per registrazione accessi
-- =========================================================================
--RAISE NOTICE 'FASE 4: Creazione/Aggiornamento procedure registrazione accessi...';

-- Aggiornamento procedura registra_accesso
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
    v_final_session_id VARCHAR(100);
BEGIN
    v_final_session_id := COALESCE(p_session_id, genera_session_id());

    INSERT INTO catasto.accesso_log (utente_id, timestamp, azione, indirizzo_ip, user_agent, esito, session_id, application_name)
    VALUES (p_utente_id, CURRENT_TIMESTAMP, p_azione, p_indirizzo_ip, p_user_agent, p_esito, v_final_session_id, p_application_name);

    IF p_azione = 'login' AND p_esito = TRUE THEN
        UPDATE catasto.utente SET ultimo_accesso = CURRENT_TIMESTAMP WHERE id = p_utente_id;
        PERFORM catasto.imposta_utente_sessione(p_utente_id, v_final_session_id, p_indirizzo_ip);
    END IF;
END;
$$;

-- Procedura per logout utente
CREATE OR REPLACE PROCEDURE logout_utente(
    p_utente_id INTEGER,
    p_session_id VARCHAR(100),
    p_indirizzo_ip VARCHAR(40) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Registra logout
    CALL catasto.registra_accesso(p_utente_id, 'logout', p_indirizzo_ip, NULL, TRUE, p_session_id, 'CatastoApp');
    -- Resetta variabili di sessione DB per la connessione corrente
    PERFORM set_config('app.user_id', NULL, FALSE);
    PERFORM set_config('app.session_id', NULL, FALSE);
    PERFORM set_config('app.ip_address', NULL, FALSE);
    -- RAISE NOTICE 'Variabili sessione DB resettate.';