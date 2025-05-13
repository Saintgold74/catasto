# core/services/volture_service.py
import logging
from datetime import date, datetime
from .audit_service import record_audit

logger = logging.getLogger("CatastoAppLogger.VoltureService")

def create_voltura_service(db_manager, documento_id: int, tipo_voltura: str, data_registrazione: date,
                           numero_protocollo: str = None, anno_protocollo: int = None, 
                           partita_precedente_id: int = None, partita_attuale_id: int = None,
                           note: str = None,
                           current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea una nuova voltura."""
    logger.info(f"Tentativo creazione voltura: Tipo {tipo_voltura}, Documento ID {documento_id}, Data {data_registrazione}")

    # Validazioni di base
    if not partita_precedente_id and not partita_attuale_id:
        error_msg = "Creazione voltura fallita: almeno una tra partita precedente e attuale deve essere specificata."
        logger.error(error_msg)
        if current_user_id: record_audit(db_manager, current_user_id, "CREATE_VOLTURA_FAIL", error_msg, "volture", success=False)
        raise ValueError(error_msg)
    
    # Potrebbe esserci un controllo per evitare volture duplicate per lo stesso documento/protocollo

    query = """
        INSERT INTO volture (
            documento_id, tipo_voltura, data_registrazione, numero_protocollo, anno_protocollo,
            partita_precedente_id, partita_attuale_id, note, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        ) RETURNING id
    """
    params = (
        documento_id, tipo_voltura, data_registrazione, numero_protocollo, anno_protocollo,
        partita_precedente_id, partita_attuale_id, note
    )
    try:
        result = db_manager.execute_query(query, params, fetch_one=True)
        if result and result['id']:
            voltura_id = result['id']
            db_manager.commit()
            log_msg = f"Voltura (ID: {voltura_id}, Tipo: {tipo_voltura}) creata per Documento ID {documento_id}."
            logger.info(log_msg)
            if current_user_id:
                record_audit(db_manager, current_user_id, "CREATE_VOLTURA", log_msg, 
                             "volture", voltura_id, session_id, client_ip_address, success=True)
            
            # Logica aggiuntiva post-voltura (es. aggiornamento stato partite, intestazioni)
            # Questa parte è complessa e dipende dalle regole di business.
            # Ad esempio, una voltura "per afflusso" (nuova partita) potrebbe richiedere la creazione di nuove intestazioni
            # per la partita_attuale_id basate sui dettagli del documento o input utente.
            # Una voltura "per variazione" potrebbe chiudere intestazioni sulla partita_precedente_id
            # e aprirne di nuove sulla partita_attuale_id.
            # Questo è OLTRE una semplice CRUD e richiede un'analisi più approfondita del workflow.
            # Per ora, ci limitiamo a creare il record della voltura.

            return voltura_id
        else:
            db_manager.rollback()
            logger.error(f"Creazione voltura Tipo {tipo_voltura}, Documento ID {documento_id} fallita.")
            if current_user_id: record_audit(db_manager, current_user_id, "CREATE_VOLTURA_FAIL", "DB error", "volture", success=False)
            return None
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service creazione voltura Tipo {tipo_voltura}: {e}", exc_info=True)
        if current_user_id: record_audit(db_manager, current_user_id, "CREATE_VOLTURA_FAIL", f"Errore: {str(e)[:100]}", "volture", success=False)
        raise

def get_voltura_by_id_service(db_manager, voltura_id: int):
    """Recupera una voltura specifica tramite il suo ID."""
    logger.debug(f"Recupero voltura con ID: {voltura_id}")
    query = """
        SELECT v.id, v.documento_id, d.tipo_documento as nome_tipo_documento, d.data_documento,
               v.tipo_voltura, v.data_registrazione, v.numero_protocollo, v.anno_protocollo,
               v.partita_precedente_id, pp.numero_partita as numero_partita_precedente,
               v.partita_attuale_id, pa.numero_partita as numero_partita_attuale,
               v.note, v.created_at, v.updated_at
        FROM volture v
        JOIN documenti d ON v.documento_id = d.id
        LEFT JOIN partite pp ON v.partita_precedente_id = pp.id
        LEFT JOIN partite pa ON v.partita_attuale_id = pa.id
        WHERE v.id = %s
    """
    try:
        voltura = db_manager.execute_query(query, (voltura_id,), fetch_one=True)
        if voltura:
            logger.debug(f"Voltura ID: {voltura_id} trovata.")
        else:
            logger.warning(f"Voltura ID: {voltura_id} non trovata.")
        return voltura
    except Exception as e:
        logger.error(f"Errore durante il recupero della voltura ID {voltura_id}: {e}", exc_info=True)
        return None

def get_volture_by_partita_service(db_manager, partita_id: int):
    """Recupera tutte le volture che coinvolgono una specifica partita (sia come precedente che attuale)."""
    logger.debug(f"Recupero volture per Partita ID: {partita_id}")
    query = """
        SELECT v.id, v.documento_id, d.tipo_documento as nome_tipo_documento, 
               v.tipo_voltura, v.data_registrazione, v.numero_protocollo,
               v.partita_precedente_id, pp.numero_partita as numero_partita_precedente,
               v.partita_attuale_id, pa.numero_partita as numero_partita_attuale
        FROM volture v
        JOIN documenti d ON v.documento_id = d.id
        LEFT JOIN partite pp ON v.partita_precedente_id = pp.id
        LEFT JOIN partite pa ON v.partita_attuale_id = pa.id
        WHERE v.partita_precedente_id = %s OR v.partita_attuale_id = %s
        ORDER BY v.data_registrazione DESC, v.id DESC
    """
    try:
        volture = db_manager.execute_query(query, (partita_id, partita_id), fetch_all=True)
        logger.debug(f"Trovate {len(volture) if volture else 0} volture per Partita ID {partita_id}.")
        return volture
    except Exception as e:
        logger.error(f"Errore recupero volture per Partita ID {partita_id}: {e}", exc_info=True)
        return []

def get_volture_by_documento_service(db_manager, documento_id: int):
    """Recupera tutte le volture associate a un documento."""
    # Simile a get_volture_by_partita_service, ma con WHERE su v.documento_id
    logger.debug(f"Recupero volture per Documento ID: {documento_id}")
    query = """
        SELECT v.id, v.tipo_voltura, v.data_registrazione, v.numero_protocollo,
               v.partita_precedente_id, pp.numero_partita as numero_partita_precedente,
               v.partita_attuale_id, pa.numero_partita as numero_partita_attuale
        FROM volture v
        LEFT JOIN partite pp ON v.partita_precedente_id = pp.id
        LEFT JOIN partite pa ON v.partita_attuale_id = pa.id
        WHERE v.documento_id = %s
        ORDER BY v.data_registrazione DESC, v.id DESC
    """
    try:
        volture = db_manager.execute_query(query, (documento_id,), fetch_all=True)
        return volture
    except Exception as e:
        logger.error(f"Errore recupero volture per Documento ID {documento_id}: {e}", exc_info=True)
        return []


def update_voltura_service(db_manager, voltura_id: int, dati_voltura: dict,
                           current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Aggiorna i dati di una voltura esistente."""
    logger.info(f"Tentativo aggiornamento voltura ID: {voltura_id}")
    
    # Assicurarsi che almeno una partita sia specificata
    if dati_voltura.get('partita_precedente_id') is None and dati_voltura.get('partita_attuale_id') is None:
        error_msg = "Aggiornamento voltura fallito: almeno una tra partita precedente e attuale deve essere specificata."
        logger.error(error_msg)
        if current_user_id: record_audit(db_manager, current_user_id, "UPDATE_VOLTURA_FAIL", error_msg, "volture", voltura_id, success=False)
        raise ValueError(error_msg)

    query = """
        UPDATE volture SET
            documento_id = %(documento_id)s, 
            tipo_voltura = %(tipo_voltura)s, 
            data_registrazione = %(data_registrazione)s, 
            numero_protocollo = %(numero_protocollo)s, 
            anno_protocollo = %(anno_protocollo)s,
            partita_precedente_id = %(partita_precedente_id)s, 
            partita_attuale_id = %(partita_attuale_id)s, 
            note = %(note)s,
            updated_at = NOW()
        WHERE id = %(voltura_id)s
    """
    dati_voltura['voltura_id'] = voltura_id
    try:
        db_manager.execute_query(query, dati_voltura)
        db_manager.commit()
        log_msg = f"Voltura ID {voltura_id} (Tipo: {dati_voltura.get('tipo_voltura')}) aggiornata."
        logger.info(log_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_VOLTURA", log_msg, 
                         "volture", voltura_id, session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service aggiornamento voltura ID: {voltura_id}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_VOLTURA_FAIL", 
                         f"Errore aggiornamento voltura ID {voltura_id}: {str(e)[:100]}", 
                         "volture", voltura_id, session_id, client_ip_address, success=False)
        raise

def delete_voltura_service(db_manager, voltura_id: int,
                           current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Cancella una voltura."""
    logger.warning(f"Tentativo cancellazione voltura ID: {voltura_id}.")
    
    # Una voltura è un record storico. La cancellazione fisica potrebbe non essere desiderabile.
    # Considerare un flag 'annullata' o 'stornata'.
    # Se si procede con la cancellazione, non ci sono tipicamente dipendenze dirette che la bloccano,
    # ma potrebbe invalidare la storia di una partita.

    query = "DELETE FROM volture WHERE id = %s"
    try:
        db_manager.execute_query(query, (voltura_id,))
        db_manager.commit()
        logger.info(f"Voltura ID: {voltura_id} cancellata con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_VOLTURA", 
                         f"Voltura (ID:{voltura_id}) cancellata.", "volture", voltura_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service cancellazione voltura ID: {voltura_id}: {e}", exc_info=True)
        if current_user_id:
             record_audit(db_manager, current_user_id, "DELETE_VOLTURA_FAIL", 
                          f"Errore cancellazione voltura (ID:{voltura_id}): {str(e)[:100]}", 
                          "volture", voltura_id, session_id, client_ip_address, success=False)
        raise