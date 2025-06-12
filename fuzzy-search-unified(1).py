#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Widget per Ricerca Fuzzy nel Database Catasto - Versione Completa
==================================================================
File: fuzzy_search_widget_unified.py
Autore: Marco Santoro
Data: 10/06/2025
Versione: 4.0 (solo expanded, tutte le funzionalità)

Supporta:
- Ricerca in tutte le entità (possessori, località, immobili, variazioni, contratti, partite)
- Export multipli (TXT, PDF, CSV, JSON)
- Vista unificata e per tipo
- Dettagli avanzati delle entità
"""

import logging
import time
import json
import csv
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QGroupBox,
    QSlider, QCheckBox, QComboBox, QProgressBar, QFrame, QHeaderView,
    QMessageBox, QApplication, QFileDialog, QDialog, QSpinBox,
    QSplitter, QScrollArea, QFormLayout, QDialogButtonBox, QSpacerItem,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QPalette

# ========================================================================
# VERIFICA E IMPORT DELLE ESTENSIONI GIN
# ========================================================================

# Prova a importare l'estensione expanded (più completa)
try:
    from catasto_gin_extension_expanded import extend_db_manager_with_gin_expanded
    GIN_EXPANDED_AVAILABLE = True
except ImportError:
    GIN_EXPANDED_AVAILABLE = False
    extend_db_manager_with_gin_expanded = None

# Prova a importare l'estensione base
try:
    from catasto_gin_extension import extend_db_manager_with_gin
    GIN_BASIC_AVAILABLE = True
except ImportError:
    GIN_BASIC_AVAILABLE = False
    extend_db_manager_with_gin = None

# Flag globale per disponibilità GIN
GIN_AVAILABLE = GIN_EXPANDED_AVAILABLE or GIN_BASIC_AVAILABLE

# ========================================================================
# THREAD PER RICERCHE IN BACKGROUND
# ========================================================================

class FuzzySearchThread(QThread):
    """Thread per eseguire ricerche fuzzy in background."""
    
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, gin_search, query_text, options):
        super().__init__()
        self.gin_search = gin_search
        self.query_text = query_text
        self.options = options
        
    def run(self):
        """Esegue la ricerca fuzzy unificata."""
        try:
            self.progress_updated.emit(10)
            
            threshold = self.options.get('threshold', 0.3)
            max_results_per_type = self.options.get('max_results_per_type', 30)
            
            self.progress_updated.emit(30)
            
            # Usa sempre la ricerca unificata
            if hasattr(self.gin_search, 'search_all_entities_fuzzy'):
                results = self.gin_search.search_all_entities_fuzzy(
                    self.query_text,
                    search_possessori=self.options.get('search_possessori', True),
                    search_localita=self.options.get('search_localita', True),
                    search_immobili=self.options.get('search_immobili', True),
                    search_variazioni=self.options.get('search_variazioni', True),
                    search_contratti=self.options.get('search_contratti', True),
                    search_partite=self.options.get('search_partite', True),
                    max_results_per_type=max_results_per_type
                )
            else:
                # Fallback: usa ricerche individuali e combina i risultati
                self.progress_updated.emit(20)
                results = {'results_by_type': {}}
                total_steps = sum(1 for k, v in self.options.items() if k.startswith('search_') and v)
                current_step = 0
                
                # Ricerca possessori
                if self.options.get('search_possessori', True):
                    current_step += 1
                    self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                    if hasattr(self.gin_search, 'search_possessori_fuzzy'):
                        possessori = self.gin_search.search_possessori_fuzzy(
                            self.query_text, threshold, self.options.get('max_results', 100)
                        )
                        if possessori:
                            results['results_by_type']['possessore'] = [
                                {
                                    'entity_id': p.get('id'),
                                    'display_text': p.get('nome_completo', ''),
                                    'detail_text': p.get('comune_nome', ''),
                                    'similarity_score': p.get('similarity_score', 0),
                                    'search_field': 'nome_completo',
                                    'additional_info': {
                                        'paternita': p.get('paternita', ''),
                                        'comune': p.get('comune_nome', ''),
                                        'num_partite': p.get('num_partite', 0)
                                    }
                                } for p in possessori
                            ]
                
                # Ricerca località
                if self.options.get('search_localita', True):
                    current_step += 1
                    self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                    if hasattr(self.gin_search, 'search_localita_fuzzy'):
                        localita = self.gin_search.search_localita_fuzzy(
                            self.query_text, threshold, self.options.get('max_results', 100)
                        )
                        if localita:
                            results['results_by_type']['localita'] = [
                                {
                                    'entity_id': l.get('id'),
                                    'display_text': f"{l.get('nome', '')} {l.get('civico', '')}".strip(),
                                    'detail_text': l.get('comune_nome', ''),
                                    'similarity_score': l.get('similarity_score', 0),
                                    'search_field': 'nome',
                                    'additional_info': {
                                        'tipo': l.get('tipo', ''),
                                        'comune': l.get('comune_nome', ''),
                                        'num_immobili': l.get('num_immobili', 0)
                                    }
                                } for l in localita
                            ]
                
                # Aggiungi ricerche per altre entità se disponibili...
                # (immobili, variazioni, contratti, partite)
                
                results['status'] = 'OK'
            
            # Aggiungi metadati
            results['query_text'] = self.query_text
            results['threshold'] = threshold
            results['timestamp'] = datetime.now()
            results['search_type'] = 'unified'
            
            # Calcola totale risultati
            if 'results_by_type' in results:
                total = sum(len(entities) for entities in results.get('results_by_type', {}).values())
            else:
                total = sum(len(entities) for key, entities in results.items() 
                          if isinstance(entities, list))
            results['total_results'] = total
            
            self.progress_updated.emit(100)
            self.results_ready.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

# ========================================================================
# DIALOG PER DETTAGLI ENTITÀ
# ========================================================================

class EntityDetailsDialog(QDialog):
    """Dialog per visualizzare i dettagli completi di un'entità."""
    
    def __init__(self, db_manager, entity_type, entity_id, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.entity_type = entity_type
        self.entity_id = entity_id
        
        self.setWindowTitle(f"Dettagli {entity_type.title()} - ID {entity_id}")
        self.setMinimumSize(600, 400)
        self.setup_ui()
        self.load_details()
        
    def setup_ui(self):
        """Configura l'interfaccia del dialog."""
        layout = QVBoxLayout(self)
        
        # Area dettagli principali
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        layout.addWidget(self.details_text)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Aggiorna")
        self.refresh_btn.clicked.connect(self.load_details)
        buttons_layout.addWidget(self.refresh_btn)
        
        buttons_layout.addStretch()
        
        self.close_btn = QPushButton("Chiudi")
        self.close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
    def load_details(self):
        """Carica i dettagli dell'entità."""
        try:
            if hasattr(self.db_manager, 'get_entity_details'):
                details = self.db_manager.get_entity_details(self.entity_type, self.entity_id)
                
                if details.get('status') == 'OK':
                    self.display_details(details['details'])
                else:
                    self.details_text.setPlainText(f"Errore: {details.get('error', 'Impossibile caricare i dettagli')}")
            else:
                self.details_text.setPlainText("Funzionalità dettagli non disponibile")
                
        except Exception as e:
            self.details_text.setPlainText(f"Errore nel caricamento: {str(e)}")
            
    def display_details(self, details):
        """Visualizza i dettagli formattati."""
        text = f"=== DETTAGLI {self.entity_type.upper()} ===\n\n"
        
        for key, value in details.items():
            if value is not None:
                # Formatta le date
                if 'data' in key.lower() and hasattr(value, 'strftime'):
                    value = value.strftime('%d/%m/%Y')
                
                # Formatta i booleani
                elif isinstance(value, bool):
                    value = "Sì" if value else "No"
                
                # Capitalizza le chiavi per la visualizzazione
                display_key = key.replace('_', ' ').title()
                text += f"{display_key}: {value}\n"
        
        self.details_text.setPlainText(text)

# ========================================================================
# WIDGET PRINCIPALE RICERCA FUZZY
# ========================================================================

class FuzzySearchWidget(QWidget):
    """Widget completo per ricerca fuzzy in tutte le entità del catasto."""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent
        self.logger = logging.getLogger(__name__)
        
        # Inizializza componenti GIN
        self.gin_search = None
        self._init_gin_extensions()
        
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
        
    def _init_gin_extensions(self):
        """Inizializza le estensioni GIN appropriate."""
        if not self.db_manager:
            return
            
        # Prova prima l'estensione expanded se disponibile
        if GIN_EXPANDED_AVAILABLE:
            try:
                self.extended_db_manager = extend_db_manager_with_gin_expanded(self.db_manager)
                self.gin_search = self.extended_db_manager
                self.gin_expanded = True
                self.logger.info("Estensione GIN expanded caricata con successo")
            except Exception as e:
                self.logger.error(f"Errore caricamento GIN expanded: {e}")
                self.gin_expanded = False
        
        # Fallback all'estensione base se necessario
        if not self.gin_search and GIN_BASIC_AVAILABLE:
            try:
                self.extended_db_manager = extend_db_manager_with_gin(self.db_manager)
                self.gin_search = self.extended_db_manager
                self.gin_expanded = False
                self.logger.info("Estensione GIN base caricata con successo")
            except Exception as e:
                self.logger.error(f"Errore caricamento GIN base: {e}")
    
    def _setup_ui(self):
        """Configura l'interfaccia utente completa."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # === AREA RICERCA ===
        search_frame = QFrame()
        search_frame.setFrameStyle(QFrame.StyledPanel)
        search_frame.setMaximumHeight(120)
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(10, 8, 10, 8)
        
        # Riga principale di ricerca
        search_row = QHBoxLayout()
        
        search_row.addWidget(QLabel("🔍"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca in possessori, località, immobili, variazioni, contratti, partite...")
        search_row.addWidget(self.search_edit, 1)
        
        self.search_btn = QPushButton("Cerca")
        self.search_btn.clicked.connect(self._perform_search)
        search_row.addWidget(self.search_btn)
        
        self.clear_btn = QPushButton("🗑️")
        self.clear_btn.setMaximumWidth(30)
        self.clear_btn.clicked.connect(self._clear_search)
        search_row.addWidget(self.clear_btn)
        
        search_layout.addLayout(search_row)
        
        # Controlli avanzati
        controls_row = QHBoxLayout()
        
        # Soglia similarità
        controls_row.addWidget(QLabel("Soglia:"))
        self.precision_slider = QSlider(Qt.Horizontal)
        self.precision_slider.setRange(10, 90)
        self.precision_slider.setValue(30)
        self.precision_slider.setMaximumWidth(100)
        controls_row.addWidget(self.precision_slider)
        
        self.precision_label = QLabel("0.30")
        self.precision_label.setMinimumWidth(30)
        controls_row.addWidget(self.precision_label)
        
        # Max risultati
        controls_row.addWidget(QLabel("Max:"))
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["50", "100", "200", "500"])
        self.max_results_combo.setCurrentText("100")
        self.max_results_combo.setMaximumWidth(60)
        controls_row.addWidget(self.max_results_combo)
        
        controls_row.addStretch()
        
        # Pulsanti azione
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.clicked.connect(self._export_results)
        self.export_btn.setEnabled(False)
        controls_row.addWidget(self.export_btn)
        
        self.indices_btn = QPushButton("🔧 Indici")
        self.indices_btn.clicked.connect(self._check_gin_status)
        controls_row.addWidget(self.indices_btn)
        
        search_layout.addLayout(controls_row)
        main_layout.addWidget(search_frame)
        
        # === CHECKBOXES PER TIPI DI RICERCA ===
        types_layout = QHBoxLayout()
        
        self.search_possessori_cb = QCheckBox("👥 Possessori")
        self.search_possessori_cb.setChecked(True)
        types_layout.addWidget(self.search_possessori_cb)
        
        self.search_localita_cb = QCheckBox("🏘️ Località")
        self.search_localita_cb.setChecked(True)
        types_layout.addWidget(self.search_localita_cb)
        
        self.search_variazioni_cb = QCheckBox("📋 Variazioni")
        self.search_variazioni_cb.setChecked(True)
        types_layout.addWidget(self.search_variazioni_cb)
        
        self.search_immobili_cb = QCheckBox("🏢 Immobili")
        self.search_immobili_cb.setChecked(True)
        types_layout.addWidget(self.search_immobili_cb)
        
        self.search_contratti_cb = QCheckBox("📄 Contratti")
        self.search_contratti_cb.setChecked(True)
        types_layout.addWidget(self.search_contratti_cb)
        
        self.search_partite_cb = QCheckBox("📊 Partite")
        self.search_partite_cb.setChecked(True)
        types_layout.addWidget(self.search_partite_cb)
        
        types_layout.addStretch()
        main_layout.addLayout(types_layout)
        
        # === AREA RISULTATI ===
        results_frame = QFrame()
        results_frame.setFrameStyle(QFrame.StyledPanel)
        results_layout = QVBoxLayout(results_frame)
        results_layout.setContentsMargins(5, 5, 5, 5)
        
        # Header risultati
        results_header = QHBoxLayout()
        self.results_label = QLabel("🔍 Risultati ricerca")
        self.results_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        results_header.addWidget(self.results_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        results_header.addWidget(self.progress_bar)
        
        results_header.addStretch()
        
        self.results_count_label = QLabel("0 risultati")
        results_header.addWidget(self.results_count_label)
        
        results_layout.addLayout(results_header)
        
        # Tabs risultati
        self._create_results_tabs()
        results_layout.addWidget(self.results_tabs)
        
        main_layout.addWidget(results_frame, 1)
        
        # === STATUS BAR ===
        self._create_status_bar()
        main_layout.addLayout(self.status_layout)
        
        # === DEBUG AREA (minimale) ===
        debug_frame = QFrame()
        debug_frame.setMaximumHeight(50)
        debug_layout = QHBoxLayout(debug_frame)
        debug_layout.setContentsMargins(5, 2, 5, 2)
        
        self.status_label = QLabel("Sistema ricerca fuzzy pronto")
        self.status_label.setStyleSheet("font-size: 10px; color: #666;")
        debug_layout.addWidget(self.status_label)
        
        debug_layout.addStretch()
        
        self.indices_status_label = QLabel("Indici: Non verificato")
        self.indices_status_label.setStyleSheet("font-size: 10px; color: #666;")
        debug_layout.addWidget(self.indices_status_label)
        
        main_layout.addWidget(debug_frame)
        
        # Focus iniziale
        self.search_edit.setFocus()
    
    def _create_results_tabs(self):
        """Crea i tab per i risultati."""
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)
        
        # Tab Unificata
        self.unified_table = self._create_unified_table()
        self.results_tabs.addTab(self.unified_table, "🔍 Tutti")
        
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
    
    def _create_status_bar(self):
        """Crea la barra di stato."""
        self.status_layout = QHBoxLayout()
        
        self.stats_label = QLabel("Inserire almeno 3 caratteri per iniziare")
        self.stats_label.setStyleSheet("color: gray; font-size: 11px;")
        self.status_layout.addWidget(self.stats_label)
        
        self.status_layout.addStretch()
    
    def _create_unified_table(self):
        """Crea la tabella unificata."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo", "Azioni"
        ])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        
        return table
    
    def _create_possessori_tab(self):
        """Crea il tab per i possessori."""
        possessori_group = QGroupBox("👥 Possessori")
        layout = QVBoxLayout(possessori_group)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Tabella possessori
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(6)
        self.possessori_table.setHorizontalHeaderLabels([
            "ID", "Nome Completo", "Paternità", "Comune", "Similarità", "Azioni"
        ])
        
        header = self.possessori_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
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
        self.localita_table.setColumnCount(6)
        self.localita_table.setHorizontalHeaderLabels([
            "ID", "Nome", "Tipo", "Comune", "Similarità", "Azioni"
        ])
        
        header = self.localita_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
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
        self.variazioni_table.setColumnCount(7)
        self.variazioni_table.setHorizontalHeaderLabels([
            "ID", "Tipo", "Da Partita", "A Partita", "Data", "Similarità", "Campo"
        ])
        
        header = self.variazioni_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
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
        
        # Tabella immobili
        self.immobili_table = QTableWidget()
        self.immobili_table.setColumnCount(7)
        self.immobili_table.setHorizontalHeaderLabels([
            "ID", "Natura", "Partita", "Località", "Comune", "Similarità", "Campo"
        ])
        
        header = self.immobili_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
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
        self.contratti_table.setColumnCount(6)
        self.contratti_table.setHorizontalHeaderLabels([
            "ID", "Tipo", "Data", "Notaio", "Similarità", "Campo"
        ])
        
        header = self.contratti_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
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
        self.partite_table.setColumnCount(7)
        self.partite_table.setHorizontalHeaderLabels([
            "ID", "Numero", "Suffisso", "Comune", "Stato", "Similarità", "Campo"
        ])
        
        header = self.partite_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
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
            lambda v: self.precision_label.setText(f"{v/100:.2f}")
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
        self.possessori_table.doubleClicked.connect(lambda: self._on_entity_double_click('possessore'))
        self.localita_table.doubleClicked.connect(lambda: self._on_entity_double_click('localita'))
        self.variazioni_table.doubleClicked.connect(lambda: self._on_entity_double_click('variazione'))
        self.immobili_table.doubleClicked.connect(lambda: self._on_entity_double_click('immobile'))
        self.contratti_table.doubleClicked.connect(lambda: self._on_entity_double_click('contratto'))
        self.partite_table.doubleClicked.connect(lambda: self._on_entity_double_click('partita'))
        self.unified_table.doubleClicked.connect(self._on_unified_double_click)
    
    def _check_gin_status(self):
        """Verifica stato indici GIN."""
        if not self.gin_search:
            self.indices_status_label.setText("❌ Non disponibile")
            return
            
        try:
            # Prova metodi diversi in base all'estensione
            if hasattr(self.gin_search, 'verify_gin_indices'):
                result = self.gin_search.verify_gin_indices()
                if result.get('status') == 'OK':
                    total = result.get('total_indices', 0)
                    gin_count = result.get('gin_indices', 0)
                    self.indices_status_label.setText(f"✅ {gin_count}/{total} GIN")
                else:
                    self.indices_status_label.setText("❌ Errore verifica")
                    
            elif hasattr(self.gin_search, 'get_gin_indices_status'):
                indices = self.gin_search.get_gin_indices_status()
                if indices:
                    self.indices_status_label.setText(f"✅ {len(indices)} indici")
                else:
                    self.indices_status_label.setText("❌ Nessun indice")
                    
        except Exception as e:
            self.indices_status_label.setText("❌ Errore verifica")
    
    def _on_search_text_changed(self, text):
        """Gestisce cambiamenti nel testo di ricerca."""
        if len(text) >= 3:
            self.search_timer.start(800)
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
        
        if not self.gin_search:
            QMessageBox.warning(self, "Errore", "Sistema di ricerca fuzzy non disponibile")
            return
        
        # Prepara parametri ricerca
        threshold = self.precision_slider.value() / 100.0
        max_results = int(self.max_results_combo.currentText())
        
        # Usa sempre ricerca unificata
        search_type = 'unified'
        
        search_options = {
            'search_type': search_type,
            'threshold': threshold,
            'max_results': max_results,
            'search_possessori': self.search_possessori_cb.isChecked(),
            'search_localita': self.search_localita_cb.isChecked(),
            'search_variazioni': self.search_variazioni_cb.isChecked(),
            'search_immobili': self.search_immobili_cb.isChecked(),
            'search_contratti': self.search_contratti_cb.isChecked(),
            'search_partite': self.search_partite_cb.isChecked(),
            'max_results_per_type': 30
        }
        
        # Avvia ricerca in thread separato
        if self.search_thread and self.search_thread.isRunning():
            return
        
        self.progress_bar.setVisible(True)
        self.status_label.setText("🔍 Ricerca in corso...")
        self.status_label.setStyleSheet("color: blue; font-size: 10px;")
        self.search_btn.setEnabled(False)
        
        self.search_thread = FuzzySearchThread(
            self.gin_search, query_text, search_options
        )
        self.search_thread.results_ready.connect(self._display_results)
        self.search_thread.error_occurred.connect(self._handle_search_error)
        self.search_thread.progress_updated.connect(self.progress_bar.setValue)
        self.search_thread.finished.connect(self._search_finished)
        self.search_thread.start()
    
    def _display_results(self, results):
        """Visualizza i risultati della ricerca."""
        try:
            start_time = time.time()
            self.current_results = results
            
            # Se abbiamo risultati nel formato expanded
            if 'results_by_type' in results:
                self._display_unified_results(results['results_by_type'])
                self._populate_individual_tabs_expanded(results['results_by_type'])
            else:
                # Formato standard - convertiamo per la vista unificata
                self._clear_unified_table()
                converted_results = self._convert_standard_to_unified(results)
                if converted_results:
                    self._display_unified_results(converted_results)
                
                # Popola tab individuali
                self._populate_possessori_table(results.get('possessori', []))
                self._populate_localita_table(results.get('localita', []))
                self._populate_variazioni_table(results.get('variazioni', []))
                self._populate_immobili_table(results.get('immobili', []))
                self._populate_contratti_table(results.get('contratti', []))
                self._populate_partite_table(results.get('partite', []))
            
            # Aggiorna contatori nei tab
            total = results.get('total_results', 0)
            self._update_tab_counters(results)
            
            # Statistiche
            exec_time = time.time() - start_time
            threshold = results.get('threshold', 0)
            
            if total > 0:
                self.stats_label.setText(
                    f"Trovati {total} risultati in {exec_time:.3f}s [soglia: {threshold:.2f}]"
                )
            else:
                self.stats_label.setText("Nessun risultato trovato")
            
            # Abilita export se ci sono risultati
            self.export_btn.setEnabled(total > 0)
            self.results_count_label.setText(f"{total} risultati")
            
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
    
    def _display_unified_results(self, results_by_type):
        """Visualizza i risultati nella tab unificata."""
        table = self.unified_table
        table.setRowCount(0)
        
        row = 0
        for entity_type, entities in results_by_type.items():
            for entity in entities:
                table.insertRow(row)
                
                # Tipo con icona
                type_icons = {
                    'possessore': '👥',
                    'localita': '🏠',
                    'immobile': '🏢',
                    'variazione': '🔄',
                    'contratto': '📄',
                    'partita': '📋'
                }
                
                icon = type_icons.get(entity_type, '📁')
                table.setItem(row, 0, QTableWidgetItem(f"{icon} {entity_type.title()}"))
                table.setItem(row, 1, QTableWidgetItem(entity.get('display_text', '')))
                table.setItem(row, 2, QTableWidgetItem(entity.get('detail_text', '')))
                
                # Barra di similarità
                similarity = entity.get('similarity_score', 0)
                similarity_item = QTableWidgetItem(f"{similarity:.3f}")
                similarity_item.setData(Qt.UserRole, similarity)
                table.setItem(row, 3, similarity_item)
                
                table.setItem(row, 4, QTableWidgetItem(entity.get('search_field', '')))
                
                # Pulsante dettagli
                details_btn = QPushButton("📋 Dettagli")
                details_btn.clicked.connect(
                    lambda checked, et=entity_type, eid=entity.get('entity_id'): 
                    self._show_entity_details(et, eid)
                )
                table.setCellWidget(row, 5, details_btn)
                
                # Memorizza i dati per l'export
                table.item(row, 0).setData(Qt.UserRole, {
                    'entity_type': entity_type,
                    'entity_id': entity.get('entity_id'),
                    'full_data': entity
                })
                
                row += 1
    
    def _clear_unified_table(self):
        """Pulisce la tabella unificata."""
        self.unified_table.setRowCount(0)
    
    def _convert_standard_to_unified(self, results):
        """Converte i risultati dal formato standard al formato unificato."""
        converted = {}
        
        # Possessori
        if 'possessori' in results and results['possessori']:
            converted['possessore'] = [
                {
                    'entity_id': p.get('id'),
                    'display_text': p.get('nome_completo', ''),
                    'detail_text': p.get('comune_nome', ''),
                    'similarity_score': p.get('similarity_score', 0),
                    'search_field': 'nome_completo',
                    'additional_info': {
                        'paternita': p.get('paternita', ''),
                        'comune': p.get('comune_nome', ''),
                        'num_partite': p.get('num_partite', 0)
                    }
                } for p in results['possessori']
            ]
        
        # Località
        if 'localita' in results and results['localita']:
            converted['localita'] = [
                {
                    'entity_id': l.get('id'),
                    'display_text': f"{l.get('nome', '')} {l.get('civico', '')}".strip(),
                    'detail_text': l.get('comune_nome', ''),
                    'similarity_score': l.get('similarity_score', 0),
                    'search_field': 'nome',
                    'additional_info': {
                        'tipo': l.get('tipo', ''),
                        'comune': l.get('comune_nome', ''),
                        'num_immobili': l.get('num_immobili', 0)
                    }
                } for l in results['localita']
            ]
        
        # Aggiungi altre conversioni per immobili, variazioni, ecc. se necessario
        
        return converted if converted else None
    
    def _populate_individual_tabs_expanded(self, results_by_type):
        """Popola le tab individuali con dati del formato expanded."""
        # Possessori
        if 'possessore' in results_by_type:
            self._populate_possessori_expanded(results_by_type['possessore'])
            
        # Località
        if 'localita' in results_by_type:
            self._populate_localita_expanded(results_by_type['localita'])
            
        # Immobili
        if 'immobile' in results_by_type:
            self._populate_immobili_expanded(results_by_type['immobile'])
            
        # Variazioni
        if 'variazione' in results_by_type:
            self._populate_variazioni_expanded(results_by_type['variazione'])
            
        # Contratti
        if 'contratto' in results_by_type:
            self._populate_contratti_expanded(results_by_type['contratto'])
            
        # Partite
        if 'partita' in results_by_type:
            self._populate_partite_expanded(results_by_type['partita'])
    
    def _populate_possessori_table(self, possessori):
        """Popola la tabella dei possessori (formato standard)."""
        self.possessori_table.setRowCount(len(possessori))
        
        for row, p in enumerate(possessori):
            # ID
            self.possessori_table.setItem(row, 0, QTableWidgetItem(str(p.get('id', ''))))
            
            # Nome completo
            nome_item = QTableWidgetItem(p.get('nome_completo', ''))
            nome_item.setData(Qt.UserRole, p)
            self.possessori_table.setItem(row, 1, nome_item)
            
            # Paternità
            self.possessori_table.setItem(row, 2, QTableWidgetItem(p.get('paternita', '')))
            
            # Comune
            self.possessori_table.setItem(row, 3, QTableWidgetItem(p.get('comune_nome', '')))
            
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
            self.possessori_table.setItem(row, 4, sim_item)
            
            # Pulsante azioni
            action_btn = QPushButton("📋")
            action_btn.clicked.connect(
                lambda checked, eid=p.get('id'): 
                self._show_entity_details('possessore', eid)
            )
            self.possessori_table.setCellWidget(row, 5, action_btn)
    
    def _populate_possessori_expanded(self, possessori):
        """Popola la tabella possessori dal formato expanded."""
        self.possessori_table.setRowCount(len(possessori))
        
        for row, possessore in enumerate(possessori):
            info = possessore.get('additional_info', {})
            
            self.possessori_table.setItem(row, 0, QTableWidgetItem(str(possessore.get('entity_id', ''))))
            self.possessori_table.setItem(row, 1, QTableWidgetItem(possessore.get('display_text', '')))
            self.possessori_table.setItem(row, 2, QTableWidgetItem(info.get('paternita', 'N/A')))
            self.possessori_table.setItem(row, 3, QTableWidgetItem(info.get('comune', 'N/A')))
            self.possessori_table.setItem(row, 4, QTableWidgetItem(f"{possessore.get('similarity_score', 0):.3f}"))
            
            # Pulsante azioni
            action_btn = QPushButton("📋")
            action_btn.clicked.connect(
                lambda checked, eid=possessore.get('entity_id'): 
                self._show_entity_details('possessore', eid)
            )
            self.possessori_table.setCellWidget(row, 5, action_btn)
    
    def _populate_localita_table(self, localita):
        """Popola la tabella delle località (formato standard)."""
        self.localita_table.setRowCount(len(localita))
        
        for row, l in enumerate(localita):
            # ID
            self.localita_table.setItem(row, 0, QTableWidgetItem(str(l.get('id', ''))))
            
            # Nome con civico
            nome = l.get('nome', '')
            civico = l.get('civico', '')
            nome_completo = f"{nome} {civico}" if civico else nome
            nome_item = QTableWidgetItem(nome_completo)
            nome_item.setData(Qt.UserRole, l)
            self.localita_table.setItem(row, 1, nome_item)
            
            # Tipo
            self.localita_table.setItem(row, 2, QTableWidgetItem(l.get('tipo', '')))
            
            # Comune
            self.localita_table.setItem(row, 3, QTableWidgetItem(l.get('comune_nome', '')))
            
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
            self.localita_table.setItem(row, 4, sim_item)
            
            # Pulsante azioni
            action_btn = QPushButton("📋")
            action_btn.clicked.connect(
                lambda checked, eid=l.get('id'): 
                self._show_entity_details('localita', eid)
            )
            self.localita_table.setCellWidget(row, 5, action_btn)
    
    def _populate_localita_expanded(self, localita):
        """Popola la tabella località dal formato expanded."""
        self.localita_table.setRowCount(len(localita))
        
        for row, loc in enumerate(localita):
            info = loc.get('additional_info', {})
            
            self.localita_table.setItem(row, 0, QTableWidgetItem(str(loc.get('entity_id', ''))))
            self.localita_table.setItem(row, 1, QTableWidgetItem(loc.get('display_text', '')))
            self.localita_table.setItem(row, 2, QTableWidgetItem(info.get('tipo', 'N/A')))
            self.localita_table.setItem(row, 3, QTableWidgetItem(info.get('comune', 'N/A')))
            self.localita_table.setItem(row, 4, QTableWidgetItem(f"{loc.get('similarity_score', 0):.3f}"))
            
            # Pulsante azioni
            action_btn = QPushButton("📋")
            action_btn.clicked.connect(
                lambda checked, eid=loc.get('entity_id'): 
                self._show_entity_details('localita', eid)
            )
            self.localita_table.setCellWidget(row, 5, action_btn)
    
    def _populate_variazioni_table(self, variazioni):
        """Popola la tabella delle variazioni (formato standard)."""
        self.variazioni_table.setRowCount(len(variazioni))
        
        for row, v in enumerate(variazioni):
            # ID
            self.variazioni_table.setItem(row, 0, QTableWidgetItem(str(v.get('id', ''))))
            
            # Tipo
            tipo_item = QTableWidgetItem(v.get('tipo', ''))
            tipo_item.setData(Qt.UserRole, v)
            self.variazioni_table.setItem(row, 1, tipo_item)
            
            # Da partita
            self.variazioni_table.setItem(row, 2, QTableWidgetItem(str(v.get('partita_origine_id', ''))))
            
            # A partita
            self.variazioni_table.setItem(row, 3, QTableWidgetItem(str(v.get('partita_destinazione_id', ''))))
            
            # Data
            data = v.get('data_variazione', '')
            if isinstance(data, str) and len(data) > 10:
                data = data[:10]
            self.variazioni_table.setItem(row, 4, QTableWidgetItem(str(data)))
            
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
            self.variazioni_table.setItem(row, 5, sim_item)
            
            # Campo ricerca
            self.variazioni_table.setItem(row, 6, QTableWidgetItem(v.get('search_field', '')))
    
    def _populate_variazioni_expanded(self, variazioni):
        """Popola la tabella variazioni dal formato expanded."""
        self.variazioni_table.setRowCount(len(variazioni))
        
        for row, variazione in enumerate(variazioni):
            info = variazione.get('additional_info', {})
            
            self.variazioni_table.setItem(row, 0, QTableWidgetItem(str(variazione.get('entity_id', ''))))
            self.variazioni_table.setItem(row, 1, QTableWidgetItem(variazione.get('display_text', '')))
            
            # Estrai da detail_text o additional_info
            detail_parts = variazione.get('detail_text', '').split(' - ')
            if len(detail_parts) >= 2:
                partite_info = detail_parts[0].replace('Partita ', '')
                self.variazioni_table.setItem(row, 2, QTableWidgetItem(partite_info.split(' → ')[0]))
                if ' → ' in partite_info:
                    self.variazioni_table.setItem(row, 3, QTableWidgetItem(partite_info.split(' → ')[1]))
                else:
                    self.variazioni_table.setItem(row, 3, QTableWidgetItem('N/A'))
            else:
                self.variazioni_table.setItem(row, 2, QTableWidgetItem('N/A'))
                self.variazioni_table.setItem(row, 3, QTableWidgetItem('N/A'))
                
            # Data variazione
            data_var = info.get('data_variazione', 'N/A')
            if hasattr(data_var, 'strftime'):
                data_var = data_var.strftime('%d/%m/%Y')
            self.variazioni_table.setItem(row, 4, QTableWidgetItem(str(data_var)))
            
            self.variazioni_table.setItem(row, 5, QTableWidgetItem(f"{variazione.get('similarity_score', 0):.3f}"))
            self.variazioni_table.setItem(row, 6, QTableWidgetItem(variazione.get('search_field', '')))
    
    def _populate_immobili_table(self, immobili):
        """Popola la tabella degli immobili (formato standard)."""
        self.immobili_table.setRowCount(len(immobili))
        
        for row, i in enumerate(immobili):
            # ID
            self.immobili_table.setItem(row, 0, QTableWidgetItem(str(i.get('id', ''))))
            
            # Natura
            natura = i.get('natura', '')
            natura_item = QTableWidgetItem(natura)
            natura_item.setData(Qt.UserRole, i)
            self.immobili_table.setItem(row, 1, natura_item)
            
            # Partita con suffisso
            numero_partita = str(i.get('numero_partita', ''))
            suffisso = str(i.get('suffisso', ''))
            partita_completa = f"{numero_partita}/{suffisso}" if suffisso else numero_partita
            self.immobili_table.setItem(row, 2, QTableWidgetItem(partita_completa))
            
            # Località
            self.immobili_table.setItem(row, 3, QTableWidgetItem(i.get('localita', '')))
            
            # Comune
            self.immobili_table.setItem(row, 4, QTableWidgetItem(i.get('comune', '')))
            
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
            
            # Campo ricerca
            self.immobili_table.setItem(row, 6, QTableWidgetItem(i.get('search_field', '')))
    
    def _populate_immobili_expanded(self, immobili):
        """Popola la tabella immobili dal formato expanded."""
        self.immobili_table.setRowCount(len(immobili))
        
        for row, immobile in enumerate(immobili):
            info = immobile.get('additional_info', {})
            
            self.immobili_table.setItem(row, 0, QTableWidgetItem(str(immobile.get('entity_id', ''))))
            self.immobili_table.setItem(row, 1, QTableWidgetItem(immobile.get('display_text', '')))
            
            # Partita completa
            numero = info.get('partita', info.get('numero_partita', 'N/A'))
            suffisso = info.get('suffisso_partita', '')
            if suffisso and suffisso.strip():
                partita_completa = f"{numero} {suffisso.strip()}"
            else:
                partita_completa = str(numero)
            self.immobili_table.setItem(row, 2, QTableWidgetItem(partita_completa))
            
            self.immobili_table.setItem(row, 3, QTableWidgetItem(info.get('localita', 'N/A')))
            self.immobili_table.setItem(row, 4, QTableWidgetItem(info.get('comune', 'N/A')))
            self.immobili_table.setItem(row, 5, QTableWidgetItem(f"{immobile.get('similarity_score', 0):.3f}"))
            self.immobili_table.setItem(row, 6, QTableWidgetItem(immobile.get('search_field', '')))
    
    def _populate_contratti_table(self, contratti):
        """Popola la tabella dei contratti (formato standard)."""
        self.contratti_table.setRowCount(len(contratti))
        
        for row, c in enumerate(contratti):
            # ID
            self.contratti_table.setItem(row, 0, QTableWidgetItem(str(c.get('id', ''))))
            
            # Tipo
            tipo_item = QTableWidgetItem(c.get('tipo', ''))
            tipo_item.setData(Qt.UserRole, c)
            self.contratti_table.setItem(row, 1, tipo_item)
            
            # Data
            data = c.get('data_stipula', c.get('data_contratto', ''))
            if isinstance(data, str) and len(data) > 10:
                data = data[:10]
            self.contratti_table.setItem(row, 2, QTableWidgetItem(str(data)))
            
            # Notaio
            self.contratti_table.setItem(row, 3, QTableWidgetItem(c.get('notaio', '')))
            
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
            self.contratti_table.setItem(row, 4, sim_item)
            
            # Campo ricerca
            self.contratti_table.setItem(row, 5, QTableWidgetItem(c.get('search_field', '')))
    
    def _populate_contratti_expanded(self, contratti):
        """Popola la tabella contratti dal formato expanded."""
        self.contratti_table.setRowCount(len(contratti))
        
        for row, contratto in enumerate(contratti):
            info = contratto.get('additional_info', {})
            
            self.contratti_table.setItem(row, 0, QTableWidgetItem(str(contratto.get('entity_id', ''))))
            self.contratti_table.setItem(row, 1, QTableWidgetItem(contratto.get('display_text', '')))
            
            # Data contratto
            data_contr = info.get('data_contratto', 'N/A')
            if hasattr(data_contr, 'strftime'):
                data_contr = data_contr.strftime('%d/%m/%Y')
            self.contratti_table.setItem(row, 2, QTableWidgetItem(str(data_contr)))
            
            self.contratti_table.setItem(row, 3, QTableWidgetItem(info.get('notaio', 'N/A')))
            self.contratti_table.setItem(row, 4, QTableWidgetItem(f"{contratto.get('similarity_score', 0):.3f}"))
            self.contratti_table.setItem(row, 5, QTableWidgetItem(contratto.get('search_field', '')))
    
    def _populate_partite_table(self, partite):
        """Popola la tabella delle partite (formato standard)."""
        self.partite_table.setRowCount(len(partite))
        
        for row, p in enumerate(partite):
            # ID
            self.partite_table.setItem(row, 0, QTableWidgetItem(str(p.get('id', ''))))
            
            # Numero
            numero_item = QTableWidgetItem(str(p.get('numero_partita', '')))
            numero_item.setData(Qt.UserRole, p)
            self.partite_table.setItem(row, 1, numero_item)
            
            # Suffisso
            self.partite_table.setItem(row, 2, QTableWidgetItem(p.get('suffisso_partita', '')))
            
            # Comune
            self.partite_table.setItem(row, 3, QTableWidgetItem(p.get('comune_nome', '')))
            
            # Stato
            self.partite_table.setItem(row, 4, QTableWidgetItem(p.get('stato', '')))
            
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
            self.partite_table.setItem(row, 5, sim_item)
            
            # Campo ricerca
            self.partite_table.setItem(row, 6, QTableWidgetItem(p.get('search_field', '')))
    
    def _populate_partite_expanded(self, partite):
        """Popola la tabella partite dal formato expanded."""
        self.partite_table.setRowCount(len(partite))
        
        for row, partita in enumerate(partite):
            info = partita.get('additional_info', {})
            
            self.partite_table.setItem(row, 0, QTableWidgetItem(str(partita.get('entity_id', ''))))
            self.partite_table.setItem(row, 1, QTableWidgetItem(str(info.get('numero_partita', 'N/A'))))
            self.partite_table.setItem(row, 2, QTableWidgetItem(info.get('suffisso_partita', '') or ''))
            self.partite_table.setItem(row, 3, QTableWidgetItem(info.get('comune', 'N/A')))
            self.partite_table.setItem(row, 4, QTableWidgetItem(info.get('stato', 'N/A')))
            self.partite_table.setItem(row, 5, QTableWidgetItem(f"{partita.get('similarity_score', 0):.3f}"))
            self.partite_table.setItem(row, 6, QTableWidgetItem(partita.get('search_field', '')))
    
    def _update_tab_counters(self, results):
        """Aggiorna i contatori nei tab."""
        if 'results_by_type' in results:
            # Formato expanded
            counts = {
                'possessori': len(results['results_by_type'].get('possessore', [])),
                'localita': len(results['results_by_type'].get('localita', [])),
                'variazioni': len(results['results_by_type'].get('variazione', [])),
                'immobili': len(results['results_by_type'].get('immobile', [])),
                'contratti': len(results['results_by_type'].get('contratto', [])),
                'partite': len(results['results_by_type'].get('partita', []))
            }
        else:
            # Formato standard
            counts = {
                'possessori': len(results.get('possessori', [])),
                'localita': len(results.get('localita', [])),
                'variazioni': len(results.get('variazioni', [])),
                'immobili': len(results.get('immobili', [])),
                'contratti': len(results.get('contratti', [])),
                'partite': len(results.get('partite', []))
            }
        
        self.results_tabs.setTabText(1, f"👥 Possessori ({counts['possessori']})")
        self.results_tabs.setTabText(2, f"🏘️ Località ({counts['localita']})")
        self.results_tabs.setTabText(3, f"📋 Variazioni ({counts['variazioni']})")
        self.results_tabs.setTabText(4, f"🏢 Immobili ({counts['immobili']})")
        self.results_tabs.setTabText(5, f"📄 Contratti ({counts['contratti']})")
        self.results_tabs.setTabText(6, f"📊 Partite ({counts['partite']})")
    
    def _clear_results(self):
        """Pulisce tutti i risultati."""
        for table in [self.unified_table, self.possessori_table, self.localita_table, 
                     self.variazioni_table, self.immobili_table, self.contratti_table, 
                     self.partite_table]:
            table.setRowCount(0)
        
        # Reset contatori tab
        self.results_tabs.setTabText(1, "👥 Possessori")
        self.results_tabs.setTabText(2, "🏘️ Località")
        self.results_tabs.setTabText(3, "📋 Variazioni")
        self.results_tabs.setTabText(4, "🏢 Immobili")
        self.results_tabs.setTabText(5, "📄 Contratti")
        self.results_tabs.setTabText(6, "📊 Partite")
        
        # Disabilita export
        self.export_btn.setEnabled(False)
        self.results_count_label.setText("0 risultati")
        
        self.current_results = {}
    
    def _handle_search_error(self, error_message):
        """Gestisce errori di ricerca."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Errore ricerca")
        self.status_label.setStyleSheet("color: red; font-size: 10px;")
        QMessageBox.critical(self, "Errore Ricerca", f"Errore durante la ricerca:\n{error_message}")
    
    def _search_finished(self):
        """Chiamato quando la ricerca termina."""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
    
    def _clear_search(self):
        """Pulisce la ricerca."""
        self.search_edit.clear()
        self._clear_results()
        self.status_label.setText("Ricerca pulita")
    
    # ========================================================================
    # METODI PER EXPORT
    # ========================================================================
    
    def _export_results(self):
        """Export che supporta tutti i formati."""
        if not self.current_results or (
            'total_results' in self.current_results and 
            self.current_results['total_results'] == 0
        ):
            QMessageBox.warning(self, "Attenzione", "Nessun risultato da esportare")
            return
        
        # Dialog per scegliere il formato
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Esporta Risultati",
            f"ricerca_fuzzy_{timestamp}",
            "Text Files (*.txt);;PDF Files (*.pdf);;CSV Files (*.csv);;JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            ext = file_path.split('.')[-1].lower()
            
            if ext == 'txt':
                self._export_results_txt(file_path)
            elif ext == 'pdf':
                self._export_results_pdf(file_path)
            elif ext == 'csv':
                self._export_results_csv(file_path)
            elif ext == 'json':
                self._export_results_json(file_path)
            else:
                # Default a TXT se estensione non riconosciuta
                if not file_path.endswith('.txt'):
                    file_path += '.txt'
                self._export_results_txt(file_path)
            
            QMessageBox.information(self, "Export completato", f"Risultati salvati in:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Errore Export", f"Errore durante l'esportazione:\n{e}")
    
    def _export_results_txt(self, filename):
        """Esporta risultati in formato TXT."""
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("RISULTATI RICERCA FUZZY\n")
            f.write("=" * 60 + "\n")
            f.write(f"Query: {self.current_results.get('query_text', 'N/A')}\n")
            f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Export per ogni tipo di risultato
            result_types = [
                ('possessori', 'POSSESSORI', ['nome_completo', 'comune_nome']),
                ('localita', 'LOCALITÀ', ['nome', 'civico', 'comune_nome']),
                ('variazioni', 'VARIAZIONI', ['tipo', 'data_variazione', 'descrizione']),
                ('immobili', 'IMMOBILI', ['natura', 'classificazione', 'comune_nome']),
                ('contratti', 'CONTRATTI', ['tipo', 'data_stipula']),
                ('partite', 'PARTITE', ['numero_partita', 'tipo_partita', 'comune_nome'])
            ]
            
            for key, title, fields in result_types:
                items = self.current_results.get(key, [])
                if items:
                    f.write(f"{title} ({len(items)})\n")
                    f.write("-" * 40 + "\n")
                    for item in items:
                        text_parts = []
                        for field in fields:
                            if field in item and item[field]:
                                text_parts.append(str(item[field]))
                        f.write(f"• {' - '.join(text_parts)} (Similarità: {item.get('similarity_score', 0):.1%})\n")
                    f.write("\n")
    
    def _export_results_pdf(self, filename):
        """Esporta risultati in formato PDF usando fpdf."""
        try:
            from fpdf import FPDF
            
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
            
            # Sezioni risultati
            sections = [
                ('possessori', 'POSSESSORI', ['Nome', 'Comune', 'Simil.'], 
                 lambda p: [p.get('nome_completo', 'N/A'), 
                           p.get('comune_nome', 'N/A'), 
                           f"{p.get('similarity_score', 0):.1%}"],
                 [80, 70, 40]),
                
                ('localita', 'LOCALITÀ', ['Nome', 'Comune', 'Simil.'],
                 lambda l: [f"{l.get('nome', 'N/A')} {l.get('civico', '')}".strip(),
                           l.get('comune_nome', 'N/A'),
                           f"{l.get('similarity_score', 0):.1%}"],
                 [80, 70, 40])
            ]
            
            for key, title, headers, get_row, widths in sections:
                items = self.current_results.get(key, [])
                if items:
                    # Controlla se serve nuova pagina
                    if pdf.get_y() > 250:
                        pdf.add_page()
                    
                    # Titolo sezione
                    pdf.set_font('Arial', 'B', 14)
                    pdf.cell(0, 10, f"{title} ({len(items)})", 0, 1)
                    pdf.ln(2)
                    
                    # Header tabella
                    pdf.set_font('Arial', 'B', 10)
                    pdf.set_fill_color(200, 200, 200)
                    for i, (header, width) in enumerate(zip(headers, widths)):
                        pdf.cell(width, 8, header, 1, 0, 'C', 1)
                    pdf.ln()
                    
                    # Dati
                    pdf.set_font('Arial', '', 9)
                    pdf.set_fill_color(245, 245, 245)
                    
                    for idx, item in enumerate(items[:50]):  # Max 50 per tipo
                        if pdf.get_y() > 260:
                            pdf.add_page()
                            # Ripeti header
                            pdf.set_font('Arial', 'B', 10)
                            pdf.set_fill_color(200, 200, 200)
                            for i, (header, width) in enumerate(zip(headers, widths)):
                                pdf.cell(width, 8, header, 1, 0, 'C', 1)
                            pdf.ln()
                            pdf.set_font('Arial', '', 9)
                            pdf.set_fill_color(245, 245, 245)
                        
                        row_data = get_row(item)
                        fill = idx % 2 == 0
                        
                        for value, width in zip(row_data, widths):
                            if isinstance(value, str) and len(value) > width/2:
                                value = value[:int(width/2)-3] + '...'
                            pdf.cell(width, 7, str(value), 1, 0, 'L', fill)
                        pdf.ln()
                    
                    pdf.ln(5)
            
            # Salva il PDF
            pdf.output(filename)
            
        except ImportError:
            QMessageBox.warning(
                self, "Libreria mancante", 
                "Per l'esportazione PDF è necessaria la libreria fpdf.\n\n"
                "Installa con: pip install fpdf"
            )
    
    def _export_results_csv(self, filename):
        """Esporta risultati in formato CSV."""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header generale
            writer.writerow(['RISULTATI RICERCA FUZZY'])
            writer.writerow(['Query:', self.current_results.get('query_text', 'N/A')])
            writer.writerow(['Data:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            
            # Export per tipo
            export_configs = [
                ('possessori', ['Tipo', 'Nome Completo', 'Comune', 'Similarità']),
                ('localita', ['Tipo', 'Nome', 'Civico', 'Comune', 'Similarità']),
                ('immobili', ['Tipo', 'Natura', 'Classificazione', 'Comune', 'Similarità']),
                ('variazioni', ['Tipo', 'Tipo Variazione', 'Data', 'Descrizione', 'Similarità']),
                ('contratti', ['Tipo', 'Tipo Contratto', 'Data', 'Partita', 'Similarità']),
                ('partite', ['Tipo', 'Numero', 'Tipo Partita', 'Comune', 'Similarità'])
            ]
            
            for entity_type, headers in export_configs:
                items = self.current_results.get(entity_type, [])
                if items:
                    writer.writerow(headers)
                    for item in items:
                        row = [entity_type.upper()]
                        if entity_type == 'possessori':
                            row.extend([
                                item.get('nome_completo', ''),
                                item.get('comune_nome', ''),
                                f"{item.get('similarity_score', 0):.3f}"
                            ])
                        elif entity_type == 'localita':
                            row.extend([
                                item.get('nome', ''),
                                item.get('civico', ''),
                                item.get('comune_nome', ''),
                                f"{item.get('similarity_score', 0):.3f}"
                            ])
                        # ... altri tipi ...
                        writer.writerow(row)
                    writer.writerow([])
    
    def _export_results_json(self, filename):
        """Esporta risultati in formato JSON."""
        export_data = {
            'query': self.current_results.get('query_text', 'N/A'),
            'timestamp': datetime.now().isoformat(),
            'threshold': self.current_results.get('threshold', 0),
            'results': {}
        }
        
        # Copia risultati escludendo metadati
        for key in ['possessori', 'localita', 'variazioni', 'immobili', 'contratti', 'partite']:
            if key in self.current_results:
                export_data['results'][key] = self.current_results[key]
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False, default=str)
    
    # ========================================================================
    # METODI GESTIONE DOPPIO CLICK
    # ========================================================================
    
    def _on_entity_double_click(self, entity_type):
        """Gestisce il doppio click nelle tab specifiche."""
        # Mappa tipo entità -> tabella
        table_map = {
            'possessore': self.possessori_table,
            'localita': self.localita_table,
            'variazione': self.variazioni_table,
            'immobile': self.immobili_table,
            'contratto': self.contratti_table,
            'partita': self.partite_table
        }
        
        table = table_map.get(entity_type)
        if not table:
            return
            
        current_row = table.currentRow()
        if current_row >= 0:
            id_item = table.item(current_row, 0)
            if id_item:
                entity_id = int(id_item.text()) if id_item.text().isdigit() else None
                if entity_id:
                    self._show_entity_details(entity_type, entity_id)
    
    def _on_unified_double_click(self, index):
        """Gestisce il doppio click nella tab unificata."""
        if index.isValid():
            row = index.row()
            item = self.unified_table.item(row, 0)
            if item:
                data = item.data(Qt.UserRole)
                if isinstance(data, dict):
                    entity_type = data.get('entity_type')
                    entity_id = data.get('entity_id')
                    if entity_type and entity_id:
                        self._show_entity_details(entity_type, entity_id)
    
    def _show_entity_details(self, entity_type, entity_id):
        """Mostra i dettagli usando il dialog avanzato."""
        try:
            # Usa il dialog generico per dettagli
            dialog = EntityDetailsDialog(self.db_manager, entity_type, entity_id, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore apertura dettagli: {str(e)}")

# ========================================================================
# FUNZIONI DI INTEGRAZIONE
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
        fuzzy_widget = FuzzySearchWidget(main_window.db_manager, main_window)
        
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

def integrate_expanded_fuzzy_search_widget(main_gui, db_manager):
    """Integra il widget di ricerca fuzzy."""
    fuzzy_widget = FuzzySearchWidget(db_manager)
    
    if hasattr(main_gui, 'tab_widget') or hasattr(main_gui, 'tabs'):
        tab_widget = getattr(main_gui, 'tab_widget', getattr(main_gui, 'tabs', None))
        if tab_widget:
            tab_widget.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
            print("Widget ricerca fuzzy integrato come nuovo tab")
    else:
        print("ATTENZIONE: GUI non ha tab_widget/tabs, integrazione manuale necessaria")
        
    return fuzzy_widget

# ========================================================================
# ALIAS PER RETROCOMPATIBILITÀ
# ========================================================================

# Classi
UnifiedFuzzySearchWidget = FuzzySearchWidget  # Alias per compatibilità
CompactFuzzySearchWidget = FuzzySearchWidget  # Tutto è expanded ora
ExpandedFuzzySearchWidget = FuzzySearchWidget
ExpandedFuzzySearchWorker = FuzzySearchThread

# Funzioni di integrazione
add_working_fuzzy_search_tab_to_main_window = add_fuzzy_search_tab_to_main_window
add_enhanced_fuzzy_search_tab_to_main_window = add_fuzzy_search_tab_to_main_window
add_optimized_fuzzy_search_tab_to_main_window = add_fuzzy_search_tab_to_main_window
add_complete_fuzzy_search_tab_to_main_window = add_fuzzy_search_tab_to_main_window

# Export per convenienza
FUZZY_SEARCH_AVAILABLE = GIN_AVAILABLE

# ========================================================================
# ESEMPIO DI UTILIZZO STANDALONE
# ========================================================================

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    
    # Simula un database manager per test
    class MockDBManager:
        def __init__(self):
            self.schema = "catasto"
    
    # Test widget
    print("Test widget ricerca fuzzy completo:")
    widget = FuzzySearchWidget(MockDBManager())
    widget.setWindowTitle("Ricerca Fuzzy - Sistema Catasto")
    widget.resize(1200, 800)
    widget.show()
    
    sys.exit(app.exec_())
