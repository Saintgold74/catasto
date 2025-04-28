-- Imposta lo schema
SET search_path TO catasto;

-- 1. Test inserimento nuovo possessore (con gestione duplicati)
DO $$
DECLARE
    v_possessore_id INTEGER;
    v_cognome VARCHAR := 'Rossi Marco';
    v_paternita VARCHAR := 'fu Antonio';
    v_nome_completo VARCHAR := 'Rossi Marco fu Antonio';
BEGIN
    -- Verifica se il possessore esiste già
    SELECT id INTO v_possessore_id FROM possessore 
    WHERE cognome_nome = v_cognome AND paternita = v_paternita;
    
    IF v_possessore_id IS NULL THEN
        -- Inserisci il nuovo possessore
        CALL inserisci_possessore('Carcare', v_cognome, v_paternita, v_nome_completo, true);
        RAISE NOTICE 'Inserito nuovo possessore: %', v_nome_completo;
    ELSE
        RAISE NOTICE 'Possessore già esistente con ID %: %', v_possessore_id, v_nome_completo;
    END IF;
END $$;

-- Verifica dell'inserimento
SELECT id, cognome_nome, paternita, nome_completo FROM possessore 
WHERE cognome_nome = 'Rossi Marco';

-- 2. Test registrazione consultazione (con gestione duplicati)
DO $$
DECLARE
    v_consultazione_id INTEGER;
    v_richiedente VARCHAR := 'Lucia Neri';
    v_documento VARCHAR := 'CI XY9876543';
    v_oggi DATE := CURRENT_DATE;
BEGIN
    -- Verifica se la consultazione esiste già
    SELECT id INTO v_consultazione_id FROM consultazione 
    WHERE richiedente = v_richiedente AND data = v_oggi;
    
    IF v_consultazione_id IS NULL THEN
        -- Inserisci la nuova consultazione
        CALL registra_consultazione(v_oggi, v_richiedente, v_documento, 
            'Ricerca genealogica', 'Partite di Carcare', 'Dott. Bianchi');
        RAISE NOTICE 'Inserita nuova consultazione per: %', v_richiedente;
    ELSE
        RAISE NOTICE 'Consultazione già esistente con ID % per: %', v_consultazione_id, v_richiedente;
    END IF;
END $$;

-- Verifica della consultazione
SELECT id, data, richiedente, motivazione FROM consultazione 
WHERE richiedente = 'Lucia Neri';

-- 3. Test creazione partita con possessori (con gestione duplicati)
DO $$
DECLARE
    v_partita_id INTEGER;
    v_numero_partita INTEGER := 302; -- Cambiato da 301 a 302
    v_comune VARCHAR := 'Carcare';
    v_fossati_id INTEGER;
    v_rossi_id INTEGER;
    v_possessore_ids INTEGER[];
BEGIN
    -- Verifica se la partita esiste già
    SELECT id INTO v_partita_id FROM partita 
    WHERE comune_nome = v_comune AND numero_partita = v_numero_partita;
    
    -- Trova gli ID dei possessori
    SELECT id INTO v_fossati_id FROM possessore 
    WHERE nome_completo LIKE 'Fossati%' LIMIT 1;
    
    SELECT id INTO v_rossi_id FROM possessore 
    WHERE cognome_nome = 'Rossi Marco' LIMIT 1;
    
    -- Costruisci l'array degli ID dei possessori
    IF v_fossati_id IS NOT NULL AND v_rossi_id IS NOT NULL THEN
        v_possessore_ids := ARRAY[v_fossati_id, v_rossi_id];
    ELSIF v_fossati_id IS NOT NULL THEN
        v_possessore_ids := ARRAY[v_fossati_id];
    ELSIF v_rossi_id IS NOT NULL THEN
        v_possessore_ids := ARRAY[v_rossi_id];
    ELSE
        v_possessore_ids := '{}';
    END IF;
    
    IF v_partita_id IS NULL THEN
        -- Inserisci la nuova partita
        IF array_length(v_possessore_ids, 1) > 0 THEN
            CALL inserisci_partita_con_possessori(
                v_comune,
                v_numero_partita,
                'principale',
                CURRENT_DATE,
                v_possessore_ids
            );
            RAISE NOTICE 'Inserita nuova partita % per il comune % con possessori: %', 
                v_numero_partita, v_comune, v_possessore_ids;
        ELSE
            RAISE NOTICE 'Non sono stati trovati possessori validi per la partita';
        END IF;
    ELSE
        RAISE NOTICE 'Partita già esistente con ID %: % - %', v_partita_id, v_comune, v_numero_partita;
    END IF;
END $$;

-- Verifica della nuova partita
SELECT * FROM partita WHERE comune_nome = 'Carcare' AND numero_partita = 302;

SELECT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato,
       pos.id AS possessore_id, pos.nome_completo
FROM partita p
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
WHERE p.comune_nome = 'Carcare' AND p.numero_partita = 302;

-- 4. Ricerca di partite per numero
SELECT 
    p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato,
    string_agg(pos.nome_completo, ', ') AS possessori
FROM partita p
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
WHERE p.numero_partita = 221
GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato;

-- 5. Ricerca di immobili per località
SELECT 
    i.id, i.natura, i.consistenza, i.classificazione,
    l.nome AS localita, l.comune_nome,
    p.numero_partita, 
    string_agg(pos.nome_completo, ', ') AS possessori
FROM immobile i
JOIN localita l ON i.localita_id = l.id
JOIN partita p ON i.partita_id = p.id
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
WHERE l.nome LIKE '%Verdi%'
GROUP BY i.id, i.natura, i.consistenza, i.classificazione, l.nome, l.comune_nome, p.numero_partita;

-- 6. Elenco completo dei possessori con le loro partite
SELECT
    pos.id, pos.nome_completo, pos.comune_nome,
    array_agg(DISTINCT p.numero_partita) FILTER (WHERE p.id IS NOT NULL) AS partite,
    count(DISTINCT i.id) AS numero_immobili
FROM possessore pos
LEFT JOIN partita_possessore pp ON pos.id = pp.possessore_id
LEFT JOIN partita p ON pp.partita_id = p.id
LEFT JOIN immobile i ON p.id = i.partita_id
GROUP BY pos.id, pos.nome_completo, pos.comune_nome
ORDER BY pos.nome_completo;

-- 7. Ricerca possessori per nome (utilizzando la funzione creata)
SELECT * FROM cerca_possessori('Fossati');

-- 8. Immobili di un possessore (utilizzando la funzione creata)
DO $$
DECLARE
    v_possessore_id INTEGER;
BEGIN
    SELECT id INTO v_possessore_id FROM possessore 
    WHERE nome_completo LIKE 'Fossati%' LIMIT 1;
    
    IF v_possessore_id IS NOT NULL THEN
        RAISE NOTICE 'Esecuzione get_immobili_possessore per ID %', v_possessore_id;
        -- La tabella dei risultati sarà visualizzata dopo questo blocco
    ELSE
        RAISE NOTICE 'Possessore "Fossati" non trovato';
    END IF;
END $$;

SELECT * FROM get_immobili_possessore(
    (SELECT id FROM possessore WHERE nome_completo LIKE 'Fossati%' LIMIT 1)
);

-- 9. Uso della vista per visualizzare partite complete
-- Verifica se la vista esiste
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_views 
               WHERE schemaname = 'catasto' AND viewname = 'v_partite_complete') THEN
        RAISE NOTICE 'Vista v_partite_complete disponibile';
    ELSE
        RAISE NOTICE 'Vista v_partite_complete non disponibile - potrebbe essere necessario crearla';
    END IF;
END $$;

-- Esegui la query in modo sicuro
SELECT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato,
       string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
       COUNT(DISTINCT i.id) AS num_immobili
FROM partita p
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
LEFT JOIN immobile i ON p.id = i.partita_id
WHERE p.comune_nome = 'Carcare'
GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato;

-- 10. Uso della vista per visualizzare variazioni
-- Verifica se la vista esiste
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_views 
               WHERE schemaname = 'catasto' AND viewname = 'v_variazioni_complete') THEN
        RAISE NOTICE 'Vista v_variazioni_complete disponibile';
    ELSE
        RAISE NOTICE 'Vista v_variazioni_complete non disponibile - potrebbe essere necessario crearla';
    END IF;
END $$;

-- Esegui la query in modo sicuro
SELECT 
    v.id AS variazione_id,
    v.tipo AS tipo_variazione,
    v.data_variazione,
    p_orig.numero_partita AS partita_origine_numero,
    p_orig.comune_nome AS partita_origine_comune,
    p_dest.numero_partita AS partita_dest_numero,
    p_dest.comune_nome AS partita_dest_comune,
    c.tipo AS tipo_contratto,
    c.data_contratto,
    c.notaio,
    c.repertorio
FROM variazione v
JOIN partita p_orig ON v.partita_origine_id = p_orig.id
LEFT JOIN partita p_dest ON v.partita_destinazione_id = p_dest.id
LEFT JOIN contratto c ON v.id = c.variazione_id;