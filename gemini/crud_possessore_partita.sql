
-- ========================================================
-- CRUD per la tabella `possessore`
-- ========================================================

-- CREATE
CREATE OR REPLACE PROCEDURE inserisci_possessore(
    p_comune_nome VARCHAR,
    p_cognome_nome VARCHAR,
    p_paternita VARCHAR,
    p_nome_completo VARCHAR,
    p_attivo BOOLEAN DEFAULT true
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO catasto.possessore (comune_nome, cognome_nome, paternita, nome_completo, attivo)
    VALUES (p_comune_nome, p_cognome_nome, p_paternita, p_nome_completo, p_attivo);
END;
$$;

-- READ
CREATE OR REPLACE FUNCTION leggi_possessore(p_id INTEGER)
RETURNS TABLE (
    id INTEGER,
    nome_completo VARCHAR,
    comune_nome VARCHAR,
    attivo BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT id, nome_completo, comune_nome, attivo
    FROM catasto.possessore
    WHERE id = p_id;
END;
$$ LANGUAGE plpgsql;

-- UPDATE
CREATE OR REPLACE PROCEDURE aggiorna_possessore(
    p_id INTEGER,
    p_nome_completo VARCHAR,
    p_attivo BOOLEAN
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE catasto.possessore
    SET nome_completo = p_nome_completo,
        attivo = p_attivo,
        data_modifica = CURRENT_TIMESTAMP
    WHERE id = p_id;
END;
$$;

-- DELETE (soft delete)
CREATE OR REPLACE PROCEDURE disattiva_possessore(p_id INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE catasto.possessore
    SET attivo = FALSE,
        data_modifica = CURRENT_TIMESTAMP
    WHERE id = p_id;
END;
$$;


-- ========================================================
-- CRUD per la tabella `partita`
-- ========================================================

-- CREATE
CREATE OR REPLACE PROCEDURE inserisci_partita(
    p_comune_nome VARCHAR,
    p_numero_partita INTEGER,
    p_tipo VARCHAR,
    p_data_impianto DATE,
    p_stato VARCHAR DEFAULT 'attiva'
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO catasto.partita (
        comune_nome, numero_partita, tipo, data_impianto, stato, data_creazione, data_modifica
    ) VALUES (
        p_comune_nome, p_numero_partita, p_tipo, p_data_impianto, p_stato, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
    );
END;
$$;

-- READ
CREATE OR REPLACE FUNCTION leggi_partita(p_id INTEGER)
RETURNS TABLE (
    id INTEGER,
    comune_nome VARCHAR,
    numero_partita INTEGER,
    tipo VARCHAR,
    stato VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT id, comune_nome, numero_partita, tipo, stato
    FROM catasto.partita
    WHERE id = p_id;
END;
$$ LANGUAGE plpgsql;

-- UPDATE
CREATE OR REPLACE PROCEDURE aggiorna_partita(
    p_id INTEGER,
    p_stato VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE catasto.partita
    SET stato = p_stato,
        data_modifica = CURRENT_TIMESTAMP
    WHERE id = p_id;
END;
$$;

-- DELETE (soft delete)
CREATE OR REPLACE PROCEDURE disattiva_partita(p_id INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE catasto.partita
    SET stato = 'disattivata',
        data_modifica = CURRENT_TIMESTAMP
    WHERE id = p_id;
END;
$$;
