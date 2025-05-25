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
import sys
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import json
import uuid
import os
import shutil # Per trovare i percorsi degli eseguibili


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
    def __init__(self, dbname, user, password, host, port, 
                 schema="catasto", 
                 log_file="db_core.log", 
                 log_level=logging.DEBUG): # <--- ASSICURATI CHE log_level SIA QUI COME PARAMETRO

        self.conn_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port
        }
        self.schema = schema
        self.conn = None
        self.pool = None
        self.keep_alive_query = "SELECT 1"
        self.application_name = "CatastoApp"

        # --- INIZIALIZZAZIONE DEL LOGGER ---
        self.logger = logging.getLogger(f"CatastoDB_{dbname}_{host}")
        
        # Usa il parametro log_level dalla firma del metodo
        self.logger.setLevel(log_level) # <--- USA IL PARAMETRO log_level QUI

        if not self.logger.handlers:
            log_format_str = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            formatter = logging.Formatter(log_format_str)

            try:
                file_h = logging.FileHandler(log_file, mode='a', encoding='utf-8')
                file_h.setFormatter(formatter)
                self.logger.addHandler(file_h)
            except Exception as e:
                print(f"ATTENZIONE: Impossibile creare il file handler per il logger {self.logger.name} su {log_file}: {e}")

            if log_level == logging.DEBUG or not getattr(sys, 'frozen', False):
                console_h = logging.StreamHandler(sys.stdout)
                console_h.setFormatter(formatter)
                self.logger.addHandler(console_h)
        # --- FINE INIZIALIZZAZIONE LOGGER ---

        self.logger.info(f"Inizializzato gestore per database {self.conn_params['dbname']} (schema: {self.schema}) con log_level: {logging.getLevelName(self.logger.getEffectiveLevel())}")
        
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                **self.conn_params,
                options=f'-c search_path={self.schema},public -c application_name={self.application_name}'
            )
            self.logger.info(f"Pool di connessioni PostgreSQL per '{self.application_name}' inizializzato con successo.")
        except psycopg2.Error as e:
            self.logger.error(f"Errore durante l'inizializzazione del pool di connessioni PostgreSQL: {e}", exc_info=True)
            self.pool = None
            # raise # Considera di rilanciare se il pool è critico


    # --- Metodi Base Connessione e Transazione ---

    def connect(self) -> bool:
        """Stabilisce una connessione al database."""
        try:
            if self.conn and not self.conn.closed:
                logger.warning("Chiusura connessione DB esistente prima di riconnettere.")
                self.disconnect()

            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
            self.cur = self.conn.cursor(cursor_factory=DictCursor)
            logger.info("Connessione stabilita con successo")
            return True
        except psycopg2.OperationalError as op_err:
             logger.error(f"Errore operativo durante la connessione (controllare DB e parametri): {op_err}")
             self.conn = None; self.cur = None; return False
        except Exception as e:
            logger.error(f"Errore generico durante la connessione: {e}")
            self.conn = None; self.cur = None; return False

    def disconnect(self):
        """Chiude la connessione al database."""
        try:
            if self.conn and not self.conn.closed:
                 self.clear_session_app_user() # Tenta di pulire il contesto
            if self.cur: self.cur.close()
            if self.conn: self.conn.close()
            logger.info("Disconnessione completata")
        except Exception as e:
            logger.error(f"Errore durante la disconnessione: {e}")
        finally:
             self.conn = None; self.cur = None
    def _get_connection(self):
        """
        Ottiene una connessione dal pool se disponibile e inizializzato,
        altrimenti tenta di utilizzare/stabilire la connessione singola self.conn.
        Solleva un'eccezione se nessuna connessione può essere ottenuta.
        """
        conn = None
        if self.pool:
            try:
                conn = self.pool.getconn()
                if conn:
                    self.logger.debug(f"Connessione ottenuta dal pool. Dettagli: {conn.dsn}")
                    # Opzionale: imposta search_path qui se non fatto nelle opzioni del pool o se serve riconferma
                    # with conn.cursor() as cur:
                    #     cur.execute(f"SET search_path TO {self.schema}, public;")
                    #     cur.execute(f"SET application_name TO '{self.application_name}';")
                    # conn.commit() # se search_path e application_name lo richiedono
                    return conn
            except psycopg2.Error as e:
                self.logger.error(f"Errore nell'ottenere una connessione dal pool: {e}. Tento fallback su connessione singola.", exc_info=True)
                # Non fare self.pool = None qui, il pool potrebbe essere temporaneamente esaurito
        
        # Fallback o uso primario della connessione singola se il pool non è usato/disponibile
        self.logger.debug("Pool non disponibile o errore, tento di usare/stabilire connessione singola.")
        if not self.conn or self.conn.closed:
            self.logger.debug("Connessione singola non attiva o chiusa, tento di (ri)connettere.")
            if not self.connect(): # Tenta di stabilire la connessione singola
                self.logger.error("Impossibile stabilire la connessione singola al database in _get_connection.")
                raise psycopg2.OperationalError("Impossibile ottenere una connessione valida al database.")
        
        if self.conn and not self.conn.closed:
             self.logger.debug(f"Utilizzo della connessione singola esistente. Dettagli: {self.conn.dsn}")
             return self.conn
        else: # Questo non dovrebbe accadere se self.connect() ha successo
            self.logger.error("Fallimento critico: nessuna connessione disponibile dopo tentativi.")
            raise psycopg2.OperationalError("Nessuna connessione al database disponibile dopo tutti i tentativi.")


    def _release_connection(self, conn_to_release):
        """
        Rilascia una connessione al pool se proviene dal pool.
        Non fa nulla per la connessione singola self.conn (verrà chiusa da disconnect).
        """
        if self.pool and conn_to_release is not self.conn: # Solo se abbiamo un pool E la connessione non è quella singola
            try:
                self.pool.putconn(conn_to_release)
                self.logger.debug(f"Connessione rilasciata al pool. Dettagli DSN: {conn_to_release.dsn if not conn_to_release.closed else 'CONN CHIUSA'}")
            except psycopg2.Error as e:
                self.logger.error(f"Errore nel rilasciare la connessione al pool: {e}. La connessione potrebbe essere chiusa forzatamente.", exc_info=True)
                # Come fallback, chiudi la connessione se non può essere restituita al pool
                try:
                    if not conn_to_release.closed:
                        conn_to_release.close()
                except psycopg2.Error:
                    pass # Ignora errori sulla chiusura forzata
            except Exception as ex: # Cattura altri errori come "pool non accetta più connessioni"
                 self.logger.error(f"Errore generico nel rilasciare la connessione al pool: {ex}. La connessione potrebbe essere chiusa forzatamente.", exc_info=True)
                 try:
                    if not conn_to_release.closed:
                        conn_to_release.close()
                 except psycopg2.Error:
                    pass
        elif conn_to_release is self.conn:
            self.logger.debug("Tentativo di rilasciare la connessione singola self.conn, nessuna azione richiesta qui.")
        else:
            self.logger.warning(f"Tentativo di rilasciare una connessione sconosciuta o pool non attivo. Connessione DSN: {conn_to_release.dsn if conn_to_release and not conn_to_release.closed else 'N/A o CHIUSA'}")
            # Opzionalmente, chiudi connessioni sconosciute per sicurezza se non fanno parte del pool o di self.conn
            # if conn_to_release and not conn_to_release.closed:
            #     try:
            #         conn_to_release.close()
            #     except psycopg2.Error:
            #         pass


    def commit(self):
        """Conferma le modifiche al database."""
        if self.conn and not self.conn.closed:
             try:
                 self.conn.commit()
                 logger.debug("Commit eseguito.")
             except Exception as e:
                 logger.error(f"Errore commit: {e}")
                 self.rollback()
        else: logger.warning("Tentativo di commit senza connessione attiva.")

    def rollback(self):
        """Annulla le modifiche al database."""
        if self.conn and not self.conn.closed:
             try:
                 self.conn.rollback()
                 logger.info("Rollback eseguito.")
             except Exception as e:
                 logger.error(f"Errore rollback: {e}")
        else: logger.warning("Tentativo di rollback senza connessione attiva.")

    def execute_query(self, query: str, params: Optional[tuple] = None, fetch_results: bool = False) -> bool:
        """Esegue una query SQL. Gestisce transazioni e logging."""
        if not self.conn or self.conn.closed:
            logger.error("Nessuna connessione attiva al database.")
            self.cursor = None # Assicura che cursor sia None se non c'è connessione
            return False
        try:
            # Potrebbe essere meglio creare un nuovo cursore per ogni query
            # per evitare problemi con stati di cursori precedenti,
            # oppure assicurarsi che venga resettato correttamente.
            self.cursor = self.conn.cursor(cursor_factory=DictCursor) # Crea/Ricrea il cursore

            self.cursor.execute(query, params)
            logger.debug(f"Query eseguita: {self.cursor.query.decode() if self.cursor.query else query}") # Logga la query effettiva

            # Se la query non è di tipo SELECT (o non ci si aspetta risultati immediati qui),
            # il successo è dato dall'assenza di eccezioni.
            # Il commit verrà gestito esternamente o da metodi specifici.
            
            # Non resettare self.cursor a None qui se vuoi accedere a rowcount o fetchone dopo
            return True

        except psycopg2.Error as e:
            logger.error(f"Errore DB durante l'esecuzione della query: {query[:100]}... Errore: {e}")
            if self.conn and not self.conn.closed: # Solo se la connessione è ancora valida
                self.rollback() # Esegui rollback in caso di errore
            # self.cursor = None # Potrebbe essere utile resettarlo in caso di errore
            return False
        except Exception as e:
            logger.error(f"Errore Python generico durante l'esecuzione della query: {e}")
            if self.conn and not self.conn.closed:
                self.rollback()
            # self.cursor = None
            return False

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
    
    def is_connected(self) -> bool:
        """Verifica se la connessione al database è attiva."""
        if self.conn and not self.conn.closed:
            try:
                # Esegue una query semplice per testare la connessione
                # self.cur.execute("SELECT 1") # Potrebbe essere troppo invasivo se il cursore è occupato
                return True # Se conn non è None e non è closed, assumiamo sia ok per questo contesto
            except (psycopg2.InterfaceError, psycopg2.OperationalError):
                return False
        return False
    # --- Metodi CRUD e Ricerca Base (MODIFICATI per comune_id) ---
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
    def get_comuni(self, search_term: Optional[str] = None) -> List[Dict]:
        """Recupera comuni (ID e nome) con filtro opzionale per nome."""
        try:
            select_clause = "SELECT id, nome, provincia, regione FROM catasto.comune" # Seleziona ID
            if search_term:
                query = f"{select_clause} WHERE nome ILIKE %s ORDER BY nome"
                params = (f"%{search_term}%",)
            else:
                query = f"{select_clause} ORDER BY nome"
                params = None
            if self.execute_query(query, params):
                return self.fetchall() # Ritorna lista di dict con 'id', 'nome', ecc.
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_comuni: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in get_comuni: {e}")
        return []
    
    def get_all_comuni_details(self) -> List[Dict[str, Any]]:
        """
        Recupera i dettagli disponibili di tutti i comuni dalla tabella catasto.comune.
        I campi codice_catastale, data_istituzione, data_soppressione, note
        NON sono presenti nella tabella 'comune' attuale e quindi non verranno popolati.
        """
        query_effettiva = """
            SELECT 
                id, 
                nome AS nome_comune, -- La GUI si aspetta 'nome_comune'
                provincia,
                regione -- Aggiungiamo regione se può essere utile, anche se la GUI non la usa direttamente
                -- codice_catastale, data_istituzione, data_soppressione, note (NON PRESENTI IN 'comune')
            FROM catasto.comune 
            ORDER BY nome_comune;
        """
        try:
            if self.execute_query(query_effettiva):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_all_comuni_details: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in get_all_comuni_details: {e}")
        return []

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

    def insert_possessore(self, comune_id: int, cognome_nome: str, paternita: Optional[str], # Usa comune_id
                        nome_completo: str, attivo: bool = True) -> Optional[int]:
        """Inserisce un nuovo possessore usando la procedura SQL. Ritorna l'ID."""
        try:
            # Procedura SQL aggiornata per accettare comune_id
            if self.execute_query("CALL inserisci_possessore(%s, %s, %s, %s, %s)",
                                  (comune_id, cognome_nome, paternita, nome_completo, attivo)):
                self.commit()
                # Recupera l'ID
                return self.check_possessore_exists(nome_completo, comune_id)
            return None
        except psycopg2.Error as db_err:
            # Gestione specifica per violazione constraint (es. comune_id non esiste)
            if db_err.pgcode == psycopg2.errors.ForeignKeyViolation:
                 logger.error(f"Errore FK in insert_possessore: Comune ID {comune_id} non valido? Dettagli: {db_err}")
            else:
                 logger.error(f"Errore DB specifico in insert_possessore: {db_err}")
            # Rollback è già stato fatto da execute_query
            return None
        except Exception as e:
            logger.error(f"Errore Python in insert_possessore: {e}")
            self.rollback()
            return None

    def get_possessori_by_comune(self, comune_id: int) -> List[Dict]: # Usa comune_id
        """Recupera possessori per comune ID, includendo il nome del comune."""
        try:
            # Query SQL aggiornata per JOIN
            query = """
                SELECT pos.id, c.nome as comune_nome, pos.cognome_nome, pos.paternita,
                    pos.nome_completo, pos.attivo
                FROM catasto.possessore pos  -- Schema qualificato
                JOIN catasto.comune c ON pos.comune_id = c.id -- Chiave corretta se è comune.id e possessore.comune_id
                WHERE pos.comune_id = %s ORDER BY pos.nome_completo;
            """
            if self.execute_query(query, (comune_id,)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_possessori_by_comune: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in get_possessori_by_comune: {e}")
        return []

    def insert_localita(self, comune_id: int, nome: str, tipo: str, # Usa comune_id
                      civico: Optional[int] = None) -> Optional[int]:
        """Inserisce o recupera una località (basato su comune_id, nome, civico). Ritorna l'ID."""
        # Vincolo UNIQUE su comune_id, nome, civico
        query_insert = """
            INSERT INTO localita (comune_id, nome, tipo, civico)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (comune_id, nome, civico) DO NOTHING
            RETURNING id
        """
        query_select = """
            SELECT id FROM localita
            WHERE comune_id = %s AND nome = %s AND (
                  (civico IS NULL AND %s IS NULL) OR (civico = %s)
            )
        """
        try:
            inserted_id = None
            if self.execute_query(query_insert, (comune_id, nome, tipo, civico)):
                result = self.fetchone()
                if result:
                    inserted_id = result['id']
                    self.commit()
                    logger.info(f"Località '{nome}' (Comune ID: {comune_id}) inserita con ID: {inserted_id}")
                    return inserted_id
            elif self.conn is None or self.conn.closed: return None

            logger.info(f"Località '{nome}' (Comune ID: {comune_id}) potrebbe esistere già. Tentativo selezione.")
            if self.execute_query(query_select, (comune_id, nome, civico, civico)):
                existing = self.fetchone()
                if existing:
                    logger.info(f"Località '{nome}' (Comune ID: {comune_id}) trovata con ID: {existing['id']}")
                    return existing['id']
                else: logger.warning(f"Località '{nome}' (Comune ID: {comune_id}) non trovata."); return None
            return None

        except psycopg2.Error as db_err:
            if db_err.pgcode == psycopg2.errors.ForeignKeyViolation:
                 logger.error(f"Errore FK in insert_localita: Comune ID {comune_id} non valido? Dettagli: {db_err}")
            else:
                 logger.error(f"Errore DB in insert_localita '{nome}': {db_err}")
            return None
        except Exception as e: logger.error(f"Errore Python in insert_localita '{nome}': {e}"); self.rollback(); return None

    def get_partite_by_comune(self, comune_id: int) -> List[Dict]: # Usa comune_id
        """Recupera partite per comune ID, includendo nome comune."""
        try:
            # Query SQL aggiornata
            query = """
                SELECT
                    p.id, c.nome as comune_nome, p.numero_partita, p.tipo, p.data_impianto,
                    p.data_chiusura, p.stato,
                    string_agg(DISTINCT pos.nome_completo, ', ') as possessori,
                    COUNT(DISTINCT i.id) as num_immobili
                FROM partita p
                JOIN comune c ON p.comune_id = c.id
                LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
                LEFT JOIN possessore pos ON pp.possessore_id = pos.id
                LEFT JOIN immobile i ON p.id = i.partita_id
                WHERE p.comune_id = %s
                GROUP BY p.id, c.nome -- Raggruppa per id e nome comune
                ORDER BY p.numero_partita
            """
            if self.execute_query(query, (comune_id,)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_partite_by_comune: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in get_partite_by_comune: {e}")
        return []

    def get_partita_details(self, partita_id: int) -> Optional[Dict]:
        """Recupera dettagli completi di una partita (MODIFICATO per nome comune)."""
        try:
            partita = {}
            # Info base partita (con nome comune)
            query_partita = """
                SELECT p.*, c.nome as comune_nome, c.id as comune_id
                FROM partita p
                JOIN comune c ON p.comune_id = c.id
                WHERE p.id = %s
            """
            if not self.execute_query(query_partita, (partita_id,)): return None
            partita_base = self.fetchone()
            if not partita_base: logger.warning(f"Partita ID {partita_id} non trovata."); return None
            partita.update(partita_base)

            # Possessori
            query_poss = """
                SELECT pos.id, pos.nome_completo, pp.titolo, pp.quota
                FROM possessore pos JOIN partita_possessore pp ON pos.id = pp.possessore_id
                WHERE pp.partita_id = %s ORDER BY pos.nome_completo
            """
            partita['possessori'] = self.fetchall() if self.execute_query(query_poss, (partita_id,)) else []

            # Immobili
            query_imm = """
                SELECT i.id, i.natura, i.numero_piani, i.numero_vani, i.consistenza, i.classificazione,
                       l.nome as localita_nome, l.tipo as localita_tipo, l.civico
                FROM immobile i JOIN localita l ON i.localita_id = l.id
                WHERE i.partita_id = %s ORDER BY l.nome, i.natura
            """
            partita['immobili'] = self.fetchall() if self.execute_query(query_imm, (partita_id,)) else []

            # Variazioni
            query_var = """
                SELECT v.*, c.tipo as tipo_contratto, c.data_contratto, c.notaio, c.repertorio, c.note as contratto_note
                FROM variazione v LEFT JOIN contratto c ON v.id = c.variazione_id
                WHERE v.partita_origine_id = %s OR v.partita_destinazione_id = %s
                ORDER BY v.data_variazione DESC
            """
            partita['variazioni'] = self.fetchall() if self.execute_query(query_var, (partita_id, partita_id)) else []

            return partita
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_partita_details (ID: {partita_id}): {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in get_partita_details (ID: {partita_id}): {e}")
        return None

    def update_partita(self, partita_id: int, dati_modificati: Dict[str, Any]):
        """
        Aggiorna i dati di una partita esistente nel database.
        Solleva eccezioni specifiche in caso di errore.

        Args:
            partita_id: L'ID della partita da aggiornare.
            dati_modificati: Un dizionario contenente i campi della partita da aggiornare.
                             Campi attesi e gestiti: 'numero_partita', 'tipo', 
                             'data_impianto', 'data_chiusura', 'numero_provenienza', 'stato'.

        Raises:
            DBDataError: Se partita_id o dati_modificati non sono validi.
            DBNotFoundError: Se la partita con l'ID specificato non viene trovata.
            DBUniqueConstraintError: Se l'aggiornamento viola un vincolo di unicità (es. numero_partita duplicato nel comune).
            DBMError: Per altri errori generici del database.
        """
        if not isinstance(partita_id, int) or partita_id <= 0:
            self.logger.error(f"update_partita: partita_id non valido: {partita_id}")
            raise DBDataError(f"ID partita non valido: {partita_id}")
        if not isinstance(dati_modificati, dict):
            self.logger.error(f"update_partita: dati_modificati non è un dizionario per partita ID {partita_id}.")
            raise DBDataError("Formato dati per l'aggiornamento non valido.")

        set_clauses = []
        params = []
        conn = None # Inizializza conn a None per il blocco finally

        # Mappa dei campi permessi e se possono essere NULL
        # (nome_campo_dict, nome_colonna_db, is_nullable)
        allowed_fields = {
            "numero_partita": ("numero_partita", False),
            "tipo": ("tipo", False),
            "data_impianto": ("data_impianto", True),
            "data_chiusura": ("data_chiusura", True),
            "numero_provenienza": ("numero_provenienza", True),
            "stato": ("stato", False),
        }

        for key_dict, (col_db, _) in allowed_fields.items():
            if key_dict in dati_modificati:
                set_clauses.append(f"{col_db} = %s")
                params.append(dati_modificati[key_dict])
            # Se un campo NOT NULL non è in dati_modificati, causerà un errore se si tenta di impostarlo a NULL
            # La logica della UI dovrebbe garantire che i campi NOT NULL abbiano sempre un valore.

        # Verifica che i campi obbligatori (se li consideriamo tali per un UPDATE) siano presenti.
        # La tabella ha già i suoi vincoli NOT NULL che verranno applicati dal DB.
        # Qui ci assicuriamo solo che l'UPDATE abbia senso.
        if "numero_partita" not in dati_modificati or dati_modificati.get("numero_partita") is None:
            raise DBDataError("Il campo 'numero_partita' è obbligatorio e non può essere nullo per l'aggiornamento.")
        if "tipo" not in dati_modificati or dati_modificati.get("tipo") is None:
            raise DBDataError("Il campo 'tipo' è obbligatorio e non può essere nullo per l'aggiornamento.")
        if "stato" not in dati_modificati or dati_modificati.get("stato") is None:
            raise DBDataError("Il campo 'stato' è obbligatorio e non può essere nullo per l'aggiornamento.")


        if not set_clauses:
            self.logger.info(f"update_partita: Nessun campo valido fornito per l'aggiornamento della partita ID {partita_id} (esclusa data_modifica).")
            # Decidi se questo è un errore o un "no-op" che consideri successo.
            # Aggiorniamo comunque data_modifica.
            set_clauses.append("data_modifica = CURRENT_TIMESTAMP")
            # Se solo data_modifica, params è vuoto fino all'aggiunta di partita_id
        else:
            set_clauses.append("data_modifica = CURRENT_TIMESTAMP")


        query = f"""
            UPDATE {self.schema}.partita
            SET {', '.join(set_clauses)}
            WHERE id = %s;
        """
        # Aggiungi partita_id alla fine della lista dei parametri per la clausola WHERE
        params.append(partita_id)
        params_tuple = tuple(params)

        try:
            conn = self._get_connection() # Ottieni la connessione
            with conn.cursor() as cur:
                self.logger.debug(f"Esecuzione query UPDATE partita ID {partita_id}: {cur.mogrify(query, params_tuple).decode('utf-8', 'ignore')}")
                cur.execute(query, params_tuple)

                if cur.rowcount == 0:
                    # Se rowcount è 0, la riga con l'ID specificato non esiste.
                    # (Con data_modifica = CURRENT_TIMESTAMP, se la riga esistesse, rowcount dovrebbe essere 1)
                    conn.rollback() # Annulla la transazione (anche se probabilmente non ha fatto nulla)
                    self.logger.warning(f"Tentativo di aggiornare partita ID {partita_id} che non è stata trovata.")
                    raise DBNotFoundError(f"Nessuna partita trovata con ID {partita_id} per l'aggiornamento.")
                
                conn.commit()
                self.logger.info(f"Partita ID {partita_id} aggiornata con successo. Righe modificate: {cur.rowcount}")

        except psycopg2.errors.UniqueViolation as uve:
            if conn: conn.rollback()
            constraint_name = getattr(uve.diag, 'constraint_name', "N/D")
            error_detail = getattr(uve, 'pgerror', str(uve))
            self.logger.error(f"Errore di violazione di unicità (vincolo: {constraint_name}) durante l'aggiornamento della partita ID {partita_id}: {error_detail}")
            # Messaggio più specifico per il vincolo comune_id, numero_partita
            if constraint_name == "partita_comune_id_numero_partita_key": # Assumendo sia questo il nome del tuo vincolo UNIQUE
                msg = "Il numero di partita specificato è già in uso per il comune associato."
            else:
                msg = f"Violazione di un vincolo di unicità (vincolo: {constraint_name}). I dati inseriti sono duplicati."
            raise DBUniqueConstraintError(msg, constraint_name=constraint_name, details=error_detail) from uve
        
        except psycopg2.errors.CheckViolation as cve:
            if conn: conn.rollback()
            constraint_name = getattr(cve.diag, 'constraint_name', "N/D")
            error_detail = getattr(cve, 'pgerror', str(cve))
            self.logger.error(f"Errore di violazione di CHECK constraint (vincolo: {constraint_name}) per partita ID {partita_id}: {error_detail}")
            msg = f"I dati forniti violano una regola di validazione del database (vincolo: {constraint_name})."
            # Esempi: tipo partita non valido, stato non valido
            if constraint_name == "partita_tipo_check":
                msg = "Il 'tipo' di partita specificato non è valido (ammessi: 'principale', 'secondaria')."
            elif constraint_name == "partita_stato_check":
                msg = "Lo 'stato' della partita specificato non è valido (ammessi: 'attiva', 'inattiva')."
            raise DBDataError(msg) from cve

        except psycopg2.Error as e: # Altri errori specifici di psycopg2/DB
            if conn: conn.rollback()
            error_detail = getattr(e, 'pgerror', str(e))
            self.logger.error(f"Errore DB generico durante l'aggiornamento della partita ID {partita_id}: {error_detail}", exc_info=True)
            raise DBMError(f"Errore database durante l'aggiornamento della partita: {error_detail}") from e
        
        except Exception as e: # Catch-all per altri errori Python imprevisti
            if conn and not conn.closed: conn.rollback() # Controlla se conn è definita e non chiusa
            self.logger.error(f"Errore imprevisto Python durante l'aggiornamento della partita ID {partita_id}: {e}", exc_info=True)
            raise DBMError(f"Errore di sistema imprevisto durante l'aggiornamento: {e}") from e
        
        finally:
            if conn:
                self._release_connection(conn) # Rilascia la connessione al pool

    # Assicurati di avere il metodo release_connection se usi un pool
    # def release_connection(self, conn):
    #     if self.conn_pool and conn:
    #         self.conn_pool.putconn(conn)
    #         self.logger.debug("Connessione rilasciata al pool.")
    # O se non usi un pool esplicito ma chiudi le connessioni:
    # def release_connection(self, conn):
    #     if conn:
    #         conn.close()
    #         self.logger.debug("Connessione chiusa.")

    
    
    def search_partite(self, comune_id: Optional[int] = None, numero_partita: Optional[int] = None, # Usa comune_id
                      possessore: Optional[str] = None, immobile_natura: Optional[str] = None) -> List[Dict]:
        """Ricerca partite con filtri multipli (MODIFICATO per comune_id)."""
        try:
            conditions = []; params = []; joins = ""
            select_cols = "p.id, c.nome as comune_nome, p.numero_partita, p.tipo, p.stato"
            query_base = f"SELECT DISTINCT {select_cols} FROM partita p JOIN comune c ON p.comune_id = c.id" # JOIN

            if possessore:
                if "partita_possessore pp" not in joins:
                    joins += " LEFT JOIN partita_possessore pp ON p.id = pp.partita_id LEFT JOIN possessore pos ON pp.possessore_id = pos.id"
                conditions.append("pos.nome_completo ILIKE %s"); params.append(f"%{possessore}%")
            if immobile_natura:
                if "immobile i" not in joins: joins += " LEFT JOIN immobile i ON p.id = i.partita_id"
                conditions.append("i.natura ILIKE %s"); params.append(f"%{immobile_natura}%")
            if comune_id is not None: # Filtro per ID
                conditions.append("p.comune_id = %s"); params.append(comune_id)
            if numero_partita is not None:
                conditions.append("p.numero_partita = %s"); params.append(numero_partita)

            query = query_base + joins
            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY c.nome, p.numero_partita" # Ordina per nome

            if self.execute_query(query, tuple(params)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in search_partite: {db_err}")
        except Exception as e: logger.error(f"Errore Python in search_partite: {e}")
        return []

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

    def delete_immobile(self, immobile_id: int) -> bool:
        """Chiama la procedura SQL elimina_immobile."""
        call_proc = "CALL elimina_immobile(%s)"
        try:
            if self.execute_query(call_proc, (immobile_id,)): self.commit(); logger.info(f"Immobile ID {immobile_id} eliminato."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB eliminazione immobile ID {immobile_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python eliminazione immobile ID {immobile_id}: {e}"); self.rollback(); return False

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

    def registra_nuova_proprieta(self, comune_id: int, numero_partita: int, data_impianto: date, # Usa comune_id
                                 possessori: List[Dict], immobili: List[Dict]) -> bool:
        """Chiama la procedura SQL registra_nuova_proprieta (MODIFICATA per comune_id)."""
        try:
            possessori_json = json.dumps(possessori)
            immobili_json = json.dumps(immobili)
            # Procedura SQL aggiornata per comune_id
            call_proc = "CALL registra_nuova_proprieta(%s, %s, %s, %s::json, %s::json)"
            params = (comune_id, numero_partita, data_impianto, possessori_json, immobili_json) # Passa ID
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Registrata nuova proprietà: Comune ID {comune_id}, Partita N.{numero_partita}")
                return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB registrazione nuova proprietà (Partita {numero_partita}): {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python registrazione nuova proprietà (Partita {numero_partita}): {e}"); self.rollback(); return False

    def registra_passaggio_proprieta(self, partita_origine_id: int, comune_id: int, numero_partita: int, # Usa comune_id
                                     tipo_variazione: str, data_variazione: date, tipo_contratto: str,
                                     data_contratto: date, **kwargs) -> bool:
        """Chiama la procedura SQL registra_passaggio_proprieta (MODIFICATA per comune_id)."""
        try:
            nuovi_poss_list = kwargs.get('nuovi_possessori')
            imm_trasf_list = kwargs.get('immobili_da_trasferire')
            nuovi_poss_json = json.dumps(nuovi_poss_list) if nuovi_poss_list is not None else None
            imm_trasf_array = imm_trasf_list if imm_trasf_list is not None else None

            # Procedura SQL aggiornata per comune_id
            call_proc = "CALL registra_passaggio_proprieta(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::json, %s, %s)"
            params = (
                partita_origine_id, comune_id, numero_partita, tipo_variazione, data_variazione, # Passa ID
                tipo_contratto, data_contratto, kwargs.get('notaio'), kwargs.get('repertorio'),
                nuovi_poss_json, imm_trasf_array, kwargs.get('note')
            )
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Registrato passaggio proprietà: Origine ID {partita_origine_id} -> Nuova Partita N.{numero_partita} (Comune ID {comune_id})")
                return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB registrazione passaggio proprietà (Origine ID {partita_origine_id}): {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python registrazione passaggio proprietà (Origine ID {partita_origine_id}): {e}"); self.rollback(); return False

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

    def duplicate_partita(self, partita_id: int, nuovo_numero_partita: int,
                          mantenere_possessori: bool = True, mantenere_immobili: bool = False) -> bool:
        """Chiama la procedura SQL duplica_partita (invariata rispetto a comune_id)."""
        call_proc = "CALL duplica_partita(%s, %s, %s, %s)"
        params = (partita_id, nuovo_numero_partita, mantenere_possessori, mantenere_immobili)
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Partita ID {partita_id} duplicata in N.{nuovo_numero_partita}."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB duplicazione partita ID {partita_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python duplicazione partita ID {partita_id}: {e}"); self.rollback(); return False

    def transfer_immobile(self, immobile_id: int, nuova_partita_id: int, registra_variazione: bool = False) -> bool:
        """Chiama la procedura SQL trasferisci_immobile (invariata rispetto a comune_id)."""
        call_proc = "CALL trasferisci_immobile(%s, %s, %s)"
        params = (immobile_id, nuova_partita_id, registra_variazione)
        try:
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Immobile ID {immobile_id} trasferito a partita ID {nuova_partita_id}."); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB trasferimento immobile ID {immobile_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python trasferimento immobile ID {immobile_id}: {e}"); self.rollback(); return False

    # --- Metodi di Reportistica (MODIFICATI dove serve join per nome) ---

    def genera_certificato_proprieta(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL genera_certificato_proprieta (SQL aggiornata)."""
        try:
            # Funzione SQL aggiornata per fare JOIN
            query = "SELECT genera_certificato_proprieta(%s) AS certificato"
            if self.execute_query(query, (partita_id,)): result = self.fetchone(); return result.get('certificato') if result else None
            return None
        except psycopg2.Error as db_err: logger.error(f"Errore DB gen cert prop (ID: {partita_id}): {db_err}"); return None
        except Exception as e: logger.error(f"Errore Py gen cert prop (ID: {partita_id}): {e}"); return None

    def genera_report_genealogico(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL genera_report_genealogico (SQL aggiornata)."""
        try:
            # Funzione SQL aggiornata per fare JOIN
            query = "SELECT genera_report_genealogico(%s) AS report"
            if self.execute_query(query, (partita_id,)): result = self.fetchone(); return result.get('report') if result else None
            return None
        except psycopg2.Error as db_err: logger.error(f"Errore DB gen report gen (ID: {partita_id}): {db_err}"); return None
        except Exception as e: logger.error(f"Errore Py gen report gen (ID: {partita_id}): {e}"); return None

    def genera_report_possessore(self, possessore_id: int) -> Optional[str]:
        """Chiama la funzione SQL genera_report_possessore (SQL aggiornata)."""
        try:
             # Funzione SQL aggiornata per fare JOIN
            query = "SELECT genera_report_possessore(%s) AS report"
            if self.execute_query(query, (possessore_id,)): result = self.fetchone(); return result.get('report') if result else None
            return None
        except psycopg2.Error as db_err: logger.error(f"Errore DB gen report poss (ID: {possessore_id}): {db_err}"); return None
        except Exception as e: logger.error(f"Errore Py gen report poss (ID: {possessore_id}): {e}"); return None

    def genera_report_consultazioni(self, data_inizio: Optional[date] = None, data_fine: Optional[date] = None,
                                   richiedente: Optional[str] = None) -> Optional[str]:
        """Chiama la funzione SQL genera_report_consultazioni (invariata rispetto a comune_id)."""
        try:
            query = "SELECT genera_report_consultazioni(%s, %s, %s) AS report"
            params = (data_inizio, data_fine, richiedente)
            if self.execute_query(query, params): result = self.fetchone(); return result.get('report') if result else None
            return None
        except psycopg2.Error as db_err: logger.error(f"Errore DB gen report cons: {db_err}"); return None
        except Exception as e: logger.error(f"Errore Py gen report cons: {e}"); return None

    # --- Metodi Viste Materializzate (MODIFICATI per comune_id e query join) ---

    def get_statistiche_comune(self) -> List[Dict]:
        """Recupera dati dalla vista materializzata mv_statistiche_comune (aggiornata)."""
        try:
            # La vista SQL è stata aggiornata per usare join e nome comune
            query = "SELECT * FROM mv_statistiche_comune ORDER BY comune"
            if self.execute_query(query): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_statistiche_comune: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_statistiche_comune: {e}"); return []

    def get_immobili_per_tipologia(self, comune_id: Optional[int] = None, limit: int = 100) -> List[Dict]: # Usa comune_id
        """Recupera dati dalla vista materializzata mv_immobili_per_tipologia (aggiornata), filtrando per ID."""
        try:
            params = []
            # La vista SQL è stata aggiornata per usare nome comune
            query = "SELECT * FROM mv_immobili_per_tipologia" # La vista ha 'comune_nome'
            if comune_id is not None:
                 # Filtra direttamente sulla vista se il nome è univoco,
                 # altrimenti serve un JOIN o modifica della vista per includere ID
                 query = """
                     SELECT m.* FROM mv_immobili_per_tipologia m
                     JOIN comune c ON m.comune_nome = c.nome
                     WHERE c.id = %s
                 """
                 params.append(comune_id)

            query += " ORDER BY comune_nome, classificazione LIMIT %s"; params.append(limit)
            if self.execute_query(query, tuple(params)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_immobili_per_tipologia: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_immobili_per_tipologia: {e}"); return []

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
    def get_partita_data_for_export(self, partita_id: int) -> Optional[Dict]:
        """
        Recupera i dati completi di una partita come dizionario Python per l'esportazione.
        Chiama la funzione SQL esporta_partita_json che restituisce JSON.
        """
        try:
            query = "SELECT esporta_partita_json(%s) AS partita_data" # La funzione SQL restituisce JSON
            if self.execute_query(query, (partita_id,)):
                result = self.fetchone()
                if result and result.get('partita_data'):
                    # psycopg2 dovrebbe aver già convertito il tipo JSON di PostgreSQL in un dict Python
                    return result['partita_data'] 
            logger.warning(f"Nessun dato trovato per partita ID {partita_id} per l'esportazione.")
            return None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_partita_data_for_export (ID: {partita_id}): {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python get_partita_data_for_export (ID: {partita_id}): {e}")
            return None
        
        # Recupero possessori associati (modificato per includere paternita e cognome_nome)
        possessori_query = """
            SELECT 
                p.id, p.nome_completo, p.cognome_nome, p.paternita,
                pp.quota, pp.diritti_obblighi, 
                t.nome as titolo_proprieta, pp.data_inizio_validita, pp.data_fine_validita
            FROM catasto.possessori p
            JOIN catasto.partita_possessore pp ON p.id = pp.possessore_id
            LEFT JOIN catasto.titoli_proprieta t ON pp.titolo_proprieta_id = t.id
            WHERE pp.partita_id = %s
            ORDER BY p.nome_completo;
        """
        # Assumendo che self._fetch_all_dict esista e funzioni o sia stato sostituito dalla logica con DictCursor
        # dict_cursor_poss = self.conn.cursor(cursor_factory=DictCursor) # Esempio se fatto direttamente
        # dict_cursor_poss.execute(possessori_query, (partita_id,))
        # partita_data['possessori'] = [dict(row) for row in dict_cursor_poss.fetchall()]
        # dict_cursor_poss.close()
        
        # Se usi un metodo helper come self._fetch_all_dict:
        partita_data['possessori'] = self._fetch_all_dict(possessori_query, (partita_id,))


    def get_possessore_data_for_export(self, possessore_id: int) -> Optional[Dict]:
        """
        Recupera i dati completi di un possessore come dizionario Python per l'esportazione.
        Chiama la funzione SQL esporta_possessore_json che restituisce JSON.
        """
        try:
            query = "SELECT esporta_possessore_json(%s) AS possessore_data" # La funzione SQL restituisce JSON
            if self.execute_query(query, (possessore_id,)):
                result = self.fetchone()
                if result and result.get('possessore_data'):
                    return result['possessore_data']
            logger.warning(f"Nessun dato trovato per possessore ID {possessore_id} per l'esportazione.")
            return None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_possessore_data_for_export (ID: {possessore_id}): {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python get_possessore_data_for_export (ID: {possessore_id}): {e}")
            return None

    # --- Metodi Manutenzione e Ottimizzazione (Invariati rispetto a comune_id) ---

    def verifica_integrita_database(self) -> Tuple[bool, str]:
        """Chiama la procedura SQL verifica_integrita_database e cattura i messaggi."""
        # Implementazione originale OK
        messages = []; original_notice_handler = None; problemi_trovati = False; output_msg = ""
        if not self.conn or self.conn.closed: return True, "Errore: Connessione DB non attiva."
        try:
            if hasattr(self.conn, 'notices'): original_notice_handler = self.conn.notices.copy(); self.conn.notices.append(lambda notice: messages.append(str(notice).strip().replace("NOTICE: ","")))
            else: self.conn.add_notice_handler(lambda notice: messages.append(str(notice).strip().replace("NOTICE: ","")))
            if self.execute_query("CALL verifica_integrita_database(NULL)"): self.commit()
            else: problemi_trovati = True; messages.append("Errore esecuzione procedura verifica_integrita_database.")
            for msg in messages:
                if "Problemi" in msg or "Problema:" in msg or "WARNING:" in msg: problemi_trovati = True
                output_msg += msg + "\n"
            if not problemi_trovati and not output_msg: output_msg = "Nessun problema di integrità rilevato."
        except psycopg2.Error as db_err: logger.error(f"Errore DB verifica integrità: {db_err}"); output_msg = f"Errore DB verifica: {db_err}"; problemi_trovati = True
        except Exception as e: logger.error(f"Errore Python verifica integrità: {e}"); output_msg = f"Errore Python verifica: {e}"; problemi_trovati = True
        finally:
            if hasattr(self.conn, 'notices') and original_notice_handler is not None: self.conn.notices = original_notice_handler
        return problemi_trovati, output_msg.strip()

    def refresh_materialized_views(self) -> bool:
        """Aggiorna tutte le viste materializzate definite nel database."""
        logger.info("Avvio aggiornamento viste materializzate...")
        try:
            if self.execute_query("CALL aggiorna_tutte_statistiche()"): self.commit(); logger.info("Aggiornamento viste completato."); return True
            else: logger.error("Fallita chiamata a 'aggiorna_tutte_statistiche'."); return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB aggiornamento viste: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python aggiornamento viste: {e}"); self.rollback(); return False

    def run_database_maintenance(self) -> bool:
        """Esegue ANALYZE e aggiorna le viste materializzate."""
        logger.info("Avvio manutenzione database (ANALYZE, REFRESH MV)...")
        try:
            if self.execute_query("CALL manutenzione_database()"): self.commit(); logger.info("Manutenzione (ANALYZE, REFRESH MV) completata."); return True
            else: logger.error("Fallita chiamata a 'manutenzione_database'."); return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB manutenzione: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python manutenzione: {e}"); self.rollback(); return False

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
        """Imposta variabili di sessione PostgreSQL per l'audit."""
        if not self.conn or self.conn.closed: logger.warning("Tentativo set var sessione senza connessione."); return False
        try:
            user_id_str = str(user_id) if user_id is not None else None; ip_str = client_ip if client_ip is not None else None
            if self.execute_query("SELECT set_config('app.user_id', %s, FALSE);", (user_id_str,)) and \
               self.execute_query("SELECT set_config('app.ip_address', %s, FALSE);", (ip_str,)):
                logger.debug(f"Var sessione impostate: app.user_id='{user_id_str}', app.ip_address='{ip_str}'")
                return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB set var sessione: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python set var sessione: {e}"); return False

    def clear_session_app_user(self):
        """Resetta le variabili di sessione PostgreSQL per l'audit."""
        logger.debug("Reset variabili di sessione app.")
        self.set_session_app_user(user_id=None, client_ip=None)

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
        """Chiama la procedura SQL crea_utente."""
        try:
            call_proc = "CALL crea_utente(%s, %s, %s, %s, %s)"
            params = (username, password_hash, nome_completo, email, ruolo)
            if self.execute_query(call_proc, params): self.commit(); logger.info(f"Utente '{username}' creato."); return True
            return False
        except psycopg2.errors.UniqueViolation: logger.error(f"Errore creazione utente: Username '{username}' o Email '{email}' già esistente."); return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB creazione utente '{username}': {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python creazione utente '{username}': {e}"); self.rollback(); return False

    # In catasto_db_manager.py, dentro la classe CatastoDBManager

    def get_user_credentials(self, username_param: str) -> Optional[Dict]:
        """Recupera ID, username, hash password, nome_completo e ruolo per un utente attivo."""
        try:
            # AGGIUNGERE 'ruolo' ALLA SELECT
            query = "SELECT id, username, password_hash, nome_completo, ruolo FROM utente WHERE username = %s AND attivo = TRUE"
            if self.execute_query(query, (username_param,)):
                user_data = self.fetchone()
                if user_data:
                    logger.info(f"Credenziali (incluso ruolo) recuperate per utente: {user_data.get('username')}, Ruolo: {user_data.get('ruolo')}")
                return user_data # Restituisce l'intero dizionario che ora include 'ruolo'
            return None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_user_credentials per '{username_param}': {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python get_user_credentials per '{username_param}': {e}")
            return None

    def register_access(self, utente_id: int, azione: str, indirizzo_ip: Optional[str] = None,
                        user_agent: Optional[str] = None, esito: bool = True,
                        application_name: str = 'CatastoApp') -> Optional[str]:
        """Chiama la procedura SQL registra_accesso, generando un session_id."""
        session_id = None
        try:
            session_id = str(uuid.uuid4())
            call_proc = "CALL registra_accesso(%s, %s, %s, %s, %s, %s, %s)"
            params = (utente_id, azione, indirizzo_ip, user_agent, esito, session_id, application_name)
            if self.execute_query(call_proc, params):
                self.commit(); logger.info(f"Registrato accesso: Utente ID {utente_id}, Azione {azione}, Esito {esito}, Sessione {session_id[:8]}..."); return session_id
            else: logger.error(f"Fallita chiamata a registra_accesso per utente ID {utente_id}."); return None
        except psycopg2.Error as db_err: logger.error(f"Errore DB registrazione accesso utente ID {utente_id}: {db_err}"); return None
        except Exception as e: logger.error(f"Errore Python registrazione accesso utente ID {utente_id}: {e}"); self.rollback(); return None

    def logout_user(self, user_id: Optional[int], session_id: Optional[str], client_ip: Optional[str] = None) -> bool:
        """Chiama la procedura SQL logout_utente e resetta il contesto di sessione."""
        if user_id is None or session_id is None: logger.warning("Tentativo logout senza user_id/session_id."); self.clear_session_app_user(); return False
        success = False
        #if self.db_manager:
        self.clear_audit_session_variables() # Chiamata corretta al metodo della stessa classe
        try:
            call_proc = "CALL logout_utente(%s, %s, %s)"
            success = self.execute_query(call_proc, (user_id, session_id, client_ip))
            if success: self.commit(); logger.info(f"Logout registrato per utente ID {user_id}, sessione {session_id[:8]}...")
        except psycopg2.Error as db_err: logger.error(f"Errore DB logout utente ID {user_id}: {db_err}")
        except Exception as e: logger.error(f"Errore Python logout utente ID {user_id}: {e}"); self.rollback()
        finally:
             # Resetta sempre le variabili di sessione dopo il logout
             self.clear_session_app_user()
        return success
        

    def check_permission(self, utente_id: int, permesso_nome: str) -> bool:
        """Chiama la funzione SQL ha_permesso."""
        try:
            query = "SELECT ha_permesso(%s, %s) AS permesso"
            if self.execute_query(query, (utente_id, permesso_nome)): result = self.fetchone(); return result.get('permesso', False) if result else False
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB verifica permesso '{permesso_nome}' per utente ID {utente_id}: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python verifica permesso '{permesso_nome}' per utente ID {utente_id}: {e}"); return False

    def get_utenti(self, solo_attivi: Optional[bool] = None) -> List[Dict]:
        """
        Recupera un elenco di utenti dal database.
        È possibile filtrare per utenti solo attivi.
        """
        try:
            query = "SELECT id, username, nome_completo, email, ruolo, attivo, ultimo_accesso FROM utente"
            conditions = []
            params = []

            if solo_attivi is not None:
                conditions.append("attivo = %s")
                params.append(solo_attivi)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY username"

            if self.execute_query(query, tuple(params) if params else None):
                utenti = self.fetchall()
                logger.info(f"Recuperati {len(utenti)} utenti.")
                return utenti
            return []
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB durante il recupero degli utenti: {db_err}")
            return []
        except Exception as e:
            logger.error(f"Errore Python durante il recupero degli utenti: {e}")
            return []
    def get_utente_by_id(self, utente_id: int) -> Optional[Dict]:
        """Recupera i dettagli di un singolo utente tramite ID."""
        try:
            query = "SELECT id, username, nome_completo, email, ruolo, attivo FROM utente WHERE id = %s"
            if self.execute_query(query, (utente_id,)):
                return self.fetchone()
            return None
        except Exception as e:
            logger.error(f"Errore durante il recupero dell'utente ID {utente_id}: {e}")
            return None

    def update_user_details(self, utente_id: int, nome_completo: Optional[str] = None, 
                            email: Optional[str] = None, ruolo: Optional[str] = None, 
                            attivo: Optional[bool] = None) -> bool:
        """
        Aggiorna i dettagli di un utente (nome_completo, email, ruolo, stato attivo).
        Non aggiorna lo username o la password qui.
        """
        if not any([nome_completo, email, ruolo, attivo is not None]):
            logger.warning("Nessun dettaglio fornito per l'aggiornamento utente.")
            return False
        
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
                logger.error(f"Ruolo non valido: {ruolo}")
                return False
            fields_to_update.append("ruolo = %s")
            params.append(ruolo)
        if attivo is not None:
            fields_to_update.append("attivo = %s")
            params.append(attivo)
        
        if not fields_to_update: # Dovrebbe essere già gestito dal controllo any() sopra
            return False

        params.append(utente_id)
        query = f"UPDATE utente SET {', '.join(fields_to_update)}, data_modifica = CURRENT_TIMESTAMP WHERE id = %s"
        
        try:
            if self.execute_query(query, tuple(params)):
                self.commit()
                logger.info(f"Dettagli utente ID {utente_id} aggiornati.")
                return True
            return False
        except psycopg2.errors.UniqueViolation:
            logger.error(f"Errore aggiornamento utente ID {utente_id}: Email '{email}' potrebbe essere già in uso.")
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore durante l'aggiornamento dell'utente ID {utente_id}: {e}")
            self.rollback()
            return False

    def reset_user_password(self, utente_id: int, new_password_hash: str) -> bool:
        """Resetta la password di un utente (tipicamente da un admin)."""
        try:
            query = "UPDATE utente SET password_hash = %s, data_modifica = CURRENT_TIMESTAMP WHERE id = %s"
            if self.execute_query(query, (new_password_hash, utente_id)):
                self.commit()
                logger.info(f"Password resettata per utente ID {utente_id}.")
                return True
            return False
        except Exception as e:
            logger.error(f"Errore durante il reset password per utente ID {utente_id}: {e}")
            self.rollback()
            return False

    def deactivate_user(self, utente_id: int) -> bool:
        """Disattiva un utente (soft delete)."""
        try:
            # Potremmo anche voler invalidare sessioni attive qui, ma è più complesso.
            query = "UPDATE utente SET attivo = FALSE, data_modifica = CURRENT_TIMESTAMP WHERE id = %s"
            if self.execute_query(query, (utente_id,)):
                self.commit()
                logger.info(f"Utente ID {utente_id} disattivato.")
                return True
            return False
        except Exception as e:
            logger.error(f"Errore durante la disattivazione dell'utente ID {utente_id}: {e}")
            self.rollback()
            return False

    # Potrebbe essere utile anche un activate_user se si vuole riattivare
    def activate_user(self, utente_id: int) -> bool:
        """Riattiva un utente precedentemente disattivato."""
        try:
            query = "UPDATE utente SET attivo = TRUE, data_modifica = CURRENT_TIMESTAMP WHERE id = %s"
            if self.execute_query(query, (utente_id,)):
                self.commit()
                logger.info(f"Utente ID {utente_id} riattivato.")
                return True
            return False
        except Exception as e:
            logger.error(f"Errore durante la riattivazione dell'utente ID {utente_id}: {e}")
            self.rollback()
            return False
    def delete_user_permanently(self, utente_id: int) -> bool:
        """
        Elimina fisicamente un utente dal database.
        ATTENZIONE: Operazione distruttiva. Considerare le implicazioni per i log.
        """
        # Controllo preliminare per evitare di eliminare l'unico admin o utenti speciali
        # Questa logica potrebbe essere più complessa (es. controllare se è l'UNICO admin)
        utente_da_eliminare = self.get_utente_by_id(utente_id)
        if utente_da_eliminare and utente_da_eliminare.get('ruolo') == 'admin':
            # Conta quanti admin ci sono
            admin_count_query = "SELECT COUNT(*) AS count FROM utente WHERE ruolo = 'admin' AND attivo = TRUE"
            if self.execute_query(admin_count_query):
                count_result = self.fetchone()
                if count_result and count_result['count'] <= 1:
                    logger.error(f"Tentativo di eliminare l'unico utente amministratore (ID: {utente_id}). Operazione negata.")
                    return False
    
        try:
            # Opzionale: prima di eliminare l'utente, si potrebbero gestire i record dipendenti
            # in accesso_log e audit_log se non si usa ON DELETE SET NULL o CASCADE.
            # Esempio: ANNULLARE utente_id / app_user_id nei log (se si preferisce non avere ID orfani)
            # self.execute_query("UPDATE accesso_log SET utente_id = NULL WHERE utente_id = %s", (utente_id,))
            # self.execute_query("UPDATE audit_log SET app_user_id = NULL WHERE app_user_id = %s", (utente_id,))
            # self.commit() # Se si eseguono queste query

            query = "DELETE FROM utente WHERE id = %s"
            if self.execute_query(query, (utente_id,)):
                # execute_query dovrebbe aver già fatto commit se la query è andata a buon fine
                # ma se l'operazione DELETE non solleva eccezioni e rowcount è > 0, si assume successo.
                # Per DELETE, rowcount è importante. self.cur.rowcount dopo execute_query
                if self.cur and self.cur.rowcount > 0:
                    self.commit() # Commit esplicito dopo il DELETE
                    logger.info(f"Utente ID {utente_id} eliminato fisicamente con successo.")
                    return True
                else:
                    logger.warning(f"Nessun utente trovato con ID {utente_id} per l'eliminazione fisica, o rowcount non disponibile.")
                    self.rollback() # Rollback se nessun utente è stato effettivamente eliminato
                    return False
            return False
        except psycopg2.Error as db_err: # Specificamente per errori DB come violazioni FK
            logger.error(f"Errore DB durante l'eliminazione fisica dell'utente ID {utente_id}: {db_err}")
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore Python durante l'eliminazione fisica dell'utente ID {utente_id}: {e}")
            self.rollback()
            return False

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
    
    def _find_executable(self, name: str) -> Optional[str]:
        """Cerca un eseguibile nel PATH di sistema."""
        executable_path = shutil.which(name)
        if executable_path:
            self.logger.info(f"Trovato eseguibile '{name}' in: {executable_path}")
            return executable_path
        else:
            self.logger.warning(f"Eseguibile '{name}' non trovato nel PATH di sistema.")
            return None

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
                                 pg_dump_executable_path_ui: str, # Percorso dalla UI
                                 format_type: str = "custom",
                                 include_blobs: bool = False
                                ) -> Optional[List[str]]:
        
        actual_pg_dump_path = self._resolve_executable_path(pg_dump_executable_path_ui, "pg_dump.exe") # o solo "pg_dump" per cross-platform
        if not actual_pg_dump_path:
            return None # Errore già loggato da _resolve_executable_path

        # ... (resto del metodo come prima, usando actual_pg_dump_path)
        # Assicurati che db_user, db_host, db_port, db_name siano recuperati correttamente
        if not all([self.conn_params.get("user"), self.conn_params.get("host"),
                    str(self.conn_params.get("port")), self.conn_params.get("dbname")]):
            self.logger.error("Parametri di connessione mancanti per il backup.")
            return None

        db_user = self.conn_params.get("user")
        db_host = self.conn_params.get("host")
        db_port = str(self.conn_params.get("port"))
        db_name = self.conn_params.get("dbname")

        command = [actual_pg_dump_path]
        command.extend(["-U", db_user])
        command.extend(["-h", db_host])
        command.extend(["-p", db_port])

        if format_type == "custom":
            command.extend(["-Fc"])
        elif format_type == "plain":
            command.extend(["-Fp"])
        else:
            self.logger.error(f"Formato di backup non supportato: {format_type}")
            return None

        command.extend(["--file", backup_file_path])
        
        if include_blobs:
            command.extend(["--blobs"])
        
        command.append(db_name)
        
        self.logger.info(f"Comando di backup preparato: {' '.join(command)}")
        return command

    def get_restore_command_parts(self,
                                  backup_file_path: str,
                                  pg_tool_executable_path_ui: str # Percorso dalla UI per pg_restore o psql
                                 ) -> Optional[List[str]]:
        
        db_user = self.conn_params.get("user")
        db_host = self.conn_params.get("host")
        db_port = str(self.conn_params.get("port"))
        db_name = self.conn_params.get("dbname")

        if not all([db_user, db_host, db_port, db_name]):
            self.logger.error("Parametri di connessione mancanti per il ripristino.")
            return None

        command: List[str] = []
        filename, file_extension = os.path.splitext(backup_file_path)
        file_extension = file_extension.lower()

        actual_pg_tool_path = None
        if file_extension in [".dump", ".backup", ".custom"]:
            actual_pg_tool_path = self._resolve_executable_path(pg_tool_executable_path_ui, "pg_restore.exe") # o "pg_restore"
            if not actual_pg_tool_path: return None
            
            command = [actual_pg_tool_path]
            command.extend(["-U", db_user, "-h", db_host, "-p", db_port, "-d", db_name])
            command.extend(["--clean", "--if-exists", "--verbose"]) # Aggiunto verbose per pg_restore
            command.append(backup_file_path)
            
        elif file_extension == ".sql":
            actual_pg_tool_path = self._resolve_executable_path(pg_tool_executable_path_ui, "psql.exe") # o "psql"
            if not actual_pg_tool_path: return None

            command = [actual_pg_tool_path]
            command.extend(["-U", db_user, "-h", db_host, "-p", db_port, "-d", db_name])
            command.extend(["-f", backup_file_path, "-v", "ON_ERROR_STOP=1"])
        else:
            self.logger.error(f"Formato file di backup non riconosciuto: '{file_extension}'")
            return None
            
        self.logger.info(f"Comando di ripristino preparato: {' '.join(command)}")
        return command
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

    # All'interno della classe CatastoDBManager
    # All'interno della classe CatastoDBManager
    def ricerca_avanzata_possessori(self,
                                    query_text: str,
                                    # comune_id è stato rimosso come parametro
                                    similarity_threshold: Optional[float] = 0.2
                                ) -> List[Dict[str, Any]]:
        """
        Esegue una ricerca avanzata di possessori utilizzando le funzioni di similarità di PostgreSQL.
        Utilizza una soglia di similarità specificata.
        """
        
        # La funzione SQL ora accetta (TEXT, REAL)
        query = "SELECT * FROM catasto.ricerca_avanzata_possessori(%s::TEXT, %s::REAL);"
        params = (query_text, similarity_threshold)
        
        try:
            if not self.conn or self.conn.closed:
                logger.error("Connessione al database non attiva.")
                return []
            
            # Assicurati che DictCursor sia importato: from psycopg2.extras import DictCursor
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                if logger.level == logging.DEBUG:
                    try:
                        log_query = cur.mogrify(query, params)
                        logger.debug(f"Esecuzione query (ricerca avanzata possessori): {log_query.decode('utf-8', errors='ignore')}")
                    except Exception as e_mogrify:
                        logger.debug(f"Impossibile eseguire mogrify: {e_mogrify}. Query: {query}, Params: {params}")
                
                cur.execute(query, params)
                results_raw = cur.fetchall()
            
            results = [dict(row) for row in results_raw] if results_raw else []

            if results:
                # *** MODIFICA QUI: Rimuovi comune_id dai messaggi di log ***
                logger.info(f"Ricerca avanzata possessori per '{query_text}' (soglia: {similarity_threshold}) ha prodotto {len(results)} risultati.")
            else:
                # *** MODIFICA QUI: Rimuovi comune_id dai messaggi di log ***
                logger.info(f"Nessun risultato per ricerca avanzata possessori: '{query_text}' (soglia: {similarity_threshold}).")
            return results
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB durante la ricerca avanzata dei possessori: {db_err}")
            self.rollback()
            return []
        except Exception as e:
            # Questo è l'errore che stai vedendo ora (NameError)
            logger.error(f"Errore Python imprevisto durante la ricerca avanzata dei possessori: {e}")
            # Potresti non voler fare rollback per un NameError, dipende se una transazione è attiva
            # self.rollback() # Commentato per ora per NameError
            return []
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

    def get_historical_periods(self) -> List[Dict]:
        """Recupera i periodi storici definiti."""
        try:
            query = "SELECT id, nome, anno_inizio, anno_fine, descrizione FROM periodo_storico ORDER BY anno_inizio"
            if self.execute_query(query): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_historical_periods: {db_err}"); return []
        except Exception as e: logger.error(f"Errore Python get_historical_periods: {e}"); return []
        return []

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
    def set_audit_session_variables(self, app_user_id: Optional[int], session_id: Optional[str]):
        """Imposta le variabili di sessione per l'audit log."""
        if app_user_id is None or session_id is None:
            self.logger.warning("Tentativo di impostare variabili di sessione audit con None.")
            return False # o solleva un errore

        # Usare una connessione dedicata per questi SET non transazionali,
        # oppure assicurarsi che la connessione corrente non sia in una transazione fallita.
        # Idealmente, questi SET dovrebbero essere eseguiti all'inizio di ogni "sessione" logica dell'utente con il DB.
        try:
            with self._get_connection() as conn: # Usa il metodo corretto per ottenere una connessione
                with conn.cursor() as cur:
                    # È buona norma usare placeholder anche per current_setting se il valore viene da input,
                    # ma qui stiamo definendo il nome della variabile.
                    # Assicurati che lo schema 'catasto' esista se prefissi le variabili.
                    # PostgreSQL non supporta placeholder per i nomi delle GUC.
                    # Il quoting è importante se i valori possono contenere caratteri speciali.
                    # psycopg2 farà il quoting corretto per i valori.

                    # SQL per impostare la variabile di sessione (GUC - Grand Unified Configuration)
                    # Queste variabili devono essere prefissate da un nome di estensione custom o un nome univoco.
                    # Ad es., se hai un'estensione "catasto_app", potresti usare "catasto_app.user_id".
                    # Altrimenti, un prefisso come "catasto_audit.user_id".
                    # Per semplicità, uso "catasto.app_user_id" assumendo che non crei conflitti.

                    # Pulisce prima le impostazioni precedenti per la sessione corrente
                    cur.execute("RESET catasto.app_user_id;")
                    cur.execute("RESET catasto.session_id;")

                    # Imposta i nuovi valori
                    cur.execute(f"SET session catasto.app_user_id = '{app_user_id}';") # Intentionally not using %s for GUC name
                    cur.execute(f"SET session catasto.session_id = %s;", (session_id,))

                    # Per verificare (opzionale, per debug):
                    # cur.execute("SELECT current_setting('catasto.app_user_id', true), current_setting('catasto.session_id', true);")
                    # self.logger.debug(f"Audit session variables set: {cur.fetchone()}")

                    conn.commit() # I SET sono a livello di sessione, ma il commit chiude la transazione del cursor.
                                # Per i GUC di sessione, non sono transazionali nel senso stretto,
                                # ma è bene gestire il ciclo di vita della connessione/cursore.
                    self.logger.info(f"Variabili di sessione per audit impostate: app_user_id={app_user_id}, session_id={session_id[:8]}...")
                    return True
        except psycopg2.Error as e:
            self.logger.error(f"Errore DB durante l'impostazione delle variabili di sessione audit: {e}")
            # Potrebbe essere necessario invalidare la connessione nel pool se l'errore è grave
            return False
        except Exception as e:
            self.logger.error(f"Errore generico durante l'impostazione delle variabili di sessione audit: {e}")
            return False

    def clear_audit_session_variables(self):
        """Pulisce le variabili di sessione per l'audit log (es. al logout)."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("RESET catasto.app_user_id;")
                    cur.execute("RESET catasto.session_id;")
                    conn.commit()
                    self.logger.info("Variabili di sessione per audit resettate.")
                    return True
        except psycopg2.Error as e:
            self.logger.error(f"Errore DB durante il reset delle variabili di sessione audit: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Errore generico durante il reset delle variabili di sessione audit: {e}")
            return False

    # Nel tuo metodo `login_user` o dove gestisci il login dell'utente applicativo in CatastoDBManager,
    # dopo aver verificato le credenziali e ottenuto l'app_user_id e generato/recuperato un session_id:
    # self.set_audit_session_variables(app_user_id, session_id_valido)

    # E nel metodo `logout_user`:
    # self.clear_audit_session_variables()
    # E anche nel `disconnect` o `closeEvent` della GUI per sicurezza.    
        
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