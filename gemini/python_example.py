#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Esempio di utilizzo del gestore database catastale
=================================================
Questo script mostra esempi pratici di come utilizzare
la classe CatastoDBManager per interagire con il database,
includendo gestione utenti e audit.

Autore: Marco Santoro
Data: 25/04/2025 (Versione completa e aggiornata 1.3)
"""

from catasto_db_manager import CatastoDBManager # Assicurati che catasto_db_manager.py sia nello stesso percorso o nel PYTHONPATH
from datetime import date, datetime
import json
import os
import sys
import hashlib
import getpass # Per nascondere input password
import logging # Aggiungi questa riga vicino agli altri import
import bcrypt # Aggiungi questo import all'inizio del file
from typing import Optional, List, Dict, Any # Aggiunto per type hinting

# --- Logger (assicurati che sia definito, es. logger = logging.getLogger(__name__)) ---
# Se non è già definito globalmente, ottienilo:
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
    versione = "1.3" # Versione aggiornata
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
     """Funzione helper per hashare la password. USARE BCRYPT IN PRODUZIONE!"""
     # Esempio con SHA256 (NON SICURO PER PASSWORD REALI)
     return hashlib.sha256(password.encode('utf-8')).hexdigest()

def _verify_password(stored_hash: str, provided_password: str) -> bool:
     """Funzione helper per verificare la password. USARE BCRYPT IN PRODUZIONE!"""
     # Esempio con SHA256
     return stored_hash == _hash_password(provided_password)

def _set_session_context(db: CatastoDBManager):
     """Imposta il contesto utente nel DB se loggato per l'audit."""
     global logged_in_user_id
     if logged_in_user_id:
          # Imposta le variabili di sessione PostgreSQL
          db.set_session_app_user(logged_in_user_id, client_ip_address)
     else:
          # Assicura che il contesto sia pulito se non c'è utente
          db.clear_session_app_user()

def _confirm_action(prompt: str) -> bool:
     """Chiede conferma all'utente."""
     return input(f"{prompt} (s/n)? ").strip().lower() == 's'

def _hash_password(password: str) -> str:
    """Funzione helper per hashare la password usando bcrypt."""
    # Genera il sale e crea l'hash
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    # Ritorna l'hash come stringa decodificata per salvarlo nel DB (VARCHAR)
    return hashed_bytes.decode('utf-8')

def _verify_password(stored_hash: str, provided_password: str) -> bool:
    """Funzione helper per verificare la password usando bcrypt."""
    try:
        stored_hash_bytes = stored_hash.encode('utf-8')
        provided_password_bytes = provided_password.encode('utf-8')
        # Confronta la password fornita con l'hash memorizzato
        return bcrypt.checkpw(provided_password_bytes, stored_hash_bytes)
    except ValueError:
        # Questo errore può verificarsi se stored_hash non è un hash bcrypt valido
        logger.error(f"Tentativo di verifica con hash non valido: {stored_hash[:10]}...")
        return False
    except Exception as e:
        logger.error(f"Errore imprevisto durante la verifica bcrypt: {e}")
        return False

# --- Funzioni di Inserimento Dati (Componenti dei Menu) ---

def inserisci_possessore(db: CatastoDBManager, comune_preselezionato: Optional[str] = None) -> Optional[int]:
    """Funzione interattiva per inserire un nuovo possessore."""
    _set_session_context(db) # Imposta contesto prima dell'operazione
    stampa_intestazione("AGGIUNGI NUOVO POSSESSORE")

    if comune_preselezionato:
        comune = comune_preselezionato
        print(f"Comune: {comune}")
    else:
        comune = input("Comune: ").strip()
        if not comune:
             print("Comune obbligatorio.")
             return None

    cognome_nome = input("Cognome e nome: ").strip()
    paternita = input("Paternita (es. 'fu Roberto'): ").strip()
    nome_completo = f"{cognome_nome} {paternita}".strip()
    conferma = input(f"Nome completo calcolato: [{nome_completo}]\nPremi INVIO per confermare o inserisci valore diverso: ").strip()
    if conferma:
        nome_completo = conferma

    if comune and cognome_nome and nome_completo:
        possessore_id = db.insert_possessore(comune, cognome_nome, paternita, nome_completo, True)
        if possessore_id:
            print(f"Possessore '{nome_completo}' inserito con successo (ID: {possessore_id})")
            return possessore_id
        else:
            print("Errore durante l'inserimento del possessore (controllare log).")
    else:
        print("Dati incompleti, operazione annullata.")
    return None

def inserisci_localita(db: CatastoDBManager) -> Optional[int]:
    """Funzione interattiva per inserire una nuova località."""
    _set_session_context(db) # Imposta contesto prima dell'operazione
    stampa_intestazione("AGGIUNGI NUOVA LOCALITA")

    comune = input("Comune: ").strip()
    nome = input("Nome localita: ").strip()
    if not comune or not nome:
        print("Dati incompleti, operazione annullata.")
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
        civico_input = input("Numero civico (opzionale): ").strip()
        if civico_input.isdigit():
            civico = int(civico_input)

    # insert_localita nel manager gestisce ON CONFLICT e ritorna l'ID esistente o nuovo
    localita_id = db.insert_localita(comune, nome, tipo, civico)
    if localita_id:
        print(f"Localita '{nome}' ({tipo}) inserita/trovata con ID: {localita_id}")
        return localita_id
    else:
        print("Errore durante l'inserimento/recupero della localita (controllare log).")
        return None

def aggiungi_comune(db: CatastoDBManager):
    """Funzione interattiva per inserire un nuovo comune."""
    _set_session_context(db) # Imposta contesto prima dell'operazione
    stampa_intestazione("AGGIUNGI NUOVO COMUNE")
    nome = input("Nome comune: ").strip()
    provincia = input("Provincia: ").strip()
    regione = input("Regione: ").strip()

    if not (nome and provincia and regione):
        print("Dati incompleti, operazione annullata")
        return

    periodo_id = None
    periodi = db.get_historical_periods()
    if periodi:
        print("\nSeleziona il periodo storico di riferimento:")
        for i, p in enumerate(periodi, 1):
            fine = p.get('anno_fine') or 'presente'
            print(f"{i}. {p['nome']} ({p['anno_inizio']}-{fine}) - ID: {p['id']}")

        default_periodo_id = next((p['id'] for p in periodi if p['nome'] == 'Repubblica Italiana'), periodi[-1]['id'] if periodi else None)
        scelta = input(f"Numero periodo (INVIO per default - ID {default_periodo_id}): ").strip()

        if scelta.isdigit() and 1 <= int(scelta) <= len(periodi):
            periodo_id = periodi[int(scelta) - 1]['id']
        elif not scelta and default_periodo_id:
            periodo_id = default_periodo_id
        else:
            print("Selezione periodo non valida, usando default se possibile.")
            periodo_id = default_periodo_id
    else:
        print("Nessun periodo storico trovato. Impossibile procedere.")
        return

    if periodo_id is None:
        print("ID Periodo storico non valido. Operazione annullata.")
        return

    # La gestione ON CONFLICT è fatta nel DB
    query = "INSERT INTO comune (nome, provincia, regione, periodo_id) VALUES (%s, %s, %s, %s) ON CONFLICT (nome) DO NOTHING"
    if db.execute_query(query, (nome, provincia, regione, periodo_id)):
        # Verifica se l'inserimento ha avuto effetto
        if db.execute_query("SELECT 1 FROM comune WHERE nome = %s", (nome,)) and db.fetchone():
            db.commit()
            print(f"Comune '{nome}' inserito/esistente con successo.")
        else:
            print("Errore: Comune non trovato dopo tentativo di inserimento (potrebbe essere un conflitto gestito con DO NOTHING).")
            # Non serve rollback se DO NOTHING
    else:
        print("Errore durante l'inserimento del comune.")
        # Rollback gestito in execute_query


# Inserisci questa funzione in python_example.py dopo l'import
# e prima della definizione di menu_consultazione

def _esporta_entita_json(db: CatastoDBManager, tipo_entita: str, etichetta_id: str, nome_file_prefix: str):
    """
    Funzione generica per esportare un'entità (partita o possessore) in formato JSON.

    Args:
        db: Istanza di CatastoDBManager.
        tipo_entita: Tipo di entità ('partita' o 'possessore').
        etichetta_id: Etichetta da usare nel prompt per l'ID (es. "ID della Partita").
        nome_file_prefix: Prefisso per il nome del file di output (es. "partita").
    """
    stampa_intestazione(f"ESPORTA {tipo_entita.upper()} IN JSON")
    id_entita_str = input(f"{etichetta_id} da esportare: ").strip()

    if not id_entita_str.isdigit():
        print("ID non valido.")
        return

    entita_id = int(id_entita_str)
    json_data_str = None

    try:
        if tipo_entita == 'partita':
            json_data_str = db.export_partita_json(entita_id)
        elif tipo_entita == 'possessore':
            json_data_str = db.export_possessore_json(entita_id)
        else:
            print(f"Tipo entità '{tipo_entita}' non supportato per l'esportazione.")
            return

        if json_data_str:
            print(f"\n--- DATI JSON {tipo_entita.upper()} ---")
            print(json_data_str)
            print("-" * (len(tipo_entita) + 16)) # Adatta la lunghezza della linea
            filename = f"{nome_file_prefix}_{entita_id}.json"
            if _confirm_action(f"Salvare in '{filename}'"):
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(json_data_str)
                    print(f"Dati salvati in {filename}")
                except Exception as e:
                    print(f"Errore nel salvataggio del file: {e}")
        else:
            print(f"{tipo_entita.capitalize()} non trovato/a o errore durante l'esportazione.")

    except Exception as e:
        # Logga l'errore se necessario, o gestiscilo diversamente
        print(f"Si è verificato un errore durante l'esportazione: {e}")


def menu_principale(db: CatastoDBManager):
    """Menu principale dell'applicazione."""
    global logged_in_user_id, current_session_id

    while True:
        stampa_intestazione("MENU PRINCIPALE")
        if logged_in_user_id:
             print(f"--- Utente connesso: ID {logged_in_user_id} (Sessione: {current_session_id[:8]}...) ---")
        else:
             print("--- Nessun utente connesso ---")

        print("1. Consultazione dati")
        print("2. Inserimento e gestione dati")
        print("3. Generazione report")
        print("4. Manutenzione database")
        print("5. Sistema di audit")
        print("6. Gestione Utenti e Sessione")
        print("7. Sistema di Backup")
        print("8. Funzionalità Storiche Avanzate")
        print("9. Esci")

        scelta = input("\nSeleziona un'opzione (1-9): ").strip()

        # Imposta contesto PRIMA di entrare nei sottomenu
        _set_session_context(db)

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
                 print("Logout automatico prima dell'uscita...")
                 db.logout_user(logged_in_user_id, current_session_id, client_ip_address)
                 logged_in_user_id = None
                 current_session_id = None
            break
        else:
            print("Opzione non valida!")

# --- Menu Consultazione ---

def menu_consultazione(db: CatastoDBManager):
    """Menu per operazioni di consultazione dati."""
    # Le operazioni di sola lettura non necessitano di contesto sessione per l'audit
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
        print("14. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-14): ").strip()

        if scelta == "1":
            search_term = input("Termine di ricerca comune (lascia vuoto per tutti): ").strip()
            comuni = db.get_comuni(search_term or None)
            stampa_intestazione(f"COMUNI TROVATI ({len(comuni)})")
            if comuni:
                for c in comuni: print(f"- {c['nome']} ({c['provincia']}, {c['regione']})")
            else: print("Nessun comune trovato.")

        elif scelta == "2":
            comune = input("Nome comune per elenco partite (esatto): ").strip()
            if comune:
                partite = db.get_partite_by_comune(comune)
                stampa_intestazione(f"PARTITE DI {comune.upper()} ({len(partite)})")
                if partite:
                    for p in partite:
                        stato = p['stato'].upper()
                        possessori_str = p.get('possessori', 'N/D') or 'Nessuno'
                        print(f"ID: {p['id']} - N.{p['numero_partita']} ({p['tipo']}) - Stato: {stato}")
                        print(f"  Possessori: {possessori_str}")
                        print(f"  Num. Immobili: {p.get('num_immobili', 0)}")
                        print("-" * 20)
                else: print("Nessuna partita trovata.")
            else: print("Nome comune obbligatorio.")

        elif scelta == "3":
            comune = input("Nome comune per elenco possessori (esatto): ").strip()
            if comune:
                possessori = db.get_possessori_by_comune(comune)
                stampa_intestazione(f"POSSESSORI DI {comune.upper()} ({len(possessori)})")
                if possessori:
                    for p in possessori:
                        stato = "Attivo" if p.get('attivo') else "Non Attivo"
                        print(f"ID: {p['id']} - {p['nome_completo']} - Stato: {stato}")
                else: print("Nessun possessore trovato.")
            else: print("Nome comune obbligatorio.")

        elif scelta == "4":
            stampa_intestazione("RICERCA PARTITE (SEMPLICE)")
            comune = input("Comune (anche parziale): ").strip()
            numero_str = input("Numero partita (esatto): ").strip()
            possessore = input("Nome possessore (anche parziale): ").strip()
            natura = input("Natura immobile (anche parziale): ").strip()
            numero_partita = int(numero_str) if numero_str.isdigit() else None

            partite = db.search_partite(
                comune_nome=comune or None,
                numero_partita=numero_partita,
                possessore=possessore or None,
                immobile_natura=natura or None
            )
            stampa_intestazione(f"RISULTATI RICERCA PARTITE ({len(partite)})")
            if partite:
                for p in partite:
                    print(f"ID: {p['id']} - {p['comune_nome']} - Partita N.{p['numero_partita']} ({p['tipo']}) - Stato: {p['stato']}")
            else: print("Nessuna partita trovata con questi criteri.")

        elif scelta == "5":
            id_partita_str = input("ID della partita per dettagli: ").strip()
            if id_partita_str.isdigit():
                partita_id = int(id_partita_str)
                partita = db.get_partita_details(partita_id)
                if partita:
                    stampa_intestazione(f"DETTAGLI PARTITA N.{partita['numero_partita']} ({partita['comune_nome']})")
                    print(f"ID: {partita['id']} - Tipo: {partita['tipo']} - Stato: {partita['stato']}")
                    print(f"Data Impianto: {partita['data_impianto']} - Data Chiusura: {partita.get('data_chiusura') or 'N/D'}")

                    print("\nPOSSESSORI:")
                    if partita.get('possessori'):
                        for pos in partita['possessori']:
                            quota_str = f" (Quota: {pos.get('quota')})" if pos.get('quota') else ""
                            print(f"- ID:{pos['id']} {pos['nome_completo']}{quota_str}")
                    else: print("  Nessuno")

                    print("\nIMMOBILI:")
                    if partita.get('immobili'):
                        for imm in partita['immobili']:
                            loc_str = f"{imm['localita_nome']}"
                            if imm.get('civico'): loc_str += f", {imm['civico']}"
                            loc_str += f" ({imm['localita_tipo']})"
                            print(f"- ID:{imm['id']} {imm['natura']} in {loc_str}")
                            print(f"  Class: {imm.get('classificazione') or 'N/D'} - Cons: {imm.get('consistenza') or 'N/D'} - Piani: {imm.get('numero_piani') or 'N/D'} - Vani: {imm.get('numero_vani') or 'N/D'}")
                    else: print("  Nessuno")

                    print("\nVARIAZIONI:")
                    if partita.get('variazioni'):
                        for var in partita['variazioni']:
                             dest_partita_str = f" -> Partita Dest. ID {var.get('partita_destinazione_id')}" if var.get('partita_destinazione_id') else ""
                             print(f"- ID:{var['id']} Tipo:{var['tipo']} Data:{var['data_variazione']}{dest_partita_str}")
                             if var.get('tipo_contratto'):
                                  print(f"  Contratto: {var['tipo_contratto']} del {var['data_contratto']} (Notaio: {var.get('notaio') or 'N/D'}, Rep: {var.get('repertorio') or 'N/D'})")
                             if var.get('note'): print(f"  Note Variazione: {var['note']}")
                    else: print("  Nessuna")
                else: print(f"Partita con ID {id_partita_str} non trovata.")
            else: print("ID partita non valido.")

        elif scelta == "6":
             comune = input("Nome comune per elenco località (esatto): ").strip()
             if comune:
                 query = "SELECT id, nome, tipo, civico FROM localita WHERE comune_nome = %s ORDER BY tipo, nome, civico"
                 if db.execute_query(query, (comune,)):
                      localita = db.fetchall()
                      stampa_intestazione(f"LOCALITÀ DI {comune.upper()} ({len(localita)})")
                      if localita:
                           for loc in localita:
                                civ_str = f", civico {loc['civico']}" if loc['civico'] is not None else ""
                                print(f"ID: {loc['id']} - {loc['nome']} ({loc['tipo']}){civ_str}")
                      else: print("Nessuna località trovata.")
                 else: print("Errore nella ricerca delle località.")
             else: print("Nome comune obbligatorio.")

        elif scelta == "7":
             stampa_intestazione("RICERCA AVANZATA POSSESSORI (Similarità)")
             query_text = input("Termine di ricerca (nome/cognome/paternità): ").strip()
             if query_text:
                  results = db.ricerca_avanzata_possessori(query_text)
                  if results:
                       print(f"\nTrovati {len(results)} risultati (ordinati per similarità):")
                       for r in results:
                            sim_perc = round(r.get('similarity', 0) * 100, 1)
                            print(f"- ID: {r['id']} {r['nome_completo']} ({r['comune_nome']})")
                            print(f"  Similarità: {sim_perc}% - Partite: {r.get('num_partite', 0)}")
                  else: print("Nessun risultato trovato.")
             else: print("Termine di ricerca obbligatorio.")

        elif scelta == "8":
             stampa_intestazione("RICERCA AVANZATA IMMOBILI")
             comune = input("Comune (vuoto per tutti): ").strip() or None
             natura = input("Natura Immobile (parziale, vuoto per tutti): ").strip() or None
             localita = input("Località (parziale, vuoto per tutti): ").strip() or None
             classif = input("Classificazione (esatta, vuoto per tutti): ").strip() or None
             possessore = input("Possessore (parziale, vuoto per tutti): ").strip() or None
             results = db.ricerca_avanzata_immobili(comune, natura, localita, classif, possessore)
             if results:
                  print(f"\nTrovati {len(results)} immobili:")
                  for r in results:
                       print(f"- Imm.ID: {r['immobile_id']} - {r['natura']} in {r['localita_nome']} ({r['comune']})")
                       print(f"  Partita N.{r['partita_numero']} - Class: {r.get('classificazione') or 'N/D'}")
                       print(f"  Possessori: {r.get('possessori') or 'N/D'}")
             else: print("Nessun immobile trovato.")

        elif scelta == "9":
             stampa_intestazione("CERCA IMMOBILI SPECIFICI")
             part_id_str = input("Filtra per ID Partita (vuoto per non filtrare): ").strip()
             comune = input("Filtra per Comune (esatto, vuoto per non filtrare): ").strip() or None
             loc_id_str = input("Filtra per ID Località (vuoto per non filtrare): ").strip()
             natura = input("Filtra per Natura (parziale, vuoto per non filtrare): ").strip() or None
             classif = input("Filtra per Classificazione (esatta, vuoto per non filtrare): ").strip() or None
             try:
                  part_id = int(part_id_str) if part_id_str else None
                  loc_id = int(loc_id_str) if loc_id_str else None
                  immobili = db.search_immobili(part_id, comune, loc_id, natura, classif)
                  if immobili:
                       print(f"\nTrovati {len(immobili)} immobili:")
                       for imm in immobili:
                            print(f"- ID: {imm['id']}, Nat:{imm['natura']}, Loc:{imm['localita_nome']} ({imm['comune_nome']}), Part:{imm['numero_partita']}, Class:{imm.get('classificazione','-')}")
                  else: print("Nessun immobile trovato.")
             except ValueError: print("ID non valido.")

        elif scelta == "10":
             stampa_intestazione("CERCA VARIAZIONI")
             tipo = input("Tipo (Acquisto/Successione/..., vuoto per tutti): ").strip().capitalize() or None
             data_i_str = input("Data inizio (YYYY-MM-DD, vuoto per non filtrare): ").strip()
             data_f_str = input("Data fine (YYYY-MM-DD, vuoto per non filtrare): ").strip()
             part_o_id_str = input("ID Partita Origine (vuoto per non filtrare): ").strip()
             part_d_id_str = input("ID Partita Destinazione (vuoto per non filtrare): ").strip()
             comune = input("Comune Origine (esatto, vuoto per non filtrare): ").strip() or None
             try:
                  data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date() if data_i_str else None
                  data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date() if data_f_str else None
                  part_o_id = int(part_o_id_str) if part_o_id_str else None
                  part_d_id = int(part_d_id_str) if part_d_id_str else None
                  variazioni = db.search_variazioni(tipo, data_i, data_f, part_o_id, part_d_id, comune)
                  if variazioni:
                       print(f"\nTrovate {len(variazioni)} variazioni:")
                       for v in variazioni:
                            dest_str = f" -> {v.get('partita_destinazione_numero', '-')}" if v.get('partita_destinazione_id') else ""
                            print(f"- ID:{v['id']} {v['data_variazione']} {v['tipo']} Partita:{v['partita_origine_numero']}({v['comune_nome']}){dest_str} Rif:{v.get('numero_riferimento') or '-'}/{v.get('nominativo_riferimento') or '-'}")
                  else: print("Nessuna variazione trovata.")
             except ValueError: print("Input ID o Data non validi.")

        elif scelta == "11":
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

        # --- MODIFICA QUI ---
        elif scelta == "12":
            _esporta_entita_json(db,
                                 tipo_entita='partita',
                                 etichetta_id='ID della Partita',
                                 nome_file_prefix='partita')

        elif scelta == "13":
            _esporta_entita_json(db,
                                 tipo_entita='possessore',
                                 etichetta_id='ID del Possessore',
                                 nome_file_prefix='possessore')
        # --- FINE MODIFICA ---

        elif scelta == "14":
             break
        else:
             print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Inserimento ---

def menu_inserimento(db: CatastoDBManager):
    """Menu per operazioni di inserimento e gestione dati."""
    while True:
        stampa_intestazione("INSERIMENTO E GESTIONE DATI")
        print("1. Aggiungi nuovo comune")
        print("2. Aggiungi nuovo possessore")
        print("3. Aggiungi nuova localita")
        print("4. Registra nuova proprieta (Workflow completo)")
        print("5. Registra passaggio di proprieta (Workflow completo)")
        print("6. Registra consultazione")
        print("7. Inserisci Contratto per Variazione")
        print("8. Duplica Partita")
        print("9. Trasferisci Immobile a Nuova Partita")
        print("10. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-10): ").strip()

        # Imposta contesto sessione PRIMA di eseguire l'azione scelta
        _set_session_context(db)

        if scelta == "1": aggiungi_comune(db)
        elif scelta == "2": inserisci_possessore(db)
        elif scelta == "3": inserisci_localita(db)
        elif scelta == "4": _registra_nuova_proprieta_interattivo(db)
        elif scelta == "5": _registra_passaggio_proprieta_interattivo(db)
        elif scelta == "6": _registra_consultazione_interattivo(db)
        elif scelta == "7": _inserisci_contratto_interattivo(db)
        elif scelta == "8": _duplica_partita_interattivo(db)
        elif scelta == "9": _trasferisci_immobile_interattivo(db)
        elif scelta == "10": break
        else: print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Funzioni Helper per menu_inserimento ---
# (Implementazioni dettagliate per _registra_nuova_proprieta_interattivo, etc.)
# Queste funzioni usano input() per raccogliere dati dall'utente

def _registra_nuova_proprieta_interattivo(db: CatastoDBManager):
     """Guida l'utente nell'inserimento di una nuova proprietà."""
     stampa_intestazione("REGISTRA NUOVA PROPRIETA")
     comune = input("Comune: ").strip()
     num_partita_str = input("Numero nuova partita: ").strip()
     data_imp_str = input("Data impianto (YYYY-MM-DD): ").strip()

     if not comune or not num_partita_str.isdigit() or not data_imp_str:
          print("Comune, numero partita e data impianto sono obbligatori.")
          return
     try:
          numero_partita = int(num_partita_str)
          data_impianto = datetime.strptime(data_imp_str, "%Y-%m-%d").date()
     except ValueError:
          print("Formato numero partita o data non valido.")
          return

     possessori = []
     print("\n--- Inserimento Possessori ---")
     while True:
          nome_completo = input("Nome completo possessore (o INVIO per terminare): ").strip()
          if not nome_completo: break
          possessore_id_esistente = db.check_possessore_exists(nome_completo, comune)
          dati_possessore = {"nome_completo": nome_completo}
          if possessore_id_esistente:
               print(f"  -> Trovato possessore esistente ID: {possessore_id_esistente}")
          else:
               print("  -> Nuovo possessore. Inserisci dettagli:")
               dati_possessore["cognome_nome"] = input("     Cognome e Nome: ").strip()
               dati_possessore["paternita"] = input("     Paternità: ").strip()
               if not dati_possessore["cognome_nome"]: print("Cognome e Nome obbligatori."); continue
          quota = input(f"  Quota per {nome_completo} (es. 1/2, vuoto per esclusiva): ").strip()
          if quota: dati_possessore["quota"] = quota
          possessori.append(dati_possessore)
     if not possessori: print("È necessario almeno un possessore."); return

     immobili = []
     print("\n--- Inserimento Immobili ---")
     while True:
          natura = input("Natura immobile (es. Casa, o INVIO per terminare): ").strip()
          if not natura: break
          localita_nome = input("  Nome località: ").strip()
          if not localita_nome: print("Nome località obbligatorio."); continue
          # Prova a inserire/trovare località (assume tipo 'via' se non specificato)
          # Migliorabile chiedendo il tipo all'utente
          localita_id = db.insert_localita(comune, localita_nome, 'via')
          if not localita_id: print(f"Errore gestione località '{localita_nome}'."); continue

          dati_immobile = {
               "natura": natura, "localita_id": localita_id,
               "classificazione": input("  Classificazione: ").strip() or None,
               "numero_piani": None, "numero_vani": None,
               "consistenza": input("  Consistenza (es. 120 mq): ").strip() or None
          }
          piani_str = input("  Numero Piani (solo numero): ").strip()
          if piani_str.isdigit(): dati_immobile["numero_piani"] = int(piani_str)
          vani_str = input("  Numero Vani (solo numero): ").strip()
          if vani_str.isdigit(): dati_immobile["numero_vani"] = int(vani_str)

          immobili.append(dati_immobile)
     if not immobili: print("È necessario almeno un immobile."); return

     print("\nRiepilogo:")
     print(f"Comune: {comune}, Partita N.{numero_partita}, Data: {data_impianto}")
     print(f"Possessori: {len(possessori)}")
     for p in possessori: print(f"  - {p['nome_completo']} {'(Quota: ' + p['quota'] + ')' if 'quota' in p else ''}")
     print(f"Immobili: {len(immobili)}")
     for i in immobili: print(f"  - {i['natura']} (Loc. ID: {i['localita_id']})")

     if _confirm_action("Procedere con la registrazione?"):
          if db.registra_nuova_proprieta(comune, numero_partita, data_impianto, possessori, immobili):
               print("Nuova proprietà registrata con successo.")
          else:
               print("Errore durante la registrazione della nuova proprietà (controllare log).")

def _registra_passaggio_proprieta_interattivo(db: CatastoDBManager):
     """Guida l'utente nella registrazione di un passaggio di proprietà."""
     stampa_intestazione("REGISTRA PASSAGGIO DI PROPRIETA")
     id_orig_str = input("ID Partita di Origine: ").strip()
     if not id_orig_str.isdigit(): print("ID non valido."); return
     partita_origine_id = int(id_orig_str)

     partita_orig = db.get_partita_details(partita_origine_id)
     if not partita_orig: print(f"Partita origine ID {partita_origine_id} non trovata."); return
     if partita_orig['stato'] == 'inattiva': print("La partita di origine è già inattiva."); return
     print(f"Partita Origine: N.{partita_orig['numero_partita']} ({partita_orig['comune_nome']})")

     comune_dest = input(f"Comune nuova partita (INVIO per '{partita_orig['comune_nome']}'): ").strip() or partita_orig['comune_nome']
     num_part_dest_str = input("Numero nuova partita: ").strip()
     if not num_part_dest_str.isdigit(): print("Numero partita non valido."); return
     numero_partita_dest = int(num_part_dest_str)

     tipo_var = input("Tipo Variazione (es. Vendita, Successione): ").strip().capitalize()
     data_var_str = input("Data Variazione (YYYY-MM-DD): ").strip()
     tipo_contr = input("Tipo Contratto associato (es. Vendita, Successione): ").strip().capitalize()
     data_contr_str = input("Data Contratto (YYYY-MM-DD): ").strip()
     if not tipo_var or not data_var_str or not tipo_contr or not data_contr_str:
          print("Tipo/Data Variazione e Tipo/Data Contratto obbligatori."); return
     try:
          data_variazione = datetime.strptime(data_var_str, "%Y-%m-%d").date()
          data_contratto = datetime.strptime(data_contr_str, "%Y-%m-%d").date()
     except ValueError: print("Formato data non valido."); return

     notaio = input("Notaio (opzionale): ").strip() or None
     repertorio = input("Repertorio (opzionale): ").strip() or None
     note_var = input("Note variazione (opzionale): ").strip() or None

     nuovi_possessori_list = []
     if _confirm_action("Specificare nuovi possessori per la nuova partita (altrimenti verranno copiati)?"):
         print("\n--- Inserimento Nuovi Possessori ---")
         while True:
             nome_completo = input("Nome completo possessore (o INVIO per terminare): ").strip()
             if not nome_completo: break
             dati_poss = {"nome_completo": nome_completo}
             if not db.check_possessore_exists(nome_completo, comune_dest):
                  print("  -> Nuovo possessore:")
                  dati_poss["cognome_nome"] = input("     Cognome e Nome: ").strip()
                  dati_poss["paternita"] = input("     Paternità: ").strip()
                  if not dati_poss["cognome_nome"]: print("Cognome e Nome obbligatori."); continue
             quota = input(f"  Quota per {nome_completo} (vuoto per esclusiva): ").strip()
             if quota: dati_poss["quota"] = quota
             nuovi_possessori_list.append(dati_poss)

     immobili_da_trasferire_list = None
     if _confirm_action("Specificare quali immobili trasferire (altrimenti tutti)?"):
          immobili_da_trasferire_list = []
          print("\n--- Selezione Immobili da Trasferire ---")
          if partita_orig.get('immobili'):
               print("Immobili nella partita di origine:")
               for imm in partita_orig['immobili']: print(f"  ID: {imm['id']} - {imm['natura']}")
               while True:
                    id_imm_str = input("Inserisci ID immobile da trasferire (o INVIO per terminare): ").strip()
                    if not id_imm_str: break
                    if id_imm_str.isdigit() and any(imm['id'] == int(id_imm_str) for imm in partita_orig['immobili']):
                         immobili_da_trasferire_list.append(int(id_imm_str))
                         print(f"  -> Aggiunto immobile ID {id_imm_str}")
                    else: print("  ID non valido o non presente nella partita origine.")
          else: print("  Nessun immobile trovato nella partita origine.")

     print("\nRiepilogo Passaggio:")
     print(f"Da Partita ID {partita_origine_id} a N.{numero_partita_dest} ({comune_dest})")
     print(f"Variazione: {tipo_var} del {data_variazione}")
     print(f"Contratto: {tipo_contr} del {data_contratto}")
     print(f"Nuovi Possessori: {'Specificati' if nuovi_possessori_list else 'Copiati dall origine'}")
     print(f"Immobili: {'Selezionati' if immobili_da_trasferire_list is not None else 'Tutti'}")

     if _confirm_action("Procedere con la registrazione del passaggio?"):
          if db.registra_passaggio_proprieta(
               partita_origine_id, comune_dest, numero_partita_dest, tipo_var, data_variazione,
               tipo_contr, data_contratto, notaio=notaio, repertorio=repertorio,
               nuovi_possessori=nuovi_possessori_list or None,
               immobili_da_trasferire=immobili_da_trasferire_list,
               note=note_var
          ):
               print("Passaggio di proprietà registrato con successo.")
          else:
               print("Errore durante la registrazione del passaggio (controllare log).")

def _registra_consultazione_interattivo(db: CatastoDBManager):
     """Guida l'utente nella registrazione di una consultazione."""
     stampa_intestazione("REGISTRA CONSULTAZIONE")
     data_str = input("Data consultazione (YYYY-MM-DD, INVIO per oggi): ").strip()
     richiedente = input("Richiedente: ").strip()
     doc_id = input("Documento Identità (opzionale): ").strip() or None
     motivazione = input("Motivazione (opzionale): ").strip() or None
     materiale = input("Materiale Consultato: ").strip()
     funzionario = input("Funzionario Autorizzante: ").strip()

     if not richiedente or not materiale or not funzionario:
          print("Richiedente, Materiale e Funzionario sono obbligatori.")
          return
     try:
          data_cons = datetime.strptime(data_str, "%Y-%m-%d").date() if data_str else date.today()
     except ValueError:
          print("Formato data non valido.")
          return

     if db.registra_consultazione(data_cons, richiedente, doc_id, motivazione, materiale, funzionario):
          print("Consultazione registrata con successo.")
     else:
          print("Errore durante la registrazione della consultazione (controllare log).")

def _inserisci_contratto_interattivo(db: CatastoDBManager):
     """Guida l'utente nell'inserimento di un contratto."""
     stampa_intestazione("INSERISCI CONTRATTO PER VARIAZIONE")
     var_id_str = input("ID della Variazione a cui collegare il contratto: ").strip()
     if not var_id_str.isdigit(): print("ID Variazione non valido."); return
     var_id = int(var_id_str)

     # Verifica esistenza variazione
     if not db.execute_query("SELECT 1 FROM variazione WHERE id = %s", (var_id,)) or not db.fetchone():
          print(f"Variazione ID {var_id} non trovata."); return

     tipo_contr = input("Tipo Contratto (es. Vendita, Successione): ").strip().capitalize()
     data_contr_str = input("Data Contratto (YYYY-MM-DD): ").strip()
     if not tipo_contr or not data_contr_str: print("Tipo e Data contratto obbligatori."); return
     try:
          data_contr = datetime.strptime(data_contr_str, "%Y-%m-%d").date()
     except ValueError: print("Formato data non valido."); return

     notaio = input("Notaio (opzionale): ").strip() or None
     repertorio = input("Repertorio (opzionale): ").strip() or None
     note = input("Note Contratto (opzionale): ").strip() or None

     if db.insert_contratto(var_id, tipo_contr, data_contr, notaio, repertorio, note):
          print(f"Contratto inserito con successo per Variazione ID {var_id}.")
     else:
          print("Errore durante l'inserimento del contratto (controllare log).")

def _duplica_partita_interattivo(db: CatastoDBManager):
     """Guida l'utente nella duplicazione di una partita."""
     stampa_intestazione("DUPLICA PARTITA")
     id_orig_str = input("ID Partita da duplicare: ").strip()
     if not id_orig_str.isdigit(): print("ID non valido."); return
     partita_id_orig = int(id_orig_str)

     partita_orig = db.get_partita_details(partita_id_orig)
     if not partita_orig: print(f"Partita ID {partita_id_orig} non trovata."); return
     print(f"Partita da duplicare: N.{partita_orig['numero_partita']} ({partita_orig['comune_nome']})")

     nuovo_num_str = input("Nuovo numero per la partita duplicata: ").strip()
     if not nuovo_num_str.isdigit(): print("Numero non valido."); return
     nuovo_num = int(nuovo_num_str)

     mant_poss = _confirm_action("Mantenere gli stessi possessori?")
     mant_imm = _confirm_action("Mantenere gli stessi immobili?")

     if _confirm_action(f"Duplicare Partita ID {partita_id_orig} in N.{nuovo_num}?"):
          if db.duplicate_partita(partita_id_orig, nuovo_num, mant_poss, mant_imm):
               print("Partita duplicata con successo.")
          else:
               print("Errore durante la duplicazione (controllare log).")

def _trasferisci_immobile_interattivo(db: CatastoDBManager):
     """Guida l'utente nel trasferimento di un immobile."""
     stampa_intestazione("TRASFERISCI IMMOBILE")
     imm_id_str = input("ID Immobile da trasferire: ").strip()
     if not imm_id_str.isdigit(): print("ID Immobile non valido."); return
     immobile_id = int(imm_id_str)

     # Verifica esistenza immobile e ottieni partita corrente
     if not db.execute_query("SELECT partita_id FROM immobile WHERE id = %s", (immobile_id,)):
          print(f"Errore verifica Immobile ID {immobile_id}."); return
     imm_info = db.fetchone()
     if not imm_info: print(f"Immobile ID {immobile_id} non trovato."); return
     print(f"Immobile ID {immobile_id} appartiene attualmente a Partita ID {imm_info['partita_id']}")

     part_dest_id_str = input("ID Partita di destinazione: ").strip()
     if not part_dest_id_str.isdigit(): print("ID Partita Destinazione non valido."); return
     partita_dest_id = int(part_dest_id_str)
     if partita_dest_id == imm_info['partita_id']: print("Impossibile trasferire immobile alla stessa partita."); return

     # Verifica esistenza e stato partita destinazione
     if not db.execute_query("SELECT stato FROM partita WHERE id = %s", (partita_dest_id,)):
          print(f"Errore verifica Partita Destinazione ID {partita_dest_id}."); return
     part_dest = db.fetchone()
     if not part_dest: print(f"Partita Destinazione ID {partita_dest_id} non trovata."); return
     if part_dest['stato'] != 'attiva': print("La partita di destinazione non è attiva."); return

     reg_var = _confirm_action("Registrare una variazione per questo trasferimento?")

     if _confirm_action(f"Trasferire Immobile ID {immobile_id} a Partita ID {partita_dest_id}?"):
          if db.transfer_immobile(immobile_id, partita_dest_id, reg_var):
               print("Immobile trasferito con successo.")
          else:
               print("Errore durante il trasferimento (controllare log).")

# --- Menu Report ---

def menu_report(db: CatastoDBManager):
    """Menu per la generazione di report."""
    while True:
        stampa_intestazione("GENERAZIONE REPORT")
        print("1. Certificato di proprieta")
        print("2. Report genealogico")
        print("3. Report possessore")
        print("4. Report consultazioni")
        print("5. Statistiche per comune (Vista Materializzata)")
        print("6. Riepilogo immobili per tipologia (Vista Materializzata)")
        print("7. Visualizza Partite Complete (Vista Materializzata)")
        print("8. Cronologia Variazioni (Vista Materializzata)")
        print("9. Report Annuale Partite per Comune (Funzione)")
        print("10. Report Proprietà Possessore per Periodo (Funzione)")
        print("11. Report Statistico Comune")
        print("12. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-12): ").strip()

        if scelta == "1":
            partita_id_str = input("Inserisci l'ID della partita: ").strip()
            if partita_id_str.isdigit():
                partita_id = int(partita_id_str)
                certificato = db.genera_certificato_proprieta(partita_id)
                if certificato:
                    stampa_intestazione("CERTIFICATO DI PROPRIETA")
                    print(certificato)
                    filename = f"certificato_partita_{partita_id}_{date.today()}.txt"
                    if _confirm_action(f"Salvare su file '{filename}'?"):
                         try:
                              with open(filename, 'w', encoding='utf-8') as f: f.write(certificato)
                              print(f"Certificato salvato.")
                         except Exception as e: print(f"Errore salvataggio: {e}")
                else: print("Nessun dato disponibile o errore generazione.")
            else: print("ID non valido!")

        elif scelta == "2":
            partita_id_str = input("Inserisci l'ID della partita: ").strip()
            if partita_id_str.isdigit():
                partita_id = int(partita_id_str)
                report = db.genera_report_genealogico(partita_id)
                if report:
                    stampa_intestazione("REPORT GENEALOGICO")
                    print(report)
                    filename = f"report_genealogico_{partita_id}_{date.today()}.txt"
                    if _confirm_action(f"Salvare su file '{filename}'?"):
                         try:
                              with open(filename, 'w', encoding='utf-8') as f: f.write(report)
                              print(f"Report salvato.")
                         except Exception as e: print(f"Errore salvataggio: {e}")
                else: print("Nessun dato disponibile o errore generazione.")
            else: print("ID non valido!")

        elif scelta == "3":
            possessore_id_str = input("Inserisci l'ID del possessore: ").strip()
            if possessore_id_str.isdigit():
                possessore_id = int(possessore_id_str)
                report = db.genera_report_possessore(possessore_id)
                if report:
                    stampa_intestazione("REPORT POSSESSORE")
                    print(report)
                    filename = f"report_possessore_{possessore_id}_{date.today()}.txt"
                    if _confirm_action(f"Salvare su file '{filename}'?"):
                         try:
                              with open(filename, 'w', encoding='utf-8') as f: f.write(report)
                              print(f"Report salvato.")
                         except Exception as e: print(f"Errore salvataggio: {e}")
                else: print("Nessun dato disponibile o errore generazione.")
            else: print("ID non valido!")

        elif scelta == "4":
            stampa_intestazione("REPORT CONSULTAZIONI")
            data_inizio_str = input("Data inizio (YYYY-MM-DD, vuoto per inizio): ").strip()
            data_fine_str = input("Data fine (YYYY-MM-DD, vuoto per fine): ").strip()
            richiedente = input("Richiedente (vuoto per tutti): ").strip() or None
            try:
                data_inizio = datetime.strptime(data_inizio_str, "%Y-%m-%d").date() if data_inizio_str else None
                data_fine = datetime.strptime(data_fine_str, "%Y-%m-%d").date() if data_fine_str else None
            except ValueError: print("Formato data non valido."); continue

            report = db.genera_report_consultazioni(data_inizio, data_fine, richiedente)
            if report:
                print(report)
                if _confirm_action("Salvare su file?"):
                    oggi = date.today().strftime("%Y%m%d")
                    filename = f"report_consultazioni_{oggi}.txt"
                    try:
                         with open(filename, 'w', encoding='utf-8') as f: f.write(report)
                         print(f"Report salvato in {filename}.")
                    except Exception as e: print(f"Errore salvataggio: {e}")
            else: print("Nessun dato disponibile o errore generazione.")

        elif scelta == "5":
            stampa_intestazione("STATISTICHE PER COMUNE (Vista Materializzata)")
            stats = db.get_statistiche_comune()
            if stats:
                for s in stats:
                    print(f"Comune: {s['comune']} ({s['provincia']})")
                    print(f"  Partite: Totali={s['totale_partite']}, Attive={s['partite_attive']}, Inattive={s['partite_inattive']}")
                    print(f"  Possessori: {s['totale_possessori']}")
                    print(f"  Immobili: {s['totale_immobili']}")
                    print("-" * 30)
            else: print("Nessuna statistica disponibile o errore.")

        elif scelta == "6":
            stampa_intestazione("RIEPILOGO IMMOBILI PER TIPOLOGIA (Vista Materializzata)")
            comune_filter = input("Filtra per comune (lascia vuoto per tutti): ").strip() or None
            stats = db.get_immobili_per_tipologia(comune_nome=comune_filter)
            if stats:
                current_comune = None
                for s in stats:
                    if s['comune_nome'] != current_comune:
                        current_comune = s['comune_nome']
                        print(f"\n--- Comune: {current_comune} ---")
                    print(f"  Classificazione: {s.get('classificazione') or 'N/D'}")
                    print(f"    Numero Immobili: {s.get('numero_immobili', 0)}")
                    print(f"    Totale Piani: {s.get('totale_piani', 0)}")
                    print(f"    Totale Vani: {s.get('totale_vani', 0)}")
            else: print("Nessun dato disponibile o errore.")

        elif scelta == "7":
            stampa_intestazione("VISUALIZZA PARTITE COMPLETE (Vista Materializzata)")
            comune_filter = input("Filtra per comune (vuoto per tutti): ").strip() or None
            stato_filter = input("Filtra per stato (attiva/inattiva, vuoto per tutti): ").strip() or None
            partite = db.get_partite_complete_view(comune_nome=comune_filter, stato=stato_filter)
            if partite:
                print(f"Trovate {len(partite)} partite:")
                for p in partite:
                    print(f"\nID: {p['partita_id']} - N.{p['numero_partita']} ({p['comune_nome']}) - Stato: {p['stato']}")
                    print(f"  Tipo: {p['tipo']}, Data Imp.: {p['data_impianto']}")
                    print(f"  Possessori: {p.get('possessori') or 'N/D'}")
                    print(f"  Imm: {p.get('num_immobili',0)} Tipi: {p.get('tipi_immobili') or 'N/D'} Loc: {p.get('localita') or 'N/D'}")
            else: print("Nessuna partita trovata.")

        elif scelta == "8":
            stampa_intestazione("CRONOLOGIA VARIAZIONI (Vista Materializzata)")
            comune_filter = input("Filtra per comune origine (vuoto per tutti): ").strip() or None
            tipo_filter = input("Filtra per tipo variazione (vuoto per tutti): ").strip().capitalize() or None
            variazioni = db.get_cronologia_variazioni(comune_origine=comune_filter, tipo_variazione=tipo_filter)
            if variazioni:
                print(f"Trovate {len(variazioni)} variazioni:")
                for v in variazioni:
                    print(f"\nID Var:{v['variazione_id']} Tipo:{v['tipo_variazione']} Data:{v['data_variazione']}")
                    print(f"  Origine: N.{v['partita_origine_numero']} ({v['comune_origine']}) Poss: {v.get('possessori_origine') or 'N/D'}")
                    if v.get('partita_dest_numero'):
                       print(f"  Destinaz: N.{v['partita_dest_numero']} ({v['comune_dest']}) Poss: {v.get('possessori_dest') or 'N/D'}")
                    if v.get('tipo_contratto'):
                       print(f"  Contratto: {v['tipo_contratto']} del {v['data_contratto']} (Notaio: {v.get('notaio') or 'N/D'})")
            else: print("Nessuna variazione trovata.")

        elif scelta == "9":
            stampa_intestazione("REPORT ANNUALE PARTITE PER COMUNE (Funzione)")
            comune = input("Nome comune: ").strip()
            anno_str = input("Anno del report: ").strip()
            if comune and anno_str.isdigit():
                anno = int(anno_str)
                report = db.get_report_annuale_partite(comune, anno)
                if report:
                    print(f"\nReport per {comune} - Anno {anno}:")
                    for r in report:
                        print(f"  N.{r['numero_partita']} ({r['tipo']}) Stato:{r['stato']} Imp:{r['data_impianto']}")
                        print(f"    Poss: {r.get('possessori') or 'N/D'} Imm:{r.get('num_immobili',0)} Var:{r.get('variazioni_anno',0)}")
                else: print("Nessun dato trovato o errore.")
            else: print("Comune e anno validi richiesti.")

        elif scelta == "10":
             stampa_intestazione("REPORT PROPRIETÀ POSSESSORE PER PERIODO (Funzione)")
             poss_id_str = input("ID del possessore: ").strip()
             data_i_str = input("Data inizio periodo (YYYY-MM-DD): ").strip()
             data_f_str = input("Data fine periodo (YYYY-MM-DD): ").strip()
             if not (poss_id_str.isdigit() and data_i_str and data_f_str):
                  print("ID Possessore e date obbligatori."); continue
             try:
                 possessore_id = int(poss_id_str)
                 data_inizio = datetime.strptime(data_i_str, "%Y-%m-%d").date()
                 data_fine = datetime.strptime(data_f_str, "%Y-%m-%d").date()
             except ValueError: print("Formato ID o data non validi."); continue

             report = db.get_report_proprieta_possessore(possessore_id, data_inizio, data_fine)
             if report:
                 print(f"\nProprietà ID {possessore_id} tra {data_inizio} e {data_fine}:")
                 for r in report:
                     quota_str = f" (Quota: {r['quota']})" if r['quota'] else ""
                     print(f"- Partita N.{r['numero_partita']} ({r['comune_nome']}) ID:{r['partita_id']}")
                     print(f"  Titolo: {r['titolo']}{quota_str} Periodo: {r['data_inizio']} - {r['data_fine']}")
                     print(f"  Immobili: {r.get('immobili_posseduti') or 'Nessuno'}")
             else: print("Nessun dato trovato.")

        elif scelta == "11":
             stampa_intestazione("REPORT STATISTICO COMUNE")
             comune = input("Nome comune: ").strip()
             if comune:
                 report_data = db.get_report_comune(comune)
                 if report_data:
                     print(f"\nStatistiche per {report_data['comune']}:")
                     print(f"  Partite: Tot {report_data['totale_partite']} (Att:{report_data['partite_attive']}, Inatt:{report_data['partite_inattive']})")
                     print(f"  Possessori: {report_data['totale_possessori']} (Medi per Partita: {report_data.get('possessori_per_partita', 0):.2f})")
                     print(f"  Immobili Totali: {report_data['totale_immobili']}")
                     print("  Immobili per Classe:")
                     try:
                         imm_per_classe = json.loads(report_data['immobili_per_classe']) if report_data.get('immobili_per_classe') else {}
                         if imm_per_classe:
                              for classe, count in imm_per_classe.items(): print(f"    - {classe or 'Non Class.'}: {count}")
                         else: print("    N/D")
                     except (json.JSONDecodeError, TypeError): print("    (Dati non validi)")
                 else: print(f"Comune '{comune}' non trovato o errore.")
             else: print("Nome comune obbligatorio.")

        elif scelta == "12":
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Manutenzione ---

def menu_manutenzione(db: CatastoDBManager):
    """Menu per la manutenzione del database."""
    while True:
        stampa_intestazione("MANUTENZIONE DATABASE")
        print("1. Verifica integrita database")
        print("2. Aggiorna Viste Materializzate")
        print("3. Esegui Manutenzione Generale (VACUUM, ANALYZE)")
        print("4. Analizza Query Lente (Richiede pg_stat_statements)")
        print("5. Controlla Frammentazione Indici")
        print("6. Ottieni Suggerimenti Ottimizzazione")
        print("7. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-7): ").strip()

        _set_session_context(db) # Imposta contesto prima dell'azione

        if scelta == "1":
            stampa_intestazione("VERIFICA INTEGRITA DATABASE")
            print("Avvio verifica...")
            problemi, messaggio = db.verifica_integrita_database()
            print("\n--- Risultato Verifica ---")
            print(messaggio)
            print("--- Fine Risultato ---")
            if problemi:
                print("\nATTENZIONE: Sono stati rilevati problemi!")
                # if _confirm_action("Eseguire correzione automatica (ATTENZIONE: operazione potenzialmente rischiosa)?"):
                #     print("Avvio correzione...")
                #     if db.execute_query("CALL ripara_problemi_database(TRUE)"): # Chiamata diretta procedura
                #          db.commit()
                #          print("Correzione automatica tentata.")
                #          print("Rieseguire la verifica integrità.")
                #     else:
                #          print("Errore durante il tentativo di correzione.")
                print("(La correzione automatica non è abilitata in questo esempio)")
            else:
                print("\nNessun problema critico di integrita rilevato.")

        elif scelta == "2":
            stampa_intestazione("AGGIORNAMENTO VISTE MATERIALIZZATE")
            if _confirm_action("Aggiornare tutte le viste materializzate (potrebbe richiedere tempo)?"):
                print("Avvio aggiornamento...")
                if db.refresh_materialized_views():
                    print("Aggiornamento completato con successo.")
                else:
                    print("Errore durante l'aggiornamento delle viste (controllare log).")

        elif scelta == "3":
            stampa_intestazione("ESEGUI MANUTENZIONE GENERALE")
            if _confirm_action("Eseguire VACUUM ANALYZE e aggiornare viste (richiede tempo)?"):
                print("Avvio manutenzione...")
                if db.run_database_maintenance():
                    print("Manutenzione generale completata.")
                else:
                    print("Errore durante l'esecuzione della manutenzione (controllare log).")

        elif scelta == "4":
            stampa_intestazione("ANALIZZA QUERY LENTE")
            print("NOTA: Richiede l'estensione 'pg_stat_statements' abilitata e configurata.")
            min_dur_str = input("Durata minima query in ms (default 1000): ").strip() or "1000"
            if min_dur_str.isdigit():
                min_duration = int(min_dur_str)
                slow_queries = db.analyze_slow_queries(min_duration)
                if slow_queries:
                    print(f"\nTrovate {len(slow_queries)} query più lente di {min_duration} ms:")
                    for q in slow_queries:
                         durata = round(q.get('durata_ms', 0), 2)
                         righe = q.get('righe_restituite', 'N/A')
                         chiamate = q.get('chiamate', 'N/A')
                         q_text = q.get('query_text', '')[:150] + ("..." if len(q.get('query_text','')) > 150 else "")
                         print(f"\n ID:{q.get('query_id','N/A')} Durata:{durata}ms Chiamate:{chiamate} Righe:{righe}")
                         print(f"   Query: {q_text}")
                elif slow_queries is not None: # Lista vuota, non None (errore)
                    print(f"Nessuna query trovata con durata media > {min_duration} ms.")
                # Se è None, errore già loggato dal manager
            else: print("Durata non valida.")

        elif scelta == "5":
            stampa_intestazione("CONTROLLA FRAMMENTAZIONE INDICI")
            print("Avvio controllo (i risultati dettagliati appaiono nei log del DB)...")
            db.check_index_fragmentation() # La funzione Python ora stampa solo un messaggio
            print("Controllo eseguito. Verificare i log del database per indici con frammentazione > 30%.")

        elif scelta == "6":
            stampa_intestazione("OTTIENI SUGGERIMENTI OTTIMIZZAZIONE")
            suggestions = db.get_optimization_suggestions()
            if suggestions:
                print("\nSuggerimenti:")
                print(suggestions)
            else:
                print("Nessun suggerimento disponibile o errore.")

        elif scelta == "7":
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Audit ---

def menu_audit(db: CatastoDBManager):
    """Menu per la gestione e consultazione del sistema di audit."""
    while True:
        stampa_intestazione("SISTEMA DI AUDIT")
        print("1. Consulta log di audit")
        print("2. Visualizza cronologia di un record")
        print("3. Genera report di audit")
        print("4. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-4): ").strip()

        if scelta == "1":
            stampa_intestazione("CONSULTA LOG DI AUDIT")
            tabella = input("Tabella (vuoto per tutte): ").strip() or None
            op = input("Operazione (I/U/D, vuoto per tutte): ").strip().upper() or None
            rec_id_str = input("ID Record (vuoto per tutti): ").strip()
            app_user_id_str = input("ID Utente App (vuoto per tutti): ").strip()
            session_id_str = input("ID Sessione (vuoto per tutti): ").strip() or None
            utente_db_str = input("Utente DB (vuoto per tutti): ").strip() or None
            data_i_str = input("Data inizio (YYYY-MM-DD, vuoto per inizio): ").strip()
            data_f_str = input("Data fine (YYYY-MM-DD, vuoto per fine): ").strip()

            rec_id = int(rec_id_str) if rec_id_str.isdigit() else None
            app_user_id = int(app_user_id_str) if app_user_id_str.isdigit() else None
            data_inizio, data_fine = None, None
            try:
                if data_i_str: data_inizio = datetime.strptime(data_i_str, "%Y-%m-%d").date()
                if data_f_str: data_fine = datetime.strptime(data_f_str, "%Y-%m-%d").date()
            except ValueError: print("Formato data non valido."); continue

            logs = db.get_audit_log(
                tabella=tabella, operazione=op, record_id=rec_id, data_inizio=data_inizio, data_fine=data_fine,
                utente_db=utente_db_str, app_user_id=app_user_id, session_id=session_id_str
            )
            stampa_intestazione(f"RISULTATI LOG AUDIT ({len(logs)})")
            if not logs: print("Nessun log trovato.")
            else:
                op_map = {"I": "Ins", "U": "Upd", "D": "Del"}
                for log in logs:
                    user_info = f"DB:{log.get('db_user', '?')}"
                    if log.get('app_user_id') is not None:
                        user_info += f" App:{log.get('app_user_id')}({log.get('app_username', '?')})"
                    else: user_info += " App:N/A"
                    print(f"ID:{log['id']} {log['timestamp']:%y-%m-%d %H:%M} {op_map.get(log['operazione'],'?')} "
                          f"T:{log['tabella']} R:{log['record_id']} {user_info} S:{log.get('session_id','-')[:8]} IP:{log.get('ip_address','-')}")
                    if log['operazione'] == 'U' and _confirm_action("  Vedere dettagli modifiche?"):
                         try:
                              prima = json.loads(log.get('dati_prima') or '{}')
                              dopo = json.loads(log.get('dati_dopo') or '{}')
                              all_keys = set(prima.keys()) | set(dopo.keys())
                              for k in sorted(list(all_keys)):
                                   v1 = prima.get(k)
                                   v2 = dopo.get(k)
                                   if v1 != v2: print(f"    - {k}: {v1} -> {v2}")
                         except Exception as e: print(f"    Errore visualizzazione dettagli: {e}")
                    print("-" * 40)

        elif scelta == "2":
            stampa_intestazione("CRONOLOGIA RECORD")
            tabella = input("Nome tabella (es. partita, possessore): ").strip()
            record_id_str = input("ID record: ").strip()
            if tabella and record_id_str.isdigit():
                history = db.get_record_history(tabella, int(record_id_str))
                stampa_intestazione(f"CRONOLOGIA {tabella.upper()} ID {record_id_str} ({len(history)} modifiche)")
                if not history: print(f"Nessuna modifica registrata.")
                else:
                    op_map = {"I": "Inserimento", "U": "Aggiornamento", "D": "Cancellazione"}
                    for i, record in enumerate(history, 1):
                         user = record.get('utente') or record.get('db_user', '?') # Compatibilità nome colonna
                         print(f"{i}. {op_map.get(record['operazione'], record['operazione'])} - {record['timestamp']:%Y-%m-%d %H:%M} - Utente:{user}")
                         if record['operazione'] == 'U':
                              print("  Modifiche:")
                              try:
                                   prima = json.loads(record.get('dati_prima') or '{}')
                                   dopo = json.loads(record.get('dati_dopo') or '{}')
                                   all_keys = set(prima.keys()) | set(dopo.keys())
                                   for k in sorted(list(all_keys)):
                                        v1 = prima.get(k)
                                        v2 = dopo.get(k)
                                        if v1 != v2: print(f"    - {k}: {v1} -> {v2}")
                              except Exception as e: print(f"    Impossibile elaborare dettagli: {e}")
                         print() # Riga vuota tra le modifiche
            else: print("Tabella e ID record validi richiesti.")

        elif scelta == "3":
            stampa_intestazione("GENERA REPORT DI AUDIT")
            tabella = input("Tabella (vuoto per tutte): ").strip() or None
            op = input("Operazione (I/U/D, vuoto per tutte): ").strip().upper() or None
            app_user_id_str = input("ID Utente App (vuoto per tutti): ").strip()
            utente_db = input("Utente DB (vuoto per tutti): ").strip() or None
            data_i_str = input("Data inizio (YYYY-MM-DD, vuoto per inizio): ").strip()
            data_f_str = input("Data fine (YYYY-MM-DD, vuoto per fine): ").strip()
            app_user_id = int(app_user_id_str) if app_user_id_str.isdigit() else None
            data_inizio, data_fine = None, None
            try:
                 if data_i_str: data_inizio = datetime.strptime(data_i_str, "%Y-%m-%d").date()
                 if data_f_str: data_fine = datetime.strptime(data_f_str, "%Y-%m-%d").date()
            except ValueError: print("Formato data non valido."); continue

            report = db.genera_report_audit(
                tabella=tabella, operazione=op, data_inizio=data_inizio, data_fine=data_fine,
                utente_db=utente_db, app_user_id=app_user_id
            )
            print(report)
            if _confirm_action("Salvare report su file?"):
                 oggi = date.today().strftime("%Y%m%d")
                 filename = f"report_audit_{oggi}.txt"
                 try:
                      with open(filename, 'w', encoding='utf-8') as f: f.write(report)
                      print(f"Report salvato in {filename}.")
                 except Exception as e: print(f"Errore salvataggio: {e}")

        elif scelta == "4":
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Utenti e Sessione ---

def menu_utenti(db: CatastoDBManager):
    """Menu per la gestione degli utenti, login e logout."""
    # Rende esplicito l'uso delle variabili globali per la sessione
    global logged_in_user_id, current_session_id, client_ip_address

    while True:
        stampa_intestazione("GESTIONE UTENTI E SESSIONE")
        if logged_in_user_id:
             print(f"--- Utente Attivo: ID {logged_in_user_id} (Sessione: {current_session_id[:8]}...) ---")
        else:
             print("--- Nessun utente connesso ---")

        print("1. Crea nuovo utente")
        print("2. Login Utente")
        print("3. Logout Utente")
        print("4. Verifica Permesso Utente")
        print("5. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-5): ").strip()

        # Imposta contesto PRIMA di operazioni potenzialmente auditate
        # (Nota: _set_session_context usa le variabili globali logged_in_user_id e client_ip_address)
        _set_session_context(db)

        if scelta == "1": # Crea nuovo utente
            stampa_intestazione("CREA NUOVO UTENTE")
            username = input("Username: ").strip()
            password = getpass.getpass("Password: ")
            password_confirm = getpass.getpass("Conferma Password: ")

            if not password:
                print("La password non può essere vuota.")
                continue # Torna al menu

            if password != password_confirm:
                print("Le password non coincidono.")
                continue # Torna al menu

            nome_completo = input("Nome completo: ").strip()
            email = input("Email: ").strip()
            print("Ruoli disponibili: admin, archivista, consultatore")
            ruolo = input("Ruolo: ").strip().lower()

            if not all([username, nome_completo, email, ruolo]):
                print("Username, nome completo, email e ruolo sono obbligatori.")
                continue # Torna al menu

            if ruolo not in ['admin', 'archivista', 'consultatore']:
                print("Ruolo non valido. Scegli tra: admin, archivista, consultatore.")
                continue # Torna al menu

            # Hash della password usando bcrypt PRIMA di inviarla al DB Manager
            try:
                password_hash = _hash_password(password)
                logger.debug(f"Password hash generato per {username}: {password_hash[:10]}...")
            except Exception as hash_err:
                logger.error(f"Errore durante l'hashing della password per {username}: {hash_err}")
                print("Si è verificato un errore tecnico durante la creazione dell'hash.")
                continue # Torna al menu

            # Chiama il DB Manager con l'hash generato
            if db.create_user(username, password_hash, nome_completo, email, ruolo):
                print(f"Utente '{username}' creato con successo.")
            else:
                # L'errore specifico (es. utente duplicato) dovrebbe essere già stato loggato da db.create_user
                print(f"Errore durante la creazione dell'utente '{username}' (controllare log).")

        elif scelta == "2": # Login Utente
            if logged_in_user_id:
                print("Sei già connesso. Esegui prima il logout (opzione 3).")
                continue # Torna al menu

            stampa_intestazione("LOGIN UTENTE")
            username = input("Username: ").strip()
            password = getpass.getpass("Password: ")

            if not username or not password:
                print("Username e password sono obbligatori.")
                continue # Torna al menu

            credentials = db.get_user_credentials(username)
            login_success = False
            user_id = None # Inizializza user_id

            if credentials:
                user_id = credentials['id'] # Ottieni l'ID per il log accessi
                stored_hash = credentials['password_hash']
                logger.debug(f"Tentativo login per utente ID {user_id}. Hash recuperato: {stored_hash[:10]}...")

                # Verifica la password fornita con l'hash memorizzato usando bcrypt
                if _verify_password(stored_hash, password):
                    login_success = True
                    print(f"Login riuscito per l'utente ID: {user_id}")
                    logger.info(f"Login riuscito per utente ID: {user_id}")
                else:
                    print("Password errata.")
                    logger.warning(f"Tentativo di login fallito (password errata) per utente ID: {user_id}")
            else:
                 print("Utente non trovato o non attivo.")
                 logger.warning(f"Tentativo di login fallito (utente '{username}' non trovato o non attivo).")
                 # Non abbiamo un user_id, quindi non possiamo registrare l'accesso fallito nel log DB

            # Registra l'accesso solo se l'utente è stato trovato (user_id is not None)
            if user_id is not None:
                session_id_returned = db.register_access(user_id, 'login', indirizzo_ip=client_ip_address, esito=login_success)
                if login_success and session_id_returned:
                    # Imposta le variabili globali di sessione SOLO se il login è riuscito E la registrazione accesso ha funzionato
                    logged_in_user_id = user_id
                    current_session_id = session_id_returned
                    # Imposta il contesto di sessione nel DB
                    if not db.set_session_app_user(logged_in_user_id, client_ip_address):
                        logger.error("Impossibile impostare il contesto di sessione nel DB dopo il login!")
                        # Considerare se annullare il login a questo punto?
                    print(f"Sessione {current_session_id[:8]}... avviata.")
                elif login_success and not session_id_returned:
                    # Caso anomalo: login verificato ma errore registrazione accesso/sessione
                    print("Errore critico: Impossibile registrare la sessione di accesso nel database.")
                    logger.error(f"Login verificato per user ID {user_id} ma fallita registrazione accesso.")
                    # Non impostare le variabili globali di sessione
                    logged_in_user_id = None
                    current_session_id = None
                # Se login_success è False, register_access registrerà il tentativo fallito

        elif scelta == "3": # Logout Utente
             if not logged_in_user_id:
                 print("Nessun utente attualmente connesso.")
                 continue # Torna al menu

             stampa_intestazione("LOGOUT UTENTE")
             print(f"Disconnessione utente ID: {logged_in_user_id}...")
             # Passa user_id e session_id correnti alla funzione di logout
             if db.logout_user(logged_in_user_id, current_session_id, client_ip_address):
                 print("Logout eseguito con successo.")
             else:
                 # L'errore dovrebbe essere loggato da logout_user
                 print("Errore durante la registrazione del logout (controllare log).")

             # Resetta sempre le variabili globali dopo il tentativo di logout
             logged_in_user_id = None
             current_session_id = None
             # Il contesto DB viene resettato da db.logout_user() internamente

        elif scelta == "4": # Verifica Permesso Utente
             stampa_intestazione("VERIFICA PERMESSO UTENTE")
             utente_id_str = input("ID Utente (lascia vuoto per utente corrente): ").strip()
             utente_id_to_check = None

             if utente_id_str.isdigit():
                 try:
                     utente_id_to_check = int(utente_id_str)
                 except ValueError:
                     print("ID utente non valido.")
                     continue # Torna al menu
             elif logged_in_user_id:
                 utente_id_to_check = logged_in_user_id
                 print(f"(Verifica per utente corrente ID: {utente_id_to_check})")
             else:
                 print("Nessun utente corrente e ID non specificato.")
                 continue # Torna al menu

             permesso = input("Nome del permesso (es. 'modifica_partite'): ").strip()
             if not permesso:
                 print("Il nome del permesso è obbligatorio.")
                 continue # Torna al menu

             if utente_id_to_check is not None:
                 try:
                     ha_permesso = db.check_permission(utente_id_to_check, permesso)
                     if ha_permesso:
                         print(f"L'utente ID {utente_id_to_check} HA il permesso '{permesso}'.")
                     else:
                         # Questo può significare che non ha il permesso o che c'è stato un errore (controllare log)
                         print(f"L'utente ID {utente_id_to_check} NON HA il permesso '{permesso}' o si è verificato un errore.")
                 except Exception as perm_err:
                     logger.error(f"Errore durante la verifica del permesso '{permesso}' per user ID {utente_id_to_check}: {perm_err}")
                     print("Si è verificato un errore durante la verifica del permesso.")
             # Non c'è 'else' qui perché i casi precedenti coprono tutto

        elif scelta == "5": # Torna al menu principale
            break # Esce dal ciclo while di menu_utenti
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...") # Pausa prima di mostrare di nuovo il menu
# --- Menu Backup ---

def menu_backup(db: CatastoDBManager):
    """Menu per le operazioni di Backup e Restore."""
    while True:
        stampa_intestazione("SISTEMA DI BACKUP E RESTORE")
        print("NOTA BENE: I comandi di backup/restore devono essere eseguiti manualmente nella shell.")
        print("\n1. Ottieni comando per Backup")
        print("2. Visualizza Log Backup Recenti")
        print("3. Ottieni comando per Restore (da ID Log)")
        print("4. Registra manualmente un Backup eseguito")
        print("5. Genera Script Bash per Backup Automatico")
        print("6. Pulisci Log Backup vecchi")
        print("7. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-7): ").strip()

        _set_session_context(db) # Imposta contesto prima dell'azione (per registrazione log)

        if scelta == "1":
            stampa_intestazione("OTTIENI COMANDO BACKUP")
            print("Tipi di backup: completo, schema, dati")
            tipo = input("Inserisci tipo (default: completo): ").strip() or 'completo'
            if tipo not in ['completo', 'schema', 'dati']: print("Tipo non valido."); continue
            cmd = db.get_backup_command_suggestion(tipo=tipo)
            if cmd: print("\n--- Comando Suggerito (eseguire in shell) ---\n", cmd, "\n" + "-"*55)
            else: print("Errore generazione comando.")

        elif scelta == "2":
            stampa_intestazione("LOG BACKUP RECENTI")
            logs = db.get_backup_logs()
            if logs:
                for log in logs:
                    esito = "OK" if log['esito'] else "FALLITO"
                    dim = f"{log['dimensione_bytes']} bytes" if log.get('dimensione_bytes') is not None else "N/D"
                    print(f"ID:{log['id']} {log['timestamp']:%Y-%m-%d %H:%M} Tipo:{log['tipo']} Esito:{esito}")
                    print(f"  File: {log['nome_file']} ({dim}) Utente:{log['utente']}")
                    if log.get('messaggio'): print(f"  Msg: {log['messaggio']}")
                    print("-" * 30)
            else: print("Nessun log di backup trovato.")

        elif scelta == "3":
            stampa_intestazione("OTTIENI COMANDO RESTORE")
            log_id_str = input("ID del log di backup da cui ripristinare: ").strip()
            if log_id_str.isdigit():
                cmd = db.get_restore_command_suggestion(int(log_id_str))
                if cmd:
                    print("\n--- Comando Suggerito (eseguire in shell) ---\n", cmd, "\n" + "-"*55)
                    print("ATTENZIONE: Il restore sovrascriverà i dati attuali!")
                else: print("ID log non valido o errore.")
            else: print("ID non valido.")

        elif scelta == "4":
             stampa_intestazione("REGISTRA BACKUP MANUALE")
             nome_file = input("Nome file backup: ").strip()
             percorso = input("Percorso completo file: ").strip()
             utente = input("Utente esecuzione (default 'manuale'): ").strip() or 'manuale'
             tipo = input("Tipo ('completo', 'schema', 'dati'): ").strip()
             esito_str = input("Backup riuscito? (s/n): ").strip().lower()
             msg = input("Messaggio (opzionale): ").strip() or None
             dim_str = input("Dimensione bytes (opzionale): ").strip()

             if not all([nome_file, percorso, tipo]): print("Nome, percorso e tipo obbligatori."); continue
             if tipo not in ['completo', 'schema', 'dati']: print("Tipo non valido."); continue
             esito = esito_str == 's'
             dim = int(dim_str) if dim_str.isdigit() else None

             backup_id = db.register_backup_log(nome_file, utente, tipo, esito, percorso, dim, msg)
             if backup_id: print(f"Backup manuale registrato con ID: {backup_id}")
             else: print("Errore registrazione backup manuale.")

        elif scelta == "5":
            stampa_intestazione("GENERA SCRIPT BACKUP AUTOMATICO")
            backup_dir = input("Directory destinazione backup (es. /var/backups/catasto): ").strip()
            script_name = input("Nome file script (es. backup_catasto.sh): ").strip()
            if not backup_dir or not script_name: print("Directory e nome script obbligatori."); continue

            script_content = db.generate_backup_script(backup_dir)
            if script_content:
                try:
                    with open(script_name, 'w', encoding='utf-8') as f: f.write(script_content)
                    os.chmod(script_name, 0o755) # Rende eseguibile
                    print(f"Script '{script_name}' generato in {os.getcwd()}.")
                    print("Configura un cron job o task schedulato per eseguirlo.")
                except Exception as e: print(f"Errore salvataggio script: {e}")
            else: print("Errore generazione script.")

        elif scelta == "6":
            stampa_intestazione("PULISCI LOG BACKUP VECCHI")
            giorni_str = input("Conserva log degli ultimi quanti giorni? (default 30): ").strip() or "30"
            if giorni_str.isdigit():
                if db.cleanup_old_backup_logs(int(giorni_str)): print("Pulizia log vecchi completata.")
                else: print("Errore pulizia log.")
            else: print("Numero giorni non valido.")

        elif scelta == "7":
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Menu Storico Avanzato ---

def menu_storico_avanzato(db: CatastoDBManager):
    """Menu per le funzionalità storiche avanzate."""
    while True:
        stampa_intestazione("FUNZIONALITÀ STORICHE AVANZATE")
        print("1. Visualizza Periodi Storici")
        print("2. Ottieni Nome Storico Entità per Anno")
        print("3. Registra Nome Storico Entità")
        print("4. Ricerca Documenti Storici")
        print("5. Visualizza Albero Genealogico Proprietà")
        print("6. Statistiche Catastali per Periodo")
        print("7. Collega Documento a Partita")
        print("8. Torna al menu principale")
        scelta = input("\nSeleziona un'opzione (1-8): ").strip()

        _set_session_context(db) # Imposta contesto prima dell'azione

        if scelta == "1":
            stampa_intestazione("PERIODI STORICI")
            periodi = db.get_historical_periods()
            if periodi:
                for p in periodi:
                    fine = p.get('anno_fine') or 'oggi'
                    print(f"ID:{p['id']} {p['nome']} ({p['anno_inizio']}-{fine}) Desc: {p.get('descrizione') or '-'}")
            else: print("Nessun periodo storico trovato.")

        elif scelta == "2":
            stampa_intestazione("OTTIENI NOME STORICO ENTITÀ")
            tipo_ent = input("Tipo entità (comune/localita): ").strip().lower()
            if tipo_ent not in ['comune', 'localita']: print("Tipo non valido."); continue
            id_ent_str = input(f"ID {tipo_ent}: ").strip()
            anno_str = input("Anno (INVIO per corrente): ").strip()
            if not id_ent_str.isdigit(): print("ID non valido."); continue
            entita_id = int(id_ent_str)
            anno = int(anno_str) if anno_str.isdigit() else None # None usa default nella funzione DB

            nome_info = db.get_historical_name(tipo_ent, entita_id, anno)
            if nome_info:
                fine = nome_info.get('anno_fine') or 'oggi'
                print(f"\nNome in anno {anno or datetime.now().year}: {nome_info['nome']}")
                print(f" Periodo: {nome_info['periodo_nome']} ({nome_info['anno_inizio']}-{fine})")
            else: print("Nessun nome storico trovato.")

        elif scelta == "3":
            stampa_intestazione("REGISTRA NOME STORICO")
            tipo_ent = input("Tipo entità (comune/localita): ").strip().lower()
            if tipo_ent not in ['comune', 'localita']: print("Tipo non valido."); continue
            id_ent_str = input(f"ID {tipo_ent}: ").strip()
            nome_storico = input("Nome storico da registrare: ").strip()
            periodi = db.get_historical_periods()
            if not periodi: print("Definire prima i periodi storici."); continue
            print("\nPeriodi disponibili:")
            for p in periodi: print(f" ID: {p['id']} - {p['nome']}")
            periodo_id_str = input("ID Periodo storico: ").strip()
            anno_i_str = input("Anno inizio validità nome: ").strip()
            anno_f_str = input("Anno fine validità (INVIO se valido fino a fine periodo): ").strip()

            if not (id_ent_str.isdigit() and nome_storico and periodo_id_str.isdigit() and anno_i_str.isdigit()):
                 print("ID entità, nome, ID periodo e anno inizio obbligatori."); continue
            try:
                 entita_id = int(id_ent_str)
                 periodo_id = int(periodo_id_str)
                 anno_inizio = int(anno_i_str)
                 anno_fine = int(anno_f_str) if anno_f_str.isdigit() else None
            except ValueError: print("Input numerico non valido."); continue
            note = input("Note (opzionale): ").strip() or None

            if db.register_historical_name(tipo_ent, entita_id, nome_storico, periodo_id, anno_inizio, anno_fine, note):
                print("Nome storico registrato.")
            else: print("Errore registrazione nome storico.")

        elif scelta == "4":
             stampa_intestazione("RICERCA DOCUMENTI STORICI")
             titolo = input("Titolo (parziale, INVIO per non filtrare): ").strip() or None
             tipo_doc = input("Tipo documento (esatto, INVIO per non filtrare): ").strip() or None
             periodo_id_str = input("ID Periodo storico (INVIO per non filtrare): ").strip()
             anno_i_str = input("Anno inizio (INVIO per non filtrare): ").strip()
             anno_f_str = input("Anno fine (INVIO per non filtrare): ").strip()
             part_id_str = input("ID Partita collegata (INVIO per non filtrare): ").strip()
             try:
                 periodo_id = int(periodo_id_str) if periodo_id_str else None
                 anno_inizio = int(anno_i_str) if anno_i_str else None
                 anno_fine = int(anno_f_str) if anno_f_str else None
                 partita_id = int(part_id_str) if part_id_str else None
             except ValueError: print("Input ID/Anno non valido."); continue

             documenti = db.search_historical_documents(titolo, tipo_doc, periodo_id, anno_inizio, anno_fine, partita_id)
             if documenti:
                 print(f"\nTrovati {len(documenti)} documenti:")
                 for doc in documenti:
                      print(f"- ID:{doc['documento_id']} {doc['titolo']} ({doc['tipo_documento']}) Anno:{doc['anno']} Periodo:{doc['periodo_nome']}")
                      if doc.get('descrizione'): print(f"  Desc: {doc['descrizione']}")
                      if doc.get('partite_correlate'): print(f"  Partite: {doc['partite_correlate']}")
             else: print("Nessun documento trovato.")

        elif scelta == "5":
            stampa_intestazione("ALBERO GENEALOGICO PROPRIETÀ")
            part_id_str = input("ID della partita di partenza: ").strip()
            if part_id_str.isdigit():
                albero = db.get_property_genealogy(int(part_id_str))
                if albero:
                    print("\nLivello | Relazione    | ID Partita | Comune           | N. Partita | Tipo       | Possessori")
                    print("--------|--------------|------------|------------------|------------|------------|-----------")
                    for nodo in albero:
                        poss = (nodo.get('possessori') or '')[:40] + ('...' if len(nodo.get('possessori','')) > 40 else '')
                        data_v = f" ({nodo['data_variazione']})" if nodo.get('data_variazione') else ""
                        print(f" {str(nodo.get('livello', '?')).rjust(6)} | {nodo.get('tipo_relazione', '').ljust(12)} | {str(nodo.get('partita_id', '')).ljust(10)} | {nodo.get('comune_nome', '').ljust(16)} | {str(nodo.get('numero_partita', '')).ljust(10)} | {nodo.get('tipo', '').ljust(10)} | {poss}{data_v}")
                else: print("Impossibile generare albero genealogico.")
            else: print("ID partita non valido.")

        elif scelta == "6":
             stampa_intestazione("STATISTICHE CATASTALI PER PERIODO")
             comune = input("Filtra per comune (INVIO per tutti): ").strip() or None
             anno_i_str = input("Anno inizio (default 1900): ").strip() or "1900"
             anno_f_str = input("Anno fine (INVIO per corrente): ").strip()
             if not anno_i_str.isdigit() or (anno_f_str and not anno_f_str.isdigit()):
                  print("Anni non validi."); continue
             anno_i = int(anno_i_str)
             anno_f = int(anno_f_str) if anno_f_str else None

             stats = db.get_cadastral_stats_by_period(comune, anno_i, anno_f)
             if stats:
                   print("\nAnno  | Comune           | Nuove P. | Chiuse P. | Tot Attive | Variazioni | Imm. Reg.")
                   print("------|------------------|----------|-----------|------------|------------|-----------")
                   for s in stats:
                       print(f" {s['anno']} | {s.get('comune_nome', 'Totale').ljust(16)} | "
                             f"{str(s.get('nuove_partite', 0)).rjust(8)} | "
                             f"{str(s.get('partite_chiuse', 0)).rjust(9)} | "
                             f"{str(s.get('totale_partite_attive', 0)).rjust(10)} | "
                             f"{str(s.get('variazioni', 0)).rjust(10)} | "
                             f"{str(s.get('immobili_registrati', 0)).rjust(9)}")
             else: print("Nessuna statistica trovata.")

        elif scelta == "7":
            stampa_intestazione("COLLEGA DOCUMENTO A PARTITA")
            doc_id_str = input("ID Documento Storico: ").strip()
            part_id_str = input("ID Partita da collegare: ").strip()
            if not (doc_id_str.isdigit() and part_id_str.isdigit()): print("ID non validi."); continue
            doc_id = int(doc_id_str)
            part_id = int(part_id_str)
            print("Rilevanza: primaria, secondaria, correlata")
            rilevanza = input("Inserisci rilevanza (default correlata): ").strip() or 'correlata'
            note = input("Note (opzionale): ").strip() or None

            if db.link_document_to_partita(doc_id, part_id, rilevanza, note):
                print("Collegamento creato/aggiornato.")
            else: print("Errore creazione collegamento.")

        elif scelta == "8":
            break
        else:
            print("Opzione non valida!")
        input("\nPremi INVIO per continuare...")

# --- Funzione Main ---
def main():
    # Configurazione iniziale del logger (puoi metterla qui o a livello globale)
    # Se la configurazione è già in catasto_db_manager, basta ottenere il logger:
    logger = logging.getLogger(__name__) # Ottieni un logger per questo modulo
    db_config = {
        "dbname": "catasto_storico",
        "user": "postgres",
        "password": "Markus74",  # !! SOSTITUIRE CON PASSWORD REALE O METODO SICURO !!
        "host": "localhost",
        "port": 5432,
        "schema": "catasto"
    }
    stampa_locandina_introduzione()
    db = CatastoDBManager(**db_config)

    if not db.connect():
        print("ERRORE CRITICO: Impossibile connettersi al database. Verifica i parametri e lo stato del server.")
        sys.exit(1)

    global logged_in_user_id, current_session_id # Necessario per resettare in finally

    try:
        menu_principale(db)
    except KeyboardInterrupt:
        print("\nOperazione interrotta dall'utente.")
    except Exception as e:
        logger.exception(f"Errore non gestito nel menu principale: {e}") # Logga l'eccezione completa
        print(f"ERRORE IMPREVISTO: {e}")
    finally:
        # Esegui logout se necessario prima di chiudere
        if logged_in_user_id and current_session_id and db.conn and not db.conn.closed:
             print("\nEsecuzione logout prima della chiusura...")
             db.logout_user(logged_in_user_id, current_session_id, client_ip_address)
        # Resetta le variabili globali
        logged_in_user_id = None
        current_session_id = None
        # Chiudi la connessione
        if db:
            db.disconnect()
        print("\nApplicazione terminata.")

if __name__ == "__main__":
    main()