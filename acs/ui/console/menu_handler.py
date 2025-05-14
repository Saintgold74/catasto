# ui/console/menu_handler.py
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Callable

# Importa i servizi necessari
from core.services import (
    utenti_service,
    anagrafiche_service, # Il nostro servizio modificato
    partite_service,
    possessore_service,
    immobili_service,
    volture_service,
    documenti_service,
    reporting_service
)
# Importa le utility della UI
from .ui_utils import (
    seleziona_da_lista, chiedi_conferma, input_valore,
    formatta_data_utente, parse_data_utente, validatore_non_vuoto,
    input_sicuro_password
)

# Importa per la sessione SQLAlchemy
from sqlalchemy.orm import Session
from core.db_manager import get_db # Assumendo che get_db sia definito in db_manager.py

logger = logging.getLogger("CatastoAppLogger.MenuHandler")

ADMIN_ROLE_ID = 1 # Da caricare da config o DB idealmente

# --- Menu Gestione Utenti (Lasciato per ora con il vecchio stile db_manager passato, da adattare quando utenti_service sarà convertito) ---
# Nota: Se utenti_service viene convertito a SQLAlchemy, anche questo menu dovrà usare db: Session
def gestisci_utenti(
    db_manager_old, # Temporaneamente mantenuto se utenti_service non è convertito
    logged_in_user_id: Optional[int], 
    current_user_role_id: Optional[int], 
    current_session_id: Optional[str], 
    client_ip_address: Optional[str]
):
    audit_info_dict = {
        "current_user_id": logged_in_user_id,
        "client_ip_address": client_ip_address,
        "session_id": current_session_id
    }

    if current_user_role_id != ADMIN_ROLE_ID:
        print("Accesso negato. Funzionalità riservata agli amministratori.")
        return

    # Questa è una semplificazione. Idealmente, se utenti_service usa SQLAlchemy,
    # questa funzione dovrebbe ricevere db: Session come gli altri menu.
    # Per ora, presumo che utenti_service usi ancora il vecchio db_manager.
    db_session_for_utenti: Optional[Session] = None
    if not db_manager_old: # Se non viene passato il vecchio db_manager, proviamo ad usare SQLAlchemy
        db_session_for_utenti = next(get_db())
    
    # db_context sarà la sessione SQLAlchemy o il vecchio db_manager
    db_context = db_session_for_utenti if db_session_for_utenti else db_manager_old

    try:
        while True:
            print("\n--- Gestione Utenti (Admin) ---")
            print("1. Visualizza lista utenti")
            print("2. Crea nuovo utente (da Admin)")
            print("3. Modifica dati utente")
            print("4. Disattiva (soft delete) utente")
            print("5. Resetta password utente")
            print("0. Torna al menu principale")
            scelta = input("Scegli un'opzione: ")

            if scelta == '1':
                # Assumendo che get_users_service sia ancora basato su db_manager_old
                users = utenti_service.get_users_service(db_context)
                if users:
                    print("\n--- Lista Utenti ---")
                    for user in users:
                        print(f"ID: {user['id']}, Username: {user['username']}, Email: {user['email']}, "
                              f"Nome: {user.get('nome_completo', 'N/D')}, Ruolo: {user.get('nome_ruolo', 'N/A')}, "
                              f"Attivo: {user['is_active']}, Ultimo Login: {formatta_data_utente(user.get('last_login')) if user.get('last_login') else 'N/A'}")
                elif users == []:
                    print("Nessun utente trovato.")

            elif scelta == '2': # Crea utente
                print("\n--- Creazione Nuovo Utente (Admin) ---")
                username = input_valore("Username:", validatore=validatore_non_vuoto)
                if not username: continue
                email = input_valore("Email:", validatore=validatore_non_vuoto) # Aggiungi validatore email se lo hai
                if not email: continue
                nome_completo = input_valore("Nome Completo:", validatore=validatore_non_vuoto)
                if not nome_completo: continue
                plain_password = input_sicuro_password("Password temporanea:", min_length=1) # ui_utils non ha min_length, ma input_valore sì
                if not plain_password: continue
                
                roles = utenti_service.get_user_roles_service(db_context)
                if not roles: print("Impossibile recuperare i ruoli."); continue
                selected_role = seleziona_da_lista(roles, "Seleziona Ruolo Utente", desc_keys=['nome_ruolo'])
                if not selected_role: continue
                role_id_to_assign = selected_role['id']

                try:
                    # Chiamata a utenti_service (ancora con vecchio db_manager)
                    utenti_service.register_user_service(
                        db_context, username, plain_password, email, role_id_to_assign, nome_completo,
                        client_ip_address=client_ip_address,
                        created_by_user_id=logged_in_user_id
                    )
                    print(f"Utente {username} creato (o tentativo inviato).")
                except ValueError as ve:
                    print(f"ERRORE: {ve}")
                except Exception as e_reg:
                    logger.error(f"Errore imprevisto creazione utente: {e_reg}", exc_info=True)
                    print(f"Errore imprevisto: {e_reg}")
            
            elif scelta == '3':
                _modifica_utente_admin_menu(db_context, logged_in_user_id, client_ip_address, current_session_id)
            elif scelta == '4':
                _disattiva_utente_admin_menu(db_context, logged_in_user_id, client_ip_address, current_session_id)
            elif scelta == '5':
                _reset_password_admin_menu(db_context, logged_in_user_id, client_ip_address, current_session_id)
            elif scelta == '0':
                break
            else:
                print("Scelta non valida.")
    finally:
        if db_session_for_utenti:
            db_session_for_utenti.close()


def _modifica_utente_admin_menu(db_context, admin_user_id, client_ip, session_id_audit): # db_context può essere session o db_manager
    print("\n--- Modifica Dati Utente (Admin) ---")
    # Assumendo che utenti_service.get_users_service e get_user_by_id_service usino db_context
    utenti = utenti_service.get_users_service(db_context)
    if not utenti: print("Nessun utente da modificare."); return

    utente_selezionato = seleziona_da_lista(utenti, "Seleziona Utente da Modificare", 
                                            desc_keys=['username', 'nome_completo', 'email', 'nome_ruolo'])
    if not utente_selezionato: return
    user_id_to_update = utente_selezionato['id']
    dettagli_utente_attuale = utenti_service.get_user_by_id_service(db_context, user_id_to_update)
    if not dettagli_utente_attuale: print(f"Impossibile recuperare dettagli per ID {user_id_to_update}."); return

    print(f"\nModifica utente: {dettagli_utente_attuale['username']} (ID: {user_id_to_update})")
    dati_da_aggiornare = {}
    # ... (logica per chiedere i campi da modificare, come nel tuo file originale)
    nuova_email = input_valore(f"Nuova Email (attuale: {dettagli_utente_attuale.get('email')}):", obbligatorio=False)
    if nuova_email and nuova_email != dettagli_utente_attuale.get('email'): dati_da_aggiornare['email'] = nuova_email
    # ... altri campi ...
    
    if not dati_da_aggiornare: print("Nessuna modifica."); return
    if chiedi_conferma(f"Confermi le modifiche per {dettagli_utente_attuale['username']}? Dati: {dati_da_aggiornare}"):
        try:
            utenti_service.update_user_service( # Assumendo che usi db_context
                db_context, user_id_to_update, dati_da_aggiornare,
                current_user_id=admin_user_id, client_ip_address=client_ip, session_id=session_id_audit
            )
            print("Utente aggiornato (o tentativo inviato).")
        except ValueError as ve: print(f"ERRORE: {ve}")
        except Exception as e_upd: logger.error(f"Errore update utente: {e_upd}", exc_info=True); print(f"Errore: {e_upd}")

# ... (similmente per _disattiva_utente_admin_menu, _reset_password_admin_menu, _cambia_password_utente_menu,
#      assicurandosi che usino db_context (che potrebbe essere una sessione SQLAlchemy se utenti_service è convertito,
#      o il vecchio db_manager se non lo è ancora) )

# --- Menu Anagrafiche Base (MODIFICATO per SQLAlchemy) ---
def gestisci_anagrafiche_base(
    logged_in_user_id: Optional[int],
    current_user_role_id: Optional[int], # Per permessi futuri
    current_session_id: Optional[str],
    client_ip_address: Optional[str]
):
    db: Session = next(get_db())
    try:
        while True:
            print("\n--- Gestione Anagrafiche di Base ---")
            print("1. Gestisci Comuni")
            print("2. Gestisci Sezioni")
            print("3. Visualizza Tipi Documento")
            print("4. Visualizza Tipi Immobile")
            print("5. Visualizza Tipi Possesso")
            print("6. Visualizza Tipi Variazione")
            print("0. Torna al menu principale")
            scelta_anag = input("Scegli un'opzione: ")

            if scelta_anag == '1':
                _menu_crud_comuni(db, logged_in_user_id, current_session_id, client_ip_address)
            elif scelta_anag == '2':
                _menu_crud_sezioni(db, logged_in_user_id, current_session_id, client_ip_address)
            elif scelta_anag == '3':
                _visualizza_anagrafica_semplice(db, "Tipo Documento", anagrafiche_service.get_tipi_documento_service)
            elif scelta_anag == '4':
                _visualizza_anagrafica_semplice(db, "Tipo Immobile", anagrafiche_service.get_tipi_immobile_service)
            elif scelta_anag == '5':
                _visualizza_anagrafica_semplice(db, "Tipo Possesso", anagrafiche_service.get_tipi_possesso_service)
            elif scelta_anag == '6':
                _visualizza_anagrafica_semplice(db, "Tipo Variazione", anagrafiche_service.get_tipi_variazione_service)
            elif scelta_anag == '0':
                break
            else:
                print("Scelta non valida.")
    finally:
        db.close()

def _menu_crud_comuni(
    db: Session,
    logged_in_user_id: Optional[int],
    current_session_id: Optional[str],
    client_ip_address: Optional[str]
):
    nome_entita = "Comune"
    while True:
        print(f"\n--- Gestione {nome_entita} ---")
        print(f"1. Visualizza tutti i {nome_entita}")
        print(f"2. Aggiungi nuovo {nome_entita}")
        print(f"3. Modifica {nome_entita}")
        print(f"4. Cancella {nome_entita}")
        print("0. Torna indietro")
        scelta = input("Scegli un'opzione: ")

        if scelta == '1':
            print(f"\n--- Lista {nome_entita} ---")
            elementi = anagrafiche_service.get_comuni_service(db)
            if elementi:
                for idx, el in enumerate(elementi):
                    print(f"{idx+1}. ID: {el['id']} - Nome: {el['nome']}, Prov: {el['provincia']}, Reg: {el['regione']}")
            else:
                print(f"Nessun {nome_entita} trovato.")
        
        elif scelta == '2':
            print(f"\n--- Aggiungi Nuovo {nome_entita} ---")
            nome = input_valore("Nome Comune:", validatore=validatore_non_vuoto)
            if nome is None: continue
            provincia = input_valore("Provincia:", validatore=validatore_non_vuoto)
            if provincia is None: continue
            regione = input_valore("Regione:", validatore=validatore_non_vuoto)
            if regione is None: continue

            if chiedi_conferma(f"Creare {nome_entita}: Nome='{nome}', Provincia='{provincia}', Regione='{regione}'?"):
                risultato = anagrafiche_service.create_comune_service(
                    db, nome, provincia, regione,
                    audit_user_id=logged_in_user_id,
                    audit_session_id=current_session_id,
                    audit_client_ip=client_ip_address
                )
                if risultato and "error" not in risultato:
                    print(f"{nome_entita} ID {risultato.get('id')} creato con successo.")
                elif risultato and "error" in risultato:
                    print(f"ERRORE: {risultato['error']}")
                else:
                    print(f"Creazione {nome_entita} fallita.")
        
        elif scelta == '3':
            print(f"\n--- Modifica {nome_entita} ---")
            comuni_list = anagrafiche_service.get_comuni_service(db)
            if not comuni_list: print(f"Nessun {nome_entita} da modificare."); continue
            
            comune_sel = seleziona_da_lista(comuni_list, f"Seleziona {nome_entita} da modificare", desc_keys=['nome', 'provincia'])
            if not comune_sel: continue
            comune_id_mod = comune_sel['id']
            
            dettagli_attuali = anagrafiche_service.get_comune_by_id_service(db, comune_id_mod)
            if not dettagli_attuali: print(f"{nome_entita} ID {comune_id_mod} non più trovato."); continue

            print(f"Modifica per {nome_entita}: {dettagli_attuali['nome']}. Lascia vuoto per non modificare.")
            dati_update = {}
            nome_nuovo = input_valore(f"Nuovo Nome (attuale: {dettagli_attuali['nome']}):", obbligatorio=False, default=dettagli_attuali['nome'])
            if nome_nuovo != dettagli_attuali['nome']: dati_update['nome'] = nome_nuovo
            
            prov_nuova = input_valore(f"Nuova Provincia (attuale: {dettagli_attuali['provincia']}):", obbligatorio=False, default=dettagli_attuali['provincia'])
            if prov_nuova != dettagli_attuali['provincia']: dati_update['provincia'] = prov_nuova
            
            reg_nuova = input_valore(f"Nuova Regione (attuale: {dettagli_attuali['regione']}):", obbligatorio=False, default=dettagli_attuali['regione'])
            if reg_nuova != dettagli_attuali['regione']: dati_update['regione'] = reg_nuova

            if not dati_update: print("Nessuna modifica specificata."); continue

            if chiedi_conferma(f"Aggiornare {nome_entita} ID {comune_id_mod} con dati: {dati_update}?"):
                try:
                    success = anagrafiche_service.update_comune_service(
                        db, comune_id_mod, dati_update,
                        audit_user_id=logged_in_user_id,
                        audit_session_id=current_session_id,
                        audit_client_ip=client_ip_address
                    )
                    if success: print(f"{nome_entita} aggiornato con successo.")
                    else: print(f"Aggiornamento {nome_entita} fallito o nessuna modifica effettuata.")
                except ValueError as ve: # Cattura ValueError da IntegrityError
                    print(f"ERRORE: {ve}")
                except Exception as e_upd:
                    logger.error(f"Errore imprevisto update comune: {e_upd}", exc_info=True)
                    print(f"Errore imprevisto: {e_upd}")

        elif scelta == '4':
            print(f"\n--- Cancella {nome_entita} ---")
            comuni_list = anagrafiche_service.get_comuni_service(db)
            if not comuni_list: print(f"Nessun {nome_entita} da cancellare."); continue
            
            comune_sel = seleziona_da_lista(comuni_list, f"Seleziona {nome_entita} da cancellare", desc_keys=['nome', 'provincia'])
            if not comune_sel: continue
            comune_id_del = comune_sel['id']
            
            if chiedi_conferma(f"ATTENZIONE: Sei sicuro di voler cancellare il comune '{comune_sel['nome']}' (ID: {comune_id_del})?", default_yes=False):
                try:
                    success = anagrafiche_service.delete_comune_service(
                        db, comune_id_del,
                        audit_user_id=logged_in_user_id,
                        audit_session_id=current_session_id,
                        audit_client_ip=client_ip_address
                    )
                    if success: print(f"{nome_entita} cancellato con successo.")
                    else: print(f"Cancellazione {nome_entita} fallita.")
                except ValueError as ve: # Cattura l'errore di dipendenza
                    print(f"ERRORE: {ve}")
                except Exception as e_del:
                    logger.error(f"Errore imprevisto cancellazione comune: {e_del}", exc_info=True)
                    print(f"Errore imprevisto: {e_del}")
        elif scelta == '0':
            break
        else:
            print("Scelta non valida.")

def _menu_crud_sezioni(
    db: Session,
    logged_in_user_id: Optional[int],
    current_session_id: Optional[str],
    client_ip_address: Optional[str]
):
    nome_entita = "Sezione"
    while True:
        print(f"\n--- Gestione {nome_entita} ---")
        print(f"1. Visualizza {nome_entita} (per Comune)")
        print(f"2. Aggiungi nuova {nome_entita}")
        print(f"3. Modifica {nome_entita}")
        print(f"4. Cancella {nome_entita}")
        print("0. Torna indietro")
        scelta = input("Scegli un'opzione: ")

        if scelta == '1':
            comuni = anagrafiche_service.get_comuni_service(db)
            if not comuni: print("Nessun comune definito per filtrare le sezioni."); continue
            comune_sel = seleziona_da_lista(comuni, "Seleziona Comune per visualizzare le Sezioni (0 per tutte, se supportato)", desc_keys=['nome'])
            comune_id_filtro = comune_sel['id'] if comune_sel else None
            
            print(f"\n--- Lista {nome_entita} {'per ' + comune_sel['nome'] if comune_sel else ''} ---")
            elementi = anagrafiche_service.get_sezioni_service(db, comune_id_filter=comune_id_filtro)
            if elementi:
                for idx, el in enumerate(elementi):
                    print(f"{idx+1}. ID: {el['id']} - Nome: {el['nome_sezione']}, Cod: {el.get('codice_sezione', 'N/D')}, Comune: {el['nome_comune']}")
            else:
                print(f"Nessuna {nome_entita} trovata.")
        
        elif scelta == '2': # Aggiungi Sezione
            print(f"\n--- Aggiungi Nuova {nome_entita} ---")
            comuni = anagrafiche_service.get_comuni_service(db)
            if not comuni: print("Nessun comune disponibile per associare la sezione."); continue
            comune_sel = seleziona_da_lista(comuni, "Seleziona Comune di appartenenza", desc_keys=['nome'])
            if not comune_sel: continue
            comune_id_scelto = comune_sel['id']

            nome_sezione = input_valore("Nome Sezione:", validatore=validatore_non_vuoto)
            if nome_sezione is None: continue
            codice_sezione = input_valore("Codice Sezione (opzionale):", obbligatorio=False)
            note = input_valore("Note (opzionale):", obbligatorio=False)

            if chiedi_conferma(f"Creare Sezione: Nome='{nome_sezione}', Codice='{codice_sezione}' per Comune '{comune_sel['nome']}'?"):
                risultato = anagrafiche_service.create_sezione_service(
                    db, comune_id_scelto, nome_sezione, codice_sezione, note,
                    audit_user_id=logged_in_user_id,
                    audit_session_id=current_session_id,
                    audit_client_ip=client_ip_address
                )
                if risultato and "error" not in risultato:
                    print(f"{nome_entita} ID {risultato.get('id')} creata con successo.")
                elif risultato and "error" in risultato:
                    print(f"ERRORE: {risultato['error']}")
                else:
                    print(f"Creazione {nome_entita} fallita.")

        elif scelta == '3': # Modifica Sezione
            print(f"\n--- Modifica {nome_entita} ---")
            # Prima fai selezionare una sezione (potrebbe essere necessario filtrare per comune prima)
            tutte_le_sezioni = anagrafiche_service.get_sezioni_service(db) # Ottiene tutte per la selezione iniziale
            if not tutte_le_sezioni: print(f"Nessuna {nome_entita} da modificare."); continue

            sezione_sel = seleziona_da_lista(tutte_le_sezioni, f"Seleziona {nome_entita} da modificare", 
                                              desc_keys=['nome_sezione', 'codice_sezione', 'nome_comune'])
            if not sezione_sel: continue
            sezione_id_mod = sezione_sel['id']
            
            dettagli_attuali = anagrafiche_service.get_sezione_by_id_service(db, sezione_id_mod)
            if not dettagli_attuali: print(f"{nome_entita} ID {sezione_id_mod} non più trovata."); continue

            print(f"Modifica per {nome_entita}: {dettagli_attuali['nome_sezione']}. Lascia vuoto per non modificare.")
            dati_update = {}
            # Non permettiamo di cambiare comune_id qui per semplicità, richiederebbe logica più complessa.

            nome_nuovo = input_valore(f"Nuovo Nome Sezione (attuale: {dettagli_attuali['nome_sezione']}):", obbligatorio=False, default=dettagli_attuali['nome_sezione'])
            if nome_nuovo != dettagli_attuali['nome_sezione']: dati_update['nome_sezione'] = nome_nuovo
            
            codice_nuovo = input_valore(f"Nuovo Codice Sezione (attuale: {dettagli_attuali.get('codice_sezione','N/D')}):", obbligatorio=False, default=dettagli_attuali.get('codice_sezione'))
            if codice_nuovo != dettagli_attuali.get('codice_sezione'): dati_update['codice_sezione'] = codice_nuovo
            
            note_nuove = input_valore(f"Nuove Note (attuali: {dettagli_attuali.get('note','N/D')}):", obbligatorio=False, default=dettagli_attuali.get('note'))
            if note_nuove != dettagli_attuali.get('note'): dati_update['note'] = note_nuove

            if not dati_update: print("Nessuna modifica specificata."); continue

            if chiedi_conferma(f"Aggiornare {nome_entita} ID {sezione_id_mod} con dati: {dati_update}?"):
                try:
                    success = anagrafiche_service.update_sezione_service(
                        db, sezione_id_mod, dati_update,
                        audit_user_id=logged_in_user_id,
                        audit_session_id=current_session_id,
                        audit_client_ip=client_ip_address
                    )
                    if success: print(f"{nome_entita} aggiornata con successo.")
                    else: print(f"Aggiornamento {nome_entita} fallito o nessuna modifica.")
                except ValueError as ve: print(f"ERRORE: {ve}")
                except Exception as e_upd_sez: logger.error(f"Errore update sezione: {e_upd_sez}", exc_info=True); print(f"Errore: {e_upd_sez}")
        
        elif scelta == '4': # Cancella Sezione
            print(f"\n--- Cancella {nome_entita} ---")
            tutte_le_sezioni = anagrafiche_service.get_sezioni_service(db)
            if not tutte_le_sezioni: print(f"Nessuna {nome_entita} da cancellare."); continue
            
            sezione_sel = seleziona_da_lista(tutte_le_sezioni, f"Seleziona {nome_entita} da cancellare", 
                                              desc_keys=['nome_sezione', 'codice_sezione', 'nome_comune'])
            if not sezione_sel: continue
            sezione_id_del = sezione_sel['id']
            
            if chiedi_conferma(f"ATTENZIONE: Sei sicuro di voler cancellare la sezione '{sezione_sel['nome_sezione']}' (ID: {sezione_id_del})?", default_yes=False):
                try:
                    success = anagrafiche_service.delete_sezione_service(
                        db, sezione_id_del,
                        audit_user_id=logged_in_user_id,
                        audit_session_id=current_session_id,
                        audit_client_ip=client_ip_address
                    )
                    if success: print(f"{nome_entita} cancellata con successo.")
                    else: print(f"Cancellazione {nome_entita} fallita.")
                except ValueError as ve: print(f"ERRORE: {ve}")
                except Exception as e_del_sez: logger.error(f"Errore cancella sezione: {e_del_sez}", exc_info=True); print(f"Errore: {e_del_sez}")

        elif scelta == '0':
            break
        else:
            print("Scelta non valida.")

def _visualizza_anagrafica_semplice(
    db: Session,
    nome_entita: str,
    get_all_service_func: Callable[[Session], List[Dict[str, Any]]]
):
    print(f"\n--- Lista {nome_entita} ---")
    elementi = get_all_service_func(db)
    if elementi:
        for idx, el in enumerate(elementi):
            print(f"{idx+1}. ID: {el['id']} - Nome: {el['nome']} (Desc: {el.get('descrizione', 'N/D')})")
    else:
        print(f"Nessun {nome_entita} trovato.")
    input("Premi Invio per continuare...")


# --- Menu Gestione Partite (MODIFICATO per SQLAlchemy in anagrafiche_service) ---
def gestisci_partite_menu(
    db: Session, # Ora accetta la sessione SQLAlchemy
    logged_in_user_id: Optional[int],
    current_session_id: Optional[str],
    client_ip_address: Optional[str]
):
    # audit_info non più necessario se passiamo i parametri individualmente
    while True:
        print("\n--- Gestione Partite ---")
        print("1. Visualizza/Cerca Partite")
        print("2. Inserisci Nuova Partita")
        # ... (altre opzioni come prima) ...
        print("0. Torna al menu principale")
        scelta = input("Scegli un'opzione: ")

        if scelta == '1':
            _visualizza_cerca_partite_menu(db, logged_in_user_id, current_session_id, client_ip_address)
        elif scelta == '2':
            _inserisci_nuova_partita_menu(db, logged_in_user_id, current_session_id, client_ip_address)
        # ... implementa gli altri casi ...
        elif scelta == '0':
            break
        else:
            print("Scelta non valida.")

def _visualizza_cerca_partite_menu(
    db: Session,
    logged_in_user_id: Optional[int],
    current_session_id: Optional[str],
    client_ip_address: Optional[str]
):
    print("\n--- Visualizza/Cerca Partite ---")
    comune_id_filtro: Optional[int] = None
    sezione_id_filtro: Optional[int] = None
    numero_partita_filtro: Optional[str] = None
    cognome_possessore_filtro: Optional[str] = None
    
    print("Lasciare vuoto per non filtrare per quel criterio.")
    
    comuni = anagrafiche_service.get_comuni_service(db) # Usa la sessione db
    if comuni:
        comune_sel = seleziona_da_lista(comuni, titolo="Filtra per Comune (opzionale, 0 per saltare)", desc_keys=['nome'])
        if comune_sel: 
            comune_id_filtro = comune_sel['id']
            sezioni = anagrafiche_service.get_sezioni_service(db, comune_id_filter=comune_id_filtro) # Usa la sessione db
            if sezioni:
                sezione_sel = seleziona_da_lista(sezioni, titolo="Filtra per Sezione (opzionale, 0 per saltare)", desc_keys=['nome_sezione'])
                if sezione_sel: sezione_id_filtro = sezione_sel['id']

    numero_partita_filtro = input_valore("Numero Partita (opzionale):", obbligatorio=False)
    cognome_possessore_filtro = input_valore("Cognome/Denom. Possessore (opzionale):", obbligatorio=False)

    # La chiamata a partite_service.search_partite_service dovrà essere adattata quando
    # partite_service sarà convertito a SQLAlchemy per accettare db: Session.
    # Per ora, questa parte rimane concettualmente simile ma la chiamata effettiva fallirebbe
    # se search_partite_service si aspetta ancora il vecchio db_manager.
    print(f"\n[!] Ricerca partite con filtri (partite_service da convertire a SQLAlchemy):")
    print(f"    Comune ID: {comune_id_filtro}, Sezione ID: {sezione_id_filtro}, Numero: {numero_partita_filtro}, Possessore: {cognome_possessore_filtro}")
    
    # Esempio di chiamata (ipotizzando che partite_service sia stato convertito):
    # partite_trovate = partite_service.search_partite_service(
    #     db,
    #     comune_id=comune_id_filtro,
    #     sezione_id=sezione_id_filtro,
    #     numero_partita=numero_partita_filtro,
    #     cognome_possessore=cognome_possessore_filtro,
    #     # ... altri filtri e parametri di audit ...
    # )
    # if partite_trovate:
    #     # ... visualizza ...
    # else:
    #     print("Nessuna partita trovata.")
    input("Funzionalità di ricerca e visualizzazione dettagli partita da completare dopo conversione di partite_service. Premi Invio...")


def _inserisci_nuova_partita_menu(
    db: Session, 
    logged_in_user_id: Optional[int], 
    current_session_id: Optional[str], 
    client_ip_address: Optional[str]
):
    print("\n--- Inserisci Nuova Partita ---")
    comuni = anagrafiche_service.get_comuni_service(db)
    if not comuni: print("Nessun comune definito. Impossibile creare partita."); return
    comune_sel = seleziona_da_lista(comuni, "Seleziona Comune", desc_keys=['nome'])
    if not comune_sel: return
    comune_id = comune_sel['id']

    sezioni = anagrafiche_service.get_sezioni_service(db, comune_id_filter=comune_id)
    if not sezioni: print(f"Nessuna sezione definita per il comune '{comune_sel['nome']}'."); return
    sezione_sel = seleziona_da_lista(sezioni, f"Seleziona Sezione per {comune_sel['nome']}", desc_keys=['nome_sezione'])
    if not sezione_sel: return
    sezione_id = sezione_sel['id']

    numero_partita = input_valore("Numero Partita:", validatore=validatore_non_vuoto)
    if not numero_partita: return
    
    data_creazione_str = input_valore("Data Creazione Partita (GG/MM/AAAA, oggi se vuoto):", tipo=str, obbligatorio=False)
    data_creazione = parse_data_utente(data_creazione_str) or datetime.now().date()

    tipo_partita = input_valore("Tipo Partita (es. Terreni, Fabbricati):", obbligatorio=False)
    note_partita = input_valore("Note Partita:", obbligatorio=False)

    # La chiamata a partite_service.create_partita_service dovrà essere adattata
    # quando partite_service sarà convertito a SQLAlchemy.
    print(f"\n[!] Creazione partita (partite_service da convertire a SQLAlchemy):")
    print(f"    Comune ID: {comune_id}, Sezione ID: {sezione_id}, Numero: {numero_partita}")
    # Esempio di chiamata:
    # risultato_creazione = partite_service.create_partita_service(
    #     db, comune_id, numero_partita, sezione_id, data_creazione, tipo_partita, note_partita,
    #     audit_user_id=logged_in_user_id, audit_session_id=current_session_id, audit_client_ip=client_ip_address
    # )
    # if risultato_creazione and "error" not in risultato_creazione:
    #     partita_id_creata = risultato_creazione.get('id')
    #     print(f"Partita N.{numero_partita} creata con ID {partita_id_creata}.")
    #     if chiedi_conferma("Vuoi aggiungere intestatari ora?"): _gestisci_intestazioni_partita(db, partita_id_creata, ...)
    #     if chiedi_conferma("Vuoi aggiungere immobili ora?"): _gestisci_immobili_partita(db, partita_id_creata, ...)
    # else:
    #     print(f"Creazione partita fallita: {risultato_creazione.get('error') if risultato_creazione else 'Errore sconosciuto'}")
    input("Funzionalità di creazione partita da completare dopo conversione di partite_service. Premi Invio...")

# ... (Altre funzioni come _gestisci_intestazioni_partita, _aggiungi_intestatario_a_partita, etc.
#      dovranno essere adattate quando i servizi partite_service e possessore_service saranno convertiti)

# --- Menu Principale (MODIFICATO per passare parametri di stato e gestire sessioni) ---
def menu_principale(
    logged_in_user_id: Optional[int],
    current_user_role_id: Optional[int],
    current_session_id: Optional[str],
    client_ip_address: Optional[str],
    db_manager_old_instance # Mantenuto temporaneamente se alcuni servizi non sono convertiti
):
    logger.info(f"Utente ID {logged_in_user_id} (Ruolo ID: {current_user_role_id}, Sessione: {current_session_id}) al menu principale.")

    while True:
        print("\n--- Menu Principale ---")
        print("1. Gestione Partite")
        print("2. Gestione Possessori")
        print("3. Gestione Immobili")
        print("4. Gestione Volture")
        print("5. Gestione Documenti")
        print("6. Gestione Anagrafiche di Base")
        print("7. Genera Report")
        print("8. Cambia la mia password")
        if current_user_role_id == ADMIN_ROLE_ID:
            print("9. Gestione Utenti (Admin)")
        print("0. Logout e Esci")
        
        scelta = input("Scegli un'opzione: ")

        # Gestione della sessione per ogni "unità di lavoro" del menu
        if scelta in ['1', '2', '3', '4', '5', '7']: # Opzioni che interagiranno con servizi (da convertire)
            db_session_menu: Session = next(get_db())
            try:
                if scelta == '1':
                    gestisci_partite_menu(db_session_menu, logged_in_user_id, current_session_id, client_ip_address)
                elif scelta == '2':
                    print("Menu Gestione Possessori - Da implementare con SQLAlchemy")
                    # gestisci_possessori_menu(db_session_menu, logged_in_user_id, ...)
                # ... implementare gli altri ...
            finally:
                db_session_menu.close()
        
        elif scelta == '6': # Gestione Anagrafiche (usa già SQLAlchemy internamente)
            gestisci_anagrafiche_base(logged_in_user_id, current_user_role_id, current_session_id, client_ip_address)
        
        elif scelta == '8': # Cambia password (presumibilmente utenti_service non è ancora convertito)
            # _cambia_password_utente_menu(db_manager_old_instance, logged_in_user_id, client_ip_address, current_session_id)
            print("Funzione Cambia Password (presume utenti_service non ancora convertito a SQLAlchemy)")
            # Se utenti_service fosse convertito:
            # db_session_pass: Session = next(get_db())
            # try:
            #     _cambia_password_utente_menu(db_session_pass, logged_in_user_id, client_ip_address, current_session_id)
            # finally:
            #     db_session_pass.close()


        elif scelta == '9' and current_user_role_id == ADMIN_ROLE_ID:
            gestisci_utenti(db_manager_old_instance, logged_in_user_id, current_user_role_id, current_session_id, client_ip_address)
        
        elif scelta == '0':
            print("Logout in corso...")
            # Qui dovresti chiamare utenti_service.logout_user_service
            # Se utenti_service è convertito, otterrai una sessione db e la passerai.
            # Se usa ancora db_manager_old_instance, passerai quello.
            # Esempio (se utenti_service usa db_manager_old_instance):
            if utenti_service.logout_user_service(db_manager_old_instance, logged_in_user_id, current_session_id, client_ip_address):
                 logger.info(f"Utente ID {logged_in_user_id} logout completato.")
            else:
                 logger.warning(f"Problema durante il logout per utente ID {logged_in_user_id}.")
            break
        else:
            print("Scelta non valida. Riprova.")