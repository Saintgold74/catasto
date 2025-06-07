-- File: 13_workflow_integrati.sql (Versione v1.2 - Corretto errore SELECT INTO)
-- Oggetto: Procedure per workflow integrati nel database Catasto Storico
-- Data: 30/04/2025

SET search_path TO catasto, public;

------------------------------------------------------------------------------
-- SEZIONE 1: WORKFLOW COMPLETI DI REGISTRAZIONE PROPRIETÀ
------------------------------------------------------------------------------

-- Procedura per la registrazione completa di una nuova proprietà
-- File: 03_funzioni-procedure.sql (o dove la tua procedura è definita)

-- Adatta la firma per includere p_suffisso_partita
CREATE OR REPLACE PROCEDURE catasto.registra_nuova_proprieta(
    p_comune_id INTEGER,
    p_numero_partita INTEGER,
    p_data_impianto DATE,
    p_possessori_json JSONB,
    p_immobili_json JSONB,
    p_suffisso_partita TEXT -- <<< NUOVO PARAMETRO AGGIUNTO
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_nuova_partita_id INTEGER;
    v_possessore RECORD;
    v_immobile RECORD;
    v_localita_id INTEGER;
    v_possessore_id INTEGER;
BEGIN
    -- Validazione di base
    IF p_comune_id IS NULL OR p_numero_partita IS NULL OR p_data_impianto IS NULL THEN
        RAISE EXCEPTION 'ID Comune, Numero Partita e Data Impianto sono obbligatori.';
    END IF;

    -- Inserimento della nuova partita (con il nuovo campo suffisso)
    INSERT INTO catasto.partita (
        comune_id, 
        numero_partita, 
        suffisso_partita, -- <<< MODIFICA QUI
        data_impianto, 
        tipo, 
        stato
    ) VALUES (
        p_comune_id,
        p_numero_partita,
        p_suffisso_partita, -- <<< MODIFICA QUI
        p_data_impianto,
        'principale',
        'attiva'
    ) RETURNING id INTO v_nuova_partita_id;

    -- Inserimento dei possessori associati
    IF jsonb_array_length(p_possessori_json) > 0 THEN
        FOR v_possessore IN SELECT * FROM jsonb_to_recordset(p_possessori_json) AS x(
            id INTEGER, 
            nome_completo TEXT, 
            paternita TEXT,
            cognome_nome TEXT,
            titolo TEXT, 
            quota TEXT
        )
        LOOP
            -- Assumiamo che l'ID del possessore sia fornito dal JSON
            -- Se l'ID non è fornito, bisognerebbe prima creare il possessore
            IF v_possessore.id IS NULL THEN
                 -- Logica per creare un nuovo possessore se non esiste (omessa per brevità, ma potrebbe essere necessaria)
                 -- Per ora assumiamo che il possessore esista già
                RAISE EXCEPTION 'ID del possessore mancante nel JSON: %', v_possessore.nome_completo;
            END IF;
            
            v_possessore_id := v_possessore.id;

            INSERT INTO catasto.partita_possessore (partita_id, possessore_id, titolo, quota, tipo_partita)
            VALUES (v_nuova_partita_id, v_possessore_id, v_possessore.titolo, v_possessore.quota, 'principale');
        END LOOP;
    ELSE
        RAISE EXCEPTION 'È necessario fornire almeno un possessore.';
    END IF;

    -- Inserimento degli immobili associati
    IF jsonb_array_length(p_immobili_json) > 0 THEN
        FOR v_immobile IN SELECT * FROM jsonb_to_recordset(p_immobili_json) AS x(
            natura TEXT,
            localita_id INTEGER,
            classificazione TEXT,
            consistenza TEXT,
            numero_piani INTEGER,
            numero_vani INTEGER
        )
        LOOP
            v_localita_id := v_immobile.localita_id;

            -- Inserisci l'immobile
            INSERT INTO catasto.immobile (
                partita_id,
                localita_id,
                natura,
                classificazione,
                consistenza,
                numero_piani,
                numero_vani
            ) VALUES (
                v_nuova_partita_id,
                v_localita_id,
                v_immobile.natura,
                v_immobile.classificazione,
                v_immobile.consistenza,
                v_immobile.numero_piani,
                v_immobile.numero_vani
            );
        END LOOP;
    ELSE
        RAISE EXCEPTION 'È necessario fornire almeno un immobile.';
    END IF;
    
    -- Se necessario, la procedura potrebbe restituire l'ID, ma le CALL non lo fanno direttamente.
    -- La logica Python che recupera l'ID dopo la chiamata è corretta.

END;
$$;

-- Procedura per la registrazione di un passaggio di proprietà completo
-- File: 13_workflow_integrati.sql (o dove la tua procedura è definita)

-- Adatta la firma per includere p_suffisso_nuova_partita
CREATE OR REPLACE PROCEDURE catasto.registra_passaggio_proprieta(
    p_partita_origine_id INTEGER,
    p_comune_id_nuova_partita INTEGER,
    p_numero_nuova_partita INTEGER,
    p_suffisso_nuova_partita VARCHAR(20) DEFAULT NULL, -- Questo ha un default

    -- TUTTI I PARAMETRI DA QUI IN POI DEVONO AVERE UN DEFAULT SE SONO NULLABILI
    -- O SE I LORO TIPI NON IMPLICANO UN DEFAULT PER QUALCHE RAGIONE.
    -- I parametri che già avevi senza DEFAULT, e che sono NULLABILI, ora devono averlo.
    -- Quelli che sono NOT NULL (nel senso logico o se li vuoi obbligatori), non lo metti.
    -- Tuttavia, per coerenza con la regola di PostgreSQL sulla posizione dei default,
    -- anche se sono concettualmente NOT NULL, se compaiono dopo un default, la loro
    -- firma deve avere un default. Questo è il "trucco" o la "regola" di PostgreSQL.

    p_tipo_variazione TEXT DEFAULT NULL, -- AGGIUNGI DEFAULT NULL
    p_data_variazione DATE DEFAULT NULL, -- AGGIUNGI DEFAULT NULL
    p_tipo_contratto TEXT DEFAULT NULL, -- AGGIUNGI DEFAULT NULL
    p_data_contratto DATE DEFAULT NULL, -- AGGIUNGI DEFAULT NULL
    p_notaio TEXT DEFAULT NULL,
    p_repertorio TEXT DEFAULT NULL,
    p_nuovi_possessori_json JSONB DEFAULT NULL, -- AGGIUNGI DEFAULT NULL e usa JSONB per coerenza con Python
    p_immobili_da_trasferire_ids INTEGER[] DEFAULT NULL, -- AGGIUNGI DEFAULT NULL
    p_note_variazione TEXT DEFAULT NULL -- AGGIUNGI DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_nuova_partita_id INTEGER;
    v_variazione_id INTEGER;
    v_temp_imm_id INTEGER;
    v_possessore_data JSONB;
    v_nuovo_poss_id INTEGER;
    v_partita_sorgente_id INTEGER;
    v_partita_destinazione_id INTEGER; -- Aggiunto per chiarezza, sarà v_nuova_partita_id
    v_comune_riferimento_id INTEGER;
    v_cognome_nome TEXT;
    v_paternita TEXT;
    v_nome_completo TEXT;
    v_attivo BOOLEAN;
    v_titolo TEXT;
    v_quota TEXT;
BEGIN
    -- Valida che la nuova partita non esista già
    IF EXISTS (SELECT 1 FROM catasto.partita
               WHERE comune_id = p_comune_id_nuova_partita
                 AND numero_partita = p_numero_nuova_partita
                 AND (suffisso_partita = p_suffisso_nuova_partita OR (suffisso_partita IS NULL AND p_suffisso_nuova_partita IS NULL))) THEN
        RAISE EXCEPTION 'Esiste già una partita con il numero %s e suffisso %s nel comune %s.',
                       p_numero_nuova_partita, COALESCE(p_suffisso_nuova_partita, 'NULL'), p_comune_id_nuova_partita;
    END IF;

    -- Crea la nuova partita
    INSERT INTO catasto.partita (comune_id, numero_partita, data_impianto, stato, tipo, suffisso_partita)
    VALUES (p_comune_id_nuova_partita, p_numero_nuova_partita, p_data_variazione, 'attiva', 'principale', p_suffisso_nuova_partita)
    RETURNING id INTO v_nuova_partita_id;

    v_partita_destinazione_id := v_nuova_partita_id; -- La nuova partita è la destinazione

    -- Registra la variazione principale
    INSERT INTO catasto.variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento, note)
    VALUES (p_partita_origine_id, v_partita_destinazione_id, p_tipo_variazione, p_data_variazione, p_repertorio, p_notaio, p_note_variazione)
    RETURNING id INTO v_variazione_id;

    -- Inserisci il contratto associato alla variazione
    INSERT INTO catasto.contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note_variazione); -- Usa p_note_variazione per note del contratto

    -- Trasferisci gli immobili specificati alla nuova partita
    IF p_immobili_da_trasferire_ids IS NOT NULL THEN
        FOREACH v_temp_imm_id IN ARRAY p_immobili_da_trasferire_ids
        LOOP
            UPDATE catasto.immobile SET partita_id = v_partita_destinazione_id WHERE id = v_temp_imm_id;
            -- Qui potresti anche aggiungere una variazione di tipo 'trasferimento immobile' specifica per ogni immobile se necessario
        END LOOP;
    END IF;

    -- Assegna i nuovi possessori alla nuova partita
    IF p_nuovi_possessori_json IS NOT NULL THEN
        FOR v_possessore_data IN SELECT * FROM json_each(p_nuovi_possessori_json)
        LOOP
            v_nome_completo := (v_possessore_data.value ->> 'nome_completo');
            v_cognome_nome := (v_possessore_data.value ->> 'cognome_nome');
            v_paternita := (v_possessore_data.value ->> 'paternita');
            v_comune_riferimento_id := (v_possessore_data.value ->> 'comune_id')::INTEGER;
            v_attivo := COALESCE((v_possessore_data.value ->> 'attivo')::BOOLEAN, TRUE);
            v_titolo := (v_possessore_data.value ->> 'titolo');
            v_quota := (v_possessore_data.value ->> 'quota');

            -- Verifica se il possessore esiste già (per nome_completo nel comune di riferimento)
            SELECT id INTO v_nuovo_poss_id FROM catasto.possessore
            WHERE nome_completo = v_nome_completo AND comune_id = v_comune_riferimento_id LIMIT 1;

            IF v_nuovo_poss_id IS NULL THEN -- Se non esiste, crea il possessore
                INSERT INTO catasto.possessore (nome_completo, cognome_nome, paternita, comune_id, attivo)
                VALUES (v_nome_completo, v_cognome_nome, v_paternita, v_comune_riferimento_id, v_attivo)
                RETURNING id INTO v_nuovo_poss_id;
            END IF;

            -- Associa il possessore alla nuova partita
            INSERT INTO catasto.partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
            VALUES (v_partita_destinazione_id, v_nuovo_poss_id, 'principale', v_titolo, v_quota);
        END LOOP;
    END IF;

    -- Imposta la partita di origine a "inattiva" o gestisci la sua chiusura
    -- Questo dipende dalla logica del passaggio di proprietà (es. chiude la vecchia partita)
    -- Per esempio: UPDATE catasto.partita SET stato = 'inattiva', data_chiusura = p_data_variazione WHERE id = p_partita_origine_id;

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