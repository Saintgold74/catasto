#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Esempio di utilizzo del gestore database catastale - Versione Migliorata
=======================================================================
Questo script mostra esempi pratici di come utilizzare
la classe CatastoDBManager per interagire con il database.

Include miglioramenti per:
- Configurazione esterna
- Validazione input centralizzata
- Sicurezza password (bcrypt, getpass)
- Formattazione output (tabulate)

Autore: Marco Santoro
Data: 24/04/2025
"""

# Import necessari
from catasto_db_manager import CatastoDBManager # Assumi sia nello stesso folder o path
from datetime import date, datetime
import json
import os
import sys
import bcrypt
import getpass
from tabulate import tabulate
from typing import Optional, List, Dict, Any

# Import per configurazione (Scegli una delle due opzioni)
# Opzione 1: python-dotenv
from dotenv import load_dotenv
# Opzione 2: configparser
# import configparser

# === HELPER FUNCTIONS ===

def stampa_intestazione(titolo: str):
    """Stampa un'intestazione formattata."""
    print("\n" + "=" * 80)
    print(f" {titolo} ".center(80, "="))
    print("=" * 80)

def get_validated_input(prompt: str, validation_type: str = 'text', required: bool = True, choices: Optional[List[str]] = None) -> Optional[str]:
    """
    Richiede input all'utente con validazione.

    Args:
        prompt: Il messaggio da mostrare all'utente.
        validation_type: 'text', 'int', 'float', 'date', 'choice', 'password', 'email'.
        required: Se True, l'input non può essere vuoto.
        choices: Lista di scelte valide se validation_type è 'choice' (case-insensitive).

    Returns:
        L'input validato come stringa, o None se non richiesto e lasciato vuoto o errore.
    """
    prompt_suffix = (" (obbligatorio): " if required else " (opzionale, INVIO per saltare): ")

    while True:
        user_input: str
        if validation_type == 'password':
            user_input = getpass.getpass(prompt + prompt_suffix)
        else:
            user_input = input(prompt + prompt_suffix)

        user_input = user_input.strip()

        if not user_input:
            if required:
                print("Errore: Questo campo è obbligatorio.")
                continue
            else:
                return None # Input vuoto e non richiesto

        if validation_type == 'int':
            if not user_input.isdigit() and not (user_input.startswith('-') and user_input[1:].isdigit()):
                print("Errore: Inserire un numero intero valido.")
                continue
            return user_input

        elif validation_type == 'float':
             try:
                 float(user_input.replace(',', '.')) # Accetta sia . che , come separatore decimale
                 return user_input.replace(',', '.') # Restituisce sempre con .
             except ValueError:
                 print("Errore: Inserire un numero valido (es. 123 o 45.67).")
                 continue

        elif validation_type == 'date':
            try:
                datetime.strptime(user_input, "%Y-%m-%d")
                return user_input
            except ValueError:
                print("Errore: Inserire una data valida nel formato YYYY-MM-DD.")
                continue

        elif validation_type == 'choice':
            if choices:
                 # Confronto case-insensitive
                 lower_choices = [str(c).lower() for c in choices]
                 if user_input.lower() not in lower_choices:
                     print(f"Errore: Scelta non valida. Opzioni: {', '.join(map(str, choices))}")
                     continue
                 # Restituisci l'input originale per mantenere il case se necessario
                 return user_input
            else:
                 # Se non ci sono scelte definite, tratta come testo normale
                 return user_input

        elif validation_type == 'email':
            # Validazione molto basica per email
            if '@' not in user_input or '.' not in user_input.split('@')[-1]:
                print("Errore: Inserire un indirizzo email valido.")
                continue
            return user_input

        elif validation_type in ['text', 'password']:
             return user_input

        else:
            print(f"Errore interno: tipo di validazione '{validation_type}' non gestito.")
            return None

def display_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None, tablefmt: str = "grid"):
    """Visualizza una lista di dizionari come tabella formattata."""
    if not data:
        print("Nessun dato da visualizzare.")
        return

    if not headers:
        # Usa le chiavi del primo dizionario come header se non forniti
        # Mantiene l'ordine delle chiavi del primo elemento (in Python 3.7+)
        if data:
            headers = list(data[0].keys())
        else:
            print("Nessun dato e nessun header specificato.")
            return

    # Estrai i dati in formato lista di liste per tabulate
    # Gestisce valori None o mancanti trasformandoli in 'N/D'
    table_data = [[item.get(header, 'N/D') for header in headers] for item in data]

    # Stampa la tabella
    print(tabulate(table_data, headers=[h.replace('_', ' ').title() for h in headers], tablefmt=tablefmt))

def ask_yes_no(prompt: str, default: Optional[bool] = None) -> bool:
    """Fa una domanda Sì/No all'utente."""
    choices = "[s/n]"
    if default is True:
        choices = "[S/n]"
    elif default is False:
        choices = "[s/N]"

    while True:
        resp_str = input(f"{prompt} {choices}: ").strip().lower()
        if not resp_str:
            if default is not None:
                return default
            else:
                print("Risposta richiesta.")
                continue
        if resp_str in ['s', 'si', 'sì', 'y', 'yes']:
            return True
        if resp_str in ['n', 'no']:
            return False
        print("Risposta non valida. Inserire 's' o 'n'.")

# --- FINE HELPER FUNCTIONS ---

# === FUNZIONI SPECIFICHE DI INSERIMENTO (riutilizzate in menu) ===

def inserisci_possessore(db: CatastoDBManager, comune_preselezionato: Optional[str] = None) -> Optional[int]:
    """Funzione per l'inserimento di un nuovo possessore, usa helpers."""
    stampa_intestazione("AGGIUNGI NUOVO POSSESSORE")

    if not comune_preselezionato:
        comune = get_validated_input("Comune di residenza", required=True)
        if not comune: return None
    else:
        comune = comune_preselezionato
        print(f"Comune: {comune}")

    nome_completo = get_validated_input("Nome completo", required=True)
    if not nome_completo: return None

    codice_fiscale = get_validated_input("Codice Fiscale (opzionale)", required=False)
    paternita = get_validated_input("Paternità (opzionale)", required=False)
    data_nascita_str = get_validated_input("Data di nascita (YYYY-MM-DD, opzionale)", validation_type='date', required=False)
    luogo_nascita = get_validated_input("Luogo di nascita (opzionale)", required=False)
    note = get_validated_input("Note (opzionale)", required=False)

    data_nascita = datetime.strptime(data_nascita_str, "%Y-%m-%d").date() if data_nascita_str else None

    try:
        # Assumendo che db.inserisci_possessore esista (era nello script 03/13)
        possessore_id = db.inserisci_possessore(
            nome_completo=nome_completo,
            codice_fiscale=codice_fiscale,
            comune_residenza=comune,
            paternita=paternita,
            data_nascita=data_nascita,
            luogo_nascita=luogo_nascita,
            note=note
        )
        if possessore_id:
            print(f"Possessore '{nome_completo}' inserito con ID: {possessore_id}")
            return possessore_id
        else:
            print("Errore durante l'inserimento del possessore (controlla i log).")
            return None
    except AttributeError:
         print("ERRORE: Metodo 'inserisci_possessore' non trovato in CatastoDBManager.")
         return None
    except Exception as e:
        print(f"Errore imprevisto: {e}")
        return None

# === MENU FUNCTIONS ===

def menu_consultazione(db: CatastoDBManager):
    """Menu per operazioni di consultazione."""
    while True:
        stampa_intestazione("CONSULTAZIONE DATI")
        print(" 1. Elenco comuni")
        print(" 2. Elenco partite per comune")
        print(" 3. Elenco possessori per comune")
        print(" 4. Ricerca partite (Semplice)")
        print(" 5. Dettagli partita")
        print(" 6. Elenco localita per comune")
        print(" 7. Ricerca Avanzata Possessori (Similarità)")
        print(" 8. Ricerca Avanzata Immobili")
        print(" 9. Cerca Immobili Specifici")
        print("10. Cerca Variazioni")
        print("11. Cerca Consultazioni")
        print("12. Esporta Partita in JSON")
        print("13. Esporta Possessore in JSON")
        print("\n14. Torna al menu principale")

        scelta = get_validated_input("Seleziona un'opzione", validation_type='int', required=True)
        if not scelta: continue

        if scelta == "1":
            stampa_intestazione("ELENCO COMUNI")
            comuni = db.get_comuni()
            display_table(comuni, headers=['id', 'nome', 'provincia', 'regione'])

        elif scelta == "2":
            stampa_intestazione("ELENCO PARTITE PER COMUNE")
            comune_nome = get_validated_input("Nome Comune")
            if comune_nome:
                partite = db.get_partite_per_comune(comune_nome)
                display_table(partite, headers=['id', 'numero_partita', 'tipo', 'stato', 'data_impianto'])

        elif scelta == "3":
            stampa_intestazione("ELENCO POSSESSORI PER COMUNE")
            comune_nome = get_validated_input("Nome Comune")
            if comune_nome:
                possessori = db.get_possessori_per_comune(comune_nome)
                display_table(possessori, headers=['id', 'nome_completo', 'paternita', 'data_nascita'])

        elif scelta == "4":
            stampa_intestazione("RICERCA PARTITE (SEMPLICE)")
            comune = get_validated_input("Nome Comune (opzionale)", required=False)
            tipo = get_validated_input("Tipo Partita (opzionale)", required=False)
            stato = get_validated_input("Stato (attiva/inattiva, opzionale)", required=False, choices=['attiva', 'inattiva'])
            possessore_nome = get_validated_input("Nome Possessore (parziale, opzionale)", required=False)
            natura_immobile = get_validated_input("Natura Immobile (parziale, opzionale)", required=False)
            partite = db.search_partite(
                comune_nome=comune,
                tipo=tipo,
                stato=stato,
                possessore_search=possessore_nome,
                natura_immobile_search=natura_immobile
            )
            display_table(partite, headers=['id', 'numero_partita', 'comune_nome', 'tipo', 'stato', 'possessori', 'immobili'])

        elif scelta == "5":
             stampa_intestazione("DETTAGLI PARTITA")
             partita_id_str = get_validated_input("ID Partita", validation_type='int', required=True)
             if partita_id_str:
                 try:
                     partita_id = int(partita_id_str)
                     dettagli = db.get_partita_details(partita_id)
                     if dettagli:
                          print("\nDettagli Partita:")
                          for key, value in dettagli['partita_info'].items():
                              print(f"  {key.replace('_', ' ').title()}: {value}")
                          print("\n  Possessori:")
                          display_table(dettagli['possessori'], headers=['id', 'nome_completo', 'titolo', 'quota'])
                          print("\n  Immobili:")
                          display_table(dettagli['immobili'], headers=['id', 'natura', 'numero_piani', 'numero_vani', 'localita_nome'])
                     else:
                          print("Partita non trovata.")
                 except ValueError:
                     print("ID non valido.")
                 except Exception as e:
                     print(f"Errore nel recuperare dettagli: {e}")

        elif scelta == "6":
            stampa_intestazione("ELENCO LOCALITA PER COMUNE")
            comune_nome = get_validated_input("Nome Comune", required=True)
            if comune_nome:
                 localita = db.get_localita_per_comune(comune_nome)
                 display_table(localita, headers=['id', 'nome', 'tipo_localita', 'note'])

        elif scelta == "7":
            stampa_intestazione("RICERCA AVANZATA POSSESSORI (Similarità)")
            query_text = get_validated_input("Termine di ricerca per nome/cognome/paternità", required=True)
            if query_text:
                results = db.ricerca_avanzata_possessori(query_text)
                if results:
                     # Format similarity before display
                     formatted_results = []
                     for r in results:
                          similarity_perc = round(r.get('similarity', 0) * 100, 1)
                          formatted_results.append({
                               'ID': r.get('id'),
                               'Nome Completo': r.get('nome_completo'),
                               'Comune': r.get('comune_nome'),
                               'Similarità (%)': similarity_perc,
                               'N. Partite': r.get('num_partite')
                          })
                     display_table(formatted_results)
                else:
                    print("Nessun possessore trovato.")

        elif scelta == "8":
             stampa_intestazione("RICERCA AVANZATA IMMOBILI")
             comune = get_validated_input("Comune (opzionale)", required=False)
             natura = get_validated_input("Natura Immobile (opzionale)", required=False)
             localita = get_validated_input("Località (opzionale)", required=False)
             classificazione = get_validated_input("Classificazione (opzionale)", required=False)
             possessore = get_validated_input("Possessore (opzionale)", required=False)

             results = db.ricerca_avanzata_immobili(
                 comune=comune, natura=natura, localita=localita,
                 classificazione=classificazione, possessore=possessore
             )
             display_table(results, headers=['immobile_id', 'natura', 'localita_nome', 'comune', 'classificazione', 'possessori', 'partita_numero'])

        elif scelta == "9":
            stampa_intestazione("CERCA IMMOBILI SPECIFICI")
            part_id_str = get_validated_input("Filtra per ID Partita (opzionale)", validation_type='int', required=False)
            comune = get_validated_input("Filtra per Comune (opzionale)", required=False)
            loc_id_str = get_validated_input("Filtra per ID Località (opzionale)", validation_type='int', required=False)
            natura = get_validated_input("Filtra per Natura (parziale, opzionale)", required=False)
            classif = get_validated_input("Filtra per Classificazione (esatta, opzionale)", required=False)

            try:
                part_id = int(part_id_str) if part_id_str else None
                loc_id = int(loc_id_str) if loc_id_str else None

                immobili = db.search_immobili(
                    partita_id=part_id, comune_nome=comune, localita_id=loc_id,
                    natura=natura, classificazione=classif
                )
                display_table(immobili, headers=['id', 'natura', 'numero_piani', 'numero_vani', 'classificazione', 'localita_nome', 'comune_nome', 'numero_partita'])
            except ValueError:
                print("ID non valido.")
            except Exception as e:
                print(f"Errore: {e}")

        elif scelta == "10":
            stampa_intestazione("CERCA VARIAZIONI")
            tipo = get_validated_input("Filtra per Tipo (es. Vendita, Successione, opzionale)", required=False)
            data_i_str = get_validated_input("Data inizio (YYYY-MM-DD, opzionale)", validation_type='date', required=False)
            data_f_str = get_validated_input("Data fine (YYYY-MM-DD, opzionale)", validation_type='date', required=False)
            part_o_id_str = get_validated_input("ID Partita Origine (opzionale)", validation_type='int', required=False)
            part_d_id_str = get_validated_input("ID Partita Destinazione (opzionale)", validation_type='int', required=False)
            comune = get_validated_input("Filtra per Comune Origine (opzionale)", required=False)

            try:
                data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date() if data_i_str else None
                data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date() if data_f_str else None
                part_o_id = int(part_o_id_str) if part_o_id_str else None
                part_d_id = int(part_d_id_str) if part_d_id_str else None

                variazioni = db.search_variazioni(
                    tipo=tipo, data_inizio=data_i, data_fine=data_f,
                    partita_origine_id=part_o_id, partita_destinazione_id=part_d_id, comune=comune
                )
                display_table(variazioni, headers=['id', 'tipo', 'data_variazione', 'partita_origine_numero', 'comune_nome', 'partita_destinazione_numero', 'numero_riferimento', 'nominativo_riferimento'])
            except ValueError:
                 print("Input ID o Data non validi.")
            except Exception as e:
                print(f"Errore: {e}")

        elif scelta == "11":
            stampa_intestazione("CERCA CONSULTAZIONI")
            data_i_str = get_validated_input("Data inizio (YYYY-MM-DD, opzionale)", validation_type='date', required=False)
            data_f_str = get_validated_input("Data fine (YYYY-MM-DD, opzionale)", validation_type='date', required=False)
            richiedente = get_validated_input("Filtra per Richiedente (parziale, opzionale)", required=False)
            funzionario = get_validated_input("Filtra per Funzionario (parziale, opzionale)", required=False)
            try:
                data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date() if data_i_str else None
                data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date() if data_f_str else None

                consultazioni = db.search_consultazioni(
                    data_inizio=data_i, data_fine=data_f, richiedente=richiedente, funzionario=funzionario
                )
                display_table(consultazioni, headers=['id', 'data', 'richiedente', 'documento_identita', 'motivazione', 'materiale_consultato', 'funzionario_autorizzante'])
            except ValueError:
                print("Formato Data non valido.")
            except Exception as e:
                print(f"Errore: {e}")

        elif scelta == "12":
            stampa_intestazione("ESPORTA PARTITA IN JSON")
            partita_id_str = get_validated_input("ID della Partita da esportare", validation_type='int', required=True)
            if partita_id_str:
                try:
                    partita_id = int(partita_id_str)
                    json_data = db.export_partita_json(partita_id)
                    if json_data:
                        print("\n--- DATI JSON PARTITA ---")
                        # Stampa il JSON formattato
                        print(json_data) # export_partita_json ora dovrebbe restituire stringa formattata
                        print("-" * 25)
                        filename = f"partita_{partita_id}.json"
                        if ask_yes_no(f"Salvare in '{filename}'?", default=True):
                            try:
                                with open(filename, 'w', encoding='utf-8') as f:
                                    f.write(json_data)
                                print(f"Dati salvati in {filename}")
                            except IOError as ioe:
                                 print(f"Errore di scrittura file: {ioe}")
                    else:
                        print("Partita non trovata o errore durante l'esportazione.")
                except ValueError:
                    print("ID non valido.")
                except Exception as e:
                     print(f"Errore imprevisto: {e}")

        elif scelta == "13":
            stampa_intestazione("ESPORTA POSSESSORE IN JSON")
            poss_id_str = get_validated_input("ID del Possessore da esportare", validation_type='int', required=True)
            if poss_id_str:
                try:
                    poss_id = int(poss_id_str)
                    json_data = db.export_possessore_json(poss_id)
                    if json_data:
                        print("\n--- DATI JSON POSSESSORE ---")
                        print(json_data)
                        print("-" * 26)
                        filename = f"possessore_{poss_id}.json"
                        if ask_yes_no(f"Salvare in '{filename}'?", default=True):
                             try:
                                 with open(filename, 'w', encoding='utf-8') as f:
                                     f.write(json_data)
                                 print(f"Dati salvati in {filename}")
                             except IOError as ioe:
                                  print(f"Errore di scrittura file: {ioe}")
                    else:
                        print("Possessore non trovato o errore durante l'esportazione.")
                except ValueError:
                    print("ID non valido.")
                except Exception as e:
                     print(f"Errore imprevisto: {e}")

        elif scelta == "14":
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")


def menu_inserimento(db: CatastoDBManager):
    """Menu per operazioni di inserimento e gestione."""
    while True:
        stampa_intestazione("INSERIMENTO E GESTIONE DATI")
        print(" 1. Aggiungi nuovo comune")
        print(" 2. Aggiungi nuovo possessore")
        print(" 3. Aggiungi nuova localita")
        print(" 4. Registra nuova proprieta (Partita)")
        print(" 5. Registra passaggio di proprieta")
        print(" 6. Registra consultazione")
        print(" 7. Inserisci Contratto per Variazione")
        print(" 8. Duplica Partita")
        print(" 9. Trasferisci Immobile a Nuova Partita")
        print("\n10. Torna al menu principale")

        scelta = get_validated_input("Seleziona un'opzione", validation_type='int', required=True)
        if not scelta: continue

        if scelta == "1":
            stampa_intestazione("AGGIUNGI NUOVO COMUNE")
            nome = get_validated_input("Nome Comune", required=True)
            provincia = get_validated_input("Provincia", required=True)
            regione = get_validated_input("Regione", required=True)
            if nome and provincia and regione:
                if db.insert_comune(nome, provincia, regione):
                    print(f"Comune '{nome}' inserito/aggiornato.")
                else:
                    print("Errore inserimento comune.")

        elif scelta == "2":
            inserisci_possessore(db) # Usa la funzione helper

        elif scelta == "3":
            stampa_intestazione("AGGIUNGI NUOVA LOCALITA")
            comune_nome = get_validated_input("Nome Comune a cui appartiene", required=True)
            nome_localita = get_validated_input("Nome Località", required=True)
            tipo = get_validated_input("Tipo Località (es. Frazione, Borgata, opzionale)", required=False)
            note = get_validated_input("Note (opzionale)", required=False)
            if comune_nome and nome_localita:
                 localita_id = db.insert_localita(comune_nome, nome_localita, tipo, note)
                 if localita_id:
                      print(f"Località '{nome_localita}' inserita/trovata con ID: {localita_id}")
                 else:
                      print("Errore inserimento località.")

        elif scelta == "4":
            stampa_intestazione("REGISTRA NUOVA PROPRIETA (PARTITA)")
            # Questa è complessa, usa ancora input standard per brevità,
            # ma idealmente andrebbe scomposta e userebbe get_validated_input per ogni campo
            print("Inserisci i dati della nuova partita:")
            comune_nome = input("Nome Comune: ")
            numero_partita = input("Numero Partita: ")
            tipo_partita = input("Tipo Partita (Terreni/Fabbricati): ")
            data_impianto_str = input("Data Impianto (YYYY-MM-DD): ")

            possessori_info = []
            while True:
                print("\nInserisci possessore:")
                # Qui si potrebbe chiamare inserisci_possessore o cercare un possessore esistente
                nome_poss = input("Nome completo possessore: ")
                titolo = input("Titolo (Proprietà/Usufrutto/etc.): ")
                quota = input("Quota (es. 1/2, 1/1 - opzionale): ") or None
                possessori_info.append({'nome_completo': nome_poss, 'titolo': titolo, 'quota': quota})
                if not ask_yes_no("Aggiungere un altro possessore?", default=False):
                    break

            immobili_info = []
            while True:
                 print("\nInserisci immobile:")
                 natura = input("Natura (es. Casa, Prato, Bosco): ")
                 loc = input("Località: ")
                 piani_str = input("Numero Piani (opzionale): ")
                 vani_str = input("Numero Vani (opzionale): ")
                 consistenza = input("Consistenza (es. 10 mq, 5 are - opzionale): ") or None
                 classe = input("Classificazione (opzionale): ") or None

                 piani = int(piani_str) if piani_str.isdigit() else None
                 vani = int(vani_str) if vani_str.isdigit() else None

                 immobili_info.append({
                      'natura': natura, 'localita': loc, 'numero_piani': piani,
                      'numero_vani': vani, 'consistenza': consistenza, 'classificazione': classe
                 })
                 if not ask_yes_no("Aggiungere un altro immobile?", default=False):
                      break
            try:
                 data_impianto = datetime.strptime(data_impianto_str, "%Y-%m-%d").date()
                 # Chiama la procedura v2 che gestisce inserimento/verifica possessori/località
                 partita_id = db.registra_nuova_proprieta_v2(
                      comune_nome, numero_partita, tipo_partita, data_impianto,
                      possessori_info, immobili_info
                 )
                 if partita_id:
                      print(f"Nuova proprietà registrata con ID Partita: {partita_id}")
                 else:
                      print("Errore durante la registrazione della proprietà (controlla log).")
            except ValueError:
                 print("Formato data impianto non valido (YYYY-MM-DD).")
            except Exception as e:
                 print(f"Errore imprevisto: {e}")


        elif scelta == "5":
            stampa_intestazione("REGISTRA PASSAGGIO DI PROPRIETA")
            # Anche questo è complesso, usa input standard per brevità
            try:
                partita_id_origine = int(input("ID Partita origine: "))
                tipo_variazione = input("Tipo variazione (Vendita/Successione/Donazione/Divisione): ")
                data_variazione_str = input("Data variazione (YYYY-MM-DD): ")
                data_variazione = datetime.strptime(data_variazione_str, "%Y-%m-%d").date()

                # Gestione Possessori Uscenti
                possessori_uscenti_ids = []
                print("\nSpecificare ID dei possessori USCENTI (INVIO per terminare):")
                while True:
                    pid_str = input("ID Possessore Uscente: ")
                    if not pid_str: break
                    if pid_str.isdigit():
                         possessori_uscenti_ids.append(int(pid_str))
                    else:
                         print("ID non valido.")

                # Gestione Possessori Entranti
                possessori_entranti_info = []
                print("\nSpecificare nuovi possessori ENTRANTI:")
                while True:
                    # Qui si potrebbe cercare un possessore esistente per ID o inserirlo
                    nome_poss = input("Nome completo nuovo possessore (o INVIO per terminare): ")
                    if not nome_poss: break
                    titolo = input("Titolo (Proprietà/Usufrutto/etc.): ")
                    quota = input("Quota (es. 1/2, 1/1 - opzionale): ") or None
                    possessori_entranti_info.append({'nome_completo': nome_poss, 'titolo': titolo, 'quota': quota})

                # Gestione Dati Contratto (Opzionale)
                tipo_contratto = input("Tipo Contratto (opzionale): ") or None
                data_contratto = None
                if tipo_contratto:
                    data_contratto_str = input("Data contratto (YYYY-MM-DD, opzionale): ")
                    if data_contratto_str:
                        try:
                            data_contratto = datetime.strptime(data_contratto_str, "%Y-%m-%d").date()
                        except ValueError:
                            print("Formato data contratto non valido, verrà ignorato.")
                notaio = input("Notaio (opzionale): ") or None
                repertorio = input("Repertorio (opzionale): ") or None
                note_contratto = input("Note Contratto (opzionale): ") or None

                # Crea oggetto contratto se ci sono dati
                contratto_info = None
                if tipo_contratto and data_contratto:
                     contratto_info = {
                          'tipo': tipo_contratto, 'data': data_contratto, 'notaio': notaio,
                          'repertorio': repertorio, 'note': note_contratto
                     }

                # Chiama la procedura v2
                risultato = db.registra_passaggio_proprieta_v2(
                    partita_id_origine, tipo_variazione, data_variazione,
                    possessori_uscenti_ids, possessori_entranti_info, contratto_info
                )

                if risultato and risultato.get('success'):
                    print("Passaggio di proprietà registrato con successo.")
                    print(f"  Nuova Partita ID: {risultato.get('nuova_partita_id', 'N/D')}")
                    print(f"  Variazione ID: {risultato.get('variazione_id', 'N/D')}")
                    if risultato.get('contratto_id'):
                        print(f"  Contratto ID: {risultato['contratto_id']}")
                else:
                    print(f"Errore durante la registrazione: {risultato.get('message', 'Errore sconosciuto')}")

            except ValueError:
                print("ID Partita o formato data non valido.")
            except Exception as e:
                 print(f"Errore imprevisto: {e}")


        elif scelta == "6":
            stampa_intestazione("REGISTRA CONSULTAZIONE")
            richiedente = get_validated_input("Richiedente", required=True)
            doc_id = get_validated_input("Documento Identità (opzionale)", required=False)
            motivazione = get_validated_input("Motivazione", required=True)
            materiale = get_validated_input("Materiale Consultato", required=True)
            funzionario = get_validated_input("Funzionario Autorizzante", required=True)
            data_str = get_validated_input("Data consultazione (YYYY-MM-DD, default oggi)", validation_type='date', required=False)

            if richiedente and motivazione and materiale and funzionario:
                try:
                    data_consultazione = datetime.strptime(data_str, "%Y-%m-%d").date() if data_str else date.today()
                    cons_id = db.registra_consultazione(
                        data=data_consultazione, richiedente=richiedente, documento_identita=doc_id,
                        motivazione=motivazione, materiale_consultato=materiale, funzionario_autorizzante=funzionario
                    )
                    if cons_id:
                        print(f"Consultazione registrata con ID: {cons_id}")
                    else:
                        print("Errore registrazione consultazione.")
                except ValueError:
                     print("Formato data non valido.")
                except Exception as e:
                     print(f"Errore imprevisto: {e}")

        elif scelta == "7":
            stampa_intestazione("INSERISCI CONTRATTO PER VARIAZIONE")
            var_id_str = get_validated_input("ID Variazione a cui collegare il contratto", validation_type='int', required=True)
            tipo_contratto = get_validated_input("Tipo contratto", required=True) # Aggiungere choices se utile
            data_str = get_validated_input("Data contratto (YYYY-MM-DD)", validation_type='date', required=True)
            notaio = get_validated_input("Notaio (opzionale)", required=False)
            repertorio = get_validated_input("Repertorio (opzionale)", required=False)
            note = get_validated_input("Note (opzionale)", required=False)

            if var_id_str and tipo_contratto and data_str:
                try:
                    var_id = int(var_id_str)
                    data_contratto = datetime.strptime(data_str, "%Y-%m-%d").date()

                    if db.insert_contratto(var_id, tipo_contratto, data_contratto, notaio, repertorio, note):
                        print("Contratto inserito con successo.")
                    else:
                        print("Errore durante l'inserimento del contratto.")
                except ValueError:
                    print("ID Variazione o formato data non valido.")
                except Exception as e:
                    print(f"Errore: {e}")

        elif scelta == "8":
            stampa_intestazione("DUPLICA PARTITA")
            partita_id_orig_str = get_validated_input("ID Partita da duplicare", validation_type='int', required=True)
            nuovo_num_str = get_validated_input("Nuovo numero per la partita duplicata", validation_type='int', required=True)
            mant_poss = ask_yes_no("Mantenere i possessori?", default=True)
            mant_imm = ask_yes_no("Mantenere gli immobili?", default=False)

            if partita_id_orig_str and nuovo_num_str:
                try:
                    partita_id_orig = int(partita_id_orig_str)
                    nuovo_num = int(nuovo_num_str)

                    if db.duplicate_partita(partita_id_orig, nuovo_num, mant_poss, mant_imm):
                        print("Partita duplicata con successo.")
                    else:
                        print("Errore durante la duplicazione della partita.")
                except ValueError:
                    print("ID o numero partita non valido.")
                except Exception as e:
                    print(f"Errore: {e}")

        elif scelta == "9":
            stampa_intestazione("TRASFERISCI IMMOBILE")
            imm_id_str = get_validated_input("ID Immobile da trasferire", validation_type='int', required=True)
            part_dest_id_str = get_validated_input("ID Partita di destinazione", validation_type='int', required=True)
            reg_var = ask_yes_no("Registrare una variazione per questo trasferimento?", default=False)

            if imm_id_str and part_dest_id_str:
                try:
                    imm_id = int(imm_id_str)
                    part_dest_id = int(part_dest_id_str)

                    if db.transfer_immobile(imm_id, part_dest_id, reg_var):
                        print("Immobile trasferito con successo.")
                    else:
                        print("Errore durante il trasferimento dell'immobile.")
                except ValueError:
                    print("ID non valido.")
                except Exception as e:
                    print(f"Errore: {e}")

        elif scelta == "10":
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")

def menu_report(db: CatastoDBManager):
    """Menu per la generazione di report."""
    while True:
        stampa_intestazione("GENERAZIONE REPORT")
        print(" 1. Certificato di proprieta")
        print(" 2. Report genealogico (NON IMPLEMENTATO IN PYTHON)") # Mantenuto?
        print(" 3. Report possessore (NON IMPLEMENTATO IN PYTHON)") # Mantenuto?
        print(" 4. Report consultazioni (Periodo)")
        print(" 5. Statistiche per comune (Vista Materializzata)")
        print(" 6. Riepilogo immobili per tipologia (Vista Materializzata)")
        print(" 7. Visualizza Partite Complete (Vista Materializzata)")
        print(" 8. Cronologia Variazioni (Vista Materializzata)")
        print(" 9. Report Annuale Partite per Comune (Funzione)")
        print("10. Report Proprietà Possessore per Periodo (Funzione)")
        print("11. Report Statistico Comune")
        print("\n12. Torna al menu principale")

        scelta = get_validated_input("Seleziona un'opzione", validation_type='int', required=True)
        if not scelta: continue

        if scelta == "1":
            stampa_intestazione("CERTIFICATO DI PROPRIETA")
            partita_id_str = get_validated_input("ID Partita", validation_type='int', required=True)
            if partita_id_str:
                 try:
                      partita_id = int(partita_id_str)
                      certificato = db.genera_certificato_proprieta(partita_id)
                      if certificato:
                           print("\n--- CERTIFICATO ---")
                           print(certificato)
                           print("-" * 17)
                           filename = f"certificato_partita_{partita_id}.txt"
                           if ask_yes_no(f"Salvare certificato in '{filename}'?", default=False):
                                try:
                                     with open(filename, 'w', encoding='utf-8') as f:
                                          f.write(certificato)
                                     print(f"Certificato salvato in {filename}")
                                except IOError as ioe:
                                     print(f"Errore scrittura file: {ioe}")
                      else:
                           print("Errore generazione certificato o partita non trovata.")
                 except ValueError:
                      print("ID non valido.")
                 except Exception as e:
                      print(f"Errore: {e}")

        elif scelta == "2":
             print("Funzionalità 'Report Genealogico' non ancora implementata in questo script.")
        elif scelta == "3":
             print("Funzionalità 'Report Possessore' non ancora implementata in questo script.")

        elif scelta == "4":
             stampa_intestazione("REPORT CONSULTAZIONI PER PERIODO")
             data_i_str = get_validated_input("Data inizio (YYYY-MM-DD)", validation_type='date', required=True)
             data_f_str = get_validated_input("Data fine (YYYY-MM-DD)", validation_type='date', required=True)
             if data_i_str and data_f_str:
                  try:
                      data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date()
                      data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date()
                      report = db.get_report_consultazioni(data_i, data_f)
                      if report:
                           print("\n--- REPORT CONSULTAZIONI ---")
                           print(report)
                           print("-" * 26)
                           filename = f"report_consultazioni_{data_i}__{data_f}.txt"
                           if ask_yes_no(f"Salvare report in '{filename}'?", default=False):
                                try:
                                     with open(filename, 'w', encoding='utf-8') as f:
                                          f.write(report)
                                     print(f"Report salvato in {filename}")
                                except IOError as ioe:
                                     print(f"Errore scrittura file: {ioe}")
                      else:
                           print("Nessuna consultazione trovata nel periodo o errore.")
                  except ValueError:
                       print("Date non valide.")
                  except Exception as e:
                       print(f"Errore: {e}")

        elif scelta == "5":
            stampa_intestazione("STATISTICHE PER COMUNE (Vista Materializzata)")
            stats = db.get_statistiche_comune()
            display_table(stats, headers=['comune', 'provincia', 'totale_partite', 'partite_attive', 'partite_inattive', 'totale_possessori', 'totale_immobili'])

        elif scelta == "6":
            stampa_intestazione("RIEPILOGO IMMOBILI PER TIPOLOGIA (Vista Materializzata)")
            comune_filter = get_validated_input("Filtra per comune (opzionale)", required=False)
            stats = db.get_immobili_per_tipologia(comune_nome=comune_filter if comune_filter else None)
            display_table(stats, headers=['comune_nome', 'classificazione', 'numero_immobili', 'totale_piani', 'totale_vani'])

        elif scelta == "7":
            stampa_intestazione("VISUALIZZA PARTITE COMPLETE (Vista Materializzata)")
            comune_filter = get_validated_input("Filtra per comune (opzionale)", required=False)
            stato_filter = get_validated_input("Filtra per stato (attiva/inattiva, opzionale)", required=False, choices=['attiva', 'inattiva'])
            partite = db.get_partite_complete_view(
                comune_nome=comune_filter,
                stato=stato_filter
            )
            # L'output di questa vista è complesso, display_table potrebbe non essere ideale senza pre-elaborazione
            if partite:
                print(f"Trovate {len(partite)} partite:")
                for p in partite:
                     print(f"\nID: {p['partita_id']} - Partita {p['numero_partita']} ({p['comune_nome']}) - Stato: {p['stato']}")
                     print(f"  Tipo: {p['tipo']}, Data Impianto: {p['data_impianto']}")
                     print(f"  Possessori: {p['possessori']}") # Stringa aggregata
                     print(f"  Num. Immobili: {p['num_immobili']}, Tipi: {p['tipi_immobili']}") # Stringa aggregata
                     print(f"  Località: {p['localita']}") # Stringa aggregata
            else:
                 print("Nessuna partita trovata.")


        elif scelta == "8":
            stampa_intestazione("CRONOLOGIA VARIAZIONI (Vista Materializzata)")
            comune_filter = get_validated_input("Filtra per comune origine (opzionale)", required=False)
            tipo_filter = get_validated_input("Filtra per tipo variazione (opzionale)", required=False)
            variazioni = db.get_cronologia_variazioni(
                comune_origine=comune_filter,
                tipo_variazione=tipo_filter
            )
            display_table(variazioni, headers=[
                'variazione_id', 'tipo_variazione', 'data_variazione',
                'partita_origine_numero', 'comune_origine', 'possessori_origine',
                'partita_dest_numero', 'comune_dest', 'possessori_dest',
                'tipo_contratto', 'notaio', 'data_contratto'
            ])

        elif scelta == "9":
            stampa_intestazione("REPORT ANNUALE PARTITE PER COMUNE (Funzione)")
            comune = get_validated_input("Inserisci il nome del comune", required=True)
            anno_str = get_validated_input("Inserisci l'anno del report", validation_type='int', required=True)
            if comune and anno_str:
                try:
                    anno = int(anno_str)
                    report = db.get_report_annuale_partite(comune, anno)
                    display_table(report, headers=['numero_partita', 'tipo', 'stato', 'data_impianto', 'possessori', 'num_immobili', 'variazioni_anno'])
                except ValueError:
                    print("Anno non valido.")
                except Exception as e:
                     print(f"Errore: {e}")


        elif scelta == "10":
             stampa_intestazione("REPORT PROPRIETÀ POSSESSORE PER PERIODO (Funzione)")
             poss_id_str = get_validated_input("Inserisci l'ID del possessore", validation_type='int', required=True)
             data_i_str = get_validated_input("Data inizio periodo (YYYY-MM-DD)", validation_type='date', required=True)
             data_f_str = get_validated_input("Data fine periodo (YYYY-MM-DD)", validation_type='date', required=True)
             if poss_id_str and data_i_str and data_f_str:
                 try:
                     poss_id = int(poss_id_str)
                     data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date()
                     data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date()

                     report = db.get_report_proprieta_possessore(poss_id, data_i, data_f)
                     display_table(report, headers=['partita_id', 'numero_partita', 'comune_nome', 'titolo', 'quota', 'data_inizio', 'data_fine', 'immobili_posseduti'])
                 except ValueError:
                     print("ID possessore o formato data non validi.")
                 except Exception as e:
                     print(f"Errore: {e}")

        elif scelta == "11":
             stampa_intestazione("REPORT STATISTICO COMUNE")
             comune = get_validated_input("Inserisci il nome del comune", required=True)
             if comune:
                 report_data = db.get_report_comune(comune)
                 if report_data:
                     print(f"\nStatistiche per {report_data['comune']}:")
                     print(f"  Totale Partite: {report_data['totale_partite']}")
                     print(f"  Partite Attive: {report_data['partite_attive']}")
                     print(f"  Partite Inattive: {report_data['partite_inattive']}")
                     print(f"  Totale Possessori: {report_data['totale_possessori']}")
                     print(f"  Totale Immobili: {report_data['totale_immobili']}")
                     # Parsing e visualizzazione del JSON interno
                     try:
                         imm_per_classe = json.loads(report_data['immobili_per_classe']) if report_data.get('immobili_per_classe') else {}
                         print("  Immobili per Classificazione:")
                         if imm_per_classe:
                             # Converti a lista di dict per tabulate
                             table_data = [[classe, count] for classe, count in imm_per_classe.items()]
                             print(tabulate(table_data, headers=["Classificazione", "Numero"], tablefmt="plain"))
                         else:
                             print("    N/D")
                     except (json.JSONDecodeError, TypeError):
                         print("  Immobili per Classificazione: (Dati non validi o vuoti)")
                     print(f"  Possessori Medi per Partita: {report_data.get('possessori_per_partita', 0):.2f}")
                 else:
                     print(f"Comune '{comune}' non trovato o errore nel generare il report.")

        elif scelta == "12":
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")


def menu_manutenzione(db: CatastoDBManager):
    """Menu per la manutenzione del database."""
    while True:
        stampa_intestazione("MANUTENZIONE DATABASE")
        print("1. Verifica integrita database (NON IMPLEMENTATO)") # Mantenuto?
        print("2. Aggiorna Viste Materializzate (per Report Avanzati)")
        print("3. Esegui Manutenzione Generale (VACUUM ANALYZE, etc.)")
        print("4. Analizza Query Lente (Richiede pg_stat_statements)")
        print("5. Controlla Frammentazione Indici")
        print("6. Ottieni Suggerimenti Ottimizzazione")
        print("\n7. Torna al menu principale")

        scelta = get_validated_input("Seleziona un'opzione", validation_type='int', required=True)
        if not scelta: continue

        if scelta == "1":
            print("Funzionalità 'Verifica Integrità' non ancora implementata in questo script.")

        elif scelta == "2":
            stampa_intestazione("AGGIORNAMENTO VISTE MATERIALIZZATE")
            print("Avvio aggiornamento...")
            if db.refresh_materialized_views():
                print("Aggiornamento completato con successo.")
            else:
                print("Errore durante l'aggiornamento delle viste.")

        elif scelta == "3":
            stampa_intestazione("ESEGUI MANUTENZIONE GENERALE")
            print("Questa operazione (VACUUM, ANALYZE) può richiedere tempo...")
            if ask_yes_no("Procedere?", default=False):
                if db.run_database_maintenance(): # Usa la versione Python corretta
                    print("Manutenzione generale completata.")
                else:
                    print("Errore durante l'esecuzione della manutenzione (controlla log).")
            else:
                print("Operazione annullata.")

        elif scelta == "4":
            stampa_intestazione("ANALIZZA QUERY LENTE")
            print("NOTA: Richiede l'estensione 'pg_stat_statements' abilitata nel database.")
            min_duration_str = get_validated_input("Durata minima query in ms (default 1000)", validation_type='int', required=False)
            try:
                min_duration = int(min_duration_str) if min_duration_str else 1000
                slow_queries = db.analyze_slow_queries(min_duration)

                if slow_queries: # Lista non None e non vuota
                     print(f"\nTrovate {len(slow_queries)} query più lente di {min_duration} ms:")
                     # Semplifica l'output per tabulate
                     display_data = []
                     for q in slow_queries:
                          durata_fmt = round(q.get('durata_ms', 0), 2)
                          query_text = q.get('query_text', '')
                          query_text_short = (query_text[:80] + "...") if len(query_text) > 80 else query_text
                          display_data.append({
                               'ID': q.get('query_id', 'N/A'),
                               'Durata Media (ms)': durata_fmt,
                               'Chiamate': q.get('chiamate', 'N/A'),
                               'Righe Medie': q.get('righe_restituite', 'N/A'),
                               'Query (inizio)': query_text_short
                          })
                     display_table(display_data)
                elif slow_queries == []: # Lista vuota
                    print(f"Nessuna query trovata con durata media superiore a {min_duration} ms.")
                # Se slow_queries è None, l'errore è già stato loggato

            except ValueError:
                print("Durata non valida.")
            except Exception as e:
                print(f"Errore durante l'analisi: {e}")

        elif scelta == "5":
            stampa_intestazione("CONTROLLA FRAMMENTAZIONE INDICI")
            print("Esecuzione controllo (output principale nei log del DB)...")
            fragmented_indices = db.check_index_fragmentation()
            if fragmented_indices:
                 print("\nIndici con frammentazione > 30% (rilevati programmaticamente):")
                 display_table(fragmented_indices, headers=['schema_name', 'table_name', 'index_name', 'bloat_ratio', 'bloat_size'])
                 print("\nConsidera REINDEX per questi indici.")
            elif fragmented_indices == []:
                print("Nessun indice con frammentazione significativa (>30%) rilevato programmaticamente.")
            else:
                print("Controllo eseguito. Verifica i log del database PostgreSQL per i messaggi dettagliati (RAISE NOTICE) o se la lettura programmatica è fallita.")

        elif scelta == "6":
            stampa_intestazione("OTTIENI SUGGERIMENTI OTTIMIZZAZIONE")
            suggestions = db.get_optimization_suggestions()
            if suggestions:
                print("\nSuggerimenti:\n" + suggestions)
            else:
                print("Nessun suggerimento disponibile o errore nel recupero.")

        elif scelta == "7":
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")


def menu_audit(db: CatastoDBManager):
    """Menu per le funzionalità di audit."""
    while True:
        stampa_intestazione("SISTEMA DI AUDIT")
        print("1. Visualizza Log Audit Recenti")
        print("2. Cerca nel Log Audit")
        print("3. Genera Report Audit per Periodo")
        print("\n4. Torna al menu principale")

        scelta = get_validated_input("Seleziona un'opzione", validation_type='int', required=True)
        if not scelta: continue

        if scelta == "1":
            stampa_intestazione("LOG AUDIT RECENTI")
            limit_str = get_validated_input("Numero di log da visualizzare (default 20)", validation_type='int', required=False)
            limit = int(limit_str) if limit_str else 20
            logs = db.get_audit_logs(limit=limit)
            display_table(logs, headers=['id', 'timestamp', 'utente_db', 'utente_app', 'azione', 'tabella_interessata', 'record_id', 'vecchi_dati', 'nuovi_dati'])

        elif scelta == "2":
            stampa_intestazione("CERCA NEL LOG AUDIT")
            utente = get_validated_input("Utente Applicazione (opzionale)", required=False)
            azione = get_validated_input("Azione (es. INSERT, UPDATE, DELETE, opzionale)", required=False)
            tabella = get_validated_input("Tabella Interessata (opzionale)", required=False)
            data_i_str = get_validated_input("Data inizio (YYYY-MM-DD, opzionale)", validation_type='date', required=False)
            data_f_str = get_validated_input("Data fine (YYYY-MM-DD, opzionale)", validation_type='date', required=False)
            try:
                data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date() if data_i_str else None
                data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date() if data_f_str else None
                logs = db.search_audit_logs(
                    utente_app=utente, azione=azione, tabella=tabella, data_inizio=data_i, data_fine=data_f
                )
                display_table(logs, headers=['id', 'timestamp', 'utente_db', 'utente_app', 'azione', 'tabella_interessata', 'record_id', 'vecchi_dati', 'nuovi_dati'])
            except ValueError:
                print("Formato data non valido.")
            except Exception as e:
                 print(f"Errore ricerca audit: {e}")


        elif scelta == "3":
            stampa_intestazione("GENERA REPORT AUDIT PER PERIODO")
            data_i_str = get_validated_input("Data inizio (YYYY-MM-DD)", validation_type='date', required=True)
            data_f_str = get_validated_input("Data fine (YYYY-MM-DD)", validation_type='date', required=True)
            if data_i_str and data_f_str:
                try:
                    data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date()
                    data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date()
                    report = db.generate_audit_report(data_i, data_f)
                    if report:
                        print("\n--- REPORT AUDIT ---")
                        print(report)
                        print("-" * 18)
                        filename = f"report_audit_{data_i}__{data_f}.txt"
                        if ask_yes_no(f"Salvare report in '{filename}'?", default=False):
                             try:
                                 with open(filename, 'w', encoding='utf-8') as f:
                                      f.write(report)
                                 print(f"Report salvato in {filename}")
                             except IOError as ioe:
                                  print(f"Errore scrittura file: {ioe}")
                    else:
                         print("Nessun dato audit trovato nel periodo o errore.")
                except ValueError:
                    print("Date non valide.")
                except Exception as e:
                    print(f"Errore: {e}")

        elif scelta == "4":
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")


def menu_utenti(db: CatastoDBManager):
    """Menu per la gestione degli utenti."""
    while True:
        stampa_intestazione("GESTIONE UTENTI")
        print("1. Crea nuovo utente")
        print("2. Simula Login Utente")
        print("3. Verifica Permesso Utente")
        print("\n4. Torna al menu principale")

        scelta = get_validated_input("Seleziona un'opzione", validation_type='int', required=True)
        if not scelta: continue

        if scelta == "1":
            stampa_intestazione("CREA NUOVO UTENTE")
            username = get_validated_input("Username", required=True)
            if not username: continue
            password = get_validated_input("Password", validation_type='password', required=True)
            if not password: continue
            nome_completo = get_validated_input("Nome completo", required=True)
            if not nome_completo: continue
            email = get_validated_input("Email", validation_type='email', required=True)
            if not email: continue
            ruolo = get_validated_input("Ruolo", required=True, choices=['admin', 'archivista', 'consultatore'])
            if not ruolo: continue

            if db.create_user(username, password, nome_completo, email, ruolo):
                print(f"Utente '{username}' creato con successo.")
            # L'errore specifico viene loggato da CatastoDBManager

        elif scelta == "2":
            stampa_intestazione("SIMULA LOGIN UTENTE")
            username = get_validated_input("Username", required=True)
            if not username: continue
            password = get_validated_input("Password", validation_type='password', required=True)
            if not password: continue

            credentials = db.get_user_credentials(username)

            if credentials and 'id' in credentials and 'password_hash' in credentials:
                stored_hash = credentials['password_hash']
                user_id = credentials['id']
                try:
                    # Verifica con bcrypt
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                        print(f"Login riuscito per l'utente ID: {user_id}")
                        db.register_access(user_id, 'login', esito=True)
                        # Qui si potrebbe impostare uno stato di 'utente loggato' per l'app
                    else:
                        print("Password errata.")
                        db.register_access(user_id, 'login', esito=False)
                except ValueError as bve:
                     print(f"Errore nella verifica password: hash non valido nel DB? {bve}")
                     logger.error(f"Tentativo di login per {username} fallito - hash DB non valido?")
                except Exception as e:
                     print(f"Errore imprevisto durante verifica password: {e}")
            else:
                print("Utente non trovato o non attivo.")

        elif scelta == "3":
            stampa_intestazione("VERIFICA PERMESSO UTENTE")
            utente_id_str = get_validated_input("ID Utente", validation_type='int', required=True)
            permesso = get_validated_input("Nome del permesso (es. 'modifica_partite')", required=True)
            if utente_id_str and permesso:
                try:
                    utente_id = int(utente_id_str)
                    if db.check_permission(utente_id, permesso):
                        print(f"L'utente {utente_id} HA il permesso '{permesso}'.")
                    else:
                        print(f"L'utente {utente_id} NON HA il permesso '{permesso}'.")
                except ValueError:
                     print("ID utente non valido.") # Già gestito da get_validated_input
                except Exception as e:
                    print(f"Errore durante la verifica del permesso: {e}")

        elif scelta == "4":
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")


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
        print("\n7. Torna al menu principale")

        scelta = get_validated_input("Seleziona un'opzione", validation_type='int', required=True)
        if not scelta: continue

        if scelta == "1":
            stampa_intestazione("OTTIENI COMANDO BACKUP")
            tipo_backup = get_validated_input("Tipo di backup", required=True, choices=['completo', 'schema', 'dati'])
            if tipo_backup:
                command_suggestion = db.get_backup_command_suggestion(tipo=tipo_backup)
                if command_suggestion:
                    print("\n--- Comando Suggerito (da eseguire nella shell) ---")
                    print(command_suggestion)
                    print("-" * 55)
                else:
                    print("Errore nel generare il suggerimento del comando.")

        elif scelta == "2":
            stampa_intestazione("LOG BACKUP RECENTI")
            limit_str = get_validated_input("Numero di log da visualizzare (default 20)", validation_type='int', required=False)
            limit = int(limit_str) if limit_str else 20
            logs = db.get_backup_logs(limit=limit)
            if logs:
                 # Prepara i dati per display_table
                 headers = ["ID", "Timestamp", "Tipo", "Esito", "Utente", "Nome File", "Dimensione", "Percorso", "Messaggio"]
                 log_data = []
                 for log in logs:
                      esito_str = "OK" if log.get('esito', False) else "FALLITO"
                      dim_bytes = log.get('dimensione_bytes')
                      dim_str = f"{dim_bytes} bytes" if dim_bytes is not None else "N/D"
                      log_data.append([
                           log.get('id', 'N/D'),
                           log.get('timestamp', 'N/D'),
                           log.get('tipo', 'N/D'),
                           esito_str,
                           log.get('utente', 'N/D'),
                           log.get('nome_file', 'N/D'),
                           dim_str,
                           log.get('percorso_file', 'N/D'),
                           log.get('messaggio', '')
                      ])
                 display_table(log_data, headers=headers)
            else:
                 print("Nessun log di backup trovato.")


        elif scelta == "3":
            stampa_intestazione("OTTIENI COMANDO RESTORE")
            log_id_str = get_validated_input("ID del log di backup da cui ripristinare", validation_type='int', required=True)
            if log_id_str:
                try:
                    log_id = int(log_id_str)
                    command_suggestion = db.get_restore_command_suggestion(log_id)
                    if command_suggestion:
                        print("\n--- Comando Suggerito (da eseguire nella shell) ---")
                        print(command_suggestion)
                        print("-" * 55)
                        print("\nATTENZIONE: Il restore sovrascriverà i dati attuali!")
                    else:
                        print(f"ID log {log_id} non valido, non trovato o errore nel generare il suggerimento.")
                except ValueError:
                     print("ID non valido.") # Già gestito
                except Exception as e:
                     print(f"Errore: {e}")

        elif scelta == "4":
             stampa_intestazione("REGISTRA BACKUP MANUALE")
             nome_file = get_validated_input("Nome del file di backup creato", required=True)
             if not nome_file: continue
             percorso_file = get_validated_input("Percorso completo del file", required=True)
             if not percorso_file: continue
             utente = get_validated_input("Utente che ha eseguito il backup (default: 'manuale')", required=False) or 'manuale'
             tipo = get_validated_input("Tipo", required=True, choices=['completo', 'schema', 'dati'])
             if not tipo: continue
             esito = ask_yes_no("Il backup è andato a buon fine?", default=True)
             messaggio = get_validated_input("Messaggio aggiuntivo (opzionale)", required=False)
             dimensione_str = get_validated_input("Dimensione in bytes (opzionale)", validation_type='int', required=False)
             try:
                 dimensione = int(dimensione_str) if dimensione_str else None
                 backup_id = db.register_backup_log(nome_file, utente, tipo, esito, percorso_file, dimensione, messaggio)
                 if backup_id:
                     print(f"Backup manuale registrato con ID: {backup_id}")
                 else:
                     print("Errore durante la registrazione del backup manuale.")
             except ValueError:
                  print("Dimensione non valida.")
             except Exception as e:
                  print(f"Errore: {e}")


        elif scelta == "5":
            stampa_intestazione("GENERA SCRIPT BACKUP AUTOMATICO")
            backup_dir = get_validated_input("Directory di destinazione per i backup (es. /var/backups/catasto)", required=True)
            if not backup_dir: continue
            script_name = get_validated_input("Nome del file per lo script (es. backup_catasto.sh)", required=True)
            if not script_name: continue

            script_content = db.generate_backup_script(backup_dir)
            if script_content:
                try:
                    save_path = os.path.join(os.getcwd(), script_name) # Salva nella directory corrente
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(script_content)
                    # Prova a rendere eseguibile (funziona su Linux/Mac)
                    try:
                         os.chmod(save_path, 0o755)
                    except OSError:
                         print(f"Attenzione: Impossibile impostare permessi eseguibili per {script_name} (potrebbe essere Windows).")
                    print(f"\nScript '{script_name}' generato con successo in: {save_path}")
                    print("Istruzioni:")
                    print(f"1. Sposta lo script sul server del database.")
                    print(f"2. Assicurati che la directory '{backup_dir}' esista sul server e sia scrivibile dall'utente PostgreSQL.")
                    print("3. Configura un cron job (Linux/macOS) o un Task Scheduler (Windows) per eseguirlo regolarmente.")
                except IOError as e:
                    print(f"Errore durante il salvataggio dello script: {e}")
                except Exception as e:
                     print(f"Errore imprevisto: {e}")
            else:
                print("Errore durante la generazione dello script.")

        elif scelta == "6":
            stampa_intestazione("PULISCI LOG BACKUP VECCHI")
            giorni_str = get_validated_input("Conserva i log degli ultimi quanti giorni? (default: 30)", validation_type='int', required=False)
            try:
                giorni = int(giorni_str) if giorni_str else 30
                print(f"\nVerranno eliminati i log di backup più vecchi di {giorni} giorni.")
                if ask_yes_no("Procedere?", default=False):
                    if db.cleanup_old_backup_logs(giorni):
                        print("Pulizia dei log vecchi completata.")
                    else:
                        print("Errore durante la pulizia dei log.")
                else:
                     print("Operazione annullata.")
            except ValueError:
                print("Numero di giorni non valido.")
            except Exception as e:
                 print(f"Errore: {e}")

        elif scelta == "7":
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")


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
        print("\n8. Torna al menu principale")

        scelta = get_validated_input("Seleziona un'opzione", validation_type='int', required=True)
        if not scelta: continue

        if scelta == "1":
            stampa_intestazione("PERIODI STORICI")
            periodi = db.get_historical_periods()
            display_table(periodi, headers=['id', 'nome', 'anno_inizio', 'anno_fine', 'descrizione'])

        elif scelta == "2":
            stampa_intestazione("OTTIENI NOME STORICO ENTITÀ")
            tipo_entita = get_validated_input("Tipo entità", required=True, choices=['comune', 'localita'])
            if not tipo_entita: continue
            entita_id_str = get_validated_input(f"ID {tipo_entita}", validation_type='int', required=True)
            if not entita_id_str: continue
            anno_str = get_validated_input("Anno (lascia vuoto per anno corrente)", validation_type='int', required=False)
            try:
                entita_id = int(entita_id_str)
                anno = int(anno_str) if anno_str else None # Passa None se vuoto

                nome_info = db.get_historical_name(tipo_entita, entita_id, anno)
                if nome_info:
                    anno_usato = anno if anno else datetime.now().year
                    fine = nome_info.get('anno_fine', 'oggi')
                    print(f"\nNome in anno {anno_usato}: {nome_info['nome']}")
                    print(f"  Periodo: {nome_info['periodo_nome']} ({nome_info['anno_inizio']} - {fine})")
                else:
                    print(f"Nessun nome storico trovato per {tipo_entita} ID {entita_id} nell'anno specificato.")
            except ValueError:
                print("ID entità non valido.") # Gestito da helper
            except Exception as e:
                 print(f"Errore: {e}")

        elif scelta == "3":
            stampa_intestazione("REGISTRA NOME STORICO")
            tipo_entita = get_validated_input("Tipo entità", required=True, choices=['comune', 'localita'])
            if not tipo_entita: continue
            entita_id_str = get_validated_input(f"ID {tipo_entita}", validation_type='int', required=True)
            if not entita_id_str: continue
            nome_storico = get_validated_input("Nome storico", required=True)
            if not nome_storico: continue

            # Mostra i periodi disponibili per la selezione
            print("\nPeriodi storici disponibili:")
            periodi = db.get_historical_periods()
            if not periodi:
                print("Nessun periodo storico definito nel DB. Impossibile procedere.")
                continue
            period_choices = [str(p['id']) for p in periodi] # ID come stringhe per choices
            display_table(periodi, headers=['id', 'nome', 'anno_inizio', 'anno_fine'])

            periodo_id_str = get_validated_input("ID Periodo storico", required=True, choices=period_choices)
            if not periodo_id_str: continue
            anno_inizio_str = get_validated_input("Anno inizio validità nome", validation_type='int', required=True)
            if not anno_inizio_str: continue
            anno_fine_str = get_validated_input("Anno fine validità nome (opzionale)", validation_type='int', required=False)
            note = get_validated_input("Note (opzionale)", required=False)

            try:
                entita_id = int(entita_id_str)
                periodo_id = int(periodo_id_str)
                anno_inizio = int(anno_inizio_str)
                anno_fine = int(anno_fine_str) if anno_fine_str else None

                if db.register_historical_name(tipo_entita, entita_id, nome_storico, periodo_id, anno_inizio, anno_fine, note):
                    print("Nome storico registrato con successo.")
                else:
                    print("Errore durante la registrazione del nome storico.")

            except ValueError:
                print("Input numerico non valido (ID o Anno).")
            except Exception as e:
                 print(f"Errore imprevisto: {e}")

        elif scelta == "4":
             stampa_intestazione("RICERCA DOCUMENTI STORICI")
             titolo = get_validated_input("Titolo (parziale, opzionale)", required=False)
             tipo_doc = get_validated_input("Tipo documento (esatto, opzionale)", required=False)
             periodo_id_str = get_validated_input("ID Periodo storico (opzionale)", validation_type='int', required=False)
             anno_inizio_str = get_validated_input("Anno inizio (opzionale)", validation_type='int', required=False)
             anno_fine_str = get_validated_input("Anno fine (opzionale)", validation_type='int', required=False)
             partita_id_str = get_validated_input("ID Partita collegata (opzionale)", validation_type='int', required=False)

             try:
                 periodo_id = int(periodo_id_str) if periodo_id_str else None
                 anno_inizio = int(anno_inizio_str) if anno_inizio_str else None
                 anno_fine = int(anno_fine_str) if anno_fine_str else None
                 partita_id = int(partita_id_str) if partita_id_str else None

                 documenti = db.search_historical_documents(
                     title=titolo, doc_type=tipo_doc, period_id=periodo_id,
                     year_start=anno_inizio, year_end=anno_fine, partita_id=partita_id
                 )
                 display_table(documenti, headers=['documento_id', 'titolo', 'tipo_documento', 'anno', 'periodo_nome', 'descrizione', 'partite_correlate'])
             except ValueError:
                  print("Input ID o Anno non valido.")
             except Exception as e:
                  print(f"Errore: {e}")

        elif scelta == "5":
            stampa_intestazione("ALBERO GENEALOGICO PROPRIETÀ")
            partita_id_str = get_validated_input("ID della partita di partenza", validation_type='int', required=True)
            if partita_id_str:
                try:
                    partita_id = int(partita_id_str)
                    albero = db.get_property_genealogy(partita_id)
                    if albero:
                         # Formattazione speciale per l'albero
                         print("\nAlbero Genealogico:")
                         headers = ['Livello', 'Relazione', 'ID Partita', 'Comune', 'N. Partita', 'Tipo', 'Possessori', 'Data Variazione']
                         table_data = []
                         for nodo in albero:
                              table_data.append([
                                   nodo.get('livello', '?'),
                                   nodo.get('tipo_relazione', ''),
                                   nodo.get('partita_id', ''),
                                   nodo.get('comune_nome', ''),
                                   nodo.get('numero_partita', ''),
                                   nodo.get('tipo', ''),
                                   nodo.get('possessori', ''),
                                   nodo.get('data_variazione', 'N/D')
                              ])
                         print(tabulate(table_data, headers=headers, tablefmt="grid"))
                    else:
                        print("Impossibile generare l'albero genealogico per la partita specificata.")
                except ValueError:
                     print("ID partita non valido.")
                except Exception as e:
                     print(f"Errore: {e}")

        elif scelta == "6":
             stampa_intestazione("STATISTICHE CATASTALI PER PERIODO")
             comune = get_validated_input("Filtra per comune (opzionale)", required=False)
             anno_i_str = get_validated_input("Anno inizio (default 1900)", validation_type='int', required=False)
             anno_f_str = get_validated_input("Anno fine (default anno corrente)", validation_type='int', required=False)
             try:
                  anno_i = int(anno_i_str) if anno_i_str else 1900
                  anno_f = int(anno_f_str) if anno_f_str else None # Passa None se vuoto

                  stats = db.get_cadastral_stats_by_period(
                      comune=comune, year_start=anno_i, year_end=anno_f
                  )
                  display_table(stats, headers=['anno', 'comune_nome', 'nuove_partite', 'partite_chiuse', 'totale_partite_attive', 'variazioni', 'immobili_registrati'])
             except ValueError:
                  print("Input Anno non valido.")
             except Exception as e:
                  print(f"Errore: {e}")

        elif scelta == "7":
            stampa_intestazione("COLLEGA DOCUMENTO A PARTITA")
            doc_id_str = get_validated_input("ID del Documento Storico", validation_type='int', required=True)
            if not doc_id_str: continue
            part_id_str = get_validated_input("ID della Partita da collegare", validation_type='int', required=True)
            if not part_id_str: continue
            rilevanza = get_validated_input("Rilevanza", required=False, choices=['primaria', 'secondaria', 'correlata']) or 'correlata'
            note = get_validated_input("Note (opzionale)", required=False)
            try:
                doc_id = int(doc_id_str)
                part_id = int(part_id_str)
                if db.link_document_to_partita(doc_id, part_id, rilevanza, note):
                    print("Collegamento creato/aggiornato con successo.")
                else:
                    print("Errore durante la creazione del collegamento.")
            except ValueError:
                 print("ID non valido.")
            except Exception as e:
                 print(f"Errore: {e}")

        elif scelta == "8":
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")

def menu_principale(db: CatastoDBManager):
    """Menu principale per testare varie funzionalità."""
    menu_options = {
        "1": ("Consultazione dati", menu_consultazione),
        "2": ("Inserimento e gestione dati", menu_inserimento),
        "3": ("Generazione report", menu_report),
        "4": ("Manutenzione database", menu_manutenzione),
        "5": ("Sistema di audit", menu_audit),
        "6": ("Gestione Utenti", menu_utenti),
        "7": ("Sistema di Backup", menu_backup),
        "8": ("Funzionalità Storiche Avanzate", menu_storico_avanzato),
        "9": ("Esci", None) # Usa None per l'uscita
    }

    while True:
        stampa_intestazione("MENU PRINCIPALE")
        for key, (desc, _) in menu_options.items():
             print(f"{key}. {desc}")

        scelta = input(f"\nSeleziona un'opzione (1-{len(menu_options)}): ")

        if scelta in menu_options:
            desc, func = menu_options[scelta]
            if func:
                try:
                    func(db) # Chiama la funzione del menu corrispondente
                except Exception as menu_err:
                     # Cattura errori non gestiti all'interno dei menu
                     print(f"\nERRORE IMPREVISTO nel menu '{desc}': {menu_err}")
                     logger.exception(f"Errore non gestito nel menu {desc}")
                     input("\nPremi INVIO per continuare...")
            else:
                # Opzione Esci
                break
        else:
            print("Opzione non valida!")


# === MAIN EXECUTION BLOCK ===

def main():
    # Carica configurazione da file .env
    load_dotenv()
    db_config = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "schema": os.getenv("DB_SCHEMA", "catasto") # Default se non specificato
    }

    # Verifica parametri essenziali
    required_params = ["dbname", "user", "password", "host", "port"]
    missing_params = [p for p in required_params if not db_config.get(p)]
    if missing_params:
        print(f"ERRORE: Parametri di configurazione mancanti nel file .env: {', '.join(missing_params)}")
        sys.exit(1)

    # Converti porta a intero
    try:
         db_config["port"] = int(db_config["port"])
    except (ValueError, TypeError):
         print(f"ERRORE: Porta DB non valida nel file .env: {db_config['port']}")
         sys.exit(1)

    # Inizializza il gestore con la configurazione caricata
    db = CatastoDBManager(**db_config)

    # Verifica la connessione
    if not db.connect():
        print("ERRORE: Impossibile connettersi al database. Verifica i parametri nel file .env e lo stato del server DB.")
        sys.exit(1)

    try:
        menu_principale(db)
    except KeyboardInterrupt:
        print("\nOperazione interrotta dall'utente.")
    except Exception as global_err:
         print(f"\nERRORE GLOBALE NON GESTITO: {global_err}")
         logger.exception("Errore globale non gestito nell'applicazione.")
    finally:
        # Assicurati che la connessione sia chiusa all'uscita
        db.disconnect()
        print("\nConnessione al database chiusa. Uscita.")

if __name__ == "__main__":
    main()