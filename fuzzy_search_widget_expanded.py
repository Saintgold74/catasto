# ========================================================================
# WIDGET RICERCA FUZZY AMPLIATO - TUTTE LE ENTITÀ
# File: fuzzy_search_widget_expanded.py
# ========================================================================

"""
Widget completo per ricerca fuzzy ampliata con supporto per tutte le entità
del sistema catasto: possessori, località, immobili, variazioni, contratti e partite.

Nuove funzionalità:
- Ricerca in immobili (natura, classificazione, consistenza)
- Ricerca in variazioni (tipo, nominativo, numero riferimento)
- Ricerca in contratti (tipo, notaio, repertorio, note)
- Ricerca in partite (numero, suffisso)
- Ricerca unificata con risultati raggruppati per tipo
- Filtri avanzati per tipo di entità
- Export risultati in CSV/JSON
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QLabel, QSlider, QCheckBox, 
    QTabWidget, QProgressBar, QGroupBox, QFormLayout, QSpinBox,
    QTextEdit, QFrame, QSplitter, QHeaderView, QMessageBox,
    QComboBox, QApplication, QSizePolicy, QScrollArea, QDialog,
    QFileDialog, QButtonGroup
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap
import time
import logging
import psycopg2.extras
import json
import csv
from datetime import datetime

# Importa l'estensione GIN ampliata
try:
    from catasto_gin_extension_expanded import extend_db_manager_with_gin_expanded, format_search_results_expanded
except ImportError:
    print("ATTENZIONE: catasto_gin_extension_expanded.py non trovato.")

# ========================================================================
# WORKER THREAD PER RICERCHE IN BACKGROUND
# ========================================================================

class ExpandedFuzzySearchWorker(QThread):
    """Worker thread per ricerche fuzzy ampliate in background."""
    
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, gin_search, query_text, options):
        super().__init__()
        self.gin_search = gin_search
        self.query_text = query_text
        self.options = options
        
    def run(self):
        """Esegue la ricerca ampliata in background."""
        try:
            self.progress_updated.emit(20)
            
            # Imposta soglia
            threshold = self.options.get('similarity_threshold', 0.3)
            self.gin_search.set_similarity_threshold(threshold)
            
            self.progress_updated.emit(40)
            
            # Determina il tipo di ricerca
            search_type = self.options.get('search_type', 'unified')
            
            if search_type == 'unified':
                # Ricerca unificata in tutte le entità abilitate
                results = self.gin_search.search_all_entities_fuzzy(
                    self.query_text,
                    search_possessori=self.options.get('search_possessori', True),
                    search_localita=self.options.get('search_localita', True),
                    search_immobili=self.options.get('search_immobili', True),
                    search_variazioni=self.options.get('search_variazioni', True),
                    search_contratti=self.options.get('search_contratti', True),
                    search_partite=self.options.get('search_partite', True),
                    max_results_per_type=self.options.get('max_results_per_type', 30)
                )
                
            elif search_type == 'immobili':
                results = self.gin_search.search_immobili_fuzzy(
                    self.query_text,
                    max_results=self.options.get('max_results', 50)
                )
                
            elif search_type == 'variazioni':
                results = self.gin_search.search_variazioni_fuzzy(
                    self.query_text,
                    max_results=self.options.get('max_results', 50)
                )
                
            elif search_type == 'contratti':
                results = self.gin_search.search_contratti_fuzzy(
                    self.query_text,
                    max_results=self.options.get('max_results', 50)
                )
                
            elif search_type == 'partite':
                results = self.gin_search.search_partite_fuzzy(
                    self.query_text,
                    max_results=self.options.get('max_results', 50)
                )
                
            else:
                # Fallback alla ricerca combinata originale se disponibile
                if hasattr(self.gin_search, 'search_combined_fuzzy'):
                    results = self.gin_search.search_combined_fuzzy(
                        self.query_text,
                        search_possessori=self.options.get('search_possessori', True),
                        search_localita=self.options.get('search_localita', True),
                        max_possessori=self.options.get('max_possessori', 50),
                        max_localita=self.options.get('max_localita', 20)
                    )
                else:
                    raise Exception("Tipo di ricerca non supportato")
            
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
# WIDGET PRINCIPALE RICERCA FUZZY AMPLIATA
# ========================================================================

class ExpandedFuzzySearchWidget(QWidget):
    """Widget per ricerca fuzzy ampliata in tutte le entità del catasto."""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        
        # Estendi il db_manager con capacità GIN ampliate
        if hasattr(extend_db_manager_with_gin_expanded, '__call__'):
            self.db_manager = extend_db_manager_with_gin_expanded(db_manager)
        
        self.search_worker = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        self.setup_ui()
        self.verify_indices()
        
    def setup_ui(self):
        """Configura l'interfaccia utente."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # === AREA RICERCA COMPATTA ===
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
        self.search_edit.textChanged.connect(self.on_search_text_changed)
        search_row.addWidget(self.search_edit, 1)
        
        self.search_btn = QPushButton("Cerca")
        self.search_btn.clicked.connect(self.perform_search)
        search_row.addWidget(self.search_btn)
        
        self.clear_btn = QPushButton("🗑️")
        self.clear_btn.setMaximumWidth(30)
        self.clear_btn.clicked.connect(self.clear_search)
        search_row.addWidget(self.clear_btn)
        
        search_layout.addLayout(search_row)
        
        # Controlli rapidi
        controls_row = QHBoxLayout()
        
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
        controls_row.addWidget(QLabel("Soglia:"))
        self.similarity_slider = QSlider(Qt.Horizontal)
        self.similarity_slider.setRange(10, 90)
        self.similarity_slider.setValue(30)
        self.similarity_slider.setMaximumWidth(100)
        self.similarity_slider.valueChanged.connect(self.update_similarity_label)
        controls_row.addWidget(self.similarity_slider)
        
        self.similarity_label = QLabel("0.30")
        self.similarity_label.setMinimumWidth(30)
        controls_row.addWidget(self.similarity_label)
        
        controls_row.addStretch()
        
        # Pulsanti azione
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        controls_row.addWidget(self.export_btn)
        
        self.indices_btn = QPushButton("🔧 Indici")
        self.indices_btn.clicked.connect(self.verify_indices)
        controls_row.addWidget(self.indices_btn)
        
        search_layout.addLayout(controls_row)
        main_layout.addWidget(search_frame)
        
        # === AREA RISULTATI CON TABS ===
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
        
        # Tabs per diversi tipi di risultati
        self.results_tabs = QTabWidget()
        self.results_tabs.setTabPosition(QTabWidget.North)
        
        # Tab Unificata
        self.unified_table = self.create_unified_table()
        self.results_tabs.addTab(self.unified_table, "🔍 Tutti")
        
        # Tab Possessori
        self.possessori_table = self.create_possessori_table()
        self.results_tabs.addTab(self.possessori_table, "👥 Possessori")
        
        # Tab Località
        self.localita_table = self.create_localita_table()
        self.results_tabs.addTab(self.localita_table, "🏠 Località")
        
        # Tab Immobili
        self.immobili_table = self.create_immobili_table()
        self.results_tabs.addTab(self.immobili_table, "🏢 Immobili")
        
        # Tab Variazioni
        self.variazioni_table = self.create_variazioni_table()
        self.results_tabs.addTab(self.variazioni_table, "🔄 Variazioni")
        
        # Tab Contratti
        self.contratti_table = self.create_contratti_table()
        self.results_tabs.addTab(self.contratti_table, "📄 Contratti")
        
        # Tab Partite
        self.partite_table = self.create_partite_table()
        self.results_tabs.addTab(self.partite_table, "📋 Partite")
        
        results_layout.addWidget(self.results_tabs)
        main_layout.addWidget(results_frame, 1)
        
        # === AREA DEBUG MINIMALE ===
        debug_frame = QFrame()
        debug_frame.setMaximumHeight(50)
        debug_layout = QHBoxLayout(debug_frame)
        debug_layout.setContentsMargins(5, 2, 5, 2)
        
        self.status_label = QLabel("Sistema ricerca fuzzy ampliato pronto")
        self.status_label.setStyleSheet("font-size: 10px; color: #666;")
        debug_layout.addWidget(self.status_label)
        
        debug_layout.addStretch()
        
        self.indices_status_label = QLabel("Indici: Non verificato")
        self.indices_status_label.setStyleSheet("font-size: 10px; color: #666;")
        debug_layout.addWidget(self.indices_status_label)
        
        main_layout.addWidget(debug_frame)
        
        # Focus iniziale
        self.search_edit.setFocus()
        
    def create_unified_table(self):
        """Crea la tabella per risultati unificati."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Tipo", "Nome/Descrizione", "Dettagli", "Similarità", "Campo", "Azioni"
        ])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Tipo
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # Nome
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Dettagli
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Similarità
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Campo
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Azioni
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.doubleClicked.connect(self._on_unified_double_click)
        
        return table
        
    def create_immobili_table(self):
        """Crea la tabella per immobili."""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "ID", "Natura", "Partita", "Località", "Comune", "Similarità", "Campo"
        ])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.doubleClicked.connect(lambda: self._on_entity_double_click('immobile'))
        
        return table
        
    def create_variazioni_table(self):
        """Crea la tabella per variazioni."""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "ID", "Tipo", "Da Partita", "A Partita", "Data", "Similarità", "Campo"
        ])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.doubleClicked.connect(lambda: self._on_entity_double_click('variazione'))
        
        return table
        
    def create_contratti_table(self):
        """Crea la tabella per contratti."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "ID", "Tipo", "Data", "Notaio", "Similarità", "Campo"
        ])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.doubleClicked.connect(lambda: self._on_entity_double_click('contratto'))
        
        return table
        
    def create_partite_table(self):
        """Crea la tabella per partite."""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "ID", "Numero", "Suffisso", "Comune", "Stato", "Similarità", "Campo"
        ])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.doubleClicked.connect(lambda: self._on_entity_double_click('partita'))
        
        return table
        
    def create_possessori_table(self):
        """Crea la tabella per possessori (eredita dalla versione originale)."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "ID", "Nome Completo", "Paternità", "Comune", "Similarità", "Azioni"
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
        table.doubleClicked.connect(lambda: self._on_entity_double_click('possessore'))
        
        return table
        
    def create_localita_table(self):
        """Crea la tabella per località (eredita dalla versione originale)."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "ID", "Nome", "Tipo", "Comune", "Similarità", "Azioni"
        ])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.doubleClicked.connect(lambda: self._on_entity_double_click('localita'))
        
        return table
        
    def on_search_text_changed(self):
        """Gestisce i cambiamenti nel testo di ricerca."""
        if len(self.search_edit.text()) >= 3:
            self.search_timer.start(800)  # Avvia ricerca dopo 800ms
        else:
            self.search_timer.stop()
            
    def update_similarity_label(self):
        """Aggiorna l'etichetta della soglia di similarità."""
        value = self.similarity_slider.value() / 100.0
        self.similarity_label.setText(f"{value:.2f}")
        
    def get_search_options(self):
        """Ottiene le opzioni di ricerca correnti."""
        search_type_map = {
            0: 'unified',
            1: 'immobili',
            2: 'variazioni',
            3: 'contratti',
            4: 'partite',
            5: 'combined'  # Possessori + Località
        }
        
        return {
            'search_type': search_type_map.get(self.search_type_combo.currentIndex(), 'unified'),
            'similarity_threshold': self.similarity_slider.value() / 100.0,
            'search_possessori': True,
            'search_localita': True,
            'search_immobili': True,
            'search_variazioni': True,
            'search_contratti': True,
            'search_partite': True,
            'max_results_per_type': 30,
            'max_results': 50
        }
        
    def perform_search(self):
        """Esegue la ricerca fuzzy."""
        query_text = self.search_edit.text().strip()
        
        if len(query_text) < 3:
            self.status_label.setText("⚠️ Inserire almeno 3 caratteri per la ricerca")
            return
            
        if not hasattr(self.db_manager, 'gin_search_expanded'):
            self.status_label.setText("❌ Sistema ricerca fuzzy non disponibile")
            return
            
        # Ferma ricerca precedente se in corso
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            self.search_worker.wait()
            
        # Avvia nuova ricerca
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"🔍 Ricerca: '{query_text}'...")
        self.search_btn.setEnabled(False)
        
        # Pulisci risultati precedenti
        self.clear_results()
        
        options = self.get_search_options()
        
        self.search_worker = ExpandedFuzzySearchWorker(
            self.db_manager.gin_search_expanded,
            query_text,
            options
        )
        
        self.search_worker.results_ready.connect(self.display_results)
        self.search_worker.error_occurred.connect(self.handle_search_error)
        self.search_worker.progress_updated.connect(self.progress_bar.setValue)
        self.search_worker.finished.connect(self.search_finished)
        
        self.search_worker.start()
        
    def clear_results(self):
        """Pulisce tutti i risultati."""
        for table in [self.unified_table, self.possessori_table, self.localita_table,
                     self.immobili_table, self.variazioni_table, self.contratti_table,
                     self.partite_table]:
            table.setRowCount(0)
            
        self.results_count_label.setText("0 risultati")
        self.export_btn.setEnabled(False)
        
    def display_results(self, results):
        """Visualizza i risultati della ricerca."""
        if results.get('status') != 'OK':
            self.status_label.setText(f"❌ Errore: {results.get('error', 'Errore sconosciuto')}")
            return
            
        total_results = results.get('total_results', 0)
        self.results_count_label.setText(f"{total_results} risultati")
        
        if total_results == 0:
            self.status_label.setText(f"🔍 Nessun risultato per '{results.get('query', '')}'")
            return
            
        # Visualizza risultati in base al tipo
        if 'results_by_type' in results:
            # Risultati unificati
            self.display_unified_results(results['results_by_type'])
            self.populate_individual_tabs(results['results_by_type'])
        else:
            # Risultati singoli
            self.display_single_type_results(results)
            
        self.export_btn.setEnabled(True)
        self.status_label.setText(f"✅ Trovati {total_results} risultati")
        
    def display_unified_results(self, results_by_type):
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
                table.setItem(row, 1, QTableWidgetItem(entity['display_text']))
                table.setItem(row, 2, QTableWidgetItem(entity['detail_text']))
                
                # Barra di similarità
                similarity = entity['similarity_score']
                similarity_item = QTableWidgetItem(f"{similarity:.3f}")
                similarity_item.setData(Qt.UserRole, similarity)
                table.setItem(row, 3, similarity_item)
                
                table.setItem(row, 4, QTableWidgetItem(entity['search_field']))
                
                # Pulsante dettagli
                details_btn = QPushButton("📋 Dettagli")
                details_btn.clicked.connect(
                    lambda checked, et=entity_type, eid=entity['entity_id']: 
                    self.show_entity_details(et, eid)
                )
                table.setCellWidget(row, 5, details_btn)
                
                # Memorizza i dati per l'export
                table.item(row, 0).setData(Qt.UserRole, {
                    'entity_type': entity_type,
                    'entity_id': entity['entity_id'],
                    'full_data': entity
                })
                
                row += 1
                
    def populate_individual_tabs(self, results_by_type):
        """Popola le tab individuali."""
        # Possessori
        if 'possessore' in results_by_type:
            self.populate_possessori_table(results_by_type['possessore'])
            
        # Località
        if 'localita' in results_by_type:
            self.populate_localita_table(results_by_type['localita'])
            
        # Immobili
        if 'immobile' in results_by_type:
            self.populate_immobili_table(results_by_type['immobile'])
            
        # Variazioni
        if 'variazione' in results_by_type:
            self.populate_variazioni_table(results_by_type['variazione'])
            
        # Contratti
        if 'contratto' in results_by_type:
            self.populate_contratti_table(results_by_type['contratto'])
            
        # Partite
        if 'partita' in results_by_type:
            self.populate_partite_table(results_by_type['partita'])
            
    def populate_immobili_table(self, immobili):
        """Popola la tabella degli immobili."""
        table = self.immobili_table
        table.setRowCount(len(immobili))
        
        for row, immobile in enumerate(immobili):
            info = immobile['additional_info']
            
            table.setItem(row, 0, QTableWidgetItem(str(immobile['entity_id'])))
            table.setItem(row, 1, QTableWidgetItem(immobile['display_text']))
            table.setItem(row, 2, QTableWidgetItem(
                f"{info.get('numero_partita', 'N/A')}"
                f"{' ' + info.get('suffisso_partita', '') if info.get('suffisso_partita') else ''}"
            ))
            table.setItem(row, 3, QTableWidgetItem(info.get('localita', 'N/A')))
            table.setItem(row, 4, QTableWidgetItem(info.get('comune', 'N/A')))
            table.setItem(row, 5, QTableWidgetItem(f"{immobile['similarity_score']:.3f}"))
            table.setItem(row, 6, QTableWidgetItem(immobile['search_field']))
            
            # Memorizza l'ID per i doppi click
            table.item(row, 0).setData(Qt.UserRole, immobile['entity_id'])
            
    def populate_variazioni_table(self, variazioni):
        """Popola la tabella delle variazioni."""
        table = self.variazioni_table
        table.setRowCount(len(variazioni))
        
        for row, variazione in enumerate(variazioni):
            info = variazione['additional_info']
            
            table.setItem(row, 0, QTableWidgetItem(str(variazione['entity_id'])))
            table.setItem(row, 1, QTableWidgetItem(variazione['display_text']))
            
            # Estrai da detail_text o additional_info
            detail_parts = variazione['detail_text'].split(' - ')
            if len(detail_parts) >= 2:
                partite_info = detail_parts[0].replace('Partita ', '')
                table.setItem(row, 2, QTableWidgetItem(partite_info.split(' → ')[0]))
                if ' → ' in partite_info:
                    table.setItem(row, 3, QTableWidgetItem(partite_info.split(' → ')[1]))
                else:
                    table.setItem(row, 3, QTableWidgetItem('N/A'))
            else:
                table.setItem(row, 2, QTableWidgetItem('N/A'))
                table.setItem(row, 3, QTableWidgetItem('N/A'))
                
            # Data variazione
            data_var = info.get('data_variazione', 'N/A')
            if hasattr(data_var, 'strftime'):
                data_var = data_var.strftime('%d/%m/%Y')
            table.setItem(row, 4, QTableWidgetItem(str(data_var)))
            
            table.setItem(row, 5, QTableWidgetItem(f"{variazione['similarity_score']:.3f}"))
            table.setItem(row, 6, QTableWidgetItem(variazione['search_field']))
            
            table.item(row, 0).setData(Qt.UserRole, variazione['entity_id'])
            
    def populate_contratti_table(self, contratti):
        """Popola la tabella dei contratti."""
        table = self.contratti_table
        table.setRowCount(len(contratti))
        
        for row, contratto in enumerate(contratti):
            info = contratto['additional_info']
            
            table.setItem(row, 0, QTableWidgetItem(str(contratto['entity_id'])))
            table.setItem(row, 1, QTableWidgetItem(contratto['display_text']))
            
            # Data contratto
            data_contr = info.get('data_contratto', 'N/A')
            if hasattr(data_contr, 'strftime'):
                data_contr = data_contr.strftime('%d/%m/%Y')
            table.setItem(row, 2, QTableWidgetItem(str(data_contr)))
            
            table.setItem(row, 3, QTableWidgetItem(info.get('notaio', 'N/A')))
            table.setItem(row, 4, QTableWidgetItem(f"{contratto['similarity_score']:.3f}"))
            table.setItem(row, 5, QTableWidgetItem(contratto['search_field']))
            
            table.item(row, 0).setData(Qt.UserRole, contratto['entity_id'])
            
    def populate_partite_table(self, partite):
        """Popola la tabella delle partite."""
        table = self.partite_table
        table.setRowCount(len(partite))
        
        for row, partita in enumerate(partite):
            info = partita['additional_info']
            
            table.setItem(row, 0, QTableWidgetItem(str(partita['entity_id'])))
            table.setItem(row, 1, QTableWidgetItem(str(info.get('numero_partita', 'N/A'))))
            table.setItem(row, 2, QTableWidgetItem(info.get('suffisso_partita', '') or ''))
            table.setItem(row, 3, QTableWidgetItem(info.get('comune', 'N/A')))
            table.setItem(row, 4, QTableWidgetItem(info.get('stato', 'N/A')))
            table.setItem(row, 5, QTableWidgetItem(f"{partita['similarity_score']:.3f}"))
            table.setItem(row, 6, QTableWidgetItem(partita['search_field']))
            
            table.item(row, 0).setData(Qt.UserRole, partita['entity_id'])
            
    def populate_possessori_table(self, possessori):
        """Popola la tabella dei possessori."""
        table = self.possessori_table
        table.setRowCount(len(possessori))
        
        for row, possessore in enumerate(possessori):
            info = possessore['additional_info']
            
            table.setItem(row, 0, QTableWidgetItem(str(possessore['entity_id'])))
            table.setItem(row, 1, QTableWidgetItem(possessore['display_text']))
            table.setItem(row, 2, QTableWidgetItem(info.get('paternita', 'N/A')))
            table.setItem(row, 3, QTableWidgetItem(info.get('comune', 'N/A')))
            table.setItem(row, 4, QTableWidgetItem(f"{possessore['similarity_score']:.3f}"))
            
            # Pulsante azioni
            action_btn = QPushButton("📋")
            action_btn.clicked.connect(
                lambda checked, eid=possessore['entity_id']: 
                self.show_entity_details('possessore', eid)
            )
            table.setCellWidget(row, 5, action_btn)
            
            table.item(row, 0).setData(Qt.UserRole, possessore['entity_id'])
            
    def populate_localita_table(self, localita):
        """Popola la tabella delle località."""
        table = self.localita_table
        table.setRowCount(len(localita))
        
        for row, loc in enumerate(localita):
            info = loc['additional_info']
            
            table.setItem(row, 0, QTableWidgetItem(str(loc['entity_id'])))
            table.setItem(row, 1, QTableWidgetItem(loc['display_text']))
            table.setItem(row, 2, QTableWidgetItem(info.get('tipo', 'N/A')))
            table.setItem(row, 3, QTableWidgetItem(info.get('comune', 'N/A')))
            table.setItem(row, 4, QTableWidgetItem(f"{loc['similarity_score']:.3f}"))
            
            # Pulsante azioni
            action_btn = QPushButton("📋")
            action_btn.clicked.connect(
                lambda checked, eid=loc['entity_id']: 
                self.show_entity_details('localita', eid)
            )
            table.setCellWidget(row, 5, action_btn)
            
            table.item(row, 0).setData(Qt.UserRole, loc['entity_id'])
            
    def display_single_type_results(self, results):
        """Visualizza risultati per un singolo tipo di entità."""
        # Implementa per risultati non unificati se necessario
        pass
        
    def handle_search_error(self, error_msg):
        """Gestisce gli errori di ricerca."""
        self.status_label.setText(f"❌ Errore ricerca: {error_msg}")
        QMessageBox.warning(self, "Errore Ricerca", f"Errore durante la ricerca:\n{error_msg}")
        
    def search_finished(self):
        """Chiamata quando la ricerca è terminata."""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
        
    def clear_search(self):
        """Pulisce la ricerca."""
        self.search_edit.clear()
        self.clear_results()
        self.status_label.setText("Ricerca pulita")
        
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
                        self.show_entity_details(entity_type, entity_id)
                        
    def _on_entity_double_click(self, entity_type):
        """Gestisce il doppio click nelle tab specifiche."""
        def handler():
            # Trova la tab attiva
            current_widget = self.results_tabs.currentWidget()
            current_row = current_widget.currentRow()
            
            if current_row >= 0:
                id_item = current_widget.item(current_row, 0)
                if id_item:
                    entity_id = id_item.data(Qt.UserRole)
                    if entity_id:
                        self.show_entity_details(entity_type, entity_id)
        
        return handler
        
    def show_entity_details(self, entity_type, entity_id):
        """Mostra i dettagli di un'entità."""
        dialog = EntityDetailsDialog(self.db_manager, entity_type, entity_id, self)
        dialog.exec_()
        
    def export_results(self):
        """Esporta i risultati in CSV o JSON."""
        if self.unified_table.rowCount() == 0:
            QMessageBox.information(self, "Export", "Nessun risultato da esportare")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Esporta Risultati", 
            f"ricerca_fuzzy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            if file_path.endswith('.json'):
                self.export_to_json(file_path)
            else:
                self.export_to_csv(file_path)
                
            QMessageBox.information(self, "Export", f"Risultati esportati in:\n{file_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "Errore Export", f"Errore durante l'export:\n{str(e)}")
            
    def export_to_csv(self, file_path):
        """Esporta in formato CSV."""
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Header
            writer.writerow(['Tipo', 'Nome/Descrizione', 'Dettagli', 'Similarità', 'Campo'])
            
            # Dati
            for row in range(self.unified_table.rowCount()):
                row_data = []
                for col in range(5):  # Escludi la colonna azioni
                    item = self.unified_table.item(row, col)
                    row_data.append(item.text() if item else '')
                writer.writerow(row_data)
                
    def export_to_json(self, file_path):
        """Esporta in formato JSON."""
        data = []
        
        for row in range(self.unified_table.rowCount()):
            item = self.unified_table.item(row, 0)
            full_data = item.data(Qt.UserRole) if item else {}
            
            if isinstance(full_data, dict) and 'full_data' in full_data:
                data.append(full_data['full_data'])
                
        with open(file_path, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False, default=str)
            
    def verify_indices(self):
        """Verifica lo stato degli indici GIN."""
        try:
            if hasattr(self.db_manager, 'verify_gin_indices'):
                result = self.db_manager.verify_gin_indices()
                
                if result.get('status') == 'OK':
                    total = result.get('total_indices', 0)
                    gin_count = result.get('gin_indices', 0)
                    self.indices_status_label.setText(f"Indici: {gin_count}/{total} GIN")
                    
                    if gin_count == total:
                        self.indices_status_label.setStyleSheet("color: green;")
                    else:
                        self.indices_status_label.setStyleSheet("color: orange;")
                else:
                    self.indices_status_label.setText("Indici: Errore")
                    self.indices_status_label.setStyleSheet("color: red;")
                    
            else:
                self.indices_status_label.setText("Indici: Non disponibile")
                
        except Exception as e:
            self.indices_status_label.setText("Indici: Errore")
            self.status_label.setText(f"Errore verifica indici: {str(e)}")

# ========================================================================
# FUNZIONE DI INTEGRAZIONE PER GUI PRINCIPALE
# ========================================================================

def integrate_expanded_fuzzy_search_widget(main_gui, db_manager):
    """Integra il widget di ricerca fuzzy ampliato nella GUI principale."""
    
    # Crea il widget
    fuzzy_widget = ExpandedFuzzySearchWidget(db_manager)
    
    # Aggiunge alla GUI principale come nuovo tab
    if hasattr(main_gui, 'tab_widget'):
        main_gui.tab_widget.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
        print("Widget ricerca fuzzy ampliato integrato come nuovo tab")
    else:
        print("ATTENZIONE: main_gui non ha tab_widget, integrazione manuale necessaria")
        
    return fuzzy_widget

# ========================================================================
# ESEMPIO DI UTILIZZO
# ========================================================================

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    print("Widget ricerca fuzzy ampliato per sistema catasto")
    print("Richiede: catasto_gin_extension_expanded.py e CatastoDBManager")
    
    # Esempio di app standalone (richiede configurazione database)
    app = QApplication(sys.argv)
    
    # Nota: richiede un db_manager configurato
    # widget = ExpandedFuzzySearchWidget(db_manager)
    # widget.show()
    
    print("Per utilizzare, integrare con integrate_expanded_fuzzy_search_widget(main_gui, db_manager)")
    # app.exec_()