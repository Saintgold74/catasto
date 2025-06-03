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
import uuid  # Se usato per session_id in modalità offline
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

# Importazioni PyQt5
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QLabel, QLineEdit,
                            QComboBox, QTabWidget,  QMessageBox,
                            QGridLayout, QDialog,  QMainWindow,  QStyle,  QSpinBox,
                            QInputDialog,  QFrame,  QAction,
                            QFormLayout, QDialogButtonBox, )
# Aggiunto QCloseEvent
from PyQt5.QtGui import  QCloseEvent
from PyQt5.QtCore import Qt, QSettings, pyqtSlot, QEvent, QObject, pyqtSignal
# In gui_main.py, dopo le importazioni PyQt e standard:
# E le sue eccezioni se servono qui
from catasto_db_manager import CatastoDBManager

# Dai nuovi moduli che creeremo:
from gui_widgets import (
    ElencoComuniWidget, RicercaPartiteWidget, RicercaPossessoriWidget,
    RicercaAvanzataImmobiliWidget, InserimentoComuneWidget, InserimentoPossessoreWidget,
    InserimentoLocalitaWidget, RegistrazioneProprietaWidget, OperazioniPartitaWidget,
    EsportazioniWidget, ReportisticaWidget, StatisticheWidget, GestioneUtentiWidget,
    AuditLogViewerWidget, BackupRestoreWidget, AdminDBOperationsWidget,RegistraConsultazioneWidget
   )
from app_utils import FPDF_AVAILABLE, QPasswordLineEdit, _verify_password, _hash_password


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
    class DBMError(Exception):
        pass

    class DBUniqueConstraintError(DBMError):
        pass

    class DBNotFoundError(DBMError):
        pass

    class DBDataError(DBMError):
        pass
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

# Esempio: ID, Nome Compl, Cognome/Nome, Paternità, Quota, Titolo
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
# Nomi per le chiavi di QSettings (globali o definite prima di run_gui_app)
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
# --- Configurazione Logger (assicurati sia definito prima del suo uso) ---
gui_logger = logging.getLogger("CatastoGUI")
if not gui_logger.hasHandlers():
    # ... (configurazione handler come prima) ...
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s' # Aggiunto filename e lineno
    gui_log_handler = logging.FileHandler("catasto_gui.log", mode='a', encoding='utf-8') # Aggiunto encoding e mode
    gui_log_handler.setFormatter(logging.Formatter(log_format))
    gui_logger.addHandler(gui_log_handler)
    gui_logger.setLevel(logging.DEBUG) # Imposta a DEBUG per più dettagli durante lo sviluppo

    # Esempio di Console Handler (per debug durante lo sviluppo)
    # if not getattr(sys, 'frozen', False): # Per non mostrare in console se è un eseguibile frozen
    #    console_handler = logging.StreamHandler(sys.stdout)
    #    console_handler.setFormatter(logging.Formatter(log_format))
    #    gui_logger.addHandler(console_handler)
client_ip_address_gui: str = "127.0.0.1"


class DBConfigDialog(QDialog):  # Definizione del Dialogo (come fornito precedentemente)
    def __init__(self, parent=None, initial_config: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Configurazione Connessione Database")
        self.setModal(True)
        self.setMinimumWidth(450)  # Leggermente più largo

        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope,
                                  "ArchivioDiStatoSavona", "CatastoStoricoApp")
        logging.getLogger("CatastoGUI").debug(
            f"DBConfigDialog usa QSettings file: {self.settings.fileName()}")

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)  # Allinea etichette a destra

        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(
            ["Locale (localhost)", "Remoto (Server Specifico)"])
        self.db_type_combo.currentIndexChanged.connect(self._db_type_changed)
        layout.addRow("Tipo di Server Database:", self.db_type_combo)

        self.host_label = QLabel("Indirizzo Server Host (*):")  # Aggiunto (*)
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText(
            "Es. 192.168.1.100 o nomeserver.locale")
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
        btn_save = self.button_box.addButton(
            "Salva e Procedi", QDialogButtonBox.AcceptRole)
        btn_cancel = self.button_box.addButton(
            QDialogButtonBox.Cancel)  # Qt si occuperà del testo

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
        if not is_remoto:  # Se selezionato "Locale"
            # Imposta default e rendilo non visibile ma il valore è lì
            self.host_edit.setText("localhost")
            # Rendi localhost non modificabile per "Locale"
            self.host_edit.setReadOnly(True)
        else:  # Se selezionato "Remoto"
            self.host_edit.setReadOnly(False)
            if self.host_edit.text() == "localhost":  # Se prima era locale, pulisci per input utente
                self.host_edit.clear()

    def _populate_from_config(self, config: Dict[str, Any]):
        db_type_str = config.get(SETTINGS_DB_TYPE, "Locale (localhost)")
        # Imposta l'indice della combobox in base al testo, con fallback
        type_index = self.db_type_combo.findText(
            db_type_str, Qt.MatchFixedString)
        if type_index >= 0:
            self.db_type_combo.setCurrentIndex(type_index)
        elif "Remoto" in db_type_str:  # Fallback se il testo non matcha esattamente
            self.db_type_combo.setCurrentIndex(1)
        else:
            self.db_type_combo.setCurrentIndex(0)

        self.host_edit.setText(config.get(SETTINGS_DB_HOST, "localhost"))

        # --- CORREZIONE PER LA PORTA ---
        # Potrebbe essere None, stringa, o int
        port_value_from_config = config.get(SETTINGS_DB_PORT)
        default_port = 5432

        current_port_value = default_port  # Inizia con il default
        if port_value_from_config is not None:
            try:
                current_port_value = int(port_value_from_config)
            except (ValueError, TypeError):
                # Se logging.getLogger("CatastoGUI") non è definito qui, usa print o logging standard
                # logging.getLogger("CatastoGUI").warning(f"Valore porta non valido '{port_value_from_config}' dalla configurazione, usando default {default_port}.")
                print(
                    f"ATTENZIONE: Valore porta non valido '{port_value_from_config}' dalla configurazione, usando default {default_port}.")
                # Ripristina il default in caso di errore di conversione
                current_port_value = default_port

        self.port_spinbox.setValue(current_port_value)
        # --- FINE CORREZIONE ---

        self.dbname_edit.setText(config.get(
            SETTINGS_DB_NAME, "catasto_storico"))
        self.user_edit.setText(config.get(SETTINGS_DB_USER, "postgres"))
        self.schema_edit.setText(config.get(SETTINGS_DB_SCHEMA, "catasto"))

        # Assicura che la visibilità di host_edit sia corretta
        self._db_type_changed(self.db_type_combo.currentIndex())

    def _load_settings(self):
        """Carica le impostazioni da QSettings e popola i campi."""
        config = {}
        config[SETTINGS_DB_TYPE] = self.settings.value(
            SETTINGS_DB_TYPE, "Locale (localhost)")
        config[SETTINGS_DB_HOST] = self.settings.value(
            SETTINGS_DB_HOST, "localhost")
        config[SETTINGS_DB_PORT] = self.settings.value(
            SETTINGS_DB_PORT, 5432, type=int)
        config[SETTINGS_DB_NAME] = self.settings.value(
            SETTINGS_DB_NAME, "catasto_storico")
        config[SETTINGS_DB_USER] = self.settings.value(
            SETTINGS_DB_USER, "postgres")
        config[SETTINGS_DB_SCHEMA] = self.settings.value(
            SETTINGS_DB_SCHEMA, "catasto")
        self._populate_from_config(config)

    def accept(self):
        if not self.dbname_edit.text().strip():
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il nome del database è obbligatorio.")
            return
        if not self.user_edit.text().strip():
            QMessageBox.warning(self, "Dati Mancanti",
                                "L'utente del database è obbligatorio.")
            return

        is_remoto = (self.db_type_combo.currentIndex() == 1)
        host_val = self.host_edit.text().strip()
        if is_remoto and not host_val:
            QMessageBox.warning(
                self, "Dati Mancanti", "L'indirizzo del server host è obbligatorio per database remoto.")
            return

        self._save_settings()
        super().accept()

    def _save_settings(self):
        self.settings.setValue(
            SETTINGS_DB_TYPE, self.db_type_combo.currentText())
        host_to_save = "localhost" if self.db_type_combo.currentIndex(
        ) == 0 else self.host_edit.text().strip()
        self.settings.setValue(SETTINGS_DB_HOST, host_to_save)
        self.settings.setValue(SETTINGS_DB_PORT, self.port_spinbox.value())
        self.settings.setValue(
            SETTINGS_DB_NAME, self.dbname_edit.text().strip())
        self.settings.setValue(SETTINGS_DB_USER, self.user_edit.text().strip())
        self.settings.setValue(
            SETTINGS_DB_SCHEMA, self.schema_edit.text().strip() or "catasto")
        self.settings.sync()
        logging.getLogger("CatastoGUI").info(
            f"Impostazioni di connessione al database salvate in: {self.settings.fileName()}")

    def get_config_values(self) -> Dict[str, Any]:
        host_val = "localhost" if self.db_type_combo.currentIndex(
        ) == 0 else self.host_edit.text().strip()
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
        self.current_session_id_from_dialog: Optional[str] = None # NUOVO attributo per conservare l'UUID

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

        credentials = self.db_manager.get_user_credentials(username) # Presumiamo restituisca anche 'id' utente app
        login_success = False
        user_id_app = None # ID utente dell'applicazione

        if credentials:
            user_id_app = credentials.get('id') # ID dell'utente dalla tabella 'utente'
            stored_hash = credentials.get('password_hash')
            is_active = credentials.get('attivo', False)

            if not is_active:
                QMessageBox.warning(self, "Login Fallito", "Utente non attivo.")
                logging.getLogger("CatastoGUI").warning(f"Login GUI fallito (utente '{username}' non attivo).")
                return # Non procedere oltre se l'utente non è attivo

            if stored_hash and _verify_password(stored_hash, password): # Usa la tua funzione di verifica
                login_success = True
                logging.getLogger("CatastoGUI").info(f"Verifica password GUI OK per utente '{username}' (ID App: {user_id_app})")
            else:
                QMessageBox.warning(self, "Login Fallito", "Username o Password errati.")
                logging.getLogger("CatastoGUI").warning(f"Login GUI fallito (pwd errata) per utente '{username}'.")
                self.password_edit.selectAll()
                self.password_edit.setFocus()
                return
        else:
            QMessageBox.warning(self, "Login Fallito", "Username o Password errati.") # Messaggio generico
            logging.getLogger("CatastoGUI").warning(f"Login GUI fallito (utente '{username}' non trovato).")
            self.username_edit.selectAll()
            self.username_edit.setFocus()
            return

        if login_success and user_id_app is not None:
            try:
                # Chiamata a register_access (modificato in db_manager)
                # Ora dovrebbe restituire l'UUID della sessione
                session_uuid_returned = self.db_manager.register_access(
                    user_id=user_id_app, # Passa l'ID dell'utente dell'applicazione
                    action='login',
                    esito=True,
                    indirizzo_ip=client_ip_address_gui, # Assumendo che client_ip_address_gui sia definita globalmente o accessibile
                    application_name='CatastoAppGUI'
                )

                if session_uuid_returned:
                    self.logged_in_user_id = user_id_app
                    self.logged_in_user_info = credentials # Contiene tutti i dati dell'utente, incluso 'id'
                    self.current_session_id_from_dialog = session_uuid_returned # Salva l'UUID

                    # Imposta le variabili di sessione PostgreSQL per l'audit
                    # user_id_app è l'ID dell'utente da 'utente.id'
                    # session_uuid_returned è l'UUID dalla tabella 'sessioni_accesso.id_sessione'
                    if not self.db_manager.set_audit_session_variables(user_id_app, session_uuid_returned):
                        QMessageBox.critical(self, "Errore Audit", "Impossibile impostare le informazioni di sessione per l'audit. Il login non può procedere.")
                        # Considera di non fare self.accept() qui se questo è un errore bloccante
                        return 
                    
                    QMessageBox.information(self, "Login Riuscito",
                                            f"Benvenuto {self.logged_in_user_info.get('nome_completo', username)}!")
                    self.accept() # Chiude il dialogo e segnala successo
                else:
                    # register_access ha fallito nel restituire un session_id
                    QMessageBox.critical(self, "Login Fallito", "Errore critico: Impossibile registrare la sessione di accesso nel database.")
                    logging.getLogger("CatastoGUI").error(f"Login GUI OK per utente '{username}' ma fallita registrazione della sessione (nessun UUID sessione restituito).")
            
            except DBMError as e_dbm: # Cattura DBMError da register_access o set_audit_session_variables
                QMessageBox.critical(self, "Errore di Login (DB)", f"Errore durante il processo di login:\n{str(e_dbm)}")
                logging.getLogger("CatastoGUI").error(f"DBMError durante il login per {username}: {str(e_dbm)}")
            except Exception as e_gen: # Altri errori imprevisti
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore di sistema durante il login:\n{str(e_gen)}")
                logging.getLogger("CatastoGUI").error(f"Errore imprevisto durante il login per {username}: {str(e_gen)}", exc_info=True)

class CatastoMainWindow(QMainWindow):
    def __init__(self):
        super(CatastoMainWindow, self).__init__()
        self.logger = logging.getLogger("CatastoGUI") # ASSEGNA IL LOGGER QUI
        self.db_manager: Optional[CatastoDBManager] = None
        self.logged_in_user_id: Optional[int] = None      # ID utente dell'applicazione
        self.logged_in_user_info: Optional[Dict] = None # Dettagli utente
        self.current_session_id: Optional[str] = None   # UUID della sessione attiva

        # Inizializzazione dei QTabWidget per i sotto-tab se si usa questa organizzazione
        self.consultazione_sub_tabs = QTabWidget()
        self.inserimento_sub_tabs = QTabWidget()
        # Aggiungere altri se necessario (es. per Sistema)

        self.initUI()

    def initUI(self):
        self.setWindowTitle(
            "Gestionale Catasto Storico - Archivio di Stato Savona")
        self.setMinimumSize(1280, 720)
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)

        self.create_status_bar_content()
        self.create_menu_bar()  # Aggiungi questa chiamata

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        self.setCentralWidget(self.central_widget)

        self.statusBar().showMessage("Pronto.")
        # self.create_menu_bar() # Commenta o rimuovi questa riga se il menu bar non è usato

    # Esempio di Menu Bar (opzionale)
    # All'interno della classe CatastoMainWindow
    # All'interno della classe CatastoMainWindow
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        settings_menu = menu_bar.addMenu("&Impostazioni")
        config_db_action = QAction(QApplication.style().standardIcon(QStyle.SP_ComputerIcon),  # Esempio icona
                                   "Configurazione &Database...", self)
        config_db_action.setStatusTip(
            "Modifica i parametri di connessione al database")
        config_db_action.triggered.connect(
            self._apri_dialogo_configurazione_db)
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
        exit_action = QAction(QApplication.style().standardIcon(
            QStyle.SP_DialogCloseButton), "&Esci", self)
        exit_action.setStatusTip("Chiudi l'applicazione")
        # Chiama il metodo close della finestra
        exit_action.triggered.connect(self.close)
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

        self.logout_button = QPushButton(QApplication.style(
        ).standardIcon(QStyle.SP_DialogCloseButton), "Logout")
        self.logout_button.setToolTip(
            "Effettua il logout dell'utente corrente")
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
                              user_id: Optional[int],      # ID utente dell'applicazione
                              user_info: Optional[Dict],   # Dettagli utente
                              session_id: Optional[str]):  # UUID della sessione
        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: Inizio perform_initial_setup")
        self.db_manager = db_manager
        self.logged_in_user_id = user_id
        self.logged_in_user_info = user_info
        self.current_session_id = session_id # Memorizza l'UUID della sessione

        # --- Aggiornamento etichetta stato DB ---
        db_name_configured = "N/Config"  # Default
        db_name_configured = "N/Config"
        if self.db_manager:
            db_name_configured = self.db_manager.get_current_dbname() or "N/Config(None)"

        connection_status_text = ""
        if hasattr(self, 'pool_initialized_successfully'):
            if self.pool_initialized_successfully:
                connection_status_text = f"Database: Connesso ({db_name_configured})"
            else:
                connection_status_text = f"Database: Non Pronto/Inesistente ({db_name_configured})"
        else:
            connection_status_text = f"Database: Stato Sconosciuto ({db_name_configured})"
        self.db_status_label.setText(connection_status_text)

        if self.logged_in_user_info: # Se l'utente è loggato
            user_display = self.logged_in_user_info.get('nome_completo') or self.logged_in_user_info.get('username', 'N/D')
            ruolo_display = self.logged_in_user_info.get('ruolo', 'N/D')
            # L'ID utente è già in self.logged_in_user_id
            self.user_status_label.setText(f"Utente: {user_display} (ID: {self.logged_in_user_id}, Ruolo: {ruolo_display}, Sessione: {str(self.current_session_id)[:8]}...)")
            self.logout_button.setEnabled(True)
            self.statusBar().showMessage(f"Login come {user_display} effettuato con successo.")
        else: # Modalità setup DB (admin_offline) o nessun login
            ruolo_fittizio = self.logged_in_user_info.get('ruolo') if self.logged_in_user_info else None
            if ruolo_fittizio == 'admin_offline':
                 self.user_status_label.setText(f"Utente: Admin Setup (Sessione: {str(self.current_session_id)[:8]}...)")
                 self.logout_button.setEnabled(True) # L'admin_offline può fare "logout" per chiudere l'app
                 self.statusBar().showMessage("Modalità configurazione database.")
            else: # Nessun login valido, ma il pool potrebbe essere attivo (improbabile con flusso attuale)
                 self.user_status_label.setText("Utente: Non Autenticato")
                 self.logout_button.setEnabled(False)
                 self.statusBar().showMessage("Pronto.")


        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: Chiamata a setup_tabs")
        self.setup_tabs()
        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        self.update_ui_based_on_role()
        
        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: Chiamata a self.show()")
        self.show()
        logging.getLogger("CatastoGUI").info(">>> CatastoMainWindow: self.show() completato. Fine perform_initial_setup")

    # All'interno della classe CatastoMainWindow in prova.py

    def setup_tabs(self):
        if not self.db_manager:
            logging.getLogger("CatastoGUI").error(
                "Tentativo di configurare i tab senza un db_manager.")
            QMessageBox.critical(self, "Errore Critico",
                                 "DB Manager non inizializzato.")
            return
        self.tabs.clear()  # Pulisce i tab principali esistenti prima di ricrearli

        # --- Tab Consultazione (QTabWidget per contenere sotto-tab) ---
        # Assicurati che self.consultazione_sub_tabs sia un'istanza di QTabWidget
        if not hasattr(self, 'consultazione_sub_tabs') or not isinstance(self.consultazione_sub_tabs, QTabWidget):
            self.consultazione_sub_tabs = QTabWidget()
        self.consultazione_sub_tabs.clear()  # Pulisce i sotto-tab precedenti

        # Crea e memorizza il riferimento a ElencoComuniWidget
        self.elenco_comuni_widget_ref = ElencoComuniWidget(self.db_manager, self.consultazione_sub_tabs) #
        self.consultazione_sub_tabs.addTab(self.elenco_comuni_widget_ref, "Elenco Comuni")
        
        self.consultazione_sub_tabs.addTab(RicercaPartiteWidget(
            self.db_manager, self.consultazione_sub_tabs), "Ricerca Partite") #
        self.consultazione_sub_tabs.addTab(RicercaPossessoriWidget(
            self.db_manager, self.consultazione_sub_tabs), "Ricerca Avanzata Possessori") #
        self.consultazione_sub_tabs.addTab(RicercaAvanzataImmobiliWidget(
            self.db_manager, self.consultazione_sub_tabs), "Ricerca Immobili Avanzata") #
        
        self.tabs.addTab(self.consultazione_sub_tabs, "Consultazione e Modifica")

        # --- Tab Inserimento e Gestione ---
        inserimento_gestione_contenitore = QWidget()
        layout_contenitore_inserimento = QVBoxLayout(inserimento_gestione_contenitore)

        if not hasattr(self, 'inserimento_sub_tabs') or not isinstance(self.inserimento_sub_tabs, QTabWidget):
            self.inserimento_sub_tabs = QTabWidget()
        self.inserimento_sub_tabs.clear() # Pulisci i sotto-tab di inserimento

        utente_per_inserimenti = self.logged_in_user_info if self.logged_in_user_info else {}

        # 1. Crea l'istanza di InserimentoComuneWidget e assegnala a self.inserimento_comune_widget_ref
        self.inserimento_comune_widget_ref = InserimentoComuneWidget( #
            parent=self.inserimento_sub_tabs,
            db_manager=self.db_manager,
            utente_attuale_info=utente_per_inserimenti
        )
        
        # 2. Ora puoi tentare la disconnessione (opzionale, ma più sicuro se fatto qui)
        #    e poi la connessione.
        try:
            self.inserimento_comune_widget_ref.comune_appena_inserito.disconnect(self.handle_comune_appena_inserito)
            logging.getLogger("CatastoGUI").debug("Disconnessione precedente di comune_appena_inserito (se esistente) riuscita.")
        except TypeError: 
            logging.getLogger("CatastoGUI").debug("Nessuna connessione precedente da disconnettere per comune_appena_inserito.")
        
        self.inserimento_comune_widget_ref.comune_appena_inserito.connect(self.handle_comune_appena_inserito)
        logging.getLogger("CatastoGUI").info(f"Segnale comune_appena_inserito da istanza ID {id(self.inserimento_comune_widget_ref)} connesso allo slot handle_comune_appena_inserito.")
        
        self.inserimento_sub_tabs.addTab(self.inserimento_comune_widget_ref, "Nuovo Comune")
        
        # Aggiungi gli altri sotto-tab di inserimento
        self.inserimento_sub_tabs.addTab(InserimentoPossessoreWidget( #
            self.db_manager, self.inserimento_sub_tabs), "Nuovo Possessore")
        self.inserimento_sub_tabs.addTab(InserimentoLocalitaWidget( #
            self.db_manager, self.inserimento_sub_tabs), "Nuova Località")
        
        # Istanza di RegistrazioneProprietaWidget e OperazioniPartitaWidget
        # Salva i riferimenti se necessario per connettere segnali tra loro
        registrazione_widget_instance = RegistrazioneProprietaWidget(self.db_manager, self.inserimento_sub_tabs) #
        self.inserimento_sub_tabs.addTab(registrazione_widget_instance, "Registrazione Proprietà")
        
        operazioni_widget_instance = OperazioniPartitaWidget(self.db_manager, self.inserimento_sub_tabs) #
        self.inserimento_sub_tabs.addTab(operazioni_widget_instance, "Operazioni Partita")

        # Connetti il segnale da RegistrazioneProprietaWidget a OperazioniPartitaWidget
        if registrazione_widget_instance and operazioni_widget_instance:
            registrazione_widget_instance.partita_creata_per_operazioni_collegate.connect(
                lambda partita_id, comune_id: self._handle_partita_creata_per_operazioni(
                    partita_id, comune_id, operazioni_widget_instance
                )
            )
            logging.getLogger("CatastoGUI").info(
                "Segnale 'partita_creata_per_operazioni_collegate' connesso.")
        else: # Questo log è utile per il debug se qualcosa va storto con le istanze
            logging.getLogger("CatastoGUI").error(
                "Impossibile connettere il segnale partita_creata: RegistrazioneProprietaWidget o OperazioniPartitaWidget non sono state istanziate correttamente.")

        self.inserimento_sub_tabs.addTab(
            RegistraConsultazioneWidget( #
                self.db_manager, self.logged_in_user_info, self.inserimento_sub_tabs),
            "Registra Consultazione"
        )
        
        layout_contenitore_inserimento.addWidget(self.inserimento_sub_tabs)
        self.tabs.addTab(inserimento_gestione_contenitore, "Inserimento e Gestione")

        # --- Tab Esportazioni ---
        self.tabs.addTab(EsportazioniWidget(self.db_manager, self), "Esportazioni") #

        # --- Tab Reportistica ---
        self.tabs.addTab(ReportisticaWidget(self.db_manager, self), "Reportistica") #

        # --- Tab Statistiche e Viste Materializzate ---
        self.tabs.addTab(StatisticheWidget(self.db_manager, self), "Statistiche e Viste") #

        # --- Tab Gestione Utenti (solo per admin) ---
        if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin':
            self.tabs.addTab(GestioneUtentiWidget( #
                self.db_manager, self.logged_in_user_info, self), "Gestione Utenti")

        # --- Tab Sistema ---
        # sistema_sub_tabs viene ricreato qui, quindi non serve clear() se è locale a questo metodo
        sistema_sub_tabs = QTabWidget() 
        if self.db_manager:
            self.audit_viewer_widget = AuditLogViewerWidget(self.db_manager, sistema_sub_tabs) #
            sistema_sub_tabs.addTab(self.audit_viewer_widget, "Log di Audit")

            self.backup_restore_widget = BackupRestoreWidget(self.db_manager, sistema_sub_tabs) #
            sistema_sub_tabs.addTab(self.backup_restore_widget, "Backup/Ripristino DB")

            self.admin_db_ops_widget = AdminDBOperationsWidget(self.db_manager, sistema_sub_tabs) #
            sistema_sub_tabs.addTab(self.admin_db_ops_widget, "Amministrazione DB")
        else:
            # Fallback se db_manager non è pronto
            error_widget_audit = QLabel("Errore: DB Manager non inizializzato per il Log di Audit.")
            sistema_sub_tabs.addTab(error_widget_audit, "Log di Audit")
            error_widget_backup = QLabel(
                "Errore: DB Manager non inizializzato per Backup/Ripristino.")
            sistema_sub_tabs.addTab(error_widget_backup, "Backup/Ripristino")

        # --- Tab Sistema ---
        sistema_sub_tabs = QTabWidget()
        if self.db_manager:
            self.audit_viewer_widget = AuditLogViewerWidget(
                self.db_manager, sistema_sub_tabs)
            sistema_sub_tabs.addTab(self.audit_viewer_widget, "Log di Audit")

            self.backup_restore_widget = BackupRestoreWidget(
                self.db_manager, sistema_sub_tabs)
            sistema_sub_tabs.addTab(
                self.backup_restore_widget, "Backup/Ripristino DB")

            # --- NUOVO TAB AMMINISTRAZIONE DB ---
            self.admin_db_ops_widget = AdminDBOperationsWidget(
                self.db_manager, sistema_sub_tabs)
            sistema_sub_tabs.addTab(
                self.admin_db_ops_widget, "Amministrazione DB")
            # --- FINE NUOVO TAB ---
        else:
            # ... (fallback come prima) ...
            error_widget_audit = QLabel(
                "Errore: DB Manager non inizializzato per il Log di Audit.")
            sistema_sub_tabs.addTab(error_widget_audit, "Log di Audit")
            error_widget_backup = QLabel(
                "Errore: DB Manager non inizializzato per Backup/Ripristino.")
            sistema_sub_tabs.addTab(
                error_widget_backup, "Backup/Ripristino DB")
            error_widget_admin_ops = QLabel(
                "Errore: DB Manager non inizializzato per Amministrazione DB.")
            sistema_sub_tabs.addTab(
                error_widget_admin_ops, "Amministrazione DB")

        self.tabs.addTab(sistema_sub_tabs, "Sistema")

        # La chiamata a self.update_ui_based_on_role() avverrà dopo in perform_initial_setup,
        # quindi il pulsante self.btn_nuovo_comune_nel_tab e i tab verranno abilitati/disabilitati correttamente.

    # ... (definizione di is_admin, is_archivista, is_admin_offline come prima) ...
        ruolo = None
        if self.logged_in_user_info:  # Verifica se logged_in_user_info è stato impostato
            ruolo = self.logged_in_user_info.get('ruolo')

        is_admin = ruolo == 'admin'
        is_archivista = ruolo == 'archivista'
        is_admin_offline = ruolo == 'admin_offline'

        # Abilita/disabilita il pulsante nel tab Inserimento e Gestione
        if hasattr(self, 'btn_nuovo_comune_nel_tab'):  # Controllo per sicurezza
            self.btn_nuovo_comune_nel_tab.setEnabled(is_admin or is_archivista)

        tab_indices = {self.tabs.tabText(
            i): i for i in range(self.tabs.count())}

        # Abilitazione standard dei tab se l'utente è loggato e non è admin_offline
        consultazione_enabled = bool(
            self.logged_in_user_info and not is_admin_offline)
        inserimento_enabled = (
            is_admin or is_archivista) and not is_admin_offline
        # Anche archivisti vedono statistiche
        statistiche_enabled = (
            is_admin or is_archivista) and not is_admin_offline
        gestione_utenti_enabled = is_admin and not is_admin_offline
        # Solo admin normali per il tab Sistema, l'admin_offline lo gestiamo dopo
        sistema_enabled = is_admin

        if "Consultazione" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Consultazione"], consultazione_enabled)
        if "Inserimento e Gestione" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Inserimento e Gestione"], inserimento_enabled)
        if "Esportazioni" in tab_indices:
            # Anche consultatori esportano
            self.tabs.setTabEnabled(
                tab_indices["Esportazioni"], consultazione_enabled)
        if "Reportistica" in tab_indices:
            # Anche consultatori vedono report
            self.tabs.setTabEnabled(
                tab_indices["Reportistica"], consultazione_enabled)
        if "Statistiche e Viste" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Statistiche e Viste"], statistiche_enabled)
        if "Gestione Utenti" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Gestione Utenti"], gestione_utenti_enabled)

        # Gestione specifica per il tab "Sistema"
        if "Sistema" in tab_indices:
            if is_admin_offline:  # Se siamo in modalità setup DB
                # Abilita solo il tab Sistema
                self.tabs.setTabEnabled(tab_indices["Sistema"], True)
                # Seleziona automaticamente il tab Sistema e il sotto-tab Amministrazione DB
                self.tabs.setCurrentIndex(tab_indices["Sistema"])
                if hasattr(self, 'sistema_sub_tabs'):
                    admin_db_ops_tab_index = -1
                    for i in range(self.sistema_sub_tabs.count()):
                        if self.sistema_sub_tabs.tabText(i) == "Amministrazione DB":
                            admin_db_ops_tab_index = i
                            break
                    if admin_db_ops_tab_index != -1:
                        self.sistema_sub_tabs.setCurrentIndex(
                            admin_db_ops_tab_index)
            else:  # Utente admin normale loggato
                self.tabs.setTabEnabled(tab_indices["Sistema"], is_admin)

        # Disabilita tutti gli altri tab se siamo in modalità admin_offline e il pool non è inizializzato
        if is_admin_offline and hasattr(self, 'pool_initialized_successfully') and not self.pool_initialized_successfully:
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) != "Sistema":
                    self.tabs.setTabEnabled(i, False)

        # Logout button
        if hasattr(self, 'logout_button'):
            self.logout_button.setEnabled(
                not is_admin_offline and bool(self.logged_in_user_id))

    @pyqtSlot(int)
    def handle_comune_appena_inserito(self, nuovo_comune_id: int):
        self.logger.info(f"SLOT handle_comune_appena_inserito ESEGUITO per nuovo comune ID: {nuovo_comune_id}") # Log entrata slot
        if self.elenco_comuni_widget_ref is not None:
            self.logger.info(f"Riferimento a ElencoComuniWidget ({id(self.elenco_comuni_widget_ref)}) valido. Chiamata a load_comuni_data().")
            self.elenco_comuni_widget_ref.load_comuni_data()
        else:
            self.logger.warning("Riferimento a ElencoComuniWidget è None! Impossibile aggiornare la lista dei comuni.")
    def _handle_partita_creata_per_operazioni(self, nuova_partita_id: int, comune_id_partita: int,
                                              target_operazioni_widget: OperazioniPartitaWidget):
        """
        Slot per gestire la creazione di una nuova partita e il passaggio al tab
        delle operazioni collegate, pre-compilando l'ID.
        """
        logging.getLogger("CatastoGUI").info(
            f"Nuova Partita ID {nuova_partita_id} (Comune ID {comune_id_partita}) creata. Passaggio al tab Operazioni.")

        # Trova l'indice del tab principale "Inserimento e Gestione"
        idx_tab_inserimento = -1
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Inserimento e Gestione":
                idx_tab_inserimento = i
                break

        if idx_tab_inserimento != -1:
            # Vai al tab principale "Inserimento e Gestione"
            self.tabs.setCurrentIndex(idx_tab_inserimento)

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
                    self.inserimento_sub_tabs.setCurrentIndex(
                        idx_sotto_tab_operazioni)
                    # Chiama il metodo su OperazioniPartitaWidget per impostare l'ID
                    target_operazioni_widget.seleziona_e_carica_partita_sorgente(
                        nuova_partita_id)
                else:
                    logging.getLogger("CatastoGUI").error(
                        "Impossibile trovare il sotto-tab 'Operazioni su Partita' per il cambio automatico.")
            else:
                logging.getLogger("CatastoGUI").error(
                    "'self.inserimento_sub_tabs' non trovato in CatastoMainWindow.")
        else:
            logging.getLogger("CatastoGUI").error(
                "Impossibile trovare il tab principale 'Inserimento e Gestione'.")

    def update_ui_based_on_role(self):
        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        ruolo = None
        is_admin_offline_mode = False

        # Determina se siamo in modalità offline o se un utente è loggato
        if hasattr(self, 'pool_initialized_successfully') and not self.pool_initialized_successfully:
            if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin_offline':
                is_admin_offline_mode = True
                ruolo = 'admin_offline'  # Usa il ruolo fittizio

        if not is_admin_offline_mode and self.logged_in_user_info:
            ruolo = self.logged_in_user_info.get('ruolo')

        is_admin = ruolo == 'admin'
        is_archivista = ruolo == 'archivista'

        logging.getLogger("CatastoGUI").debug(
            f"update_ui_based_on_role: Ruolo effettivo considerato: {ruolo}, is_admin_offline: {is_admin_offline_mode}")

        # Abilitazione pulsante Nuovo Comune nel tab Inserimento (se esiste)
        if hasattr(self, 'btn_nuovo_comune_nel_tab'):
            can_add_comune = (
                is_admin or is_archivista) and not is_admin_offline_mode
            self.btn_nuovo_comune_nel_tab.setEnabled(can_add_comune)
            logging.getLogger("CatastoGUI").debug(
                f"Pulsante Nuovo Comune abilitato: {can_add_comune}")

        tab_indices = {self.tabs.tabText(
            i): i for i in range(self.tabs.count())}
        logging.getLogger("CatastoGUI").debug(
            f"Tab disponibili: {tab_indices}")

        # Logica di abilitazione dei tab
        # Se il pool non è inizializzato o siamo in admin_offline, la maggior parte dei tab è disabilitata
        # a meno che non sia il tab "Sistema".
        db_ready_for_normal_ops = hasattr(
            self, 'pool_initialized_successfully') and self.pool_initialized_successfully and not is_admin_offline_mode

        # Tutti gli utenti loggati (non offline)
        consultazione_enabled = db_ready_for_normal_ops
        inserimento_enabled = (
            is_admin or is_archivista) and db_ready_for_normal_ops
        statistiche_enabled = (
            is_admin or is_archivista) and db_ready_for_normal_ops
        gestione_utenti_enabled = is_admin and db_ready_for_normal_ops

        # Tab Sistema è accessibile per admin normali, o per admin_offline (per setup DB)
        sistema_enabled = is_admin or is_admin_offline_mode

        if "Consultazione" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Consultazione"], consultazione_enabled)
            logging.getLogger("CatastoGUI").debug(
                f"Tab Consultazione abilitato: {consultazione_enabled}")
        if "Inserimento e Gestione" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Inserimento e Gestione"], inserimento_enabled)
            logging.getLogger("CatastoGUI").debug(
                f"Tab Inserimento e Gestione abilitato: {inserimento_enabled}")
        if "Esportazioni" in tab_indices:
            self.tabs.setTabEnabled(
                # Anche consultatori
                tab_indices["Esportazioni"], consultazione_enabled)
            logging.getLogger("CatastoGUI").debug(
                f"Tab Esportazioni abilitato: {consultazione_enabled}")
        if "Reportistica" in tab_indices:
            self.tabs.setTabEnabled(
                # Anche consultatori
                tab_indices["Reportistica"], consultazione_enabled)
            logging.getLogger("CatastoGUI").debug(
                f"Tab Reportistica abilitato: {consultazione_enabled}")
        if "Statistiche e Viste" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Statistiche e Viste"], statistiche_enabled)
            logging.getLogger("CatastoGUI").debug(
                f"Tab Statistiche e Viste abilitato: {statistiche_enabled}")
        if "Gestione Utenti" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Gestione Utenti"], gestione_utenti_enabled)
            logging.getLogger("CatastoGUI").debug(
                f"Tab Gestione Utenti abilitato: {gestione_utenti_enabled}")

        if "Sistema" in tab_indices:
            self.tabs.setTabEnabled(tab_indices["Sistema"], sistema_enabled)
            logging.getLogger("CatastoGUI").debug(
                f"Tab Sistema abilitato: {sistema_enabled}")
            if sistema_enabled and is_admin_offline_mode:
                self.tabs.setCurrentIndex(tab_indices["Sistema"])
                if hasattr(self, 'sistema_sub_tabs'):
                    admin_db_ops_tab_index = -1
                    for i in range(self.sistema_sub_tabs.count()):
                        if self.sistema_sub_tabs.tabText(i) == "Amministrazione DB":
                            admin_db_ops_tab_index = i
                            break
                    if admin_db_ops_tab_index != -1:
                        self.sistema_sub_tabs.setCurrentIndex(
                            admin_db_ops_tab_index)
                        logging.getLogger("CatastoGUI").debug(
                            "Tab Sistema -> Amministrazione DB selezionato per modalità offline.")

        if hasattr(self, 'logout_button'):
            self.logout_button.setEnabled(
                not is_admin_offline_mode and bool(self.logged_in_user_id))

    def apri_dialog_inserimento_comune(self):  # Metodo integrato nella classe
        if not self.db_manager:
            QMessageBox.critical(
                self, "Errore", "Manager Database non inizializzato.")
            return
        if not self.logged_in_user_info:
            QMessageBox.warning(self, "Login Richiesto",
                                "Effettuare il login per procedere.")
            return

        ruolo_utente = self.logged_in_user_info.get('ruolo')
        if ruolo_utente not in ['admin', 'archivista']:
            QMessageBox.warning(self, "Accesso Negato",
                                "Non si dispone delle autorizzazioni necessarie per aggiungere un comune.")
            return

        utente_login_username = self.logged_in_user_info.get(
            'username', 'log_utente_sconosciuto')

        dialog = InserimentoComuneWidget(
            self.db_manager, utente_login_username, self)  # Passa 'self' come parent
        if dialog.exec_() == QDialog.Accepted:
            logging.getLogger("CatastoGUI").info(
                f"Dialogo inserimento comune chiuso con successo da utente '{utente_login_username}'.")
            QMessageBox.information(
                self, "Comune Aggiunto", "Il nuovo comune è stato registrato con successo.")
            # Aggiorna la vista dell'elenco comuni se presente nel tab consultazione
            # Questo ciclo cerca il widget ElencoComuniWidget tra i sotto-tab di consultazione
            if hasattr(self, 'consultazione_sub_tabs'):
                for i in range(self.consultazione_sub_tabs.count()):
                    widget = self.consultazione_sub_tabs.widget(i)
                    if isinstance(widget, ElencoComuniWidget):
                        widget.load_comuni_data()  # Assumendo che ElencoComuniWidget abbia questo metodo
                        logging.getLogger("CatastoGUI").info(
                            "Elenco comuni nel tab consultazione aggiornato.")
                        break
        else:
            logging.getLogger("CatastoGUI").info(
                f"Dialogo inserimento comune annullato da utente '{utente_login_username}'.")

    def _apri_dialogo_configurazione_db(self):
        logging.getLogger("CatastoGUI").info(
            "Apertura dialogo configurazione DB da menu.")
        current_config_for_dialog = {}
        settings = QSettings(QSettings.IniFormat, QSettings.UserScope,
                             "ArchivioDiStatoSavona", "CatastoStoricoApp")

        current_config_for_dialog[SETTINGS_DB_TYPE] = settings.value(
            SETTINGS_DB_TYPE, "Locale (localhost)")
        current_config_for_dialog[SETTINGS_DB_HOST] = settings.value(
            SETTINGS_DB_HOST, "localhost")
        # Fornisci un default stringa e converti qui per assicurare che il tipo sia corretto per int()
        # Leggi come stringa, default a stringa "5432"
        port_str_val = settings.value(SETTINGS_DB_PORT, "5432")
        try:
            current_config_for_dialog[SETTINGS_DB_PORT] = int(port_str_val)
        except (ValueError, TypeError):
            # Fallback se la stringa non è un intero valido
            current_config_for_dialog[SETTINGS_DB_PORT] = 5432
            logging.getLogger("CatastoGUI").warning(
                f"Valore porta non valido '{port_str_val}' letto da QSettings, usando default 5432.")

        current_config_for_dialog[SETTINGS_DB_NAME] = settings.value(
            SETTINGS_DB_NAME, "catasto_storico")
        current_config_for_dialog[SETTINGS_DB_USER] = settings.value(
            SETTINGS_DB_USER, "postgres")
        current_config_for_dialog[SETTINGS_DB_SCHEMA] = settings.value(
            SETTINGS_DB_SCHEMA, "catasto")

        config_dialog = DBConfigDialog(
            self, initial_config=current_config_for_dialog)
        if config_dialog.exec_() == QDialog.Accepted:
            # Le impostazioni sono state salvate dal dialogo stesso
            QMessageBox.information(self, "Configurazione Salvata",
                                    "Le impostazioni del database sono state aggiornate.\n"
                                    "È necessario riavviare l'applicazione per applicare le modifiche.")
            # Qui, il riavvio è la strada più semplice. Modificare un DBManager attivo
            # con un nuovo pool e nuovi parametri è complesso e soggetto a errori.

    def handle_logout(self):
        if self.logged_in_user_id is not None and self.current_session_id and self.db_manager:
            # Chiama il logout_user del db_manager passando l'ID utente e l'ID sessione correnti
            if self.db_manager.logout_user(self.logged_in_user_id, self.current_session_id, client_ip_address_gui):
                QMessageBox.information(self, "Logout", "Logout effettuato con successo.")
                logging.getLogger("CatastoGUI").info(f"Logout utente ID {self.logged_in_user_id}, sessione {self.current_session_id[:8]}... registrato nel DB.")
            else:
                # Anche se la registrazione DB fallisce, procedi con il logout lato client
                QMessageBox.warning(self, "Logout", "Logout effettuato. Errore durante la registrazione remota del logout.")
                logging.getLogger("CatastoGUI").warning(f"Logout utente ID {self.logged_in_user_id}, sessione {self.current_session_id[:8]}... Errore registrazione DB.")

            # Resetta le informazioni utente e sessione nella GUI
            self.logged_in_user_id = None
            self.logged_in_user_info = None
            self.current_session_id = None # IMPORTANTE: Resetta l'ID sessione

            # Non è necessario chiamare db_manager.clear_session_app_user() qui perché
            # db_manager.logout_user() dovrebbe già chiamare _clear_audit_session_variables_with_conn()
            # sulla connessione usata per aggiornare sessioni_accesso.

            self.user_status_label.setText("Utente: Nessuno")
            # Potresti voler cambiare lo stato del DB qui, ma di solito rimane "Connesso"
            # self.db_status_label.setText("Database: Connesso (Logout effettuato)") 
            self.logout_button.setEnabled(False)
            
            self.tabs.clear() # Rimuove tutti i tab
            # Potresti voler re-inizializzare i tab in uno stato "non loggato" o semplicemente chiudere.
            # Per ora, chiudiamo l'applicazione dopo il logout per semplicità.
            self.statusBar().showMessage("Logout effettuato. L'applicazione verrà chiusa.")
            
            # Chiude l'applicazione dopo un breve ritardo per permettere all'utente di leggere il messaggio
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, self.close) # Chiude dopo 1.5 secondi

        else:
            logging.getLogger("CatastoGUI").warning("Tentativo di logout senza una sessione utente valida o db_manager.")


    def closeEvent(self, event: QCloseEvent):
        logging.getLogger("CatastoGUI").info("Evento closeEvent intercettato in CatastoMainWindow.")
        
        if hasattr(self, 'db_manager') and self.db_manager:
            pool_era_attivo = self.db_manager.pool is not None

            if pool_era_attivo:
                # Se un utente è loggato con una sessione attiva, esegui il logout
                if self.logged_in_user_id is not None and self.current_session_id:
                    logging.getLogger("CatastoGUI").info(f"Chiusura applicazione: logout di sicurezza per utente ID {self.logged_in_user_id}, sessione {self.current_session_id[:8]}...")
                    self.db_manager.logout_user(self.logged_in_user_id, self.current_session_id, client_ip_address_gui)
                else:
                    # Se non c'è un utente loggato specifico o una sessione, ma il pool è attivo,
                    # potremmo comunque voler tentare una pulizia generica delle variabili di sessione sulla connessione usata per questo.
                    # Tuttavia, senza una sessione specifica, _clear_audit_session_variables_with_conn non ha senso.
                    # clear_audit_session_variables() (quella che prende una nuova connessione dal pool) potrebbe essere chiamata,
                    # ma è meno critica qui se non c'è una sessione utente attiva da invalidare.
                    # La cosa più importante è che logout_user chiami _clear_audit_session_variables_with_conn.
                    self.logger.info("Nessun utente/sessione attiva da loggare out esplicitamente, ma il pool era attivo.")
                    # Se db_manager.clear_audit_session_variables() è progettato per essere chiamato in modo sicuro
                    # anche se non c'è una sessione utente specifica (es. resetta per la prossima connessione),
                    # potresti chiamarlo. Altrimenti, è meglio affidarsi alla pulizia fatta da logout_user.
                    # self.db_manager.clear_audit_session_variables() # VALUTARE SE NECESSARIO QUI

            # Chiudi sempre il pool se esiste
            self.db_manager.close_pool()
            logging.getLogger("CatastoGUI").info("Tentativo di chiusura del pool di connessioni al database completato durante closeEvent.")
        else:
            logging.getLogger("CatastoGUI").warning("DB Manager non disponibile durante closeEvent o pool già None.")

        logging.getLogger("CatastoGUI").info("Applicazione GUI Catasto Storico terminata via closeEvent.")
        event.accept()

# --- Fine Classe CatastoMainWindow ---
def run_gui_app():
    app = QApplication(sys.argv)
    QApplication.setOrganizationName("ArchivioDiStatoSavona")
    QApplication.setApplicationName("CatastoStoricoApp")
    app.setStyleSheet(MODERN_STYLESHEET)

    # Questo avviso è meglio mostrarlo una volta che la finestra principale è visibile, se FPDF_AVAILABLE è False
    # dal file app_utils.py
    # if not FPDF_AVAILABLE:
    # QMessageBox.warning(None, "Avviso Dipendenza Mancante", ...)

    settings = QSettings(QSettings.IniFormat, QSettings.UserScope,
                         "ArchivioDiStatoSavona", "CatastoStoricoApp")

    db_manager_gui: Optional[CatastoDBManager] = None
    main_window_instance = CatastoMainWindow() # Crea istanza finestra principale

    retry_setup = True
    initial_setup_successful = False # Flag per controllare se l'app può procedere al loop eventi

    while retry_setup:
        retry_setup = False # Assume successo per questa iterazione, a meno di errori specifici
        active_db_config: Optional[Dict[str, Any]] = None

        # 1. Carica o chiedi configurazione DB
        if settings.contains(SETTINGS_DB_NAME) and settings.value(SETTINGS_DB_NAME, type=str).strip():
            gui_logger.info(f"Caricamento configurazione DB da QSettings: {settings.fileName()}")
            active_db_config = {
                # ... (logica per caricare da QSettings come nel tuo codice, assicurati che SETTINGS_DB_PORT sia gestito correttamente come int)
                "type": settings.value(SETTINGS_DB_TYPE, "Locale (localhost)"),
                "host": settings.value(SETTINGS_DB_HOST, "localhost"),
                "port": settings.value(SETTINGS_DB_PORT, 5432, type=int), # Leggi come int
                "dbname": settings.value(SETTINGS_DB_NAME, "catasto_storico"),
                "user": settings.value(SETTINGS_DB_USER, "postgres"),
                "schema": settings.value(SETTINGS_DB_SCHEMA, "catasto")
            }
        else:
            gui_logger.info("Nessuna configurazione DB valida. Apertura dialogo di configurazione iniziale.")
            config_dialog = DBConfigDialog(parent=None, initial_config=None)
            if config_dialog.exec_() == QDialog.Accepted:
                active_db_config = config_dialog.get_config_values()
                if not active_db_config or not active_db_config.get("dbname"):
                    QMessageBox.critical(None, "Errore Critico", "Configurazione DB non valida. L'applicazione si chiuderà.")
                    if db_manager_gui: db_manager_gui.close_pool() # Assicura chiusura se istanziato
                    sys.exit(1)
            else: # Dialogo di configurazione annullato
                gui_logger.info("Configurazione DB iniziale annullata dall'utente. Uscita.")
                if db_manager_gui: db_manager_gui.close_pool()
                sys.exit(0)
        
        gui_logger.info(f"Configurazione DB attiva: { {k:v for k,v in active_db_config.items() if k != 'password'} }")

        # 2. Chiedi password DB
        db_password, ok = QInputDialog.getText(None, "Autenticazione Database",
                                               f"Password per utente '{active_db_config['user']}'\nDB: '{active_db_config['dbname']}'@{active_db_config['host']}:{active_db_config['port']}",
                                               QLineEdit.Password)
        if not ok: # Utente ha annullato il dialogo password
            gui_logger.info("Inserimento password annullato dall'utente. Uscita.")
            if db_manager_gui: db_manager_gui.close_pool()
            sys.exit(0)
        # La password vuota è permessa, sarà il DB a validarla

        # 3. Istanzia/Re-istanzia DBManager e inizializza il pool
        if db_manager_gui and db_manager_gui.pool: # Chiudi pool precedente se si ritenta
            db_manager_gui.close_pool()
        
        db_manager_gui = CatastoDBManager(
            dbname=active_db_config["dbname"], user=active_db_config["user"], password=db_password,
            host=active_db_config["host"], port=active_db_config["port"], schema=active_db_config["schema"],
            application_name=f"CatastoAppGUI_{active_db_config['dbname']}", # Nome app specifico per il pool
            log_level=gui_logger.level # Usa lo stesso livello di log della GUI per il db_manager
        )
        main_window_instance.db_manager = db_manager_gui # Assegna alla finestra principale
        main_window_instance.pool_initialized_successfully = False # Resetta per questo tentativo

        # 4. Tentativo di inizializzare il pool principale
        if db_manager_gui.initialize_main_pool():
            main_window_instance.pool_initialized_successfully = True
            gui_logger.info(f"Pool per DB '{active_db_config['dbname']}' inizializzato con successo.")
            
            # 4.1. Procedi con il Login Utente normale
            login_dialog_success = False
            while not login_dialog_success: # Permetti di ritentare il login utente
                login_dialog = LoginDialog(db_manager_gui, parent=main_window_instance)
                if login_dialog.exec_() == QDialog.Accepted:
                    if login_dialog.logged_in_user_id is not None and login_dialog.current_session_id_from_dialog:
                        main_window_instance.perform_initial_setup(
                            db_manager_gui,
                            login_dialog.logged_in_user_id,
                            login_dialog.logged_in_user_info,
                            login_dialog.current_session_id_from_dialog
                        )
                        login_dialog_success = True
                        initial_setup_successful = True # L'app è pronta per il loop eventi
                        retry_setup = False # Successo, esci dal loop di configurazione DB
                    else: # Errore interno di LoginDialog dopo aver premuto OK
                        QMessageBox.critical(None, "Errore Login Interno", "Dati di login non validi dopo l'autenticazione. Riprovare.")
                        # Non uscire dall'app, lascia che l'utente ritenti il login o annulli
                        # login_dialog_success rimane False, quindi il loop di login continua
                else: # Utente ha annullato il LoginDialog
                    gui_logger.info("Login utente annullato. Uscita dall'applicazione.")
                    retry_setup = False # Esci dal loop di configurazione DB
                    initial_setup_successful = False # L'app non deve procedere
                    break # Esci dal loop di login
            
            if not login_dialog_success and not initial_setup_successful: # Se è uscito dal loop di login senza successo
                if db_manager_gui: db_manager_gui.close_pool()
                sys.exit(0)

        else: # initialize_main_pool() è fallito
            main_window_instance.pool_initialized_successfully = False
            db_target_name_failed = active_db_config.get("dbname", "N/D")
            host_failed = active_db_config.get("host", "N/D")
            gui_logger.error(f"Fallimento inizializzazione pool principale per DB '{db_target_name_failed}' su host '{host_failed}'.")

            # 4.2. Gestisci fallimento inizializzazione pool
            db_exists_on_server = db_manager_gui.check_database_exists(
                db_target_name_failed, active_db_config.get("user"), db_password
            )

            if not db_exists_on_server and host_failed.lower() in ["localhost", "127.0.0.1"]:
                gui_logger.warning(f"DB '{db_target_name_failed}' non trovato su server locale. Avvio in modalità setup limitata (admin_offline).")
                QMessageBox.information(None, "Database Non Trovato",
                                        f"Il database '{db_target_name_failed}' non sembra esistere sul server locale.\n"
                                        "L'applicazione verrà avviata in modalità limitata per permettere la creazione e configurazione del database tramite il tab 'Sistema -> Amministrazione DB'.")
                
                main_window_instance.logged_in_user_info = {'ruolo': 'admin_offline', 'id': 0, 'username': 'admin_setup', 'nome_completo': 'Admin Setup DB'}
                main_window_instance.logged_in_user_id = 0
                main_window_instance.current_session_id = str(uuid.uuid4()) # Sessione fittizia per admin_offline
                
                main_window_instance.perform_initial_setup(
                    db_manager_gui, 
                    main_window_instance.logged_in_user_id, 
                    main_window_instance.logged_in_user_info, 
                    main_window_instance.current_session_id
                )
                initial_setup_successful = True # L'app può partire in modalità limitata
                retry_setup = False 
            else: # DB esiste ma inaccessibile, o server remoto non risponde, o credenziali errate, ecc.
                error_msg_detail = f"Impossibile connettersi al database: '{db_target_name_failed}' su '{host_failed}'.\n"
                if db_exists_on_server:
                    error_msg_detail += "Il database sembra esistere, ma la connessione è fallita (verificare password, privilegi, stato server).\n"
                else:
                    error_msg_detail += "Il database potrebbe non esistere o il server non è raggiungibile.\n"
                error_msg_detail += "\nControllare i file di log per dettagli specifici sull'errore di connessione.\nVuoi modificare la configurazione e riprovare?"

                reply = QMessageBox.critical(None, "Errore Connessione Database",
                                             error_msg_detail,
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    retry_setup = True # Riprova il ciclo di configurazione DB
                    # DBConfigDialog verrà mostrato all'inizio del prossimo ciclo while
                else: # Utente sceglie di non riconfigurare
                    gui_logger.info("Uscita scelta dall'utente dopo fallimento connessione DB e nessuna riconfigurazione.")
                    initial_setup_successful = False
                    retry_setup = False # Esci dal loop

    # --- Fine Loop `while retry_setup` ---

    if initial_setup_successful:
        gui_logger.info("Setup iniziale completato. Avvio loop eventi dell'applicazione...")
        try:
            exit_code = app.exec_()
            gui_logger.info(f"Loop eventi applicazione terminato con codice: {exit_code}")
        except Exception as e_exec:
            gui_logger.critical(f"Errore imprevisto durante app.exec_(): {e_exec}", exc_info=True)
            # Assicura chiusura pool anche qui
            if db_manager_gui:
                db_manager_gui.close_pool()
            sys.exit(1) # Uscita con errore
    else:
        gui_logger.warning("Setup iniziale non completato con successo. L'applicazione non verrà avviata.")
        # Il pool potrebbe essere stato chiuso nei blocchi di errore precedenti se istanziato
        # Ma una chiamata sicura qui non fa male.
        if db_manager_gui:
            db_manager_gui.close_pool()
        sys.exit(1) # Uscita se il setup non è andato a buon fine

    # Chiusura finale del pool se non già fatto
    if db_manager_gui:
        db_manager_gui.close_pool()
    
    sys.exit(getattr(app, 'returnCode', 0) if 'app' in locals() and hasattr(app, 'returnCode') else 0)

if __name__ == "__main__":
    # Assicurati che il logger sia configurato prima di qualsiasi chiamata
    if not logging.getLogger("CatastoGUI").hasHandlers():
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
...  # (resto della configurazione del logger) ...

run_gui_app()
