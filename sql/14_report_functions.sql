-- Imposta lo schema
SET search_path TO catasto;

-- ========================================================================
-- Funzione: genera_report_genealogico
-- Genera un report genealogico di una partita, mostrando predecessori e successori
-- ========================================================================
CREATE OR REPLACE FUNCTION genera_report_genealogico(p_partita_id INTEGER)
RETURNS TEXT AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_report TEXT;
    v_record RECORD;
    v_predecessori_trovati BOOLEAN := FALSE;
    v_successori_trovati BOOLEAN := FALSE;
    v_possessori TEXT := '';
BEGIN
    -- Recupera i dati della partita
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    
    IF NOT FOUND THEN
        RETURN 'Partita con ID ' || p_partita_id || ' non trovata';
    END IF;
    
    -- Intestazione report
    v_report := '============================================================' || E'\n';
    v_report := v_report || '              REPORT GENEALOGICO DELLA PROPRIETA' || E'\n';
    v_report := v_report || '                   CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';
    
    -- Dati generali della partita
    v_report := v_report || 'COMUNE: ' || v_partita.comune_nome || E'\n';
    v_report := v_report || 'PARTITA N.: ' || v_partita.numero_partita || E'\n';
    v_report := v_report || 'TIPO: ' || v_partita.tipo || E'\n';
    v_report := v_report || 'DATA IMPIANTO: ' || v_partita.data_impianto || E'\n';
    v_report := v_report || 'STATO: ' || v_partita.stato || E'\n';
    IF v_partita.data_chiusura IS NOT NULL THEN
        v_report := v_report || 'DATA CHIUSURA: ' || v_partita.data_chiusura || E'\n';
    END IF;
    v_report := v_report || E'\n';
    
    -- Possessori della partita
    v_report := v_report || '-------------------- INTESTATARI --------------------' || E'\n';
    FOR v_record IN 
        SELECT 
            pos.nome_completo, 
            pp.titolo, 
            pp.quota
        FROM partita_possessore pp
        JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE pp.partita_id = p_partita_id
    LOOP
        v_report := v_report || '- ' || v_record.nome_completo;
        IF v_record.titolo = 'comproprieta' AND v_record.quota IS NOT NULL THEN
            v_report := v_report || ' (quota: ' || v_record.quota || ')';
        END IF;
        v_report := v_report || E'\n';
    END LOOP;
    v_report := v_report || E'\n';
    
    -- Predecessori (da dove proviene la partita)
    v_report := v_report || '-------------------- PREDECESSORI --------------------' || E'\n';
    
    -- Verifica se proviene da un'altra partita
    IF v_partita.numero_provenienza IS NOT NULL THEN
        FOR v_record IN 
            SELECT 
                p.id AS partita_id,
                p.comune_nome,
                p.numero_partita,
                p.data_impianto,
                p.data_chiusura,
                STRING_AGG(pos.nome_completo, ', ') AS possessori,
                v.tipo AS tipo_variazione,
                v.data_variazione
            FROM partita p
            JOIN variazione v ON p.id = v.partita_origine_id
            LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
            LEFT JOIN possessore pos ON pp.possessore_id = pos.id
            WHERE v.partita_destinazione_id = p_partita_id
            GROUP BY p.id, p.comune_nome, p.numero_partita, p.data_impianto, p.data_chiusura, v.tipo, v.data_variazione
        LOOP
            v_predecessori_trovati := TRUE;
            v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
            v_report := v_report || '  Periodo: ' || v_record.data_impianto || ' - ';
            IF v_record.data_chiusura IS NOT NULL THEN
                v_report := v_report || v_record.data_chiusura;
            ELSE
                v_report := v_report || 'attiva';
            END IF;
            v_report := v_report || E'\n';
            v_report := v_report || '  Intestatari: ' || v_record.possessori || E'\n';
            v_report := v_report || '  Variazione: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione || E'\n';
            v_report := v_report || E'\n';
        END LOOP;
    END IF;
    
    IF NOT v_predecessori_trovati THEN
        v_report := v_report || 'Nessun predecessore trovato. Partita originale.' || E'\n\n';
    END IF;
    
    -- Successori (dove è confluita la partita)
    v_report := v_report || '-------------------- SUCCESSORI --------------------' || E'\n';
    
    FOR v_record IN 
        SELECT 
            p.id AS partita_id,
            p.comune_nome,
            p.numero_partita,
            p.data_impianto,
            p.data_chiusura,
            STRING_AGG(pos.nome_completo, ', ') AS possessori,
            v.tipo AS tipo_variazione,
            v.data_variazione
        FROM partita p
        JOIN variazione v ON p.id = v.partita_destinazione_id
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE v.partita_origine_id = p_partita_id
        GROUP BY p.id, p.comune_nome, p.numero_partita, p.data_impianto, p.data_chiusura, v.tipo, v.data_variazione
    LOOP
        v_successori_trovati := TRUE;
        v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
        v_report := v_report || '  Periodo: ' || v_record.data_impianto || ' - ';
        IF v_record.data_chiusura IS NOT NULL THEN
            v_report := v_report || v_record.data_chiusura;
        ELSE
            v_report := v_report || 'attiva';
        END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Intestatari: ' || v_record.possessori || E'\n';
        v_report := v_report || '  Variazione: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione || E'\n';
        v_report := v_report || E'\n';
    END LOOP;
    
    IF NOT v_successori_trovati THEN
        IF v_partita.stato = 'attiva' THEN
            v_report := v_report || 'Nessun successore trovato. La partita e'''' ancora attiva.' || E'\n\n';
        ELSE
            v_report := v_report || 'Nessun successore trovato nonostante la partita sia chiusa.' || E'\n\n';
        END IF;
    END IF;
    
    -- Piè di pagina report
    v_report := v_report || '============================================================' || E'\n';
    v_report := v_report || 'Report generato il: ' || CURRENT_DATE || E'\n';
    v_report := v_report || '============================================================' || E'\n';
    
    RETURN v_report;
END;
$$ LANGUAGE plpgsql;

-- ========================================================================
-- Funzione: genera_certificato_proprieta
-- Genera un certificato di proprieta immobiliare
-- ========================================================================
CREATE OR REPLACE FUNCTION genera_certificato_proprieta(p_partita_id INTEGER)
RETURNS TEXT AS $$
DECLARE
    v_partita partita%ROWTYPE;
    v_certificato TEXT;
    v_possessori TEXT;
    v_immobili TEXT;
    v_immobile RECORD;
    v_record RECORD;
BEGIN
    -- Recupera i dati della partita
    SELECT * INTO v_partita FROM partita WHERE id = p_partita_id;
    
    IF NOT FOUND THEN
        RETURN 'Partita con ID ' || p_partita_id || ' non trovata';
    END IF;
    
    -- Intestazione certificato
    v_certificato := '============================================================' || E'\n';
    v_certificato := v_certificato || '                CERTIFICATO DI PROPRIETA IMMOBILIARE' || E'\n';
    v_certificato := v_certificato || '                     CATASTO STORICO ANNI ''50' || E'\n';
    v_certificato := v_certificato || '============================================================' || E'\n\n';
    
    -- Dati generali della partita
    v_certificato := v_certificato || 'COMUNE: ' || v_partita.comune_nome || E'\n';
    v_certificato := v_certificato || 'PARTITA N.: ' || v_partita.numero_partita || E'\n';
    v_certificato := v_certificato || 'TIPO: ' || v_partita.tipo || E'\n';
    v_certificato := v_certificato || 'DATA IMPIANTO: ' || v_partita.data_impianto || E'\n';
    v_certificato := v_certificato || 'STATO: ' || v_partita.stato || E'\n';
    IF v_partita.data_chiusura IS NOT NULL THEN
        v_certificato := v_certificato || 'DATA CHIUSURA: ' || v_partita.data_chiusura || E'\n';
    END IF;
    IF v_partita.numero_provenienza IS NOT NULL THEN
        v_certificato := v_certificato || 'PROVENIENZA: Partita n. ' || v_partita.numero_provenienza || E'\n';
    END IF;
    v_certificato := v_certificato || E'\n';
    
    -- Possessori della partita
    v_certificato := v_certificato || '-------------------- INTESTATARI --------------------' || E'\n';
    FOR v_record IN 
        SELECT 
            pos.nome_completo, 
            pp.titolo, 
            pp.quota
        FROM partita_possessore pp
        JOIN possessore pos ON pp.possessore_id = pos.id
        WHERE pp.partita_id = p_partita_id
        ORDER BY pos.nome_completo
    LOOP
        v_certificato := v_certificato || '- ' || v_record.nome_completo;
        IF v_record.titolo = 'comproprieta' AND v_record.quota IS NOT NULL THEN
            v_certificato := v_certificato || ' (quota: ' || v_record.quota || ')';
        END IF;
        v_certificato := v_certificato || E'\n';
    END LOOP;
    v_certificato := v_certificato || E'\n';
    
    -- Immobili della partita
    v_certificato := v_certificato || '-------------------- IMMOBILI --------------------' || E'\n';
    FOR v_immobile IN 
        SELECT 
            i.id,
            i.natura,
            i.numero_piani,
            i.numero_vani,
            i.consistenza,
            i.classificazione,
            l.tipo AS tipo_localita,
            l.nome AS nome_localita,
            l.civico
        FROM immobile i
        JOIN localita l ON i.localita_id = l.id
        WHERE i.partita_id = p_partita_id
        ORDER BY l.nome, i.natura
    LOOP
        v_certificato := v_certificato || 'Immobile ID: ' || v_immobile.id || E'\n';
        v_certificato := v_certificato || '  Natura: ' || v_immobile.natura || E'\n';
        v_certificato := v_certificato || '  Localita: ' || v_immobile.nome_localita;
        IF v_immobile.civico IS NOT NULL THEN
            v_certificato := v_certificato || ', ' || v_immobile.civico;
        END IF;
        v_certificato := v_certificato || ' (' || v_immobile.tipo_localita || ')' || E'\n';
        
        IF v_immobile.numero_piani IS NOT NULL THEN
            v_certificato := v_certificato || '  Piani: ' || v_immobile.numero_piani || E'\n';
        END IF;
        IF v_immobile.numero_vani IS NOT NULL THEN
            v_certificato := v_certificato || '  Vani: ' || v_immobile.numero_vani || E'\n';
        END IF;
        IF v_immobile.consistenza IS NOT NULL THEN
            v_certificato := v_certificato || '  Consistenza: ' || v_immobile.consistenza || E'\n';
        END IF;
        IF v_immobile.classificazione IS NOT NULL THEN
            v_certificato := v_certificato || '  Classificazione: ' || v_immobile.classificazione || E'\n';
        END IF;
        
        v_certificato := v_certificato || E'\n';
    END LOOP;
    
    -- Verificare eventuali variazioni
    v_certificato := v_certificato || '-------------------- VARIAZIONI --------------------' || E'\n';
    FOR v_record IN 
        SELECT 
            v.tipo,
            v.data_variazione,
            v.numero_riferimento,
            p2.numero_partita AS partita_destinazione_numero,
            p2.comune_nome AS partita_destinazione_comune,
            c.tipo AS tipo_contratto,
            c.data_contratto,
            c.notaio,
            c.repertorio
        FROM variazione v
        LEFT JOIN partita p2 ON v.partita_destinazione_id = p2.id
        LEFT JOIN contratto c ON v.id = c.variazione_id
        WHERE v.partita_origine_id = p_partita_id
        ORDER BY v.data_variazione DESC
    LOOP
        v_certificato := v_certificato || 'Variazione: ' || v_record.tipo || ' del ' || v_record.data_variazione || E'\n';
        IF v_record.partita_destinazione_numero IS NOT NULL THEN
            v_certificato := v_certificato || '  Nuova partita: ' || v_record.partita_destinazione_numero;
            IF v_record.partita_destinazione_comune != v_partita.comune_nome THEN
                v_certificato := v_certificato || ' (Comune: ' || v_record.partita_destinazione_comune || ')';
            END IF;
            v_certificato := v_certificato || E'\n';
        END IF;
        IF v_record.tipo_contratto IS NOT NULL THEN
            v_certificato := v_certificato || '  Contratto: ' || v_record.tipo_contratto || ' del ' || v_record.data_contratto || E'\n';
            IF v_record.notaio IS NOT NULL THEN
                v_certificato := v_certificato || '  Notaio: ' || v_record.notaio || E'\n';
            END IF;
            IF v_record.repertorio IS NOT NULL THEN
                v_certificato := v_certificato || '  Repertorio: ' || v_record.repertorio || E'\n';
            END IF;
        END IF;
        v_certificato := v_certificato || E'\n';
    END LOOP;
    
    -- Piè di pagina certificato
    v_certificato := v_certificato || '============================================================' || E'\n';
    v_certificato := v_certificato || 'Certificato generato il: ' || CURRENT_DATE || E'\n';
    v_certificato := v_certificato || 'Il presente certificato ha valore puramente storico e documentale.' || E'\n';
    v_certificato := v_certificato || '============================================================' || E'\n';
    
    RETURN v_certificato;
END;
$$ LANGUAGE plpgsql;

-- ========================================================================
-- Funzione: genera_report_possessore
-- Genera un report storico delle proprieta di un possessore
-- ========================================================================
CREATE OR REPLACE FUNCTION genera_report_possessore(p_possessore_id INTEGER)
RETURNS TEXT AS $$
DECLARE
    v_possessore possessore%ROWTYPE;
    v_report TEXT;
    v_record RECORD;
    v_immobile RECORD;
BEGIN
    -- Recupera i dati del possessore
    SELECT * INTO v_possessore FROM possessore WHERE id = p_possessore_id;
    
    IF NOT FOUND THEN
        RETURN 'Possessore con ID ' || p_possessore_id || ' non trovato';
    END IF;
    
    -- Intestazione report
    v_report := '============================================================' || E'\n';
    v_report := v_report || '              REPORT STORICO DEL POSSESSORE' || E'\n';
    v_report := v_report || '                CATASTO STORICO ANNI ''50' || E'\n';
    v_report := v_report || '============================================================' || E'\n\n';
    
    -- Dati generali del possessore
    v_report := v_report || 'POSSESSORE: ' || v_possessore.nome_completo || E'\n';
    IF v_possessore.paternita IS NOT NULL THEN
        v_report := v_report || 'PATERNITA: ' || v_possessore.paternita || E'\n';
    END IF;
    v_report := v_report || 'COMUNE: ' || v_possessore.comune_nome || E'\n';
    v_report := v_report || 'STATO: ' || CASE WHEN v_possessore.attivo THEN 'Attivo' ELSE 'Non attivo' END || E'\n\n';
    
    -- Elenco delle partite possedute (attuali e passate)
    v_report := v_report || '-------------------- PARTITE INTESTATE --------------------' || E'\n';
    
    FOR v_record IN 
        SELECT 
            p.id AS partita_id,
            p.comune_nome,
            p.numero_partita,
            p.tipo,
            p.data_impianto,
            p.data_chiusura,
            p.stato,
            pp.titolo,
            pp.quota,
            COUNT(i.id) AS num_immobili
        FROM partita p
        JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN immobile i ON p.id = i.partita_id
        WHERE pp.possessore_id = p_possessore_id
        GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.data_impianto, p.data_chiusura, p.stato, pp.titolo, pp.quota
        ORDER BY p.data_impianto DESC
    LOOP
        v_report := v_report || 'Partita n. ' || v_record.numero_partita || ' (' || v_record.comune_nome || ')' || E'\n';
        v_report := v_report || '  Tipo: ' || v_record.tipo || E'\n';
        v_report := v_report || '  Periodo: ' || v_record.data_impianto || ' - ';
        IF v_record.data_chiusura IS NOT NULL THEN
            v_report := v_report || v_record.data_chiusura;
        ELSE
            v_report := v_report || 'attiva';
        END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Stato: ' || v_record.stato || E'\n';
        v_report := v_report || '  Titolo: ' || v_record.titolo;
        IF v_record.quota IS NOT NULL THEN
            v_report := v_report || ' (quota: ' || v_record.quota || ')';
        END IF;
        v_report := v_report || E'\n';
        v_report := v_report || '  Immobili: ' || v_record.num_immobili || E'\n\n';
        
        -- Elenco degli immobili per questa partita
        FOR v_immobile IN 
            SELECT 
                i.natura,
                l.nome AS localita_nome,
                l.tipo AS tipo_localita,
                i.classificazione
            FROM immobile i
            JOIN localita l ON i.localita_id = l.id
            WHERE i.partita_id = v_record.partita_id
        LOOP
            v_report := v_report || '    - ' || v_immobile.natura || ' in ' || v_immobile.localita_nome;
            IF v_immobile.classificazione IS NOT NULL THEN
                v_report := v_report || ' (' || v_immobile.classificazione || ')';
            END IF;
            v_report := v_report || E'\n';
        END LOOP;
        v_report := v_report || E'\n';
    END LOOP;
    
    -- Storia delle variazioni che coinvolgono il possessore
    v_report := v_report || '-------------------- VARIAZIONI --------------------' || E'\n';
    
    FOR v_record IN 
        SELECT 
            v.tipo AS tipo_variazione,
            v.data_variazione,
            p_orig.comune_nome AS comune_origine,
            p_orig.numero_partita AS partita_origine,
            p_dest.comune_nome AS comune_destinazione,
            p_dest.numero_partita AS partita_destinazione,
            c.tipo AS tipo_contratto,
            c.data_contratto,
            c.notaio,
            c.repertorio
        FROM variazione v
        JOIN partita p_orig ON v.partita_origine_id = p_orig.id
        LEFT JOIN partita p_dest ON v.partita_destinazione_id = p_dest.id
        LEFT JOIN contratto c ON v.id = c.variazione_id
        WHERE EXISTS (
            SELECT 1 FROM partita_possessore pp
            WHERE pp.partita_id = p_orig.id AND pp.possessore_id = p_possessore_id
        ) OR EXISTS (
            SELECT 1 FROM partita_possessore pp
            WHERE pp.partita_id = p_dest.id AND pp.possessore_id = p_possessore_id
        )
        ORDER BY v.data_variazione DESC
    LOOP
        v_report := v_report || 'Variazione: ' || v_record.tipo_variazione || ' del ' || v_record.data_variazione || E'\n';
        v_report := v_report || '  Da: Partita n. ' || v_record.partita_origine || ' (' || v_record.comune_origine || ')' || E'\n';
        IF v_record.partita_destinazione IS NOT NULL THEN
            v_report := v_report || '  A: Partita n. ' || v_record.partita_destinazione || ' (' || v_record.comune_destinazione || ')' || E'\n';
        END IF;
        IF v_record.tipo_contratto IS NOT NULL THEN
            v_report := v_report || '  Contratto: ' || v_record.tipo_contratto || ' del ' || v_record.data_contratto || E'\n';
            IF v_record.notaio IS NOT NULL THEN
                v_report := v_report || '  Notaio: ' || v_record.notaio || E'\n';
            END IF;
            IF v_record.repertorio IS NOT NULL THEN
                v_report := v_report || '  Repertorio: ' || v_record.repertorio || E'\n';
            END IF;
        END IF;
        v_report := v_report || E'\n';
    END LOOP;
    
    -- Piè di pagina report
    v_report := v_report || '============================================================' || E'\n';
    v_report := v_report || 'Report generato il: ' || CURRENT_DATE || E'\n';
    v_report := v_report || '============================================================' || E'\n';
    
    RETURN v_report;
END;
$$ LANGUAGE plpgsql;
