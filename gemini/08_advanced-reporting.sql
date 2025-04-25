-- Imposta lo schema
SET search_path TO catasto;

-- 1. Vista materializzata per statistiche per comune
CREATE MATERIALIZED VIEW mv_statistiche_comune AS
SELECT
    c.nome AS comune,
    c.provincia,
    COUNT(DISTINCT p.id) AS totale_partite,
    COUNT(DISTINCT CASE WHEN p.stato = 'attiva' THEN p.id END) AS partite_attive,
    COUNT(DISTINCT CASE WHEN p.stato = 'inattiva' THEN p.id END) AS partite_inattive,
    COUNT(DISTINCT pos.id) AS totale_possessori,
    COUNT(DISTINCT i.id) AS totale_immobili
FROM comune c
LEFT JOIN partita p ON c.nome = p.comune_nome
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
LEFT JOIN immobile i ON p.id = i.partita_id
GROUP BY c.nome, c.provincia;

CREATE UNIQUE INDEX idx_mv_statistiche_comune ON mv_statistiche_comune(comune);

-- Procedura per aggiornare le statistiche
CREATE OR REPLACE PROCEDURE aggiorna_statistiche_comune()
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_statistiche_comune;
END;
$$;

-- 2. Vista materializzata per riepilogo immobili per tipologia
CREATE MATERIALIZED VIEW mv_immobili_per_tipologia AS
SELECT
    comune_nome,
    classificazione,
    COUNT(*) AS numero_immobili,
    SUM(CASE WHEN numero_piani IS NOT NULL THEN numero_piani ELSE 0 END) AS totale_piani,
    SUM(CASE WHEN numero_vani IS NOT NULL THEN numero_vani ELSE 0 END) AS totale_vani
FROM immobile i
JOIN partita p ON i.partita_id = p.id
WHERE p.stato = 'attiva'
GROUP BY comune_nome, classificazione;

CREATE INDEX idx_mv_immobili_tipologia_comune ON mv_immobili_per_tipologia(comune_nome);
CREATE INDEX idx_mv_immobili_tipologia_class ON mv_immobili_per_tipologia(classificazione);

-- 3. Vista materializzata per l'elenco completo delle partite con possessori e immobili
CREATE MATERIALIZED VIEW mv_partite_complete AS
SELECT
    p.id AS partita_id,
    p.comune_nome,
    p.numero_partita,
    p.tipo,
    p.data_impianto,
    p.stato,
    string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
    COUNT(DISTINCT i.id) AS num_immobili,
    string_agg(DISTINCT i.natura, ', ') AS tipi_immobili,
    string_agg(DISTINCT l.nome, ', ') AS localita
FROM partita p
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
LEFT JOIN immobile i ON p.id = i.partita_id
LEFT JOIN localita l ON i.localita_id = l.id
GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.data_impianto, p.stato;

CREATE INDEX idx_mv_partite_complete_comune ON mv_partite_complete(comune_nome);
CREATE INDEX idx_mv_partite_complete_numero ON mv_partite_complete(numero_partita);
CREATE INDEX idx_mv_partite_complete_stato ON mv_partite_complete(stato);

-- 4. Vista materializzata per la cronologia delle variazioni
CREATE MATERIALIZED VIEW mv_cronologia_variazioni AS
SELECT
    v.id AS variazione_id,
    v.tipo AS tipo_variazione,
    v.data_variazione,
    p_orig.numero_partita AS partita_origine_numero,
    p_orig.comune_nome AS comune_origine,
    string_agg(DISTINCT pos_orig.nome_completo, ', ') AS possessori_origine,
    p_dest.numero_partita AS partita_dest_numero,
    p_dest.comune_nome AS comune_dest,
    string_agg(DISTINCT pos_dest.nome_completo, ', ') AS possessori_dest,
    c.tipo AS tipo_contratto,
    c.notaio,
    c.data_contratto
FROM variazione v
JOIN partita p_orig ON v.partita_origine_id = p_orig.id
LEFT JOIN partita p_dest ON v.partita_destinazione_id = p_dest.id
LEFT JOIN contratto c ON v.id = c.variazione_id
LEFT JOIN partita_possessore pp_orig ON p_orig.id = pp_orig.partita_id
LEFT JOIN possessore pos_orig ON pp_orig.possessore_id = pos_orig.id
LEFT JOIN partita_possessore pp_dest ON p_dest.id = pp_dest.partita_id
LEFT JOIN possessore pos_dest ON pp_dest.possessore_id = pos_dest.id
GROUP BY v.id, v.tipo, v.data_variazione, p_orig.numero_partita, p_orig.comune_nome,
         p_dest.numero_partita, p_dest.comune_nome, c.tipo, c.notaio, c.data_contratto;

CREATE INDEX idx_mv_variazioni_data ON mv_cronologia_variazioni(data_variazione);
CREATE INDEX idx_mv_variazioni_tipo ON mv_cronologia_variazioni(tipo_variazione);
CREATE INDEX idx_mv_variazioni_comune_orig ON mv_cronologia_variazioni(comune_origine);

-- 5. Funzione per generare report annuale delle partite per comune
CREATE OR REPLACE FUNCTION report_annuale_partite(p_comune VARCHAR, p_anno INTEGER)
RETURNS TABLE (
    numero_partita INTEGER,
    tipo VARCHAR,
    data_impianto DATE,
    stato VARCHAR,
    possessori TEXT,
    num_immobili BIGINT,
    variazioni_anno BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.numero_partita,
        p.tipo,
        p.data_impianto,
        p.stato,
        string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
        COUNT(DISTINCT i.id) AS num_immobili,
        (SELECT COUNT(*) FROM variazione v
         WHERE (v.partita_origine_id = p.id OR v.partita_destinazione_id = p.id)
         AND EXTRACT(YEAR FROM v.data_variazione) = p_anno) AS variazioni_anno
    FROM partita p
    LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
    LEFT JOIN possessore pos ON pp.possessore_id = pos.id
    LEFT JOIN immobile i ON p.id = i.partita_id
    WHERE p.comune_nome = p_comune 
    AND (EXTRACT(YEAR FROM p.data_impianto) <= p_anno)
    AND (p.data_chiusura IS NULL OR EXTRACT(YEAR FROM p.data_chiusura) >= p_anno)
    GROUP BY p.id, p.numero_partita, p.tipo, p.data_impianto, p.stato
    ORDER BY p.numero_partita;
END;
$$ LANGUAGE plpgsql;

-- 6. Funzione per generare report delle proprietà di un possessore in un determinato periodo
CREATE OR REPLACE FUNCTION report_proprieta_possessore(
    p_possessore_id INTEGER,
    p_data_inizio DATE,
    p_data_fine DATE
)
RETURNS TABLE (
    partita_id INTEGER,
    comune_nome VARCHAR,
    numero_partita INTEGER,
    titolo VARCHAR,
    quota VARCHAR,
    data_inizio DATE,
    data_fine DATE,
    immobili_posseduti TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS partita_id,
        p.comune_nome,
        p.numero_partita,
        pp.titolo,
        pp.quota,
        GREATEST(p.data_impianto, p_data_inizio) AS data_inizio,
        LEAST(COALESCE(p.data_chiusura, p_data_fine), p_data_fine) AS data_fine,
        string_agg(i.natura || ' in ' || l.nome, ', ') AS immobili_posseduti
    FROM partita p
    JOIN partita_possessore pp ON p.id = pp.partita_id
    LEFT JOIN immobile i ON p.id = i.partita_id
    LEFT JOIN localita l ON i.localita_id = l.id
    WHERE pp.possessore_id = p_possessore_id
    AND p.data_impianto <= p_data_fine
    AND (p.data_chiusura IS NULL OR p.data_chiusura >= p_data_inizio)
    GROUP BY p.id, p.comune_nome, p.numero_partita, pp.titolo, pp.quota
    ORDER BY p.comune_nome, p.numero_partita;
END;
$$ LANGUAGE plpgsql;

-- 7. Procedura per aggiornare tutte le viste materializzate
CREATE OR REPLACE PROCEDURE aggiorna_tutte_statistiche()
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_statistiche_comune;
    REFRESH MATERIALIZED VIEW mv_immobili_per_tipologia;
    REFRESH MATERIALIZED VIEW mv_partite_complete;
    REFRESH MATERIALIZED VIEW mv_cronologia_variazioni;
END;
$$;

-- Pianificazione dell'aggiornamento automatico delle viste materializzate
-- NOTA: questa è solo una dimostrazione. In PostgreSQL questo va fatto con pg_cron o con un job esterno
COMMENT ON PROCEDURE aggiorna_tutte_statistiche() IS 'Procedura da eseguire con pg_cron o job esterno giornaliero';

-- Aggiornamento iniziale delle viste materializzate
CALL aggiorna_tutte_statistiche();