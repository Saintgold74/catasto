-- =====================================================
-- Script di inserimento dati di esempio per Catasto Storico
-- VERSIONE AVANZATA 2.0 (16/04/2025)
-- =====================================================
-- Questo script inserisce un set completo di dati di esempio nel database
-- con gestione ottimizzata dei duplicati e controlli di integrità
-- =====================================================

-- Imposta lo schema
SET search_path TO catasto;

-- =====================================================
-- SEZIONE 1: FUNZIONI DI SUPPORTO PER L'INSERIMENTO 
-- =====================================================

-- Funzione di supporto per inserire comuni gestendo i duplicati
CREATE OR REPLACE FUNCTION inserisci_comune_sicuro(
    p_nome VARCHAR, 
    p_provincia VARCHAR, 
    p_regione VARCHAR
) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
    v_count INTEGER;
BEGIN
    -- Verifica se il comune esiste già
    SELECT COUNT(*) INTO v_count FROM comune WHERE nome = p_nome;
    
    IF v_count = 0 THEN
        -- Inserisci il nuovo comune
        INSERT INTO comune (nome, provincia, regione) 
        VALUES (p_nome, p_provincia, p_regione);
        RAISE NOTICE 'Comune % inserito con successo', p_nome;
    ELSE
        RAISE NOTICE 'Comune % già esistente, aggiornamento dati', p_nome;
        UPDATE comune SET provincia = p_provincia, regione = p_regione WHERE nome = p_nome;
    END IF;
    
    RETURN 1; -- Ritorna 1 per indicare successo
END;
$$ LANGUAGE plpgsql;

-- Funzione di supporto per inserire possessori gestendo i duplicati
CREATE OR REPLACE FUNCTION inserisci_possessore_sicuro(
    p_comune_nome VARCHAR, 
    p_cognome_nome VARCHAR, 
    p_paternita VARCHAR, 
    p_nome_completo VARCHAR, 
    p_attivo BOOLEAN DEFAULT TRUE
) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se il possessore esiste già
    SELECT id INTO v_id FROM possessore 
    WHERE comune_nome = p_comune_nome AND nome_completo = p_nome_completo;
    
    IF v_id IS NULL THEN
        -- Inserisci il nuovo possessore
        INSERT INTO possessore (comune_nome, cognome_nome, paternita, nome_completo, attivo) 
        VALUES (p_comune_nome, p_cognome_nome, p_paternita, p_nome_completo, p_attivo)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Possessore % inserito con ID %', p_nome_completo, v_id;
    ELSE
        RAISE NOTICE 'Possessore % già esistente con ID %', p_nome_completo, v_id;
        -- Aggiorna i dati se necessario
        UPDATE possessore 
        SET cognome_nome = p_cognome_nome,
            paternita = p_paternita,
            attivo = p_attivo
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Funzione di supporto per inserire località gestendo i duplicati
CREATE OR REPLACE FUNCTION inserisci_localita_sicura(
    p_comune_nome VARCHAR, 
    p_nome VARCHAR, 
    p_tipo VARCHAR, 
    p_civico INTEGER DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se la località esiste già
    SELECT id INTO v_id FROM localita 
    WHERE comune_nome = p_comune_nome AND nome = p_nome AND (civico = p_civico OR (civico IS NULL AND p_civico IS NULL));
    
    IF v_id IS NULL THEN
        -- Inserisci la nuova località
        INSERT INTO localita (comune_nome, nome, tipo, civico) 
        VALUES (p_comune_nome, p_nome, p_tipo, p_civico)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Località % inserita con ID %', p_nome, v_id;
    ELSE
        RAISE NOTICE 'Località % già esistente con ID %', p_nome, v_id;
        -- Aggiorna i dati se necessario
        UPDATE localita SET tipo = p_tipo WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Funzione di supporto per inserire partite gestendo i duplicati
CREATE OR REPLACE FUNCTION inserisci_partita_sicura(
    p_comune_nome VARCHAR, 
    p_numero_partita INTEGER, 
    p_tipo VARCHAR, 
    p_data_impianto DATE, 
    p_stato VARCHAR DEFAULT 'attiva',
    p_numero_provenienza INTEGER DEFAULT NULL,
    p_data_chiusura DATE DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se la partita esiste già
    SELECT id INTO v_id FROM partita 
    WHERE comune_nome = p_comune_nome AND numero_partita = p_numero_partita;
    
    IF v_id IS NULL THEN
        -- Inserisci la nuova partita
        INSERT INTO partita (comune_nome, numero_partita, tipo, data_impianto, stato, numero_provenienza, data_chiusura) 
        VALUES (p_comune_nome, p_numero_partita, p_tipo, p_data_impianto, p_stato, p_numero_provenienza, p_data_chiusura)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Partita % del comune % inserita con ID %', p_numero_partita, p_comune_nome, v_id;
    ELSE
        RAISE NOTICE 'Partita % del comune % già esistente con ID %', p_numero_partita, p_comune_nome, v_id;
        -- Aggiorna i dati se necessario
        UPDATE partita SET 
            tipo = p_tipo,
            data_impianto = p_data_impianto,
            stato = p_stato,
            numero_provenienza = p_numero_provenienza,
            data_chiusura = p_data_chiusura
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Funzione di supporto per collegare partite e possessori
CREATE OR REPLACE FUNCTION collega_partita_possessore(
    p_partita_id INTEGER, 
    p_possessore_id INTEGER, 
    p_tipo_partita VARCHAR, 
    p_titolo VARCHAR DEFAULT 'proprietà esclusiva',
    p_quota VARCHAR DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se il collegamento esiste già
    SELECT id INTO v_id FROM partita_possessore 
    WHERE partita_id = p_partita_id AND possessore_id = p_possessore_id;
    
    IF v_id IS NULL THEN
        -- Crea il nuovo collegamento
        INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) 
        VALUES (p_partita_id, p_possessore_id, p_tipo_partita, p_titolo, p_quota)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Collegamento partita-possessore creato con ID %', v_id;
    ELSE
        RAISE NOTICE 'Collegamento partita-possessore già esistente con ID %', v_id;
        -- Aggiorna i dati se necessario
        UPDATE partita_possessore 
        SET tipo_partita = p_tipo_partita,
            titolo = p_titolo, 
            quota = p_quota
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Funzione di supporto per inserire immobili gestendo i duplicati
CREATE OR REPLACE FUNCTION inserisci_immobile_sicuro(
    p_partita_id INTEGER, 
    p_localita_id INTEGER, 
    p_natura VARCHAR, 
    p_numero_piani INTEGER DEFAULT NULL, 
    p_numero_vani INTEGER DEFAULT NULL, 
    p_consistenza VARCHAR DEFAULT NULL, 
    p_classificazione VARCHAR DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se l'immobile esiste già (in base alla partita, località e natura)
    SELECT id INTO v_id FROM immobile 
    WHERE partita_id = p_partita_id AND localita_id = p_localita_id AND natura = p_natura;
    
    IF v_id IS NULL THEN
        -- Inserisci il nuovo immobile
        INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) 
        VALUES (p_partita_id, p_localita_id, p_natura, p_numero_piani, p_numero_vani, p_consistenza, p_classificazione)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Immobile % inserito con ID %', p_natura, v_id;
    ELSE
        RAISE NOTICE 'Immobile % già esistente con ID %', p_natura, v_id;
        -- Aggiorna i dati se necessario
        UPDATE immobile 
        SET numero_piani = COALESCE(p_numero_piani, numero_piani),
            numero_vani = COALESCE(p_numero_vani, numero_vani),
            consistenza = COALESCE(p_consistenza, consistenza),
            classificazione = COALESCE(p_classificazione, classificazione)
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Funzione di supporto per inserire variazioni gestendo i duplicati
CREATE OR REPLACE FUNCTION inserisci_variazione_sicura(
    p_partita_origine_id INTEGER, 
    p_partita_destinazione_id INTEGER, 
    p_tipo VARCHAR, 
    p_data_variazione DATE, 
    p_numero_riferimento VARCHAR DEFAULT NULL, 
    p_nominativo_riferimento VARCHAR DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se la variazione esiste già
    SELECT id INTO v_id FROM variazione 
    WHERE partita_origine_id = p_partita_origine_id 
      AND (partita_destinazione_id = p_partita_destinazione_id OR 
           (partita_destinazione_id IS NULL AND p_partita_destinazione_id IS NULL))
      AND data_variazione = p_data_variazione;
    
    IF v_id IS NULL THEN
        -- Inserisci la nuova variazione
        INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento) 
        VALUES (p_partita_origine_id, p_partita_destinazione_id, p_tipo, p_data_variazione, p_numero_riferimento, p_nominativo_riferimento)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Variazione inserita con ID %', v_id;
    ELSE
        RAISE NOTICE 'Variazione già esistente con ID %', v_id;
        -- Aggiorna i dati se necessario
        UPDATE variazione 
        SET tipo = p_tipo,
            numero_riferimento = COALESCE(p_numero_riferimento, numero_riferimento),
            nominativo_riferimento = COALESCE(p_nominativo_riferimento, nominativo_riferimento)
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Funzione di supporto per inserire contratti gestendo i duplicati
CREATE OR REPLACE FUNCTION inserisci_contratto_sicuro(
    p_variazione_id INTEGER, 
    p_tipo VARCHAR, 
    p_data_contratto DATE, 
    p_notaio VARCHAR DEFAULT NULL, 
    p_repertorio VARCHAR DEFAULT NULL, 
    p_note TEXT DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se il contratto esiste già
    SELECT id INTO v_id FROM contratto WHERE variazione_id = p_variazione_id;
    
    IF v_id IS NULL THEN
        -- Inserisci il nuovo contratto
        INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note) 
        VALUES (p_variazione_id, p_tipo, p_data_contratto, p_notaio, p_repertorio, p_note)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Contratto inserito con ID %', v_id;
    ELSE
        RAISE NOTICE 'Contratto già esistente con ID %', v_id;
        -- Aggiorna i dati se necessario
        UPDATE contratto 
        SET tipo = p_tipo,
            data_contratto = p_data_contratto,
            notaio = COALESCE(p_notaio, notaio),
            repertorio = COALESCE(p_repertorio, repertorio),
            note = COALESCE(p_note, note)
        WHERE id = v_id;
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- Funzione di supporto per inserire consultazioni gestendo i duplicati
CREATE OR REPLACE FUNCTION inserisci_consultazione_sicura(
    p_data DATE, 
    p_richiedente VARCHAR, 
    p_documento_identita VARCHAR DEFAULT NULL, 
    p_motivazione TEXT DEFAULT NULL, 
    p_materiale_consultato TEXT DEFAULT NULL,
    p_funzionario_autorizzante VARCHAR DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
BEGIN
    -- Verifica se la consultazione esiste già (stessa data e richiedente)
    SELECT id INTO v_id FROM consultazione 
    WHERE data = p_data AND richiedente = p_richiedente AND materiale_consultato = p_materiale_consultato;
    
    IF v_id IS NULL THEN
        -- Inserisci la nuova consultazione
        INSERT INTO consultazione (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante) 
        VALUES (p_data, p_richiedente, p_documento_identita, p_motivazione, p_materiale_consultato, p_funzionario_autorizzante)
        RETURNING id INTO v_id;
        RAISE NOTICE 'Consultazione inserita con ID %', v_id;
    ELSE
        RAISE NOTICE 'Consultazione già esistente con ID %', v_id;
        -- Non aggiorniamo i dati esistenti per mantenere l'integrità storica
    END IF;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- SEZIONE 2: INSERIMENTO DATI PRINCIPALI
-- =====================================================

-- Inserimento Comuni con gestione duplicati
SELECT inserisci_comune_sicuro('Carcare', 'Savona', 'Liguria');
SELECT inserisci_comune_sicuro('Cairo Montenotte', 'Savona', 'Liguria');
SELECT inserisci_comune_sicuro('Altare', 'Savona', 'Liguria');
SELECT inserisci_comune_sicuro('Millesimo', 'Savona', 'Liguria');
SELECT inserisci_comune_sicuro('Cengio', 'Savona', 'Liguria');
SELECT inserisci_comune_sicuro('Cosseria', 'Savona', 'Liguria');
SELECT inserisci_comune_sicuro('Mallare', 'Savona', 'Liguria');

-- Inserimento Registri Partite con gestione duplicati
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Carcare
    SELECT COUNT(*) INTO v_count FROM registro_partite WHERE comune_nome = 'Carcare' AND anno_impianto = 1950;
    IF v_count = 0 THEN
        INSERT INTO registro_partite (comune_nome, anno_impianto, numero_volumi, stato_conservazione) 
        VALUES ('Carcare', 1950, 3, 'Buono');
        RAISE NOTICE 'Registro partite di Carcare inserito';
    ELSE
        RAISE NOTICE 'Registro partite di Carcare già esistente';
    END IF;
    
    -- Cairo Montenotte
    SELECT COUNT(*) INTO v_count FROM registro_partite WHERE comune_nome = 'Cairo Montenotte' AND anno_impianto = 1948;
    IF v_count = 0 THEN
        INSERT INTO registro_partite (comune_nome, anno_impianto, numero_volumi, stato_conservazione) 
        VALUES ('Cairo Montenotte', 1948, 5, 'Discreto');
        RAISE NOTICE 'Registro partite di Cairo Montenotte inserito';
    ELSE
        RAISE NOTICE 'Registro partite di Cairo Montenotte già esistente';
    END IF;
    
    -- Altare
    SELECT COUNT(*) INTO v_count FROM registro_partite WHERE comune_nome = 'Altare' AND anno_impianto = 1952;
    IF v_count = 0 THEN
        INSERT INTO registro_partite (comune_nome, anno_impianto, numero_volumi, stato_conservazione) 
        VALUES ('Altare', 1952, 2, 'Ottimo');
        RAISE NOTICE 'Registro partite di Altare inserito';
    ELSE
        RAISE NOTICE 'Registro partite di Altare già esistente';
    END IF;
    
    -- Millesimo
    SELECT COUNT(*) INTO v_count FROM registro_partite WHERE comune_nome = 'Millesimo' AND anno_impianto = 1949;
    IF v_count = 0 THEN
        INSERT INTO registro_partite (comune_nome, anno_impianto, numero_volumi, stato_conservazione) 
        VALUES ('Millesimo', 1949, 4, 'Buono');
        RAISE NOTICE 'Registro partite di Millesimo inserito';
    ELSE
        RAISE NOTICE 'Registro partite di Millesimo già esistente';
    END IF;
    
    -- Cengio
    SELECT COUNT(*) INTO v_count FROM registro_partite WHERE comune_nome = 'Cengio' AND anno_impianto = 1951;
    IF v_count = 0 THEN
        INSERT INTO registro_partite (comune_nome, anno_impianto, numero_volumi, stato_conservazione) 
        VALUES ('Cengio', 1951, 3, 'Discreto');
        RAISE NOTICE 'Registro partite di Cengio inserito';
    ELSE
        RAISE NOTICE 'Registro partite di Cengio già esistente';
    END IF;
END $;

-- Inserimento Immobili con gestione duplicati
-- Carcare
SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 221), 
    (SELECT id FROM localita WHERE comune_nome = 'Carcare' AND nome = 'Regione Vista'), 
    'Molino da cereali', 2, NULL, '150 mq', 'Artigianale'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 219), 
    (SELECT id FROM localita WHERE comune_nome = 'Carcare' AND nome = 'Via Giuseppe Verdi' AND civico = 12), 
    'Casa', 3, 8, '210 mq', 'Abitazione civile'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 245), 
    (SELECT id FROM localita WHERE comune_nome = 'Carcare' AND nome = 'Via Roma' AND civico = 5), 
    'Magazzino', 1, NULL, '80 mq', 'Deposito'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 256), 
    (SELECT id FROM localita WHERE comune_nome = 'Carcare' AND nome = 'Via Garibaldi' AND civico = 23), 
    'Casa', 2, 6, '160 mq', 'Abitazione civile'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 267), 
    (SELECT id FROM localita WHERE comune_nome = 'Carcare' AND nome = 'Piazza Caravadossi' AND civico = 1), 
    'Negozio', 1, NULL, '85 mq', 'Commerciale'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 284), 
    (SELECT id FROM localita WHERE comune_nome = 'Carcare' AND nome = 'Via Castellani' AND civico = 7), 
    'Casa', 3, 10, '240 mq', 'Abitazione civile'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 293), 
    (SELECT id FROM localita WHERE comune_nome = 'Carcare' AND nome = 'Regione Cirietta'), 
    'Terreno agricolo', NULL, NULL, '5000 mq', 'Agricolo'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 301), 
    (SELECT id FROM localita WHERE comune_nome = 'Carcare' AND nome = 'Località Vispa'), 
    'Fabbricato rurale', 2, 4, '120 mq', 'Abitazione rurale'
);

-- Cairo Montenotte
SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 112), 
    (SELECT id FROM localita WHERE comune_nome = 'Cairo Montenotte' AND nome = 'Borgata Ferrere'), 
    'Fabbricato rurale', 2, 5, '180 mq', 'Abitazione rurale'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 118), 
    (SELECT id FROM localita WHERE comune_nome = 'Cairo Montenotte' AND nome = 'Strada Provinciale' AND civico = 76), 
    'Casa', 2, 6, '160 mq', 'Abitazione civile'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 125), 
    (SELECT id FROM localita WHERE comune_nome = 'Cairo Montenotte' AND nome = 'Via Roma' AND civico = 18), 
    'Casa', 4, 12, '320 mq', 'Abitazione civile'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 132), 
    (SELECT id FROM localita WHERE comune_nome = 'Cairo Montenotte' AND nome = 'Corso Dante' AND civico = 25), 
    'Negozio con abitazione', 2, 8, '200 mq', 'Misto'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 143), 
    (SELECT id FROM localita WHERE comune_nome = 'Cairo Montenotte' AND nome = 'Frazione Rocchetta'), 
    'Fabbricato industriale', 1, NULL, '500 mq', 'Industriale'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 156), 
    (SELECT id FROM localita WHERE comune_nome = 'Cairo Montenotte' AND nome = 'Località Carnovale'), 
    'Terreno agricolo', NULL, NULL, '8000 mq', 'Agricolo'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 187), 
    (SELECT id FROM localita WHERE comune_nome = 'Cairo Montenotte' AND nome = 'Via Roma' AND civico = 18), 
    'Magazzino', 1, NULL, '60 mq', 'Deposito'
);

-- Altare
SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 87), 
    (SELECT id FROM localita WHERE comune_nome = 'Altare' AND nome = 'Via Palermo' AND civico = 22), 
    'Laboratorio', 1, NULL, '120 mq', 'Artigianale'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 92), 
    (SELECT id FROM localita WHERE comune_nome = 'Altare' AND nome = 'Piazza Consolato' AND civico = 3), 
    'Casa', 3, 9, '230 mq', 'Abitazione civile'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 96), 
    (SELECT id FROM localita WHERE comune_nome = 'Altare' AND nome = 'Via Roma' AND civico = 8), 
    'Negozio', 1, NULL, '70 mq', 'Commerciale'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 104), 
    (SELECT id FROM localita WHERE comune_nome = 'Altare' AND nome = 'Regione Acque'), 
    'Terreno agricolo', NULL, NULL, '3000 mq', 'Agricolo'
);

-- Millesimo
SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Millesimo' AND numero_partita = 45), 
    (SELECT id FROM localita WHERE comune_nome = 'Millesimo' AND nome = 'Piazza Italia' AND civico = 1), 
    'Palazzo storico', 4, 20, '650 mq', 'Abitazione signorile'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Millesimo' AND numero_partita = 52), 
    (SELECT id FROM localita WHERE comune_nome = 'Millesimo' AND nome = 'Via Partigiani' AND civico = 15), 
    'Casa', 2, 7, '175 mq', 'Abitazione civile'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Millesimo' AND numero_partita = 68), 
    (SELECT id FROM localita WHERE comune_nome = 'Millesimo' AND nome = 'Località Acquafredda'), 
    'Molino da cereali', 2, NULL, '140 mq', 'Artigianale'
);

-- Cengio
SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Cengio' AND numero_partita = 123), 
    (SELECT id FROM localita WHERE comune_nome = 'Cengio' AND nome = 'Via Bormida' AND civico = 7), 
    'Casa', 2, 6, '160 mq', 'Abitazione civile'
);

SELECT inserisci_immobile_sicuro(
    (SELECT id FROM partita WHERE comune_nome = 'Cengio' AND numero_partita = 128), 
    (SELECT id FROM localita WHERE comune_nome = 'Cengio' AND nome = 'Località Genepro'), 
    'Fabbricato rurale', 1, 3, '90 mq', 'Abitazione rurale'
);

-- Inserimento Variazioni
-- Variazione 1: Successione Ferraro
SELECT inserisci_variazione_sicura(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 118), 
    NULL, 
    'Successione', 
    '1952-08-15', 
    '22/52', 
    'Ferraro Caterina'
);

-- Variazione 2: Vendita terreno
SELECT inserisci_variazione_sicura(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 301), 
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 221), 
    'Vendita', 
    '1954-08-22', 
    '45/54', 
    'Fossati Angelo a Barberis Giovanni'
);

-- Variazione 3: Successione Del Carretto
SELECT inserisci_variazione_sicura(
    (SELECT id FROM partita WHERE comune_nome = 'Millesimo' AND numero_partita = 68), 
    NULL, 
    'Successione', 
    '1954-05-17', 
    '12/54', 
    'Del Carretto Francesco'
);

-- Variazione 4: Frazionamento terreno Berruti
SELECT inserisci_variazione_sicura(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 187), 
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 112), 
    'Frazionamento', 
    '1954-11-10', 
    '56/54', 
    'Berruti Antonio'
);

-- Inserimento Contratti con gestione duplicati
-- Contratto per la variazione 1
SELECT inserisci_contratto_sicuro(
    (SELECT id FROM variazione WHERE 
        partita_origine_id = (SELECT id FROM partita WHERE comune_nome = 'Millesimo' AND numero_partita = 68) 
        AND data_variazione = '1954-05-17'),
    'Successione', 
    '1954-05-10', 
    'Notaio Bianchi', 
    '203/54', 
    'Successione per morte del proprietario Francesco Del Carretto'
);

-- Contratto per la variazione 4
SELECT inserisci_contratto_sicuro(
    (SELECT id FROM variazione WHERE 
        partita_origine_id = (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 187) 
        AND data_variazione = '1954-11-10'),
    'Frazionamento', 
    '1954-11-05', 
    'Notaio Verdi', 
    '612/54', 
    'Frazionamento terreno in località Carnovale'
);

-- Inserimento Consultazioni con gestione duplicati
SELECT inserisci_consultazione_sicura(
    '2025-04-01', 
    'Mario Bianchi', 
    'CI AB1234567', 
    'Ricerca storica', 
    'Registro partite Carcare 1950', 
    'Dott. Verdi'
);

SELECT inserisci_consultazione_sicura(
    '2025-04-05', 
    'Studio Legale Rossi', 
    'Tessera Ordine 55213', 
    'Verifica proprietà', 
    'Partite 221 e 219 Carcare', 
    'Dott. Verdi'
);

SELECT inserisci_consultazione_sicura(
    '2025-04-08', 
    'Giovanna Neri', 
    'CI CD7890123', 
    'Ricerca genealogica', 
    'Possessori Cairo Montenotte', 
    'Dott.ssa Bianchi'
);

SELECT inserisci_consultazione_sicura(
    '2025-04-10', 
    'Università di Genova', 
    'Lettera richiesta 789/25', 
    'Ricerca storica urbanistica', 
    'Immobili centro storico Millesimo', 
    'Dott. Rossi'
);

SELECT inserisci_consultazione_sicura(
    '2025-04-12', 
    'Geom. Paolo Verdi', 
    'CI EF4567890', 
    'Verifica confini', 
    'Partita 128 Cengio', 
    'Dott.ssa Bianchi'
);

SELECT inserisci_consultazione_sicura(
    '2025-04-15', 
    'Mario Bianchi', 
    'CI AB1234567', 
    'Integrazione ricerca', 
    'Variazioni proprietà Carcare 1952-1954', 
    'Dott. Verdi'
);

-- =====================================================
-- SEZIONE 3: VERIFICA DEI DATI INSERITI E STATISTICHE
-- =====================================================

-- Verifica il numero totale di record per tabella
DO $
DECLARE
    v_comuni INTEGER;
    v_registri_partite INTEGER;
    v_registri_matricole INTEGER;
    v_possessori INTEGER;
    v_localita INTEGER;
    v_partite INTEGER;
    v_partite_possessori INTEGER;
    v_immobili INTEGER;
    v_variazioni INTEGER;
    v_contratti INTEGER;
    v_consultazioni INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_comuni FROM comune;
    SELECT COUNT(*) INTO v_registri_partite FROM registro_partite;
    SELECT COUNT(*) INTO v_registri_matricole FROM registro_matricole;
    SELECT COUNT(*) INTO v_possessori FROM possessore;
    SELECT COUNT(*) INTO v_localita FROM localita;
    SELECT COUNT(*) INTO v_partite FROM partita;
    SELECT COUNT(*) INTO v_partite_possessori FROM partita_possessore;
    SELECT COUNT(*) INTO v_immobili FROM immobile;
    SELECT COUNT(*) INTO v_variazioni FROM variazione;
    SELECT COUNT(*) INTO v_contratti FROM contratto;
    SELECT COUNT(*) INTO v_consultazioni FROM consultazione;
    
    RAISE NOTICE '=====================================================';
    RAISE NOTICE 'STATISTICHE DEL DATABASE CATASTO STORICO';
    RAISE NOTICE '=====================================================';
    RAISE NOTICE 'Comuni: %', v_comuni;
    RAISE NOTICE 'Registri Partite: %', v_registri_partite;
    RAISE NOTICE 'Registri Matricole: %', v_registri_matricole;
    RAISE NOTICE 'Possessori: %', v_possessori;
    RAISE NOTICE 'Località: %', v_localita;
    RAISE NOTICE 'Partite: %', v_partite;
    RAISE NOTICE 'Collegamenti Partite-Possessori: %', v_partite_possessori;
    RAISE NOTICE 'Immobili: %', v_immobili;
    RAISE NOTICE 'Variazioni: %', v_variazioni;
    RAISE NOTICE 'Contratti: %', v_contratti;
    RAISE NOTICE 'Consultazioni: %', v_consultazioni;
    RAISE NOTICE '=====================================================';
END $;

-- Verifica delle statistiche per comune
DO $
DECLARE
    r RECORD;
BEGIN
    RAISE NOTICE 'DISTRIBUZIONE PARTITE PER COMUNE:';
    RAISE NOTICE '-----------------------------------------------------';
    RAISE NOTICE '%-20s | %-10s | %-10s | %-10s', 'COMUNE', 'PARTITE', 'IMMOBILI', 'POSSESSORI';
    RAISE NOTICE '-----------------------------------------------------';
    
    FOR r IN (
        SELECT 
            c.nome AS comune, 
            COUNT(DISTINCT p.id) AS partite,
            COUNT(DISTINCT i.id) AS immobili,
            COUNT(DISTINCT pos.id) AS possessori
        FROM comune c
        LEFT JOIN partita p ON c.nome = p.comune_nome
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        LEFT JOIN immobile i ON p.id = i.partita_id
        GROUP BY c.nome
        ORDER BY partite DESC
    )
    LOOP
        RAISE NOTICE '%-20s | %-10s | %-10s | %-10s', 
                     r.comune, r.partite, r.immobili, r.possessori;
    END LOOP;
    RAISE NOTICE '-----------------------------------------------------';
END $;

-- Verifica delle tipologie di immobili
DO $
DECLARE
    r RECORD;
BEGIN
    RAISE NOTICE 'DISTRIBUZIONE IMMOBILI PER CLASSIFICAZIONE:';
    RAISE NOTICE '-----------------------------------------------------';
    RAISE NOTICE '%-25s | %-10s', 'CLASSIFICAZIONE', 'NUMERO';
    RAISE NOTICE '-----------------------------------------------------';
    
    FOR r IN (
        SELECT 
            classificazione, 
            COUNT(*) AS numero
        FROM immobile
        GROUP BY classificazione
        ORDER BY numero DESC
    )
    LOOP
        RAISE NOTICE '%-25s | %-10s', r.classificazione, r.numero;
    END LOOP;
    RAISE NOTICE '-----------------------------------------------------';
END $;

-- Elimina le funzioni di supporto 
DROP FUNCTION IF EXISTS inserisci_comune_sicuro(VARCHAR, VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS inserisci_possessore_sicuro(VARCHAR, VARCHAR, VARCHAR, VARCHAR, BOOLEAN);
DROP FUNCTION IF EXISTS inserisci_localita_sicura(VARCHAR, VARCHAR, VARCHAR, INTEGER);
DROP FUNCTION IF EXISTS inserisci_partita_sicura(VARCHAR, INTEGER, VARCHAR, DATE, VARCHAR, INTEGER, DATE);
DROP FUNCTION IF EXISTS collega_partita_possessore(INTEGER, INTEGER, VARCHAR, VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS inserisci_immobile_sicuro(INTEGER, INTEGER, VARCHAR, INTEGER, INTEGER, VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS inserisci_variazione_sicura(INTEGER, INTEGER, VARCHAR, DATE, VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS inserisci_contratto_sicuro(INTEGER, VARCHAR, DATE, VARCHAR, VARCHAR, TEXT);
DROP FUNCTION IF EXISTS inserisci_consultazione_sicura(DATE, VARCHAR, VARCHAR, TEXT, TEXT, VARCHAR);

RAISE NOTICE 'Inserimento dati di esempio completato con successo!';
Cairo Montenotte' AND numero_partita = 118) 
        AND data_variazione = '1952-08-15'),
    'Successione', 
    '1952-08-10', 
    'Notaio Rossi', 
    '1234/52', 
    'Successione per morte del proprietario Luigi Ferraro'
);

-- Contratto per la variazione 2
SELECT inserisci_contratto_sicuro(
    (SELECT id FROM variazione WHERE 
        partita_origine_id = (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 301) 
        AND data_variazione = '1954-08-22'),
    'Vendita', 
    '1954-08-15', 
    'Notaio Verdi', 
    '487/54', 
    'Vendita fabbricato rurale in Località Vispa'
);

-- Contratto per la variazione 3
SELECT inserisci_contratto_sicuro(
    (SELECT id FROM variazione WHERE 
        partita_origine_id = (SELECT id FROM partita WHERE comune_nome = '

-- Inserimento Registri Matricole con gestione duplicati
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Carcare
    SELECT COUNT(*) INTO v_count FROM registro_matricole WHERE comune_nome = 'Carcare' AND anno_impianto = 1950;
    IF v_count = 0 THEN
        INSERT INTO registro_matricole (comune_nome, anno_impianto, numero_volumi, stato_conservazione) 
        VALUES ('Carcare', 1950, 2, 'Buono');
        RAISE NOTICE 'Registro matricole di Carcare inserito';
    ELSE
        RAISE NOTICE 'Registro matricole di Carcare già esistente';
    END IF;
    
    -- Cairo Montenotte
    SELECT COUNT(*) INTO v_count FROM registro_matricole WHERE comune_nome = 'Cairo Montenotte' AND anno_impianto = 1948;
    IF v_count = 0 THEN
        INSERT INTO registro_matricole (comune_nome, anno_impianto, numero_volumi, stato_conservazione) 
        VALUES ('Cairo Montenotte', 1948, 4, 'Discreto');
        RAISE NOTICE 'Registro matricole di Cairo Montenotte inserito';
    ELSE
        RAISE NOTICE 'Registro matricole di Cairo Montenotte già esistente';
    END IF;
    
    -- Altare
    SELECT COUNT(*) INTO v_count FROM registro_matricole WHERE comune_nome = 'Altare' AND anno_impianto = 1952;
    IF v_count = 0 THEN
        INSERT INTO registro_matricole (comune_nome, anno_impianto, numero_volumi, stato_conservazione) 
        VALUES ('Altare', 1952, 1, 'Ottimo');
        RAISE NOTICE 'Registro matricole di Altare inserito';
    ELSE
        RAISE NOTICE 'Registro matricole di Altare già esistente';
    END IF;
    
    -- Millesimo
    SELECT COUNT(*) INTO v_count FROM registro_matricole WHERE comune_nome = 'Millesimo' AND anno_impianto = 1949;
    IF v_count = 0 THEN
        INSERT INTO registro_matricole (comune_nome, anno_impianto, numero_volumi, stato_conservazione) 
        VALUES ('Millesimo', 1949, 3, 'Buono');
        RAISE NOTICE 'Registro matricole di Millesimo inserito';
    ELSE
        RAISE NOTICE 'Registro matricole di Millesimo già esistente';
    END IF;
    
    -- Cengio
    SELECT COUNT(*) INTO v_count FROM registro_matricole WHERE comune_nome = 'Cengio' AND anno_impianto = 1951;
    IF v_count = 0 THEN
        INSERT INTO registro_matricole (comune_nome, anno_impianto, numero_volumi, stato_conservazione) 
        VALUES ('Cengio', 1951, 2, 'Discreto');
        RAISE NOTICE 'Registro matricole di Cengio inserito';
    ELSE
        RAISE NOTICE 'Registro matricole di Cengio già esistente';
    END IF;
END $$;
-- Inserimento Possessori con gestione duplicati
-- Carcare
SELECT inserisci_possessore_sicuro('Carcare', 'Fossati Angelo', 'fu Roberto', 'Fossati Angelo fu Roberto', true);
SELECT inserisci_possessore_sicuro('Carcare', 'Caviglia Maria', 'fu Giuseppe', 'Caviglia Maria fu Giuseppe', true);
SELECT inserisci_possessore_sicuro('Carcare', 'Barberis Giovanni', 'fu Paolo', 'Barberis Giovanni fu Paolo', true);
SELECT inserisci_possessore_sicuro('Carcare', 'De Rossi Gina', 'fu Vittorio', 'De Rossi Gina fu Vittorio', true);
SELECT inserisci_possessore_sicuro('Carcare', 'Bianchi Carlo', 'fu Antonio', 'Bianchi Carlo fu Antonio', true);
SELECT inserisci_possessore_sicuro('Carcare', 'Rossi Franco', 'fu Giuseppe', 'Rossi Franco fu Giuseppe', true);
SELECT inserisci_possessore_sicuro('Carcare', 'Ivaldi Luisa', 'fu Marco', 'Ivaldi Luisa fu Marco', true);

-- Cairo Montenotte
SELECT inserisci_possessore_sicuro('Cairo Montenotte', 'Berruti Antonio', 'fu Luigi', 'Berruti Antonio fu Luigi', true);
SELECT inserisci_possessore_sicuro('Cairo Montenotte', 'Ferraro Caterina', 'fu Marco', 'Ferraro Caterina fu Marco', true);
SELECT inserisci_possessore_sicuro('Cairo Montenotte', 'Valbonesi Pietro', 'fu Cesare', 'Valbonesi Pietro fu Cesare', true);
SELECT inserisci_possessore_sicuro('Cairo Montenotte', 'Zunino Maria', 'fu Carlo', 'Zunino Maria fu Carlo', true);
SELECT inserisci_possessore_sicuro('Cairo Montenotte', 'Gallo Stefano', 'fu Domenico', 'Gallo Stefano fu Domenico', true);

-- Altare
SELECT inserisci_possessore_sicuro('Altare', 'Bormioli Pietro', 'fu Carlo', 'Bormioli Pietro fu Carlo', true);
SELECT inserisci_possessore_sicuro('Altare', 'Saroldi Anna', 'fu Giovanni', 'Saroldi Anna fu Giovanni', true);
SELECT inserisci_possessore_sicuro('Altare', 'Torterolo Bruno', 'fu Alfonso', 'Torterolo Bruno fu Alfonso', true);

-- Millesimo
SELECT inserisci_possessore_sicuro('Millesimo', 'Del Carretto Francesco', 'fu Alfonso', 'Del Carretto Francesco fu Alfonso', true);
SELECT inserisci_possessore_sicuro('Millesimo', 'Astesiano Rosa', 'fu Pietro', 'Astesiano Rosa fu Pietro', true);
SELECT inserisci_possessore_sicuro('Millesimo', 'Perlini Alberto', 'fu Cesare', 'Perlini Alberto fu Cesare', true);

-- Cengio
SELECT inserisci_possessore_sicuro('Cengio', 'Marenco Luigi', 'fu Mario', 'Marenco Luigi fu Mario', true);
SELECT inserisci_possessore_sicuro('Cengio', 'Bertola Elena', 'fu Giovanni', 'Bertola Elena fu Giovanni', true);

-- Inserimento Località con gestione duplicati
-- Carcare
SELECT inserisci_localita_sicura('Carcare', 'Regione Vista', 'regione', NULL);
SELECT inserisci_localita_sicura('Carcare', 'Via Giuseppe Verdi', 'via', 12);
SELECT inserisci_localita_sicura('Carcare', 'Via Roma', 'via', 5);
SELECT inserisci_localita_sicura('Carcare', 'Via Garibaldi', 'via', 23);
SELECT inserisci_localita_sicura('Carcare', 'Piazza Caravadossi', 'via', 1);
SELECT inserisci_localita_sicura('Carcare', 'Via Castellani', 'via', 7);
SELECT inserisci_localita_sicura('Carcare', 'Regione Cirietta', 'regione', NULL);
SELECT inserisci_localita_sicura('Carcare', 'Località Vispa', 'borgata', NULL);

-- Cairo Montenotte
SELECT inserisci_localita_sicura('Cairo Montenotte', 'Borgata Ferrere', 'borgata', NULL);
SELECT inserisci_localita_sicura('Cairo Montenotte', 'Strada Provinciale', 'via', 76);
SELECT inserisci_localita_sicura('Cairo Montenotte', 'Via Roma', 'via', 18);
SELECT inserisci_localita_sicura('Cairo Montenotte', 'Corso Dante', 'via', 25);
SELECT inserisci_localita_sicura('Cairo Montenotte', 'Frazione Rocchetta', 'borgata', NULL);
SELECT inserisci_localita_sicura('Cairo Montenotte', 'Località Carnovale', 'borgata', NULL);

-- Altare
SELECT inserisci_localita_sicura('Altare', 'Via Palermo', 'via', 22);
SELECT inserisci_localita_sicura('Altare', 'Piazza Consolato', 'via', 3);
SELECT inserisci_localita_sicura('Altare', 'Via Roma', 'via', 8);
SELECT inserisci_localita_sicura('Altare', 'Regione Acque', 'regione', NULL);

-- Millesimo
SELECT inserisci_localita_sicura('Millesimo', 'Piazza Italia', 'via', 1);
SELECT inserisci_localita_sicura('Millesimo', 'Via Partigiani', 'via', 15);
SELECT inserisci_localita_sicura('Millesimo', 'Località Acquafredda', 'borgata', NULL);

-- Cengio
SELECT inserisci_localita_sicura('Cengio', 'Via Bormida', 'via', 7);
SELECT inserisci_localita_sicura('Cengio', 'Località Genepro', 'borgata', NULL);

-- Inserimento Partite con gestione duplicati
-- Carcare
SELECT inserisci_partita_sicura('Carcare', 221, 'principale', '1950-05-10', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Carcare', 219, 'principale', '1950-05-10', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Carcare', 245, 'secondaria', '1951-03-22', 'attiva', 219, NULL);
SELECT inserisci_partita_sicura('Carcare', 256, 'principale', '1951-06-15', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Carcare', 267, 'principale', '1951-09-03', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Carcare', 284, 'principale', '1952-02-21', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Carcare', 293, 'secondaria', '1952-05-14', 'attiva', 267, NULL);
SELECT inserisci_partita_sicura('Carcare', 301, 'principale', '1952-11-30', 'inattiva', NULL, '1954-08-22');

-- Cairo Montenotte
SELECT inserisci_partita_sicura('Cairo Montenotte', 112, 'principale', '1948-11-05', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Cairo Montenotte', 118, 'principale', '1949-01-15', 'inattiva', NULL, '1953-06-22');
SELECT inserisci_partita_sicura('Cairo Montenotte', 125, 'principale', '1949-03-18', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Cairo Montenotte', 132, 'principale', '1949-07-04', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Cairo Montenotte', 143, 'principale', '1949-10-21', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Cairo Montenotte', 156, 'secondaria', '1950-04-17', 'attiva', 143, NULL);
SELECT inserisci_partita_sicura('Cairo Montenotte', 187, 'principale', '1951-02-28', 'inattiva', NULL, '1954-11-10');

-- Altare
SELECT inserisci_partita_sicura('Altare', 87, 'principale', '1952-07-03', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Altare', 92, 'principale', '1952-08-19', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Altare', 96, 'principale', '1952-09-25', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Altare', 104, 'secondaria', '1953-01-12', 'attiva', 92, NULL);

-- Millesimo
SELECT inserisci_partita_sicura('Millesimo', 45, 'principale', '1949-06-14', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Millesimo', 52, 'principale', '1949-09-30', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Millesimo', 68, 'principale', '1950-03-11', 'inattiva', NULL, '1954-05-17');

-- Cengio
SELECT inserisci_partita_sicura('Cengio', 123, 'principale', '1951-04-22', 'attiva', NULL, NULL);
SELECT inserisci_partita_sicura('Cengio', 128, 'principale', '1951-07-19', 'attiva', NULL, NULL);

-- Associazione Partite-Possessori con gestione duplicati
-- Carcare
SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 221), 
    (SELECT id FROM possessore WHERE nome_completo = 'Fossati Angelo fu Roberto'), 
    'principale', 'proprietà esclusiva', NULL
);

-- Cairo Montenotte
SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 112), 
    (SELECT id FROM possessore WHERE nome_completo = 'Berruti Antonio fu Luigi'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 118), 
    (SELECT id FROM possessore WHERE nome_completo = 'Ferraro Caterina fu Marco'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 125), 
    (SELECT id FROM possessore WHERE nome_completo = 'Valbonesi Pietro fu Cesare'), 
    'principale', 'comproprietà', '1/2'
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 125), 
    (SELECT id FROM possessore WHERE nome_completo = 'Zunino Maria fu Carlo'), 
    'principale', 'comproprietà', '1/2'
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 132), 
    (SELECT id FROM possessore WHERE nome_completo = 'Gallo Stefano fu Domenico'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 143), 
    (SELECT id FROM possessore WHERE nome_completo = 'Berruti Antonio fu Luigi'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 156), 
    (SELECT id FROM possessore WHERE nome_completo = 'Berruti Antonio fu Luigi'), 
    'secondaria', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 187), 
    (SELECT id FROM possessore WHERE nome_completo = 'Ferraro Caterina fu Marco'), 
    'principale', 'proprietà esclusiva', NULL
);

-- Altare
SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 87), 
    (SELECT id FROM possessore WHERE nome_completo = 'Bormioli Pietro fu Carlo'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 92), 
    (SELECT id FROM possessore WHERE nome_completo = 'Saroldi Anna fu Giovanni'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 96), 
    (SELECT id FROM possessore WHERE nome_completo = 'Torterolo Bruno fu Alfonso'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 104), 
    (SELECT id FROM possessore WHERE nome_completo = 'Saroldi Anna fu Giovanni'), 
    'secondaria', 'proprietà esclusiva', NULL
);

-- Millesimo
SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Millesimo' AND numero_partita = 45), 
    (SELECT id FROM possessore WHERE nome_completo = 'Del Carretto Francesco fu Alfonso'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Millesimo' AND numero_partita = 52), 
    (SELECT id FROM possessore WHERE nome_completo = 'Astesiano Rosa fu Pietro'), 
    'principale', 'comproprietà', '1/2'
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Millesimo' AND numero_partita = 52), 
    (SELECT id FROM possessore WHERE nome_completo = 'Perlini Alberto fu Cesare'), 
    'principale', 'comproprietà', '1/2'
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Millesimo' AND numero_partita = 68), 
    (SELECT id FROM possessore WHERE nome_completo = 'Del Carretto Francesco fu Alfonso'), 
    'principale', 'proprietà esclusiva', NULL
);

-- Cengio
SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Cengio' AND numero_partita = 123), 
    (SELECT id FROM possessore WHERE nome_completo = 'Marenco Luigi fu Mario'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Cengio' AND numero_partita = 128), 
    (SELECT id FROM possessore WHERE nome_completo = 'Bertola Elena fu Giovanni'), 
    'principale', 'proprietà esclusiva', NULL
);

-- Relazioni tra partite (principale-secondaria)
DO $
DECLARE
    v_count INTEGER;
BEGIN
    -- Carcare: partita 219 collegata a partita 245
    SELECT COUNT(*) INTO v_count FROM partita_relazione 
    WHERE partita_principale_id = (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 219)
    AND partita_secondaria_id = (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 245);
    
    IF v_count = 0 THEN
        INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id) 
        VALUES(
            (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 219),
            (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 245)
        );
        RAISE NOTICE 'Relazione tra partite 219 e 245 di Carcare inserita';
    ELSE
        RAISE NOTICE 'Relazione tra partite 219 e 245 di Carcare già esistente';
    END IF;
    
    -- Carcare: partita 267 collegata a partita 293
    SELECT COUNT(*) INTO v_count FROM partita_relazione 
    WHERE partita_principale_id = (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 267)
    AND partita_secondaria_id = (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 293);
    
    IF v_count = 0 THEN
        INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id) 
        VALUES(
            (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 267),
            (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 293)
        );
        RAISE NOTICE 'Relazione tra partite 267 e 293 di Carcare inserita';
    ELSE
        RAISE NOTICE 'Relazione tra partite 267 e 293 di Carcare già esistente';
    END IF;
    
    -- Cairo Montenotte: partita 143 collegata a partita 156
    SELECT COUNT(*) INTO v_count FROM partita_relazione 
    WHERE partita_principale_id = (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 143)
    AND partita_secondaria_id = (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 156);
    
    IF v_count = 0 THEN
        INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id) 
        VALUES(
            (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 143),
            (SELECT id FROM partita WHERE comune_nome = 'Cairo Montenotte' AND numero_partita = 156)
        );
        RAISE NOTICE 'Relazione tra partite 143 e 156 di Cairo Montenotte inserita';
    ELSE
        RAISE NOTICE 'Relazione tra partite 143 e 156 di Cairo Montenotte già esistente';
    END IF;
    
    -- Altare: partita 92 collegata a partita 104
    SELECT COUNT(*) INTO v_count FROM partita_relazione 
    WHERE partita_principale_id = (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 92)
    AND partita_secondaria_id = (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 104);
    
    IF v_count = 0 THEN
        INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id) 
        VALUES(
            (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 92),
            (SELECT id FROM partita WHERE comune_nome = 'Altare' AND numero_partita = 104)
        );
        RAISE NOTICE 'Relazione tra partite 92 e 104 di Altare inserita';
    ELSE
        RAISE NOTICE 'Relazione tra partite 92 e 104 di Altare già esistente';
    END IF;
END $;

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 219), 
    (SELECT id FROM possessore WHERE nome_completo = 'Caviglia Maria fu Giuseppe'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 245), 
    (SELECT id FROM possessore WHERE nome_completo = 'Barberis Giovanni fu Paolo'), 
    'secondaria', 'comproprietà', '1/2'
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 245), 
    (SELECT id FROM possessore WHERE nome_completo = 'Caviglia Maria fu Giuseppe'), 
    'secondaria', 'comproprietà', '1/2'
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 256), 
    (SELECT id FROM possessore WHERE nome_completo = 'De Rossi Gina fu Vittorio'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 267), 
    (SELECT id FROM possessore WHERE nome_completo = 'Bianchi Carlo fu Antonio'), 
    'principale', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 284), 
    (SELECT id FROM possessore WHERE nome_completo = 'Rossi Franco fu Giuseppe'), 
    'principale', 'comproprietà', '2/3'
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 284), 
    (SELECT id FROM possessore WHERE nome_completo = 'Ivaldi Luisa fu Marco'), 
    'principale', 'comproprietà', '1/3'
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 293), 
    (SELECT id FROM possessore WHERE nome_completo = 'Bianchi Carlo fu Antonio'), 
    'secondaria', 'proprietà esclusiva', NULL
);

SELECT collega_partita_possessore(
    (SELECT id FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 301), 
    (SELECT id FROM possessore WHERE nome_completo = 'Fossati Angelo fu Roberto'), 
    'principale', 'proprietà esclusiva', NULL
);