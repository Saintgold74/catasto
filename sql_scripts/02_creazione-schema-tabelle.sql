-- File: 02_creazione-schema-tabelle.sql (Versione CORRETTA Definitiva)

-- Dopo la creazione del database, utilizzare un comando ALTER
ALTER DATABASE catasto_storico SET search_path TO catasto, public; -- Aggiunto public

-- Creazione dello schema
CREATE SCHEMA IF NOT EXISTS catasto;

-- Imposta lo schema predefinito per la sessione corrente
SET search_path TO catasto, public; -- Aggiunto public per le estensioni

-- Estensioni necessarie
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public; -- O catasto se preferito
CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA public;   -- O catasto se preferito

-- Tabella COMUNE (Modificata con ID PK)
CREATE TABLE comune (
    id SERIAL PRIMARY KEY, -- Chiave primaria numerica
    nome VARCHAR(100) NOT NULL UNIQUE, -- Nome rimane, ma ora è solo UNIQUE
    provincia VARCHAR(100) NOT NULL,
    regione VARCHAR(100) NOT NULL,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
    -- La colonna periodo_id da script 11 verrà aggiunta lì o qui se preferito
);
COMMENT ON TABLE comune IS 'Tabella dei comuni catalogati nel catasto storico (con ID PK).';

-- Tabella REGISTRO_PARTITE (Modificata per usare comune_id)
CREATE TABLE registro_partite (
    id SERIAL PRIMARY KEY,
    comune_id INTEGER NOT NULL REFERENCES comune(id) ON UPDATE CASCADE ON DELETE RESTRICT, -- FK su ID
    anno_impianto INTEGER NOT NULL,
    numero_volumi INTEGER NOT NULL,
    stato_conservazione VARCHAR(100),
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(comune_id, anno_impianto) -- UNIQUE su ID + anno
);
COMMENT ON TABLE registro_partite IS 'Registro delle partite catastali per comune (referenzia comune.id).';

-- Tabella REGISTRO_MATRICOLE (Modificata per usare comune_id)
CREATE TABLE registro_matricole (
    id SERIAL PRIMARY KEY,
    comune_id INTEGER NOT NULL REFERENCES comune(id) ON UPDATE CASCADE ON DELETE RESTRICT, -- FK su ID
    anno_impianto INTEGER NOT NULL,
    numero_volumi INTEGER NOT NULL,
    stato_conservazione VARCHAR(100),
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(comune_id, anno_impianto) -- UNIQUE su ID + anno
);
COMMENT ON TABLE registro_matricole IS 'Registro delle matricole (possessori) per comune (referenzia comune.id).';

-- Tabella PARTITA (Modificata per usare comune_id)
CREATE TABLE catasto.partita (
    id SERIAL PRIMARY KEY,
    comune_id INTEGER NOT NULL REFERENCES catasto.comune(id) ON DELETE RESTRICT,
    numero_partita INTEGER NOT NULL,
    -- NUOVA COLONNA: suffisso_partita
    suffisso_partita VARCHAR(20) DEFAULT NULL,
    data_impianto DATE NOT NULL,
    data_chiusura DATE,
    numero_provenienza VARCHAR(50), -- O INTEGER, a seconda del formato previsto
    stato VARCHAR(20) NOT NULL CHECK (stato IN ('attiva', 'inattiva')),
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('principale', 'secondaria')),
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);

-- Aggiorna il vincolo di unicità:
-- Vecchio: UNIQUE (comune_id, numero_partita)
-- Nuovo:   UNIQUE (comune_id, numero_partita, suffisso_partita)
-- PostgreSQL tratta NULL come valori distinti per UNIQUE.
-- Questo significa che puoi avere (1, 10, NULL) e (1, 10, NULL) solo se usi NULLS NOT DISTINCT (PG 15+).
-- Per versioni precedenti (o default), (1, 10, NULL) sarà unico.
-- Se hai bisogno di UNA SOLA partita con suffisso NULL per ogni (comune_id, numero_partita)
-- e le altre devono avere un suffisso, questa UNIQUE va bene.
ALTER TABLE catasto.partita
ADD CONSTRAINT partita_unique_numero_suffisso_comune UNIQUE (comune_id, numero_partita, suffisso_partita);

-- COMMENTI (per documentazione nel DB)
COMMENT ON TABLE catasto.partita IS 'Tabelle per la gestione delle partite catastali storiche.';
COMMENT ON COLUMN catasto.partita.id IS 'Identificatore univoco della partita.';
COMMENT ON COLUMN catasto.partita.comune_id IS 'Chiave esterna al comune di riferimento.';
COMMENT ON COLUMN catasto.partita.numero_partita IS 'Numero identificativo della partita.';
COMMENT ON COLUMN catasto.partita.suffisso_partita IS 'Suffisso aggiuntivo per identificare partite duplicate con lo stesso numero (es. bis, ter, A, B).'; -- NUOVO COMMENTO
COMMENT ON COLUMN catasto.partita.data_impianto IS 'Data di creazione/impianto della partita.';
COMMENT ON COLUMN catasto.partita.data_chiusura IS 'Data di chiusura della partita.';
COMMENT ON COLUMN catasto.partita.numero_provenienza IS 'Numero di riferimento da cui proviene la partita (es. altra partita).';
COMMENT ON COLUMN catasto.partita.stato IS 'Stato attuale della partita (attiva, inattiva).';
COMMENT ON COLUMN catasto.partita.tipo IS 'Tipo di partita (principale, secondaria).';
COMMENT ON COLUMN catasto.partita.data_creazione IS 'Timestamp di creazione del record.';
COMMENT ON COLUMN catasto.partita.data_modifica IS 'Timestamp dell''ultima modifica del record.';

-- Tabella POSSESSORE (Modificata per usare comune_id)
CREATE TABLE possessore (
    id SERIAL PRIMARY KEY,
    comune_id INTEGER NOT NULL REFERENCES comune(id) ON UPDATE CASCADE ON DELETE RESTRICT, -- FK su ID
    cognome_nome VARCHAR(255) NOT NULL,
    paternita VARCHAR(255),
    nome_completo VARCHAR(255) NOT NULL,
    attivo BOOLEAN NOT NULL DEFAULT TRUE,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE possessore IS 'Proprietari o possessori di immobili (referenzia comune.id).';

-- Tabella di relazione tra PARTITA e POSSESSORE (Nessuna modifica necessaria qui)
CREATE TABLE partita_possessore (
    id SERIAL PRIMARY KEY,
    partita_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    possessore_id INTEGER NOT NULL REFERENCES possessore(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    tipo_partita VARCHAR(20) NOT NULL CHECK (tipo_partita IN ('principale', 'secondaria')),
    titolo VARCHAR(50) NOT NULL DEFAULT 'proprietà esclusiva',
    quota VARCHAR(20) DEFAULT NULL,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(partita_id, possessore_id)
);
COMMENT ON TABLE partita_possessore IS 'Relazione tra partite e possessori.';

-- Tabella LOCALITA (Modificata per usare comune_id)
CREATE TABLE localita (
    id SERIAL PRIMARY KEY,
    comune_id INTEGER NOT NULL REFERENCES comune(id) ON UPDATE CASCADE ON DELETE RESTRICT, -- FK su ID
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('Regione', 'Via', 'Borgata', 'Altro')),
    civico INTEGER,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(comune_id, nome, civico) -- UNIQUE su ID + nome + civico
    -- La colonna periodo_id da script 11 verrà aggiunta lì o qui se preferito
);
COMMENT ON TABLE localita IS 'Località o indirizzi degli immobili (referenzia comune.id).';

-- Tabella IMMOBILE (Nessuna modifica diretta per comune_id, relazione indiretta tramite partita_id)
CREATE TABLE immobile (
    id SERIAL PRIMARY KEY,
    partita_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    localita_id INTEGER NOT NULL REFERENCES localita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    natura VARCHAR(100) NOT NULL,
    numero_piani INTEGER,
    numero_vani INTEGER,
    consistenza VARCHAR(255),
    classificazione VARCHAR(100),
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE immobile IS 'Immobili registrati nel catasto.';

-- Relazione tra PARTITE (Nessuna modifica necessaria qui)
CREATE TABLE partita_relazione (
    id SERIAL PRIMARY KEY,
    partita_principale_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    partita_secondaria_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    CHECK (partita_principale_id != partita_secondaria_id),
    UNIQUE(partita_principale_id, partita_secondaria_id)
);
COMMENT ON TABLE partita_relazione IS 'Relazioni tra partite principali e secondarie.';

-- Tabella VARIAZIONE (Nessuna modifica necessaria qui)
CREATE TABLE variazione (
    id SERIAL PRIMARY KEY,
    partita_origine_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    partita_destinazione_id INTEGER REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('Vendita', 'Acquisto', 'Successione','Variazione', 'Frazionamento', 'Divisione', 'Trasferimento', 'Altro')),
    data_variazione DATE NOT NULL,
    numero_riferimento VARCHAR(50),
    nominativo_riferimento VARCHAR(255),
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE variazione IS 'Variazioni di proprietà o modifiche alle partite.';

-- Tabella CONTRATTO (Nessuna modifica necessaria qui)
CREATE TABLE contratto (
    id SERIAL PRIMARY KEY,
    variazione_id INTEGER NOT NULL REFERENCES variazione(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('Atto di Compravendita',
            'Dichiarazione di Successione','Atto di Donazione','Sentenza Giudiziale','Atto di Divisione','Verbale di Asta Pubblica',
            'Permuta','Usucapione','Altro Atto Pubblico','Scrittura Privata')),
    data_contratto DATE NOT NULL,
    notaio VARCHAR(255),
    repertorio VARCHAR(100),
    note TEXT,
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE contratto IS 'Contratti che documentano le variazioni.';

-- Tabella CONSULTAZIONE (Nessuna modifica necessaria qui)
CREATE TABLE consultazione (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    richiedente VARCHAR(255) NOT NULL,
    documento_identita VARCHAR(100),
    motivazione TEXT,
    materiale_consultato TEXT,
    funzionario_autorizzante VARCHAR(255),
    data_creazione TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE consultazione IS 'Registro delle consultazioni dello archivio.';

-- Indici per migliorare le performance (Aggiornati per comune_id dove necessario)
CREATE INDEX IF NOT EXISTS idx_partita_numero ON partita(numero_partita);
CREATE INDEX IF NOT EXISTS idx_possessore_nome ON possessore(nome_completo);
CREATE INDEX IF NOT EXISTS idx_immobile_natura ON immobile(natura);
CREATE INDEX IF NOT EXISTS idx_variazione_tipo ON variazione(tipo);
CREATE INDEX IF NOT EXISTS idx_localita_nome ON localita(nome);
CREATE INDEX IF NOT EXISTS idx_partita_comune ON partita(comune_id); -- Indice su comune_id
CREATE INDEX IF NOT EXISTS idx_possessore_comune ON possessore(comune_id); -- Indice su comune_id
CREATE INDEX IF NOT EXISTS idx_localita_comune ON localita(comune_id); -- Indice su comune_id
CREATE INDEX IF NOT EXISTS idx_immobile_partita ON immobile(partita_id);
CREATE INDEX IF NOT EXISTS idx_immobile_localita ON immobile(localita_id);
CREATE INDEX IF NOT EXISTS idx_variazione_partita_origine ON variazione(partita_origine_id);
CREATE INDEX IF NOT EXISTS idx_variazione_partita_destinazione ON variazione(partita_destinazione_id);
CREATE INDEX IF NOT EXISTS idx_contratto_variazione ON contratto(variazione_id);
CREATE INDEX IF NOT EXISTS idx_partita_possessore_partita ON partita_possessore(partita_id);
CREATE INDEX IF NOT EXISTS idx_partita_possessore_possessore ON partita_possessore(possessore_id);

-- === Creazione Tabella AUDIT_LOG ===
-- (Spostata qui da script 06/15 per assicurare l'esistenza prima di ALTER/VIEW)

CREATE TABLE IF NOT EXISTS catasto.audit_log (
    id SERIAL PRIMARY KEY,
    tabella VARCHAR(100) NOT NULL,
    operazione CHAR(1) NOT NULL CHECK (operazione IN ('I', 'U', 'D')),
    record_id INTEGER, -- Permette NULL per PK non standard o non 'id'
    dati_prima JSONB,
    dati_dopo JSONB,
    utente VARCHAR(100), -- Nome utente DB che ha eseguito l'operazione
    ip_address VARCHAR(40),
    timestamp TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP,
    -- Colonne per integrazione utenti
    session_id VARCHAR(100), -- Aggiunto da script 15
    app_user_id INTEGER      -- Aggiunto da script 15
    -- NON aggiungere FK a utente qui, verrà aggiunto nello script 15
);

CREATE INDEX IF NOT EXISTS idx_audit_tabella ON catasto.audit_log(tabella);
CREATE INDEX IF NOT EXISTS idx_audit_operazione ON catasto.audit_log(operazione);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON catasto.audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_record_id ON catasto.audit_log(record_id) WHERE record_id IS NOT NULL; -- Indice opzionale
CREATE INDEX IF NOT EXISTS idx_audit_app_user_id ON catasto.audit_log(app_user_id) WHERE app_user_id IS NOT NULL; -- Indice opzionale

COMMENT ON TABLE catasto.audit_log IS 'Tabella per la registrazione delle modifiche ai dati (audit trail).';

-- Inserimento primo comune come esempio (ora inserisce anche ID automaticamente)
-- Lasciato commentato se si usa lo script 04 per i dati
-- INSERT INTO comune (nome, provincia, regione) VALUES ('Carcare', 'Savona', 'Liguria');

-- ========================================================================
-- AGGIUNTA ALLA SEZIONE INDICI in 02_creazione-schema-tabelle.sql
-- Aggiungi dopo gli indici esistenti, prima della sezione AUDIT_LOG
-- ========================================================================

-- ========================================================================
-- INDICI GIN PER RICERCA FUZZY (OPZIONALI - per installazioni avanzate)
-- Richiede estensione pg_trgm installata
-- ========================================================================
DO $$
BEGIN
    -- Verifica se pg_trgm è disponibile
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_trgm') THEN
        -- Installa estensione se non presente
        CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA public;
        
        -- Crea indici GIN per ricerca fuzzy
        CREATE INDEX IF NOT EXISTS idx_gin_possessore_nome_completo_trgm
        ON possessore USING gin (nome_completo gin_trgm_ops);
        
        CREATE INDEX IF NOT EXISTS idx_gin_possessore_cognome_nome_trgm
        ON possessore USING gin (cognome_nome gin_trgm_ops);
        
        CREATE INDEX IF NOT EXISTS idx_gin_possessore_paternita_trgm
        ON possessore USING gin (paternita gin_trgm_ops)
        WHERE paternita IS NOT NULL;
        
        CREATE INDEX IF NOT EXISTS idx_gin_localita_nome_trgm
        ON localita USING gin (nome gin_trgm_ops);
        
        RAISE NOTICE 'Indici GIN per ricerca fuzzy creati con successo';
    ELSE
        RAISE NOTICE 'Estensione pg_trgm non disponibile - indici GIN saltati';
    END IF;
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Privilegi insufficienti per pg_trgm - indici GIN saltati';
    WHEN OTHERS THEN
        RAISE NOTICE 'Errore creazione indici GIN: %', SQLERRM;
END $$;