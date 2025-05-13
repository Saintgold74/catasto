# core/services/anagrafiche_service.py
import logging
from .audit_service import record_audit # Assumendo che audit_service.py sia nella stessa directory
from datetime import date, datetime # Assicura che 'date' e 'datetime' siano importati

# Ottieni un logger specifico per questo modulo
logger = logging.getLogger("CatastoAppLogger.AnagraficheService")

# --- Gestione Comuni ---
def create_comune_service(db_manager, nome: str, codice_catastale: str, provincia: str, regione: str, note: str = None, 
                          current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea un nuovo comune."""
    logger.info(f"Tentativo creazione comune: {nome}")
    # Verifica se il comune esiste già (per codice catastale che dovrebbe essere unico)
    check_query = "SELECT id FROM comuni WHERE codice_catastale = %s"
    existing_comune = db_manager.execute_query(check_query, (codice_catastale,), fetch_one=True)
    if existing_comune:
        error_msg = f"Comune con codice catastale '{codice_catastale}' già esistente (ID: {existing_comune['id']})."
        logger.warning(error_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "CREATE_COMUNE_FAIL", 
                         error_msg, "comuni", client_ip_address=client_ip_address, success=False)
        raise ValueError(error_msg)

    query = """
        INSERT INTO comuni (nome, codice_catastale, provincia, regione, note, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW()) RETURNING id
    """
    try:
        result = db_manager.execute_query(query, (nome, codice_catastale, provincia, regione, note), fetch_one=True)
        if result and result['id']:
            comune_id = result['id']
            db_manager.commit()
            logger.info(f"Comune '{nome}' (ID: {comune_id}) creato con successo.")
            if current_user_id:
                record_audit(db_manager, current_user_id, "CREATE_COMUNE", 
                             f"Comune {nome} (ID:{comune_id}) creato.", "comuni", comune_id,
                             session_id, client_ip_address, success=True)
            return comune_id
        else:
            db_manager.rollback()
            logger.error(f"Creazione comune '{nome}' fallita (nessun ID ritornato).")
            if current_user_id:
                 record_audit(db_manager, current_user_id, "CREATE_COMUNE_FAIL", 
                              f"Fallimento creazione comune {nome} (DB error).", "comuni", 
                              session_id=session_id, client_ip_address=client_ip_address, success=False)
            return None
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante creazione comune '{nome}': {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "CREATE_COMUNE_FAIL", 
                         f"Errore creazione comune {nome}: {str(e)[:100]}", "comuni", 
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise

def get_comuni_service(db_manager, nome_comune_search: str = None):
    """Recupera i comuni, opzionalmente filtrati per nome."""
    logger.debug(f"Recupero comuni. Filtro nome: {nome_comune_search}")
    if nome_comune_search:
        query = "SELECT id, nome, codice_catastale, provincia, regione, note FROM comuni WHERE nome ILIKE %s ORDER BY nome"
        params = (f"%{nome_comune_search}%",)
    else:
        query = "SELECT id, nome, codice_catastale, provincia, regione, note FROM comuni ORDER BY nome"
        params = None
    try:
        comuni = db_manager.execute_query(query, params, fetch_all=True)
        logger.debug(f"Trovati {len(comuni) if comuni else 0} comuni.")
        return comuni
    except Exception as e:
        logger.error(f"Errore durante il recupero dei comuni: {e}", exc_info=True)
        return []

def get_comune_by_id_service(db_manager, comune_id: int):
    """Recupera un comune specifico tramite il suo ID."""
    logger.debug(f"Recupero comune con ID: {comune_id}")
    query = "SELECT id, nome, codice_catastale, provincia, regione, note FROM comuni WHERE id = %s"
    try:
        comune = db_manager.execute_query(query, (comune_id,), fetch_one=True)
        if comune:
            logger.debug(f"Comune ID: {comune_id} trovato: {comune['nome']}")
        else:
            logger.debug(f"Comune ID: {comune_id} non trovato.")
        return comune
    except Exception as e:
        logger.error(f"Errore durante il recupero del comune ID {comune_id}: {e}", exc_info=True)
        return None


def update_comune_service(db_manager, comune_id: int, nome: str, codice_catastale: str, provincia: str, regione: str, note: str = None,
                           current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Aggiorna i dati di un comune esistente."""
    logger.info(f"Tentativo aggiornamento comune ID: {comune_id} con nome: {nome}")
    
    # Opzionale: verifica se un altro comune ha già il nuovo codice catastale (se deve rimanere unico)
    check_query = "SELECT id FROM comuni WHERE codice_catastale = %s AND id != %s"
    existing_comune = db_manager.execute_query(check_query, (codice_catastale, comune_id), fetch_one=True)
    if existing_comune:
        error_msg = f"Aggiornamento fallito: un altro comune (ID: {existing_comune['id']}) utilizza già il codice catastale '{codice_catastale}'."
        logger.warning(error_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_COMUNE_FAIL", 
                         error_msg, "comuni", comune_id, 
                         session_id, client_ip_address, success=False)
        raise ValueError(error_msg)

    query = """
        UPDATE comuni SET nome = %s, codice_catastale = %s, provincia = %s, regione = %s, note = %s, updated_at = NOW()
        WHERE id = %s
    """
    try:
        # execute_query per UPDATE/DELETE di solito non ritorna dati a meno che non usi RETURNING.
        # Se non ci sono errori, consideriamo l'operazione riuscita.
        db_manager.execute_query(query, (nome, codice_catastale, provincia, regione, note, comune_id))
        db_manager.commit()
        logger.info(f"Comune ID: {comune_id} aggiornato con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_COMUNE", 
                         f"Comune {nome} (ID:{comune_id}) aggiornato.", "comuni", comune_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante aggiornamento comune ID: {comune_id}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_COMUNE_FAIL", 
                         f"Errore aggiornamento comune {nome} (ID:{comune_id}): {str(e)[:100]}", "comuni", comune_id,
                         session_id, client_ip_address, success=False)
        raise

def delete_comune_service(db_manager, comune_id: int, 
                          current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Cancella un comune, solo se non ha dipendenze (es. sezioni)."""
    logger.warning(f"Tentativo cancellazione comune ID: {comune_id}.")
    
    # 1. Controllo dipendenze (esempio: sezioni)
    dependency_check_query = "SELECT 1 FROM sezioni WHERE comune_id = %s LIMIT 1"
    dependency = db_manager.execute_query(dependency_check_query, (comune_id,), fetch_one=True)
    if dependency:
        error_msg = f"Impossibile cancellare comune ID {comune_id}: esistono sezioni associate."
        logger.error(error_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_COMUNE_FAIL", 
                         error_msg, "comuni", comune_id, 
                         session_id, client_ip_address, success=False)
        raise ValueError(error_msg) # Solleva un'eccezione che l'UI può intercettare

    query = "DELETE FROM comuni WHERE id = %s"
    try:
        db_manager.execute_query(query, (comune_id,))
        db_manager.commit()
        logger.info(f"Comune ID: {comune_id} cancellato con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_COMUNE", 
                         f"Comune (ID:{comune_id}) cancellato.", "comuni", comune_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante cancellazione comune ID: {comune_id}: {e}", exc_info=True)
        if current_user_id:
             record_audit(db_manager, current_user_id, "DELETE_COMUNE_FAIL", 
                          f"Errore cancellazione comune (ID:{comune_id}): {str(e)[:100]}", "comuni", comune_id,
                          session_id, client_ip_address, success=False)
        raise

# --- Gestione Sezioni ---
def create_sezione_service(db_manager, comune_id: int, nome_sezione: str, codice_sezione: str = None, note: str = None,
                           current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea una nuova sezione per un comune."""
    logger.info(f"Tentativo creazione sezione: '{nome_sezione}' per comune ID: {comune_id}")
    # Opzionale: verifica se una sezione con lo stesso nome/codice esiste già per quel comune
    check_query = "SELECT id FROM sezioni WHERE comune_id = %s AND (nome_sezione = %s OR (codice_sezione IS NOT NULL AND codice_sezione = %s))"
    existing_sezione = db_manager.execute_query(check_query, (comune_id, nome_sezione, codice_sezione), fetch_one=True)
    if existing_sezione:
        error_msg = f"Sezione con nome '{nome_sezione}' o codice '{codice_sezione}' già esistente per comune ID {comune_id}."
        logger.warning(error_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "CREATE_SEZIONE_FAIL", error_msg, "sezioni", client_ip_address=client_ip_address, success=False)
        raise ValueError(error_msg)
        
    query = """
        INSERT INTO sezioni (comune_id, nome_sezione, codice_sezione, note, created_at, updated_at)
        VALUES (%s, %s, %s, %s, NOW(), NOW()) RETURNING id
    """
    try:
        result = db_manager.execute_query(query, (comune_id, nome_sezione, codice_sezione, note), fetch_one=True)
        if result and result['id']:
            sezione_id = result['id']
            db_manager.commit()
            logger.info(f"Sezione '{nome_sezione}' (ID: {sezione_id}) creata per comune ID {comune_id}.")
            if current_user_id:
                record_audit(db_manager, current_user_id, "CREATE_SEZIONE", 
                             f"Sezione {nome_sezione} (ID:{sezione_id}) creata per comune ID {comune_id}.", 
                             "sezioni", sezione_id, session_id, client_ip_address, success=True)
            return sezione_id
        else:
            db_manager.rollback()
            logger.error(f"Creazione sezione '{nome_sezione}' fallita (nessun ID ritornato).")
            if current_user_id:
                record_audit(db_manager, current_user_id, "CREATE_SEZIONE_FAIL", f"Fallimento creazione sezione {nome_sezione}.", "sezioni", session_id=session_id, client_ip_address=client_ip_address, success=False)
            return None
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service creazione sezione '{nome_sezione}': {e}", exc_info=True)
        if current_user_id:
             record_audit(db_manager, current_user_id, "CREATE_SEZIONE_FAIL", f"Errore creazione sezione {nome_sezione}: {str(e)[:100]}", "sezioni", session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise

def get_sezioni_service(db_manager, comune_id: int = None, nome_sezione_search: str = None):
    """Recupera le sezioni, opzionalmente filtrate per comune_id e/o nome sezione."""
    logger.debug(f"Recupero sezioni. Filtro comune ID: {comune_id}, Filtro nome: {nome_sezione_search}")
    
    base_query = """
        SELECT s.id, s.comune_id, c.nome as nome_comune, s.nome_sezione, s.codice_sezione, s.note 
        FROM sezioni s 
        JOIN comuni c ON s.comune_id = c.id
    """
    conditions = []
    params = []

    if comune_id is not None:
        conditions.append("s.comune_id = %s")
        params.append(comune_id)
    if nome_sezione_search:
        conditions.append("s.nome_sezione ILIKE %s")
        params.append(f"%{nome_sezione_search}%")

    if conditions:
        query = base_query + " WHERE " + " AND ".join(conditions)
    else:
        query = base_query
    
    query += " ORDER BY c.nome, s.nome_sezione"
    
    try:
        sezioni = db_manager.execute_query(query, tuple(params), fetch_all=True)
        logger.debug(f"Trovate {len(sezioni) if sezioni else 0} sezioni.")
        return sezioni
    except Exception as e:
        logger.error(f"Errore recupero sezioni: {e}", exc_info=True)
        return []

def get_sezione_by_id_service(db_manager, sezione_id: int):
    """Recupera una sezione specifica tramite il suo ID."""
    logger.debug(f"Recupero sezione con ID: {sezione_id}")
    query = """
        SELECT s.id, s.comune_id, c.nome as nome_comune, s.nome_sezione, s.codice_sezione, s.note 
        FROM sezioni s
        JOIN comuni c ON s.comune_id = c.id
        WHERE s.id = %s
    """
    try:
        sezione = db_manager.execute_query(query, (sezione_id,), fetch_one=True)
        if sezione:
            logger.debug(f"Sezione ID: {sezione_id} trovata: {sezione['nome_sezione']}")
        else:
            logger.debug(f"Sezione ID: {sezione_id} non trovata.")
        return sezione
    except Exception as e:
        logger.error(f"Errore durante il recupero della sezione ID {sezione_id}: {e}", exc_info=True)
        return None

def update_sezione_service(db_manager, sezione_id: int, comune_id: int, nome_sezione: str, codice_sezione: str = None, note: str = None,
                           current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Aggiorna i dati di una sezione esistente."""
    logger.info(f"Tentativo aggiornamento sezione ID: {sezione_id} con nome: {nome_sezione}")
    # Opzionale: verifica unicità nome/codice all'interno del comune, escludendo la sezione corrente
    check_query = "SELECT id FROM sezioni WHERE comune_id = %s AND (nome_sezione = %s OR (codice_sezione IS NOT NULL AND codice_sezione = %s)) AND id != %s"
    existing_sezione = db_manager.execute_query(check_query, (comune_id, nome_sezione, codice_sezione, sezione_id), fetch_one=True)
    if existing_sezione:
        error_msg = f"Aggiornamento fallito: altra sezione (ID: {existing_sezione['id']}) con nome '{nome_sezione}' o codice '{codice_sezione}' già esistente per comune ID {comune_id}."
        logger.warning(error_msg)
        if current_user_id:
             record_audit(db_manager, current_user_id, "UPDATE_SEZIONE_FAIL", error_msg, "sezioni", sezione_id, success=False)
        raise ValueError(error_msg)

    query = """
        UPDATE sezioni SET comune_id = %s, nome_sezione = %s, codice_sezione = %s, note = %s, updated_at = NOW()
        WHERE id = %s
    """
    try:
        db_manager.execute_query(query, (comune_id, nome_sezione, codice_sezione, note, sezione_id))
        db_manager.commit()
        logger.info(f"Sezione ID: {sezione_id} aggiornata con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_SEZIONE", 
                         f"Sezione {nome_sezione} (ID:{sezione_id}) aggiornata.", "sezioni", sezione_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante aggiornamento sezione ID: {sezione_id}: {e}", exc_info=True)
        if current_user_id:
             record_audit(db_manager, current_user_id, "UPDATE_SEZIONE_FAIL", f"Errore aggiornamento sezione {nome_sezione} (ID:{sezione_id}): {str(e)[:100]}", "sezioni", sezione_id, success=False)
        raise

def delete_sezione_service(db_manager, sezione_id: int,
                           current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Cancella una sezione, solo se non ha dipendenze (es. partite)."""
    logger.warning(f"Tentativo cancellazione sezione ID: {sezione_id}.")
    # 1. Controllo dipendenze (esempio: partite)
    dependency_check_query = "SELECT 1 FROM partite WHERE sezione_id = %s LIMIT 1" # Adatta 'partite' e 'sezione_id' al tuo schema
    dependency = db_manager.execute_query(dependency_check_query, (sezione_id,), fetch_one=True)
    if dependency:
        error_msg = f"Impossibile cancellare sezione ID {sezione_id}: esistono partite associate."
        logger.error(error_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_SEZIONE_FAIL", error_msg, "sezioni", sezione_id, success=False)
        raise ValueError(error_msg)

    query = "DELETE FROM sezioni WHERE id = %s"
    try:
        db_manager.execute_query(query, (sezione_id,))
        db_manager.commit()
        logger.info(f"Sezione ID: {sezione_id} cancellata con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_SEZIONE", 
                         f"Sezione (ID:{sezione_id}) cancellata.", "sezioni", sezione_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante cancellazione sezione ID: {sezione_id}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_SEZIONE_FAIL", f"Errore cancellazione sezione (ID:{sezione_id}): {str(e)[:100]}", "sezioni", sezione_id, success=False)
        raise

# --- Gestione Qualifiche Possessore ---
def create_qualifica_service(db_manager, nome_qualifica: str, descrizione: str = None,
                             current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea una nuova qualifica per i possessori."""
    logger.info(f"Tentativo creazione qualifica: {nome_qualifica}")
    check_query = "SELECT id FROM qualifiche_possessore WHERE nome_qualifica = %s"
    existing = db_manager.execute_query(check_query, (nome_qualifica,), fetch_one=True)
    if existing:
        error_msg = f"Qualifica '{nome_qualifica}' già esistente (ID: {existing['id']})."
        logger.warning(error_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "CREATE_QUALIFICA_FAIL", error_msg, "qualifiche_possessore", success=False)
        raise ValueError(error_msg)

    query = "INSERT INTO qualifiche_possessore (nome_qualifica, descrizione, created_at, updated_at) VALUES (%s, %s, NOW(), NOW()) RETURNING id"
    try:
        result = db_manager.execute_query(query, (nome_qualifica, descrizione), fetch_one=True)
        if result and result['id']:
            qualifica_id = result['id']
            db_manager.commit()
            logger.info(f"Qualifica '{nome_qualifica}' (ID: {qualifica_id}) creata.")
            if current_user_id:
                record_audit(db_manager, current_user_id, "CREATE_QUALIFICA", f"Qualifica {nome_qualifica} (ID:{qualifica_id}) creata.", "qualifiche_possessore", qualifica_id, session_id, client_ip_address, success=True)
            return qualifica_id
        else:
            db_manager.rollback(); # Audit
            return None
    except Exception as e:
        db_manager.rollback(); logger.error(f"Errore Service creazione qualifica '{nome_qualifica}': {e}", exc_info=True); # Audit
        raise

def get_qualifiche_service(db_manager):
    """Recupera tutte le qualifiche dei possessori."""
    logger.debug("Recupero qualifiche possessore.")
    query = "SELECT id, nome_qualifica, descrizione FROM qualifiche_possessore ORDER BY nome_qualifica"
    try:
        return db_manager.execute_query(query, fetch_all=True)
    except Exception as e:
        logger.error(f"Errore recupero qualifiche: {e}", exc_info=True)
        return []
        
def get_qualifica_by_id_service(db_manager, qualifica_id: int):
    logger.debug(f"Recupero qualifica ID: {qualifica_id}")
    query = "SELECT id, nome_qualifica, descrizione FROM qualifiche_possessore WHERE id = %s"
    try:
        return db_manager.execute_query(query, (qualifica_id,), fetch_one=True)
    except Exception as e:
        logger.error(f"Errore recupero qualifica ID {qualifica_id}: {e}", exc_info=True)
        return None


def update_qualifica_service(db_manager, qualifica_id: int, nome_qualifica: str, descrizione: str = None,
                             current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Aggiorna una qualifica esistente."""
    logger.info(f"Tentativo aggiornamento qualifica ID: {qualifica_id} con nome: {nome_qualifica}")
    check_query = "SELECT id FROM qualifiche_possessore WHERE nome_qualifica = %s AND id != %s"
    existing = db_manager.execute_query(check_query, (nome_qualifica, qualifica_id), fetch_one=True)
    if existing:
        error_msg = f"Aggiornamento fallito: altra qualifica (ID: {existing['id']}) ha già il nome '{nome_qualifica}'."
        logger.warning(error_msg)
        if current_user_id: record_audit(db_manager, current_user_id, "UPDATE_QUALIFICA_FAIL", error_msg, "qualifiche_possessore", qualifica_id, success=False)
        raise ValueError(error_msg)

    query = "UPDATE qualifiche_possessore SET nome_qualifica = %s, descrizione = %s, updated_at = NOW() WHERE id = %s"
    try:
        db_manager.execute_query(query, (nome_qualifica, descrizione, qualifica_id))
        db_manager.commit()
        logger.info(f"Qualifica ID: {qualifica_id} aggiornata.")
        if current_user_id: record_audit(db_manager, current_user_id, "UPDATE_QUALIFICA", f"Qualifica {nome_qualifica} (ID:{qualifica_id}) aggiornata.", "qualifiche_possessore", qualifica_id, session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback(); logger.error(f"Errore Service aggiornamento qualifica ID: {qualifica_id}: {e}", exc_info=True)
        if current_user_id: record_audit(db_manager, current_user_id, "UPDATE_QUALIFICA_FAIL", f"Errore aggiornamento qualifica {nome_qualifica} (ID:{qualifica_id}): {str(e)[:100]}", "qualifiche_possessore", qualifica_id, success=False)
        raise

def delete_qualifica_service(db_manager, qualifica_id: int,
                             current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Cancella una qualifica, solo se non ha dipendenze."""
    logger.warning(f"Tentativo cancellazione qualifica ID: {qualifica_id}.")
    # Controllo dipendenze (es. tabella 'intestazioni' o 'possessori_storico' se qualifica_id è lì)
    # Adatta il nome della tabella e del campo FK al tuo schema
    dependency_check_query = "SELECT 1 FROM intestazioni WHERE qualifica_id = %s LIMIT 1" 
    dependency = db_manager.execute_query(dependency_check_query, (qualifica_id,), fetch_one=True)
    if dependency:
        error_msg = f"Impossibile cancellare qualifica ID {qualifica_id}: è utilizzata nelle intestazioni."
        logger.error(error_msg)
        if current_user_id: record_audit(db_manager, current_user_id, "DELETE_QUALIFICA_FAIL", error_msg, "qualifiche_possessore", qualifica_id, success=False)
        raise ValueError(error_msg)

    query = "DELETE FROM qualifiche_possessore WHERE id = %s"
    try:
        db_manager.execute_query(query, (qualifica_id,))
        db_manager.commit()
        logger.info(f"Qualifica ID: {qualifica_id} cancellata.")
        if current_user_id: record_audit(db_manager, current_user_id, "DELETE_QUALIFICA", f"Qualifica (ID:{qualifica_id}) cancellata.", "qualifiche_possessore", qualifica_id, session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback(); logger.error(f"Errore Service cancellazione qualifica ID: {qualifica_id}: {e}", exc_info=True)
        if current_user_id: record_audit(db_manager, current_user_id, "DELETE_QUALIFICA_FAIL", f"Errore cancellazione qualifica (ID:{qualifica_id}): {str(e)[:100]}", "qualifiche_possessore", qualifica_id, success=False)
        raise

# --- Gestione Titoli/Diritti ---
def create_titolo_service(db_manager, nome_titolo: str, descrizione: str = None,
                          current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea un nuovo titolo/diritto."""
    logger.info(f"Tentativo creazione titolo: {nome_titolo}")
    check_query = "SELECT id FROM titoli_diritti WHERE nome_titolo = %s"
    existing = db_manager.execute_query(check_query, (nome_titolo,), fetch_one=True)
    if existing:
        error_msg = f"Titolo '{nome_titolo}' già esistente (ID: {existing['id']})."
        logger.warning(error_msg)
        if current_user_id: record_audit(db_manager, current_user_id, "CREATE_TITOLO_FAIL", error_msg, "titoli_diritti", success=False)
        raise ValueError(error_msg)

    query = "INSERT INTO titoli_diritti (nome_titolo, descrizione, created_at, updated_at) VALUES (%s, %s, NOW(), NOW()) RETURNING id"
    try:
        result = db_manager.execute_query(query, (nome_titolo, descrizione), fetch_one=True)
        if result and result['id']:
            titolo_id = result['id']
            db_manager.commit()
            logger.info(f"Titolo '{nome_titolo}' (ID: {titolo_id}) creato.")
            if current_user_id: record_audit(db_manager, current_user_id, "CREATE_TITOLO", f"Titolo {nome_titolo} (ID:{titolo_id}) creato.", "titoli_diritti", titolo_id, session_id, client_ip_address, success=True)
            return titolo_id
        else:
            db_manager.rollback(); # Audit
            return None
    except Exception as e:
        db_manager.rollback(); logger.error(f"Errore Service creazione titolo '{nome_titolo}': {e}", exc_info=True); # Audit
        raise

def get_titoli_service(db_manager):
    """Recupera tutti i titoli/diritti."""
    logger.debug("Recupero titoli/diritti.")
    query = "SELECT id, nome_titolo, descrizione FROM titoli_diritti ORDER BY nome_titolo"
    try:
        return db_manager.execute_query(query, fetch_all=True)
    except Exception as e:
        logger.error(f"Errore recupero titoli: {e}", exc_info=True)
        return []

def get_titolo_by_id_service(db_manager, titolo_id: int):
    logger.debug(f"Recupero titolo ID: {titolo_id}")
    query = "SELECT id, nome_titolo, descrizione FROM titoli_diritti WHERE id = %s"
    try:
        return db_manager.execute_query(query, (titolo_id,), fetch_one=True)
    except Exception as e:
        logger.error(f"Errore recupero titolo ID {titolo_id}: {e}", exc_info=True)
        return None


def update_titolo_service(db_manager, titolo_id: int, nome_titolo: str, descrizione: str = None,
                          current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Aggiorna un titolo/diritto esistente."""
    logger.info(f"Tentativo aggiornamento titolo ID: {titolo_id} con nome: {nome_titolo}")
    check_query = "SELECT id FROM titoli_diritti WHERE nome_titolo = %s AND id != %s"
    existing = db_manager.execute_query(check_query, (nome_titolo, titolo_id), fetch_one=True)
    if existing:
        error_msg = f"Aggiornamento fallito: altro titolo (ID: {existing['id']}) ha già il nome '{nome_titolo}'."
        logger.warning(error_msg)
        if current_user_id: record_audit(db_manager, current_user_id, "UPDATE_TITOLO_FAIL", error_msg, "titoli_diritti", titolo_id, success=False)
        raise ValueError(error_msg)

    query = "UPDATE titoli_diritti SET nome_titolo = %s, descrizione = %s, updated_at = NOW() WHERE id = %s"
    try:
        db_manager.execute_query(query, (nome_titolo, descrizione, titolo_id))
        db_manager.commit()
        logger.info(f"Titolo ID: {titolo_id} aggiornato.")
        if current_user_id: record_audit(db_manager, current_user_id, "UPDATE_TITOLO", f"Titolo {nome_titolo} (ID:{titolo_id}) aggiornato.", "titoli_diritti", titolo_id, session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback(); logger.error(f"Errore Service aggiornamento titolo ID: {titolo_id}: {e}", exc_info=True)
        if current_user_id: record_audit(db_manager, current_user_id, "UPDATE_TITOLO_FAIL", f"Errore aggiornamento titolo {nome_titolo} (ID:{titolo_id}): {str(e)[:100]}", "titoli_diritti", titolo_id, success=False)
        raise

def delete_titolo_service(db_manager, titolo_id: int,
                          current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Cancella un titolo/diritto, solo se non ha dipendenze."""
    logger.warning(f"Tentativo cancellazione titolo ID: {titolo_id}.")
    # Controllo dipendenze (es. tabella 'intestazioni' o 'possessori_storico' se titolo_id è lì)
    # Adatta il nome della tabella e del campo FK al tuo schema
    dependency_check_query = "SELECT 1 FROM intestazioni WHERE titolo_id = %s LIMIT 1" 
    dependency = db_manager.execute_query(dependency_check_query, (titolo_id,), fetch_one=True)
    if dependency:
        error_msg = f"Impossibile cancellare titolo ID {titolo_id}: è utilizzato nelle intestazioni."
        logger.error(error_msg)
        if current_user_id: record_audit(db_manager, current_user_id, "DELETE_TITOLO_FAIL", error_msg, "titoli_diritti", titolo_id, success=False)
        raise ValueError(error_msg)
    
    query = "DELETE FROM titoli_diritti WHERE id = %s"
    try:
        db_manager.execute_query(query, (titolo_id,))
        db_manager.commit()
        logger.info(f"Titolo ID: {titolo_id} cancellato.")
        if current_user_id: record_audit(db_manager, current_user_id, "DELETE_TITOLO", f"Titolo (ID:{titolo_id}) cancellato.", "titoli_diritti", titolo_id, session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback(); logger.error(f"Errore Service cancellazione titolo ID: {titolo_id}: {e}", exc_info=True)
        if current_user_id: record_audit(db_manager, current_user_id, "DELETE_TITOLO_FAIL", f"Errore cancellazione titolo (ID:{titolo_id}): {str(e)[:100]}", "titoli_diritti", titolo_id, success=False)
        raise