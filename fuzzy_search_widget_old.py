#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Widget per Ricerca Fuzzy nel Database Catasto
==============================================
File: fuzzy_search_widget.py
Autore: Marco Santoro
Data: 10/06/2025
Versione: 2.0 (con export TXT/PDF e dettagli migliorati)
"""

import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QGroupBox,
    QSlider, QCheckBox, QComboBox, QProgressBar, QFrame, QHeaderView,
    QMessageBox, QApplication, QFileDialog, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont

# Import estensione GIN per ricerca fuzzy
try:
    from catasto_gin_extension import extend_db_manager_with_gin
    GIN_AVAILABLE = True
    print("DEBUG: Importazione GIN riuscita")
except ImportError as e:
    GIN_AVAILABLE = False
    extend_db_manager_with_gin = None
    print(f"DEBUG: Errore importazione GIN: {e}")
except Exception as e:
    GIN_AVAILABLE = False
    extend_db_manager_with_gin = None
    print(f"DEBUG: Errore generico importazione: {e}")
class FuzzySearchThread(QThread):
    """Thread per eseguire ricerche fuzzy in background."""
    
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, gin_search, query_text, threshold, max_results, search_options):
        super().__init__()
        self.gin_search = gin_search
        self.query_text = query_text
        self.threshold = threshold
        self.max_results = max_results
        self.search_options = search_options
        
    def run(self):
        """Esegue la ricerca fuzzy."""
        try:
            self.progress_updated.emit(10)
            
            results = {}
            total_steps = sum(1 for option, enabled in self.search_options.items() if enabled)
            current_step = 0
            
            # Ricerca possessori
            if self.search_options.get('possessori', True):
                current_step += 1
                self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                possessori = self.gin_search.search_possessori_fuzzy(
                    self.query_text, self.threshold, self.max_results
                )
                results['possessori'] = possessori or []
            
            # Ricerca località
            if self.search_options.get('localita', True):
                current_step += 1
                self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                localita = self.gin_search.search_localita_fuzzy(
                    self.query_text, self.threshold, self.max_results
                )
                results['localita'] = localita or []
            
            # Ricerca variazioni
            if self.search_options.get('variazioni', True):
                current_step += 1
                self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                variazioni = self.gin_search.search_variazioni_fuzzy(
                    self.query_text, self.threshold, self.max_results
                )
                results['variazioni'] = variazioni or []
            
            # Ricerca immobili
            if self.search_options.get('immobili', True):
                current_step += 1
                self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                immobili = self.gin_search.search_immobili_fuzzy(
                    self.query_text, self.threshold, self.max_results
                )
                results['immobili'] = immobili or []
            
            # Ricerca contratti
            if self.search_options.get('contratti', True):
                current_step += 1
                self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                contratti = self.gin_search.search_contratti_fuzzy(
                    self.query_text, self.threshold, self.max_results
                )
                results['contratti'] = contratti or []
            
            # Ricerca partite
            if self.search_options.get('partite', True):
                current_step += 1
                self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                partite = self.gin_search.search_partite_fuzzy(
                    self.query_text, self.threshold, self.max_results
                )
                results['partite'] = partite or []
            
            self.progress_updated.emit(90)
            
            # Aggiungi metadati
            results['query_text'] = self.query_text
            results['threshold'] = self.threshold
            results['timestamp'] = datetime.now()
            
            self.progress_updated.emit(100)
            self.results_ready.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class CompactFuzzySearchWidget(QWidget):
    """Widget compatto per ricerca fuzzy con layout ottimizzato."""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent
        self.logger = logging.getLogger(__name__)
        
        # Inizializza componenti GIN
        
        self.gin_search = None
        if GIN_AVAILABLE and db_manager:
            try:
                self.extended_db_manager = extend_db_manager_with_gin(db_manager)
                self.gin_search = self.extended_db_manager  # Usa il db_manager esteso
            except Exception as e:
                self.logger.error(f"Errore inizializzazione GIN search: {e}")        
        # Variabili di stato
        self.current_results = {}
        self.search_thread = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        
        # Setup UI
        self._setup_ui()
        self._setup_signals()
        self._check_gin_status()
        
    def _setup_ui(self):
        """Configura l'interfaccia utente."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        # === AREA CONTROLLI ===
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setSpacing(6)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        
        # Prima riga: ricerca e precisione
        search_row = QHBoxLayout()
        
        search_row.addWidget(QLabel("Ricerca:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Inserisci testo da cercare (min. 3 caratteri)...")
        self.search_edit.setMinimumWidth(300)
        search_row.addWidget(self.search_edit)
        
        search_row.addWidget(QLabel("Precisione:"))
        
        self.precision_slider = QSlider(Qt.Horizontal)
        self.precision_slider.setRange(10, 90)
        self.precision_slider.setValue(30)
        self.precision_slider.setMaximumWidth(100)
        search_row.addWidget(self.precision_slider)
        
        self.precision_label = QLabel("30%")
        self.precision_label.setMinimumWidth(35)
        search_row.addWidget(self.precision_label)
        
        search_row.addWidget(QLabel("Max:"))
        
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["50", "100", "200", "500"])
        self.max_results_combo.setCurrentText("100")
        self.max_results_combo.setMaximumWidth(60)
        search_row.addWidget(self.max_results_combo)
        
        search_row.addStretch()
        controls_layout.addLayout(search_row)
        
        # Seconda riga: opzioni ricerca
        options_row = QHBoxLayout()
        
        self.search_possessori_cb = QCheckBox("👥 Possessori")
        self.search_possessori_cb.setChecked(True)
        options_row.addWidget(self.search_possessori_cb)
        
        self.search_localita_cb = QCheckBox("🏘️ Località")
        self.search_localita_cb.setChecked(True)
        options_row.addWidget(self.search_localita_cb)
        
        self.search_variazioni_cb = QCheckBox("📋 Variazioni")
        self.search_variazioni_cb.setChecked(True)
        options_row.addWidget(self.search_variazioni_cb)
        
        self.search_immobili_cb = QCheckBox("🏢 Immobili")
        self.search_immobili_cb.setChecked(True)
        options_row.addWidget(self.search_immobili_cb)
        
        self.search_contratti_cb = QCheckBox("📄 Contratti")
        self.search_contratti_cb.setChecked(True)
        options_row.addWidget(self.search_contratti_cb)
        
        self.search_partite_cb = QCheckBox("📊 Partite")
        self.search_partite_cb.setChecked(True)
        options_row.addWidget(self.search_partite_cb)
        
        options_row.addWidget(QLabel("|"))
        
        # Pulsanti export
        export_layout = QHBoxLayout()
        
        self.export_txt_button = QPushButton("Esporta in TXT")
        self.export_txt_button.setEnabled(False)
        self.export_txt_button.clicked.connect(self._export_results_txt)
        export_layout.addWidget(self.export_txt_button)
        
        self.export_pdf_button = QPushButton("Esporta in PDF")
        self.export_pdf_button.setEnabled(False)
        self.export_pdf_button.clicked.connect(self._export_results_pdf)
        export_layout.addWidget(self.export_pdf_button)
        
        options_row.addLayout(export_layout)
        options_row.addStretch()
        controls_layout.addLayout(options_row)
        
        main_layout.addWidget(controls_frame)
        
        # === PROGRESS BAR ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # === TAB RISULTATI ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)
        
        # Tab Possessori
        self.possessori_tab = self._create_possessori_tab()
        self.results_tabs.addTab(self.possessori_tab, "👥 Possessori")
        
        # Tab Località
        self.localita_tab = self._create_localita_tab()
        self.results_tabs.addTab(self.localita_tab, "🏘️ Località")
        
        # Tab Variazioni
        self.variazioni_tab = self._create_variazioni_tab()
        self.results_tabs.addTab(self.variazioni_tab, "📋 Variazioni")
        
        # Tab Immobili
        self.immobili_tab = self._create_immobili_tab()
        self.results_tabs.addTab(self.immobili_tab, "🏢 Immobili")
        
        # Tab Contratti
        self.contratti_tab = self._create_contratti_tab()
        self.results_tabs.addTab(self.contratti_tab, "📄 Contratti")
        
        # Tab Partite
        self.partite_tab = self._create_partite_tab()
        self.results_tabs.addTab(self.partite_tab, "📊 Partite")
        
        main_layout.addWidget(self.results_tabs)
        
        # === STATUS BAR ===
        status_layout = QHBoxLayout()
        
        self.stats_label = QLabel("Inserire almeno 3 caratteri per iniziare")
        self.stats_label.setStyleSheet("color: gray; font-size: 11px;")
        status_layout.addWidget(self.stats_label)
        
        status_layout.addStretch()
        
        self.indices_status_label = QLabel("Verifica indici...")
        self.indices_status_label.setStyleSheet("color: orange; font-size: 10px;")
        status_layout.addWidget(self.indices_status_label)
        
        self.status_label = QLabel("Pronto")
        self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 10px;")
        status_layout.addWidget(self.status_label)
        
        main_layout.addLayout(status_layout)
        
        # === DEBUG AREA (compatta) ===
        debug_frame = QFrame()
        debug_frame.setFrameStyle(QFrame.StyledPanel)
        debug_layout = QVBoxLayout(debug_frame)
        debug_layout.setContentsMargins(4, 4, 4, 4)
        
        debug_header = QHBoxLayout()
        debug_header.addWidget(QLabel("Debug:"))
        debug_header.addStretch()
        
        clear_debug_btn = QPushButton("Pulisci")
        clear_debug_btn.setMaximumSize(60, 20)
        clear_debug_btn.clicked.connect(lambda: self.debug_text.clear())
        debug_header.addWidget(clear_debug_btn)
        
        debug_layout.addLayout(debug_header)
        
        self.debug_text = QTextEdit()
        self.debug_text.setMaximumHeight(80)
        self.debug_text.setStyleSheet("font-size: 9px;")
        debug_layout.addWidget(self.debug_text)
        
        main_layout.addWidget(debug_frame)
        
    def _create_possessori_tab(self):
        """Crea il tab per i possessori."""
        possessori_group = QGroupBox("👥 Possessori")
        layout = QVBoxLayout(possessori_group)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Tabella possessori
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(4)
        self.possessori_table.setHorizontalHeaderLabels([
            "Nome Completo", "Comune", "Partite", "Similitud."
        ])
        
        header = self.possessori_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.possessori_table)
        
        return possessori_group
    
    def _create_localita_tab(self):
        """Crea il tab per le località."""
        localita_group = QGroupBox("🏘️ Località")
        layout = QVBoxLayout(localita_group)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Tabella località
        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(4)
        self.localita_table.setHorizontalHeaderLabels([
            "Nome", "Comune", "Immobili", "Similitud."
        ])
        
        header = self.localita_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.localita_table.setAlternatingRowColors(True)
        self.localita_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.localita_table)
        
        return localita_group
    
    def _create_variazioni_tab(self):
        """Crea il tab per le variazioni."""
        variazioni_group = QGroupBox("📋 Variazioni")
        layout = QVBoxLayout(variazioni_group)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Tabella variazioni
        self.variazioni_table = QTableWidget()
        self.variazioni_table.setColumnCount(4)
        self.variazioni_table.setHorizontalHeaderLabels([
            "Tipo", "Data", "Descrizione", "Similitud."
        ])
        
        header = self.variazioni_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.variazioni_table.setAlternatingRowColors(True)
        self.variazioni_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.variazioni_table)
        
        return variazioni_group
    
    def _create_immobili_tab(self):
        """Crea il tab per gli immobili."""
        immobili_group = QGroupBox("🏢 Immobili")
        layout = QVBoxLayout(immobili_group)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Tabella immobili con più colonne
        self.immobili_table = QTableWidget()
        self.immobili_table.setColumnCount(6)  # Aumenta a 6 colonne
        self.immobili_table.setHorizontalHeaderLabels([
            "Natura", "Classificazione", "Partita", "Comune", "Località", "Similitud."
        ])
        
        header = self.immobili_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Natura
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Classificazione
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Partita
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Comune
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Località
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Similitud.
        
        self.immobili_table.setAlternatingRowColors(True)
        self.immobili_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.immobili_table)
        
        return immobili_group
    
    def _create_contratti_tab(self):
        """Crea il tab per i contratti."""
        contratti_group = QGroupBox("📄 Contratti")
        layout = QVBoxLayout(contratti_group)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Tabella contratti
        self.contratti_table = QTableWidget()
        self.contratti_table.setColumnCount(4)
        self.contratti_table.setHorizontalHeaderLabels([
            "Tipo", "Data Stipula", "Partita", "Similitud."
        ])
        
        header = self.contratti_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.contratti_table.setAlternatingRowColors(True)
        self.contratti_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.contratti_table)
        
        return contratti_group
    
    def _create_partite_tab(self):
        """Crea il tab per le partite."""
        partite_group = QGroupBox("📊 Partite")
        layout = QVBoxLayout(partite_group)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Tabella partite
        self.partite_table = QTableWidget()
        self.partite_table.setColumnCount(4)
        self.partite_table.setHorizontalHeaderLabels([
            "Numero", "Tipo", "Comune", "Similitud."
        ])
        
        header = self.partite_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.partite_table.setAlternatingRowColors(True)
        self.partite_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.partite_table)
        
        return partite_group
    
    def _setup_signals(self):
        """Configura i segnali."""
        # Ricerca in tempo reale
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        
        # Aggiornamento slider precisione
        self.precision_slider.valueChanged.connect(
            lambda v: self.precision_label.setText(f"{v}%")
        )
        self.precision_slider.valueChanged.connect(self._trigger_search_if_text)
        
        # Cambi opzioni rilanciano ricerca
        self.max_results_combo.currentTextChanged.connect(self._trigger_search_if_text)
        self.search_possessori_cb.toggled.connect(self._trigger_search_if_text)
        self.search_localita_cb.toggled.connect(self._trigger_search_if_text)
        self.search_variazioni_cb.toggled.connect(self._trigger_search_if_text)
        self.search_immobili_cb.toggled.connect(self._trigger_search_if_text)
        self.search_contratti_cb.toggled.connect(self._trigger_search_if_text)
        self.search_partite_cb.toggled.connect(self._trigger_search_if_text)
        
        # Doppio click per dettagli
        self.possessori_table.doubleClicked.connect(self._on_possessore_double_click)
        self.localita_table.doubleClicked.connect(self._on_localita_double_click)
        self.variazioni_table.doubleClicked.connect(self._on_variazione_double_click)
        self.immobili_table.doubleClicked.connect(self._on_immobile_double_click)
        self.contratti_table.doubleClicked.connect(self._on_contratto_double_click)
        self.partite_table.doubleClicked.connect(self._on_partita_double_click)
    
    def _check_gin_status(self):
        """Verifica stato indici GIN."""
        if not self.gin_search:
            self.indices_status_label.setText("❌ Non disponibile")
            return
            
        try:
            indices = self.gin_search.get_gin_indices_status() if hasattr(self.gin_search, 'get_gin_indices_status') else []
            if indices:
                self.indices_status_label.setText(f"✅ {len(indices)} indici")
                self.debug_text.append(f"✅ Indici GIN: {len(indices)} trovati")
            else:
                self.indices_status_label.setText("❌ Nessun indice")
                self.debug_text.append("❌ Nessun indice GIN")
                
        except Exception as e:
            self.indices_status_label.setText("❌ Errore verifica")
            self.debug_text.append(f"❌ Errore verifica indici: {e}")
    
    def _on_search_text_changed(self, text):
        """Gestisce cambiamenti nel testo di ricerca."""
        if len(text) >= 3:
            self.search_timer.start(500)  # Attesa 500ms prima di cercare
            self.stats_label.setText("Ricerca in corso...")
        else:
            self.search_timer.stop()
            self._clear_results()
            if len(text) == 0:
                self.stats_label.setText("Inserire almeno 3 caratteri per iniziare")
            else:
                self.stats_label.setText(f"Inserire almeno {3 - len(text)} caratteri")
    
    def _trigger_search_if_text(self):
        """Rilancia ricerca se c'è testo sufficiente."""
        if len(self.search_edit.text().strip()) >= 3:
            self.search_timer.start(200)
    
    def _perform_search(self):
        """Esegue la ricerca fuzzy."""
        query_text = self.search_edit.text().strip()
        if len(query_text) < 3:
            return
        # DEBUG: Aggiungi questo
        print(f"DEBUG: self.gin_search = {self.gin_search}")
        print(f"DEBUG: type(self.gin_search) = {type(self.gin_search)}")
        
        if not self.gin_search:
            QMessageBox.warning(self, "Errore", "Sistema di ricerca fuzzy non disponibile")
            return
        
        # Prepara parametri ricerca
        threshold = self.precision_slider.value() / 100.0
        max_results = int(self.max_results_combo.currentText())
        
        search_options = {
            'possessori': self.search_possessori_cb.isChecked(),
            'localita': self.search_localita_cb.isChecked(),
            'variazioni': self.search_variazioni_cb.isChecked(),
            'immobili': self.search_immobili_cb.isChecked(),
            'contratti': self.search_contratti_cb.isChecked(),
            'partite': self.search_partite_cb.isChecked()
        }
        
        # Avvia ricerca in thread separato
        if self.search_thread and self.search_thread.isRunning():
            return  # Ricerca già in corso
        
        self.progress_bar.setVisible(True)
        self.status_label.setText("🔍 Ricerca in corso...")
        self.status_label.setStyleSheet("color: blue; font-size: 10px;")
        
        self.search_thread = FuzzySearchThread(
            self.gin_search, query_text, threshold, max_results, search_options
        )
        self.search_thread.results_ready.connect(self._display_results)
        self.search_thread.error_occurred.connect(self._handle_search_error)
        self.search_thread.progress_updated.connect(self.progress_bar.setValue)
        self.search_thread.start()
        
        self.debug_text.append(f"🔍 Ricerca: '{query_text}' (soglia: {threshold:.2f})")
    
    def _display_results(self, results):
        """Visualizza i risultati della ricerca."""
        try:
            start_time = time.time()
            self.current_results = results
            
            # Popola le tabelle
            self._populate_possessori_table(results.get('possessori', []))
            self._populate_localita_table(results.get('localita', []))
            self._populate_variazioni_table(results.get('variazioni', []))
            self._populate_immobili_table(results.get('immobili', []))
            self._populate_contratti_table(results.get('contratti', []))
            self._populate_partite_table(results.get('partite', []))
            
            # Aggiorna contatori nei tab
            possessori_count = len(results.get('possessori', []))
            localita_count = len(results.get('localita', []))
            variazioni_count = len(results.get('variazioni', []))
            immobili_count = len(results.get('immobili', []))
            contratti_count = len(results.get('contratti', []))
            partite_count = len(results.get('partite', []))
            
            self.results_tabs.setTabText(0, f"👥 Possessori ({possessori_count})")
            self.results_tabs.setTabText(1, f"🏘️ Località ({localita_count})")
            self.results_tabs.setTabText(2, f"📋 Variazioni ({variazioni_count})")
            self.results_tabs.setTabText(3, f"🏢 Immobili ({immobili_count})")
            self.results_tabs.setTabText(4, f"📄 Contratti ({contratti_count})")
            self.results_tabs.setTabText(5, f"📊 Partite ({partite_count})")
            
            # Statistiche
            total = possessori_count + localita_count + variazioni_count + immobili_count + contratti_count + partite_count
            exec_time = time.time() - start_time
            threshold = results.get('threshold', 0)
            
            if total > 0:
                self.stats_label.setText(
                    f"Trovati {total} risultati "
                    f"(possessori: {possessori_count}, località: {localita_count}, "
                    f"variazioni: {variazioni_count}, immobili: {immobili_count}, "
                    f"contratti: {contratti_count}, partite: {partite_count}) "
                    f"in {exec_time:.3f}s [soglia: {threshold:.2f}]"
                )
            else:
                self.stats_label.setText("Nessun risultato trovato")
            
            # Abilita export se ci sono risultati
            self.export_txt_button.setEnabled(total > 0)
            self.export_pdf_button.setEnabled(total > 0)
            
            # Status finale
            if total > 0:
                self.status_label.setText(f"✅ {total} risultati trovati")
                self.status_label.setStyleSheet("color: green; font-size: 10px;")
            else:
                self.status_label.setText("ℹ️ Nessun risultato trovato")
                self.status_label.setStyleSheet("color: gray; font-size: 10px;")
                
        except Exception as e:
            self.logger.error(f"Errore visualizzazione risultati: {e}")
            self.status_label.setText("❌ Errore visualizzazione")
            self.status_label.setStyleSheet("color: red; font-size: 10px;")
        finally:
            self.progress_bar.setVisible(False)
    
    def _populate_possessori_table(self, possessori):
        """Popola la tabella dei possessori."""
        self.possessori_table.setRowCount(len(possessori))
        
        for row, p in enumerate(possessori):
            # Nome completo
            nome_item = QTableWidgetItem(p.get('nome_completo', ''))
            nome_item.setData(Qt.UserRole, p)
            self.possessori_table.setItem(row, 0, nome_item)
            
            # Comune
            self.possessori_table.setItem(row, 1, QTableWidgetItem(p.get('comune_nome', '')))
            
            # Numero partite
            num_partite = str(p.get('num_partite', 0))
            self.possessori_table.setItem(row, 2, QTableWidgetItem(num_partite))
            
            # Similarità con colore
            similarity = p.get('similarity_score', 0)
            sim_item = QTableWidgetItem(f"{similarity:.3f}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            if similarity > 0.7:
                sim_item.setBackground(QColor(144, 238, 144))
            elif similarity > 0.5:
                sim_item.setBackground(QColor(255, 255, 224))
            else:
                sim_item.setBackground(QColor(255, 228, 225))
            self.possessori_table.setItem(row, 3, sim_item)
    
    def _populate_localita_table(self, localita):
        """Popola la tabella delle località."""
        self.localita_table.setRowCount(len(localita))
        
        for row, l in enumerate(localita):
            # Nome con civico
            nome = l.get('nome', '')
            civico = l.get('civico', '')
            nome_completo = f"{nome} {civico}" if civico else nome
            nome_item = QTableWidgetItem(nome_completo)
            nome_item.setData(Qt.UserRole, l)
            self.localita_table.setItem(row, 0, nome_item)
            
            # Comune
            self.localita_table.setItem(row, 1, QTableWidgetItem(l.get('comune_nome', '')))
            
            # Numero immobili
            num_immobili = str(l.get('num_immobili', 0))
            self.localita_table.setItem(row, 2, QTableWidgetItem(num_immobili))
            
            # Similarità
            similarity = l.get('similarity_score', 0)
            sim_item = QTableWidgetItem(f"{similarity:.3f}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            if similarity > 0.7:
                sim_item.setBackground(QColor(144, 238, 144))
            elif similarity > 0.5:
                sim_item.setBackground(QColor(255, 255, 224))
            else:
                sim_item.setBackground(QColor(255, 228, 225))
            self.localita_table.setItem(row, 3, sim_item)
    
    def _populate_variazioni_table(self, variazioni):
        """Popola la tabella delle variazioni."""
        self.variazioni_table.setRowCount(len(variazioni))
        
        for row, v in enumerate(variazioni):
            # Tipo
            tipo_item = QTableWidgetItem(v.get('tipo', ''))
            tipo_item.setData(Qt.UserRole, v)
            self.variazioni_table.setItem(row, 0, tipo_item)
            
            # Data
            data = v.get('data_variazione', '')
            if isinstance(data, str) and len(data) > 10:
                data = data[:10]  # Solo la data, non l'ora
            self.variazioni_table.setItem(row, 1, QTableWidgetItem(str(data)))
            
            # Descrizione (troncata)
            descrizione = v.get('descrizione', '')
            if len(descrizione) > 50:
                descrizione = descrizione[:47] + "..."
            self.variazioni_table.setItem(row, 2, QTableWidgetItem(descrizione))
            
            # Similarità
            similarity = v.get('similarity_score', 0)
            sim_item = QTableWidgetItem(f"{similarity:.3f}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            if similarity > 0.7:
                sim_item.setBackground(QColor(144, 238, 144))
            elif similarity > 0.5:
                sim_item.setBackground(QColor(255, 255, 224))
            else:
                sim_item.setBackground(QColor(255, 228, 225))
            self.variazioni_table.setItem(row, 3, sim_item)
    
    def _populate_immobili_table(self, immobili):
        """Popola la tabella degli immobili."""
        self.immobili_table.setRowCount(len(immobili))
        
        for row, i in enumerate(immobili):
            # Natura
            natura = i.get('natura', '')
            natura_item = QTableWidgetItem(natura)
            natura_item.setData(Qt.UserRole, i)
            self.immobili_table.setItem(row, 0, natura_item)
            
            # Classificazione (troncata se troppo lunga)
            classificazione = i.get('classificazione', '')
            if len(classificazione) > 50:
                classificazione = classificazione[:47] + "..."
            self.immobili_table.setItem(row, 1, QTableWidgetItem(classificazione))
            
            # Partita con suffisso
            numero_partita = str(i.get('numero_partita', ''))
            suffisso = str(i.get('suffisso', ''))
            partita_completa = f"{numero_partita}/{suffisso}" if suffisso else numero_partita
            self.immobili_table.setItem(row, 2, QTableWidgetItem(partita_completa))
            
            # Comune
            self.immobili_table.setItem(row, 3, QTableWidgetItem(i.get('comune', '')))
            
            # Località
            self.immobili_table.setItem(row, 4, QTableWidgetItem(i.get('localita', '')))
            
            # Similarità
            similarity = i.get('similarity_score', 0)
            sim_item = QTableWidgetItem(f"{similarity:.3f}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            if similarity > 0.7:
                sim_item.setBackground(QColor(144, 238, 144))
            elif similarity > 0.5:
                sim_item.setBackground(QColor(255, 255, 224))
            else:
                sim_item.setBackground(QColor(255, 228, 225))
            self.immobili_table.setItem(row, 5, sim_item)
    
    def _populate_contratti_table(self, contratti):
        """Popola la tabella dei contratti."""
        self.contratti_table.setRowCount(len(contratti))
        
        for row, c in enumerate(contratti):
            # Tipo
            tipo_item = QTableWidgetItem(c.get('tipo', ''))
            tipo_item.setData(Qt.UserRole, c)
            self.contratti_table.setItem(row, 0, tipo_item)
            
            # Data stipula
            data = c.get('data_stipula', '')
            if isinstance(data, str) and len(data) > 10:
                data = data[:10]
            self.contratti_table.setItem(row, 1, QTableWidgetItem(str(data)))
            
            # Partita
            partita = str(c.get('numero_partita', ''))
            self.contratti_table.setItem(row, 2, QTableWidgetItem(partita))
            
            # Similarità
            similarity = c.get('similarity_score', 0)
            sim_item = QTableWidgetItem(f"{similarity:.3f}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            if similarity > 0.7:
                sim_item.setBackground(QColor(144, 238, 144))
            elif similarity > 0.5:
                sim_item.setBackground(QColor(255, 255, 224))
            else:
                sim_item.setBackground(QColor(255, 228, 225))
            self.contratti_table.setItem(row, 3, sim_item)
    
    def _populate_partite_table(self, partite):
        """Popola la tabella delle partite."""
        self.partite_table.setRowCount(len(partite))
        
        for row, p in enumerate(partite):
            # Numero
            numero_item = QTableWidgetItem(str(p.get('numero_partita', '')))
            numero_item.setData(Qt.UserRole, p)
            self.partite_table.setItem(row, 0, numero_item)
            
            # Tipo
            self.partite_table.setItem(row, 1, QTableWidgetItem(p.get('tipo_partita', '')))
            
            # Comune
            self.partite_table.setItem(row, 2, QTableWidgetItem(p.get('comune_nome', '')))
            
            # Similarità
            similarity = p.get('similarity_score', 0)
            sim_item = QTableWidgetItem(f"{similarity:.3f}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            if similarity > 0.7:
                sim_item.setBackground(QColor(144, 238, 144))
            elif similarity > 0.5:
                sim_item.setBackground(QColor(255, 255, 224))
            else:
                sim_item.setBackground(QColor(255, 228, 225))
            self.partite_table.setItem(row, 3, sim_item)
    
    def _clear_results(self):
        """Pulisce tutti i risultati."""
        for table in [self.possessori_table, self.localita_table, self.variazioni_table,
                     self.immobili_table, self.contratti_table, self.partite_table]:
            table.setRowCount(0)
        
        # Reset contatori tab
        self.results_tabs.setTabText(0, "👥 Possessori")
        self.results_tabs.setTabText(1, "🏘️ Località")
        self.results_tabs.setTabText(2, "📋 Variazioni")
        self.results_tabs.setTabText(3, "🏢 Immobili")
        self.results_tabs.setTabText(4, "📄 Contratti")
        self.results_tabs.setTabText(5, "📊 Partite")
        
        # Disabilita export
        self.export_txt_button.setEnabled(False)
        self.export_pdf_button.setEnabled(False)
        
        self.current_results = {}
    
    def _handle_search_error(self, error_message):
        """Gestisce errori di ricerca."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Errore ricerca")
        self.status_label.setStyleSheet("color: red; font-size: 10px;")
        self.debug_text.append(f"❌ Errore: {error_message}")
        QMessageBox.critical(self, "Errore Ricerca", f"Errore durante la ricerca:\n{error_message}")
    
    def _export_results_txt(self):
        """Esporta risultati in formato TXT."""
        if not self.current_results:
            QMessageBox.warning(self, "Attenzione", "Nessun risultato da esportare")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Salva risultati in TXT",
                f"ricerca_fuzzy_{timestamp}.txt",
                "File di testo (*.txt)"
            )
            
            if not filename:
                return
                
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("RISULTATI RICERCA FUZZY\n")
                f.write("=" * 60 + "\n")
                f.write(f"Query: {self.current_results.get('query_text', 'N/A')}\n")
                f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Possessori
                possessori = self.current_results.get('possessori', [])
                if possessori:
                    f.write(f"POSSESSORI ({len(possessori)})\n")
                    f.write("-" * 40 + "\n")
                    for p in possessori:
                        f.write(f"• {p.get('nome_completo', 'N/A')} - {p.get('comune_nome', 'N/A')} "
                               f"(Similarità: {p.get('similarity_score', 0):.1%})\n")
                    f.write("\n")
                
                # Località
                localita = self.current_results.get('localita', [])
                if localita:
                    f.write(f"LOCALITÀ ({len(localita)})\n")
                    f.write("-" * 40 + "\n")
                    for l in localita:
                        nome = l.get('nome', 'N/A')
                        civico = l.get('civico', '')
                        nome_completo = f"{nome} {civico}" if civico else nome
                        f.write(f"• {nome_completo} - {l.get('comune_nome', 'N/A')} "
                               f"(Similarità: {l.get('similarity_score', 0):.1%})\n")
                    f.write("\n")
                
                # Variazioni
                variazioni = self.current_results.get('variazioni', [])
                if variazioni:
                    f.write(f"VARIAZIONI ({len(variazioni)})\n")
                    f.write("-" * 40 + "\n")
                    for v in variazioni:
                        f.write(f"• {v.get('tipo', 'N/A')} del {v.get('data_variazione', 'N/A')}\n")
                        f.write(f"  {v.get('descrizione', '')}\n")
                        f.write(f"  Similarità: {v.get('similarity_score', 0):.1%}\n\n")
                
                # Immobili
                immobili = self.current_results.get('immobili', [])
                if immobili:
                    f.write(f"IMMOBILI ({len(immobili)})\n")
                    f.write("-" * 40 + "\n")
                    for i in immobili:
                        f.write(f"• {i.get('classificazione', 'N/A')} - {i.get('comune_nome', 'N/A')} "
                               f"(Similarità: {i.get('similarity_score', 0):.1%})\n")
                    f.write("\n")
                
                # Contratti
                contratti = self.current_results.get('contratti', [])
                if contratti:
                    f.write(f"CONTRATTI ({len(contratti)})\n")
                    f.write("-" * 40 + "\n")
                    for c in contratti:
                        f.write(f"• {c.get('tipo', 'N/A')} - {c.get('data_stipula', 'N/A')} "
                               f"(Similarità: {c.get('similarity_score', 0):.1%})\n")
                    f.write("\n")
                
                # Partite
                partite = self.current_results.get('partite', [])
                if partite:
                    f.write(f"PARTITE ({len(partite)})\n")
                    f.write("-" * 40 + "\n")
                    for p in partite:
                        f.write(f"• N.{p.get('numero_partita', '?')} - {p.get('tipo_partita', 'N/A')} "
                               f"(Similarità: {p.get('similarity_score', 0):.1%})\n")
                    f.write("\n")
            
            QMessageBox.information(self, "Export completato", f"Risultati salvati in:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Errore Export", f"Errore durante l'esportazione TXT:\n{e}")
    
    def _export_results_pdf(self):
        """Esporta risultati in formato PDF usando fpdf."""
        try:
            from fpdf import FPDF
            
            if not self.current_results:
                QMessageBox.warning(self, "Attenzione", "Nessun risultato da esportare")
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Salva risultati in PDF",
                f"ricerca_fuzzy_{timestamp}.pdf",
                "File PDF (*.pdf)"
            )
            
            if not filename:
                return
            
            # Crea PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Titolo
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'RISULTATI RICERCA FUZZY', 0, 1, 'C')
            pdf.ln(5)
            
            # Informazioni query
            query_text = self.current_results.get('query_text', 'N/A')
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(30, 8, 'Query:', 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, query_text, 0, 1)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(30, 8, 'Data:', 0, 0)
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 0, 1)
            pdf.ln(10)
            
            # Funzione helper per creare sezioni
            def add_section(title, data, headers, get_row_data, col_widths):
                if not data:
                    return
                    
                # Controlla se serve una nuova pagina
                if pdf.get_y() > 250:
                    pdf.add_page()
                
                # Titolo sezione
                pdf.set_font('Arial', 'B', 14)
                pdf.cell(0, 10, f"{title} ({len(data)})", 0, 1)
                pdf.ln(2)
                
                # Intestazioni tabella
                pdf.set_font('Arial', 'B', 10)
                pdf.set_fill_color(200, 200, 200)
                for i, (header, width) in enumerate(zip(headers, col_widths)):
                    pdf.cell(width, 8, header, 1, 0, 'C', 1)
                pdf.ln()
                
                # Dati tabella
                pdf.set_font('Arial', '', 9)
                pdf.set_fill_color(245, 245, 245)
                
                for idx, item in enumerate(data[:50]):  # Limita a 50 righe
                    # Controlla se serve una nuova pagina
                    if pdf.get_y() > 260:
                        pdf.add_page()
                        # Ripeti intestazioni
                        pdf.set_font('Arial', 'B', 10)
                        pdf.set_fill_color(200, 200, 200)
                        for i, (header, width) in enumerate(zip(headers, col_widths)):
                            pdf.cell(width, 8, header, 1, 0, 'C', 1)
                        pdf.ln()
                        pdf.set_font('Arial', '', 9)
                        pdf.set_fill_color(245, 245, 245)
                    
                    row_data = get_row_data(item)
                    fill = idx % 2 == 0
                    
                    for i, (value, width) in enumerate(zip(row_data, col_widths)):
                        # Tronca il testo se troppo lungo
                        if isinstance(value, str) and len(value) > width/2:
                            value = value[:int(width/2)-3] + '...'
                        pdf.cell(width, 7, str(value), 1, 0, 'L', fill)
                    pdf.ln()
                
                pdf.ln(5)
            
            # POSSESSORI
            add_section(
                "POSSESSORI",
                self.current_results.get('possessori', []),
                ['Nome Completo', 'Comune', 'Simil.'],
                lambda p: [
                    p.get('nome_completo', 'N/A'),
                    p.get('comune', 'N/A'),
                    f"{p.get('similarity_score', 0):.1%}"
                ],
                [80, 70, 40]  # larghezze colonne
            )
            
            # LOCALITÀ
            add_section(
                "LOCALITÀ",
                self.current_results.get('localita', []),
                ['Nome', 'Tipo', 'Comune', 'Simil.'],
                lambda l: [
                    f"{l.get('nome', 'N/A')} {l.get('civico', '')}".strip(),
                    l.get('tipo', 'N/A'),
                    l.get('comune_nome', 'N/A'),
                    f"{l.get('similarity_score', 0):.1%}"
                ],
                [70, 40, 50, 30]
            )
            
            # VARIAZIONI
            add_section(
                "VARIAZIONI",
                self.current_results.get('variazioni', []),
                ['Tipo', 'Data', 'Nominativo', 'Simil.'],
                lambda v: [
                    v.get('tipo', 'N/A'),
                    str(v.get('data_variazione', 'N/A'))[:10],
                    v.get('nominativo_riferimento', '')[:30],
                    f"{v.get('similarity_score', 0):.1%}"
                ],
                [50, 30, 80, 30]
            )
            
            # IMMOBILI
            add_section(
                "IMMOBILI",
                self.current_results.get('immobili', []),
                ['Natura', 'Classificazione', 'Partita', 'Comune', 'Simil.'],
                lambda i: [
                    i.get('natura', 'N/A'),
                    i.get('classificazione', 'N/A')[:30],
                    f"{i.get('numero_partita', '')}/{i.get('suffisso', '')}",
                    i.get('comune', 'N/A'),
                    f"{i.get('similarity_score', 0):.1%}"
                ],
                [40, 50, 30, 40, 30]
            )
            
            # CONTRATTI
            add_section(
                "CONTRATTI",
                self.current_results.get('contratti', []),
                ['Tipo', 'Data', 'Notaio', 'Simil.'],
                lambda c: [
                    c.get('tipo', 'N/A'),
                    str(c.get('data_contratto', 'N/A'))[:10],
                    c.get('notaio', 'N/A')[:40],
                    f"{c.get('similarity_score', 0):.1%}"
                ],
                [50, 30, 80, 30]
            )
            
            # PARTITE
            add_section(
                "PARTITE",
                self.current_results.get('partite', []),
                ['Numero', 'Suffisso', 'Comune', 'Simil.'],
                lambda p: [
                    str(p.get('numero_partita', '?')),
                    p.get('suffisso', ''),
                    p.get('comune', 'N/A'),
                    f"{p.get('similarity_score', 0):.1%}"
                ],
                [40, 30, 90, 30]
            )
            
            # Riepilogo finale
            pdf.set_font('Arial', 'I', 10)
            total_results = sum(len(self.current_results.get(key, [])) 
                            for key in ['possessori', 'localita', 'variazioni', 
                                        'immobili', 'contratti', 'partite'])
            pdf.cell(0, 10, f'Totale risultati: {total_results}', 0, 1, 'C')
            
            # Salva il PDF
            pdf.output(filename)
            QMessageBox.information(self, "Export completato", f"Risultati salvati in:\n{filename}")
            
        except ImportError:
            QMessageBox.warning(
                self, "Libreria mancante", 
                "Per l'esportazione PDF è necessaria la libreria fpdf.\n\n"
                "Installa con: pip install fpdf"
            )
        except Exception as e:
            QMessageBox.critical(self, "Errore Export PDF", f"Errore durante l'esportazione PDF:\n{e}")
    
    # === METODI GESTIONE DOPPIO CLICK ===
    
    def _on_possessore_double_click(self, index):
        """Gestisce doppio click su possessore con dettagli migliorati."""
        item = self.possessori_table.item(index.row(), 0)
        if item:
            possessore_data = item.data(Qt.UserRole)
            possessore_id = possessore_data.get('id')
            
            try:
                # Ottieni dettagli aggiuntivi dal database
                if hasattr(self.db_manager, 'get_possessore_details'):
                    details = self.db_manager.get_possessore_details(possessore_id)
                else:
                    details = possessore_data
                
                # Costruisci il messaggio informativo
                nome = details.get('nome_completo', 'N/A')
                comune = details.get('comune_nome', 'N/A')
                num_partite = details.get('num_partite', 0)
                
                dettagli_msg = f"Nome: {nome}\n"
                dettagli_msg += f"Comune: {comune}\n"
                dettagli_msg += f"Partite collegate: {num_partite}\n\n"
                
                if 'codice_fiscale' in details:
                    dettagli_msg += f"Codice Fiscale: {details.get('codice_fiscale', 'N/A')}\n"
                if 'data_nascita' in details:
                    dettagli_msg += f"Data Nascita: {details.get('data_nascita', 'N/A')}\n"
                if 'luogo_nascita' in details:
                    dettagli_msg += f"Luogo Nascita: {details.get('luogo_nascita', 'N/A')}\n"
                    
                dettagli_msg += f"\nSimilarità ricerca: {possessore_data.get('similarity_score', 0):.1%}"
                
                QMessageBox.information(
                    self, f"Dettagli Possessore ID {possessore_id}",
                    dettagli_msg
                )
                
            except Exception as e:
                # Fallback al messaggio semplice
                QMessageBox.information(
                    self, f"Possessore ID {possessore_id}",
                    f"Nome: {possessore_data.get('nome_completo', 'N/A')}\n"
                    f"Comune: {possessore_data.get('comune_nome', 'N/A')}\n"
                    f"Partite: {possessore_data.get('num_partite', 0)}\n\n"
                    f"Errore caricamento dettagli: {e}"
                )
    
    def _on_localita_double_click(self, index):
        """Gestisce doppio click su località con dettagli migliorati."""
        item = self.localita_table.item(index.row(), 0)
        if item:
            localita_data = item.data(Qt.UserRole)
            localita_id = localita_data.get('id')
            
            try:
                # Ottieni dettagli aggiuntivi dal database
                if hasattr(self.db_manager, 'get_localita_details'):
                    details = self.db_manager.get_localita_details(localita_id)
                else:
                    details = localita_data
                
                # Costruisci il messaggio informativo
                nome = details.get('nome', 'N/A')
                civico = details.get('civico', '')
                nome_completo = f"{nome} {civico}" if civico else nome
                tipo = details.get('tipo', 'N/A')
                comune = details.get('comune_nome', 'N/A')
                
                dettagli_msg = f"Località: {nome_completo}\n"
                dettagli_msg += f"Tipo: {tipo}\n"
                dettagli_msg += f"Comune: {comune}\n"
                
                if 'num_immobili' in details:
                    dettagli_msg += f"Immobili: {details.get('num_immobili', 0)}\n"
                if 'cap' in details:
                    dettagli_msg += f"CAP: {details.get('cap', 'N/A')}\n"
                if 'zona' in details:
                    dettagli_msg += f"Zona: {details.get('zona', 'N/A')}\n"
                    
                dettagli_msg += f"\nSimilarità ricerca: {localita_data.get('similarity_score', 0):.1%}"
                
                QMessageBox.information(
                    self, f"Dettagli Località ID {localita_id}",
                    dettagli_msg
                )
                
            except Exception as e:
                # Fallback al messaggio semplice
                nome_completo = f"{localita_data.get('nome', 'N/A')} {localita_data.get('civico', '')}".strip()
                QMessageBox.information(
                    self, f"Località ID {localita_id}",
                    f"Nome: {nome_completo}\n"
                    f"Tipo: {localita_data.get('tipo', 'N/A')}\n"
                    f"Comune: {localita_data.get('comune_nome', 'N/A')}\n\n"
                    f"Errore caricamento dettagli: {e}"
                )
    
    def _on_variazione_double_click(self, index):
        """Gestisce doppio click su variazione."""
        item = self.variazioni_table.item(index.row(), 0)
        if item:
            variazione_data = item.data(Qt.UserRole)
            variazione_id = variazione_data.get('id')
            
            dettagli_msg = f"Tipo: {variazione_data.get('tipo', 'N/A')}\n"
            dettagli_msg += f"Data: {variazione_data.get('data_variazione', 'N/A')}\n"
            dettagli_msg += f"Descrizione: {variazione_data.get('descrizione', 'N/A')}\n"
            dettagli_msg += f"Partita: {variazione_data.get('numero_partita', 'N/A')}\n"
            dettagli_msg += f"\nSimilarità ricerca: {variazione_data.get('similarity_score', 0):.1%}"
            
            QMessageBox.information(
                self, f"Dettagli Variazione ID {variazione_id}",
                dettagli_msg
            )
    
    def _on_immobile_double_click(self, index):
        """Gestisce doppio click su immobile."""
        item = self.immobili_table.item(index.row(), 0)
        if item:
            immobile_data = item.data(Qt.UserRole)
            immobile_id = immobile_data.get('id')
            
            dettagli_msg = f"Classificazione: {immobile_data.get('classificazione', 'N/A')}\n"
            dettagli_msg += f"Natura: {immobile_data.get('natura', 'N/A')}\n"
            dettagli_msg += f"Partita: {immobile_data.get('numero_partita', 'N/A')}\n"
            dettagli_msg += f"Comune: {immobile_data.get('comune_nome', 'N/A')}\n"
            dettagli_msg += f"\nSimilarità ricerca: {immobile_data.get('similarity_score', 0):.1%}"
            
            QMessageBox.information(
                self, f"Dettagli Immobile ID {immobile_id}",
                dettagli_msg
            )
    
    def _on_contratto_double_click(self, index):
        """Gestisce doppio click su contratto."""
        item = self.contratti_table.item(index.row(), 0)
        if item:
            contratto_data = item.data(Qt.UserRole)
            contratto_id = contratto_data.get('id')
            
            dettagli_msg = f"Tipo: {contratto_data.get('tipo', 'N/A')}\n"
            dettagli_msg += f"Data Stipula: {contratto_data.get('data_stipula', 'N/A')}\n"
            dettagli_msg += f"Partita: {contratto_data.get('numero_partita', 'N/A')}\n"
            dettagli_msg += f"Contraente: {contratto_data.get('contraente', 'N/A')}\n"
            dettagli_msg += f"\nSimilarità ricerca: {contratto_data.get('similarity_score', 0):.1%}"
            
            QMessageBox.information(
                self, f"Dettagli Contratto ID {contratto_id}",
                dettagli_msg
            )
    
    def _on_partita_double_click(self, index):
        """Gestisce doppio click su partita."""
        item = self.partite_table.item(index.row(), 0)
        if item:
            partita_data = item.data(Qt.UserRole)
            partita_id = partita_data.get('id')
            
            dettagli_msg = f"Numero: {partita_data.get('numero_partita', 'N/A')}\n"
            dettagli_msg += f"Tipo: {partita_data.get('tipo_partita', 'N/A')}\n"
            dettagli_msg += f"Comune: {partita_data.get('comune_nome', 'N/A')}\n"
            dettagli_msg += f"Anno Attivazione: {partita_data.get('anno_attivazione', 'N/A')}\n"
            dettagli_msg += f"\nSimilarità ricerca: {partita_data.get('similarity_score', 0):.1%}"
            
            QMessageBox.information(
                self, f"Dettagli Partita ID {partita_id}",
                dettagli_msg
            )

# ========================================================================
# FUNZIONE DI INTEGRAZIONE CON GUI PRINCIPALE
# ========================================================================

def add_fuzzy_search_tab_to_main_window(main_window):
    """
    Aggiunge il tab di ricerca fuzzy alla finestra principale.
    
    Args:
        main_window: Istanza di CatastoMainWindow
        
    Returns:
        bool: True se aggiunto con successo, False altrimenti
    """
    try:
        if not hasattr(main_window, 'db_manager') or not main_window.db_manager:
            if hasattr(main_window, 'logger'):
                main_window.logger.warning("Database manager non disponibile per ricerca fuzzy")
            else:
                print("❌ Database manager non disponibile per ricerca fuzzy")
            return False
            
        # Crea il widget di ricerca fuzzy
        fuzzy_widget = CompactFuzzySearchWidget(main_window.db_manager, main_window)
        
        # Aggiunge il tab alla finestra principale
        tab_index = main_window.tabs.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
        
        if hasattr(main_window, 'logger'):
            main_window.logger.info(f"Tab Ricerca Fuzzy aggiunto all'indice {tab_index}")
        else:
            print(f"✅ Tab Ricerca Fuzzy aggiunto all'indice {tab_index}")
        
        return True
        
    except Exception as e:
        if hasattr(main_window, 'logger'):
            main_window.logger.error(f"Errore aggiunta tab ricerca fuzzy: {e}")
        else:
            print(f"❌ Errore aggiunta tab ricerca fuzzy: {e}")
        
        import traceback
        traceback.print_exc()
        return False

# Alias per compatibilità con versioni precedenti
add_working_fuzzy_search_tab_to_main_window = add_fuzzy_search_tab_to_main_window
add_enhanced_fuzzy_search_tab_to_main_window = add_fuzzy_search_tab_to_main_window
add_optimized_fuzzy_search_tab_to_main_window = add_fuzzy_search_tab_to_main_window
add_complete_fuzzy_search_tab_to_main_window = add_fuzzy_search_tab_to_main_window

# ========================================================================
# ESEMPIO DI UTILIZZO STANDALONE
# ========================================================================

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Simula un database manager (per test)
    class MockDBManager:
        def __init__(self):
            self.schema = "catasto"
            
        def get_possessore_details(self, possessore_id):
            return {
                'id': possessore_id,
                'nome_completo': 'Test Possessore',
                'comune_nome': 'Test Comune',
                'num_partite': 3,
                'codice_fiscale': 'TESTCF123456789',
                'data_nascita': '1980-01-01',
                'luogo_nascita': 'Test Città'
            }
            
        def get_localita_details(self, localita_id):
            return {
                'id': localita_id,
                'nome': 'Test Località',
                'tipo': 'Via',
                'comune_nome': 'Test Comune',
                'num_immobili': 5,
                'cap': '12345',
                'zona': 'Centro'
            }
    
    widget = CompactFuzzySearchWidget(MockDBManager())
    widget.show()
    
    sys.exit(app.exec_())