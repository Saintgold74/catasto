# ========================================================================
# WIDGET RICERCA FUZZY SEMPLIFICATO - SENZA DROPDOWN TIPOLOGIE
# File: fuzzy_search_widget_simplified.py
# ========================================================================

"""
Widget ricerca fuzzy semplificato che mostra sempre tutti i tipi di risultati
in tab separati, senza dropdown per selezionare tipologie specifiche.

Funzionalità:
- Ricerca unificata in possessori, località e variazioni
- Layout compatto ottimizzato
- Tab separati per ogni tipo di risultato
- Gestione automatica della visibilità dei tab in base ai risultati
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QLabel, QSlider, QCheckBox, 
    QTabWidget, QProgressBar, QFrame, QHeaderView, QMessageBox,
    QComboBox, QSizePolicy, QTextEdit, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor
import time
import logging

# Importa l'estensione GIN
try:
    from catasto_gin_extension import extend_db_manager_with_gin
except ImportError:
    print("ATTENZIONE: catasto_gin_extension.py non trovato.")

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
        """Esegue la ricerca unificata in background."""
        try:
            self.progress_updated.emit(20)
            
            # Imposta soglia
            threshold = self.options.get('similarity_threshold', 0.3)
            self.gin_search.set_similarity_threshold(threshold)
            
            self.progress_updated.emit(40)
            
            # Ricerca unificata sempre su tutti i tipi
            results = self.gin_search.search_combined_fuzzy(
                self.query_text,
                search_possessori=True,  # Sempre attivo
                search_localita=True,   # Sempre attivo
                similarity_threshold=threshold,
                max_possessori=self.options.get('max_results', 50),
                max_localita=self.options.get('max_results', 50) // 2
            )
            
            # Se esiste la ricerca variazioni, aggiungila
            if hasattr(self.gin_search, 'search_variazioni_fuzzy'):
                self.progress_updated.emit(70)
                variazioni = self.gin_search.search_variazioni_fuzzy(
                    self.query_text, threshold, self.options.get('max_results', 50) // 3
                )
                results['variazioni'] = variazioni
            else:
                results['variazioni'] = []
            
            self.progress_updated.emit(100)
            self.results_ready.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class SimplifiedFuzzySearchWidget(QWidget):
    """Widget ricerca fuzzy semplificato senza dropdown tipologie."""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.gin_search = None
        self.search_worker = None
        self.current_results = {}
        self.logger = logging.getLogger("CatastoGUI")
        
        # Timer per debouncing
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        
        self.setupUI()
        self.setup_gin_extension()
        
    def setupUI(self):
        """Configura interfaccia utente semplificata."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)
        
        # === HEADER COMPATTO ===
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🔍 Ricerca Avanzata")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        self.status_label = QLabel("Inserisci almeno 3 caratteri per iniziare")
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        
        main_layout.addLayout(header_layout)
        
        # === CONTROLLI DI RICERCA COMPATTI ===
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel)
        controls_frame.setMaximumHeight(70)
        
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 5, 8, 5)
        controls_layout.setSpacing(5)
        
        # Prima riga: Campo ricerca + Clear
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Cerca:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Nome, cognome, località, tipo variazione... (min 3 caratteri)")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        search_row.addWidget(self.search_edit)
        
        self.clear_button = QPushButton("✕")
        self.clear_button.setMaximumSize(QSize(25, 25))
        self.clear_button.setToolTip("Pulisci ricerca")
        self.clear_button.clicked.connect(self._clear_search)
        search_row.addWidget(self.clear_button)
        
        controls_layout.addLayout(search_row)
        
        # Seconda riga: Precisione + Limite risultati + Export + Indici
        options_row = QHBoxLayout()
        
        # Precisione
        options_row.addWidget(QLabel("Precisione:"))
        self.precision_slider = QSlider(Qt.Horizontal)
        self.precision_slider.setRange(10, 80)
        self.precision_slider.setValue(30)
        self.precision_slider.setMaximumWidth(100)
        self.precision_slider.valueChanged.connect(self._update_precision_label)
        options_row.addWidget(self.precision_slider)
        
        self.precision_label = QLabel("0.30")
        self.precision_label.setMinimumWidth(35)
        self.precision_label.setStyleSheet("font-weight: bold; color: blue; font-size: 10px;")
        options_row.addWidget(self.precision_label)
        
        options_row.addWidget(QLabel("|"))  # Separatore
        
        # Max risultati
        options_row.addWidget(QLabel("Max:"))
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["20", "50", "100", "200"])
        self.max_results_combo.setCurrentText("50")
        self.max_results_combo.setMaximumWidth(60)
        options_row.addWidget(self.max_results_combo)
        
        options_row.addWidget(QLabel("|"))  # Separatore
        
        # Pulsante export
        self.export_button = QPushButton("📤")
        self.export_button.setMaximumSize(QSize(30, 25))
        self.export_button.setToolTip("Esporta Risultati")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_results)
        options_row.addWidget(self.export_button)
        
        # Pulsante verifica indici
        self.check_indices_button = QPushButton("🔧")
        self.check_indices_button.setMaximumSize(QSize(30, 25))
        self.check_indices_button.setToolTip("Verifica Indici GIN")
        self.check_indices_button.clicked.connect(self._check_gin_indices)
        options_row.addWidget(self.check_indices_button)
        
        options_row.addStretch()
        controls_layout.addLayout(options_row)
        
        main_layout.addWidget(controls_frame)
        
        # === PROGRESS BAR ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # === AREA RISULTATI CON TAB ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)
        
        # Tab Possessori
        self.possessori_table = self._create_possessori_table()
        self.results_tabs.addTab(self.possessori_table, "👥 Possessori")
        
        # Tab Località
        self.localita_table = self._create_localita_table()
        self.results_tabs.addTab(self.localita_table, "🏠 Località")
        
        # Tab Variazioni (inizialmente nascosto)
        self.variazioni_table = self._create_variazioni_table()
        self.variazioni_tab_index = self.results_tabs.addTab(self.variazioni_table, "📋 Variazioni")
        self.results_tabs.setTabVisible(self.variazioni_tab_index, False)
        
        main_layout.addWidget(self.results_tabs)
        
        # === STATISTICHE COMPATTE ===
        self.stats_label = QLabel("Inserire almeno 3 caratteri per iniziare")
        self.stats_label.setStyleSheet("color: #666; font-size: 10px; padding: 3px;")
        main_layout.addWidget(self.stats_label)
        
        # Focus iniziale
        self.search_edit.setFocus()
    
    def _create_possessori_table(self):
        """Crea tabella possessori."""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Nome Completo", "Comune", "N. Partite", "Similarità"])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Imposta resize mode
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        # Connetti doppio click
        table.itemDoubleClicked.connect(self._on_possessore_double_click)
        
        return table
    
    def _create_localita_table(self):
        """Crea tabella località."""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Nome Località", "Comune", "N. Immobili", "Similarità"])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Imposta resize mode
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        # Connetti doppio click
        table.itemDoubleClicked.connect(self._on_localita_double_click)
        
        return table
    
    def _create_variazioni_table(self):
        """Crea tabella variazioni."""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["ID", "Tipo", "Data", "Descrizione", "Similarità"])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Imposta resize mode
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        # Connetti doppio click
        table.itemDoubleClicked.connect(self._on_variazione_double_click)
        
        return table
    
    def setup_gin_extension(self):
        """Inizializza estensione GIN."""
        try:
            self.gin_search = extend_db_manager_with_gin(self.db_manager)
            if self.gin_search:
                self.status_label.setText("✅ Sistema ricerca fuzzy pronto")
                self.status_label.setStyleSheet("color: green; font-size: 10px;")
            else:
                self.status_label.setText("❌ Errore inizializzazione ricerca fuzzy")
                self.status_label.setStyleSheet("color: red; font-size: 10px;")
        except Exception as e:
            self.logger.error(f"Errore setup GIN: {e}")
            self.status_label.setText("❌ Errore estensione GIN")
            self.status_label.setStyleSheet("color: red; font-size: 10px;")
    
    def _on_search_text_changed(self):
        """Gestisce cambio testo ricerca."""
        text = self.search_edit.text().strip()
        if len(text) >= 3:
            self.search_timer.stop()
            self.search_timer.start(500)  # Debounce 500ms
        else:
            self._clear_results()
    
    def _update_precision_label(self, value):
        """Aggiorna label precisione."""
        self.precision_label.setText(f"{value/100:.2f}")
        # Riavvia ricerca se c'è del testo
        if len(self.search_edit.text().strip()) >= 3:
            self.search_timer.stop()
            self.search_timer.start(300)
    
    def _perform_search(self):
        """Esegue ricerca fuzzy unificata."""
        query_text = self.search_edit.text().strip()
        
        if len(query_text) < 3:
            return
            
        if not self.gin_search:
            QMessageBox.warning(self, "Errore", "Estensione ricerca fuzzy non disponibile")
            return
        
        # Prepara opzioni (sempre tutti i tipi)
        max_results = int(self.max_results_combo.currentText())
        options = {
            'similarity_threshold': self.precision_slider.value() / 100.0,
            'max_results': max_results
        }
        
        # Avvia ricerca in background
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ricerca in corso...")
        self.status_label.setStyleSheet("color: blue; font-size: 10px;")
        
        self.search_worker = FuzzySearchWorker(self.gin_search, query_text, options)
        self.search_worker.results_ready.connect(self._display_results)
        self.search_worker.error_occurred.connect(self._handle_search_error)
        self.search_worker.progress_updated.connect(self.progress_bar.setValue)
        self.search_worker.start()
    
    def _display_results(self, results):
        """Visualizza risultati unificati."""
        try:
            self.current_results = results
            
            # Popola tabelle
            possessori = results.get('possessori', [])
            localita = results.get('localita', [])
            variazioni = results.get('variazioni', [])
            
            self._populate_possessori_table(possessori)
            self._populate_localita_table(localita)
            self._populate_variazioni_table(variazioni)
            
            # Aggiorna tab titles e visibilità
            self.results_tabs.setTabText(0, f"👥 Possessori ({len(possessori)})")
            self.results_tabs.setTabText(1, f"🏠 Località ({len(localita)})")
            self.results_tabs.setTabText(self.variazioni_tab_index, f"📋 Variazioni ({len(variazioni)})")
            
            # Mostra tab variazioni solo se ci sono risultati
            self.results_tabs.setTabVisible(self.variazioni_tab_index, len(variazioni) > 0)
            
            # Aggiorna statistiche
            total = len(possessori) + len(localita) + len(variazioni)
            exec_time = results.get('execution_time', 0)
            threshold = results.get('similarity_threshold', 0)
            
            self.stats_label.setText(
                f"🔍 '{results.get('query_text', '')}' → "
                f"{len(possessori)} possessori, {len(localita)} località, {len(variazioni)} variazioni "
                f"(totale: {total}) in {exec_time:.3f}s [soglia: {threshold:.2f}]"
            )
            
            # Abilita export se ci sono risultati
            self.export_button.setEnabled(total > 0)
            
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
        """Popola tabella possessori."""
        self.possessori_table.setRowCount(len(possessori))
        
        for row, possessore in enumerate(possessori):
            # Nome completo
            item_nome = QTableWidgetItem(possessore.get('nome_completo', ''))
            item_nome.setData(Qt.UserRole, possessore)
            self.possessori_table.setItem(row, 0, item_nome)
            
            # Comune
            self.possessori_table.setItem(row, 1, 
                QTableWidgetItem(possessore.get('comune_nome', '')))
            
            # Numero partite
            num_partite = possessore.get('num_partite', 0)
            self.possessori_table.setItem(row, 2, 
                QTableWidgetItem(str(num_partite)))
            
            # Similarità con colore
            similarity = possessore.get('similarity', 0)
            sim_item = QTableWidgetItem(f"{similarity:.1%}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            self._apply_similarity_color(sim_item, similarity)
            self.possessori_table.setItem(row, 3, sim_item)
        
        self.possessori_table.resizeColumnsToContents()
    
    def _populate_localita_table(self, localita):
        """Popola tabella località."""
        self.localita_table.setRowCount(len(localita))
        
        for row, loc in enumerate(localita):
            # Nome località
            item_nome = QTableWidgetItem(loc.get('nome', ''))
            item_nome.setData(Qt.UserRole, loc)
            self.localita_table.setItem(row, 0, item_nome)
            
            # Comune
            self.localita_table.setItem(row, 1, 
                QTableWidgetItem(loc.get('comune_nome', '')))
            
            # Numero immobili
            num_immobili = loc.get('num_immobili', 0)
            self.localita_table.setItem(row, 2, 
                QTableWidgetItem(str(num_immobili)))
            
            # Similarità con colore
            similarity = loc.get('similarity', 0)
            sim_item = QTableWidgetItem(f"{similarity:.1%}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            self._apply_similarity_color(sim_item, similarity)
            self.localita_table.setItem(row, 3, sim_item)
        
        self.localita_table.resizeColumnsToContents()
    
    def _populate_variazioni_table(self, variazioni):
        """Popola tabella variazioni."""
        self.variazioni_table.setRowCount(len(variazioni))
        
        for row, variazione in enumerate(variazioni):
            # ID
            item_id = QTableWidgetItem(str(variazione.get('id', '')))
            item_id.setData(Qt.UserRole, variazione)
            item_id.setTextAlignment(Qt.AlignCenter)
            self.variazioni_table.setItem(row, 0, item_id)
            
            # Tipo
            self.variazioni_table.setItem(row, 1, 
                QTableWidgetItem(variazione.get('tipo', '')))
            
            # Data
            self.variazioni_table.setItem(row, 2, 
                QTableWidgetItem(str(variazione.get('data_variazione', ''))))
            
            # Descrizione
            desc = self._format_variazione_description(variazione)
            self.variazioni_table.setItem(row, 3, QTableWidgetItem(desc))
            
            # Similarità con colore
            similarity = variazione.get('similarity_score', 0)
            sim_item = QTableWidgetItem(f"{similarity:.1%}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            self._apply_similarity_color(sim_item, similarity)
            self.variazioni_table.setItem(row, 4, sim_item)
        
        self.variazioni_table.resizeColumnsToContents()
    
    def _apply_similarity_color(self, item, similarity):
        """Applica colore basato sulla similarità."""
        if similarity > 0.7:
            item.setBackground(QColor(144, 238, 144))  # Verde
        elif similarity > 0.5:
            item.setBackground(QColor(255, 255, 224))  # Giallo
        else:
            item.setBackground(QColor(255, 228, 225))  # Rosa
    
    def _format_variazione_description(self, variazione):
        """Formatta descrizione variazione."""
        parts = []
        
        if variazione.get('nominativo_riferimento'):
            parts.append(f"Rif: {variazione['nominativo_riferimento']}")
        
        if variazione.get('origine_numero') and variazione.get('origine_comune'):
            parts.append(f"da P.{variazione['origine_numero']} ({variazione['origine_comune']})")
        
        if variazione.get('destinazione_numero') and variazione.get('destinazione_comune'):
            parts.append(f"a P.{variazione['destinazione_numero']} ({variazione['destinazione_comune']})")
        
        if variazione.get('notaio'):
            parts.append(f"Not. {variazione['notaio']}")
        
        return " | ".join(parts) if parts else "Variazione catastale"
    
    def _clear_search(self):
        """Pulisce ricerca e risultati."""
        self.search_edit.clear()
        self._clear_results()
    
    def _clear_results(self):
        """Pulisce solo i risultati."""
        self.possessori_table.setRowCount(0)
        self.localita_table.setRowCount(0)
        self.variazioni_table.setRowCount(0)
        
        self.results_tabs.setTabText(0, "👥 Possessori")
        self.results_tabs.setTabText(1, "🏠 Località")
        self.results_tabs.setTabText(self.variazioni_tab_index, "📋 Variazioni")
        self.results_tabs.setTabVisible(self.variazioni_tab_index, False)
        
        self.stats_label.setText("Inserire almeno 3 caratteri per iniziare")
        self.export_button.setEnabled(False)
        self.status_label.setText("Pronto")
        self.status_label.setStyleSheet("color: green; font-size: 10px;")
        self.current_results = {}
    
    def _handle_search_error(self, error_message):
        """Gestisce errori di ricerca."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Errore ricerca")
        self.status_label.setStyleSheet("color: red; font-size: 10px;")
        QMessageBox.critical(self, "Errore Ricerca", f"Errore durante la ricerca:\n{error_message}")
    
    def _check_gin_indices(self):
        """Verifica stato indici GIN."""
        if not self.gin_search:
            QMessageBox.warning(self, "Errore", "Estensione GIN non disponibile")
            return
            
        try:
            indices = self.gin_search.get_gin_indices_info()
            if indices:
                details = []
                for idx in indices:
                    details.append(f"• {idx.get('indexname', 'N/A')}: {idx.get('index_size', 'N/A')}")
                
                QMessageBox.information(
                    self, "Stato Indici GIN", 
                    f"Trovati {len(indices)} indici GIN:\n\n" + "\n".join(details)
                )
            else:
                QMessageBox.warning(
                    self, "Indici GIN", 
                    "Nessun indice GIN trovato!\n\nLa ricerca fuzzy potrebbe essere lenta."
                )
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore verifica indici: {e}")
    
    def _export_results(self):
        """Esporta risultati in formato testo."""
        if not self.current_results:
            QMessageBox.warning(self, "Attenzione", "Nessun risultato da esportare")
            return
        
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ricerca_fuzzy_{timestamp}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("RISULTATI RICERCA FUZZY\n")
                f.write("=" * 60 + "\n")
                f.write(f"Query: {self.current_results.get('query_text', 'N/A')}\n")
                f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Soglia similarità: {self.current_results.get('similarity_threshold', 'N/A')}\n")
                f.write(f"Tempo esecuzione: {self.current_results.get('execution_time', 'N/A'):.3f}s\n\n")
                
                # Possessori
                possessori = self.current_results.get('possessori', [])
                f.write(f"POSSESSORI ({len(possessori)})\n")
                f.write("-" * 40 + "\n")
                for p in possessori:
                    f.write(f"• {p.get('nome_completo', 'N/A')} - {p.get('comune_nome', 'N/A')} "
                           f"({p.get('num_partite', 0)} partite) - Sim: {p.get('similarity', 0):.1%}\n")
                f.write("\n")
                
                # Località
                localita = self.current_results.get('localita', [])
                f.write(f"LOCALITÀ ({len(localita)})\n")
                f.write("-" * 40 + "\n")
                for l in localita:
                    f.write(f"• {l.get('nome', 'N/A')} - {l.get('comune_nome', 'N/A')} "
                           f"({l.get('num_immobili', 0)} immobili) - Sim: {l.get('similarity', 0):.1%}\n")
                f.write("\n")
                
                # Variazioni
                variazioni = self.current_results.get('variazioni', [])
                if variazioni:
                    f.write(f"VARIAZIONI ({len(variazioni)})\n")
                    f.write("-" * 40 + "\n")
                    for v in variazioni:
                        f.write(f"• ID {v.get('id', 'N/A')} - {v.get('tipo', 'N/A')} del {v.get('data_variazione', 'N/A')}\n")
                        f.write(f"  {self._format_variazione_description(v)}\n")
                        f.write(f"  Similarità: {v.get('similarity_score', 0):.1%}\n\n")
            
            QMessageBox.information(self, "Export Completato", f"Risultati esportati in:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Errore Export", f"Errore durante l'esportazione:\n{e}")
    
    def _on_possessore_double_click(self, item):
        """Gestisce doppio click su possessore."""
        if item.column() == 0:  # Solo dalla colonna nome
            possessore_data = item.data(Qt.UserRole)
            if possessore_data:
                QMessageBox.information(
                    self, "Dettagli Possessore",
                    f"Nome: {possessore_data.get('nome_completo', 'N/A')}\n"
                    f"Comune: {possessore_data.get('comune_nome', 'N/A')}\n"
                    f"Numero partite: {possessore_data.get('num_partite', 0)}\n"
                    f"Similarità: {possessore_data.get('similarity', 0):.1%}\n\n"
                    f"ID Possessore: {possessore_data.get('id', 'N/A')}"
                )
    
    def _on_localita_double_click(self, item):
        """Gestisce doppio click su località."""
        if item.column() == 0:  # Solo dalla colonna nome
            localita_data = item.data(Qt.UserRole)
            if localita_data:
                QMessageBox.information(
                    self, "Dettagli Località",
                    f"Nome: {localita_data.get('nome', 'N/A')}\n"
                    f"Tipo: {localita_data.get('tipo', 'N/A')}\n"
                    f"Comune: {localita_data.get('comune_nome', 'N/A')}\n"
                    f"Numero immobili: {localita_data.get('num_immobili', 0)}\n"
                    f"Similarità: {localita_data.get('similarity', 0):.1%}\n\n"
                    f"ID Località: {localita_data.get('id', 'N/A')}"
                )
    
    def _on_variazione_double_click(self, item):
        """Gestisce doppio click su variazione."""
        if item.column() == 0:  # Solo dalla colonna ID
            variazione_data = item.data(Qt.UserRole)
            if variazione_data:
                # Crea dialogo dettagliato per variazione
                self._show_variazione_details(variazione_data)
    
    def _show_variazione_details(self, variazione):
        """Mostra dettagli variazione in dialogo."""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Dettagli Variazione ID {variazione.get('id')}")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Testo con dettagli
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        
        details = f"""VARIAZIONE ID {variazione.get('id')}

Tipo: {variazione.get('tipo', 'N/A')}
Data Variazione: {variazione.get('data_variazione', 'N/A')}
Numero Riferimento: {variazione.get('numero_riferimento', 'N/A')}
Nominativo Riferimento: {variazione.get('nominativo_riferimento', 'N/A')}

PARTITA ORIGINE:
Numero: {variazione.get('origine_numero', 'N/A')}
Comune: {variazione.get('origine_comune', 'N/A')}

PARTITA DESTINAZIONE:
Numero: {variazione.get('destinazione_numero', 'N/A')}
Comune: {variazione.get('destinazione_comune', 'N/A')}

CONTRATTO:
Tipo: {variazione.get('tipo_contratto', 'N/A')}
Data: {variazione.get('data_contratto', 'N/A')}
Notaio: {variazione.get('notaio', 'N/A')}

Similarità: {variazione.get('similarity_score', 0):.1%}"""
        
        details_text.setPlainText(details)
        layout.addWidget(details_text)
        
        # Pulsante chiudi
        close_button = QPushButton("Chiudi")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()

# ========================================================================
# FUNZIONE PER INTEGRAZIONE IN GUI_MAIN
# ========================================================================

def add_simplified_fuzzy_search_tab_to_main_window(main_window):
    """Aggiunge tab ricerca fuzzy semplificata alla finestra principale."""
    try:
        if hasattr(main_window, 'db_manager') and main_window.db_manager:
            fuzzy_widget = SimplifiedFuzzySearchWidget(main_window.db_manager, main_window)
            main_window.tab_widget.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
            print("✅ Tab Ricerca Fuzzy Semplificata aggiunto con successo")
            return True
        else:
            print("❌ Database manager non disponibile")
            return False
    except Exception as e:
        print(f"❌ Errore aggiunta tab ricerca fuzzy: {e}")
        return False
