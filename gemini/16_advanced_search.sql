-- Imposta lo schema (assicurati che sia corretto nel tuo script)
SET search_path TO catasto, public; -- Aggiungi public se pg_trgm è lì

-- ========================================================================
-- Funzione: ricerca_avanzata_possessori
-- Ricerca possessori basandosi sulla similarità testuale con nome/cognome/paternità
-- utilizzando l'estensione pg_trgm.
-- ========================================================================
CREATE OR REPLACE FUNCTION ricerca_avanzata_possessori(
    p_query_text TEXT,
    p_similarity_threshold REAL DEFAULT 0.2 -- Soglia minima di similarità (0.0 - 1.0)
)
RETURNS TABLE (
    id INTEGER,
    nome_completo VARCHAR,
    comune_nome VARCHAR,
    similarity REAL, -- Similarità calcolata
    num_partite BIGINT -- Numero di partite associate
) AS $$
BEGIN
    -- Verifica che pg_trgm sia installato (opzionale, ma utile)
    -- PERFORM 1 FROM pg_extension WHERE extname = 'pg_trgm';
    -- IF NOT FOUND THEN
    --    RAISE EXCEPTION 'Estensione pg_trgm non installata. Eseguire: CREATE EXTENSION pg_trgm;';
    -- END IF;

    -- Esegui la query di ricerca per similarità
    RETURN QUERY
    WITH possessore_similarity AS (
        SELECT
            p.id,
            p.nome_completo,
            p.comune_nome,
            -- Calcola la similarità massima tra il termine di ricerca e i campi rilevanti
            GREATEST(
                similarity(p.nome_completo, p_query_text),
                similarity(p.cognome_nome, p_query_text),
                COALESCE(similarity(p.paternita, p_query_text), 0.0) -- Gestisce paternita NULL
            ) AS sim
        FROM possessore p
        WHERE
            -- Filtra usando l'operatore % di pg_trgm (più veloce se indicizzato)
            -- Oppure usando la funzione similarity()
            p.nome_completo % p_query_text
            OR p.cognome_nome % p_query_text
            OR (p.paternita IS NOT NULL AND p.paternita % p_query_text)
    )
    SELECT
        ps.id,
        ps.nome_completo,
        ps.comune_nome,
        ps.sim AS similarity,
        COUNT(DISTINCT pp.partita_id) AS num_partite
    FROM possessore_similarity ps
    LEFT JOIN partita_possessore pp ON ps.id = pp.possessore_id -- Join per contare le partite
    WHERE ps.sim >= p_similarity_threshold -- Applica la soglia di similarità
    GROUP BY ps.id, ps.nome_completo, ps.comune_nome, ps.sim -- Raggruppa per calcolare num_partite
    ORDER BY similarity DESC, ps.nome_completo -- Ordina per similarità decrescente
    LIMIT 100; -- Limita i risultati per sicurezza/performance

END;
$$ LANGUAGE plpgsql;

-- ========================================================================
-- OTTIMIZZAZIONE (CONSIGLIATA): Creare un indice GIN per pg_trgm
-- Questo migliora drasticamente le performance della ricerca per similarità
-- su tabelle grandi. Eseguire una sola volta.
-- ========================================================================
-- Crea indice su nome_completo (il campo più probabile per la ricerca)
--CREATE INDEX IF NOT EXISTS idx_gin_possessore_nome_completo_trgm
ON possessore
USING gin (nome_completo gin_trgm_ops);

-- Crea indici simili anche per cognome_nome e paternita se si prevede
-- di fare ricerche frequenti specificamente su quei campi
--CREATE INDEX IF NOT EXISTS idx_gin_possessore_cognome_nome_trgm
ON possessore
USING gin (cognome_nome gin_trgm_ops);

--CREATE INDEX IF NOT EXISTS idx_gin_possessore_paternita_trgm
ON possessore
USING gin (paternita gin_trgm_ops)
WHERE paternita IS NOT NULL; -- Indice su colonna nullable