# app_paths.py

import logging
import sys
import os
from pathlib import Path

def resource_path(relative_path):
    """
    Ottiene il percorso assoluto della risorsa, funziona sia in sviluppo che con PyInstaller.
    """
    try:
        # PyInstaller crea una cartella temporanea e ci mette il percorso in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        # In sviluppo, usiamo il percorso del file corrente
        base_path = Path(__file__).parent
    return base_path / relative_path

# --- DEFINIZIONE DEI PERCORSI PRINCIPALI ---

# Directory principale del progetto
BASE_DIR = Path(__file__).resolve().parent

# Directory per i log
LOGS_DIR = BASE_DIR / "logs"

# Directory per gli allegati
ALLEGATI_DIR = BASE_DIR / "allegati_catasto"

# Directory per le esportazioni
ESPORTAZIONI_DIR = BASE_DIR / "esportazioni"

# Directory delle risorse (icone, stili, etc.)
RESOURCES_DIR = BASE_DIR / "resources"

# Percorso del file di stile QSS di default
DEFAULT_STYLE_PATH = RESOURCES_DIR / "meridiana_style.qss"

# Assicurati che le directory principali esistano all'avvio del modulo
LOGS_DIR.mkdir(parents=True, exist_ok=True)
ESPORTAZIONI_DIR.mkdir(parents=True, exist_ok=True)
def get_base_path():
    """Ottiene il percorso base dell'applicazione."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    """Ottiene il percorso assoluto di una risorsa."""
    base_path = get_base_path()
    return os.path.join(base_path, relative_path)

# --- INIZIO FUNZIONI SPOSTATE ---

def get_available_styles() -> list:
    """Scansiona la sottocartella 'styles' e restituisce una lista dei file .qss trovati."""
    logger = logging.getLogger(__name__)
    try:
        # Usa resource_path per essere compatibile con l'eseguibile
        styles_dir = resource_path("styles")
        if os.path.exists(styles_dir):
            return [f for f in os.listdir(styles_dir) if f.endswith('.qss')]
        else:
            logger.warning(f"Cartella stili non trovata in: {styles_dir}")
            return []
    except Exception as e:
        logger.error(f"Errore nella scansione della cartella stili: {e}")
        return []

def load_stylesheet(filename: str) -> str:
    """Carica un file di stylesheet usando il percorso corretto."""
    logger = logging.getLogger(__name__)
    try:
        # La funzione resource_path costruisce già il percorso completo e corretto
        style_path = resource_path(os.path.join('styles', filename))
        logger.info(f"Tentativo di caricamento stylesheet da: {style_path}")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            logger.warning(f"File stylesheet non trovato al percorso: {style_path}")
            return ""
    except Exception as e:
        logger.error(f"Errore critico durante il caricamento dello stylesheet '{filename}': {e}", exc_info=True)
        return ""


# --- FUNZIONI DI SUPPORTO SPECIFICHE ---

def get_logo_path():
    """Ritorna il percorso del logo principale dell'applicazione."""
    return resource_path(os.path.join('resources', 'logo_meridiana.png'))

def get_style_file(style_name):
    """
    Ritorna il percorso di un file di stile specifico dalla cartella 'styles'.

    Args:
        style_name: Nome del file di stile (es. 'blu_savoia.qss')
    """
    return resource_path(os.path.join('styles', style_name))

