# ========================================================================
# WIDGET RICERCA FUZZY COMPLETO - TUTTE LE ENTITÀ
# File: complete_fuzzy_search_widget.py
# ========================================================================

"""
Widget ricerca fuzzy completo che cerca in tutte le entità del sistema catasto:
- Possessori (nomi e cognomi)
- Località (nomi luoghi)
- Immobili (natura, classificazione, consistenza)
- Variazioni (tipo, nominativo, numero riferimento)
- Contratti (tipo, notaio, repertorio, note)
- Partite (numero partita, suffisso)

Utilizza la funzione SQL search_all_entities_fuzzy() per performance ottimali.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QTableWidget, QTableWidgetItem, QLabel, QSlider, QTabWidget, 
    QProgressBar, QFrame, QHeaderView, QMessageBox, QComboBox, 
    QTextEdit, QDialog, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor
import time
import logging
import psycopg2.extras

class CompleteFuzzySearchWorker(QThread):
    """Worker thread per ricerca fuzzy completa in tutte le entità."""
    
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, gin_search, query_text, options):
        super().__init__()
        self.gin_search = gin_search
        self.query_text = query_text
        self.options = options
        
    def run(self):
        """Esegue la ricerca completa in background."""
        try:
            self.progress_updated.emit(20)
            
            # Imposta soglia
            threshold = self.options.get('similarity_threshold', 0.3)
            self.gin_search.set_similarity_threshold(threshold)
            
            self.progress_updated.emit(40)
            
            # Ricerca in tutte le entità usando la funzione SQL unificata
            results = self.gin_search.search_all_entities_complete(
                self.query_text,
                similarity_threshold=threshold,
                search_possessori=self.options.get('search_possessori', True),
                search_localita=self.options.get('search_localita', True),
                search_immobili=self.options.get('search_immobili', True),
                search_variazioni=self.options.get('search_variazioni', True),
                search_contratti=self.options.get('search_contratti', True),
                search_partite=self.options.get('search_partite', True),
                max_results_per_type=self.options.get('max_results', 30)
            )
            
            self.progress_updated.emit(100)
            self.results_ready.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class CompleteFuzzySearchWidget(QWidget):
    """Widget ricerca fuzzy completo per tutte le entità del catasto."""
    
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
        """Configura interfaccia utente completa."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)
        
        # === HEADER COMPATTO ===
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🔍 Ricerca Completa nel Catasto")
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
        
        # === CONTROLLI DI RICERCA ===
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel)
        controls_frame.setMaximumHeight(100)
        
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 5, 8, 5)
        controls_layout.setSpacing(5)
        
        # Prima riga: Campo ricerca
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Cerca:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca in tutto il catasto: nomi, luoghi, immobili, variazioni, contratti, partite...")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        search_row.addWidget(self.search_edit)
        
        self.clear_button = QPushButton("✕")
        self.clear_button.setMaximumSize(QSize(25, 25))
        self.clear_button.setToolTip("Pulisci ricerca")
        self.clear_button.clicked.connect(self._clear_search)
        search_row.addWidget(self.clear_button)
        
        controls_layout.addLayout(search_row)
        
        # Seconda riga: Precisione e controlli
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
        
        options_row.addWidget(QLabel("|"))
        
        # Max risultati
        options_row.addWidget(QLabel("Max per tipo:"))
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["10", "20", "30", "50"])
        self.max_results_combo.setCurrentText("30")
        self.max_results_combo.setMaximumWidth(60)
        options_row.addWidget(self.max_results_combo)
        
        options_row.addWidget(QLabel("|"))
        
        # Pulsanti utility
        self.export_button = QPushButton("📤")
        self.export_button.setMaximumSize(QSize(30, 25))
        self.export_button.setToolTip("Esporta Risultati")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_results)
        options_row.addWidget(self.export_button)
        
        self.check_indices_button = QPushButton("🔧")
        self.check_indices_button.setMaximumSize(QSize(30, 25))
        self.check_indices_button.setToolTip("Verifica Indici GIN")
        self.check_indices_button.clicked.connect(self._check_gin_indices)
        options_row.addWidget(self.check_indices_button)
        
        options_row.addStretch()
        controls_layout.addLayout(options_row)
        
        # Terza riga: Filtri tipologie
        filters_row = QHBoxLayout()
        filters_row.addWidget(QLabel("Cerca in:"))
        
        self.search_possessori_cb = QCheckBox("👥 Possessori")
        self.search_possessori_cb.setChecked(True)
        filters_row.addWidget(self.search_possessori_cb)
        
        self.search_localita_cb = QCheckBox("🏠 Località")
        self.search_localita_cb.setChecked(True)
        filters_row.addWidget(self.search_localita_cb)
        
        self.search_immobili_cb = QCheckBox("🏢 Immobili")
        self.search_immobili_cb.setChecked(True)
        filters_row.addWidget(self.search_immobili_cb)
        
        self.search_variazioni_cb = QCheckBox("📋 Variazioni")
        self.search_variazioni_cb.setChecked(True)
        filters_row.addWidget(self.search_variazioni_cb)
        
        self.search_contratti_cb = QCheckBox("📄 Contratti")
        self.search_contratti_cb.setChecked(True)
        filters_row.addWidget(self.search_contratti_cb)
        
        self.search_partite_cb = QCheckBox("📊 Partite")
        self.search_partite_cb.setChecked(True)
        filters_row.addWidget(self.search_partite_cb)
        
        filters_row.addStretch()
        controls_layout.addLayout(filters_row)
        
        main_layout.addWidget(controls_frame)
        
        # === PROGRESS BAR ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # === AREA RISULTATI CON TAB ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)
        
        # Tab per ogni tipologia di entità
        self.possessori_table = self._create_entity_table(["Nome Completo", "Comune", "Paternità", "Similarità"])
        self.possessori_tab_index = self.results_tabs.addTab(self.possessori_table, "👥 Possessori")
        
        self.localita_table = self._create_entity_table(["Nome", "Tipo", "Comune", "Similarità"])
        self.localita_tab_index = self.results_tabs.addTab(self.localita_table, "🏠 Località")
        
        self.immobili_table = self._create_entity_table(["Natura", "Partita", "Località", "Classificazione", "Similarità"])
        self.immobili_tab_index = self.results_tabs.addTab(self.immobili_table, "🏢 Immobili")
        
        self.variazioni_table = self._create_entity_table(["Tipo", "Data", "Partite", "Nominativo", "Similarità"])
        self.variazioni_tab_index = self.results_tabs.addTab(self.variazioni_table, "📋 Variazioni")
        
        self.contratti_table = self._create_entity_table(["Tipo", "Data", "Notaio", "Repertorio", "Similarità"])
        self.contratti_tab_index = self.results_tabs.addTab(self.contratti_table, "📄 Contratti")
        
        self.partite_table = self._create_entity_table(["Numero", "Tipo", "Stato", "Comune", "Similarità"])
        self.partite_tab_index = self.results_tabs.addTab(self.partite_table, "📊 Partite")
        
        # Inizialmente nascondi tutti i tab (verranno mostrati solo se hanno risultati)
        for i in range(1, self.results_tabs.count()):
            self.results_tabs.setTabVisible(i, False)
        
        main_layout.addWidget(self.results_tabs)
        
        # === STATISTICHE ===
        self.stats_label = QLabel("Inserire almeno 3 caratteri per iniziare la ricerca completa")
        self.stats_label.setStyleSheet("color: #666; font-size: 10px; padding: 3px;")
        main_layout.addWidget(self.stats_label)
        
        # Focus iniziale
        self.search_edit.setFocus()
    
    def _create_entity_table(self, headers):
        """Crea tabella standard per un tipo di entità."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Imposta resize mode
        header = table.horizontalHeader()
        for i in range(len(headers) - 1):  # Tutte tranne l'ultima (Similarità)
            if i == 0:
                header.setSectionResizeMode(i, QHeaderView.Stretch)  # Prima colonna espandibile
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeToContents)  # Similarità
        
        # Connetti doppio click
        table.itemDoubleClicked.connect(lambda item, tbl=table: self._on_entity_double_click(item, tbl))
        
        return table
    
    def setup_gin_extension(self):
        """Inizializza estensione GIN completa."""
        try:
            # Importa e inizializza l'estensione completa
            from catasto_gin_extension import extend_db_manager_with_gin
            
            self.gin_search = extend_db_manager_with_gin(self.db_manager)
            if self.gin_search:
                # Aggiungi il metodo per ricerca completa se non esiste
                if not hasattr(self.gin_search, 'search_all_entities_complete'):
                    self._add_complete_search_method()
                
                self.status_label.setText("✅ Sistema ricerca fuzzy completo pronto")
                self.status_label.setStyleSheet("color: green; font-size: 10px;")
            else:
                self.status_label.setText("❌ Errore inizializzazione ricerca fuzzy")
                self.status_label.setStyleSheet("color: red; font-size: 10px;")
        except Exception as e:
            self.logger.error(f"Errore setup GIN completo: {e}")
            self.status_label.setText("❌ Errore estensione GIN")
            self.status_label.setStyleSheet("color: red; font-size: 10px;")
    
    def _add_complete_search_method(self):
        """Aggiunge il metodo di ricerca completa all'estensione GIN."""
        def search_all_entities_complete(query_text, similarity_threshold=0.3, 
                                       search_possessori=True, search_localita=True,
                                       search_immobili=True, search_variazioni=True,
                                       search_contratti=True, search_partite=True,
                                       max_results_per_type=30):
            """Ricerca in tutte le entità usando la funzione SQL unificata."""
            start_time = time.time()
            
            try:
                with self.db_manager.get_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        # Chiama la funzione SQL che hai già implementato
                        cur.execute("""
                            SELECT * FROM search_all_entities_fuzzy(
                                %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """, (
                            query_text,
                            similarity_threshold,
                            search_possessori,
                            search_localita,
                            search_immobili,
                            search_variazioni,
                            search_contratti,
                            search_partite,
                            max_results_per_type
                        ))
                        
                        raw_results = cur.fetchall()
                        
                        # Organizza risultati per tipologia
                        results = {
                            'query_text': query_text,
                            'similarity_threshold': similarity_threshold,
                            'possessori': [],
                            'localita': [],
                            'immobili': [],
                            'variazioni': [],
                            'contratti': [],
                            'partite': [],
                            'execution_time': time.time() - start_time
                        }
                        
                        for row in raw_results:
                            entity_type = row['entity_type']
                            if entity_type in results:
                                # Converte il result in formato compatibile con il widget
                                entity_data = dict(row)
                                entity_data['id'] = row['entity_id']
                                entity_data['similarity'] = row['similarity_score']
                                entity_data['nome_completo'] = row['display_text']
                                entity_data['descrizione'] = row['detail_text']
                                
                                # Decodifica additional_info JSON se presente
                                if row.get('additional_info'):
                                    additional = row['additional_info']
                                    entity_data.update(additional)
                                
                                results[entity_type + 's' if not entity_type.endswith('e') else entity_type[:-1] + 'i'].append(entity_data)
                        
                        return results
                        
            except Exception as e:
                self.logger.error(f"Errore ricerca completa: {e}")
                return {
                    'query_text': query_text,
                    'similarity_threshold': similarity_threshold,
                    'possessori': [], 'localita': [], 'immobili': [],
                    'variazioni': [], 'contratti': [], 'partite': [],
                    'execution_time': time.time() - start_time,
                    'error': str(e)
                }
        
        # Aggiungi il metodo all'istanza
        import types
        self.gin_search.search_all_entities_complete = types.MethodType(search_all_entities_complete, self.gin_search)
    
    def _on_search_text_changed(self):
        """Gestisce cambio testo ricerca."""
        text = self.search_edit.text().strip()
        if len(text) >= 3:
            self.search_timer.stop()
            self.search_timer.start(500)
        else:
            self._clear_results()
    
    def _update_precision_label(self, value):
        """Aggiorna label precisione."""
        self.precision_label.setText(f"{value/100:.2f}")
        if len(self.search_edit.text().strip()) >= 3:
            self.search_timer.stop()
            self.search_timer.start(300)
    
    def _perform_search(self):
        """Esegue ricerca fuzzy completa."""
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
            'max_results': max_results,
            'search_possessori': self.search_possessori_cb.isChecked(),
            'search_localita': self.search_localita_cb.isChecked(),
            'search_immobili': self.search_immobili_cb.isChecked(),
            'search_variazioni': self.search_variazioni_cb.isChecked(),
            'search_contratti': self.search_contratti_cb.isChecked(),
            'search_partite': self.search_partite_cb.isChecked()
        }
        
        # Avvia ricerca in background
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ricerca in corso in tutte le entità...")
        self.status_label.setStyleSheet("color: blue; font-size: 10px;")
        
        self.search_worker = CompleteFuzzySearchWorker(self.gin_search, query_text, options)
        self.search_worker.results_ready.connect(self._display_results)
        self.search_worker.error_occurred.connect(self._handle_search_error)
        self.search_worker.progress_updated.connect(self.progress_bar.setValue)
        self.search_worker.start()
    
    def _display_results(self, results):
        """Visualizza risultati completi."""
        try:
            self.current_results = results
            
            # Conta risultati per tipologia
            counts = {
                'possessori': len(results.get('possessori', [])),
                'localita': len(results.get('localita', [])),
                'immobili': len(results.get('immobili', [])),
                'variazioni': len(results.get('variazioni', [])),
                'contratti': len(results.get('contratti', [])),
                'partite': len(results.get('partite', []))
            }
            
            # Popola tabelle
            self._populate_possessori_table(results.get('possessori', []))
            self._populate_localita_table(results.get('localita', []))
            self._populate_immobili_table(results.get('immobili', []))
            self._populate_variazioni_table(results.get('variazioni', []))
            self._populate_contratti_table(results.get('contratti', []))
            self._populate_partite_table(results.get('partite', []))
            
            # Aggiorna tab titles e visibilità
            self.results_tabs.setTabText(self.possessori_tab_index, f"👥 Possessori ({counts['possessori']})")
            self.results_tabs.setTabText(self.localita_tab_index, f"🏠 Località ({counts['localita']})")
            self.results_tabs.setTabText(self.immobili_tab_index, f"🏢 Immobili ({counts['immobili']})")
            self.results_tabs.setTabText(self.variazioni_tab_index, f"📋 Variazioni ({counts['variazioni']})")
            self.results_tabs.setTabText(self.contratti_tab_index, f"📄 Contratti ({counts['contratti']})")
            self.results_tabs.setTabText(self.partite_tab_index, f"📊 Partite ({counts['partite']})")
            
            # Mostra/nascondi tab in base ai risultati
            for i, (key, count) in enumerate(counts.items()):
                if i < self.results_tabs.count():
                    self.results_tabs.setTabVisible(i, count > 0)
            
            # Statistiche
            total = sum(counts.values())
            exec_time = results.get('execution_time', 0)
            threshold = results.get('similarity_threshold', 0)
            
            stats_parts = []
            for tipo, count in counts.items():
                if count > 0:
                    stats_parts.append(f"{count} {tipo}")
            
            self.stats_label.setText(
                f"🔍 '{results.get('query_text', '')}' → "
                f"{', '.join(stats_parts)} "
                f"(totale: {total}) in {exec_time:.3f}s [soglia: {threshold:.2f}]"
            )
            
            # Abilita export
            self.export_button.setEnabled(total > 0)
            
            # Status finale
            if total > 0:
                self.status_label.setText(f"✅ {total} risultati trovati in {len(stats_parts)} tipologie")
                self.status_label.setStyleSheet("color: green; font-size: 10px;")
                
                # Attiva il primo tab con risultati
                for i, count in enumerate(counts.values()):
                    if count > 0:
                        self.results_tabs.setCurrentIndex(i)
                        break
            else:
                self.status_label.setText("ℹ️ Nessun risultato trovato in nessuna tipologia")
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
        
        for row, p in enumerate(possessori):
            self._set_table_item(self.possessori_table, row, 0, p.get('nome_completo', ''), p)
            self._set_table_item(self.possessori_table, row, 1, p.get('comune', ''))
            self._set_table_item(self.possessori_table, row, 2, p.get('paternita', ''))
            self._set_similarity_item(self.possessori_table, row, 3, p.get('similarity', 0))
    
    def _populate_localita_table(self, localita):
        """Popola tabella località."""
        self.localita_table.setRowCount(len(localita))
        
        for row, l in enumerate(localita):
            nome = l.get('nome_completo', l.get('nome', ''))
            civico = l.get('civico', '')
            nome_completo = f"{nome} {civico}" if civico else nome
            
            self._set_table_item(self.localita_table, row, 0, nome_completo, l)
            self._set_table_item(self.localita_table, row, 1, l.get('tipo', ''))
            self._set_table_item(self.localita_table, row, 2, l.get('comune', ''))
            self._set_similarity_item(self.localita_table, row, 3, l.get('similarity', 0))
    
    def _populate_immobili_table(self, immobili):
        """Popola tabella immobili."""
        self.immobili_table.setRowCount(len(immobili))
        
        for row, i in enumerate(immobili):
            partita_info = f"N.{i.get('numero_partita', '?')}"
            if i.get('suffisso_partita'):
                partita_info += f" {i['suffisso_partita']}"
            
            self._set_table_item(self.immobili_table, row, 0, i.get('nome_completo', i.get('natura', '')), i)
            self._set_table_item(self.immobili_table, row, 1, partita_info)
            self._set_table_item(self.immobili_table, row, 2, i.get('localita', ''))
            self._set_table_item(self.immobili_table, row, 3, i.get('classificazione', ''))
            self._set_similarity_item(self.immobili_table, row, 4, i.get('similarity', 0))
    
    def _populate_variazioni_table(self, variazioni):
        """Popola tabella variazioni."""
        self.variazioni_table.setRowCount(len(variazioni))
        
        for row, v in enumerate(variazioni):
            partite_info = f"{v.get('numero_partita_origine', '?')}"
            if v.get('numero_partita_destinazione'):
                partite_info += f" → {v['numero_partita_destinazione']}"
            
            self._set_table_item(self.variazioni_table, row, 0, v.get('nome_completo', v.get('tipo', '')), v)
            self._set_table_item(self.variazioni_table, row, 1, str(v.get('data_variazione', '')))
            self._set_table_item(self.variazioni_table, row, 2, partite_info)
            self._set_table_item(self.variazioni_table, row, 3, v.get('nominativo_riferimento', ''))
            self._set_similarity_item(self.variazioni_table, row, 4, v.get('similarity', 0))
    
    def _populate_contratti_table(self, contratti):
        """Popola tabella contratti."""
        self.contratti_table.setRowCount(len(contratti))
        
        for row, c in enumerate(contratti):
            self._set_table_item(self.contratti_table, row, 0, c.get('nome_completo', c.get('tipo', '')), c)
            self._set_table_item(self.contratti_table, row, 1, str(c.get('data_contratto', '')))
            self._set_table_item(self.contratti_table, row, 2, c.get('notaio', ''))
            self._set_table_item(self.contratti_table, row, 3, c.get('repertorio', ''))
            self._set_similarity_item(self.contratti_table, row, 4, c.get('similarity', 0))
    
    def _populate_partite_table(self, partite):
        """Popola tabella partite."""
        self.partite_table.setRowCount(len(partite))
        
        for row, p in enumerate(partite):
            numero = str(p.get('numero_partita', ''))
            if p.get('suffisso_partita'):
                numero += f" {p['suffisso_partita']}"
            
            self._set_table_item(self.partite_table, row, 0, numero, p)
            self._set_table_item(self.partite_table, row, 1, p.get('tipo', ''))
            self._set_table_item(self.partite_table, row, 2, p.get('stato', ''))
            self._set_table_item(self.partite_table, row, 3, p.get('comune', ''))
            self._set_similarity_item(self.partite_table, row, 4, p.get('similarity', 0))
    
    def _set_table_item(self, table, row, col, text, data=None):
        """Helper per impostare item nella tabella."""
        item = QTableWidgetItem(str(text))
        if data and col == 0:  # Salva dati completi nella prima colonna
            item.setData(Qt.UserRole, data)
        table.setItem(row, col, item)
    
    def _set_similarity_item(self, table, row, col, similarity):
        """Helper per impostare item similarità con colore."""
        item = QTableWidgetItem(f"{similarity:.1%}")
        item.setTextAlignment(Qt.AlignCenter)
        
        # Colori basati sulla similarità
        if similarity > 0.7:
            item.setBackground(QColor(144, 238, 144))  # Verde
        elif similarity > 0.5:
            item.setBackground(QColor(255, 255, 224))  # Giallo
        else:
            item.setBackground(QColor(255, 228, 225))  # Rosa
            
        table.setItem(row, col, item)
    
    def _clear_search(self):
        """Pulisce ricerca e risultati."""
        self.search_edit.clear()
        self._clear_results()
    
    def _clear_results(self):
        """Pulisce solo i risultati."""
        tables = [
            self.possessori_table, self.localita_table, self.immobili_table,
            self.variazioni_table, self.contratti_table, self.partite_table
        ]
        
        for table in tables:
            table.setRowCount(0)
        
        # Reset tab titles
        tab_names = ["👥 Possessori", "🏠 Località", "🏢 Immobili", "📋 Variazioni", "📄 Contratti", "📊 Partite"]
        for i, name in enumerate(tab_names):
            if i < self.results_tabs.count():
                self.results_tabs.setTabText(i, name)
                self.results_tabs.setTabVisible(i, i == 0)  # Solo il primo visibile
        
        self.stats_label.setText("Inserire almeno 3 caratteri per iniziare la ricerca completa")
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
            if hasattr(self.gin_search, 'get_gin_indices_info'):
                indices = self.gin_search.get_gin_indices_info()
            else:
                QMessageBox.information(self, "Verifica Indici", "Funzione verifica indici non disponibile")
                return
                
            if indices:
                details = []
                for idx in indices:
                    details.append(f"• {idx.get('indexname', 'N/A')}: {idx.get('index_size', 'N/A')}")
                
                QMessageBox.information(
                    self, "Stato Indici GIN", 
                    f"Trovati {len(indices)} indici GIN per ricerca completa:\n\n" + "\n".join(details)
                )
            else:
                QMessageBox.warning(
                    self, "Indici GIN", 
                    "Nessun indice GIN trovato!\n\nEsegui lo script expand_fuzzy_search.sql per creare gli indici necessari."
                )
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore verifica indici: {e}")
    
    def _export_results(self):
        """Esporta risultati completi."""
        if not self.current_results:
            QMessageBox.warning(self, "Attenzione", "Nessun risultato da esportare")
            return
        
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ricerca_completa_{timestamp}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write("RISULTATI RICERCA FUZZY COMPLETA\n")
                f.write("=" * 70 + "\n")
                f.write(f"Query: {self.current_results.get('query_text', 'N/A')}\n")
                f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Soglia similarità: {self.current_results.get('similarity_threshold', 'N/A')}\n")
                f.write(f"Tempo esecuzione: {self.current_results.get('execution_time', 'N/A'):.3f}s\n\n")
                
                # Esporta ogni tipologia
                entity_types = [
                    ('possessori', 'POSSESSORI'),
                    ('localita', 'LOCALITÀ'),
                    ('immobili', 'IMMOBILI'),
                    ('variazioni', 'VARIAZIONI'),
                    ('contratti', 'CONTRATTI'),
                    ('partite', 'PARTITE')
                ]
                
                for key, title in entity_types:
                    entities = self.current_results.get(key, [])
                    if entities:
                        f.write(f"{title} ({len(entities)})\n")
                        f.write("-" * 50 + "\n")
                        for entity in entities:
                            f.write(f"• {entity.get('nome_completo', 'N/A')} - ")
                            f.write(f"Sim: {entity.get('similarity', 0):.1%}\n")
                            if entity.get('descrizione'):
                                f.write(f"  {entity['descrizione']}\n")
                        f.write("\n")
            
            QMessageBox.information(self, "Export Completato", f"Risultati esportati in:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Errore Export", f"Errore durante l'esportazione:\n{e}")
    
    def _on_entity_double_click(self, item, table):
        """Gestisce doppio click su entità."""
        if item.column() == 0:  # Solo dalla prima colonna
            entity_data = item.data(Qt.UserRole)
            if entity_data:
                self._show_entity_details(entity_data, table)
    
    def _show_entity_details(self, entity_data, table):
        """Mostra dettagli entità in dialogo."""
        # Determina il tipo di entità in base alla tabella
        entity_type = "Entità"
        if table == self.possessori_table:
            entity_type = "Possessore"
        elif table == self.localita_table:
            entity_type = "Località"
        elif table == self.immobili_table:
            entity_type = "Immobile"
        elif table == self.variazioni_table:
            entity_type = "Variazione"
        elif table == self.contratti_table:
            entity_type = "Contratto"
        elif table == self.partite_table:
            entity_type = "Partita"
        
        # Crea dialogo dettagli
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Dettagli {entity_type}")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Testo con dettagli
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        
        # Formatta dettagli in base ai dati disponibili
        details = f"{entity_type.upper()}\n"
        details += "=" * 50 + "\n\n"
        
        for key, value in entity_data.items():
            if key not in ['similarity', 'nome_completo'] and value:
                formatted_key = key.replace('_', ' ').title()
                details += f"{formatted_key}: {value}\n"
        
        details += f"\nSimilarità: {entity_data.get('similarity', 0):.1%}\n"
        
        if entity_data.get('descrizione'):
            details += f"\nDescrizione: {entity_data['descrizione']}\n"
        
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

def add_complete_fuzzy_search_tab_to_main_window(main_window):
    """Aggiunge tab ricerca fuzzy completa alla finestra principale."""
    try:
        if hasattr(main_window, 'db_manager') and main_window.db_manager:
            fuzzy_widget = CompleteFuzzySearchWidget(main_window.db_manager, main_window)
            
            # Usa 'tabs' per CatastoMainWindow
            if hasattr(main_window, 'tabs'):
                main_window.tabs.addTab(fuzzy_widget, "🔍 Ricerca Completa")
            elif hasattr(main_window, 'tab_widget'):
                main_window.tab_widget.addTab(fuzzy_widget, "🔍 Ricerca Completa")
            else:
                print("❌ Nessun container tab trovato")
                return False
            
            print("✅ Tab Ricerca Fuzzy Completa aggiunto con successo")
            return True
        else:
            print("❌ Database manager non disponibile")
            return False
    except Exception as e:
        print(f"❌ Errore aggiunta tab ricerca fuzzy completa: {e}")
        import traceback
        print(f"Dettagli errore: {traceback.format_exc()}")
        return False