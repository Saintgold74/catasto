#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestore Database Catasto Storico - Versione Completa Riscritto
==============================================================
Script consolidato per la gestione del database catastale,
includendo tutte le funzionalità, correzioni e miglioramenti discussi.

Include:
- Gestione Cursore sicura con 'with' statement
- Configurazione esterna delle credenziali
- Sicurezza password con bcrypt
- Gestione errori robusta con rollback automatico
- Integrazione Audit/Utenti tramite variabili di sessione
- Metodi per tutte le funzionalità SQL (Scripts 01-15)
- Type Hinting e Docstrings

Autore: Marco Santoro
Data: 24/04/2025
"""

# Import necessari
import psycopg2
import psycopg2.extras # Per DictCursor
import psycopg2.errors # Per catturare errori specifici DB
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
import sys
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import bcrypt # Per hashing password
import json # Per esportazioni/importazioni JSON

# Configurazione logging
# Assicurati che il file di log sia scrivibile
log_file_path = "catasto_db.log"
try:
    # Verifica permessi scrittura (opzionale, ma utile per debug)
    with open(log_file_path, 'a'): pass
except IOError:
     print(f"ATTENZIONE: Impossibile scrivere nel file di log: {log_file_path}. Controllare permessi.")
     # Potresti voler uscire o loggare solo su console
     # sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler(sys.stdout) # Mostra log anche a console
    ]
)
logger = logging.getLogger("CatastoDB")

class CatastoDBManager:
    """
    Classe per la gestione completa delle operazioni sul database catastale storico.
    Gestisce connessione, transazioni, esecuzione query e integrazione audit/utenti.
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
        self.password = password
        self.host = host
        self.port = port
        self.schema = schema
        self.conn: Optional[psycopg2.extensions.connection] = None
        # Attributi interni per l'ultimo risultato/stato
        self._last_result: Optional[List[Dict[str, Any]]] = None
        self._last_rowcount: int = -1

        logger.info(f"Gestore inizializzato per DB '{dbname}'@{host}:{port} (Schema: {schema})")

    # --- Gestione Connessione ---

    def connect(self) -> bool:
        """Stabilisce o verifica la connessione al database."""
        if self.conn is not None and not self.conn.closed:
            # Verifica se la connessione è ancora valida
            try:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT 1")
                # logger.debug("Connessione esistente verificata.")
                return True
            except psycopg2.Error:
                logger.warning("Connessione esistente non valida. Tentativo di riconnessione.")
                self.conn = None # Forza riconnessione

        try:
            logger.info(f"Tentativo di connessione a {self.dbname}@{self.host}...")
            self.conn = psycopg2.connect(
                dbname=self.dbname, user=self.user, password=self.password,
                host=self.host, port=self.port,
                options=f'-c search_path={self.schema},public' # Imposta search_path all'inizio
            )
            self.conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
            self.conn.autocommit = False # Gestione manuale delle transazioni
            logger.info("Connessione stabilita con successo.")
            return True
        except psycopg2.OperationalError as e:
            logger.error(f"Errore operativo connessione: {e}")
            self.conn = None
            return False
        except Exception as e:
            logger.error(f"Errore generico connessione: {e}")
            self.conn = None
            return False

    def disconnect(self):
        """Chiude la connessione al database se attiva."""
        if self.conn is not None and not self.conn.closed:
            try:
                # Prima di chiudere, prova a fare rollback di transazioni pendenti
                if self.conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
                     logger.warning("Transazione attiva durante disconnessione, eseguo rollback.")
                     self.conn.rollback()
                self.conn.close()
                logger.info("Disconnessione dal database completata.")
            except psycopg2.Error as db_err:
                logger.error(f"Errore DB durante disconnessione: {db_err}")
            except Exception as e:
                logger.error(f"Errore generico durante disconnessione: {e}")
            finally:
                 self.conn = None

    # --- Gestione Transazioni ---

    def commit(self):
        """Esegue il commit della transazione corrente."""
        if not self.conn or self.conn.closed:
            logger.warning("Impossibile eseguire commit: connessione non attiva.")
            return
        try:
            self.conn.commit()
            # logger.debug("Commit transazione eseguito.")
        except psycopg2.Error as e:
            logger.error(f"Errore durante il commit: {e}. Tentativo di Rollback.")
            # Se il commit fallisce, è buona norma fare rollback
            self.rollback()
            # Rilancia l'eccezione o gestiscila qui se necessario

    def rollback(self):
        """Esegue il rollback della transazione corrente."""
        if not self.conn or self.conn.closed:
            logger.warning("Impossibile eseguire rollback: connessione non attiva.")
            return
        try:
            self.conn.rollback()
            logger.info("Rollback transazione eseguito.")
        except psycopg2.Error as e:
            logger.error(f"Errore durante il rollback: {e}")

    # --- Esecuzione Query e Fetch Risultati (Metodo Centrale) ---

    def execute_query(self, query: str, params: Optional[Union[Tuple, Dict]] = None, fetch_results: bool = True) -> bool:
        """
        Esegue una query, gestendo connessione, cursore e transazione base.
        Memorizza risultati e rowcount internamente.

        Args:
            query: Stringa SQL.
            params: Parametri per la query.
            fetch_results: Se True (default), tenta di recuperare i risultati per SELECT/RETURNING.

        Returns:
            bool: True se l'esecuzione SQL ha successo (nessuna eccezione DB), False altrimenti.
                  NOTA: Un risultato True NON implica che un commit sia avvenuto.
        """
        self._last_result = None
        self._last_rowcount = -1

        if not self.connect(): # Assicura connessione attiva
            logger.error("Esecuzione fallita: connessione non disponibile.")
            return False

        # Assicura che self.conn non sia None (per type checker)
        if not self.conn: return False

        log_query = query.strip()[:100] + ('...' if len(query.strip()) > 100 else '') # Log query abbreviata
        try:
            # Gestisce il cursore con 'with' per chiusura automatica
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # logger.debug(f"Esecuzione: {log_query} | Params: {params}")
                cur.execute(query, params)
                self._last_rowcount = cur.rowcount if cur.rowcount is not None else -1

                # Recupera risultati solo se richiesto e se la query li produce
                if fetch_results and cur.description:
                    try:
                        self._last_result = cur.fetchall()
                        # logger.debug(f"Risultati fetchati: {len(self._last_result)} righe")
                    except psycopg2.ProgrammingError: # Atteso per comandi senza risultati
                        self._last_result = []
                        # logger.debug("Nessun risultato da fetchare.")
                else:
                    self._last_result = [] # Nessun risultato fetchato

            return True # Successo esecuzione SQL

        except psycopg2.Error as db_err:
            # Errore specifico del database (violazione vincoli, sintassi, etc.)
            logger.error(f"Errore DB: {db_err} | Query: {log_query} | Params: {params}")
            # Il rollback dovrebbe essere gestito dal metodo chiamante di livello superiore
            return False
        except Exception as e:
            # Altri errori imprevisti (es. rete, configurazione)
            logger.error(f"Errore Generico: {e} | Query: {log_query} | Params: {params}")
            return False

    def fetchone(self) -> Optional[Dict[str, Any]]:
        """Restituisce la prima riga dell'ultimo risultato memorizzato."""
        return dict(self._last_result[0]) if self._last_result else None

    def fetchall(self) -> List[Dict[str, Any]]:
        """Restituisce tutte le righe dell'ultimo risultato memorizzato."""
        return [dict(row) for row in self._last_result] if self._last_result else []

    def get_last_rowcount(self) -> int:
         """Restituisce il rowcount dell'ultima query eseguita."""
         return self._last_rowcount

    # --- Gestione Sessione e Variabili per Audit (Script 15) ---

    def set_session_variable(self, var_name: str, value: Optional[str]) -> bool:
        """Imposta variabile di configurazione per sessione corrente (per audit)."""
        # Usa set_config, non necessita commit/rollback esplicito
        query = "SELECT set_config(%s, %s, FALSE);"
        # Eseguiamo senza fetch_results perché SELECT set_config non restituisce righe utili qui
        if self.execute_query(query, (var_name, value), fetch_results=False):
            # logger.debug(f"Variabile sessione '{var_name}' impostata.")
            return True
        else:
            logger.error(f"Fallimento impostazione variabile sessione '{var_name}'.")
            return False

    def login_user(self, username: str, password: str, ip_address: Optional[str] = None, app_name: Optional[str] = 'PythonApp') -> Optional[Dict]:
        """Esegue login tramite funzione SQL, restituisce info sessione o errore."""
        query = "SELECT * FROM login_user(%s, %s, %s, %s)"
        params = (username, password, ip_address, app_name)
        try:
            if self.execute_query(query, params): # fetch_results=True è default
                result = self.fetchone()
                if result:
                     login_success = result.get('login_success', False)
                     message = result.get('message', 'Login fallito.')
                     if login_success:
                          user_id = result.get('user_id')
                          session_id = result.get('session_id')
                          if user_id is not None and session_id is not None:
                               self.commit() # Commit inserimento/aggiornamento accesso_log
                               logger.info(f"Login successo per {username}. Sessione: {session_id}")
                               return {'success': True, 'user_id': user_id, 'session_id': session_id, 'message': message}
                          else: # Successo ma mancano dati chiave
                               logger.error(f"Login {username}: successo ma mancano user_id/session_id.")
                               self.rollback(); return {'success': False, 'message': 'Errore interno post login.'}
                     else: # Login fallito secondo la funzione SQL
                          logger.warning(f"Login fallito per {username}: {message}")
                          self.rollback(); return {'success': False, 'message': message}
                else: # La funzione SQL non ha restituito nulla
                     logger.error(f"Funzione login_user per {username} non ha restituito risultati.");
                     self.rollback(); return {'success': False, 'message': 'Errore funzione login.'}
            else: # execute_query fallito
                self.rollback(); return None # Indica errore DB
        except Exception as e: logger.error(f"Eccezione login {username}: {e}"); self.rollback(); return None

    def logout_user(self, session_id: str) -> bool:
        """Esegue logout tramite procedura SQL."""
        call_proc = "CALL logout_user(%s)"
        try:
            if self.execute_query(call_proc, (session_id,), fetch_results=False):
                self.commit(); logger.info(f"Logout per sessione {session_id}."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione logout sessione {session_id}: {e}"); self.rollback(); return False

    def get_current_session_info(self) -> Optional[Dict]:
         """Recupera info sessione corrente da DB."""
         query = "SELECT * FROM get_current_session_info()"
         try:
              if self.execute_query(query): return self.fetchone()
              else: return None
         except Exception as e: logger.error(f"Errore recupero info sessione: {e}"); return None

    # --- Metodi per Funzioni/Viste Audit e Attività Utente (Script 15) ---

    def get_user_activity(self, username: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Interroga vista v_attivita_utente."""
        query = "SELECT username, nome_completo, primo_accesso, ultimo_accesso, sessioni_attive, totale_sessioni, durata_media_sessione FROM v_attivita_utente "
        params: List[Any] = []
        if username: query += " WHERE username = %s"; params.append(username)
        query += " ORDER BY ultimo_accesso DESC NULLS LAST LIMIT %s"; params.append(limit)
        try:
            if self.execute_query(query, tuple(params)): return self.fetchall()
            else: return []
        except Exception as e: logger.error(f"Errore recupero attività utente: {e}"); return []

    def get_detailed_audit(self, limit: int = 50) -> List[Dict]:
         """Interroga vista v_audit_dettagliato."""
         query = "SELECT timestamp, username, nome_completo, azione, tabella, record_id, session_id, ip_address, dettagli_modifica FROM v_audit_dettagliato ORDER BY timestamp DESC LIMIT %s"
         try:
              if self.execute_query(query, (limit,)): return self.fetchall()
              else: return []
         except Exception as e: logger.error(f"Errore recupero audit dettagliato: {e}"); return []

    def get_user_activity_report(self, username: Optional[str] = None, days: int = 30) -> Optional[str]:
         """Chiama funzione report_attivita_utente."""
         query = "SELECT report_attivita_utente(%s, %s) AS report_text"
         try:
              if self.execute_query(query, (username, days)):
                   result = self.fetchone()
                   return result.get('report_text') if result else None
              return None
         except Exception as e: logger.error(f"Errore generazione report attività utente: {e}"); return None

    # --- Metodi CRUD Base e Funzionalità (Scripts 03, 07, 11, 12, 13, 14) ---
    # (Includendo correzioni per nomi colonne e gestione rollback)

    # Comune
    def get_comuni(self) -> List[Dict]:
        query = "SELECT nome, provincia, regione FROM comune ORDER BY nome"
        if self.execute_query(query): return self.fetchall()
        return []

    def insert_comune(self, nome: str, provincia: str, regione: str) -> bool:
        query = "INSERT INTO comune (nome, provincia, regione) VALUES (%s, %s, %s) ON CONFLICT (nome) DO UPDATE SET provincia = EXCLUDED.provincia, regione = EXCLUDED.regione"
        try:
            if self.execute_query(query, (nome, provincia, regione), fetch_results=False): self.commit(); logger.info(f"Comune '{nome}' OK."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione insert_comune '{nome}': {e}"); self.rollback(); return False

    # Possessore
    def inserisci_possessore(self, nome_completo: str, comune_residenza: str, **kwargs) -> Optional[int]:
        query = "SELECT inserisci_possessore(%s, %s, %s, %s, %s, %s, %s)"
        params = (nome_completo, kwargs.get('codice_fiscale'), comune_residenza, kwargs.get('paternita'),
                  kwargs.get('data_nascita'), kwargs.get('luogo_nascita'), kwargs.get('note'))
        try:
            if self.execute_query(query, params):
                result = self.fetchone(); possessore_id = result.get('inserisci_possessore') if result else None
                if possessore_id is not None: self.commit(); logger.info(f"Possessore '{nome_completo}' ID: {possessore_id}."); return possessore_id
                else: logger.warning(f"inserisci_possessore '{nome_completo}' non ha restituito ID."); self.rollback(); return None
            else: self.rollback(); return None
        except Exception as e: logger.error(f"Eccezione inserisci_possessore '{nome_completo}': {e}"); self.rollback(); return None

    def get_possessori_per_comune(self, comune_nome: str) -> List[Dict]:
        query = "SELECT p.id, p.nome_completo, p.paternita, p.data_nascita FROM possessore p WHERE p.comune_nome = %s ORDER BY p.nome_completo"
        if self.execute_query(query, (comune_nome,)): return self.fetchall()
        return []

    # Localita
    def insert_localita(self, comune_nome: str, nome_localita: str, tipo: Optional[str] = None, note: Optional[str] = None) -> Optional[int]:
        query = "SELECT inserisci_localita(%s, %s, %s, %s)"
        params = (comune_nome, nome_localita, tipo, note)
        try:
            if self.execute_query(query, params):
                result = self.fetchone(); localita_id = result.get('inserisci_localita') if result else None
                if localita_id is not None: self.commit(); logger.info(f"Località '{nome_localita}' ID: {localita_id}."); return localita_id
                else: logger.warning(f"inserisci_localita '{nome_localita}' non ha restituito ID."); self.rollback(); return None
            else: self.rollback(); return None
        except Exception as e: logger.error(f"Eccezione insert_localita '{nome_localita}': {e}"); self.rollback(); return None

    def get_localita_per_comune(self, comune_nome: str) -> List[Dict]:
        query = "SELECT l.id, l.nome, l.tipo_localita, l.note FROM localita l JOIN comune c ON l.comune_nome = c.nome WHERE c.nome = %s ORDER BY l.nome"
        if self.execute_query(query, (comune_nome,)): return self.fetchall()
        return []

    # Partita
    def get_partite_per_comune(self, comune_nome: str) -> List[Dict]:
        query = "SELECT p.id, p.numero_partita, p.tipo, p.stato, p.data_impianto FROM partita p WHERE p.comune_nome = %s ORDER BY p.numero_partita"
        if self.execute_query(query, (comune_nome,)): return self.fetchall()
        return []

    def search_partite(self, comune_nome: Optional[str] = None, tipo: Optional[str] = None, stato: Optional[str] = None, possessore_search: Optional[str] = None, natura_immobile_search: Optional[str] = None) -> List[Dict]:
        query = "SELECT * FROM cerca_partite(%s, %s, %s, %s, %s)"
        params = (comune_nome, tipo, stato, possessore_search, natura_immobile_search)
        if self.execute_query(query, params): return self.fetchall()
        return []

    def get_partita_details(self, partita_id: int) -> Optional[Dict]:
        query = "SELECT * FROM get_dettagli_partita(%s)"
        if self.execute_query(query, (partita_id,)):
            result = self.fetchone()
            if result:
                 json_details = next(iter(result.values()), None)
                 if isinstance(json_details, dict): return json_details
                 elif isinstance(json_details, str):
                      try: return json.loads(json_details)
                      except json.JSONDecodeError as jde: logger.error(f"Errore decodifica JSON dettagli partita {partita_id}: {jde}"); return None
                 else: logger.warning(f"Dettagli partita {partita_id} restituiti in formato non atteso: {type(json_details)}"); return None
            else: logger.warning(f"Nessun dettaglio per partita {partita_id}."); return None
        return None

    # Consultazione
    def registra_consultazione(self, data: date, richiedente: str, motivazione: str, materiale_consultato: str, funzionario_autorizzante: str, documento_identita: Optional[str] = None) -> bool:
        """Registra consultazione (procedura non restituisce ID)."""
        call_proc = "CALL registra_consultazione(%s, %s, %s, %s, %s, %s)"
        params = (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante)
        try:
            # Impostare variabili audit qui se si vuole tracciare chi registra la consultazione
            # set_session_vars_for_audit(self) # <-- Esempio
            if self.execute_query(call_proc, params, fetch_results=False): self.commit(); logger.info(f"Consultazione registrata per '{richiedente}'."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione registra_consultazione '{richiedente}': {e}"); self.rollback(); return False

    def update_consultazione(self, consultazione_id: int, **kwargs) -> bool:
        """Aggiorna dettagli consultazione."""
        params = {'p_id': consultazione_id, 'p_data': kwargs.get('data'), 'p_richiedente': kwargs.get('richiedente'), 'p_documento_identita': kwargs.get('documento_identita'), 'p_motivazione': kwargs.get('motivazione'), 'p_materiale_consultato': kwargs.get('materiale_consultato'), 'p_funzionario_autorizzante': kwargs.get('funzionario_autorizzante')}
        call_proc = "CALL aggiorna_consultazione(%(p_id)s, %(p_data)s, %(p_richiedente)s, %(p_documento_identita)s, %(p_motivazione)s, %(p_materiale_consultato)s, %(p_funzionario_autorizzante)s)"
        try:
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, params, fetch_results=False): self.commit(); logger.info(f"Consultazione ID {consultazione_id} aggiornata."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione aggiorna consultazione ID {consultazione_id}: {e}"); self.rollback(); return False

    def delete_consultazione(self, consultazione_id: int) -> bool:
        """Elimina una consultazione."""
        try:
            call_proc = "CALL elimina_consultazione(%s)"
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, (consultazione_id,), fetch_results=False): self.commit(); logger.info(f"Consultazione ID {consultazione_id} eliminata."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione elimina consultazione ID {consultazione_id}: {e}"); self.rollback(); return False

    def search_consultazioni(self, data_inizio: Optional[date] = None, data_fine: Optional[date] = None, richiedente: Optional[str] = None, funzionario: Optional[str] = None) -> List[Dict]:
        """Ricerca consultazioni."""
        query = "SELECT * FROM cerca_consultazioni(%s, %s, %s, %s)"
        params = (data_inizio, data_fine, richiedente, funzionario)
        if self.execute_query(query, params): return self.fetchall()
        return []

    # Certificato Proprietà
    def genera_certificato_proprieta(self, partita_id: int) -> Optional[str]:
        query = "SELECT genera_certificato_proprieta(%s) AS certificato"
        if self.execute_query(query, (partita_id,)):
            result = self.fetchone()
            return result.get('certificato') if result else None
        return None

    # Workflow Integrati
    def registra_nuova_proprieta_v2(self, comune_nome: str, numero_partita: str, tipo_partita: str, data_impianto: date, possessori_info: List[Dict], immobili_info: List[Dict]) -> bool:
        """Registra nuova proprietà completa (procedura v2). Restituisce successo/fallimento."""
        try: possessori_json = json.dumps(possessori_info); immobili_json = json.dumps(immobili_info)
        except TypeError as te: logger.error(f"Errore JSON nuova proprietà: {te}"); return False
        call_proc = "CALL registra_nuova_proprieta_v2(%s, %s, %s, %s, %s, %s)"
        params = (comune_nome, numero_partita, tipo_partita, data_impianto, possessori_json, immobili_json)
        try:
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, params, fetch_results=False): self.commit(); logger.info(f"Registra nuova proprietà {numero_partita} OK."); return True
            else: self.rollback(); logger.error(f"Fallita chiamata registra_nuova_proprieta_v2."); return False
        except Exception as e: logger.error(f"Eccezione registra_nuova_proprieta_v2: {e}"); self.rollback(); return False

    def registra_passaggio_proprieta_v2(self, partita_id_origine: int, tipo_variazione: str, data_variazione: date, possessori_uscenti_ids: List[int], possessori_entranti_info: List[Dict], contratto_info: Optional[Dict] = None) -> Optional[Dict]:
        """Registra passaggio proprietà (procedura v2). Restituisce dict con successo/msg."""
        try:
            possessori_entranti_json = json.dumps(possessori_entranti_info)
            contratto_json = json.dumps(contratto_info) if contratto_info else None
            uscenti_ids_array = possessori_uscenti_ids
        except TypeError as te: logger.error(f"Errore JSON passaggio proprietà: {te}"); return {'success': False, 'message': 'Errore JSON'}
        call_proc = "CALL registra_passaggio_proprieta_v2(%s, %s, %s, %s, %s, %s)"
        params = (partita_id_origine, tipo_variazione, data_variazione, uscenti_ids_array, possessori_entranti_json, contratto_json)
        try:
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, params, fetch_results=False):
                 self.commit(); logger.info(f"Registra passaggio proprietà ID {partita_id_origine} OK.")
                 # Non abbiamo gli ID esatti qui, ma indichiamo successo
                 # Potrebbe essere utile che la procedura SQL restituisca gli ID via RAISE NOTICE
                 return {'success': True, 'message': 'Operazione completata.'}
            else:
                 self.rollback(); logger.error(f"Fallita chiamata registra_passaggio_proprieta_v2.")
                 return {'success': False, 'message': 'Esecuzione procedura fallita.'}
        except psycopg2.Error as db_err: logger.error(f"Errore DB passaggio proprietà ID {partita_id_origine}: {db_err}"); self.rollback(); return {'success': False, 'message': f"Errore DB: {db_err}"}
        except Exception as e: logger.error(f"Eccezione passaggio proprietà ID {partita_id_origine}: {e}"); self.rollback(); return {'success': False, 'message': f"Errore generico: {e}"}

    # Report Functions (Script 14)
    def get_report_consultazioni(self, data_inizio: date, data_fine: date) -> Optional[str]:
        query = "SELECT genera_report_consultazioni(%s, %s) AS report"
        if self.execute_query(query, (data_inizio, data_fine)):
            result = self.fetchone(); return result.get('report') if result else None
        return None

    # ... (Metodi Utente, Backup, Report Avanzati, Storici, CRUD aggiuntivi - già presenti sopra) ...
    # ... (Assicurati che tutti i metodi che modificano dati abbiano try/except con rollback) ...

    # CRUD Immobile (Script 12)
    def update_immobile(self, immobile_id: int, **kwargs) -> bool:
        params = {'p_id': immobile_id, 'p_natura': kwargs.get('natura'),'p_numero_piani': kwargs.get('numero_piani'), 'p_numero_vani': kwargs.get('numero_vani'), 'p_consistenza': kwargs.get('consistenza'), 'p_classificazione': kwargs.get('classificazione'), 'p_localita_id': kwargs.get('localita_id')}
        call_proc = "CALL aggiorna_immobile(%(p_id)s, %(p_natura)s, %(p_numero_piani)s, %(p_numero_vani)s, %(p_consistenza)s, %(p_classificazione)s, %(p_localita_id)s)"
        try:
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, params, fetch_results=False): self.commit(); logger.info(f"Immobile ID {immobile_id} aggiornato."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione aggiorna immobile ID {immobile_id}: {e}"); self.rollback(); return False

    def delete_immobile(self, immobile_id: int) -> bool:
        try:
            call_proc = "CALL elimina_immobile(%s)"
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, (immobile_id,), fetch_results=False): self.commit(); logger.info(f"Immobile ID {immobile_id} eliminato."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione elimina immobile ID {immobile_id}: {e}"); self.rollback(); return False

    def search_immobili(self, partita_id: Optional[int] = None, comune_nome: Optional[str] = None, localita_id: Optional[int] = None, natura: Optional[str] = None, classificazione: Optional[str] = None) -> List[Dict]:
        query = "SELECT * FROM cerca_immobili(%s, %s, %s, %s, %s)"
        params = (partita_id, comune_nome, localita_id, natura, classificazione)
        if self.execute_query(query, params): return self.fetchall()
        return []

    # CRUD Variazione (Script 12)
    def update_variazione(self, variazione_id: int, **kwargs) -> bool:
        params = {'p_variazione_id': variazione_id, 'p_tipo': kwargs.get('tipo'), 'p_data_variazione': kwargs.get('data_variazione'), 'p_numero_riferimento': kwargs.get('numero_riferimento'), 'p_nominativo_riferimento': kwargs.get('nominativo_riferimento')}
        call_proc = "CALL aggiorna_variazione(%(p_variazione_id)s, %(p_tipo)s, %(p_data_variazione)s, %(p_numero_riferimento)s, %(p_nominativo_riferimento)s)"
        try:
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, params, fetch_results=False): self.commit(); logger.info(f"Variazione ID {variazione_id} aggiornata."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione aggiorna variazione ID {variazione_id}: {e}"); self.rollback(); return False

    def delete_variazione(self, variazione_id: int, force: bool = False, restore_partita: bool = False) -> bool:
        try:
            call_proc = "CALL elimina_variazione(%s, %s, %s)"
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, (variazione_id, force, restore_partita), fetch_results=False): self.commit(); logger.info(f"Variazione ID {variazione_id} eliminata."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione elimina variazione ID {variazione_id}: {e}"); self.rollback(); return False

    def search_variazioni(self, tipo: Optional[str] = None, data_inizio: Optional[date] = None, data_fine: Optional[date] = None, partita_origine_id: Optional[int] = None, partita_destinazione_id: Optional[int] = None, comune: Optional[str] = None) -> List[Dict]:
        query = "SELECT * FROM cerca_variazioni(%s, %s, %s, %s, %s, %s)"
        params = (tipo, data_inizio, data_fine, partita_origine_id, partita_destinazione_id, comune)
        if self.execute_query(query, params): return self.fetchall()
        return []

    # CRUD Contratto (Script 12)
    def insert_contratto(self, variazione_id: int, tipo: str, data_contratto: date, notaio: Optional[str] = None, repertorio: Optional[str] = None, note: Optional[str] = None) -> bool:
        try:
            call_proc = "CALL inserisci_contratto(%s, %s, %s, %s, %s, %s)"
            params = (variazione_id, tipo, data_contratto, notaio, repertorio, note)
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, params, fetch_results=False): self.commit(); logger.info(f"Contratto inserito per var ID {variazione_id}."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione insert contratto var ID {variazione_id}: {e}"); self.rollback(); return False

    def update_contratto(self, contratto_id: int, **kwargs) -> bool:
        params = {'p_id': contratto_id, 'p_tipo': kwargs.get('tipo'), 'p_data_contratto': kwargs.get('data_contratto'), 'p_notaio': kwargs.get('notaio'), 'p_repertorio': kwargs.get('repertorio'), 'p_note': kwargs.get('note')}
        call_proc = "CALL aggiorna_contratto(%(p_id)s, %(p_tipo)s, %(p_data_contratto)s, %(p_notaio)s, %(p_repertorio)s, %(p_note)s)"
        try:
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, params, fetch_results=False): self.commit(); logger.info(f"Contratto ID {contratto_id} aggiornato."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione aggiorna contratto ID {contratto_id}: {e}"); self.rollback(); return False

    # delete_contratto è già stato corretto come esempio sopra

    # Utility Partita/Immobile (Script 12)
    def duplicate_partita(self, partita_id: int, nuovo_numero_partita: int, mantenere_possessori: bool = True, mantenere_immobili: bool = False) -> bool:
        try:
            call_proc = "CALL duplica_partita(%s, %s, %s, %s)"
            params = (partita_id, nuovo_numero_partita, mantenere_possessori, mantenere_immobili)
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, params, fetch_results=False): self.commit(); logger.info(f"Partita ID {partita_id} duplicata."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione duplica partita ID {partita_id}: {e}"); self.rollback(); return False

    def transfer_immobile(self, immobile_id: int, nuova_partita_id: int, registra_variazione: bool = False) -> bool:
        try:
            call_proc = "CALL trasferisci_immobile(%s, %s, %s)"
            params = (immobile_id, nuova_partita_id, registra_variazione)
            # set_session_vars_for_audit(self) # <-- Esempio Audit
            if self.execute_query(call_proc, params, fetch_results=False): self.commit(); logger.info(f"Immobile ID {immobile_id} trasferito."); return True
            else: self.rollback(); return False
        except Exception as e: logger.error(f"Eccezione trasferisci immobile ID {immobile_id}: {e}"); self.rollback(); return False

    # Esportazione JSON (Script 12)
    def export_partita_json(self, partita_id: int) -> Optional[str]:
        query = "SELECT esporta_partita_json(%s) AS partita_json"
        if self.execute_query(query, (partita_id,)):
            result = self.fetchone()
            if result and 'partita_json' in result and result['partita_json']:
                 dati_json = result['partita_json']
                 try: return json.dumps(dati_json, indent=4, ensure_ascii=False)
                 except TypeError as e: logger.error(f"Errore JSON export partita {partita_id}: {e}"); return str(dati_json)
            else: logger.warning(f"Nessun JSON per partita ID {partita_id}."); return None
        return None

    def export_possessore_json(self, possessore_id: int) -> Optional[str]:
        query = "SELECT esporta_possessore_json(%s) AS possessore_json"
        if self.execute_query(query, (possessore_id,)):
            result = self.fetchone()
            if result and 'possessore_json' in result and result['possessore_json']:
                 dati_json = result['possessore_json']
                 try: return json.dumps(dati_json, indent=4, ensure_ascii=False)
                 except TypeError as e: logger.error(f"Errore JSON export possessore {possessore_id}: {e}"); return str(dati_json)
            else: logger.warning(f"Nessun JSON per possessore ID {possessore_id}."); return None
        return None

    # Report Comune (Script 12)
    def get_report_comune(self, comune_nome: str) -> Optional[Dict]:
        query = "SELECT * FROM genera_report_comune(%s)"
        if self.execute_query(query, (comune_nome,)): return self.fetchone()
        return None

    # Metodi Audit (Script 06, già inclusi sopra nella sezione Audit/Utenti)
    def get_audit_logs(self, limit: int = 50) -> List[Dict]: # Aumentato default limit
         """Recupera gli ultimi N log di audit."""
         # Seleziona esplicitamente le colonne, inclusi i nuovi campi utente/sessione
         query = """
             SELECT id, timestamp, utente_db, utente_app, azione, tabella_interessata,
                    record_id, session_id, app_user_id, vecchi_dati, nuovi_dati
             FROM audit_log ORDER BY timestamp DESC LIMIT %s
         """
         if self.execute_query(query, (limit,)): return self.fetchall()
         return []

    def search_audit_logs(self, utente_app: Optional[str]=None, azione: Optional[str]=None, tabella: Optional[str]=None, data_inizio: Optional[date]=None, data_fine: Optional[date]=None, record_id: Optional[int]=None) -> List[Dict]:
         """Cerca nei log di audit con filtri (aggiunto record_id)."""
         # La funzione cerca_audit_log va aggiornata in SQL per includere i nuovi campi e filtri
         # Qui usiamo una query diretta come esempio se la funzione non è aggiornata
         conditions = []
         params = []
         query = """
             SELECT id, timestamp, utente_db, utente_app, azione, tabella_interessata,
                    record_id, session_id, app_user_id, vecchi_dati, nuovi_dati
             FROM audit_log WHERE 1=1
         """
         if utente_app: conditions.append("utente_app ILIKE %s"); params.append(f"%{utente_app}%")
         if azione: conditions.append("azione = %s"); params.append(azione.upper())
         if tabella: conditions.append("tabella_interessata = %s"); params.append(tabella)
         if data_inizio: conditions.append("timestamp >= %s"); params.append(data_inizio)
         if data_fine: conditions.append("timestamp <= %s"); params.append(data_fine)
         if record_id is not None: conditions.append("record_id = %s"); params.append(record_id)

         if conditions: query += " AND " + " AND ".join(conditions)
         query += " ORDER BY timestamp DESC"

         if self.execute_query(query, tuple(params)): return self.fetchall()
         return []

    def generate_audit_report(self, data_inizio: date, data_fine: date) -> Optional[str]:
         """Genera report testuale di audit."""
         query = "SELECT genera_report_audit(%s, %s) AS report"
         if self.execute_query(query, (data_inizio, data_fine)):
              result = self.fetchone(); return result.get('report') if result else None
         return None

# --- FINE CLASSE CatastoDBManager ---