# ========================================================================
# WIDGET RICERCA FUZZY COMPLETO - VERSIONE CON DIALOGHI INTEGRATI
# File: fuzzy_search_widget.py
# ========================================================================

"""
Widget completo per ricerca fuzzy con indici GIN, layout ottimizzato 
e collegamento ai dialoghi esistenti PartitaDetailsDialog e ModificaPartitaDialog.

Funzionalità:
- Ricerca fuzzy in tempo reale con tolleranza errori
- Layout ottimizzato per massimizzare spazio risultati
- Collegamento completo ai dettagli di possessori e località
- Integrazione con PartitaDetailsDialog e ModificaPartitaDialog esistenti
- Esportazione risultati e verifica indici GIN
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QLabel, QSlider, QCheckBox, 
    QTabWidget, QProgressBar, QGroupBox, QFormLayout, QSpinBox,
    QTextEdit, QFrame, QSplitter, QHeaderView, QMessageBox,
    QComboBox, QApplication, QSizePolicy, QScrollArea, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon
import time
import logging
import psycopg2.extras

# Importa l'estensione GIN
try:
    from catasto_gin_extension import extend_db_manager_with_gin, format_search_results
except ImportError:
    print("ATTENZIONE: catasto_gin_extension.py non trovato. Assicurati che sia nella stessa cartella.")

# Importa i dialoghi esistenti per partite
try:
    from gui_widgets import PartitaDetailsDialog, ModificaPartitaDialog
    DIALOGHI_PARTITA_DISPONIBILI = True
except ImportError:
    print("ATTENZIONE: PartitaDetailsDialog e/o ModificaPartitaDialog non trovati in gui_widgets")
    DIALOGHI_PARTITA_DISPONIBILI = False

# ========================================================================
# WORKER THREAD PER RICERCHE IN BACKGROUND
# ========================================================================

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

# ========================================================================
# WIDGET PRINCIPALE RICERCA FUZZY
# ========================================================================

class CompactFuzzySearchWidget(QWidget):
    """
    Widget ricerca fuzzy con layout compatto ottimizzato per i risultati
    e integrazione completa con i dialoghi esistenti delle partite.
    """
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger("FuzzySearch")
        
        # Estende il DB manager con funzionalità GIN
        self.gin_search = extend_db_manager_with_gin(db_manager)
        
        # Timer per ricerca differita
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        
        # Worker thread
        self.search_worker = None
        
        self._setup_compact_ui()
        self._setup_signals()
        self._check_gin_status()
    
    def _setup_compact_ui(self):
        """Setup UI compatta."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)
        
        # === BARRA DI RICERCA COMPATTA ===
        search_frame = QFrame()
        search_frame.setFrameStyle(QFrame.StyledPanel)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(8, 6, 8, 6)
        
        # Campo ricerca principale
        search_layout.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca possessori, località, ecc... (min. 3 caratteri)")
        self.search_edit.setMinimumWidth(300)
        search_layout.addWidget(self.search_edit, stretch=2)
        
        # Controlli compatti in linea
        search_layout.addWidget(QLabel("Precisione:"))
        self.precision_slider = QSlider(Qt.Horizontal)
        self.precision_slider.setRange(20, 90)
        self.precision_slider.setValue(30)
        self.precision_slider.setMaximumWidth(80)
        search_layout.addWidget(self.precision_slider)
        
        self.precision_label = QLabel("30%")
        self.precision_label.setMinimumWidth(35)
        search_layout.addWidget(self.precision_label)
        
        search_layout.addWidget(QLabel("Max:"))
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["10", "25", "50", "100"])
        self.max_results_combo.setCurrentText("25")
        self.max_results_combo.setMaximumWidth(60)
        search_layout.addWidget(self.max_results_combo)
        
        # Checkbox compatte
        self.search_possessori_cb = QCheckBox("Possessori")
        self.search_possessori_cb.setChecked(True)
        search_layout.addWidget(self.search_possessori_cb)
        
        self.search_localita_cb = QCheckBox("Località")
        self.search_localita_cb.setChecked(True)
        search_layout.addWidget(self.search_localita_cb)
        
        main_layout.addWidget(search_frame)
        
        # === BARRA STATO COMPATTA ===
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("Inserisci almeno 3 caratteri per iniziare")
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(120)
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(status_layout)
        
        # === AREA RISULTATI MASSIMIZZATA ===
        self.results_splitter = QSplitter(Qt.Horizontal)
        
        # Possessori
        possessori_widget = self._create_possessori_widget()
        self.results_splitter.addWidget(possessori_widget)
        
        # Località  
        localita_widget = self._create_localita_widget()
        self.results_splitter.addWidget(localita_widget)
        
        # Imposta proporzioni: 60% possessori, 40% località
        self.results_splitter.setSizes([600, 400])
        
        main_layout.addWidget(self.results_splitter, stretch=1)
    
    def _create_possessori_widget(self):
        """Crea widget possessori con pulsanti per dialoghi partite."""
        possessori_group = QGroupBox("👤 Possessori")
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
        
        # Pulsanti azioni possessori
        buttons_layout = QHBoxLayout()
        
        self.btn_dettagli_possessore = QPushButton("Dettagli Possessore")
        self.btn_dettagli_possessore.clicked.connect(self._mostra_dettagli_possessore)
        self.btn_dettagli_possessore.setEnabled(False)
        buttons_layout.addWidget(self.btn_dettagli_possessore)
        
        self.btn_partite_possessore = QPushButton("Vedi Partite")
        self.btn_partite_possessore.clicked.connect(self._mostra_partite_possessore)
        self.btn_partite_possessore.setEnabled(False)
        buttons_layout.addWidget(self.btn_partite_possessore)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return possessori_group
    
    def _create_localita_widget(self):
        """Crea widget località con pulsanti per dialoghi partite."""
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
        
        # Pulsanti azioni località
        buttons_layout = QHBoxLayout()
        
        self.btn_dettagli_localita = QPushButton("Dettagli Località")
        self.btn_dettagli_localita.clicked.connect(self._mostra_dettagli_localita)
        self.btn_dettagli_localita.setEnabled(False)
        buttons_layout.addWidget(self.btn_dettagli_localita)
        
        self.btn_immobili_localita = QPushButton("Vedi Immobili")
        self.btn_immobili_localita.clicked.connect(self._mostra_immobili_localita)
        self.btn_immobili_localita.setEnabled(False)
        buttons_layout.addWidget(self.btn_immobili_localita)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        return localita_group
    
    def _setup_signals(self):
        """Configura segnali."""
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
        
        # Selezioni tabelle
        self.possessori_table.itemSelectionChanged.connect(self._on_possessori_selection_changed)
        self.localita_table.itemSelectionChanged.connect(self._on_localita_selection_changed)
        
        # Doppio click per azioni rapide
        self.possessori_table.itemDoubleClicked.connect(self._on_possessore_double_click)
        self.localita_table.itemDoubleClicked.connect(self._on_localita_double_click)
    
    def _check_gin_status(self):
        """Verifica stato indici GIN."""
        if not self.gin_search:
            self.status_label.setText("⚠️ Ricerca fuzzy non disponibile")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
            self.search_edit.setEnabled(False)
            return
            
        try:
            status_info = self.gin_search.check_gin_indexes_status()
            if status_info['all_indexes_exist']:
                self.status_label.setText("✅ Ricerca fuzzy attiva")
                self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 10px;")
            else:
                missing = len(status_info['missing_indexes'])
                self.status_label.setText(f"⚠️ {missing} indici GIN mancanti")
                self.status_label.setStyleSheet("color: orange; font-weight: bold; font-size: 10px;")
        except Exception as e:
            self.status_label.setText("❌ Errore verifica indici")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
    
    def _on_search_text_changed(self, text):
        """Gestisce cambiamento testo ricerca."""
        if len(text) >= 3:
            self.search_timer.stop()
            self.search_timer.start(600)
            self.status_label.setText("Preparazione...")
            self.status_label.setStyleSheet("color: orange; font-weight: bold; font-size: 10px;")
        else:
            self.search_timer.stop()
            self._clear_results()
    
    def _trigger_search_if_text(self):
        """Rilancia ricerca se c'è testo sufficiente."""
        if len(self.search_edit.text().strip()) >= 3:
            self.search_timer.stop()
            self.search_timer.start(300)  # Ricerca più veloce per cambi opzioni
    
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
        try:
            # Aggiorna possessori
            possessori = results.get('possessori', [])
            self._populate_possessori_table(possessori)
            
            # Aggiorna località
            localita = results.get('localita', [])
            self._populate_localita_table(localita)
            
            # Aggiorna status
            total_results = len(possessori) + len(localita)
            if total_results > 0:
                self.status_label.setText(f"✅ {total_results} risultati ({len(possessori)} possessori, {len(localita)} località)")
                self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 10px;")
            else:
                self.status_label.setText("ℹ️ Nessun risultato trovato")
                self.status_label.setStyleSheet("color: gray; font-weight: bold; font-size: 10px;")
                
        except Exception as e:
            self.logger.error(f"Errore visualizzazione risultati: {e}")
            self.status_label.setText("❌ Errore visualizzazione")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
        finally:
            self.progress_bar.setVisible(False)
    
    def _populate_possessori_table(self, possessori):
        """Popola tabella possessori."""
        self.possessori_table.setRowCount(len(possessori))
        
        for row, possessore in enumerate(possessori):
            # Nome completo
            item_nome = QTableWidgetItem(possessore.get('nome_completo', ''))
            item_nome.setData(Qt.UserRole, possessore)  # Salva dati completi
            self.possessori_table.setItem(row, 0, item_nome)
            
            # Comune
            self.possessori_table.setItem(row, 1, 
                QTableWidgetItem(possessore.get('comune_nome', '')))
            
            # Numero partite
            num_partite = possessore.get('num_partite', 0)
            self.possessori_table.setItem(row, 2, 
                QTableWidgetItem(str(num_partite)))
            
            # Similarità
            similarita = possessore.get('similarity', 0)
            self.possessori_table.setItem(row, 3, 
                QTableWidgetItem(f"{similarita:.1%}"))
        
        self.possessori_table.resizeColumnsToContents()
    
    def _populate_localita_table(self, localita):
        """Popola tabella località."""
        self.localita_table.setRowCount(len(localita))
        
        for row, loc in enumerate(localita):
            # Nome località
            item_nome = QTableWidgetItem(loc.get('nome', ''))
            item_nome.setData(Qt.UserRole, loc)  # Salva dati completi
            self.localita_table.setItem(row, 0, item_nome)
            
            # Comune
            self.localita_table.setItem(row, 1, 
                QTableWidgetItem(loc.get('comune_nome', '')))
            
            # Numero immobili
            num_immobili = loc.get('num_immobili', 0)
            self.localita_table.setItem(row, 2, 
                QTableWidgetItem(str(num_immobili)))
            
            # Similarità
            similarita = loc.get('similarity', 0)
            self.localita_table.setItem(row, 3, 
                QTableWidgetItem(f"{similarita:.1%}"))
        
        self.localita_table.resizeColumnsToContents()
    
    def _handle_search_error(self, error_msg):
        """Gestisce errori ricerca."""
        self.logger.error(f"Errore ricerca fuzzy: {error_msg}")
        self.status_label.setText(f"❌ Errore: {error_msg}")
        self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
        self.progress_bar.setVisible(False)
    
    def _clear_results(self):
        """Pulisce risultati."""
        self.possessori_table.setRowCount(0)
        self.localita_table.setRowCount(0)
        self.status_label.setText("Inserisci almeno 3 caratteri per iniziare")
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        self._aggiorna_stato_pulsanti()
    
    # ========================================================================
    # GESTIONE SELEZIONI E PULSANTI
    # ========================================================================
    
    def _on_possessori_selection_changed(self):
        """Gestisce cambio selezione possessori."""
        self._aggiorna_stato_pulsanti()
    
    def _on_localita_selection_changed(self):
        """Gestisce cambio selezione località."""
        self._aggiorna_stato_pulsanti()
    
    def _aggiorna_stato_pulsanti(self):
        """Aggiorna stato pulsanti in base alle selezioni."""
        has_possessore_selection = bool(self.possessori_table.selectedItems())
        self.btn_dettagli_possessore.setEnabled(has_possessore_selection)
        self.btn_partite_possessore.setEnabled(has_possessore_selection)
        
        has_localita_selection = bool(self.localita_table.selectedItems())
        self.btn_dettagli_localita.setEnabled(has_localita_selection)
        self.btn_immobili_localita.setEnabled(has_localita_selection)
    
    # ========================================================================
    # AZIONI SU POSSESSORI CON INTEGRAZIONE DIALOGHI PARTITE
    # ========================================================================
    
    def _on_possessore_double_click(self, item):
        """Gestisce doppio click su possessore - mostra dettagli."""
        self._mostra_dettagli_possessore()
    
    def _mostra_dettagli_possessore(self):
        """Mostra dettagli possessore selezionato."""
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selezione", "Seleziona un possessore dalla tabella.")
            return
        
        row = selected_items[0].row()
        item = self.possessori_table.item(row, 0)
        possessore_data = item.data(Qt.UserRole)
        
        if not possessore_data:
            QMessageBox.warning(self, "Errore", "Dati possessore non disponibili.")
            return
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Recupera partite collegate al possessore
            possessore_id = possessore_data.get('id')
            partite = self._get_partite_per_possessore(possessore_id)
            
            QApplication.restoreOverrideCursor()
            
            # Mostra dialog con dettagli completi
            self._mostra_dialog_dettagli_possessore(possessore_data, partite)
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Errore", f"Errore recupero dettagli possessore: {e}")
    
    def _mostra_partite_possessore(self):
        """Mostra lista partite del possessore con opzioni di dettaglio/modifica."""
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selezione", "Seleziona un possessore dalla tabella.")
            return
        
        row = selected_items[0].row()
        item = self.possessori_table.item(row, 0)
        possessore_data = item.data(Qt.UserRole)
        possessore_id = possessore_data.get('id')
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            partite = self._get_partite_per_possessore(possessore_id)
            QApplication.restoreOverrideCursor()
            
            if not partite:
                QMessageBox.information(self, "Partite", "Nessuna partita trovata per questo possessore.")
                return
            
            # Mostra dialog con lista partite e opzioni di azione
            self._mostra_dialog_partite_possessore(possessore_data, partite)
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Errore", f"Errore recupero partite: {e}")
    
    def _get_partite_per_possessore(self, possessore_id):
        """Recupera partite associate al possessore."""
        try:
            # Usa il metodo del db_manager se disponibile
            if hasattr(self.db_manager, 'get_partite_per_possessore'):
                return self.db_manager.get_partite_per_possessore(possessore_id)
            else:
                # Query diretta se il metodo non esiste
                conn = self.db_manager._get_connection()
                try:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                        query = """
                        SELECT DISTINCT p.*, c.nome as comune_nome, pp.titolo, pp.quota
                        FROM partita p
                        JOIN possessore_partita pp ON p.id = pp.partita_id
                        JOIN comune c ON p.comune_id = c.id
                        WHERE pp.possessore_id = %s
                        ORDER BY p.numero_partita;
                        """
                        cur.execute(query, (possessore_id,))
                        return [dict(row) for row in cur.fetchall()]
                finally:
                    self.db_manager._release_connection(conn)
        except Exception as e:
            self.logger.error(f"Errore recupero partite per possessore {possessore_id}: {e}")
            return []
    
    def _mostra_dialog_dettagli_possessore(self, possessore_data, partite):
        """Mostra dialog dettagli possessore con info partite."""
        nome = possessore_data.get('nome_completo', 'N/A')
        comune = possessore_data.get('comune_nome', 'N/A')
        paternita = possessore_data.get('paternita', 'N/A')
        
        dettagli = f"👤 POSSESSORE: {nome}\n"
        dettagli += f"🏛️ COMUNE: {comune}\n"
        dettagli += f"👨‍👦 PATERNITÀ: {paternita}\n"
        dettagli += f"📋 PARTITE ASSOCIATE: {len(partite)}\n\n"
        
        if partite:
            dettagli += "PARTITE PRINCIPALI:\n"
            for i, p in enumerate(partite[:5]):  # Prime 5 partite
                numero = p.get('numero_partita', '?')
                suffisso = p.get('suffisso_partita', '')
                tipo = p.get('tipo', 'N/A')
                titolo = p.get('titolo', 'N/A')
                quota = p.get('quota', 'N/A')
                
                partita_str = f"N.{numero}"
                if suffisso:
                    partita_str += f"/{suffisso}"
                
                dettagli += f"• {partita_str} ({tipo}) - {titolo}: {quota}\n"
            
            if len(partite) > 5:
                dettagli += f"... e altre {len(partite) - 5} partite\n"
            
            dettagli += "\nUSA 'Vedi Partite' per azioni su singole partite."
        
        QMessageBox.information(self, f"Dettagli Possessore ID {possessore_data.get('id')}", dettagli)
    
    def _mostra_dialog_partite_possessore(self, possessore_data, partite):
        """Mostra dialog con lista partite e pulsanti per azioni."""
        if not DIALOGHI_PARTITA_DISPONIBILI:
            QMessageBox.warning(self, "Funzionalità Non Disponibile", 
                               "I dialoghi per la gestione partite non sono disponibili.")
            return
        
        # Crea dialog personalizzato per selezionare partita
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Partite di {possessore_data.get('nome_completo', 'N/A')}")
        dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Info possessore
        info_label = QLabel(f"👤 {possessore_data.get('nome_completo', 'N/A')} - "
                           f"🏛️ {possessore_data.get('comune_nome', 'N/A')}")
        info_label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #f0f0f0;")
        layout.addWidget(info_label)
        
        # Tabella partite
        partite_table = QTableWidget()
        partite_table.setColumnCount(5)
        partite_table.setHorizontalHeaderLabels(["ID", "Numero", "Tipo", "Stato", "Titolo/Quota"])
        partite_table.setSelectionBehavior(QTableWidget.SelectRows)
        partite_table.setAlternatingRowColors(True)
        
        partite_table.setRowCount(len(partite))
        for row, partita in enumerate(partite):
            partite_table.setItem(row, 0, QTableWidgetItem(str(partita.get('id', ''))))
            
            numero_str = str(partita.get('numero_partita', ''))
            if partita.get('suffisso_partita'):
                numero_str += f"/{partita.get('suffisso_partita')}"
            partite_table.setItem(row, 1, QTableWidgetItem(numero_str))
            
            partite_table.setItem(row, 2, QTableWidgetItem(partita.get('tipo', '')))
            partite_table.setItem(row, 3, QTableWidgetItem(partita.get('stato', '')))
            
            titolo_quota = f"{partita.get('titolo', 'N/A')}: {partita.get('quota', 'N/A')}"
            partite_table.setItem(row, 4, QTableWidgetItem(titolo_quota))
        
        partite_table.resizeColumnsToContents()
        layout.addWidget(partite_table)
        
        # Pulsanti azioni
        buttons_layout = QHBoxLayout()
        
        btn_dettagli = QPushButton("Mostra Dettagli Partita")
        btn_dettagli.clicked.connect(lambda: self._apri_dettagli_partita_selezionata(partite_table, dialog))
        buttons_layout.addWidget(btn_dettagli)
        
        btn_modifica = QPushButton("Modifica Partita")
        btn_modifica.clicked.connect(lambda: self._apri_modifica_partita_selezionata(partite_table, dialog))
        buttons_layout.addWidget(btn_modifica)
        
        buttons_layout.addStretch()
        
        btn_chiudi = QPushButton("Chiudi")
        btn_chiudi.clicked.connect(dialog.accept)
        buttons_layout.addWidget(btn_chiudi)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec_()
    
    def _apri_dettagli_partita_selezionata(self, table, parent_dialog):
        """Apre PartitaDetailsDialog per la partita selezionata."""
        selected_items = table.selectedItems()
        if not selected_items:
            QMessageBox.warning(parent_dialog, "Selezione", "Seleziona una partita dalla tabella.")
            return
        
        row = selected_items[0].row()
        partita_id_item = table.item(row, 0)
        
        if partita_id_item and partita_id_item.text().isdigit():
            partita_id = int(partita_id_item.text())
            
            # Usa PartitaDetailsDialog esistente
            partita_details = self.db_manager.get_partita_details(partita_id)
            if partita_details:
                details_dialog = PartitaDetailsDialog(partita_details, self)
                details_dialog.exec_()
            else:
                QMessageBox.warning(parent_dialog, "Errore", 
                                   f"Impossibile recuperare dettagli partita ID {partita_id}")
        else:
            QMessageBox.warning(parent_dialog, "Errore", "ID partita non valido.")
    
    def _apri_modifica_partita_selezionata(self, table, parent_dialog):
        """Apre ModificaPartitaDialog per la partita selezionata."""
        selected_items = table.selectedItems()
        if not selected_items:
            QMessageBox.warning(parent_dialog, "Selezione", "Seleziona una partita dalla tabella.")
            return
        
        row = selected_items[0].row()
        partita_id_item = table.item(row, 0)
        
        if partita_id_item and partita_id_item.text().isdigit():
            partita_id = int(partita_id_item.text())
            
            # Usa ModificaPartitaDialog esistente
            modifica_dialog = ModificaPartitaDialog(self.db_manager, partita_id, self)
            if modifica_dialog.exec_() == QDialog.Accepted:
                QMessageBox.information(parent_dialog, "Modifica Completata", 
                                       "Modifiche alla partita salvate con successo.")
                parent_dialog.accept()  # Chiudi il dialog partite
                # Potresti voler ricaricare i risultati della ricerca qui
                self._perform_search()
        else:
            QMessageBox.warning(parent_dialog, "Errore", "ID partita non valido.")
    
    # ========================================================================
    # AZIONI SU LOCALITÀ
    # ========================================================================
    
    def _on_localita_double_click(self, item):
        """Gestisce doppio click su località - mostra dettagli."""
        self._mostra_dettagli_localita()
    
    def _mostra_dettagli_localita(self):
        """Mostra dettagli località selezionata."""
        selected_items = self.localita_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selezione", "Seleziona una località dalla tabella.")
            return
        
        row = selected_items[0].row()
        item = self.localita_table.item(row, 0)
        localita_data = item.data(Qt.UserRole)
        
        if not localita_data:
            QMessageBox.warning(self, "Errore", "Dati località non disponibili.")
            return
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            # Recupera immobili collegati alla località
            localita_id = localita_data.get('id')
            immobili = self._get_immobili_per_localita(localita_id)
            
            QApplication.restoreOverrideCursor()
            
            # Mostra dialog con dettagli
            self._mostra_dialog_dettagli_localita(localita_data, immobili)
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Errore", f"Errore recupero dettagli località: {e}")
    
    def _mostra_immobili_localita(self):
        """Mostra immobili della località selezionata."""
        selected_items = self.localita_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selezione", "Seleziona una località dalla tabella.")
            return
        
        row = selected_items[0].row()
        item = self.localita_table.item(row, 0)
        localita_data = item.data(Qt.UserRole)
        localita_id = localita_data.get('id')
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            immobili = self._get_immobili_per_localita(localita_id)
            QApplication.restoreOverrideCursor()
            
            if not immobili:
                QMessageBox.information(self, "Immobili", "Nessun immobile trovato per questa località.")
                return
            
            # Mostra dialog con lista immobili
            self._mostra_dialog_immobili_localita(localita_data, immobili)
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Errore", f"Errore recupero immobili: {e}")
    
    def _get_immobili_per_localita(self, localita_id):
        """Recupera immobili associati alla località."""
        try:
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    query = """
                    SELECT i.*, p.numero_partita, p.tipo as tipo_partita, 
                           c.nome as comune_nome, l.nome as localita_nome
                    FROM immobile i
                    JOIN partita p ON i.partita_id = p.id
                    JOIN comune c ON p.comune_id = c.id
                    LEFT JOIN localita l ON i.localita_id = l.id
                    WHERE i.localita_id = %s
                    ORDER BY p.numero_partita, i.id;
                    """
                    cur.execute(query, (localita_id,))
                    return [dict(row) for row in cur.fetchall()]
            finally:
                self.db_manager._release_connection(conn)
        except Exception as e:
            self.logger.error(f"Errore recupero immobili per località {localita_id}: {e}")
            return []
    
    def _mostra_dialog_dettagli_localita(self, localita_data, immobili):
        """Mostra dialog dettagli località."""
        nome = localita_data.get('nome', 'N/A')
        comune = localita_data.get('comune_nome', 'N/A')
        
        dettagli = f"🏘️ LOCALITÀ: {nome}\n"
        dettagli += f"🏛️ COMUNE: {comune}\n"
        dettagli += f"🏠 IMMOBILI ASSOCIATI: {len(immobili)}\n\n"
        
        if immobili:
            dettagli += "IMMOBILI PRINCIPALI:\n"
            for i, imm in enumerate(immobili[:5]):  # Primi 5 immobili
                natura = imm.get('natura', 'N/A')
                civico = imm.get('civico', '')
                partita = imm.get('numero_partita', '?')
                classificazione = imm.get('classificazione', 'N/A')
                
                civico_str = f" n.{civico}" if civico else ""
                dettagli += f"• {natura}{civico_str} (Partita {partita}) - Classe: {classificazione}\n"
            
            if len(immobili) > 5:
                dettagli += f"... e altri {len(immobili) - 5} immobili\n"
            
            dettagli += "\nUSA 'Vedi Immobili' per dettagli completi."
        
        QMessageBox.information(self, f"Dettagli Località ID {localita_data.get('id')}", dettagli)
    
    def _mostra_dialog_immobili_localita(self, localita_data, immobili):
        """Mostra dialog con lista immobili e possibilità di vedere partite."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Immobili in {localita_data.get('nome', 'N/A')}")
        dialog.setMinimumSize(700, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Info località
        info_label = QLabel(f"🏘️ {localita_data.get('nome', 'N/A')} - "
                           f"🏛️ {localita_data.get('comune_nome', 'N/A')}")
        info_label.setStyleSheet("font-weight: bold; padding: 5px; background-color: #f0f0f0;")
        layout.addWidget(info_label)
        
        # Tabella immobili
        immobili_table = QTableWidget()
        immobili_table.setColumnCount(6)
        immobili_table.setHorizontalHeaderLabels(["Partita", "Natura", "Civico", "Classe", "Consist.", "Rendita"])
        immobili_table.setSelectionBehavior(QTableWidget.SelectRows)
        immobili_table.setAlternatingRowColors(True)
        
        immobili_table.setRowCount(len(immobili))
        for row, immobile in enumerate(immobili):
            # Salva ID partita per azioni
            partita_item = QTableWidgetItem(str(immobile.get('numero_partita', '')))
            partita_item.setData(Qt.UserRole, immobile.get('partita_id'))
            immobili_table.setItem(row, 0, partita_item)
            
            immobili_table.setItem(row, 1, QTableWidgetItem(immobile.get('natura', '')))
            immobili_table.setItem(row, 2, QTableWidgetItem(str(immobile.get('civico', ''))))
            immobili_table.setItem(row, 3, QTableWidgetItem(immobile.get('classificazione', '')))
            immobili_table.setItem(row, 4, QTableWidgetItem(str(immobile.get('consistenza', ''))))
            immobili_table.setItem(row, 5, QTableWidgetItem(str(immobile.get('rendita_lire', ''))))
        
        immobili_table.resizeColumnsToContents()
        layout.addWidget(immobili_table)
        
        # Pulsanti azioni
        buttons_layout = QHBoxLayout()
        
        btn_dettagli_partita = QPushButton("Dettagli Partita")
        btn_dettagli_partita.clicked.connect(lambda: self._apri_dettagli_partita_da_immobile(immobili_table, dialog))
        buttons_layout.addWidget(btn_dettagli_partita)
        
        btn_modifica_partita = QPushButton("Modifica Partita")
        btn_modifica_partita.clicked.connect(lambda: self._apri_modifica_partita_da_immobile(immobili_table, dialog))
        buttons_layout.addWidget(btn_modifica_partita)
        
        buttons_layout.addStretch()
        
        btn_chiudi = QPushButton("Chiudi")
        btn_chiudi.clicked.connect(dialog.accept)
        buttons_layout.addWidget(btn_chiudi)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec_()
    
    def _apri_dettagli_partita_da_immobile(self, table, parent_dialog):
        """Apre dettagli partita dall'immobile selezionato."""
        selected_items = table.selectedItems()
        if not selected_items:
            QMessageBox.warning(parent_dialog, "Selezione", "Seleziona un immobile dalla tabella.")
            return
        
        row = selected_items[0].row()
        partita_item = table.item(row, 0)
        partita_id = partita_item.data(Qt.UserRole)
        
        if partita_id and DIALOGHI_PARTITA_DISPONIBILI:
            partita_details = self.db_manager.get_partita_details(partita_id)
            if partita_details:
                details_dialog = PartitaDetailsDialog(partita_details, self)
                details_dialog.exec_()
            else:
                QMessageBox.warning(parent_dialog, "Errore", f"Impossibile recuperare dettagli partita ID {partita_id}")
        else:
            QMessageBox.warning(parent_dialog, "Errore", "ID partita non valido o dialoghi non disponibili.")
    
    def _apri_modifica_partita_da_immobile(self, table, parent_dialog):
        """Apre modifica partita dall'immobile selezionato."""
        selected_items = table.selectedItems()
        if not selected_items:
            QMessageBox.warning(parent_dialog, "Selezione", "Seleziona un immobile dalla tabella.")
            return
        
        row = selected_items[0].row()
        partita_item = table.item(row, 0)
        partita_id = partita_item.data(Qt.UserRole)
        
        if partita_id and DIALOGHI_PARTITA_DISPONIBILI:
            modifica_dialog = ModificaPartitaDialog(self.db_manager, partita_id, self)
            if modifica_dialog.exec_() == QDialog.Accepted:
                QMessageBox.information(parent_dialog, "Modifica Completata", 
                                       "Modifiche alla partita salvate con successo.")
                parent_dialog.accept()
                self._perform_search()  # Ricarica risultati
        else:
            QMessageBox.warning(parent_dialog, "Errore", "ID partita non valido o dialoghi non disponibili.")

# ========================================================================
# FUNZIONE DI INTEGRAZIONE CON MAIN WINDOW
# ========================================================================

def add_enhanced_fuzzy_search_tab_to_main_window(main_window):
    """
    Aggiunge il tab ricerca fuzzy potenziato alla finestra principale.
    
    Args:
        main_window: Istanza CatastoMainWindow
        
    Returns:
        bool: True se aggiunto con successo
    """
    try:
        if not hasattr(main_window, 'db_manager') or not main_window.db_manager:
            print("❌ DB manager non disponibile per ricerca fuzzy")
            return False
        
        # Crea il widget ricerca fuzzy
        fuzzy_widget = CompactFuzzySearchWidget(main_window.db_manager, main_window)
        
        # Aggiunge il tab
        main_window.tabs.addTab(fuzzy_widget, "🔍 Ricerca Fuzzy")
        
        print("✅ Tab Ricerca Fuzzy Potenziato aggiunto con successo")
        return True
        
    except Exception as e:
        print(f"❌ Errore aggiunta tab ricerca fuzzy: {e}")
        import traceback
        traceback.print_exc()
        return False

# Alias per compatibilità
add_optimized_fuzzy_search_tab_to_main_window = add_enhanced_fuzzy_search_tab_to_main_window