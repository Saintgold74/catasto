-- File: 04_dati_stress_test.sql (v1.3 - Con gestione conflitti)
SET search_path TO catasto, public;

CREATE OR REPLACE PROCEDURE popola_dati_stress_test(
    p_num_comuni INTEGER DEFAULT 5,
    p_possessori_per_comune INTEGER DEFAULT 100,
    p_partite_per_possessore_medio INTEGER DEFAULT 5,
    p_immobili_per_partita_media INTEGER DEFAULT 3,
    p_percentuale_variazioni FLOAT DEFAULT 0.1
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_comune_id INTEGER;
    v_possessore_id INTEGER;
    v_partita_id INTEGER;
    v_localita_id INTEGER;
    v_variazione_id INTEGER;
    v_partita_origine_id INTEGER;
    v_partita_destinazione_id INTEGER;
    v_nome_comune TEXT;
    v_start_time TIMESTAMPTZ(0);
    v_end_time TIMESTAMPTZ(0);
    v_last_partita_num INTEGER := 1000;
    v_possessore_ids INTEGER[];
    v_partita_ids INTEGER[];
    v_localita_ids INTEGER[];
    v_tipi_localita_ids INTEGER[];
    v_random_tipo_id INTEGER;
    v_total_partite_created INTEGER := 0;
BEGIN
    v_start_time := clock_timestamp();
    RAISE NOTICE '[STRESS TEST] Inizio popolamento: %', v_start_time;

    SELECT array_agg(id) INTO v_tipi_localita_ids FROM catasto.tipo_localita;
    IF v_tipi_localita_ids IS NULL OR array_length(v_tipi_localita_ids, 1) = 0 THEN
        RAISE EXCEPTION 'Tabella tipo_localita vuota. Popolarla prima di eseguire lo stress test.';
    END IF;

    FOR i IN 1..p_num_comuni LOOP
        v_nome_comune := 'Comune Stress Test ' || i;

        -- --- INIZIO CORREZIONE ---
        -- Inserisce il comune solo se non esiste già.
        INSERT INTO comune (nome, provincia, regione)
        VALUES (v_nome_comune, 'Prov ' || i, 'Regione Stress')
        ON CONFLICT (nome) DO NOTHING;
        
        -- Recupera l'ID del comune, che sia stato appena inserito o che esistesse già.
        SELECT id INTO v_comune_id FROM comune WHERE nome = v_nome_comune;
        -- --- FINE CORREZIONE ---

        RAISE NOTICE '--- Gestione Comune %/%: % (ID: %) ---', i, p_num_comuni, v_nome_comune, v_comune_id;

        -- (Il resto dello script da qui in poi rimane invariato)
        v_possessore_ids := '{}';
        v_partita_ids := '{}';
        v_localita_ids := '{}';
        v_last_partita_num := 1000;

        FOR j IN 1..(p_possessori_per_comune / 10) LOOP
             v_random_tipo_id := v_tipi_localita_ids[floor(random()*array_length(v_tipi_localita_ids, 1) + 1)];
             INSERT INTO localita (comune_id, nome, tipo_id, civico)
             VALUES (v_comune_id, 'Via Stress ' || i || '-' || j, v_random_tipo_id, floor(random()*100 + 1)::int)
             ON CONFLICT (comune_id, nome, civico) DO NOTHING
             RETURNING id INTO v_localita_id;
             IF v_localita_id IS NOT NULL THEN
                v_localita_ids := array_append(v_localita_ids, v_localita_id);
             END IF;
        END LOOP;
        
        RAISE NOTICE '  -> Gestite % localita per il comune.', array_length(v_localita_ids, 1);

        IF array_length(v_localita_ids, 1) IS NULL THEN
             RAISE WARNING 'Nessuna localita trovata o creata per comune ID %, impossibile creare immobili.', v_comune_id;
             CONTINUE;
        END IF;
        
        -- (continua con la logica per possessori, partite, etc.)

    END LOOP;

    v_end_time := clock_timestamp();
    RAISE NOTICE '[STRESS TEST] Fine popolamento: %', v_end_time;
    RAISE NOTICE '[STRESS TEST] Durata totale: %', v_end_time - v_start_time;

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING '[STRESS TEST] Errore durante il popolamento: % - SQLSTATE: %', SQLERRM, SQLSTATE;
END;
$$;


-- Chiamata alla procedura (invariata)
DO $$ BEGIN RAISE NOTICE 'Esecuzione procedura popola_dati_stress_test...'; END $$;
CALL popola_dati_stress_test(
    p_num_comuni => 5,
    p_possessori_per_comune => 100,
    p_partite_per_possessore_medio => 5,
    p_immobili_per_partita_media => 3,
    p_percentuale_variazioni => 0.10
);
DO $$ BEGIN RAISE NOTICE 'Procedura popola_dati_stress_test completata.'; END $$;