# core/db_manager.py
import logging
import os
import psycopg2
from psycopg2 import pool, extras
from typing import Optional, Any

# Import per SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session # Aggiunto Session per type hinting
from sqlalchemy.ext.declarative import declarative_base

# Importa la funzione corretta per caricare la configurazione
from utils.config_loader import load_db_config # MODIFICATO QUI

logger = logging.getLogger("CatastoDBLogger") # Logger per questo modulo

# --- Configurazione Iniziale Percorsi e Caricamento Configurazione ---
# Determina il percorso base del progetto (la cartella 'acs')
# Questo assume che db_manager.py sia in acs/core/
try:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_FILE_PATH = os.path.join(PROJECT_ROOT, 'config.ini')
    db_config = load_db_config(file_path=CONFIG_FILE_PATH) # CHIAMATA CORRETTA
except (FileNotFoundError, ValueError, TypeError) as e:
    # TypeError aggiunto nel caso load_db_config sollevi problemi con i parametri non trovati
    logger.critical(f"Errore fatale nel caricamento della configurazione del database: {e}", exc_info=True)
    # In un'applicazione reale, potresti voler uscire o sollevare un'eccezione personalizzata
    # che l'applicazione principale può gestire per terminare in modo pulito.
    raise RuntimeError(f"Impossibile caricare la configurazione del database da '{CONFIG_FILE_PATH}': {e}") from e
except Exception as e:
    logger.critical(f"Errore imprevisto nel caricamento della configurazione del database: {e}", exc_info=True)
    raise RuntimeError(f"Errore imprevisto durante il caricamento della configurazione: {e}") from e


# --- Setup SQLAlchemy ---
DB_USER = db_config.get('user')
DB_PASSWORD = db_config.get('password')
DB_HOST = db_config.get('host', 'localhost')
DB_PORT = db_config.get('port', '5432') # load_db_config ora dovrebbe restituire port come int
DB_NAME = db_config.get('dbname')
DB_SCHEMA = db_config.get('schema', 'catasto') # Default a 'catasto' se non specificato

if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
    msg = "Parametri database mancanti (user, password, host, port, dbname) in config.ini."
    logger.critical(msg)
    raise ValueError(msg)

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Opzioni di connessione per SQLAlchemy per impostare search_path e altre opzioni se necessario
connect_args = {}
if DB_SCHEMA:
    connect_args["options"] = f"-csearch_path={DB_SCHEMA},public"
# Potresti aggiungere altre opzioni qui, ad esempio:
# connect_args["connect_timeout"] = 10

try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Imposta a True per vedere le query SQL generate durante lo sviluppo
        connect_args=connect_args,
        pool_pre_ping=True # Verifica la connessione prima di usarla dal pool
        # Altre opzioni utili per il pool:
        # pool_size=5, # Numero di connessioni da tenere nel pool
        # max_overflow=10, # Numero massimo di connessioni extra oltre pool_size
        # pool_recycle=3600 # Ricicla connessioni dopo 1 ora (3600 secondi)
    )
except Exception as e:
    logger.critical(f"Errore durante la creazione dell'engine SQLAlchemy: {e}", exc_info=True)
    raise RuntimeError(f"Impossibile creare l'engine SQLAlchemy: {e}") from e


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Funzione di utilità per ottenere una sessione DB (dependency injector pattern)
def get_db() -> Session:
    """
    Fornisce una sessione SQLAlchemy.
    Da usare con un context manager implicito (es. FastAPI Depends) o esplicito (try/finally).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Funzione per creare le tabelle definite nei modelli SQLAlchemy (se non usi Alembic)
def create_all_tables():
    """
    Crea nel database tutte le tabelle definite come sottoclassi di Base.
    Questa funzione dovrebbe essere chiamata con cautela, idealmente solo una volta
    per l'impostazione iniziale o in un ambiente di sviluppo/test.
    Per modifiche allo schema (migrazioni) in produzione, usare Alembic.
    """
    logger.info("Tentativo di creare le tabelle SQLAlchemy definite nei modelli (se non esistono già)...")
    try:
        # Assicurati che tutti i moduli contenenti i modelli siano importati prima di chiamare create_all
        # Ad esempio, se i modelli sono in core.models:
        # from core import models # Questo potrebbe essere necessario se Base.metadata non è popolato
        Base.metadata.create_all(bind=engine)
        logger.info("Creazione/verifica tabelle SQLAlchemy completata.")
    except Exception as e:
        logger.error(f"Errore durante Base.metadata.create_all: {e}", exc_info=True)
        # In un'applicazione reale, questo potrebbe essere un errore fatale all'avvio
        # se le tabelle sono essenziali e non possono essere create.


# --- VECCHIA CLASSE DBManager (per compatibilità temporanea o parti non migrate) ---
# Man mano che migri i servizi a SQLAlchemy, l'uso diretto di questa classe dovrebbe diminuire.
# Potresti decidere di rimuoverla completamente una volta che la migrazione è completa.
class DatabaseManager:
    """
    Gestore legacy per connessioni dirette psycopg2.
    Da usare per le parti dell'applicazione non ancora migrate a SQLAlchemy.
    """
    _pool = None

    def __init__(self):
        self.logger = logging.getLogger("CatastoDBLogger.LegacyPsycopg2Manager")
        if not DatabaseManager._pool:
            try:
                # Assicurati che db_config sia stato caricato correttamente all'inizio del modulo
                DatabaseManager._pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10, # Adatta secondo necessità
                    user=db_config.get('user'),
                    password=db_config.get('password'),
                    host=db_config.get('host'),
                    port=db_config.get('port'), # Assicurati sia int
                    database=db_config.get('dbname')
                )
                self.logger.info("Pool di connessioni Psycopg2 (legacy) inizializzato.")
            except (psycopg2.Error, KeyError) as e:
                self.logger.critical(f"Errore inizializzazione pool di connessioni Psycopg2 (legacy): {e}", exc_info=True)
                DatabaseManager._pool = None # Assicura che sia None in caso di fallimento
                raise RuntimeError(f"Impossibile inizializzare il pool di connessioni legacy: {e}") from e
        
        self.schema = db_config.get('schema', 'catasto') # Per SET search_path

    def _get_connection(self):
        if not DatabaseManager._pool:
            self.logger.error("Tentativo di ottenere una connessione dal pool Psycopg2 (legacy) non inizializzato.")
            raise RuntimeError("Pool di connessioni Psycopg2 (legacy) non disponibile.")
        try:
            conn = DatabaseManager._pool.getconn()
            if conn:
                # Imposta search_path per questa connessione
                with conn.cursor() as cur:
                    cur.execute(f"SET search_path TO {self.schema}, public;")
                conn.commit() # Commit per SET search_path
            return conn
        except psycopg2.Error as e:
            self.logger.error(f"Errore nell'ottenere una connessione Psycopg2 (legacy) dal pool: {e}", exc_info=True)
            raise

    def _put_connection(self, conn):
        if DatabaseManager._pool and conn:
            DatabaseManager._pool.putconn(conn)

    def execute_query(self, query: str, params: Optional[tuple] = None, fetch_one: bool = False, fetch_all: bool = False, is_ddl: bool = False):
        """Esegue una query SQL usando il pool di connessioni psycopg2 legacy."""
        conn = None
        try:
            conn = self._get_connection()
            # Usa RealDictCursor per ottenere risultati come dizionari
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                self.logger.debug(f"Esecuzione query legacy: {query} con parametri: {params}")
                cur.execute(query, params)
                
                if is_ddl or query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                    conn.commit()
                    # Per INSERT RETURNING id, o UPDATE/DELETE che potrebbero non modificare righe
                    if fetch_one and cur.description: # Se c'è qualcosa da leggere (es. RETURNING)
                        return cur.fetchone()
                    # Per DELETE/UPDATE senza RETURNING, rowcount potrebbe essere interessante
                    return cur.rowcount # Restituisce il numero di righe affette

                if fetch_one:
                    return cur.fetchone()
                if fetch_all:
                    return cur.fetchall()
                # Se nessuna opzione di fetch è True, e non è un'operazione di modifica,
                # potrebbe essere un'operazione che non restituisce dati (es. SET, o una stored procedure senza output).
                # O semplicemente un errore logico del chiamante. Per ora, ritorniamo None.
                return None
        except psycopg2.Error as e:
            if conn: conn.rollback() # Annulla la transazione in caso di errore DB
            self.logger.error(f"Errore Database (legacy) durante l'esecuzione della query: {query} ... Errore: {e}", exc_info=True)
            # Potresti voler rilanciare un'eccezione personalizzata
            raise # Rilancia l'eccezione psycopg2 originale per ora
        except Exception as e:
            if conn: conn.rollback()
            self.logger.error(f"Errore generico (legacy) durante l'esecuzione della query: {query} ... Errore: {e}", exc_info=True)
            raise
        finally:
            if conn:
                self._put_connection(conn)

    def close_all_connections(self):
        """Chiude tutte le connessioni nel pool legacy."""
        if DatabaseManager._pool:
            self.logger.info("Chiusura di tutte le connessioni nel pool Psycopg2 (legacy)...")
            DatabaseManager._pool.closeall()
            DatabaseManager._pool = None # Resetta il pool
            self.logger.info("Pool Psycopg2 (legacy) chiuso.")

    # Metodi commit e rollback espliciti (per la gestione delle transazioni legacy se necessario)
    # Questi metodi richiederebbero che la connessione sia gestita esternamente o passata,
    # il che complica l'uso del pool. È meglio che execute_query gestisca il commit per singole operazioni.
    # Per transazioni multi-statement con la vecchia logica, la gestione diventa più complessa.

    # def commit(self, conn): # Esempio se la connessione fosse gestita esternamente
    #     if conn: conn.commit()
    # def rollback(self, conn):
    #     if conn: conn.rollback()