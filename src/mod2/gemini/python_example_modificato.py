#!/usr/bin/env python3
# -*- coding: utf-8 -*-\
"""
Esempio di utilizzo del gestore database catastale - Versione Completa Riscritto e Integrato
=========================================================================================
Script completo per interagire con il database catastale storico.

Include:
- Configurazione esterna tramite .env
- Validazione input centralizzata con get_validated_input
- Sicurezza password con bcrypt e getpass
- Formattazione output tabellare con tabulate
- Gestione sessione utente per integrazione con audit log
- Implementazione completa di tutti i menu

Autore: Marco Santoro
Data: 24/04/2025
"""

# Import necessari
import sys
import os
import json
from datetime import date, datetime
import getpass
from typing import Optional, List, Dict, Any, Union

# Import librerie esterne
try:
    import bcrypt
    from tabulate import tabulate
    from dotenv import load_dotenv
except ImportError as ie:
    print(f"ERRORE: Libreria mancante - {ie}. Eseguire 'pip install bcrypt tabulate python-dotenv'")
    sys.exit(1)

# Import classe gestore DB
try:
    from catasto_db_manager import CatastoDBManager, logger
except ImportError:
    print("ERRORE: Impossibile importare 'CatastoDBManager'. Assicurati che 'catasto_db_manager.py' sia nella stessa directory.")
    sys.exit(1)

# === STATO SESSIONE GLOBALE ===
SESSION_INFO: Dict[str, Optional[Union[int, str]]] = {
    "user_id": None,
    "username": None,
    "session_id": None
}

# === HELPER FUNCTIONS ===

def stampa_intestazione(titolo: str):
    """Stampa un'intestazione formattata."""
    bar = "=" * 80
    print(f"\n{bar}")
    print(f" {titolo} ".center(80, "="))
    print(bar)

def get_validated_input(prompt: str, validation_type: str = 'text', required: bool = True, choices: Optional[List[Any]] = None) -> Optional[str]:
    """Richiede input all'utente con validazione."""
    prompt_suffix = (" (obbligatorio): " if required else " (opzionale, INVIO per saltare): ")
    input_function = getpass.getpass if validation_type == 'password' else input
    while True:
        try:
            user_input = input_function(prompt + prompt_suffix).strip()
            if not user_input:
                if required: print(" >> Errore: Campo obbligatorio."); continue
                else: return None
            if validation_type == 'int':
                int(user_input); return user_input
            elif validation_type == 'float':
                normalized = user_input.replace(',', '.'); float(normalized); return normalized
            elif validation_type == 'date':
                datetime.strptime(user_input, "%Y-%m-%d"); return user_input
            elif validation_type == 'choice' and choices:
                str_choices = [str(c).lower() for c in choices]
                if user_input.lower() not in str_choices:
                    print(f" >> Errore: Scelte valide: {', '.join(map(str, choices))}"); continue
                return user_input
            elif validation_type == 'email':
                parts = user_input.split('@');
                if len(parts) != 2 or '.' not in parts[1] or not parts[1].split('.')[-1]: print(" >> Errore: Email non valida."); continue
                return user_input
            elif validation_type in ['text', 'password', 'choice']: return user_input
            else: print(f" >> Errore interno: tipo validazione '{validation_type}' non gestito."); return None
        except ValueError: print(" >> Errore: Input numerico o data non valido.")
        except EOFError: print("\nInput interrotto."); return None
        except KeyboardInterrupt: print("\nOperazione annullata."); sys.exit(0)

def display_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None, tablefmt: str = "pretty", max_col_width: Optional[int] = None):
    """Visualizza dati tabellari usando tabulate."""
    if not data: print(" -- Nessun dato da visualizzare --"); return
    if not headers: headers = list(data[0].keys()) if data else []
    if not headers: print(" -- Dati presenti ma nessun header --"); return
    table_data = []
    for item in data:
        row = []
        for header in headers:
            value = item.get(header, 'N/D')
            str_value = str(value) if value is not None else 'N/D'
            if max_col_width and len(str_value) > max_col_width: str_value = str_value[:max_col_width - 3] + "..."
            row.append(str_value)
        table_data.append(row)
    formatted_headers = [h.replace('_', ' ').title() for h in headers]
    try: print(tabulate(table_data, headers=formatted_headers, tablefmt=tablefmt, missingval="N/D"))
    except Exception as e: print(f"Errore tabulate: {e}"); print(formatted_headers); [print(row) for row in table_data]

def ask_yes_no(prompt: str, default: Optional[bool] = None) -> bool:
    """Fa una domanda Sì/No, restituendo booleano."""
    choices = "[s/n]" if default is None else ("[S/n]" if default else "[s/N]")
    while True:
        resp_str = input(f"{prompt} {choices}: ").strip().lower()
        if not resp_str:
            if default is not None: return default
            else: print(" >> Risposta richiesta."); continue
        if resp_str in ['s', 'si', 'sì', 'y', 'yes']: return True
        if resp_str in ['n', 'no']: return False
        print(" >> Risposta non valida. Inserire 's' o 'n'.")

def set_session_vars_for_audit(db: CatastoDBManager):
     """Imposta le variabili di sessione DB per l'audit trigger."""
     user_id_str = str(SESSION_INFO["user_id"]) if SESSION_INFO["user_id"] is not None else None
     session_id_str = str(SESSION_INFO["session_id"]) if SESSION_INFO["session_id"] is not None else None
     # logger.debug(f"Impostazione var sessione: user={user_id_str}, session={session_id_str}")
     db.set_session_variable('app.user_id', user_id_str)
     db.set_session_variable('app.session_id', session_id_str)

# === FUNZIONI SPECIFICHE DI INSERIMENTO ===

def inserisci_possessore(db: CatastoDBManager, comune_preselezionato: Optional[str] = None) -> Optional[int]:
    """Funzione guidata per inserire/trovare un possessore."""
    stampa_intestazione("AGGIUNGI NUOVO POSSESSORE")
    if not comune_preselezionato: comune = get_validated_input("Comune residenza", required=True);
    else: comune = comune_preselezionato; print(f"Comune: {comune}")
    if not comune: return None
    nome_completo = get_validated_input("Nome completo", required=True)
    if not nome_completo: return None
    codice_fiscale = get_validated_input("Codice Fiscale (opz)", required=False)
    paternita = get_validated_input("Paternità (opz)", required=False)
    data_nascita_str = get_validated_input("Data nascita (YYYY-MM-DD, opz)", validation_type='date', required=False)
    luogo_nascita = get_validated_input("Luogo nascita (opz)", required=False)
    note = get_validated_input("Note (opz)", required=False)
    data_nascita = datetime.strptime(data_nascita_str, "%Y-%m-%d").date() if data_nascita_str else None
    try:
        set_session_vars_for_audit(db) # Audit
        possessore_id = db.inserisci_possessore(nome_completo=nome_completo, codice_fiscale=codice_fiscale, comune_residenza=comune, paternita=paternita, data_nascita=data_nascita, luogo_nascita=luogo_nascita, note=note)
        if possessore_id is not None: print(f" => Possessore '{nome_completo}' ID: {possessore_id}"); return possessore_id
        else: print(" >> Errore inserimento possessore."); return None
    except AttributeError: print(" >> ERRORE: Metodo 'inserisci_possessore' non trovato."); return None
    except Exception as e: print(f" >> Errore imprevisto: {e}"); return None

# === MENU FUNCTIONS ===

def menu_consultazione(db: CatastoDBManager):
    """Menu consultazione dati (sola lettura)."""
    while True:
        stampa_intestazione("CONSULTAZIONE DATI")
        options = { "1": "Elenco comuni", "2": "Elenco partite per comune", "3": "Elenco possessori per comune", "4": "Ricerca partite (Semplice)", "5": "Dettagli partita", "6": "Elenco localita per comune", "7": "Ricerca Avanzata Possessori (Similarità)", "8": "Ricerca Avanzata Immobili", "9": "Cerca Immobili Specifici", "10": "Cerca Variazioni", "11": "Cerca Consultazioni", "12": "Esporta Partita in JSON", "13": "Esporta Possessore in JSON", "14": "Torna al menu principale" }
        for k, v in options.items(): print(f"{k.rjust(2)}. {v}")
        scelta = get_validated_input("\nSeleziona", validation_type='choice', choices=list(options.keys()))
        if not scelta: continue
        try:
            if scelta == "1": stampa_intestazione(options[scelta]); display_table(db.get_comuni(), ['nome', 'provincia', 'regione'])
            # --- BLOCCO CORRETTO per scelta == "2" ---
            elif scelta == "2":
                stampa_intestazione(options[scelta]) # options["2"] == "Elenco partite per comune"
                comune = get_validated_input("Nome Comune", required=True)
                if comune:
                    # Chiama il metodo del DB e passa gli header a display_table
                    partite = db.get_partite_per_comune(comune)
                    display_table(partite,
                                  headers=['id', 'numero_partita', 'tipo', 'stato', 'data_impianto'])
            # --- FINE BLOCCO CORRETTO ---
            # --- BLOCCO CORRETTO per scelta == "3" ---
            elif scelta == "3":
                stampa_intestazione(options[scelta]) # options["3"] == "Elenco possessori per comune"
                comune = get_validated_input("Nome Comune", required=True)
                if comune:
                    # Chiama il metodo DB e passa gli header a display_table
                    possessori = db.get_possessori_per_comune(comune)
                    display_table(possessori,
                                  headers=['id', 'nome_completo', 'paternita', 'data_nascita'])
            # --- FINE BLOCCO CORRETTO ---
            elif scelta == "4":
                stampa_intestazione(options[scelta]); com = get_validated_input("Comune (opz)", False); tipo = get_validated_input("Tipo (Terreni/Fabbricati, opz)", False, ['Terreni','Fabbricati']); stato = get_validated_input("Stato (attiva/inattiva, opz)", False, ['attiva', 'inattiva']); p_nome = get_validated_input("Nome Possessore (parz, opz)", False); n_imm = get_validated_input("Natura Immobile (parz, opz)", False)
                display_table(db.search_partite(com, tipo, stato, p_nome, n_imm), ['id', 'numero_partita', 'comune_nome', 'tipo', 'stato', 'possessori', 'immobili'], max_col_width=25)
            elif scelta == "5":
                 stampa_intestazione(options[scelta]); p_id = get_validated_input("ID Partita", True, 'int')
                 if p_id:
                      det = db.get_partita_details(int(p_id))
                      if det and isinstance(det, dict): print("\n--- Dettagli Partita ---"); display_table([det.get('partita_info', {})]); print("\n--- Possessori ---"); display_table(det.get('possessori', []), ['id', 'nome_completo', 'titolo', 'quota']); print("\n--- Immobili ---"); display_table(det.get('immobili', []), ['id', 'natura', 'piani', 'vani', 'localita'])
                      else: print(f" >> Nessun dettaglio trovato per partita ID {p_id}.")
            # --- BLOCCO CORRETTO per scelta == "6" ---
            elif scelta == "6":
                stampa_intestazione(options[scelta]) # options["6"] == "Elenco localita per comune"
                comune = get_validated_input("Nome Comune", required=True)
                if comune:
                    localita_list = db.get_localita_per_comune(comune)
                    display_table(localita_list,
                                  headers=['id', 'nome', 'tipo_localita', 'note'])
            # --- FINE BLOCCO CORRETTO ---
            elif scelta == "7":
                 stampa_intestazione(options[scelta]); q_txt = get_validated_input("Termine ricerca nome/cognome/paternità", True)
                 if q_txt:
                      res = db.ricerca_avanzata_possessori(q_txt)
                      if res: fmt = [{'ID': r['id'], 'Nome': r['nome_completo'], 'Comune': r['comune_nome'], 'Simil(%)': round(r['similarity']*100,1), 'N.Part': r['num_partite']} for r in res]; display_table(fmt)
                      else: print(" -- Nessun risultato --")
            elif scelta == "8":
                 stampa_intestazione(options[scelta]); com = get_validated_input("Comune (opz)", False); nat = get_validated_input("Natura (opz)", False); loc = get_validated_input("Località (opz)", False); clas = get_validated_input("Classificazione (opz)", False); poss = get_validated_input("Possessore (opz)", False)
                 display_table(db.ricerca_avanzata_immobili(com, nat, loc, clas, poss), ['immobile_id', 'natura', 'localita_nome', 'comune', 'classificazione', 'possessori', 'partita_numero'])
            elif scelta == "9":
                 stampa_intestazione(options[scelta]); p_id = get_validated_input("ID Partita (opz)", False, 'int'); com = get_validated_input("Comune (opz)", False); l_id = get_validated_input("ID Località (opz)", False, 'int'); nat = get_validated_input("Natura (parz, opz)", False); clas = get_validated_input("Classificazione (esatta, opz)", False)
                 display_table(db.search_immobili(int(p_id) if p_id else None, com, int(l_id) if l_id else None, nat, clas), ['id', 'natura', 'piani', 'vani', 'classificazione', 'localita', 'comune', 'partita'])
            elif scelta == "10":
                 stampa_intestazione(options[scelta]); tipo = get_validated_input("Tipo (es. Vendita, opz)", False); d_i = get_validated_input("Data inizio (YYYY-MM-DD, opz)", False, 'date'); d_f = get_validated_input("Data fine (YYYY-MM-DD, opz)", False, 'date'); p_o = get_validated_input("ID Part Orig (opz)", False, 'int'); p_d = get_validated_input("ID Part Dest (opz)", False, 'int'); com = get_validated_input("Comune Orig (opz)", False)
                 data_i = datetime.strptime(d_i, "%Y-%m-%d").date() if d_i else None; data_f = datetime.strptime(d_f, "%Y-%m-%d").date() if d_f else None; p_o_id = int(p_o) if p_o else None; p_d_id = int(p_d) if p_d else None
                 display_table(db.search_variazioni(tipo, data_i, data_f, p_o_id, p_d_id, com), ['id', 'tipo', 'data_variazione', 'partita_origine', 'comune', 'partita_destinazione', 'rif_numero', 'rif_nominativo'])
            elif scelta == "11":
                 stampa_intestazione(options[scelta]); d_i = get_validated_input("Data inizio (YYYY-MM-DD, opz)", False, 'date'); d_f = get_validated_input("Data fine (YYYY-MM-DD, opz)", False, 'date'); ric = get_validated_input("Richiedente (parz, opz)", False); fun = get_validated_input("Funzionario (parz, opz)", False)
                 data_i = datetime.strptime(d_i, "%Y-%m-%d").date() if d_i else None; data_f = datetime.strptime(d_f, "%Y-%m-%d").date() if d_f else None
                 display_table(db.search_consultazioni(data_i, data_f, ric, fun), ['id', 'data', 'richiedente', 'doc_id', 'motivazione', 'materiale', 'funzionario'])
            # --- BLOCCO CORRETTO E RE-INDENTATO per scelta == "12" ---
            elif scelta == "12":
                stampa_intestazione(options[scelta]) # options["12"] == "Esporta Partita in JSON"
                partita_id_str = get_validated_input("ID della Partita da esportare", validation_type='int', required=True)
                if partita_id_str:
                    try:
                        partita_id = int(partita_id_str)
                        json_data = db.export_partita_json(partita_id)
                        if json_data:
                            print("\n--- DATI JSON PARTITA ---")
                            print(json_data) # Già formattato da db manager
                            print("-" * 25)
                            filename = f"partita_{partita_id}.json"
                            # Questo blocco IF deve essere indentato sotto l'IF precedente
                            if ask_yes_no(f"Salvare in '{filename}'?", default=True):
                                # Questo blocco TRY deve essere indentato sotto l'IF ask_yes_no
                                try:
                                    # Questo blocco WITH deve essere indentato sotto il TRY
                                    with open(filename, 'w', encoding='utf-8') as f:
                                        f.write(json_data)
                                    # Questo PRINT deve essere indentato come WITH (ma fuori da esso)
                                    print(f" => Dati salvati in {filename}")
                                # Questo EXCEPT deve essere allineato con il TRY corrispondente
                                except IOError as e:
                                     print(f" >> Errore di scrittura file: {e}")
                        # Questo ELSE deve essere allineato con l'IF json_data
                        else:
                            print(" >> Partita non trovata o errore durante l'esportazione.")
                    # Questo EXCEPT deve essere allineato con il TRY esterno
                    except ValueError:
                        print(" >> ID non valido.")
                    # Questo EXCEPT deve essere allineato con il TRY esterno
                    except Exception as e:
                         print(f" >> Errore imprevisto: {e}")
            # --- FINE BLOCCO CORRETTO ---
            elif scelta == "13":
                 stampa_intestazione(options[scelta]); p_id = get_validated_input("ID Possessore", True, 'int')
                 if p_id:
                     json_data = db.export_possessore_json(int(p_id))
                     if json_data: print("\n--- JSON POSSESSORE ---\n" + json_data); fn=f"poss_{p_id}.json";
                     # --- Blocco Corretto per Salvataggio File (Possessore) ---
                     if ask_yes_no(f"Salvare in '{filename}'?", default=True):
                         try:
                             with open(filename, 'w', encoding='utf-8') as f:
                                 f.write(json_data)
                             print(f" => Dati salvati in {filename}")
                         except IOError as e:
                              print(f" >> Errore di scrittura file: {e}")
                    # --- Fine Blocco Corretto ---
                     else: print(" >> Esportazione fallita.")
            elif scelta == "14": break
            else: print(" >> Opzione non valida!")
        except ValueError: print(" >> Errore: Input numerico o data non valido.")
        except Exception as e: print(f" >> Errore imprevisto consultazione: {e}")
        input("\nPremi INVIO per continuare...")

def menu_inserimento(db: CatastoDBManager):
    """Menu inserimento e gestione dati (con audit)."""
    while True:
        stampa_intestazione("INSERIMENTO E GESTIONE DATI")
        options = { "1": "Aggiungi comune", "2": "Aggiungi possessore", "3": "Aggiungi localita", "4": "Registra nuova proprieta", "5": "Registra passaggio proprieta", "6": "Registra consultazione", "7": "Inserisci Contratto", "8": "Duplica Partita", "9": "Trasferisci Immobile", "10": "Torna al menu principale"}
        for k, v in options.items(): print(f"{k.rjust(2)}. {v}")
        scelta = get_validated_input("\nSeleziona", validation_type='choice', choices=list(options.keys()))
        if not scelta: continue

        audited_ops = ["1", "2", "3", "4", "5", "7", "8", "9"] # Esclude Registra consultazione (6)
        needs_audit_check = scelta in audited_ops
        user_logged_in = SESSION_INFO["user_id"] is not None

        if needs_audit_check and not user_logged_in:
             print("\n !! ATTENZIONE: Nessun utente loggato. Operazione non correttamente auditata. Procedere? !!")
             if not ask_yes_no("Confermi?", default=False): continue
        if needs_audit_check: set_session_vars_for_audit(db) # Imposta comunque (NULL se non loggato)

        try:
            if scelta == "1":
                stampa_intestazione(options[scelta]); nome=get_validated_input("Nome",True); prov=get_validated_input("Prov (SV)",True); reg=get_validated_input("Regione",True)
                if nome and prov and reg:
                    if db.insert_comune(nome, prov, reg): print(f" => Comune '{nome}' OK.")
                    else: print(" >> Errore DB.")
            elif scelta == "2": inserisci_possessore(db) # Audit già dentro la funzione
            elif scelta == "3":
                 stampa_intestazione(options[scelta]); com=get_validated_input("Comune appartenenza", True);
                 if not com: continue; nome_loc=get_validated_input("Nome Località", True);
                 if not nome_loc: continue; tipo=get_validated_input("Tipo (opz)", False); note=get_validated_input("Note (opz)", False)
                 loc_id = db.insert_localita(com, nome_loc, tipo, note)
                 if loc_id is not None: print(f" => Località '{nome_loc}' OK (ID: {loc_id}).")
                 else: print(" >> Errore DB.")
            elif scelta == "4": # Registra Nuova Proprietà
                 stampa_intestazione(options[scelta]); print(" --- Dati Partita ---")
                 com=get_validated_input("Comune", True); num_p=get_validated_input("Numero Partita", True, 'int'); tipo_p=get_validated_input("Tipo", True, ['Terreni','Fabbricati']); data_i=get_validated_input("Data Impianto (YYYY-MM-DD)", True, 'date')
                 if not all([com, num_p, tipo_p, data_i]): print(" >> Dati partita mancanti."); continue
                 poss_info = []; print("\n--- Possessori ---")
                 while True: nome=get_validated_input(f"Nome P.{len(poss_info)+1} (INVIO fine)", False);
                 if nome is None: break; titolo=get_validated_input("Titolo", True); quota=get_validated_input("Quota (opz)", False); poss_info.append({'nome_completo':nome, 'titolo':titolo, 'quota':quota})
                 if not poss_info: print(" >> Almeno un possessore richiesto."); continue
                 imm_info = []; print("\n--- Immobili ---")
                 while True: natura=get_validated_input(f"Natura Imm.{len(imm_info)+1} (INVIO fine)", False);
                 if natura is None: break; loc=get_validated_input("Località", True); piani=get_validated_input("Piani (opz)", False, 'int'); vani=get_validated_input("Vani (opz)", False, 'int'); cons=get_validated_input("Consistenza (opz)", False); clas=get_validated_input("Classe (opz)", False)
                 if not loc: print("Località obbligatoria."); continue; imm_info.append({'natura':natura, 'localita':loc, 'numero_piani':int(piani) if piani else None, 'numero_vani':int(vani) if vani else None, 'consistenza':cons, 'classificazione':clas})
                 if not imm_info: print(" >> Almeno un immobile richiesto."); continue
                 data_imp = datetime.strptime(data_i, "%Y-%m-%d").date()
                 if db.registra_nuova_proprieta_v2(com, num_p, tipo_p, data_imp, poss_info, imm_info): print(f" => Registrazione proprietà {num_p} OK.")
                 else: print(" >> Errore registrazione proprietà.")
            elif scelta == "5": # Registra Passaggio Proprietà
                 stampa_intestazione(options[scelta]); p_id_orig = get_validated_input("ID Partita origine", True, 'int')
                 if not p_id_orig: continue; tipo_var=get_validated_input("Tipo variazione", True, ['Vendita','Successione','Donazione','Divisione','Altro']); data_var=get_validated_input("Data variazione (YYYY-MM-DD)", True, 'date')
                 if not tipo_var or not data_var: continue
                 data_v = datetime.strptime(data_var, "%Y-%m-%d").date()
                 poss_uscenti_ids = []; print("\n--- Possessori Uscenti (ID) ---")
                 # --- Blocco Corretto: Possessori Uscenti ---
            print("\n--- Specificare ID Possessori USCENTI ---")
            while True:
                pid_str = get_validated_input("ID (INVIO per terminare)", validation_type='int', required=False)
                if pid_str is None:
                    break # Esce dal ciclo while se l'utente preme INVIO
                try:
                    possessori_uscenti_ids.append(int(pid_str))
                except ValueError: # Anche se get_validated_input valida, doppia sicurezza
                    print(" >> ID non valido.")
            # --- Fine Blocco Corretto ---
            elif scelta == "6": # Registra Consultazione (Non auditato di default)
                 stampa_intestazione(options[scelta]); ric=get_validated_input("Richiedente",True); did=get_validated_input("Doc ID (opz)",False); motiv=get_validated_input("Motivazione",True); mat=get_validated_input("Materiale",True); funz=get_validated_input("Funzionario",True); data_str=get_validated_input("Data (YYYY-MM-DD, def oggi)",False,'date')
                 if ric and motiv and mat and funz: data_c = datetime.strptime(data_str, "%Y-%m-%d").date() if data_str else date.today();
                 if db.registra_consultazione(data_c, ric, motiv, mat, funz, did): print(" => Consultazione registrata.")
                 else: print(" >> Errore.")
            elif scelta == "7": # Inserisci Contratto
                 stampa_intestazione(options[scelta]); var_id = get_validated_input("ID Variazione", True, 'int'); tipo_c = get_validated_input("Tipo", True); data_c = get_validated_input("Data (YYYY-MM-DD)", True, 'date'); notaio=get_validated_input("Notaio (opz)", False); rep=get_validated_input("Repertorio (opz)", False); note=get_validated_input("Note (opz)", False)
                 if var_id and tipo_c and data_c: data_contr = datetime.strptime(data_c, "%Y-%m-%d").date();
                 if db.insert_contratto(int(var_id), tipo_c, data_contr, notaio, rep, note): print(" => Contratto inserito.")
                 else: print(" >> Errore.")
            elif scelta == "8": # Duplica Partita
                 stampa_intestazione(options[scelta]); p_orig = get_validated_input("ID Partita da duplicare", True, 'int'); n_num = get_validated_input("Nuovo numero", True, 'int')
                 if p_orig and n_num: m_poss=ask_yes_no("Mantenere possessori?", True); m_imm=ask_yes_no("Mantenere immobili?", False);
                 if db.duplicate_partita(int(p_orig), int(n_num), m_poss, m_imm): print(" => Partita duplicata.")
                 else: print(" >> Errore.")
            elif scelta == "9": # Trasferisci Immobile
                 stampa_intestazione(options[scelta]); imm_id = get_validated_input("ID Immobile", True, 'int'); p_dest = get_validated_input("ID Partita destinazione", True, 'int')
                 if imm_id and p_dest: reg_var=ask_yes_no("Registrare variazione?", False);
                 if db.transfer_immobile(int(imm_id), int(p_dest), reg_var): print(" => Immobile trasferito.")
                 else: print(" >> Errore.")
            elif scelta == "10": break
            else: print(" >> Opzione non valida!")
        except ValueError: print(" >> Errore: Input numerico o data non valido.")
        except Exception as e: print(f" >> Errore imprevisto: {e}")
        input("\nPremi INVIO per continuare...")


def menu_report(db: CatastoDBManager):
    """Menu generazione report (sola lettura)."""
    while True:
        stampa_intestazione("GENERAZIONE REPORT")
        options = { "1": "Certificato proprieta", "2": "Report genealogico (Partita)", "3": "Report Proprietà Possessore (Periodo)", "4": "Report consultazioni (Periodo)", "5": "Statistiche comune (MV)", "6": "Riepilogo immobili tipo (MV)", "7": "Partite Complete (MV)", "8": "Cronologia Variazioni (MV)", "9": "Report Annuale Partite Comune", "10": "Report Statistico Comune", "11": "Torna al menu principale"}
        for k, v in options.items(): print(f"{k.rjust(2)}. {v}")
        scelta = get_validated_input("\nSeleziona", validation_type='choice', choices=list(options.keys()))
        if not scelta: continue
        try:
            if scelta == "1":
                 stampa_intestazione(options[scelta]); p_id = get_validated_input("ID Partita", True, 'int')
                 if p_id: cert = db.genera_certificato_proprieta(int(p_id));
                 if cert: print("\n--- CERTIFICATO ---\n"+cert); fn=f"cert_{p_id}.txt";
                 if ask_yes_no(f"Salvare {fn}?",False): try:open(fn,'w',encoding='utf-8').write(cert);print("Salvato.") except IOError as e:print(f"Errore file:{e}")
                 else: print(" >> Errore generazione cert.")
            elif scelta == "2":
                 stampa_intestazione(options[scelta]); p_id = get_validated_input("ID Partita partenza", True, 'int')
                 if p_id: alb = db.get_property_genealogy(int(p_id)); display_table(alb, ['Livello','Relazione','ID Partita','Comune','N Partita','Tipo','Possessori','Data Var'])
            elif scelta == "3":
                 stampa_intestazione(options[scelta]); p_id = get_validated_input("ID Possessore", True, 'int'); d_i = get_validated_input("Data inizio (YYYY-MM-DD)", True, 'date'); d_f = get_validated_input("Data fine (YYYY-MM-DD)", True, 'date')
                 if p_id and d_i and d_f: data_i=datetime.strptime(d_i,"%Y-%m-%d").date(); data_f=datetime.strptime(d_f,"%Y-%m-%d").date(); rep=db.get_report_proprieta_possessore(int(p_id), data_i, data_f); display_table(rep, ['partita_id', 'num_partita', 'comune', 'titolo', 'quota', 'data_inizio', 'data_fine', 'immobili'])
            elif scelta == "4":
                 stampa_intestazione(options[scelta]); d_i = get_validated_input("Data inizio (YYYY-MM-DD)", True, 'date'); d_f = get_validated_input("Data fine (YYYY-MM-DD)", True, 'date')
                 if d_i and d_f: data_i=datetime.strptime(d_i,"%Y-%m-%d").date(); data_f=datetime.strptime(d_f,"%Y-%m-%d").date(); rep_txt=db.get_report_consultazioni(data_i, data_f)
                 if rep_txt: print("\n--- REPORT CONSULTAZIONI ---\n"+rep_txt); fn=f"rep_cons_{data_i}_{data_f}.txt";
                 if ask_yes_no(f"Salvare {fn}?", False): try:open(fn,'w',encoding='utf-8').write(rep_txt);print("Salvato.") except IOError as e:print(f"Errore file:{e}")
                 else: print(" >> Nessun dato trovato.")
            elif scelta == "5": stampa_intestazione(options[scelta]); display_table(db.get_statistiche_comune(), ['comune', 'provincia', 'tot_partite', 'p_attive', 'p_inattive', 'tot_poss', 'tot_imm'])
            elif scelta == "6": stampa_intestazione(options[scelta]); com = get_validated_input("Filtra comune (opz)", False); display_table(db.get_immobili_per_tipologia(com), ['comune', 'classificazione', 'num_imm', 'tot_piani', 'tot_vani'])
            elif scelta == "7": stampa_intestazione(options[scelta]); com = get_validated_input("Filtra comune (opz)", False); stato = get_validated_input("Stato (opz)", False, ['attiva','inattiva']); display_table(db.get_partite_complete_view(com, stato), ['partita_id', 'num_partita', 'comune', 'tipo', 'stato', 'data_imp', 'possessori', 'num_imm', 'tipi_imm', 'localita'], max_col_width=30)
            elif scelta == "8": stampa_intestazione(options[scelta]); com = get_validated_input("Comune orig (opz)", False); tipo = get_validated_input("Tipo var (opz)", False); display_table(db.get_cronologia_variazioni(com, tipo), ['var_id', 'tipo_var', 'data_var', 'part_orig', 'com_orig', 'part_dest', 'com_dest', 'tipo_contr', 'data_contr', 'notaio'], max_col_width=25)
            elif scelta == "9": stampa_intestazione(options[scelta]); com = get_validated_input("Comune", True); anno = get_validated_input("Anno", True, 'int'); if com and anno: display_table(db.get_report_annuale_partite(com, int(anno)), ['num_partita', 'tipo', 'stato', 'data_imp', 'possessori', 'num_imm', 'var_anno'])
            elif scelta == "10":
                 stampa_intestazione(options[scelta]); com = get_validated_input("Comune", True)
                 if com:
                      rep = db.get_report_comune(com)
                      if rep: print(f"\n--- Statistiche {rep.get('comune','N/D')} ---"); [print(f" {k.replace('_',' ').title()}: {v}") for k,v in rep.items() if k!='immobili_per_classe']; imm_cls = rep.get('immobili_per_classe'); print("\n Immobili/Classe:");
                      if isinstance(imm_cls, dict) and imm_cls: display_table([[k,v] for k,v in imm_cls.items()], ["Classe","Num"])
                      else: print("  N/D")
                      else: print(f" >> Report non generato per {com}.")
            elif scelta == "11": break
            else: print(" >> Opzione non valida!")
        except ValueError: print(" >> Errore: Input numerico o data non valido.")
        except Exception as e: print(f" >> Errore imprevisto report: {e}")
        input("\nPremi INVIO per continuare...")


def menu_manutenzione(db: CatastoDBManager):
    """Menu manutenzione database."""
    while True:
        stampa_intestazione("MANUTENZIONE DATABASE")
        options = { "1": "Verifica integrita (NON IMPL.)", "2": "Aggiorna Viste Materializzate", "3": "Esegui Manutenzione Generale", "4": "Analizza Query Lente", "5": "Controlla Frammentazione Indici", "6": "Ottieni Suggerimenti Ottimizzazione", "7": "Torna al menu principale" }
        for k, v in options.items(): print(f"{k.rjust(2)}. {v}")
        scelta = get_validated_input("\nSeleziona", validation_type='choice', choices=list(options.keys()))
        if not scelta: continue
        audited_ops = ["2"] # Solo aggiorna MV potrebbe essere auditato
        if scelta in audited_ops:
             if not SESSION_INFO["user_id"]: print("\n !! ATTENZIONE: Operazione non auditata (no login). !!")
             set_session_vars_for_audit(db)
        try:
            if scelta == "1": print(" Non implementato.")
            elif scelta == "2": stampa_intestazione(options[scelta]); print(" Avvio..."); if db.refresh_materialized_views(): print(" => Viste aggiornate.") else: print(" >> Errore.")
            elif scelta == "3": stampa_intestazione(options[scelta]); print(" VACUUM, ANALYZE... richiede tempo."); if ask_yes_no("Procedere?", False): print(" Esecuzione..."); if db.run_database_maintenance(): print(" => Manutenzione OK.") else: print(" >> Errore.") else: print(" Annullato.")
            elif scelta == "4":
                 stampa_intestazione(options[scelta]); print(" Richiede 'pg_stat_statements'."); min_d = get_validated_input("Durata min ms (def 1000)", False, 'int')
                 s_q = db.analyze_slow_queries(int(min_d) if min_d else 1000)
                 if s_q is not None:
                      if s_q: print(f"\n--- Query Lente (> {min_d or 1000} ms) ---"); sq_d = [{'ID':q['query_id'], 'Dur(ms)':round(q['durata_ms'],2), 'N':q['chiamate'], 'Righe':round(q['righe_restituite'],1), 'Query':(q['query_text'][:80]+'...') } for q in s_q]; display_table(sq_d)
                      else: print(f" -- Nessuna query lenta trovata --")
            elif scelta == "5":
                 stampa_intestazione(options[scelta]); print(" Esecuzione (output log DB)..."); f_ind = db.check_index_fragmentation()
                 if f_ind: print("\n--- Indici Frammentati (>30%) ---"); display_table(f_ind, ['schema', 'tabella', 'indice', 'ratio', 'dimensione']); print("\nConsidera REINDEX.")
                 elif f_ind == []: print(" -- Nessuna frammentazione >30% rilevata --")
                 else: print(" -- Verifica log DB --")
            elif scelta == "6": stampa_intestazione(options[scelta]); sugg = db.get_optimization_suggestions(); if sugg: print("\n--- Suggerimenti ---\n"+sugg); else: print(" >> Nessun suggerimento.")
            elif scelta == "7": break
            else: print(" >> Opzione non valida!")
        except ValueError: print(" >> Errore: Input numerico non valido.")
        except Exception as e: print(f" >> Errore imprevisto manutenzione: {e}")
        input("\nPremi INVIO per continuare...")


def menu_audit(db: CatastoDBManager):
    """Menu sistema di audit e attività utenti."""
    while True:
        stampa_intestazione("SISTEMA DI AUDIT E ATTIVITÀ UTENTI")
        options = { "1": "Log Audit Recenti", "2": "Cerca Log Audit", "3": "Report Audit Generale (Periodo)", "4": "Attività Utenti Recenti", "5": "Audit Dettagliato Recente", "6": "Report Attività Utente (Periodo)", "7": "Torna al menu principale"}
        for k,v in options.items(): print(f"{k.rjust(2)}. {v}")
        scelta = get_validated_input("\nSeleziona", validation_type='choice', choices=list(options.keys()))
        if not scelta: continue
        try:
            if scelta == "1":
                 stampa_intestazione(options[scelta]); limit = get_validated_input("Num log (def 50)", False, 'int')
                 logs = db.get_audit_logs(int(limit) if limit else 50)
                 hdrs = ['id','timestamp','utente_db','utente_app','azione','tabella','record_id','session_id','app_user_id','vecchi_dati','nuovi_dati']
                 display_table(logs, headers=hdrs, max_col_width=25)
            elif scelta == "2":
                 stampa_intestazione(options[scelta]); data_i=None; data_f=None; rec_id=None
                 usr=get_validated_input("Utente App (opz)", False); act=get_validated_input("Azione (I/U/D, opz)", False, ['I','U','D']); tab=get_validated_input("Tabella (opz)", False); r_id=get_validated_input("Record ID (opz)", False, 'int'); d_i=get_validated_input("Data inizio (opz)", False, 'date'); d_f=get_validated_input("Data fine (opz)", False, 'date')
                 if d_i: data_i=datetime.strptime(d_i, "%Y-%m-%d").date()
                 if d_f: data_f=datetime.strptime(d_f, "%Y-%m-%d").date()
                 if r_id: rec_id=int(r_id)
                 logs = db.search_audit_logs(usr, act, tab, data_i, data_f, rec_id)
                 hdrs = ['id','timestamp','utente_db','utente_app','azione','tabella','record_id','session_id','app_user_id','vecchi_dati','nuovi_dati']
                 display_table(logs, headers=hdrs, max_col_width=25)
            elif scelta == "3":
                 stampa_intestazione(options[scelta]); d_i = get_validated_input("Data inizio", True, 'date'); d_f = get_validated_input("Data fine", True, 'date')
                 if d_i and d_f: data_i=datetime.strptime(d_i,"%Y-%m-%d").date(); data_f=datetime.strptime(d_f,"%Y-%m-%d").date(); rep=db.generate_audit_report(data_i, data_f)
                 if rep: print("\n--- REPORT AUDIT ---\n"+rep); fn=f"rep_audit_{data_i}_{data_f}.txt";
                 if ask_yes_no(f"Salvare {fn}?", False): try:open(fn,'w',encoding='utf-8').write(rep);print("Salvato.") except IOError as e:print(f"Errore file:{e}")
                 else: print(" >> Nessun dato trovato.")
            elif scelta == "4":
                 stampa_intestazione(options[scelta]); usr=get_validated_input("Username (opz)", False); limit=get_validated_input("Num record (def 50)", False, 'int')
                 act = db.get_user_activity(usr, int(limit) if limit else 50)
                 display_table(act, ['username','nome_completo','primo_accesso','ultimo_accesso','sessioni_attive','totale_sessioni','durata_media_s'])
            elif scelta == "5":
                 stampa_intestazione(options[scelta]); limit = get_validated_input("Num record (def 50)", False, 'int')
                 aud_det = db.get_detailed_audit(int(limit) if limit else 50)
                 display_table(aud_det, ['timestamp','username','nome','azione','tabella','rec_id','session_id','ip','dettagli_modifica'], max_col_width=35)
            elif scelta == "6":
                 stampa_intestazione(options[scelta]); usr=get_validated_input("Username (opz)", False); days=get_validated_input("Num giorni (def 30)", False, 'int')
                 rep=db.get_user_activity_report(usr, int(days) if days else 30)
                 if rep: print("\n--- REPORT ATTIVITÀ ---\n"+rep); uf=usr if usr else "tutti"; fn=f"rep_att_{uf}_{days or 30}gg.txt";
                 if ask_yes_no(f"Salvare {fn}?", False): try:open(fn,'w',encoding='utf-8').write(rep);print("Salvato.") except IOError as e:print(f"Errore file:{e}")
                 else: print(" >> Nessun dato trovato.")
            elif scelta == "7": break
            else: print(" >> Opzione non valida!")
        except ValueError: print(" >> Errore: Input numerico o data non valido.")
        except Exception as e: print(f" >> Errore imprevisto audit: {e}")
        input("\nPremi INVIO per continuare...")


def menu_utenti(db: CatastoDBManager):
    """Menu gestione utenti, login e logout."""
    global SESSION_INFO
    while True:
        usr = SESSION_INFO.get("username")
        stampa_intestazione(f"GESTIONE UTENTI (Utente: {usr or 'Nessuno'})")
        options = {"1": "Crea utente", "2": "Login", "3": "Logout", "4": "Verifica Permesso", "5": "Info Sessione", "6": "Torna al menu principale"}
        for k,v in options.items(): print(f"{k.rjust(2)}. {v}")
        scelta = get_validated_input("\nSeleziona", validation_type='choice', choices=list(options.keys()))
        if not scelta: continue
        try:
            if scelta == "1":
                 stampa_intestazione(options[scelta]); username=get_validated_input("Username", True); passwd=get_validated_input("Password", True, 'password'); nome=get_validated_input("Nome Completo", True); email=get_validated_input("Email", True, 'email'); ruolo=get_validated_input("Ruolo", True, ['admin','archivista','consultatore'])
                 if all([username, passwd, nome, email, ruolo]): set_session_vars_for_audit(db);
                 if db.create_user(username, passwd, nome, email, ruolo): print(f" => Utente '{username}' creato.")
            elif scelta == "2": # Login
                 stampa_intestazione(options[scelta])
                 if SESSION_INFO["user_id"]: print(f" Già loggato come {SESSION_INFO['username']}. Logout prima."); continue
                 username=get_validated_input("Username", True); passwd=get_validated_input("Password", True, 'password')
                 if username and passwd:
                      ip="127.0.0.1"; app="CatastoPy"; res=db.login_user(username, passwd, ip, app)
                      if res and res.get('success'): SESSION_INFO={"user_id":res.get('user_id'), "username":username, "session_id":res.get('session_id')}; print(f" => Login OK: {username}. Sessione: {SESSION_INFO['session_id']}"); set_session_vars_for_audit(db)
                      elif res: print(f" >> Login fallito: {res.get('message', 'Errore')}")
                      else: print(" >> Errore DB login.")
            elif scelta == "3": # Logout
                 stampa_intestazione(options[scelta])
                 if not SESSION_INFO["session_id"]: print(" Nessun utente loggato."); continue
                 if db.logout_user(str(SESSION_INFO["session_id"])): print(f" => Logout per {SESSION_INFO['username']} OK.")
                 else: print(" >> Errore logout DB.")
                 SESSION_INFO = {"user_id": None, "username": None, "session_id": None}; set_session_vars_for_audit(db)
            elif scelta == "4":
                 stampa_intestazione(options[scelta]); target_id=get_validated_input("ID Utente da verificare", True, 'int'); perm=get_validated_input("Permesso", True)
                 if target_id and perm:
                      if db.check_permission(int(target_id), perm): print(f" => Utente {target_id} HA permesso '{perm}'.")
                      else: print(f" => Utente {target_id} NON HA permesso '{perm}'.")
            elif scelta == "5":
                 stampa_intestazione(options[scelta]); info=db.get_current_session_info()
                 print(" Stato Locale:"); [print(f"  - {k}: {v}") for k,v in SESSION_INFO.items()]
                 print("\n Info DB:");
                 if info: display_table([info])
                 else: print("  Nessuna info DB.")
            elif scelta == "6": break
            else: print(" >> Opzione non valida!")
        except ValueError: print(" >> Errore: Input numerico non valido.")
        except Exception as e: print(f" >> Errore imprevisto utenti: {e}")
        input("\nPremi INVIO per continuare...")


def menu_backup(db: CatastoDBManager):
     """Menu gestione backup."""
     while True:
        stampa_intestazione("SISTEMA DI BACKUP E RESTORE")
        print(" NOTA: Comandi da eseguire manualmente nella shell.")
        options = { "1": "Ottieni comando Backup", "2": "Log Backup Recenti", "3": "Ottieni comando Restore", "4": "Registra Backup Manuale", "5": "Genera Script Backup", "6": "Pulisci Log Vecchi", "7": "Torna al menu principale"}
        for k,v in options.items(): print(f"{k.rjust(2)}. {v}")
        scelta = get_validated_input("\nSeleziona", validation_type='choice', choices=list(options.keys()))
        if not scelta: continue
        try:
            if scelta == "1":
                 stampa_intestazione(options[scelta]); tipo = get_validated_input("Tipo", True, ['completo','schema','dati'])
                 if tipo: cmd = db.get_backup_command_suggestion(tipo);
                 if cmd: print("\n--- Comando Suggerito ---\n" + cmd); print("-" * 55)
                 else: print(" >> Errore generazione.")
            elif scelta == "2":
                 stampa_intestazione(options[scelta]); limit = get_validated_input("Num log (def 20)", False, 'int')
                 logs = db.get_backup_logs(int(limit) if limit else 20)
                 hdrs = ["ID", "Timestamp", "Tipo", "Esito", "Utente", "Nome File", "Dimens.", "Percorso", "Msg"]
                 l_data = [[l.get(h.lower().split(' ')[0],'N/D') for h in hdrs] for l in logs]
                 # Formattazione specifica per Esito e Dimensione
                 for row in l_data:
                     row[3] = "OK" if row[3] else "FALLITO" # Esito
                     try: row[6] = f"{int(row[6])} bytes" if row[6] != 'N/D' else 'N/D' # Dimensione
                     except: pass # Ignora errori conversione dimensione
                 display_table(l_data, hdrs, max_col_width=40)
            elif scelta == "3":
                 stampa_intestazione(options[scelta]); log_id = get_validated_input("ID log backup", True, 'int')
                 if log_id: cmd = db.get_restore_command_suggestion(int(log_id));
                 if cmd: print("\n--- Comando Suggerito ---\n" + cmd); print("-" * 55 + "\n ATTENZIONE: Sovrascrive DB!");
                 else: print(f" >> ID log {log_id} non valido o errore.")
            elif scelta == "4":
                 stampa_intestazione(options[scelta]); nf=get_validated_input("Nome file", True); pf=get_validated_input("Percorso file", True); ut=get_validated_input("Utente (def: 'manuale')", False) or 'manuale'; tipo=get_validated_input("Tipo", True, ['completo','schema','dati']); esito=ask_yes_no("Buon fine?", True); msg=get_validated_input("Msg (opz)", False); dim=get_validated_input("Dim bytes (opz)", False, 'int')
                 if all([nf, pf, tipo]): b_id = db.register_backup_log(nf, ut, tipo, esito, pf, int(dim) if dim else None, msg);
                 if b_id is not None: print(f" => Backup manuale registrato ID: {b_id}")
                 else: print(" >> Errore registrazione.")
            elif scelta == "5":
                 stampa_intestazione(options[scelta]); b_dir=get_validated_input("Dir destinazione (server DB!)", True); s_name=get_validated_input("Nome file script (es. backup.sh)", True)
                 if b_dir and s_name: script=db.generate_backup_script(b_dir)
                 if script: try: path=os.path.join(os.getcwd(), s_name); open(path,'w',encoding='utf-8').write(script); print(f"\n=> Script '{s_name}' generato: {path}\n   Ricorda di spostarlo, verificarlo e schedularlo sul server DB."); try: os.chmod(path, 0o755); except OSError: print(" Attenzione: permessi non impostati.") except IOError as e: print(f"Errore file: {e}"); except Exception as e: print(f"Errore script: {e}")
                 else: print(" >> Errore generazione script.")
            elif scelta == "6":
                 stampa_intestazione(options[scelta]); giorni = get_validated_input("Conserva log ultimi giorni? (def 30)", False, 'int')
                 g = int(giorni) if giorni else 30;
                 if g < 0: print("Numero giorni non valido."); continue
                 if ask_yes_no(f"Eliminare log > {g} giorni?", False):
                      if db.cleanup_old_backup_logs(g): print(" => Pulizia OK.")
                      else: print(" >> Errore pulizia.")
                 else: print(" Annullato.")
            elif scelta == "7": break
            else: print(" >> Opzione non valida!")
        except ValueError: print(" >> Errore: Input numerico non valido.")
        except Exception as e: print(f" >> Errore imprevisto backup: {e}")
        input("\nPremi INVIO per continuare...")


def menu_storico_avanzato(db: CatastoDBManager):
    """Menu funzionalità storiche avanzate."""
    while True:
        stampa_intestazione("FUNZIONALITÀ STORICHE AVANZATE")
        options = { "1": "Visualizza Periodi Storici", "2": "Ottieni Nome Storico", "3": "Registra Nome Storico", "4": "Ricerca Documenti Storici", "5": "Albero Genealogico Proprietà", "6": "Statistiche Catastali Periodo", "7": "Collega Documento a Partita", "8": "Torna al menu principale"}
        for k, v in options.items(): print(f"{k.rjust(2)}. {v}")
        scelta = get_validated_input("\nSeleziona", validation_type='choice', choices=list(options.keys()))
        if not scelta: continue

        audited_ops = ["3", "7"]
        if scelta in audited_ops:
             if not SESSION_INFO["user_id"]: print("\n !! ATTENZIONE: Operazione non auditata (no login). !!")
             set_session_vars_for_audit(db)
        try:
            if scelta == "1": stampa_intestazione(options[scelta]); display_table(db.get_historical_periods(), ['id', 'nome', 'anno_inizio', 'anno_fine', 'descrizione'])
            elif scelta == "2":
                 stampa_intestazione(options[scelta]); tipo = get_validated_input("Tipo entità", True, ['comune','localita']); eid = get_validated_input(f"ID {tipo}", True, 'int'); anno = get_validated_input("Anno (opz)", False, 'int')
                 if tipo and eid: n_info = db.get_historical_name(tipo, int(eid), int(anno) if anno else None);
                 if n_info: print(f"\n=> Nome: {n_info['nome']} (Periodo: {n_info['periodo_nome']} [{n_info['anno_inizio']}-{n_info.get('anno_fine','oggi')}])");
                 else: print(" >> Nome storico non trovato.")
            elif scelta == "3": # Registra Nome Storico
                 stampa_intestazione(options[scelta]); tipo=get_validated_input("Tipo entità", True, ['comune','localita']); eid=get_validated_input(f"ID {tipo}", True, 'int'); nome_h=get_validated_input("Nome storico", True)
                 periodi=db.get_historical_periods();
                 if not periodi: print(" >> Definire periodi storici."); continue
                 print("\nPeriodi:"); display_table(periodi, ['id','nome']); p_choices=[str(p['id']) for p in periodi]
                 p_id=get_validated_input("ID Periodo", True, 'choice', p_choices); a_ini=get_validated_input("Anno inizio", True, 'int'); a_fine=get_validated_input("Anno fine (opz)", False, 'int'); note=get_validated_input("Note (opz)", False)
                 if all([tipo, eid, nome_h, p_id, a_ini]):
                      if db.register_historical_name(tipo, int(eid), nome_h, int(p_id), int(a_ini), int(a_fine) if a_fine else None, note): print(" => Nome storico registrato.")
                      else: print(" >> Errore registrazione.")
            elif scelta == "4": # Ricerca Documenti
                 stampa_intestazione(options[scelta]); tit=get_validated_input("Titolo (parz, opz)", False); tipo_d=get_validated_input("Tipo doc (opz)", False); p_id=get_validated_input("ID Periodo (opz)", False, 'int'); a_i=get_validated_input("Anno inizio (opz)", False, 'int'); a_f=get_validated_input("Anno fine (opz)", False, 'int'); part_id=get_validated_input("ID Partita (opz)", False, 'int')
                 docs = db.search_historical_documents(tit, tipo_d, int(p_id) if p_id else None, int(a_i) if a_i else None, int(a_f) if a_f else None, int(part_id) if part_id else None)
                 display_table(docs, ['doc_id', 'titolo', 'tipo_doc', 'anno', 'periodo', 'desc', 'partite_correlate'])
            elif scelta == "5": # Albero Genealogico
                 stampa_intestazione(options[scelta]); p_id = get_validated_input("ID Partita partenza", True, 'int')
                 if p_id: alb = db.get_property_genealogy(int(p_id)); print("\n--- Albero ---"); display_table(alb, ['Livello','Relazione','ID Partita','Comune','N Partita','Tipo','Possessori','Data Var'])
            elif scelta == "6": # Statistiche Periodo
                 stampa_intestazione(options[scelta]); com=get_validated_input("Comune (opz)", False); a_i=get_validated_input("Anno inizio (def 1900)", False, 'int'); a_f=get_validated_input("Anno fine (def oggi)", False, 'int')
                 stats = db.get_cadastral_stats_by_period(com, int(a_i) if a_i else 1900, int(a_f) if a_f else None)
                 display_table(stats, ['anno', 'comune', 'nuove_p', 'chiuse_p', 'tot_attive', 'variazioni', 'imm_reg'])
            elif scelta == "7": # Collega Documento
                 stampa_intestazione(options[scelta]); doc_id=get_validated_input("ID Documento", True, 'int'); part_id=get_validated_input("ID Partita", True, 'int'); rel=get_validated_input("Rilevanza (def correlata)", False, ['primaria','secondaria','correlata']) or 'correlata'; note=get_validated_input("Note (opz)", False)
                 if doc_id and part_id:
                      if db.link_document_to_partita(int(doc_id), int(part_id), rel, note): print(" => Collegamento OK.")
                      else: print(" >> Errore collegamento.")
            elif scelta == "8": break
            else: print(" >> Opzione non valida!")
        except ValueError: print(" >> Errore: Input numerico o data non valido.")
        except Exception as e: print(f" >> Errore imprevisto storico: {e}")
        input("\nPremi INVIO per continuare...")


def menu_principale(db: CatastoDBManager):
    """Menu principale dell'applicazione."""
    menu_options = { "1": ("Consultazione dati", menu_consultazione), "2": ("Inserimento/Gestione", menu_inserimento), "3": ("Generazione report", menu_report), "4": ("Manutenzione DB", menu_manutenzione), "5": ("Audit e Attività", menu_audit), "6": ("Gestione Utenti", menu_utenti), "7": ("Backup/Restore", menu_backup), "8": ("Funzionalità Storiche", menu_storico_avanzato), "9": ("Esci", None) }
    while True:
        usr = SESSION_INFO.get("username")
        stampa_intestazione(f"MENU PRINCIPALE CATASTO (Utente: {usr or 'Nessuno'})")
        for key, (desc, _) in menu_options.items(): print(f"{key.rjust(2)}. {desc}")
        scelta = input(f"\nSeleziona (1-{len(menu_options)}): ")
        if scelta in menu_options:
            desc, func = menu_options[scelta]
            if func:
                try: func(db)
                except Exception as menu_err: logger.exception(f"Errore menu {desc}"); print(f"\n!! ERRORE MENU: {menu_err} !!")
            else: break # Esci
        else: print(" >> Opzione non valida!")


# === BLOCCO DI ESECUZIONE PRINCIPALE ===

def main():
    """Carica config, inizializza DB e avvia menu principale."""
    print("Avvio applicazione Catasto Storico...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(script_dir, '.env')
    if not os.path.exists(dotenv_path): print(f"ERRORE: File .env non trovato in {script_dir}"); sys.exit(1)
    load_dotenv(dotenv_path=dotenv_path)
    db_config = {"dbname": os.getenv("DB_NAME"),"user": os.getenv("DB_USER"), "password": os.getenv("DB_PASSWORD"),"host": os.getenv("DB_HOST"), "port": os.getenv("DB_PORT"),"schema": os.getenv("DB_SCHEMA", "catasto")}
    required = ["dbname", "user", "password", "host", "port"]
    if any(not db_config.get(p) for p in required): print(f"ERRORE: Parametri mancanti in .env: {[p for p in required if not db_config.get(p)]}"); sys.exit(1)
    try: db_config["port"] = int(db_config["port"]) # type: ignore
    except: print(f"ERRORE: Porta DB non valida: {db_config['port']}"); sys.exit(1)

    db = CatastoDBManager(**db_config) # type: ignore
    if not db.connect(): print("\nERRORE CRITICO: Connessione DB fallita."); sys.exit(1)

    # Pulisci variabili sessione DB all'avvio
    db.set_session_variable('app.user_id', None); db.set_session_variable('app.session_id', None)

    try: menu_principale(db)
    except KeyboardInterrupt: print("\nOperazione interrotta.")
    except Exception: logger.exception("Errore globale non gestito."); print("\n!! ERRORE GLOBALE !!")
    finally:
        if SESSION_INFO["session_id"]: print(f"\nLogout utente {SESSION_INFO['username']}..."); db.logout_user(str(SESSION_INFO["session_id"]))
        db.disconnect(); print("\nApplicazione terminata.")

if __name__ == "__main__":
    main()