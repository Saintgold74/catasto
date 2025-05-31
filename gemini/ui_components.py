#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Componenti UI per Gestionale Catasto Storico
============================================
Autore: Marco Santoro
Data: 31/05/2025
Versione: 1.0
"""

import logging
import json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

# Importazioni PyQt5
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QLabel, QLineEdit,
                            QComboBox, QTabWidget, QTextEdit, QMessageBox,
                            QCheckBox, QGroupBox, QGridLayout, QTableWidget,
                            QTableWidgetItem, QDateEdit, QScrollArea,
                            QDialog, QListWidget, QDateTimeEdit,
                            QListWidgetItem, QFileDialog, QStyle, QStyleFactory, QSpinBox,
                            QInputDialog, QHeaderView, QFrame, QAbstractItemView, QSizePolicy,
                            QFormLayout, QDialogButtonBox, QDoubleSpinBox, QMainWindow)
from PyQt5.QtCore import Qt, QDate, QSettings, QDateTime
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

# Importa le utilità
from utils import (gui_logger, _hash_password, _verify_password, 
                  qdate_to_datetime, datetime_to_qdate, FPDF_AVAILABLE)

# Importa riferimento al database manager
try:
    from catasto_db_manager import CatastoDBManager
except ImportError:
    gui_logger.error("Impossibile importare CatastoDBManager. Verificare l'installazione.")
    # Definizione di fallback per permettere l'esecuzione in fase di sviluppo
    class CatastoDBManager:
        pass

# Widget personalizzati base
class QPasswordLineEdit(QLineEdit):
    """Widget per l'input di password con asterischi."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)

# Widget per la tabella degli immobili
class ImmobiliTableWidget(QTableWidget):
    """Tabella per visualizzare dati relativi agli immobili."""
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
        self.setRowCount(0)  # Pulisce la tabella
        if not immobili:
            return
        
        for i, immobile in enumerate(immobili):
            self.insertRow(i)
            
            # ID immobile
            id_item = QTableWidgetItem(str(immobile.get('id', '')))
            id_item.setData(Qt.UserRole, immobile.get('id'))
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(i, 0, id_item)
            
            # Natura
            natura_item = QTableWidgetItem(str(immobile.get('natura', '')))
            natura_item.setFlags(natura_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(i, 1, natura_item)
            
            # Classificazione
            classif_item = QTableWidgetItem(str(immobile.get('classificazione', '')))
            classif_item.setFlags(classif_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(i, 2, classif_item)
            
            # Consistenza
            consist_item = QTableWidgetItem(str(immobile.get('consistenza', '')))
            consist_item.setFlags(consist_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(i, 3, consist_item)
            
            # Località
            localita_item = QTableWidgetItem(str(immobile.get('localita_nome', '')))
            localita_item.setFlags(localita_item.flags() & ~Qt.ItemIsEditable)
            self.setItem(i, 4, localita_item)
        
        # Ridimensiona colonne al contenuto
        self.resizeColumnsToContents()

# Dialoghi
class CreateUserDialog(QDialog):
    """Dialogo per la creazione di un nuovo utente."""
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
        """Gestisce la creazione dell'utente."""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        confirm = self.confirm_edit.text()
        nome = self.nome_edit.text().strip()
        email = self.email_edit.text().strip()
        ruolo = self.ruolo_combo.currentText()
        
        # Validazione
        if len(username) < 3:
            QMessageBox.warning(self, "Validazione", "Lo username deve essere di almeno 3 caratteri.")
            self.username_edit.setFocus()
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "Validazione", "La password deve essere di almeno 6 caratteri.")
            self.password_edit.setFocus()
            return
        
        if password != confirm:
            QMessageBox.warning(self, "Validazione", "Le password non corrispondono.")
            self.confirm_edit.setFocus()
            return
        
        if not nome:
            QMessageBox.warning(self, "Validazione", "Il nome completo è obbligatorio.")
            self.nome_edit.setFocus()
            return
        
        # Email opzionale ma deve avere formato corretto se presente
        if email and '@' not in email:
            QMessageBox.warning(self, "Validazione", "Email non valida.")
            self.email_edit.setFocus()
            return
        
        # Crea l'utente nel database
        try:
            user_data = {
                'username': username,
                'password_hash': _hash_password(password),
                'nome_completo': nome,
                'email': email,
                'ruolo': ruolo,
                'ultimo_accesso': None
            }
            new_user_id = self.db_manager.create_user(user_data)
            QMessageBox.information(self, "Utente Creato", 
                                  f"Utente {username} creato con successo (ID: {new_user_id}).")
            self.accept()  # Chiude il dialogo
        except Exception as e:
            # Gestisci le diverse eccezioni
            error_msg = str(e)
            if 'unique constraint' in error_msg.lower() and 'username' in error_msg.lower():
                QMessageBox.critical(self, "Errore", f"Username già in uso: {username}")
            else:
                QMessageBox.critical(self, "Errore", f"Errore durante la creazione dell'utente: {e}")

class LoginDialog(QDialog):
    """Dialogo per il login utente."""
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
        """Gestisce il processo di login."""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Login", "Inserisci username e password.")
            return
        
        try:
            # Verifica credenziali
            user_data = self.db_manager.get_user_by_username(username)
            if not user_data:
                QMessageBox.warning(self, "Login", "Username non trovato.")
                return
            
            stored_hash = user_data.get('password_hash')
            if not stored_hash or not _verify_password(stored_hash, password):
                QMessageBox.warning(self, "Login", "Password non valida.")
                return
            
            # Login valido
            self.logged_in_user_id = user_data.get('id')
            self.logged_in_user_info = user_data
            
            # Registra il login
            session_id = str(uuid.uuid4())
            self.current_session_id = session_id
            self.db_manager.register_login(self.logged_in_user_id, session_id)
            
            # Login completato con successo
            QMessageBox.information(self, "Login", 
                                   f"Benvenuto, {user_data.get('nome_completo')}!")
            self.accept()
            
        except Exception as e:
            gui_logger.exception(f"Errore durante il login: {e}")
            QMessageBox.critical(self, "Errore", f"Errore durante il login: {e}")

class ComuneSelectionDialog(QDialog):
    """Dialogo per la selezione di un comune."""
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
        """Carica la lista dei comuni, opzionalmente filtrata."""
        try:
            comuni = self.db_manager.get_comuni_list(filter_text)
            self.comuni_list.clear()
            for comune in comuni:
                item = QListWidgetItem(f"{comune['nome']} ({comune['provincia']})")
                item.setData(Qt.UserRole, comune)
                self.comuni_list.addItem(item)
            
            if not comuni:
                self.comuni_list.addItem("Nessun comune trovato")
        except Exception as e:
            gui_logger.exception(f"Errore nel caricamento comuni: {e}")
            QMessageBox.critical(self, "Errore", f"Errore nel caricamento comuni: {e}")

    def filter_comuni(self):
        """Filtra la lista dei comuni in base al testo inserito."""
        filter_text = self.search_edit.text().strip()
        self.load_comuni(filter_text)

    def handle_select(self):
        """Gestisce la selezione di un comune dalla lista."""
        current_item = self.comuni_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Selezione", "Seleziona un comune dalla lista.")
            return
        
        comune_data = current_item.data(Qt.UserRole)
        if not isinstance(comune_data, dict):  # Potrebbe essere il messaggio "Nessun comune trovato"
            QMessageBox.warning(self, "Selezione", "Nessun comune valido selezionato.")
            return
        
        self.selected_comune_id = comune_data.get('id')
        self.selected_comune_name = comune_data.get('nome')
        self.accept()
