#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Esempio di utilizzo del gestore database catastale (MODIFICATO per comune.id PK e bcrypt)
======================================================================================
Questo script mostra esempi pratici di come utilizzare
la classe CatastoDBManager per interagire con il database,
includendo gestione utenti e audit.

Autore: Marco Santoro
Data: 29/04/2025 (Versione completa e aggiornata 1.4)
"""

# Assicurati che catasto_db_manager sia la versione aggiornata per comune_id
from catasto_db_manager import CatastoDBManager
from datetime import date, datetime
import json
import os
import sys
import hashlib # Non più usato per password, ma potrebbe servire per altro
import getpass # Per nascondere input password
import logging # Per logging
import bcrypt  # Per hashing sicuro password
from typing import Optional, List, Dict, Any # Per type hinting

# --- Configurazione Logging ---
# Configura il logging se non già fatto a livello globale
logging.basicConfig(
    level=logging.INFO, # O DEBUG per maggiori dettagli
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("python_example.log"), # Log separato per l'esempio
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Variabili Globali per Sessione Utente (SEMPLIFICATE) ---
# In un'app reale, usare meccanismi di sessione più robusti
logged_in_user_id: Optional[int] = None
current_session_id: Optional[str] = None
# Simula IP client, da ottenere dinamicamente in un'app reale (es. da richiesta web)
client_ip_address: str = "127.0.0.1"

# --- Funzioni Helper per Interfaccia Utente ---

def stampa_locandina_introduzione():
    """Stampa una locandina di introduzione testuale."""
    larghezza = 80
    oggi = date.today().strftime("%d/%m/%Y")
    versione = "1.4" # Versione aggiornata
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

# --- NUOVA Funzione Helper per Selezionare Comune ---
def _seleziona_comune(db: CatastoDBManager, prompt: str = "Seleziona il comune:") -> Optional[int]:
    """
    Mostra l'elenco dei comuni e chiede all'utente di selezionarne uno.
    Ritorna l'ID del comune selezionato o None se la selezione non è valida o annullata.
    """
    comuni = db.get_comuni() # Ottiene lista con ID e nome
    if not comuni:
        print("\nERRORE: Nessun comune trovato nel database. Aggiungere prima un comune.")
        return None

    print(f"\n{prompt}")
    for i, c in enumerate(comuni, 1):
        # Mostra ID e Nome per la selezione
        print(f"{i}. {c['nome']} (ID: {c['id']})")
    print("0. Annulla")

    while True:
        scelta = input(f"Inserisci il numero (1-{len(comuni)}) o 0 per annullare: ").strip()
        if scelta == '0':
            return None # Annullato dall'utente
        if scelta.isdigit():
            try:
                scelta_int = int(scelta)
                if 1 <= scelta_int <= len(comuni):
                    comune_selezionato = comuni[scelta_int - 1]
                    print(f"--> Comune selezionato: {comune_selezionato['nome']} (ID: {comune_selezionato['id']})")
                    return comune_selezionato['id'] # Ritorna l'ID
                else:
                    print("Selezione fuori range. Riprova.")
            except ValueError:
                 print("Input numerico non valido. Riprova.")
        else:
            print("Input non numerico. Riprova.")


# --- Funzioni di Inserimento Dati (MODIFICATE per comune_id) ---

def inserisci_possessore(db: CatastoDBManager) -> Optional[int]:
    """Funzione interattiva per inserire un nuovo possessore (usa _seleziona_comune)."""
    _set_session_context(db)
    stampa_intestazione("AGGIUNGI NUOVO POSSESSORE")

    # Seleziona il comune usando la nuova funzione helper
    comune_id_selezionato = _seleziona_comune(db)
    if comune_id_selezionato is None:
        print("Operazione annullata.")
        return None

    # Ottieni altri dati
    cognome_nome = input("Cognome e nome: ").strip()
    paternita = input("Paternita (es. 'fu Roberto'): ").strip()
    # Calcola nome completo
    nome_completo = f"{cognome_nome} {paternita}".strip()
    # Chiedi conferma o modifica
    conferma = input(f"Nome completo calcolato: [{nome_completo}]\nPremi INVIO per confermare o inserisci valore diverso: ").strip()
    if conferma:
        nome_completo = conferma

    if cognome_nome and nome_completo:
        # Chiama il metodo del manager con l'ID del comune
        possessore_id = db.insert_possessore(comune_id_selezionato, cognome_nome, paternita, nome_completo, True)
        if possessore_id:
            print(f"Possessore '{nome_completo}' inserito con successo (ID: {possessore_id})")
            return possessore_id
        else:
            # L'errore specifico dovrebbe essere loggato dal manager
            print("Errore durante l'inserimento del possessore (controllare log).")
    else:
        print("Dati incompleti (Cognome/Nome o Nome Completo mancanti), operazione annullata.")
    return None

def inserisci_localita(db: CatastoDBManager) -> Optional[int]:
    """Funzione interattiva per inserire una nuova località (usa _seleziona_comune)."""
    _set_session_context(db)
    stampa_intestazione("AGGIUNGI NUOVA LOCALITA")

    # Seleziona il comune
    comune_id_selezionato = _seleziona_comune(db)
    if comune_id_selezionato is None:
        print("Operazione annullata.")
        return None

    # Ottieni altri dati
    nome = input("Nome localita: ").strip()
    if not nome:
        print("Nome località obbligatorio. Operazione annullata.")
        return None

    print("\nSeleziona il tipo di localita:")
    print("1. Regione")
    print("2. Via")
    print("3. Borgata")
    tipo_scelta = input("Scegli un'opzione (1-3): ").strip()
    tipo_map = {"1": "regione", "2": "via", "3": "borgata"}
    if tipo_scelta not in tipo_map:
        print("Scelta tipo non valida.")
        return None
    tipo = tipo_map[tipo_scelta]

    civico = None
    if tipo == "via":
        civico_input = input("Numero civico (opzionale, solo numero): ").strip()
        if civico_input.isdigit():
            civico = int(civico_input)

    # Chiama il manager con l'ID del comune
    # insert_localita nel manager gestisce ON CONFLICT e ritorna l'ID esistente o nuovo
    localita_id = db.insert_localita(comune_id_selezionato, nome, tipo, civico)
    if localita_id:
        print(f"Localita '{nome}' ({tipo}) inserita/trovata con ID: {localita_id}")
        return localita_id
    else:
        print("Errore durante l'inserimento/recupero della localita (controllare log).")
        return None

def aggiungi_comune(db: CatastoDBManager):
    """Funzione interattiva per inserire un nuovo comune."""
    # Questa funzione ora inserisce solo il comune. L'associazione al periodo storico
    # è stata rimossa da qui, andrebbe gestita separatamente se necessaria.
    _set_session_context(db)
    stampa_intestazione("AGGIUNGI NUOVO COMUNE")
    nome = input("Nome comune: ").strip()
    provincia = input("Provincia: ").strip()
    regione = input("Regione: ").strip()

    if not (nome and provincia and regione):
        print("Dati incompleti (Nome, Provincia, Regione obbligatori), operazione annullata")
        return

    # La gestione ON CONFLICT è fatta nel DB (su comune.nome)
    query = "INSERT INTO comune (nome, provincia, regione) VALUES (%s, %s, %s) ON CONFLICT (nome) DO NOTHING"
    try:
        if db.execute_query(query, (nome, provincia, regione)):
            # Verifica se l'inserimento ha avuto effetto o se esisteva già
            if db.execute_query("SELECT 1 FROM comune WHERE nome = %s", (nome,)) and db.fetchone():
                db.commit() # Commit solo se la query è andata a buon fine (anche se DO NOTHING)
                print(f"Comune '{nome}' inserito o già esistente.")
            else:
                # Questo caso non dovrebbe verificarsi se la execute_query ha successo
                print(f"Errore imprevisto: Comune '{nome}' non trovato dopo INSERT/ON CONFLICT.")
                db.rollback() # Rollback per sicurezza
        else:
            # Errore nella execute_query (già loggato e rollback fatto)
            print("Errore durante l'esecuzione della query di inserimento del comune.")
    except psycopg2.Error as db_err:
        # Errore specifico del DB (es. violazione constraint non gestita da ON CONFLICT)
        print(f"Errore database durante l'inserimento del comune: {db_err}")
        # Rollback già fatto in execute_query
    except Exception as e:
        logger.error(f"Errore Python in aggiungi_comune: {e}")
        print(f"Errore imprevisto durante l'inserimento del comune: {e}")
        db.rollback() # Rollback per sicurezza


# --- Esportazione JSON (invariata nella logica Python, assume funzioni SQL aggiornate) ---
def _esporta_entita_json(db: CatastoDBManager, tipo_entita: str, etichetta_id: str, nome_file_prefix: str):
    """Funzione generica per esportare un'entità in formato JSON."""
    stampa_intestazione(f"ESPORTA {tipo_entita.upper()} IN JSON")
    id_entita_str = input(f"{etichetta_id} da esportare: ").strip()
    if not id_entita_str.isdigit(): print("ID non valido."); return
    entita_id = int(id_entita_str)
    json_data_str = None
    try:
        if tipo_entita == 'partita': json_data_str = db.export_partita_json(entita_id)
        elif tipo_entita == 'possessore': json_data_str = db.export_possessore_json(entita_id)
        else: print(f"Tipo entità '{tipo_entita}' non supportato."); return

        if json_data_str:
            print(f"\n--- DATI JSON {tipo_entita.upper()} ---"); print(json_data_str); print("-" * (len(tipo_entita) + 16))
            filename = f"{nome_file_prefix}_{entita_id}.json"
            if _confirm_action(f"Salvare in '{filename}'"):
                try:
                    with open(filename, 'w', encoding='utf-8') as f: f.write(json_data_str)
                    print(f"Dati salvati in {filename}")
                except Exception as e: print(f"Errore nel salvataggio del file: {e}")
        else: print(f"{tipo_entita.capitalize()} non trovato/a o errore esportazione (controllare log).")
    except Exception as e: print(f"Si è verificato un errore durante l'esportazione: {e}")


# --- Menu Principale (invariato nella struttura) ---
def menu_principale(db: CatastoDBManager):
    """Menu principale dell'applicazione."""
    global logged_in_user_id, current_session_id
    while True:
        stampa_intestazione("MENU PRINCIPALE")
        if logged_in_user_id: print(f"--- Utente connesso: ID {logged_in_user_id} (Sessione: {current_session_id[:8]}...) ---")
        else: print("--- Nessun utente connesso ---")
        print("1. Consultazione dati"); print("2. Inserimento e gestione dati"); print("3. Generazione report")
        print("4. Manutenzione database"); print("5. Sistema di audit"); print("6. Gestione Utenti e Sessione")
        print("7. Sistema di Backup"); print("8. Funzionalità Storiche Avanzate"); print("9. Esci")
        scelta = input("\nSeleziona un'opzione (1-9): ").strip()
        _set_session_context(db) # Imposta contesto PRIMA di entrare nei sottomenu
        if scelta == "1": menu_consultazione(db)
        elif scelta == "2": menu_inserimento(db)
        elif scelta == "3": menu_report(db)
        elif scelta == "4": menu_manutenzione(db)
        elif scelta == "5": menu_audit(db)
        elif scelta == "6": menu_utenti(db)
        elif scelta == "7": menu_backup(db)
        elif scelta == "8": menu_storico_avanzato(db)
        elif scelta == "9":
            if logged_in_user_id and current_session_id:
                 print("Logout automatico prima dell'uscita..."); db.logout_user(logged_in_user_id, current_session_id, client_ip_address)
                 logged_in_user_id = None; current_session_id = None
            break
        else: print("Opzione non valida!")

# --- Menu Consultazione (MODIFICATO per comune_id) ---
def menu_consultazione(db: CatastoDBManager):
    """Menu per operazioni di consultazione dati."""
    while True:
        stampa_intestazione("CONSULTAZIONE DATI")
        print("1. Elenco comuni"); print("2. Elenco partite per comune"); print("3. Elenco possessori per comune")
        print("4. Ricerca partite (Semplice)"); print("5. Dettagli partita"); print("6. Elenco localita per comune")
        print("7. Ricerca Avanzata Possessori (Similarità)"); print("8. Ricerca Avanzata Immobili")
        print("9. Cerca Immobili Specifici"); print("10. Cerca Variazioni"); print("11. Cerca Consultazioni")
        print("12. Esporta Partita in JSON"); print("13. Esporta Possessore in JSON"); print("14. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-14): ").strip()

        if scelta == "1": # Elenco comuni (mostra anche ID)
            search_term = input("Termine di ricerca nome comune (lascia vuoto per tutti): ").strip()
            comuni = db.get_comuni(search_term or None)
            stampa_intestazione(f"COMUNI TROVATI ({len(comuni)})")
            if comuni:
                # Mostra ID accanto al nome
                for c in comuni: print(f"- ID: {c['id']} Nome: {c['nome']} ({c['provincia']}, {c['regione']})")
            else: print("Nessun comune trovato.")

        elif scelta == "2": # Elenco partite per comune (usa _seleziona_comune)
            comune_id = _seleziona_comune(db, "Seleziona il comune per visualizzare le partite:")
            if comune_id is not None:
                partite = db.get_partite_by_comune(comune_id) # Passa ID
                # Il manager ritorna comune_nome grazie al JOIN
                comune_nome_display = partite[0]['comune_nome'] if partite else "N/D"
                stampa_intestazione(f"PARTITE DI {comune_nome_display.upper()} ({len(partite)})")
                if partite:
                    for p in partite:
                        stato = p['stato'].upper()
                        possessori_str = p.get('possessori', 'N/D') or 'Nessuno'
                        print(f"ID: {p['id']} - N.{p['numero_partita']} ({p['tipo']}) - Stato: {stato}")
                        print(f"  Possessori: {possessori_str}")
                        print(f"  Num. Immobili: {p.get('num_immobili', 0)}")
                        print("-" * 20)
                else: print("Nessuna partita trovata.")
            # else: implicitamente non fa nulla se la selezione è annullata

        elif scelta == "3": # Elenco possessori per comune (usa _seleziona_comune)
            comune_id = _seleziona_comune(db, "Seleziona il comune per visualizzare i possessori:")
            if comune_id is not None:
                possessori = db.get_possessori_by_comune(comune_id) # Passa ID
                comune_nome_display = possessori[0]['comune_nome'] if possessori else "N/D"
                stampa_intestazione(f"POSSESSORI DI {comune_nome_display.upper()} ({len(possessori)})")
                if possessori:
                    for p in possessori:
                        stato = "Attivo" if p.get('attivo') else "Non Attivo"
                        print(f"ID: {p['id']} - {p['nome_completo']} - Stato: {stato}")
                else: print("Nessun possessore trovato.")
            # else: implicitamente non fa nulla

        elif scelta == "4": # Ricerca partite (usa _seleziona_comune opzionale)
            stampa_intestazione("RICERCA PARTITE (SEMPLICE)")
            comune_id = None
            if _confirm_action("Filtrare per comune?"):
                 comune_id = _seleziona_comune(db, "Seleziona il comune per cui filtrare:")
                 if comune_id is None: print("Filtro comune annullato."); # Continua senza filtro comune o annulla? Decidiamo di continuare senza.

            numero_str = input("Numero partita (esatto, opzionale): ").strip()
            possessore = input("Nome possessore (anche parziale, opzionale): ").strip()
            natura = input("Natura immobile (anche parziale, opzionale): ").strip()
            numero_partita = int(numero_str) if numero_str.isdigit() else None

            partite = db.search_partite( # Passa comune_id
                comune_id=comune_id,
                numero_partita=numero_partita,
                possessore=possessore or None,
                immobile_natura=natura or None
            )
            stampa_intestazione(f"RISULTATI RICERCA PARTITE ({len(partite)})")
            if partite:
                for p in partite: # search_partite ritorna comune_nome
                    print(f"ID: {p['id']} - {p['comune_nome']} - Partita N.{p['numero_partita']} ({p['tipo']}) - Stato: {p['stato']}")
            else: print("Nessuna partita trovata con questi criteri.")

        elif scelta == "5": # Dettagli partita (invariato, manager fa JOIN)
            id_partita_str = input("ID della partita per dettagli: ").strip()
            if id_partita_str.isdigit():
                partita_id_int = int(id_partita_str)
                partita = db.get_partita_details(partita_id_int)
                if partita:
                    # Il metodo get_partita_details è stato aggiornato per includere comune_nome
                    stampa_intestazione(f"DETTAGLI PARTITA N.{partita['numero_partita']} (Comune: {partita['comune_nome']})")
                    print(f"ID: {partita['id']} - Tipo: {partita['tipo']} - Stato: {partita['stato']}")
                    print(f"Data Impianto: {partita['data_impianto']} - Data Chiusura: {partita.get('data_chiusura') or 'N/D'}")
                    print("\nPOSSESSORI:")
                    if partita.get('possessori'):
                        for pos in partita['possessori']: print(f"- ID:{pos['id']} {pos['nome_completo']}{f' (Quota: {pos.get('quota')})' if pos.get('quota') else ''}")
                    else: print("  Nessuno")
                    print("\nIMMOBILI:")
                    if partita.get('immobili'):
                        for imm in partita['immobili']:
                            loc_str = f"{imm['localita_nome']}{f', {imm['civico']}' if imm.get('civico') else ''} ({imm['localita_tipo']})"
                            print(f"- ID:{imm['id']} {imm['natura']} in {loc_str}")
                            print(f"  Class: {imm.get('classificazione') or 'N/D'} - Cons: {imm.get('consistenza') or 'N/D'} - Piani: {imm.get('numero_piani') or 'N/D'} - Vani: {imm.get('numero_vani') or 'N/D'}")
                    else: print("  Nessuno")
                    print("\nVARIAZIONI:")
                    if partita.get('variazioni'):
                        for var in partita['variazioni']:
                             dest_partita_str = f" -> Partita Dest. ID {var.get('partita_destinazione_id')}" if var.get('partita_destinazione_id') else ""
                             print(f"- ID:{var['id']} Tipo:{var['tipo']} Data:{var['data_variazione']}{dest_partita_str}")
                             if var.get('tipo_contratto'): print(f"  Contratto: {var['tipo_contratto']} del {var['data_contratto']} (Notaio: {var.get('notaio') or 'N/D'}, Rep: {var.get('repertorio') or 'N/D'})")
                             if var.get('contratto_note'): print(f"  Note Contratto: {var['contratto_note']}") # Corretto nome chiave? Verifica get_partita_details
                    else: print("  Nessuna")
                else: print(f"Partita con ID {partita_id_int} non trovata.")
            else: print("ID partita non valido.")

        elif scelta == "6": # Elenco località per comune (usa _seleziona_comune)
             comune_id = _seleziona_comune(db, "Seleziona il comune per visualizzare le località:")
             if comune_id is not None:
                 # Trova il nome del comune per il titolo
                 comune_info = next((c for c in db.get_comuni() if c['id'] == comune_id), {'nome': 'N/D'})
                 comune_nome_display = comune_info['nome']

                 # Query diretta (o creare metodo dedicato nel manager)
                 query = "SELECT id, nome, tipo, civico FROM localita WHERE comune_id = %s ORDER BY tipo, nome, civico"
                 if db.execute_query(query, (comune_id,)):
                      localita = db.fetchall()
                      stampa_intestazione(f"LOCALITÀ DI {comune_nome_display.upper()} ({len(localita)})")
                      if localita:
                           for loc in localita: print(f"ID: {loc['id']} - {loc['nome']} ({loc['tipo']}){f', civico {loc['civico']}' if loc['civico'] is not None else ''}")
                      else: print("Nessuna località trovata.")
                 else: print("Errore nella ricerca delle località.")
             # else: selezione annullata

        elif scelta == "7": # Ricerca Avanzata Possessori (invariato, SQL fa JOIN)
             stampa_intestazione("RICERCA AVANZATA POSSESSORI (Similarità)")
             query_text = input("Termine di ricerca (nome/cognome/paternità): ").strip()
             if query_text:
                  # Assumiamo che ricerca_avanzata_possessori ritorni comune_nome
                  results = db.ricerca_avanzata_possessori(query_text)
                  if results:
                       print(f"\nTrovati {len(results)} risultati (ordinati per similarità):")
                       for r in results:
                            sim_perc = round(r.get('similarity', 0) * 100, 1)
                            print(f"- ID: {r['id']} {r['nome_completo']} (Comune: {r.get('comune_nome', '?')})") # Mostra nome comune
                            print(f"  Similarità: {sim_perc}% - Partite: {r.get('num_partite', 0)}")
                  else: print("Nessun risultato trovato.")
             else: print("Termine di ricerca obbligatorio.")

        elif scelta == "8": # Ricerca Avanzata Immobili (usa _seleziona_comune opzionale)
             stampa_intestazione("RICERCA AVANZATA IMMOBILI")
             comune_id = None
             if _confirm_action("Filtrare per comune?"):
                 comune_id = _seleziona_comune(db, "Seleziona il comune per cui filtrare:")
                 if comune_id is None: print("Filtro comune annullato.")

             natura = input("Natura Immobile (parziale, vuoto per tutti): ").strip() or None
             localita_nome = input("Nome Località (parziale, vuoto per tutti): ").strip() or None # Ricerca su nome
             classif = input("Classificazione (esatta, vuoto per tutti): ").strip() or None
             possessore_nome = input("Nome Possessore (parziale, vuoto per tutti): ").strip() or None # Ricerca su nome

             # Il metodo del manager accetta comune_id
             # Assumiamo che la funzione SQL sottostante sia aggiornata per usare comune_id e restituire nome comune
             results = db.ricerca_avanzata_immobili(comune_id, natura, localita_nome, classif, possessore_nome)
             if results:
                  print(f"\nTrovati {len(results)} immobili:")
                  for r in results:
                       # Assumiamo che il metodo/SQL ritorni comune_nome
                       print(f"- Imm.ID: {r['immobile_id']} - {r['natura']} in {r['localita_nome']} (Comune: {r.get('comune_nome','?')})")
                       print(f"  Partita N.{r['partita_numero']} - Class: {r.get('classificazione') or 'N/D'}")
                       print(f"  Possessori: {r.get('possessori') or 'N/D'}")
             else: print("Nessun immobile trovato.")

        elif scelta == "9": # Cerca Immobili Specifici (usa _seleziona_comune opzionale)
             stampa_intestazione("CERCA IMMOBILI SPECIFICI")
             part_id_str = input("Filtra per ID Partita (vuoto per non filtrare): ").strip()
             comune_id = None
             if _confirm_action("Filtrare per comune?"):
                 comune_id = _seleziona_comune(db, "Seleziona il comune per cui filtrare:")
                 if comune_id is None: print("Filtro comune annullato.")

             loc_id_str = input("Filtra per ID Località (vuoto per non filtrare): ").strip()
             natura = input("Filtra per Natura (parziale, vuoto per non filtrare): ").strip() or None
             classif = input("Filtra per Classificazione (esatta, vuoto per non filtrare): ").strip() or None
             try:
                  part_id = int(part_id_str) if part_id_str else None
                  loc_id = int(loc_id_str) if loc_id_str else None
                  # Il metodo del manager accetta comune_id
                  immobili = db.search_immobili(part_id, comune_id, loc_id, natura, classif)
                  if immobili:
                       print(f"\nTrovati {len(immobili)} immobili:")
                       # Assumiamo che il metodo/SQL ritorni comune_nome
                       for imm in immobili: print(f"- ID: {imm['id']}, Nat:{imm['natura']}, Loc:{imm['localita_nome']} (Comune:{imm.get('comune_nome','?')}), Part:{imm['numero_partita']}, Class:{imm.get('classificazione','-')}")
                  else: print("Nessun immobile trovato.")
             except ValueError: print("ID non valido.")

        elif scelta == "10": # Cerca Variazioni (usa _seleziona_comune opzionale)
             stampa_intestazione("CERCA VARIAZIONI")
             tipo = input("Tipo (Acquisto/Successione/..., vuoto per tutti): ").strip().capitalize() or None
             data_i_str = input("Data inizio (YYYY-MM-DD, vuoto per non filtrare): ").strip()
             data_f_str = input("Data fine (YYYY-MM-DD, vuoto per non filtrare): ").strip()
             part_o_id_str = input("ID Partita Origine (vuoto per non filtrare): ").strip()
             part_d_id_str = input("ID Partita Destinazione (vuoto per non filtrare): ").strip()
             comune_id = None
             if _confirm_action("Filtrare per comune di origine?"):
                 comune_id = _seleziona_comune(db, "Seleziona il comune di origine per cui filtrare:")
                 if comune_id is None: print("Filtro comune annullato.")

             try:
                  data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date() if data_i_str else None
                  data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date() if data_f_str else None
                  part_o_id = int(part_o_id_str) if part_o_id_str else None
                  part_d_id = int(part_d_id_str) if part_d_id_str else None
                  # Il metodo del manager accetta comune_id
                  variazioni = db.search_variazioni(tipo, data_i, data_f, part_o_id, part_d_id, comune_id)
                  if variazioni:
                       print(f"\nTrovate {len(variazioni)} variazioni:")
                       # Assumiamo che il metodo/SQL ritorni comune_nome
                       for v in variazioni:
                            dest_str = f" -> Dest.Partita:{v.get('partita_destinazione_numero', '-')}" if v.get('partita_destinazione_id') else ""
                            print(f"- ID:{v['id']} {v['data_variazione']} {v['tipo']} Orig.Partita:{v['partita_origine_numero']}(Comune:{v.get('comune_nome','?')}){dest_str} Rif:{v.get('numero_riferimento') or '-'}/{v.get('nominativo_riferimento') or '-'}")
                  else: print("Nessuna variazione trovata.")
             except ValueError: print("Input ID o Data non validi.")

        elif scelta == "11": # Cerca Consultazioni (invariato)
             stampa_intestazione("CERCA CONSULTAZIONI")
             data_i_str = input("Data inizio (YYYY-MM-DD, vuoto per non filtrare): ").strip()
             data_f_str = input("Data fine (YYYY-MM-DD, vuoto per non filtrare): ").strip()
             richiedente = input("Richiedente (parziale, vuoto per non filtrare): ").strip() or None
             funzionario = input("Funzionario (parziale, vuoto per non filtrare): ").strip() or None
             try:
                  data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date() if data_i_str else None
                  data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date() if data_f_str else None
                  consultazioni = db.search_consultazioni(data_i, data_f, richiedente, funzionario)
                  if consultazioni:
                       print(f"\nTrovate {len(consultazioni)} consultazioni:")
                       for c in consultazioni:
                            print(f"- ID:{c['id']} {c['data']} Rich:{c['richiedente']} Funz:{c['funzionario_autorizzante']}")
                            print(f"  Mat: {c['materiale_consultato']}")
                  else: print("Nessuna consultazione trovata.")
             except ValueError: print("Formato Data non valido.")

        elif scelta == "12": # Esporta Partita (invariato)
            _esporta_entita_json(db, tipo_entita='partita', etichetta_id='ID della Partita', nome_file_prefix='partita')

        elif scelta == "13": # Esporta Possessore (invariato)
            _esporta_entita_json(db, tipo_entita='possessore', etichetta_id='ID del Possessore', nome_file_prefix='possessore')

        elif scelta == "14": break # Torna al menu principale
        else: print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Inserimento (MODIFICATO per comune_id) ---
def menu_inserimento(db: CatastoDBManager):
    """Menu per operazioni di inserimento e gestione dati."""
    while True:
        stampa_intestazione("INSERIMENTO E GESTIONE DATI")
        print("1. Aggiungi nuovo comune"); print("2. Aggiungi nuovo possessore"); print("3. Aggiungi nuova localita")
        print("4. Registra nuova proprieta (Workflow)"); print("5. Registra passaggio di proprieta (Workflow)")
        print("6. Registra consultazione"); print("7. Inserisci Contratto per Variazione"); print("8. Duplica Partita")
        print("9. Trasferisci Immobile a Nuova Partita"); print("10. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-10): ").strip()
        _set_session_context(db) # Imposta contesto sessione

        if scelta == "1": aggiungi_comune(db)
        elif scelta == "2": inserisci_possessore(db) # Usa versione aggiornata con selezione comune
        elif scelta == "3": inserisci_localita(db)   # Usa versione aggiornata con selezione comune
        elif scelta == "4": _registra_nuova_proprieta_interattivo(db) # Usa versione aggiornata con selezione comune
        elif scelta == "5": _registra_passaggio_proprieta_interattivo(db) # Usa versione aggiornata con selezione comune
        elif scelta == "6": _registra_consultazione_interattivo(db) # Invariato
        elif scelta == "7": _inserisci_contratto_interattivo(db)   # Invariato
        elif scelta == "8": _duplica_partita_interattivo(db)       # Invariato
        elif scelta == "9": _trasferisci_immobile_interattivo(db)  # Invariato
        elif scelta == "10": break
        else: print("Opzione non valida!")
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


# --- Menu Report (MODIFICATO per comune_id) ---
def menu_report(db: CatastoDBManager):
    """Menu per la generazione di report."""
    while True:
        stampa_intestazione("GENERAZIONE REPORT")
        print("1. Certificato di proprieta"); print("2. Report genealogico"); print("3. Report possessore")
        print("4. Report consultazioni"); print("5. Statistiche per comune (Vista)"); print("6. Riepilogo immobili per tipologia (Vista)")
        print("7. Visualizza Partite Complete (Vista)"); print("8. Cronologia Variazioni (Vista)")
        print("9. Report Annuale Partite per Comune (Funzione)"); print("10. Report Proprietà Possessore per Periodo (Funzione)")
        print("11. Report Statistico Comune (Funzione)"); print("12. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-12): ").strip()

        if scelta == "1": # Certificato Proprietà (invariato)
            partita_id_str = input("Inserisci l'ID della partita: ").strip()
            if partita_id_str.isdigit():
                partita_id = int(partita_id_str)
                certificato = db.genera_certificato_proprieta(partita_id) # Funzione SQL deve fare JOIN per nome comune
                if certificato:
                    stampa_intestazione("CERTIFICATO DI PROPRIETA"); print(certificato)
                    filename = f"certificato_partita_{partita_id}_{date.today()}.txt"
                    if _confirm_action(f"Salvare su file '{filename}'?"):
                         try: 
                             with open(filename, 'w', encoding='utf-8') as f: 
                                f.write(certificato); print("Certificato salvato.")
                         except Exception as e: print(f"Errore salvataggio: {e}")
                else: print("Nessun dato disponibile o errore generazione.")
            else: print("ID non valido!")

        elif scelta == "2": # Report Genealogico (invariato)
            partita_id_str = input("Inserisci l'ID della partita: ").strip()
            if partita_id_str.isdigit():
                partita_id = int(partita_id_str)
                report = db.genera_report_genealogico(partita_id) # Funzione SQL deve fare JOIN per nomi comuni
                if report:
                    stampa_intestazione("REPORT GENEALOGICO"); print(report)
                    filename = f"report_genealogico_{partita_id}_{date.today()}.txt"
                    if _confirm_action(f"Salvare su file '{filename}'?"):
                         try: 
                             with open(filename, 'w', encoding='utf-8') as f: 
                                f.write(report); print("Report salvato.")
                         except Exception as e: print(f"Errore salvataggio: {e}")
                else: print("Nessun dato disponibile o errore generazione.")
            else: print("ID non valido!")

        elif scelta == "3": # Report Possessore (invariato)
            possessore_id_str = input("Inserisci l'ID del possessore: ").strip()
            if possessore_id_str.isdigit():
                possessore_id = int(possessore_id_str)
                report = db.genera_report_possessore(possessore_id) # Funzione SQL deve fare JOIN per nomi comuni
                if report:
                    stampa_intestazione("REPORT POSSESSORE"); print(report)
                    filename = f"report_possessore_{possessore_id}_{date.today()}.txt"
                    if _confirm_action(f"Salvare su file '{filename}'?"):
                         try: 
                             with open(filename, 'w', encoding='utf-8') as f: 
                                f.write(report); print("Report salvato.")
                         except Exception as e: print(f"Errore salvataggio: {e}")
                else: print("Nessun dato disponibile o errore generazione.")
            else: print("ID non valido!")

        elif scelta == "4": # Report Consultazioni (invariato)
            stampa_intestazione("REPORT CONSULTAZIONI")
            data_inizio_str = input("Data inizio (YYYY-MM-DD, vuoto per inizio): ").strip()
            data_fine_str = input("Data fine (YYYY-MM-DD, vuoto per fine): ").strip()
            richiedente = input("Richiedente (vuoto per tutti): ").strip() or None
            try: data_inizio = datetime.strptime(data_inizio_str, "%Y-%m-%d").date() if data_inizio_str else None; data_fine = datetime.strptime(data_fine_str, "%Y-%m-%d").date() if data_fine_str else None
            except ValueError: print("Formato data non valido."); continue
            report = db.genera_report_consultazioni(data_inizio, data_fine, richiedente)
            if report:
                print(report)
                if _confirm_action("Salvare su file?"):
                    oggi = date.today().strftime("%Y%m%d"); filename = f"report_consultazioni_{oggi}.txt"
                    try: 
                        with open(filename, 'w', encoding='utf-8') as f: 
                            f.write(report); print(f"Report salvato in {filename}.")
                    except Exception as e: print(f"Errore salvataggio: {e}")
            else: print("Nessun dato disponibile o errore generazione.")

        elif scelta == "5": # Statistiche per comune (Vista)
            stampa_intestazione("STATISTICHE PER COMUNE (Vista Materializzata)")
            stats = db.get_statistiche_comune() # Metodo/Vista aggiornati
            if stats:
                for s in stats:
                    print(f"Comune: {s['comune']} ({s['provincia']})") # 'comune' è il nome dalla vista
                    print(f"  Partite: Tot={s['totale_partite']}, Att={s['partite_attive']}, Inatt={s['partite_inattive']}")
                    print(f"  Possessori: {s['totale_possessori']}, Immobili: {s['totale_immobili']}"); print("-" * 30)
            else: print("Nessuna statistica disponibile o errore.")

        elif scelta == "6": # Riepilogo immobili (Vista) (usa _seleziona_comune opzionale)
            stampa_intestazione("RIEPILOGO IMMOBILI PER TIPOLOGIA (Vista Materializzata)")
            comune_id = None
            if _confirm_action("Filtrare per comune?"):
                 comune_id = _seleziona_comune(db, "Seleziona il comune per cui filtrare:")
                 if comune_id is None: print("Filtro comune annullato.")
            stats = db.get_immobili_per_tipologia(comune_id=comune_id) # Passa ID (o None)
            if stats:
                current_comune = None
                for s in stats:
                    if s['comune_nome'] != current_comune: current_comune = s['comune_nome']; print(f"\n--- Comune: {current_comune} ---")
                    print(f"  Classificazione: {s.get('classificazione') or 'N/D'}")
                    print(f"    Num Immobili: {s.get('numero_immobili', 0)}, Tot Piani: {s.get('totale_piani', 0)}, Tot Vani: {s.get('totale_vani', 0)}")
            else: print("Nessun dato disponibile o errore.")

        elif scelta == "7": # Visualizza Partite Complete (Vista) (usa _seleziona_comune opzionale)
            stampa_intestazione("VISUALIZZA PARTITE COMPLETE (Vista Materializzata)")
            comune_id = None
            if _confirm_action("Filtrare per comune?"):
                 comune_id = _seleziona_comune(db, "Seleziona il comune per cui filtrare:")
                 if comune_id is None: print("Filtro comune annullato.")
            stato_filter = input("Filtra per stato (attiva/inattiva, vuoto per tutti): ").strip() or None
            partite = db.get_partite_complete_view(comune_id=comune_id, stato=stato_filter) # Passa ID (o None)
            if partite:
                print(f"Trovate {len(partite)} partite:")
                for p in partite:
                    print(f"\nID: {p['partita_id']} - N.{p['numero_partita']} (Comune: {p['comune_nome']}) - Stato: {p['stato']}")
                    print(f"  Tipo: {p['tipo']}, Data Imp.: {p['data_impianto']}")
                    print(f"  Possessori: {p.get('possessori') or 'N/D'}")
                    print(f"  Imm: {p.get('num_immobili',0)} Tipi: {p.get('tipi_immobili') or 'N/D'} Loc: {p.get('localita') or 'N/D'}")
            else: print("Nessuna partita trovata.")

        elif scelta == "8": # Cronologia Variazioni (Vista) (usa _seleziona_comune opzionale)
            stampa_intestazione("CRONOLOGIA VARIAZIONI (Vista Materializzata)")
            comune_id = None
            if _confirm_action("Filtrare per comune di origine?"):
                 comune_id = _seleziona_comune(db, "Seleziona il comune di origine per cui filtrare:")
                 if comune_id is None: print("Filtro comune annullato.")
            tipo_filter = input("Filtra per tipo variazione (vuoto per tutti): ").strip().capitalize() or None
            variazioni = db.get_cronologia_variazioni(comune_origine_id=comune_id, tipo_variazione=tipo_filter) # Passa ID (o None)
            if variazioni:
                print(f"Trovate {len(variazioni)} variazioni:")
                for v in variazioni:
                    print(f"\nID Var:{v['variazione_id']} Tipo:{v['tipo_variazione']} Data:{v['data_variazione']}")
                    print(f"  Origine: N.{v['partita_origine_numero']} (Comune:{v['comune_origine']}) Poss: {v.get('possessori_origine') or 'N/D'}")
                    if v.get('partita_dest_numero'): print(f"  Destinaz: N.{v['partita_dest_numero']} (Comune:{v['comune_dest']}) Poss: {v.get('possessori_dest') or 'N/D'}")
                    if v.get('tipo_contratto'): print(f"  Contratto: {v['tipo_contratto']} del {v['data_contratto']} (Notaio: {v.get('notaio') or 'N/D'})")
            else: print("Nessuna variazione trovata.")

        elif scelta == "9": # Report Annuale Partite (Funzione) (usa _seleziona_comune)
            stampa_intestazione("REPORT ANNUALE PARTITE PER COMUNE (Funzione)")
            comune_id = _seleziona_comune(db, "Seleziona il comune per il report:")
            if comune_id is None: print("Selezione annullata."); continue
            anno_str = input("Anno del report: ").strip()
            if anno_str.isdigit():
                anno = int(anno_str)
                report = db.get_report_annuale_partite(comune_id, anno) # Passa ID
                comune_info = next((c for c in db.get_comuni() if c['id'] == comune_id), {'nome': 'N/D'}) # Trova nome
                if report:
                    print(f"\nReport per {comune_info['nome']} - Anno {anno}:")
                    for r in report:
                        print(f"  N.{r['numero_partita']} ({r['tipo']}) Stato:{r['stato']} Imp:{r['data_impianto']}")
                        print(f"    Poss: {r.get('possessori') or 'N/D'} Imm:{r.get('num_immobili',0)} Var:{r.get('variazioni_anno',0)}")
                else: print("Nessun dato trovato o errore.")
            else: print("Anno non valido.")

        elif scelta == "10": # Report Proprietà Possessore (invariato)
             stampa_intestazione("REPORT PROPRIETÀ POSSESSORE PER PERIODO (Funzione)")
             poss_id_str = input("ID del possessore: ").strip()
             data_i_str = input("Data inizio periodo (YYYY-MM-DD): ").strip()
             data_f_str = input("Data fine periodo (YYYY-MM-DD): ").strip()
             if not (poss_id_str.isdigit() and data_i_str and data_f_str): print("ID Possessore e date obbligatori."); continue
             try: possessore_id = int(poss_id_str); data_inizio = datetime.strptime(data_i_str, "%Y-%m-%d").date(); data_fine = datetime.strptime(data_f_str, "%Y-%m-%d").date()
             except ValueError: print("Formato ID o data non validi."); continue
             report = db.get_report_proprieta_possessore(possessore_id, data_inizio, data_fine) # Funzione SQL aggiornata
             if report:
                 print(f"\nProprietà ID {possessore_id} tra {data_inizio} e {data_fine}:")
                 for r in report:
                     quota_str = f" (Quota: {r['quota']})" if r['quota'] else ""
                     print(f"- Partita N.{r['numero_partita']} ({r['comune_nome']}) ID:{r['partita_id']}") # Funzione ritorna nome comune
                     print(f"  Titolo: {r['titolo']}{quota_str} Periodo: {r['data_inizio']} - {r['data_fine']}")
                     print(f"  Immobili: {r.get('immobili_posseduti') or 'Nessuno'}")
             else: print("Nessun dato trovato.")

        elif scelta == "11": # Report Statistico Comune (Funzione) (usa _seleziona_comune)
             stampa_intestazione("REPORT STATISTICO COMUNE (Funzione)")
             comune_id = _seleziona_comune(db, "Seleziona il comune per il report:")
             if comune_id is not None:
                 report_data = db.get_report_comune(comune_id) # Passa ID
                 if report_data:
                     print(f"\nStatistiche per {report_data['comune']}:") # Funzione ritorna nome
                     print(f"  Partite: Tot {report_data['totale_partite']} (Att:{report_data['partite_attive']}, Inatt:{report_data['partite_inattive']})")
                     print(f"  Possessori: {report_data['totale_possessori']} (Medi per Partita: {report_data.get('possessori_per_partita', 0):.2f})")
                     print(f"  Immobili Totali: {report_data['totale_immobili']}")
                     print("  Immobili per Classe:")
                     try:
                         imm_per_classe = json.loads(report_data['immobili_per_classe']) if report_data.get('immobili_per_classe') else {}
                         if imm_per_classe: [print(f"    - {classe or 'Non Class.'}: {count}") for classe, count in imm_per_classe.items()]
                         else: print("    N/D")
                     except (json.JSONDecodeError, TypeError): print("    (Dati JSON non validi)")
                 else: print(f"Comune ID {comune_id} non trovato o errore report.")
             # else: selezione annullata

        elif scelta == "12": break
        else: print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Manutenzione (invariato) ---
def menu_manutenzione(db: CatastoDBManager):
    """Menu per la manutenzione del database."""
    while True:
        stampa_intestazione("MANUTENZIONE DATABASE")
        print("1. Verifica integrita database"); print("2. Aggiorna Viste Materializzate"); print("3. Esegui Manutenzione Generale (ANALYZE)")
        print("4. Analizza Query Lente (Richiede pg_stat_statements)"); print("5. Controlla Frammentazione Indici")
        print("6. Ottieni Suggerimenti Ottimizzazione"); print("7. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-7): ").strip()
        _set_session_context(db)
        if scelta == "1":
            stampa_intestazione("VERIFICA INTEGRITA DATABASE"); print("Avvio verifica...")
            problemi, messaggio = db.verifica_integrita_database()
            print("\n--- Risultato Verifica ---"); print(messaggio); print("--- Fine Risultato ---")
            if problemi: print("\nATTENZIONE: Rilevati problemi!"); print("(La correzione automatica non è implementata in questo esempio)")
            else: print("\nNessun problema critico rilevato.")
        elif scelta == "2":
            stampa_intestazione("AGGIORNAMENTO VISTE MATERIALIZZATE")
            if _confirm_action("Aggiornare tutte le viste materializzate?"):
                print("Avvio aggiornamento...");
                if db.refresh_materialized_views(): print("Aggiornamento completato.")
                else: print("Errore durante l'aggiornamento (controllare log).")
        elif scelta == "3":
            stampa_intestazione("ESEGUI MANUTENZIONE GENERALE (ANALYZE)")
            if _confirm_action("Eseguire ANALYZE e aggiornare viste?"):
                print("Avvio manutenzione (ANALYZE, REFRESH MV)...")
                if db.run_database_maintenance(): print("Manutenzione completata.")
                else: print("Errore durante la manutenzione (controllare log).")
        elif scelta == "4":
            stampa_intestazione("ANALIZZA QUERY LENTE")
            print("NOTA: Richiede estensione 'pg_stat_statements' abilitata."); min_dur_str = input("Durata minima query in ms (default 1000): ").strip() or "1000"
            if min_dur_str.isdigit():
                slow_queries = db.analyze_slow_queries(int(min_dur_str))
                if slow_queries:
                    print(f"\nTrovate {len(slow_queries)} query più lente di {min_dur_str} ms:")
                    for q in slow_queries:
                         dur = round(q.get('durata_ms', 0), 2); righe = q.get('righe_restituite', 'N/A'); call = q.get('chiamate', 'N/A'); q_text = (q.get('query_text', '')[:150] + "...")
                         print(f"\n ID:{q.get('query_id','N/A')} Durata:{dur}ms Chiamate:{call} Righe:{righe}"); print(f"   Query: {q_text}")
                elif slow_queries is not None: print(f"Nessuna query trovata con durata media > {min_dur_str} ms.")
            else: print("Durata non valida.")
        elif scelta == "5":
            stampa_intestazione("CONTROLLA FRAMMENTAZIONE INDICI"); print("Avvio controllo...")
            db.check_index_fragmentation(); print("Controllo eseguito. Verificare i log del database per dettagli.")
        elif scelta == "6":
            stampa_intestazione("OTTIENI SUGGERIMENTI OTTIMIZZAZIONE")
            suggestions = db.get_optimization_suggestions()
            if suggestions: print("\nSuggerimenti:\n", suggestions)
            else: print("Nessun suggerimento disponibile o errore.")
        elif scelta == "7": break
        else: print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Audit (invariato) ---
def menu_audit(db: CatastoDBManager):
    """Menu per la gestione e consultazione del sistema di audit."""
    while True:
        stampa_intestazione("SISTEMA DI AUDIT")
        print("1. Consulta log di audit"); print("2. Visualizza cronologia di un record")
        print("3. Genera report di audit"); print("4. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-4): ").strip()
        if scelta == "1":
            stampa_intestazione("CONSULTA LOG DI AUDIT")
            tabella = input("Tabella (vuoto per tutte): ").strip() or None; op = input("Operazione (I/U/D, vuoto per tutte): ").strip().upper() or None
            rec_id_str = input("ID Record (vuoto per tutti): ").strip(); app_user_id_str = input("ID Utente App (vuoto per tutti): ").strip()
            session_id_str = input("ID Sessione (vuoto per tutti): ").strip() or None; utente_db_str = input("Utente DB (vuoto per tutti): ").strip() or None
            data_i_str = input("Data inizio (YYYY-MM-DD, vuoto): ").strip(); data_f_str = input("Data fine (YYYY-MM-DD, vuoto): ").strip()
            rec_id = int(rec_id_str) if rec_id_str.isdigit() else None; app_user_id = int(app_user_id_str) if app_user_id_str.isdigit() else None
            data_inizio, data_fine = None, None
            try:
                if data_i_str: data_inizio = datetime.strptime(data_i_str, "%Y-%m-%d").date()
                if data_f_str: data_fine = datetime.strptime(data_f_str, "%Y-%m-%d").date()
            except ValueError: print("Formato data non valido."); continue
            logs = db.get_audit_log(tabella, op, rec_id, data_inizio, data_fine, utente_db, app_user_id, session_id_str)
            stampa_intestazione(f"RISULTATI LOG AUDIT ({len(logs)})")
            if not logs: print("Nessun log trovato.")
            else:
                op_map = {"I": "Ins", "U": "Upd", "D": "Del"}
                for log in logs:
                    user_info = f"DB:{log.get('db_user', '?')}" + (f" App:{log.get('app_user_id')}({log.get('app_username', '?')})" if log.get('app_user_id') is not None else " App:N/A")
                    print(f"ID:{log['audit_id']} {log['timestamp']:%y-%m-%d %H:%M} {op_map.get(log['operazione'],'?')} "
                          f"T:{log['tabella']} R:{log.get('record_id','N/A')} {user_info} S:{log.get('session_id','-')[:8]} IP:{log.get('ip_address','-')}")
                    # if log['operazione'] == 'U' and _confirm_action("  Vedere dettagli modifiche?"): ... # Logica dettagli (omessa per brevità)
                    print("-" * 40)
        elif scelta == "2":
            stampa_intestazione("CRONOLOGIA RECORD")
            tabella = input("Nome tabella (es. partita, possessore): ").strip()
            record_id_str = input("ID record: ").strip()
            if tabella and record_id_str.isdigit():
                history = db.get_record_history(tabella, int(record_id_str))
                stampa_intestazione(f"CRONOLOGIA {tabella.upper()} ID {record_id_str} ({len(history)} eventi)")
                if not history: print("Nessuna modifica registrata.")
                else:
                    op_map = {"I": "Inserimento", "U": "Aggiornamento", "D": "Cancellazione"}
                    for i, record in enumerate(history, 1):
                         user = record.get('utente') or record.get('db_user', '?')
                         print(f"{i}. {op_map.get(record['operazione'], '?')} - {record['timestamp']:%Y-%m-%d %H:%M} - Utente:{user}")
                         # if record['operazione'] == 'U': ... # Logica dettagli (omessa per brevità)
                         print()
            else: print("Tabella e ID record validi richiesti.")
        elif scelta == "3":
            stampa_intestazione("GENERA REPORT DI AUDIT")
            tabella = input("Tabella (vuoto per tutte): ").strip() or None; op = input("Operazione (I/U/D, vuoto per tutte): ").strip().upper() or None
            app_user_id_str = input("ID Utente App (vuoto per tutti): ").strip(); utente_db = input("Utente DB (vuoto per tutti): ").strip() or None
            data_i_str = input("Data inizio (YYYY-MM-DD, vuoto): ").strip(); data_f_str = input("Data fine (YYYY-MM-DD, vuoto): ").strip()
            app_user_id = int(app_user_id_str) if app_user_id_str.isdigit() else None; data_inizio, data_fine = None, None
            try:
                 if data_i_str: data_inizio = datetime.strptime(data_i_str, "%Y-%m-%d").date()
                 if data_f_str: data_fine = datetime.strptime(data_f_str, "%Y-%m-%d").date()
            except ValueError: print("Formato data non valido."); continue
            report = db.genera_report_audit(tabella, data_inizio, data_fine, op, utente_db, app_user_id)
            print(report)
            if _confirm_action("Salvare report su file?"):
                 oggi = date.today().strftime("%Y%m%d"); filename = f"report_audit_{oggi}.txt"
                 try: 
                     with open(filename, 'w', encoding='utf-8') as f: 
                        f.write(report); print(f"Report salvato in {filename}.")
                 except Exception as e: print(f"Errore salvataggio: {e}")
        elif scelta == "4": break
        else: print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Utenti e Sessione (Usa bcrypt, invariato rispetto a comune_id) ---
def menu_utenti(db: CatastoDBManager):
    """Menu per la gestione degli utenti, login e logout."""
    global logged_in_user_id, current_session_id, client_ip_address
    while True:
        stampa_intestazione("GESTIONE UTENTI E SESSIONE")
        if logged_in_user_id: print(f"--- Utente Attivo: ID {logged_in_user_id} (Sessione: {current_session_id[:8]}...) ---")
        else: print("--- Nessun utente connesso ---")
        print("1. Crea nuovo utente"); print("2. Login Utente"); print("3. Logout Utente")
        print("4. Verifica Permesso Utente"); print("5. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-5): ").strip()
        _set_session_context(db)
        if scelta == "1": # Crea nuovo utente
            stampa_intestazione("CREA NUOVO UTENTE")
            username = input("Username: ").strip(); password = getpass.getpass("Password: "); password_confirm = getpass.getpass("Conferma Password: ")
            if not password: print("Password obbligatoria."); continue
            if password != password_confirm: print("Le password non coincidono."); continue
            nome_completo = input("Nome completo: ").strip(); email = input("Email: ").strip()
            print("Ruoli disponibili: admin, archivista, consultatore"); ruolo = input("Ruolo: ").strip().lower()
            if not all([username, nome_completo, email, ruolo]): print("Tutti i campi (eccetto password vuota) sono obbligatori."); continue
            if ruolo not in ['admin', 'archivista', 'consultatore']: print("Ruolo non valido."); continue
            try: password_hash = _hash_password(password); logger.debug(f"Hash generato per {username}")
            except Exception as hash_err: logger.error(f"Errore hashing password per {username}: {hash_err}"); print("Errore tecnico hashing."); continue
            if db.create_user(username, password_hash, nome_completo, email, ruolo): print(f"Utente '{username}' creato.")
            else: print(f"Errore creazione utente '{username}' (controllare log - es. duplicato).")
        elif scelta == "2": # Login Utente
            if logged_in_user_id: print("Già connesso. Logout prima."); continue
            stampa_intestazione("LOGIN UTENTE"); username = input("Username: ").strip(); password = getpass.getpass("Password: ")
            if not username or not password: print("Username e password obbligatori."); continue
            credentials = db.get_user_credentials(username); login_success = False; user_id = None
            if credentials:
                user_id = credentials['id']; stored_hash = credentials['password_hash']
                logger.debug(f"Tentativo login per user ID {user_id}. Hash: {stored_hash[:10]}...")
                if _verify_password(stored_hash, password): login_success = True; print(f"Login riuscito per utente ID: {user_id}"); logger.info(f"Login OK per ID: {user_id}")
                else: print("Password errata."); logger.warning(f"Login fallito (pwd errata) per ID: {user_id}")
            else: print("Utente non trovato o non attivo."); logger.warning(f"Login fallito (utente '{username}' non trovato/attivo).")
            if user_id is not None: # Registra accesso se utente trovato
                session_id_returned = db.register_access(user_id, 'login', indirizzo_ip=client_ip_address, esito=login_success)
                if login_success and session_id_returned:
                    logged_in_user_id = user_id; current_session_id = session_id_returned
                    if not db.set_session_app_user(logged_in_user_id, client_ip_address): logger.error("Impossibile impostare contesto DB post-login!")
                    print(f"Sessione {current_session_id[:8]}... avviata.")
                elif login_success and not session_id_returned:
                    print("Errore critico: Impossibile registrare sessione accesso."); logger.error(f"Login OK per ID {user_id} ma fallita reg. accesso.")
                    logged_in_user_id = None; current_session_id = None # Non loggare utente
        elif scelta == "3": # Logout Utente
             if not logged_in_user_id: print("Nessun utente connesso."); continue
             stampa_intestazione("LOGOUT UTENTE"); print(f"Disconnessione utente ID: {logged_in_user_id}...")
             if db.logout_user(logged_in_user_id, current_session_id, client_ip_address): print("Logout eseguito.")
             else: print("Errore registrazione logout (controllare log).")
             logged_in_user_id = None; current_session_id = None
        elif scelta == "4": # Verifica Permesso
             stampa_intestazione("VERIFICA PERMESSO UTENTE"); utente_id_str = input("ID Utente (vuoto per utente corrente): ").strip(); utente_id_to_check = None
             if utente_id_str.isdigit():
                 try: utente_id_to_check = int(utente_id_str)
                 except ValueError: print("ID utente non valido."); continue
             elif logged_in_user_id: utente_id_to_check = logged_in_user_id; print(f"(Verifica per utente corrente ID: {utente_id_to_check})")
             else: print("Nessun utente corrente e ID non specificato."); continue
             permesso = input("Nome del permesso (es. 'modifica_partite'): ").strip()
             if not permesso: print("Nome permesso obbligatorio."); continue
             if utente_id_to_check is not None:
                 try:
                     ha_permesso = db.check_permission(utente_id_to_check, permesso)
                     if ha_permesso: print(f"Utente ID {utente_id_to_check} HA il permesso '{permesso}'.")
                     else: print(f"Utente ID {utente_id_to_check} NON HA il permesso '{permesso}' o errore.")
                 except Exception as perm_err: logger.error(f"Errore verifica permesso '{permesso}' user ID {utente_id_to_check}: {perm_err}"); print("Errore verifica permesso.")
        elif scelta == "5": break
        else: print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Backup (invariato) ---
def menu_backup(db: CatastoDBManager):
    """Menu per le operazioni di Backup e Restore."""
    while True:
        stampa_intestazione("SISTEMA DI BACKUP E RESTORE")
        print("NOTA BENE: I comandi backup/restore vanno eseguiti manualmente nella shell."); print("\n1. Ottieni comando per Backup"); print("2. Visualizza Log Backup Recenti")
        print("3. Ottieni comando per Restore (da ID Log)"); print("4. Registra manualmente un Backup eseguito"); print("5. Genera Script Bash per Backup Automatico")
        print("6. Pulisci Log Backup vecchi"); print("7. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-7): ").strip()
        _set_session_context(db)
        if scelta == "1":
            stampa_intestazione("OTTIENI COMANDO BACKUP"); print("Tipi: completo, schema, dati"); tipo = input("Tipo (default: completo): ").strip() or 'completo'
            if tipo not in ['completo', 'schema', 'dati']: print("Tipo non valido."); continue
            cmd = db.get_backup_command_suggestion(tipo=tipo)
            if cmd: print("\n--- Comando Suggerito (eseguire in shell) ---\n", cmd, "\n" + "-"*55)
            else: print("Errore generazione comando.")
        elif scelta == "2":
            stampa_intestazione("LOG BACKUP RECENTI"); logs = db.get_backup_logs()
            if logs:
                for log in logs:
                    esito = "OK" if log['esito'] else "FALLITO"; dim = f"{log['dimensione_bytes']} bytes" if log.get('dimensione_bytes') is not None else "N/D"
                    print(f"ID:{log['id']} {log['timestamp']:%Y-%m-%d %H:%M} Tipo:{log['tipo']} Esito:{esito}")
                    print(f"  File: {log['nome_file']} ({dim}) Utente:{log['utente']}");
                    if log.get('messaggio'): print(f"  Msg: {log['messaggio']}")
                    print("-" * 30)
            else: print("Nessun log di backup trovato.")
        elif scelta == "3":
            stampa_intestazione("OTTIENI COMANDO RESTORE"); log_id_str = input("ID del log di backup da cui ripristinare: ").strip()
            if log_id_str.isdigit():
                cmd = db.get_restore_command_suggestion(int(log_id_str))
                if cmd: print("\n--- Comando Suggerito (eseguire in shell) ---\n", cmd, "\n" + "-"*55); print("ATTENZIONE: Sovrascriverà i dati attuali!")
                else: print("ID log non valido o errore.")
            else: print("ID non valido.")
        elif scelta == "4":
             stampa_intestazione("REGISTRA BACKUP MANUALE"); nome_file = input("Nome file backup: ").strip(); percorso = input("Percorso completo file: ").strip()
             utente = input("Utente esecuzione (default 'manuale'): ").strip() or 'manuale'; tipo = input("Tipo ('completo', 'schema', 'dati'): ").strip()
             esito_str = input("Backup riuscito? (s/n): ").strip().lower(); msg = input("Messaggio (opzionale): ").strip() or None; dim_str = input("Dimensione bytes (opzionale): ").strip()
             if not all([nome_file, percorso, tipo]): print("Nome, percorso e tipo obbligatori."); continue
             if tipo not in ['completo', 'schema', 'dati']: print("Tipo non valido."); continue
             esito = esito_str == 's'; dim = int(dim_str) if dim_str.isdigit() else None
             backup_id = db.register_backup_log(nome_file, utente, tipo, esito, percorso, dim, msg)
             if backup_id: print(f"Backup manuale registrato con ID: {backup_id}")
             else: print("Errore registrazione backup manuale.")
        elif scelta == "5":
            stampa_intestazione("GENERA SCRIPT BACKUP AUTOMATICO"); backup_dir = input("Directory destinazione backup: ").strip(); script_name = input("Nome file script (es. backup_catasto.sh): ").strip()
            if not backup_dir or not script_name: print("Directory e nome script obbligatori."); continue
            script_content = db.generate_backup_script(backup_dir)
            if script_content:
                try:
                    with open(script_name, 'w', encoding='utf-8') as f: f.write(script_content); os.chmod(script_name, 0o755) # Rende eseguibile
                    print(f"Script '{script_name}' generato in {os.getcwd()}."); print("Configura cron job o task schedulato.")
                except Exception as e: print(f"Errore salvataggio script: {e}")
            else: print("Errore generazione script.")
        elif scelta == "6":
            stampa_intestazione("PULISCI LOG BACKUP VECCHI"); giorni_str = input("Conserva log ultimi giorni? (default 30): ").strip() or "30"
            if giorni_str.isdigit():
                if db.cleanup_old_backup_logs(int(giorni_str)): print("Pulizia log vecchi completata.")
                else: print("Errore pulizia log.")
            else: print("Numero giorni non valido.")
        elif scelta == "7": break
        else: print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Storico Avanzato (MODIFICATO per comune_id) ---
def menu_storico_avanzato(db: CatastoDBManager):
    """Menu per le funzionalità storiche avanzate."""
    while True:
        stampa_intestazione("FUNZIONALITÀ STORICHE AVANZATE")
        print("1. Visualizza Periodi Storici"); print("2. Ottieni Nome Storico Entità per Anno"); print("3. Registra Nome Storico Entità")
        print("4. Ricerca Documenti Storici"); print("5. Visualizza Albero Genealogico Proprietà"); print("6. Statistiche Catastali per Periodo")
        print("7. Collega Documento a Partita"); print("8. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-8): ").strip()
        _set_session_context(db)

        if scelta == "1": # Visualizza Periodi Storici (invariato)
            stampa_intestazione("PERIODI STORICI"); periodi = db.get_historical_periods()
            if periodi: [print(f"ID:{p['id']} {p['nome']} ({p['anno_inizio']}-{p.get('anno_fine') or 'oggi'}) Desc: {p.get('descrizione') or '-'}") for p in periodi]
            else: print("Nessun periodo storico trovato.")

        elif scelta == "2": # Ottieni Nome Storico (invariato, usa ID entità)
            stampa_intestazione("OTTIENI NOME STORICO ENTITÀ")
            tipo_ent = input("Tipo entità (comune/localita): ").strip().lower()
            if tipo_ent not in ['comune', 'localita']: print("Tipo non valido."); continue
            id_ent_str = input(f"ID {tipo_ent}: ").strip()
            anno_str = input("Anno (INVIO per corrente): ").strip()
            if not id_ent_str.isdigit(): print("ID non valido."); continue
            entita_id = int(id_ent_str); anno = int(anno_str) if anno_str.isdigit() else None
            nome_info = db.get_historical_name(tipo_ent, entita_id, anno)
            if nome_info:
                print(f"\nNome in anno {anno or datetime.now().year}: {nome_info['nome']}")
                print(f" Periodo: {nome_info['periodo_nome']} ({nome_info['anno_inizio']}-{nome_info.get('anno_fine') or 'oggi'})")
            else: print("Nessun nome storico trovato.")

        elif scelta == "3": # Registra Nome Storico (invariato, usa ID entità)
            stampa_intestazione("REGISTRA NOME STORICO")
            tipo_ent = input("Tipo entità (comune/localita): ").strip().lower()
            if tipo_ent not in ['comune', 'localita']: print("Tipo non valido."); continue
            id_ent_str = input(f"ID {tipo_ent}: ").strip(); nome_storico = input("Nome storico da registrare: ").strip()
            periodi = db.get_historical_periods()
            if not periodi: print("Definire prima i periodi storici."); continue
            print("\nPeriodi disponibili:"); [print(f" ID: {p['id']} - {p['nome']}") for p in periodi]
            periodo_id_str = input("ID Periodo storico: ").strip(); anno_i_str = input("Anno inizio validità nome: ").strip()
            anno_f_str = input("Anno fine validità (INVIO se valido fino a fine periodo): ").strip()
            if not (id_ent_str.isdigit() and nome_storico and periodo_id_str.isdigit() and anno_i_str.isdigit()): print("ID entità, nome, ID periodo e anno inizio obbligatori."); continue
            try: entita_id = int(id_ent_str); periodo_id = int(periodo_id_str); anno_inizio = int(anno_i_str); anno_fine = int(anno_f_str) if anno_f_str.isdigit() else None
            except ValueError: print("Input numerico non valido."); continue
            note = input("Note (opzionale): ").strip() or None
            if db.register_historical_name(tipo_ent, entita_id, nome_storico, periodo_id, anno_inizio, anno_fine, note): print("Nome storico registrato.")
            else: print("Errore registrazione nome storico.")

        elif scelta == "4": # Ricerca Documenti Storici (invariato)
             stampa_intestazione("RICERCA DOCUMENTI STORICI")
             titolo = input("Titolo (parziale, INVIO ): ").strip() or None; tipo_doc = input("Tipo documento (esatto, INVIO ): ").strip() or None
             periodo_id_str = input("ID Periodo storico (INVIO ): ").strip(); anno_i_str = input("Anno inizio (INVIO ): ").strip(); anno_f_str = input("Anno fine (INVIO ): ").strip()
             part_id_str = input("ID Partita collegata (INVIO ): ").strip()
             try: 
                periodo_id = int(periodo_id_str) if periodo_id_str else None; 
                anno_inizio = int(anno_i_str) if anno_i_str else None
                anno_fine = int(anno_f_str) if anno_f_str else None; partita_id = int(part_id_str) if part_id_str else None
             except ValueError: print("Input ID/Anno non valido."); continue
             documenti = db.search_historical_documents(titolo, tipo_doc, periodo_id, anno_inizio, anno_fine, partita_id)
             if documenti:
                 print(f"\nTrovati {len(documenti)} documenti:")
                 for doc in documenti:
                      print(f"- ID:{doc['documento_id']} {doc['titolo']} ({doc['tipo_documento']}) Anno:{doc['anno']} Periodo:{doc['periodo_nome']}")
                      if doc.get('descrizione'): print(f"  Desc: {doc['descrizione']}")
                      if doc.get('partite_correlate'): print(f"  Partite: {doc['partite_correlate']}") # SQL deve fare JOIN per nome comune
             else: print("Nessun documento trovato.")

        elif scelta == "5": # Albero Genealogico (invariato)
            stampa_intestazione("ALBERO GENEALOGICO PROPRIETÀ")
            part_id_str = input("ID della partita di partenza: ").strip()
            if part_id_str.isdigit():
                albero = db.get_property_genealogy(int(part_id_str)) # Funzione SQL deve fare JOIN per nome comune
                if albero:
                    print("\nLivello | Relazione    | ID Partita | Comune           | N. Partita | Tipo       | Possessori")
                    print("--------|--------------|------------|------------------|------------|------------|-----------")
                    for nodo in albero:
                        poss = (nodo.get('possessori') or '')[:40] + ('...' if len(nodo.get('possessori','')) > 40 else '')
                        data_v = f" ({nodo['data_variazione']})" if nodo.get('data_variazione') else ""
                        print(f" {str(nodo.get('livello', '?')).rjust(6)} | {nodo.get('tipo_relazione', '').ljust(12)} | {str(nodo.get('partita_id', '')).ljust(10)} | {nodo.get('comune_nome', '').ljust(16)} | {str(nodo.get('numero_partita', '')).ljust(10)} | {nodo.get('tipo', '').ljust(10)} | {poss}{data_v}")
                else: print("Impossibile generare albero genealogico.")
            else: print("ID partita non valido.")

        elif scelta == "6": # Statistiche Catastali per Periodo (usa _seleziona_comune opzionale)
             stampa_intestazione("STATISTICHE CATASTALI PER PERIODO")
             comune_id = None
             if _confirm_action("Filtrare per comune?"):
                 comune_id = _seleziona_comune(db, "Seleziona il comune per cui filtrare:")
                 # Continua anche se comune_id è None (nessun filtro comune)

             anno_i_str = input("Anno inizio (default 1900): ").strip() or "1900"
             anno_f_str = input("Anno fine (INVIO per corrente): ").strip()
             if not anno_i_str.isdigit() or (anno_f_str and not anno_f_str.isdigit()): print("Anni non validi."); continue
             anno_i = int(anno_i_str); anno_f = int(anno_f_str) if anno_f_str else None

             stats = db.get_cadastral_stats_by_period(comune_id, anno_i, anno_f) # Passa ID (o None)
             if stats:
                   # Assumiamo che la funzione SQL sia aggiornata per restituire comune_nome
                   print("\nAnno  | Comune           | Nuove P. | Chiuse P. | Tot Attive | Variazioni | Imm. Reg.")
                   print("------|------------------|----------|-----------|------------|------------|-----------")
                   for s in stats:
                       print(f" {s['anno']} | {s.get('comune_nome', 'Totale').ljust(16)} | "
                             f"{str(s.get('nuove_partite', 0)).rjust(8)} | {str(s.get('partite_chiuse', 0)).rjust(9)} | "
                             f"{str(s.get('totale_partite_attive', 0)).rjust(10)} | {str(s.get('variazioni', 0)).rjust(10)} | "
                             f"{str(s.get('immobili_registrati', 0)).rjust(9)}")
             else: print("Nessuna statistica trovata.")

        elif scelta == "7": # Collega Documento a Partita (invariato)
            stampa_intestazione("COLLEGA DOCUMENTO A PARTITA")
            doc_id_str = input("ID Documento Storico: ").strip(); part_id_str = input("ID Partita da collegare: ").strip()
            if not (doc_id_str.isdigit() and part_id_str.isdigit()): print("ID non validi."); continue
            doc_id = int(doc_id_str); part_id = int(part_id_str)
            print("Rilevanza: primaria, secondaria, correlata"); rilevanza = input("Inserisci rilevanza (default correlata): ").strip() or 'correlata'
            note = input("Note (opzionale): ").strip() or None
            if db.link_document_to_partita(doc_id, part_id, rilevanza, note): print("Collegamento creato/aggiornato.")
            else: print("Errore creazione collegamento (controllare log).")

        elif scelta == "8": break
        else: print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")


# --- Funzione Main (invariata) ---
def main():
    # Configurazione DB (!! USA PASSWORD SICURA IN PRODUZIONE !!)
    db_config = {
        "dbname": "catasto_storico", "user": "postgres", "password": "Markus74",
        "host": "localhost", "port": 5432, "schema": "catasto"
    }
    stampa_locandina_introduzione()
    # Usa il manager aggiornato
    db = CatastoDBManager(**db_config)

    if not db.connect():
        print("ERRORE CRITICO: Impossibile connettersi al database. Verifica i parametri e lo stato del server.")
        sys.exit(1)

    # Riferimento alle globali per il blocco finally
    global logged_in_user_id, current_session_id

    try:
        # Esegui il menu principale
        menu_principale(db)
    except KeyboardInterrupt:
        print("\nOperazione interrotta dall'utente.")
    except Exception as e:
        # Logga l'eccezione completa per debug
        logger.exception(f"Errore non gestito nel menu principale: {e}")
        print(f"ERRORE IMPREVISTO: {e}")
    finally:
        # Esegui logout se necessario prima di chiudere
        if logged_in_user_id and current_session_id and db.conn and not db.conn.closed:
             print("\nEsecuzione logout prima della chiusura...")
             db.logout_user(logged_in_user_id, current_session_id, client_ip_address)
        # Resetta le variabili globali (anche se l'app termina)
        logged_in_user_id = None
        current_session_id = None
        # Chiudi la connessione
        if db:
            db.disconnect()
        print("\nApplicazione terminata.")

# --- Avvio Script ---
if __name__ == "__main__":
    main()