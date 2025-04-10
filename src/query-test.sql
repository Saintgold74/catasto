-- Imposta lo schema
SET search_path TO catasto;

-- 1. Test inserimento nuovo possessore (con transazione esplicita)
BEGIN;
CALL inserisci_possessore('Carcare', 'Rossi Marco', 'fu Antonio', 'Rossi Marco fu Antonio', true);
COMMIT;

-- Verifica dell'inserimento
SELECT * FROM possessore WHERE cognome_nome = 'Rossi Marco';

-- 2. Test registrazione consultazione (con transazione esplicita)
BEGIN;
CALL registra_consultazione(CURRENT_DATE, 'Lucia Neri', 'CI XY9876543', 
   'Ricerca genealogica', 'Partite di Carcare', 'Dott. Bianchi');
COMMIT;

-- Verifica della consultazione
SELECT * FROM consultazione WHERE richiedente = 'Lucia Neri';

-- 3. Test creazione partita con possessori
BEGIN;
CALL inserisci_partita_con_possessori(
    'Carcare',           -- comune
    301,                 -- numero partita
    'principale',        -- tipo
    CURRENT_DATE,        -- data impianto
    ARRAY[1, 7]          -- id dei possessori (Fossati Angelo e Rossi Marco)
);
COMMIT;

-- Verifica della nuova partita
SELECT * FROM v_partite_complete WHERE numero_partita = 301;

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
    array_agg(DISTINCT p.numero_partita) AS partite,
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
SELECT * FROM get_immobili_possessore(1);

-- 9. Uso della vista per visualizzare partite complete
SELECT * FROM v_partite_complete WHERE comune_nome = 'Carcare';

-- 10. Uso della vista per visualizzare variazioni
SELECT * FROM v_variazioni_complete;