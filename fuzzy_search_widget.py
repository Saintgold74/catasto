# ========================================================================
# WIDGET RICERCA FUZZY COMPLETO - VERSIONE FINALE
# File: fuzzy_search_widget.py
# ========================================================================

"""
Widget completo per ricerca fuzzy con indici GIN, layout ottimizzato 
e collegamento ai dettagli delle partite.

Funzionalità:
- Ricerca fuzzy in tempo reale con tolleranza errori
- Layout ottimizzato per massimizzare spazio risultati
- Collegamento completo ai dettagli di possessori e località
- Integrazione con DettaglioPartitaDialog esistente
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

# Importa il dialog di dettaglio partita esistente
try:
    from gui_widgets import DettaglioPartitaDialog
except ImportError:
    print("ATTENZIONE: DettaglioPartitaDialog non trovato in gui_widgets")
    DettaglioPartitaDialog = None

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
# HELPER CLASS PER GESTIONE PARTITE E IMMOBILI COLLEGATI
# ========================================================================

class PartiteCollegate:
    """Classe helper per gestire le partite collegate ai possessori/località."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger("CatastoGUI")
    
    def get_partite_per_possessore(self, possessore_id: int):
        """Recupera tutte le partite associate a un possessore."""
        try:
            # Usando il metodo esistente del db_manager
            partite = self.db_manager.get_partite_per_possessore(possessore_id)
            self.logger.info(f"Trovate {len(partite)} partite per possessore {possessore_id}")
            return partite
        except Exception as e:
            self.logger.error(f"Errore recupero partite per possessore {possessore_id}: {e}")
            return []
    
    def get_immobili_per_localita(self, localita_id: int):
        """Recupera tutti gli immobili in una località."""
        try:
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    query = """
                    SELECT 
                        i.id as immobile_id,
                        i.natura,
                        i.numero_piani,
                        i.numero_vani,
                        i.consistenza,
                        i.classificazione,
                        p.id as partita_id,
                        p.numero_partita,
                        p.tipo as tipo_partita,
                        c.nome as comune_nome
                    FROM immobile i
                    JOIN partita p ON i.partita_id = p.id
                    JOIN comune c ON p.comune_id = c.id
                    WHERE i.localita_id = %s
                    ORDER BY p.numero_partita, i.natura
                    """
                    cur.execute(query, (localita_id,))
                    results = cur.fetchall()
                    immobili = [dict(row) for row in results] if results else []
                    
                    self.logger.info(f"Trovati {len(immobili)} immobili per località {localita_id}")
                    return immobili
            finally:
                self.db_manager._release_connection(conn)
        except Exception as e:
            self.logger.error(f"Errore recupero immobili per località {localita_id}: {e}")
            return []

# ========================================================================
# DIALOG DETTAGLI POSSESSORE
# ========================================================================

class DettagliPossessoreDialog(QDialog):
    """Dialog per mostrare i dettagli completi di un possessore con le sue partite."""
    
    def __init__(self, possessore_data, partite_collegate, db_manager, parent=None):
        super().__init__(parent)
        self.possessore_data = possessore_data
        self.partite_collegate = partite_collegate
        self.db_manager = db_manager
        self.setupUI()
        
    def setupUI(self):
        nome = self.possessore_data.get('nome_completo', 'N/A')
        self.setWindowTitle(f"Dettagli Possessore - {nome}")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # === INFORMAZIONI POSSESSORE ===
        info_group = QGroupBox("Informazioni Possessore")
        info_layout = QFormLayout(info_group)
        
        info_layout.addRow("ID:", QLabel(str(self.possessore_data.get('id', 'N/A'))))
        info_layout.addRow("Nome Completo:", QLabel(nome))
        
        cognome_nome = self.possessore_data.get('cognome_nome', 'N/A')
        if cognome_nome and cognome_nome != 'N/A':
            info_layout.addRow("Cognome Nome:", QLabel(cognome_nome))
        
        paternita = self.possessore_data.get('paternita', 'N/A')
        if paternita and paternita != 'N/A':
            info_layout.addRow("Paternità:", QLabel(paternita))
            
        info_layout.addRow("Comune:", QLabel(self.possessore_data.get('comune_nome', 'N/A')))
        info_layout.addRow("Numero Partite:", QLabel(str(len(self.partite_collegate))))
        
        layout.addWidget(info_group)
        
        # === PARTITE COLLEGATE ===
        partite_group = QGroupBox(f"Partite Collegate ({len(self.partite_collegate)})")
        partite_layout = QVBoxLayout(partite_group)
        
        if self.partite_collegate:
            self.partite_table = QTableWidget()
            self.partite_table.setColumnCount(6)
            self.partite_table.setHorizontalHeaderLabels([
                "ID", "Numero", "Tipo", "Comune", "Titolo", "Quota"
            ])
            
            # Popola tabella partite
            self.partite_table.setRowCount(len(self.partite_collegate))
            for row, partita in enumerate(self.partite_collegate):
                # ID Partita
                id_item = QTableWidgetItem(str(partita.get('partita_id', '')))
                id_item.setData(Qt.UserRole, partita.get('partita_id'))
                self.partite_table.setItem(row, 0, id_item)
                
                # Numero partita
                numero = str(partita.get('numero_partita', ''))
                suffisso = partita.get('suffisso_partita', '')
                if suffisso:
                    numero += f" ({suffisso})"
                self.partite_table.setItem(row, 1, QTableWidgetItem(numero))
                
                # Altri campi
                self.partite_table.setItem(row, 2, QTableWidgetItem(partita.get('tipo_partita', '')))
                self.partite_table.setItem(row, 3, QTableWidgetItem(partita.get('comune_nome', '')))
                self.partite_table.setItem(row, 4, QTableWidgetItem(partita.get('titolo_possesso', '')))
                self.partite_table.setItem(row, 5, QTableWidgetItem(partita.get('quota_possesso', '')))
            
            # Configurazione tabella
            self.partite_table.resizeColumnsToContents()
            self.partite_table.setAlternatingRowColors(True)
            self.partite_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.partite_table.setSortingEnabled(True)
            self.partite_table.doubleClicked.connect(self.apri_dettaglio_partita)
            
            partite_layout.addWidget(self.partite_table)
            
            # Pulsanti azioni
            actions_layout = QHBoxLayout()
            
            self.btn_apri_partita = QPushButton("📋 Apri Dettaglio Partita")
            self.btn_apri_partita.clicked.connect(self.apri_dettaglio_partita_selezionata)
            self.btn_apri_partita.setEnabled(False)
            
            self.partite_table.itemSelectionChanged.connect(
                lambda: self.btn_apri_partita.setEnabled(len(self.partite_table.selectedItems()) > 0)
            )
            
            actions_layout.addWidget(self.btn_apri_partita)
            actions_layout.addStretch()
            
            partite_layout.addLayout(actions_layout)
            
        else:
            no_partite_label = QLabel("Nessuna partita collegata a questo possessore.")
            no_partite_label.setAlignment(Qt.AlignCenter)
            no_partite_label.setStyleSheet("color: #666; font-style: italic;")
            partite_layout.addWidget(no_partite_label)
        
        layout.addWidget(partite_group)
        
        # === PULSANTI FINALI ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
    def apri_dettaglio_partita(self):
        """Apre il dettaglio della partita con doppio click."""
        current_row = self.partite_table.currentRow()
        if current_row >= 0:
            item = self.partite_table.item(current_row, 0)
            if item:
                partita_id = item.data(Qt.UserRole)
                self._apri_dettaglio_partita_id(partita_id)
    
    def apri_dettaglio_partita_selezionata(self):
        """Apre il dettaglio della partita selezionata dal pulsante."""
        current_row = self.partite_table.currentRow()
        if current_row >= 0:
            item = self.partite_table.item(current_row, 0)
            if item:
                partita_id = item.data(Qt.UserRole)
                self._apri_dettaglio_partita_id(partita_id)
    
    def _apri_dettaglio_partita_id(self, partita_id):
        """Apre il dialog di dettaglio partita."""
        if DettaglioPartitaDialog and self.db_manager:
            try:
                dettaglio_dialog = DettaglioPartitaDialog(
                    self.db_manager, 
                    partita_id, 
                    parent=self
                )
                dettaglio_dialog.exec_()
            except Exception as e:
                QMessageBox.critical(
                    self, "Errore", 
                    f"Impossibile aprire i dettagli della partita {partita_id}:\n{e}"
                )
        else:
            QMessageBox.information(
                self, "Dettaglio Partita", 
                f"Apertura dettagli partita ID: {partita_id}\n\n"
                f"DettaglioPartitaDialog: {'Disponibile' if DettaglioPartitaDialog else 'Non disponibile'}\n"
                f"DB Manager: {'Disponibile' if self.db_manager else 'Non disponibile'}"
            )

# ========================================================================
# DIALOG DETTAGLI LOCALITÀ
# ========================================================================

class DettagliLocalitaDialog(QDialog):
    """Dialog per mostrare i dettagli di una località con gli immobili collegati."""
    
    def __init__(self, localita_data, immobili_collegati, db_manager, parent=None):
        super().__init__(parent)
        self.localita_data = localita_data
        self.immobili_collegati = immobili_collegati
        self.db_manager = db_manager
        self.setupUI()
        
    def setupUI(self):
        nome_localita = self.localita_data.get('nome', 'N/A')
        civico = self.localita_data.get('civico', '')
        nome_completo = f"{nome_localita} {civico}" if civico else nome_localita
        
        self.setWindowTitle(f"Dettagli Località - {nome_completo}")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # === INFORMAZIONI LOCALITÀ ===
        info_group = QGroupBox("Informazioni Località")
        info_layout = QFormLayout(info_group)
        
        info_layout.addRow("ID:", QLabel(str(self.localita_data.get('id', 'N/A'))))
        info_layout.addRow("Nome:", QLabel(nome_localita))
        info_layout.addRow("Tipo:", QLabel(self.localita_data.get('tipo', 'N/A')))
        if civico:
            info_layout.addRow("Civico:", QLabel(str(civico)))
        info_layout.addRow("Comune:", QLabel(self.localita_data.get('comune_nome', 'N/A')))
        info_layout.addRow("Numero Immobili:", QLabel(str(len(self.immobili_collegati))))
        
        layout.addWidget(info_group)
        
        # === IMMOBILI COLLEGATI ===
        immobili_group = QGroupBox(f"Immobili in questa Località ({len(self.immobili_collegati)})")
        immobili_layout = QVBoxLayout(immobili_group)
        
        if self.immobili_collegati:
            self.immobili_table = QTableWidget()
            self.immobili_table.setColumnCount(8)
            self.immobili_table.setHorizontalHeaderLabels([
                "ID Imm.", "Natura", "Piani", "Vani", "Classificazione", "Partita", "Tipo", "Comune"
            ])
            
            # Popola tabella immobili
            self.immobili_table.setRowCount(len(self.immobili_collegati))
            for row, immobile in enumerate(self.immobili_collegati):
                # ID Immobile
                id_item = QTableWidgetItem(str(immobile.get('immobile_id', '')))
                id_item.setData(Qt.UserRole, immobile.get('partita_id'))  # Salva partita_id per apertura
                self.immobili_table.setItem(row, 0, id_item)
                
                # Dati immobile
                self.immobili_table.setItem(row, 1, QTableWidgetItem(immobile.get('natura', '')))
                self.immobili_table.setItem(row, 2, QTableWidgetItem(str(immobile.get('numero_piani', '') or '')))
                self.immobili_table.setItem(row, 3, QTableWidgetItem(str(immobile.get('numero_vani', '') or '')))
                self.immobili_table.setItem(row, 4, QTableWidgetItem(immobile.get('classificazione', '')))
                
                # Partita
                numero_partita = immobile.get('numero_partita', '')
                self.immobili_table.setItem(row, 5, QTableWidgetItem(f"N.{numero_partita}"))
                
                # Tipo partita e comune
                self.immobili_table.setItem(row, 6, QTableWidgetItem(immobile.get('tipo_partita', '')))
                self.immobili_table.setItem(row, 7, QTableWidgetItem(immobile.get('comune_nome', '')))
            
            # Configurazione tabella
            self.immobili_table.resizeColumnsToContents()
            self.immobili_table.setAlternatingRowColors(True)
            self.immobili_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.immobili_table.setSortingEnabled(True)
            self.immobili_table.doubleClicked.connect(self.apri_dettaglio_partita_da_immobile)
            
            immobili_layout.addWidget(self.immobili_table)
            
            # Pulsanti azioni
            actions_layout = QHBoxLayout()
            
            self.btn_apri_partita = QPushButton("📋 Apri Partita dell'Immobile")
            self.btn_apri_partita.clicked.connect(self.apri_dettaglio_partita_selezionata)
            self.btn_apri_partita.setEnabled(False)
            
            self.immobili_table.itemSelectionChanged.connect(
                lambda: self.btn_apri_partita.setEnabled(len(self.immobili_table.selectedItems()) > 0)
            )
            
            actions_layout.addWidget(self.btn_apri_partita)
            actions_layout.addStretch()
            
            immobili_layout.addLayout(actions_layout)
            
        else:
            no_immobili_label = QLabel("Nessun immobile trovato in questa località.")
            no_immobili_label.setAlignment(Qt.AlignCenter)
            no_immobili_label.setStyleSheet("color: #666; font-style: italic;")
            immobili_layout.addWidget(no_immobili_label)
        
        layout.addWidget(immobili_group)
        
        # === PULSANTI FINALI ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
    def apri_dettaglio_partita_da_immobile(self):
        """Apre il dettaglio della partita dell'immobile con doppio click."""
        current_row = self.immobili_table.currentRow()
        if current_row >= 0:
            item = self.immobili_table.item(current_row, 0)
            if item:
                partita_id = item.data(Qt.UserRole)
                self._apri_dettaglio_partita_id(partita_id)
    
    def apri_dettaglio_partita_selezionata(self):
        """Apre il dettaglio della partita dell'immobile selezionato."""
        current_row = self.immobili_table.currentRow()
        if current_row >= 0:
            item = self.immobili_table.item(current_row, 0)
            if item:
                partita_id = item.data(Qt.UserRole)
                self._apri_dettaglio_partita_id(partita_id)
    
    def _apri_dettaglio_partita_id(self, partita_id):
        """Apre il dialog di dettaglio partita."""
        if DettaglioPartitaDialog and self.db_manager:
            try:
                dettaglio_dialog = DettaglioPartitaDialog(
                    self.db_manager, 
                    partita_id, 
                    parent=self
                )
                dettaglio_dialog.exec_()
            except Exception as e:
                QMessageBox.critical(
                    self, "Errore", 
                    f"Impossibile aprire i dettagli della partita {partita_id}:\n{e}"
                )
        else:
            QMessageBox.information(
                self, "Dettaglio Partita", 
                f"Apertura dettagli partita ID: {partita_id}\n\n"
                f"DettaglioPartitaDialog: {'Disponibile' if DettaglioPartitaDialog else 'Non disponibile'}\n"
                f"DB Manager: {'Disponibile' if self.db_manager else 'Non disponibile'}"
            )

# ========================================================================
# WIDGET PRINCIPALE RICERCA FUZZY
# ========================================================================

class FuzzySearchWidget(QWidget):
    """
    Widget completo per ricerca fuzzy con layout ottimizzato 
    e collegamento ai dettagli delle partite.
    """
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.gin_search = None
        self.search_worker = None
        self.partite_helper = None
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
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # === HEADER COMPATTO ===
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        title_label = QLabel("🔍 Ricerca Avanzata")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        self.status_label = QLabel("Pronto")
        self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 10px;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        
        main_layout.addLayout(header_layout)
        
        # === CONTROLLI COMPATTI ===
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel)
        controls_frame.setMaximumHeight(80)
        
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setSpacing(3)
        controls_layout.setContentsMargins(8, 5, 8, 5)
        
        # Prima riga: Campo ricerca
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
        
        # Seconda riga: Controlli
        controls_row = QHBoxLayout()
        controls_row.setSpacing(15)
        
        # Precisione
        precision_group = QHBoxLayout()
        precision_group.addWidget(QLabel("Precisione:"))
        
        self.precision_slider = QSlider(Qt.Horizontal)
        self.precision_slider.setRange(10, 80)
        self.precision_slider.setValue(30)
        self.precision_slider.valueChanged.connect(self._update_precision_label)
        self.precision_slider.setMaximumWidth(100)
        
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
        
        # Pulsante verifica indici
        self.check_indices_button = QPushButton("🔧")
        self.check_indices_button.setMaximumSize(QSize(30, 25))
        self.check_indices_button.setToolTip("Verifica Indici GIN")
        self.check_indices_button.clicked.connect(self._check_gin_indices)
        
        # Assembla controlli
        controls_row.addLayout(precision_group)
        controls_row.addWidget(QLabel("|"))
        controls_row.addWidget(self.search_possessori_cb)
        controls_row.addWidget(self.search_localita_cb)
        controls_row.addWidget(QLabel("|"))
        controls_row.addLayout(limit_group)
        controls_row.addStretch()
        controls_row.addWidget(self.check_indices_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(3)
        
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
        
        # Barra statistiche
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
        
        # === TAB RISULTATI ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setTabPosition(QTabWidget.North)
        
        # Tab Possessori
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(6)
        self.possessori_table.setHorizontalHeaderLabels([
            "ID", "Nome Completo", "Comune", "Similarità", "Partite", "Azioni"
        ])
        
        # Configurazione tabella possessori
        header = self.possessori_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Nome
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Comune
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Similarità
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Partite
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Azioni
        
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.doubleClicked.connect(self._on_possessore_double_click)
        self.possessori_table.setShowGrid(False)
        self.possessori_table.verticalHeader().setVisible(False)
        
        self.results_tabs.addTab(self.possessori_table, "👥 Possessori")
        
        # Tab Località
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
        
        # === DEBUG AREA RIDOTTA ===
        debug_frame = QFrame()
        debug_frame.setMaximumHeight(60)
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
        
        # === LAYOUT FINALE ===
        main_layout.addWidget(results_frame, 1)  # Espandibile
        main_layout.addWidget(debug_frame, 0)    # Fisso
        
        # Focus iniziale
        self.search_edit.setFocus()
        
    def setup_gin_extension(self):
        """Inizializza l'estensione GIN e helper partite."""
        try:
            if not self.db_manager:
                self.debug_text.append("❌ Database manager non disponibile")
                self.status_label.setText("DB non disponibile")
                self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 10px;")
                return
                
            self.gin_search = extend_db_manager_with_gin(self.db_manager)
            self.partite_helper = PartiteCollegate(self.db_manager)
            
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
        
        if precision < 0.25:
            color = "red"
        elif precision < 0.5:
            color = "blue"
        else:
            color = "green"
            
        self.precision_label.setStyleSheet(f"font-weight: bold; color: {color}; font-size: 10px;")
        
    def _on_search_text_changed(self, text):
        """Gestisce cambio testo con debouncing."""
        if len(text) >= 3:
            self.search_timer.stop()
            self.search_timer.start(600)
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
        
        # Aggiorna statistiche
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
        
        # Abilita export
        self.export_button.setEnabled(total > 0)
        
        # Status
        self.status_label.setText(f"✓ {total} risultati")
        self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 10px;")
        
        self.debug_text.append(f"✅ '{results.get('query_text', '')}': {total} risultati")
        
    def _populate_possessori_table(self, possessori):
        """Popola tabella possessori."""
        self.possessori_table.setRowCount(len(possessori))
        
        for row, p in enumerate(possessori):
            # ID
            id_item = QTableWidgetItem(str(p.get('id', '')))
            id_item.setData(Qt.UserRole, p)
            id_item.setTextAlignment(Qt.AlignCenter)
            self.possessori_table.setItem(row, 0, id_item)
            
            # Nome completo con tooltip
            nome_item = QTableWidgetItem(p.get('nome_completo', ''))
            tooltip_parts = []
            if p.get('cognome_nome'):
                tooltip_parts.append(f"Cognome: {p.get('cognome_nome')}")
            if p.get('paternita'):
                tooltip_parts.append(f"Paternità: {p.get('paternita')}")
            if tooltip_parts:
                nome_item.setToolTip("\n".join(tooltip_parts))
            self.possessori_table.setItem(row, 1, nome_item)
            
            # Comune
            self.possessori_table.setItem(row, 2, QTableWidgetItem(p.get('comune_nome', '')))
            
            # Similarità con colore
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
            
            # Azioni
            action_item = QTableWidgetItem("👁️")
            action_item.setTextAlignment(Qt.AlignCenter)
            action_item.setToolTip("Doppio click per dettagli")
            self.possessori_table.setItem(row, 5, action_item)
            
    def _populate_localita_table(self, localita):
        """Popola tabella località."""
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
            
    def _on_possessore_double_click(self, index):
        """Gestisce doppio click su possessore con dettagli completi."""
        item = self.possessori_table.item(index.row(), 0)
        if item:
            possessore_data = item.data(Qt.UserRole)
            possessore_id = possessore_data.get('id')
            
            if not self.partite_helper:
                QMessageBox.warning(self, "Errore", "Helper partite non disponibile")
                return
            
            try:
                # Recupera le partite collegate
                QApplication.setOverrideCursor(Qt.WaitCursor)
                partite_collegate = self.partite_helper.get_partite_per_possessore(possessore_id)
                QApplication.restoreOverrideCursor()
                
                # Apre il dialog dettagliato
                dettagli_dialog = DettagliPossessoreDialog(
                    possessore_data, 
                    partite_collegate,
                    self.db_manager,
                    parent=self
                )
                dettagli_dialog.exec_()
                
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(
                    self, "Errore", 
                    f"Errore recupero dettagli possessore {possessore_id}:\n{e}"
                )
            
    def _on_localita_double_click(self, index):
        """Gestisce doppio click su località con dettagli completi."""
        item = self.localita_table.item(index.row(), 0)
        if item:
            localita_data = item.data(Qt.UserRole)
            localita_id = localita_data.get('id')
            
            if not self.partite_helper:
                QMessageBox.warning(self, "Errore", "Helper partite non disponibile")
                return
            
            try:
                # Recupera gli immobili collegati
                QApplication.setOverrideCursor(Qt.WaitCursor)
                immobili_collegati = self.partite_helper.get_immobili_per_localita(localita_id)
                QApplication.restoreOverrideCursor()
                
                # Apre il dialog dettagliato
                dettagli_dialog = DettagliLocalitaDialog(
                    localita_data, 
                    immobili_collegati,
                    self.db_manager,
                    parent=self
                )
                dettagli_dialog.exec_()
                
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(
                    self, "Errore", 
                    f"Errore recupero dettagli località {localita_id}:\n{e}"
                )
    
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
                
                details = []
                for idx in indices:
                    details.append(f"• {idx.get('indexname', 'N/A')}: {idx.get('index_size', 'N/A')}")
                
                QMessageBox.information(
                    self, "Stato Indici GIN", 
                    f"✅ Trovati {len(indices)} indici GIN attivi:\n\n" + "\n".join(details)
                )
            else:
                self.indices_status_label.setText("❌ Nessun indice")
                self.debug_text.append("❌ Nessun indice GIN")
                QMessageBox.warning(
                    self, "Indici GIN", 
                    "❌ Nessun indice GIN trovato!\n\n"
                    "La ricerca fuzzy potrebbe essere lenta."
                )
                
        except Exception as e:
            self.indices_status_label.setText("❌ Errore")
            self.debug_text.append(f"❌ Errore indici: {e}")
            
    def _export_results(self):
        """Esporta risultati in formato testo."""
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

# ========================================================================
# FUNZIONE DI INTEGRAZIONE NELLA MAIN WINDOW
# ========================================================================

def add_fuzzy_search_tab_to_main_window(main_window):
    """
    Aggiunge il tab di ricerca fuzzy completo alla finestra principale.
    
    Args:
        main_window: Istanza di CatastoMainWindow
    """
    try:
        if not hasattr(main_window, 'db_manager') or not main_window.db_manager:
            main_window.logger.warning("Database manager non disponibile per ricerca fuzzy")
            return False
            
        # Crea il widget completo
        fuzzy_widget = FuzzySearchWidget(main_window.db_manager, main_window)
        
        # Aggiunge al TabWidget principale
        tab_index = main_window.tabs.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
        
        main_window.logger.info(f"Tab Ricerca Fuzzy Completo aggiunto all'indice {tab_index}")
        return True
        
    except Exception as e:
        main_window.logger.error(f"Errore aggiunta tab ricerca fuzzy completo: {e}")
        return False

# ========================================================================
# ALIAS PER COMPATIBILITÀ
# ========================================================================

# Mantieni compatibilità con import precedenti
add_optimized_fuzzy_search_tab_to_main_window = add_fuzzy_search_tab_to_main_window
add_enhanced_fuzzy_search_tab_to_main_window = add_fuzzy_search_tab_to_main_window

# ========================================================================
# ESEMPIO DI UTILIZZO STANDALONE
# ========================================================================

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Simula un database manager per test
    class MockDBManager:
        def __init__(self):
            self.schema = "catasto"
    
    widget = FuzzySearchWidget(MockDBManager())
    widget.show()
    
    sys.exit(app.exec_())
