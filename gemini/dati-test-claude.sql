-- File: dati_test_migliorati.sql
-- Oggetto: Dati di test realistici per il Catasto Storico
-- Data: 19/05/2025
-- Autore: Claude

SET search_path TO catasto, public;

-- Procedura generale per caricare dati di test realistici
CREATE OR REPLACE PROCEDURE carica_dati_test_realistici()
LANGUAGE plpgsql AS $$
DECLARE
    -- IDs Comuni
    v_carcare_id INTEGER;
    v_cairo_id INTEGER;
    v_altare_id INTEGER;
    v_millesimo_id INTEGER;
    v_cosseria_id INTEGER;

    -- IDs Possessori
    v_rossi_g_id INTEGER;
    v_bianchi_a_id INTEGER;
    v_ferraro_c_id INTEGER;
    v_olivieri_m_id INTEGER;
    v_gallo_p_id INTEGER;
    v_bruno_f_id INTEGER;
    v_martini_e_id INTEGER;
    v_ricci_l_id INTEGER;
    v_esposito_s_id INTEGER;
    v_romano_d_id INTEGER;

    -- IDs Località
    v_loc_car_roma_id INTEGER;
    v_loc_car_cavour_id INTEGER;
    v_loc_car_garibaldi_id INTEGER;
    v_loc_car_mazzini_id INTEGER;
    v_loc_car_dante_id INTEGER;
    v_loc_cai_italia_id INTEGER;
    v_loc_cai_colombo_id INTEGER;
    v_loc_cai_marconi_id INTEGER;
    v_loc_cai_matteotti_id INTEGER;
    v_loc_alt_vittorio_id INTEGER;
    v_loc_alt_trento_id INTEGER;
    v_loc_mil_fontane_id INTEGER;
    v_loc_mil_castello_id INTEGER;
    v_loc_cos_provinciale_id INTEGER;
    v_loc_cos_piave_id INTEGER;

    -- IDs Partite
    v_par_car_101_id INTEGER;
    v_par_car_102_id INTEGER;
    v_par_car_103_id INTEGER;
    v_par_car_104_id INTEGER;
    v_par_cai_201_id INTEGER;
    v_par_cai_202_id INTEGER;
    v_par_cai_203_id INTEGER;
    v_par_alt_301_id INTEGER;
    v_par_alt_302_id INTEGER;
    v_par_mil_401_id INTEGER;
    v_par_cos_501_id INTEGER;

    -- IDs Variazioni
    v_var_succ_car_id INTEGER;
    v_var_vend_cai_id INTEGER;
    v_var_fraz_alt_id INTEGER;
    v_var_vend_car_nuova_id INTEGER;

BEGIN
    -- === 1. Inserimento Comuni ===
    RAISE NOTICE 'Inserimento Comuni...';
    INSERT INTO comune (nome, provincia, regione) 
    VALUES ('Carcare', 'Savona', 'Liguria') 
    ON CONFLICT (nome) DO UPDATE SET provincia = 'Savona'
    RETURNING id INTO v_carcare_id;
    
    INSERT INTO comune (nome, provincia, regione) 
    VALUES ('Cairo Montenotte', 'Savona', 'Liguria') 
    ON CONFLICT (nome) DO UPDATE SET provincia = 'Savona'
    RETURNING id INTO v_cairo_id;
    
    INSERT INTO comune (nome, provincia, regione) 
    VALUES ('Altare', 'Savona', 'Liguria') 
    ON CONFLICT (nome) DO UPDATE SET provincia = 'Savona'
    RETURNING id INTO v_altare_id;
    
    INSERT INTO comune (nome, provincia, regione) 
    VALUES ('Millesimo', 'Savona', 'Liguria') 
    ON CONFLICT (nome) DO UPDATE SET provincia = 'Savona'
    RETURNING id INTO v_millesimo_id;
    
    INSERT INTO comune (nome, provincia, regione) 
    VALUES ('Cosseria', 'Savona', 'Liguria') 
    ON CONFLICT (nome) DO UPDATE SET provincia = 'Savona'
    RETURNING id INTO v_cosseria_id;

    -- Recupera gli ID se esistevano già
    IF v_carcare_id IS NULL THEN
        SELECT id INTO v_carcare_id FROM comune WHERE nome = 'Carcare';
    END IF;
    IF v_cairo_id IS NULL THEN
        SELECT id INTO v_cairo_id FROM comune WHERE nome = 'Cairo Montenotte';
    END IF;
    IF v_altare_id IS NULL THEN
        SELECT id INTO v_altare_id FROM comune WHERE nome = 'Altare';
    END IF;
    IF v_millesimo_id IS NULL THEN
        SELECT id INTO v_millesimo_id FROM comune WHERE nome = 'Millesimo';
    END IF;
    IF v_cosseria_id IS NULL THEN
        SELECT id INTO v_cosseria_id FROM comune WHERE nome = 'Cosseria';
    END IF;

    RAISE NOTICE 'Comuni creati: Carcare(ID:%), Cairo Montenotte(ID:%), Altare(ID:%), Millesimo(ID:%), Cosseria(ID:%)', 
                 v_carcare_id, v_cairo_id, v_altare_id, v_millesimo_id, v_cosseria_id;

    -- === 2. Inserimento Registri ===
    RAISE NOTICE 'Inserimento Registri Partite/Matricole...';
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) 
    VALUES (v_carcare_id, 1951, 4, 'Ottimo') 
    ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) 
    VALUES (v_cairo_id, 1950, 6, 'Buono') 
    ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) 
    VALUES (v_altare_id, 1952, 3, 'Discreto') 
    ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) 
    VALUES (v_millesimo_id, 1949, 2, 'Buono') 
    ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) 
    VALUES (v_cosseria_id, 1953, 1, 'Ottimo') 
    ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) 
    VALUES (v_carcare_id, 1951, 3, 'Ottimo') 
    ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) 
    VALUES (v_cairo_id, 1950, 5, 'Buono') 
    ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) 
    VALUES (v_altare_id, 1952, 2, 'Discreto') 
    ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) 
    VALUES (v_millesimo_id, 1949, 2, 'Buono') 
    ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) 
    VALUES (v_cosseria_id, 1953, 1, 'Ottimo') 
    ON CONFLICT (comune_id, anno_impianto) DO NOTHING;

    -- === 3. Inserimento Possessori ===
    RAISE NOTICE 'Inserimento Possessori...';
    
    -- Possessori di Carcare
    SELECT id INTO v_rossi_g_id FROM possessore WHERE comune_id = v_carcare_id AND nome_completo = 'Rossi Giovanni fu Ernesto';
    IF v_rossi_g_id IS NULL THEN
        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
        VALUES (v_carcare_id, 'Rossi Giovanni', 'fu Ernesto', 'Rossi Giovanni fu Ernesto', true)
        RETURNING id INTO v_rossi_g_id;
    END IF;
    
    SELECT id INTO v_bianchi_a_id FROM possessore WHERE comune_id = v_carcare_id AND nome_completo = 'Bianchi Angela fu Pietro';
    IF v_bianchi_a_id IS NULL THEN
        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
        VALUES (v_carcare_id, 'Bianchi Angela', 'fu Pietro', 'Bianchi Angela fu Pietro', true)
        RETURNING id INTO v_bianchi_a_id;
    END IF;
    
    -- Possessori di Cairo Montenotte
    SELECT id INTO v_ferraro_c_id FROM possessore WHERE comune_id = v_cairo_id AND nome_completo = 'Ferraro Carlo fu Mario';
    IF v_ferraro_c_id IS NULL THEN
        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
        VALUES (v_cairo_id, 'Ferraro Carlo', 'fu Mario', 'Ferraro Carlo fu Mario', true)
        RETURNING id INTO v_ferraro_c_id;
    END IF;
    
    SELECT id INTO v_olivieri_m_id FROM possessore WHERE comune_id = v_cairo_id AND nome_completo = 'Olivieri Maria fu Giuseppe';
    IF v_olivieri_m_id IS NULL THEN
        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
        VALUES (v_cairo_id, 'Olivieri Maria', 'fu Giuseppe', 'Olivieri Maria fu Giuseppe', true)
        RETURNING id INTO v_olivieri_m_id;
    END IF;
    
    SELECT id INTO v_gallo_p_id FROM possessore WHERE comune_id = v_cairo_id AND nome_completo = 'Gallo Paolo fu Vincenzo';
    IF v_gallo_p_id IS NULL THEN
        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
        VALUES (v_cairo_id, 'Gallo Paolo', 'fu Vincenzo', 'Gallo Paolo fu Vincenzo', true)
        RETURNING id INTO v_gallo_p_id;
    END IF;
    
    -- Possessori di Altare
    SELECT id INTO v_bruno_f_id FROM possessore WHERE comune_id = v_altare_id AND nome_completo = 'Bruno Francesco fu Antonio';
    IF v_bruno_f_id IS NULL THEN
        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
        VALUES (v_altare_id, 'Bruno Francesco', 'fu Antonio', 'Bruno Francesco fu Antonio', true)
        RETURNING id INTO v_bruno_f_id;
    END IF;
    
    SELECT id INTO v_martini_e_id FROM possessore WHERE comune_id = v_altare_id AND nome_completo = 'Martini Elena fu Domenico';
    IF v_martini_e_id IS NULL THEN
        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
        VALUES (v_altare_id, 'Martini Elena', 'fu Domenico', 'Martini Elena fu Domenico', true)
        RETURNING id INTO v_martini_e_id;
    END IF;
    
    -- Possessori di Millesimo
    SELECT id INTO v_ricci_l_id FROM possessore WHERE comune_id = v_millesimo_id AND nome_completo = 'Ricci Luigi fu Roberto';
    IF v_ricci_l_id IS NULL THEN
        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
        VALUES (v_millesimo_id, 'Ricci Luigi', 'fu Roberto', 'Ricci Luigi fu Roberto', true)
        RETURNING id INTO v_ricci_l_id;
    END IF;
    
    -- Possessori di Cosseria
    SELECT id INTO v_esposito_s_id FROM possessore WHERE comune_id = v_cosseria_id AND nome_completo = 'Esposito Sofia fu Michele';
    IF v_esposito_s_id IS NULL THEN
        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
        VALUES (v_cosseria_id, 'Esposito Sofia', 'fu Michele', 'Esposito Sofia fu Michele', true)
        RETURNING id INTO v_esposito_s_id;
    END IF;
    
    SELECT id INTO v_romano_d_id FROM possessore WHERE comune_id = v_cosseria_id AND nome_completo = 'Romano Davide fu Salvatore';
    IF v_romano_d_id IS NULL THEN
        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
        VALUES (v_cosseria_id, 'Romano Davide', 'fu Salvatore', 'Romano Davide fu Salvatore', true)
        RETURNING id INTO v_romano_d_id;
    END IF;

    RAISE NOTICE 'Inseriti 10 possessori nei vari comuni';

    -- === 4. Inserimento Località ===
    RAISE NOTICE 'Inserimento Località...';
    
    -- Località di Carcare
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_carcare_id, 'Via Roma', 'via', 15)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_car_roma_id;
    
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_carcare_id, 'Via Cavour', 'via', 8)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_car_cavour_id;
    
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_carcare_id, 'Via Garibaldi', 'via', 22)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_car_garibaldi_id;
    
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_carcare_id, 'Via Mazzini', 'via', 5)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_car_mazzini_id;
    
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_carcare_id, 'Via Dante Alighieri', 'via', 12)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_car_dante_id;
    
    -- Località di Cairo Montenotte
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_cairo_id, 'Corso Italia', 'via', 45)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_cai_italia_id;
    
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_cairo_id, 'Via Cristoforo Colombo', 'via', 32)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_cai_colombo_id;
    
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_cairo_id, 'Via Guglielmo Marconi', 'via', 18)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_cai_marconi_id;
    
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_cairo_id, 'Via Giacomo Matteotti', 'via', 7)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_cai_matteotti_id;
    
    -- Località di Altare
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_altare_id, 'Corso Vittorio Emanuele', 'via', 28)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_alt_vittorio_id;
    
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_altare_id, 'Via Trento e Trieste', 'via', 10)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_alt_trento_id;
    
    -- Località di Millesimo
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_millesimo_id, 'Via delle Fontane', 'via', 5)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_mil_fontane_id;
    
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_millesimo_id, 'Via del Castello', 'via', 3)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_mil_castello_id;
    
    -- Località di Cosseria
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_cosseria_id, 'Strada Provinciale', 'via', 24)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_cos_provinciale_id;
    
    INSERT INTO localita (comune_id, nome, tipo, civico)
    VALUES (v_cosseria_id, 'Via Piave', 'via', 9)
    ON CONFLICT (comune_id, nome, civico) DO NOTHING
    RETURNING id INTO v_loc_cos_piave_id;
    
    -- Recupera gli ID se esistevano già
    SELECT id INTO v_loc_car_roma_id FROM localita WHERE comune_id = v_carcare_id AND nome = 'Via Roma' AND civico = 15;
    SELECT id INTO v_loc_car_cavour_id FROM localita WHERE comune_id = v_carcare_id AND nome = 'Via Cavour' AND civico = 8;
    SELECT id INTO v_loc_car_garibaldi_id FROM localita WHERE comune_id = v_carcare_id AND nome = 'Via Garibaldi' AND civico = 22;
    SELECT id INTO v_loc_car_mazzini_id FROM localita WHERE comune_id = v_carcare_id AND nome = 'Via Mazzini' AND civico = 5;
    SELECT id INTO v_loc_car_dante_id FROM localita WHERE comune_id = v_carcare_id AND nome = 'Via Dante Alighieri' AND civico = 12;
    SELECT id INTO v_loc_cai_italia_id FROM localita WHERE comune_id = v_cairo_id AND nome = 'Corso Italia' AND civico = 45;
    SELECT id INTO v_loc_cai_colombo_id FROM localita WHERE comune_id = v_cairo_id AND nome = 'Via Cristoforo Colombo' AND civico = 32;
    SELECT id INTO v_loc_cai_marconi_id FROM localita WHERE comune_id = v_cairo_id AND nome = 'Via Guglielmo Marconi' AND civico = 18;
    SELECT id INTO v_loc_cai_matteotti_id FROM localita WHERE comune_id = v_cairo_id AND nome = 'Via Giacomo Matteotti' AND civico = 7;
    SELECT id INTO v_loc_alt_vittorio_id FROM localita WHERE comune_id = v_altare_id AND nome = 'Corso Vittorio Emanuele' AND civico = 28;
    SELECT id INTO v_loc_alt_trento_id FROM localita WHERE comune_id = v_altare_id AND nome = 'Via Trento e Trieste' AND civico = 10;
    SELECT id INTO v_loc_mil_fontane_id FROM localita WHERE comune_id = v_millesimo_id AND nome = 'Via delle Fontane' AND civico = 5;
    SELECT id INTO v_loc_mil_castello_id FROM localita WHERE comune_id = v_millesimo_id AND nome = 'Via del Castello' AND civico = 3;
    SELECT id INTO v_loc_cos_provinciale_id FROM localita WHERE comune_id = v_cosseria_id AND nome = 'Strada Provinciale' AND civico = 24;
    SELECT id INTO v_loc_cos_piave_id FROM localita WHERE comune_id = v_cosseria_id AND nome = 'Via Piave' AND civico = 9;

    RAISE NOTICE 'Inserite 15 località nei vari comuni';

    -- === 5. Inserimento Partite ===
    RAISE NOTICE 'Inserimento Partite...';
    
    -- Partite di Carcare
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (v_carcare_id, 101, 'principale', '1951-03-15', 'attiva')
    ON CONFLICT (comune_id, numero_partita) DO NOTHING
    RETURNING id INTO v_par_car_101_id;
    
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (v_carcare_id, 102, 'principale', '1951-03-22', 'attiva')
    ON CONFLICT (comune_id, numero_partita) DO NOTHING
    RETURNING id INTO v_par_car_102_id;
    
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (v_carcare_id, 103, 'secondaria', '1951-04-05', 'attiva')
    ON CONFLICT (comune_id, numero_partita) DO NOTHING
    RETURNING id INTO v_par_car_103_id;
    
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (v_carcare_id, 104, 'principale', '1951-04-18', 'attiva')
    ON CONFLICT (comune_id, numero_partita) DO NOTHING
    RETURNING id INTO v_par_car_104_id;
    
    -- Partite di Cairo Montenotte
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (v_cairo_id, 201, 'principale', '1950-06-10', 'attiva')
    ON CONFLICT (comune_id, numero_partita) DO NOTHING
    RETURNING id INTO v_par_cai_201_id;
    
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (v_cairo_id, 202, 'principale', '1950-07-05', 'attiva')
    ON CONFLICT (comune_id, numero_partita) DO NOTHING
    RETURNING id INTO v_par_cai_202_id;
    
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato, data_chiusura)
    VALUES (v_cairo_id, 203, 'principale', '1950-08-12', 'inattiva', '1953-02-28')
    ON CONFLICT (comune_id, numero_partita) DO UPDATE SET stato = 'inattiva', data_chiusura = '1953-02-28'
    RETURNING id INTO v_par_cai_203_id;
    
    -- Partite di Altare
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (v_altare_id, 301, 'principale', '1952-04-20', 'attiva')
    ON CONFLICT (comune_id, numero_partita) DO NOTHING
    RETURNING id INTO v_par_alt_301_id;
    
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (v_altare_id, 302, 'principale', '1952-05-18', 'attiva')
    ON CONFLICT (comune_id, numero_partita) DO NOTHING
    RETURNING id INTO v_par_alt_302_id;
    
    -- Partite di Millesimo
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (v_millesimo_id, 401, 'principale', '1949-11-08', 'attiva')
    ON CONFLICT (comune_id, numero_partita) DO NOTHING
    RETURNING id INTO v_par_mil_401_id;
    
    -- Partite di Cosseria
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato)
    VALUES (v_cosseria_id, 501, 'principale', '1953-03-15', 'attiva')
    ON CONFLICT (comune_id, numero_partita) DO NOTHING
    RETURNING id INTO v_par_cos_501_id;

    -- Recupera gli ID se esistevano già
    SELECT id INTO v_par_car_101_id FROM partita WHERE comune_id = v_carcare_id AND numero_partita = 101;
    SELECT id INTO v_par_car_102_id FROM partita WHERE comune_id = v_carcare_id AND numero_partita = 102;
    SELECT id INTO v_par_car_103_id FROM partita WHERE comune_id = v_carcare_id AND numero_partita = 103;
    SELECT id INTO v_par_car_104_id FROM partita WHERE comune_id = v_carcare_id AND numero_partita = 104;
    SELECT id INTO v_par_cai_201_id FROM partita WHERE comune_id = v_cairo_id AND numero_partita = 201;
    SELECT id INTO v_par_cai_202_id FROM partita WHERE comune_id = v_cairo_id AND numero_partita = 202;
    SELECT id INTO v_par_cai_203_id FROM partita WHERE comune_id = v_cairo_id AND numero_partita = 203;
    SELECT id INTO v_par_alt_301_id FROM partita WHERE comune_id = v_altare_id AND numero_partita = 301;
    SELECT id INTO v_par_alt_302_id FROM partita WHERE comune_id = v_altare_id AND numero_partita = 302;
    SELECT id INTO v_par_mil_401_id FROM partita WHERE comune_id = v_millesimo_id AND numero_partita = 401;
    SELECT id INTO v_par_cos_501_id FROM partita WHERE comune_id = v_cosseria_id AND numero_partita = 501;

    RAISE NOTICE 'Inserite 11 partite nei vari comuni';

    -- === 6. Inserimento Relazioni Partita-Possessore ===
    RAISE NOTICE 'Inserimento Associazioni Partita-Possessore...';
    
    -- Associazioni per partite di Carcare
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_car_101_id, v_rossi_g_id, 'principale', 'proprietà esclusiva', NULL)
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_car_102_id, v_bianchi_a_id, 'principale', 'proprietà esclusiva', NULL)
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_car_103_id, v_rossi_g_id, 'secondaria', 'comproprietà', '1/2')
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_car_103_id, v_bianchi_a_id, 'secondaria', 'comproprietà', '1/2')
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_car_104_id, v_rossi_g_id, 'principale', 'proprietà esclusiva', NULL)
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    -- Associazioni per partite di Cairo Montenotte
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_cai_201_id, v_ferraro_c_id, 'principale', 'proprietà esclusiva', NULL)
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_cai_202_id, v_olivieri_m_id, 'principale', 'comproprietà', '2/3')
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_cai_202_id, v_gallo_p_id, 'principale', 'comproprietà', '1/3')
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_cai_203_id, v_gallo_p_id, 'principale', 'proprietà esclusiva', NULL)
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    -- Associazioni per partite di Altare
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_alt_301_id, v_bruno_f_id, 'principale', 'proprietà esclusiva', NULL)
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_alt_302_id, v_martini_e_id, 'principale', 'proprietà esclusiva', NULL)
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    -- Associazioni per partite di Millesimo
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_mil_401_id, v_ricci_l_id, 'principale', 'proprietà esclusiva', NULL)
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    -- Associazioni per partite di Cosseria
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_cos_501_id, v_esposito_s_id, 'principale', 'comproprietà', '1/2')
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;
    
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
    VALUES (v_par_cos_501_id, v_romano_d_id, 'principale', 'comproprietà', '1/2')
    ON CONFLICT (partita_id, possessore_id) DO NOTHING;

    RAISE NOTICE 'Inserite associazioni tra partite e possessori';

    -- === 7. Inserimento Relazioni tra Partite ===
    RAISE NOTICE 'Inserimento Relazioni Partita...';
    
    INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id)
    VALUES (v_par_car_102_id, v_par_car_103_id)
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Inserite relazioni tra partite';

    -- === 8. Inserimento Immobili ===
    RAISE NOTICE 'Inserimento Immobili...';
    
    -- Immobili per partite di Carcare
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_car_101_id, v_loc_car_roma_id, 'Palazzo storico', 3, 12, '450 mq', 'Abitazione signorile')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_car_102_id, v_loc_car_cavour_id, 'Casa', 2, 6, '180 mq', 'Abitazione civile')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_car_102_id, v_loc_car_cavour_id, 'Giardino', NULL, NULL, '80 mq', 'Area scoperta')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_car_103_id, v_loc_car_garibaldi_id, 'Opificio', 1, NULL, '250 mq', 'Artigianale')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_car_104_id, v_loc_car_mazzini_id, 'Negozio', 1, 2, '75 mq', 'Commerciale')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_car_104_id, v_loc_car_dante_id, 'Magazzino', 1, NULL, '120 mq', 'Deposito')
    ON CONFLICT DO NOTHING;
    
    -- Immobili per partite di Cairo Montenotte
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_cai_201_id, v_loc_cai_italia_id, 'Villetta', 2, 8, '220 mq', 'Abitazione signorile')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_cai_201_id, v_loc_cai_italia_id, 'Giardino', NULL, NULL, '300 mq', 'Area scoperta')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_cai_202_id, v_loc_cai_colombo_id, 'Fabbricato commerciale', 2, 4, '380 mq', 'Commerciale')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_cai_203_id, v_loc_cai_marconi_id, 'Casa colonica', 2, 5, '160 mq', 'Abitazione rurale')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_cai_203_id, v_loc_cai_matteotti_id, 'Terreno agricolo', NULL, NULL, '5000 mq', 'Terreno')
    ON CONFLICT DO NOTHING;
    
    -- Immobili per partite di Altare
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_alt_301_id, v_loc_alt_vittorio_id, 'Laboratorio artigianale', 1, NULL, '180 mq', 'Artigianale')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_alt_302_id, v_loc_alt_trento_id, 'Appartamento', 1, 4, '95 mq', 'Abitazione civile')
    ON CONFLICT DO NOTHING;
    
    -- Immobili per partite di Millesimo
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_mil_401_id, v_loc_mil_fontane_id, 'Mulino ad acqua', 2, NULL, '210 mq', 'Opificio storico')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_mil_401_id, v_loc_mil_castello_id, 'Casetta', 1, 3, '70 mq', 'Abitazione rurale')
    ON CONFLICT DO NOTHING;
    
    -- Immobili per partite di Cosseria
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_cos_501_id, v_loc_cos_provinciale_id, 'Caseggiato rurale', 2, 6, '210 mq', 'Abitazione rurale')
    ON CONFLICT DO NOTHING;
    
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
    VALUES (v_par_cos_501_id, v_loc_cos_piave_id, 'Fienile', 1, NULL, '90 mq', 'Deposito agricolo')
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Inseriti 16 immobili nei vari comuni';

    -- === 9. Inserimento Variazioni e Contratti ===
    RAISE NOTICE 'Inserimento Variazioni e Contratti...';
    
    -- Variazione per Partita 203 di Cairo (successione)
    SELECT id INTO v_var_succ_car_id 
    FROM variazione 
    WHERE partita_origine_id = v_par_cai_203_id AND tipo = 'Successione';
    
    IF v_var_succ_car_id IS NULL THEN
        INSERT INTO variazione (
            partita_origine_id, partita_destinazione_id, tipo, data_variazione, 
            numero_riferimento, nominativo_riferimento
        )
        VALUES (
            v_par_cai_203_id, NULL, 'Successione', '1953-02-28', 
            '15/53', 'Gallo Paolo'
        )
        RETURNING id INTO v_var_succ_car_id;
        
        INSERT INTO contratto (
            variazione_id, tipo, data_contratto, notaio, repertorio, note
        )
        VALUES (
            v_var_succ_car_id, 'Successione', '1953-02-20', 
            'Notaio Bianchi Alberto', '2548/53', 
            'Successione per causa di morte del proprietario'
        );
    END IF;
    
    -- Variazione per Partita 201 di Cairo (vendita a Partita 202)
    SELECT id INTO v_var_vend_cai_id 
    FROM variazione 
    WHERE partita_origine_id = v_par_cai_201_id AND partita_destinazione_id = v_par_cai_202_id;
    
    IF v_var_vend_cai_id IS NULL THEN
        INSERT INTO variazione (
            partita_origine_id, partita_destinazione_id, tipo, data_variazione, 
            numero_riferimento, nominativo_riferimento
        )
        VALUES (
            v_par_cai_201_id, v_par_cai_202_id, 'Vendita', '1953-05-15', 
            'Atto 145/53', 'Ferraro Carlo'
        )
        RETURNING id INTO v_var_vend_cai_id;
        
        INSERT INTO contratto (
            variazione_id, tipo, data_contratto, notaio, repertorio, note
        )
        VALUES (
            v_var_vend_cai_id, 'Vendita', '1953-05-10', 
            'Notaio Rossi Francesco', '3127/53', 
            'Vendita parziale del giardino di pertinenza'
        );
    END IF;
    
    -- Variazione per Partita 301 di Altare (frazionamento)
    SELECT id INTO v_var_fraz_alt_id 
    FROM variazione 
    WHERE partita_origine_id = v_par_alt_301_id AND tipo = 'Frazionamento';
    
    IF v_var_fraz_alt_id IS NULL THEN
        INSERT INTO variazione (
            partita_origine_id, partita_destinazione_id, tipo, data_variazione, 
            numero_riferimento, nominativo_riferimento
        )
        VALUES (
            v_par_alt_301_id, v_par_alt_302_id, 'Frazionamento', '1954-03-25', 
            'Atto 78/54', 'Bruno Francesco'
        )
        RETURNING id INTO v_var_fraz_alt_id;
        
        INSERT INTO contratto (
            variazione_id, tipo, data_contratto, notaio, repertorio, note
        )
        VALUES (
            v_var_fraz_alt_id, 'Divisione', '1954-03-18', 
            'Notaio Verdi Giuseppe', '982/54', 
            'Divisione di laboratorio in due unità distinte'
        );
    END IF;
    
    -- Variazione per Partita 101 di Carcare (vendita a nuova partita)
    -- Crea una nuova partita per Rossi
    DECLARE v_par_car_150_id INTEGER;
    BEGIN
        INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato, numero_provenienza)
        VALUES (v_carcare_id, 150, 'principale', '1953-07-10', 'attiva', 101)
        ON CONFLICT (comune_id, numero_partita) DO NOTHING
        RETURNING id INTO v_par_car_150_id;
        
        IF v_par_car_150_id IS NULL THEN
            SELECT id INTO v_par_car_150_id FROM partita 
            WHERE comune_id = v_carcare_id AND numero_partita = 150;
        END IF;
        
        -- Associa Rossi alla nuova partita
        INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
        VALUES (v_par_car_150_id, v_rossi_g_id, 'principale', 'proprietà esclusiva', NULL)
        ON CONFLICT (partita_id, possessore_id) DO NOTHING;
        
        -- Crea variazione
        SELECT id INTO v_var_vend_car_nuova_id 
        FROM variazione 
        WHERE partita_origine_id = v_par_car_101_id AND partita_destinazione_id = v_par_car_150_id;
        
        IF v_var_vend_car_nuova_id IS NULL THEN
            INSERT INTO variazione (
                partita_origine_id, partita_destinazione_id, tipo, data_variazione, 
                numero_riferimento, nominativo_riferimento
            )
            VALUES (
                v_par_car_101_id, v_par_car_150_id, 'Vendita', '1953-07-10', 
                'Atto 267/53', 'Rossi Giovanni'
            )
            RETURNING id INTO v_var_vend_car_nuova_id;
            
            INSERT INTO contratto (
                variazione_id, tipo, data_contratto, notaio, repertorio, note
            )
            VALUES (
                v_var_vend_car_nuova_id, 'Vendita', '1953-07-05', 
                'Notaio Bianchi Alberto', '2675/53', 
                'Vendita di una porzione del palazzo'
            );
        END IF;
    END;

    RAISE NOTICE 'Inserite variazioni con contratti associati';

    -- === 10. Inserimento Consultazioni ===
    RAISE NOTICE 'Inserimento Consultazioni...';
    
    INSERT INTO consultazione (
        data, richiedente, documento_identita, motivazione, 
        materiale_consultato, funzionario_autorizzante
    )
    VALUES (
        '2025-03-10', 'Dott. Martini Luca', 'CI AY5632147', 
        'Ricerca storica edifici del centro storico', 
        'Registro partite Carcare 1951-1952', 'Dott.ssa Ferrero Carla'
    )
    ON CONFLICT DO NOTHING;
    
    INSERT INTO consultazione (
        data, richiedente, documento_identita, motivazione, 
        materiale_consultato, funzionario_autorizzante
    )
    VALUES (
        '2025-03-25', 'Studio Notarile Rossi', 'Tessera Ordine 23562', 
        'Verifica proprietà immobili', 
        'Partite 101, 102, 103 Carcare', 'Dott. Bianchi Marco'
    )
    ON CONFLICT DO NOTHING;
    
    INSERT INTO consultazione (
        data, richiedente, documento_identita, motivazione, 
        materiale_consultato, funzionario_autorizzante
    )
    VALUES (
        '2025-04-08', 'Geom. Esposito Roberto', 'CI BX7341852', 
        'Pratiche edilizie immobili storici', 
        'Registri Cairo Montenotte e Altare', 'Dott.ssa Ferrero Carla'
    )
    ON CONFLICT DO NOTHING;
    
    INSERT INTO consultazione (
        data, richiedente, documento_identita, motivazione, 
        materiale_consultato, funzionario_autorizzante
    )
    VALUES (
        '2025-04-15', 'Prof.ssa Gallo Stefania', 'CI AZ3825974', 
        'Ricerca universitaria architettura storica della valle', 
        'Registri completi dei 5 comuni', 'Dott. Verdi Paolo'
    )
    ON CONFLICT DO NOTHING;
    
    INSERT INTO consultazione (
        data, richiedente, documento_identita, motivazione, 
        materiale_consultato, funzionario_autorizzante
    )
    VALUES (
        '2025-05-05', 'Arch. Romano Teresa', 'CI BZ2541832', 
        'Progetto restauro palazzo storico', 
        'Partita 101 Carcare e variazioni', 'Dott. Bianchi Marco'
    )
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Inserite consultazioni';

    -- === 11. Inserimento Periodi Storici di Riferimento ===
    RAISE NOTICE 'Inserimento Periodi Storici...';
    
    INSERT INTO periodo_storico (nome, anno_inizio, anno_fine, descrizione)
    VALUES (
        'Regno di Sardegna', 1720, 1861, 
        'Periodo del Regno di Sardegna prima dell''unità d''Italia'
    )
    ON CONFLICT DO NOTHING;
    
    INSERT INTO periodo_storico (nome, anno_inizio, anno_fine, descrizione)
    VALUES (
        'Regno d''Italia', 1861, 1946, 
        'Periodo del Regno d''Italia'
    )
    ON CONFLICT DO NOTHING;
    
    INSERT INTO periodo_storico (nome, anno_inizio, anno_fine, descrizione)
    VALUES (
        'Repubblica Italiana', 1946, NULL, 
        'Periodo della Repubblica Italiana'
    )
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Inseriti periodi storici';

    -- === 12. Inserimento Utenti di Test ===
    RAISE NOTICE 'Inserimento Utenti di Test...';
    
    -- Password hash (bcrypt) per la password 'password'
    DECLARE v_password_hash VARCHAR := '$2a$12$S0BO7pqRyV4YuMxP1E/w6uLT72vBz9pP/Z6YdX3Jn9MMLxJ3W4gh.';
    
    INSERT INTO utenti (username, password_hash, nome_completo, email, role_id, is_active)
    VALUES (
        'admin', v_password_hash, 'Amministratore Sistema', 
        'admin@esempio.it', 
        (SELECT id FROM ruoli_utente WHERE nome_ruolo = 'admin'),
        TRUE
    )
    ON CONFLICT (username) DO NOTHING;
    
    INSERT INTO utenti (username, password_hash, nome_completo, email, role_id, is_active)
    VALUES (
        'archivista', v_password_hash, 'Mario Archivisti', 
        'archivista@esempio.it', 
        (SELECT id FROM ruoli_utente WHERE nome_ruolo = 'archivista'),
        TRUE
    )
    ON CONFLICT (username) DO NOTHING;
    
    INSERT INTO utenti (username, password_hash, nome_completo, email, role_id, is_active)
    VALUES (
        'consultatore', v_password_hash, 'Carlo Consultatori', 
        'consultatore@esempio.it', 
        (SELECT id FROM ruoli_utente WHERE nome_ruolo = 'consultatore'),
        TRUE
    )
    ON CONFLICT (username) DO NOTHING;

    RAISE NOTICE 'Inseriti utenti di test per accesso al sistema';

    -- === 13. Inserimento Nomi Storici ===
    RAISE NOTICE 'Inserimento Nomi Storici...';
    
    INSERT INTO nome_storico (
        entita_tipo, entita_id, nome, periodo_id, anno_inizio, anno_fine, note
    )
    VALUES (
        'comune', 
        (SELECT id FROM comune WHERE nome = 'Cairo Montenotte'), 
        'Cairo', 
        (SELECT id FROM periodo_storico WHERE nome = 'Regno di Sardegna'), 
        1720, 1861, 
        'Nome storico precedente all''unificazione'
    )
    ON CONFLICT DO NOTHING;
    
    INSERT INTO nome_storico (
        entita_tipo, entita_id, nome, periodo_id, anno_inizio, anno_fine, note
    )
    VALUES (
        'localita', 
        v_loc_car_mazzini_id, 
        'Via Comunale', 
        (SELECT id FROM periodo_storico WHERE nome = 'Regno di Sardegna'), 
        1800, 1861, 
        'Denominazione precedente'
    )
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Inseriti nomi storici';

    -- === 14. Inserimento Documenti Storici ===
    RAISE NOTICE 'Inserimento Documenti Storici...';
    
    DECLARE v_doc_id_1 INTEGER;
    DECLARE v_doc_id_2 INTEGER;
    BEGIN
        INSERT INTO documento_storico (
            titolo, descrizione, anno, periodo_id, tipo_documento, 
            percorso_file, metadati
        )
        VALUES (
            'Mappa Catastale Carcare 1875', 
            'Mappa originale del catasto storico di Carcare redatta nel 1875', 
            1875, 
            (SELECT id FROM periodo_storico WHERE nome = 'Regno d''Italia'), 
            'Mappa', 
            '/archivio/mappe/carcare_1875.jpg', 
            '{"dimensioni": "60x80 cm", "scala": "1:1000", "stato_conservazione": "buono"}'::jsonb
        )
        ON CONFLICT DO NOTHING
        RETURNING id INTO v_doc_id_1;
        
        INSERT INTO documento_storico (
            titolo, descrizione, anno, periodo_id, tipo_documento, 
            percorso_file, metadati
        )
        VALUES (
            'Registro di Stima Altare 1888', 
            'Registro delle stime catastali di Altare dell''anno 1888', 
            1888, 
            (SELECT id FROM periodo_storico WHERE nome = 'Regno d''Italia'), 
            'Registro', 
            '/archivio/registri/altare_1888.pdf', 
            '{"pagine": 120, "formato": "32x22 cm", "stato_conservazione": "discreto"}'::jsonb
        )
        ON CONFLICT DO NOTHING
        RETURNING id INTO v_doc_id_2;
        
        -- Collegamenti tra documenti e partite
        IF v_doc_id_1 IS NOT NULL AND v_par_car_101_id IS NOT NULL THEN
            INSERT INTO documento_partita (documento_id, partita_id, rilevanza, note)
            VALUES (
                v_doc_id_1, v_par_car_101_id, 'primaria', 
                'Il palazzo è chiaramente identificabile nella mappa'
            )
            ON CONFLICT DO NOTHING;
        END IF;
        
        IF v_doc_id_2 IS NOT NULL AND v_par_alt_301_id IS NOT NULL THEN
            INSERT INTO documento_partita (documento_id, partita_id, rilevanza, note)
            VALUES (
                v_doc_id_2, v_par_alt_301_id, 'secondaria', 
                'Il laboratorio è menzionato nelle stime'
            )
            ON CONFLICT DO NOTHING;
        END IF;
    END;

    RAISE NOTICE 'Inseriti documenti storici con collegamenti alle partite';

    RAISE NOTICE '[DATI TEST] Caricamento dati di test realistici completato con successo!';
    
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING '[DATI TEST] Errore durante il popolamento: % - SQLSTATE: %', SQLERRM, SQLSTATE;
END;
$;

-- Chiamata alla procedura per generare i dati
DO $ BEGIN 
    RAISE NOTICE 'Esecuzione procedura carica_dati_test_realistici...'; 
END $;

CALL carica_dati_test_realistici();

DO $ BEGIN 
    RAISE NOTICE 'Procedura carica_dati_test_realistici completata.'; 
END $;

-- Eventuale chiamata per aggiornare statistiche
CALL aggiorna_tutte_statistiche();

-- Istruzioni finali
RAISE NOTICE 'Tutti i dati di test realistici sono stati caricati con successo!';
RAISE NOTICE 'Ora è possibile testare le funzionalità del sistema con dati più verosimili.';
