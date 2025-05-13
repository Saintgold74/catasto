# core/services/audit_service.py
import logging
from datetime import datetime
from typing import Optional, Any
import json # Per la conversione in JSON per campi jsonb

logger = logging.getLogger("CatastoAppLogger.AuditService")

def _map_action_to_operazione(action: str) -> Optional[str]:
    """
    Mappa una stringa di azione descrittiva a un singolo carattere per la colonna 'operazione'.
    La colonna 'operazione' nella tabella audit_log accetta 'I', 'U', 'D'.
    Questa funzione necessita di un'attenta mappatura o di un'estensione dei valori
    permessi nel CHECK constraint della colonna 'operazione' nel database.
    """
    action_upper = action.upper()
    # Mappature di base
    if "CREATE" in action_upper or "REGISTER_USER_SUCCESS" in action_upper or "INSERT" in action_upper:
        return 'I'
    elif "UPDATE" in action_upper or "CHANGE_PASSWORD_SUCCESS" in action_upper or "RESET_PASSWORD_SUCCESS" in action_upper:
        return 'U'
    elif "DELETE" in action_upper or "DEACTIVATE_USER_SUCCESS" in action_upper: # Assumendo che 'DELETE' qui significhi soft delete (che è un UPDATE) o hard delete
        return 'D' # O 'U' se il soft delete è un UPDATE di is_active

    # Per azioni non CRUD dirette o fallimenti, la mappatura a I,U,D è problematica
    # se 'operazione' è NOT NULL e ha solo I,U,D nel CHECK.
    # Potresti aggiungere 'L' (Login), 'F' (Fail), 'V' (View), 'E' (Error) al tuo CHECK constraint
    # e mappare di conseguenza.
    # Per ora, se non è una chiara I,U,D, restituiamo un placeholder o None,
    # ma questo causerà problemi se 'operazione' è NOT NULL senza un valore valido.
    # È FONDAMENTALE che tu decida come gestire questo mapping.
    
    # Esempio di mappatura più estesa (richiede modifica del CHECK constraint nel DB):
    if "LOGIN_SUCCESS" in action_upper: return 'L' # Login
    if "LOGOUT_SUCCESS" in action_upper: return 'O' # Logout (Other o Out)
    if "FAIL" in action_upper: return 'F'       # Failure
    if "GET" in action_upper or "VIEW" in action_upper or "SEARCH" in action_upper : return 'S' # Select/Search/View

    logger.warning(f"Azione di audit '{action}' non ha una mappatura chiara a I, U, D, L, O, F, S. Verrà usato un placeholder o potrebbe fallire.")
    # Se 'operazione' è NOT NULL e accetta solo I,U,D, questo causerà errore.
    # Usiamo 'X' come placeholder per "Azione non specificata/Altro"
    # DEVI AGGIUNGERE 'X', 'L', 'O', 'F', 'S' (e altri necessari) al tuo CHECK constraint su catasto.audit_log.operazione
    return 'X' 

def record_audit(db_manager, 
                 app_user_id_param: Optional[int], # Corrisponde a app_user_id (integer)
                 action: str, 
                 details_str: str = "", 
                 table_name_param: Optional[str] = None, # Corrisponde a tabella (varchar)
                 record_id_param: Any = None,        # Corrisponde a record_id (integer)
                 session_id_param: Optional[str] = None, # Corrisponde a session_id (varchar)
                 client_ip_address_param: Optional[str] = None, # Corrisponde a ip_address (varchar)
                 # 'success' rimosso perché non c'è nella tabella audit_log fornita
                 username_param: Optional[str] = None # Corrisponde a utente (varchar)
                ):
    """
    Registra un evento di audit nel database, adattato allo schema della tabella
    catasto.audit_log fornito dall'utente.
    """
    
    operazione_db = _map_action_to_operazione(action)
    
    # Gestione di record_id: la colonna nel DB è INTEGER
    record_id_db = None
    if record_id_param is not None:
        try:
            record_id_db = int(record_id_param)
        except (ValueError, TypeError):
            logger.warning(f"Audit: record_id '{record_id_param}' non è un intero valido, sarà registrato come NULL.")
            # Non impostare a str(record_id_param) perché la colonna DB è INTEGER

    # Prepara i dettagli per la colonna JSONB 'dati_dopo'
    # Include l'azione originale per contesto, dato che 'operazione' è solo un carattere.
    dati_dopo_jsonb = None
    if details_str or action: # Salva sempre l'azione originale nei dettagli se possibile
        log_details_content = {"message": details_str if details_str else "Nessun dettaglio aggiuntivo."}
        if action:
            log_details_content["original_action_string"] = action
        try:
            dati_dopo_jsonb = json.dumps(log_details_content)
        except TypeError:
            logger.error("Audit: dettagli non serializzabili in JSON.", exc_info=True)
            dati_dopo_jsonb = json.dumps({"message": "Errore: dettagli non serializzabili.", "original_action_string": action})

    # Query INSERT adattata ESATTAMENTE alle colonne della tabella catasto.audit_log dell'utente
    # Colonne: id, tabella, operazione, record_id, dati_prima, dati_dopo, utente, ip_address, timestamp, session_id, app_user_id
    # 'dati_prima' non è gestito da questa funzione al momento, verrà inserito come NULL.
    # 'id' e 'timestamp' hanno valori di default nel DB.
    query = """
        INSERT INTO catasto.audit_log (
            app_user_id,      -- integer, nullable
            tabella,          -- character varying(100), not null
            operazione,       -- character(1), not null (mappato da action)
            record_id,        -- integer, nullable
            dati_dopo,        -- jsonb, nullable (per i dettagli)
            utente,           -- character varying(100), nullable (per lo username testuale)
            ip_address,       -- character varying(40), nullable
            session_id,       -- character varying(100), nullable
            timestamp         -- timestamp without time zone, default CURRENT_TIMESTAMP
            -- 'dati_prima' non è incluso qui, sarà NULL o il suo default se definito
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
    """
    
    params = (
        app_user_id_param,
        table_name_param,
        operazione_db, 
        record_id_db,
        dati_dopo_jsonb,
        username_param, # Passa lo username qui, se disponibile
        client_ip_address_param,
        session_id_param,
        datetime.now() # Passa esplicitamente il timestamp per coerenza, anche se ha un default
    )

    try:
        db_manager.execute_query(query, params)
        # Il commit per l'audit è una questione delicata.
        # Se l'operazione principale è fallita e ha fatto rollback, l'audit di quel fallimento
        # potrebbe necessitare di un commit separato o di essere scritto con una connessione diversa.
        # Se il db_manager è in AUTOCOMMIT, questo è già gestito.
        # Per ora, non gestiamo commit/rollback specifici per l'audit qui,
        # affidandoci alla gestione transazionale del chiamante o all'AUTOCOMMIT.
        logger.info(f"Audit registrato: AppUserID '{app_user_id_param}', Azione '{action}' (Op: '{operazione_db}'), Tabella '{table_name_param}'")
    except Exception as e_audit_final:
        # Se l'audit stesso fallisce, logga l'errore ma non far fallire l'operazione principale
        # che potrebbe aver già avuto successo.
        logger.error(f"FALLIMENTO SCRITTURA RECORD AUDIT: AppUserID '{app_user_id_param}', Azione '{action}'. Errore DB: {e_audit_final}", exc_info=True)