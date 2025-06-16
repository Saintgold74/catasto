import os
import sys

def get_base_path():
    """Ottiene il percorso base dell'applicazione, funzionante sia in sviluppo che come eseguibile PyInstaller."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # In un eseguibile PyInstaller
        return sys._MEIPASS
    else:
        # In ambiente di sviluppo
        return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    """Ottiene il percorso assoluto di una risorsa."""
    base_path = get_base_path()
    return os.path.join(base_path, relative_path)

def get_style_file(style_name):
    """Ritorna il percorso di un file di stile specifico."""
    return resource_path(os.path.join('styles', style_name))

# Aggiungi altre funzioni se necessario per altre risorse...