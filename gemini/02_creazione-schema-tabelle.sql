-- Dopo la creazione del database, utilizzare un comando ALTER
ALTER DATABASE catasto_storico SET search_path TO catasto;

-- Creazione dello schema
CREATE SCHEMA IF NOT EXISTS catasto;

-- Imposta lo schema predefinito
SET search_path TO catasto;

-- Estensione per il supporto UUID se necessario
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabella COMUNE
CREATE TABLE comune (
    nome VARCHAR(100) PRIMARY KEY,
    provincia VARCHAR(100) NOT NULL,
    regione VARCHAR(100) NOT NULL,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella REGISTRO_PARTITE
CREATE TABLE registro_partite (
    id SERIAL PRIMARY KEY,
    comune_nome VARCHAR(100) NOT NULL REFERENCES comune(nome) ON UPDATE CASCADE ON DELETE RESTRICT,
    anno_impianto INTEGER NOT NULL,
    numero_volumi INTEGER NOT NULL,
    stato_conservazione VARCHAR(100),
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(comune_nome, anno_impianto)
);

-- Tabella REGISTRO_MATRICOLE
CREATE TABLE registro_matricole (
    id SERIAL PRIMARY KEY,
    comune_nome VARCHAR(100) NOT NULL REFERENCES comune(nome) ON UPDATE CASCADE ON DELETE RESTRICT,
    anno_impianto INTEGER NOT NULL,
    numero_volumi INTEGER NOT NULL,
    stato_conservazione VARCHAR(100),
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(comune_nome, anno_impianto)
);

-- Tabella PARTITA
CREATE TABLE partita (
    id SERIAL PRIMARY KEY,
    comune_nome VARCHAR(100) NOT NULL REFERENCES comune(nome) ON UPDATE CASCADE ON DELETE RESTRICT,
    numero_partita INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('principale', 'secondaria')),
    data_impianto DATE,
    data_chiusura DATE,
    numero_provenienza INTEGER,
    stato VARCHAR(20) NOT NULL DEFAULT 'attiva' CHECK (stato IN ('attiva', 'inattiva')),
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(comune_nome, numero_partita)
);

-- Tabella POSSESSORE
CREATE TABLE possessore (
    id SERIAL PRIMARY KEY,
    comune_nome VARCHAR(100) NOT NULL REFERENCES comune(nome) ON UPDATE CASCADE ON DELETE RESTRICT,
    cognome_nome VARCHAR(255) NOT NULL,
    paternita VARCHAR(255),
    nome_completo VARCHAR(255) NOT NULL,
    attivo BOOLEAN NOT NULL DEFAULT TRUE,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella di relazione tra PARTITA e POSSESSORE
CREATE TABLE partita_possessore (
    id SERIAL PRIMARY KEY,
    partita_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    possessore_id INTEGER NOT NULL REFERENCES possessore(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    tipo_partita VARCHAR(20) NOT NULL CHECK (tipo_partita IN ('principale', 'secondaria')),
    titolo VARCHAR(50) NOT NULL DEFAULT 'proprietà esclusiva',
    quota VARCHAR(20) DEFAULT NULL,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(partita_id, possessore_id)
);

-- Tabella LOCALITA
CREATE TABLE localita (
    id SERIAL PRIMARY KEY,
    comune_nome VARCHAR(100) NOT NULL REFERENCES comune(nome) ON UPDATE CASCADE ON DELETE RESTRICT,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('regione', 'via', 'borgata')),
    civico INTEGER,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(comune_nome, nome, civico)
);

-- Tabella IMMOBILE
CREATE TABLE immobile (
    id SERIAL PRIMARY KEY,
    partita_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    localita_id INTEGER NOT NULL REFERENCES localita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    natura VARCHAR(100) NOT NULL,
    numero_piani INTEGER,
    numero_vani INTEGER,
    consistenza VARCHAR(255),
    classificazione VARCHAR(100),
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relazione tra PARTITE (per gestire partite principali-secondarie)
CREATE TABLE partita_relazione (
    id SERIAL PRIMARY KEY,
    partita_principale_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    partita_secondaria_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (partita_principale_id != partita_secondaria_id),
    UNIQUE(partita_principale_id, partita_secondaria_id)
);

-- Tabella VARIAZIONE
CREATE TABLE variazione (
    id SERIAL PRIMARY KEY,
    partita_origine_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    partita_destinazione_id INTEGER REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('Acquisto', 'Successione', 'Variazione', 'Frazionamento', 'Divisione')),
    data_variazione DATE NOT NULL,
    numero_riferimento VARCHAR(50),
    nominativo_riferimento VARCHAR(255),
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella CONTRATTO
CREATE TABLE contratto (
    id SERIAL PRIMARY KEY,
    variazione_id INTEGER NOT NULL REFERENCES variazione(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('Vendita', 'Divisione', 'Successione', 'Donazione')),
    data_contratto DATE NOT NULL,
    notaio VARCHAR(255),
    repertorio VARCHAR(100),
    note TEXT,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella CONSULTAZIONE
CREATE TABLE consultazione (
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    richiedente VARCHAR(255) NOT NULL,
    documento_identita VARCHAR(100),
    motivazione TEXT,
    materiale_consultato TEXT,
    funzionario_autorizzante VARCHAR(255),
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indici per migliorare le performance
CREATE INDEX idx_partita_numero ON partita(numero_partita);
CREATE INDEX idx_possessore_nome ON possessore(nome_completo);
CREATE INDEX idx_immobile_natura ON immobile(natura);
CREATE INDEX idx_variazione_tipo ON variazione(tipo);
CREATE INDEX idx_localita_nome ON localita(nome);
CREATE INDEX idx_partita_comune ON partita(comune_nome);
CREATE INDEX idx_possessore_comune ON possessore(comune_nome);
CREATE INDEX idx_localita_comune ON localita(comune_nome);
CREATE INDEX idx_immobile_partita ON immobile(partita_id);
CREATE INDEX idx_immobile_localita ON immobile(localita_id);
CREATE INDEX idx_variazione_partita_origine ON variazione(partita_origine_id);
CREATE INDEX idx_variazione_partita_destinazione ON variazione(partita_destinazione_id);
CREATE INDEX idx_contratto_variazione ON contratto(variazione_id);
CREATE INDEX idx_partita_possessore_partita ON partita_possessore(partita_id);
CREATE INDEX idx_partita_possessore_possessore ON partita_possessore(possessore_id);

-- Commenti sulle tabelle
COMMENT ON TABLE comune IS 'Tabella dei comuni catalogati nel catasto storico';
COMMENT ON TABLE registro_partite IS 'Registro delle partite catastali per comune';
COMMENT ON TABLE registro_matricole IS 'Registro delle matricole (possessori) per comune';
COMMENT ON TABLE partita IS 'Partite catastali che rappresentano proprietà immobiliari';
COMMENT ON TABLE possessore IS 'Proprietari o possessori di immobili';
COMMENT ON TABLE partita_possessore IS 'Relazione tra partite e possessori';
COMMENT ON TABLE localita IS 'Località o indirizzi degli immobili';
COMMENT ON TABLE immobile IS 'Immobili registrati nel catasto';
COMMENT ON TABLE partita_relazione IS 'Relazioni tra partite principali e secondarie';
COMMENT ON TABLE variazione IS 'Variazioni di proprietà o modifiche alle partite';
COMMENT ON TABLE contratto IS 'Contratti che documentano le variazioni';
COMMENT ON TABLE consultazione IS 'Registro delle consultazioni dello archivio';

-- Inserimento primo comune come esempio
INSERT INTO comune (nome, provincia, regione) VALUES ('Carcare', 'Savona', 'Liguria');