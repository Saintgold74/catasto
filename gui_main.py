#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaccia Grafica per Gestionale Catasto Storico
=================================================
Autore: Marco Santoro
Data: 18/05/2025
Versione: 1.2 (con integrazione menu esportazioni)
"""
import sys
import os
import logging
import uuid # Se usato per session_id in modalità offline
import getpass 
import json
import bcrypt
import csv # Aggiunto per esportazione CSV
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

# Importazioni PyQt5
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QLabel, QLineEdit,
                            QComboBox, QTabWidget, QTextEdit, QMessageBox,
                            QCheckBox, QGroupBox, QGridLayout, QTableWidget,
                            QTableWidgetItem, QDateEdit, QScrollArea,
                            QDialog, QListWidget,QMainWindow,QDateTimeEdit ,
                            QListWidgetItem, QFileDialog, QStyle, QStyleFactory, QSpinBox,
                            QInputDialog, QHeaderView,QFrame,QAbstractItemView,QSizePolicy,QAction, 
                            QMenu,QFormLayout,QDialogButtonBox,QProgressBar,QDoubleSpinBox) 
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QCloseEvent # Aggiunto QCloseEvent
from PyQt5.QtCore import Qt, QDate, QSettings, QDateTime,QProcess, QStandardPaths,pyqtSignal 
# In gui_main.py, dopo le importazioni PyQt e standard:
from catasto_db_manager import CatastoDBManager # E le sue eccezioni se servono qui

# Dai nuovi moduli che creeremo:
from gui_widgets import (
    ElencoComuniWidget, RicercaPartiteWidget, RicercaPossessoriWidget,
    RicercaAvanzataImmobiliWidget, InserimentoComuneWidget, InserimentoPossessoreWidget,
    InserimentoLocalitaWidget, RegistrazioneProprietaWidget, OperazioniPartitaWidget,
    EsportazioniWidget, ReportisticaWidget, StatisticheWidget, GestioneUtentiWidget,
    AuditLogViewerWidget, BackupRestoreWidget, AdminDBOperationsWidget,
    RegistraConsultazioneWidget # Assicurati che tutti i widget usati in setup_tabs siano qui
)
from app_utils import FPDF_AVAILABLE , QPasswordLineEdit,_verify_password, _hash_password


try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    # QMessageBox.warning(None, "Avviso Dipendenza", "La libreria FPDF non è installata. L'esportazione in PDF non sarà disponibile.")
    # Non mostrare il messaggio qui, ma gestire la disabilitazione dei pulsanti PDF.

# Importazione del gestore DB (il percorso potrebbe necessitare aggiustamenti)
try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    # Fallback o definizione locale se preferisci non importare direttamente
    # (ma l'importazione è più pulita se sono definite in db_manager)
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass
    QMessageBox.warning(None, "Avviso Importazione", 
                         "Eccezioni DB personalizzate non trovate in catasto_db_manager, usando definizioni fallback.")
# Importazione del gestore DB, con gestione dell'errore di importazione
try:
    from catasto_db_manager import CatastoDBManager
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    try:
        from catasto_db_manager import CatastoDBManager
    except ImportError:
        QMessageBox.critical(None, "Errore Importazione", 
                             "Non è possibile importare CatastoDBManager. "
                             "Assicurati che catasto_db_manager.py sia accessibile.")
        sys.exit(1)

# Importazioni dagli altri nuovi moduli (verranno create dopo)
# from gui_widgets import (ElencoComuniWidget, ...) # Esempio
# from app_utils import (FPDF_AVAILABLE, ...) # Esempio

# Costanti per le colonne delle tabelle, se usate in più punti

COLONNE_POSSESSORI_DETTAGLI_NUM = 6 # Esempio: ID, Nome Compl, Cognome/Nome, Paternità, Quota, Titolo
COLONNE_POSSESSORI_DETTAGLI_LABELS = ["ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]
# Costanti per la configurazione delle tabelle dei possessori, se usate in più punti
# Scegli nomi specifici se diverse tabelle hanno diverse configurazioni
COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM = 5 # Esempio: ID, Nome Compl, Paternità, Comune, Num. Partite
COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS = ["ID", "Nome Completo", "Paternità", "Comune Rif.", "Num. Partite"]

# Per InserimentoPossessoreWidget, se la sua tabella è diversa:
COLONNE_INSERIMENTO_POSSESSORI_NUM = 4 # Esempio: ID, Nome Completo, Paternità, Comune
COLONNE_INSERIMENTO_POSSESSORI_LABELS = ["ID", "Nome Completo", "Paternità", "Comune Riferimento"]

NUOVE_ETICHETTE_POSSESSORI = ["id", "nome_completo", "codice_fiscale", "data_nascita", "cognome_nome", "paternita", "indirizzo_residenza", "comune_residenza_nome", "attivo", "note", "num_partite"]
# Nomi per le chiavi di QSettings (globali o definite prima di run_gui_app)
# --- Nomi per le chiavi di QSettings (definisci globalmente o prima di run_gui_app) ---
SETTINGS_DB_TYPE = "Database/Type"
SETTINGS_DB_HOST = "Database/Host"
SETTINGS_DB_PORT = "Database/Port"
SETTINGS_DB_NAME = "Database/DBName"
SETTINGS_DB_USER = "Database/User"
SETTINGS_DB_SCHEMA = "Database/Schema"
# Non salviamo la password in QSettings
SETTINGS_DB_PASSWORD = "Database/Password"  # Non usato, ma definito per completezza
# --- Stylesheet Moderno (senza icone custom sui pulsanti principali) ---
MODERN_STYLESHEET = """
    * {
        font-family: Segoe UI, Arial, sans-serif; /* Font più moderno, fallback a sans-serif */
        font-size: 10pt;
        color: #333333; /* Testo scuro di default */
    }
    QMainWindow {
        background-color: #F4F4F4; /* Sfondo principale grigio molto chiaro */
    }
    QWidget {
        background-color: #F4F4F4;
    }
    QLabel {
        color: #202020;
        background-color: transparent;
        padding: 2px;
    }
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QComboBox {
        background-color: #FFFFFF;
        color: #333333;
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        padding: 5px;
        selection-background-color: #0078D4; /* Blu per selezione testo */
        selection-color: white;
    }
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, 
    QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QComboBox:focus {
        border: 1px solid #0078D4; /* Bordo blu quando in focus */
        /* box-shadow: 0 0 3px #0078D4; /* Leggera ombra esterna (potrebbe non funzionare su tutte le piattaforme Qt) */
    }
    QLineEdit[readOnly="true"], QTextEdit[readOnly="true"] {
        background-color: #E9E9E9;
        color: #505050;
    }
    QPushButton {
        background-color: #0078D4; /* Blu Microsoft come colore primario */
        color: white;
        border: none; /* No bordo per un look più flat */
        border-radius: 4px;
        padding: 8px 15px;
        font-weight: bold;
        min-width: 80px;
    }
    QPushButton:hover {
        background-color: #005A9E; /* Blu più scuro per hover */
    }
    QPushButton:pressed {
        background-color: #004C8A; /* Ancora più scuro per pressed */
    }
    QPushButton:disabled {
        background-color: #BDBDBD;
        color: #757575;
    }
    QTabWidget::pane {
        border-top: 1px solid #D0D0D0;
        background-color: #FFFFFF; /* Sfondo bianco per il contenuto dei tab */
        padding: 5px;
    }
    QTabBar::tab {
        background: #E0E0E0;
        color: #424242;
        border: 1px solid #D0D0D0;
        border-bottom: none; /* Il bordo inferiore è gestito dal pane o dal tab selezionato */
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 7px 12px;
        margin-right: 2px;
    }
    QTabBar::tab:hover {
        background: #D0D0D0;
    }
    QTabBar::tab:selected {
        background: #FFFFFF; /* Stesso colore del pane */
        color: #0078D4;     /* Colore d'accento per il testo del tab selezionato */
        font-weight: bold;
        border-color: #D0D0D0;
        /* Rimuovi il bordo inferiore del tab selezionato per farlo fondere con il pane */
        border-bottom-color: #FFFFFF; 
    }
    QTableWidget {
        gridline-color: #E0E0E0;
        background-color: #FFFFFF;
        alternate-background-color: #F9F9F9;
        selection-background-color: #60AFFF; /* Blu più chiaro per selezione tabella */
        selection-color: #FFFFFF;
        border: 1px solid #D0D0D0;
    }
    QHeaderView::section {
        background-color: #F0F0F0;
        color: #333333;
        padding: 5px;
        border: 1px solid #D0D0D0;
        border-bottom-width: 1px; 
        font-weight: bold;
    }
    QComboBox::drop-down {
        border: none;
        background: transparent;
        width: 20px;
    }
    QComboBox::down-arrow {
        image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-arrow-down-16.png); /* Freccia standard di Qt */
    }
    QComboBox QAbstractItemView { /* Lista a discesa */
        border: 1px solid #D0D0D0;
        selection-background-color: #0078D4;
        selection-color: white;
        background-color: white;
        padding: 2px;
    }
    QGroupBox {
        background-color: #FFFFFF;
        border: 1px solid #D0D0D0;
        border-radius: 4px;
        margin-top: 1.5ex; /* Spazio per il titolo */
        padding: 10px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px 0 5px;
        left: 10px;
        color: #0078D4; /* Titolo del GroupBox con colore d'accento */
    }
    QCheckBox {
        spacing: 5px;
    }
    QCheckBox::indicator {
        width: 16px; height: 16px;
        border: 1px solid #B0B0B0; border-radius: 3px;
        background-color: white;
    }
    QCheckBox::indicator:checked {
        background-color: #0078D4; border-color: #005A9E;
        /* Per un checkmark SVG (richiede Qt 5.15+ o gestione via QIcon) */
        /* image: url(path/to/checkmark.svg) */
    }
    QStatusBar {
        background-color: #E0E0E0;
        color: #333333;
    }
    QMenuBar { background-color: #E0E0E0; color: #333333; }
    QMenuBar::item:selected { background: #C0C0C0; }
    QMenu { background-color: #FFFFFF; border: 1px solid #B0B0B0; color: #333333;}
    QMenu::item:selected { background-color: #0078D4; color: white; }
"""


# Configurazione del logger (SOLO IN gui_main.py)
gui_logger = logging.getLogger("CatastoGUI") # Assegna l'oggetto logger a una variabile
gui_logger.setLevel(logging.INFO) # o logging.DEBUG

# Se non ha già handler, li aggiunge:
if not gui_logger.hasHandlers():
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    # Esempio di File Handler
    gui_log_handler = logging.FileHandler("catasto_gui.log") # Nome del file di log
    gui_log_handler.setFormatter(logging.Formatter(log_format))
    gui_logger.addHandler(gui_log_handler)

    # Esempio di Console Handler (per debug durante lo sviluppo)
    # if not getattr(sys, 'frozen', False): # Per non mostrare in console se è un eseguibile frozen
    #    console_handler = logging.StreamHandler(sys.stdout)
    #    console_handler.setFormatter(logging.Formatter(log_format))
    #    gui_logger.addHandler(console_handler)
client_ip_address_gui: str = "127.0.0.1"

class DBConfigDialog(QDialog): # Definizione del Dialogo (come fornito precedentemente)
    def __init__(self, parent=None, initial_config: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Configurazione Connessione Database")
        self.setModal(True)
        self.setMinimumWidth(450) # Leggermente più largo

        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, 
                                  "ArchivioDiStatoSavona", "CatastoStoricoApp")
        logging.getLogger("CatastoGUI").debug(f"DBConfigDialog usa QSettings file: {self.settings.fileName()}")

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight) # Allinea etichette a destra

        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["Locale (localhost)", "Remoto (Server Specifico)"])
        self.db_type_combo.currentIndexChanged.connect(self._db_type_changed)
        layout.addRow("Tipo di Server Database:", self.db_type_combo)

        self.host_label = QLabel("Indirizzo Server Host (*):") # Aggiunto (*)
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("Es. 192.168.1.100 o nomeserver.locale")
        layout.addRow(self.host_label, self.host_edit)

        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1, 65535)
        self.port_spinbox.setValue(5432)
        layout.addRow("Porta Server (*):", self.port_spinbox)

        self.dbname_edit = QLineEdit()
        layout.addRow("Nome Database (*):", self.dbname_edit)

        self.user_edit = QLineEdit()
        layout.addRow("Utente Database (*):", self.user_edit)
        
        self.schema_edit = QLineEdit()
        layout.addRow("Schema Database (es. catasto):", self.schema_edit)
        
        self.button_box = QDialogButtonBox()
        btn_save = self.button_box.addButton("Salva e Procedi", QDialogButtonBox.AcceptRole)
        btn_cancel = self.button_box.addButton(QDialogButtonBox.Cancel) # Qt si occuperà del testo
        
        self.button_box.accepted.connect(self.accept) 
        self.button_box.rejected.connect(self.reject)
        layout.addRow(self.button_box)

        # Popola i campi e imposta visibilità iniziale
        if initial_config:
            self._populate_from_config(initial_config)
        else:
            self._load_settings() 
        self._db_type_changed(self.db_type_combo.currentIndex())

    def _db_type_changed(self, index):
        is_remoto = (index == 1) 
        self.host_label.setVisible(is_remoto)
        self.host_edit.setVisible(is_remoto)
        if not is_remoto: # Se selezionato "Locale"
            self.host_edit.setText("localhost") # Imposta default e rendilo non visibile ma il valore è lì
            self.host_edit.setReadOnly(True) # Rendi localhost non modificabile per "Locale"
        else: # Se selezionato "Remoto"
            self.host_edit.setReadOnly(False)
            if self.host_edit.text() == "localhost": # Se prima era locale, pulisci per input utente
                self.host_edit.clear()

    def _populate_from_config(self, config: Dict[str, Any]):
        db_type_str = config.get(SETTINGS_DB_TYPE, "Locale (localhost)")
        # Imposta l'indice della combobox in base al testo, con fallback
        type_index = self.db_type_combo.findText(db_type_str, Qt.MatchFixedString)
        if type_index >= 0:
            self.db_type_combo.setCurrentIndex(type_index)
        elif "Remoto" in db_type_str: # Fallback se il testo non matcha esattamente
            self.db_type_combo.setCurrentIndex(1)
        else:
            self.db_type_combo.setCurrentIndex(0)
        
        self.host_edit.setText(config.get(SETTINGS_DB_HOST, "localhost"))
        
        # --- CORREZIONE PER LA PORTA ---
        port_value_from_config = config.get(SETTINGS_DB_PORT) # Potrebbe essere None, stringa, o int
        default_port = 5432
        
        current_port_value = default_port # Inizia con il default
        if port_value_from_config is not None:
            try:
                current_port_value = int(port_value_from_config)
            except (ValueError, TypeError):
                # Se logging.getLogger("CatastoGUI") non è definito qui, usa print o logging standard
                # logging.getLogger("CatastoGUI").warning(f"Valore porta non valido '{port_value_from_config}' dalla configurazione, usando default {default_port}.")
                print(f"ATTENZIONE: Valore porta non valido '{port_value_from_config}' dalla configurazione, usando default {default_port}.")
                current_port_value = default_port # Ripristina il default in caso di errore di conversione
        
        self.port_spinbox.setValue(current_port_value)
        # --- FINE CORREZIONE ---
            
        self.dbname_edit.setText(config.get(SETTINGS_DB_NAME, "catasto_storico"))
        self.user_edit.setText(config.get(SETTINGS_DB_USER, "postgres"))
        self.schema_edit.setText(config.get(SETTINGS_DB_SCHEMA, "catasto"))

        self._db_type_changed(self.db_type_combo.currentIndex()) # Assicura che la visibilità di host_edit sia corretta

    def _load_settings(self):
        """Carica le impostazioni da QSettings e popola i campi."""
        config = {}
        config[SETTINGS_DB_TYPE] = self.settings.value(SETTINGS_DB_TYPE, "Locale (localhost)")
        config[SETTINGS_DB_HOST] = self.settings.value(SETTINGS_DB_HOST, "localhost")
        config[SETTINGS_DB_PORT] = self.settings.value(SETTINGS_DB_PORT, 5432, type=int)
        config[SETTINGS_DB_NAME] = self.settings.value(SETTINGS_DB_NAME, "catasto_storico")
        config[SETTINGS_DB_USER] = self.settings.value(SETTINGS_DB_USER, "postgres")
        config[SETTINGS_DB_SCHEMA] = self.settings.value(SETTINGS_DB_SCHEMA, "catasto")
        self._populate_from_config(config)

    def accept(self):
        if not self.dbname_edit.text().strip():
            QMessageBox.warning(self, "Dati Mancanti", "Il nome del database è obbligatorio."); return
        if not self.user_edit.text().strip():
            QMessageBox.warning(self, "Dati Mancanti", "L'utente del database è obbligatorio."); return
        
        is_remoto = (self.db_type_combo.currentIndex() == 1)
        host_val = self.host_edit.text().strip()
        if is_remoto and not host_val:
            QMessageBox.warning(self, "Dati Mancanti", "L'indirizzo del server host è obbligatorio per database remoto."); return
        
        self._save_settings()
        super().accept()

    def _save_settings(self):
        self.settings.setValue(SETTINGS_DB_TYPE, self.db_type_combo.currentText())
        host_to_save = "localhost" if self.db_type_combo.currentIndex() == 0 else self.host_edit.text().strip()
        self.settings.setValue(SETTINGS_DB_HOST, host_to_save)
        self.settings.setValue(SETTINGS_DB_PORT, self.port_spinbox.value())
        self.settings.setValue(SETTINGS_DB_NAME, self.dbname_edit.text().strip())
        self.settings.setValue(SETTINGS_DB_USER, self.user_edit.text().strip())
        self.settings.setValue(SETTINGS_DB_SCHEMA, self.schema_edit.text().strip() or "catasto")
        self.settings.sync()
        logging.getLogger("CatastoGUI").info(f"Impostazioni di connessione al database salvate in: {self.settings.fileName()}")

    def get_config_values(self) -> Dict[str, Any]:
        host_val = "localhost" if self.db_type_combo.currentIndex() == 0 else self.host_edit.text().strip()
        return {
            "host": host_val,
            "port": self.port_spinbox.value(),
            "dbname": self.dbname_edit.text().strip(),
            "user": self.user_edit.text().strip(),
            "schema": self.schema_edit.text().strip() or "catasto",
            # "type" è implicito da host localhost vs altro
        }
class LoginDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super(LoginDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.logged_in_user_id: Optional[int] = None
        self.logged_in_user_info: Optional[Dict] = None
        self.current_session_id: Optional[str] = None
        
        self.setWindowTitle("Login - Catasto Storico")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        
        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Username:"), 0, 0)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Inserisci username")
        form_layout.addWidget(self.username_edit, 0, 1)
        
        form_layout.addWidget(QLabel("Password:"), 1, 0)
        self.password_edit = QPasswordLineEdit()
        form_layout.addWidget(self.password_edit, 1, 1)
        
        layout.addLayout(form_layout)
        
        buttons_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self.handle_login)
        
        self.cancel_button = QPushButton("Esci")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.username_edit.setFocus()

    def handle_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Login Fallito", "Username e password sono obbligatori.")
            return
        
        credentials = self.db_manager.get_user_credentials(username)
        login_success = False
        
        if credentials:
            user_id_local = credentials['id']
            stored_hash = credentials['password_hash']
            
            if _verify_password(stored_hash, password):
                login_success = True
                logging.getLogger("CatastoGUI").info(f"Login GUI OK per ID: {user_id_local}")
            else:
                QMessageBox.warning(self, "Login Fallito", "Password errata.")
                logging.getLogger("CatastoGUI").warning(f"Login GUI fallito (pwd errata) per ID: {user_id_local}")
                self.password_edit.selectAll()
                self.password_edit.setFocus()
                return
        else:
            QMessageBox.warning(self, "Login Fallito", "Utente non trovato o non attivo.")
            logging.getLogger("CatastoGUI").warning(f"Login GUI fallito (utente '{username}' non trovato/attivo).")
            self.username_edit.selectAll()
            self.username_edit.setFocus()
            return
        
        if login_success and user_id_local is not None:
            session_id_returned = self.db_manager.register_access(
                user_id_local, 'login', 
                indirizzo_ip=client_ip_address_gui,
                esito=True,
                application_name='CatastoAppGUI'
            )
            
            if session_id_returned:
                self.logged_in_user_id = user_id_local
                self.logged_in_user_info = credentials # Contiene l'ID dell'utente DB, non app_user_id!
                                                    # Assicurati che 'id' in credentials sia l'app_user_id
                self.current_session_id = session_id_returned

                # Imposta le variabili di sessione per l'audit
                # Assumendo che user_id_local sia l'app_user_id
                if not self.db_manager.set_audit_session_variables(self.logged_in_user_id, self.current_session_id): # <--- CHIAMATA
                    # Gestisci l'errore, forse il login non dovrebbe procedere
                    QMessageBox.critical(self, "Errore Audit", "Impossibile impostare le informazioni di sessione per l'audit.")
                    # Potresti decidere di non accettare il login qui

                # Commentato perché il metodo `set_session_app_user` sembra fare qualcosa di simile,
                # ma `set_audit_session_variables` è più specifico per i GUC.
                # if not self.db_manager.set_session_app_user(self.logged_in_user_id, client_ip_address_gui):
                #    logging.getLogger("CatastoGUI").error("Impossibile impostare contesto DB post-login!")

                QMessageBox.information(self, "Login Riuscito", 
                                        f"Benvenuto {self.logged_in_user_info.get('nome_completo', username)}!")
                self.accept()
            else:
                QMessageBox.critical(self, "Login Fallito", "Errore critico: Impossibile registrare la sessione di accesso.")
                logging.getLogger("CatastoGUI").error(f"Login GUI OK per ID {user_id_local} ma fallita reg. accesso.")
                
class CreateUserDialog(QDialog):
    def __init__(self, db_manager, parent=None): # db_manager è CatastoDBManager
        super(CreateUserDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Crea Nuovo Utente")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Username:"), 0, 0)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Min. 3 caratteri")
        form_layout.addWidget(self.username_edit, 0, 1)

        form_layout.addWidget(QLabel("Password:"), 1, 0)
        self.password_edit = QPasswordLineEdit() # Usa la classe definita sopra
        self.password_edit.setPlaceholderText("Min. 6 caratteri")
        form_layout.addWidget(self.password_edit, 1, 1)

        form_layout.addWidget(QLabel("Conferma Password:"), 2, 0)
        self.confirm_edit = QPasswordLineEdit() # Usa la classe definita sopra
        form_layout.addWidget(self.confirm_edit, 2, 1)

        form_layout.addWidget(QLabel("Nome Completo:"), 3, 0)
        self.nome_edit = QLineEdit()
        form_layout.addWidget(self.nome_edit, 3, 1)

        form_layout.addWidget(QLabel("Email:"), 4, 0)
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("es. utente@dominio.it")
        form_layout.addWidget(self.email_edit, 4, 1)

        form_layout.addWidget(QLabel("Ruolo:"), 5, 0)
        self.ruolo_combo = QComboBox()
        self.ruolo_combo.addItems(["admin", "archivista", "consultatore"]) # Ruoli standard
        form_layout.addWidget(self.ruolo_combo, 5, 1)

        frame_form = QFrame() # Un frame per raggruppare i campi
        frame_form.setLayout(form_layout)
        frame_form.setFrameShape(QFrame.StyledPanel) # Aspetto più gradevole
        layout.addWidget(frame_form)

        buttons_layout = QHBoxLayout()
        self.create_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton), "Crea Utente")
        self.create_button.clicked.connect(self.handle_create_user)
        self.create_button.setDefault(True)

        self.cancel_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.create_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.username_edit.setFocus()

    def handle_create_user(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        confirm = self.confirm_edit.text()
        nome_completo = self.nome_edit.text().strip()
        email = self.email_edit.text().strip()
        ruolo = self.ruolo_combo.currentText()

        if not all([username, password, nome_completo, email, ruolo]):
            QMessageBox.warning(self, "Errore di Validazione", "Tutti i campi sono obbligatori.")
            return
        if len(username) < 3:
            QMessageBox.warning(self, "Errore di Validazione", "L'username deve essere di almeno 3 caratteri.")
            return
        if len(password) < 6:
            QMessageBox.warning(self, "Errore di Validazione", "La password deve essere di almeno 6 caratteri.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Errore di Validazione", "Le password non coincidono.")
            self.password_edit.setFocus()
            self.password_edit.selectAll()
            return

        # Potresti aggiungere una validazione email più robusta qui (es. con regex)

        try:
            password_hash = _hash_password(password) # Utilizza la funzione globale

            if self.db_manager.create_user(username, password_hash, nome_completo, email, ruolo):
                QMessageBox.information(self, "Successo", f"Utente '{username}' creato con successo.")
                self.accept() 
            else:
                # Il db_manager.create_user dovrebbe loggare l'errore specifico.
                # Potrebbe fallire per utente duplicato o altri vincoli DB.
                QMessageBox.critical(self, "Errore Database", 
                                     f"Impossibile creare l'utente '{username}'.\n"
                                     "Verificare che l'username non sia già in uso e controllare i log del database.")
        except Exception as e:
            # Questo cattura errori imprevisti, inclusi quelli dall'hashing o dalla chiamata DB.
            # Assicurati che logging.getLogger("CatastoGUI") sia definito e accessibile globalmente o passato.
            # Se logging.getLogger("CatastoGUI") non è disponibile, usa print() o logging standard.
            # logging.getLogger("CatastoGUI").error(f"Errore imprevisto durante la creazione dell'utente {username}: {e}")
            QMessageBox.critical(self, "Errore Inaspettato", 
                                 f"Si è verificato un errore imprevisto: {e}")
class CatastoMainWindow(QMainWindow):
    def __init__(self):
        
        super(CatastoMainWindow, self).__init__()
        self.db_manager: Optional[CatastoDBManager] = None
        self.logged_in_user_id: Optional[int] = None
        self.logged_in_user_info: Optional[Dict] = None
        self.current_session_id: Optional[str] = None

        # Inizializzazione dei QTabWidget per i sotto-tab se si usa questa organizzazione
        self.consultazione_sub_tabs = QTabWidget()
        self.inserimento_sub_tabs = QTabWidget()
        # Aggiungere altri se necessario (es. per Sistema)

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Gestionale Catasto Storico - Archivio di Stato Savona")
        self.setMinimumSize(1280, 720)
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)

        self.create_status_bar_content()
        self.create_menu_bar() # Aggiungi questa chiamata

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        self.setCentralWidget(self.central_widget)

        self.statusBar().showMessage("Pronto.")
        #self.create_menu_bar() # Commenta o rimuovi questa riga se il menu bar non è usato

    # Esempio di Menu Bar (opzionale)
    # All'interno della classe CatastoMainWindow
    # All'interno della classe CatastoMainWindow
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        settings_menu = menu_bar.addMenu("&Impostazioni")
        config_db_action = QAction(QApplication.style().standardIcon(QStyle.SP_ComputerIcon), # Esempio icona
                               "Configurazione &Database...", self)
        config_db_action.setStatusTip("Modifica i parametri di connessione al database")
        config_db_action.triggered.connect(self._apri_dialogo_configurazione_db)
        settings_menu.addAction(config_db_action)

        # --- INIZIO SEZIONE DA RIMUOVERE O COMMENTARE ---
        # Se "Nuovo Comune" è solo nel tab, queste righe non servono più qui.
        #
        # self.nuovo_comune_action = QAction(QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder), "Nuovo &Comune...", self)
        # self.nuovo_comune_action.setStatusTip("Registra un nuovo comune nel sistema")
        # self.nuovo_comune_action.triggered.connect(self.apri_dialog_inserimento_comune)
        # # self.nuovo_comune_action.setEnabled(False) # L'abilitazione era gestita da update_ui_based_on_role
        # file_menu.addAction(self.nuovo_comune_action) # <-- QUESTA RIGA CAUSA L'ERRORE se self.nuovo_comune_action non è definito

        # file_menu.addSeparator() # Rimuovi anche questo se non ci sono altre azioni prima di "Esci"
        # --- FINE SEZIONE DA RIMUOVERE O COMMENTARE ---

        # Azione per Uscire (questa può rimanere)
        exit_action = QAction(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton), "&Esci", self)
        exit_action.setStatusTip("Chiudi l'applicazione")
        exit_action.triggered.connect(self.close) # Chiama il metodo close della finestra
        file_menu.addAction(exit_action)

        # Puoi aggiungere altri menu e azioni qui se necessario
        # Esempio:
        # if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin':
        #     admin_menu = menu_bar.addMenu("&Amministrazione")
        #     gestione_utenti_action = QAction("Gestione &Utenti", self)
        #     # gestione_utenti_action.triggered.connect(self.mostra_tab_gestione_utenti)
        #     admin_menu.addAction(gestione_utenti_action)


    def create_status_bar_content(self):
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setFrameShadow(QFrame.Sunken)
        status_layout = QHBoxLayout(status_frame)

        self.db_status_label = QLabel("Database: Non connesso")
        self.user_status_label = QLabel("Utente: Nessuno")

        # RIGA RIMOSSA: La definizione di self.btn_nuovo_comune_toolbar
        # self.btn_nuovo_comune_toolbar = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder), "Nuovo Comune")
        # self.btn_nuovo_comune_toolbar.setToolTip("Registra un nuovo comune nel sistema (Accesso: Admin, Archivista)")
        # self.btn_nuovo_comune_toolbar.clicked.connect(self.apri_dialog_inserimento_comune)
        # self.btn_nuovo_comune_toolbar.setEnabled(False)

        self.logout_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton), "Logout")
        self.logout_button.setToolTip("Effettua il logout dell'utente corrente")
        self.logout_button.clicked.connect(self.handle_logout)
        self.logout_button.setEnabled(False)

        status_layout.addWidget(self.db_status_label)
        status_layout.addSpacing(20)
        status_layout.addWidget(self.user_status_label)
        status_layout.addStretch()
        
        # RIGA RIMOSSA: L'aggiunta di self.btn_nuovo_comune_toolbar al layout
        # status_layout.addWidget(self.btn_nuovo_comune_toolbar)
        # status_layout.addSpacing(10) # Rimuovi anche questo se btn_nuovo_comune_toolbar è rimosso
                                     # o lascialo se vuoi uno spazio prima del logout button.
                                     # Per pulizia, se il pulsante è via, anche lo spazio dedicato può andare.

        status_layout.addWidget(self.logout_button)
        self.main_layout.addWidget(status_frame)

    def perform_initial_setup(self, db_manager: CatastoDBManager, 
                              user_id: Optional[int], 
                              user_info: Optional[Dict], 
                              session_id: Optional[str]):
        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: Inizio perform_initial_setup")
        self.db_manager = db_manager # Assicurati che questo sia l'unico posto dove viene impostato
        self.logged_in_user_id = user_id
        self.logged_in_user_info = user_info
        self.current_session_id = session_id

        # --- Aggiornamento etichetta stato DB ---
        db_name_configured = "N/Config" # Default
        if self.db_manager:
            # Recupera sempre il nome del DB configurato, indipendentemente dallo stato del pool
            db_name_configured = self.db_manager.get_current_dbname() or "N/Config(None)"

        # Lo stato del pool determina se è "Connesso", "Errore Pool", o "Non Esistente/Pronto"
        connection_status_text = ""
        if hasattr(self, 'pool_initialized_successfully'): # Attributo impostato da run_gui_app
            if self.pool_initialized_successfully:
                connection_status_text = f"Database: Connesso ({db_name_configured})"
            else: # Pool non inizializzato (DB non esiste o errore pool)
                # Qui potremmo distinguere ulteriormente se db_exists era True ma il pool è fallito.
                # Per ora, un messaggio generico che il DB non è pronto per le operazioni normali.
                connection_status_text = f"Database: Non Pronto/Inesistente ({db_name_configured})"
        else:
            # Fallback se pool_initialized_successfully non è stato impostato (non dovrebbe accadere)
            connection_status_text = f"Database: Stato Sconosciuto ({db_name_configured})"
            logging.getLogger("CatastoGUI").warning("Attributo 'pool_initialized_successfully' non trovato in CatastoMainWindow.")

        self.db_status_label.setText(connection_status_text)
        logging.getLogger("CatastoGUI").info(f"DEBUG perform_initial_setup: db_status_label IMPOSTATO A: '{connection_status_text}'")

        # --- Aggiornamento etichetta utente ---
        if self.logged_in_user_info: # Controlla se l'utente è effettivamente loggato
            user_display = self.logged_in_user_info.get('nome_completo') or self.logged_in_user_info.get('username', 'N/D')
            ruolo_display = self.logged_in_user_info.get('ruolo', 'N/D')
            self.user_status_label.setText(f"Utente: {user_display} (ID: {self.logged_in_user_id}, Ruolo: {ruolo_display})")
            self.logout_button.setEnabled(True) # Abilita logout se c'è un utente loggato
            self.statusBar().showMessage(f"Login come {user_display} effettuato con successo.")
        else: # Caso di avvio senza login (es. DB non esiste)
            self.user_status_label.setText("Utente: Non Autenticato (Modalità Setup)")
            self.logout_button.setEnabled(False)
            self.statusBar().showMessage("Modalità configurazione database.")
        
        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: Chiamata a setup_tabs")
        self.setup_tabs() # setup_tabs DEVE essere in grado di gestire db_manager.pool == None
        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        self.update_ui_based_on_role()

        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: Chiamata a self.show()")
        self.show()
        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: self.show() completato. Fine perform_initial_setup")
    # All'interno della classe CatastoMainWindow in prova.py
    def setup_tabs(self):
        if not self.db_manager:
            logging.getLogger("CatastoGUI").error("Tentativo di configurare i tab senza un db_manager.")
            QMessageBox.critical(self, "Errore Critico", "DB Manager non inizializzato.")
            return
        self.tabs.clear()# Pulisce i tab esistenti prima di ricrearli

        # --- Tab Consultazione (QTabWidget per contenere sotto-tab) ---
        self.consultazione_sub_tabs.clear() # Pulisce i sotto-tab precedenti
        self.consultazione_sub_tabs.addTab(ElencoComuniWidget(self.db_manager, self.consultazione_sub_tabs), "Elenco Comuni")
        self.consultazione_sub_tabs.addTab(RicercaPartiteWidget(self.db_manager, self.consultazione_sub_tabs), "Ricerca Partite")
        self.consultazione_sub_tabs.addTab(RicercaPossessoriWidget(self.db_manager, self.consultazione_sub_tabs), "Ricerca Avanzata Possessori")
        self.consultazione_sub_tabs.addTab(RicercaAvanzataImmobiliWidget(self.db_manager, self.consultazione_sub_tabs), "Ricerca Immobili Avanzata")
        self.tabs.addTab(self.consultazione_sub_tabs, "Consultazione e Modifica")

        # --- Tab Inserimento e Gestione ---
        inserimento_gestione_contenitore = QWidget() # Contenitore principale per questo tab
        layout_contenitore_inserimento = QVBoxLayout(inserimento_gestione_contenitore)

        # Rimuoviamo il pulsante che apriva il dialogo, ora è un tab
        # if hasattr(self, 'btn_nuovo_comune_nel_tab'):
        #     layout_contenitore_inserimento.removeWidget(self.btn_nuovo_comune_nel_tab)
        #     self.btn_nuovo_comune_nel_tab.deleteLater() # Pulisce il vecchio pulsante
        #     del self.btn_nuovo_comune_nel_tab

        # QTabWidget per i sotto-tab di Inserimento
        if not hasattr(self, 'inserimento_sub_tabs') or not isinstance(self.inserimento_sub_tabs, QTabWidget):
            self.inserimento_sub_tabs = QTabWidget()
        #self.inserimento_sub_tabs.clear() 

        # Aggiungi InserimentoComuneWidget come primo sotto-tab
        # Assicurati che self.logged_in_user_info sia il dizionario corretto
        utente_per_inserimenti = self.logged_in_user_info if self.logged_in_user_info else {} # Passa un dict vuoto se None

        self.inserimento_sub_tabs.addTab(
            InserimentoComuneWidget(
                parent=self.inserimento_sub_tabs, 
                db_manager=self.db_manager, 
                utente_attuale_info=utente_per_inserimenti
            ), 
            "Nuovo Comune"
                )
        # Aggiungi gli altri sotto-tab di inserimento come prima
        self.inserimento_sub_tabs.addTab(InserimentoPossessoreWidget(self.db_manager, self.inserimento_sub_tabs), "Nuovo Possessore")
        self.inserimento_sub_tabs.addTab(InserimentoLocalitaWidget(self.db_manager, self.inserimento_sub_tabs), "Nuova Località")
        self.inserimento_sub_tabs.addTab(InserimentoLocalitaWidget(self.db_manager, self.inserimento_sub_tabs), "Nuova Località")
        self.inserimento_sub_tabs.addTab(RegistrazioneProprietaWidget(self.db_manager, self.inserimento_sub_tabs), "Registrazione Proprietà")
        self.inserimento_sub_tabs.addTab(OperazioniPartitaWidget(self.db_manager, self.inserimento_sub_tabs), "Operazioni Partita")
        registrazione_widget_instance = None
        operazioni_widget_instance = None

        # Se i widget sono già aggiunti a inserimento_sub_tabs
        for i in range(self.inserimento_sub_tabs.count()):
            widget = self.inserimento_sub_tabs.widget(i)
            if isinstance(widget, RegistrazioneProprietaWidget):
                registrazione_widget_instance = widget
            elif isinstance(widget, OperazioniPartitaWidget):
                operazioni_widget_instance = widget
        
        if registrazione_widget_instance and operazioni_widget_instance:
            registrazione_widget_instance.partita_creata_per_operazioni_collegate.connect(
                # Usa una lambda per passare l'istanza corretta di OperazioniPartitaWidget
                lambda partita_id, comune_id: self._handle_partita_creata_per_operazioni(
                    partita_id, comune_id, operazioni_widget_instance 
                )
            )
            logging.getLogger("CatastoGUI").info("Segnale 'partita_creata_per_operazioni_collegate' connesso.")
        else:
            logging.getLogger("CatastoGUI").error("Impossibile connettere il segnale: RegistrazioneProprietaWidget o OperazioniPartitaWidget non trovati nei sotto-tab di inserimento.")
        self.inserimento_sub_tabs.addTab(
            RegistraConsultazioneWidget(self.db_manager, self.logged_in_user_info, self.inserimento_sub_tabs), 
            "Registra Consultazione"
        )
        layout_contenitore_inserimento.addWidget(self.inserimento_sub_tabs)
        self.tabs.addTab(inserimento_gestione_contenitore, "Inserimento e Gestione")

        # --- Tab Esportazioni ---
        self.tabs.addTab(EsportazioniWidget(self.db_manager, self), "Esportazioni")

        # --- Tab Reportistica ---
        self.tabs.addTab(ReportisticaWidget(self.db_manager, self), "Reportistica")

        # --- Tab Statistiche e Viste Materializzate ---
        self.tabs.addTab(StatisticheWidget(self.db_manager, self), "Statistiche e Viste")

        # --- Tab Gestione Utenti (solo per admin) ---
        if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin':
            self.tabs.addTab(GestioneUtentiWidget(self.db_manager, self.logged_in_user_info, self), "Gestione Utenti")

        # --- Tab Sistema ---
        sistema_sub_tabs = QTabWidget() # Continuiamo a usare un QTabWidget per futuri sotto-tab

        if self.db_manager: # Assicurati che db_manager sia inizializzato
            # Aggiungi il AuditLogViewerWidget come primo sotto-tab
            self.audit_viewer_widget = AuditLogViewerWidget(self.db_manager, sistema_sub_tabs)
            sistema_sub_tabs.addTab(self.audit_viewer_widget, "Log di Audit")

            # ---> QUI È L'AGGIUNTA IMPORTANTE <---
            self.backup_restore_widget = BackupRestoreWidget(self.db_manager, sistema_sub_tabs)
            sistema_sub_tabs.addTab(self.backup_restore_widget, "Backup/Ripristino")
            # ---> FINE AGGIUNTA <---

        else:
            # Fallback se db_manager non è pronto (non dovrebbe succedere se il login è ok)
            error_widget_audit = QLabel("Errore: DB Manager non inizializzato per il Log di Audit.")
            sistema_sub_tabs.addTab(error_widget_audit, "Log di Audit")
            error_widget_backup = QLabel("Errore: DB Manager non inizializzato per Backup/Ripristino.")
            sistema_sub_tabs.addTab(error_widget_backup, "Backup/Ripristino")


        # --- Tab Sistema ---
        sistema_sub_tabs = QTabWidget() 
        if self.db_manager:
            self.audit_viewer_widget = AuditLogViewerWidget(self.db_manager, sistema_sub_tabs)
            sistema_sub_tabs.addTab(self.audit_viewer_widget, "Log di Audit")

            self.backup_restore_widget = BackupRestoreWidget(self.db_manager, sistema_sub_tabs)
            sistema_sub_tabs.addTab(self.backup_restore_widget, "Backup/Ripristino DB")
            
            # --- NUOVO TAB AMMINISTRAZIONE DB ---
            self.admin_db_ops_widget = AdminDBOperationsWidget(self.db_manager, sistema_sub_tabs)
            sistema_sub_tabs.addTab(self.admin_db_ops_widget, "Amministrazione DB")
            # --- FINE NUOVO TAB ---
        else:
            # ... (fallback come prima) ...
            error_widget_audit = QLabel("Errore: DB Manager non inizializzato per il Log di Audit.")
            sistema_sub_tabs.addTab(error_widget_audit, "Log di Audit")
            error_widget_backup = QLabel("Errore: DB Manager non inizializzato per Backup/Ripristino.")
            sistema_sub_tabs.addTab(error_widget_backup, "Backup/Ripristino DB")
            error_widget_admin_ops = QLabel("Errore: DB Manager non inizializzato per Amministrazione DB.")
            sistema_sub_tabs.addTab(error_widget_admin_ops, "Amministrazione DB")


        self.tabs.addTab(sistema_sub_tabs, "Sistema")

        # La chiamata a self.update_ui_based_on_role() avverrà dopo in perform_initial_setup,
        # quindi il pulsante self.btn_nuovo_comune_nel_tab e i tab verranno abilitati/disabilitati correttamente.

    # ... (definizione di is_admin, is_archivista, is_admin_offline come prima) ...
        ruolo = None
        if self.logged_in_user_info: # Verifica se logged_in_user_info è stato impostato
            ruolo = self.logged_in_user_info.get('ruolo')
        
        is_admin = ruolo == 'admin'
        is_archivista = ruolo == 'archivista'
        is_admin_offline = ruolo == 'admin_offline'

        # Abilita/disabilita il pulsante nel tab Inserimento e Gestione
        if hasattr(self, 'btn_nuovo_comune_nel_tab'): # Controllo per sicurezza
            self.btn_nuovo_comune_nel_tab.setEnabled(is_admin or is_archivista)
        
        tab_indices = {self.tabs.tabText(i): i for i in range(self.tabs.count())}

        # Abilitazione standard dei tab se l'utente è loggato e non è admin_offline
        consultazione_enabled = bool(self.logged_in_user_info and not is_admin_offline)
        inserimento_enabled = (is_admin or is_archivista) and not is_admin_offline
        statistiche_enabled = (is_admin or is_archivista) and not is_admin_offline # Anche archivisti vedono statistiche
        gestione_utenti_enabled = is_admin and not is_admin_offline
        sistema_enabled = is_admin # Solo admin normali per il tab Sistema, l'admin_offline lo gestiamo dopo

        if "Consultazione" in tab_indices: self.tabs.setTabEnabled(tab_indices["Consultazione"], consultazione_enabled)
        if "Inserimento e Gestione" in tab_indices: self.tabs.setTabEnabled(tab_indices["Inserimento e Gestione"], inserimento_enabled)
        if "Esportazioni" in tab_indices: self.tabs.setTabEnabled(tab_indices["Esportazioni"], consultazione_enabled) # Anche consultatori esportano
        if "Reportistica" in tab_indices: self.tabs.setTabEnabled(tab_indices["Reportistica"], consultazione_enabled) # Anche consultatori vedono report
        if "Statistiche e Viste" in tab_indices: self.tabs.setTabEnabled(tab_indices["Statistiche e Viste"], statistiche_enabled)
        if "Gestione Utenti" in tab_indices: self.tabs.setTabEnabled(tab_indices["Gestione Utenti"], gestione_utenti_enabled)
        
        # Gestione specifica per il tab "Sistema"
        if "Sistema" in tab_indices:
            if is_admin_offline: # Se siamo in modalità setup DB
                self.tabs.setTabEnabled(tab_indices["Sistema"], True) # Abilita solo il tab Sistema
                # Seleziona automaticamente il tab Sistema e il sotto-tab Amministrazione DB
                self.tabs.setCurrentIndex(tab_indices["Sistema"])
                if hasattr(self, 'sistema_sub_tabs'):
                    admin_db_ops_tab_index = -1
                    for i in range(self.sistema_sub_tabs.count()):
                        if self.sistema_sub_tabs.tabText(i) == "Amministrazione DB":
                            admin_db_ops_tab_index = i
                            break
                    if admin_db_ops_tab_index != -1:
                        self.sistema_sub_tabs.setCurrentIndex(admin_db_ops_tab_index)
            else: # Utente admin normale loggato
                self.tabs.setTabEnabled(tab_indices["Sistema"], is_admin)
        
        # Disabilita tutti gli altri tab se siamo in modalità admin_offline e il pool non è inizializzato
        if is_admin_offline and hasattr(self, 'pool_initialized_successfully') and not self.pool_initialized_successfully:
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) != "Sistema":
                    self.tabs.setTabEnabled(i, False)
        
        # Logout button
        if hasattr(self, 'logout_button'):
            self.logout_button.setEnabled(not is_admin_offline and bool(self.logged_in_user_id))
    def _handle_partita_creata_per_operazioni(self, nuova_partita_id: int, comune_id_partita: int, 
                                             target_operazioni_widget: OperazioniPartitaWidget):
        """
        Slot per gestire la creazione di una nuova partita e il passaggio al tab
        delle operazioni collegate, pre-compilando l'ID.
        """
        logging.getLogger("CatastoGUI").info(f"Nuova Partita ID {nuova_partita_id} (Comune ID {comune_id_partita}) creata. Passaggio al tab Operazioni.")
        
        # Trova l'indice del tab principale "Inserimento e Gestione"
        idx_tab_inserimento = -1
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Inserimento e Gestione":
                idx_tab_inserimento = i
                break
        
        if idx_tab_inserimento != -1:
            self.tabs.setCurrentIndex(idx_tab_inserimento) # Vai al tab principale "Inserimento e Gestione"
            
            # Ora, all'interno di questo tab, trova il sotto-tab "Operazioni su Partita"
            # e imposta il suo indice corrente.
            # Assumiamo che self.inserimento_sub_tabs sia l'attributo corretto che contiene OperazioniPartitaWidget.
            if hasattr(self, 'inserimento_sub_tabs'):
                idx_sotto_tab_operazioni = -1
                for i in range(self.inserimento_sub_tabs.count()):
                    # Controlla se il widget del sotto-tab è l'istanza che ci interessa
                    if self.inserimento_sub_tabs.widget(i) == target_operazioni_widget:
                        idx_sotto_tab_operazioni = i
                        break
                
                if idx_sotto_tab_operazioni != -1:
                    self.inserimento_sub_tabs.setCurrentIndex(idx_sotto_tab_operazioni)
                    # Chiama il metodo su OperazioniPartitaWidget per impostare l'ID
                    target_operazioni_widget.seleziona_e_carica_partita_sorgente(nuova_partita_id)
                else:
                    logging.getLogger("CatastoGUI").error("Impossibile trovare il sotto-tab 'Operazioni su Partita' per il cambio automatico.")
            else:
                logging.getLogger("CatastoGUI").error("'self.inserimento_sub_tabs' non trovato in CatastoMainWindow.")
        else:
            logging.getLogger("CatastoGUI").error("Impossibile trovare il tab principale 'Inserimento e Gestione'.")

    def update_ui_based_on_role(self):
        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        ruolo = None
        is_admin_offline_mode = False 
        
        # Determina se siamo in modalità offline o se un utente è loggato
        if hasattr(self, 'pool_initialized_successfully') and not self.pool_initialized_successfully:
            if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin_offline':
                is_admin_offline_mode = True
                ruolo = 'admin_offline' # Usa il ruolo fittizio
        
        if not is_admin_offline_mode and self.logged_in_user_info:
            ruolo = self.logged_in_user_info.get('ruolo')

        is_admin = ruolo == 'admin'
        is_archivista = ruolo == 'archivista'
        
        logging.getLogger("CatastoGUI").debug(f"update_ui_based_on_role: Ruolo effettivo considerato: {ruolo}, is_admin_offline: {is_admin_offline_mode}")

        # Abilitazione pulsante Nuovo Comune nel tab Inserimento (se esiste)
        if hasattr(self, 'btn_nuovo_comune_nel_tab'):
            can_add_comune = (is_admin or is_archivista) and not is_admin_offline_mode
            self.btn_nuovo_comune_nel_tab.setEnabled(can_add_comune)
            logging.getLogger("CatastoGUI").debug(f"Pulsante Nuovo Comune abilitato: {can_add_comune}")
        
        tab_indices = {self.tabs.tabText(i): i for i in range(self.tabs.count())}
        logging.getLogger("CatastoGUI").debug(f"Tab disponibili: {tab_indices}")

        # Logica di abilitazione dei tab
        # Se il pool non è inizializzato o siamo in admin_offline, la maggior parte dei tab è disabilitata
        # a meno che non sia il tab "Sistema".
        db_ready_for_normal_ops = hasattr(self, 'pool_initialized_successfully') and self.pool_initialized_successfully and not is_admin_offline_mode

        consultazione_enabled = db_ready_for_normal_ops # Tutti gli utenti loggati (non offline)
        inserimento_enabled = (is_admin or is_archivista) and db_ready_for_normal_ops
        statistiche_enabled = (is_admin or is_archivista) and db_ready_for_normal_ops
        gestione_utenti_enabled = is_admin and db_ready_for_normal_ops
        
        # Tab Sistema è accessibile per admin normali, o per admin_offline (per setup DB)
        sistema_enabled = is_admin or is_admin_offline_mode

        if "Consultazione" in tab_indices: 
            self.tabs.setTabEnabled(tab_indices["Consultazione"], consultazione_enabled)
            logging.getLogger("CatastoGUI").debug(f"Tab Consultazione abilitato: {consultazione_enabled}")
        if "Inserimento e Gestione" in tab_indices: 
            self.tabs.setTabEnabled(tab_indices["Inserimento e Gestione"], inserimento_enabled)
            logging.getLogger("CatastoGUI").debug(f"Tab Inserimento e Gestione abilitato: {inserimento_enabled}")
        if "Esportazioni" in tab_indices: 
            self.tabs.setTabEnabled(tab_indices["Esportazioni"], consultazione_enabled) # Anche consultatori
            logging.getLogger("CatastoGUI").debug(f"Tab Esportazioni abilitato: {consultazione_enabled}")
        if "Reportistica" in tab_indices: 
            self.tabs.setTabEnabled(tab_indices["Reportistica"], consultazione_enabled) # Anche consultatori
            logging.getLogger("CatastoGUI").debug(f"Tab Reportistica abilitato: {consultazione_enabled}")
        if "Statistiche e Viste" in tab_indices: 
            self.tabs.setTabEnabled(tab_indices["Statistiche e Viste"], statistiche_enabled)
            logging.getLogger("CatastoGUI").debug(f"Tab Statistiche e Viste abilitato: {statistiche_enabled}")
        if "Gestione Utenti" in tab_indices: 
            self.tabs.setTabEnabled(tab_indices["Gestione Utenti"], gestione_utenti_enabled)
            logging.getLogger("CatastoGUI").debug(f"Tab Gestione Utenti abilitato: {gestione_utenti_enabled}")
        
        if "Sistema" in tab_indices:
            self.tabs.setTabEnabled(tab_indices["Sistema"], sistema_enabled)
            logging.getLogger("CatastoGUI").debug(f"Tab Sistema abilitato: {sistema_enabled}")
            if sistema_enabled and is_admin_offline_mode:
                self.tabs.setCurrentIndex(tab_indices["Sistema"])
                if hasattr(self, 'sistema_sub_tabs'):
                    admin_db_ops_tab_index = -1
                    for i in range(self.sistema_sub_tabs.count()):
                        if self.sistema_sub_tabs.tabText(i) == "Amministrazione DB":
                            admin_db_ops_tab_index = i; break
                    if admin_db_ops_tab_index != -1:
                        self.sistema_sub_tabs.setCurrentIndex(admin_db_ops_tab_index)
                        logging.getLogger("CatastoGUI").debug("Tab Sistema -> Amministrazione DB selezionato per modalità offline.")
        
        if hasattr(self, 'logout_button'):
            self.logout_button.setEnabled(not is_admin_offline_mode and bool(self.logged_in_user_id))
    def apri_dialog_inserimento_comune(self): # Metodo integrato nella classe
        if not self.db_manager:
            QMessageBox.critical(self, "Errore", "Manager Database non inizializzato.")
            return
        if not self.logged_in_user_info:
            QMessageBox.warning(self, "Login Richiesto", "Effettuare il login per procedere.")
            return

        ruolo_utente = self.logged_in_user_info.get('ruolo')
        if ruolo_utente not in ['admin', 'archivista']:
            QMessageBox.warning(self, "Accesso Negato",
                                "Non si dispone delle autorizzazioni necessarie per aggiungere un comune.")
            return

        utente_login_username = self.logged_in_user_info.get('username', 'log_utente_sconosciuto')

        dialog = InserimentoComuneWidget(self.db_manager, utente_login_username, self) # Passa 'self' come parent
        if dialog.exec_() == QDialog.Accepted:
            logging.getLogger("CatastoGUI").info(f"Dialogo inserimento comune chiuso con successo da utente '{utente_login_username}'.")
            QMessageBox.information(self, "Comune Aggiunto", "Il nuovo comune è stato registrato con successo.")
            # Aggiorna la vista dell'elenco comuni se presente nel tab consultazione
            # Questo ciclo cerca il widget ElencoComuniWidget tra i sotto-tab di consultazione
            if hasattr(self, 'consultazione_sub_tabs'):
                 for i in range(self.consultazione_sub_tabs.count()):
                    widget = self.consultazione_sub_tabs.widget(i)
                    if isinstance(widget, ElencoComuniWidget):
                        widget.load_comuni_data() # Assumendo che ElencoComuniWidget abbia questo metodo
                        logging.getLogger("CatastoGUI").info("Elenco comuni nel tab consultazione aggiornato.")
                        break
        else:
            logging.getLogger("CatastoGUI").info(f"Dialogo inserimento comune annullato da utente '{utente_login_username}'.")

    def _apri_dialogo_configurazione_db(self):
        logging.getLogger("CatastoGUI").info("Apertura dialogo configurazione DB da menu.")
        current_config_for_dialog = {}
        settings = QSettings(QSettings.IniFormat, QSettings.UserScope, 
                             "ArchivioDiStatoSavona", "CatastoStoricoApp")
        
        current_config_for_dialog[SETTINGS_DB_TYPE] = settings.value(SETTINGS_DB_TYPE, "Locale (localhost)")
        current_config_for_dialog[SETTINGS_DB_HOST] = settings.value(SETTINGS_DB_HOST, "localhost")
        # Fornisci un default stringa e converti qui per assicurare che il tipo sia corretto per int()
        port_str_val = settings.value(SETTINGS_DB_PORT, "5432") # Leggi come stringa, default a stringa "5432"
        try:
            current_config_for_dialog[SETTINGS_DB_PORT] = int(port_str_val)
        except (ValueError, TypeError):
            current_config_for_dialog[SETTINGS_DB_PORT] = 5432 # Fallback se la stringa non è un intero valido
            logging.getLogger("CatastoGUI").warning(f"Valore porta non valido '{port_str_val}' letto da QSettings, usando default 5432.")

        current_config_for_dialog[SETTINGS_DB_NAME] = settings.value(SETTINGS_DB_NAME, "catasto_storico")
        current_config_for_dialog[SETTINGS_DB_USER] = settings.value(SETTINGS_DB_USER, "postgres")
        current_config_for_dialog[SETTINGS_DB_SCHEMA] = settings.value(SETTINGS_DB_SCHEMA, "catasto")

        config_dialog = DBConfigDialog(self, initial_config=current_config_for_dialog)
        if config_dialog.exec_() == QDialog.Accepted:
            # Le impostazioni sono state salvate dal dialogo stesso
            QMessageBox.information(self, "Configurazione Salvata", 
                                    "Le impostazioni del database sono state aggiornate.\n"
                                    "È necessario riavviare l'applicazione per applicare le modifiche.")
            # Qui, il riavvio è la strada più semplice. Modificare un DBManager attivo
            # con un nuovo pool e nuovi parametri è complesso e soggetto a errori.
    def handle_logout(self):
        if self.logged_in_user_id and self.current_session_id and self.db_manager:
            if self.db_manager.logout_user(self.logged_in_user_id, self.current_session_id, client_ip_address_gui): #
                QMessageBox.information(self, "Logout", "Logout effettuato con successo.")
            else:
                QMessageBox.warning(self, "Logout Fallito", "Errore durante la registrazione del logout.")

            self.logged_in_user_id = None
            self.logged_in_user_info = None
            self.current_session_id = None
            if self.db_manager: self.db_manager.clear_session_app_user()

            self.user_status_label.setText("Utente: Nessuno")
            self.db_status_label.setText("Database: Connesso (Logout effettuato)") # O "Non connesso" se si chiude la conn
            self.logout_button.setEnabled(False)
            #self.btn_nuovo_comune_toolbar.setEnabled(False)
            # if hasattr(self, 'menuBar'): self.menuBar().setEnabled(False)


            for i in range(self.tabs.count()): # Disabilita tutti i tab
                self.tabs.setTabEnabled(i, False)
            self.tabs.clear() # Rimuove tutti i tab

            self.statusBar().showMessage("Logout effettuato. Riavviare l'applicazione per un nuovo login.")
            # Potrebbe essere preferibile chiudere e richiedere un nuovo avvio dell'app
            # piuttosto che tentare di tornare al dialogo di login da qui.
            self.close() # Chiude la finestra principale, che triggera closeEvent
        else:
            logging.getLogger("CatastoGUI").warning("Tentativo di logout senza una sessione utente o db_manager validi.")


    def closeEvent(self, event: QCloseEvent):
        logging.getLogger("CatastoGUI").info("Evento closeEvent intercettato in CatastoMainWindow.")

        if hasattr(self, 'db_manager') and self.db_manager:
            pool_era_attivo_prima_di_closeevent = self.db_manager.pool is not None

            if pool_era_attivo_prima_di_closeevent:
                if hasattr(self, 'logged_in_user_id') and self.logged_in_user_id and \
                   hasattr(self, 'current_session_id') and self.current_session_id:
                    logging.getLogger("CatastoGUI").info(f"Chiusura applicazione: esecuzione logout di sicurezza per utente ID: {self.logged_in_user_id}...")
                    self.db_manager.logout_user(self.logged_in_user_id, self.current_session_id, client_ip_address_gui)
                else:
                    logging.getLogger("CatastoGUI").info("Nessun utente loggato o sessione attiva, pulizia variabili audit generica.")
                    self.db_manager.clear_audit_session_variables() # Tenta di pulire se il pool è attivo
            else:
                logging.getLogger("CatastoGUI").info("Pool del DB principale non attivo durante closeEvent, operazioni di logout/pulizia audit su DB saltate.")

            # Chiudi il pool (close_pool() gestisce il caso in cui self.pool sia già None)
            self.db_manager.close_pool() 
            logging.getLogger("CatastoGUI").info("Tentativo di chiusura del pool di connessioni al database completato.")
        else:
            logging.getLogger("CatastoGUI").warning("DB Manager non disponibile durante closeEvent.")

        logging.getLogger("CatastoGUI").info("Applicazione GUI Catasto Storico terminata.")
        event.accept()

# --- Fine Classe CatastoMainWindow ---
def run_gui_app():
    app = QApplication(sys.argv)
    QApplication.setOrganizationName("ArchivioDiStatoSavona")
    QApplication.setApplicationName("CatastoStoricoApp")
    app.setStyleSheet(MODERN_STYLESHEET)

    if not FPDF_AVAILABLE:
        QMessageBox.warning(None, "Avviso Dipendenza Mancante",
                            "La libreria FPDF non è installata.\nL'esportazione PDF non sarà disponibile.")

    settings = QSettings(QSettings.IniFormat, QSettings.UserScope, 
                        "ArchivioDiStatoSavona", "CatastoStoricoApp")
    
    db_manager_gui = None # Sarà istanziato dopo aver ottenuto config e password
    main_window_instance = CatastoMainWindow() # Crea la finestra principale subito
                                            # per usarla come parent dei dialoghi se necessario.

    retry_setup = True
    active_db_config = None

    while retry_setup:
        retry_setup = False # Assume che questa iterazione sia l'ultima a meno di errori specifici
        active_db_config = None # Resetta per ogni tentativo

        # 1. Carica o chiedi la configurazione del database (host, porta, dbname, user, schema)
        if settings.contains(SETTINGS_DB_NAME) and settings.value(SETTINGS_DB_NAME, type=str).strip():
            logging.getLogger("CatastoGUI").info(f"Caricamento configurazione DB da QSettings: {settings.fileName()}")
            active_db_config = {
                "type": settings.value(SETTINGS_DB_TYPE, "Locale (localhost)"),
                "host": settings.value(SETTINGS_DB_HOST, "localhost"),
                "port": settings.value(SETTINGS_DB_PORT, 5432, type=int),
                "dbname": settings.value(SETTINGS_DB_NAME, "catasto_storico"),
                "user": settings.value(SETTINGS_DB_USER, "postgres"),
                "schema": settings.value(SETTINGS_DB_SCHEMA, "catasto")
            }
        else:
            logging.getLogger("CatastoGUI").info("Nessuna configurazione DB valida. Apertura dialogo di configurazione iniziale.")
            config_dialog = DBConfigDialog(parent=None, initial_config=None) # Passa None come parent
            if config_dialog.exec_() == QDialog.Accepted:
                active_db_config = config_dialog.get_config_values()
                if not active_db_config or not active_db_config.get("dbname"):
                    QMessageBox.critical(None, "Errore Critico", "Configurazione DB non valida. L'app si chiuderà.")
                    sys.exit(1)
            else:
                logging.getLogger("CatastoGUI").info("Configurazione DB iniziale annullata. Uscita.")
                sys.exit(0)
        
        logging.getLogger("CatastoGUI").info(f"Configurazione DB corrente: {active_db_config}")

        # 2. Chiedi la password del database
        db_password, ok = QInputDialog.getText(None, "Autenticazione Database",
                                            f"Password per utente '{active_db_config['user']}'\nDB: '{active_db_config['dbname']}'\nHost: '{active_db_config['host']}:{active_db_config['port']}'",
                                            QLineEdit.Password)
        if not ok: # Utente ha premuto Annulla o chiuso il dialogo password
            logging.getLogger("CatastoGUI").info("Inserimento password annullato. Uscita.")
            sys.exit(0)
        # La password vuota è permessa, il DB deciderà se è valida.

        # 3. Istanzia DBManager
        if db_manager_gui and db_manager_gui.pool: # Chiudi il pool precedente se stiamo ritentando
            db_manager_gui.close_pool()
            
        db_manager_gui = CatastoDBManager(
            dbname=active_db_config["dbname"], user=active_db_config["user"], password=db_password,
            host=active_db_config["host"], port=active_db_config["port"], schema=active_db_config["schema"],
            application_name=f"CatastoAppGUI_{active_db_config['dbname']}", # Nome pool più specifico
            log_file="catasto_main_db.log", log_level=logging.DEBUG
        )
        main_window_instance.db_manager = db_manager_gui
        main_window_instance.pool_initialized_successfully = False # Resetta per ogni tentativo

        # 4. Tentativo di inizializzare il pool principale e gestire errori
        if db_manager_gui.initialize_main_pool(): # Tenta di connettersi al DB target
            main_window_instance.pool_initialized_successfully = True
            logging.getLogger("CatastoGUI").info(f"Pool per DB '{active_db_config['dbname']}' inizializzato con successo.")
            if hasattr(main_window_instance, 'db_status_label'):
                main_window_instance.db_status_label.setText(f"Database: Connesso ({active_db_config['dbname']})")
            # Procedi al login utente normale
            login_success = False
            while not login_success:
                login_dialog = LoginDialog(db_manager_gui)
                if login_dialog.exec_() == QDialog.Accepted:
                    if login_dialog.logged_in_user_id is not None: # Controllo più robusto
                        main_window_instance.perform_initial_setup(
                            db_manager_gui, login_dialog.logged_in_user_id,
                            login_dialog.logged_in_user_info, login_dialog.current_session_id
                        )
                        login_success = True
                        retry_setup = False # Successo, esci dal loop di setup
                    else:
                        QMessageBox.critical(None, "Errore Login", "Dati di login interni non validi."); sys.exit(1) # Uscita critica
                else: # Login annullato
                    logging.getLogger("CatastoGUI").info("Login annullato. Uscita."); 
                    if db_manager_gui: db_manager_gui.close_pool(); 
                    sys.exit(0)
        else: # Fallimento inizializzazione pool principale
            db_target_name = active_db_config.get("dbname", "sconosciuto")
            # Controlla se il DB *target* esiste sul server (se il server è raggiungibile)
            # Le credenziali db_admin_... servono per connettersi a 'postgres' e controllare
            # Qui usiamo le credenziali fornite per l'app; potrebbero non bastare se l'utente non è superuser.
            # Il tab Amministrazione DB chiederà credenziali admin dedicate per creare il DB.
            server_host = active_db_config.get("host")
            db_exists_on_server = db_manager_gui.check_database_exists(db_target_name, active_db_config.get("user"), db_password)
            
            if not db_exists_on_server and server_host in ["localhost", "127.0.0.1"]: # E il server è locale o sembra raggiungibile
                logging.getLogger("CatastoGUI").warning(f"DB '{db_target_name}' non trovato su server '{server_host}'. Avvio in modalità setup.")
                QMessageBox.information(None, "Database Non Esistente",
                                    f"Il DB '{db_target_name}' non esiste sul server.\n"
                                    "Avvio in modalità configurazione limitata per permettere la creazione del database.")
                
                main_window_instance.logged_in_user_info = {'ruolo': 'admin_offline', 'id': 0, 'username': 'admin_setup', 'nome_completo': 'Admin Setup'}
                main_window_instance.logged_in_user_id = 0
                main_window_instance.current_session_id = str(uuid.uuid4())
                main_window_instance.perform_initial_setup(db_manager_gui, 0, main_window_instance.logged_in_user_info, main_window_instance.current_session_id)
                retry_setup = False # Esci dal loop di setup, l'utente userà l'admin tab
            else: # Altro errore di connessione (server remoto non raggiungibile, credenziali errate per DB target, ecc.)
                logging.getLogger("CatastoGUI").error(f"Fallita inizializzazione pool per DB '{db_target_name}' su host '{server_host}'.")
                reply = QMessageBox.warning(None, "Errore Connessione Database",
                                    f"Impossibile connettersi al database configurato:\n"
                                    f"DB: {db_target_name}\nHost: {server_host}\nUtente: {active_db_config['user']}\n\n"
                                    "Possibili cause: server non raggiungibile, credenziali errate, database non accessibile.\n\n"
                                    "Vuoi modificare la configurazione di connessione?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    retry_setup = True # Riprova il ciclo di configurazione
                    # Riapri DBConfigDialog pre-popolato con active_db_config
                    config_dialog_retry = DBConfigDialog(parent=None, initial_config=active_db_config)
                    if config_dialog_retry.exec_() == QDialog.Accepted:
                        # Le nuove impostazioni sono già state salvate da DBConfigDialog in QSettings
                        # Il loop while(retry_setup) rileggerà le impostazioni da QSettings
                        pass
                    else: # L'utente ha annullato la riconfigurazione
                        logging.getLogger("CatastoGUI").info("Riconfigurazione database annullata. Uscita.")
                        sys.exit(0)
                else: # L'utente ha scelto di non riconfigurare -> esci
                    logging.getLogger("CatastoGUI").info("L'utente ha scelto di non modificare la configurazione dopo errore. Uscita.")
                    sys.exit(0)
            
            # Se siamo arrivati qui in modalità limitata o dopo un errore gestito senza retry
            if not retry_setup and not main_window_instance.pool_initialized_successfully:
                if hasattr(main_window_instance, 'db_status_label'):
                    main_window_instance.db_status_label.setText(f"Database: Non Connesso/Errore ({db_target_name})")
                if hasattr(main_window_instance, 'user_status_label'):
                    if main_window_instance.logged_in_user_info and main_window_instance.logged_in_user_info.get('ruolo') == 'admin_offline':
                        main_window_instance.user_status_label.setText("Utente: Modalità Setup (DB non pronto)")
                    else: # Dovrebbe essere coperto dall'uscita precedente
                        main_window_instance.user_status_label.setText("Utente: Non Autenticato")
                if hasattr(main_window_instance, 'logout_button'):
                    main_window_instance.logout_button.setEnabled(False)

    # --- Fine Loop while retry_setup ---

    if main_window_instance and (main_window_instance.pool_initialized_successfully or \
    (main_window_instance.logged_in_user_info and main_window_instance.logged_in_user_info.get('ruolo') == 'admin_offline')):
        logging.getLogger("CatastoGUI").info(">>> run_gui_app: Avvio loop eventi applicazione...")
        exit_code = app.exec_()
        logging.getLogger("CatastoGUI").info(f">>> run_gui_app: app.exec_() TERMINATO con codice: {exit_code}")
    else:
        logging.getLogger("CatastoGUI").critical("Avvio applicazione fallito: configurazione DB o login non completati.")
        # Non chiudere il pool qui perché potrebbe essere già stato chiuso o mai aperto.
        # Il db_manager_gui.close_pool() alla fine di run_gui_app gestirà la chiusura se il pool esiste.

    if db_manager_gui: db_manager_gui.close_pool() # Assicura la chiusura se è stato istanziato
    sys.exit(getattr(app, 'returnCode', 0) if 'app' in locals() and hasattr(app, 'returnCode') else 0)


# Aggiungere un metodo per modificare la configurazione in CatastoMainWindow
# Nel metodo create_menu_bar(self) di CatastoMainWindow:
# ...
# settings_menu = menu_bar.addMenu("&Impostazioni")
# config_db_action = QAction("Configurazione &Database...", self)
# config_db_action.triggered.connect(self._apri_dialogo_modifica_configurazione_db) # Nuovo slot
# settings_menu.addAction(config_db_action)
# ...

# Nuovo slot in CatastoMainWindow:
# def _apri_dialogo_modifica_configurazione_db(self):
#     logging.getLogger("CatastoGUI").info("Apertura dialogo modifica configurazione DB da menu.")
#     current_config_from_qsettings = {}
#     settings = QSettings("ArchivioDiStatoSavona", "CatastoStoricoApp")
#     if settings.contains(SETTINGS_DB_NAME):
#         current_config_from_qsettings = {
#             SETTINGS_DB_TYPE: settings.value(SETTINGS_DB_TYPE),
#             SETTINGS_DB_HOST: settings.value(SETTINGS_DB_HOST),
#             SETTINGS_DB_PORT: settings.value(SETTINGS_DB_PORT, type=int),
#             SETTINGS_DB_NAME: settings.value(SETTINGS_DB_NAME),
#             SETTINGS_DB_USER: settings.value(SETTINGS_DB_USER),
#             SETTINGS_DB_SCHEMA: settings.value(SETTINGS_DB_SCHEMA)
#         }
#
#     config_dialog = DBConfigDialog(self, initial_config=current_config_from_qsettings)
#     if config_dialog.exec_() == QDialog.Accepted:
#         # Le impostazioni sono state salvate in QSettings da DBConfigDialog
#         QMessageBox.information(self, "Configurazione Salvata",
#                                 "Le impostazioni del database sono state aggiornate.\n"
#                                 "È necessario RIAVVIARE l'applicazione per applicare le modifiche.")

if __name__ == "__main__":
     # Il logging dovrebbe essere configurato qui se non già fatto altrove all'inizio del file
     # Esempio:
 if not logging.getLogger("CatastoGUI").hasHandlers():
     log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
...# (resto della configurazione del logger) ...

run_gui_app()
