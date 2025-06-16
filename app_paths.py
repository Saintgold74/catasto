import os
import sys

def get_base_path():
    """
    Ottiene il percorso base dell'applicazione.
    Funziona sia per lo sviluppo che per l'eseguibile PyInstaller.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Siamo in un eseguibile PyInstaller
        return sys._MEIPASS
    else:
        # Siamo in ambiente di sviluppo
        # Usiamo __file__ che è l'approccio standard in sviluppo
        return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    """
    Ottiene il percorso assoluto di una risorsa partendo dal percorso base.
    """
    base_path = get_base_path()
    return os.path.join(base_path, relative_path)

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

# Potresti aggiungere altre funzioni simili se necessario
# Esempio:
# def get_manual_path():
#     return resource_path(os.path.join('resources', 'manuale_utente.pdf'))
