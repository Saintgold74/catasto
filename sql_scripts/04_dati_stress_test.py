-- File: 04_dati_stress_test.sql
-- Oggetto: Popola il database con un ampio set di dati per stress test.
-- ATTENZIONE: Eseguire su un database PULITO o dopo aver troncato le tabelle rilevanti.
-- Data: 03/05/2025

SET search_path TO catasto, public;

-- Procedura per la generazione massiva di dati
CREATE OR REPLACE PROCEDURE popola_dati_stress_test(
    p_num_comuni INTEGER DEFAULT 5,
    p_possessori_per_comune INTEGER DEFAULT 100,
    p_partite_per_possessore_medio INTEGER DEFAULT 5,
    p_immobili_per_partita_media INTEGER DEFAULT 3,
    p_percentuale_variazioni FLOAT DEFAULT 0.1 -- Percentuale di partite che subiscono una variazione
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_comune_id INTEGER;
    v_possessore_id INTEGER;
    v_partita_id INTEGER;
    v_localita_id INTEGER;
    v_immobile_id INTEGER;
    v_variazione_id INTEGER;
    v_partita_origine_id INTEGER;
    v_partita_destinazione_id INTEGER;
    v_comune_counter INTEGER;
    v_possessore_counter INTEGER;
    v_partita_counter INTEGER;
    v_immobile_counter INTEGER;
    v_localita_counter INTEGER;
    v_random_float FLOAT;
    v_random_int INTEGER;
    v_nome_comune TEXT;
    v_nome_possessore TEXT;
    v_nome_localita TEXT;
    v_numero_partita INTEGER;
    v_start_time TIMESTAMPTZ(0);
    v_end_time TIMESTAMPTZ(0);
    v_last_partita_num INTEGER := 1000; -- Numero di partenza per le partite generate
    v_possessore_ids INTEGER[];
    v_partita_ids INTEGER[];
    v_localita_ids INTEGER[];
BEGIN
    v_start_time := clock_timestamp();
    RAISE NOTICE '[STRESS TEST] Inizio popolamento: %', v_start_time;

    -- 1. Genera Comuni
    RAISE NOTICE 'Generazione % Comuni...', p_num_comuni;
    FOR v_comune_counter IN 1..p_num_comuni LOOP
        v_nome_comune := 'Comune Stress Test ' || v_comune_counter;
        INSERT INTO comune (nome, provincia, regione)
        VALUES (v_nome_comune, 'Prov ' || v_comune_counter, 'Regione Stress')
        RETURNING id INTO v_comune_id;

        -- Reset per ogni comune
        v_possessore_ids := '{}';
        v_partita_ids := '{}';
        v_localita_ids := '{}';
        v_last_partita_num := 1000; -- Resetta numerazione partite per comune

        -- 2. Genera Località per il Comune
        v_localita_counter := 1;
        WHILE v_localita_counter <= p_possessori_per_comune / 5 LOOP -- Meno località dei possessori
             v_nome_localita := 'Via Stress ' || v_comune_counter || '-' || v_localita_counter;
             INSERT INTO localita (comune_id, nome, tipo, civico)
             VALUES (v_comune_id, v_nome_localita, 'via', floor(random()*100 + 1)::int)
             RETURNING id INTO v_localita_id;
             v_localita_ids := array_append(v_localita_ids, v_localita_id);
             v_localita_counter := v_localita_counter + 1;
        END LOOP;
        IF array_length(v_localita_ids, 1) IS NULL THEN
             RAISE WARNING 'Nessuna località creata per comune ID %, impossibile creare immobili.', v_comune_id;
             CONTINUE; -- Salta al prossimo comune se non ci sono località
        END IF;

        -- 3. Genera Possessori per il Comune
        RAISE NOTICE '  Generazione % Possessori per Comune ID %...', p_possessori_per_comune, v_comune_id;
        FOR v_possessore_counter IN 1..p_possessori_per_comune LOOP
            v_nome_possessore := 'Possessore ' || v_comune_counter || '-' || v_possessore_counter || ' Rossi';
            INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
            VALUES (v_comune_id, 'Stress ' || v_possessore_counter, 'fu Stress Test', v_nome_possessore, TRUE)
            RETURNING id INTO v_possessore_id;
            v_possessore_ids := array_append(v_possessore_ids, v_possessore_id);
        END LOOP;

        -- 4. Genera Partite e Immobili
        RAISE NOTICE '  Generazione Partite e Immobili...';
        FOR v_possessore_id IN SELECT unnest(v_possessore_ids) LOOP
            FOR v_partita_counter IN 1..p_partite_per_possessore_medio LOOP
                v_last_partita_num := v_last_partita_num + 1;
                INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
                VALUES (v_comune_id, v_last_partita_num, 'principale', NOW()::date - interval '1 year' * floor(random()*50), 'attiva')
                RETURNING id INTO v_partita_id;
                v_partita_ids := array_append(v_partita_ids, v_partita_id);

                -- Collega il possessore alla partita (proprietà esclusiva per semplicità qui)
                INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo)
                VALUES (v_partita_id, v_possessore_id, 'principale', 'proprietà esclusiva');

                 -- Genera Immobili per la partita
                FOR v_immobile_counter IN 1..p_immobili_per_partita_media LOOP
                    -- Seleziona una località casuale TRA QUELLE DEL COMUNE CORRENTE
                    v_localita_id := v_localita_ids[floor(random()*array_length(v_localita_ids, 1) + 1)];
                    INSERT INTO immobile (partita_id, localita_id, natura, classificazione, consistenza)
                    VALUES (
                        v_partita_id,
                        v_localita_id,
                        'Edificio Stress ' || v_immobile_counter,
                        'Classe Stress ' || floor(random()*5+1),
                        floor(random()*200 + 50)::text || ' mq'
                    );
                END LOOP;
            END LOOP;
        END LOOP;

        -- 5. Genera Variazioni e Contratti (per una percentuale delle partite)
        RAISE NOTICE '  Generazione Variazioni e Contratti...';
        FOR v_partita_origine_id IN SELECT unnest(v_partita_ids) LOOP
             v_random_float := random();
             IF v_random_float < p_percentuale_variazioni THEN
                 -- Crea una nuova partita di destinazione nello stesso comune
                 v_last_partita_num := v_last_partita_num + 1;
                 INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, numero_provenienza, stato)
                 VALUES (v_comune_id, v_last_partita_num, 'principale', NOW()::date - interval '1 day' * floor(random()*100), (SELECT numero_partita FROM partita WHERE id=v_partita_origine_id), 'attiva')
                 RETURNING id INTO v_partita_destinazione_id;

                 -- Seleziona un possessore casuale per la nuova partita (dal pool del comune)
                 v_possessore_id := v_possessore_ids[floor(random()*array_length(v_possessore_ids, 1) + 1)];
                 INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo)
                 VALUES (v_partita_destinazione_id, v_possessore_id, 'principale', 'proprietà esclusiva');

                 -- Crea la variazione
                 INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione)
                 VALUES (v_partita_origine_id, v_partita_destinazione_id, 'Vendita Stress', NOW()::date - interval '1 day' * floor(random()*100))
                 RETURNING id INTO v_variazione_id;

                 -- Crea il contratto associato
                 INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio)
                 VALUES (v_variazione_id, 'Vendita Stress', NOW()::date - interval '1 day' * floor(random()*100 + 1), 'Notaio Stress Test');

                 -- Chiudi la partita di origine
                 UPDATE partita SET stato = 'inattiva', data_chiusura = (SELECT data_variazione FROM variazione WHERE id = v_variazione_id)
                 WHERE id = v_partita_origine_id;

                 -- Trasferisci gli immobili (semplificato: trasferisce tutti)
                 UPDATE immobile SET partita_id = v_partita_destinazione_id
                 WHERE partita_id = v_partita_origine_id;

             END IF;
        END LOOP;

    END LOOP; -- Fine loop comuni

    v_end_time := clock_timestamp();
    RAISE NOTICE '[STRESS TEST] Fine popolamento: %', v_end_time;
    RAISE NOTICE '[STRESS TEST] Durata totale: %', v_end_time - v_start_time;

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING '[STRESS TEST] Errore durante il popolamento: % - SQLSTATE: %', SQLERRM, SQLSTATE;
    -- Non fare rollback, così vediamo fin dove è arrivato
END;
$$;

-- Chiamata alla procedura per generare i dati
-- Esempio: 5 comuni, 100 possessori/comune, 5 partite/possessore, 3 immobili/partita, 10% variazioni
-- ATTENZIONE: Numeri elevati possono richiedere tempo e risorse significative!
DO $$ BEGIN RAISE NOTICE 'Esecuzione procedura popola_dati_stress_test...'; END $$;
CALL popola_dati_stress_test(
    p_num_comuni => 5,
    p_possessori_per_comune => 100,
    p_partite_per_possessore_medio => 5,
    p_immobili_per_partita_media => 3,
    p_percentuale_variazioni => 0.10
);
DO $$ BEGIN RAISE NOTICE 'Procedura popola_dati_stress_test completata.'; END $$;

-- Eventuale chiamata per aggiornare le viste materializzate dopo il popolamento
-- CALL aggiorna_tutte_statistiche(); -- Se definita e necessaria