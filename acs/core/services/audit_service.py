# core/services/audit_service.py
import logging
from datetime import datetime, timezone # Assicurati che timezone sia importato se usi aware datetime
from typing import Optional, Any

# Importa il modello AuditLog e la Session SQLAlchemy
from sqlalchemy.orm import Session
from core.models import AuditLog # Assumendo che AuditLog sia definito in core/models.py

logger = logging.getLogger("CatastoAppLogger.AuditService")

def record_audit(
    db: Session, # Modificato: accetta una sessione SQLAlchemy
    user_id: Optional[int],
    session_id: Optional[str],
    client_ip_address: Optional[str],
    action: str,
    table_name: Optional[str] = None,
    record_id: Optional[Any] = None,
    details: Optional[str] = None,
    success: bool = True
):
    """Registra un evento di audit nel database usando SQLAlchemy."""

    record_id_str = str(record_id) if record_id is not None else None

    try:
        # Crea un'istanza del modello AuditLog
        # Assicurati che i nomi dei campi corrispondano al tuo modello AuditLog
        # e alla tabella audit_log nel DB (user_id, client_ip_address, action, table_name, record_id)
        audit_entry = AuditLog(
            user_id=user_id, # Corrisponde a AuditLog.user_id nel modello
            session_id=session_id,
            client_ip_address=client_ip_address,
            action=action, # Corrisponde a AuditLog.action
            table_name=table_name, # Corrisponde a AuditLog.table_name
            record_id=record_id_str, # Corrisponde a AuditLog.record_id
            details=details,
            success=success
            # timestamp ha server_default nel modello AuditLog
        )
        db.add(audit_entry)
        # Il commit NON dovrebbe essere fatto qui.
        # L'audit dovrebbe far parte della transazione del servizio chiamante.
        # Se il servizio chiamante fa rollback, anche l'audit verrà annullato.
        # Se il servizio chiamante fa commit, l'audit verrà salvato insieme.
        # db.commit() # Rimuovi o commenta questo commit

        # Non loggare qui il successo dell'audit per evitare loop,
        # a meno che non sia un logging molto specifico.
    except SQLAlchemyError as e_sql:
        # È importante non far fallire l'operazione principale a causa di un errore di audit.
        # Potresti anche decidere di non fare db.rollback() qui per non impattare
        # la transazione principale se l'audit è considerato "best-effort".
        logger.error(f"FALLIMENTO REGISTRAZIONE AUDIT (SQLAlchemy): User {user_id}, Azione '{action}'. Errore: {e_sql}", exc_info=True)
    except Exception as e_generic:
        logger.error(f"Errore generico in record_audit (SQLAlchemy): {e_generic}", exc_info=True)