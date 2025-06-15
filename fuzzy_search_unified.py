#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
<<<<<<< HEAD
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
=======
Widget Unificato per Ricerca Fuzzy nel Database Catasto
========================================================
File: fuzzy_search_unified.py
Autore: Marco Santoro
Data: 12/06/2025
Versione: 4.0 (Logica Unificata)

Descrizione:
Questa versione elimina la distinzione tra modalità 'compact' e 'expanded',
adottando un'unica interfaccia robusta e completa per la ricerca fuzzy.
La logica condizionale basata sul parametro 'mode' è stata rimossa per
semplificare il codice e risolvere errori di attributo.
>>>>>>> new_entry
"""

import logging
import time
import json
import csv
from datetime import datetime,date
from typing import Optional, List, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QGroupBox,
    QSlider, QCheckBox, QComboBox, QProgressBar, QFrame, QHeaderView,
    QMessageBox, QApplication, QFileDialog, QDialog, QSpinBox,
    QSplitter, QScrollArea, QFormLayout, QDialogButtonBox, QSpacerItem,
    QSizePolicy,QMessageBox, QApplication, QFileDialog, QDialog 
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
<<<<<<< HEAD
from PyQt5.QtGui import QColor, QFont, QPalette

# ========================================================================
# VERIFICA E IMPORT DELLE ESTENSIONI GIN
# ========================================================================

# Prova a importare l'estensione expanded (più completa)
=======
from PyQt5.QtGui import QColor, QFont
from dialogs import PartitaDetailsDialog, ModificaPossessoreDialog, ModificaLocalitaDialog
from app_utils import _get_default_export_path, prompt_to_open_file

>>>>>>> new_entry
try:
    from dialogs import ModificaImmobileDialog
except ImportError:
    ModificaImmobileDialog = None # Fallback se non esiste


try:
    from app_utils import BulkReportPDF, FPDF_AVAILABLE
except ImportError:
    FPDF_AVAILABLE = False
    class BulkReportPDF: pass
# ========================================================================
# THREAD PER RICERCHE IN BACKGROUND
# ========================================================================

<<<<<<< HEAD
class FuzzySearchThread(QThread):
    """Thread per eseguire ricerche fuzzy in background."""
    
=======
class UnifiedFuzzySearchThread(QThread):
    """Thread unificato per eseguire ricerche fuzzy in background."""
>>>>>>> new_entry
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, gin_search_manager, query_text, options):
        super().__init__()
        self.gin_search_manager = gin_search_manager
        self.query_text = query_text
        self.options = options

    def run(self):
<<<<<<< HEAD
        """Esegue la ricerca fuzzy unificata."""
=======
        """Esegue la ricerca fuzzy."""
>>>>>>> new_entry
        try:
            self.progress_updated.emit(10)
            
            threshold = self.options.get('threshold', 0.3)
<<<<<<< HEAD
            max_results_per_type = self.options.get('max_results_per_type', 30)
            
            self.progress_updated.emit(30)
            
            # CORREZIONE: Passare threshold come secondo parametro
            if hasattr(self.gin_search, 'search_all_entities_fuzzy'):
                results = self.gin_search.search_all_entities_fuzzy(
                    self.query_text,
                    threshold,  # ← AGGIUNTO: parametro threshold
                    search_possessori=self.options.get('search_possessori', True),
                    search_localita=self.options.get('search_localita', True),
                    search_immobili=self.options.get('search_immobili', True),
                    search_variazioni=self.options.get('search_variazioni', True),
                    search_contratti=self.options.get('search_contratti', True),
                    search_partite=self.options.get('search_partite', True),
                    max_results_per_type=max_results_per_type
                )
            else:
                # Fallback con ricerche individuali..
                
                # Ricerca possessori
                if self.options.get('search_possessori', True):
                    current_step += 1
                    self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                    if hasattr(self.gin_search, 'search_possessori_fuzzy'):
                        possessori = self.gin_search.search_possessori_fuzzy(
                            self.query_text, threshold, max_results
                        )
                        results['possessori'] = possessori or []
                
                # Ricerca località
                if self.options.get('search_localita', True):
                    current_step += 1
                    self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                    if hasattr(self.gin_search, 'search_localita_fuzzy'):
                        localita = self.gin_search.search_localita_fuzzy(
                            self.query_text, threshold, max_results
                        )
                        results['localita'] = localita or []
                
                # Ricerca variazioni
                if self.options.get('search_variazioni', True):
                    current_step += 1
                    self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                    if hasattr(self.gin_search, 'search_variazioni_fuzzy'):
                        variazioni = self.gin_search.search_variazioni_fuzzy(
                            self.query_text, threshold, max_results
                        )
                        results['variazioni'] = variazioni or []
                
                # Ricerca immobili
                if self.options.get('search_immobili', True):
                    current_step += 1
                    self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                    if hasattr(self.gin_search, 'search_immobili_fuzzy'):
                        immobili = self.gin_search.search_immobili_fuzzy(
                            self.query_text, threshold, max_results
                        )
                        results['immobili'] = immobili or []
                
                # Ricerca contratti
                if self.options.get('search_contratti', True):
                    current_step += 1
                    self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                    if hasattr(self.gin_search, 'search_contratti_fuzzy'):
                        contratti = self.gin_search.search_contratti_fuzzy(
                            self.query_text, threshold, max_results
                        )
                        results['contratti'] = contratti or []
                
                # Ricerca partite
                if self.options.get('search_partite', True):
                    current_step += 1
                    self.progress_updated.emit(int(20 + (current_step * 60 / total_steps)))
                    if hasattr(self.gin_search, 'search_partite_fuzzy'):
                        partite = self.gin_search.search_partite_fuzzy(
                            self.query_text, threshold, max_results
                        )
                        results['partite'] = partite or []
            
            # Aggiungi metadati
            results['query_text'] = self.query_text
            results['threshold'] = threshold
            results['timestamp'] = datetime.now()
            results['search_type'] = search_type
            
            # Calcola totale risultati
            if 'results_by_type' in results:
                total = sum(len(entities) for entities in results['results_by_type'].values())
            else:
                total = sum(len(entities) for key, entities in results.items() 
                          if isinstance(entities, list))
            results['total_results'] = total
            
=======
            max_results = self.options.get('max_results', 100)

            # --- MODIFICA: Logica di ricerca semplificata ---
            # Questo thread ora chiama un metodo unificato che a sua volta
            # orchestra le ricerche individuali.
            # Assumiamo che `gin_search_manager` abbia un metodo come `search_all_entities_fuzzy`.
            if not hasattr(self.gin_search_manager, 'search_all_entities_fuzzy'):
                self.error_occurred.emit("Il DB Manager non supporta 'search_all_entities_fuzzy'.")
                return

            self.progress_updated.emit(30)

            results_data = self.gin_search_manager.search_all_entities_fuzzy(
                query_text=self.query_text,
                search_possessori=self.options.get('search_possessori', True),
                search_localita=self.options.get('search_localita', True),
                search_immobili=self.options.get('search_immobili', True),
                search_variazioni=self.options.get('search_variazioni', True),
                search_contratti=self.options.get('search_contratti', True),
                search_partite=self.options.get('search_partite', True),
                max_results_per_type=self.options.get('max_results_per_type', 50),
                similarity_threshold=threshold
            )

            # Prepara il dizionario finale per l'emissione del segnale
            final_results = {
                'query_text': self.query_text,
                'threshold': threshold,
                'timestamp': datetime.now(),
                'total_results': sum(len(entities) for entities in results_data.values()),
                'results_by_type': results_data # Mantiene la struttura per tipo
            }

>>>>>>> new_entry
            self.progress_updated.emit(100)
            self.results_ready.emit(final_results)

        except Exception as e:
            logging.getLogger(__name__).error(f"Errore nel thread di ricerca: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
<<<<<<< HEAD
    def _verify_available_functions(self):
        """Verifica quali funzioni di ricerca sono disponibili."""
        if not self.gin_search:
            return {}
        
        available_functions = {}
        functions_to_check = [
            'search_possessori_fuzzy',
            'search_localita_fuzzy', 
            'search_immobili_fuzzy',
            'search_variazioni_fuzzy',
            'search_contratti_fuzzy',
            'search_partite_fuzzy',
            'search_all_entities_fuzzy',
            'verify_gin_indices'
        ]
        
        for func_name in functions_to_check:
            available_functions[func_name] = hasattr(self.gin_search, func_name)
            if not available_functions[func_name]:
                self.logger.warning(f"Funzione {func_name} non disponibile")
        
        return available_functions
=======


>>>>>>> new_entry
# ========================================================================
# DIALOG PER DETTAGLI ENTITÀ
# ========================================================================

<<<<<<< HEAD
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
    
=======
class UnifiedFuzzySearchWidget(QWidget):
    """Widget unificato per ricerca fuzzy con una singola interfaccia robusta."""

    # --- MODIFICA: Il costruttore non ha più il parametro 'mode' ---
>>>>>>> new_entry
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.parent_window = parent
        self.logger = logging.getLogger(__name__)

        # Inizializza componenti GIN. Assumiamo che db_manager sia già esteso.
        self.gin_search = self.db_manager

        # Variabili di stato
        self.current_results = {}
        self.search_thread = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
<<<<<<< HEAD
        
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
=======

        # Setup UI
        self._init_ui() # --- MODIFICA: Chiamata a un singolo metodo di setup UI
        self._setup_signals()
        self._check_gin_status()

  

    def _init_ui(self):
        """Configura l'interfaccia utente unificata con un layout robusto."""
        # Layout principale dell'intero widget
>>>>>>> new_entry
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # --- INIZIO NUOVA STRUTTURA ---
        # 1. Creiamo un widget contenitore per tutti i contenuti tranne la status bar
        content_container_widget = QWidget()
        content_layout = QVBoxLayout(content_container_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        # --- FINE NUOVA STRUTTURA ---

        # === AREA RICERCA (da aggiungere al content_layout) ===
        search_frame = QFrame()
        search_frame.setFrameStyle(QFrame.StyledPanel)
        search_frame.setMaximumHeight(120)
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(10, 8, 10, 8)
        # ... (il codice interno di search_frame, search_row, controls_row rimane identico)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca in possessori, località, immobili, variazioni, contratti, partite...")
        search_row.addWidget(self.search_edit, 1)
        self.search_btn = QPushButton("Cerca")
        search_row.addWidget(self.search_btn)
        self.clear_btn = QPushButton("🗑️")
        self.clear_btn.setMaximumWidth(30)
        search_row.addWidget(self.clear_btn)
        search_layout.addLayout(search_row)
        # --- BLOCCO "CONTROLLI AVANZATI" DA SOSTITUIRE ---
        controls_row = QHBoxLayout()
<<<<<<< HEAD
        
        # Tipo di ricerca
        controls_row.addWidget(QLabel("Tipo:"))
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems([
            "Unificata", "Solo Immobili", "Solo Variazioni", 
            "Solo Contratti", "Solo Partite", "Possessori+Località"
        ])
        self.search_type_combo.setMaximumWidth(150)
        controls_row.addWidget(self.search_type_combo)
        
        # Soglia similarità
=======
>>>>>>> new_entry
        controls_row.addWidget(QLabel("Soglia:"))
        self.precision_slider = QSlider(Qt.Horizontal)
        self.precision_slider.setRange(10, 90)
        self.precision_slider.setValue(30)
        self.precision_slider.setMaximumWidth(100)
        controls_row.addWidget(self.precision_slider)

        self.precision_label = QLabel("0.30")
        self.precision_label.setMinimumWidth(30)
        controls_row.addWidget(self.precision_label)

        controls_row.addWidget(QLabel("Max Risultati:"))
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["50", "100", "200", "500"])
        self.max_results_combo.setCurrentText("100")
        self.max_results_combo.setMaximumWidth(70)
        controls_row.addWidget(self.max_results_combo)

        controls_row.addStretch()

        # Creiamo i nuovi pulsanti specifici
        self.btn_export_csv = QPushButton("Esporta CSV")
        self.btn_export_csv.setEnabled(False)
        controls_row.addWidget(self.btn_export_csv)

        self.btn_export_pdf = QPushButton("Esporta PDF")
        self.btn_export_pdf.setEnabled(False)
        if not FPDF_AVAILABLE:
            self.btn_export_pdf.setToolTip("Libreria FPDF2 non trovata. Funzione non disponibile.")
        controls_row.addWidget(self.btn_export_pdf)
        
        # La riga errata "controls_row.addWidget(self.export_btn)" è stata rimossa.
        
        search_layout.addLayout(controls_row)
        # --- FINE BLOCCO DA SOSTITUIRE ---
        
        content_layout.addWidget(search_frame) # AGGIUNTO AL CONTENT_LAYOUT

        # === CHECKBOXES (da aggiungere al content_layout) ===
        types_layout = QHBoxLayout()
<<<<<<< HEAD
        
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
=======
        types_group = QGroupBox("Cerca in:")
        types_group_layout = QHBoxLayout(types_group)
        # ... (tutte le checkbox vengono create e aggiunte a types_group_layout come prima) ...
        self.search_possessori_cb = QCheckBox("👥 Possessori"); self.search_possessori_cb.setChecked(True); types_group_layout.addWidget(self.search_possessori_cb)
        self.search_localita_cb = QCheckBox("🏘️ Località"); self.search_localita_cb.setChecked(True); types_group_layout.addWidget(self.search_localita_cb)
        self.search_immobili_cb = QCheckBox("🏢 Immobili"); self.search_immobili_cb.setChecked(True); types_group_layout.addWidget(self.search_immobili_cb)
        self.search_variazioni_cb = QCheckBox("📋 Variazioni"); self.search_variazioni_cb.setChecked(True); types_group_layout.addWidget(self.search_variazioni_cb)
        self.search_contratti_cb = QCheckBox("📄 Contratti"); self.search_contratti_cb.setChecked(True); types_group_layout.addWidget(self.search_contratti_cb)
        self.search_partite_cb = QCheckBox("📊 Partite"); self.search_partite_cb.setChecked(True); types_group_layout.addWidget(self.search_partite_cb)
        types_layout.addWidget(types_group)

        content_layout.addLayout(types_layout) # AGGIUNTO AL CONTENT_LAYOUT

        # === AREA RISULTATI (da aggiungere al content_layout) ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)
        # ... (tutta la creazione delle tabelle e l'aggiunta a results_tabs rimane identica) ...
        self.unified_table = self._create_table_widget(["Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo"], [1, 2], 3); self.results_tabs.addTab(self.unified_table, "🔍 Tutti")
        self.possessori_table = self._create_table_widget(["Nome Completo", "Comune", "Partite", "Similitud."], [0], 3); self.results_tabs.addTab(self.possessori_table, "👥 Possessori")
        self.localita_table = self._create_table_widget(["Nome", "Tipo", "Civico", "Comune", "Immobili", "Similitud."], [0, 3], 5); self.results_tabs.addTab(self.localita_table, "📍 Località")
        self.immobili_table = self._create_table_widget(["Natura", "Classificazione", "Partita", "Suffisso", "Comune", "Similitud."], [1, 4], 5); self.results_tabs.addTab(self.immobili_table, "🏢 Immobili")
        self.variazioni_table = self._create_table_widget(["Tipo", "Data", "Rif. e Partita Origine", "Similitud."], [2], 3)
        self.results_tabs.addTab(self.variazioni_table, "📋 Variazioni")
        self.contratti_table = self._create_table_widget(["Tipo", "Data", "Partita", "Similitud."], [0], 3); self.results_tabs.addTab(self.contratti_table, "📄 Contratti")
        # --- MODIFICA QUESTA RIGA ---
        self.partite_table = self._create_table_widget(
            ["Numero", "Suffisso", "Possessori", "Tipo", "Stato", "Data Impianto", "Comune", "Similitud."],
            [2, 6],  # Indici delle colonne da espandere (Possessori e Comune)
            7        # L'indice della colonna 'Similitud.' ora è 7
        )
        # --- FINE MODIFICA --- 
        self.results_tabs.addTab(self.partite_table, "📊 Partite")

        content_layout.addWidget(self.results_tabs) # AGGIUNTO AL CONTENT_LAYOUT

        # --- AGGIUNTA DEL CONTENITORE AL LAYOUT PRINCIPALE ---
        # Diamo a tutto il blocco dei contenuti un fattore di stretch > 0
        main_layout.addWidget(content_container_widget, 1)

        # === STATUS BAR (ora separata e sicura) ===
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.StyledPanel)
        status_frame.setFrameShadow(QFrame.Sunken)
        status_frame.setMaximumHeight(30)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(5, 2, 5, 2)
        self.stats_label = QLabel("Inserire almeno 3 caratteri per iniziare")
        status_layout.addWidget(self.stats_label)
        status_layout.addStretch()
        self.indices_status_label = QLabel("Verifica indici...")
        status_layout.addWidget(self.indices_status_label)
        
        # Aggiungiamo la status bar al layout principale senza stretch
        main_layout.addWidget(status_frame)

        self.search_edit.setFocus()

    def _create_table_widget(self, headers, stretch_columns, similarity_col_index):
        """Helper per creare una QTableWidget standardizzata."""
>>>>>>> new_entry
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = table.horizontalHeader()
        for i in range(len(headers)):
            if i in stretch_columns:
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # Salva l'indice della colonna di similarità per usi futuri (es. colorazione)
        table.setProperty("similarity_col", similarity_col_index)
        return table
<<<<<<< HEAD
    
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
=======

    def _setup_signals(self):
        """Configura i segnali."""
>>>>>>> new_entry
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_btn.clicked.connect(self._perform_search)
        self.clear_btn.clicked.connect(self._clear_search)
        
<<<<<<< HEAD
        # Aggiornamento slider precisione
        self.precision_slider.valueChanged.connect(
            lambda v: self.precision_label.setText(f"{v/100:.2f}")
        )
        self.precision_slider.valueChanged.connect(self._trigger_search_if_text)
        
        # Cambi opzioni rilanciano ricerca
        self.max_results_combo.currentTextChanged.connect(self._trigger_search_if_text)
        self.search_type_combo.currentTextChanged.connect(self._trigger_search_if_text)
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
    
=======
        self.precision_slider.valueChanged.connect(lambda v: self.precision_label.setText(f"{v/100:.2f}"))
        self.precision_slider.sliderReleased.connect(self._trigger_search_if_text)

        self.max_results_combo.currentTextChanged.connect(self._trigger_search_if_text)
        # --- MODIFICA QUI: Colleghiamo i nuovi pulsanti ---
        # Rimuoviamo la vecchia riga: self.export_btn.clicked.connect(self._export_results)
        self.btn_export_csv.clicked.connect(self._handle_export_csv)
        self.btn_export_pdf.clicked.connect(self._handle_export_pdf)
        # --- FINE MODIFICA ---

        # Checkbox
        for cb in [self.search_possessori_cb, self.search_localita_cb, self.search_immobili_cb,
                   self.search_variazioni_cb, self.search_contratti_cb, self.search_partite_cb]: # AGGIUNTE NUOVE CHECKBOX
            cb.toggled.connect(self._trigger_search_if_text)

        # Double-click
        
        # --- MODIFICA QUI: Colleghiamo il doppio click per tutte le tabelle ---
        self.unified_table.doubleClicked.connect(self._on_unified_double_click)
        self.possessori_table.doubleClicked.connect(self._on_possessori_double_click)
        self.localita_table.doubleClicked.connect(self._on_localita_double_click)
        self.immobili_table.doubleClicked.connect(self._on_immobili_double_click)
        self.variazioni_table.doubleClicked.connect(self._on_variazioni_double_click)
        self.contratti_table.doubleClicked.connect(self._on_contratti_double_click)
        self.partite_table.doubleClicked.connect(self._on_partite_double_click)
        # --- FINE MODIFICA ---

>>>>>>> new_entry
    def _check_gin_status(self):
        """Verifica lo stato degli indici GIN."""
        if not self.gin_search or not hasattr(self.gin_search, 'verify_gin_indices'):
            self.indices_status_label.setText("❌ Ricerca non disponibile")
            return
        try:
<<<<<<< HEAD
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
    
=======
            result = self.gin_search.verify_gin_indices()
            if result.get('status') == 'OK' and result.get('gin_indices', 0) > 0:
                self.indices_status_label.setText(f"✅ Indici GIN attivi ({result['gin_indices']})")
            else:
                self.indices_status_label.setText("⚠️ Indici GIN mancanti o non validi")
        except Exception as e:
            self.indices_status_label.setText("❌ Errore verifica indici")
            self.logger.error(f"Errore verifica indici GIN: {e}")

>>>>>>> new_entry
    def _on_search_text_changed(self, text):
        """Gestisce il cambiamento del testo di ricerca."""
        if len(text) >= 3:
<<<<<<< HEAD
            self.search_timer.start(800)
            self.stats_label.setText("Ricerca in corso...")
=======
            self.search_timer.start(800) # Delay per evitare ricerche a ogni tasto
            self.stats_label.setText("Pronto per la ricerca...")
>>>>>>> new_entry
        else:
            self.search_timer.stop()
            self._clear_results()
            self.stats_label.setText(f"Inserire almeno {3 - len(text)} caratteri in più")

    def _trigger_search_if_text(self):
        """Rilancia la ricerca se c'è abbastanza testo."""
        if len(self.search_edit.text().strip()) >= 3:
            self._perform_search()

    def _perform_search(self):
        """Esegue la ricerca vera e propria, gestendo il thread precedente."""
        query_text = self.search_edit.text().strip()
        if len(query_text) < 3:
            return

        if not self.gin_search:
            QMessageBox.warning(self, "Errore", "Sistema di ricerca fuzzy non disponibile.")
            return
<<<<<<< HEAD
        
        # Prepara parametri ricerca
        threshold = self.precision_slider.value() / 100.0
        max_results = int(self.max_results_combo.currentText())
        
        # Determina tipo di ricerca
        search_type = 'unified'
        if hasattr(self, 'search_type_combo'):
            type_map = {
                0: 'unified',
                1: 'immobili', 
                2: 'variazioni',
                3: 'contratti',
                4: 'partite',
                5: 'combined'
            }
            search_type = type_map.get(self.search_type_combo.currentIndex(), 'unified')
        
=======

        # --- MODIFICA CRUCIALE: Gestione del thread esistente ---
        if self.search_thread and self.search_thread.isRunning():
            self.logger.debug("Ricerca precedente ancora in corso. Tentativo di fermarla.")
            self.search_thread.quit()  # Chiede al thread di terminare in modo pulito
            self.search_thread.wait(500) # Attende al massimo 500ms
            if self.search_thread.isRunning():
                self.logger.warning("Il thread precedente non si è fermato in tempo, terminazione forzata.")
                self.search_thread.terminate() # Estrema ratio
                self.search_thread.wait()

>>>>>>> new_entry
        search_options = {
            'threshold': self.precision_slider.value() / 100.0,
            'max_results': int(self.max_results_combo.currentText()),
            'search_possessori': self.search_possessori_cb.isChecked(),
            'search_localita': self.search_localita_cb.isChecked(),
            'search_immobili': self.search_immobili_cb.isChecked(),
            # --- AGGIUNGERE QUESTE OPZIONI ---
            'search_variazioni': self.search_variazioni_cb.isChecked(),
            'search_contratti': self.search_contratti_cb.isChecked(),
            'search_partite': self.search_partite_cb.isChecked(),
        }

        

        self.search_btn.setEnabled(False)
        self.stats_label.setText("Ricerca in corso...")
        
<<<<<<< HEAD
        self.progress_bar.setVisible(True)
        self.status_label.setText("🔍 Ricerca in corso...")
        self.status_label.setStyleSheet("color: blue; font-size: 10px;")
        self.search_btn.setEnabled(False)
        
        self.search_thread = FuzzySearchThread(
            self.gin_search, query_text, search_options
        )
=======
        self.search_thread = UnifiedFuzzySearchThread(self.gin_search, query_text, search_options)
>>>>>>> new_entry
        self.search_thread.results_ready.connect(self._display_results)
        self.search_thread.error_occurred.connect(self._handle_search_error)
        self.search_thread.finished.connect(lambda: self.search_btn.setEnabled(True))
        self.search_thread.start()
<<<<<<< HEAD
    
    def _handle_search_error(self, error_message):
        """Gestisce errori di ricerca."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Errore ricerca")
        self.status_label.setStyleSheet("color: red; font-size: 10px;")
        self.search_btn.setEnabled(True)
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

    def _perform_individual_searches(self, query_text, options):
        """Esegue ricerche individuali con gestione errori robusta."""
        results = {'results_by_type': {}}
        threshold = options.get('threshold', 0.3)
        max_results = options.get('max_results', 100)
        
        # Ricerca possessori
        if options.get('search_possessori', True):
            try:
                if hasattr(self.gin_search, 'search_possessori_fuzzy'):
                    possessori = self.gin_search.search_possessori_fuzzy(
                        query_text, threshold, max_results
                    )
                    if possessori:
                        # Converte al formato unificato
                        results['results_by_type']['possessore'] = [
                            self._convert_possessore_to_unified(p) for p in possessori
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca possessori: {e}")
        
        # Ricerca località
        if options.get('search_localita', True):
            try:
                if hasattr(self.gin_search, 'search_localita_fuzzy'):
                    localita = self.gin_search.search_localita_fuzzy(
                        query_text, threshold, max_results
                    )
                    if localita:
                        results['results_by_type']['localita'] = [
                            self._convert_localita_to_unified(l) for l in localita
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca località: {e}")
        
        # Ricerca immobili
        if options.get('search_immobili', True):
            try:
                if hasattr(self.gin_search, 'search_immobili_fuzzy'):
                    immobili = self.gin_search.search_immobili_fuzzy(
                        query_text, threshold, max_results
                    )
                    if immobili:
                        results['results_by_type']['immobile'] = [
                            self._convert_immobile_to_unified(i) for i in immobili
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca immobili: {e}")
        
        # Ricerca variazioni
        if options.get('search_variazioni', True):
            try:
                if hasattr(self.gin_search, 'search_variazioni_fuzzy'):
                    variazioni = self.gin_search.search_variazioni_fuzzy(
                        query_text, threshold, max_results
                    )
                    if variazioni:
                        results['results_by_type']['variazione'] = [
                            self._convert_variazione_to_unified(v) for v in variazioni
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca variazioni: {e}")
        
        # Ricerca contratti
        if options.get('search_contratti', True):
            try:
                if hasattr(self.gin_search, 'search_contratti_fuzzy'):
                    contratti = self.gin_search.search_contratti_fuzzy(
                        query_text, threshold, max_results
                    )
                    if contratti:
                        results['results_by_type']['contratto'] = [
                            self._convert_contratto_to_unified(c) for c in contratti
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca contratti: {e}")
        
        # Ricerca partite
        if options.get('search_partite', True):
            try:
                if hasattr(self.gin_search, 'search_partite_fuzzy'):
                    partite = self.gin_search.search_partite_fuzzy(
                        query_text, threshold, max_results
                    )
                    if partite:
                        results['results_by_type']['partita'] = [
                            self._convert_partita_to_unified(p) for p in partite
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca partite: {e}")
        
        return results

    
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
                # Formato standard
                self._clear_unified_table()
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
=======

    def _display_results(self, results):
        """Visualizza i risultati della ricerca."""
        self.current_results = results
        results_by_type = results.get('results_by_type', {})
        
        self._populate_unified_table(results_by_type)
        self._populate_individual_tables(results_by_type)
        self._update_tab_counters(results_by_type)
        
        total = results.get('total_results', 0)
        self.stats_label.setText(f"Trovati {total} risultati per '{results.get('query_text')}'")
        # --- MODIFICA QUI ---
        self.btn_export_csv.setEnabled(total > 0)
        if FPDF_AVAILABLE:
            self.btn_export_pdf.setEnabled(total > 0)
        # --- FINE MODIFICA ---
    
    def _populate_table(self, table: QTableWidget, data: List[Dict], row_mapper_func):
        """Funzione helper per popolare una QTableWidget."""
>>>>>>> new_entry
        table.setRowCount(0)
        table.setRowCount(len(data))
        similarity_col = table.property("similarity_col")

        for row_idx, item_data in enumerate(data):
            row_content = row_mapper_func(item_data)
            for col_idx, cell_text in enumerate(row_content):
                item = QTableWidgetItem(str(cell_text))
                if col_idx == 0: # Salva i dati completi nel primo item della riga
                    item.setData(Qt.UserRole, item_data)
                
                # Applica colorazione alla colonna di similarità
                if similarity_col is not None and col_idx == similarity_col:
                    try:
                        similarity = float(cell_text)
                        if similarity > 0.7: item.setBackground(QColor("#d4edda")) # Verde
                        elif similarity > 0.5: item.setBackground(QColor("#fff3cd")) # Giallo
                        else: item.setBackground(QColor("#f8d7da")) # Rosso
                    except (ValueError, TypeError):
                        pass
                
                table.setItem(row_idx, col_idx, item)

    def _populate_unified_table(self, results_by_type: Dict[str, List]):
        self.unified_table.setRowCount(0)
        row = 0
        type_icons = {
            'possessore': '👥', 'localita': '🏘️', 'immobile': '🏢', 
            'variazione': '📋', 'contratto': '📄', 'partita': '📊'
        }
        for entity_type, entities in results_by_type.items():
            for entity in entities:
                self.unified_table.insertRow(row)
                icon = type_icons.get(entity_type, '📁')
                
                # ["Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo"]
                self.unified_table.setItem(row, 0, QTableWidgetItem(f"{icon} {entity_type.title()}"))
                self.unified_table.item(row,0).setData(Qt.UserRole, {'type': entity_type, 'data': entity}) # Salva dati per doppio click
                
                self.unified_table.setItem(row, 1, QTableWidgetItem(entity.get('display_text', '')))
                self.unified_table.setItem(row, 2, QTableWidgetItem(entity.get('detail_text', '')))
                self.unified_table.setItem(row, 3, QTableWidgetItem(f"{entity.get('similarity_score', 0):.3f}"))
                self.unified_table.setItem(row, 4, QTableWidgetItem(entity.get('search_field', '')))
                row += 1
<<<<<<< HEAD
    
    def _clear_unified_table(self):
        """Pulisce la tabella unificata."""
        self.unified_table.setRowCount(0)
    
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
=======

    def _populate_individual_tables(self, results_by_type: Dict[str, List]):
        self._populate_table(self.possessori_table, results_by_type.get('possessore', []), 
            lambda p: [p.get('nome_completo', ''), p.get('comune_nome', ''), p.get('num_partite', 0), f"{p.get('similarity_score', 0):.3f}"])
        
        # --- MODIFICA QUESTA CHIAMATA ---
        self._populate_table(self.localita_table, results_by_type.get('localita', []),
            lambda l: [
                l.get('nome', ''),
                l.get('tipo', '') or '',      # Aggiunto
                l.get('civico', '') or '',    # Aggiunto
                l.get('comune_nome', ''),
                l.get('num_immobili', 0),
                f"{l.get('similarity_score', 0):.3f}"
            ]
        )
        # --- FINE MODIFICA ---
        # --- MODIFICA QUESTA CHIAMATA ---
        self._populate_table(self.immobili_table, results_by_type.get('immobile', []), 
            lambda i: [
                i.get('natura', ''),
                i.get('classificazione', ''),
                i.get('numero_partita', ''),
                i.get('suffisso_partita', '') or '', # Aggiunto il valore per la nuova colonna
                i.get('comune_nome', ''),
                f"{i.get('similarity_score', 0):.3f}"
            ]
        )
        # --- FINE MODIFICA ---

        self._populate_table(self.variazioni_table, results_by_type.get('variazione', []),
            lambda v: [
                v.get('tipo', ''),
                v.get('data_variazione', ''),
                v.get('detail_text', ''), # Usa detail_text per la nuova colonna
                f"{v.get('similarity_score', 0):.3f}"])

        self._populate_table(self.contratti_table, results_by_type.get('contratto', []), 
            lambda c: [c.get('tipo', ''), c.get('data_contratto', ''), c.get('numero_partita', ''), f"{c.get('similarity_score', 0):.3f}"])

        self._populate_table(self.partite_table, results_by_type.get('partita', []), 
            lambda pt: [
                pt.get('numero_partita', ''),
                pt.get('suffisso_partita', '') or '',
                pt.get('possessori_concatenati', '') or '', # NUOVA COLONNA
                pt.get('tipo_partita', ''),
                pt.get('stato', ''),
                str(pt.get('data_impianto', '')) if pt.get('data_impianto') else '',
                pt.get('comune_nome', ''),
                f"{pt.get('similarity_score', 0):.3f}"
            ]
        )
    def _update_tab_counters(self, results_by_type: Dict[str, List]):
        """Aggiorna i contatori nei titoli dei tab."""
        # --- MODIFICA: La logica di base_index non è più necessaria ---
        self.results_tabs.setTabText(0, f"🔍 Tutti ({sum(len(v) for v in results_by_type.values())})")
        self.results_tabs.setTabText(1, f"👥 Possessori ({len(results_by_type.get('possessore', []))})")
        self.results_tabs.setTabText(2, f"🏘️ Località ({len(results_by_type.get('localita', []))})")
        self.results_tabs.setTabText(3, f"🏢 Immobili ({len(results_by_type.get('immobile', []))})")
        # --- AGGIUNGERE QUESTE RIGHE ---
        self.results_tabs.setTabText(4, f"📋 Variazioni ({len(results_by_type.get('variazione', []))})")
        self.results_tabs.setTabText(5, f"📄 Contratti ({len(results_by_type.get('contratto', []))})")
        self.results_tabs.setTabText(6, f"📊 Partite ({len(results_by_type.get('partita', []))})")

    def _clear_results(self):
        """Pulisce tutti i risultati e i contatori."""
        tables = [
            self.unified_table, self.possessori_table, self.localita_table, 
            self.immobili_table, self.variazioni_table, self.contratti_table, 
            self.partite_table
        ]
        for table in tables:
            table.setRowCount(0)
        
        self._update_tab_counters({})
        
        # --- MODIFICA QUI: Disabilita i nuovi pulsanti invece del vecchio ---
        self.btn_export_csv.setEnabled(False)
        self.btn_export_pdf.setEnabled(False)
        # --- FINE MODIFICA ---
>>>>>>> new_entry
        
        self.current_results = {}

    def _handle_search_error(self, error_message):
<<<<<<< HEAD
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
    # CORREZIONE 2: Aggiungere verifica robusta delle funzioni disponibili
    # ========================================================================

    def _verify_available_functions(self):
        """Verifica quali funzioni di ricerca sono disponibili."""
        if not self.gin_search:
            return {}
        
        available_functions = {}
        functions_to_check = [
            'search_possessori_fuzzy',
            'search_localita_fuzzy', 
            'search_immobili_fuzzy',
            'search_variazioni_fuzzy',
            'search_contratti_fuzzy',
            'search_partite_fuzzy',
            'search_all_entities_fuzzy',
            'verify_gin_indices'
        ]
        
        for func_name in functions_to_check:
            available_functions[func_name] = hasattr(self.gin_search, func_name)
            if not available_functions[func_name]:
                self.logger.warning(f"Funzione {func_name} non disponibile")
        
        return available_functions

    # ========================================================================
    # CORREZIONE 3: Gestione sicura delle ricerche individuali
    # ========================================================================

    def _perform_individual_searches(self, query_text, options):
        """Esegue ricerche individuali con gestione errori robusta."""
        results = {'results_by_type': {}}
        threshold = options.get('threshold', 0.3)
        max_results = options.get('max_results', 100)
        
        # Ricerca possessori
        if options.get('search_possessori', True):
            try:
                if hasattr(self.gin_search, 'search_possessori_fuzzy'):
                    possessori = self.gin_search.search_possessori_fuzzy(
                        query_text, threshold, max_results
                    )
                    if possessori:
                        # Converte al formato unificato
                        results['results_by_type']['possessore'] = [
                            self._convert_possessore_to_unified(p) for p in possessori
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca possessori: {e}")
        
        # Ricerca località
        if options.get('search_localita', True):
            try:
                if hasattr(self.gin_search, 'search_localita_fuzzy'):
                    localita = self.gin_search.search_localita_fuzzy(
                        query_text, threshold, max_results
                    )
                    if localita:
                        results['results_by_type']['localita'] = [
                            self._convert_localita_to_unified(l) for l in localita
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca località: {e}")
        
        # Ricerca immobili
        if options.get('search_immobili', True):
            try:
                if hasattr(self.gin_search, 'search_immobili_fuzzy'):
                    immobili = self.gin_search.search_immobili_fuzzy(
                        query_text, threshold, max_results
                    )
                    if immobili:
                        results['results_by_type']['immobile'] = [
                            self._convert_immobile_to_unified(i) for i in immobili
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca immobili: {e}")
        
        # Ricerca variazioni
        if options.get('search_variazioni', True):
            try:
                if hasattr(self.gin_search, 'search_variazioni_fuzzy'):
                    variazioni = self.gin_search.search_variazioni_fuzzy(
                        query_text, threshold, max_results
                    )
                    if variazioni:
                        results['results_by_type']['variazione'] = [
                            self._convert_variazione_to_unified(v) for v in variazioni
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca variazioni: {e}")
        
        # Ricerca contratti
        if options.get('search_contratti', True):
            try:
                if hasattr(self.gin_search, 'search_contratti_fuzzy'):
                    contratti = self.gin_search.search_contratti_fuzzy(
                        query_text, threshold, max_results
                    )
                    if contratti:
                        results['results_by_type']['contratto'] = [
                            self._convert_contratto_to_unified(c) for c in contratti
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca contratti: {e}")
        
        # Ricerca partite
        if options.get('search_partite', True):
            try:
                if hasattr(self.gin_search, 'search_partite_fuzzy'):
                    partite = self.gin_search.search_partite_fuzzy(
                        query_text, threshold, max_results
                    )
                    if partite:
                        results['results_by_type']['partita'] = [
                            self._convert_partita_to_unified(p) for p in partite
                        ]
            except Exception as e:
                self.logger.error(f"Errore ricerca partite: {e}")
        
        return results

    # ========================================================================
    # CORREZIONE 4: Funzioni di conversione al formato unificato
    # ========================================================================

    def _convert_possessore_to_unified(self, possessore):
        """Converte risultato possessore al formato unificato."""
        return {
            'entity_id': possessore.get('id'),
            'entity_type': 'possessore',
            'display_text': possessore.get('nome_completo', ''),
            'detail_text': possessore.get('comune_nome', ''),
            'similarity_score': possessore.get('similarity_score', 0),
            'search_field': 'nome_completo',
            'additional_info': {
                'paternita': possessore.get('paternita', ''),
                'comune': possessore.get('comune_nome', ''),
                'num_partite': possessore.get('num_partite', 0)
            }
        }

    def _convert_localita_to_unified(self, localita):
        """Converte risultato località al formato unificato."""
        return {
            'entity_id': localita.get('id'),
            'entity_type': 'localita',
            'display_text': f"{localita.get('nome', '')} {localita.get('civico', '')}".strip(),
            'detail_text': localita.get('comune_nome', ''),
            'similarity_score': localita.get('similarity_score', 0),
            'search_field': 'nome',
            'additional_info': {
                'tipo': localita.get('tipo', ''),
                'comune': localita.get('comune_nome', ''),
                'num_immobili': localita.get('num_immobili', 0)
            }
        }

    def _convert_immobile_to_unified(self, immobile):
        """Converte risultato immobile al formato unificato."""
        return {
            'entity_id': immobile.get('id'),
            'entity_type': 'immobile', 
            'display_text': immobile.get('natura', ''),
            'detail_text': f"Partita {immobile.get('numero_partita', '')} - {immobile.get('comune_nome', '')}",
            'similarity_score': immobile.get('similarity_score', 0),
            'search_field': immobile.get('search_field', 'natura'),
            'additional_info': {
                'natura': immobile.get('natura', ''),
                'classificazione': immobile.get('classificazione', ''),
                'consistenza': immobile.get('consistenza', ''),
                'partita': immobile.get('numero_partita', ''),
                'suffisso_partita': immobile.get('suffisso_partita', ''),
                'localita': immobile.get('localita_nome', ''),
                'comune': immobile.get('comune_nome', '')
            }
        }

    def _convert_variazione_to_unified(self, variazione):
        """Converte risultato variazione al formato unificato."""
        return {
            'entity_id': variazione.get('id'),
            'entity_type': 'variazione',
            'display_text': variazione.get('tipo', ''),
            'detail_text': f"Partita {variazione.get('partita_origine_id', '')} → {variazione.get('partita_destinazione_id', '')} - {variazione.get('data_variazione', '')}",
            'similarity_score': variazione.get('similarity_score', 0),
            'search_field': variazione.get('search_field', 'tipo'),
            'additional_info': {
                'tipo': variazione.get('tipo', ''),
                'data_variazione': variazione.get('data_variazione'),
                'partita_origine': variazione.get('partita_origine_id'),
                'partita_destinazione': variazione.get('partita_destinazione_id'),
                'nominativo_riferimento': variazione.get('nominativo_riferimento', ''),
                'numero_riferimento': variazione.get('numero_riferimento', '')
            }
        }

    def _convert_contratto_to_unified(self, contratto):
        """Converte risultato contratto al formato unificato."""
        return {
            'entity_id': contratto.get('id'),
            'entity_type': 'contratto',
            'display_text': contratto.get('tipo', ''),
            'detail_text': f"{contratto.get('notaio', '')} - {contratto.get('data_stipula', '')}",
            'similarity_score': contratto.get('similarity_score', 0),
            'search_field': contratto.get('search_field', 'tipo'),
            'additional_info': {
                'tipo': contratto.get('tipo', ''),
                'data_contratto': contratto.get('data_stipula'),
                'notaio': contratto.get('notaio', ''),
                'repertorio': contratto.get('repertorio', ''),
                'note': contratto.get('note', ''),
                'partita_id': contratto.get('partita_id')
            }
        }

    def _convert_partita_to_unified(self, partita):
        """Converte risultato partita al formato unificato."""
        return {
            'entity_id': partita.get('id'),
            'entity_type': 'partita',
            'display_text': f"Partita {partita.get('numero_partita', '')} {partita.get('suffisso_partita', '')}".strip(),
            'detail_text': f"{partita.get('comune_nome', '')} - {partita.get('stato', '')}",
            'similarity_score': partita.get('similarity_score', 0),
            'search_field': partita.get('search_field', 'numero_partita'),
            'additional_info': {
                'numero_partita': partita.get('numero_partita'),
                'suffisso_partita': partita.get('suffisso_partita', ''),
                'tipo_partita': partita.get('tipo_partita', ''),
                'comune': partita.get('comune_nome', ''),
                'stato': partita.get('stato', ''),
                'num_immobili': partita.get('num_immobili', 0)
            }
        }

    # ========================================================================
    # CORREZIONE 5: Verifica completa degli indici GIN
    # ========================================================================

    def _comprehensive_gin_check(self):
        """Verifica completa degli indici GIN e delle funzioni."""
        if not self.gin_search:
            return {
                'status': 'ERROR',
                'message': 'Estensione GIN non disponibile',
                'indices': [],
                'functions': {}
            }
        
        try:
            # Verifica indici
            indices_status = {}
            if hasattr(self.gin_search, 'verify_gin_indices'):
                indices_result = self.gin_search.verify_gin_indices()
                if indices_result.get('status') == 'OK':
                    indices_status = indices_result
                
            # Verifica funzioni
            functions_status = self._verify_available_functions()
            
            # Verifica estensione pg_trgm
            trgm_available = False
            if hasattr(self.gin_search, 'check_pg_trgm_extension'):
                trgm_available = self.gin_search.check_pg_trgm_extension()
            
            return {
                'status': 'OK',
                'indices': indices_status,
                'functions': functions_status,
                'pg_trgm_available': trgm_available,
                'recommended_indices': [
                    'idx_gin_possessore_nome_completo_trgm',
                    'idx_gin_possessore_cognome_nome_trgm',
                    'idx_gin_possessore_paternita_trgm',
                    'idx_gin_localita_nome_trgm',
                    'idx_gin_immobili_natura',
                    'idx_gin_variazioni_tipo',
                    'idx_gin_contratti_notaio',
                    'idx_gin_partite_numero'
                ]
            }
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': str(e),
                'indices': [],
                'functions': {}
            }

    # ========================================================================
    # CORREZIONE 6: Test di coerenza SQL-Python
    # ========================================================================

    def test_sql_python_coherence(self):
        """Test per verificare la coerenza tra implementazione Python e SQL."""
        results = {
            'coherence_score': 0,
            'tests_passed': 0,
            'tests_total': 0,
            'issues': []
        }
        
        if not self.gin_search:
            results['issues'].append("Estensione GIN non disponibile")
            return results
        
        # Test 1: Verifica presenza funzioni base
        base_functions = ['search_possessori_fuzzy', 'search_localita_fuzzy']
        for func in base_functions:
            results['tests_total'] += 1
            if hasattr(self.gin_search, func):
                results['tests_passed'] += 1
            else:
                results['issues'].append(f"Funzione mancante: {func}")
        
        # Test 2: Verifica funzioni ampliato
        extended_functions = [
            'search_immobili_fuzzy', 'search_variazioni_fuzzy',
            'search_contratti_fuzzy', 'search_partite_fuzzy'
        ]
        for func in extended_functions:
            results['tests_total'] += 1
            if hasattr(self.gin_search, func):
                results['tests_passed'] += 1
            else:
                results['issues'].append(f"Funzione ampliata mancante: {func}")
        
        # Test 3: Verifica funzione unificata
        results['tests_total'] += 1
        if hasattr(self.gin_search, 'search_all_entities_fuzzy'):
            results['tests_passed'] += 1
            
            # Test parametri funzione unificata
            try:
                # Test con parametri corretti
                test_result = self.gin_search.search_all_entities_fuzzy(
                    "test", 0.3, True, True, True, True, True, True, 10
                )
                results['tests_total'] += 1
                results['tests_passed'] += 1
            except Exception as e:
                results['issues'].append(f"Errore parametri funzione unificata: {e}")
        else:
            results['issues'].append("Funzione search_all_entities_fuzzy mancante")
        
        # Test 4: Verifica indici GIN
        results['tests_total'] += 1
        if hasattr(self.gin_search, 'verify_gin_indices'):
            try:
                indices_check = self.gin_search.verify_gin_indices()
                if indices_check.get('status') == 'OK':
                    results['tests_passed'] += 1
                else:
                    results['issues'].append("Verifica indici GIN fallita")
            except Exception as e:
                results['issues'].append(f"Errore verifica indici: {e}")
        else:
            results['issues'].append("Funzione verify_gin_indices mancante")
        
        # Calcola score di coerenza
        if results['tests_total'] > 0:
            results['coherence_score'] = (results['tests_passed'] / results['tests_total']) * 100
        
        return results
=======
        """Gestisce gli errori di ricerca."""
        self.search_btn.setEnabled(True)
        self.stats_label.setText("❌ Errore ricerca")
        self.logger.error(f"Errore ricerca fuzzy: {error_message}")
        QMessageBox.critical(self, "Errore Ricerca", f"Si è verificato un errore:\n{error_message}")

    def _clear_search(self):
        """Pulisce il campo di ricerca e i risultati."""
        self.search_edit.clear()
        self._clear_results()
        self.stats_label.setText("Pronto")
>>>>>>> new_entry

    # In fuzzy_search_unified.py, dentro la classe UnifiedFuzzySearchWidget
    # In fuzzy_search_unified.py, SOSTITUISCI il metodo _on_unified_double_click con questo

    def _on_unified_double_click(self, index):
        """
        Gestisce il doppio click nella tabella unificata, chiamando il gestore appropriato.
        """
        if not index.isValid(): return
            
        item_con_dati = self.unified_table.item(index.row(), 0)
        if not item_con_dati: return

        full_item_data = item_con_dati.data(Qt.UserRole)
        if not isinstance(full_item_data, dict): return

        entity_type = full_item_data.get('type')

        # Simula un evento di doppio click sul tab appropriato
        if entity_type == 'partita':
            self._on_partite_double_click(index)
        elif entity_type == 'possessore':
            self._on_possessori_double_click(index)
        elif entity_type == 'localita':
            self._on_localita_double_click(index)
        elif entity_type == 'immobile':
            self._on_immobili_double_click(index)
        elif entity_type == 'variazione':
            self._on_variazioni_double_click(index)
        elif entity_type == 'contratto':
            self._on_contratti_double_click(index)
        else:
            QMessageBox.warning(self, "Tipo Sconosciuto", f"Nessuna azione di dettaglio definita per il tipo '{entity_type}'.")
    def _handle_export_csv(self):
        """Esporta i risultati correnti della ricerca unificata in un file CSV."""
        if not self.current_results or not self.current_results.get('total_results', 0) > 0:
            QMessageBox.warning(self, "Nessun Risultato", "Non ci sono risultati da esportare.")
            return

        query_text = self.current_results.get('query_text', 'ricerca')
        default_filename = f"ricerca_fuzzy_{query_text}_{date.today().isoformat()}.csv"
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Risultati in CSV", default_filename, "File CSV (*.csv)")

        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # Usiamo le intestazioni della tabella "Tutti"
                headers = ['Tipo Entità', 'Nome/Descrizione', 'Dettagli', 'Similarità', 'Campo Trovato']
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(headers)
                
                for entity_type, entities in self.current_results.get('results_by_type', {}).items():
                    for entity in entities:
                        writer.writerow([
                            entity_type,
                            entity.get('display_text', ''),
                            entity.get('detail_text', ''),
                            f"{entity.get('similarity_score', 0):.3f}",
                            entity.get('search_field', '')
                        ])
            prompt_to_open_file(self, filename)
        except Exception as e:
            self.logger.error(f"Errore esportazione CSV fuzzy: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file CSV:\n{e}")

    def _handle_export_pdf(self):
        """Esporta i risultati correnti della ricerca unificata in un file PDF."""
        if not self.current_results or not self.current_results.get('total_results', 0) > 0:
            QMessageBox.warning(self, "Nessun Risultato", "Non ci sono risultati da esportare.")
            return
            
        query_text = self.current_results.get('query_text', 'ricerca')
        default_filename = f"ricerca_fuzzy_{query_text}_{date.today().isoformat()}.pdf"
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Risultati in PDF", default_filename, "File PDF (*.pdf)")

        if not filename:
            return

        try:
            pdf = BulkReportPDF(report_title=f"Risultati Ricerca Fuzzy per '{query_text}'")
            pdf.add_page()
            
            for entity_type, entities in self.current_results.get('results_by_type', {}).items():
                if not entities: continue
                
                pdf.set_font('Helvetica', 'B', 12)
                pdf.cell(0, 10, f"Risultati per: {entity_type.title()} ({len(entities)})", ln=1)
                
                headers = ['Nome/Descrizione', 'Dettagli', 'Similarità']
                # Adattiamo i dati per la tabella
                data_rows = [
                    (entity.get('display_text', ''), entity.get('detail_text', ''), f"{entity.get('similarity_score', 0):.3f}")
                    for entity in entities
                ]
                # La classe BulkReportPDF gestirà la creazione della tabella
                pdf.print_table(headers, data_rows)
                pdf.ln(5)

            pdf.output(filename)
            prompt_to_open_file(self, filename)
        except Exception as e:
            self.logger.error(f"Errore esportazione PDF fuzzy: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile generare il file PDF:\n{e}")
    # In fuzzy_search_unified.py, aggiungi questo metodo alla classe UnifiedFuzzySearchWidget

    def _get_entity_id_from_table(self, table: QTableWidget, index) -> Optional[int]:
        """Helper generico per estrarre l'ID dell'entità da una riga della tabella."""
        if not index.isValid():
            return None

        # I dati completi sono sempre salvati nella UserRole della prima colonna (indice 0)
        item_con_dati = table.item(index.row(), 0)
        if not item_con_dati:
            return None
            
        entity_data_wrapper = item_con_dati.data(Qt.UserRole)
        if not isinstance(entity_data_wrapper, dict):
            return None

        # Gestisce sia il tab "Tutti" (dove i dati sono annidati in 'data') 
        # sia i tab specifici (dove i dati sono al primo livello).
        if 'data' in entity_data_wrapper and isinstance(entity_data_wrapper['data'], dict):
            return entity_data_wrapper['data'].get('entity_id')
        elif 'entity_id' in entity_data_wrapper:
            return entity_data_wrapper.get('entity_id')

        return None

    def _on_possessori_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.possessori_table, index)
        if entity_id:
            dialog = ModificaPossessoreDialog(self.db_manager, entity_id, self)
            if dialog.exec_() == QDialog.Accepted:
                self._perform_search() # Aggiorna i risultati se ci sono state modifiche

    def _on_localita_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.localita_table, index)
        if entity_id:
            localita_details = self.db_manager.get_localita_details(entity_id)
            if localita_details and localita_details.get('comune_id'):
                dialog = ModificaLocalitaDialog(self.db_manager, entity_id, localita_details.get('comune_id'), self)
                if dialog.exec_() == QDialog.Accepted:
                    self._perform_search()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per la località ID {entity_id}.")

    def _on_immobili_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.immobili_table, index)
        if entity_id:
            immobile_details = self.db_manager.get_immobile_details(entity_id)
            if immobile_details and immobile_details.get('partita_id'):
                partita_details = self.db_manager.get_partita_details(immobile_details.get('partita_id'))
                if partita_details and partita_details.get('comune_id'):
                    dialog = ModificaImmobileDialog(self.db_manager, entity_id, partita_details.get('comune_id'), self)
                    if dialog.exec_() == QDialog.Accepted:
                        self._perform_search()
                else:
                    QMessageBox.warning(self, "Errore Dati", f"Impossibile determinare il comune per l'immobile ID {entity_id}.")
            else:
                 QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per l'immobile ID {entity_id}.")

    def _on_partite_double_click(self, index):
        entity_id = self._get_entity_id_from_table(self.partite_table, index)
        if entity_id:
            full_details = self.db_manager.get_partita_details(entity_id)
            if full_details:
                dialog = PartitaDetailsDialog(full_details, self)
                dialog.exec_()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per la partita ID {entity_id}.")

    def _show_generic_details_popup(self, table: QTableWidget, index: 'QModelIndex', entity_type_name: str):
        """Mostra un popup leggibile per entità senza un dialogo di dettaglio dedicato."""
        item_con_dati = table.item(index.row(), 0)
        if not item_con_dati: return
        entity_data = item_con_dati.data(Qt.UserRole)
        entity_id = entity_data.get('entity_id', 'N/A')

        testo_formattato = f"<h3>Dettagli - {entity_type_name.title()} ID: {entity_id}</h3>"
        testo_formattato += "<table border='0' cellspacing='5'>"
        for key, value in entity_data.items():
            chiave_formattata = key.replace('_', ' ').title()
            testo_formattato += f"<tr><td><b>{chiave_formattata}:</b></td><td>{value}</td></tr>"
        testo_formattato += "</table>"
        QMessageBox.information(self, f"Dettagli - {entity_type_name.title()}", testo_formattato)

    def _on_variazioni_double_click(self, index):
        self._show_generic_details_popup(self.variazioni_table, index, 'variazione')

    def _on_contratti_double_click(self, index):
        self._show_generic_details_popup(self.contratti_table, index, 'contratto')
# ========================================================================
# FUNZIONI DI INTEGRAZIONE
# ========================================================================

# In fuzzy_search_unified.py, SOSTITUISCI l'intera funzione add_fuzzy_search_tab_to_main_window

def add_fuzzy_search_tab_to_main_window(main_window): # RIMOSSO il parametro 'mode'
    """
<<<<<<< HEAD
    Aggiunge il tab di ricerca fuzzy alla finestra principale.
    
    Args:
        main_window: Istanza di CatastoMainWindow
        
    Returns:
        bool: True se aggiunto con successo, False altrimenti
=======
    Aggiunge il tab di ricerca fuzzy unificato alla finestra principale.
>>>>>>> new_entry
    """
    try:
        if not hasattr(main_window, 'db_manager') or not main_window.db_manager:
            if hasattr(main_window, 'logger'):
                main_window.logger.warning("Database manager non disponibile per ricerca fuzzy")
            else:
                print("❌ Database manager non disponibile per ricerca fuzzy")
            return False
            
<<<<<<< HEAD
        # Crea il widget di ricerca fuzzy
        fuzzy_widget = FuzzySearchWidget(main_window.db_manager, main_window)
=======
        # --- MODIFICA QUI: Creiamo il widget senza passare 'mode' ---
        # Il parent corretto è il QTabWidget della finestra principale, cioè 'main_window.tabs'
        fuzzy_widget = UnifiedFuzzySearchWidget(main_window.db_manager, parent=main_window.tabs)
>>>>>>> new_entry
        
        # Aggiunge il tab alla finestra principale
        # Il nome del tab ora è fisso, non dipende più dalla modalità
        tab_index = main_window.tabs.addTab(fuzzy_widget, "🔍 Ricerca Globale")
        
        if hasattr(main_window, 'logger'):
            main_window.logger.info(f"Tab Ricerca Globale aggiunto all'indice {tab_index}")
        else:
            print(f"✅ Tab Ricerca Globale aggiunto all'indice {tab_index}")
        
        return True
        
    except Exception as e:
        if hasattr(main_window, 'logger'):
            main_window.logger.error(f"Errore aggiunta tab ricerca fuzzy: {e}", exc_info=True)
        else:
            print(f"❌ Errore aggiunta tab ricerca fuzzy: {e}")
        
        import traceback
        traceback.print_exc()
<<<<<<< HEAD
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
=======
        return False
>>>>>>> new_entry
