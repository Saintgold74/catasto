# ========================================================================
# WIDGET FUZZY FUNZIONANTE - BASE + VARIAZIONI
# File: working_fuzzy_search_widget.py
# ========================================================================

"""
Widget ricerca fuzzy che funziona sicuramente, basato sul widget originale
ma con aggiunta delle variazioni.

Cerca in:
- Possessori (funzione esistente)
- Località (funzione esistente) 
- Variazioni (query diretta sicura)
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

class WorkingFuzzySearchWorker(QThread):
    """Worker thread per ricerca fuzzy sicura."""
    
    results_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, gin_search, query_text, options):
        super().__init__()
        self.gin_search = gin_search
        self.query_text = query_text
        self.options = options
        
    def run(self):
        """Esegue la ricerca usando solo metodi sicuri."""
        try:
            self.progress_updated.emit(20)
            
            # Imposta soglia
            threshold = self.options.get('similarity_threshold', 0.3)
            self.gin_search.set_similarity_threshold(threshold)
            
            self.progress_updated.emit(40)
            
            # Inizializza risultati per tutte le entità
            results = {
                'query_text': self.query_text,
                'similarity_threshold': threshold,
                'possessori': [],
                'localita': [],
                'variazioni': [],
                'immobili': [],
                'contratti': [],
                'partite': [],
                'execution_time': 0
            }
            
            start_time = time.time()
            
            # Ricerca possessori (metodo esistente)
            if self.options.get('search_possessori', True):
                if hasattr(self.gin_search, 'search_possessori_fuzzy'):
                    results['possessori'] = self.gin_search.search_possessori_fuzzy(
                        self.query_text, threshold, self.options.get('max_results', 50)
                    )
            
            self.progress_updated.emit(60)
            
            # Ricerca località (metodo esistente)
            if self.options.get('search_localita', True):
                if hasattr(self.gin_search, 'search_localita_fuzzy'):
                    results['localita'] = self.gin_search.search_localita_fuzzy(
                        self.query_text, threshold, self.options.get('max_results', 50) // 2
                    )
            
            # Ricerca immobili (se richiesta)
            if self.options.get('search_immobili', True):
                results['immobili'] = self._search_immobili_safe(
                    self.query_text, threshold, self.options.get('max_results', 50) // 4
                )
            
            # Ricerca contratti (se richiesta)
            if self.options.get('search_contratti', True):
                results['contratti'] = self._search_contratti_safe(
                    self.query_text, threshold, self.options.get('max_results', 50) // 4
                )
            
            # Ricerca partite (se richiesta)
            if self.options.get('search_partite', True):
                results['partite'] = self._search_partite_safe(
                    self.query_text, threshold, self.options.get('max_results', 50) // 4
                )
            
            # Ricerca variazioni (query diretta)
            if self.options.get('search_variazioni', True):
                results['variazioni'] = self._search_variazioni_safe(
                    self.query_text, threshold, self.options.get('max_results', 50) // 3
                )
            
            results['execution_time'] = time.time() - start_time
            
            self.progress_updated.emit(100)
            self.results_ready.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _search_variazioni_safe(self, query_text, threshold, max_results):
        """Ricerca sicura nelle variazioni."""
        try:
            # Usa il metodo corretto del CatastoDBManager
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Query semplice e sicura
                    cur.execute("""
                        SELECT 
                            v.id,
                            v.tipo,
                            v.data_variazione,
                            v.numero_riferimento,
                            v.nominativo_riferimento,
                            po.numero_partita as origine_numero,
                            pd.numero_partita as destinazione_numero,
                            co.nome as comune_nome,
                            similarity(v.tipo, %s) as sim_tipo,
                            similarity(COALESCE(v.nominativo_riferimento, ''), %s) as sim_nominativo
                        FROM variazione v
                        LEFT JOIN partita po ON v.partita_origine_id = po.id
                        LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
                        LEFT JOIN comune co ON po.comune_id = co.id
                        WHERE (
                            v.tipo ILIKE %s OR
                            COALESCE(v.nominativo_riferimento, '') ILIKE %s OR
                            COALESCE(v.numero_riferimento, '') ILIKE %s
                        )
                        ORDER BY sim_tipo DESC, sim_nominativo DESC
                        LIMIT %s
                    """, (
                        query_text, query_text,  # Per similarity
                        f'%{query_text}%',       # Per ILIKE tipo
                        f'%{query_text}%',       # Per ILIKE nominativo
                        f'%{query_text}%',       # Per ILIKE numero_riferimento
                        max_results
                    ))
                    
                    results = []
                    for row in cur.fetchall():
                        variazione = dict(row)
                        
                        # Calcola similarità massima
                        sim_tipo = variazione.get('sim_tipo', 0) or 0
                        sim_nominativo = variazione.get('sim_nominativo', 0) or 0
                        variazione['similarity'] = max(sim_tipo, sim_nominativo)
                        
                        # Formatta nome completo
                        variazione['nome_completo'] = f"{variazione['tipo']}"
                        if variazione.get('nominativo_riferimento'):
                            variazione['nome_completo'] += f" - {variazione['nominativo_riferimento']}"
                        
                        # Formatta descrizione
                        desc_parts = [f"{variazione['tipo']} del {variazione['data_variazione']}"]
                        if variazione.get('origine_numero'):
                            desc_parts.append(f"Partita {variazione['origine_numero']}")
                        if variazione.get('destinazione_numero'):
                            desc_parts.append(f"→ {variazione['destinazione_numero']}")
                        if variazione.get('comune_nome'):
                            desc_parts.append(f"({variazione['comune_nome']})")
                        
                        variazione['descrizione'] = " ".join(desc_parts)
                        
                        results.append(variazione)
                    
                    return results
            finally:
                # Rilascia la connessione al pool
                self.gin_search.db_manager._release_connection(conn)
                    
        except Exception as e:
            print(f"Errore ricerca variazioni: {e}")
            return []
    
    def _search_immobili_safe(self, query_text, threshold, max_results):
        """Ricerca sicura negli immobili."""
        try:
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            i.id,
                            i.natura,
                            i.classificazione,
                            i.consistenza,
                            i.numero_piani,
                            i.numero_vani,
                            p.numero_partita,
                            p.suffisso_partita,
                            l.nome as localita_nome,
                            c.nome as comune_nome,
                            similarity(i.natura, %s) as sim_natura,
                            similarity(COALESCE(i.classificazione, ''), %s) as sim_classificazione,
                            similarity(COALESCE(i.consistenza, ''), %s) as sim_consistenza
                        FROM immobile i
                        JOIN partita p ON i.partita_id = p.id
                        JOIN localita l ON i.localita_id = l.id
                        JOIN comune c ON p.comune_id = c.id
                        WHERE (
                            i.natura ILIKE %s OR
                            COALESCE(i.classificazione, '') ILIKE %s OR
                            COALESCE(i.consistenza, '') ILIKE %s
                        )
                        ORDER BY 
                            GREATEST(
                                similarity(i.natura, %s),
                                similarity(COALESCE(i.classificazione, ''), %s),
                                similarity(COALESCE(i.consistenza, ''), %s)
                            ) DESC
                        LIMIT %s
                    """, (
                        query_text, query_text, query_text,  # Per similarity
                        f'%{query_text}%',  # natura ILIKE
                        f'%{query_text}%',  # classificazione ILIKE
                        f'%{query_text}%',  # consistenza ILIKE
                        query_text, query_text, query_text,  # Per GREATEST
                        max_results
                    ))
                    
                    results = []
                    for row in cur.fetchall():
                        immobile = dict(row)
                        
                        # Calcola similarità massima
                        sim_natura = immobile.get('sim_natura', 0) or 0
                        sim_classificazione = immobile.get('sim_classificazione', 0) or 0
                        sim_consistenza = immobile.get('sim_consistenza', 0) or 0
                        immobile['similarity'] = max(sim_natura, sim_classificazione, sim_consistenza)
                        
                        # Formatta nome completo
                        immobile['nome_completo'] = immobile['natura']
                        
                        # Formatta partita
                        partita_str = f"N.{immobile['numero_partita']}"
                        if immobile.get('suffisso_partita'):
                            partita_str += f" {immobile['suffisso_partita']}"
                        immobile['partita_completa'] = partita_str
                        
                        results.append(immobile)
                    
                    return results
            finally:
                self.gin_search.db_manager._release_connection(conn)
        except Exception as e:
            print(f"Errore ricerca immobili: {e}")
            return []
    
    def _search_contratti_safe(self, query_text, threshold, max_results):
        """Ricerca sicura nei contratti."""
        try:
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            c.id,
                            c.tipo,
                            c.data_contratto,
                            c.notaio,
                            c.repertorio,
                            c.note,
                            v.tipo as variazione_tipo,
                            v.id as variazione_id,
                            similarity(c.tipo, %s) as sim_tipo,
                            similarity(COALESCE(c.notaio, ''), %s) as sim_notaio,
                            similarity(COALESCE(c.repertorio, ''), %s) as sim_repertorio,
                            similarity(COALESCE(c.note, ''), %s) as sim_note
                        FROM contratto c
                        LEFT JOIN variazione v ON c.variazione_id = v.id
                        WHERE (
                            c.tipo ILIKE %s OR
                            COALESCE(c.notaio, '') ILIKE %s OR
                            COALESCE(c.repertorio, '') ILIKE %s OR
                            COALESCE(c.note, '') ILIKE %s
                        )
                        ORDER BY 
                            GREATEST(
                                similarity(c.tipo, %s),
                                similarity(COALESCE(c.notaio, ''), %s),
                                similarity(COALESCE(c.repertorio, ''), %s),
                                similarity(COALESCE(c.note, ''), %s)
                            ) DESC
                        LIMIT %s
                    """, (
                        query_text, query_text, query_text, query_text,  # Per similarity
                        f'%{query_text}%',  # tipo ILIKE
                        f'%{query_text}%',  # notaio ILIKE
                        f'%{query_text}%',  # repertorio ILIKE
                        f'%{query_text}%',  # note ILIKE
                        query_text, query_text, query_text, query_text,  # Per GREATEST
                        max_results
                    ))
                    
                    results = []
                    for row in cur.fetchall():
                        contratto = dict(row)
                        
                        # Calcola similarità massima
                        sim_tipo = contratto.get('sim_tipo', 0) or 0
                        sim_notaio = contratto.get('sim_notaio', 0) or 0
                        sim_repertorio = contratto.get('sim_repertorio', 0) or 0
                        sim_note = contratto.get('sim_note', 0) or 0
                        contratto['similarity'] = max(sim_tipo, sim_notaio, sim_repertorio, sim_note)
                        
                        # Formatta nome completo
                        contratto['nome_completo'] = contratto['tipo']
                        
                        # Formatta descrizione variazione
                        if contratto.get('variazione_tipo'):
                            contratto['variazione_descrizione'] = f"{contratto['variazione_tipo']} (ID: {contratto['variazione_id']})"
                        else:
                            contratto['variazione_descrizione'] = "N/A"
                        
                        results.append(contratto)
                    
                    return results
            finally:
                self.gin_search.db_manager._release_connection(conn)
        except Exception as e:
            print(f"Errore ricerca contratti: {e}")
            return []
    
    def _search_partite_safe(self, query_text, threshold, max_results):
        """Ricerca sicura nelle partite."""
        try:
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            p.id,
                            p.numero_partita,
                            p.suffisso_partita,
                            p.tipo,
                            p.stato,
                            p.data_impianto,
                            p.data_chiusura,
                            c.nome as comune_nome,
                            similarity(p.numero_partita::text, %s) as sim_numero,
                            similarity(COALESCE(p.suffisso_partita, ''), %s) as sim_suffisso
                        FROM partita p
                        JOIN comune c ON p.comune_id = c.id
                        WHERE (
                            p.numero_partita::text ILIKE %s OR
                            COALESCE(p.suffisso_partita, '') ILIKE %s
                        )
                        ORDER BY 
                            GREATEST(
                                similarity(p.numero_partita::text, %s),
                                similarity(COALESCE(p.suffisso_partita, ''), %s)
                            ) DESC
                        LIMIT %s
                    """, (
                        query_text, query_text,  # Per similarity
                        f'%{query_text}%',  # numero ILIKE
                        f'%{query_text}%',  # suffisso ILIKE
                        query_text, query_text,  # Per GREATEST
                        max_results
                    ))
                    
                    results = []
                    for row in cur.fetchall():
                        partita = dict(row)
                        
                        # Calcola similarità massima
                        sim_numero = partita.get('sim_numero', 0) or 0
                        sim_suffisso = partita.get('sim_suffisso', 0) or 0
                        partita['similarity'] = max(sim_numero, sim_suffisso)
                        
                        # Formatta nome completo
                        nome = str(partita['numero_partita'])
                        if partita.get('suffisso_partita'):
                            nome += f" {partita['suffisso_partita']}"
                        partita['nome_completo'] = nome
                        
                        results.append(partita)
                    
                    return results
            finally:
                self.gin_search.db_manager._release_connection(conn)
        except Exception as e:
            print(f"Errore ricerca partite: {e}")
            return []

class WorkingFuzzySearchWidget(QWidget):
    """Widget ricerca fuzzy funzionante con possessori, località e variazioni."""
    
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
        """Configura interfaccia utente."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)
        
        # === HEADER ===
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🔍 Ricerca nel Catasto")
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
        
        # === CONTROLLI ===
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel)
        controls_frame.setMaximumHeight(80)
        
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 5, 8, 5)
        controls_layout.setSpacing(5)
        
        # Prima riga: Campo ricerca
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Cerca:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cerca possessori, località, variazioni... (min 3 caratteri)")
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        search_row.addWidget(self.search_edit)
        
        self.clear_button = QPushButton("✕")
        self.clear_button.setMaximumSize(QSize(25, 25))
        self.clear_button.setToolTip("Pulisci ricerca")
        self.clear_button.clicked.connect(self._clear_search)
        search_row.addWidget(self.clear_button)
        
        controls_layout.addLayout(search_row)
        
        # Seconda riga: Controlli
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
        options_row.addWidget(QLabel("Max:"))
        self.max_results_combo = QComboBox()
        self.max_results_combo.addItems(["20", "50", "100"])
        self.max_results_combo.setCurrentText("50")
        self.max_results_combo.setMaximumWidth(60)
        options_row.addWidget(self.max_results_combo)
        
        options_row.addWidget(QLabel("|"))
        
        # Checkbox tipologie (aggiornate)
        self.search_possessori_cb = QCheckBox("👥 Possessori")
        self.search_possessori_cb.setChecked(True)
        options_row.addWidget(self.search_possessori_cb)
        
        self.search_localita_cb = QCheckBox("🏠 Località")
        self.search_localita_cb.setChecked(True)
        options_row.addWidget(self.search_localita_cb)
        
        self.search_variazioni_cb = QCheckBox("📋 Variazioni")
        self.search_variazioni_cb.setChecked(True)
        options_row.addWidget(self.search_variazioni_cb)
        
        self.search_immobili_cb = QCheckBox("🏢 Immobili")
        self.search_immobili_cb.setChecked(True)
        options_row.addWidget(self.search_immobili_cb)
        
        self.search_contratti_cb = QCheckBox("📄 Contratti")
        self.search_contratti_cb.setChecked(True)
        options_row.addWidget(self.search_contratti_cb)
        
        self.search_partite_cb = QCheckBox("📊 Partite")
        self.search_partite_cb.setChecked(True)
        options_row.addWidget(self.search_partite_cb)
        
        options_row.addWidget(QLabel("|"))
        
        # Pulsanti utility
        self.export_button = QPushButton("📤")
        self.export_button.setMaximumSize(QSize(30, 25))
        self.export_button.setToolTip("Esporta Risultati")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_results)
        options_row.addWidget(self.export_button)
        
        options_row.addStretch()
        controls_layout.addLayout(options_row)
        
        main_layout.addWidget(controls_frame)
        
        # === PROGRESS BAR ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # === TAB RISULTATI ===
        self.results_tabs = QTabWidget()
        self.results_tabs.setMinimumHeight(400)
        
        # Tab Possessori
        self.possessori_table = self._create_possessori_table()
        self.results_tabs.addTab(self.possessori_table, "👥 Possessori")
        
        # Tab Località
        self.localita_table = self._create_localita_table()
        self.results_tabs.addTab(self.localita_table, "🏠 Località")
        
        # Tab Variazioni (sempre visibile)
        self.variazioni_table = self._create_variazioni_table()
        self.variazioni_tab_index = self.results_tabs.addTab(self.variazioni_table, "📋 Variazioni")
        # Non nascondere più il tab - rimane sempre visibile
        
        # Tab Immobili (sempre visibile)
        self.immobili_table = self._create_immobili_table()
        self.immobili_tab_index = self.results_tabs.addTab(self.immobili_table, "🏢 Immobili")
        
        # Tab Contratti (sempre visibile)
        self.contratti_table = self._create_contratti_table()
        self.contratti_tab_index = self.results_tabs.addTab(self.contratti_table, "📄 Contratti")
        
        # Tab Partite (sempre visibile)
        self.partite_table = self._create_partite_table()
        self.partite_tab_index = self.results_tabs.addTab(self.partite_table, "📊 Partite")
        
        main_layout.addWidget(self.results_tabs)
        
        # === STATISTICHE ===
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
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
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
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        table.itemDoubleClicked.connect(self._on_localita_double_click)
        return table
    
    def _create_variazioni_table(self):
        """Crea tabella variazioni."""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Tipo", "Data", "Nominativo", "Descrizione", "Similarità"])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
    def _create_immobili_table(self):
        """Crea tabella immobili."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Natura", "Partita", "Località", "Classificazione", "Consistenza", "Similarità"])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Natura
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Partita
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Località
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Classificazione
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Consistenza
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Similarità
        
        table.itemDoubleClicked.connect(self._on_immobile_double_click)
        return table
    
    def _create_contratti_table(self):
        """Crea tabella contratti."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Tipo", "Data", "Notaio", "Repertorio", "Variazione", "Similarità"])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Tipo
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Data
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Notaio
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Repertorio
        header.setSectionResizeMode(4, QHeaderView.Stretch)           # Variazione
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Similarità
        
        table.itemDoubleClicked.connect(self._on_contratto_double_click)
        return table
    
    def _create_partite_table(self):
        """Crea tabella partite."""
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["Numero", "Suffisso", "Tipo", "Stato", "Comune", "Similarità"])
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Numero
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Suffisso
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Tipo
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Stato
        header.setSectionResizeMode(4, QHeaderView.Stretch)           # Comune
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Similarità
        
        table.itemDoubleClicked.connect(self._on_partita_double_click)
        return table
    
    def setup_gin_extension(self):
        """Inizializza estensione GIN."""
        try:
            from catasto_gin_extension import extend_db_manager_with_gin
            
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
        """Esegue ricerca fuzzy."""
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
            'search_variazioni': self.search_variazioni_cb.isChecked(),
            'search_immobili': self.search_immobili_cb.isChecked(),
            'search_contratti': self.search_contratti_cb.isChecked(),
            'search_partite': self.search_partite_cb.isChecked()
        }
        
        # Avvia ricerca in background
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ricerca in corso...")
        self.status_label.setStyleSheet("color: blue; font-size: 10px;")
        
        self.search_worker = WorkingFuzzySearchWorker(self.gin_search, query_text, options)
        self.search_worker.results_ready.connect(self._display_results)
        self.search_worker.error_occurred.connect(self._handle_search_error)
        self.search_worker.progress_updated.connect(self.progress_bar.setValue)
        self.search_worker.start()
    
    def _display_results(self, results):
        """Visualizza risultati."""
        try:
            self.current_results = results
            
            # Conta risultati
            possessori = results.get('possessori', [])
            localita = results.get('localita', [])
            variazioni = results.get('variazioni', [])
            immobili = results.get('immobili', [])
            contratti = results.get('contratti', [])
            partite = results.get('partite', [])
            
            # Popola tabelle solo se esistono
            if hasattr(self, 'possessori_table') and self.possessori_table:
                self._populate_possessori_table(possessori)
            if hasattr(self, 'localita_table') and self.localita_table:
                self._populate_localita_table(localita)
            if hasattr(self, 'variazioni_table') and self.variazioni_table:
                self._populate_variazioni_table(variazioni)
            if hasattr(self, 'immobili_table') and self.immobili_table:
                self._populate_immobili_table(immobili)
            if hasattr(self, 'contratti_table') and self.contratti_table:
                self._populate_contratti_table(contratti)
            if hasattr(self, 'partite_table') and self.partite_table:
                self._populate_partite_table(partite)
            
            # Aggiorna tab titles solo se il widget tab esiste
            if hasattr(self, 'results_tabs') and self.results_tabs:
                self.results_tabs.setTabText(0, f"👥 Possessori ({len(possessori)})")
                self.results_tabs.setTabText(1, f"🏠 Località ({len(localita)})")
                
                if hasattr(self, 'variazioni_tab_index'):
                    self.results_tabs.setTabText(self.variazioni_tab_index, f"📋 Variazioni ({len(variazioni)})")
                if hasattr(self, 'immobili_tab_index'):
                    self.results_tabs.setTabText(self.immobili_tab_index, f"🏢 Immobili ({len(immobili)})")
                if hasattr(self, 'contratti_tab_index'):
                    self.results_tabs.setTabText(self.contratti_tab_index, f"📄 Contratti ({len(contratti)})")
                if hasattr(self, 'partite_tab_index'):
                    self.results_tabs.setTabText(self.partite_tab_index, f"📊 Partite ({len(partite)})")
            
            # Statistiche complete
            total = len(possessori) + len(localita) + len(variazioni) + len(immobili) + len(contratti) + len(partite)
            exec_time = results.get('execution_time', 0)
            threshold = results.get('similarity_threshold', 0)
            
            if hasattr(self, 'stats_label') and self.stats_label:
                self.stats_label.setText(
                    f"🔍 '{results.get('query_text', '')}' → "
                    f"{len(possessori)} possessori, {len(localita)} località, {len(variazioni)} variazioni, "
                    f"{len(immobili)} immobili, {len(contratti)} contratti, {len(partite)} partite "
                    f"(totale: {total}) in {exec_time:.3f}s [soglia: {threshold:.2f}]"
                )
            
            # Abilita export
            if hasattr(self, 'export_button') and self.export_button:
                self.export_button.setEnabled(total > 0)
            
            # Status finale
            if hasattr(self, 'status_label') and self.status_label:
                if total > 0:
                    self.status_label.setText(f"✅ {total} risultati trovati")
                    self.status_label.setStyleSheet("color: green; font-size: 10px;")
                else:
                    self.status_label.setText("ℹ️ Nessun risultato trovato")
                    self.status_label.setStyleSheet("color: gray; font-size: 10px;")
                
        except Exception as e:
            self.logger.error(f"Errore visualizzazione risultati: {e}")
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText("❌ Errore visualizzazione")
                self.status_label.setStyleSheet("color: red; font-size: 10px;")
            print(f"DEBUG - Errore dettagliato: {e}")
            import traceback
            print(f"DEBUG - Traceback: {traceback.format_exc()}")
        finally:
            if hasattr(self, 'progress_bar') and self.progress_bar:
                self.progress_bar.setVisible(False)
    
    def _populate_possessori_table(self, possessori):
        """Popola tabella possessori."""
        self.possessori_table.setRowCount(len(possessori))
        
        for row, possessore in enumerate(possessori):
            item_nome = QTableWidgetItem(possessore.get('nome_completo', ''))
            item_nome.setData(Qt.UserRole, possessore)
            self.possessori_table.setItem(row, 0, item_nome)
            
            self.possessori_table.setItem(row, 1, 
                QTableWidgetItem(possessore.get('comune_nome', '')))
            
            num_partite = possessore.get('num_partite', 0)
            self.possessori_table.setItem(row, 2, 
                QTableWidgetItem(str(num_partite)))
            
            # Debug: stampa tutti i campi per capire come si chiama la similarità
            if row == 0:  # Solo per il primo risultato
                print(f"DEBUG Possessore - Campi disponibili: {list(possessore.keys())}")
                for key, value in possessore.items():
                    if 'sim' in key.lower():
                        print(f"DEBUG Possessore - Campo {key}: {value}")
            
            # Prova diversi nomi per il campo similarità
            similarity = (possessore.get('similarity') or 
                         possessore.get('similarity_score') or 
                         possessore.get('sim_score') or 0)
            
            sim_item = QTableWidgetItem(f"{similarity:.1%}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            self._apply_similarity_color(sim_item, similarity)
            self.possessori_table.setItem(row, 3, sim_item)
        
        self.possessori_table.resizeColumnsToContents()
    
    def _populate_localita_table(self, localita):
        """Popola tabella località."""
        self.localita_table.setRowCount(len(localita))
        
        # Ottieni il conteggio immobili per tutte le località in una sola query
        immobili_counts = self._get_immobili_counts_for_localita([loc.get('id') for loc in localita])
        
        for row, loc in enumerate(localita):
            item_nome = QTableWidgetItem(loc.get('nome', ''))
            item_nome.setData(Qt.UserRole, loc)
            self.localita_table.setItem(row, 0, item_nome)
            
            self.localita_table.setItem(row, 1, 
                QTableWidgetItem(loc.get('comune_nome', '')))
            
            # Usa il conteggio ottenuto dalla query separata
            num_immobili = immobili_counts.get(loc.get('id'), 0)
            self.localita_table.setItem(row, 2, 
                QTableWidgetItem(str(num_immobili)))
            
            # Prova diversi nomi per il campo similarità
            similarity = (loc.get('similarity') or 
                         loc.get('similarity_score') or 
                         loc.get('sim_score') or 0)
            
            sim_item = QTableWidgetItem(f"{similarity:.1%}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            self._apply_similarity_color(sim_item, similarity)
            self.localita_table.setItem(row, 3, sim_item)
        
        self.localita_table.resizeColumnsToContents()
    
    def _get_immobili_counts_for_localita(self, localita_ids):
        """Ottiene il conteggio degli immobili per le località specificate."""
        if not localita_ids:
            return {}
        
        try:
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Query per contare gli immobili per località
                    placeholders = ','.join(['%s'] * len(localita_ids))
                    cur.execute(f"""
                        SELECT 
                            localita_id,
                            COUNT(*) as num_immobili
                        FROM immobile 
                        WHERE localita_id IN ({placeholders})
                        GROUP BY localita_id
                    """, localita_ids)
                    
                    results = cur.fetchall()
                    return {row['localita_id']: row['num_immobili'] for row in results}
            finally:
                self.gin_search.db_manager._release_connection(conn)
        except Exception as e:
            print(f"Errore conteggio immobili per località: {e}")
            return {}
    
    def _populate_variazioni_table(self, variazioni):
        """Popola tabella variazioni."""
        self.variazioni_table.setRowCount(len(variazioni))
        
        for row, variazione in enumerate(variazioni):
            # Tipo
            item_tipo = QTableWidgetItem(variazione.get('tipo', ''))
            item_tipo.setData(Qt.UserRole, variazione)
            self.variazioni_table.setItem(row, 0, item_tipo)
            
            # Data
            self.variazioni_table.setItem(row, 1, 
                QTableWidgetItem(str(variazione.get('data_variazione', ''))))
            
            # Nominativo
            self.variazioni_table.setItem(row, 2, 
                QTableWidgetItem(variazione.get('nominativo_riferimento', '')))
            
            # Descrizione
            self.variazioni_table.setItem(row, 3, 
                QTableWidgetItem(variazione.get('descrizione', '')))
            
            # Similarità
            similarity = variazione.get('similarity', 0)
            sim_item = QTableWidgetItem(f"{similarity:.1%}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            self._apply_similarity_color(sim_item, similarity)
            self.variazioni_table.setItem(row, 4, sim_item)
        
        self.variazioni_table.resizeColumnsToContents()
    
    def _populate_immobili_table(self, immobili):
        """Popola tabella immobili."""
        self.immobili_table.setRowCount(len(immobili))
        
        for row, immobile in enumerate(immobili):
            # Natura
            item_natura = QTableWidgetItem(immobile.get('natura', ''))
            item_natura.setData(Qt.UserRole, immobile)
            self.immobili_table.setItem(row, 0, item_natura)
            
            # Partita
            self.immobili_table.setItem(row, 1, 
                QTableWidgetItem(immobile.get('partita_completa', '')))
            
            # Località
            self.immobili_table.setItem(row, 2, 
                QTableWidgetItem(immobile.get('localita_nome', '')))
            
            # Classificazione
            self.immobili_table.setItem(row, 3, 
                QTableWidgetItem(immobile.get('classificazione', '')))
            
            # Consistenza
            self.immobili_table.setItem(row, 4, 
                QTableWidgetItem(immobile.get('consistenza', '')))
            
            # Similarità
            similarity = immobile.get('similarity', 0)
            sim_item = QTableWidgetItem(f"{similarity:.1%}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            self._apply_similarity_color(sim_item, similarity)
            self.immobili_table.setItem(row, 5, sim_item)
        
        self.immobili_table.resizeColumnsToContents()
    
    def _populate_contratti_table(self, contratti):
        """Popola tabella contratti."""
        self.contratti_table.setRowCount(len(contratti))
        
        for row, contratto in enumerate(contratti):
            # Tipo
            item_tipo = QTableWidgetItem(contratto.get('tipo', ''))
            item_tipo.setData(Qt.UserRole, contratto)
            self.contratti_table.setItem(row, 0, item_tipo)
            
            # Data
            self.contratti_table.setItem(row, 1, 
                QTableWidgetItem(str(contratto.get('data_contratto', ''))))
            
            # Notaio
            self.contratti_table.setItem(row, 2, 
                QTableWidgetItem(contratto.get('notaio', '')))
            
            # Repertorio
            self.contratti_table.setItem(row, 3, 
                QTableWidgetItem(contratto.get('repertorio', '')))
            
            # Variazione
            self.contratti_table.setItem(row, 4, 
                QTableWidgetItem(contratto.get('variazione_descrizione', '')))
            
            # Similarità
            similarity = contratto.get('similarity', 0)
            sim_item = QTableWidgetItem(f"{similarity:.1%}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            self._apply_similarity_color(sim_item, similarity)
            self.contratti_table.setItem(row, 5, sim_item)
        
        self.contratti_table.resizeColumnsToContents()
    
    def _populate_partite_table(self, partite):
        """Popola tabella partite."""
        self.partite_table.setRowCount(len(partite))
        
        for row, partita in enumerate(partite):
            # Numero
            item_numero = QTableWidgetItem(str(partita.get('numero_partita', '')))
            item_numero.setData(Qt.UserRole, partita)
            self.partite_table.setItem(row, 0, item_numero)
            
            # Suffisso
            self.partite_table.setItem(row, 1, 
                QTableWidgetItem(partita.get('suffisso_partita', '')))
            
            # Tipo
            self.partite_table.setItem(row, 2, 
                QTableWidgetItem(partita.get('tipo', '')))
            
            # Stato
            self.partite_table.setItem(row, 3, 
                QTableWidgetItem(partita.get('stato', '')))
            
            # Comune
            self.partite_table.setItem(row, 4, 
                QTableWidgetItem(partita.get('comune_nome', '')))
            
            # Similarità
            similarity = partita.get('similarity', 0)
            sim_item = QTableWidgetItem(f"{similarity:.1%}")
            sim_item.setTextAlignment(Qt.AlignCenter)
            self._apply_similarity_color(sim_item, similarity)
            self.partite_table.setItem(row, 5, sim_item)
        
        self.partite_table.resizeColumnsToContents()
    
    def _apply_similarity_color(self, item, similarity):
        """Applica colore basato sulla similarità."""
        if similarity > 0.7:
            item.setBackground(QColor(144, 238, 144))  # Verde
        elif similarity > 0.5:
            item.setBackground(QColor(255, 255, 224))  # Giallo
        else:
            item.setBackground(QColor(255, 228, 225))  # Rosa
    
    def _clear_search(self):
        """Pulisce ricerca e risultati."""
        self.search_edit.clear()
        self._clear_results()
    
    def _clear_results(self):
        """Pulisce solo i risultati."""
        # Controlla che le tabelle esistano prima di pulirle
        if hasattr(self, 'possessori_table') and self.possessori_table:
            self.possessori_table.setRowCount(0)
        if hasattr(self, 'localita_table') and self.localita_table:
            self.localita_table.setRowCount(0)
        if hasattr(self, 'variazioni_table') and self.variazioni_table:
            self.variazioni_table.setRowCount(0)
        if hasattr(self, 'immobili_table') and self.immobili_table:
            self.immobili_table.setRowCount(0)
        if hasattr(self, 'contratti_table') and self.contratti_table:
            self.contratti_table.setRowCount(0)
        if hasattr(self, 'partite_table') and self.partite_table:
            self.partite_table.setRowCount(0)
        
        # Aggiorna i titoli dei tab solo se esistono
        if hasattr(self, 'results_tabs') and self.results_tabs:
            self.results_tabs.setTabText(0, "👥 Possessori")
            self.results_tabs.setTabText(1, "🏠 Località")
            
            if hasattr(self, 'variazioni_tab_index'):
                self.results_tabs.setTabText(self.variazioni_tab_index, "📋 Variazioni")
            if hasattr(self, 'immobili_tab_index'):
                self.results_tabs.setTabText(self.immobili_tab_index, "🏢 Immobili")
            if hasattr(self, 'contratti_tab_index'):
                self.results_tabs.setTabText(self.contratti_tab_index, "📄 Contratti")
            if hasattr(self, 'partite_tab_index'):
                self.results_tabs.setTabText(self.partite_tab_index, "📊 Partite")
        
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
    
    def _export_results(self):
        """Esporta risultati."""
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
                f.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Possessori
                possessori = self.current_results.get('possessori', [])
                if possessori:
                    f.write(f"POSSESSORI ({len(possessori)})\n")
                    f.write("-" * 40 + "\n")
                    for p in possessori:
                        f.write(f"• {p.get('nome_completo', 'N/A')} - {p.get('comune_nome', 'N/A')} "
                               f"(Sim: {p.get('similarity', 0):.1%})\n")
                    f.write("\n")
                
                # Località
                localita = self.current_results.get('localita', [])
                if localita:
                    f.write(f"LOCALITÀ ({len(localita)})\n")
                    f.write("-" * 40 + "\n")
                    for l in localita:
                        f.write(f"• {l.get('nome', 'N/A')} - {l.get('comune_nome', 'N/A')} "
                               f"(Sim: {l.get('similarity', 0):.1%})\n")
                    f.write("\n")
                
                # Variazioni
                variazioni = self.current_results.get('variazioni', [])
                if variazioni:
                    f.write(f"VARIAZIONI ({len(variazioni)})\n")
                    f.write("-" * 40 + "\n")
                    for v in variazioni:
                        f.write(f"• {v.get('tipo', 'N/A')} del {v.get('data_variazione', 'N/A')}\n")
                        f.write(f"  {v.get('descrizione', '')}\n")
                        f.write(f"  Similarità: {v.get('similarity', 0):.1%}\n\n")
                
                # Immobili
                immobili = self.current_results.get('immobili', [])
                if immobili:
                    f.write(f"IMMOBILI ({len(immobili)})\n")
                    f.write("-" * 40 + "\n")
                    for i in immobili:
                        f.write(f"• {i.get('natura', 'N/A')} - Partita {i.get('partita_completa', 'N/A')}\n")
                        f.write(f"  Località: {i.get('localita_nome', 'N/A')}\n")
                        f.write(f"  Classificazione: {i.get('classificazione', 'N/A')}\n")
                        f.write(f"  Similarità: {i.get('similarity', 0):.1%}\n\n")
                
                # Contratti
                contratti = self.current_results.get('contratti', [])
                if contratti:
                    f.write(f"CONTRATTI ({len(contratti)})\n")
                    f.write("-" * 40 + "\n")
                    for c in contratti:
                        f.write(f"• {c.get('tipo', 'N/A')} del {c.get('data_contratto', 'N/A')}\n")
                        f.write(f"  Notaio: {c.get('notaio', 'N/A')}\n")
                        f.write(f"  Repertorio: {c.get('repertorio', 'N/A')}\n")
                        f.write(f"  Similarità: {c.get('similarity', 0):.1%}\n\n")
                
                # Partite
                partite = self.current_results.get('partite', [])
                if partite:
                    f.write(f"PARTITE ({len(partite)})\n")
                    f.write("-" * 40 + "\n")
                    for p in partite:
                        f.write(f"• N. {p.get('numero_partita', 'N/A')} {p.get('suffisso_partita', '')}\n")
                        f.write(f"  Comune: {p.get('comune_nome', 'N/A')} - Stato: {p.get('stato', 'N/A')}\n")
                        f.write(f"  Similarità: {p.get('similarity', 0):.1%}\n\n")
            
            QMessageBox.information(self, "Export Completato", f"Risultati esportati in:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Errore Export", f"Errore durante l'esportazione:\n{e}")
    
    def _get_partita_info_by_number(self, numero_partita, comune_nome):
        """Ottiene informazioni partita per numero e comune."""
        if not numero_partita:
            return None
        
        try:
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT p.*, c.nome as comune_nome
                        FROM partita p
                        JOIN comune c ON p.comune_id = c.id
                        WHERE p.numero_partita = %s AND c.nome ILIKE %s
                        LIMIT 1
                    """, (numero_partita, f'%{comune_nome}%'))
                    
                    result = cur.fetchone()
                    return dict(result) if result else None
            finally:
                self.gin_search.db_manager._release_connection(conn)
        except Exception as e:
            print(f"Errore recupero partita {numero_partita}: {e}")
            return None
    
    def _get_variazione_info_by_id(self, variazione_id):
        """Ottiene informazioni variazione per ID."""
        if not variazione_id:
            return None
        
        try:
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            v.*,
                            po.numero_partita as numero_partita_origine,
                            co.nome as comune_origine,
                            pd.numero_partita as numero_partita_destinazione,
                            cd.nome as comune_destinazione
                        FROM variazione v
                        LEFT JOIN partita po ON v.partita_origine_id = po.id
                        LEFT JOIN comune co ON po.comune_id = co.id
                        LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
                        LEFT JOIN comune cd ON pd.comune_id = cd.id
                        WHERE v.id = %s
                    """, (variazione_id,))
                    
                    result = cur.fetchone()
                    return dict(result) if result else None
            finally:
                self.gin_search.db_manager._release_connection(conn)
        except Exception as e:
            print(f"Errore recupero variazione {variazione_id}: {e}")
            return None
    
    def _show_partita_details_dialog(self, partita_info, parent_dialog):
        """Mostra dialogo dettagli partita."""
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle(f"Partita N. {partita_info.get('numero_partita')}")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        
        details = f"""PARTITA N. {partita_info.get('numero_partita')} {partita_info.get('suffisso_partita', '')}

Tipo: {partita_info.get('tipo', 'N/A')}
Stato: {partita_info.get('stato', 'N/A')}
Comune: {partita_info.get('comune_nome', 'N/A')}
Data Impianto: {partita_info.get('data_impianto', 'N/A')}
Data Chiusura: {partita_info.get('data_chiusura', 'N/A')}
ID: {partita_info.get('id', 'N/A')}"""
        
        details_text.setPlainText(details)
        layout.addWidget(details_text)
        
        close_button = QPushButton("Chiudi")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _show_variazione_details_dialog(self, variazione_info, parent_dialog):
        """Mostra dialogo dettagli variazione."""
        dialog = QDialog(parent_dialog)
        dialog.setWindowTitle(f"Variazione ID {variazione_info.get('id')}")
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QVBoxLayout()
        
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        
        details = f"""VARIAZIONE ID {variazione_info.get('id')}

Tipo: {variazione_info.get('tipo', 'N/A')}
Data: {variazione_info.get('data_variazione', 'N/A')}
Numero Riferimento: {variazione_info.get('numero_riferimento', 'N/A')}
Nominativo: {variazione_info.get('nominativo_riferimento', 'N/A')}

Partita Origine: N. {variazione_info.get('numero_partita_origine', 'N/A')} ({variazione_info.get('comune_origine', 'N/A')})
Partita Destinazione: N. {variazione_info.get('numero_partita_destinazione', 'N/A')} ({variazione_info.get('comune_destinazione', 'N/A')})"""
        
        details_text.setPlainText(details)
        layout.addWidget(details_text)
        
        close_button = QPushButton("Chiudi")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def _on_possessore_double_click(self, item):
        """Gestisce doppio click su possessore."""
        if item.column() == 0:
            possessore_data = item.data(Qt.UserRole)
            if possessore_data:
                # Trova la similarità con gli stessi criteri della tabella
                similarity = (possessore_data.get('similarity') or 
                             possessore_data.get('similarity_score') or 
                             possessore_data.get('sim_score') or 0)
                
                QMessageBox.information(
                    self, "Dettagli Possessore",
                    f"Nome: {possessore_data.get('nome_completo', 'N/A')}\n"
                    f"Comune: {possessore_data.get('comune_nome', 'N/A')}\n"
                    f"Numero partite: {possessore_data.get('num_partite', 0)}\n"
                    f"Similarità: {similarity:.1%}\n"
                    f"ID: {possessore_data.get('id', 'N/A')}"
                )
    
    def _on_localita_double_click(self, item):
        """Gestisce doppio click su località."""
        if item.column() == 0:
            localita_data = item.data(Qt.UserRole)
            if localita_data:
                # Trova la similarità con gli stessi criteri della tabella
                similarity = (localita_data.get('similarity') or 
                             localita_data.get('similarity_score') or 
                             localita_data.get('sim_score') or 0)
                
                # Ottieni il numero di immobili con una query diretta
                num_immobili = self._get_immobili_count_for_single_localita(localita_data.get('id'))
                
                QMessageBox.information(
                    self, "Dettagli Località",
                    f"Nome: {localita_data.get('nome', 'N/A')}\n"
                    f"Tipo: {localita_data.get('tipo', 'N/A')}\n"
                    f"Comune: {localita_data.get('comune_nome', 'N/A')}\n"
                    f"Numero immobili: {num_immobili}\n"
                    f"Similarità: {similarity:.1%}\n"
                    f"ID: {localita_data.get('id', 'N/A')}"
                )
    
    def _get_immobili_count_for_single_localita(self, localita_id):
        """Ottiene il conteggio degli immobili per una singola località."""
        if not localita_id:
            return 0
        
        try:
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM immobile 
                        WHERE localita_id = %s
                    """, (localita_id,))
                    
                    result = cur.fetchone()
                    return result[0] if result else 0
            finally:
                self.gin_search.db_manager._release_connection(conn)
        except Exception as e:
            print(f"Errore conteggio immobili per località {localita_id}: {e}")
            return 0
    
    def _on_variazione_double_click(self, item):
        """Gestisce doppio click su variazione."""
        if item.column() == 0:
            variazione_data = item.data(Qt.UserRole)
            if variazione_data:
                # Crea dialogo dettagliato
                dialog = QDialog(self)
                dialog.setWindowTitle(f"Dettagli Variazione ID {variazione_data.get('id')}")
                dialog.setModal(True)
                dialog.resize(500, 350)
                
                layout = QVBoxLayout()
                
                details_text = QTextEdit()
                details_text.setReadOnly(True)
                
                details = f"""VARIAZIONE ID {variazione_data.get('id')}

Tipo: {variazione_data.get('tipo', 'N/A')}
Data: {variazione_data.get('data_variazione', 'N/A')}
Numero Riferimento: {variazione_data.get('numero_riferimento', 'N/A')}
Nominativo: {variazione_data.get('nominativo_riferimento', 'N/A')}

Partita Origine: {variazione_data.get('origine_numero', 'N/A')}
Partita Destinazione: {variazione_data.get('destinazione_numero', 'N/A')}
Comune: {variazione_data.get('comune_nome', 'N/A')}

Similarità: {variazione_data.get('similarity', 0):.1%}
Descrizione: {variazione_data.get('descrizione', 'N/A')}"""
                
                details_text.setPlainText(details)
                layout.addWidget(details_text)
                
                close_button = QPushButton("Chiudi")
                close_button.clicked.connect(dialog.accept)
                layout.addWidget(close_button)
                
                dialog.setLayout(layout)
                dialog.exec_()
    
    def _on_immobile_double_click(self, item):
        """Gestisce doppio click su immobile."""
        if item.column() == 0:
            immobile_data = item.data(Qt.UserRole)
            if immobile_data:
                similarity = immobile_data.get('similarity', 0)
                
                # Crea dialogo dettagliato per immobile
                dialog = QDialog(self)
                dialog.setWindowTitle(f"Dettagli Immobile ID {immobile_data.get('id')}")
                dialog.setModal(True)
                dialog.resize(600, 450)
                
                layout = QVBoxLayout()
                
                details_text = QTextEdit()
                details_text.setReadOnly(True)
                
                # Ottieni informazioni aggiuntive sull'immobile
                additional_info = self._get_immobile_additional_info(immobile_data.get('id'))
                
                details = f"""IMMOBILE ID {immobile_data.get('id')}

CARATTERISTICHE PRINCIPALI:
Natura: {immobile_data.get('natura', 'N/A')}
Classificazione: {immobile_data.get('classificazione', 'N/A')}
Consistenza: {immobile_data.get('consistenza', 'N/A')}
Numero Piani: {immobile_data.get('numero_piani', 'N/A')}
Numero Vani: {immobile_data.get('numero_vani', 'N/A')}

UBICAZIONE:
Località: {immobile_data.get('localita_nome', 'N/A')}
Comune: {immobile_data.get('comune_nome', 'N/A')}

PARTITA:
Numero: {immobile_data.get('numero_partita', 'N/A')}
Suffisso: {immobile_data.get('suffisso_partita', 'N/A')}
Tipo Partita: {additional_info.get('tipo_partita', 'N/A')}
Stato Partita: {additional_info.get('stato_partita', 'N/A')}

POSSESSORI:
{additional_info.get('possessori_info', 'Nessun possessore trovato')}

RICERCA:
Similarità: {similarity:.1%}
Data Creazione: {immobile_data.get('data_creazione', 'N/A')}
Data Modifica: {immobile_data.get('data_modifica', 'N/A')}"""
                
                details_text.setPlainText(details)
                layout.addWidget(details_text)
                
                # Pulsanti
                button_layout = QHBoxLayout()
                
                close_button = QPushButton("Chiudi")
                close_button.clicked.connect(dialog.accept)
                button_layout.addWidget(close_button)
                
                # Pulsante per vedere la partita completa (se disponibile)
                if immobile_data.get('numero_partita'):
                    partita_button = QPushButton("Vedi Partita Completa")
                    partita_button.clicked.connect(lambda: self._show_partita_from_immobile(immobile_data, dialog))
                    button_layout.addWidget(partita_button)
                
                layout.addLayout(button_layout)
                dialog.setLayout(layout)
                dialog.exec_()
    
    def _get_immobile_additional_info(self, immobile_id):
        """Ottiene informazioni aggiuntive sull'immobile."""
        if not immobile_id:
            return {}
        
        try:
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Query per ottenere informazioni complete sull'immobile
                    cur.execute("""
                        SELECT 
                            i.*,
                            p.tipo as tipo_partita,
                            p.stato as stato_partita,
                            p.data_impianto,
                            p.data_chiusura,
                            l.tipo as tipo_localita,
                            l.civico,
                            c.nome as comune_nome,
                            -- Possessori della partita
                            STRING_AGG(
                                DISTINCT CONCAT(pos.nome_completo, ' (', pp.titolo, ')'), 
                                ', ' ORDER BY pos.nome_completo
                            ) as possessori_info
                        FROM immobile i
                        JOIN partita p ON i.partita_id = p.id
                        JOIN localita l ON i.localita_id = l.id
                        JOIN comune c ON p.comune_id = c.id
                        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
                        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
                        WHERE i.id = %s
                        GROUP BY i.id, p.id, l.id, c.id
                    """, (immobile_id,))
                    
                    result = cur.fetchone()
                    if result:
                        return dict(result)
                    return {}
            finally:
                self.gin_search.db_manager._release_connection(conn)
        except Exception as e:
            print(f"Errore nel recupero info immobile {immobile_id}: {e}")
            return {}
    
    def _show_partita_from_immobile(self, immobile_data, parent_dialog):
        """Mostra i dettagli della partita associata all'immobile."""
        partita_info = self._get_partita_info_by_number(
            immobile_data.get('numero_partita'), 
            immobile_data.get('comune_nome')
        )
        
        if partita_info:
            self._show_partita_details_dialog(partita_info, parent_dialog)
        else:
            QMessageBox.warning(parent_dialog, "Informazione", "Impossibile recuperare i dettagli della partita.")
    
    def _on_contratto_double_click(self, item):
        """Gestisce doppio click su contratto."""
        if item.column() == 0:
            contratto_data = item.data(Qt.UserRole)
            if contratto_data:
                similarity = contratto_data.get('similarity', 0)
                
                # Crea dialogo dettagliato per contratto
                dialog = QDialog(self)
                dialog.setWindowTitle(f"Dettagli Contratto ID {contratto_data.get('id')}")
                dialog.setModal(True)
                dialog.resize(650, 500)
                
                layout = QVBoxLayout()
                
                details_text = QTextEdit()
                details_text.setReadOnly(True)
                
                # Ottieni informazioni aggiuntive sul contratto
                additional_info = self._get_contratto_additional_info(contratto_data.get('id'))
                
                details = f"""CONTRATTO ID {contratto_data.get('id')}

INFORMAZIONI PRINCIPALI:
Tipo: {contratto_data.get('tipo', 'N/A')}
Data Contratto: {contratto_data.get('data_contratto', 'N/A')}
Notaio: {contratto_data.get('notaio', 'N/A')}
Repertorio: {contratto_data.get('repertorio', 'N/A')}

VARIAZIONE COLLEGATA:
Tipo Variazione: {contratto_data.get('variazione_tipo', 'N/A')}
ID Variazione: {contratto_data.get('variazione_id', 'N/A')}
Data Variazione: {additional_info.get('data_variazione', 'N/A')}
Nominativo Riferimento: {additional_info.get('nominativo_riferimento', 'N/A')}
Numero Riferimento: {additional_info.get('numero_riferimento', 'N/A')}

PARTITE COINVOLTE:
Partita Origine: {additional_info.get('partita_origine_info', 'N/A')}
Partita Destinazione: {additional_info.get('partita_destinazione_info', 'N/A')}

NOTE:
{contratto_data.get('note', 'Nessuna nota')}

RICERCA:
Similarità: {similarity:.1%}
Data Creazione: {additional_info.get('data_creazione', 'N/A')}
Data Modifica: {additional_info.get('data_modifica', 'N/A')}"""
                
                details_text.setPlainText(details)
                layout.addWidget(details_text)
                
                # Pulsanti
                button_layout = QHBoxLayout()
                
                close_button = QPushButton("Chiudi")
                close_button.clicked.connect(dialog.accept)
                button_layout.addWidget(close_button)
                
                # Pulsante per vedere la variazione completa
                if contratto_data.get('variazione_id'):
                    variazione_button = QPushButton("Vedi Variazione Completa")
                    variazione_button.clicked.connect(lambda: self._show_variazione_from_contratto(contratto_data, dialog))
                    button_layout.addWidget(variazione_button)
                
                layout.addLayout(button_layout)
                dialog.setLayout(layout)
                dialog.exec_()
    
    def _get_contratto_additional_info(self, contratto_id):
        """Ottiene informazioni aggiuntive sul contratto."""
        if not contratto_id:
            return {}
        
        try:
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            c.*,
                            v.data_variazione,
                            v.nominativo_riferimento,
                            v.numero_riferimento,
                            po.numero_partita as numero_partita_origine,
                            co.nome as comune_origine,
                            pd.numero_partita as numero_partita_destinazione,
                            cd.nome as comune_destinazione
                        FROM contratto c
                        LEFT JOIN variazione v ON c.variazione_id = v.id
                        LEFT JOIN partita po ON v.partita_origine_id = po.id
                        LEFT JOIN comune co ON po.comune_id = co.id
                        LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
                        LEFT JOIN comune cd ON pd.comune_id = cd.id
                        WHERE c.id = %s
                    """, (contratto_id,))
                    
                    result = cur.fetchone()
                    if result:
                        info = dict(result)
                        
                        # Formatta informazioni partite
                        if info.get('numero_partita_origine'):
                            info['partita_origine_info'] = f"N. {info['numero_partita_origine']} ({info.get('comune_origine', 'N/A')})"
                        else:
                            info['partita_origine_info'] = 'N/A'
                        
                        if info.get('numero_partita_destinazione'):
                            info['partita_destinazione_info'] = f"N. {info['numero_partita_destinazione']} ({info.get('comune_destinazione', 'N/A')})"
                        else:
                            info['partita_destinazione_info'] = 'N/A'
                        
                        return info
                    return {}
            finally:
                self.gin_search.db_manager._release_connection(conn)
        except Exception as e:
            print(f"Errore nel recupero info contratto {contratto_id}: {e}")
            return {}
    
    def _show_variazione_from_contratto(self, contratto_data, parent_dialog):
        """Mostra i dettagli della variazione associata al contratto."""
        variazione_info = self._get_variazione_info_by_id(contratto_data.get('variazione_id'))
        
        if variazione_info:
            self._show_variazione_details_dialog(variazione_info, parent_dialog)
        else:
            QMessageBox.warning(parent_dialog, "Informazione", "Impossibile recuperare i dettagli della variazione.")
    
    def _on_partita_double_click(self, item):
        """Gestisce doppio click su partita."""
        if item.column() == 0:
            partita_data = item.data(Qt.UserRole)
            if partita_data:
                similarity = partita_data.get('similarity', 0)
                
                # Crea dialogo dettagliato per partita
                dialog = QDialog(self)
                dialog.setWindowTitle(f"Dettagli Partita N. {partita_data.get('numero_partita')} {partita_data.get('suffisso_partita', '')}")
                dialog.setModal(True)
                dialog.resize(700, 600)
                
                layout = QVBoxLayout()
                
                details_text = QTextEdit()
                details_text.setReadOnly(True)
                
                # Ottieni informazioni complete sulla partita
                complete_info = self._get_partita_complete_info(partita_data.get('id'))
                
                details = f"""PARTITA N. {partita_data.get('numero_partita')} {partita_data.get('suffisso_partita', '')}

INFORMAZIONI PRINCIPALI:
ID Partita: {partita_data.get('id')}
Numero: {partita_data.get('numero_partita')}
Suffisso: {partita_data.get('suffisso_partita', 'N/A')}
Tipo: {partita_data.get('tipo', 'N/A')}
Stato: {partita_data.get('stato', 'N/A')}
Comune: {partita_data.get('comune_nome', 'N/A')}

DATE:
Data Impianto: {partita_data.get('data_impianto', 'N/A')}
Data Chiusura: {partita_data.get('data_chiusura', 'N/A')}

POSSESSORI ({complete_info.get('num_possessori', 0)}):
{complete_info.get('possessori_info', 'Nessun possessore')}

IMMOBILI ({complete_info.get('num_immobili', 0)}):
{complete_info.get('immobili_info', 'Nessun immobile')}

VARIAZIONI ({complete_info.get('num_variazioni', 0)}):
{complete_info.get('variazioni_info', 'Nessuna variazione')}

RICERCA:
Similarità: {similarity:.1%}
Data Creazione: {complete_info.get('data_creazione', 'N/A')}
Data Modifica: {complete_info.get('data_modifica', 'N/A')}"""
                
                details_text.setPlainText(details)
                layout.addWidget(details_text)
                
                # Pulsanti
                button_layout = QHBoxLayout()
                
                close_button = QPushButton("Chiudi")
                close_button.clicked.connect(dialog.accept)
                button_layout.addWidget(close_button)
                
                # Pulsante per esportare dettaglio partita
                export_button = QPushButton("Esporta Dettaglio")
                export_button.clicked.connect(lambda: self._export_partita_details(partita_data, complete_info))
                button_layout.addWidget(export_button)
                
                layout.addLayout(button_layout)
                dialog.setLayout(layout)
                dialog.exec_()
    
    def _get_partita_complete_info(self, partita_id):
        """Ottiene informazioni complete sulla partita."""
        if not partita_id:
            return {}
        
        try:
            conn = self.gin_search.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    # Query per informazioni complete partita
                    cur.execute("""
                        SELECT 
                            p.*,
                            -- Conteggi
                            (SELECT COUNT(*) FROM partita_possessore pp WHERE pp.partita_id = p.id) as num_possessori,
                            (SELECT COUNT(*) FROM immobile i WHERE i.partita_id = p.id) as num_immobili,
                            (SELECT COUNT(*) FROM variazione v WHERE v.partita_origine_id = p.id OR v.partita_destinazione_id = p.id) as num_variazioni,
                            
                            -- Possessori
                            (SELECT STRING_AGG(
                                CONCAT(pos.nome_completo, ' (', pp.titolo, 
                                       CASE WHEN pp.quota IS NOT NULL THEN CONCAT(', ', pp.quota) ELSE '' END, ')'), 
                                '; ' ORDER BY pos.nome_completo
                            ) FROM partita_possessore pp 
                            JOIN possessore pos ON pp.possessore_id = pos.id 
                            WHERE pp.partita_id = p.id) as possessori_info,
                            
                            -- Immobili
                            (SELECT STRING_AGG(
                                CONCAT(i.natura, 
                                       CASE WHEN i.classificazione IS NOT NULL THEN CONCAT(' - ', i.classificazione) ELSE '' END,
                                       ' (Loc: ', l.nome, ')'), 
                                '; ' ORDER BY i.natura
                            ) FROM immobile i 
                            JOIN localita l ON i.localita_id = l.id 
                            WHERE i.partita_id = p.id) as immobili_info,
                            
                            -- Variazioni
                            (SELECT STRING_AGG(
                                CONCAT(v.tipo, ' del ', v.data_variazione,
                                       CASE WHEN v.nominativo_riferimento IS NOT NULL 
                                            THEN CONCAT(' (', v.nominativo_riferimento, ')') 
                                            ELSE '' END), 
                                '; ' ORDER BY v.data_variazione DESC
                            ) FROM variazione v 
                            WHERE v.partita_origine_id = p.id OR v.partita_destinazione_id = p.id) as variazioni_info
                            
                        FROM partita p
                        WHERE p.id = %s
                    """, (partita_id,))
                    
                    result = cur.fetchone()
                    if result:
                        return dict(result)
                    return {}
            finally:
                self.gin_search.db_manager._release_connection(conn)
        except Exception as e:
            print(f"Errore nel recupero info completa partita {partita_id}: {e}")
            return {}
    
    def _export_partita_details(self, partita_data, complete_info):
        """Esporta i dettagli completi della partita."""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dettaglio_partita_{partita_data.get('numero_partita')}_{timestamp}.txt"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write(f"DETTAGLIO PARTITA N. {partita_data.get('numero_partita')} {partita_data.get('suffisso_partita', '')}\n")
                f.write(f"Comune: {partita_data.get('comune_nome', 'N/A')}\n")
                f.write(f"ID Partita: {partita_data.get('id')}\n")
                f.write("=" * 70 + "\n")
                f.write(f"Tipo: {partita_data.get('tipo', 'N/A')}\n")
                f.write(f"Stato: {partita_data.get('stato', 'N/A')}\n")
                f.write(f"Data Impianto: {partita_data.get('data_impianto', 'N/A')}\n")
                f.write(f"Data Chiusura: {partita_data.get('data_chiusura', 'N/A')}\n\n")
                
                f.write("POSSESSORI\n")
                f.write("=" * 30 + "\n")
                if complete_info.get('possessori_info'):
                    for possessore in complete_info['possessori_info'].split('; '):
                        f.write(f"  - {possessore}\n")
                else:
                    f.write("  Nessun possessore associato.\n")
                
                f.write("\nIMMOBILI\n")
                f.write("=" * 30 + "\n")
                if complete_info.get('immobili_info'):
                    for immobile in complete_info['immobili_info'].split('; '):
                        f.write(f"  - {immobile}\n")
                else:
                    f.write("  Nessun immobile associato.\n")
                
                f.write("\nVARIAZIONI\n")
                f.write("=" * 30 + "\n")
                if complete_info.get('variazioni_info'):
                    for variazione in complete_info['variazioni_info'].split('; '):
                        f.write(f"  - {variazione}\n")
                else:
                    f.write("  Nessuna variazione associata.\n")
                
                f.write(f"\nFINE DETTAGLIO PARTITA\n")
                f.write("=" * 70 + "\n")
            
            QMessageBox.information(self, "Export Completato", f"Dettaglio partita esportato in:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Errore Export", f"Errore durante l'esportazione:\n{e}")

# ========================================================================
# FUNZIONE PER INTEGRAZIONE IN GUI_MAIN
# ========================================================================

def add_working_fuzzy_search_tab_to_main_window(main_window):
    """Aggiunge tab ricerca fuzzy funzionante alla finestra principale."""
    try:
        if hasattr(main_window, 'db_manager') and main_window.db_manager:
            fuzzy_widget = WorkingFuzzySearchWidget(main_window.db_manager, main_window)
            
            if hasattr(main_window, 'tabs'):
                main_window.tabs.addTab(fuzzy_widget, "🔍 Ricerca Completa")
            elif hasattr(main_window, 'tab_widget'):
                main_window.tab_widget.addTab(fuzzy_widget, "🔍 Ricerca Completa")
            else:
                print("❌ Nessun container tab trovato")
                return False
            
            print("✅ Tab Ricerca Fuzzy Funzionante aggiunto con successo")
            return True
        else:
            print("❌ Database manager non disponibile")
            return False
    except Exception as e:
        print(f"❌ Errore aggiunta tab ricerca fuzzy: {e}")
        import traceback
        print(f"Dettagli errore: {traceback.format_exc()}")
        return False