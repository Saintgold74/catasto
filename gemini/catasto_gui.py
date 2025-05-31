#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionale Catasto Storico - Interfaccia Grafica
================================================
Applicazione GUI per la gestione del catasto storico.

Autore: Marco Santoro
Data: 31/05/2025
Versione: 1.0 (modularizzata)
"""

import sys
import os
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

# Importazioni PyQt5
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget,
                            QVBoxLayout, QHBoxLayout, QLabel, QMessageBox,
                            QStyleFactory, QSplashScreen, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, QSettings, QSize
from PyQt5.QtGui import QPixmap, QIcon, QFont

# Debug print per tracciare le importazioni
print("Inizializzazione imports...")

# Importa i moduli personalizzati
try:
    print("Importando utils...")
    from utils import (gui_logger, set_qsettings_defaults, CSS_STYLE, 
                    QDate_to_datetime, datetime_to_QDate, CatastoDBError)
    print("Import utils completato")
    
    print("Importando ui_components...")
    from ui_components import (LoginDialog, CreateUserDialog, ComuneSelectionDialog,
                            QPasswordLineEdit, ImmobiliTableWidget)
    print("Import ui_components completato")
    
    print("Importando pdf_export...")
    from pdf_export import (PDFPartita, PDFPossessore, GenericTextReportPDF,
                        gui_esporta_partita_json as esporta_partita_json, 
                        gui_esporta_partita_csv as esporta_partita_csv, 
                        gui_esporta_partita_pdf as esporta_partita_pdf,
                        gui_esporta_possessore_json as esporta_possessore_json, 
                        gui_esporta_possessore_csv as esporta_possessore_csv, 
                        gui_esporta_possessore_pdf as esporta_possessore_pdf)
    print("Import pdf_export completato")
    
    print("Importando search_widgets...")
    from search_widgets import RicercaPartiteWidget, RicercaPossessoriWidget
    print("Import search_widgets completato")
except Exception as e:
    print(f"Errore durante l'importazione: {e}")
    print(f"Tipo di errore: {type(e).__name__}")
    import traceback
    traceback.print_exc()

# Importa il database manager
try:
    from catasto_db_manager import CatastoDBManager
except ImportError:
    gui_logger.error("Impossibile importare CatastoDBManager. Verificare l'installazione.")
    QMessageBox.critical(None, "Errore Critico", 
                        "Impossibile importare il modulo CatastoDBManager.\n"
                        "L'applicazione verrà chiusa.")
    sys.exit(1)


class EsportazioniWidget(QWidget):
    """Widget per le funzionalità di esportazione dati."""
    def __init__(self, db_manager, parent=None):
        super(EsportazioniWidget, self).__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()
        
    def setup_ui(self):
        """Configura l'interfaccia utente del widget."""
        layout = QVBoxLayout()
        
        # Gruppo Esportazione Partite
        partite_layout = QVBoxLayout()
        partite_label = QLabel("<h3>Esportazione Partite</h3>")
        partite_layout.addWidget(partite_label)
        
        # Layout per ID partita
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("ID Partita:"))
        
        from PyQt5.QtWidgets import QSpinBox
        self.partita_id_spinner = QSpinBox()
        self.partita_id_spinner.setMinimum(1)
        self.partita_id_spinner.setMaximum(999999)
        id_layout.addWidget(self.partita_id_spinner)
        
        id_layout.addStretch()
        partite_layout.addLayout(id_layout)
        
        # Pulsanti esportazione partite
        buttons_layout = QHBoxLayout()
        
        from PyQt5.QtWidgets import QPushButton
        self.btn_export_partita_json = QPushButton("Esporta in JSON")
        self.btn_export_partita_json.clicked.connect(self.handle_export_partita_json)
        buttons_layout.addWidget(self.btn_export_partita_json)
        
        self.btn_export_partita_csv = QPushButton("Esporta in CSV")
        self.btn_export_partita_csv.clicked.connect(self.handle_export_partita_csv)
        buttons_layout.addWidget(self.btn_export_partita_csv)
        
        self.btn_export_partita_pdf = QPushButton("Esporta in PDF")
        self.btn_export_partita_pdf.clicked.connect(self.handle_export_partita_pdf)
        buttons_layout.addWidget(self.btn_export_partita_pdf)
        
        partite_layout.addLayout(buttons_layout)
        layout.addLayout(partite_layout)
        
        # Separatore
        from PyQt5.QtWidgets import QFrame
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # Gruppo Esportazione Possessori
        possessori_layout = QVBoxLayout()
        possessori_label = QLabel("<h3>Esportazione Possessori</h3>")
        possessori_layout.addWidget(possessori_label)
        
        # Layout per ID possessore
        id_poss_layout = QHBoxLayout()
        id_poss_layout.addWidget(QLabel("ID Possessore:"))
        
        self.possessore_id_spinner = QSpinBox()
        self.possessore_id_spinner.setMinimum(1)
        self.possessore_id_spinner.setMaximum(999999)
        id_poss_layout.addWidget(self.possessore_id_spinner)
        
        id_poss_layout.addStretch()
        possessori_layout.addLayout(id_poss_layout)
        
        # Pulsanti esportazione possessori
        poss_buttons_layout = QHBoxLayout()
        
        self.btn_export_possessore_json = QPushButton("Esporta in JSON")
        self.btn_export_possessore_json.clicked.connect(self.handle_export_possessore_json)
        poss_buttons_layout.addWidget(self.btn_export_possessore_json)
        
        self.btn_export_possessore_csv = QPushButton("Esporta in CSV")
        self.btn_export_possessore_csv.clicked.connect(self.handle_export_possessore_csv)
        poss_buttons_layout.addWidget(self.btn_export_possessore_csv)
        
        self.btn_export_possessore_pdf = QPushButton("Esporta in PDF")
        self.btn_export_possessore_pdf.clicked.connect(self.handle_export_possessore_pdf)
        poss_buttons_layout.addWidget(self.btn_export_possessore_pdf)
        
        possessori_layout.addLayout(poss_buttons_layout)
        layout.addLayout(possessori_layout)
        
        # Aggiungi spazio vuoto in fondo
        layout.addStretch()
        
        self.setLayout(layout)
    
    def handle_export_partita_json(self):
        """Gestisce l'esportazione della partita in formato JSON."""
        partita_id = self.partita_id_spinner.value()
        esporta_partita_json(self.db_manager, partita_id, self)
    
    def handle_export_partita_csv(self):
        """Gestisce l'esportazione della partita in formato CSV."""
        partita_id = self.partita_id_spinner.value()
        esporta_partita_csv(self.db_manager, partita_id, self)
    
    def handle_export_partita_pdf(self):
        """Gestisce l'esportazione della partita in formato PDF."""
        partita_id = self.partita_id_spinner.value()
        esporta_partita_pdf(self.db_manager, partita_id, self)
    
    def handle_export_possessore_json(self):
        """Gestisce l'esportazione del possessore in formato JSON."""
        possessore_id = self.possessore_id_spinner.value()
        esporta_possessore_json(self.db_manager, possessore_id, self)
    
    def handle_export_possessore_csv(self):
        """Gestisce l'esportazione del possessore in formato CSV."""
        possessore_id = self.possessore_id_spinner.value()
        esporta_possessore_csv(self.db_manager, possessore_id, self)
    
    def handle_export_possessore_pdf(self):
        """Gestisce l'esportazione del possessore in formato PDF."""
        possessore_id = self.possessore_id_spinner.value()
        esporta_possessore_pdf(self.db_manager, possessore_id, self)


class MainWindow(QMainWindow):
    """Finestra principale dell'applicazione."""
    def __init__(self):
        super(MainWindow, self).__init__()
        
        # Imposta titolo e dimensioni finestra
        self.setWindowTitle("Gestionale Catasto Storico - v1.0")
        self.resize(1200, 800)
        
        # Inizializza le impostazioni
        self.settings = QSettings("CatastoStorico", "GestionaleCatasto")
        set_qsettings_defaults(self.settings)
        
        # Inizializza il gestore del database
        try:
            self.db_manager = CatastoDBManager()
            self.db_manager.connect()
        except Exception as e:
            gui_logger.error(f"Errore durante la connessione al database: {e}")
            QMessageBox.critical(self, "Errore di Connessione", 
                                f"Impossibile connettersi al database:\n{str(e)}")
            sys.exit(1)
        
        # Applica stile CSS
        self.setStyleSheet(CSS_STYLE)
        
        # Login all'avvio
        self.show_login_dialog()
    
    def show_login_dialog(self):
        """Mostra il dialogo di login."""
        login_dialog = LoginDialog(self.db_manager, self)
        result = login_dialog.exec_()
        
        if result == LoginDialog.Accepted:
            gui_logger.info(f"Login effettuato: {self.db_manager.current_user_info['username']}")
            self.setup_main_ui()
        else:
            gui_logger.info("Login annullato, chiusura applicazione")
            sys.exit(0)
    
    def setup_main_ui(self):
        """Configura l'interfaccia utente principale dopo il login."""
        # Widget centrale
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Info utente
        user_info_layout = QHBoxLayout()
        username = self.db_manager.current_user_info.get('username', 'Utente')
        user_role = self.db_manager.current_user_info.get('ruolo', 'Ruolo non definito')
        user_label = QLabel(f"<b>Utente:</b> {username} ({user_role})")
        user_info_layout.addWidget(user_label)
        
        user_info_layout.addStretch()
        
        logout_button = QPushButton("Logout")
        logout_button.clicked.connect(self.handle_logout)
        user_info_layout.addWidget(logout_button)
        
        main_layout.addLayout(user_info_layout)
        
        # Tab Widget per le diverse funzionalità
        tab_widget = QTabWidget()
        
        # Tab Ricerca Partite
        ricerca_partite_widget = RicercaPartiteWidget(self.db_manager)
        tab_widget.addTab(ricerca_partite_widget, "Ricerca Partite")
        
        # Tab Ricerca Possessori
        ricerca_possessori_widget = RicercaPossessoriWidget(self.db_manager)
        tab_widget.addTab(ricerca_possessori_widget, "Ricerca Possessori")
        
        # Tab Esportazioni
        esportazioni_widget = EsportazioniWidget(self.db_manager)
        tab_widget.addTab(esportazioni_widget, "Esportazioni")
        
        main_layout.addWidget(tab_widget)
        
        self.setCentralWidget(central_widget)
        
        # Barra di stato
        self.statusBar().showMessage(f"Connesso al database - {self.db_manager.get_db_version()}")
    
    def handle_logout(self):
        """Gestisce il logout dell'utente."""
        if QMessageBox.question(self, "Conferma Logout", 
                               "Sei sicuro di voler effettuare il logout?",
                               QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            gui_logger.info(f"Logout utente: {self.db_manager.current_user_info['username']}")
            self.db_manager.logout()
            QMessageBox.information(self, "Logout", "Logout effettuato con successo.")
            self.close()
    
    def closeEvent(self, event):
        """Gestisce l'evento di chiusura della finestra."""
        try:
            if hasattr(self, 'db_manager') and self.db_manager:
                self.db_manager.close()
            gui_logger.info("Applicazione chiusa correttamente")
        except Exception as e:
            gui_logger.error(f"Errore durante la chiusura dell'applicazione: {e}")
        event.accept()


def main():
    """Funzione principale dell'applicazione."""
    print("Avvio funzione main()")
    try:
        app = QApplication(sys.argv)
        app.setStyle(QStyleFactory.create('Fusion'))
        print("App QApplication creata")
        
        # Carica e mostra la schermata di avvio
        print("Tentativo di caricare lo splash screen...")
        try:
            splash_pixmap = QPixmap("splash.png")
            print(f"Splash screen caricato: {not splash_pixmap.isNull()}")
            if not splash_pixmap.isNull():
                splash = QSplashScreen(splash_pixmap)
                splash.show()
                app.processEvents()
                print("Splash screen mostrato")
            else:
                print("File splash.png non trovato o non valido")
                splash = None
        except Exception as e:
            print(f"Errore durante il caricamento dello splash screen: {e}")
            splash = None
        
        # Piccolo ritardo per mostrare lo splash screen
        print("Programmazione avvio applicazione principale...")
        QTimer.singleShot(1500, lambda: start_app(app, splash))
        print("Avvio del loop principale dell'applicazione...")
        
        return app.exec_()
    except Exception as e:
        print(f"Errore catastrofico in main(): {e}")
        print(f"Tipo di errore: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return 1


def start_app(app, splash=None):
    """Avvia l'applicazione principale dopo lo splash screen."""
    print("Avvio funzione start_app()")
    try:
        if splash:
            print("Chiusura splash screen")
            splash.close()
        
        print("Creazione istanza MainWindow...")
        main_window = MainWindow()
        print("MainWindow creata con successo")
        
        print("Visualizzazione MainWindow...")
        main_window.show()
        print("MainWindow visualizzata")
    except Exception as e:
        print(f"Errore in start_app(): {e}")
        print(f"Tipo di errore: {type(e).__name__}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
