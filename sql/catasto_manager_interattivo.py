import os
import sys
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import json
import csv

import psycopg2
from psycopg2 import pool, sql, extras
import yaml
import dotenv

# [Tutto il codice precedente rimane invariato, aggiungo le seguenti funzioni alla fine]

def menu_principale():
    """
    Menu principale interattivo per il sistema catastale
    """
    manager = CatastoManager()
    
    while True:
        print("\n--- SISTEMA GESTIONE CATASTO STORICO ---")
        print("1. Registra Nuova Proprietà")
        print("2. Cerca Proprietà")
        print("3. Visualizza Dettagli Proprietà")
        print("4. Esci")
        
        scelta = input("Seleziona un'opzione: ").strip()
        
        try:
            if scelta == '1':
                registra_proprieta_interattiva()
            
            elif scelta == '2':
                # Ricerca proprietà
                print("\n--- RICERCA PROPRIETÀ ---")
                print("Criteri di ricerca (lascia vuoto per saltare)")
                
                filtri = {}
                comune = input("Comune: ").strip()
                if comune:
                    filtri['comune'] = comune
                
                numero_partita = input("Numero Partita: ").strip()
                if numero_partita:
                    filtri['numero_partita'] = int(numero_partita)
                
                data_inizio = input("Data Inizio (AAAA-MM-GG): ").strip()
                if data_inizio:
                    filtri['data_inizio'] = date.fromisoformat(data_inizio)
                
                data_fine = input("Data Fine (AAAA-MM-GG): ").strip()
                if data_fine:
                    filtri['data_fine'] = date.fromisoformat(data_fine)
                
                # Esegui ricerca
                risultati = manager.cerca_proprieta(filtri)
                
                if risultati:
                    print("\nRISULTATI RICERCA:")
                    print("ID  Comune      N.Partita  Data Impianto  Stato   Possessori")
                    print("-" * 70)
                    for prop in risultati:
                        print(f"{prop['id']:<3} {prop['comune_nome']:<12} {prop['numero_partita']:<10} {prop['data_impianto']} {prop['stato']:<7} {prop['possessori']}")
                else:
                    print("Nessuna proprietà trovata.")
            
            elif scelta == '3':
                # Visualizza dettagli di una specifica proprietà
                try:
                    id_partita = int(input("Inserisci ID Partita: ").strip())
                    dettagli = manager.cerca_proprieta({'numero_partita': id_partita})
                    
                    if dettagli:
                        prop = dettagli[0]
                        print("\n--- DETTAGLI PROPRIETÀ ---")
                        print(f"ID Partita: {prop['id']}")
                        print(f"Comune: {prop['comune_nome']}")
                        print(f"Numero Partita: {prop['numero_partita']}")
                        print(f"Data Impianto: {prop['data_impianto']}")
                        print(f"Stato: {prop['stato']}")
                        print(f"Possessori: {prop['possessori']}")
                        print(f"Numero Immobili: {prop['num_immobili']}")
                    else:
                        print("Nessuna proprietà trovata con questo ID.")
                
                except ValueError:
                    print("ID Partita non valido.")
                except Exception as e:
                    print(f"Errore durante la ricerca: {e}")
            
            elif scelta == '4':
                print("Chiusura del sistema. Arrivederci!")
                break
            
            else:
                print("Opzione non valida. Riprova.")
        
        except Exception as e:
            print(f"Si è verificato un errore: {e}")
        
        input("\nPremi Invio per continuare...")

def main():
    """
    Punto di ingresso principale dell'applicazione
    """
    try:
        # Configurazione logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("catasto.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        logger = logging.getLogger(__name__)

        # Verifica configurazione
        manager = CatastoManager()
        
        # Avvia menu principale
        menu_principale()

    except Exception as e:
        print(f"Errore di avvio: {e}")
        logger.error(f"Errore di avvio dell'applicazione: {e}")

if __name__ == "__main__":
    main()
