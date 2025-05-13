# core/services/utenti_service.py
import bcrypt
import logging
from uuid import uuid4
from datetime import datetime
#import logging
#from typing import Optional, Dict, Any, List, Union # Assicurati che Dict, Any, List, Union siano qui se usati
# ... altri import (bcrypt, uuid4, datetime, .audit_service, psycopg2.extensions)
from typing import Union, Optional, List, Dict, Any # Assicurati che tutti i tipi usati siano importati
import psycopg2.extensions # Per ISOLATION_LEVEL_AUTOCOMMIT

# Importa il servizio di audit
from .audit_service import record_audit

logger = logging.getLogger("CatastoAppLogger.UtentiService")

# --- Funzioni di Hashing Password ---
def hash_password(plain_password: str) -> bytes:
    """Genera un hash sicuro per la password fornita."""
    if not plain_password:
        raise ValueError("La password non può essere vuota.")
    password_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password

def verify_password(plain_password: str, hashed_password_from_db: Union[str, bytes]) -> bool:
    """
    Verifica una password in chiaro rispetto a un hash memorizzato.
    L'hash dal DB potrebbe essere stringa (se encodato in latin-1/hex) o bytes.
    """
    if not plain_password or not hashed_password_from_db:
        return False
        
    password_bytes = plain_password.encode('utf-8')
    
    if isinstance(hashed_password_from_db, str):
        # Prova a decodificare da 'latin-1' se è una stringa come memorizzata da bcrypt in alcuni DB
        # o se è stata precedentemente encodata così per il salvataggio.
        try:
            hashed_password_bytes = hashed_password_from_db.encode('latin-1')
        except UnicodeEncodeError:
            logger.error("Impossibile encodare l'hash della password (stringa) in bytes con latin-1.")
            return False # O gestisci diversamente se usi un altro encoding per la stringa hash
    elif isinstance(hashed_password_from_db, bytes):
        hashed_password_bytes = hashed_password_from_db
    else:
        logger.error(f"Formato hash password non valido: {type(hashed_password_from_db)}")
        return False
        
    try:
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)
    except ValueError as ve: # Ad es. se l'hash non è valido per bcrypt
        logger.warning(f"Errore durante la verifica della password (possibile hash non valido): {ve}")
        return False
    except Exception as e:
        logger.error(f"Errore imprevisto durante bcrypt.checkpw: {e}")
        return False

# --- Servizi Utente ---
def register_user_service(db_manager, username: str, plain_password: str, email: str, role_id: int, 
                          nome_completo: str, client_ip_address: Optional[str] = None, 
                          created_by_user_id: Optional[int] = None):
    """
    Registra un nuovo utente nel sistema.
    'created_by_user_id' è l'ID dell'utente che esegue la creazione (es. admin),
    o None per self-registration.
    """
    logger.info(f"Tentativo di registrazione per l'utente: {username}")

    # Prepara i parametri per l'audit in caso di fallimento iniziale
    # Per la registrazione self-service, current_user_id potrebbe essere None
    audit_user_for_fail = created_by_user_id 

    try:
        # 1. Controlla se l'username o l'email esistono già
        check_query = "SELECT id FROM utenti WHERE username = %s OR email = %s"
        existing_user = db_manager.execute_query(check_query, (username, email), fetch_one=True)
        
        if existing_user:
            error_msg = f"Username '{username}' o email '{email}' già esistente."
            logger.warning(error_msg)
            # Non è necessario rollback qui se la transazione è già fallita o se questa è la prima query
            # e non ci sono modifiche. Ma per sicurezza, se si usa READ_COMMITTED:
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                 db_manager.rollback()
            record_audit(db_manager, audit_user_for_fail, "REGISTER_USER_FAIL", 
                         error_msg, "utenti", session_id=None, # session_id non ancora creato
                         client_ip_address=client_ip_address, success=False)
            raise ValueError(error_msg)

        # 2. Hash della password
        hashed_pw_bytes = hash_password(plain_password)
        # Memorizza l'hash come stringa decodificata (es. latin-1) se il campo DB è VARCHAR,
        # o mantienilo come bytes se il campo DB è BYTEA. Assumiamo VARCHAR per ora.
        hashed_pw_str_for_db = hashed_pw_bytes.decode('latin-1') # O un altro encoding se necessario

        # 3. Inserisci il nuovo utente
        # Assicurati che la query e i parametri corrispondano alla tua tabella 'utenti'
        # inclusi 'nome_completo', 'is_active' e i campi timestamp corretti
        insert_query = """
            INSERT INTO utenti (username, password_hash, email, role_id, nome_completo, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), NOW()) RETURNING id
        """
        params = (username, hashed_pw_str_for_db, email, role_id, nome_completo)
        
        user_record = db_manager.execute_query(insert_query, params, fetch_one=True)
        
        if user_record and user_record['id']:
            user_id = user_record['id']
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.commit()
            logger.info(f"Utente '{username}' (ID: {user_id}) registrato con successo.")
            
            audit_user_for_success = created_by_user_id if created_by_user_id is not None else user_id
            record_audit(db_manager, audit_user_for_success, "REGISTER_USER_SUCCESS", 
                         f"Utente {username} (ID: {user_id}) registrato.", "utenti", user_id,
                         session_id=None, client_ip_address=client_ip_address, success=True)
            return user_id
        else:
            # Questo caso (nessun ID ritornato dopo INSERT RETURNING id) dovrebbe essere raro se la query è corretta
            logger.error(f"Registrazione utente '{username}' fallita dopo l'inserimento (nessun ID ritornato).")
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.rollback()
            record_audit(db_manager, audit_user_for_fail, "REGISTER_USER_FAIL", 
                         f"Registrazione utente {username} fallita (nessun ID ritornato).", "utenti",
                         session_id=None, client_ip_address=client_ip_address, success=False)
            return None
            
    except ValueError as ve: # Cattura il ValueError sollevato sopra se l'utente esiste già
        # Il logger e il rollback sono già stati gestiti prima di sollevare ValueError
        raise # Rilancia per notificare il chiamante in main_app.py
    except Exception as e:
        logger.error(f"Errore critico durante la registrazione dell'utente '{username}': {e}", exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback() # Assicura rollback per qualsiasi altra eccezione
        record_audit(db_manager, audit_user_for_fail, "REGISTER_USER_FAIL", 
                     f"Errore critico registrazione utente {username}: {str(e)[:200]}", "utenti",
                     session_id=None, client_ip_address=client_ip_address, success=False)
        raise # Rilancia per notificare il chiamante in main_app.py

def login_user_service(db_manager, username: str, plain_password: str, client_ip_address: Optional[str] = None) -> tuple[Optional[int], Optional[int], Optional[str], str]:
    """
    Autentica un utente e gestisce la sessione.
    Restituisce (user_id, role_id, session_id, messaggio).
    """
    logger.info(f"Tentativo di login per l'utente: {username}")
    query = "SELECT id, password_hash, role_id, is_active FROM utenti WHERE username = %s"
    
    user_data = None
    try:
        user_data = db_manager.execute_query(query, (username,), fetch_one=True)
    except Exception as query_err:
        # Se la query fallisce (es. UndefinedTable, InFailedSqlTransaction), l'errore viene loggato da db_manager
        # e rilanciato. Lo catturiamo qui per l'audit e per fornire un messaggio utente.
        logger.error(f"Errore DB durante il recupero utente '{username}' per login: {query_err}")
        record_audit(db_manager, None, "LOGIN_FAIL", f"Errore DB login utente {username}: {str(query_err)[:100]}", "utenti", 
                     client_ip_address=client_ip_address, success=False)
        return None, None, None, f"Errore durante il tentativo di login: {query_err}"

    if user_data and user_data['is_active']:
        # L'hash dal DB potrebbe essere stringa o bytes, verify_password dovrebbe gestirlo
        hashed_password_from_db = user_data['password_hash'] 
        
        if verify_password(plain_password, hashed_password_from_db):
            user_id = user_data['id']
            role_id = user_data['role_id']
            session_id = str(uuid4()) # Genera un ID di sessione univoco
            
            # Aggiorna ultimo accesso e registra sessione
            update_login_query = "UPDATE utenti SET last_login = NOW() WHERE id = %s"
            log_session_query = """
                INSERT INTO sessioni_utente (user_id, session_id, client_ip_address, login_time) 
                VALUES (%s, %s, %s, NOW())
            """
            try:
                db_manager.execute_query(update_login_query, (user_id,))
                db_manager.execute_query(log_session_query, (user_id, session_id, client_ip_address))
                if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                    db_manager.commit()
                
                logger.info(f"Utente '{username}' (ID: {user_id}) loggato con successo. Sessione: {session_id}")
                record_audit(db_manager, user_id, "LOGIN_SUCCESS", f"Utente {username} loggato.", "utenti", user_id, 
                             session_id=session_id, client_ip_address=client_ip_address, success=True)
                return user_id, role_id, session_id, "Login effettuato con successo."
            except Exception as e_session:
                logger.error(f"Errore durante l'aggiornamento post-login per utente {username}: {e_session}", exc_info=True)
                if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                    db_manager.rollback()
                # L'utente è autenticato, ma la registrazione della sessione/last_login è fallita.
                # Potresti decidere di far fallire il login o procedere con un avviso.
                # Per ora, consideriamo fallito il setup completo della sessione.
                record_audit(db_manager, user_id, "LOGIN_FAIL", f"Errore setup sessione post-login: {str(e_session)[:100]}", "utenti", user_id, 
                             session_id=session_id, client_ip_address=client_ip_address, success=False)
                return None, None, None, "Login fallito a causa di un errore interno post-autenticazione."
        else:
            logger.warning(f"Password errata per l'utente: {username}")
            record_audit(db_manager, user_data['id'] if user_data else None, "LOGIN_FAIL", f"Password errata per utente {username}.", "utenti", 
                         user_data['id'] if user_data else None, client_ip_address=client_ip_address, success=False)
            return None, None, None, "Username o password non validi."
    elif user_data and not user_data['is_active']:
        logger.warning(f"Tentativo di login per utente disattivato: {username}")
        record_audit(db_manager, user_data['id'], "LOGIN_FAIL", f"Tentativo login utente disattivato {username}.", "utenti", 
                     user_data['id'], client_ip_address=client_ip_address, success=False)
        return None, None, None, "Account utente disattivato."
    else:
        logger.warning(f"Utente non trovato: {username}")
        # Non registrare audit per "utente non trovato" per evitare user enumeration,
        # oppure registra con user_id=None.
        record_audit(db_manager, None, "LOGIN_FAIL", f"Utente non trovato: {username}.", "utenti", 
                     client_ip_address=client_ip_address, success=False)
        return None, None, None, "Username o password non validi."

def logout_user_service(db_manager, user_id: int, session_id: str, client_ip_address: Optional[str] = None):
    """Effettua il logout dell'utente aggiornando il logout_time nella sessione."""
    logger.info(f"Tentativo di logout per utente ID: {user_id}, Sessione: {session_id}")
    query = "UPDATE sessioni_utente SET logout_time = NOW() WHERE user_id = %s AND session_id = %s AND logout_time IS NULL"
    try:
        rows_affected = db_manager.execute_query(query, (user_id, session_id))
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.commit()
        
        if rows_affected > 0:
            logger.info(f"Logout utente ID {user_id}, Sessione {session_id} registrato con successo.")
            record_audit(db_manager, user_id, "LOGOUT_SUCCESS", "Logout effettuato.", "sessioni_utente", session_id, 
                         session_id=session_id, client_ip_address=client_ip_address, success=True)
            return True
        else:
            # Sessione non trovata o già terminata
            logger.warning(f"Nessuna sessione attiva trovata per logout utente ID {user_id}, Sessione {session_id}, o già terminata.")
            # Non è strettamente un fallimento se la sessione non c'era, ma logghiamo.
            record_audit(db_manager, user_id, "LOGOUT_NO_SESSION", "Sessione non attiva/trovata per logout.", "sessioni_utente", session_id,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
            return False # O True se non si considera un errore
            
    except Exception as e:
        logger.error(f"Errore durante il logout per utente ID {user_id}: {e}", exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback()
        record_audit(db_manager, user_id, "LOGOUT_FAIL", f"Errore logout: {str(e)[:100]}", "sessioni_utente", session_id,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        return False

def get_users_service(db_manager) -> List[Dict[str, Any]]:
    """Recupera una lista di tutti gli utenti con il nome del loro ruolo."""
    # Assumendo che la tabella ruoli si chiami 'ruoli_utente' e utenti.role_id sia la FK
    query = """
        SELECT u.id, u.username, u.email, u.nome_completo, u.is_active, u.last_login, u.created_at, r.nome_ruolo
        FROM utenti u
        JOIN ruoli_utente r ON u.role_id = r.id
        ORDER BY u.username
    """
    try:
        users = db_manager.execute_query(query, fetch_all=True)
        return users if users else []
    except Exception as e:
        logger.error(f"Errore durante il recupero della lista utenti: {e}", exc_info=True)
        return []

def get_user_roles_service(db_manager) -> List[Dict[str, Any]]:
    """Recupera tutti i ruoli utente disponibili."""
    query = "SELECT id, nome_ruolo, descrizione FROM ruoli_utente ORDER BY nome_ruolo"
    try:
        roles = db_manager.execute_query(query, fetch_all=True)
        return roles if roles else []
    except Exception as e:
        logger.error(f"Errore durante il recupero dei ruoli utente: {e}", exc_info=True)
        return []
# In core/services/utenti_service.py
# ... (dopo le altre funzioni di servizio utenti come get_user_roles_service) ...

def get_user_by_id_service(db_manager, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Recupera i dettagli di un utente specifico tramite il suo ID,
    includendo il nome del ruolo.
    """
    logger.debug(f"Tentativo di recupero utente con ID: {user_id}")
    # Assumendo che la tabella ruoli si chiami 'ruoli_utente' e utenti.role_id sia la FK
    # e che la tabella utenti abbia le colonne come definite (nome_completo, is_active, ecc.)
    query = """
        SELECT 
            u.id, 
            u.username, 
            u.email, 
            u.nome_completo, 
            u.is_active, 
            u.last_login, 
            u.created_at, 
            u.updated_at,
            u.role_id, 
            r.nome_ruolo
        FROM 
            utenti u
        JOIN 
            ruoli_utente r ON u.role_id = r.id
        WHERE 
            u.id = %s
    """
    try:
        user_data = db_manager.execute_query(query, (user_id,), fetch_one=True)
        if user_data:
            logger.info(f"Utente ID {user_id} ('{user_data['username']}') recuperato con successo.")
            return dict(user_data) # Converte DictRow in dict standard se necessario
        else:
            logger.warning(f"Nessun utente trovato con ID: {user_id}")
            return None
    except Exception as e:
        logger.error(f"Errore durante il recupero dell'utente ID {user_id}: {e}", exc_info=True)
        # Non c'è transazione da annullare per una SELECT, ma è buona norma non lasciare eccezioni non gestite
        # db_manager.rollback() # Generalmente non necessario per SELECT fallite
        return None
# In core/services/utenti_service.py
# ... (dopo get_user_by_id_service e gli altri import) ...

def update_user_service(db_manager, user_id_to_update: int, data_to_update: Dict[str, Any],
                        current_user_id: Optional[int] = None, 
                        client_ip_address: Optional[str] = None,
                        session_id: Optional[str] = None) -> bool:
    """
    Aggiorna i dati di un utente esistente.
    Non gestisce l'aggiornamento della password (usare funzioni dedicate).

    Args:
        db_manager: L'istanza del gestore del database.
        user_id_to_update: L'ID dell'utente da aggiornare.
        data_to_update: Un dizionario con i campi e i nuovi valori.
                        Campi permessi: 'email', 'nome_completo', 'role_id', 'is_active'.
        current_user_id: L'ID dell'utente che esegue l'operazione (per audit).
        client_ip_address: IP dell'utente che esegue l'operazione (per audit).
        session_id: ID della sessione dell'utente che esegue l'operazione (per audit).

    Returns:
        True se l'aggiornamento ha successo, False altrimenti.
    """
    logger.info(f"Tentativo di aggiornamento per l'utente ID: {user_id_to_update} da parte dell'utente ID: {current_user_id}")

    if not data_to_update:
        logger.warning("Nessun dato fornito per l'aggiornamento.")
        return False

    # Campi che permettiamo di aggiornare tramite questa funzione
    allowed_fields_to_update = {'email', 'nome_completo', 'role_id', 'is_active'}
    
    set_clauses = []
    params = []
    update_details_log = [] # Per registrare cosa è stato cambiato

    for field, value in data_to_update.items():
        if field in allowed_fields_to_update:
            # Validazione specifica per campo se necessario (es. formato email)
            if field == 'email' and (not isinstance(value, str) or "@" not in value): # Validazione email molto base
                logger.warning(f"Formato email non valido per l'aggiornamento: {value}")
                # Potresti sollevare un ValueError o semplicemente ignorare questo campo
                continue 
            
            set_clauses.append(f"{field} = %s")
            params.append(value)
            update_details_log.append(f"{field}='{value}'")
        elif field == 'password_hash' or field == 'password':
            logger.warning("Tentativo di aggiornare la password tramite update_user_service. Ignorato. Usare change_password_service.")
        # Ignora altri campi non permessi

    if not set_clauses:
        logger.warning("Nessun campo valido fornito per l'aggiornamento o valori non validi.")
        # Audit di tentativo fallito se si vuole
        record_audit(db_manager, current_user_id, "UPDATE_USER_FAIL",
                     f"Tentativo di aggiornare utente ID {user_id_to_update} fallito: nessun campo valido.",
                     "utenti", user_id_to_update,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        return False

    # Aggiungi sempre l'aggiornamento del timestamp
    set_clauses.append("updated_at = NOW()")
    
    query = f"UPDATE utenti SET {', '.join(set_clauses)} WHERE id = %s"
    params.append(user_id_to_update)

    try:
        # Opzionale: verifica se l'utente esiste prima di aggiornare
        # existing_user = get_user_by_id_service(db_manager, user_id_to_update)
        # if not existing_user:
        #     logger.warning(f"Tentativo di aggiornare utente non esistente ID: {user_id_to_update}")
        #     record_audit(...)
        #     return False

        rows_affected = db_manager.execute_query(query, tuple(params)) # execute_query restituisce rowcount

        if rows_affected > 0:
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.commit()
            log_message = f"Utente ID {user_id_to_update} aggiornato con successo. Dati: {', '.join(update_details_log)}"
            logger.info(log_message)
            record_audit(db_manager, current_user_id, "UPDATE_USER_SUCCESS",
                         log_message, "utenti", user_id_to_update,
                         session_id=session_id, client_ip_address=client_ip_address, success=True)
            return True
        elif rows_affected == 0:
            # Nessuna riga affetta potrebbe significare che l'ID utente non esiste o i valori erano già quelli.
            # Se si è certi che l'ID esista (es. controllo precedente), allora i dati non sono cambiati.
            logger.warning(f"Aggiornamento utente ID {user_id_to_update} non ha modificato righe (utente non trovato o dati identici).")
            # Non fare rollback se non ci sono errori, la transazione potrebbe essere comunque valida per altre operazioni
            # se non in autocommit. Ma dato che non ha modificato nulla, un rollback è sicuro se l'operazione era isolata.
            # if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            #     db_manager.rollback() # O non fare nulla se si considera "non errore"
            record_audit(db_manager, current_user_id, "UPDATE_USER_NO_CHANGE",
                         f"Tentativo di aggiornare utente ID {user_id_to_update}: nessuna modifica (utente non trovato o dati identici). Dati: {', '.join(update_details_log)}",
                         "utenti", user_id_to_update,
                         session_id=session_id, client_ip_address=client_ip_address, success=False) # Successo = False perché non ha aggiornato
            return False 
        else: # rows_affected è None o < 0, improbabile con execute_query che restituisce rowcount
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.rollback()
            logger.error(f"Aggiornamento utente ID {user_id_to_update} ha restituito un rowcount inatteso: {rows_affected}")
            record_audit(db_manager, current_user_id, "UPDATE_USER_FAIL",
                         f"Aggiornamento utente ID {user_id_to_update} fallito, rowcount inatteso. Dati: {', '.join(update_details_log)}",
                         "utenti", user_id_to_update,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
            return False

    except psycopg2.Error as db_err: # Ad es. violazione UNIQUE constraint su email
        logger.error(f"Errore DB durante l'aggiornamento dell'utente ID {user_id_to_update}: {db_err}", exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback()
        record_audit(db_manager, current_user_id, "UPDATE_USER_FAIL",
                     f"Errore DB aggiornamento utente ID {user_id_to_update}: {str(db_err)[:200]}. Dati: {', '.join(update_details_log)}",
                     "utenti", user_id_to_update,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise # Rilancia per permettere al chiamante di gestire l'errore specifico del DB
    except Exception as e:
        logger.error(f"Errore Python generico durante l'aggiornamento dell'utente ID {user_id_to_update}: {e}", exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback()
        record_audit(db_manager, current_user_id, "UPDATE_USER_FAIL",
                     f"Errore generico aggiornamento utente ID {user_id_to_update}: {str(e)[:200]}. Dati: {', '.join(update_details_log)}",
                     "utenti", user_id_to_update,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise # Rilancia l'eccezione
dati = {
        'email': 'nuova.email@example.com',
        'nome_completo': 'Mario Rossi Aggiornato',
        'role_id': 2,  # ID del nuovo ruolo
        'is_active': True
    }
# In core/services/utenti_service.py
# ... (dopo update_user_service e gli altri import) ...

def delete_user_service(db_manager, user_id_to_delete: int,
                        current_user_id: Optional[int] = None,
                        client_ip_address: Optional[str] = None,
                        session_id: Optional[str] = None) -> bool:
    """
    Esegue un "soft delete" di un utente impostando il suo campo is_active a FALSE.
    Impedisce l'auto-cancellazione.

    Args:
        db_manager: L'istanza del gestore del database.
        user_id_to_delete: L'ID dell'utente da "cancellare" (disattivare).
        current_user_id: L'ID dell'utente che esegue l'operazione (per audit e controllo auto-cancellazione).
        client_ip_address: IP dell'utente che esegue l'operazione (per audit).
        session_id: ID della sessione dell'utente che esegue l'operazione (per audit).

    Returns:
        True se l'utente è stato disattivato con successo, False altrimenti.
    """
    logger.info(f"Tentativo di soft delete per l'utente ID: {user_id_to_delete} da parte dell'utente ID: {current_user_id}")

    # 1. Controllo auto-cancellazione
    if user_id_to_delete == current_user_id:
        logger.warning(f"Utente ID {current_user_id} ha tentato di cancellare se stesso. Operazione non permessa.")
        record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
                     f"Tentativo di auto-cancellazione (utente ID {user_id_to_delete}).",
                     "utenti", user_id_to_delete,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        # Potresti sollevare un ValueError qui per notificare l'UI in modo più esplicito
        # raise ValueError("Non è possibile cancellare il proprio account utente.")
        return False

    # 2. Opzionale: Protezione per utenti "speciali" (es. admin principale con ID 1)
    # if user_id_to_delete == 1: # Assumendo che l'ID 1 sia un admin non cancellabile
    #     logger.warning(f"Tentativo di cancellare l'utente admin principale (ID: 1). Operazione non permessa.")
    #     record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
    #                  "Tentativo di cancellare l'utente admin principale.", "utenti", user_id_to_delete,
    #                  session_id=session_id, client_ip_address=client_ip_address, success=False)
    #     return False

    # 3. Query per il soft delete (imposta is_active = FALSE e aggiorna updated_at)
    # Assicurati che la tua tabella 'utenti' abbia la colonna 'is_active' e 'updated_at'
    query = "UPDATE utenti SET is_active = FALSE, updated_at = NOW() WHERE id = %s AND is_active = TRUE"
    params = (user_id_to_delete,)

    try:
        rows_affected = db_manager.execute_query(query, params)

        if rows_affected > 0:
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.commit()
            log_message = f"Utente ID {user_id_to_delete} disattivato (soft delete) con successo."
            logger.info(log_message)
            record_audit(db_manager, current_user_id, "DELETE_USER_SUCCESS", # O "DEACTIVATE_USER_SUCCESS"
                         log_message, "utenti", user_id_to_delete,
                         session_id=session_id, client_ip_address=client_ip_address, success=True)
            return True
        elif rows_affected == 0:
            # L'utente potrebbe non esistere o essere già inattivo.
            # Controlliamo se esiste per dare un feedback più preciso.
            user_exists_check = get_user_by_id_service(db_manager, user_id_to_delete)
            if user_exists_check:
                if not user_exists_check.get('is_active'):
                    logger.info(f"Utente ID {user_id_to_delete} era già inattivo.")
                    # Consideralo un successo o un "nessuna modifica" a seconda della logica desiderata.
                    # Per ora, lo trattiamo come se l'obiettivo fosse raggiunto.
                    record_audit(db_manager, current_user_id, "DELETE_USER_NO_CHANGE",
                                 f"Utente ID {user_id_to_delete} era già inattivo.", "utenti", user_id_to_delete,
                                 session_id=session_id, client_ip_address=client_ip_address, success=True) # Successo perché lo stato finale è "inattivo"
                    return True # L'obiettivo è che sia inattivo, quindi è "successo"
                else: # Altro caso, raro se rows_affected è 0 e l'utente è attivo
                    logger.warning(f"Soft delete per utente ID {user_id_to_delete} non ha modificato righe, ma l'utente risulta attivo. Strano.")

            else:
                logger.warning(f"Tentativo di soft delete per utente non esistente ID: {user_id_to_delete}")
            
            # Se arriviamo qui e rows_affected è 0, qualcosa non è andato come previsto o l'utente non è stato trovato/modificato.
            record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
                         f"Soft delete per utente ID {user_id_to_delete} non ha modificato righe (utente non trovato o già inattivo senza rilevamento precedente).",
                         "utenti", user_id_to_delete,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
            return False
        else: # rows_affected < 0 o None, improbabile
             if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.rollback()
             logger.error(f"Soft delete per utente ID {user_id_to_delete} ha restituito un rowcount inatteso: {rows_affected}")
             record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
                         f"Soft delete per utente ID {user_id_to_delete} fallito, rowcount inatteso.",
                         "utenti", user_id_to_delete,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
             return False

    except psycopg2.Error as db_err:
        logger.error(f"Errore DB durante il soft delete dell'utente ID {user_id_to_delete}: {db_err}", exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback()
        record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
                     f"Errore DB soft delete utente ID {user_id_to_delete}: {str(db_err)[:200]}",
                     "utenti", user_id_to_delete,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise # Rilancia per permettere al chiamante di gestire l'errore specifico del DB
    except Exception as e:
        logger.error(f"Errore Python generico durante il soft delete dell'utente ID {user_id_to_delete}: {e}", exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback()
        record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
                     f"Errore generico soft delete utente ID {user_id_to_delete}: {str(e)[:200]}",
                     "utenti", user_id_to_delete,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise # Rilancia l'eccezione
    # In core/services/utenti_service.py
# ... (dopo update_user_service e gli altri import) ...

def delete_user_service(db_manager, user_id_to_delete: int,
                        current_user_id: Optional[int] = None,
                        client_ip_address: Optional[str] = None,
                        session_id: Optional[str] = None) -> bool:
    """
    Esegue un "soft delete" di un utente impostando il suo campo is_active a FALSE.
    Impedisce l'auto-cancellazione.

    Args:
        db_manager: L'istanza del gestore del database.
        user_id_to_delete: L'ID dell'utente da "cancellare" (disattivare).
        current_user_id: L'ID dell'utente che esegue l'operazione (per audit e controllo auto-cancellazione).
        client_ip_address: IP dell'utente che esegue l'operazione (per audit).
        session_id: ID della sessione dell'utente che esegue l'operazione (per audit).

    Returns:
        True se l'utente è stato disattivato con successo, False altrimenti.
    """
    logger.info(f"Tentativo di soft delete per l'utente ID: {user_id_to_delete} da parte dell'utente ID: {current_user_id}")

    # 1. Controllo auto-cancellazione
    if user_id_to_delete == current_user_id:
        logger.warning(f"Utente ID {current_user_id} ha tentato di cancellare se stesso. Operazione non permessa.")
        record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
                     f"Tentativo di auto-cancellazione (utente ID {user_id_to_delete}).",
                     "utenti", user_id_to_delete,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        # Potresti sollevare un ValueError qui per notificare l'UI in modo più esplicito
        # raise ValueError("Non è possibile cancellare il proprio account utente.")
        return False

    # 2. Opzionale: Protezione per utenti "speciali" (es. admin principale con ID 1)
    # if user_id_to_delete == 1: # Assumendo che l'ID 1 sia un admin non cancellabile
    #     logger.warning(f"Tentativo di cancellare l'utente admin principale (ID: 1). Operazione non permessa.")
    #     record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
    #                  "Tentativo di cancellare l'utente admin principale.", "utenti", user_id_to_delete,
    #                  session_id=session_id, client_ip_address=client_ip_address, success=False)
    #     return False

    # 3. Query per il soft delete (imposta is_active = FALSE e aggiorna updated_at)
    # Assicurati che la tua tabella 'utenti' abbia la colonna 'is_active' e 'updated_at'
    query = "UPDATE utenti SET is_active = FALSE, updated_at = NOW() WHERE id = %s AND is_active = TRUE"
    params = (user_id_to_delete,)

    try:
        rows_affected = db_manager.execute_query(query, params)

        if rows_affected > 0:
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.commit()
            log_message = f"Utente ID {user_id_to_delete} disattivato (soft delete) con successo."
            logger.info(log_message)
            record_audit(db_manager, current_user_id, "DELETE_USER_SUCCESS", # O "DEACTIVATE_USER_SUCCESS"
                         log_message, "utenti", user_id_to_delete,
                         session_id=session_id, client_ip_address=client_ip_address, success=True)
            return True
        elif rows_affected == 0:
            # L'utente potrebbe non esistere o essere già inattivo.
            # Controlliamo se esiste per dare un feedback più preciso.
            user_exists_check = get_user_by_id_service(db_manager, user_id_to_delete)
            if user_exists_check:
                if not user_exists_check.get('is_active'):
                    logger.info(f"Utente ID {user_id_to_delete} era già inattivo.")
                    # Consideralo un successo o un "nessuna modifica" a seconda della logica desiderata.
                    # Per ora, lo trattiamo come se l'obiettivo fosse raggiunto.
                    record_audit(db_manager, current_user_id, "DELETE_USER_NO_CHANGE",
                                 f"Utente ID {user_id_to_delete} era già inattivo.", "utenti", user_id_to_delete,
                                 session_id=session_id, client_ip_address=client_ip_address, success=True) # Successo perché lo stato finale è "inattivo"
                    return True # L'obiettivo è che sia inattivo, quindi è "successo"
                else: # Altro caso, raro se rows_affected è 0 e l'utente è attivo
                    logger.warning(f"Soft delete per utente ID {user_id_to_delete} non ha modificato righe, ma l'utente risulta attivo. Strano.")

            else:
                logger.warning(f"Tentativo di soft delete per utente non esistente ID: {user_id_to_delete}")
            
            # Se arriviamo qui e rows_affected è 0, qualcosa non è andato come previsto o l'utente non è stato trovato/modificato.
            record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
                         f"Soft delete per utente ID {user_id_to_delete} non ha modificato righe (utente non trovato o già inattivo senza rilevamento precedente).",
                         "utenti", user_id_to_delete,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
            return False
        else: # rows_affected < 0 o None, improbabile
             if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.rollback()
             logger.error(f"Soft delete per utente ID {user_id_to_delete} ha restituito un rowcount inatteso: {rows_affected}")
             record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
                         f"Soft delete per utente ID {user_id_to_delete} fallito, rowcount inatteso.",
                         "utenti", user_id_to_delete,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
             return False

    except psycopg2.Error as db_err:
        logger.error(f"Errore DB durante il soft delete dell'utente ID {user_id_to_delete}: {db_err}", exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback()
        record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
                     f"Errore DB soft delete utente ID {user_id_to_delete}: {str(db_err)[:200]}",
                     "utenti", user_id_to_delete,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise # Rilancia per permettere al chiamante di gestire l'errore specifico del DB
    except Exception as e:
        logger.error(f"Errore Python generico durante il soft delete dell'utente ID {user_id_to_delete}: {e}", exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback()
        record_audit(db_manager, current_user_id, "DELETE_USER_FAIL",
                     f"Errore generico soft delete utente ID {user_id_to_delete}: {str(e)[:200]}",
                     "utenti", user_id_to_delete,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise # Rilancia l'eccezione
    # In core/services/utenti_service.py
# ... (dopo delete_user_service e gli altri import) ...

def change_password_service(db_manager, user_id: int, old_plain_password: str, new_plain_password: str,
                            current_user_id: Optional[int] = None, # L'ID dell'utente che invoca, dovrebbe coincidere con user_id
                            client_ip_address: Optional[str] = None,
                            session_id: Optional[str] = None) -> tuple[bool, str]:
    """
    Permette a un utente di cambiare la propria password dopo aver verificato quella vecchia.

    Args:
        db_manager: L'istanza del gestore del database.
        user_id: L'ID dell'utente la cui password deve essere cambiata.
        old_plain_password: La password attuale dell'utente, in chiaro.
        new_plain_password: La nuova password desiderata, in chiaro.
        current_user_id: L'ID dell'utente che sta eseguendo l'operazione.
                         Per questa funzione, ci si aspetta user_id == current_user_id.
        client_ip_address: IP dell'utente (per audit).
        session_id: ID della sessione utente (per audit).

    Returns:
        Una tupla (bool, str) indicante successo/fallimento e un messaggio.
    """
    logger.info(f"Tentativo di cambio password per l'utente ID: {user_id} da parte dell'utente ID: {current_user_id}")

    # Controllo di autorizzazione: l'utente può cambiare solo la propria password.
    # Un admin che resetta la password di un altro utente dovrebbe usare una funzione diversa (es. admin_reset_password_service).
    if user_id != current_user_id:
        logger.warning(f"Tentativo non autorizzato di cambio password per utente ID {user_id} da parte di utente ID {current_user_id}.")
        # Non registrare audit dettagliato per non rivelare tentativi di accesso non autorizzato a specifiche funzionalità
        # Ma l'audit del sistema potrebbe registrare un tentativo di azione non permessa se il menu_handler ha un controllo di ruolo.
        return False, "Operazione non autorizzata."

    # Validazione input base
    if not old_plain_password or not new_plain_password:
        msg = "La vecchia e la nuova password non possono essere vuote."
        logger.warning(msg)
        return False, msg
    
    if new_plain_password == old_plain_password:
        msg = "La nuova password deve essere diversa da quella vecchia."
        logger.warning(msg)
        return False, msg

    # Potresti aggiungere qui controlli di complessità per new_plain_password se necessario

    try:
        # 1. Recupera l'utente e l'hash della password attuale
        query_user = "SELECT id, password_hash, is_active FROM utenti WHERE id = %s"
        user_data = db_manager.execute_query(query_user, (user_id,), fetch_one=True)

        if not user_data:
            msg = f"Utente ID {user_id} non trovato."
            logger.warning(msg)
            # Audit di tentativo su utente non esistente
            record_audit(db_manager, current_user_id, "CHANGE_PASSWORD_FAIL", msg, "utenti", user_id,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
            return False, msg
        
        if not user_data['is_active']:
            msg = f"L'account utente ID {user_id} è disattivato. Impossibile cambiare password."
            logger.warning(msg)
            record_audit(db_manager, current_user_id, "CHANGE_PASSWORD_FAIL", msg, "utenti", user_id,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
            return False, msg

        # 2. Verifica la vecchia password
        hashed_password_from_db = user_data['password_hash']
        if not verify_password(old_plain_password, hashed_password_from_db):
            msg = "La vecchia password fornita non è corretta."
            logger.warning(msg + f" (Utente ID: {user_id})")
            # Registra il tentativo fallito
            record_audit(db_manager, current_user_id, "CHANGE_PASSWORD_FAIL", msg, "utenti", user_id,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
            return False, msg

        # 3. Hash della nuova password
        new_hashed_pw_bytes = hash_password(new_plain_password)
        new_hashed_pw_str_for_db = new_hashed_pw_bytes.decode('latin-1') # O il tuo encoding per il DB

        # 4. Aggiorna la password nel database e il timestamp updated_at
        update_query = "UPDATE utenti SET password_hash = %s, updated_at = NOW() WHERE id = %s"
        params = (new_hashed_pw_str_for_db, user_id)
        
        rows_affected = db_manager.execute_query(update_query, params)

        if rows_affected > 0:
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.commit()
            msg = f"Password per utente ID {user_id} cambiata con successo."
            logger.info(msg)
            record_audit(db_manager, current_user_id, "CHANGE_PASSWORD_SUCCESS", msg, "utenti", user_id,
                         session_id=session_id, client_ip_address=client_ip_address, success=True)
            return True, msg
        else:
            # Improbabile se l'utente è stato trovato e la query è corretta, ma gestiamolo.
            # Potrebbe accadere se l'ID utente non esiste (nonostante il check precedente, in caso di race condition o errore logico)
            msg = f"Cambio password per utente ID {user_id} non ha modificato righe (utente non trovato durante l'update?)."
            logger.error(msg)
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.rollback() # Annulla se qualcosa è andato storto nell'update
            record_audit(db_manager, current_user_id, "CHANGE_PASSWORD_FAIL", msg, "utenti", user_id,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
            return False, msg

    except psycopg2.Error as db_err:
        msg = f"Errore DB durante il cambio password per utente ID {user_id}: {db_err}"
        logger.error(msg, exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback()
        record_audit(db_manager, current_user_id, "CHANGE_PASSWORD_FAIL", f"Errore DB: {str(db_err)[:200]}", "utenti", user_id,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        # Non rilanciare l'eccezione direttamente all'UI se non vuoi esporre dettagli DB,
        # ma restituisci un messaggio di errore generico.
        return False, "Errore interno durante il cambio password. Riprova più tardi."
    except ValueError as ve: # Ad es. da hash_password se la nuova password è vuota
        msg = f"Errore di validazione durante il cambio password per utente ID {user_id}: {ve}"
        logger.warning(msg)
        # Non c'è bisogno di rollback qui se l'errore è prima della query DB
        record_audit(db_manager, current_user_id, "CHANGE_PASSWORD_FAIL", msg, "utenti", user_id,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        return False, str(ve)
    except Exception as e:
        msg = f"Errore Python generico durante il cambio password per utente ID {user_id}: {e}"
        logger.error(msg, exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback() # Rollback per sicurezza
        record_audit(db_manager, current_user_id, "CHANGE_PASSWORD_FAIL", f"Errore generico: {str(e)[:200]}", "utenti", user_id,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        return False, "Si è verificato un errore imprevisto. Riprova più tardi."
    # In core/services/utenti_service.py
# ... (dopo change_password_service e gli altri import) ...

def admin_reset_password_service(db_manager, user_id_to_reset: int, new_plain_password: str,
                                 admin_user_id: int, # L'ID dell'admin che esegue l'operazione
                                 client_ip_address: Optional[str] = None,
                                 session_id: Optional[str] = None) -> tuple[bool, str]:
    """
    Permette a un amministratore di resettare la password di un utente.

    Args:
        db_manager: L'istanza del gestore del database.
        user_id_to_reset: L'ID dell'utente la cui password deve essere resettata.
        new_plain_password: La nuova password da impostare, in chiaro.
        admin_user_id: L'ID dell'amministratore che esegue l'operazione.
        client_ip_address: IP dell'amministratore (per audit).
        session_id: ID della sessione dell'amministratore (per audit).

    Returns:
        Una tupla (bool, str) indicante successo/fallimento e un messaggio.
    """
    logger.info(f"Tentativo di reset password per utente ID: {user_id_to_reset} da parte dell'admin ID: {admin_user_id}")

    # 1. Verifica che l'esecutore (admin_user_id) sia un amministratore
    admin_user_data = get_user_by_id_service(db_manager, admin_user_id) # Usa la funzione che abbiamo creato
    
    if not admin_user_data or not admin_user_data.get('is_active'):
        msg = "Utente amministratore non valido o non attivo."
        logger.error(msg + f" (Admin ID: {admin_user_id})")
        # Non registrare audit se l'admin stesso non è valido, per evitare abusi del log
        return False, "Operazione non autorizzata (admin non valido)."

    # Assumiamo che il nome del ruolo admin sia 'admin' o 'amministratore'
    # Questa logica di verifica ruolo potrebbe essere centralizzata o più robusta.
    admin_role_name = admin_user_data.get('nome_ruolo', '').lower()
    if admin_role_name not in ['admin', 'amministratore']:
        msg = f"Utente ID {admin_user_id} non ha i permessi di amministratore per resettare password."
        logger.warning(msg)
        record_audit(db_manager, admin_user_id, "ADMIN_RESET_PASSWORD_AUTH_FAIL", msg, "utenti", user_id_to_reset,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        return False, "Operazione non autorizzata (permessi insufficienti)."

    # 2. L'admin non dovrebbe resettare la propria password con questa funzione
    if user_id_to_reset == admin_user_id:
        msg = "Gli amministratori devono usare la funzione 'cambia la mia password' per il proprio account."
        logger.info(msg + f" (Admin ID: {admin_user_id})")
        # Non è un fallimento di sicurezza, ma un uso improprio della funzione
        return False, msg

    # 3. Validazione della nuova password
    if not new_plain_password:
        msg = "La nuova password non può essere vuota."
        logger.warning(msg)
        return False, msg
    # Potresti aggiungere qui controlli di complessità per new_plain_password

    try:
        # 4. Verifica che l'utente da resettare esista (opzionale, l'UPDATE fallirebbe comunque)
        user_to_reset_data = get_user_by_id_service(db_manager, user_id_to_reset)
        if not user_to_reset_data:
            msg = f"Utente da resettare (ID: {user_id_to_reset}) non trovato."
            logger.warning(msg)
            record_audit(db_manager, admin_user_id, "ADMIN_RESET_PASSWORD_FAIL", msg, "utenti", user_id_to_reset,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
            return False, msg
        
        # Non è necessario controllare se user_to_reset_data['is_active'],
        # un admin potrebbe voler resettare la password di un account disattivato per riattivarlo.

        # 5. Hash della nuova password
        new_hashed_pw_bytes = hash_password(new_plain_password)
        new_hashed_pw_str_for_db = new_hashed_pw_bytes.decode('latin-1') # O il tuo encoding per il DB

        # 6. Aggiorna la password nel database e il timestamp updated_at
        update_query = "UPDATE utenti SET password_hash = %s, updated_at = NOW() WHERE id = %s"
        params = (new_hashed_pw_str_for_db, user_id_to_reset)
        
        rows_affected = db_manager.execute_query(update_query, params)

        if rows_affected > 0:
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.commit()
            msg = f"Password per utente ID {user_id_to_reset} resettata con successo dall'admin ID {admin_user_id}."
            logger.info(msg)
            record_audit(db_manager, admin_user_id, "ADMIN_RESET_PASSWORD_SUCCESS", msg, "utenti", user_id_to_reset,
                         session_id=session_id, client_ip_address=client_ip_address, success=True)
            return True, "Password resettata con successo."
        else:
            # Improbabile se l'utente è stato trovato prima, ma gestiamolo.
            msg = f"Reset password per utente ID {user_id_to_reset} non ha modificato righe (utente non trovato durante l'update?)."
            logger.error(msg)
            if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
                db_manager.rollback()
            record_audit(db_manager, admin_user_id, "ADMIN_RESET_PASSWORD_FAIL", msg, "utenti", user_id_to_reset,
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
            return False, "Reset password fallito (utente non trovato o errore imprevisto)."

    except psycopg2.Error as db_err:
        msg = f"Errore DB durante il reset password per utente ID {user_id_to_reset} da admin ID {admin_user_id}: {db_err}"
        logger.error(msg, exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback()
        record_audit(db_manager, admin_user_id, "ADMIN_RESET_PASSWORD_FAIL", f"Errore DB: {str(db_err)[:200]}", "utenti", user_id_to_reset,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        return False, "Errore interno durante il reset della password. Riprova più tardi."
    except ValueError as ve: # Ad es. da hash_password se la nuova password è vuota
        msg = f"Errore di validazione durante il reset password: {ve}"
        logger.warning(msg)
        record_audit(db_manager, admin_user_id, "ADMIN_RESET_PASSWORD_FAIL", msg, "utenti", user_id_to_reset,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        return False, str(ve)
    except Exception as e:
        msg = f"Errore Python generico durante il reset password per utente ID {user_id_to_reset}: {e}"
        logger.error(msg, exc_info=True)
        if db_manager.conn and db_manager.conn.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT:
            db_manager.rollback()
        record_audit(db_manager, admin_user_id, "ADMIN_RESET_PASSWORD_FAIL", f"Errore generico: {str(e)[:200]}", "utenti", user_id_to_reset,
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        return False, "Si è verificato un errore imprevisto. Riprova più tardi."
    
# Potresti aggiungere altre funzioni di servizio per utenti, come:
# - update_user_service (per modificare dati utente, ruolo, stato attivo)
# - delete_user_service (con cautela!)
# - change_password_service
# - get_user_by_id_service