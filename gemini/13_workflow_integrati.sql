-- Imposta lo schema
SET search_path TO catasto;

/*
 * PROCEDURE PER WORKFLOW INTEGRATI
 * per il Catasto Storico 
 * Versione 1.0 - 13/04/2025
 * MODIFICATA: Rimosse funzioni di report, manutenzione e backup duplicate.
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