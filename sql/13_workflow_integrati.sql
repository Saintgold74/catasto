-- Imposta lo schema
SET search_path TO catasto, public; -- Aggiunto public per estensioni

/*
 * PROCEDURE PER WORKFLOW INTEGRATI (MODIFICATE per comune.id PK)
 * per il Catasto Storico
 * Versione 1.1
 */

------------------------------------------------------------------------------
-- SEZIONE 1: WORKFLOW COMPLETI DI REGISTRAZIONE PROPRIETÀ
------------------------------------------------------------------------------

-- Procedura per la registrazione completa di una nuova proprietà (MODIFICATA)
CREATE OR REPLACE PROCEDURE registra_nuova_proprieta(
    -- Parametri per la partita
    p_comune_id INTEGER, -- *** MODIFICATO: Accetta ID comune ***
    p_numero_partita INTEGER,
    p_data_impianto DATE,
    -- Parametri per i possessori (array di record)
    p_possessori JSON,  -- [{"nome_completo": "...", "cognome_nome": "...", "paternita": "...", "quota": "..."}]
                        -- Nota: il comune_id per i possessori verrà preso da p_comune_id
    -- Parametri per gli immobili
    p_immobili JSON     -- [{"natura": "...", "localita_nome": "...", "tipo_localita": "...", "classificazione": "...", "civico": N}]
                        -- Nota: il comune_id per le località verrà preso da p_comune_id
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
    v_comune_nome_check VARCHAR; -- Per verifica esistenza comune
BEGIN
    -- Verifiche preliminari
    SELECT nome INTO v_comune_nome_check FROM comune WHERE id = p_comune_id; -- Verifica su ID
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Il comune con ID % non esiste', p_comune_id;
    END IF;

    IF EXISTS (SELECT 1 FROM partita WHERE comune_id = p_comune_id AND numero_partita = p_numero_partita) THEN -- Verifica su ID
        RAISE EXCEPTION 'La partita % già esiste nel comune ID %', p_numero_partita, p_comune_id;
    END IF;

    -- Inserisci o recupera i possessori (Usa p_comune_id)
    FOR v_possessore IN SELECT * FROM json_to_recordset(p_possessori)
        AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT)
    LOOP
        -- Verifica se il possessore esiste già nel comune specificato
        SELECT id INTO v_possessore_id
        FROM possessore
        WHERE comune_id = p_comune_id AND nome_completo = v_possessore.nome_completo; -- Verifica su ID

        IF NOT FOUND THEN
            -- Crea un nuovo possessore usando l'ID del comune
            INSERT INTO possessore(comune_id, cognome_nome, paternita, nome_completo, attivo)
            VALUES (p_comune_id, v_possessore.cognome_nome, v_possessore.paternita, v_possessore.nome_completo, TRUE)
            RETURNING id INTO v_possessore_id;
        END IF;

        -- Aggiungi all'array dei possessori
        v_possessore_ids := array_append(v_possessore_ids, v_possessore_id);
    END LOOP;

    -- Crea la partita (Usa p_comune_id)
    INSERT INTO partita(comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (p_comune_id, p_numero_partita, 'principale', p_data_impianto, 'attiva')
    RETURNING id INTO v_partita_id;

    -- Collega i possessori alla partita (Logica per titolo/quota invariata)
    FOR i IN 1..array_length(v_possessore_ids, 1)
    LOOP
        v_possessore_id := v_possessore_ids[i];

        -- Estrai la quota dal JSON originale
        SELECT quota INTO v_possessore FROM json_to_recordset(p_possessori)
        AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT)
        OFFSET (i-1) LIMIT 1;

        INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
        VALUES (
            v_partita_id,
            v_possessore_id,
            'principale',
            CASE WHEN v_possessore.quota IS NULL OR v_possessore.quota = '' THEN 'proprietà esclusiva' ELSE 'comproprietà' END,
            NULLIF(v_possessore.quota, '') -- Inserisce NULL se la quota è vuota
        );
    END LOOP;

    -- Crea gli immobili (Usa p_comune_id per le località)
    FOR v_immobile IN SELECT * FROM json_to_recordset(p_immobili)
        AS x(natura TEXT, localita_nome TEXT, tipo_localita TEXT, classificazione TEXT, numero_piani INTEGER, numero_vani INTEGER, consistenza TEXT, civico INTEGER)
    LOOP
        -- Verifica se la località esiste (Usa p_comune_id e nome)
        SELECT id INTO v_localita_id
        FROM localita
        WHERE comune_id = p_comune_id AND nome = v_immobile.localita_nome AND (civico IS NULL OR civico = v_immobile.civico); -- Verifica su ID e nome (+civico)

        IF NOT FOUND THEN
            -- Crea una nuova località (Usa p_comune_id)
            INSERT INTO localita(comune_id, nome, tipo, civico)
            VALUES (p_comune_id, v_immobile.localita_nome, COALESCE(v_immobile.tipo_localita, 'regione'), v_immobile.civico)
            RETURNING id INTO v_localita_id;
        END IF;

        -- Crea l'immobile (usa ID località trovato/creato)
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

    RAISE NOTICE 'Registrazione completata. Partita % creata con ID % per Comune ID %', p_numero_partita, v_partita_id, p_comune_id;
END;
$$;

-- Procedura per la registrazione di un passaggio di proprietà completo (MODIFICATA)
CREATE OR REPLACE PROCEDURE registra_passaggio_proprieta(
    -- Partita di origine
    p_partita_origine_id INTEGER,
    -- Informazioni nuova partita
    p_comune_id INTEGER, -- *** MODIFICATO: Accetta ID comune ***
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
                                           -- Nota: il comune_id per i possessori verrà preso da p_comune_id
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
    v_comune_nome_check VARCHAR; -- Per verifica esistenza comune
BEGIN
    -- Recupera informazioni sulla partita di origine
    SELECT * INTO v_partita_origine FROM partita WHERE id = p_partita_origine_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita di origine con ID % non trovata', p_partita_origine_id;
    END IF;

    IF v_partita_origine.stato = 'inattiva' THEN
        RAISE EXCEPTION 'La partita di origine è già inattiva';
    END IF;

    -- Verifica esistenza comune destinazione
    SELECT nome INTO v_comune_nome_check FROM comune WHERE id = p_comune_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Il comune di destinazione con ID % non esiste', p_comune_id;
    END IF;

    -- Verifica che la nuova partita non esista già nel comune di destinazione
    IF EXISTS (SELECT 1 FROM partita WHERE comune_id = p_comune_id AND numero_partita = p_numero_partita) THEN -- Verifica su ID
        RAISE EXCEPTION 'La partita % già esiste nel comune ID %', p_numero_partita, p_comune_id;
    END IF;

    -- Crea i nuovi possessori se necessario (Usa p_comune_id)
    IF p_nuovi_possessori IS NOT NULL THEN
        FOR v_possessore IN SELECT * FROM json_to_recordset(p_nuovi_possessori)
            AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT) -- Aggiunto quota
        LOOP
            -- Verifica se il possessore esiste già nel comune specificato
            SELECT id INTO v_possessore_id
            FROM possessore
            WHERE comune_id = p_comune_id AND nome_completo = v_possessore.nome_completo; -- Verifica su ID

            IF NOT FOUND THEN
                -- Crea un nuovo possessore
                INSERT INTO possessore(comune_id, cognome_nome, paternita, nome_completo, attivo) -- Usa ID comune
                VALUES (p_comune_id, v_possessore.cognome_nome, v_possessore.paternita, v_possessore.nome_completo, TRUE)
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
        -- Assicurati che gli ID possessori esistano nel comune di destinazione?
        -- Potrebbe essere necessario un controllo aggiuntivo o assumere che siano validi.
    END IF;

    -- Crea la nuova partita (Usa p_comune_id)
    INSERT INTO partita(comune_id, numero_partita, tipo, data_impianto, numero_provenienza, stato) -- Usa ID comune
    VALUES (p_comune_id, p_numero_partita, 'principale', p_data_variazione, v_partita_origine.numero_partita, 'attiva')
    RETURNING id INTO v_nuova_partita_id;

    -- Collega i possessori alla nuova partita (Gestisci quote se presenti nel JSON p_nuovi_possessori)
    IF p_nuovi_possessori IS NOT NULL THEN
         FOR i IN 1..array_length(v_possessore_ids, 1) LOOP
            v_possessore_id := v_possessore_ids[i];
            SELECT quota INTO v_possessore FROM json_to_recordset(p_nuovi_possessori)
               AS x(nome_completo TEXT, cognome_nome TEXT, paternita TEXT, quota TEXT)
               OFFSET (i-1) LIMIT 1;
            INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
            VALUES (v_nuova_partita_id, v_possessore_id, 'principale',
                    CASE WHEN v_possessore.quota IS NULL OR v_possessore.quota = '' THEN 'proprietà esclusiva' ELSE 'comproprietà' END,
                    NULLIF(v_possessore.quota,''));
         END LOOP;
    ELSE -- Copia titolo e quota dall'origine
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
            LIMIT 1; -- Dovrebbe essercene solo uno

            -- Fallback se non trovato (improbabile ma sicuro)
            IF NOT FOUND THEN
                INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo)
                VALUES (v_nuova_partita_id, v_possessore_id, 'principale', 'proprietà esclusiva');
            END IF;
        END LOOP;
    END IF;

    -- Registra la variazione (Invariato)
    INSERT INTO variazione(partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento)
    VALUES (p_partita_origine_id, v_nuova_partita_id, p_tipo_variazione, p_data_variazione, p_numero_partita::TEXT,
           (SELECT string_agg(nome_completo, ', ') FROM possessore WHERE id = ANY(v_possessore_ids)))
    RETURNING id INTO v_variazione_id;

    -- Registra il contratto (Invariato)
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note);

    -- Trasferisci gli immobili (Invariato)
    IF p_immobili_da_trasferire IS NULL THEN
        UPDATE immobile SET partita_id = v_nuova_partita_id
        WHERE partita_id = p_partita_origine_id;
    ELSE
        FOREACH v_immobile_id IN ARRAY p_immobili_da_trasferire
        LOOP
            UPDATE immobile SET partita_id = v_nuova_partita_id
            WHERE id = v_immobile_id AND partita_id = p_partita_origine_id;
            IF NOT FOUND THEN RAISE WARNING 'Immobile ID % non trovato nella partita origine %', v_immobile_id, p_partita_origine_id; END IF;
        END LOOP;
    END IF;

    -- Chiudi la partita di origine (Invariato)
    UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione
    WHERE id = p_partita_origine_id;

    RAISE NOTICE 'Passaggio di proprietà registrato. Nuova partita ID: % per Comune ID: %', v_nuova_partita_id, p_comune_id;
END;
$$;

-- Procedura per gestire un frazionamento di proprietà (MODIFICATA)
-- Nota: Assumiamo che il JSON p_nuove_partite contenga comune_id invece di comune_nome
CREATE OR REPLACE PROCEDURE registra_frazionamento(
    p_partita_origine_id INTEGER,
    p_data_variazione DATE,
    p_tipo_contratto VARCHAR(50),
    p_data_contratto DATE,
    -- JSON ora deve contenere comune_id se diverso da origine
    p_nuove_partite JSON, -- [{"numero_partita": 123, "comune_id": ID, "possessori":[ID1, ID2], "immobili":[ID1,ID2,ID3]}]
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
    v_comune_id INTEGER; -- *** Variabile per ID comune ***
    v_possessore_id INTEGER;
    v_immobile_id INTEGER;
BEGIN
    -- Recupera info partita origine (incluso comune_id)
    SELECT * INTO v_partita_origine FROM partita WHERE id = p_partita_origine_id;

    IF NOT FOUND THEN RAISE EXCEPTION 'Partita origine ID % non trovata', p_partita_origine_id; END IF;
    IF v_partita_origine.stato = 'inattiva' THEN RAISE EXCEPTION 'Partita origine già inattiva'; END IF;

    -- Registra variazione principale
    INSERT INTO variazione(partita_origine_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento)
    VALUES (p_partita_origine_id, 'Frazionamento', p_data_variazione, 'FRAZ-' || p_partita_origine_id, 'Frazionamento partita ' || v_partita_origine.numero_partita)
    RETURNING id INTO v_variazione_id;

    -- Registra contratto
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note);

    -- Processa ogni nuova partita definita nel JSON
    FOR v_nuova_partita IN SELECT * FROM json_to_recordset(p_nuove_partite)
        AS x(numero_partita INTEGER, comune_id INTEGER, possessori JSON, immobili JSON) -- *** Usa comune_id dal JSON ***
    LOOP
        -- Usa comune_id dal JSON, se non fornito usa quello della partita origine
        v_comune_id := COALESCE(v_nuova_partita.comune_id, v_partita_origine.comune_id);

        -- Verifica esistenza comune (se diverso da origine)
        IF v_comune_id != v_partita_origine.comune_id AND NOT EXISTS (SELECT 1 FROM comune WHERE id = v_comune_id) THEN
             RAISE EXCEPTION 'Comune ID % specificato nel JSON non esiste', v_comune_id;
        END IF;

        -- Verifica che nuova partita non esista già nel comune target
        IF EXISTS (SELECT 1 FROM partita WHERE comune_id = v_comune_id AND numero_partita = v_nuova_partita.numero_partita) THEN
            RAISE EXCEPTION 'Partita % già esiste nel comune ID %', v_nuova_partita.numero_partita, v_comune_id;
        END IF;

        -- Crea nuova partita (Usa v_comune_id)
        INSERT INTO partita(comune_id, numero_partita, tipo, data_impianto, numero_provenienza, stato)
        VALUES (v_comune_id, v_nuova_partita.numero_partita, 'principale', p_data_variazione, v_partita_origine.numero_partita, 'attiva')
        RETURNING id INTO v_nuova_partita_id;

        -- Collega la nuova partita alla variazione (UPDATE invece di inserire multiple variazioni)
        -- Potrebbe essere meglio creare una variazione per ogni nuova partita? Dipende dal requisito.
        -- Per ora, colleghiamo tutte alla variazione principale
        -- UPDATE variazione SET partita_destinazione_id = v_nuova_partita_id WHERE id = v_variazione_id; -- Questo sovrascrive! Non va bene.
        -- Alternativa: Creare una variazione per ogni coppia origine->destinazione?
        -- Semplificazione: La variazione principale indica il frazionamento, non le destinazioni multiple.

        -- Collega possessori (Assumiamo JSON 'possessori' contenga array di ID possessore)
        IF json_typeof(v_nuova_partita.possessori) = 'array' THEN
            FOR v_possessore_id IN SELECT value::INTEGER FROM json_array_elements_text(v_nuova_partita.possessori) LOOP
                -- Copia titolo/quota dall'associazione originale (se esiste)
                INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo, quota)
                SELECT v_nuova_partita_id, pp.possessore_id, pp.tipo_partita, pp.titolo, pp.quota
                FROM partita_possessore pp
                WHERE pp.partita_id = p_partita_origine_id AND pp.possessore_id = v_possessore_id
                LIMIT 1;
                 -- Fallback se non trovato nella partita origine (improbabile per frazionamento?)
                IF NOT FOUND THEN
                   INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita, titolo)
                   VALUES (v_nuova_partita_id, v_possessore_id, 'principale', 'proprietà esclusiva');
                END IF;
            END LOOP;
        END IF;

        -- Trasferisci immobili (Assumiamo JSON 'immobili' contenga array di ID immobile)
         IF json_typeof(v_nuova_partita.immobili) = 'array' THEN
            FOR v_immobile_id IN SELECT value::INTEGER FROM json_array_elements_text(v_nuova_partita.immobili) LOOP
                UPDATE immobile SET partita_id = v_nuova_partita_id
                WHERE id = v_immobile_id AND partita_id = p_partita_origine_id;
                IF NOT FOUND THEN RAISE WARNING 'Immobile ID % non trovato nella partita origine % o già trasferito', v_immobile_id, p_partita_origine_id; END IF;
            END LOOP;
         END IF;

         RAISE NOTICE 'Creata nuova partita ID % (Num %) per Comune ID %', v_nuova_partita_id, v_nuova_partita.numero_partita, v_comune_id;

    END LOOP;

    -- Verifica se chiudere la partita di origine (se non ha più immobili collegati)
    IF NOT EXISTS (SELECT 1 FROM immobile WHERE partita_id = p_partita_origine_id) THEN
        UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione
        WHERE id = p_partita_origine_id;
        RAISE NOTICE 'Partita origine ID % chiusa perché senza immobili.', p_partita_origine_id;
    ELSE
        RAISE NOTICE 'Partita origine ID % mantenuta attiva (ha ancora immobili).', p_partita_origine_id;
    END IF;

    RAISE NOTICE 'Frazionamento partita origine ID % completato.', p_partita_origine_id;
END;
$$;


------------------------------------------------------------------------------
-- SEZIONE 4: WORKFLOW PER INTEGRAZIONE CON ARCHIVIO DI STATO (MODIFICATA)
------------------------------------------------------------------------------

-- Procedura per simulare sincronizzazione con Archivio di Stato (MODIFICATA per join comune)
CREATE OR REPLACE PROCEDURE sincronizza_con_archivio_stato(
    p_partita_id INTEGER,
    p_riferimento_archivio VARCHAR,
    p_data_sincronizzazione DATE DEFAULT CURRENT_DATE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_comune_nome VARCHAR; -- Per nome comune
    v_partita_json JSON;
    v_log_message TEXT;
BEGIN
    -- Recupera dati partita e nome comune
    SELECT p.*, c.nome
    INTO v_partita, v_comune_nome
    FROM partita p
    JOIN comune c ON p.comune_id = c.id -- *** JOIN AGGIUNTO ***
    WHERE p.id = p_partita_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita ID % non trovata', p_partita_id;
    END IF;

    -- Genera JSON (usando la funzione esistente se aggiornata, altrimenti semplice)
    BEGIN
        SELECT catasto.esporta_partita_json(p_partita_id) INTO v_partita_json;
    EXCEPTION
        WHEN undefined_function THEN
            RAISE NOTICE 'Funzione esporta_partita_json non trovata, genero JSON base.';
            SELECT json_build_object('id', v_partita.id, 'comune_nome', v_comune_nome, 'numero_partita', v_partita.numero_partita)
            INTO v_partita_json;
        WHEN OTHERS THEN
            RAISE WARNING 'Errore in esporta_partita_json: %, genero JSON base.', SQLERRM;
             SELECT json_build_object('id', v_partita.id, 'comune_nome', v_comune_nome, 'numero_partita', v_partita.numero_partita)
            INTO v_partita_json;
    END;

    -- Simulazione chiamata API
    v_log_message := 'SIMULAZIONE: ';
    v_log_message := v_log_message || 'Inviati dati della partita ' || v_partita.numero_partita;
    v_log_message := v_log_message || ' del comune ' || v_comune_nome; -- Usa nome recuperato
    v_log_message := v_log_message || ' all''Archivio di Stato con riferimento ' || p_riferimento_archivio;
    v_log_message := v_log_message || ' in data ' || p_data_sincronizzazione;

    RAISE NOTICE '%', v_log_message;

    RAISE NOTICE 'Sincronizzazione simulata con Archivio di Stato completata.';
END;
$$;