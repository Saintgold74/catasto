# utils/config_loader.py
import configparser
import os
import logging

# Ottieni un logger specifico per questo modulo, che sarà configurato da setup_logging
logger = logging.getLogger("CatastoAppLogger.ConfigLoader")

def load_db_config(file_path="config.ini"):
    """
    Carica la configurazione del database dal file specificato.
    """
    if not os.path.exists(file_path):
        logger.error(f"File di configurazione '{file_path}' non trovato.")
        raise FileNotFoundError(f"File di configurazione '{file_path}' non trovato.")
    
    parser = configparser.ConfigParser()
    parser.read(file_path)
    
    if 'database' not in parser:
        logger.error("Sezione [database] mancante nel file di configurazione.")
        raise ValueError("Sezione [database] mancante nel file di configurazione.")
    
    try:
        db_params = dict(parser['database'])
        if 'port' in db_params: # Converti la porta in intero
            db_params['port'] = int(db_params['port'])
        logger.info(f"Configurazione database caricata da '{file_path}'.")
        return db_params
    except Exception as e:
        logger.error(f"Errore durante il parsing dei parametri del database: {e}")
        raise