-- Menu per Catasto Storico
CREATE OR REPLACE FUNCTION catasto.menu_principale()
RETURNS void AS $$
DECLARE
    v_scelta INTEGER;
    v_partita_id INTEGER;
    v_possessore_id INTEGER;
    v_comune VARCHAR;
    v_problemi_trovati BOOLEAN;
BEGIN
    LOOP
        RAISE NOTICE '============================================================';
        RAISE NOTICE '                 SISTEMA CATASTO STORICO                   ';
        RAISE NOTICE '============================================================';
        RAISE NOTICE '';
        RAISE NOTICE '1) Visualizzare un certificato di proprietà';
        RAISE NOTICE '2) Generare report genealogico di una proprietà';
        RAISE NOTICE '3) Generare report storico di un possessore';
        RAISE NOTICE '4) Verificare integrità del database';
        RAISE NOTICE '5) Riparare problemi del database';
        RAISE NOTICE '6) Creare backup dei dati';
        RAISE NOTICE '0) Uscire';
        RAISE NOTICE '';
        RAISE NOTICE 'Inserire il numero dell''opzione desiderata:';
        
        -- In una implementazione reale, qui si dovrebbe leggere l'input dell'utente
        -- Ma in PL/pgSQL non è possibile farlo direttamente, quindi simuliamo
        v_scelta := 0;  -- Imposta un valore simulato, in un'app reale verrebbe dall'utente
        
        CASE v_scelta
            WHEN 1 THEN
                -- Simulazione di richiesta parametri
                v_partita_id := 1;  -- In un'app reale verrebbe inserito dall'utente
                RAISE NOTICE 'Certificato di proprietà:';
                RAISE NOTICE '%', genera_certificato_proprieta(v_partita_id);
                
            WHEN 2 THEN
                v_partita_id := 1;  -- In un'app reale verrebbe inserito dall'utente
                RAISE NOTICE 'Report genealogico:';
                RAISE NOTICE '%', genera_report_genealogico(v_partita_id);
                
            WHEN 3 THEN
                v_possessore_id := 1;  -- In un'app reale verrebbe inserito dall'utente
                RAISE NOTICE 'Report possessore:';
                RAISE NOTICE '%', genera_report_possessore(v_possessore_id);
                
            WHEN 4 THEN
                CALL verifica_integrita_database(v_problemi_trovati);
                
            WHEN 5 THEN
                CALL ripara_problemi_database(TRUE);
                
            WHEN 6 THEN
                CALL backup_logico_dati();
                
            WHEN 0 THEN
                RAISE NOTICE 'Uscita dal programma.';
                EXIT;
                
            ELSE
                RAISE NOTICE 'Opzione non valida. Riprova.';
        END CASE;
        
        -- Pausa (simulata)
        RAISE NOTICE 'Premi un tasto per continuare...';
    END LOOP;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;