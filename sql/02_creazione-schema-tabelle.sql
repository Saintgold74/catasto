-- Dopo la creazione del database, utilizzare un comando ALTER
-- ALTER DATABASE catasto_storico SET search_path TO catasto, public; -- Aggiunto public

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
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(comune_id, anno_impianto) -- UNIQUE su ID + anno
);
COMMENT ON TABLE registro_matricole IS 'Registro delle matricole (possessori) per comune (referenzia comune.id).';

-- Tabella PARTITA (Modificata per usare comune_id)
CREATE TABLE partita (
    id SERIAL PRIMARY KEY,
    comune_id INTEGER NOT NULL REFERENCES comune(id) ON UPDATE CASCADE ON DELETE RESTRICT, -- FK su ID
    numero_partita INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('principale', 'secondaria')),
    data_impianto DATE,
    data_chiusura DATE,
    numero_provenienza INTEGER,
    stato VARCHAR(20) NOT NULL DEFAULT 'attiva' CHECK (stato IN ('attiva', 'inattiva')),
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(comune_id, numero_partita) -- UNIQUE su ID + numero_partita
);
COMMENT ON TABLE partita IS 'Partite catastali (referenzia comune.id).';

-- Tabella POSSESSORE (Modificata per usare comune_id)
CREATE TABLE possessore (
    id SERIAL PRIMARY KEY,
    comune_id INTEGER NOT NULL REFERENCES comune(id) ON UPDATE CASCADE ON DELETE RESTRICT, -- FK su ID
    cognome_nome VARCHAR(255) NOT NULL,
    paternita VARCHAR(255),
    nome_completo VARCHAR(255) NOT NULL,
    attivo BOOLEAN NOT NULL DEFAULT TRUE,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(partita_id, possessore_id)
);
COMMENT ON TABLE partita_possessore IS 'Relazione tra partite e possessori.';

-- Tabella LOCALITA (Modificata per usare comune_id)
CREATE TABLE localita (
    id SERIAL PRIMARY KEY,
    comune_id INTEGER NOT NULL REFERENCES comune(id) ON UPDATE CASCADE ON DELETE RESTRICT, -- FK su ID
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('regione', 'via', 'borgata')),
    civico INTEGER,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE immobile IS 'Immobili registrati nel catasto.';

-- Relazione tra PARTITE (Nessuna modifica necessaria qui)
CREATE TABLE partita_relazione (
    id SERIAL PRIMARY KEY,
    partita_principale_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    partita_secondaria_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (partita_principale_id != partita_secondaria_id),
    UNIQUE(partita_principale_id, partita_secondaria_id)
);
COMMENT ON TABLE partita_relazione IS 'Relazioni tra partite principali e secondarie.';

-- Tabella VARIAZIONE (Nessuna modifica necessaria qui)
CREATE TABLE variazione (
    id SERIAL PRIMARY KEY,
    partita_origine_id INTEGER NOT NULL REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    partita_destinazione_id INTEGER REFERENCES partita(id) ON UPDATE CASCADE ON DELETE RESTRICT,
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('Acquisto', 'Successione', 'Variazione', 'Frazionamento', 'Divisione', 'Trasferimento')), -- Aggiunto Trasferimento
    data_variazione DATE NOT NULL,
    numero_riferimento VARCHAR(50),
    nominativo_riferimento VARCHAR(255),
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE variazione IS 'Variazioni di proprietà o modifiche alle partite.';

-- Tabella CONTRATTO (Nessuna modifica necessaria qui)
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
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_modifica TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE consultazione IS 'Registro delle consultazioni dello archivio.';

-- Indici per migliorare le performance (Aggiornati per comune_id dove necessario)
CREATE INDEX idx_partita_numero ON partita(numero_partita);
CREATE INDEX idx_possessore_nome ON possessore(nome_completo);
CREATE INDEX idx_immobile_natura ON immobile(natura);
CREATE INDEX idx_variazione_tipo ON variazione(tipo);
CREATE INDEX idx_localita_nome ON localita(nome);
CREATE INDEX idx_partita_comune ON partita(comune_id); -- Indice su comune_id
CREATE INDEX idx_possessore_comune ON possessore(comune_id); -- Indice su comune_id
CREATE INDEX idx_localita_comune ON localita(comune_id); -- Indice su comune_id
CREATE INDEX idx_immobile_partita ON immobile(partita_id);
CREATE INDEX idx_immobile_localita ON immobile(localita_id);
CREATE INDEX idx_variazione_partita_origine ON variazione(partita_origine_id);
CREATE INDEX idx_variazione_partita_destinazione ON variazione(partita_destinazione_id);
CREATE INDEX idx_contratto_variazione ON contratto(variazione_id);
CREATE INDEX idx_partita_possessore_partita ON partita_possessore(partita_id);
CREATE INDEX idx_partita_possessore_possessore ON partita_possessore(possessore_id);

-- Inserimento primo comune come esempio (ora con ID implicito)
-- NOTA: Questo INSERT è ora ridondante se usi lo script 04 per i dati di esempio,
--       ma lo lascio per completezza dello script 02 originale.
-- INSERT INTO comune (nome, provincia, regione) VALUES ('Carcare', 'Savona', 'Liguria');

-- Applicazione del trigger per l'aggiornamento del timestamp di modifica
-- (Assumendo che la funzione update_modified_column() sia definita nello script 03)
-- CREATE TRIGGER update_comune_modifica BEFORE UPDATE ON comune FOR EACH ROW EXECUTE FUNCTION update_modified_column();
-- ... (aggiungere trigger per le altre tabelle modificate, se non già presenti in script 03)