#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Applicazione Principale Catasto Storico (Refactored)
====================================================
Punto di ingresso per l'applicazione di gestione del catasto storico.
Gestisce la configurazione, la connessione al database, l'autenticazione
e il lancio del menu principale.

Autore: Marco Santoro (Versione Refactored)
Data: [Data Corrente]
"""

import sys
import socket # Assicurati che socket sia importato
import logging # Il setup sarà chiamato da logger_setup
# import netifaces # Per ottenere l'IP, alternativa a socket.gethostbyname(socket.gethostname())
                  # Potrebbe richiedere `pip install netifaces`
                  # Se non vuoi dipendenze esterne, usa socket come prima o un default.

from utils.logger_setup import setup_logging
from utils.config_loader import load_db_config
from core.db_manager import DatabaseManager
from core.services import utenti_service # Per login/logout/registrazione
from ui.console.ui_utils import stampa_locandina_introduzione, input_valore, input_sicuro_password, chiedi_conferma
from ui.console.menu_handler import menu_principale
from typing import Optional
#from core.services import utenti_service
from datetime import date, datetime # Assicura che 'date' e 'datetime' siano importati
# Importa i moduli necessari per il menu principale e altre funzionalità
# Assicurati che i moduli siano correttamente importati e disponibili

# Logger globale per main_app
logger: Optional[logging.Logger] = None

# Stato globale del login (mantenuto in main_app)
logged_in_user_id: Optional[int] = None
current_user_role_id: Optional[int] = None 
current_session_id: Optional[str] = None
client_ip_address: Optional[str] = "127.0.0.1" # Default

def get_local_ip_address():
    """
    Tenta di ottenere l'indirizzo IP locale usando solo il modulo standard socket.
    Se fallisce, restituisce un indirizzo di fallback (es. '127.0.0.1').
    """
    try:
        # Questo è un trucco comune per ottenere l'IP con cui la macchina
        # si connetterebbe a un server esterno. Non invia dati reali.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1) # Timeout breve per non bloccare a lungo
        try:
            # Non è necessario che l'host sia effettivamente raggiungibile,
            # serve solo per far sì che il sistema operativo scelga un'interfaccia.
            s.connect(('8.8.8.8', 1)) 
            ip_address = s.getsockname()[0]
        except Exception:
            # Fallback se connect fallisce (es. nessuna connessione di rete attiva)
            # Prova con gethostname, anche se a volte può restituire 'localhost' o 127.0.0.1
            try:
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
            except socket.gaierror: # Errore nella risoluzione dell'hostname
                ip_address = '127.0.0.1' # Fallback finale
        finally:
            s.close()
        return ip_address
    except Exception:
        # Fallback estremo se anche la creazione del socket fallisce
        return "127.0.0.1"
def authenticate_user(db_manager_instance: DatabaseManager) -> bool:
    """Gestisce il processo di login o registrazione dell'utente."""
    global logged_in_user_id, current_user_role_id, current_session_id, client_ip_address
    
    client_ip_address = get_local_ip_address() # Ottieni l'IP all'inizio
    logger.info(f"Indirizzo IP client rilevato/usato: {client_ip_address}")

    max_login_attempts = 3
    login_attempts = 0

    while login_attempts < max_login_attempts:
        print("\n--- Autenticazione ---")
        print("1. Login")
        print("2. Registra nuovo utente (self-service, se abilitato)")
        print("0. Esci dall'applicazione")
        auth_choice = input("Scegli un'opzione: ")

        if auth_choice == '1':
            username = input_valore("Username:", obbligatorio=True)
            if not username: continue # Torna a scelta auth
            password = input_sicuro_password()
            if not password: continue # Torna a scelta auth

            try:
                user_id, role_id, session_id, message = utenti_service.login_user_service(
                    db_manager_instance, username, password, client_ip_address
                )
                print(message) # Messaggio da login_user_service
                if user_id and role_id and session_id:
                    logged_in_user_id = user_id
                    current_user_role_id = role_id
                    current_session_id = session_id
                    logger.info(f"Login successo per utente ID {user_id}, Ruolo ID {role_id}, Sessione {session_id}")
                    return True # Autenticazione riuscita
                else:
                    login_attempts += 1
                    print(f"Tentativi di login rimasti: {max_login_attempts - login_attempts}")
                    if login_attempts >= max_login_attempts:
                        print("Troppi tentativi di login falliti. Uscita dall'applicazione.")
                        return False
            except Exception as e:
                logger.error(f"Errore durante il tentativo di login: {e}", exc_info=True)
                print(f"Si è verificato un errore durante il login: {e}")
                # Non incrementare tentativi per errori di sistema, ma l'utente deve riprovare
        
        elif auth_choice == '2':
            # Logica di registrazione self-service
            # Di solito un nuovo utente si registra con un ruolo base (es. "utente standard")
            # L'amministratore può poi elevare i privilegi se necessario.
            print("\n--- Registrazione Nuovo Utente ---")
            username_reg = input_valore("Scegli Username:", obbligatorio=True)
            if not username_reg: continue
            email_reg = input_valore("Email:", obbligatorio=True) # Aggiungere validazione email
            if not email_reg: continue
            password_reg1 = input_sicuro_password("Scegli Password: ")
            if not password_reg1: continue
            password_reg2 = input_sicuro_password("Conferma Password: ")
            if password_reg1 != password_reg2:
                print("Le password non coincidono. Riprova.")
                continue

            
            nome_completo_reg = input_valore("Nome Completo:", obbligatorio=True) # <-- CHIEDI NOME COMPLETO
            if not nome_completo_reg: continue 
            # Ruolo di default per la registrazione self-service (es. ID 2 = Utente Standard)
                # Questo ID dovrebbe essere configurabile o recuperato dal DB.
            DEFAULT_SELF_REGISTER_ROLE_ID = 2 

            try:
                # Passa nome_completo_reg alla funzione di servizio
                new_user_id = utenti_service.register_user_service(
                    db_manager_instance, username_reg, password_reg1, email_reg, 
                    DEFAULT_SELF_REGISTER_ROLE_ID, 
                    nome_completo=nome_completo_reg, # <-- PASSALO QUI
                    client_ip_address=client_ip_address,
                    created_by_user_id=None # Self-registration
                    # Considera di passare un dizionario audit_params se necessario
                )
          
                if new_user_id:
                    print(f"Registrazione per l'utente '{username_reg}' completata con successo!")
                    print("Ora puoi effettuare il login.")
                    # Non fa login automatico, torna al menu di autenticazione
                else:
                    # register_user_service dovrebbe sollevare ValueError se l'utente esiste già
                    # o restituire None per altri fallimenti non eccezionali.
                    print("Registrazione fallita. Controlla i log o riprova.")
            except ValueError as ve: # Es. utente già esistente
                print(f"ERRORE REGISTRAZIONE: {ve}")
            except Exception as e:
                logger.error(f"Errore critico durante la registrazione: {e}", exc_info=True)
                print(f"Si è verificato un errore imprevisto durante la registrazione: {e}")

        elif auth_choice == '0':
            print("Uscita dall'applicazione.")
            return False # Esce
        else:
            print("Scelta non valida.")
            login_attempts +=1 # Considera scelta non valida come tentativo

    return False # Se esce dal loop senza successo

def main():
    """Funzione principale dell'applicazione."""
    global logger, logged_in_user_id, current_session_id, client_ip_address

    # 1. Setup Logging (una sola volta)
    # I nomi dei logger devono corrispondere a quelli usati nei moduli
    logger = setup_logging(app_logger_name="CatastoAppLogger", db_logger_name="CatastoDBLogger")
    logger.info("Avvio Applicazione Catasto Storico...")

    # 2. Carica Configurazione DB
    try:
        db_params = load_db_config()
    except (FileNotFoundError, ValueError) as e_conf:
        logger.critical(f"Errore caricamento configurazione database: {e_conf}. Impossibile avviare.")
        print(f"ERRORE CRITICO CONFIGURAZIONE: {e_conf}")
        sys.exit(1)

    # 3. Inizializza DatabaseManager
    db = DatabaseManager(db_params)

    # 4. Connessione al Database
    if not db.connect():
        logger.critical("Fallimento connessione al database all'avvio. L'applicazione terminerà.")
        print("ERRORE CRITICO: Impossibile connettersi al database. Verifica i parametri e lo stato del server.")
        sys.exit(1)
    
    stampa_locandina_introduzione()

    # 5. Autenticazione Utente
    if not authenticate_user(db):
        logger.info("Autenticazione fallita o utente ha scelto di uscire. Chiusura applicazione.")
        db.disconnect()
        sys.exit(0)

    # 6. Esegui Menu Principale (solo se autenticato)
    try:
        menu_principale(db, logged_in_user_id, current_user_role_id, current_session_id, client_ip_address)
    except KeyboardInterrupt:
        logger.info("Operazione interrotta dall'utente (Ctrl+C) nel menu principale.")
        print("\nOperazione interrotta.")
    except Exception as e_main:
        logger.exception(f"Errore non gestito nel ciclo principale dell'applicazione: {e_main}")
        print(f"ERRORE IMPREVISTO: {e_main}. L'applicazione potrebbe dover terminare.")
    finally:
        # 7. Logout e Disconnessione
        if logged_in_user_id and current_session_id and db.conn and not db.conn.closed:
             logger.info(f"Esecuzione logout per utente ID {logged_in_user_id}, sessione {current_session_id}...")
             try:
                 utenti_service.logout_user_service(db, logged_in_user_id, current_session_id, client_ip_address)
             except Exception as e_logout:
                 logger.error(f"Errore durante il logout automatico: {e_logout}", exc_info=True)
        
        logger.info("Chiusura connessione al database...")
        db.disconnect()
        logger.info("Applicazione Catasto Storico terminata.")
        print("\nGrazie per aver utilizzato il Gestionale Catasto Storico. Arrivederci!")

if __name__ == "__main__":
    main()