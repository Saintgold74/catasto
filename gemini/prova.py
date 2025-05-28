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
                            QInputDialog, QHeaderView,QFrame,QAbstractItemView,QSizePolicy,QAction, QMenu,QFormLayout,QDialogButtonBox) 
from PyQt5.QtCore import Qt, QDate, QSettings 
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QCloseEvent # Aggiunto QCloseEvent
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtCore import Qt, QDate, QSettings, QDateTime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGroupBox, QFormLayout, QApplication, QStyle,
                             QFileDialog, QTextEdit, QProgressBar, QMessageBox, QComboBox,
                             QLineEdit) # Aggiunte QComboBox e QLineEdit per opzioni
from PyQt5.QtCore import QProcess # Per eseguire comandi esterni
import os # Per gestire percorsi# <--- ASSICURATI CHE QDateTime SIA PRESENTE
from PyQt5.QtCore import Qt, QDate, QSettings, QDateTime # Assicurati che QDateTime sia qui
from PyQt5.QtCore import pyqtSignal


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

# Importazione FPDF per esportazione PDF
try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    # QMessageBox.warning(None, "Avviso Dipendenza", "La libreria FPDF non è installata. L'esportazione in PDF non sarà disponibile.")
    # Non mostrare il messaggio qui, ma gestire la disabilitazione dei pulsanti PDF.
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
    if q_date.isNull() or not q_date.isValid(): # Controlla anche isValid
        return None
    return date(q_date.year(), q_date.month(), q_date.day())

def datetime_to_qdate(dt_date: Optional[date]) -> QDate:
    if dt_date is None:
        return QDate() # Restituisce una QDate "nulla"
    return QDate(dt_date.year, dt_date.month, dt_date.day)

class QPasswordLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        
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
            # Assicurati che gui_logger sia definito e accessibile globalmente o passato.
            # Se gui_logger non è disponibile, usa print() o logging standard.
            # logging.getLogger("CatastoGUI").error(f"Errore imprevisto durante la creazione dell'utente {username}: {e}")
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
                #    gui_logger.error("Impossibile impostare contesto DB post-login!")

                QMessageBox.information(self, "Login Riuscito", 
                                        f"Benvenuto {self.logged_in_user_info.get('nome_completo', username)}!")
                self.accept()
            else:
                QMessageBox.critical(self, "Login Fallito", "Errore critico: Impossibile registrare la sessione di accesso.")
                gui_logger.error(f"Login GUI OK per ID {user_id_local} ma fallita reg. accesso.")
class ComuneSelectionDialog(QDialog): # ASSICURATI CHE SIA QUI O PRIMA DI DOVE SERVE
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
        self.search_button.clicked.connect(self.filter_comuni) # Usa self.filter_comuni
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        self.comuni_list = QListWidget()
        self.comuni_list.setAlternatingRowColors(True)
        self.comuni_list.itemDoubleClicked.connect(self.handle_select) # Connessione corretta
        layout.addWidget(self.comuni_list)
        
        buttons_layout = QHBoxLayout()
        self.select_button = QPushButton("Seleziona")
        self.select_button.setDefault(True)
        self.select_button.clicked.connect(self.handle_select) # Connessione corretta
        
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
                    item.setData(Qt.UserRole + 1, comune['nome']) # Per recuperare il nome facilmente
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
            self.selected_comune_name = current_item.data(Qt.UserRole + 1) # Salva anche il nome
            self.accept()
        else:
            QMessageBox.warning(self, "Attenzione", "Seleziona un comune valido dalla lista.")








# --- Classi PDF (da python_example.py) ---
if FPDF_AVAILABLE:
    class PDFPartita(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, 'Dettaglio Partita Catastale', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'B', 8) # Cambiato in Bold per coerenza
            self.cell(0, 10, f'Pagina {self.page_no()}', border=0, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

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
                except Exception as e: # FPDFException non è definita se FPDF non è importato
                    if "Not enough horizontal space" in str(e):
                        gui_logger.warning(f"FPDFException: {e} per il testo: {text_to_write[:100]}...")
                        self.multi_cell(page_width, 5, f"{key.replace('_', ' ').title()}: [ERRORE DATI TROPPO LUNGHI]", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    else:
                        raise e
            self.ln(2) # Aggiungo un po' di spazio

        def simple_table(self, headers, data_rows, col_widths_percent=None):
            self.set_font('Helvetica', 'B', 9) # Header in grassetto
            effective_page_width = self.w - self.l_margin - self.r_margin
            
            if col_widths_percent:
                col_widths = [effective_page_width * (p/100) for p in col_widths_percent]
            else:
                num_cols = len(headers)
                default_col_width = effective_page_width / num_cols if num_cols > 0 else effective_page_width
                col_widths = [default_col_width] * num_cols
            
            for i, header in enumerate(headers):
                align = 'C' # Centra gli header
                if i == len(headers) - 1: # Ultima cella della riga header
                    self.cell(col_widths[i], 7, header, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                else:
                    self.cell(col_widths[i], 7, header, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)

            self.set_font('Helvetica', '', 8)
            for row in data_rows:
                for i, item in enumerate(row):
                    text = str(item) if item is not None else ''
                    align = 'L' # Dati allineati a sinistra
                    if i == len(row) - 1: # Ultima cella della riga dati
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
            self.set_font('Helvetica', 'I', 8) # Originale era 'I'
            self.cell(0, 10, f'Pagina {self.page_no()}', border=0, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

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
                except Exception as e: # FPDFException
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
else: # FPDF non disponibile
    class PDFPartita: pass # Definizioni vuote per evitare errori di NameError
    class PDFPossessore: pass


# --- Funzioni di esportazione adattate per GUI ---
def gui_esporta_partita_json(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    # Recupera i dati usando il metodo del db_manager che restituisce il dizionario completo
    # Questo metodo è get_partita_data_for_export, NON export_partita_json
    dict_data = db_manager.get_partita_data_for_export(partita_id) 
    
    if dict_data:
        # --- INIZIO MODIFICA ---
        def json_serial(obj):
            """JSON serializer per oggetti non serializzabili di default (date/datetime)."""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            # Potresti voler gestire altri tipi qui se necessario
            # Esempio per Decimal (se usi la libreria decimal):
            # from decimal import Decimal
            # if isinstance(obj, Decimal):
            #    return str(obj) # o float(obj) a seconda della precisione richiesta
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        
        try:
            json_data_str = json.dumps(dict_data, indent=4, ensure_ascii=False, default=json_serial)
        except TypeError as te:
            gui_logger.error(f"Errore di serializzazione JSON per partita ID {partita_id}: {te} - Dati: {dict_data}")
            QMessageBox.critical(parent_widget, "Errore di Serializzazione", 
                                 f"Errore durante la conversione dei dati della partita in JSON: {te}\n"
                                 "Controllare i log per i dettagli.")
            return
        # --- FINE MODIFICA ---

        default_filename = f"partita_{partita_id}_{date.today().isoformat()}.json"
        filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva JSON Partita", default_filename, "JSON Files (*.json)")
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_data_str)
                QMessageBox.information(parent_widget, "Esportazione JSON", f"Partita esportata con successo in:\n{filename}")
            except Exception as e:
                gui_logger.error(f"Errore durante il salvataggio del file JSON per partita ID {partita_id}: {e}")
                QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante il salvataggio del file JSON:\n{e}")
    else:
        QMessageBox.warning(parent_widget, "Errore Dati", f"Partita con ID {partita_id} non trovata o errore nel recupero dei dati per l'esportazione.")


def gui_esporta_partita_csv(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati partita non validi per l'esportazione CSV.")
        return

    default_filename = f"partita_{partita_id}_{date.today()}.csv"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva CSV Partita", default_filename, "CSV Files (*.csv)")
    if not filename: return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            p = partita_data['partita']
            writer.writerow(['--- DETTAGLI PARTITA ---'])
            for key, value in p.items(): writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])

            if partita_data.get('possessori'):
                writer.writerow(['--- POSSESSORI ---'])
                headers = list(partita_data['possessori'][0].keys()) if partita_data['possessori'] else []
                if headers: writer.writerow([h.replace('_', ' ').title() for h in headers])
                for pos in partita_data['possessori']: writer.writerow([pos.get(h) for h in headers])
                writer.writerow([])

            if partita_data.get('immobili'):
                writer.writerow(['--- IMMOBILI ---'])
                headers = list(partita_data['immobili'][0].keys()) if partita_data['immobili'] else []
                if headers: writer.writerow([h.replace('_', ' ').title() for h in headers])
                for imm in partita_data['immobili']: writer.writerow([imm.get(h) for h in headers])
                writer.writerow([])
            
            if partita_data.get('variazioni'):
                writer.writerow(['--- VARIAZIONI ---'])
                headers = list(partita_data['variazioni'][0].keys()) if partita_data['variazioni'] else []
                if headers: writer.writerow([h.replace('_', ' ').title() for h in headers])
                for var in partita_data['variazioni']: writer.writerow([var.get(h) for h in headers])
        QMessageBox.information(parent_widget, "Esportazione CSV", f"Partita esportata con successo in:\n{filename}")
    except Exception as e:
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione CSV:\n{e}")

def gui_esporta_partita_pdf(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    if not FPDF_AVAILABLE:
        QMessageBox.warning(parent_widget, "Funzionalità non disponibile", "La libreria FPDF è necessaria per l'esportazione in PDF, ma non è installata.")
        return
        
    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati partita non validi per l'esportazione PDF.")
        return

    default_filename = f"partita_{partita_id}_{date.today()}.pdf"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva PDF Partita", default_filename, "PDF Files (*.pdf)")
    if not filename: return

    try:
        pdf = PDFPartita()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        pdf.add_page()
        
        p = partita_data['partita']
        pdf.chapter_title('Dettagli Partita')
        pdf.chapter_body({k: p.get(k) for k in ['id', 'comune_nome', 'numero_partita', 'tipo', 'data_impianto', 'stato', 'data_chiusura', 'numero_provenienza']})

        if partita_data.get('possessori'):
            pdf.chapter_title('Possessori')
            headers = ['ID', 'Nome Completo', 'Titolo', 'Quota']
            data_rows = [[pos.get('id'), pos.get('nome_completo'), pos.get('titolo'), pos.get('quota')] for pos in partita_data['possessori']]
            pdf.simple_table(headers, data_rows)

        if partita_data.get('immobili'):
            pdf.chapter_title('Immobili')
            headers = ['ID', 'Natura', 'Località', 'Class.', 'Consist.']
            data_rows = [[imm.get('id'), imm.get('natura'), f"{imm.get('localita_nome','')} {imm.get('civico','')}".strip(), imm.get('classificazione'), imm.get('consistenza')] for imm in partita_data['immobili']]
            pdf.simple_table(headers, data_rows)

        if partita_data.get('variazioni'):
            pdf.chapter_title('Variazioni')
            headers = ['ID', 'Tipo', 'Data Var.', 'Contratto', 'Notaio']
            data_rows = []
            for var in partita_data['variazioni']:
                contr_str = f"{var.get('contratto_tipo','')} del {var.get('data_contratto','')}" if var.get('contratto_tipo') else ''
                data_rows.append([var.get('id'), var.get('tipo'), var.get('data_variazione'), contr_str, var.get('notaio')])
            pdf.simple_table(headers, data_rows)
            
        pdf.output(filename)
        QMessageBox.information(parent_widget, "Esportazione PDF", f"Partita esportata con successo in:\n{filename}")
    except Exception as e:
        gui_logger.exception("Errore esportazione PDF partita (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione PDF:\n{e}")


def gui_esporta_possessore_json(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    dict_data = db_manager.get_possessore_data_for_export(possessore_id)
    if dict_data:
        json_data_str = json.dumps(dict_data, indent=4, ensure_ascii=False)
        default_filename = f"possessore_{possessore_id}_{date.today()}.json"
        filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva JSON Possessore", default_filename, "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f: f.write(json_data_str)
                QMessageBox.information(parent_widget, "Esportazione JSON", f"Possessore esportato con successo in:\n{filename}")
            except Exception as e: QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante il salvataggio del file JSON:\n{e}")
    else: QMessageBox.warning(parent_widget, "Errore Dati", f"Possessore con ID {possessore_id} non trovato o errore recupero dati.")

def gui_esporta_possessore_csv(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati possessore non validi per l'esportazione CSV.")
        return

    default_filename = f"possessore_{possessore_id}_{date.today()}.csv"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva CSV Possessore", default_filename, "CSV Files (*.csv)")
    if not filename: return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            p_info = possessore_data['possessore']
            writer.writerow(['--- DETTAGLI POSSESSORE ---'])
            for key, value in p_info.items(): writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])

            if possessore_data.get('partite'): # La chiave è 'partite' dal JSON, non 'partite_associate'
                writer.writerow(['--- PARTITE ASSOCIATE ---'])
                headers = list(possessore_data['partite'][0].keys()) if possessore_data['partite'] else []
                if headers: writer.writerow([h.replace('_', ' ').title() for h in headers])
                for part in possessore_data['partite']: writer.writerow([part.get(h) for h in headers])
                writer.writerow([])
            
            if possessore_data.get('immobili'):
                writer.writerow(['--- IMMOBILI ASSOCIATI (TRAMITE PARTITE) ---'])
                headers = list(possessore_data['immobili'][0].keys()) if possessore_data['immobili'] else []
                if headers: writer.writerow([h.replace('_', ' ').title() for h in headers])
                for imm in possessore_data['immobili']: writer.writerow([imm.get(h) for h in headers])

        QMessageBox.information(parent_widget, "Esportazione CSV", f"Possessore esportato con successo in:\n{filename}")
    except Exception as e:
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione CSV:\n{e}")

def gui_esporta_possessore_pdf(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    if not FPDF_AVAILABLE:
        QMessageBox.warning(parent_widget, "Funzionalità non disponibile", "La libreria FPDF è necessaria per l'esportazione in PDF, ma non è installata.")
        return
        
    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati possessore non validi per l'esportazione PDF.")
        return

    default_filename = f"possessore_{possessore_id}_{date.today()}.pdf"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva PDF Possessore", default_filename, "PDF Files (*.pdf)")
    if not filename: return

    try:
        pdf = PDFPossessore()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        pdf.add_page()
        
        p_info = possessore_data['possessore']
        pdf.chapter_title('Dettagli Possessore')
        details_poss = {
            'ID Possessore': p_info.get('id'), 'Nome Completo': p_info.get('nome_completo'),
            'Comune Riferimento': p_info.get('comune_nome'), # Aggiunto comune_nome
            'Paternità': p_info.get('paternita'),
            'Stato': "Attivo" if p_info.get('attivo') else "Non Attivo",
        }
        pdf.chapter_body(details_poss)

        if possessore_data.get('partite'):
            pdf.chapter_title('Partite Associate')
            headers = ['ID Part.', 'Num. Partita', 'Comune', 'Tipo', 'Quota', 'Titolo']
            col_widths_percent = [10, 15, 25, 15, 15, 20] 
            data_rows = []
            for part in possessore_data['partite']:
                data_rows.append([
                    part.get('id'), part.get('numero_partita'), part.get('comune_nome'),
                    part.get('tipo'), part.get('quota'), part.get('titolo')
                ])
            pdf.simple_table(headers, data_rows, col_widths_percent=col_widths_percent)
        
        if possessore_data.get('immobili'):
            pdf.chapter_title('Immobili Associati (tramite Partite)')
            headers = ['ID Imm.', 'Natura', 'Località', 'Part. N.', 'Comune Part.']
            col_widths_percent_imm = [10, 30, 25, 15, 20]
            data_rows_imm = []
            for imm in possessore_data['immobili']:
                data_rows_imm.append([
                    imm.get('id'), imm.get('natura'), imm.get('localita_nome'),
                    imm.get('numero_partita'), imm.get('comune_nome')
                ])
            pdf.simple_table(headers, data_rows_imm, col_widths_percent_imm)

        pdf.output(filename)
        QMessageBox.information(parent_widget, "Esportazione PDF", f"Possessore esportato con successo in:\n{filename}")
    except Exception as e:
        gui_logger.exception("Errore esportazione PDF possessore (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione PDF:\n{e}")

# --- Widget per Esportazioni ---
class EsportazioniWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_partita_id_export: Optional[int] = None
        self.selected_possessore_id_export: Optional[int] = None

        main_layout = QVBoxLayout(self)
        
        # Sotto-Tab
        sub_tabs = QTabWidget()
        
        # Sotto-tab Esporta Partita
        esporta_partita_widget = QWidget()
        ep_layout = QVBoxLayout(esporta_partita_widget)
        
        ep_input_group = QGroupBox("Seleziona Partita da Esportare")
        ep_input_layout = QGridLayout(ep_input_group)
        ep_input_layout.addWidget(QLabel("ID Partita:"), 0, 0)
        self.partita_id_export_edit = QSpinBox()
        self.partita_id_export_edit.setMinimum(1); self.partita_id_export_edit.setMaximum(999999)
        ep_input_layout.addWidget(self.partita_id_export_edit, 0, 1)
        self.btn_cerca_partita_export = QPushButton("Cerca Partita...")
        self.btn_cerca_partita_export.clicked.connect(self._cerca_partita_per_export)
        ep_input_layout.addWidget(self.btn_cerca_partita_export, 0, 2)
        self.partita_info_export_label = QLabel("Nessuna partita selezionata.")
        ep_input_layout.addWidget(self.partita_info_export_label, 1, 0, 1, 3)
        ep_layout.addWidget(ep_input_group)

        ep_btn_layout = QHBoxLayout()
        self.btn_export_partita_json = QPushButton("Esporta JSON")
        self.btn_export_partita_json.clicked.connect(self._handle_export_partita_json)
        self.btn_export_partita_csv = QPushButton("Esporta CSV")
        self.btn_export_partita_csv.clicked.connect(self._handle_export_partita_csv)
        self.btn_export_partita_pdf = QPushButton("Esporta PDF")
        self.btn_export_partita_pdf.clicked.connect(self._handle_export_partita_pdf)
        self.btn_export_partita_pdf.setEnabled(FPDF_AVAILABLE) # Disabilita se FPDF non c'è
        ep_btn_layout.addWidget(self.btn_export_partita_json)
        ep_btn_layout.addWidget(self.btn_export_partita_csv)
        ep_btn_layout.addWidget(self.btn_export_partita_pdf)
        ep_layout.addLayout(ep_btn_layout)
        ep_layout.addStretch()
        sub_tabs.addTab(esporta_partita_widget, "Esporta Partita")

        # Sotto-tab Esporta Possessore
        esporta_possessore_widget = QWidget()
        eposs_layout = QVBoxLayout(esporta_possessore_widget)
        
        eposs_input_group = QGroupBox("Seleziona Possessore da Esportare")
        eposs_input_layout = QGridLayout(eposs_input_group)
        eposs_input_layout.addWidget(QLabel("ID Possessore:"), 0, 0)
        self.possessore_id_export_edit = QSpinBox()
        self.possessore_id_export_edit.setMinimum(1); self.possessore_id_export_edit.setMaximum(999999)
        eposs_input_layout.addWidget(self.possessore_id_export_edit, 0, 1)
        self.btn_cerca_possessore_export = QPushButton("Cerca Possessore...")
        self.btn_cerca_possessore_export.clicked.connect(self._cerca_possessore_per_export)
        eposs_input_layout.addWidget(self.btn_cerca_possessore_export, 0, 2)
        self.possessore_info_export_label = QLabel("Nessun possessore selezionato.")
        eposs_input_layout.addWidget(self.possessore_info_export_label, 1, 0, 1, 3)
        eposs_layout.addWidget(eposs_input_group)
        
        eposs_btn_layout = QHBoxLayout()
        self.btn_export_poss_json = QPushButton("Esporta JSON")
        self.btn_export_poss_json.clicked.connect(self._handle_export_possessore_json)
        self.btn_export_poss_csv = QPushButton("Esporta CSV")
        self.btn_export_poss_csv.clicked.connect(self._handle_export_possessore_csv)
        self.btn_export_poss_pdf = QPushButton("Esporta PDF")
        self.btn_export_poss_pdf.clicked.connect(self._handle_export_possessore_pdf)
        self.btn_export_poss_pdf.setEnabled(FPDF_AVAILABLE) # Disabilita se FPDF non c'è
        eposs_btn_layout.addWidget(self.btn_export_poss_json)
        eposs_btn_layout.addWidget(self.btn_export_poss_csv)
        eposs_btn_layout.addWidget(self.btn_export_poss_pdf)
        eposs_layout.addLayout(eposs_btn_layout)
        eposs_layout.addStretch()
        sub_tabs.addTab(esporta_possessore_widget, "Esporta Possessore")

        main_layout.addWidget(sub_tabs)

    def _cerca_partita_per_export(self):
        dialog = PartitaSearchDialog(self.db_manager, self) # Assumendo che PartitaSearchDialog esista e sia simile a quello per i report
        if dialog.exec_() == QDialog.Accepted and dialog.selected_partita_id:
            self.selected_partita_id_export = dialog.selected_partita_id
            self.partita_id_export_edit.setValue(self.selected_partita_id_export)
            # Potrebbe mostrare nome comune e numero partita
            partita_details = self.db_manager.get_partita_details(self.selected_partita_id_export)
            if partita_details:
                self.partita_info_export_label.setText(f"Selezionata: N. {partita_details.get('numero_partita')} (Comune: {partita_details.get('comune_nome')})")
            else:
                self.partita_info_export_label.setText("Partita non trovata.")
        else:
            self.selected_partita_id_export = None
            self.partita_info_export_label.setText("Nessuna partita selezionata.")


    def _handle_export_partita_json(self):
        partita_id = self.partita_id_export_edit.value()
        if partita_id > 0:
            gui_esporta_partita_json(self, self.db_manager, partita_id)
        else: QMessageBox.warning(self, "Selezione Mancante", "Inserisci o cerca un ID Partita valido.")

    def _handle_export_partita_csv(self):
        partita_id = self.partita_id_export_edit.value()
        if partita_id > 0:
            gui_esporta_partita_csv(self, self.db_manager, partita_id)
        else: QMessageBox.warning(self, "Selezione Mancante", "Inserisci o cerca un ID Partita valido.")

    def _handle_export_partita_pdf(self):
        partita_id = self.partita_id_export_edit.value()
        if partita_id > 0:
            gui_esporta_partita_pdf(self, self.db_manager, partita_id)
        else: QMessageBox.warning(self, "Selezione Mancante", "Inserisci o cerca un ID Partita valido.")

    def _cerca_possessore_per_export(self):
        gui_logger.info(">>> _cerca_possessore_per_export: Metodo chiamato.")
        
        dialog = PossessoreSelectionDialog(
            db_manager=self.db_manager, 
            comune_id=None, # Per ricerca globale
            parent=self
        )
        dialog.setWindowTitle("Seleziona Possessore per Esportazione")

        if dialog.exec_() == QDialog.Accepted:
            # --- MODIFICA QUI ---
            if hasattr(dialog, 'selected_possessore') and \
               dialog.selected_possessore and \
               isinstance(dialog.selected_possessore, dict) and \
               dialog.selected_possessore.get('id') is not None:
                
                self.selected_possessore_id_export = dialog.selected_possessore.get('id')
                self.possessore_id_export_edit.setValue(self.selected_possessore_id_export)
                
                nome_completo_sel = dialog.selected_possessore.get('nome_completo', 'N/D')
                # Per il nome del comune, potremmo dover fare una chiamata separata se non è già in selected_possessore
                # o se get_possessore_full_details lo restituisce in modo più affidabile.
                # Il dizionario 'selected_possessore' dovrebbe contenere anche 'comune_riferimento_nome' se
                # la query in PossessoreSelectionDialog (get_possessori_by_comune o search_possessori_by_term_globally)
                # lo include con un JOIN alla tabella comuni.
                # Altrimenti, recuperiamo i dettagli completi.
                
                comune_nome_sel = dialog.selected_possessore.get('comune_riferimento_nome', None)
                if comune_nome_sel is None: # Fallback se non presente in selected_possessore
                    details = self.db_manager.get_possessore_full_details(self.selected_possessore_id_export)
                    if details:
                        comune_nome_sel = details.get('comune_riferimento_nome', 'N/D')
                    else:
                        comune_nome_sel = 'N/D (dettagli non trovati)'
                
                self.possessore_info_export_label.setText(
                    f"Selezionato: {nome_completo_sel} (Comune Rif.: {comune_nome_sel}, ID: {self.selected_possessore_id_export})"
                )
                gui_logger.info(f"_cerca_possessore_per_export: Possessore selezionato ID {self.selected_possessore_id_export}")

            else: # selected_possessore non impostato o ID mancante
                self.selected_possessore_id_export = None
                self.possessore_id_export_edit.setValue(0) 
                self.possessore_info_export_label.setText("Nessun possessore selezionato o ID non valido.")
                gui_logger.warning("_cerca_possessore_per_export: Dialogo accettato ma 'selected_possessore' o il suo 'id' non validi.")
            # --- FINE MODIFICA ---
        else: # Dialogo annullato
            # Non resettare necessariamente la selezione precedente se l'utente annulla
            if self.selected_possessore_id_export is None: # Resetta solo se non c'era già una selezione valida
                self.possessore_id_export_edit.setValue(0)
                self.possessore_info_export_label.setText("Nessun possessore selezionato.")
            gui_logger.info("_cerca_possessore_per_export: Dialogo selezione annullato.")


    def _handle_export_possessore_json(self):
        possessore_id = self.possessore_id_export_edit.value()
        if possessore_id > 0:
            gui_esporta_possessore_json(self, self.db_manager, possessore_id)
        else: QMessageBox.warning(self, "Selezione Mancante", "Inserisci o cerca un ID Possessore valido.")
        
    def _handle_export_possessore_csv(self):
        possessore_id = self.possessore_id_export_edit.value()
        if possessore_id > 0:
            gui_esporta_possessore_csv(self, self.db_manager, possessore_id)
        else: QMessageBox.warning(self, "Selezione Mancante", "Inserisci o cerca un ID Possessore valido.")

    def _handle_export_possessore_pdf(self):
        possessore_id = self.possessore_id_export_edit.value()
        if possessore_id > 0:
            gui_esporta_possessore_pdf(self, self.db_manager, possessore_id)
        else: QMessageBox.warning(self, "Selezione Mancante", "Inserisci o cerca un ID Possessore valido.")
                # Non fare self.reject() qui, permette un altro tentativo o l'uscita manuale
# --- Finestra di Creazione Utente ---
# --- Finestra principale ---


# --- Widget per riepilogo dati immobili ---
class ImmobiliTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super(ImmobiliTableWidget, self).__init__(parent)
        
        # Impostazione colonne
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["ID", "Natura", "Classificazione", "Consistenza", "Località"])
        
        # Altre impostazioni
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSortingEnabled(True)
    
    def populate_data(self, immobili: List[Dict]):
        """Popola la tabella con i dati degli immobili."""
        self.setRowCount(0)  # Resetta la tabella
        
        for immobile in immobili:
            row_position = self.rowCount()
            self.insertRow(row_position)
            
            # Imposta i dati per ogni cella
            self.setItem(row_position, 0, QTableWidgetItem(str(immobile.get('id', ''))))
            self.setItem(row_position, 1, QTableWidgetItem(immobile.get('natura', '')))
            self.setItem(row_position, 2, QTableWidgetItem(immobile.get('classificazione', '')))
            self.setItem(row_position, 3, QTableWidgetItem(immobile.get('consistenza', '')))
            
            # Informazioni sulla località
            localita_text = ""
            if 'localita_nome' in immobile:
                localita_text = immobile['localita_nome']
                if 'civico' in immobile and immobile['civico'] is not None:
                    localita_text += f", {immobile['civico']}"
                if 'localita_tipo' in immobile:
                    localita_text += f" ({immobile['localita_tipo']})"
            
            self.setItem(row_position, 4, QTableWidgetItem(localita_text))
        
        # Adatta le dimensioni delle colonne al contenuto
        self.resizeColumnsToContents()

# --- Schede specifiche per Consultazione ---
class RicercaPartiteWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(RicercaPartiteWidget, self).__init__(parent)
        self.db_manager = db_manager
        
        layout = QVBoxLayout()
        
        # Criteri di ricerca
        criteria_group = QGroupBox("Criteri di Ricerca")
        criteria_layout = QGridLayout()
        
        # Comune
        comune_label = QLabel("Comune:")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_id = None
        self.comune_display = QLabel("Nessun comune selezionato")
        self.clear_comune_button = QPushButton("Cancella")
        self.clear_comune_button.clicked.connect(self.clear_comune)
        
        criteria_layout.addWidget(comune_label, 0, 0)
        criteria_layout.addWidget(self.comune_button, 0, 1)
        criteria_layout.addWidget(self.comune_display, 0, 2)
        criteria_layout.addWidget(self.clear_comune_button, 0, 3)
        
        # Numero partita
        numero_label = QLabel("Numero Partita:")
        self.numero_edit = QSpinBox()
        self.numero_edit.setMinimum(0)
        self.numero_edit.setMaximum(9999)
        self.numero_edit.setSpecialValueText("Qualsiasi")
        
        criteria_layout.addWidget(numero_label, 1, 0)
        criteria_layout.addWidget(self.numero_edit, 1, 1)
        
        # Possessore
        possessore_label = QLabel("Nome Possessore:")
        self.possessore_edit = QLineEdit()
        self.possessore_edit.setPlaceholderText("Qualsiasi possessore")
        
        criteria_layout.addWidget(possessore_label, 2, 0)
        criteria_layout.addWidget(self.possessore_edit, 2, 1, 1, 3)
        
        # Natura immobile
        natura_label = QLabel("Natura Immobile:")
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Qualsiasi natura immobile")
        
        criteria_layout.addWidget(natura_label, 3, 0)
        criteria_layout.addWidget(self.natura_edit, 3, 1, 1, 3)
        
        criteria_group.setLayout(criteria_layout)
        layout.addWidget(criteria_group)
        
        # Pulsante Ricerca
        search_button = QPushButton("Cerca Partite")
        search_button.clicked.connect(self.do_search)
        layout.addWidget(search_button)
        
        # Risultati
        results_group = QGroupBox("Risultati")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["ID", "Comune", "Numero", "Tipo", "Stato"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        results_layout.addWidget(self.results_table)
        
        # Dettagli partita selezionata
        self.detail_button = QPushButton("Mostra Dettagli Partita")
        self.detail_button.clicked.connect(self.show_details)
        results_layout.addWidget(self.detail_button)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        self.setLayout(layout)
    
    def select_comune(self):
        """Apre il selettore di comuni."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)
    
    def clear_comune(self):
        """Cancella il comune selezionato."""
        self.comune_id = None
        self.comune_display.setText("Nessun comune selezionato")
    
    def do_search(self):
        """Esegue la ricerca partite in base ai criteri."""
        comune_id = self.comune_id
        numero_partita_val = self.numero_edit.value()
        numero_partita = numero_partita_val if numero_partita_val > 0 and self.numero_edit.text() != self.numero_edit.specialValueText() else None
        
        possessore = self.possessore_edit.text().strip() or None
        natura = self.natura_edit.text().strip() or None
        
        # --- Stampa di DEBUG dei parametri inviati ---
        gui_logger.debug(f"RicercaPartiteWidget.do_search - Parametri inviati al DBManager:")
        gui_logger.debug(f"  comune_id: {comune_id} (tipo: {type(comune_id)})")
        gui_logger.debug(f"  numero_partita: {numero_partita} (tipo: {type(numero_partita)})")
        gui_logger.debug(f"  possessore: '{possessore}' (tipo: {type(possessore)})")
        gui_logger.debug(f"  immobile_natura: '{natura}' (tipo: {type(natura)})")
        # --- Fine Stampa di DEBUG ---
        
        try:
            partite = self.db_manager.search_partite(
                comune_id=comune_id,
                numero_partita=numero_partita,
                possessore=possessore,
                immobile_natura=natura
            )
            
            # --- Stampa di DEBUG dei risultati ricevuti ---
            gui_logger.debug(f"RicercaPartiteWidget.do_search - Risultati ricevuti dal DBManager (tipo: {type(partite)}):")
            if partite is not None: # Controlla se partite è None prima di len()
                gui_logger.debug(f"  Numero di partite ricevute: {len(partite)}")
                # Se vuoi vedere i primi risultati per debug (attenzione con dati sensibili):
                # for i, p_item in enumerate(partite[:3]): # Logga al massimo i primi 3
                #    gui_logger.debug(f"    Partita {i}: {p_item}")
            else:
                gui_logger.debug("  Nessun risultato (variabile 'partite' è None).")
            # --- Fine Stampa di DEBUG ---

            self.results_table.setRowCount(0) # Pulisce la tabella prima di popolarla
            
            if partite: # Verifica se la lista 'partite' non è vuota
                self.results_table.setRowCount(len(partite))
                for row_idx, partita_data in enumerate(partite): # Usa nomi variabili chiari
                    # Popolamento tabella come da suo codice esistente
                    self.results_table.setItem(row_idx, 0, QTableWidgetItem(str(partita_data.get('id', ''))))
                    self.results_table.setItem(row_idx, 1, QTableWidgetItem(partita_data.get('comune_nome', '')))
                    self.results_table.setItem(row_idx, 2, QTableWidgetItem(str(partita_data.get('numero_partita', ''))))
                    self.results_table.setItem(row_idx, 3, QTableWidgetItem(partita_data.get('tipo', '')))
                    self.results_table.setItem(row_idx, 4, QTableWidgetItem(partita_data.get('stato', '')))
                self.results_table.resizeColumnsToContents() # Adatta le colonne al contenuto
                QMessageBox.information(self, "Ricerca Completata", f"Trovate {len(partite)} partite corrispondenti ai criteri.")
            else:
                gui_logger.info("RicercaPartiteWidget.do_search - Nessuna partita trovata o la lista risultati è vuota.")
                QMessageBox.information(self, "Ricerca Completata", "Nessuna partita trovata con i criteri specificati.")

        except Exception as e:
            gui_logger.error(f"Errore imprevisto durante RicercaPartiteWidget.do_search: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore di Ricerca", f"Si è verificato un errore imprevisto durante la ricerca: {e}")

    
    def show_details(self):
        """Mostra i dettagli della partita selezionata."""
        # Ottiene l'ID della partita selezionata
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Attenzione", "Seleziona una partita dalla lista.")
            return
        
        # Ottiene l'ID dalla prima colonna della riga selezionata
        row = selected_items[0].row()
        partita_id_item = self.results_table.item(row, 0)
        
        if partita_id_item and partita_id_item.text().isdigit():
            partita_id = int(partita_id_item.text())
            
            # Ottiene i dettagli della partita
            partita = self.db_manager.get_partita_details(partita_id)
            
            if partita:
                # Crea e mostra una finestra di dialogo per i dettagli
                details_dialog = PartitaDetailsDialog(partita, self)
                details_dialog.exec_()
            else:
                QMessageBox.warning(self, "Errore", f"Non è stato possibile recuperare i dettagli della partita ID {partita_id}.")
        else:
            QMessageBox.warning(self, "Errore", "ID partita non valido.")
class RicercaPossessoriWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        main_layout = QVBoxLayout(self)
        
        # --- Gruppo per i Criteri di Ricerca ---
        search_criteria_group = QGroupBox("Criteri di Ricerca Possessori")
        criteria_layout = QGridLayout(search_criteria_group)
        
        # ... (campi di ricerca come prima: self.search_term_edit, self.similarity_threshold_spinbox, self.search_button) ...
        criteria_layout.addWidget(QLabel("Termine di ricerca (nome, cognome, ecc.):"), 0, 0)
        self.search_term_edit = QLineEdit()
        self.search_term_edit.setPlaceholderText("Inserisci parte del nome o altri termini...")
        criteria_layout.addWidget(self.search_term_edit, 0, 1, 1, 2)
        
        criteria_layout.addWidget(QLabel("Soglia di similarità (0.0 - 1.0):"), 1, 0)
        self.similarity_threshold_spinbox = QDoubleSpinBox()
        self.similarity_threshold_spinbox.setMinimum(0.0)
        self.similarity_threshold_spinbox.setMaximum(1.0)
        self.similarity_threshold_spinbox.setSingleStep(0.05)
        self.similarity_threshold_spinbox.setValue(0.3) 
        criteria_layout.addWidget(self.similarity_threshold_spinbox, 1, 1)
        
        self.search_button = QPushButton("Cerca Possessori")
        self.search_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.search_button.clicked.connect(self._perform_search)
        criteria_layout.addWidget(self.search_button, 1, 2)

        main_layout.addWidget(search_criteria_group)
        
        # --- Tabella per i Risultati ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7) 
        self.results_table.setHorizontalHeaderLabels([
            "ID", "Nome Completo", "Cognome Nome", "Paternità", "Comune Rif.", "Similarità", "Num. Partite"
        ])
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection) # Assicurati sia SingleSelection
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_azione) # Nuovo collegamento
        self.results_table.itemDoubleClicked.connect(self.apri_modifica_possessore_selezionato) # Modifica al doppio click

        main_layout.addWidget(self.results_table)

        # --- Pulsanti di Azione sotto la Tabella ---
        action_layout = QHBoxLayout()
        self.btn_modifica_possessore = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Modifica Selezionato")
        self.btn_modifica_possessore.setToolTip("Modifica i dati del possessore selezionato")
        self.btn_modifica_possessore.clicked.connect(self.apri_modifica_possessore_selezionato)
        self.btn_modifica_possessore.setEnabled(False) # Inizialmente disabilitato
        action_layout.addWidget(self.btn_modifica_possessore)
        action_layout.addStretch() # Spinge i pulsanti a sinistra o distribuisce lo spazio
        main_layout.addLayout(action_layout)

        self.setLayout(main_layout)


    def _aggiorna_stato_pulsanti_azione(self):
        """Abilita/disabilita i pulsanti di azione in base alla selezione nella tabella."""
        has_selection = bool(self.results_table.selectedItems())
        self.btn_modifica_possessore.setEnabled(has_selection)

    def _get_selected_possessore_id(self) -> Optional[int]:
        """Restituisce l'ID del possessore attualmente selezionato nella tabella dei risultati."""
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return None
        
        current_row = self.results_table.currentRow()
        if current_row < 0:
            return None
            
        id_item = self.results_table.item(current_row, 0) # Colonna ID
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def apri_modifica_possessore_selezionato(self): # Può essere chiamato da pulsante o doppio click
        possessore_id = self._get_selected_possessore_id()
        if possessore_id is not None:
            # Istanziamo e apriamo ModificaPossessoreDialog
            dialog = ModificaPossessoreDialog(self.db_manager, possessore_id, self)
            if dialog.exec_() == QDialog.Accepted:
                # Se il dialogo è stato accettato (cioè le modifiche sono state salvate),
                # ricarichiamo i risultati della ricerca per riflettere le modifiche.
                # Questo potrebbe richiedere di rieseguire l'ultima ricerca o di aggiornare la riga.
                # Per semplicità, rieseguiamo l'ultima ricerca se i criteri sono ancora validi.
                QMessageBox.information(self, "Modifica Possessore", "Modifiche al possessore salvate con successo.")
                self._perform_search() # Riesegue l'ultima ricerca per aggiornare la tabella
        else:
            QMessageBox.warning(self, "Nessuna Selezione", "Per favore, seleziona un possessore dalla tabella da modificare.")

    def _perform_search(self):
        # ... (la tua logica esistente per _perform_search) ...
        search_term = self.search_term_edit.text().strip()
        similarity_threshold = self.similarity_threshold_spinbox.value()
        
        if not search_term and not self.isVisible(): # Evita ricerca vuota se il widget non è visibile la prima volta
            self.results_table.setRowCount(0)
            self._aggiorna_stato_pulsanti_azione()
            return
        if not search_term and self.isVisible(): # Se visibile e si preme cerca senza termine
             QMessageBox.information(self, "Ricerca Possessori", "Inserire un termine di ricerca.")
             self.results_table.setRowCount(0)
             self._aggiorna_stato_pulsanti_azione()
             return

        try:
            possessori = self.db_manager.ricerca_avanzata_possessori(
                query_text=search_term,
                similarity_threshold=similarity_threshold
            )
            self.results_table.setRowCount(0)
            if not possessori:
                QMessageBox.information(self, "Ricerca Possessori", "Nessun possessore trovato con i criteri specificati.")
            else:
                self.results_table.setRowCount(len(possessori))
                for row_idx, possessore_data in enumerate(possessori):
                    col = 0
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(str(possessore_data.get('id', 'N/D')))); col+=1
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(possessore_data.get('nome_completo', 'N/D'))); col+=1
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(possessore_data.get('cognome_nome', 'N/D'))); col+=1
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(possessore_data.get('paternita', 'N/D'))); col+=1
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(possessore_data.get('comune_nome', 'N/D'))); col+=1 # Nome del comune
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(f"{possessore_data.get('similarity', 0.0):.3f}")); col+=1
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(str(possessore_data.get('num_partite', 'N/D')))); col+=1
                self.results_table.resizeColumnsToContents()
            
        except Exception as e:
            gui_logger.error(f"Errore durante la ricerca possessori (GUI - Consultazione): {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Ricerca", f"Si è verificato un errore durante la ricerca: {e}")
        finally:
            self._aggiorna_stato_pulsanti_azione() # Aggiorna stato pulsanti dopo ricerca


    # Rimuovi _show_possessore_details se non serve più o se è sostituito da apri_modifica_possessore_selezionato
    # def _show_possessore_details(self, item: QTableWidgetItem): ...

# --- Dialogo Dettagli Partita ---
class PartitaDetailsDialog(QDialog):
    def __init__(self, partita_data, parent=None):
        super(PartitaDetailsDialog, self).__init__(parent)
        self.partita = partita_data
        
        self.setWindowTitle(f"Dettagli Partita {partita_data['numero_partita']}")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        NUOVE_COLONNE_POSSESSORI = 6 # o 5 se non mostri cognome_nome separato
        NUOVE_ETICHETTE_POSSESSORI = ["ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]
    # --- Layout della finestra ---
        # Intestazione
        header_layout = QHBoxLayout()
        
        title_label = QLabel(f"<h2>Partita N.{self.partita['numero_partita']} - {self.partita['comune_nome']}</h2>")
        header_layout.addWidget(title_label)
        
        layout.addLayout(header_layout)
        
        # Informazioni generali
        info_group = QGroupBox("Informazioni Generali")
        info_layout = QGridLayout()
        
        info_layout.addWidget(QLabel("<b>ID:</b>"), 0, 0)
        info_layout.addWidget(QLabel(str(self.partita['id'])), 0, 1)
        
        info_layout.addWidget(QLabel("<b>Tipo:</b>"), 0, 2)
        info_layout.addWidget(QLabel(self.partita['tipo']), 0, 3)
        
        info_layout.addWidget(QLabel("<b>Stato:</b>"), 1, 0)
        info_layout.addWidget(QLabel(self.partita['stato']), 1, 1)
        
        info_layout.addWidget(QLabel("<b>Data Impianto:</b>"), 1, 2)
        info_layout.addWidget(QLabel(str(self.partita['data_impianto'])), 1, 3)
        
        if self.partita.get('data_chiusura'):
            info_layout.addWidget(QLabel("<b>Data Chiusura:</b>"), 2, 0)
            info_layout.addWidget(QLabel(str(self.partita['data_chiusura'])), 2, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Tabs per possessori, immobili, variazioni
        tabs = QTabWidget()
        
        # Tab Possessori
        possessori_tab = QWidget()
        possessori_layout = QVBoxLayout()
        
        possessori_table = QTableWidget()
        possessori_table.setColumnCount(4)
        possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Titolo", "Quota"])
        possessori_table.setAlternatingRowColors(True)
        
        if self.partita.get('possessori'):
            possessori_table.setRowCount(len(self.partita['possessori']))
            for i, possessore in enumerate(self.partita['possessori']):
                possessori_table.setItem(i, 0, QTableWidgetItem(str(possessore.get('id', ''))))
                possessori_table.setItem(i, 1, QTableWidgetItem(possessore.get('nome_completo', '')))
                possessori_table.setItem(i, 2, QTableWidgetItem(possessore.get('titolo', '')))
                possessori_table.setItem(i, 3, QTableWidgetItem(possessore.get('quota', '')))
        
        possessori_layout.addWidget(possessori_table)
        possessori_tab.setLayout(possessori_layout)
        tabs.addTab(possessori_tab, "Possessori")
        
        # Tab Immobili
        immobili_tab = QWidget()
        immobili_layout = QVBoxLayout()
        
        immobili_table = ImmobiliTableWidget()
        
        if self.partita.get('immobili'):
            immobili_table.populate_data(self.partita['immobili'])
        
        immobili_layout.addWidget(immobili_table)
        immobili_tab.setLayout(immobili_layout)
        tabs.addTab(immobili_tab, "Immobili")
        
        # Tab Variazioni
        variazioni_tab = QWidget()
        variazioni_layout = QVBoxLayout()
        
        variazioni_table = QTableWidget()
        variazioni_table.setColumnCount(5)
        variazioni_table.setHorizontalHeaderLabels(["ID", "Tipo", "Data", "Partita Dest.", "Contratto"])
        variazioni_table.setAlternatingRowColors(True)
        
        if self.partita.get('variazioni'):
            variazioni_table.setRowCount(len(self.partita['variazioni']))
            for i, var in enumerate(self.partita['variazioni']):
                variazioni_table.setItem(i, 0, QTableWidgetItem(str(var.get('id', ''))))
                variazioni_table.setItem(i, 1, QTableWidgetItem(var.get('tipo', '')))
                variazioni_table.setItem(i, 2, QTableWidgetItem(str(var.get('data_variazione', ''))))
                
                # Partita destinazione
                dest_text = str(var.get('partita_destinazione_id', '')) if var.get('partita_destinazione_id') else "-"
                variazioni_table.setItem(i, 3, QTableWidgetItem(dest_text))
                
                # Contratto info
                contratto_text = ""
                if var.get('tipo_contratto'):
                    contratto_text = f"{var['tipo_contratto']} del {var.get('data_contratto', '')}"
                    if var.get('notaio'):
                        contratto_text += f" - {var['notaio']}"
                
                variazioni_table.setItem(i, 4, QTableWidgetItem(contratto_text))
        
        variazioni_layout.addWidget(variazioni_table)
        variazioni_tab.setLayout(variazioni_layout)
        tabs.addTab(variazioni_tab, "Variazioni")
        
        layout.addWidget(tabs)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        export_button = QPushButton("Esporta in JSON")
        export_button.clicked.connect(self.export_to_json)
        
        close_button = QPushButton("Chiudi")
        close_button.clicked.connect(self.accept)
        
        buttons_layout.addWidget(export_button)
        buttons_layout.addWidget(close_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def export_to_json(self):
        """Esporta i dettagli della partita in formato JSON."""
        if not self.partita: # Assicurati che self.partita contenga i dati
            QMessageBox.warning(self, "Errore Dati", "Nessun dato della partita da esportare.")
            return

        partita_id = self.partita.get('id', 'sconosciuto') # Usa .get per sicurezza
        
        default_filename = f"partita_{partita_id}_{date.today().isoformat()}.json" # Usa isoformat per la data nel nome file
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Salva JSON Partita", 
            default_filename, 
            "JSON files (*.json)"
        )
        
        if file_path:
            try:
                # --- INIZIO MODIFICA ---
                def json_serial(obj):
                    """JSON serializer per oggetti non serializzabili di default (date/datetime)."""
                    if isinstance(obj, (datetime, date)):
                        return obj.isoformat() # Converte date/datetime in stringa ISO 8601
                    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

                # Usa l'handler personalizzato con json.dumps
                json_str = json.dumps(self.partita, indent=4, ensure_ascii=False, default=json_serial)
                # --- FINE MODIFICA ---
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                
                QMessageBox.information(self, "Esportazione Completata", f"I dati della partita sono stati salvati in:\n{file_path}")
            except TypeError as te: # Cattura specificamente il TypeError se json_serial non copre tutto
                gui_logger.error(f"Errore di serializzazione JSON: {te} - Dati: {self.partita}")
                QMessageBox.critical(self, "Errore di Serializzazione", 
                                     f"Errore durante la conversione dei dati in JSON: {te}\n"
                                     "Controllare i log per i dettagli dei dati problematici.")
            except Exception as e:
                gui_logger.error(f"Errore durante l'esportazione JSON della partita: {e}")
                QMessageBox.critical(self, "Errore Esportazione", f"Errore durante il salvataggio del file JSON:\n{e}")

class PartiteComuneDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, nome_comune: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.nome_comune = nome_comune
        # Aggiungi per tracciare l'utente loggato, se necessario per l'audit di modifica
        # self.current_user_info = getattr(parent, 'logged_in_user_info', None) if parent else None


        self.setWindowTitle(f"Partite del Comune di {self.nome_comune} (ID: {self.comune_id})")
        self.setMinimumSize(850, 550) # Leggermente più grande per il nuovo pulsante

        layout = QVBoxLayout(self)

        # ... (Tabella Partite come prima) ...
        self.partite_table = QTableWidget()
        self.partite_table.setColumnCount(7)
        self.partite_table.setHorizontalHeaderLabels([
            "ID Partita", "Numero", "Tipo", "Stato",
            "Data Impianto", "Possessori (Anteprima)", "Num. Immobili"
        ])
        self.partite_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.partite_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.partite_table.setSelectionMode(QTableWidget.SingleSelection)
        self.partite_table.setAlternatingRowColors(True)
        self.partite_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # O ResizeToContents
        self.partite_table.setSortingEnabled(True)
        self.partite_table.itemDoubleClicked.connect(self.apri_dettaglio_partita_selezionata)
        # Disabilita il pulsante modifica se nessuna riga è selezionata
        self.partite_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsante_modifica)


        layout.addWidget(self.partite_table)

        # --- Pulsanti Azione ---
        action_buttons_layout = QHBoxLayout()

        self.btn_apri_dettaglio = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogInfoView), "Vedi Dettagli")
        self.btn_apri_dettaglio.clicked.connect(self.apri_dettaglio_partita_selezionata_da_pulsante)
        self.btn_apri_dettaglio.setEnabled(False) # Inizialmente disabilitato
        action_buttons_layout.addWidget(self.btn_apri_dettaglio)

        self.btn_modifica_partita = QPushButton("Modifica Partita") # USARE ICONA ADATTA
        self.btn_modifica_partita.setToolTip("Modifica i dati della partita selezionata")
        self.btn_modifica_partita.clicked.connect(self.apri_modifica_partita_selezionata)
        self.btn_modifica_partita.setEnabled(False) # Inizialmente disabilitato
        action_buttons_layout.addWidget(self.btn_modifica_partita)
        
        action_buttons_layout.addStretch()

        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.accept)
        action_buttons_layout.addWidget(self.close_button)
        
        layout.addLayout(action_buttons_layout)

        self.setLayout(layout)
        self.load_partite_data()

    def _aggiorna_stato_pulsante_modifica(self):
        """Abilita/disabilita il pulsante modifica in base alla selezione."""
        has_selection = bool(self.partite_table.selectedItems())
        self.btn_modifica_partita.setEnabled(has_selection)
        self.btn_apri_dettaglio.setEnabled(has_selection)

    def _get_selected_partita_id(self) -> Optional[int]:
        """Restituisce l'ID della partita attualmente selezionata nella tabella."""
        selected_items = self.partite_table.selectedItems()
        if not selected_items:
            return None
        
        row = self.partite_table.currentRow()
        if row < 0:
            return None
        
        partita_id_item = self.partite_table.item(row, 0) # Colonna ID Partita
        if partita_id_item and partita_id_item.text().isdigit():
            return int(partita_id_item.text())
        return None

    def apri_dettaglio_partita_selezionata_da_pulsante(self):
        """Azione per il pulsante 'Vedi Dettagli'."""
        partita_id = self._get_selected_partita_id()
        if partita_id is not None:
            partita_details_data = self.db_manager.get_partita_details(partita_id)
            if partita_details_data:
                details_dialog = PartitaDetailsDialog(partita_details_data, self)
                details_dialog.exec_()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile recuperare i dettagli per la partita ID {partita_id}.")
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona una partita dalla tabella per vederne i dettagli.")


    def apri_modifica_partita_selezionata(self):
        partita_id = self._get_selected_partita_id()
        if partita_id is not None:
            # Qui istanzieremo e apriremo ModificaPartitaDialog
            # Passando self.db_manager, partita_id, e self (come parent)
            # Esempio:
            dialog = ModificaPartitaDialog(self.db_manager, partita_id, self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_partite_data() # Ricarica i dati se le modifiche sono state salvate
                QMessageBox.information(self, "Modifica Partita", "Modifiche alla partita salvate con successo.")
        else:
            QMessageBox.warning(self, "Nessuna Selezione", "Per favore, seleziona una partita da modificare.")

    # ... (load_partite_data e apri_dettaglio_partita_selezionata (per doppio click) come prima) ...
    def load_partite_data(self): # Assicurati che questo metodo esista e funzioni
        self.partite_table.setRowCount(0)
        self.partite_table.setSortingEnabled(False)
        try:
            partite_list = self.db_manager.get_partite_by_comune(self.comune_id)
            if partite_list:
                self.partite_table.setRowCount(len(partite_list))
                for row_idx, partita in enumerate(partite_list):
                    col = 0
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('id', '')))); col+=1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('numero_partita', '')))); col+=1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(partita.get('tipo', ''))); col+=1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(partita.get('stato', ''))); col+=1
                    data_imp = partita.get('data_impianto')
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(data_imp) if data_imp else '')); col+=1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(partita.get('possessori', ''))); col+=1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('num_immobili', '0')))); col+=1
                self.partite_table.resizeColumnsToContents()
            else:
                gui_logger.info(f"Nessuna partita trovata per il comune ID: {self.comune_id}")
        except Exception as e:
            gui_logger.error(f"Errore durante il caricamento delle partite per comune ID {self.comune_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
        finally:
            self.partite_table.setSortingEnabled(True)
        self._aggiorna_stato_pulsante_modifica() # Aggiorna stato dopo caricamento

    def apri_dettaglio_partita_selezionata(self, item: QTableWidgetItem): # Per doppio click
         if not item: return
         partita_id = self._get_selected_partita_id() # Usa l'helper
         if partita_id is not None:
             partita_details_data = self.db_manager.get_partita_details(partita_id)
             if partita_details_data:
                 details_dialog = PartitaDetailsDialog(partita_details_data, self)
                 details_dialog.exec_()
             else:
                 QMessageBox.warning(self, "Errore Dati", f"Impossibile recuperare i dettagli per la partita ID {partita_id}.")
class ModificaPartitaDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, partita_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.partita_id = partita_id
        self.partita_data_originale = None
        self.problematic_default_date_db = date(2000, 1, 1)# Definiamo la data problematica

        self.setWindowTitle(f"Modifica Partita ID: {self.partita_id}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._init_ui() # Chiama l'inizializzazione dell'UI
        self._load_partita_data() # Carica i dati della partita
        self._load_possessori_associati() # Carica i possessori per il tab

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Tab Widget Principale ---
        self.tab_widget = QTabWidget(self)
        main_layout.addWidget(self.tab_widget)

        # --- Tab 1: Dati Generali Partita ---
        self.tab_dati_generali = QWidget()
        form_layout_generali = QFormLayout(self.tab_dati_generali)

        self.id_label = QLabel(str(self.partita_id))
        form_layout_generali.addRow("ID Partita:", self.id_label)
        self.comune_label = QLabel("Comune non specificato") # Verrà popolato da _load_partita_data
        form_layout_generali.addRow("Comune:", self.comune_label)

        self.numero_partita_spinbox = QSpinBox()
        self.numero_partita_spinbox.setRange(1, 999999)
        form_layout_generali.addRow("Numero Partita (*):", self.numero_partita_spinbox)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["principale", "secondaria"]) # Assicurati che questi siano i valori corretti
        form_layout_generali.addRow("Tipo (*):", self.tipo_combo)

        self.data_impianto_edit = QDateEdit()
        self.data_impianto_edit.setCalendarPopup(True)
        self.data_impianto_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_impianto_edit.setSpecialValueText(" ") # Permette di visualizzare come vuoto
        self.data_impianto_edit.setDate(QDate()) # Data nulla di default
        form_layout_generali.addRow("Data Impianto:", self.data_impianto_edit)

        self.data_chiusura_edit = QDateEdit()
        self.data_chiusura_edit.setCalendarPopup(True)
        self.data_chiusura_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_chiusura_edit.setSpecialValueText(" ") # Permette di visualizzare come vuoto
        self.data_chiusura_edit.setDate(QDate()) # Data nulla di default
        form_layout_generali.addRow("Data Chiusura:", self.data_chiusura_edit)

        self.numero_provenienza_spinbox = QSpinBox()
        self.numero_provenienza_spinbox.setRange(0, 999999) # Assumendo che 0 sia per "Nessuno"
        self.numero_provenienza_spinbox.setSpecialValueText("Nessuno") # Testo per quando il valore è 0 (o il minimo)
        form_layout_generali.addRow("Numero Provenienza:", self.numero_provenienza_spinbox)

        self.stato_combo = QComboBox()
        self.stato_combo.addItems(["attiva", "inattiva"]) # Assicurati siano corretti
        form_layout_generali.addRow("Stato (*):", self.stato_combo)

        self.tab_widget.addTab(self.tab_dati_generali, "Dati Generali")
        
        # --- Tab 2: Possessori Associati (come da tuo codice esistente) ---
        self.tab_possessori = QWidget()
        layout_possessori = QVBoxLayout(self.tab_possessori)

        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(5)
        self.possessori_table.setHorizontalHeaderLabels([
            "ID Rel.", "ID Poss.", "Nome Completo Possessore", "Titolo", "Quota"
        ])
        # ... (altre impostazioni tabella possessori come da tuo codice) ...
        self.possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.setSelectionMode(QTableWidget.SingleSelection)
        self.possessori_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.possessori_table.horizontalHeader().setStretchLastSection(True)
        self.possessori_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_possessori)
        layout_possessori.addWidget(self.possessori_table)

        possessori_buttons_layout = QHBoxLayout()
        self.btn_aggiungi_possessore = QPushButton("Aggiungi Possessore...")
        self.btn_aggiungi_possessore.clicked.connect(self._aggiungi_possessore_a_partita)
        possessori_buttons_layout.addWidget(self.btn_aggiungi_possessore)

        self.btn_modifica_legame_possessore = QPushButton("Modifica Legame...")
        self.btn_modifica_legame_possessore.clicked.connect(self._modifica_legame_possessore)
        self.btn_modifica_legame_possessore.setEnabled(False)
        possessori_buttons_layout.addWidget(self.btn_modifica_legame_possessore)

        self.btn_rimuovi_possessore = QPushButton("Rimuovi dalla Partita")
        self.btn_rimuovi_possessore.clicked.connect(self._rimuovi_possessore_da_partita)
        self.btn_rimuovi_possessore.setEnabled(False)
        possessori_buttons_layout.addWidget(self.btn_rimuovi_possessore)
        possessori_buttons_layout.addStretch()
        layout_possessori.addLayout(possessori_buttons_layout)
        self.tab_widget.addTab(self.tab_possessori, "Possessori Associati")

        # --- Pulsanti Salva/Annulla ---
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton), "Salva Modifiche Dati Generali")
        self.save_button.setToolTip("Salva solo le modifiche apportate nel tab 'Dati Generali'")
        self.save_button.clicked.connect(self._save_changes)
        
        self.close_dialog_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton), "Chiudi")
        self.close_dialog_button.setToolTip("Chiude il dialogo. Le modifiche ai possessori sono salvate individualmente.")
        self.close_dialog_button.clicked.connect(self.accept)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.close_dialog_button)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

    def _load_partita_data(self):
        self.partita_data_originale = self.db_manager.get_partita_details(self.partita_id)
        if not self.partita_data_originale:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare i dati per la partita ID: {self.partita_id}.")
            from PyQt5.QtCore import QTimer 
            QTimer.singleShot(0, self.reject) 
            return

        self.comune_label.setText(self.partita_data_originale.get('comune_nome', "N/D"))
        self.numero_partita_spinbox.setValue(self.partita_data_originale.get('numero_partita', 0))
        
        tipo_idx = self.tipo_combo.findText(self.partita_data_originale.get('tipo', ''), Qt.MatchFixedString)
        if tipo_idx >= 0: 
            self.tipo_combo.setCurrentIndex(tipo_idx)
        
        stato_idx = self.stato_combo.findText(self.partita_data_originale.get('stato', ''), Qt.MatchFixedString)
        if stato_idx >= 0: 
            self.stato_combo.setCurrentIndex(stato_idx)

        data_impianto_db = self.partita_data_originale.get('data_impianto')
        if data_impianto_db and isinstance(data_impianto_db, date): # Usa 'date' importato
            self.data_impianto_edit.setDate(datetime_to_qdate(data_impianto_db))
        else:
            self.data_impianto_edit.setDate(QDate())

        data_chiusura_db = self.partita_data_originale.get('data_chiusura')
        
        if data_chiusura_db is None or data_chiusura_db == self.problematic_default_date_db:
            self.data_chiusura_edit.setDate(QDate.currentDate())
        elif isinstance(data_chiusura_db, date): # Usa 'date' importato
            self.data_chiusura_edit.setDate(datetime_to_qdate(data_chiusura_db))
        else:
            self.data_chiusura_edit.setDate(QDate())
        
        num_prov_val = self.partita_data_originale.get('numero_provenienza')
        if num_prov_val is not None:
            self.numero_provenienza_spinbox.setValue(num_prov_val)
        else:
            self.numero_provenienza_spinbox.setValue(self.numero_provenienza_spinbox.minimum())



    def _save_changes(self):
        # Raccogli i dati dai campi del form
        dati_modificati = {
            "numero_partita": self.numero_partita_spinbox.value(),
            "tipo": self.tipo_combo.currentText(),
            "stato": self.stato_combo.currentText(),
            # Inizializza le date a None, verranno popolate se valide
            "data_impianto": None,
            "data_chiusura": None,
            "numero_provenienza": None,
        }

        q_data_impianto = self.data_impianto_edit.date()
        # Controlla se la data è valida E se il testo non è vuoto (per via dello specialValueText)
        if q_data_impianto.isValid() and self.data_impianto_edit.text().strip():
            dati_modificati["data_impianto"] = qdate_to_datetime(q_data_impianto)
        
        q_data_chiusura = self.data_chiusura_edit.date()
        if q_data_chiusura.isValid() and self.data_chiusura_edit.text().strip():
            dati_modificati["data_chiusura"] = qdate_to_datetime(q_data_chiusura)
        
        num_prov_value = self.numero_provenienza_spinbox.value()
        # Controlla se il testo visualizzato è lo specialValueText
        if self.numero_provenienza_spinbox.text() != self.numero_provenienza_spinbox.specialValueText() and num_prov_value != self.numero_provenienza_spinbox.minimum(): # Evita di salvare il valore speciale
            dati_modificati["numero_provenienza"] = num_prov_value
        # Se è lo special value text, numero_provenienza resta None, che è corretto.

        # Validazione input
        if dati_modificati["numero_partita"] <= 0:
            QMessageBox.warning(self, "Dati Non Validi", "Il numero della partita deve essere un valore positivo.")
            self.numero_partita_spinbox.setFocus()
            return

        if dati_modificati["data_impianto"] and dati_modificati["data_chiusura"]:
            if dati_modificati["data_chiusura"] < dati_modificati["data_impianto"]:
                QMessageBox.warning(self, "Date Non Valide", 
                                    "La data di chiusura non può essere precedente alla data di impianto.")
                self.data_chiusura_edit.setFocus()
                return
        
        # Tentativo di aggiornamento del database (come da suo codice esistente)
        try:
            gui_logger.info(f"Tentativo di aggiornare i dati generali della partita ID {self.partita_id} con: {dati_modificati}")
            self.db_manager.update_partita(self.partita_id, dati_modificati)
            gui_logger.info(f"Dati generali della Partita ID {self.partita_id} aggiornati con successo.")
            QMessageBox.information(self, "Salvataggio Dati Generali", "Modifiche ai dati generali della partita salvate con successo.")
            self._load_partita_data() # Ricarica per coerenza, anche se il dialogo non si chiude
            # self.accept() # Rimuovi questo se il pulsante "Salva" non deve chiudere il dialogo intero
        except DBUniqueConstraintError as uve:
            gui_logger.warning(f"Violazione di unicità aggiornando partita ID {self.partita_id}: {uve.message}")
            QMessageBox.warning(self, "Errore di Unicità", f"Impossibile salvare i dati generali:\n{uve.message}")
            if hasattr(self, 'numero_partita_spinbox'): self.numero_partita_spinbox.setFocus()
        except DBNotFoundError as nfe:
            gui_logger.error(f"Partita ID {self.partita_id} non trovata per aggiornamento: {nfe.message}")
            QMessageBox.critical(self, "Errore Aggiornamento", str(nfe.message))
            self.reject()
        except DBDataError as dde:
            gui_logger.warning(f"Errore dati aggiornando partita ID {self.partita_id}: {dde.message}")
            QMessageBox.warning(self, "Errore Dati Non Validi", f"Impossibile salvare i dati generali:\n{dde.message}")
        except DBMError as dbe:
            gui_logger.error(f"Errore DB aggiornando partita ID {self.partita_id}: {dbe.message}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Errore salvataggio dati generali:\n{dbe.message}")
        except AttributeError as ae:
            gui_logger.critical(f"Errore di attributo (possibile bug) aggiornando partita ID {self.partita_id}: {ae}", exc_info=True)
            QMessageBox.critical(self, "Errore Interno Applicazione", f"Errore interno (AttributeError):\n{ae}")
        except Exception as e:
            gui_logger.critical(f"Errore critico imprevisto aggiornando partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto", f"Errore di sistema imprevisto:\n{type(e).__name__}: {e}")


    def _aggiorna_stato_pulsanti_possessori(self):
        has_selection = bool(self.possessori_table.selectedItems())
        self.btn_modifica_legame_possessore.setEnabled(has_selection)
        self.btn_rimuovi_possessore.setEnabled(has_selection)

    def _load_partita_data(self):
        # ... (come prima, popola i campi del tab "Dati Generali") ...
        self.partita_data_originale = self.db_manager.get_partita_details(self.partita_id)
        if not self.partita_data_originale:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare i dati per la partita ID: {self.partita_id}.")
            from PyQt5.QtCore import QTimer # Importazione locale
            QTimer.singleShot(0, self.reject)
            return

        self.comune_label.setText(self.partita_data_originale.get('comune_nome', "N/D"))
        self.numero_partita_spinbox.setValue(self.partita_data_originale.get('numero_partita', 0))
        tipo_idx = self.tipo_combo.findText(self.partita_data_originale.get('tipo', ''), Qt.MatchFixedString)
        if tipo_idx >= 0: self.tipo_combo.setCurrentIndex(tipo_idx)
        data_impianto = self.partita_data_originale.get('data_impianto')
        if data_impianto: self.data_impianto_edit.setDate(QDate(data_impianto.year, data_impianto.month, data_impianto.day))
        else: self.data_impianto_edit.setDate(QDate())
        data_chiusura = self.partita_data_originale.get('data_chiusura')
        if data_chiusura: self.data_chiusura_edit.setDate(QDate(data_chiusura.year, data_chiusura.month, data_chiusura.day))
        else: self.data_chiusura_edit.setDate(QDate())
        self.numero_provenienza_spinbox.setValue(self.partita_data_originale.get('numero_provenienza') or 0)
        stato_idx = self.stato_combo.findText(self.partita_data_originale.get('stato', ''), Qt.MatchFixedString)
        if stato_idx >= 0: self.stato_combo.setCurrentIndex(stato_idx)

# All'interno della classe ModificaPartitaDialog in prova.py

    def _load_possessori_associati(self):
        self.possessori_table.setRowCount(0)
        self.possessori_table.setSortingEnabled(False)
        gui_logger.info(f"DEBUG: Inizio _load_possessori_associati per partita ID: {self.partita_id}")

        if not self.db_manager:
            QMessageBox.critical(self, "Errore", "DB Manager non disponibile per caricare i possessori.")
            self._aggiorna_stato_pulsanti_possessori()
            return
        if self.partita_id is None:
            QMessageBox.warning(self, "Errore", "ID Partita non specificato.")
            self._aggiorna_stato_pulsanti_possessori()
            return
            
        gui_logger.info(f"Caricamento possessori associati per partita ID: {self.partita_id}")
        try:
            # Questa chiamata ora funziona e restituisce i dati, secondo il tuo log
            possessori = self.db_manager.get_possessori_per_partita(self.partita_id)
            gui_logger.info(f"DEBUG: Dati possessori ricevuti dal DB: {possessori}") # Stampa i dati ricevuti 
            
            if possessori: # Se la lista 'possessori' non è vuota
                self.possessori_table.setRowCount(len(possessori))
                gui_logger.info(f"DEBUG: Tabella impostata a {len(possessori)} righe.")
                for row_idx, poss_data in enumerate(possessori): # Itera sui dizionari restituiti
                    gui_logger.info(f"DEBUG: Popolamento riga {row_idx}, dati: {poss_data}")
                    col = 0
                    
                    # Colonna 0: ID Relazione (partita_possessore.id)
                    id_rel_val = poss_data.get('id_relazione_partita_possessore', '')
                    id_rel_item = QTableWidgetItem(str(id_rel_val))
                    id_rel_item.setData(Qt.UserRole, id_rel_val) # Salva l'ID per uso futuro
                    self.possessori_table.setItem(row_idx, col, id_rel_item); col+=1
                    
                    # Colonna 1: ID Possessore (possessore.id)
                    id_poss_val = poss_data.get('possessore_id', '')
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(str(id_poss_val))); col+=1
                    
                    # Colonna 2: Nome Completo Possessore
                    nome_val = poss_data.get('nome_completo_possessore', 'N/D')
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(nome_val)); col+=1
                    
                    # Colonna 3: Titolo Possesso
                    titolo_val = poss_data.get('titolo_possesso', 'N/D')
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(titolo_val)); col+=1
                    
                    # Colonna 4: Quota Possesso
                    quota_val = poss_data.get('quota_possesso', 'N/D')
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(quota_val)); col+=1
                
                self.possessori_table.resizeColumnsToContents()
                gui_logger.info("DEBUG: Popolamento tabella completato.")
            else:
                gui_logger.info(f"DEBUG: Nessun possessore (lista vuota) per la partita ID {self.partita_id}")
                gui_logger.info(f"Nessun possessore trovato (lista vuota) per la partita ID {self.partita_id}")
                # Potresti voler mostrare un messaggio nella tabella, es:
                # self.possessori_table.setRowCount(1)
                # self.possessori_table.setItem(0, 0, QTableWidgetItem("Nessun possessore associato a questa partita."))
                # self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount()) # Occupa l'intera riga

        except Exception as e: # Cattura eccezioni generiche durante il popolamento della tabella
            gui_logger.error(f"Errore durante il popolamento della tabella possessori per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Popolamento Tabella", 
                                 f"Si è verificato un errore durante la visualizzazione dei possessori associati:\n{e}")
        finally:
            self.possessori_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_possessori()
    

    def _aggiungi_possessore_a_partita(self):
        gui_logger.debug(f"Richiesta aggiunta possessore per partita ID {self.partita_id}")

        # Passo 1: Seleziona o Crea il Possessore
        comune_id_partita = self.partita_data_originale.get('comune_id') if self.partita_data_originale else None
        if comune_id_partita is None:
             QMessageBox.warning(self, "Errore", "Comune della partita non determinato. Impossibile aggiungere possessore.")
             return
        
        # --- Blocco Selezione/Creazione Possessore ---
        # Assicurati che PossessoreSelectionDialog sia importato e funzioni come previsto
        # Dovrebbe restituire l'ID e il nome del possessore selezionato/creato.
        # Qui ipotizziamo che il tuo PossessoreSelectionDialog imposti
        # self.selected_possessore = {'id': ..., 'nome_completo': ...} quando accettato.
        possessore_dialog = PossessoreSelectionDialog(self.db_manager, comune_id_partita, self)
        
        selected_possessore_id = None
        selected_possessore_nome = None

        if possessore_dialog.exec_() == QDialog.Accepted:
            if hasattr(possessore_dialog, 'selected_possessore') and possessore_dialog.selected_possessore:
                selected_possessore_id = possessore_dialog.selected_possessore.get('id')
                selected_possessore_nome = possessore_dialog.selected_possessore.get('nome_completo')
            # Aggiungi altri fallback se il tuo PossessoreSelectionDialog restituisce i dati in modo diverso
        
        if not selected_possessore_id or not selected_possessore_nome:
            gui_logger.info("Nessun possessore selezionato o creato.")
            return
        # --- Fine Blocco Selezione/Creazione Possessore ---

        gui_logger.info(f"Possessore selezionato/creato: ID {selected_possessore_id}, Nome: {selected_possessore_nome}")

        # Passo 2: Chiedi Titolo e Quota per questo legame
        tipo_partita_corrente = self.partita_data_originale.get('tipo', 'principale')

        # Usa il metodo statico corretto che abbiamo definito: get_details_for_new_legame
        dettagli_legame = DettagliLegamePossessoreDialog.get_details_for_new_legame(
            selected_possessore_nome, 
            tipo_partita_corrente, 
            self
        )

        if not dettagli_legame:
            gui_logger.info("Inserimento dettagli legame annullato.")
            return
            
        titolo_possesso = dettagli_legame["titolo"]
        quota_possesso = dettagli_legame["quota"]
        tipo_partita_rel_da_usare = tipo_partita_corrente # Come discusso

        # Passo 3: Chiama il metodo del DBManager per aggiungere il legame
        try:
            # Questa è la chiamata effettiva al DBManager
            success = self.db_manager.aggiungi_possessore_a_partita(
                partita_id=self.partita_id,
                possessore_id=selected_possessore_id,
                tipo_partita_rel=tipo_partita_rel_da_usare,
                titolo=titolo_possesso,
                quota=quota_possesso
            )

            if success: # Assumendo che aggiungi_possessore_a_partita restituisca True o sollevi eccezione
                gui_logger.info(f"Possessore ID {selected_possessore_id} aggiunto con successo alla partita ID {self.partita_id}")
                QMessageBox.information(self, "Successo", 
                                        f"Possessore '{selected_possessore_nome}' aggiunto alla partita.")
                self._load_possessori_associati() # Aggiorna la tabella dei possessori
            # else: # Questo blocco else non serve se il metodo DB solleva eccezioni per fallimenti
            #     QMessageBox.critical(self, "Errore", "Impossibile aggiungere il possessore alla partita (il DBManager ha restituito False).")
        
        except DBUniqueConstraintError as uve_rel:
            gui_logger.warning(f"Violazione unicità aggiungendo possessore {selected_possessore_id} a partita {self.partita_id}: {uve_rel}")
            QMessageBox.warning(self, "Errore di Unicità",
                                f"Impossibile aggiungere il possessore:\n{uve_rel.message}\n"
                                "Questo possessore potrebbe essere già associato a questa partita.")
        except (DBMError, DBDataError) as dbe_rel:
            gui_logger.error(f"Errore DB aggiungendo possessore {selected_possessore_id} a partita {self.partita_id}: {dbe_rel}")
            QMessageBox.critical(self, "Errore Database",
                                 f"Errore durante l'aggiunta del possessore alla partita:\n{dbe_rel.message}")
        except AttributeError as ae: 
            gui_logger.critical(f"Metodo 'aggiungi_possessore_a_partita' non trovato o altro AttributeError: {ae}", exc_info=True)
            QMessageBox.critical(self, "Errore Implementazione", "Funzionalità per aggiungere possessore non completamente implementata o errore interno.")
        except Exception as e_rel:
            gui_logger.critical(f"Errore imprevisto aggiungendo possessore {selected_possessore_id} a partita {self.partita_id}: {e_rel}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e_rel}")

    def _modifica_legame_possessore(self):
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un possessore dalla tabella per modificarne il legame.")
            return

        current_row = selected_items[0].row()
        # L'ID della relazione partita_possessore è memorizzato in UserRole della prima colonna (ID Rel.)
        id_relazione_pp = self.possessori_table.item(current_row, 0).data(Qt.UserRole)
        if id_relazione_pp is None: # Controllo di sicurezza
            QMessageBox.critical(self, "Errore Interno", "ID relazione non trovato per il possessore selezionato.")
            return
            
        nome_possessore_attuale = self.possessori_table.item(current_row, 2).text() # Nome
        titolo_attuale = self.possessori_table.item(current_row, 3).text()      # Titolo
        quota_attuale_item = self.possessori_table.item(current_row, 4)          # Quota
        quota_attuale = quota_attuale_item.text() if quota_attuale_item and quota_attuale_item.text() != 'N/D' else None


        gui_logger.debug(f"Richiesta modifica legame per relazione ID {id_relazione_pp} (Possessore: {nome_possessore_attuale})")

        tipo_partita_corrente = self.partita_data_originale.get('tipo', 'principale')
        
        nuovi_dettagli_legame = DettagliLegamePossessoreDialog.get_details_for_edit_legame(
            nome_possessore_attuale,
            tipo_partita_corrente,
            titolo_attuale,
            quota_attuale,
            self
        )

        if not nuovi_dettagli_legame:
            gui_logger.info("Modifica dettagli legame annullata.")
            return

        # Passo 3: Chiama il metodo del DBManager per aggiornare il legame
        try:
            # Metodo da creare in CatastoDBManager:
            # aggiorna_legame_partita_possessore(self, partita_possessore_id: int, 
            #                                   titolo: str, quota: Optional[str]) -> bool
            success = self.db_manager.aggiorna_legame_partita_possessore(
                partita_possessore_id=id_relazione_pp,
                titolo=nuovi_dettagli_legame["titolo"],
                quota=nuovi_dettagli_legame["quota"]
                # tipo_partita_rel non viene modificato qui, si assume resti lo stesso
            )

            if success:
                gui_logger.info(f"Legame ID {id_relazione_pp} aggiornato con successo.")
                QMessageBox.information(self, "Successo", "Dettagli del legame possessore aggiornati.")
                self._load_possessori_associati() # Aggiorna la tabella
            # else: # Se il metodo DBManager restituisce False
            #     QMessageBox.critical(self, "Errore", "Impossibile aggiornare il legame del possessore.")
        
        except (DBMError, DBDataError) as dbe_legame: # Cattura eccezioni specifiche
            gui_logger.error(f"Errore DB aggiornando legame {id_relazione_pp}: {dbe_legame}")
            QMessageBox.critical(self, "Errore Database",
                                 f"Errore durante l'aggiornamento del legame:\n{dbe_legame.message}")
        except AttributeError as ae:
            gui_logger.critical(f"Metodo 'aggiorna_legame_partita_possessore' non trovato: {ae}", exc_info=True)
            QMessageBox.critical(self, "Errore Implementazione", "Funzionalità per aggiornare legame non completamente implementata.")
        except Exception as e_legame:
            gui_logger.critical(f"Errore imprevisto aggiornando legame {id_relazione_pp}: {e_legame}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e_legame}")

    def _rimuovi_possessore_da_partita(self):
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un legame possessore dalla tabella da rimuovere.")
            return

        id_relazione_pp = selected_items[0].data(Qt.UserRole) # ID da partita_possessore.id
        nome_possessore = self.possessori_table.item(selected_items[0].row(), 2).text()
        
        if id_relazione_pp is None:
            QMessageBox.critical(self, "Errore Interno", "ID relazione non trovato per il possessore selezionato.")
            return

        reply = QMessageBox.question(self, "Conferma Rimozione Legame",
                                     f"Sei sicuro di voler rimuovere il legame con il possessore '{nome_possessore}' (ID Relazione: {id_relazione_pp}) da questa partita?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            gui_logger.debug(f"Richiesta rimozione legame ID {id_relazione_pp}")
            try:
                # Metodo da creare in CatastoDBManager:
                # rimuovi_possessore_da_partita(self, partita_possessore_id: int) -> bool
                success = self.db_manager.rimuovi_possessore_da_partita(id_relazione_pp)
                
                if success:
                    gui_logger.info(f"Legame ID {id_relazione_pp} rimosso con successo.")
                    QMessageBox.information(self, "Successo", "Legame con il possessore rimosso dalla partita.")
                    self._load_possessori_associati() # Aggiorna la tabella
                # else: # Se il metodo restituisce False
                #     QMessageBox.critical(self, "Errore", "Impossibile rimuovere il legame del possessore.")

            except DBNotFoundError as nfe_rel: # Se il legame non esiste più
                gui_logger.warning(f"Tentativo di rimuovere legame ID {id_relazione_pp} non trovato: {nfe_rel}")
                QMessageBox.warning(self, "Operazione Fallita", str(nfe_rel.message))
                self._load_possessori_associati() # Aggiorna comunque la tabella
            except DBMError as dbe_rel:
                gui_logger.error(f"Errore DB rimuovendo legame {id_relazione_pp}: {dbe_rel}")
                QMessageBox.critical(self, "Errore Database",
                                     f"Errore durante la rimozione del legame:\n{dbe_rel.message}")
            except AttributeError as ae:
                gui_logger.critical(f"Metodo 'rimuovi_possessore_da_partita' non trovato: {ae}", exc_info=True)
                QMessageBox.critical(self, "Errore Implementazione", "Funzionalità per rimuovere legame non completamente implementata.")
            except Exception as e_rel:
                gui_logger.critical(f"Errore imprevisto rimuovendo legame {id_relazione_pp}: {e_rel}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e_rel}")


    def _save_changes(self): # Questo ora salva SOLO i dati generali della partita

        # --- 1. Raccogli i dati dai campi del form ---
        # Raccogli i dati dai campi del form
        dati_modificati = {
            "numero_partita": self.numero_partita_spinbox.value(),
            "tipo": self.tipo_combo.currentText(),
            "stato": self.stato_combo.currentText(),
        }
        q_data_impianto = self.data_impianto_edit.date()
        if q_data_impianto.isValid() and self.data_impianto_edit.text().strip() != "":
            dati_modificati["data_impianto"] = q_data_impianto.toPyDate()
        else:
            dati_modificati["data_impianto"] = None
        q_data_chiusura = self.data_chiusura_edit.date()
        if q_data_chiusura.isValid() and self.data_chiusura_edit.text().strip() != "":
            dati_modificati["data_chiusura"] = q_data_chiusura.toPyDate()
        else:
            dati_modificati["data_chiusura"] = None
        num_prov_value = self.numero_provenienza_spinbox.value()
        if self.numero_provenienza_spinbox.text() == self.numero_provenienza_spinbox.specialValueText():
            dati_modificati["numero_provenienza"] = None
        else:
            dati_modificati["numero_provenienza"] = num_prov_value

        if dati_modificati["numero_partita"] <= 0:
            QMessageBox.warning(self, "Dati Non Validi", "Il numero della partita deve essere un valore positivo.")
            self.numero_partita_spinbox.setFocus()
            self.numero_partita_spinbox.selectAll()
            return
        if dati_modificati["data_impianto"] and dati_modificati["data_chiusura"]:
            if dati_modificati["data_chiusura"] < dati_modificati["data_impianto"]:
                QMessageBox.warning(self, "Date Non Valide", "La data di chiusura non può essere precedente alla data di impianto.")
                self.data_chiusura_edit.setFocus()
                return
        try:
            gui_logger.info(f"Tentativo di aggiornare i dati generali della partita ID {self.partita_id} con: {dati_modificati}")
            self.db_manager.update_partita(self.partita_id, dati_modificati) # Assumiamo che questo sollevi eccezioni in caso di errore
            gui_logger.info(f"Dati generali della Partita ID {self.partita_id} aggiornati con successo.")
            # Non chiamare self.accept() qui, perché il pulsante "Salva Modifiche Dati Generali" non deve chiudere il dialogo principale
            # Il dialogo principale si chiude con il pulsante "Chiudi"
            QMessageBox.information(self, "Salvataggio Dati Generali", "Modifiche ai dati generali della partita salvate con successo.")
            # Ricarica i dati generali per riflettere eventuali normalizzazioni o valori di default dal DB
            self._load_partita_data() 
            # Il parent (PartiteComuneDialog) verrà aggiornato solo quando questo dialogo si chiude con Accept.
            # Dobbiamo decidere se il salvataggio dei dati generali deve emettere un segnale o se il parent si aggiorna solo alla chiusura.
            # Per ora, il parent si aggiorna quando il dialogo ModificaPartitaDialog viene 'accepted'.
            # Il pulsante "Chiudi" ora fa self.accept(), quindi il parent aggiornerà.

        except (DBUniqueConstraintError, DBNotFoundError, DBDataError, DBMError, AttributeError, Exception) as e:
            # Riusa la logica di gestione eccezioni che avevi già perfezionato per mostrare i messaggi appropriati
            # (quella che inizia con DBUniqueConstraintError as uve: etc.)
            # Questa è una semplificazione, dovresti avere i blocchi except specifici qui
            error_title = "Errore Salvataggio"
            error_message = f"Errore durante il salvataggio dei dati generali:\n{type(e).__name__}: {str(e)}"
            if isinstance(e, DBUniqueConstraintError):
                error_title = "Errore di Unicità"
                error_message = f"Impossibile salvare i dati generali:\n{e.message}\nIl numero di partita potrebbe essere già in uso."
                if hasattr(self, 'numero_partita_spinbox'): self.numero_partita_spinbox.setFocus()

        q_data_chiusura = self.data_chiusura_edit.date()
        if q_data_chiusura.isValid() and self.data_chiusura_edit.text().strip() != "":
            dati_modificati["data_chiusura"] = q_data_chiusura.toPyDate()
        else:
            dati_modificati["data_chiusura"] = None
            
        num_prov_value = self.numero_provenienza_spinbox.value()
        # Controlla se il testo visualizzato è il testo speciale per "valore nullo"
        if self.numero_provenienza_spinbox.text() == self.numero_provenienza_spinbox.specialValueText():
            dati_modificati["numero_provenienza"] = None
        elif num_prov_value == 0 and self.numero_provenienza_spinbox.minimum() == 0 : # Se 0 è un valore valido e non lo specialValueText
             # Se 0 è un valore valido e non "Nessuno", allora usa 0.
             # Se 0 è interpretato come "Nessuno" o non specificato E non è lo specialValueText
             # allora la logica qui potrebbe aver bisogno di aggiustamenti in base a come vuoi trattare 0.
             # Per ora, se specialValueText non matcha e il valore è 0, assumiamo che 0 sia un valore valido
             # (anche se il DB potrebbe avere NULL per questo). Se 0 deve essere NULL, allora:
             # dati_modificati["numero_provenienza"] = None if num_prov_value == 0 else num_prov_value
             dati_modificati["numero_provenienza"] = num_prov_value # Lascia decidere al DB se 0 è valido o deve essere NULL
        else:
            dati_modificati["numero_provenienza"] = num_prov_value


        # --- 2. Validazione input a livello di UI (opzionale, ma buona pratica) ---
        # Esempio: se il numero partita non può essere zero o negativo
        if dati_modificati["numero_partita"] <= 0:
            QMessageBox.warning(self, "Dati Non Validi", "Il numero della partita deve essere un valore positivo.")
            self.numero_partita_spinbox.setFocus()
            self.numero_partita_spinbox.selectAll()
            return # Interrompe il salvataggio

        # Aggiungi qui altre validazioni preliminari della UI se necessario.
        # Ad esempio, controllare che data_chiusura non sia precedente a data_impianto.
        if dati_modificati["data_impianto"] and dati_modificati["data_chiusura"]:
            if dati_modificati["data_chiusura"] < dati_modificati["data_impianto"]:
                QMessageBox.warning(self, "Date Non Valide", 
                                    "La data di chiusura non può essere precedente alla data di impianto.")
                self.data_chiusura_edit.setFocus()
                return # Interrompe il salvataggio

        # --- 3. Tentativo di aggiornamento del database e gestione errori ---
        try:
            gui_logger.info(f"Tentativo di aggiornare la partita ID {self.partita_id} con i dati: {dati_modificati}")
            self.db_manager.update_partita(self.partita_id, dati_modificati)
            
            # Se update_partita NON solleva eccezioni, l'operazione è andata a buon fine
            gui_logger.info(f"Partita ID {self.partita_id} aggiornata con successo nel database.")
            self.accept() # Chiude il dialogo e restituisce QDialog.Accepted

        except DBUniqueConstraintError as uve:
            gui_logger.warning(f"Violazione di unicità durante l'aggiornamento della partita ID {self.partita_id} con numero {dati_modificati.get('numero_partita')}: {uve}")
            QMessageBox.warning(self, "Errore di Unicità",
                                f"Impossibile salvare le modifiche:\n{uve.message}\n"
                                "Il numero di partita specificato potrebbe essere già in uso per il comune di appartenenza.")
            if hasattr(self, 'numero_partita_spinbox'): # Assicurati che il widget esista
                self.numero_partita_spinbox.setFocus()
                self.numero_partita_spinbox.selectAll()
        
        except DBNotFoundError as nfe:
            gui_logger.error(f"Partita ID {self.partita_id} non trovata per l'aggiornamento: {nfe}")
            QMessageBox.critical(self, "Errore Aggiornamento",
                                 f"Impossibile salvare le modifiche:\n{nfe.message}\nLa partita potrebbe essere stata eliminata da un altro utente.")
            self.reject() # Chiude il dialogo indicando fallimento o che la risorsa non c'è più

        except DBDataError as dde: # Per errori di validazione sollevati dal DBManager o dal DB (es. CheckConstraint)
            gui_logger.warning(f"Errore nei dati forniti per l'aggiornamento della partita ID {self.partita_id}: {dde}")
            QMessageBox.warning(self, "Errore Dati Non Validi",
                                f"Impossibile salvare le modifiche:\n{dde.message}\n"
                                "Verificare la correttezza dei valori inseriti.")
            # Potresti voler mettere il focus sul campo problematico se l'errore lo indica

        except DBMError as dbe: # Altri errori DB gestiti e sollevati dal db_manager
            gui_logger.error(f"Errore database gestito durante l'aggiornamento della partita ID {self.partita_id}: {dbe}")
            QMessageBox.critical(self, "Errore Database",
                                 f"Si è verificato un errore durante il salvataggio nel database:\n{dbe.message}")
        
        except AttributeError as ae: # Cattura specificamente AttributeError
            gui_logger.critical(f"Errore di attributo (probabile bug di programmazione) durante l'aggiornamento della partita ID {self.partita_id}: {ae}", exc_info=True)
            QMessageBox.critical(self, "Errore Interno Applicazione",
                                 f"Si è verificato un errore interno (AttributeError):\n{ae}\n"
                                 "Questo indica un problema nel codice dell'applicazione.\n"
                                 "Contattare lo sviluppatore fornendo i dettagli dal log.")

        except Exception as e: # Catch-all per qualsiasi altra eccezione Python imprevista
            gui_logger.critical(f"Errore critico e imprevisto durante il salvataggio delle modifiche alla partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto",
                                 f"Si è verificato un errore di sistema imprevisto durante il salvataggio:\n"
                                 f"{type(e).__name__}: {e}\n"
                                 "Controllare i log dell'applicazione per il traceback completo.")
            gui_logger.error(f"Errore salvataggio dati generali partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, error_title, error_message)


    # Metodi placeholder per le azioni sui possessori (da implementare successivamente)
    # def _aggiungi_possessore_a_partita(self):
    #     self.output_text_edit.append("DEBUG: _aggiungi_possessore_a_partita da implementare\n")
    #     # Qui apri dialogo per selezionare possessore e inserire titolo/quota
    #     # Poi chiama db_manager.aggiungi_possessore_a_partita(...)
    #     # Poi self._load_possessori_associati()

    # def _modifica_legame_possessore(self):
    #     selected_items = self.possessori_table.selectedItems()
    #     if not selected_items: return
    #     id_relazione = int(self.possessori_table.item(selected_items[0].row(), 0).text())
    #     self.output_text_edit.append(f"DEBUG: _modifica_legame_possessore per ID Relazione {id_relazione} (da implementare)\n")
    #     # Qui apri dialogo per modificare titolo/quota per id_relazione
    #     # Poi chiama db_manager.aggiorna_legame_partita_possessore(...)
    #     # Poi self._load_possessori_associati()

    # def _rimuovi_possessore_da_partita(self):
    #     selected_items = self.possessori_table.selectedItems()
    #     if not selected_items: return
    #     id_relazione = int(self.possessori_table.item(selected_items[0].row(), 0).text())
    #     nome_possessore = self.possessori_table.item(selected_items[0].row(), 2).text()
        
    #     reply = QMessageBox.question(self, "Conferma Rimozione",
    #                                  f"Rimuovere il possessore '{nome_possessore}' da questa partita?",
    #                                  QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    #     if reply == QMessageBox.Yes:
    #         self.output_text_edit.append(f"DEBUG: _rimuovi_possessore_da_partita per ID Relazione {id_relazione} (da implementare)\n")
    #         # Chiama db_manager.rimuovi_possessore_da_partita(id_relazione)
    #         # Poi self._load_possessori_associati()

# Non dimenticare di importare ModificaPartitaDialog dove serve, ad esempio in PartiteComuneDialog
class OperazioniPartitaWidget(QWidget):
    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        # Attributi per la partita sorgente
        self.selected_partita_id_source: Optional[int] = None
        self.selected_partita_comune_id_source: Optional[int] = None 
        self.selected_partita_comune_nome_source: Optional[str] = None
        
        # Attributo per l'immobile selezionato nel tab "Trasferisci Immobile"
        self.selected_immobile_id_transfer: Optional[int] = None
        
        # Lista temporanea per i nuovi possessori nel tab "Passaggio Proprietà"
        self._pp_temp_nuovi_possessori: List[Dict[str, Any]] = [] 

        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10,10,10,10)
        main_layout.setSpacing(15)

        # --- 1. Selezione Partita Sorgente (Comune a tutti i tab sottostanti) ---
        source_partita_group = QGroupBox("Selezione Partita Sorgente")
        source_partita_layout = QGridLayout(source_partita_group)

        source_partita_layout.addWidget(QLabel("ID Partita Sorgente:"), 0, 0)
        self.source_partita_id_spinbox = QSpinBox()
        self.source_partita_id_spinbox.setRange(1, 9999999) # Range ampio per ID
        self.source_partita_id_spinbox.setToolTip("Inserisci l'ID della partita o usa 'Cerca'")
        source_partita_layout.addWidget(self.source_partita_id_spinbox, 0, 1)

        self.btn_cerca_source_partita = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogContentsView), " Cerca Partita...")
        self.btn_cerca_source_partita.setToolTip("Cerca una partita esistente da usare come sorgente")
        self.btn_cerca_source_partita.clicked.connect(self._cerca_partita_sorgente)
        source_partita_layout.addWidget(self.btn_cerca_source_partita, 0, 2)
        
        # Pulsante per caricare la partita dall'ID inserito nello SpinBox
        self.btn_load_source_partita_from_id = QPushButton(QApplication.style().standardIcon(QStyle.SP_ArrowRight), " Carica da ID")
        self.btn_load_source_partita_from_id.setToolTip("Carica i dettagli della partita usando l'ID inserito")
        self.btn_load_source_partita_from_id.clicked.connect(self._load_partita_sorgente_from_spinbox)
        source_partita_layout.addWidget(self.btn_load_source_partita_from_id, 0, 3)


        self.source_partita_info_label = QLabel("Nessuna partita sorgente selezionata.")
        self.source_partita_info_label.setWordWrap(True)
        self.source_partita_info_label.setStyleSheet("QLabel { padding: 5px; background-color: #e8f0fe; border: 1px solid #d_3c_cf; border-radius: 3px; min-height: 2em; }")
        source_partita_layout.addWidget(self.source_partita_info_label, 1, 0, 1, 4) # Span su 4 colonne
        main_layout.addWidget(source_partita_group)

        # --- 2. QTabWidget per le diverse operazioni ---
        self.operazioni_tabs = QTabWidget()
        main_layout.addWidget(self.operazioni_tabs, 1) 

        # --- Creazione dei Tab ---
        self._crea_tab_duplica_partita()
        self._crea_tab_trasferisci_immobile()
        self._crea_tab_passaggio_proprieta()

        self.setLayout(main_layout)

    def _crea_tab_duplica_partita(self):
        duplica_widget = QWidget() 
        duplica_main_layout = QVBoxLayout(duplica_widget) 
        duplica_group = QGroupBox("Opzioni per la Duplicazione") 
        duplica_form_layout = QFormLayout(duplica_group)
        duplica_form_layout.setSpacing(10)

        self.nuovo_numero_partita_spinbox = QSpinBox()
        self.nuovo_numero_partita_spinbox.setRange(1, 9999999)
        duplica_form_layout.addRow("Nuovo Numero Partita (*):", self.nuovo_numero_partita_spinbox)
        self.duplica_mantieni_poss_check = QCheckBox("Mantieni Possessori Originali nella Nuova Partita")
        self.duplica_mantieni_poss_check.setChecked(True)
        duplica_form_layout.addRow(self.duplica_mantieni_poss_check)
        self.duplica_mantieni_imm_check = QCheckBox("Copia gli Immobili Originali nella Nuova Partita")
        self.duplica_mantieni_imm_check.setChecked(False) 
        duplica_form_layout.addRow(self.duplica_mantieni_imm_check)
        self.btn_esegui_duplicazione = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton), " Esegui Duplicazione")
        self.btn_esegui_duplicazione.clicked.connect(self._esegui_duplicazione_partita)
        duplica_form_layout.addRow(self.btn_esegui_duplicazione)
        
        duplica_main_layout.addWidget(duplica_group)
        duplica_main_layout.addStretch(1)
        self.operazioni_tabs.addTab(duplica_widget, "Duplica Partita")

    def _crea_tab_trasferisci_immobile(self):
        transfer_widget = QWidget()
        transfer_main_layout = QVBoxLayout(transfer_widget)
        transfer_group = QGroupBox("Dettagli Trasferimento Immobile")
        transfer_form_layout = QFormLayout(transfer_group) 
        transfer_form_layout.setSpacing(10)

        transfer_form_layout.addRow(QLabel("Immobili nella Partita Sorgente (selezionarne uno):"))
        self.immobili_partita_sorgente_table = QTableWidget()
        self.immobili_partita_sorgente_table.setColumnCount(3)
        self.immobili_partita_sorgente_table.setHorizontalHeaderLabels(["ID Imm.", "Natura", "Località"])
        self.immobili_partita_sorgente_table.setSelectionMode(QTableWidget.SingleSelection)
        self.immobili_partita_sorgente_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.immobili_partita_sorgente_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.immobili_partita_sorgente_table.setFixedHeight(150)
        self.immobili_partita_sorgente_table.itemSelectionChanged.connect(self._immobile_sorgente_selezionato)
        transfer_form_layout.addRow(self.immobili_partita_sorgente_table)
        
        self.immobile_id_transfer_label = QLabel("Nessun immobile selezionato.")
        self.immobile_id_transfer_label.setStyleSheet("font-style: italic; color: #555;")
        transfer_form_layout.addRow(self.immobile_id_transfer_label)

        dest_partita_container_widget = QWidget()
        dest_partita_h_layout = QHBoxLayout(dest_partita_container_widget)
        dest_partita_h_layout.setContentsMargins(0,0,0,0)
        self.dest_partita_id_spinbox = QSpinBox()
        self.dest_partita_id_spinbox.setRange(1, 9999999)
        dest_partita_h_layout.addWidget(self.dest_partita_id_spinbox)
        self.btn_cerca_dest_partita = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogContentsView), " Cerca...")
        self.btn_cerca_dest_partita.clicked.connect(self._cerca_partita_destinazione)
        dest_partita_h_layout.addWidget(self.btn_cerca_dest_partita)
        transfer_form_layout.addRow("ID Partita Destinazione (*):", dest_partita_container_widget)
        
        self.dest_partita_info_label = QLabel("Nessuna partita destinazione selezionata.")
        self.dest_partita_info_label.setStyleSheet("font-style: italic; color: #555;")
        transfer_form_layout.addRow(self.dest_partita_info_label)

        self.transfer_registra_var_check = QCheckBox("Registra Variazione Catastale per questo Trasferimento")
        transfer_form_layout.addRow(self.transfer_registra_var_check)

        self.btn_esegui_trasferimento = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton), " Esegui Trasferimento Immobile")
        self.btn_esegui_trasferimento.clicked.connect(self._esegui_trasferimento_immobile)
        transfer_form_layout.addRow(self.btn_esegui_trasferimento)
        
        transfer_main_layout.addWidget(transfer_group)
        transfer_main_layout.addStretch(1)
        self.operazioni_tabs.addTab(transfer_widget, "Trasferisci Immobile")

    def _crea_tab_passaggio_proprieta(self):
        passaggio_widget_main_container = QWidget()
        passaggio_tab_layout = QVBoxLayout(passaggio_widget_main_container)
        passaggio_scroll = QScrollArea(passaggio_widget_main_container)
        passaggio_scroll.setWidgetResizable(True)
        passaggio_scroll_content_widget = QWidget()
        passaggio_main_layout_scroll = QVBoxLayout(passaggio_scroll_content_widget)
        passaggio_main_layout_scroll.setSpacing(15)

        dati_atto_group = QGroupBox("Dati Nuova Partita e Atto di Trasferimento")
        passaggio_form_layout = QFormLayout(dati_atto_group)
        passaggio_form_layout.setSpacing(10)

        self.pp_nuova_partita_numero_spinbox = QSpinBox()
        self.pp_nuova_partita_numero_spinbox.setRange(1, 9999999)
        passaggio_form_layout.addRow("Numero Nuova Partita (*):", self.pp_nuova_partita_numero_spinbox)
        self.pp_nuova_partita_comune_label = QLabel("Il comune sarà lo stesso della partita sorgente.")
        passaggio_form_layout.addRow("Comune Nuova Partita:", self.pp_nuova_partita_comune_label)
        
        self.pp_tipo_variazione_combo = QComboBox()
        tipi_variazione_validi = ['Vendita','Acquisto', 'Successione', 'Variazione', 'Frazionamento', 'Divisione', 'Trasferimento','Altro']
        self.pp_tipo_variazione_combo.addItems(tipi_variazione_validi)
        if tipi_variazione_validi: self.pp_tipo_variazione_combo.setCurrentIndex(0)
        passaggio_form_layout.addRow("Tipo Variazione (*):", self.pp_tipo_variazione_combo)

        self.pp_data_variazione_edit = QDateEdit(calendarPopup=True); self.pp_data_variazione_edit.setDisplayFormat("yyyy-MM-dd"); self.pp_data_variazione_edit.setDate(QDate.currentDate())
        passaggio_form_layout.addRow("Data Variazione (*):", self.pp_data_variazione_edit)
        self.pp_tipo_contratto_edit = QLineEdit(); self.pp_tipo_contratto_edit.setPlaceholderText("Es. Atto Notarile, Denuncia Successione")
        passaggio_form_layout.addRow("Tipo Atto/Contratto (*):", self.pp_tipo_contratto_edit)
        self.pp_data_contratto_edit = QDateEdit(calendarPopup=True); self.pp_data_contratto_edit.setDisplayFormat("yyyy-MM-dd"); self.pp_data_contratto_edit.setDate(QDate.currentDate())
        passaggio_form_layout.addRow("Data Atto/Contratto (*):", self.pp_data_contratto_edit)
        self.pp_notaio_edit = QLineEdit()
        passaggio_form_layout.addRow("Notaio/Autorità Emittente:", self.pp_notaio_edit)
        self.pp_repertorio_edit = QLineEdit()
        passaggio_form_layout.addRow("N. Repertorio/Protocollo:", self.pp_repertorio_edit)
        self.pp_note_variazione_edit = QTextEdit(); self.pp_note_variazione_edit.setFixedHeight(60)
        passaggio_form_layout.addRow("Note Variazione:", self.pp_note_variazione_edit)
        passaggio_main_layout_scroll.addWidget(dati_atto_group)

        immobili_transfer_group_pp = QGroupBox("Immobili da Includere nella Nuova Partita")
        immobili_transfer_layout_pp = QVBoxLayout(immobili_transfer_group_pp)
        self.pp_trasferisci_tutti_immobili_check = QCheckBox("Includi TUTTI gli immobili dalla partita sorgente")
        self.pp_trasferisci_tutti_immobili_check.setChecked(True)
        self.pp_trasferisci_tutti_immobili_check.toggled.connect(self._toggle_selezione_immobili_pp)
        immobili_transfer_layout_pp.addWidget(self.pp_trasferisci_tutti_immobili_check)
        self.pp_immobili_da_selezionare_table = QTableWidget()
        self.pp_immobili_da_selezionare_table.setColumnCount(4) 
        self.pp_immobili_da_selezionare_table.setHorizontalHeaderLabels(["Sel.", "ID Imm.", "Natura", "Località"])
        self.pp_immobili_da_selezionare_table.setSelectionMode(QTableWidget.NoSelection)
        self.pp_immobili_da_selezionare_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pp_immobili_da_selezionare_table.setFixedHeight(150)
        self.pp_immobili_da_selezionare_table.setVisible(False)
        immobili_transfer_layout_pp.addWidget(self.pp_immobili_da_selezionare_table)
        passaggio_main_layout_scroll.addWidget(immobili_transfer_group_pp)
        
        nuovi_poss_group = QGroupBox("Nuovi Possessori per la Nuova Partita")
        nuovi_poss_layout = QVBoxLayout(nuovi_poss_group)
        self.pp_nuovi_possessori_table = QTableWidget()
        self.pp_nuovi_possessori_table.setColumnCount(4) 
        self.pp_nuovi_possessori_table.setHorizontalHeaderLabels(["ID Poss.", "Nome Completo", "Titolo (*)", "Quota"])
        self.pp_nuovi_possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pp_nuovi_possessori_table.setSelectionMode(QTableWidget.SingleSelection)
        self.pp_nuovi_possessori_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.pp_nuovi_possessori_table.horizontalHeader().setStretchLastSection(True)
        self.pp_nuovi_possessori_table.setFixedHeight(150)
        nuovi_poss_layout.addWidget(self.pp_nuovi_possessori_table)
        nuovi_poss_buttons_layout = QHBoxLayout()
        self.pp_btn_aggiungi_nuovo_possessore = QPushButton(
            QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder), # O QStyle.SP_FileLinkIcon o QStyle.SP_ToolBarAddButton
            " Aggiungi Possessore..."
        )
        self.pp_btn_aggiungi_nuovo_possessore.setToolTip("Aggiungi un nuovo possessore (o seleziona uno esistente) alla lista per la nuova partita")
        self.pp_btn_aggiungi_nuovo_possessore.clicked.connect(self._pp_aggiungi_nuovo_possessore)
        nuovi_poss_buttons_layout.addWidget(self.pp_btn_aggiungi_nuovo_possessore)
        
       # CORREZIONE ICONA QUI:
        self.pp_btn_rimuovi_nuovo_possessore = QPushButton(
            QApplication.style().standardIcon(QStyle.SP_TrashIcon), # O QStyle.SP_DialogDiscardButton
            " Rimuovi Selezionato"
        )
        self.pp_btn_rimuovi_nuovo_possessore = QPushButton(QApplication.style().standardIcon(QStyle.SP_TrashIcon), " Rimuovi Selezionato") # Esempio Icona
        self.pp_btn_rimuovi_nuovo_possessore.clicked.connect(self._pp_rimuovi_nuovo_possessore_selezionato)
        nuovi_poss_buttons_layout.addWidget(self.pp_btn_rimuovi_nuovo_possessore)
        nuovi_poss_buttons_layout.addStretch()
        nuovi_poss_layout.addLayout(nuovi_poss_buttons_layout)
        passaggio_main_layout_scroll.addWidget(nuovi_poss_group)

        self.pp_btn_esegui_passaggio = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton), " Esegui Passaggio Proprietà")
        self.pp_btn_esegui_passaggio.clicked.connect(self._esegui_passaggio_proprieta)
        passaggio_main_layout_scroll.addWidget(self.pp_btn_esegui_passaggio, 0, Qt.AlignRight)
        passaggio_main_layout_scroll.addStretch(1)
        
        passaggio_scroll.setWidget(passaggio_scroll_content_widget)
        passaggio_tab_layout.addWidget(passaggio_scroll)
        self.operazioni_tabs.addTab(passaggio_widget_main_container, "Passaggio Proprietà (Voltura)")


    # --- Metodi Helper e Handler ---
    def _load_partita_sorgente_from_spinbox(self):
        partita_id_val = self.source_partita_id_spinbox.value()
        if partita_id_val > 0:
            self.selected_partita_id_source = partita_id_val
            self._aggiorna_info_partita_sorgente()
        else:
            QMessageBox.warning(self, "ID Non Valido", "Inserire un ID partita sorgente valido.")
            self.selected_partita_id_source = None
            self._aggiorna_info_partita_sorgente() # Per resettare le label e tabelle

    def _cerca_partita_sorgente(self):
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_partita_id:
            self.selected_partita_id_source = dialog.selected_partita_id
            self.source_partita_id_spinbox.setValue(self.selected_partita_id_source)
            self._aggiorna_info_partita_sorgente()
        else:
            # Non resettare selected_partita_id_source se l'utente annulla, 
            # potrebbe voler mantenere la selezione precedente se c'era
            if not self.selected_partita_id_source: # Resetta solo se non c'era già una selezione
                self.source_partita_info_label.setText("Nessuna partita sorgente selezionata.")
                self.selected_partita_comune_id_source = None
                self.selected_partita_comune_nome_source = None
                if hasattr(self, 'immobili_partita_sorgente_table'): self.immobili_partita_sorgente_table.setRowCount(0)
                if hasattr(self, 'pp_immobili_da_selezionare_table'): self.pp_immobili_da_selezionare_table.setRowCount(0)
                if hasattr(self, 'pp_nuova_partita_comune_label'): self.pp_nuova_partita_comune_label.setText("Il comune sarà lo stesso della partita sorgente.")

    def _aggiorna_info_partita_sorgente(self):
        if self.selected_partita_id_source:
            partita_details = self.db_manager.get_partita_details(self.selected_partita_id_source)
            if partita_details:
                self.selected_partita_comune_id_source = partita_details.get('comune_id')
                self.selected_partita_comune_nome_source = partita_details.get('comune_nome', 'N/D')
                self.source_partita_info_label.setText(
                    f"Partita Sorgente: N. {partita_details.get('numero_partita')} "
                    f"(Comune: {self.selected_partita_comune_nome_source} [ID: {self.selected_partita_comune_id_source}], Partita ID: {self.selected_partita_id_source})"
                )
                immobili = partita_details.get('immobili', [])
                if hasattr(self, '_carica_immobili_partita_sorgente'): self._carica_immobili_partita_sorgente(immobili)
                if hasattr(self, '_pp_carica_immobili_per_selezione'): self._pp_carica_immobili_per_selezione(immobili)
                if hasattr(self, 'pp_nuova_partita_comune_label'):
                    self.pp_nuova_partita_comune_label.setText(
                        f"{self.selected_partita_comune_nome_source} (ID: {self.selected_partita_comune_id_source})"
                    )
            else: # Partita non trovata
                self.source_partita_info_label.setText(f"Partita ID {self.selected_partita_id_source} non trovata.")
                self.selected_partita_id_source = None; self.selected_partita_comune_id_source = None; self.selected_partita_comune_nome_source = None
                if hasattr(self, 'immobili_partita_sorgente_table'): self.immobili_partita_sorgente_table.setRowCount(0)
                if hasattr(self, 'pp_immobili_da_selezionare_table'): self.pp_immobili_da_selezionare_table.setRowCount(0)
                if hasattr(self, 'pp_nuova_partita_comune_label'): self.pp_nuova_partita_comune_label.setText("Selezionare una partita sorgente valida.")
        else: # Nessun ID sorgente valido
             self.source_partita_info_label.setText("Nessuna partita sorgente selezionata o ID non valido.")
             self.selected_partita_comune_id_source = None; self.selected_partita_comune_nome_source = None
             if hasattr(self, 'immobili_partita_sorgente_table'): self.immobili_partita_sorgente_table.setRowCount(0)
             if hasattr(self, 'pp_immobili_da_selezionare_table'): self.pp_immobili_da_selezionare_table.setRowCount(0)
             if hasattr(self, 'pp_nuova_partita_comune_label'): self.pp_nuova_partita_comune_label.setText("Selezionare una partita sorgente.")

    def _esegui_duplicazione_partita(self):
        if self.selected_partita_id_source is None:
            QMessageBox.warning(self, "Selezione Mancante", "Selezionare una partita sorgente prima di duplicare.")
            return
        if self.selected_partita_comune_id_source is None:
            QMessageBox.warning(self, "Errore Interno", "Comune della partita sorgente non determinato. Caricare la partita sorgente.")
            return

        nuovo_numero = self.nuovo_numero_partita_spinbox.value()
        if nuovo_numero <= 0:
            QMessageBox.warning(self, "Dati Non Validi", "Il nuovo numero di partita deve essere un valore positivo.")
            self.nuovo_numero_partita_spinbox.setFocus(); return
        
        try:
            existing_partita = self.db_manager.search_partite(
                comune_id=self.selected_partita_comune_id_source,
                numero_partita=nuovo_numero
            )
            if existing_partita:
                QMessageBox.warning(self, "Errore Duplicazione", 
                                    f"Esiste già una partita con il numero {nuovo_numero} "
                                    f"nel comune '{self.selected_partita_comune_nome_source}'. Scegliere un numero diverso.")
                self.nuovo_numero_partita_spinbox.setFocus(); return
        except DBMError as e:
             QMessageBox.critical(self, "Errore Verifica Partita", f"Errore durante la verifica della partita esistente:\n{str(e)}"); return

        mant_poss = self.duplica_mantieni_poss_check.isChecked()
        mant_imm = self.duplica_mantieni_imm_check.isChecked()

        try:
            success = self.db_manager.duplicate_partita(
                self.selected_partita_id_source, nuovo_numero, mant_poss, mant_imm
            )
            if success:
                QMessageBox.information(self, "Successo", 
                                        f"Partita ID {self.selected_partita_id_source} duplicata con successo "
                                        f"con nuovo numero partita {nuovo_numero}.")
                self.nuovo_numero_partita_spinbox.setValue(self.nuovo_numero_partita_spinbox.minimum()) 
                self.duplica_mantieni_poss_check.setChecked(True)
                self.duplica_mantieni_imm_check.setChecked(False)
        except DBMError as e:
            QMessageBox.critical(self, "Errore Duplicazione", f"Errore durante la duplicazione:\n{str(e)}")
        except Exception as e_gen:
            gui_logger.critical(f"Errore imprevisto duplicazione: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore:\n{type(e_gen).__name__}: {str(e_gen)}")

    def _carica_immobili_partita_sorgente(self, immobili_data: List[Dict[str,Any]]):
        table = self.immobili_partita_sorgente_table
        table.setRowCount(0)
        table.setSortingEnabled(False)
        self.selected_immobile_id_transfer = None 
        self.immobile_id_transfer_label.setText("Nessun immobile selezionato.")
        if immobili_data:
            table.setRowCount(len(immobili_data))
            for row, immobile in enumerate(immobili_data):
                table.setItem(row, 0, QTableWidgetItem(str(immobile.get('id'))))
                table.setItem(row, 1, QTableWidgetItem(immobile.get('natura')))
                loc_text = f"{immobile.get('localita_nome', '')} {immobile.get('civico', '')}".strip()
                table.setItem(row, 2, QTableWidgetItem(loc_text))
            table.resizeColumnsToContents()
        else:
            table.setRowCount(1)
            no_imm_item = QTableWidgetItem("Nessun immobile associato a questa partita.")
            no_imm_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(0,0,no_imm_item)
            table.setSpan(0,0,1,table.columnCount())
        table.setSortingEnabled(True)

    def _immobile_sorgente_selezionato(self):
        selected_rows = self.immobili_partita_sorgente_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_immobile_id_transfer = None
            self.immobile_id_transfer_label.setText("Nessun immobile selezionato.")
            return
        
        row = selected_rows[0].row()
        id_item = self.immobili_partita_sorgente_table.item(row, 0)
        natura_item = self.immobili_partita_sorgente_table.item(row, 1)
        if id_item and id_item.text().isdigit():
            self.selected_immobile_id_transfer = int(id_item.text())
            natura_text = natura_item.text() if natura_item else "N/D"
            self.immobile_id_transfer_label.setText(f"Immobile da trasferire: ID {self.selected_immobile_id_transfer} ({natura_text})")
        else:
            self.selected_immobile_id_transfer = None
            self.immobile_id_transfer_label.setText("Selezione immobile non valida (ID mancante o non numerico).")

    def _cerca_partita_destinazione(self):
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_partita_id:
            self.dest_partita_id_spinbox.setValue(dialog.selected_partita_id)
            partita_details = self.db_manager.get_partita_details(dialog.selected_partita_id)
            if partita_details:
                self.dest_partita_info_label.setText(
                    f"Destinazione: N. {partita_details.get('numero_partita')} "
                    f"(Comune: {partita_details.get('comune_nome', 'N/D')} [ID: {partita_details.get('comune_id')}], Partita ID: {dialog.selected_partita_id})"
                )
            else:
                self.dest_partita_info_label.setText(f"Partita destinazione ID {dialog.selected_partita_id} non trovata.")
        else:
             self.dest_partita_info_label.setText("Nessuna partita destinazione selezionata.")

    def _esegui_trasferimento_immobile(self):
        if self.selected_immobile_id_transfer is None:
            QMessageBox.warning(self, "Selezione Mancante", "Selezionare un immobile dalla partita sorgente da trasferire.")
            return
        id_partita_dest = self.dest_partita_id_spinbox.value()
        if id_partita_dest <= 0:
            QMessageBox.warning(self, "Dati Non Validi", "Selezionare o inserire un ID partita di destinazione valido.")
            return
        if self.selected_partita_id_source is not None and id_partita_dest == self.selected_partita_id_source:
            QMessageBox.warning(self, "Operazione Non Valida", "La partita di destinazione non può essere uguale alla partita sorgente.")
            return

        registra_var = self.transfer_registra_var_check.isChecked()
        try:
            success = self.db_manager.transfer_immobile(
                self.selected_immobile_id_transfer, id_partita_dest, registra_var
            )
            if success:
                QMessageBox.information(self, "Successo",
                                        f"Immobile ID {self.selected_immobile_id_transfer} trasferito "
                                        f"alla partita ID {id_partita_dest} con successo.")
                self._aggiorna_info_partita_sorgente() # Ricarica immobili sorgente
                self.dest_partita_id_spinbox.setValue(self.dest_partita_id_spinbox.minimum())
                self.dest_partita_info_label.setText("Nessuna partita destinazione selezionata.")
                self.transfer_registra_var_check.setChecked(False)
        except DBMError as e:
            QMessageBox.critical(self, "Errore Trasferimento", f"Errore durante il trasferimento dell'immobile:\n{str(e)}")
        except Exception as e_gen:
            gui_logger.critical(f"Errore imprevisto trasferimento immobile: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore:\n{type(e_gen).__name__}: {str(e_gen)}")

    def _toggle_selezione_immobili_pp(self, checked: bool):
        if hasattr(self, 'pp_immobili_da_selezionare_table'):
            self.pp_immobili_da_selezionare_table.setVisible(not checked)
            if checked and hasattr(self, '_pp_pulisci_selezione_immobili_specifici'):
                self._pp_pulisci_selezione_immobili_specifici()
            
    def _pp_pulisci_selezione_immobili_specifici(self):
        if hasattr(self, 'pp_immobili_da_selezionare_table'):
            table = self.pp_immobili_da_selezionare_table
            for row in range(table.rowCount()):
                cell_widget = table.cellWidget(row, 0) 
                if isinstance(cell_widget, QCheckBox): cell_widget.setChecked(False)

    def _pp_carica_immobili_per_selezione(self, immobili_data: List[Dict[str, Any]]):
        if not hasattr(self, 'pp_immobili_da_selezionare_table'):
            gui_logger.error("Tabella 'pp_immobili_da_selezionare_table' non inizializzata.")
            return
        table = self.pp_immobili_da_selezionare_table; table.setRowCount(0); table.setSortingEnabled(False)
        if immobili_data:
            table.setRowCount(len(immobili_data))
            for row, immobile in enumerate(immobili_data):
                chk = QCheckBox(); chk.setProperty("immobile_id", immobile.get('id')); table.setCellWidget(row, 0, chk)
                id_i = QTableWidgetItem(str(immobile.get('id','N/D'))); id_i.setFlags(id_i.flags() & ~Qt.ItemIsEditable); table.setItem(row, 1, id_i)
                nat_i = QTableWidgetItem(immobile.get('natura','N/D')); nat_i.setFlags(nat_i.flags() & ~Qt.ItemIsEditable); table.setItem(row, 2, nat_i)
                loc_t = f"{immobile.get('localita_nome', '')} {immobile.get('civico', '')}".strip(); loc_i = QTableWidgetItem(loc_t); loc_i.setFlags(loc_i.flags() & ~Qt.ItemIsEditable); table.setItem(row, 3, loc_i)
            # Configurazione resize mode per le colonne
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed) # Checkbox
            table.setColumnWidth(0, 35) 
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents) # ID
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # Natura
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch) # Località
        else: 
            table.setRowCount(1)
            msg_item = QTableWidgetItem("Nessun immobile disponibile nella partita sorgente per la selezione.")
            msg_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(0, 0, msg_item); table.setSpan(0, 0, 1, table.columnCount())
        table.setSortingEnabled(True)

    def _pp_aggiungi_nuovo_possessore(self):
        if not self.selected_partita_comune_id_source:
            QMessageBox.warning(self, "Comune Mancante", "Selezionare una partita sorgente per determinare il comune di riferimento dei nuovi possessori.")
            return
        dialog_sel_poss = PossessoreSelectionDialog(self.db_manager, self.selected_partita_comune_id_source, self)
        dialog_sel_poss.setWindowTitle("Seleziona o Crea Nuovo Possessore per Nuova Partita")
        possessore_info_completa_sel = None
        if dialog_sel_poss.exec_() == QDialog.Accepted:
            if hasattr(dialog_sel_poss, 'selected_possessore') and dialog_sel_poss.selected_possessore:
                poss_id_sel = dialog_sel_poss.selected_possessore.get('id')
                if poss_id_sel:
                    dettagli_poss_db = self.db_manager.get_possessore_full_details(poss_id_sel)
                    if dettagli_poss_db: possessore_info_completa_sel = dettagli_poss_db
                    else: QMessageBox.warning(self, "Errore", f"Impossibile recuperare dettagli per possessore ID {poss_id_sel}."); return
                else: QMessageBox.warning(self, "Errore", "Nessun ID possessore valido dalla selezione."); return
            else: gui_logger.warning("PossessoreSelectionDialog non ha restituito 'selected_possessore'."); return
        else: gui_logger.info("Aggiunta possessore per PP annullata (selezione/creazione)."); return

        if not possessore_info_completa_sel or possessore_info_completa_sel.get('id') is None:
            QMessageBox.warning(self, "Errore", "Dati del possessore non validi."); return

        dettagli_leg = DettagliLegamePossessoreDialog.get_details_for_new_legame(
            nome_possessore=possessore_info_completa_sel.get("nome_completo", "N/D"), 
            tipo_partita_attuale='principale', parent=self
        )
        if dettagli_leg:
            self._pp_temp_nuovi_possessori.append({
                "possessore_id": possessore_info_completa_sel.get("id"), 
                "nome_completo": possessore_info_completa_sel.get("nome_completo"),
                "cognome_nome": possessore_info_completa_sel.get("cognome_nome"),
                "paternita": possessore_info_completa_sel.get("paternita"),
                "comune_riferimento_id": possessore_info_completa_sel.get("comune_riferimento_id"),
                "attivo": possessore_info_completa_sel.get("attivo", True),
                "titolo": dettagli_leg["titolo"],    
                "quota": dettagli_leg["quota"]       
            })
            self._pp_aggiorna_tabella_nuovi_possessori()
        else: gui_logger.info("Aggiunta dettagli legame per PP annullata.")

    def _pp_rimuovi_nuovo_possessore_selezionato(self):
        selected_rows = self.pp_nuovi_possessori_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un possessore dalla lista dei nuovi possessori da rimuovere.")
            return
        row_to_remove = selected_rows[0].row()
        if 0 <= row_to_remove < len(self._pp_temp_nuovi_possessori):
            del self._pp_temp_nuovi_possessori[row_to_remove]
            self._pp_aggiorna_tabella_nuovi_possessori()

    def _pp_aggiorna_tabella_nuovi_possessori(self):
        table = self.pp_nuovi_possessori_table
        table.setRowCount(0); table.setSortingEnabled(False)
        if self._pp_temp_nuovi_possessori:
            table.setRowCount(len(self._pp_temp_nuovi_possessori))
            for r, pd in enumerate(self._pp_temp_nuovi_possessori):
                table.setItem(r,0,QTableWidgetItem(str(pd.get("possessore_id"))))
                table.setItem(r,1,QTableWidgetItem(pd.get("nome_completo")))
                table.setItem(r,2,QTableWidgetItem(pd.get("titolo")))
                table.setItem(r,3,QTableWidgetItem(pd.get("quota","")))
            table.resizeColumnsToContents()
        table.setSortingEnabled(True)

    def _esegui_passaggio_proprieta(self):
        gui_logger.info("Avvio _esegui_passaggio_proprieta.")
        if self.selected_partita_id_source is None or self.selected_partita_comune_id_source is None:
            QMessageBox.warning(self, "Selezione Mancante", "Selezionare una partita sorgente valida."); return
        
        nuova_part_num = self.pp_nuova_partita_numero_spinbox.value()
        if nuova_part_num <= 0:
            QMessageBox.warning(self, "Dati Mancanti", "Numero nuova partita non valido."); self.pp_nuova_partita_numero_spinbox.setFocus(); return
        
        try:
            existing_partita_check = self.db_manager.search_partite(comune_id=self.selected_partita_comune_id_source, numero_partita=nuova_part_num)
            if existing_partita_check:
                QMessageBox.warning(self, "Errore Creazione Partita", f"Partita N.{nuova_part_num} già esistente nel comune '{self.selected_partita_comune_nome_source}'."); self.pp_nuova_partita_numero_spinbox.setFocus(); return
        except DBMError as e:
             QMessageBox.critical(self, "Errore Verifica Partita", f"Errore verifica partita esistente:\n{str(e)}"); return

        tipo_variazione = self.pp_tipo_variazione_combo.currentText()
        data_variazione_q = self.pp_data_variazione_edit.date()
        tipo_contratto = self.pp_tipo_contratto_edit.text().strip()
        data_contratto_q = self.pp_data_contratto_edit.date()

        if not tipo_variazione: QMessageBox.warning(self, "Dati Atto Mancanti", "Selezionare un Tipo Variazione."); self.pp_tipo_variazione_combo.setFocus(); return
        if data_variazione_q.isNull() or not tipo_contratto or data_contratto_q.isNull():
            QMessageBox.warning(self, "Dati Atto Mancanti", "Data Variazione, Tipo Atto/Contratto e Data Atto/Contratto sono obbligatori."); return
        
        data_variazione = data_variazione_q.toPyDate(); data_contratto = data_contratto_q.toPyDate()
        notaio = self.pp_notaio_edit.text().strip() or None; repertorio = self.pp_repertorio_edit.text().strip() or None
        note_v = self.pp_note_variazione_edit.toPlainText().strip() or None

        if not self._pp_temp_nuovi_possessori:
            QMessageBox.warning(self, "Possessori Mancanti", "Aggiungere almeno un nuovo possessore."); return

        imm_ids_trasf: List[int] = []
        if self.pp_trasferisci_tutti_immobili_check.isChecked():
            source_table_immobili = self.immobili_partita_sorgente_table
            for r in range(source_table_immobili.rowCount()):
                 id_itm_widget = source_table_immobili.item(r,0)
                 if id_itm_widget and id_itm_widget.text().isdigit(): imm_ids_trasf.append(int(id_itm_widget.text()))
        else:
            sel_tbl_imm = self.pp_immobili_da_selezionare_table
            for r in range(sel_tbl_imm.rowCount()):
                chk_widget = sel_tbl_imm.cellWidget(r,0)
                if isinstance(chk_widget, QCheckBox) and chk_widget.isChecked():
                    id_itm_widget = sel_tbl_imm.item(r,1) 
                    if id_itm_widget and id_itm_widget.text().isdigit(): imm_ids_trasf.append(int(id_itm_widget.text()))
            if not imm_ids_trasf:
                QMessageBox.warning(self, "Immobili Mancanti", "Selezionare immobili da trasferire."); return
        
        lista_possessori_per_db = []
        for poss_data_ui in self._pp_temp_nuovi_possessori:
            dati_per_json = {
                "possessore_id": poss_data_ui.get("possessore_id"),
                "nome_completo": poss_data_ui.get("nome_completo"),
                "cognome_nome": poss_data_ui.get("cognome_nome"),
                "paternita": poss_data_ui.get("paternita"),
                "comune_id": poss_data_ui.get("comune_riferimento_id"),
                "attivo": poss_data_ui.get("attivo", True),
                "titolo": poss_data_ui.get("titolo"),
                "quota": poss_data_ui.get("quota")
            }
            lista_possessori_per_db.append(dati_per_json)
        gui_logger.debug(f"PP: Lista possessori inviata al DBManager: {lista_possessori_per_db}")

        try:
            success = self.db_manager.registra_passaggio_proprieta(
                partita_origine_id=self.selected_partita_id_source, 
                comune_id_nuova_partita=self.selected_partita_comune_id_source,
                numero_nuova_partita=nuova_part_num, 
                tipo_variazione=tipo_variazione, data_variazione=data_variazione,
                tipo_contratto=tipo_contratto, data_contratto=data_contratto, 
                notaio=notaio, repertorio=repertorio,
                nuovi_possessori_list=lista_possessori_per_db, 
                immobili_da_trasferire_ids=imm_ids_trasf if imm_ids_trasf else None,
                note_variazione=note_v
            )
            if success:
                QMessageBox.information(self, "Successo", "Passaggio di proprietà registrato con successo.")
                self.pp_nuova_partita_numero_spinbox.setValue(self.pp_nuova_partita_numero_spinbox.minimum())
                if self.pp_tipo_variazione_combo.count() > 0: self.pp_tipo_variazione_combo.setCurrentIndex(0) 
                self.pp_data_variazione_edit.setDate(QDate.currentDate())
                self.pp_tipo_contratto_edit.clear(); self.pp_data_contratto_edit.setDate(QDate.currentDate())
                self.pp_notaio_edit.clear(); self.pp_repertorio_edit.clear(); self.pp_note_variazione_edit.clear()
                self.pp_trasferisci_tutti_immobili_check.setChecked(True) 
                self._pp_temp_nuovi_possessori.clear(); self._pp_aggiorna_tabella_nuovi_possessori()
                self._aggiorna_info_partita_sorgente()
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            gui_logger.error(f"Errore durante la registrazione del passaggio di proprietà: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Errore Operazione", f"Impossibile registrare il passaggio di proprietà:\n{str(e)}")
        except Exception as e_gen:
            gui_logger.critical(f"Errore imprevisto passaggio proprietà: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto", f"Errore imprevisto:\n{type(e_gen).__name__}: {str(e_gen)}")

class ModificaPossessoreDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, possessore_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.possessore_id = possessore_id
        self.possessore_data_originale = None 
        # Per l'audit, se vuoi confrontare i dati vecchi e nuovi
        # self.current_user_info = getattr(QApplication.instance().main_window, 'logged_in_user_info', None) # Modo per prendere utente
                                                                                                        # se main_window è accessibile

        self.setWindowTitle(f"Modifica Dati Possessore ID: {self.possessore_id}")
        self.setMinimumWidth(450)

        self._init_ui()
        self._load_possessore_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.id_label = QLabel(str(self.possessore_id))
        form_layout.addRow("ID Possessore:", self.id_label)

        self.nome_completo_edit = QLineEdit()
        form_layout.addRow("Nome Completo (*):", self.nome_completo_edit)
        
        self.cognome_nome_edit = QLineEdit() # Campo che avevi nello schema per ricerca/ordinamento
        form_layout.addRow("Cognome e Nome (per ricerca):", self.cognome_nome_edit)

        self.paternita_edit = QLineEdit()
        form_layout.addRow("Paternità:", self.paternita_edit)

        self.attivo_checkbox = QCheckBox("Possessore Attivo")
        form_layout.addRow(self.attivo_checkbox)

        # Comune di Riferimento
        comune_ref_layout = QHBoxLayout()
        self.comune_ref_label = QLabel("Comune non specificato") # Verrà popolato
        self.btn_cambia_comune_ref = QPushButton("Cambia...")
        self.btn_cambia_comune_ref.clicked.connect(self._cambia_comune_riferimento)
        comune_ref_layout.addWidget(self.comune_ref_label)
        comune_ref_layout.addStretch()
        comune_ref_layout.addWidget(self.btn_cambia_comune_ref)
        form_layout.addRow("Comune di Riferimento:", comune_ref_layout)
        
        # ID del comune di riferimento (nascosto, ma utile da tenere)
        self.selected_comune_ref_id: Optional[int] = None


        # Aggiungere qui altri campi se vuoi estendere la tabella possessore
        # self.codice_fiscale_edit = QLineEdit()
        # form_layout.addRow("Codice Fiscale:", self.codice_fiscale_edit)
        # self.data_nascita_edit = QDateEdit()
        # self.data_nascita_edit.setCalendarPopup(True) ...
        # form_layout.addRow("Data Nascita:", self.data_nascita_edit)

        layout.addLayout(form_layout)

        # Pulsanti
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton), "Salva Modifiche")
        self.save_button.clicked.connect(self._save_changes)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def _load_possessore_data(self):
        # Metodo da creare in CatastoDBManager: get_possessore_details(possessore_id)
        # Dovrebbe restituire un dizionario con tutti i campi di possessore,
        # incluso comune_id e il nome del comune (comune_riferimento_nome).
        self.possessore_data_originale = self.db_manager.get_possessore_full_details(self.possessore_id) # Rinominato per chiarezza

        if not self.possessore_data_originale:
            QMessageBox.critical(self, "Errore Caricamento",
                                 f"Impossibile caricare i dati per il possessore ID: {self.possessore_id}.\n"
                                 "Il dialogo verrà chiuso.")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, self.reject) # Chiudi dopo che il messaggio è stato processato
            return

        self.nome_completo_edit.setText(self.possessore_data_originale.get('nome_completo', ''))
        self.cognome_nome_edit.setText(self.possessore_data_originale.get('cognome_nome', '')) # Campo cognome_nome
        self.paternita_edit.setText(self.possessore_data_originale.get('paternita', ''))
        self.attivo_checkbox.setChecked(self.possessore_data_originale.get('attivo', True))
        
        self.selected_comune_ref_id = self.possessore_data_originale.get('comune_riferimento_id') # Salva l'ID
        nome_comune_ref = self.possessore_data_originale.get('comune_riferimento_nome', "Nessun comune assegnato")
        self.comune_ref_label.setText(f"{nome_comune_ref} (ID: {self.selected_comune_ref_id or 'N/A'})")


    def _cambia_comune_riferimento(self):
        # Usa ComuneSelectionDialog per cambiare il comune di riferimento
        dialog = ComuneSelectionDialog(self.db_manager, self, title="Seleziona Nuovo Comune di Riferimento")
        if dialog.exec_() == QDialog.Accepted and dialog.selected_comune_id:
            self.selected_comune_ref_id = dialog.selected_comune_id
            self.comune_ref_label.setText(f"{dialog.selected_comune_name} (ID: {self.selected_comune_ref_id})")
            gui_logger.info(f"Nuovo comune di riferimento selezionato per possessore (non ancora salvato): ID {self.selected_comune_ref_id}, Nome: {dialog.selected_comune_name}")


    def _save_changes(self):
        gui_logger.info(f"DEBUG: _save_changes chiamato per possessore ID {self.possessore_id}") # NUOVA STAMPA
        dati_modificati = {
            "nome_completo": self.nome_completo_edit.text().strip(),
            "cognome_nome": self.cognome_nome_edit.text().strip() or None, # Può essere nullo
            "paternita": self.paternita_edit.text().strip() or None,    # Può essere nullo
            "attivo": self.attivo_checkbox.isChecked(),
            "comune_riferimento_id": self.selected_comune_ref_id, # L'ID del comune selezionato
        }
        gui_logger.info(f"DEBUG: Dati dalla UI: {dati_modificati}") # NUOVA STAMPA


        if not dati_modificati["nome_completo"]:
            QMessageBox.warning(self, "Dati Mancanti", "Il 'Nome Completo' del possessore è obbligatorio.")
            self.nome_completo_edit.setFocus()
            return
        
        if dati_modificati["comune_riferimento_id"] is None:
            QMessageBox.warning(self, "Dati Mancanti", "Il 'Comune di Riferimento' è obbligatorio.")
            # Non c'è un campo input diretto per il focus, ma l'utente deve usare il pulsante
            self.btn_cambia_comune_ref.setFocus()
            return

        try:
            gui_logger.info(f"DEBUG: Chiamata a db_manager.update_possessore per ID {self.possessore_id}") # NUOVA STAMPA
            gui_logger.info(f"Tentativo di aggiornare il possessore ID {self.possessore_id} con i dati: {dati_modificati}")
            # Metodo da creare in CatastoDBManager: update_possessore(possessore_id, dati_modificati)
            self.db_manager.update_possessore(self.possessore_id, dati_modificati)
            
            gui_logger.info(f"Possessore ID {self.possessore_id} aggiornato con successo.")
            gui_logger.info(f"DEBUG: db_manager.update_possessore completato per ID {self.possessore_id}") # NUOVA STAMPA
            self.accept() # Chiude il dialogo e restituisce QDialog.Accepted

        # Gestione eccezioni simile a quella di update_partita (DBUniqueConstraintError, DBDataError, DBMError, etc.)
        # Ad esempio, se nome_completo + comune_id deve essere univoco, o altri vincoli.
        # Per ora, un gestore generico per errori DB e altri errori.
        except (DBMError, DBDataError) as dbe_poss: # Usa le tue eccezioni personalizzate
            gui_logger.error(f"Errore DB durante aggiornamento possessore ID {self.possessore_id}: {dbe_poss}", exc_info=True)
            QMessageBox.critical(self, "Errore Database",
                                 f"Errore durante il salvataggio delle modifiche al possessore:\n{dbe_poss.message if hasattr(dbe_poss, 'message') else str(dbe_poss)}")
        except AttributeError as ae:
            gui_logger.critical(f"Metodo 'update_possessore' non trovato o altro AttributeError: {ae}", exc_info=True)
            QMessageBox.critical(self, "Errore Implementazione", "Funzionalità per aggiornare possessore non completamente implementata o errore interno.")
        except Exception as e_poss:
            gui_logger.critical(f"Errore critico imprevisto durante il salvataggio del possessore ID {self.possessore_id}: {e_poss}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto",
                                 f"Si è verificato un errore di sistema imprevisto:\n{type(e_poss).__name__}: {e_poss}")

class DettagliLegamePossessoreDialog(QDialog):
    def __init__(self, nome_possessore_selezionato: str, partita_tipo: str, 
                 titolo_attuale: Optional[str] = None, # Nuovo
                 quota_attuale: Optional[str] = None,   # Nuovo
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Dettagli Legame per {nome_possessore_selezionato}")
        self.setMinimumWidth(400)

        self.titolo: Optional[str] = None
        self.quota: Optional[str] = None
        # self.tipo_partita_rel: str = partita_tipo

        layout = QFormLayout(self)

        self.titolo_edit = QLineEdit()
        self.titolo_edit.setPlaceholderText("Es. proprietà esclusiva, usufrutto")
        self.titolo_edit.setText(titolo_attuale if titolo_attuale is not None else "proprietà esclusiva") # Pre-compila
        layout.addRow("Titolo di Possesso (*):", self.titolo_edit)

        self.quota_edit = QLineEdit()
        self.quota_edit.setPlaceholderText("Es. 1/1, 1/2 (lasciare vuoto se non applicabile)")
        self.quota_edit.setText(quota_attuale if quota_attuale is not None else "") # Pre-compila
        layout.addRow("Quota (opzionale):", self.quota_edit)

        # ... (pulsanti OK/Annulla e metodo _accept_details come prima) ...
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogOkButton), "OK")
        self.ok_button.clicked.connect(self._accept_details)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addRow(buttons_layout)
        self.setLayout(layout)
        self.titolo_edit.setFocus()

    def _accept_details(self):
        # ... (come prima) ...
        titolo_val = self.titolo_edit.text().strip()
        if not titolo_val:
            QMessageBox.warning(self, "Dato Mancante", "Il titolo di possesso è obbligatorio.")
            self.titolo_edit.setFocus()
            return
        self.titolo = titolo_val
        self.quota = self.quota_edit.text().strip() or None
        self.accept()


    # Metodo statico per l'inserimento (come prima)
    @staticmethod
    def get_details_for_new_legame(nome_possessore: str, tipo_partita_attuale: str, parent=None) -> Optional[Dict[str, Any]]:
        # Chiamiamo il costruttore senza titolo_attuale e quota_attuale,
        # così userà i default (None) e quindi il testo placeholder o il default "proprietà esclusiva"
        dialog = DettagliLegamePossessoreDialog(
            nome_possessore_selezionato=nome_possessore,
            partita_tipo=tipo_partita_attuale,
            # titolo_attuale e quota_attuale non vengono passati,
            # quindi __init__ userà i loro valori di default (None)
            parent=parent
        )
        if dialog.exec_() == QDialog.Accepted:
            return {
                "titolo": dialog.titolo,
                "quota": dialog.quota,
                # "tipo_partita_rel": dialog.tipo_partita_rel # Se lo gestisci
            }
        return None

    # NUOVO Metodo statico per la modifica
    @staticmethod
    def get_details_for_edit_legame(nome_possessore: str, tipo_partita_attuale: str, 
                                    titolo_init: str, quota_init: Optional[str], 
                                    parent=None) -> Optional[Dict[str, Any]]:
        dialog = DettagliLegamePossessoreDialog(nome_possessore, tipo_partita_attuale, 
                                                titolo_attuale=titolo_init, 
                                                quota_attuale=quota_init, 
                                                parent=parent)
        dialog.setWindowTitle(f"Modifica Legame per {nome_possessore}") # Titolo specifico per modifica
        if dialog.exec_() == QDialog.Accepted:
            return {
                "titolo": dialog.titolo,
                "quota": dialog.quota,
            }
        return None
    



# All'interno della classe PossessoriComuneDialog in prova.py

class PossessoriComuneDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, nome_comune: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.nome_comune = nome_comune

        self.setWindowTitle(f"Possessori del Comune di {self.nome_comune} (ID: {self.comune_id})")
        self.setMinimumSize(800, 500)

        layout = QVBoxLayout(self)

        # Tabella Possessori (come prima)
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(5)
        self.possessori_table.setHorizontalHeaderLabels([
            "ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Stato"
        ])
        self.possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.setSelectionMode(QTableWidget.SingleSelection)
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # o ResizeToContents
        self.possessori_table.setSortingEnabled(True)
        self.possessori_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_azione) # NUOVO
        self.possessori_table.itemDoubleClicked.connect(self.apri_modifica_possessore_selezionato) # NUOVO per doppio click

        layout.addWidget(self.possessori_table)

        # --- NUOVI Pulsanti di Azione ---
        action_layout = QHBoxLayout()
        self.btn_modifica_possessore = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Modifica Selezionato")
        self.btn_modifica_possessore.setToolTip("Modifica i dati del possessore selezionato")
        self.btn_modifica_possessore.clicked.connect(self.apri_modifica_possessore_selezionato)
        self.btn_modifica_possessore.setEnabled(False) # Inizialmente disabilitato
        action_layout.addWidget(self.btn_modifica_possessore)
        
        action_layout.addStretch() # Spazio

        self.close_button = QPushButton("Chiudi") # Pulsante Chiudi esistente
        self.close_button.clicked.connect(self.accept)
        action_layout.addWidget(self.close_button)
        
        layout.addLayout(action_layout)
        # --- FINE NUOVI Pulsanti di Azione ---

        self.setLayout(layout)
        self.load_possessori_data()

    def _aggiorna_stato_pulsanti_azione(self): # NUOVO METODO
        """Abilita/disabilita i pulsanti di azione in base alla selezione nella tabella."""
        has_selection = bool(self.possessori_table.selectedItems())
        self.btn_modifica_possessore.setEnabled(has_selection)

    def _get_selected_possessore_id(self) -> Optional[int]: # NUOVO METODO HELPER
        """Restituisce l'ID del possessore attualmente selezionato nella tabella."""
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            return None
        
        current_row = self.possessori_table.currentRow()
        if current_row < 0:
            return None
            
        id_item = self.possessori_table.item(current_row, 0) # Colonna ID Poss.
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def apri_modifica_possessore_selezionato(self):
        gui_logger.debug("DEBUG: apri_modifica_possessore_selezionato chiamato.") # NUOVA STAMPA
        possessore_id = self._get_selected_possessore_id()
        if possessore_id is not None:
            gui_logger.debug(f"DEBUG: ID Possessore selezionato: {possessore_id}") # NUOVA STAMPA
            dialog = ModificaPossessoreDialog(self.db_manager, possessore_id, self)
            
            dialog_result = dialog.exec_() # Salva il risultato
            gui_logger.debug(f"DEBUG: ModificaPossessoreDialog.exec_() restituito: {dialog_result} (Accepted è {QDialog.Accepted})") # NUOVA STAMPA

            if dialog_result == QDialog.Accepted:
                gui_logger.info("DEBUG: ModificaPossessoreDialog accettato. Ricaricamento dati possessori...") # NUOVA STAMPA
                QMessageBox.information(self, "Modifica Possessore", 
                                        "Modifiche al possessore salvate con successo.")
                self.load_possessori_data()
            else:
                gui_logger.info("DEBUG: ModificaPossessoreDialog non accettato (probabilmente Annulla o errore nel salvataggio).") # NUOVA STAMPA
        else:
            gui_logger.warning("DEBUG: Tentativo di modificare possessore, ma nessun ID selezionato.") # NUOVA STAMPA
            QMessageBox.warning(self, "Nessuna Selezione", 
                                "Per favore, seleziona un possessore dalla tabella da modificare.")


    def load_possessori_data(self):
        """Carica i possessori per il comune specificato."""
        self.possessori_table.setRowCount(0)
        self.possessori_table.setSortingEnabled(False)
        try:
            possessori_list = self.db_manager.get_possessori_by_comune(self.comune_id)
            if possessori_list:
                self.possessori_table.setRowCount(len(possessori_list))
                for row_idx, possessore in enumerate(possessori_list):
                    col = 0
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(str(possessore.get('id', '')))); col+=1
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(possessore.get('nome_completo', ''))); col+=1
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(possessore.get('cognome_nome', ''))); col+=1
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(possessore.get('paternita', ''))); col+=1
                    stato_str = "Attivo" if possessore.get('attivo', False) else "Non Attivo"
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(stato_str)); col+=1
                self.possessori_table.resizeColumnsToContents()
            else:
                gui_logger.info(f"Nessun possessore trovato per il comune ID: {self.comune_id}")
        # ... (gestione eccezioni come prima) ...
        except Exception as e:
            gui_logger.error(f"Errore durante il caricamento dei possessori per comune ID {self.comune_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
        finally:
            self.possessori_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_azione() # Aggiorna stato pulsanti dopo caricamento


    # Rimuovi la vecchia logica di itemDoubleClicked se ora fa la stessa cosa di apri_modifica...
    # def apri_dettaglio_possessore_selezionato(self, item): ...
             
# --- Scheda per Inserimento Possessore ---

class InserimentoPossessoreWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comuni_list_data: List[Dict[str, Any]] = [] # Per memorizzare i dati dei comuni
        self.selected_comune_id: Optional[int] = None

        main_layout = QVBoxLayout(self)

        # === Gruppo per i dati del possessore ===
        form_group = QGroupBox("Dati del Nuovo Possessore")
        form_layout = QGridLayout(form_group)

        form_layout.addWidget(QLabel("Nome Completo:"), 0, 0)
        self.nome_completo_edit = QLineEdit()
        form_layout.addWidget(self.nome_completo_edit, 0, 1)

        form_layout.addWidget(QLabel("Paternità:"), 1, 0)
        self.paternita_edit = QLineEdit()
        form_layout.addWidget(self.paternita_edit, 1, 1)
        
        form_layout.addWidget(QLabel("Cognome Nome (opzionale, per ricerca):"), 2, 0)
        self.cognome_nome_edit = QLineEdit() # Se hai questo campo nel DB e lo vuoi inserire
        form_layout.addWidget(self.cognome_nome_edit, 2, 1)

        form_layout.addWidget(QLabel("Comune di Riferimento:"), 3, 0)
        self.comune_combo = QComboBox()
        self._load_comuni_for_combo() # Popola la combobox
        form_layout.addWidget(self.comune_combo, 3, 1)
        
        self.attivo_checkbox = QCheckBox("Attivo")
        self.attivo_checkbox.setChecked(True) # Default a True
        form_layout.addWidget(self.attivo_checkbox, 4, 0, 1, 2) # Span su due colonne

        main_layout.addWidget(form_group)

        # === Tabella per visualizzare i possessori (SE QUESTO WIDGET LA NECESSITA) ===
        # Se InserimentoPossessoreWidget è *solo* un form per creare un nuovo possessore,
        # allora questa tabella potrebbe non essere necessaria qui.
        # Se è necessaria, ad esempio per mostrare una lista di possessori esistenti
        # per evitare duplicati o per selezionarne uno da modificare (anche se il nome del widget
        # suggerisce solo "Inserimento"), allora inizializzala.

        # 1. CREA l'istanza della tabella e assegnala a self.attributo
        ##self.possessori_table = QTableWidget(self) # 'self' come parent

        # 2. DEFINISCI le colonne e le etichette SPECIFICHE per questa tabella
        #    Usa valori letterali o costanti di classe/modulo ben definite.
        #    NON usare 'NUOVE_COLONNE_POSSESSORI' a meno che non sia definita
        #    globalmente o come costante di classe e sia intesa per QUESTO widget.

        # Esempio: se questa tabella mostra una lista di possessori già inseriti
        # per riferimento o per una futura funzionalità di modifica da qui.
        numero_colonne_per_tabella_inserimento = 5 # Ad Esempio: ID, Nome Completo, Paternità, Comune, Attivo
        etichette_per_tabella_inserimento = ["ID", "Nome Completo", "Paternità", "Comune Rif.", "Stato"]
        
        ##self.possessori_table.setColumnCount(numero_colonne_per_tabella_inserimento) # Questa era la riga problematica
        ##self.possessori_table.setHorizontalHeaderLabels(etichette_per_tabella_inserimento)
        
        # Configura la tabella
        ##self.possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        ##self.possessori_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        ##self.possessori_table.setAlternatingRowColors(True)
        ##self.possessori_table.horizontalHeader().setStretchLastSection(True)
        # Potresti voler caricare i dati in questa tabella con un pulsante o all'inizializzazione.
        # self._carica_possessori_esistenti_in_tabella() # Esempio di metodo da chiamare

        # Aggiungi la tabella al layout SOLO SE deve essere visibile in questo widget
        # Se il widget è solo un form, probabilmente non vuoi mostrarla qui.
        # main_layout.addWidget(self.possessori_table) 

        # Pulsante per salvare
        self.save_button = QPushButton("Salva Nuovo Possessore")
        self.save_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_button.clicked.connect(self._salva_possessore) # Connetti a un metodo
        main_layout.addWidget(self.save_button)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _load_comuni_for_combo(self):
        try:
            self.comuni_list_data = self.db_manager.get_comuni()
            self.comune_combo.clear()
            if self.comuni_list_data:
                for comune in self.comuni_list_data:
                    self.comune_combo.addItem(f"{comune['nome']} ({comune['provincia']})", userData=comune['id'])
            else:
                self.comune_combo.addItem("Nessun comune nel DB")
        except Exception as e:
            gui_logger.error(f"Errore caricamento comuni in InserimentoPossessoreWidget: {e}")
            self.comune_combo.addItem("Errore caricamento comuni")

    def _salva_possessore(self):
        nome_completo = self.nome_completo_edit.text().strip()
        paternita = self.paternita_edit.text().strip()
        cognome_nome = self.cognome_nome_edit.text().strip() # Recupera anche questo
        
        idx_comune = self.comune_combo.currentIndex()
        # Assicurati che itemData restituisca un intero o sia convertibile
        comune_id_selezionato_data = self.comune_combo.itemData(idx_comune)
        comune_id_selezionato: Optional[int] = None
        if comune_id_selezionato_data is not None:
            try:
                comune_id_selezionato = int(comune_id_selezionato_data)
            except ValueError:
                gui_logger.error(f"ID comune non valido nella combobox: {comune_id_selezionato_data}")
                QMessageBox.warning(self, "Errore Interno", "ID comune selezionato non valido.")
                return
        
        attivo = self.attivo_checkbox.isChecked()

        # Validazione input lato UI (prima di chiamare il DBManager)
        if not nome_completo:
            QMessageBox.warning(self, "Dati Mancanti", "Il campo 'Nome Completo' è obbligatorio.")
            self.nome_completo_edit.setFocus()
            return
        if comune_id_selezionato is None:
            QMessageBox.warning(self, "Dati Mancanti", "Selezionare un comune di riferimento.")
            self.comune_combo.setFocus()
            return

        try:
            # La chiamata a db_manager.create_possessore ora restituisce l'ID del nuovo possessore
            # o solleva un'eccezione specifica in caso di errore.
            new_possessore_id = self.db_manager.create_possessore(
                nome_completo=nome_completo,
                paternita=paternita if paternita else None, 
                comune_riferimento_id=comune_id_selezionato,
                attivo=attivo,
                cognome_nome=cognome_nome if cognome_nome else None
            )
            
            # Se create_possessore non solleva eccezioni e restituisce un ID, l'operazione è andata a buon fine.
            if new_possessore_id is not None: # Controllo aggiuntivo, anche se dovrebbe sempre esserci un ID o un'eccezione.
                QMessageBox.information(self, "Successo", 
                                        f"Possessore '{nome_completo}' creato con successo. ID: {new_possessore_id}.")
                # Pulisci i campi del form dopo il salvataggio
                self.nome_completo_edit.clear()
                self.paternita_edit.clear()
                self.cognome_nome_edit.clear()
                self.comune_combo.setCurrentIndex(-1) # Resetta la combobox (seleziona nessun item)
                self.attivo_checkbox.setChecked(True) # Riporta al default
                
                # Opzionale: se InserimentoPossessoreWidget avesse una tabella per mostrare i possessori,
                # qui si potrebbe chiamare un metodo per ricaricarla, ad esempio:
                # self._carica_possessori_esistenti_in_tabella() 
            else:
                # Questo blocco potrebbe non essere mai raggiunto se create_possessore
                # solleva sempre un'eccezione in caso di fallimento piuttosto che restituire None.
                # Ma lo teniamo per sicurezza nel caso create_possessore potesse restituire None
                # per qualche fallimento "silenzioso" non gestito da eccezioni.
                gui_logger.error("create_possessore ha restituito None senza sollevare un'eccezione esplicita.")
                QMessageBox.critical(self, "Errore Inserimento", 
                                     "Impossibile creare il possessore. Nessun ID restituito e nessun errore specifico dal database.")

        except DBUniqueConstraintError as uve:
            gui_logger.warning(f"Errore di unicità durante il salvataggio del possessore '{nome_completo}': {uve.message}")
            QMessageBox.critical(self, "Errore di Unicità", 
                                 f"Impossibile creare il possessore:\n{uve.message}")
            # Potresti voler mettere il focus sul campo che ha causato il problema, se noto.
            # Esempio: if "nome_completo" in uve.message.lower(): self.nome_completo_edit.setFocus()

        except DBDataError as dde:
            gui_logger.warning(f"Errore nei dati forniti per il possessore '{nome_completo}': {dde.message}")
            QMessageBox.warning(self, "Dati Non Validi", 
                                f"Impossibile creare il possessore:\n{dde.message}")
            # Potresti voler mettere il focus sul campo problematico.
            # Esempio: if "comune" in dde.message.lower(): self.comune_combo.setFocus()

        except DBMError as dbe: # Altri errori specifici del DBManager ma non di unicità o dati.
            gui_logger.error(f"Errore database gestito durante il salvataggio del possessore '{nome_completo}': {dbe.message}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", 
                                 f"Si è verificato un errore durante la creazione del possessore nel database:\n{dbe.message}")
        
        except Exception as e: # Catch-all per qualsiasi altra eccezione Python imprevista
            gui_logger.critical(f"Errore critico e imprevisto durante il salvataggio del possessore '{nome_completo}': {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto", 
                                 f"Si è verificato un errore di sistema imprevisto durante il salvataggio:\n"
                                 f"{type(e).__name__}: {e}\n"
                                 "Controllare i log dell'applicazione per il traceback completo.")


# --- Scheda per Localita ---
class InserimentoLocalitaWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(InserimentoLocalitaWidget, self).__init__(parent)
        self.db_manager = db_manager
        
        layout = QVBoxLayout()
        
        # Form di inserimento
        form_group = QGroupBox("Inserimento Nuova Località")
        form_layout = QGridLayout()
        
        # Comune
        comune_label = QLabel("Comune:")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_id = None
        self.comune_display = QLabel("Nessun comune selezionato")
        
        form_layout.addWidget(comune_label, 0, 0)
        form_layout.addWidget(self.comune_button, 0, 1)
        form_layout.addWidget(self.comune_display, 0, 2)
        
        # Nome località
        nome_label = QLabel("Nome località:")
        self.nome_edit = QLineEdit()
        
        form_layout.addWidget(nome_label, 1, 0)
        form_layout.addWidget(self.nome_edit, 1, 1, 1, 2)
        
        # Tipo
        tipo_label = QLabel("Tipo:")
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["regione", "via", "borgata"])
        
        form_layout.addWidget(tipo_label, 2, 0)
        form_layout.addWidget(self.tipo_combo, 2, 1)
        
        # Civico
        civico_label = QLabel("Civico (solo per vie):")
        self.civico_edit = QSpinBox()
        self.civico_edit.setMinimum(0)
        self.civico_edit.setMaximum(9999)
        self.civico_edit.setSpecialValueText("Nessun civico")
        
        form_layout.addWidget(civico_label, 3, 0)
        form_layout.addWidget(self.civico_edit, 3, 1)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Pulsante inserimento
        insert_button = QPushButton("Inserisci Località")
        insert_button.clicked.connect(self.insert_localita)
        layout.addWidget(insert_button)
        
        # Riepilogo località del comune selezionato
        summary_group = QGroupBox("Località nel Comune Selezionato")
        summary_layout = QVBoxLayout()
        
        self.refresh_button = QPushButton("Aggiorna Lista")
        self.refresh_button.clicked.connect(self.refresh_localita)
        
        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(4)
        self.localita_table.setHorizontalHeaderLabels(["ID", "Nome", "Tipo", "Civico"])
        self.localita_table.setAlternatingRowColors(True)
        self.localita_table.horizontalHeader().setStretchLastSection(True)
        
        summary_layout.addWidget(self.refresh_button)
        summary_layout.addWidget(self.localita_table)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        self.setLayout(layout)
    
    def select_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)
            self.refresh_localita() # <-- Chiamata per aggiornare la tabella delle località
        # else: # Opzionale: resetta se l'utente annulla
            # self.comune_id = None
            # self.comune_display.setText("Nessun comune selezionato")
            # self.refresh_localita() 
    
    def insert_localita(self):
        """Inserisce una nuova località."""
        # Valida i dati di input
        if not self.comune_id:
            QMessageBox.warning(self, "Errore", "Seleziona un comune.")
            return
        
        nome = self.nome_edit.text().strip()
        tipo = self.tipo_combo.currentText()
        civico = self.civico_edit.value() if self.civico_edit.value() > 0 else None
        
        if not nome:
            QMessageBox.warning(self, "Errore", "Il nome della località è obbligatorio.")
            return
        
        # Inserisci località
        localita_id = self.db_manager.insert_localita(
            self.comune_id, nome, tipo, civico
        )
        
        if localita_id:
            QMessageBox.information(self, "Successo", f"Località '{nome}' inserita con ID: {localita_id}")
            
            # Pulisci i campi
            self.nome_edit.clear()
            self.civico_edit.setValue(0)
            
            # Aggiorna la lista delle località
            self.refresh_localita()
        else:
            QMessageBox.critical(self, "Errore", "Errore durante l'inserimento della località.")
    
    def refresh_localita(self):
        """Aggiorna la lista delle località per il comune selezionato."""
        self.localita_table.setRowCount(0) # Pulisce la tabella
        self.localita_table.setSortingEnabled(False) # Disabilita sorting durante il popolamento

        if self.comune_id: # Assicurati che comune_id sia stato impostato da select_comune
            gui_logger.info(f"DEBUG: InserimentoLocalitaWidget - Chiamata refresh_localita per comune ID: {self.comune_id}")
            try:
                # Chiama il metodo refattorizzato del DBManager
                localita_list = self.db_manager.get_localita_by_comune(self.comune_id) # Non serve filtro qui, vogliamo tutte le località del comune
                
                if localita_list:
                    self.localita_table.setRowCount(len(localita_list))
                    for i, loc in enumerate(localita_list):
                        self.localita_table.setItem(i, 0, QTableWidgetItem(str(loc.get('id', ''))))
                        self.localita_table.setItem(i, 1, QTableWidgetItem(loc.get('nome', '')))
                        self.localita_table.setItem(i, 2, QTableWidgetItem(loc.get('tipo', '')))
                        civico_text = str(loc.get('civico', '')) if loc.get('civico') is not None else "-"
                        self.localita_table.setItem(i, 3, QTableWidgetItem(civico_text))
                    self.localita_table.resizeColumnsToContents()
                else:
                    gui_logger.info(f"Nessuna località trovata per il comune ID: {self.comune_id} in InserimentoLocalitaWidget.")
                    # Potresti voler mostrare un messaggio nella tabella se è vuota
                    # self.localita_table.setItem(0, 0, QTableWidgetItem("Nessuna località per questo comune."))
                    # self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())


            except AttributeError as ae: # Se get_localita_by_comune non dovesse esistere (non dovrebbe succedere ora)
                gui_logger.error(f"Metodo get_localita_by_comune non trovato nel db_manager (chiamato da InserimentoLocalitaWidget): {ae}")
                QMessageBox.critical(self, "Errore Funzionalità", "Funzione per caricare località non implementata correttamente.")
            except Exception as e:
                gui_logger.error(f"Errore durante l'aggiornamento della lista località per comune {self.comune_id}: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Caricamento", f"Impossibile aggiornare la lista delle località: {e}")
        else:
            gui_logger.info("InserimentoLocalitaWidget - refresh_localita: Nessun comune_id selezionato.")
            # La tabella è già stata pulita, quindi apparirà vuota.
        
        self.localita_table.setSortingEnabled(True) # Riabilita sorting

# --- Scheda per statistiche (Vista MV) ---
class StatisticheWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(StatisticheWidget, self).__init__(parent)
        self.db_manager = db_manager
        
        layout = QVBoxLayout()
        
        # Tabs per le diverse statistiche
        tabs = QTabWidget()
        
        # Tab Statistiche per Comune
        stats_comune_tab = QWidget()
        stats_comune_layout = QVBoxLayout()
        
        refresh_stats_button = QPushButton("Aggiorna Statistiche")
        refresh_stats_button.clicked.connect(self.refresh_stats_comune)
        
        self.stats_comune_table = QTableWidget()
        self.stats_comune_table.setColumnCount(7)
        self.stats_comune_table.setHorizontalHeaderLabels([
            "Comune", "Provincia", "Totale Partite", "Partite Attive", 
            "Partite Inattive", "Totale Possessori", "Totale Immobili"
        ])
        self.stats_comune_table.setAlternatingRowColors(True)
        self.stats_comune_table.horizontalHeader().setStretchLastSection(True)
        
        stats_comune_layout.addWidget(refresh_stats_button)
        stats_comune_layout.addWidget(self.stats_comune_table)
        
        stats_comune_tab.setLayout(stats_comune_layout)
        tabs.addTab(stats_comune_tab, "Statistiche per Comune")
        
        # Tab Immobili per Tipologia
        immobili_tab = QWidget()
        immobili_layout = QVBoxLayout()
        
        self.comune_filter_button = QPushButton("Filtra per Comune...")
        self.comune_filter_button.clicked.connect(self.filter_immobili_per_comune)
        self.comune_filter_id = None
        self.comune_filter_display = QLabel("Visualizzando tutti i comuni")
        
        self.clear_filter_button = QPushButton("Rimuovi Filtro")
        self.clear_filter_button.clicked.connect(self.clear_immobili_filter)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.comune_filter_button)
        filter_layout.addWidget(self.comune_filter_display)
        filter_layout.addWidget(self.clear_filter_button)
        
        self.refresh_immobili_button = QPushButton("Aggiorna Dati")
        self.refresh_immobili_button.clicked.connect(self.refresh_immobili_tipologia)
        
        self.immobili_table = QTableWidget()
        self.immobili_table.setColumnCount(6)
        self.immobili_table.setHorizontalHeaderLabels([
            "Comune", "Classificazione", "Numero Immobili", 
            "Totale Piani", "Totale Vani", "Media Vani/Immobile"
        ])
        self.immobili_table.setAlternatingRowColors(True)
        self.immobili_table.horizontalHeader().setStretchLastSection(True)
        
        immobili_layout.addLayout(filter_layout)
        immobili_layout.addWidget(self.refresh_immobili_button)
        immobili_layout.addWidget(self.immobili_table)
        
        immobili_tab.setLayout(immobili_layout)
        tabs.addTab(immobili_tab, "Immobili per Tipologia")
        
        # Tab Manutenzione Viste
        manutenzione_tab = QWidget()
        manutenzione_layout = QVBoxLayout()
        
        self.update_views_button = QPushButton("Aggiorna Tutte le Viste Materializzate")
        self.update_views_button.clicked.connect(self.update_all_views)
        
        self.maintenance_button = QPushButton("Esegui Manutenzione Database (ANALYZE)")
        self.maintenance_button.clicked.connect(self.run_maintenance)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        
        manutenzione_layout.addWidget(self.update_views_button)
        manutenzione_layout.addWidget(self.maintenance_button)
        manutenzione_layout.addWidget(QLabel("Log Operazioni:"))
        manutenzione_layout.addWidget(self.status_text)
        
        manutenzione_tab.setLayout(manutenzione_layout)
        tabs.addTab(manutenzione_tab, "Manutenzione Viste")
        
        layout.addWidget(tabs)
        self.setLayout(layout)
        
        # Carica dati iniziali
        self.refresh_stats_comune()
        self.refresh_immobili_tipologia()
    
    def refresh_stats_comune(self):
        """Aggiorna la tabella delle statistiche per comune."""
        self.stats_comune_table.setRowCount(0)
        
        stats = self.db_manager.get_statistiche_comune()
        
        if stats:
            self.stats_comune_table.setRowCount(len(stats))
            
            for i, s in enumerate(stats):
                self.stats_comune_table.setItem(i, 0, QTableWidgetItem(s.get('comune', '')))
                self.stats_comune_table.setItem(i, 1, QTableWidgetItem(s.get('provincia', '')))
                self.stats_comune_table.setItem(i, 2, QTableWidgetItem(str(s.get('totale_partite', 0))))
                self.stats_comune_table.setItem(i, 3, QTableWidgetItem(str(s.get('partite_attive', 0))))
                self.stats_comune_table.setItem(i, 4, QTableWidgetItem(str(s.get('partite_inattive', 0))))
                self.stats_comune_table.setItem(i, 5, QTableWidgetItem(str(s.get('totale_possessori', 0))))
                self.stats_comune_table.setItem(i, 6, QTableWidgetItem(str(s.get('totale_immobili', 0))))
            
            self.stats_comune_table.resizeColumnsToContents()
            
            self.log_status("Statistiche comuni aggiornate.")
    
    def filter_immobili_per_comune(self):
        """Filtra le statistiche immobili per comune."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_filter_id = dialog.selected_comune_id
            self.comune_filter_display.setText(f"Comune: {dialog.selected_comune_name}")
            self.refresh_immobili_tipologia()
    
    def clear_immobili_filter(self):
        """Rimuove il filtro per comune dalle statistiche immobili."""
        self.comune_filter_id = None
        self.comune_filter_display.setText("Visualizzando tutti i comuni")
        self.refresh_immobili_tipologia()
    
    def refresh_immobili_tipologia(self):
        """Aggiorna la tabella degli immobili per tipologia."""
        self.immobili_table.setRowCount(0)
        
        stats = self.db_manager.get_immobili_per_tipologia(self.comune_filter_id)
        
        if stats:
            self.immobili_table.setRowCount(len(stats))
            
            for i, s in enumerate(stats):
                self.immobili_table.setItem(i, 0, QTableWidgetItem(s.get('comune_nome', '')))
                self.immobili_table.setItem(i, 1, QTableWidgetItem(s.get('classificazione', 'N/D')))
                
                num_immobili = s.get('numero_immobili', 0)
                self.immobili_table.setItem(i, 2, QTableWidgetItem(str(num_immobili)))
                
                self.immobili_table.setItem(i, 3, QTableWidgetItem(str(s.get('totale_piani', 0))))
                
                totale_vani = s.get('totale_vani', 0)
                self.immobili_table.setItem(i, 4, QTableWidgetItem(str(totale_vani)))
                
                # Calcola media vani/immobile
                media_vani = round(totale_vani / num_immobili, 2) if num_immobili > 0 else 0
                self.immobili_table.setItem(i, 5, QTableWidgetItem(str(media_vani)))
            
            self.immobili_table.resizeColumnsToContents()
            
            status_text = "Dati immobili aggiornati"
            if self.comune_filter_id:
                comune_nome = self.comune_filter_display.text().replace("Comune: ", "")
                status_text += f" (filtrati per {comune_nome})"
            status_text += "."
            
            self.log_status(status_text)
    
    def update_all_views(self):
        """Aggiorna tutte le viste materializzate."""
        self.log_status("Avvio aggiornamento di tutte le viste materializzate...")
        
        if self.db_manager.refresh_materialized_views():
            self.log_status("Aggiornamento viste completato con successo.")
            
            # Aggiorna le tabelle
            self.refresh_stats_comune()
            self.refresh_immobili_tipologia()
        else:
            self.log_status("ERRORE: Aggiornamento viste non riuscito. Controlla i log.")
    
    def run_maintenance(self):
        """Esegue la manutenzione generale del database."""
        self.log_status("Avvio manutenzione database (ANALYZE)...")
        
        if self.db_manager.run_database_maintenance():
            self.log_status("Manutenzione database completata con successo.")
        else:
            self.log_status("ERRORE: Manutenzione database non riuscita. Controlla i log.")
    
    def log_status(self, message):
        """Aggiunge un messaggio al log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")




# --- Scheda per Registrazione Nuova Proprietà ---
class RegistrazioneProprietaWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(RegistrazioneProprietaWidget, self).__init__(parent)
        self.db_manager = db_manager
        
        layout = QVBoxLayout()
        
        # Form di inserimento
        form_group = QGroupBox("Registrazione Nuova Proprietà")
        form_layout = QGridLayout()
        
        # Comune
        comune_label = QLabel("Comune:")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_id = None
        self.comune_display = QLabel("Nessun comune selezionato")
        
        form_layout.addWidget(comune_label, 0, 0)
        form_layout.addWidget(self.comune_button, 0, 1)
        form_layout.addWidget(self.comune_display, 0, 2)
        
        # Numero partita
        num_partita_label = QLabel("Numero Partita:")
        self.num_partita_edit = QSpinBox()
        self.num_partita_edit.setMinimum(1)
        self.num_partita_edit.setMaximum(9999)
        
        form_layout.addWidget(num_partita_label, 1, 0)
        form_layout.addWidget(self.num_partita_edit, 1, 1)
        
        # Data impianto
        data_label = QLabel("Data Impianto:")
        self.data_edit = QDateEdit()
        self.data_edit.setCalendarPopup(True)
        self.data_edit.setDate(QDate.currentDate())
        
        form_layout.addWidget(data_label, 2, 0)
        form_layout.addWidget(self.data_edit, 2, 1)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Possessori
        possessori_group = QGroupBox("Possessori")
        possessori_layout = QVBoxLayout()
        
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(4)
        self.possessori_table.setHorizontalHeaderLabels(["Nome Completo", "Cognome e Nome", "Paternità", "Quota"])
        self.possessori_table.horizontalHeader().setStretchLastSection(True)
        
        self.add_possessore_button = QPushButton("Aggiungi Possessore")
        self.add_possessore_button.clicked.connect(self.add_possessore)
        self.remove_possessore_button = QPushButton("Rimuovi Possessore Selezionato")
        self.remove_possessore_button.clicked.connect(self.remove_possessore)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_possessore_button)
        button_layout.addWidget(self.remove_possessore_button)
        
        possessori_layout.addWidget(self.possessori_table)
        possessori_layout.addLayout(button_layout)
        
        possessori_group.setLayout(possessori_layout)
        layout.addWidget(possessori_group)
        
        # Immobili
        immobili_group = QGroupBox("Immobili")
        immobili_layout = QVBoxLayout()
        
        self.immobili_table = QTableWidget()
        self.immobili_table.setColumnCount(5)
        self.immobili_table.setHorizontalHeaderLabels(["Natura", "Località", "Classificazione", "Consistenza", "Piani/Vani"])
        self.immobili_table.horizontalHeader().setStretchLastSection(True)
        
        self.add_immobile_button = QPushButton("Aggiungi Immobile")
        self.add_immobile_button.clicked.connect(self.add_immobile)
        self.remove_immobile_button = QPushButton("Rimuovi Immobile Selezionato")
        self.remove_immobile_button.clicked.connect(self.remove_immobile)
        
        button_immobili_layout = QHBoxLayout()
        button_immobili_layout.addWidget(self.add_immobile_button)
        button_immobili_layout.addWidget(self.remove_immobile_button)
        
        immobili_layout.addWidget(self.immobili_table)
        immobili_layout.addLayout(button_immobili_layout)
        
        immobili_group.setLayout(immobili_layout)
        layout.addWidget(immobili_group)
        
        # Pulsante registrazione
        self.register_button = QPushButton("Registra Nuova Proprietà")
        self.register_button.clicked.connect(self.register_property)
        layout.addWidget(self.register_button)
        
        self.setLayout(layout)
        
        # Array per memorizzare i dati
        self.possessori_data = []
        self.immobili_data = []
    
    def select_comune(self):
        """Apre il selettore di comuni."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)
    
    def add_possessore(self):
        """Aggiunge un possessore alla lista."""
        dialog = PossessoreSelectionDialog(self.db_manager, self.comune_id, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_possessore:
            self.possessori_data.append(dialog.selected_possessore)
            self.update_possessori_table()
    
    def remove_possessore(self):
        """Rimuove il possessore selezionato dalla lista."""
        selected_rows = self.possessori_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione", "Seleziona un possessore da rimuovere.")
            return
        
        row = selected_rows[0].row()
        if 0 <= row < len(self.possessori_data):
            del self.possessori_data[row]
            self.update_possessori_table()
    
    def update_possessori_table(self):
        """Aggiorna la tabella dei possessori."""
        if not hasattr(self, 'possessori_data') or self.possessori_data is None:
            self.possessori_data = [] # Assicura che sia una lista se non definito

        self.possessori_table.setRowCount(len(self.possessori_data))
        
        # Assicurati che NUOVE_ETICHETTE_POSSESSORI sia definito globalmente,
        # come attributo di classe/istanza, o passato al metodo se necessario.
        # Esempio: NUOVE_ETICHETTE_POSSESSORI = ["cognome_nome", "paternita_dettaglio", ...]
        # Se non è definito, il controllo 'in NUOVE_ETICHETTE_POSSESSORI' causerà un NameError.
        # Per ora, assumiamo che sia definito da qualche parte accessibile.
        # Se non lo è, dovrà definirlo o rimuovere il blocco condizionale se le colonne sono fisse.

        for i, dati_possessore in enumerate(self.possessori_data): # Usa 'i' e 'dati_possessore'
            current_col = 0 # Inizializza l'indice di colonna per ogni riga

            # Colonna 0: Nome Completo (come da sua logica originale)
            self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('nome_completo', ''))))
            current_col += 1

            # Colonna 1: Cognome e Nome (come da sua logica originale)
            # Questa potrebbe essere la stessa del blocco "NUOVE COLONNE" o una versione diversa.
            # Se 'cognome_nome' in NUOVE_ETICHETTE_POSSESSORI è per una visualizzazione speciale, gestiscila qui.
            if 'cognome_nome' in NUOVE_ETICHETTE_POSSESSORI: # Assumendo NUOVE_ETICHETTE_POSSESSORI sia definito
                # Usa il valore da dati_possessore.get('cognome_nome', 'N/D')
                # Questa era la colonna che causava l'errore usando 'row_idx' e 'col' non definite.
                self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('cognome_nome', 'N/D'))))
            else:
                # Fallback o gestione se 'cognome_nome' non è in NUOVE_ETICHETTE_POSSESSORI ma è una colonna fissa
                self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('cognome_nome', ''))))
            current_col += 1

            # Colonna 2: Paternità
            # Il blocco "NUOVE COLONNE" aveva anche una 'paternita'. Chiarire quale usare.
            # Se il blocco if precedente gestiva una 'paternita' condizionale:
            # if 'paternita_speciale' in NUOVE_ETICHETTE_POSSESSORI:
            #     self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('paternita_speciale', 'N/D'))))
            # else:
            #     self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('paternita', ''))))
            # current_col += 1
            # Oppure, se è sempre la stessa 'paternita':
            self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('paternita', ''))))
            current_col += 1
            
            # Colonna 3: Quota
            self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('quota', ''))))
            current_col += 1
            
            # Aggiungere altre colonne se necessario, seguendo il pattern:
            # self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('nome_campo', ''))))
            # current_col += 1

        self.possessori_table.resizeColumnsToContents()
    
    def add_immobile(self):
        """Aggiunge un immobile alla lista."""
        dialog = ImmobileDialog(self.db_manager, self.comune_id, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.immobile_data:
            self.immobili_data.append(dialog.immobile_data)
            self.update_immobili_table()
    
    def remove_immobile(self):
        """Rimuove l'immobile selezionato dalla lista."""
        selected_rows = self.immobili_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione", "Seleziona un immobile da rimuovere.")
            return
        
        row = selected_rows[0].row()
        if 0 <= row < len(self.immobili_data):
            del self.immobili_data[row]
            self.update_immobili_table()
    
    def update_immobili_table(self):
        """Aggiorna la tabella degli immobili."""
        self.immobili_table.setRowCount(len(self.immobili_data))
        
        for i, immobile in enumerate(self.immobili_data):
            self.immobili_table.setItem(i, 0, QTableWidgetItem(immobile.get('natura', '')))
            self.immobili_table.setItem(i, 1, QTableWidgetItem(immobile.get('localita_nome', '')))
            self.immobili_table.setItem(i, 2, QTableWidgetItem(immobile.get('classificazione', '')))
            self.immobili_table.setItem(i, 3, QTableWidgetItem(immobile.get('consistenza', '')))
            
            piani_vani = ""
            if 'numero_piani' in immobile and immobile['numero_piani']:
                piani_vani += f"Piani: {immobile['numero_piani']}"
            if 'numero_vani' in immobile and immobile['numero_vani']:
                if piani_vani:
                    piani_vani += ", "
                piani_vani += f"Vani: {immobile['numero_vani']}"
            
            self.immobili_table.setItem(i, 4, QTableWidgetItem(piani_vani))
    
    # All'interno della classe RegistrazioneProprietaWidget in prova.py

    def register_property(self):
        """Registra la nuova proprietà nel database."""
        # Validazione input (come da suo codice esistente)
        if not self.comune_id:
            QMessageBox.warning(self, "Errore", "Seleziona un comune.")
            return
        if not self.possessori_data: # Assicurati che self.possessori_data sia una lista di dizionari corretta
            QMessageBox.warning(self, "Errore", "Aggiungi almeno un possessore.")
            return
        if not self.immobili_data: # Assicurati che self.immobili_data sia una lista di dizionari corretta
            QMessageBox.warning(self, "Errore", "Aggiungi almeno un immobile.")
            return
        
        numero_partita = self.num_partita_edit.value()
        data_impianto = self.data_edit.date().toPyDate()
        
        try:
            # Il metodo db_manager.registra_nuova_proprieta ora restituisce True
            # o solleva un'eccezione specifica (DBUniqueConstraintError, DBDataError, DBMError).
            success = self.db_manager.registra_nuova_proprieta(
                self.comune_id,
                numero_partita,
                data_impianto,
                self.possessori_data, 
                self.immobili_data
            )
            
            if success: # Se non ci sono state eccezioni e il metodo db_manager ha restituito True
                QMessageBox.information(self, "Successo", "Nuova proprietà registrata con successo.")
                # Pulisce i campi dell'interfaccia
                self.comune_id = None
                self.comune_display.setText("Nessun comune selezionato")
                self.num_partita_edit.setValue(1) # O il suo valore di default
                self.data_edit.setDate(QDate.currentDate())
                self.possessori_data = [] # Resetta le liste interne
                self.immobili_data = []
                self.update_possessori_table() # Aggiorna le tabelle nella UI
                self.update_immobili_table()
            # else: Questo blocco non è più necessario se il fallimento è segnalato solo da eccezioni.
            # QMessageBox.critical(self, "Errore", "Registrazione della proprietà fallita (DB manager ha restituito False).")

        # Gestione delle eccezioni specifiche che registra_nuova_proprieta potrebbe sollevare
        except DBUniqueConstraintError as uve:
            gui_logger.error(f"Errore di unicità registrando la proprietà: {uve.message}", exc_info=True)
            QMessageBox.critical(self, "Errore di Unicità", 
                                 f"Impossibile registrare la proprietà:\n{uve.message}\n"
                                 "Una partita con lo stesso numero potrebbe già esistere per questo comune, o altri dati sono duplicati.")
        except DBDataError as dde: # Per errori nei dati JSON o altri dati non validi passati alla procedura
            gui_logger.error(f"Errore nei dati forniti per la registrazione della proprietà: {dde.message}", exc_info=True)
            QMessageBox.warning(self, "Dati Non Validi", 
                                f"Impossibile registrare la proprietà:\n{dde.message}")
        except DBMError as dbe: # Per altri errori generici provenienti dal DBManager o dal database
            gui_logger.error(f"Errore database durante la registrazione della proprietà: {dbe.message}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", 
                                 f"Si è verificato un errore durante la registrazione nel database:\n{dbe.message}")
        except Exception as e: # Catch-all per altri errori Python imprevisti
            gui_logger.critical(f"Errore critico e imprevisto durante la registrazione della proprietà: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto", 
                                 f"Si è verificato un errore di sistema imprevisto durante la registrazione:\n"
                                 f"{type(e).__name__}: {e}\n"
                                 "Controllare i log dell'applicazione per il traceback completo.")

# --- Dialog per la Selezione dei Possessori ---
class PossessoreSelectionDialog(QDialog):
    def __init__(self, db_manager, comune_id, parent=None):
        super(PossessoreSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.selected_possessore = None
        
        self.setWindowTitle("Seleziona Possessore")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Tab per selezione o creazione
        tabs = QTabWidget()
        
        # Tab Seleziona
        select_tab = QWidget()
        select_layout = QVBoxLayout()
        
        # Filtro
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filtra per nome:")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare...")
        self.filter_edit.textChanged.connect(self.filter_possessori)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)
        
        select_layout.addLayout(filter_layout)
        
        # Tabella possessori
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(4)
        self.possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Paternità", "Stato"])
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.setSelectionMode(QTableWidget.SingleSelection)
        self.possessori_table.itemDoubleClicked.connect(self.select_from_table)
        
        select_layout.addWidget(self.possessori_table)
        
        select_tab.setLayout(select_layout)
        tabs.addTab(select_tab, "Seleziona Esistente")
        
        # Tab Crea
        create_tab = QWidget()
        create_layout = QGridLayout()
        
        # Cognome e nome
        cognome_label = QLabel("Cognome e nome:")
        self.cognome_edit = QLineEdit()
        
        create_layout.addWidget(cognome_label, 0, 0)
        create_layout.addWidget(self.cognome_edit, 0, 1)
        
        # Paternità
        paternita_label = QLabel("Paternità:")
        self.paternita_edit = QLineEdit()
        
        create_layout.addWidget(paternita_label, 1, 0)
        create_layout.addWidget(self.paternita_edit, 1, 1)
        
        # Nome completo
        nome_completo_label = QLabel("Nome completo:")
        self.nome_completo_edit = QLineEdit()
        self.nome_completo_update_button = QPushButton("Genera da cognome+paternità")
        self.nome_completo_update_button.clicked.connect(self.update_nome_completo)
        
        create_layout.addWidget(nome_completo_label, 2, 0)
        create_layout.addWidget(self.nome_completo_edit, 2, 1)
        create_layout.addWidget(self.nome_completo_update_button, 2, 2)
        
        # Quota
        quota_label = QLabel("Quota (vuoto per esclusiva):")
        self.quota_edit = QLineEdit()
        self.quota_edit.setPlaceholderText("Es. 1/2, 1/3, ecc.")
        
        create_layout.addWidget(quota_label, 3, 0)
        create_layout.addWidget(self.quota_edit, 3, 1)
        
        create_tab.setLayout(create_layout)
        tabs.addTab(create_tab, "Crea Nuovo")
        
        layout.addWidget(tabs)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Seleziona")
        self.ok_button.clicked.connect(self.handle_selection)
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # Carica i possessori iniziali
        self.current_tab = 0
        tabs.currentChanged.connect(self.tab_changed)
        self.load_possessori()
    
    def tab_changed(self, index):
        """Gestisce il cambio di tab."""
        self.current_tab = index
        if index == 0:
            self.ok_button.setText("Seleziona")
        else:
            self.ok_button.setText("Crea e Seleziona")
    
    def load_possessori(self, filter_text: Optional[str] = None):
        self.possessori_table.setRowCount(0) # Pulisce la tabella
        self.possessori_table.setSortingEnabled(False)
        
        possessori_list: List[Dict[str, Any]] = [] # Inizializza a lista vuota

        try:
            # Il filter_text viene passato dalla chiamata in filter_possessori, 
            # che a sua volta lo prende da self.filter_edit.text().strip()
            actual_filter_text = filter_text if filter_text and filter_text.strip() else None

            if self.comune_id is not None:
                # Scenario 1: Comune specificato, filtra per comune e poi per testo
                gui_logger.debug(f"PossessoreSelectionDialog: Caricamento per comune_id={self.comune_id}, filtro='{actual_filter_text}'")
                gui_logger.debug(f"load_possessori: self.comune_id={self.comune_id}, actual_filter_text='{actual_filter_text}'")
                temp_list = self.db_manager.get_possessori_by_comune(self.comune_id)
                if actual_filter_text:
                    ft_lower = actual_filter_text.lower()
                    possessori_list = [
                        p for p in temp_list 
                        if ft_lower in p.get('nome_completo', '').lower() or \
                           (p.get('cognome_nome') and ft_lower in p.get('cognome_nome', '').lower()) # Controlla se cognome_nome esiste
                    ]
                else:
                    possessori_list = temp_list
            elif actual_filter_text:
                # Scenario 2: Nessun comune specificato, ma c'è un testo di filtro -> ricerca globale
                gui_logger.debug(f"PossessoreSelectionDialog: Caricamento globale con filtro='{actual_filter_text}'")
                # Necessita di un metodo nel DBManager per cercare possessori globalmente per nome/cf/ecc.
                # Creeremo search_possessori_globally più avanti.
                # Per ora, potremmo usare ricerca_avanzata_possessori se è adatto.
                # ATTENZIONE: ricerca_avanzata_possessori restituisce campi extra (similarity, num_partite)
                # che questa tabella non si aspetta. È meglio un metodo dedicato.
                # Chiamiamo un nuovo metodo (da creare in DBManager):
                gui_logger.debug("load_possessori: Ramo - ricerca globale per testo.")
                possessori_list = self.db_manager.search_possessori_by_term_globally(actual_filter_text)
                gui_logger.info(f"load_possessori: Risultato da search_possessori_by_term_globally: {possessori_list}") # LOG IMPORTANTE
            else:
                # Scenario 3: Nessun comune e nessun testo di filtro.
                # Non carichiamo nulla per evitare di mostrare tutti i possessori del database.
                # L'utente deve inserire un termine di ricerca se non c'è un contesto di comune.
                gui_logger.debug("PossessoreSelectionDialog: Nessun comune_id e nessun testo di filtro. Tabella non popolata.")
                gui_logger.debug("load_possessori: Ramo - nessun comune, nessun filtro.")
                # La tabella rimane vuota, o potresti aggiungere un item "Inserisci un termine per cercare".

            # Popolamento della tabella (assicurati che i nomi delle chiavi siano corretti)
            if possessori_list: # Se la lista contiene risultati
                gui_logger.info(f">>> Popolando possessori_table con {len(possessori_list)} righe.") # LOG AGGIUNTO
                self.possessori_table.setRowCount(len(possessori_list))
                for i, pos_data in enumerate(possessori_list):
                    col = 0
                    item_id_str = str(pos_data.get('id', 'N/D'))
                    item_nome_str = pos_data.get('nome_completo', 'N/D')
                    item_pater_str = pos_data.get('paternita', 'N/D')
                    item_stato_str = "Attivo" if pos_data.get('attivo', False) else "Non Attivo"
                    
                    # LOG AGGIUNTO PER OGNI RIGA
                    gui_logger.debug(f"    Riga {i}: ID='{item_id_str}', Nome='{item_nome_str}', Pater='{item_pater_str}', Stato='{item_stato_str}'")

                    self.possessori_table.setItem(i, col, QTableWidgetItem(item_id_str)); col+=1
                    self.possessori_table.setItem(i, col, QTableWidgetItem(item_nome_str)); col+=1
                    self.possessori_table.setItem(i, col, QTableWidgetItem(item_pater_str)); col+=1
                    self.possessori_table.setItem(i, col, QTableWidgetItem(item_stato_str)); col+=1
                
                self.possessori_table.resizeColumnsToContents()
                gui_logger.info(">>> Popolamento possessori_table completato.") # LOG AGGIUNTO
            elif actual_filter_text or self.comune_id: # Mostra "Nessun risultato" solo se è stata tentata una ricerca attiva
                self.possessori_table.setRowCount(1)
                self.possessori_table.setItem(0, 0, QTableWidgetItem("Nessun possessore trovato con i criteri specificati."))
                self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())
            # else: se nessun filtro e nessun comune, la tabella è intenzionalmente vuota.

        except Exception as e:
            gui_logger.error(f"Errore durante il caricamento dei possessori in PossessoreSelectionDialog: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare i possessori: {e}")
            # Mostra errore anche nella tabella
            self.possessori_table.setRowCount(1)
            self.possessori_table.setItem(0,0, QTableWidgetItem(f"Errore caricamento: {e}"))
            self.possessori_table.setSpan(0,0,1, self.possessori_table.columnCount())
        finally:
            self.possessori_table.setSortingEnabled(True)

    # Il metodo filter_possessori dovrebbe rimanere com'è, chiamando load_possessori con il testo.
    def filter_possessori(self): # Questo metodo è collegato a self.filter_edit.textChanged
        filter_text = self.filter_edit.text().strip()
        gui_logger.info(f">>> PossessoreSelectionDialog.filter_possessori: Testo filtro='{filter_text}'")
    
        # Chiama load_possessori; il testo del filtro verrà usato se comune_id è None
        self.load_possessori(filter_text if filter_text else None)

    
    
    def update_nome_completo(self):
        """Aggiorna il nome completo in base a cognome e paternità."""
        cognome = self.cognome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()
        
        if cognome:
            nome_completo = cognome
            if paternita:
                nome_completo += f" {paternita}"
            
            self.nome_completo_edit.setText(nome_completo)
    
    def select_from_table(self, item):
        """Gestisce la selezione dalla tabella dei possessori."""
        row = item.row()
        self.handle_selection()
    
    def handle_selection(self):
        """Gestisce la selezione o creazione del possessore."""
        if self.current_tab == 0:  # Tab "Seleziona Esistente"
            selected_rows = self.possessori_table.selectedIndexes()
            if not selected_rows:
                QMessageBox.warning(self, "Attenzione", "Seleziona un possessore dalla tabella.")
                return
            
            row = selected_rows[0].row()
            possessore_id_text = self.possessori_table.item(row, 0).text()
            nome_completo_text = self.possessori_table.item(row, 1).text()
            # Recupera anche gli altri dati se servono per self.selected_possessore
            cognome_nome_text = self.possessori_table.item(row, 2).text() if self.possessori_table.columnCount() > 2 and self.possessori_table.item(row, 2) else None
            paternita_text = self.possessori_table.item(row, 3).text() if self.possessori_table.columnCount() > 3 and self.possessori_table.item(row, 3) else None
            # ... e così via per altri campi se la tabella li mostra e servono ...

            if possessore_id_text.isdigit():
                self.selected_possessore = {
                    'id': int(possessore_id_text),
                    'nome_completo': nome_completo_text,
                    'cognome_nome': cognome_nome_text, # Aggiunto
                    'paternita': paternita_text,       # Aggiunto
                    # 'comune_riferimento_id': self.comune_id, # Il comune_id del dialogo, se pertinente
                    # 'attivo': True # O leggi dalla tabella se presente
                    # Aggiungi qui altri campi che vuoi passare indietro dal possessore selezionato
                }
                # Non chiediamo più la quota qui, verrà chiesta separatamente se necessario
                # dal widget chiamante (es. DettagliLegamePossessoreDialog)
                self.accept()
            else:
                QMessageBox.warning(self, "Errore Selezione", "ID possessore non valido nella tabella.")
        
        elif self.current_tab == 1:  # Tab "Crea Nuovo"
            nome_completo = self.nome_completo_edit.text().strip()
            paternita = self.paternita_edit.text().strip()
            # Assumiamo che tu abbia anche un campo per cognome_nome nel tab "Crea Nuovo"
            # Se non c'è, devi aggiungerlo o gestirlo diversamente
            cognome_nome = self.cognome_nome_edit.text().strip() if hasattr(self, 'cognome_nome_edit') else None

            # Validazione campi per nuovo possessore
            if not nome_completo:
                QMessageBox.warning(self, "Dati Mancanti", "Il 'Nome Completo' è obbligatorio per un nuovo possessore.")
                self.nome_completo_edit.setFocus(); return
            if not cognome_nome: # Se cognome_nome è NOT NULL nella tabella possessore
                QMessageBox.warning(self, "Dati Mancanti", "Il 'Cognome Nome' è obbligatorio per un nuovo possessore.")
                if hasattr(self, 'cognome_nome_edit'): self.cognome_nome_edit.setFocus();
                return
            if self.comune_id is None: # comune_id è quello del dialogo, che deve essere il comune di riferimento
                QMessageBox.warning(self, "Contesto Mancante", "Comune di riferimento non specificato per creare un nuovo possessore.")
                return

            try:
                # --- CORREZIONE QUI ---
                # possessore_id = self.db_manager.create_possessore() # Vecchia chiamata, con erroressore( # VECCHIA CHIAMATA
                new_possessore_id = self.db_manager.create_possessore( # NUOVA CHIAMATA
                    nome_completo=nome_completo,
                    paternita=paternita if paternita else None,
                    comune_riferimento_id=self.comune_id, # Usa il comune_id del contesto del dialogo
                    attivo=True, # Default per un nuovo possessore
                    cognome_nome=cognome_nome # Passa il cognome_nome
                )
                # --- FINE CORREZIONE ---
            
                if new_possessore_id is not None:
                    self.selected_possessore = {
                        'id': new_possessore_id,
                        'nome_completo': nome_completo,
                        'cognome_nome': cognome_nome,
                        'paternita': paternita,
                        'comune_riferimento_id': self.comune_id,
                        'attivo': True
                        # Non c'è 'quota' qui, perché è legata al legame partita-possessore, non al possessore stesso
                    }
                    QMessageBox.information(self, "Successo", f"Nuovo possessore '{nome_completo}' creato con ID: {new_possessore_id}.")
                    self.accept() # Chiude e segnala successo
                # else: create_possessore solleva eccezioni in caso di fallimento
            
            except (DBUniqueConstraintError, DBDataError, DBMError) as e:
                QMessageBox.critical(self, "Errore Creazione Possessore", str(e))
            except Exception as e_gen:
                gui_logger.critical(f"Errore imprevisto creazione possessore: {e_gen}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {type(e_gen).__name__}: {e_gen}")
        else: # Altro tab? (non dovrebbe esserci)
             QMessageBox.warning(self, "Azione Non Valida", "Azione non riconosciuta per il tab corrente.")

     # --- Dialog per l'Inserimento degli Immobili ---
class ImmobileDialog(QDialog):
    def __init__(self, db_manager, comune_id, parent=None):
        super(ImmobileDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.immobile_data = None
        
        self.setWindowTitle("Inserisci Immobile")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        form_layout = QGridLayout()
        
        # Natura
        natura_label = QLabel("Natura:")
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Es. Casa, Terreno, Garage, ecc.")
        
        form_layout.addWidget(natura_label, 0, 0)
        form_layout.addWidget(self.natura_edit, 0, 1)
        
        # Località
        localita_label = QLabel("Località:")
        self.localita_button = QPushButton("Seleziona Località...")
        self.localita_button.clicked.connect(self.select_localita)
        self.localita_id = None
        self.localita_display = QLabel("Nessuna località selezionata")
        
        form_layout.addWidget(localita_label, 1, 0)
        form_layout.addWidget(self.localita_button, 1, 1)
        form_layout.addWidget(self.localita_display, 1, 2)
        
        # Classificazione
        classificazione_label = QLabel("Classificazione:")
        self.classificazione_edit = QLineEdit()
        self.classificazione_edit.setPlaceholderText("Es. Abitazione civile, Deposito, ecc.")
        
        form_layout.addWidget(classificazione_label, 2, 0)
        form_layout.addWidget(self.classificazione_edit, 2, 1)
        
        # Consistenza
        consistenza_label = QLabel("Consistenza:")
        self.consistenza_edit = QLineEdit()
        self.consistenza_edit.setPlaceholderText("Es. 120 mq")
        
        form_layout.addWidget(consistenza_label, 3, 0)
        form_layout.addWidget(self.consistenza_edit, 3, 1)
        
        # Numero piani
        piani_label = QLabel("Numero piani:")
        self.piani_edit = QSpinBox()
        self.piani_edit.setMinimum(0)
        self.piani_edit.setMaximum(99)
        self.piani_edit.setSpecialValueText("Non specificato")
        
        form_layout.addWidget(piani_label, 4, 0)
        form_layout.addWidget(self.piani_edit, 4, 1)
        
        # Numero vani
        vani_label = QLabel("Numero vani:")
        self.vani_edit = QSpinBox()
        self.vani_edit.setMinimum(0)
        self.vani_edit.setMaximum(99)
        self.vani_edit.setSpecialValueText("Non specificato")
        
        form_layout.addWidget(vani_label, 5, 0)
        form_layout.addWidget(self.vani_edit, 5, 1)
        
        layout.addLayout(form_layout)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Inserisci")
        self.ok_button.clicked.connect(self.handle_insert)
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def select_localita(self):
        """Apre un dialogo per selezionare la località."""
        if self.comune_id is None: # Aggiunto controllo per sicurezza
            QMessageBox.warning(self, "Comune Mancante", 
                                "Selezionare un comune per la partita prima di scegliere una località per l'immobile.")
            return

        # Istanzia LocalitaSelectionDialog in MODALITÀ SELEZIONE
        dialog = LocalitaSelectionDialog(self.db_manager, 
                                         self.comune_id, 
                                         self,  # parent
                                         selection_mode=True) # <<<--- MODIFICA CHIAVE QUI
        
        result = dialog.exec_()
        
        if result == QDialog.Accepted: # L'utente ha premuto "Seleziona" in LocalitaSelectionDialog
            if dialog.selected_localita_id is not None and dialog.selected_localita_name is not None:
                self.localita_id = dialog.selected_localita_id
                self.localita_display.setText(dialog.selected_localita_name)
                gui_logger.info(f"ImmobileDialog: Località selezionata ID: {self.localita_id}, Nome: '{self.localita_display.text()}'")
            else:
                # Questo caso dovrebbe essere raro se _conferma_selezione in LocalitaSelectionDialog funziona correttamente
                gui_logger.warning("ImmobileDialog: LocalitaSelectionDialog accettato ma ID/nome località non validi.")
        # else: L'utente ha premuto "Annulla" o chiuso il dialogo LocalitaSelectionDialog,
        # quindi non aggiorniamo nulla e la selezione precedente (o nessuna selezione) rimane.

    
    def handle_insert(self):
        """Gestisce l'inserimento dell'immobile."""
        # Validazione input
        natura = self.natura_edit.text().strip()
        if not natura:
            QMessageBox.warning(self, "Errore", "La natura dell'immobile è obbligatoria.")
            return
        
        if not self.localita_id:
            QMessageBox.warning(self, "Errore", "Seleziona una località.")
            return
        
        # Raccoglie i dati
        classificazione = self.classificazione_edit.text().strip() or None
        consistenza = self.consistenza_edit.text().strip() or None
        numero_piani = self.piani_edit.value() if self.piani_edit.value() > 0 else None
        numero_vani = self.vani_edit.value() if self.vani_edit.value() > 0 else None
        
        # Crea il dizionario dei dati dell'immobile
        self.immobile_data = {
            'natura': natura,
            'localita_id': self.localita_id,
            'localita_nome': self.localita_display.text(),
            'classificazione': classificazione,
            'consistenza': consistenza,
            'numero_piani': numero_piani,
            'numero_vani': numero_vani
        }
        
        self.accept()

      # --- Dialog per la Selezione delle Località ---
# All'interno della classe LocalitaSelectionDialog in prova.py

# All'interno della classe LocalitaSelectionDialog in prova.py

# All'interno di prova.py

class LocalitaSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, parent=None, 
                 selection_mode: bool = False): # NUOVO parametro selection_mode
        super(LocalitaSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.selection_mode = selection_mode  # Memorizza la modalità operativa
        
        self.selected_localita_id: Optional[int] = None
        self.selected_localita_name: Optional[str] = None
        
        if self.selection_mode:
            self.setWindowTitle(f"Seleziona Località per Comune ID: {self.comune_id}")
        else:
            self.setWindowTitle(f"Gestione Località per Comune ID: {self.comune_id}")
            
        self.setMinimumSize(650, 450)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        # --- Tab 1: Seleziona/Visualizza/Modifica Esistente ---
        select_tab = QWidget()
        select_layout = QVBoxLayout(select_tab)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtra per nome:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare...")
        # Connetti textChanged a una lambda che chiama load_localita e aggiorna i pulsanti
        self.filter_edit.textChanged.connect(
            lambda: (self.load_localita(), self._aggiorna_stato_pulsanti_azione_localita())
        )
        filter_layout.addWidget(self.filter_edit)
        select_layout.addLayout(filter_layout)
        
        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(4)
        self.localita_table.setHorizontalHeaderLabels(["ID", "Nome", "Tipo", "Civico"])
        self.localita_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.localita_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.localita_table.setSelectionMode(QTableWidget.SingleSelection)
        self.localita_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_azione_localita)
        self.localita_table.itemDoubleClicked.connect(self._handle_double_click) # Gestirà doppio click
        select_layout.addWidget(self.localita_table)

        select_action_layout = QHBoxLayout()
        self.btn_modifica_localita = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Modifica Selezionata")
        self.btn_modifica_localita.setToolTip("Modifica i dati della località selezionata")
        self.btn_modifica_localita.clicked.connect(self.apri_modifica_localita_selezionata)
        if self.selection_mode: # In modalità selezione, nascondi il pulsante "Modifica"
            self.btn_modifica_localita.setVisible(False)
        select_action_layout.addWidget(self.btn_modifica_localita)
        select_action_layout.addStretch()
        select_layout.addLayout(select_action_layout)
        self.tabs.addTab(select_tab, "Visualizza Località") # Cambiato nome tab per chiarezza

        # --- Tab 2: Crea Nuova Località ---
        # Questo tab viene mostrato solo se non siamo in modalità selezione
        if not self.selection_mode:
            create_tab = QWidget()
            create_form_layout = QFormLayout(create_tab)
            self.nome_edit_nuova = QLineEdit()
            self.tipo_combo_nuova = QComboBox()
            self.tipo_combo_nuova.addItems(["regione", "via", "borgata"])
            self.civico_spinbox_nuova = QSpinBox()
            self.civico_spinbox_nuova.setMinimum(0)
            self.civico_spinbox_nuova.setMaximum(99999)
            self.civico_spinbox_nuova.setSpecialValueText("Nessuno")
            create_form_layout.addRow(QLabel("Nome località (*):"), self.nome_edit_nuova)
            create_form_layout.addRow(QLabel("Tipo (*):"), self.tipo_combo_nuova)
            create_form_layout.addRow(QLabel("Numero Civico (0 se assente):"), self.civico_spinbox_nuova)
            self.btn_salva_nuova_localita = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton) ,"Salva Nuova Località")
            self.btn_salva_nuova_localita.clicked.connect(self._salva_nuova_localita_da_tab)
            create_form_layout.addRow(self.btn_salva_nuova_localita)
            self.tabs.addTab(create_tab, "Crea Nuova Località")

        # --- Pulsanti in fondo al dialogo ---
        buttons_layout = QHBoxLayout()
        
        # Pulsante SELEZIONA (solo in modalità selezione)
        self.select_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton),"Seleziona")
        self.select_button.setToolTip("Conferma la località selezionata dalla tabella")
        self.select_button.clicked.connect(self._conferma_selezione)
        if not self.selection_mode: # Nascondi se non in modalità selezione
            self.select_button.setVisible(False)
        buttons_layout.addWidget(self.select_button)
        
        buttons_layout.addStretch()
        
        # Pulsante ANNULLA/CHIUDI
        cancel_text = "Annulla" if self.selection_mode else "Chiudi"
        self.chiudi_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton), cancel_text)
        self.chiudi_button.clicked.connect(self.reject) # self.reject chiude il dialogo senza segnalare accettazione
        buttons_layout.addWidget(self.chiudi_button)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        
        self.load_localita() # Carica i dati e aggiorna lo stato dei pulsanti

    def _handle_double_click(self, item: QTableWidgetItem):
        """Gestisce il doppio click sulla tabella."""
        if self.selection_mode and self.tabs.currentIndex() == 0:
            # Se in modalità selezione e nel tab di visualizzazione, il doppio click seleziona
            self._conferma_selezione()
        elif not self.selection_mode and self.tabs.currentIndex() == 0:
            # Se non in modalità selezione, il doppio click apre la modifica
            self.apri_modifica_localita_selezionata()

    def _conferma_selezione(self):
        """Conferma la selezione della località e chiude il dialogo con Accept."""
        if not self.selection_mode: # Questa azione è solo per la modalità selezione
            return

        if self.tabs.currentIndex() == 0: # Assicurati che siamo nel tab di visualizzazione/selezione
            selected_items = self.localita_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una località dalla tabella.")
                return
            
            current_row = self.localita_table.currentRow()
            if current_row < 0: return

            try:
                self.selected_localita_id = int(self.localita_table.item(current_row, 0).text())
                nome = self.localita_table.item(current_row, 1).text()
                tipo = self.localita_table.item(current_row, 2).text()
                civico_item_text = self.localita_table.item(current_row, 3).text()
                
                self.selected_localita_name = nome
                if civico_item_text and civico_item_text != "-":
                    self.selected_localita_name += f", {civico_item_text}"
                self.selected_localita_name += f" ({tipo})"
                
                gui_logger.info(f"LocalitaSelectionDialog: Località selezionata ID: {self.selected_localita_id}, Nome: '{self.selected_localita_name}'")
                self.accept() # Chiude il dialogo e QDialog.Accepted viene restituito a exec_()
            except ValueError:
                QMessageBox.critical(self, "Errore Dati", "ID località non valido nella tabella.")
            except Exception as e:
                gui_logger.error(f"Errore in _conferma_selezione: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore durante la conferma della selezione: {e}")
        # else: se siamo nel tab "Crea Nuova", il pulsante "Seleziona" non dovrebbe essere attivo o visibile

    def _aggiorna_stato_pulsanti_azione_localita(self):
        is_select_tab_active = (self.tabs.currentIndex() == 0)
        has_selection_in_table = bool(self.localita_table.selectedItems())
        
        # Pulsante Modifica (visibile e attivo solo se non in selection_mode)
        self.btn_modifica_localita.setEnabled(
            is_select_tab_active and has_selection_in_table and not self.selection_mode
        )
        
        # Pulsante Seleziona (visibile e attivo solo se in selection_mode)
        self.select_button.setEnabled(
            is_select_tab_active and has_selection_in_table and self.selection_mode
        )

    def load_localita(self, filter_text: Optional[str] = None): # filter_text è già opzionale
        self.localita_table.setRowCount(0)
        self.localita_table.setSortingEnabled(False)
        
        # Usa il testo attuale dal QLineEdit del filtro, non il parametro 'filter_text' se non fornito
        actual_filter_text = self.filter_edit.text().strip() if hasattr(self, 'filter_edit') and self.filter_edit else None

        if self.comune_id:
            try:
                # Passa actual_filter_text al metodo del DBManager
                localita_results = self.db_manager.get_localita_by_comune(self.comune_id, actual_filter_text)
                if localita_results:
                    self.localita_table.setRowCount(len(localita_results))
                    for i, loc in enumerate(localita_results):
                        self.localita_table.setItem(i, 0, QTableWidgetItem(str(loc.get('id', ''))))
                        self.localita_table.setItem(i, 1, QTableWidgetItem(loc.get('nome', '')))
                        self.localita_table.setItem(i, 2, QTableWidgetItem(loc.get('tipo', '')))
                        civico_text = str(loc.get('civico', '')) if loc.get('civico') is not None else "-"
                        self.localita_table.setItem(i, 3, QTableWidgetItem(civico_text))
                    self.localita_table.resizeColumnsToContents()
            except Exception as e:
                gui_logger.error(f"Errore caricamento località per comune {self.comune_id}: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare le località: {e}")
        
        self.localita_table.setSortingEnabled(True)
        self._aggiorna_stato_pulsanti_azione_localita() # Chiamata fondamentale qui

    # Mantenga invariati i metodi _salva_nuova_localita_da_tab, 
    # apri_modifica_localita_selezionata, e _get_selected_localita_id_from_table
    # come erano nella sua ultima versione funzionante per quelle logiche.
    # ... (copia qui i metodi _salva_nuova_localita_da_tab, apri_modifica_localita_selezionata, 
    #  e _get_selected_localita_id_from_table dalla tua versione precedente del codice)
    def _salva_nuova_localita_da_tab(self):
        nome = self.nome_edit_nuova.text().strip()
        tipo = self.tipo_combo_nuova.currentText()
        civico_val = self.civico_spinbox_nuova.value()
        civico = civico_val if self.civico_spinbox_nuova.text() != self.civico_spinbox_nuova.specialValueText() and civico_val != 0 else None
        if not nome:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
            self.nome_edit_nuova.setFocus()
            return
        if not self.comune_id:
            QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato. Impossibile creare località.")
            return
        try:
            localita_id_creata = self.db_manager.insert_localita(self.comune_id, nome, tipo, civico)
            if localita_id_creata is not None:
                QMessageBox.information(self, "Località Creata", f"Località '{nome}' registrata con ID: {localita_id_creata}")
                self.load_localita() 
                self.tabs.setCurrentIndex(0) 
                self.nome_edit_nuova.clear()
                self.tipo_combo_nuova.setCurrentIndex(0) 
                self.civico_spinbox_nuova.setValue(0) 
        except (DBDataError, DBMError) as dbe:
            gui_logger.error(f"Errore inserimento località: {dbe}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Impossibile inserire località:\n{getattr(dbe, 'message', str(dbe))}")
        except Exception as e:
            gui_logger.error(f"Errore imprevisto inserimento località: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {e}")

    def apri_modifica_localita_selezionata(self):
        localita_id_sel = self._get_selected_localita_id_from_table()
        if localita_id_sel is not None:
            dialog = ModificaLocalitaDialog(self.db_manager, localita_id_sel, self.comune_id, self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_localita() 
        else:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una località dalla tabella per modificarla.")
            
    def _get_selected_localita_id_from_table(self) -> Optional[int]:
        selected_items = self.localita_table.selectedItems()
        if not selected_items: return None
        current_row = self.localita_table.currentRow()
        if current_row < 0: return None
        id_item = self.localita_table.item(current_row, 0)
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def _salva_nuova_localita_da_tab(self): # NUOVO METODO per il pulsante nel tab "Crea Nuova"
        nome = self.nome_edit.text().strip() # Assumendo che questi siano i QLineEdit del tab "Crea"
        tipo = self.tipo_combo.currentText()
        civico_val = self.civico_edit.value()
        civico = civico_val if self.civico_edit.text() != self.civico_edit.specialValueText() and civico_val > 0 else None

        if not nome:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
            self.nome_edit.setFocus()
            return
        if not self.comune_id:
            QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato per la creazione della località.")
            return

        try:
            localita_id_creata = self.db_manager.insert_localita(
                self.comune_id, nome, tipo, civico
            )
            if localita_id_creata is not None:
                QMessageBox.information(self, "Località Creata", f"Località '{nome}' registrata con ID: {localita_id_creata}")
                self.load_localita() # Ricarica la lista nel tab "Visualizza/Modifica"
                self.tabs.setCurrentIndex(0) # Torna al primo tab
                # Pulisci i campi del form di creazione
                self.nome_edit.clear()
                self.tipo_combo.setCurrentIndex(0) # o un default
                self.civico_edit.setValue(self.civico_edit.minimum()) # o 0 e special value text
            # else: gestito da eccezioni in insert_localita
        except (DBDataError, DBMError) as dbe:
            gui_logger.error(f"Errore inserimento località: {dbe}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Impossibile inserire località:\n{dbe.message if hasattr(dbe, 'message') else str(dbe)}")
        except Exception as e:
            gui_logger.error(f"Errore imprevisto inserimento località: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {e}")
    
    # Rimuovi il vecchio `handle_selection_or_creation` se non più usato dal pulsante OK generale.
    # def handle_selection_or_creation(self): ... (RIMUOVERE SE OK BUTTON È RIMOSSO)

    # ... (resto dei metodi: load_localita, filter_localita, apri_modifica_localita_selezionata, _get_selected_localita_id_from_table)

    def _tab_changed(self, index):
        """Gestisce il cambio di tab e aggiorna il testo del pulsante OK."""
        if index == 0: # Tab "Seleziona/Modifica Esistente"
            self.ok_button.setText("Seleziona Località")
            self.ok_button.setToolTip("Conferma la località selezionata dalla tabella.")
        else: # Tab "Crea Nuova"
            self.ok_button.setText("Crea e Seleziona")
            self.ok_button.setToolTip("Crea la nuova località e la seleziona.")
        self._aggiorna_stato_pulsanti_azione_localita()


    def _aggiorna_stato_pulsanti_azione_localita(self):
        """Abilita/disabilita il pulsante Modifica Località."""
        # Il pulsante Modifica è visibile solo se il tab "Visualizza e Modifica" è attivo
        is_select_tab_active = (self.tabs.currentIndex() == 0) 
        has_selection_in_table = bool(self.localita_table.selectedItems())
        
        # Abilita il pulsante "Modifica Selezionata" solo se siamo nel tab corretto 
        # E se una riga è selezionata nella tabella
        self.btn_modifica_localita.setEnabled(is_select_tab_active and has_selection_in_table)
        
        # La riga seguente che si riferiva a self.ok_button va rimossa:
        # self.ok_button.setEnabled(True) # Rimuovi questa riga


    def _get_selected_localita_id_from_table(self) -> Optional[int]: # NUOVO METODO HELPER
        selected_items = self.localita_table.selectedItems()
        if not selected_items:
            return None
        current_row = self.localita_table.currentRow()
        if current_row < 0: return None
        id_item = self.localita_table.item(current_row, 0) # Colonna ID
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def apri_modifica_localita_selezionata(self): # NUOVO METODO
        localita_id_sel = self._get_selected_localita_id_from_table()
        if localita_id_sel is not None:
            # Istanziamo e apriamo ModificaLocalitaDialog
            dialog = ModificaLocalitaDialog(self.db_manager, localita_id_sel, self.comune_id, self) # Passa comune_id
            if dialog.exec_() == QDialog.Accepted:
                QMessageBox.information(self, "Modifica Località", "Modifiche alla località salvate con successo.")
                self.load_localita(self.filter_edit.text().strip() or None) # Ricarica con filtro corrente
        else:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una località dalla tabella per modificarla.")

    # Rinomina il vecchio handle_selection a handle_selection_or_creation
    def handle_selection_or_creation(self): # Unico gestore per il pulsante OK
        current_tab_index = self.tabs.currentIndex()
        if current_tab_index == 0: # Tab "Seleziona/Modifica Esistente" -> Azione di Selezione
            selected_rows = self.localita_table.selectedIndexes()
            if not selected_rows:
                QMessageBox.warning(self, "Attenzione", "Seleziona una località dalla tabella.")
                return
            row = selected_rows[0].row()
            self.selected_localita_id = int(self.localita_table.item(row, 0).text())
            nome = self.localita_table.item(row, 1).text()
            tipo = self.localita_table.item(row, 2).text()
            civico = self.localita_table.item(row, 3).text()
            self.selected_localita_name = nome
            if civico != "-": self.selected_localita_name += f", {civico}"
            self.selected_localita_name += f" ({tipo})"
            self.accept() # Conferma la selezione
        
        else:  # Tab "Crea Nuova" -> Azione di Creazione (come prima)
            nome = self.nome_edit.text().strip()
            tipo = self.tipo_combo.currentText()
            civico_val = self.civico_edit.value()
            # Se specialValueText è "Nessun civico" e civico_val è 0, allora è None
            civico = civico_val if self.civico_edit.text() != self.civico_edit.specialValueText() and civico_val > 0 else None

            if not nome:
                QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
                self.nome_edit.setFocus()
                return
            if not self.comune_id:
                QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato.")
                return

            try:
                localita_id_creata = self.db_manager.insert_localita(
                    self.comune_id, nome, tipo, civico
                )
                if localita_id_creata is not None:
                    self.selected_localita_id = localita_id_creata
                    self.selected_localita_name = nome
                    if civico: self.selected_localita_name += f", {civico}"
                    self.selected_localita_name += f" ({tipo})"
                    QMessageBox.information(self, "Località Creata/Trovata", f"Località '{self.selected_localita_name}' registrata con ID: {self.selected_localita_id}")
                    self.load_localita() # Ricarica la lista nel tab "Seleziona"
                    self.tabs.setCurrentIndex(0) # Torna al tab di selezione
                    # Trova e seleziona la località appena creata (opzionale)
                    for r in range(self.localita_table.rowCount()):
                        if self.localita_table.item(r,0) and int(self.localita_table.item(r,0).text()) == self.selected_localita_id:
                            self.localita_table.selectRow(r)
                            break
                    # Non chiamare self.accept() qui se l'utente deve poi selezionare dalla lista
                    # o se il pulsante era "Crea e Seleziona", allora self.accept() è corretto.
                    # Dato il testo "Crea e Seleziona", self.accept() ci sta.
                    self.accept() 
                # else: gestito da eccezioni
            except (DBDataError, DBMError) as dbe:
                gui_logger.error(f"Errore inserimento località: {dbe}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Impossibile inserire località:\n{dbe.message if hasattr(dbe, 'message') else str(dbe)}")
            except Exception as e:
                gui_logger.error(f"Errore imprevisto inserimento località: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {e}")

    # ... (load_localita, filter_localita come prima, assicurati che _aggiorna_stato_pulsanti_azione_localita sia chiamato in load_localita)
    def load_localita(self, filter_text: Optional[str] = None):
        # ... (come l'avevamo implementata, chiamando db_manager.get_localita_by_comune) ...
        self.localita_table.setRowCount(0)
        self.localita_table.setSortingEnabled(False)
        if self.comune_id:
            try:
                localita_results = self.db_manager.get_localita_by_comune(self.comune_id, filter_text)
                if localita_results:
                    self.localita_table.setRowCount(len(localita_results))
                    for i, loc in enumerate(localita_results):
                        self.localita_table.setItem(i, 0, QTableWidgetItem(str(loc.get('id', ''))))
                        self.localita_table.setItem(i, 1, QTableWidgetItem(loc.get('nome', '')))
                        self.localita_table.setItem(i, 2, QTableWidgetItem(loc.get('tipo', '')))
                        civico_text = str(loc.get('civico', '')) if loc.get('civico') is not None else "-"
                        self.localita_table.setItem(i, 3, QTableWidgetItem(civico_text))
                    self.localita_table.resizeColumnsToContents()
            except Exception as e:
                gui_logger.error(f"Errore caricamento località per comune {self.comune_id}: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare le località: {e}")
        else:
            self.localita_table.setRowCount(1)
            self.localita_table.setItem(0,0,QTableWidgetItem("ID Comune non disponibile per caricare località."))
        
        self.localita_table.setSortingEnabled(True)
        self._aggiorna_stato_pulsanti_azione_localita() # Chiamata qui

# In prova.py, aggiungi questa nuova classe

class ModificaLocalitaDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, localita_id: int, comune_id_parent: int, parent=None): # Aggiunto comune_id_parent
        super().__init__(parent)
        self.db_manager = db_manager
        self.localita_id = localita_id
        self.comune_id_parent = comune_id_parent # ID del comune a cui questa località appartiene (non modificabile)
        self.localita_data_originale = None

        self.setWindowTitle(f"Modifica Dati Località ID: {self.localita_id}")
        self.setMinimumWidth(450)

        self._init_ui()
        self._load_localita_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.id_label = QLabel(str(self.localita_id))
        form_layout.addRow("ID Località:", self.id_label)
        self.comune_display_label = QLabel("Caricamento nome comune...") # Verrà popolato
        form_layout.addRow("Comune di Appartenenza:", self.comune_display_label)

        self.nome_edit = QLineEdit()
        form_layout.addRow("Nome Località (*):", self.nome_edit)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["regione", "via", "borgata"]) # Coerente con la tabella
        form_layout.addRow("Tipo (*):", self.tipo_combo)

        self.civico_spinbox = QSpinBox()
        self.civico_spinbox.setMinimum(0) # 0 potrebbe significare "non applicabile"
        self.civico_spinbox.setMaximum(99999)
        self.civico_spinbox.setSpecialValueText("Nessuno") # Se 0 è "Nessuno"
        form_layout.addRow("Numero Civico (0 se assente):", self.civico_spinbox)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton),"Salva Modifiche")
        self.save_button.clicked.connect(self._save_changes)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCancelButton),"Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def _load_localita_data(self):
        # Metodo da creare in CatastoDBManager: get_localita_details(localita_id)
        # Dovrebbe restituire: id, nome, tipo, civico, comune_id, e il nome del comune (comune_nome)
        self.localita_data_originale = self.db_manager.get_localita_details(self.localita_id) # Metodo da creare

        if not self.localita_data_originale:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare dati per località ID: {self.localita_id}.")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, self.reject)
            return

        self.nome_edit.setText(self.localita_data_originale.get('nome', ''))
        
        tipo_idx = self.tipo_combo.findText(self.localita_data_originale.get('tipo', ''), Qt.MatchFixedString)
        if tipo_idx >= 0: self.tipo_combo.setCurrentIndex(tipo_idx)
        
        civico_val = self.localita_data_originale.get('civico')
        if civico_val is not None:
            self.civico_spinbox.setValue(civico_val)
        else: # Se civico è NULL nel DB
            self.civico_spinbox.setValue(self.civico_spinbox.minimum()) # Imposta a 0 (che potrebbe essere "Nessuno")
            # o se 0 è un civico valido, dovresti avere un modo per distinguere
            # Forse il QSpinBox non è ideale se NULL è molto diverso da 0.
            # Un QLineEdit che accetta numeri o è vuoto potrebbe essere più flessibile per il civico.
            # Per ora, lasciamo QSpinBox e 0 (con specialValueText) per NULL.

        # Visualizza il nome del comune (non modificabile qui)
        self.comune_display_label.setText(
            f"{self.localita_data_originale.get('comune_nome', 'N/D')} (ID: {self.localita_data_originale.get('comune_id', 'N/D')})"
        )
        # Verifica che il comune_id della località corrisponda a quello del dialogo genitore
        if self.localita_data_originale.get('comune_id') != self.comune_id_parent:
            gui_logger.warning(f"Incoerenza Comune ID: Località {self.localita_id} appartiene a comune {self.localita_data_originale.get('comune_id')} ma aperta da contesto comune {self.comune_id_parent}")
            # Potresti mostrare un avviso, ma per ora procediamo.


    def _save_changes(self):
        dati_modificati = {
            "nome": self.nome_edit.text().strip(),
            "tipo": self.tipo_combo.currentText(),
        }
        
        civico_val = self.civico_spinbox.value()
        if self.civico_spinbox.text() == self.civico_spinbox.specialValueText() or civico_val == 0:
            dati_modificati["civico"] = None
        else:
            dati_modificati["civico"] = civico_val

        if not dati_modificati["nome"]:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
            self.nome_edit.setFocus()
            return
        # Aggiungi altre validazioni UI se necessario
        try:
            gui_logger.info(f"Tentativo di aggiornare località ID {self.localita_id} con: {dati_modificati}")
            self.db_manager.update_localita(self.localita_id, dati_modificati) # Chiamata al metodo

            gui_logger.info(f"Località ID {self.localita_id} aggiornata con successo.")
            self.accept() # Chiudi se ha successo

        except DBUniqueConstraintError as uve:
            gui_logger.warning(f"Violazione unicità per località ID {self.localita_id}: {uve.message}")
            QMessageBox.warning(self, "Errore di Unicità",
                                f"Impossibile salvare le modifiche:\n{uve.message}\n"
                                "Una località con lo stesso nome e civico potrebbe già esistere in questo comune.")
            self.nome_edit.setFocus() # O il campo civico se più appropriato
        except DBNotFoundError as nfe:
            gui_logger.error(f"Località ID {self.localita_id} non trovata per l'aggiornamento: {nfe.message}")
            QMessageBox.critical(self, "Errore Aggiornamento", str(nfe.message))
            self.reject() # Chiudi perché il record non esiste più
        except DBDataError as dde:
            gui_logger.warning(f"Errore dati per località ID {self.localita_id}: {dde.message}")
            QMessageBox.warning(self, "Errore Dati Non Validi",
                                f"Impossibile salvare le modifiche:\n{dde.message}")
        except DBMError as dbe:
            gui_logger.error(f"Errore DB aggiornando località ID {self.localita_id}: {dbe.message}")
            QMessageBox.critical(self, "Errore Database", f"Errore salvataggio località:\n{dbe.message}")
        except AttributeError as ae: # Per debug se il metodo non è ancora in db_manager
            gui_logger.critical(f"Metodo 'update_localita' non trovato o altro AttributeError: {ae}", exc_info=True)
            QMessageBox.critical(self, "Errore Implementazione", "Funzionalità non completamente implementata.")
        except Exception as e:
            gui_logger.critical(f"Errore imprevisto salvataggio località ID {self.localita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico", f"Errore imprevisto: {e}")

class ReportisticaWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(ReportisticaWidget, self).__init__(parent)
        self.db_manager = db_manager
        
        layout = QVBoxLayout()
        
        # Tabs per i diversi tipi di report
        tabs = QTabWidget()
        
        # Tab Certificato Proprietà
        certificato_tab = QWidget()
        certificato_layout = QVBoxLayout()
        
        # Input per ID partita
        input_layout = QHBoxLayout()
        partita_id_label = QLabel("ID della partita:")
        self.partita_id_edit = QSpinBox()
        self.partita_id_edit.setMinimum(1)
        self.partita_id_edit.setMaximum(999999)
        self.search_partita_button = QPushButton("Cerca...")
        self.search_partita_button.clicked.connect(self.search_partita)
        
        input_layout.addWidget(partita_id_label)
        input_layout.addWidget(self.partita_id_edit)
        input_layout.addWidget(self.search_partita_button)
        
        # Pulsante genera report
        self.generate_cert_button = QPushButton("Genera Certificato")
        self.generate_cert_button.clicked.connect(self.generate_certificato)
        
        # Area di visualizzazione
        self.certificato_text = QTextEdit()
        self.certificato_text.setReadOnly(True)
        
        # Pulsante esporta
        self.export_cert_button = QPushButton("Esporta in File")
        self.export_cert_button.clicked.connect(lambda: self.export_report(self.certificato_text.toPlainText(), "certificato"))
        
        certificato_layout.addLayout(input_layout)
        certificato_layout.addWidget(self.generate_cert_button)
        certificato_layout.addWidget(self.certificato_text)
        certificato_layout.addWidget(self.export_cert_button)
        
        certificato_tab.setLayout(certificato_layout)
        tabs.addTab(certificato_tab, "Certificato Proprietà")
        
        # Tab Report Genealogico
        genealogico_tab = QWidget()
        genealogico_layout = QVBoxLayout()
        
        # Input per ID partita
        input_gen_layout = QHBoxLayout()
        partita_id_gen_label = QLabel("ID della partita:")
        self.partita_id_gen_edit = QSpinBox()
        self.partita_id_gen_edit.setMinimum(1)
        self.partita_id_gen_edit.setMaximum(999999)
        self.search_partita_gen_button = QPushButton("Cerca...")
        self.search_partita_gen_button.clicked.connect(self.search_partita_gen)
        
        input_gen_layout.addWidget(partita_id_gen_label)
        input_gen_layout.addWidget(self.partita_id_gen_edit)
        input_gen_layout.addWidget(self.search_partita_gen_button)
        
        # Pulsante genera report
        self.generate_gen_button = QPushButton("Genera Report Genealogico")
        self.generate_gen_button.clicked.connect(self.generate_genealogico)
        
        # Area di visualizzazione
        self.genealogico_text = QTextEdit()
        self.genealogico_text.setReadOnly(True)
        
        # Pulsante esporta
        self.export_gen_button = QPushButton("Esporta in File")
        self.export_gen_button.clicked.connect(lambda: self.export_report(self.genealogico_text.toPlainText(), "genealogico"))
        
        genealogico_layout.addLayout(input_gen_layout)
        genealogico_layout.addWidget(self.generate_gen_button)
        genealogico_layout.addWidget(self.genealogico_text)
        genealogico_layout.addWidget(self.export_gen_button)
        
        genealogico_tab.setLayout(genealogico_layout)
        tabs.addTab(genealogico_tab, "Report Genealogico")
        
        # Tab Report Possessore
        possessore_tab = QWidget()
        possessore_layout = QVBoxLayout()
        
        # Input per ID possessore
        input_pos_layout = QHBoxLayout()
        possessore_id_label = QLabel("ID del possessore:")
        self.possessore_id_edit = QSpinBox()
        self.possessore_id_edit.setMinimum(1)
        self.possessore_id_edit.setMaximum(999999)
        self.search_possessore_button = QPushButton("Cerca...")
        self.search_possessore_button.clicked.connect(self.search_possessore)
        
        input_pos_layout.addWidget(possessore_id_label)
        input_pos_layout.addWidget(self.possessore_id_edit)
        input_pos_layout.addWidget(self.search_possessore_button)
        
        # Pulsante genera report
        self.generate_pos_button = QPushButton("Genera Report Possessore")
        self.generate_pos_button.clicked.connect(self.generate_possessore)
        
        # Area di visualizzazione
        self.possessore_text = QTextEdit()
        self.possessore_text.setReadOnly(True)
        
        # Pulsante esporta
        self.export_pos_button = QPushButton("Esporta in File")
        self.export_pos_button.clicked.connect(lambda: self.export_report(self.possessore_text.toPlainText(), "possessore"))
        
        possessore_layout.addLayout(input_pos_layout)
        possessore_layout.addWidget(self.generate_pos_button)
        possessore_layout.addWidget(self.possessore_text)
        possessore_layout.addWidget(self.export_pos_button)
        
        possessore_tab.setLayout(possessore_layout)
        tabs.addTab(possessore_tab, "Report Possessore")
        
        # Tab Report Consultazioni
        consultazioni_tab = QWidget()
        consultazioni_layout = QVBoxLayout()
        
        # Input per filtri
        filters_layout = QGridLayout()
        
        data_inizio_label = QLabel("Data inizio:")
        self.data_inizio_edit = QDateEdit()
        self.data_inizio_edit.setCalendarPopup(True)
        self.data_inizio_edit.setDate(QDate.currentDate().addYears(-1))
        self.data_inizio_check = QCheckBox("Usa filtro")
        self.data_inizio_check.setChecked(True)
        
        data_fine_label = QLabel("Data fine:")
        self.data_fine_edit = QDateEdit()
        self.data_fine_edit.setCalendarPopup(True)
        self.data_fine_edit.setDate(QDate.currentDate())
        self.data_fine_check = QCheckBox("Usa filtro")
        self.data_fine_check.setChecked(True)
        
        richiedente_label = QLabel("Richiedente:")
        self.richiedente_edit = QLineEdit()
        self.richiedente_edit.setPlaceholderText("Qualsiasi richiedente")
        
        filters_layout.addWidget(data_inizio_label, 0, 0)
        filters_layout.addWidget(self.data_inizio_edit, 0, 1)
        filters_layout.addWidget(self.data_inizio_check, 0, 2)
        
        filters_layout.addWidget(data_fine_label, 1, 0)
        filters_layout.addWidget(self.data_fine_edit, 1, 1)
        filters_layout.addWidget(self.data_fine_check, 1, 2)
        
        filters_layout.addWidget(richiedente_label, 2, 0)
        filters_layout.addWidget(self.richiedente_edit, 2, 1, 1, 2)
        
        # Pulsante genera report
        self.generate_cons_button = QPushButton("Genera Report Consultazioni")
        self.generate_cons_button.clicked.connect(self.generate_consultazioni)
        
        # Area di visualizzazione
        self.consultazioni_text = QTextEdit()
        self.consultazioni_text.setReadOnly(True)
        
        # Pulsante esporta
        self.export_cons_button = QPushButton("Esporta in File")
        self.export_cons_button.clicked.connect(lambda: self.export_report(self.consultazioni_text.toPlainText(), "consultazioni"))
        
        consultazioni_layout.addLayout(filters_layout)
        consultazioni_layout.addWidget(self.generate_cons_button)
        consultazioni_layout.addWidget(self.consultazioni_text)
        consultazioni_layout.addWidget(self.export_cons_button)
        
        consultazioni_tab.setLayout(consultazioni_layout)
        tabs.addTab(consultazioni_tab, "Report Consultazioni")
        
        layout.addWidget(tabs)
        self.setLayout(layout)
    
    def search_partita(self):
        """Apre un dialogo per cercare una partita."""
        dialog = PartitaSearchDialog(self.db_manager, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_partita_id:
            self.partita_id_edit.setValue(dialog.selected_partita_id)
    
    def search_partita_gen(self):
        """Apre un dialogo per cercare una partita per il report genealogico."""
        dialog = PartitaSearchDialog(self.db_manager, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_partita_id:
            self.partita_id_gen_edit.setValue(dialog.selected_partita_id)
    
    def search_possessore(self):
        """Apre un dialogo per cercare un possessore."""
        dialog = PossessoreSelSctionDialog(self.db_manager, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_possessore_id:
            self.possessore_id_edit.setValue(dialog.selected_possessore_id)
    
    def generate_certificato(self):
        """Genera un certificato di proprietà."""
        partita_id = self.partita_id_edit.value()
        
        if partita_id <= 0:
            QMessageBox.warning(self, "Errore", "Inserisci un ID partita valido.")
            return
        
        certificato = self.db_manager.genera_certificato_proprieta(partita_id)
        
        if certificato:
            self.certificato_text.setText(certificato)
        else:
            QMessageBox.warning(self, "Errore", f"Impossibile generare il certificato per la partita ID {partita_id}.")
    
    def generate_genealogico(self):
        """Genera un report genealogico."""
        partita_id = self.partita_id_gen_edit.value()
        
        if partita_id <= 0:
            QMessageBox.warning(self, "Errore", "Inserisci un ID partita valido.")
            return
        
        report = self.db_manager.genera_report_genealogico(partita_id)
        
        if report:
            self.genealogico_text.setText(report)
        else:
            QMessageBox.warning(self, "Errore", f"Impossibile generare il report genealogico per la partita ID {partita_id}.")
    
    def generate_possessore(self):
        """Genera un report sul possessore."""
        possessore_id = self.possessore_id_edit.value()
        
        if possessore_id <= 0:
            QMessageBox.warning(self, "Errore", "Inserisci un ID possessore valido.")
            return
        
        report = self.db_manager.genera_report_possessore(possessore_id)
        
        if report:
            self.possessore_text.setText(report)
        else:
            QMessageBox.warning(self, "Errore", f"Impossibile generare il report per il possessore ID {possessore_id}.")
    
    def generate_consultazioni(self):
        """Genera un report sulle consultazioni."""
        data_inizio = self.data_inizio_edit.date().toPyDate() if self.data_inizio_check.isChecked() else None
        data_fine = self.data_fine_edit.date().toPyDate() if self.data_fine_check.isChecked() else None
        richiedente = self.richiedente_edit.text().strip() or None
        
        report = self.db_manager.genera_report_consultazioni(data_inizio, data_fine, richiedente)
        
        if report:
            self.consultazioni_text.setText(report)
        else:
            QMessageBox.warning(self, "Errore", "Impossibile generare il report consultazioni.")
    
    def export_report(self, text, report_type):
        """Esporta un report in un file di testo."""
        if not text:
            QMessageBox.warning(self, "Attenzione", "Nessun report da esportare.")
            return
        
        oggi = datetime.now().strftime("%Y%m%d")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Salva Report", f"report_{report_type}_{oggi}.txt", "File di testo (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)
                QMessageBox.information(self, "Esportazione Completata", f"Report salvato in {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante l'esportazione: {str(e)}")

           # --- Dialog di Ricerca Partite ---
class PartitaSearchDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super(PartitaSearchDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.selected_partita_id = None
        
        self.setWindowTitle("Ricerca Partita")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        # Form di ricerca
        form_group = QGroupBox("Criteri di Ricerca")
        form_layout = QGridLayout()
        
        # Comune
        comune_label = QLabel("Comune:")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_id = None
        self.comune_display = QLabel("Tutti i comuni")
        self.clear_comune_button = QPushButton("Cancella")
        self.clear_comune_button.clicked.connect(self.clear_comune)
        
        form_layout.addWidget(comune_label, 0, 0)
        form_layout.addWidget(self.comune_button, 0, 1)
        form_layout.addWidget(self.comune_display, 0, 2)
        form_layout.addWidget(self.clear_comune_button, 0, 3)
        
        # Numero partita
        numero_label = QLabel("Numero Partita:")
        self.numero_edit = QSpinBox()
        self.numero_edit.setMinimum(0)
        self.numero_edit.setMaximum(9999)
        self.numero_edit.setSpecialValueText("Qualsiasi")
        
        form_layout.addWidget(numero_label, 1, 0)
        form_layout.addWidget(self.numero_edit, 1, 1)
        
        # Possessore
        possessore_label = QLabel("Nome Possessore:")
        self.possessore_edit = QLineEdit()
        self.possessore_edit.setPlaceholderText("Qualsiasi possessore")
        
        form_layout.addWidget(possessore_label, 2, 0)
        form_layout.addWidget(self.possessore_edit, 2, 1, 1, 3)
        
        # Natura immobile
        natura_label = QLabel("Natura Immobile:")
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Qualsiasi natura immobile")
        
        form_layout.addWidget(natura_label, 3, 0)
        form_layout.addWidget(self.natura_edit, 3, 1, 1, 3)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Pulsante ricerca
        search_button = QPushButton("Cerca")
        search_button.clicked.connect(self.do_search)
        layout.addWidget(search_button)
        
        # Tabella risultati
        results_group = QGroupBox("Risultati")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["ID", "Comune", "Numero", "Tipo", "Stato"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.itemDoubleClicked.connect(self.select_partita)
        
        results_layout.addWidget(self.results_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Seleziona")
        self.select_button.clicked.connect(self.select_partita)
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.select_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def select_comune(self):
        """Apre il selettore di comuni."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)
    
    def clear_comune(self):
        """Cancella il comune selezionato."""
        self.comune_id = None
        self.comune_display.setText("Tutti i comuni")
    
    def do_search(self):
        """Esegue la ricerca partite in base ai criteri."""
        # Prepara i parametri
        comune_id = self.comune_id
        numero_partita = self.numero_edit.value() if self.numero_edit.value() > 0 else None
        possessore = self.possessore_edit.text().strip() or None
        natura = self.natura_edit.text().strip() or None
        
        # Esegue la ricerca
        partite = self.db_manager.search_partite(
            comune_id=comune_id,
            numero_partita=numero_partita,
            possessore=possessore,
            immobile_natura=natura
        )
        
        # Popola la tabella risultati
        self.results_table.setRowCount(0)
        
        for partita in partite:
            row_position = self.results_table.rowCount()
            self.results_table.insertRow(row_position)
            
            self.results_table.setItem(row_position, 0, QTableWidgetItem(str(partita.get('id', ''))))
            self.results_table.setItem(row_position, 1, QTableWidgetItem(partita.get('comune_nome', '')))
            self.results_table.setItem(row_position, 2, QTableWidgetItem(str(partita.get('numero_partita', ''))))
            self.results_table.setItem(row_position, 3, QTableWidgetItem(partita.get('tipo', '')))
            self.results_table.setItem(row_position, 4, QTableWidgetItem(partita.get('stato', '')))
        
        # Adatta le colonne al contenuto
        self.results_table.resizeColumnsToContents()
    
    def select_partita(self):
        """Seleziona la partita e accetta il dialogo."""
        selected_rows = self.results_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione", "Seleziona una partita dalla tabella.")
            return
        
        row = selected_rows[0].row()
        partita_id_item = self.results_table.item(row, 0)
        
        if partita_id_item and partita_id_item.text().isdigit():
            self.selected_partita_id = int(partita_id_item.text())
            self.accept()
        else:
            QMessageBox.warning(self, "Errore", "ID partita non valido.")
class PeriodoStoricoDetailsDialog(QDialog):
    def __init__(self, db_manager: 'CatastoDBManager', periodo_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.periodo_id = periodo_id
        self.periodo_data_originale: Optional[Dict[str, Any]] = None

        self.setWindowTitle(f"Dettagli/Modifica Periodo Storico ID: {self.periodo_id}")
        self.setMinimumWidth(450)
        self.setModal(True)

        self._initUI()
        self._load_data()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Campi Visualizzazione (non editabili)
        self.id_label = QLabel(str(self.periodo_id))
        self.data_creazione_label = QLabel()
        self.data_modifica_label = QLabel()

        form_layout.addRow("ID Periodo:", self.id_label)

        # Campi Editabili
        self.nome_edit = QLineEdit()
        form_layout.addRow("Nome Periodo (*):", self.nome_edit)

        self.anno_inizio_spinbox = QSpinBox()
        self.anno_inizio_spinbox.setRange(0, 3000) # Adatta il range se necessario
        form_layout.addRow("Anno Inizio (*):", self.anno_inizio_spinbox)

        self.anno_fine_spinbox = QSpinBox()
        self.anno_fine_spinbox.setRange(0, 3000) 
        # Permetti "nessun anno fine" usando un valore speciale o gestendo 0 come "non impostato"
        self.anno_fine_spinbox.setSpecialValueText(" ") # Vuoto se 0 (o il minimo)
        self.anno_fine_spinbox.setMinimum(0) # 0 potrebbe significare "non specificato"
        form_layout.addRow("Anno Fine (0 se aperto):", self.anno_fine_spinbox)
        
        self.descrizione_edit = QTextEdit()
        self.descrizione_edit.setFixedHeight(100)
        form_layout.addRow("Descrizione:", self.descrizione_edit)

        form_layout.addRow("Data Creazione:", self.data_creazione_label)
        form_layout.addRow("Ultima Modifica:", self.data_modifica_label)
        
        main_layout.addLayout(form_layout)

        # Pulsanti
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._save_changes)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def _load_data(self):
        self.periodo_data_originale = self.db_manager.get_periodo_storico_details(self.periodo_id)

        if not self.periodo_data_originale:
            QMessageBox.critical(self, "Errore Caricamento", 
                                 f"Impossibile caricare i dettagli per il periodo ID: {self.periodo_id}.")
            # Chiudi il dialogo se i dati non possono essere caricati
            # Usiamo QTimer per permettere al messaggio di essere processato prima di chiudere
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, self.reject)
            return

        self.nome_edit.setText(self.periodo_data_originale.get('nome', ''))
        self.anno_inizio_spinbox.setValue(self.periodo_data_originale.get('anno_inizio', 0))
        
        anno_fine_val = self.periodo_data_originale.get('anno_fine')
        if anno_fine_val is not None:
            self.anno_fine_spinbox.setValue(anno_fine_val)
        else: # Se anno_fine è NULL nel DB
            self.anno_fine_spinbox.setValue(self.anno_fine_spinbox.minimum()) # Mostra testo speciale (" ")

        self.descrizione_edit.setText(self.periodo_data_originale.get('descrizione', ''))
        
        dc = self.periodo_data_originale.get('data_creazione')
        self.data_creazione_label.setText(dc.strftime('%Y-%m-%d %H:%M:%S') if dc else 'N/D')
        dm = self.periodo_data_originale.get('data_modifica')
        self.data_modifica_label.setText(dm.strftime('%Y-%m-%d %H:%M:%S') if dm else 'N/D')

    def _save_changes(self):
        dati_da_salvare = {
            "nome": self.nome_edit.text().strip(),
            "anno_inizio": self.anno_inizio_spinbox.value(),
            "descrizione": self.descrizione_edit.toPlainText().strip()
        }

        anno_fine_val_ui = self.anno_fine_spinbox.value()
        if self.anno_fine_spinbox.text() == self.anno_fine_spinbox.specialValueText() or anno_fine_val_ui == self.anno_fine_spinbox.minimum():
            dati_da_salvare["anno_fine"] = None # Salva NULL se vuoto o valore minimo
        else:
            dati_da_salvare["anno_fine"] = anno_fine_val_ui

        # Validazione base
        if not dati_da_salvare["nome"]:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome del periodo è obbligatorio.")
            self.nome_edit.setFocus()
            return
        if dati_da_salvare["anno_inizio"] <= 0: # O altra logica per anno inizio
            QMessageBox.warning(self, "Dati Non Validi", "L'anno di inizio deve essere valido.")
            self.anno_inizio_spinbox.setFocus()
            return
        if dati_da_salvare["anno_fine"] is not None and dati_da_salvare["anno_fine"] < dati_da_salvare["anno_inizio"]:
            QMessageBox.warning(self, "Date Non Valide", "L'anno di fine non può essere precedente all'anno di inizio.")
            self.anno_fine_spinbox.setFocus()
            return

        try:
            success = self.db_manager.update_periodo_storico(self.periodo_id, dati_da_salvare)
            if success:
                QMessageBox.information(self, "Successo", "Periodo storico aggiornato con successo.")
                self.accept() # Chiude il dialogo e segnala successo
            # else: # update_periodo_storico solleva eccezioni per fallimenti
            # QMessageBox.critical(self, "Errore", "Impossibile aggiornare il periodo storico.")
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            gui_logger.error(f"Errore salvataggio periodo storico ID {self.periodo_id}: {str(e)}")
            QMessageBox.critical(self, "Errore Salvataggio", str(e))
        except Exception as e_gen:
            gui_logger.critical(f"Errore imprevisto salvataggio periodo storico ID {self.periodo_id}: {str(e_gen)}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {str(e_gen)}")


class UserSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, parent=None, title="Seleziona Utente", exclude_user_id: Optional[int] = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.selected_user_id: Optional[int] = None
        self.exclude_user_id = exclude_user_id

        layout = QVBoxLayout(self)
        
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Nome Completo", "Ruolo", "Stato"])
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.itemDoubleClicked.connect(self._accept_selection)
        layout.addWidget(self.user_table)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("Seleziona")
        ok_button.clicked.connect(self._accept_selection)
        cancel_button = QPushButton("Annulla")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.load_users()

    def load_users(self):
        self.user_table.setRowCount(0)
        users = self.db_manager.get_utenti()
        for user_data in users:
            if self.exclude_user_id and user_data['id'] == self.exclude_user_id:
                continue
            row_pos = self.user_table.rowCount()
            self.user_table.insertRow(row_pos)
            self.user_table.setItem(row_pos, 0, QTableWidgetItem(str(user_data['id'])))
            self.user_table.setItem(row_pos, 1, QTableWidgetItem(user_data['username']))
            self.user_table.setItem(row_pos, 2, QTableWidgetItem(user_data['nome_completo']))
            self.user_table.setItem(row_pos, 3, QTableWidgetItem(user_data['ruolo']))
            self.user_table.setItem(row_pos, 4, QTableWidgetItem("Attivo" if user_data['attivo'] else "Non Attivo"))
        self.user_table.resizeColumnsToContents()


    def _accept_selection(self):
        selected_rows = self.user_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            self.selected_user_id = int(self.user_table.item(row, 0).text())
            self.accept()
        else:
            QMessageBox.warning(self, "Selezione", "Per favore, seleziona un utente dalla lista.")


# --- Finestra Principale ---# --- Finestra principale ---

# --- Widget per la Gestione Utenti ---
class GestioneUtentiWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, current_user_info: Optional[Dict], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user_info = current_user_info # Info dell'utente loggato
        self.is_admin = self.current_user_info.get('ruolo') == 'admin' if self.current_user_info else False

        layout = QVBoxLayout(self)
        
        # Pulsanti Azioni
        action_layout = QHBoxLayout()
        self.btn_crea_utente = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder), " Crea Nuovo Utente")
        self.btn_crea_utente.clicked.connect(self.crea_nuovo_utente)
        self.btn_crea_utente.setEnabled(self.is_admin)
        action_layout.addWidget(self.btn_crea_utente)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Tabella Utenti
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6) # ID, Username, Nome Completo, Email, Ruolo, Stato
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Nome Completo", "Email", "Ruolo", "Stato"])
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.user_table.itemDoubleClicked.connect(self.modifica_utente_selezionato) # Opzionale
        layout.addWidget(self.user_table)

        # Pulsanti di gestione per utente selezionato
        manage_layout = QHBoxLayout()
        self.btn_modifica_utente = QPushButton("Modifica Utente")
        self.btn_modifica_utente.clicked.connect(self.modifica_utente_selezionato)
        self.btn_modifica_utente.setEnabled(self.is_admin)

        self.btn_reset_password = QPushButton("Resetta Password")
        self.btn_reset_password.clicked.connect(self.reset_password_utente_selezionato)
        self.btn_reset_password.setEnabled(self.is_admin)

        self.btn_toggle_stato = QPushButton("Attiva/Disattiva Utente")
        self.btn_toggle_stato.clicked.connect(self.toggle_stato_utente_selezionato)
        self.btn_toggle_stato.setEnabled(self.is_admin)
        
        self.btn_delete_utente = QPushButton("Elimina Utente")
        self.btn_delete_utente.clicked.connect(self.elimina_utente_selezionato)
        self.btn_delete_utente.setEnabled(self.is_admin)


        manage_layout.addWidget(self.btn_modifica_utente)
        manage_layout.addWidget(self.btn_reset_password)
        manage_layout.addWidget(self.btn_toggle_stato)
        manage_layout.addWidget(self.btn_delete_utente)
        layout.addLayout(manage_layout)

        self.refresh_user_list()

    def refresh_user_list(self):
        self.user_table.setRowCount(0)
        utenti = self.db_manager.get_utenti() # Prende tutti gli utenti
        for user_data in utenti:
            row_pos = self.user_table.rowCount()
            self.user_table.insertRow(row_pos)
            self.user_table.setItem(row_pos, 0, QTableWidgetItem(str(user_data['id'])))
            self.user_table.setItem(row_pos, 1, QTableWidgetItem(user_data['username']))
            self.user_table.setItem(row_pos, 2, QTableWidgetItem(user_data['nome_completo']))
            self.user_table.setItem(row_pos, 3, QTableWidgetItem(user_data.get('email', 'N/D')))
            self.user_table.setItem(row_pos, 4, QTableWidgetItem(user_data['ruolo']))
            self.user_table.setItem(row_pos, 5, QTableWidgetItem("Attivo" if user_data['attivo'] else "Non Attivo"))
        self.user_table.resizeColumnsToContents()

    def crea_nuovo_utente(self):
        dialog = CreateUserDialog(self.db_manager, self) # CreateUserDialog come definito prima
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_user_list()
            QMessageBox.information(self, "Successo", "Nuovo utente creato.")

    def _get_selected_user_id(self) -> Optional[int]:
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Nessuna Selezione", "Per favore, seleziona un utente dalla lista.")
            return None
        try:
            return int(self.user_table.item(selected_rows[0].row(), 0).text())
        except (ValueError, AttributeError):
            QMessageBox.critical(self, "Errore", "Impossibile ottenere l'ID dell'utente selezionato.")
            return None
            
    def modifica_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None: return

        utente_attuale = self.db_manager.get_utente_by_id(user_id)
        if not utente_attuale:
            QMessageBox.critical(self, "Errore", f"Utente con ID {user_id} non trovato."); return

        # Qui aprirebbe un dialogo per modificare i dettagli, simile a CreateUserDialog ma pre-popolato
        # Per semplicità, usiamo QInputDialog per alcuni campi
        nome_attuale = utente_attuale.get('nome_completo', '')
        new_nome, ok = QInputDialog.getText(self, "Modifica Nome", f"Nuovo nome completo (attuale: '{nome_attuale}'):", text=nome_attuale)
        if not ok: return # Annullato

        email_attuale = utente_attuale.get('email', '')
        new_email, ok = QInputDialog.getText(self, "Modifica Email", f"Nuova email (attuale: '{email_attuale}'):", text=email_attuale)
        if not ok: return

        ruoli = ["admin", "archivista", "consultatore"]
        ruolo_attuale = utente_attuale.get('ruolo', 'consultatore')
        new_ruolo, ok = QInputDialog.getItem(self, "Modifica Ruolo", f"Nuovo ruolo (attuale: '{ruolo_attuale}'):", ruoli, ruoli.index(ruolo_attuale) if ruolo_attuale in ruoli else 0, False)
        if not ok: return

        update_params = {}
        if new_nome and new_nome != nome_attuale: update_params['nome_completo'] = new_nome
        if new_email and new_email != email_attuale: update_params['email'] = new_email
        if new_ruolo and new_ruolo != ruolo_attuale: update_params['ruolo'] = new_ruolo
        
        if update_params:
            if self.db_manager.update_user_details(user_id, **update_params):
                QMessageBox.information(self, "Successo", "Dettagli utente aggiornati.")
                self.refresh_user_list()
            else:
                QMessageBox.critical(self, "Errore", "Aggiornamento fallito. Controllare i log.")
        else:
            QMessageBox.information(self, "Info", "Nessuna modifica apportata.")


    def reset_password_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None: return
        if user_id == self.current_user_info.get('id'):
            QMessageBox.warning(self, "Azione Non Permessa", "Non puoi resettare la tua password da questa interfaccia.")
            return

        new_password, ok = QInputDialog.getText(self, "Reset Password", "Inserisci la nuova password temporanea:", QLineEdit.Password)
        if ok and new_password:
            new_password_confirm, ok_confirm = QInputDialog.getText(self, "Conferma Password", "Conferma la nuova password temporanea:", QLineEdit.Password)
            if ok_confirm and new_password == new_password_confirm:
                try:
                    new_hash = _hash_password(new_password)
                    if self.db_manager.reset_user_password(user_id, new_hash):
                        QMessageBox.information(self, "Successo", f"Password per utente ID {user_id} resettata.")
                    else:
                        QMessageBox.critical(self, "Errore", "Reset password fallito.")
                except Exception as e:
                    QMessageBox.critical(self, "Errore Hashing", f"Errore durante l'hashing: {e}")
            elif ok_confirm: # ma password non coincidono
                QMessageBox.warning(self, "Errore", "Le password non coincidono.")
        elif ok: # password vuota
             QMessageBox.warning(self, "Errore", "La password non può essere vuota.")


    def toggle_stato_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None: return
        if user_id == self.current_user_info.get('id'):
            QMessageBox.warning(self, "Azione Non Permessa", "Non puoi modificare lo stato del tuo account.")
            return

        utente_target = self.db_manager.get_utente_by_id(user_id)
        if not utente_target: QMessageBox.critical(self, "Errore", "Utente non trovato."); return

        nuovo_stato_attivo = not utente_target['attivo']
        azione_str = "RIATTIVARE" if nuovo_stato_attivo else "DISATTIVARE"
        
        reply = QMessageBox.question(self, "Conferma Stato", 
                                     f"L'utente '{utente_target['username']}' è attualmente {'ATTIVO' if utente_target['attivo'] else 'NON ATTIVO'}.\n"
                                     f"Vuoi {azione_str} questo utente?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            success = False
            if nuovo_stato_attivo:
                success = self.db_manager.activate_user(user_id)
            else:
                success = self.db_manager.deactivate_user(user_id)
            
            if success:
                QMessageBox.information(self, "Successo", f"Stato utente '{utente_target['username']}' aggiornato.")
                self.refresh_user_list()
            else:
                QMessageBox.critical(self, "Errore", "Aggiornamento stato fallito.")

    def elimina_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None: return
        if user_id == self.current_user_info.get('id'):
            QMessageBox.warning(self, "Azione Non Permessa", "Non puoi eliminare te stesso.")
            return

        utente_target = self.db_manager.get_utente_by_id(user_id)
        if not utente_target: QMessageBox.critical(self, "Errore", "Utente non trovato."); return

        reply = QMessageBox.warning(self, "Conferma Eliminazione", 
                                    f"ATTENZIONE: Stai per eliminare PERMANENTEMENTE l'utente '{utente_target['username']}' (ID: {user_id}).\n"
                                    "Questa operazione è IRREVERSIBILE e i riferimenti nei log verranno impostati a NULL (se configurato).\n"
                                    "Sei assolutamente sicuro?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Ulteriore conferma digitando lo username
            confirm_username, ok = QInputDialog.getText(self, "Conferma Finale", 
                                                        f"Per confermare l'eliminazione permanente di '{utente_target['username']}', riscrivi il suo username:")
            if ok and confirm_username == utente_target['username']:
                if self.db_manager.delete_user_permanently(user_id):
                    QMessageBox.information(self, "Successo", f"Utente '{utente_target['username']}' eliminato permanentemente.")
                    self.refresh_user_list()
                else:
                    QMessageBox.critical(self, "Errore", "Eliminazione fallita. Controllare i log (es. è l'unico admin attivo?).")
            elif ok: # Username non corrispondente
                QMessageBox.warning(self, "Annullato", "Username non corrispondente. Eliminazione annullata.")
            # else: l'utente ha premuto annulla su QInputDialog

# Altri Widget per i Tab (da creare)
class InserimentoComuneWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, # parent come primo argomento dopo self
                 db_manager: Optional['CatastoDBManager'] = None, 
                 utente_attuale_info: Optional[Dict[str, Any]] = None):
        super().__init__(parent) # Passa il parent ricevuto
        
        # È buona norma verificare se db_manager è stato fornito, se è essenziale
        if db_manager is None:
            gui_logger.critical("InserimentoComuneWidget: db_manager non fornito all'inizializzazione!")
            # Qui potrebbe essere necessario disabilitare il widget o sollevare un errore
            # per evitare AttributeError più avanti se si tenta di usare self.db_manager.
            # Per ora, ci affidiamo al fatto che venga sempre passato correttamente.
        
        self.db_manager = db_manager 
        self.utente_attuale_info = utente_attuale_info
        
        self._initUI()
        self._carica_elenco_periodi() # Assumendo che _carica_elenco_periodi esista


    def _initUI(self):
        # ... (definizione di main_layout, form_group, form_layout_container, form_layout come prima) ...
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        form_group = QGroupBox("Dati del Nuovo Comune")
        form_layout_container = QVBoxLayout(form_group)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.nome_comune_edit = QLineEdit()
        self.provincia_edit = QLineEdit("SV") 
        self.provincia_edit.setMaxLength(2)
        self.regione_edit = QLineEdit() 
        self.periodo_id_spinbox = QSpinBox()
        self.periodo_id_spinbox.setMinimum(1)
        self.periodo_id_spinbox.setMaximum(99999)
        form_layout.addRow("Nome Comune (*):", self.nome_comune_edit)
        form_layout.addRow("Provincia (*):", self.provincia_edit)
        form_layout.addRow("Regione (*):", self.regione_edit)
        form_layout.addRow("Periodo ID (*):", self.periodo_id_spinbox)
        form_layout_container.addLayout(form_layout)
        main_layout.addWidget(form_group)

        # --- Sezione Riepilogo Periodi Storici ---
        periodi_riepilogo_group = QGroupBox("Riferimento Periodi Storici")
        periodi_riepilogo_layout = QVBoxLayout(periodi_riepilogo_group)
        periodi_riepilogo_layout.setSpacing(5)

        # Layout per pulsanti sopra la tabella dei periodi
        periodi_table_actions_layout = QHBoxLayout()
        self.btn_dettaglio_modifica_periodo = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogInfoView) ," Dettagli/Modifica Periodo")
        self.btn_dettaglio_modifica_periodo.setToolTip("Visualizza o modifica i dettagli del periodo storico selezionato")
        self.btn_dettaglio_modifica_periodo.clicked.connect(self._apri_dettaglio_modifica_periodo)
        self.btn_dettaglio_modifica_periodo.setEnabled(False) # Inizialmente disabilitato
        periodi_table_actions_layout.addWidget(self.btn_dettaglio_modifica_periodo)
        periodi_table_actions_layout.addStretch()
        btn_aggiorna_periodi = QPushButton(QApplication.style().standardIcon(QStyle.SP_BrowserReload), " Aggiorna Elenco")
        btn_aggiorna_periodi.clicked.connect(self._carica_elenco_periodi)
        periodi_table_actions_layout.addWidget(btn_aggiorna_periodi)
        periodi_riepilogo_layout.addLayout(periodi_table_actions_layout) # Aggiungi layout azioni sopra la tabella

        self.periodi_table = QTableWidget()
        self.periodi_table.setColumnCount(4) 
        self.periodi_table.setHorizontalHeaderLabels(["ID", "Nome Periodo", "Anno Inizio", "Anno Fine"])
        self.periodi_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.periodi_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.periodi_table.setSelectionMode(QTableWidget.SingleSelection)
        self.periodi_table.setAlternatingRowColors(True)
        self.periodi_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) 
        self.periodi_table.setMinimumHeight(120) 
        self.periodi_table.setMaximumHeight(250)
        self.periodi_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsante_dettaglio_periodo) # Connetti a nuovo metodo
        self.periodi_table.itemDoubleClicked.connect(self._apri_dettaglio_modifica_periodo_da_doppio_click) # Connetti doppio click

        periodi_riepilogo_layout.addWidget(self.periodi_table)
        main_layout.addWidget(periodi_riepilogo_group)
        
        # ... (linea e pulsanti Inserisci/Pulisci come prima) ...
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.submit_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton), " Inserisci Comune")
        self.submit_button.clicked.connect(self.inserisci_comune)
        self.clear_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogDiscardButton), " Pulisci Campi")
        self.clear_button.clicked.connect(self.pulisci_campi)
        button_layout.addStretch() 
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)
        main_layout.addStretch(1)


    def _aggiorna_stato_pulsante_dettaglio_periodo(self):
        """Abilita il pulsante Dettagli/Modifica Periodo se una riga è selezionata."""
        if hasattr(self, 'btn_dettaglio_modifica_periodo'): # Controllo di sicurezza
            self.btn_dettaglio_modifica_periodo.setEnabled(bool(self.periodi_table.selectedItems()))

    def _get_selected_periodo_id(self) -> Optional[int]:
        """Restituisce l'ID del periodo attualmente selezionato nella tabella dei periodi."""
        selected_items = self.periodi_table.selectedItems()
        if not selected_items:
            return None
        
        current_row = self.periodi_table.currentRow()
        if current_row < 0: return None
            
        id_item = self.periodi_table.item(current_row, 0) # Colonna ID
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def _apri_dettaglio_modifica_periodo_da_doppio_click(self, item: QTableWidgetItem):
        """Gestisce il doppio click sulla tabella dei periodi."""
        # Non serve controllare item se la chiamata proviene da un segnale valido di itemDoubleClicked
        self._apri_dettaglio_modifica_periodo()

    def _apri_dettaglio_modifica_periodo(self):
        """Apre il dialogo per visualizzare/modificare il periodo selezionato."""
        selected_periodo_id = self._get_selected_periodo_id()
        if selected_periodo_id is None:
            QMessageBox.information(self, "Nessuna Selezione", 
                                    "Selezionare un periodo dalla tabella per vederne/modificarne i dettagli.")
            return

        dialog = PeriodoStoricoDetailsDialog(self.db_manager, selected_periodo_id, self)
        if dialog.exec_() == QDialog.Accepted:
            # Se il dialogo è stato accettato (modifiche salvate), ricarica l'elenco dei periodi
            gui_logger.info(f"Dialogo dettagli/modifica periodo ID {selected_periodo_id} chiuso con successo. Aggiorno elenco periodi.")
            self._carica_elenco_periodi()
        else:
            gui_logger.info(f"Dialogo dettagli/modifica periodo ID {selected_periodo_id} annullato o chiuso.")

    # Mantieni _carica_elenco_periodi, pulisci_campi, inserisci_comune come sono stati definiti correttamente prima.
    # ...
    def _carica_elenco_periodi(self):
        self.periodi_table.setRowCount(0) 
        self.periodi_table.setSortingEnabled(False)
        try:
            gui_logger.info("Chiamata a db_manager.get_historical_periods()...") 
            periodi = self.db_manager.get_historical_periods()
            gui_logger.info(f"Elenco periodi ricevuto da DBManager (tipo: {type(periodi)}): {periodi if periodi is not None else 'None'}")
            if periodi: 
                gui_logger.info(f"Numero di periodi ricevuti: {len(periodi)}")
                self.periodi_table.setRowCount(len(periodi))
                for row_idx, periodo_data in enumerate(periodi):
                    col = 0
                    id_item = QTableWidgetItem(str(periodo_data.get('id', 'N/D')))
                    self.periodi_table.setItem(row_idx, col, id_item); col+=1
                    nome_item = QTableWidgetItem(periodo_data.get('nome', 'N/D'))
                    self.periodi_table.setItem(row_idx, col, nome_item); col+=1
                    anno_i_item = QTableWidgetItem(str(periodo_data.get('anno_inizio', 'N/D')))
                    self.periodi_table.setItem(row_idx, col, anno_i_item); col+=1
                    anno_f_item = QTableWidgetItem(str(periodo_data.get('anno_fine', 'N/D')))
                    self.periodi_table.setItem(row_idx, col, anno_f_item); col+=1
                self.periodi_table.resizeColumnsToContents()
            else: 
                gui_logger.warning("Nessun periodo storico restituito da db_manager.get_historical_periods() o la lista è vuota.")
                self.periodi_table.setRowCount(1)
                self.periodi_table.setItem(0,0, QTableWidgetItem("Nessun periodo storico trovato nel database."))
                self.periodi_table.setSpan(0, 0, 1, self.periodi_table.columnCount())
        except Exception as e:
            gui_logger.error(f"Errore imprevisto durante _carica_elenco_periodi: {e}", exc_info=True)
            QMessageBox.warning(self, "Errore Caricamento Periodi", f"Impossibile caricare l'elenco dei periodi:\n{type(e).__name__}: {e}")
            self.periodi_table.setRowCount(1)
            self.periodi_table.setItem(0,0, QTableWidgetItem("Errore nel caricamento dei periodi."))
            self.periodi_table.setSpan(0, 0, 1, self.periodi_table.columnCount())
        finally:
            self.periodi_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsante_dettaglio_periodo() # Aggiorna stato pulsante qui


    def pulisci_campi(self):
        self.nome_comune_edit.clear()
        self.provincia_edit.setText("SV")
        self.regione_edit.clear() 
        self.periodo_id_spinbox.setValue(self.periodo_id_spinbox.minimum()) 
        self.nome_comune_edit.setFocus()

    def inserisci_comune(self):
        nome_comune = self.nome_comune_edit.text().strip()
        provincia = self.provincia_edit.text().strip()
        regione = self.regione_edit.text().strip() 
        periodo_id_val = self.periodo_id_spinbox.value()
        if not nome_comune:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome del comune è obbligatorio.")
            self.nome_comune_edit.setFocus(); return
        if not provincia:
            QMessageBox.warning(self, "Dati Mancanti", "La provincia è obbligatoria (2 caratteri).")
            self.provincia_edit.setFocus(); return
        if not regione: 
            QMessageBox.warning(self, "Dati Mancanti", "La regione è obbligatoria.")
            self.regione_edit.setFocus(); return
        if periodo_id_val < self.periodo_id_spinbox.minimum():
            QMessageBox.warning(self, "Dati Mancanti", "L'ID del periodo è obbligatorio e deve essere un valore valido.")
            self.periodo_id_spinbox.setFocus(); return
        username_per_log = "utente_sconosciuto"
        if self.utente_attuale_info and isinstance(self.utente_attuale_info, dict):
            username_per_log = self.utente_attuale_info.get('username', 'utente_sconosciuto')
        elif isinstance(self.utente_attuale_info, str):
             username_per_log = self.utente_attuale_info
        gui_logger.debug(f"InserimentoComuneWidget: Invio al DBManager -> nome='{nome_comune}', prov='{provincia}', regione='{regione}', periodo_id='{periodo_id_val}', utente='{username_per_log}'")
        try:
            comune_id = self.db_manager.aggiungi_comune(
                nome_comune=nome_comune, provincia=provincia, regione=regione, 
                periodo_id=periodo_id_val, utente=username_per_log 
            )
            if comune_id is not None:
                QMessageBox.information(self, "Successo", f"Comune '{nome_comune}' inserito con ID: {comune_id}.")
                self.pulisci_campi()
                self._carica_elenco_periodi()
                main_window = self.window() 
                if isinstance(main_window, CatastoMainWindow):
                    if hasattr(main_window, 'consultazione_sub_tabs'):
                         for i in range(main_window.consultazione_sub_tabs.count()):
                            widget_in_tab = main_window.consultazione_sub_tabs.widget(i)
                            if isinstance(widget_in_tab, ElencoComuniWidget):
                                widget_in_tab.load_comuni_data()
                                gui_logger.info("Elenco comuni nel tab consultazione aggiornato.")
                                break
        except DBUniqueConstraintError as uve:
            gui_logger.warning(f"Unicità violata inserendo comune '{nome_comune}': {str(uve)}")
            QMessageBox.critical(self, "Errore di Unicità", str(uve))
        except DBDataError as dde:
            gui_logger.warning(f"Dati non validi per comune '{nome_comune}': {str(dde)}")
            QMessageBox.warning(self, "Dati Non Validi", str(dde))
        except DBMError as dbe: 
            gui_logger.error(f"Errore DB inserendo comune '{nome_comune}': {str(dbe)}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", str(dbe))
        except Exception as e:
            gui_logger.critical(f"Errore imprevisto inserendo comune '{nome_comune}': {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico", f"Errore imprevisto: {type(e).__name__}: {e}")


class AuditLogViewerWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Visualizzatore Log di Audit") # Titolo opzionale se usato come finestra separata

        self._init_ui()
        self._load_initial_data() # Caricheremo i dati all'avvio o su richiesta

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Gruppo Filtri ---
        filters_group = QGroupBox("Filtri di Ricerca Log")
        filters_form_layout = QFormLayout(filters_group) # Usiamo QFormLayout per etichette e campi allineati

        self.filter_table_name_edit = QLineEdit()
        filters_form_layout.addRow("Nome Tabella:", self.filter_table_name_edit)

        self.filter_operation_combo = QComboBox()
        self.filter_operation_combo.addItems(["Tutte", "INSERT (I)", "UPDATE (U)", "DELETE (D)"])
        filters_form_layout.addRow("Operazione:", self.filter_operation_combo)
        
        # Filtro per Utente Applicativo (ID)
        self.filter_app_user_id_edit = QLineEdit()
        self.filter_app_user_id_edit.setPlaceholderText("ID utente (opzionale)")
        filters_form_layout.addRow("ID Utente Applicativo:", self.filter_app_user_id_edit)

        # Filtro per ID Record
        self.filter_record_id_edit = QLineEdit()
        self.filter_record_id_edit.setPlaceholderText("ID record modificato (opzionale)")
        filters_form_layout.addRow("ID Record:", self.filter_record_id_edit)

        # Filtro per Data/Ora
        self.filter_start_datetime_edit = QDateTimeEdit(self)
        self.filter_start_datetime_edit.setDateTime(QDateTime.currentDateTime().addDays(-7)) # Default: ultima settimana
        self.filter_start_datetime_edit.setCalendarPopup(True)
        self.filter_start_datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        filters_form_layout.addRow("Da Data/Ora:", self.filter_start_datetime_edit)

        self.filter_end_datetime_edit = QDateTimeEdit(self)
        self.filter_end_datetime_edit.setDateTime(QDateTime.currentDateTime()) # Default: ora attuale
        self.filter_end_datetime_edit.setCalendarPopup(True)
        self.filter_end_datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        filters_form_layout.addRow("A Data/Ora:", self.filter_end_datetime_edit)
        
        self.filter_search_text_edit = QLineEdit()
        self.filter_search_text_edit.setPlaceholderText("Cerca in dati JSON (opzionale, può essere lento)")
        filters_form_layout.addRow("Testo in Dati JSON:", self.filter_search_text_edit)


        self.search_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton), "Applica Filtri / Cerca")
        self.search_button.clicked.connect(self._apply_filters_and_search)
        
        self.reset_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCancelButton), "Resetta Filtri") # O SP_TrashIcon
        self.reset_button.clicked.connect(self._reset_filters)

        buttons_filter_layout = QHBoxLayout()
        buttons_filter_layout.addWidget(self.search_button)
        buttons_filter_layout.addWidget(self.reset_button)
        filters_form_layout.addRow(buttons_filter_layout) # Aggiungi layout bottoni al form layout

        main_layout.addWidget(filters_group)

        # --- Tabella Risultati Log ---
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(9) # ID Log, Timestamp, Utente App, Sessione, Tabella, Operazione, Record ID, IP, Dettagli (per JSON)
        self.log_table.setHorizontalHeaderLabels([
            "ID Log", "Timestamp", "ID Utente App", "ID Sessione", "Tabella",
            "Operazione", "ID Record", "Indirizzo IP", "Modifiche?"
        ])
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.log_table.setSelectionMode(QTableWidget.SingleSelection)
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setStretchLastSection(True)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.setSortingEnabled(True) # Abilita sorting client-side (o implementa server-side)
        self.log_table.itemSelectionChanged.connect(self._display_log_details) # Per mostrare dati JSON
        main_layout.addWidget(self.log_table)

        # --- Area Dettagli JSON ---
        details_group = QGroupBox("Dettagli Modifica (JSON)")
        details_layout = QHBoxLayout(details_group) # Layout orizzontale per Dati Prima e Dati Dopo

        self.details_before_text = QTextEdit()
        self.details_before_text.setReadOnly(True)
        self.details_before_text.setPlaceholderText("Dati prima della modifica...")
        details_layout.addWidget(QLabel("Dati Prima:"))
        details_layout.addWidget(self.details_before_text)

        self.details_after_text = QTextEdit()
        self.details_after_text.setReadOnly(True)
        self.details_after_text.setPlaceholderText("Dati dopo la modifica...")
        details_layout.addWidget(QLabel("Dati Dopo:"))
        details_layout.addWidget(self.details_after_text)
        
        # Imposta stretch factors per dare più spazio ai QTextEdit rispetto alle QLabel
        details_layout.setStretchFactor(self.details_before_text, 1)
        details_layout.setStretchFactor(self.details_after_text, 1)
        details_layout.setStretchFactor(details_layout.itemAt(0).widget(), 0) # QLabel "Dati Prima:"
        details_layout.setStretchFactor(details_layout.itemAt(2).widget(), 0) # QLabel "Dati Dopo:"


        main_layout.addWidget(details_group)
        
        # TODO: Aggiungere controlli di paginazione ( QLabel per info pagina, QPushButton per Precedente/Successiva)
        # self.pagination_label = QLabel("Pagina 1 di X (Y risultati)")
        # self.prev_page_button = QPushButton("Precedente")
        # self.next_page_button = QPushButton("Successiva")
        # pagination_layout = QHBoxLayout()
        # ... aggiungere widget al pagination_layout e poi al main_layout ...

        self.setLayout(main_layout)

    def _apply_filters_and_search(self):
        # Qui recupereremo i valori dai campi di filtro
        filters = {
            "table_name": self.filter_table_name_edit.text().strip() or None,
            "operation_char": None,
            "app_user_id": self.filter_app_user_id_edit.text().strip() or None,
            "record_id": self.filter_record_id_edit.text().strip() or None,
            "start_datetime": self.filter_start_datetime_edit.dateTime().toPyDateTime(),
            "end_datetime": self.filter_end_datetime_edit.dateTime().toPyDateTime(),
            "search_text_json": self.filter_search_text_edit.text().strip() or None,
        }
        
        op_text = self.filter_operation_combo.currentText()
        if "INSERT" in op_text: filters["operation_char"] = "I"
        elif "UPDATE" in op_text: filters["operation_char"] = "U"
        elif "DELETE" in op_text: filters["operation_char"] = "D"

        # Converti app_user_id e record_id in interi se sono numerici, altrimenti None
        if filters["app_user_id"] and filters["app_user_id"].isdigit():
            filters["app_user_id"] = int(filters["app_user_id"])
        else:
            filters["app_user_id"] = None # O mostra un errore se si aspetta un numero

        if filters["record_id"] and filters["record_id"].isdigit():
            filters["record_id"] = int(filters["record_id"])
        else:
            filters["record_id"] = None

        self.current_filters = filters # Salva i filtri correnti per la paginazione
        self.current_page = 1
        self._fetch_and_display_logs()

    def _reset_filters(self):
        self.filter_table_name_edit.clear()
        self.filter_operation_combo.setCurrentIndex(0) # "Tutte"
        self.filter_app_user_id_edit.clear()
        self.filter_record_id_edit.clear()
        self.filter_start_datetime_edit.setDateTime(QDateTime.currentDateTime().addDays(-7))
        self.filter_end_datetime_edit.setDateTime(QDateTime.currentDateTime())
        self.filter_search_text_edit.clear()
        
        self.current_filters = None
        self.current_page = 1
        self._fetch_and_display_logs() # Ricarica con filtri resettati (o tutti i log recenti)


    def _fetch_and_display_logs(self, page_number: int = 1):
        # Questo metodo chiamerà db_manager.get_audit_logs(self.current_filters, page=page_number)
        # e popolerà self.log_table. Per ora, lo lasciamo come placeholder.
        self.log_table.setRowCount(0) # Pulisce la tabella
        self.details_before_text.clear()
        self.details_after_text.clear()
        
        # --- Logica di Test (da sostituire con chiamata DB reale) ---
        if not hasattr(self, 'db_manager') or not self.db_manager:
            QMessageBox.warning(self, "Errore", "DB Manager non disponibile.")
            return

        # Prepara i filtri per il db_manager.get_audit_logs (metodo da creare)
        filters_for_db = getattr(self, 'current_filters', {}) # Usa filtri correnti o dizionario vuoto
        if not filters_for_db: # Se filtri resettati, imposta un default ragionevole
             filters_for_db = {
                "start_datetime": QDateTime.currentDateTime().addDays(-7).toPyDateTime(),
                "end_datetime": QDateTime.currentDateTime().toPyDateTime()
             }


        try:
            # Assumiamo che db_manager.get_audit_logs() restituisca (lista_log, totale_record_filtrati)
            # Per ora, non implementiamo la paginazione completa qui, ma il metodo DB dovrebbe supportarla.
            logs, total_records = self.db_manager.get_audit_logs(
                filters=filters_for_db,
                page=page_number, # Da implementare la gestione della paginazione UI
                page_size=100    # Esempio di dimensione pagina
            )

            if logs:
                self.log_table.setRowCount(len(logs))
                for row_idx, log_entry in enumerate(logs):
                    col = 0
                    # ID Log
                    item_id = QTableWidgetItem(str(log_entry.get('id', '')))
                    item_id.setData(Qt.UserRole, log_entry) # Salva l'intero dict del log nell'item
                    self.log_table.setItem(row_idx, col, item_id); col+=1
                    # Timestamp
                    ts = log_entry.get('timestamp')
                    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "N/D"
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(ts_str)); col+=1
                    # ID Utente App
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(str(log_entry.get('app_user_id', 'N/D')))); col+=1
                    # ID Sessione (troncato per brevità)
                    session_id_full = log_entry.get('session_id', 'N/D')
                    session_id_display = (session_id_full[:8] + '...') if session_id_full and len(session_id_full) > 8 else session_id_full
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(session_id_display)); col+=1
                    # Tabella
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(log_entry.get('tabella', 'N/D'))); col+=1
                    # Operazione
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(log_entry.get('operazione', 'N/D'))); col+=1
                    # ID Record
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(str(log_entry.get('record_id', 'N/D')))); col+=1
                    # Indirizzo IP
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(log_entry.get('ip_address', 'N/D'))); col+=1
                    # Modifiche? (semplice indicatore se dati_prima o dati_dopo esistono)
                    has_changes = "Sì" if log_entry.get('dati_prima') or log_entry.get('dati_dopo') else "No"
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(has_changes)); col+=1

                self.log_table.resizeColumnsToContents() # Adatta larghezza colonne
                # TODO: Aggiorna self.pagination_label
            else:
                # TODO: Aggiorna self.pagination_label con "Nessun risultato"
                pass # Nessun log trovato

        except AttributeError as ae: # Se get_audit_logs non esiste in db_manager
            self.log_table.setRowCount(1)
            self.log_table.setItem(0,0, QTableWidgetItem(f"Errore: metodo get_audit_logs non trovato in DBManager ({ae})"))
            gui_logger.error(f"AuditLogViewer: db_manager non ha get_audit_logs: {ae}")
        except Exception as e:
            self.log_table.setRowCount(1)
            self.log_table.setItem(0,0, QTableWidgetItem(f"Errore durante il caricamento dei log: {e}"))
            gui_logger.error(f"AuditLogViewer: Errore caricamento log: {e}", exc_info=True)


    def _display_log_details(self):
        selected_items = self.log_table.selectedItems()
        if not selected_items:
            self.details_before_text.clear()
            self.details_after_text.clear()
            return

        # Prendiamo l'intero record del log memorizzato nel primo item della riga
        first_item_selected_row = self.log_table.item(selected_items[0].row(), 0)
        if not first_item_selected_row: return

        log_entry_data = first_item_selected_row.data(Qt.UserRole) # Recupera il dict del log
        if not log_entry_data or not isinstance(log_entry_data, dict):
            self.details_before_text.setText("Dati del log non disponibili o corrotti.")
            self.details_after_text.clear()
            return

        dati_prima = log_entry_data.get('dati_prima')
        dati_dopo = log_entry_data.get('dati_dopo')

        self.details_before_text.setText(json.dumps(dati_prima, indent=4, ensure_ascii=False) if dati_prima else "Nessun dato precedente.")
        self.details_after_text.setText(json.dumps(dati_dopo, indent=4, ensure_ascii=False) if dati_dopo else "Nessun dato successivo.")


    def _load_initial_data(self):
        # Carica i log più recenti all'avvio del widget
        self.current_filters = {
            "start_datetime": QDateTime.currentDateTime().addDays(-1).toPyDateTime(), # Default: ultime 24 ore
            "end_datetime": QDateTime.currentDateTime().toPyDateTime()
        }
        self.current_page = 1
        self._fetch_and_display_logs()

# ... (Fine della classe AuditLogViewerWidget) ...

# Poi, in CatastoMainWindow, nel metodo setup_tabs:
# Sostituisci la parte del placeholder per il tab "Sistema" con:
#
# self.audit_viewer_widget = AuditLogViewerWidget(self.db_manager, sistema_sub_tabs)
# sistema_sub_tabs.addTab(self.audit_viewer_widget, "Log di Audit")
# # ... (eventualmente aggiungi altri sotto-tab a sistema_sub_tabs per Backup, ecc.)
# self.tabs.addTab(sistema_sub_tabs, "Sistema")

class BackupRestoreWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Backup e Ripristino Database")

        # Processi per pg_dump e pg_restore
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_process_finished)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Sezione Backup ---
        backup_group = QGroupBox("Backup Database")
        backup_layout = QFormLayout(backup_group)

        self.backup_file_path_edit = QLineEdit()
        self.backup_file_path_edit.setPlaceholderText("Seleziona percorso e nome del file di backup...")
        self.backup_file_path_edit.setReadOnly(True)
        btn_browse_backup_path = QPushButton("Sfoglia...")
        btn_browse_backup_path.clicked.connect(self._browse_backup_file_save_path)
        backup_path_layout = QHBoxLayout()
        backup_path_layout.addWidget(self.backup_file_path_edit)
        backup_path_layout.addWidget(btn_browse_backup_path)
        backup_layout.addRow("File di Backup:", backup_path_layout)

        self.backup_format_combo = QComboBox()
        self.backup_format_combo.addItems([
            "Custom (compresso, per pg_restore - raccomandato)", # .dump o .backup
            "Plain SQL (testo semplice)" # .sql
        ])
        backup_layout.addRow("Formato Backup:", self.backup_format_combo)

        # Opzionale: percorso pg_dump se non nel PATH
        self.pg_dump_path_edit = QLineEdit()
        self.pg_dump_path_edit.setPlaceholderText("Es. C:\\Program Files\\PostgreSQL\\16\\bin\\pg_dump.exe (opzionale)")
        backup_layout.addRow("Percorso pg_dump (opz.C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe):", self.pg_dump_path_edit)


        self.backup_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton), "Esegui Backup")
        self.backup_button.clicked.connect(self._start_backup)
        backup_layout.addRow(self.backup_button)

        main_layout.addWidget(backup_group)

        # --- Sezione Ripristino ---
        restore_group = QGroupBox("Ripristino Database")
        restore_layout = QFormLayout(restore_group)

        self.restore_file_path_edit = QLineEdit()
        self.restore_file_path_edit.setPlaceholderText("Seleziona il file di backup da ripristinare...")
        self.restore_file_path_edit.setReadOnly(True)
        btn_browse_restore_path = QPushButton("Sfoglia...")
        btn_browse_restore_path.clicked.connect(self._browse_restore_file_open_path)
        restore_path_layout = QHBoxLayout()
        restore_path_layout.addWidget(self.restore_file_path_edit)
        restore_path_layout.addWidget(btn_browse_restore_path)
        restore_layout.addRow("File di Backup:", restore_path_layout)

        # Opzionale: percorso pg_restore/psql se non nel PATH
        self.pg_restore_path_edit = QLineEdit()
        self.pg_restore_path_edit.setPlaceholderText("Es. ...\\bin\\pg_restore.exe o ...\\bin\\psql.exe (opz.)")
        restore_layout.addRow("Percorso pg_restore/psql (opz.):", self.pg_restore_path_edit)

        self.restore_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton), "Esegui Ripristino")
        self.restore_button.clicked.connect(self._start_restore)
        restore_layout.addRow(self.restore_button)
        restore_layout.addRow(QLabel("<font color='red'><b>ATTENZIONE:</b> Il ripristino sovrascriverà i dati correnti nel database. Procedere con cautela.</font>"))


        main_layout.addWidget(restore_group)

        # --- Output e Progresso ---
        output_group = QGroupBox("Output Operazione")
        output_layout = QVBoxLayout(output_group)
        self.output_text_edit = QTextEdit()
        self.output_text_edit.setReadOnly(True)
        self.output_text_edit.setLineWrapMode(QTextEdit.NoWrap) # Per output comandi
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False) # Mostra solo durante l'operazione

        output_layout.addWidget(self.output_text_edit)
        output_layout.addWidget(self.progress_bar)
        main_layout.addWidget(output_group, 1) # Il 1 dà a questo widget più stretch factor

        self.setLayout(main_layout)

    def _browse_backup_file_save_path(self):
        # Ottieni il nome del database usando il nuovo metodo del db_manager
        current_dbname = self.db_manager.get_current_dbname() # Usa il nuovo metodo getter
        default_db_name = current_dbname if current_dbname else "catasto_storico" # Fallback se get_current_dbname restituisce None

        default_filename = f"{default_db_name}_backup_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}"
        
        if self.backup_format_combo.currentIndex() == 0: # Custom
            filter_str = "File di Backup PostgreSQL Custom (*.dump *.backup);;Tutti i file (*)"
            default_filename += ".dump"
        else: # Plain SQL
            filter_str = "File SQL (*.sql);;Tutti i file (*)"
            default_filename += ".sql"

        filePath, _ = QFileDialog.getSaveFileName(self, "Salva Backup Database", default_filename, filter_str)
        if filePath:
            self.backup_file_path_edit.setText(filePath)
    def _browse_restore_file_open_path(self):
        filter_str = "File di Backup PostgreSQL (*.dump *.backup *.sql);;File Custom (*.dump *.backup);;File SQL (*.sql);;Tutti i file (*)"
        filePath, _ = QFileDialog.getOpenFileName(self, "Seleziona File di Backup per Ripristino", "", filter_str)
        if filePath:
            self.restore_file_path_edit.setText(filePath)

    def _update_ui_for_process(self, is_running: bool):
        self.backup_button.setEnabled(not is_running)
        self.restore_button.setEnabled(not is_running)
        self.progress_bar.setVisible(is_running)
        if is_running:
            self.progress_bar.setRange(0,0) # Indicatore di attività (busy)
            self.output_text_edit.clear()
        else:
            self.progress_bar.setRange(0,1) # Resetta
            self.progress_bar.setValue(0)

    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode(errors='ignore')
        self.output_text_edit.append(data)

    def _handle_stderr(self):
        data = self.process.readAllStandardError().data().decode(errors='ignore')
        self.output_text_edit.append(f"<font color='red'>ERRORE: {data}</font>")

    # All'interno della classe BackupRestoreWidget in prova.py

    def _handle_process_finished(self, exitCode, exitStatus):
        is_restore = self.process.property("is_restore_operation")
        self.process.setProperty("is_restore_operation", False) # Resetta la proprietà

        self.output_text_edit.append(f"<hr>DEBUG: Processo terminato. ExitCode: {exitCode}, ExitStatus: {exitStatus}, Operazione Ripristino: {is_restore}<hr>")
        self._update_ui_for_process(False) # Riabilita UI (pulsanti, progress bar)

        operation_name = "Ripristino" if is_restore else "Backup"
        success_message_box_needed = False # <--- INIZIALIZZA QUI a False

        if exitStatus == QProcess.CrashExit:
            self.output_text_edit.append(f"<font color='red'><b>ERRORE CRITICO: Il processo di {operation_name.lower()} è terminato inaspettatamente (crash).</b></font>")
            QMessageBox.critical(self, f"Errore Processo {operation_name}", f"Il processo di {operation_name.lower()} è terminato inaspettatamente.")
        elif exitCode != 0:
            self.output_text_edit.append(f"<font color='red'><b>FALLITO: Il processo di {operation_name.lower()} è terminato con codice d'errore: {exitCode}.</b></font>")
            QMessageBox.warning(self, f"Operazione {operation_name} Fallita",
                                f"L'operazione di {operation_name.lower()} è fallita (codice: {exitCode}). Controllare l'output per i dettagli.")
        else: # exitCode == 0, il processo stesso ha terminato con successo
            self.output_text_edit.append(f"<font color='green'><b>Comando di {operation_name.lower()} terminato (exit code 0). Verificare l'output per errori specifici del tool.</b></font>")
            # Nota: pg_dump può scrivere errori su stderr e uscire comunque con 0.
            # Il messaggio di "successo" finale dipende se stderr era vuoto o conteneva errori.
            # Qui, per ora, assumiamo che exit code 0 sia "successo del processo".
            success_message_box_needed = True # Imposta a True se l'exit code è 0

        # --- Gestione Riconnessione Pool e Messaggio Finale ---
        if is_restore:
            self.output_text_edit.append("<i>Tentativo di ripristinare le connessioni dell'applicazione al database...</i>\n")
            QApplication.processEvents()
            if self.db_manager.reconnect_pool_if_needed(): # Decommenta quando implementato
                 self.output_text_edit.append("<i>Connessioni dell'applicazione al database ripristinate.</i>\n")
                 if success_message_box_needed:
                      QMessageBox.information(self, f"Operazione {operation_name} Completata",
                                             f"L'operazione di {operation_name.lower()} è stata completata e le connessioni sono state ripristinate.")
                      QMessageBox.information(self, "Verifica Dati",
                                             "Il ripristino sembra completato. Si consiglia di verificare i dati e, se necessario, riavviare l'applicazione.")
            else:
                 self.output_text_edit.append("<font color='red'><b>FALLITO: Impossibile ripristinare le connessioni al database. Si prega di RIAVVIARE L'APPLICAZIONE.</b></font>\n")
                 QMessageBox.critical(self, "Errore Riconnessione Critico", 
                                      "Impossibile ripristinare le connessioni al database dopo il ripristino.\n"
                                      "L'applicazione deve essere riavviata.")
            # Semplificazione temporanea senza gestione pool esplicita qui:
            if success_message_box_needed:
                QMessageBox.information(self, f"Operazione {operation_name} Completata",
                                        f"Il comando di {operation_name.lower()} è terminato. Controllare l'output per il risultato effettivo.\n"
                                        "Se il ripristino ha avuto successo, potrebbe essere necessario riavviare l'applicazione.")

        elif success_message_box_needed: # Per operazioni diverse dal ripristino (es. backup)
             QMessageBox.information(self, f"Operazione {operation_name} Completata",
                                    f"Il comando di {operation_name.lower()} è terminato (exit code 0).\n"
                                    "Controllare l'output per eventuali errori specifici dello strumento (es. pg_dump).")
    def _start_backup(self):
        backup_file = self.backup_file_path_edit.text()
        if not backup_file:
            QMessageBox.warning(self, "Percorso Mancante", "Selezionare un percorso e un nome file per il backup.")
            return

        if os.path.exists(backup_file):
            reply = QMessageBox.question(self, "Conferma Sovrascrittura",
                                         f"Il file '{os.path.basename(backup_file)}' esiste già.\nVuoi sovrascriverlo?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

         # --- Richiesta Password ---
        # Recupera utente e dbname tramite i metodi getter del db_manager
        db_user_for_prompt = self.db_manager.get_current_user() or "N/Utente"
        db_name_for_prompt = self.db_manager.get_current_dbname() or "N/Database"

        password, ok = QInputDialog.getText(self, "Autenticazione Database per Backup",
                                            f"Inserisci la password per l'utente '{db_user_for_prompt}' "
                                            f"sul database '{db_name_for_prompt}':",
                                            QLineEdit.Password)
        if not ok:
            self.output_text_edit.append("<i>Backup annullato dall'utente (dialogo password chiuso).</i>")
            return
        if not password.strip(): 
            QMessageBox.warning(self, "Password Mancante", "La password non può essere vuota.")
            self.output_text_edit.append("<font color='orange'>Backup fallito: password non fornita.</font>")
            self._update_ui_for_process(False) # Assicurati di resettare la UI
            return
        # --- Fine Richiesta Password ---

        self._update_ui_for_process(True)
        self.output_text_edit.clear() # Pulisci output precedente
        self.output_text_edit.append(f"Avvio backup su: {backup_file}...\n")

        command_parts = self.db_manager.get_backup_command_parts(
            backup_file_path=backup_file,
            pg_dump_executable_path_ui=self.pg_dump_path_edit.text().strip(),
            format_type="custom" if self.backup_format_combo.currentIndex() == 0 else "plain",
            include_blobs=False # O come hai deciso
        )

        if not command_parts:
            self.output_text_edit.append("<font color='red'><b>ERRORE: Impossibile costruire il comando di backup. Verificare il percorso di pg_dump e i log.</b></font>")
            self._update_ui_for_process(False)
            QMessageBox.critical(self, "Errore Comando", "Impossibile preparare il comando di backup. Controllare i log dell'applicazione.")
            return

        executable = command_parts[0]
        args = command_parts[1:]

        self.output_text_edit.append(f"Comando da eseguire: {executable} {' '.join(args)}\n")

        process_env = self.process.processEnvironment()
        self.output_text_edit.append(f"<i>Tentativo di impostare PGPASSWORD per l'utente '{db_user_for_prompt}'...</i>\n") # Usa la variabile
        try:
            process_env.insert("PGPASSWORD", password)
            self.process.setProcessEnvironment(process_env)
            self.output_text_edit.append("<i>PGPASSWORD impostata per questo processo.</i>\n")
        except Exception as e: 
            self.output_text_edit.append(f"<font color='red'><b>ERRORE nell'impostare PGPASSWORD: {e}</b></font>\n")
            self.output_text_edit.append("<font color='orange'>Il backup potrebbe fallire o rimanere bloccato.</font>\n")

        self.process.setProperty("is_restore_operation", False) # Assicura che sia False per il backup
        self.process.start(executable, args)

    # All'interno della classe BackupRestoreWidget in prova.py
# nel metodo _start_restore

    def _start_restore(self):
        restore_file = self.restore_file_path_edit.text()
        if not restore_file:
            QMessageBox.warning(self, "File Mancante", "Selezionare un file di backup da cui ripristinare.")
            return
        if not os.path.exists(restore_file):
            QMessageBox.critical(self, "Errore File", f"Il file di backup '{restore_file}' non è stato trovato.")
            return

        # --- AVVISI E CONFERME MULTIPLE ---
        # Recupera i dettagli del DB usando i metodi getter
        dbname_to_restore = self.db_manager.get_current_dbname() or "Database Sconosciuto"

        db_host_for_prompt = "N/Host" # Fallback
        if hasattr(self.db_manager, '_conn_params_dict') and self.db_manager._conn_params_dict:
             db_host_for_prompt = self.db_manager._conn_params_dict.get('host', 'N/Host')

        db_user_for_prompt = self.db_manager.get_current_user() or "Utente Sconosciuto"

        if dbname_to_restore == "Database Sconosciuto": # Controllo di sicurezza aggiuntivo
            QMessageBox.critical(self, "Errore Configurazione", "Nome del database di destinazione non recuperabile.")
            return

        reply = QMessageBox.warning(self, "Conferma Ripristino Critico",
                                     f"<b>ATTENZIONE ESTREMA!</b>\n\n"
                                     f"Stai per ripristinare il database dal file:\n'{os.path.basename(restore_file)}'\n"
                                     f"sul database di destinazione:\n<b>'{dbname_to_restore}'</b> "
                                     f"(Host: {db_host_for_prompt}, Utente DB: {db_user_for_prompt}).\n\n"
                                     "<b>Questa operazione SOVRASCRIVERÀ tutti i dati correnti nel database di destinazione e NON PUÒ ESSERE ANNULLATA.</b>\n\n"
                                     "Si raccomanda VIVAMENTE di aver effettuato un backup recente e verificato del database corrente prima di procedere.\n\n"
                                     "Sei assolutamente sicuro di voler continuare?",
                                     QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if reply == QMessageBox.Cancel:
            self.output_text_edit.append("<i>Ripristino annullato dall'utente (prima conferma).</i>")
            return

        text_confirm, ok = QInputDialog.getText(self, "Conferma Finale Ripristino Obbligatoria",
                                                f"Per confermare il ripristino che sovrascriverà PERMANENTEMENTE il database '{dbname_to_restore}',\n"
                                                f"digita il nome del database qui sotto (deve corrispondere esattamente):")
        if not ok:
            self.output_text_edit.append("<i>Ripristino annullato dall'utente (dialogo conferma nome DB chiuso).</i>")
            return
        if text_confirm.strip() != dbname_to_restore:
            QMessageBox.critical(self, "Ripristino Annullato",
                                 f"Il nome del database inserito ('{text_confirm.strip()}') non corrisponde a '{dbname_to_restore}'.\n"
                                 "Ripristino annullato per sicurezza.")
            self.output_text_edit.append("<font color='red'>Ripristino annullato: conferma nome database fallita.</font>")
            return
        # --- FINE AVVISI E CONFERME ---

        # --- Richiesta Password ---
        password, ok = QInputDialog.getText(self, "Autenticazione Database per Ripristino",
                                            f"Inserisci la password per l'utente '{db_user_for_prompt}' " 
                                            f"per il database '{dbname_to_restore}':",
                                            QLineEdit.Password)
        if not ok:
            self.output_text_edit.append("<i>Ripristino annullato (dialogo password chiuso).</i>")
            return
        if not password.strip():
            QMessageBox.warning(self, "Password Mancante", "La password non può essere vuota per il ripristino.")
            self.output_text_edit.append("<font color='orange'>Ripristino fallito: password non fornita.</font>")
            self._update_ui_for_process(False) 
            return
        # --- Fine Richiesta Password ---

        self._update_ui_for_process(True)
        self.output_text_edit.clear() 
        self.output_text_edit.append(f"Avvio ripristino del database '{dbname_to_restore}' da: {restore_file}...\n")
        self.output_text_edit.append("<font color='orange'><b>AVVISO: L'applicazione potrebbe non rispondere durante l'operazione di ripristino. Attendere il completamento.</b></font>\n")
        QApplication.processEvents() 

        # Logica per la disconnessione temporanea del pool (se decommentata e implementata)
        self.output_text_edit.append("<i>Tentativo di chiudere le connessioni attive dell'applicazione al database...</i>\n")
        QApplication.processEvents()
        if not self.db_manager.disconnect_pool_temporarily(): # CORRETTO
            QMessageBox.critical(self, "Errore Critico Ripristino",
                                 "Impossibile chiudere le connessioni esistenti al database prima del ripristino.\n"
                                 "L'operazione è stata annullata per sicurezza.")
            self.output_text_edit.append("<font color='red'><b>FALLITO: Impossibile chiudere le connessioni al database. Ripristino annullato.</b></font>")
            self._update_ui_for_process(False)
            return
        self.output_text_edit.append("<i>Connessioni dell'applicazione al database chiuse temporaneamente.</i>\n")
        QApplication.processEvents()

        command_parts = self.db_manager.get_restore_command_parts(
            backup_file_path=restore_file,
            pg_tool_executable_path_ui=self.pg_restore_path_edit.text().strip()
        )

        if not command_parts:
            self.output_text_edit.append("<font color='red'><b>ERRORE: Impossibile costruire il comando di ripristino. Controllare il percorso dell'eseguibile e i log.</b></font>")
            self._update_ui_for_process(False)
            # Tentativo di riconnettere il pool se la disconnessione era avvenuta
            self.output_text_edit.append("<i>Tentativo di ripristinare le connessioni dell'applicazione (dopo fallimento preparazione comando)...</i>")
            if not self.db_manager.reconnect_pool_if_needed(): # CORRETTO
                 self.output_text_edit.append("<font color='red'><b>FALLITO riconnessione pool. Riavviare l'app.</b></font>")
            else:
                 self.output_text_edit.append("<i>Connessioni applicazione ripristinate.</i>")
            QMessageBox.critical(self, "Errore Comando", "Impossibile preparare il comando di ripristino.")
            return

        executable = command_parts[0]
        args = command_parts[1:]
        self.output_text_edit.append(f"Comando da eseguire: {executable} {' '.join(args)}\n")

        process_env = self.process.processEnvironment()
        self.output_text_edit.append(f"<i>Tentativo di impostare PGPASSWORD per l'utente '{db_user_for_prompt}'...</i>\n")
        try:
            process_env.insert("PGPASSWORD", password)
            self.process.setProcessEnvironment(process_env)
            self.output_text_edit.append("<i>PGPASSWORD impostata per questo processo.</i>\n")
        except Exception as e: 
            self.output_text_edit.append(f"<font color='red'><b>ERRORE nell'impostare PGPASSWORD: {e}</b></font>\n")

        self.process.setProperty("is_restore_operation", True)
        self.process.start(executable, args)


class RicercaAvanzataImmobiliWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_comune_id: Optional[int] = None
        self.selected_localita_id: Optional[int] = None

        main_layout = QVBoxLayout(self)

        criteria_group = QGroupBox("Criteri di Ricerca Avanzata Immobili")
        criteria_layout = QGridLayout(criteria_group)

        # Riga 0: Comune
        criteria_layout.addWidget(QLabel("Comune:"), 0, 0)
        self.comune_display_label = QLabel("Qualsiasi comune")
        criteria_layout.addWidget(self.comune_display_label, 0, 1)
        self.btn_seleziona_comune = QPushButton("Seleziona...")
        self.btn_seleziona_comune.clicked.connect(self._seleziona_comune_per_ricerca)
        criteria_layout.addWidget(self.btn_seleziona_comune, 0, 2)
        self.btn_reset_comune = QPushButton("Reset")
        self.btn_reset_comune.clicked.connect(self._reset_comune_ricerca)
        criteria_layout.addWidget(self.btn_reset_comune, 0, 3)

        # Riga 1: Località
        criteria_layout.addWidget(QLabel("Località:"), 1, 0)
        self.localita_display_label = QLabel("Qualsiasi località")
        criteria_layout.addWidget(self.localita_display_label, 1, 1)
        self.btn_seleziona_localita = QPushButton("Seleziona...")
        self.btn_seleziona_localita.clicked.connect(self._seleziona_localita_per_ricerca)
        self.btn_seleziona_localita.setEnabled(False)
        criteria_layout.addWidget(self.btn_seleziona_localita, 1, 2)
        self.btn_reset_localita = QPushButton("Reset")
        self.btn_reset_localita.clicked.connect(self._reset_localita_ricerca)
        criteria_layout.addWidget(self.btn_reset_localita, 1, 3)

        # Riga 2: Natura e Classificazione
        criteria_layout.addWidget(QLabel("Natura Immobile:"), 2, 0)
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Es. Casa, Terreno (lascia vuoto per qualsiasi)")
        criteria_layout.addWidget(self.natura_edit, 2, 1, 1, 3)

        criteria_layout.addWidget(QLabel("Classificazione:"), 3, 0)
        self.classificazione_edit = QLineEdit()
        self.classificazione_edit.setPlaceholderText("Es. Abitazione civile, Oliveto (lascia vuoto per qualsiasi)")
        criteria_layout.addWidget(self.classificazione_edit, 3, 1, 1, 3)
        
        # Riga 4: Consistenza (come testo per ricerca parziale)
        criteria_layout.addWidget(QLabel("Testo Consistenza:"), 4, 0)
        self.consistenza_search_edit = QLineEdit()
        self.consistenza_search_edit.setPlaceholderText("Es. 120, are, vani (ricerca parziale)")
        criteria_layout.addWidget(self.consistenza_search_edit, 4, 1, 1, 3)

        # Riga 5: Numero Piani
        criteria_layout.addWidget(QLabel("Piani Min:"), 5, 0)
        self.piani_min_spinbox = QSpinBox()
        self.piani_min_spinbox.setMinimum(0); self.piani_min_spinbox.setValue(0)
        criteria_layout.addWidget(self.piani_min_spinbox, 5, 1)
        criteria_layout.addWidget(QLabel("Piani Max:"), 5, 2)
        self.piani_max_spinbox = QSpinBox()
        self.piani_max_spinbox.setMinimum(0); self.piani_max_spinbox.setMaximum(99); self.piani_max_spinbox.setValue(0)
        self.piani_max_spinbox.setSpecialValueText("Qualsiasi")
        criteria_layout.addWidget(self.piani_max_spinbox, 5, 3)

        # Riga 6: Numero Vani
        criteria_layout.addWidget(QLabel("Vani Min:"), 6, 0)
        self.vani_min_spinbox = QSpinBox()
        self.vani_min_spinbox.setMinimum(0); self.vani_min_spinbox.setValue(0)
        criteria_layout.addWidget(self.vani_min_spinbox, 6, 1)
        criteria_layout.addWidget(QLabel("Vani Max:"), 6, 2)
        self.vani_max_spinbox = QSpinBox()
        self.vani_max_spinbox.setMinimum(0); self.vani_max_spinbox.setMaximum(999); self.vani_max_spinbox.setValue(0)
        self.vani_max_spinbox.setSpecialValueText("Qualsiasi")
        criteria_layout.addWidget(self.vani_max_spinbox, 6, 3)
        
        # Riga 7: Nome Possessore (NUOVO CAMPO)
        criteria_layout.addWidget(QLabel("Nome Possessore:"), 7, 0)
        self.nome_possessore_edit = QLineEdit()
        self.nome_possessore_edit.setPlaceholderText("Ricerca parziale nome possessore (lascia vuoto per qualsiasi)")
        criteria_layout.addWidget(self.nome_possessore_edit, 7, 1, 1, 3)

        main_layout.addWidget(criteria_group)

        self.btn_esegui_ricerca_immobili = QPushButton("Esegui Ricerca Immobili")
        self.btn_esegui_ricerca_immobili.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.btn_esegui_ricerca_immobili.clicked.connect(self._esegui_ricerca_effettiva)
        main_layout.addWidget(self.btn_esegui_ricerca_immobili)

        results_group = QGroupBox("Risultati Ricerca")
        results_layout = QVBoxLayout(results_group)
        self.risultati_immobili_table = QTableWidget()
        # Colonne basate sulla funzione SQL cerca_immobili_avanzato
        self.risultati_immobili_table.setColumnCount(10)
        self.risultati_immobili_table.setHorizontalHeaderLabels([
            "ID Imm.", "Part. N.", "Comune", "Località", "Natura", 
            "Class.", "Consist.", "Piani", "Vani", "Possessori"
        ])
        self.risultati_immobili_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.risultati_immobili_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.risultati_immobili_table.setAlternatingRowColors(True)
        self.risultati_immobili_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents) # ResizeToContents
        self.risultati_immobili_table.horizontalHeader().setStretchLastSection(True) # Ultima colonna stretch
        self.risultati_immobili_table.setSortingEnabled(True)
        results_layout.addWidget(self.risultati_immobili_table)
        main_layout.addWidget(results_group)

        self.setLayout(main_layout)

    def _seleziona_comune_per_ricerca(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_comune_id:
            self.selected_comune_id = dialog.selected_comune_id
            self.comune_display_label.setText(f"{dialog.selected_comune_name} (ID: {self.selected_comune_id})")
            self.btn_seleziona_localita.setEnabled(True)
            self._reset_localita_ricerca()
        elif not self.selected_comune_id:
            self.comune_display_label.setText("Qualsiasi comune")
            self.btn_seleziona_localita.setEnabled(False)

    def _reset_comune_ricerca(self):
        self.selected_comune_id = None
        self.comune_display_label.setText("Qualsiasi comune")
        self.btn_seleziona_localita.setEnabled(False)
        self._reset_localita_ricerca()

    def _seleziona_localita_per_ricerca(self):
        if not self.selected_comune_id:
            QMessageBox.warning(self, "Comune Mancante", "Seleziona prima un comune per filtrare le località.")
            return
        
        # Apre LocalitaSelectionDialog in MODALITÀ SELEZIONE
        dialog = LocalitaSelectionDialog(self.db_manager, self.selected_comune_id, self, 
                                         selection_mode=True) 
        
        if dialog.exec_() == QDialog.Accepted: # Se l'utente ha premuto "Seleziona" nel dialogo
            if dialog.selected_localita_id is not None and dialog.selected_localita_name is not None:
                self.selected_localita_id = dialog.selected_localita_id
                self.localita_display_label.setText(f"{dialog.selected_localita_name} (ID: {self.selected_localita_id})")
                gui_logger.info(f"RicercaAvanzataImmobili: Località selezionata ID: {self.selected_localita_id}, Nome: {dialog.selected_localita_name}")
            else:
                # Questo caso è improbabile se _conferma_selezione funziona, ma per sicurezza
                gui_logger.warning("RicercaAvanzataImmobili: LocalitaSelectionDialog accettato ma nessun ID/nome località valido è stato restituito.")
                # Potrebbe essere utile resettare qui, o lasciare la selezione precedente.
                # self._reset_localita_ricerca() 
        # else: # Dialogo annullato (premuto "Annulla" o chiuso)
            # Non fare nulla, la selezione precedente (o nessuna selezione) rimane.
            # Non è necessario chiamare self._reset_localita_ricerca() a meno che non sia il comportamento desiderato.
            gui_logger.info("Selezione località annullata o dialogo chiuso.")


    def _reset_localita_ricerca(self):
        self.selected_localita_id = None
        self.localita_display_label.setText("Qualsiasi località")

    def _esegui_ricerca_effettiva(self):
        p_comune_id = self.selected_comune_id
        p_localita_id = self.selected_localita_id
        p_natura = self.natura_edit.text().strip() or None
        p_classificazione = self.classificazione_edit.text().strip() or None
        p_consistenza_search = self.consistenza_search_edit.text().strip() or None # Campo unico per ricerca testuale consistenza

        p_piani_min = self.piani_min_spinbox.value() if self.piani_min_spinbox.value() > 0 else None
        p_piani_max = self.piani_max_spinbox.value() if self.piani_max_spinbox.value() != 0 else None # 0 è speciale "Qualsiasi"

        p_vani_min = self.vani_min_spinbox.value() if self.vani_min_spinbox.value() > 0 else None
        p_vani_max = self.vani_max_spinbox.value() if self.vani_max_spinbox.value() != 0 else None

        p_nome_possessore = self.nome_possessore_edit.text().strip() or None
        
        # --- STAMPE DI DEBUG DA AGGIUNGERE/DECOMMENTARE ---
        print("-" * 30)
        print("DEBUG GUI: Parametri inviati a ricerca_avanzata_immobili_gui:")
        print(f"  comune_id: {p_comune_id} (tipo: {type(p_comune_id)})")
        print(f"  localita_id: {p_localita_id} (tipo: {type(p_localita_id)})")
        print(f"  natura_search: '{p_natura}' (tipo: {type(p_natura)})")
        print(f"  classificazione_search: '{p_classificazione}' (tipo: {type(p_classificazione)})")
        print(f"  consistenza_search: '{p_consistenza_search}' (tipo: {type(p_consistenza_search)})")
        print(f"  piani_min: {p_piani_min} (tipo: {type(p_piani_min)})")
        print(f"  piani_max: {p_piani_max} (tipo: {type(p_piani_max)})")
        print(f"  vani_min: {p_vani_min} (tipo: {type(p_vani_min)})")
        print(f"  vani_max: {p_vani_max} (tipo: {type(p_vani_max)})")
        print(f"  nome_possessore_search: '{p_nome_possessore}' (tipo: {type(p_nome_possessore)})")
        print("-" * 30)
        # --- FINE STAMPE DI DEBUG ---

        try:
            immobili_trovati = self.db_manager.ricerca_avanzata_immobili_gui(
                comune_id=p_comune_id,
                localita_id=p_localita_id,
                natura_search=p_natura,
                classificazione_search=p_classificazione,
                consistenza_search=p_consistenza_search,
                piani_min=p_piani_min,
                piani_max=p_piani_max,
                vani_min=p_vani_min,
                vani_max=p_vani_max,
                nome_possessore_search=p_nome_possessore,
                data_inizio_possesso_search=None, # Non ancora in GUI
                data_fine_possesso_search=None    # Non ancora in GUI
            )

            self.risultati_immobili_table.setRowCount(0)
            if immobili_trovati:
                self.risultati_immobili_table.setRowCount(len(immobili_trovati))
                for row_idx, immobile in enumerate(immobili_trovati):
                    col = 0
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(str(immobile.get('id_immobile', '')))); col+=1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(str(immobile.get('numero_partita', '')))); col+=1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(immobile.get('comune_nome', ''))); col+=1
                    localita_display = f"{immobile.get('localita_nome', '')}"
                    if immobile.get('civico'):
                        localita_display += f", {immobile.get('civico')}"
                    if immobile.get('localita_tipo'):
                        localita_display += f" ({immobile.get('localita_tipo')})"
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(localita_display.strip())); col+=1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(immobile.get('natura', ''))); col+=1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(immobile.get('classificazione', ''))); col+=1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(immobile.get('consistenza', ''))); col+=1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(str(immobile.get('numero_piani', '')) if immobile.get('numero_piani') is not None else '')); col+=1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(str(immobile.get('numero_vani', '')) if immobile.get('numero_vani') is not None else '')); col+=1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(immobile.get('possessori_attuali', ''))); col+=1 # Campo dalla funzione SQL
                
                # self.risultati_immobili_table.resizeColumnsToContents() # Potrebbe essere lento con molti dati
                QMessageBox.information(self, "Ricerca Completata", f"Trovati {len(immobili_trovati)} immobili.")
            else:
                QMessageBox.information(self, "Ricerca Completata", "Nessun immobile trovato con i criteri specificati.")
        except AttributeError as ae:
             gui_logger.error(f"Metodo di ricerca immobili non trovato nel db_manager: {ae}", exc_info=True)
             QMessageBox.critical(self, "Errore Interno", f"Funzionalità di ricerca non implementata correttamente nel gestore DB: {ae}")
        except Exception as e:
            gui_logger.error(f"Errore durante la ricerca avanzata immobili: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Ricerca", f"Si è verificato un errore imprevisto: {e}")

class ElencoComuniWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        layout = QVBoxLayout(self)
        
        comuni_group = QGroupBox("Elenco Comuni Registrati")
        comuni_layout = QVBoxLayout(comuni_group)
        
        # ... (filter_comuni_edit e comuni_table come prima) ...
        self.filter_comuni_edit = QLineEdit()
        self.filter_comuni_edit.setPlaceholderText("Filtra per nome, provincia...")
        self.filter_comuni_edit.textChanged.connect(self.apply_filter)
        comuni_layout.addWidget(self.filter_comuni_edit)

        self.comuni_table = QTableWidget()
        self.comuni_table.setColumnCount(7) 
        self.comuni_table.setHorizontalHeaderLabels([
            "ID", "Nome Comune", "Cod. Catastale", "Provincia", 
            "Data Istituzione", "Data Soppressione", "Note"
        ])
        self.comuni_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.comuni_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.comuni_table.setAlternatingRowColors(True)
        self.comuni_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.comuni_table.setSortingEnabled(True)
        self.comuni_table.itemDoubleClicked.connect(self.mostra_partite_del_comune)
        comuni_layout.addWidget(self.comuni_table)

        # === NUOVI PULSANTI PER AZIONI SUL COMUNE SELEZIONATO ===
        action_buttons_layout = QHBoxLayout()
        self.btn_mostra_partite = QPushButton("Mostra Partite del Comune")
        self.btn_mostra_partite.clicked.connect(self.azione_mostra_partite)
        action_buttons_layout.addWidget(self.btn_mostra_partite)

        self.btn_mostra_possessori = QPushButton("Mostra Possessori del Comune") # NUOVO
        self.btn_mostra_possessori.clicked.connect(self.azione_mostra_possessori) # NUOVO
        action_buttons_layout.addWidget(self.btn_mostra_possessori) # NUOVO

         # === VERIFICA QUESTA SEZIONE ===
        self.btn_mostra_localita = QPushButton("Mostra Località del comune") # 1. Creazione del pulsante
        self.btn_mostra_localita.setToolTip("Mostra le località del comune selezionato")
        self.btn_mostra_localita.clicked.connect(self.azione_mostra_localita) # 2. Connessione al metodo
        action_buttons_layout.addWidget(self.btn_mostra_localita) # 3. Aggiunta al layout dei pulsanti
        # ===============================
        action_buttons_layout.addStretch()
        comuni_layout.addLayout(action_buttons_layout)
        # =======================================================
        
        layout.addWidget(comuni_group)
        self.setLayout(layout)
        
        self.load_comuni_data()

    def load_comuni_data(self):
        """Carica i dati di tutti i comuni nella tabella."""
        self.comuni_table.setRowCount(0) # Pulisce la tabella
        self.comuni_table.setSortingEnabled(False) # Disabilita sorting durante il caricamento
        
        try:
            # Assumiamo che db_manager.get_all_comuni_details() esista e restituisca tutti i campi.
            # Se non esiste, dobbiamo crearlo o adattare un metodo esistente.
            # get_comuni() potrebbe non bastare se non restituisce tutti i dettagli.
            # Per ora, creiamo un ipotetico get_all_comuni_details basato sullo schema.
            
            # Metodo ipotetico in CatastoDBManager:
            # def get_all_comuni_details(self) -> List[Dict[str, Any]]:
            #     query = "SELECT comune_id AS id, nome_comune, codice_catastale, provincia, data_istituzione, data_soppressione, note FROM catasto.comuni ORDER BY nome_comune;"
            #     if self.execute_query(query):
            #         return self.fetchall()
            #     return []

            comuni_list = self.db_manager.get_all_comuni_details() # Assicurati che questo metodo esista e funzioni!
            
            if comuni_list:
                self.comuni_table.setRowCount(len(comuni_list))
                for row_idx, comune in enumerate(comuni_list):
                    col = 0
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(str(comune.get('id', '')))); col+=1
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(comune.get('nome_comune', ''))); col+=1
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(comune.get('codice_catastale', ''))); col+=1
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(comune.get('provincia', ''))); col+=1
                    
                    data_ist = comune.get('data_istituzione')
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(str(data_ist) if data_ist else '')); col+=1
                    
                    data_soppr = comune.get('data_soppressione')
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(str(data_soppr) if data_soppr else '')); col+=1
                    
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(comune.get('note', ''))); col+=1
                
                self.comuni_table.resizeColumnsToContents()
            else:
                gui_logger.info("Nessun comune trovato nel database.")
                
        except AttributeError as ae: # Se get_all_comuni_details non esiste
            gui_logger.error(f"Attributo mancante nel db_manager: {ae}. Assicurati che 'get_all_comuni_details' esista.")
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Funzione dati comuni non trovata: {ae}")
        except Exception as e:
            gui_logger.error(f"Errore durante il caricamento dei comuni: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
        finally:
            self.comuni_table.setSortingEnabled(True) # Riabilita sorting

    def apply_filter(self):
        """Filtra le righe della tabella in base al testo inserito."""
        filter_text = self.filter_comuni_edit.text().strip().lower()
        for row in range(self.comuni_table.rowCount()):
            row_visible = False
            if not filter_text: # Se il filtro è vuoto, mostra tutte le righe
                row_visible = True
            else:
                for col in range(self.comuni_table.columnCount()):
                    item = self.comuni_table.item(row, col)
                    if item and filter_text in item.text().lower():
                        row_visible = True
                        break
            self.comuni_table.setRowHidden(row, not row_visible)
            
    def _get_selected_comune_info(self) -> Optional[Tuple[int, str]]:
        """Helper per ottenere ID e nome del comune correntemente selezionato nella tabella."""
        selected_items = self.comuni_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")
            return None
        
        row = self.comuni_table.currentRow() # selectedItems può dare più item se la selezione non è per riga
                                           # currentRow è più sicuro per single row selection
        if row < 0: # Nessuna riga effettivamente selezionata
             QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")
             return None

        try:
            comune_id_item = self.comuni_table.item(row, 0) # Colonna ID
            nome_comune_item = self.comuni_table.item(row, 1) # Colonna Nome Comune
            
            if comune_id_item and nome_comune_item:
                comune_id = int(comune_id_item.text())
                nome_comune = nome_comune_item.text()
                return comune_id, nome_comune
            else:
                QMessageBox.warning(self, "Errore Selezione", "Impossibile recuperare ID o nome del comune dalla riga.")
                return None
        except ValueError:
            QMessageBox.warning(self, "Errore Dati", "L'ID del comune non è un numero valido.")
            return None
        except Exception as e:
            gui_logger.error(f"Errore in _get_selected_comune_info: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore", f"Si è verificato un errore imprevisto: {e}")
            return None

    def mostra_partite_del_comune(self, item: QTableWidgetItem): # Questo è per il doppio click
        """Apre un dialogo con le partite del comune selezionato tramite doppio click."""
        # Questa funzione ora può usare l'helper se item è valido,
        # o mantenere la sua logica se item è il modo primario per ottenere la riga.
        if not item: return
        row = item.row()
        # ... (resto della logica di mostra_partite_del_comune come prima, usando 'row' per prendere ID e nome)
        try:
            comune_id_item = self.comuni_table.item(row, 0)
            nome_comune_item = self.comuni_table.item(row, 1)
            if comune_id_item and nome_comune_item:
                comune_id = int(comune_id_item.text())
                nome_comune = nome_comune_item.text()
                dialog = PartiteComuneDialog(self.db_manager, comune_id, nome_comune, self)
                dialog.exec_()
        except ValueError: QMessageBox.warning(self, "Errore Dati", "L'ID del comune non è un numero valido.")
        except Exception as e: gui_logger.error(f"Errore in mostra_partite_del_comune: {e}", exc_info=True); QMessageBox.critical(self, "Errore", f"Errore: {e}")


    def azione_mostra_partite(self):
        """Azione per il pulsante 'Mostra Partite del Comune'."""
        selected_info = self._get_selected_comune_info()
        if selected_info:
            comune_id, nome_comune = selected_info
            dialog = PartiteComuneDialog(self.db_manager, comune_id, nome_comune, self)
            dialog.exec_()

    def azione_mostra_possessori(self): # NUOVO METODO
        """Azione per il pulsante 'Mostra Possessori del Comune'."""
        selected_info = self._get_selected_comune_info()
        if selected_info:
            comune_id, nome_comune = selected_info
            dialog = PossessoriComuneDialog(self.db_manager, comune_id, nome_comune, self)
            dialog.exec_()
            
    def azione_mostra_localita(self):
        """Azione per il pulsante 'Mostra Località del Comune'.
        Usa la LocalitaSelectionDialog esistente per visualizzazione."""
        selected_info = self._get_selected_comune_info()
        if selected_info:
            comune_id, nome_comune = selected_info

            # Usa la tua classe LocalitaSelectionDialog esistente
            dialog = LocalitaSelectionDialog(self.db_manager, comune_id, self) # Passa 'self' come parent

            # Opzionale: personalizza il titolo se vuoi che sia diverso da "Seleziona Località"
            # quando viene aperta solo per consultazione.
            dialog.setWindowTitle(f"Località del Comune di {nome_comune} (ID: {comune_id})")

            # .exec_() aprirà il dialogo in modo modale.
            # L'utente potrà vedere le località nel tab "Seleziona Esistente".
            # Non ci interessa il valore restituito (selected_localita_id) in questo contesto.
            dialog.exec_()     
# ... (altre importazioni e classi definite prima, come LoginDialog, CreateUserDialog, vari Widget dei tab, ecc.)
# ASSICURARSI CHE TUTTE LE CLASSI WIDGET DEI TAB (ElencoComuniWidget, RicercaPartiteWidget, ecc.)
# SIANO DEFINITE PRIMA DI CatastoMainWindow

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

    def perform_initial_setup(self, db_manager: CatastoDBManager, user_id: int, user_info: Dict, session_id: str):
        gui_logger.info(">>> CatastoMainWindow: Inizio perform_initial_setup")
        self.db_manager = db_manager
        self.logged_in_user_id = user_id
        self.logged_in_user_info = user_info
        self.current_session_id = session_id

        # --- Aggiornamento etichetta stato DB ---
        db_name_to_display = "ERRORE_NOME_DB" # Default se qualcosa va storto nel recupero
        connection_seems_ok = False

        if self.db_manager and self.db_manager.pool: # Il pool è il nostro indicatore principale ora
            gui_logger.info("DEBUG perform_initial_setup: db_manager e pool esistono.")
            if hasattr(self.db_manager, '_conn_params_dict') and self.db_manager._conn_params_dict:
                db_name_to_display = self.db_manager._conn_params_dict.get('dbname', 'N/D')
                gui_logger.info(f"DEBUG perform_initial_setup: db_name recuperato: {db_name_to_display}")
            else:
                gui_logger.warning("DEBUG perform_initial_setup: db_manager non ha _conn_params_dict o è vuoto.")
            
            # Dato che run_gui_app ha già testato la connessione al pool con successo,
            # possiamo considerare la connessione "attiva" a questo punto.
            connection_seems_ok = True 
        else:
            gui_logger.error("DEBUG perform_initial_setup: db_manager o db_manager.pool NON esistono!")
            db_name_to_display = "Gestore DB non inizializzato"

        if connection_seems_ok:
            new_label_text = f"Database: Connesso ({db_name_to_display})"
            self.db_status_label.setText(new_label_text)
            gui_logger.info(f"DEBUG perform_initial_setup: db_status_label IMPOSTATO A: '{new_label_text}'")
        else:
            new_label_text = f"Database: NON CONNESSO ({db_name_to_display})"
            self.db_status_label.setText(new_label_text)
            gui_logger.warning(f"DEBUG perform_initial_setup: db_status_label IMPOSTATO A: '{new_label_text}'")
        # --- Fine aggiornamento etichetta stato DB ---

        # Aggiornamento etichetta utente (come prima)
        user_display = self.logged_in_user_info.get('nome_completo') or self.logged_in_user_info.get('username', 'N/D')
        ruolo_display = self.logged_in_user_info.get('ruolo', 'N/D')
        self.user_status_label.setText(f"Utente: {user_display} (ID: {self.logged_in_user_id}, Ruolo: {ruolo_display})")
        self.logout_button.setEnabled(True)

        self.statusBar().showMessage(f"Login come {user_display} effettuato con successo.")
        
        gui_logger.info(">>> CatastoMainWindow: Chiamata a setup_tabs")
        self.setup_tabs()
        gui_logger.info(">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        self.update_ui_based_on_role()

        gui_logger.info(">>> CatastoMainWindow: Chiamata a self.show()")
        self.show()
        gui_logger.info(">>> CatastoMainWindow: self.show() completato. Fine perform_initial_setup")

    # All'interno della classe CatastoMainWindow in prova.py
    def setup_tabs(self):
        if not self.db_manager:
            gui_logger.error("Tentativo di configurare i tab senza un db_manager.")
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
        self.inserimento_sub_tabs.addTab(RegistrazioneProprietaWidget(self.db_manager, self.inserimento_sub_tabs), "Registra Proprietà")
        self.inserimento_sub_tabs.addTab(OperazioniPartitaWidget(self.db_manager, self.inserimento_sub_tabs), "Operazioni su Partita")
       
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


        # Qui potresti aggiungere altri widget per Manutenzione ecc. come altri sotto-tab
        # Esempio:
        # manutenzione_widget = ManutenzioneWidget(self.db_manager, sistema_sub_tabs) # Dovrai creare ManutenzioneWidget
        # sistema_sub_tabs.addTab(manutenzione_widget, "Manutenzione DB")

        self.tabs.addTab(sistema_sub_tabs, "Sistema")

        # La chiamata a self.update_ui_based_on_role() avverrà dopo in perform_initial_setup,
        # quindi il pulsante self.btn_nuovo_comune_nel_tab e i tab verranno abilitati/disabilitati correttamente.

    def update_ui_based_on_role(self):
        if not self.logged_in_user_info:
            for i in range(self.tabs.count()):
                self.tabs.setTabEnabled(i, False)
            # if hasattr(self, 'nuovo_comune_action'): # Rimuovi se non usi più il menu
            #     self.nuovo_comune_action.setEnabled(False)
            if hasattr(self, 'btn_nuovo_comune_nel_tab'): # Nuovo pulsante
                self.btn_nuovo_comune_nel_tab.setEnabled(False)
            return

        is_admin = self.logged_in_user_info.get('ruolo') == 'admin'
        is_archivista = self.logged_in_user_info.get('ruolo') == 'archivista'

        # Rimuovi o commenta la gestione di self.nuovo_comune_action
        # if hasattr(self, 'nuovo_comune_action'):
        #     self.nuovo_comune_action.setEnabled(is_admin or is_archivista)

        # Abilita/disabilita il nuovo pulsante nel tab
        if hasattr(self, 'btn_nuovo_comune_nel_tab'):
            self.btn_nuovo_comune_nel_tab.setEnabled(is_admin or is_archivista)

        tab_indices = {self.tabs.tabText(i): i for i in range(self.tabs.count())}

        if "Consultazione" in tab_indices: self.tabs.setTabEnabled(tab_indices["Consultazione"], True)
        if "Ricerca Avanzata Possessori" in tab_indices: self.tabs.setTabEnabled(tab_indices["Ricerca Avanzata Possessori"], True)
        if "Esportazioni" in tab_indices: self.tabs.setTabEnabled(tab_indices["Esportazioni"], True)
        if "Reportistica" in tab_indices: self.tabs.setTabEnabled(tab_indices["Reportistica"], True)

        if "Inserimento e Gestione" in tab_indices:
            self.tabs.setTabEnabled(tab_indices["Inserimento e Gestione"], is_admin or is_archivista)
        if "Statistiche e Viste" in tab_indices:
            self.tabs.setTabEnabled(tab_indices["Statistiche e Viste"], is_admin or is_archivista)
        if "Gestione Utenti" in tab_indices:
            self.tabs.setTabEnabled(tab_indices["Gestione Utenti"], is_admin)
        if "Sistema" in tab_indices:
            self.tabs.setTabEnabled(tab_indices["Sistema"], is_admin)

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
            gui_logger.info(f"Dialogo inserimento comune chiuso con successo da utente '{utente_login_username}'.")
            QMessageBox.information(self, "Comune Aggiunto", "Il nuovo comune è stato registrato con successo.")
            # Aggiorna la vista dell'elenco comuni se presente nel tab consultazione
            # Questo ciclo cerca il widget ElencoComuniWidget tra i sotto-tab di consultazione
            if hasattr(self, 'consultazione_sub_tabs'):
                 for i in range(self.consultazione_sub_tabs.count()):
                    widget = self.consultazione_sub_tabs.widget(i)
                    if isinstance(widget, ElencoComuniWidget):
                        widget.load_comuni_data() # Assumendo che ElencoComuniWidget abbia questo metodo
                        gui_logger.info("Elenco comuni nel tab consultazione aggiornato.")
                        break
        else:
            gui_logger.info(f"Dialogo inserimento comune annullato da utente '{utente_login_username}'.")


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
            gui_logger.warning("Tentativo di logout senza una sessione utente o db_manager validi.")


    def closeEvent(self, event: QCloseEvent): # QCloseEvent deve essere importato in prova.py
        gui_logger.info("Evento closeEvent intercettato in CatastoMainWindow.")

        # Esegui il logout dell'utente applicativo se loggato
        if hasattr(self, 'logged_in_user_id') and self.logged_in_user_id and \
           hasattr(self, 'current_session_id') and self.current_session_id and \
           hasattr(self, 'db_manager') and self.db_manager:
            gui_logger.info(f"Chiusura applicazione: esecuzione logout di sicurezza per utente ID: {self.logged_in_user_id}...")
            self.db_manager.logout_user(self.logged_in_user_id, self.current_session_id, client_ip_address_gui) # Assicurati che client_ip_address_gui sia definito
            self.db_manager.clear_audit_session_variables() 

        # Chiudi il pool di connessioni del database
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.close_pool() 
            gui_logger.info("Pool di connessioni al database chiuso.")

        gui_logger.info("Applicazione GUI Catasto Storico terminata.")
        event.accept() # Conferma la chiusura della finestra

# --- Fine Classe CatastoMainWindow ---

def run_gui_app():
    app = QApplication(sys.argv)
    
    # Applica UN SOLO stylesheet principale all'avvio
    app.setStyleSheet("""
        * {
            font-size: 10pt;
            color: #202020; /* Testo scuro di default per tutti i widget */
        }
        QMainWindow {
            background-color: #F0F0F0; /* Sfondo principale grigio molto chiaro */
        }
        QWidget { /* Sfondo di base per i widget figli, se non specificato diversamente */
            background-color: #F0F0F0;
        }

        /* ----- Etichette ----- */
        QLabel {
            color: #101010; /* Testo leggermente più scuro per le etichette */
            background-color: transparent; /* Assicura che non abbiano sfondo proprio se non voluto */
        }

        /* ----- Campi di Input ----- */
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {
            background-color: #FFFFFF; /* Sfondo bianco per input */
            color: #202020;
            border: 1px solid #B0B0B0; /* Bordo grigio medio */
            border-radius: 3px;
            padding: 4px; /* Aumentato leggermente il padding */
        }
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
            border: 1px solid #0078D7; /* Bordo blu quando l'input ha il focus */
        }

        /* ----- Pulsanti ----- */
        QPushButton {
            background-color: #4CAF50; /* Pulsanti di azione principali verdi */
            color: white;
            border: 1px solid #3E8E41; /* Bordo leggermente più scuro del bg */
            border-radius: 5px;
            padding: 6px 12px; /* Padding per dare respiro */
            font-weight: bold;
            min-width: 70px; /* Larghezza minima per coerenza */
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3e8e41;
        }
        QPushButton:disabled { /* Stile per pulsanti disabilitati */
            background-color: #D0D0D0;
            color: #808080;
            border-color: #B0B0B0;
        }
        /* Pulsanti secondari o meno impattanti (se necessario, si possono usare classi oggetto)
        QPushButton#secondaryButton {
            background-color: #E0E0E0;
            color: #202020;
            border: 1px solid #B0B0B0;
        }
        QPushButton#secondaryButton:hover { background-color: #D0D0D0; }
        QPushButton#secondaryButton:pressed { background-color: #C0C0C0; }
        */

        /* ----- Tabs ----- */
        QTabWidget::pane {
            border: 1px solid #C0C0C0;       /* Bordo del contenuto del tab */
            border-top: none;                /* Rimuoviamo il bordo superiore del pane, sarà gestito dai tab */
            background-color: #F8F8F8;       /* Sfondo del pane */
        }

        QTabBar {
            /* Opzionale: se vuoi un bordo sotto l'intera barra dei tab che li separi dal pane */
            /* border-bottom: 1px solid #C0C0C0; */
            /* Se si usa il bordo sopra, i tab potrebbero necessitare di aggiustamenti per sovrapporsi */
        }

        QTabBar::tab {
            background: #E0E0E0;             /* Sfondo tab non selezionato */
            color: #303030;                  /* Testo tab non selezionato */
            border-top: 1px solid #C0C0C0;
            border-left: 1px solid #C0C0C0;
            border-right: 1px solid #C0C0C0;
            border-bottom: 1px solid #C0C0C0; /* Tutti i tab hanno un bordo inferiore */
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            min-width: 8ex;
            padding: 6px 9px;                /* Padding consistente */
            margin-right: 1px;               /* Piccola spaziatura tra i tab */
            /* Assicurati che non ci sia un margin-bottom residuo qui che possa causare problemi */
        }

        QTabBar::tab:hover {
            background: #D5D5D5;
            color: #101010;
        }

        QTabBar::tab:selected {
            background: #F8F8F8;             /* Sfondo tab selezionato (uguale al pane per effetto "fuso") */
            color: #000000;                  /* Testo tab selezionato più scuro/nero */
            font-weight: bold;
            border-top: 1px solid #C0C0C0;
            border-left: 1px solid #C0C0C0;
            border-right: 1px solid #C0C0C0;
            border-bottom: 1px solid #F8F8F8; /* TRUCCO: Bordo inferiore dello stesso colore dello sfondo del tab/pane */
                                              /* Questo fa "scomparire" il bordo inferiore, facendolo sembrare connesso al pane. */
            /* Nessun margin-bottom negativo necessario con questo approccio se il pane non ha bordo superiore */
            /* padding: 5px 8px; // Assicurarsi che il padding sia lo stesso dello stato non selezionato */
        }

        /* ----- Tabelle ----- */
        QTableWidget {
            gridline-color: #D0D0D0; /* Griglia chiara */
            background-color: #FFFFFF; /* Sfondo tabella bianco */
            color: #202020;
            alternate-background-color: #F5F5F5; /* Alternanza righe grigio molto chiaro */
            selection-background-color: #0078D7; /* Blu per selezione */
            selection-color: white;              /* Testo bianco su selezione */
            border: 1px solid #C0C0C0;
        }
        QHeaderView::section {
            background-color: #E8E8E8; /* Sfondo header tabella */
            color: #202020;
            padding: 5px;
            border: 1px solid #C0C0C0;
            border-bottom-width: 2px; /* Bordo inferiore più marcato per separare dall'area dati */
            font-weight: bold;
        }

        /* ----- QComboBox ----- */
        QComboBox {
            background-color: white;
            color: #202020;
            border: 1px solid #B0B0B0;
            border-radius: 3px;
            padding: 4px;
            min-width: 6em;
        }
        QComboBox:hover {
            border-color: #808080;
        }
        QComboBox::drop-down { /* Pulsante per la tendina */
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 1px;
            border-left-color: #C0C0C0;
            border-left-style: solid;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
            background: #E8E8E8;
        }
        QComboBox::down-arrow {
            /* Se usi icone custom, qui va l'icona per la freccia scura.
               Altrimenti, Qt dovrebbe usare una freccia di sistema che si adatta.
               image: url(path/to/your/dark_arrow_icon.png);
            */
            width: 10px;
            height: 10px;
        }
        QComboBox QAbstractItemView { /* La lista a discesa */
            background-color: #FFFFFF;
            color: #202020;
            border: 1px solid #B0B0B0;
            selection-background-color: #0078D7; /* Blu per selezione item */
            selection-color: white;
            outline: 0px;
            padding: 2px;
        }

        /* ----- ToolTips ----- */
        QToolTip {
            background-color: #FFFFE0; /* Giallo chiaro classico per tooltip */
            color: black;
            border: 1px solid #B0B0B0;
            padding: 3px;
        }

        /* ----- QMessageBox (Dialoghi di Messaggio) ----- */
        QMessageBox {
            background-color: #F0F0F0; /* Sfondo del dialogo */
        }
        QMessageBox QLabel { /* Etichette di testo dentro QMessageBox */
            color: #202020; /* Testo scuro */
            background-color: transparent;
            /*min-width: 150px; // Assicura che il testo abbia spazio */
        }
        /* I QPushButton in QMessageBox erediteranno lo stile globale dei QPushButton */

        /* ----- QMenuBar e QMenu (Menu a Tendina) ----- */
        QMenuBar {
            background-color: #E8E8E8; /* Sfondo barra menu */
            color: #202020;
            spacing: 2px;
        }
        QMenuBar::item {
            background: transparent;
            padding: 4px 10px;
            border-radius: 3px;
        }
        QMenuBar::item:selected {
            background: #D0D0D0;
            color: black;
        }
        QMenuBar::item:pressed {
            background: #C0C0C0; /* Un po' più scuro quando premuto */
        }
        QMenu {
            background-color: #FFFFFF; /* Sfondo menu a tendina bianco */
            color: #202020;
            border: 1px solid #B0B0B0;
            padding: 4px;
        }
        QMenu::item {
            padding: 5px 25px 5px 25px;
            border-radius: 3px;
        }
        QMenu::item:selected {
            background-color: #0078D7; /* Blu per highlight selezione azione */
            color: white;
        }
        QMenu::separator {
            height: 1px;
            background: #D0D0D0; /* Separatore chiaro */
            margin: 4px 0px 4px 0px;
        }
        QMenu::icon {
            padding-left: 5px;
        }

        /* ----- ScrollArea e ScrollBar (se necessario uno stile specifico) ----- */
        QScrollArea {
            border: 1px solid #C0C0C0;
            background: white;
        }
        QScrollBar:horizontal {
            border: none;
            background: #E0E0E0;
            height: 12px;
            margin: 0px 15px 0 15px;
        }
        QScrollBar::handle:horizontal {
            background: #B0B0B0;
            min-width: 20px;
            border-radius: 6px;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: #C0C0C0;
            width: 14px;
            subcontrol-origin: margin;
        }
        QScrollBar::add-line:horizontal { subcontrol-position: right; }
        QScrollBar::sub-line:horizontal { subcontrol-position: left; }

        QScrollBar:vertical {
            border: none;
            background: #E0E0E0;
            width: 12px;
            margin: 15px 0 15px 0;
        }
        QScrollBar::handle:vertical {
            background: #B0B0B0;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: #C0C0C0;
            height: 14px;
            subcontrol-origin: margin;
        }
        QScrollBar::add-line:vertical { subcontrol-position: bottom; }
        QScrollBar::sub-line:vertical { subcontrol-position: top; }

        /* ----- Altri Widget Comuni ----- */
        QGroupBox {
            background-color: #F5F5F5; /* Sfondo leggermente diverso per i group box */
            border: 1px solid #C0C0C0;
            border-radius: 4px;
            margin-top: 2ex; /* Spazio per il titolo */
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left; /* Posizione titolo */
            padding: 0 5px 0 5px;
            left: 10px; /* Spostamento del titolo */
            color: #101010;
        }
        QCheckBox {
            spacing: 5px; /* Spazio tra checkbox e testo */
        }
        QCheckBox::indicator { /* Il quadratino della checkbox */
            width: 16px;
            height: 16px;
            border: 1px solid #B0B0B0;
            border-radius: 3px;
            background-color: white;
        }
        QCheckBox::indicator:checked {
            background-color: #4CAF50; /* Verde quando checkato */
            border-color: #3E8E41;
            image: url(path/to/your/checkmark_white_icon.png); /* Icona di spunta bianca, opzionale */
        }
        QCheckBox::indicator:disabled {
            background-color: #E0E0E0;
            border-color: #C0C0C0;
        }
        QFrame#status_frame { /* Se hai un QFrame con objectName='status_frame' per la status bar */
            background-color: #E0E0E0;
            border-top: 1px solid #B0B0B0;
        }
    """)

    if not FPDF_AVAILABLE:
        QMessageBox.warning(None, "Avviso Dipendenza Mancante",
                             "La libreria FPDF non è installata.\n"
                             "L'esportazione dei report in formato PDF non sarà disponibile.\n"
                             "Puoi installarla con: pip install fpdf2")

    db_config_gui = {
    "dbname": "catasto_storico", "user": "postgres", "password": "Markus74",
    "host": "localhost", "port": 5432, "schema": "catasto"
    }
    # Non è necessario specificare log_file o log_level qui se i default nel costruttore vanno bene
    db_manager_gui = CatastoDBManager(**db_config_gui) 

    # Se volessi sovrascrivere i default, potresti fare:
    # db_manager_gui = CatastoDBManager(
    #     **db_config_gui,
    #     log_file="mio_log_personale.log",
    #     log_level=logging.WARNING
    # )

    db_manager_gui = CatastoDBManager(
        dbname=db_config_gui["dbname"], 
        user=db_config_gui["user"], 
        password=db_config_gui["password"],
        host=db_config_gui["host"], 
        port=db_config_gui["port"],
        schema=db_config_gui.get("schema", "catasto"), # Usa .get() per schema opzionale
        # Assicurati di passare anche min_conn, max_conn, application_name, log_file, log_level
        # se li hai resi parametri obbligatori del __init__ o se vuoi sovrascrivere i default.
        # Esempio basato sulla firma __init__ che abbiamo discusso:
        application_name="CatastoAppGUI_Main", # Nome specifico per l'istanza principale
        log_file="catasto_main_db.log",
        log_level=logging.DEBUG, # O il livello che preferisci per la produzione
        min_conn=1,
        max_conn=5 # O i valori che preferisci per il pool principale
    )

    # Verifica se il pool è stato inizializzato con successo nel costruttore
    if db_manager_gui.pool is None: # <--- NUOVO CONTROLLO
        QMessageBox.critical(None, "Errore Inizializzazione Database",
                             "Impossibile inizializzare il pool di connessioni al database.\n"
                             "Verifica i parametri di connessione, che il server PostgreSQL sia in esecuzione e i log dell'applicazione.\n"
                             "L'applicazione verrà chiusa.")
        # db_manager_gui.close_pool() # Non necessario se il pool è None, ma per sicurezza
        sys.exit(1)
    else:
        # Opzionale: potresti voler "testare" il pool ottenendo e rilasciando una connessione
        # per essere sicuro che sia veramente funzionante, ma __init__ dovrebbe già loggare errori.
        try:
            conn_test = db_manager_gui._get_connection()
            db_manager_gui._release_connection(conn_test)
            gui_logger.info("Test di connessione iniziale al pool riuscito.")
        except Exception as test_conn_err:
            QMessageBox.critical(None, "Errore Connessione Pool",
                                 f"Il pool sembra inizializzato, ma non è possibile ottenere una connessione:\n{test_conn_err}\n"
                                 "L'applicazione verrà chiusa.")
            db_manager_gui.close_pool()
            sys.exit(1)

    main_window_instance = None # Riferimento alla finestra principale
    login_success = False

    while not login_success: # Continua a mostrare il login finché non ha successo o l'utente esce
        login_dialog = LoginDialog(db_manager_gui)
        if login_dialog.exec_() == QDialog.Accepted:
            if login_dialog.logged_in_user_id and login_dialog.logged_in_user_info and login_dialog.current_session_id:
                main_window_instance = CatastoMainWindow() 
                main_window_instance.perform_initial_setup(
                    db_manager_gui,
                    login_dialog.logged_in_user_id,
                    login_dialog.logged_in_user_info,
                    login_dialog.current_session_id
                )
                login_success = True
            else:
                # Questo caso non dovrebbe accadere se LoginDialog.accept() è chiamato solo su login valido
                QMessageBox.critical(None, "Errore Login", "Dati di login non validi ricevuti dal dialogo.")
                # Potrebbe essere meglio chiudere l'app qui o loggare e ritentare
                db_manager_gui.close_pool() # <--- USA QUESTO
                sys.exit(1) # Uscita critica
        else: # LoginDialog è stato chiuso o cancellato
            gui_logger.info("Login annullato o fallito. Uscita dall'applicazione GUI.")
            if db_manager_gui: db_manager_gui.close_pool() # <--- USA QUESTO
            sys.exit(0) # Uscita pulita
            
    if main_window_instance and login_success:
        gui_logger.info(">>> run_gui_app: Login successo, preparazione per app.exec_()")

        # Se vuoi usare una QPalette in aggiunta o al posto di alcune parti del QSS:
        # palette = QPalette()
        # # Esempio di configurazione aggiuntiva o di base se il QSS non è completo
        # palette.setColor(QPalette.Window, QColor(53, 53, 53)) # Sfondo scuro per la finestra
        # palette.setColor(QPalette.WindowText, Qt.white)       # Testo bianco sulla finestra
        # palette.setColor(QPalette.Base, QColor(25, 25, 25))    # Sfondo per input widgets
        # palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45)) # Colore alternato righe
        # palette.setColor(QPalette.ToolTipBase, Qt.white)
        # palette.setColor(QPalette.ToolTipText, Qt.black)
        # palette.setColor(QPalette.Text, Qt.white)            # Colore testo generico
        # palette.setColor(QPalette.Button, QColor(60, 60, 60))  # Sfondo pulsanti (se non da QSS)
        # palette.setColor(QPalette.ButtonText, Qt.white)      # Testo pulsanti (se non da QSS)
        # palette.setColor(QPalette.BrightText, Qt.red)
        # palette.setColor(QPalette.Link, QColor(42, 130, 218))
        # palette.setColor(QPalette.Highlight, QColor(42, 130, 218)) # Colore selezione
        # palette.setColor(QPalette.HighlightedText, Qt.white) # Testo selezionato
        # app.setPalette(palette)

        gui_logger.info(">>> run_gui_app: STA PER ESSERE CHIAMATO app.exec_()")
        exit_code = app.exec_()
        gui_logger.info(f">>> run_gui_app: app.exec_() TERMINATO con codice: {exit_code}")
        sys.exit(exit_code)
    else:
        # Questo blocco viene raggiunto se main_window_instance non è stata creata
        # o login_success è False, il che indicherebbe un problema nel ciclo di login
        # che non ha portato a un'uscita anticipata.
        gui_logger.error("Avvio dell'applicazione fallito: main_window_instance non inizializzata o login non riuscito prima di app.exec_().")
        if db_manager_gui: # Assicurati che db_manager_gui sia definito
            db_manager_gui.close_pool() # <--- USA QUESTO
        sys.exit(1)

    
if __name__ == "__main__":
     # Il logging dovrebbe essere configurato qui se non già fatto altrove all'inizio del file
     # Esempio:
 if not gui_logger.hasHandlers():
     log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
...# (resto della configurazione del logger) ...

run_gui_app()