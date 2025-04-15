-- Imposta lo schema
SET search_path TO catasto;

/*
 * PROCEDURE PER WORKFLOW INTEGRATI
 * per il Catasto Storico 
 * Versione 1.0 - 13/04/2025
 */

------------------------------------------------------------------------------
-- SEZIONE 1: WORKFLOW COMPLETI DI REGISTRAZIONE PROPRIETÀ
------------------------------------------------------------------------------

-- Procedura per la registrazione completa di una nuova proprietà
-- Include inserimento possessori, partita, località e immobili in un'unica transazione
CREATE OR REPLACE PROCEDURE registra_nuova_proprieta(
    -- Parametri per la partita
    p_comune_nome VARCHAR(100),
    p_numero_partita INTEGER,
    p_data_impianto DATE,
    -- Parametri per i possessori (array di record)
    p_possessori JSON,  -- [{"nome_completo": "...", "cognome_nome": "...", "paternita": "...", "quota": "..."}]
    -- Parametri per gli immobili
    p_immobili JSON     -- [{"natura": "...", "localita": "...", "tipo_localita": "...", "classificazione": "..."}]
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita_id INTEGER;
    v_possessore_id INTEGER;
    v_localita_id INTEGER;
    v_possessore RECORD;
    v_immobile RECORD;
    v_possessore_ids INTEGER[] := '{}';
BEGIN
    -- Verifiche preliminari
    IF NOT EXISTS (SELECT 1 FROM comune WHERE nome = p_comune_nome) THEN
        RAISE EXCEPTION 'Il comune % non esiste', p_comune_nome;
    END IF;
    
    IF EXISTS (SELECT 1 FROM partita WHERE comune_nome = p_comune_nome AND numero_partita = p_numero_partita) THEN
        RAISE EXCEPTION 'La partita % già esiste nel comune %', p_numero_partita, p_comune_nome;
    END IF;
    
    -- Inserisci o recupera i possessori
    FOR v_possessore IN SELECT * FROM json_to_recordset(p_possessori) 
        AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT)
    LOOP
        -- Verifica se il possessore esiste già
        SELECT id INTO v_possessore_id 
        FROM possessore 
        WHERE comune_nome = p_comune_nome AND nome_completo = v_possessore.nome_completo;
        
        IF NOT FOUND THEN
            -- Crea un nuovo possessore
            INSERT INTO possessore(comune_nome, cognome_nome, paternita, nome_completo, attivo)
            VALUES (p_comune_nome, v_possessore.cognome_nome, v_possessore.paternita, v_possessore.nome_completo, TRUE)
            RETURNING id INTO v_possessore_id;
        END IF;
        
        -- Aggiungi all'array dei possessori
        v_possessore_ids := array_append(v_possessore_ids, v_possessore_id);
    END LOOP;
    
    -- Crea la partita
    INSERT INTO partita(comune_nome, numero_partita, tipo, data_impianto, stato)
    VALUES (p_comune_nome, p_numero_partita, 'principale', p_data_impianto, 'attiva')
    RETURNING id INTO v_partita_id;
    
    -- Collega i possessori alla partita
    FOR i IN 1..array_length(v_possessore_ids, 1)
    LOOP
        v_possessore_id := v_possessore_ids[i];
        
        -- Estrai la quota dal JSON originale
        SELECT quota INTO v_possessore FROM json_to_recordset(p_possessori) 
        AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT)
        OFFSET (i-1) LIMIT 1;
        
        -- Determina il titolo in base alla quota
        INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
        VALUES (
            v_partita_id, 
            v_possessore_id, 
            'principale',
            CASE WHEN v_possessore.quota IS NULL THEN 'proprietà esclusiva' ELSE 'comproprietà' END,
            v_possessore.quota
        );
    END LOOP;
    
    -- Crea gli immobili
    FOR v_immobile IN SELECT * FROM json_to_recordset(p_immobili) 
        AS x(natura TEXT, localita TEXT, tipo_localita TEXT, classificazione TEXT, numero_piani INTEGER, numero_vani INTEGER, consistenza TEXT)
    LOOP
        -- Verifica se la località esiste
        SELECT id INTO v_localita_id 
        FROM localita 
        WHERE comune_nome = p_comune_nome AND nome = v_immobile.localita;
        
        IF NOT FOUND THEN
            -- Crea una nuova località
            INSERT INTO localita(comune_nome, nome, tipo)
            VALUES (p_comune_nome, v_immobile.localita, COALESCE(v_immobile.tipo_localita, 'regione'))
            RETURNING id INTO v_localita_id;
        END IF;
        
        -- Crea l'immobile
        INSERT INTO immobile(partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
        VALUES (
            v_partita_id,
            v_localita_id,
            v_immobile.natura,
            v_immobile.numero_piani,
            v_immobile.numero_vani,
            v_immobile.consistenza,
            v_immobile.classificazione
        );
    END LOOP;
    
    RAISE NOTICE 'Registrazione completata con successo. Partita % creata con ID %', p_numero_partita, v_partita_id;
END;
$$;

-- Procedura per la registrazione di un passaggio di proprietà completo
CREATE OR REPLACE PROCEDURE registra_passaggio_proprieta(
    -- Partita di origine
    p_partita_origine_id INTEGER,
    -- Informazioni nuova partita
    p_comune_nome VARCHAR(100),
    p_numero_partita INTEGER,
    -- Dati della variazione
    p_tipo_variazione VARCHAR(50),
    p_data_variazione DATE,
    -- Dati contratto
    p_tipo_contratto VARCHAR(50),
    p_data_contratto DATE,
    p_notaio VARCHAR(255) DEFAULT NULL,
    p_repertorio VARCHAR(100) DEFAULT NULL,
    -- Possessori nuovi
    p_nuovi_possessori JSON DEFAULT NULL,  -- [{"nome_completo": "...", "cognome_nome": "...", "paternita": "..."}]
    -- Immobili da trasferire (se null, tutti)
    p_immobili_da_trasferire INTEGER[] DEFAULT NULL,
    -- Note
    p_note TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita_origine partita%ROWTYPE;
    v_nuova_partita_id INTEGER;
    v_variazione_id INTEGER;
    v_possessore_id INTEGER;
    v_possessore RECORD;
    v_immobile_id INTEGER;
    v_possessore_ids INTEGER[] := '{}';
BEGIN
    -- Recupera informazioni sulla partita di origine
    SELECT * INTO v_partita_origine FROM partita WHERE id = p_partita_origine_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita di origine con ID % non trovata', p_partita_origine_id;
    END IF;
    
    IF v_partita_origine.stato = 'inattiva' THEN
        RAISE EXCEPTION 'La partita di origine è già inattiva';
    END IF;
    
    -- Verifica che la nuova partita non esista già
    IF EXISTS (SELECT 1 FROM partita WHERE comune_nome = p_comune_nome AND numero_partita = p_numero_partita) THEN
        RAISE EXCEPTION 'La partita % già esiste nel comune %', p_numero_partita, p_comune_nome;
    END IF;
    
    -- Crea i nuovi possessori se necessario
    IF p_nuovi_possessori IS NOT NULL THEN
        FOR v_possessore IN SELECT * FROM json_to_recordset(p_nuovi_possessori) 
            AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT)
        LOOP
            -- Verifica se il possessore esiste già
            SELECT id INTO v_possessore_id 
            FROM possessore 
            WHERE comune_nome = p_comune_nome AND nome_completo = v_possessore.nome_completo;
            
            IF NOT FOUND THEN
                -- Crea un nuovo possessore
                INSERT INTO possessore(comune_nome, cognome_nome, paternita, nome_completo, attivo)
                VALUES (p_comune_nome, v_possessore.cognome_nome, v_possessore.paternita, v_possessore.nome_completo, TRUE)
                RETURNING id INTO v_possessore_id;
            END IF;
            
            -- Aggiungi all'array dei possessori
            v_possessore_ids := array_append(v_possessore_ids, v_possessore_id);
        END LOOP;
    END IF;
    
    -- Se non sono specificati nuovi possessori, usa gli stessi della partita di origine
    IF array_length(v_possessore_ids, 1) IS NULL THEN
        SELECT array_agg(possessore_id) INTO v_possessore_ids
        FROM partita_possessore
        WHERE partita_id = p_partita_origine_id;
    END IF;
    
    -- Crea la nuova partita
    INSERT INTO partita(comune_nome, numero_partita, tipo, data_impianto, numero_provenienza, stato)
    VALUES (p_comune_nome, p_numero_partita, 'principale', p_data_variazione, v_partita_origine.numero_partita, 'attiva')
    RETURNING id INTO v_nuova_partita_id;
    
    -- Collega i possessori alla nuova partita
    FOREACH v_possessore_id IN ARRAY v_possessore_ids
    LOOP
        INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
        SELECT 
            v_nuova_partita_id,
            v_possessore_id,
            'principale',
            titolo,
            quota
        FROM partita_possessore
        WHERE partita_id = p_partita_origine_id AND possessore_id = v_possessore_id
        LIMIT 1;
        
        -- Se non c'è una quota esistente, imposta come proprietà esclusiva
        IF NOT FOUND THEN
            INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo)
            VALUES (v_nuova_partita_id, v_possessore_id, 'principale', 'proprietà esclusiva');
        END IF;
    END LOOP;
    
    -- Registra la variazione
    INSERT INTO variazione(
        partita_origine_id, partita_destinazione_id, tipo, 
        data_variazione, numero_riferimento, nominativo_riferimento
    )
    VALUES (
        p_partita_origine_id, v_nuova_partita_id, p_tipo_variazione,
        p_data_variazione, p_numero_partita::TEXT, 
        (SELECT string_agg(nome_completo, ', ') FROM possessore WHERE id = ANY(v_possessore_ids))
    )
    RETURNING id INTO v_variazione_id;
    
    -- Registra il contratto
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note);
    
    -- Trasferisci gli immobili
    IF p_immobili_da_trasferire IS NULL THEN
        -- Trasferisci tutti gli immobili
        UPDATE immobile SET partita_id = v_nuova_partita_id
        WHERE partita_id = p_partita_origine_id;
    ELSE
        -- Trasferisci solo gli immobili specificati
        FOREACH v_immobile_id IN ARRAY p_immobili_da_trasferire
        LOOP
            UPDATE immobile SET partita_id = v_nuova_partita_id
            WHERE id = v_immobile_id AND partita_id = p_partita_origine_id;
            
            IF NOT FOUND THEN
                RAISE WARNING 'Immobile con ID % non trovato nella partita di origine', v_immobile_id;
            END IF;
        END LOOP;
    END IF;
    
    -- Chiudi la partita di origine
    UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione
    WHERE id = p_partita_origine_id;
    
    RAISE NOTICE 'Passaggio di proprietà registrato con successo. Nuova partita ID: %', v_nuova_partita_id;
END;
$$;

-- Procedura per gestire un frazionamento di proprietà
CREATE OR REPLACE PROCEDURE registra_frazionamento(
    -- Partita di origine
    p_partita_origine_id INTEGER,
    -- Dati della variazione
    p_data_variazione DATE,
    -- Dati del contratto
    p_tipo_contratto VARCHAR(50),
    p_data_contratto DATE,
    -- Nuove partite da creare con i rispettivi immobili
    p_nuove_partite JSON, -- [{"numero_partita": 123, "comune":"...", "possessori":[{"id":1}], "immobili":[1,2,3]}]
    -- Parametri opzionali
    p_notaio VARCHAR(255) DEFAULT NULL,
    p_repertorio VARCHAR(100) DEFAULT NULL,
    -- Note
    p_note TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita_origine partita%ROWTYPE;
    v_nuova_partita RECORD;
    v_nuova_partita_id INTEGER;
    v_variazione_id INTEGER;
    v_comune_nome VARCHAR(100);
    v_possessore_id INTEGER;
    v_immobile_id INTEGER;
BEGIN
    -- Recupera informazioni sulla partita di origine
    SELECT * INTO v_partita_origine FROM partita WHERE id = p_partita_origine_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita di origine con ID % non trovata', p_partita_origine_id;
    END IF;
    
    IF v_partita_origine.stato = 'inattiva' THEN
        RAISE EXCEPTION 'La partita di origine è già inattiva';
    END IF;
    
    -- Registra la variazione principale di frazionamento
    INSERT INTO variazione(
        partita_origine_id, partita_destinazione_id, tipo, 
        data_variazione, numero_riferimento, nominativo_riferimento
    )
    VALUES (
        p_partita_origine_id, NULL, 'Frazionamento',
        p_data_variazione, 'FRAZ-' || p_partita_origine_id, 'Frazionamento partita ' || v_partita_origine.numero_partita
    )
    RETURNING id INTO v_variazione_id;
    
    -- Registra il contratto
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note);
    
    -- Processa ogni nuova partita
    FOR v_nuova_partita IN SELECT * FROM json_to_recordset(p_nuove_partite) 
        AS x(numero_partita INTEGER, comune TEXT, possessori JSON, immobili JSON)
    LOOP
        v_comune_nome := COALESCE(v_nuova_partita.comune, v_partita_origine.comune_nome);
        
        -- Verifica che la nuova partita non esista già
        IF EXISTS (SELECT 1 FROM partita WHERE comune_nome = v_comune_nome AND numero_partita = v_nuova_partita.numero_partita) THEN
            RAISE EXCEPTION 'La partita % già esiste nel comune %', v_nuova_partita.numero_partita, v_comune_nome;
        END IF;
        
        -- Crea la nuova partita
        INSERT INTO partita(comune_nome, numero_partita, tipo, data_impianto, numero_provenienza, stato)
        VALUES (v_comune_nome, v_nuova_partita.numero_partita, 'principale', p_data_variazione, v_partita_origine.numero_partita, 'attiva')
        RETURNING id INTO v_nuova_partita_id;
        
        -- Collega la nuova partita alla variazione
        UPDATE variazione 
        SET partita_destinazione_id = v_nuova_partita_id
        WHERE id = v_variazione_id;
        
        -- Collega i possessori alla nuova partita
        FOR v_possessore_id IN SELECT value::INTEGER FROM json_array_elements(v_nuova_partita.possessori)
        LOOP
            INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
            SELECT 
                v_nuova_partita_id,
                possessore_id,
                'principale',
                titolo,
                quota
            FROM partita_possessore
            WHERE partita_id = p_partita_origine_id AND possessore_id = v_possessore_id;
        END LOOP;
        
        -- Trasferisci gli immobili specificati
        FOR v_immobile_id IN SELECT value::INTEGER FROM json_array_elements(v_nuova_partita.immobili)
        LOOP
            UPDATE immobile SET partita_id = v_nuova_partita_id
            WHERE id = v_immobile_id AND partita_id = p_partita_origine_id;
            
            IF NOT FOUND THEN
                RAISE WARNING 'Immobile con ID % non trovato nella partita di origine', v_immobile_id;
            END IF;
        END LOOP;
    END LOOP;
    
    -- Verifica se tutti gli immobili sono stati trasferiti
    IF NOT EXISTS (SELECT 1 FROM immobile WHERE partita_id = p_partita_origine_id) THEN
        -- Chiudi la partita di origine se non ha più immobili
        UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione
        WHERE id = p_partita_origine_id;
    END IF;
    
    RAISE NOTICE 'Frazionamento della partita % registrato con successo', v_partita_origine.numero_partita;
END;
$$;

------------------------------------------------------------------------------
-- SEZIONE 2: WORKFLOW PER RICERCA E REPORT
------------------------------------------------------------------------------

/*-- Procedura per generare un certificato di proprietà immobiliare
CREATE OR REPLACE FUNCTION genera_certificato_proprieta(
    p_partita_id INTEGER
)

RETURNS TEXT AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_certificato TEXT;
    v_possessori TEXT;
    v_immobili TEXT;
    v_immobile RECORD;
    v_record RECORD;
BEGIN
    -- Recupera i dati della partita
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita con ID % non trovata', p_partita_id;
    END IF;
    
    -- Intestazione certificato
    v_certificato := '============================================================' || E'\n';
    v_certificato := v_certificato || '                CERTIFICATO DI PROPRIETÀ IMMOBILIARE' || E'\n';
    v_certificato := v_certificato || '                     CATASTO STORICO ANNI ''50' || E'\n';
    v_certificato := v_certificato || '============================================================' || E'\n\n';
    
    -- Dati generali della partita
    v_certificato := v_certificato || 'COMUNE: ' || v_partita.comune_nome || E'\n';
    v_certificato := v_certificato || 'PARTITA N.: ' || v_partita.numero_partita || E'\n';
    v_certificato := v_certificato || 'TIPO: ' || v_partita.tipo || E'\n';
    v_certificato := v_certificato || 'DATA IMPIANTO: ' || v_partita.data_impianto || E'\n';
    v_certificato := v_certificato || 'STATO: ' || v_partita.stato || E'\n';
    IF v_partita.data_chiusura IS NOT NULL THEN
        v_certificato := v_certificato || 'DATA CHIUSURA: ' || v_partita.data_chiusura || E'\n';
    END IF;
    IF v_partita.numero_provenienza IS NOT NULL THEN
        v_certificato := v_certificato || 'PROVENIENZA: Partita n. ' || v_partita.numero_provenienza || E'\n';
    END IF;
    v_certificato := v_certificato || E'\n';
    
    -- Possessori della partita
    v_certificato := v_certificato || '-------------------- INTESTATARI --------------------' || E'\n';
    FOR v_record IN 
        SELECT 
            pos.nome_completo, 
            pp.titolo, 
            pp.quota
        FROM partita_possessore pp
        JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE pp.partita_id = p_partita_id
        ORDER BY pos.nome_completo
    LOOP
        v_certificato := v_certificato || '- ' || v_record.nome_completo;
        IF v_record.titolo = 'comproprietà' AND v_record.quota IS NOT NULL THEN
            v_certificato := v_certificato || ' (quota: ' || v_record.quota || ')';
        END IF;
        v_certificato := v_certificato || E'\n';
    END LOOP;
    v_certificato := v_certificato || E'\n';
    
    -- Immobili della partita
    v_certificato := v_certificato || '-------------------- IMMOBILI --------------------' || E'\n';
    FOR v_immobile IN 
        SELECT 
            i.id,
            i.natura,
            i.numero_piani,
            i.numero_vani,
            i.consistenza,
            i.classificazione,
            l.tipo AS tipo_localita,
            l.nome AS nome_localita,
            l.civico
        FROM immobile i
        JOIN localita l ON i.localita_id = l.id
        WHERE i.partita_id = p_partita_id
        ORDER BY l.nome, i.natura
    LOOP
        v_certificato := v_certificato || 'Immobile ID: ' || v_immobile.id || E'\n';
        v_certificato := v_certificato || '  Natura: ' || v_immobile.natura || E'\n';
        v_certificato := v_certificato || '  Località: ' || v_immobile.nome_localita;
        IF v_immobile.civico IS NOT NULL THEN
            v_certificato := v_certificato || ', ' || v_immobile.civico;
        END IF;
        v_certificato := v_certificato || ' (' || v_immobile.tipo_localita || ')' || E'\n';
        
        IF v_immobile.numero_piani IS NOT NULL THEN
            v_certificato := v_certificato || '  Piani: ' || v_immobile.numero_piani || E'\n';
        END IF;
        IF v_immobile.numero_vani IS NOT NULL THEN
            v_certificato := v_certificato || '  Vani: ' || v_immobile.numero_vani || E'\n';
        END IF;
        IF v_immobile.consistenza IS NOT NULL THEN
            v_certificato := v_certificato || '  Consistenza: ' || v_immobile.consistenza || E'\n';
        END IF;
        IF v_immobile.classificazione IS NOT NULL THEN
            v_certificato := v_certificato || '  Classificazione: ' || v_immobile.classificazione || E'\n';
        END IF;
        
        v_certificato := v_certificato || E'\n';
    END LOOP;
    
    -- Verificare eventuali variazioni
    v_certificato := v_certificato || '-------------------- VARIAZIONI --------------------' || E'\n';
    FOR v_record IN 
        SELECT 
            v.tipo,
            v.data_variazione,
            v.numero_riferimento,
            p2.numero_partita AS partita_destinazione_numero,
            p2.comune_nome AS partita_destinazione_comune,
            c.tipo AS tipo_contratto,
            c.data_contratto,
            c.notaio,
            c.repertorio
        FROM variazione v
        LEFT JOIN partita p2 ON v.partita_destinazione_id = p2.id
        LEFT JOIN contratto c ON v.id = c.variazione_id
        WHERE v.partita_origine_id = p_partita_id
        ORDER BY v.data_variazione DESC
    LOOP
        v_certificato := v_certificato || 'Variazione: ' || v_record.tipo || ' del ' || v_record.data_variazione || E'\n';
        IF v_record.partita_destinazione_numero IS NOT NULL THEN
            v_certificato := v_certificato || '  Nuova partita: ' || v_record.partita_destinazione_numero;
            IF v_record.partita_destinazione_comune != v_partita.comune_nome THEN
                v_certificato := v_certificato || ' (Comune: ' || v_record.partita_destinazione_comune || ')';
            END IF;
            v_certificato := v_certificato || E'\n';
        END IF;
        IF v_record.tipo_contratto IS NOT NULL THEN
            v_certificato := v_certificato || '  Contratto: ' || v_record.tipo_contratto || ' del ' || v_record.data_contratto || E'\n';
            IF v_record.notaio IS NOT NULL THEN
                v_certificato := v_certificato || '  Notaio: ' || v_record.notaio || E'\n';
            END IF;
            IF v_record.repertorio IS NOT NULL THEN
                v_certificato := v_certificato || '  Repertorio: ' || v_record.repertorio || E'\n';
            END IF;
        END IF;
        v_certificato := v_certificato || E'\n';
    END LOOP;
    
    -- Piè di pagina certificato
    v_certificato := v_certificato || '============================================================' || E'\n';
    v_certificato := v_certificato || 'Certificato generato il: ' || CURRENT_DATE || E'\n';
    v_certificato := v_certificato || 'Il presente certificato ha valore puramente storico e documentale.' || E'\n';
    v_certificato := v_certificato || '============================================================' || E'\n';
    
    RETURN v_certificato;
END;

$$;

-- Funzione per generare un report genealogico di una proprietà
CREATE OR REPLACE FUNCTION genera_report_genealogico(
    p_partita_id INTEGER
)
RETURNS TEXT AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_report TEXT;
    v_record RECORD;
    v_predecessori_trovati BOOLEAN := FALSE;
    v_successori_trovati BOOLEAN := FALSE;
BEGIN
    -- Recupera i dati della partita
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita con ID % non trovata', p_partita_id;
    END IF;
    
    -- Intestazione report
    v_report := '============================================================' || E'\n';
    v_report := v_report || '              REPORT GENEALOGICO DELLA PROPRIETÀ' || E'\n';
    v_report := v_report || '                   CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';
    
    -- Dati generali della partita
    v_report := v_report || 'COMUNE: ' || v_partita.comune_nome || E'\n';
    v_report := v_report || 'PARTITA N.: ' || v_partita.numero_partita || E'\n';
    v_report := v_report || 'TIPO: ' || v_partita.tipo || E'\n';
    v_report := v_report || 'DATA IMPIANTO: ' || v_partita.data_impianto || E'\n';
    v_report := v_report || 'STATO: ' || v_partita.stato || E'\n';
    IF v_partita.data_chiusura IS NOT NULL THEN
        v_report := v_report || 'DATA CHIUSURA: ' || v_partita.data_chiusura || E'\n';
    END IF;
    v_report := v_report || E'\n';
    
    -- Possessori della partita
    v_report := v_report || '-------------------- INTESTATARI --------------------' || E'\n';
    FOR v_record IN 
        SELECT 
            pos.nome_completo, 
            pp.titolo, 
            pp.quota
        FROM partita_possessore pp
        JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE pp.partita_id = p_partita_id
    LOOP
        v_report := v_report || '- ' || v_record.nome_completo;
        IF v_record.titolo = 'comproprietà' AND v_record.quota IS NOT NULL THEN
            v_report := v_report || ' (quota: ' || v_record.quota || ')';
        END IF;
        v_report := v_report || E'\n';
    END LOOP;
    v_report := v_report || E'\n';
    
    -- Predecessori (da dove proviene la partita)
    v_report := v_report || '-------------------- PREDECESSORI --------------------' || E'\n';
    
    -- Verifica se proviene da un'altra partita
    IF v_partita.numero_provenienza IS NOT NULL THEN
        FOR v_record IN 
            SELECT 
                p.id AS partita_id,
                p.comune_nome,
                p.numero_partita,
                p.data_impianto,
                p.data_chiusura,
                STRING_AGG(pos.nome_completo, ', ') AS possessori,
                v.tipo AS tipo_variazione,
                v.data_variazione
            FROM partita p
            JOIN variazione v ON p.id = v.partita_origine_id
            LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
            LEFT JOIN possessore pos ON pp.possessore_id = pos.id
            WHERE v.partita_destinazione_id = p_partita_id
            GROUP BY p.id, p.comune_nome, p.numero_partita, p.data_impianto, p.data_chiusura, v.tipo, v.data_variazione
        LOOP
            v_predecessori_trovati := TRUE;
            v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
            v_report := v_report || '  Periodo: ' || v_record.data_impianto || ' - ';
            IF v_record.data_chiusura IS NOT NULL THEN
                v_report := v_report || v_record.data_chiusura;
            ELSE
                v_report := v_report || 'attiva';
            END IF;
            v_report := v_report || E'\n';
            v_report := v_report || '  Intestatari: ' || v_record.possessori || E'\n';
            v_report := v_report || '  Variazione: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione || E'\n';
            v_report := v_report || E'\n';
        END LOOP;
    END IF;
    
    IF NOT v_predecessori_trovati THEN
        v_report := v_report || 'Nessun predecessore trovato. Partita originale.' || E'\n\n';
    END IF;
    
    -- Successori (dove è confluita la partita)
    v_report := v_report || '-------------------- SUCCESSORI --------------------' || E'\n';
    
    FOR v_record IN 
        SELECT 
            p.id AS partita_id,
            p.comune_nome,
            p.numero_partita,
            p.data_impianto,
            p.data_chiusura,
            STRING_AGG(pos.nome_completo, ', ') AS possessori,
            v.tipo AS tipo_variazione,
            v.data_variazione
        FROM partita p
        JOIN variazione v ON p.id = v.partita_destinazione_id
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE v.partita_origine_id = p_partita_id
        GROUP BY p.id, p.comune_nome, p.numero_partita, p.data_impianto, p.data_chiusura, v.tipo, v.data_variazione
    LOOP
        v_successori_trovati := TRUE;
        v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
        v_report := v_report || '  Periodo: ' || v_record.data_impianto || ' - ';
        IF v_record.data_chiusura IS NOT NULL THEN
            v_report := v_report || v_record.data_chiusura;
        ELSE
            v_report := v_report || 'attiva';
        END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Intestatari: ' || v_record.possessori || E'\n';
        v_report := v_report || '  Variazione: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione || E'\n';
        v_report := v_report || E'\n';
    END LOOP;
    
    IF NOT v_successori_trovati THEN
        IF v_partita.stato = 'attiva' THEN
            v_report := v_report || 'Nessun successore trovato. La partita è ancora attiva.' || E'\n\n';
        ELSE
            v_report := v_report || 'Nessun successore trovato nonostante la partita sia chiusa.' || E'\n\n';
        END IF;
    END IF;
    
    -- Piè di pagina report
    v_report := v_report || '============================================================' || E'\n';
    v_report := v_report || 'Report generato il: ' || CURRENT_DATE || E'\n';
    v_report := v_report || '============================================================' || E'\n';
    
    RETURN v_report;
END;
$$;

-- Funzione per generare un report storico delle proprietà di un possessore
CREATE OR REPLACE FUNCTION genera_report_possessore(
    p_possessore_id INTEGER
)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    v_possessore possessore%ROWTYPE;
    v_report TEXT;
    v_record RECORD;
    v_immobile RECORD;
BEGIN
    -- Recupera i dati del possessore
    SELECT * INTO v_possessore FROM possessore WHERE id = p_possessore_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Possessore con ID % non trovato', p_possessore_id;
    END IF;
    
    -- Intestazione report
    v_report := '============================================================' || E'\n';
    v_report := v_report || '              REPORT STORICO DEL POSSESSORE' || E'\n';
    v_report := v_report || '                CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';
    
    -- Dati generali del possessore
    v_report := v_report || 'POSSESSORE: ' || v_possessore.nome_completo || E'\n';
    IF v_possessore.paternita IS NOT NULL THEN
        v_report := v_report || 'PATERNITÀ: ' || v_possessore.paternita || E'\n';
    END IF;
    v_report := v_report || 'COMUNE: ' || v_possessore.comune_nome || E'\n';
    v_report := v_report || 'STATO: ' || CASE WHEN v_possessore.attivo THEN 'Attivo' ELSE 'Non attivo' END || E'\n\n';
    
    -- Elenco delle partite possedute (attuali e passate)
    v_report := v_report || '-------------------- PARTITE INTESTATE --------------------' || E'\n';
    
    FOR v_record IN 
        SELECT 
            p.id AS partita_id,
            p.comune_nome,
            p.numero_partita,
            p.tipo,
            p.data_impianto,
            p.data_chiusura,
            p.stato,
            pp.titolo,
            pp.quota,
            COUNT(i.id) AS num_immobili
        FROM partita p
        JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN immobile i ON p.id = i.partita_id
        WHERE pp.possessore_id = p_possessore_id
        GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.data_impianto, p.data_chiusura, p.stato, pp.titolo, pp.quota
        ORDER BY p.data_impianto DESC
    LOOP
        v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
        v_report := v_report || '  Tipo: ' || v_record.tipo || E'\n';
        v_report := v_report || '  Periodo: ' || v_record.data_impianto || ' - ';
        IF v_record.data_chiusura IS NOT NULL THEN
            v_report := v_report || v_record.data_chiusura;
        ELSE
            v_report := v_report || 'attiva';
        END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Stato: ' || v_record.stato || E'\n';
        v_report := v_report || '  Titolo: ' || v_record.titolo;
        IF v_record.quota IS NOT NULL THEN
            v_report := v_report || ' (quota: ' || v_record.quota || ')';
        END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Immobili: ' || v_record.num_immobili || E'\n\n';
        
        -- Elenco degli immobili per questa partita
        FOR v_immobile IN 
            SELECT 
                i.natura,
                l.nome AS localita_nome,
                l.tipo AS tipo_localita,
                i.classificazione
            FROM immobile i
            JOIN localita l ON i.localita_id = l.id
            WHERE i.partita_id = v_record.partita_id
        LOOP
            v_report := v_report || '    - ' || v_immobile.natura || ' in ' || v_immobile.localita_nome;
            IF v_immobile.classificazione IS NOT NULL THEN
                v_report := v_report || ' (' || v_immobile.classificazione || ')';
            END IF;
            v_report := v_report || E'\n';
        END LOOP;
        v_report := v_report || E'\n';
    END LOOP;
    
    -- Storia delle variazioni che coinvolgono il possessore
    v_report := v_report || '-------------------- VARIAZIONI --------------------' || E'\n';
    
    FOR v_record IN 
        SELECT 
            v.tipo AS tipo_variazione,
            v.data_variazione,
            p_orig.comune_nome AS comune_origine,
            p_orig.numero_partita AS partita_origine,
            p_dest.comune_nome AS comune_destinazione,
            p_dest.numero_partita AS partita_destinazione,
            c.tipo AS tipo_contratto,
            c.data_contratto,
            c.notaio,
            c.repertorio
        FROM variazione v
        JOIN partita p_orig ON v.partita_origine_id = p_orig.id
        LEFT JOIN partita p_dest ON v.partita_destinazione_id = p_dest.id
        LEFT JOIN contratto c ON v.id = c.variazione_id
        WHERE EXISTS (
            SELECT 1 FROM partita_possessore pp
            WHERE pp.partita_id = p_orig.id AND pp.possessore_id = p_possessore_id
        ) OR EXISTS (
            SELECT 1 FROM partita_possessore pp
            WHERE pp.partita_id = p_dest.id AND pp.possessore_id = p_possessore_id
        )
        ORDER BY v.data_variazione DESC
    LOOP
        v_report := v_report || 'Variazione: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione || E'\n';
        v_report := v_report || '  Da: Partita n. ' || v_record.partita_origine || ' (' || v_record.comune_origine || ')' || E'\n';
        IF v_record.partita_destinazione IS NOT NULL THEN
            v_report := v_report || '  A: Partita n. ' || v_record.partita_destinazione || ' (' || v_record.comune_destinazione || ')' || E'\n';
        END IF;
        IF v_record.tipo_contratto IS NOT NULL THEN
            v_report := v_report || '  Contratto: ' || v_record.tipo_contratto || ' del ' || v_record.data_contratto || E'\n';
            IF v_record.notaio IS NOT NULL THEN
                v_report := v_report || '  Notaio: ' || v_record.notaio || E'\n';
            END IF;
            IF v_record.repertorio IS NOT NULL THEN
                v_report := v_report || '  Repertorio: ' || v_record.repertorio || E'\n';
            END IF;
        END IF;
        v_report := v_report || E'\n';
    END LOOP;
    
    -- Piè di pagina report
    v_report := v_report || '============================================================' || E'\n';
    v_report := v_report || 'Report generato il: ' || CURRENT_DATE || E'\n';
    v_report := v_report || '============================================================' || E'\n';
    
    RETURN v_report;
END;
$$;
*/
------------------------------------------------------------------------------
-- SEZIONE 3: WORKFLOW PER LA MANUTENZIONE DEL SISTEMA
------------------------------------------------------------------------------

-- Procedura per verifica integrità del database
CREATE OR REPLACE PROCEDURE verifica_integrita_database(
    OUT p_problemi_trovati BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;
    v_problemi TEXT := '';
BEGIN
    p_problemi_trovati := FALSE;
    
    -- 1. Verifica partite senza possessori
    SELECT COUNT(*) INTO v_count FROM partita p
    WHERE NOT EXISTS (
        SELECT 1 FROM partita_possessore pp WHERE pp.partita_id = p.id
    );
    
    IF v_count > 0 THEN
        p_problemi_trovati := TRUE;
        v_problemi := v_problemi || '- Trovate ' || v_count || ' partite senza possessori' || E'\n';
    END IF;
    
    -- 2. Verifica possessori senza partite
    SELECT COUNT(*) INTO v_count FROM possessore pos
    WHERE pos.attivo = TRUE AND NOT EXISTS (
        SELECT 1 FROM partita_possessore pp WHERE pp.possessore_id = pos.id
    );
    
    IF v_count > 0 THEN
        v_problemi := v_problemi || '- Trovati ' || v_count || ' possessori attivi senza partite associate' || E'\n';
        -- Questo è un avviso, non un errore di integrità
    END IF;
    
    -- 3. Verifica partite inattive con immobili
    SELECT COUNT(*) INTO v_count FROM partita p
    WHERE p.stato = 'inattiva' AND EXISTS (
        SELECT 1 FROM immobile i WHERE i.partita_id = p.id
    );
    
    IF v_count > 0 THEN
        p_problemi_trovati := TRUE;
        v_problemi := v_problemi || '- Trovate ' || v_count || ' partite inattive con immobili associati' || E'\n';
    END IF;
    
    -- 4. Verifica variazioni con partite destinate non esistenti
    SELECT COUNT(*) INTO v_count FROM variazione v
    WHERE v.partita_destinazione_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM partita p WHERE p.id = v.partita_destinazione_id
    );
    
    IF v_count > 0 THEN
        p_problemi_trovati := TRUE;
        v_problemi := v_problemi || '- Trovate ' || v_count || ' variazioni con partite destinazione non esistenti' || E'\n';
    END IF;
    
    -- 5. Verifica partite chiuse senza data di chiusura
    SELECT COUNT(*) INTO v_count FROM partita p
    WHERE p.stato = 'inattiva' AND p.data_chiusura IS NULL;
    
    IF v_count > 0 THEN
        p_problemi_trovati := TRUE;
        v_problemi := v_problemi || '- Trovate ' || v_count || ' partite inattive senza data di chiusura' || E'\n';
    END IF;
    
    -- 6. Verifica variazioni senza contratti
    SELECT COUNT(*) INTO v_count FROM variazione v
    WHERE NOT EXISTS (
        SELECT 1 FROM contratto c WHERE c.variazione_id = v.id
    );
    
    IF v_count > 0 THEN
        v_problemi := v_problemi || '- Trovate ' || v_count || ' variazioni senza contratti associati' || E'\n';
        -- Può essere normale in alcuni casi, quindi è solo un avviso
    END IF;
    
    -- 7. Verifica immobili senza località
    SELECT COUNT(*) INTO v_count FROM immobile i
    WHERE NOT EXISTS (
        SELECT 1 FROM localita l WHERE l.id = i.localita_id
    );
    
    IF v_count > 0 THEN
        p_problemi_trovati := TRUE;
        v_problemi := v_problemi || '- Trovati ' || v_count || ' immobili con località non esistente' || E'\n';
    END IF;
    
    -- Stampa risultati
    IF p_problemi_trovati THEN
        RAISE WARNING 'Problemi di integrità rilevati:%', E'\n' || v_problemi;
    ELSE
        IF v_problemi != '' THEN
            RAISE NOTICE 'Nessun problema critico rilevato, ma ci sono alcuni avvisi:%', E'\n' || v_problemi;
        ELSE
            RAISE NOTICE 'Nessun problema di integrità rilevato nel database.';
        END IF;
    END IF;
END;
$$;

-- Procedura per la correzione automatica di problemi comuni
CREATE OR REPLACE PROCEDURE ripara_problemi_database(
    p_correzione_automatica BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_problemi_trovati BOOLEAN;
    v_partita_record RECORD;
    v_variazione_record RECORD;
    v_nuova_partita_id INTEGER;
    v_count INTEGER;
    v_sql TEXT;
BEGIN
    -- Prima esegue la verifica di integrità
    CALL verifica_integrita_database(v_problemi_trovati);
    
    IF NOT v_problemi_trovati THEN
        RAISE NOTICE 'Nessun problema critico da correggere.';
        RETURN;
    END IF;
    
    IF NOT p_correzione_automatica THEN
        RAISE NOTICE 'Per eseguire le correzioni automatiche, impostare p_correzione_automatica=TRUE.';
        RETURN;
    END IF;
    
    RAISE NOTICE 'Avvio correzione automatica...';
    
    -- 1. Correggi partite inattive con immobili
    FOR v_partita_record IN 
        SELECT p.id, p.numero_partita, p.comune_nome
        FROM partita p
        WHERE p.stato = 'inattiva' AND EXISTS (
            SELECT 1 FROM immobile i WHERE i.partita_id = p.id
        )
    LOOP
        -- Crea una nuova partita temporanea per gli immobili orfani
        v_sql := 'INSERT INTO partita(comune_nome, numero_partita, tipo, data_impianto, numero_provenienza, stato) ' ||
                 'VALUES ($1, $2, ''principale'', CURRENT_DATE, $3, ''attiva'') RETURNING id';
        
        EXECUTE v_sql INTO v_nuova_partita_id 
        USING v_partita_record.comune_nome, 
              (SELECT MAX(numero_partita) + 1 FROM partita WHERE comune_nome = v_partita_record.comune_nome),
              v_partita_record.numero_partita;
        
        -- Sposta gli immobili nella nuova partita
        UPDATE immobile SET partita_id = v_nuova_partita_id WHERE partita_id = v_partita_record.id;
        
        RAISE NOTICE 'Corretti immobili della partita % (comune %), spostati nella nuova partita %',
                    v_partita_record.numero_partita, v_partita_record.comune_nome, v_nuova_partita_id;
    END LOOP;
    
    -- 2. Correggi partite inattive senza data di chiusura
    UPDATE partita 
    SET data_chiusura = CURRENT_DATE
    WHERE stato = 'inattiva' AND data_chiusura IS NULL;
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    IF v_count > 0 THEN
        RAISE NOTICE 'Corrette % partite inattive senza data di chiusura', v_count;
    END IF;
    
    -- 3. Rimuovi variazioni con partite destinazione non esistenti
    FOR v_variazione_record IN 
        SELECT v.id, v.partita_origine_id, v.partita_destinazione_id
        FROM variazione v
        WHERE v.partita_destinazione_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM partita p WHERE p.id = v.partita_destinazione_id
        )
    LOOP
        -- Elimina il contratto associato
        DELETE FROM contratto WHERE variazione_id = v_variazione_record.id;
        
        -- Ripristina la partita di origine se necessario
        UPDATE partita
        SET stato = 'attiva', data_chiusura = NULL
        WHERE id = v_variazione_record.partita_origine_id AND stato = 'inattiva';
        
        -- Elimina la variazione
        DELETE FROM variazione WHERE id = v_variazione_record.id;
        
        RAISE NOTICE 'Rimossa variazione invalida con ID %', v_variazione_record.id;
    END LOOP;
    
    -- Esegui di nuovo la verifica per controllare i progressi
    CALL verifica_integrita_database(v_problemi_trovati);
    
    IF NOT v_problemi_trovati THEN
        RAISE NOTICE 'Correzione automatica completata con successo.';
    ELSE
        RAISE WARNING 'Correzione automatica completata, ma alcuni problemi richiedono intervento manuale.';
    END IF;
END;
$$;

-- Procedura per eseguire un backup logico dei dati
CREATE OR REPLACE PROCEDURE backup_logico_dati(
    p_directory VARCHAR DEFAULT '/tmp',
    p_prefisso_file VARCHAR DEFAULT 'catasto_backup'
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_timestamp VARCHAR := TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD_HH24MISS');
    v_filename VARCHAR;
    v_command VARCHAR;
    v_tabelle TEXT;
BEGIN
    -- Costruisci il nome del file
    v_filename := p_prefisso_file || '_' || v_timestamp || '.sql';
    v_tabelle := 'comune,registro_partite,registro_matricole,possessore,partita,partita_possessore,';
    v_tabelle := v_tabelle || 'localita,immobile,partita_relazione,variazione,contratto,consultazione';
    
    -- Costruisci il comando pg_dump
    v_command := 'pg_dump -U postgres -d catasto_storico -n catasto -t catasto.' || 
                 REPLACE(v_tabelle, ',', ' -t catasto.') || 
                 ' --data-only --column-inserts -f ' || p_directory || '/' || v_filename;
    
    -- Mostra il comando da eseguire
    RAISE NOTICE 'Per eseguire il backup, esegui il seguente comando da shell:';
    RAISE NOTICE '%', v_command;
    
    -- Registra il backup nella tabella backup_registro
    INSERT INTO backup_registro (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)
    VALUES (
        v_filename, 
        CURRENT_USER, 
        NULL, -- dimensione sconosciuta fino all'esecuzione effettiva
        'dati',
        FALSE, -- da aggiornare dopo l'esecuzione effettiva
        'Backup pianificato ma non ancora eseguito', 
        p_directory || '/' || v_filename
    );
    
    RAISE NOTICE 'Backup registrato nel sistema. Eseguire manualmente il comando sopra.';
    RAISE NOTICE 'Dopo l''esecuzione, aggiornare il registro con:';
    RAISE NOTICE 'UPDATE backup_registro SET esito = TRUE, dimensione_bytes = ... WHERE nome_file = ''%'';', v_filename;
END;
$$;

-- Procedura per importare dati da un backup
CREATE OR REPLACE PROCEDURE importa_backup(
    p_file_path VARCHAR,
    p_solo_verifica BOOLEAN DEFAULT TRUE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_command VARCHAR;
BEGIN
    -- Controllo preliminare
    IF NOT p_file_path ~ '\.sql' THEN
        RAISE EXCEPTION 'Il file deve avere estensione .sql';
    END IF;
    
    -- Comando per l'importazione
    IF p_solo_verifica THEN
        -- Verifica senza eseguire realmente l'importazione
        v_command := 'psql -U postgres -d catasto_storico -f ' || p_file_path || ' -e --set ON_ERROR_STOP=on --set AUTOCOMMIT=off -c "BEGIN; ROLLBACK;"';
        
        RAISE NOTICE 'Verifica del backup senza importazione:';
        RAISE NOTICE '%', v_command;
    ELSE
        -- Importazione effettiva
        v_command := 'psql -U postgres -d catasto_storico -f ' || p_file_path || ' -e --set ON_ERROR_STOP=on';
        
        RAISE NOTICE 'Per importare il backup, esegui il comando:';
        RAISE NOTICE '%', v_command;
    END IF;
    
    RAISE NOTICE 'ATTENZIONE: L''importazione sovrascriverà i dati esistenti!';
    RAISE NOTICE 'Si consiglia di eseguire un backup prima dell''importazione.';
END;
$$;

------------------------------------------------------------------------------
-- SEZIONE 4: WORKFLOW PER INTEGRAZIONE CON ARCHIVIO DI STATO
------------------------------------------------------------------------------

-- Procedura per l'aggiornamento sincronizzato con il sistema dell'Archivio di Stato
-- Questa è una simulazione che mostra la struttura, ma l'integrazione reale richiederebbe API specifiche
CREATE OR REPLACE PROCEDURE sincronizza_con_archivio_stato(
    p_partita_id INTEGER,
    p_riferimento_archivio VARCHAR,
    p_data_sincronizzazione DATE DEFAULT CURRENT_DATE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_partita_json JSON;
    v_log_message TEXT;
BEGIN
    -- Recupera i dati della partita
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita con ID % non trovata', p_partita_id;
    END IF;
    
    -- Genera il JSON con tutti i dati della partita
    --SELECT esporta_partita_json(p_partita_id) INTO v_partita_json;

    -- Genera un JSON semplice con dati base della partita
    SELECT json_build_object(
        'id', v_partita.id,
        'comune_nome', v_partita.comune_nome,
        'numero_partita', v_partita.numero_partita
    ) INTO v_partita_json;
        
    -- In una implementazione reale, qui ci sarebbe una chiamata API
    -- all'Archivio di Stato per inviare i dati. 
    -- Simuliamo il processo:
    v_log_message := 'SIMULAZIONE: ';
    v_log_message := v_log_message || 'Inviati dati della partita ' || v_partita.numero_partita;
    v_log_message := v_log_message || ' del comune ' || v_partita.comune_nome;
    v_log_message := v_log_message || ' all''Archivio di Stato con riferimento ' || p_riferimento_archivio;
    v_log_message := v_log_message || ' in data ' || p_data_sincronizzazione;
    
    -- Registriamo la sincronizzazione
    -- In un'implementazione reale si avrebbe una tabella apposita per tracciare le sincronizzazioni
    RAISE NOTICE '%', v_log_message;
    
    -- Esempio di come si potrebbe implementare con un campo aggiuntivo:
    -- UPDATE partita 
    -- SET ultima_sincronizzazione_archivio = p_data_sincronizzazione,
    --     riferimento_archivio = p_riferimento_archivio
    -- WHERE id = p_partita_id;
    
    RAISE NOTICE 'Sincronizzazione con l''Archivio di Stato completata simulando l''invio di % byte di dati.', 
                 LENGTH(v_partita_json::TEXT);
END;
$$;