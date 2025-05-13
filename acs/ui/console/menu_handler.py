# ui/console/menu_handler.py
import logging
from datetime import date, datetime

# Importa i servizi necessari
from core.services import (
    utenti_service, anagrafiche_service, partite_service, 
    possessore_service, immobili_service, volture_service, 
    documenti_service, reporting_service
)
# Importa le utility della UI
from .ui_utils import (
    seleziona_da_lista, chiedi_conferma, input_valore, 
    formatta_data_utente, parse_data_utente, validatore_non_vuoto
)
from typing import List, Dict, Any, Optional, Callable # Aggiungiamo tutti quelli che potrebbero servire in questo modulo

logger = logging.getLogger("CatastoAppLogger.MenuHandler")

# Variabili globali per lo stato del login (saranno gestite da main_app.py e passate ai menu)
# NON definirle qui, ma aspettati che vengano passate come argomenti.
# logged_in_user_id: Optional[int] = None
# current_user_role_id: Optional[int] = None # Assumendo che role_id sia un int
# current_session_id: Optional[str] = None
# client_ip_address: Optional[str] = "127.0.0.1" # Esempio, da ottenere dinamicamente se possibile

# --- Funzioni Helper per i Menu (che interagiscono con i servizi) ---

def _get_user_input_for_audit(db_manager, user_id, session_id, client_ip):
    """Helper per non ripetere i parametri di audit nelle chiamate ai servizi."""
    return {
        "current_user_id": user_id,
        "session_id": session_id,
        "client_ip_address": client_ip
    }

def _handle_service_call(service_function, *args, success_message="Operazione completata con successo.", db_manager=None, audit_params=None, **kwargs):
    """
    Wrapper per chiamare funzioni di servizio, gestire eccezioni base e logging/audit.
    `audit_params` è il dizionario restituito da `_get_user_input_for_audit`.
    Le funzioni di servizio dovrebbero gestire il proprio logging/audit dettagliato e commit/rollback.
    Questo wrapper è per feedback all'utente e gestione errori generica.
    """
    try:
        # Passa db_manager e i parametri di audit se la funzione di servizio li accetta
        # (la maggior parte delle funzioni di servizio create li accetta come kwargs individuali)
        final_kwargs = kwargs.copy()
        if db_manager: final_kwargs['db_manager'] = db_manager # Alcuni servizi potrebbero non averlo se non interagiscono con DB
        if audit_params: final_kwargs.update(audit_params)
        
        # Le nostre funzioni di servizio sono state definite per prendere db_manager come primo argomento
        # e i parametri di audit come kwargs.
        # es: create_comune_service(db_manager, nome, codice_catastale, ..., current_user_id=..., ...)
        # Quindi, se db_manager è tra gli args, non c'è bisogno di passarlo di nuovo via kwargs.

        # Semplifichiamo: assumiamo che il primo arg sia db_manager, e gli altri siano i dati,
        # e audit_params siano passati come kwargs.
        
        # Le funzioni di servizio che abbiamo scritto accettano db_manager come primo argomento
        # e i parametri per audit come keyword arguments separati.
        # Quindi, la chiamata dovrebbe essere: service_function(db_manager, *args_specifici_servizio, **audit_params, **altri_kwargs)
        
        # Per come abbiamo definito i servizi, db_manager è il primo argomento.
        # Gli altri sono specifici. Audit params sono kwargs.
        
        # Assumendo che service_function prenda db_manager come primo argomento
        result = service_function(db_manager, *args, **audit_params if audit_params else {}, **kwargs)

        if result or result is None: # Molte funzioni CRUD ritornano ID, True, o None su fallimento non eccezionale
            print(success_message)
            if isinstance(result, (int, str)): # Se ritorna un ID
                 print(f"ID Entità creata/modificata: {result}")
            return result
        else: # Se la funzione di servizio ritorna False esplicitamente
            print("Operazione fallita (controllare i log per dettagli).")
            return None
            
    except ValueError as ve: # Errori di validazione o di business logic
        logger.warning(f"Errore di validazione/business: {ve}")
        print(f"ERRORE: {ve}")
        return None
    except Exception as e:
        logger.error(f"Errore imprevisto durante l'operazione: {e}", exc_info=True)
        print(f"ERRORE IMPREVISTO: {e}. Controllare i log.")
        return None

# --- Menu Gestione Utenti ---
def gestisci_utenti(db_manager, logged_in_user_id, current_user_role_id, current_session_id, client_ip_address):
    audit_info = _get_user_input_for_audit(db_manager, logged_in_user_id, current_session_id, client_ip_address)
    
    # Solo amministratori (es. role_id = 1) possono gestire utenti
    # Questa logica di autorizzazione dovrebbe essere più robusta, magari basata su permessi specifici.
    # Per ora, un semplice controllo sul role_id.
    # Assumiamo che il ruolo di amministratore abbia ID 1. Recuperalo dinamicamente se possibile.
    ADMIN_ROLE_ID = 1 # Dovrebbe essere caricato da config o DB

    if current_user_role_id != ADMIN_ROLE_ID:
        print("Accesso negato. Funzionalità riservata agli amministratori.")
        return

    while True:
        print("\n--- Gestione Utenti (Admin) ---")
        print("1. Visualizza lista utenti")
        print("2. Crea nuovo utente (da Admin)") # Diverso da registrazione self-service
        # print("3. Modifica utente (es. ruolo, stato attivo)") # TODO
        # print("4. Resetta password utente") # TODO
        print("0. Torna al menu principale")
        scelta = input("Scegli un'opzione: ")

        if scelta == '1':
            users = _handle_service_call(utenti_service.get_users_service,
                                         success_message="Lista utenti recuperata.",
                                         db_manager=db_manager, audit_params=audit_info)
            if users:
                print("\n--- Lista Utenti ---")
                for user in users:
                    print(f"ID: {user['id']}, Username: {user['username']}, Email: {user['email']}, Ruolo: {user['nome_ruolo']}, Attivo: {user['is_active']}, Creato: {formatta_data_utente(user['created_at']) if user.get('created_at') else 'N/A'}, Ultimo Login: {formatta_data_utente(user['last_login']) if user.get('last_login') else 'N/A'}")
            elif users == []:
                print("Nessun utente trovato.")

        elif scelta == '2':
            print("\n--- Creazione Nuovo Utente (Admin) ---")
            username = input_valore("Username:", obbligatorio=True)
            if not username: continue
            email = input_valore("Email:", obbligatorio=True) # Aggiungere validazione email
            if not email: continue
            plain_password = input_valore("Password temporanea:", tipo=str, obbligatorio=True) # Potrebbe essere generata
            if not plain_password: continue
            
            roles = utenti_service.get_user_roles_service(db_manager)
            if not roles: 
                print("Impossibile recuperare i ruoli. Creazione utente annullata.")
                continue
            selected_role = seleziona_da_lista(roles, titolo="Seleziona Ruolo Utente", desc_keys=['nome_ruolo'])
            if not selected_role: continue
            role_id_to_assign = selected_role['id']

            _handle_service_call(utenti_service.register_user_service,
                                 username, plain_password, email, role_id_to_assign,
                                 success_message=f"Utente {username} creato con successo.",
                                 db_manager=db_manager, 
                                 # Passa chi sta creando l'utente per l'audit
                                 audit_params={**audit_info, "created_by_user_id": logged_in_user_id})


        elif scelta == '0':
            break
        else:
            print("Scelta non valida.")

# --- Menu Anagrafiche Base ---
def gestisci_anagrafiche_base(db_manager, logged_in_user_id, current_session_id, client_ip_address):
    audit_info = _get_user_input_for_audit(db_manager, logged_in_user_id, current_session_id, client_ip_address)
    
    while True:
        print("\n--- Gestione Anagrafiche di Base ---")
        print("1. Gestisci Comuni")
        print("2. Gestisci Sezioni")
        print("3. Gestisci Qualifiche Possessore")
        print("4. Gestisci Titoli/Diritti")
        print("0. Torna al menu precedente")
        scelta_anag = input("Scegli un'opzione: ")

        if scelta_anag == '1':
            _menu_crud_generico(db_manager, "Comune", 
                                anagrafiche_service.get_comuni_service,
                                anagrafiche_service.get_comune_by_id_service,
                                anagrafiche_service.create_comune_service,
                                anagrafiche_service.update_comune_service,
                                anagrafiche_service.delete_comune_service,
                                ["nome", "codice_catastale", "provincia", "regione"], # Campi per create/update
                                {"nome": str, "codice_catastale": str, "provincia": str, "regione": str, "note": str}, # Tipi per input
                                desc_keys_lista=['nome', 'codice_catastale'], # Per visualizzazione lista
                                audit_info=audit_info)
        elif scelta_anag == '2':
             # Per le sezioni, la creazione/update richiede un comune_id
            _menu_crud_sezioni(db_manager, audit_info)
        elif scelta_anag == '3':
            _menu_crud_generico(db_manager, "Qualifica Possessore",
                                anagrafiche_service.get_qualifiche_service,
                                anagrafiche_service.get_qualifica_by_id_service,
                                anagrafiche_service.create_qualifica_service,
                                anagrafiche_service.update_qualifica_service,
                                anagrafiche_service.delete_qualifica_service,
                                ["nome_qualifica", "descrizione"],
                                {"nome_qualifica": str, "descrizione": str},
                                desc_keys_lista=['nome_qualifica'],
                                audit_info=audit_info)
        elif scelta_anag == '4':
            _menu_crud_generico(db_manager, "Titolo/Diritto",
                                anagrafiche_service.get_titoli_service,
                                anagrafiche_service.get_titolo_by_id_service,
                                anagrafiche_service.create_titolo_service,
                                anagrafiche_service.update_titolo_service,
                                anagrafiche_service.delete_titolo_service,
                                ["nome_titolo", "descrizione"],
                                {"nome_titolo": str, "descrizione": str},
                                desc_keys_lista=['nome_titolo'],
                                audit_info=audit_info)
        elif scelta_anag == '0':
            break
        else:
            print("Scelta non valida.")

# --- Helper per CRUD generico (usato da anagrafiche_base) ---
def _menu_crud_generico(db_manager, nome_entita, get_all_service, get_by_id_service, 
                        create_service, update_service, delete_service,
                        campi_input_create_update: List[str], # Nomi dei campi richiesti per create/update
                        tipi_input: Dict[str, type], # Dizionario nome_campo: tipo per input_valore
                        desc_keys_lista: List[str] = ['nome'], # Chiavi per descrivere l'elemento nella lista
                        audit_info: dict = None,
                        search_field_name: Optional[str] = None, # Nome del campo per la ricerca (es. 'nome_comune_search')
                        extra_create_params: Optional[dict] = None, # Parametri fissi aggiuntivi per create_service
                        extra_update_params: Optional[dict] = None  # Parametri fissi aggiuntivi per update_service
                        ):
    """Menu CRUD generico per anagrafiche semplici."""
    while True:
        print(f"\n--- Gestione {nome_entita} ---")
        print(f"1. Visualizza tutti i {nome_entita}")
        print(f"2. Aggiungi nuovo {nome_entita}")
        print(f"3. Modifica {nome_entita}")
        print(f"4. Cancella {nome_entita}")
        print("0. Torna indietro")
        scelta = input("Scegli un'opzione: ")

        if scelta == '1':
            search_term = None
            if search_field_name:
                search_term = input_valore(f"Cerca per {search_field_name} (lascia vuoto per tutti):", obbligatorio=False)

            if search_field_name and search_term:
                # Assumiamo che il servizio accetti un kwarg con il nome del search_field_name
                elementi, _ = _handle_service_call(get_all_service, **{search_field_name: search_term},
                                                 success_message=f"Lista {nome_entita} recuperata.",
                                                 db_manager=db_manager, audit_params=audit_info) \
                                                 if search_field_name else (None, 0) # Fallback se non corretto
                if not search_field_name: # Chiamata senza filtro se il servizio non accetta kwargs così
                     elementi, _ = _handle_service_call(get_all_service,
                                                 success_message=f"Lista {nome_entita} recuperata.",
                                                 db_manager=db_manager, audit_params=audit_info) \
                                                 if hasattr(get_all_service, "__call__") else (None, 0)

            else: # Nessun termine di ricerca o campo di ricerca non definito
                # Alcuni servizi (es. get_comuni) accettano il termine come primo argomento opzionale
                # Altri (es. get_qualifiche) no. Dobbiamo gestire questa differenza.
                # Per ora, se search_field_name non c'è, chiamiamo senza argomenti di ricerca.
                if get_all_service == anagrafiche_service.get_comuni_service: # Caso speciale per comuni
                     elementi = _handle_service_call(get_all_service, search_term, # search_term può essere None
                                                 success_message=f"Lista {nome_entita} recuperata.",
                                                 db_manager=db_manager, audit_params=audit_info)
                else: # Per altri servizi che non hanno ricerca diretta nel get_all
                     elementi = _handle_service_call(get_all_service,
                                                 success_message=f"Lista {nome_entita} recuperata.",
                                                 db_manager=db_manager, audit_params=audit_info)


            if elementi:
                for idx, el in enumerate(elementi):
                    desc_parts = [str(el.get(k, 'N/D')) for k in desc_keys_lista]
                    print(f"{idx+1}. ID: {el.get('id', 'N/D')} - {' / '.join(desc_parts)}")
            elif elementi == []:
                print(f"Nessun {nome_entita} trovato.")
        
        elif scelta == '2': # Aggiungi
            print(f"\n--- Aggiungi Nuovo {nome_entita} ---")
            dati_nuovo = {}
            for campo in campi_input_create_update:
                is_obbligatorio = True # Per semplicità, rendi tutti obbligatori, o aggiungi logica
                tipo_campo = tipi_input.get(campo, str)
                valore = input_valore(f"{campo.replace('_', ' ').capitalize()}:", tipo=tipo_campo, obbligatorio=is_obbligatorio)
                if valore is None and is_obbligatorio: # L'utente ha annullato
                    print("Creazione annullata.")
                    dati_nuovo = None; break
                dati_nuovo[campo] = valore
            
            if dati_nuovo:
                if extra_create_params: dati_nuovo.update(extra_create_params)
                _handle_service_call(create_service, 
                                     **dati_nuovo, # Passa i dati come keyword arguments
                                     success_message=f"{nome_entita} creato con successo.",
                                     db_manager=db_manager, audit_params=audit_info)

        elif scelta == '3': # Modifica
            print(f"\n--- Modifica {nome_entita} ---")
            lista_completa = get_all_service(db_manager) # Ricarica lista per selezione
            if not lista_completa : print(f"Nessun {nome_entita} da modificare."); continue
            # Se lista_completa è una tupla (dati, conteggio), prendi solo i dati
            if isinstance(lista_completa, tuple) and len(lista_completa) == 2: lista_completa = lista_completa[0]


            elemento_sel = seleziona_da_lista(lista_completa, titolo=f"Seleziona {nome_entita} da modificare", desc_keys=desc_keys_lista)
            if not elemento_sel: continue
            id_elemento = elemento_sel['id']
            
            # Recupera i dettagli completi dell'elemento per pre-compilare i campi
            dettagli_elemento = get_by_id_service(db_manager, id_elemento)
            if not dettagli_elemento: print(f"{nome_entita} con ID {id_elemento} non trovato."); continue

            print(f"Modifica in corso per {nome_entita} ID: {id_elemento}. Lasciare vuoto per non modificare (se non obbligatorio).")
            dati_modificati = {}
            for campo in campi_input_create_update:
                tipo_campo = tipi_input.get(campo, str)
                default_val = dettagli_elemento.get(campo)
                # Converte date in stringhe per default se necessario per input_valore
                if isinstance(default_val, date): default_val = formatta_data_utente(default_val)

                is_obbligatorio_update = False # In update, i campi potrebbero non essere tutti obbligatori da reinserire
                
                prompt_mod = f"{campo.replace('_', ' ').capitalize()} (attuale: {default_val if default_val is not None else 'N/D'}):"
                valore = input_valore(prompt_mod, tipo=tipo_campo, obbligatorio=is_obbligatorio_update, default=default_val if not is_obbligatorio_update else None)
                
                if valore is None and not is_obbligatorio_update and default_val is not None:
                     dati_modificati[campo] = dettagli_elemento.get(campo) # Mantieni il vecchio valore se lasciato vuoto e c'era un default
                elif valore is not None:
                     dati_modificati[campo] = valore
                else: # Se il campo era None e viene lasciato vuoto (e non è obbligatorio), rimane None
                     dati_modificati[campo] = dettagli_elemento.get(campo) # o None direttamente

            if dati_modificati:
                if extra_update_params: dati_modificati.update(extra_update_params)
                # L'update service di solito prende id_elemento come primo argomento, poi i dati
                _handle_service_call(update_service, 
                                     id_elemento, 
                                     **dati_modificati, # Passa i dati come keyword arguments
                                     success_message=f"{nome_entita} ID {id_elemento} aggiornato con successo.",
                                     db_manager=db_manager, audit_params=audit_info)

        elif scelta == '4': # Cancella
            print(f"\n--- Cancella {nome_entita} ---")
            lista_completa = get_all_service(db_manager)
            if not lista_completa : print(f"Nessun {nome_entita} da cancellare."); continue
            if isinstance(lista_completa, tuple) and len(lista_completa) == 2: lista_completa = lista_completa[0]

            elemento_sel = seleziona_da_lista(lista_completa, titolo=f"Seleziona {nome_entita} da cancellare", desc_keys=desc_keys_lista)
            if not elemento_sel: continue
            id_elemento = elemento_sel['id']

            desc_parts = [str(elemento_sel.get(k, 'N/D')) for k in desc_keys_lista]
            if chiedi_conferma(f"Sei sicuro di voler cancellare {nome_entita} ID {id_elemento} ({' / '.join(desc_parts)})?"):
                _handle_service_call(delete_service, 
                                     id_elemento,
                                     success_message=f"{nome_entita} ID {id_elemento} cancellato con successo.",
                                     db_manager=db_manager, audit_params=audit_info)
        elif scelta == '0':
            break
        else:
            print("Scelta non valida.")


def _menu_crud_sezioni(db_manager, audit_info: dict):
    """Menu CRUD specifico per le Sezioni, che richiedono la selezione di un Comune."""
    nome_entita = "Sezione"
    get_all_service_sez = anagrafiche_service.get_sezioni_service
    get_by_id_service_sez = anagrafiche_service.get_sezione_by_id_service
    create_service_sez = anagrafiche_service.create_sezione_service
    update_service_sez = anagrafiche_service.update_sezione_service
    delete_service_sez = anagrafiche_service.delete_sezione_service
    
    campi_input = ["nome_sezione", "codice_sezione", "note"]
    tipi_input_sez = {"nome_sezione": str, "codice_sezione": str, "note": str}
    desc_keys_lista_sez = ['nome_sezione', 'codice_sezione', 'nome_comune']


    while True:
        print(f"\n--- Gestione {nome_entita} ---")
        print(f"1. Visualizza tutte le {nome_entita} (opz. per comune)")
        print(f"2. Aggiungi nuova {nome_entita}")
        print(f"3. Modifica {nome_entita}")
        print(f"4. Cancella {nome_entita}")
        print("0. Torna indietro")
        scelta = input("Scegli un'opzione: ")

        if scelta == '1':
            print("\nVuoi filtrare le sezioni per comune?")
            comuni = anagrafiche_service.get_comuni_service(db_manager)
            if not comuni: print("Nessun comune trovato per filtrare."); continue
            
            comune_selezionato = seleziona_da_lista(comuni, titolo="Seleziona Comune per filtrare (0 per tutte)", desc_keys=['nome'])
            comune_id_filtro = comune_selezionato['id'] if comune_selezionato else None
            
            elementi = _handle_service_call(get_all_service_sez, comune_id=comune_id_filtro,
                                             success_message="Lista Sezioni recuperata.",
                                             db_manager=db_manager, audit_params=audit_info)
            if elementi:
                for idx, el in enumerate(elementi):
                    desc_parts = [str(el.get(k, 'N/D')) for k in desc_keys_lista_sez]
                    print(f"{idx+1}. ID: {el.get('id', 'N/D')} - {' / '.join(desc_parts)}")
            elif elementi == []:
                print("Nessuna sezione trovata.")

        elif scelta == '2': # Aggiungi Sezione
            print(f"\n--- Aggiungi Nuova {nome_entita} ---")
            comuni = anagrafiche_service.get_comuni_service(db_manager)
            if not comuni: print("Nessun comune disponibile per associare la sezione."); continue
            comune_sel = seleziona_da_lista(comuni, titolo="Seleziona Comune di appartenenza", desc_keys=['nome'])
            if not comune_sel: continue
            comune_id_scelto = comune_sel['id']

            dati_nuovo = {"comune_id": comune_id_scelto}
            for campo in campi_input:
                val = input_valore(f"{campo.replace('_',' ').capitalize()}:", tipo=tipi_input_sez.get(campo,str), obbligatorio=(campo=="nome_sezione"))
                if val is None and campo=="nome_sezione": dati_nuovo=None; break
                dati_nuovo[campo] = val
            
            if dati_nuovo:
                _handle_service_call(create_service_sez, **dati_nuovo, 
                                     success_message=f"{nome_entita} creata.", 
                                     db_manager=db_manager, audit_params=audit_info)
        
        elif scelta == '3': # Modifica Sezione
            print(f"\n--- Modifica {nome_entita} ---")
            # Per modificare una sezione, è meglio visualizzarle tutte o per comune
            tutte_le_sezioni = get_all_service_sez(db_manager) # Ottiene tutte per la selezione
            if not tutte_le_sezioni: print(f"Nessuna {nome_entita} da modificare."); continue

            sezione_sel = seleziona_da_lista(tutte_le_sezioni, titolo=f"Seleziona {nome_entita} da modificare", desc_keys=desc_keys_lista_sez)
            if not sezione_sel: continue
            id_sezione = sezione_sel['id']
            
            dettagli_sezione = get_by_id_service_sez(db_manager, id_sezione)
            if not dettagli_sezione: print(f"{nome_entita} con ID {id_sezione} non trovata."); continue

            print(f"Modifica in corso per {nome_entita} ID: {id_sezione} '{dettagli_sezione.get('nome_sezione')}'.")
            
            # Selezione nuovo comune (opzionale, o mantieni il corrente)
            comuni = anagrafiche_service.get_comuni_service(db_manager)
            print(f"Comune attuale: {dettagli_sezione.get('nome_comune')} (ID: {dettagli_sezione.get('comune_id')})")
            if chiedi_conferma("Vuoi cambiare il comune di appartenenza?", default_yes=False):
                comune_cambiato_sel = seleziona_da_lista(comuni, titolo="Seleziona Nuovo Comune", desc_keys=['nome'])
                comune_id_nuovo = comune_cambiato_sel['id'] if comune_cambiato_sel else dettagli_sezione.get('comune_id')
            else:
                comune_id_nuovo = dettagli_sezione.get('comune_id')

            dati_mod = {"comune_id": comune_id_nuovo}
            for campo in campi_input:
                val = input_valore(f"{campo.replace('_',' ').capitalize()} (attuale: {dettagli_sezione.get(campo, 'N/D')}):", 
                                   tipo=tipi_input_sez.get(campo,str), 
                                   obbligatorio=False, default=dettagli_sezione.get(campo))
                dati_mod[campo] = val if val is not None else dettagli_sezione.get(campo) # Mantiene vecchio se lasciato vuoto

            if dati_mod:
                _handle_service_call(update_service_sez, id_sezione, **dati_mod,
                                     success_message=f"{nome_entita} ID {id_sezione} aggiornata.",
                                     db_manager=db_manager, audit_params=audit_info)

        elif scelta == '4': # Cancella Sezione
            _menu_crud_generico(db_manager, nome_entita, get_all_service_sez, get_by_id_service_sez,
                                None, None, delete_service_sez, # Non usiamo create/update qui
                                [], {}, desc_keys_lista_sez, audit_info) # Solo per la parte di selezione e delete

        elif scelta == '0': break
        else: print("Scelta non valida.")


# --- Menu Gestione Partite ---
def gestisci_partite_menu(db_manager, logged_in_user_id, current_session_id, client_ip_address):
    audit_info = _get_user_input_for_audit(db_manager, logged_in_user_id, current_session_id, client_ip_address)
    # ... (Implementare il menu per Partite, simile a python_example.py, usando i servizi di partite_service)
    # Questo menu sarà complesso a causa delle relazioni (intestazioni, immobili, etc.)
    # Ecco uno scheletro di base:
    while True:
        print("\n--- Gestione Partite ---")
        print("1. Visualizza/Cerca Partite")
        print("2. Inserisci Nuova Partita")
        print("3. Modifica Partita Esistente")
        print("4. Cancella Partita") # Con molta cautela!
        print("5. Gestisci Intestazioni Partita (collega/scollega possessori)")
        # print("6. Gestisci Immobili della Partita") (potrebbe essere un sottomenu di visualizza/modifica partita)
        print("0. Torna al menu principale")
        scelta = input("Scegli un'opzione: ")

        if scelta == '1':
            _visualizza_cerca_partite_menu(db_manager, audit_info)
        elif scelta == '2':
            _inserisci_nuova_partita_menu(db_manager, audit_info)
        # ... altri casi ...
        elif scelta == '0': break
        else: print("Scelta non valida.")

def _visualizza_cerca_partite_menu(db_manager, audit_info):
    print("\n--- Visualizza/Cerca Partite ---")
    # Implementa logica di ricerca usando partite_service.search_partite_service
    # e visualizza i risultati. Permetti di selezionare una partita per vedere i dettagli.
    comune_id = None; sezione_id = None; numero_partita = None; cognome_possessore = None; # ... e altri campi di search_partite_service
    
    print("Lasciare vuoto per non filtrare per quel criterio.")
    
    # Richiedi input per i criteri di ricerca
    comuni = anagrafiche_service.get_comuni_service(db_manager)
    if comuni:
        comune_sel = seleziona_da_lista(comuni, titolo="Filtra per Comune (opzionale)", desc_keys=['nome'])
        if comune_sel: 
            comune_id = comune_sel['id']
            sezioni = anagrafiche_service.get_sezioni_service(db_manager, comune_id=comune_id)
            if sezioni:
                sezione_sel = seleziona_da_lista(sezioni, titolo="Filtra per Sezione (opzionale)", desc_keys=['nome_sezione'])
                if sezione_sel: sezione_id = sezione_sel['id']

    numero_partita = input_valore("Numero Partita (opzionale):", obbligatorio=False)
    # ... altri input per la ricerca (possessore, immobile) ...
    cognome_possessore = input_valore("Cognome/Denom. Possessore (opzionale):", obbligatorio=False)
    # cf_possessore = input_valore("CF/P.IVA Possessore (opzionale):", obbligatorio=False)
    # foglio_imm = input_valore("Foglio Immobile (opzionale):", obbligatorio=False)
    # particella_imm = input_valore("Particella Immobile (opzionale):", obbligatorio=False)


    partite_trovate = _handle_service_call(
        partite_service.search_partite_service,
        comune_id=comune_id, sezione_id=sezione_id, numero_partita=numero_partita,
        cognome_possessore=cognome_possessore, # cf_possessore=cf_possessore,
        # fg=foglio_imm, particella=particella_imm,
        success_message="Ricerca partite completata.",
        db_manager=db_manager, audit_params=audit_info
    )

    if partite_trovate:
        print("\n--- Risultati Ricerca Partite ---")
        # Visualizza e permetti selezione per dettagli, simile a _menu_crud_generico
        partita_selezionata = seleziona_da_lista(partite_trovate, 
                                                titolo="Seleziona Partita per dettagli",
                                                desc_keys=['numero_partita', 'nome_comune', 'nome_sezione'])
        if partita_selezionata:
            _visualizza_dettaglio_partita(db_manager, partita_selezionata['id'], audit_info)
            
    elif partite_trovate == []:
        print("Nessuna partita trovata con i criteri specificati.")


def _visualizza_dettaglio_partita(db_manager, partita_id, audit_info):
    print(f"\n--- Dettaglio Partita ID: {partita_id} ---")
    partita = _handle_service_call(partite_service.get_partita_by_id_service, partita_id, db_manager=db_manager, audit_params=audit_info)
    if not partita: return

    print(f"Numero Partita: {partita['numero_partita']}")
    print(f"Comune: {partita['nome_comune']} (ID: {partita['comune_id']})")
    print(f"Sezione: {partita['nome_sezione']} (ID: {partita['sezione_id']})")
    print(f"Data Creazione: {formatta_data_utente(partita['data_creazione'])}")
    if partita.get('data_soppressione'): print(f"Data Soppressione: {formatta_data_utente(partita['data_soppressione'])}")
    print(f"Tipo Partita: {partita.get('tipo_partita', 'N/D')}")
    print(f"Note Partita: {partita.get('note_partita', 'N/D')}")
    
    # Visualizza Intestazioni
    print("\n--- Intestatari ---")
    intestazioni = partite_service.get_intestazioni_partita_service(db_manager, partita_id)
    if intestazioni:
        for i in intestazioni:
            print(f"- {i['cognome_denominazione']} {i.get('nome','')} (CF: {i.get('codice_fiscale_partita_iva','N/D')})")
            print(f"  Qualifica: {i['nome_qualifica']}, Titolo: {i['nome_titolo']}, Quota: {i.get('quota_diritto','N/D')}")
            print(f"  Validità: da {formatta_data_utente(i['data_inizio_validita'])} a {formatta_data_utente(i.get('data_fine_validita')) if i.get('data_fine_validita') else 'Attuale'}")
            if i.get('note_intestazione'): print(f"  Note Intestazione: {i['note_intestazione']}")
    else:
        print("Nessun intestatario trovato per questa partita.")

    # Visualizza Immobili
    print("\n--- Immobili ---")
    immobili = immobili_service.get_immobili_by_partita_service(db_manager, partita_id)
    if immobili:
        for imm in immobili:
            print(f"- Fg.{imm['foglio']}/Part.{imm['numero_particella']}/Sub.{imm.get('subalterno','')} (ID: {imm['id']})")
            print(f"  Cat: {imm.get('categoria_catastale','')}, Cl: {imm.get('classe','')}, Cons: {imm.get('consistenza','')}, Rendita: {imm.get('rendita','')}")
            print(f"  Validità: da {formatta_data_utente(imm['data_inizio_validita'])} a {formatta_data_utente(imm.get('data_fine_validita')) if imm.get('data_fine_validita') else 'Attuale'}")
            # Visualizza indirizzi per questo immobile
            indirizzi_imm = immobili_service.get_indirizzi_by_immobile_service(db_manager, imm['id'])
            if indirizzi_imm:
                for ind in indirizzi_imm:
                    print(f"    Indirizzo: {ind['via']} {ind['numero_civico']} (Comune: {ind.get('nome_comune_indirizzo', 'N/D')})")
            elif imm.get('indirizzo_manuale'):
                 print(f"    Indirizzo (manuale): {imm['indirizzo_manuale']}")


    else:
        print("Nessun immobile trovato per questa partita.")
    
    # Altre sezioni (Volture, Documenti collegati) possono essere aggiunte qui
    input("\nPremi Invio per continuare...")


def _inserisci_nuova_partita_menu(db_manager, audit_info):
    print("\n--- Inserisci Nuova Partita ---")
    # Raccogli dati per la nuova partita
    comuni = anagrafiche_service.get_comuni_service(db_manager)
    if not comuni: print("Nessun comune definito. Impossibile creare partita."); return
    comune_sel = seleziona_da_lista(comuni, "Seleziona Comune", desc_keys=['nome'])
    if not comune_sel: return
    comune_id = comune_sel['id']

    sezioni = anagrafiche_service.get_sezioni_service(db_manager, comune_id=comune_id)
    if not sezioni: print(f"Nessuna sezione definita per il comune '{comune_sel['nome']}'. Impossibile creare partita."); return
    sezione_sel = seleziona_da_lista(sezioni, f"Seleziona Sezione per {comune_sel['nome']}", desc_keys=['nome_sezione'])
    if not sezione_sel: return
    sezione_id = sezione_sel['id']

    numero_partita = input_valore("Numero Partita:", obbligatorio=True)
    if not numero_partita: return
    
    data_creazione_str = input_valore("Data Creazione Partita (GG/MM/AAAA, lascia vuoto per oggi):", tipo=str, obbligatorio=False)
    data_creazione = parse_data_utente(data_creazione_str) or datetime.now().date()

    tipo_partita = input_valore("Tipo Partita (es. Terreni, Fabbricati, Ente Urbano):", obbligatorio=False)
    note_partita = input_valore("Note Partita:", obbligatorio=False)

    # Chiamata al servizio
    partita_id_creata = _handle_service_call(
        partite_service.create_partita_service,
        comune_id=comune_id, 
        numero_partita=numero_partita, 
        sezione_id=sezione_id,
        data_creazione=data_creazione,
        tipo_partita=tipo_partita,
        note=note_partita,
        success_message=f"Partita N.{numero_partita} creata.",
        db_manager=db_manager, audit_params=audit_info
    )
    if partita_id_creata:
        if chiedi_conferma("Vuoi aggiungere intestatari a questa nuova partita ora?"):
            _gestisci_intestazioni_partita(db_manager, partita_id_creata, audit_info)
        if chiedi_conferma("Vuoi aggiungere immobili a questa nuova partita ora?"):
            _gestisci_immobili_partita(db_manager, partita_id_creata, audit_info)


def _gestisci_intestazioni_partita(db_manager, partita_id, audit_info):
    # Permetti di aggiungere/rimuovere/modificare intestatari per la partita_id
    partita_info = partite_service.get_partita_by_id_service(db_manager, partita_id)
    if not partita_info: print(f"Partita ID {partita_id} non trovata."); return

    while True:
        print(f"\n--- Gestione Intestatari per Partita N.{partita_info['numero_partita']} ({partita_info['nome_comune']}) ---")
        intestazioni = partite_service.get_intestazioni_partita_service(db_manager, partita_id)
        if intestazioni:
            print("Intestatari attuali:")
            for idx, i in enumerate(intestazioni):
                 print(f"{idx+1}. {i['cognome_denominazione']} {i.get('nome','')} (ID Intestazione: {i['intestazione_id']}) - {i['nome_qualifica']} di {i['nome_titolo']} per {i.get('quota_diritto','N/D')}")
                 print(f"   Valida da: {formatta_data_utente(i['data_inizio_validita'])} a: {formatta_data_utente(i.get('data_fine_validita')) if i.get('data_fine_validita') else 'Attuale'}")
        else:
            print("Nessun intestatario attualmente associato.")

        print("\nOpzioni Intestazioni:")
        print("1. Aggiungi nuovo intestatario")
        print("2. Modifica intestazione esistente")
        print("3. Chiudi (termina validità) intestazione esistente")
        print("4. Rimuovi fisicamente intestazione esistente (sconsigliato per storico)")
        print("0. Torna al menu partita")
        scelta_int = input("Scegli: ")

        if scelta_int == '1': # Aggiungi
            _aggiungi_intestatario_a_partita(db_manager, partita_id, audit_info)
        elif scelta_int == '2': # Modifica
            if not intestazioni: print("Nessuna intestazione da modificare."); continue
            sel = seleziona_da_lista(intestazioni, "Seleziona intestazione da MODIFICARE", 
                                     desc_keys=['cognome_denominazione', 'nome_qualifica', 'nome_titolo'], id_key='intestazione_id')
            if sel: _modifica_intestazione_esistente(db_manager, sel['intestazione_id'], audit_info)
        elif scelta_int == '3': # Chiudi
            if not intestazioni: print("Nessuna intestazione da chiudere."); continue
            attive = [i for i in intestazioni if not i.get('data_fine_validita')]
            if not attive: print("Nessuna intestazione attualmente attiva da chiudere."); continue
            sel = seleziona_da_lista(attive, "Seleziona intestazione ATTIVA da CHIUDERE", 
                                     desc_keys=['cognome_denominazione', 'nome_qualifica', 'nome_titolo'], id_key='intestazione_id')
            if sel:
                data_fine_str = input_valore("Data fine validità (GG/MM/AAAA, oggi se vuoto):", tipo=str, obbligatorio=False)
                data_fine = parse_data_utente(data_fine_str) or datetime.now().date()
                if chiedi_conferma(f"Chiudere intestazione ID {sel['intestazione_id']} al {formatta_data_utente(data_fine)}?"):
                    _handle_service_call(partite_service.close_intestazione_service,
                                         sel['intestazione_id'], data_fine=data_fine,
                                         success_message="Intestazione chiusa con successo.",
                                         db_manager=db_manager, audit_params=audit_info)
        elif scelta_int == '4': # Rimuovi
            if not intestazioni: print("Nessuna intestazione da rimuovere."); continue
            sel = seleziona_da_lista(intestazioni, "Seleziona intestazione da RIMUOVERE FISICAMENTE", 
                                     desc_keys=['cognome_denominazione', 'nome_qualifica', 'nome_titolo'], id_key='intestazione_id')
            if sel:
                if chiedi_conferma(f"ATTENZIONE: Rimuovere FISICAMENTE l'intestazione ID {sel['intestazione_id']}? Questa operazione non è reversibile e può compromettere lo storico.", default_yes=False):
                    _handle_service_call(partite_service.unlink_possessore_da_partita_service,
                                         sel['intestazione_id'],
                                         success_message="Intestazione rimossa fisicamente.",
                                         db_manager=db_manager, audit_params=audit_info)

        elif scelta_int == '0': break
        else: print("Scelta non valida.")


def _aggiungi_intestatario_a_partita(db_manager, partita_id, audit_info):
    print("\n--- Aggiungi Intestatario ---")
    # 1. Seleziona o crea possessore
    possessore_id = None
    if chiedi_conferma("Il possessore esiste già anagrafato?", default_yes=True):
        cognome_cerca = input_valore("Cognome/Denominazione da cercare:", obbligatorio=False)
        cf_cerca = input_valore("CF/P.IVA da cercare (opzionale):", obbligatorio=False)
        poss_trovati, _ = possessori_service.get_possessori_service(db_manager, cognome_search=cognome_cerca, cf_search=cf_cerca, limit=20)
        if poss_trovati:
            poss_sel = seleziona_da_lista(poss_trovati, "Seleziona Possessore esistente", desc_keys=['cognome_denominazione', 'nome', 'codice_fiscale_partita_iva'])
            if poss_sel: possessore_id = poss_sel['id']
        else:
            print("Nessun possessore trovato con i criteri. Procedi con la creazione.")
    
    if not possessore_id: # Crea nuovo possessore
        # Raccogli dati per nuovo possessore (menu semplificato qui)
        print("Creazione nuovo possessore:")
        dati_poss = {}
        dati_poss['cognome_denominazione'] = input_valore("Cognome/Denominazione:", obbligatorio=True)
        if not dati_poss['cognome_denominazione']: return
        dati_poss['nome'] = input_valore("Nome (se persona fisica):", obbligatorio=False)
        dati_poss['codice_fiscale_partita_iva'] = input_valore("CF/P.IVA:", obbligatorio=False)
        # ... altri campi per possessore ...
        possessore_id = _handle_service_call(possessori_service.create_possessore_service, 
                                           **dati_poss,
                                           success_message="Possessore creato.",
                                           db_manager=db_manager, audit_params=audit_info)
        if not possessore_id: print("Creazione possessore fallita."); return

    # 2. Seleziona Qualifica
    qualifiche = anagrafiche_service.get_qualifiche_service(db_manager)
    if not qualifiche: print("Nessuna qualifica definita."); return
    qual_sel = seleziona_da_lista(qualifiche, "Seleziona Qualifica", desc_keys=['nome_qualifica'])
    if not qual_sel: return
    qualifica_id = qual_sel['id']

    # 3. Seleziona Titolo/Diritto
    titoli = anagrafiche_service.get_titoli_service(db_manager)
    if not titoli: print("Nessun titolo/diritto definito."); return
    tit_sel = seleziona_da_lista(titoli, "Seleziona Titolo/Diritto", desc_keys=['nome_titolo'])
    if not tit_sel: return
    titolo_id = tit_sel['id']

    # 4. Altri dati intestazione
    quota = input_valore("Quota Diritto (es. 1/1, 1000/1000, usufrutto):", obbligatorio=False)
    data_inizio_str = input_valore("Data Inizio Validità (GG/MM/AAAA, oggi se vuoto):", tipo=str, obbligatorio=False)
    data_inizio = parse_data_utente(data_inizio_str) or datetime.now().date()
    note_int = input_valore("Note Intestazione:", obbligatorio=False)

    _handle_service_call(partite_service.link_possessore_a_partita_service,
                         partita_id, possessore_id, qualifica_id, titolo_id,
                         quota_diritto=quota, data_inizio_validita=data_inizio, note=note_int,
                         success_message="Intestatario aggiunto/collegato alla partita.",
                         db_manager=db_manager, audit_params=audit_info)

# ... (Implementare _modifica_intestazione_esistente e _gestisci_immobili_partita) ...
# ... (Implementare gli altri menu: possessori, immobili, volture, documenti, report) ...

# --- Menu Principale ---
def menu_principale(db_manager, logged_in_user_id, current_user_role_id, current_session_id, client_ip_address):
    """Menu principale dell'applicazione."""
    logger.info(f"Utente ID {logged_in_user_id} (Ruolo ID: {current_user_role_id}, Sessione: {current_session_id}) ha effettuato l'accesso al menu principale.")
    
    while True:
        print("\n--- Menu Principale ---")
        print("1. Gestione Partite")
        print("2. Gestione Possessori")
        print("3. Gestione Immobili")
        print("4. Gestione Volture")
        print("5. Gestione Documenti")
        print("6. Gestione Anagrafiche di Base (Comuni, Sezioni, etc.)")
        print("7. Genera Report")
        if current_user_role_id == 1: # Assumendo 1 sia Admin Role ID
            print("8. Gestione Utenti (Admin)")
        print("0. Logout e Esci")
        
        scelta = input("Scegli un'opzione: ")

        if scelta == '1':
            gestisci_partite_menu(db_manager, logged_in_user_id, current_session_id, client_ip_address)
        elif scelta == '2':
            # gestisci_possessori_menu(db_manager, logged_in_user_id, current_session_id, client_ip_address) # Da implementare
            print("Menu Gestione Possessori - Da implementare")
        elif scelta == '3':
            # gestisci_immobili_menu(db_manager, logged_in_user_id, current_session_id, client_ip_address) # Da implementare
            print("Menu Gestione Immobili - Da implementare")
        elif scelta == '4':
            # gestisci_volture_menu(db_manager, logged_in_user_id, current_session_id, client_ip_address) # Da implementare
            print("Menu Gestione Volture - Da implementare")
        elif scelta == '5':
            # gestisci_documenti_menu(db_manager, logged_in_user_id, current_session_id, client_ip_address) # Da implementare
            print("Menu Gestione Documenti - Da implementare")
        elif scelta == '6':
            gestisci_anagrafiche_base(db_manager, logged_in_user_id, current_session_id, client_ip_address)
        elif scelta == '7':
            # menu_genera_report(db_manager, logged_in_user_id, current_session_id, client_ip_address) # Da implementare
            print("Menu Genera Report - Da implementare")
        elif scelta == '8' and current_user_role_id == 1:
            gestisci_utenti(db_manager, logged_in_user_id, current_user_role_id, current_session_id, client_ip_address)
        elif scelta == '0':
            print("Logout in corso...")
            break # Esce dal loop del menu principale, il logout effettivo sarà in main_app.py
        else:
            print("Scelta non valida. Riprova.")