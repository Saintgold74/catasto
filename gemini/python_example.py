#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Esempio di utilizzo del gestore database catastale
======================================================================================
Questo script mostra esempi pratici di come utilizzare
la classe CatastoDBManager per interagire con il database,
includendo gestione utenti e audit.

Autore: Marco Santoro
Data: 16/05/2025 (Versione completa riscritta con login all'avvio e struttura menu corretta)
"""

from catasto_db_manager import CatastoDBManager
from datetime import date, datetime
import json
import os
import sys
import getpass # Per nascondere input password
import logging # Per logging
import bcrypt  # Per hashing sicuro password
from typing import Optional, List, Dict, Any # Per type hinting

# --- Configurazione Logging ---
logging.basicConfig(
    level=logging.INFO, # O DEBUG per maggiori dettagli
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("python_example.log"), # Log separato per l'esempio
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Variabili Globali per Sessione Utente ---
logged_in_user_id: Optional[int] = None
logged_in_user_info: Optional[Dict] = None # Per username/nome_completo
current_session_id: Optional[str] = None
client_ip_address: str = "127.0.0.1" # Simula IP client

# --- Funzioni Helper per Interfaccia Utente ---

def stampa_locandina_introduzione():
    """Stampa una locandina di introduzione testuale."""
    larghezza = 80
    oggi = date.today().strftime("%d/%m/%Y")
    versione = "1.5" # Versione aggiornata
    titolo = "Applicazione Gestione Catasto Storico"
    autore = "Marco Santoro"
    ente = "Archivio di Stato di Savona"
    realizzato_per = f"Realizzato da {autore} per conto dell'{ente}"

    print("+" + "-" * (larghezza - 2) + "+")
    print("|" + " " * (larghezza - 2) + "|")
    print("|" + titolo.center(larghezza - 2) + "|")
    print("|" + ("Versione " + versione).center(larghezza - 2) + "|")
    print("|" + ("Data: " + oggi).center(larghezza - 2) + "|")
    print("|" + " " * (larghezza - 2) + "|")
    print("|" + realizzato_per.center(larghezza - 2) + "|")
    print("|" + " " * (larghezza - 2) + "|")
    print("+" + "-" * (larghezza - 2) + "+")
    print("\n")

def stampa_intestazione(titolo: str):
    """Stampa un'intestazione formattata."""
    print("\n" + "=" * 80)
    print(f" {titolo} ".center(80, "="))
    print("=" * 80)

def _hash_password(password: str) -> str:
    """Funzione helper per hashare la password usando bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

def _verify_password(stored_hash: str, provided_password: str) -> bool:
    """Funzione helper per verificare la password usando bcrypt."""
    try:
        stored_hash_bytes = stored_hash.encode('utf-8')
        provided_password_bytes = provided_password.encode('utf-8')
        return bcrypt.checkpw(provided_password_bytes, stored_hash_bytes)
    except ValueError:
        logger.error(f"Tentativo di verifica con hash non valido: {stored_hash[:10]}...")
        return False
    except Exception as e:
        logger.error(f"Errore imprevisto durante la verifica bcrypt: {e}")
        return False

def _set_session_context(db: CatastoDBManager):
    """Imposta il contesto utente nel DB se loggato per l'audit."""
    global logged_in_user_id, client_ip_address
    if logged_in_user_id:
        db.set_session_app_user(logged_in_user_id, client_ip_address)
    else:
        db.clear_session_app_user()

def _confirm_action(prompt: str) -> bool:
    """Chiede conferma all'utente."""
    return input(f"{prompt} (s/n)? ").strip().lower() == 's'

def _seleziona_comune(db: CatastoDBManager, prompt: str = "Seleziona il comune:") -> Optional[int]:
    """
    Mostra l'elenco dei comuni e chiede all'utente di selezionarne uno.
    Ritorna l'ID del comune selezionato o None se la selezione non è valida o annullata.
    """
    comuni = db.get_comuni()
    if not comuni:
        print("\nERRORE: Nessun comune trovato nel database. Aggiungere prima un comune.")
        return None

    print(f"\n{prompt}")
    for i, c in enumerate(comuni, 1):
        print(f"{i}. {c['nome']} (ID: {c['id']})")
    print("0. Annulla")

    while True:
        scelta = input(f"Inserisci il numero (1-{len(comuni)}) o 0 per annullare: ").strip()
        if scelta == '0':
            return None
        if scelta.isdigit():
            try:
                scelta_int = int(scelta)
                if 1 <= scelta_int <= len(comuni):
                    comune_selezionato = comuni[scelta_int - 1]
                    print(f"--> Comune selezionato: {comune_selezionato['nome']} (ID: {comune_selezionato['id']})")
                    return comune_selezionato['id']
                else:
                    print("Selezione fuori range. Riprova.")
            except ValueError:
                 print("Input numerico non valido. Riprova.")
        else:
            print("Input non numerico. Riprova.")

# --- Funzione di Login dedicata (da chiamare all'avvio) ---
def esegui_login(db: CatastoDBManager) -> bool:
    """
    Gestisce il processo di login dell'utente.
    Restituisce True se il login ha successo, False altrimenti.
    """
    global logged_in_user_id, logged_in_user_info, current_session_id

    max_tentativi = 3
    tentativi = 0

    while tentativi < max_tentativi:
        stampa_intestazione("LOGIN UTENTE")
        username_login = input("Username: ").strip()
        password_login = getpass.getpass("Password: ")

        if not username_login or not password_login:
            print("Username e password sono obbligatori.")
            tentativi += 1
            if tentativi < max_tentativi:
                print(f"Tentativi rimasti: {max_tentativi - tentativi}")
                input("Premi INVIO per riprovare...")
            continue

        credentials = db.get_user_credentials(username_login) # Assumiamo restituisca id, username, password_hash, nome_completo
        login_success_local = False
        user_id_local = None

        if credentials:
            user_id_local = credentials['id']
            stored_hash = credentials['password_hash']
            logger.debug(f"Tentativo login per user ID {user_id_local}. Hash: {stored_hash[:10]}...")

            if _verify_password(stored_hash, password_login):
                login_success_local = True
            else:
                print("Password errata.")
                logger.warning(f"Login fallito (pwd errata) per user ID: {user_id_local}")
        else:
            print("Utente non trovato o non attivo.")
            logger.warning(f"Login fallito (utente '{username_login}' non trovato/attivo).")

        if user_id_local is not None: # Utente esiste nel DB, registriamo il tentativo
            # Passa application_name alla procedura registra_accesso
            session_id_returned = db.register_access(user_id_local, 'login', 
                                                     indirizzo_ip=client_ip_address, 
                                                     esito=login_success_local,
                                                     application_name='CatastoAppCLI') # Nome applicazione esplicito

            if login_success_local and session_id_returned:
                logged_in_user_id = user_id_local
                logged_in_user_info = {'id': user_id_local,
                                       'username': credentials.get('username'),
                                       'nome_completo': credentials.get('nome_completo')}
                current_session_id = session_id_returned
                if not db.set_session_app_user(logged_in_user_id, client_ip_address): # Imposta contesto per audit
                    logger.error("Impossibile impostare contesto DB post-login!")
                user_display_name = logged_in_user_info.get('nome_completo') or logged_in_user_info.get('username', 'N/D')
                print(f"\nLogin riuscito per utente: {user_display_name} (ID: {logged_in_user_id})")
                print(f"Sessione {current_session_id[:8]}... avviata.")
                return True # Login riuscito
            elif login_success_local and not session_id_returned:
                print("Errore critico: Impossibile registrare sessione accesso.")
                logger.error(f"Login OK per ID {user_id_local} ma fallita reg. accesso.")
            # else: login fallito, l'errore è già stato stampato
        
        tentativi += 1
        if tentativi < max_tentativi:
            print(f"Tentativi rimasti: {max_tentativi - tentativi}")
            input("Premi INVIO per riprovare...")

    print("Numero massimo di tentativi di login raggiunto. Uscita dal programma.")
    return False

# --- Funzioni dei Sottomenu ---

def menu_consultazione(db: CatastoDBManager):
    """Menu per operazioni di consultazione dati."""
    _set_session_context(db) # Imposta contesto per audit all'ingresso del menu

    while True:
        stampa_intestazione("CONSULTAZIONE DATI")
        print("1. Elenco comuni")
        print("2. Elenco partite per comune")
        print("3. Elenco possessori per comune")
        print("4. Ricerca partite (Semplice)")
        print("5. Dettagli partita")
        print("6. Elenco localita per comune")
        print("7. Ricerca Avanzata Possessori (Similarità)")
        print("8. Ricerca Avanzata Immobili")
        print("9. Cerca Immobili Specifici")
        print("10. Cerca Variazioni")
        print("11. Cerca Consultazioni")
        print("12. Esporta Partita in JSON")
        print("13. Esporta Possessore in JSON")
        print("0. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (0-13): ").strip()

        if scelta == "1": # Elenco comuni
            search_term = input("Termine di ricerca nome comune (lascia vuoto per tutti): ").strip()
            comuni = db.get_comuni(search_term or None)
            stampa_intestazione(f"COMUNI TROVATI ({len(comuni)})")
            if comuni:
                for c_item in comuni: # Rinominato per evitare conflitto con 'c' in _seleziona_comune
                    print(f"- ID: {c_item['id']} Nome: {c_item['nome']} ({c_item['provincia']}, {c_item['regione']})")
            else:
                print("Nessun comune trovato.")

        elif scelta == "2": # Elenco partite per comune
            comune_id = _seleziona_comune(db, "Seleziona il comune per visualizzare le partite:")
            if comune_id is not None:
                partite = db.get_partite_by_comune(comune_id)
                comune_info = next((c for c in db.get_comuni() if c['id'] == comune_id), None)
                comune_nome_display = comune_info['nome'] if comune_info else (partite[0]['comune_nome'] if partite else "N/D")
                stampa_intestazione(f"PARTITE DI {comune_nome_display.upper()} ({len(partite)})")
                if partite:
                    for p_item in partite: # Rinominato
                        stato = p_item['stato'].upper()
                        possessori_str = p_item.get('possessori', 'N/D') or 'Nessuno'
                        indirizzi_str = p_item.get('indirizzi_immobili', 'N/D') or 'Nessuno' # Per modifica suggerita
                        print(f"ID: {p_item['id']} - N.{p_item['numero_partita']} ({p_item['tipo']}) - Stato: {stato}")
                        print(f"  Possessori: {possessori_str}")
                        print(f"  Num. Immobili: {p_item.get('num_immobili', 0)}")
                        # print(f"  Indirizzi: {indirizzi_str}") # Decommentare se si implementa l'aggiunta indirizzi
                        print("-" * 20)
                else:
                    print("Nessuna partita trovata.")

        elif scelta == "3": # Elenco possessori per comune
            comune_id = _seleziona_comune(db, "Seleziona il comune per visualizzare i possessori:")
            if comune_id is not None:
                possessori = db.get_possessori_by_comune(comune_id)
                comune_info = next((c for c in db.get_comuni() if c['id'] == comune_id), None)
                comune_nome_display = comune_info['nome'] if comune_info else (possessori[0]['comune_nome'] if possessori else "N/D")
                stampa_intestazione(f"POSSESSORI DI {comune_nome_display.upper()} ({len(possessori)})")
                if possessori:
                    for p_item in possessori: # Rinominato
                        stato_p = "Attivo" if p_item.get('attivo') else "Non Attivo"
                        print(f"ID: {p_item['id']} - {p_item['nome_completo']} - Stato: {stato_p}")
                else:
                    print("Nessun possessore trovato.")

        elif scelta == "4": # Ricerca partite (Semplice)
            stampa_intestazione("RICERCA PARTITE (SEMPLICE)")
            comune_id_filter = None
            if _confirm_action("Filtrare per comune?"):
                 comune_id_filter = _seleziona_comune(db, "Seleziona il comune per cui filtrare:")
                 if comune_id_filter is None: print("Filtro comune annullato.")
            numero_str = input("Numero partita (esatto, opzionale): ").strip()
            possessore_filter = input("Nome possessore (anche parziale, opzionale): ").strip()
            natura_filter = input("Natura immobile (anche parziale, opzionale): ").strip()
            numero_partita_filter = int(numero_str) if numero_str.isdigit() else None
            partite_ricerca = db.search_partite( # Rinominato variabile
                comune_id=comune_id_filter, numero_partita=numero_partita_filter,
                possessore=possessore_filter or None, immobile_natura=natura_filter or None)
            stampa_intestazione(f"RISULTATI RICERCA PARTITE ({len(partite_ricerca)})")
            if partite_ricerca:
                for p_item in partite_ricerca: # Rinominato
                    print(f"ID: {p_item['id']} - {p_item['comune_nome']} - Partita N.{p_item['numero_partita']} ({p_item['tipo']}) - Stato: {p_item['stato']}")
            else:
                print("Nessuna partita trovata con questi criteri.")

        elif scelta == "5": # Dettagli partita
            id_partita_str = input("ID della partita per dettagli: ").strip()
            if id_partita_str.isdigit():
                partita_id_int = int(id_partita_str)
                partita_dettaglio = db.get_partita_details(partita_id_int) # Rinominato
                if partita_dettaglio:
                    stampa_intestazione(f"DETTAGLI PARTITA N.{partita_dettaglio['numero_partita']} (Comune: {partita_dettaglio['comune_nome']})")
                    print(f"ID: {partita_dettaglio['id']} - Tipo: {partita_dettaglio['tipo']} - Stato: {partita_dettaglio['stato']}")
                    print(f"Data Impianto: {partita_dettaglio['data_impianto']} - Data Chiusura: {partita_dettaglio.get('data_chiusura') or 'N/D'}")
                    print("\nPOSSESSORI:")
                    if partita_dettaglio.get('possessori'):
                        for pos_item in partita_dettaglio['possessori']: # Rinominato
                            print(f"- ID:{pos_item['id']} {pos_item['nome_completo']}{f' (Quota: {pos_item.get('quota')})' if pos_item.get('quota') else ''}")
                    else: print("  Nessuno")
                    print("\nIMMOBILI:")
                    if partita_dettaglio.get('immobili'):
                        for imm_item in partita_dettaglio['immobili']: # Rinominato
                            loc_str = f"{imm_item['localita_nome']}{f', {imm_item['civico']}' if imm_item.get('civico') else ''} ({imm_item['localita_tipo']})"
                            print(f"- ID:{imm_item['id']} {imm_item['natura']} in {loc_str}")
                            print(f"  Class: {imm_item.get('classificazione') or 'N/D'} - Cons: {imm_item.get('consistenza') or 'N/D'} - Piani: {imm_item.get('numero_piani') or 'N/D'} - Vani: {imm_item.get('numero_vani') or 'N/D'}")
                    else: print("  Nessuno")
                    print("\nVARIAZIONI:")
                    if partita_dettaglio.get('variazioni'):
                        for var_item in partita_dettaglio['variazioni']: # Rinominato
                             dest_partita_str = f" -> Partita Dest. ID {var_item.get('partita_destinazione_id')}" if var_item.get('partita_destinazione_id') else ""
                             print(f"- ID:{var_item['id']} Tipo:{var_item['tipo']} Data:{var_item['data_variazione']}{dest_partita_str}")
                             if var_item.get('tipo_contratto'): print(f"  Contratto: {var_item['tipo_contratto']} del {var_item['data_contratto']} (Notaio: {var_item.get('notaio') or 'N/D'}, Rep: {var_item.get('repertorio') or 'N/D'})")
                             if var_item.get('contratto_note'): print(f"  Note Contratto: {var_item['contratto_note']}")
                    else: print("  Nessuna")
                else:
                    print(f"Partita con ID {partita_id_int} non trovata.")
            else:
                print("ID partita non valido.")

        elif scelta == "6": # Elenco località per comune
             comune_id = _seleziona_comune(db, "Seleziona il comune per visualizzare le località:")
             if comune_id is not None:
                 comune_info = next((c for c in db.get_comuni() if c['id'] == comune_id), {'nome': 'N/D'})
                 comune_nome_display = comune_info['nome']
                 query = "SELECT id, nome, tipo, civico FROM localita WHERE comune_id = %s ORDER BY tipo, nome, civico"
                 if db.execute_query(query, (comune_id,)):
                      localita_list = db.fetchall()
                      stampa_intestazione(f"LOCALITÀ DI {comune_nome_display.upper()} ({len(localita_list)})")
                      if localita_list:
                           for loc_item in localita_list: # Rinominato
                               print(f"ID: {loc_item['id']} - {loc_item['nome']} ({loc_item['tipo']}){f', civico {loc_item['civico']}' if loc_item['civico'] is not None else ''}")
                      else:
                           print("Nessuna località trovata.")
                 else:
                      print("Errore nella ricerca delle località.")

        elif scelta == "7": # Ricerca Avanzata Possessori
             stampa_intestazione("RICERCA AVANZATA POSSESSORI (Similarità)")
             query_text = input("Termine di ricerca (nome/cognome/paternità): ").strip()
             if query_text:
                  # Chiamata corretta con il secondo parametro opzionale (threshold)
                  soglia_str = input("Soglia di similarità (0.0-1.0, INVIO per default 0.2): ").strip()
                  soglia = 0.2
                  if soglia_str:
                      try:
                          soglia = float(soglia_str)
                          if not (0.0 <= soglia <= 1.0):
                              print("Soglia non valida, uso default 0.2.")
                              soglia = 0.2
                      except ValueError:
                          print("Input soglia non numerico, uso default 0.2.")
                          soglia = 0.2
                  
                  results_possessori = db.ricerca_avanzata_possessori(query_text, similarity_threshold=soglia) # Rinominato
                  if results_possessori:
                       print(f"\nTrovati {len(results_possessori)} risultati (ordinati per similarità):")
                       for r_item in results_possessori:
                            sim_perc = round(r_item.get('similarity', 0) * 100, 1)
                            print(f"- ID: {r_item['id']} {r_item['nome_completo']} (Comune: {r_item.get('comune_nome', '?')})")
                            print(f"  Similarità: {sim_perc}% - Partite: {r_item.get('num_partite', 0)}")
                  else:
                       print("Nessun risultato trovato.")
             else:
                 print("Termine di ricerca obbligatorio.")

        elif scelta == "8": # Ricerca Avanzata Immobili
             stampa_intestazione("RICERCA AVANZATA IMMOBILI")
             comune_id_filter = None
             if _confirm_action("Filtrare per comune?"):
                 comune_id_filter = _seleziona_comune(db, "Seleziona il comune per cui filtrare:")
                 if comune_id_filter is None: print("Filtro comune annullato.")
             natura_filter = input("Natura Immobile (parziale, vuoto per tutti): ").strip() or None
             localita_nome_filter = input("Nome Località (parziale, vuoto per tutti): ").strip() or None
             classif_filter = input("Classificazione (esatta, vuoto per tutti): ").strip() or None
             possessore_nome_filter = input("Nome Possessore (parziale, vuoto per tutti): ").strip() or None
             results_immobili = db.ricerca_avanzata_immobili( # Rinominato
                 comune_id_filter, natura_filter, localita_nome_filter, classif_filter, possessore_nome_filter)
             if results_immobili:
                  print(f"\nTrovati {len(results_immobili)} immobili:")
                  for r_item in results_immobili:
                       print(f"- Imm.ID: {r_item['immobile_id']} - {r_item['natura']} in {r_item['localita_nome']} (Comune: {r_item.get('comune_nome','?')})")
                       print(f"  Partita N.{r_item['partita_numero']} - Class: {r_item.get('classificazione') or 'N/D'}")
                       print(f"  Possessori: {r_item.get('possessori') or 'N/D'}")
             else:
                 print("Nessun immobile trovato.")

        elif scelta == "9": # Cerca Immobili Specifici
             stampa_intestazione("CERCA IMMOBILI SPECIFICI")
             part_id_str = input("Filtra per ID Partita (vuoto per non filtrare): ").strip()
             comune_id_filter = None
             if _confirm_action("Filtrare per comune?"):
                 comune_id_filter = _seleziona_comune(db, "Seleziona il comune per cui filtrare:")
                 if comune_id_filter is None: print("Filtro comune annullato.")
             loc_id_str = input("Filtra per ID Località (vuoto per non filtrare): ").strip()
             natura_filter = input("Filtra per Natura (parziale, vuoto per non filtrare): ").strip() or None
             classif_filter = input("Filtra per Classificazione (esatta, vuoto per non filtrare): ").strip() or None
             try:
                  part_id_filter = int(part_id_str) if part_id_str else None
                  loc_id_filter = int(loc_id_str) if loc_id_str else None
                  immobili_list = db.search_immobili(
                      part_id_filter, comune_id_filter, loc_id_filter, natura_filter, classif_filter)
                  if immobili_list:
                       print(f"\nTrovati {len(immobili_list)} immobili:")
                       for imm_item in immobili_list:
                           print(f"- ID: {imm_item['id']}, Nat:{imm_item['natura']}, Loc:{imm_item['localita_nome']} (Comune:{imm_item.get('comune_nome','?')}), Part:{imm_item['numero_partita']}, Class:{imm_item.get('classificazione','-')}")
                  else:
                       print("Nessun immobile trovato.")
             except ValueError:
                 print("ID non valido.")

        elif scelta == "10": # Cerca Variazioni
             stampa_intestazione("CERCA VARIAZIONI")
             tipo_filter = input("Tipo (Acquisto/Successione/..., vuoto per tutti): ").strip().capitalize() or None
             data_i_str = input("Data inizio (YYYY-MM-DD, vuoto per non filtrare): ").strip()
             data_f_str = input("Data fine (YYYY-MM-DD, vuoto per non filtrare): ").strip()
             part_o_id_str = input("ID Partita Origine (vuoto per non filtrare): ").strip()
             part_d_id_str = input("ID Partita Destinazione (vuoto per non filtrare): ").strip()
             comune_id_filter = None
             if _confirm_action("Filtrare per comune di origine?"):
                 comune_id_filter = _seleziona_comune(db, "Seleziona il comune di origine per cui filtrare:")
                 if comune_id_filter is None: print("Filtro comune annullato.")
             try:
                  data_i_filter = datetime.strptime(data_i_str, "%Y-%m-%d").date() if data_i_str else None
                  data_f_filter = datetime.strptime(data_f_str, "%Y-%m-%d").date() if data_f_str else None
                  part_o_id_filter = int(part_o_id_str) if part_o_id_str else None
                  part_d_id_filter = int(part_d_id_str) if part_d_id_str else None
                  variazioni_list = db.search_variazioni(
                      tipo_filter, data_i_filter, data_f_filter, part_o_id_filter, part_d_id_filter, comune_id_filter)
                  if variazioni_list:
                       print(f"\nTrovate {len(variazioni_list)} variazioni:")
                       for v_item in variazioni_list:
                            dest_str = f" -> Dest.Partita:{v_item.get('partita_destinazione_numero', '-')}" if v_item.get('partita_destinazione_id') else ""
                            print(f"- ID:{v_item['id']} {v_item['data_variazione']} {v_item['tipo']} Orig.Partita:{v_item['partita_origine_numero']}(Comune:{v_item.get('comune_nome','?')}){dest_str} Rif:{v_item.get('numero_riferimento') or '-'}/{v_item.get('nominativo_riferimento') or '-'}")
                  else:
                       print("Nessuna variazione trovata.")
             except ValueError:
                 print("Input ID o Data non validi.")

        elif scelta == "11": # Cerca Consultazioni
             stampa_intestazione("CERCA CONSULTAZIONI")
             data_i_str = input("Data inizio (YYYY-MM-DD, vuoto per non filtrare): ").strip()
             data_f_str = input("Data fine (YYYY-MM-DD, vuoto per non filtrare): ").strip()
             richiedente_filter = input("Richiedente (parziale, vuoto per non filtrare): ").strip() or None
             funzionario_filter = input("Funzionario (parziale, vuoto per non filtrare): ").strip() or None
             try:
                  data_i_filter = datetime.strptime(data_i_str, "%Y-%m-%d").date() if data_i_str else None
                  data_f_filter = datetime.strptime(data_f_str, "%Y-%m-%d").date() if data_f_str else None
                  consultazioni_list = db.search_consultazioni(data_i_filter, data_f_filter, richiedente_filter, funzionario_filter)
                  if consultazioni_list:
                       print(f"\nTrovate {len(consultazioni_list)} consultazioni:")
                       for c_item in consultazioni_list:
                            print(f"- ID:{c_item['id']} {c_item['data']} Rich:{c_item['richiedente']} Funz:{c_item['funzionario_autorizzante']}")
                            print(f"  Mat: {c_item['materiale_consultato']}")
                  else:
                       print("Nessuna consultazione trovata.")
             except ValueError:
                 print("Formato Data non valido.")

        elif scelta == "12": # Esporta Partita
            _esporta_entita_json(db, tipo_entita='partita', etichetta_id='ID della Partita', nome_file_prefix='partita')
        elif scelta == "13": # Esporta Possessore
            _esporta_entita_json(db, tipo_entita='possessore', etichetta_id='ID del Possessore', nome_file_prefix='possessore')
        elif scelta == "0":
            break 
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

def menu_inserimento(db: CatastoDBManager):
    _set_session_context(db)
    while True:
        stampa_intestazione("INSERIMENTO E GESTIONE DATI")
        print("1. Aggiungi nuovo comune")
        print("2. Aggiungi nuovo possessore")
        print("3. Aggiungi nuova localita")
        print("4. Registra nuova proprieta (Workflow)")
        print("5. Registra passaggio di proprieta (Workflow)")
        print("6. Registra consultazione")
        print("7. Inserisci Contratto per Variazione")
        print("8. Duplica Partita")
        print("9. Trasferisci Immobile a Nuova Partita")
        print("0. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (0-9): ").strip()

        if scelta == "1": aggiungi_comune(db)
        elif scelta == "2": inserisci_possessore(db)
        elif scelta == "3": inserisci_localita(db)
        elif scelta == "4": _registra_nuova_proprieta_interattivo(db)
        elif scelta == "5": _registra_passaggio_proprieta_interattivo(db)
        elif scelta == "6": _registra_consultazione_interattivo(db)
        elif scelta == "7": _inserisci_contratto_interattivo(db)
        elif scelta == "8": _duplica_partita_interattivo(db)
        elif scelta == "9": _trasferisci_immobile_interattivo(db)
        elif scelta == "0":
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Funzioni Helper per menu_inserimento (MODIFICATE per comune_id) ---

def _registra_nuova_proprieta_interattivo(db: CatastoDBManager):
     """Guida l'utente nell'inserimento di una nuova proprietà (usa comune_id)."""
     stampa_intestazione("REGISTRA NUOVA PROPRIETA")
     comune_id = _seleziona_comune(db, "Seleziona il comune per la nuova proprietà:")
     if comune_id is None: print("Operazione annullata."); return

     num_partita_str = input("Numero nuova partita: ").strip()
     data_imp_str = input("Data impianto (YYYY-MM-DD): ").strip()
     if not num_partita_str.isdigit() or not data_imp_str: print("Numero partita e data impianto obbligatori."); return
     try: numero_partita = int(num_partita_str); data_impianto = datetime.strptime(data_imp_str, "%Y-%m-%d").date()
     except ValueError: print("Formato numero partita o data non valido."); return

     possessori = [] # Lista di dict per JSON
     print("\n--- Inserimento Possessori ---")
     while True:
          nome_completo = input("Nome completo possessore (o INVIO per terminare): ").strip()
          if not nome_completo: break
          # Verifica esistenza nel comune selezionato (passa ID)
          possessore_id_esistente = db.check_possessore_exists(nome_completo, comune_id)
          dati_possessore = {"nome_completo": nome_completo} # Inizia a costruire dict JSON
          if possessore_id_esistente: print(f"  -> Trovato possessore esistente ID: {possessore_id_esistente}")
          else:
               print("  -> Nuovo possessore. Inserisci dettagli:")
               dati_possessore["cognome_nome"] = input("     Cognome e Nome: ").strip()
               dati_possessore["paternita"] = input("     Paternità: ").strip()
               if not dati_possessore["cognome_nome"]: print("Cognome e Nome obbligatori."); continue
          quota = input(f"  Quota per {nome_completo} (es. 1/2, vuoto per esclusiva): ").strip()
          if quota: dati_possessore["quota"] = quota # Aggiungi quota al dict JSON
          possessori.append(dati_possessore) # Aggiungi dict alla lista
     if not possessori: print("È necessario almeno un possessore."); return

     immobili = [] # Lista di dict per JSON
     print("\n--- Inserimento Immobili ---")
     while True:
          natura = input("Natura immobile (es. Casa, o INVIO per terminare): ").strip()
          if not natura: break
          localita_nome = input("  Nome località: ").strip()
          if not localita_nome: print("Nome località obbligatorio."); continue
          # Tenta di inserire/trovare località (usa comune_id)
          # Qui potremmo migliorare chiedendo tipo e civico per una corrispondenza più precisa
          localita_id = db.insert_localita(comune_id, localita_nome, 'via') # Assume 'via', passa ID comune
          if not localita_id: print(f"Errore gestione località '{localita_nome}'."); continue

          # Costruisci dict JSON per immobile
          dati_immobile = {"natura": natura, "localita_id": localita_id, # Usa localita_id trovato/creato
                           "classificazione": input("  Classificazione (opzionale): ").strip() or None,
                           "numero_piani": None, "numero_vani": None,
                           "consistenza": input("  Consistenza (es. 120 mq, opzionale): ").strip() or None}
          piani_str = input("  Numero Piani (solo numero, opzionale): ").strip()
          if piani_str.isdigit(): dati_immobile["numero_piani"] = int(piani_str)
          vani_str = input("  Numero Vani (solo numero, opzionale): ").strip()
          if vani_str.isdigit(): dati_immobile["numero_vani"] = int(vani_str)
          # Aggiungi civico se necessario nel dict (non presente in questa versione)
          immobili.append(dati_immobile) # Aggiungi dict alla lista
     if not immobili: print("È necessario almeno un immobile."); return

     # Recupera nome comune per riepilogo
     comune_info = next((c for c in db.get_comuni() if c['id'] == comune_id), {'nome': 'N/D'})
     print("\nRiepilogo:")
     print(f"Comune: {comune_info['nome']} (ID: {comune_id}), Partita N.{numero_partita}, Data: {data_impianto}")
     print(f"Possessori: {len(possessori)}")
     for p in possessori: print(f"  - {p['nome_completo']} {'(Quota: ' + p.get('quota','Esclusiva') + ')' if p.get('quota') else ''}")
     print(f"Immobili: {len(immobili)}")
     # Recupera nome località per il riepilogo (richiede query aggiuntiva o modifica alla struttura dati raccolta)
     for i_dict in immobili:
         loc_info = db.fetchone() if db.execute_query("SELECT nome FROM localita WHERE id=%s", (i_dict['localita_id'],)) else {'nome': '?'}
         print(f"  - {i_dict['natura']} in {loc_info.get('nome','?')} (Loc. ID: {i_dict['localita_id']})")


     if _confirm_action("Procedere con la registrazione?"):
          # Chiama il manager con comune_id e le liste JSON
          if db.registra_nuova_proprieta(comune_id, numero_partita, data_impianto, possessori, immobili):
              print("Nuova proprietà registrata con successo.")
          else:
              print("Errore durante la registrazione della nuova proprietà (controllare log).")

def _registra_passaggio_proprieta_interattivo(db: CatastoDBManager):
     """Guida l'utente nella registrazione di un passaggio di proprietà (usa comune_id)."""
     stampa_intestazione("REGISTRA PASSAGGIO DI PROPRIETA")
     id_orig_str = input("ID Partita di Origine: ").strip()
     if not id_orig_str.isdigit(): print("ID non valido."); return
     partita_origine_id = int(id_orig_str)

     partita_orig = db.get_partita_details(partita_origine_id) # Ottiene anche comune_id e comune_nome origine
     if not partita_orig: print(f"Partita origine ID {partita_origine_id} non trovata."); return
     if partita_orig['stato'] == 'inattiva': print("La partita di origine è già inattiva."); return
     print(f"Partita Origine: N.{partita_orig['numero_partita']} (Comune: {partita_orig['comune_nome']}, ID: {partita_orig['comune_id']})")

     # Selezione comune destinazione (può essere lo stesso o diverso)
     print("\nSeleziona il comune per la nuova partita:")
     comune_dest_id = _seleziona_comune(db, "Seleziona comune destinazione")
     if comune_dest_id is None: print("Operazione annullata."); return

     num_part_dest_str = input("Numero nuova partita: ").strip()
     if not num_part_dest_str.isdigit(): print("Numero partita non valido."); return
     numero_partita_dest = int(num_part_dest_str)

     # Dati Variazione e Contratto
     tipo_var = input("Tipo Variazione (es. Vendita, Successione): ").strip().capitalize()
     data_var_str = input("Data Variazione (YYYY-MM-DD): ").strip()
     tipo_contr = input("Tipo Contratto associato (es. Vendita, Successione): ").strip().capitalize()
     data_contr_str = input("Data Contratto (YYYY-MM-DD): ").strip()
     if not tipo_var or not data_var_str or not tipo_contr or not data_contr_str: print("Tipo/Data Variazione e Tipo/Data Contratto obbligatori."); return
     try: data_variazione = datetime.strptime(data_var_str, "%Y-%m-%d").date(); data_contratto = datetime.strptime(data_contr_str, "%Y-%m-%d").date()
     except ValueError: print("Formato data non valido."); return

     notaio = input("Notaio (opzionale): ").strip() or None; repertorio = input("Repertorio (opzionale): ").strip() or None; note_var = input("Note variazione (opzionale): ").strip() or None

     # Gestione Nuovi Possessori (verranno creati/cercati nel comune_dest_id)
     nuovi_possessori_list = [] # Lista di dict per JSON
     if _confirm_action("Specificare nuovi possessori per la nuova partita (altrimenti verranno copiati)?"):
         print(f"\n--- Inserimento Nuovi Possessori (nel comune ID: {comune_dest_id}) ---")
         while True:
             nome_completo = input("Nome completo possessore (o INVIO per terminare): ").strip()
             if not nome_completo: break
             dati_poss = {"nome_completo": nome_completo}
             # Verifica esistenza nel comune di destinazione (usa ID)
             if not db.check_possessore_exists(nome_completo, comune_dest_id):
                  print("  -> Nuovo possessore:"); dati_poss["cognome_nome"] = input("     Cognome e Nome: ").strip(); dati_poss["paternita"] = input("     Paternità: ").strip()
                  if not dati_poss["cognome_nome"]: print("Cognome e Nome obbligatori."); continue
             quota = input(f"  Quota per {nome_completo} (vuoto per esclusiva): ").strip()
             if quota: dati_poss["quota"] = quota
             nuovi_possessori_list.append(dati_poss)
         # Se non ne inserisce nessuno ma ha scelto di specificarli, la lista sarà vuota
         if not nuovi_possessori_list: print("ATTENZIONE: Nessun nuovo possessore specificato, verranno copiati dall'origine se possibile.")

     # Selezione Immobili da Trasferire
     immobili_da_trasferire_list = None # Lista di ID interi
     if _confirm_action("Specificare quali immobili trasferire (altrimenti tutti)?"):
          immobili_da_trasferire_list = []
          print("\n--- Selezione Immobili da Trasferire ---")
          if partita_orig.get('immobili'):
               print("Immobili nella partita di origine:"); [print(f"  ID: {imm['id']} - {imm['natura']}") for imm in partita_orig['immobili']]
               while True:
                    id_imm_str = input("Inserisci ID immobile da trasferire (o INVIO per terminare): ").strip()
                    if not id_imm_str: break
                    if id_imm_str.isdigit() and any(imm['id'] == int(id_imm_str) for imm in partita_orig['immobili']):
                         immobili_da_trasferire_list.append(int(id_imm_str)); print(f"  -> Aggiunto immobile ID {id_imm_str}")
                    else: print("  ID non valido o non presente.")
          else: print("  Nessun immobile trovato nella partita origine.")

     # Riepilogo
     comune_dest_info = next((c for c in db.get_comuni() if c['id'] == comune_dest_id), {'nome': 'N/D'})
     print("\nRiepilogo Passaggio:")
     print(f"Da Partita ID {partita_origine_id} a N.{numero_partita_dest} (Comune: {comune_dest_info['nome']} ID: {comune_dest_id})")
     print(f"Variazione: {tipo_var} del {data_variazione}")
     print(f"Contratto: {tipo_contr} del {data_contratto}")
     print(f"Nuovi Possessori: {'Specificati (' + str(len(nuovi_possessori_list)) + ')' if nuovi_possessori_list else 'Copiati dall origine'}")
     print(f"Immobili: {'Selezionati (' + str(len(immobili_da_trasferire_list or [])) + ')' if immobili_da_trasferire_list is not None else 'Tutti'}")


     if _confirm_action("Procedere con la registrazione del passaggio?"):
          # Chiama il manager con comune_dest_id
          if db.registra_passaggio_proprieta(
               partita_origine_id, comune_dest_id, numero_partita_dest, tipo_var, data_variazione,
               tipo_contr, data_contratto, notaio=notaio, repertorio=repertorio,
               nuovi_possessori=nuovi_possessori_list or None, # Passa lista vuota se non specificati ma scelti
               immobili_da_trasferire=immobili_da_trasferire_list, note=note_var
          ):
               print("Passaggio di proprietà registrato con successo.")
          else:
               print("Errore durante la registrazione del passaggio (controllare log).")

# --- Funzioni Invariate rispetto a comune_id ---
def _registra_consultazione_interattivo(db: CatastoDBManager):
     """Guida l'utente nella registrazione di una consultazione."""
     stampa_intestazione("REGISTRA CONSULTAZIONE")
     data_str = input("Data consultazione (YYYY-MM-DD, INVIO per oggi): ").strip()
     richiedente = input("Richiedente: ").strip()
     doc_id = input("Documento Identità (opzionale): ").strip() or None
     motivazione = input("Motivazione (opzionale): ").strip() or None
     materiale = input("Materiale Consultato: ").strip()
     funzionario = input("Funzionario Autorizzante: ").strip()
     if not richiedente or not materiale or not funzionario: print("Richiedente, Materiale e Funzionario obbligatori."); return
     try: data_cons = datetime.strptime(data_str, "%Y-%m-%d").date() if data_str else date.today()
     except ValueError: print("Formato data non valido."); return
     if db.registra_consultazione(data_cons, richiedente, doc_id, motivazione, materiale, funzionario): print("Consultazione registrata.")
     else: print("Errore registrazione consultazione (controllare log).")

def _inserisci_contratto_interattivo(db: CatastoDBManager):
     """Guida l'utente nell'inserimento di un contratto per una variazione esistente."""
     stampa_intestazione("INSERISCI CONTRATTO PER VARIAZIONE")
     var_id_str = input("ID della Variazione a cui collegare il contratto: ").strip()
     if not var_id_str.isdigit(): print("ID Variazione non valido."); return
     var_id = int(var_id_str)
     if not db.execute_query("SELECT 1 FROM variazione WHERE id = %s", (var_id,)) or not db.fetchone(): print(f"Variazione ID {var_id} non trovata."); return
     tipo_contr = input("Tipo Contratto (es. Vendita, Successione): ").strip().capitalize()
     data_contr_str = input("Data Contratto (YYYY-MM-DD): ").strip()
     if not tipo_contr or not data_contr_str: print("Tipo e Data contratto obbligatori."); return
     try: data_contr = datetime.strptime(data_contr_str, "%Y-%m-%d").date()
     except ValueError: print("Formato data non valido."); return
     notaio = input("Notaio (opzionale): ").strip() or None
     repertorio = input("Repertorio (opzionale): ").strip() or None
     note = input("Note Contratto (opzionale): ").strip() or None
     if db.insert_contratto(var_id, tipo_contr, data_contr, notaio, repertorio, note): print(f"Contratto inserito per Variazione ID {var_id}.")
     else: print("Errore inserimento contratto (controllare log - potrebbe esistere già).")

def _duplica_partita_interattivo(db: CatastoDBManager):
     """Guida l'utente nella duplicazione di una partita."""
     stampa_intestazione("DUPLICA PARTITA")
     id_orig_str = input("ID Partita da duplicare: ").strip()
     if not id_orig_str.isdigit(): print("ID non valido."); return
     partita_id_orig = int(id_orig_str)
     partita_orig = db.get_partita_details(partita_id_orig) # Recupera anche comune_nome
     if not partita_orig: print(f"Partita ID {partita_id_orig} non trovata."); return
     print(f"Partita da duplicare: N.{partita_orig['numero_partita']} (Comune: {partita_orig['comune_nome']})")
     nuovo_num_str = input("Nuovo numero per la partita duplicata (nello stesso comune): ").strip()
     if not nuovo_num_str.isdigit(): print("Numero non valido."); return
     nuovo_num = int(nuovo_num_str)
     mant_poss = _confirm_action("Mantenere gli stessi possessori?")
     mant_imm = _confirm_action("Duplicare anche gli immobili associati?")
     if _confirm_action(f"Duplicare Partita ID {partita_id_orig} in N.{nuovo_num}?"):
          if db.duplicate_partita(partita_id_orig, nuovo_num, mant_poss, mant_imm): print("Partita duplicata.")
          else: print("Errore durante la duplicazione (controllare log - es. partita già esistente).")

def _trasferisci_immobile_interattivo(db: CatastoDBManager):
     """Guida l'utente nel trasferimento di un immobile tra partite."""
     stampa_intestazione("TRASFERISCI IMMOBILE")
     imm_id_str = input("ID Immobile da trasferire: ").strip()
     if not imm_id_str.isdigit(): print("ID Immobile non valido."); return
     immobile_id = int(imm_id_str)
     if not db.execute_query("SELECT partita_id FROM immobile WHERE id = %s", (immobile_id,)): print(f"Errore verifica Immobile ID {immobile_id}."); return
     imm_info = db.fetchone()
     if not imm_info: print(f"Immobile ID {immobile_id} non trovato."); return
     print(f"Immobile ID {immobile_id} appartiene a Partita ID {imm_info['partita_id']}")
     part_dest_id_str = input("ID Partita di destinazione: ").strip()
     if not part_dest_id_str.isdigit(): print("ID Partita Destinazione non valido."); return
     partita_dest_id = int(part_dest_id_str)
     if partita_dest_id == imm_info['partita_id']: print("Impossibile trasferire immobile alla stessa partita."); return
     if not db.execute_query("SELECT stato FROM partita WHERE id = %s", (partita_dest_id,)): print(f"Errore verifica Partita Dest. ID {partita_dest_id}."); return
     part_dest = db.fetchone()
     if not part_dest: print(f"Partita Destinazione ID {partita_dest_id} non trovata."); return
     if part_dest['stato'] != 'attiva': print("La partita di destinazione non è attiva."); return
     reg_var = _confirm_action("Registrare una variazione di tipo 'Trasferimento' per questa operazione?")
     if _confirm_action(f"Trasferire Immobile ID {immobile_id} da Partita ID {imm_info['partita_id']} a Partita ID {partita_dest_id}?"):
          if db.transfer_immobile(immobile_id, partita_dest_id, reg_var): print("Immobile trasferito.")
          else: print("Errore durante il trasferimento (controllare log).")

def menu_report(db: CatastoDBManager):
    _set_session_context(db)
    while True:
        stampa_intestazione("GENERAZIONE REPORT")
        print("1. Certificato di proprieta")
        print("2. Report genealogico")
        print("3. Report possessore")
        print("4. Report consultazioni")
        print("5. Statistiche per comune (Vista)")
        print("6. Riepilogo immobili per tipologia (Vista)")
        print("7. Visualizza Partite Complete (Vista)")
        print("8. Cronologia Variazioni (Vista)")
        print("9. Report Annuale Partite per Comune (Funzione)")
        print("10. Report Proprietà Possessore per Periodo (Funzione)")
        print("11. Report Statistico Comune (Funzione)")
        print("0. Torna al menu principale") # Modificato da 12
        scelta = input("\nSeleziona un'opzione (0-11): ").strip() # Modificato da 1-12

        if scelta == "1":
            partita_id_str = input("Inserisci l'ID della partita: ").strip()
            if partita_id_str.isdigit():
                partita_id = int(partita_id_str)
                certificato = db.genera_certificato_proprieta(partita_id)
                if certificato:
                    stampa_intestazione("CERTIFICATO DI PROPRIETA"); print(certificato)
                    filename = f"certificato_partita_{partita_id}_{date.today()}.txt"
                    if _confirm_action(f"Salvare su file '{filename}'?"):
                         try: 
                             with open(filename, 'w', encoding='utf-8') as f: f.write(certificato); print("Certificato salvato.")
                         except Exception as e: print(f"Errore salvataggio: {e}")
                else: print("Nessun dato disponibile o errore generazione.")
            else: print("ID non valido!")
        # ... (Implementare le altre opzioni del menu report in modo simile) ...
        elif scelta == "0": # Modificato da 12
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

def menu_manutenzione(db: CatastoDBManager):
    _set_session_context(db)
    while True:
        stampa_intestazione("MANUTENZIONE DATABASE")
        print("1. Verifica integrita database")
        print("2. Aggiorna Viste Materializzate")
        print("3. Esegui Manutenzione Generale (ANALYZE)")
        print("4. Analizza Query Lente (Richiede pg_stat_statements)")
        print("5. Controlla Frammentazione Indici")
        print("6. Ottieni Suggerimenti Ottimizzazione")
        print("0. Torna al menu principale") # Modificato da 7
        scelta = input("\nSeleziona un'opzione (0-6): ").strip() # Modificato da 1-7

        if scelta == "1":
            stampa_intestazione("VERIFICA INTEGRITA DATABASE"); print("Avvio verifica...")
            # ... (Logica originale verifica integrità) ...
            problemi, messaggio = db.verifica_integrita_database()
            print("\n--- Risultato Verifica ---"); print(messaggio); print("--- Fine Risultato ---")
            if problemi: print("\nATTENZIONE: Rilevati problemi!"); print("(La correzione automatica non è implementata in questo esempio)")
            else: print("\nNessun problema critico rilevato.")
        # ... (Implementare le altre opzioni del menu manutenzione) ...
        elif scelta == "0": # Modificato da 7
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

def menu_audit(db: CatastoDBManager):
    _set_session_context(db)
    while True:
        stampa_intestazione("SISTEMA DI AUDIT")
        print("1. Consulta log di audit")
        print("2. Visualizza cronologia di un record")
        print("3. Genera report di audit")
        print("0. Torna al menu principale") # Modificato da 4
        scelta = input("\nSeleziona un'opzione (0-3): ").strip() # Modificato da 1-4

        if scelta == "1":
            stampa_intestazione("CONSULTA LOG DI AUDIT")
            # ... (Logica originale consultazione log) ...
            tabella = input("Tabella (vuoto per tutte): ").strip() or None; op = input("Operazione (I/U/D, vuoto per tutte): ").strip().upper() or None
            rec_id_str = input("ID Record (vuoto per tutti): ").strip(); app_user_id_str = input("ID Utente App (vuoto per tutti): ").strip()
            session_id_str = input("ID Sessione (vuoto per tutti): ").strip() or None; utente_db_str = input("Utente DB (vuoto per tutti): ").strip() or None
            data_i_str = input("Data inizio (YYYY-MM-DD, vuoto): ").strip(); data_f_str = input("Data fine (YYYY-MM-DD, vuoto): ").strip()
            rec_id = int(rec_id_str) if rec_id_str.isdigit() else None; app_user_id_audit = int(app_user_id_str) if app_user_id_str.isdigit() else None # Rinominato
            data_inizio, data_fine = None, None
            try:
                if data_i_str: data_inizio = datetime.strptime(data_i_str, "%Y-%m-%d").date()
                if data_f_str: data_fine = datetime.strptime(data_f_str, "%Y-%m-%d").date()
            except ValueError: print("Formato data non valido."); input("\nPremi INVIO per continuare..."); continue
            logs = db.get_audit_log(tabella, op, rec_id, data_inizio, data_fine, utente_db_str, app_user_id_audit, session_id_str) # Usato utente_db_str
            stampa_intestazione(f"RISULTATI LOG AUDIT ({len(logs)})")
            if not logs: print("Nessun log trovato.")
            else:
                op_map = {"I": "Ins", "U": "Upd", "D": "Del"}
                for log_item in logs: # Rinominato
                    user_info = f"DB:{log_item.get('db_user', '?')}" + (f" App:{log_item.get('app_user_id')}({log_item.get('app_username', '?')})" if log_item.get('app_user_id') is not None else " App:N/A")
                    print(f"ID:{log_item['audit_id']} {log_item['timestamp']:%y-%m-%d %H:%M} {op_map.get(log_item['operazione'],'?')} "
                          f"T:{log_item['tabella']} R:{log_item.get('record_id','N/A')} {user_info} S:{log_item.get('session_id','-')[:8]} IP:{log_item.get('ip_address','-')}")
                    print("-" * 40)
        # ... (Implementare le altre opzioni del menu audit) ...
        elif scelta == "0": # Modificato da 4
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

def menu_backup(db: CatastoDBManager):
    _set_session_context(db)
    while True:
        stampa_intestazione("SISTEMA DI BACKUP E RESTORE")
        print("NOTA BENE: I comandi backup/restore vanno eseguiti manualmente nella shell.")
        print("1. Ottieni comando per Backup")
        print("2. Visualizza Log Backup Recenti")
        print("3. Ottieni comando per Restore (da ID Log)")
        print("4. Registra manualmente un Backup eseguito")
        print("5. Genera Script Bash per Backup Automatico")
        print("6. Pulisci Log Backup vecchi")
        print("0. Torna al menu principale") # Modificato da 7
        scelta = input("\nSeleziona un'opzione (0-6): ").strip() # Modificato da 1-7

        if scelta == "1":
            stampa_intestazione("OTTIENI COMANDO BACKUP")
            # ... (Logica originale comando backup) ...
            print("Tipi: completo, schema, dati"); tipo = input("Tipo (default: completo): ").strip() or 'completo'
            if tipo not in ['completo', 'schema', 'dati']: print("Tipo non valido."); input("\nPremi INVIO per continuare..."); continue
            cmd = db.get_backup_command_suggestion(tipo=tipo)
            if cmd: print("\n--- Comando Suggerito (eseguire in shell) ---\n", cmd, "\n" + "-"*55)
            else: print("Errore generazione comando.")
        # ... (Implementare le altre opzioni del menu backup) ...
        elif scelta == "0": # Modificato da 7
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

def menu_storico_avanzato(db: CatastoDBManager):
    _set_session_context(db)
    while True:
        stampa_intestazione("FUNZIONALITÀ STORICHE AVANZATE")
        print("1. Visualizza Periodi Storici")
        print("2. Ottieni Nome Storico Entità per Anno")
        print("3. Registra Nome Storico Entità")
        print("4. Ricerca Documenti Storici")
        print("5. Visualizza Albero Genealogico Proprietà")
        print("6. Statistiche Catastali per Periodo")
        print("7. Collega Documento a Partita")
        print("0. Torna al menu principale") # Modificato da 8
        scelta = input("\nSeleziona un'opzione (0-7): ").strip() # Modificato da 1-8

        if scelta == "1":
            stampa_intestazione("PERIODI STORICI")
            # ... (Logica originale visualizza periodi) ...
            periodi = db.get_historical_periods()
            if periodi: [print(f"ID:{p['id']} {p['nome']} ({p['anno_inizio']}-{p.get('anno_fine') or 'oggi'}) Desc: {p.get('descrizione') or '-'}") for p in periodi]
            else: print("Nessun periodo storico trovato.")
        # ... (Implementare le altre opzioni del menu storico) ...
        elif scelta == "0": # Modificato da 8
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")


# --- Menu Utenti e Sessione (MODIFICATO: Rimosso Login, aggiornato per tornare False su Logout) ---
def menu_utenti(db: CatastoDBManager) -> bool: # Aggiunto tipo di ritorno
    """Menu per la gestione degli utenti e logout. Ritorna False se l'utente fa logout, True altrimenti."""
    # _set_session_context(db) # Già chiamato da menu_principale prima di entrare qui

    global logged_in_user_id, logged_in_user_info, current_session_id # Dichiarazione global all'inizio


    while True:
        stampa_intestazione("GESTIONE UTENTI E SESSIONE")
        if logged_in_user_id and logged_in_user_info:
            user_display = logged_in_user_info.get('nome_completo') or logged_in_user_info.get('username', 'N/D')
            print(f"--- Utente Attivo: {user_display} (ID: {logged_in_user_id}, Sessione: {current_session_id[:8]}...) ---")
        else:
            print("--- ERRORE: Nessun utente connesso ---") # Non dovrebbe accadere
            return False # Forza uscita se si arriva qui in uno stato anomalo

        print("1. Crea nuovo utente (richiede privilegi admin)")
        print("2. Logout Utente")
        print("3. Verifica Permesso Utente")
        print("4. Elenca Utenti Registrati")
        print("0. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (0-4): ").strip()

        if scelta == "1":
            stampa_intestazione("CREA NUOVO UTENTE")
            username_new = input("Username: ").strip() # Rinominato per evitare conflitti
            password_new = getpass.getpass("Password: ")
            password_confirm = getpass.getpass("Conferma Password: ")
            if not password_new: print("Password obbligatoria."); input("\nPremi INVIO per continuare..."); continue
            if password_new != password_confirm: print("Le password non coincidono."); input("\nPremi INVIO per continuare..."); continue
            nome_completo_new = input("Nome completo: ").strip()
            email_new = input("Email: ").strip()
            print("Ruoli disponibili: admin, archivista, consultatore")
            ruolo_new = input("Ruolo: ").strip().lower()
            if not all([username_new, nome_completo_new, email_new, ruolo_new]): print("Tutti i campi sono obbligatori."); input("\nPremi INVIO per continuare..."); continue
            if ruolo_new not in ['admin', 'archivista', 'consultatore']: print("Ruolo non valido."); input("\nPremi INVIO per continuare..."); continue
            try:
                password_hash = _hash_password(password_new)
                logger.debug(f"Hash generato per {username_new}")
            except Exception as hash_err:
                logger.error(f"Errore hashing password per {username_new}: {hash_err}"); print("Errore tecnico hashing."); input("\nPremi INVIO per continuare..."); continue
            if db.create_user(username_new, password_hash, nome_completo_new, email_new, ruolo_new):
                print(f"Utente '{username_new}' creato.")
            else:
                print(f"Errore creazione utente '{username_new}' (controllare log).")
        elif scelta == "2":
             stampa_intestazione("LOGOUT UTENTE")
             user_display_logout = "N/D"
             if logged_in_user_info:
                 user_display_logout = logged_in_user_info.get('nome_completo') or logged_in_user_info.get('username', 'N/D')
             print(f"Disconnessione utente: {user_display_logout} (ID: {logged_in_user_id})...")
             if db.logout_user(logged_in_user_id, current_session_id, client_ip_address):
                 print("Logout eseguito con successo.")
             else:
                 print("Errore durante la registrazione del logout (controllare log).")
             logged_in_user_id = None
             logged_in_user_info = None
             current_session_id = None
             db.clear_session_app_user()
             print("Verrai reindirizzato alla schermata di login.")
             input("\nPremi INVIO per continuare...") # Attende prima di tornare al ciclo di login
             return False # Segnala logout
        elif scelta == "3":
             stampa_intestazione("VERIFICA PERMESSO UTENTE")
             utente_id_str = input(f"ID Utente (INVIO per utente corrente: {logged_in_user_id if logged_in_user_id else 'N/A'}): ").strip()
             utente_id_to_check = None
             if utente_id_str.isdigit():
                 try: utente_id_to_check = int(utente_id_str)
                 except ValueError: print("ID utente non valido."); input("\nPremi INVIO per continuare..."); continue
             elif logged_in_user_id: utente_id_to_check = logged_in_user_id
             else: print("Nessun utente corrente e ID non specificato."); input("\nPremi INVIO per continuare..."); continue
             permesso_check = input("Nome del permesso (es. 'modifica_partite'): ").strip() # Rinominato
             if not permesso_check: print("Nome permesso obbligatorio."); input("\nPremi INVIO per continuare..."); continue
             if utente_id_to_check is not None:
                 try:
                     ha_permesso = db.check_permission(utente_id_to_check, permesso_check)
                     if ha_permesso: print(f"Utente ID {utente_id_to_check} HA il permesso '{permesso_check}'.")
                     else: print(f"Utente ID {utente_id_to_check} NON HA il permesso '{permesso_check}' o errore.")
                 except Exception as perm_err: logger.error(f"Errore verifica permesso '{permesso_check}' user ID {utente_id_to_check}: {perm_err}"); print("Errore verifica permesso.")
        elif scelta == "4":
            stampa_intestazione("ELENCO UTENTI REGISTRATI")
            filtro_attivi_str = input("Vuoi visualizzare solo gli utenti attivi? (s/n, INVIO per tutti): ").strip().lower()
            solo_attivi_filter = None
            if filtro_attivi_str == 's': solo_attivi_filter = True
            elif filtro_attivi_str == 'n': solo_attivi_filter = False
            utenti_list = db.get_utenti(solo_attivi=solo_attivi_filter) # Rinominato
            if utenti_list:
                print(f"\n--- Trovati {len(utenti_list)} utenti ---"); print("-" * 80)
                print(f"{'ID':<5} | {'Username':<20} | {'Nome Completo':<25} | {'Ruolo':<12} | {'Stato':<8} | {'Ultimo Accesso'}"); print("-" * 80)
                for utente_item in utenti_list:
                    stato_utente = "Attivo" if utente_item['attivo'] else "Non Attivo" # Rinominato
                    ultimo_accesso_str = utente_item['ultimo_accesso'].strftime('%Y-%m-%d %H:%M:%S') if utente_item['ultimo_accesso'] else "Mai"
                    print(f"{utente_item['id']:<5} | {utente_item['username']:<20} | {utente_item['nome_completo']:<25} | {utente_item['ruolo']:<12} | {stato_utente:<8} | {ultimo_accesso_str}")
                print("-" * 80)
            else: print("Nessun utente trovato con i criteri specificati.")
        elif scelta == "0":
            break # Esce dal loop di menu_utenti
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")
    return True # Ritorna True se l'utente non ha fatto logout esplicito da questo menu

# --- Menu Principale (MODIFICATO per gestire stato login da menu_utenti) ---
def menu_principale(db: CatastoDBManager):
    """Menu principale dell'applicazione."""
    global logged_in_user_id, logged_in_user_info, current_session_id 

    utente_ancora_loggato = True
    while utente_ancora_loggato:
        stampa_intestazione("MENU PRINCIPALE")
        if logged_in_user_id and logged_in_user_info:
            user_display = logged_in_user_info.get('nome_completo') or logged_in_user_info.get('username', 'N/D')
            print(f"--- Utente connesso: {user_display} (ID: {logged_in_user_id}, Sessione: {current_session_id[:8]}...) ---")
        else:
            print("--- ERRORE: Sessione utente non valida. Riprovare il login. ---")
            return # Esce da menu_principale, forzerà re-login in main()

        print("1. Consultazione dati")
        print("2. Inserimento e gestione dati")
        print("3. Generazione report")
        print("4. Manutenzione database")
        print("5. Sistema di audit")
        print("6. Gestione Utenti e Sessione")
        print("7. Sistema di Backup")
        print("8. Funzionalità Storiche Avanzate")
        print("9. Esci (Logout e chiusura programma)")
        scelta = input("\nSeleziona un'opzione (1-9): ").strip()
        
        # _set_session_context(db) # Ora chiamato all'inizio di ogni sottomenu

        if scelta == "1": menu_consultazione(db)
        elif scelta == "2": menu_inserimento(db)
        elif scelta == "3": menu_report(db)
        elif scelta == "4": menu_manutenzione(db)
        elif scelta == "5": menu_audit(db)
        elif scelta == "6":
            utente_ancora_loggato = menu_utenti(db) # menu_utenti ora restituisce False se l'utente fa logout
            # Se utente_ancora_loggato è False, il loop while di menu_principale terminerà naturalmente
        elif scelta == "7": menu_backup(db)
        elif scelta == "8": menu_storico_avanzato(db)
        elif scelta == "9":
            print("Uscita dal programma richiesta...")
            # global logged_in_user_id # Per poterla modificare
            # Il logout effettivo con db.logout_user avverrà nel finally di main,
            # ma resettiamo l'ID qui per segnalare a main la volontà di uscire.
            logged_in_user_id = None # Segnala che la sessione è da considerarsi terminata
            utente_ancora_loggato = False 
            break # Esce dal loop di menu_principale


# --- Funzione Main (MODIFICATA per login all'avvio) ---
def main():
    db_config = {
        "dbname": "catasto_storico", "user": "postgres", "password": "Markus74",
        "host": "localhost", "port": 5432, "schema": "catasto"
    }
    stampa_locandina_introduzione()
    db = CatastoDBManager(**db_config)

    if not db.connect():
        print("ERRORE CRITICO: Impossibile connettersi al database. Verifica i parametri e lo stato del server.")
        sys.exit(1)

    global logged_in_user_id, logged_in_user_info, current_session_id

    try:
        while True:
            logged_in_user_id = None # Resetta stato login ad ogni iterazione del loop principale
            logged_in_user_info = None
            current_session_id = None
            db.clear_session_app_user()

            if not esegui_login(db):
                print("Login fallito o annullato. Uscita dal programma.")
                break 

            menu_principale(db) # Entra nel menu principale dopo login riuscito

            # Se menu_principale esce, significa che l'utente ha scelto "Esci" (opzione 9)
            # o ha fatto logout da menu_utenti. In entrambi i casi, logged_in_user_id sarà None
            # o menu_principale avrà terminato il suo loop (se utente_ancora_loggato è diventato False).
            
            if not logged_in_user_id: # Controlla se c'è stato un logout
                print("\nSessione utente terminata.")
                rilog_choice = input("Vuoi effettuare un altro login? (s/n): ").strip().lower()
                if rilog_choice != 's':
                    break # Esce dal loop while True e termina il programma
                # Altrimenti, il loop ricomincia e chiama esegui_login()
            else:
                # Se si arriva qui con utente ancora loggato, significa che menu_principale
                # è uscito per un motivo non gestito come logout o uscita esplicita.
                # Per sicurezza e per evitare loop infiniti, usciamo.
                logger.info("Uscita inattesa da menu_principale con utente ancora loggato. Terminazione.")
                break

    except KeyboardInterrupt:
        print("\nOperazione interrotta dall'utente.")
    except Exception as e:
        logger.exception(f"Errore non gestito nel programma: {e}")
        print(f"ERRORE IMPREVISTO: {e}")
    finally:
        print("\nBlocco Finally in esecuzione...")
        if logged_in_user_id and current_session_id and db.is_connected(): # Usa un metodo per verificare la connessione
             print(f"Esecuzione logout di sicurezza per utente ID: {logged_in_user_id}...")
             db.logout_user(logged_in_user_id, current_session_id, client_ip_address)
        
        logged_in_user_id = None
        logged_in_user_info = None
        current_session_id = None
        
        if db:
            db.disconnect()
        print("Applicazione terminata.")

# --- Avvio Script ---
if __name__ == "__main__":
    main()