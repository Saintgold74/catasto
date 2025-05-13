# core/services/partite_service.py
import logging
from datetime import date, datetime
from .audit_service import record_audit # Assumendo che audit_service.py sia nella stessa directory

# Ottieni un logger specifico per questo modulo
logger = logging.getLogger("CatastoAppLogger.PartiteService")

# --- Gestione Partite ---
def create_partita_service(db_manager, comune_id: int, numero_partita: str, sezione_id: int, 
                           data_creazione: date = None, data_soppressione: date = None, 
                           tipo_partita: str = None, note: str = None,
                           current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea una nuova partita catastale."""
    logger.info(f"Tentativo creazione partita: Numero {numero_partita}, Comune ID {comune_id}, Sezione ID {sezione_id}")

    if data_creazione is None:
        data_creazione = datetime.now().date()

    # Verifica se una partita con lo stesso numero, comune e sezione esiste già
    check_query = "SELECT id FROM partite WHERE comune_id = %s AND numero_partita = %s AND sezione_id = %s"
    existing_partita = db_manager.execute_query(check_query, (comune_id, numero_partita, sezione_id), fetch_one=True)
    if existing_partita:
        error_msg = f"Partita con Numero '{numero_partita}', Comune ID {comune_id}, Sezione ID {sezione_id} già esistente (ID: {existing_partita['id']})."
        logger.warning(error_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "CREATE_PARTITA_FAIL", error_msg, "partite", 
                         client_ip_address=client_ip_address, success=False)
        raise ValueError(error_msg)

    query = """
        INSERT INTO partite (comune_id, numero_partita, sezione_id, data_creazione, data_soppressione, tipo_partita, note, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW()) RETURNING id
    """
    params = (comune_id, numero_partita, sezione_id, data_creazione, data_soppressione, tipo_partita, note)
    
    try:
        result = db_manager.execute_query(query, params, fetch_one=True)
        if result and result['id']:
            partita_id = result['id']
            db_manager.commit()
            logger.info(f"Partita Numero '{numero_partita}' (ID: {partita_id}) creata con successo.")
            if current_user_id:
                record_audit(db_manager, current_user_id, "CREATE_PARTITA", 
                             f"Partita N.{numero_partita} (ID:{partita_id}) creata.", "partite", partita_id,
                             session_id, client_ip_address, success=True)
            return partita_id
        else:
            db_manager.rollback()
            logger.error(f"Creazione partita Numero '{numero_partita}' fallita (nessun ID ritornato).")
            if current_user_id:
                 record_audit(db_manager, current_user_id, "CREATE_PARTITA_FAIL", 
                              f"Fallimento creazione partita N.{numero_partita} (DB error).", "partite",
                              session_id=session_id, client_ip_address=client_ip_address, success=False)
            return None
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante creazione partita Numero '{numero_partita}': {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "CREATE_PARTITA_FAIL", 
                         f"Errore creazione partita N.{numero_partita}: {str(e)[:100]}", "partite",
                         session_id=session_id, client_ip_address=client_ip_address, success=False)
        raise

def get_partita_by_id_service(db_manager, partita_id: int):
    """Recupera una partita specifica tramite il suo ID, includendo nomi di comune e sezione."""
    logger.debug(f"Recupero partita con ID: {partita_id}")
    query = """
        SELECT p.id, p.numero_partita, p.comune_id, c.nome as nome_comune, 
               p.sezione_id, s.nome_sezione as nome_sezione, 
               p.data_creazione, p.data_soppressione, p.tipo_partita, p.note,
               p.created_at, p.updated_at
        FROM partite p
        JOIN comuni c ON p.comune_id = c.id
        JOIN sezioni s ON p.sezione_id = s.id
        WHERE p.id = %s
    """
    try:
        partita = db_manager.execute_query(query, (partita_id,), fetch_one=True)
        if partita:
            logger.debug(f"Partita ID: {partita_id} trovata: N.{partita['numero_partita']}")
        else:
            logger.warning(f"Partita ID: {partita_id} non trovata.")
        return partita
    except Exception as e:
        logger.error(f"Errore durante il recupero della partita ID {partita_id}: {e}", exc_info=True)
        return None

def get_partite_by_numero_service(db_manager, numero_partita: str, comune_id: int = None, sezione_id: int = None):
    """Recupera partite per numero, opzionalmente filtrate per comune e sezione."""
    logger.debug(f"Ricerca partite per Numero: {numero_partita}, ComuneID: {comune_id}, SezioneID: {sezione_id}")
    base_query = """
        SELECT p.id, p.numero_partita, c.nome as nome_comune, s.nome_sezione, 
               p.data_creazione, p.data_soppressione, p.tipo_partita
        FROM partite p
        JOIN comuni c ON p.comune_id = c.id
        JOIN sezioni s ON p.sezione_id = s.id
    """
    conditions = ["p.numero_partita = %s"]
    params = [numero_partita]

    if comune_id is not None:
        conditions.append("p.comune_id = %s")
        params.append(comune_id)
    if sezione_id is not None:
        conditions.append("p.sezione_id = %s")
        params.append(sezione_id)
    
    query = base_query + " WHERE " + " AND ".join(conditions) + " ORDER BY c.nome, s.nome_sezione, p.numero_partita"
    
    try:
        partite = db_manager.execute_query(query, tuple(params), fetch_all=True)
        logger.debug(f"Trovate {len(partite) if partite else 0} partite per numero '{numero_partita}'.")
        return partite
    except Exception as e:
        logger.error(f"Errore ricerca partite per numero '{numero_partita}': {e}", exc_info=True)
        return []

def update_partita_service(db_manager, partita_id: int, comune_id: int, numero_partita: str, sezione_id: int, 
                           data_creazione: date = None, data_soppressione: date = None, 
                           tipo_partita: str = None, note: str = None,
                           current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Aggiorna i dati di una partita esistente."""
    logger.info(f"Tentativo aggiornamento partita ID: {partita_id}")

    # Verifica unicità se numero/comune/sezione cambiano (escludendo la partita corrente)
    check_query = "SELECT id FROM partite WHERE comune_id = %s AND numero_partita = %s AND sezione_id = %s AND id != %s"
    existing_partita = db_manager.execute_query(check_query, (comune_id, numero_partita, sezione_id, partita_id), fetch_one=True)
    if existing_partita:
        error_msg = f"Aggiornamento fallito: altra partita (ID: {existing_partita['id']}) con Numero '{numero_partita}', Comune ID {comune_id}, Sezione ID {sezione_id} già esistente."
        logger.warning(error_msg)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_PARTITA_FAIL", error_msg, "partite", partita_id, 
                         session_id, client_ip_address, success=False)
        raise ValueError(error_msg)

    query = """
        UPDATE partite 
        SET comune_id = %s, numero_partita = %s, sezione_id = %s, 
            data_creazione = %s, data_soppressione = %s, tipo_partita = %s, note = %s, 
            updated_at = NOW()
        WHERE id = %s
    """
    params = (comune_id, numero_partita, sezione_id, data_creazione, data_soppressione, tipo_partita, note, partita_id)
    try:
        db_manager.execute_query(query, params)
        db_manager.commit()
        logger.info(f"Partita ID: {partita_id} aggiornata con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_PARTITA", 
                         f"Partita N.{numero_partita} (ID:{partita_id}) aggiornata.", "partite", partita_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante aggiornamento partita ID: {partita_id}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_PARTITA_FAIL", 
                         f"Errore aggiornamento partita N.{numero_partita} (ID:{partita_id}): {str(e)[:100]}", "partite", partita_id,
                         session_id, client_ip_address, success=False)
        raise

def delete_partita_service(db_manager, partita_id: int, 
                           current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Cancella una partita, solo se non ha dipendenze significative (es. intestazioni attive, immobili)."""
    logger.warning(f"Tentativo cancellazione partita ID: {partita_id}.")
    
    # 1. Controllo dipendenze (esempi, adatta al tuo schema e logica di business)
    # Dipendenza da intestazioni:
    dep_intest_query = "SELECT 1 FROM intestazioni WHERE partita_id = %s LIMIT 1"
    if db_manager.execute_query(dep_intest_query, (partita_id,), fetch_one=True):
        error_msg = f"Impossibile cancellare partita ID {partita_id}: esistono intestazioni associate."
        logger.error(error_msg); record_audit_fail(); raise ValueError(error_msg)

    # Dipendenza da immobili:
    dep_imm_query = "SELECT 1 FROM immobili WHERE partita_id = %s LIMIT 1"
    if db_manager.execute_query(dep_imm_query, (partita_id,), fetch_one=True):
        error_msg = f"Impossibile cancellare partita ID {partita_id}: esistono immobili associati."
        logger.error(error_msg); record_audit_fail(); raise ValueError(error_msg)

    # Dipendenza da volture:
    dep_volt_query = "SELECT 1 FROM volture WHERE partita_precedente_id = %s OR partita_attuale_id = %s LIMIT 1"
    if db_manager.execute_query(dep_volt_query, (partita_id, partita_id), fetch_one=True):
        error_msg = f"Impossibile cancellare partita ID {partita_id}: è coinvolta in volture."
        logger.error(error_msg); record_audit_fail(); raise ValueError(error_msg)
        
    # Dipendenza da documenti_partite:
    dep_doc_query = "SELECT 1 FROM documenti_partite WHERE partita_id = %s LIMIT 1"
    if db_manager.execute_query(dep_doc_query, (partita_id,), fetch_one=True):
        # Potrebbe essere accettabile cancellare i link o chiedere conferma
        logger.warning(f"La partita ID {partita_id} ha documenti associati. I link verranno rimossi.")
        # Esegui la cancellazione dei link prima di cancellare la partita:
        # delete_links_query = "DELETE FROM documenti_partite WHERE partita_id = %s"
        # db_manager.execute_query(delete_links_query, (partita_id,))
        # Questa logica di cancellazione a cascata o blocco deve essere decisa attentamente.

    def record_audit_fail(msg=None): # Funzione helper locale per audit fallimento
        if current_user_id:
            details = msg or f"Fallimento cancellazione partita (ID:{partita_id}) a causa di dipendenze."
            record_audit(db_manager, current_user_id, "DELETE_PARTITA_FAIL", details, "partite", partita_id, 
                         session_id, client_ip_address, success=False)

    query = "DELETE FROM partite WHERE id = %s"
    try:
        db_manager.execute_query(query, (partita_id,))
        db_manager.commit()
        logger.info(f"Partita ID: {partita_id} cancellata con successo (dopo controllo dipendenze).")
        if current_user_id:
            record_audit(db_manager, current_user_id, "DELETE_PARTITA", 
                         f"Partita (ID:{partita_id}) cancellata.", "partite", partita_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante cancellazione partita ID: {partita_id}: {e}", exc_info=True)
        if current_user_id:
             record_audit(db_manager, current_user_id, "DELETE_PARTITA_FAIL", 
                          f"Errore cancellazione partita (ID:{partita_id}): {str(e)[:100]}", "partite", partita_id,
                          session_id, client_ip_address, success=False)
        raise

def search_partite_service(db_manager, comune_id: int = None, sezione_id: int = None, numero_partita: str = None, 
                           cognome_possessore: str = None, nome_possessore: str = None, cf_possessore: str = None,
                           fg: str = None, particella: str = None, subalterno: str = None): # Aggiunti campi per ricerca immobile
    """Ricerca avanzata di partite."""
    logger.info(f"Ricerca partite avanzata con criteri: Comune {comune_id}, Sezione {sezione_id}, N.Partita {numero_partita}, Possessore {cognome_possessore} {nome_possessore} ({cf_possessore}), Immobile Fg:{fg}/Part:{particella}/Sub:{subalterno}")

    select_clause = """
        SELECT DISTINCT p.id, p.numero_partita, c.nome AS nome_comune, s.nome_sezione,
                        p.data_creazione, p.data_soppressione, p.tipo_partita
        FROM partite p
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
    if numero_partita:
        conditions.append("p.numero_partita ILIKE %s")
        params.append(f"%{numero_partita}%")

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
    
    if fg or particella or subalterno:
        joins.append("JOIN immobili imm ON p.id = imm.partita_id")
        if fg:
            conditions.append("imm.foglio ILIKE %s")
            params.append(f"%{fg}%")
        if particella:
            conditions.append("imm.numero_particella ILIKE %s")
            params.append(f"%{particella}%")
        if subalterno:
            conditions.append("imm.subalterno ILIKE %s")
            params.append(f"%{subalterno}%")

    # Rimuovi join duplicati
    unique_joins = list(dict.fromkeys(joins))
    query = select_clause + " " + " ".join(unique_joins)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY c.nome, s.nome_sezione, p.numero_partita"
    
    try:
        partite = db_manager.execute_query(query, tuple(params), fetch_all=True)
        logger.info(f"Trovate {len(partite) if partite else 0} partite per i criteri di ricerca.")
        return partite
    except Exception as e:
        logger.error(f"Errore durante la ricerca avanzata delle partite: {e}", exc_info=True)
        return []

# --- Gestione Intestazioni (Link Partita-Possessore) ---
def link_possessore_a_partita_service(db_manager, partita_id: int, possessore_id: int, 
                                      qualifica_id: int, titolo_id: int, 
                                      quota_diritto: str = None, data_inizio_validita: date = None, 
                                      data_fine_validita: date = None, note: str = None,
                                      current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Crea o aggiorna un'intestazione (link tra partita e possessore con dettagli)."""
    logger.info(f"Collegamento possessore ID {possessore_id} a partita ID {partita_id}")

    if data_inizio_validita is None:
        data_inizio_validita = datetime.now().date()

    # Upsert: inserisce se non esiste, altrimenti aggiorna.
    # L'unicità è data da (partita_id, possessore_id, qualifica_id, titolo_id, data_inizio_validita)
    # o una combinazione più semplice se il modello di business lo permette.
    # Per un vero upsert, la tabella dovrebbe avere un UNIQUE constraint su questi campi.
    # Qui simuliamo un controllo e poi INSERT o UPDATE (o usiamo ON CONFLICT DO UPDATE di PostgreSQL)

    query_upsert = """
        INSERT INTO intestazioni (partita_id, possessore_id, qualifica_id, titolo_id, quota_diritto, data_inizio_validita, data_fine_validita, note, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (partita_id, possessore_id, qualifica_id, titolo_id, data_inizio_validita) -- Assumendo questo constraint
        DO UPDATE SET quota_diritto = EXCLUDED.quota_diritto,
                      data_fine_validita = EXCLUDED.data_fine_validita,
                      note = EXCLUDED.note,
                      updated_at = NOW()
        RETURNING id, CASE WHEN xmax = 0 THEN 'INSERT' ELSE 'UPDATE' END AS operation; 
        -- xmax = 0 per INSERT, xmax != 0 per UPDATE (in PostgreSQL)
    """
    # Se non hai un constraint di unicità che copra data_inizio_validita,
    # l'upsert ON CONFLICT potrebbe non funzionare come atteso per registrazioni multiple con date diverse.
    # In quel caso, dovresti prima cercare un'intestazione "attiva" simile e magari "chiuderla" (impostando data_fine_validita)
    # prima di inserirne una nuova. Questa logica di storicizzazione può essere complessa.
    # Il tuo codice originale CatastoDBManager faceva un semplice INSERT. Adotterò un INSERT
    # con possibilità di errore se esiste già una combinazione identica (se hai un UNIQUE constraint).
    # Per ora, un semplice INSERT. Se l'UI deve gestire l'aggiornamento, lo farà chiamando un update_intestazione_service.

    query_insert = """
        INSERT INTO intestazioni (partita_id, possessore_id, qualifica_id, titolo_id, quota_diritto, data_inizio_validita, data_fine_validita, note, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()) RETURNING id
    """
    params = (partita_id, possessore_id, qualifica_id, titolo_id, quota_diritto, data_inizio_validita, data_fine_validita, note)

    try:
        # Verifichiamo se esiste già un link IDENTICO per evitare duplicati se non c'è constraint
        # Questo è un controllo base. La logica di storicizzazione effettiva (chiudere vecchie intestazioni, aprirne nuove)
        # è più complessa e dipende dai requisiti.
        check_query = """
        SELECT id FROM intestazioni WHERE partita_id = %s AND possessore_id = %s AND qualifica_id = %s AND titolo_id = %s 
                                 AND data_inizio_validita = %s 
                                 AND (data_fine_validita IS NULL AND %s IS NULL OR data_fine_validita = %s) 
        """ # Confronta anche data_fine_validita
        existing_link = db_manager.execute_query(check_query, (partita_id, possessore_id, qualifica_id, titolo_id, data_inizio_validita, data_fine_validita, data_fine_validita), fetch_one=True)
        
        if existing_link:
            logger.warning(f"Link identico già esistente (ID: {existing_link['id']}) per Partita {partita_id} e Possessore {possessore_id}. Nessuna azione intrapresa.")
            # Non è un errore, ma non si fa nulla o si aggiorna. Per ora, non facciamo nulla.
            # Potresti voler aggiornare le note o la quota se è l'unica cosa che cambia.
            return existing_link['id'] # Ritorna l'ID del link esistente


        result = db_manager.execute_query(query_insert, params, fetch_one=True)
        if result and result['id']:
            intestazione_id = result['id']
            db_manager.commit()
            logger.info(f"Intestazione (ID: {intestazione_id}) creata: Partita {partita_id} -> Possessore {possessore_id}.")
            if current_user_id:
                record_audit(db_manager, current_user_id, "LINK_POSS_PARTITA", 
                             f"Link creato Partita ID {partita_id} - Possessore ID {possessore_id}.", 
                             "intestazioni", intestazione_id, session_id, client_ip_address, success=True)
            return intestazione_id
        else:
            db_manager.rollback()
            logger.error(f"Creazione link Partita {partita_id} - Possessore {possessore_id} fallita.")
            if current_user_id: record_audit(db_manager, current_user_id, "LINK_POSS_PARTITA_FAIL", "DB error creazione link.", "intestazioni", success=False)
            return None
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service link Partita {partita_id} - Possessore {possessore_id}: {e}", exc_info=True)
        if current_user_id: record_audit(db_manager, current_user_id, "LINK_POSS_PARTITA_FAIL", f"Errore creazione link: {str(e)[:100]}", "intestazioni", success=False)
        raise

def get_intestazioni_partita_service(db_manager, partita_id: int):
    """Recupera tutte le intestazioni (possessori) per una data partita."""
    logger.debug(f"Recupero intestazioni per partita ID: {partita_id}")
    query = """
        SELECT i.id as intestazione_id, i.partita_id, i.possessore_id, 
               pos.cognome_denominazione, pos.nome, pos.codice_fiscale_partita_iva,
               i.qualifica_id, q.nome_qualifica, 
               i.titolo_id, t.nome_titolo,
               i.quota_diritto, i.data_inizio_validita, i.data_fine_validita, i.note as note_intestazione
        FROM intestazioni i
        JOIN possessori pos ON i.possessore_id = pos.id
        JOIN qualifiche_possessore q ON i.qualifica_id = q.id
        JOIN titoli_diritti t ON i.titolo_id = t.id
        WHERE i.partita_id = %s
        ORDER BY i.data_inizio_validita DESC, pos.cognome_denominazione, pos.nome
    """
    try:
        intestazioni = db_manager.execute_query(query, (partita_id,), fetch_all=True)
        logger.debug(f"Trovate {len(intestazioni) if intestazioni else 0} intestazioni per partita ID {partita_id}.")
        return intestazioni
    except Exception as e:
        logger.error(f"Errore recupero intestazioni per partita ID {partita_id}: {e}", exc_info=True)
        return []

def get_partite_possessore_service(db_manager, possessore_id: int):
    """Recupera tutte le partite intestate a un dato possessore."""
    logger.debug(f"Recupero partite per possessore ID: {possessore_id}")
    query = """
        SELECT p.id as partita_id, p.numero_partita, c.nome as nome_comune, s.nome_sezione,
               i.id as intestazione_id, q.nome_qualifica, t.nome_titolo, i.quota_diritto,
               i.data_inizio_validita, i.data_fine_validita
        FROM intestazioni i
        JOIN partite p ON i.partita_id = p.id
        JOIN comuni c ON p.comune_id = c.id
        JOIN sezioni s ON p.sezione_id = s.id
        JOIN qualifiche_possessore q ON i.qualifica_id = q.id
        JOIN titoli_diritti t ON i.titolo_id = t.id
        WHERE i.possessore_id = %s
        ORDER BY c.nome, s.nome_sezione, p.numero_partita, i.data_inizio_validita DESC
    """
    try:
        partite = db_manager.execute_query(query, (possessore_id,), fetch_all=True)
        logger.debug(f"Trovate {len(partite) if partite else 0} partite per possessore ID {possessore_id}.")
        return partite
    except Exception as e:
        logger.error(f"Errore recupero partite per possessore ID {possessore_id}: {e}", exc_info=True)
        return []

def update_intestazione_service(db_manager, intestazione_id: int, qualifica_id: int, titolo_id: int,
                                quota_diritto: str = None, data_inizio_validita: date = None, 
                                data_fine_validita: date = None, note: str = None,
                                current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Aggiorna i dettagli di un'intestazione esistente."""
    logger.info(f"Tentativo aggiornamento intestazione ID: {intestazione_id}")
    
    # Logica per assicurare che data_inizio_validita non sia modificata se non esplicitamente o se causa sovrapposizioni
    # Questa parte può diventare complessa a seconda delle regole di storicizzazione.
    # Per ora, permettiamo l'aggiornamento dei campi forniti.

    query = """
        UPDATE intestazioni
        SET qualifica_id = %s, titolo_id = %s, quota_diritto = %s, 
            data_inizio_validita = COALESCE(%s, data_inizio_validita), -- Non aggiorna se None
            data_fine_validita = %s, -- Può essere impostata a NULL
            note = %s, 
            updated_at = NOW()
        WHERE id = %s
    """
    params = (qualifica_id, titolo_id, quota_diritto, data_inizio_validita, data_fine_validita, note, intestazione_id)
    
    try:
        db_manager.execute_query(query, params)
        db_manager.commit()
        logger.info(f"Intestazione ID: {intestazione_id} aggiornata con successo.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_INTESTAZIONE", 
                         f"Intestazione (ID:{intestazione_id}) aggiornata.", "intestazioni", intestazione_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante aggiornamento intestazione ID: {intestazione_id}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "UPDATE_INTESTAZIONE_FAIL", 
                         f"Errore aggiornamento intestazione (ID:{intestazione_id}): {str(e)[:100]}", "intestazioni", intestazione_id,
                         session_id, client_ip_address, success=False)
        raise

def unlink_possessore_da_partita_service(db_manager, intestazione_id: int,
                                         current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Rimuove un'intestazione (scollega un possessore da una partita)."""
    # Invece di cancellare, spesso è meglio "chiudere" l'intestazione impostando data_fine_validita.
    # Se vuoi cancellare fisicamente:
    logger.warning(f"Tentativo cancellazione fisica intestazione ID: {intestazione_id}. Considerare la chiusura logica.")
    
    query = "DELETE FROM intestazioni WHERE id = %s"
    try:
        # Potrebbe essere necessario un controllo se questa intestazione è referenziata da volture come "intestazione_cedente" o "acquirente"
        # se lo schema lo prevede.
        db_manager.execute_query(query, (intestazione_id,))
        db_manager.commit()
        logger.info(f"Intestazione ID: {intestazione_id} cancellata fisicamente.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "UNLINK_POSS_PARTITA", 
                         f"Intestazione (ID:{intestazione_id}) cancellata fisicamente.", "intestazioni", intestazione_id,
                         session_id, client_ip_address, success=True)
        return True
    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante cancellazione intestazione ID: {intestazione_id}: {e}", exc_info=True)
        if current_user_id:
             record_audit(db_manager, current_user_id, "UNLINK_POSS_PARTITA_FAIL", 
                          f"Errore cancellazione intestazione (ID:{intestazione_id}): {str(e)[:100]}", "intestazioni", intestazione_id,
                          session_id, client_ip_address, success=False)
        raise

def close_intestazione_service(db_manager, intestazione_id: int, data_fine: date = None,
                               current_user_id: int = None, session_id: str = None, client_ip_address: str = None):
    """Chiude logicamente un'intestazione impostando la data_fine_validita."""
    logger.info(f"Tentativo chiusura logica intestazione ID: {intestazione_id}")
    if data_fine is None:
        data_fine = datetime.now().date()
    
    query = "UPDATE intestazioni SET data_fine_validita = %s, updated_at = NOW() WHERE id = %s AND data_fine_validita IS NULL"
    try:
        db_manager.execute_query(query, (data_fine, intestazione_id))
        db_manager.commit() # Assumendo che execute_query restituisca rowcount o sollevi errore
        # Controlla se la riga è stata effettivamente aggiornata (es. rowcount == 1)
        logger.info(f"Intestazione ID: {intestazione_id} chiusa logicamente al {data_fine}.")
        if current_user_id:
            record_audit(db_manager, current_user_id, "CLOSE_INTESTAZIONE", 
                         f"Intestazione (ID:{intestazione_id}) chiusa al {data_fine}.", "intestazioni", intestazione_id,
                         session_id, client_ip_address, success=True)
        return True

    except Exception as e:
        db_manager.rollback()
        logger.error(f"Errore Service durante chiusura intestazione ID: {intestazione_id}: {e}", exc_info=True)
        if current_user_id:
            record_audit(db_manager, current_user_id, "CLOSE_INTESTAZIONE_FAIL", 
                         f"Errore chiusura intestazione (ID:{intestazione_id}): {str(e)[:100]}", "intestazioni", intestazione_id,
                         session_id, client_ip_address, success=False)
        raise