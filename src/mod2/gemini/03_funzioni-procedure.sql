-- Imposta lo schema
SET search_path TO catasto;

-- 1. Funzione per aggiornare automaticamente il timestamp di modifica
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.data_modifica = now();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Applica i trigger per aggiornare il timestamp sulle tabelle principali
CREATE TRIGGER update_comune_modifica
BEFORE UPDATE ON comune
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_partita_modifica
BEFORE UPDATE ON partita
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_possessore_modifica
BEFORE UPDATE ON possessore
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_immobile_modifica
BEFORE UPDATE ON immobile
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_localita_modifica
BEFORE UPDATE ON localita
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_variazione_modifica
BEFORE UPDATE ON variazione
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- 2. Procedura per inserire un nuovo possessore (CORRETTA: senza COMMIT)
CREATE OR REPLACE PROCEDURE inserisci_possessore(
    p_comune_nome VARCHAR(100),
    p_cognome_nome VARCHAR(255),
    p_paternita VARCHAR(255),
    p_nome_completo VARCHAR(255),
    p_attivo BOOLEAN DEFAULT TRUE
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO possessore(comune_nome, cognome_nome, paternita, nome_completo, attivo)
    VALUES (p_comune_nome, p_cognome_nome, p_paternita, p_nome_completo, p_attivo);
END;
$$;

-- 3. Funzione per verificare se una partita è attiva
CREATE OR REPLACE FUNCTION is_partita_attiva(p_partita_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_stato VARCHAR(20);
BEGIN
    SELECT stato INTO v_stato FROM partita WHERE id = p_partita_id;
    RETURN (v_stato = 'attiva');
END;
$$ LANGUAGE plpgsql;

-- 4. Procedura per registrare una nuova partita e relativi possessori (CORRETTA: senza COMMIT)
CREATE OR REPLACE PROCEDURE inserisci_partita_con_possessori(
    p_comune_nome VARCHAR(100),
    p_numero_partita INTEGER,
    p_tipo VARCHAR(20),
    p_data_impianto DATE,
    p_possessore_ids INTEGER[]
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_partita_id INTEGER;
    v_possessore_id INTEGER;
BEGIN
    -- Inserisci la partita
    INSERT INTO partita(comune_nome, numero_partita, tipo, data_impianto, stato)
    VALUES (p_comune_nome, p_numero_partita, p_tipo, p_data_impianto, 'attiva')
    RETURNING id INTO v_partita_id;
    
    -- Collega i possessori
    FOREACH v_possessore_id IN ARRAY p_possessore_ids
    LOOP
        INSERT INTO partita_possessore(partita_id, possessore_id, tipo_partita)
        VALUES (v_partita_id, v_possessore_id, p_tipo);
    END LOOP;
END;
$$;

-- 5. Procedura per registrare una variazione di proprietà (CORRETTA: senza COMMIT)
CREATE OR REPLACE PROCEDURE registra_variazione(
    p_partita_origine_id INTEGER,
    p_partita_destinazione_id INTEGER,
    p_tipo VARCHAR(50),
    p_data_variazione DATE,
    p_numero_riferimento VARCHAR(50),
    p_nominativo_riferimento VARCHAR(255),
    p_tipo_contratto VARCHAR(50),
    p_data_contratto DATE,
    p_notaio VARCHAR(255),
    p_repertorio VARCHAR(100),
    p_note TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_variazione_id INTEGER;
BEGIN
    -- Verifica che la partita origine sia attiva
    IF NOT is_partita_attiva(p_partita_origine_id) THEN
        RAISE EXCEPTION 'La partita di origine non è attiva';
    END IF;
    
    -- Inserisci la variazione
    INSERT INTO variazione(partita_origine_id, partita_destinazione_id, tipo, data_variazione, 
                          numero_riferimento, nominativo_riferimento)
    VALUES (p_partita_origine_id, p_partita_destinazione_id, p_tipo, p_data_variazione, 
           p_numero_riferimento, p_nominativo_riferimento)
    RETURNING id INTO v_variazione_id;
    
    -- Inserisci il contratto associato
    INSERT INTO contratto(variazione_id, tipo, data_contratto, notaio, repertorio, note)
    VALUES (v_variazione_id, p_tipo_contratto, p_data_contratto, p_notaio, p_repertorio, p_note);
    
    -- Se è una variazione che inattiva la partita di origine
    IF p_tipo IN ('Vendita', 'Successione', 'Frazionamento') THEN
        UPDATE partita SET stato = 'inattiva', data_chiusura = p_data_variazione
        WHERE id = p_partita_origine_id;
    END IF;
END;
$$;

-- 6. Funzione per ottenere tutti gli immobili di un possessore
CREATE OR REPLACE FUNCTION get_immobili_possessore(p_possessore_id INTEGER)
RETURNS TABLE (
    immobile_id INTEGER,
    natura VARCHAR(100),
    localita_nome VARCHAR(255),
    comune VARCHAR(100),
    partita_numero INTEGER,
    tipo_partita VARCHAR(20)
) AS $$
BEGIN
    RETURN QUERY
    SELECT i.id, i.natura, l.nome, l.comune_nome, p.numero_partita, pp.tipo_partita
    FROM immobile i
    JOIN localita l ON i.localita_id = l.id
    JOIN partita p ON i.partita_id = p.id
    JOIN partita_possessore pp ON p.id = pp.partita_id
    WHERE pp.possessore_id = p_possessore_id AND p.stato = 'attiva';
END;
$$ LANGUAGE plpgsql;

-- 7. Procedura per registrare una consultazione (CORRETTA: senza COMMIT)
CREATE OR REPLACE PROCEDURE registra_consultazione(
    p_data DATE,
    p_richiedente VARCHAR(255),
    p_documento_identita VARCHAR(100),
    p_motivazione TEXT,
    p_materiale_consultato TEXT,
    p_funzionario_autorizzante VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO consultazione(data, richiedente, documento_identita, motivazione, 
                             materiale_consultato, funzionario_autorizzante)
    VALUES (p_data, p_richiedente, p_documento_identita, p_motivazione, 
           p_materiale_consultato, p_funzionario_autorizzante);
END;
$$;

-- 8. Vista per facilitare la ricerca di partite
CREATE OR REPLACE VIEW v_partite_complete AS
SELECT 
    p.id AS partita_id,
    p.comune_nome,
    p.numero_partita,
    p.tipo,
    p.data_impianto,
    p.data_chiusura,
    p.stato,
    pos.id AS possessore_id,
    pos.cognome_nome,
    pos.paternita,
    pos.nome_completo,
    pp.titolo,
    pp.quota,
    COUNT(i.id) AS num_immobili
FROM partita p
LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
LEFT JOIN possessore pos ON pp.possessore_id = pos.id
LEFT JOIN immobile i ON p.id = i.partita_id
GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.data_impianto, p.data_chiusura, 
         p.stato, pos.id, pos.cognome_nome, pos.paternita, pos.nome_completo, pp.titolo, pp.quota;

-- 9. Vista per le variazioni complete con contratti
CREATE OR REPLACE VIEW v_variazioni_complete AS
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

-- 10. Funzione per ricerca full-text di possessori
CREATE OR REPLACE FUNCTION cerca_possessori(p_query TEXT)
RETURNS TABLE (
    id INTEGER,
    nome_completo VARCHAR(255),
    comune_nome VARCHAR(100),
    num_partite BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.nome_completo,
        p.comune_nome,
        COUNT(DISTINCT pp.partita_id) AS num_partite
    FROM possessore p
    LEFT JOIN partita_possessore pp ON p.id = pp.possessore_id
    WHERE 
        p.nome_completo ILIKE '%' || p_query || '%' OR
        p.cognome_nome ILIKE '%' || p_query || '%' OR
        p.paternita ILIKE '%' || p_query || '%'
    GROUP BY p.id, p.nome_completo, p.comune_nome
    ORDER BY num_partite DESC;
END;
$$ LANGUAGE plpgsql;