-- Imposta lo schema
SET search_path TO catasto, public;

-- Test basati sui dati inseriti da carica_dati_esempio_completo()

-- 1. Test inserimento nuovo possessore (che fallirà per duplicato se dati già caricati)
DO $$
DECLARE
    v_possessore_id INTEGER;
    v_comune_id INTEGER;
    v_cognome VARCHAR := 'Rossi Marco';
    v_paternita VARCHAR := 'fu Antonio';
    v_nome_completo VARCHAR := 'Rossi Marco fu Antonio';
BEGIN
    SELECT id INTO v_comune_id FROM comune WHERE nome = 'Carcare';
    IF NOT FOUND THEN RAISE EXCEPTION 'Comune Carcare non trovato'; END IF;

    SELECT id INTO v_possessore_id FROM possessore
    WHERE comune_id = v_comune_id AND nome_completo = v_nome_completo;

    IF v_possessore_id IS NULL THEN
        CALL inserisci_possessore(v_comune_id, v_cognome, v_paternita, v_nome_completo, true);
        RAISE NOTICE 'Test 1: Inserito nuovo possessore: %', v_nome_completo;
    ELSE
        RAISE NOTICE 'Test 1: Possessore già esistente con ID %: %', v_possessore_id, v_nome_completo;
    END IF;
END $$;

-- Verifica dell'inserimento (o esistenza)
SELECT pos.id, pos.cognome_nome, pos.paternita, pos.nome_completo, c.nome as comune_nome
FROM possessore pos JOIN comune c ON pos.comune_id = c.id
WHERE c.nome = 'Carcare' AND pos.cognome_nome = 'Rossi Marco';

-- 2. Test registrazione consultazione (che fallirà per duplicato se dati già caricati e stesso giorno)
DO $$
DECLARE
    v_consultazione_id INTEGER;
    v_richiedente VARCHAR := 'Lucia Neri';
    v_oggi DATE := CURRENT_DATE;
BEGIN
    SELECT id INTO v_consultazione_id FROM consultazione
    WHERE richiedente = v_richiedente AND data = v_oggi;

    IF v_consultazione_id IS NULL THEN
        CALL registra_consultazione(v_oggi, v_richiedente, 'CI XY9876543',
            'Ricerca genealogica', 'Partite di Carcare', 'Dott. Bianchi');
        RAISE NOTICE 'Test 2: Inserita nuova consultazione per: %', v_richiedente;
    ELSE
        RAISE NOTICE 'Test 2: Consultazione già esistente oggi con ID % per: %', v_consultazione_id, v_richiedente;
    END IF;
END $$;

-- Verifica della consultazione
SELECT id, data, richiedente, motivazione FROM consultazione
WHERE richiedente LIKE 'Lucia Neri%' ORDER BY data DESC;

-- 3. Test creazione partita con possessori (che fallirà per duplicato se dati già caricati)
DO $$
DECLARE
    v_partita_id INTEGER;
    v_numero_partita INTEGER := 302; -- Numero non usato negli esempi
    v_comune_id INTEGER;
    v_fossati_id INTEGER;
    v_rossi_id INTEGER;
    v_possessore_ids INTEGER[];
BEGIN
    SELECT id INTO v_comune_id FROM comune WHERE nome = 'Carcare';
    IF NOT FOUND THEN RAISE EXCEPTION 'Comune Carcare non trovato'; END IF;

    SELECT id INTO v_partita_id FROM partita
    WHERE comune_id = v_comune_id AND numero_partita = v_numero_partita;

    SELECT id INTO v_fossati_id FROM possessore WHERE comune_id=v_comune_id AND nome_completo LIKE 'Fossati%';
    SELECT id INTO v_rossi_id FROM possessore WHERE comune_id=v_comune_id AND nome_completo LIKE 'Rossi Marco%';

    v_possessore_ids := ARRAY[]::INTEGER[];
    IF v_fossati_id IS NOT NULL THEN v_possessore_ids := array_append(v_possessore_ids, v_fossati_id); END IF;
    IF v_rossi_id IS NOT NULL THEN v_possessore_ids := array_append(v_possessore_ids, v_rossi_id); END IF;

    IF v_partita_id IS NULL THEN
        IF array_length(v_possessore_ids, 1) > 0 THEN
            CALL inserisci_partita_con_possessori(v_comune_id, v_numero_partita, 'principale', CURRENT_DATE, v_possessore_ids);
            RAISE NOTICE 'Test 3: Inserita nuova partita % per comune ID % con possessori: %', v_numero_partita, v_comune_id, v_possessore_ids;
        ELSE
            RAISE NOTICE 'Test 3: Non trovati possessori (Fossati/Rossi) nel comune ID %', v_comune_id;
        END IF;
    ELSE
        RAISE NOTICE 'Test 3: Partita % per comune ID % già esistente con ID %', v_numero_partita, v_comune_id, v_partita_id;
    END IF;
END $$;

-- Verifica della nuova partita (se creata)
SELECT p.*, c.nome as comune_nome
FROM partita p JOIN comune c ON p.comune_id = c.id
WHERE c.nome = 'Carcare' AND p.numero_partita = 302;

-- 4. Ricerca di partite per numero (es. Carcare 221)
RAISE NOTICE 'Test 4: Ricerca partita numero 221';
SELECT
    p.id, c.nome as comune_nome, p.numero_partita, p.tipo, p.stato,
    string_agg(pos.nome_completo, ', ') AS possessori
FROM partita p
JOIN comune c ON p.comune_id = c.id
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
WHERE p.numero_partita = 221 AND c.nome = 'Carcare' -- Specifica anche comune per sicurezza
GROUP BY p.id, c.nome, p.numero_partita, p.tipo, p.stato;

-- 5. Ricerca di immobili per località (es. Via Giuseppe Verdi)
RAISE NOTICE 'Test 5: Ricerca immobili in Via Giuseppe Verdi';
SELECT
    i.id, i.natura, i.consistenza, i.classificazione,
    l.nome AS localita, c.nome AS comune_nome,
    p.numero_partita,
    string_agg(pos.nome_completo, ', ') AS possessori
FROM immobile i
JOIN localita l ON i.localita_id = l.id
JOIN comune c ON l.comune_id = c.id
JOIN partita p ON i.partita_id = p.id
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
WHERE l.nome LIKE '%Verdi%' AND c.nome = 'Carcare' -- Specifica comune
GROUP BY i.id, i.natura, i.consistenza, i.classificazione, l.nome, c.nome, p.numero_partita;

-- 6. Elenco completo dei possessori con le loro partite e numero immobili
RAISE NOTICE 'Test 6: Elenco possessori con partite e immobili';
SELECT
    pos.id, pos.nome_completo, c.nome AS comune_nome,
    array_agg(DISTINCT p.numero_partita) FILTER (WHERE p.id IS NOT NULL) AS partite_numero,
    count(DISTINCT i.id) AS numero_immobili
FROM possessore pos
JOIN comune c ON pos.comune_id = c.id
LEFT JOIN partita_possessore pp ON pos.id = pp.possessore_id
LEFT JOIN partita p ON pp.partita_id = p.id AND p.comune_id = pos.comune_id -- Join sicuro
LEFT JOIN immobile i ON p.id = i.partita_id
GROUP BY pos.id, pos.nome_completo, c.nome
ORDER BY c.nome, pos.nome_completo;

-- 7. Ricerca possessori per nome (utilizzando la funzione aggiornata cerca_possessori)
RAISE NOTICE 'Test 7: Ricerca possessore "Fossati"';
SELECT * FROM cerca_possessori('Fossati');

RAISE NOTICE 'Test 7: Ricerca possessore "Maria"';
SELECT * FROM cerca_possessori('Maria');

-- 8. Immobili di un possessore (utilizzando la funzione aggiornata get_immobili_possessore)
DO $$
DECLARE
    v_possessore_id INTEGER;
BEGIN
    SELECT id INTO v_possessore_id FROM possessore WHERE nome_completo LIKE 'Caviglia Maria%' LIMIT 1;
    IF v_possessore_id IS NOT NULL THEN
        RAISE NOTICE 'Test 8: Esecuzione get_immobili_possessore per ID % (Caviglia Maria)', v_possessore_id;
    ELSE
        RAISE NOTICE 'Test 8: Possessore "Caviglia Maria" non trovato';
    END IF;
END $$;

SELECT * FROM get_immobili_possessore( (SELECT id FROM possessore WHERE nome_completo LIKE 'Caviglia Maria%' LIMIT 1) );

-- 9. Uso della vista aggiornata v_partite_complete
RAISE NOTICE 'Test 9: Vista v_partite_complete (Comune Carcare)';
SELECT * FROM v_partite_complete WHERE comune_nome = 'Carcare';

-- 10. Uso della vista aggiornata v_variazioni_complete
RAISE NOTICE 'Test 10: Vista v_variazioni_complete';
SELECT * FROM v_variazioni_complete ORDER BY data_variazione DESC;

-- 11. Test Ricerca Avanzata Possessori (pg_trgm)
RAISE NOTICE 'Test 11: Ricerca avanzata possessore "Angelo Fosati" (typo)';
SELECT * FROM ricerca_avanzata_possessori('Angelo Fosati', 0.2); -- Simile a Fossati Angelo

RAISE NOTICE 'Test 11: Ricerca avanzata possessore "Rossi A"';
SELECT * FROM ricerca_avanzata_possessori('Rossi A', 0.3); -- Simile a Rossi Marco

-- 12. Test Funzione Report Annuale
DO $$
DECLARE v_comune_id INTEGER;
BEGIN
    SELECT id INTO v_comune_id FROM comune WHERE nome = 'Carcare';
    IF v_comune_id IS NOT NULL THEN
        RAISE NOTICE 'Test 12: Report annuale partite per Carcare (ID: %), Anno 1950', v_comune_id;
        PERFORM * FROM report_annuale_partite(v_comune_id, 1950); -- Chiamata per visualizzare risultati
    END IF;
END $$;
SELECT * FROM report_annuale_partite((SELECT id FROM comune WHERE nome = 'Carcare'), 1950);

RAISE NOTICE 'Tutti i test completati.';