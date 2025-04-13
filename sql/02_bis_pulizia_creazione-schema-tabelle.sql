-- Imposta lo schema
SET search_path TO catasto;

-- Elimina tutte le tabelle in ordine inverso rispetto alle dipendenze
DROP TABLE IF EXISTS backup_registro CASCADE;
DROP TABLE IF EXISTS consultazione CASCADE;
DROP TABLE IF EXISTS contratto CASCADE;
DROP TABLE IF EXISTS variazione CASCADE;
DROP TABLE IF EXISTS partita_relazione CASCADE;
DROP TABLE IF EXISTS immobile CASCADE;
DROP TABLE IF EXISTS localita CASCADE;
DROP TABLE IF EXISTS partita_possessore CASCADE;
DROP TABLE IF EXISTS possessore CASCADE;
DROP TABLE IF EXISTS partita CASCADE;
DROP TABLE IF EXISTS registro_matricole CASCADE;
DROP TABLE IF EXISTS registro_partite CASCADE;
DROP TABLE IF EXISTS comune CASCADE;
-- Aggiungi altre tabelle se necessario