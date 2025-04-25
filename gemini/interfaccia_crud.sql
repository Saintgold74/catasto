\echo '\nINTERFACCIA SEMPLICE PER CATASTO STORICO\n'
\echo '==========================================='

-- Imposta lo schema corretto
SET search_path TO catasto;

-- Crea una funzione per generare il menù
CREATE OR REPLACE FUNCTION show_menu() RETURNS void AS $$
BEGIN
    RAISE NOTICE '
    INTERFACCIA CATASTO STORICO
    =========================
    1. Visualizza comuni
    2. Visualizza partite
    3. Visualizza possessori
    4. Visualizza immobili
    5. Inserisci nuovo possessore
    6. Inserisci nuova partita
    7. Inserisci nuovo immobile
    8. Genera certificato proprietà
    9. Ricerca possessori
    10. Ricerca immobili
    11. Aggiorna un possessore
    12. Aggiorna un immobile
    13. Elimina una consultazione
    14. Registra variazione proprietà
    0. Esci
    ';
END;
$$ LANGUAGE plpgsql;

-- Funzione principale del menù
CREATE OR REPLACE FUNCTION run_menu(p_choice INTEGER DEFAULT 1) RETURNS INTEGER AS $$
DECLARE
    v_id INTEGER;
    v_nome VARCHAR(100);
    v_comune VARCHAR(100);
    v_paternita VARCHAR(255);
    v_numero_partita INTEGER;
    v_tipo VARCHAR(50);
    v_data DATE;
    v_possessore_id INTEGER;
    v_partita_id INTEGER;
    v_localita_id INTEGER;
    v_natura VARCHAR(100);
    v_classificazione VARCHAR(100);
    v_cognome_nome VARCHAR(255);
    v_attivo BOOLEAN;
    v_query TEXT;
    v_consultazione_id INTEGER;
    v_partita_origine_id INTEGER;
    v_partita_dest_id INTEGER;
    v_tipo_variazione VARCHAR(50);
    v_data_variazione DATE;
    v_numero_riferimento VARCHAR(50);
    v_nominativo TEXT;
    v_array_possessori INTEGER[];
BEGIN
    PERFORM show_menu();
    
    RAISE NOTICE 'Scelta attuale: %', p_choice;
    
    CASE p_choice
        WHEN 0 THEN
            RAISE NOTICE 'Uscita...';
            RETURN 0;
        
        WHEN 1 THEN  -- Visualizza comuni
            RAISE NOTICE 'ELENCO COMUNI:';
            RAISE NOTICE '--------------';
            FOR v_comune IN SELECT nome FROM comune ORDER BY nome LOOP
                RAISE NOTICE '%', v_comune;
            END LOOP;
            
        WHEN 2 THEN  -- Visualizza partite
            RAISE NOTICE 'ELENCO PARTITE (limitato a 10):';
            RAISE NOTICE '--------------------------';
            FOR v_query IN 
                SELECT 'N. ' || numero_partita || ' - ' || comune_nome || 
                       ' (Stato: ' || stato || ', ID: ' || id || ')'
                FROM partita
                ORDER BY comune_nome, numero_partita
                LIMIT 10
            LOOP
                RAISE NOTICE '%', v_query;
            END LOOP;
            
        WHEN 3 THEN  -- Visualizza possessori
            RAISE NOTICE 'ELENCO POSSESSORI (limitato a 10):';
            RAISE NOTICE '--------------------------------';
            FOR v_query IN 
                SELECT 'ID: ' || id || ' - ' || nome_completo || ' (' || comune_nome || ')'
                FROM possessore
                ORDER BY comune_nome, nome_completo
                LIMIT 10
            LOOP
                RAISE NOTICE '%', v_query;
            END LOOP;
            
        WHEN 4 THEN  -- Visualizza immobili
            RAISE NOTICE 'ELENCO IMMOBILI (limitato a 10):';
            RAISE NOTICE '--------------------------------';
            FOR v_query IN 
                SELECT 'ID: ' || i.id || ' - ' || i.natura || 
                       ' in ' || l.nome || 
                       ' (Partita: ' || p.numero_partita || 
                       ', Comune: ' || p.comune_nome || ')'
                FROM immobile i
                JOIN localita l ON i.localita_id = l.id
                JOIN partita p ON i.partita_id = p.id
                ORDER BY p.comune_nome, p.numero_partita
                LIMIT 10
            LOOP
                RAISE NOTICE '%', v_query;
            END LOOP;
            
        WHEN 5 THEN  -- Inserisci nuovo possessore
            RAISE NOTICE 'INSERIMENTO NUOVO POSSESSORE:';
            RAISE NOTICE '--------------------------';
            
            -- In una interfaccia reale, qui chiederesti input all'utente
            -- Per esempio:
            v_comune := 'Carcare';
            v_cognome_nome := 'Rossi Giovanni';
            v_paternita := 'fu Pietro';
            v_nome := v_cognome_nome || ' ' || v_paternita;
            
            RAISE NOTICE 'Inserimento di: % in %', v_nome, v_comune;
            
            CALL inserisci_possessore(v_comune, v_cognome_nome, v_paternita, v_nome, true);
            
            RAISE NOTICE 'Possessore inserito con successo!';
            
        WHEN 6 THEN  -- Inserisci nuova partita
            RAISE NOTICE 'INSERIMENTO NUOVA PARTITA:';
            RAISE NOTICE '------------------------';
            
            -- Esempio di inserimento predefinito
            v_comune := 'Carcare';
            v_numero_partita := 999;  -- Esempio
            v_tipo := 'principale';
            v_data := CURRENT_DATE;
            
            -- Cerca un possessore esistente per collegarlo
            SELECT id INTO v_possessore_id 
            FROM possessore 
            WHERE comune_nome = v_comune 
            LIMIT 1;
            
            v_array_possessori := ARRAY[v_possessore_id];
            
            RAISE NOTICE 'Inserimento partita n. % in % per possessore ID: %', 
                        v_numero_partita, v_comune, v_possessore_id;
            
            CALL inserisci_partita_con_possessori(
                v_comune, v_numero_partita, v_tipo, v_data, v_array_possessori
            );
            
            RAISE NOTICE 'Partita inserita con successo!';
            
        WHEN 7 THEN  -- Inserisci nuovo immobile
            RAISE NOTICE 'INSERIMENTO NUOVO IMMOBILE:';
            RAISE NOTICE '---------------------------';
            
            -- Trova una partita attiva
            SELECT id INTO v_partita_id 
            FROM partita 
            WHERE stato = 'attiva' 
            LIMIT 1;
            
            -- Trova una località
            SELECT id INTO v_localita_id 
            FROM localita 
            LIMIT 1;
            
            -- Dati di esempio
            v_natura := 'Casa di abitazione';
            v_classificazione := 'Abitazione civile';
            
            RAISE NOTICE 'Inserimento immobile: % per partita ID: %', 
                        v_natura, v_partita_id;
            
            INSERT INTO immobile (
                partita_id, localita_id, natura, 
                numero_piani, numero_vani, consistenza, classificazione
            )
            VALUES (
                v_partita_id, v_localita_id, v_natura, 
                2, 5, '120 mq', v_classificazione
            );
            
            RAISE NOTICE 'Immobile inserito con successo!';
            
        WHEN 8 THEN  -- Genera certificato proprietà
            RAISE NOTICE 'GENERAZIONE CERTIFICATO PROPRIETÀ:';
            RAISE NOTICE '----------------------------------';
            
            -- Trova una partita
            SELECT id INTO v_partita_id 
            FROM partita 
            LIMIT 1;
            
            RAISE NOTICE 'Generazione certificato per partita ID: %', v_partita_id;
            
            RAISE NOTICE E'\n%', genera_certificato_proprieta(v_partita_id);
            
        WHEN 9 THEN  -- Ricerca possessori
            RAISE NOTICE 'RICERCA POSSESSORI:';
            RAISE NOTICE '------------------';
            
            -- Esempio di ricerca
            v_nome := 'Fossati';  -- Esempio di cognome da cercare
            
            RAISE NOTICE 'Ricerca possessori con nome contenente: %', v_nome;
            
            FOR v_query IN 
                SELECT 'ID: ' || id || ' - ' || nome_completo || 
                       ' (' || comune_nome || ') - Partite: ' || num_partite
                FROM cerca_possessori(v_nome)
            LOOP
                RAISE NOTICE '%', v_query;
            END LOOP;
            
        WHEN 10 THEN  -- Ricerca immobili
            RAISE NOTICE 'RICERCA IMMOBILI:';
            RAISE NOTICE '----------------';
            
            -- Parametri di esempio
            v_comune := 'Carcare';
            v_natura := 'Casa';
            
            RAISE NOTICE 'Ricerca immobili in % con natura contenente: %', v_comune, v_natura;
            
            FOR v_query IN 
                SELECT 'ID: ' || id || ' - ' || natura || 
                       ' in ' || localita_nome || 
                       ' (Partita: ' || numero_partita || ')'
                FROM cerca_immobili(NULL, v_comune, NULL, v_natura, NULL)
            LOOP
                RAISE NOTICE '%', v_query;
            END LOOP;
            
        WHEN 11 THEN  -- Aggiorna un possessore
            RAISE NOTICE 'AGGIORNAMENTO POSSESSORE:';
            RAISE NOTICE '------------------------';
            
            -- Trova un possessore
            SELECT id INTO v_possessore_id 
            FROM possessore 
            LIMIT 1;
            
            -- Dati di esempio
            v_attivo := false;
            
            RAISE NOTICE 'Aggiornamento possessore ID %: stato attivo = %', v_possessore_id, v_attivo;
            
            UPDATE possessore 
            SET attivo = v_attivo 
            WHERE id = v_possessore_id;
            
            RAISE NOTICE 'Possessore aggiornato con successo!';
            
        WHEN 12 THEN  -- Aggiorna un immobile
            RAISE NOTICE 'AGGIORNAMENTO IMMOBILE:';
            RAISE NOTICE '----------------------';
            
            -- Trova un immobile
            SELECT id INTO v_id 
            FROM immobile 
            LIMIT 1;
            
            -- Dati di esempio
            v_natura := 'Casa ristrutturata';
            
            RAISE NOTICE 'Aggiornamento immobile ID %: natura = %', v_id, v_natura;
            
            CALL aggiorna_immobile(v_id, v_natura, NULL, NULL, NULL, NULL, NULL);
            
            RAISE NOTICE 'Immobile aggiornato con successo!';
            
        WHEN 13 THEN  -- Elimina una consultazione
            RAISE NOTICE 'ELIMINAZIONE CONSULTAZIONE:';
            RAISE NOTICE '---------------------------';
            
            -- Trova una consultazione
            SELECT id INTO v_consultazione_id 
            FROM consultazione 
            LIMIT 1;
            
            IF v_consultazione_id IS NOT NULL THEN
                RAISE NOTICE 'Eliminazione consultazione ID: %', v_consultazione_id;
                
                CALL elimina_consultazione(v_consultazione_id);
                
                RAISE NOTICE 'Consultazione eliminata con successo!';
            ELSE
                RAISE NOTICE 'Nessuna consultazione trovata!';
            END IF;
            
        WHEN 14 THEN  -- Registra variazione proprietà
            RAISE NOTICE 'REGISTRAZIONE VARIAZIONE:';
            RAISE NOTICE '------------------------';
            
            -- Trova una partita origine attiva
            SELECT id INTO v_partita_origine_id 
            FROM partita 
            WHERE stato = 'attiva' 
            LIMIT 1;
            
            -- Trova una partita destinazione attiva ma diversa
            SELECT id INTO v_partita_dest_id 
            FROM partita 
            WHERE stato = 'attiva' AND id != v_partita_origine_id
            LIMIT 1;
            
            IF v_partita_origine_id IS NULL OR v_partita_dest_id IS NULL THEN
                RAISE NOTICE 'Non ci sono abbastanza partite attive per una variazione!';
            ELSE
                -- Dati di esempio
                v_tipo_variazione := 'Vendita';
                v_data_variazione := CURRENT_DATE;
                v_numero_riferimento := 'TEST-001';
                v_nominativo := 'Test variazione';
                
                RAISE NOTICE 'Registrazione variazione da partita % a %', 
                            v_partita_origine_id, v_partita_dest_id;
                
                CALL registra_variazione(
                    v_partita_origine_id, v_partita_dest_id, v_tipo_variazione,
                    v_data_variazione, v_numero_riferimento, v_nominativo,
                    'Vendita', v_data_variazione, 'Notaio Test', 'Rep123', 'Note di test'
                );
                
                RAISE NOTICE 'Variazione registrata con successo!';
            END IF;
            
        ELSE
            RAISE NOTICE 'Scelta non valida!';
    END CASE;
    
    RETURN 1;  -- Ritorna 1 per continuare il ciclo
END;
$$ LANGUAGE plpgsql;

-- Sequenza di comandi per testare varie funzionalità
SELECT run_menu(1);  -- Visualizza comuni
SELECT run_menu(2);  -- Visualizza partite
SELECT run_menu(3);  -- Visualizza possessori
SELECT run_menu(5);  -- Inserisci nuovo possessore
SELECT run_menu(9);  -- Ricerca possessori
SELECT run_menu(8);  -- Genera certificato proprietà
SELECT run_menu(0);  -- Esci

-- Rimuove le funzioni temporanee
DROP FUNCTION IF EXISTS run_menu(INTEGER);
DROP FUNCTION IF EXISTS show_menu();

\echo '\nTest completato!\n'