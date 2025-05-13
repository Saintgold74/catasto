# core/services/immobili_service.py
import logging
from datetime import date, datetime
from .audit_service import record_audit

logger = logging.getLogger("CatastoAppLogger.ImmobiliService")

# --- Gestione Immobili ---
def create_immobile_service(db_manager, partita_id: int, foglio: str, numero_particella: str, 
                            subalterno: str = None, categoria_catastale: str = None, classe: str = None,
                            consistenza: str = None, rendita: float = None, 
                            data_inizio_validita: date = None, data_fine_validita: date = None,
                            note: str = None, indirizzo_manuale: str = None,
                            current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea un nuovo immobile associato a una partita."""
    logger.info(f"Tentativo creazione immobile per Partita ID {partita_id}: Fg.{foglio}/Part.{numero_particella}/Sub.{subalterno or ''}")

    if data_inizio_validita is None:
        data_inizio_validita = datetime.now().date()

    # Verifica se un immobile identico (stessa partita, foglio, particella, sub) esiste già ed è "attivo"
    # (cioè data_fine_validita IS NULL o futura). Questo dipende dalle regole di storicizzazione.
    # Per ora, assumiamo che la combinazione partita_id, foglio, numero_particella, subalterno debba essere unica
    # per gli immobili "attualmente validi" o che si voglia permettere la storicizzazione (più record per lo stesso identificativo
    # ma con periodi di validità diversi). Il tuo codice originale non sembrava avere questo controllo esplicito per create_immobile.
    # Se si vuole unicità per Fg/Part/Sub attivi per una data partita, aggiungere un check.

    query = """
        INSERT INTO immobili (
            partita_id, foglio, numero_particella, subalterno, categoria_catastale, classe,
            consistenza, rendita, data_inizio_validita, data_fine_validita, note, indirizzo_manuale, 
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        ) RETURNING id
    """
    params = (
        partita_id, foglio, numero_particella, subalterno, categoria_catastale, classe,
        consistenza, rendita, data_inizio_validita, data_fine_validita, note, indirizzo_manuale
    )
    
    try:
        result = db_manager.execute_query(query, params, fetch_one=True)
        if result and result['id']:
            immobile_id = result['id']
            db_manager.commit()
            log_msg = f"Immobile Fg.{foglio}/Part.{numero_particella}/Sub.{subalterno or ''} (ID: {immobile_id}) creato per Partita ID {partita_id}."
            logger.info(log_msg)
            if current_user_id:
                record_audit(db_manager, current_user_id, "CREATE_IMMOBILE", log_msg, 
                             "immobili", immobile_id, session_id, client_ip_address, success=True)
            return immobile_id
        else:
            db_manager.rollback()
            logger.error(f"Creazione immobile Fg.{foglio}/Part.{numero_particella} fallita (nessun ID ritornato).")
            if current_user_id:
                record_audit(db_manager, current_user_id, "CREATE_IMMOBILE_FAIL", 
                             f"Fallimento creazione immobile Fg.{foglio}/Part.{numero_particella} (DB error).", 
                             "immobili", session_id=session_id, client_ip_address=client_ip_address, success=False)
            return None
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service creazione immobile Fg.{foglio}/Part.{numero_particella}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "CREATE_IMMOBILE_FAIL", 
                         f"Errore creazione immobile Fg.{foglio}/Part.{numero_particella}: {str(e)[:100]}", 
                         "immobili", session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise

def get_immobili_by_partita_service(db_manager, partita_id: int):
    """Recupera tutti gli immobili associati a una data partita."""
    logger.debug(f"Recupero immobili per Partita ID: {partita_id}")
    query = """
        SELECT id, partita_id, foglio, numero_particella, subalterno, categoria_catastale, 
               classe, consistenza, rendita, data_inizio_validita, data_fine_validita, 
               note, indirizzo_manuale
        FROM immobili
        WHERE partita_id = %s
        ORDER BY foglio, numero_particella, subalterno, data_inizio_validita DESC
    """
    try:
        immobili = db_manager.execute_query(query, (partita_id,), fetch_all=True)
        logger.debug(f"Trovati {len(immobili) if immobili else 0} immobili per Partita ID {partita_id}.")
        return immobili
    except Exception as e:
        logger.error(f"Errore recupero immobili per Partita ID {partita_id}: {e}", exc_info=True)
        return []

def get_immobile_by_id_service(db_manager, immobile_id: int):
    """Recupera un immobile specifico tramite il suo ID."""
    logger.debug(f"Recupero immobile con ID: {immobile_id}")
    query = """
        SELECT id, partita_id, foglio, numero_particella, subalterno, categoria_catastale, 
               classe, consistenza, rendita, data_inizio_validita, data_fine_validita, 
               note, indirizzo_manuale, created_at, updated_at
        FROM immobili
        WHERE id = %s
    """
    try:
        immobile = db_manager.execute_query(query, (immobile_id,), fetch_one=True)
        if immobile:
            logger.debug(f"Immobile ID: {immobile_id} trovato.")
        else:
            logger.warning(f"Immobile ID: {immobile_id} non trovato.")
        return immobile
    except Exception as e:
        logger.error(f"Errore durante il recupero dell'immobile ID {immobile_id}: {e}", exc_info=True)
        return None

def update_immobile_service(db_manager, immobile_id: int, dati_immobile: dict,
                            current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Aggiorna i dati di un immobile esistente."""
    logger.info(f"Tentativo aggiornamento immobile ID: {immobile_id}")

    # Il tuo codice originale non sembrava avere un controllo di unicità qui,
    # ma se foglio/particella/sub per una data partita devono essere unici per immobili attivi,
    # andrebbe aggiunto un check simile a create_immobile_service.

    # Costruzione dinamica dei campi da aggiornare o query completa
    # Per semplicità, assumiamo che dati_immobile contenga tutti i campi necessari
    query = """
        UPDATE immobili SET
            partita_id = %(partita_id)s, 
            foglio = %(foglio)s, 
            numero_particella = %(numero_particella)s, 
            subalterno = %(subalterno)s, 
            categoria_catastale = %(categoria_catastale)s, 
            classe = %(classe)s,
            consistenza = %(consistenza)s, 
            rendita = %(rendita)s, 
            data_inizio_validita = %(data_inizio_validita)s, 
            data_fine_validita = %(data_fine_validita)s, 
            note = %(note)s,
            indirizzo_manuale = %(indirizzo_manuale)s,
            updated_at = NOW()
        WHERE id = %(immobile_id)s
    """
    # Assicurati che 'immobile_id' sia in dati_immobile
    dati_immobile['immobile_id'] = immobile_id

    try:
        db_manager.execute_query(query, dati_immobile)
        db_manager.commit()
        log_msg = f"Immobile ID: {immobile_id} (Fg.{dati_immobile.get('foglio')}/Part.{dati_immobile.get('numero_particella')}) aggiornato."
        logger.info(log_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_IMMOBILE", log_msg, 
                         "immobili", immobile_id, session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante aggiornamento immobile ID: {immobile_id}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_IMMOBILE_FAIL", 
                         f"Errore aggiornamento immobile ID {immobile_id}: {str(e)[:100]}", 
                         "immobili", immobile_id, session_id, client_ip_address, success=False)
        raise

def delete_immobile_service(db_manager, immobile_id: int, 
                            current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Cancella un immobile, solo se non ha dipendenze critiche (es. indirizzi, se non si vuole cancellarli a cascata)."""
    logger.warning(f"Tentativo cancellazione immobile ID: {immobile_id}.")
    
    # Controllo dipendenze (es. indirizzi associati)
    dep_indir_query = "SELECT 1 FROM indirizzi WHERE immobile_id = %s LIMIT 1"
    if db_manager.execute_query(dep_indir_query, (immobile_id,), fetch_one=True):
        # Decisione da prendere: cancellare a cascata gli indirizzi o bloccare?
        # Per ora blocchiamo e richiediamo la cancellazione manuale degli indirizzi.
        error_msg = f"Impossibile cancellare immobile ID {immobile_id}: esistono indirizzi associati. Rimuovere prima gli indirizzi."
        logger.error(error_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_IMMOBILE_FAIL", error_msg, 
                         "immobili", immobile_id, session_id, client_ip_address, success=False)
        raise ValueError(error_msg)
        # Se si volesse cancellare a cascata:
        # delete_indirizzi_query = "DELETE FROM indirizzi WHERE immobile_id = %s"
        # db_manager.execute_query(delete_indirizzi_query, (immobile_id,))

    query = "DELETE FROM immobili WHERE id = %s"
    try:
        db_manager.execute_query(query, (immobile_id,))
        db_manager.commit()
        logger.info(f"Immobile ID: {immobile_id} cancellato con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_IMMOBILE", 
                         f"Immobile (ID:{immobile_id}) cancellato.", "immobili", immobile_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante cancellazione immobile ID: {immobile_id}: {e}", exc_info=True)
        if current_user_id:
             record_audit(db_manager, current_user_id, "DELETE_IMMOBILE_FAIL", 
                          f"Errore cancellazione immobile (ID:{immobile_id}): {str(e)[:100]}", 
                          "immobili", immobile_id, session_id, client_ip_address, success=False)
        raise

def search_immobili_avanzato_service(db_manager, comune_id: int=None, sezione_id: int=None, foglio: str=None, 
                                     numero_particella: str=None, subalterno: str=None, 
                                     cognome_possessore: str=None, nome_possessore: str=None, cf_possessore: str=None,
                                     via: str=None, civico: str=None):
    """Ricerca avanzata di immobili basata su vari criteri."""
    logger.info(f"Ricerca immobili avanzata con criteri: ComuneID {comune_id}, SezioneID {sezione_id}, Fg {foglio}, Part {numero_particella}, Sub {subalterno}, Poss {cognome_possessore} {nome_possessore}, Indirizzo {via} {civico}")

    select_clause = """
        SELECT DISTINCT imm.id as immobile_id, imm.foglio, imm.numero_particella, imm.subalterno,
                        imm.categoria_catastale, imm.classe, imm.consistenza, imm.rendita,
                        p.id as partita_id, p.numero_partita,
                        c.nome as nome_comune, s.nome_sezione
        FROM immobili imm
        JOIN partite p ON imm.partita_id = p.id
        JOIN comuni c ON p.comune_id = c.id
        JOIN sezioni s ON p.sezione_id = s.id
    """
    joins = []
    conditions = []
    params = []

    if comune_id:
        conditions.append("p.comune_id = %s")
        params.append(comune_id)
    if sezione_id:
        conditions.append("p.sezione_id = %s")
        params.append(sezione_id)
    if foglio:
        conditions.append("imm.foglio ILIKE %s")
        params.append(f"%{foglio}%")
    if numero_particella:
        conditions.append("imm.numero_particella ILIKE %s")
        params.append(f"%{numero_particella}%")
    if subalterno:
        conditions.append("imm.subalterno ILIKE %s")
        params.append(f"%{subalterno}%")

    if cognome_possessore or nome_possessore or cf_possessore:
        joins.append("JOIN intestazioni i ON p.id = i.partita_id")
        joins.append("JOIN possessori pos ON i.possessore_id = pos.id")
        if cognome_possessore:
            conditions.append("pos.cognome_denominazione ILIKE %s")
            params.append(f"%{cognome_possessore}%")
        if nome_possessore:
            conditions.append("pos.nome ILIKE %s")
            params.append(f"%{nome_possessore}%")
        if cf_possessore:
            conditions.append("pos.codice_fiscale_partita_iva ILIKE %s")
            params.append(f"%{cf_possessore}%")
        # Per le intestazioni attive, potresti aggiungere:
        # conditions.append("(i.data_fine_validita IS NULL OR i.data_fine_validita >= CURRENT_DATE)")


    if via or civico:
        joins.append("LEFT JOIN indirizzi ind ON imm.id = ind.immobile_id") # LEFT JOIN se un immobile può non avere indirizzo in DB
        if via:
            conditions.append("ind.via ILIKE %s")
            params.append(f"%{via}%")
        if civico:
            conditions.append("ind.numero_civico ILIKE %s")
            params.append(f"%{civico}%")
        # Se si cerca anche nell'indirizzo_manuale dell'immobile:
        # if via and not (cognome_possessore or nome_possessore or cf_possessore): # Evita OR complessi se già joinato per indirizzi
        #    conditions.append("imm.indirizzo_manuale ILIKE %s")
        #    params.append(f"%{via}%")


    unique_joins = list(dict.fromkeys(joins)) # Rimuove duplicati se joinato più volte
    query = select_clause + " " + " ".join(unique_joins)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY c.nome, s.nome_sezione, imm.foglio, imm.numero_particella, imm.subalterno"
    
    try:
        immobili = db_manager.execute_query(query, tuple(params), fetch_all=True)
        logger.info(f"Trovati {len(immobili) if immobili else 0} immobili per i criteri di ricerca avanzata.")
        return immobili
    except Exception as e:
        logger.error(f"Errore durante la ricerca avanzata degli immobili: {e}", exc_info=True)
        return []

# --- Gestione Indirizzi (associati agli immobili) ---
def create_indirizzo_service(db_manager, immobile_id: int, via: str, numero_civico: str, 
                             interno: str = None, scala: str = None, piano: str = None, 
                             cap: str = None, comune_indirizzo_id: int = None, frazione: str = None, note: str = None,
                             current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea un nuovo indirizzo per un immobile."""
    logger.info(f"Tentativo creazione indirizzo per Immobile ID {immobile_id}: {via} {numero_civico}")
    
    # Potrebbe esserci un controllo per evitare indirizzi duplicati per lo stesso immobile, se necessario

    query = """
        INSERT INTO indirizzi (
            immobile_id, via, numero_civico, interno, scala, piano, cap, 
            comune_id, frazione, note, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        ) RETURNING id
    """
    params = (
        immobile_id, via, numero_civico, interno, scala, piano, cap, 
        comune_indirizzo_id, frazione, note
    )
    try:
        result = db_manager.execute_query(query, params, fetch_one=True)
        if result and result['id']:
            indirizzo_id = result['id']
            db_manager.commit()
            log_msg = f"Indirizzo ID {indirizzo_id} ({via} {numero_civico}) creato per Immobile ID {immobile_id}."
            logger.info(log_msg)
            if current_user_id:
                record_audit(db_manager, current_user_id, "CREATE_INDIRIZZO", log_msg, 
                             "indirizzi", indirizzo_id, session_id, client_ip_address, success=True)
            return indirizzo_id
        else:
            db_manager.rollback()
            logger.error(f"Creazione indirizzo {via} {numero_civico} fallita.")
            if current_user_id: record_audit(db_manager, current_user_id, "CREATE_INDIRIZZO_FAIL", "DB error", "indirizzi", success=False)
            return None
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service creazione indirizzo {via} {numero_civico}: {e}", exc_info=True)
        if current_user_id: record_audit(db_manager, current_user_id, "CREATE_INDIRIZZO_FAIL", f"Errore: {str(e)[:100]}", "indirizzi", success=False)
        raise

def get_indirizzi_by_immobile_service(db_manager, immobile_id: int):
    """Recupera tutti gli indirizzi associati a un immobile."""
    logger.debug(f"Recupero indirizzi per Immobile ID: {immobile_id}")
    query = """
        SELECT i.id, i.immobile_id, i.via, i.numero_civico, i.interno, i.scala, i.piano, 
               i.cap, i.comune_id as comune_indirizzo_id, c.nome as nome_comune_indirizzo, i.frazione, i.note
        FROM indirizzi i
        LEFT JOIN comuni c ON i.comune_id = c.id 
        WHERE i.immobile_id = %s
        ORDER BY i.via, i.numero_civico -- O un altro ordine logico
    """
    try:
        indirizzi = db_manager.execute_query(query, (immobile_id,), fetch_all=True)
        logger.debug(f"Trovati {len(indirizzi) if indirizzi else 0} indirizzi per Immobile ID {immobile_id}.")
        return indirizzi
    except Exception as e:
        logger.error(f"Errore recupero indirizzi per Immobile ID {immobile_id}: {e}", exc_info=True)
        return []

def update_indirizzo_service(db_manager, indirizzo_id: int, dati_indirizzo: dict,
                             current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Aggiorna i dati di un indirizzo esistente."""
    logger.info(f"Tentativo aggiornamento indirizzo ID: {indirizzo_id}")
    
    query = """
        UPDATE indirizzi SET
            immobile_id = %(immobile_id)s, 
            via = %(via)s, 
            numero_civico = %(numero_civico)s, 
            interno = %(interno)s, 
            scala = %(scala)s, 
            piano = %(piano)s, 
            cap = %(cap)s, 
            comune_id = %(comune_id)s, 
            frazione = %(frazione)s, 
            note = %(note)s,
            updated_at = NOW()
        WHERE id = %(indirizzo_id)s
    """
    dati_indirizzo['indirizzo_id'] = indirizzo_id
    try:
        db_manager.execute_query(query, dati_indirizzo)
        db_manager.commit()
        log_msg = f"Indirizzo ID {indirizzo_id} ({dati_indirizzo.get('via')} {dati_indirizzo.get('numero_civico')}) aggiornato."
        logger.info(log_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_INDIRIZZO", log_msg, 
                         "indirizzi", indirizzo_id, session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service aggiornamento indirizzo ID: {indirizzo_id}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_INDIRIZZO_FAIL", 
                         f"Errore aggiornamento indirizzo ID {indirizzo_id}: {str(e)[:100]}", 
                         "indirizzi", indirizzo_id, session_id, client_ip_address, success=False)
        raise

def delete_indirizzo_service(db_manager, indirizzo_id: int,
                             current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Cancella un indirizzo."""
    logger.warning(f"Tentativo cancellazione indirizzo ID: {indirizzo_id}.")
    # Gli indirizzi di solito non hanno dipendenze che bloccano la cancellazione,
    # a meno che non siano referenziati altrove (es. documenti di spedizione, non in questo contesto).
    query = "DELETE FROM indirizzi WHERE id = %s"
    try:
        db_manager.execute_query(query, (indirizzo_id,))
        db_manager.commit()
        logger.info(f"Indirizzo ID: {indirizzo_id} cancellato con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_INDIRIZZO", 
                         f"Indirizzo (ID:{indirizzo_id}) cancellato.", "indirizzi", indirizzo_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service cancellazione indirizzo ID: {indirizzo_id}: {e}", exc_info=True)
        if current_user_id:
             record_audit(db_manager, current_user_id, "DELETE_INDIRIZZO_FAIL", 
                          f"Errore cancellazione indirizzo (ID:{indirizzo_id}): {str(e)[:100]}", 
                          "indirizzi", indirizzo_id, session_id, client_ip_address, success=False)
        raise