# config.py

import logging
from logging.handlers import RotatingFileHandler

# Ora questo import è sicuro, perché app_paths è autonomo
from app_paths import LOGS_DIR 

# --- Nomi per le chiavi di QSettings (definisci globalmente o prima di run_gui_app) ---
SETTINGS_DB_TYPE = "Database/Type"
SETTINGS_DB_HOST = "Database/Host"
SETTINGS_DB_PORT = "Database/Port"
SETTINGS_DB_NAME = "Database/DBName"
SETTINGS_DB_USER = "Database/User"
SETTINGS_DB_SCHEMA = "Database/Schema"
# Non salviamo la password in QSettings
# Non usato, ma definito per completezza
SETTINGS_DB_PASSWORD = "Database/Password"

COLONNE_POSSESSORI_DETTAGLI_NUM = 6
COLONNE_POSSESSORI_DETTAGLI_LABELS = [
    "ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]
# Costanti per la configurazione delle tabelle dei possessori, se usate in più punti
# Scegli nomi specifici se diverse tabelle hanno diverse configurazioni
# Esempio: ID, Nome Compl, Paternità, Comune, Num. Partite
COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM = 5
COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS = [
    "ID", "Nome Completo", "Paternità", "Comune Rif.", "Num. Partite"]

# Per InserimentoPossessoreWidget, se la sua tabella è diversa:
# Esempio: ID, Nome Completo, Paternità, Comune
COLONNE_INSERIMENTO_POSSESSORI_NUM = 4
COLONNE_INSERIMENTO_POSSESSORI_LABELS = [
    "ID", "Nome Completo", "Paternità", "Comune Riferimento"]

NUOVE_ETICHETTE_POSSESSORI = ["id", "nome_completo", "codice_fiscale", "data_nascita", "cognome_nome",
                              "paternita", "indirizzo_residenza", "comune_residenza_nome", "attivo", "note", "num_partite"]


# --- MODALITÀ DI SVILUPPO ---
DEVELOPMENT_MODE = True

# --- CONFIGURAZIONE CENTRALIZZATA DEL LOGGER ---
def setup_global_logging():
    """Configura e restituisce il logger principale dell'applicazione."""
    log_file = LOGS_DIR / "meridiana_app.log"
    
    logger = logging.getLogger("MeridianaAppLogger")
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_global_logging()


def setup_global_logging():
    """Configura e restituisce il logger principale dell'applicazione."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "meridiana_app.log"
    
    logger = logging.getLogger("MeridianaAppLogger")
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Crea l'istanza del logger che verrà importata da tutti gli altri moduli.
# Il nome 'logger' è più standard e breve.
logger = setup_global_logging()