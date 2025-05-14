# acs/core/db_sqlalchemy_setup.py

import os
import configparser
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import logging

# Configurazione del logger
logger = logging.getLogger(__name__) # Usiamo __name__ per il logger del modulo
# Idealmente, la configurazione base del logging (livello, formato, handler)
# verrebbe fatta nel punto di ingresso principale dell'applicazione (es. main_app.py)
# per evitare configurazioni multiple. Per ora, ci assicuriamo che il logger esista.

# --- Configurazione Iniziale Percorsi e Caricamento Configurazione ---

# Assumiamo che questo file (db_sqlalchemy_setup.py) sia in acs/core/
# Quindi PROJECT_ROOT è due livelli sopra.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE_PATH = os.path.join(PROJECT_ROOT, 'config.ini') # Percorso al file config.ini

def load_db_config(file_path=CONFIG_FILE_PATH) -> dict:
    """
    Carica la configurazione del database dal file specificato.
    """
    if not os.path.exists(file_path):
        msg = f"File di configurazione '{file_path}' non trovato."
        logger.critical(msg)
        raise FileNotFoundError(msg)
    
    parser = configparser.ConfigParser()
    parser.read(file_path)
    
    if 'database' not in parser:
        msg = "Sezione [database] mancante nel file di configurazione."
        logger.critical(msg)
        raise ValueError(msg)
    
    try:
        db_params = dict(parser['database'])
        # Assicura che la porta sia un intero, se presente
        if 'port' in db_params and db_params['port']:
            db_params['port'] = int(db_params['port'])
        else: # Default PostgreSQL port
            db_params['port'] = 5432
        
        # Valori di default per host e schema se non presenti
        if 'host' not in db_params or not db_params['host']:
            db_params['host'] = 'localhost'
        if 'schema' not in db_params or not db_params['schema']:
            db_params['schema'] = 'catasto' # Il suo schema di default
            
        logger.info(f"Configurazione database caricata da '{file_path}'.")
        return db_params
    except Exception as e:
        logger.critical(f"Errore durante il parsing dei parametri del database da '{file_path}': {e}", exc_info=True)
        raise ValueError(f"Errore parsing configurazione DB: {e}") from e

try:
    db_config = load_db_config()
except (FileNotFoundError, ValueError) as e_conf:
    # Questo errore è critico, l'applicazione non può partire senza config DB.
    # Verrà gestito nel main_app.py, qui lo logghiamo e rilanciamo per informazione.
    logger.critical(f"Errore irreversibile nel caricamento della configurazione del database: {e_conf}")
    raise

# --- Setup SQLAlchemy ---
DB_USER = db_config.get('user')
DB_PASSWORD = db_config.get('password')
DB_HOST = db_config.get('host')
DB_PORT = db_config.get('port')
DB_NAME = db_config.get('dbname')
DB_SCHEMA = db_config.get('schema')

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME, DB_SCHEMA]):
    missing_params = [k for k, v in {
        "user": DB_USER, "password": DB_PASSWORD, "host": DB_HOST,
        "port": DB_PORT, "dbname": DB_NAME, "schema": DB_SCHEMA
    }.items() if not v]
    msg = f"Parametri database mancanti in config.ini: {', '.join(missing_params)}."
    logger.critical(msg)
    raise ValueError(msg)

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Argomenti di connessione per impostare lo search_path
connect_args = {"options": f"-csearch_path={DB_SCHEMA},public"}

try:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        echo=False,  # Impostare a True per vedere le query SQL generate (utile in sviluppo)
        pool_pre_ping=True # Controlla la validità delle connessioni prima dell'uso
    )
    logger.info("Engine SQLAlchemy creato con successo.")
except Exception as e_engine:
    logger.critical(f"Errore durante la creazione dell'engine SQLAlchemy: {e_engine}", exc_info=True)
    raise RuntimeError(f"Impossibile creare l'engine SQLAlchemy: {e_engine}") from e_engine

# Creazione di una SessionLocal factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
logger.info("SessionLocal SQLAlchemy creata.")

# Base per le classi dei modelli ORM
Base = declarative_base()
logger.info("SQLAlchemy Base dichiarativa creata.")

# Dependency per ottenere la sessione del DB
def get_db():
    db = SessionLocal()
    try:
        logger.debug(f"Sessione DB {id(db)} aperta.")
        yield db
    finally:
        logger.debug(f"Sessione DB {id(db)} chiusa.")
        db.close()

# Funzione opzionale per creare tutte le tabelle (utile in sviluppo)
# Da chiamare con cautela, specialmente se si usa Alembic o script SQL per le migrazioni.
def create_database_tables():
    """
    Crea tutte le tabelle definite nei modelli ORM che ereditano da Base.
    ATTENZIONE: Usare con cautela in produzione o se si gestisce lo schema con script SQL/Alembic.
    """
    logger.info("Tentativo di creare le tabelle definite nei modelli SQLAlchemy (se non esistono)...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Creazione/verifica tabelle SQLAlchemy completata con successo.")
    except Exception as e_create_tables:
        logger.error(f"Errore durante Base.metadata.create_all: {e_create_tables}", exc_info=True)
        # Potrebbe essere utile rilanciare l'eccezione se questa operazione è considerata critica al momento della chiamata
        # raise

if __name__ == '__main__':
    # Piccolo test per verificare se il setup funziona
    # Questo verrà eseguito solo se si lancia direttamente db_sqlalchemy_setup.py
    print("Esecuzione test di db_sqlalchemy_setup.py...")
    try:
        print(f"PROJECT_ROOT: {PROJECT_ROOT}")
        print(f"CONFIG_FILE_PATH: {CONFIG_FILE_PATH}")
        
        # Verifica caricamento configurazione
        cfg = load_db_config()
        print("Configurazione caricata:")
        for key, value in cfg.items():
            # Non stampare la password nei log o output di produzione
            print(f"  {key}: {'******' if key == 'password' else value}")
        
        print(f"DATABASE_URL: postgresql+psycopg2://{cfg.get('user')}:******@{cfg.get('host')}:{cfg.get('port')}/{cfg.get('dbname')}")
        print(f"connect_args: {connect_args}")

        # Test connessione engine
        with engine.connect() as connection:
            print("Connessione all'engine SQLAlchemy riuscita!")
            # Test search_path
            result = connection.execute("SHOW search_path;")
            current_search_path = result.scalar_one()
            print(f"Search_path corrente nel DB: {current_search_path}")
            if DB_SCHEMA not in current_search_path:
                print(f"ATTENZIONE: Lo schema '{DB_SCHEMA}' potrebbe non essere nel search_path effettivo della connessione.")
        
        # Test SessionLocal
        test_session = next(get_db())
        print(f"Sessione DB di test creata: {test_session}")
        test_session.close()
        print("Sessione DB di test chiusa.")
        
        print("\nTest di db_sqlalchemy_setup.py completato con successo.")
        
    except Exception as e_test:
        print(f"\nERRORE durante il test di db_sqlalchemy_setup.py: {e_test}")
        logger.error(f"Errore nel blocco di test __main__: {e_test}", exc_info=True)