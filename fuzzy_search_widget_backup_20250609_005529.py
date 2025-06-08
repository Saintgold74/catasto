# ========================================================================
# PASSO 6: WIDGET RICERCA FUZZY PER GUI CATASTO
# File: fuzzy_search_widget.py
# ========================================================================

"""
Widget per ricerca fuzzy che si integra nella GUI principale del catasto.
Utilizza l'estensione GIN per ricerca avanzata in tempo reale.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QLabel, QSlider, QCheckBox, 
    QTabWidget, QProgressBar, QGroupBox, QFormLayout, QSpinBox,
    QTextEdit, QFrame, QSplitter, QHeaderView, QMessageBox,
    QComboBox, QApplication
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

class FuzzySearchWidget(QWidget):
    """
    Widget principale per ricerca fuzzy integrato nella GUI del catasto.
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
        """Configura l'interfaccia utente."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # === HEADER CON TITOLO ===
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        title_label = QLabel("🔍 Ricerca Avanzata (Fuzzy Search)")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        self.status_label = QLabel("Pronto")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        
        main_layout.addWidget(header_frame)
        
        # === SEZIONE RICERCA ===
        search_group = QGroupBox("Parametri di Ricerca")
        search_layout = QFormLayout(search_group)
        
        # Campo ricerca principale
        search_input_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Inserisci nome, cognome, località... (min 3 caratteri)")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        
        self.clear_button = QPushButton("✕")
        self.clear_button.setMaximumSize(QSize(30, 30))
        self.clear_button.setToolTip("Pulisci ricerca")
        self.clear_button.clicked.connect(self._clear_search)
        
        search_input_layout.addWidget(self.search_edit)
        search_input_layout.addWidget(self.clear_button)
        search_layout.addRow("Cerca:", search_input_layout)
        
        # Slider precisione
        precision_layout = QHBoxLayout()
        self.precision_slider = QSlider(Qt.Horizontal)
        self.precision_slider.setRange(10, 80)  # 0.1 - 0.8
        self.precision_slider.setValue(30)  # Default 0.3
        self.precision_slider.valueChanged.connect(self._update_precision_label)
        
        self.precision_label = QLabel("0.30")
        self.precision_label.setMinimumWidth(40)
        self.precision_label.setStyleSheet("font-weight: bold; color: blue;")
        
        precision_layout.addWidget(QLabel("Bassa"))
        precision_layout.addWidget(self.precision_slider)
        precision_layout.addWidget(QLabel("Alta"))
        precision_layout.addWidget(self.precision_label)
        search_layout.addRow("Precisione:", precision_layout)
        
        # Opzioni ricerca
        options_layout = QHBoxLayout()
        self.search_possessori_cb = QCheckBox("Possessori")
        self.search_possessori_cb.setChecked(True)
        self.search_localita_cb = QCheckBox("Località")
        self.search_localita_cb.setChecked(True)
        
        # Limiti risultati
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["20", "50", "100", "200"])
        self.max_results_combo.setCurrentText("50")
        
        options_layout.addWidget(self.search_possessori_cb)
        options_layout.addWidget(self.search_localita_cb)
        options_layout.addStretch()
        options_layout.addWidget(QLabel("Max risultati:"))
        options_layout.addWidget(self.max_results_combo)
        search_layout.addRow("Opzioni:", options_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        search_layout.addRow("Progresso:", self.progress_bar)
        
        main_layout.addWidget(search_group)
        
        # === SEZIONE RISULTATI ===
        results_group = QGroupBox("Risultati Ricerca")
        results_layout = QVBoxLayout(results_group)
        
        # Statistiche
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Nessuna ricerca effettuata")
        self.export_button = QPushButton("📋 Esporta Risultati")
        self.export_button.clicked.connect(self._export_results)
        self.export_button.setEnabled(False)
        
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.export_button)
        results_layout.addLayout(stats_layout)
        
        # Tab risultati
        self.results_tabs = QTabWidget()
        
        # Tab Possessori
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(7)
        self.possessori_table.setHorizontalHeaderLabels([
            "ID", "Nome Completo", "Cognome Nome", "Paternità", "Comune", "Similarità", "N. Partite"
        ])
        self.possessori_table.horizontalHeader().setStretchLastSection(True)
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.doubleClicked.connect(self._on_possessore_double_click)
        
        self.results_tabs.addTab(self.possessori_table, "👥 Possessori")
        
        # Tab Località
        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(6)
        self.localita_table.setHorizontalHeaderLabels([
            "ID", "Nome", "Tipo", "Civico", "Comune", "Similarità"
        ])
        self.localita_table.horizontalHeader().setStretchLastSection(True)
        self.localita_table.setAlternatingRowColors(True)
        self.localita_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.localita_table.doubleClicked.connect(self._on_localita_double_click)
        
        self.results_tabs.addTab(self.localita_table, "🏠 Località")
        
        results_layout.addWidget(self.results_tabs)
        main_layout.addWidget(results_group)
        
        # === SEZIONE INFO/DEBUG ===
        info_group = QGroupBox("Informazioni Sistema")
        info_layout = QVBoxLayout(info_group)
        
        info_controls_layout = QHBoxLayout()
        self.check_indices_button = QPushButton("🔧 Verifica Indici GIN")
        self.check_indices_button.clicked.connect(self._check_gin_indices)
        
        self.indices_status_label = QLabel("Non verificato")
        
        info_controls_layout.addWidget(self.check_indices_button)
        info_controls_layout.addWidget(self.indices_status_label)
        info_controls_layout.addStretch()
        
        info_layout.addLayout(info_controls_layout)
        
        # Area log/debug (collassabile)
        self.debug_text = QTextEdit()
        self.debug_text.setMaximumHeight(80)
        self.debug_text.setPlainText("Sistema ricerca fuzzy inizializzato...")
        info_layout.addWidget(self.debug_text)
        
        main_layout.addWidget(info_group)
        
        # Focus iniziale
        self.search_edit.setFocus()
        
    def setup_gin_extension(self):
        """Inizializza l'estensione GIN."""
        try:
            if not self.db_manager:
                self.debug_text.append("❌ Database manager non disponibile")
                self.status_label.setText("DB non disponibile")
                self.status_label.setStyleSheet("color: red; font-weight: bold;")
                return
                
            self.gin_search = extend_db_manager_with_gin(self.db_manager)
            self.debug_text.append("✅ Estensione GIN inizializzata")
            self.status_label.setText("Pronto per ricerca")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
        except Exception as e:
            self.debug_text.append(f"❌ Errore inizializzazione GIN: {e}")
            self.status_label.setText("Errore inizializzazione")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
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
            
        self.precision_label.setStyleSheet(f"font-weight: bold; color: {color};")
        
    def _on_search_text_changed(self, text):
        """Gestisce cambio testo con debouncing."""
        if len(text) >= 3:
            self.search_timer.stop()
            self.search_timer.start(800)  # 800ms di attesa
            self.status_label.setText("Preparazione ricerca...")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
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
        self.status_label.setText("Ricerca in corso...")
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")
        
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
        threshold = results.get('similarity_threshold', 0)
        
        self.stats_label.setText(
            f"🔍 '{results.get('query_text', '')}' → "
            f"{len(possessori)} possessori, {len(localita)} località "
            f"(totale: {total}) in {exec_time:.3f}s [soglia: {threshold:.2f}]"
        )
        
        # Aggiorna tab titles
        self.results_tabs.setTabText(0, f"👥 Possessori ({len(possessori)})")
        self.results_tabs.setTabText(1, f"🏠 Località ({len(localita)})")
        
        # Abilita export se ci sono risultati
        self.export_button.setEnabled(total > 0)
        
        # Status
        self.status_label.setText(f"Completato - {total} risultati")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        
        self.debug_text.append(f"✅ Ricerca '{results.get('query_text', '')}': {total} risultati")
        
    def _populate_possessori_table(self, possessori):
        """Popola tabella possessori."""
        self.possessori_table.setRowCount(len(possessori))
        
        for row, p in enumerate(possessori):
            # ID
            id_item = QTableWidgetItem(str(p.get('id', '')))
            id_item.setData(Qt.UserRole, p)  # Salva dati completi
            self.possessori_table.setItem(row, 0, id_item)
            
            # Dati principali
            self.possessori_table.setItem(row, 1, QTableWidgetItem(p.get('nome_completo', '')))
            self.possessori_table.setItem(row, 2, QTableWidgetItem(p.get('cognome_nome', '')))
            self.possessori_table.setItem(row, 3, QTableWidgetItem(p.get('paternita', '')))
            self.possessori_table.setItem(row, 4, QTableWidgetItem(p.get('comune_nome', '')))
            
            # Similarità con colore
            similarity = p.get('similarity_score', 0)
            sim_item = QTableWidgetItem(f"{similarity:.3f}")
            if similarity > 0.7:
                sim_item.setBackground(QColor(144, 238, 144))  # Verde
            elif similarity > 0.5:
                sim_item.setBackground(QColor(255, 255, 224))  # Giallo
            else:
                sim_item.setBackground(QColor(255, 228, 225))  # Rosa
            self.possessori_table.setItem(row, 5, sim_item)
            
            # Numero partite
            self.possessori_table.setItem(row, 6, QTableWidgetItem(str(p.get('num_partite', 0))))
            
        self.possessori_table.resizeColumnsToContents()
        
    def _populate_localita_table(self, localita):
        """Popola tabella località."""
        self.localita_table.setRowCount(len(localita))
        
        for row, l in enumerate(localita):
            # ID
            id_item = QTableWidgetItem(str(l.get('id', '')))
            id_item.setData(Qt.UserRole, l)  # Salva dati completi
            self.localita_table.setItem(row, 0, id_item)
            
            # Dati principali
            self.localita_table.setItem(row, 1, QTableWidgetItem(l.get('nome', '')))
            self.localita_table.setItem(row, 2, QTableWidgetItem(l.get('tipo', '')))
            self.localita_table.setItem(row, 3, QTableWidgetItem(str(l.get('civico', '') or '')))
            self.localita_table.setItem(row, 4, QTableWidgetItem(l.get('comune_nome', '')))
            
            # Similarità con colore
            similarity = l.get('similarity_score', 0)
            sim_item = QTableWidgetItem(f"{similarity:.3f}")
            if similarity > 0.7:
                sim_item.setBackground(QColor(144, 238, 144))
            elif similarity > 0.5:
                sim_item.setBackground(QColor(255, 255, 224))
            else:
                sim_item.setBackground(QColor(255, 228, 225))
            self.localita_table.setItem(row, 5, sim_item)
            
        self.localita_table.resizeColumnsToContents()
        
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
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        
    def _handle_search_error(self, error_message):
        """Gestisce errori di ricerca."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Errore ricerca")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.debug_text.append(f"❌ Errore: {error_message}")
        QMessageBox.critical(self, "Errore Ricerca", f"Errore durante la ricerca:\n{error_message}")
        
    def _check_gin_indices(self):
        """Verifica stato indici GIN."""
        if not self.gin_search:
            self.indices_status_label.setText("Estensione non disponibile")
            return
            
        try:
            indices = self.gin_search.get_gin_indices_info()
            if indices:
                self.indices_status_label.setText(f"✅ {len(indices)} indici attivi")
                self.debug_text.append(f"✅ Verifica indici: {len(indices)} trovati")
                
                # Mostra dettagli
                details = []
                for idx in indices:
                    details.append(f"• {idx.get('indexname', 'N/A')}: {idx.get('index_size', 'N/A')}")
                
                QMessageBox.information(
                    self, "Stato Indici GIN", 
                    f"Trovati {len(indices)} indici GIN:\n\n" + "\n".join(details)
                )
            else:
                self.indices_status_label.setText("❌ Nessun indice")
                self.debug_text.append("❌ Nessun indice GIN trovato")
                QMessageBox.warning(
                    self, "Indici GIN", 
                    "Nessun indice GIN trovato!\n\nLa ricerca fuzzy potrebbe essere lenta."
                )
                
        except Exception as e:
            self.indices_status_label.setText("❌ Errore verifica")
            self.debug_text.append(f"❌ Errore verifica indici: {e}")
            
    def _export_results(self):
        """Esporta risultati in formato testo."""
        if not hasattr(self, 'current_results'):
            return
            
        try:
            formatted_text = format_search_results(self.current_results)
            
            from PyQt5.QtWidgets import QTextEdit, QDialog, QVBoxLayout, QPushButton
            
            # Finestra di preview
            dialog = QDialog(self)
            dialog.setWindowTitle("Anteprima Esportazione")
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
            QMessageBox.critical(self, "Errore Export", f"Errore durante l'esportazione:\n{e}")
            
    def _on_possessore_double_click(self, index):
        """Gestisce doppio click su possessore."""
        item = self.possessori_table.item(index.row(), 0)
        if item:
            possessore_data = item.data(Qt.UserRole)
            possessore_id = possessore_data.get('id')
            nome = possessore_data.get('nome_completo', 'N/A')
            
            QMessageBox.information(
                self, f"Possessore ID {possessore_id}",
                f"Nome: {nome}\n"
                f"Comune: {possessore_data.get('comune_nome', 'N/A')}\n"
                f"Partite collegate: {possessore_data.get('num_partite', 0)}\n\n"
                f"Funzionalità di visualizzazione dettagliata\n"
                f"verrà implementata nel widget principale."
            )
            
    def _on_localita_double_click(self, index):
        """Gestisce doppio click su località."""
        item = self.localita_table.item(index.row(), 0)
        if item:
            localita_data = item.data(Qt.UserRole)
            localita_id = localita_data.get('id')
            nome = localita_data.get('nome', 'N/A')
            
            QMessageBox.information(
                self, f"Località ID {localita_id}",
                f"Nome: {nome}\n"
                f"Tipo: {localita_data.get('tipo', 'N/A')}\n"
                f"Civico: {localita_data.get('civico', 'N/A')}\n"
                f"Comune: {localita_data.get('comune_nome', 'N/A')}\n\n"
                f"Funzionalità di visualizzazione dettagliata\n"
                f"verrà implementata nel widget principale."
            )

# ========================================================================
# FUNZIONE DI INTEGRAZIONE NELLA MAIN WINDOW
# ========================================================================

def add_fuzzy_search_tab_to_main_window(main_window):
    """
    Aggiunge il tab di ricerca fuzzy alla finestra principale.
    
    Args:
        main_window: Istanza di CatastoMainWindow
    """
    try:
        if not hasattr(main_window, 'db_manager') or not main_window.db_manager:
            main_window.logger.warning("Database manager non disponibile per ricerca fuzzy")
            return False
            
        # Crea il widget
        fuzzy_widget = FuzzySearchWidget(main_window.db_manager, main_window)
        
        # Aggiunge al TabWidget principale
        tab_index = main_window.tabs.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
        
        main_window.logger.info(f"Tab Ricerca Fuzzy aggiunto all'indice {tab_index}")
        return True
        
    except Exception as e:
        main_window.logger.error(f"Errore aggiunta tab ricerca fuzzy: {e}")
        return False

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
    
    widget = FuzzySearchWidget(MockDBManager())
    widget.show()
    
    sys.exit(app.exec_())
