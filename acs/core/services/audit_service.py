# core/services/audit_service.py
import logging
from datetime import datetime

# Ottieni un logger specifico per questo modulo
logger = logging.getLogger("CatastoAppLogger.AuditService")

def record_audit(db_manager, user_id: int, action: str, details: str = "", 
                 table_name: str = None, record_id: any = None, 
                 session_id: str = None, client_ip_address: str = None, success: bool = True):
    """
    Registra un evento di audit nel database.
    """
    query = """
        INSERT INTO audit_log (user_id, session_id, client_ip_address, action_performed, 
                               table_name_affected, record_id_affected, details, success, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    # Converti record_id in stringa se è un intero, per coerenza o se il campo DB è testuale
    if record_id is not None and not isinstance(record_id, str):
        record_id_str = str(record_id)
    else:
        record_id_str = record_id

    try:
        db_manager.execute_query(query, (
            user_id, session_id, client_ip_address, action, 
            table_name, record_id_str, details, success, datetime.now()
        ))
        db_manager.commit() # L'audit log spesso si auto-committa
        logger.info(f"Audit registrato: User {user_id}, Azione '{action}', Successo: {success}, Dettagli: {details[:100]}")
    except Exception as e:
        # Non far fallire l'operazione principale per un errore di audit
        logger.error(f"FALLIMENTO REGISTRAZIONE AUDIT: User {user_id}, Azione '{action}'. Errore: {e}", exc_info=True)
        # Non fare rollback qui, potrebbe annullare l'operazione principale