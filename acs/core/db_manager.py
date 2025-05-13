# core/db_manager.py
import psycopg2
from psycopg2.extras import DictCursor # Per accedere ai risultati come dizionari
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_COMMITTED 
# Importa quote_ident per gestire nomi di schema in modo sicuro
from psycopg2.extensions import quote_ident 
import logging
from typing import Optional, Any # Aggiungiamo Optional e Any (usato in execute_query)
# from datetime import datetime # Non sembra essere usato direttamente in questa classe refactored

class DatabaseManager:
    """
    Gestore di basso livello per la connessione e l'esecuzione di query
    sul database PostgreSQL.
    """
    def __init__(self, db_config: dict):
        """
        Inizializza il DatabaseManager.
        'db_config' è un dizionario con i parametri di connessione,
        potenzialmente includendo una chiave 'schema'.
        """
        # Crea una copia di db_config per non modificare l'originale
        self.connect_params = db_config.copy()
        
        # Estrai 'schema' dai parametri di connessione e rimuovilo, 
        # poiché non è un parametro diretto di psycopg2.connect().
        # Default a 'catasto' se 'schema' non è specificato in db_config.
        self.schema_to_set = self.connect_params.pop('schema', 'catasto') 
        
        self.conn = None
        # Usa il logger configurato centralmente da logger_setup.py
        self.logger = logging.getLogger("CatastoDBLogger") 
        # Per debug dettagliato delle query, puoi impostare il livello qui o globalmente
        # self.logger.setLevel(logging.DEBUG) 

    def connect(self) -> bool:
        """
        Stabilisce la connessione al database e imposta lo schema search_path.
        Restituisce True se la connessione ha successo, False altrimenti.
        """
        if self.conn and not self.conn.closed:
            self.logger.info("Connessione al database già attiva.")
            return True
        try:
            self.logger.info(f"Tentativo di connessione al database: {self.connect_params.get('dbname')}@{self.connect_params.get('host')}")
            
            # Usa self.connect_params che NON CONTIENE PIÙ 'schema'
            self.conn = psycopg2.connect(**self.connect_params)
            
            # Impostazione del livello di isolamento:
            # ISOLATION_LEVEL_READ_COMMITTED è un buon default per molte applicazioni,
            # richiede commit/rollback espliciti per le transazioni.
            # ISOLATION_LEVEL_AUTOCOMMIT fa sì che ogni istruzione venga commessa immediatamente.
            # Scegli quello più adatto al tuo flusso di lavoro.
            # Se i tuoi servizi gestiscono esplicitamente commit/rollback, READ_COMMITTED è preferibile.
            self.conn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
            # self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT) # Alternativa

            self.logger.info(f"Connessione al database '{self.connect_params.get('dbname')}' riuscita.")

            # Imposta lo search_path per la sessione corrente se uno schema è specificato
            if self.schema_to_set:
                with self.conn.cursor() as cur:
                    # Usa quote_ident per gestire in modo sicuro i nomi degli schemi
                    # che potrebbero contenere caratteri speciali o essere case-sensitive.
                    safe_schema_name = quote_ident(self.schema_to_set, self.conn)
                    cur.execute(f"SET search_path TO {safe_schema_name}, public;")
                self.logger.info(f"Search path impostato a: {self.schema_to_set}, public")
            
            return True
            
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore di connessione al database: {db_err}", exc_info=True)
            self.conn = None # Assicura che conn sia None se la connessione fallisce
            return False
        except Exception as e: # Cattura altre eccezioni impreviste
            self.logger.error(f"Errore generico non-DB durante la connessione: {e}", exc_info=True)
            self.conn = None
            return False

    def disconnect(self):
        """Chiude la connessione al database, se attiva."""
        if self.conn and not self.conn.closed:
            try:
                self.conn.close()
                self.logger.info("Disconnessione dal database riuscita.")
            except psycopg2.Error as db_err:
                self.logger.error(f"Errore durante la disconnessione dal database: {db_err}", exc_info=True)
            finally:
                self.conn = None # Imposta a None in ogni caso dopo il tentativo di chiusura
        else:
            self.logger.info("Nessuna connessione attiva da chiudere o già chiusa.")

    def commit(self):
        """
        Esegue il commit della transazione corrente.
        Ha effetto solo se il livello di isolamento non è AUTOCOMMIT.
        """
        if self.conn and not self.conn.closed:
            if self.conn.isolation_level != ISOLATION_LEVEL_AUTOCOMMIT:
                try:
                    self.conn.commit()
                    self.logger.debug("Commit della transazione eseguito.")
                except psycopg2.Error as db_err:
                    self.logger.error(f"Errore durante il commit della transazione: {db_err}", exc_info=True)
                    raise # Rilancia per permettere al servizio chiamante di gestire l'errore
            else:
                self.logger.debug("AUTOCOMMIT attivo, commit esplicito non necessario/applicabile.")
        else:
            self.logger.warning("Tentativo di commit su connessione non attiva o chiusa.")

    def rollback(self):
        """
        Esegue il rollback della transazione corrente.
        Ha effetto solo se il livello di isolamento non è AUTOCOMMIT.
        """
        if self.conn and not self.conn.closed:
            if self.conn.isolation_level != ISOLATION_LEVEL_AUTOCOMMIT:
                try:
                    self.conn.rollback()
                    self.logger.info("Rollback della transazione eseguito.")
                except psycopg2.Error as db_err:
                    self.logger.error(f"Errore durante il rollback della transazione: {db_err}", exc_info=True)
                    # Generalmente non si rilancia l'eccezione qui, poiché il rollback è spesso l'ultima risorsa
            else:
                self.logger.debug("AUTOCOMMIT attivo, rollback esplicito non ha effetto su statement precedenti in questo modo.")
        else:
            self.logger.warning("Tentativo di rollback su connessione non attiva o chiusa.")

    def _format_row_as_dict(self, row: tuple, cursor_desc) -> Optional[dict]:
        """
        Converte una tupla di riga in un dizionario usando la descrizione del cursore.
        Utile se non si usa DictCursor o si necessita di una conversione personalizzata.
        Con DictCursor, questo metodo è meno necessario per l'uso standard.
        """
        if row is None:
            return None
        return dict(zip([col.name for col in cursor_desc], row))

    def execute_query(self, query: str, params: Optional[tuple] = None, 
                      fetch_one: bool = False, fetch_all: bool = False, 
                      use_dict_cursor: bool = True) -> Any:
        """
        Esegue una query SQL.

        Args:
            query: La stringa SQL della query.
            params: Una tupla di parametri per la query (opzionale).
            fetch_one: True se si deve recuperare una sola riga.
            fetch_all: True se si devono recuperare tutte le righe.
            use_dict_cursor: True per usare DictCursor (risultati come dizionari), 
                             False per usare un cursore standard (risultati come tuple).

        Returns:
            - Una singola riga (come dizionario o tupla) se fetch_one è True.
            - Una lista di righe (come dizionari o tuple) se fetch_all è True.
            - Il numero di righe affette (rowcount) per operazioni DML (INSERT, UPDATE, DELETE)
              se né fetch_one né fetch_all sono True.
            - Solleva eccezioni psycopg2.Error in caso di problemi con il database.
        """
        if not self.conn or self.conn.closed:
            self.logger.error("Tentativo di esecuzione query su connessione non attiva o chiusa.")
            raise psycopg2.OperationalError("Connessione al database non attiva.")

        cursor_factory_to_use = DictCursor if use_dict_cursor else None
        
        try:
            with self.conn.cursor(cursor_factory=cursor_factory_to_use) as cur:
                # Logging della query (opzionale e attenzione con dati sensibili)
                if self.logger.isEnabledFor(logging.DEBUG): # Controlla il livello prima di mogrify
                     try:
                         # cur.mogrify() mostra la query come sarebbe eseguita, utile per debug
                         self.logger.debug(f"Esecuzione Query: {cur.mogrify(query, params).decode(self.conn.encoding, 'ignore')}")
                     except Exception as mogrify_err:
                         # Mogrify può fallire con alcuni tipi di dati non standard o errori di encoding
                         self.logger.debug(f"Esecuzione Query (mogrify fallito: {mogrify_err}): {query} con params: {params}")
                # else: # Log più sintetico se non in DEBUG
                #    self.logger.info(f"Esecuzione Query (sommario): {query[:100]}...")

                cur.execute(query, params)
                
                if fetch_one:
                    return cur.fetchone() # Restituisce un DictRow o una tupla
                if fetch_all:
                    return cur.fetchall() # Restituisce una lista di DictRow o tuple
                
                # Per INSERT, UPDATE, DELETE, se non è specificato fetch_one/fetch_all,
                # restituiamo il numero di righe affette.
                # Questo è utile per confermare che un'operazione DML ha avuto l'effetto atteso.
                # Per DDL (CREATE, ALTER, DROP), rowcount è spesso -1 o non significativo.
                return cur.rowcount 
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore Database durante l'esecuzione della query: {query[:200]}... Errore: {db_err}", exc_info=True)
            # Il rollback dovrebbe essere gestito dal servizio chiamante, che ha iniziato la transazione.
            raise  # Rilancia l'eccezione per essere gestita dal servizio
        except Exception as e: # Cattura altre eccezioni Python impreviste
            self.logger.error(f"Errore Python generico durante l'esecuzione della query: {e}", exc_info=True)
            raise