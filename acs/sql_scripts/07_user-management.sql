-- Imposta lo schema
SET search_path TO catasto;

-- Tabella per i ruoli degli utenti
CREATE TABLE catasto.ruoli_utente (
    id SERIAL PRIMARY KEY,
    nome_ruolo VARCHAR(50) UNIQUE NOT NULL,
    descrizione TEXT
);
INSERT INTO catasto.ruoli_utente (nome_ruolo, descrizione) VALUES 
('admin', 'Amministratore del sistema'),
('archivista', 'Archivista con permessi di modifica dati'),
('consultatore', 'Utente con permessi di sola lettura')
ON CONFLICT (nome_ruolo) DO NOTHING;

-- Tabella per gli utenti
CREATE TABLE utenti (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Hash della password (NON salvare password in chiaro!)
    nome_completo VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    --ruolo VARCHAR(20) NOT NULL CHECK (ruolo IN ('admin', 'archivista', 'consultatore')),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE catasto.utenti ADD COLUMN role_id INTEGER REFERENCES catasto.ruoli_utente(id);
-- Potrebbe essere necessario renderla NOT NULL a seconda della logica

CREATE INDEX idx_utente_username ON utente(username);
CREATE INDEX idx_utente_ruolo ON utente(ruolo);

-- Tabella per il log degli accessi
CREATE TABLE accesso_log (
    id SERIAL PRIMARY KEY,
    utente_id INTEGER REFERENCES utente(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    azione VARCHAR(50) NOT NULL, -- 'login', 'logout', 'password_change', ecc.
    indirizzo_ip VARCHAR(40),
    user_agent TEXT,
    esito BOOLEAN -- successo o fallimento
);

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
    p_esito BOOLEAN
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
INSERT INTO utente (username, password_hash, nome_completo, email, ruolo)
VALUES ('admin', 'password_hash_qui', 'Amministratore Sistema', 'admin@example.com', 'admin');

-- Applicazione del trigger per l'aggiornamento del timestamp di modifica
CREATE TRIGGER update_utente_modifica
BEFORE UPDATE ON utente
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TABLE catasto.sessioni_utente (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES catasto.utenti(id) ON DELETE CASCADE,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    client_ip_address VARCHAR(45),
    login_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP WITH TIME ZONE
);
CREATE TABLE catasto.audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES catasto.utenti(id) ON DELETE SET NULL, -- O non referenziare se vuoi loggare anche azioni anonime
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(100) NOT NULL,         -- Es. LOGIN_SUCCESS, CREATE_PARTITA
    table_name VARCHAR(100),             -- Tabella interessata
    record_id VARCHAR(255),                 -- ID del record interessato (può essere stringa o int a seconda della tabella)
    details TEXT,                        -- Dettagli aggiuntivi (JSON o testo)
    session_id VARCHAR(255),             -- ID della sessione utente
    client_ip_address VARCHAR(45),
    success BOOLEAN
);