-- Creazione del database
CREATE DATABASE catasto_storico
  WITH OWNER = postgres
  ENCODING = 'UTF8'
  LC_COLLATE = 'Italian_Italy.1252'
  LC_CTYPE = 'Italian_Italy.1252'
  template=template0
  TABLESPACE = pg_default
  CONNECTION LIMIT = -1;

COMMENT ON DATABASE catasto_storico IS 'Database per la gestione del catasto storico degli anni ''50';