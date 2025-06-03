import sys
print(f"Percorso sys.executable: {sys.executable}")
print(f"Percorsi sys.path: {sys.path}")

pyqt5_version = "N/D"
qt_version_pyqt = "N/D"
pyqt5_import_path = "N/D"
qstandardpaths_class_exists = False
qstandardpaths_libraries_location_exists = False
qtsvgwidgets_imported_ok = False
qtsvgwidgets_import_path = "N/D"
qtgui_import_path = "N/D"
qtcore_import_path = "N/D"
qtwidgets_import_path = "N/D"

print("\n--- Test Importazione Moduli PyQt5 ---")
try:
    import PyQt5
    from PyQt5.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
    pyqt5_version = PYQT_VERSION_STR
    qt_version_pyqt = QT_VERSION_STR
    pyqt5_import_path = PyQt5.__file__
    print(f"PyQt5 versione: {pyqt5_version}")
    print(f"Qt versione compilata con PyQt5: {qt_version_pyqt}")
    print(f"PyQt5 è stato importato da: {pyqt5_import_path}")

    try:
        from PyQt5 import QtCore
        qtcore_import_path = QtCore.__file__
        print(f"SUCCESS: PyQt5.QtCore importato da: {qtcore_import_path}")
        try:
            from PyQt5.QtCore import QStandardPaths
            qstandardpaths_class_exists = True
            print("SUCCESS: Classe QStandardPaths importata.")
            if hasattr(QStandardPaths, 'LibrariesLocation'):
                qstandardpaths_libraries_location_exists = True
                print("SUCCESS: QStandardPaths.LibrariesLocation ESISTE.")
            else:
                print("ERRORE: Attributo 'LibrariesLocation' NON TROVATO in QStandardPaths.")
        except ImportError:
            print("ERRORE: Impossibile importare QStandardPaths da PyQt5.QtCore.")
        except Exception as e_qsp:
            print(f"ERRORE durante il test di QStandardPaths: {e_qsp}")
    except ImportError:
        print("ERRORE CRITICO: Impossibile importare PyQt5.QtCore.")
        
    try:
        from PyQt5 import QtGui
        qtgui_import_path = QtGui.__file__
        print(f"SUCCESS: PyQt5.QtGui importato da: {qtgui_import_path}")
    except ImportError:
        print("ERRORE CRITICO: Impossibile importare PyQt5.QtGui.")

    try:
        from PyQt5 import QtWidgets
        qtwidgets_import_path = QtWidgets.__file__
        print(f"SUCCESS: PyQt5.QtWidgets importato da: {qtwidgets_import_path}")
    except ImportError:
        print("ERRORE CRITICO: Impossibile importare PyQt5.QtWidgets.")
        
    try:
        from PyQt5 import QtSvgWidgets # Tentiamo l'import qui
        qtsvgwidgets_imported_ok = True
        qtsvgwidgets_import_path = QtSvgWidgets.__file__
        print(f"SUCCESS: PyQt5.QtSvgWidgets importato da: {qtsvgwidgets_import_path}")
    except ImportError:
        print("ERRORE: Impossibile importare PyQt5.QtSvgWidgets.")
    except Exception as e_qtsvg:
        print(f"ERRORE sconosciuto durante l'importazione di QtSvgWidgets: {e_qtsvg}")

except ImportError:
    print("ERRORE CRITICO: Impossibile importare il modulo base PyQt5.")
except Exception as e_gen:
    print(f"Errore generale durante i test di importazione PyQt5: {e_gen}")

print("\n--- Riepilogo Diagnostica Finale ---")
print(f"- Python Executable: {sys.executable}")
print(f"- PyQt5 importato: {'Sì' if pyqt5_version != 'N/D' else 'No'}")
if pyqt5_version != "N/D":
    print(f"  - Versione PyQt5: {pyqt5_version}")
    print(f"  - Versione Qt: {qt_version_pyqt}")
    print(f"  - Percorso PyQt5: {pyqt5_import_path}")
    print(f"  - QtCore importato da: {qtcore_import_path}")
    print(f"  - QtGui importato da: {qtgui_import_path}")
    print(f"  - QtWidgets importato da: {qtwidgets_import_path}")
print(f"- Classe QStandardPaths importata: {qstandardpaths_class_exists}")
print(f"- QStandardPaths.LibrariesLocation esiste: {qstandardpaths_libraries_location_exists}")
print(f"- QtSvgWidgets importato: {qtsvgwidgets_imported_ok}")
if qtsvgwidgets_imported_ok:
    print(f"  - Percorso QtSvgWidgets: {qtsvgwidgets_import_path}")