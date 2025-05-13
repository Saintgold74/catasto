-- File: 00_svuota_dati.sql
-- Oggetto: ELIMINA TUTTI I DATI DALLE TABELLE CATASTALI (MANTIENE STRUTTURA)
-- USO: Eseguire PRIMA di caricare nuovi set di dati.
-- ATTENZIONE: OPERAZIONE IRREVERSIBILE!

-- Connettiti al database catasto_storico prima di eseguire questo script

SET search_path TO catasto, public;

TRUNCATE TABLE
    comune,
    partita,
    possessore,
    localita,
    immobile,
    partita_possessore,
    variazione,
    contratto,
    consultazione,
    documento_storico,
    partita_documento,
    nome_storico,
    -- Includi/Escludi queste tabelle come necessario:
    audit_log,
    backup_log,
    access_log,
    utenti,
    sessioni
    -- periodo_storico -- Probabilmente da NON includere
RESTART IDENTITY CASCADE;

-- Messaggio opzionale alla fine
\echo '*** DATI DELLE TABELLE CATASTALI ELIMINATI CON SUCCESSO (STRUTTURA MANTENUTA) ***'