#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaccia Grafica per Gestionale Catasto Storico
=================================================
Questo script fornisce un'interfaccia grafica per l'utilizzo del
Gestionale Catasto Storico, basandosi sulle funzionalità
implementate in catasto_db_manager.py e sfruttate in python_example.py.

Autore: [Nome Utente]
Data: 14/05/2025
Versione: 1.0
"""

import sys
import os
import logging
import getpass
import json
import bcrypt
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QComboBox, QTabWidget, QTextEdit, QMessageBox,
                            QCheckBox, QGroupBox, QGridLayout, QTableWidget,
                            QTableWidgetItem, QDateEdit, QScrollArea, 
                            QStackedWidget, QFrame, QDialog, QListWidget,
                            QListWidgetItem, QFileDialog, QSplitter, QStyle, QStyleFactory, QSpinBox)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette

# Importa catasto_db_manager
try:
    from catasto_db_manager import CatastoDBManager
except ImportError:
    print("ERRORE: Non è possibile importare CatastoDBManager. Assicurati che catasto_db_manager.py sia nella stessa directory.")
    sys.exit(1)

# --- Configurazione Logging ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("catasto_gui.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Variabili Globali per Sessione Utente ---
logged_in_user_id: Optional[int] = None
current_session_id: Optional[str] = None
# Simula IP client, da ottenere dinamicamente in un'app reale
client_ip_address: str = "127.0.0.1"

# --- Funzioni Helper per Password ---
def _hash_password(password: str) -> str:
    """Funzione helper per hashare la password usando bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

def _verify_password(stored_hash: str, provided_password: str) -> bool:
    """Funzione helper per verificare la password usando bcrypt."""
    try:
        stored_hash_bytes = stored_hash.encode('utf-8')
        provided_password_bytes = provided_password.encode('utf-8')
        return bcrypt.checkpw(provided_password_bytes, stored_hash_bytes)
    except ValueError:
        logger.error(f"Tentativo di verifica con hash non valido: {stored_hash[:10]}...")
        return False
    except Exception as e:
        logger.error(f"Errore imprevisto durante la verifica bcrypt: {e}")
        return False

# --- Password LineEdit personalizzato ---
class QPasswordLineEdit(QLineEdit):
    """LineEdit specializzato per password con visibilità toggle."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        
        # Aggiunge pulsante per mostrare/nascondere la password
        self.toggleAction = self.addAction(
            QApplication.style().standardIcon(QStyle.SP_DialogYesButton),
            QLineEdit.TrailingPosition
        )
        self.toggleAction.triggered.connect(self.toggle_password_visibility)
        
    def toggle_password_visibility(self):
        if self.echoMode() == QLineEdit.Password:
            self.setEchoMode(QLineEdit.Normal)
            self.toggleAction.setIcon(
                QApplication.style().standardIcon(QStyle.SP_DialogNoButton)
            )
        else:
            self.setEchoMode(QLineEdit.Password)
            self.toggleAction.setIcon(
                QApplication.style().standardIcon(QStyle.SP_DialogYesButton)
            )

# --- Finestra di Login ---
class LoginDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super(LoginDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.successful_login = False
        self.user_id = None
        self.session_id = None
        
        self.setWindowTitle("Login - Catasto Storico")
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout()
        
        # Credenziali
        form_layout = QGridLayout()
        
        username_label = QLabel("Username:")
        self.username_edit = QLineEdit()
        form_layout.addWidget(username_label, 0, 0)
        form_layout.addWidget(self.username_edit, 0, 1)
        
        password_label = QLabel("Password:")
        self.password_edit = QPasswordLineEdit()
        form_layout.addWidget(password_label, 1, 0)
        form_layout.addWidget(self.password_edit, 1, 1)
        
        # Ricorda credenziali
        self.remember_checkbox = QCheckBox("Ricorda credenziali")
        form_layout.addWidget(self.remember_checkbox, 2, 0, 1, 2)
        
        # Aggiungi un frame per il form
        form_frame = QFrame()
        form_frame.setLayout(form_layout)
        form_frame.setFrameShape(QFrame.Box)
        form_frame.setFrameShadow(QFrame.Sunken)
        
        layout.addWidget(form_frame)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.handle_login)
        self.login_button.setAutoDefault(True)
        self.login_button.setDefault(True)
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def handle_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Errore di Login", "Username e password sono obbligatori.")
            return
        
        credentials = self.db_manager.get_user_credentials(username)
        login_success = False
        user_id = None
        
        if credentials:
            user_id = credentials['id']
            stored_hash = credentials['password_hash']
            logger.debug(f"Tentativo login per user ID {user_id}. Hash: {stored_hash[:10]}...")
            
            if _verify_password(stored_hash, password):
                login_success = True
                logger.info(f"Login OK per ID: {user_id}")
            else:
                QMessageBox.critical(self, "Errore di Login", "Password errata.")
                logger.warning(f"Login fallito (pwd errata) per ID: {user_id}")
                return
        else:
            QMessageBox.critical(self, "Errore di Login", "Utente non trovato o non attivo.")
            logger.warning(f"Login fallito (utente '{username}' non trovato/attivo).")
            return
        
        if user_id is not None:
            session_id_returned = self.db_manager.register_access(
                user_id, 'login', indirizzo_ip=client_ip_address, esito=login_success
            )
            
            if login_success and session_id_returned:
                self.successful_login = True
                self.user_id = user_id
                self.session_id = session_id_returned
                if not self.db_manager.set_session_app_user(self.user_id, client_ip_address):
                    logger.error("Impossibile impostare contesto DB post-login!")
                QMessageBox.information(self, "Login Riuscito", f"Benvenuto! Sessione {session_id_returned[:8]}... avviata.")
                self.accept()
            elif login_success and not session_id_returned:
                error_msg = "Errore critico: Impossibile registrare sessione accesso."
                QMessageBox.critical(self, "Errore di Login", error_msg)
                logger.error(f"Login OK per ID {user_id} ma fallita reg. accesso.")
                self.reject()

# --- Finestra di Creazione Utente ---
class CreateUserDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super(CreateUserDialog, self).__init__(parent)
        self.db_manager = db_manager
        
        self.setWindowTitle("Crea Nuovo Utente")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        form_layout = QGridLayout()
        
        # Username
        username_label = QLabel("Username:")
        self.username_edit = QLineEdit()
        form_layout.addWidget(username_label, 0, 0)
        form_layout.addWidget(self.username_edit, 0, 1)
        
        # Password
        password_label = QLabel("Password:")
        self.password_edit = QPasswordLineEdit()
        form_layout.addWidget(password_label, 1, 0)
        form_layout.addWidget(self.password_edit, 1, 1)
        
        # Conferma Password
        confirm_label = QLabel("Conferma Password:")
        self.confirm_edit = QPasswordLineEdit()
        form_layout.addWidget(confirm_label, 2, 0)
        form_layout.addWidget(self.confirm_edit, 2, 1)
        
        # Nome Completo
        nome_label = QLabel("Nome Completo:")
        self.nome_edit = QLineEdit()
        form_layout.addWidget(nome_label, 3, 0)
        form_layout.addWidget(self.nome_edit, 3, 1)
        
        # Email
        email_label = QLabel("Email:")
        self.email_edit = QLineEdit()
        form_layout.addWidget(email_label, 4, 0)
        form_layout.addWidget(self.email_edit, 4, 1)
        
        # Ruolo
        ruolo_label = QLabel("Ruolo:")
        self.ruolo_combo = QComboBox()
        self.ruolo_combo.addItems(["admin", "archivista", "consultatore"])
        form_layout.addWidget(ruolo_label, 5, 0)
        form_layout.addWidget(self.ruolo_combo, 5, 1)
        
        frame = QFrame()
        frame.setLayout(form_layout)
        frame.setFrameShape(QFrame.Box)
        frame.setFrameShadow(QFrame.Sunken)
        
        layout.addWidget(frame)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        self.create_button = QPushButton("Crea Utente")
        self.create_button.clicked.connect(self.handle_create_user)
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.create_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def handle_create_user(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        confirm = self.confirm_edit.text()
        nome_completo = self.nome_edit.text().strip()
        email = self.email_edit.text().strip()
        ruolo = self.ruolo_combo.currentText()
        
        # Validazione
        if not all([username, password, nome_completo, email, ruolo]):
            QMessageBox.warning(self, "Errore", "Tutti i campi sono obbligatori.")
            return
        
        if password != confirm:
            QMessageBox.warning(self, "Errore", "Le password non coincidono.")
            return
        
        try:
            password_hash = _hash_password(password)
            logger.debug(f"Hash generato per {username}")
            
            if self.db_manager.create_user(username, password_hash, nome_completo, email, ruolo):
                QMessageBox.information(self, "Successo", f"Utente '{username}' creato con successo.")
                self.accept()
            else:
                QMessageBox.critical(self, "Errore", f"Errore creazione utente '{username}' (controllare log - es. duplicato).")
        except Exception as hash_err:
            logger.error(f"Errore hashing password per {username}: {hash_err}")
            QMessageBox.critical(self, "Errore", "Errore tecnico nella gestione della password.")

# --- Selettore di Comune con finestra dialog ---
class ComuneSelectionDialog(QDialog):
    def __init__(self, db_manager, parent=None, title="Seleziona Comune"):
        super(ComuneSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.selected_comune_id = None
        self.selected_comune_name = None
        
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout()
        
        # Campo di ricerca
        search_layout = QHBoxLayout()
        search_label = QLabel("Filtra comuni:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Digita per filtrare...")
        self.search_edit.textChanged.connect(self.filter_comuni)
        self.search_button = QPushButton("Cerca")
        self.search_button.clicked.connect(self.filter_comuni)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_button)
        
        layout.addLayout(search_layout)
        
        # Lista comuni
        self.comuni_list = QListWidget()
        self.comuni_list.setAlternatingRowColors(True)
        self.comuni_list.itemDoubleClicked.connect(self.handle_select)
        layout.addWidget(self.comuni_list)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Seleziona")
        self.select_button.clicked.connect(self.handle_select)
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.select_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # Carica comuni inizialmente
        self.load_comuni()
    
    def load_comuni(self, filter_text=None):
        """Carica i comuni dal database con filtro opzionale."""
        self.comuni_list.clear()
        comuni = self.db_manager.get_comuni(filter_text)
        
        if comuni:
            for comune in comuni:
                item = QListWidgetItem(f"{comune['nome']} (ID: {comune['id']}, {comune['provincia']})")
                # Salva l'id del comune come dato utente
                item.setData(Qt.UserRole, comune['id'])
                self.comuni_list.addItem(item)
        else:
            self.comuni_list.addItem("Nessun comune trovato.")
    
    def filter_comuni(self):
        """Filtra la lista dei comuni in base al testo inserito."""
        filter_text = self.search_edit.text().strip()
        self.load_comuni(filter_text if filter_text else None)
    
    def handle_select(self):
        """Gestisce la selezione di un comune dalla lista."""
        current_item = self.comuni_list.currentItem()
        if current_item and current_item.data(Qt.UserRole):
            self.selected_comune_id = current_item.data(Qt.UserRole)
            self.selected_comune_name = current_item.text().split(" (ID:")[0]
            self.accept()
        else:
            QMessageBox.warning(self, "Attenzione", "Seleziona un comune valido.")

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

# --- Dialogo Dettagli Partita ---
class PartitaDetailsDialog(QDialog):
    def __init__(self, partita_data, parent=None):
        super(PartitaDetailsDialog, self).__init__(parent)
        self.partita = partita_data
        
        self.setWindowTitle(f"Dettagli Partita {partita_data['numero_partita']}")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
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
        partita_id = self.partita['id']
        
        # Usa QFileDialog per selezionare il percorso del file
        file_path, _ = QFileDialog.getSaveFileName(self, "Salva JSON", f"partita_{partita_id}.json", "JSON files (*.json)")
        
        if file_path:
            try:
                # Converti il dizionario in stringa JSON formattata
                json_str = json.dumps(self.partita, indent=4, ensure_ascii=False)
                
                # Scrivi sul file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                
                QMessageBox.information(self, "Esportazione Completata", f"I dati sono stati salvati in {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante l'esportazione: {str(e)}")

# --- Scheda per Inserimento Possessore ---
class InserimentoPossessoreWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(InserimentoPossessoreWidget, self).__init__(parent)
        self.db_manager = db_manager
        
        layout = QVBoxLayout()
        
        # Form di inserimento
        form_group = QGroupBox("Inserimento Nuovo Possessore")
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
        
        # Cognome e nome
        cognome_label = QLabel("Cognome e nome:")
        self.cognome_edit = QLineEdit()
        
        form_layout.addWidget(cognome_label, 1, 0)
        form_layout.addWidget(self.cognome_edit, 1, 1, 1, 2)
        
        # Paternità
        paternita_label = QLabel("Paternità:")
        self.paternita_edit = QLineEdit()
        self.paternita_edit.setPlaceholderText("es. 'fu Roberto'")
        
        form_layout.addWidget(paternita_label, 2, 0)
        form_layout.addWidget(self.paternita_edit, 2, 1, 1, 2)
        
        # Nome completo
        nome_completo_label = QLabel("Nome completo:")
        self.nome_completo_edit = QLineEdit()
        self.nome_completo_update_button = QPushButton("Genera da cognome+paternità")
        self.nome_completo_update_button.clicked.connect(self.update_nome_completo)
        
        form_layout.addWidget(nome_completo_label, 3, 0)
        form_layout.addWidget(self.nome_completo_edit, 3, 1)
        form_layout.addWidget(self.nome_completo_update_button, 3, 2)
        
        # Stato attivo
        attivo_label = QLabel("Attivo:")
        self.attivo_checkbox = QCheckBox()
        self.attivo_checkbox.setChecked(True)
        
        form_layout.addWidget(attivo_label, 4, 0)
        form_layout.addWidget(self.attivo_checkbox, 4, 1)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Pulsante inserimento
        insert_button = QPushButton("Inserisci Possessore")
        insert_button.clicked.connect(self.insert_possessore)
        layout.addWidget(insert_button)
        
        # Riepilogo possessori del comune selezionato
        summary_group = QGroupBox("Possessori nel Comune Selezionato")
        summary_layout = QVBoxLayout()
        
        self.refresh_button = QPushButton("Aggiorna Lista")
        self.refresh_button.clicked.connect(self.refresh_possessori)
        
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(4)
        self.possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Paternità", "Stato"])
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.horizontalHeader().setStretchLastSection(True)
        
        summary_layout.addWidget(self.refresh_button)
        summary_layout.addWidget(self.possessori_table)
        
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
            # Aggiorna la lista dei possessori per il comune selezionato
            self.refresh_possessori()
    
    def update_nome_completo(self):
        """Aggiorna il nome completo in base a cognome e paternità."""
        cognome = self.cognome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()
        
        if cognome:
            nome_completo = cognome
            if paternita:
                nome_completo += f" {paternita}"
            
            self.nome_completo_edit.setText(nome_completo)
    
    def insert_possessore(self):
        """Inserisce un nuovo possessore."""
        # Valida i dati di input
        if not self.comune_id:
            QMessageBox.warning(self, "Errore", "Seleziona un comune.")
            return
        
        cognome_nome = self.cognome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()
        nome_completo = self.nome_completo_edit.text().strip()
        attivo = self.attivo_checkbox.isChecked()
        
        if not cognome_nome:
            QMessageBox.warning(self, "Errore", "Il cognome e nome è obbligatorio.")
            return
        
        if not nome_completo:
            QMessageBox.warning(self, "Errore", "Il nome completo è obbligatorio.")
            return
        
        # Inserisci possessore
        possessore_id = self.db_manager.insert_possessore(
            self.comune_id, cognome_nome, paternita, nome_completo, attivo
        )
        
        if possessore_id:
            QMessageBox.information(self, "Successo", f"Possessore '{nome_completo}' inserito con ID: {possessore_id}")
            
            # Pulisci i campi
            self.cognome_edit.clear()
            self.paternita_edit.clear()
            self.nome_completo_edit.clear()
            
            # Aggiorna la lista dei possessori
            self.refresh_possessori()
        else:
            QMessageBox.critical(self, "Errore", "Errore durante l'inserimento del possessore.")
    
    def refresh_possessori(self):
        """Aggiorna la lista dei possessori per il comune selezionato."""
        self.possessori_table.setRowCount(0)
        
        if self.comune_id:
            possessori = self.db_manager.get_possessori_by_comune(self.comune_id)
            
            if possessori:
                self.possessori_table.setRowCount(len(possessori))
                
                for i, pos in enumerate(possessori):
                    self.possessori_table.setItem(i, 0, QTableWidgetItem(str(pos.get('id', ''))))
                    self.possessori_table.setItem(i, 1, QTableWidgetItem(pos.get('nome_completo', '')))
                    self.possessori_table.setItem(i, 2, QTableWidgetItem(pos.get('paternita', '')))
                    
                    stato = "Attivo" if pos.get('attivo') else "Non Attivo"
                    self.possessori_table.setItem(i, 3, QTableWidgetItem(stato))
            
            self.possessori_table.resizeColumnsToContents()

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

# --- Finestra principale ---
class CatastoMainWindow(QMainWindow):
    def __init__(self):
        super(CatastoMainWindow, self).__init__()
        
        self.db_manager = None
        self.initUI()
        self.connect_to_database()
    
    def initUI(self):
        self.setWindowTitle("Gestionale Catasto Storico")
        self.setMinimumSize(1000, 700)
        
        # Widget centrale
        self.central_widget = QWidget()
        self.central_layout = QVBoxLayout()
        
        # Area di stato
        self.create_status_area()
        
        # Tabs principali
        self.tabs = QTabWidget()
        
        # I tab effettivi verranno aggiunti dopo la connessione al database
        
        self.central_layout.addWidget(self.tabs)
        self.central_widget.setLayout(self.central_layout)
        self.setCentralWidget(self.central_widget)
        
        # Barra di stato
        self.statusBar().showMessage("Pronto")
    
    def create_status_area(self):
        """Crea l'area di stato in alto."""
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.Box)
        status_frame.setFrameShadow(QFrame.Sunken)
        status_layout = QHBoxLayout()
        
        self.db_status_label = QLabel("Database: Non connesso")
        self.user_status_label = QLabel("Utente: Nessuno")
        
        self.connect_button = QPushButton("Connetti")
        self.connect_button.clicked.connect(self.connect_to_database)
        
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.handle_login)
        self.login_button.setEnabled(False)
        
        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.handle_logout)
        self.logout_button.setEnabled(False)
        
        status_layout.addWidget(self.db_status_label)
        status_layout.addWidget(self.user_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.connect_button)
        status_layout.addWidget(self.login_button)
        status_layout.addWidget(self.logout_button)
        
        status_frame.setLayout(status_layout)
        self.central_layout.addWidget(status_frame)
    
    def connect_to_database(self):
        """Connette al database."""
        try:
            # Usa valori predefiniti da catasto_db_manager.py
            self.db_manager = CatastoDBManager(
                dbname="catasto_storico", 
                user="postgres", 
                password="Markus74", 
                host="localhost", 
                port=5432, 
                schema="catasto"
            )
            
            if self.db_manager.connect():
                self.db_status_label.setText("Database: Connesso")
                self.connect_button.setText("Riconnetti")
                self.login_button.setEnabled(True)
                
                self.statusBar().showMessage("Connessione al database stabilita")
                
                # Inizializza i tab dopo la connessione
                self.setup_tabs()
            else:
                QMessageBox.critical(self, "Errore", "Impossibile connettersi al database.")
                self.db_status_label.setText("Database: ERRORE")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore durante la connessione: {str(e)}")
            logger.error(f"Errore connessione database: {e}")
    
    def setup_tabs(self):
        """Configura i tab principali dopo la connessione."""
        # Pulisce i tab esistenti
        self.tabs.clear()
        
        # Tab Consultazione
        consultazione_tab = QTabWidget()
        
        # Sotto-tab di Consultazione
        consultazione_tab.addTab(RicercaPartiteWidget(self.db_manager), "Ricerca Partite")
        
        # Aggiungi altri sotto-tab di consultazione qui...
        
        self.tabs.addTab(consultazione_tab, "Consultazione")
        
        # Tab Inserimento
        inserimento_tab = QTabWidget()
        
        # Sotto-tab di Inserimento
        inserimento_tab.addTab(InserimentoPossessoreWidget(self.db_manager), "Inserisci Possessore")
        inserimento_tab.addTab(InserimentoLocalitaWidget(self.db_manager), "Inserisci Località")
        
        # Aggiungi altri sotto-tab di inserimento qui...
        
        self.tabs.addTab(inserimento_tab, "Inserimento")
        
        # Tab Reportistica
        reportistica_tab = QTabWidget()
        
        # Aggiungi sotto-tab di reportistica qui...
        
        self.tabs.addTab(reportistica_tab, "Reportistica")
        
        # Tab Statistiche
        self.tabs.addTab(StatisticheWidget(self.db_manager), "Statistiche")
        
        # Tab Utenti
        utenti_tab = QWidget()
        utenti_layout = QVBoxLayout()
        
        create_user_button = QPushButton("Crea Nuovo Utente")
        create_user_button.clicked.connect(self.create_new_user)
        
        utenti_layout.addWidget(create_user_button)
        utenti_layout.addStretch()
        
        utenti_tab.setLayout(utenti_layout)
        self.tabs.addTab(utenti_tab, "Utenti")
    
    def handle_login(self):
        """Gestisce il login utente."""
        global logged_in_user_id, current_session_id
        
        if not self.db_manager:
            QMessageBox.warning(self, "Attenzione", "Connettiti prima al database.")
            return
        
        login_dialog = LoginDialog(self.db_manager, self)
        result = login_dialog.exec_()
        
        if result == QDialog.Accepted and login_dialog.successful_login:
            logged_in_user_id = login_dialog.user_id
            current_session_id = login_dialog.session_id
            
            self.user_status_label.setText(f"Utente: ID {logged_in_user_id}")
            self.login_button.setEnabled(False)
            self.logout_button.setEnabled(True)
            
            self.statusBar().showMessage("Login effettuato con successo")
    
    def handle_logout(self):
        """Gestisce il logout utente."""
        global logged_in_user_id, current_session_id
        
        if logged_in_user_id and current_session_id and self.db_manager:
            if self.db_manager.logout_user(logged_in_user_id, current_session_id, client_ip_address):
                QMessageBox.information(self, "Logout", "Logout effettuato con successo.")
            else:
                QMessageBox.warning(self, "Attenzione", "Errore durante il logout.")
            
            logged_in_user_id = None
            current_session_id = None
            
            self.user_status_label.setText("Utente: Nessuno")
            self.login_button.setEnabled(True)
            self.logout_button.setEnabled(False)
            
            self.statusBar().showMessage("Logout effettuato")
    
    def create_new_user(self):
        """Apre la finestra di creazione nuovo utente."""
        if not self.db_manager:
            QMessageBox.warning(self, "Attenzione", "Connettiti prima al database.")
            return
        
        create_dialog = CreateUserDialog(self.db_manager, self)
        create_dialog.exec_()
    
    def closeEvent(self, event):
        """Gestisce la chiusura dell'applicazione."""
        global logged_in_user_id, current_session_id
        
        # Esegui logout automatico se necessario
        if logged_in_user_id and current_session_id and self.db_manager:
            self.db_manager.logout_user(logged_in_user_id, current_session_id, client_ip_address)
            logged_in_user_id = None
            current_session_id = None
        
        # Chiudi la connessione database
        if self.db_manager:
            self.db_manager.disconnect()
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))  # Stile moderno
    
    # Imposta un tema più moderno
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    mainWindow = CatastoMainWindow()
    mainWindow.show()
    sys.exit(app.exec_())