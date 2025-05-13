# core/services/utenti_service.py
import bcrypt
import logging
from uuid import uuid4
from datetime import datetime
from .audit_service import record_audit # Assicurati che questo import funzioni (stessa directory)
from typing import Union, Optional # Aggiungiamo anche Optional che potrebbe servire

# Ottieni un logger specifico per questo modulo
logger = logging.getLogger("CatastoAppLogger.UtentiService")

SALT_ROUNDS = 12 # Numero di round per bcrypt, puoi renderlo configurabile

def hash_password(plain_password: str) -> bytes:
    """Genera l'hash di una password usando bcrypt."""
    if not plain_password:
        raise ValueError("La password non può essere vuota.")
    salt = bcrypt.gensalt(rounds=SALT_ROUNDS)
    hashed_pw = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
    return hashed_pw

def verify_password(plain_password: str, hashed_password_from_db: Union[str, bytes]) -> bool:
    """Verifica una password plain text con un hash memorizzato."""
    if not plain_password or not hashed_password_from_db:
        return False
    
    # Assicura che l'hash dal DB sia in bytes
    if isinstance(hashed_password_from_db, str):
        # Se l'hash è stato salvato come stringa (es. dopo .decode()), ri-encodalo
        # Questo dipende da come l'hai salvato. Se è una stringa esadecimale o base64,
        # la conversione sarà diversa. Assumiamo che sia stata salvata come stringa UTF-8
        # dell'hash binario.
        db_hashed_bytes = hashed_password_from_db.encode('utf-8')
    else:
        db_hashed_bytes = hashed_password_from_db
        
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), db_hashed_bytes)
    except ValueError as e: # Può accadere se l'hash non è valido (es. troppo corto, formato errato)
        logger.error(f"Errore durante la verifica della password (possibile hash non valido): {e}")
        return False


def register_user_service(db_manager, username, plain_password, email, role_id, 
                          client_ip_address=None, created_by_user_id=None):
    """Registra un nuovo utente nel database."""
    logger.info(f"Tentativo di registrazione per l'utente: {username}")
    
    # Verifica se l'utente esiste già
    check_query = "SELECT id FROM utenti WHERE username = %s OR email = %s"
    existing_user = db_manager.execute_query(check_query, (username, email), fetch_one=True)
    if existing_user:
        logger.warning(f"Tentativo di registrazione fallito: username '{username}' o email '{email}' già esistente.")
        # Potresti voler distinguere tra username ed email duplicati
        # Per ora, un messaggio generico
        error_message = f"Username '{username}' o email '{email}' già in uso."
        if existing_user['username'] == username :
             error_message = f"Username '{username}' già in uso."
        elif existing_user['email'] == email:
             error_message = f"Email '{email}' già in uso."

        record_audit(db_manager, created_by_user_id or None, "REGISTER_USER_FAIL", 
                     f"Tentativo di registrazione utente {username} fallito: {error_message}", 
                     "utenti", client_ip_address=client_ip_address, success=False)
        raise ValueError(error_message)

    hashed_pw_bytes = hash_password(plain_password)
    
    # Salva l'hash come stringa (UTF-8) o mantienilo come byte array se il driver lo supporta
    # Molti driver preferiscono stringhe per i campi bytea o testuali.
    # Se il campo DB è BYTEA, psycopg2 può gestire direttamente i bytes.
    # Se è TEXT, devi decodificare (es. hashed_pw_bytes.decode('utf-8', 'ignore') o base64).
    # Per semplicità, assumiamo che il driver gestisca i bytes o che il campo sia testuale
    # e accetti la rappresentazione stringa dell'hash (che non è l'hash grezzo!).
    # La pratica migliore per BYTEA è passare `psycopg2.Binary(hashed_pw_bytes)`
    # Per TEXT, `hashed_pw_bytes.decode('latin-1')` o base64.
    # Il tuo codice originale usava `password_hash` quindi probabilmente era testo.
    # Bcrypt produce hash che possono contenere caratteri non validi per UTF-8 diretto
    # se si tenta di decodificarli direttamente. È meglio usare `latin-1` o `ascii`
    # per la rappresentazione stringa se il campo DB è testuale e non bytea.
    # Se il tuo campo `password_hash` in DB è di tipo `BYTEA`, passa `hashed_pw_bytes` direttamente.
    # Se è `TEXT`, una rappresentazione sicura è base64:
    # import base64
    # hashed_pw_for_db = base64.b64encode(hashed_pw_bytes).decode('ascii')

    # Per ora, presumo che il tuo campo password_hash sia TEXT e che tu stia salvando
    # una stringa che bcrypt può comunque leggere (es. la stringa prodotta da hashpw).
    # bcrypt.hashpw restituisce bytes, questi bytes possono essere salvati in un campo bytea.
    # Se il campo è text, va convertito in modo sicuro.
    # Il tuo CatastoDBManager originale sembrava salvare stringhe.
    # Per coerenza con `verify_password` che gestisce stringhe dal DB:
    hashed_pw_str_for_db = hashed_pw_bytes.decode('latin-1') # O 'ascii' se preferisci, ma latin-1 è più sicuro per byte arbitrari


    insert_query = """
        INSERT INTO utenti (username, password_hash, email, role_id, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, TRUE, NOW(), NOW()) RETURNING id
    """
    try:
        user_record = db_manager.execute_query(insert_query, (username, hashed_pw_str_for_db, email, role_id), fetch_one=True)
        if user_record and user_record['id']:
            user_id = user_record['id']
            db_manager.commit()
            logger.info(f"Utente '{username}' (ID: {user_id}) registrato con successo.")
            record_audit(db_manager, created_by_user_id or user_id, "REGISTER_USER_SUCCESS", 
                         f"Utente {username} (ID: {user_id}) registrato.", "utenti", user_id,
                         client_ip_address=client_ip_address, success=True)
            return user_id
        else:
            db_manager.rollback()
            logger.error(f"Registrazione utente '{username}' fallita dopo l'inserimento.")
            record_audit(db_manager, created_by_user_id or None, "REGISTER_USER_FAIL", 
                         f"Registrazione utente {username} fallita (nessun ID ritornato).", "utenti",
                         client_ip_address=client_ip_address, success=False)
            return None
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore critico durante la registrazione dell'utente '{username}': {e}", exc_info=True)
        record_audit(db_manager, created_by_user_id or None, "REGISTER_USER_FAIL", 
                     f"Errore critico registrazione utente {username}: {str(e)[:100]}", "utenti",
                     client_ip_address=client_ip_address, success=False)
        raise # Rilancia per informare l'UI

def login_user_service(db_manager, username, plain_password, client_ip_address=None):
    """Effettua il login di un utente e registra la sessione."""
    logger.info(f"Tentativo di login per l'utente: {username}")
    query = "SELECT id, password_hash, role_id, is_active FROM utenti WHERE username = %s"
    
    user_data = db_manager.execute_query(query, (username,), fetch_one=True)

    if user_data:
        if not user_data['is_active']:
            logger.warning(f"Tentativo di login fallito per l'utente '{username}': account non attivo.")
            record_audit(db_manager, user_data['id'], "LOGIN_FAIL", 
                         f"Utente {username} account non attivo.", "utenti", user_data['id'], 
                         client_ip_address=client_ip_address, success=False)
            return None, None, None, "Account utente non attivo."

        # hashed_password_from_db è la stringa letta dal DB (es. latin-1)
        hashed_password_from_db = user_data['password_hash'] 

        if verify_password(plain_password, hashed_password_from_db.encode('latin-1')): # Ri-encodala a bytes per bcrypt
            user_id = user_data['id']
            role_id = user_data['role_id']
            session_id = str(uuid4())
            
            log_session_query = """
                INSERT INTO sessioni_utente (user_id, session_id, client_ip_address, login_time)
                VALUES (%s, %s, %s, NOW())
            """
            try:
                db_manager.execute_query(log_session_query, (user_id, session_id, client_ip_address))
                db_manager.commit()
                logger.info(f"Utente '{username}' (ID: {user_id}) loggato con successo. Sessione: {session_id}")
                record_audit(db_manager, user_id, "LOGIN_SUCCESS", 
                             f"Utente {username} loggato.", "sessioni_utente", session_id, 
                             session_id=session_id, client_ip_address=client_ip_address, success=True)
                return user_id, role_id, session_id, "Login riuscito."
            except Exception as e:
                db_manager.rollback()
                logger.error(f"Errore durante la registrazione della sessione per l'utente '{username}': {e}", exc_info=True)
                # Nonostante l'errore di sessione, l'utente è autenticato. Potresti decidere di farlo procedere comunque.
                # Oppure considerarlo un fallimento del login. Per ora, lo consideriamo un fallimento.
                record_audit(db_manager, user_id, "LOGIN_FAIL", 
                             f"Errore registrazione sessione per utente {username}: {str(e)[:100]}", 
                             "sessioni_utente", client_ip_address=client_ip_address, success=False)
                return None, None, None, "Errore durante la registrazione della sessione."
        else:
            logger.warning(f"Tentativo di login fallito per l'utente '{username}': password errata.")
            record_audit(db_manager, user_data['id'], "LOGIN_FAIL", 
                         f"Password errata per utente {username}.", "utenti", user_data['id'], 
                         client_ip_address=client_ip_address, success=False)
            return None, None, None, "Username o password non validi."
    else:
        logger.warning(f"Tentativo di login fallito: utente '{username}' non trovato.")
        # Non registrare audit per utente non trovato per non rivelare l'esistenza di username
        return None, None, None, "Username o password non validi."


def logout_user_service(db_manager, user_id, session_id, client_ip_address=None):
    """Effettua il logout di un utente aggiornando la sessione."""
    logger.info(f"Tentativo di logout per l'utente ID: {user_id}, Sessione: {session_id}")
    query = "UPDATE sessioni_utente SET logout_time = NOW() WHERE session_id = %s AND user_id = %s AND logout_time IS NULL"
    try:
        db_manager.execute_query(query, (session_id, user_id))
        # Qui `execute_query` potrebbe restituire il numero di righe aggiornate se modificato per farlo.
        # Per ora assumiamo che se non ci sono errori, è andato a buon fine.
        db_manager.commit()
        logger.info(f"Utente ID: {user_id} sloggato con successo per la sessione: {session_id}")
        record_audit(db_manager, user_id, "LOGOUT_SUCCESS", 
                     f"Utente ID {user_id} sloggato.", "sessioni_utente", session_id, 
                     session_id=session_id, client_ip_address=client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore durante il logout per l'utente ID: {user_id}, Sessione: {session_id}: {e}", exc_info=True)
        record_audit(db_manager, user_id, "LOGOUT_FAIL", 
                     f"Errore logout utente ID {user_id}: {str(e)[:100]}", "sessioni_utente", session_id, 
                     session_id=session_id, client_ip_address=client_ip_address, success=False)
        return False

def get_user_roles_service(db_manager):
    """Recupera tutti i ruoli utente disponibili."""
    logger.debug("Recupero lista ruoli utente.")
    query = "SELECT id, nome_ruolo, descrizione FROM ruoli_utente ORDER BY nome_ruolo"
    try:
        roles = db_manager.execute_query(query, fetch_all=True)
        logger.debug(f"Trovati {len(roles) if roles else 0} ruoli.")
        return roles
    except Exception as e:
        logger.error(f"Errore durante il recupero dei ruoli utente: {e}", exc_info=True)
        return []

def get_users_service(db_manager):
    """Recupera una lista di tutti gli utenti (informazioni limitate)."""
    logger.debug("Recupero lista utenti.")
    query = """
        SELECT u.id, u.username, u.email, r.nome_ruolo, u.is_active, u.created_at, u.last_login 
        FROM utenti u
        JOIN ruoli_utente r ON u.role_id = r.id
        ORDER BY u.username
    """
    try:
        users = db_manager.execute_query(query, fetch_all=True)
        logger.debug(f"Trovati {len(users) if users else 0} utenti.")
        return users
    except Exception as e:
        logger.error(f"Errore durante il recupero degli utenti: {e}", exc_info=True)
        return []

# Potresti aggiungere qui altre funzioni di gestione utenti, come:
# - update_user_profile
# - change_user_password (per utenti loggati)
# - admin_reset_user_password
# - activate_deactivate_user
# - manage_user_roles (se un utente può avere più ruoli o se i ruoli possono essere cambiati)