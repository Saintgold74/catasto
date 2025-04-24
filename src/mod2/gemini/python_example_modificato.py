#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Esempio di utilizzo del gestore database catastale
=================================================
Questo script mostra esempi pratici di come utilizzare
la classe CatastoDBManager per interagire con il database.

Autore: Marco Santoro
Data: 17/04/2025
"""

from catasto_db_manager import CatastoDBManager
from datetime import date, datetime
import json
import os
import sys
import hashlib

def stampa_intestazione(titolo):
    """Stampa un'intestazione formattata"""
    print("\n" + "=" * 80)
    print(f" {titolo} ".center(80, "="))
    print("=" * 80)

def inserisci_possessore(db, comune_preselezionato=None):
    """
    Funzione per l'inserimento di un nuovo possessore
    
    Args:
        db: Istanza del database manager
        comune_preselezionato: Nome del comune (opzionale)
        
    Returns:
        Optional[int]: ID del possessore inserito, None in caso di errore
    """
    stampa_intestazione("AGGIUNGI NUOVO POSSESSORE")
    
    # Se il comune non è preselezionato, chiedilo all'utente
    if comune_preselezionato:
        comune = comune_preselezionato
        print(f"Comune: {comune}")
    else:
        comune = input("Comune: ")
    
    cognome_nome = input("Cognome e nome: ")
    paternita = input("Paternita (es. 'fu Roberto'): ")
    
    # Calcola automaticamente il nome completo
    nome_completo = f"{cognome_nome} {paternita}"
    conferma = input(f"Nome completo: [{nome_completo}] (premi INVIO per confermare o inserisci un valore diverso): ")
    if conferma:
        nome_completo = conferma
    
    if comune and cognome_nome:
        # Esegui l'inserimento tramite procedura
        possessore_id = db.insert_possessore(comune, cognome_nome, paternita, nome_completo, True)
        if possessore_id:
            print(f"Possessore {nome_completo} inserito con successo (ID: {possessore_id})")
            return possessore_id
        else:
            print("Errore durante l'inserimento")
    else:
        print("Dati incompleti, operazione annullata")
    
    return None

def inserisci_localita(db):
    """
    Funzione per l'inserimento di una nuova località
    
    Args:
        db: Istanza del database manager
        
    Returns:
        Optional[int]: ID della località inserita, None in caso di errore
    """
    stampa_intestazione("AGGIUNGI NUOVA LOCALITA")
    
    comune = input("Comune: ")
    nome = input("Nome localita: ")
    
    if not comune or not nome:
        print("Dati incompleti, operazione annullata")
        return None
    
    # Chiedi il tipo di località
    print("\nSeleziona il tipo di localita:")
    print("1. Regione")
    print("2. Via")
    print("3. Borgata")
    tipo_scelta = input("Scegli un'opzione (1-3): ")
    
    tipo_mapping = {
        "1": "regione",
        "2": "via",
        "3": "borgata"
    }
    
    if tipo_scelta not in tipo_mapping:
        print("Scelta non valida, operazione annullata")
        return None
    
    tipo = tipo_mapping[tipo_scelta]
    
    # Chiedi il civico solo per le vie
    civico = None
    if tipo == "via":
        civico_input = input("Numero civico (opzionale): ")
        if civico_input and civico_input.isdigit():
            civico = int(civico_input)
    
    # Esegui l'inserimento
    try:
        query = """
        INSERT INTO localita (comune_nome, nome, tipo, civico) 
        VALUES (%s, %s, %s, %s) 
        RETURNING id
        """
        if db.execute_query(query, (comune, nome, tipo, civico)):
            result = db.fetchone()
            if result:
                localita_id = result['id']
                db.commit()
                print(f"Localita {nome} inserita con successo (ID: {localita_id})")
                return localita_id
    except Exception as e:
        print(f"Errore durante l'inserimento della localita: {e}")
        db.rollback()
    
    print("Errore durante l'inserimento o localita gia esistente")
    return None

def menu_principale(db):
    """Menu principale per testare varie funzionalità"""
    while True:
        stampa_intestazione("MENU PRINCIPALE")
        print("1. Consultazione dati")
        print("2. Inserimento e gestione dati")
        print("3. Generazione report")
        print("4. Manutenzione database")
        print("5. Sistema di audit")
        print("6. Gestione Utenti")
        print("7. Sistema di Backup")
        print("8. Funzionalità Storiche Avanzate") # <-- NUOVA OPZIONE
        print("9. Esci")                          # <-- AGGIORNATO

        scelta = input("\nSeleziona un'opzione (1-9): ") # <-- AGGIORNATO RANGE

        if scelta == "1":
            menu_consultazione(db)
        elif scelta == "2":
            menu_inserimento(db)
        elif scelta == "3":
            menu_report(db)
        elif scelta == "4":
            menu_manutenzione(db)
        elif scelta == "5":
            menu_audit(db)
        elif scelta == "6":
            menu_utenti(db)
        elif scelta == "7": # <-- NUOVA OPZIONE
            menu_backup(db) # <-- Chiama il nuovo menu
        elif scelta == "8": # <-- NUOVA OPZIONE
            menu_storico_avanzato(db) # <-- Chiama il nuovo menu
        elif scelta == "9": # <-- AGGIORNATO
            break
        else:
            print("Opzione non valida!")
def aggiungi_comune(db):
    """Funzione per l'inserimento di un nuovo comune"""
    stampa_intestazione("AGGIUNGI NUOVO COMUNE")
    nome = input("Nome comune: ")
    provincia = input("Provincia: ")
    regione = input("Regione: ")
    
    if nome and provincia and regione:
        # Recupera periodi storici disponibili dal database
        if db.execute_query("SELECT id, nome, anno_inizio, anno_fine FROM periodo_storico ORDER BY anno_inizio"):
            periodi = db.fetchall()
            
            if periodi:
                print("\nSeleziona il periodo storico:")
                for i, periodo in enumerate(periodi, 1):
                    anno_fine = periodo['anno_fine'] if periodo['anno_fine'] else 'presente'
                    print(f"{i}. {periodo['nome']} ({periodo['anno_inizio']}-{anno_fine})")
                
                scelta = input("\nNumero periodo (default: Repubblica Italiana): ")
                
                # Imposta il periodo predefinito (Repubblica Italiana)
                periodo_id = next((p['id'] for p in periodi if p['nome'] == 'Repubblica Italiana'), periodi[-1]['id'])
                
                # Se l'utente ha scelto un periodo
                if scelta.isdigit() and 1 <= int(scelta) <= len(periodi):
                    periodo_id = periodi[int(scelta)-1]['id']
                
                # Esegui l'inserimento con il periodo
                if db.execute_query(
                    "INSERT INTO comune (nome, provincia, regione, periodo_id) VALUES (%s, %s, %s, %s) ON CONFLICT (nome) DO NOTHING",
                    (nome, provincia, regione, periodo_id)
                ):
                    db.commit()
                    print(f"Comune {nome} inserito con successo o già esistente")
                else:
                    print("Errore durante l'inserimento")
            else:
                print("Impossibile recuperare i periodi storici, verrà usato il periodo predefinito")
                # Inserimento senza periodo (usa default)
                if db.execute_query(
                    "INSERT INTO comune (nome, provincia, regione) VALUES (%s, %s, %s) ON CONFLICT (nome) DO NOTHING",
                    (nome, provincia, regione)
                ):
                    db.commit()
                    print(f"Comune {nome} inserito con successo o già esistente")
                else:
                    print("Errore durante l'inserimento")
        else:
            print("Errore nel recupero dei periodi storici, verrà usato il periodo predefinito")
            # Inserimento senza periodo (usa default)
            if db.execute_query(
                "INSERT INTO comune (nome, provincia, regione) VALUES (%s, %s, %s) ON CONFLICT (nome) DO NOTHING",
                (nome, provincia, regione)
            ):
                db.commit()
                print(f"Comune {nome} inserito con successo o già esistente")
            else:
                print("Errore durante l'inserimento")
    else:
        print("Dati incompleti, operazione annullata")
def menu_consultazione(db):
    """Menu per operazioni di consultazione"""
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
        # --- NUOVE OPZIONI ---
        print("9. Cerca Immobili Specifici")
        print("10. Cerca Variazioni")
        print("11. Cerca Consultazioni")
        print("12. Esporta Partita in JSON")
        print("13. Esporta Possessore in JSON")
        # --- FINE NUOVE OPZIONI ---
        print("14. Torna al menu principale") # <-- AGGIORNATO

        scelta = input("\nSeleziona un'opzione (1-14): ") # <-- AGGIORNATO RANGE

        
        if scelta == "1":
            # Elenco comuni
            search_term = input("Termine di ricerca (lascia vuoto per tutti): ")
            comuni = db.get_comuni(search_term)
            stampa_intestazione(f"COMUNI REGISTRATI ({len(comuni)})")
            for c in comuni:
                print(f"{c['nome']} ({c['provincia']}, {c['regione']})")
        
        elif scelta == "2":
            # Elenco partite per comune
            comune = input("Inserisci il nome del comune (anche parziale): ")
            partite = db.get_partite_by_comune(comune)
            stampa_intestazione(f"PARTITE DEL COMUNE {comune.upper()} ({len(partite)})")
            for p in partite:
                stato = "ATTIVA" if p['stato'] == 'attiva' else "INATTIVA"
                print(f"ID: {p['id']} - Partita {p['numero_partita']} - {p['tipo']} - {stato}")
                if p['possessori']:
                    print(f"  Possessori: {p['possessori']}")
                print(f"  Immobili: {p['num_immobili']}")
                print()
        
        elif scelta == "3":
            # Elenco possessori per comune
            comune = input("Inserisci il nome del comune: ")
            possessori = db.get_possessori_by_comune(comune)
            stampa_intestazione(f"POSSESSORI DEL COMUNE {comune.upper()} ({len(possessori)})")
            for p in possessori:
                stato = "ATTIVO" if p['attivo'] else "NON ATTIVO"
                print(f"ID: {p['id']} - {p['nome_completo']} - {stato}")
        
        elif scelta == "4":
            # Ricerca partite
            stampa_intestazione("RICERCA PARTITE")
            print("Inserisci i criteri di ricerca (lascia vuoto per non specificare)")
            comune = input("Comune (anche parziale): ")
            numero = input("Numero partita: ")
            possessore = input("Nome possessore (anche parziale): ")
            natura = input("Natura immobile (anche parziale): ")
            
            # Converti il numero in intero se specificato
            numero_partita = int(numero) if numero.strip() else None
            
            # Esegui la ricerca
            partite = db.search_partite(
                comune_nome=comune if comune.strip() else None,
                numero_partita=numero_partita,
                possessore=possessore if possessore.strip() else None,
                immobile_natura=natura if natura.strip() else None
            )
            
            stampa_intestazione(f"RISULTATI RICERCA ({len(partite)})")
            for p in partite:
                print(f"ID: {p['id']} - {p['comune_nome']} - Partita {p['numero_partita']} - {p['tipo']}")
        
        elif scelta == "5":
            # Dettagli partita
            id_partita = input("Inserisci l'ID della partita: ")
            if id_partita.isdigit():
                partita = db.get_partita_details(int(id_partita))
                if partita:
                    stampa_intestazione(f"DETTAGLI PARTITA {partita['numero_partita']} - {partita['comune_nome']}")
                    print(f"ID: {partita['id']}")
                    print(f"Tipo: {partita['tipo']}")
                    print(f"Stato: {partita['stato']}")
                    print(f"Data impianto: {partita['data_impianto']}")
                    if partita['data_chiusura']:
                        print(f"Data chiusura: {partita['data_chiusura']}")
                    
                    # Possessori
                    print("\nPOSSESSORI:")
                    for pos in partita['possessori']:
                        print(f"- ID: {pos['id']} - {pos['nome_completo']}")
                        if pos['quota']:
                            print(f"  Quota: {pos['quota']}")
                    
                    # Immobili
                    print("\nIMMOBILI:")
                    for imm in partita['immobili']:
                        print(f"- ID: {imm['id']} - {imm['natura']} - {imm['localita_nome']}")
                        if 'tipologia' in imm and imm['tipologia']:
                            print(f"  Tipologia: {imm['tipologia']}")
                        if imm['consistenza']:
                            print(f"  Consistenza: {imm['consistenza']}")
                        if imm['classificazione']:
                            print(f"  Classificazione: {imm['classificazione']}")
                    
                    # Variazioni
                    if partita['variazioni']:
                        print("\nVARIAZIONI:")
                        for var in partita['variazioni']:
                            print(f"- ID: {var['id']} - {var['tipo']} del {var['data_variazione']}")
                            if var['tipo_contratto']:
                                print(f"  Contratto: {var['tipo_contratto']} del {var['data_contratto']}")
                                if var['notaio']:
                                    print(f"  Notaio: {var['notaio']}")
                else:
                    print("Partita non trovata!")
            else:
                print("ID non valido!")
        
        elif scelta == "6":
            # Elenco località per comune
            comune = input("Inserisci il nome del comune (anche parziale): ")
            if comune:
                query = """
                SELECT id, nome, tipo, civico 
                FROM localita 
                WHERE comune_nome ILIKE %s 
                ORDER BY tipo, nome
                """
                if db.execute_query(query, (f"%{comune}%",)):
                    localita = db.fetchall()
                    stampa_intestazione(f"LOCALITA DEL COMUNE {comune.upper()} ({len(localita)})")
                    for loc in localita:
                        civico_str = f", {loc['civico']}" if loc['civico'] else ""
                        print(f"ID: {loc['id']} - {loc['nome']}{civico_str} ({loc['tipo']})")
                else:
                    print("Errore durante la ricerca delle localita")
            else:
                print("Nome comune richiesto")
        
        elif scelta == "7":
            stampa_intestazione("RICERCA AVANZATA POSSESSORI (Similarità)")
            query_text = input("Inserisci termine di ricerca per nome/cognome/paternità: ")
            if query_text:
                results = db.ricerca_avanzata_possessori(query_text)
                if results:
                    print(f"\nTrovati {len(results)} risultati (ordinati per similarità):")
                    for r in results:
                         # Arrotonda la similarità per una migliore visualizzazione
                         similarity_perc = round(r.get('similarity', 0) * 100, 1)
                         print(f"  ID: {r['id']} - {r['nome_completo']} ({r['comune_nome']})")
                         print(f"    Similarità: {similarity_perc}% - Partite: {r['num_partite']}")
                else:
                    print("Nessun possessore trovato per la ricerca avanzata.")
            else:
                print("Termine di ricerca non inserito.")

        elif scelta == "8":
             stampa_intestazione("RICERCA AVANZATA IMMOBILI")
             print("Inserisci i criteri di ricerca (lascia vuoto per non filtrare)")
             comune = input("Comune: ")
             natura = input("Natura Immobile: ")
             localita = input("Località: ")
             classificazione = input("Classificazione: ")
             possessore = input("Possessore: ")

             results = db.ricerca_avanzata_immobili(
                 comune=comune if comune else None,
                 natura=natura if natura else None,
                 localita=localita if localita else None,
                 classificazione=classificazione if classificazione else None,
                 possessore=possessore if possessore else None
             )

             if results:
                 print(f"\nTrovati {len(results)} immobili:")
                 for r in results:
                     print(f"\n  Immobile ID: {r['immobile_id']} - Natura: {r['natura']}")
                     print(f"    Località: {r['localita_nome']} ({r['comune']})")
                     if r['classificazione']:
                         print(f"    Classificazione: {r['classificazione']}")
                     print(f"    Partita: {r['partita_numero']}")
                     print(f"    Possessori: {r['possessori']}")
             else:
                 print("Nessun immobile trovato per i criteri specificati.")

        elif scelta == "9":
            stampa_intestazione("CERCA IMMOBILI SPECIFICI")
            try:
                part_id_str = input("Filtra per ID Partita (vuoto per non filtrare): ")
                comune = input("Filtra per Comune (vuoto per non filtrare): ")
                loc_id_str = input("Filtra per ID Località (vuoto per non filtrare): ")
                natura = input("Filtra per Natura (parziale, vuoto per non filtrare): ")
                classif = input("Filtra per Classificazione (esatta, vuoto per non filtrare): ")

                part_id = int(part_id_str) if part_id_str.isdigit() else None
                loc_id = int(loc_id_str) if loc_id_str.isdigit() else None

                immobili = db.search_immobili(
                    partita_id=part_id,
                    comune_nome=comune if comune else None,
                    localita_id=loc_id,
                    natura=natura if natura else None,
                    classificazione=classif if classif else None
                )
                if immobili:
                     print(f"\nTrovati {len(immobili)} immobili:")
                     for imm in immobili:
                          print(f"- ID: {imm['id']}, Natura: {imm['natura']}, Località: {imm['localita_nome']} ({imm['comune_nome']}), Partita: {imm['numero_partita']}")
                          # Aggiungere altri dettagli se necessario
                else:
                     print("Nessun immobile trovato con questi criteri.")
            except ValueError:
                print("ID non valido.")
            except Exception as e:
                print(f"Errore: {e}")

        elif scelta == "10":
            stampa_intestazione("CERCA VARIAZIONI")
            try:
                tipo = input("Filtra per Tipo (es. Vendita, Successione, vuoto per tutti): ")
                data_i_str = input("Data inizio (YYYY-MM-DD, vuoto per non filtrare): ")
                data_f_str = input("Data fine (YYYY-MM-DD, vuoto per non filtrare): ")
                part_o_id_str = input("ID Partita Origine (vuoto per non filtrare): ")
                part_d_id_str = input("ID Partita Destinazione (vuoto per non filtrare): ")
                comune = input("Filtra per Comune Origine (vuoto per non filtrare): ")

                data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date() if data_i_str else None
                data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date() if data_f_str else None
                part_o_id = int(part_o_id_str) if part_o_id_str.isdigit() else None
                part_d_id = int(part_d_id_str) if part_d_id_str.isdigit() else None

                variazioni = db.search_variazioni(
                    tipo=tipo if tipo else None,
                    data_inizio=data_i,
                    data_fine=data_f,
                    partita_origine_id=part_o_id,
                    partita_destinazione_id=part_d_id,
                    comune=comune if comune else None
                )
                if variazioni:
                     print(f"\nTrovate {len(variazioni)} variazioni:")
                     for v in variazioni:
                          dest_str = f"-> {v['partita_destinazione_numero']}" if v['partita_destinazione_numero'] else ""
                          print(f"- ID: {v['id']}, Tipo: {v['tipo']}, Data: {v['data_variazione']}")
                          print(f"  Partita: {v['partita_origine_numero']} ({v['comune_nome']}) {dest_str}")
                          print(f"  Rif: {v['numero_riferimento']} - {v['nominativo_riferimento']}")
                else:
                     print("Nessuna variazione trovata.")

            except ValueError:
                 print("Input ID o Data non validi.")
            except Exception as e:
                print(f"Errore: {e}")

        elif scelta == "11":
            stampa_intestazione("CERCA CONSULTAZIONI")
            try:
                data_i_str = input("Data inizio (YYYY-MM-DD, vuoto per non filtrare): ")
                data_f_str = input("Data fine (YYYY-MM-DD, vuoto per non filtrare): ")
                richiedente = input("Filtra per Richiedente (parziale, vuoto per non filtrare): ")
                funzionario = input("Filtra per Funzionario (parziale, vuoto per non filtrare): ")

                data_i = datetime.strptime(data_i_str, "%Y-%m-%d").date() if data_i_str else None
                data_f = datetime.strptime(data_f_str, "%Y-%m-%d").date() if data_f_str else None

                consultazioni = db.search_consultazioni(
                    data_inizio=data_i,
                    data_fine=data_f,
                    richiedente=richiedente if richiedente else None,
                    funzionario=funzionario if funzionario else None
                )
                if consultazioni:
                     print(f"\nTrovate {len(consultazioni)} consultazioni:")
                     for c in consultazioni:
                         print(f"- ID: {c['id']}, Data: {c['data']}, Richiedente: {c['richiedente']}")
                         print(f"  Materiale: {c['materiale_consultato']}, Funzionario: {c['funzionario_autorizzante']}")
                else:
                     print("Nessuna consultazione trovata.")
            except ValueError:
                print("Formato Data non valido.")
            except Exception as e:
                print(f"Errore: {e}")

        elif scelta == "12":
            stampa_intestazione("ESPORTA PARTITA IN JSON")
            try:
                partita_id = int(input("ID della Partita da esportare: "))
                json_data = db.export_partita_json(partita_id)
                if json_data:
                    print("\n--- DATI JSON PARTITA ---")
                    print(json_data)
                    print("-" * 25)
                    filename = f"partita_{partita_id}.json"
                    if input(f"Salvare in '{filename}'? (s/n): ").lower() == 's':
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(json_data)
                        print(f"Dati salvati in {filename}")
                else:
                    print("Partita non trovata o errore durante l'esportazione.")
            except ValueError:
                print("ID non valido.")

        elif scelta == "13":
            stampa_intestazione("ESPORTA POSSESSORE IN JSON")
            try:
                poss_id = int(input("ID del Possessore da esportare: "))
                json_data = db.export_possessore_json(poss_id)
                if json_data:
                    print("\n--- DATI JSON POSSESSORE ---")
                    print(json_data)
                    print("-" * 26)
                    filename = f"possessore_{poss_id}.json"
                    if input(f"Salvare in '{filename}'? (s/n): ").lower() == 's':
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(json_data)
                        print(f"Dati salvati in {filename}")
                else:
                    print("Possessore non trovato o errore durante l'esportazione.")
            except ValueError:
                print("ID non valido.")

        elif scelta == "14": # <-- AGGIORNATO
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")

def menu_inserimento(db):
    """Menu per operazioni di inserimento e gestione"""
    while True:
        stampa_intestazione("INSERIMENTO E GESTIONE DATI")
        print("1. Aggiungi nuovo comune")
        print("2. Aggiungi nuovo possessore")
        print("3. Aggiungi nuova localita")
        print("4. Registra nuova proprieta")
        print("5. Registra passaggio di proprieta")
        print("6. Registra consultazione")
        # --- NUOVE OPZIONI ---
        print("7. Inserisci Contratto per Variazione")
        print("8. Duplica Partita")
        print("9. Trasferisci Immobile a Nuova Partita")
        # --- FINE NUOVE OPZIONI ---
        print("10. Torna al menu principale") # <-- AGGIORNATO

        scelta = input("\nSeleziona un'opzione (1-10): ") # <-- AGGIORNATO RANGE

        if scelta == "1":
            # Aggiungi comune
            aggiungi_comune(db)
        
        elif scelta == "2":
            # Aggiungi possessore
            inserisci_possessore(db)
        
        elif scelta == "3":
            # Aggiungi località
            inserisci_localita(db)
        
        elif scelta == "4":
            # Registra nuova proprietà
            stampa_intestazione("REGISTRA NUOVA PROPRIETA")
            
            # Raccolta dati principali
            comune = input("Comune: ")
            numero_partita = input("Numero partita: ")
            
            try:
                # Verifica se i dati di base sono validi
                if not comune or not numero_partita.isdigit():
                    raise ValueError("Comune o numero partita non validi")
                
                numero_partita = int(numero_partita)
                data_impianto = input("Data impianto (YYYY-MM-DD): ")
                data_impianto = datetime.strptime(data_impianto, "%Y-%m-%d").date()
                
                # Raccolta dati possessori
                possessori = []
                while True:
                    stampa_intestazione("INSERIMENTO POSSESSORE")
                    nome_completo = input("Nome completo possessore (vuoto per terminare): ")
                    if not nome_completo:
                        break
                    
                    # Verifica se il possessore esiste già
                    possessore_id = db.check_possessore_exists(nome_completo, comune)
                    if possessore_id:
                        print(f"Possessore esistente con ID: {possessore_id}")
                        cognome_nome = input("Cognome e nome (se diverso): ")
                        paternita = input("Paternita (se diversa): ")
                        quota = input("Quota (vuoto se proprieta esclusiva): ")
                        
                        possessore = {
                            "nome_completo": nome_completo,
                            "cognome_nome": cognome_nome if cognome_nome else nome_completo.split()[0],
                            "paternita": paternita,
                        }
                    else:
                        # Nuovo possessore
                        print(f"Possessore non trovato. Inserisci i dettagli:")
                        cognome_nome = input("Cognome e nome: ")
                        paternita = input("Paternita: ")
                        quota = input("Quota (vuoto se proprieta esclusiva): ")
                        
                        possessore = {
                            "nome_completo": nome_completo,
                            "cognome_nome": cognome_nome,
                            "paternita": paternita
                        }
                    
                    if quota:
                        possessore["quota"] = quota
                    
                    possessori.append(possessore)
                    print(f"Possessore {nome_completo} aggiunto")
                
                if not possessori:
                    raise ValueError("Nessun possessore inserito")
                
                # Raccolta dati immobili
                immobili = []
                while True:
                    stampa_intestazione("INSERIMENTO IMMOBILE")
                    natura = input("Natura immobile (vuoto per terminare): ")
                    if not natura:
                        break
                    
                    # Aggiunta della tipologia immobile
                    tipologia = input("Tipologia immobile (opzionale): ")
                    
                    # Selezione o inserimento località
                    print("\nGestione localita:")
                    print("1. Usa localita esistente")
                    print("2. Inserisci nuova localita")
                    scelta_localita = input("Scegli un'opzione (1-2): ")
                    
                    localita_id = None
                    localita_nome = None
                    tipo_localita = None
                    
                    if scelta_localita == "1":
                        # Cerca e usa una località esistente
                        localita_nome = input("Nome localita esistente: ")
                        query = "SELECT id, nome, tipo FROM localita WHERE nome ILIKE %s AND comune_nome ILIKE %s"
                        if db.execute_query(query, (f"%{localita_nome}%", f"%{comune}%")):
                            localita_risultati = db.fetchall()
                            
                            if not localita_risultati:
                                print("Nessuna localita trovata con questo nome")
                                continue
                            
                            print("\nLocalita trovate:")
                            for i, loc in enumerate(localita_risultati, 1):
                                print(f"{i}. {loc['nome']} ({loc['tipo']}), ID: {loc['id']}")
                            
                            scelta_idx = input("Seleziona una localita (numero): ")
                            if scelta_idx.isdigit() and 0 < int(scelta_idx) <= len(localita_risultati):
                                localita_selezionata = localita_risultati[int(scelta_idx) - 1]
                                localita_id = localita_selezionata['id']
                                localita_nome = localita_selezionata['nome']
                                tipo_localita = localita_selezionata['tipo']
                            else:
                                print("Scelta non valida")
                                continue
                        else:
                            print("Errore durante la ricerca delle localita")
                            continue
                    
                    elif scelta_localita == "2":
                        # Inserisci una nuova località
                        localita_id = inserisci_localita(db)
                        if not localita_id:
                            print("Inserimento localita fallito")
                            continue
                    else:
                        print("Scelta non valida")
                        continue
                    
                    # Altri dati immobile
                    classificazione = input("Classificazione: ")
                    
                    numero_piani = input("Numero piani (opzionale): ")
                    numero_vani = input("Numero vani (opzionale): ")
                    consistenza = input("Consistenza (opzionale): ")
                    
                    immobile = {
                        "natura": natura,
                        "tipologia": tipologia,  # Nuovo campo tipologia
                        "localita_id": localita_id,  # Usiamo l'ID invece del nome
                        "classificazione": classificazione
                    }
                    
                    if numero_piani:
                        immobile["numero_piani"] = int(numero_piani)
                    if numero_vani:
                        immobile["numero_vani"] = int(numero_vani)
                    if consistenza:
                        immobile["consistenza"] = consistenza
                    
                    immobili.append(immobile)
                    print(f"Immobile {natura} aggiunto")
                
                if not immobili:
                    raise ValueError("Nessun immobile inserito")
                
                # Registrazione della proprietà usando la versione modificata
                if db.registra_nuova_proprieta_v2(
                    comune, numero_partita, data_impianto, possessori, immobili
                ):
                    print(f"Proprieta registrata con successo: {comune}, partita {numero_partita}")
                else:
                    print("Errore durante la registrazione della proprieta")
                
            except ValueError as e:
                print(f"Errore: {e}")
            except Exception as e:
                print(f"Errore imprevisto: {e}")
        
        elif scelta == "5":
            # Registra passaggio di proprietà
            stampa_intestazione("REGISTRA PASSAGGIO DI PROPRIETA")
            
            try:
                # Partita di origine
                partita_origine_id = input("ID partita di origine: ")
                if not partita_origine_id.isdigit():
                    raise ValueError("ID partita non valido")
                
                partita_origine_id = int(partita_origine_id)
                
                # Dati nuova partita
                comune = input("Comune nuova partita: ")
                numero_partita = input("Numero nuova partita: ")
                if not numero_partita.isdigit():
                    raise ValueError("Numero partita non valido")
                
                numero_partita = int(numero_partita)
                
                # Dati variazione
                tipo_variazione = input("Tipo variazione (Vendita/Successione/Frazionamento): ")
                data_variazione = input("Data variazione (YYYY-MM-DD): ")
                data_variazione = datetime.strptime(data_variazione, "%Y-%m-%d").date()
                
                # Dati contratto
                tipo_contratto = input("Tipo contratto: ")
                data_contratto = input("Data contratto (YYYY-MM-DD): ")
                data_contratto = datetime.strptime(data_contratto, "%Y-%m-%d").date()
                notaio = input("Notaio (opzionale): ")
                repertorio = input("Repertorio (opzionale): ")
                
                # Possessori e immobili
                includi_possessori = input("Specificare nuovi possessori? (s/n): ").lower() == 's'
                nuovi_possessori = None
                
                if includi_possessori:
                    nuovi_possessori = []
                    while True:
                        nome_completo = input("Nome completo possessore (vuoto per terminare): ")
                        if not nome_completo:
                            break
                        
                        # Verifica se il possessore esiste
                        possessore_id = db.check_possessore_exists(nome_completo, comune)
                        
                        if possessore_id:
                            print(f"Possessore trovato con ID: {possessore_id}")
                            cognome_nome = input("Cognome e nome (se diverso): ")
                            paternita = input("Paternita (se diversa): ")
                        else:
                            print(f"Possessore non trovato nel database.")
                            risposta = input("Vuoi inserire un nuovo possessore? (s/n): ")
                            if risposta.lower() == 's':
                                possessore_id = inserisci_possessore(db, comune)
                                if not possessore_id:
                                    continue
                                
                                # Recupera i dati del possessore appena inserito
                                db.execute_query(
                                    "SELECT cognome_nome, paternita, nome_completo FROM possessore WHERE id = %s",
                                    (possessore_id,)
                                )
                                possessore_data = db.fetchone()
                                if possessore_data:
                                    cognome_nome = possessore_data['cognome_nome']
                                    paternita = possessore_data['paternita']
                                    nome_completo = possessore_data['nome_completo']
                            else:
                                continue
                        
                        nuovi_possessori.append({
                            "nome_completo": nome_completo,
                            "cognome_nome": cognome_nome,
                            "paternita": paternita
                        })
                
                includi_immobili = input("Specificare immobili da trasferire? (s/n): ").lower() == 's'
                immobili_da_trasferire = None
                
                if includi_immobili:
                    immobili_da_trasferire = []
                    while True:
                        immobile_id = input("ID immobile da trasferire (vuoto per terminare): ")
                        if not immobile_id:
                            break
                        
                        if immobile_id.isdigit():
                            immobili_da_trasferire.append(int(immobile_id))
                
                note = input("Note (opzionale): ")
                
                # Registrazione del passaggio
                if db.registra_passaggio_proprieta(
                    partita_origine_id, comune, numero_partita, tipo_variazione, data_variazione,
                    tipo_contratto, data_contratto, notaio=notaio, repertorio=repertorio,
                    nuovi_possessori=nuovi_possessori, immobili_da_trasferire=immobili_da_trasferire,
                    note=note
                ):
                    print(f"Passaggio di proprieta registrato con successo")
                else:
                    print("Errore durante la registrazione del passaggio di proprieta")
                
            except ValueError as e:
                print(f"Errore: {e}")
            except Exception as e:
                print(f"Errore imprevisto: {e}")
        
        elif scelta == "6":
            # Registra consultazione
            stampa_intestazione("REGISTRA CONSULTAZIONE")
            
            try:
                data = input("Data consultazione (YYYY-MM-DD, vuoto per oggi): ")
                if data:
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                else:
                    data = date.today()
                
                richiedente = input("Richiedente: ")
                if not richiedente:
                    raise ValueError("Richiedente obbligatorio")
                
                documento = input("Documento identita: ")
                motivazione = input("Motivazione: ")
                materiale = input("Materiale consultato: ")
                funzionario = input("Funzionario autorizzante: ")
                
                if db.registra_consultazione(
                    data, richiedente, documento, motivazione, materiale, funzionario
                ):
                    print("Consultazione registrata con successo")
                else:
                    print("Errore durante la registrazione della consultazione")
                
            except ValueError as e:
                print(f"Errore: {e}")
            except Exception as e:
                print(f"Errore imprevisto: {e}")
        
        elif scelta == "7":
            stampa_intestazione("INSERISCI CONTRATTO PER VARIAZIONE")
            try:
                var_id = int(input("ID Variazione a cui collegare il contratto: "))
                tipo_contratto = input("Tipo contratto (Vendita/Divisione/Successione/Donazione): ")
                data_str = input("Data contratto (YYYY-MM-DD): ")
                data_contratto = datetime.strptime(data_str, "%Y-%m-%d").date()
                notaio = input("Notaio (opzionale): ")
                repertorio = input("Repertorio (opzionale): ")
                note = input("Note (opzionale): ")

                if db.insert_contratto(var_id, tipo_contratto, data_contratto,
                                        notaio if notaio else None,
                                        repertorio if repertorio else None,
                                        note if note else None):
                    print("Contratto inserito con successo.")
                else:
                    print("Errore durante l'inserimento del contratto.")
            except ValueError:
                print("ID Variazione o formato data non valido.")
            except Exception as e:
                print(f"Errore: {e}")

        elif scelta == "8":
            stampa_intestazione("DUPLICA PARTITA")
            try:
                partita_id_orig = int(input("ID Partita da duplicare: "))
                nuovo_num = int(input("Nuovo numero per la partita duplicata: "))
                possessori_str = input("Mantenere i possessori? (s/n, default s): ").lower() or 's'
                immobili_str = input("Mantenere gli immobili? (s/n, default n): ").lower() or 'n'
                mant_poss = possessori_str == 's'
                mant_imm = immobili_str == 's'

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
            try:
                imm_id = int(input("ID Immobile da trasferire: "))
                part_dest_id = int(input("ID Partita di destinazione: "))
                reg_var_str = input("Registrare una variazione per questo trasferimento? (s/n, default n): ").lower() or 'n'
                reg_var = reg_var_str == 's'

                if db.transfer_immobile(imm_id, part_dest_id, reg_var):
                    print("Immobile trasferito con successo.")
                else:
                    print("Errore durante il trasferimento dell'immobile.")
            except ValueError:
                print("ID non valido.")
            except Exception as e:
                print(f"Errore: {e}")

        elif scelta == "10": # <-- AGGIORNATO
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")

def menu_report(db):
    """Menu per la generazione di report"""
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
        # --- NUOVA OPZIONE ---
        print("11. Report Statistico Comune")
        # --- FINE NUOVA OPZIONE ---
        print("12. Torna al menu principale") # <-- AGGIORNATO

        scelta = input("\nSeleziona un'opzione (1-12): ") # <-- AGGIORNATO RANGE

        
        if scelta == "1":
            # Certificato di proprietà
            partita_id = input("Inserisci l'ID della partita: ")
            if partita_id.isdigit():
                certificato = db.genera_certificato_proprieta(int(partita_id))
                
                # Verifica se ci sono dati prima di proporre il salvataggio
                if certificato and not certificato.startswith('Partita con ID'):
                    stampa_intestazione("CERTIFICATO DI PROPRIETA")
                    print(certificato)
                    
                    # Salvataggio su file
                    if input("\nSalvare su file? (s/n): ").lower() == 's':
                        filename = f"certificato_partita_{partita_id}_{date.today()}.txt"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(certificato)
                        print(f"Certificato salvato nel file: {filename}")
                else:
                    print("Nessun dato disponibile per questa partita")
            else:
                print("ID non valido!")
        
        elif scelta == "2":
            # Report genealogico
            partita_id = input("Inserisci l'ID della partita: ")
            if partita_id.isdigit():
                report = db.genera_report_genealogico(int(partita_id))
                
                # Verifica se ci sono dati prima di proporre il salvataggio
                if report and not report.startswith('Partita con ID'):
                    stampa_intestazione("REPORT GENEALOGICO")
                    print(report)
                    
                    # Salvataggio su file
                    if input("\nSalvare su file? (s/n): ").lower() == 's':
                        filename = f"report_genealogico_{partita_id}_{date.today()}.txt"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(report)
                        print(f"Report salvato nel file: {filename}")
                else:
                    print("Nessun dato disponibile per questa partita")
            else:
                print("ID non valido!")
        
        elif scelta == "3":
            # Report possessore
            possessore_id = input("Inserisci l'ID del possessore: ")
            if possessore_id.isdigit():
                report = db.genera_report_possessore(int(possessore_id))
                
                # Verifica se ci sono dati prima di proporre il salvataggio
                if report and not report.startswith('Possessore con ID'):
                    stampa_intestazione("REPORT POSSESSORE")
                    print(report)
                    
                    # Salvataggio su file
                    if input("\nSalvare su file? (s/n): ").lower() == 's':
                        filename = f"report_possessore_{possessore_id}_{date.today()}.txt"
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(report)
                        print(f"Report salvato nel file: {filename}")
                else:
                    print("Nessun dato disponibile per questo possessore")
            else:
                print("ID non valido!")
        
        elif scelta == "4":
            # Report consultazioni
            stampa_intestazione("REPORT CONSULTAZIONI")
            
            # Chiedi i parametri di filtro
            print("Inserisci i parametri per filtrare (lascia vuoto per non applicare filtro)")
            data_inizio_str = input("Data inizio (YYYY-MM-DD): ")
            data_fine_str = input("Data fine (YYYY-MM-DD): ")
            richiedente = input("Richiedente: ")
            
            # Converti le date
            data_inizio = None
            data_fine = None
            
            if data_inizio_str:
                try:
                    data_inizio = datetime.strptime(data_inizio_str, "%Y-%m-%d").date()
                except ValueError:
                    print("Formato data non valido, filtro non applicato")
            
            if data_fine_str:
                try:
                    data_fine = datetime.strptime(data_fine_str, "%Y-%m-%d").date()
                except ValueError:
                    print("Formato data non valido, filtro non applicato")
            
            # Verifica se specificare richiedente
            richiedente = richiedente if richiedente.strip() else None
            
            # Genera il report
            report = db.genera_report_consultazioni(data_inizio, data_fine, richiedente)
            
            if report:
                # Visualizza il report
                stampa_intestazione("REPORT CONSULTAZIONI")
                print(report)
                
                # Salvataggio su file
                if input("\nSalvare su file? (s/n): ").lower() == 's':
                    oggi = date.today().strftime("%Y%m%d")
                    filename = f"report_consultazioni_{oggi}.txt"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(report)
                    print(f"Report salvato nel file: {filename}")
            else:
                print("Nessun dato disponibile o errore durante la generazione del report")
        
         # --- NUOVI BLOCCHI CASE ---
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
            else:
                print("Nessuna statistica disponibile o errore.")

        elif scelta == "6":
            stampa_intestazione("RIEPILOGO IMMOBILI PER TIPOLOGIA (Vista Materializzata)")
            comune_filter = input("Filtra per comune (lascia vuoto per tutti): ")
            stats = db.get_immobili_per_tipologia(comune_nome=comune_filter if comune_filter else None)
            if stats:
                current_comune = None
                for s in stats:
                    if s['comune_nome'] != current_comune:
                        current_comune = s['comune_nome']
                        print(f"\n--- Comune: {current_comune} ---")
                    print(f"  Classificazione: {s['classificazione']}")
                    print(f"    Numero Immobili: {s['numero_immobili']}")
                    print(f"    Totale Piani: {s['totale_piani']}")
                    print(f"    Totale Vani: {s['totale_vani']}")
            else:
                print("Nessun dato disponibile o errore.")

        elif scelta == "7":
            stampa_intestazione("VISUALIZZA PARTITE COMPLETE (Vista Materializzata)")
            comune_filter = input("Filtra per comune (lascia vuoto per tutti): ")
            stato_filter = input("Filtra per stato (attiva/inattiva, lascia vuoto per tutti): ")
            partite = db.get_partite_complete_view(comune_nome=comune_filter if comune_filter else None,
                                                   stato=stato_filter if stato_filter else None)
            if partite:
                print(f"Trovate {len(partite)} partite:")
                for p in partite:
                    print(f"\nID: {p['partita_id']} - Partita {p['numero_partita']} ({p['comune_nome']}) - Stato: {p['stato']}")
                    print(f"  Tipo: {p['tipo']}, Data Impianto: {p['data_impianto']}")
                    print(f"  Possessori: {p['possessori']}")
                    print(f"  Num. Immobili: {p['num_immobili']}, Tipi: {p['tipi_immobili']}")
                    print(f"  Località: {p['localita']}")
            else:
                print("Nessuna partita trovata per i criteri specificati.")

        elif scelta == "8":
            stampa_intestazione("CRONOLOGIA VARIAZIONI (Vista Materializzata)")
            comune_filter = input("Filtra per comune origine (lascia vuoto per tutti): ")
            tipo_filter = input("Filtra per tipo variazione (lascia vuoto per tutti): ")
            variazioni = db.get_cronologia_variazioni(comune_origine=comune_filter if comune_filter else None,
                                                     tipo_variazione=tipo_filter if tipo_filter else None)
            if variazioni:
                print(f"Trovate {len(variazioni)} variazioni:")
                for v in variazioni:
                    print(f"\nID Variazione: {v['variazione_id']} - Tipo: {v['tipo_variazione']} del {v['data_variazione']}")
                    print(f"  Origine: Partita {v['partita_origine_numero']} ({v['comune_origine']})")
                    print(f"    Possessori Origine: {v['possessori_origine']}")
                    if v['partita_dest_numero']:
                       print(f"  Destinazione: Partita {v['partita_dest_numero']} ({v['comune_dest']})")
                       print(f"    Possessori Destinazione: {v['possessori_dest']}")
                    if v['tipo_contratto']:
                       print(f"  Contratto: {v['tipo_contratto']} del {v['data_contratto']} (Notaio: {v['notaio']})")
            else:
                print("Nessuna variazione trovata per i criteri specificati.")

        elif scelta == "9":
            stampa_intestazione("REPORT ANNUALE PARTITE PER COMUNE (Funzione)")
            comune = input("Inserisci il nome del comune: ")
            try:
                anno = int(input("Inserisci l'anno del report: "))
                report = db.get_report_annuale_partite(comune, anno)
                if report:
                    print(f"\nReport per {comune} - Anno {anno}:")
                    for r in report:
                        print(f"  Partita {r['numero_partita']} ({r['tipo']}) - Stato: {r['stato']} - Impianto: {r['data_impianto']}")
                        print(f"    Possessori: {r['possessori']}")
                        print(f"    Num. Immobili: {r['num_immobili']}, Variazioni Anno: {r['variazioni_anno']}")
                else:
                    print("Nessun dato trovato o errore.")
            except ValueError:
                print("Anno non valido.")

        elif scelta == "10":
             stampa_intestazione("REPORT PROPRIETÀ POSSESSORE PER PERIODO (Funzione)")
             try:
                 possessore_id = int(input("Inserisci l'ID del possessore: "))
                 data_inizio_str = input("Data inizio periodo (YYYY-MM-DD): ")
                 data_fine_str = input("Data fine periodo (YYYY-MM-DD): ")
                 data_inizio = datetime.strptime(data_inizio_str, "%Y-%m-%d").date()
                 data_fine = datetime.strptime(data_fine_str, "%Y-%m-%d").date()

                 report = db.get_report_proprieta_possessore(possessore_id, data_inizio, data_fine)
                 if report:
                     print(f"\nProprietà del possessore ID {possessore_id} tra {data_inizio} e {data_fine}:")
                     for r in report:
                         quota_str = f" (Quota: {r['quota']})" if r['quota'] else ""
                         print(f"  Partita {r['numero_partita']} ({r['comune_nome']}) - ID: {r['partita_id']}")
                         print(f"    Titolo: {r['titolo']}{quota_str}")
                         print(f"    Periodo possesso nella ricerca: {r['data_inizio']} - {r['data_fine']}")
                         print(f"    Immobili: {r['immobili_posseduti']}")
                 else:
                     print("Nessun dato trovato per il possessore nel periodo specificato.")
             except ValueError:
                 print("ID possessore o formato data non validi.")
             except Exception as e:
                 print(f"Errore: {e}")

        # --- FINE NUOVI BLOCCHI CASE ---

        elif scelta == "11":
             stampa_intestazione("REPORT STATISTICO COMUNE")
             comune = input("Inserisci il nome del comune: ")
             report_data = db.get_report_comune(comune)
             if report_data:
                 print(f"\nStatistiche per {report_data['comune']}:")
                 print(f"  Totale Partite: {report_data['totale_partite']}")
                 print(f"  Partite Attive: {report_data['partite_attive']}")
                 print(f"  Partite Inattive: {report_data['partite_inattive']}")
                 print(f"  Totale Possessori: {report_data['totale_possessori']}")
                 print(f"  Totale Immobili: {report_data['totale_immobili']}")
                 # Il JSON viene restituito come stringa da psycopg2 se è un tipo JSON/JSONB
                 try:
                     imm_per_classe = json.loads(report_data['immobili_per_classe']) if report_data['immobili_per_classe'] else {}
                     print("  Immobili per Classificazione:")
                     if imm_per_classe:
                         for classe, count in imm_per_classe.items():
                             print(f"    - {classe}: {count}")
                     else:
                         print("    N/D")
                 except (json.JSONDecodeError, TypeError):
                     print("  Immobili per Classificazione: (Dati non validi o vuoti)")
                 print(f"  Possessori Medi per Partita: {report_data.get('possessori_per_partita', 0):.2f}")
             else:
                 print(f"Comune '{comune}' non trovato o errore nel generare il report.")

        elif scelta == "12": # <-- AGGIORNATO
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")

def menu_manutenzione(db):
    """Menu per la manutenzione del database"""
    while True:
        stampa_intestazione("MANUTENZIONE DATABASE")
        print("1. Verifica integrita database")
        print("2. Aggiorna Viste Materializzate (per Report Avanzati)")
        # --- NUOVE OPZIONI ---
        print("3. Esegui Manutenzione Generale (VACUUM ANALYZE, etc.)")
        print("4. Analizza Query Lente (Richiede pg_stat_statements)")
        print("5. Controlla Frammentazione Indici")
        print("6. Ottieni Suggerimenti Ottimizzazione")
        # --- FINE NUOVE OPZIONI ---
        print("7. Torna al menu principale") # <-- AGGIORNATO

        scelta = input("\nSeleziona un'opzione (1-7): ") # <-- AGGIORNATO RANGE

        if scelta == "1":
            # Verifica integrità
            stampa_intestazione("VERIFICA INTEGRITA DATABASE")
            print("Avvio verifica...")
            
            problemi_trovati, messaggio = db.verifica_integrita_database()
            
            if problemi_trovati:
                print("\nATTENZIONE: Sono stati rilevati problemi di integrita!")
                print(messaggio)
                
                if input("\nEseguire correzione automatica? (s/n): ").lower() == 's':
                    db.execute_query("CALL ripara_problemi_database(TRUE)")
                    db.commit()
                    print("Correzione automatica eseguita.")
                    
                    # Verifica nuovamente
                    print("\nNuova verifica dopo la correzione:")
                    problemi_trovati, messaggio = db.verifica_integrita_database()
                    if problemi_trovati:
                        print("Ci sono ancora problemi. Potrebbe essere necessario un intervento manuale.")
                    else:
                        print("Tutti i problemi sono stati risolti!")
            else:
                print("\nNessun problema di integrita rilevato. Il database è in buono stato.")
        
        elif scelta == "2": # <-- NUOVO BLOCCO
            stampa_intestazione("AGGIORNAMENTO VISTE MATERIALIZZATE")
            print("Avvio aggiornamento...")
            if db.refresh_materialized_views():
                print("Aggiornamento completato con successo.")
            else:
                print("Errore durante l'aggiornamento delle viste.")

        # --- NUOVI BLOCCHI CASE ---
        elif scelta == "3":
            stampa_intestazione("ESEGUI MANUTENZIONE GENERALE")
            print("Questa operazione potrebbe richiedere del tempo...")
            conferma = input("Procedere? (s/n): ").lower()
            if conferma == 's':
                if db.run_database_maintenance():
                    print("Manutenzione generale completata.")
                else:
                    print("Errore durante l'esecuzione della manutenzione.")
            else:
                print("Operazione annullata.")

        elif scelta == "4":
            stampa_intestazione("ANALIZZA QUERY LENTE")
            print("NOTA: Richiede l'estensione 'pg_stat_statements' abilitata nel database.")
            try:
                min_duration = int(input("Durata minima query in ms (default 1000): ") or 1000)
                slow_queries = db.analyze_slow_queries(min_duration)
                if slow_queries:
                    print(f"\nTrovate {len(slow_queries)} query più lente di {min_duration} ms:")
                    for q in slow_queries:
                         durata_fmt = round(q.get('durata_ms', 0), 2)
                         print(f"\n  ID: {q.get('query_id', 'N/A')}")
                         print(f"    Durata Media: {durata_fmt} ms")
                         print(f"    Chiamate: {q.get('chiamate', 'N/A')}")
                         print(f"    Righe Restituite (Media): {q.get('righe_restituite', 'N/A')}")
                         query_text_short = q.get('query_text', '')[:150] + "..." if len(q.get('query_text', '')) > 150 else q.get('query_text', '')
                         print(f"    Testo Query (inizio): {query_text_short}")
                elif slow_queries is not None: # Lista vuota significa che non ci sono query lente sopra la soglia
                    print(f"Nessuna query trovata con durata media superiore a {min_duration} ms.")
                # Se slow_queries è None, l'errore è già stato loggato da db manager
            except ValueError:
                print("Durata non valida.")
            except Exception as e:
                print(f"Errore durante l'analisi: {e}")


        elif scelta == "5":
            stampa_intestazione("CONTROLLA FRAMMENTAZIONE INDICI")
            print("Esecuzione controllo...")
            # La procedura SQL stampa i risultati tramite RAISE NOTICE.
            # La funzione Python attualmente restituisce una lista vuota,
            # ma esegue la chiamata SQL.
            db.check_index_fragmentation()
            print("Controllo eseguito. Verifica i log del database (o l'output della console se configurato)")
            print("per vedere gli indici con frammentazione > 30%.")


        elif scelta == "6":
            stampa_intestazione("OTTIENI SUGGERIMENTI OTTIMIZZAZIONE")
            suggestions = db.get_optimization_suggestions()
            if suggestions:
                print("\nSuggerimenti:")
                print(suggestions)
            else:
                print("Errore nel recuperare i suggerimenti.")
        # --- FINE NUOVI BLOCCHI CASE ---

        elif scelta == "7": # <-- AGGIORNATO
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")
def menu_audit(db):
    """Menu per la gestione e consultazione del sistema di audit"""
    while True:
        stampa_intestazione("SISTEMA DI AUDIT")
        print("1. Consulta log di audit")
        print("2. Visualizza cronologia di un record")
        print("3. Genera report di audit")
        print("4. Torna al menu principale")
        
        scelta = input("\nSeleziona un'opzione (1-4): ")
        
        if scelta == "1":
            # Consultazione log di audit
            stampa_intestazione("CONSULTA LOG DI AUDIT")
            
            # Raccogli i parametri di ricerca
            print("Inserisci i parametri di ricerca (lascia vuoto per non filtrare)")
            tabella = input("Nome tabella (es. partita, possessore): ")
            
            operazione = None
            op_scelta = input("Tipo operazione (1=Inserimento, 2=Aggiornamento, 3=Cancellazione, vuoto=tutte): ")
            if op_scelta == "1":
                operazione = "I"
            elif op_scelta == "2":
                operazione = "U"
            elif op_scelta == "3":
                operazione = "D"
            
            record_id = input("ID record: ")
            record_id = int(record_id) if record_id and record_id.isdigit() else None
            
            data_inizio_str = input("Data inizio (YYYY-MM-DD): ")
            data_fine_str = input("Data fine (YYYY-MM-DD): ")
            
            utente = input("Utente: ")
            
            # Converti le date
            data_inizio = None
            data_fine = None
            
            try:
                if data_inizio_str:
                    data_inizio = datetime.strptime(data_inizio_str, "%Y-%m-%d").date()
                if data_fine_str:
                    data_fine = datetime.strptime(data_fine_str, "%Y-%m-%d").date()
            except ValueError:
                print("Formato data non valido!")
                continue
            
            # Esegui la ricerca
            logs = db.get_audit_log(
                tabella=tabella if tabella else None,
                operazione=operazione,
                record_id=record_id,
                data_inizio=data_inizio,
                data_fine=data_fine,
                utente=utente if utente else None
            )
            
            # Visualizza i risultati
            stampa_intestazione(f"RISULTATI LOG AUDIT ({len(logs)})")
            
            if not logs:
                print("Nessun log trovato per i criteri specificati")
            else:
                for log in logs:
                    op_map = {"I": "Inserimento", "U": "Aggiornamento", "D": "Cancellazione"}
                    print(f"ID: {log['id']} - {op_map.get(log['operazione'], log['operazione'])} - {log['tabella']} - Record {log['record_id']}")
                    print(f"  Timestamp: {log['timestamp']} - Utente: {log['utente']}")
                    
                    # Mostra dettagli aggiuntivi per alcuni log
                    # Limitiamo la visualizzazione in linea per non sovraccaricare l'output
                    if input("\nVisualizzare dettagli delle modifiche? (s/n): ").lower() == 's':
                        if log['operazione'] == 'U' and log['dati_prima'] and log['dati_dopo']:
                            try:
                                import json
                                dati_prima = json.loads(log['dati_prima'])
                                dati_dopo = json.loads(log['dati_dopo'])
                                
                                print("\nModifiche:")
                                for chiave in dati_prima:
                                    if chiave in dati_dopo and dati_prima[chiave] != dati_dopo[chiave]:
                                        print(f"  - {chiave}: {dati_prima[chiave]} -> {dati_dopo[chiave]}")
                            except:
                                print("  Impossibile elaborare i dettagli delle modifiche")
                        elif log['operazione'] == 'I':
                            print("  Inserimento di un nuovo record")
                        elif log['operazione'] == 'D':
                            print("  Cancellazione di un record esistente")
        
        elif scelta == "2":
            # Visualizza cronologia di un record
            stampa_intestazione("CRONOLOGIA RECORD")
            
            tabella = input("Nome tabella (es. partita, possessore): ")
            record_id = input("ID record: ")
            
            if not tabella or not record_id.isdigit():
                print("Tabella e ID record sono richiesti!")
                continue
            
            record_id = int(record_id)
            
            # Ottieni la cronologia
            history = db.get_record_history(tabella, record_id)
            
            stampa_intestazione(f"CRONOLOGIA {tabella.upper()} ID {record_id} ({len(history)} modifiche)")
            
            if not history:
                print(f"Nessuna modifica registrata per {tabella} con ID {record_id}")
            else:
                for i, record in enumerate(history, 1):
                    op_map = {"I": "Inserimento", "U": "Aggiornamento", "D": "Cancellazione"}
                    print(f"{i}. {op_map.get(record['operazione'], record['operazione'])} - {record['timestamp']} - {record['utente']}")
                    
                    if record['operazione'] == 'U':
                        print("  Modifiche:")
                        try:
                            import json
                            dati_prima = json.loads(record['dati_prima']) if record['dati_prima'] else {}
                            dati_dopo = json.loads(record['dati_dopo']) if record['dati_dopo'] else {}
                            
                            for chiave in dati_prima:
                                if chiave in dati_dopo and dati_prima[chiave] != dati_dopo[chiave]:
                                    val_prima = "NULL" if dati_prima[chiave] is None else dati_prima[chiave]
                                    val_dopo = "NULL" if dati_dopo[chiave] is None else dati_dopo[chiave]
                                    print(f"    - {chiave}: {val_prima} -> {val_dopo}")
                        except Exception as e:
                            print(f"    Impossibile elaborare i dettagli: {e}")
                    
                    print()
        
        elif scelta == "3":
            # Genera report di audit
            stampa_intestazione("GENERA REPORT DI AUDIT")
            
            # Raccogli i parametri di ricerca
            print("Inserisci i parametri per il report (lascia vuoto per non filtrare)")
            tabella = input("Nome tabella (es. partita, possessore): ")
            
            operazione = None
            op_scelta = input("Tipo operazione (1=Inserimento, 2=Aggiornamento, 3=Cancellazione, vuoto=tutte): ")
            if op_scelta == "1":
                operazione = "I"
            elif op_scelta == "2":
                operazione = "U"
            elif op_scelta == "3":
                operazione = "D"
            
            data_inizio_str = input("Data inizio (YYYY-MM-DD): ")
            data_fine_str = input("Data fine (YYYY-MM-DD): ")
            
            utente = input("Utente: ")
            
            # Converti le date
            data_inizio = None
            data_fine = None
            
            try:
                if data_inizio_str:
                    data_inizio = datetime.strptime(data_inizio_str, "%Y-%m-%d").date()
                if data_fine_str:
                    data_fine = datetime.strptime(data_fine_str, "%Y-%m-%d").date()
            except ValueError:
                print("Formato data non valido!")
                continue
            
            # Genera il report
            report = db.genera_report_audit(
                tabella=tabella if tabella else None,
                operazione=operazione,
                data_inizio=data_inizio,
                data_fine=data_fine,
                utente=utente if utente else None
            )
            
            # Visualizza il report
            stampa_intestazione("REPORT DI AUDIT")
            print(report)
            
            # Salvataggio su file
            if input("\nSalvare su file? (s/n): ").lower() == 's':
                oggi = date.today().strftime("%Y%m%d")
                filename = f"report_audit_{oggi}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"Report salvato nel file: {filename}")
        
        elif scelta == "4":
            break
        else:
            print("Opzione non valida!")
        
        input("\nPremi INVIO per continuare...")

def menu_utenti(db):
    """Menu per la gestione degli utenti"""
    while True:
        stampa_intestazione("GESTIONE UTENTI")
        print("1. Crea nuovo utente")
        print("2. Simula Login Utente")
        print("3. Verifica Permesso Utente")
        print("4. Torna al menu principale")

        scelta = input("\nSeleziona un'opzione (1-4): ")

        if scelta == "1":
            # Crea nuovo utente
            stampa_intestazione("CREA NUOVO UTENTE")
            username = input("Username: ")
            password = input("Password: ")
            nome_completo = input("Nome completo: ")
            email = input("Email: ")
            print("Ruoli disponibili: admin, archivista, consultatore")
            ruolo = input("Ruolo: ")

            if not all([username, password, nome_completo, email, ruolo]):
                print("Tutti i campi sono obbligatori.")
                continue

            if ruolo not in ['admin', 'archivista', 'consultatore']:
                print("Ruolo non valido.")
                continue

            # Hash della password (IMPORTANTE: usare un metodo più sicuro in produzione!)
            # Questo è solo un esempio dimostrativo con SHA256.
            # In un'app reale, usare librerie come bcrypt o Argon2.
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

            if db.create_user(username, password_hash, nome_completo, email, ruolo):
                print(f"Utente '{username}' creato con successo.")
            else:
                print(f"Errore durante la creazione dell'utente '{username}'.")

        elif scelta == "2":
            # Simula Login
            stampa_intestazione("SIMULA LOGIN UTENTE")
            username = input("Username: ")
            password = input("Password: ")

            credentials = db.get_user_credentials(username)

            if credentials:
                # Verifica password (IMPORTANTE: confrontare gli hash!)
                # Di nuovo, questo è un esempio con SHA256. Usare la stessa funzione di hashing
                # utilizzata durante la creazione dell'utente.
                entered_password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

                if entered_password_hash == credentials['password_hash']:
                    print(f"Login riuscito per l'utente ID: {credentials['id']}")
                    # Registra l'accesso riuscito
                    db.register_access(credentials['id'], 'login', esito=True)
                    # Qui potresti salvare l'ID utente per operazioni successive
                else:
                    print("Password errata.")
                    # Registra il tentativo di login fallito
                    db.register_access(credentials['id'], 'login', esito=False)
            else:
                print("Utente non trovato o non attivo.")
                # Opzionalmente, potresti registrare un tentativo di login per un utente inesistente
                # ma richiederebbe una logica diversa (es. utente_id = 0 o NULL).

        elif scelta == "3":
            # Verifica Permesso
            stampa_intestazione("VERIFICA PERMESSO UTENTE")
            try:
                utente_id = int(input("ID Utente: "))
                permesso = input("Nome del permesso (es. 'modifica_partite'): ")

                if db.check_permission(utente_id, permesso):
                    print(f"L'utente {utente_id} HA il permesso '{permesso}'.")
                else:
                    print(f"L'utente {utente_id} NON HA il permesso '{permesso}'.")
            except ValueError:
                print("ID Utente non valido.")
            except Exception as e:
                print(f"Errore durante la verifica del permesso: {e}")


        elif scelta == "4":
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")

def menu_backup(db):
    """Menu per le operazioni di Backup e Restore"""
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

        scelta = input("\nSeleziona un'opzione (1-7): ")

        if scelta == "1":
            stampa_intestazione("OTTIENI COMANDO BACKUP")
            print("Tipi di backup: completo, schema, dati")
            tipo_backup = input("Inserisci tipo di backup (default: completo): ") or 'completo'
            if tipo_backup not in ['completo', 'schema', 'dati']:
                print("Tipo non valido.")
                continue

            command_suggestion = db.get_backup_command_suggestion(tipo=tipo_backup)
            if command_suggestion:
                print("\n--- Comando Suggerito (da eseguire nella shell) ---")
                print(command_suggestion)
                print("-" * 55)
            else:
                print("Errore nel generare il suggerimento del comando.")

        elif scelta == "2":
            stampa_intestazione("LOG BACKUP RECENTI")
            logs = db.get_backup_logs()
            if logs:
                for log in logs:
                    esito_str = "OK" if log['esito'] else "FALLITO"
                    dimensione_str = f"{log['dimensione_bytes']} bytes" if log['dimensione_bytes'] else "N/D"
                    print(f"ID: {log['id']} - {log['timestamp']} - Tipo: {log['tipo']} - Esito: {esito_str}")
                    print(f"  File: {log['nome_file']} ({dimensione_str})")
                    print(f"  Utente: {log['utente']}")
                    if log['messaggio']:
                        print(f"  Messaggio: {log['messaggio']}")
                    print("-" * 30)
            else:
                print("Nessun log di backup trovato.")

        elif scelta == "3":
            stampa_intestazione("OTTIENI COMANDO RESTORE")
            try:
                log_id = int(input("Inserisci l'ID del log di backup da cui ripristinare: "))
                command_suggestion = db.get_restore_command_suggestion(log_id)
                if command_suggestion:
                    print("\n--- Comando Suggerito (da eseguire nella shell) ---")
                    print(command_suggestion)
                    print("-" * 55)
                    print("ATTENZIONE: Il restore sovrascriverà i dati attuali!")
                else:
                    print("ID log non valido o errore nel generare il suggerimento.")
            except ValueError:
                print("ID non valido.")

        elif scelta == "4":
             stampa_intestazione("REGISTRA BACKUP MANUALE")
             nome_file = input("Nome del file di backup creato: ")
             percorso_file = input("Percorso completo del file: ")
             utente = input("Utente che ha eseguito il backup (default: 'manuale'): ") or 'manuale'
             tipo = input("Tipo ('completo', 'schema', 'dati'): ")
             esito_str = input("Il backup è andato a buon fine? (s/n): ").lower()
             messaggio = input("Messaggio aggiuntivo (opzionale): ")
             dimensione_str = input("Dimensione in bytes (opzionale): ")

             if not all([nome_file, percorso_file, tipo]):
                 print("Nome file, percorso e tipo sono obbligatori.")
                 continue
             if tipo not in ['completo', 'schema', 'dati']:
                 print("Tipo non valido.")
                 continue

             esito = esito_str == 's'
             dimensione = int(dimensione_str) if dimensione_str.isdigit() else None

             backup_id = db.register_backup_log(nome_file, utente, tipo, esito, percorso_file, dimensione, messaggio)
             if backup_id:
                 print(f"Backup manuale registrato con ID: {backup_id}")
             else:
                 print("Errore durante la registrazione del backup manuale.")


        elif scelta == "5":
            stampa_intestazione("GENERA SCRIPT BACKUP AUTOMATICO")
            backup_dir = input("Inserisci la directory di destinazione per i backup (es. /var/backups/catasto): ")
            script_name = input("Nome del file per lo script (es. backup_catasto.sh): ")
            if not backup_dir or not script_name:
                print("Directory e nome script sono obbligatori.")
                continue

            script_content = db.generate_backup_script(backup_dir)
            if script_content:
                try:
                    with open(script_name, 'w', encoding='utf-8') as f:
                        f.write(script_content)
                    os.chmod(script_name, 0o755) # Rende lo script eseguibile
                    print(f"Script '{script_name}' generato con successo nella directory corrente.")
                    print("Ricorda di configurare un cron job o un task schedulato per eseguirlo regolarmente.")
                except Exception as e:
                    print(f"Errore durante il salvataggio dello script: {e}")
            else:
                print("Errore durante la generazione dello script.")

        elif scelta == "6":
            stampa_intestazione("PULISCI LOG BACKUP VECCHI")
            try:
                giorni = int(input("Conserva i log degli ultimi quanti giorni? (default: 30): ") or 30)
                if db.cleanup_old_backup_logs(giorni):
                    print("Pulizia dei log vecchi completata.")
                else:
                    print("Errore durante la pulizia dei log.")
            except ValueError:
                print("Numero di giorni non valido.")

        elif scelta == "7":
            break
        else:
            print("Opzione non valida!")

        input("\nPremi INVIO per continuare...")
def menu_storico_avanzato(db):
    """Menu per le funzionalità storiche avanzate"""
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

        scelta = input("\nSeleziona un'opzione (1-8): ")

        if scelta == "1":
            stampa_intestazione("PERIODI STORICI")
            periodi = db.get_historical_periods()
            if periodi:
                for p in periodi:
                    fine = p.get('anno_fine', 'oggi')
                    print(f"ID: {p['id']} - {p['nome']} ({p['anno_inizio']} - {fine})")
                    if p['descrizione']:
                        print(f"  Desc: {p['descrizione']}")
            else:
                print("Nessun periodo storico trovato.")

        elif scelta == "2":
            stampa_intestazione("OTTIENI NOME STORICO ENTITÀ")
            tipo_entita = input("Tipo entità (comune/localita): ").lower()
            if tipo_entita not in ['comune', 'localita']:
                print("Tipo entità non valido.")
                continue
            try:
                entita_id = int(input(f"ID {tipo_entita}: "))
                anno_str = input("Anno (lascia vuoto per anno corrente): ")
                anno = int(anno_str) if anno_str.isdigit() else None

                nome_info = db.get_historical_name(tipo_entita, entita_id, anno)
                if nome_info:
                    fine = nome_info.get('anno_fine', 'oggi')
                    print(f"\nNome in anno {anno if anno else datetime.now().year}: {nome_info['nome']}")
                    print(f"  Periodo: {nome_info['periodo_nome']} ({nome_info['anno_inizio']} - {fine})")
                else:
                    print(f"Nessun nome storico trovato per {tipo_entita} ID {entita_id} nell'anno specificato.")
            except ValueError:
                print("ID entità non valido.")

        elif scelta == "3":
            stampa_intestazione("REGISTRA NOME STORICO")
            tipo_entita = input("Tipo entità (comune/localita): ").lower()
            if tipo_entita not in ['comune', 'localita']:
                print("Tipo entità non valido.")
                continue
            try:
                entita_id = int(input(f"ID {tipo_entita}: "))
                nome_storico = input("Nome storico: ")
                # Mostra i periodi disponibili per la selezione
                print("\nPeriodi storici disponibili:")
                periodi = db.get_historical_periods()
                if not periodi:
                    print("Nessun periodo storico definito nel DB. Impossibile procedere.")
                    continue
                for p in periodi:
                     print(f"  ID: {p['id']} - {p['nome']}")
                periodo_id = int(input("ID Periodo storico: "))
                anno_inizio = int(input("Anno inizio validità nome: "))
                anno_fine_str = input("Anno fine validità nome (lascia vuoto se valido fino a fine periodo): ")
                anno_fine = int(anno_fine_str) if anno_fine_str.isdigit() else None
                note = input("Note (opzionale): ")

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
             titolo = input("Titolo (parziale, lascia vuoto per non filtrare): ")
             tipo_doc = input("Tipo documento (esatto, lascia vuoto per non filtrare): ")
             periodo_id_str = input("ID Periodo storico (lascia vuoto per non filtrare): ")
             anno_inizio_str = input("Anno inizio (lascia vuoto per non filtrare): ")
             anno_fine_str = input("Anno fine (lascia vuoto per non filtrare): ")
             partita_id_str = input("ID Partita collegata (lascia vuoto per non filtrare): ")

             try:
                 periodo_id = int(periodo_id_str) if periodo_id_str.isdigit() else None
                 anno_inizio = int(anno_inizio_str) if anno_inizio_str.isdigit() else None
                 anno_fine = int(anno_fine_str) if anno_fine_str.isdigit() else None
                 partita_id = int(partita_id_str) if partita_id_str.isdigit() else None

                 documenti = db.search_historical_documents(
                     title=titolo if titolo else None,
                     doc_type=tipo_doc if tipo_doc else None,
                     period_id=periodo_id,
                     year_start=anno_inizio,
                     year_end=anno_fine,
                     partita_id=partita_id
                 )

                 if documenti:
                     print(f"\nTrovati {len(documenti)} documenti:")
                     for doc in documenti:
                          print(f"\n  ID: {doc['documento_id']} - Titolo: {doc['titolo']}")
                          print(f"    Tipo: {doc['tipo_documento']} - Anno: {doc['anno']} - Periodo: {doc['periodo_nome']}")
                          if doc['descrizione']:
                               print(f"    Desc: {doc['descrizione']}")
                          if doc['partite_correlate']:
                               print(f"    Partite Correlate: {doc['partite_correlate']}")
                 else:
                     print("Nessun documento trovato per i criteri specificati.")
             except ValueError:
                  print("Input ID o Anno non valido.")

        elif scelta == "5":
            stampa_intestazione("ALBERO GENEALOGICO PROPRIETÀ")
            try:
                partita_id = int(input("Inserisci l'ID della partita di partenza: "))
                albero = db.get_property_genealogy(partita_id)
                if albero:
                    print("\nLivello | Relazione    | ID Partita | Comune           | N. Partita | Tipo       | Possessori")
                    print("--------|--------------|------------|------------------|------------|------------|-----------")
                    for nodo in albero:
                        livello = nodo.get('livello', '?')
                        rel = nodo.get('tipo_relazione', '').ljust(12)
                        p_id = str(nodo.get('partita_id', '')).ljust(10)
                        com = nodo.get('comune_nome', '').ljust(16)
                        num = str(nodo.get('numero_partita', '')).ljust(10)
                        tipo = nodo.get('tipo', '').ljust(10)
                        poss = nodo.get('possessori', '')
                        data_var = f" (da {nodo['data_variazione']})" if nodo.get('data_variazione') else ""
                        print(f" {str(livello).rjust(6)} | {rel} | {p_id} | {com} | {num} | {tipo} | {poss}{data_var}")
                else:
                    print("Impossibile generare l'albero genealogico per la partita specificata.")
            except ValueError:
                 print("ID partita non valido.")

        elif scelta == "6":
             stampa_intestazione("STATISTICHE CATASTALI PER PERIODO")
             comune = input("Filtra per comune (lascia vuoto per tutti): ")
             try:
                  anno_i_str = input("Anno inizio (default 1900): ") or "1900"
                  anno_f_str = input("Anno fine (default anno corrente): ")
                  anno_i = int(anno_i_str)
                  anno_f = int(anno_f_str) if anno_f_str.isdigit() else None

                  stats = db.get_cadastral_stats_by_period(
                      comune=comune if comune else None,
                      year_start=anno_i,
                      year_end=anno_f
                  )

                  if stats:
                       print("\nAnno  | Comune           | Nuove P. | Chiuse P. | Tot Attive | Variazioni | Imm. Reg.")
                       print("------|------------------|----------|-----------|------------|------------|-----------")
                       for s in stats:
                            print(f" {s['anno']} | {s.get('comune_nome', 'N/D').ljust(16)} | "
                                  f"{str(s.get('nuove_partite', 0)).rjust(8)} | "
                                  f"{str(s.get('partite_chiuse', 0)).rjust(9)} | "
                                  f"{str(s.get('totale_partite_attive', 0)).rjust(10)} | "
                                  f"{str(s.get('variazioni', 0)).rjust(10)} | "
                                  f"{str(s.get('immobili_registrati', 0)).rjust(9)}")
                  else:
                       print("Nessuna statistica trovata per il periodo/comune specificato.")
             except ValueError:
                  print("Input Anno non valido.")

        elif scelta == "7":
            stampa_intestazione("COLLEGA DOCUMENTO A PARTITA")
            try:
                doc_id = int(input("ID del Documento Storico: "))
                part_id = int(input("ID della Partita da collegare: "))
                print("Rilevanza: primaria, secondaria, correlata")
                rilevanza = input("Inserisci rilevanza (default: correlata): ") or 'correlata'
                note = input("Note (opzionale): ")

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



def main():
    # Configura la connessione
    db_config = {
        "dbname": "catasto_storico",
        "user": "postgres",
        "password": "Markus74",  # Sostituisci con la tua password
        "host": "localhost",
        "port": 5432,
        "schema": "catasto"
    }
    
    # Inizializza il gestore
    db = CatastoDBManager(**db_config)
    
    # Verifica la connessione
    if not db.connect():
        print("ERRORE: Impossibile connettersi al database. Verifica i parametri.")
        sys.exit(1)
    
    try:
        # Esempi di operazioni
        menu_principale(db)
    except KeyboardInterrupt:
        print("\nOperazione interrotta dall'utente.")
    except Exception as e:
        print(f"ERRORE: {e}")
    finally:
        # Chiudi sempre la connessione
        db.disconnect()
        print("\nConnessione al database chiusa.")

if __name__ == "__main__":
    main()