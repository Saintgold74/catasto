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
import socket
import logging
import signal # Per gestire Ctrl+C
from getpass import getpass
from typing import Optional

# Import per setup logging e caricamento configurazione
from utils.logger_setup import setup_logging
from utils.config_loader import load_db_config

# Import per SQLAlchemy (NUOVO)
from core.db_manager import SessionLocal, create_all_tables # Aggiunto SessionLocal e create_all_tables
from sqlalchemy.orm import Session # Per type hinting

# Import per il DatabaseManager legacy (RINOMINATO per chiarezza)
# from core.db_manager import DatabaseManager as LegacyDatabaseManager 

# Servizi (utenti_service ora si aspetta una sessione SQLAlchemy)
from core.services import utenti_service 

# Import per setup logging e caricamento configurazione
from utils.logger_setup import setup_logging
from utils.config_loader import load_db_config

# Import per SQLAlchemy
from core.db_manager import SessionLocal, create_all_tables 
from sqlalchemy.orm import Session 

# Servizi
from core.services import utenti_service 

# UI e gestione menu
from ui.console.menu_handler import menu_principale 
from ui.console.ui_utils import (
    stampa_titolo,          # NUOVA (da ui_utils modificato)
    stampa_errore,          # NUOVA (da ui_utils modificato)
    stampa_messaggio,       # NUOVA (da ui_utils modificato)
    stampa_avviso,          # NUOVA (da ui_utils modificato)
    stampa_locandina_introduzione,
    input_valore,           # ESISTENTE (uso più esteso)
    input_sicuro_password,  # ESISTENTE
    chiedi_conferma         # ESISTENTE (per sostituire conferma_uscita)
)

try:
    import readline
except ImportError:
    try:
        # Prova a importare pyreadline3 come alternativa su Windows
        import pyreadline3 as readline 
        print("INFO: Modulo 'readline' non trovato. Utilizzo di 'pyreadline3' come alternativa.")
    except ImportError:
        # Se neanche pyreadline3 è disponibile, l'input funzionerà comunque
        # ma senza le feature avanzate di readline (history, editing avanzato).
        print("INFO: Né 'readline' né 'pyreadline3' trovati. Le funzionalità avanzate di input da console potrebbero non essere disponibili.")
        readline = None # Definisci readline come None per evitare errori se viene usato altrove senza controllo

# Variabili globali per lo stato dell'applicazione
logger: Optional[logging.Logger] = None
logged_in_user_id: Optional[int] = None
current_user_role_id: Optional[int] = None 
current_session_id: Optional[str] = None # Questo sarà l'UUID della sessione
client_ip_address: str = "127.0.0.1" # Default

def get_local_ip_address() -> str:
    """Tenta di ottenere l'indirizzo IP locale."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        try:
            s.connect(('8.8.8.8', 1)) 
            ip_address = s.getsockname()[0]
        except Exception:
            try:
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
            except socket.gaierror:
                ip_address = '127.0.0.1'
        finally:
            s.close()
        return ip_address
    except Exception:
        return "127.0.0.1"

# --- Funzione di Autenticazione (MODIFICATA per accettare sessione SQLAlchemy) ---
def authenticate_user(db_sqla_session: Session) -> bool: # db_sqla_session è di tipo Session
    """
    Gestisce il login o la registrazione dell'utente usando SQLAlchemy.
    """
    global logged_in_user_id, current_user_role_id, current_session_id, client_ip_address, logger

    client_ip_address = get_local_ip_address()
    logger.info(f"Indirizzo IP client rilevato/usato: {client_ip_address}")

    MAX_LOGIN_ATTEMPTS = 3
    login_attempts = 0
    self_registration_enabled = True # Abilita per default, potrebbe essere da config.ini

    while True:
        stampa_titolo("--- Autenticazione ---")
        print("1. Login")
        if self_registration_enabled:
            print("2. Registra nuovo utente (self-service)")
        print("0. Esci dall'applicazione")
        
        choice = input_valore("Scegli un'opzione:", tipo_atteso=str).strip()

        if choice == '1': # Login
            if login_attempts >= MAX_LOGIN_ATTEMPTS:
                stampa_errore("Troppi tentativi di login falliti. L'applicazione terminerà.")
                return False

            username = input_valore("Username:", tipo_atteso=str, obbligatorio=True).strip()
            if not username: continue
            password = getpass("Password: ")
            
            try:
                user_id, role_id, session_id_str, message = utenti_service.login_user_service(
                    db_sqla_session, username, password, client_ip_address
                )
                
                if user_id and role_id and session_id_str:
                    stampa_messaggio(f"Login riuscito: {message}")
                    logged_in_user_id = user_id
                    current_user_role_id = role_id
                    current_session_id = session_id_str
                    return True
                else:
                    stampa_errore(f"Login fallito: {message}")
                    login_attempts += 1
                    stampa_avviso(f"Tentativi di login rimasti: {MAX_LOGIN_ATTEMPTS - login_attempts}")
                    if login_attempts >= MAX_LOGIN_ATTEMPTS:
                        stampa_errore("Troppi tentativi di login falliti. L'applicazione terminerà.")
                        return False
            except Exception as e:
                logger.error(f"Errore durante il tentativo di login: {e}", exc_info=True)
                stampa_errore(f"Si è verificato un errore durante il login: {e}")
                login_attempts += 1 # Considera anche errore di sistema come tentativo per non bloccare l'utente in un loop
                stampa_avviso(f"Tentativi di login rimasti: {MAX_LOGIN_ATTEMPTS - login_attempts}")


        elif choice == '2' and self_registration_enabled: # Registrazione Utente
            stampa_titolo("--- Registrazione Nuovo Utente ---")
            new_username = input_valore("Scegli un Username:", tipo_atteso=str, obbligatorio=True).strip()
            if not new_username: continue
            new_password = getpass("Scegli una Password: ")
            if not new_password:
                stampa_avviso("La password non può essere vuota.")
                continue
            confirm_password = getpass("Conferma Password: ")
            if new_password != confirm_password:
                stampa_errore("Le password non coincidono.")
                continue
            new_email = input_valore("Inserisci la tua Email:", tipo_atteso=str, obbligatorio=True).strip()
            if not new_email: continue # Semplice controllo, una validazione email più robusta sarebbe meglio
            new_nome_completo = input_valore("Inserisci il tuo Nome Completo:", tipo_atteso=str, obbligatorio=True).strip()
            if not new_nome_completo: continue
            
            DEFAULT_SELF_REG_ROLE_ID = 3 # ID Ruolo 'utente_base', da rendere configurabile

            try:
                # Assumiamo che register_user_service sia stato migrato ad SQLAlchemy
                registered_user_id = utenti_service.register_user_service(
                    db=db_sqla_session, 
                    username=new_username,
                    plain_password=new_password,
                    email=new_email,
                    role_id=DEFAULT_SELF_REG_ROLE_ID, 
                    nome_completo=new_nome_completo,
                    client_ip_address=client_ip_address,
                    created_by_user_id=None 
                )
                if registered_user_id:
                    stampa_messaggio(f"Registrazione utente '{new_username}' avvenuta con successo! Ora puoi effettuare il login.")
                # Se register_user_service solleva eccezioni per fallimenti, non ci sarà un 'else' qui.
            except ValueError as ve: 
                stampa_errore(f"Errore di registrazione: {ve}")
            except Exception as e_reg:
                logger.error(f"Errore durante la registrazione self-service: {e_reg}", exc_info=True)
                stampa_errore(f"Si è verificato un errore imprevisto durante la registrazione: {e_reg}")

        elif choice == '0': 
            return False
        else:
            stampa_errore("Scelta non valida. Riprova.")

# --- Funzione Principale ---
def main():
    global logger, logged_in_user_id, current_session_id, client_ip_address, current_user_role_id

    logger = setup_logging(app_logger_name="CatastoAppLogger", db_logger_name="CatastoDBLogger")
    logger.info("Avvio Applicazione Catasto Storico...")

    try:
        db_params_config = load_db_config() 
    except (FileNotFoundError, ValueError) as e_conf:
        logger.critical(f"Errore caricamento configurazione database: {e_conf}. Impossibile avviare.")
        print(f"ERRORE CRITICO CONFIGURAZIONE: {e_conf}")
        sys.exit(1)

    # --- GESTIONE DATABASE SQLAlchemy ---
    db_sqla_session: Optional[Session] = None # Type hint corretto
    try:
        # Commentare create_all_tables() in produzione o se si usa Alembic.
        # Utile per la prima configurazione/sviluppo per creare le tabelle definite nei modelli.
        # create_all_tables() 
        
        db_sqla_session = SessionLocal() 
        logger.info("Sessione SQLAlchemy creata e pronta.")
    except Exception as e_sqla_init:
        logger.critical(f"Fallimento inizializzazione SQLAlchemy: {e_sqla_init}. L'applicazione terminerà.", exc_info=True)
        print(f"ERRORE CRITICO: Impossibile inizializzare SQLAlchemy. Dettagli: {e_sqla_init}")
        if db_sqla_session: db_sqla_session.close()
        sys.exit(1)
    
    # Il DatabaseManager Legacy non è più inizializzato qui,
    # a meno che non sia esplicitamente necessario per parti non migrate.
    # db_legacy_manager = None 

    # --- FLUSSO APPLICAZIONE ---
    stampa_locandina_introduzione()

    if not authenticate_user(db_sqla_session):
        logger.info("Autenticazione fallita o utente ha scelto di uscire. Chiusura applicazione.")
        if db_sqla_session: db_sqla_session.close()
        sys.exit(0)

    # Esegui Menu Principale (solo se autenticato)
    try:
        if logged_in_user_id and current_session_id:
             logger.info("Accesso al menu principale...")
             # menu_principale ora riceverà la sessione SQLAlchemy.
             # Assicurati che menu_handler.py e i servizi che chiama siano stati adattati
             # per usare la sessione SQLAlchemy.
             menu_principale(db_sqla_session, 
                             logged_in_user_id, 
                             current_user_role_id, 
                             current_session_id, 
                             client_ip_address)
        else:
            logger.error("Tentativo di accesso al menu principale senza autenticazione valida.")
            stampa_errore("Errore: Autenticazione non valida per accedere al menu.")

    except KeyboardInterrupt:
        logger.info("Operazione interrotta dall'utente (Ctrl+C) nel menu principale.")
        print("\nOperazione interrotta.")
    except Exception as e_main: # Cattura eccezioni più generiche dal menu principale
        logger.exception(f"Errore non gestito nel ciclo principale dell'applicazione: {e_main}")
        stampa_errore(f"ERRORE IMPREVISTO: {e_main}. L'applicazione potrebbe dover terminare.")
    finally:
        # Logout e Chiusura Sessione
        if logged_in_user_id and current_session_id and db_sqla_session:
             logger.info(f"Esecuzione logout per utente ID {logged_in_user_id}, sessione {current_session_id}...")
             try:
                 utenti_service.logout_user_service(db_sqla_session, logged_in_user_id, current_session_id, client_ip_address)
             except Exception as e_logout:
                 logger.error(f"Errore durante il logout automatico (SQLAlchemy): {e_logout}", exc_info=True)
        
        if db_sqla_session:
            logger.info("Chiusura sessione SQLAlchemy...")
            db_sqla_session.close()
            
        logger.info("Applicazione Catasto Storico terminata.")
        print("\nGrazie per aver utilizzato il Gestionale Catasto Storico. Arrivederci!")

if __name__ == "__main__":
    # Gestione di SIGINT (Ctrl+C) per un'uscita più pulita
    def signal_handler(sig, frame):
        print('\nInterruzione rilevata (Ctrl+C). Chiusura pulita in corso (potrebbe richiedere un istante)...')
        # Non tentare di chiudere la sessione DB qui, potrebbe essere in uno stato inconsistente.
        # Il blocco finally in main() dovrebbe occuparsene se il flusso arriva fin lì.
        # L'uscita forzata qui è un fallback.
        sys.exit(0) 

    signal.signal(signal.SIGINT, signal_handler)
    main()