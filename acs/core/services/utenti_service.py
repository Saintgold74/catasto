# core/services/utenti_service.py
import bcrypt
import logging
from uuid import uuid4
from datetime import datetime, timezone # Assicurati che timezone sia importato
from typing import Union, Optional, List, Dict, Any

# Import per SQLAlchemy
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError # Per gestire errori specifici

# Importa i modelli SQLAlchemy
from core.models import Utente, RuoloUtente, SessioneUtente # Assicurati che i modelli siano corretti

# Importa il servizio di audit (presumendo adattato per SQLAlchemy)
from .audit_service import record_audit

logger = logging.getLogger("CatastoAppLogger.UtentiService")

# --- Funzioni di Hashing Password (Invariate) ---
def hash_password(plain_password: str) -> bytes:
    if not plain_password:
        raise ValueError("La password non può essere vuota.")
    password_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    return hashed_password

def verify_password(plain_password: str, hashed_password_from_db: Union[str, bytes]) -> bool:
    if not plain_password or not hashed_password_from_db:
        return False
    password_bytes = plain_password.encode('utf-8')
    if isinstance(hashed_password_from_db, str):
        try:
            hashed_password_bytes = hashed_password_from_db.encode('latin-1')
        except UnicodeEncodeError:
            logger.error("Impossibile encodare l'hash della password (stringa) in bytes con latin-1.")
            return False
    elif isinstance(hashed_password_from_db, bytes):
        hashed_password_bytes = hashed_password_from_db
    else:
        logger.error(f"Formato hash password non valido: {type(hashed_password_from_db)}")
        return False
    try:
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)
    except ValueError as ve:
        logger.warning(f"Errore durante la verifica della password (possibile hash non valido): {ve}")
        return False
    except Exception as e:
        logger.error(f"Errore imprevisto durante bcrypt.checkpw: {e}")
        return False

# --- Servizi Utente (RISCRITTI CON SQLAlchemy) ---

def register_user_service(
    db: Session,
    username: str,
    plain_password: str,
    email: str,
    role_id: int,
    nome_completo: str,
    client_ip_address: Optional[str] = None,
    created_by_user_id: Optional[int] = None # Per admin creation, altrimenti self-registration
) -> tuple[Optional[int], str]:
    """Registra un nuovo utente nel sistema usando SQLAlchemy."""
    logger.info(f"Tentativo di registrazione SQLAlchemy per l'utente: {username}")
    audit_user_for_fail = created_by_user_id

    try:
        # 1. Controlla se l'username o l'email esistono già
        existing_user = db.query(Utente).filter(
            (Utente.username == username) | (Utente.email == email)
        ).first()
        
        if existing_user:
            msg = ""
            if existing_user.username == username:
                msg = f"Username '{username}' già esistente."
            elif existing_user.email == email:
                msg = f"Email '{email}' già esistente."
            logger.warning(msg)
            record_audit(db, audit_user_for_fail, None, client_ip_address, 
                         "REGISTER_USER_FAIL", "utenti", None, msg, False)
            return None, msg

        hashed_pw_bytes = hash_password(plain_password)
        hashed_pw_str_for_db = hashed_pw_bytes.decode('latin-1')

        nuovo_utente = Utente(
            username=username,
            password_hash=hashed_pw_str_for_db,
            email=email,
            role_id=role_id,
            nome_completo=nome_completo,
            is_active=True # Default per nuovi utenti
            # created_at e updated_at hanno server_default nel modello
        )
        db.add(nuovo_utente)
        db.commit()
        db.refresh(nuovo_utente)
        
        user_id = nuovo_utente.id
        logger.info(f"Utente '{username}' (ID: {user_id}) registrato con successo (SQLAlchemy).")
        
        audit_user_for_success = created_by_user_id if created_by_user_id is not None else user_id
        record_audit(db, audit_user_for_success, None, client_ip_address,
                     "REGISTER_USER_SUCCESS", "utenti", user_id, f"Utente {username} (ID: {user_id}) registrato.", True)
        return user_id, "Registrazione completata con successo."
            
    except IntegrityError as ie:
        db.rollback()
        logger.error(f"Errore di integrità durante registrazione utente {username}: {ie.orig}", exc_info=True)
        msg = "Errore durante la registrazione: un valore fornito è già in uso."
        if "utenti_username_key" in str(ie.orig).lower(): msg = f"Username '{username}' già esistente."
        elif "utenti_email_key" in str(ie.orig).lower(): msg = f"Email '{email}' già esistente."
        record_audit(db, audit_user_for_fail, None, client_ip_address,
                     "REGISTER_USER_FAIL", "utenti", None, msg, False)
        return None, msg
    except ValueError as ve: # Da hash_password
        logger.warning(f"Errore di validazione durante registrazione utente {username}: {ve}")
        record_audit(db, audit_user_for_fail, None, client_ip_address,
                     "REGISTER_USER_FAIL", "utenti", None, str(ve), False)
        return None, str(ve)
    except SQLAlchemyError as e_sql:
        db.rollback()
        logger.error(f"Errore SQLAlchemy durante registrazione utente {username}: {e_sql}", exc_info=True)
        record_audit(db, audit_user_for_fail, None, client_ip_address,
                     "REGISTER_USER_FAIL", "utenti", None, f"Errore DB: {str(e_sql)[:100]}", False)
        return None, "Errore database durante la registrazione."
    except Exception as e:
        db.rollback()
        logger.error(f"Errore critico durante registrazione utente '{username}': {e}", exc_info=True)
        record_audit(db, audit_user_for_fail, None, client_ip_address,
                     "REGISTER_USER_FAIL", "utenti", None, f"Errore critico: {str(e)[:200]}", False)
        return None, "Errore imprevisto durante la registrazione."

def login_user_service(
    db: Session,
    username: str,
    plain_password: str,
    client_ip_address: Optional[str] = None
) -> tuple[Optional[int], Optional[int], Optional[str], str]:
    logger.info(f"Tentativo di login SQLAlchemy per l'utente: {username}")
    audit_user_id_on_fail: Optional[int] = None
    try:
        utente_obj = db.query(Utente).filter(Utente.username == username).first()

        if utente_obj and utente_obj.is_active:
            audit_user_id_on_fail = utente_obj.id
            if verify_password(plain_password, utente_obj.password_hash):
                user_id = utente_obj.id
                role_id = utente_obj.role_id
                session_id_str = str(uuid4())

                utente_obj.last_login = datetime.now(timezone.utc) # Usare UTC per consistenza

                nuova_sessione = SessioneUtente(
                    user_id=user_id,
                    session_id=session_id_str,
                    client_ip_address=client_ip_address
                    # login_time ha server_default
                )
                db.add(nuova_sessione)
                db.commit()
                
                logger.info(f"Utente '{username}' (ID: {user_id}) loggato (SQLAlchemy). Sessione: {session_id_str}")
                record_audit(db, user_id, session_id_str, client_ip_address,
                             "LOGIN_SUCCESS", "utenti", user_id, f"Utente {username} loggato.", True)
                return user_id, role_id, session_id_str, "Login effettuato con successo."
            else:
                logger.warning(f"Password errata per utente (SQLAlchemy): {username}")
                record_audit(db, audit_user_id_on_fail, None, client_ip_address,
                             "LOGIN_FAIL", "utenti", audit_user_id_on_fail, f"Password errata per utente {username}.", False)
                return None, None, None, "Username o password non validi."
        elif utente_obj and not utente_obj.is_active:
            audit_user_id_on_fail = utente_obj.id
            logger.warning(f"Tentativo login SQLAlchemy per utente disattivato: {username}")
            record_audit(db, audit_user_id_on_fail, None, client_ip_address,
                         "LOGIN_FAIL", "utenti", audit_user_id_on_fail, f"Tentativo login utente disattivato {username}.", False)
            return None, None, None, "Account utente disattivato."
        else:
            logger.warning(f"Utente non trovato (SQLAlchemy): {username}")
            record_audit(db, None, None, client_ip_address,
                         "LOGIN_FAIL", "utenti", None, f"Utente non trovato: {username}.", False)
            return None, None, None, "Username o password non validi."
    except SQLAlchemyError as e_sql:
        db.rollback()
        logger.error(f"Errore SQLAlchemy login utente {username}: {e_sql}", exc_info=True)
        record_audit(db, audit_user_id_on_fail, None, client_ip_address, "LOGIN_FAIL", 
                     "utenti", audit_user_id_on_fail, f"Errore DB login: {str(e_sql)[:100]}", False)
        return None, None, None, "Errore database durante il login. Riprova più tardi."
    except Exception as e_generic:
        db.rollback()
        logger.error(f"Errore generico login SQLAlchemy per {username}: {e_generic}", exc_info=True)
        record_audit(db, audit_user_id_on_fail, None, client_ip_address, "LOGIN_FAIL", 
                     "utenti", audit_user_id_on_fail, f"Errore generico login: {str(e_generic)[:100]}", False)
        return None, None, None, "Errore imprevisto durante il login. Riprova più tardi."

def logout_user_service(
    db: Session,
    user_id: int,
    session_id: str,
    client_ip_address: Optional[str] = None
) -> bool:
    """Effettua il logout dell'utente aggiornando il logout_time nella sessione SQLAlchemy."""
    logger.info(f"Tentativo logout SQLAlchemy per utente ID: {user_id}, Sessione: {session_id}")
    try:
        session_obj = db.query(SessioneUtente).filter(
            SessioneUtente.user_id == user_id,
            SessioneUtente.session_id == session_id,
            SessioneUtente.logout_time == None # Cerca sessione attiva
        ).first()

        if session_obj:
            session_obj.logout_time = datetime.now(timezone.utc) # Usare UTC
            db.commit()
            logger.info(f"Logout utente ID {user_id}, Sessione {session_id} registrato (SQLAlchemy).")
            record_audit(db, user_id, session_id, client_ip_address,
                         "LOGOUT_SUCCESS", "sessioni_utente", session_id, "Logout effettuato.", True)
            return True
        else:
            logger.warning(f"Nessuna sessione attiva trovata per logout utente ID {user_id}, Sessione {session_id}.")
            record_audit(db, user_id, session_id, client_ip_address,
                         "LOGOUT_NO_SESSION", "sessioni_utente", session_id, "Sessione non attiva/trovata per logout.", False)
            return False
    except SQLAlchemyError as e_sql:
        db.rollback()
        logger.error(f"Errore SQLAlchemy logout utente ID {user_id}: {e_sql}", exc_info=True)
        record_audit(db, user_id, session_id, client_ip_address,
                     "LOGOUT_FAIL", "sessioni_utente", session_id, f"Errore logout: {str(e_sql)[:100]}", False)
        return False
    except Exception as e_generic:
        db.rollback()
        logger.error(f"Errore generico logout utente ID {user_id}: {e_generic}", exc_info=True)
        record_audit(db, user_id, session_id, client_ip_address,
                     "LOGOUT_FAIL", "sessioni_utente", session_id, f"Errore generico logout: {str(e_generic)[:100]}", False)
        return False

def get_users_service(db: Session) -> List[Dict[str, Any]]:
    """Recupera lista utenti con nome ruolo usando SQLAlchemy."""
    logger.info("Recupero lista utenti con ruoli (SQLAlchemy)...")
    try:
        utenti_con_ruolo = db.query(
            Utente.id, Utente.username, Utente.email, Utente.nome_completo,
            Utente.is_active, Utente.last_login, Utente.created_at,
            RuoloUtente.nome_ruolo
        ).join(RuoloUtente, Utente.role_id == RuoloUtente.id).order_by(Utente.username).all()
        
        return [
            {
                "id": u.id, "username": u.username, "email": u.email,
                "nome_completo": u.nome_completo, "is_active": u.is_active,
                "last_login": u.last_login, "created_at": u.created_at,
                "nome_ruolo": u.nome_ruolo
            } for u in utenti_con_ruolo
        ]
    except SQLAlchemyError as e:
        logger.error(f"Errore SQLAlchemy recupero lista utenti: {e}", exc_info=True)
        return []

def get_user_roles_service(db: Session) -> List[Dict[str, Any]]:
    """Recupera tutti i ruoli utente disponibili usando SQLAlchemy."""
    logger.info("Recupero ruoli utente (SQLAlchemy)...")
    try:
        ruoli = db.query(RuoloUtente).order_by(RuoloUtente.nome_ruolo).all()
        return [{"id": r.id, "nome_ruolo": r.nome_ruolo, "descrizione": r.descrizione} for r in ruoli]
    except SQLAlchemyError as e:
        logger.error(f"Errore SQLAlchemy recupero ruoli utente: {e}", exc_info=True)
        return []

def get_user_by_id_service(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """Recupera dettagli utente per ID, con nome ruolo, usando SQLAlchemy."""
    logger.info(f"Recupero utente ID {user_id} con ruolo (SQLAlchemy)...")
    try:
        user_data = db.query(
            Utente.id, Utente.username, Utente.email, Utente.nome_completo,
            Utente.is_active, Utente.last_login, Utente.created_at, Utente.updated_at,
            Utente.role_id, RuoloUtente.nome_ruolo
        ).join(RuoloUtente, Utente.role_id == RuoloUtente.id).filter(Utente.id == user_id).first()
        
        if user_data:
            return {
                "id": user_data.id, "username": user_data.username, "email": user_data.email,
                "nome_completo": user_data.nome_completo, "is_active": user_data.is_active,
                "last_login": user_data.last_login, "created_at": user_data.created_at,
                "updated_at": user_data.updated_at, "role_id": user_data.role_id,
                "nome_ruolo": user_data.nome_ruolo
            }
        logger.warning(f"Nessun utente trovato con ID (SQLAlchemy): {user_id}")
        return None
    except SQLAlchemyError as e:
        logger.error(f"Errore SQLAlchemy recupero utente ID {user_id}: {e}", exc_info=True)
        return None

def update_user_service(
    db: Session,
    user_id_to_update: int,
    data_to_update: Dict[str, Any],
    audit_user_id: Optional[int],
    audit_session_id: Optional[str],
    audit_client_ip: Optional[str]
) -> tuple[bool, str]:
    """Aggiorna dati utente (no password) usando SQLAlchemy."""
    logger.info(f"Tentativo aggiornamento SQLAlchemy utente ID {user_id_to_update} da utente ID {audit_user_id}")
    if not data_to_update:
        return False, "Nessun dato fornito per l'aggiornamento."

    allowed_fields = {'email', 'nome_completo', 'role_id', 'is_active'}
    fields_to_set_log = []
    
    try:
        utente_obj = db.query(Utente).filter(Utente.id == user_id_to_update).first()
        if not utente_obj:
            return False, f"Utente ID {user_id_to_update} non trovato."

        for field, value in data_to_update.items():
            if field in allowed_fields:
                if getattr(utente_obj, field) != value: # Applica solo se il valore è diverso
                    setattr(utente_obj, field, value)
                    fields_to_set_log.append(f"{field}='{value}'")
            elif field in ['password', 'password_hash']:
                logger.warning("Tentativo di aggiornare password tramite update_user_service. Ignorato.")
        
        if not fields_to_set_log:
            return True, "Nessuna modifica effettiva ai dati dell'utente." # Considerato successo

        utente_obj.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(utente_obj)
        
        log_msg = f"Utente ID {user_id_to_update} aggiornato. Modifiche: {', '.join(fields_to_set_log)}"
        logger.info(log_msg)
        record_audit(db, audit_user_id, audit_session_id, audit_client_ip,
                     "UPDATE_USER_SUCCESS", "utenti", user_id_to_update, log_msg, True)
        return True, "Utente aggiornato con successo."

    except IntegrityError as ie:
        db.rollback()
        msg = f"Errore di integrità: {ie.orig}"
        if "utenti_email_key" in str(ie.orig).lower() and 'email' in data_to_update : msg = f"Email '{data_to_update['email']}' già in uso."
        logger.error(f"Errore integrità SQLAlchemy aggiornamento utente {user_id_to_update}: {ie.orig}", exc_info=True)
        record_audit(db, audit_user_id, audit_session_id, audit_client_ip, "UPDATE_USER_FAIL", 
                     "utenti", user_id_to_update, msg, False)
        return False, msg
    except SQLAlchemyError as e_sql:
        db.rollback()
        logger.error(f"Errore SQLAlchemy aggiornamento utente {user_id_to_update}: {e_sql}", exc_info=True)
        record_audit(db, audit_user_id, audit_session_id, audit_client_ip, "UPDATE_USER_FAIL", 
                     "utenti", user_id_to_update, f"Errore DB: {str(e_sql)[:100]}", False)
        return False, "Errore database durante l'aggiornamento."
    except Exception as e:
        db.rollback()
        logger.error(f"Errore generico aggiornamento utente {user_id_to_update}: {e}", exc_info=True)
        record_audit(db, audit_user_id, audit_session_id, audit_client_ip, "UPDATE_USER_FAIL", 
                     "utenti", user_id_to_update, f"Errore generico: {str(e)[:100]}", False)
        return False, "Errore imprevisto durante l'aggiornamento."

def delete_user_service( # Soft delete
    db: Session,
    user_id_to_delete: int,
    audit_user_id: Optional[int], # Chi esegue l'azione
    audit_session_id: Optional[str],
    audit_client_ip: Optional[str]
) -> tuple[bool, str]:
    """Soft delete utente (imposta is_active=False) usando SQLAlchemy."""
    logger.info(f"Tentativo soft delete SQLAlchemy utente ID {user_id_to_delete} da utente ID {audit_user_id}")

    if user_id_to_delete == audit_user_id:
        msg = "Non è possibile disattivare il proprio account."
        logger.warning(msg + f" (Utente ID {audit_user_id})")
        record_audit(db, audit_user_id, audit_session_id, audit_client_ip, "DELETE_USER_FAIL",
                     "utenti", user_id_to_delete, "Tentativo di auto-disattivazione.", False)
        return False, msg
    
    # Aggiungi qui eventuali controlli per non disattivare admin speciali se necessario

    try:
        utente_obj = db.query(Utente).filter(Utente.id == user_id_to_delete).first()
        if not utente_obj:
            return False, f"Utente ID {user_id_to_delete} non trovato."
        
        if not utente_obj.is_active:
            return True, f"Utente ID {user_id_to_delete} è già inattivo." # Considerato successo

        utente_obj.is_active = False
        utente_obj.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(utente_obj)
        
        log_msg = f"Utente ID {user_id_to_delete} disattivato (soft delete)."
        logger.info(log_msg)
        record_audit(db, audit_user_id, audit_session_id, audit_client_ip,
                     "DELETE_USER_SUCCESS", "utenti", user_id_to_delete, log_msg, True)
        return True, "Utente disattivato con successo."

    except SQLAlchemyError as e_sql:
        db.rollback()
        logger.error(f"Errore SQLAlchemy soft delete utente {user_id_to_delete}: {e_sql}", exc_info=True)
        record_audit(db, audit_user_id, audit_session_id, audit_client_ip, "DELETE_USER_FAIL",
                     "utenti", user_id_to_delete, f"Errore DB: {str(e_sql)[:100]}", False)
        return False, "Errore database durante la disattivazione."
    except Exception as e:
        db.rollback()
        logger.error(f"Errore generico soft delete utente {user_id_to_delete}: {e}", exc_info=True)
        record_audit(db, audit_user_id, audit_session_id, audit_client_ip, "DELETE_USER_FAIL",
                     "utenti", user_id_to_delete, f"Errore generico: {str(e)[:100]}", False)
        return False, "Errore imprevisto durante la disattivazione."

def change_password_service(
    db: Session,
    user_id: int, # L'ID dell'utente che sta cambiando la propria password
    old_plain_password: str,
    new_plain_password: str,
    audit_session_id: Optional[str], # session_id dell'utente che cambia la password
    audit_client_ip: Optional[str]
) -> tuple[bool, str]:
    """Permette a un utente di cambiare la propria password usando SQLAlchemy."""
    logger.info(f"Tentativo cambio password SQLAlchemy per utente ID: {user_id}")

    if not old_plain_password or not new_plain_password:
        return False, "La vecchia e la nuova password non possono essere vuote."
    if new_plain_password == old_plain_password:
        return False, "La nuova password deve essere diversa da quella vecchia."
    # Aggiungi qui validazioni di complessità per new_plain_password se necessario

    try:
        utente_obj = db.query(Utente).filter(Utente.id == user_id).first()
        if not utente_obj:
            return False, f"Utente ID {user_id} non trovato."
        if not utente_obj.is_active:
            return False, "Account utente disattivato."

        if not verify_password(old_plain_password, utente_obj.password_hash):
            logger.warning(f"Vecchia password errata per cambio password utente ID {user_id}.")
            record_audit(db, user_id, audit_session_id, audit_client_ip, "CHANGE_PASSWORD_FAIL",
                         "utenti", user_id, "Vecchia password errata.", False)
            return False, "La vecchia password fornita non è corretta."

        hashed_pw_bytes = hash_password(new_plain_password)
        utente_obj.password_hash = hashed_pw_bytes.decode('latin-1')
        utente_obj.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        log_msg = f"Password per utente ID {user_id} cambiata con successo."
        logger.info(log_msg)
        record_audit(db, user_id, audit_session_id, audit_client_ip, "CHANGE_PASSWORD_SUCCESS",
                     "utenti", user_id, log_msg, True)
        return True, "Password cambiata con successo."

    except ValueError as ve: # Da hash_password
        return False, str(ve)
    except SQLAlchemyError as e_sql:
        db.rollback()
        logger.error(f"Errore SQLAlchemy cambio password utente {user_id}: {e_sql}", exc_info=True)
        record_audit(db, user_id, audit_session_id, audit_client_ip, "CHANGE_PASSWORD_FAIL",
                     "utenti", user_id, f"Errore DB: {str(e_sql)[:100]}", False)
        return False, "Errore database durante il cambio password."
    except Exception as e:
        db.rollback()
        logger.error(f"Errore generico cambio password utente {user_id}: {e}", exc_info=True)
        record_audit(db, user_id, audit_session_id, audit_client_ip, "CHANGE_PASSWORD_FAIL",
                     "utenti", user_id, f"Errore generico: {str(e)[:100]}", False)
        return False, "Errore imprevisto durante il cambio password."


def admin_reset_password_service(
    db: Session,
    user_id_to_reset: int,
    new_plain_password: str,
    admin_user_id: int, # Chi esegue l'azione
    admin_session_id: Optional[str],
    admin_client_ip: Optional[str]
) -> tuple[bool, str]:
    """Permette a un admin di resettare la password di un utente usando SQLAlchemy."""
    logger.info(f"Admin ID {admin_user_id} tenta reset password SQLAlchemy per utente ID {user_id_to_reset}")

    # Verifica se l'esecutore è un admin (presumendo che admin abbia role_id specifico, es. 1)
    # Questa logica di verifica ruolo dovrebbe essere robusta
    admin_obj = db.query(Utente).filter(Utente.id == admin_user_id, Utente.is_active == True).first()
    if not admin_obj or admin_obj.role_id != 1: # Assumendo ADMIN_ROLE_ID = 1
        logger.warning(f"Tentativo non autorizzato di reset password da utente ID {admin_user_id}.")
        return False, "Operazione non autorizzata (permessi admin richiesti)."
    
    if user_id_to_reset == admin_user_id:
        return False, "L'admin deve usare 'cambia la mia password' per il proprio account."
    if not new_plain_password:
        return False, "La nuova password non può essere vuota."

    try:
        utente_obj = db.query(Utente).filter(Utente.id == user_id_to_reset).first()
        if not utente_obj:
            return False, f"Utente ID {user_id_to_reset} da resettare non trovato."
        
        # Non è necessario controllare is_active dell'utente target, un admin potrebbe resettarla apposta

        hashed_pw_bytes = hash_password(new_plain_password)
        utente_obj.password_hash = hashed_pw_bytes.decode('latin-1')
        utente_obj.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        log_msg = f"Password per utente ID {user_id_to_reset} resettata da admin ID {admin_user_id}."
        logger.info(log_msg)
        record_audit(db, admin_user_id, admin_session_id, admin_client_ip,
                     "ADMIN_RESET_PASSWORD_SUCCESS", "utenti", user_id_to_reset, log_msg, True)
        return True, "Password resettata con successo."

    except ValueError as ve: # Da hash_password
        return False, str(ve)
    except SQLAlchemyError as e_sql:
        db.rollback()
        logger.error(f"Errore SQLAlchemy admin reset password utente {user_id_to_reset}: {e_sql}", exc_info=True)
        record_audit(db, admin_user_id, admin_session_id, admin_client_ip, "ADMIN_RESET_PASSWORD_FAIL",
                     "utenti", user_id_to_reset, f"Errore DB: {str(e_sql)[:100]}", False)
        return False, "Errore database durante il reset password."
    except Exception as e:
        db.rollback()
        logger.error(f"Errore generico admin reset password utente {user_id_to_reset}: {e}", exc_info=True)
        record_audit(db, admin_user_id, admin_session_id, admin_client_ip, "ADMIN_RESET_PASSWORD_FAIL",
                     "utenti", user_id_to_reset, f"Errore generico: {str(e)[:100]}", False)
        return False, "Errore imprevisto durante il reset password."