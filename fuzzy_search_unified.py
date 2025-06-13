#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
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
    QSizePolicy,QMessageBox, QApplication, QFileDialog, QDialog 
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont
# --- AGGIUNGERE QUESTE IMPORTAZIONI ---
from dialogs import PartitaDetailsDialog, ModificaPossessoreDialog, ModificaLocalitaDialog
# Assumiamo che esista un ModificaImmobileDialog, se non c'è lo gestiremo nel fallback
try:
    from dialogs import ModificaImmobileDialog
except ImportError:
    ModificaImmobileDialog = None # Fallback se non esiste
# --- FINE AGGIUNTE ---


# ========================================================================
# THREAD UNIFICATO PER RICERCHE IN BACKGROUND
# ========================================================================

class UnifiedFuzzySearchThread(QThread):
    """Thread unificato per eseguire ricerche fuzzy in background."""
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, gin_search_manager, query_text, options):
        super().__init__()
        self.gin_search_manager = gin_search_manager
        self.query_text = query_text
        self.options = options

    def run(self):
        """Esegue la ricerca fuzzy."""
        try:
            self.progress_updated.emit(10)
            
            threshold = self.options.get('threshold', 0.3)
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

            self.progress_updated.emit(100)
            self.results_ready.emit(final_results)

        except Exception as e:
            logging.getLogger(__name__).error(f"Errore nel thread di ricerca: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


# ========================================================================
# WIDGET PRINCIPALE UNIFICATO
# ========================================================================

class UnifiedFuzzySearchWidget(QWidget):
    """Widget unificato per ricerca fuzzy con una singola interfaccia robusta."""

    # --- MODIFICA: Il costruttore non ha più il parametro 'mode' ---
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

        # Setup UI
        self._init_ui() # --- MODIFICA: Chiamata a un singolo metodo di setup UI
        self._setup_signals()
        self._check_gin_status()

  

    def _init_ui(self):
        """Configura l'interfaccia utente unificata con un layout robusto."""
        # Layout principale dell'intero widget
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
        controls_row = QHBoxLayout()
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
        self.export_btn = QPushButton("📤 Export")
        self.export_btn.setEnabled(False)
        controls_row.addWidget(self.export_btn)
        search_layout.addLayout(controls_row)
        
        content_layout.addWidget(search_frame) # AGGIUNTO AL CONTENT_LAYOUT

        # === CHECKBOXES (da aggiungere al content_layout) ===
        types_layout = QHBoxLayout()
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
        self.variazioni_table = self._create_table_widget(["Tipo", "Data", "Descrizione", "Similitud."], [2], 3); self.results_tabs.addTab(self.variazioni_table, "📋 Variazioni")
        self.contratti_table = self._create_table_widget(["Tipo", "Data", "Partita", "Similitud."], [0], 3); self.results_tabs.addTab(self.contratti_table, "📄 Contratti")
        self.partite_table = self._create_table_widget(["Numero", "Suffisso", "Tipo", "Comune", "Similitud."], [3], 4); self.results_tabs.addTab(self.partite_table, "📊 Partite")

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

    def _setup_signals(self):
        """Configura i segnali."""
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.search_btn.clicked.connect(self._perform_search)
        self.clear_btn.clicked.connect(self._clear_search)
        
        self.precision_slider.valueChanged.connect(lambda v: self.precision_label.setText(f"{v/100:.2f}"))
        self.precision_slider.sliderReleased.connect(self._trigger_search_if_text)

        self.max_results_combo.currentTextChanged.connect(self._trigger_search_if_text)
        self.export_btn.clicked.connect(self._export_results)

        # Checkbox
        for cb in [self.search_possessori_cb, self.search_localita_cb, self.search_immobili_cb,
                   self.search_variazioni_cb, self.search_contratti_cb, self.search_partite_cb]: # AGGIUNTE NUOVE CHECKBOX
            cb.toggled.connect(self._trigger_search_if_text)

        # Double-click
        self.unified_table.doubleClicked.connect(self._on_unified_double_click)
        # Qui potresti aggiungere i double-click per le tabelle individuali se necessario
        # self.possessori_table.doubleClicked.connect(...)

    def _check_gin_status(self):
        """Verifica lo stato degli indici GIN."""
        if not self.gin_search or not hasattr(self.gin_search, 'verify_gin_indices'):
            self.indices_status_label.setText("❌ Ricerca non disponibile")
            return
        try:
            result = self.gin_search.verify_gin_indices()
            if result.get('status') == 'OK' and result.get('gin_indices', 0) > 0:
                self.indices_status_label.setText(f"✅ Indici GIN attivi ({result['gin_indices']})")
            else:
                self.indices_status_label.setText("⚠️ Indici GIN mancanti o non validi")
        except Exception as e:
            self.indices_status_label.setText("❌ Errore verifica indici")
            self.logger.error(f"Errore verifica indici GIN: {e}")

    def _on_search_text_changed(self, text):
        """Gestisce il cambiamento del testo di ricerca."""
        if len(text) >= 3:
            self.search_timer.start(800) # Delay per evitare ricerche a ogni tasto
            self.stats_label.setText("Pronto per la ricerca...")
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

        # --- MODIFICA CRUCIALE: Gestione del thread esistente ---
        if self.search_thread and self.search_thread.isRunning():
            self.logger.debug("Ricerca precedente ancora in corso. Tentativo di fermarla.")
            self.search_thread.quit()  # Chiede al thread di terminare in modo pulito
            self.search_thread.wait(500) # Attende al massimo 500ms
            if self.search_thread.isRunning():
                self.logger.warning("Il thread precedente non si è fermato in tempo, terminazione forzata.")
                self.search_thread.terminate() # Estrema ratio
                self.search_thread.wait()

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
        
        self.search_thread = UnifiedFuzzySearchThread(self.gin_search, query_text, search_options)
        self.search_thread.results_ready.connect(self._display_results)
        self.search_thread.error_occurred.connect(self._handle_search_error)
        self.search_thread.finished.connect(lambda: self.search_btn.setEnabled(True))
        self.search_thread.start()

    def _display_results(self, results):
        """Visualizza i risultati della ricerca."""
        self.current_results = results
        results_by_type = results.get('results_by_type', {})
        
        self._populate_unified_table(results_by_type)
        self._populate_individual_tables(results_by_type)
        self._update_tab_counters(results_by_type)
        
        total = results.get('total_results', 0)
        self.stats_label.setText(f"Trovati {total} risultati per '{results.get('query_text')}'")
        self.export_btn.setEnabled(total > 0)
    
    def _populate_table(self, table: QTableWidget, data: List[Dict], row_mapper_func):
        """Funzione helper per popolare una QTableWidget."""
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

        # --- AGGIUNGERE QUESTE CHIAMATE ---
        self._populate_table(self.variazioni_table, results_by_type.get('variazione', []), 
            lambda v: [v.get('tipo', ''), v.get('data_variazione', ''), v.get('descrizione', ''), f"{v.get('similarity_score', 0):.3f}"])

        self._populate_table(self.contratti_table, results_by_type.get('contratto', []), 
            lambda c: [c.get('tipo', ''), c.get('data_contratto', ''), c.get('numero_partita', ''), f"{c.get('similarity_score', 0):.3f}"])

        self._populate_table(self.partite_table, results_by_type.get('partita', []), 
            lambda pt: [pt.get('numero_partita', ''), pt.get('suffisso_partita', '') or '', pt.get('tipo_partita', ''), pt.get('comune_nome', ''), f"{pt.get('similarity_score', 0):.3f}"])

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
            self.partite_table # AGGIUNTE NUOVE TABELLE
        ]
        for table in tables:
            table.setRowCount(0)
        
        # --- MODIFICA: `_update_tab_counters` ora gestisce anche il caso vuoto ---
        self._update_tab_counters({})
        
        self.export_btn.setEnabled(False)
        self.current_results = {}

    def _handle_search_error(self, error_message):
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

    # In fuzzy_search_unified.py, dentro la classe UnifiedFuzzySearchWidget

    def _on_unified_double_click(self, index):
        """
        Gestisce il doppio click nella tabella unificata, aprendo un dialogo
        di dettaglio appropriato in base al tipo di entità.
        """
        if not index.isValid():
            return
            
        item_con_dati = self.unified_table.item(index.row(), 0)
        if not item_con_dati:
            return

        full_item_data = item_con_dati.data(Qt.UserRole)
        if not isinstance(full_item_data, dict):
            return

        entity_type = full_item_data.get('type')
        entity_data = full_item_data.get('data', {})
        entity_id = entity_data.get('entity_id')

        if not entity_type or not entity_id:
            QMessageBox.warning(self, "Errore Dati", "Impossibile recuperare tipo o ID dell'entità selezionata.")
            return

        self.logger.info(f"Doppio click su entità di tipo '{entity_type}' con ID {entity_id}.")

        # --- Logica di smistamento per aprire il dialogo corretto ---

        if entity_type == 'partita':
            # Per PartitaDetailsDialog serve il dizionario completo dei dettagli
            full_details = self.db_manager.get_partita_details(entity_id)
            if full_details:
                dialog = PartitaDetailsDialog(full_details, self)
                dialog.exec_()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per la partita ID {entity_id}.")
        
        elif entity_type == 'possessore':
            # Riusiamo il dialogo di modifica, che mostra già tutti i dettagli
            dialog = ModificaPossessoreDialog(self.db_manager, entity_id, self)
            dialog.exec_()
            # Se il dialogo viene accettato (modifiche salvate), rieseguiamo la ricerca
            if dialog.result() == QDialog.Accepted:
                self._perform_search()

        elif entity_type == 'localita':
            # Riusiamo il dialogo di modifica. Dobbiamo recuperare il comune_id.
            localita_details = self.db_manager.get_localita_details(entity_id)
            if localita_details and localita_details.get('comune_id'):
                dialog = ModificaLocalitaDialog(self.db_manager, entity_id, localita_details.get('comune_id'), self)
                dialog.exec_()
                if dialog.result() == QDialog.Accepted:
                    self._perform_search()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per la località ID {entity_id}.")

        elif entity_type == 'immobile' and ModificaImmobileDialog:
             # Riusiamo il dialogo di modifica. Dobbiamo recuperare il comune_id della partita a cui appartiene.
            immobile_details = self.db_manager.get_immobile_details(entity_id)
            if immobile_details and immobile_details.get('partita_id'):
                partita_details = self.db_manager.get_partita_details(immobile_details.get('partita_id'))
                if partita_details and partita_details.get('comune_id'):
                    dialog = ModificaImmobileDialog(self.db_manager, entity_id, partita_details.get('comune_id'), self)
                    dialog.exec_()
                    if dialog.result() == QDialog.Accepted:
                        self._perform_search()
                else:
                    QMessageBox.warning(self, "Errore Dati", f"Impossibile determinare il comune per l'immobile ID {entity_id}.")
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile caricare i dettagli per l'immobile ID {entity_id}.")

        else:
            # Fallback per tutti gli altri tipi: mostra un popup formattato e leggibile
            testo_formattato = f"<h3>Dettagli - {entity_type.title()} ID: {entity_id}</h3>"
            testo_formattato += "<table border='0' cellspacing='5'>"
            for key, value in entity_data.items():
                chiave_formattata = key.replace('_', ' ').title()
                testo_formattato += f"<tr><td><b>{chiave_formattata}:</b></td><td>{value}</td></tr>"
            testo_formattato += "</table>"
            
            QMessageBox.information(self, f"Dettagli - {entity_type.title()}", testo_formattato)
    # --- METODI PER EXPORT (da implementare o semplificare) ---
    def _export_results(self):
        if not self.current_results or not self.current_results.get('total_results', 0) > 0:
            QMessageBox.warning(self, "Nessun Risultato", "Non ci sono risultati da esportare.")
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Esporta Risultati", f"ricerca_fuzzy_{datetime.now():%Y%m%d_%H%M%S}",
            "File JSON (*.json);;File CSV (*.csv);;File di Testo (*.txt)"
        )

        if not file_path:
            return

        try:
            if selected_filter.startswith("File JSON"):
                self._export_to_json(file_path)
            elif selected_filter.startswith("File CSV"):
                self._export_to_csv(file_path)
            else: # TXT
                self._export_to_txt(file_path)
            QMessageBox.information(self, "Esportazione Completata", f"Dati esportati con successo in:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore Esportazione", f"Si è verificato un errore: {e}")
            self.logger.error(f"Errore esportazione dati fuzzy: {e}", exc_info=True)

    def _export_to_json(self, file_path):
        export_data = self.current_results
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

    def _export_to_txt(self, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"Risultati Ricerca Fuzzy per: '{self.current_results.get('query_text')}'\n")
            f.write(f"Data: {self.current_results.get('timestamp')}\n")
            f.write("="*80 + "\n\n")
            
            for entity_type, entities in self.current_results.get('results_by_type', {}).items():
                if entities:
                    f.write(f"--- {entity_type.upper()} ({len(entities)}) ---\n")
                    for entity in entities:
                        display = entity.get('display_text', 'N/D')
                        detail = entity.get('detail_text', '')
                        score = entity.get('similarity_score', 0)
                        f.write(f"- {display} | {detail} (Score: {score:.3f})\n")
                    f.write("\n")

    def _export_to_csv(self, file_path):
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['entity_type', 'display_text', 'detail_text', 'similarity_score', 'search_field', 'entity_id'])
            
            for entity_type, entities in self.current_results.get('results_by_type', {}).items():
                for entity in entities:
                    writer.writerow([
                        entity_type,
                        entity.get('display_text', ''),
                        entity.get('detail_text', ''),
                        entity.get('similarity_score', 0),
                        entity.get('search_field', ''),
                        entity.get('entity_id', '')
                    ])

# ========================================================================
# FUNZIONI DI INTEGRAZIONE
# ========================================================================

def add_fuzzy_search_tab_to_main_window(main_window, mode='compact'):
    """
    Aggiunge il tab di ricerca fuzzy alla finestra principale.
    
    Args:
        main_window: Istanza di CatastoMainWindow
        mode: 'compact' o 'expanded'
        
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
        fuzzy_widget = UnifiedFuzzySearchWidget(main_window.db_manager, mode, main_window)
        
        # Aggiunge il tab alla finestra principale
        tab_index = main_window.tabs.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
        
        if hasattr(main_window, 'logger'):
            main_window.logger.info(f"Tab Ricerca Fuzzy ({mode}) aggiunto all'indice {tab_index}")
        else:
            print(f"✅ Tab Ricerca Fuzzy ({mode}) aggiunto all'indice {tab_index}")
        
        return True
        
    except Exception as e:
        if hasattr(main_window, 'logger'):
            main_window.logger.error(f"Errore aggiunta tab ricerca fuzzy: {e}")
        else:
            print(f"❌ Errore aggiunta tab ricerca fuzzy: {e}")
        
        import traceback
        traceback.print_exc()
        return False