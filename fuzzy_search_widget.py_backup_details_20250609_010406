# ========================================================================
# WIDGET RICERCA FUZZY - LAYOUT OTTIMIZZATO
# File: fuzzy_search_widget_optimized.py
# ========================================================================

"""
Widget per ricerca fuzzy con layout ottimizzato per massimizzare 
lo spazio dei risultati riducendo la parte controlli.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QLabel, QSlider, QCheckBox, 
    QTabWidget, QProgressBar, QGroupBox, QFormLayout, QSpinBox,
    QTextEdit, QFrame, QSplitter, QHeaderView, QMessageBox,
    QComboBox, QApplication, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon
import time
import logging

# Importa l'estensione GIN
try:
    from catasto_gin_extension import extend_db_manager_with_gin, format_search_results
except ImportError:
    print("ATTENZIONE: catasto_gin_extension.py non trovato. Assicurati che sia nella stessa cartella.")

class FuzzySearchWorker(QThread):
    """Worker thread per ricerche fuzzy in background."""
    
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, gin_search, query_text, options):
        super().__init__()
        self.gin_search = gin_search
        self.query_text = query_text
        self.options = options
        
    def run(self):
        """Esegue la ricerca in background."""
        try:
            self.progress_updated.emit(20)
            
            # Imposta soglia
            threshold = self.options.get('similarity_threshold', 0.3)
            self.gin_search.set_similarity_threshold(threshold)
            
            self.progress_updated.emit(50)
            
            # Ricerca combinata
            results = self.gin_search.search_combined_fuzzy(
                self.query_text,
                search_possessori=self.options.get('search_possessori', True),
                search_localita=self.options.get('search_localita', True),
                similarity_threshold=threshold,
                max_possessori=self.options.get('max_possessori', 50),
                max_localita=self.options.get('max_localita', 20)
            )
            
            self.progress_updated.emit(100)
            self.results_ready.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class CompactFuzzySearchWidget(QWidget):
    """
    Widget ricerca fuzzy con layout compatto ottimizzato per i risultati.
    """
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.gin_search = None
        self.search_worker = None
        self.logger = logging.getLogger("CatastoGUI")
        
        # Timer per debouncing della ricerca
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        
        self.setupUI()
        self.setup_gin_extension()
        
    def setupUI(self):
        """Configura l'interfaccia utente ottimizzata."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)  # Ridotto da 10 a 5
        main_layout.setContentsMargins(5, 5, 5, 5)  # Margini ridotti
        
        # === HEADER COMPATTO ===
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # Titolo più piccolo
        title_label = QLabel("🔍 Ricerca Avanzata")
        title_font = QFont()
        title_font.setPointSize(12)  # Ridotto da 14
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        self.status_label = QLabel("Pronto")
        self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 10px;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        
        main_layout.addLayout(header_layout)
        
        # === CONTROLLI COMPATTI IN RIGA SINGOLA ===
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel)
        controls_frame.setMaximumHeight(80)  # Altezza fissa ridotta
        
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setSpacing(3)
        controls_layout.setContentsMargins(8, 5, 8, 5)
        
        # Prima riga: Campo ricerca + Clear
        search_row = QHBoxLayout()
        search_row.setSpacing(5)
        
        search_label = QLabel("Cerca:")
        search_label.setMinimumWidth(40)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nome, cognome, località... (min 3 caratteri)")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        
        self.clear_button = QPushButton("✕")
        self.clear_button.setMaximumSize(QSize(25, 25))
        self.clear_button.setToolTip("Pulisci")
        self.clear_button.clicked.connect(self._clear_search)
        
        search_row.addWidget(search_label)
        search_row.addWidget(self.search_edit)
        search_row.addWidget(self.clear_button)
        
        # Seconda riga: Controlli in linea
        controls_row = QHBoxLayout()
        controls_row.setSpacing(15)
        
        # Precisione compatta
        precision_group = QHBoxLayout()
        precision_group.addWidget(QLabel("Precisione:"))
        
        self.precision_slider = QSlider(Qt.Horizontal)
        self.precision_slider.setRange(10, 80)
        self.precision_slider.setValue(30)
        self.precision_slider.valueChanged.connect(self._update_precision_label)
        self.precision_slider.setMaximumWidth(100)  # Slider più corto
        
        self.precision_label = QLabel("0.30")
        self.precision_label.setMinimumWidth(30)
        self.precision_label.setStyleSheet("font-weight: bold; color: blue; font-size: 10px;")
        
        precision_group.addWidget(self.precision_slider)
        precision_group.addWidget(self.precision_label)
        
        # Opzioni ricerca
        self.search_possessori_cb = QCheckBox("Possessori")
        self.search_possessori_cb.setChecked(True)
        self.search_localita_cb = QCheckBox("Località")
        self.search_localita_cb.setChecked(True)
        
        # Limite risultati
        limit_group = QHBoxLayout()
        limit_group.addWidget(QLabel("Max:"))
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["20", "50", "100", "200"])
        self.max_results_combo.setCurrentText("50")
        self.max_results_combo.setMaximumWidth(60)
        limit_group.addWidget(self.max_results_combo)
        
        # Pulsante verifica indici (compatto)
        self.check_indices_button = QPushButton("🔧")
        self.check_indices_button.setMaximumSize(QSize(30, 25))
        self.check_indices_button.setToolTip("Verifica Indici GIN")
        self.check_indices_button.clicked.connect(self._check_gin_indices)
        
        # Assembla la riga controlli
        controls_row.addLayout(precision_group)
        controls_row.addWidget(QLabel("|"))  # Separatore visivo
        controls_row.addWidget(self.search_possessori_cb)
        controls_row.addWidget(self.search_localita_cb)
        controls_row.addWidget(QLabel("|"))
        controls_row.addLayout(limit_group)
        controls_row.addStretch()
        controls_row.addWidget(self.check_indices_button)
        
        # Progress bar (nascosta di default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(3)  # Progress bar ultra-sottile
        
        # Assembla i controlli
        controls_layout.addLayout(search_row)
        controls_layout.addLayout(controls_row)
        controls_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(controls_frame)
        
        # === SEZIONE RISULTATI ESPANSA ===
        results_frame = QFrame()
        results_frame.setFrameStyle(QFrame.StyledPanel)
        results_layout = QVBoxLayout(results_frame)
        results_layout.setSpacing(5)
        results_layout.setContentsMargins(5, 5, 5, 5)
        
        # Barra statistiche compatta
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        
        self.stats_label = QLabel("Inserire almeno 3 caratteri per iniziare")
        self.stats_label.setStyleSheet("font-size: 11px; color: #666;")
        
        self.export_button = QPushButton("📋")
        self.export_button.setMaximumSize(QSize(30, 25))
        self.export_button.setToolTip("Esporta Risultati")
        self.export_button.clicked.connect(self._export_results)
        self.export_button.setEnabled(False)
        
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.export_button)
        
        results_layout.addLayout(stats_layout)
        
        # === TAB RISULTATI ESPANSI ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setTabPosition(QTabWidget.North)
        
        # Tab Possessori - Ottimizzato per spazio
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(6)  # Ridotto da 7 a 6 colonne
        self.possessori_table.setHorizontalHeaderLabels([
            "ID", "Nome Completo", "Comune", "Similarità", "Partite", "Azioni"
        ])
        
        # Configurazione tabella ottimizzata
        header = self.possessori_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Nome (espandibile)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Comune
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Similarità
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Partite
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Azioni
        
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.doubleClicked.connect(self._on_possessore_double_click)
        self.possessori_table.setShowGrid(False)  # Più pulito
        self.possessori_table.verticalHeader().setVisible(False)  # Nasconde numeri riga
        
        self.results_tabs.addTab(self.possessori_table, "👥 Possessori")
        
        # Tab Località - Ottimizzato
        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(6)
        self.localita_table.setHorizontalHeaderLabels([
            "ID", "Nome", "Tipo", "Comune", "Similarità", "Azioni"
        ])
        
        # Configurazione tabella località
        header_loc = self.localita_table.horizontalHeader()
        header_loc.setStretchLastSection(False)
        header_loc.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header_loc.setSectionResizeMode(1, QHeaderView.Stretch)          # Nome
        header_loc.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Tipo
        header_loc.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Comune
        header_loc.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Similarità
        header_loc.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Azioni
        
        self.localita_table.setAlternatingRowColors(True)
        self.localita_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.localita_table.doubleClicked.connect(self._on_localita_double_click)
        self.localita_table.setShowGrid(False)
        self.localita_table.verticalHeader().setVisible(False)
        
        self.results_tabs.addTab(self.localita_table, "🏠 Località")
        
        results_layout.addWidget(self.results_tabs)
        
        # === DEBUG AREA COLLASSABILE ===
        debug_frame = QFrame()
        debug_frame.setMaximumHeight(60)  # Area debug molto ridotta
        debug_layout = QVBoxLayout(debug_frame)
        debug_layout.setContentsMargins(5, 2, 5, 2)
        
        debug_header = QHBoxLayout()
        debug_toggle = QLabel("ℹ️ Debug")
        debug_toggle.setStyleSheet("font-size: 10px; color: #666;")
        
        self.indices_status_label = QLabel("Non verificato")
        self.indices_status_label.setStyleSheet("font-size: 10px; color: #666;")
        
        debug_header.addWidget(debug_toggle)
        debug_header.addStretch()
        debug_header.addWidget(self.indices_status_label)
        
        self.debug_text = QTextEdit()
        self.debug_text.setMaximumHeight(30)
        self.debug_text.setPlainText("Sistema ricerca fuzzy inizializzato...")
        self.debug_text.setStyleSheet("font-size: 9px; background-color: #f5f5f5;")
        
        debug_layout.addLayout(debug_header)
        debug_layout.addWidget(self.debug_text)
        
        # === LAYOUT FINALE CON PROPORZIONI ===
        # Usa proportion per dare più spazio ai risultati
        main_layout.addWidget(results_frame, 1)  # Peso 1 = espandibile
        main_layout.addWidget(debug_frame, 0)    # Peso 0 = dimensione fissa
        
        # Focus iniziale
        self.search_edit.setFocus()
        
    def setup_gin_extension(self):
        """Inizializza l'estensione GIN."""
        try:
            if not self.db_manager:
                self.debug_text.append("❌ Database manager non disponibile")
                self.status_label.setText("DB non disponibile")
                self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
                return
                
            self.gin_search = extend_db_manager_with_gin(self.db_manager)
            self.debug_text.append("✅ Estensione GIN inizializzata")
            self.status_label.setText("Pronto")
            self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 10px;")
            
        except Exception as e:
            self.debug_text.append(f"❌ Errore inizializzazione GIN: {e}")
            self.status_label.setText("Errore inizializzazione")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
            self.logger.error(f"Errore setup GIN extension: {e}")
            
    def _update_precision_label(self, value):
        """Aggiorna label precisione e colore."""
        precision = value / 100.0
        self.precision_label.setText(f"{precision:.2f}")
        
        # Colore basato su precisione
        if precision < 0.25:
            color = "red"  # Molto permissivo
        elif precision < 0.5:
            color = "blue"  # Medio
        else:
            color = "green"  # Restrittivo
            
        self.precision_label.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 10px;")
        
    def _on_search_text_changed(self, text):
        """Gestisce cambio testo con debouncing."""
        if len(text) >= 3:
            self.search_timer.stop()
            self.search_timer.start(600)  # Ridotto da 800ms a 600ms
            self.status_label.setText("Preparazione...")
            self.status_label.setStyleSheet("color: orange; font-weight: bold; font-size: 10px;")
        else:
            self.search_timer.stop()
            self._clear_results()
            
    def _perform_search(self):
        """Esegue la ricerca fuzzy."""
        query_text = self.search_edit.text().strip()
        
        if len(query_text) < 3:
            return
            
        if not self.gin_search:
            QMessageBox.warning(self, "Errore", "Estensione ricerca fuzzy non disponibile")
            return
            
        # Prepara opzioni
        max_results = int(self.max_results_combo.currentText())
        options = {
            'similarity_threshold': self.precision_slider.value() / 100.0,
            'search_possessori': self.search_possessori_cb.isChecked(),
            'search_localita': self.search_localita_cb.isChecked(),
            'max_possessori': max_results,
            'max_localita': max_results // 2
        }
        
        # Avvia ricerca in background
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ricerca...")
        self.status_label.setStyleSheet("color: blue; font-weight: bold; font-size: 10px;")
        
        self.search_worker = FuzzySearchWorker(self.gin_search, query_text, options)
        self.search_worker.results_ready.connect(self._display_results)
        self.search_worker.error_occurred.connect(self._handle_search_error)
        self.search_worker.progress_updated.connect(self.progress_bar.setValue)
        self.search_worker.start()
        
    def _display_results(self, results):
        """Visualizza risultati ricerca."""
        self.progress_bar.setVisible(False)
        
        # Salva risultati per export
        self.current_results = results
        
        # Popola tabelle
        possessori = results.get('possessori', [])
        localita = results.get('localita', [])
        
        self._populate_possessori_table(possessori)
        self._populate_localita_table(localita)
        
        # Aggiorna statistiche (più compatto)
        total = len(possessori) + len(localita)
        exec_time = results.get('execution_time', 0)
        
        self.stats_label.setText(
            f"🔍 '{results.get('query_text', '')}' → "
            f"{len(possessori)} possessori, {len(localita)} località "
            f"({exec_time:.3f}s)"
        )
        
        # Aggiorna tab titles
        self.results_tabs.setTabText(0, f"👥 Possessori ({len(possessori)})")
        self.results_tabs.setTabText(1, f"🏠 Località ({len(localita)})")
        
        # Abilita export se ci sono risultati
        self.export_button.setEnabled(total > 0)
        
        # Status
        self.status_label.setText(f"✓ {total} risultati")
        self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 10px;")
        
        self.debug_text.append(f"✅ '{results.get('query_text', '')}': {total} risultati")
        
    def _populate_possessori_table(self, possessori):
        """Popola tabella possessori ottimizzata."""
        self.possessori_table.setRowCount(len(possessori))
        
        for row, p in enumerate(possessori):
            # ID (più piccolo)
            id_item = QTableWidgetItem(str(p.get('id', '')))
            id_item.setData(Qt.UserRole, p)
            id_item.setTextAlignment(Qt.AlignCenter)
            self.possessori_table.setItem(row, 0, id_item)
            
            # Nome completo (principale)
            nome_item = QTableWidgetItem(p.get('nome_completo', ''))
            nome_item.setToolTip(f"Cognome: {p.get('cognome_nome', 'N/A')}\nPaternità: {p.get('paternita', 'N/A')}")
            self.possessori_table.setItem(row, 1, nome_item)
            
            # Comune
            self.possessori_table.setItem(row, 2, QTableWidgetItem(p.get('comune_nome', '')))
            
            # Similarità con colore e centrato
            similarity = p.get('similarity_score', 0)
            sim_item = QTableWidgetItem(f"{similarity:.3f}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            if similarity > 0.7:
                sim_item.setBackground(QColor(144, 238, 144))  # Verde
            elif similarity > 0.5:
                sim_item.setBackground(QColor(255, 255, 224))  # Giallo
            else:
                sim_item.setBackground(QColor(255, 228, 225))  # Rosa
            self.possessori_table.setItem(row, 3, sim_item)
            
            # Numero partite
            partite_item = QTableWidgetItem(str(p.get('num_partite', 0)))
            partite_item.setTextAlignment(Qt.AlignCenter)
            self.possessori_table.setItem(row, 4, partite_item)
            
            # Pulsante azioni
            action_item = QTableWidgetItem("👁️")
            action_item.setTextAlignment(Qt.AlignCenter)
            action_item.setToolTip("Doppio click per dettagli")
            self.possessori_table.setItem(row, 5, action_item)
            
    def _populate_localita_table(self, localita):
        """Popola tabella località ottimizzata."""
        self.localita_table.setRowCount(len(localita))
        
        for row, l in enumerate(localita):
            # ID
            id_item = QTableWidgetItem(str(l.get('id', '')))
            id_item.setData(Qt.UserRole, l)
            id_item.setTextAlignment(Qt.AlignCenter)
            self.localita_table.setItem(row, 0, id_item)
            
            # Nome con civico
            nome = l.get('nome', '')
            civico = l.get('civico', '')
            nome_completo = f"{nome} {civico}" if civico else nome
            self.localita_table.setItem(row, 1, QTableWidgetItem(nome_completo))
            
            # Tipo
            self.localita_table.setItem(row, 2, QTableWidgetItem(l.get('tipo', '')))
            
            # Comune
            self.localita_table.setItem(row, 3, QTableWidgetItem(l.get('comune_nome', '')))
            
            # Similarità con colore
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
            
            # Azioni
            action_item = QTableWidgetItem("👁️")
            action_item.setTextAlignment(Qt.AlignCenter)
            action_item.setToolTip("Doppio click per dettagli")
            self.localita_table.setItem(row, 5, action_item)
            
    # === METODI UTILITY (copiati dal widget originale) ===
    
    def _clear_search(self):
        """Pulisce ricerca e risultati."""
        self.search_edit.clear()
        self._clear_results()
        
    def _clear_results(self):
        """Pulisce solo i risultati."""
        self.possessori_table.setRowCount(0)
        self.localita_table.setRowCount(0)
        self.stats_label.setText("Inserire almeno 3 caratteri per iniziare")
        self.results_tabs.setTabText(0, "👥 Possessori")
        self.results_tabs.setTabText(1, "🏠 Località")
        self.export_button.setEnabled(False)
        self.status_label.setText("Pronto")
        self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 10px;")
        
    def _handle_search_error(self, error_message):
        """Gestisce errori di ricerca."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Errore")
        self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
        self.debug_text.append(f"❌ Errore: {error_message}")
        QMessageBox.critical(self, "Errore Ricerca", f"Errore durante la ricerca:\n{error_message}")
        
    def _check_gin_indices(self):
        """Verifica stato indici GIN."""
        if not self.gin_search:
            self.indices_status_label.setText("❌ Non disponibile")
            return
            
        try:
            indices = self.gin_search.get_gin_indices_info()
            if indices:
                self.indices_status_label.setText(f"✅ {len(indices)} indici")
                self.debug_text.append(f"✅ Indici: {len(indices)} trovati")
                
                QMessageBox.information(
                    self, "Indici GIN", 
                    f"✅ Trovati {len(indices)} indici GIN attivi\n\n"
                    "Il sistema di ricerca fuzzy è operativo."
                )
            else:
                self.indices_status_label.setText("❌ Nessun indice")
                self.debug_text.append("❌ Nessun indice GIN")
                QMessageBox.warning(self, "Indici GIN", "❌ Nessun indice GIN trovato!")
                
        except Exception as e:
            self.indices_status_label.setText("❌ Errore")
            self.debug_text.append(f"❌ Errore indici: {e}")
            
    def _export_results(self):
        """Esporta risultati."""
        if not hasattr(self, 'current_results'):
            return
            
        try:
            formatted_text = format_search_results(self.current_results)
            
            from PyQt5.QtWidgets import QTextEdit, QDialog, QVBoxLayout, QPushButton
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Export Risultati Ricerca")
            dialog.resize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            text_edit = QTextEdit()
            text_edit.setPlainText(formatted_text)
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)
            
            close_button = QPushButton("Chiudi")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)
            
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "Errore Export", f"Errore esportazione:\n{e}")
            
    def _on_possessore_double_click(self, index):
        """Gestisce doppio click su possessore."""
        item = self.possessori_table.item(index.row(), 0)
        if item:
            possessore_data = item.data(Qt.UserRole)
            QMessageBox.information(
                self, f"Possessore ID {possessore_data.get('id')}",
                f"👤 {possessore_data.get('nome_completo', 'N/A')}\n"
                f"🏛️ {possessore_data.get('comune_nome', 'N/A')}\n"
                f"📋 {possessore_data.get('num_partite', 0)} partite collegate\n\n"
                f"🔗 Collegamento ai dettagli sarà implementato"
            )
            
    def _on_localita_double_click(self, index):
        """Gestisce doppio click su località."""
        item = self.localita_table.item(index.row(), 0)
        if item:
            localita_data = item.data(Qt.UserRole)
            civico = f" {localita_data.get('civico', '')}" if localita_data.get('civico') else ""
            QMessageBox.information(
                self, f"Località ID {localita_data.get('id')}",
                f"🏠 {localita_data.get('nome', 'N/A')}{civico}\n"
                f"📍 {localita_data.get('tipo', 'N/A')}\n"
                f"🏛️ {localita_data.get('comune_nome', 'N/A')}\n\n"
                f"🔗 Collegamento ai dettagli sarà implementato"
            )

# ========================================================================
# FUNZIONE DI INTEGRAZIONE AGGIORNATA
# ========================================================================

def add_optimized_fuzzy_search_tab_to_main_window(main_window):
    """
    Aggiunge il tab di ricerca fuzzy ottimizzato alla finestra principale.
    """
    try:
        if not hasattr(main_window, 'db_manager') or not main_window.db_manager:
            main_window.logger.warning("Database manager non disponibile per ricerca fuzzy")
            return False
            
        # Crea il widget ottimizzato
        fuzzy_widget = CompactFuzzySearchWidget(main_window.db_manager, main_window)
        
        # Aggiunge al TabWidget principale
        tab_index = main_window.tabs.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
        
        main_window.logger.info(f"Tab Ricerca Fuzzy Ottimizzato aggiunto all'indice {tab_index}")
        return True
        
    except Exception as e:
        main_window.logger.error(f"Errore aggiunta tab ricerca fuzzy ottimizzato: {e}")
        return False
