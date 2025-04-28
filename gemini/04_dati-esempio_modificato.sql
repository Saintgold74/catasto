-- Imposta lo schema
SET search_path TO catasto;

/*
 * Script per l'inserimento di dati di esempio nel database del catasto storico
 * Questo script offre due modalità:
 * 1. Inserimento di dati di esempio predefiniti
 * 2. Importazione di dati da file CSV
 *
 * Utilizzare il parametro p_source per specificare la modalità:
 *   - 'predefined': utilizza i dati predefiniti (default)
 *   - 'csv': importa dati da file CSV
 *
 * Per l'importazione da CSV, è necessario specificare il percorso dei file
 * tramite il parametro p_csv_path
 */

-- Funzione per gestire l'inserimento di dati di esempio
CREATE OR REPLACE PROCEDURE carica_dati_esempio(
    p_source VARCHAR DEFAULT 'predefined',
    p_csv_path VARCHAR DEFAULT '/tmp/csv/'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;
    v_comune_count INTEGER;
    v_file_exists BOOLEAN;
BEGIN
    -- Verifica se esistono già dati nel database
    SELECT COUNT(*) INTO v_comune_count FROM comune;
    
    IF v_comune_count > 0 THEN
        RAISE NOTICE 'Ci sono già dati nel database. Procedere con cautela.';
    END IF;

    -- Gestione in base alla fonte dei dati
    IF p_source = 'predefined' THEN
        RAISE NOTICE 'Caricamento dati predefiniti...';
        PERFORM carica_dati_predefiniti();
    ELSIF p_source = 'csv' THEN
        -- Verifica l'esistenza della directory e dei file CSV
        -- Nota: In PostgreSQL standard non è possibile verificare l'esistenza di file
        -- Questo controllo è solo indicativo e andrebbe implementato a livello applicativo
        RAISE NOTICE 'Caricamento dati da CSV nella directory: %', p_csv_path;
        PERFORM carica_dati_csv(p_csv_path);
    ELSE
        RAISE EXCEPTION 'Fonte dati non valida. Utilizzare "predefined" o "csv".';
    END IF;
    
    RAISE NOTICE 'Caricamento dati completato con successo.';
END;
$$;

-- Funzione per caricare i dati predefiniti
CREATE OR REPLACE FUNCTION carica_dati_predefiniti()
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    -- Inserimento Comuni (con ON CONFLICT per evitare duplicati)
    INSERT INTO comune (nome, provincia, regione) VALUES 
    ('Carcare', 'Savona', 'Liguria'),
    ('Cairo Montenotte', 'Savona', 'Liguria'),
    ('Altare', 'Savona', 'Liguria')
    ON CONFLICT (nome) DO NOTHING;

    -- Inserimento Registri Partite
    INSERT INTO registro_partite (comune_nome, anno_impianto, numero_volumi, stato_conservazione) VALUES
    ('Carcare', 1950, 3, 'Buono'),
    ('Cairo Montenotte', 1948, 5, 'Discreto'),
    ('Altare', 1952, 2, 'Ottimo');

    -- Inserimento Registri Matricole
    INSERT INTO registro_matricole (comune_nome, anno_impianto, numero_volumi, stato_conservazione) VALUES
    ('Carcare', 1950, 2, 'Buono'),
    ('Cairo Montenotte', 1948, 4, 'Discreto'),
    ('Altare', 1952, 1, 'Ottimo');

    -- Inserimento Possessori
    INSERT INTO possessore (comune_nome, cognome_nome, paternita, nome_completo, attivo) VALUES
    ('Carcare', 'Fossati Angelo', 'fu Roberto', 'Fossati Angelo fu Roberto', true),
    ('Carcare', 'Caviglia Maria', 'fu Giuseppe', 'Caviglia Maria fu Giuseppe', true),
    ('Carcare', 'Barberis Giovanni', 'fu Paolo', 'Barberis Giovanni fu Paolo', true),
    ('Cairo Montenotte', 'Berruti Antonio', 'fu Luigi', 'Berruti Antonio fu Luigi', true),
    ('Cairo Montenotte', 'Ferraro Caterina', 'fu Marco', 'Ferraro Caterina fu Marco', true),
    ('Altare', 'Bormioli Pietro', 'fu Carlo', 'Bormioli Pietro fu Carlo', true);

    -- Inserimento Località
    INSERT INTO localita (comune_nome, nome, tipo, civico) VALUES
    ('Carcare', 'Regione Vista', 'regione', NULL),
    ('Carcare', 'Via Giuseppe Verdi', 'via', 12),
    ('Carcare', 'Via Roma', 'via', 5),
    ('Cairo Montenotte', 'Borgata Ferrere', 'borgata', NULL),
    ('Cairo Montenotte', 'Strada Provinciale', 'via', 76),
    ('Altare', 'Via Palermo', 'via', 22);

    -- Inserimento Partite
    INSERT INTO partita (comune_nome, numero_partita, tipo, data_impianto, stato) VALUES
    ('Carcare', 221, 'principale', '1950-05-10', 'attiva'),
    ('Carcare', 219, 'principale', '1950-05-10', 'attiva'),
    ('Carcare', 245, 'secondaria', '1951-03-22', 'attiva'),
    ('Cairo Montenotte', 112, 'principale', '1948-11-05', 'attiva'),
    ('Cairo Montenotte', 118, 'principale', '1949-01-15', 'inattiva'),
    ('Altare', 87, 'principale', '1952-07-03', 'attiva');

    -- Associazione Partite-Possessori
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES
    (1, 1, 'principale', 'proprietà esclusiva', NULL),
    (2, 2, 'principale', 'proprietà esclusiva', NULL),
    (3, 3, 'secondaria', 'comproprietà', '1/2'),
    (3, 2, 'secondaria', 'comproprietà', '1/2'),
    (4, 4, 'principale', 'proprietà esclusiva', NULL),
    (5, 5, 'principale', 'proprietà esclusiva', NULL),
    (6, 6, 'principale', 'proprietà esclusiva', NULL);

    -- Relazioni tra partite (principale-secondaria)
    INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id) VALUES
    (2, 3);

    -- Inserimento Immobili
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES
    (1, 1, 'Molino da cereali', 2, NULL, '150 mq', 'Artigianale'),
    (2, 2, 'Casa', 3, 8, '210 mq', 'Abitazione civile'),
    (3, 3, 'Magazzino', 1, NULL, '80 mq', 'Deposito'),
    (4, 4, 'Fabbricato rurale', 2, 5, '180 mq', 'Abitazione rurale'),
    (5, 5, 'Casa', 2, 6, '160 mq', 'Abitazione civile'),
    (6, 6, 'Laboratorio', 1, NULL, '120 mq', 'Artigianale');

    -- Inserimento Variazioni
    INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento) VALUES
    (5, NULL, 'Successione', '1952-08-15', '22/52', 'Ferraro Caterina');

    -- Inserimento Contratti
    INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note) VALUES
    (1, 'Successione', '1952-08-10', 'Notaio Rossi', '1234/52', 'Successione per morte del proprietario Luigi Ferraro');

    -- Inserimento Consultazioni
    INSERT INTO consultazione (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante) VALUES
    ('2025-04-01', 'Mario Bianchi', 'CI AB1234567', 'Ricerca storica', 'Registro partite Carcare 1950', 'Dott. Verdi'),
    ('2025-04-05', 'Studio Legale Rossi', 'Tessera Ordine 55213', 'Verifica proprietà', 'Partite 221 e 219 Carcare', 'Dott. Verdi');
END;
$$;

-- Funzione per caricare i dati da file CSV
CREATE OR REPLACE FUNCTION carica_dati_csv(p_csv_path VARCHAR)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_comuni_file VARCHAR := p_csv_path || 'comuni.csv';
    v_possessori_file VARCHAR := p_csv_path || 'possessori.csv';
    v_localita_file VARCHAR := p_csv_path || 'localita.csv';
    v_partite_file VARCHAR := p_csv_path || 'partite.csv';
    v_immobili_file VARCHAR := p_csv_path || 'immobili.csv';
    v_variazioni_file VARCHAR := p_csv_path || 'variazioni.csv';
    v_sql TEXT;
BEGIN
    -- Creazione di tabelle temporanee per il caricamento dei CSV
    CREATE TEMP TABLE temp_comuni (
        nome VARCHAR(100),
        provincia VARCHAR(100),
        regione VARCHAR(100)
    );
    
    CREATE TEMP TABLE temp_possessori (
        comune_nome VARCHAR(100),
        cognome_nome VARCHAR(255),
        paternita VARCHAR(255),
        nome_completo VARCHAR(255),
        attivo BOOLEAN
    );
    
    CREATE TEMP TABLE temp_localita (
        comune_nome VARCHAR(100),
        nome VARCHAR(255),
        tipo VARCHAR(50),
        civico INTEGER
    );
    
    CREATE TEMP TABLE temp_partite (
        comune_nome VARCHAR(100),
        numero_partita INTEGER,
        tipo VARCHAR(20),
        data_impianto DATE,
        stato VARCHAR(20)
    );
    
    CREATE TEMP TABLE temp_partita_possessore (
        partita_comune VARCHAR(100),
        partita_numero INTEGER,
        possessore_nome_completo VARCHAR(255),
        tipo_partita VARCHAR(20),
        titolo VARCHAR(50),
        quota VARCHAR(20)
    );
    
    CREATE TEMP TABLE temp_immobili (
        partita_comune VARCHAR(100),
        partita_numero INTEGER,
        localita_nome VARCHAR(255),
        natura VARCHAR(100),
        numero_piani INTEGER,
        numero_vani INTEGER,
        consistenza VARCHAR(255),
        classificazione VARCHAR(100)
    );
    
    CREATE TEMP TABLE temp_variazioni (
        partita_origine_comune VARCHAR(100),
        partita_origine_numero INTEGER,
        partita_dest_comune VARCHAR(100),
        partita_dest_numero INTEGER,
        tipo VARCHAR(50),
        data_variazione DATE,
        numero_riferimento VARCHAR(50),
        nominativo_riferimento VARCHAR(255)
    );
    
    -- Caricamento dei file CSV nelle tabelle temporanee
    BEGIN
        -- Caricamento comuni
        v_sql := 'COPY temp_comuni FROM ''' || v_comuni_file || ''' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
        EXECUTE v_sql;
        RAISE NOTICE 'Caricati dati comuni da %', v_comuni_file;
        
        -- Inserimento comuni nella tabella principale
        INSERT INTO comune (nome, provincia, regione)
        SELECT nome, provincia, regione FROM temp_comuni
        ON CONFLICT (nome) DO NOTHING;
        
        -- Caricamento possessori
        v_sql := 'COPY temp_possessori FROM ''' || v_possessori_file || ''' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
        EXECUTE v_sql;
        RAISE NOTICE 'Caricati dati possessori da %', v_possessori_file;
        
        -- Inserimento possessori nella tabella principale
        INSERT INTO possessore (comune_nome, cognome_nome, paternita, nome_completo, attivo)
        SELECT comune_nome, cognome_nome, paternita, nome_completo, attivo FROM temp_possessori;
        
        -- Caricamento località
        v_sql := 'COPY temp_localita FROM ''' || v_localita_file || ''' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
        EXECUTE v_sql;
        RAISE NOTICE 'Caricati dati località da %', v_localita_file;
        
        -- Inserimento località nella tabella principale
        INSERT INTO localita (comune_nome, nome, tipo, civico)
        SELECT comune_nome, nome, tipo, civico FROM temp_localita;
        
        -- Caricamento partite
        v_sql := 'COPY temp_partite FROM ''' || v_partite_file || ''' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
        EXECUTE v_sql;
        RAISE NOTICE 'Caricati dati partite da %', v_partite_file;
        
        -- Inserimento partite nella tabella principale
        INSERT INTO partita (comune_nome, numero_partita, tipo, data_impianto, stato)
        SELECT comune_nome, numero_partita, tipo, data_impianto, stato FROM temp_partite;
        
        -- Caricamento relazioni partita-possessore
        v_sql := 'COPY temp_partita_possessore FROM ''' || p_csv_path || 'partita_possessore.csv'' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
        EXECUTE v_sql;
        RAISE NOTICE 'Caricati dati relazioni partita-possessore';
        
        -- Inserimento relazioni partita-possessore
        INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
        SELECT 
            p.id, 
            pos.id, 
            tp.tipo_partita, 
            tp.titolo, 
            tp.quota
        FROM temp_partita_possessore tp
        JOIN partita p ON p.comune_nome = tp.partita_comune AND p.numero_partita = tp.partita_numero
        JOIN possessore pos ON pos.nome_completo = tp.possessore_nome_completo;
        
        -- Caricamento immobili
        v_sql := 'COPY temp_immobili FROM ''' || v_immobili_file || ''' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
        EXECUTE v_sql;
        RAISE NOTICE 'Caricati dati immobili da %', v_immobili_file;
        
        -- Inserimento immobili
        INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
        SELECT 
            p.id, 
            l.id, 
            ti.natura, 
            ti.numero_piani, 
            ti.numero_vani, 
            ti.consistenza, 
            ti.classificazione
        FROM temp_immobili ti
        JOIN partita p ON p.comune_nome = ti.partita_comune AND p.numero_partita = ti.partita_numero
        JOIN localita l ON l.comune_nome = ti.partita_comune AND l.nome = ti.localita_nome;
        
        -- Caricamento variazioni
        v_sql := 'COPY temp_variazioni FROM ''' || v_variazioni_file || ''' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
        EXECUTE v_sql;
        RAISE NOTICE 'Caricati dati variazioni da %', v_variazioni_file;
        
        -- Inserimento variazioni
        INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento)
        SELECT 
            po.id, 
            pd.id, 
            tv.tipo, 
            tv.data_variazione, 
            tv.numero_riferimento, 
            tv.nominativo_riferimento
        FROM temp_variazioni tv
        JOIN partita po ON po.comune_nome = tv.partita_origine_comune AND po.numero_partita = tv.partita_origine_numero
        LEFT JOIN partita pd ON pd.comune_nome = tv.partita_dest_comune AND pd.numero_partita = tv.partita_dest_numero;
    
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore nel caricamento dei dati da CSV: %', SQLERRM;
    END;
    
    -- Pulizia tabelle temporanee
    DROP TABLE IF EXISTS temp_comuni;
    DROP TABLE IF EXISTS temp_possessori;
    DROP TABLE IF EXISTS temp_localita;
    DROP TABLE IF EXISTS temp_partite;
    DROP TABLE IF EXISTS temp_partita_possessore;
    DROP TABLE IF EXISTS temp_immobili;
    DROP TABLE IF EXISTS temp_variazioni;
END;
$$;

-- Funzione per esportare i dati verso CSV (utile per generare dataset di esempio)
CREATE OR REPLACE PROCEDURE esporta_dati_csv(
    p_export_path VARCHAR DEFAULT '/tmp/csv/'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sql TEXT;
BEGIN
    -- Esportazione comuni
    v_sql := 'COPY (SELECT nome, provincia, regione FROM comune) TO ''' || 
             p_export_path || 'comuni.csv'' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
    EXECUTE v_sql;
    
    -- Esportazione possessori
    v_sql := 'COPY (SELECT comune_nome, cognome_nome, paternita, nome_completo, attivo FROM possessore) TO ''' || 
             p_export_path || 'possessori.csv'' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
    EXECUTE v_sql;
    
    -- Esportazione località
    v_sql := 'COPY (SELECT comune_nome, nome, tipo, civico FROM localita) TO ''' || 
             p_export_path || 'localita.csv'' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
    EXECUTE v_sql;
    
    -- Esportazione partite
    v_sql := 'COPY (SELECT comune_nome, numero_partita, tipo, data_impianto, stato FROM partita) TO ''' || 
             p_export_path || 'partite.csv'' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
    EXECUTE v_sql;
    
    -- Esportazione relazioni partita-possessore
    v_sql := 'COPY (
        SELECT 
            p.comune_nome AS partita_comune, 
            p.numero_partita AS partita_numero, 
            pos.nome_completo, 
            pp.tipo_partita, 
            pp.titolo, 
            pp.quota 
        FROM partita_possessore pp
        JOIN partita p ON pp.partita_id = p.id
        JOIN possessore pos ON pp.possessore_id = pos.id
    ) TO ''' || p_export_path || 'partita_possessore.csv'' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
    EXECUTE v_sql;
    
    -- Esportazione immobili
    v_sql := 'COPY (
        SELECT 
            p.comune_nome AS partita_comune, 
            p.numero_partita AS partita_numero, 
            l.nome AS localita_nome, 
            i.natura, 
            i.numero_piani, 
            i.numero_vani, 
            i.consistenza, 
            i.classificazione
        FROM immobile i
        JOIN partita p ON i.partita_id = p.id
        JOIN localita l ON i.localita_id = l.id
    ) TO ''' || p_export_path || 'immobili.csv'' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
    EXECUTE v_sql;
    
    -- Esportazione variazioni
    v_sql := 'COPY (
        SELECT 
            po.comune_nome AS partita_origine_comune, 
            po.numero_partita AS partita_origine_numero, 
            pd.comune_nome AS partita_dest_comune, 
            pd.numero_partita AS partita_dest_numero, 
            v.tipo, 
            v.data_variazione, 
            v.numero_riferimento, 
            v.nominativo_riferimento
        FROM variazione v
        JOIN partita po ON v.partita_origine_id = po.id
        LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
    ) TO ''' || p_export_path || 'variazioni.csv'' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
    EXECUTE v_sql;
    
    RAISE NOTICE 'Dati esportati con successo nella directory %', p_export_path;
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Errore nell''esportazione dei dati in CSV: %', SQLERRM;
END;
$$;

-- Procedura per generare template CSV vuoti
CREATE OR REPLACE PROCEDURE genera_template_csv(
    p_export_path VARCHAR DEFAULT '/tmp/csv/'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sql TEXT;
BEGIN
    -- Template comuni
    v_sql := 'COPY (
        SELECT 
            ''Carcare''::VARCHAR AS nome, 
            ''Savona''::VARCHAR AS provincia, 
            ''Liguria''::VARCHAR AS regione
        WHERE FALSE
    ) TO ''' || p_export_path || 'template_comuni.csv'' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
    EXECUTE v_sql;
    
    -- Template possessori
    v_sql := 'COPY (
        SELECT 
            ''Carcare''::VARCHAR AS comune_nome, 
            ''Rossi Mario''::VARCHAR AS cognome_nome, 
            ''fu Antonio''::VARCHAR AS paternita, 
            ''Rossi Mario fu Antonio''::VARCHAR AS nome_completo, 
            TRUE::BOOLEAN AS attivo
        WHERE FALSE
    ) TO ''' || p_export_path || 'template_possessori.csv'' WITH (FORMAT csv, HEADER true, DELIMITER '';'')';
    EXECUTE v_sql;
    
    -- Continua con gli altri template...
    
    RAISE NOTICE 'Template CSV generati nella directory %', p_export_path;
EXCEPTION WHEN OTHERS THEN
    RAISE EXCEPTION 'Errore nella generazione dei template CSV: %', SQLERRM;
END;
$$;

-- Esempio di utilizzo della procedura principale
DO $$
BEGIN
    -- Per caricare dati predefiniti:
    -- CALL carica_dati_esempio('predefined');
    
    -- Per caricare dati da CSV:
    -- CALL carica_dati_esempio('csv', '/percorso/ai/csv/');
    
    -- Per esportare i dati attuali in CSV:
    -- CALL esporta_dati_csv('/percorso/di/output/');
    
    -- Per generare template CSV:
    -- CALL genera_template_csv('/percorso/di/output/');
    
    -- Di default, carica i dati predefiniti
    CALL carica_dati_esempio();
END;
$$;
