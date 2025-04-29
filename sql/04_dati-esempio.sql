-- Imposta lo schema
SET search_path TO catasto, public;

/*
 * Script per l'inserimento di dati di esempio nel database del catasto storico
 * VERSIONE MODIFICATA per compatibilità con comune.id PK
 * Utilizza una procedura per gestire l'inserimento e le relazioni tramite ID.
 */

-- Procedura principale per caricare i dati di esempio
CREATE OR REPLACE PROCEDURE carica_dati_esempio_completo()
LANGUAGE plpgsql
AS $$
DECLARE
    -- IDs Comuni
    v_carcare_id INTEGER;
    v_cairo_id INTEGER;
    v_altare_id INTEGER;

    -- IDs Possessori
    v_fossati_a_id INTEGER;
    v_caviglia_m_id INTEGER;
    v_barberis_g_id INTEGER;
    v_berruti_a_id INTEGER;
    v_ferraro_c_id INTEGER;
    v_bormioli_p_id INTEGER;
    v_rossi_m_id INTEGER; -- Nuovo possessore per test

    -- IDs Località
    v_loc_car_vista_id INTEGER;
    v_loc_car_verdi_id INTEGER;
    v_loc_car_roma_id INTEGER;
    v_loc_cai_ferrere_id INTEGER;
    v_loc_cai_prov_id INTEGER;
    v_loc_alt_palermo_id INTEGER;

    -- IDs Partite
    v_par_car_221_id INTEGER;
    v_par_car_219_id INTEGER;
    v_par_car_245_id INTEGER; -- Secondaria
    v_par_cai_112_id INTEGER;
    v_par_cai_118_id INTEGER; -- Inattiva
    v_par_alt_87_id INTEGER;
    v_par_car_305_id INTEGER; -- Nuova per variazione

    -- IDs Variazioni
    v_var_cai_succ_id INTEGER;
    v_var_car_vend_id INTEGER;

BEGIN
    RAISE NOTICE 'Inizio caricamento dati di esempio...';

    -- === 1. Inserimento Comuni ===
    RAISE NOTICE 'Inserimento Comuni...';
    INSERT INTO comune (nome, provincia, regione) VALUES ('Carcare', 'Savona', 'Liguria') ON CONFLICT (nome) DO UPDATE SET nome=EXCLUDED.nome RETURNING id INTO v_carcare_id;
    INSERT INTO comune (nome, provincia, regione) VALUES ('Cairo Montenotte', 'Savona', 'Liguria') ON CONFLICT (nome) DO UPDATE SET nome=EXCLUDED.nome RETURNING id INTO v_cairo_id;
    INSERT INTO comune (nome, provincia, regione) VALUES ('Altare', 'Savona', 'Liguria') ON CONFLICT (nome) DO UPDATE SET nome=EXCLUDED.nome RETURNING id INTO v_altare_id;
    RAISE NOTICE '  -> Carcare ID: %, Cairo ID: %, Altare ID: %', v_carcare_id, v_cairo_id, v_altare_id;

    -- === 2. Inserimento Registri (Opzionale, se li usi) ===
    RAISE NOTICE 'Inserimento Registri Partite/Matricole...';
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_carcare_id, 1950, 3, 'Buono') ON CONFLICT DO NOTHING;
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_cairo_id, 1948, 5, 'Discreto') ON CONFLICT DO NOTHING;
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_altare_id, 1952, 2, 'Ottimo') ON CONFLICT DO NOTHING;
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_carcare_id, 1950, 2, 'Buono') ON CONFLICT DO NOTHING;
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_cairo_id, 1948, 4, 'Discreto') ON CONFLICT DO NOTHING;
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_altare_id, 1952, 1, 'Ottimo') ON CONFLICT DO NOTHING;

    -- === 3. Inserimento Possessori ===
    RAISE NOTICE 'Inserimento Possessori...';
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Fossati Angelo', 'fu Roberto', 'Fossati Angelo fu Roberto', true) RETURNING id INTO v_fossati_a_id;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Caviglia Maria', 'fu Giuseppe', 'Caviglia Maria fu Giuseppe', true) RETURNING id INTO v_caviglia_m_id;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Barberis Giovanni', 'fu Paolo', 'Barberis Giovanni fu Paolo', true) RETURNING id INTO v_barberis_g_id;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_cairo_id, 'Berruti Antonio', 'fu Luigi', 'Berruti Antonio fu Luigi', true) RETURNING id INTO v_berruti_a_id;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_cairo_id, 'Ferraro Caterina', 'fu Marco', 'Ferraro Caterina fu Marco', true) RETURNING id INTO v_ferraro_c_id;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_altare_id, 'Bormioli Pietro', 'fu Carlo', 'Bormioli Pietro fu Carlo', true) RETURNING id INTO v_bormioli_p_id;
    INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Rossi Marco', 'fu Antonio', 'Rossi Marco fu Antonio', true) RETURNING id INTO v_rossi_m_id; -- Nuovo
    RAISE NOTICE '  -> Inseriti 7 possessori.';

    -- === 4. Inserimento Località ===
    RAISE NOTICE 'Inserimento Località...';
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_carcare_id, 'Regione Vista', 'regione', NULL) RETURNING id INTO v_loc_car_vista_id;
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_carcare_id, 'Via Giuseppe Verdi', 'via', 12) RETURNING id INTO v_loc_car_verdi_id;
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_carcare_id, 'Via Roma', 'via', 5) RETURNING id INTO v_loc_car_roma_id;
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_cairo_id, 'Borgata Ferrere', 'borgata', NULL) RETURNING id INTO v_loc_cai_ferrere_id;
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_cairo_id, 'Strada Provinciale', 'via', 76) RETURNING id INTO v_loc_cai_prov_id;
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_altare_id, 'Via Palermo', 'via', 22) RETURNING id INTO v_loc_alt_palermo_id;
    RAISE NOTICE '  -> Inserite 6 località.';

    -- === 5. Inserimento Partite ===
    RAISE NOTICE 'Inserimento Partite...';
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_carcare_id, 221, 'principale', '1950-05-10', 'attiva') RETURNING id INTO v_par_car_221_id;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_carcare_id, 219, 'principale', '1950-05-10', 'attiva') RETURNING id INTO v_par_car_219_id;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_carcare_id, 245, 'secondaria', '1951-03-22', 'attiva') RETURNING id INTO v_par_car_245_id;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_cairo_id, 112, 'principale', '1948-11-05', 'attiva') RETURNING id INTO v_par_cai_112_id;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato, data_chiusura) VALUES (v_cairo_id, 118, 'principale', '1949-01-15', 'inattiva', '1952-08-15') RETURNING id INTO v_par_cai_118_id; -- Inserita già inattiva per coerenza con variazione
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_altare_id, 87, 'principale', '1952-07-03', 'attiva') RETURNING id INTO v_par_alt_87_id;
    RAISE NOTICE '  -> Inserite 6 partite esistenti.';

    -- === 6. Associazione Partite-Possessori ===
    RAISE NOTICE 'Inserimento Associazioni Partita-Possessore...';
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES
    (v_par_car_221_id, v_fossati_a_id, 'principale', 'proprietà esclusiva', NULL), -- Fossati -> Carcare 221
    (v_par_car_219_id, v_caviglia_m_id, 'principale', 'proprietà esclusiva', NULL), -- Caviglia -> Carcare 219
    (v_par_car_245_id, v_barberis_g_id, 'secondaria', 'comproprietà', '1/2'),    -- Barberis -> Carcare 245 (1/2)
    (v_par_car_245_id, v_caviglia_m_id, 'secondaria', 'comproprietà', '1/2'),    -- Caviglia -> Carcare 245 (1/2)
    (v_par_cai_112_id, v_berruti_a_id, 'principale', 'proprietà esclusiva', NULL), -- Berruti -> Cairo 112
    (v_par_cai_118_id, v_ferraro_c_id, 'principale', 'proprietà esclusiva', NULL), -- Ferraro -> Cairo 118 (partita ora inattiva)
    (v_par_alt_87_id, v_bormioli_p_id, 'principale', 'proprietà esclusiva', NULL); -- Bormioli -> Altare 87

    -- === 7. Relazioni tra partite ===
    RAISE NOTICE 'Inserimento Relazioni Partita...';
    INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id) VALUES (v_par_car_219_id, v_par_car_245_id); -- Carcare 219 -> 245

    -- === 8. Inserimento Immobili ===
    RAISE NOTICE 'Inserimento Immobili...';
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES
    (v_par_car_221_id, v_loc_car_vista_id, 'Molino da cereali', 2, NULL, '150 mq', 'Artigianale'),
    (v_par_car_219_id, v_loc_car_verdi_id, 'Casa', 3, 8, '210 mq', 'Abitazione civile'),
    (v_par_car_219_id, v_loc_car_verdi_id, 'Giardino', NULL, NULL, '50 mq', 'Area scoperta'), -- Secondo immobile su Carcare 219
    (v_par_car_245_id, v_loc_car_roma_id, 'Magazzino', 1, NULL, '80 mq', 'Deposito'),
    (v_par_cai_112_id, v_loc_cai_ferrere_id, 'Fabbricato rurale', 2, 5, '180 mq', 'Abitazione rurale'),
    (v_par_cai_118_id, v_loc_cai_prov_id, 'Casa', 2, 6, '160 mq', 'Abitazione civile'), -- Immobile su partita inattiva
    (v_par_alt_87_id, v_loc_alt_palermo_id, 'Laboratorio', 1, NULL, '120 mq', 'Artigianale');
    RAISE NOTICE '  -> Inseriti 7 immobili.';

    -- === 9. Inserimento Variazioni e Contratti ===
    RAISE NOTICE 'Inserimento Variazioni e Contratti...';
    -- 9.1 Successione che ha reso inattiva Cairo 118
    INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento) VALUES
    (v_par_cai_118_id, NULL, 'Successione', '1952-08-15', '22/52', 'Ferraro Caterina') RETURNING id INTO v_var_cai_succ_id;
    INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note) VALUES
    (v_var_cai_succ_id, 'Successione', '1952-08-10', 'Notaio Bianchi', '1234/52', 'Successione per morte del proprietario Luigi Ferraro');

    -- 9.2 Vendita parziale da Fossati a Rossi (Nuova partita)
    --     Crea la nuova partita per Rossi
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato, numero_provenienza) VALUES
    (v_carcare_id, 305, 'principale', '1953-02-20', 'attiva', 221) RETURNING id INTO v_par_car_305_id;
    --     Associa Rossi alla nuova partita
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo) VALUES
    (v_par_car_305_id, v_rossi_m_id, 'principale', 'proprietà esclusiva');
    --     Registra la variazione (Fossati -> Rossi)
    INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento) VALUES
    (v_par_car_221_id, v_par_car_305_id, 'Vendita', '1953-02-20', 'Atto Not. Verdi', 'Rossi Marco') RETURNING id INTO v_var_car_vend_id;
    INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note) VALUES
    (v_var_car_vend_id, 'Vendita', '1953-02-15', 'Notaio Verdi', '567/53', 'Vendita parziale di immobile da partita 221');
    --     Trasferisci un immobile (il Molino) da Fossati a Rossi
    --     NOTA: Qui assumiamo di sapere l'ID dell'immobile (che è 1 secondo l'ordine di INSERT)
    UPDATE immobile SET partita_id = v_par_car_305_id WHERE id = (SELECT id FROM immobile WHERE partita_id = v_par_car_221_id AND natura='Molino da cereali');
    --     Se Fossati non ha più immobili, la partita 221 dovrebbe diventare inattiva?
    --     In questo esempio semplice, la lasciamo attiva assumendo che ci siano altri immobili non trasferiti.

    -- === 10. Inserimento Consultazioni ===
    RAISE NOTICE 'Inserimento Consultazioni...';
    INSERT INTO consultazione (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante) VALUES
    ('2025-04-01', 'Mario Bianchi', 'CI AB1234567', 'Ricerca storica', 'Registro partite Carcare 1950', 'Dott. Verdi'),
    ('2025-04-05', 'Studio Legale Rossi', 'Tessera Ordine 55213', 'Verifica proprietà', 'Partite 221 e 305 Carcare', 'Dott. Verdi'); -- Aggiornato materiale

    RAISE NOTICE 'Caricamento dati di esempio completato con successo.';

END;
$$;

-- Esempio di chiamata per caricare i dati
-- Questa chiamata può essere eseguita una sola volta dopo aver creato le tabelle e la procedura.
-- Inseriscila alla fine dello script 04 o eseguila separatamente.
DO $$
BEGIN
    RAISE NOTICE 'Tentativo di caricare i dati di esempio...';
    CALL carica_dati_esempio_completo();
END $$;