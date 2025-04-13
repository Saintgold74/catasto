-- Modifiche possibili dopo la creazione
ALTER DATABASE catasto_storico 
  OWNER TO postgres;

ALTER DATABASE catasto_storico 
  CONNECTION LIMIT = -1;

COMMENT ON DATABASE catasto_storico IS 'Database per la gestione del catasto storico degli anni ''50';

-- L'encoding non può essere modificato dopo la creazione del database
-- ALTER DATABASE catasto_storico SET ENCODING = 'UTF8'; -- Non funzionerà

COMMENT ON DATABASE catasto_storico IS 'Database per la gestione del catasto storico degli anni ''50';