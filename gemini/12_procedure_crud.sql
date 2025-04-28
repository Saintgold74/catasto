-- Imposta lo schema
SET search_path TO catasto;

-- Correzione della procedura aggiorna_immobile
CREATE OR REPLACE PROCEDURE aggiorna_immobile(
    p_id INTEGER,
    p_natura VARCHAR(100) DEFAULT NULL,
    p_numero_piani INTEGER DEFAULT NULL,
    p_numero_vani INTEGER DEFAULT NULL,
    p_consistenza VARCHAR(255) DEFAULT NULL,
    p_classificazione VARCHAR(100) DEFAULT NULL,
    p_localita_id INTEGER DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE immobile
    SET natura = COALESCE(p_natura, natura),
        numero_piani = COALESCE(p_numero_piani, numero_piani),
        numero_vani = COALESCE(p_numero_vani, numero_vani),
        consistenza = COALESCE(p_consistenza, consistenza),
        classificazione = COALESCE(p_classificazione, classificazione),
        localita_id = COALESCE(p_localita_id, localita_id)
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Immobile con ID % non trovato', p_id;
    END IF;

    RAISE NOTICE 'Immobile con ID % aggiornato con successo', p_id;
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE EXCEPTION 'La località specificata non esiste';
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento dell''immobile: %', SQLERRM;
END;
$$;

-- Correzione della procedura elimina_immobile
CREATE OR REPLACE PROCEDURE elimina_immobile(
    p_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM immobile WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Immobile con ID % non trovato', p_id;
    END IF;

    RAISE NOTICE 'Immobile con ID % eliminato con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione dell''immobile: %', SQLERRM;
END;
$$;

-- Correzione della funzione cerca_immobili
CREATE OR REPLACE FUNCTION cerca_immobili(
    p_partita_id INTEGER DEFAULT NULL,
    p_comune_nome VARCHAR DEFAULT NULL,
    p_localita_id INTEGER DEFAULT NULL,
    p_natura VARCHAR DEFAULT NULL,
    p_classificazione VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id INTEGER,
    partita_id INTEGER,
    numero_partita INTEGER,
    comune_nome VARCHAR,
    localita_nome VARCHAR,
    natura VARCHAR,
    numero_piani INTEGER,
    numero_vani INTEGER,
    consistenza VARCHAR,
    classificazione VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.id,
        i.partita_id,
        p.numero_partita,
        p.comune_nome,
        l.nome AS localita_nome,
        i.natura,
        i.numero_piani,
        i.numero_vani,
        i.consistenza,
        i.classificazione
    FROM immobile i
    JOIN partita p ON i.partita_id = p.id
    JOIN localita l ON i.localita_id = l.id
    WHERE (p_partita_id IS NULL OR i.partita_id = p_partita_id)
      AND (p_comune_nome IS NULL OR p.comune_nome = p_comune_nome)
      AND (p_localita_id IS NULL OR i.localita_id = p_localita_id)
      AND (p_natura IS NULL OR i.natura ILIKE '%' || p_natura || '%')
      AND (p_classificazione IS NULL OR i.classificazione = p_classificazione)
    ORDER BY p.comune_nome, p.numero_partita, i.natura;
END;
$$ LANGUAGE plpgsql;

-- Correzione della procedura aggiorna_variazione
CREATE OR REPLACE PROCEDURE aggiorna_variazione(
    p_variazione_id INTEGER,
    p_tipo VARCHAR(50) DEFAULT NULL,
    p_data_variazione DATE DEFAULT NULL,
    p_numero_riferimento VARCHAR(50) DEFAULT NULL,
    p_nominativo_riferimento VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE variazione
    SET tipo = COALESCE(p_tipo, tipo),
        data_variazione = COALESCE(p_data_variazione, data_variazione),
        numero_riferimento = COALESCE(p_numero_riferimento, numero_riferimento),
        nominativo_riferimento = COALESCE(p_nominativo_riferimento, nominativo_riferimento)
    WHERE id = p_variazione_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Variazione con ID % non trovata', p_variazione_id;
    END IF;

    RAISE NOTICE 'Variazione con ID % aggiornata con successo', p_variazione_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento della variazione: %', SQLERRM;
END;
$$;

-- Correzione della procedura elimina_variazione
CREATE OR REPLACE PROCEDURE elimina_variazione(
    p_id INTEGER,
    p_forza BOOLEAN DEFAULT FALSE,
    p_ripristina_partita BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;
    v_partita_origine_id INTEGER;
    v_data_variazione DATE;
BEGIN
    -- Verifica l'esistenza di dipendenze
    IF NOT p_forza THEN
        SELECT COUNT(*) INTO v_count FROM contratto WHERE variazione_id = p_id;
        IF v_count > 0 THEN
            RAISE EXCEPTION 'La variazione con ID % ha % contratti associati. Usa p_forza=TRUE per eliminare comunque', p_id, v_count;
        END IF;
    END IF;

    -- Recupera informazioni sulla partita di origine
    SELECT partita_origine_id, data_variazione
    INTO v_partita_origine_id, v_data_variazione
    FROM variazione
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Variazione con ID % non trovata', p_id;
    END IF;

    -- Elimina i contratti collegati se p_forza=TRUE
    IF p_forza THEN
        DELETE FROM contratto WHERE variazione_id = p_id;
    END IF;

    -- Elimina la variazione
    DELETE FROM variazione WHERE id = p_id;

    -- Ripristina la partita di origine se richiesto
    IF p_ripristina_partita AND v_partita_origine_id IS NOT NULL THEN
        UPDATE partita
        SET stato = 'attiva',
            data_chiusura = NULL
        WHERE id = v_partita_origine_id
          AND data_chiusura = v_data_variazione;

        RAISE NOTICE 'La partita di origine con ID % è stata ripristinata come attiva', v_partita_origine_id;
    END IF;

    RAISE NOTICE 'Variazione con ID % eliminata con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione della variazione: %', SQLERRM;
END;
$$;

-- Correzione della funzione cerca_variazioni
CREATE OR REPLACE FUNCTION cerca_variazioni(
    p_tipo VARCHAR DEFAULT NULL,
    p_data_inizio DATE DEFAULT NULL,
    p_data_fine DATE DEFAULT NULL,
    p_partita_origine_id INTEGER DEFAULT NULL,
    p_partita_destinazione_id INTEGER DEFAULT NULL,
    p_comune VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id INTEGER,
    tipo VARCHAR,
    data_variazione DATE,
    partita_origine_id INTEGER,
    partita_origine_numero INTEGER,
    partita_destinazione_id INTEGER,
    partita_destinazione_numero INTEGER,
    comune_nome VARCHAR,
    numero_riferimento VARCHAR,
    nominativo_riferimento VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id,
        v.tipo,
        v.data_variazione,
        v.partita_origine_id,
        po.numero_partita AS partita_origine_numero,
        v.partita_destinazione_id,
        pd.numero_partita AS partita_destinazione_numero,
        po.comune_nome,
        v.numero_riferimento,
        v.nominativo_riferimento
    FROM variazione v
    JOIN partita po ON v.partita_origine_id = po.id
    LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
    WHERE (p_tipo IS NULL OR v.tipo = p_tipo)
      AND (p_data_inizio IS NULL OR v.data_variazione >= p_data_inizio)
      AND (p_data_fine IS NULL OR v.data_variazione <= p_data_fine)
      AND (p_partita_origine_id IS NULL OR v.partita_origine_id = p_partita_origine_id)
      AND (p_partita_destinazione_id IS NULL OR v.partita_destinazione_id = p_partita_destinazione_id)
      AND (p_comune IS NULL OR po.comune_nome = p_comune)
    ORDER BY v.data_variazione DESC, po.comune_nome, po.numero_partita;
END;
$$ LANGUAGE plpgsql;

-- Correzione della procedura inserisci_contratto
CREATE OR REPLACE PROCEDURE inserisci_contratto(
    p_variazione_id INTEGER,
    p_tipo VARCHAR(50),
    p_data_contratto DATE,
    p_notaio VARCHAR(255) DEFAULT NULL,
    p_repertorio VARCHAR(100) DEFAULT NULL,
    p_note TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Verifica se la variazione esiste
    PERFORM 1 FROM variazione WHERE id = p_variazione_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'La variazione con ID % non esiste', p_variazione_id;
    END IF;

    -- Verifica se esiste già un contratto per questa variazione
    PERFORM 1 FROM contratto WHERE variazione_id = p_variazione_id;

    IF FOUND THEN
        RAISE EXCEPTION 'Esiste già un contratto per la variazione con ID %', p_variazione_id;
    END IF;

    -- Inserisci il contratto
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (p_variazione_id, p_tipo, p_data_contratto, p_notaio, p_repertorio, p_note);

    RAISE NOTICE 'Contratto inserito con successo per la variazione con ID %', p_variazione_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''inserimento del contratto: %', SQLERRM;
END;
$$;

-- Correzione della procedura aggiorna_contratto
CREATE OR REPLACE PROCEDURE aggiorna_contratto(
    p_id INTEGER,
    p_tipo VARCHAR(50) DEFAULT NULL,
    p_data_contratto DATE DEFAULT NULL,
    p_notaio VARCHAR(255) DEFAULT NULL,
    p_repertorio VARCHAR(100) DEFAULT NULL,
    p_note TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE contratto
    SET tipo = COALESCE(p_tipo, tipo),
        data_contratto = COALESCE(p_data_contratto, data_contratto),
        notaio = COALESCE(p_notaio, notaio),
        repertorio = COALESCE(p_repertorio, repertorio),
        note = COALESCE(p_note, note)
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contratto con ID % non trovato', p_id;
    END IF;

    RAISE NOTICE 'Contratto con ID % aggiornato con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento del contratto: %', SQLERRM;
END;
$$;

-- Correzione della procedura elimina_contratto
CREATE OR REPLACE PROCEDURE elimina_contratto(
    p_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM contratto WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Contratto con ID % non trovato', p_id;
    END IF;

    RAISE NOTICE 'Contratto con ID % eliminato con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione del contratto: %', SQLERRM;
END;
$$;

-- Correzione della procedura aggiorna_consultazione
CREATE OR REPLACE PROCEDURE aggiorna_consultazione(
    p_id INTEGER,
    p_data DATE DEFAULT NULL,
    p_richiedente VARCHAR(255) DEFAULT NULL,
    p_documento_identita VARCHAR(100) DEFAULT NULL,
    p_motivazione TEXT DEFAULT NULL,
    p_materiale_consultato TEXT DEFAULT NULL,
    p_funzionario_autorizzante VARCHAR(255) DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE consultazione
    SET data = COALESCE(p_data, data),
        richiedente = COALESCE(p_richiedente, richiedente),
        documento_identita = COALESCE(p_documento_identita, documento_identita),
        motivazione = COALESCE(p_motivazione, motivazione),
        materiale_consultato = COALESCE(p_materiale_consultato, materiale_consultato),
        funzionario_autorizzante = COALESCE(p_funzionario_autorizzante, funzionario_autorizzante)
    WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consultazione con ID % non trovata', p_id;
    END IF;

    RAISE NOTICE 'Consultazione con ID % aggiornata con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''aggiornamento della consultazione: %', SQLERRM;
END;
$$;

-- Correzione della procedura elimina_consultazione
CREATE OR REPLACE PROCEDURE elimina_consultazione(
    p_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM consultazione WHERE id = p_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consultazione con ID % non trovata', p_id;
    END IF;

    RAISE NOTICE 'Consultazione con ID % eliminata con successo', p_id;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Errore durante l''eliminazione della consultazione: %', SQLERRM;
END;
$$;

-- Correzione della funzione cerca_consultazioni
CREATE OR REPLACE FUNCTION cerca_consultazioni(
    p_data_inizio DATE DEFAULT NULL,
    p_data_fine DATE DEFAULT NULL,
    p_richiedente VARCHAR DEFAULT NULL,
    p_funzionario VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id INTEGER,
    data DATE,
    richiedente VARCHAR,
    documento_identita VARCHAR,
    motivazione TEXT,
    materiale_consultato TEXT,
    funzionario_autorizzante VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.data,
        c.richiedente,
        c.documento_identita,
        c.motivazione,
        c.materiale_consultato,
        c.funzionario_autorizzante
    FROM consultazione c
    WHERE (p_data_inizio IS NULL OR c.data >= p_data_inizio)
      AND (p_data_fine IS NULL OR c.data <= p_data_fine)
      AND (p_richiedente IS NULL OR c.richiedente ILIKE '%' || p_richiedente || '%')
      AND (p_funzionario IS NULL OR c.funzionario_autorizzante ILIKE '%' || p_funzionario || '%')
    ORDER BY c.data DESC, c.richiedente;
END;
$$ LANGUAGE plpgsql;

-- Correzione della procedura duplica_partita
CREATE OR REPLACE PROCEDURE duplica_partita(
    p_partita_id INTEGER,
    p_nuovo_numero_partita INTEGER,
    p_mantenere_possessori BOOLEAN DEFAULT TRUE,
    p_mantenere_immobili BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita_record partita%ROWTYPE;
    v_nuova_partita_id INTEGER;
    v_possessore_record RECORD;
    v_immobile_record RECORD;
BEGIN
    -- Recupera la partita originale
    SELECT * INTO v_partita_record FROM partita WHERE id = p_partita_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partita con ID % non trovata', p_partita_id;
    END IF;

    -- Verifica che il nuovo numero partita non esista già
    PERFORM 1 FROM partita
    WHERE comune_nome = v_partita_record.comune_nome AND numero_partita = p_nuovo_numero_partita;

    IF FOUND THEN
        RAISE EXCEPTION 'Esiste già una partita con numero % nel comune %',
                        p_nuovo_numero_partita, v_partita_record.comune_nome;
    END IF;

    -- Crea la nuova partita
    INSERT INTO partita(
        comune_nome, numero_partita, tipo, data_impianto, numero_provenienza, stato
    ) VALUES (
        v_partita_record.comune_nome,
        p_nuovo_numero_partita,
        v_partita_record.tipo,
        CURRENT_DATE,
        v_partita_record.numero_partita,
        'attiva'
    )
    RETURNING id INTO v_nuova_partita_id;

    -- Duplica i possessori se richiesto
    IF p_mantenere_possessori THEN
        FOR v_possessore_record IN
            SELECT * FROM partita_possessore WHERE partita_id = p_partita_id
        LOOP
            INSERT INTO partita_possessore(
                partita_id, possessore_id, tipo_partita, titolo, quota
            ) VALUES (
                v_nuova_partita_id,
                v_possessore_record.possessore_id,
                v_possessore_record.tipo_partita,
                v_possessore_record.titolo,
                v_possessore_record.quota
            );
        END LOOP;
    END IF;

    -- Duplica gli immobili se richiesto
    IF p_mantenere_immobili THEN
        FOR v_immobile_record IN
            SELECT * FROM immobile WHERE partita_id = p_partita_id
        LOOP
            INSERT INTO immobile(
                partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione
            ) VALUES (
                v_nuova_partita_id,
                v_immobile_record.localita_id,
                v_immobile_record.natura,
                v_immobile_record.numero_piani,
                v_immobile_record.numero_vani,
                v_immobile_record.consistenza,
                v_immobile_record.classificazione
            );
        END LOOP;
    END IF;

    RAISE NOTICE 'Partita % duplicata con successo. Nuova partita numero % con ID %',
                v_partita_record.numero_partita, p_nuovo_numero_partita, v_nuova_partita_id;
END;
$$;

-- Correzione della procedura trasferisci_immobile
CREATE OR REPLACE PROCEDURE trasferisci_immobile(
    p_immobile_id INTEGER,
    p_nuova_partita_id INTEGER,
    p_registra_variazione BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_vecchia_partita_id INTEGER;
    v_variazione_id INTEGER;
BEGIN
    -- Verifica che l'immobile esista
    SELECT partita_id INTO v_vecchia_partita_id FROM immobile WHERE id = p_immobile_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Immobile con ID % non trovato', p_immobile_id;
    END IF;

    -- Verifica che la nuova partita esista ed è attiva
    IF NOT is_partita_attiva(p_nuova_partita_id) THEN
        RAISE EXCEPTION 'La nuova partita con ID % non esiste o non è attiva', p_nuova_partita_id;
    END IF;

    -- Registra una variazione se richiesto
    IF p_registra_variazione THEN
        INSERT INTO variazione(
            partita_origine_id, partita_destinazione_id, tipo, data_variazione,
            numero_riferimento, nominativo_riferimento
        ) VALUES (
            v_vecchia_partita_id, p_nuova_partita_id, 'Trasferimento', CURRENT_DATE,
            'TI-' || p_immobile_id, 'Trasferimento immobile'
        )
        RETURNING id INTO v_variazione_id;

        RAISE NOTICE 'Registrata variazione con ID % per il trasferimento dell''immobile', v_variazione_id;
    END IF;

    -- Trasferisce l'immobile
    UPDATE immobile SET partita_id = p_nuova_partita_id WHERE id = p_immobile_id;

    RAISE NOTICE 'Immobile con ID % trasferito con successo dalla partita % alla partita %',
                p_immobile_id, v_vecchia_partita_id, p_nuova_partita_id;
END;
$$;

-- Correzione della funzione esporta_partita_json
CREATE OR REPLACE FUNCTION esporta_partita_json(
    p_partita_id INTEGER
)
RETURNS JSON AS $$
DECLARE
    v_json JSON;
BEGIN
    SELECT json_build_object(
        'partita', row_to_json(p),
        'possessori', (
            SELECT json_agg(row_to_json(pos_data))
            FROM (
                SELECT pos.*, pp.titolo, pp.quota
                FROM possessore pos
                JOIN partita_possessore pp ON pos.id = pp.possessore_id
                WHERE pp.partita_id = p.id
            ) pos_data
        ),
        'immobili', (
            SELECT json_agg(row_to_json(imm_data))
            FROM (
                SELECT i.*, l.nome as localita_nome, l.comune_nome, l.tipo as localita_tipo
                FROM immobile i
                JOIN localita l ON i.localita_id = l.id
                WHERE i.partita_id = p.id
            ) imm_data
        ),
        'variazioni', (
            SELECT json_agg(row_to_json(var_data))
            FROM (
                SELECT v.*, c.tipo as contratto_tipo, c.data_contratto, c.notaio, c.repertorio
                FROM variazione v
                LEFT JOIN contratto c ON v.id = c.variazione_id
                WHERE v.partita_origine_id = p.id OR v.partita_destinazione_id = p.id
            ) var_data
        )
    ) INTO v_json
    FROM partita p
    WHERE p.id = p_partita_id;

    IF v_json IS NULL THEN
        RAISE EXCEPTION 'Partita con ID % non trovata', p_partita_id;
    END IF;

    RETURN v_json;
END;
$$ LANGUAGE plpgsql;

-- Correzione della funzione esporta_possessore_json
CREATE OR REPLACE FUNCTION esporta_possessore_json(
    p_possessore_id INTEGER
)
RETURNS JSON AS $$
DECLARE
    v_json JSON;
BEGIN
    SELECT json_build_object(
        'possessore', row_to_json(pos),
        'partite', (
            SELECT json_agg(row_to_json(part_data))
            FROM (
                SELECT p.*, pp.titolo, pp.quota
                FROM partita p
                JOIN partita_possessore pp ON p.id = pp.partita_id
                WHERE pp.possessore_id = pos.id
            ) part_data
        ),
        'immobili', (
            SELECT json_agg(row_to_json(imm_data))
            FROM (
                SELECT i.*, l.nome as localita_nome, p.numero_partita, p.comune_nome
                FROM immobile i
                JOIN partita p ON i.partita_id = p.id
                JOIN localita l ON i.localita_id = l.id
                JOIN partita_possessore pp ON p.id = pp.partita_id
                WHERE pp.possessore_id = pos.id
            ) imm_data
        )
    ) INTO v_json
    FROM possessore pos
    WHERE pos.id = p_possessore_id;

    IF v_json IS NULL THEN
        RAISE EXCEPTION 'Possessore con ID % non trovato', p_possessore_id;
    END IF;

    RETURN v_json;
END;
$$ LANGUAGE plpgsql;

-- *NUOVA DEFINIZIONE CORRETTA* della funzione genera_report_comune
CREATE OR REPLACE FUNCTION genera_report_comune(
    p_comune_nome VARCHAR
)
RETURNS TABLE (
    comune VARCHAR,
    totale_partite BIGINT,
    totale_possessori BIGINT,
    totale_immobili BIGINT,
    partite_attive BIGINT,
    partite_inattive BIGINT,
    immobili_per_classe JSON,
    possessori_per_partita NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH comune_base AS ( -- Seleziona il comune per assicurarsi che esista
        SELECT nome FROM comune WHERE nome = p_comune_nome LIMIT 1
    ),
    immobili_classe_agg AS ( -- CTE per calcolare separatamente il JSON degli immobili
        SELECT
            p_comune_nome AS comune_nome, -- Aggiungi comune_nome per il join
            json_object_agg(COALESCE(i.classificazione, 'Non Class.'), COUNT(*)) AS immobili_json
        FROM immobile i
        JOIN partita p ON i.partita_id = p.id
        WHERE p.comune_nome = p_comune_nome
        GROUP BY p.comune_nome -- Gruppo per comune per ottenere un JSON per comune
    ),
    stats AS ( -- CTE principale per le altre statistiche
        SELECT
            c.nome AS comune_nome,
            COUNT(DISTINCT p.id) AS totale_partite,
            COUNT(DISTINCT pos.id) AS totale_possessori,
            COUNT(DISTINCT i.id) AS totale_immobili,
            COUNT(DISTINCT CASE WHEN p.stato = 'attiva' THEN p.id END) AS partite_attive,
            COUNT(DISTINCT CASE WHEN p.stato = 'inattiva' THEN p.id END) AS partite_inattive
            -- Rimosso il calcolo di immobili_per_classe da qui
        FROM comune c
        LEFT JOIN partita p ON c.nome = p.comune_nome
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        LEFT JOIN immobile i ON p.id = i.partita_id
        WHERE c.nome = p_comune_nome
        GROUP BY c.nome
    )
    -- Join finale per combinare i risultati
    SELECT
        cb.nome AS comune,
        COALESCE(s.totale_partite, 0) AS totale_partite,
        COALESCE(s.totale_possessori, 0) AS totale_possessori,
        COALESCE(s.totale_immobili, 0) AS totale_immobili,
        COALESCE(s.partite_attive, 0) AS partite_attive,
        COALESCE(s.partite_inattive, 0) AS partite_inattive,
        ica.immobili_json AS immobili_per_classe, -- Prendi il JSON dalla CTE separata
        CASE
            WHEN COALESCE(s.totale_partite, 0) = 0 THEN 0
            ELSE COALESCE(s.totale_possessori, 0)::NUMERIC / s.totale_partite
        END AS possessori_per_partita
    FROM comune_base cb
    LEFT JOIN stats s ON cb.nome = s.comune_nome
    LEFT JOIN immobili_classe_agg ica ON cb.nome = ica.comune_nome;

END;
$$ LANGUAGE plpgsql;