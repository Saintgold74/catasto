#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurazione dell'applicazione Catasto Storico
================================================
Questo modulo contiene le configurazioni dell'applicazione.
"""

import os
import json
import logging
import time
from datetime import datetime

# Configurazione di default del database
DEFAULT_DB_CONFIG = {
    "dbname": "catasto_storico",
    "user": "postgres",
    "password": "Markus74",
    "host": "localhost",
    "port": 5432,
    "schema": "catasto"
}

# Configurazione logging
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = "catasto_app.log"

def setup_logging(log_dir=None):
    """Configura il sistema di logging con supporto per directory personalizzate."""
    if log_dir is None:
        # Usa una directory standard, come la home dell'utente
        log_dir = os.path.join(os.path.expanduser("~"), ".catasto_app")
    
    # Crea la directory se non esiste
    os.makedirs(log_dir, exist_ok=True)
    
    log_path = os.path.join(log_dir, LOG_FILE)
    
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("CatastoApp")

# Funzioni per gestire il file di configurazione
def load_config(config_file="config.json"):
    """Carica la configurazione da file"""
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger = setup_logging()
            logger.error(f"Errore nel caricamento della configurazione: {e}")
    return {"database": DEFAULT_DB_CONFIG}

def save_config(config, config_file="config.json"):
    """Salva la configurazione su file"""
    try:
        # Crea la directory se non esiste
        config_dir = os.path.dirname(os.path.abspath(config_file))
        os.makedirs(config_dir, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logger = setup_logging()
        logger.error(f"Errore nel salvataggio della configurazione: {e}")
        return False

# Dizionario per i tipi di variazione e contratti
TIPI_VARIAZIONE = ["Acquisto", "Successione", "Variazione", "Frazionamento", "Divisione"]
TIPI_CONTRATTO = ["Vendita", "Divisione", "Successione", "Donazione"]
TIPI_LOCALITA = ["regione", "via", "borgata"]
TIPI_PARTITA = ["principale", "secondaria"]
TIPI_UTENTE = ["admin", "archivista", "consultatore"]

# Formati date
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

def format_date(date_obj):
    """Formatta un oggetto data"""
    if date_obj:
        return date_obj.strftime(DATE_FORMAT)
    return ""

def format_datetime(datetime_obj):
    """Formatta un oggetto datetime"""
    if datetime_obj:
        return datetime_obj.strftime(DATETIME_FORMAT)
    return ""

def parse_date(date_str):
    """Converte una stringa in un oggetto date"""
    if date_str:
        try:
            return datetime.strptime(date_str, DATE_FORMAT).date()
        except ValueError:
            pass
    return None

# Versione dell'applicazione
APP_VERSION = "1.0.0"
APP_NAME = "Gestione Catasto Storico"
APP_DESCRIPTION = "Applicazione per la gestione del catasto storico italiano degli anni '50"

# Directory di backup predefinita
DEFAULT_BACKUP_DIR = os.path.join(os.path.expanduser("~"), ".catasto_app", "backups")
os.makedirs(DEFAULT_BACKUP_DIR, exist_ok=True)