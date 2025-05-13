-- File: 16_advanced_search.sql (Versione Corretta)
-- Oggetto: Funzioni per la ricerca avanzata nel database Catasto Storico
-- Versione: 1.1
-- Data: 30/04/2025
-- Note: Corretta sintassi funzione e aggiunto join con comune.

-- Imposta lo schema (assicurati che sia corretto nel tuo ambiente)
SET search_path TO catasto, public; -- Aggiunto public se pg_trgm è lì

-- ========================================================================
-- Funzione: ricerca_avanzata_possessori
-- Ricerca possessori basandosi sulla similarità testuale con nome/cognome/paternità
-- utilizzando l'estensione pg_trgm.
-- Include il nome del comune nei risultati.
-- ========================================================================
CREATE OR REPLACE FUNCTION ricerca_avanzata_possessori(
    p_query_text TEXT,
    p_similarity_threshold REAL DEFAULT 0.2 -- Soglia minima di similarità (0.0 - 1.0)
)
RETURNS TABLE (
    id INTEGER,             -- ID del possessore trovato
    nome_completo VARCHAR,  -- Nome completo del possessore
    comune_nome VARCHAR,    -- Nome del comune di residenza/riferimento del possessore
    similarity REAL,        -- Punteggio di similarità calcolato (0.0 a 1.0)
    num_partite BIGINT      -- Numero di partite catastali associate a questo possessore
) AS $$
BEGIN
    -- Esegui la query di ricerca per similarità
    RETURN QUERY
    WITH possessore_similarity AS (
        -- Sottoquery per calcolare la similarità per ogni possessore
        SELECT
            p.id,
            p.nome_completo,
            c.nome AS comune_nome, -- Seleziona il nome del comune tramite JOIN
            -- Calcola la similarità massima tra il termine di ricerca e i campi rilevanti
            GREATEST(
                similarity(p.nome_completo, p_query_text),
                similarity(p.cognome_nome, p_query_text),
                COALESCE(similarity(p.paternita, p_query_text), 0.0) -- Gestisce paternita NULL
            ) AS sim
        FROM possessore p
        JOIN comune c ON p.comune_id = c.id -- *** JOIN con la tabella comune ***
        WHERE
            -- Filtro preliminare usando l'operatore % di pg_trgm (efficiente se indicizzato)
            -- Controlla se c'è una qualche similarità, anche bassa
            p.nome_completo % p_query_text
            OR p.cognome_nome % p_query_text
            OR (p.paternita IS NOT NULL AND p.paternita % p_query_text)
    )
    -- Seleziona i risultati finali, applica la soglia e conta le partite
    SELECT
        ps.id,
        ps.nome_completo,
        ps.comune_nome,         -- Nome del comune ottenuto dalla CTE
        ps.sim AS similarity,
        COUNT(DISTINCT pp.partita_id)::BIGINT AS num_partite -- Conta le partite associate
    FROM possessore_similarity ps
    LEFT JOIN partita_possessore pp ON ps.id = pp.possessore_id -- Join per contare le partite
    WHERE ps.sim >= p_similarity_threshold -- Applica la soglia minima di similarità
    GROUP BY ps.id, ps.nome_completo, ps.comune_nome, ps.sim -- Raggruppa per calcolare num_partite
    ORDER BY similarity DESC, ps.nome_completo -- Ordina per similarità decrescente
    LIMIT 100; -- Limita il numero di risultati per sicurezza e performance

END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ricerca_avanzata_possessori(TEXT, REAL) IS
'Ricerca possessori tramite similarità testuale (pg_trgm) su nome_completo, cognome_nome e paternita, restituendo anche il nome del comune e il numero di partite associate. Richiede l''estensione pg_trgm.';

-- ========================================================================
-- OTTIMIZZAZIONE (CONSIGLIATA): Creare indici GIN per pg_trgm
-- Questi indici migliorano drasticamente le performance della ricerca per similarità
-- su tabelle grandi. Eseguire una sola volta dopo aver creato l'estensione.
-- (Lasciati commentati per evitare errori se già esistenti o se l'estensione non c'è)
-- ========================================================================
/* -- Decommenta per creare gli indici (esegui una sola volta)

-- Indice principale su nome_completo
CREATE INDEX IF NOT EXISTS idx_gin_possessore_nome_completo_trgm
ON possessore
USING gin (nome_completo gin_trgm_ops);

-- Indice opzionale su cognome_nome
CREATE INDEX IF NOT EXISTS idx_gin_possessore_cognome_nome_trgm
ON possessore
USING gin (cognome_nome gin_trgm_ops);

-- Indice opzionale su paternita (solo per valori non NULL)
CREATE INDEX IF NOT EXISTS idx_gin_possessore_paternita_trgm
ON possessore
USING gin (paternita gin_trgm_ops)
WHERE paternita IS NOT NULL;

*/