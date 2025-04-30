-- File: 17_funzione_ricerca_immobili.sql
-- Oggetto: Definizione funzione per ricerca avanzata immobili
-- Versione: 1.0
-- Data: 30/04/2025

SET search_path TO catasto, public; -- Assicurati che lo schema sia corretto

-- ========================================================================
-- Funzione: ricerca_avanzata_immobili
-- Ricerca immobili basandosi su criteri multipli, inclusi dati da tabelle collegate.
-- ========================================================================
CREATE OR REPLACE FUNCTION ricerca_avanzata_immobili(
    p_comune_id INTEGER DEFAULT NULL,         -- ID del comune (o NULL per tutti)
    p_natura TEXT DEFAULT NULL,               -- Natura immobile (ricerca parziale ILIKE)
    p_localita TEXT DEFAULT NULL,             -- Nome località (ricerca parziale ILIKE)
    p_classificazione TEXT DEFAULT NULL,      -- Classificazione (ricerca esatta o ILIKE se preferito)
    p_possessore TEXT DEFAULT NULL            -- Nome possessore (ricerca parziale ILIKE)
)
RETURNS TABLE (
    immobile_id INTEGER,
    natura VARCHAR,
    localita_nome VARCHAR,
    comune_nome VARCHAR,
    partita_numero INTEGER,
    classificazione VARCHAR,
    possessori TEXT -- Aggregazione dei nomi possessori
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT -- Evita duplicati se un immobile ha più possessori che matchano
        i.id AS immobile_id,
        i.natura,
        l.nome AS localita_nome,
        c.nome AS comune_nome,
        p.numero_partita,
        i.classificazione,
        string_agg(DISTINCT pos.nome_completo, ', ') AS possessori
    FROM immobile i
    JOIN partita p ON i.partita_id = p.id
    JOIN localita l ON i.localita_id = l.id
    JOIN comune c ON p.comune_id = c.id
    -- Join opzionale per filtrare per possessore
    LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
    LEFT JOIN possessore pos ON pp.possessore_id = pos.id
    WHERE
        (p_comune_id IS NULL OR p.comune_id = p_comune_id)
    AND (p_natura IS NULL OR i.natura ILIKE '%' || p_natura || '%')
    AND (p_localita IS NULL OR l.nome ILIKE '%' || p_localita || '%')
    AND (p_classificazione IS NULL OR i.classificazione ILIKE p_classificazione) -- Usiamo ILIKE per flessibilità, cambia in = se serve esatto
    AND (
            p_possessore IS NULL -- Se non viene fornito il possessore, non filtrare per quello
            OR -- Altrimenti, verifica se ALMENO UN possessore della partita matcha
            EXISTS (
                SELECT 1
                FROM partita_possessore pp_check
                JOIN possessore pos_check ON pp_check.possessore_id = pos_check.id
                WHERE pp_check.partita_id = p.id
                  AND pos_check.nome_completo ILIKE '%' || p_possessore || '%'
            )
        )
    GROUP BY i.id, i.natura, l.nome, c.nome, p.numero_partita, i.classificazione -- Raggruppa per aggregare i possessori
    ORDER BY c.nome, p.numero_partita, i.natura;

END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ricerca_avanzata_immobili(INTEGER, TEXT, TEXT, TEXT, TEXT) IS
'Ricerca immobili avanzata per comune ID, natura, località, classificazione e nome possessore.';