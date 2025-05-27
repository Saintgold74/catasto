#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dialoghi e Widget per Gestionale Catasto Storico
================================================
Autore: Marco Santoro
Data: 18/05/2025
Versione: 1.2

Questo file contiene tutti i dialoghi e widget personalizzati
utilizzati dall'applicazione principale.
"""

import sys
import os
import logging
import getpass 
import json
import bcrypt
import csv
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
                            QInputDialog, QHeaderView,QFrame,QAbstractItemView,QSizePolicy,
                            QAction, QMenu,QFormLayout,QDialogButtonBox) 
from PyQt5.QtCore import Qt, QDate, QSettings, QDateTime
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QCloseEvent
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtCore import Qt, QDate, QSettings, QDateTime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGroupBox, QFormLayout, QApplication, QStyle,
                             QFileDialog, QTextEdit, QProgressBar, QMessageBox, QComboBox,
                             QLineEdit)
from PyQt5.QtCore import QProcess
from PyQt5.QtCore import Qt, QDate, QSettings, QDateTime
from PyQt5.QtCore import pyqtSignal

# Costanti per la configurazione delle tabelle
COLONNE_POSSESSORI_DETTAGLI_NUM = 6
COLONNE_POSSESSORI_DETTAGLI_LABELS = ["ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]
COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM = 5
COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS = ["ID", "Nome Completo", "Paternità", "Comune Rif.", "Num. Partite"]
COLONNE_INSERIMENTO_POSSESSORI_NUM = 4
COLONNE_INSERIMENTO_POSSESSORI_LABELS = ["ID", "Nome Completo", "Paternità", "Comune Riferimento"]
NUOVE_ETICHETTE_POSSESSORI = ["id", "nome_completo", "codice_fiscale", "data_nascita", "cognome_nome", "paternita", "indirizzo_residenza", "comune_residenza_nome", "attivo", "note", "num_partite"]

# Importazione FPDF per esportazione PDF
try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

# Importazione eccezioni personalizzate
try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass
    QMessageBox.warning(None, "Avviso Importazione", 
                         "Eccezioni DB personalizzate non trovate in catasto_db_manager, usando definizioni fallback.")

# Importazione CatastoDBManager
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

# --- Configurazione Logging per GUI ---
gui_logger = logging.getLogger("CatastoGUI")
if not gui_logger.hasHandlers():
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    gui_log_handler = logging.FileHandler("catasto_gui.log")
    gui_log_handler.setFormatter(logging.Formatter(log_format))
    
    if not getattr(sys, 'frozen', False): 
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_format))
        gui_logger.addHandler(console_handler)

    gui_logger.addHandler(gui_log_handler)
    gui_logger.setLevel(logging.INFO)

client_ip_address_gui: str = "127.0.0.1"

# --- Funzioni Helper per Password ---
def _hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

def _verify_password(stored_hash: str, provided_password: str) -> bool:
    try:
        stored_hash_bytes = stored_hash.encode('utf-8')
        provided_password_bytes = provided_password.encode('utf-8')
        return bcrypt.checkpw(provided_password_bytes, stored_hash_bytes)
    except ValueError:
        gui_logger.error(f"Tentativo di verifica con hash non valido: {stored_hash[:10]}...")
        return False
    except Exception as e:
        gui_logger.error(f"Errore imprevisto durante la verifica bcrypt: {e}")
        return False

def qdate_to_datetime(q_date: QDate) -> Optional[date]:
    if q_date.isNull() or not q_date.isValid():
        return None
    return date(q_date.year(), q_date.month(), q_date.day())

def datetime_to_qdate(dt_date: Optional[date]) -> QDate:
    if dt_date is None:
        return QDate()
    return QDate(dt_date.year, dt_date.month, dt_date.day)

# --- Classi PDF ---
if FPDF_AVAILABLE:
    class PDFPartita(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, 'Dettaglio Partita Catastale', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'B', 8)
            self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

        def chapter_title(self, title):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 6, title, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            self.ln(2)

        def chapter_body(self, data_dict):
            self.set_font('Helvetica', '', 10)
            page_width = self.w - self.l_margin - self.r_margin
            for key, value in data_dict.items():
                text_to_write = f"{key.replace('_', ' ').title()}: {value if value is not None else 'N/D'}"
                try:
                    self.multi_cell(page_width, 5, text_to_write, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                except Exception as e:
                    if "Not enough horizontal space" in str(e):
                        gui_logger.warning(f"FPDFException: {e} per il testo: {text_to_write[:100]}...")
                        self.multi_cell(page_width, 5, f"{key.replace('_', ' ').title()}: [ERRORE DATI TROPPO LUNGHI]", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    else:
                        raise e
            self.ln(2)

        def simple_table(self, headers, data_rows, col_widths_percent=None):
            self.set_font('Helvetica', 'B', 9)
            effective_page_width = self.w - self.l_margin - self.r_margin
            
            if col_widths_percent:
                col_widths = [effective_page_width * (p/100) for p in col_widths_percent]
            else:
                num_cols = len(headers)
                default_col_width = effective_page_width / num_cols if num_cols > 0 else effective_page_width
                col_widths = [default_col_width] * num_cols
            
            for i, header in enumerate(headers):
                align = 'C'
                if i == len(headers) - 1:
                    self.cell(col_widths[i], 7, header, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                else:
                    self.cell(col_widths[i], 7, header, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)

            self.set_font('Helvetica', '', 8)
            for row in data_rows:
                for i, item in enumerate(row):
                    text = str(item) if item is not None else ''
                    align = 'L'
                    if i == len(row) - 1:
                        self.cell(col_widths[i], 6, text, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                    else:
                        self.cell(col_widths[i], 6, text, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)
            self.ln(4)

    class PDFPossessore(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, 'Dettaglio Possessore Catastale', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, f'Pagina {self.page_no()}', border=0, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

        def chapter_title(self, title):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 6, title, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            self.ln(2)

        def chapter_body(self, data_dict):
            self.set_font('Helvetica', '', 10)
            page_width = self.w - self.l_margin - self.r_margin
            for key, value in data_dict.items():
                text_to_write = f"{key.replace('_', ' ').title()}: {value if value is not None else 'N/D'}"
                try:
                    self.multi_cell(page_width, 5, text_to_write, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                except Exception as e:
                    if "Not enough horizontal space" in str(e):
                        gui_logger.warning(f"FPDFException (chapter_body possessore): {e} per testo: {text_to_write[:100]}...")
                        self.multi_cell(page_width, 5, f"{key.replace('_', ' ').title()}: [DATI TROPPO LUNGHI]", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                    else: raise e
            self.ln(2)

        def simple_table(self, headers, data_rows, col_widths_percent=None):
            self.set_font('Helvetica', 'B', 9)
            effective_page_width = self.w - self.l_margin - self.r_margin
            
            if col_widths_percent:
                col_widths = [effective_page_width * (p/100) for p in col_widths_percent]
            else:
                num_cols = len(headers)
                default_col_width = effective_page_width / num_cols if num_cols > 0 else effective_page_width
                col_widths = [default_col_width] * num_cols

            for i, header in enumerate(headers):
                align = 'C'
                if i == len(headers) - 1:
                    self.cell(col_widths[i], 7, header, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                else:
                    self.cell(col_widths[i], 7, header, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)

            self.set_font('Helvetica', '', 8)
            for row in data_rows:
                for i, item in enumerate(row):
                    text = str(item) if item is not None else ''
                    align = 'L'
                    if i == len(row) - 1:
                        self.cell(col_widths[i], 6, text, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                    else:
                        self.cell(col_widths[i], 6, text, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)
            self.ln(4)
else:
    class PDFPartita: pass
    class PDFPossessore: pass

# --- Widget di Base ---
class QPasswordLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)

# --- Dialoghi di Login e Creazione Utente ---
class CreateUserDialog(QDialog):
    def __init__(self, db_manager, parent=None):
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
        self.password_edit = QPasswordLineEdit()
        self.password_edit.setPlaceholderText("Min. 6 caratteri")
        form_layout.addWidget(self.password_edit, 1, 1)

        form_layout.addWidget(QLabel("Conferma Password:"), 2, 0)
        self.confirm_edit = QPasswordLineEdit()
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
        self.ruolo_combo.addItems(["admin", "archivista", "consultatore"])
        form_layout.addWidget(self.ruolo_combo, 5, 1)

        frame_form = QFrame()
        frame_form.setLayout(form_layout)
        frame_form.setFrameShape(QFrame.StyledPanel)
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

        try:
            password_hash = _hash_password(password)

            if self.db_manager.create_user(username, password_hash, nome_completo, email, ruolo):
                QMessageBox.information(self, "Successo", f"Utente '{username}' creato con successo.")
                self.accept() 
            else:
                QMessageBox.critical(self, "Errore Database", 
                                     f"Impossibile creare l'utente '{username}'.\n"
                                     "Verificare che l'username non sia già in uso e controllare i log del database.")
        except Exception as e:
            QMessageBox.critical(self, "Errore Inaspettato", 
                                 f"Si è verificato un errore imprevisto: {e}")

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
                gui_logger.info(f"Login GUI OK per ID: {user_id_local}")
            else:
                QMessageBox.warning(self, "Login Fallito", "Password errata.")
                gui_logger.warning(f"Login GUI fallito (pwd errata) per ID: {user_id_local}")
                self.password_edit.selectAll()
                self.password_edit.setFocus()
                return
        else:
            QMessageBox.warning(self, "Login Fallito", "Utente non trovato o non attivo.")
            gui_logger.warning(f"Login GUI fallito (utente '{username}' non trovato/attivo).")
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
                self.logged_in_user_info = credentials
                self.current_session_id = session_id_returned

                if not self.db_manager.set_audit_session_variables(self.logged_in_user_id, self.current_session_id):
                    QMessageBox.critical(self, "Errore Audit", "Impossibile impostare le informazioni di sessione per l'audit.")

                QMessageBox.information(self, "Login Riuscito", 
                                        f"Benvenuto {self.logged_in_user_info.get('nome_completo', username)}!")
                self.accept()
            else:
                QMessageBox.critical(self, "Login Fallito", "Errore critico: Impossibile registrare la sessione di accesso.")
                gui_logger.error(f"Login GUI OK per ID {user_id_local} ma fallita reg. accesso.")

# --- Dialoghi di Selezione ---
class ComuneSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, parent=None, title="Seleziona Comune"):
        super(ComuneSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.selected_comune_id: Optional[int] = None
        self.selected_comune_name: Optional[str] = None
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        layout = QVBoxLayout(self)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Filtra comuni:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Digita per filtrare...")
        self.search_edit.textChanged.connect(self.filter_comuni)
        search_layout.addWidget(self.search_edit)
        
        self.search_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_BrowserReload), "")
        self.search_button.setToolTip("Aggiorna lista comuni")
        self.search_button.clicked.connect(self.filter_comuni)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        self.comuni_list = QListWidget()
        self.comuni_list.setAlternatingRowColors(True)
        self.comuni_list.itemDoubleClicked.connect(self.handle_select)
        layout.addWidget(self.comuni_list)
        
        buttons_layout = QHBoxLayout()
        self.select_button = QPushButton("Seleziona")
        self.select_button.setDefault(True)
        self.select_button.clicked.connect(self.handle_select)
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.select_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)
        
        self.load_comuni()

    def load_comuni(self, filter_text: Optional[str] = None):
        self.comuni_list.clear()
        try:
            comuni = self.db_manager.get_comuni(filter_text)
            if comuni:
                for comune in comuni:
                    item = QListWidgetItem(f"{comune['nome']} (ID: {comune['id']}, {comune['provincia']})")
                    item.setData(Qt.UserRole, comune['id'])
                    item.setData(Qt.UserRole + 1, comune['nome'])
                    self.comuni_list.addItem(item)
            else:
                self.comuni_list.addItem("Nessun comune trovato.")
        except Exception as e:
            gui_logger.error(f"Errore caricamento comuni nel dialogo: {e}")
            self.comuni_list.addItem("Errore caricamento comuni.")

    def filter_comuni(self):
        filter_text = self.search_edit.text().strip()
        self.load_comuni(filter_text if filter_text else None)

    def handle_select(self):
        current_item = self.comuni_list.currentItem()
        if current_item and current_item.data(Qt.UserRole) is not None:
            self.selected_comune_id = current_item.data(Qt.UserRole)
            self.selected_comune_name = current_item.data(Qt.UserRole + 1)
            self.accept()
        else:
            QMessageBox.warning(self, "Attenzione", "Seleziona un comune valido dalla lista.")

# Continua nel file catasto_gui_dialogs.py con tutti gli altri dialoghi e widget...
# Per brevità, includiamo qui solo alcuni esempi. Il file completo dovrebbe contenere:
# - PartitaSearchDialog
# - PossessoreSearchDialog
# - LocalitaSelectionDialog
# - ModificaPartitaDialog
# - ModificaPossessoreDialog
# - ModificaLocalitaDialog
# - DettagliLegamePossessoreDialog
# - PartitaDetailsDialog
# - PartiteComuneDialog
# - PossessoriComuneDialog
# - PeriodoStoricoDetailsDialog
# - UserSelectionDialog
# - PossessoreSelectionDialog
# - ImmobileDialog
# - Tutti i widget per i tab (RicercaPartiteWidget, RicercaPossessoriWidget, etc.)

# Export delle classi principali per l'importazione
__all__ = [
    'CreateUserDialog', 'LoginDialog', 'ComuneSelectionDialog',
    'gui_logger', 'client_ip_address_gui', '_hash_password', '_verify_password',
    'qdate_to_datetime', 'datetime_to_qdate', 'FPDF_AVAILABLE',
    'PDFPartita', 'PDFPossessore', 'QPasswordLineEdit',
    # Aggiungi qui tutte le altre classi che vuoi esportare
]