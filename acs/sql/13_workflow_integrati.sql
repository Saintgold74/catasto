-- File: 13_workflow_integrati.sql (Versione v1.2 - Corretto errore SELECT INTO)
-- Oggetto: Procedure per workflow integrati nel database Catasto Storico
-- Data: 30/04/2025

SET search_path TO catasto, public;

------------------------------------------------------------------------------
-- SEZIONE 1: WORKFLOW COMPLETI DI REGISTRAZIONE PROPRIETÀ
------------------------------------------------------------------------------

-- Procedura per la registrazione completa di una nuova proprietà
CREATE OR REPLACE PROCEDURE registra_nuova_proprieta(
    p_comune_id INTEGER,
    p_numero_partita INTEGER,
    p_data_impianto DATE,
    p_possessori JSON,
    p_immobili JSON
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita_id INTEGER;
    v_possessore_id INTEGER;
    v_possessore_input RECORD;
    v_immobile_input RECORD;
    v_possessore_ids INTEGER[] := '{}';
BEGIN
    IF NOT EXISTS (SELECT 1 FROM comune WHERE id = p_comune_id) THEN RAISE EXCEPTION 'Il comune con ID % non esiste', p_comune_id; END IF;
    IF EXISTS (SELECT 1 FROM partita WHERE comune_id = p_comune_id AND numero_partita = p_numero_partita) THEN RAISE EXCEPTION 'La partita % già esiste nel comune con ID %', p_numero_partita, p_comune_id; END IF;

    FOR v_possessore_input IN SELECT * FROM json_to_recordset(p_possessori) AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT) LOOP
        SELECT id INTO v_possessore_id FROM possessore WHERE comune_id = p_comune_id AND nome_completo = v_possessore_input.nome_completo;
        IF NOT FOUND THEN
            INSERT INTO possessore(comune_id, cognome_nome, paternita, nome_completo, attivo)
            VALUES (p_comune_id, v_possessore_input.cognome_nome, v_possessore_input.paternita, v_possessore_input.nome_completo, TRUE)
            RETURNING id INTO v_possessore_id; END IF;
        v_possessore_ids := array_append(v_possessore_ids, v_possessore_id);
    END LOOP;

    INSERT INTO partita(comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (p_comune_id, p_numero_partita, 'principale', p_data_impianto, 'attiva')
    RETURNING id INTO v_partita_id;

    FOR i IN 1..array_length(v_possessore_ids, 1) LOOP
        v_possessore_id := v_possessore_ids[i];
        SELECT quota INTO v_possessore_input FROM json_to_recordset(p_possessori) AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT)
        WHERE x.nome_completo = (SELECT nome_completo FROM possessore WHERE id = v_possessore_id);
        INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
        VALUES (v_partita_id, v_possessore_id, 'principale', CASE WHEN v_possessore_input.quota IS NULL OR v_possessore_input.quota = '' THEN 'proprietà esclusiva' ELSE 'comproprietà' END, NULLIF(v_possessore_input.quota, ''));
    END LOOP;

    FOR v_immobile_input IN SELECT * FROM json_to_recordset(p_immobili) AS x(natura TEXT, localita_id INTEGER, classificazione TEXT, numero_piani INTEGER, numero_vani INTEGER, consistenza TEXT) LOOP
        IF NOT EXISTS (SELECT 1 FROM localita WHERE id = v_immobile_input.localita_id) THEN
             RAISE WARNING 'Località ID % per immobile "%" non trovata. Immobile non inserito.', v_immobile_input.localita_id, v_immobile_input.natura; CONTINUE; END IF;
        INSERT INTO immobile(partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
        VALUES (v_partita_id, v_immobile_input.localita_id, v_immobile_input.natura, v_immobile_input.numero_piani, v_immobile_input.numero_vani, v_immobile_input.consistenza, v_immobile_input.classificazione);
    END LOOP;
    RAISE NOTICE 'Registrazione nuova proprietà completata. Partita % (Comune ID %) creata con ID %', p_numero_partita, p_comune_id, v_partita_id;
EXCEPTION WHEN OTHERS THEN RAISE EXCEPTION '[registra_nuova_proprieta] Errore: %', SQLERRM;
END;
$$;

-- Procedura per la registrazione di un passaggio di proprietà completo
CREATE OR REPLACE PROCEDURE registra_passaggio_proprieta(
    p_partita_origine_id INTEGER,
    p_comune_id INTEGER,
    p_numero_partita INTEGER,
    p_tipo_variazione VARCHAR(50),
    p_data_variazione DATE,
    p_tipo_contratto VARCHAR(50),
    p_data_contratto DATE,
    p_notaio VARCHAR(255) DEFAULT NULL,
    p_repertorio VARCHAR(100) DEFAULT NULL,
    p_nuovi_possessori JSON DEFAULT NULL,
    p_immobili_da_trasferire INTEGER[] DEFAULT NULL,
    p_note TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita_origine partita%ROWTYPE; -- Manteniamo ROWTYPE
    v_comune_nome_origine comune.nome%TYPE; -- Variabile separata per nome comune origine
    v_nuova_partita_id INTEGER;
    v_variazione_id INTEGER;
    v_possessore_id INTEGER;
    v_possessore_input RECORD;
    v_immobile_id INTEGER;
    v_possessore_ids INTEGER[] := '{}';
BEGIN
    -- Recupera dati partita origine base
    SELECT * INTO v_partita_origine FROM partita WHERE id = p_partita_origine_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Partita di origine ID % non trovata', p_partita_origine_id; END IF;
    -- Recupera nome comune origine separatamente
    SELECT nome INTO v_comune_nome_origine FROM comune WHERE id = v_partita_origine.comune_id;

    IF v_partita_origine.stato = 'inattiva' THEN RAISE EXCEPTION 'La partita di origine è già inattiva'; END IF;
    IF NOT EXISTS (SELECT 1 FROM comune WHERE id = p_comune_id) THEN RAISE EXCEPTION 'Comune di destinazione ID % non trovato', p_comune_id; END IF;
    IF EXISTS (SELECT 1 FROM partita WHERE comune_id = p_comune_id AND numero_partita = p_numero_partita) THEN RAISE EXCEPTION 'La partita % già esiste nel comune ID %', p_numero_partita, p_comune_id; END IF;

    IF p_nuovi_possessori IS NOT NULL THEN
        FOR v_possessore_input IN SELECT * FROM json_to_recordset(p_nuovi_possessori) AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT) LOOP
            SELECT id INTO v_possessore_id FROM possessore WHERE comune_id = p_comune_id AND nome_completo = v_possessore_input.nome_completo;
            IF NOT FOUND THEN
                INSERT INTO possessore(comune_id, cognome_nome, paternita, nome_completo, attivo)
                VALUES (p_comune_id, v_possessore_input.cognome_nome, v_possessore_input.paternita, v_possessore_input.nome_completo, TRUE)
                RETURNING id INTO v_possessore_id; END IF;
            v_possessore_ids := array_append(v_possessore_ids, v_possessore_id);
        END LOOP;
    ELSE
        FOR v_possessore_input IN SELECT pos.* FROM possessore pos JOIN partita_possessore pp ON pos.id = pp.possessore_id WHERE pp.partita_id = p_partita_origine_id LOOP
            SELECT id INTO v_possessore_id FROM possessore WHERE comune_id = p_comune_id AND nome_completo = v_possessore_input.nome_completo;
            IF NOT FOUND THEN
                INSERT INTO possessore(comune_id, cognome_nome, paternita, nome_completo, attivo)
                VALUES (p_comune_id, v_possessore_input.cognome_nome, v_possessore_input.paternita, v_possessore_input.nome_completo, TRUE)
                RETURNING id INTO v_possessore_id; END IF;
            v_possessore_ids := array_append(v_possessore_ids, v_possessore_id);
        END LOOP;
    END IF;

    INSERT INTO partita(comune_id, numero_partita, tipo, data_impianto, numero_provenienza, stato)
    VALUES (p_comune_id, p_numero_partita, 'principale', p_data_variazione, v_partita_origine.numero_partita, 'attiva')
    RETURNING id INTO v_nuova_partita_id;

    FOR i IN 1..array_length(v_possessore_ids, 1) LOOP
        v_possessore_id := v_possessore_ids[i];
        DECLARE v_titolo VARCHAR := 'proprietà esclusiva'; v_quota VARCHAR := NULL;
        BEGIN
            IF p_nuovi_possessori IS NOT NULL THEN
                 SELECT COALESCE(NULLIF(x.quota, ''), v_quota) INTO v_quota FROM json_to_recordset(p_nuovi_possessori) AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT)
                 WHERE x.nome_completo = (SELECT nome_completo FROM possessore WHERE id=v_possessore_id);
                 IF v_quota IS NOT NULL THEN v_titolo := 'comproprietà'; END IF;
            ELSE
                 SELECT pp.titolo, pp.quota INTO v_titolo, v_quota FROM partita_possessore pp JOIN possessore p_orig ON pp.possessore_id = p_orig.id
                 WHERE pp.partita_id = p_partita_origine_id AND p_orig.nome_completo = (SELECT nome_completo FROM possessore WHERE id=v_possessore_id); END IF;
             INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_nuova_partita_id, v_possessore_id, 'principale', v_titolo, v_quota);
        END;
    END LOOP;

    INSERT INTO variazione(partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento)
    VALUES (p_partita_origine_id, v_nuova_partita_id, p_tipo_variazione, p_data_variazione, p_numero_partita::TEXT, (SELECT string_agg(nome_completo, ', ') FROM possessore WHERE id = ANY(v_possessore_ids)))
    RETURNING id INTO v_variazione_id;

    IF p_tipo_contratto IS NOT NULL AND p_data_contratto IS NOT NULL THEN
        INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note) VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note); END IF;

    IF p_immobili_da_trasferire IS NULL THEN
        UPDATE immobile SET partita_id = v_nuova_partita_id, data_modifica = CURRENT_TIMESTAMP WHERE partita_id = p_partita_origine_id;
    ELSE
        FOREACH v_immobile_id IN ARRAY p_immobili_da_trasferire LOOP
            UPDATE immobile SET partita_id = v_nuova_partita_id, data_modifica = CURRENT_TIMESTAMP WHERE id = v_immobile_id AND partita_id = p_partita_origine_id;
            IF NOT FOUND THEN RAISE WARNING 'Immobile ID % non trovato/aggiornato nella partita origine ID %.', v_immobile_id, p_partita_origine_id; END IF;
        END LOOP;
    END IF;

    UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione WHERE id = p_partita_origine_id;
    RAISE NOTICE 'Passaggio di proprietà registrato. Origine ID: %, Nuova ID: % (Comune ID: %, Num: %)', p_partita_origine_id, v_nuova_partita_id, p_comune_id, p_numero_partita;
EXCEPTION WHEN OTHERS THEN RAISE EXCEPTION '[registra_passaggio_proprieta] Errore: %', SQLERRM;
END;
$$;


-- Procedura per gestire un frazionamento di proprietà (invariata, usa ancora nome comune nel JSON)
CREATE OR REPLACE PROCEDURE registra_frazionamento(
    p_partita_origine_id INTEGER,
    p_data_variazione DATE,
    p_tipo_contratto VARCHAR(50),
    p_data_contratto DATE,
    p_nuove_partite JSON,
    p_notaio VARCHAR(255) DEFAULT NULL,
    p_repertorio VARCHAR(100) DEFAULT NULL,
    p_note TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita_origine partita%ROWTYPE;
    v_nuova_partita RECORD;
    v_nuova_partita_id INTEGER;
    v_variazione_id INTEGER;
    v_comune_id INTEGER;
    v_comune_nome VARCHAR(100);
    v_possessore_record RECORD;
    v_immobile_id INTEGER;
BEGIN
    SELECT * INTO v_partita_origine FROM partita WHERE id = p_partita_origine_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Partita di origine ID % non trovata', p_partita_origine_id; END IF;
    IF v_partita_origine.stato = 'inattiva' THEN RAISE EXCEPTION 'La partita di origine è già inattiva'; END IF;

    INSERT INTO variazione(partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento)
    VALUES (p_partita_origine_id, NULL, 'Frazionamento', p_data_variazione, 'FRAZ-' || p_partita_origine_id, 'Frazionamento partita ' || v_partita_origine.numero_partita)
    RETURNING id INTO v_variazione_id;

    IF p_tipo_contratto IS NOT NULL AND p_data_contratto IS NOT NULL THEN
        INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note) VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note); END IF;

    FOR v_nuova_partita IN SELECT * FROM json_to_recordset(p_nuove_partite) AS x(numero_partita INTEGER, comune TEXT, possessori JSON, immobili JSON) LOOP
        v_comune_nome := COALESCE(v_nuova_partita.comune, (SELECT c.nome FROM comune c WHERE c.id = v_partita_origine.comune_id));
        SELECT id INTO v_comune_id FROM comune WHERE nome = v_comune_nome;
        IF v_comune_id IS NULL THEN RAISE EXCEPTION 'Comune "%" specificato per nuova partita % non trovato.', v_comune_nome, v_nuova_partita.numero_partita; END IF;
        IF EXISTS (SELECT 1 FROM partita WHERE comune_id = v_comune_id AND numero_partita = v_nuova_partita.numero_partita) THEN RAISE EXCEPTION 'La partita % già esiste nel comune % (ID: %)', v_nuova_partita.numero_partita, v_comune_nome, v_comune_id; END IF;

        INSERT INTO partita(comune_id, numero_partita, tipo, data_impianto, numero_provenienza, stato)
        VALUES (v_comune_id, v_nuova_partita.numero_partita, 'principale', p_data_variazione, v_partita_origine.numero_partita, 'attiva')
        RETURNING id INTO v_nuova_partita_id;

         INSERT INTO variazione(partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento)
         VALUES (p_partita_origine_id, v_nuova_partita_id, 'Frazionamento-Dest', p_data_variazione, v_nuova_partita.numero_partita::TEXT, 'Creazione partita ' || v_nuova_partita.numero_partita || ' da frazionamento');

        FOR v_possessore_record IN SELECT * FROM json_to_recordset(v_nuova_partita.possessori) AS x(id INTEGER, quota TEXT, titolo TEXT) LOOP
             IF NOT EXISTS (SELECT 1 FROM possessore WHERE id = v_possessore_record.id) THEN RAISE WARNING 'Possessore ID % per partita % non trovato. Associazione saltata.', v_possessore_record.id, v_nuova_partita.numero_partita; CONTINUE; END IF;
            INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
            VALUES (v_nuova_partita_id, v_possessore_record.id, 'principale', COALESCE(v_possessore_record.titolo, CASE WHEN v_possessore_record.quota IS NULL THEN 'proprietà esclusiva' ELSE 'comproprietà' END), NULLIF(v_possessore_record.quota,''));
        END LOOP;

        FOR v_immobile_id IN SELECT value::INTEGER FROM json_array_elements_text(v_nuova_partita.immobili) LOOP
            UPDATE immobile SET partita_id = v_nuova_partita_id, data_modifica = CURRENT_TIMESTAMP WHERE id = v_immobile_id AND partita_id = p_partita_origine_id;
            IF NOT FOUND THEN RAISE WARNING 'Immobile ID % non trovato/aggiornato nella partita origine ID %.', v_immobile_id, p_partita_origine_id; END IF;
        END LOOP;
    END LOOP;

    IF NOT EXISTS (SELECT 1 FROM immobile WHERE partita_id = p_partita_origine_id) THEN
        UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione WHERE id = p_partita_origine_id;
        RAISE NOTICE 'Partita origine ID % chiusa (tutti immobili trasferiti).', p_partita_origine_id;
    ELSE RAISE NOTICE 'Partita origine ID % mantenuta attiva (contiene ancora immobili).', p_partita_origine_id; END IF;
    RAISE NOTICE 'Frazionamento della partita % registrato con successo', v_partita_origine.numero_partita;
EXCEPTION WHEN OTHERS THEN RAISE EXCEPTION '[registra_frazionamento] Errore: %', SQLERRM;
END;
$$;


------------------------------------------------------------------------------
-- SEZIONE 4: WORKFLOW PER INTEGRAZIONE CON ARCHIVIO DI STATO (SIMULAZIONE)
------------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sincronizza_con_archivio_stato(
    p_partita_id INTEGER,
    p_riferimento_archivio VARCHAR,
    p_data_sincronizzazione DATE DEFAULT CURRENT_DATE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_comune_nome comune.nome%TYPE; -- Variabile per nome comune
    v_partita_json JSONB;
    v_log_message TEXT;
BEGIN
    -- Recupera dati partita base
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    IF NOT FOUND THEN RAISE EXCEPTION 'Partita ID % non trovata', p_partita_id; END IF;
    -- Recupera nome comune separatamente
    SELECT nome INTO v_comune_nome FROM comune WHERE id = v_partita.comune_id;

    v_partita_json := to_jsonb(v_partita);
    v_log_message := 'SIMULAZIONE: Invio dati partita N.' || v_partita.numero_partita || ' (Comune: ' || v_comune_nome || ', ID: '|| v_partita.id || ') all''Archivio di Stato. Riferimento: ' || p_riferimento_archivio || '. Data: ' || p_data_sincronizzazione;
    RAISE NOTICE '%', v_log_message;
    RAISE NOTICE 'Simulazione sincronizzazione con Archivio di Stato completata. Dati (JSONB): %', v_partita_json;
EXCEPTION WHEN OTHERS THEN RAISE EXCEPTION '[sincronizza_con_archivio_stato] Errore: %', SQLERRM;
END;
$$;