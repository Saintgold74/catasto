-- Imposta lo schema
SET search_path TO catasto;

-- Tabella per gli utenti
CREATE TABLE utente (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Hash della password (NON salvare password in chiaro!)
    nome_completo VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    ruolo VARCHAR(20) NOT NULL CHECK (ruolo IN ('admin', 'archivista', 'consultatore')),
    attivo BOOLEAN DEFAULT TRUE,
    ultimo_accesso TIMESTAMP,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_utente_username ON utente(username);
CREATE INDEX idx_utente_ruolo ON utente(ruolo);

-- Tabella per il log degli accessi
CREATE TABLE accesso_log (
    id SERIAL PRIMARY KEY,
    utente_id INTEGER REFERENCES utente(id) ON DELETE SET NULL, -- <<< MODIFICA QUI
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    azione VARCHAR(50) NOT NULL,
    indirizzo_ip VARCHAR(40),
    user_agent TEXT,
    esito BOOLEAN,
    session_id VARCHAR(100) NULL,
    application_name VARCHAR(100) NULL
);

COMMENT ON COLUMN accesso_log.session_id IS 'ID univoco della sessione utente, se applicabile.';
COMMENT ON COLUMN accesso_log.application_name IS 'Nome dell''applicazione client che ha generato l''accesso (es. CatastoApp, WebApp).';

CREATE INDEX idx_accesso_utente ON accesso_log(utente_id);
CREATE INDEX idx_accesso_timestamp ON accesso_log(timestamp);

-- Tabella per i permessi
CREATE TABLE permesso (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) UNIQUE NOT NULL,
    descrizione TEXT
);

-- Tabella di collegamento tra utenti e permessi
CREATE TABLE utente_permesso (
    utente_id INTEGER REFERENCES utente(id) ON DELETE CASCADE,
    permesso_id INTEGER REFERENCES permesso(id) ON DELETE CASCADE,
    data_assegnazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (utente_id, permesso_id)
);

-- Funzione per verificare se un utente ha un determinato permesso
CREATE OR REPLACE FUNCTION ha_permesso(p_utente_id INTEGER, p_permesso_nome VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    v_ruolo VARCHAR(20);
    v_permesso_count INTEGER;
BEGIN
    -- Verifica se l'utente è attivo
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
$$ LANGUAGE plpgsql;

-- Procedura per creare un nuovo utente (con password hash)
CREATE OR REPLACE PROCEDURE crea_utente(
    p_username VARCHAR(50),
    p_password VARCHAR(255), -- Questa dovrebbe essere già hashata nell'applicazione
    p_nome_completo VARCHAR(100),
    p_email VARCHAR(100),
    p_ruolo VARCHAR(20)
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO utente (username, password_hash, nome_completo, email, ruolo)
    VALUES (p_username, p_password, p_nome_completo, p_email, p_ruolo);
END;
$$;

-- Procedura per aggiornare l'ultimo accesso di un utente
CREATE OR REPLACE PROCEDURE registra_accesso(
    p_utente_id INTEGER,
    p_azione VARCHAR(50),
    p_indirizzo_ip VARCHAR(40),
    p_user_agent TEXT,
    p_esito BOOLEAN,
	p_session_id VARCHAR(100),       -- NUOVO
    p_application_name VARCHAR(100)  -- NUOVO
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Registra l'accesso
    INSERT INTO accesso_log (utente_id, azione, indirizzo_ip, user_agent, esito)
    VALUES (p_utente_id, p_azione, p_indirizzo_ip, p_user_agent, p_esito);

    -- Se è un login riuscito, aggiorna l'ultimo accesso
    IF p_azione = 'login' AND p_esito = TRUE THEN
        UPDATE utente SET ultimo_accesso = CURRENT_TIMESTAMP
        WHERE id = p_utente_id;
    END IF;
END;
$$;

-- Inserire in 07_user-management.sql o 15_integration_audit_users.sql
-- Assicurarsi che lo schema sia corretto (SET search_path TO catasto, public;)

CREATE OR REPLACE PROCEDURE catasto.logout_utente(
    p_utente_id INTEGER,
    p_session_id VARCHAR(100),
    p_client_ip VARCHAR(40) DEFAULT NULL -- Opzionale, ma utile per il log
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_application_name VARCHAR(100);
BEGIN
    -- Potrebbe voler recuperare il nome dell'applicazione dal contesto di sessione se impostato,
    -- o passarlo come parametro se necessario per accesso_log.
    -- Per semplicità, qui lo impostiamo a un valore generico o lo lasciamo NULL
    -- se la tabella accesso_log accetta NULL per application_name.
    -- Se la sua tabella accesso_log richiede application_name, dovrà gestirlo.
    
    -- Tentativo di recuperare application_name se impostato in sessione (opzionale)
    BEGIN
        v_application_name := current_setting('app.application_name', true);
    EXCEPTION
        WHEN undefined_object THEN -- 'app.application_name' non è impostato
            v_application_name := 'CatastoApp-Logout'; -- Valore di default o NULL
    END;

    -- Registra l'evento di logout nella tabella accesso_log
    -- Assumiamo che la tabella accesso_log sia stata aggiornata per includere session_id e application_name
    INSERT INTO catasto.accesso_log (
        utente_id,
        azione,
        indirizzo_ip,
        session_id,
        application_name,
        esito,
        timestamp -- o lasciare il default se la colonna ha DEFAULT CURRENT_TIMESTAMP
    )
    VALUES (
        p_utente_id,
        'logout',
        p_client_ip,
        p_session_id,
        v_application_name, -- o un valore fisso/NULL se non gestito
        TRUE,               -- Logout si assume sempre riuscito a questo punto
        CURRENT_TIMESTAMP
    );

    RAISE NOTICE 'Logout registrato per utente ID % (Sessione: %, IP: %)', p_utente_id, p_session_id, p_client_ip;

EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING '[logout_utente] Errore durante la registrazione del logout per utente ID %: % - SQLSTATE: %', p_utente_id, SQLERRM, SQLSTATE;
        -- Non sollevare EXCEPTION qui per permettere al codice Python di procedere con la disconnessione,
        -- ma loggare l'avviso è importante.
END;
$$;

-- Inserimento permessi base
INSERT INTO permesso (nome, descrizione) VALUES
('visualizza_partite', 'Permesso di visualizzare le partite catastali'),
('modifica_partite', 'Permesso di modificare le partite catastali'),
('visualizza_possessori', 'Permesso di visualizzare i possessori'),
('modifica_possessori', 'Permesso di modificare i possessori'),
('visualizza_immobili', 'Permesso di visualizzare gli immobili'),
('modifica_immobili', 'Permesso di modificare gli immobili'),
('registra_variazioni', 'Permesso di registrare variazioni di proprietà'),
('gestione_utenti', 'Permesso di gestire gli utenti');

-- Utente amministratore di default (password: admin123 - in produzione usare un hash sicuro!)
DO $$
DECLARE
    admin_username TEXT := 'admin';
    admin_email TEXT := 'admin@archivio.savona.it';
    -- METTA QUI L'HASH BCRYPT VALIDO E GENERATO DA LEI
    admin_password_hash TEXT := '$2b$12$r0aa.7569LtbyofetxSRtOWZzWAQDbD9XTC1SQ4bHVXDURlQwXszy'; 
    user_exists BOOLEAN;
BEGIN
    SET LOCAL search_path TO catasto, public;
    SELECT EXISTS(SELECT 1 FROM utente WHERE username = admin_username) INTO user_exists;
    IF NOT user_exists THEN
        INSERT INTO utente (username, password_hash, nome_completo, email, ruolo, attivo)
        VALUES (admin_username, admin_password_hash, 'Amministratore Sistema', admin_email, 'admin', TRUE);
        RAISE NOTICE 'Utente amministratore di default "%" creato (da 07_user-management.sql).', admin_username;
    ELSE
        RAISE NOTICE 'Utente amministratore di default "%" già esistente (controllato da 07_user-management.sql).', admin_username;
    END IF;
END $$;

-- Applicazione del trigger per l'aggiornamento del timestamp di modifica
CREATE TRIGGER update_utente_modifica
BEFORE UPDATE ON utente
FOR EACH ROW EXECUTE FUNCTION update_modified_column();