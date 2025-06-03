import sys
print(f"Percorso sys.executable: {sys.executable}")
print(f"Percorsi sys.path: {sys.path}")
try:
    import PyQt5
    from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, QStandardPaths
    print(f"PyQt5 versione: {PYQT_VERSION_STR}")
    print(f"Qt versione compilata con PyQt5: {QT_VERSION_STR}")
    print(f"PyQt5 è stato importato da: {PyQt5.__file__}")

    # Verifica percorsi librerie Qt (potrebbe dare un'idea)
    library_paths = QStandardPaths.standardLocations(QStandardPaths.LibrariesLocation)
    print(f"Percorsi Librerie Qt Standard: {library_paths}")

    # Tentativo di importare QtSvgWidgets di nuovo
    from PyQt5 import QtSvgWidgets
    print("SUCCESS: PyQt5.QtSvgWidgets importato correttamente!")
    print(f"QtSvgWidgets importato da: {QtSvgWidgets.__file__}")

except ImportError as e:
    print(f"ERRORE durante l'importazione di PyQt5 o QtSvgWidgets: {e}")
except Exception as e_gen:
    print(f"Altro errore: {e_gen}")