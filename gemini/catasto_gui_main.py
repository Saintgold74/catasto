#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Applicazione Principale Gestionale Catasto Storico
==================================================
Autore: Marco Santoro
Data: 18/05/2025
Versione: 1.2

Questo file contiene la finestra principale e la logica
di avvio dell'applicazione GUI.
"""

import sys
import logging
from typing import Optional, Dict
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QLabel, QTabWidget,
                            QMessageBox, QFrame, QStyle, QDialog,QAction,
                            QFileDialog, QLineEdit, QTextEdit, QSpinBox,
                            QDoubleSpinBox, QDateEdit)
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtGui import QCloseEvent

# Importa tutti i dialoghi e widget dal file separato
from catasto_gui_dialogs import *

# Import DB Manager
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

# --- Funzioni di esportazione adattate per GUI ---
def gui_esporta_partita_json(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    dict_data = db_manager.get_partita_data_for_export(partita_id) 
    
    if dict_data:
        def json_serial(obj):
            """JSON serializer per oggetti non serializzabili di default (date/datetime)."""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        
        try:
            json_data_str = json.dumps(dict_data, indent=4, ensure_ascii=False, default=json_serial)
        except TypeError as te:
            gui_logger.error(f"Errore di serializzazione JSON per partita ID {partita_id}: {te} - Dati: {dict_data}")
            QMessageBox.critical(parent_widget, "Errore di Serializzazione", 
                                 f"Errore durante la conversione dei dati della partita in JSON: {te}\n"
                                 "Controllare i log per i dettagli.")
            return

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

            if possessore_data.get('partite'):
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
            'Comune Riferimento': p_info.get('comune_nome'),
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

# --- Finestra principale ---
class CatastoMainWindow(QMainWindow):
    def __init__(self):
        super(CatastoMainWindow, self).__init__()
        self.db_manager: Optional[CatastoDBManager] = None
        self.logged_in_user_id: Optional[int] = None
        self.logged_in_user_info: Optional[Dict] = None
        self.current_session_id: Optional[str] = None

        # Inizializzazione dei QTabWidget per i sotto-tab
        self.consultazione_sub_tabs = QTabWidget()
        self.inserimento_sub_tabs = QTabWidget()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Gestionale Catasto Storico - Archivio di Stato Savona")
        self.setMinimumSize(1280, 720)
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)

        self.create_status_bar_content()
        self.create_menu_bar()

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        self.setCentralWidget(self.central_widget)

        self.statusBar().showMessage("Pronto.")

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        exit_action = QAction(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton), "&Esci", self)
        exit_action.setStatusTip("Chiudi l'applicazione")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def create_status_bar_content(self):
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setFrameShadow(QFrame.Sunken)
        status_layout = QHBoxLayout(status_frame)

        self.db_status_label = QLabel("Database: Non connesso")
        self.user_status_label = QLabel("Utente: Nessuno")

        self.logout_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton), "Logout")
        self.logout_button.setToolTip("Effettua il logout dell'utente corrente")
        self.logout_button.clicked.connect(self.handle_logout)
        self.logout_button.setEnabled(False)

        status_layout.addWidget(self.db_status_label)
        status_layout.addSpacing(20)
        status_layout.addWidget(self.user_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.logout_button)
        self.main_layout.addWidget(status_frame)

    def perform_initial_setup(self, db_manager: CatastoDBManager, user_id: int, user_info: Dict, session_id: str):
        gui_logger.info(">>> CatastoMainWindow: Inizio perform_initial_setup")
        self.db_manager = db_manager
        self.logged_in_user_id = user_id
        self.logged_in_user_info = user_info
        self.current_session_id = session_id

        # Aggiornamento etichetta stato DB
        db_name_to_display = "ERRORE_NOME_DB"
        connection_seems_ok = False

        if self.db_manager and self.db_manager.pool:
            gui_logger.info("DEBUG perform_initial_setup: db_manager e pool esistono.")
            if hasattr(self.db_manager, '_conn_params_dict') and self.db_manager._conn_params_dict:
                db_name_to_display = self.db_manager._conn_params_dict.get('dbname', 'N/D')
                gui_logger.info(f"DEBUG perform_initial_setup: db_name recuperato: {db_name_to_display}")
            else:
                gui_logger.warning("DEBUG perform_initial_setup: db_manager non ha _conn_params_dict o è vuoto.")
            
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

        # Aggiornamento etichetta utente
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

    def setup_tabs(self):
        if not self.db_manager:
            gui_logger.error("Tentativo di configurare i tab senza un db_manager.")
            QMessageBox.critical(self, "Errore Critico", "DB Manager non inizializzato.")
            return
        self.tabs.clear()

        # Tab Consultazione
        self.consultazione_sub_tabs.clear()
        self.consultazione_sub_tabs.addTab(ElencoComuniWidget(self.db_manager, self.consultazione_sub_tabs), "Elenco Comuni")
        self.consultazione_sub_tabs.addTab(RicercaPartiteWidget(self.db_manager, self.consultazione_sub_tabs), "Ricerca Partite")
        self.consultazione_sub_tabs.addTab(RicercaPossessoriWidget(self.db_manager, self.consultazione_sub_tabs), "Ricerca Avanzata Possessori")
        self.consultazione_sub_tabs.addTab(RicercaAvanzataImmobiliWidget(self.db_manager, self.consultazione_sub_tabs), "Ricerca Immobili Avanzata")
        self.tabs.addTab(self.consultazione_sub_tabs, "Consultazione e Modifica")

        # Tab Inserimento e Gestione
        inserimento_gestione_contenitore = QWidget()
        layout_contenitore_inserimento = QVBoxLayout(inserimento_gestione_contenitore)

        if not hasattr(self, 'inserimento_sub_tabs') or not isinstance(self.inserimento_sub_tabs, QTabWidget):
            self.inserimento_sub_tabs = QTabWidget()

        utente_per_inserimenti = self.logged_in_user_info if self.logged_in_user_info else {}

        self.inserimento_sub_tabs.addTab(
            InserimentoComuneWidget(
                parent=self.inserimento_sub_tabs, 
                db_manager=self.db_manager, 
                utente_attuale_info=utente_per_inserimenti
            ), 
            "Nuovo Comune"
        )
        self.inserimento_sub_tabs.addTab(InserimentoPossessoreWidget(self.db_manager, self.inserimento_sub_tabs), "Nuovo Possessore")
        self.inserimento_sub_tabs.addTab(InserimentoLocalitaWidget(self.db_manager, self.inserimento_sub_tabs), "Nuova Località")
        self.inserimento_sub_tabs.addTab(RegistrazioneProprietaWidget(self.db_manager, self.inserimento_sub_tabs), "Registra Proprietà")
        self.inserimento_sub_tabs.addTab(OperazioniPartitaWidget(self.db_manager, self.inserimento_sub_tabs), "Operazioni su Partita")
       
        layout_contenitore_inserimento.addWidget(self.inserimento_sub_tabs)
        self.tabs.addTab(inserimento_gestione_contenitore, "Inserimento e Gestione")

        # Tab Esportazioni
        self.tabs.addTab(EsportazioniWidget(self.db_manager, self), "Esportazioni")

        # Tab Reportistica
        self.tabs.addTab(ReportisticaWidget(self.db_manager, self), "Reportistica")

        # Tab Statistiche e Viste Materializzate
        self.tabs.addTab(StatisticheWidget(self.db_manager, self), "Statistiche e Viste")

        # Tab Gestione Utenti (solo per admin)
        if self.logged_in_user_info and self.logged_in_user_info.get('ruolo') == 'admin':
            self.tabs.addTab(GestioneUtentiWidget(self.db_manager, self.logged_in_user_info, self), "Gestione Utenti")

        # Tab Sistema
        sistema_sub_tabs = QTabWidget()

        if self.db_manager:
            self.audit_viewer_widget = AuditLogViewerWidget(self.db_manager, sistema_sub_tabs)
            sistema_sub_tabs.addTab(self.audit_viewer_widget, "Log di Audit")

            self.backup_restore_widget = BackupRestoreWidget(self.db_manager, sistema_sub_tabs)
            sistema_sub_tabs.addTab(self.backup_restore_widget, "Backup/Ripristino")
        else:
            error_widget_audit = QLabel("Errore: DB Manager non inizializzato per il Log di Audit.")
            sistema_sub_tabs.addTab(error_widget_audit, "Log di Audit")
            error_widget_backup = QLabel("Errore: DB Manager non inizializzato per Backup/Ripristino.")
            sistema_sub_tabs.addTab(error_widget_backup, "Backup/Ripristino")

        self.tabs.addTab(sistema_sub_tabs, "Sistema")

    def update_ui_based_on_role(self):
        if not self.logged_in_user_info:
            for i in range(self.tabs.count()):
                self.tabs.setTabEnabled(i, False)
            if hasattr(self, 'btn_nuovo_comune_nel_tab'):
                self.btn_nuovo_comune_nel_tab.setEnabled(False)
            return

        is_admin = self.logged_in_user_info.get('ruolo') == 'admin'
        is_archivista = self.logged_in_user_info.get('ruolo') == 'archivista'

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

    def handle_logout(self):
        if self.logged_in_user_id and self.current_session_id and self.db_manager:
            if self.db_manager.logout_user(self.logged_in_user_id, self.current_session_id, client_ip_address_gui):
                QMessageBox.information(self, "Logout", "Logout effettuato con successo.")
            else:
                QMessageBox.warning(self, "Logout Fallito", "Errore durante la registrazione del logout.")

            self.logged_in_user_id = None
            self.logged_in_user_info = None
            self.current_session_id = None
            if self.db_manager: self.db_manager.clear_session_app_user()

            self.user_status_label.setText("Utente: Nessuno")
            self.db_status_label.setText("Database: Connesso (Logout effettuato)")
            self.logout_button.setEnabled(False)

            for i in range(self.tabs.count()):
                self.tabs.setTabEnabled(i, False)
            self.tabs.clear()

            self.statusBar().showMessage("Logout effettuato. Riavviare l'applicazione per un nuovo login.")
            self.close()
        else:
            gui_logger.warning("Tentativo di logout senza una sessione utente o db_manager validi.")

    def closeEvent(self, event: QCloseEvent):
        gui_logger.info("Evento closeEvent intercettato in CatastoMainWindow.")

        # Esegui il logout dell'utente applicativo se loggato
        if hasattr(self, 'logged_in_user_id') and self.logged_in_user_id and \
           hasattr(self, 'current_session_id') and self.current_session_id and \
           hasattr(self, 'db_manager') and self.db_manager:
            gui_logger.info(f"Chiusura applicazione: esecuzione logout di sicurezza per utente ID: {self.logged_in_user_id}...")
            self.db_manager.logout_user(self.logged_in_user_id, self.current_session_id, client_ip_address_gui)
            self.db_manager.clear_audit_session_variables() 

        # Chiudi il pool di connessioni del database
        if hasattr(self, 'db_manager') and self.db_manager:
            self.db_manager.close_pool() 
            gui_logger.info("Pool di connessioni al database chiuso.")

        gui_logger.info("Applicazione GUI Catasto Storico terminata.")
        event.accept()

# --- Funzione principale per avviare l'applicazione ---
def run_gui_app():
    app = QApplication(sys.argv)
    
    # Applica UN SOLO stylesheet principale all'avvio
    app.setStyleSheet("""
        * {
            font-size: 10pt;
            color: #202020;
        }
        QMainWindow {
            background-color: #F0F0F0;
        }
        QWidget {
            background-color: #F0F0F0;
        }

        /* ----- Etichette ----- */
        QLabel {
            color: #101010;
            background-color: transparent;
        }

        /* ----- Campi di Input ----- */
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit {
            background-color: #FFFFFF;
            color: #202020;
            border: 1px solid #B0B0B0;
            border-radius: 3px;
            padding: 4px;
        }
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
            border: 1px solid #0078D7;
        }

        /* ----- Pulsanti ----- */
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: 1px solid #3E8E41;
            border-radius: 5px;
            padding: 6px 12px;
            font-weight: bold;
            min-width: 70px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3e8e41;
        }
        QPushButton:disabled {
            background-color: #D0D0D0;
            color: #808080;
            border-color: #B0B0B0;
        }

        /* ----- Tabs ----- */
        QTabWidget::pane {
            border: 1px solid #C0C0C0;
            border-top: none;
            background-color: #F8F8F8;
        }

        QTabBar::tab {
            background: #E0E0E0;
            color: #303030;
            border-top: 1px solid #C0C0C0;
            border-left: 1px solid #C0C0C0;
            border-right: 1px solid #C0C0C0;
            border-bottom: 1px solid #C0C0C0;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            min-width: 8ex;
            padding: 6px 9px;
            margin-right: 1px;
        }

        QTabBar::tab:hover {
            background: #D5D5D5;
            color: #101010;
        }

        QTabBar::tab:selected {
            background: #F8F8F8;
            color: #000000;
            font-weight: bold;
            border-top: 1px solid #C0C0C0;
            border-left: 1px solid #C0C0C0;
            border-right: 1px solid #C0C0C0;
            border-bottom: 1px solid #F8F8F8;
        }

        /* ----- Tabelle ----- */
        QTableWidget {
            gridline-color: #D0D0D0;
            background-color: #FFFFFF;
            color: #202020;
            alternate-background-color: #F5F5F5;
            selection-background-color: #0078D7;
            selection-color: white;
            border: 1px solid #C0C0C0;
        }
        QHeaderView::section {
            background-color: #E8E8E8;
            color: #202020;
            padding: 5px;
            border: 1px solid #C0C0C0;
            border-bottom-width: 2px;
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
        QComboBox::drop-down {
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
            width: 10px;
            height: 10px;
        }
        QComboBox QAbstractItemView {
            background-color: #FFFFFF;
            color: #202020;
            border: 1px solid #B0B0B0;
            selection-background-color: #0078D7;
            selection-color: white;
            outline: 0px;
            padding: 2px;
        }

        /* ----- ToolTips ----- */
        QToolTip {
            background-color: #FFFFE0;
            color: black;
            border: 1px solid #B0B0B0;
            padding: 3px;
        }

        /* ----- QMessageBox ----- */
        QMessageBox {
            background-color: #F0F0F0;
        }
        QMessageBox QLabel {
            color: #202020;
            background-color: transparent;
        }

        /* ----- QMenuBar e QMenu ----- */
        QMenuBar {
            background-color: #E8E8E8;
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
            background: #C0C0C0;
        }
        QMenu {
            background-color: #FFFFFF;
            color: #202020;
            border: 1px solid #B0B0B0;
            padding: 4px;
        }
        QMenu::item {
            padding: 5px 25px 5px 25px;
            border-radius: 3px;
        }
        QMenu::item:selected {
            background-color: #0078D7;
            color: white;
        }
        QMenu::separator {
            height: 1px;
            background: #D0D0D0;
            margin: 4px 0px 4px 0px;
        }
        QMenu::icon {
            padding-left: 5px;
        }

        /* ----- ScrollArea e ScrollBar ----- */
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
            background-color: #F5F5F5;
            border: 1px solid #C0C0C0;
            border-radius: 4px;
            margin-top: 2ex;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px 0 5px;
            left: 10px;
            color: #101010;
        }
        QCheckBox {
            spacing: 5px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #B0B0B0;
            border-radius: 3px;
            background-color: white;
        }
        QCheckBox::indicator:checked {
            background-color: #4CAF50;
            border-color: #3E8E41;
        }
        QCheckBox::indicator:disabled {
            background-color: #E0E0E0;
            border-color: #C0C0C0;
        }
        QFrame#status_frame {
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

    db_manager_gui = CatastoDBManager(
        dbname=db_config_gui["dbname"], 
        user=db_config_gui["user"], 
        password=db_config_gui["password"],
        host=db_config_gui["host"], 
        port=db_config_gui["port"],
        schema=db_config_gui.get("schema", "catasto"),
        application_name="CatastoAppGUI_Main",
        log_file="catasto_main_db.log",
        log_level=logging.DEBUG,
        min_conn=1,
        max_conn=5
    )

    # Verifica se il pool è stato inizializzato con successo
    if db_manager_gui.pool is None:
        QMessageBox.critical(None, "Errore Inizializzazione Database",
                             "Impossibile inizializzare il pool di connessioni al database.\n"
                             "Verifica i parametri di connessione, che il server PostgreSQL sia in esecuzione e i log dell'applicazione.\n"
                             "L'applicazione verrà chiusa.")
        sys.exit(1)
    else:
        # Test di connessione iniziale
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

    main_window_instance = None
    login_success = False

    while not login_success:
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
                QMessageBox.critical(None, "Errore Login", "Dati di login non validi ricevuti dal dialogo.")
                db_manager_gui.close_pool()
                sys.exit(1)
        else:
            gui_logger.info("Login annullato o fallito. Uscita dall'applicazione GUI.")
            if db_manager_gui: db_manager_gui.close_pool()
            sys.exit(0)
            
    if main_window_instance and login_success:
        gui_logger.info(">>> run_gui_app: Login successo, preparazione per app.exec_()")
        gui_logger.info(">>> run_gui_app: STA PER ESSERE CHIAMATO app.exec_()")
        exit_code = app.exec_()
        gui_logger.info(f">>> run_gui_app: app.exec_() TERMINATO con codice: {exit_code}")
        sys.exit(exit_code)
    else:
        gui_logger.error("Avvio dell'applicazione fallito: main_window_instance non inizializzata o login non riuscito prima di app.exec_().")
        if db_manager_gui:
            db_manager_gui.close_pool()
        sys.exit(1)

    
if __name__ == "__main__":
    # Il logging dovrebbe essere configurato qui se non già fatto altrove all'inizio del file
    if not gui_logger.hasHandlers():
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        # Aggiungi qui la configurazione completa del logger se necessario
    
    run_gui_app()