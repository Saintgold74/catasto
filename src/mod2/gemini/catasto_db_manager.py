#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestore Database Catasto Storico - Versione Riscritto
=====================================================
Script per la gestione del database catastale con supporto
per operazioni CRUD e chiamate alle stored procedure/funzioni.

Include miglioramenti per:
- Gestione Cursore con 'with' statement
- Configurazione esterna delle credenziali
- Sicurezza password con bcrypt
- Gestione errori più robusta (esempio)
- Type Hinting

Autore: Marco Santoro
Data: 24/04/2025
"""

import psycopg2
import psycopg2.extras # Per DictCursor
import psycopg2.errors # Per catturare errori specifici DB
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
import sys
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import bcrypt # Per hashing password
import json # Per esportazioni JSON

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("catasto_db.log", encoding='utf-8'), # Specifica encoding
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CatastoDB")

class CatastoDBManager:
    """
    Classe per la gestione delle operazioni sul database catastale storico.
    Gestisce connessione, transazioni ed esecuzione query.
    """

    def __init__(self, dbname: str, user: str, password: str,
                 host: str, port: int, schema: str = "catasto"):
        """
        Inizializza il gestore del database. Le credenziali devono essere fornite.

        Args:
            dbname: Nome del database.
            user: Nome utente per la connessione.
            password: Password per la connessione.
            host: Host del server database.
            port: Porta del server database.
            schema: Schema predefinito da usare (default: 'catasto').
        """
        self.dbname = dbname
        self.user = user
        self.password = password # Memorizza per riconnessione
        self.host = host
        self.port = port
        self.schema = schema
        self.conn: Optional[psycopg2.extensions.connection] = None
        # Attributi per memorizzare l'ultimo risultato/stato da execute_query
        self._last_result: Optional[List[Dict[str, Any]]] = None
        self._last_rowcount: int = -1

        logger.info(f"Inizializzato gestore per database {dbname} (Host: {host}) schema {schema}")

    # --- Gestione Connessione ---

    def connect(self) -> bool:
        """Stabilisce la connessione al database utilizzando gli attributi della classe."""
        if self.conn is not None and not self.conn.closed:
            # logger.debug("Connessione già attiva.")
            return True
        try:
            logger.info(f"Tentativo di connessione a {self.dbname} su {self.host}:{self.port}...")
            self.conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            # Imposta livello isolamento e autocommit a False (gestione manuale transazioni)
            self.conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
            self.conn.autocommit = False
            # Imposta lo schema di ricerca per la sessione
            with self.conn.cursor() as cur:
                 # Usa placeholder per lo schema per sicurezza minima (anche se raro per SET)
                 cur.execute("SET search_path TO %s, public;", (self.schema,))

            logger.info("Connessione stabilita con successo")
            return True
        except psycopg2.OperationalError as e:
            logger.error(f"Errore operativo durante la connessione: {e}")
            self.conn = None
            return False
        except Exception as e:
            logger.error(f"Errore generico durante la connessione: {e}")
            self.conn = None
            return False

    def disconnect(self):
        """Chiude la connessione al database se aperta."""
        if self.conn is not None and not self.conn.closed:
            try:
                self.conn.close()
                logger.info("Disconnessione dal database completata.")
            except Exception as e:
                logger.error(f"Errore durante la disconnessione: {e}")
            finally:
                 self.conn = None # Assicura che sia None dopo chiusura o errore

    # --- Gestione Transazioni ---

    def commit(self):
        """Esegue il commit della transazione corrente."""
        if self.conn and not self.conn.closed:
            try:
                self.conn.commit()
                # logger.debug("Commit transazione eseguito.")
            except psycopg2.Error as e:
                logger.error(f"Errore durante il commit: {e}")
                # Considera se propagare l'errore
        else:
            logger.warning("Impossibile eseguire commit: connessione non attiva.")

    def rollback(self):
        """Esegue il rollback della transazione corrente."""
        if self.conn and not self.conn.closed:
            try:
                self.conn.rollback()
                logger.info("Rollback transazione avvenuto con successo.")
            except psycopg2.Error as e:
                logger.error(f"Errore durante il rollback: {e}")
        else:
            logger.warning("Impossibile eseguire rollback: connessione non attiva.")

    # --- Esecuzione Query e Fetch Risultati ---

    def execute_query(self, query: str, params: Optional[Union[Tuple, Dict]] = None) -> bool:
        """
        Esegue una query sul database, gestendo la connessione e il cursore con 'with'.
        I risultati (se presenti) vengono memorizzati in self._last_result.

        Args:
            query: La stringa SQL della query.
            params: I parametri per la query (opzionale).

        Returns:
            bool: True se l'esecuzione non ha generato eccezioni, False altrimenti.
        """
        self._last_result = None
        self._last_rowcount = -1

        if not self.conn or self.conn.closed:
            logger.warning("Connessione persa o non inizializzata. Tentativo di riconnessione...")
            if not self.connect():
                logger.error("Impossibile eseguire la query: riconnessione fallita.")
                return False
            # Se la riconnessione ha successo, conn non è più None

        # Assicurati che self.conn non sia None prima di usarlo (controllo per mypy)
        if not self.conn:
             logger.error("Errore critico: Connessione è None anche dopo tentativo di connect.")
             return False

        try:
            # Usa un context manager per il cursore (DictCursor per risultati come dizionari)
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # logger.debug(f"Esecuzione query: {cur.mogrify(query, params).decode('utf-8','ignore') if params else query}")
                cur.execute(query, params)
                self._last_rowcount = cur.rowcount

                # Recupera i risultati se la query li produce (es. SELECT, funzioni RETURNING)
                if cur.description:
                    try:
                         self._last_result = cur.fetchall()
                         # logger.debug(f"Query results fetched: {len(self._last_result)} rows")
                    except psycopg2.ProgrammingError as pe:
                         logger.debug(f"Nessun risultato da fetchare (atteso per CALL/INSERT/etc.): {pe}")
                         self._last_result = []
                else:
                     self._last_result = [] # Nessun risultato atteso

            return True # Esecuzione riuscita (nessuna eccezione)

        except psycopg2.Error as db_err: # Cattura errori specifici di psycopg2
            logger.error(f"Errore DB durante l'esecuzione della query: {db_err}")
            # Non è necessario loggare query/params qui se vengono loggati dai metodi chiamanti
            # logger.error(f"Query: {query}")
            # logger.error(f"Parametri: {params}")
            # Il rollback viene gestito nel metodo chiamante di livello superiore
            return False
        except Exception as e: # Cattura altri errori imprevisti
            logger.error(f"Errore generico durante l'esecuzione della query: {e}")
            # logger.error(f"Query: {query}")
            # logger.error(f"Parametri: {params}")
            return False

    def fetchone(self) -> Optional[Dict[str, Any]]:
        """
        Restituisce la prima riga dell'ultimo risultato memorizzato da execute_query.
        """
        if self._last_result and len(self._last_result) > 0:
            return dict(self._last_result[0]) # Restituisce una copia
        return None

    def fetchall(self) -> List[Dict[str, Any]]:
        """
        Restituisce tutte le righe dell'ultimo risultato memorizzato da execute_query.
        """
        # Restituisce una copia della lista di dizionari
        return [dict(row) for row in self._last_result] if self._last_result else []

    def get_last_rowcount(self) -> int:
         """Restituisce il rowcount dell'ultima query eseguita."""
         return self._last_rowcount

    # --- METODI CRUD BASE (Script 03/13) ---

    def get_comuni(self) -> List[Dict]:
        """Recupera tutti i comuni dal database."""
        if self.execute_query("SELECT id, nome, provincia, regione FROM comune ORDER BY nome"):
            return self.fetchall()
        return []

    def insert_comune(self, nome: str, provincia: str, regione: str) -> bool:
        """Inserisce o aggiorna un comune."""
        query = """
            INSERT INTO comune (nome, provincia, regione) VALUES (%s, %s, %s)
            ON CONFLICT (nome) DO UPDATE SET
                provincia = EXCLUDED.provincia,
                regione = EXCLUDED.regione
        """
        try:
            if self.execute_query(query, (nome, provincia, regione)):
                self.commit()
                logger.info(f"Comune '{nome}' inserito/aggiornato.")
                return True
            return False
        except Exception as e:
             logger.error(f"Errore DB in insert_comune per '{nome}': {e}")
             self.rollback()
             return False

    def inserisci_possessore(self, nome_completo: str, comune_residenza: str,
                             codice_fiscale: Optional[str] = None, paternita: Optional[str] = None,
                             data_nascita: Optional[date] = None, luogo_nascita: Optional[str] = None,
                             note: Optional[str] = None) -> Optional[int]:
        """
        Inserisce un nuovo possessore nel database usando la funzione SQL
        e restituisce l'ID del possessore inserito o trovato.
        """
        query = "SELECT inserisci_possessore(%s, %s, %s, %s, %s, %s, %s)"
        params = (nome_completo, codice_fiscale, comune_residenza, paternita, data_nascita, luogo_nascita, note)
        try:
            if self.execute_query(query, params):
                result = self.fetchone()
                possessore_id = result.get('inserisci_possessore') if result else None
                if possessore_id:
                    self.commit() # Commit solo se l'inserimento ha avuto successo
                    logger.info(f"Possessore '{nome_completo}' inserito/trovato con ID: {possessore_id}")
                    return possessore_id
                else:
                     logger.warning(f"La funzione inserisci_possessore per '{nome_completo}' non ha restituito un ID.")
                     self.rollback() # Annulla se non è stato restituito un ID valido
                     return None
            else:
                self.rollback() # Annulla se execute_query fallisce
                return None
        except Exception as e:
            logger.error(f"Errore DB in inserisci_possessore per '{nome_completo}': {e}")
            self.rollback()
            return None

    def get_possessori_per_comune(self, comune_nome: str) -> List[Dict]:
        """Recupera i possessori residenti in un dato comune."""
        query = """
            SELECT p.id, p.nome_completo, p.paternita, p.data_nascita
            FROM possessore p JOIN comune c ON p.comune_residenza_id = c.id
            WHERE c.nome = %s ORDER BY p.nome_completo
        """
        if self.execute_query(query, (comune_nome,)):
            return self.fetchall()
        return []

    def insert_localita(self, comune_nome: str, nome_localita: str,
                        tipo: Optional[str] = None, note: Optional[str] = None) -> Optional[int]:
        """Inserisce una località associata a un comune."""
        query = "SELECT inserisci_localita(%s, %s, %s, %s)"
        params = (comune_nome, nome_localita, tipo, note)
        try:
            if self.execute_query(query, params):
                result = self.fetchone()
                localita_id = result.get('inserisci_localita') if result else None
                if localita_id:
                    self.commit()
                    logger.info(f"Località '{nome_localita}' inserita/trovata con ID: {localita_id} per comune '{comune_nome}'.")
                    return localita_id
                else:
                     logger.warning(f"Funzione inserisci_localita per '{nome_localita}' non ha restituito ID.")
                     self.rollback()
                     return None
            else:
                self.rollback()
                return None
        except Exception as e:
            logger.error(f"Errore DB in insert_localita per '{nome_localita}': {e}")
            self.rollback()
            return None

    def get_localita_per_comune(self, comune_nome: str) -> List[Dict]:
        """Recupera le località di un comune."""
        query = """
            SELECT l.id, l.nome, l.tipo_localita, l.note
            FROM localita l JOIN comune c ON l.comune_id = c.id
            WHERE c.nome = %s ORDER BY l.nome
        """
        if self.execute_query(query, (comune_nome,)):
            return self.fetchall()
        return []

    def get_partite_per_comune(self, comune_nome: str) -> List[Dict]:
        """Recupera le partite di un comune."""
        query = """
            SELECT p.id, p.numero_partita, p.tipo, p.stato, p.data_impianto
            FROM partita p JOIN comune c ON p.comune_id = c.id
            WHERE c.nome = %s ORDER BY p.numero_partita
        """
        if self.execute_query(query, (comune_nome,)):
            return self.fetchall()
        return []

    def search_partite(self, comune_nome: Optional[str] = None, tipo: Optional[str] = None,
                       stato: Optional[str] = None, possessore_search: Optional[str] = None,
                       natura_immobile_search: Optional[str] = None) -> List[Dict]:
        """Esegue una ricerca semplice delle partite con vari filtri."""
        query = "SELECT * FROM cerca_partite(%s, %s, %s, %s, %s)"
        params = (comune_nome, tipo, stato, possessore_search, natura_immobile_search)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def get_partita_details(self, partita_id: int) -> Optional[Dict]:
        """Recupera dettagli completi di una partita usando la funzione SQL."""
        query = "SELECT * FROM get_dettagli_partita(%s)"
        if self.execute_query(query, (partita_id,)):
            result = self.fetchone() # La funzione restituisce una sola riga JSON
            if result:
                 # La funzione SQL restituisce una singola colonna di tipo JSON o JSONB
                 # Accediamo al primo (e unico) valore del dizionario risultato
                 json_details = next(iter(result.values()), None)
                 if json_details:
                     # psycopg2 potrebbe aver già decodificato il JSON in un dict Python
                     if isinstance(json_details, dict):
                         return json_details
                     else: # Altrimenti, prova a decodificare la stringa JSON
                         try:
                             return json.loads(json_details)
                         except json.JSONDecodeError as jde:
                              logger.error(f"Errore decodifica JSON dettagli partita {partita_id}: {jde}")
                              return None
                 else:
                      logger.warning(f"Dettagli partita ID {partita_id} restituiti vuoti dalla funzione SQL.")
                      return None
            else:
                 logger.warning(f"Nessun dettaglio trovato per partita ID {partita_id}.")
                 return None
        return None

    def registra_consultazione(self, data: date, richiedente: str, motivazione: str, materiale_consultato: str, funzionario_autorizzante: str, documento_identita: Optional[str] = None) -> Optional[int]:
        """Registra una consultazione usando la procedura SQL."""
        # Questa procedura (da script 03) non restituisce ID, quindi commit diretto
        call_proc = "CALL registra_consultazione(%s, %s, %s, %s, %s, %s)"
        params = (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante)
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Consultazione registrata per '{richiedente}' in data {data}.")
                # Non possiamo restituire l'ID direttamente da questa procedura
                # Potremmo fare una query SELECT successiva se necessario, ma complica.
                return 0 # Restituisce 0 per indicare successo senza ID
            else:
                self.rollback()
                return None # Indica fallimento
        except Exception as e:
            logger.error(f"Errore DB registrazione consultazione per '{richiedente}': {e}")
            self.rollback()
            return None

    def genera_certificato_proprieta(self, partita_id: int) -> Optional[str]:
        """Genera il testo del certificato di proprietà per una partita."""
        query = "SELECT genera_certificato_proprieta(%s) AS certificato"
        if self.execute_query(query, (partita_id,)):
            result = self.fetchone()
            return result.get('certificato') if result else None
        return None

    # --- METODI PER WORKFLOW INTEGRATI (Script 13) ---

    def registra_nuova_proprieta_v2(self, comune_nome: str, numero_partita: str, tipo_partita: str, data_impianto: date,
                                    possessori_info: List[Dict], immobili_info: List[Dict]) -> Optional[int]:
        """Registra una nuova proprietà completa (Partita, Possessori, Immobili) usando la procedura v2."""
        # Converti le liste di dizionari in stringhe JSON per la procedura SQL
        try:
            possessori_json = json.dumps(possessori_info)
            immobili_json = json.dumps(immobili_info)
        except TypeError as te:
            logger.error(f"Errore nella serializzazione JSON per nuova proprietà: {te}")
            return None

        call_proc = "CALL registra_nuova_proprieta_v2(%s, %s, %s, %s, %s, %s)"
        params = (comune_nome, numero_partita, tipo_partita, data_impianto, possessori_json, immobili_json)
        try:
            # La procedura v2 dovrebbe restituire l'ID della partita creata tramite un parametro OUT o RAISE NOTICE.
            # Poiché CALL non gestisce facilmente OUT in psycopg2 standard, assumiamo che sollevi eccezione in caso di errore.
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Registrazione nuova proprietà (Partita {numero_partita}, Comune {comune_nome}) avviata.")
                # L'ID esatto non viene restituito qui, si potrebbe fare query successiva se necessario.
                # Restituiamo un valore fittizio > 0 per indicare successo potenziale
                return 1
            else:
                logger.error(f"Fallita chiamata a registra_nuova_proprieta_v2 (rollback eseguito).")
                self.rollback()
                return None
        except psycopg2.Error as db_err:
             logger.error(f"Errore DB in registra_nuova_proprieta_v2: {db_err}")
             self.rollback()
             return None
        except Exception as e:
            logger.error(f"Errore generico in registra_nuova_proprieta_v2: {e}")
            self.rollback()
            return None


    def registra_passaggio_proprieta_v2(self, partita_id_origine: int, tipo_variazione: str, data_variazione: date,
                                        possessori_uscenti_ids: List[int], possessori_entranti_info: List[Dict],
                                        contratto_info: Optional[Dict] = None) -> Optional[Dict]:
        """Registra un passaggio di proprietà usando la procedura v2."""
        try:
            possessori_entranti_json = json.dumps(possessori_entranti_info)
            contratto_json = json.dumps(contratto_info) if contratto_info else None
            uscenti_ids_array = possessori_uscenti_ids # psycopg2 converte liste Python in array SQL

        except TypeError as te:
            logger.error(f"Errore nella serializzazione JSON per passaggio proprietà: {te}")
            return {'success': False, 'message': 'Errore interno serializzazione JSON'}

        call_proc = "CALL registra_passaggio_proprieta_v2(%s, %s, %s, %s, %s, %s)"
        params = (partita_id_origine, tipo_variazione, data_variazione, uscenti_ids_array, possessori_entranti_json, contratto_json)

        try:
            # Anche qui, la procedura v2 potrebbe non restituire valori direttamente via CALL.
            # Assumiamo successo se non ci sono eccezioni.
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Registrazione passaggio proprietà per Partita ID {partita_id_origine} avviata.")
                # Non abbiamo gli ID esatti qui, ma indichiamo successo
                return {'success': True, 'message': 'Operazione avviata con successo.'}
            else:
                self.rollback()
                logger.error(f"Fallita chiamata a registra_passaggio_proprieta_v2.")
                # Tenta di recuperare un messaggio di errore se la procedura lo imposta
                # Questo richiede che la procedura SQL usi RAISE EXCEPTION con dettagli
                # o una funzione separata per leggere lo stato/errore. Qui simuliamo.
                return {'success': False, 'message': 'Esecuzione procedura fallita (controlla log DB).'}
        except psycopg2.Error as db_err:
             logger.error(f"Errore DB in registra_passaggio_proprieta_v2: {db_err}")
             self.rollback()
             # Prova a estrarre il messaggio dall'eccezione
             return {'success': False, 'message': f"Errore DB: {db_err}"}
        except Exception as e:
            logger.error(f"Errore generico in registra_passaggio_proprieta_v2: {e}")
            self.rollback()
            return {'success': False, 'message': f"Errore generico: {e}"}


    # --- METODI REPORTISTICA (Script 14) ---

    def get_report_consultazioni(self, data_inizio: date, data_fine: date) -> Optional[str]:
        """Genera un report testuale delle consultazioni in un periodo."""
        query = "SELECT genera_report_consultazioni(%s, %s) AS report"
        if self.execute_query(query, (data_inizio, data_fine)):
            result = self.fetchone()
            return result.get('report') if result else None
        return None

    # --- METODI PER LA GESTIONE UTENTI (Script 07) ---

    def create_user(self, username: str, plain_password: str, nome_completo: str, email: str, ruolo: str) -> bool:
        """Crea un nuovo utente, hashando la password con bcrypt."""
        try:
            password_hash_bytes = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
            password_hash = password_hash_bytes.decode('utf-8')

            call_proc = "CALL crea_utente(%s, %s, %s, %s, %s)"
            if self.execute_query(call_proc, (username, password_hash, nome_completo, email, ruolo)):
                self.commit()
                logger.info(f"Utente {username} creato con successo.")
                return True
            self.rollback()
            return False
        except psycopg2.errors.UniqueViolation:
             logger.error(f"Errore: Username '{username}' o Email '{email}' già esistente.")
             self.rollback()
             return False
        except psycopg2.Error as db_err:
             logger.error(f"Errore DB durante creazione utente {username}: {db_err}")
             self.rollback()
             return False
        except Exception as e:
            logger.error(f"Errore generico creazione utente {username}: {e}")
            self.rollback()
            return False

    def get_user_credentials(self, username: str) -> Optional[Dict]:
        """Recupera ID e hash password (bcrypt) per verifica login."""
        query = "SELECT id, password_hash FROM utente WHERE username = %s AND attivo = TRUE"
        try:
            if self.execute_query(query, (username,)):
                return self.fetchone()
            return None
        except Exception as e:
            logger.error(f"Errore recupero credenziali per {username}: {e}")
            return None

    def register_access(self, utente_id: Optional[int], azione: str, indirizzo_ip: Optional[str] = None, user_agent: Optional[str] = None, esito: bool = True) -> bool:
        """Registra un evento di accesso nel log."""
        # Gestisci il caso di utente non trovato (es. login fallito per utente inesistente)
        # La procedura SQL potrebbe accettare NULL per utente_id
        effective_user_id = utente_id if utente_id is not None else None # O un valore speciale se la proc. lo richiede

        call_proc = "CALL registra_accesso(%s, %s, %s, %s, %s)"
        params = (effective_user_id, azione, indirizzo_ip, user_agent, esito)
        try:
            # Questa operazione dovrebbe essere atomica, commit/rollback gestito qui
            if self.execute_query(call_proc, params):
                self.commit()
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore durante registrazione accesso per utente {effective_user_id}: {e}")
            self.rollback()
            return False

    def check_permission(self, utente_id: int, permesso_nome: str) -> bool:
        """Verifica se un utente ha un permesso."""
        query = "SELECT ha_permesso(%s, %s) AS permesso"
        try:
            if self.execute_query(query, (utente_id, permesso_nome)):
                result = self.fetchone()
                return result.get('permesso', False) if result else False
            return False
        except Exception as e:
             logger.error(f"Errore verifica permesso '{permesso_nome}' per utente {utente_id}: {e}")
             return False

    # --- METODI PER REPORTISTICA AVANZATA (Script 08) ---

    def refresh_materialized_views(self) -> bool:
        """Aggiorna tutte le viste materializzate definite nello script 08."""
        try:
            logger.info("Avvio aggiornamento viste materializzate...")
            # Chiama la procedura SQL che raggruppa gli aggiornamenti
            if self.execute_query("CALL aggiorna_tutte_statistiche()"):
                self.commit() # Commit necessario dopo CALL
                logger.info("Viste materializzate aggiornate con successo.")
                return True
            else:
                 logger.error("Chiamata a aggiorna_tutte_statistiche() fallita.")
                 self.rollback()
                 return False
        except Exception as e:
            logger.error(f"Errore durante l'aggiornamento delle viste materializzate: {e}")
            self.rollback()
            return False

    def get_statistiche_comune(self) -> List[Dict]:
        """Recupera statistiche per comune dalla vista materializzata."""
        query = "SELECT comune, provincia, totale_partite, partite_attive, partite_inattive, totale_possessori, totale_immobili FROM mv_statistiche_comune ORDER BY comune"
        if self.execute_query(query):
            return self.fetchall()
        return []

    def get_immobili_per_tipologia(self, comune_nome: Optional[str] = None) -> List[Dict]:
        """Recupera riepilogo immobili per tipologia dalla vista materializzata."""
        params = []
        query = "SELECT comune_nome, classificazione, numero_immobili, totale_piani, totale_vani FROM mv_immobili_per_tipologia"
        if comune_nome:
            query += " WHERE comune_nome = %s"
            params.append(comune_nome)
        query += " ORDER BY comune_nome, classificazione"
        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []

    def get_partite_complete_view(self, comune_nome: Optional[str] = None, stato: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Recupera dati completi partite dalla vista materializzata."""
        conditions = []
        params = []
        query = "SELECT partita_id, comune_nome, numero_partita, tipo, data_impianto, stato, possessori, num_immobili, tipi_immobili, localita FROM mv_partite_complete"
        if comune_nome:
            conditions.append("comune_nome ILIKE %s")
            params.append(f"%{comune_nome}%")
        if stato:
            conditions.append("stato = %s")
            params.append(stato)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY comune_nome, numero_partita LIMIT %s"
        params.append(limit)
        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []

    def get_cronologia_variazioni(self, comune_origine: Optional[str] = None, tipo_variazione: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Recupera cronologia variazioni dalla vista materializzata."""
        conditions = []
        params = []
        query = "SELECT variazione_id, tipo_variazione, data_variazione, partita_origine_numero, comune_origine, possessori_origine, partita_dest_numero, comune_dest, possessori_dest, tipo_contratto, notaio, data_contratto FROM mv_cronologia_variazioni"
        if comune_origine:
            conditions.append("comune_origine ILIKE %s")
            params.append(f"%{comune_origine}%")
        if tipo_variazione:
            conditions.append("tipo_variazione = %s")
            params.append(tipo_variazione)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY data_variazione DESC LIMIT %s"
        params.append(limit)
        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []

    def get_report_annuale_partite(self, comune: str, anno: int) -> List[Dict]:
        """Genera report annuale partite per comune."""
        query = "SELECT * FROM report_annuale_partite(%s, %s)"
        if self.execute_query(query, (comune, anno)):
            return self.fetchall()
        return []

    def get_report_proprieta_possessore(self, possessore_id: int, data_inizio: date, data_fine: date) -> List[Dict]:
        """Genera report proprietà di un possessore in un periodo."""
        query = "SELECT * FROM report_proprieta_possessore(%s, %s, %s)"
        if self.execute_query(query, (possessore_id, data_inizio, data_fine)):
            return self.fetchall()
        return []

    # --- METODI PER IL SISTEMA DI BACKUP (Script 09) ---

    def register_backup_log(self, nome_file: str, utente: str, tipo: str, esito: bool, percorso_file: str, dimensione_bytes: Optional[int] = None, messaggio: Optional[str] = None) -> Optional[int]:
        """Registra un'operazione di backup nel log."""
        try:
            query = "SELECT registra_backup(%s, %s, %s, %s, %s, %s, %s)"
            params = (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)
            if self.execute_query(query, params):
                result = self.fetchone()
                backup_id = result.get('registra_backup') if result else None
                if backup_id is not None: # Controlla se non è None
                    self.commit()
                    logger.info(f"Registrato log di backup con ID: {backup_id}")
                    return backup_id
                else:
                    logger.warning("La funzione registra_backup non ha restituito un ID.")
                    self.rollback() # Annulla se non c'è ID
                    return None
            else:
                self.rollback() # Annulla se execute fallisce
                return None
        except Exception as e:
            logger.error(f"Errore durante la registrazione del log di backup: {e}")
            self.rollback()
            return None

    def get_backup_command_suggestion(self, tipo: str = 'completo') -> Optional[str]:
        """Ottiene suggerimento comando pg_dump."""
        query = "SELECT get_backup_commands(%s) AS commands"
        if self.execute_query(query, (tipo,)):
            result = self.fetchone()
            return result.get('commands') if result else None
        return None

    def get_restore_command_suggestion(self, backup_log_id: int) -> Optional[str]:
        """Ottiene suggerimento comando psql per restore."""
        check_query = "SELECT 1 FROM backup_registro WHERE id = %s"
        if self.execute_query(check_query, (backup_log_id,)):
             if not self.fetchone():
                  logger.error(f"Nessun log di backup trovato con ID: {backup_log_id}")
                  return None # ID non trovato

        query = "SELECT get_restore_commands(%s) AS command"
        if self.execute_query(query, (backup_log_id,)):
            result = self.fetchone()
            return result.get('command') if result else None
        return None

    def cleanup_old_backup_logs(self, giorni_conservazione: int = 30) -> bool:
        """Esegue pulizia log di backup vecchi."""
        try:
            call_proc = "CALL pulizia_backup_vecchi(%s)"
            if self.execute_query(call_proc, (giorni_conservazione,)):
                self.commit()
                logger.info(f"Eseguita pulizia log di backup più vecchi di {giorni_conservazione} giorni.")
                return True
            else:
                 self.rollback()
                 return False
        except Exception as e:
            logger.error(f"Errore durante la pulizia dei log di backup: {e}")
            self.rollback()
            return False

    def generate_backup_script(self, backup_dir: str) -> Optional[str]:
        """Genera script bash per backup automatico."""
        query = "SELECT genera_script_backup_automatico(%s) AS script_content"
        if self.execute_query(query, (backup_dir,)):
            result = self.fetchone()
            return result.get('script_content') if result else None
        return None

    def get_backup_logs(self, limit: int = 20) -> List[Dict]:
        """Recupera gli ultimi N log di backup."""
        query = """
            SELECT id, nome_file, timestamp, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file
            FROM backup_registro ORDER BY timestamp DESC LIMIT %s
        """
        if self.execute_query(query, (limit,)):
            return self.fetchall()
        return []

    # --- METODI PER OTTIMIZZAZIONE E RICERCA AVANZATA (Script 10) ---

    def ricerca_avanzata_possessori(self, query_text: str) -> List[Dict]:
        """Esegue ricerca avanzata (similarità) sui possessori."""
        query = "SELECT * FROM ricerca_avanzata_possessori(%s)"
        if self.execute_query(query, (query_text,)):
            return self.fetchall()
        logger.error(f"Errore durante ricerca avanzata possessori per '{query_text}'")
        return []

    def ricerca_avanzata_immobili(self, comune: Optional[str] = None, natura: Optional[str] = None, localita: Optional[str] = None, classificazione: Optional[str] = None, possessore: Optional[str] = None) -> List[Dict]:
        """Esegue ricerca avanzata immobili con filtri multipli."""
        query = "SELECT * FROM ricerca_avanzata_immobili(%s, %s, %s, %s, %s)"
        params = (comune, natura, localita, classificazione, possessore)
        if self.execute_query(query, params):
            return self.fetchall()
        logger.error("Errore durante ricerca avanzata immobili")
        return []

    def run_database_maintenance(self) -> bool:
        """Esegue VACUUM ANALYZE direttamente e aggiorna viste materializzate."""
        all_success = True
        original_autocommit = None
        tables_to_maintain = ['comune', 'possessore', 'partita', 'immobile', 'localita', 'variazione', 'contratto', 'consultazione', 'utente', 'audit_log', 'backup_registro', 'periodo_storico', 'nome_storico', 'documento_storico', 'documento_partita']

        try:
            if not self.conn or self.conn.closed:
                 if not self.connect():
                      return False
            if not self.conn: return False # Controllo aggiuntivo

            original_autocommit = self.conn.autocommit
            self.conn.autocommit = True
            logger.info("Impostata modalità autocommit per VACUUM/ANALYZE.")

            for table in tables_to_maintain:
                logger.info(f"Esecuzione VACUUM ANALYZE su {self.schema}.{table}...")
                # Aggiungi schema al nome tabella per sicurezza
                if not self.execute_query(f"VACUUM (VERBOSE, ANALYZE) {self.schema}.{table}"):
                    logger.warning(f"VACUUM ANALYZE su {table} potrebbe essere fallito (controllare log DB).")

            logger.info("VACUUM ANALYZE completato.")

        except Exception as e:
            logger.error(f"Errore durante VACUUM/ANALYZE in autocommit: {e}")
            all_success = False
        finally:
            if self.conn and not self.conn.closed:
                if original_autocommit is not None:
                    self.conn.autocommit = original_autocommit
                    logger.info(f"Ripristinata modalità autocommit a: {original_autocommit}")
                else:
                     self.conn.autocommit = False # Default sicuro
                     logger.warning("Ripristinata modalità autocommit a False (stato originale sconosciuto).")

        if all_success:
            logger.info("Aggiornamento Viste Materializzate (post manutenzione)...")
            if not self.refresh_materialized_views():
                 logger.error("Fallito aggiornamento delle viste materializzate post manutenzione.")
                 all_success = False
            else:
                 logger.info("Viste Materializzate aggiornate post manutenzione.")

        return all_success

    def analyze_slow_queries(self, min_duration_ms: int = 1000) -> List[Dict]:
        """Chiama funzione SQL per analizzare query lente (richiede pg_stat_statements)."""
        # Verifica estensione (opzionale ma utile)
        ext_ok = False
        try:
             if self.execute_query("SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements' LIMIT 1"):
                  if self.fetchone():
                       ext_ok = True
                  else:
                       logger.error("Estensione 'pg_stat_statements' NON è abilitata/installata.")
             else:
                  logger.warning("Impossibile verificare estensione 'pg_stat_statements'.")
        except Exception as check_err:
             logger.warning(f"Errore verifica estensione pg_stat_statements: {check_err}")

        if not ext_ok: return [] # Non procedere senza estensione

        logger.info(f"Ricerca query più lente di {min_duration_ms} ms...")
        query = "SELECT * FROM analizza_query_lente(%s)"
        try:
            if self.execute_query(query, (min_duration_ms,)):
                return self.fetchall()
            return []
        except psycopg2.Error as db_err:
             logger.error(f"Errore analisi query lente: {db_err}. Estensione 'pg_stat_statements' configurata correttamente?")
             return []
        except Exception as e:
             logger.error(f"Errore generico analisi query lente: {e}")
             return []

    def check_index_fragmentation(self) -> Optional[List[Dict]]:
        """Esegue procedura SQL per controllare frammentazione indici."""
        try:
            logger.info("Avvio controllo frammentazione indici (Output principale nei log DB)...")
            # Esegui la procedura; l'output principale è via RAISE NOTICE nel DB
            if not self.execute_query("CALL controlla_frammentazione_indici()"):
                 self.rollback() # Annulla se la chiamata fallisce
                 return None

            self.commit() # Commit dopo CALL

            # Tenta di leggere risultati da tabella temporanea (se procedura modificata)
            logger.info("Tentativo lettura risultati frammentazione da 'index_stats' (opzionale)...")
            if self.execute_query("SELECT schema_name, table_name, index_name, bloat_ratio, bloat_size FROM index_stats WHERE bloat_ratio > 30 ORDER BY bloat_ratio DESC"):
                 results = self.fetchall()
                 if results:
                     logger.info(f"Trovati {len(results)} indici frammentati (programmaticamente).")
                 else:
                     logger.info("Nessun indice frammentato rilevato programmaticamente (>30%).")
                 # Potresti voler droppare la tabella temp qui se usata
                 return results
            else:
                 logger.warning("Impossibile leggere 'index_stats'. Controlla log DB per output procedura.")
                 return None # Indica che non sono stati letti programmaticamente
        except psycopg2.errors.UndefinedTable:
             logger.info("'index_stats' non trovata, procedura probabilmente usa solo RAISE NOTICE.")
             self.commit() # Commit comunque la CALL se non ci sono stati altri errori
             return None
        except Exception as e:
            logger.error(f"Errore durante controllo/lettura frammentazione: {e}")
            self.rollback()
            return None

    def get_optimization_suggestions(self) -> Optional[str]:
        """Ottiene suggerimenti generali ottimizzazione."""
        query = "SELECT suggerimenti_ottimizzazione() AS suggestions"
        if self.execute_query(query):
            result = self.fetchone()
            return result.get('suggestions') if result else None
        return None

    # --- METODI PER FUNZIONALITÀ STORICHE AVANZATE (Script 11) ---

    def get_historical_periods(self) -> List[Dict]:
        """Recupera tutti i periodi storici."""
        query = "SELECT id, nome, anno_inizio, anno_fine, descrizione FROM periodo_storico ORDER BY anno_inizio"
        if self.execute_query(query):
            return self.fetchall()
        return []

    def get_historical_name(self, entity_type: str, entity_id: int, year: Optional[int] = None) -> Optional[Dict]:
        """Ottiene nome storico per entità in un anno."""
        effective_year = year if year is not None else datetime.now().year
        query = "SELECT * FROM get_nome_storico(%s, %s, %s)"
        if self.execute_query(query, (entity_type, entity_id, effective_year)):
            return self.fetchone()
        return None

    def register_historical_name(self, entity_type: str, entity_id: int, name: str, period_id: int, year_start: int, year_end: Optional[int] = None, notes: Optional[str] = None) -> bool:
        """Registra un nome storico per un'entità."""
        try:
            call_proc = "CALL registra_nome_storico(%s, %s, %s, %s, %s, %s, %s)"
            params = (entity_type, entity_id, name, period_id, year_start, year_end, notes)
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Registrato nome storico '{name}' per {entity_type} ID {entity_id}.")
                return True
            self.rollback()
            return False
        except psycopg2.Error as db_err:
             logger.error(f"Errore DB registrazione nome storico: {db_err}")
             self.rollback()
             return False
        except Exception as e:
            logger.error(f"Errore generico registrazione nome storico: {e}")
            self.rollback()
            return False

    def search_historical_documents(self, title: Optional[str] = None, doc_type: Optional[str] = None, period_id: Optional[int] = None, year_start: Optional[int] = None, year_end: Optional[int] = None, partita_id: Optional[int] = None) -> List[Dict]:
        """Ricerca documenti storici."""
        query = "SELECT * FROM ricerca_documenti_storici(%s, %s, %s, %s, %s, %s)"
        params = (title, doc_type, period_id, year_start, year_end, partita_id)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def get_property_genealogy(self, partita_id: int) -> List[Dict]:
        """Ricostruisce albero genealogico di una proprietà."""
        query = "SELECT * FROM albero_genealogico_proprieta(%s)"
        if self.execute_query(query, (partita_id,)):
            return self.fetchall()
        return []

    def get_cadastral_stats_by_period(self, comune: Optional[str] = None, year_start: int = 1900, year_end: Optional[int] = None) -> List[Dict]:
        """Ottiene statistiche catastali aggregate per anno e comune."""
        effective_year_end = year_end if year_end is not None else datetime.now().year
        query = "SELECT * FROM statistiche_catastali_periodo(%s, %s, %s)"
        params = (comune, year_start, effective_year_end)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def link_document_to_partita(self, document_id: int, partita_id: int, relevance: str = 'correlata', notes: Optional[str] = None) -> bool:
        """Collega un documento storico a una partita."""
        if relevance not in ['primaria', 'secondaria', 'correlata']:
            logger.error(f"Rilevanza non valida: {relevance}")
            return False
        query = """
            INSERT INTO documento_partita (documento_id, partita_id, rilevanza, note)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (documento_id, partita_id) DO UPDATE SET
                rilevanza = EXCLUDED.rilevanza,
                note = EXCLUDED.note
        """
        params = (document_id, partita_id, relevance, notes)
        try:
            if self.execute_query(query, params):
                self.commit()
                logger.info(f"Documento ID {document_id} collegato a Partita ID {partita_id}.")
                return True
            self.rollback()
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB nel collegare doc {document_id} a partita {partita_id}: {db_err}")
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore generico nel collegare doc {document_id} a partita {partita_id}: {e}")
            self.rollback()
            return False

    # --- METODI CRUD E UTILITY AGGIUNTIVI (Script 12) ---

    def update_immobile(self, immobile_id: int, **kwargs) -> bool:
        """Aggiorna dettagli immobile."""
        params = {
            'p_id': immobile_id, 'p_natura': kwargs.get('natura'),
            'p_numero_piani': kwargs.get('numero_piani'), 'p_numero_vani': kwargs.get('numero_vani'),
            'p_consistenza': kwargs.get('consistenza'), 'p_classificazione': kwargs.get('classificazione'),
            'p_localita_id': kwargs.get('localita_id')
        }
        call_proc = "CALL aggiorna_immobile(%(p_id)s, %(p_natura)s, %(p_numero_piani)s, %(p_numero_vani)s, %(p_consistenza)s, %(p_classificazione)s, %(p_localita_id)s)"
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Immobile ID {immobile_id} aggiornato.")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore aggiornamento immobile ID {immobile_id}: {e}")
            self.rollback()
            return False

    def delete_immobile(self, immobile_id: int) -> bool:
        """Elimina un immobile."""
        try:
            call_proc = "CALL elimina_immobile(%s)"
            if self.execute_query(call_proc, (immobile_id,)):
                self.commit()
                logger.info(f"Immobile ID {immobile_id} eliminato.")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore eliminazione immobile ID {immobile_id}: {e}")
            self.rollback()
            return False

    def search_immobili(self, partita_id: Optional[int] = None, comune_nome: Optional[str] = None, localita_id: Optional[int] = None, natura: Optional[str] = None, classificazione: Optional[str] = None) -> List[Dict]:
        """Ricerca immobili specifici."""
        query = "SELECT * FROM cerca_immobili(%s, %s, %s, %s, %s)"
        params = (partita_id, comune_nome, localita_id, natura, classificazione)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def update_variazione(self, variazione_id: int, **kwargs) -> bool:
        """Aggiorna dettagli variazione."""
        params = {
            'p_variazione_id': variazione_id, 'p_tipo': kwargs.get('tipo'),
            'p_data_variazione': kwargs.get('data_variazione'),
            'p_numero_riferimento': kwargs.get('numero_riferimento'),
            'p_nominativo_riferimento': kwargs.get('nominativo_riferimento')
        }
        call_proc = "CALL aggiorna_variazione(%(p_variazione_id)s, %(p_tipo)s, %(p_data_variazione)s, %(p_numero_riferimento)s, %(p_nominativo_riferimento)s)"
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Variazione ID {variazione_id} aggiornata.")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore aggiornamento variazione ID {variazione_id}: {e}")
            self.rollback()
            return False

    def delete_variazione(self, variazione_id: int, force: bool = False, restore_partita: bool = False) -> bool:
        """Elimina una variazione."""
        try:
            call_proc = "CALL elimina_variazione(%s, %s, %s)"
            if self.execute_query(call_proc, (variazione_id, force, restore_partita)):
                self.commit()
                logger.info(f"Variazione ID {variazione_id} eliminata (force={force}, restore={restore_partita}).")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore eliminazione variazione ID {variazione_id}: {e}")
            self.rollback()
            return False

    def search_variazioni(self, tipo: Optional[str] = None, data_inizio: Optional[date] = None, data_fine: Optional[date] = None, partita_origine_id: Optional[int] = None, partita_destinazione_id: Optional[int] = None, comune: Optional[str] = None) -> List[Dict]:
        """Ricerca variazioni con filtri."""
        query = "SELECT * FROM cerca_variazioni(%s, %s, %s, %s, %s, %s)"
        params = (tipo, data_inizio, data_fine, partita_origine_id, partita_destinazione_id, comune)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def insert_contratto(self, variazione_id: int, tipo: str, data_contratto: date, notaio: Optional[str] = None, repertorio: Optional[str] = None, note: Optional[str] = None) -> bool:
        """Inserisce un nuovo contratto."""
        try:
            call_proc = "CALL inserisci_contratto(%s, %s, %s, %s, %s, %s)"
            params = (variazione_id, tipo, data_contratto, notaio, repertorio, note)
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Contratto inserito per variazione ID {variazione_id}.")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore inserimento contratto per variazione ID {variazione_id}: {e}")
            self.rollback()
            return False

    def update_contratto(self, contratto_id: int, **kwargs) -> bool:
        """Aggiorna dettagli contratto."""
        params = {
            'p_id': contratto_id, 'p_tipo': kwargs.get('tipo'),
            'p_data_contratto': kwargs.get('data_contratto'), 'p_notaio': kwargs.get('notaio'),
            'p_repertorio': kwargs.get('repertorio'), 'p_note': kwargs.get('note')
        }
        call_proc = "CALL aggiorna_contratto(%(p_id)s, %(p_tipo)s, %(p_data_contratto)s, %(p_notaio)s, %(p_repertorio)s, %(p_note)s)"
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Contratto ID {contratto_id} aggiornato.")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore aggiornamento contratto ID {contratto_id}: {e}")
            self.rollback()
            return False

    def delete_contratto(self, contratto_id: int) -> bool:
        """Elimina un contratto."""
        try:
            call_proc = "CALL elimina_contratto(%s)"
            if self.execute_query(call_proc, (contratto_id,)):
                self.commit()
                logger.info(f"Contratto ID {contratto_id} eliminato.")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore eliminazione contratto ID {contratto_id}: {e}")
            self.rollback()
            return False

    def update_consultazione(self, consultazione_id: int, **kwargs) -> bool:
        """Aggiorna dettagli consultazione."""
        params = {
            'p_id': consultazione_id, 'p_data': kwargs.get('data'),
            'p_richiedente': kwargs.get('richiedente'), 'p_documento_identita': kwargs.get('documento_identita'),
            'p_motivazione': kwargs.get('motivazione'), 'p_materiale_consultato': kwargs.get('materiale_consultato'),
            'p_funzionario_autorizzante': kwargs.get('funzionario_autorizzante')
        }
        call_proc = "CALL aggiorna_consultazione(%(p_id)s, %(p_data)s, %(p_richiedente)s, %(p_documento_identita)s, %(p_motivazione)s, %(p_materiale_consultato)s, %(p_funzionario_autorizzante)s)"
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Consultazione ID {consultazione_id} aggiornata.")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore aggiornamento consultazione ID {consultazione_id}: {e}")
            self.rollback()
            return False

    def delete_consultazione(self, consultazione_id: int) -> bool:
        """Elimina una consultazione."""
        try:
            call_proc = "CALL elimina_consultazione(%s)"
            if self.execute_query(call_proc, (consultazione_id,)):
                self.commit()
                logger.info(f"Consultazione ID {consultazione_id} eliminata.")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore eliminazione consultazione ID {consultazione_id}: {e}")
            self.rollback()
            return False

    def search_consultazioni(self, data_inizio: Optional[date] = None, data_fine: Optional[date] = None, richiedente: Optional[str] = None, funzionario: Optional[str] = None) -> List[Dict]:
        """Ricerca consultazioni."""
        query = "SELECT * FROM cerca_consultazioni(%s, %s, %s, %s)"
        params = (data_inizio, data_fine, richiedente, funzionario)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def duplicate_partita(self, partita_id: int, nuovo_numero_partita: int, mantenere_possessori: bool = True, mantenere_immobili: bool = False) -> bool:
        """Duplica una partita."""
        try:
            call_proc = "CALL duplica_partita(%s, %s, %s, %s)"
            params = (partita_id, nuovo_numero_partita, mantenere_possessori, mantenere_immobili)
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Partita ID {partita_id} duplicata con nuovo numero {nuovo_numero_partita}.")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore duplicazione partita ID {partita_id}: {e}")
            self.rollback()
            return False

    def transfer_immobile(self, immobile_id: int, nuova_partita_id: int, registra_variazione: bool = False) -> bool:
        """Trasferisce un immobile a un'altra partita."""
        try:
            call_proc = "CALL trasferisci_immobile(%s, %s, %s)"
            params = (immobile_id, nuova_partita_id, registra_variazione)
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Immobile ID {immobile_id} trasferito alla partita ID {nuova_partita_id}.")
                return True
            self.rollback()
            return False
        except Exception as e:
            logger.error(f"Errore trasferimento immobile ID {immobile_id}: {e}")
            self.rollback()
            return False

    def export_partita_json(self, partita_id: int) -> Optional[str]:
        """Esporta dati partita in JSON."""
        query = "SELECT esporta_partita_json(%s) AS partita_json"
        if self.execute_query(query, (partita_id,)):
            result = self.fetchone()
            if result and 'partita_json' in result and result['partita_json']:
                 # La funzione SQL restituisce JSON, psycopg2 potrebbe averlo già parsato
                 dati_json = result['partita_json']
                 try:
                     # Riformatta per leggibilità
                     return json.dumps(dati_json, indent=4, ensure_ascii=False)
                 except TypeError as e:
                      logger.error(f"Errore serializzazione JSON per partita {partita_id}: {e}")
                      return str(dati_json) # Fallback
            else:
                 logger.warning(f"Nessun dato JSON restituito per partita ID {partita_id}.")
                 return None
        return None

    def export_possessore_json(self, possessore_id: int) -> Optional[str]:
        """Esporta dati possessore in JSON."""
        query = "SELECT esporta_possessore_json(%s) AS possessore_json"
        if self.execute_query(query, (possessore_id,)):
            result = self.fetchone()
            if result and 'possessore_json' in result and result['possessore_json']:
                 dati_json = result['possessore_json']
                 try:
                     return json.dumps(dati_json, indent=4, ensure_ascii=False)
                 except TypeError as e:
                      logger.error(f"Errore serializzazione JSON per possessore {possessore_id}: {e}")
                      return str(dati_json)
            else:
                  logger.warning(f"Nessun dato JSON restituito per possessore ID {possessore_id}.")
                  return None
        return None

    def get_report_comune(self, comune_nome: str) -> Optional[Dict]:
        """Genera report statistico per comune."""
        query = "SELECT * FROM genera_report_comune(%s)"
        if self.execute_query(query, (comune_nome,)):
            return self.fetchone() # La funzione restituisce max 1 riga
        return None

    # --- METODI AUDIT (Script 06) ---
    def get_audit_logs(self, limit: int = 20) -> List[Dict]:
         """Recupera gli ultimi N log di audit."""
         query = "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT %s"
         if self.execute_query(query, (limit,)):
              return self.fetchall()
         return []

    def search_audit_logs(self, utente_app: Optional[str]=None, azione: Optional[str]=None, tabella: Optional[str]=None, data_inizio: Optional[date]=None, data_fine: Optional[date]=None) -> List[Dict]:
         """Cerca nei log di audit con filtri."""
         query = "SELECT * FROM cerca_audit_log(%s, %s, %s, %s, %s)"
         params = (utente_app, azione, tabella, data_inizio, data_fine)
         if self.execute_query(query, params):
              return self.fetchall()
         return []

    def generate_audit_report(self, data_inizio: date, data_fine: date) -> Optional[str]:
         """Genera un report testuale di audit per un periodo."""
         query = "SELECT genera_report_audit(%s, %s) AS report"
         if self.execute_query(query, (data_inizio, data_fine)):
              result = self.fetchone()
              return result.get('report') if result else None
         return None


# --- Blocco Esecuzione Test (Rimosso - Usare python_example_modificato.py) ---
# if __name__ == "__main__":
#      # Codice di test rimosso
#      pass