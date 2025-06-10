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
#from fuzzy_search_widget import add_complete_fuzzy_search_tab_to_main_window as add_fuzzy_search_tab_to_main_window
from fuzzy_search_widget import add_fuzzy_search_tab_to_main_window
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
                             QFormLayout, QDialogButtonBox, QFileDialog)
# Aggiunto QCloseEvent
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtCore import Qt, QSettings, pyqtSlot, QEvent, QObject, pyqtSignal
from PyQt5.QtWidgets import QAction, QApplication, QStyle
# In gui_main.py, dopo le importazioni PyQt e standard:
# E le sue eccezioni se servono qui
from catasto_db_manager import CatastoDBManager

# Dai nuovi moduli che creeremo:
from gui_widgets import (
    LandingPageWidget, ElencoComuniWidget, RicercaPartiteWidget,
    RicercaPossessoriWidget, RicercaAvanzataImmobiliWidget, InserimentoComuneWidget,
    InserimentoPossessoreWidget, InserimentoLocalitaWidget, RegistrazioneProprietaWidget,
    OperazioniPartitaWidget, EsportazioniWidget, ReportisticaWidget, StatisticheWidget,
    GestioneUtentiWidget, AuditLogViewerWidget, BackupRestoreWidget, AdminDBOperationsWidget,
    RegistraConsultazioneWidget, WelcomeScreen  # Aggiunto se non c'era
)
from gui_widgets import (
    DBConfigDialog, DettaglioPartitaDialog # Aggiungere qui
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
    # Aggiunto filename e lineno
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    gui_log_handler = logging.FileHandler(
        "catasto_gui.log", mode='a', encoding='utf-8')  # Aggiunto encoding e mode
    gui_log_handler.setFormatter(logging.Formatter(log_format))
    gui_logger.addHandler(gui_log_handler)
    # Imposta a DEBUG per più dettagli durante lo sviluppo
    gui_logger.setLevel(logging.DEBUG)

    # Esempio di Console Handler (per debug durante lo sviluppo)
    # if not getattr(sys, 'frozen', False): # Per non mostrare in console se è un eseguibile frozen
    #    console_handler = logging.StreamHandler(sys.stdout)
    #    console_handler.setFormatter(logging.Formatter(log_format))
    #    gui_logger.addHandler(console_handler)
client_ip_address_gui: str = "127.0.0.1"



class LoginDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super(LoginDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.logged_in_user_id: Optional[int] = None
        self.logged_in_user_info: Optional[Dict] = None
        # NUOVO attributo per conservare l'UUID
        self.current_session_id_from_dialog: Optional[str] = None

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
            QMessageBox.warning(self, "Login Fallito",
                                "Username e password sono obbligatori.")
            return

        credentials = self.db_manager.get_user_credentials(
            username)  # Presumiamo restituisca anche 'id' utente app
        login_success = False
        user_id_app = None  # ID utente dell'applicazione

        if credentials:
            # ID dell'utente dalla tabella 'utente'
            user_id_app = credentials.get('id')
            stored_hash = credentials.get('password_hash')
            is_active = credentials.get('attivo', False)

            if not is_active:
                QMessageBox.warning(self, "Login Fallito",
                                    "Utente non attivo.")
                logging.getLogger("CatastoGUI").warning(
                    f"Login GUI fallito (utente '{username}' non attivo).")
                return  # Non procedere oltre se l'utente non è attivo

            # Usa la tua funzione di verifica
            if stored_hash and _verify_password(stored_hash, password):
                login_success = True
                logging.getLogger("CatastoGUI").info(
                    f"Verifica password GUI OK per utente '{username}' (ID App: {user_id_app})")
            else:
                QMessageBox.warning(self, "Login Fallito",
                                    "Username o Password errati.")
                logging.getLogger("CatastoGUI").warning(
                    f"Login GUI fallito (pwd errata) per utente '{username}'.")
                self.password_edit.selectAll()
                self.password_edit.setFocus()
                return
        else:
            # Messaggio generico
            QMessageBox.warning(self, "Login Fallito",
                                "Username o Password errati.")
            logging.getLogger("CatastoGUI").warning(
                f"Login GUI fallito (utente '{username}' non trovato).")
            self.username_edit.selectAll()
            self.username_edit.setFocus()
            return

        if login_success and user_id_app is not None:
            try:
                # Chiamata a register_access (modificato in db_manager)
                # Ora dovrebbe restituire l'UUID della sessione
                session_uuid_returned = self.db_manager.register_access(
                    user_id=user_id_app,  # Passa l'ID dell'utente dell'applicazione
                    action='login',
                    esito=True,
                    # Assumendo che client_ip_address_gui sia definita globalmente o accessibile
                    indirizzo_ip=client_ip_address_gui,
                    application_name='CatastoAppGUI'
                )

                if session_uuid_returned:
                    self.logged_in_user_id = user_id_app
                    # Contiene tutti i dati dell'utente, incluso 'id'
                    self.logged_in_user_info = credentials
                    self.current_session_id_from_dialog = session_uuid_returned  # Salva l'UUID

                    # Imposta le variabili di sessione PostgreSQL per l'audit
                    # user_id_app è l'ID dell'utente da 'utente.id'
                    # session_uuid_returned è l'UUID dalla tabella 'sessioni_accesso.id_sessione'
                    if not self.db_manager.set_audit_session_variables(user_id_app, session_uuid_returned):
                        QMessageBox.critical(
                            self, "Errore Audit", "Impossibile impostare le informazioni di sessione per l'audit. Il login non può procedere.")
                        # Considera di non fare self.accept() qui se questo è un errore bloccante
                        return

                    QMessageBox.information(self, "Login Riuscito",
                                            f"Benvenuto {self.logged_in_user_info.get('nome_completo', username)}!")
                    self.accept()  # Chiude il dialogo e segnala successo
                else:
                    # register_access ha fallito nel restituire un session_id
                    QMessageBox.critical(
                        self, "Login Fallito", "Errore critico: Impossibile registrare la sessione di accesso nel database.")
                    logging.getLogger("CatastoGUI").error(
                        f"Login GUI OK per utente '{username}' ma fallita registrazione della sessione (nessun UUID sessione restituito).")

            except DBMError as e_dbm:  # Cattura DBMError da register_access o set_audit_session_variables
                QMessageBox.critical(
                    self, "Errore di Login (DB)", f"Errore durante il processo di login:\n{str(e_dbm)}")
                logging.getLogger("CatastoGUI").error(
                    f"DBMError durante il login per {username}: {str(e_dbm)}")
            except Exception as e_gen:  # Altri errori imprevisti
                QMessageBox.critical(
                    self, "Errore Imprevisto", f"Errore di sistema durante il login:\n{str(e_gen)}")
                logging.getLogger("CatastoGUI").error(
                    f"Errore imprevisto durante il login per {username}: {str(e_gen)}", exc_info=True)


try:
    from fuzzy_search_widget_expanded import ExpandedFuzzySearchWidget
    FUZZY_SEARCH_AVAILABLE = True
except ImportError as e:
    print(f"[INIT] Ricerca fuzzy non disponibile")
    FUZZY_SEARCH_AVAILABLE = False

class CatastoMainWindow(QMainWindow):
    def __init__(self):
        super(CatastoMainWindow, self).__init__()
        self.logger = logging.getLogger("CatastoGUI")
        self.db_manager: Optional[CatastoDBManager] = None
        self.logged_in_user_id: Optional[int] = None
        self.logged_in_user_info: Optional[Dict] = None
        self.current_session_id: Optional[str] = None
        # AGGIUNGI QUESTA RIGA PER INIZIALIZZARE L'ATTRIBUTO
        self.pool_initialized_successful: bool = False  # <--- AGGIUNTA

        # Inizializzazione dei QTabWidget per i sotto-tab se si usa questa organizzazione
        self.consultazione_sub_tabs = QTabWidget()
        self.inserimento_sub_tabs = QTabWidget()
        self.sistema_sub_tabs = QTabWidget()  # Deve essere inizializzato qui

        # Riferimenti ai widget specifici, inizializzati a None
        self.landing_page_widget: Optional[LandingPageWidget] = None
        self.elenco_comuni_widget_ref: Optional[ElencoComuniWidget] = None
        self.ricerca_partite_widget_ref: Optional[RicercaPartiteWidget] = None
        self.ricerca_possessori_widget_ref: Optional[RicercaPossessoriWidget] = None
        self.ricerca_avanzata_immobili_widget_ref: Optional[RicercaAvanzataImmobiliWidget] = None
        self.inserimento_comune_widget_ref: Optional[InserimentoComuneWidget] = None
        self.inserimento_possessore_widget_ref: Optional[InserimentoPossessoreWidget] = None
        self.inserimento_localita_widget_ref: Optional[InserimentoLocalitaWidget] = None
        self.registrazione_proprieta_widget_ref: Optional[RegistrazioneProprietaWidget] = None
        self.operazioni_partita_widget_ref: Optional[OperazioniPartitaWidget] = None
        self.registra_consultazione_widget_ref: Optional[RegistraConsultazioneWidget] = None
        self.esportazioni_widget_ref: Optional[EsportazioniWidget] = None
        self.reportistica_widget_ref: Optional[ReportisticaWidget] = None
        self.statistiche_widget_ref: Optional[StatisticheWidget] = None
        self.gestione_utenti_widget_ref: Optional[GestioneUtentiWidget] = None
        self.audit_viewer_widget_ref: Optional[AuditLogViewerWidget] = None
        self.backup_restore_widget_ref: Optional[BackupRestoreWidget] = None
        self.admin_db_ops_widget_ref: Optional[AdminDBOperationsWidget] = None

        self.initUI()

    def initUI(self):
        self.setWindowTitle(
            "Gestionale Catasto Storico - Archivio di Stato Savona")
        self.setMinimumSize(1280, 720)
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)

        self.create_status_bar_content()
        self.create_menu_bar()

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        self.setCentralWidget(self.central_widget)

        self.statusBar().showMessage("Pronto.")

    

    def perform_initial_setup(self, db_manager: CatastoDBManager,
                              # ID utente dell'applicazione
                              user_id: Optional[int],
                              user_info: Optional[Dict],   # Dettagli utente
                              session_id: Optional[str]):  # UUID della sessione
        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Inizio perform_initial_setup")
        self.db_manager = db_manager
        self.logged_in_user_id = user_id
        self.logged_in_user_info = user_info
        self.current_session_id = session_id  # Memorizza l'UUID della sessione

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

        if self.logged_in_user_info:  # Se l'utente è loggato
            user_display = self.logged_in_user_info.get(
                'nome_completo') or self.logged_in_user_info.get('username', 'N/D')
            ruolo_display = self.logged_in_user_info.get('ruolo', 'N/D')
            # L'ID utente è già in self.logged_in_user_id
            self.user_status_label.setText(
                f"Utente: {user_display} (ID: {self.logged_in_user_id}, Ruolo: {ruolo_display}, Sessione: {str(self.current_session_id)[:8]}...)")
            self.logout_button.setEnabled(True)
            self.statusBar().showMessage(
                f"Login come {user_display} effettuato con successo.")
        else:  # Modalità setup DB (admin_offline) o nessun login
            ruolo_fittizio = self.logged_in_user_info.get(
                'ruolo') if self.logged_in_user_info else None
            if ruolo_fittizio == 'admin_offline':
                self.user_status_label.setText(
                    f"Utente: Admin Setup (Sessione: {str(self.current_session_id)[:8]}...)")
                # L'admin_offline può fare "logout" per chiudere l'app
                self.logout_button.setEnabled(True)
                self.statusBar().showMessage("Modalità configurazione database.")
            # Nessun login valido, ma il pool potrebbe essere attivo (improbabile con flusso attuale)
            else:
                self.user_status_label.setText("Utente: Non Autenticato")
                self.logout_button.setEnabled(False)
                self.statusBar().showMessage("Pronto.")

        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Chiamata a setup_tabs")
        self.setup_tabs()
        # Integrazione ricerca fuzzy ampliata
        try:
            fuzzy_widget = integrate_expanded_fuzzy_search_widget(self, self.db_manager)
            print("✅ Ricerca fuzzy ampliata integrata con successo")
        except Exception as e:
            print(f"⚠️ Errore integrazione ricerca fuzzy: {e}")
        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        self.update_ui_based_on_role()

        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: Chiamata a self.show()")
        self.show()
        logging.getLogger("CatastoGUI").info(
            ">>> CatastoMainWindow: self.show() completato. Fine perform_initial_setup")

    # All'interno della classe CatastoMainWindow in prova.py

    def create_menu_bar(self):
        """
        Crea e popola la barra dei menu principale dell'applicazione.
        Versione compatibile con PyQt5.
        """
        menu_bar = self.menuBar()

        # --- 1. Crea i Menu Principali ---
        file_menu = menu_bar.addMenu("&File")
        settings_menu = menu_bar.addMenu("&Impostazioni")
        
        # --- 2. Definisci TUTTE le Azioni ---

        # Azione per importare da CSV
        import_action = QAction("Importa Possessori da CSV...", self)
        import_action.setStatusTip("Importa una lista di possessori da un file CSV")
        import_action.triggered.connect(self._import_possessori_csv) # Assicurati che il metodo _import_possessori_csv esista nella classe

        import_partite_action = QAction("Importa Partite da CSV...", self)
        import_partite_action.setStatusTip("Importa una lista di partite da un file CSV")
        import_partite_action.triggered.connect(self._import_partite_csv)
        # Azione per uscire
        exit_action = QAction(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton), "&Esci", self)
        exit_action.setStatusTip("Chiudi l'applicazione")
        exit_action.triggered.connect(self.close)

        # Azione per la configurazione del DB
        config_db_action = QAction(QApplication.style().standardIcon(QStyle.SP_ComputerIcon), "Configurazione &Database...", self)
        config_db_action.setStatusTip("Modifica i parametri di connessione al database")
        config_db_action.triggered.connect(self._apri_dialogo_configurazione_db) # Assicurati che anche questo metodo esista

        # --- 3. Aggiungi le Azioni ai Menu nell'ordine desiderato ---

        # Aggiungi azioni al menu "File"
        file_menu.addAction(import_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        file_menu.addAction(import_partite_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)


        # Aggiungi azioni al menu "Impostazioni"
        settings_menu.addAction(config_db_action)
        
        # Nota: Ho rimosso la parte relativa a "Nuovo Comune" che sembrava codice residuo
        # e poteva causare confusione o errori. Se ti serve, può essere aggiunta
        # di nuovo in modo strutturato.


    def create_status_bar_content(self):
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setFrameShadow(QFrame.Sunken)
        status_layout = QHBoxLayout(status_frame)

        self.db_status_label = QLabel("Database: Non connesso")
        self.user_status_label = QLabel("Utente: Nessuno")

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
        status_layout.addWidget(self.logout_button)
        self.main_layout.addWidget(status_frame)

    def perform_initial_setup(self, db_manager: CatastoDBManager,
                              user_id: Optional[int],
                              user_info: Optional[Dict],
                              session_id: Optional[str]):
        self.logger.info(">>> CatastoMainWindow: Inizio perform_initial_setup")
        self.db_manager = db_manager
        self.logged_in_user_id = user_id
        self.logged_in_user_info = user_info
        self.current_session_id = session_id

        db_name_configured = "N/Config"
        if self.db_manager:
            db_name_configured = self.db_manager.get_current_dbname() or "N/Config(None)"

        connection_status_text = ""
        # Questo controllo è ridondante se pool_initialized_successful è sempre inizializzato in __init__
        if hasattr(self, 'pool_initialized_successful'):
            if self.pool_initialized_successful:
                connection_status_text = f"Database: Connesso ({db_name_configured})"
            else:
                connection_status_text = f"Database: Non Pronto/Inesistente ({db_name_configured})"
        else:  # Questo ramo non dovrebbe più essere raggiunto se pool_initialized_successful è sempre inizializzato
            connection_status_text = f"Database: Stato Sconosciuto ({db_name_configured})"
        self.db_status_label.setText(connection_status_text)

        if self.logged_in_user_info:
            user_display = self.logged_in_user_info.get(
                'nome_completo') or self.logged_in_user_info.get('username', 'N/D')
            ruolo_display = self.logged_in_user_info.get('ruolo', 'N/D')
            self.user_status_label.setText(
                f"Utente: {user_display} (ID: {self.logged_in_user_id}, Ruolo: {ruolo_display}, Sessione: {str(self.current_session_id)[:8]}...)")
            self.logout_button.setEnabled(True)
            self.statusBar().showMessage(
                f"Login come {user_display} effettuato con successo.")
        else:
            ruolo_fittizio = self.logged_in_user_info.get(
                'ruolo') if self.logged_in_user_info else None
            if ruolo_fittizio == 'admin_offline':
                self.user_status_label.setText(
                    f"Utente: Admin Setup (Sessione: {str(self.current_session_id)[:8]}...)")
                self.logout_button.setEnabled(True)
                self.statusBar().showMessage("Modalità configurazione database.")
            else:
                self.user_status_label.setText("Utente: Non Autenticato")
                self.logout_button.setEnabled(False)
                self.statusBar().showMessage("Pronto.")

        self.logger.info(">>> CatastoMainWindow: Chiamata a setup_tabs")
        self.setup_tabs()
        self.logger.info(
            ">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        self.update_ui_based_on_role()

        self.logger.info(">>> CatastoMainWindow: Chiamata a self.show()")
        self.show()
        self.logger.info(
            ">>> CatastoMainWindow: self.show() completato. Fine perform_initial_setup")

    def setup_tabs(self):
        if not self.db_manager:
            self.logger.error(
                "Tentativo di configurare i tab senza un db_manager.")
            QMessageBox.critical(self, "Errore Critico",
                                 "DB Manager non inizializzato.")
            return

        self.tabs.clear()

        # Inizializza gli attributi self.xxxx_sub_tabs qui, se sono usati per contenere i sotto-tab
        # Esempio: self.consultazione_sub_tabs = QTabWidget()
        # Se non sono attributi di istanza, non serve self. qui, ma è meglio che lo siano per la coerenza
        # e per permettere a update_ui_based_on_role di accedervi.
        self.consultazione_sub_tabs = QTabWidget()
        self.inserimento_sub_tabs = QTabWidget()
        self.sistema_sub_tabs = QTabWidget()  # Assicurati sia inizializzato

        # --- 1. Landing Page (Primo Tab) ---
        self.landing_page_widget = LandingPageWidget(self.tabs)
        self.tabs.addTab(self.landing_page_widget, "🏠 Home")

        if self.landing_page_widget:
            self.landing_page_widget.apri_elenco_comuni_signal.connect(
                lambda: self.activate_tab_and_sub_tab("Consultazione e Modifica", "Principale"))
            self.landing_page_widget.apri_ricerca_partite_signal.connect(
                lambda: self.activate_tab_and_sub_tab("Consultazione e Modifica", "Ricerca Partite"))
            self.landing_page_widget.apri_ricerca_possessori_signal.connect(
                lambda: self.activate_tab_and_sub_tab("Consultazione e Modifica", "Ricerca Avanzata Possessori"))
            self.landing_page_widget.apri_registra_proprieta_signal.connect(
                lambda: self.activate_tab_and_sub_tab("Inserimento e Gestione", "Registrazione Proprietà"))
            self.landing_page_widget.apri_registra_possessore_signal.connect(
                lambda: self.activate_tab_and_sub_tab("Inserimento e Gestione", "Nuovo Possessore"))
            self.landing_page_widget.apri_registra_consultazione_signal.connect(
                lambda: self.activate_tab_and_sub_tab("Inserimento e Gestione", "Registra Consultazione"))
            # Correggi i nomi dei segnali per Reportistica, usando i nomi che hai dichiarato in gui_widgets.py
            self.landing_page_widget.apri_report_proprieta_signal.connect(
                lambda: self.activate_tab_and_sub_tab("Reportistica", "Report Proprietà", activate_report_sub_tab=True))
            self.landing_page_widget.apri_report_genealogico_signal.connect(lambda: self.activate_tab_and_sub_tab(
                "Reportistica", "Report Genealogico", activate_report_sub_tab=True))

        # --- 2. Tab Consultazione e Modifica ---
        self.elenco_comuni_widget_ref = ElencoComuniWidget(
            self.db_manager, self.consultazione_sub_tabs)
        self.consultazione_sub_tabs.addTab(
            self.elenco_comuni_widget_ref, "Principale")

        self.ricerca_partite_widget_ref = RicercaPartiteWidget(
            self.db_manager, self.consultazione_sub_tabs)
        self.consultazione_sub_tabs.addTab(
            self.ricerca_partite_widget_ref, "Ricerca Partite")

        self.ricerca_possessori_widget_ref = RicercaPossessoriWidget(
            self.db_manager, self.consultazione_sub_tabs)
        self.consultazione_sub_tabs.addTab(
            self.ricerca_possessori_widget_ref, "Ricerca Avanzata Possessori")

        self.ricerca_avanzata_immobili_widget_ref = RicercaAvanzataImmobiliWidget(
            self.db_manager, self.consultazione_sub_tabs)
        self.consultazione_sub_tabs.addTab(
            self.ricerca_avanzata_immobili_widget_ref, "Ricerca Immobili Avanzata")

        self.tabs.addTab(self.consultazione_sub_tabs,
                         "Consultazione e Modifica")

        # --- 3. Tab Inserimento e Gestione ---
        utente_per_inserimenti = self.logged_in_user_info if self.logged_in_user_info else {}
        inserimento_gestione_contenitore = QWidget()
        layout_contenitore_inserimento = QVBoxLayout(
            inserimento_gestione_contenitore)  # Corretto, ora usa il contenitore

        self.inserimento_comune_widget_ref = InserimentoComuneWidget(
            parent=self.inserimento_sub_tabs,  # Parent è il QTabWidget interno
            db_manager=self.db_manager,
            utente_attuale_info=utente_per_inserimenti
        )
        try:  # Disconnessione e Riconnessione del segnale per InserimentoComuneWidget
            self.inserimento_comune_widget_ref.comune_appena_inserito.disconnect(
                self.handle_comune_appena_inserito)
        except TypeError:
            pass  # Sollevato se il segnale non era connesso
        self.inserimento_comune_widget_ref.comune_appena_inserito.connect(
            self.handle_comune_appena_inserito)
        self.inserimento_sub_tabs.addTab(
            self.inserimento_comune_widget_ref, "Nuovo Comune")

        self.inserimento_possessore_widget_ref = InserimentoPossessoreWidget(
            self.db_manager, self.inserimento_sub_tabs)
        self.inserimento_sub_tabs.addTab(
            self.inserimento_possessore_widget_ref, "Nuovo Possessore")

        self.inserimento_localita_widget_ref = InserimentoLocalitaWidget(
            self.db_manager, self.inserimento_sub_tabs)
        self.inserimento_sub_tabs.addTab(
            self.inserimento_localita_widget_ref, "Nuova Località")

        self.registrazione_proprieta_widget_ref = RegistrazioneProprietaWidget(
            self.db_manager, self.inserimento_sub_tabs)
        self.inserimento_sub_tabs.addTab(
            self.registrazione_proprieta_widget_ref, "Registrazione Proprietà")

        self.operazioni_partita_widget_ref = OperazioniPartitaWidget(
            self.db_manager, self.inserimento_sub_tabs)
        self.inserimento_sub_tabs.addTab(
            self.operazioni_partita_widget_ref, "Operazioni Partita")

        if self.registrazione_proprieta_widget_ref and self.operazioni_partita_widget_ref:
            try:  # Disconnetti prima di riconnettere per evitare connessioni multiple
                self.registrazione_proprieta_widget_ref.partita_creata_per_operazioni_collegate.disconnect()
            except TypeError:
                pass
            self.registrazione_proprieta_widget_ref.partita_creata_per_operazioni_collegate.connect(
                lambda partita_id, comune_id: self._handle_partita_creata_per_operazioni(
                    partita_id, comune_id, self.operazioni_partita_widget_ref
                )
            )
            self.logger.info(
                "Segnale 'partita_creata_per_operazioni_collegate' connesso.")
        else:
            self.logger.error(
                "Impossibile connettere segnale partita_creata: widget non istanziati.")

        self.registra_consultazione_widget_ref = RegistraConsultazioneWidget(
            self.db_manager, self.logged_in_user_info, self.inserimento_sub_tabs)
        self.inserimento_sub_tabs.addTab(
            self.registra_consultazione_widget_ref, "Registra Consultazione")

        # Aggiungi i sotto-tab al layout del contenitore
        layout_contenitore_inserimento.addWidget(self.inserimento_sub_tabs)
        # Aggiungi il contenitore come tab principale
        self.tabs.addTab(inserimento_gestione_contenitore,
                         "Inserimento e Gestione")

        # --- 4. Tab Esportazioni ---
        self.esportazioni_widget_ref = EsportazioniWidget(
            self.db_manager, self)
        self.tabs.addTab(self.esportazioni_widget_ref, "Esportazioni")

        # --- 5. Tab Reportistica ---
        self.reportistica_widget_ref = ReportisticaWidget(
            self.db_manager, self)
        self.tabs.addTab(self.reportistica_widget_ref, "Reportistica")

        # --- 6. Tab Statistiche e Viste Materializzate ---
        self.statistiche_widget_ref = StatisticheWidget(self.db_manager, self)
        self.tabs.addTab(self.statistiche_widget_ref, "Statistiche e Viste")

        # --- 7. Tab Gestione Utenti (condizionale) ---
        if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin':
            self.gestione_utenti_widget_ref = GestioneUtentiWidget(
                self.db_manager, self.logged_in_user_info, self)
            self.tabs.addTab(self.gestione_utenti_widget_ref,
                             "Gestione Utenti")
        else:
            self.gestione_utenti_widget_ref = None

        # --- 8. Tab Sistema ---
        # Il contenitore per i sotto-tab di sistema
        sistema_contenitore = QWidget()
        # Assicurati che questo sia passato correttamente
        layout_contenitore_sistema = QVBoxLayout(sistema_contenitore)

        if self.db_manager:
            self.audit_viewer_widget_ref = AuditLogViewerWidget(
                self.db_manager, self.sistema_sub_tabs)
            self.sistema_sub_tabs.addTab(
                self.audit_viewer_widget_ref, "Log di Audit")

            self.backup_restore_widget_ref = BackupRestoreWidget(
                self.db_manager, self.sistema_sub_tabs)
            self.sistema_sub_tabs.addTab(
                self.backup_restore_widget_ref, "Backup/Ripristino DB")

            self.admin_db_ops_widget_ref = AdminDBOperationsWidget(
                self.db_manager, self.sistema_sub_tabs)
            self.sistema_sub_tabs.addTab(
                self.admin_db_ops_widget_ref, "Amministrazione DB")
        else:
            error_label = QLabel(
                "DB Manager non disponibile per i widget di sistema.")
            error_label.setAlignment(Qt.AlignCenter)
            self.sistema_sub_tabs.addTab(error_label, "Errore Sistema")

        # Aggiungi i sotto-tab al layout del contenitore
        layout_contenitore_sistema.addWidget(self.sistema_sub_tabs)
        # Aggiungi il contenitore come tab principale
        self.tabs.addTab(sistema_contenitore, "Sistema")

        # Imposta la Landing Page come tab attivo all'avvio
                # === AGGIUNTA TAB RICERCA FUZZY ===
        if FUZZY_SEARCH_AVAILABLE and self.db_manager:
            try:
                success = add_fuzzy_search_tab_to_main_window(self)
                if success:
                    print("✅ Tab ricerca fuzzy semplificato aggiunto")
                else:
                    print("⚠️ Errore aggiunta tab ricerca fuzzy")
            except Exception as e:
                print(f"⚠️ Errore ricerca fuzzy: {e}")

    # Nuovo metodo per attivare i tab e sotto-tab

    # main_tab_name, sub_tab_name, activate_report_sub_tab (opzionale)
    @pyqtSlot(str, str, bool)
    def activate_tab_and_sub_tab(self, main_tab_name: str, sub_tab_name: str, activate_report_sub_tab: bool = False):
        self.logger.info(
            f"Richiesta attivazione: Tab Principale='{main_tab_name}', Sotto-Tab='{sub_tab_name}'")

        main_tab_index = -1
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == main_tab_name:
                main_tab_index = i
                break

        if main_tab_index != -1:
            self.tabs.setCurrentIndex(main_tab_index)
            # Ora gestisci il sotto-tab
            main_tab_widget = self.tabs.widget(main_tab_index)
            # Se il tab principale contiene altri tab
            if isinstance(main_tab_widget, QTabWidget):
                sub_tab_index = -1
                for i in range(main_tab_widget.count()):
                    if main_tab_widget.tabText(i) == sub_tab_name:
                        sub_tab_index = i
                        break
                if sub_tab_index != -1:
                    main_tab_widget.setCurrentIndex(sub_tab_index)

                    # Logica specifica se si attiva un sotto-tab della Reportistica
                    if activate_report_sub_tab and main_tab_name == "Reportistica":
                        if hasattr(self, 'reportistica_widget_ref') and self.reportistica_widget_ref:
                            # Il widget ReportisticaWidget stesso è un QTabWidget
                            report_tabs = self.reportistica_widget_ref.findChild(
                                QTabWidget)  # Cerca il QTabWidget interno
                            if report_tabs:
                                target_report_tab_index = -1
                                for i in range(report_tabs.count()):
                                    # sub_tab_name qui è il nome del report specifico
                                    if report_tabs.tabText(i) == sub_tab_name:
                                        target_report_tab_index = i
                                        break
                                if target_report_tab_index != -1:
                                    report_tabs.setCurrentIndex(
                                        target_report_tab_index)
                                    self.logger.info(
                                        f"Attivato sotto-tab '{sub_tab_name}' in Reportistica.")
                                else:
                                    self.logger.warning(
                                        f"Sotto-tab report '{sub_tab_name}' non trovato in Reportistica.")
                            else:
                                self.logger.warning(
                                    "QTabWidget interno non trovato in ReportisticaWidget per attivare sotto-tab.")
                else:
                    self.logger.warning(
                        f"Sotto-tab '{sub_tab_name}' non trovato nel tab principale '{main_tab_name}'.")
            elif main_tab_widget is not None:  # Il tab principale è un widget diretto, non un QTabWidget
                self.logger.info(
                    f"Tab principale '{main_tab_name}' attivato (è un widget diretto).")
            else:
                self.logger.error(
                    f"Widget per il tab principale '{main_tab_name}' non trovato (None).")
        else:
            self.logger.error(f"Tab principale '{main_tab_name}' non trovato.")

    @pyqtSlot(int)
    def handle_comune_appena_inserito(self, nuovo_comune_id: int):
        self.logger.info(
            f"SLOT handle_comune_appena_inserito ESEGUITO per nuovo comune ID: {nuovo_comune_id}")
        if hasattr(self, 'elenco_comuni_widget_ref') and self.elenco_comuni_widget_ref:
            self.logger.info(
                f"Riferimento a ElencoComuniWidget ({id(self.elenco_comuni_widget_ref)}) valido. Chiamata a load_comuni_data().")
            self.elenco_comuni_widget_ref.load_comuni_data()
        else:
            self.logger.warning(
                "Riferimento a ElencoComuniWidget è None o non esiste! Impossibile aggiornare la lista dei comuni.")

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
        self.logger.info(
            ">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        ruolo = None
        is_admin_offline_mode = False

        # Determina se siamo in modalità offline o se un utente è loggato
        # La pool_initialized_successful è un attributo di CatastoMainWindow.
        # logged_in_user_info è un dizionario con i dettagli dell'utente.

        # Scenario 1: Modalità Admin Offline (DB non connesso in modo normale)
        # Questo si verifica quando self.pool_initialized_successful è False.
        if not self.pool_initialized_successful:
            if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin_offline':
                is_admin_offline_mode = True
                ruolo = 'admin_offline'  # Ruolo fittizio per la gestione UI in questa modalità
            else:
                # Se pool_initialized_successful è False ma non siamo admin_offline,
                # significa che la connessione è fallita e l'utente non ha scelto admin_offline.
                # In questo caso, nessun ruolo "normale" è valido per abilitare i tab.
                ruolo = None  # Nessun ruolo normale per abilitare i tab
        else:
            # Scenario 2: Database connesso normalmente
            if self.logged_in_user_info:
                ruolo = self.logged_in_user_info.get('ruolo')
            else:
                # Questo caso non dovrebbe succedere con il flusso attuale (dopo login, user_info non è None)
                # Ma per sicurezza, se non c'è user_info, il ruolo è None.
                ruolo = None

        is_admin = (ruolo == 'admin')
        is_archivista = (ruolo == 'archivista')
        is_consultatore = (ruolo == 'consultatore')

        self.logger.debug(
            f"update_ui_based_on_role: Ruolo effettivo considerato: {ruolo}, is_admin_offline: {is_admin_offline_mode}")

        # La logica di abilitazione dei tab principali si basa sul ruolo e sullo stato della connessione.
        # db_ready_for_normal_ops è True solo se il pool è inizializzato con successo E NON siamo in modalità admin_offline.
        db_ready_for_normal_ops = self.pool_initialized_successful and not is_admin_offline_mode

        # Determina lo stato di abilitazione per ciascun tipo di funzionalità
        # Consultazione e Modifica (Principale, Ricerca Partite, Ricerca Possessori, Ricerca Immobili Avanzata)
        consultazione_enabled = db_ready_for_normal_ops

        # Inserimento e Gestione (Nuovo Comune, Nuovo Possessore, Nuova Località, Registrazione Proprietà, Operazioni Partita, Registra Consultazione)
        inserimento_enabled = db_ready_for_normal_ops and (
            is_admin or is_archivista)

        # Esportazioni (Partita, Possessore)
        esportazioni_enabled = db_ready_for_normal_ops and (
            is_admin or is_archivista or is_consultatore)  # Tutti gli utenti normali

        # Reportistica (Report Proprietà, Genealogico, Possessore, Consultazioni)
        reportistica_enabled = db_ready_for_normal_ops and (
            is_admin or is_archivista or is_consultatore)  # Tutti gli utenti normali

        # Statistiche e Viste (Statistiche per Comune, Immobili per Tipologia, Manutenzione Database)
        statistiche_enabled = db_ready_for_normal_ops and (
            is_admin or is_archivista)  # Generalmente per ruoli più gestionali

        # Gestione Utenti (Solo per admin connessi normalmente)
        gestione_utenti_enabled = db_ready_for_normal_ops and is_admin

        # Sistema (Log di Audit, Backup/Ripristino DB, Amministrazione DB)
        # Accessibile per admin normali O per admin_offline (per setup DB iniziale)
        sistema_enabled = is_admin or is_admin_offline_mode

        # Applica lo stato di abilitazione ai tab
        tab_indices = {self.tabs.tabText(
            i): i for i in range(self.tabs.count())}

        if "Consultazione e Modifica" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Consultazione e Modifica"], consultazione_enabled)
            self.logger.debug(
                f"Tab 'Consultazione e Modifica' abilitato: {consultazione_enabled}")

        if "Inserimento e Gestione" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Inserimento e Gestione"], inserimento_enabled)
            self.logger.debug(
                f"Tab 'Inserimento e Gestione' abilitato: {inserimento_enabled}")

        if "Esportazioni" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Esportazioni"], esportazioni_enabled)
            self.logger.debug(
                f"Tab 'Esportazioni' abilitato: {esportazioni_enabled}")

        if "Reportistica" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Reportistica"], reportistica_enabled)
            self.logger.debug(
                f"Tab 'Reportistica' abilitato: {reportistica_enabled}")

        if "Statistiche e Viste" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Statistiche e Viste"], statistiche_enabled)
            self.logger.debug(
                f"Tab 'Statistiche e Viste' abilitato: {statistiche_enabled}")

        # Il tab "Gestione Utenti" è un tab diretto, non un sotto-tab. Se è stato aggiunto come tale.
        # Se invece è un sotto-tab di "Sistema", allora il controllo è sul sotto-tab specifico.
        # Data la tua struttura: self.tabs.addTab(self.gestione_utenti_widget_ref, "Gestione Utenti")
        if "Gestione Utenti" in tab_indices:
            self.tabs.setTabEnabled(
                tab_indices["Gestione Utenti"], gestione_utenti_enabled)
            self.logger.debug(
                f"Tab 'Gestione Utenti' abilitato: {gestione_utenti_enabled}")

        if "Sistema" in tab_indices:
            self.tabs.setTabEnabled(tab_indices["Sistema"], sistema_enabled)
            self.logger.debug(f"Tab 'Sistema' abilitato: {sistema_enabled}")

            # Se siamo in modalità admin_offline, forza la selezione del tab "Sistema" -> "Amministrazione DB"
            if sistema_enabled and is_admin_offline_mode:
                self.tabs.setCurrentIndex(tab_indices["Sistema"])
                if hasattr(self, 'sistema_sub_tabs'):
                    admin_db_ops_tab_index = -1
                    # Cerca il sotto-tab "Amministrazione DB" all'interno del QTabWidget self.sistema_sub_tabs
                    for i in range(self.sistema_sub_tabs.count()):
                        if self.sistema_sub_tabs.tabText(i) == "Amministrazione DB":
                            admin_db_ops_tab_index = i
                            break
                    if admin_db_ops_tab_index != -1:
                        self.sistema_sub_tabs.setCurrentIndex(
                            admin_db_ops_tab_index)
                        self.logger.debug(
                            "Tab 'Sistema' -> 'Amministrazione DB' selezionato per modalità offline.")
                    else:
                        self.logger.warning(
                            "Sotto-tab 'Amministrazione DB' non trovato nel tab 'Sistema'.")
                else:
                    self.logger.warning(
                        "self.sistema_sub_tabs non è un QTabWidget o non è stato inizializzato.")

        # Abilitazione/Disabilitazione del pulsante Logout
        if hasattr(self, 'logout_button'):
            self.logout_button.setEnabled(
                not is_admin_offline_mode and bool(self.logged_in_user_id))

        self.logger.info("update_ui_based_on_role completato.")

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
                            "Principale nel tab consultazione aggiornato.")
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
                QMessageBox.information(
                    self, "Logout", "Logout effettuato con successo.")
                logging.getLogger("CatastoGUI").info(
                    f"Logout utente ID {self.logged_in_user_id}, sessione {self.current_session_id[:8]}... registrato nel DB.")
            else:
                # Anche se la registrazione DB fallisce, procedi con il logout lato client
                QMessageBox.warning(
                    self, "Logout", "Logout effettuato. Errore durante la registrazione remota del logout.")
                logging.getLogger("CatastoGUI").warning(
                    f"Logout utente ID {self.logged_in_user_id}, sessione {self.current_session_id[:8]}... Errore registrazione DB.")

            # Resetta le informazioni utente e sessione nella GUI
            self.logged_in_user_id = None
            self.logged_in_user_info = None
            self.current_session_id = None  # IMPORTANTE: Resetta l'ID sessione

            # Non è necessario chiamare db_manager.clear_session_app_user() qui perché
            # db_manager.logout_user() dovrebbe già chiamare _clear_audit_session_variables_with_conn()
            # sulla connessione usata per aggiornare sessioni_accesso.

            self.user_status_label.setText("Utente: Nessuno")
            # Potresti voler cambiare lo stato del DB qui, ma di solito rimane "Connesso"
            # self.db_status_label.setText("Database: Connesso (Logout effettuato)")
            self.logout_button.setEnabled(False)

            self.tabs.clear()  # Rimuove tutti i tab
            # Potresti voler re-inizializzare i tab in uno stato "non loggato" o semplicemente chiudere.
            # Per ora, chiudiamo l'applicazione dopo il logout per semplicità.
            self.statusBar().showMessage("Logout effettuato. L'applicazione verrà chiusa.")

            # Chiude l'applicazione dopo un breve ritardo per permettere all'utente di leggere il messaggio
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, self.close)  # Chiude dopo 1.5 secondi

        else:
            logging.getLogger("CatastoGUI").warning(
                "Tentativo di logout senza una sessione utente valida o db_manager.")

    def closeEvent(self, event: QCloseEvent):
        logging.getLogger("CatastoGUI").info(
            "Evento closeEvent intercettato in CatastoMainWindow.")

        if hasattr(self, 'db_manager') and self.db_manager:
            pool_era_attivo = self.db_manager.pool is not None

            if pool_era_attivo:
                # Se un utente è loggato con una sessione attiva, esegui il logout
                if self.logged_in_user_id is not None and self.current_session_id:
                    logging.getLogger("CatastoGUI").info(
                        f"Chiusura applicazione: logout di sicurezza per utente ID {self.logged_in_user_id}, sessione {self.current_session_id[:8]}...")
                    self.db_manager.logout_user(
                        self.logged_in_user_id, self.current_session_id, client_ip_address_gui)
                else:
                    # Se non c'è un utente loggato specifico o una sessione, ma il pool è attivo,
                    # potremmo comunque voler tentare una pulizia generica delle variabili di sessione sulla connessione usata per questo.
                    # Tuttavia, senza una sessione specifica, _clear_audit_session_variables_with_conn non ha senso.
                    # clear_audit_session_variables() (quella che prende una nuova connessione dal pool) potrebbe essere chiamata,
                    # ma è meno critica qui se non c'è una sessione utente attiva da invalidare.
                    # La cosa più importante è che logout_user chiami _clear_audit_session_variables_with_conn.
                    self.logger.info(
                        "Nessun utente/sessione attiva da loggare out esplicitamente, ma il pool era attivo.")
                    # Se db_manager.clear_audit_session_variables() è progettato per essere chiamato in modo sicuro
                    # anche se non c'è una sessione utente specifica (es. resetta per la prossima connessione),
                    # potresti chiamarlo. Altrimenti, è meglio affidarsi alla pulizia fatta da logout_user.
                    # self.db_manager.clear_audit_session_variables() # VALUTARE SE NECESSARIO QUI

            # Chiudi sempre il pool se esiste
            self.db_manager.close_pool()
            logging.getLogger("CatastoGUI").info(
                "Tentativo di chiusura del pool di connessioni al database completato durante closeEvent.")
        else:
            logging.getLogger("CatastoGUI").warning(
                "DB Manager non disponibile durante closeEvent o pool già None.")

        logging.getLogger("CatastoGUI").info(
            "Applicazione GUI Catasto Storico terminata via closeEvent.")
        event.accept()

# --- Fine Classe CatastoMainWindow ---

    def _import_possessori_csv(self):
        """
        Gestisce il flusso di importazione: 1. Scegli Comune, 2. Scegli File, 3. Importa.
        """
        try:
            # --- PASSO 1: Chiedi all'utente di selezionare un comune ---
            comuni = self.db_manager.get_elenco_comuni_semplice()
            if not comuni:
                QMessageBox.warning(self, "Nessun Comune", "Nessun comune trovato nel database. Impossibile importare.")
                return

            # Crea una lista di nomi di comuni per il dialogo
            nomi_comuni = [c[1] for c in comuni]
            
            nome_comune_selezionato, ok = QInputDialog.getItem(
                self, 
                "Selezione Comune", 
                "A quale comune vuoi associare i nuovi possessori?",
                nomi_comuni, 
                0, # Indice iniziale
                False # Non editabile
            )
            
            if not ok or not nome_comune_selezionato:
                # L'utente ha premuto Annulla
                return

            # Trova l'ID del comune selezionato
            comune_id_selezionato = None
            for comun_id, comun_nome in comuni:
                if comun_nome == nome_comune_selezionato:
                    comune_id_selezionato = comun_id
                    break
            
            if comune_id_selezionato is None:
                # Non dovrebbe mai succedere, ma è una sicurezza
                QMessageBox.critical(self, "Errore", "Impossibile trovare l'ID del comune selezionato.")
                return

            # --- PASSO 2: Chiedi all'utente di selezionare il file CSV ---
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Seleziona il file CSV con i possessori",
                "",
                "File CSV (*.csv);;Tutti i file (*)"
            )

            if not file_path:
                return

            # --- PASSO 3: Avvia l'importazione ---
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            num_imported = self.db_manager.import_possessori_from_csv(file_path, comune_id_selezionato)
            
            QMessageBox.information(
                self,
                "Importazione Completata",
                f"Operazione completata con successo!\n\nSono stati importati {num_imported} nuovi possessori nel comune di {nome_comune_selezionato}."
            )
            # Qui puoi chiamare una funzione per aggiornare la vista
            # self.refresh_view()

        except Exception as e:
            QMessageBox.critical(self, "Errore durante l'importazione", f"Si è verificato un errore:\n\n{e}")
        finally:
            QApplication.restoreOverrideCursor()
    
    def _import_partite_csv(self):
        """
        Gestisce il flusso di importazione delle partite:
        1. Scegli Comune, 2. Scegli File, 3. Importa.
        """
        try:
            # Chiedi all'utente di selezionare un comune
            comuni = self.db_manager.get_elenco_comuni_semplice()
            if not comuni:
                QMessageBox.warning(self, "Nessun Comune", "Nessun comune trovato nel database. Impossibile importare.")
                return

            nomi_comuni = [c[1] for c in comuni]
            nome_comune_selezionato, ok = QInputDialog.getItem(
                self, "Selezione Comune", "A quale comune vuoi associare le nuove partite?", nomi_comuni, 0, False
            )
            if not ok or not nome_comune_selezionato:
                return

            comune_id_selezionato = next((cid for cid, cnome in comuni if cnome == nome_comune_selezionato), None)
            if comune_id_selezionato is None:
                QMessageBox.critical(self, "Errore", "Impossibile trovare l'ID del comune selezionato.")
                return

            # Chiedi all'utente di selezionare il file CSV
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Seleziona il file CSV con le partite", "", "File CSV (*.csv);;Tutti i file (*)"
            )
            if not file_path:
                return

            # Avvia l'importazione
            QApplication.setOverrideCursor(Qt.WaitCursor)
            num_imported = self.db_manager.import_partite_from_csv(file_path, comune_id_selezionato)
            
            QMessageBox.information(
                self, "Importazione Completata",
                f"Operazione completata con successo!\n\nSono state importate {num_imported} nuove partite nel comune di {nome_comune_selezionato}."
            )

        except Exception as e:
            QMessageBox.critical(self, "Errore durante l'importazione", f"Si è verificato un errore:\n\n{e}")
        finally:
            QApplication.restoreOverrideCursor()


    # --- PASSO 2: Modifica la funzione 'create_menu_bar' per aggiungere la nuova opzione ---

    # All'interno di create_menu_bar(self), trova dove definisci le azioni del menu "File".

    # Azione per importare possessori (già esistente)
    # import_possessori_action = QAction("Importa Possessori da CSV...", self)
    # import_possessori_action.triggered.connect(self._import_possessori_csv)

    # *** NUOVA AZIONE DA AGGIUNGERE SOTTO ***
    # Azione per importare partite
    #import_partite_action = QAction("Importa Partite da CSV...", self)
    #import_partite_action.setStatusTip("Importa una lista di partite da un file CSV")
    #import_partite_action.triggered.connect(self._import_partite_csv)


    # ... e poi, dove aggiungi le azioni al menu...

    # file_menu.addAction(import_possessori_action)
    # *** NUOVA RIGA DA AGGIUNGERE SOTTO ***
    # file_menu.addAction(import_partite_action)
    # file_menu.addSeparator()
    # file_menu.addAction(exit_action)

def run_gui_app():
    app = QApplication(sys.argv)
    QApplication.setOrganizationName("ArchivioDiStatoSavona")
    QApplication.setApplicationName("CatastoStoricoApp")
    app.setStyleSheet(MODERN_STYLESHEET)

    settings = QSettings(QSettings.IniFormat, QSettings.UserScope,
                         "ArchivioDiStatoSavona", "CatastoStoricoApp")

    db_manager_gui: Optional[CatastoDBManager] = None
    main_window_instance = CatastoMainWindow()

    base_dir_app = os.path.dirname(os.path.abspath(sys.argv[0]))
    logo_path_for_welcome = os.path.join(base_dir_app, "resources", "logo_meridiana.png")
    help_manual_url = "https://www.google.com/search?q=manuale+catasto_storico+online"

    # --- Nuovo Flusso di Avvio Semplificato ---
    while True: # Loop esterno che si ripete finché la connessione al DB principale non ha successo O l'utente esce/va in Admin Offline
        gui_logger.info("Avvio nuovo ciclo di connessione DB.")
        
        # 1. Apri il dialogo di configurazione DB. Questo dialogo è ora l'unico punto per modificare le impostazioni.
        # I valori iniziali del dialogo verranno caricati da QSettings, usando i default_preset_config se non salvati.
        config_dialog = DBConfigDialog(parent=None, allow_test_connection=True)
        
        if config_dialog.exec_() != QDialog.Accepted:
            # Se l'utente annulla la configurazione DB, esci dall'applicazione.
            gui_logger.info("Configurazione Database annullata dall'utente. Uscita dall'applicazione.")
            sys.exit(0)
        
        # L'utente ha cliccato "Salva e Connetti" nel dialogo.
        # Recupera i valori CORRENTI dal dialogo, inclusa la password che è stata inserita.
        current_db_config_values = config_dialog.get_config_values(include_password=True)

        # 2. Istanzia/Re-istanzia DBManager e tenta inizializzazione pool con i valori ottenuti.
        if db_manager_gui: # Chiudi il pool precedente se esiste
            db_manager_gui.close_pool()
        
        db_manager_gui = CatastoDBManager(
            dbname=current_db_config_values["dbname"],
            user=current_db_config_values["user"],
            password=current_db_config_values["password"],
            host=current_db_config_values["host"],
            port=current_db_config_values["port"],
            schema=current_db_config_values["schema"],
            application_name=f"CatastoAppGUI_{current_db_config_values['dbname']}",
            log_level=gui_logger.level
        )
        main_window_instance.db_manager = db_manager_gui
        main_window_instance.pool_initialized_successful = False # Resetta lo stato per questo tentativo


        # 3. Tentativo di inizializzare il pool principale
        if db_manager_gui.initialize_main_pool():
            main_window_instance.pool_initialized_successful = True
            gui_logger.info(f"Pool per DB '{current_db_config_values['dbname']}' inizializzato con successo.")
            
            # --- CONNESSO CON SUCCESSO: PROCEDI AL LOGIN UTENTE ---
            login_dialog = LoginDialog(db_manager_gui, parent=main_window_instance)
            if login_dialog.exec_() == QDialog.Accepted:
                if login_dialog.logged_in_user_id is not None and login_dialog.current_session_id_from_dialog:
                    # Login riuscito, mostra Welcome Screen
                    welcome_screen = WelcomeScreen(
                        parent=None,
                        logo_path=logo_path_for_welcome,
                        help_url=help_manual_url
                    )
                    welcome_screen_result = welcome_screen.exec_()

                    if welcome_screen_result == QDialog.Accepted:
                        gui_logger.info("Welcome Screen chiusa (Accepted).")
                        main_window_instance.perform_initial_setup(
                            db_manager_gui,
                            login_dialog.logged_in_user_id,
                            login_dialog.logged_in_user_info,
                            login_dialog.current_session_id_from_dialog
                        )
                        break # Esci dal loop esterno (setup completo e successo)

                    else: # Welcome Screen chiusa non "Accepted" (es. utente chiude X)
                        gui_logger.info("Welcome Screen chiusa (non Accepted). Uscita dall'applicazione.")
                        sys.exit(0)
                else: # Errore interno di LoginDialog (dati mancanti dopo accettazione)
                    QMessageBox.critical(None, "Errore Login Interno", "Dati di login non validi dopo l'autenticazione. Riprovare.")
                    continue # Torna all'inizio del loop esterno per riaprire DBConfigDialog e riprovare
            else: # LoginDialog annullato
                gui_logger.info("Login utente annullato. Uscita dall'applicazione.")
                sys.exit(0)
        
        else: # Inizializzazione pool fallita: Gestisci errori di connessione/autenticazione
            main_window_instance.pool_initialized_successful = False
            db_target_name_failed = current_db_config_values.get("dbname", "N/D")
            host_failed = current_db_config_values.get("host", "N/D")
            gui_logger.error(f"FALLIMENTO inizializzazione pool principale per DB '{db_target_name_failed}' su host '{host_failed}'.")

            # Analizza il tipo di errore per dare un feedback preciso all'utente
            last_db_error_message = ""
            # Questo approccio è solo una sicurezza; la funzione initialize_main_pool dovrebbe già loggare l'errore dettagliato.
            # Se vuoi un messaggio più specifico, puoi aggiungere un attributo per l'ultimo errore in CatastoDBManager.
            
            # Possibile miglioramento: CatastoDBManager potrebbe esporre l'ultimo errore di connessione.
            # Per ora, usiamo un messaggio generico o tentiamo di estrarre dal log, ma è meno robusto.
            
            # Per avere un messaggio più preciso qui, initialize_main_pool dovrebbe sollevare un'eccezione custom (DBConnectionError, DBAuthError)
            # o passare l'errore Psycopg2 specifico. Per ora, ci basiamo sulla stringa del messaggio.
            
            # Aggiunto log dettagliato per l'errore del pool in CatastoDBManager.initialize_main_pool()
            # La logica qui sotto analizza il messaggio di errore per presentare un QMessageBox più specifico.

            # Esempio di come potresti aver modificato initialize_main_pool per esporre l'errore:
            # try:
            #     conn_test = self.pool.getconn()
            #     # ... successo
            # except psycopg2.Error as pool_get_err:
            #     self._last_connect_error = pool_get_err # Salva l'errore nell'istanza
            #     # ... fallimento
            # Poi qui: last_db_error = db_manager_gui._last_connect_error

            # Poiché _last_connect_error non è standard, cerchiamo nel messaggio dell'errore (dal log)
            # O, meglio, db_manager_gui.initialize_main_pool() potrebbe catturare e passare l'errore Psycopg2.
            
            error_details_from_db_manager = db_manager_gui.get_last_connect_error_details() if hasattr(db_manager_gui, 'get_last_connect_error_details') else {}
            pgcode = error_details_from_db_manager.get('pgcode')
            pgerror_msg = error_details_from_db_manager.get('pgerror')

            if pgcode == '28P01' or ("password fallita" in str(pgerror_msg).lower() if pgerror_msg else False): # Codice per password sbagliata
                QMessageBox.critical(None, "Errore Autenticazione Database",
                                     "La password fornita per l'utente del database è sbagliata. "
                                     "Verificare la password e riprovare.",
                                     QMessageBox.Ok)
            elif pgcode == '08001' or ("timed out" in str(pgerror_msg).lower() if pgerror_msg else False) or ("connessione rifiutata" in str(pgerror_msg).lower() if pgerror_msg else False): # Codici per problemi di connessione
                 QMessageBox.critical(None, "Errore Connessione Database",
                                     f"Impossibile connettersi al database '{db_target_name_failed}' su '{host_failed}'. "
                                     "Il server potrebbe non essere in esecuzione, il firewall potrebbe bloccare la connessione, o l'indirizzo/porta sono errati. "
                                     "Verificare la configurazione del server PostgreSQL e del firewall.",
                                     QMessageBox.Ok)
            else:
                # Caso di fallback per errori generici o "DB non trovato"
                db_exists_on_server = False
                try:
                    db_exists_on_server = db_manager_gui.check_database_exists(
                        db_target_name_failed, current_db_config_values.get("user"), current_db_config_values.get("password")
                    )
                except Exception as e:
                    gui_logger.warning(f"Errore durante la verifica esistenza DB per modalità Admin Offline: {e}", exc_info=True)
                    db_exists_on_server = False # Se la verifica fallisce, assumi non esista o sia inaccessibile

                if not db_exists_on_server and host_failed.lower() in ["localhost", "127.0.0.1"]:
                    gui_logger.warning(f"DB '{db_target_name_failed}' non trovato su server locale. Avvio in modalità setup limitata (admin_offline).")
                    QMessageBox.information(None, "Database Non Trovato",
                                            f"Il database '{db_target_name_failed}' non sembra esistere sul server locale.\n"
                                            "L'applicazione verrà avviata in modalità limitata per permettere la creazione e configurazione del database tramite il tab 'Sistema -> Amministrazione DB'.")

                    main_window_instance.logged_in_user_info = {'ruolo': 'admin_offline', 'id': 0, 'username': 'admin_setup', 'nome_completo': 'Admin Setup DB'}
                    main_window_instance.logged_in_user_id = 0
                    main_window_instance.current_session_id = str(uuid.uuid4())
                    
                    main_window_instance.perform_initial_setup(
                        db_manager_gui,
                        main_window_instance.logged_in_user_id,
                        main_window_instance.logged_in_user_info,
                        main_window_instance.current_session_id
                    )
                    app.exec_() # Avvia il loop degli eventi per la modalità offline
                    sys.exit(0)
                else: # Errore generico di connessione o DB remoto non raggiungibile
                    QMessageBox.critical(None, "Errore Connessione Database",
                                         f"Errore generico di connessione al database. "
                                         "Verificare che il server sia raggiungibile, che le credenziali siano corrette e che il database esista.",
                                         QMessageBox.Ok)
            
            continue # Torna all'inizio del loop esterno per riaprire il DBConfigDialog con gli ultimi valori inseriti/salvati

    # --- Fine del flusso di avvio ---

    # Se l'applicazione è arrivata qui, significa che il setup è stato completato e la main_window_instance è stata mostrata.
    gui_logger.info("Setup iniziale completato. Avvio loop eventi dell'applicazione...")
    try:
        exit_code = app.exec_()
        gui_logger.info(f"Loop eventi applicazione terminato con codice: {exit_code}")
    except Exception as e_exec:
        gui_logger.critical(f"Errore imprevisto durante app.exec_(): {e_exec}", exc_info=True)
        if db_manager_gui:
            db_manager_gui.close_pool()
        sys.exit(1)

    if db_manager_gui:
        db_manager_gui.close_pool()
    
    sys.exit(getattr(app, 'returnCode', 0) if hasattr(app, 'returnCode') else 0)



if __name__ == "__main__":
    # Assicurati che il logger sia configurato prima di qualsiasi chiamata
    if not logging.getLogger("CatastoGUI").hasHandlers():
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
...  # (resto della configurazione del logger) ...

run_gui_app()
