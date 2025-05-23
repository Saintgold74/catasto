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
                            QDialog, QListWidget,QMainWindow,
                            QListWidgetItem, QFileDialog, QStyle, QStyleFactory, QSpinBox,
                            QInputDialog, QHeaderView,QFrame,QAbstractItemView,QSizePolicy,QAction, QMenu,QFormLayout) 
from PyQt5.QtCore import Qt, QDate, QSettings 
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QCloseEvent # Aggiunto QCloseEvent
from PyQt5.QtWidgets import QDoubleSpinBox


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
                self.logged_in_user_info = credentials
                self.current_session_id = session_id_returned
                
                if not self.db_manager.set_session_app_user(self.logged_in_user_id, client_ip_address_gui):
                    gui_logger.error("Impossibile impostare contesto DB post-login!")
                
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
        # Assumendo esista un PossessoreSearchDialog, simile a PartitaSearchDialog
        # Altrimenti, si può usare un semplice QInputDialog per l'ID.
        dialog = PossessoreSearchDialog(self.db_manager, self) # Assumiamo che PossessoreSearchDialog esista
        if dialog.exec_() == QDialog.Accepted and dialog.selected_possessore_id:
            self.selected_possessore_id_export = dialog.selected_possessore_id
            self.possessore_id_export_edit.setValue(self.selected_possessore_id_export)
            # Mostra info possessore
            poss_details = self.db_manager.get_possessore_data_for_export(self.selected_possessore_id_export) # usa il metodo corretto
            if poss_details and 'possessore' in poss_details:
                self.possessore_info_export_label.setText(f"Selezionato: {poss_details['possessore'].get('nome_completo')} (Comune: {poss_details['possessore'].get('comune_nome')})")
            else:
                self.possessore_info_export_label.setText("Possessore non trovato.")
        else:
            self.selected_possessore_id_export = None
            self.possessore_info_export_label.setText("Nessun possessore selezionato.")


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
        
        # Mostra un messaggio con il numero di risultati
        QMessageBox.information(self, "Ricerca Completata", f"Trovate {len(partite)} partite corrispondenti ai criteri.")
    
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
        
        criteria_layout.addWidget(QLabel("Termine di ricerca (nome, cognome, ecc.):"), 0, 0)
        self.search_term_edit = QLineEdit()
        self.search_term_edit.setPlaceholderText("Inserisci parte del nome o altri termini...")
        criteria_layout.addWidget(self.search_term_edit, 0, 1, 1, 2)
        
        # Opzione per la soglia di similarità (come nel tab Ricerca Avanzata)
        criteria_layout.addWidget(QLabel("Soglia di similarità (0.0 - 1.0):"), 1, 0)
        self.similarity_threshold_spinbox = QDoubleSpinBox()
        self.similarity_threshold_spinbox.setMinimum(0.0)
        self.similarity_threshold_spinbox.setMaximum(1.0)
        self.similarity_threshold_spinbox.setSingleStep(0.05)
        self.similarity_threshold_spinbox.setValue(0.3) # Un default ragionevole per la consultazione
        criteria_layout.addWidget(self.similarity_threshold_spinbox, 1, 1)
        
        self.search_button = QPushButton("Cerca Possessori")
        self.search_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton)) # O SP_performSearch
        self.search_button.clicked.connect(self._perform_search)
        criteria_layout.addWidget(self.search_button, 1, 2)
        
        main_layout.addWidget(search_criteria_group)
        
        # --- Tabella per i Risultati ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7) # ID, Nome Completo, Cognome/Nome, Paternità, Comune, Similarità, Num. Partite
        self.results_table.setHorizontalHeaderLabels([
            "ID", "Nome Completo", "Cognome Nome", "Paternità", "Comune Rif.", "Similarità", "Num. Partite"
        ])
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.itemDoubleClicked.connect(self._show_possessore_details) # Opzionale
        main_layout.addWidget(self.results_table)

    def _perform_search(self):
        search_term = self.search_term_edit.text().strip()
        similarity_threshold = self.similarity_threshold_spinbox.value()
        
        if not search_term:
            QMessageBox.warning(self, "Input Mancante", "Per favore, inserisci un termine di ricerca.")
            return
            
        try:
            # Usiamo la funzione esistente ricerca_avanzata_possessori
            possessori = self.db_manager.ricerca_avanzata_possessori(
                query_text=search_term,
                similarity_threshold=similarity_threshold
            )
            
            self.results_table.setRowCount(0) # Pulisce la tabella
            
            if not possessori:
                QMessageBox.information(self, "Ricerca Possessori", "Nessun possessore trovato con i criteri specificati.")
                return
                
            self.results_table.setRowCount(len(possessori))
            for row_idx, possessore_data in enumerate(possessori):
                col = 0
                self.results_table.setItem(row_idx, col, QTableWidgetItem(str(possessore_data.get('id', 'N/D')))); col+=1
                self.results_table.setItem(row_idx, col, QTableWidgetItem(possessore_data.get('nome_completo', 'N/D'))); col+=1
                self.results_table.setItem(row_idx, col, QTableWidgetItem(possessore_data.get('cognome_nome', 'N/D'))); col+=1 # NUOVA COLONNA
                self.results_table.setItem(row_idx, col, QTableWidgetItem(possessore_data.get('paternita', 'N/D'))); col+=1    # NUOVA COLONNA
                self.results_table.setItem(row_idx, col, QTableWidgetItem(possessore_data.get('comune_nome', 'N/D'))); col+=1
                self.results_table.setItem(row_idx, col, QTableWidgetItem(f"{possessore_data.get('similarity', 0.0):.3f}")); col+=1
                self.results_table.setItem(row_idx, col, QTableWidgetItem(str(possessore_data.get('num_partite', 'N/D')))); col+=1
            
            self.results_table.resizeColumnsToContents()
            
        except Exception as e:
            gui_logger.error(f"Errore durante la ricerca possessori (GUI - Consultazione): {e}")
            QMessageBox.critical(self, "Errore Ricerca", f"Si è verificato un errore durante la ricerca: {e}")

    def _show_possessore_details(self, item: QTableWidgetItem):
        if item is None:
            return
        try:
            row = item.row()
            possessore_id_str = self.results_table.item(row, 0).text()
            possessore_id = int(possessore_id_str)
            
            # Qui dovresti implementare un dialogo per mostrare i dettagli del possessore.
            # Potrebbe essere una nuova classe PossessoreDetailsDialog.
            # Per ora, mostriamo un QMessageBox.
            
            # Esempio di recupero dati dettagliati (richiede un metodo in db_manager)
            # dettagli_possessore = self.db_manager.get_possessore_full_details(possessore_id) 
            # if dettagli_possessore:
            #    dialog = PossessoreDetailsDialog(dettagli_possessore, self)
            #    dialog.exec_()
            # else:
            #    QMessageBox.warning(self, "Dettagli non trovati", f"Impossibile recuperare i dettagli per il possessore ID {possessore_id}.")

            QMessageBox.information(self, "Dettaglio Possessore", 
                                    f"Dettaglio per possessore ID: {possessore_id} (dialogo dettagli da implementare).")
        except ValueError:
            QMessageBox.warning(self, "Errore ID", "ID del possessore non valido nella tabella.")
        except Exception as e:
            gui_logger.error(f"Errore nell'aprire dettagli possessore: {e}")
            QMessageBox.critical(self, "Errore", f"Impossibile mostrare i dettagli: {e}")

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

        self.setWindowTitle(f"Partite del Comune di {self.nome_comune} (ID: {self.comune_id})")
        self.setMinimumSize(800, 500) # Dimensioni generose per la tabella

        layout = QVBoxLayout(self)

        # Filtro (opzionale, per ora semplice tabella)
        # Si potrebbe aggiungere un QLineEdit per filtrare le partite per numero o possessore

        # Tabella Partite
        self.partite_table = QTableWidget()
        # ID, Numero, Tipo, Stato, Data Impianto, Possessori (stringa), Num. Immobili
        self.partite_table.setColumnCount(7)
        self.partite_table.setHorizontalHeaderLabels([
            "ID Partita", "Numero", "Tipo", "Stato",
            "Data Impianto", "Possessori (Anteprima)", "Num. Immobili"
        ])
        self.partite_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.partite_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.partite_table.setSelectionMode(QTableWidget.SingleSelection) # O ExtendedSelection se vuoi multiselezione
        self.partite_table.setAlternatingRowColors(True)
        self.partite_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.partite_table.setSortingEnabled(True)
        self.partite_table.itemDoubleClicked.connect(self.apri_dettaglio_partita_selezionata) # Per aprire PartitaDetailsDialog

        layout.addWidget(self.partite_table)

        # Pulsante Chiudi
        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button, alignment=Qt.AlignRight)

        self.setLayout(layout)
        self.load_partite_data()

    def load_partite_data(self):
        """Carica le partite per il comune specificato."""
        self.partite_table.setRowCount(0)
        self.partite_table.setSortingEnabled(False)

        try:
            # Assumiamo che db_manager.get_partite_by_comune(comune_id) esista
            # e restituisca una lista di dizionari con le chiavi necessarie.
            # Dal tuo catasto_db_manager.py, la query in get_partite_by_comune include:
            # p.id, c.nome as comune_nome, p.numero_partita, p.tipo, p.data_impianto,
            # p.data_chiusura, p.stato,
            # string_agg(DISTINCT pos.nome_completo, ', ') as possessori,
            # COUNT(DISTINCT i.id) as num_immobili
            partite_list = self.db_manager.get_partite_by_comune(self.comune_id) #

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
        except AttributeError as ae:
            gui_logger.error(f"Attributo mancante nel db_manager: {ae}. Assicurati che 'get_partite_by_comune' esista.")
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Funzione dati partite non trovata: {ae}")
        except Exception as e:
            gui_logger.error(f"Errore durante il caricamento delle partite per comune ID {self.comune_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
        finally:
            self.partite_table.setSortingEnabled(True)

    def apri_dettaglio_partita_selezionata(self, item):
         """Apre il dialogo dei dettagli per la partita selezionata."""
         if not item: return
         row = item.row()
         partita_id_str = self.partite_table.item(row, 0).text()
         if partita_id_str.isdigit():
             partita_id = int(partita_id_str)
          # Il metodo get_partita_details già esiste nel tuo db_manager
             partita_details_data = self.db_manager.get_partita_details(partita_id) #
             if partita_details_data:
                 # Assumendo che PartitaDetailsDialog esista e sia importato
                 details_dialog = PartitaDetailsDialog(partita_details_data, self)
                 details_dialog.exec_()
             else:
                 QMessageBox.warning(self, "Errore Dati", f"Impossibile recuperare i dettagli per la partita ID {partita_id}.")
         else:
             QMessageBox.warning(self, "ID Non Valido", "ID partita non valido nella riga selezionata.")
class PossessoriComuneDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, nome_comune: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.nome_comune = nome_comune

        self.setWindowTitle(f"Possessori del Comune di {self.nome_comune} (ID: {self.comune_id})")
        self.setMinimumSize(800, 500)

        layout = QVBoxLayout(self)

        # Tabella Possessori
        self.possessori_table = QTableWidget()
        # ID, Nome Completo, Cognome/Nome (se disponibile), Paternità, Stato
        self.possessori_table.setColumnCount(5) # Aggiunta colonna per Cognome/Nome
        self.possessori_table.setHorizontalHeaderLabels([
            "ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Stato"
        ])
        self.possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.setSelectionMode(QTableWidget.SingleSelection)
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.possessori_table.setSortingEnabled(True)
        # self.possessori_table.itemDoubleClicked.connect(self.apri_dettaglio_possessore_selezionato) # Per futuri dettagli

        layout.addWidget(self.possessori_table)

        # Pulsante Chiudi
        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button, alignment=Qt.AlignRight)

        self.setLayout(layout)
        self.load_possessori_data()

    def load_possessori_data(self):
        """Carica i possessori per il comune specificato."""
        self.possessori_table.setRowCount(0)
        self.possessori_table.setSortingEnabled(False)

        try:
            # Utilizziamo il metodo che hai confermato esistere e funzionare:
            # db_manager.get_possessori_by_comune(comune_id)
            # Questo metodo, dal tuo codice, restituisce:
            # pos.id, c.nome as comune_nome, pos.cognome_nome, pos.paternita, pos.nome_completo, pos.attivo
            possessori_list = self.db_manager.get_possessori_by_comune(self.comune_id) #

            if possessori_list:
                self.possessori_table.setRowCount(len(possessori_list))
                for row_idx, possessore in enumerate(possessori_list):
                    col = 0
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(str(possessore.get('id', '')))); col+=1
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(possessore.get('nome_completo', ''))); col+=1
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(possessore.get('cognome_nome', ''))); col+=1 # Da get_possessori_by_comune
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(possessore.get('paternita', ''))); col+=1
                    stato_str = "Attivo" if possessore.get('attivo', False) else "Non Attivo"
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(stato_str)); col+=1
                
                self.possessori_table.resizeColumnsToContents()
            else:
                gui_logger.info(f"Nessun possessore trovato per il comune ID: {self.comune_id}")
        except AttributeError as ae:
            gui_logger.error(f"Attributo mancante nel db_manager: {ae}. Assicurati che 'get_possessori_by_comune' esista e sia corretto.")
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Funzione dati possessori non trovata o errata: {ae}")
        except Exception as e:
            gui_logger.error(f"Errore durante il caricamento dei possessori per comune ID {self.comune_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
        finally:
            self.possessori_table.setSortingEnabled(True)

    # def apri_dettaglio_possessore_selezionato(self, item):
    #     """Apre il dialogo dei dettagli per il possessore selezionato (DA IMPLEMENTARE)."""
    #     if not item: return
    #     row = item.row()
    #     possessore_id_str = self.possessori_table.item(row, 0).text()
    #     if possessore_id_str.isdigit():
    #         possessore_id = int(possessore_id_str)
    #         # Qui dovresti avere un DialogoDettagliPossessore e un metodo in db_manager
    #         # per recuperare tutti i dettagli del possessore, incluse le partite associate.
    #         # Esempio: possessore_details_data = self.db_manager.get_possessore_full_details(possessore_id)
    #         # if possessore_details_data:
    #         # details_dialog = DialogoDettagliPossessore(possessore_details_data, self)
    #         # details_dialog.exec_()
    #         QMessageBox.information(self, "Dettaglio Possessore", f"Dettaglio per ID {possessore_id} (da implementare)")
    #     else:
    #         QMessageBox.warning(self, "ID Non Valido", "ID possessore non valido.")
             
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
        comune_id_selezionato = self.comune_combo.itemData(idx_comune) if idx_comune >= 0 else None
        
        attivo = self.attivo_checkbox.isChecked()

        if not nome_completo:
            QMessageBox.warning(self, "Dati Mancanti", "Il campo 'Nome Completo' è obbligatorio.")
            return
        if comune_id_selezionato is None:
            QMessageBox.warning(self, "Dati Mancanti", "Selezionare un comune di riferimento.")
            return

        try:
            # Assumendo che db_manager.create_possessore accetti anche cognome_nome
            # Se il tuo metodo create_possessore non lo accetta, dovrai modificarlo
            # o non passare cognome_nome se non è un campo del DB.
            success = self.db_manager.create_possessore(
                nome_completo=nome_completo,
                paternita=paternita if paternita else None, # Passa None se vuoto
                comune_riferimento_id=comune_id_selezionato,
                attivo=attivo,
                cognome_nome=cognome_nome if cognome_nome else None # Passa anche questo
            )
            if success:
                QMessageBox.information(self, "Successo", f"Possessore '{nome_completo}' creato con successo.")
                # Pulisci i campi del form dopo il salvataggio
                self.nome_completo_edit.clear()
                self.paternita_edit.clear()
                self.cognome_nome_edit.clear()
                self.comune_combo.setCurrentIndex(-1) # Resetta combobox
                self.attivo_checkbox.setChecked(True)
                # Potresti voler ricaricare la tabella dei possessori, se ne hai una in questo widget
                # self._carica_possessori_esistenti_in_tabella() 
            else:
                QMessageBox.critical(self, "Errore Database", "Impossibile creare il possessore. Controllare i log.")
        except Exception as e:
            gui_logger.error(f"Errore durante il salvataggio del possessore: {e}")
            QMessageBox.critical(self, "Errore Critico", f"Si è verificato un errore imprevisto: {e}")


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
        """Apre il selettore di comuni."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)
            # Aggiorna la lista delle località per il comune selezionato
            self.refresh_localita()
    
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
        self.localita_table.setRowCount(0)
        
        if self.comune_id:
            # Esegue una query diretta per le località
            query = "SELECT id, nome, tipo, civico FROM localita WHERE comune_id = %s ORDER BY tipo, nome, civico"
            if self.db_manager.execute_query(query, (self.comune_id,)):
                localita = self.db_manager.fetchall()
                
                if localita:
                    self.localita_table.setRowCount(len(localita))
                    
                    for i, loc in enumerate(localita):
                        self.localita_table.setItem(i, 0, QTableWidgetItem(str(loc.get('id', ''))))
                        self.localita_table.setItem(i, 1, QTableWidgetItem(loc.get('nome', '')))
                        self.localita_table.setItem(i, 2, QTableWidgetItem(loc.get('tipo', '')))
                        
                        civico_text = str(loc.get('civico', '')) if loc.get('civico') is not None else "-"
                        self.localita_table.setItem(i, 3, QTableWidgetItem(civico_text))
                
                self.localita_table.resizeColumnsToContents()

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
    
    def register_property(self):
        """Registra la nuova proprietà nel database."""
        # Validazione input
        if not self.comune_id:
            QMessageBox.warning(self, "Errore", "Seleziona un comune.")
            return
        
        if not self.possessori_data:
            QMessageBox.warning(self, "Errore", "Aggiungi almeno un possessore.")
            return
        
        if not self.immobili_data:
            QMessageBox.warning(self, "Errore", "Aggiungi almeno un immobile.")
            return
        
        # Raccoglie i dati
        numero_partita = self.num_partita_edit.value()
        data_impianto = self.data_edit.date().toPyDate()
        
        # Chiama la funzione del DB manager
        result = self.db_manager.registra_nuova_proprieta(
            self.comune_id,
            numero_partita,
            data_impianto,
            self.possessori_data,
            self.immobili_data
        )
        
        if result:
            QMessageBox.information(self, "Successo", "Nuova proprietà registrata con successo.")
            
            # Pulisce i campi
            self.comune_id = None
            self.comune_display.setText("Nessun comune selezionato")
            self.num_partita_edit.setValue(1)
            self.data_edit.setDate(QDate.currentDate())
            self.possessori_data = []
            self.immobili_data = []
            self.update_possessori_table()
            self.update_immobili_table()
        else:
            QMessageBox.critical(self, "Errore", "Errore durante la registrazione della proprietà.")

class RicercaAvanzataWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Ricerca Avanzata per Similarità") # Titolo del widget, anche se nel tab non si vede
        
        main_layout = QVBoxLayout(self)
        
        # --- Sezione Ricerca Possessori per Similarità ---
        possessori_group = QGroupBox("Ricerca Avanzata Possessori per Similarità")
        possessori_layout = QGridLayout(possessori_group)
        
        possessori_layout.addWidget(QLabel("Termine di ricerca (nome, cognome, paternità):"), 0, 0)
        self.possessore_query_edit = QLineEdit()
        self.possessore_query_edit.setPlaceholderText("Inserisci parte del nome, cognome o paternità...")
        possessori_layout.addWidget(self.possessore_query_edit, 0, 1, 1, 2) # Span su 2 colonne
        
        possessori_layout.addWidget(QLabel("Soglia di similarità (0.0 - 1.0):"), 1, 0)
        self.possessore_soglia_spinbox = QDoubleSpinBox()
        self.possessore_soglia_spinbox.setMinimum(0.0)
        self.possessore_soglia_spinbox.setMaximum(1.0)
        self.possessore_soglia_spinbox.setSingleStep(0.05)
        self.possessore_soglia_spinbox.setValue(0.2) # Valore di default
        possessori_layout.addWidget(self.possessore_soglia_spinbox, 1, 1)
        
        self.btn_cerca_possessori_av = QPushButton("Cerca Possessori")
        self.btn_cerca_possessori_av.setIcon(QApplication.style().standardIcon(QStyle.SP_FileDialogContentsView))
        self.btn_cerca_possessori_av.clicked.connect(self._esegui_ricerca_possessori_avanzata)
        possessori_layout.addWidget(self.btn_cerca_possessori_av, 1, 2)
        
        main_layout.addWidget(possessori_group)
        
        # Tabella per i risultati della ricerca possessori
        self.risultati_possessori_table = QTableWidget()
        self.risultati_possessori_table.setColumnCount(5) # ID, Nome Completo, Comune Nome, Similarità, Num. Partite
        self.risultati_possessori_table.setHorizontalHeaderLabels([
            "ID", "Nome Completo", "Comune Riferimento", "Similarità", "Num. Partite"
        ])
        self.risultati_possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.risultati_possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.risultati_possessori_table.setAlternatingRowColors(True)
        self.risultati_possessori_table.horizontalHeader().setStretchLastSection(True)
        self.risultati_possessori_table.itemDoubleClicked.connect(self._apri_dettaglio_possessore) # Opzionale
        main_layout.addWidget(self.risultati_possessori_table)
        
        # TODO: Potresti aggiungere qui altre sezioni per ricerca avanzata immobili, partite, ecc.
        # usando sub-tab o altri QGroupBox se necessario.

        main_layout.addStretch() # Per spingere gli elementi in alto

    def _esegui_ricerca_possessori_avanzata(self):
        query_text = self.possessore_query_edit.text().strip()
        similarity_threshold = self.possessore_soglia_spinbox.value()
        
        if not query_text:
            QMessageBox.warning(self, "Input Mancante", "Inserisci un termine di ricerca per i possessori.")
            return
            
        try:
            # Chiamata al metodo del db_manager (versione a 2 parametri)
            risultati = self.db_manager.ricerca_avanzata_possessori(
                query_text=query_text,
                similarity_threshold=similarity_threshold
            )
            
            self.risultati_possessori_table.setRowCount(0) # Pulisce la tabella
            
            if not risultati:
                QMessageBox.information(self, "Ricerca Avanzata", "Nessun possessore trovato con i criteri specificati.")
                return
                
            self.risultati_possessori_table.setRowCount(len(risultati))
            for row_idx, possessore in enumerate(risultati):
                self.risultati_possessori_table.setItem(row_idx, 0, QTableWidgetItem(str(possessore.get('id', 'N/D'))))
                self.risultati_possessori_table.setItem(row_idx, 1, QTableWidgetItem(possessore.get('nome_completo', 'N/D')))
                self.risultati_possessori_table.setItem(row_idx, 2, QTableWidgetItem(possessore.get('comune_nome', 'N/D'))) # Dal JOIN nella funzione SQL
                self.risultati_possessori_table.setItem(row_idx, 3, QTableWidgetItem(f"{possessore.get('similarity', 0.0):.3f}")) # Formatta la similarità
                self.risultati_possessori_table.setItem(row_idx, 4, QTableWidgetItem(str(possessore.get('num_partite', 'N/D')))) # Dal COUNT nella funzione SQL

            self.risultati_possessori_table.resizeColumnsToContents()
            
        except Exception as e:
            gui_logger.error(f"Errore durante la ricerca avanzata possessori (GUI): {e}")
            QMessageBox.critical(self, "Errore Ricerca", f"Si è verificato un errore: {e}")

    def _apri_dettaglio_possessore(self, item): # Funzione opzionale
         if item is None: return
         row = item.row()
         try:
             possessore_id = int(self.risultati_possessori_table.item(row, 0).text())
    #         # Qui potresti aprire un dialogo con i dettagli del possessore,
    #         # simile a PartitaDetailsDialog ma per possessori.
             QMessageBox.information(self, "Dettaglio", f"Dettaglio per possessore ID: {possessore_id} (da implementare).")
         except (ValueError, TypeError) as e:
             gui_logger.error(f"Errore nel recuperare ID possessore dalla tabella: {e}")

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
    
    def load_possessori(self, filter_text=None):
        """Carica i possessori dal database con filtro opzionale."""
        self.possessori_table.setRowCount(0)
        
        if self.comune_id:
            possessori_list = self.db_manager.get_possessori_by_comune(self.comune_id) # Rinominato per chiarezza
            
            if possessori_list:
                if filter_text:
                    possessori_list = [p for p in possessori_list if filter_text.lower() in p.get('nome_completo', '').lower()]
                
                self.possessori_table.setRowCount(len(possessori_list))
                
                # Assicurati che NUOVE_ETICHETTE_POSSESSORI sia definito globalmente o come attributo di classe/istanza
                # Esempio: NUOVE_ETICHETTE_POSSESSORI = ["cognome_nome", "paternita_dettaglio", ...]

                for i, pos_data in enumerate(possessori_list): # Usa 'i' come indice di riga, 'pos_data' per i dati del possessore
                    col = 0 # Inizializza l'indice di colonna per ogni riga

                    # Colonna ID
                    self.possessori_table.setItem(i, col, QTableWidgetItem(str(pos_data.get('id', ''))))
                    col += 1

                    # Colonna Nome Completo
                    self.possessori_table.setItem(i, col, QTableWidgetItem(pos_data.get('nome_completo', '')))
                    col += 1
                    
                    # Gestione delle "NUOVE COLONNE" in modo dinamico o specifico
                    # Esempio se vuoi aggiungere 'cognome_nome' se presente in NUOVE_ETICHETTE_POSSESSORI
                    if 'cognome_nome' in NUOVE_ETICHETTE_POSSESSORI:
                        self.possessori_table.setItem(i, col, QTableWidgetItem(str(pos_data.get('cognome_nome', 'N/D'))))
                        col += 1
                    
                    # Colonna Paternita (originale, la tua riga successiva la sovrascriverebbe o sarebbe la colonna successiva)
                    # Se la 'paternita' dal blocco "NUOVE COLONNE" è diversa o aggiuntiva:
                    if 'paternita_dettaglio' in NUOVE_ETICHETTE_POSSESSORI: # Esempio se hai un'etichetta specifica
                        self.possessori_table.setItem(i, col, QTableWidgetItem(str(pos_data.get('paternita', 'N/D')))) # o un campo diverso da pos_data
                        col += 1
                    # Altrimenti, se la riga successiva gestisce la paternità standard:
                    # self.possessori_table.setItem(i, col, QTableWidgetItem(pos_data.get('paternita', '')))
                    # col += 1

                    # La tua riga successiva per 'paternita'
                    # Questa riga sembra essere la gestione standard della paternità.
                    # Assicurati che 'col' abbia il valore corretto qui.
                    # Se le "NUOVE COLONNE" hanno già incrementato 'col', allora questa potrebbe
                    # essere la colonna successiva.
                    # Per ora, assumo che questa sia la colonna standard per 'paternita'
                    # e che le "NUOVE COLONNE" siano inserite prima se NUOVE_ETICHETTE_POSSESSORI lo prevede.
                    # Se il blocco "NUOVE COLONNE" gestisce già la paternità, questa riga potrebbe essere ridondante o errata.
                    
                    # Riconsiderando la logica originale:
                    # Colonna 0: id
                    # Colonna 1: nome_completo
                    # Il blocco "NUOVE COLONNE" è inserito in modo confuso.
                    # Semplifichiamo e rendiamo l'ordine esplicito:

                # Ri-strutturazione del ciclo per maggiore chiarezza:
                for i, pos_data in enumerate(possessori_list):
                    current_col = 0

                    # ID
                    self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(pos_data.get('id', ''))))
                    current_col += 1

                    # Nome Completo
                    self.possessori_table.setItem(i, current_col, QTableWidgetItem(pos_data.get('nome_completo', '')))
                    current_col += 1

                    # Cognome e Nome (se la colonna è prevista)
                    if 'cognome_nome' in NUOVE_ETICHETTE_POSSESSORI:
                        self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(pos_data.get('cognome_nome', 'N/D'))))
                        current_col += 1
                    
                    # Paternità (se la colonna è prevista E diversa da quella standard)
                    # O la tua colonna paternità standard:
                    self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(pos_data.get('paternita', 'N/D'))))
                    current_col += 1
                    
                    # Stato
                    stato_str = "Attivo" if pos_data.get('attivo') else "Non Attivo"
                    self.possessori_table.setItem(i, current_col, QTableWidgetItem(stato_str))
                    current_col += 1

                    # Aggiungi qui altre colonne se necessario, usando current_col e incrementandolo

                self.possessori_table.resizeColumnsToContents()
    
    def filter_possessori(self):
        """Filtra i possessori in base al testo inserito."""
        filter_text = self.filter_edit.text().strip()
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
        if self.current_tab == 0:  # Seleziona esistente
            selected_rows = self.possessori_table.selectedIndexes()
            if not selected_rows:
                QMessageBox.warning(self, "Attenzione", "Seleziona un possessore dalla tabella.")
                return
            
            row = selected_rows[0].row()
            
            # Recupera i dati del possessore selezionato
            possessore_id = int(self.possessori_table.item(row, 0).text())
            nome_completo = self.possessori_table.item(row, 1).text()
            paternita = self.possessori_table.item(row, 2).text() if self.possessori_table.item(row, 2) else ""
            
            # Dialogo per la quota
            quota, ok = QInputDialog.getText(
                self, "Quota", "Inserisci la quota (vuoto per esclusiva):",
                QLineEdit.Normal, ""
            )
            
            if ok:
                self.selected_possessore = {
                    'id': possessore_id,
                    'nome_completo': nome_completo,
                    'paternita': paternita,
                    'quota': quota
                }
                self.accept()
        
        else:  # Crea nuovo
            cognome_nome = self.cognome_edit.text().strip()
            paternita = self.paternita_edit.text().strip()
            nome_completo = self.nome_completo_edit.text().strip()
            quota = self.quota_edit.text().strip()
            
            if not cognome_nome or not nome_completo:
                QMessageBox.warning(self, "Errore", "Cognome e nome e Nome completo sono obbligatori.")
                return
            
            # Inserisci nuovo possessore
            possessore_id = self.db_manager.insert_possessore(
                self.comune_id, cognome_nome, paternita, nome_completo, True
            )
            
            if possessore_id:
                self.selected_possessore = {
                    'id': possessore_id,
                    'nome_completo': nome_completo,
                    'cognome_nome': cognome_nome,
                    'paternita': paternita,
                    'quota': quota
                }
                self.accept()
            else:
                QMessageBox.critical(self, "Errore", "Errore durante l'inserimento del possessore.")

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
        dialog = LocalitaSelectionDialog(self.db_manager, self.comune_id, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_localita_id:
            self.localita_id = dialog.selected_localita_id
            self.localita_display.setText(dialog.selected_localita_name)
    
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
class LocalitaSelectionDialog(QDialog):
    def __init__(self, db_manager, comune_id, parent=None):
        super(LocalitaSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.selected_localita_id = None
        self.selected_localita_name = None
        
        self.setWindowTitle("Seleziona Località")
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
        self.filter_edit.textChanged.connect(self.filter_localita)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)
        
        select_layout.addLayout(filter_layout)
        
        # Tabella località
        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(4)
        self.localita_table.setHorizontalHeaderLabels(["ID", "Nome", "Tipo", "Civico"])
        self.localita_table.setAlternatingRowColors(True)
        self.localita_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.localita_table.setSelectionMode(QTableWidget.SingleSelection)
        self.localita_table.itemDoubleClicked.connect(self.select_from_table)
        
        select_layout.addWidget(self.localita_table)
        
        select_tab.setLayout(select_layout)
        tabs.addTab(select_tab, "Seleziona Esistente")
        
        # Tab Crea
        create_tab = QWidget()
        create_layout = QGridLayout()
        
        # Nome
        nome_label = QLabel("Nome località:")
        self.nome_edit = QLineEdit()
        
        create_layout.addWidget(nome_label, 0, 0)
        create_layout.addWidget(self.nome_edit, 0, 1)
        
        # Tipo
        tipo_label = QLabel("Tipo:")
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["regione", "via", "borgata"])
        
        create_layout.addWidget(tipo_label, 1, 0)
        create_layout.addWidget(self.tipo_combo, 1, 1)
        
        # Civico
        civico_label = QLabel("Civico (solo per vie):")
        self.civico_edit = QSpinBox()
        self.civico_edit.setMinimum(0)
        self.civico_edit.setMaximum(9999)
        self.civico_edit.setSpecialValueText("Nessun civico")
        
        create_layout.addWidget(civico_label, 2, 0)
        create_layout.addWidget(self.civico_edit, 2, 1)
        
        create_tab.setLayout(create_layout)
        tabs.addTab(create_tab, "Crea Nuova")
        
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
        
        # Carica le località iniziali
        self.current_tab = 0
        tabs.currentChanged.connect(self.tab_changed)
        self.load_localita()
    
    def tab_changed(self, index):
        """Gestisce il cambio di tab."""
        self.current_tab = index
        if index == 0:
            self.ok_button.setText("Seleziona")
        else:
            self.ok_button.setText("Crea e Seleziona")
    
    def load_localita(self, filter_text=None):
        """Carica le località dal database con filtro opzionale."""
        self.localita_table.setRowCount(0)
        
        if self.comune_id:
            # Esegue una query diretta per le località
            query = "SELECT id, nome, tipo, civico FROM localita WHERE comune_id = %s ORDER BY tipo, nome, civico"
            if self.db_manager.execute_query(query, (self.comune_id,)):
                localita = self.db_manager.fetchall()
                
                if localita:
                    # Filtra se necessario
                    if filter_text:
                        localita = [l for l in localita if filter_text.lower() in l.get('nome', '').lower()]
                    
                    self.localita_table.setRowCount(len(localita))
                    
                    for i, loc in enumerate(localita):
                        self.localita_table.setItem(i, 0, QTableWidgetItem(str(loc.get('id', ''))))
                        self.localita_table.setItem(i, 1, QTableWidgetItem(loc.get('nome', '')))
                        self.localita_table.setItem(i, 2, QTableWidgetItem(loc.get('tipo', '')))
                        
                        civico_text = str(loc.get('civico', '')) if loc.get('civico') is not None else "-"
                        self.localita_table.setItem(i, 3, QTableWidgetItem(civico_text))
                
                self.localita_table.resizeColumnsToContents()
    
    def filter_localita(self):
        """Filtra le località in base al testo inserito."""
        filter_text = self.filter_edit.text().strip()
        self.load_localita(filter_text if filter_text else None)
    
    def select_from_table(self, item):
        """Gestisce la selezione dalla tabella delle località."""
        row = item.row()
        self.handle_selection()
    
    def handle_selection(self):
        """Gestisce la selezione o creazione della località."""
        if self.current_tab == 0:  # Seleziona esistente
            selected_rows = self.localita_table.selectedIndexes()
            if not selected_rows:
                QMessageBox.warning(self, "Attenzione", "Seleziona una località dalla tabella.")
                return
            
            row = selected_rows[0].row()
            
            # Recupera i dati della località selezionata
            self.selected_localita_id = int(self.localita_table.item(row, 0).text())
            self.selected_localita_name = self.localita_table.item(row, 1).text()
            
            # Include il tipo e il civico nel nome visualizzato
            tipo = self.localita_table.item(row, 2).text()
            civico = self.localita_table.item(row, 3).text()
            if civico != "-":
                self.selected_localita_name += f", {civico}"
            self.selected_localita_name += f" ({tipo})"
            
            self.accept()
        
        else:  # Crea nuova
            nome = self.nome_edit.text().strip()
            tipo = self.tipo_combo.currentText()
            civico = self.civico_edit.value() if self.civico_edit.value() > 0 else None
            
            if not nome:
                QMessageBox.warning(self, "Errore", "Il nome della località è obbligatorio.")
                return
            
            # Inserisci nuova località
            localita_id = self.db_manager.insert_localita(
                self.comune_id, nome, tipo, civico
            )
            
            if localita_id:
                self.selected_localita_id = localita_id
                self.selected_localita_name = nome
                
                # Include il tipo e il civico nel nome visualizzato
                if civico:
                    self.selected_localita_name += f", {civico}"
                self.selected_localita_name += f" ({tipo})"
                
                self.accept()
            else:
                QMessageBox.critical(self, "Errore", "Errore durante l'inserimento della località.")

          # --- Scheda per Reportistica ---
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
        dialog = PossessoreSearchDialog(self.db_manager, self)
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
class InserimentoComuneWidget(QDialog): # o QWidget
    def __init__(self, db_manager, utente_attuale, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.utente_attuale = utente_attuale

        self.setWindowTitle("Inserimento Nuovo Comune")
        self.setModal(True)
        self.initUI()

    def initUI(self):
        layout = QFormLayout(self) # Assicurati che QFormLayout sia importato

        self.nome_comune_edit = QLineEdit()
        self.codice_catastale_edit = QLineEdit()
        self.codice_catastale_edit.setMaxLength(4)
        self.provincia_edit = QLineEdit("SV") # Valore predefinito
        self.provincia_edit.setMaxLength(2)

        self.data_istituzione_edit = QDateEdit()
        self.data_istituzione_edit.setCalendarPopup(True)
        self.data_istituzione_edit.setDisplayFormat("yyyy-MM-dd")
        # La riga .setNullable(True) è stata rimossa
        self.data_istituzione_edit.setDate(QDate()) # Imposta una data nulla/invalida inizialmente
        self.data_istituzione_edit.setSpecialValueText(" ") # Mostra come vuoto se la data non è valida

        self.data_soppressione_edit = QDateEdit()
        self.data_soppressione_edit.setCalendarPopup(True)
        self.data_soppressione_edit.setDisplayFormat("yyyy-MM-dd")
        # La riga .setNullable(True) è stata rimossa
        self.data_soppressione_edit.setDate(QDate()) # Imposta una data nulla/invalida inizialmente
        self.data_soppressione_edit.setSpecialValueText(" ") # Mostra come vuoto se la data non è valida

        self.note_edit = QTextEdit()

        layout.addRow("Nome Comune (*):", self.nome_comune_edit)
        layout.addRow("Codice Catastale:", self.codice_catastale_edit)
        layout.addRow("Provincia (*):", self.provincia_edit)
        layout.addRow("Data Istituzione:", self.data_istituzione_edit)
        layout.addRow("Data Soppressione:", self.data_soppressione_edit)
        layout.addRow("Note:", self.note_edit)

        self.submit_button = QPushButton("Inserisci Comune")
        self.submit_button.clicked.connect(self.inserisci_comune)
        self.clear_button = QPushButton("Pulisci Campi")
        self.clear_button.clicked.connect(self.pulisci_campi)
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.cancel_button)

        layout.addRow(button_layout)
        self.setLayout(layout)

    def pulisci_campi(self):
        self.nome_comune_edit.clear()
        self.codice_catastale_edit.clear()
        self.provincia_edit.setText("SV")
        self.data_istituzione_edit.setDate(QDate())
        self.data_istituzione_edit.setSpecialValueText(" ")
        self.data_soppressione_edit.setDate(QDate())
        self.data_soppressione_edit.setSpecialValueText(" ")
        self.note_edit.clear()

    def inserisci_comune(self):
        nome_comune = self.nome_comune_edit.text().strip()
        codice_catastale = self.codice_catastale_edit.text().strip().upper() # Converti in maiuscolo
        provincia = self.provincia_edit.text().strip().upper() # Converti in maiuscolo

        data_istituzione = None
        if self.data_istituzione_edit.date().isValid() and not self.data_istituzione_edit.date().isNull():
            data_istituzione = self.data_istituzione_edit.date().toPyDate()

        data_soppressione = None
        if self.data_soppressione_edit.date().isValid() and not self.data_soppressione_edit.date().isNull():
            data_soppressione = self.data_soppressione_edit.date().toPyDate()

        note = self.note_edit.toPlainText().strip()

        if not nome_comune:
            QMessageBox.warning(self, "Errore Inserimento", "Il nome del comune è obbligatorio.")
            return
        if not provincia:
            QMessageBox.warning(self, "Errore Inserimento", "La provincia è obbligatoria.")
            return
        if len(provincia) != 2:
            QMessageBox.warning(self, "Errore Inserimento", "La provincia deve essere di 2 caratteri (es. SV).")
            return
        if codice_catastale and len(codice_catastale) != 4:
            QMessageBox.warning(self, "Errore Inserimento", "Il codice catastale deve essere di 4 caratteri (es. L781).")
            return
        # Controllo aggiuntivo per il formato del codice catastale (una lettera seguita da tre numeri)
        if codice_catastale and not (codice_catastale[0].isalpha() and codice_catastale[1:].isdigit() and len(codice_catastale) == 4) :
             QMessageBox.warning(self, "Errore Inserimento", "Il codice catastale deve iniziare con una lettera seguita da tre cifre (es. L781).")
             return

        try:
            # Assicurati che il tuo db_manager sia accessibile come self.db
            # e che utente_attuale sia disponibile come self.utente_attuale
            comune_id = self.db.aggiungi_comune(
                nome_comune=nome_comune,
                codice_catastale=codice_catastale if codice_catastale else None,
                provincia=provincia,
                data_istituzione=data_istituzione,
                data_soppressione=data_soppressione,
                note=note if note else None,
                utente=self.utente_attuale
            )

            if comune_id:
                QMessageBox.information(self, "Successo", f"Comune '{nome_comune}' inserito con ID: {comune_id}.")
                # Eventuale segnale per aggiornare altre viste
                # self.comune_aggiunto.emit() # Se si implementa un segnale
                self.pulisci_campi()
                self.accept() # Chiude il dialogo
            else:
                # Questo potrebbe non essere mai raggiunto se aggiungi_comune solleva sempre eccezioni in caso di fallimento
                QMessageBox.critical(self, "Errore Inserimento", "Impossibile inserire il comune. Il metodo nel DB manager non ha restituito un ID.")

        except ValueError as ve: # Esempio di gestione errore specifico da db_manager
            QMessageBox.critical(self, "Errore Dati", f"Errore nei dati forniti: {ve}")
        except Exception as e: # Gestione generica per altri errori (es. DB)
            # Potresti voler loggare l'errore completo e mostrare un messaggio più generico
            # logger.error(f"Errore database durante inserimento comune: {e}", exc_info=True)
            messaggio = f"Errore durante l'inserimento del comune: {e}"
            if "comuni_nome_comune_key" in str(e).lower():
                messaggio = f"Errore: Esiste già un comune con il nome '{nome_comune}'."
            elif "comuni_codice_catastale_key" in str(e).lower():
                 messaggio = f"Errore: Esiste già un comune con il codice catastale '{codice_catastale}'."
            QMessageBox.critical(self, "Errore Database", messaggio)

class AuditWidget(QWidget): # Esempio
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Widget Audit Log (TODO)"))

class BackupWidget(QWidget): # Esempio
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Widget Backup (TODO)"))


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
        dialog = LocalitaSelectionDialog(self.db_manager, self.selected_comune_id, self) # Usa LocalitaSelectionDialog
        dialog.setWindowTitle(f"Seleziona Località per Comune ID: {self.selected_comune_id}")
        if dialog.exec_() == QDialog.Accepted and dialog.selected_localita_id:
            self.selected_localita_id = dialog.selected_localita_id
            self.localita_display_label.setText(f"{dialog.selected_localita_name} (ID: {self.selected_localita_id})")
        elif not self.selected_localita_id:
            self.localita_display_label.setText("Qualsiasi località")

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
        self.inserimento_main_tab = QTabWidget()
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
    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        self.nuovo_comune_action = QAction(QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder), "Nuovo &Comune...", self)
        self.nuovo_comune_action.setStatusTip("Registra un nuovo comune nel sistema")
        self.nuovo_comune_action.triggered.connect(self.apri_dialog_inserimento_comune)
        # self.nuovo_comune_action.setEnabled(False) # L'abilitazione è gestita da update_ui_based_on_role
        file_menu.addAction(self.nuovo_comune_action)

        file_menu.addSeparator() # Separatore

        # Azione per Uscire
        exit_action = QAction(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton), "&Esci", self)
        exit_action.setStatusTip("Chiudi l'applicazione")
        exit_action.triggered.connect(self.close) # Chiama il metodo close della finestra
        file_menu.addAction(exit_action)

        # Puoi aggiungere altri menu e azioni qui (es. "Amministrazione" > "Gestione Utenti")
        # if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin':
        #     admin_menu = menu_bar.addMenu("&Amministrazione")
        #     gestione_utenti_action = QAction("Gestione &Utenti", self)
        #     # gestione_utenti_action.triggered.connect(self.mostra_tab_gestione_utenti) # Dovresti creare questo metodo
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

        db_name = "N/D"
        if hasattr(self.db_manager, 'conn_params') and self.db_manager.conn_params: # Controllo robustezza
            db_name = self.db_manager.conn_params.get('dbname', 'N/D')
        self.db_status_label.setText(f"Database: Connesso ({db_name})")

        user_display = self.logged_in_user_info.get('nome_completo') or self.logged_in_user_info.get('username', 'N/D') # Assicurati che logged_in_user_info sia impostato
        self.statusBar().showMessage(f"Login come {user_display} effettuato con successo.")

         # ---> AGGIUNGI QUESTA RIGA PER DEFINIRE ruolo_display <---
        ruolo_display = self.logged_in_user_info.get('ruolo', 'N/D') 
        
        self.user_status_label.setText(f"Utente: {user_display} (ID: {self.logged_in_user_id}, Ruolo: {ruolo_display})")

        self.logout_button.setEnabled(True)
        # L'abilitazione di btn_nuovo_comune_toolbar è gestita da update_ui_based_on_role

        self.statusBar().showMessage(f"Login come {user_display} effettuato con successo.")
        self.setup_tabs() # Configura i tab
        self.update_ui_based_on_role() # Applica i permessi UI subito dopo aver impostato i tab
        self.show()
        
        gui_logger.info(">>> CatastoMainWindow: Chiamata a setup_tabs")
        self.setup_tabs()
        gui_logger.info(">>> CatastoMainWindow: Chiamata a update_ui_based_on_role")
        self.update_ui_based_on_role()

        gui_logger.info(">>> CatastoMainWindow: Chiamata a self.show()")
        self.show() # <-- ESSENZIALE
        gui_logger.info(">>> CatastoMainWindow: self.show() completato. Fine perform_initial_setup")

    def setup_tabs(self):
        if not self.db_manager:
            gui_logger.error("Tentativo di configurare i tab senza un db_manager.")
            QMessageBox.critical(self, "Errore Critico", "DB Manager non inizializzato. Impossibile caricare i tab.")
            return
        self.tabs.clear() # Pulisce i tab esistenti prima di ricrearli

        # --- Tab Consultazione (QTabWidget per contenere sotto-tab) ---
        self.consultazione_sub_tabs.clear() # Pulisce i sotto-tab precedenti
        self.consultazione_sub_tabs.addTab(ElencoComuniWidget(self.db_manager, self.consultazione_sub_tabs), "Elenco Comuni")
        self.consultazione_sub_tabs.addTab(RicercaPartiteWidget(self.db_manager, self.consultazione_sub_tabs), "Ricerca Partite")
        self.consultazione_sub_tabs.addTab(RicercaPossessoriWidget(self.db_manager, self.consultazione_sub_tabs), "Ricerca Possessori")
        self.consultazione_sub_tabs.addTab(RicercaAvanzataImmobiliWidget(self.db_manager, self.consultazione_sub_tabs), "Ricerca Immobili Avanzata")
        self.tabs.addTab(self.consultazione_sub_tabs, "Consultazione")

        # --- Tab Inserimento e Gestione (QTabWidget per sotto-tab) ---
        self.inserimento_main_tab.clear()
        self.inserimento_main_tab.addTab(InserimentoPossessoreWidget(self.db_manager, self.inserimento_main_tab), "Nuovo Possessore")
        self.inserimento_main_tab.addTab(InserimentoLocalitaWidget(self.db_manager, self.inserimento_main_tab), "Nuova Località")
        self.inserimento_main_tab.addTab(RegistrazioneProprietaWidget(self.db_manager, self.inserimento_main_tab), "Registra Proprietà")
        # Nota: InserimentoComuneWidget è gestito come dialogo modale, non un tab.
        self.tabs.addTab(self.inserimento_main_tab, "Inserimento e Gestione")

        # --- Tab Ricerca Avanzata Possessori (se diverso da quello in Consultazione) ---
        # Questo widget (RicercaAvanzataWidget) è quello per la ricerca fuzzy dei possessori
        self.tabs.addTab(RicercaAvanzataWidget(self.db_manager, self), "Ricerca Avanzata Possessori")

        # --- Tab Esportazioni ---
        self.tabs.addTab(EsportazioniWidget(self.db_manager, self), "Esportazioni")

        # --- Tab Reportistica ---
        self.tabs.addTab(ReportisticaWidget(self.db_manager, self), "Reportistica")

        # --- Tab Statistiche e Viste Materializzate ---
        self.tabs.addTab(StatisticheWidget(self.db_manager, self), "Statistiche e Viste")

        # --- Tab Gestione Utenti (solo per admin) ---
        # Questo tab viene aggiunto condizionatamente, quindi non serve disabilitarlo in update_ui_based_on_role se non esiste
        if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin':
            self.tabs.addTab(GestioneUtentiWidget(self.db_manager, self.logged_in_user_info, self), "Gestione Utenti")

        # --- Tab Sistema (placeholder per Audit, Backup) ---
        sistema_sub_tabs = QTabWidget()
        placeholder_sistema = QWidget(sistema_sub_tabs)
        placeholder_sistema_layout = QVBoxLayout(placeholder_sistema)
        placeholder_sistema_layout.addWidget(QLabel("Funzionalità di Sistema (Audit, Backup, Manutenzione) da implementare qui."))
        sistema_sub_tabs.addTab(placeholder_sistema, "Info Sistema")
        # Esempio se si avessero i widget pronti:
        # if hasattr(self, 'AuditWidget'): sistema_sub_tabs.addTab(AuditWidget(self.db_manager, sistema_sub_tabs), "Audit Log")
        # if hasattr(self, 'BackupWidget'): sistema_sub_tabs.addTab(BackupWidget(self.db_manager, sistema_sub_tabs), "Backup")
        self.tabs.addTab(sistema_sub_tabs, "Sistema")

        # Non è necessario chiamare self.update_ui_based_on_role() qui,
        # perché viene chiamato in perform_initial_setup DOPO setup_tabs.

    def update_ui_based_on_role(self):
        if not self.logged_in_user_info:
            for i in range(self.tabs.count()):
                self.tabs.setTabEnabled(i, False)
            # self.btn_nuovo_comune_toolbar.setEnabled(False) # RIMOSSO O MODIFICATO
            if hasattr(self, 'nuovo_comune_action'): # Controlla se l'azione del menu esiste
                self.nuovo_comune_action.setEnabled(False)
            # if hasattr(self, 'menuBar'): self.menuBar().setEnabled(False) # Se hai un menu bar
            return

        # if hasattr(self, 'menuBar'): self.menuBar().setEnabled(True)

        is_admin = self.logged_in_user_info.get('ruolo') == 'admin'
        is_archivista = self.logged_in_user_info.get('ruolo') == 'archivista'

        # Abilita/Disabilita l'azione del menu "Nuovo Comune"
        if hasattr(self, 'nuovo_comune_action'): # Controlla se l'azione del menu esiste
            self.nuovo_comune_action.setEnabled(is_admin or is_archivista)
        
        # Rimuovi la riga che si riferisce a self.btn_nuovo_comune_toolbar
        # self.btn_nuovo_comune_toolbar.setEnabled(is_admin or is_archivista) # RIMOSSA

        # Mappa dei nomi dei tab ai loro indici attuali per riferimento
        tab_indices = {self.tabs.tabText(i): i for i in range(self.tabs.count())}

        # Logica di abilitazione dei tab principali
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
            self.tabs.setTabEnabled(tab_indices["Sistema"], is_admin) # Solo admin per funzioni di sistema critiche

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


    def closeEvent(self, event: QCloseEvent): # Specificare il tipo dell'evento
        gui_logger.info("Evento closeEvent intercettato.")
        # Registra il logout se l'utente chiude la finestra mentre è loggato
        if self.logged_in_user_id and self.current_session_id and self.db_manager:
            gui_logger.info(f"Chiusura applicazione: esecuzione logout di sicurezza per utente ID: {self.logged_in_user_id}...")
            self.db_manager.logout_user(self.logged_in_user_id, self.current_session_id, client_ip_address_gui) #

        if self.db_manager:
            self.db_manager.disconnect()
            gui_logger.info("Connessione al database chiusa.")

        gui_logger.info("Applicazione GUI Catasto Storico terminata.")
        # QApplication.instance().quit() # Non sempre necessario qui se event.accept() è chiamato
        event.accept() # Conferma la chiusura della finestra

# --- Fine Classe CatastoMainWindow ---

def run_gui_app():
    app = QApplication(sys.argv)
    
    # Applica UN SOLO stylesheet principale all'avvio
    app.setStyleSheet("""
        * { 
            font-size: 10pt; /* Dimensione font globale */
        }
        QMainWindow {
            background-color: #353535; /* Esempio: Sfondo scuro per coerenza con la palette */
            /* Se usi una QPalette per QPalette.Window, potresti non aver bisogno di questo */
        }
        QPushButton {
            background-color: #4CAF50; 
            color: white;
            border-radius: 5px;
            padding: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3e8e41;
        }
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #2E2E2E; /* Sfondo scuro per input */
            color: #E0E0E0; /* Testo chiaro per input */
            border: 1px solid #505050;
            border-radius: 3px;
            padding: 3px;
        }
        QLabel {
            color: #E0E0E0; /* Testo chiaro per etichette */
        }
        QTabWidget::pane { 
            border-top: 2px solid #505050;
            margin-top: -1px; 
        }
        QTabBar::tab { 
            background: #3E3E3E;
            color: #E0E0E0;
            border: 1px solid #505050;
            border-bottom-color: #505050; 
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            min-width: 8ex;
            padding: 3px 5px;
        }
        QTabBar::tab:selected, QTabBar::tab:hover {
            background: #4A4A4A;
            color: white;
        }
        QTabBar::tab:selected {
            border-color: #606060;
            border-bottom-color: #4A4A4A; 
        }
        QTableWidget {
            gridline-color: #505050; 
            background-color: #2E2E2E;
            color: #E0E0E0;
            alternate-background-color: #353535; 
        }
        QHeaderView::section { 
            background-color: #3E3E3E;
            color: #E0E0E0;
            padding: 4px;
            border: 1px solid #505050;
            font-weight: bold;
        }
        QToolTip { /* Stile per i ToolTip tramite QSS */
            background-color: #555555;
            color: white;
            border: 1px solid #666666;
            padding: 2px;
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
    db_manager_gui = CatastoDBManager(**db_config_gui)

    if not db_manager_gui.connect():
        QMessageBox.critical(None, "Errore Connessione Database",
                             "Impossibile connettersi al database.\n"
                             "Verifica i parametri di connessione e che il server PostgreSQL sia in esecuzione.\n"
                             "L'applicazione verrà chiusa.")
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
                db_manager_gui.disconnect()
                sys.exit(1) # Uscita critica
        else: # LoginDialog è stato chiuso o cancellato
            gui_logger.info("Login annullato o fallito. Uscita dall'applicazione GUI.")
            if db_manager_gui: db_manager_gui.disconnect()
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
            db_manager_gui.disconnect()
        sys.exit(1)

    
if __name__ == "__main__":
     # Il logging dovrebbe essere configurato qui se non già fatto altrove all'inizio del file
     # Esempio:
 if not gui_logger.hasHandlers():
     log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
...# (resto della configurazione del logger) ...

run_gui_app()