import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Importa i modelli SQLAlchemy necessari
from core.models import (
    Comune,
    Sezione,
    TipoDocumento,
    TipoImmobile,
    TipoPossesso,
    TipoVariazione
)
# Importa la funzione di audit (presumendo che sarà adattata)
# from core.services.audit_service import record_audit

logger = logging.getLogger("CatastoAppLogger.AnagraficheService")

# === Funzioni di Servizio per COMUNI ===

def get_comuni_service(db: Session) -> List[Dict[str, Any]]:
    """Recupera tutti i comuni, ordinati per nome."""
    logger.info("Recupero lista comuni tramite SQLAlchemy.")
    try:
        comuni_obj = db.query(Comune).order_by(Comune.nome).all()
        return [
            {
                "id": c.id,
                "nome": c.nome,
                "provincia": c.provincia,
                "regione": c.regione,
                "data_creazione": c.data_creazione,
                "data_modifica": c.data_modifica,
            }
            for c in comuni_obj
        ]
    except SQLAlchemyError as e:
        logger.error(f"Errore SQLAlchemy durante il recupero dei comuni: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Errore generico durante il recupero dei comuni: {e}", exc_info=True)
        return []

def get_comune_by_id_service(db: Session, comune_id: int) -> Optional[Dict[str, Any]]:
    """Recupera un comune specifico per ID."""
    logger.info(f"Recupero comune ID {comune_id} tramite SQLAlchemy.")
    try:
        comune_obj = db.query(Comune).filter(Comune.id == comune_id).first()
        if comune_obj:
            return {
                "id": comune_obj.id,
                "nome": comune_obj.nome,
                "provincia": comune_obj.provincia,
                "regione": comune_obj.regione,
                "data_creazione": comune_obj.data_creazione,
                "data_modifica": comune_obj.data_modifica,
            }
        return None
    except SQLAlchemyError as e:
        logger.error(f"Errore SQLAlchemy durante il recupero del comune ID {comune_id}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Errore generico durante il recupero del comune ID {comune_id}: {e}", exc_info=True)
        return None

def create_comune_service(
    db: Session,
    nome: str,
    provincia: str,
    regione: str,
    audit_user_id: Optional[int],
    audit_session_id: Optional[str],
    audit_client_ip: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Crea un nuovo comune."""
    logger.info(f"Tentativo creazione comune '{nome}' tramite SQLAlchemy.")
    try:
        # Verifica se esiste già un comune con lo stesso nome (UNIQUE constraint)
        existing_comune = db.query(Comune).filter(Comune.nome == nome).first()
        if existing_comune:
            logger.warning(f"Comune con nome '{nome}' esiste già (ID: {existing_comune.id}).")
            # Non registrare audit di fallimento qui, la logica chiamante potrebbe gestirlo
            return {"error": f"Comune con nome '{nome}' esiste già.", "id": existing_comune.id}

        nuovo_comune = Comune(nome=nome, provincia=provincia, regione=regione)
        db.add(nuovo_comune)
        db.commit()
        db.refresh(nuovo_comune)
        logger.info(f"Comune '{nome}' creato con ID {nuovo_comune.id}.")
        
        # record_audit(db, audit_user_id, audit_session_id, audit_client_ip,
        #              action="CREATE_COMUNE", table_name="comune", record_id=nuovo_comune.id,
        #              details=f"Creato comune: {nome}", success=True)
                     
        return get_comune_by_id_service(db, nuovo_comune.id) # Restituisce il dizionario completo
    except IntegrityError as e: # Cattura errori di violazione dei vincoli (es. UNIQUE)
        db.rollback()
        logger.error(f"Errore di integrità SQLAlchemy durante la creazione del comune '{nome}': {e}", exc_info=True)
        # record_audit(db, audit_user_id, audit_session_id, audit_client_ip,
        #              action="CREATE_COMUNE_FAIL", table_name="comune",
        #              details=f"Errore integrità creazione comune {nome}: {e.orig}", success=False)
        return {"error": f"Errore di integrità: {e.orig}"} # e.orig contiene l'errore del DB driver
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Errore SQLAlchemy durante la creazione del comune '{nome}': {e}", exc_info=True)
        # record_audit(db, audit_user_id, audit_session_id, audit_client_ip,
        #              action="CREATE_COMUNE_FAIL", table_name="comune",
        #              details=f"Errore SQLAlchemy creazione comune {nome}: {str(e)}", success=False)
        return {"error": "Errore database durante la creazione del comune."}
    except Exception as e:
        db.rollback()
        logger.error(f"Errore generico durante la creazione del comune '{nome}': {e}", exc_info=True)
        # record_audit(...)
        return {"error": "Errore generico durante la creazione del comune."}


def update_comune_service(
    db: Session,
    comune_id: int,
    data_to_update: Dict[str, Any],
    audit_user_id: Optional[int],
    audit_session_id: Optional[str],
    audit_client_ip: Optional[str],
) -> bool:
    """Aggiorna un comune esistente."""
    logger.info(f"Tentativo aggiornamento comune ID {comune_id} tramite SQLAlchemy.")
    try:
        comune_obj = db.query(Comune).filter(Comune.id == comune_id).first()
        if not comune_obj:
            logger.warning(f"Comune ID {comune_id} non trovato per aggiornamento.")
            return False

        updated_fields_log = []
        for key, value in data_to_update.items():
            if hasattr(comune_obj, key) and getattr(comune_obj, key) != value:
                setattr(comune_obj, key, value)
                updated_fields_log.append(f"{key}='{value}'")
        
        if not updated_fields_log:
            logger.info(f"Nessuna modifica effettiva per comune ID {comune_id}.")
            return True # O False se si vuole indicare "nessuna modifica"

        db.commit()
        db.refresh(comune_obj) # Opzionale, per avere l'oggetto aggiornato con eventuali trigger/default DB
        logger.info(f"Comune ID {comune_obj.id} ('{comune_obj.nome}') aggiornato. Modifiche: {', '.join(updated_fields_log)}")
        
        # record_audit(db, audit_user_id, audit_session_id, audit_client_ip,
        #              action="UPDATE_COMUNE", table_name="comune", record_id=comune_id,
        #              details=f"Aggiornato comune {comune_obj.nome}. Modifiche: {', '.join(updated_fields_log)}", success=True)
        return True
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Errore di integrità SQLAlchemy durante aggiornamento comune ID {comune_id}: {e}", exc_info=True)
        # record_audit(...)
        # Potresti voler restituire un messaggio d'errore più specifico
        raise # Rilancia per farla gestire dal chiamante se necessario
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Errore SQLAlchemy durante aggiornamento comune ID {comune_id}: {e}", exc_info=True)
        # record_audit(...)
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Errore generico durante aggiornamento comune ID {comune_id}: {e}", exc_info=True)
        # record_audit(...)
        return False

def delete_comune_service(
    db: Session,
    comune_id: int,
    audit_user_id: Optional[int],
    audit_session_id: Optional[str],
    audit_client_ip: Optional[str],
) -> bool:
    """Cancella un comune (verificare se ci sono dipendenze come Sezioni o Partite prima di cancellare)."""
    logger.info(f"Tentativo cancellazione comune ID {comune_id} tramite SQLAlchemy.")
    try:
        comune_obj = db.query(Comune).filter(Comune.id == comune_id).first()
        if not comune_obj:
            logger.warning(f"Comune ID {comune_id} non trovato per cancellazione.")
            return False

        # CONTROLLO DIPENDENZE:
        # Prima di cancellare un comune, verifica se ci sono sezioni o altre entità collegate.
        # Questa logica dipende da come hai definito le relazioni e le regole di cancellazione (ON DELETE).
        # Esempio: se ci sono sezioni che impediscono la cancellazione (es. FK senza ON DELETE CASCADE)
        sezioni_collegate = db.query(Sezione).filter(Sezione.comune_id == comune_id).count()
        if sezioni_collegate > 0:
            logger.warning(f"Impossibile cancellare comune ID {comune_id} perché ha {sezioni_collegate} sezioni collegate.")
            # record_audit(db, audit_user_id, audit_session_id, audit_client_ip,
            #              action="DELETE_COMUNE_FAIL", table_name="comune", record_id=comune_id,
            #              details=f"Tentativo cancellazione fallito: comune {comune_obj.nome} ha sezioni collegate.", success=False)
            raise ValueError(f"Impossibile cancellare il comune '{comune_obj.nome}' perché ha sezioni collegate.")

        nome_comune_cancellato = comune_obj.nome
        db.delete(comune_obj)
        db.commit()
        logger.info(f"Comune '{nome_comune_cancellato}' (ID: {comune_id}) cancellato con successo.")
        # record_audit(db, audit_user_id, audit_session_id, audit_client_ip,
        #              action="DELETE_COMUNE", table_name="comune", record_id=comune_id,
        #              details=f"Cancellato comune: {nome_comune_cancellato}", success=True)
        return True
    except IntegrityError as e: # Potrebbe accadere se il DB ha FK che impediscono il delete non gestite prima
        db.rollback()
        logger.error(f"Errore di integrità SQLAlchemy durante cancellazione comune ID {comune_id}: {e}", exc_info=True)
        # record_audit(...)
        raise # Rilancia
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Errore SQLAlchemy durante cancellazione comune ID {comune_id}: {e}", exc_info=True)
        # record_audit(...)
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Errore generico durante cancellazione comune ID {comune_id}: {e}", exc_info=True)
        # record_audit(...)
        return False

# === Funzioni di Servizio per SEZIONI ===

def get_sezioni_service(db: Session, comune_id_filter: Optional[int] = None) -> List[Dict[str, Any]]:
    """Recupera le sezioni, opzionalmente filtrate per comune_id."""
    logger.info(f"Recupero sezioni (comune ID: {comune_id_filter}) tramite SQLAlchemy.")
    try:
        query = db.query(
            Sezione.id,
            Sezione.comune_id,
            Comune.nome.label("nome_comune"),
            Sezione.nome_sezione,
            Sezione.codice_sezione,
            Sezione.note,
            Sezione.data_creazione,
            Sezione.data_modifica
        ).join(Comune, Sezione.comune_id == Comune.id)

        if comune_id_filter is not None:
            query = query.filter(Sezione.comune_id == comune_id_filter)
        
        sezioni_rows = query.order_by(Sezione.nome_sezione).all()
        
        return [
            {
                "id": s.id, "comune_id": s.comune_id, "nome_comune": s.nome_comune,
                "nome_sezione": s.nome_sezione, "codice_sezione": s.codice_sezione,
                "note": s.note, "data_creazione": s.data_creazione, "data_modifica": s.data_modifica
            } for s in sezioni_rows
        ]
    except SQLAlchemyError as e:
        logger.error(f"Errore SQLAlchemy recupero sezioni: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Errore generico recupero sezioni: {e}", exc_info=True)
        return []

def get_sezione_by_id_service(db: Session, sezione_id: int) -> Optional[Dict[str, Any]]:
    """Recupera una sezione specifica per ID, includendo il nome del comune."""
    logger.info(f"Recupero sezione ID {sezione_id} tramite SQLAlchemy.")
    try:
        sezione_row = db.query(
            Sezione.id,
            Sezione.comune_id,
            Comune.nome.label("nome_comune"),
            Sezione.nome_sezione,
            Sezione.codice_sezione,
            Sezione.note,
            Sezione.data_creazione,
            Sezione.data_modifica
        ).join(Comune, Sezione.comune_id == Comune.id).filter(Sezione.id == sezione_id).first()
        
        if sezione_row:
            return {
                "id": sezione_row.id, "comune_id": sezione_row.comune_id, "nome_comune": sezione_row.nome_comune,
                "nome_sezione": sezione_row.nome_sezione, "codice_sezione": sezione_row.codice_sezione,
                "note": sezione_row.note, "data_creazione": sezione_row.data_creazione, "data_modifica": sezione_row.data_modifica
            }
        return None
    except SQLAlchemyError as e:
        logger.error(f"Errore SQLAlchemy recupero sezione ID {sezione_id}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Errore generico recupero sezione ID {sezione_id}: {e}", exc_info=True)
        return None

def create_sezione_service(
    db: Session,
    comune_id: int,
    nome_sezione: str,
    codice_sezione: Optional[str],
    note: Optional[str],
    audit_user_id: Optional[int],
    audit_session_id: Optional[str],
    audit_client_ip: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Crea una nuova sezione."""
    logger.info(f"Tentativo creazione sezione '{nome_sezione}' per comune ID {comune_id} tramite SQLAlchemy.")
    try:
        # Verifica unicità (comune_id, codice_sezione) se codice_sezione è fornito
        if codice_sezione:
            existing_sezione = db.query(Sezione).filter_by(comune_id=comune_id, codice_sezione=codice_sezione).first()
            if existing_sezione:
                msg = f"Sezione con codice '{codice_sezione}' esiste già per il comune ID {comune_id}."
                logger.warning(msg)
                return {"error": msg, "id": existing_sezione.id}
        
        # Potresti voler verificare anche l'unicità di (comune_id, nome_sezione) se necessario
        
        nuova_sezione = Sezione(
            comune_id=comune_id,
            nome_sezione=nome_sezione,
            codice_sezione=codice_sezione,
            note=note
        )
        db.add(nuova_sezione)
        db.commit()
        db.refresh(nuova_sezione)
        logger.info(f"Sezione '{nome_sezione}' creata con ID {nuova_sezione.id} per comune ID {comune_id}.")
        # record_audit(...)
        return get_sezione_by_id_service(db, nuova_sezione.id)
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Errore integrità SQLAlchemy creazione sezione '{nome_sezione}': {e}", exc_info=True)
        # record_audit(...)
        return {"error": f"Errore di integrità: {e.orig}"}
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Errore SQLAlchemy creazione sezione '{nome_sezione}': {e}", exc_info=True)
        # record_audit(...)
        return {"error": "Errore database durante la creazione della sezione."}
    except Exception as e:
        db.rollback()
        logger.error(f"Errore generico creazione sezione '{nome_sezione}': {e}", exc_info=True)
        # record_audit(...)
        return {"error": "Errore generico durante la creazione della sezione."}

def update_sezione_service(
    db: Session,
    sezione_id: int,
    data_to_update: Dict[str, Any],
    audit_user_id: Optional[int],
    audit_session_id: Optional[str],
    audit_client_ip: Optional[str],
) -> bool:
    """Aggiorna una sezione esistente."""
    logger.info(f"Tentativo aggiornamento sezione ID {sezione_id} tramite SQLAlchemy.")
    try:
        sezione_obj = db.query(Sezione).filter(Sezione.id == sezione_id).first()
        if not sezione_obj:
            logger.warning(f"Sezione ID {sezione_id} non trovata per aggiornamento.")
            return False

        updated_fields_log = []
        # Non permettere la modifica di comune_id tramite questo update semplice
        allowed_fields = {"nome_sezione", "codice_sezione", "note"}

        for key, value in data_to_update.items():
            if key in allowed_fields and hasattr(sezione_obj, key) and getattr(sezione_obj, key) != value:
                setattr(sezione_obj, key, value)
                updated_fields_log.append(f"{key}='{value}'")
        
        if not updated_fields_log:
            logger.info(f"Nessuna modifica effettiva per sezione ID {sezione_id}.")
            return True

        db.commit()
        db.refresh(sezione_obj)
        logger.info(f"Sezione ID {sezione_obj.id} ('{sezione_obj.nome_sezione}') aggiornata. Modifiche: {', '.join(updated_fields_log)}")
        # record_audit(...)
        return True
    except IntegrityError as e: # Es. se si viola UNIQUE(comune_id, codice_sezione)
        db.rollback()
        logger.error(f"Errore integrità SQLAlchemy aggiornamento sezione ID {sezione_id}: {e}", exc_info=True)
        # record_audit(...)
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Errore SQLAlchemy aggiornamento sezione ID {sezione_id}: {e}", exc_info=True)
        # record_audit(...)
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Errore generico aggiornamento sezione ID {sezione_id}: {e}", exc_info=True)
        # record_audit(...)
        return False

def delete_sezione_service(
    db: Session,
    sezione_id: int,
    audit_user_id: Optional[int],
    audit_session_id: Optional[str],
    audit_client_ip: Optional[str],
) -> bool:
    """Cancella una sezione."""
    logger.info(f"Tentativo cancellazione sezione ID {sezione_id} tramite SQLAlchemy.")
    try:
        sezione_obj = db.query(Sezione).filter(Sezione.id == sezione_id).first()
        if not sezione_obj:
            logger.warning(f"Sezione ID {sezione_id} non trovata per cancellazione.")
            return False
        
        # CONTROLLO DIPENDENZE (es. immobili collegati a questa sezione)
        # if db.query(Immobile).filter(Immobile.sezione_id == sezione_id).count() > 0:
        #     logger.warning(f"Impossibile cancellare sezione ID {sezione_id} perché ha immobili collegati.")
        #     raise ValueError("Impossibile cancellare la sezione perché ha immobili collegati.")

        nome_sezione_cancellata = sezione_obj.nome_sezione
        db.delete(sezione_obj)
        db.commit()
        logger.info(f"Sezione '{nome_sezione_cancellata}' (ID: {sezione_id}) cancellata.")
        # record_audit(...)
        return True
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Errore integrità SQLAlchemy cancellazione sezione ID {sezione_id}: {e}", exc_info=True)
        # record_audit(...)
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Errore SQLAlchemy cancellazione sezione ID {sezione_id}: {e}", exc_info=True)
        # record_audit(...)
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Errore generico cancellazione sezione ID {sezione_id}: {e}", exc_info=True)
        # record_audit(...)
        return False

# === Funzioni di Servizio per ALTRE ANAGRAFICHE (Tipi semplici) ===

def _get_anagrafica_base_service(db: Session, model_class, order_by_attr) -> List[Dict[str, Any]]:
    """Funzione helper generica per recuperare anagrafiche semplici (id, nome, descrizione)."""
    try:
        items_obj = db.query(model_class).order_by(order_by_attr).all()
        return [
            {"id": item.id, "nome": item.nome, "descrizione": getattr(item, 'descrizione', None)}
            for item in items_obj
        ]
    except SQLAlchemyError as e:
        logger.error(f"Errore SQLAlchemy recupero {model_class.__tablename__}: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Errore generico recupero {model_class.__tablename__}: {e}", exc_info=True)
        return []

def get_tipi_documento_service(db: Session) -> List[Dict[str, Any]]:
    logger.info("Recupero tipi documento tramite SQLAlchemy.")
    return _get_anagrafica_base_service(db, TipoDocumento, TipoDocumento.nome)

def get_tipi_immobile_service(db: Session) -> List[Dict[str, Any]]:
    logger.info("Recupero tipi immobile tramite SQLAlchemy.")
    return _get_anagrafica_base_service(db, TipoImmobile, TipoImmobile.nome)

def get_tipi_possesso_service(db: Session) -> List[Dict[str, Any]]:
    logger.info("Recupero tipi possesso tramite SQLAlchemy.")
    return _get_anagrafica_base_service(db, TipoPossesso, TipoPossesso.nome)

def get_tipi_variazione_service(db: Session) -> List[Dict[str, Any]]:
    logger.info("Recupero tipi variazione tramite SQLAlchemy.")
    return _get_anagrafica_base_service(db, TipoVariazione, TipoVariazione.nome)

# Le funzioni CRUD generiche dell'originale anagrafiche_service.py (create_anagrafica_service, etc.)
# che operavano su nomi di tabella dinamici sono state omesse.
# Con SQLAlchemy ORM, è prassi comune avere servizi specifici per modello
# o, per operazioni veramente generiche, usare session.execute(text(...)) con cautela.
# Se hai bisogno di CRUD per TipoDocumento, TipoImmobile, etc., dovresti creare funzioni
# specifiche simili a quelle per Comune e Sezione.