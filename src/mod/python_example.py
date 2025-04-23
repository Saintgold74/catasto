#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Esempio di utilizzo del gestore database catastale
=================================================
Questo script mostra esempi pratici di come utilizzare
la classe CatastoDBManager per interagire con il database.

Autore: Claude AI
Data: 17/04/2025
"""

from catasto_db_manager import CatastoDBManager
from datetime import date, datetime
import json
import os
import sys

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
    paternita = input("Paternità (es. 'fu Roberto'): ")
    
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

def menu_principale(db):
    """Menu principale per testare varie funzionalità"""
    while True:
        stampa_intestazione("MENU PRINCIPALE")
        print("1. Consultazione dati")
        print("2. Inserimento e gestione dati")
        print("3. Generazione report")
        print("4. Manutenzione database")
        print("5. Esci")
        
        scelta = input("\nSeleziona un'opzione (1-5): ")
        
        if scelta == "1":
            menu_consultazione(db)
        elif scelta == "2":
            menu_inserimento(db)
        elif scelta == "3":
            menu_report(db)
        elif scelta == "4":
            menu_manutenzione(db)
        elif scelta == "5":
            break
        else:
            print("Opzione non valida!")

def menu_consultazione(db):
    """Menu per operazioni di consultazione"""
    while True:
        stampa_intestazione("CONSULTAZIONE DATI")
        print("1. Elenco comuni")
        print("2. Elenco partite per comune")
        print("3. Elenco possessori per comune")
        print("4. Ricerca partite")
        print("5. Dettagli partita")
        print("6. Torna al menu principale")
        
        scelta = input("\nSeleziona un'opzione (1-6): ")
        
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
        print("3. Registra nuova proprietà")
        print("4. Registra passaggio di proprietà")
        print("5. Registra consultazione")
        print("6. Torna al menu principale")
        
        scelta = input("\nSeleziona un'opzione (1-6): ")
        
        if scelta == "1":
            # Aggiungi comune
            stampa_intestazione("AGGIUNGI NUOVO COMUNE")
            nome = input("Nome comune: ")
            provincia = input("Provincia: ")
            regione = input("Regione: ")
            
            if nome and provincia and regione:
                # Esegui l'inserimento
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
        
        elif scelta == "2":
            # Aggiungi possessore
            inserisci_possessore(db)
        
        elif scelta == "3":
            # Registra nuova proprietà
            stampa_intestazione("REGISTRA NUOVA PROPRIETÀ")
            
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
                        paternita = input("Paternità (se diversa): ")
                        quota = input("Quota (vuoto se proprietà esclusiva): ")
                        
                        possessore = {
                            "nome_completo": nome_completo,
                            "cognome_nome": cognome_nome if cognome_nome else nome_completo.split()[0],
                            "paternita": paternita,
                        }
                    else:
                        # Nuovo possessore
                        print(f"Possessore non trovato. Inserisci i dettagli:")
                        cognome_nome = input("Cognome e nome: ")
                        paternita = input("Paternità: ")
                        quota = input("Quota (vuoto se proprietà esclusiva): ")
                        
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
                    
                    localita = input("Località: ")
                    tipo_localita = input("Tipo località (regione/via/borgata): ") or "via"
                    classificazione = input("Classificazione: ")
                    
                    numero_piani = input("Numero piani (opzionale): ")
                    numero_vani = input("Numero vani (opzionale): ")
                    consistenza = input("Consistenza (opzionale): ")
                    
                    immobile = {
                        "natura": natura,
                        "localita": localita,
                        "tipo_localita": tipo_localita,
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
                
                # Registrazione della proprietà
                if db.registra_nuova_proprieta(
                    comune, numero_partita, data_impianto, possessori, immobili
                ):
                    print(f"Proprietà registrata con successo: {comune}, partita {numero_partita}")
                else:
                    print("Errore durante la registrazione della proprietà")
                
            except ValueError as e:
                print(f"Errore: {e}")
            except Exception as e:
                print(f"Errore imprevisto: {e}")
        
        elif scelta == "4":
            # Registra passaggio di proprietà
            stampa_intestazione("REGISTRA PASSAGGIO DI PROPRIETÀ")
            
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
                            paternita = input("Paternità (se diversa): ")
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
                    print(f"Passaggio di proprietà registrato con successo")
                else:
                    print("Errore durante la registrazione del passaggio di proprietà")
                
            except ValueError as e:
                print(f"Errore: {e}")
            except Exception as e:
                print(f"Errore imprevisto: {e}")
        
        elif scelta == "5":
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
                
                documento = input("Documento identità: ")
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
        
        elif scelta == "6":
            break
        else:
            print("Opzione non valida!")
        
        input("\nPremi INVIO per continuare...")

def menu_report(db):
    """Menu per la generazione di report"""
    while True:
        stampa_intestazione("GENERAZIONE REPORT")
        print("1. Certificato di proprietà")
        print("2. Report genealogico")
        print("3. Report possessore")
        print("4. Torna al menu principale")
        
        scelta = input("\nSeleziona un'opzione (1-4): ")
        
        if scelta == "1":
            # Certificato di proprietà
            partita_id = input("Inserisci l'ID della partita: ")
            if partita_id.isdigit():
                certificato = db.genera_certificato_proprieta(int(partita_id))
                
                stampa_intestazione("CERTIFICATO DI PROPRIETÀ")
                print(certificato)
                
                # Salvataggio su file
                if input("\nSalvare su file? (s/n): ").lower() == 's':
                    filename = f"certificato_partita_{partita_id}_{date.today()}.txt"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(certificato)
                    print(f"Certificato salvato nel file: {filename}")
            else:
                print("ID non valido!")
        
        elif scelta == "2":
            # Report genealogico
            partita_id = input("Inserisci l'ID della partita: ")
            if partita_id.isdigit():
                report = db.genera_report_genealogico(int(partita_id))
                
                stampa_intestazione("REPORT GENEALOGICO")
                print(report)
                
                # Salvataggio su file
                if input("\nSalvare su file? (s/n): ").lower() == 's':
                    filename = f"report_genealogico_{partita_id}_{date.today()}.txt"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(report)
                    print(f"Report salvato nel file: {filename}")
            else:
                print("ID non valido!")
        
        elif scelta == "3":
            # Report possessore
            possessore_id = input("Inserisci l'ID del possessore: ")
            if possessore_id.isdigit():
                report = db.genera_report_possessore(int(possessore_id))
                
                stampa_intestazione("REPORT POSSESSORE")
                print(report)
                
                # Salvataggio su file
                if input("\nSalvare su file? (s/n): ").lower() == 's':
                    filename = f"report_possessore_{possessore_id}_{date.today()}.txt"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(report)
                    print(f"Report salvato nel file: {filename}")
            else:
                print("ID non valido!")
        
        elif scelta == "4":
            break
        else:
            print("Opzione non valida!")
        
        input("\nPremi INVIO per continuare...")

def menu_manutenzione(db):
    """Menu per la manutenzione del database"""
    while True:
        stampa_intestazione("MANUTENZIONE DATABASE")
        print("1. Verifica integrità database")
        print("2. Torna al menu principale")
        
        scelta = input("\nSeleziona un'opzione (1-2): ")
        
        if scelta == "1":
            # Verifica integrità
            stampa_intestazione("VERIFICA INTEGRITÀ DATABASE")
            print("Avvio verifica...")
            
            problemi_trovati, messaggio = db.verifica_integrita_database()
            
            if problemi_trovati:
                print("\nATTENZIONE: Sono stati rilevati problemi di integrità!")
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
                print("\nNessun problema di integrità rilevato. Il database è in buono stato.")
        
        elif scelta == "2":
            break
        else:
            print("Opzione non valida!")
        
        input("\nPremi INVIO per continuare...")

def main():
    # Configura la connessione
    db_config = {
        "dbname": "catasto_storico",
        "user": "postgres",
        "password": "Markus74",  # Inserisci la tua password qui
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

            