# ========================================================================
# WIDGET RICERCA FUZZY - CON COLLEGAMENTO AI DETTAGLI
# File: enhanced_fuzzy_widget_with_details.py  
# ========================================================================

"""
Estensione del widget ricerca fuzzy con collegamento ai dettagli delle partite
e visualizzazione completa delle informazioni di possessori e località.
"""

# [Qui vanno tutti gli import del widget precedente...]
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

# Importa l'estensione GIN
try:
    from catasto_gin_extension import extend_db_manager_with_gin, format_search_results
except ImportError:
    print("ATTENZIONE: catasto_gin_extension.py non trovato.")

# Importa i widget di dettaglio esistenti
try:
    from gui_widgets import PartitaDetailsDialog
except ImportError:
    print("ATTENZIONE: PartitaDetailsDialog non trovato in gui_widgets")
    PartitaDetailsDialog = None

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
            # Query per trovare immobili collegati alla località
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

class DettagliPossessoreDialog(QDialog):
    """Dialog per mostrare i dettagli completi di un possessore con le sue partite."""
    
    def __init__(self, possessore_data, partite_collegate, parent=None):
        super().__init__(parent)
        self.possessore_data = possessore_data
        self.partite_collegate = partite_collegate
        self.setupUI()
        
    def setupUI(self):
        self.setWindowTitle(f"Dettagli Possessore - {self.possessore_data.get('nome_completo', 'N/A')}")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # === INFORMAZIONI POSSESSORE ===
        info_group = QGroupBox("Informazioni Possessore")
        info_layout = QFormLayout(info_group)
        
        info_layout.addRow("ID:", QLabel(str(self.possessore_data.get('id', 'N/A'))))
        info_layout.addRow("Nome Completo:", QLabel(self.possessore_data.get('nome_completo', 'N/A')))
        info_layout.addRow("Cognome Nome:", QLabel(self.possessore_data.get('cognome_nome', 'N/A')))
        info_layout.addRow("Paternità:", QLabel(self.possessore_data.get('paternita', 'N/A')))
        info_layout.addRow("Comune:", QLabel(self.possessore_data.get('comune_nome', 'N/A')))
        
        layout.addWidget(info_group)
        
        # === PARTITE COLLEGATE ===
        partite_group = QGroupBox(f"Partite Collegate ({len(self.partite_collegate)})")
        partite_layout = QVBoxLayout(partite_group)
        
        self.partite_table = QTableWidget()
        self.partite_table.setColumnCount(6)
        self.partite_table.setHorizontalHeaderLabels([
            "ID Partita", "Numero", "Tipo", "Comune", "Titolo", "Quota"
        ])
        
        # Popola tabella partite
        self.partite_table.setRowCount(len(self.partite_collegate))
        for row, partita in enumerate(self.partite_collegate):
            self.partite_table.setItem(row, 0, QTableWidgetItem(str(partita.get('partita_id', ''))))
            self.partite_table.setItem(row, 1, QTableWidgetItem(str(partita.get('numero_partita', ''))))
            self.partite_table.setItem(row, 2, QTableWidgetItem(partita.get('tipo_partita', '')))
            self.partite_table.setItem(row, 3, QTableWidgetItem(partita.get('comune_nome', '')))
            self.partite_table.setItem(row, 4, QTableWidgetItem(partita.get('titolo_possesso', '')))
            self.partite_table.setItem(row, 5, QTableWidgetItem(partita.get('quota_possesso', '')))
        
        self.partite_table.resizeColumnsToContents()
        self.partite_table.setAlternatingRowColors(True)
        self.partite_table.setSelectionBehavior(QTableWidget.SelectRows)
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
        
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        actions_layout.addWidget(close_btn)
        
        partite_layout.addLayout(actions_layout)
        layout.addWidget(partite_group)
        
    def apri_dettaglio_partita(self):
        """Apre il dettaglio della partita con doppio click."""
        current_row = self.partite_table.currentRow()
        if current_row >= 0:
            partita = self.partite_collegate[current_row]
            partita_id = partita.get('partita_id')
            self._apri_dettaglio_partita_id(partita_id)
    
    def apri_dettaglio_partita_selezionata(self):
        """Apre il dettaglio della partita selezionata dal pulsante."""
        current_row = self.partite_table.currentRow()
        if current_row >= 0:
            partita = self.partite_collegate[current_row]
            partita_id = partita.get('partita_id')
            self._apri_dettaglio_partita_id(partita_id)
    
    def _apri_dettaglio_partita_id(self, partita_id):
        """Apre il dialog di dettaglio partita."""
        if PartitaDetailsDialog and hasattr(self.parent(), 'db_manager'):
            try:
                # Usa il widget esistente per mostrare i dettagli
                dettaglio_dialog = PartitaDetailsDialog(
                    self.parent().db_manager, 
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
                f"(Integrazione con PartitaDetailsDialog in corso)"
            )

class DettagliLocalitaDialog(QDialog):
    """Dialog per mostrare i dettagli di una località con gli immobili collegati."""
    
    def __init__(self, localita_data, immobili_collegati, parent=None):
        super().__init__(parent)
        self.localita_data = localita_data
        self.immobili_collegati = immobili_collegati
        self.setupUI()
        
    def setupUI(self):
        nome_localita = self.localita_data.get('nome', 'N/A')
        civico = self.localita_data.get('civico', '')
        nome_completo = f"{nome_localita} {civico}" if civico else nome_localita
        
        self.setWindowTitle(f"Dettagli Località - {nome_completo}")
        self.setMinimumSize(700, 500)
        
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
        
        layout.addWidget(info_group)
        
        # === IMMOBILI COLLEGATI ===
        immobili_group = QGroupBox(f"Immobili in questa Località ({len(self.immobili_collegati)})")
        immobili_layout = QVBoxLayout(immobili_group)
        
        self.immobili_table = QTableWidget()
        self.immobili_table.setColumnCount(7)
        self.immobili_table.setHorizontalHeaderLabels([
            "ID Immobile", "Natura", "Piani", "Vani", "Classificazione", "Partita", "Comune"
        ])
        
        # Popola tabella immobili
        self.immobili_table.setRowCount(len(self.immobili_collegati))
        for row, immobile in enumerate(self.immobili_collegati):
            self.immobili_table.setItem(row, 0, QTableWidgetItem(str(immobile.get('immobile_id', ''))))
            self.immobili_table.setItem(row, 1, QTableWidgetItem(immobile.get('natura', '')))
            self.immobili_table.setItem(row, 2, QTableWidgetItem(str(immobile.get('numero_piani', '') or '')))
            self.immobili_table.setItem(row, 3, QTableWidgetItem(str(immobile.get('numero_vani', '') or '')))
            self.immobili_table.setItem(row, 4, QTableWidgetItem(immobile.get('classificazione', '')))
            self.immobili_table.setItem(row, 5, QTableWidgetItem(f"N.{immobile.get('numero_partita', '')}"))
            self.immobili_table.setItem(row, 6, QTableWidgetItem(immobile.get('comune_nome', '')))
        
        self.immobili_table.resizeColumnsToContents()
        self.immobili_table.setAlternatingRowColors(True)
        self.immobili_table.setSelectionBehavior(QTableWidget.SelectRows)
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
        
        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(self.accept)
        actions_layout.addWidget(close_btn)
        
        immobili_layout.addLayout(actions_layout)
        layout.addWidget(immobili_group)
        
    def apri_dettaglio_partita_da_immobile(self):
        """Apre il dettaglio della partita dell'immobile con doppio click."""
        current_row = self.immobili_table.currentRow()
        if current_row >= 0:
            immobile = self.immobili_collegati[current_row]
            partita_id = immobile.get('partita_id')
            self._apri_dettaglio_partita_id(partita_id)
    
    def apri_dettaglio_partita_selezionata(self):
        """Apre il dettaglio della partita dell'immobile selezionato."""
        current_row = self.immobili_table.currentRow()
        if current_row >= 0:
            immobile = self.immobili_collegati[current_row]
            partita_id = immobile.get('partita_id')
            self._apri_dettaglio_partita_id(partita_id)
    
    def _apri_dettaglio_partita_id(self, partita_id):
        """Apre il dialog di dettaglio partita."""
        if PartitaDetailsDialog and hasattr(self.parent(), 'db_manager'):
            try:
                dettaglio_dialog = PartitaDetailsDialog(
                    self.parent().db_manager, 
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
                f"(Integrazione con PartitaDetailsDialog in corso)"
            )

# [Qui va la classe CompactFuzzySearchWidget del widget precedente, 
#  ma con le modifiche ai metodi _on_possessore_double_click e _on_localita_double_click]

class EnhancedFuzzySearchWidget(CompactFuzzySearchWidget):
    """
    Widget ricerca fuzzy potenziato con collegamento completo ai dettagli.
    Estende CompactFuzzySearchWidget aggiungendo funzionalità di dettaglio.
    """
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
        self.partite_helper = PartiteCollegate(db_manager)
        
    def _on_possessore_double_click(self, index):
        """Gestisce doppio click su possessore con dettagli completi."""
        item = self.possessori_table.item(index.row(), 0)
        if item:
            possessore_data = item.data(Qt.UserRole)
            possessore_id = possessore_data.get('id')
            
            try:
                # Recupera le partite collegate
                QApplication.setOverrideCursor(Qt.WaitCursor)
                partite_collegate = self.partite_helper.get_partite_per_possessore(possessore_id)
                QApplication.restoreOverrideCursor()
                
                # Apre il dialog dettagliato
                dettagli_dialog = DettagliPossessoreDialog(
                    possessore_data, 
                    partite_collegate, 
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
            
            try:
                # Recupera gli immobili collegati
                QApplication.setOverrideCursor(Qt.WaitCursor)
                immobili_collegati = self.partite_helper.get_immobili_per_localita(localita_id)
                QApplication.restoreOverrideCursor()
                
                # Apre il dialog dettagliato
                dettagli_dialog = DettagliLocalitaDialog(
                    localita_data, 
                    immobili_collegati, 
                    parent=self
                )
                dettagli_dialog.exec_()
                
            except Exception as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(
                    self, "Errore", 
                    f"Errore recupero dettagli località {localita_id}:\n{e}"
                )

# ========================================================================
# FUNZIONE DI INTEGRAZIONE FINALE
# ========================================================================

def add_enhanced_fuzzy_search_tab_to_main_window(main_window):
    """
    Aggiunge il tab di ricerca fuzzy potenziato con collegamenti ai dettagli.
    """
    try:
        if not hasattr(main_window, 'db_manager') or not main_window.db_manager:
            main_window.logger.warning("Database manager non disponibile per ricerca fuzzy")
            return False
            
        # Crea il widget potenziato
        fuzzy_widget = EnhancedFuzzySearchWidget(main_window.db_manager, main_window)
        
        # Aggiunge al TabWidget principale
        tab_index = main_window.tabs.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
        
        main_window.logger.info(f"Tab Ricerca Fuzzy Potenziato aggiunto all'indice {tab_index}")
        return True
        
    except Exception as e:
        main_window.logger.error(f"Errore aggiunta tab ricerca fuzzy potenziato: {e}")
        return False
