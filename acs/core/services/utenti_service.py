# core/services/utenti_service.py
import bcrypt
import logging
from uuid import uuid4
from datetime import datetime
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

# Potresti aggiungere altre funzioni di servizio per utenti, come:
# - update_user_service (per modificare dati utente, ruolo, stato attivo)
# - delete_user_service (con cautela!)
# - change_password_service
# - get_user_by_id_service