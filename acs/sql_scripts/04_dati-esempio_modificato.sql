-- Imposta lo schema
SET search_path TO catasto, public;

/*
 * Script per l'inserimento di dati di esempio nel database del catasto storico
 * VERSIONE CORRETTA per compatibilità con comune.id PK
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
    RAISE NOTICE '[DATI ESEMPIO] Inizio caricamento...';

    -- === 1. Inserimento Comuni ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Comuni...';
    -- Usa ON CONFLICT per rendere rieseguibile senza errori se i comuni esistono già
    INSERT INTO comune (nome, provincia, regione) VALUES ('Carcare', 'Savona', 'Liguria') ON CONFLICT (nome) DO UPDATE SET provincia = EXCLUDED.provincia RETURNING id INTO v_carcare_id;
    INSERT INTO comune (nome, provincia, regione) VALUES ('Cairo Montenotte', 'Savona', 'Liguria') ON CONFLICT (nome) DO UPDATE SET provincia = EXCLUDED.provincia RETURNING id INTO v_cairo_id;
    INSERT INTO comune (nome, provincia, regione) VALUES ('Altare', 'Savona', 'Liguria') ON CONFLICT (nome) DO UPDATE SET provincia = EXCLUDED.provincia RETURNING id INTO v_altare_id;
    -- Recupera gli ID anche se esistevano già
    SELECT id INTO v_carcare_id FROM comune WHERE nome='Carcare';
    SELECT id INTO v_cairo_id FROM comune WHERE nome='Cairo Montenotte';
    SELECT id INTO v_altare_id FROM comune WHERE nome='Altare';
    RAISE NOTICE '[DATI ESEMPIO]   -> Carcare ID: %, Cairo ID: %, Altare ID: %', v_carcare_id, v_cairo_id, v_altare_id;

    -- === 2. Inserimento Registri (Opzionale, se li usi) ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Registri Partite/Matricole...';
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_carcare_id, 1950, 3, 'Buono') ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_cairo_id, 1948, 5, 'Discreto') ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    INSERT INTO registro_partite (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_altare_id, 1952, 2, 'Ottimo') ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_carcare_id, 1950, 2, 'Buono') ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_cairo_id, 1948, 4, 'Discreto') ON CONFLICT (comune_id, anno_impianto) DO NOTHING;
    INSERT INTO registro_matricole (comune_id, anno_impianto, numero_volumi, stato_conservazione) VALUES (v_altare_id, 1952, 1, 'Ottimo') ON CONFLICT (comune_id, anno_impianto) DO NOTHING;

    -- === 3. Inserimento Possessori ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Possessori...';
    -- Usiamo ON CONFLICT per robustezza, assumendo UNIQUE(comune_id, nome_completo) se aggiunto, altrimenti si basa su SELECT
    SELECT id INTO v_fossati_a_id FROM possessore WHERE comune_id=v_carcare_id AND nome_completo='Fossati Angelo fu Roberto';
    IF v_fossati_a_id IS NULL THEN INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Fossati Angelo', 'fu Roberto', 'Fossati Angelo fu Roberto', true) RETURNING id INTO v_fossati_a_id; END IF;

    SELECT id INTO v_caviglia_m_id FROM possessore WHERE comune_id=v_carcare_id AND nome_completo='Caviglia Maria fu Giuseppe';
    IF v_caviglia_m_id IS NULL THEN INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Caviglia Maria', 'fu Giuseppe', 'Caviglia Maria fu Giuseppe', true) RETURNING id INTO v_caviglia_m_id; END IF;

    SELECT id INTO v_barberis_g_id FROM possessore WHERE comune_id=v_carcare_id AND nome_completo='Barberis Giovanni fu Paolo';
    IF v_barberis_g_id IS NULL THEN INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Barberis Giovanni', 'fu Paolo', 'Barberis Giovanni fu Paolo', true) RETURNING id INTO v_barberis_g_id; END IF;

    SELECT id INTO v_berruti_a_id FROM possessore WHERE comune_id=v_cairo_id AND nome_completo='Berruti Antonio fu Luigi';
    IF v_berruti_a_id IS NULL THEN INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_cairo_id, 'Berruti Antonio', 'fu Luigi', 'Berruti Antonio fu Luigi', true) RETURNING id INTO v_berruti_a_id; END IF;

    SELECT id INTO v_ferraro_c_id FROM possessore WHERE comune_id=v_cairo_id AND nome_completo='Ferraro Caterina fu Marco';
    IF v_ferraro_c_id IS NULL THEN INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_cairo_id, 'Ferraro Caterina', 'fu Marco', 'Ferraro Caterina fu Marco', true) RETURNING id INTO v_ferraro_c_id; END IF;

    SELECT id INTO v_bormioli_p_id FROM possessore WHERE comune_id=v_altare_id AND nome_completo='Bormioli Pietro fu Carlo';
    IF v_bormioli_p_id IS NULL THEN INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_altare_id, 'Bormioli Pietro', 'fu Carlo', 'Bormioli Pietro fu Carlo', true) RETURNING id INTO v_bormioli_p_id; END IF;

    SELECT id INTO v_rossi_m_id FROM possessore WHERE comune_id=v_carcare_id AND nome_completo='Rossi Marco fu Antonio';
    IF v_rossi_m_id IS NULL THEN INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo) VALUES (v_carcare_id, 'Rossi Marco', 'fu Antonio', 'Rossi Marco fu Antonio', true) RETURNING id INTO v_rossi_m_id; END IF;
    RAISE NOTICE '[DATI ESEMPIO]   -> Inseriti/Trovati 7 possessori.';

    -- === 4. Inserimento Località ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Località...';
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_carcare_id, 'Regione Vista', 'regione', NULL) ON CONFLICT(comune_id, nome, civico) DO NOTHING RETURNING id INTO v_loc_car_vista_id;
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_carcare_id, 'Via Giuseppe Verdi', 'via', 12) ON CONFLICT(comune_id, nome, civico) DO NOTHING RETURNING id INTO v_loc_car_verdi_id;
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_carcare_id, 'Via Roma', 'via', 5) ON CONFLICT(comune_id, nome, civico) DO NOTHING RETURNING id INTO v_loc_car_roma_id;
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_cairo_id, 'Borgata Ferrere', 'borgata', NULL) ON CONFLICT(comune_id, nome, civico) DO NOTHING RETURNING id INTO v_loc_cai_ferrere_id;
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_cairo_id, 'Strada Provinciale', 'via', 76) ON CONFLICT(comune_id, nome, civico) DO NOTHING RETURNING id INTO v_loc_cai_prov_id;
    INSERT INTO localita (comune_id, nome, tipo, civico) VALUES (v_altare_id, 'Via Palermo', 'via', 22) ON CONFLICT(comune_id, nome, civico) DO NOTHING RETURNING id INTO v_loc_alt_palermo_id;
    -- Recupera ID se esistevano già
    SELECT id INTO v_loc_car_vista_id FROM localita WHERE comune_id=v_carcare_id AND nome='Regione Vista' AND civico IS NULL;
    SELECT id INTO v_loc_car_verdi_id FROM localita WHERE comune_id=v_carcare_id AND nome='Via Giuseppe Verdi' AND civico=12;
    SELECT id INTO v_loc_car_roma_id FROM localita WHERE comune_id=v_carcare_id AND nome='Via Roma' AND civico=5;
    SELECT id INTO v_loc_cai_ferrere_id FROM localita WHERE comune_id=v_cairo_id AND nome='Borgata Ferrere' AND civico IS NULL;
    SELECT id INTO v_loc_cai_prov_id FROM localita WHERE comune_id=v_cairo_id AND nome='Strada Provinciale' AND civico=76;
    SELECT id INTO v_loc_alt_palermo_id FROM localita WHERE comune_id=v_altare_id AND nome='Via Palermo' AND civico=22;
    RAISE NOTICE '[DATI ESEMPIO]   -> Inserite/Trovate 6 località.';

    -- === 5. Inserimento Partite ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Partite...';
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_carcare_id, 221, 'principale', '1950-05-10', 'attiva') ON CONFLICT(comune_id, numero_partita) DO NOTHING RETURNING id INTO v_par_car_221_id;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_carcare_id, 219, 'principale', '1950-05-10', 'attiva') ON CONFLICT(comune_id, numero_partita) DO NOTHING RETURNING id INTO v_par_car_219_id;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_carcare_id, 245, 'secondaria', '1951-03-22', 'attiva') ON CONFLICT(comune_id, numero_partita) DO NOTHING RETURNING id INTO v_par_car_245_id;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_cairo_id, 112, 'principale', '1948-11-05', 'attiva') ON CONFLICT(comune_id, numero_partita) DO NOTHING RETURNING id INTO v_par_cai_112_id;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato, data_chiusura) VALUES (v_cairo_id, 118, 'principale', '1949-01-15', 'inattiva', '1952-08-15') ON CONFLICT(comune_id, numero_partita) DO UPDATE SET stato=EXCLUDED.stato, data_chiusura=EXCLUDED.data_chiusura RETURNING id INTO v_par_cai_118_id;
    INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato) VALUES (v_altare_id, 87, 'principale', '1952-07-03', 'attiva') ON CONFLICT(comune_id, numero_partita) DO NOTHING RETURNING id INTO v_par_alt_87_id;
    -- Recupera ID se esistevano già
    SELECT id INTO v_par_car_221_id FROM partita WHERE comune_id=v_carcare_id AND numero_partita=221;
    SELECT id INTO v_par_car_219_id FROM partita WHERE comune_id=v_carcare_id AND numero_partita=219;
    SELECT id INTO v_par_car_245_id FROM partita WHERE comune_id=v_carcare_id AND numero_partita=245;
    SELECT id INTO v_par_cai_112_id FROM partita WHERE comune_id=v_cairo_id AND numero_partita=112;
    SELECT id INTO v_par_cai_118_id FROM partita WHERE comune_id=v_cairo_id AND numero_partita=118;
    SELECT id INTO v_par_alt_87_id FROM partita WHERE comune_id=v_altare_id AND numero_partita=87;
    RAISE NOTICE '[DATI ESEMPIO]   -> Inserite/Trovate 6 partite esistenti.';

    -- === 6. Associazione Partite-Possessori ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Associazioni Partita-Possessore...';
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_car_221_id, v_fossati_a_id, 'principale', 'proprietà esclusiva', NULL) ON CONFLICT DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_car_219_id, v_caviglia_m_id, 'principale', 'proprietà esclusiva', NULL) ON CONFLICT DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_car_245_id, v_barberis_g_id, 'secondaria', 'comproprietà', '1/2') ON CONFLICT DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_car_245_id, v_caviglia_m_id, 'secondaria', 'comproprietà', '1/2') ON CONFLICT DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_cai_112_id, v_berruti_a_id, 'principale', 'proprietà esclusiva', NULL) ON CONFLICT DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_cai_118_id, v_ferraro_c_id, 'principale', 'proprietà esclusiva', NULL) ON CONFLICT DO NOTHING;
    INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota) VALUES (v_par_alt_87_id, v_bormioli_p_id, 'principale', 'proprietà esclusiva', NULL) ON CONFLICT DO NOTHING;

    -- === 7. Relazioni tra partite ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Relazioni Partita...';
    INSERT INTO partita_relazione (partita_principale_id, partita_secondaria_id) VALUES (v_par_car_219_id, v_par_car_245_id) ON CONFLICT DO NOTHING;

    -- === 8. Inserimento Immobili ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Immobili...';
    -- Usiamo ON CONFLICT per robustezza, assumendo UNIQUE(partita_id, localita_id, natura) - SE AGGIUNTO! Altrimenti rimuovere ON CONFLICT.
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES (v_par_car_221_id, v_loc_car_vista_id, 'Molino da cereali', 2, NULL, '150 mq', 'Artigianale') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES (v_par_car_219_id, v_loc_car_verdi_id, 'Casa', 3, 8, '210 mq', 'Abitazione civile') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES (v_par_car_219_id, v_loc_car_verdi_id, 'Giardino', NULL, NULL, '50 mq', 'Area scoperta') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES (v_par_car_245_id, v_loc_car_roma_id, 'Magazzino', 1, NULL, '80 mq', 'Deposito') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES (v_par_cai_112_id, v_loc_cai_ferrere_id, 'Fabbricato rurale', 2, 5, '180 mq', 'Abitazione rurale') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES (v_par_cai_118_id, v_loc_cai_prov_id, 'Casa', 2, 6, '160 mq', 'Abitazione civile') ON CONFLICT DO NOTHING;
    INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione) VALUES (v_par_alt_87_id, v_loc_alt_palermo_id, 'Laboratorio', 1, NULL, '120 mq', 'Artigianale') ON CONFLICT DO NOTHING;
    RAISE NOTICE '[DATI ESEMPIO]   -> Inseriti/Saltati 7 immobili.';

    -- === 9. Inserimento Variazioni e Contratti ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Variazioni e Contratti...';
    -- 9.1 Successione Cairo 118 (già inattiva)
    -- Verifica se variazione esiste già prima di inserirla
    SELECT id INTO v_var_cai_succ_id FROM variazione WHERE partita_origine_id = v_par_cai_118_id AND tipo = 'Successione';
    IF v_var_cai_succ_id IS NULL THEN
        INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento) VALUES
        (v_par_cai_118_id, NULL, 'Successione', '1952-08-15', '22/52', 'Ferraro Caterina') RETURNING id INTO v_var_cai_succ_id;
        INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note) VALUES
        (v_var_cai_succ_id, 'Successione', '1952-08-10', 'Notaio Bianchi', '1234/52', 'Successione per morte del proprietario Luigi Ferraro');
    END IF;

    -- 9.2 Vendita parziale da Fossati a Rossi (Nuova partita)
    --     Crea nuova partita per Rossi (se non esiste)
    SELECT id INTO v_par_car_305_id FROM partita WHERE comune_id = v_carcare_id AND numero_partita = 305;
    IF v_par_car_305_id IS NULL THEN
        INSERT INTO partita (comune_id, numero_partita, tipo, data_impianto, stato, numero_provenienza) VALUES
        (v_carcare_id, 305, 'principale', '1953-02-20', 'attiva', 221) RETURNING id INTO v_par_car_305_id;
        -- Associa Rossi
        INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo) VALUES
        (v_par_car_305_id, v_rossi_m_id, 'principale', 'proprietà esclusiva') ON CONFLICT DO NOTHING;
         -- Trasferisci immobile (Molino ID 1)
        UPDATE immobile SET partita_id = v_par_car_305_id WHERE id = 1 AND partita_id = v_par_car_221_id;
    END IF;

    -- Registra variazione (se non esiste)
    SELECT id INTO v_var_car_vend_id FROM variazione WHERE partita_origine_id = v_par_car_221_id AND partita_destinazione_id = v_par_car_305_id;
    IF v_var_car_vend_id IS NULL THEN
        INSERT INTO variazione (partita_origine_id, partita_destinazione_id, tipo, data_variazione, numero_riferimento, nominativo_riferimento) VALUES
        (v_par_car_221_id, v_par_car_305_id, 'Vendita', '1953-02-20', 'Atto Not. Verdi', 'Rossi Marco') RETURNING id INTO v_var_car_vend_id;
        INSERT INTO contratto (variazione_id, tipo, data_contratto, notaio, repertorio, note) VALUES
        (v_var_car_vend_id, 'Vendita', '1953-02-15', 'Notaio Verdi', '567/53', 'Vendita parziale di immobile da partita 221');
    END IF;

    -- === 10. Inserimento Consultazioni ===
    RAISE NOTICE '[DATI ESEMPIO] Inserimento Consultazioni...';
    INSERT INTO consultazione (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante) VALUES
    ('2025-04-01', 'Mario Bianchi', 'CI AB1234567', 'Ricerca storica', 'Registro partite Carcare 1950', 'Dott. Verdi') ON CONFLICT DO NOTHING;
    INSERT INTO consultazione (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante) VALUES
    ('2025-04-05', 'Studio Legale Rossi', 'Tessera Ordine 55213', 'Verifica proprietà', 'Partite 221 e 305 Carcare', 'Dott. Verdi') ON CONFLICT DO NOTHING;

    RAISE NOTICE '[DATI ESEMPIO] Caricamento dati di esempio completato.';

END;
$$;

-- Esempio di chiamata per caricare i dati
-- Questa chiamata può essere eseguita una sola volta dopo aver creato le tabelle e la procedura.
DO $$
BEGIN
    -- Verifica se ci sono già dati significativi prima di caricare
    -- (Questo DO block esegue la procedura definita sopra)
    IF NOT EXISTS (SELECT 1 FROM partita LIMIT 1) THEN
       RAISE NOTICE 'Database vuoto, caricamento dati di esempio...';
       CALL carica_dati_esempio_completo();
    ELSE
       RAISE NOTICE 'Database contiene già dati, salto caricamento dati di esempio predefiniti.';
       -- Potresti voler comunque chiamare CALL carica_dati_esempio_completo();
       -- se la procedura usa ON CONFLICT ed è sicura da rieseguire.
       -- CALL carica_dati_esempio_completo(); -- Decommenta se vuoi rieseguire
    END IF;
END $$;