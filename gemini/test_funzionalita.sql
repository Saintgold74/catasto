DO $$
DECLARE
    v_count INTEGER;
BEGIN
    RAISE NOTICE '🔍 Test: Verifica presenza vista v_partite_complete';
    SELECT COUNT(*) INTO v_count FROM pg_views 
    WHERE schemaname = 'catasto' AND viewname = 'v_partite_complete';
    IF v_count = 0 THEN
        RAISE EXCEPTION '❌ Vista v_partite_complete non trovata';
    END IF;

    RAISE NOTICE '✅ Vista v_partite_complete trovata';

    RAISE NOTICE '🔍 Test: Query su v_partite_complete restituisce righe';
    EXECUTE 'SELECT COUNT(*) FROM catasto.v_partite_complete' INTO v_count;
    IF v_count = 0 THEN
        RAISE WARNING '⚠️ Nessuna riga trovata in v_partite_complete';
    ELSE
        RAISE NOTICE '✅ v_partite_complete contiene % righe', v_count;
    END IF;

    RAISE NOTICE '🔍 Test: Funzione cerca_possessori';
    SELECT COUNT(*) INTO v_count FROM cerca_possessori('Fossati');
    IF v_count = 0 THEN
        RAISE WARNING '⚠️ Nessun risultato per cerca_possessori(''Fossati'')';
    ELSE
        RAISE NOTICE '✅ cerca_possessori restituisce % risultati', v_count;
    END IF;

    RAISE NOTICE '🔍 Test: Ricerca immobili per località contenente "Verdi"';
    EXECUTE $q$SELECT COUNT(*) FROM immobile i
             JOIN localita l ON i.localita_id = l.id
             WHERE l.nome ILIKE '%Verdi%'$q$ INTO v_count;
    IF v_count = 0 THEN
        RAISE WARNING '⚠️ Nessun immobile trovato per località "Verdi"';
    ELSE
        RAISE NOTICE '✅ Trovati % immobili in località "Verdi"', v_count;
    END IF;

    RAISE NOTICE '✅ Tutti i test completati con successo';
END;
$$;
