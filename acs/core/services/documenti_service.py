# core/services/documenti_service.py
import logging
from datetime import date, datetime
from .audit_service import record_audit

logger = logging.getLogger("CatastoAppLogger.DocumentiService")

def create_documento_service(db_manager, tipo_documento: str, data_documento: date, 
                             descrizione: str = None, numero_protocollo_esterno: str = None,
                             ente_emittente: str = None, percorso_file_scannerizzato: str = None, 
                             note: str = None,
                             current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea un nuovo documento."""
    logger.info(f"Tentativo creazione documento: Tipo {tipo_documento}, Data {data_documento}")

    # Potrebbe esserci un controllo per evitare documenti duplicati basati su tipo, data e protocollo, se necessario.
    # Per ora, si assume che la combinazione non debba essere strettamente unica o che sia gestita dall'UI.

    query = """
        INSERT INTO documenti (
            tipo_documento, data_documento, descrizione, numero_protocollo_esterno, 
            ente_emittente, percorso_file_scannerizzato, note, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        ) RETURNING id
    """
    params = (
        tipo_documento, data_documento, descrizione, numero_protocollo_esterno,
        ente_emittente, percorso_file_scannerizzato, note
    )
    
    try:
        result = db_manager.execute_query(query, params, fetch_one=True)
        if result and result['id']:
            documento_id = result['id']
            db_manager.commit()
            log_msg = f"Documento (ID: {documento_id}, Tipo: {tipo_documento}, Data: {data_documento}) creato."
            logger.info(log_msg)
            if current_user_id:
                record_audit(db_manager, current_user_id, "CREATE_DOCUMENTO", log_msg, 
                             "documenti", documento_id, session_id, client_ip_address, success=True)
            return documento_id
        else:
            db_manager.rollback()
            logger.error(f"Creazione documento Tipo {tipo_documento} fallita (nessun ID ritornato).")
            if current_user_id: 
                record_audit(db_manager, current_user_id, "CREATE_DOCUMENTO_FAIL", 
                             "DB error creazione documento.", "documenti", 
                             session_id=session_id, client_ip_address=client_ip_address, success=False)
            return None
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service creazione documento Tipo {tipo_documento}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "CREATE_DOCUMENTO_FAIL", 
                         f"Errore creazione documento: {str(e)[:100]}", "documenti", 
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise

def get_documento_by_id_service(db_manager, documento_id: int):
    """Recupera un documento specifico tramite il suo ID."""
    logger.debug(f"Recupero documento con ID: {documento_id}")
    query = """
        SELECT id, tipo_documento, data_documento, descrizione, numero_protocollo_esterno,
               ente_emittente, percorso_file_scannerizzato, note, created_at, updated_at
        FROM documenti
        WHERE id = %s
    """
    try:
        documento = db_manager.execute_query(query, (documento_id,), fetch_one=True)
        if documento:
            logger.debug(f"Documento ID: {documento_id} trovato (Tipo: {documento['tipo_documento']}).")
        else:
            logger.warning(f"Documento ID: {documento_id} non trovato.")
        return documento
    except Exception as e:
        logger.error(f"Errore durante il recupero del documento ID {documento_id}: {e}", exc_info=True)
        return None

def get_documenti_service(db_manager, tipo_documento_search: str = None, data_da: date = None, data_a: date = None, limit: int = 100, offset: int = 0):
    """Recupera una lista di documenti, con filtri e paginazione."""
    logger.debug(f"Recupero documenti. Tipo: '{tipo_documento_search}', Da: {data_da}, A: {data_a}, Limit: {limit}, Offset: {offset}")
    
    base_query = """
        SELECT id, tipo_documento, data_documento, descrizione, numero_protocollo_esterno, ente_emittente
        FROM documenti
    """
    conditions = []
    params = []

    if tipo_documento_search:
        conditions.append("tipo_documento ILIKE %s")
        params.append(f"%{tipo_documento_search}%")
    if data_da:
        conditions.append("data_documento >= %s")
        params.append(data_da)
    if data_a:
        conditions.append("data_documento <= %s")
        params.append(data_a)

    if conditions:
        query = base_query + " WHERE " + " AND ".join(conditions)
    else:
        query = base_query
    
    query += " ORDER BY data_documento DESC, id DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    try:
        documenti = db_manager.execute_query(query, tuple(params), fetch_all=True)
        
        count_query = "SELECT COUNT(*) as total FROM documenti"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)
        
        total_count_result = db_manager.execute_query(count_query, tuple(params[:-2]), fetch_one=True) # Esclude limit e offset
        total_records = total_count_result['total'] if total_count_result else 0
        
        logger.debug(f"Trovati {len(documenti) if documenti else 0} documenti (Totali: {total_records}).")
        return documenti, total_records
    except Exception as e:
        logger.error(f"Errore durante il recupero dei documenti: {e}", exc_info=True)
        return [], 0

def update_documento_service(db_manager, documento_id: int, dati_documento: dict,
                             current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Aggiorna i dati di un documento esistente."""
    logger.info(f"Tentativo aggiornamento documento ID: {documento_id}")
    
    query = """
        UPDATE documenti SET
            tipo_documento = %(tipo_documento)s, 
            data_documento = %(data_documento)s, 
            descrizione = %(descrizione)s, 
            numero_protocollo_esterno = %(numero_protocollo_esterno)s, 
            ente_emittente = %(ente_emittente)s,
            percorso_file_scannerizzato = %(percorso_file_scannerizzato)s, 
            note = %(note)s,
            updated_at = NOW()
        WHERE id = %(documento_id)s
    """
    dati_documento['documento_id'] = documento_id 
    try:
        db_manager.execute_query(query, dati_documento)
        db_manager.commit()
        log_msg = f"Documento ID {documento_id} (Tipo: {dati_documento.get('tipo_documento')}) aggiornato."
        logger.info(log_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_DOCUMENTO", log_msg, 
                         "documenti", documento_id, session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service aggiornamento documento ID: {documento_id}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_DOCUMENTO_FAIL", 
                         f"Errore aggiornamento documento ID {documento_id}: {str(e)[:100]}", 
                         "documenti", documento_id, session_id, client_ip_address, success=False)
        raise

def delete_documento_service(db_manager, documento_id: int,
                             current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Cancella un documento, solo se non ha dipendenze (es. volture, link a partite)."""
    logger.warning(f"Tentativo cancellazione documento ID: {documento_id}.")
    
    # 1. Controllo dipendenze: volture
    dep_volt_query = "SELECT 1 FROM volture WHERE documento_id = %s LIMIT 1"
    if db_manager.execute_query(dep_volt_query, (documento_id,), fetch_one=True):
        error_msg = f"Impossibile cancellare documento ID {documento_id}: esistono volture associate."
        logger.error(error_msg)
        if current_user_id: record_audit(db_manager, current_user_id, "DELETE_DOCUMENTO_FAIL", error_msg, "documenti", documento_id, success=False)
        raise ValueError(error_msg)

    # 2. Controllo dipendenze: link a partite (documenti_partite)
    dep_link_query = "SELECT 1 FROM documenti_partite WHERE documento_id = %s LIMIT 1"
    if db_manager.execute_query(dep_link_query, (documento_id,), fetch_one=True):
        # Decisione: cancellare i link o bloccare? Per ora blocchiamo.
        error_msg = f"Impossibile cancellare documento ID {documento_id}: esistono link a partite associati. Rimuovere prima i link."
        logger.error(error_msg)
        if current_user_id: record_audit(db_manager, current_user_id, "DELETE_DOCUMENTO_FAIL", error_msg, "documenti", documento_id, success=False)
        raise ValueError(error_msg)
        # Se si volesse cancellare i link:
        # delete_links_query = "DELETE FROM documenti_partite WHERE documento_id = %s"
        # db_manager.execute_query(delete_links_query, (documento_id,))


    query = "DELETE FROM documenti WHERE id = %s"
    try:
        db_manager.execute_query(query, (documento_id,))
        db_manager.commit()
        logger.info(f"Documento ID: {documento_id} cancellato con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_DOCUMENTO", 
                         f"Documento (ID:{documento_id}) cancellato.", "documenti", documento_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service cancellazione documento ID: {documento_id}: {e}", exc_info=True)
        if current_user_id:
             record_audit(db_manager, current_user_id, "DELETE_DOCUMENTO_FAIL", 
                          f"Errore cancellazione documento (ID:{documento_id}): {str(e)[:100]}", 
                          "documenti", documento_id, session_id, client_ip_address, success=False)
        raise

# --- Gestione Link Documento-Partita ---
def link_documento_a_partita_service(db_manager, documento_id: int, partita_id: int, 
                                     rilevanza: str = None, note: str = None,
                                     current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea o aggiorna un link tra un documento e una partita (UPSERT)."""
    logger.info(f"Collegamento Documento ID {documento_id} a Partita ID {partita_id}. Rilevanza: {rilevanza}")
    
    # La tua query originale usava ON CONFLICT, il che è ottimo se hai un UNIQUE constraint
    # su (documento_id, partita_id) nella tabella documenti_partite.
    query_upsert = """
        INSERT INTO documenti_partite (documento_id, partita_id, rilevanza, note, created_at, updated_at)
        VALUES (%s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (documento_id, partita_id) 
        DO UPDATE SET rilevanza = EXCLUDED.rilevanza,
                      note = EXCLUDED.note,
                      updated_at = NOW()
        RETURNING id, CASE WHEN xmax = 0 THEN 'INSERT' ELSE 'UPDATE' END AS operation;
    """
    # Se non hai il constraint e vuoi evitare duplicati, dovresti fare un SELECT prima.
    # Ma ON CONFLICT è più efficiente e atomico.
    params = (documento_id, partita_id, rilevanza, note)
    try:
        result = db_manager.execute_query(query_upsert, params, fetch_one=True)
        if result and result['id']:
            link_id = result['id']
            operation = result['operation'] # 'INSERT' o 'UPDATE'
            db_manager.commit()
            log_msg = f"Link Documento ID {documento_id} - Partita ID {partita_id} (ID: {link_id}) {operation.lower()}ed. Rilevanza: {rilevanza}"
            logger.info(log_msg)
            if current_user_id:
                audit_action = "LINK_DOC_PARTITA_CREATE" if operation == "INSERT" else "LINK_DOC_PARTITA_UPDATE"
                record_audit(db_manager, current_user_id, audit_action, log_msg, 
                             "documenti_partite", link_id, session_id, client_ip_address, success=True)
            return link_id, operation
        else:
            # Questo blocco potrebbe non essere mai raggiunto con ON CONFLICT se la query è corretta
            db_manager.rollback()
            logger.error(f"Link Doc {documento_id} - Partita {partita_id} fallito (nessun ID/operazione ritornato).")
            if current_user_id: record_audit(db_manager, current_user_id, "LINK_DOC_PARTITA_FAIL", "DB error", "documenti_partite", success=False)
            return None, None
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service link Doc {documento_id} - Partita {partita_id}: {e}", exc_info=True)
        if current_user_id: record_audit(db_manager, current_user_id, "LINK_DOC_PARTITA_FAIL", f"Errore: {str(e)[:100]}", "documenti_partite", success=False)
        raise

def get_documenti_per_partita_service(db_manager, partita_id: int):
    """Recupera i documenti collegati a una partita."""
    logger.debug(f"Recupero documenti per Partita ID: {partita_id}")
    query = """
        SELECT d.id as documento_id, d.tipo_documento, d.data_documento, d.descrizione,
               dp.rilevanza, dp.note as note_link, dp.id as link_id
        FROM documenti d
        JOIN documenti_partite dp ON d.id = dp.documento_id
        WHERE dp.partita_id = %s
        ORDER BY d.data_documento DESC, d.tipo_documento
    """
    try:
        documenti = db_manager.execute_query(query, (partita_id,), fetch_all=True)
        logger.debug(f"Trovati {len(documenti) if documenti else 0} documenti per Partita ID {partita_id}.")
        return documenti
    except Exception as e:
        logger.error(f"Errore recupero documenti per Partita ID {partita_id}: {e}", exc_info=True)
        return []

def get_partite_per_documento_service(db_manager, documento_id: int):
    """Recupera le partite collegate a un documento."""
    logger.debug(f"Recupero partite per Documento ID: {documento_id}")
    query = """
        SELECT p.id as partita_id, p.numero_partita, c.nome as nome_comune, s.nome_sezione,
               dp.rilevanza, dp.note as note_link, dp.id as link_id
        FROM partite p
        JOIN comuni c ON p.comune_id = c.id
        JOIN sezioni s ON p.sezione_id = s.id
        JOIN documenti_partite dp ON p.id = dp.partita_id
        WHERE dp.documento_id = %s
        ORDER BY c.nome, s.nome_sezione, p.numero_partita
    """
    try:
        partite = db_manager.execute_query(query, (documento_id,), fetch_all=True)
        logger.debug(f"Trovate {len(partite) if partite else 0} partite per Documento ID {documento_id}.")
        return partite
    except Exception as e:
        logger.error(f"Errore recupero partite per Documento ID {documento_id}: {e}", exc_info=True)
        return []

def unlink_documento_da_partita_service(db_manager, link_id: int = None, documento_id: int = None, partita_id: int = None,
                                        current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Rimuove un link specifico tra documento e partita."""
    if not link_id and not (documento_id and partita_id):
        raise ValueError("È necessario fornire link_id oppure sia documento_id che partita_id.")

    if link_id:
        logger.warning(f"Tentativo cancellazione link documento-partita per Link ID: {link_id}.")
        query = "DELETE FROM documenti_partite WHERE id = %s"
        params = (link_id,)
        log_identifier = f"Link ID {link_id}"
    else:
        logger.warning(f"Tentativo cancellazione link tra Documento ID {documento_id} e Partita ID {partita_id}.")
        query = "DELETE FROM documenti_partite WHERE documento_id = %s AND partita_id = %s"
        params = (documento_id, partita_id)
        log_identifier = f"Doc ID {documento_id} - Partita ID {partita_id}"


    try:
        db_manager.execute_query(query, params)
        db_manager.commit()
        logger.info(f"Link documento-partita ({log_identifier}) cancellato con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "UNLINK_DOC_PARTITA", 
                         f"Link {log_identifier} cancellato.", 
                         "documenti_partite", link_id or f"{documento_id}-{partita_id}", # Usa un ID composto se link_id non c'è
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service cancellazione link documento-partita ({log_identifier}): {e}", exc_info=True)
        if current_user_id:
             record_audit(db_manager, current_user_id, "UNLINK_DOC_PARTITA_FAIL", 
                          f"Errore cancellazione link {log_identifier}: {str(e)[:100]}", 
                          "documenti_partite", link_id or f"{documento_id}-{partita_id}",
                          session_id, client_ip_address, success=False)
        raise