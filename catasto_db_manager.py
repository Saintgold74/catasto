#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestore Database Catasto Storico (MODIFICATO per comune.id PK)
==============================================================
Script per la gestione del database catastale con supporto
per operazioni CRUD, chiamate alle stored procedure, gestione utenti,
audit, backup e funzionalità avanzate.

Autore: Marco Santoro (Versione rivista e pulita)
Data: 29/04/2025
"""

import psycopg2
import psycopg2.errors # Importa specificamente gli errori
from psycopg2.extras import DictCursor
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
from psycopg2 import sql, extras, pool
import sys, csv
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import json
import uuid
import os
import shutil # Per trovare i percorsi degli eseguibili
# --- CORREZIONE ---
# Ho corretto il nome della classe in 'CatastoDBAdapter' con la 'B' maiuscola.
from catasto_db_adapter import CatastoDBAdapter

# ------------------

COLONNE_POSSESSORI_DETTAGLI_NUM = 6 # Esempio: ID, Nome Compl, Cognome/Nome, Paternità, Quota, Titolo
COLONNE_POSSESSORI_DETTAGLI_LABELS = ["ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]

# --- Configurazione Logging ---
# Configura il logger se non già fatto altrove
if not logging.getLogger("CatastoDB").hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("catasto_db.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
logger = logging.getLogger("CatastoDB")
# logger.setLevel(logging.DEBUG) # Decommenta per vedere query mogrify
# ------------ ECCEZIONI PERSONALIZZATE ------------
class DBMError(Exception):
    """Classe base per errori specifici del DBManager."""
    pass

class DBUniqueConstraintError(DBMError):
    """Sollevata quando un vincolo di unicità viene violato."""
    def __init__(self, message, constraint_name=None, details=None):
        super().__init__(message)
        self.constraint_name = constraint_name
        self.details = details

class DBNotFoundError(DBMError):
    """Sollevata quando un record atteso non viene trovato per un'operazione."""
    pass

class DBDataError(DBMError):
    """Sollevata per errori relativi a dati o parametri forniti non validi."""
    pass
# -------------------------------------------------

class CatastoDBManager:
    """
    Gestisce le operazioni di amministrazione e manutenzione del database Catasto.
    Versione semplificata.
    """
    # --- CORREZIONE DEFINITIVA ---
    # Aggiunto **kwargs per accettare qualsiasi argomento keyword extra (come 'schema', 
    # 'application_name', etc.) senza causare un TypeError.
    def __init__(self, dbname, user, password, host, port, log_level=logging.INFO, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)

        # Gli argomenti extra in kwargs (es. schema, application_name) vengono
        # semplicemente ignorati qui, rendendo il costruttore compatibile.
        connection_string = f"dbname='{dbname}' user='{user}' password='{password}' host='{host}' port='{port}'"
        
        self.db_adapter = CatastoDBAdapter(connection_string)
        
        if not self.db_adapter.connect():
             self.logger.warning(f"Connessione iniziale fallita per: {connection_string}")
        else:
            self.logger.info("CatastoDBManager inizializzato e connesso con successo.")




    def initialize_main_pool(self) -> bool:
        if self.pool:
            self.logger.info("Pool principale già inizializzato.")
            return True

        target_dbname = self._main_db_conn_params.get("dbname")
        # Costruisci i parametri per il pool, includendo application_name
        pool_config = {
            "minconn": self._min_conn_pool,
            "maxconn": self._max_conn_pool,
            **self._main_db_conn_params, # Espande dbname, user, password, host, port
            "options": f"-c search_path={self.schema},public -c application_name='{self.application_name}_{target_dbname}'"
        }
        try:
            self.logger.info(f"Tentativo di inizializzazione pool per DB '{target_dbname}' con parametri: { {k:v for k,v in pool_config.items() if k != 'password'} }") # Non loggare la password
            self.pool = psycopg2.pool.ThreadedConnectionPool(**pool_config)

            conn_test = None
            try:
                conn_test = self.pool.getconn()
                self.logger.info(f"Pool di connessioni '{self.application_name}_{target_dbname}' per DB '{target_dbname}' inizializzato e testato con successo.")
                return True
            except psycopg2.Error as pool_get_err:
                self.logger.critical(f"Pool per DB '{target_dbname}' creato, ma FALLITO ottenimento connessione di test. Errore Psycopg2: {pool_get_err}", exc_info=False) # exc_info=False per non avere il traceback completo qui, solo il messaggio psycopg2
                self.logger.critical(f"   Dettagli Errore Psycopg2: pgcode={getattr(pool_get_err, 'pgcode', 'N/A')}, pgerror={getattr(pool_get_err, 'pgerror', 'N/A')}")
                if self.pool: self.pool.closeall()
                self.pool = None
                return False
            finally:
                if conn_test and self.pool: self.pool.putconn(conn_test)

        except psycopg2.Error as e_init: # Cattura specificamente errori psycopg2 durante la creazione del pool
            self.logger.critical(f"FALLIMENTO inizializzazione pool principale per DB '{target_dbname}'. Errore Psycopg2: {e_init}", exc_info=False)
            self.logger.critical(f"   Dettagli Errore Psycopg2: pgcode={getattr(e_init, 'pgcode', 'N/A')}, pgerror={getattr(e_init, 'pgerror', 'N/A')}")
            self.pool = None
            return False
        except Exception as e_generic: # Altri errori Python imprevisti
            self.logger.critical(f"FALLIMENTO inizializzazione pool principale per DB '{target_dbname}'. Errore generico: {e_generic}", exc_info=True)
            self.pool = None
            return False
    def close_pool(self):
        """
        Chiude tutte le connessioni nel pool e imposta self.pool a None.
        Questo metodo dovrebbe essere chiamato quando l'applicazione si chiude
        o quando il database a cui il pool è connesso viene cancellato.
        """
        if self.pool:
            try:
                pool_name_app = self.pool._kwargs.get('application_name', self.application_name) # Tenta di ottenere il nome specifico del pool
                db_name_pooled = self.pool._kwargs.get('dbname', 'N/D')
                self.logger.info(f"Tentativo di chiusura del pool di connessioni '{pool_name_app}' per il database '{db_name_pooled}'...")
                self.pool.closeall()
                self.logger.info(f"Pool di connessioni '{pool_name_app}' (DB: '{db_name_pooled}') chiuso con successo.")
            except Exception as e:
                self.logger.error(f"Errore durante la chiusura del pool di connessioni: {e}", exc_info=True)
            finally:
                self.pool = None # Assicura che il pool sia None dopo il tentativo di chiusura, anche in caso di errore.
        else:
            self.logger.info("close_pool chiamato, ma il pool non era attivo o già None.")

    def _get_maintenance_connection(self, db_user_admin: str, db_password_admin: str, maintenance_dbname: str = "postgres"):
        """Ottiene una connessione singola a un database di manutenzione (es. postgres)."""
        maint_conn_params = self._main_db_conn_params.copy()
        maint_conn_params["dbname"] = maintenance_dbname
        # Usa le credenziali dell'utente admin del DB fornite, non quelle dell'app per catasto_storico
        maint_conn_params["user"] = db_user_admin
        maint_conn_params["password"] = db_password_admin 
        
        self.logger.info(f"Tentativo di connessione al DB di manutenzione '{maintenance_dbname}' come utente '{db_user_admin}'.")
        try:
            conn = psycopg2.connect(**maint_conn_params)
            conn.autocommit = True # Utile per comandi come CREATE DATABASE
            return conn
        except psycopg2.Error as e:
            self.logger.error(f"Errore connessione al DB di manutenzione '{maintenance_dbname}': {e}", exc_info=True)
            raise DBMError(f"Impossibile connettersi al database '{maintenance_dbname}': {e}") from e

    def check_database_exists(self, target_dbname: str, admin_user: str, admin_password: str) -> bool:
        """Verifica se un database specifico esiste connettendosi a 'postgres'."""
        conn_maint = None
        exists = False
        try:
            conn_maint = self._get_maintenance_connection(admin_user, admin_password, maintenance_dbname="postgres")
            with conn_maint.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_dbname,))
                exists = cur.fetchone() is not None
                self.logger.info(f"Controllo esistenza database '{target_dbname}': {'Esiste' if exists else 'Non esiste'}.")
        except DBMError as e: # Errore di connessione al DB di manutenzione
            self.logger.error(f"Impossibile verificare esistenza DB '{target_dbname}' due to error connecting to maintenance DB: {e}")
            # In questo caso, non possiamo sapere se esiste, consideriamo che non esista o sia inaccessibile
            exists = False 
        except psycopg2.Error as e: # Altri errori SQL
            self.logger.error(f"Errore DB verificando esistenza database '{target_dbname}': {e}", exc_info=True)
            exists = False
        finally:
            if conn_maint:
                conn_maint.close()
        return exists

    def create_target_database(self, target_dbname: str, admin_user: str, admin_password: str) -> bool:
        """Crea il database target (es. catasto_storico) se non esiste, connettendosi a 'postgres'."""
        conn_maint = None
        try:
            # Prima verifica se esiste per evitare errore CREATE se esiste già
            if self.check_database_exists(target_dbname, admin_user, admin_password):
                self.logger.info(f"Il database '{target_dbname}' esiste già. Nessuna azione di creazione eseguita.")
                return True # Considera successo se esiste già

            conn_maint = self._get_maintenance_connection(admin_user, admin_password, maintenance_dbname="postgres")
            with conn_maint.cursor() as cur: # autocommit è True sulla connessione
                self.logger.info(f"Tentativo di creare il database '{target_dbname}'...")
                # Usa sql.SQL per formattare nomi di database in modo sicuro
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_dbname)))
                self.logger.info(f"Database '{target_dbname}' creato con successo.")
            return True
        except DBMError as e: # Errore di connessione al DB di manutenzione
            self.logger.error(f"Impossibile creare DB '{target_dbname}' due to error connecting to maintenance DB: {e}")
            return False
        except psycopg2.Error as e: # Altri errori SQL, es. "database ... already exists" se il check precedente fallisce
            self.logger.error(f"Errore DB durante la creazione del database '{target_dbname}': {getattr(e, 'pgerror', str(e))}", exc_info=False)
            if "already exists" in str(e).lower(): # Se esiste già, consideralo OK
                self.logger.info(f"Database '{target_dbname}' esisteva già (errore CREATE DATABASE ignorato).")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Errore Python imprevisto durante la creazione del database '{target_dbname}': {e}", exc_info=True)
            return False
        finally:
            if conn_maint:
                conn_maint.close()

    # Modifica _get_connection
    def _get_connection(self):
        if not self.pool:
            self.logger.error("Tentativo di ottenere connessione ma il pool principale non è inizializzato.")
            # Potrebbe essere meglio sollevare un'eccezione più specifica che la UI può catturare
            # per informare l'utente che il DB non è pronto.
            raise DBMError("Pool di connessioni al database principale non inizializzato. "
                        "È necessario creare o configurare il database tramite il tab 'Amministrazione DB'.")
        try:
                conn = self.pool.getconn()
                self.logger.debug(f"Connessione {id(conn)} ottenuta dal pool. DSN: {conn.dsn if hasattr(conn, 'dsn') and not conn.closed else 'N/A o Chiusa'}")
                return conn
        except Exception as e: # Cattura errori da getconn() come PoolError (se il pool è pieno e non può crescere)
                self.logger.error(f"Errore critico nell'ottenere una connessione dal pool: {e}", exc_info=True)
                raise psycopg2.OperationalError(f"Impossibile ottenere una connessione valida dal pool: {e}")

    def _release_connection(self, conn):
        """Rilascia una connessione al pool."""
        if self.pool and conn and not conn.closed: # Aggiungi 'and not conn.closed'
            try:
                self.pool.putconn(conn)
                self.logger.debug(f"Connessione {id(conn)} rilasciata al pool.")
            except Exception as e:
                self.logger.error(f"Errore nel rilasciare connessione {id(conn)} al pool: {e}. Tento chiusura forzata.", exc_info=True)
                try: 
                    if not conn.closed: conn.close()
                except psycopg2.Error: pass
        elif not self.pool:
            self.logger.warning(f"Tentativo di rilasciare connessione {id(conn)} ma il pool non è (più) attivo. Tento chiusura.")
            try:
                if conn and not conn.closed: conn.close()
            except psycopg2.Error: pass
        elif conn and conn.closed:
            self.logger.debug(f"Connessione {id(conn)} era già chiusa, non ripristinato al pool.")
    def disconnect_pool_temporarily(self) -> bool:
        self.logger.info("Chiusura temporanea del pool di connessioni per operazione di ripristino...")
        self.close_pool() # Chiude e nullifica self.pool
        return True # Assume successo; close_pool gestisce i suoi log
    def reconnect_pool_if_needed(self) -> bool:
        self.logger.info("Tentativo di ricreare il pool di connessioni dopo operazione di ripristino...")
        if not self.pool: # Se il pool è None (come dopo close_pool)
            # CORREZIONE QUI: chiama il metodo corretto
            if not self.initialize_main_pool(): # Tenta di reinizializzarlo
                self.logger.error("Fallimento nella reinizializzazione del pool durante reconnect_pool_if_needed.")
                return False # Indica che la reinizializzazione è fallita
        
        # Verifica aggiuntiva che il pool sia ora attivo e funzionante
        if self.pool:
            try:
                test_conn = self._get_connection() # Questo solleverà DBMError se il pool è ancora None o problematico
                if test_conn: # Assicurati che la connessione sia valida
                    self._release_connection(test_conn)
                    self.logger.info("Pool ricreato/verificato e testato con successo dopo riconnessione.")
                    return True
                else: # _get_connection ha restituito None senza sollevare eccezione (improbabile con la logica attuale)
                    self.logger.error("Pool sembra attivo ma _get_connection ha restituito None durante reconnect_pool_if_needed.")
                    return False
            except DBMError as e_dbm: # Cattura DBMError se _get_connection fallisce
                self.logger.error(f"Pool ricreato (o era già esistente), ma test di connessione fallito: {e_dbm}", exc_info=False)
                return False
            except Exception as e: # Altri errori imprevisti
                self.logger.error(f"Errore generico durante il test del pool ricreato: {e}", exc_info=True)
                return False
        else: # Se self.pool è ancora None dopo il tentativo di initialize_main_pool()
            self.logger.error("Fallimento nella ricreazione del pool (self.pool è ancora None) durante reconnect_pool_if_needed.")
            return False

    def get_current_dbname(self) -> Optional[str]:
        if hasattr(self, '_main_db_conn_params') and self._main_db_conn_params: # DEVE USARE _main_db_conn_params
            return self._main_db_conn_params.get("dbname")
        # Aggiorna anche il messaggio di log se vuoi essere preciso
        self.logger.warning("Tentativo di accesso a dbname fallito: _main_db_conn_params non trovato o vuoto.")
        return None

    def get_current_user(self) -> Optional[str]:
        if hasattr(self, '_main_db_conn_params') and self._main_db_conn_params: # DEVE USARE _main_db_conn_params
            return self._main_db_conn_params.get("user")
        self.logger.warning("Tentativo di accesso a user fallito: _main_db_conn_params non trovato o vuoto.")
        return None

    def get_connection_parameters(self) -> Dict[str, Any]:
        if hasattr(self, '_main_db_conn_params') and self._main_db_conn_params: # DEVE USARE _main_db_conn_params
            params_copy = self._main_db_conn_params.copy()
            params_copy.pop('password', None) 
            return params_copy
        self.logger.warning("Tentativo di accesso ai parametri di connessione fallito: _main_db_conn_params non definito.")
        return {}
    

    
    def fetchall(self) -> List[Dict]:
        """Recupera tutti i risultati dell'ultima query come lista di dizionari."""
        # Utilizza self.cursor, che è impostato da execute_query
        if self.cursor and not self.cursor.closed:
            try:
                # Il DictCursor restituisce già dict-like rows, quindi dict(row) potrebbe essere ridondante
                # ma non è dannoso. Se self.cursor.fetchall() restituisce già una lista di dict (o DictRow),
                # la conversione esplicita potrebbe non essere necessaria.
                # Per sicurezza e chiarezza, lasciamola se DictCursor non restituisce dict nativi.
                # Se DictCursor restituisce oggetti DictRow, sono già simili a dizionari.
                risultati = self.cursor.fetchall()
                # Se DictCursor è usato, ogni 'row' in 'risultati' è già un oggetto simile a un dizionario.
                # La conversione [dict(row) for row in ...] è sicura.
                return risultati # Se DictCursor restituisce direttamente una lista di dizionari (o oggetti DictRow)
                # oppure: return [dict(row) for row in risultati] # Se necessario convertire esplicitamente
            except psycopg2.ProgrammingError: # Si verifica se si tenta di fetch da una query che non restituisce risultati
                logger.warning("Nessun risultato da recuperare per l'ultima query (fetchall).")
                return []
            except Exception as e:
                logger.error(f"Errore generico durante fetchall: {e}")
                return []
        else: # self.cursor è None o è chiuso
            logger.warning("Tentativo di fetchall senza un cursore valido o su un cursore chiuso.")
            return []

    def fetchone(self) -> Optional[Dict[str, Any]]:
        """Recupera una riga dal cursore."""
        if self.cursor: # Verifica che il cursore esista
            try:
                return self.cursor.fetchone()
            except psycopg2.Error as e:
                logger.error(f"Errore DB durante fetchone: {e}")
                return None
        else:
            logger.warning("Tentativo di fetchone senza un cursore valido.")
            return None
    
        # --- Metodi CRUD e Ricerca Base (MODIFICATI per comune_id) ---
 # All'interno della classe CatastoDBManager in catasto_db_manager.py
# Assicurati che le importazioni e le definizioni delle eccezioni siano presenti.
# import datetime
# from typing import Optional, Dict, Any, List 
# from datetime import date # Già importato se datetime è importato

    def aggiungi_comune(self,
                        nome_comune: str,
                        provincia: str,
                        # note: Optional[str] = None, # RIMOSSO dagli argomenti se non usato
                        regione: Optional[str] = None, 
                        periodo_id: Optional[int] = None,
                        utente: Optional[str] = None
                       ) -> Optional[int]:
        if not nome_comune or not nome_comune.strip():
            self.logger.error("aggiungi_comune: Il nome del comune è obbligatorio.")
            raise DBDataError("Il nome del comune è obbligatorio.")
        provincia_norm = provincia.strip().upper() if isinstance(provincia, str) else ""
        if not provincia_norm or len(provincia_norm) != 2:
            self.logger.error(f"aggiungi_comune: Provincia non valida: '{provincia}'. Deve essere di 2 caratteri.")
            raise DBDataError("La provincia è obbligatoria e deve essere di 2 caratteri (es. SV).")

        # actual_note = note.strip() if isinstance(note, str) and note.strip() else None # RIMOSSO
        actual_regione = regione.strip() if isinstance(regione, str) and regione.strip() else None
        
        # Query SQL aggiornata senza 'note'
        query = f"""
            INSERT INTO {self.schema}.comune 
                (nome, provincia, regione, periodo_id, 
                 data_creazione, data_modifica)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id;
        """
        # Parametri aggiornati senza actual_note
        params = (nome_comune.strip(), provincia_norm, actual_regione, periodo_id)
        
        conn = None
        new_comune_id = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.info(f"DBManager: Tentativo di aggiungere comune: Nome='{nome_comune.strip()}', Prov='{provincia_norm}', "
                                 f"Regione='{actual_regione}', PeriodoID='{periodo_id}', Utente (info): '{utente}'") # Rimosso Note dal log
                cur.execute(query, params)
                result = cur.fetchone()
                if result and result[0] is not None:
                    new_comune_id = result[0]
                    conn.commit()
                    self.logger.info(f"Comune '{nome_comune.strip()}' aggiunto con successo. ID: {new_comune_id}.")
                else:
                    conn.rollback()
                    self.logger.error("aggiungi_comune: Inserimento fallito, nessun ID restituito.")
                    raise DBMError("Creazione del comune fallita (nessun ID restituito).")
            return new_comune_id

        # ... (gestione eccezioni come prima, assicurati che non ci siano riferimenti a 'note'
        #      nei messaggi di errore se non pertinenti) ...
        except psycopg2.errors.UniqueViolation as uve:
            if conn: conn.rollback()
            constraint_name = getattr(uve.diag, 'constraint_name', "N/D")
            error_detail = getattr(uve, 'pgerror', str(uve))
            self.logger.error(f"Unicità violata (vincolo: {constraint_name}) aggiungendo comune '{nome_comune.strip()}': {error_detail}")
            msg = f"Impossibile aggiungere il comune: i dati violano un vincolo di unicità (vincolo: {constraint_name}). "
            if "comuni_nome_key" in str(constraint_name).lower() or "comuni_nome_comune_key" in str(constraint_name).lower():
                 msg += f"Esiste già un comune con il nome '{nome_comune.strip()}'."
            raise DBUniqueConstraintError(msg, constraint_name=constraint_name, details=error_detail) from uve
        except psycopg2.errors.UndefinedColumn as ude: 
            if conn: conn.rollback()
            error_detail = getattr(ude, 'pgerror', str(ude)) 
            self.logger.error(f"Errore colonna non definita aggiungendo comune '{nome_comune.strip()}': {error_detail}", exc_info=True)
            msg_user = "Una colonna specificata per l'inserimento del comune non esiste nel database."
            msg_user += "\nVerificare la struttura della tabella 'comune'."
            raise DBMError(msg_user) from ude
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            error_detail = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB generico aggiungendo comune '{nome_comune.strip()}': {error_detail}", exc_info=True)
            raise DBMError(f"Errore database durante l'aggiunta del comune: {error_detail}") from db_err
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python imprevisto aggiungendo comune '{nome_comune.strip()}': {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante l'aggiunta del comune: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
    def registra_comune_nel_db(self, nome: str, provincia: str, regione: str) -> Optional[int]:
        comune_id: Optional[int] = None
        query_insert = """
        INSERT INTO catasto.comune (nome, provincia, regione)
        VALUES (%s, %s, %s)
        ON CONFLICT (nome) DO NOTHING
        RETURNING id;
        """
        query_select = "SELECT id FROM catasto.comune WHERE nome = %s;"

        try:
            if self.execute_query(query_insert, (nome, provincia, regione)):
                # execute_query DEVE aver impostato self.cursor se ha restituito True
                if self.cursor is None: # Controllo di sicurezza aggiuntivo
                    logger.error(f"Errore critico: self.cursor è None dopo execute_query riuscita per INSERT comune '{nome}'.")
                    self.rollback()
                    return None

                risultato_insert = None
                if self.cursor.description: # Verifica se la query poteva ritornare risultati
                    try:
                        risultato_insert = self.cursor.fetchone() # Prova a fare fetch
                    except psycopg2.ProgrammingError as pe: # Es. "no results to fetch"
                        logger.warning(f"Nessun risultato da fetchone() per INSERT comune '{nome}' (probabile ON CONFLICT DO NOTHING): {pe}")
                        risultato_insert = None

                if risultato_insert and 'id' in risultato_insert:
                    comune_id = risultato_insert['id']
                    self.commit()
                    logger.info(f"Comune '{nome}' (ID: {comune_id}) inserito con successo nel database.")
                    return comune_id
                else: # L'INSERT non ha inserito (ON CONFLICT DO NOTHING) o ID non recuperato
                    logger.info(f"Comune '{nome}' non inserito da INSERT (probabile conflitto). Tentativo di SELECT.")
                    if self.execute_query(query_select, (nome,)):
                        if self.cursor is None: # Controllo di sicurezza
                            logger.error(f"Errore critico: self.cursor è None dopo execute_query riuscita per SELECT comune '{nome}'.")
                            self.rollback()
                            return None
                        
                        risultato_select = self.fetchone() # fetchone() ora dovrebbe usare il cursore del SELECT
                        if risultato_select and 'id' in risultato_select:
                            comune_id = risultato_select['id']
                            self.commit() 
                            logger.info(f"Comune '{nome}' (ID: {comune_id}) già esistente, operazione confermata.")
                            return comune_id
                        else:
                            logger.error(f"Errore logico: Comune '{nome}' non inserito e non trovato dopo ON CONFLICT e successivo SELECT.")
                            self.rollback()
                            return None
                    else: # Errore durante il SELECT
                        # execute_query dovrebbe aver già gestito il rollback
                        logger.error(f"Errore DB nel selezionare il comune '{nome}' dopo un potenziale conflitto.")
                        return None
            else: # Errore durante l'INSERT iniziale
                # execute_query dovrebbe aver già gestito il rollback
                logger.error(f"Errore DB iniziale durante l'inserimento del comune '{nome}'.")
                return None

        except psycopg2.Error as db_err:
            logger.error(f"Errore database (psycopg2) in registra_comune_nel_db per '{nome}': {db_err}")
            self.rollback()
            return None
        except AttributeError as ae: # Specifico per l'errore 'has no attribute cursor' se persiste
            logger.error(f"AttributeError in registra_comune_nel_db per '{nome}': {ae}. Controllare gestione self.cursor.")
            self.rollback()
            return None
        except Exception as e:
            logger.error(f"Errore Python generico in registra_comune_nel_db per '{nome}': {e}")
            self.rollback()
            return None
    def get_comuni(self, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = None
        comuni_list = []
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query_base = f"SELECT id, nome, provincia, regione FROM {self.schema}.comune"
                if search_term:
                    query = f"{query_base} WHERE nome ILIKE %s ORDER BY nome"
                    params = (f"%{search_term}%",)
                else:
                    query = f"{query_base} ORDER BY nome"
                    params = None
                
                self.logger.debug(f"Esecuzione get_comuni: {cur.mogrify(query, params).decode('utf-8', 'ignore') if params else query}")
                cur.execute(query, params)
                results = cur.fetchall()
                comuni_list = [dict(row) for row in results] if results else []
                self.logger.info(f"Recuperati {len(comuni_list)} comuni (search_term: '{search_term}').")
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_comuni: {db_err}", exc_info=True)
            # Non sollevare eccezione, comportamento precedente restituiva lista vuota
        except Exception as e:
            self.logger.error(f"Errore Python in get_comuni: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return comuni_list
    
    def get_all_comuni_details(self) -> List[Dict[str, Any]]:
        """Recupera i dettagli disponibili di tutti i comuni."""
        conn = None
        comuni_list = []
        query = f"""
            SELECT id, nome AS nome_comune, provincia, regione, 
                data_creazione, data_modifica 
            FROM {self.schema}.comune ORDER BY nome_comune;
        """ # Corretta per riflettere le colonne esistenti
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_all_comuni_details: {query}")
                cur.execute(query)
                results = cur.fetchall()
                if results:
                    comuni_list = [dict(row) for row in results]
                self.logger.info(f"Recuperati {len(comuni_list)} comuni per get_all_comuni_details.")
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_all_comuni_details: {db_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python in get_all_comuni_details: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return comuni_list
    def get_elenco_comuni_semplice(self):
        """
        Recupera un elenco di tutti i comuni (ID e nome) per popolare una scelta utente.
        Utilizza il pool di connessioni della classe.
        """
        conn = None
        try:
            conn = self._get_connection()  # Prende una connessione dal pool
            with conn.cursor() as cur:
                # --- CORREZIONE QUI ---
                # Ho sostituito 'denominazione' con 'nome'
                cur.execute("SELECT id, nome FROM comune ORDER BY nome")
                return cur.fetchall()
        except psycopg2.Error as e:
            self.logger.error(f"Errore nel recuperare l'elenco dei comuni: {e}")
            raise e
        finally:
            if conn:
                self._release_connection(conn)  # Rilascia la connessione al pool

    def import_possessori_from_csv(self, file_path, comune_id):
        """
        Importa una lista di possessori da un file CSV associandoli a un comune specifico.
        Utilizza il pool di connessioni e gestisce una transazione.
        """
        records_to_import = []

        # FASE 1: Lettura e validazione del CSV (invariata)
        try:
            with open(file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                required_headers = {'cognome_nome', 'nome_completo'}
                if not required_headers.issubset(reader.fieldnames):
                    raise ValueError(f"Intestazioni mancanti nel CSV. Richieste: {', '.join(required_headers)}")

                for row in reader:
                    if not row.get('cognome_nome') or not row.get('nome_completo'):
                        raise ValueError(f"Dati mancanti alla riga {reader.line_num}. 'cognome_nome' e 'nome_completo' sono obbligatori.")
                    records_to_import.append(row)
        except FileNotFoundError:
            raise FileNotFoundError(f"File non trovato: {file_path}")
        except Exception as e:
            raise IOError(f"Errore leggendo il file CSV: {e}")

        if not records_to_import:
            return 0

        # FASE 2: Inserimento nel Database usando il pool e una transazione
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                conn.autocommit = False  # Inizia la transazione
                
                for i, record in enumerate(records_to_import):
                    line_num = i + 2
                    nome_completo = record['nome_completo']
                    
                    cur.execute("SELECT id FROM possessore WHERE nome_completo = %s AND comune_id = %s", (nome_completo, comune_id))
                    if cur.fetchone():
                        raise ValueError(f"Errore riga {line_num}: Il possessore '{nome_completo}' esiste già nel comune selezionato.")

                    cur.execute(
                        """
                        INSERT INTO possessore (comune_id, cognome_nome, paternita, nome_completo, attivo)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            comune_id, record['cognome_nome'], record.get('paternita'),
                            nome_completo, True
                        )
                    )
            
            conn.commit()  # Conferma la transazione se il loop si completa
            return len(records_to_import)

        except (Exception, psycopg2.Error) as error:
            if conn:
                conn.rollback()  # Annulla la transazione in caso di qualsiasi errore
            
            if isinstance(error, ValueError):
                raise error
            else:
                raise ValueError(f"Importazione annullata a causa di un errore del database: {error}")
        finally:
            if conn:
                self._release_connection(conn)

    def import_partite_from_csv(self, file_path, comune_id):
        """
        Importa una lista di partite da un file CSV associandole a un comune specifico.
        L'operazione è transazionale.
        """
        records_to_import = []

        # FASE 1: Lettura e validazione del file CSV
        try:
            with open(file_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                required_headers = {'numero_partita', 'data_impianto', 'stato', 'tipo'}
                if not required_headers.issubset(reader.fieldnames):
                    raise ValueError(f"Intestazioni mancanti nel CSV. Richieste: {', '.join(required_headers)}")

                for row in reader:
                    # Validazione dei dati obbligatori per ogni riga
                    if not all(row.get(key) for key in required_headers):
                        raise ValueError(f"Dati mancanti alla riga {reader.line_num}. 'numero_partita', 'data_impianto', 'stato' e 'tipo' sono obbligatori.")
                    records_to_import.append(row)
        except FileNotFoundError:
            raise FileNotFoundError(f"File non trovato: {file_path}")
        except Exception as e:
            raise IOError(f"Errore leggendo il file CSV: {e}")

        if not records_to_import:
            return 0

        # FASE 2: Inserimento nel Database usando il pool e una transazione
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                conn.autocommit = False  # Inizia la transazione

                for i, record in enumerate(records_to_import):
                    line_num = i + 2
                    numero_partita = record['numero_partita']
                    suffisso_partita = record.get('suffisso_partita') or None # Gestisce stringhe vuote

                    # Controlla se la partita esiste già per quel comune
                    cur.execute(
                        "SELECT id FROM partita WHERE comune_id = %s AND numero_partita = %s AND (suffisso_partita = %s OR (suffisso_partita IS NULL AND %s IS NULL))",
                        (comune_id, numero_partita, suffisso_partita, suffisso_partita)
                    )
                    if cur.fetchone():
                        suffisso_str = f" con suffisso '{suffisso_partita}'" if suffisso_partita else ""
                        raise ValueError(f"Errore riga {line_num}: La partita numero '{numero_partita}'{suffisso_str} esiste già nel comune selezionato.")

                    cur.execute(
                        """
                        INSERT INTO partita (comune_id, numero_partita, suffisso_partita, data_impianto, data_chiusura, numero_provenienza, stato, tipo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            comune_id,
                            numero_partita,
                            suffisso_partita,
                            record['data_impianto'],
                            record.get('data_chiusura') or None, # Gestisce stringa vuota o chiave mancante
                            record.get('numero_provenienza') or None,
                            record['stato'],
                            record['tipo']
                        )
                    )
            
            conn.commit()
            return len(records_to_import)

        except (Exception, psycopg2.Error) as error:
            if conn:
                conn.rollback()
            
            if isinstance(error, ValueError):
                raise error
            else:
                raise ValueError(f"Importazione annullata a causa di un errore del database: {error}")
        finally:
            if conn:
                self._release_connection(conn)

    def check_possessore_exists(self, nome_completo: str, comune_id: Optional[int] = None) -> Optional[int]:
        """Verifica se un possessore esiste (per nome completo e comune_id) e ritorna il suo ID."""
        try:
            if comune_id is not None:
                query = "SELECT id FROM possessore WHERE nome_completo = %s AND comune_id = %s AND attivo = TRUE" # Usa comune_id
                params = (nome_completo, comune_id)
            else:
                query = "SELECT id FROM possessore WHERE nome_completo = %s AND attivo = TRUE"
                params = (nome_completo,)
            if self.execute_query(query, params):
                result = self.fetchone()
                return result['id'] if result else None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in check_possessore_exists: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in check_possessore_exists: {e}")
        return None

    # All'interno della classe CatastoDBManager in catasto_db_manager.py

    def create_possessore(self, 
                          nome_completo: str, 
                          comune_riferimento_id: int,
                          paternita: Optional[str] = None, 
                          attivo: bool = True, 
                          cognome_nome: Optional[str] = None
                         ) -> Optional[int]: # Restituisce l'ID del nuovo possessore o None
        """
        Crea un nuovo possessore nel database.
        Utilizza il pool di connessioni.
        Solleva eccezioni specifiche in caso di errore (es. DBUniqueConstraintError).

        Args:
            nome_completo: Il nome completo del possessore (obbligatorio).
            comune_riferimento_id: L'ID del comune di riferimento (obbligatorio).
            paternita: La paternità del possessore (opzionale).
            attivo: Stato del possessore (default True).
            cognome_nome: Cognome e Nome separati, per ricerca/ordinamento (opzionale).

        Returns:
            L'ID del possessore appena creato se l'operazione ha successo, altrimenti None.
            Solleva eccezioni in caso di errori DB che non riesce a gestire.
        """
        if not nome_completo or not nome_completo.strip():
            self.logger.error("create_possessore: Il nome_completo è obbligatorio.")
            raise DBDataError("Il nome completo del possessore è obbligatorio.")
        if comune_riferimento_id is None or not isinstance(comune_riferimento_id, int) or comune_riferimento_id <= 0:
            self.logger.error(f"create_possessore: comune_riferimento_id non valido: {comune_riferimento_id}")
            raise DBDataError("ID del comune di riferimento non valido.")

        query = f"""
            INSERT INTO {self.schema}.possessore 
                (nome_completo, paternita, comune_id, attivo, cognome_nome, data_creazione, data_modifica)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id;
        """
        # Gestisci i valori opzionali che potrebbero essere stringhe vuote passate dalla GUI
        actual_paternita = paternita.strip() if isinstance(paternita, str) and paternita.strip() else None
        actual_cognome_nome = cognome_nome.strip() if isinstance(cognome_nome, str) and cognome_nome.strip() else None
        
        params = (nome_completo.strip(), actual_paternita, comune_riferimento_id, attivo, actual_cognome_nome)
        
        conn = None
        new_possessore_id = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione query create_possessore: {cur.mogrify(query, params).decode('utf-8', 'ignore')}")
                cur.execute(query, params)
                result = cur.fetchone()
                if result and result[0] is not None:
                    new_possessore_id = result[0]
                    conn.commit()
                    self.logger.info(f"Possessore '{nome_completo}' (Comune ID: {comune_riferimento_id}) creato con successo. ID: {new_possessore_id}.")
                else:
                    # Questo non dovrebbe accadere se RETURNING id è usato e l'insert ha successo senza sollevare eccezioni
                    conn.rollback() # Assicurati che la transazione sia annullata
                    self.logger.error("create_possessore: Inserimento fallito, nessun ID restituito e nessuna eccezione DB esplicita.")
                    raise DBMError("Creazione del possessore fallita senza un errore database specifico.")
            
            return new_possessore_id

        except psycopg2.errors.UniqueViolation as uve:
            if conn: conn.rollback()
            constraint_name = getattr(uve.diag, 'constraint_name', "N/D")
            error_detail = getattr(uve, 'pgerror', str(uve)) # Dettaglio errore da PostgreSQL
            self.logger.error(f"Errore di unicità (vincolo: {constraint_name}) creando possessore '{nome_completo}': {error_detail}")
            # Potresti avere un vincolo UNIQUE su (nome_completo, comune_id) o altri campi.
            # Adatta il messaggio in base ai tuoi vincoli specifici.
            if "possessore_nome_completo_comune_id_key" in str(constraint_name).lower(): # Esempio di nome vincolo
                 msg = f"Un possessore con nome '{nome_completo}' esiste già in questo comune."
            else:
                 msg = f"Impossibile creare il possessore: i dati violano un vincolo di unicità (vincolo: {constraint_name})."
            raise DBUniqueConstraintError(msg, constraint_name=constraint_name, details=error_detail) from uve
        
        except psycopg2.errors.ForeignKeyViolation as fke:
            if conn: conn.rollback()
            constraint_name = getattr(fke.diag, 'constraint_name', "N/D")
            error_detail = getattr(fke, 'pgerror', str(fke))
            self.logger.error(f"Violazione Foreign Key (vincolo: {constraint_name}) creando possessore '{nome_completo}': {error_detail}")
            if "possessore_comune_id_fkey" in str(constraint_name).lower(): # Nome del tuo vincolo FK su comune_id
                 msg = f"Il comune di riferimento specificato (ID: {comune_riferimento_id}) non esiste."
            else:
                 msg = f"Impossibile creare il possessore: errore di riferimento a dati esterni (vincolo: {constraint_name})."
            raise DBMError(msg) from fke # Potresti creare una DBForeignKeyError specifica
            
        except psycopg2.Error as db_err: # Altri errori DB specifici
            if conn: conn.rollback()
            error_detail = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB generico creando possessore '{nome_completo}': {error_detail}", exc_info=True)
            raise DBMError(f"Errore database durante la creazione del possessore: {error_detail}") from db_err
        
        except Exception as e: # Errori Python imprevisti
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python imprevisto creando possessore '{nome_completo}': {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante la creazione del possessore: {e}") from e
        
        finally:
            if conn:
                self._release_connection(conn)

    # In catasto_db_manager.py, all'interno della classe CatastoDBManager

    def get_possessori_by_comune(self, comune_id: int, filter_text: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = None
        possessori_list = []

        query_base = f"""
            SELECT pos.id, c.nome as comune_nome, pos.cognome_nome, pos.paternita,
                pos.nome_completo, pos.attivo
            FROM {self.schema}.possessore pos
            JOIN {self.schema}.comune c ON pos.comune_id = c.id
            WHERE pos.comune_id = %s
        """
        params = [comune_id]

        if filter_text:
            query_base += """
                AND (
                    pos.nome_completo ILIKE %s OR
                    pos.cognome_nome ILIKE %s OR
                    pos.paternita ILIKE %s
                )
            """
            filter_like = f"%{filter_text}%"
            params.extend([filter_like, filter_like, filter_like])

        query = query_base + " ORDER BY pos.nome_completo;"

        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_possessori_by_comune per comune_id {comune_id} con filtro '{filter_text}': {cur.mogrify(query, tuple(params)).decode('utf-8', 'ignore')}")
                cur.execute(query, tuple(params))
                results = cur.fetchall()
                possessori_list = [dict(row) for row in results] if results else []
                self.logger.info(f"Recuperati {len(possessori_list)} possessori per comune ID {comune_id} (filtro: '{filter_text}').")
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_possessori_by_comune (ID: {comune_id}, filtro: '{filter_text}'): {db_err}", exc_info=True)
            raise DBMError(f"Errore database durante il recupero dei possessori: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        except Exception as e:
            self.logger.error(f"Errore Python in get_possessori_by_comune (ID: {comune_id}, filtro: '{filter_text}'): {e}", exc_info=True)
            raise DBMError(f"Errore di sistema durante il recupero dei possessori: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
        return possessori_list

    
    def get_partite_per_possessore(self, possessore_id: int) -> List[Dict[str, Any]]:
        """
        Recupera tutte le partite associate a un possessore specifico.
        
        Args:
            possessore_id: ID del possessore
            
        Returns:
            Lista di dizionari contenenti i dettagli delle partite
            
        Raises:
            DBMError: Per errori di database
            DBDataError: Se l'ID possessore non è valido
        """
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            raise DBDataError(f"ID possessore non valido: {possessore_id}")
        
        conn = None
        try:
            query = f"""
                SELECT DISTINCT
                    p.id,
                    p.numero_partita,
                    p.suffisso_partita,
                    p.tipo,
                    p.stato,
                    p.data_impianto,
                    c.nome as comune_nome,
                    c.id as comune_id,
                    pp.titolo,
                    pp.quota,
                    pp.tipo_partita,
                    (SELECT COUNT(*) FROM {self.schema}.immobile i WHERE i.partita_id = p.id) as num_immobili
                FROM {self.schema}.partita p
                JOIN {self.schema}.comune c ON p.comune_id = c.id
                JOIN {self.schema}.partita_possessore pp ON p.id = pp.partita_id
                WHERE pp.possessore_id = %s
                ORDER BY c.nome, p.numero_partita, p.suffisso_partita
            """
            
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione query get_partite_per_possessore per possessore ID {possessore_id}")
                cur.execute(query, (possessore_id,))
                results = cur.fetchall()
                
                partite_list = [dict(row) for row in results] if results else []
                self.logger.info(f"Trovate {len(partite_list)} partite per possessore ID {possessore_id}")
                return partite_list
                
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_partite_per_possessore per possessore {possessore_id}: {db_err}", exc_info=True)
            if conn: 
                conn.rollback()
            raise DBMError(f"Errore database durante il recupero delle partite per possessore: {db_err}") from db_err
            
        except Exception as e:
            self.logger.error(f"Errore Python in get_partite_per_possessore per possessore {possessore_id}: {e}", exc_info=True)
            if conn: 
                conn.rollback()
            raise DBMError(f"Errore imprevisto durante il recupero delle partite: {e}") from e
            
        finally:
            if conn:
                self._release_connection(conn)
    def get_localita_by_comune(self, comune_id: int, filter_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recupera località per comune_id, con filtro opzionale per nome."""
        conn = None
        localita_list = []
        
        query_base = f"SELECT id, nome, tipo, civico FROM {self.schema}.localita WHERE comune_id = %s"
        params: List[Union[int, str]] = [comune_id] # Usa Union da typing

        if filter_text:
            query_base += " AND nome ILIKE %s"
            params.append(f"%{filter_text}%")
        
        query = query_base + " ORDER BY tipo, nome, civico;"

        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_localita_by_comune per comune_id {comune_id}: {cur.mogrify(query, tuple(params)).decode('utf-8', 'ignore')}")
                cur.execute(query, tuple(params))
                results = cur.fetchall()
                if results:
                    localita_list = [dict(row) for row in results]
                self.logger.info(f"Recuperate {len(localita_list)} località per comune ID {comune_id} (filtro: '{filter_text}').")
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_localita_by_comune: {db_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python in get_localita_by_comune: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return localita_list
    def search_possessori_by_term_globally(self, search_term: Optional[str], limit: int = 200) -> List[Dict[str, Any]]: # Aggiunto limite
        """
        Ricerca possessori globalmente. Se search_term è None, restituisce i primi 'limit' possessori.
        Altrimenti, filtra per nome_completo, cognome_nome, paternita.
        Restituisce i campi necessari per PossessoreSelectionDialog.
        """
        conn = None
        data_list: List[Dict[str, Any]] = []
        
        # Query base che include il JOIN per il nome del comune
        query_base = f"""
            SELECT p.id, p.nome_completo, p.cognome_nome, p.paternita, p.attivo,
                   c.nome AS comune_riferimento_nome 
            FROM {self.schema}.possessore p
            LEFT JOIN {self.schema}.comune c ON p.comune_id = c.id 
        """
        
        params = []
        where_clauses = []

        if search_term and search_term.strip():
            like_term = f"%{search_term.strip()}%"
            where_clauses.append("(p.nome_completo ILIKE %s OR p.cognome_nome ILIKE %s OR p.paternita ILIKE %s)")
            params.extend([like_term, like_term, like_term])
        
        query = query_base
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY p.nome_completo LIMIT %s;" # Applica sempre il limite
        params.append(limit)
        
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                log_msg_params = f"search_term='{search_term}', limit={limit}"
                self.logger.debug(f"Esecuzione search_possessori_by_term_globally: Query='{cur.mogrify(query, tuple(params)).decode('utf-8', 'ignore')}'")
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                if rows:
                    data_list = [dict(row) for row in rows]
                self.logger.info(f"search_possessori_by_term_globally ({log_msg_params}) ha trovato {len(data_list)} possessori.")
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in search_possessori_by_term_globally: {db_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python in search_possessori_by_term_globally: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return data_list
    def get_possessori_per_partita(self, partita_id: int) -> List[Dict[str, Any]]:
        """
        Recupera tutti i possessori associati a una data partita, inclusi i dettagli
        del legame dalla tabella partita_possessore.

        Args:
            partita_id: L'ID della partita per cui recuperare i possessori.

        Returns:
            Una lista di dizionari, dove ogni dizionario rappresenta un possessore associato
            e contiene: 'id_relazione_partita_possessore' (partita_possessore.id),
                         'possessore_id' (possessore.id), 
                         'nome_completo_possessore' (possessore.nome_completo),
                         'paternita_possessore' (possessore.paternita),
                         'titolo_possesso' (partita_possessore.titolo),
                         'quota_possesso' (partita_possessore.quota),
                         'tipo_partita_rel' (partita_possessore.tipo_partita).
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            self.logger.error("get_possessori_per_partita: partita_id non valido.")
            return []

        query = f"""
            SELECT
                pp.id AS id_relazione_partita_possessore,
                pos.id AS possessore_id,
                pos.nome_completo AS nome_completo_possessore,
                pos.paternita AS paternita_possessore, 
                pp.titolo AS titolo_possesso,
                pp.quota AS quota_possesso,
                pp.tipo_partita AS tipo_partita_rel 
            FROM
                {self.schema}.partita_possessore pp
            JOIN
                {self.schema}.possessore pos ON pp.possessore_id = pos.id
            WHERE
                pp.partita_id = %s
            ORDER BY
                pos.nome_completo;
        """
        
        possessori_associati = []
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione query get_possessori_per_partita per partita_id {partita_id}: {cur.mogrify(query, (partita_id,)).decode('utf-8', 'ignore')}")
                cur.execute(query, (partita_id,))
                results = cur.fetchall()
                if results:
                    possessori_associati = [dict(row) for row in results]
                self.logger.info(f"Trovati {len(possessori_associati)} possessori per la partita ID {partita_id}.")
        except psycopg2.Error as e:
            self.logger.error(f"Errore DB durante il recupero dei possessori per la partita ID {partita_id}: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore generico durante il recupero dei possessori per la partita ID {partita_id}: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        
        return possessori_associati


    def insert_localita(self, comune_id: int, nome: str, tipo: str,
                        civico: Optional[int] = None) -> Optional[int]:
        """
        Inserisce una nuova località se non esiste una combinazione identica 
        (comune_id, nome, civico), altrimenti recupera l'ID della località esistente.
        Ritorna l'ID della località (nuova o esistente).
        Solleva eccezioni specifiche in caso di errore.
        """
        if not (isinstance(comune_id, int) and comune_id > 0):
            raise DBDataError(f"ID comune non valido per inserimento località: {comune_id}")
        if not (isinstance(nome, str) and nome.strip()):
            raise DBDataError("Il nome della località è obbligatorio.")
        if not (isinstance(tipo, str) and tipo.strip()): # Aggiungi validazione per i valori di 'tipo' se necessario
            raise DBDataError("Il tipo di località è obbligatorio.")

        # Normalizza civico: se è 0 e vuoi trattarlo come NULL, fallo qui.
        # La tua tabella ha UNIQUE(comune_id, nome, civico), quindi NULL è distinto.
        actual_civico = civico if civico is not None and civico > 0 else None # Esempio: tratta 0 come NULL

        conn = None
        localita_id: Optional[int] = None

        # Query 1: Tentativo di inserimento con ON CONFLICT DO NOTHING
        # Questo approccio è buono perché è atomico.
        # Se c'è un conflitto, non fa nulla e non restituisce 'id'.
        # Se non c'è conflitto, inserisce e restituisce 'id'.
        query_insert_on_conflict = f"""
            INSERT INTO {self.schema}.localita (comune_id, nome, tipo, civico, data_creazione, data_modifica)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (comune_id, nome, civico) DO NOTHING 
            RETURNING id; 
        """ 
        # Nota: ON CONFLICT (comune_id, nome, civico) DO NOTHING significa che se il civico è NULL,
        # il conflitto si verifica solo se anche il record esistente ha civico NULL.
        # Se il tuo vincolo UNIQUE gestisce i NULL in modo diverso (es. UNIQUE NULLS NOT DISTINCT),
        # questa query potrebbe comportarsi diversamente. Assumiamo UNIQUE standard.

        # Query 2: Se l'INSERT non ha restituito un ID (a causa di ON CONFLICT DO NOTHING),
        # selezioniamo l'ID della riga esistente.
        query_select_existing = f"""
            SELECT id FROM {self.schema}.localita
            WHERE comune_id = %s AND nome = %s AND
                  ((civico IS NULL AND %s IS NULL) OR (civico = %s));
        """
        
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Tentativo INSERT ON CONFLICT per località: C_ID={comune_id}, Nome='{nome}', Civico={actual_civico}")
                cur.execute(query_insert_on_conflict, (comune_id, nome.strip(), tipo.strip(), actual_civico))
                
                insert_result = cur.fetchone()
                
                if insert_result and insert_result['id']:
                    localita_id = insert_result['id']
                    conn.commit()
                    self.logger.info(f"Località '{nome}' (Comune ID: {comune_id}) inserita con successo. ID: {localita_id}.")
                else:
                    # Conflitto o nessun ID restituito, la località dovrebbe già esistere. Cercala.
                    self.logger.info(f"Località '{nome}' (Comune ID: {comune_id}) non inserita (probabile conflitto o nessun ID restituito). Tento SELECT.")
                    # Non c'è bisogno di rollback qui perché "DO NOTHING" non dovrebbe aver modificato nulla
                    # se c'è stato un conflitto. Se non c'è stato conflitto ma RETURNING id non ha funzionato,
                    # il commit precedente non sarebbe comunque avvenuto.
                    
                    cur.execute(query_select_existing, (comune_id, nome.strip(), actual_civico, actual_civico))
                    select_result = cur.fetchone()
                    if select_result and select_result['id']:
                        localita_id = select_result['id']
                        self.logger.info(f"Località '{nome}' (Comune ID: {comune_id}) già esistente trovata. ID: {localita_id}.")
                        # Nessun commit necessario per un SELECT
                    else:
                        # Questo caso è strano: INSERT non ha fatto nulla (presunto conflitto),
                        # ma il SELECT non la trova. Potrebbe indicare un problema con la gestione dei NULL
                        # nel vincolo UNIQUE o nella query SELECT, o una race condition (improbabile qui).
                        conn.rollback() # Meglio fare un rollback per sicurezza
                        self.logger.error(f"Logica inconsistente in insert_localita: non inserita e non trovata per C_ID={comune_id}, Nome='{nome}', Civico={actual_civico}.")
                        raise DBMError("Impossibile inserire o trovare la località specificata dopo un conflitto apparente.")
            
            if localita_id is None: # Non dovrebbe essere raggiunto se la logica sopra è corretta
                 raise DBMError("ID località non determinato dopo tentativo di inserimento/selezione.")

        except psycopg2.errors.ForeignKeyViolation as fke:
            if conn: conn.rollback()
            constraint_name = getattr(fke.diag, 'constraint_name', "N/D")
            self.logger.error(f"Violazione FK (vincolo: {constraint_name}) inserendo località '{nome}' per comune ID {comune_id}: {fke.pgerror}")
            if constraint_name == "localita_comune_id_fkey": # Nome del tuo vincolo FK
                msg = f"Il comune con ID {comune_id} non esiste. Impossibile inserire la località."
            else:
                msg = f"Errore di riferimento a dati esterni (vincolo: {constraint_name})."
            raise DBMError(msg) from fke
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB generico in insert_localita '{nome}': {db_err.pgerror}", exc_info=True)
            raise DBMError(f"Errore database durante l'inserimento della località: {db_err.pgerror}") from db_err
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore imprevisto Python in insert_localita '{nome}': {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
        
        return localita_id
    def get_localita_details(self, localita_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera i dettagli completi di una singola località, incluso il nome del comune.

        Args:
            localita_id: L'ID della località da recuperare.

        Returns:
            Un dizionario contenente i dettagli della località se trovata, altrimenti None.
            Il dizionario includerà: 'id', 'nome', 'tipo', 'civico', 
                                     'comune_id', 'comune_nome'.
        """
        if not isinstance(localita_id, int) or localita_id <= 0:
            self.logger.error(f"get_localita_details: localita_id non valido: {localita_id}")
            return None

        query = f"""
            SELECT
                loc.id,
                loc.nome,
                loc.tipo,
                loc.civico,
                loc.comune_id,
                com.nome AS comune_nome
            FROM
                {self.schema}.localita loc
            JOIN
                {self.schema}.comune com ON loc.comune_id = com.id
            WHERE
                loc.id = %s;
        """
        
        conn = None
        localita_data = None
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione query get_localita_details per localita_id {localita_id}: {cur.mogrify(query, (localita_id,)).decode('utf-8', 'ignore')}")
                cur.execute(query, (localita_id,))
                result = cur.fetchone()
                
                if result:
                    localita_data = dict(result)
                    self.logger.info(f"Dettagli recuperati per la località ID {localita_id}: {localita_data.get('nome')}")
                else:
                    self.logger.warning(f"Nessuna località trovata con ID {localita_id}.")
                    # Non sollevare DBNotFoundError qui, il chiamante potrebbe voler gestire None diversamente
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB durante il recupero dei dettagli della località ID {localita_id}: {db_err}", exc_info=True)
            # Non sollevare eccezione, restituisci None come da firma
        except Exception as e:
            self.logger.error(f"Errore generico durante il recupero dei dettagli della località ID {localita_id}: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        
        return localita_data
    
    def update_localita(self, localita_id: int, dati_modificati: Dict[str, Any]):
        """
        Aggiorna i dati di una località esistente nel database.
        Solleva eccezioni specifiche in caso di errore.

        Args:
            localita_id: L'ID della località da aggiornare.
            dati_modificati: Un dizionario contenente i campi della località da aggiornare.
                             Campi attesi e gestiti: 'nome', 'tipo', 'civico'.
                             Il comune_id non viene modificato qui.

        Raises:
            DBDataError: Se localita_id o dati_modificati non sono validi, o se mancano campi obbligatori.
            DBNotFoundError: Se la località con l'ID specificato non viene trovata.
            DBUniqueConstraintError: Se l'aggiornamento viola un vincolo di unicità
                                     (es. nome+civico duplicato nel comune).
            DBMError: Per altri errori generici del database.
        """
        if not isinstance(localita_id, int) or localita_id <= 0:
            self.logger.error(f"update_localita: localita_id non valido: {localita_id}")
            raise DBDataError(f"ID località non valido: {localita_id}")
        if not isinstance(dati_modificati, dict):
            self.logger.error(f"update_localita: dati_modificati non è un dizionario per località ID {localita_id}.")
            raise DBDataError("Formato dati per l'aggiornamento non valido.")

        set_clauses = []
        params = []
        conn = None

        # Validazione e costruzione della clausola SET
        nome_fornito = dati_modificati.get("nome", "").strip()
        if not nome_fornito:
            # Questo controllo dovrebbe essere fatto a livello UI, ma lo includiamo per robustezza.
            raise DBDataError("Il nome della località è obbligatorio e non può essere vuoto.")
        set_clauses.append("nome = %s")
        params.append(nome_fornito)

        tipo_fornito = dati_modificati.get("tipo")
        # Assumendo che i valori validi per 'tipo' siano quelli definiti nel CHECK constraint della tabella.
        # Potresti avere una lista di tipi validi qui per un controllo più stringente.
        # Ad esempio: valid_tipi = ["regione", "via", "borgata"]
        if not tipo_fornito: # or tipo_fornito not in valid_tipi:
            raise DBDataError(f"Il tipo di località '{tipo_fornito}' non è valido o è mancante.")
        set_clauses.append("tipo = %s")
        params.append(tipo_fornito)

        # Civico può essere None (verrà gestito come NULL nel DB)
        if "civico" in dati_modificati: # Controlla se la chiave 'civico' è presente
            set_clauses.append("civico = %s")
            params.append(dati_modificati["civico"])
        
        # Aggiungi sempre data_modifica
        set_clauses.append("data_modifica = CURRENT_TIMESTAMP")

        # Non dovremmo arrivare qui se nome o tipo sono mancanti a causa dei raise DBDataError precedenti
        # if not set_clauses: # Questo controllo è ridondante se i campi sopra sono obbligatori
        #     self.logger.info(f"update_localita: Nessun campo valido fornito per aggiornare località ID {localita_id} (esclusa data_modifica).")
        #     # Potresti decidere di non fare nulla o sollevare un errore se solo data_modifica deve essere aggiornata.
        #     # Per ora, assumiamo che almeno nome e tipo siano sempre aggiornati.
        #     pass


        query = f"""
            UPDATE {self.schema}.localita
            SET {', '.join(set_clauses)}
            WHERE id = %s;
        """
        params.append(localita_id)
        params_tuple = tuple(params)

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione query UPDATE località ID {localita_id}: {cur.mogrify(query, params_tuple).decode('utf-8', 'ignore')}")
                cur.execute(query, params_tuple)

                if cur.rowcount == 0:
                    # Verifica se la località esiste per distinguere "non trovata" da "dati identici"
                    cur.execute(f"SELECT 1 FROM {self.schema}.localita WHERE id = %s", (localita_id,))
                    if not cur.fetchone():
                        conn.rollback() # Annulla la transazione se non ha fatto nulla
                        self.logger.warning(f"Tentativo di aggiornare località ID {localita_id} non trovata.")
                        raise DBNotFoundError(f"Nessuna località trovata con ID {localita_id} per l'aggiornamento.")
                    # Se la riga esiste ma rowcount è 0, i dati (escl. data_modifica) erano identici.
                    # data_modifica è comunque aggiornata (e PostgreSQL >10 dovrebbe dare rowcount=1).
                    self.logger.info(f"Dati per località ID {localita_id} erano identici o solo data_modifica aggiornata. Righe formalmente modificate: {cur.rowcount}")
                
                conn.commit()
                self.logger.info(f"Località ID {localita_id} aggiornata con successo.")
                # Il successo è l'assenza di eccezioni; nessun return True esplicito necessario.

        except psycopg2.errors.UniqueViolation as uve:
            if conn: conn.rollback()
            constraint_name = getattr(uve.diag, 'constraint_name', "N/D")
            error_detail = getattr(uve, 'pgerror', str(uve))
            self.logger.error(f"Errore di unicità (vincolo: {constraint_name}) aggiornando località ID {localita_id}: {error_detail}")
            # Il vincolo è UNIQUE(comune_id, nome, civico)
            # Ricorda: comune_id non viene modificato qui, quindi il conflitto è su nome/civico nello stesso comune.
            if constraint_name == "localita_comune_id_nome_civico_key": # Verifica il nome esatto del tuo vincolo
                msg = "Una località con lo stesso nome e civico (o assenza di civico) esiste già in questo comune."
            else:
                msg = f"I dati forniti violano un vincolo di unicità (vincolo: {constraint_name})."
            raise DBUniqueConstraintError(msg, constraint_name=constraint_name, details=error_detail) from uve
        
        except psycopg2.errors.CheckViolation as cve:
            if conn: conn.rollback()
            constraint_name = getattr(cve.diag, 'constraint_name', "N/D")
            error_detail = getattr(cve, 'pgerror', str(cve))
            self.logger.error(f"Errore CHECK constraint (vincolo: {constraint_name}) per località ID {localita_id}: {error_detail}")
            if constraint_name == "localita_tipo_check": # Nome del tuo CHECK constraint
                 msg = f"Il 'tipo' di località specificato ('{dati_modificati.get('tipo')}') non è valido."
            else:
                 msg = f"I dati forniti violano una regola di validazione (vincolo: {constraint_name})."
            raise DBDataError(msg) from cve

        except psycopg2.Error as e: # Altri errori DB
            if conn: conn.rollback()
            error_detail = getattr(e, 'pgerror', str(e))
            self.logger.error(f"Errore DB generico aggiornando località ID {localita_id}: {error_detail}", exc_info=True)
            raise DBMError(f"Errore database durante l'aggiornamento della località: {error_detail}") from e
        
        except Exception as e: # Errori Python imprevisti
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore imprevisto Python aggiornando località ID {localita_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto: {e}") from e
        
        finally:
            if conn:
                self._release_connection(conn)

    
    def get_partite_by_comune(self, comune_id: int, filter_text: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = None
        partite_list = []
        
        # Query ottimizzata che usa sotto-query correlate (o LEFT JOIN con COUNT),
        # molto più performante di string_agg per una lista.
        query_base = f"""
            SELECT
                p.id,
                p.numero_partita,
                p.suffisso_partita,
                p.tipo,
                p.stato,
                p.data_impianto,
                (SELECT COUNT(*) FROM {self.schema}.partita_possessore pp WHERE pp.partita_id = p.id) as num_possessori,
                (SELECT COUNT(*) FROM {self.schema}.immobile i WHERE i.partita_id = p.id) as num_immobili,
                (SELECT COUNT(*) FROM {self.schema}.documento_partita dp WHERE dp.partita_id = p.id) as num_documenti_allegati
            FROM {self.schema}.partita p
            WHERE p.comune_id = %s
        """
        params = [comune_id]

        # La logica di filtro va applicata con attenzione.
        # Filtrare su un campo aggregato (come il nome del possessore) richiederebbe di nuovo un JOIN.
        # Per ora, semplifichiamo il filtro ai soli campi della tabella 'partita'.
        if filter_text:
            query_base += """
                AND (
                    CAST(p.numero_partita AS TEXT) ILIKE %s OR
                    p.tipo ILIKE %s OR
                    p.stato ILIKE %s OR
                    p.suffisso_partita ILIKE %s
                )
            """
            filter_like = f"%{filter_text}%"
            params.extend([filter_like, filter_like, filter_like, filter_like])

        query = query_base + " ORDER BY p.numero_partita, p.suffisso_partita;"

        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_partite_by_comune (ottimizzata) per comune_id {comune_id} con filtro '{filter_text}'")
                cur.execute(query, tuple(params))
                partite_list = [dict(row) for row in cur.fetchall()]
                self.logger.info(f"Recuperate {len(partite_list)} partite (query ottimizzata).")
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_partite_by_comune (ottimizzata): {db_err}", exc_info=True)
            raise DBMError(f"Errore database durante il recupero delle partite: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        except Exception as e:
            self.logger.error(f"Errore Python in get_partite_by_comune (ottimizzata): {e}", exc_info=True)
            raise DBMError(f"Errore di sistema durante il recupero delle partite: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
        return partite_list

    def get_partita_details(self, partita_id: int) -> Optional[Dict[str, Any]]:
        """Recupera dettagli completi di una partita, usando il pool e una singola connessione."""
        conn = None
        partita_details: Dict[str, Any] = {}
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Info base partita
                # AGGIUNTO p.suffisso_partita alla SELECT
                query_partita = f"""
                    SELECT p.*, c.nome as comune_nome, c.id as comune_id, p.suffisso_partita 
                    FROM {self.schema}.partita p
                    JOIN {self.schema}.comune c ON p.comune_id = c.id
                    WHERE p.id = %s;
                """
                cur.execute(query_partita, (partita_id,))
                partita_base = cur.fetchone()
                if not partita_base:
                    self.logger.warning(f"Partita ID {partita_id} non trovata in get_partita_details.")
                    return None
                partita_details.update(dict(partita_base))

                # Possessori
                query_poss = f"""
                    SELECT pos.id, pos.nome_completo, pp.titolo, pp.quota
                    FROM {self.schema}.possessore pos 
                    JOIN {self.schema}.partita_possessore pp ON pos.id = pp.possessore_id
                    WHERE pp.partita_id = %s ORDER BY pos.nome_completo;
                """
                cur.execute(query_poss, (partita_id,))
                possessori_results = cur.fetchall()
                partita_details['possessori'] = [dict(row) for row in possessori_results] if possessori_results else []

                # Immobili
                query_imm = f"""
                    SELECT i.id, i.natura, i.numero_piani, i.numero_vani, i.consistenza, i.classificazione,
                           l.nome as localita_nome, l.tipo as localita_tipo, l.civico
                    FROM {self.schema}.immobile i 
                    JOIN {self.schema}.localita l ON i.localita_id = l.id
                    WHERE i.partita_id = %s ORDER BY l.nome, i.natura;
                """
                cur.execute(query_imm, (partita_id,))
                immobili_results = cur.fetchall()
                partita_details['immobili'] = [dict(row) for row in immobili_results] if immobili_results else []

                # Variazioni (e contratti associati)
                # MODIFICA QUI LA QUERY PER INCLUDERE NUMERO PARTITA E NOME COMUNE
                query_var = f"""
                    SELECT 
                        v.*, 
                        con.tipo as tipo_contratto, 
                        con.data_contratto, 
                        con.notaio, 
                        con.repertorio, 
                        con.note as contratto_note,
                        
                        -- Dati per la partita di origine
                        po.numero_partita AS origine_numero_partita,
                        co.nome AS origine_comune_nome,
                        
                        -- Dati per la partita di destinazione
                        pd.numero_partita AS destinazione_numero_partita,
                        cd.nome AS destinazione_comune_nome
                        
                    FROM {self.schema}.variazione v 
                    LEFT JOIN {self.schema}.contratto con ON v.id = con.variazione_id
                    -- JOIN per ottenere il numero di partita e il comune della partita di origine
                    LEFT JOIN {self.schema}.partita po ON v.partita_origine_id = po.id
                    LEFT JOIN {self.schema}.comune co ON po.comune_id = co.id
                    -- JOIN per ottenere il numero di partita e il comune della partita di destinazione
                    LEFT JOIN {self.schema}.partita pd ON v.partita_destinazione_id = pd.id
                    LEFT JOIN {self.schema}.comune cd ON pd.comune_id = cd.id
                    
                    WHERE v.partita_origine_id = %s OR v.partita_destinazione_id = %s
                    ORDER BY v.data_variazione DESC;
                """
                cur.execute(query_var, (partita_id, partita_id))
                variazioni_results = cur.fetchall()
                partita_details['variazioni'] = [dict(row) for row in variazioni_results] if variazioni_results else []
            
            self.logger.info(f"Dettagli completi recuperati per partita ID {partita_id}.")

        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_partita_details (ID: {partita_id}): {db_err}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Errore Python in get_partita_details (ID: {partita_id}): {e}", exc_info=True)
            return None
        finally:
            if conn:
                self._release_connection(conn)
        
        return partita_details if partita_details.get('id') else None

    def update_partita(self, partita_id: int, dati_modificati: Dict[str, Any]):
        """
        Aggiorna i dati di una partita esistente nel database.
        Solleva eccezioni specifiche in caso di errore.
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            raise DBDataError(f"ID partita non valido: {partita_id}")
        if not isinstance(dati_modificati, dict):
            raise DBDataError("Formato dati per l'aggiornamento non valido.")

        set_clauses = []
        params = []
        conn = None

        # Mappa dei campi permessi dalla UI (esclusi quelli che non vogliamo siano modificabili da qui)
        allowed_fields = [
            "numero_partita", "tipo", "stato", 
            "data_impianto", "data_chiusura", "numero_provenienza"
        ]

        for field in allowed_fields:
            if field in dati_modificati:
                set_clauses.append(f"{field} = %s")
                params.append(dati_modificati[field])

        # Gestione specifica e corretta per il suffisso
        if "suffisso_partita" in dati_modificati:
            set_clauses.append("suffisso_partita = %s")
            suffisso_val = dati_modificati.get("suffisso_partita")
            # Controlla se è una stringa prima di usare .strip(), altrimenti passa None
            params.append(suffisso_val.strip() if isinstance(suffisso_val, str) else None)
        
        if not set_clauses:
            self.logger.info(f"update_partita: Nessun campo valido fornito per l'aggiornamento.")
            return # Nessuna modifica da fare

        set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
        params.append(partita_id)
        query = f"UPDATE {self.schema}.partita SET {', '.join(set_clauses)} WHERE id = %s;"
        params_tuple = tuple(params)

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione query UPDATE partita ID {partita_id}: {cur.mogrify(query, params_tuple).decode('utf-8', 'ignore')}")
                cur.execute(query, params_tuple)
                if cur.rowcount == 0:
                    conn.rollback()
                    raise DBNotFoundError(f"Nessuna partita trovata con ID {partita_id} per l'aggiornamento.")
                conn.commit()
                self.logger.info(f"Partita ID {partita_id} aggiornata con successo.")
        except (DBUniqueConstraintError, DBDataError, DBNotFoundError, DBMError) as e:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB gestito aggiornando partita ID {partita_id}: {e}", exc_info=True)
            raise  # Rilancia l'eccezione specifica
        except psycopg2.Error as e_psql:
            if conn: conn.rollback()
            self.logger.error(f"Errore psycopg2 non gestito aggiornando partita ID {partita_id}: {e_psql}", exc_info=True)
            raise DBMError(f"Errore database: {getattr(e_psql, 'pgerror', str(e_psql))}") from e_psql
        except Exception as e_gen:
            if conn: conn.rollback()
            self.logger.error(f"Errore generico aggiornando partita ID {partita_id}: {e_gen}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto: {e_gen}") from e_gen
        finally:
            if conn:
                self._release_connection(conn)

    def update_comune(self, comune_id: int, dati_modificati: Dict[str, Any]) -> bool:
        """
        Aggiorna i dati di un comune esistente.
        Utilizza il pool di connessioni.
        Solleva eccezioni specifiche in caso di errore.
        """
        if not isinstance(comune_id, int) or comune_id <= 0:
            self.logger.error(f"update_comune: comune_id non valido: {comune_id}")
            raise DBDataError(f"ID comune non valido per l'aggiornamento: {comune_id}")

        set_clauses = []
        params = []

        # Mappa dei campi ammessi e nome colonna DB
        allowed_fields_map = {
            "nome": "nome",
            "provincia": "provincia",
            "regione": "regione",
            "codice_catastale": "codice_catastale",
            "periodo_id": "periodo_id",
            "data_istituzione": "data_istituzione",
            "data_soppressione": "data_soppressione",
            "note": "note"
        }

        for key_dict, col_db in allowed_fields_map.items():
            if key_dict in dati_modificati: # Solo se il campo è presente nei dati da modificare
                set_clauses.append(f"{col_db} = %s")
                params.append(dati_modificati[key_dict])
        
        if not set_clauses:
            self.logger.info(f"Nessun campo valido fornito per aggiornare comune ID {comune_id} (esclusa data_modifica).")
            # Non fare nulla se non ci sono campi da aggiornare, oppure aggiorna solo data_modifica
            # Per ora, se non ci sono campi, consideriamo l'operazione "riuscita" senza modifiche.
            return True 

        set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
        params.append(comune_id) # Per la clausola WHERE id = %s

        query = f"UPDATE {self.schema}.comune SET {', '.join(set_clauses)} WHERE id = %s"
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione UPDATE comune ID {comune_id} con query: {cur.mogrify(query, tuple(params)).decode('utf-8', 'ignore')}")
                cur.execute(query, tuple(params))
                if cur.rowcount == 0:
                    cur.execute(f"SELECT 1 FROM {self.schema}.comune WHERE id = %s", (comune_id,))
                    if not cur.fetchone():
                        conn.rollback()
                        raise DBNotFoundError(f"Comune con ID {comune_id} non trovato per l'aggiornamento.")
                    self.logger.info(f"Nessuna modifica effettiva ai dati per comune ID {comune_id} (valori già aggiornati o identici, data_modifica aggiornata).")
                conn.commit()
                self.logger.info(f"Comune ID {comune_id} aggiornato con successo.")
                return True
        except psycopg2.errors.UniqueViolation as uve:
            if conn: conn.rollback()
            constraint = getattr(uve.diag, 'constraint_name', 'N/D')
            msg = f"Impossibile aggiornare il comune: i dati violano un vincolo di unicità (vincolo: {constraint})."
            if "comune_nome_key" in str(constraint).lower() or "comune_nome_unique" in str(constraint).lower(): # Adatta al nome del tuo vincolo
                msg += " Esiste già un comune con lo stesso nome."
            elif "comune_codice_catastale_key" in str(constraint).lower(): # Se hai un UNIQUE su codice_catastale
                msg += " Esiste già un comune con lo stesso codice catastale."
            self.logger.error(f"Errore unicità aggiornando comune ID {comune_id}: {msg}. Dettaglio DB: {getattr(uve, 'pgerror', str(uve))}")
            raise DBUniqueConstraintError(msg, constraint_name=constraint, details=getattr(uve, 'pgerror', str(uve))) from uve
        # Aggiungere gestione per ForeignKeyViolation se periodo_id non valido
        except psycopg2.errors.ForeignKeyViolation as fke:
            if conn: conn.rollback()
            if "comune_periodo_id_fkey" in str(fke): # Adatta al nome del tuo vincolo FK
                msg = f"ID Periodo Storico non valido: {dati_modificati.get('periodo_id')}"
                self.logger.error(msg + f" Dettaglio DB: {getattr(fke, 'pgerror', str(fke))}")
                raise DBDataError(msg) from fke
            raise DBMError(f"Errore di integrità referenziale: {getattr(fke, 'pgerror', str(fke))}") from fke
        except (DBNotFoundError, DBDataError, DBMError) as e_custom:
            if conn: conn.rollback()
            raise e_custom
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB generico aggiornando comune ID {comune_id}: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            raise DBMError(f"Errore database aggiornando comune: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python imprevisto aggiornando comune ID {comune_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto aggiornando comune: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
    
    def update_possessore(self, possessore_id: int, dati_modificati: Dict[str, Any]):
        """
        Aggiorna i dati di un possessore esistente nel database.
        Solleva eccezioni specifiche in caso di errore.

        Args:
            possessore_id: L'ID del possessore da aggiornare.
            dati_modificati: Un dizionario contenente i campi del possessore da aggiornare.
                             Campi attesi e gestiti: 'nome_completo', 'cognome_nome', 
                             'paternita', 'attivo', 'comune_riferimento_id'.

        Raises:
            DBDataError: Se possessore_id o dati_modificati non sono validi, o se mancano campi obbligatori.
            DBNotFoundError: Se il possessore con l'ID specificato non viene trovato.
            DBUniqueConstraintError: Se l'aggiornamento viola un vincolo di unicità.
            DBMError: Per altri errori generici del database.
        """
        self.logger.info(f"DEBUG: update_possessore (DBManager) chiamato per ID {possessore_id} con dati: {dati_modificati}") # NUOVA STAMPA
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            self.logger.error(f"update_possessore: possessore_id non valido: {possessore_id}")
            raise DBDataError(f"ID possessore non valido: {possessore_id}")
        if not isinstance(dati_modificati, dict):
            self.logger.error(f"update_possessore: dati_modificati non è un dizionario per possessore ID {possessore_id}.")
            raise DBDataError("Formato dati per l'aggiornamento non valido.")

        set_clauses = []
        params = []
        conn = None

        # Mappa dei campi permessi e se sono obbligatori per l'UPDATE (non nullabili nel DB)
        # (nome_campo_dict, nome_colonna_db, is_required_in_dict_for_update)
        # Nota: 'comune_id' nella tabella possessore è NOT NULL
        allowed_fields = {
            "nome_completo": ("nome_completo", True),
            "cognome_nome": ("cognome_nome", False), # Può essere NULL nel DB
            "paternita": ("paternita", False),       # Può essere NULL nel DB
            "attivo": ("attivo", True),
            "comune_riferimento_id": ("comune_id", True),
        }

        for key_dict, (col_db, is_required) in allowed_fields.items():
            if key_dict in dati_modificati:
                if dati_modificati[key_dict] is None and not is_required and key_dict not in ["cognome_nome", "paternita"]: # cognome_nome e paternita possono essere NULL
                     # Per i campi opzionali che possono essere NULL nel DB, se il valore è None, lo impostiamo
                    set_clauses.append(f"{col_db} = %s")
                    params.append(None)
                elif dati_modificati[key_dict] is not None:
                    set_clauses.append(f"{col_db} = %s")
                    params.append(dati_modificati[key_dict])
                elif is_required: # Se è richiesto e None, è un errore di dati
                    self.logger.error(f"update_possessore: Campo obbligatorio '{key_dict}' è None per possessore ID {possessore_id}.")
                    raise DBDataError(f"Il campo '{key_dict}' è obbligatorio e non può essere nullo.")
            elif is_required: # Se un campo richiesto manca completamente dal dizionario
                self.logger.error(f"update_possessore: Campo obbligatorio '{key_dict}' mancante nei dati da aggiornare per possessore ID {possessore_id}.")
                raise DBDataError(f"Il campo '{key_dict}' è obbligatorio per l'aggiornamento.")

        if not set_clauses:
            self.logger.info(f"update_possessore: Nessun campo valido fornito per l'aggiornamento del possessore ID {possessore_id} (esclusa data_modifica).")
            # Aggiorniamo comunque data_modifica
            set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
        else:
            set_clauses.append("data_modifica = CURRENT_TIMESTAMP")

        query = f"""
            UPDATE {self.schema}.possessore
            SET {', '.join(set_clauses)}
            WHERE id = %s;
        """
        params.append(possessore_id) # Aggiungi possessore_id per la clausola WHERE
        params_tuple = tuple(params)

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione query UPDATE possessore ID {possessore_id}: {cur.mogrify(query, params_tuple).decode('utf-8', 'ignore')}")
                cur.execute(query, params_tuple)

                if cur.rowcount == 0:
                    cur.execute(f"SELECT 1 FROM {self.schema}.possessore WHERE id = %s", (possessore_id,))
                    if not cur.fetchone():
                        conn.rollback()
                        self.logger.warning(f"Tentativo di aggiornare possessore ID {possessore_id} non trovato.")
                        raise DBNotFoundError(f"Nessun possessore trovato con ID {possessore_id} per l'aggiornamento.")
                    # Se la riga esiste ma rowcount è 0, i dati erano identici (data_modifica si aggiorna comunque)
                    self.logger.info(f"Dati per possessore ID {possessore_id} erano identici o solo data_modifica aggiornata. Righe formalmente modificate: {cur.rowcount}")
                
                conn.commit()
                self.logger.info(f"Possessore ID {possessore_id} aggiornato con successo (righe affette potrebbero includere solo data_modifica).")

        except psycopg2.errors.UniqueViolation as uve:
            if conn: conn.rollback()
            constraint_name = getattr(uve.diag, 'constraint_name', "N/D")
            error_detail = getattr(uve, 'pgerror', str(uve))
            self.logger.error(f"Errore di violazione di unicità (vincolo: {constraint_name}) durante l'aggiornamento del possessore ID {possessore_id}: {error_detail}")
            # Adatta il messaggio se hai vincoli di unicità specifici su possessore (es. nome_completo+comune_id)
            msg = f"I dati forniti violano un vincolo di unicità (es. nome duplicato, vincolo: {constraint_name})."
            raise DBUniqueConstraintError(msg, constraint_name=constraint_name, details=error_detail) from uve
        
        except psycopg2.errors.ForeignKeyViolation as fke: # Es. se comune_riferimento_id non esiste
            if conn: conn.rollback()
            constraint_name = getattr(fke.diag, 'constraint_name', "N/D")
            error_detail = getattr(fke, 'pgerror', str(fke))
            self.logger.error(f"Violazione Foreign Key (vincolo: {constraint_name}) per possessore ID {possessore_id}: {error_detail}")
            if constraint_name == "possessore_comune_id_fkey": # Nome del tuo vincolo FK
                 msg = "Il comune di riferimento specificato non esiste."
            else:
                 msg = f"Impossibile aggiornare il possessore: errore di riferimento a dati esterni (vincolo: {constraint_name})."
            raise DBMError(msg) from fke # O una DBForeignKeyError specifica

        except psycopg2.Error as e:
            if conn: conn.rollback()
            error_detail = getattr(e, 'pgerror', str(e))
            self.logger.error(f"Errore DB generico durante l'aggiornamento del possessore ID {possessore_id}: {error_detail}", exc_info=True)
            raise DBMError(f"Errore database durante l'aggiornamento del possessore: {error_detail}") from e
        
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore imprevisto Python durante l'aggiornamento del possessore ID {possessore_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante l'aggiornamento: {e}") from e
        
        finally:
            if conn:
                self._release_connection(conn)
    
    # All'interno della classe CatastoDBManager in catasto_db_manager.py

    # All'interno della classe CatastoDBManager in catasto_db_manager.py

    def search_partite(self, comune_id: Optional[int] = None, numero_partita: Optional[int] = None,
                       possessore: Optional[str] = None, immobile_natura: Optional[str] = None,
                       suffisso_partita: Optional[str] = None) -> List[Dict[str, Any]]: # NUOVO PARAMETRO
        """
        Ricerca partite con filtri multipli.
        Utilizza il pool di connessioni e formatta i risultati come lista di dizionari.
        """
        conn = None  # Inizializza la variabile di connessione
        # AGGIUNTO p.suffisso_partita alla SELECT
         
        try:
            conditions = []
            params = []
            current_joins_str = "" # Stringa per accumulare i JOIN necessari

            # Colonne selezionate e tabella base (partita SEMPRE joinata con comune)
            # AGGIUNTO p.suffisso_partita alla SELECT
            select_cols = "p.id, c.nome as comune_nome, p.numero_partita, p.suffisso_partita, p.tipo, p.stato" 
            query_base = f"SELECT DISTINCT {select_cols} FROM {self.schema}.partita p JOIN {self.schema}.comune c ON p.comune_id = c.id"

            if possessore:
                join_possessore_str = f" JOIN {self.schema}.partita_possessore pp ON p.id = pp.partita_id JOIN {self.schema}.possessore pos ON pp.possessore_id = pos.id"
                if join_possessore_str not in current_joins_str: # Evita di aggiungere lo stesso JOIN più volte
                    current_joins_str += join_possessore_str
                conditions.append("pos.nome_completo ILIKE %s")
                params.append(f"%{possessore}%")

            if immobile_natura:
                join_immobile_str = f" JOIN {self.schema}.immobile i ON p.id = i.partita_id"
                if join_immobile_str not in current_joins_str:
                    current_joins_str += join_immobile_str
                conditions.append("i.natura ILIKE %s")
                params.append(f"%{immobile_natura}%")

            if comune_id is not None:
                conditions.append("p.comune_id = %s")
                params.append(comune_id)

            if numero_partita is not None:
                conditions.append("p.numero_partita = %s")
                params.append(numero_partita)
            # Aggiunto il filtro per suffisso_partita
            if suffisso_partita is not None: # Se l'utente ha fornito un suffisso (anche vuoto per cercare NULL)
                if suffisso_partita.strip() == "": # Cerca quelli con suffisso NULL
                    conditions.append("p.suffisso_partita IS NULL")
                else: # Cerca un suffisso specifico
                    conditions.append("p.suffisso_partita ILIKE %s")
                    params.append(f"%{suffisso_partita.strip()}%")

            # Costruzione finale della query
            query = query_base + current_joins_str # Aggiunge tutti i join necessari
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY c.nome, p.numero_partita"

            # Logging della query e dei parametri (fondamentale per il debug)
            self.logger.debug(f"CatastoDBManager.search_partite - Query: {query} - Params: {tuple(params)}")

            conn = self._get_connection() # Ottiene una connessione dal pool
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur: # Usa DictCursor per risultati come dizionari
                cur.execute(query, tuple(params)) # Passa i parametri come tupla
                results_raw = cur.fetchall()
                
                # Log dei risultati grezzi per debug (opzionale, ma utile)
                # self.logger.debug(f"CatastoDBManager.search_partite - Raw results from DB: {results_raw}")
                
                results_list_of_dicts = [dict(row) for row in results_raw] if results_raw else []
                self.logger.info(f"CatastoDBManager.search_partite - Trovate {len(results_list_of_dicts)} partite.")
                return results_list_of_dicts

        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in search_partite: {db_err}", exc_info=True)
            if conn: conn.rollback() # Importante per errori transazionali
        except Exception as e:
            self.logger.error(f"Errore Python generico in search_partite: {e}", exc_info=True)
            if conn: conn.rollback() # Anche qui, per sicurezza
        finally:
            if conn:
                self._release_connection(conn) # Rilascia SEMPRE la connessione al pool
        return [] # Restituisce lista vuota in caso di errore o nessun risultato

    def search_immobili(self, partita_id: Optional[int] = None, comune_id: Optional[int] = None, # Usa comune_id
                        localita_id: Optional[int] = None, natura: Optional[str] = None,
                        classificazione: Optional[str] = None) -> List[Dict]:
        """Chiama la funzione SQL cerca_immobili (MODIFICATA per comune_id)."""
        try:
            # Funzione SQL aggiornata per comune_id
            query = "SELECT * FROM cerca_immobili(%s, %s, %s, %s, %s)"
            params = (partita_id, comune_id, localita_id, natura, classificazione) # Passa ID
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in search_immobili: {db_err}")
        except Exception as e: logger.error(f"Errore Python in search_immobili: {e}")
        return []

    def search_variazioni(self, tipo: Optional[str] = None, data_inizio: Optional[date] = None,
                          data_fine: Optional[date] = None, partita_origine_id: Optional[int] = None,
                          partita_destinazione_id: Optional[int] = None, comune_id: Optional[int] = None) -> List[Dict]: # Usa comune_id
        """Chiama la funzione SQL cerca_variazioni (MODIFICATA per comune_id)."""
        try:
            # Funzione SQL aggiornata per comune_id
            query = "SELECT * FROM cerca_variazioni(%s, %s, %s, %s, %s, %s)"
            params = (tipo, data_inizio, data_fine, partita_origine_id, partita_destinazione_id, comune_id) # Passa ID
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in search_variazioni: {db_err}")
        except Exception as e: logger.error(f"Errore Python in search_variazioni: {e}")
        return []

    def search_consultazioni(self, data_inizio: Optional[date] = None, data_fine: Optional[date] = None,
                             richiedente: Optional[str] = None, funzionario: Optional[str] = None) -> List[Dict]:
        """Chiama la funzione SQL cerca_consultazioni (invariata rispetto a comune_id)."""
        try:
            query = "SELECT * FROM cerca_consultazioni(%s, %s, %s, %s)"
            params = (data_inizio, data_fine, richiedente, funzionario)
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in search_consultazioni: {db_err}")
        except Exception as e: logger.error(f"Errore Python in search_consultazioni: {e}")
        return []

    # --- Metodi CRUD specifici (invariati rispetto a comune_id) ---
    def update_immobile(self, immobile_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_immobile."""
        params = {'p_id': immobile_id, 'p_natura': kwargs.get('natura'), 'p_numero_piani': kwargs.get('numero_piani'),
                  'p_numero_vani': kwargs.get('numero_vani'), 'p_consistenza': kwargs.get('consistenza'),
                  'p_classificazione': kwargs.get('classificazione'), 'p_localita_id': kwargs.get('localita_id')}
        call_proc = "CALL aggiorna_immobile(%(p_id)s, %(p_natura)s, %(p_numero_piani)s, %(p_numero_vani)s, %(p_consistenza)s, %(p_classificazione)s, %(p_localita_id)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Immobile ID {immobile_id} aggiornato."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB aggiornamento immobile ID {immobile_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python aggiornamento immobile ID {immobile_id}: {e}"); self.rollback(); return False

    def delete_immobile(self, immobile_id):
        """
        Elimina un immobile dal database utilizzando una procedura memorizzata
        e gestendo la transazione in modo sicuro con il connection pool.
        """
        call_proc = "SELECT public.delete_immobile_by_id(%s);"
        conn = None  # Inizializza la variabile della connessione
        try:
            # 1. Ottieni una connessione dal pool
            conn = self.pool.getconn()
            
            # 2. Utilizza la connessione con un blocco 'with' per il cursore
            with conn.cursor() as cur:
                # 3. Esegui la query/procedura sul cursore
                cur.execute(call_proc, (immobile_id,))
                
                # 4. Esegui il commit sulla connessione
                conn.commit()
                
                logger.info(f"Immobile ID {immobile_id} eliminato con successo.")
                return True
                
        except Exception as e:
            # Se si verifica un errore, esegui il rollback
            if conn:
                conn.rollback()
            logger.error(f"Errore durante l'eliminazione dell'immobile ID {immobile_id}: {e}")
            return False
            
        finally:
            # 5. Rilascia SEMPRE la connessione al pool
            if conn:
                self.pool.putconn(conn)
    def update_variazione(self, variazione_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_variazione."""
        params = {'p_variazione_id': variazione_id, 'p_tipo': kwargs.get('tipo'), 'p_data_variazione': kwargs.get('data_variazione'),
                  'p_numero_riferimento': kwargs.get('numero_riferimento'), 'p_nominativo_riferimento': kwargs.get('nominativo_riferimento')}
        call_proc = "CALL aggiorna_variazione(%(p_variazione_id)s, %(p_tipo)s, %(p_data_variazione)s, %(p_numero_riferimento)s, %(p_nominativo_riferimento)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Variazione ID {variazione_id} aggiornata."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB aggiornamento variazione ID {variazione_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python aggiornamento variazione ID {variazione_id}: {e}"); self.rollback(); return False

    def delete_variazione(self, variazione_id: int, force: bool = False, restore_partita: bool = False) -> bool:
        """Chiama la procedura SQL elimina_variazione."""
        call_proc = "CALL elimina_variazione(%s, %s, %s)"
        try:
            if self.execute_query(call_proc, (variazione_id, force, restore_partita)): self.commit(); logger.info(f"Variazione ID {variazione_id} eliminata."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB eliminazione variazione ID {variazione_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python eliminazione variazione ID {variazione_id}: {e}"); self.rollback(); return False

    def insert_contratto(self, variazione_id: int, tipo: str, data_contratto: date,
                         notaio: Optional[str] = None, repertorio: Optional[str] = None,
                         note: Optional[str] = None) -> bool:
        """Chiama la procedura SQL inserisci_contratto."""
        call_proc = "CALL inserisci_contratto(%s, %s, %s, %s, %s, %s)"
        params = (variazione_id, tipo, data_contratto, notaio, repertorio, note)
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Contratto inserito per variazione ID {variazione_id}."); return True
            return False
        except psycopg2.Error as db_err:
        # --- INIZIO CORREZIONE ---
        # Verifica se è l'eccezione specifica di contratto duplicato sollevata dalla procedura
        # Controlla il codice SQLSTATE ('P0001' per raise_exception) E il messaggio
            if hasattr(db_err, 'pgcode') and db_err.pgcode == 'P0001' and 'Esiste già un contratto' in str(db_err):
                logger.warning(f"Contratto per variazione ID {variazione_id} esiste già.")
            # --- FINE CORREZIONE ---
            else:
                # Logga altri errori DB generici
                logger.error(f"Errore DB inserimento contratto var ID {variazione_id}: {db_err}")
                # Potresti voler loggare anche db_err.pgcode e db_err.pgerror qui per più dettagli
                # logger.error(f"SQLSTATE: {db_err.pgcode} - Errore: {db_err.pgerror}")
            # In entrambi i casi (duplicato o altro errore DB), ritorna False
        return False
    def update_contratto(self, contratto_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_contratto."""
        params = {'p_id': contratto_id, 'p_tipo': kwargs.get('tipo'), 'p_data_contratto': kwargs.get('data_contratto'),
                  'p_notaio': kwargs.get('notaio'), 'p_repertorio': kwargs.get('repertorio'), 'p_note': kwargs.get('note')}
        call_proc = "CALL aggiorna_contratto(%(p_id)s, %(p_tipo)s, %(p_data_contratto)s, %(p_notaio)s, %(p_repertorio)s, %(p_note)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Contratto ID {contratto_id} aggiornato."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB aggiornamento contratto ID {contratto_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python aggiornamento contratto ID {contratto_id}: {e}"); self.rollback(); return False

    def delete_contratto(self, contratto_id: int) -> bool:
        """Chiama la procedura SQL elimina_contratto."""
        call_proc = "CALL elimina_contratto(%s)"
        try:
            if self.execute_query(call_proc, (contratto_id,)): self.commit(); logger.info(f"Contratto ID {contratto_id} eliminato."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB eliminazione contratto ID {contratto_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python eliminazione contratto ID {contratto_id}: {e}"); self.rollback(); return False

    def update_consultazione(self, consultazione_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_consultazione."""
        params = {'p_id': consultazione_id, 'p_data': kwargs.get('data'), 'p_richiedente': kwargs.get('richiedente'),
                  'p_documento_identita': kwargs.get('documento_identita'), 'p_motivazione': kwargs.get('motivazione'),
                  'p_materiale_consultato': kwargs.get('materiale_consultato'), 'p_funzionario_autorizzante': kwargs.get('funzionario_autorizzante')}
        call_proc = "CALL aggiorna_consultazione(%(p_id)s, %(p_data)s, %(p_richiedente)s, %(p_documento_identita)s, %(p_motivazione)s, %(p_materiale_consultato)s, %(p_funzionario_autorizzante)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Consultazione ID {consultazione_id} aggiornata."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB aggiornamento consultazione ID {consultazione_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python aggiornamento consultazione ID {consultazione_id}: {e}"); self.rollback(); return False

    def delete_consultazione(self, consultazione_id: int) -> bool:
        """Chiama la procedura SQL elimina_consultazione."""
        call_proc = "CALL elimina_consultazione(%s)"
        try:
            if self.execute_query(call_proc, (consultazione_id,)): self.commit(); logger.info(f"Consultazione ID {consultazione_id} eliminata."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB eliminazione consultazione ID {consultazione_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python eliminazione consultazione ID {consultazione_id}: {e}"); self.rollback(); return False

    # --- Metodi per Workflow Complessi (MODIFICATI per comune_id) ---

    # All'interno della classe CatastoDBManager in catasto_db_manager.py
    def registra_nuova_consultazione(self,
                                     data_consultazione: date,      # Corrisponde a 'data'
                                     richiedente: str,
                                     materiale_consultato: str,     # Obbligatorio nella UI
                                     funzionario_autorizzante: Optional[str], # Testo per la colonna VARCHAR
                                     documento_identita: Optional[str] = None,
                                     motivazione: Optional[str] = None
                                     ) -> Optional[int]: # Restituisce l'ID della consultazione o None
        """
        Registra una nuova consultazione nel database.
        Utilizza il pool di connessioni. Adattato alla struttura tabella fornita.
        """
        if not all([data_consultazione, richiedente, materiale_consultato]): # Materiale reso obbligatorio dalla UI
            self.logger.error("registra_nuova_consultazione: Campi obbligatori (data, richiedente, materiale) mancanti.")
            # Solleva eccezione che la UI può intercettare
            raise DBDataError("Data, Richiedente e Materiale Consultato sono campi obbligatori.")

        # Le colonne data_creazione e data_modifica hanno default CURRENT_TIMESTAMP
        query = f"""
            INSERT INTO {self.schema}.consultazione
                (data, richiedente, documento_identita,
                 motivazione, materiale_consultato, funzionario_autorizzante)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        params = (
            data_consultazione,
            richiedente.strip(),
            documento_identita.strip() if documento_identita else None,
            motivazione.strip() if motivazione else None,
            materiale_consultato.strip(),
            funzionario_autorizzante.strip() if funzionario_autorizzante else None
        )
        
        conn = None
        new_consultazione_id = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione registra_nuova_consultazione per richiedente: {richiedente}")
                cur.execute(query, params)
                result = cur.fetchone()
                if result and result[0] is not None:
                    new_consultazione_id = result[0]
                    conn.commit()
                    self.logger.info(f"Nuova consultazione registrata con successo. ID: {new_consultazione_id}")
                else:
                    conn.rollback()
                    self.logger.error("Registrazione consultazione fallita: nessun ID restituito dopo INSERT.")
                    raise DBMError("Fallimento registrazione consultazione: nessun ID restituito.")
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB in registra_nuova_consultazione: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            raise DBMError(f"Errore database: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python in registra_nuova_consultazione: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
        
        return new_consultazione_id
    # In catasto_db_manager.py, all'interno della classe CatastoDBManager

    def registra_nuova_proprieta(self, comune_id: int, numero_partita: int, data_impianto: date,
                                 possessori_json_str: str,
                                 immobili_json_str: str,
                                 suffisso_partita: Optional[str] = None
                                ) -> Optional[int]:
        """
        Chiama la procedura SQL catasto.registra_nuova_proprieta per registrare una nuova proprietà.
        """
        # Validazioni input base
        # ... (le validazioni iniziali restano invariate) ...
        if not (isinstance(comune_id, int) and comune_id > 0):
            raise DBDataError("Parametro 'comune_id' non valido.")
        if not (isinstance(numero_partita, int) and numero_partita > 0):
            raise DBDataError("Parametro 'numero_partita' non valido.")
        if not isinstance(data_impianto, date):
            msg = "Parametro 'data_impianto' non valido (deve essere un oggetto date)."
            self.logger.error(f"registra_nuova_proprieta: {msg}")
            raise DBDataError(msg)
        
        # Validazione JSON strings
        try:
            # Controllo solo la validità del JSON, il contenuto verrà processato dalla procedura SQL
            json.loads(possessori_json_str) 
            json.loads(immobili_json_str)   
        except json.JSONDecodeError as je:
            msg = f"Dati possessori o immobili non sono in formato JSON valido: {je}"
            self.logger.error(f"registra_nuova_proprieta: {msg}")
            raise DBDataError(msg) from je
        
        # Normalizza suffisso_partita: stringa vuota o solo spazi diventano None (NULL nel DB)
        actual_suffisso_partita = suffisso_partita.strip() if isinstance(suffisso_partita, str) and suffisso_partita.strip() else None

        conn = None
        new_partita_id: Optional[int] = None
        
        # --- Chiamata alla Procedura SQL aggiornata ---
        # La procedura SQL 'catasto.registra_nuova_proprieta' deve accettare 6 parametri
        # (comune_id, numero_partita, data_impianto, possessori_json, immobili_json, suffisso_partita)
        # La procedura stessa gestirà la validazione di unicità e l'inserimento.
         # --- MODIFICA CHIAVE QUI ---
        # Aggiungiamo il cast esplicito ::TEXT al sesto parametro
        call_proc = f"CALL {self.schema}.registra_nuova_proprieta(%s, %s, %s, %s::jsonb, %s::jsonb, %s::TEXT);"
        params = (comune_id, numero_partita, data_impianto, possessori_json_str, immobili_json_str, actual_suffisso_partita)
       
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Chiamata procedura {self.schema}.registra_nuova_proprieta per C:{comune_id}, N:{numero_partita}, Suffisso:'{actual_suffisso_partita}'")
                self.logger.debug(f"SQL CALL: {cur.mogrify(call_proc, params).decode('utf-8','ignore')}")
                cur.execute(call_proc, params)
                
                # La logica per recuperare l'ID della nuova partita dopo la CALL rimane invariata
                query_select_id = f"""
                    SELECT id FROM {self.schema}.partita 
                    WHERE comune_id = %s 
                      AND numero_partita = %s 
                      AND (suffisso_partita = %s OR (suffisso_partita IS NULL AND %s IS NULL))
                    ORDER BY data_creazione DESC, id DESC LIMIT 1; 
                """
                cur.execute(query_select_id, (comune_id, numero_partita, actual_suffisso_partita, actual_suffisso_partita))
                result = cur.fetchone()

                if result and result['id']:
                    new_partita_id = result['id']
                    conn.commit()
                    self.logger.info(f"Nuova proprietà registrata. Partita ID: {new_partita_id}.")
                else:
                    conn.rollback()
                    self.logger.error(f"Fallimento nel recuperare l'ID della nuova partita dopo la registrazione (C:{comune_id}, N:{numero_partita}).")
                    raise DBMError("Registrazione partita completata, ma impossibile recuperare l'ID della nuova partita.")
        
            return new_partita_id

        # La gestione delle eccezioni rimane invariata
        except psycopg2.errors.UndefinedFunction as udf_err:
            if conn: conn.rollback()
            self.logger.error(f"La procedura SQL '{self.schema}.registra_nuova_proprieta' non esiste: {getattr(udf_err.diag, 'message', str(udf_err))}", exc_info=True)
            raise DBMError(f"Procedura SQL non trovata o firma errata: {getattr(udf_err.diag, 'message', str(udf_err))}") from udf_err
        
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            if conn: conn.rollback()
            raise e
        
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.critical(f"Errore Python in registra_nuova_proprieta: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto: {e}") from e
        
        finally:
            if conn:
                self._release_connection(conn)
    
    def registra_passaggio_proprieta(self, 
                                         partita_origine_id: int, 
                                         comune_id_nuova_partita: int, 
                                         numero_nuova_partita: int,    
                                         tipo_variazione: str, 
                                         data_variazione: date, 
                                         tipo_contratto: str, 
                                         data_contratto: date,
                                         notaio: Optional[str] = None, 
                                         repertorio: Optional[str] = None,
                                         nuovi_possessori_list: Optional[List[Dict[str, Any]]] = None, 
                                         immobili_da_trasferire_ids: Optional[List[int]] = None, 
                                         note_variazione: Optional[str] = None,
                                         suffisso_nuova_partita: Optional[str] = None # NUOVO PARAMETRO
                                        ) -> bool:
        """
        Chiama la procedura SQL catasto.registra_passaggio_proprieta.
        La procedura SQL dovrà essere aggiornata per accettare un suffisso per la nuova partita.
        """
        conn = None
        try:
            nuovi_possessori_jsonb = json.dumps(nuovi_possessori_list) if nuovi_possessori_list else None
            
            # Assicurati che il nome della procedura e dello schema siano corretti.
            # La procedura SQL dovrà accettare questo parametro aggiuntivo.
            call_proc_str = f"CALL {self.schema}.registra_passaggio_proprieta(" \
                            f"%s, %s, %s, %s, " \
                            f"%s::TEXT, %s::DATE, " \
                            f"%s::TEXT, %s::DATE, " \
                            f"%s::TEXT, %s::TEXT, " \
                            f"%s::JSON, %s::INTEGER[], " \
                            f"%s::TEXT, %s::TEXT);" # AGGIUNTO UN %s PER IL SUFFISSO E SUO TIPO
            #     ^part_orig     ^com_nuova    ^num_nuova    ^suffisso_nuova_partita (NUOVO)
            #                  ^tipo_var    ^data_var
            #                               ^tipo_contr  ^data_contr
            #                                            ^notaio      ^repertorio
            #                                                         ^nuovi_poss (ORA ::JSON)  ^imm_da_trasf (INTEGER[])
            #                                                                                     ^note_var (TEXT)

            params = (
                partita_origine_id,
                comune_id_nuova_partita,
                numero_nuova_partita,
                suffisso_nuova_partita, # AGGIUNTO
                tipo_variazione,
                data_variazione,
                tipo_contratto,
                data_contratto,
                notaio,
                repertorio,
                nuovi_possessori_jsonb,
                immobili_da_trasferire_ids,
                note_variazione
            )
            
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.info(f"Tentativo di registrare passaggio proprietà da Partita ID {partita_origine_id} "
                                 f"a Nuova Partita N.{numero_nuova_partita} (Comune ID: {comune_id_nuova_partita}).")
                # Il logging dei params può essere molto verboso con il JSON, considera di loggare solo alcune parti.
                # self.logger.debug(f"Parametri per registra_passaggio_proprieta: {params}") 
                cur.execute(call_proc_str, params)
                conn.commit()
                self.logger.info("Passaggio di proprietà registrato con successo tramite procedura.")
                return True
        except psycopg2.Error as db_err: # Cattura errori specifici del database
            if conn: conn.rollback()
            pgerror_msg = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB durante registrazione passaggio proprietà da Partita ID {partita_origine_id}: {pgerror_msg}", exc_info=True)
            # Solleva un'eccezione più specifica se la procedura SQL usa RAISE EXCEPTION con codici definiti
            raise DBMError(f"Errore database durante la registrazione del passaggio di proprietà: {pgerror_msg}") from db_err
        except Exception as e: # Cattura altri errori Python (es. errore di serializzazione JSON se non gestito prima)
            if conn: conn.rollback()
            self.logger.error(f"Errore Python imprevisto durante registrazione passaggio proprietà da Partita ID {partita_origine_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante la registrazione del passaggio: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
        # return False # Non dovrebbe essere raggiunto se le eccezioni sono gestite
    def registra_consultazione(self, data: date, richiedente: str, documento_identita: Optional[str],
                             motivazione: Optional[str], materiale_consultato: Optional[str],
                             funzionario_autorizzante: Optional[str]) -> bool:
        """Chiama la procedura SQL registra_consultazione (invariata rispetto a comune_id)."""
        try:
            call_proc = "CALL registra_consultazione(%s, %s, %s, %s, %s, %s)"
            params = (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante)
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Registrata consultazione: Richiedente '{richiedente}', Data {data}"); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB registrazione consultazione: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python registrazione consultazione: {e}"); self.rollback(); return False

    def duplicate_partita(self, partita_id_originale: int, nuovo_numero_partita: int,
                              mantenere_possessori: bool = True, mantenere_immobili: bool = False,
                              nuovo_suffisso: Optional[str] = None # NUOVO PARAMETRO
                             ) -> bool:
        """
        Chiama la procedura SQL per duplicare una partita (es. catasto.duplica_partita).
        La procedura SQL dovrà essere aggiornata per accettare un suffisso per la nuova partita.
        """
        # Assumiamo che la procedura SQL catasto.duplica_partita accetti un suffisso
        call_proc_str = f"CALL {self.schema}.duplica_partita(%s, %s, %s, %s, %s);" # AGGIUNTO %s
        params = (partita_id_originale, nuovo_numero_partita, mantenere_possessori, mantenere_immobili, nuovo_suffisso) # AGGIUNTO nuovo_suffisso
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.info(f"Tentativo di duplicare partita ID {partita_id_originale} in Nuovo Numero Partita {nuovo_numero_partita}. "
                                 f"Mantieni Possessori: {mantenere_possessori}, Mantieni Immobili: {mantenere_immobili}")
                cur.execute(call_proc_str, params)
                conn.commit()
                self.logger.info(f"Partita ID {partita_id_originale} duplicata con successo in Nuovo Numero Partita {nuovo_numero_partita}.")
                return True
        except psycopg2.Error as db_err: # Cattura errori specifici del database
            if conn: conn.rollback()
            pgerror_msg = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB durante duplicazione partita ID {partita_id_originale}: {pgerror_msg}", exc_info=True)
            # Potrebbe sollevare eccezioni più specifiche basate su db_err.pgcode se la procedura SQL li usa
            raise DBMError(f"Errore database durante la duplicazione della partita: {pgerror_msg}") from db_err
        except Exception as e: # Cattura altri errori Python
            if conn: conn.rollback()
            self.logger.error(f"Errore Python imprevisto durante duplicazione partita ID {partita_id_originale}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante la duplicazione: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
        # return False # Non dovrebbe essere raggiunto se le eccezioni sono gestite

    def transfer_immobile(self, immobile_id: int, nuova_partita_id: int, registra_variazione: bool = False) -> bool:
        """
        Chiama la procedura SQL per trasferire un immobile a una nuova partita (es. catasto.trasferisci_immobile).
        Utilizza il pool di connessioni e gestisce commit/rollback.
        Restituisce True in caso di successo, altrimenti solleva un'eccezione.
        """
        call_proc_str = f"CALL {self.schema}.trasferisci_immobile(%s, %s, %s);"
        params = (immobile_id, nuova_partita_id, registra_variazione)
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.info(f"Tentativo di trasferire immobile ID {immobile_id} a partita ID {nuova_partita_id}. "
                                 f"Registra variazione: {registra_variazione}")
                cur.execute(call_proc_str, params)
                conn.commit()
                self.logger.info(f"Immobile ID {immobile_id} trasferito con successo a partita ID {nuova_partita_id}.")
                return True
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            pgerror_msg = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB durante trasferimento immobile ID {immobile_id}: {pgerror_msg}", exc_info=True)
            raise DBMError(f"Errore database durante il trasferimento dell'immobile: {pgerror_msg}") from db_err
        except Exception as e:
            if conn: conn.rollback()
            self.logger.error(f"Errore Python imprevisto durante trasferimento immobile ID {immobile_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante il trasferimento dell'immobile: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
        # return False # Non dovrebbe essere raggiunto
    # --- Metodi di Reportistica (MODIFICATI dove serve join per nome) ---

    # All'interno della classe CatastoDBManager in catasto_db_manager.py

    def genera_report_proprieta(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL catasto.genera_report_proprieta(%s), usando il pool."""
        if not isinstance(partita_id, int) or partita_id <= 0:
            self.logger.error(f"genera_report_proprieta: ID partita non valido: {partita_id}")
            return None
        
        conn = None
        try:
            query = f"SELECT {self.schema}.genera_report_proprieta(%s) AS report_text;" # Assicurati che la funzione SQL esista
            conn = self._get_connection()
            with conn.cursor() as cur: # Non serve DictCursor se la funzione restituisce un singolo valore testuale
                self.logger.debug(f"Esecuzione genera_report_proprieta per ID partita: {partita_id}")
                cur.execute(query, (partita_id,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    self.logger.info(f"Report di proprietà generato per partita ID {partita_id}.")
                    return str(result[0]) # La funzione SQL restituisce testo
                else:
                    self.logger.warning(f"Nessun report generato per partita ID {partita_id} o risultato NULL.")
                    return None
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in genera_report_proprieta (ID: {partita_id}): {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python in genera_report_proprieta (ID: {partita_id}): {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return None

    def genera_report_genealogico(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL catasto.genera_report_genealogico(%s), usando il pool."""
        if not isinstance(partita_id, int) or partita_id <= 0:
            self.logger.error(f"genera_report_genealogico: ID partita non valido: {partita_id}")
            return None

        conn = None
        try:
            query = f"SELECT {self.schema}.genera_report_genealogico(%s) AS report_text;" # Assicurati che la funzione SQL esista
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione genera_report_genealogico per ID partita: {partita_id}")
                cur.execute(query, (partita_id,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    self.logger.info(f"Report genealogico generato per partita ID {partita_id}.")
                    return str(result[0])
                else:
                    self.logger.warning(f"Nessun report genealogico generato per partita ID {partita_id} o risultato NULL.")
                    return None
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in genera_report_genealogico (ID: {partita_id}): {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python in genera_report_genealogico (ID: {partita_id}): {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return None

    def genera_report_possessore(self, possessore_id: int) -> Optional[str]:
        """Chiama la funzione SQL catasto.genera_report_possessore(%s), usando il pool."""
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            self.logger.error(f"genera_report_possessore: ID possessore non valido: {possessore_id}")
            return None
            
        conn = None
        try:
            query = f"SELECT {self.schema}.genera_report_possessore(%s) AS report_text;" # Assicurati che la funzione SQL esista
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione genera_report_possessore per ID possessore: {possessore_id}")
                cur.execute(query, (possessore_id,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    self.logger.info(f"Report possessore generato per ID {possessore_id}.")
                    return str(result[0])
                else:
                    self.logger.warning(f"Nessun report possessore generato per ID {possessore_id} o risultato NULL.")
                    return None
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in genera_report_possessore (ID: {possessore_id}): {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python in genera_report_possessore (ID: {possessore_id}): {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return None

    def genera_report_consultazioni(self, data_inizio: Optional[date] = None, 
                                    data_fine: Optional[date] = None,
                                    richiedente: Optional[str] = None) -> Optional[str]:
        """Chiama la funzione SQL catasto.genera_report_consultazioni, usando il pool."""
        conn = None
        try:
            query = f"SELECT {self.schema}.genera_report_consultazioni(%s, %s, %s) AS report_text;" # Assicurati che la funzione SQL esista
            params = (data_inizio, data_fine, richiedente)
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione genera_report_consultazioni con filtri: data_inizio={data_inizio}, data_fine={data_fine}, richiedente='{richiedente}'")
                cur.execute(query, params)
                result = cur.fetchone()
                if result and result[0] is not None:
                    self.logger.info("Report consultazioni generato.")
                    return str(result[0])
                else:
                    self.logger.warning("Nessun report consultazioni generato o risultato NULL.")
                    return "Nessun dato trovato per i criteri specificati." # Restituisce un messaggio invece di None
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in genera_report_consultazioni: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python in genera_report_consultazioni: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return "Errore durante la generazione del report." # Messaggio di errore generico
    # --- Metodi Viste Materializzate (MODIFICATI per comune_id e query join) ---

    def get_statistiche_comune(self) -> List[Dict[str, Any]]:
        """Recupera dati dalla vista materializzata mv_statistiche_comune."""
        conn = None
        stats_list = []
        query = f"SELECT * FROM {self.schema}.mv_statistiche_comune ORDER BY comune;" # Usa self.schema
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_statistiche_comune: {query}")
                cur.execute(query)
                results = cur.fetchall()
                if results:
                    stats_list = [dict(row) for row in results]
                self.logger.info(f"Recuperate {len(stats_list)} righe da mv_statistiche_comune.")
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_statistiche_comune: {db_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python in get_statistiche_comune: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return stats_list

    def get_immobile_details(self, immobile_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera i dettagli completi di un singolo immobile, inclusi i dati correlati.
        """
        if not isinstance(immobile_id, int) or immobile_id <= 0:
            self.logger.error(f"get_immobile_details: immobile_id non valido: {immobile_id}")
            return None

        query = f"""
            SELECT
                i.id, i.partita_id, i.localita_id, i.natura, i.classificazione, i.consistenza,
                i.numero_piani, i.numero_vani,
                p.numero_partita, p.suffisso_partita,
                c.nome AS comune_nome,
                l.nome AS localita_nome, l.tipo AS localita_tipo, l.civico
            FROM
                {self.schema}.immobile i
            JOIN
                {self.schema}.partita p ON i.partita_id = p.id
            JOIN
                {self.schema}.comune c ON p.comune_id = c.id
            JOIN
                {self.schema}.localita l ON i.localita_id = l.id
            WHERE
                i.id = %s;
        """
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_immobile_details per immobile_id {immobile_id}")
                cur.execute(query, (immobile_id,))
                immobile_data = cur.fetchone()
                
                if immobile_data:
                    self.logger.info(f"Dettagli recuperati per immobile ID {immobile_id}.")
                    return dict(immobile_data)
                else:
                    self.logger.warning(f"Nessun immobile trovato con ID {immobile_id}.")
                    return None
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB durante il recupero dei dettagli dell'immobile ID {immobile_id}: {db_err}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Errore generico durante il recupero dei dettagli dell'immobile ID {immobile_id}: {e}", exc_info=True)
            return None
        finally:
            if conn:
                self._release_connection(conn)
    def get_immobili_per_tipologia(self, comune_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        conn = None
        immobili_list = []
        params = []
        query_base = f"SELECT * FROM {self.schema}.mv_immobili_per_tipologia" # Usa self.schema

        if comune_id is not None:
            # Assumendo che mv_immobili_per_tipologia abbia comune_nome, e comune.id sia la FK
            # Questa query è un esempio, potrebbe necessitare di adattamenti basati sulla struttura esatta della vista
            query = f"""
                 SELECT m.* FROM {self.schema}.mv_immobili_per_tipologia m
                 JOIN {self.schema}.comune c ON m.comune_nome = c.nome -- o come la vista si collega al comune
                 WHERE c.id = %s
                 ORDER BY m.comune_nome, m.classificazione LIMIT %s;
            """
            params = [comune_id, limit]
        else:
            query = f"{query_base} ORDER BY comune_nome, classificazione LIMIT %s;"
            params = [limit]
        
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_immobili_per_tipologia: {cur.mogrify(query, tuple(params)).decode('utf-8', 'ignore')}")
                cur.execute(query, tuple(params))
                results = cur.fetchall()
                if results:
                    immobili_list = [dict(row) for row in results]
                self.logger.info(f"Recuperate {len(immobili_list)} righe da mv_immobili_per_tipologia.")
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_immobili_per_tipologia: {db_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python in get_immobili_per_tipologia: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return immobili_list

    def get_partite_complete_view(self, comune_id: Optional[int] = None, stato: Optional[str] = None, limit: int = 100) -> List[Dict]: # Usa comune_id
        """Recupera dati dalla vista materializzata mv_partite_complete (aggiornata), filtrando per ID."""
        try:
            params = []
            # La vista SQL è stata aggiornata per usare nome comune
            query = "SELECT * FROM mv_partite_complete" # La vista ha 'comune_nome'
            where_clauses = []
            if comune_id is not None:
                 # Filtra con JOIN
                 query = """
                     SELECT m.* FROM mv_partite_complete m
                     JOIN comune c ON m.comune_nome = c.nome
                     WHERE c.id = %s
                 """
                 params.append(comune_id)
                 if stato and stato.lower() in ['attiva', 'inattiva']:
                     query += " AND m.stato = %s"; params.append(stato.lower())
            elif stato and stato.lower() in ['attiva', 'inattiva']:
                 query += " WHERE stato = %s"; params.append(stato.lower())

            query += " ORDER BY comune_nome, numero_partita LIMIT %s"; params.append(limit)
            if self.execute_query(query, tuple(params)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_partite_complete_view: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_partite_complete_view: {e}"); return []

    def aggiorna_legame_partita_possessore(self, 
                                          partita_possessore_id: int, 
                                          titolo: str, 
                                          quota: Optional[str]
                                          # , tipo_partita_rel: Optional[str] = None # Se vuoi permettere modifica anche di questo
                                          ) -> bool: # Restituisce True o solleva eccezione
        """
        Aggiorna i dettagli (titolo, quota) di un legame esistente 
        nella tabella partita_possessore.
        """
        if not (isinstance(partita_possessore_id, int) and partita_possessore_id > 0):
            raise DBDataError(f"ID relazione partita-possessore non valido: {partita_possessore_id}")
        if not (isinstance(titolo, str) and titolo.strip()):
            raise DBDataError("Il titolo di possesso è obbligatorio.")
        
        actual_quota = quota.strip() if isinstance(quota, str) and quota.strip() else None
        # tipo_partita_da_aggiornare = tipo_partita_rel # Se lo modifichi

        set_clauses = ["titolo = %s", "quota = %s", "data_modifica = CURRENT_TIMESTAMP"]
        params = [titolo.strip(), actual_quota]
        
        # if tipo_partita_da_aggiornare: # Se si modifica anche tipo_partita
        #     if tipo_partita_da_aggiornare not in ['principale', 'secondaria']:
        #         raise DBDataError(f"Tipo partita nel legame non valido: {tipo_partita_da_aggiornare}")
        #     set_clauses.insert(0, "tipo_partita = %s") # Inserisci all'inizio per ordine parametri
        #     params.insert(0, tipo_partita_da_aggiornare)

        params.append(partita_possessore_id) # Per la clausola WHERE

        query = f"""
            UPDATE {self.schema}.partita_possessore
            SET {', '.join(set_clauses)}
            WHERE id = %s;
        """
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione query aggiorna_legame_partita_possessore ID {partita_possessore_id}: {cur.mogrify(query, tuple(params)).decode('utf-8', 'ignore')}")
                cur.execute(query, tuple(params))
                
                if cur.rowcount == 0:
                    conn.rollback()
                    self.logger.warning(f"Tentativo di aggiornare legame partita-possessore ID {partita_possessore_id} non trovato o dati identici.")
                    # Verifica se esiste
                    cur.execute(f"SELECT 1 FROM {self.schema}.partita_possessore WHERE id = %s", (partita_possessore_id,))
                    if not cur.fetchone():
                        raise DBNotFoundError(f"Legame partita-possessore con ID {partita_possessore_id} non trovato.")
                    # Se esiste ma rowcount è 0, i dati (escluso data_modifica) erano identici
                    # data_modifica è comunque aggiornata, quindi consideralo un successo.
                
                conn.commit()
                self.logger.info(f"Legame partita-possessore ID {partita_possessore_id} aggiornato. Righe modificate: {cur.rowcount if cur.rowcount > 0 else 1}")
                return True

        except (psycopg2.errors.CheckViolation, psycopg2.Error) as e: # Gestisce Check per tipo_partita se lo aggiungi
            if conn: conn.rollback()
            error_detail = getattr(e, 'pgerror', str(e))
            constraint_name = getattr(e.diag, 'constraint_name', "N/D") if hasattr(e, 'diag') else "N/D"
            self.logger.error(f"Errore DB aggiornando legame {partita_possessore_id} (vincolo: {constraint_name}): {error_detail}", exc_info=True)
            if isinstance(e, psycopg2.errors.CheckViolation) and "partita_possessore_tipo_partita_check" in str(e):
                 raise DBDataError(f"Il valore per 'tipo partita nel legame' non è valido.") from e
            raise DBMError(f"Errore database aggiornando legame: {error_detail}") from e
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore imprevisto aggiornando legame {partita_possessore_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
    
    def aggiungi_possessore_a_partita(self, 
                                     partita_id: int, 
                                     possessore_id: int,
                                     tipo_partita_rel: str, # Questo è il campo 'tipo_partita' in partita_possessore
                                     titolo: str, 
                                     quota: Optional[str]
                                    ) -> bool: # Restituisce True in caso di successo, altrimenti solleva eccezione
        """
        Aggiunge un legame tra una partita e un possessore nella tabella partita_possessore.

        Args:
            partita_id: ID della partita.
            possessore_id: ID del possessore.
            tipo_partita_rel: Il tipo di partita per questo legame (es. 'principale', 'secondaria').
                              Deve corrispondere al check constraint della tabella.
            titolo: Il titolo di possesso (es. 'proprietà esclusiva').
            quota: La quota di possesso (es. '1/2', opzionale).

        Returns:
            True se l'inserimento ha successo.

        Raises:
            DBDataError: Se i parametri di input non sono validi.
            DBUniqueConstraintError: Se il legame partita-possessore esiste già (violazione UNIQUE).
            DBMError: Per altri errori generici del database (es. Foreign Key violation se partita_id o possessore_id non esistono).
        """
        if not all([isinstance(partita_id, int) and partita_id > 0,
                    isinstance(possessore_id, int) and possessore_id > 0,
                    isinstance(titolo, str) and titolo.strip(),
                    isinstance(tipo_partita_rel, str) and tipo_partita_rel in ['principale', 'secondaria']]):
            msg = "Parametri non validi forniti per aggiungere possessore a partita."
            self.logger.error(f"aggiungi_possessore_a_partita: {msg} - P_ID:{partita_id}, POSS_ID:{possessore_id}, Titolo:'{titolo}', TipoRel:'{tipo_partita_rel}'")
            raise DBDataError(msg)
        
        # Quota può essere None o una stringa. Se è una stringa vuota, la trattiamo come None.
        if quota is not None and not isinstance(quota, str):
             raise DBDataError(f"La quota fornita ('{quota}') non è una stringa valida o None.")
        actual_quota = quota.strip() if isinstance(quota, str) and quota.strip() else None


        query = f"""
            INSERT INTO {self.schema}.partita_possessore
                (partita_id, possessore_id, tipo_partita, titolo, quota, data_creazione, data_modifica)
            VALUES
                (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id; 
        """
        params = (partita_id, possessore_id, tipo_partita_rel, titolo.strip(), actual_quota)
        
        conn = None
        new_relation_id = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione query aggiungi_possessore_a_partita: {cur.mogrify(query, params).decode('utf-8', 'ignore')}")
                cur.execute(query, params)
                new_relation_id = cur.fetchone()[0] if cur.rowcount > 0 else None
                conn.commit()
                
                if new_relation_id:
                    self.logger.info(f"Possessore ID {possessore_id} associato con successo alla partita ID {partita_id} (ID Relazione: {new_relation_id}).")
                    return True # Successo
                else:
                    # Questo non dovrebbe accadere se l'INSERT va a buon fine e RETURNING id è usato
                    # a meno che l'insert non fallisca silenziosamente (improbabile con i vincoli DB)
                    self.logger.error(f"aggiungi_possessore_a_partita: Inserimento fallito senza eccezione DB esplicita per P_ID:{partita_id}, POSS_ID:{possessore_id}.")
                    raise DBMError("Inserimento del legame partita-possessore fallito senza un errore database specifico.")

        except psycopg2.errors.UniqueViolation as uve:
            if conn: conn.rollback()
            constraint_name = getattr(uve.diag, 'constraint_name', "N/D")
            error_detail = getattr(uve, 'pgerror', str(uve))
            self.logger.warning(f"Violazione di unicità (vincolo: {constraint_name}) aggiungendo possessore {possessore_id} a partita {partita_id}: {error_detail}")
            # Il vincolo di unicità in partita_possessore è UNIQUE(partita_id, possessore_id)
            if constraint_name == "partita_possessore_partita_id_possessore_id_key": # Verifica il nome esatto del tuo vincolo
                msg = "Questo possessore è già associato a questa partita."
            else:
                msg = f"Impossibile associare il possessore: i dati violano un vincolo di unicità (vincolo: {constraint_name})."
            raise DBUniqueConstraintError(msg, constraint_name=constraint_name, details=error_detail) from uve
        
        except psycopg2.errors.ForeignKeyViolation as fke:
            if conn: conn.rollback()
            constraint_name = getattr(fke.diag, 'constraint_name', "N/D")
            error_detail = getattr(fke, 'pgerror', str(fke))
            self.logger.error(f"Violazione Foreign Key (vincolo: {constraint_name}) aggiungendo legame per P_ID:{partita_id}, POSS_ID:{possessore_id}: {error_detail}")
            msg = f"Impossibile associare il possessore: la partita o il possessore specificati non esistono (vincolo: {constraint_name})."
            raise DBMError(msg) from fke # Potresti creare una DBForeignKeyError specifica

        except psycopg2.errors.CheckViolation as cve: # Per il check su tipo_partita
            if conn: conn.rollback()
            constraint_name = getattr(cve.diag, 'constraint_name', "N/D")
            error_detail = getattr(cve, 'pgerror', str(cve))
            self.logger.error(f"Violazione CHECK constraint (vincolo: {constraint_name}) per legame P_ID:{partita_id}, POSS_ID:{possessore_id}: {error_detail}")
            msg = f"Il valore per 'tipo partita nel legame' ('{tipo_partita_rel}') non è valido (ammessi: 'principale', 'secondaria')."
            raise DBDataError(msg) from cve

        except psycopg2.Error as e:
            if conn: conn.rollback()
            error_detail = getattr(e, 'pgerror', str(e))
            self.logger.error(f"Errore DB generico aggiungendo possessore a partita (P_ID:{partita_id}, POSS_ID:{possessore_id}): {error_detail}", exc_info=True)
            raise DBMError(f"Errore database durante l'associazione del possessore: {error_detail}") from e
        
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore imprevisto Python aggiungendo possessore a partita (P_ID:{partita_id}, POSS_ID:{possessore_id}): {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante l'associazione: {e}") from e
        
        finally:
            if conn:
                self._release_connection(conn)
        
        return False # Non dovrebbe essere raggiunto se le eccezioni sono sollevate correttamente

    def rimuovi_possessore_da_partita(self, partita_possessore_id: int) -> bool: # Restituisce True o solleva eccezione
        """
        Rimuove un legame partita-possessore dalla tabella partita_possessore.
        """
        if not (isinstance(partita_possessore_id, int) and partita_possessore_id > 0):
            raise DBDataError(f"ID relazione partita-possessore non valido: {partita_possessore_id}")

        query = f"DELETE FROM {self.schema}.partita_possessore WHERE id = %s;"
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione query rimuovi_possessore_da_partita ID {partita_possessore_id}: {cur.mogrify(query, (partita_possessore_id,)).decode('utf-8', 'ignore')}")
                cur.execute(query, (partita_possessore_id,))
                
                if cur.rowcount == 0:
                    conn.rollback() # Anche se DELETE non dovrebbe fallire se la riga non c'è, è una buona pratica
                    self.logger.warning(f"Tentativo di rimuovere legame partita-possessore ID {partita_possessore_id} non trovato.")
                    raise DBNotFoundError(f"Nessun legame partita-possessore trovato con ID {partita_possessore_id} da rimuovere.")
                
                conn.commit()
                self.logger.info(f"Legame partita-possessore ID {partita_possessore_id} rimosso con successo. Righe modificate: {cur.rowcount}")
                return True

        except psycopg2.Error as e: # Errore DB generico
            if conn: conn.rollback()
            error_detail = getattr(e, 'pgerror', str(e))
            self.logger.error(f"Errore DB rimuovendo legame {partita_possessore_id}: {error_detail}", exc_info=True)
            raise DBMError(f"Errore database durante la rimozione del legame: {error_detail}") from e
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore imprevisto rimuovendo legame {partita_possessore_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
    def get_possessore_full_details(self, possessore_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera i dettagli completi di un singolo possessore, incluso il nome del comune di riferimento.

        Args:
            possessore_id: L'ID del possessore da recuperare.

        Returns:
            Un dizionario contenente i dettagli del possessore se trovato, altrimenti None.
            Il dizionario includerà: 'id', 'cognome_nome', 'paternita', 
            'nome_completo', 'attivo', 'comune_riferimento_id', 'comune_riferimento_nome',
            'data_creazione', 'data_modifica'.
        """
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            self.logger.error(f"get_possessore_full_details: possessore_id non valido: {possessore_id}")
            return None

        query = f"""
            SELECT
                p.id,
                p.cognome_nome,
                p.paternita,
                p.nome_completo,
                p.attivo,
                p.comune_id AS comune_riferimento_id, 
                c.nome AS comune_riferimento_nome, -- Nome del comune dalla tabella comune
                p.data_creazione,
                p.data_modifica
            FROM
                {self.schema}.possessore p
            LEFT JOIN 
                {self.schema}.comune c ON p.comune_id = c.id -- LEFT JOIN per gestire possessori senza comune (anche se comune_id è NOT NULL nel tuo schema)
            WHERE
                p.id = %s;
        """
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione query get_possessore_full_details per possessore_id {possessore_id}: {cur.mogrify(query, (possessore_id,)).decode('utf-8', 'ignore')}")
                cur.execute(query, (possessore_id,))
                possessore_data = cur.fetchone()
                
                if possessore_data:
                    self.logger.info(f"Dettagli recuperati per il possessore ID {possessore_id}.")
                    return dict(possessore_data)
                else:
                    self.logger.warning(f"Nessun possessore trovato con ID {possessore_id}.")
                    return None
        except psycopg2.Error as e:
            self.logger.error(f"Errore DB durante il recupero dei dettagli del possessore ID {possessore_id}: {e}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Errore generico durante il recupero dei dettagli del possessore ID {possessore_id}: {e}", exc_info=True)
            return None
        finally:
            if conn:
                self._release_connection(conn)
    
    def get_cronologia_variazioni(self, comune_origine_id: Optional[int] = None, tipo_variazione: Optional[str] = None, limit: int = 100) -> List[Dict]: # Usa comune_id
        """Recupera dati dalla vista materializzata mv_cronologia_variazioni (aggiornata), filtrando per ID."""
        try:
            params = []
            # La vista SQL è stata aggiornata per usare nomi comuni
            query = "SELECT * FROM mv_cronologia_variazioni" # Vista ha 'comune_origine' come nome
            if comune_origine_id is not None:
                query = """
                    SELECT m.* FROM mv_cronologia_variazioni m
                    JOIN comune c ON m.comune_origine = c.nome
                    WHERE c.id = %s
                """
                params.append(comune_origine_id)
                if tipo_variazione: query += " AND m.tipo_variazione = %s"; params.append(tipo_variazione)
            elif tipo_variazione:
                query += " WHERE tipo_variazione = %s"; params.append(tipo_variazione)

            query += " ORDER BY data_variazione DESC LIMIT %s"; params.append(limit)
            if self.execute_query(query, tuple(params)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_cronologia_variazioni: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_cronologia_variazioni: {e}"); return []

    # --- Metodi Funzioni Avanzate di Report (MODIFICATI) ---

    def get_report_annuale_partite(self, comune_id: int, anno: int) -> List[Dict]: # Usa comune_id
        """Chiama la funzione SQL report_annuale_partite (MODIFICATA per comune_id)."""
        try:
            # Funzione SQL aggiornata per comune_id
            query = "SELECT * FROM report_annuale_partite(%s, %s)"
            if self.execute_query(query, (comune_id, anno)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_report_annuale_partite: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_report_annuale_partite: {e}"); return []

    def get_report_proprieta_possessore(self, possessore_id: int, data_inizio: date, data_fine: date) -> List[Dict]:
        """Chiama la funzione SQL report_proprieta_possessore (SQL aggiornata per nome comune)."""
        try:
            # Funzione SQL aggiornata per JOIN
            query = "SELECT * FROM report_proprieta_possessore(%s, %s, %s)"
            if self.execute_query(query, (possessore_id, data_inizio, data_fine)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_report_proprieta_possessore: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_report_proprieta_possessore: {e}"); return []

    def get_report_comune(self, comune_id: int) -> Optional[Dict]: # Usa comune_id
        """Chiama la funzione SQL genera_report_comune (MODIFICATA per comune_id)."""
        try:
            # Funzione SQL aggiornata per comune_id
            query = "SELECT * FROM genera_report_comune(%s)"
            if self.execute_query(query, (comune_id,)): return self.fetchone()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_report_comune: {db_err}"); return None
        except Exception as e: logger.error(f"Errore Python get_report_comune: {e}"); return None

    def export_partita_json(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL esporta_partita_json (SQL aggiornata)."""
        try:
            # Funzione SQL aggiornata per fare JOIN
            query = "SELECT esporta_partita_json(%s) AS partita_json"
            if self.execute_query(query, (partita_id,)):
                result = self.fetchone()
                if result and result.get('partita_json'):
                     try: return json.dumps(result['partita_json'], indent=4, ensure_ascii=False)
                     except (TypeError, ValueError) as json_err: logger.error(f"Errore JSON export partita {partita_id}: {json_err}"); return str(result['partita_json'])
            logger.warning(f"Nessun JSON per partita ID {partita_id}.")
        except psycopg2.Error as db_err: logger.error(f"Errore DB export_partita_json (ID: {partita_id}): {db_err}")
        except Exception as e: logger.error(f"Errore Python export_partita_json (ID: {partita_id}): {e}")
        return None

    def export_possessore_json(self, possessore_id: int) -> Optional[str]:
        """Chiama la funzione SQL esporta_possessore_json (SQL aggiornata)."""
        try:
            # Funzione SQL aggiornata per fare JOIN
            query = "SELECT esporta_possessore_json(%s) AS possessore_json"
            if self.execute_query(query, (possessore_id,)):
                result = self.fetchone()
                if result and result.get('possessore_json'):
                     try: return json.dumps(result['possessore_json'], indent=4, ensure_ascii=False)
                     except (TypeError, ValueError) as json_err: logger.error(f"Errore JSON export possessore {possessore_id}: {json_err}"); return str(result['possessore_json'])
            logger.warning(f"Nessun JSON per possessore ID {possessore_id}.")
        except psycopg2.Error as db_err: logger.error(f"Errore DB export_possessore_json (ID: {possessore_id}): {db_err}")
        except Exception as e: logger.error(f"Errore Python export_possessore_json (ID: {possessore_id}): {e}")
        return None
    def get_partita_data_for_export(self, partita_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera i dati completi di una partita come dizionario Python per l'esportazione,
        chiamando la funzione SQL catasto.esporta_partita_json(%s).
        Utilizza il pool di connessioni.
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            self.logger.error(f"get_partita_data_for_export: ID partita non valido: {partita_id}")
            return None
            
        conn = None
        try:
            # Assumiamo che la funzione SQL restituisca un singolo valore JSON/JSONB
            # e che il suo schema sia corretto (es. self.schema = 'catasto')
            query = f"SELECT {self.schema}.esporta_partita_json(%s) AS partita_data;"
            
            conn = self._get_connection() # Ottiene connessione dal pool
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_partita_data_for_export per ID partita: {partita_id} con query: {query}")
                cur.execute(query, (partita_id,))
                result = cur.fetchone()
                
                if result and result['partita_data'] is not None:
                    self.logger.info(f"Dati per esportazione recuperati per partita ID {partita_id}.")
                    # psycopg2 converte automaticamente il tipo JSON/JSONB di PostgreSQL 
                    # in un dizionario Python quando si usa DictCursor o se il tipo è registrato.
                    return result['partita_data'] 
                else:
                    self.logger.warning(f"Nessun dato trovato per partita ID {partita_id} da {self.schema}.esporta_partita_json o il risultato era NULL.")
                    return None
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_partita_data_for_export (ID: {partita_id}): {db_err}", exc_info=True)
        except Exception as e: # Cattura altri errori, inclusi AttributeError se si chiamasse self.execute_query per errore
            self.logger.error(f"Errore Python generico in get_partita_data_for_export (ID: {partita_id}): {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn) # Rilascia sempre la connessione
        return None # Restituisce None in caso di qualsiasi errore


    def get_possessore_data_for_export(self, possessore_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera i dati completi di un possessore come dizionario Python per l'esportazione,
        chiamando la funzione SQL catasto.esporta_possessore_json(%s).
        Utilizza il pool di connessioni.
        """
        if not isinstance(possessore_id, int) or possessore_id <= 0:
            self.logger.error(f"get_possessore_data_for_export: ID possessore non valido: {possessore_id}")
            return None

        conn = None
        try:
            # Assumiamo che la funzione SQL restituisca un singolo valore JSON/JSONB
            # e che il suo schema sia corretto (es. self.schema = 'catasto')
            query = f"SELECT {self.schema}.esporta_possessore_json(%s) AS possessore_data;"
            
            conn = self._get_connection() # Ottiene connessione dal pool
            # Usiamo DictCursor per coerenza
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_possessore_data_for_export per ID possessore: {possessore_id} con query: {query}")
                cur.execute(query, (possessore_id,))
                result = cur.fetchone()
                
                if result and result['possessore_data'] is not None:
                    self.logger.info(f"Dati per esportazione recuperati per possessore ID {possessore_id}.")
                    # psycopg2 converte automaticamente JSON/JSONB in dict Python
                    return result['possessore_data']
                else:
                    self.logger.warning(f"Nessun dato trovato per possessore ID {possessore_id} da {self.schema}.esporta_possessore_json o il risultato era NULL.")
                    return None
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_possessore_data_for_export (ID: {possessore_id}): {db_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python generico in get_possessore_data_for_export (ID: {possessore_id}): {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn) # Rilascia sempre la connessione
        return None # Restituisce None in caso di qualsiasi errore

    # --- Metodi Manutenzione e Ottimizzazione (Invariati rispetto a comune_id) ---

    def verifica_integrita_database(self) -> Tuple[bool, str]:
        """Chiama la procedura SQL verifica_integrita_database e cattura i messaggi (notices)."""
        messages: List[str] = []
        problemi_trovati = False
        output_msg = ""
        conn = None

        def notice_handler(notice):
            messages.append(str(notice).strip().replace("NOTICE: ", ""))

        try:
            conn = self._get_connection() # Ottiene una connessione dal pool
            
            # Aggiungi il gestore di avvisi alla connessione specifica
            # Nota: conn.notices è una lista in psycopg2 >= 2. notices.append() è il modo.
            # Per versioni più vecchie o per essere sicuri, add_notice_handler potrebbe essere usato ma è più complesso da resettare.
            # Per semplicità e compatibilità, usiamo l'approccio di pulire e aggiungere.
            
            original_notices_list_ref = None
            if hasattr(conn, 'notices'): # psycopg2.extensions.connection.notices
                original_notices_list_ref = conn.notices[:] # Copia la lista attuale
                conn.notices.clear() # Pulisci per questa chiamata
                conn.notices.append(notice_handler)
            else: # Fallback per versioni/casi in cui .notices non è una lista modificabile
                  # Questo è più complesso perché add_notice_handler non ha un remove_notice_handler facile
                self.logger.warning("Attributo conn.notices non trovato come lista, i notice potrebbero non essere catturati.")

            with conn.cursor() as cur:
                # Assumendo che la procedura esista e sia CALLable
                self.logger.debug("Chiamata a procedura verifica_integrita_database(NULL)")
                cur.execute(f"CALL {self.schema}.verifica_integrita_database(NULL);")
                conn.commit() # Se la procedura fa modifiche o richiede commit per rilasciare risorse
            
            # Ora messages dovrebbe contenere i notice
            for msg in messages:
                if "Problemi" in msg or "Problema:" in msg or "WARNING:" in msg or "ERRORE:" in msg: # Aggiunto ERRORE
                    problemi_trovati = True
                output_msg += msg + "\n"
            
            if not output_msg and not problemi_trovati: # Se non ci sono messaggi e nessun problema flaggato
                output_msg = "Nessun problema di integrità rilevato o nessun avviso emesso dalla procedura."
            elif not problemi_trovati and output_msg: # Se ci sono messaggi ma nessuno è stato flaggato come problema
                output_msg = "Verifica completata con i seguenti avvisi/messaggi:\n" + output_msg
            
            self.logger.info(f"Verifica integrità completata. Problemi trovati: {problemi_trovati}. Output: {output_msg.strip()[:200]}...")

        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB durante verifica integrità: {db_err}", exc_info=True)
            output_msg = f"Errore DB durante la verifica: {getattr(db_err, 'pgerror', str(db_err))}"
            problemi_trovati = True
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python durante verifica integrità: {e}", exc_info=True)
            output_msg = f"Errore di sistema durante la verifica: {e}"
            problemi_trovati = True
        finally:
            if conn:
                # Ripristina il gestore di avvisi originale, se possibile
                if hasattr(conn, 'notices') and original_notices_list_ref is not None:
                    conn.notices.clear()
                    conn.notices.extend(original_notices_list_ref)
                self._release_connection(conn)
        
        return problemi_trovati, output_msg.strip()
    def verifica_integrita_database_gui(self) -> Tuple[bool, str]:
        """
        Esegue la procedura SQL di verifica integrità e cattura i messaggi NOTICE.
        Restituisce una tupla: (problemi_rilevati_boolean, stringa_messaggi_output).
        """
        self.logger.info("Avvio verifica integrità database...")
        conn = None
        captured_notices: List[str] = []
        problemi_rilevati_flag = False # Flag per indicare se un notice suggerisce un problema

        # Funzione handler per i messaggi NOTICE dalla connessione
        def notice_handler_gui(notice):
            msg_line = str(notice).strip()
            # Rimuovi il prefisso "NOTICE: " che psycopg2 potrebbe aggiungere
            if msg_line.upper().startswith("NOTICE:"):
                msg_line = msg_line[len("NOTICE:"):].strip()
            
            captured_notices.append(msg_line)
            # Semplice controllo per parole chiave indicative di problemi
            # Può essere reso più sofisticato se la procedura SQL usa formati specifici
            if any(keyword in msg_line.upper() for keyword in ["ERROR", "FAIL", "CORRUPT", "WARNING", "PROBLEMA"]):
                nonlocal problemi_rilevati_flag # Necessario per modificare variabile nello scope esterno
                problemi_rilevati_flag = True
                self.logger.warning(f"Potenziale problema di integrità rilevato nel notice: {msg_line}")

        try:
            conn = self._get_connection()
            
            # Salva e pulisci gli handler di notice esistenti per questa connessione
            # conn.notices è una lista in psycopg2
            original_notices_handlers = conn.notices[:] 
            conn.notices.clear()
            conn.notices.append(notice_handler_gui)

            with conn.cursor() as cur:
                self.logger.debug(f"Chiamata a procedura {self.schema}.verifica_integrita_database()")
                cur.execute(f"CALL {self.schema}.verifica_integrita_database();") # SENZA (NULL)
                conn.commit()
            
            self.logger.info("Procedura di verifica integrità database eseguita.")

        except psycopg2.errors.UndefinedFunction:
            self.logger.error(f"La procedura SQL '{self.schema}.verifica_integrita_database' non è stata trovata.", exc_info=True)
            captured_notices.append(f"ERRORE: La procedura SQL '{self.schema}.verifica_integrita_database' non esiste nel database.")
            problemi_rilevati_flag = True
        except psycopg2.Error as db_err:
            if conn: conn.rollback() # Rollback in caso di errore DB
            self.logger.error(f"Errore DB durante la verifica integrità: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            captured_notices.append(f"ERRORE DATABASE: {getattr(db_err, 'pgerror', str(db_err))}")
            problemi_rilevati_flag = True
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python imprevisto durante la verifica integrità: {e}", exc_info=True)
            captured_notices.append(f"ERRORE DI SISTEMA: {e}")
            problemi_rilevati_flag = True
        finally:
            if conn:
                # Ripristina gli handler di notice originali
                if 'original_notices_handlers' in locals():
                    conn.notices[:] = original_notices_handlers
                self._release_connection(conn)
            
        output_string = "\n".join(captured_notices).strip()
        if not output_string and not problemi_rilevati_flag:
            output_string = "Verifica completata. Nessun messaggio specifico o problema riportato dalla procedura."
            
        return problemi_rilevati_flag, output_string
    def _execute_query(self, query, params=None, fetch=None, many=False, script=False):
        """Metodo di utility per eseguire query in modo sicuro."""
        try:
            # Ora utilizza self.db_adapter che è stato correttamente salvato.
            return self.db_adapter.execute_query(query, params, fetch, many, script)
        except Exception as e:
            logging.error(f"Errore durante l'esecuzione della query: {e}")
            QMessageBox.critical(None, "Errore Database", f"Si è verificato un errore: {e}")
            return None if fetch else False
    def open_user_management_dialog(self):
        """
        Apre la finestra di dialogo per la gestione degli utenti e dei ruoli.
        """
        # --- CORREZIONE ---
        # L'importazione viene fatta qui, solo quando il metodo è chiamato.
        # A questo punto, entrambi i moduli sono già stati caricati e non c'è più un ciclo.
        from dialogs import UserManagementDialog
        try:
            # Ora utilizza self.db_adapter che è stato correttamente salvato.
            dialog = UserManagementDialog(self.db_adapter)
            dialog.exec_()
        except Exception as e:
            logging.error(f"Impossibile aprire la gestione utenti: {e}")
            QMessageBox.critical(None, "Errore", f"Impossibile aprire la finestra di gestione utenti: {e}")

    def run_sql_script(self, script_path):
        """
        Esegue un singolo script SQL.
        """
        logging.info(f"Esecuzione dello script SQL: {script_path}")
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            # Ora utilizza self.db_adapter che è stato correttamente salvato.
            if self.db_adapter.execute_script(sql_script):
                logging.info(f"Script {script_path} eseguito con successo.")
                QMessageBox.information(None, "Successo", f"Lo script {script_path} è stato eseguito correttamente.")
                return True
            else:
                return False
        except Exception as e:
            logging.error(f"Errore durante l'esecuzione dello script {script_path}: {e}")
            QMessageBox.critical(None, "Errore Script", f"Impossibile eseguire lo script {script_path}: {e}")
            return False
    def refresh_materialized_views(self, show_success_message=True):
        """
        Aggiorna tutte le viste materializzate nel database.
        """
        logging.info("Inizio aggiornamento delle viste materializzate.")
        
        progress_dialog = QProgressDialog("Aggiornamento viste materializzate in corso...", "Annulla", 0, 0)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setCancelButton(None) 
        progress_dialog.show()

        query = """
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT matviewname FROM pg_matviews WHERE schemaname = 'catasto') LOOP
                EXECUTE 'REFRESH MATERIALIZED VIEW catasto.' || quote_ident(r.matviewname);
            END LOOP;
        END $$;
        """
        try:
            success = self._execute_query(query, script=True)
            progress_dialog.close()
            if success:
                if show_success_message:
                    QMessageBox.information(None, "Successo", "Tutte le viste materializzate sono state aggiornate con successo.")
                logging.info("Viste materializzate aggiornate con successo.")
                return True
            else:
                return False
        except Exception as e:
            progress_dialog.close()
            logging.error(f"Errore critico durante l'aggiornamento delle viste: {e}")
            QMessageBox.critical(None, "Errore Aggiornamento Viste", f"Impossibile aggiornare le viste materializzate: {e}")
            return False

    def run_database_maintenance(self) -> bool:
        """Esegue manutenzione generale del database (es. ANALYZE e aggiorna viste), usando il pool."""
        self.logger.info("Avvio manutenzione database (es. ANALYZE, REFRESH MV)...")
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Assumendo che la procedura esista e sia nello schema corretto.
                # Potrebbe anche essere una serie di comandi SQL invece di una singola procedura.
                # Esempio se chiama una procedura specifica:
                self.logger.debug(f"Chiamata procedura {self.schema}.manutenzione_database()")
                cur.execute(f"CALL {self.schema}.manutenzione_database();")
                # Se manutenzione_database() non fa commit internamente, è necessario qui.
                conn.commit() 
            self.logger.info("Manutenzione database completata con successo.")
            return True
        except psycopg2.Error as db_err:
            if conn: conn.rollback() # Esegui rollback sulla connessione specifica
            self.logger.error(f"Errore DB durante la manutenzione del database: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            return False
        except Exception as e: # Per altri errori Python
            if conn and not conn.closed: conn.rollback() # Esegui rollback sulla connessione specifica
            self.logger.error(f"Errore Python imprevisto durante la manutenzione del database: {e}", exc_info=True)
            return False
        finally:
            if conn:
                self._release_connection(conn)

    def analyze_slow_queries(self, min_duration_ms: int = 1000) -> List[Dict]:
        """Chiama la funzione SQL analizza_query_lente (se esiste)."""
        logger.warning("La funzione SQL 'analizza_query_lente' potrebbe non essere definita.")
        try:
            query = "SELECT * FROM analizza_query_lente(%s)"
            if self.execute_query(query, (min_duration_ms,)): return self.fetchall()
        except psycopg2.errors.UndefinedFunction: logger.warning("Funzione 'analizza_query_lente' non trovata."); return []
        except psycopg2.errors.UndefinedTable: logger.warning("Estensione 'pg_stat_statements' non abilitata."); return []
        except psycopg2.Error as db_err: logger.error(f"Errore DB in analyze_slow_queries: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python in analyze_slow_queries: {e}"); return []
        return []

    def check_index_fragmentation(self):
        """Chiama la procedura SQL controlla_frammentazione_indici (se esiste)."""
        logger.warning("La procedura SQL 'controlla_frammentazione_indici' potrebbe non essere definita.")
        logger.info("Avvio controllo frammentazione indici (risultati nei log DB)...")
        try:
            if self.execute_query("CALL controlla_frammentazione_indici()"): self.commit(); logger.info("Controllo frammentazione avviato."); return True
            return False
        except psycopg2.errors.UndefinedFunction: logger.warning("Procedura 'controlla_frammentazione_indici' non trovata."); return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB check_index_fragmentation: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python check_index_fragmentation: {e}"); self.rollback(); return False

    def get_optimization_suggestions(self) -> Optional[str]:
        """Chiama la funzione SQL suggerimenti_ottimizzazione (se esiste)."""
        logger.warning("La funzione SQL 'suggerimenti_ottimizzazione' potrebbe non essere definita o corretta.")
        try:
            query = "SELECT suggerimenti_ottimizzazione() AS suggestions"
            if self.execute_query(query): result = self.fetchone(); return result.get('suggestions') if result else "Nessun suggerimento."
            return None
        except psycopg2.errors.UndefinedFunction: logger.warning("Funzione 'suggerimenti_ottimizzazione' non trovata."); return "Funzione suggerimenti non trovata."
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_optimization_suggestions: {db_err}"); return None
        except Exception as e: logger.error(f"Errore Python get_optimization_suggestions: {e}"); return None

    # --- Metodi Sistema Utenti e Audit (Invariati rispetto a comune_id) ---

    def set_session_app_user(self, user_id: Optional[int], client_ip: Optional[str] = None) -> bool:
        """
        Imposta variabili di sessione PostgreSQL per tracciamento generico (diverso da audit log specifico).
        Usa il pool di connessioni. Se queste sono le stesse variabili di audit, considera di unificare.
        """
        # Queste variabili sembrano diverse da 'catasto.app_user_id' e 'catasto.session_id' usate per l'audit.
        # Se sono le stesse, questo metodo potrebbe essere ridondante con set_audit_session_variables.
        # Assumiamo per ora che 'app.user_id' e 'app.ip_address' siano GUC separate.
        self.logger.debug(f"Tentativo di impostare var sessione app: app.user_id='{user_id}', app.ip_address='{client_ip}'")
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                user_id_str = str(user_id) if user_id is not None else None
                ip_str = client_ip if client_ip is not None else None
                
                # Usa SELECT set_config per impostare GUCs di sessione.
                # Il terzo argomento 'false' significa che l'impostazione dura per la sessione.
                cur.execute("SELECT set_config('app.user_id', %s, false);", (user_id_str,))
                cur.execute("SELECT set_config('app.ip_address', %s, false);", (ip_str,))
                conn.commit() # Necessario per rendere effettivi i set_config non locali alla transazione
                self.logger.info(f"Variabili di sessione applicative impostate: app.user_id='{user_id_str}', app.ip_address='{ip_str}'")
                return True
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB impostando var sessione applicative: {db_err}", exc_info=True)
            return False
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python impostando var sessione applicative: {e}", exc_info=True)
            return False
        finally:
            if conn:
                self._release_connection(conn)

    def clear_session_app_user(self):
        """Resetta le variabili di sessione PostgreSQL 'app.user_id' e 'app.ip_address'."""
        self.logger.info("Reset variabili di sessione applicative (app.user_id, app.ip_address).")
        # Richiama set_session_app_user con None per resettarle.
        # In alternativa, si potrebbe usare RESET nome_variabile;
        return self.set_session_app_user(user_id=None, client_ip=None)

    def get_audit_log(self, tabella: Optional[str]=None, operazione: Optional[str]=None,
                      record_id: Optional[int]=None, data_inizio: Optional[date]=None,
                      data_fine: Optional[date]=None, utente_db: Optional[str]=None,
                      app_user_id: Optional[int]=None, session_id: Optional[str]=None,
                      limit: int=100) -> List[Dict]:
        """Recupera log di audit con filtri opzionali dalla vista v_audit_dettagliato."""
        try:
            conditions = []; params = []
            query = "SELECT * FROM v_audit_dettagliato"
            if tabella: conditions.append("tabella = %s"); params.append(tabella)
            if operazione and operazione.upper() in ['I', 'U', 'D']: conditions.append("operazione = %s"); params.append(operazione.upper())
            if record_id is not None: conditions.append("record_id = %s"); params.append(record_id)
            if data_inizio: conditions.append("timestamp >= %s"); params.append(data_inizio)
            if data_fine: data_fine_end_day = datetime.combine(data_fine, datetime.max.time()); conditions.append("timestamp <= %s"); params.append(data_fine_end_day)
            if utente_db: conditions.append("db_user = %s"); params.append(utente_db)
            # Attenzione: filtro su app_user_id deve usare alias tabella originale se vista non lo include direttamente con alias
            # La vista v_audit_dettagliato JOIN u ON al.app_user_id = u.id, quindi al.app_user_id non è direttamente selezionato
            # Modifichiamo la vista o filtriamo su app_username? Filtriamo su ID per ora, assumendo che la vista possa essere modificata o che funzioni.
            if app_user_id is not None: conditions.append("al.app_user_id = %s"); params.append(app_user_id) # Usa al.app_user_id (potrebbe richiedere modifica vista)
            if session_id: conditions.append("session_id = %s"); params.append(session_id)

            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY timestamp DESC LIMIT %s"; params.append(limit)

            if self.execute_query(query, tuple(params)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_audit_log: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_audit_log: {e}"); return []
        return []

    def get_record_history(self, tabella: str, record_id: int) -> List[Dict]:
        """Chiama la funzione SQL get_record_history."""
        try:
            query = "SELECT * FROM get_record_history(%s, %s)"
            if self.execute_query(query, (tabella, record_id)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_record_history: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_record_history: {e}"); return []
        return []

    def genera_report_audit(self, tabella=None, data_inizio=None, data_fine=None,
                          operazione=None, utente_db=None, app_user_id=None) -> str:
        """Genera un report testuale basato sui log di audit filtrati."""
        logs = self.get_audit_log(tabella, operazione, None, data_inizio, data_fine, utente_db, app_user_id, None, 1000)
        if not logs: return "Nessun log di audit trovato per i criteri specificati."
        report_lines = ["--- Report Audit ---", f"Periodo: {data_inizio or 'Inizio'} - {data_fine or 'Fine'}"]
        if tabella: report_lines.append(f"Tabella: {tabella}")
        if operazione: report_lines.append(f"Operazione: {operazione}")
        if utente_db: report_lines.append(f"Utente DB: {utente_db}")
        if app_user_id: report_lines.append(f"Utente App ID: {app_user_id}")
        report_lines.append(f"Numero log: {len(logs)}"); report_lines.append("-" * 20)
        op_map = {"I": "Inserimento", "U": "Aggiornamento", "D": "Cancellazione"}
        for log in logs:
            ts = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if log.get('timestamp') else 'N/D'
            op = op_map.get(log.get('operazione'), '?'); tbl = log.get('tabella', '?'); rec_id = log.get('record_id', '?')
            db_u = log.get('db_user', '?'); app_u = log.get('app_username', 'N/A')
            # ID utente app non è nella vista v_audit_dettagliato di default, aggiungerlo se necessario
            # app_u_id = f" (ID: {log['app_user_id']})" if log.get('app_user_id') is not None else ""
            app_u_id = "" # Rimuovi per ora
            sess = log.get('session_id', '-')[:8]; ip = log.get('ip_address', '-')
            report_lines.append(f"{ts} | {op:<13} | Tab: {tbl:<15} | RecID: {rec_id:<5} | DB User: {db_u:<10} | App User: {app_u}{app_u_id} | Sess: {sess} | IP: {ip}")
        return "\n".join(report_lines)

    def create_user(self, username: str, password_hash: str, nome_completo: str, email: str, ruolo: str) -> bool:
        """Chiama la procedura SQL crea_utente, usando il pool."""
        conn = None
        success = False
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                call_proc = f"CALL {self.schema}.crea_utente(%s, %s, %s, %s, %s)"
                params = (username, password_hash, nome_completo, email, ruolo)
                self.logger.debug(f"Chiamata procedura crea_utente per username: {username}")
                cur.execute(call_proc, params)
                conn.commit()
                self.logger.info(f"Utente '{username}' creato con successo tramite procedura.")
                success = True
        except psycopg2.errors.UniqueViolation as uve: # Cattura violazione di unicità
            if conn: conn.rollback()
            constraint = getattr(uve.diag, 'constraint_name', 'N/D')
            self.logger.error(f"Errore creazione utente '{username}': Username o Email già esistente (vincolo: {constraint}). Dettagli: {uve.pgerror}")
            raise DBUniqueConstraintError(f"Username '{username}' o Email '{email}' già esistente.", constraint_name=constraint) from uve
        except psycopg2.Error as db_err: # Altri errori DB
            if conn: conn.rollback()
            self.logger.error(f"Errore DB creazione utente '{username}': {db_err.pgerror}", exc_info=True)
            raise DBMError(f"Errore database durante la creazione dell'utente: {db_err.pgerror}") from db_err
        except Exception as e: # Errori Python
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python creazione utente '{username}': {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante la creazione dell'utente: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
        return success # O rimuovi il return e lascia che siano solo le eccezioni a segnalare fallimento

    # In catasto_db_manager.py, dentro la classe CatastoDBManager

    # --- Metodi di gestione sessione/utente che usano il pool ---

    def get_user_credentials(self, username: str) -> Optional[Dict[str, Any]]:
        """Recupera le credenziali dell'utente per il login, usando il pool."""
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = f"""
                    SELECT id, username, password_hash, ruolo, nome_completo, email, attivo 
                    FROM {self.schema}.utente 
                    WHERE username = %s;
                """
                self.logger.debug(f"Esecuzione get_user_credentials per username: {username}")
                cur.execute(query, (username,))
                user_data = cur.fetchone()
                if user_data:
                    if not user_data['attivo']:
                        self.logger.warning(f"Tentativo di login per utente '{username}' non attivo.")
                        return None
                    self.logger.info(f"Credenziali recuperate per utente: {username}, Ruolo: {user_data.get('ruolo')}")
                    return dict(user_data)
                else:
                    self.logger.warning(f"Nessun utente trovato con username: {username}")
                    return None
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_user_credentials per '{username}': {db_err}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Errore Python in get_user_credentials per '{username}': {e}", exc_info=True)
            return None
        finally:
            if conn:
                self._release_connection(conn)

    # Metodo ESISTENTE da MODIFICARE
    def register_access(self, user_id: int, action: str, esito: bool,
                        indirizzo_ip: Optional[str] = None,
                        dettagli: Optional[str] = None,
                        application_name: Optional[str] = None,
                        # id_sessione_registrata non serve più come input se gestiamo la generazione qui
                       ) -> Optional[str]: # Restituisce l'ID sessione (UUID string) se login e successo, altrimenti None o solleva eccezione
        """
        Registra un evento di sessione (login, fail_login) nella tabella sessioni_accesso.
        Per il login con successo, genera e restituisce un UUID per la sessione.
        Utilizza il pool di connessioni.
        """
        conn = None
        session_id_to_return: Optional[str] = None

        if action == 'login' and esito:
            session_id_to_return = str(uuid.uuid4()) # Genera UUID per nuova sessione di login
            self.logger.info(f"Nuovo ID sessione generato per login utente {user_id}: {session_id_to_return}")
        elif action == 'fail_login':
            # Per i tentativi falliti, potremmo generare un UUID solo per logging,
            # ma la sessione non diventa "attiva". La procedura SQL lo gestirà.
            # O decidere di non passare un UUID specifico se la procedura lo gestisce opzionalmente per fail_login.
            # Per coerenza con la firma della procedura, passiamo un UUID anche per fail_login.
            session_id_to_return = str(uuid.uuid4()) 
            self.logger.info(f"ID evento generato per fail_login utente {user_id}: {session_id_to_return}")
        # Per altre azioni (es. 'logout', 'timeout'), l'ID sessione dovrebbe essere noto e l'aggiornamento
        # avverrebbe tramite un metodo/procedura diversa (es. logout_user che chiama logout_utente_sessione).

        # Nome della procedura SQL aggiornata
        call_proc_str = f"CALL {self.schema}.registra_evento_sessione(%s, %s, %s, %s, %s, %s, %s);"
        
        # Parametri per la procedura SQL
        # p_utente_id, p_id_sessione_uuid, p_azione, p_esito, p_indirizzo_ip, p_applicazione, p_dettagli
        params = (
            user_id,
            session_id_to_return, # Passa l'UUID generato (o None se non applicabile per l'azione)
            action,
            esito,
            indirizzo_ip,
            application_name if application_name else self.application_name, # Usa default se non fornito
            dettagli
        )

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Chiamata a procedura catasto.registra_evento_sessione per utente {user_id}, azione {action}")
                cur.execute(call_proc_str, params)
                conn.commit()
                self.logger.info(f"Evento sessione registrato: Utente ID {user_id}, Azione {action}, Esito {esito}, Sessione/Evento ID {str(session_id_to_return)[:8]}...")
                
                # Restituisce l'ID sessione solo se è un login andato a buon fine
                if action == 'login' and esito:
                    return session_id_to_return
                # Per altri casi, potremmo restituire True per successo generico o None/False per fallimento
                # Ma la firma ora suggerisce di restituire Optional[str] per l'ID sessione.
                # Se l'evento è registrato ma non è un login, restituire l'ID evento (che è lo stesso dell'UUID) può essere utile.
                return session_id_to_return # Restituisce l'UUID generato (o None se non è stato generato)

        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB in register_access (nuova logica sessioni) per utente {user_id}, azione {action}: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            raise DBMError(f"Errore database durante la registrazione dell'evento di sessione: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python in register_access (nuova logica sessioni) per utente {user_id}, azione {action}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante la registrazione dell'evento di sessione: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
        # Se arriviamo qui a causa di un'eccezione non gestita sopra, o se non è un login con successo
        return None # O sollevare eccezione

    # Metodo ESISTENTE da MODIFICARE
    def logout_user(self, user_id: int, session_id: str, ip_address: Optional[str]) -> bool:
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                call_proc_str = f"CALL {self.schema}.logout_utente_sessione(%s, %s, %s, %s);"
                params = (
                    user_id, 
                    session_id,
                    ip_address, 
                    self.application_name
                )
                self.logger.debug(f"Chiamata a procedura catasto.logout_utente_sessione per utente {user_id}, sessione {session_id[:8]}...")
                cur.execute(call_proc_str, params)

                # La procedura logout_utente_sessione aggiorna la tabella sessioni_accesso.
                # Ora, puliamo le variabili di audit SULLA STESSA CONNESSIONE prima del commit.
                self._clear_audit_session_variables_with_conn(conn)

                # Esegui il commit se tutto è andato bene fino a qui
                conn.commit() 
                self.logger.info(f"Logout per utente ID {user_id}, sessione {session_id[:8]}... completato e variabili audit pulite.")
                return True
        except psycopg2.OperationalError as op_err: # Cattura specificamente OperationalError
            self.logger.error(f"Errore OPERAZIONALE DB durante il logout dell'utente {user_id} (sessione {session_id[:8]}...): {op_err}", exc_info=True)
            # Qui la connessione è quasi certamente chiusa dal server.
            # Non tentare rollback o putconn, ma chiudi forzatamente se possibile.
            if conn and not conn.closed:
                try:
                    conn.close() # Tenta una chiusura pulita se non è già chiusa
                    self.logger.warning(f"Connessione {id(conn)} chiusa forzatamente dopo OperationalError.")
                except Exception as close_err:
                    self.logger.error(f"Errore durante la chiusura forzata della connessione dopo OperationalError: {close_err}")
            return False # Indica che il logout al server è fallito
        except psycopg2.Error as e: # Cattura altri errori psycopg2 (es. InterfaceError se non è già stato chiuso)
            self.logger.error(f"Errore DB generico durante il logout dell'utente {user_id} (sessione {session_id[:8]}...): {e}", exc_info=True)
            if conn and not conn.closed:
                try:
                    conn.rollback() # Tenta il rollback solo se la connessione è ancora aperta
                    self.logger.warning(f"Rollback eseguito per connessione {id(conn)} dopo errore DB.")
                except Exception as rb_err:
                    self.logger.error(f"Errore durante il rollback dopo errore DB: {rb_err}")
            return False
        except Exception as e:
            self.logger.error(f"Errore Python generico durante il logout dell'utente {user_id} (sessione {session_id[:8]}...): {e}", exc_info=True)
            # Nessun rollback necessario per errori Python che non sono DB-specifici
            return False
        finally:
            # Importante: Non chiamare self._release_connection(conn) nel finally
            # se la connessione potrebbe essere stata chiusa forzatamente sopra.
            # Il pool potrebbe avere un riferimento a una connessione "morta".
            # La gestione di `conn` è ora all'interno dei blocchi `except` per `OperationalError`.
            pass # Rimuovi il finally che chiama _release_connection(conn)
        

    def check_permission(self, utente_id: int, permesso_nome: str) -> bool:
        """Chiama la funzione SQL ha_permesso."""
        try:
            query = "SELECT ha_permesso(%s, %s) AS permesso"
            if self.execute_query(query, (utente_id, permesso_nome)): result = self.fetchone(); return result.get('permesso', False) if result else False
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB verifica permesso '{permesso_nome}' per utente ID {utente_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python verifica permesso '{permesso_nome}' per utente ID {utente_id}: {e}"); return False

    def get_utenti(self, solo_attivi: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Recupera un elenco di utenti, usando il pool."""
        conn = None
        utenti_list = []
        query = f"SELECT id, username, nome_completo, email, ruolo, attivo, ultimo_accesso FROM {self.schema}.utente"
        conditions = []
        params = []

        if solo_attivi is not None:
            conditions.append("attivo = %s")
            params.append(solo_attivi)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY username;"
        
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_utenti: {cur.mogrify(query, tuple(params) if params else None).decode('utf-8', 'ignore')}")
                cur.execute(query, tuple(params) if params else None)
                results = cur.fetchall()
                if results:
                    utenti_list = [dict(row) for row in results]
                self.logger.info(f"Recuperati {len(utenti_list)} utenti.")
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB durante il recupero degli utenti: {db_err}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Errore Python durante il recupero degli utenti: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn)
        return utenti_list
    def get_utente_by_id(self, utente_id: int) -> Optional[Dict[str, Any]]:
        """Recupera i dettagli di un singolo utente tramite ID, usando il pool."""
        if not isinstance(utente_id, int) or utente_id <= 0:
            self.logger.error(f"get_utente_by_id: utente_id non valido: {utente_id}")
            return None

        query = f"SELECT id, username, nome_completo, email, ruolo, attivo FROM {self.schema}.utente WHERE id = %s"
        conn = None
        try:
            conn = self._get_connection() # Ottiene connessione dal pool
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione get_utente_by_id per ID: {utente_id}")
                cur.execute(query, (utente_id,))
                user_data = cur.fetchone()
                if user_data:
                    return dict(user_data)
                else:
                    self.logger.warning(f"Nessun utente trovato con ID: {utente_id}")
                    return None
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_utente_by_id (ID: {utente_id}): {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            # Non sollevare eccezione per coerenza con la firma che restituisce Optional[Dict]
            return None
        except Exception as e:
            self.logger.error(f"Errore Python in get_utente_by_id (ID: {utente_id}): {e}", exc_info=True)
            return None
        finally:
            if conn:
                self._release_connection(conn)

    def update_user_details(self, utente_id: int, nome_completo: Optional[str] = None,
                            email: Optional[str] = None, ruolo: Optional[str] = None,
                            attivo: Optional[bool] = None) -> bool:
        """
        Aggiorna i dettagli di un utente. Utilizza il pool di connessioni.
        """
        if not any([nome_completo is not None, email is not None, ruolo is not None, attivo is not None]):
            self.logger.warning(f"Nessun dettaglio valido fornito per l'aggiornamento dell'utente ID {utente_id}.")
            return False # Nessuna operazione da eseguire se nessun campo valido è fornito

        fields_to_update = []
        params = []

        if nome_completo is not None:
            fields_to_update.append("nome_completo = %s")
            params.append(nome_completo)
        if email is not None:
            fields_to_update.append("email = %s")
            params.append(email)
        if ruolo is not None:
            if ruolo not in ['admin', 'archivista', 'consultatore']:
                self.logger.error(f"Ruolo non valido fornito per l'aggiornamento: {ruolo}")
                raise DBDataError(f"Ruolo non valido: {ruolo}") # Solleva eccezione per dati non validi
            fields_to_update.append("ruolo = %s")
            params.append(ruolo)
        if attivo is not None:
            fields_to_update.append("attivo = %s")
            params.append(attivo)
        
        if not fields_to_update: # Se, nonostante il check any(), nessun campo è stato aggiunto (improbabile)
            self.logger.info(f"Nessun campo effettivamente da aggiornare per utente ID {utente_id} (esclusa data_modifica).")
            return True # Nessuna modifica richiesta, consideralo successo

        fields_to_update.append("data_modifica = CURRENT_TIMESTAMP")
        params.append(utente_id) # Per la clausola WHERE

        query = f"UPDATE {self.schema}.utente SET {', '.join(fields_to_update)} WHERE id = %s"
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione UPDATE utente ID {utente_id}: {cur.mogrify(query, tuple(params)).decode('utf-8', 'ignore')}")
                cur.execute(query, tuple(params))
                if cur.rowcount == 0:
                    # Verifica se l'utente esiste per distinguere "non trovato" da "dati identici"
                    cur.execute(f"SELECT 1 FROM {self.schema}.utente WHERE id = %s", (utente_id,))
                    if not cur.fetchone():
                        conn.rollback()
                        self.logger.warning(f"Tentativo di aggiornare utente ID {utente_id} non trovato.")
                        raise DBNotFoundError(f"Utente con ID {utente_id} non trovato per l'aggiornamento.")
                    self.logger.info(f"Nessuna modifica effettiva ai dati per utente ID {utente_id} (valori già aggiornati o identici).")
                conn.commit()
                self.logger.info(f"Dettagli utente ID {utente_id} aggiornati.")
                return True
        except psycopg2.errors.UniqueViolation as uve:
            if conn: conn.rollback()
            constraint_name = getattr(uve.diag, 'constraint_name', 'N/D')
            msg = f"Errore aggiornamento utente ID {utente_id}: Email '{email}' potrebbe essere già in uso (vincolo: {constraint_name})."
            self.logger.error(msg + f" Dettaglio DB: {getattr(uve, 'pgerror', str(uve))}")
            raise DBUniqueConstraintError(msg, constraint_name=constraint_name, details=getattr(uve, 'pgerror', str(uve))) from uve
        except (DBDataError, DBMError) as e_custom: # Rilancia eccezioni custom
            if conn: conn.rollback()
            self.logger.error(f"Errore dati/DBM in update_user_details per ID {utente_id}: {e_custom}")
            raise
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB generico durante l'aggiornamento dell'utente ID {utente_id}: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            raise DBMError(f"Errore database durante l'aggiornamento utente: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python imprevisto durante l'aggiornamento dell'utente ID {utente_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante l'aggiornamento utente: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)
        # return False # Non dovrebbe essere raggiunto se le eccezioni sono gestite

    def reset_user_password(self, utente_id: int, new_password_hash: str) -> bool:
        """Resetta la password di un utente. Utilizza il pool di connessioni."""
        query = f"UPDATE {self.schema}.utente SET password_hash = %s, data_modifica = CURRENT_TIMESTAMP WHERE id = %s"
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (new_password_hash, utente_id))
                if cur.rowcount == 0:
                    conn.rollback()
                    self.logger.warning(f"Reset password fallito: utente ID {utente_id} non trovato.")
                    raise DBNotFoundError(f"Utente con ID {utente_id} non trovato per reset password.")
                conn.commit()
                self.logger.info(f"Password resettata per utente ID {utente_id}.")
                return True
        except (DBNotFoundError, DBMError) as e_custom:
            if conn: conn.rollback()
            self.logger.error(f"Errore in reset_user_password per ID {utente_id}: {e_custom}")
            raise
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB durante il reset password per utente ID {utente_id}: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            raise DBMError(f"Errore database durante il reset password: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python imprevisto durante il reset password per utente ID {utente_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante il reset password: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)

    def _update_user_active_status(self, utente_id: int, nuovo_stato_attivo: bool) -> bool:
        """Metodo helper per attivare o disattivare un utente."""
        query = f"UPDATE {self.schema}.utente SET attivo = %s, data_modifica = CURRENT_TIMESTAMP WHERE id = %s"
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (nuovo_stato_attivo, utente_id))
                if cur.rowcount == 0:
                    conn.rollback()
                    self.logger.warning(f"Aggiornamento stato attivo fallito: utente ID {utente_id} non trovato.")
                    raise DBNotFoundError(f"Utente con ID {utente_id} non trovato per aggiornamento stato.")
                conn.commit()
                status_str = "attivato" if nuovo_stato_attivo else "disattivato"
                self.logger.info(f"Utente ID {utente_id} {status_str}.")
                return True
        except (DBNotFoundError, DBMError) as e_custom:
            if conn: conn.rollback()
            self.logger.error(f"Errore in _update_user_active_status per ID {utente_id}: {e_custom}")
            raise
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB aggiornando stato utente ID {utente_id}: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            raise DBMError(f"Errore database aggiornando stato utente: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python imprevisto aggiornando stato utente ID {utente_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto aggiornando stato utente: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)

    def deactivate_user(self, utente_id: int) -> bool:
        """Disattiva un utente. Utilizza _update_user_active_status."""
        return self._update_user_active_status(utente_id, False)

    def activate_user(self, utente_id: int) -> bool:
        """Riattiva un utente. Utilizza _update_user_active_status."""
        return self._update_user_active_status(utente_id, True)

    def delete_user_permanently(self, utente_id: int) -> bool:
        """Elimina fisicamente un utente. Utilizza il pool di connessioni."""
        utente_da_eliminare = self.get_utente_by_id(utente_id) # Usa il metodo già corretto
        if not utente_da_eliminare: # Se get_utente_by_id restituisce None
            self.logger.warning(f"Tentativo di eliminare utente ID {utente_id} non trovato.")
            # Potresti sollevare DBNotFoundError qui o restituire False come fa il codice originale
            return False 
            
        if utente_da_eliminare.get('ruolo') == 'admin':
            conn_count = None
            try:
                conn_count = self._get_connection()
                with conn_count.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur_count:
                    cur_count.execute(f"SELECT COUNT(*) AS count FROM {self.schema}.utente WHERE ruolo = 'admin' AND attivo = TRUE")
                    count_result = cur_count.fetchone()
                    if count_result and count_result['count'] <= 1:
                        self.logger.error(f"Tentativo di eliminare l'unico utente amministratore attivo (ID: {utente_id}). Operazione negata.")
                        # Non sollevare eccezione, ma restituisci False per indicare fallimento dell'operazione logica
                        return False
            except Exception as e_count: # Qualsiasi errore durante il conteggio
                 self.logger.error(f"Errore durante il conteggio degli admin prima dell'eliminazione dell'utente ID {utente_id}: {e_count}", exc_info=True)
                 return False # Non procedere se non possiamo verificare il conteggio
            finally:
                if conn_count:
                    self._release_connection(conn_count)
        
        conn_delete = None
        try:
            conn_delete = self._get_connection()
            with conn_delete.cursor() as cur_delete:
                # FK da sessioni_accesso a utente è ON DELETE CASCADE, quindi non serve pulire sessioni_accesso manualmente
                # FK da audit_log a utente (app_user_id) è ON DELETE SET NULL (da script 15), quindi si aggiornerà automaticamente
                
                cur_delete.execute(f"DELETE FROM {self.schema}.utente WHERE id = %s", (utente_id,))
                if cur_delete.rowcount > 0:
                    conn_delete.commit()
                    self.logger.info(f"Utente ID {utente_id} eliminato fisicamente con successo.")
                    return True
                else:
                    # Questo caso è già coperto da get_utente_by_id sopra, ma per sicurezza
                    conn_delete.rollback()
                    self.logger.warning(f"Nessun utente trovato con ID {utente_id} per l'eliminazione fisica (controllo post-query).")
                    return False 
        except psycopg2.Error as db_err:
            if conn_delete: conn_delete.rollback()
            self.logger.error(f"Errore DB durante l'eliminazione fisica dell'utente ID {utente_id}: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            raise DBMError(f"Errore database durante l'eliminazione utente: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        except Exception as e:
            if conn_delete and not conn_delete.closed: conn_delete.rollback()
            self.logger.error(f"Errore Python imprevisto durante l'eliminazione fisica dell'utente ID {utente_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante l'eliminazione utente: {e}") from e
        finally:
            if conn_delete:
                self._release_connection(conn_delete)

    # --- Metodi Sistema Backup (Invariati rispetto a comune_id) ---
    def get_audit_logs(self,
                       filters: Optional[Dict[str, Any]] = None,
                       page: int = 1,
                       page_size: int = 50, # Numero di record per pagina
                       sort_by: str = 'timestamp', # Colonna di default per l'ordinamento
                       sort_order: str = 'DESC' # Ordine di default
                      ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Recupera i record dalla tabella audit_log con filtri, paginazione e ordinamento.

        Args:
            filters: Un dizionario contenente i filtri. Chiavi possibili:
                'table_name': str (ricerca parziale con ILIKE)
                'operation_char': str ('I', 'U', o 'D')
                'app_user_id': int
                'record_id': int
                'start_datetime': datetime
                'end_datetime': datetime
                'search_text_json': str (ricerca parziale ILIKE su dati_prima e dati_dopo)
                'ip_address': str (ricerca parziale ILIKE)
            page: Numero della pagina da recuperare (1-based).
            page_size: Numero di record per pagina.
            sort_by: Nome della colonna per l'ordinamento (default: 'timestamp').
                     Colonne valide: 'id', 'timestamp', 'tabella', 'operazione', 'record_id', 'app_user_id', 'ip_address'.
            sort_order: 'ASC' o 'DESC' (default: 'DESC').

        Returns:
            Una tupla contenente:
                - Una lista di dizionari, dove ogni dizionario rappresenta un record di log.
                - Il numero totale di record che soddisfano i filtri (per la paginazione).
        """
        if filters is None:
            filters = {}

        query_conditions = []
        query_params = []

        # Costruzione delle condizioni WHERE in base ai filtri
        if filters.get("table_name"):
            query_conditions.append("tabella ILIKE %s")
            query_params.append(f"%{filters['table_name']}%")
        
        if filters.get("operation_char"):
            query_conditions.append("operazione = %s")
            query_params.append(filters["operation_char"])
            
        if filters.get("app_user_id") is not None: # Controlla esplicitamente per None perché 0 è un ID valido
            query_conditions.append("app_user_id = %s")
            query_params.append(filters["app_user_id"])

        if filters.get("record_id") is not None:
            query_conditions.append("record_id = %s")
            query_params.append(filters["record_id"])

        if filters.get("start_datetime"):
            query_conditions.append("timestamp >= %s")
            query_params.append(filters["start_datetime"])

        if filters.get("end_datetime"):
            query_conditions.append("timestamp <= %s")
            query_params.append(filters["end_datetime"])
            
        if filters.get("ip_address"):
            query_conditions.append("ip_address ILIKE %s")
            query_params.append(f"%{filters['ip_address']}%")

        if filters.get("search_text_json"):
            # Attenzione: questa ricerca può essere lenta su grandi volumi di dati JSON
            # se non ci sono indici GIN appropriati sui campi JSONB.
            json_search_text = f"%{filters['search_text_json']}%"
            query_conditions.append("(dati_prima::text ILIKE %s OR dati_dopo::text ILIKE %s)")
            query_params.extend([json_search_text, json_search_text])

        where_clause = ""
        if query_conditions:
            where_clause = "WHERE " + " AND ".join(query_conditions)

        # Query per contare il totale dei record (per la paginazione)
        count_query = f"SELECT COUNT(*) FROM {self.schema}.audit_log {where_clause};"

        # Validazione e costruzione della clausola ORDER BY
        allowed_sort_columns = ['id', 'timestamp', 'tabella', 'operazione', 'record_id', 'app_user_id', 'ip_address']
        if sort_by not in allowed_sort_columns:
            sort_by = 'timestamp' # Default sicuro
        if sort_order.upper() not in ['ASC', 'DESC']:
            sort_order = 'DESC' # Default sicuro
        
        order_by_clause = f"ORDER BY {sort_by} {sort_order.upper()}"
        if sort_by != 'id': # Aggiungi 'id' come secondo criterio per un ordinamento stabile
            order_by_clause += f", id {sort_order.upper()}"


        # Calcolo dell'offset per la paginazione
        offset = (page - 1) * page_size

        # Query per recuperare i dati paginati
        data_query = f"""
            SELECT id, timestamp, app_user_id, session_id, tabella, operazione, record_id, ip_address, utente, dati_prima, dati_dopo
            FROM {self.schema}.audit_log
            {where_clause}
            {order_by_clause}
            LIMIT %s OFFSET %s;
        """
        query_params_data = query_params + [page_size, offset]
        
        logs = []
        total_records = 0

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    # Esegui la query di conteggio
                    self.logger.debug(f"Audit Log Count Query: {cur.mogrify(count_query, query_params).decode('utf-8', 'ignore')}")
                    cur.execute(count_query, query_params)
                    total_records_result = cur.fetchone()
                    if total_records_result:
                        total_records = total_records_result[0]
                    
                    if total_records > 0:
                        # Esegui la query per i dati
                        self.logger.debug(f"Audit Log Data Query: {cur.mogrify(data_query, query_params_data).decode('utf-8', 'ignore')}")
                        cur.execute(data_query, query_params_data)
                        logs = [dict(row) for row in cur.fetchall()]
                        self.logger.info(f"Recuperati {len(logs)} record di audit log (pagina {page} di {((total_records - 1) // page_size) + 1}). Totale filtrati: {total_records}")
                    else:
                        self.logger.info("Nessun record di audit log trovato con i filtri specificati.")
                        
        except psycopg2.Error as e:
            self.logger.error(f"Errore DB durante il recupero dei log di audit: {e}", exc_info=True)
            # Potresti voler sollevare un'eccezione qui o ritornare un indicatore di errore
        except Exception as e:
            self.logger.error(f"Errore generico durante il recupero dei log di audit: {e}", exc_info=True)

        return logs, total_records
    def register_backup_log(self, nome_file: str, utente: str, tipo: str, esito: bool,
                            percorso_file: str, dimensione_bytes: Optional[int] = None,
                            messaggio: Optional[str] = None) -> Optional[int]:
        """Chiama la funzione SQL registra_backup."""
        try:
            query = "SELECT registra_backup(%s, %s, %s, %s, %s, %s, %s)"
            params = (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)
            if self.execute_query(query, params):
                 result = self.fetchone(); self.commit(); backup_id = result.get('registra_backup') if result else None
                 if backup_id: logger.info(f"Log backup registrato ID: {backup_id} per '{nome_file}'")
                 else: logger.error(f"registra_backup non ha restituito ID per '{nome_file}'.")
                 return backup_id
        except psycopg2.Error as db_err: logger.error(f"Errore DB reg log backup '{nome_file}': {db_err}")
        except Exception as e: logger.error(f"Errore Python reg log backup '{nome_file}': {e}"); self.rollback()
        return None
    
    # Assicurati che anche i metodi come _find_executable, get_backup_command_parts, 
    # get_restore_command_parts siano presenti come li avevamo definiti.
    # Non interagiscono direttamente con il pool per le loro query, ma usano parametri da self.conn_params_dict
    def _find_executable(self, name: str) -> Optional[str]:
        executable_path = shutil.which(name)
        if executable_path:
            self.logger.info(f"Trovato eseguibile '{name}' in: {executable_path}")
            return executable_path
        else:
            self.logger.warning(f"Eseguibile '{name}' non trovato nel PATH di sistema.")
            return None # Modificato da return "" per coerenza con Optional[str]


    def _resolve_executable_path(self, user_provided_path: str, default_name: str) -> Optional[str]:
        # Se l'utente fornisce un percorso valido, usa quello
        if user_provided_path and os.path.isabs(user_provided_path) and os.path.exists(user_provided_path) and os.path.isfile(user_provided_path):
            self.logger.info(f"Utilizzo del percorso eseguibile fornito dall'utente: {user_provided_path} (per default {default_name})")
            return user_provided_path
        elif user_provided_path: 
            self.logger.warning(f"Percorso fornito '{user_provided_path}' per '{default_name}' non valido. Tento di cercare '{default_name}' nel PATH.")

        # Altrimenti, cerca il default_name nel PATH
        found_path_in_system = shutil.which(default_name) # default_name qui sarà "pg_restore.exe" o "psql.exe"
        if found_path_in_system:
            self.logger.info(f"Trovato eseguibile '{default_name}' nel PATH di sistema: {found_path_in_system}")
            return found_path_in_system
        else:
            self.logger.error(f"Eseguibile '{default_name}' non trovato nel PATH e nessun percorso valido fornito.")
            return None

    def get_backup_command_parts(self,
                                 backup_file_path: str,
                                 pg_dump_executable_path_ui: str,
                                 format_type: str = "custom",
                                 include_blobs: bool = False
                                ) -> Optional[List[str]]:
        
        actual_pg_dump_path = self._resolve_executable_path(pg_dump_executable_path_ui, "pg_dump.exe")
        if not actual_pg_dump_path:
            return None

        # USA L'ATTRIBUTO CORRETTO: _main_db_conn_params
        db_user = self._main_db_conn_params.get("user")
        db_host = self._main_db_conn_params.get("host")
        db_port = str(self._main_db_conn_params.get("port"))
        db_name = self._main_db_conn_params.get("dbname")

        if not all([db_user, db_host, db_port, db_name]):
            self.logger.error("Parametri di connessione mancanti per il backup (da _main_db_conn_params).")
            return None

        command = [actual_pg_dump_path, "-U", db_user, "-h", db_host, "-p", db_port]
        
        if format_type == "custom": command.append("-Fc")
        elif format_type == "plain": command.append("-Fp")
        else:
            self.logger.error(f"Formato di backup non supportato: {format_type}"); return None
        command.extend(["--file", backup_file_path])
        if include_blobs: command.append("--blobs")
        command.append(db_name)
        self.logger.info(f"Comando di backup preparato: {' '.join(command)}")
        return command

    def get_restore_command_parts(self,
                                  backup_file_path: str,
                                  pg_tool_executable_path_ui: str
                                 ) -> Optional[List[str]]:
        # USA L'ATTRIBUTO CORRETTO: _main_db_conn_params
        db_user = self._main_db_conn_params.get("user")
        db_host = self._main_db_conn_params.get("host")
        db_port = str(self._main_db_conn_params.get("port"))
        db_name = self._main_db_conn_params.get("dbname")

        if not all([db_user, db_host, db_port, db_name]):
            self.logger.error("Parametri di connessione mancanti per il ripristino (da _main_db_conn_params).")
            return None

        command: List[str] = []
        _, file_extension = os.path.splitext(backup_file_path)
        file_extension = file_extension.lower()
        actual_pg_tool_path = None

        if file_extension in [".dump", ".backup", ".custom"]:
            actual_pg_tool_path = self._resolve_executable_path(pg_tool_executable_path_ui, "pg_restore.exe")
            if not actual_pg_tool_path: return None
            command = [actual_pg_tool_path, "-U", db_user, "-h", db_host, "-p", db_port, "-d", db_name]
            command.extend(["--clean", "--if-exists", "--verbose"]) # Opzioni comuni per pg_restore
            command.append(backup_file_path)
        elif file_extension == ".sql":
            actual_pg_tool_path = self._resolve_executable_path(pg_tool_executable_path_ui, "psql.exe")
            if not actual_pg_tool_path: return None
            command = [actual_pg_tool_path, "-U", db_user, "-h", db_host, "-p", db_port, "-d", db_name]
            command.extend(["-f", backup_file_path, "-v", "ON_ERROR_STOP=1"]) # Esegui script SQL con psql
        else:
            self.logger.error(f"Formato file di backup non riconosciuto o non supportato: '{file_extension}'"); return None
        self.logger.info(f"Comando di ripristino preparato: {' '.join(command)}")
        return command

    def _resolve_executable_path(self, user_provided_path: str, default_name: str) -> Optional[str]:
        if user_provided_path and os.path.isabs(user_provided_path) and os.path.exists(user_provided_path) and os.path.isfile(user_provided_path):
            self.logger.info(f"Utilizzo del percorso eseguibile fornito: {user_provided_path}")
            return user_provided_path
        elif user_provided_path:
             self.logger.warning(f"Percorso fornito '{user_provided_path}' per '{default_name}' non valido. Tento ricerca nel PATH.")
        
        found_path_in_system = shutil.which(default_name)
        if found_path_in_system:
            self.logger.info(f"Trovato eseguibile '{default_name}' nel PATH: {found_path_in_system}")
            return found_path_in_system
        else:
            self.logger.error(f"Eseguibile '{default_name}' non trovato nel PATH e nessun percorso valido fornito.")
            # Fornire un messaggio all'utente nella GUI che il tool non è stato trovato e deve essere configurato
            return None
    def cleanup_old_backup_logs(self, giorni_conservazione: int = 30) -> bool:
        """Chiama la procedura SQL pulizia_backup_vecchi."""
        try:
            call_proc = "CALL pulizia_backup_vecchi(%s)"
            if self.execute_query(call_proc, (giorni_conservazione,)): self.commit(); logger.info(f"Eseguita pulizia log backup più vecchi di {giorni_conservazione} giorni."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB pulizia log backup: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python pulizia log backup: {e}"); self.rollback(); return False

    def generate_backup_script(self, backup_dir: str) -> Optional[str]:
        """Chiama la funzione SQL genera_script_backup_automatico."""
        try:
            query = "SELECT genera_script_backup_automatico(%s) AS script_content"
            if self.execute_query(query, (backup_dir,)): result = self.fetchone(); return result.get('script_content') if result else None
        except psycopg2.Error as db_err: logger.error(f"Errore DB gen script backup: {db_err}"); return None
        except Exception as e: logger.error(f"Errore Python gen script backup: {e}"); return None
        return None

    def get_backup_logs(self, limit: int = 20) -> List[Dict]:
        """Recupera gli ultimi N log di backup dal registro."""
        try:
            query = "SELECT * FROM backup_registro ORDER BY timestamp DESC LIMIT %s"
            if self.execute_query(query, (limit,)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_backup_logs: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_backup_logs: {e}"); return []
        return []

    
    # --- Metodi Ricerca Avanzata (MODIFICATI) ---

    def ricerca_avanzata_possessori(self,
                                    query_text: str,
                                    similarity_threshold: Optional[float] = 0.2 # Manteniamo il default che aveva
                                   ) -> List[Dict[str, Any]]:
        """
        Esegue una ricerca avanzata di possessori utilizzando le funzioni di similarità di PostgreSQL.
        Utilizza una soglia di similarità specificata e il pool di connessioni.
        La funzione SQL sottostante è catasto.ricerca_avanzata_possessori(TEXT, REAL).
        """
        
        # La funzione SQL accetta (TEXT, REAL)
        query = f"SELECT * FROM {self.schema}.ricerca_avanzata_possessori(%s::TEXT, %s::REAL);"
        params = (query_text, similarity_threshold)
        
        conn = None  # Inizializza la variabile di connessione
        try:
            conn = self._get_connection() # Ottiene una connessione dal pool
            
            # Usa DictCursor per ottenere risultati come dizionari
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Logging della query e dei parametri
                # self.logger.debug(f"Esecuzione query (ricerca avanzata possessori): Query='{cur.mogrify(query, params).decode('utf-8', 'ignore')}'")
                # Semplifichiamo il logging per evitare potenziali problemi con mogrify in alcuni contesti:
                self.logger.debug(f"Esecuzione query (ricerca avanzata possessori): Query='{query}', Params='{params}'")

                cur.execute(query, params)
                results_raw = cur.fetchall()
            
            # Trasforma i risultati grezzi in una lista di dizionari Python
            results = [dict(row) for row in results_raw] if results_raw else []

            if results:
                self.logger.info(f"Ricerca avanzata possessori per '{query_text}' (soglia: {similarity_threshold}) ha prodotto {len(results)} risultati.")
            else:
                self.logger.info(f"Nessun risultato per ricerca avanzata possessori: '{query_text}' (soglia: {similarity_threshold}).")
            return results
            
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB durante la ricerca avanzata dei possessori: {db_err}", exc_info=True)
            if conn: conn.rollback() # Rollback in caso di errore sulla connessione specifica
            return [] # Restituisce lista vuota in caso di errore DB
        except Exception as e:
            self.logger.error(f"Errore Python imprevisto durante la ricerca avanzata dei possessori: {e}", exc_info=True)
            if conn: conn.rollback() # Anche qui, per sicurezza
            return [] # Restituisce lista vuota in caso di errore generico
        finally:
            if conn:
                self._release_connection(conn) # Rilascia SEMPRE la connessione al pool

    def ricerca_avanzata_immobili_gui(self,
                                   comune_id: Optional[int] = None,
                                   localita_id: Optional[int] = None,
                                   natura_search: Optional[str] = None,
                                   classificazione_search: Optional[str] = None,
                                   consistenza_search: Optional[str] = None,
                                   piani_min: Optional[int] = None,
                                   piani_max: Optional[int] = None,
                                   vani_min: Optional[int] = None,
                                   vani_max: Optional[int] = None,
                                   nome_possessore_search: Optional[str] = None,
                                   data_inizio_possesso_search: Optional[date] = None, # Nome corretto dal metodo Python
                                   data_fine_possesso_search: Optional[date] = None   # Nome corretto dal metodo Python
                                   ) -> List[Dict[str, Any]]:
        """Chiama la funzione SQL ricerca_avanzata_immobili (DA DEFINIRE e MODIFICARE per comune_id)."""
        logger.warning("La funzione SQL 'ricerca_avanzata_immobili' potrebbe non essere definita o aggiornata per comune_id.")
        # Query con segnaposto posizionali
        query = """
            SELECT * FROM catasto.cerca_immobili_avanzato(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
        """
        # I parametri devono essere NELL'ESATTO ORDINE della definizione della funzione SQL
        params = (
            comune_id,                     # p_comune_id INTEGER
            localita_id,                   # p_localita_id INTEGER
            natura_search,                 # p_natura_search TEXT
            classificazione_search,        # p_classificazione_search TEXT
            consistenza_search,            # p_consistenza_search TEXT
            piani_min,                     # p_piani_min INTEGER
            piani_max,                     # p_piani_max INTEGER
            vani_min,                      # p_vani_min INTEGER
            vani_max,                      # p_vani_max INTEGER
            nome_possessore_search,        # p_nome_possessore_search TEXT
            data_inizio_possesso_search,   # p_data_inizio_possesso DATE
            data_fine_possesso_search      # p_data_fine_possesso DATE
        )

        self.logger.debug(f"Chiamata a catasto.cerca_immobili_avanzato con parametri POSIZIONALI: {params}")

        if self.execute_query(query, params):
            results = self.fetchall()
            self.logger.info(f"Ricerca avanzata immobili GUI ha restituito {len(results)} risultati.")
            return results if results else []
        else:
            self.logger.error("Errore durante l'esecuzione di ricerca_avanzata_immobili_gui.")
            return []

    # --- Metodi Funzionalità Storiche Avanzate (MODIFICATI) ---

    def get_historical_periods(self) -> List[Dict[str, Any]]:
        """
        Recupera i periodi storici definiti dalla tabella 'periodo_storico',
        utilizzando il pool di connessioni.
        Restituisce una lista di dizionari o una lista vuota in caso di errore.
        """
        conn = None
        periodi_list: List[Dict[str, Any]] = [] # Inizializza a lista vuota con tipo esplicito
        try:
            # Assicurati che self.schema sia corretto e che la tabella si chiami 'periodo_storico'
            query = f"SELECT id, nome, anno_inizio, anno_fine, descrizione FROM {self.schema}.periodo_storico ORDER BY anno_inizio;"
            
            conn = self._get_connection() # Ottiene una connessione dal pool
            # Usa DictCursor per ottenere risultati come dizionari (o oggetti DictRow simili a dizionari)
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione query get_historical_periods: {query}")
                cur.execute(query)
                results = cur.fetchall() # Restituisce una lista di DictRow
                
                if results:
                    # Converti esplicitamente DictRow in dict, anche se spesso non è strettamente necessario
                    # per l'accesso, garantisce che il tipo restituito sia esattamente List[Dict].
                    periodi_list = [dict(row) for row in results]
                
                self.logger.info(f"Recuperati {len(periodi_list)} periodi storici.")
        
        except psycopg2.Error as db_err: # Cattura errori specifici di psycopg2/DB
            self.logger.error(f"Errore DB in get_historical_periods: {db_err}", exc_info=True)
            # Non sollevare eccezione, restituisci lista vuota come da comportamento precedente
            # per non interrompere la UI, che mostrerà "Nessun periodo..."
        except Exception as e: # Cattura altri errori Python imprevisti
            self.logger.error(f"Errore Python generico in get_historical_periods: {e}", exc_info=True)
        finally:
            if conn:
                self._release_connection(conn) # Rilascia SEMPRE la connessione al pool
        
        return periodi_list
    def get_historical_name(self, entity_type: str, entity_id: int, year: Optional[int] = None) -> Optional[Dict]:
        """Chiama la funzione SQL get_nome_storico (SQL aggiornata per join)."""
        try:
            # Funzione SQL aggiornata per join corretti
            if year is None: year = datetime.now().year
            query = "SELECT * FROM get_nome_storico(%s, %s, %s)"
            if self.execute_query(query, (entity_type, entity_id, year)): return self.fetchone()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_historical_name ({entity_type} ID {entity_id}): {db_err}"); return None
        except Exception as e: logger.error(f"Errore Python get_historical_name ({entity_type} ID {entity_id}): {e}"); return None
        return None

    def register_historical_name(self, entity_type: str, entity_id: int, name: str,
                                 period_id: int, year_start: int, year_end: Optional[int] = None,
                                 notes: Optional[str] = None) -> bool:
        """Chiama la procedura SQL registra_nome_storico."""
        try:
            call_proc = "CALL registra_nome_storico(%s, %s, %s, %s, %s, %s, %s)"
            params = (entity_type, entity_id, name, period_id, year_start, year_end, notes)
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Registrato nome storico '{name}' per {entity_type} ID {entity_id}."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB registrazione nome storico: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python registrazione nome storico: {e}"); self.rollback(); return False

    def search_historical_documents(self, title: Optional[str] = None, doc_type: Optional[str] = None,
                                    period_id: Optional[int] = None, year_start: Optional[int] = None,
                                    year_end: Optional[int] = None, partita_id: Optional[int] = None) -> List[Dict]:
        """Chiama la funzione SQL ricerca_documenti_storici (SQL aggiornata per join)."""
        try:
            # Funzione SQL aggiornata per join corretti
            query = "SELECT * FROM ricerca_documenti_storici(%s, %s, %s, %s, %s, %s)"
            params = (title, doc_type, period_id, year_start, year_end, partita_id)
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB search_historical_documents: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python search_historical_documents: {e}"); return []
        return []
    # All'interno della classe CatastoDBManager in catasto_db_manager.py
# Assicurati che le importazioni necessarie siano presenti (datetime, Optional, Dict, Any, List, psycopg2, ecc.)

    def get_periodo_storico_details(self, periodo_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera i dettagli completi di un singolo periodo storico dal database.
        """
        if not isinstance(periodo_id, int) or periodo_id <= 0:
            self.logger.error(f"get_periodo_storico_details: periodo_id non valido: {periodo_id}")
            return None

        query = f"SELECT * FROM {self.schema}.periodo_storico WHERE id = %s;"
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione query get_periodo_storico_details per ID: {periodo_id}")
                cur.execute(query, (periodo_id,))
                result = cur.fetchone()
                if result:
                    self.logger.info(f"Dettagli recuperati per periodo storico ID {periodo_id}.")
                    return dict(result)
                else:
                    self.logger.warning(f"Nessun periodo storico trovato con ID {periodo_id}.")
                    return None
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB in get_periodo_storico_details (ID: {periodo_id}): {db_err}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Errore Python generico in get_periodo_storico_details (ID: {periodo_id}): {e}", exc_info=True)
            return None
        finally:
            if conn:
                self._release_connection(conn)

    # All'interno della classe CatastoDBManager in catasto_db_manager.py

    def update_periodo_storico(self, periodo_id: int, dati_modificati: Dict[str, Any]) -> bool:
        """
        Aggiorna i dati di un periodo storico esistente.
        I campi aggiornabili sono: nome, anno_inizio, anno_fine, descrizione.
        La colonna 'data_modifica' è stata rimossa da questa query poiché non presente
        nello schema DB fornito.
        Solleva eccezioni specifiche in caso di errore.
        """
        if not isinstance(periodo_id, int) or periodo_id <= 0:
            self.logger.error(f"update_periodo_storico: ID periodo storico non valido: {periodo_id}")
            raise DBDataError(f"ID periodo storico non valido: {periodo_id}")
        if not dati_modificati: # Se il dizionario è vuoto
            self.logger.warning(f"update_periodo_storico: Nessun dato fornito per aggiornare periodo ID {periodo_id}.")
            # Potrebbe essere considerato un no-op e restituire True se non è un errore.
            # Per ora, solleviamo un errore se nessun dato modificabile è fornito.
            raise DBDataError("Nessun dato fornito per l'aggiornamento del periodo storico.")

        set_clauses = []
        params = []

        campi_permessi = {
            "nome": "nome", 
            "anno_inizio": "anno_inizio", 
            "anno_fine": "anno_fine", 
            "descrizione": "descrizione"
        }

        modifica_effettuata = False
        for key_dict, col_db in campi_permessi.items():
            if key_dict in dati_modificati:
                valore_ui = dati_modificati[key_dict]
                
                if key_dict == "nome" and (valore_ui is None or not str(valore_ui).strip()):
                    raise DBDataError("Il nome del periodo storico non può essere vuoto.")
                
                # Gestione specifica per anno_fine che può essere None
                if key_dict == "anno_fine":
                    if isinstance(valore_ui, str) and valore_ui.strip() == "":
                        params.append(None) # Stringa vuota dalla UI diventa NULL
                    elif valore_ui == 0 and self.periodo_id_spinbox.minimum() == 0 and self.periodo_id_spinbox.specialValueText().strip() != "": # Esempio se 0 è "non impostato"
                        params.append(None)
                    else:
                        params.append(valore_ui) # Altrimenti usa il valore (int o None)
                else:
                    params.append(valore_ui)
                
                set_clauses.append(f"{col_db} = %s")
                modifica_effettuata = True

        if not modifica_effettuata: # Se nessuna delle chiavi permesse era in dati_modificati
            self.logger.info(f"Nessun campo aggiornabile fornito per periodo storico ID {periodo_id}. Nessuna operazione eseguita.")
            return True # Consideriamo un successo (nessuna modifica richiesta)

        # RIMOZIONE DI: set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
        # Se la colonna data_modifica non esiste, non possiamo aggiornarla.
        # Se volesse tracciare la modifica, dovrebbe prima aggiungere la colonna al DB.

        query = f"UPDATE {self.schema}.periodo_storico SET {', '.join(set_clauses)} WHERE id = %s;"
        params.append(periodo_id)
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.info(f"Tentativo di aggiornare periodo storico ID {periodo_id} con dati: {dati_modificati}")
                log_query_str = cur.mogrify(query, tuple(params)).decode('utf-8', 'ignore') if params else query
                self.logger.debug(f"Esecuzione query update_periodo_storico: {log_query_str}")
                cur.execute(query, tuple(params))
                
                if cur.rowcount == 0:
                    # Verifica se il record esiste per distinguere "non trovato" da "dati identici"
                    cur.execute(f"SELECT 1 FROM {self.schema}.periodo_storico WHERE id = %s", (periodo_id,))
                    if not cur.fetchone():
                        conn.rollback() # Annulla perché il record non è stato trovato
                        self.logger.warning(f"Tentativo di aggiornare periodo storico ID {periodo_id} che non è stato trovato.")
                        raise DBNotFoundError(f"Periodo storico con ID {periodo_id} non trovato per l'aggiornamento.")
                    # Se esiste ma rowcount è 0, significa che i valori forniti erano identici a quelli esistenti.
                    self.logger.info(f"Nessuna modifica effettiva ai dati per periodo ID {periodo_id} (valori già aggiornati o identici).")
                
                conn.commit()
                self.logger.info(f"Periodo storico ID {periodo_id} aggiornato con successo (o i valori erano identici).")
                return True

        except psycopg2.errors.UniqueViolation as uve:
            if conn: conn.rollback()
            constraint_name = getattr(uve.diag, 'constraint_name', "N/D")
            msg = f"Impossibile aggiornare il periodo storico: i dati violano un vincolo di unicità (vincolo: {constraint_name})."
            if "periodo_storico_nome_key" in str(constraint_name).lower(): # Adatta al nome del tuo vincolo UNIQUE per 'nome'
                 msg += f" Esiste già un periodo con lo stesso nome."
            raise DBUniqueConstraintError(msg, constraint_name=constraint_name, details=str(uve)) from uve
        except psycopg2.errors.CheckViolation as cve:
            if conn: conn.rollback()
            constraint_name = getattr(cve.diag, 'constraint_name', "N/D")
            msg = f"I dati forniti per il periodo storico violano una regola di validazione (vincolo: {constraint_name})."
            if "periodo_storico_check_anni" in str(constraint_name).lower(): # Esempio di nome vincolo
                 msg += " L'anno di fine non può essere precedente all'anno di inizio."
            raise DBDataError(msg) from cve
        except psycopg2.Error as db_err: # Inclusi UndefinedColumn se la query fosse ancora errata
            if conn: conn.rollback()
            error_detail = getattr(db_err, 'pgerror', str(db_err))
            self.logger.error(f"Errore DB aggiornando periodo storico ID {periodo_id}: {error_detail}", exc_info=True)
            raise DBMError(f"Errore database aggiornando periodo storico ID {periodo_id}: {error_detail}") from db_err
        except Exception as e:
            if conn: conn.rollback()
            self.logger.error(f"Errore Python imprevisto aggiornando periodo storico ID {periodo_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto aggiornando periodo storico ID {periodo_id}: {str(e)}") from e
        finally:
            if conn:
                self._release_connection(conn)
        # return False # Non dovrebbe essere raggiunto se le eccezioni sono gestite
    def get_property_genealogy(self, partita_id: int) -> List[Dict]:
        """Chiama la funzione SQL albero_genealogico_proprieta (SQL aggiornata per join)."""
        try:
            # Funzione SQL aggiornata per join corretti
            query = "SELECT * FROM albero_genealogico_proprieta(%s)"
            if self.execute_query(query, (partita_id,)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_property_genealogy (ID: {partita_id}): {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_property_genealogy (ID: {partita_id}): {e}"); return []
        return []

    def get_cadastral_stats_by_period(self, comune_id: Optional[int] = None, year_start: int = 1900, # Usa comune_id
                                       year_end: Optional[int] = None) -> List[Dict]:
        """Chiama la funzione SQL statistiche_catastali_periodo (MODIFICATA per comune_id)."""
        logger.warning("La funzione SQL 'statistiche_catastali_periodo' potrebbe non essere aggiornata per comune_id.")
        try:
            # Assumiamo funzione SQL aggiornata per comune_id
            if year_end is None: year_end = datetime.now().year
            query = "SELECT * FROM statistiche_catastali_periodo(%s, %s, %s)"
            params = (comune_id, year_start, year_end) # Passa ID
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.errors.UndefinedFunction: logger.warning("Funzione 'statistiche_catastali_periodo' non trovata."); return []
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_cadastral_stats_by_period: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_cadastral_stats_by_period: {e}"); return []
        return []

    def link_document_to_partita(self, document_id: int, partita_id: int,
                                 relevance: str = 'correlata', notes: Optional[str] = None) -> bool:
        """Collega un documento storico a una partita."""
        if relevance not in ['primaria', 'secondaria', 'correlata']: logger.error(f"Rilevanza non valida: '{relevance}'"); return False
        query = """
            INSERT INTO documento_partita (documento_id, partita_id, rilevanza, note) VALUES (%s, %s, %s, %s)
            ON CONFLICT (documento_id, partita_id) DO UPDATE SET rilevanza = EXCLUDED.rilevanza, note = EXCLUDED.note
        """
        try:
            if self.execute_query(query, (document_id, partita_id, relevance, notes)): self.commit(); logger.info(f"Link creato/aggiornato Doc {document_id} - Partita {partita_id}."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB link doc-partita: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python link doc-partita: {e}"); self.rollback(); return False
        
    # All'interno della classe CatastoDBManager, nel file catasto_db_manager.py

    def ricerca_avanzata_immobili_gui(self, comune_id: Optional[int] = None, localita_id: Optional[int] = None,
                                      natura_search: Optional[str] = None, classificazione_search: Optional[str] = None,
                                      consistenza_search: Optional[str] = None, # Ricerca testuale per consistenza
                                      piani_min: Optional[int] = None, piani_max: Optional[int] = None,
                                      vani_min: Optional[int] = None, vani_max: Optional[int] = None,
                                      nome_possessore_search: Optional[str] = None,
                                      data_inizio_possesso_search: Optional[date] = None, # Previsto per il futuro
                                      data_fine_possesso_search: Optional[date] = None    # Previsto per il futuro
                                     ) -> List[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    # La stringa della query ora corrisponde ai 12 parametri della funzione SQL estesa
                    # I cast ::TIPODATO sono una buona pratica se i default nella funzione SQL non sono espliciti con ::TIPODATO
                    # o se si vuole essere estremamente sicuri.
                    # Se la funzione SQL ha DEFAULT NULL e tipi chiari, i cast qui potrebbero non essere strettamente necessari
                    # ma non fanno male.
                    query = f"""
                        SELECT * FROM {self.schema}.ricerca_avanzata_immobili(
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """
                    # Nota: i parametri devono essere nell'ordine esatto definito dalla funzione SQL
                    params = (
                        comune_id, localita_id, natura_search, classificazione_search, consistenza_search,
                        piani_min, piani_max, vani_min, vani_max, nome_possessore_search,
                        data_inizio_possesso_search, data_fine_possesso_search
                    )

                    self.logger.debug(f"Chiamata a {self.schema}.ricerca_avanzata_immobili con parametri POSIZIONALI: {params}")
                    cur.execute(query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    self.logger.info(f"Ricerca avanzata immobili ha restituito {len(results)} risultati.")
                    return results
        except psycopg2.Error as e:
            self.logger.error(f"Errore DB specifico durante l'esecuzione di ricerca_avanzata_immobili_gui: {e}", exc_info=True)
            # Potresti voler sollevare un'eccezione personalizzata o gestire l'errore qui
            return []
        except Exception as e:
            self.logger.error(f"Errore generico durante ricerca_avanzata_immobili_gui: {e}", exc_info=True)
            return []
    def set_audit_session_variables(self, app_user_id: Optional[int], session_id: Optional[str]) -> bool:
        """Imposta le variabili di sessione PostgreSQL per l'audit log, usando il pool."""
        if app_user_id is None or session_id is None:
            self.logger.warning("Tentativo di impostare variabili audit con None.")
            return False
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Pulisci prima, nel caso fossero già impostate da una sessione precedente sulla stessa connessione del pool (improbabile ma sicuro)
                cur.execute("RESET ALL;") # Resetta tutte le GUC di sessione custom
                                          # O più specificamente:
                # cur.execute("SELECT set_config('catasto.app_user_id', NULL, false);") # false = non locale alla transazione
                # cur.execute("SELECT set_config('catasto.session_id', NULL, false);")

                cur.execute("SELECT set_config(%s, %s, false);", (f"{self.schema}.app_user_id", str(app_user_id)))
                cur.execute("SELECT set_config(%s, %s, false);", (f"{self.schema}.session_id", session_id))
                conn.commit() # I SET CONFIG non locali alla transazione richiedono commit per essere effettivi per la sessione
                self.logger.info(f"Variabili di sessione per audit impostate: app_user_id={app_user_id}, session_id={session_id[:8]}...")
                return True
        except psycopg2.Error as e:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB impostando variabili audit: {e}", exc_info=True)
            return False
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore generico impostando variabili audit: {e}", exc_info=True)
            return False
        finally:
            if conn:
                self._release_connection(conn)

    def _clear_audit_session_variables_with_conn(self, conn_target):
        """Metodo helper per pulire le variabili di sessione usando una connessione esistente. Chiamato da logout_user."""
        if not conn_target or conn_target.closed:
            self.logger.warning("_clear_audit_session_variables_with_conn chiamata con connessione non valida o chiusa.")
            return
        try:
            with conn_target.cursor() as cur:
                cur.execute("RESET catasto.app_user_id;")
                cur.execute("RESET catasto.session_id;")
                # Non fare commit qui, è parte della transazione del chiamante (logout_user)
            self.logger.debug("Variabili di sessione audit resettate (usando connessione esistente per logout).")
        except Exception as e:
            self.logger.error(f"Errore durante il reset delle variabili di sessione audit con connessione esistente: {e}", exc_info=True)
            # Non sollevare eccezione per non interrompere il logout principale
    def execute_sql_from_file(self, file_path: str) -> Tuple[bool, str]:
        if not os.path.exists(file_path):
            return False, f"File SQL non trovato: {file_path}"
        conn = None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            conn = self._get_connection()
            # Per DDL o script complessi, potrebbe essere necessario uscire da una transazione
            # o usare autocommit, ma questo dipende dallo script.
            # conn.autocommit = True # Usare con cautela, potrebbe interferire con il pool
            with conn.cursor() as cur:
                self.logger.info(f"Esecuzione script SQL da file: {file_path}")
                cur.execute(sql_content) # Esegue l'intero contenuto
                # Per DDL, non c'è un commit esplicito necessario se autocommit non è attivo per la sessione
                # ma è meglio fare commit se lo script contiene DML o se autocommit è off.
                # Se lo script gestisce le proprie transazioni, va bene.
                # Per script di setup DDL, spesso si eseguono fuori da una transazione esplicita
                # o con connessioni in modalità autocommit.
                # Se si usa una connessione dal pool, l'autocommit di default è solitamente False.
                conn.commit() 
            self.logger.info(f"Script SQL {file_path} eseguito con successo.")
            return True, f"Script {os.path.basename(file_path)} eseguito con successo."
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            msg = f"Errore DB eseguendo script {file_path}: {getattr(db_err, 'pgerror', str(db_err))}"
            self.logger.error(msg, exc_info=True)
            return False, msg
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            msg = f"Errore Python eseguendo script {file_path}: {e}"
            self.logger.error(msg, exc_info=True)
            return False, msg
        finally:
            # if conn and conn.autocommit: conn.autocommit = False # Ripristina se modificato
            if conn:
                self._release_connection(conn)
    def clear_audit_session_variables(self) -> bool:
        """
        Resetta le variabili di sessione PostgreSQL 'catasto.app_user_id' e 
        'catasto.session_id' a NULL per la connessione corrente.
        Usa il pool di connessioni.
        """
        self.logger.info("Reset variabili di sessione per audit (catasto.app_user_id, catasto.session_id).")
        conn = None
        try:
            conn = self._get_connection() # Se il pool è None, solleverà DBMError qui
            with conn.cursor() as cur:
                # Usare RESET è più pulito se le variabili sono state impostate con SET LOCAL o SET SESSION
                # Se sono state impostate con set_config(..., ..., false), il loro scope è la sessione.
                # Resettarle esplicitamente a NULL con set_config è un'alternativa.
                # SELECT set_config('catasto.app_user_id', NULL, false);
                # SELECT set_config('catasto.session_id', NULL, false);
                # Oppure, se sono definite con un DEFAULT nel db, RESET le riporterà al default.
                # Per GUC custom senza un DEFAULT esplicito, impostarle a NULL è più sicuro.
                
                # Tentativo 1: RESET (preferibile se hanno un default o per pulizia generale)
                # cur.execute(f"RESET {self.schema}.app_user_id;")
                # cur.execute(f"RESET {self.schema}.session_id;")
                
                # Tentativo 2: SET a NULL (più esplicito se non si è sicuri del default)
                cur.execute(f"SELECT set_config('{self.schema}.app_user_id', NULL, false);")
                cur.execute(f"SELECT set_config('{self.schema}.session_id', NULL, false);")
                
                conn.commit() # Necessario per set_config con is_local = false
                self.logger.info("Variabili di sessione per audit resettate con successo.")
                return True
        except DBMError as e: # Cattura DBMError da _get_connection se il pool non è inizializzato
            self.logger.warning(f"Impossibile resettare variabili audit: {e}")
            return False # Non sollevare eccezione, semplicemente non ha potuto farlo
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB resettando variabili audit: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            return False
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore Python resettando variabili audit: {e}", exc_info=True)
            return False
        finally:
            if conn:
                self._release_connection(conn)

    def _clear_audit_session_variables_with_conn(self, conn_target): # Questo è per il logout
        """Helper per pulire le variabili di sessione audit usando una connessione esistente."""
        if not conn_target or conn_target.closed:
            self.logger.warning("_clear_audit_session_variables_with_conn chiamata con connessione non valida.")
            return
        try:
            with conn_target.cursor() as cur:
                cur.execute(f"SELECT set_config('{self.schema}.app_user_id', NULL, false);")
                cur.execute(f"SELECT set_config('{self.schema}.session_id', NULL, false);")
                # Il commit è gestito dal chiamante (logout_user)
            self.logger.debug("Variabili di sessione audit resettate (connessione esistente).")
        except Exception as e:
            self.logger.error(f"Errore resettando variabili audit con connessione esistente: {e}", exc_info=True)
    def aggiungi_documento_storico(self, titolo: str, tipo_documento: str, percorso_file: str,
                                  descrizione: Optional[str] = None, anno: Optional[int] = None,
                                  periodo_id: Optional[int] = None, 
                                  metadati_json: Optional[str] = None) -> Optional[int]: # Restituisce l'ID del nuovo documento
        """Inserisce un nuovo record nella tabella documento_storico."""
        query = f"""
            INSERT INTO {self.schema}.documento_storico 
                (titolo, tipo_documento, percorso_file, descrizione, anno, periodo_id, metadati)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING id;
        """
        params = (titolo, tipo_documento, percorso_file, descrizione, anno, periodo_id, metadati_json)
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.info(f"Aggiunta documento: {titolo}, Percorso: {percorso_file}")
                cur.execute(query, params)
                doc_id = cur.fetchone()['id']
                conn.commit()
                self.logger.info(f"Documento storico ID {doc_id} aggiunto con successo.")
                return doc_id
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB aggiungendo documento storico '{titolo}': {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            raise DBMError(f"Errore database: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        # ... (gestione altre eccezioni come per altri metodi INSERT) ...
        finally:
            if conn: self._release_connection(conn)
        return None

    def collega_documento_a_partita(self, documento_id: int, partita_id: int, 
                                   rilevanza: str, note: Optional[str] = None) -> bool:
        """Inserisce un record nella tabella di collegamento documento_partita."""
        if rilevanza not in ['primaria', 'secondaria', 'correlata']:
            self.logger.error(f"Valore di rilevanza non valido: {rilevanza}")
            raise DBDataError(f"Valore di rilevanza non valido: {rilevanza}. Ammessi: 'primaria', 'secondaria', 'correlata'.")
        
        query = f"""
            INSERT INTO {self.schema}.documento_partita
                (documento_id, partita_id, rilevanza, note)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (documento_id, partita_id) DO UPDATE SET 
                rilevanza = EXCLUDED.rilevanza, 
                note = EXCLUDED.note,
                data_creazione = {self.schema}.documento_partita.data_creazione; -- Mantiene data_creazione originale
        """ # ON CONFLICT aggiorna se il legame esiste già
        params = (documento_id, partita_id, rilevanza, note)
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.info(f"Collegamento documento ID {documento_id} a partita ID {partita_id}, rilevanza: {rilevanza}")
                cur.execute(query, params)
                conn.commit()
                self.logger.info("Documento collegato/aggiornato alla partita con successo.")
                return True
        except psycopg2.Error as db_err:
            if conn: conn.rollback()
            self.logger.error(f"Errore DB collegando doc {documento_id} a partita {partita_id}: {getattr(db_err, 'pgerror', str(db_err))}", exc_info=True)
            raise DBMError(f"Errore database: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        # ... (gestione altre eccezioni) ...
        finally:
            if conn: self._release_connection(conn)
        return False

    def get_documenti_per_partita(self, partita_id: int) -> List[Dict[str, Any]]:
        """Recupera l'elenco dei documenti (con dettagli) associati a una partita."""
        query = f"""
            SELECT
                ds.id as documento_id,
                ds.titolo,
                ds.tipo_documento,
                ds.percorso_file,
                ds.anno,
                -- dp.id as documento_partita_id_rel, -- QUESTA RIGA NON DEVE ESSERE PRESENTE
                dp.rilevanza,
                dp.note as note_legame,
                ps.nome as nome_periodo,
                -- Aggiungi gli ID della relazione composita
                dp.documento_id as dp_documento_id,
                dp.partita_id as dp_partita_id
            FROM {self.schema}.documento_storico ds
            JOIN {self.schema}.documento_partita dp ON ds.id = dp.documento_id
            LEFT JOIN {self.schema}.periodo_storico ps ON ds.periodo_id = ps.id
            WHERE dp.partita_id = %s
            ORDER BY ds.anno DESC, ds.titolo;
        """
        conn = None
        documenti = []
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                self.logger.debug(f"Esecuzione query get_documenti_per_partita per partita_id {partita_id}: {cur.mogrify(query, (partita_id,)).decode('utf-8', 'ignore')}")
                cur.execute(query, (partita_id,))
                documenti = [dict(row) for row in cur.fetchall()]
                self.logger.info(f"Recuperati {len(documenti)} documenti per partita ID {partita_id}.")
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB durante il recupero dei documenti per la partita ID {partita_id}: {db_err}", exc_info=True)
            raise DBMError(f"Errore database: {getattr(db_err, 'pgerror', str(db_err))}") from db_err
        except Exception as e:
            self.logger.error(f"Errore generico durante il recupero dei documenti per la partita ID {partita_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema: {e}") from e
        finally:
            if conn: self._release_connection(conn)
        return documenti

    def scollega_documento_da_partita(self, documento_id: int, partita_id: int) -> bool:
        """
        Rimuove un legame documento-partita dalla tabella documento_partita usando la chiave primaria composta.
        """
        if not (isinstance(documento_id, int) and documento_id > 0):
            self.logger.error(f"scollega_documento_da_partita: ID documento non valido: {documento_id}")
            raise DBDataError(f"ID documento non valido: {documento_id}")
        if not (isinstance(partita_id, int) and partita_id > 0):
            self.logger.error(f"scollega_documento_da_partita: ID partita non valido: {partita_id}")
            raise DBDataError(f"ID partita non valido: {partita_id}")

        query = f"DELETE FROM {self.schema}.documento_partita WHERE documento_id = %s AND partita_id = %s;"
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione query scollega_documento_da_partita per doc_id={documento_id}, part_id={partita_id}: {cur.mogrify(query, (documento_id, partita_id)).decode('utf-8', 'ignore')}")
                cur.execute(query, (documento_id, partita_id))

                if cur.rowcount == 0:
                    conn.rollback()
                    self.logger.warning(f"Tentativo di scollegare documento-partita doc_id={documento_id} da partita_id={partita_id} non trovato.")
                    raise DBNotFoundError(f"Nessun legame documento-partita trovato tra documento ID {documento_id} e partita ID {partita_id} da scollegare.")

                conn.commit()
                self.logger.info(f"Legame documento doc_id={documento_id} a partita_id={partita_id} scollegato con successo. Righe modificate: {cur.rowcount}")
                return True

        except psycopg2.Error as e:
            if conn: conn.rollback()
            error_detail = getattr(e, 'pgerror', str(e))
            self.logger.error(f"Errore DB scollegando documento doc_id={documento_id} da partita_id={partita_id}: {error_detail}", exc_info=True)
            raise DBMError(f"Errore database durante lo scollegamento del documento: {error_detail}") from e
        except Exception as e:
            if conn and not conn.closed: conn.rollback()
            self.logger.error(f"Errore imprevisto scollegando documento doc_id={documento_id} da partita_id={partita_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto: {e}") from e
        finally:
            if conn:
                self._release_connection(conn)

    # Opzionali: scollega_documento_da_partita, elimina_documento_storico (con gestione file!)
        
# --- Esempio di utilizzo minimale (invariato) ---
if __name__ == "__main__":
    print("Esecuzione test minimale CatastoDBManager...")
    db = CatastoDBManager(password="Markus74") # Usa la tua password
    if db.connect():
        print("Connessione OK.")
        comuni_carcare = db.get_comuni("Carcare")
        carcare_id = None
        if comuni_carcare:
            carcare_id = comuni_carcare[0]['id']
            print(f"Trovato comune 'Carcare' con ID: {carcare_id}")
            possessori = db.get_possessori_by_comune(carcare_id)
            if possessori: print(f"Trovati {len(possessori)} possessori per Carcare (ID: {carcare_id}):")
            else: print(f"Nessun possessore trovato per Carcare (ID: {carcare_id}) o errore.")
        else: print("Comune 'Carcare' non trovato.")
        db.disconnect()
        print("Disconnessione OK.")
    else:
        print("Connessione fallita.")