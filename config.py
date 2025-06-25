# config.py

import logging,os
from logging.handlers import RotatingFileHandler

# Ora questo import è sicuro, perché app_paths è autonomo
from app_paths import LOG_DIR, get_log_file_path

from PyQt5.QtCore import QStandardPaths, QCoreApplication

from logging.handlers import RotatingFileHandler

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

def setup_global_logging(log_level=logging.INFO):
    """
    Configura il logging globale per l'applicazione, salvando i file
    in una cartella dati utente scrivibile.
    """
    try:
        # Ottiene il percorso standard per i dati dell'applicazione locale.
        # Es: C:/Users/NOME_UTENTE/AppData/Local/Marco Santoro/Meridiana/logs
        log_directory = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
        
        # Se il percorso non esiste, QStandardPaths può restituire una stringa vuota.
        # In quel caso, usiamo un percorso di fallback (anche se raro).
        if not log_directory:
            log_directory = os.path.join(os.path.expanduser("~"), "MeridianaAppData")

        # Aggiungiamo una sottocartella 'logs'
        log_directory = os.path.join(log_directory, "logs")

        # Crea la cartella di log se non esiste
        os.makedirs(log_directory, exist_ok=True)

        log_file_path = os.path.join(log_directory, "meridiana_gui.log")

        # Configurazione del logger 'CatastoGUI'
        logger = logging.getLogger("CatastoGUI")
        logger.setLevel(log_level)
        logger.handlers.clear()

        # Formattatore
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )

        # Handler per file con rotazione
        handler_file = RotatingFileHandler(
            log_file_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
        )
        handler_file.setFormatter(formatter)
        logger.addHandler(handler_file)

        # Handler per console (per debug)
        handler_console = logging.StreamHandler()
        handler_console.setFormatter(formatter)
        logger.addHandler(handler_console)

        logger.info(f"Logging configurato. File di log in: {log_file_path}")

    except Exception as e:
        print(f"ERRORE CRITICO durante la configurazione del logging: {e}")
        # Configurazione di un logger di fallback basico in caso di errore
        logging.basicConfig(level=logging.WARNING)
        logging.warning("Utilizzo configurazione di logging di fallback.")