
import os,csv,sys,logging,json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from app_utils import BulkReportPDF, FPDF_AVAILABLE, _get_default_export_path, prompt_to_open_file
import pandas as pd # Importa pandas

# Importazioni PyQt5
from PyQt5.QtCore import (QDate, QDateTime, QPoint, QProcess, QSettings, 
                          QSize, QStandardPaths, Qt, QTimer, QUrl, 
                          pyqtSignal)

from PyQt5.QtGui import (QCloseEvent, QColor, QDesktopServices, QFont, 
                         QIcon, QPalette, QPixmap)

from PyQt5.QtWebEngineWidgets import QWebEngineView

from PyQt5.QtWidgets import (QAbstractItemView, QAction, QApplication, 
                             QCheckBox, QComboBox, QDateEdit, QDateTimeEdit,
                             QDialog, QDialogButtonBox, QDoubleSpinBox,
                             QFileDialog, QFormLayout, QFrame, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QInputDialog,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QMainWindow, QMenu, QMessageBox, QProgressBar,
                             QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
                             QSpinBox, QStyle, QStyleFactory, QTabWidget,
                             QTableWidget, QTableWidgetItem, QTextEdit,
                             QVBoxLayout, QWidget,QProgressDialog,QTextBrowser)
from PyQt5.QtCore import Qt, QSettings, pyqtSlot,pyqtSignal 

# Importazione commentata (da abilitare se necessario)
# from PyQt5.QtSvgWidgets import QSvgWidget



from config import (
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT, 
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA,
    COLONNE_POSSESSORI_DETTAGLI_NUM ,COLONNE_POSSESSORI_DETTAGLI_LABELS,COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM,
    COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS, COLONNE_INSERIMENTO_POSSESSORI_NUM, COLONNE_INSERIMENTO_POSSESSORI_LABELS,
    NUOVE_ETICHETTE_POSSESSORI)



# In gui_main.py, dopo le importazioni PyQt e standard:
# E le sue eccezioni se servono qui
if TYPE_CHECKING:
    # Questa importazione avviene solo per i type checker (es. MyPy), 
    # non a runtime, quindi non crea il ciclo.
    from gui_main import CatastoMainWindow 
    from catasto_db_manager import CatastoDBManager # Se serve anche per type hint

# In gui_widgets.py, dopo le importazioni PyQt e standard:
from custom_widgets import QPasswordLineEdit
from dialogs import (DBConfigDialog,DocumentViewerDialog, ModificaPossessoreDialog, PartiteComuneDialog, ModificaImmobileDialog,
                    PossessoriComuneDialog, LocalitaSelectionDialog, ModificaComuneDialog,PeriodoStoricoDetailsDialog,
                    PartitaDetailsDialog,PDFApreviewDialog,CreateUserDialog)
from dialogs import (ComuneSelectionDialog, PartitaSearchDialog, PossessoreSelectionDialog, ImmobileDialog,LocalitaSelectionDialog, 
                    DettagliLegamePossessoreDialog, UserSelectionDialog,qdate_to_datetime, datetime_to_qdate,_hash_password,_verify_password)

from app_utils import (gui_esporta_partita_pdf, gui_esporta_partita_json, gui_esporta_partita_csv,
                       gui_esporta_possessore_pdf, gui_esporta_possessore_json, gui_esporta_possessore_csv,
                       GenericTextReportPDF,FPDF_AVAILABLE, GenericTextReportPDF)
# È possibile che alcune utility (es. hashing) siano usate da dialoghi che ora sono in gui_main.py
# In tal caso, gui_main.py importerà _hash_password da app_utils.py.



# Importazione del gestore DB e eccezioni
try:
    from catasto_db_manager import CatastoDBManager, DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    # Fallback o gestione errore
    class DBMError(Exception):
        pass  # ... definizioni fallback come nel file originale
    print("ATTENZIONE: catasto_db_manager non trovato, usando eccezioni DB fallback in gui_widgets.py")
class ElencoComuniWidget(QWidget):
    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        # Stampa di debug visibile nella console all'avvio
        print("--- DEBUG: Inizializzazione di ElencoComuniWidget ---")
        
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        
        if db_manager:
            self.db_manager = db_manager
            self.logger.info(f"Widget inizializzato CORRETTAMENTE con DBManager (ID Oggetto: {id(self.db_manager)})")
        else:
            self.db_manager = None
            self.logger.error("ERRORE CRITICO: ElencoComuniWidget inizializzato SENZA un DBManager valido!")
            QMessageBox.critical(self, "Errore Widget", "Il widget dei comuni non ha ricevuto il gestore del database.")
            return

        layout = QVBoxLayout(self)

        comuni_group = QGroupBox("Elenco Comuni Registrati")
        comuni_layout = QVBoxLayout(comuni_group)

        self.filter_comuni_edit = QLineEdit()
        self.filter_comuni_edit.setPlaceholderText("Filtra per nome, provincia...")
        self.filter_comuni_edit.textChanged.connect(self.apply_filter)
        comuni_layout.addWidget(self.filter_comuni_edit)

        self.comuni_table = QTableWidget()
        self.comuni_table.setColumnCount(7) # ID, Nome, Cod. Cat., Prov., Data Ist., Data Sopp., Note
        self.comuni_table.setHorizontalHeaderLabels([
            "ID", "Nome Comune", "Cod. Catastale", "Provincia",
            "Data Istituzione", "Data Soppressione", "Note"
        ])
        self.comuni_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.comuni_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.comuni_table.setSelectionMode(QTableWidget.SingleSelection) # Importante per menu contestuale su una riga
        self.comuni_table.setAlternatingRowColors(True)
        self.comuni_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.comuni_table.setSortingEnabled(True)
        # self.comuni_table.itemDoubleClicked.connect(self.mostra_partite_del_comune) # Il doppio click può rimanere

        # Imposta la policy per il menu contestuale sulla tabella
        self.comuni_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.comuni_table.customContextMenuRequested.connect(self.apri_menu_contestuale_comune)

        comuni_layout.addWidget(self.comuni_table)

        action_buttons_layout = QHBoxLayout()
        self.btn_mostra_partite = QPushButton("Mostra Partite del Comune Selezionato")
        self.btn_mostra_partite.clicked.connect(self.azione_mostra_partite)
        action_buttons_layout.addWidget(self.btn_mostra_partite)

        self.btn_mostra_possessori = QPushButton("Mostra Possessori del Comune Selezionato")
        self.btn_mostra_possessori.clicked.connect(self.azione_mostra_possessori)
        action_buttons_layout.addWidget(self.btn_mostra_possessori)

        self.btn_mostra_localita = QPushButton("Mostra Località del Comune Selezionato")
        self.btn_mostra_localita.clicked.connect(self.azione_mostra_localita)
        action_buttons_layout.addWidget(self.btn_mostra_localita)
        
        action_buttons_layout.addStretch()
        comuni_layout.addLayout(action_buttons_layout)
        layout.addWidget(comuni_group)
        self.setLayout(layout)

         # Chiamata esplicita per caricare i dati
        self.logger.info("Chiamata a load_comuni_data() da __init__.")
        self.load_comuni_data()

    # In gui_widgets.py, dentro la classe ElencoComuniWidget

    def load_comuni_data(self):
        self.logger.info(">>> ESECUZIONE DI load_comuni_data...")
        self.comuni_table.setSortingEnabled(False)
        self.comuni_table.setRowCount(0)

        try:
            if not self.db_manager:
                self.logger.error("load_comuni_data chiamato ma self.db_manager è None!")
                return

            self.logger.info(">>> Chiamata a db_manager.get_all_comuni_details() in corso...")
            comuni_list = self.db_manager.get_all_comuni_details()
            
            # Stampa e log fondamentali per il debug
            self.logger.info(f"--- RISULTATO RICEVUTO da db_manager: Tipo={type(comuni_list)}, Lunghezza={len(comuni_list) if comuni_list is not None else 'None'} ---")
            print(f"DEBUG UI - Dati ricevuti: {comuni_list}")

            if not comuni_list:
                self.logger.warning("Nessun comune restituito dal DB manager per la visualizzazione.")
                # Mostra un messaggio all'utente direttamente nella tabella
                self.comuni_table.setRowCount(1)
                item = QTableWidgetItem("Nessun comune trovato nel database.")
                item.setTextAlignment(Qt.AlignCenter)
                self.comuni_table.setItem(0, 0, item)
                self.comuni_table.setSpan(0, 0, 1, self.comuni_table.columnCount())
                return
            self.logger.info(f">>> Inizio ciclo FOR per popolare la tabella con {len(comuni_list)} elementi.")
            self.comuni_table.setRowCount(len(comuni_list))
            for row_idx, comune in enumerate(comuni_list):
                # L'uso di .get() è sicuro e previene crash se una chiave dovesse mancare
                self.comuni_table.setItem(row_idx, 0, QTableWidgetItem(str(comune.get('id', ''))))
                self.comuni_table.setItem(row_idx, 1, QTableWidgetItem(comune.get('nome_comune', '')))
                self.comuni_table.setItem(row_idx, 2, QTableWidgetItem(comune.get('codice_catastale', '')))
                self.comuni_table.setItem(row_idx, 3, QTableWidgetItem(comune.get('provincia', '')))
                
                data_ist = comune.get('data_istituzione')
                self.comuni_table.setItem(row_idx, 4, QTableWidgetItem(str(data_ist) if data_ist else ''))
                
                data_soppr = comune.get('data_soppressione')
                self.comuni_table.setItem(row_idx, 5, QTableWidgetItem(str(data_soppr) if data_soppr else ''))
                
                self.comuni_table.setItem(row_idx, 6, QTableWidgetItem(comune.get('note', '')))
            
            self.comuni_table.resizeColumnsToContents()
            self.logger.info(">>> Fine ciclo FOR.")

        except Exception as e:
            self.logger.error(f"Errore imprevisto durante il popolamento della tabella comuni: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore imprevisto: {e}")
        finally:
            self.comuni_table.setSortingEnabled(True)
            self.logger.info(">>> load_comuni_data terminato.")

    def apply_filter(self):
        """Filtra le righe della tabella in base al testo inserito."""
        filter_text = self.filter_comuni_edit.text().strip().lower()
        for row in range(self.comuni_table.rowCount()):
            row_visible = False
            if not filter_text:  # Se il filtro è vuoto, mostra tutte le righe
                row_visible = True
            else:
                for col in range(self.comuni_table.columnCount()):
                    item = self.comuni_table.item(row, col)
                    if item and filter_text in item.text().lower():
                        row_visible = True
                        break
            self.comuni_table.setRowHidden(row, not row_visible)
        
        filter_text = self.filter_comuni_edit.text().strip().lower()
        for row in range(self.comuni_table.rowCount()):
            row_visible = False
            if not filter_text:
                row_visible = True
            else:
                for col in range(self.comuni_table.columnCount()):
                    item = self.comuni_table.item(row, col)
                    if item and filter_text in item.text().lower():
                        row_visible = True
                        break
            self.comuni_table.setRowHidden(row, not row_visible)
    
    def _get_comune_info_from_row(self, row: int) -> Optional[Tuple[int, str]]:
        """Helper per ottenere ID e nome del comune da una specifica riga."""
        try:
            comune_id_item = self.comuni_table.item(row, 0) # Colonna ID
            nome_comune_item = self.comuni_table.item(row, 1) # Colonna Nome Comune
            if comune_id_item and nome_comune_item and comune_id_item.text().isdigit():
                return int(comune_id_item.text()), nome_comune_item.text()
        except Exception as e:
            self.logger.error(f"Errore nel recuperare info comune dalla riga {row}: {e}")
        return None

    def _get_selected_comune_info_from_table(self) -> Optional[Tuple[int, str]]:
        """Helper per ottenere ID e nome del comune attualmente selezionato nella tabella."""
        current_row = self.comuni_table.currentRow()
        if current_row < 0:
            # Nessuna riga selezionata, ma il menu contestuale potrebbe essere stato attivato su una riga specifica
            # Questo metodo è più per i pulsanti che dipendono da una selezione esplicita.
            return None 
        return self._get_comune_info_from_row(current_row)
    
    

    def _get_selected_comune_info(self) -> Optional[Tuple[int, str]]:
        """Helper per ottenere ID e nome del comune correntemente selezionato nella tabella."""
        selected_items = self.comuni_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione",
                                "Seleziona un comune dalla tabella.")
            return None

        # selectedItems può dare più item se la selezione non è per riga
        row = self.comuni_table.currentRow()
        # currentRow è più sicuro per single row selection
        if row < 0:  # Nessuna riga effettivamente selezionata
            QMessageBox.warning(self, "Nessuna Selezione",
                                "Seleziona un comune dalla tabella.")
            return None

        try:
            comune_id_item = self.comuni_table.item(row, 0)  # Colonna ID
            nome_comune_item = self.comuni_table.item(
                row, 1)  # Colonna Nome Comune

            if comune_id_item and nome_comune_item:
                comune_id = int(comune_id_item.text())
                nome_comune = nome_comune_item.text()
                return comune_id, nome_comune
            else:
                QMessageBox.warning(
                    self, "Errore Selezione", "Impossibile recuperare ID o nome del comune dalla riga.")
                return None
        except ValueError:
            QMessageBox.warning(self, "Errore Dati",
                                "L'ID del comune non è un numero valido.")
            return None
        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore in _get_selected_comune_info: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore", f"Si è verificato un errore imprevisto: {e}")
            return None

    # Questo è per il doppio click
    def mostra_partite_del_comune(self, item: QTableWidgetItem):
        """Apre un dialogo con le partite del comune selezionato tramite doppio click."""
        # Questa funzione ora può usare l'helper se item è valido,
        # o mantenere la sua logica se item è il modo primario per ottenere la riga.
        if not item:
            return
        row = item.row()
        # ... (resto della logica di mostra_partite_del_comune come prima, usando 'row' per prendere ID e nome)
        try:
            comune_id_item = self.comuni_table.item(row, 0)
            nome_comune_item = self.comuni_table.item(row, 1)
            if comune_id_item and nome_comune_item:
                comune_id = int(comune_id_item.text())
                nome_comune = nome_comune_item.text()
                dialog = PartiteComuneDialog(
                    self.db_manager, comune_id, nome_comune, self)
                dialog.exec_()
        except ValueError:
            QMessageBox.warning(self, "Errore Dati",
                                "L'ID del comune non è un numero valido.")
        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore in mostra_partite_del_comune: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore", f"Errore: {e}")
    def apri_menu_contestuale_comune(self, position: QPoint):
        index = self.comuni_table.indexAt(position)
        if not index.isValid(): return
        row = index.row()
        comune_info = self._get_comune_info_from_row(row)
        if not comune_info: return
        comune_id_selezionato, nome_comune_selezionato = comune_info
        
        menu = QMenu(self.comuni_table)
        
       # ... (azioni esistenti per Visualizza Partite, Possessori, Località) ...
        action_vedi_partite = menu.addAction(QApplication.style().standardIcon(QStyle.SP_FileDialogContentsView), "Visualizza Partite")
        action_vedi_partite.triggered.connect(lambda: self._slot_vedi_partite_comune(comune_id_selezionato, nome_comune_selezionato))
        
        action_vedi_possessori = menu.addAction(QApplication.style().standardIcon(QStyle.SP_DirLinkIcon), "Visualizza Possessori")
        action_vedi_possessori.triggered.connect(lambda: self._slot_vedi_possessori_comune(comune_id_selezionato, nome_comune_selezionato))

        action_vedi_localita = menu.addAction(QApplication.style().standardIcon(QStyle.SP_DirHomeIcon), "Visualizza Località")
        action_vedi_localita.triggered.connect(lambda: self._slot_vedi_localita_comune(comune_id_selezionato, nome_comune_selezionato))
        
        menu.addSeparator()

        # --- NUOVA AZIONE PER MODIFICA COMUNE ---
         # Azione 4: Modifica Dati Comune (senza icona)
        action_modifica_comune = menu.addAction("Modifica Dati Comune")
        action_modifica_comune.triggered.connect(
            lambda: self._slot_modifica_dati_comune(comune_id_selezionato)
        )
        
        menu.exec_(self.comuni_table.viewport().mapToGlobal(position))

    # --- Slot per le azioni del menu contestuale (e dei pulsanti) ---
    # NUOVO SLOT per gestire l'azione di modifica
    def _slot_modifica_dati_comune(self, comune_id: int):
        self.logger.info(f"Menu contestuale: richiesta modifica per comune ID {comune_id}")
        # Assicurati che ModificaComuneDialog sia importato
        dialog = ModificaComuneDialog(self.db_manager, comune_id, self) # self è il parent
        if dialog.exec_() == QDialog.Accepted:
            self.logger.info(f"Dati del comune ID {comune_id} modificati. Aggiornamento lista comuni.")
            self.load_comuni_data() # Ricarica la tabella per mostrare le modifiche
        else:
            self.logger.info(f"Modifica del comune ID {comune_id} annullata dall'utente.")
    def _slot_vedi_partite_comune(self, comune_id: int, nome_comune: str):
        self.logger.info(f"Azione: Visualizza partite per comune ID {comune_id} ('{nome_comune}')")
        dialog = PartiteComuneDialog(self.db_manager, comune_id, nome_comune, self)
        dialog.exec_()

    def _slot_vedi_possessori_comune(self, comune_id: int, nome_comune: str):
        self.logger.info(f"Azione: Visualizza possessori per comune ID {comune_id} ('{nome_comune}')")
        dialog = PossessoriComuneDialog(self.db_manager, comune_id, nome_comune, self)
        dialog.exec_()

    def _slot_vedi_localita_comune(self, comune_id: int, nome_comune: str):
        self.logger.info(f"Azione: Visualizza località per comune ID {comune_id} ('{nome_comune}')")
        dialog = LocalitaSelectionDialog(self.db_manager, comune_id, self, selection_mode=False)
        dialog.setWindowTitle(f"Località del Comune di {nome_comune}")
        dialog.exec_()

     # Metodi per i pulsanti esterni (possono riutilizzare gli slot)
    def azione_mostra_partite(self):
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            self._slot_vedi_partite_comune(selected_info[0], selected_info[1])
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")

    def azione_mostra_possessori(self):
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            self._slot_vedi_possessori_comune(selected_info[0], selected_info[1])
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")
            
    def azione_mostra_localita(self):
        selected_info = self._get_selected_comune_info_from_table()
        if selected_info:
            self._slot_vedi_localita_comune(selected_info[0], selected_info[1])
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona un comune dalla tabella.")
            
    # Il vecchio _get_selected_comune_info è stato rinominato e ora si basa sulla selezione corrente
    # Il vecchio mostra_partite_del_comune (da doppio click) può essere rimosso o adattato per usare _get_comune_info_from_row
    # Se vuoi mantenere il doppio click:
    # def mostra_partite_del_comune(self, item: QTableWidgetItem):
    #     if not item: return
    #     comune_info = self._get_comune_info_from_row(item.row())
    #     if comune_info:
    #         self._slot_vedi_partite_comune(comune_info[0], comune_info[1])

class RicercaPartiteWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(RicercaPartiteWidget, self).__init__(parent)
        self.db_manager = db_manager

        layout = QVBoxLayout()

        # Criteri di ricerca
        criteria_group = QGroupBox("Criteri di Ricerca")
        criteria_layout = QGridLayout()

        # Comune
        comune_label = QLabel("Comune:")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_id = None
        self.comune_display = QLabel("Nessun comune selezionato")
        self.clear_comune_button = QPushButton("Cancella")
        self.clear_comune_button.clicked.connect(self.clear_comune)

        criteria_layout.addWidget(comune_label, 0, 0)
        criteria_layout.addWidget(self.comune_button, 0, 1)
        criteria_layout.addWidget(self.comune_display, 0, 2)
        criteria_layout.addWidget(self.clear_comune_button, 0, 3)

        # Numero partita
        numero_label = QLabel("Numero Partita:")
        self.numero_edit = QSpinBox()
        self.numero_edit.setMinimum(0)
        self.numero_edit.setMaximum(9999)
        self.numero_edit.setSpecialValueText("Qualsiasi")

        criteria_layout.addWidget(numero_label, 1, 0)
        criteria_layout.addWidget(self.numero_edit, 1, 1)

        # Possessore
        possessore_label = QLabel("Nome Possessore:")
        self.possessore_edit = QLineEdit()
        self.possessore_edit.setPlaceholderText("Qualsiasi possessore")

        criteria_layout.addWidget(possessore_label, 2, 0)
        criteria_layout.addWidget(self.possessore_edit, 2, 1, 1, 3)

        # Natura immobile
        natura_label = QLabel("Natura Immobile:")
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Qualsiasi natura immobile")

        criteria_layout.addWidget(natura_label, 3, 0)
        criteria_layout.addWidget(self.natura_edit, 3, 1, 1, 3)

        criteria_group.setLayout(criteria_layout)
        layout.addWidget(criteria_group)

        # Pulsante Ricerca
        search_button = QPushButton("Cerca Partite")
        search_button.clicked.connect(self.do_search)
        layout.addWidget(search_button)

        # Risultati
        results_group = QGroupBox("Risultati")
        results_layout = QVBoxLayout()

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(
            ["ID", "Comune", "Numero", "Tipo", "Stato"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)

        results_layout.addWidget(self.results_table)

        # Dettagli partita selezionata
        self.detail_button = QPushButton("Mostra Dettagli Partita")
        self.detail_button.clicked.connect(self.show_details)
        results_layout.addWidget(self.detail_button)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        self.setLayout(layout)

    def select_comune(self):
        """Apre il selettore di comuni."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)

    def clear_comune(self):
        """Cancella il comune selezionato."""
        self.comune_id = None
        self.comune_display.setText("Nessun comune selezionato")

    def do_search(self):
        """Esegue la ricerca partite in base ai criteri."""
        comune_id = self.comune_id
        numero_partita_val = self.numero_edit.value()
        numero_partita = numero_partita_val if numero_partita_val > 0 and self.numero_edit.text(
        ) != self.numero_edit.specialValueText() else None

        possessore = self.possessore_edit.text().strip() or None
        natura = self.natura_edit.text().strip() or None

        # --- Stampa di DEBUG dei parametri inviati ---
        logging.getLogger("CatastoGUI").debug(
            f"RicercaPartiteWidget.do_search - Parametri inviati al DBManager:")
        logging.getLogger("CatastoGUI").debug(
            f"  comune_id: {comune_id} (tipo: {type(comune_id)})")
        logging.getLogger("CatastoGUI").debug(
            f"  numero_partita: {numero_partita} (tipo: {type(numero_partita)})")
        logging.getLogger("CatastoGUI").debug(
            f"  possessore: '{possessore}' (tipo: {type(possessore)})")
        logging.getLogger("CatastoGUI").debug(
            f"  immobile_natura: '{natura}' (tipo: {type(natura)})")
        # --- Fine Stampa di DEBUG ---

        try:
            partite = self.db_manager.search_partite(
                comune_id=comune_id,
                numero_partita=numero_partita,
                possessore=possessore,
                immobile_natura=natura
            )

            # --- Stampa di DEBUG dei risultati ricevuti ---
            logging.getLogger("CatastoGUI").debug(
                f"RicercaPartiteWidget.do_search - Risultati ricevuti dal DBManager (tipo: {type(partite)}):")
            if partite is not None:  # Controlla se partite è None prima di len()
                logging.getLogger("CatastoGUI").debug(
                    f"  Numero di partite ricevute: {len(partite)}")
                # Se vuoi vedere i primi risultati per debug (attenzione con dati sensibili):
                # for i, p_item in enumerate(partite[:3]): # Logga al massimo i primi 3
                #    logging.getLogger("CatastoGUI").debug(f"    Partita {i}: {p_item}")
            else:
                logging.getLogger("CatastoGUI").debug(
                    "  Nessun risultato (variabile 'partite' è None).")
            # --- Fine Stampa di DEBUG ---

            # Pulisce la tabella prima di popolarla
            self.results_table.setRowCount(0)

            if partite:  # Verifica se la lista 'partite' non è vuota
                self.results_table.setRowCount(len(partite))
                # Usa nomi variabili chiari
                for row_idx, partita_data in enumerate(partite):
                    # Popolamento tabella come da suo codice esistente
                    self.results_table.setItem(
                        row_idx, 0, QTableWidgetItem(str(partita_data.get('id', ''))))
                    self.results_table.setItem(row_idx, 1, QTableWidgetItem(
                        partita_data.get('comune_nome', '')))
                    self.results_table.setItem(row_idx, 2, QTableWidgetItem(
                        str(partita_data.get('numero_partita', ''))))
                    self.results_table.setItem(
                        row_idx, 3, QTableWidgetItem(partita_data.get('tipo', '')))
                    self.results_table.setItem(
                        row_idx, 4, QTableWidgetItem(partita_data.get('stato', '')))
                self.results_table.resizeColumnsToContents()  # Adatta le colonne al contenuto
                QMessageBox.information(
                    self, "Ricerca Completata", f"Trovate {len(partite)} partite corrispondenti ai criteri.")
            else:
                logging.getLogger("CatastoGUI").info(
                    "RicercaPartiteWidget.do_search - Nessuna partita trovata o la lista risultati è vuota.")
                QMessageBox.information(
                    self, "Ricerca Completata", "Nessuna partita trovata con i criteri specificati.")

        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore imprevisto durante RicercaPartiteWidget.do_search: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore di Ricerca", f"Si è verificato un errore imprevisto durante la ricerca: {e}")

    def show_details(self):
        """Mostra i dettagli della partita selezionata."""
        # Ottiene l'ID della partita selezionata
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Attenzione",
                                "Seleziona una partita dalla lista.")
            return

        # Ottiene l'ID dalla prima colonna della riga selezionata
        row = selected_items[0].row()
        partita_id_item = self.results_table.item(row, 0)

        if partita_id_item and partita_id_item.text().isdigit():
            partita_id = int(partita_id_item.text())

            # Ottiene i dettagli della partita
            partita = self.db_manager.get_partita_details(partita_id)

            if partita:
                # Crea e mostra una finestra di dialogo per i dettagli
                details_dialog = PartitaDetailsDialog(partita, self)
                details_dialog.exec_()
            else:
                QMessageBox.warning(
                    self, "Errore", f"Non è stato possibile recuperare i dettagli della partita ID {partita_id}.")
        else:
            QMessageBox.warning(self, "Errore", "ID partita non valido.")
    # ======================================================================
    # ECCO LO SLOT CHE STAI CERCANDO DI POSIZIONARE
    # È un metodo della stessa classe che contiene il pulsante e la tabella.
    # ======================================================================
    @pyqtSlot()
    def apri_dialog_modifica_immobile(self):
        """
        Slot che viene eseguito quando si clicca il pulsante "Modifica".
        Apre il dialogo di modifica per l'immobile selezionato.
        """
        selected_rows = self.tabella_immobili.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Nessuna Selezione", "Per favore, seleziona un immobile dalla tabella da modificare.")
            return

        # Prendi la riga selezionata (anche se sono multiple, consideriamo solo la prima)
        riga_selezionata = selected_rows[0].row()
        
        # Recupera l'ID dell'immobile che abbiamo salvato in precedenza
        primo_item_nella_riga = self.tabella_immobili.item(riga_selezionata, 0)
        if not primo_item_nella_riga:
            QMessageBox.critical(self, "Errore", "Impossibile recuperare i dati dalla riga selezionata.")
            return
            
        immobile_id = primo_item_nella_riga.data(Qt.UserRole)

        # Crea e lancia il dialogo, passando tutti i parametri necessari
        dialog = ModificaImmobileDialog(
            db_manager=self.db_manager,
            immobile_id=immobile_id,
            comune_id_partita=self.comune_id_attuale, # Usa l'ID del comune di questo widget
            parent=self  # Il parent è questo widget stesso
        )

        # Esegui il dialogo. Il codice si ferma qui finché il dialogo non viene chiuso.
        # Usiamo exec_() per compatibilità con tutti i nomi
        if dialog.exec_() == QDialog.Accepted:
            # Se l'utente ha premuto "Salva" e le modifiche sono state salvate,
            # aggiorna la tabella per mostrare i nuovi dati.
            print("Modifiche salvate. Aggiornamento della vista in corso...")
            self.carica_dati_immobili()
        else:
            print("Operazione di modifica annullata dall'utente.")


class RicercaAvanzataImmobiliWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_comune_id: Optional[int] = None
        self.selected_localita_id: Optional[int] = None

        main_layout = QVBoxLayout(self)

        criteria_group = QGroupBox("Criteri di Ricerca Avanzata Immobili")
        criteria_layout = QGridLayout(criteria_group)

        # Riga 0: Comune
        criteria_layout.addWidget(QLabel("Comune:"), 0, 0)
        self.comune_display_label = QLabel("Qualsiasi comune")
        criteria_layout.addWidget(self.comune_display_label, 0, 1)
        self.btn_seleziona_comune = QPushButton("Seleziona...")
        self.btn_seleziona_comune.clicked.connect(
            self._seleziona_comune_per_ricerca)
        criteria_layout.addWidget(self.btn_seleziona_comune, 0, 2)
        self.btn_reset_comune = QPushButton("Reset")
        self.btn_reset_comune.clicked.connect(self._reset_comune_ricerca)
        criteria_layout.addWidget(self.btn_reset_comune, 0, 3)

        # Riga 1: Località
        criteria_layout.addWidget(QLabel("Località:"), 1, 0)
        self.localita_display_label = QLabel("Qualsiasi località")
        criteria_layout.addWidget(self.localita_display_label, 1, 1)
        self.btn_seleziona_localita = QPushButton("Seleziona...")
        self.btn_seleziona_localita.clicked.connect(
            self._seleziona_localita_per_ricerca)
        self.btn_seleziona_localita.setEnabled(False)
        criteria_layout.addWidget(self.btn_seleziona_localita, 1, 2)
        self.btn_reset_localita = QPushButton("Reset")
        self.btn_reset_localita.clicked.connect(self._reset_localita_ricerca)
        criteria_layout.addWidget(self.btn_reset_localita, 1, 3)

        # Riga 2: Natura e Classificazione
        criteria_layout.addWidget(QLabel("Natura Immobile:"), 2, 0)
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText(
            "Es. Casa, Terreno (lascia vuoto per qualsiasi)")
        criteria_layout.addWidget(self.natura_edit, 2, 1, 1, 3)

        criteria_layout.addWidget(QLabel("Classificazione:"), 3, 0)
        self.classificazione_edit = QLineEdit()
        self.classificazione_edit.setPlaceholderText(
            "Es. Abitazione civile, Oliveto (lascia vuoto per qualsiasi)")
        criteria_layout.addWidget(self.classificazione_edit, 3, 1, 1, 3)

        # Riga 4: Consistenza (come testo per ricerca parziale)
        criteria_layout.addWidget(QLabel("Testo Consistenza:"), 4, 0)
        self.consistenza_search_edit = QLineEdit()
        self.consistenza_search_edit.setPlaceholderText(
            "Es. 120, are, vani (ricerca parziale)")
        criteria_layout.addWidget(self.consistenza_search_edit, 4, 1, 1, 3)

        # Riga 5: Numero Piani
        criteria_layout.addWidget(QLabel("Piani Min:"), 5, 0)
        self.piani_min_spinbox = QSpinBox()
        self.piani_min_spinbox.setMinimum(0)
        self.piani_min_spinbox.setValue(0)
        criteria_layout.addWidget(self.piani_min_spinbox, 5, 1)
        criteria_layout.addWidget(QLabel("Piani Max:"), 5, 2)
        self.piani_max_spinbox = QSpinBox()
        self.piani_max_spinbox.setMinimum(0)
        self.piani_max_spinbox.setMaximum(99)
        self.piani_max_spinbox.setValue(0)
        self.piani_max_spinbox.setSpecialValueText("Qualsiasi")
        criteria_layout.addWidget(self.piani_max_spinbox, 5, 3)

        # Riga 6: Numero Vani
        criteria_layout.addWidget(QLabel("Vani Min:"), 6, 0)
        self.vani_min_spinbox = QSpinBox()
        self.vani_min_spinbox.setMinimum(0)
        self.vani_min_spinbox.setValue(0)
        criteria_layout.addWidget(self.vani_min_spinbox, 6, 1)
        criteria_layout.addWidget(QLabel("Vani Max:"), 6, 2)
        self.vani_max_spinbox = QSpinBox()
        self.vani_max_spinbox.setMinimum(0)
        self.vani_max_spinbox.setMaximum(999)
        self.vani_max_spinbox.setValue(0)
        self.vani_max_spinbox.setSpecialValueText("Qualsiasi")
        criteria_layout.addWidget(self.vani_max_spinbox, 6, 3)

        # Riga 7: Nome Possessore (NUOVO CAMPO)
        criteria_layout.addWidget(QLabel("Nome Possessore:"), 7, 0)
        self.nome_possessore_edit = QLineEdit()
        self.nome_possessore_edit.setPlaceholderText(
            "Ricerca parziale nome possessore (lascia vuoto per qualsiasi)")
        criteria_layout.addWidget(self.nome_possessore_edit, 7, 1, 1, 3)

        main_layout.addWidget(criteria_group)

        self.btn_esegui_ricerca_immobili = QPushButton(
            "Esegui Ricerca Immobili")
        self.btn_esegui_ricerca_immobili.setIcon(
            QApplication.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.btn_esegui_ricerca_immobili.clicked.connect(
            self._esegui_ricerca_effettiva)
        main_layout.addWidget(self.btn_esegui_ricerca_immobili)

        results_group = QGroupBox("Risultati Ricerca")
        results_layout = QVBoxLayout(results_group)
        self.risultati_immobili_table = QTableWidget()
        # Colonne basate sulla funzione SQL cerca_immobili_avanzato
        self.risultati_immobili_table.setColumnCount(10)
        self.risultati_immobili_table.setHorizontalHeaderLabels([
            "ID Imm.", "Part. N.", "Comune", "Località", "Natura",
            "Class.", "Consist.", "Piani", "Vani", "Possessori"
        ])
        self.risultati_immobili_table.setEditTriggers(
            QTableWidget.NoEditTriggers)
        self.risultati_immobili_table.setSelectionBehavior(
            QTableWidget.SelectRows)
        self.risultati_immobili_table.setAlternatingRowColors(True)
        self.risultati_immobili_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)  # ResizeToContents
        self.risultati_immobili_table.horizontalHeader(
        ).setStretchLastSection(True)  # Ultima colonna stretch
        self.risultati_immobili_table.setSortingEnabled(True)
        results_layout.addWidget(self.risultati_immobili_table)
        main_layout.addWidget(results_group)

        self.setLayout(main_layout)

    def _seleziona_comune_per_ricerca(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_comune_id:
            self.selected_comune_id = dialog.selected_comune_id
            self.comune_display_label.setText(
                f"{dialog.selected_comune_name} (ID: {self.selected_comune_id})")
            self.btn_seleziona_localita.setEnabled(True)
            self._reset_localita_ricerca()
        elif not self.selected_comune_id:
            self.comune_display_label.setText("Qualsiasi comune")
            self.btn_seleziona_localita.setEnabled(False)

    def _reset_comune_ricerca(self):
        self.selected_comune_id = None
        self.comune_display_label.setText("Qualsiasi comune")
        self.btn_seleziona_localita.setEnabled(False)
        self._reset_localita_ricerca()

    def _seleziona_localita_per_ricerca(self):
        if not self.selected_comune_id:
            QMessageBox.warning(
                self, "Comune Mancante", "Seleziona prima un comune per filtrare le località.")
            return

        # Apre LocalitaSelectionDialog in MODALITÀ SELEZIONE
        dialog = LocalitaSelectionDialog(self.db_manager, self.selected_comune_id, self,
                                         selection_mode=True)

        if dialog.exec_() == QDialog.Accepted:  # Se l'utente ha premuto "Seleziona" nel dialogo
            if dialog.selected_localita_id is not None and dialog.selected_localita_name is not None:
                self.selected_localita_id = dialog.selected_localita_id
                self.localita_display_label.setText(
                    f"{dialog.selected_localita_name} (ID: {self.selected_localita_id})")
                logging.getLogger("CatastoGUI").info(
                    f"RicercaAvanzataImmobili: Località selezionata ID: {self.selected_localita_id}, Nome: {dialog.selected_localita_name}")
            else:
                # Questo caso è improbabile se _conferma_selezione funziona, ma per sicurezza
                logging.getLogger("CatastoGUI").warning(
                    "RicercaAvanzataImmobili: LocalitaSelectionDialog accettato ma nessun ID/nome località valido è stato restituito.")
                # Potrebbe essere utile resettare qui, o lasciare la selezione precedente.
                # self._reset_localita_ricerca()
        # else: # Dialogo annullato (premuto "Annulla" o chiuso)
            # Non fare nulla, la selezione precedente (o nessuna selezione) rimane.
            # Non è necessario chiamare self._reset_localita_ricerca() a meno che non sia il comportamento desiderato.
            logging.getLogger("CatastoGUI").info(
                "Selezione località annullata o dialogo chiuso.")

    def _reset_localita_ricerca(self):
        self.selected_localita_id = None
        self.localita_display_label.setText("Qualsiasi località")

    def _esegui_ricerca_effettiva(self):
        p_comune_id = self.selected_comune_id
        p_localita_id = self.selected_localita_id
        p_natura = self.natura_edit.text().strip() or None
        p_classificazione = self.classificazione_edit.text().strip() or None
        # Campo unico per ricerca testuale consistenza
        p_consistenza_search = self.consistenza_search_edit.text().strip() or None

        p_piani_min = self.piani_min_spinbox.value(
        ) if self.piani_min_spinbox.value() > 0 else None
        p_piani_max = self.piani_max_spinbox.value() if self.piani_max_spinbox.value(
        ) != 0 else None  # 0 è speciale "Qualsiasi"

        p_vani_min = self.vani_min_spinbox.value(
        ) if self.vani_min_spinbox.value() > 0 else None
        p_vani_max = self.vani_max_spinbox.value(
        ) if self.vani_max_spinbox.value() != 0 else None

        p_nome_possessore = self.nome_possessore_edit.text().strip() or None

        # --- STAMPE DI DEBUG DA AGGIUNGERE/DECOMMENTARE ---
        print("-" * 30)
        print("DEBUG GUI: Parametri inviati a ricerca_avanzata_immobili_gui:")
        print(f"  comune_id: {p_comune_id} (tipo: {type(p_comune_id)})")
        print(f"  localita_id: {p_localita_id} (tipo: {type(p_localita_id)})")
        print(f"  natura_search: '{p_natura}' (tipo: {type(p_natura)})")
        print(
            f"  classificazione_search: '{p_classificazione}' (tipo: {type(p_classificazione)})")
        print(
            f"  consistenza_search: '{p_consistenza_search}' (tipo: {type(p_consistenza_search)})")
        print(f"  piani_min: {p_piani_min} (tipo: {type(p_piani_min)})")
        print(f"  piani_max: {p_piani_max} (tipo: {type(p_piani_max)})")
        print(f"  vani_min: {p_vani_min} (tipo: {type(p_vani_min)})")
        print(f"  vani_max: {p_vani_max} (tipo: {type(p_vani_max)})")
        print(
            f"  nome_possessore_search: '{p_nome_possessore}' (tipo: {type(p_nome_possessore)})")
        print("-" * 30)
        # --- FINE STAMPE DI DEBUG ---

        try:
            immobili_trovati = self.db_manager.ricerca_avanzata_immobili_gui(
                comune_id=p_comune_id,
                localita_id=p_localita_id,
                natura_search=p_natura,
                classificazione_search=p_classificazione,
                consistenza_search=p_consistenza_search,
                piani_min=p_piani_min,
                piani_max=p_piani_max,
                vani_min=p_vani_min,
                vani_max=p_vani_max,
                nome_possessore_search=p_nome_possessore,
                data_inizio_possesso_search=None,  # Non ancora in GUI
                data_fine_possesso_search=None    # Non ancora in GUI
            )

            self.risultati_immobili_table.setRowCount(0)
            if immobili_trovati:
                self.risultati_immobili_table.setRowCount(
                    len(immobili_trovati))
                for row_idx, immobile in enumerate(immobili_trovati):
                    col = 0
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(str(immobile.get('id_immobile', ''))))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(str(immobile.get('numero_partita', ''))))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('comune_nome', '')))
                    col += 1
                    localita_display = f"{immobile.get('localita_nome', '')}"
                    if immobile.get('civico'):
                        localita_display += f", {immobile.get('civico')}"
                    if immobile.get('localita_tipo'):
                        localita_display += f" ({immobile.get('localita_tipo')})"
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(localita_display.strip()))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('natura', '')))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('classificazione', '')))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('consistenza', '')))
                    col += 1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(str(
                        immobile.get('numero_piani', '')) if immobile.get('numero_piani') is not None else ''))
                    col += 1
                    self.risultati_immobili_table.setItem(row_idx, col, QTableWidgetItem(str(
                        immobile.get('numero_vani', '')) if immobile.get('numero_vani') is not None else ''))
                    col += 1
                    self.risultati_immobili_table.setItem(
                        row_idx, col, QTableWidgetItem(immobile.get('possessori_attuali', '')))
                    col += 1  # Campo dalla funzione SQL

                # self.risultati_immobili_table.resizeColumnsToContents() # Potrebbe essere lento con molti dati
                QMessageBox.information(
                    self, "Ricerca Completata", f"Trovati {len(immobili_trovati)} immobili.")
            else:
                QMessageBox.information(
                    self, "Ricerca Completata", "Nessun immobile trovato con i criteri specificati.")
        except AttributeError as ae:
            logging.getLogger("CatastoGUI").error(
                f"Metodo di ricerca immobili non trovato nel db_manager: {ae}", exc_info=True)
            QMessageBox.critical(
                self, "Errore Interno", f"Funzionalità di ricerca non implementata correttamente nel gestore DB: {ae}")
        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore durante la ricerca avanzata immobili: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Ricerca",
                                 f"Si è verificato un errore imprevisto: {e}")

# In gui_widgets.py, SOSTITUISCI l'intera classe InserimentoComuneWidget con questa:

class InserimentoComuneWidget(QWidget):
    comune_appena_inserito = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None,
                 db_manager: Optional['CatastoDBManager'] = None,
                 utente_attuale_info: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.utente_attuale_info = utente_attuale_info
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self._data_loaded = False
        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_group = QGroupBox("Dati del Nuovo Comune")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)

        # --- Campi del form aggiornati ---
        self.nome_comune_edit = QLineEdit()
        form_layout.addRow("Nome Comune (*):", self.nome_comune_edit)
        
        self.provincia_edit = QLineEdit("SV")
        self.provincia_edit.setMaxLength(100)
        form_layout.addRow("Provincia (*):", self.provincia_edit)

        self.regione_edit = QLineEdit()
        self.regione_edit.setMaxLength(100)
        form_layout.addRow("Regione (*):", self.regione_edit)

        self.codice_catastale_edit = QLineEdit()
        self.codice_catastale_edit.setPlaceholderText("Es. A123 (opzionale)")
        form_layout.addRow("Codice Catastale:", self.codice_catastale_edit)
        
        # --- NUOVA GESTIONE PER DATA ISTITUZIONE (FACOLTATIVA) ---
        self.data_istituzione_check = QCheckBox("Imposta data istituzione")
        self.data_istituzione_edit = QDateEdit(calendarPopup=True)
        self.data_istituzione_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_istituzione_edit.setEnabled(False)
        self.data_istituzione_check.toggled.connect(self.data_istituzione_edit.setEnabled) # Collega il check al campo data
        data_istituzione_layout = QHBoxLayout(); data_istituzione_layout.addWidget(self.data_istituzione_check); data_istituzione_layout.addWidget(self.data_istituzione_edit)
        form_layout.addRow("Data Istituzione:", data_istituzione_layout)
        
        # --- NUOVA GESTIONE PER DATA SOPPRESSIONE (FACOLTATIVA) ---
        self.data_soppressione_check = QCheckBox("Imposta data soppressione")
        self.data_soppressione_edit = QDateEdit(calendarPopup=True)
        self.data_soppressione_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_soppressione_edit.setEnabled(False)
        self.data_soppressione_check.toggled.connect(self.data_soppressione_edit.setEnabled)
        data_soppressione_layout = QHBoxLayout(); data_soppressione_layout.addWidget(self.data_soppressione_check); data_soppressione_layout.addWidget(self.data_soppressione_edit)
        form_layout.addRow("Data Soppressione:", data_soppressione_layout)

        self.note_edit = QTextEdit()
        self.note_edit.setFixedHeight(60)
        form_layout.addRow("Note:", self.note_edit)
        
        self.periodo_combo = QComboBox()
        form_layout.addRow("Periodo Storico:", self.periodo_combo)
        
        main_layout.addWidget(form_group)

        # Pulsanti
        button_layout = QHBoxLayout()
        self.submit_button = QPushButton("Inserisci Comune"); self.submit_button.clicked.connect(self.inserisci_comune)
        self.clear_button = QPushButton("Pulisci Campi"); self.clear_button.clicked.connect(self.pulisci_campi)
        button_layout.addStretch(); button_layout.addWidget(self.submit_button); button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)
        main_layout.addStretch(1)
        self.setLayout(main_layout)

    def load_initial_data(self):
        # ... (questo metodo rimane invariato)
        if self._data_loaded or not self.db_manager or not self.db_manager.pool: return
        self._carica_elenco_periodi()
        self._data_loaded = True

    def _carica_elenco_periodi(self):
        # ... (questo metodo rimane invariato)
        self.periodo_combo.clear(); self.periodo_combo.addItem("--- Nessuno ---", None)
        try:
            periodi = self.db_manager.get_historical_periods()
            if periodi:
                for periodo in periodi:
                    display_text = f"{periodo.get('nome')} ({periodo.get('anno_inizio')} - {periodo.get('anno_fine', 'oggi')})"
                    self.periodo_combo.addItem(display_text, periodo.get('id'))
        except Exception as e:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare l'elenco dei periodi storici:\n{e}")

    def pulisci_campi(self):
        self.nome_comune_edit.clear(); self.provincia_edit.setText("SV"); self.regione_edit.clear()
        self.codice_catastale_edit.clear(); self.note_edit.clear()
        
        # --- MODIFICA QUI: Resetta anche le checkbox ---
        self.data_istituzione_check.setChecked(False)
        self.data_soppressione_check.setChecked(False)
        # Il segnale 'toggled' disabiliterà automaticamente i QDateEdit
        
        self.periodo_combo.setCurrentIndex(0)
        self.nome_comune_edit.setFocus()

    def inserisci_comune(self):
        # Raccoglie i dati da tutti i campi
        nome_comune = self.nome_comune_edit.text().strip()
        provincia = self.provincia_edit.text().strip()
        regione = self.regione_edit.text().strip()
        codice_catastale = self.codice_catastale_edit.text().strip() or None
        note = self.note_edit.toPlainText().strip() or None
        periodo_id_val = self.periodo_combo.currentData()
        
        # --- MODIFICA QUI: Legge le date solo se le checkbox sono spuntate ---
        data_ist = self.data_istituzione_edit.date().toPyDate() if self.data_istituzione_check.isChecked() else None
        data_sopp = self.data_soppressione_edit.date().toPyDate() if self.data_soppressione_check.isChecked() else None

        if not all([nome_comune, provincia, regione]):
            QMessageBox.warning(self, "Dati Mancanti", "Nome, Provincia e Regione sono campi obbligatori.")
            return

        username_per_log = self.utente_attuale_info.get('username', 'utente_sconosciuto') if self.utente_attuale_info else 'utente_sconosciuto'
        
        try:
            comune_id = self.db_manager.aggiungi_comune(
                nome_comune=nome_comune, provincia=provincia, regione=regione,
                periodo_id=periodo_id_val, codice_catastale=codice_catastale,
                data_istituzione=data_ist, data_soppressione=data_sopp, # Passa i valori corretti (o None)
                note=note, utente=username_per_log
            )
            QMessageBox.information(self, "Successo", f"Comune '{nome_comune}' inserito con ID: {comune_id}.")
            self.pulisci_campi()
            self.comune_appena_inserito.emit(comune_id)
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            QMessageBox.critical(self, "Errore Inserimento", str(e))

class InserimentoPossessoreWidget(QWidget):
    import_csv_requested = pyqtSignal()
    def __init__(self, db_manager: 'CatastoDBManager', parent=None): # Usa la stringa per il type hint se CatastoDBManager non è ancora definito/importato globalmente
        super().__init__(parent)
        self.db_manager = db_manager
        self.comuni_list_data: List[Dict[str, Any]] = []
        # self.selected_comune_id: Optional[int] = None # Se lo usi, assicurati sia gestito

        self._initUI()
    def _initUI(self):
        main_layout = QVBoxLayout(self)

        form_group = QGroupBox("Dati del Nuovo Possessore")
        form_layout = QGridLayout(form_group)
        
        # --- AGGIUNTA CHIAVE QUI: Imposta l'espansione della colonna dei campi ---
        # Dice al layout di dare tutto lo spazio orizzontale extra alla colonna 1 (la seconda)
        form_layout.setColumnStretch(1, 1)
        # --- FINE AGGIUNTA ---

        # Riga 0: Cognome e Nome
        form_layout.addWidget(QLabel("Cognome e Nome (*):"), 0, 0)
        self.cognome_nome_edit = QLineEdit()
        self.cognome_nome_edit.setPlaceholderText("Es. Rossi Mario, Bianchi Giovanni")
        form_layout.addWidget(self.cognome_nome_edit, 0, 1) # Rimosso lo span

        # Riga 1: Paternità
        form_layout.addWidget(QLabel("Paternità (es. fu Carlo):"), 1, 0)
        self.paternita_edit = QLineEdit()
        form_layout.addWidget(self.paternita_edit, 1, 1)

        # Riga 2: Pulsante Genera
        self.btn_genera_nome_completo = QPushButton("Genera Nome Completo")
        self.btn_genera_nome_completo.setToolTip("Genera il Nome Completo dai campi Cognome/Nome e Paternità")
        self.btn_genera_nome_completo.clicked.connect(self._genera_e_imposta_nome_completo)
        form_layout.addWidget(self.btn_genera_nome_completo, 2, 1, Qt.AlignLeft) # Allineato a sinistra

        # Riga 3: Nome Completo
        form_layout.addWidget(QLabel("Nome Completo (generato) (*):"), 3, 0)
        self.nome_completo_edit = QLineEdit()
        self.nome_completo_edit.setPlaceholderText("Verrà generato o inserire manualmente se necessario")
        form_layout.addWidget(self.nome_completo_edit, 3, 1)

        # Riga 4: Comune
        form_layout.addWidget(QLabel("Comune di Riferimento (*):"), 4, 0)
        self.comune_combo = QComboBox()
        # La popolazione del combo avviene in un altro metodo (lazy loading)
        form_layout.addWidget(self.comune_combo, 4, 1)

        # Riga 5: Attivo
        self.attivo_checkbox = QCheckBox("Attivo")
        self.attivo_checkbox.setChecked(True)
        form_layout.addWidget(self.attivo_checkbox, 5, 1)
        
        main_layout.addWidget(form_group)

        # Azioni Aggiuntive (Importazione)
        import_group = QGroupBox("Azioni Aggiuntive")
        import_layout = QHBoxLayout(import_group)
        self.import_button = QPushButton("📂 Importa Possessori da CSV..."); self.import_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton)); self.import_button.setToolTip("Apre una finestra per selezionare e importare un file CSV di possessori."); self.import_button.clicked.connect(self.import_csv_requested.emit)
        self.info_button_possessori = QPushButton("Info Formato"); self.info_button_possessori.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxQuestion)); self.info_button_possessori.clicked.connect(self._mostra_info_formato_csv)
        import_layout.addWidget(self.import_button); import_layout.addWidget(self.info_button_possessori); import_layout.addStretch()
        main_layout.addWidget(import_group)
        
        # Pulsanti Salva e Pulisci
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Salva Nuovo Possessore"); self.save_button.clicked.connect(self._salva_possessore)
        self.clear_button = QPushButton("Pulisci Campi"); self.clear_button.clicked.connect(self._pulisci_campi_possessore)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)
        
        main_layout.addStretch(1) # Aggiunge uno spazio elastico in fondo
        self.setLayout(main_layout)
        self._pulisci_campi_possessore() # Per impostare lo stato iniziale
    def _mostra_info_formato_csv(self):
        """Mostra un dialogo con le informazioni sul formato CSV per i possessori."""
        info_text = """
        <h3>Formato CSV per Importazione Possessori</h3>
        <p>Il file CSV deve rispettare le seguenti regole:</p>
        <ul>
            <li>Utilizzare il punto e virgola (<b>;</b>) come delimitatore.</li>
            <li>La prima riga deve contenere le intestazioni delle colonne.</li>
            <li>Le virgolette doppie (") sono gestite correttamente.</li>
        </ul>
        <p><b>Colonne Richieste:</b></p>
        <ul>
            <li><b>cognome_nome</b>: Il cognome e nome separati da spazio (es. Rossi Mario).</li>
            <li><b>nome_completo</b>: Il nome completo come deve apparire, includendo la paternità.</li>
        </ul>
        <p><b>Colonne Opzionali:</b></p>
        <ul>
            <li><b>paternita</b>: La paternità (es. fu Carlo).</li>
        </ul>
        <hr>
        <p><b>Esempio di contenuto del file:</b></p>
        <pre style="background-color:#f0f0f0; padding:5px;"><code>cognome_nome;paternita;nome_completo
        Rossi Mario;fu Giovanni;Rossi Mario fu Giovanni
        Bianchi Giuseppe;;Bianchi Giuseppe</code></pre>
        """
        QMessageBox.information(self, "Guida Formato CSV - Possessori", info_text)

    def _genera_e_imposta_nome_completo(self):
        """
        Genera il nome completo concatenando "Cognome Nome" e "Paternità"
        e lo imposta nel campo nome_completo_edit.
        """
        cognome_nome = self.cognome_nome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()
        nome_completo_generato = cognome_nome # Inizia con cognome e nome

        if cognome_nome and paternita: # Aggiungi paternità solo se entrambi sono presenti
            nome_completo_generato += f" {paternita}" # Es. "Rossi Mario fu Giovanni"
        elif cognome_nome and not paternita: # Solo cognome e nome
            pass # nome_completo_generato è già corretto
        elif not cognome_nome and paternita: # Solo paternità (improbabile ma gestito)
            nome_completo_generato = paternita 
        else: # Entrambi vuoti
            nome_completo_generato = ""
            
        self.nome_completo_edit.setText(nome_completo_generato.strip())

    def _load_comuni_for_combo(self):
        """
        Carica e popola il QComboBox con l'elenco dei comuni dal database in modo sicuro.
        """
        try:
            self.comune_combo.clear() # Pulisce l'elenco prima di ricaricarlo
            
            # self.db_manager.get_comuni() è già stato refattorizzato e funziona
            self.comuni_list_data = self.db_manager.get_comuni() 
            
            if self.comuni_list_data:
                self.comune_combo.setEnabled(True)
                self.comune_combo.addItem("--- Seleziona un comune ---", userData=None)
                for comune_data in self.comuni_list_data:
                    # Crea una stringa chiara per l'utente
                    display_text = f"{comune_data.get('nome', 'N/D')} ({comune_data.get('provincia', 'N/P')})"
                    # Associa l'ID del comune all'elemento, senza visualizzarlo
                    comune_id = comune_data.get('id')
                    self.comune_combo.addItem(display_text, userData=comune_id)
            else:
                # Gestisce il caso in cui non ci siano comuni nel DB
                self.comune_combo.addItem("Nessun comune registrato", userData=None)
                self.comune_combo.setEnabled(False)
                
        except Exception as e:
            self.logger.error(f"Errore critico durante il caricamento dei comuni nel ComboBox: {e}", exc_info=True)
            self.comune_combo.clear()
            self.comune_combo.addItem("Errore caricamento comuni", userData=None)
            self.comune_combo.setEnabled(False)

    def _pulisci_campi_possessore(self):
        """Pulisce i campi del form possessore."""
        self.cognome_nome_edit.clear()
        self.paternita_edit.clear()
        self.nome_completo_edit.clear()
        if self.comune_combo.count() > 0:
            self.comune_combo.setCurrentIndex(0) # O -1 per nessuna selezione se preferito
        self.attivo_checkbox.setChecked(True)
        self.cognome_nome_edit.setFocus()

    def _salva_possessore(self):
        # Ora 'cognome_nome' è l'input primario per nome/cognome
        # 'nome_completo' è quello generato o corretto dall'utente
        cognome_nome_input = self.cognome_nome_edit.text().strip() # Usato per DB e per generare nome completo se serve
        paternita_input = self.paternita_edit.text().strip()
        nome_completo_input = self.nome_completo_edit.text().strip() # Questo è il valore da salvare

        idx_comune = self.comune_combo.currentIndex()
        comune_id_selezionato_data = self.comune_combo.itemData(idx_comune)
        comune_id_selezionato: Optional[int] = None
        if comune_id_selezionato_data is not None:
            try:
                comune_id_selezionato = int(comune_id_selezionato_data)
            except ValueError:
                QMessageBox.warning(self, "Errore Interno", "ID comune selezionato non valido.")
                return

        attivo = self.attivo_checkbox.isChecked()

        if not nome_completo_input: # Il nome completo (generato o manuale) rimane obbligatorio
            QMessageBox.warning(self, "Dati Mancanti", "Il campo 'Nome Completo' è obbligatorio. Utilizzare 'Genera Nome Completo' o inserirlo manualmente.")
            self.nome_completo_edit.setFocus()
            return
        if not cognome_nome_input: # Rendiamo anche questo obbligatorio per coerenza
            QMessageBox.warning(self, "Dati Mancanti", "Il campo 'Cognome e Nome' è obbligatorio.")
            self.cognome_nome_edit.setFocus()
            return
        if comune_id_selezionato is None:
            QMessageBox.warning(self, "Dati Mancanti", "Selezionare un comune di riferimento.")
            self.comune_combo.setFocus()
            return

        try:
            new_possessore_id = self.db_manager.create_possessore(
                nome_completo=nome_completo_input,
                paternita=paternita_input if paternita_input else None,
                comune_riferimento_id=comune_id_selezionato,
                attivo=attivo,
                cognome_nome=cognome_nome_input # Passa il campo cognome_nome al DB manager
            )

            if new_possessore_id is not None:
                QMessageBox.information(self, "Successo",
                                        f"Possessore '{nome_completo_input}' creato con successo. ID: {new_possessore_id}.")
                self._pulisci_campi_possessore()
                # Qui potresti emettere un segnale se altri widget devono essere aggiornati
            # else: create_possessore solleva eccezioni
        # ... (stessa gestione eccezioni di prima per _salva_possessore) ...
        except DBUniqueConstraintError as uve:
            logging.getLogger("CatastoGUI").warning(f"Errore di unicità salvando possessore '{nome_completo_input}': {uve.message}")
            QMessageBox.critical(self, "Errore di Unicità", f"Impossibile creare il possessore:\n{uve.message}")
        except DBDataError as dde:
            logging.getLogger("CatastoGUI").warning(f"Errore dati per possessore '{nome_completo_input}': {dde.message}")
            QMessageBox.warning(self, "Dati Non Validi", f"Impossibile creare il possessore:\n{dde.message}")
        except DBMError as dbe:
            logging.getLogger("CatastoGUI").error(f"Errore database salvando possessore '{nome_completo_input}': {dbe.message}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Si è verificato un errore durante la creazione del possessore:\n{dbe.message}")
        except Exception as e:
            logging.getLogger("CatastoGUI").critical(f"Errore critico imprevisto salvando possessore '{nome_completo_input}': {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto", f"Errore di sistema imprevisto:\n{type(e).__name__}: {e}")



# --- Scheda per Localita ---
class InserimentoLocalitaWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(InserimentoLocalitaWidget, self).__init__(parent)
        self.db_manager = db_manager

        layout = QVBoxLayout()

        # Form di inserimento
        form_group = QGroupBox("Inserimento Nuova Località")
        form_layout = QGridLayout()

        # Comune
        comune_label = QLabel("Comune:")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_id = None
        self.comune_display = QLabel("Nessun comune selezionato")

        form_layout.addWidget(comune_label, 0, 0)
        form_layout.addWidget(self.comune_button, 0, 1)
        form_layout.addWidget(self.comune_display, 0, 2)

        # Nome località
        nome_label = QLabel("Nome località:")
        self.nome_edit = QLineEdit()

        form_layout.addWidget(nome_label, 1, 0)
        form_layout.addWidget(self.nome_edit, 1, 1, 1, 2)

        # Tipo
        tipo_label = QLabel("Tipo:")
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["Regione", "Via", "Borgata","Altro"])

        form_layout.addWidget(tipo_label, 2, 0)
        form_layout.addWidget(self.tipo_combo, 2, 1)

        # Civico
        civico_label = QLabel("Civico (solo per vie):")
        self.civico_edit = QSpinBox()
        self.civico_edit.setMinimum(0)
        self.civico_edit.setMaximum(9999)
        self.civico_edit.setSpecialValueText("Nessun civico")

        form_layout.addWidget(civico_label, 3, 0)
        form_layout.addWidget(self.civico_edit, 3, 1)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Pulsante inserimento
        insert_button = QPushButton("Inserisci Località")
        insert_button.clicked.connect(self.insert_localita)
        layout.addWidget(insert_button)

        # Riepilogo località del comune selezionato
        summary_group = QGroupBox("Località nel Comune Selezionato")
        summary_layout = QVBoxLayout()

        self.refresh_button = QPushButton("Aggiorna Lista")
        self.refresh_button.clicked.connect(self.refresh_localita)

        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(4)
        self.localita_table.setHorizontalHeaderLabels(
            ["ID", "Nome", "Tipo", "Civico"])
        self.localita_table.setAlternatingRowColors(True)
        self.localita_table.horizontalHeader().setStretchLastSection(True)

        summary_layout.addWidget(self.refresh_button)
        summary_layout.addWidget(self.localita_table)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        self.setLayout(layout)

    def select_comune(self):
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)
            self.refresh_localita()  # <-- Chiamata per aggiornare la tabella delle località
        # else: # Opzionale: resetta se l'utente annulla
            # self.comune_id = None
            # self.comune_display.setText("Nessun comune selezionato")
            # self.refresh_localita()

    def insert_localita(self):
        """Inserisce una nuova località."""
        # Valida i dati di input
        if not self.comune_id:
            QMessageBox.warning(self, "Errore", "Seleziona un comune.")
            return

        nome = self.nome_edit.text().strip()
        tipo = self.tipo_combo.currentText()
        civico = self.civico_edit.value() if self.civico_edit.value() > 0 else None

        if not nome:
            QMessageBox.warning(
                self, "Errore", "Il nome della località è obbligatorio.")
            return

        # Inserisci località
        localita_id = self.db_manager.insert_localita(
            self.comune_id, nome, tipo, civico
        )

        if localita_id:
            QMessageBox.information(
                self, "Successo", f"Località '{nome}' inserita con ID: {localita_id}")

            # Pulisci i campi
            self.nome_edit.clear()
            self.civico_edit.setValue(0)

            # Aggiorna la lista delle località
            self.refresh_localita()
        else:
            QMessageBox.critical(
                self, "Errore", "Errore durante l'inserimento della località.")

    def refresh_localita(self):
        """Aggiorna la lista delle località per il comune selezionato."""
        self.localita_table.setRowCount(0)  # Pulisce la tabella
        # Disabilita sorting durante il popolamento
        self.localita_table.setSortingEnabled(False)

        if self.comune_id:  # Assicurati che comune_id sia stato impostato da select_comune
            logging.getLogger("CatastoGUI").info(
                f"DEBUG: InserimentoLocalitaWidget - Chiamata refresh_localita per comune ID: {self.comune_id}")
            try:
                # Chiama il metodo refattorizzato del DBManager
                # Non serve filtro qui, vogliamo tutte le località del comune
                localita_list = self.db_manager.get_localita_by_comune(
                    self.comune_id)

                if localita_list:
                    self.localita_table.setRowCount(len(localita_list))
                    for i, loc in enumerate(localita_list):
                        self.localita_table.setItem(
                            i, 0, QTableWidgetItem(str(loc.get('id', ''))))
                        self.localita_table.setItem(
                            i, 1, QTableWidgetItem(loc.get('nome', '')))
                        self.localita_table.setItem(
                            i, 2, QTableWidgetItem(loc.get('tipo', '')))
                        civico_text = str(loc.get('civico', '')) if loc.get(
                            'civico') is not None else "-"
                        self.localita_table.setItem(
                            i, 3, QTableWidgetItem(civico_text))
                    self.localita_table.resizeColumnsToContents()
                else:
                    logging.getLogger("CatastoGUI").info(
                        f"Nessuna località trovata per il comune ID: {self.comune_id} in InserimentoLocalitaWidget.")
                    # Potresti voler mostrare un messaggio nella tabella se è vuota
                    self.localita_table.setItem(0, 0, QTableWidgetItem("Nessuna località per questo comune."))
                    self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())

            # Se get_localita_by_comune non dovesse esistere (non dovrebbe succedere ora)
            except AttributeError as ae:
                logging.getLogger("CatastoGUI").error(
                    f"Metodo get_localita_by_comune non trovato nel db_manager (chiamato da InserimentoLocalitaWidget): {ae}")
                QMessageBox.critical(
                    self, "Errore Funzionalità", "Funzione per caricare località non implementata correttamente.")
            except Exception as e:
                logging.getLogger("CatastoGUI").error(
                    f"Errore durante l'aggiornamento della lista località per comune {self.comune_id}: {e}", exc_info=True)
                QMessageBox.critical(
                    self, "Errore Caricamento", f"Impossibile aggiornare la lista delle località: {e}")
        else:
            logging.getLogger("CatastoGUI").info(
                "InserimentoLocalitaWidget - refresh_localita: Nessun comune_id selezionato.")
            # La tabella è già stata pulita, quindi apparirà vuota.

        self.localita_table.setSortingEnabled(True)  # Riabilita sorting
# In gui_widgets.py, aggiungi questa nuova classe

# In gui_widgets.py, sostituisci la vecchia classe InserimentoPartitaWidget con questa:

class InserimentoPartitaWidget(QWidget):
    import_csv_requested = pyqtSignal()

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self._initUI()
        self.load_initial_data() # Carichiamo i dati necessari come i comuni

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_group = QGroupBox("Dati Nuova Partita")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        
        # --- CAMPI DEL FORM AGGIORNATI SECONDO LO SCHEMA ---
        self.comune_combo = QComboBox()
        form_layout.addRow("Comune (*):", self.comune_combo)

        self.numero_partita_spin = QSpinBox()
        self.numero_partita_spin.setRange(1, 999999)
        form_layout.addRow("Numero Partita (*):", self.numero_partita_spin)

        self.suffisso_edit = QLineEdit()
        self.suffisso_edit.setPlaceholderText("Es. bis, A (opzionale)")
        self.suffisso_edit.setMaxLength(20)
        form_layout.addRow("Suffisso Partita:", self.suffisso_edit)

        self.data_impianto_edit = QDateEdit(calendarPopup=True)
        self.data_impianto_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_impianto_edit.setDate(QDate.currentDate())
        form_layout.addRow("Data Impianto (*):", self.data_impianto_edit)

        # NUOVO: Campo per data_chiusura (opzionale)
        self.data_chiusura_check = QCheckBox("Imposta data chiusura")
        self.data_chiusura_check.toggled.connect(self._toggle_data_chiusura)
        self.data_chiusura_edit = QDateEdit(calendarPopup=True)
        self.data_chiusura_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_chiusura_edit.setEnabled(False) # Inizia disabilitato
        data_chiusura_layout = QHBoxLayout()
        data_chiusura_layout.addWidget(self.data_chiusura_check)
        data_chiusura_layout.addWidget(self.data_chiusura_edit)
        form_layout.addRow("Data Chiusura:", data_chiusura_layout)
        
        # CORRETTO: Campo per numero_provenienza (testuale)
        self.numero_provenienza_edit = QLineEdit()
        self.numero_provenienza_edit.setPlaceholderText("Numero o testo di riferimento (opzionale)")
        self.numero_provenienza_edit.setMaxLength(50)
        form_layout.addRow("Numero Provenienza:", self.numero_provenienza_edit)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["principale", "secondaria"])
        form_layout.addRow("Tipo (*):", self.tipo_combo)

        self.stato_combo = QComboBox()
        self.stato_combo.addItems(["attiva", "inattiva"])
        form_layout.addRow("Stato (*):", self.stato_combo)

        # Pulsanti di azione per il form manuale
        btn_salva = QPushButton("Salva Nuova Partita")
        btn_salva.clicked.connect(self._salva_partita)
        btn_pulisci = QPushButton("Pulisci Campi")
        btn_pulisci.clicked.connect(self._pulisci_campi)
        manual_actions_layout = QHBoxLayout()
        manual_actions_layout.addStretch()
        manual_actions_layout.addWidget(btn_salva)
        manual_actions_layout.addWidget(btn_pulisci)
        form_layout.addRow(manual_actions_layout)
        main_layout.addWidget(form_group)

        # Sezione per l'importazione CSV
        import_group = QGroupBox("Importazione Massiva")
        # --- MODIFICA QUI: usiamo un QHBoxLayout ---
        import_layout = QHBoxLayout(import_group)
        
        import_button = QPushButton("📂 Importa Partite da File CSV...")
        import_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        import_button.clicked.connect(self.import_csv_requested.emit)

        # Creiamo il nuovo pulsante di aiuto
        info_button_partite = QPushButton("Info Formato")
        info_button_partite.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxQuestion))
        info_button_partite.clicked.connect(self._mostra_info_formato_csv)

        import_layout.addWidget(import_button)
        import_layout.addWidget(info_button_partite)
        import_layout.addStretch()
        # --- FINE MODIFICA ---
        main_layout.addWidget(import_group)

        main_layout.addStretch()
        self.setLayout(main_layout)
        
    def _mostra_info_formato_csv(self):
        """Mostra un dialogo con le informazioni sul formato CSV per le partite."""
        info_text = """
        <h3>Formato CSV per Importazione Partite</h3>
        <p>Il file CSV deve rispettare le seguenti regole:</p>
        <ul>
            <li>Utilizzare il punto e virgola (<b>;</b>) come delimitatore.</li>
            <li>La prima riga deve contenere le intestazioni delle colonne.</li>
        </ul>
        <p><b>Colonne Richieste (*):</b></p>
        <ul>
            <li><b>numero_partita</b> (*): Numero intero della partita.</li>
            <li><b>data_impianto</b> (*): Data in formato YYYY-MM-DD.</li>
            <li><b>stato</b> (*): Testo, 'attiva' o 'inattiva'.</li>
            <li><b>tipo</b> (*): Testo, 'principale' o 'secondaria'.</li>
        </ul>
        <p><b>Colonne Opzionali:</b></p>
        <ul>
            <li><b>suffisso_partita</b>: Suffisso testuale (es. A, bis).</li>
            <li><b>data_chiusura</b>: Data in formato YYYY-MM-DD.</li>
            <li><b>numero_provenienza</b>: Testo o numero di riferimento.</li>
        </ul>
        <hr>
        <p><b>Esempio di contenuto del file:</b></p>
        <pre style="background-color:#f0f0f0; padding:5px;"><code>numero_partita;suffisso_partita;data_impianto;stato;tipo
        1005;A;1980-05-20;attiva;principale
        1006;;1975-11-10;inattiva;principale</code></pre>
        """
        QMessageBox.information(self, "Guida Formato CSV - Partite", info_text)

    def load_initial_data(self):
        """Metodo per caricare i dati necessari, come la lista dei comuni."""
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            self.comune_combo.clear()
            self.comune_combo.addItem("--- Seleziona un comune ---", None)
            for id_comune, nome in comuni:
                self.comune_combo.addItem(nome, id_comune)
        except DBMError as e:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare l'elenco dei comuni:\n{e}")
    
    def _toggle_data_chiusura(self, checked):
        """Abilita o disabilita il QDateEdit per la data di chiusura."""
        self.data_chiusura_edit.setEnabled(checked)
        if checked:
            self.data_chiusura_edit.setDate(QDate.currentDate())
        else:
            self.data_chiusura_edit.setDate(QDate()) # Data nulla

    def _pulisci_campi(self):
        self.comune_combo.setCurrentIndex(0)
        self.numero_partita_spin.setValue(1)
        self.suffisso_edit.clear()
        self.data_impianto_edit.setDate(QDate.currentDate())
        self.data_chiusura_check.setChecked(False) # Disattiva e resetta la data chiusura
        self.numero_provenienza_edit.clear()
        self.tipo_combo.setCurrentIndex(0)
        self.stato_combo.setCurrentIndex(0)
        
    def _salva_partita(self):
        comune_id = self.comune_combo.currentData()
        if not comune_id:
            QMessageBox.warning(self, "Dati Mancanti", "È necessario selezionare un comune.")
            return

        # Recupera i dati dai campi, inclusi i nuovi
        data_chiusura = self.data_chiusura_edit.date().toPyDate() if self.data_chiusura_check.isChecked() else None
        numero_provenienza = self.numero_provenienza_edit.text().strip() or None

        try:
            new_id = self.db_manager.create_partita(
                comune_id=comune_id,
                numero_partita=self.numero_partita_spin.value(),
                tipo=self.tipo_combo.currentText(),
                stato=self.stato_combo.currentText(),
                data_impianto=self.data_impianto_edit.date().toPyDate(),
                suffisso_partita=self.suffisso_edit.text().strip() or None,
                data_chiusura=data_chiusura, # Passa il nuovo valore
                numero_provenienza=numero_provenienza # Passa il nuovo valore
            )
            QMessageBox.information(self, "Successo", f"Partita creata con successo con ID: {new_id}.")
            self._pulisci_campi()
        except (DBMError, DBUniqueConstraintError, DBDataError) as e:
            QMessageBox.critical(self, "Errore Salvataggio", f"Impossibile salvare la partita:\n{e}")


class RegistrazioneProprietaWidget(QWidget):
    partita_creata_per_operazioni_collegate = pyqtSignal(int, int)

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id: Optional[int] = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        # Salva anche il nome per la UI
        self.comune_display_name: Optional[str] = None
        self.possessori_data: List[Dict[str, Any]] = []
        self.immobili_data: List[Dict[str, Any]] = []

        self._initUI()  # Ora questo chiamerà il metodo definito sotto

    def _initUI(self):
        layout = QVBoxLayout(self)

        # --- GRUPPO DATI NUOVA PROPRIETÀ (CON LAYOUT MIGLIORATO) ---
        form_group = QGroupBox("Dati Nuova Proprietà")
        # Usiamo un QGridLayout per un controllo preciso sulla disposizione
        form_layout = QGridLayout(form_group)
        form_layout.setSpacing(10)

        # Riga 0: Selezione Comune
        comune_label = QLabel("Comune (*):")
        self.comune_display = QLabel("Nessun comune selezionato.")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        form_layout.addWidget(comune_label, 0, 0)
        form_layout.addWidget(self.comune_display, 0, 1, 1, 3) # Occupa 3 colonne
        form_layout.addWidget(self.comune_button, 0, 4)

        # Riga 1: Numero e Suffisso Partita sulla stessa linea
        num_partita_label = QLabel("Numero Partita (*):")
        self.num_partita_edit = QSpinBox()
        self.num_partita_edit.setRange(1, 9999999)
        self.num_partita_edit.setMaximumWidth(150) # Dimensione fissa per un aspetto migliore

        suffisso_label = QLabel("Suffisso Partita (opz.):")
        self.suffisso_partita_edit = QLineEdit()
        self.suffisso_partita_edit.setPlaceholderText("Es. bis, A")
        self.suffisso_partita_edit.setMaxLength(20)
        self.suffisso_partita_edit.setMaximumWidth(150) # Dimensione fissa

        form_layout.addWidget(num_partita_label, 1, 0)
        form_layout.addWidget(self.num_partita_edit, 1, 1)
        form_layout.addWidget(suffisso_label, 1, 2, Qt.AlignRight) # Allinea a destra
        form_layout.addWidget(self.suffisso_partita_edit, 1, 3)

        # Riga 2: Data Impianto
        data_label = QLabel("Data Impianto (*):")
        self.data_edit = QDateEdit(calendarPopup=True)
        self.data_edit.setDate(QDate.currentDate())
        self.data_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_edit.setMaximumWidth(150) # Dimensione fissa

        form_layout.addWidget(data_label, 2, 0)
        form_layout.addWidget(self.data_edit, 2, 1)

        # Aggiungiamo una colonna "elastica" che assorba lo spazio extra
        form_layout.setColumnStretch(5, 1)
        
        layout.addWidget(form_group)

        # --- SEZIONI POSSESSORI E IMMOBILI (INVARIATE) ---
        # Sezione Possessori
        possessori_group = QGroupBox("Possessori Associati")
        possessori_layout = QVBoxLayout(possessori_group)
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(4)
        self.possessori_table.setHorizontalHeaderLabels(["ID Poss.", "Nome Completo", "Titolo", "Quota"])
        possessori_layout.addWidget(self.possessori_table)
        btn_add_poss = QPushButton("Aggiungi Possessore")
        btn_add_poss.clicked.connect(self.add_possessore)
        btn_rem_poss = QPushButton("Rimuovi Possessore")
        btn_rem_poss.clicked.connect(self.remove_possessore)
        h_layout_poss = QHBoxLayout()
        h_layout_poss.addWidget(btn_add_poss)
        h_layout_poss.addWidget(btn_rem_poss)
        h_layout_poss.addStretch()
        possessori_layout.addLayout(h_layout_poss)
        layout.addWidget(possessori_group)

        # Sezione Immobili
        immobili_group = QGroupBox("Immobili Associati")
        immobili_layout = QVBoxLayout(immobili_group)
        self.immobili_table = QTableWidget()
        self.immobili_table.setColumnCount(5)
        self.immobili_table.setHorizontalHeaderLabels(["Natura", "Località", "Class.", "Consist.", "Piani/Vani"]) # Aggiornato header per chiarezza
        immobili_layout.addWidget(self.immobili_table)
        btn_add_imm = QPushButton("Aggiungi Immobile")
        btn_add_imm.clicked.connect(self.add_immobile)
        btn_rem_imm = QPushButton("Rimuovi Immobile")
        btn_rem_imm.clicked.connect(self.remove_immobile)
        h_layout_imm = QHBoxLayout()
        h_layout_imm.addWidget(btn_add_imm)
        h_layout_imm.addWidget(btn_rem_imm)
        h_layout_imm.addStretch()
        immobili_layout.addLayout(h_layout_imm)
        layout.addWidget(immobili_group)

        # Pulsante Registra Proprietà
        self.btn_registra_proprieta = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogSaveButton), " Registra Nuova Proprietà")
        self.btn_registra_proprieta.clicked.connect(self._salva_proprieta)
        layout.addWidget(self.btn_registra_proprieta)

        layout.addStretch(1)
    def select_comune(self):
        """Apre il selettore di comuni."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)

    def add_possessore(self):
        """
        Apre un dialogo per selezionare/creare un possessore e, in caso di successo,
        un secondo dialogo per definire i dettagli del legame (titolo e quota).
        """
        if not self.comune_id:
            QMessageBox.warning(self, "Comune Mancante", "Selezionare un comune per la partita prima di aggiungere un possessore.")
            return

        # 1. Dialogo per selezionare la PERSONA
        dialog_sel_poss = PossessoreSelectionDialog(self.db_manager, self.comune_id, self)
        if dialog_sel_poss.exec_() != QDialog.Accepted or not dialog_sel_poss.selected_possessore:
            self.logger.info("Aggiunta possessore annullata o nessun possessore selezionato.")
            return
            
        selected_possessore_info = dialog_sel_poss.selected_possessore
        
        # 2. Dialogo per chiedere i dettagli del LEGAME (Titolo, Quota)
        # Usiamo il metodo statico che abbiamo già preparato
        dettagli_legame = DettagliLegamePossessoreDialog.get_details_for_new_legame(
            nome_possessore=selected_possessore_info.get('nome_completo', 'N/D'),
            tipo_partita_attuale='principale', # Per una nuova proprietà, è 'principale'
            parent=self
        )

        if not dettagli_legame:
            self.logger.info("Definizione dettagli del legame annullata.")
            return

        # 3. Combina le informazioni e aggiungile alla lista dati
        dati_completi_possessore = {
            "id": selected_possessore_info.get('id'),
            "nome_completo": selected_possessore_info.get('nome_completo'),
            "titolo": dettagli_legame.get('titolo'), # Obbligatorio
            "quota": dettagli_legame.get('quota')   # Opzionale
        }
        
        self.possessori_data.append(dati_completi_possessore)
        self.update_possessori_table()

    def remove_possessore(self):
        """Rimuove il possessore selezionato dalla lista."""
        selected_rows = self.possessori_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione",
                                "Seleziona un possessore da rimuovere.")
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.possessori_data):
            del self.possessori_data[row]
            self.update_possessori_table()

    def update_possessori_table(self):
        """
        Aggiorna la tabella dei possessori in modo corretto e robusto.
        """
        self.possessori_table.setRowCount(0) # Pulisce la tabella
        if not hasattr(self, 'possessori_data'):
            return

        self.possessori_table.setRowCount(len(self.possessori_data))
        
        # Imposta le intestazioni corrette
        self.possessori_table.setColumnCount(4)
        self.possessori_table.setHorizontalHeaderLabels(["ID Poss.", "Nome Completo", "Titolo", "Quota"])

        for i, dati_possessore in enumerate(self.possessori_data):
            self.possessori_table.setItem(i, 0, QTableWidgetItem(str(dati_possessore.get('id', 'N/D'))))
            self.possessori_table.setItem(i, 1, QTableWidgetItem(dati_possessore.get('nome_completo', '')))
            self.possessori_table.setItem(i, 2, QTableWidgetItem(dati_possessore.get('titolo', ''))) # Ora questo valore esiste
            self.possessori_table.setItem(i, 3, QTableWidgetItem(dati_possessore.get('quota', '') or '')) # Gestisce None

        self.possessori_table.resizeColumnsToContents()

    def add_immobile(self):
        """Aggiunge un immobile alla lista."""
        dialog = ImmobileDialog(self.db_manager, self.comune_id, self)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.immobile_data:
            self.immobili_data.append(dialog.immobile_data)
            self.update_immobili_table()

    def remove_immobile(self):
        """Rimuove l'immobile selezionato dalla lista."""
        selected_rows = self.immobili_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione",
                                "Seleziona un immobile da rimuovere.")
            return

        row = selected_rows[0].row()
        if 0 <= row < len(self.immobili_data):
            del self.immobili_data[row]
            self.update_immobili_table()

    def update_immobili_table(self):
        """Aggiorna la tabella degli immobili."""
        self.immobili_table.setRowCount(len(self.immobili_data))

        for i, immobile in enumerate(self.immobili_data):
            self.immobili_table.setItem(
                i, 0, QTableWidgetItem(immobile.get('natura', '')))
            self.immobili_table.setItem(i, 1, QTableWidgetItem(
                immobile.get('localita_nome', '')))
            self.immobili_table.setItem(i, 2, QTableWidgetItem(
                immobile.get('classificazione', '')))
            self.immobili_table.setItem(
                i, 3, QTableWidgetItem(immobile.get('consistenza', '')))

            piani_vani = ""
            if 'numero_piani' in immobile and immobile['numero_piani']:
                piani_vani += f"Piani: {immobile['numero_piani']}"
            if 'numero_vani' in immobile and immobile['numero_vani']:
                if piani_vani:
                    piani_vani += ", "
                piani_vani += f"Vani: {immobile['numero_vani']}"

            self.immobili_table.setItem(i, 4, QTableWidgetItem(piani_vani))

    # All'interno della classe RegistrazioneProprietaWidget in prova.py

    def _salva_proprieta(self):
        self.logger.info("Avvio registrazione nuova proprietà...")
        if not self.comune_id:
            QMessageBox.warning(self, "Dati Mancanti", "Selezionare un comune.")
            return
        if not self.possessori_data:
            QMessageBox.warning(self, "Dati Mancanti", "Aggiungere almeno un possessore.")
            return
        if not self.immobili_data:
            QMessageBox.warning(self, "Dati Mancanti", "Aggiungere almeno un immobile.")
            return

        numero_partita = self.num_partita_edit.value()
        # Legge correttamente il valore del suffisso dalla UI
        suffisso_partita = self.suffisso_partita_edit.text().strip() or None 
        data_impianto_dt = self.data_edit.date().toPyDate()

        try:
            possessori_json_str = json.dumps(self.possessori_data)
            immobili_json_str = json.dumps(self.immobili_data)
        except TypeError as te:
            self.logger.error(f"Errore serializzazione JSON per nuova proprietà: {te}")
            QMessageBox.critical(self, "Errore Dati", f"Errore nella preparazione dei dati per il database: {te}")
            return

        try:
            # Chiamata al DB Manager, ora completa con tutti gli argomenti
            nuova_partita_id = self.db_manager.registra_nuova_proprieta(
                comune_id=self.comune_id,
                numero_partita=numero_partita,
                data_impianto=data_impianto_dt,
                possessori_json_str=possessori_json_str,
                immobili_json_str=immobili_json_str,
                suffisso_partita=suffisso_partita  # <<< QUESTA È LA RIGA MANCANTE, ORA AGGIUNTA
            )

            if nuova_partita_id is not None and self.comune_id is not None:
                suffisso_display = f" (Suffisso: {suffisso_partita})" if suffisso_partita else ""
                msg_success = f"Nuova proprietà (Partita N.{numero_partita}{suffisso_display}, ID: {nuova_partita_id}) registrata con successo."
                self.logger.info(msg_success)

                reply = QMessageBox.question(self, "Registrazione Completata",
                                             f"{msg_success}\n\nVuoi procedere con operazioni collegate (es. Duplicazione) su questa o un'altra partita?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

                if reply == QMessageBox.Yes:
                    self.partita_creata_per_operazioni_collegate.emit(nuova_partita_id, self.comune_id)

                self._pulisci_form_registrazione()

        except (DBUniqueConstraintError, DBDataError, DBMError) as e_db:
            self.logger.error(f"Errore DB registrazione proprietà: {e_db}")
            QMessageBox.critical(self, "Errore Database", str(e_db))
        except Exception as e_gen:
            self.logger.critical(f"Errore imprevisto registrazione proprietà: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {type(e_gen).__name__}: {e_gen}")
        self.logger.info("Registrazione proprietà completata.")

    def _pulisci_form_registrazione(self):
        """Pulisce tutti i campi del form di registrazione proprietà."""
        logging.getLogger("CatastoGUI").info(
            "Pulizia campi del form Registrazione Proprietà.")

        # Reset Comune selezionato
        self.comune_id = None
        self.comune_display_name = None  # Se usa una variabile per il nome del comune
        if hasattr(self, 'comune_display') and isinstance(self.comune_display, QLabel):
            self.comune_display.setText("Nessun comune selezionato")

        # Reset Numero Partita
        if hasattr(self, 'num_partita_edit') and isinstance(self.num_partita_edit, QSpinBox):
            # O un valore di default sensato come 1
            self.num_partita_edit.setValue(self.num_partita_edit.minimum())

        # Reset Data Impianto
        if hasattr(self, 'data_edit') and isinstance(self.data_edit, QDateEdit):
            self.data_edit.setDate(QDate.currentDate())

        # Reset liste dati interni
        self.possessori_data = []
        self.immobili_data = []

        # Aggiorna/Pulisci le tabelle UI dei possessori e immobili (se le ha)
        # Metodo che popola/pulisce la QTableWidget dei possessori
        if hasattr(self, 'update_possessori_table'):
            self.update_possessori_table()
        # Alternativa se non c'è update_xxx
        elif hasattr(self, 'possessori_table') and isinstance(self.possessori_table, QTableWidget):
            self.possessori_table.setRowCount(0)

        # Metodo che popola/pulisce la QTableWidget degli immobili
        if hasattr(self, 'update_immobili_table'):
            self.update_immobili_table()
        elif hasattr(self, 'immobili_table') and isinstance(self.immobili_table, QTableWidget):
            self.immobili_table.setRowCount(0)

        # Imposta il focus su un campo iniziale, ad esempio il pulsante per selezionare il comune
        if hasattr(self, 'comune_button') and isinstance(self.comune_button, QPushButton):
            self.comune_button.setFocus()
        elif hasattr(self, 'num_partita_edit'):  # O il campo numero partita
            self.num_partita_edit.setFocus()

        logging.getLogger("CatastoGUI").info(
            "Campi form Registrazione Proprietà puliti.")


class OperazioniPartitaWidget(QWidget):
    # Aggiungi questo __init__ se non c'è
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}") # AGGIUNGI QUESTA RIGA
        self.db_manager = db_manager
        self.selected_partita_id_source: Optional[int] = None
        self.selected_partita_comune_id_source: Optional[int] = None
        self.selected_partita_comune_nome_source: Optional[str] = None
        self.selected_immobile_id_transfer: Optional[int] = None
        self._pp_temp_nuovi_possessori: List[Dict[str, Any]] = []

        self.partita_destinazione_valida: bool = False

        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # --- 1. Selezione Partita Sorgente (Comune a tutti i tab sottostanti) ---
        source_partita_group = QGroupBox("Selezione Partita Sorgente")
        source_partita_layout = QGridLayout(source_partita_group)

        source_partita_layout.addWidget(QLabel("ID Partita Sorgente:"), 0, 0)
        self.source_partita_id_spinbox = QSpinBox()
        self.source_partita_id_spinbox.setRange(
            1, 9999999)  # Range ampio per ID
        self.source_partita_id_spinbox.setToolTip(
            "Inserisci l'ID della partita o usa 'Cerca'")
        source_partita_layout.addWidget(self.source_partita_id_spinbox, 0, 1)

        self.btn_cerca_source_partita = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_FileDialogContentsView), " Cerca Partita...")
        self.btn_cerca_source_partita.setToolTip(
            "Cerca una partita esistente da usare come sorgente")
        self.btn_cerca_source_partita.clicked.connect(
            self._cerca_partita_sorgente)
        source_partita_layout.addWidget(self.btn_cerca_source_partita, 0, 2)

        # Pulsante per caricare la partita dall'ID inserito nello SpinBox
        self.btn_load_source_partita_from_id = QPushButton(QApplication.style().standardIcon(QStyle.SP_ArrowRight), " Carica da ID")
        self.btn_load_source_partita_from_id.setToolTip("Carica i dettagli della partita usando l'ID inserito")
        self.btn_load_source_partita_from_id.clicked.connect(self._load_partita_sorgente_from_spinbox)
        source_partita_layout.addWidget(self.btn_load_source_partita_from_id, 0, 3)

        self.source_partita_info_label = QLabel(
            "Nessuna partita sorgente selezionata.")
        self.source_partita_info_label.setWordWrap(True)
        self.source_partita_info_label.setStyleSheet(
            "QLabel { padding: 5px; background-color: #e8f0fe; border: 1px solid #d0e0ff; border-radius: 3px; min-height: 2em; }")
        source_partita_layout.addWidget(
            self.source_partita_info_label, 1, 0, 1, 4)  # Span su 4 colonne
        main_layout.addWidget(source_partita_group)

        # --- 2. QTabWidget per le diverse operazioni ---
        self.operazioni_tabs = QTabWidget()
        main_layout.addWidget(self.operazioni_tabs, 1)

        # --- Creazione dei Tab ---
        self._crea_tab_duplica_partita()
        self._crea_tab_trasferisci_immobile()
        self._crea_tab_passaggio_proprieta()

        self.setLayout(main_layout)

    def _crea_tab_duplica_partita(self):
        duplica_widget = QWidget()
        duplica_main_layout = QVBoxLayout(duplica_widget)
        duplica_group = QGroupBox("Opzioni per la Duplicazione")
        
        # Usiamo un GridLayout per un layout più pulito
        duplica_form_layout = QGridLayout(duplica_group)
        duplica_form_layout.setSpacing(10)

        # Riga 0: Nuovo Numero e Nuovo Suffisso
        duplica_form_layout.addWidget(QLabel("Nuovo Numero Partita (*):"), 0, 0)
        self.nuovo_numero_partita_spinbox = QSpinBox()
        self.nuovo_numero_partita_spinbox.setRange(1, 9999999)
        duplica_form_layout.addWidget(self.nuovo_numero_partita_spinbox, 0, 1)

        # --- CAMPO SUFFISSO AGGIUNTO QUI ---
        duplica_form_layout.addWidget(QLabel("Suffisso Nuova Partita (opz.):"), 0, 2)
        self.duplica_suffisso_partita_edit = QLineEdit()
        self.duplica_suffisso_partita_edit.setPlaceholderText("Es. bis, A")
        self.duplica_suffisso_partita_edit.setMaxLength(20)
        duplica_form_layout.addWidget(self.duplica_suffisso_partita_edit, 0, 3)
        
        # Colonna "elastica" per non allargare i campi
        duplica_form_layout.setColumnStretch(4, 1)

        # Riga 1 e 2: Checkbox
        self.duplica_mantieni_poss_check = QCheckBox("Mantieni Possessori Originali nella Nuova Partita")
        self.duplica_mantieni_poss_check.setChecked(True)
        duplica_form_layout.addWidget(self.duplica_mantieni_poss_check, 1, 0, 1, 4) # Span su 4 colonne

        self.duplica_mantieni_imm_check = QCheckBox("Copia gli Immobili Originali nella Nuova Partita")
        self.duplica_mantieni_imm_check.setChecked(False)
        duplica_form_layout.addWidget(self.duplica_mantieni_imm_check, 2, 0, 1, 4)

        # Riga 3: Pulsante
        self.btn_esegui_duplicazione = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogApplyButton), " Esegui Duplicazione")
        self.btn_esegui_duplicazione.clicked.connect(self._esegui_duplicazione_partita)
        duplica_form_layout.addWidget(self.btn_esegui_duplicazione, 3, 0, 1, 4, Qt.AlignRight)

        duplica_main_layout.addWidget(duplica_group)
        duplica_main_layout.addStretch(1)
        self.operazioni_tabs.addTab(duplica_widget, "Duplica Partita")

    def _crea_tab_trasferisci_immobile(self):
        transfer_widget = QWidget()
        transfer_main_layout = QVBoxLayout(transfer_widget)
        transfer_group = QGroupBox("Dettagli Trasferimento Immobile")
        transfer_form_layout = QFormLayout(transfer_group)
        transfer_form_layout.setSpacing(10)

        # ... (Tabella self.immobili_partita_sorgente_table e self.immobile_id_transfer_label come prima) ...
        transfer_form_layout.addRow(
            QLabel("Immobili nella Partita Sorgente (selezionarne uno):"))
        self.immobili_partita_sorgente_table = QTableWidget()
        # Rimuovere setColumnCount e setHorizontalHeaderLabels da qui se _carica_immobili_partita_sorgente lo fa dinamicamente
        self.immobili_partita_sorgente_table.setSelectionMode(
            QTableWidget.SingleSelection)
        self.immobili_partita_sorgente_table.setSelectionBehavior(
            QTableWidget.SelectRows)
        self.immobili_partita_sorgente_table.setEditTriggers(
            QTableWidget.NoEditTriggers)
        self.immobili_partita_sorgente_table.setFixedHeight(180)
        self.immobili_partita_sorgente_table.itemSelectionChanged.connect(
            self._immobile_sorgente_selezionato)
        transfer_form_layout.addRow(self.immobili_partita_sorgente_table)

        self.immobile_id_transfer_label = QLabel(
            "Nessun immobile selezionato dalla lista sottostante.")
        self.immobile_id_transfer_label.setStyleSheet(
            "font-style: italic; color: #555;")
        transfer_form_layout.addRow(self.immobile_id_transfer_label)

        # --- Modifiche per Partita Destinazione ---
        # Contenitore per spinbox e nuovo pulsante
        dest_partita_id_container = QWidget()
        dest_partita_id_layout = QHBoxLayout(dest_partita_id_container)
        dest_partita_id_layout.setContentsMargins(0, 0, 0, 0)
        dest_partita_id_layout.setSpacing(5)

        self.dest_partita_id_spinbox = QSpinBox()
        self.dest_partita_id_spinbox.setRange(1, 9999999)
        self.dest_partita_id_spinbox.setToolTip(
            "Inserisci l'ID della partita di destinazione o usa 'Cerca'")
        # Il '1' dà più stretch allo spinbox
        dest_partita_id_layout.addWidget(self.dest_partita_id_spinbox, 1)

        # NUOVO PULSANTE "Carica ID"
        self.btn_carica_dest_partita_da_id = QPushButton(
            "Carica ID")  # Testo breve, o icona SP_ArrowRight
        self.btn_carica_dest_partita_da_id.setToolTip(
            "Verifica e carica i dettagli della partita con l'ID inserito")
        self.btn_carica_dest_partita_da_id.clicked.connect(
            self._load_partita_destinazione_from_spinbox)
        dest_partita_id_layout.addWidget(self.btn_carica_dest_partita_da_id)

        self.btn_cerca_dest_partita = QPushButton(
            "Cerca...")  # Testo più breve
        self.btn_cerca_dest_partita.setToolTip(
            "Cerca una partita esistente da usare come destinazione")
        self.btn_cerca_dest_partita.clicked.connect(
            self._cerca_partita_destinazione)
        dest_partita_id_layout.addWidget(self.btn_cerca_dest_partita)

        transfer_form_layout.addRow(
            "ID Partita Destinazione (*):", dest_partita_id_container)
        # --- Fine Modifiche per Partita Destinazione ---

        self.dest_partita_info_label = QLabel(
            "Nessuna partita destinazione selezionata o verificata.")  # Testo iniziale modificato
        self.dest_partita_info_label.setStyleSheet(
            "font-style: italic; color: #555; padding: 3px; background-color: #E8F0FE; border: 1px solid #B0C4DE; border-radius: 3px;")
        self.dest_partita_info_label.setWordWrap(True)
        transfer_form_layout.addRow(self.dest_partita_info_label)

        self.transfer_registra_var_check = QCheckBox(
            "Registra Variazione Catastale per questo Trasferimento")
        self.transfer_registra_var_check.setChecked(
            True)  # Default a True potrebbe essere sensato
        transfer_form_layout.addRow(self.transfer_registra_var_check)

        self.btn_esegui_trasferimento = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogApplyButton), " Esegui Trasferimento Immobile")
        self.btn_esegui_trasferimento.clicked.connect(
            self._esegui_trasferimento_immobile)
        self.btn_esegui_trasferimento.setEnabled(False)  # Inizia disabilitato
        transfer_form_layout.addRow(self.btn_esegui_trasferimento)

        transfer_main_layout.addWidget(transfer_group)
        transfer_main_layout.addStretch(1)
        self.operazioni_tabs.addTab(transfer_widget, "Trasferisci Immobile")

        # Connetti i segnali per aggiornare lo stato del pulsante "Esegui Trasferimento"
        self.dest_partita_id_spinbox.valueChanged.connect(
            self._update_transfer_button_state_conditionally)
        self.immobili_partita_sorgente_table.itemSelectionChanged.connect(
            self._update_transfer_button_state_conditionally)

    def _crea_tab_passaggio_proprieta(self):
        # --- Tab Passaggio Proprietà (Voltura) ---
        passaggio_widget_main_container = QWidget()
        passaggio_tab_layout = QVBoxLayout(passaggio_widget_main_container)
        passaggio_scroll = QScrollArea(passaggio_widget_main_container)
        passaggio_scroll.setWidgetResizable(True)
        passaggio_scroll_content_widget = QWidget()
        passaggio_main_layout_scroll = QVBoxLayout(
            passaggio_scroll_content_widget)
        passaggio_main_layout_scroll.setSpacing(15)

        
        dati_atto_group = QGroupBox(
            "Dati Nuova Partita e Atto di Trasferimento")
        passaggio_form_layout = QFormLayout(dati_atto_group)
        passaggio_form_layout.setSpacing(10)

        # ... (campi esistenti prima di tipo atto/contratto) ...
        self.pp_nuova_partita_numero_spinbox = QSpinBox()
        self.pp_nuova_partita_numero_spinbox.setRange(1, 9999999)
        passaggio_form_layout.addRow(
            "Numero Nuova Partita (*):", self.pp_nuova_partita_numero_spinbox)
        self.pp_nuova_partita_comune_label = QLabel(
            "Il comune sarà lo stesso della partita sorgente.")
        passaggio_form_layout.addRow(
            "Comune Nuova Partita:", self.pp_nuova_partita_comune_label)
         # NUOVO CAMPO: Suffisso Partita per Passaggio Proprietà
        self.pp_suffisso_nuova_partita_edit = QLineEdit()
        self.pp_suffisso_nuova_partita_edit.setPlaceholderText("Es. bis, ter, A, B (opzionale)")
        self.pp_suffisso_nuova_partita_edit.setMaxLength(20)
        passaggio_form_layout.addRow("Suffisso Nuova Partita (opz.):", self.pp_suffisso_nuova_partita_edit) # AGGIUNTO
            

        self.pp_tipo_variazione_combo = QComboBox()
        tipi_variazione_validi = ['Vendita', 'Acquisto', 'Successione',
                                  'Variazione', 'Frazionamento', 'Divisione', 'Trasferimento', 'Altro']
        self.pp_tipo_variazione_combo.addItems(tipi_variazione_validi)
        if tipi_variazione_validi:
            self.pp_tipo_variazione_combo.setCurrentIndex(0)
        passaggio_form_layout.addRow(
            "Tipo Variazione (*):", self.pp_tipo_variazione_combo)

        self.pp_data_variazione_edit = QDateEdit(calendarPopup=True)
        self.pp_data_variazione_edit.setDisplayFormat("yyyy-MM-dd")
        self.pp_data_variazione_edit.setDate(QDate.currentDate())
        passaggio_form_layout.addRow(
            "Data Variazione (*):", self.pp_data_variazione_edit)
        
        # --- MODIFICA QUI: SOSTITUISCI QLineEdit con QComboBox ---
        self.pp_tipo_contratto_combo = QComboBox() # CAMBIATO IN COMBOBOX
        # Lista dei tipi di atto/contratto comuni
        tipi_atto_validi = [
            "Atto di Compravendita",
            "Dichiarazione di Successione",
            "Atto di Donazione",
            "Sentenza Giudiziale",
            "Atto di Divisione",
            "Verbale di Asta Pubblica",
            "Permuta",
            "Usucapione",
            "Altro Atto Pubblico",
            "Scrittura Privata"
        ]
        self.pp_tipo_contratto_combo.addItems(tipi_atto_validi)
        # Se vuoi un valore iniziale diverso o "Seleziona tipo..." puoi aggiungerlo
        self.pp_tipo_contratto_combo.insertItem(0, "Seleziona Tipo...") # Aggiunge un placeholder
        self.pp_tipo_contratto_combo.setCurrentIndex(0) # Seleziona il placeholder inizialmente
        
        passaggio_form_layout.addRow(
            "Tipo Atto/Contratto (*):", self.pp_tipo_contratto_combo) # USATO IL NUOVO WIDGET
        # --- FINE MODIFICA ---

        self.pp_data_contratto_edit = QDateEdit(calendarPopup=True)
        self.pp_data_contratto_edit.setDisplayFormat("yyyy-MM-dd")
        self.pp_data_contratto_edit.setDate(QDate.currentDate())
        passaggio_form_layout.addRow(
            "Data Atto/Contratto (*):", self.pp_data_contratto_edit)
        self.pp_notaio_edit = QLineEdit()
        passaggio_form_layout.addRow(
            "Notaio/Autorità Emittente:", self.pp_notaio_edit)
        self.pp_repertorio_edit = QLineEdit()
        passaggio_form_layout.addRow(
            "N. Repertorio/Protocollo:", self.pp_repertorio_edit)
        self.pp_note_variazione_edit = QTextEdit()
        self.pp_note_variazione_edit.setFixedHeight(60)
        passaggio_form_layout.addRow(
            "Note Variazione:", self.pp_note_variazione_edit)
        passaggio_main_layout_scroll.addWidget(dati_atto_group)

        immobili_transfer_group_pp = QGroupBox(
            "Immobili da Includere nella Nuova Partita")
        immobili_transfer_layout_pp = QVBoxLayout(immobili_transfer_group_pp)
        self.pp_trasferisci_tutti_immobili_check = QCheckBox(
            "Includi TUTTI gli immobili dalla partita sorgente")
        self.pp_trasferisci_tutti_immobili_check.setChecked(True)
        self.pp_trasferisci_tutti_immobili_check.toggled.connect(
            self._toggle_selezione_immobili_pp)
        immobili_transfer_layout_pp.addWidget(
            self.pp_trasferisci_tutti_immobili_check)
        self.pp_immobili_da_selezionare_table = QTableWidget()
        self.pp_immobili_da_selezionare_table.setColumnCount(4)
        self.pp_immobili_da_selezionare_table.setHorizontalHeaderLabels(
            ["Sel.", "ID Imm.", "Natura", "Località"])
        self.pp_immobili_da_selezionare_table.setSelectionMode(
            QTableWidget.NoSelection)
        self.pp_immobili_da_selezionare_table.setEditTriggers(
            QTableWidget.NoEditTriggers)
        self.pp_immobili_da_selezionare_table.setFixedHeight(150)
        self.pp_immobili_da_selezionare_table.setVisible(False)
        immobili_transfer_layout_pp.addWidget(
            self.pp_immobili_da_selezionare_table)
        passaggio_main_layout_scroll.addWidget(immobili_transfer_group_pp)

        nuovi_poss_group = QGroupBox("Nuovi Possessori per la Nuova Partita")
        nuovi_poss_layout = QVBoxLayout(nuovi_poss_group)
        self.pp_nuovi_possessori_table = QTableWidget()
        self.pp_nuovi_possessori_table.setColumnCount(4)
        self.pp_nuovi_possessori_table.setHorizontalHeaderLabels(
            ["ID Poss.", "Nome Completo", "Titolo (*)", "Quota"])
        self.pp_nuovi_possessori_table.setEditTriggers(
            QTableWidget.NoEditTriggers)
        self.pp_nuovi_possessori_table.setSelectionMode(
            QTableWidget.SingleSelection)
        self.pp_nuovi_possessori_table.horizontalHeader(
        ).setSectionResizeMode(QHeaderView.ResizeToContents)
        self.pp_nuovi_possessori_table.horizontalHeader().setStretchLastSection(True)
        self.pp_nuovi_possessori_table.setFixedHeight(150)
        nuovi_poss_layout.addWidget(self.pp_nuovi_possessori_table)
        nuovi_poss_buttons_layout = QHBoxLayout()
        self.pp_btn_aggiungi_nuovo_possessore = QPushButton(
            # O QStyle.SP_FileLinkIcon o QStyle.SP_ToolBarAddButton
            QApplication.style().standardIcon(QStyle.SP_FileDialogNewFolder),
            " Aggiungi Possessore..."
        )
        self.pp_btn_aggiungi_nuovo_possessore.setToolTip(
            "Aggiungi un nuovo possessore (o seleziona uno esistente) alla lista per la nuova partita")
        self.pp_btn_aggiungi_nuovo_possessore.clicked.connect(
            self._pp_aggiungi_nuovo_possessore)
        nuovi_poss_buttons_layout.addWidget(
            self.pp_btn_aggiungi_nuovo_possessore)

       # CORREZIONE ICONA QUI:
        self.pp_btn_rimuovi_nuovo_possessore = QPushButton(
            # O QStyle.SP_DialogDiscardButton
            QApplication.style().standardIcon(QStyle.SP_TrashIcon),
            " Rimuovi Selezionato"
        )
        self.pp_btn_rimuovi_nuovo_possessore = QPushButton(QApplication.style(
            # Esempio Icona
        ).standardIcon(QStyle.SP_TrashIcon), " Rimuovi Selezionato")
        self.pp_btn_rimuovi_nuovo_possessore.clicked.connect(
            self._pp_rimuovi_nuovo_possessore_selezionato)
        nuovi_poss_buttons_layout.addWidget(
            self.pp_btn_rimuovi_nuovo_possessore)
        nuovi_poss_buttons_layout.addStretch()
        nuovi_poss_layout.addLayout(nuovi_poss_buttons_layout)
        passaggio_main_layout_scroll.addWidget(nuovi_poss_group)

        self.pp_btn_esegui_passaggio = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogApplyButton), " Esegui Passaggio Proprietà")
        self.pp_btn_esegui_passaggio.clicked.connect(
            self._esegui_passaggio_proprieta)
        passaggio_main_layout_scroll.addWidget(
            self.pp_btn_esegui_passaggio, 0, Qt.AlignRight)
        passaggio_main_layout_scroll.addStretch(1)

        passaggio_scroll.setWidget(passaggio_scroll_content_widget)
        passaggio_tab_layout.addWidget(passaggio_scroll)
        self.operazioni_tabs.addTab(
            passaggio_widget_main_container, "Passaggio Proprietà (Voltura)")

    # --- Metodi Helper e Handler ---

    def _load_partita_destinazione_from_spinbox(self):
        partita_id_dest = self.dest_partita_id_spinbox.value()
        self.dest_partita_info_label.setText("Verifica ID partita destinazione...")
        self.partita_destinazione_valida = False

        if partita_id_dest <= 0:
            self.dest_partita_info_label.setText("<font color='red'>ID partita destinazione non valido.</font>")
            self._update_transfer_button_state_conditionally()
            return

        partita_details = self.db_manager.get_partita_details(partita_id_dest)

        if partita_details:
            stato = partita_details.get('stato')
            comune = partita_details.get('comune_nome', 'N/D')
            numero = partita_details.get('numero_partita', 'N/D')
            # --- AGGIUNTA LETTURA SUFFISSO ---
            suffisso = partita_details.get('suffisso_partita')
            suffisso_display = f" (suffisso: {suffisso})" if suffisso else ""

            if self.selected_partita_id_source is not None and partita_id_dest == self.selected_partita_id_source:
                self.dest_partita_info_label.setText(f"<font color='red'>Errore: La destinazione non può essere uguale alla sorgente.</font>")
                self.partita_destinazione_valida = False
            elif stato != 'attiva':
                self.dest_partita_info_label.setText(f"<font color='red'>Errore: La partita N.{numero}{suffisso_display} non è attiva.</font>")
                self.partita_destinazione_valida = False
            else:
                self.dest_partita_info_label.setText(f"Destinazione: N. {numero}{suffisso_display} (Comune: {comune}, ID: {partita_id_dest})")
                self.partita_destinazione_valida = True
        else:
            self.dest_partita_info_label.setText(f"<font color='red'>Partita destinazione con ID {partita_id_dest} non trovata.</font>")
            self.partita_destinazione_valida = False

        self._update_transfer_button_state_conditionally()

    def _cerca_partita_destinazione(self):
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_partita_id:
            selected_id = dialog.selected_partita_id
            self.dest_partita_id_spinbox.setValue(
                selected_id)  # Imposta lo spinbox
            # Chiama la logica di caricamento e validazione
            self._load_partita_destinazione_from_spinbox()
        # else: Non fare nulla se l'utente annulla, la label non cambia o è già impostata
        # self._update_transfer_button_state_conditionally() # _load_partita_destinazione_from_spinbox lo fa già

    def _update_transfer_button_state_conditionally(self):
        """Abilita il pulsante 'Esegui Trasferimento' solo se tutte le condizioni sono soddisfatte."""
        is_enabled = False
        immobile_selezionato = self.selected_immobile_id_transfer is not None
        # Verifica solo che un ID sia nello spinbox
        id_partita_dest_inserito = self.dest_partita_id_spinbox.value() > 0

        partita_dest_diversa_da_sorgente = True
        if self.selected_partita_id_source is not None and id_partita_dest_inserito:
            partita_dest_diversa_da_sorgente = (
                self.dest_partita_id_spinbox.value() != self.selected_partita_id_source)

        if immobile_selezionato and id_partita_dest_inserito and \
           self.partita_destinazione_valida and partita_dest_diversa_da_sorgente:
            is_enabled = True

        self.btn_esegui_trasferimento.setEnabled(is_enabled)

        # Aggiorna tooltip per guidare l'utente
        if not is_enabled:
            reasons = []
            if not immobile_selezionato:
                reasons.append(
                    "selezionare un immobile dalla tabella sorgente")
            if not id_partita_dest_inserito:
                reasons.append(
                    "inserire un ID per la partita destinazione e caricarne i dettagli")
            elif not self.partita_destinazione_valida:
                reasons.append(
                    "la partita destinazione non è valida o non è attiva (controllare messaggio sopra)")
            if not partita_dest_diversa_da_sorgente and id_partita_dest_inserito:
                reasons.append(
                    "la partita destinazione deve essere diversa dalla sorgente")

            if reasons:
                self.btn_esegui_trasferimento.setToolTip(
                    "Per abilitare: " + " e ".join(reasons) + ".")
            # Caso in cui tutti i singoli check passano ma la combinazione logica di is_enabled è False (improbabile con la logica sopra)
            else:
                self.btn_esegui_trasferimento.setToolTip(
                    "Verificare tutti i campi per il trasferimento.")
        else:
            self.btn_esegui_trasferimento.setToolTip(
                "Esegue il trasferimento dell'immobile selezionato alla partita destinazione.")

    # Modifichi anche _immobile_sorgente_selezionato per chiamare l'aggiornamento del pulsante

    def _immobile_sorgente_selezionato(self):
        # ... (logica esistente per impostare self.selected_immobile_id_transfer e self.immobile_id_transfer_label)
        selected_rows = self.immobili_partita_sorgente_table.selectionModel().selectedRows()
        if not selected_rows:
            self.selected_immobile_id_transfer = None
            self.immobile_id_transfer_label.setText(
                "Nessun immobile selezionato dalla lista.")
        else:
            row = selected_rows[0].row()
            # ID Imm.
            id_item = self.immobili_partita_sorgente_table.item(row, 0)
            natura_item = self.immobili_partita_sorgente_table.item(
                row, 1)  # Natura

            if id_item and id_item.text().isdigit():
                self.selected_immobile_id_transfer = int(id_item.text())
                natura_text = natura_item.text() if natura_item else "N/D"
                self.immobile_id_transfer_label.setText(
                    f"Immobile da trasferire: ID {self.selected_immobile_id_transfer} (Natura: {natura_text})")
            else:
                self.selected_immobile_id_transfer = None
                self.immobile_id_transfer_label.setText(
                    "Selezione immobile non valida.")

        self._update_transfer_button_state_conditionally()

    def _cerca_partita_sorgente(self):
        """Apre il dialogo per cercare una partita sorgente."""
        # ... (suo codice esistente)
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_partita_id:
            self.source_partita_id_spinbox.setValue(
                dialog.selected_partita_id)  # Imposta lo spinbox
            self.selected_partita_id_source = dialog.selected_partita_id   # Imposta l'ID
            self._aggiorna_info_partita_sorgente()  # Carica i dettagli
        
            if not self.selected_partita_id_source:  # Resetta solo se non c'era già una selezione
                self.source_partita_info_label.setText(
                    "Nessuna partita sorgente selezionata.")
                self.selected_partita_comune_id_source = None
                self.selected_partita_comune_nome_source = None
                if hasattr(self, 'immobili_partita_sorgente_table'):
                    self.immobili_partita_sorgente_table.setRowCount(0)
                if hasattr(self, 'pp_immobili_da_selezionare_table'):
                    self.pp_immobili_da_selezionare_table.setRowCount(0)
                if hasattr(self, 'pp_nuova_partita_comune_label'):
                    self.pp_nuova_partita_comune_label.setText(
                        "Il comune sarà lo stesso della partita sorgente.")

    def _aggiorna_info_partita_sorgente(self):
        """
        Recupera e visualizza i dettagli della partita sorgente (selected_partita_id_source)
        e popola le UI dipendenti (es. tabella immobili per trasferimento).
        """
        # Pulisci le UI dipendenti prima di caricarne di nuove o se non c'è sorgente
        if hasattr(self, 'immobili_partita_sorgente_table'):
            self.immobili_partita_sorgente_table.setRowCount(0)
            if hasattr(self, 'selected_immobile_id_transfer'):
                self.selected_immobile_id_transfer = None
            if hasattr(self, 'immobile_id_transfer_label'):
                self.immobile_id_transfer_label.setText(
                    "Nessun immobile selezionato.")

        if hasattr(self, 'pp_immobili_da_selezionare_table'):  # Per il tab Passaggio Proprietà
            self.pp_immobili_da_selezionare_table.setRowCount(0)

        if hasattr(self, 'pp_nuova_partita_comune_label'):
            self.pp_nuova_partita_comune_label.setText(
                "Il comune sarà lo stesso della partita sorgente.")

        if self.selected_partita_id_source and self.selected_partita_id_source > 0:
            partita_details = self.db_manager.get_partita_details(
                self.selected_partita_id_source)
            if partita_details:
                self.selected_partita_comune_id_source = partita_details.get(
                    'comune_id')  # Salva per uso futuro
                self.selected_partita_comune_nome_source = partita_details.get(
                    'comune_nome', 'N/D')

                self.source_partita_info_label.setText(
                    f"Partita Sorgente: N. {partita_details.get('numero_partita')} "
                    f"(Comune: {self.selected_partita_comune_nome_source} [ID: {self.selected_partita_comune_id_source}], Partita ID: {self.selected_partita_id_source})"
                )
                immobili = partita_details.get('immobili', [])

                # Popola la tabella immobili nel tab "Trasferisci Immobile"
                if hasattr(self, '_carica_immobili_partita_sorgente'):
                    self._carica_immobili_partita_sorgente(immobili)

                # Popola la tabella immobili nel tab "Passaggio Proprietà"
                if hasattr(self, '_pp_carica_immobili_per_selezione'):
                    self._pp_carica_immobili_per_selezione(immobili)

                # Aggiorna etichetta comune nel tab "Passaggio Proprietà"
                if hasattr(self, 'pp_nuova_partita_comune_label') and self.selected_partita_comune_nome_source and self.selected_partita_comune_id_source:
                    self.pp_nuova_partita_comune_label.setText(
                        f"{self.selected_partita_comune_nome_source} (ID: {self.selected_partita_comune_id_source})"
                    )
            else:  # Partita non trovata
                self.source_partita_info_label.setText(
                    f"Partita sorgente con ID {self.selected_partita_id_source} non trovata o errore nel recupero dettagli.")
                self.selected_partita_id_source = None  # Resetta se non trovata
                self.selected_partita_comune_id_source = None
                self.selected_partita_comune_nome_source = None
        else:  # Nessun ID sorgente valido
            self.source_partita_info_label.setText(
                "Nessuna partita sorgente selezionata o ID non valido.")
            self.selected_partita_id_source = None
            self.selected_partita_comune_id_source = None
            self.selected_partita_comune_nome_source = None

        # Aggiorna lo stato dei pulsanti che dipendono dalla selezione della partita sorgente/destinazione
        if hasattr(self, '_update_transfer_button_state_conditionally'):
            self._update_transfer_button_state_conditionally()
        # Aggiungere chiamate simili per aggiornare lo stato dei pulsanti negli altri sotto-tab se necessario

    def _esegui_duplicazione_partita(self):
        self.logger.info("Avvio _esegui_duplicazione_partita.")

        if self.selected_partita_id_source is None:
            QMessageBox.warning(self, "Selezione Mancante", "Selezionare una partita sorgente prima di duplicare.")
            return
        if self.selected_partita_comune_id_source is None:
            QMessageBox.warning(self, "Errore Interno", "Comune della partita sorgente non determinato.")
            return

        nuovo_numero = self.nuovo_numero_partita_spinbox.value()
        # --- LETTURA VALORE SUFFISSO ---
        nuovo_suffisso = self.duplica_suffisso_partita_edit.text().strip() or None

        if nuovo_numero <= 0:
            QMessageBox.warning(self, "Dati Non Validi", "Il nuovo numero di partita deve essere un valore positivo.")
            return

        # --- VERIFICA UNICITÀ CON SUFFISSO ---
        try:
            existing_partita = self.db_manager.search_partite(
                comune_id=self.selected_partita_comune_id_source,
                numero_partita=nuovo_numero,
                suffisso_partita=nuovo_suffisso
            )
            if existing_partita:
                suffisso_display = f" (suffisso: {nuovo_suffisso})" if nuovo_suffisso else ""
                QMessageBox.warning(self, "Errore Duplicazione",
                                    f"Esiste già una partita con il numero {nuovo_numero}{suffisso_display} "
                                    f"nel comune '{self.selected_partita_comune_nome_source}'.")
                return
        except DBMError as e:
            QMessageBox.critical(self, "Errore Verifica Partita", f"Errore durante la verifica del numero partita:\n{str(e)}")
            return
        
        mant_poss = self.duplica_mantieni_poss_check.isChecked()
        mant_imm = self.duplica_mantieni_imm_check.isChecked()
        
        try:
            # --- CHIAMATA AL DB MANAGER CON SUFFISSO ---
            success = self.db_manager.duplicate_partita(
                partita_id_originale=self.selected_partita_id_source,
                nuovo_numero_partita=nuovo_numero,
                mantenere_possessori=mant_poss,
                mantenere_immobili=mant_imm,
                nuovo_suffisso=nuovo_suffisso
            )
            
            if success:
                suffisso_display = f" (suffisso: {nuovo_suffisso})" if nuovo_suffisso else ""
                QMessageBox.information(self, "Successo",
                                        f"Partita ID {self.selected_partita_id_source} duplicata con successo "
                                        f"in una nuova partita N. {nuovo_numero}{suffisso_display}.")
                self.nuovo_numero_partita_spinbox.setValue(1)
                self.duplica_suffisso_partita_edit.clear()
            else:
                QMessageBox.critical(self, "Errore Operazione", "La duplicazione della partita non è stata completata.")
        except DBMError as e:
            QMessageBox.critical(self, "Errore Duplicazione", f"Impossibile duplicare la partita:\n{str(e)}")
        except Exception as e_gen:
            self.logger.critical(f"Errore imprevisto durante la duplicazione: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore di sistema:\n{str(e_gen)}")


    def _carica_immobili_partita_sorgente(self, immobili_data: List[Dict[str, Any]]):
        table = self.immobili_partita_sorgente_table

        # --- NUOVE INTESTAZIONI ---
        nuove_colonne = ["ID Imm.", "Natura",
                         "Classificazione", "Consistenza", "Località Completa"]
        table.setColumnCount(len(nuove_colonne))
        table.setHorizontalHeaderLabels(nuove_colonne)
        # --- FINE NUOVE INTESTAZIONI ---

        table.setRowCount(0)
        table.setSortingEnabled(False)
        self.selected_immobile_id_transfer = None
        self.immobile_id_transfer_label.setText(
            "Nessun immobile selezionato dalla lista sottostante.")

        if immobili_data:
            table.setRowCount(len(immobili_data))
            for row, immobile in enumerate(immobili_data):
                col = 0
                table.setItem(row, col, QTableWidgetItem(
                    str(immobile.get('id', 'N/D'))))
                col += 1
                table.setItem(row, col, QTableWidgetItem(
                    immobile.get('natura', 'N/D')))
                col += 1

                # --- NUOVE COLONNE ---
                table.setItem(row, col, QTableWidgetItem(
                    immobile.get('classificazione', 'N/D')))
                col += 1
                table.setItem(row, col, QTableWidgetItem(
                    immobile.get('consistenza', 'N/D')))
                col += 1
                # --- FINE NUOVE COLONNE ---

                loc_nome = immobile.get('localita_nome', '')
                loc_tipo = immobile.get('localita_tipo', '')
                loc_civico = immobile.get('civico', '')
                loc_text = loc_nome
                if loc_tipo:
                    loc_text += f" ({loc_tipo})"
                if loc_civico:  # Civico potrebbe essere 0 o stringa vuota se non presente
                    loc_text += f", civ. {loc_civico}"
                table.setItem(row, col, QTableWidgetItem(loc_text.strip()))
                col += 1

            table.resizeColumnsToContents()  # Adatta dopo aver popolato
            # O imposta larghezze specifiche per una migliore leggibilità
            # table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) # ID
            # table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive) # Natura
            # table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch) # Località
        else:
            table.setRowCount(1)
            no_imm_item = QTableWidgetItem(
                "Nessun immobile associato a questa partita sorgente.")
            no_imm_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(0, 0, no_imm_item)
            # Occupa tutte le colonne
            table.setSpan(0, 0, 1, table.columnCount())

        table.setSortingEnabled(True)

    def _esegui_trasferimento_immobile(self):
        if self.selected_immobile_id_transfer is None:
            QMessageBox.warning(self, "Selezione Mancante",
                                "Selezionare un immobile dalla partita sorgente da trasferire.")
            return
        id_partita_dest = self.dest_partita_id_spinbox.value()
        if id_partita_dest <= 0:
            QMessageBox.warning(
                self, "Dati Non Validi", "Selezionare o inserire un ID partita di destinazione valido.")
            return
        if self.selected_partita_id_source is not None and id_partita_dest == self.selected_partita_id_source:
            QMessageBox.warning(self, "Operazione Non Valida",
                                "La partita di destinazione non può essere uguale alla partita sorgente.")
            return

        registra_var = self.transfer_registra_var_check.isChecked()
        try:
            success = self.db_manager.transfer_immobile(
                self.selected_immobile_id_transfer, id_partita_dest, registra_var
            )
            if success:
                QMessageBox.information(self, "Successo",
                                        f"Immobile ID {self.selected_immobile_id_transfer} trasferito "
                                        f"alla partita ID {id_partita_dest} con successo.")
                self._aggiorna_info_partita_sorgente()  # Ricarica immobili sorgente
                self.dest_partita_id_spinbox.setValue(
                    self.dest_partita_id_spinbox.minimum())
                self.dest_partita_info_label.setText(
                    "Nessuna partita destinazione selezionata.")
                self.transfer_registra_var_check.setChecked(False)
        except DBMError as e:
            QMessageBox.critical(self, "Errore Trasferimento",
                                 f"Errore durante il trasferimento dell'immobile:\n{str(e)}")
        except Exception as e_gen:
            logging.getLogger("CatastoGUI").critical(
                f"Errore imprevisto trasferimento immobile: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto",
                                 f"Errore:\n{type(e_gen).__name__}: {str(e_gen)}")

    def _toggle_selezione_immobili_pp(self, checked: bool):
        if hasattr(self, 'pp_immobili_da_selezionare_table'):
            self.pp_immobili_da_selezionare_table.setVisible(not checked)
            if checked and hasattr(self, '_pp_pulisci_selezione_immobili_specifici'):
                self._pp_pulisci_selezione_immobili_specifici()

    def _pp_pulisci_selezione_immobili_specifici(self):
        if hasattr(self, 'pp_immobili_da_selezionare_table'):
            table = self.pp_immobili_da_selezionare_table
            for row in range(table.rowCount()):
                cell_widget = table.cellWidget(row, 0)
                if isinstance(cell_widget, QCheckBox):
                    cell_widget.setChecked(False)

    def _pp_carica_immobili_per_selezione(self, immobili_data: List[Dict[str, Any]]):
        if not hasattr(self, 'pp_immobili_da_selezionare_table'):
            logging.getLogger("CatastoGUI").error(
                "Tabella 'pp_immobili_da_selezionare_table' non inizializzata.")
            return
        table = self.pp_immobili_da_selezionare_table
        table.setRowCount(0)
        table.setSortingEnabled(False)
        if immobili_data:
            table.setRowCount(len(immobili_data))
            for row, immobile in enumerate(immobili_data):
                chk = QCheckBox()
                chk.setProperty("immobile_id", immobile.get('id'))
                table.setCellWidget(row, 0, chk)
                id_i = QTableWidgetItem(str(immobile.get('id', 'N/D')))
                id_i.setFlags(id_i.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, 1, id_i)
                nat_i = QTableWidgetItem(immobile.get('natura', 'N/D'))
                nat_i.setFlags(nat_i.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, 2, nat_i)
                loc_t = f"{immobile.get('localita_nome', '')} {immobile.get('civico', '')}".strip(
                )
                loc_i = QTableWidgetItem(loc_t)
                loc_i.setFlags(loc_i.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, 3, loc_i)
            # Configurazione resize mode per le colonne
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # Checkbox
            table.setColumnWidth(0, 35)
            table.horizontalHeader().setSectionResizeMode(
                1, QHeaderView.ResizeToContents)  # ID
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # Natura
            table.horizontalHeader().setSectionResizeMode(
                3, QHeaderView.Stretch)  # Località
        else:
            table.setRowCount(1)
            msg_item = QTableWidgetItem(
                "Nessun immobile disponibile nella partita sorgente per la selezione.")
            msg_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(0, 0, msg_item)
            table.setSpan(0, 0, 1, table.columnCount())
        table.setSortingEnabled(True)

    def _pp_aggiungi_nuovo_possessore(self):
        if not self.selected_partita_comune_id_source:
            QMessageBox.warning(
                self, "Comune Mancante", "Selezionare una partita sorgente per determinare il comune di riferimento dei nuovi possessori.")
            return
        dialog_sel_poss = PossessoreSelectionDialog(
            self.db_manager, self.selected_partita_comune_id_source, self)
        dialog_sel_poss.setWindowTitle(
            "Seleziona o Crea Nuovo Possessore per Nuova Partita")
        possessore_info_completa_sel = None
        if dialog_sel_poss.exec_() == QDialog.Accepted:
            if hasattr(dialog_sel_poss, 'selected_possessore') and dialog_sel_poss.selected_possessore:
                poss_id_sel = dialog_sel_poss.selected_possessore.get('id')
                if poss_id_sel:
                    dettagli_poss_db = self.db_manager.get_possessore_full_details(
                        poss_id_sel)
                    if dettagli_poss_db:
                        possessore_info_completa_sel = dettagli_poss_db
                    else:
                        QMessageBox.warning(
                            self, "Errore", f"Impossibile recuperare dettagli per possessore ID {poss_id_sel}.")
                        return
                else:
                    QMessageBox.warning(
                        self, "Errore", "Nessun ID possessore valido dalla selezione.")
                    return
            else:
                logging.getLogger("CatastoGUI").warning(
                    "PossessoreSelectionDialog non ha restituito 'selected_possessore'.")
                return
        else:
            logging.getLogger("CatastoGUI").info(
                "Aggiunta possessore per PP annullata (selezione/creazione).")
            return

        if not possessore_info_completa_sel or possessore_info_completa_sel.get('id') is None:
            QMessageBox.warning(
                self, "Errore", "Dati del possessore non validi.")
            return

        dettagli_leg = DettagliLegamePossessoreDialog.get_details_for_new_legame(
            nome_possessore=possessore_info_completa_sel.get(
                "nome_completo", "N/D"),
            tipo_partita_attuale='principale', parent=self
        )
        if dettagli_leg:
            self._pp_temp_nuovi_possessori.append({
                "possessore_id": possessore_info_completa_sel.get("id"),
                "nome_completo": possessore_info_completa_sel.get("nome_completo"),
                "cognome_nome": possessore_info_completa_sel.get("cognome_nome"),
                "paternita": possessore_info_completa_sel.get("paternita"),
                "comune_riferimento_id": possessore_info_completa_sel.get("comune_riferimento_id"),
                "attivo": possessore_info_completa_sel.get("attivo", True),
                "titolo": dettagli_leg["titolo"],
                "quota": dettagli_leg["quota"]
            })
            self._pp_aggiorna_tabella_nuovi_possessori()
        else:
            logging.getLogger("CatastoGUI").info(
                "Aggiunta dettagli legame per PP annullata.")

    def _pp_rimuovi_nuovo_possessore_selezionato(self):
        selected_rows = self.pp_nuovi_possessori_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self, "Nessuna Selezione", "Seleziona un possessore dalla lista dei nuovi possessori da rimuovere.")
            return
        row_to_remove = selected_rows[0].row()
        if 0 <= row_to_remove < len(self._pp_temp_nuovi_possessori):
            del self._pp_temp_nuovi_possessori[row_to_remove]
            self._pp_aggiorna_tabella_nuovi_possessori()

    def _pp_aggiorna_tabella_nuovi_possessori(self):
        table = self.pp_nuovi_possessori_table
        table.setRowCount(0)
        table.setSortingEnabled(False)
        if self._pp_temp_nuovi_possessori:
            table.setRowCount(len(self._pp_temp_nuovi_possessori))
            for r, pd in enumerate(self._pp_temp_nuovi_possessori):
                table.setItem(r, 0, QTableWidgetItem(
                    str(pd.get("possessore_id"))))
                table.setItem(r, 1, QTableWidgetItem(pd.get("nome_completo")))
                table.setItem(r, 2, QTableWidgetItem(pd.get("titolo")))
                table.setItem(r, 3, QTableWidgetItem(pd.get("quota", "")))
            table.resizeColumnsToContents()
        table.setSortingEnabled(True)

    def _load_partita_sorgente_from_spinbox(self):
        """
        Carica i dettagli della partita sorgente usando l'ID
        inserito nello QSpinBox self.source_partita_id_spinbox.
        """
        partita_id_val = self.source_partita_id_spinbox.value()
        if partita_id_val > 0:
            self.selected_partita_id_source = partita_id_val  # Imposta l'ID della sorgente
            # Chiamata al metodo esistente che carica e visualizza i dettagli della partita sorgente
            # e popola anche la tabella degli immobili nel tab "Trasferisci Immobile"
            self._aggiorna_info_partita_sorgente()
        else:
            QMessageBox.warning(
                self, "ID Non Valido", "Inserire un ID partita sorgente valido (maggiore di zero).")
            # Potrebbe voler resettare le info se l'ID non è valido
            self.selected_partita_id_source = None
            # Chiamata per pulire le label e le tabelle
            self._aggiorna_info_partita_sorgente()

    # --- MODIFICA IN _esegui_passaggio_proprieta PER LEGGERE DA COMBOBOX ---
    def _esegui_passaggio_proprieta(self):
        self.logger.info("Avvio _esegui_passaggio_proprieta.")

        # --- 1. Validazione Dati Partita Sorgente ---
        if self.selected_partita_id_source is None or self.selected_partita_comune_id_source is None:
            QMessageBox.warning(self, "Selezione Mancante", "Selezionare una partita sorgente valida prima di procedere.")
            return

        # --- 2. Validazione Dati Nuova Partita ---
        nuova_part_num = self.pp_nuova_partita_numero_spinbox.value()
        suffisso_nuova_partita = self.pp_suffisso_nuova_partita_edit.text().strip() or None # Leggi il suffisso
        if nuova_part_num <= 0:
            QMessageBox.warning(self, "Dati Mancanti", "Il 'Numero Nuova Partita' non può essere zero o negativo.")
            self.pp_nuova_partita_numero_spinbox.setFocus()
            self.pp_nuova_partita_numero_spinbox.selectAll()
            return

        try:
                # La ricerca di esistenza deve ora usare anche il suffisso
                existing_partita_check = self.db_manager.search_partite(
                    comune_id=self.selected_partita_comune_id_source,
                    numero_partita=nuova_part_num,
                    suffisso_partita=suffisso_nuova_partita # PASSA IL SUFFISSO ALLA RICERCA
                )
                if existing_partita_check:
                    QMessageBox.warning(self, "Errore Creazione Partita",
                                        f"Esiste già una partita con il numero {nuova_part_num} "
                                        f"{('('+suffisso_nuova_partita+')' if suffisso_nuova_partita else '')} "
                                        f"nel comune '{self.selected_partita_comune_nome_source}'. Scegliere un numero/suffisso diverso.")
                    self.pp_nuova_partita_numero_spinbox.setFocus()
                    return
        except DBMError as e:
            self.logger.error(f"Errore DB durante la verifica di esistenza della nuova partita: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Verifica Partita",
                                 f"Errore durante la verifica di disponibilità del numero partita:\n{str(e)}")
            return
        except Exception as e:
            self.logger.critical(f"Errore imprevisto durante la verifica di esistenza della nuova partita: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore inatteso durante la verifica del numero partita:\n{str(e)}")
            return


        # --- 3. Validazione Dati Atto/Contratto ---
        tipo_variazione = self.pp_tipo_variazione_combo.currentText()
        if not tipo_variazione or tipo_variazione.strip() == "Seleziona Tipo...": # Assicurati che non sia il placeholder
            QMessageBox.warning(self, "Dati Atto Mancanti", "Selezionare un 'Tipo Variazione' valido.")
            self.pp_tipo_variazione_combo.setFocus()
            return

        data_variazione_q = self.pp_data_variazione_edit.date()
        if not data_variazione_q.isValid():
            QMessageBox.warning(self, "Dati Atto Mancanti", "La 'Data Variazione' è obbligatoria e deve essere valida.")
            self.pp_data_variazione_edit.setFocus()
            return
        data_variazione = data_variazione_q.toPyDate()

        # Leggi il tipo di contratto dalla QComboBox e validalo
        tipo_contratto = self.pp_tipo_contratto_combo.currentText()
        if tipo_contratto == "Seleziona Tipo..." or not tipo_contratto.strip():
            QMessageBox.warning(self, "Dati Atto Mancanti", "Selezionare un 'Tipo Atto/Contratto' valido.")
            self.pp_tipo_contratto_combo.setFocus()
            return
        
        data_contratto_q = self.pp_data_contratto_edit.date()
        if not data_contratto_q.isValid():
            QMessageBox.warning(self, "Dati Atto Mancanti", "La 'Data Atto/Contratto' è obbligatoria e deve essere valida.")
            self.pp_data_contratto_edit.setFocus()
            return
        data_contratto = data_contratto_q.toPyDate()

        # Altri campi opzionali
        notaio = self.pp_notaio_edit.text().strip() or None
        repertorio = self.pp_repertorio_edit.text().strip() or None
        note_v = self.pp_note_variazione_edit.toPlainText().strip() or None
        suffisso_nuova_partita=suffisso_nuova_partita # AGGIUNTO

        # --- 4. Validazione Nuovi Possessori ---
        if not self._pp_temp_nuovi_possessori:
            QMessageBox.warning(self, "Possessori Mancanti", "Aggiungere almeno un nuovo possessore per la nuova partita.")
            # Puoi anche impostare il focus al pulsante "Aggiungi Possessore" qui
            return
        
        # Prepara la lista di possessori per il DB, includendo i dettagli del legame
        lista_possessori_per_db = []
        for poss_data_ui in self._pp_temp_nuovi_possessori:
            # Assicurati che tutte le chiavi necessarie alla procedura SQL siano presenti nel dizionario
            lista_possessori_per_db.append({
                "possessore_id": poss_data_ui.get("possessore_id"),
                "nome_completo": poss_data_ui.get("nome_completo"),
                "cognome_nome": poss_data_ui.get("cognome_nome"), # Potrebbe non essere sempre presente o obbligatorio
                "paternita": poss_data_ui.get("paternita"),       # Potrebbe non essere sempre presente o obbligatorio
                "comune_id": poss_data_ui.get("comune_riferimento_id"), # ID del comune di riferimento del possessore
                "attivo": poss_data_ui.get("attivo", True),
                "titolo": poss_data_ui.get("titolo"),
                "quota": poss_data_ui.get("quota")
            })
        self.logger.debug(f"PP: Lista possessori inviata al DBManager: {lista_possessori_per_db}")


        # --- 5. Validazione e Selezione Immobili da Trasferire ---
        imm_ids_trasf: List[int] = []
        if self.pp_trasferisci_tutti_immobili_check.isChecked():
            # Se la checkbox "Includi TUTTI" è spuntata, raccogli tutti gli ID immobili dal table model
            source_table_immobili = self.immobili_partita_sorgente_table # Questa tabella è popolata con gli immobili della sorgente
            for r in range(source_table_immobili.rowCount()):
                id_itm_widget = source_table_immobili.item(r, 0) # Assumendo ID Imm. è nella prima colonna
                if id_itm_widget and id_itm_widget.text().isdigit():
                    imm_ids_trasf.append(int(id_itm_widget.text()))
            
            if not imm_ids_trasf:
                QMessageBox.warning(self, "Immobili Mancanti", "La partita sorgente non contiene immobili da trasferire, ma 'Includi TUTTI' è selezionato.")
                return

        else:
            # Altrimenti, raccogli solo gli ID degli immobili selezionati individualmente nella tabella
            sel_tbl_imm = self.pp_immobili_da_selezionare_table
            for r in range(sel_tbl_imm.rowCount()):
                chk_widget = sel_tbl_imm.cellWidget(r, 0) # La checkbox è nella colonna 0
                if isinstance(chk_widget, QCheckBox) and chk_widget.isChecked():
                    id_itm_widget = sel_tbl_imm.item(r, 1) # L'ID immobile è nella colonna 1 (dopo la checkbox)
                    if id_itm_widget and id_itm_widget.text().isdigit():
                        imm_ids_trasf.append(int(id_itm_widget.text()))
            
            if not imm_ids_trasf:
                QMessageBox.warning(self, "Immobili Mancanti", "Nessun immobile è stato selezionato per il trasferimento. Selezionare almeno un immobile o spuntare 'Includi TUTTI'.")
                return

        self.logger.debug(f"PP: Immobili da trasferire IDs: {imm_ids_trasf}")

        # --- 6. Esecuzione della Procedura nel DBManager ---
        try:
            success = self.db_manager.registra_passaggio_proprieta(
                partita_origine_id=self.selected_partita_id_source,
                comune_id_nuova_partita=self.selected_partita_comune_id_source,
                numero_nuova_partita=nuova_part_num,
                tipo_variazione=tipo_variazione,
                data_variazione=data_variazione,
                tipo_contratto=tipo_contratto,
                data_contratto=data_contratto,
                notaio=notaio,
                repertorio=repertorio,
                nuovi_possessori_list=lista_possessori_per_db,
                immobili_da_trasferire_ids=imm_ids_trasf if imm_ids_trasf else None, # Passa None se lista vuota
                note_variazione=note_v
            )

            # --- 7. Gestione del Successo o Fallimento ---
            if success:
                QMessageBox.information(
                    self, "Successo", "Passaggio di proprietà registrato con successo. La nuova partita è stata creata e gli immobili trasferiti.")
                self.logger.info("Passaggio di proprietà eseguito con successo.")
                self._pulisci_campi_passaggio_proprieta() # Chiama un metodo per pulire i campi
                # Ricarica i dati della partita sorgente per riflettere i cambiamenti (es. immobili rimossi)
                self._aggiorna_info_partita_sorgente()
            else:
                # Questo blocco else dovrebbe essere raggiunto solo se il db_manager restituisce False
                # senza sollevare eccezioni, ma le eccezioni sono preferibili.
                self.logger.error("registra_passaggio_proprieta ha restituito False senza eccezioni.")
                QMessageBox.critical(self, "Errore Operazione", "Il passaggio di proprietà non è stato completato (errore sconosciuto). Controllare i log.")

        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            self.logger.error(f"Errore DB durante la registrazione del passaggio di proprietà: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Operazione",
                                 f"Impossibile registrare il passaggio di proprietà a causa di un errore nel database:\n{str(e)}")
        except Exception as e_gen:
            self.logger.critical(f"Errore imprevisto durante l'esecuzione del passaggio di proprietà: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto",
                                 f"Si è verificato un errore di sistema inatteso durante l'operazione:\n{type(e_gen).__name__}: {str(e_gen)}")

    # --- NUOVO METODO: Per pulire i campi del tab Passaggio Proprietà dopo il successo ---
    def _pulisci_campi_passaggio_proprieta(self):
        self.pp_nuova_partita_numero_spinbox.setValue(self.pp_nuova_partita_numero_spinbox.minimum())
        self.pp_tipo_variazione_combo.setCurrentIndex(0)
        self.pp_data_variazione_edit.setDate(QDate.currentDate())
        self.pp_tipo_contratto_combo.setCurrentIndex(0) # Resetta la ComboBox
        self.pp_data_contratto_edit.setDate(QDate.currentDate())
        self.pp_notaio_edit.clear()
        self.pp_repertorio_edit.clear()
        self.pp_note_variazione_edit.clear()
        self.pp_trasferisci_tutti_immobili_check.setChecked(True) # Reimposta a default
        self._pp_temp_nuovi_possessori.clear() # Pulisci la lista interna
        self._pp_aggiorna_tabella_nuovi_possessori() # Aggiorna la tabella visualizzata
        self.logger.info("Campi del form Passaggio Proprietà puliti.")


    def seleziona_e_carica_partita_sorgente(self, partita_id: int):
        """Imposta l'ID della partita sorgente e carica i suoi dettagli."""
        logging.getLogger("CatastoGUI").info(
            f"OperazioniPartitaWidget: Impostazione partita sorgente ID: {partita_id} da chiamata esterna.")
        self.source_partita_id_spinbox.setValue(partita_id)
        # Usa il metodo esistente per caricare i dati
        self._load_partita_sorgente_from_spinbox()


class EsportazioniWidget(QWidget):
    # --- AGGIUNGERE QUESTO ATTRIBUTO DI CLASSE IN CIMA ---
    HEADER_MAPPINGS = {
        "Elenco Possessori": {
            "id": "ID Possessore",
            "comune_nome": "Comune di Riferimento",
            "cognome_nome": "Cognome e Nome",
            "paternita": "Paternità",
            "nome_completo": "Nome Completo",
            "attivo": "Stato Attivo",
            "num_partite": "Numero Partite Associate"
        },
        "Elenco Partite": {
            "id": "ID Partita",
            "numero_partita": "Numero Partita",
            "suffisso_partita": "Suffisso",
            "tipo": "Tipo",
            "stato": "Stato",
            "data_impianto": "Data Impianto",
            "num_possessori": "Num. Possessori",
            "num_immobili": "Num. Immobili",
            "num_documenti_allegati": "Num. Documenti"
        }
    }
    # --- FINE AGGIUNTA ---
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self._data_loaded = False

        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        selection_group = QGroupBox("Selezione Dati da Esportare")
        selection_layout = QFormLayout(selection_group)
        selection_layout.setSpacing(10)

        self.export_type_combo = QComboBox()
        self.export_type_combo.addItems(["Elenco Possessori", "Elenco Partite"])
        selection_layout.addRow("Tipo di Esportazione:", self.export_type_combo)

        self.comune_filter_combo = QComboBox()
        selection_layout.addRow("Filtra per Comune (*):", self.comune_filter_combo)
        
        main_layout.addWidget(selection_group)

        format_group = QGroupBox("Formato di Esportazione")
        format_layout = QHBoxLayout(format_group)
        format_layout.setSpacing(10)

        self.btn_export_csv = QPushButton("Esporta in CSV")
        self.btn_export_csv.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_export_csv.clicked.connect(self._handle_export_csv)
        format_layout.addWidget(self.btn_export_csv)
        
        # --- NUOVI PULSANTI ---
        self.btn_export_xls = QPushButton("Esporta in XLS (Excel)")
        self.btn_export_xls.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_export_xls.clicked.connect(self._handle_export_xls)
        format_layout.addWidget(self.btn_export_xls)

        self.btn_export_pdf = QPushButton("Esporta in PDF")
        self.btn_export_pdf.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_export_pdf.clicked.connect(self._handle_export_pdf)
        self.btn_export_pdf.setEnabled(FPDF_AVAILABLE)
        format_layout.addWidget(self.btn_export_pdf)
        # --- FINE NUOVI PULSANTI ---
        
        format_layout.addStretch()
        main_layout.addWidget(format_group)

        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        
        # --- SEZIONE MODIFICATA: Log di stato ---
        # Sostituiamo QTextEdit con QTextBrowser per una gestione dei link più robusta
        self.status_log = QTextBrowser()
        self.status_log.setPlaceholderText("I messaggi di stato dell'esportazione appariranno qui...")
        
        # QTextBrowser è già di sola lettura di default, non serve setReadOnly(True)
        
        # Questo metodo ESISTE su QTextBrowser e ci dà il controllo sui click
        self.status_log.setOpenLinks(False)
        
        # Il segnale anchorClicked è garantito su QTextBrowser
        self.status_log.anchorClicked.connect(self._open_export_file_link)
        
        main_layout.addWidget(self.status_log, 1)

        self.setLayout(main_layout)
        # --- FINE SEZIONE MODIFICATA ---

        main_layout.addWidget(self.status_log, 1)

        self.setLayout(main_layout)

    # I metodi load_initial_data, _get_export_parameters, _fetch_data_for_export, _handle_export_csv
    # rimangono invariati rispetto alla versione precedente. Li includo per completezza.

    def load_initial_data(self):
        if self._data_loaded: return
        try:
            comuni = self.db_manager.get_elenco_comuni_semplice()
            self.comune_filter_combo.clear()
            # Rimuovo l'opzione "Tutti i Comuni" per ora, per semplicità
            self.comune_filter_combo.addItem("--- Seleziona un Comune ---", None)
            for id_comune, nome in comuni:
                self.comune_filter_combo.addItem(nome, id_comune)
            self._data_loaded = True
        except DBMError as e:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare l'elenco dei comuni:\n{e}")

    def _get_export_parameters(self):
        export_type = self.export_type_combo.currentText()
        comune_id = self.comune_filter_combo.currentData()
        comune_name = self.comune_filter_combo.currentText()
        if comune_id is None:
            QMessageBox.warning(self, "Selezione Mancante", "Per favore, seleziona un comune.")
            return None, None, None
        return export_type, comune_id, comune_name

    def _fetch_data_for_export(self, export_type, comune_id):
        self.status_log.append(f"Recupero dati per '{export_type}' del comune ID {comune_id}...")
        QApplication.processEvents()
        if export_type == "Elenco Possessori":
            return self.db_manager.get_possessori_by_comune(comune_id)
        elif export_type == "Elenco Partite":
            return self.db_manager.get_partite_by_comune(comune_id)
        return None

    def _handle_export_csv(self):
        export_type, comune_id, comune_name = self._get_export_parameters()
        if not export_type: return
        data = self._fetch_data_for_export(export_type, comune_id)
        if not data:
            QMessageBox.information(self, "Nessun Dato", "Nessun dato trovato per i criteri selezionati.")
            return

        header_map = self.HEADER_MAPPINGS.get(export_type, {})
        # Se non c'è una mappa, usa le chiavi originali come fallback
        ordered_keys = list(header_map.keys()) if header_map else list(data[0].keys())
        user_friendly_headers = list(header_map.values()) if header_map else ordered_keys

        type_slug = export_type.lower().replace(" ", "_")
        default_filename_base = f"{type_slug}_{comune_name.replace(' ', '_')}_{date.today().isoformat()}.csv"
        full_default_path = _get_default_export_path(default_filename_base)
        
        filename, _ = QFileDialog.getSaveFileName(self, f"Esporta {export_type} in CSV", full_default_path, "File CSV (*.csv)")
        if not filename: return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                writer.writerow(user_friendly_headers) # Scrive le intestazioni "belle"
                # Scrive i dati accedendovi tramite le chiavi originali ordinate
                for row_dict in data:
                    writer.writerow([row_dict.get(key) for key in ordered_keys])
            
            self.status_log.append(f"<font color='green'>Esportazione CSV completata con successo.")
            QMessageBox.information(self, "Successo", f"{len(data)} record esportati con successo.")
        except Exception as e:
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file CSV:\n{e}")


    # --- NUOVI METODI PER XLS E PDF ---

    def _handle_export_xls(self):
        export_type, comune_id, comune_name = self._get_export_parameters()
        if not export_type: return
        data = self._fetch_data_for_export(export_type, comune_id)
        if not data:
            QMessageBox.information(self, "Nessun Dato", "Nessun dato trovato per l'esportazione.")
            return

        header_map = self.HEADER_MAPPINGS.get(export_type, {})

        type_slug = export_type.lower().replace(" ", "_")
        default_filename_base = f"{type_slug}_{comune_name.replace(' ', '_')}_{date.today().isoformat()}.xlsx"
        full_default_path = _get_default_export_path(default_filename_base)

        filename, _ = QFileDialog.getSaveFileName(self, f"Esporta {export_type} in Excel", full_default_path, "File Excel (*.xlsx)")
        if not filename: return
            
        try:
            df = pd.DataFrame(data)
            # Seleziona solo le colonne che abbiamo mappato, nell'ordine corretto
            if header_map:
                df = df[list(header_map.keys())]
            # Rinomina le colonne del DataFrame usando la nostra mappa
            df.rename(columns=header_map, inplace=True)
            
            df.to_excel(filename, index=False, engine='openpyxl')
            
            # Crea il link cliccabile per il log
            file_url = QUrl.fromLocalFile(filename).toString()
            base_name = os.path.basename(filename)
            success_message = f"<font color='green'>Esportazione Excel completata: <a href='{file_url}'>{base_name}</a></font>"
            self.status_log.append(success_message)
            QMessageBox.information(self, "Successo", f"{len(data)} record esportati con successo.")

        except ImportError:
            self.logger.error("La libreria 'pandas' o 'openpyxl' non è installata.")
            QMessageBox.critical(self, "Libreria Mancante", "L'esportazione in Excel richiede le librerie 'pandas' e 'openpyxl'.\nInstallale con il comando: pip install pandas openpyxl")
        except Exception as e:
            self.logger.error(f"Errore durante l'esportazione Excel di '{export_type}': {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file Excel:\n{e}")

    def _handle_export_pdf(self):
        export_type, comune_id, comune_name = self._get_export_parameters()
        if not export_type: return
        data = self._fetch_data_for_export(export_type, comune_id)
        if not data:
            QMessageBox.information(self, "Nessun Dato", "Nessun dato trovato per l'esportazione.")
            return

        header_map = self.HEADER_MAPPINGS.get(export_type, {})
        ordered_keys = list(header_map.keys()) if header_map else list(data[0].keys())
        user_friendly_headers = list(header_map.values()) if header_map else ordered_keys

        type_slug = export_type.lower().replace(" ", "_")
        default_filename_base = f"{type_slug}_{comune_name.replace(' ', '_')}_{date.today().isoformat()}.pdf"
        full_default_path = _get_default_export_path(default_filename_base)
        
        filename, _ = QFileDialog.getSaveFileName(self, f"Esporta {export_type} in PDF", full_default_path, "File PDF (*.pdf)")
        if not filename: return

        try:
            pdf_title = f"{export_type} - Comune di {comune_name}"
            pdf = BulkReportPDF(report_title=pdf_title)
            
            # Trasforma i dati per la tabella PDF, usando le chiavi ordinate
            data_rows = [[str(row.get(key, '')) for key in ordered_keys] for row in data]
            
            pdf.print_table(user_friendly_headers, data_rows) # Usa le intestazioni "belle"
            pdf.output(filename)
            
            file_url = QUrl.fromLocalFile(filename).toString()
            base_name = os.path.basename(filename)
            success_message = f"<font color='green'>Esportazione PDF completata: <a href='{file_url}'>{base_name}</a></font>"
            self.status_log.append(success_message)
            QMessageBox.information(self, "Successo", f"{len(data)} record esportati con successo.")
        except Exception as e:
            self.logger.error(f"Errore durante l'esportazione PDF di '{export_type}': {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file PDF:\n{e}")
    def _open_export_file_link(self, url: QUrl):
        """Apre il file locale puntato dall'URL cliccato nel log."""
        self.logger.info(f"Tentativo di aprire il file dal link: {url.toLocalFile()}")
        QDesktopServices.openUrl(url)


# In gui_widgets.py, SOSTITUISCI l'intera classe ReportisticaWidget con questa:

class ReportisticaWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(ReportisticaWidget, self).__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # --- Tab Report Proprietà ---
        report_tab = QWidget()
        report_layout = QFormLayout(report_tab) # Usiamo QFormLayout per un aspetto più ordinato
        
        # Selezione Partita
        partita_select_layout_prop = QHBoxLayout()
        self.partita_id_edit = QSpinBox(); self.partita_id_edit.setRange(1, 9999999)
        self.search_partita_button = QPushButton("Cerca..."); self.search_partita_button.clicked.connect(self.search_partita_prop)
        partita_select_layout_prop.addWidget(self.partita_id_edit)
        partita_select_layout_prop.addWidget(self.search_partita_button)
        report_layout.addRow("ID Partita:", partita_select_layout_prop)

        # Label per mostrare i dettagli della partita selezionata (incluso suffisso)
        self.partita_info_label_prop = QLabel("Nessuna partita selezionata.")
        self.partita_info_label_prop.setStyleSheet("font-style: italic; color: #555;")
        report_layout.addRow(self.partita_info_label_prop)

        self.generate_cert_button = QPushButton("Genera Report Proprietà"); self.generate_cert_button.clicked.connect(self.generate_report_proprieta)
        report_layout.addRow(self.generate_cert_button)
        
        self.tabs.addTab(report_tab, "Report Proprietà")

        # --- Tab Report Genealogico ---
        genealogico_tab = QWidget()
        genealogico_layout = QFormLayout(genealogico_tab)

        partita_select_layout_gen = QHBoxLayout()
        self.partita_id_gen_edit = QSpinBox(); self.partita_id_gen_edit.setRange(1, 9999999)
        self.search_partita_gen_button = QPushButton("Cerca..."); self.search_partita_gen_button.clicked.connect(self.search_partita_gen)
        partita_select_layout_gen.addWidget(self.partita_id_gen_edit)
        partita_select_layout_gen.addWidget(self.search_partita_gen_button)
        genealogico_layout.addRow("ID Partita:", partita_select_layout_gen)

        self.partita_info_label_gen = QLabel("Nessuna partita selezionata.")
        self.partita_info_label_gen.setStyleSheet("font-style: italic; color: #555;")
        genealogico_layout.addRow(self.partita_info_label_gen)

        self.generate_gen_button = QPushButton("Genera Report Genealogico"); self.generate_gen_button.clicked.connect(self.generate_genealogico)
        genealogico_layout.addRow(self.generate_gen_button)
        
        self.tabs.addTab(genealogico_tab, "Report Genealogico")

        # --- Tab Report Possessore (logica di selezione e generazione invariata) ---
        possessore_tab = QWidget()
        # ... (la UI di questo tab può rimanere la stessa, ma la aggiungeremo al nostro layout principale)
        possessore_layout = QFormLayout(possessore_tab)
        self.possessore_id_edit = QSpinBox(); self.possessore_id_edit.setRange(1, 9999999)
        self.search_possessore_button = QPushButton("Cerca..."); self.search_possessore_button.clicked.connect(self.search_possessore)
        possessore_select_layout = QHBoxLayout(); possessore_select_layout.addWidget(self.possessore_id_edit); possessore_select_layout.addWidget(self.search_possessore_button)
        possessore_layout.addRow("ID Possessore:", possessore_select_layout)
        self.generate_pos_button = QPushButton("Genera Report Possessore"); self.generate_pos_button.clicked.connect(self.generate_possessore)
        possessore_layout.addRow(self.generate_pos_button)
        self.tabs.addTab(possessore_tab, "Report Possessore")

        # --- Tab Report Consultazioni (invariato) ---
        consultazioni_tab = QWidget()
        # ... (la UI di questo tab è già funzionale)
        consultazioni_layout = QVBoxLayout(consultazioni_tab)
        # ... (aggiungi qui la UI del tab consultazioni come era prima)
        self.tabs.addTab(consultazioni_tab, "Report Consultazioni")
        
        main_layout.addWidget(self.tabs)

        # --- NUOVO: Area di output per i report e log esportazioni ---
        output_group = QGroupBox("Anteprima Report e Log Esportazioni")
        output_layout = QVBoxLayout(output_group)
        self.report_output_browser = QTextBrowser() # Usiamo QTextBrowser per i link
        self.report_output_browser.setOpenLinks(False)
        self.report_output_browser.anchorClicked.connect(self._open_export_file_link)
        self.report_output_browser.setPlaceholderText("L'anteprima del report generato e i link ai file esportati appariranno qui.")
        output_layout.addWidget(self.report_output_browser)
        
        export_buttons_layout = QHBoxLayout()
        self.export_txt_button = QPushButton("Esporta Report in TXT"); self.export_txt_button.clicked.connect(self._export_current_report_txt)
        self.export_pdf_button = QPushButton("Esporta Report in PDF"); self.export_pdf_button.clicked.connect(self._export_current_report_pdf); self.export_pdf_button.setEnabled(FPDF_AVAILABLE)
        export_buttons_layout.addStretch(); export_buttons_layout.addWidget(self.export_txt_button); export_buttons_layout.addWidget(self.export_pdf_button)
        output_layout.addLayout(export_buttons_layout)

        main_layout.addWidget(output_group, 1) # Stretch factor 1 per dare spazio
        self.setLayout(main_layout)

    def _open_export_file_link(self, url: QUrl):
        QDesktopServices.openUrl(url)

    def _update_partita_info_label(self, label_widget, partita_id):
        """Aggiorna una label con i dettagli (numero, suffisso, comune) di una partita."""
        if partita_id is None:
            label_widget.setText("Nessuna partita selezionata.")
            return
        
        details = self.db_manager.get_partita_details(partita_id)
        if details:
            suffisso_str = f"(Suffisso: {details.get('suffisso_partita')})" if details.get('suffisso_partita') else "(Nessun Suffisso)"
            label_widget.setText(f"Selezionata: N. {details.get('numero_partita')} {suffisso_str} - Comune: {details.get('comune_nome')}")
        else:
            label_widget.setText(f"<font color='red'>Partita ID {partita_id} non trovata.</font>")

    def search_partita_prop(self):
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_partita_id:
            self.partita_id_edit.setValue(dialog.selected_partita_id)
            self._update_partita_info_label(self.partita_info_label_prop, dialog.selected_partita_id)

    def search_partita_gen(self):
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_partita_id:
            self.partita_id_gen_edit.setValue(dialog.selected_partita_id)
            self._update_partita_info_label(self.partita_info_label_gen, dialog.selected_partita_id)

    def search_possessore(self):
        dialog = PossessoreSelectionDialog(db_manager=self.db_manager, comune_id=None, parent=self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_possessore:
            self.possessore_id_edit.setValue(dialog.selected_possessore.get('id', 0))

    def generate_report_proprieta(self):
        partita_id = self.partita_id_edit.value()
        if partita_id <= 0: return QMessageBox.warning(self, "Errore", "Selezionare un ID partita valido.")
        report = self.db_manager.genera_report_proprieta(partita_id)
        # --- MODIFICA QUI ---
        # Usiamo setPlainText per garantire che il contenuto sia interpretato come testo semplice
        self.report_output_browser.setPlainText(report or f"Nessun report generato per la partita ID {partita_id}.")
        # --- FINE MODIFICA --

    def generate_genealogico(self):
        partita_id = self.partita_id_gen_edit.value()
        if partita_id <= 0: return QMessageBox.warning(self, "Errore", "Selezionare un ID partita valido.")
        report = self.db_manager.genera_report_genealogico(partita_id)
        self.report_output_browser.setPlainText(report or f"Nessun report genealogico generato per la partita ID {partita_id}.")

    def generate_possessore(self):
        possessore_id = self.possessore_id_edit.value()
        if possessore_id <= 0: return QMessageBox.warning(self, "Errore", "Selezionare un ID possessore valido.")
        report = self.db_manager.genera_report_possessore(possessore_id)
        self.report_output_browser.setPlainText(report or f"Nessun report generato per il possessore ID {possessore_id}.")
        
    # La generazione del report consultazioni può rimanere in un dialogo separato o essere integrata qui.
    # Per ora la omettiamo dal nuovo layout per semplicità.

    def _export_current_report_txt(self):
        report_content = self.report_output_browser.toPlainText()
        if not report_content.strip():
            QMessageBox.warning(self, "Nessun Contenuto", "Generare un report prima di esportarlo.")
            return
        
        default_filename_base = f"report_catasto_{date.today().isoformat()}.txt"
        full_default_path = _get_default_export_path(default_filename_base)
        
        filename, _ = QFileDialog.getSaveFileName(self, "Salva Report TXT", full_default_path, "File di testo (*.txt)")
        if not filename: return
            
        try:
            with open(filename, 'w', encoding='utf-8') as f: f.write(report_content)
            file_url = QUrl.fromLocalFile(filename).toString(); base_name = os.path.basename(filename)
            self.report_output_browser.append(f"\n<hr><font color='green'>Report esportato con successo: <a href='{file_url}'>{base_name}</a></font>")
        except Exception as e:
            QMessageBox.critical(self, "Errore Esportazione", f"Impossibile salvare il file:\n{e}")

    def _export_current_report_pdf(self):
        report_content = self.report_output_browser.toPlainText()
        if not report_content.strip():
            QMessageBox.warning(self, "Nessun Contenuto", "Generare un report prima di esportarlo.")
            return
        
        default_filename_base = f"report_catasto_{date.today().isoformat()}.pdf"
        full_default_path = _get_default_export_path(default_filename_base)
        
        filename, _ = QFileDialog.getSaveFileName(self, "Salva Report PDF", full_default_path, "File PDF (*.pdf)")
        if not filename: return
            
        try:
            pdf = GenericTextReportPDF(report_title="Report Catasto Storico")
            pdf.add_page()
            pdf.add_report_text(report_content)
            pdf.output(filename)
            
            file_url = QUrl.fromLocalFile(filename).toString(); base_name = os.path.basename(filename)
            self.report_output_browser.append(f"\n<hr><font color='green'>Report PDF esportato: <a href='{file_url}'>{base_name}</a></font>")
        except Exception as e:
            QMessageBox.critical(self, "Errore Esportazione PDF", f"Impossibile generare il PDF:\n{e}")
# *** NUOVO: Classe DocumentViewerDialog ***
# Questa classe viene spostata qui per chiarezza e per essere inclusa nella riscrittura completa

class StatisticheWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(StatisticheWidget, self).__init__(parent)
        self.db_manager = db_manager

        layout = QVBoxLayout()

        # Tabs per le diverse statistiche
        tabs = QTabWidget()

        # Tab Statistiche per Comune
        stats_comune_tab = QWidget()
        stats_comune_layout = QVBoxLayout()

        refresh_stats_button = QPushButton("Aggiorna Statistiche")
        refresh_stats_button.clicked.connect(self.refresh_stats_comune)

        self.stats_comune_table = QTableWidget()
        self.stats_comune_table.setColumnCount(7)
        self.stats_comune_table.setHorizontalHeaderLabels([
            "Comune", "Provincia", "Totale Partite", "Partite Attive",
            "Partite Inattive", "Totale Possessori", "Totale Immobili"
        ])
        self.stats_comune_table.setAlternatingRowColors(True)
        self.stats_comune_table.horizontalHeader().setStretchLastSection(True)

        stats_comune_layout.addWidget(refresh_stats_button)
        stats_comune_layout.addWidget(self.stats_comune_table)

        stats_comune_tab.setLayout(stats_comune_layout)
        tabs.addTab(stats_comune_tab, "Statistiche per Comune")

        # Tab Immobili per Tipologia
        immobili_tab = QWidget()
        immobili_layout = QVBoxLayout()

        self.comune_filter_button = QPushButton("Filtra per Comune...")
        self.comune_filter_button.clicked.connect(
            self.filter_immobili_per_comune)
        self.comune_filter_id = None
        self.comune_filter_display = QLabel("Visualizzando tutti i comuni")

        self.clear_filter_button = QPushButton("Rimuovi Filtro")
        self.clear_filter_button.clicked.connect(self.clear_immobili_filter)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.comune_filter_button)
        filter_layout.addWidget(self.comune_filter_display)
        filter_layout.addWidget(self.clear_filter_button)

        self.refresh_immobili_button = QPushButton("Aggiorna Statistiche Immobili")
        self.refresh_immobili_button.clicked.connect(self.refresh_immobili_tipologia)

        self.immobili_table = QTableWidget()
        self.immobili_table.setColumnCount(6)
        self.immobili_table.setHorizontalHeaderLabels([
            "Comune", "Classificazione", "Numero Immobili", 
            "Totale Piani", "Totale Vani", "Media Vani/Immobile"
        ])
        self.immobili_table.setAlternatingRowColors(True)
        self.immobili_table.horizontalHeader().setStretchLastSection(True)

        immobili_layout.addLayout(filter_layout)
        immobili_layout.addWidget(self.refresh_immobili_button)
        immobili_layout.addWidget(self.immobili_table)

        immobili_tab.setLayout(immobili_layout)
        tabs.addTab(immobili_tab, "Immobili per Tipologia")

        # Tab per Aggiornamento Viste Materializzate (SPOSTATO QUI)
        viste_tab = QWidget()
        viste_layout = QVBoxLayout()

        viste_layout.addWidget(QLabel("Aggiornamento Viste Materializzate"))
        viste_layout.addWidget(QLabel("Le viste materializzate migliorano le performance delle statistiche aggregando i dati."))
        
        self.update_views_button = QPushButton("Aggiorna Tutte le Viste Materializzate")
        self.update_views_button.clicked.connect(self.update_all_views)
        self.update_views_button.setToolTip("Aggiorna tutte le viste materializzate del database per migliorare le performance delle statistiche")
        viste_layout.addWidget(self.update_views_button)

        viste_layout.addSpacing(15)
        viste_layout.addWidget(QLabel("Log Operazioni:"))
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setFixedHeight(200)
        viste_layout.addWidget(self.status_text)

        viste_layout.addStretch(1)
        viste_tab.setLayout(viste_layout)
        tabs.addTab(viste_tab, "Aggiornamento Viste")

        layout.addWidget(tabs)
        self.setLayout(layout)

        # Carica dati iniziali
        self.refresh_stats_comune()
        self.refresh_immobili_tipologia()

    def refresh_stats_comune(self):
        """Aggiorna la tabella delle statistiche per comune."""
        self.stats_comune_table.setRowCount(0)

        if not self.db_manager or not self.db_manager.pool:
            logging.getLogger("CatastoGUI").warning(
                "StatisticheWidget: Pool DB non inizializzato. Impossibile caricare statistiche comuni.")
            self.stats_comune_table.setRowCount(1)
            item_msg = QTableWidgetItem(
                "Database non pronto per caricare le statistiche.")
            item_msg.setTextAlignment(Qt.AlignCenter)
            self.stats_comune_table.setItem(0, 0, item_msg)
            self.stats_comune_table.setSpan(
                0, 0, 1, self.stats_comune_table.columnCount())
            return

        stats = self.db_manager.get_statistiche_comune()

        if stats:
            self.stats_comune_table.setRowCount(len(stats))

            for i, s in enumerate(stats):
                self.stats_comune_table.setItem(
                    i, 0, QTableWidgetItem(s.get('comune', '')))
                self.stats_comune_table.setItem(
                    i, 1, QTableWidgetItem(s.get('provincia', '')))
                self.stats_comune_table.setItem(
                    i, 2, QTableWidgetItem(str(s.get('totale_partite', 0))))
                self.stats_comune_table.setItem(
                    i, 3, QTableWidgetItem(str(s.get('partite_attive', 0))))
                self.stats_comune_table.setItem(
                    i, 4, QTableWidgetItem(str(s.get('partite_inattive', 0))))
                self.stats_comune_table.setItem(
                    i, 5, QTableWidgetItem(str(s.get('totale_possessori', 0))))
                self.stats_comune_table.setItem(
                    i, 6, QTableWidgetItem(str(s.get('totale_immobili', 0))))

            self.stats_comune_table.resizeColumnsToContents()
            self.log_status("Statistiche comuni aggiornate.")

    def filter_immobili_per_comune(self):
        """Filtra le statistiche immobili per comune."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_filter_id = dialog.selected_comune_id
            self.comune_filter_display.setText(
                f"Comune: {dialog.selected_comune_name}")
            self.refresh_immobili_tipologia()

    def clear_immobili_filter(self):
        """Rimuove il filtro per comune dalle statistiche immobili."""
        self.comune_filter_id = None
        self.comune_filter_display.setText("Visualizzando tutti i comuni")
        self.refresh_immobili_tipologia()

    def refresh_immobili_tipologia(self):
        """Aggiorna la tabella degli immobili per tipologia."""
        self.immobili_table.setRowCount(0)

        if not self.db_manager or not self.db_manager.pool:
            logging.getLogger("CatastoGUI").warning(
                "StatisticheWidget: Pool DB non inizializzato. Impossibile caricare statistiche immobili.")
            self.immobili_table.setRowCount(1)
            item_msg = QTableWidgetItem(
                "Database non pronto per caricare le statistiche immobili.")
            item_msg.setTextAlignment(Qt.AlignCenter)
            self.immobili_table.setItem(0, 0, item_msg)
            self.immobili_table.setSpan(
                0, 0, 1, self.immobili_table.columnCount())
            return

        stats = self.db_manager.get_immobili_per_tipologia(
            self.comune_filter_id)

        if stats:
            self.immobili_table.setRowCount(len(stats))

            for i, s in enumerate(stats):
                self.immobili_table.setItem(
                    i, 0, QTableWidgetItem(s.get('comune_nome', '')))
                self.immobili_table.setItem(
                    i, 1, QTableWidgetItem(s.get('classificazione', 'N/D')))

                num_immobili = s.get('numero_immobili', 0)
                self.immobili_table.setItem(
                    i, 2, QTableWidgetItem(str(num_immobili)))

                self.immobili_table.setItem(
                    i, 3, QTableWidgetItem(str(s.get('totale_piani', 0))))

                totale_vani = s.get('totale_vani', 0)
                self.immobili_table.setItem(
                    i, 4, QTableWidgetItem(str(totale_vani)))

                # Calcola media vani/immobile
                media_vani = round(totale_vani / num_immobili,
                                   2) if num_immobili > 0 else 0
                self.immobili_table.setItem(
                    i, 5, QTableWidgetItem(str(media_vani)))

            self.immobili_table.resizeColumnsToContents()

            status_text = "Dati immobili aggiornati"
            if self.comune_filter_id:
                comune_nome = self.comune_filter_display.text().replace("Comune: ", "")
                status_text += f" (filtrati per {comune_nome})"
            status_text += "."

            self.log_status(status_text)

    def update_all_views(self):
        """Aggiorna tutte le viste materializzate."""
        self.log_status("Avvio aggiornamento di tutte le viste materializzate...")

        if self.db_manager.refresh_materialized_views():
            self.log_status("Aggiornamento viste completato con successo.")

            # Aggiorna le tabelle delle statistiche
            self.refresh_stats_comune()
            self.refresh_immobili_tipologia()
        else:
            self.log_status("ERRORE: Aggiornamento viste non riuscito. Controlla i log.")

    def log_status(self, message, error=False):
        """Aggiunge un messaggio al log delle operazioni con timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        if error:
            self.status_text.append(f"<font color='red'>{formatted_message}</font>")
        else:
            self.status_text.append(formatted_message)
        
        # Scorri automaticamente verso il basso
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum())
        
        # Forza l'aggiornamento della UI
        QApplication.processEvents()

class GestioneUtentiWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, current_user_info: Optional[Dict], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user_info = current_user_info  # Info dell'utente loggato
        self.is_admin = self.current_user_info.get(
            'ruolo') == 'admin' if self.current_user_info else False

        layout = QVBoxLayout(self)

        # Pulsanti Azioni
        action_layout = QHBoxLayout()
        self.btn_crea_utente = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_FileDialogNewFolder), " Crea Nuovo Utente")
        self.btn_crea_utente.clicked.connect(self.crea_nuovo_utente)
        self.btn_crea_utente.setEnabled(self.is_admin)
        action_layout.addWidget(self.btn_crea_utente)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Tabella Utenti
        self.user_table = QTableWidget()
        # ID, Username, Nome Completo, Email, Ruolo, Stato
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(
            ["ID", "Username", "Nome Completo", "Email", "Ruolo", "Stato"])
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.user_table.itemDoubleClicked.connect(self.modifica_utente_selezionato) # Opzionale
        layout.addWidget(self.user_table)

        # Pulsanti di gestione per utente selezionato
        manage_layout = QHBoxLayout()
        self.btn_modifica_utente = QPushButton("Modifica Utente")
        self.btn_modifica_utente.clicked.connect(
            self.modifica_utente_selezionato)
        self.btn_modifica_utente.setEnabled(self.is_admin)

        self.btn_reset_password = QPushButton("Resetta Password")
        self.btn_reset_password.clicked.connect(
            self.reset_password_utente_selezionato)
        self.btn_reset_password.setEnabled(self.is_admin)

        self.btn_toggle_stato = QPushButton("Attiva/Disattiva Utente")
        self.btn_toggle_stato.clicked.connect(
            self.toggle_stato_utente_selezionato)
        self.btn_toggle_stato.setEnabled(self.is_admin)

        self.btn_delete_utente = QPushButton("Elimina Utente")
        self.btn_delete_utente.clicked.connect(self.elimina_utente_selezionato)
        self.btn_delete_utente.setEnabled(self.is_admin)

        manage_layout.addWidget(self.btn_modifica_utente)
        manage_layout.addWidget(self.btn_reset_password)
        manage_layout.addWidget(self.btn_toggle_stato)
        manage_layout.addWidget(self.btn_delete_utente)
        layout.addLayout(manage_layout)

        self.refresh_user_list()

    def refresh_user_list(self):
        self.user_table.setRowCount(0)
        utenti = self.db_manager.get_utenti()  # Prende tutti gli utenti
        for user_data in utenti:
            row_pos = self.user_table.rowCount()
            self.user_table.insertRow(row_pos)
            self.user_table.setItem(
                row_pos, 0, QTableWidgetItem(str(user_data['id'])))
            self.user_table.setItem(
                row_pos, 1, QTableWidgetItem(user_data['username']))
            self.user_table.setItem(
                row_pos, 2, QTableWidgetItem(user_data['nome_completo']))
            self.user_table.setItem(row_pos, 3, QTableWidgetItem(
                user_data.get('email', 'N/D')))
            self.user_table.setItem(
                row_pos, 4, QTableWidgetItem(user_data['ruolo']))
            self.user_table.setItem(row_pos, 5, QTableWidgetItem(
                "Attivo" if user_data['attivo'] else "Non Attivo"))
        self.user_table.resizeColumnsToContents()

    def crea_nuovo_utente(self):
        # CreateUserDialog come definito prima
        dialog = CreateUserDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_user_list()
            QMessageBox.information(self, "Successo", "Nuovo utente creato.")

    def _get_selected_user_id(self) -> Optional[int]:
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Nessuna Selezione",
                                "Per favore, seleziona un utente dalla lista.")
            return None
        try:
            return int(self.user_table.item(selected_rows[0].row(), 0).text())
        except (ValueError, AttributeError):
            QMessageBox.critical(
                self, "Errore", "Impossibile ottenere l'ID dell'utente selezionato.")
            return None

    def modifica_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            return

        utente_attuale = self.db_manager.get_utente_by_id(user_id)
        if not utente_attuale:
            QMessageBox.critical(
                self, "Errore", f"Utente con ID {user_id} non trovato.")
            return

        # Qui aprirebbe un dialogo per modificare i dettagli, simile a CreateUserDialog ma pre-popolato
        # Per semplicità, usiamo QInputDialog per alcuni campi
        nome_attuale = utente_attuale.get('nome_completo', '')
        new_nome, ok = QInputDialog.getText(
            self, "Modifica Nome", f"Nuovo nome completo (attuale: '{nome_attuale}'):", text=nome_attuale)
        if not ok:
            return  # Annullato

        email_attuale = utente_attuale.get('email', '')
        new_email, ok = QInputDialog.getText(
            self, "Modifica Email", f"Nuova email (attuale: '{email_attuale}'):", text=email_attuale)
        if not ok:
            return

        ruoli = ["admin", "archivista", "consultatore"]
        ruolo_attuale = utente_attuale.get('ruolo', 'consultatore')
        new_ruolo, ok = QInputDialog.getItem(self, "Modifica Ruolo", f"Nuovo ruolo (attuale: '{ruolo_attuale}'):", ruoli, ruoli.index(
            ruolo_attuale) if ruolo_attuale in ruoli else 0, False)
        if not ok:
            return

        update_params = {}
        if new_nome and new_nome != nome_attuale:
            update_params['nome_completo'] = new_nome
        if new_email and new_email != email_attuale:
            update_params['email'] = new_email
        if new_ruolo and new_ruolo != ruolo_attuale:
            update_params['ruolo'] = new_ruolo

        if update_params:
            if self.db_manager.update_user_details(user_id, **update_params):
                QMessageBox.information(
                    self, "Successo", "Dettagli utente aggiornati.")
                self.refresh_user_list()
            else:
                QMessageBox.critical(
                    self, "Errore", "Aggiornamento fallito. Controllare i log.")
        else:
            QMessageBox.information(
                self, "Info", "Nessuna modifica apportata.")

    def reset_password_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            return
        if user_id == self.current_user_info.get('id'):
            QMessageBox.warning(self, "Azione Non Permessa",
                                "Non puoi resettare la tua password da questa interfaccia.")
            return

        new_password, ok = QInputDialog.getText(
            self, "Reset Password", "Inserisci la nuova password temporanea:", QLineEdit.Password)
        if ok and new_password:
            new_password_confirm, ok_confirm = QInputDialog.getText(
                self, "Conferma Password", "Conferma la nuova password temporanea:", QLineEdit.Password)
            if ok_confirm and new_password == new_password_confirm:
                try:
                    new_hash = _hash_password(new_password)
                    if self.db_manager.reset_user_password(user_id, new_hash):
                        QMessageBox.information(
                            self, "Successo", f"Password per utente ID {user_id} resettata.")
                    else:
                        QMessageBox.critical(
                            self, "Errore", "Reset password fallito.")
                except Exception as e:
                    QMessageBox.critical(
                        self, "Errore Hashing", f"Errore durante l'hashing: {e}")
            elif ok_confirm:  # ma password non coincidono
                QMessageBox.warning(
                    self, "Errore", "Le password non coincidono.")
        elif ok:  # password vuota
            QMessageBox.warning(
                self, "Errore", "La password non può essere vuota.")

    def toggle_stato_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            return
        if user_id == self.current_user_info.get('id'):
            QMessageBox.warning(self, "Azione Non Permessa",
                                "Non puoi modificare lo stato del tuo account.")
            return

        utente_target = self.db_manager.get_utente_by_id(user_id)
        if not utente_target:
            QMessageBox.critical(self, "Errore", "Utente non trovato.")
            return

        nuovo_stato_attivo = not utente_target['attivo']
        azione_str = "RIATTIVARE" if nuovo_stato_attivo else "DISATTIVARE"

        reply = QMessageBox.question(self, "Conferma Stato",
                                     f"L'utente '{utente_target['username']}' è attualmente {'ATTIVO' if utente_target['attivo'] else 'NON ATTIVO'}.\n"
                                     f"Vuoi {azione_str} questo utente?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            success = False
            if nuovo_stato_attivo:
                success = self.db_manager.activate_user(user_id)
            else:
                success = self.db_manager.deactivate_user(user_id)

            if success:
                QMessageBox.information(
                    self, "Successo", f"Stato utente '{utente_target['username']}' aggiornato.")
                self.refresh_user_list()
            else:
                QMessageBox.critical(
                    self, "Errore", "Aggiornamento stato fallito.")

    def elimina_utente_selezionato(self):
        user_id = self._get_selected_user_id()
        if user_id is None:
            return
        if user_id == self.current_user_info.get('id'):
            QMessageBox.warning(self, "Azione Non Permessa",
                                "Non puoi eliminare te stesso.")
            return

        utente_target = self.db_manager.get_utente_by_id(user_id)
        if not utente_target:
            QMessageBox.critical(self, "Errore", "Utente non trovato.")
            return

        reply = QMessageBox.warning(self, "Conferma Eliminazione",
                                    f"ATTENZIONE: Stai per eliminare PERMANENTEMENTE l'utente '{utente_target['username']}' (ID: {user_id}).\n"
                                    "Questa operazione è IRREVERSIBILE e i riferimenti nei log verranno impostati a NULL (se configurato).\n"
                                    "Sei assolutamente sicuro?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Ulteriore conferma digitando lo username
            confirm_username, ok = QInputDialog.getText(self, "Conferma Finale",
                                                        f"Per confermare l'eliminazione permanente di '{utente_target['username']}', riscrivi il suo username:")
            if ok and confirm_username == utente_target['username']:
                if self.db_manager.delete_user_permanently(user_id):
                    QMessageBox.information(
                        self, "Successo", f"Utente '{utente_target['username']}' eliminato permanentemente.")
                    self.refresh_user_list()
                else:
                    QMessageBox.critical(
                        self, "Errore", "Eliminazione fallita. Controllare i log (es. è l'unico admin attivo?).")
            elif ok:  # Username non corrispondente
                QMessageBox.warning(
                    self, "Annullato", "Username non corrispondente. Eliminazione annullata.")
            # else: l'utente ha premuto annulla su QInputDialog

# Altri Widget per i Tab (da creare)


# In gui_widgets.py, SOSTITUISCI l'intera classe AuditLogViewerWidget con questa:

class AuditLogViewerWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        
        # Stato per la paginazione
        self.current_page = 1
        self.page_size = 100  # Record per pagina
        self.total_records = 0
        self.total_pages = 0
        self.current_filters = {}
        
        # --- MODIFICA QUI ---
        # Aggiungiamo il flag per il lazy loading
        self._data_loaded = False 

        self._init_ui()
        

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # --- Gruppo Filtri e Azioni ---
        filters_group = QGroupBox("Filtri e Azioni")
        top_layout = QVBoxLayout(filters_group)
        
        filters_form_layout = QFormLayout()
        
        self.filter_table_name_edit = QLineEdit()
        filters_form_layout.addRow("Nome Tabella:", self.filter_table_name_edit)

        self.filter_operation_combo = QComboBox()
        self.filter_operation_combo.addItems(["Tutte", "INSERT (I)", "UPDATE (U)", "DELETE (D)"])
        filters_form_layout.addRow("Operazione:", self.filter_operation_combo)

        self.filter_app_user_id_edit = QLineEdit(); self.filter_app_user_id_edit.setPlaceholderText("ID utente (opzionale)")
        filters_form_layout.addRow("ID Utente Applicativo:", self.filter_app_user_id_edit)

        self.filter_start_datetime_edit = QDateTimeEdit(self); self.filter_start_datetime_edit.setDateTime(QDateTime.currentDateTime().addDays(-7)); self.filter_start_datetime_edit.setCalendarPopup(True); self.filter_start_datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        filters_form_layout.addRow("Da Data/Ora:", self.filter_start_datetime_edit)

        self.filter_end_datetime_edit = QDateTimeEdit(self); self.filter_end_datetime_edit.setDateTime(QDateTime.currentDateTime()); self.filter_end_datetime_edit.setCalendarPopup(True); self.filter_end_datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        filters_form_layout.addRow("A Data/Ora:", self.filter_end_datetime_edit)
        
        top_layout.addLayout(filters_form_layout)
        
        # Pulsanti di azione
        action_layout = QHBoxLayout()
        self.search_button = QPushButton("Applica Filtri"); self.search_button.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.search_button.clicked.connect(self._apply_filters_and_search)
        self.reset_button = QPushButton("Resetta Filtri"); self.reset_button.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
        self.reset_button.clicked.connect(self._reset_filters)
        self.export_csv_button = QPushButton("Esporta CSV"); self.export_csv_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.export_csv_button.clicked.connect(self._handle_export_csv)
        self.export_xls_button = QPushButton("Esporta Excel"); self.export_xls_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.export_xls_button.clicked.connect(self._handle_export_xls)
        
        action_layout.addWidget(self.search_button)
        action_layout.addWidget(self.reset_button)
        action_layout.addStretch()
        action_layout.addWidget(self.export_csv_button)
        action_layout.addWidget(self.export_xls_button)
        top_layout.addLayout(action_layout)

        main_layout.addWidget(filters_group)

        # --- Tabella Risultati ---
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(8)
        self.log_table.setHorizontalHeaderLabels(["ID", "Timestamp", "Utente App", "Sessione", "Tabella", "Operazione", "ID Record", "IP"])
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers); self.log_table.setSelectionBehavior(QTableWidget.SelectRows); self.log_table.setSelectionMode(QTableWidget.SingleSelection)
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.log_table.horizontalHeader().setStretchLastSection(True); self.log_table.setAlternatingRowColors(True)
        self.log_table.itemSelectionChanged.connect(self._display_log_details)
        main_layout.addWidget(self.log_table, 1) # Stretch factor per la tabella

        # --- Controlli di Paginazione ---
        pagination_layout = QHBoxLayout()
        self.btn_first_page = QPushButton("<< Prima"); self.btn_first_page.clicked.connect(self._go_to_first_page)
        self.btn_prev_page = QPushButton("< Prec"); self.btn_prev_page.clicked.connect(self._go_to_previous_page)
        self.page_info_label = QLabel("Pagina 1 / 1 (0 risultati)"); self.page_info_label.setAlignment(Qt.AlignCenter)
        self.btn_next_page = QPushButton("Succ >"); self.btn_next_page.clicked.connect(self._go_to_next_page)
        self.btn_last_page = QPushButton("Ultima >>"); self.btn_last_page.clicked.connect(self._go_to_last_page)
        pagination_layout.addStretch(); pagination_layout.addWidget(self.btn_first_page); pagination_layout.addWidget(self.btn_prev_page)
        pagination_layout.addWidget(self.page_info_label); pagination_layout.addWidget(self.btn_next_page); pagination_layout.addWidget(self.btn_last_page); pagination_layout.addStretch()
        main_layout.addLayout(pagination_layout)
        
        # --- Area Dettagli JSON ---
        details_group = QGroupBox("Dettagli Modifica (JSON)")
        details_layout = QHBoxLayout(details_group)
        self.details_before_text = QTextEdit(); self.details_before_text.setReadOnly(True); self.details_before_text.setPlaceholderText("Dati prima della modifica...")
        self.details_after_text = QTextEdit(); self.details_after_text.setReadOnly(True); self.details_after_text.setPlaceholderText("Dati dopo la modifica...")
        details_layout.addWidget(QLabel("Dati Prima:")); details_layout.addWidget(self.details_before_text)
        details_layout.addWidget(QLabel("Dati Dopo:")); details_layout.addWidget(self.details_after_text)
        main_layout.addWidget(details_group)

    def load_initial_data(self):
        """
        Carica i dati iniziali per il visualizzatore di log.
        Viene chiamato una sola volta quando il widget diventa visibile.
        """
        if self._data_loaded:
            return
            
        self.logger.info("AuditLogViewerWidget: Esecuzione lazy loading dei log di audit...")
        self._apply_filters_and_search()
        self._data_loaded = True

    def _apply_filters_and_search(self):
        self.current_filters = {
            "table_name": self.filter_table_name_edit.text().strip() or None,
            "operation_char": None,
            "app_user_id": int(self.filter_app_user_id_edit.text()) if self.filter_app_user_id_edit.text().strip().isdigit() else None,
            "start_datetime": self.filter_start_datetime_edit.dateTime().toPyDateTime(),
            "end_datetime": self.filter_end_datetime_edit.dateTime().toPyDateTime(),
        }
        op_text = self.filter_operation_combo.currentText()
        if "INSERT" in op_text: self.current_filters["operation_char"] = "I"
        elif "UPDATE" in op_text: self.current_filters["operation_char"] = "U"
        elif "DELETE" in op_text: self.current_filters["operation_char"] = "D"
        
        self.current_page = 1
        self._fetch_and_display_logs()

    def _reset_filters(self):
        self.filter_table_name_edit.clear(); self.filter_operation_combo.setCurrentIndex(0)
        self.filter_app_user_id_edit.clear(); self.filter_start_datetime_edit.setDateTime(QDateTime.currentDateTime().addDays(-7))
        self.filter_end_datetime_edit.setDateTime(QDateTime.currentDateTime())
        self._apply_filters_and_search()

    def _fetch_and_display_logs(self):
        self.log_table.setRowCount(0)
        if not self.db_manager or not self.db_manager.pool: return
        try:
            logs, self.total_records = self.db_manager.get_audit_logs(
                filters=self.current_filters, page=self.current_page, page_size=self.page_size
            )
            self.total_pages = (self.total_records + self.page_size - 1) // self.page_size if self.total_records > 0 else 1
            
            self.log_table.setRowCount(len(logs))
            for row_idx, log in enumerate(logs):
                item_id = QTableWidgetItem(str(log.get('id', ''))); item_id.setData(Qt.UserRole, log)
                ts = log.get('timestamp'); ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "N/D"
                session_id = log.get('session_id', ''); session_display = (session_id[:8] + '...') if session_id else ''
                self.log_table.setItem(row_idx, 0, item_id); self.log_table.setItem(row_idx, 1, QTableWidgetItem(ts_str))
                self.log_table.setItem(row_idx, 2, QTableWidgetItem(str(log.get('app_user_id', '')))); self.log_table.setItem(row_idx, 3, QTableWidgetItem(session_display))
                self.log_table.setItem(row_idx, 4, QTableWidgetItem(log.get('tabella'))); self.log_table.setItem(row_idx, 5, QTableWidgetItem(log.get('operazione')))
                self.log_table.setItem(row_idx, 6, QTableWidgetItem(str(log.get('record_id', '')))); self.log_table.setItem(row_idx, 7, QTableWidgetItem(log.get('ip_address')))
            self._update_pagination_controls()
        except DBMError as e:
            QMessageBox.critical(self, "Errore Database", f"Impossibile caricare i log di audit:\n{e}")

    def _update_pagination_controls(self):
        self.page_info_label.setText(f"Pagina {self.current_page} / {self.total_pages} ({self.total_records} risultati)")
        self.btn_first_page.setEnabled(self.current_page > 1)
        self.btn_prev_page.setEnabled(self.current_page > 1)
        self.btn_next_page.setEnabled(self.current_page < self.total_pages)
        self.btn_last_page.setEnabled(self.current_page < self.total_pages)

    def _go_to_first_page(self): self.current_page = 1; self._fetch_and_display_logs()
    def _go_to_previous_page(self): self.current_page -= 1; self._fetch_and_display_logs()
    def _go_to_next_page(self): self.current_page += 1; self._fetch_and_display_logs()
    def _go_to_last_page(self): self.current_page = self.total_pages; self._fetch_and_display_logs()

    def _display_log_details(self):
        selected = self.log_table.selectedItems()
        if not selected: self.details_before_text.clear(); self.details_after_text.clear(); return
        log_entry = self.log_table.item(selected[0].row(), 0).data(Qt.UserRole)
        d_before = log_entry.get('dati_prima'); d_after = log_entry.get('dati_dopo')
        self.details_before_text.setText(json.dumps(d_before, indent=4, ensure_ascii=False) if d_before else "")
        self.details_after_text.setText(json.dumps(d_after, indent=4, ensure_ascii=False) if d_after else "")

    def _handle_export_csv(self):
        logs, total = self.db_manager.get_audit_logs(filters=self.current_filters, page=1, page_size=10000) # Esporta fino a 10000 record
        if not logs: QMessageBox.warning(self, "Nessun Dato", "Nessun log da esportare per i filtri correnti."); return
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Log in CSV", f"audit_log_{date.today()}.csv", "File CSV (*.csv)")
        if not filename: return
        try:
            headers = logs[0].keys()
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers, delimiter=';'); writer.writeheader(); writer.writerows(logs)
            QMessageBox.information(self, "Successo", f"{len(logs)} record di audit esportati in CSV.")
        except Exception as e: QMessageBox.critical(self, "Errore Esportazione", f"Errore durante l'esportazione CSV:\n{e}")

    def _handle_export_xls(self):
        logs, total = self.db_manager.get_audit_logs(filters=self.current_filters, page=1, page_size=10000)
        if not logs: QMessageBox.warning(self, "Nessun Dato", "Nessun log da esportare."); return
        filename, _ = QFileDialog.getSaveFileName(self, "Esporta Log in Excel", f"audit_log_{date.today()}.xlsx", "File Excel (*.xlsx)")
        if not filename: return
        try:
            import pandas as pd
            df = pd.DataFrame(logs); df.to_excel(filename, index=False, engine='openpyxl')
            QMessageBox.information(self, "Successo", f"{len(logs)} record di audit esportati in Excel.")
        except ImportError: QMessageBox.critical(self, "Libreria Mancante", "L'esportazione in Excel richiede 'pandas' e 'openpyxl'.")
        except Exception as e: QMessageBox.critical(self, "Errore Esportazione", f"Errore durante l'esportazione Excel:\n{e}")
# ... (Fine della classe AuditLogViewerWidget) ...

class BackupRestoreWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Backup e Ripristino Database")

        # Processi per pg_dump e pg_restore
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._handle_process_finished)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Sezione Backup ---
        backup_group = QGroupBox("Backup Database")
        backup_layout = QFormLayout(backup_group)

        self.backup_file_path_edit = QLineEdit()
        self.backup_file_path_edit.setPlaceholderText(
            "Seleziona percorso e nome del file di backup...")
        self.backup_file_path_edit.setReadOnly(True)
        btn_browse_backup_path = QPushButton("Sfoglia...")
        btn_browse_backup_path.clicked.connect(
            self._browse_backup_file_save_path)
        backup_path_layout = QHBoxLayout()
        backup_path_layout.addWidget(self.backup_file_path_edit)
        backup_path_layout.addWidget(btn_browse_backup_path)
        backup_layout.addRow("File di Backup:", backup_path_layout)

        self.backup_format_combo = QComboBox()
        self.backup_format_combo.addItems([
            # .dump o .backup
            "Custom (compresso, per pg_restore - raccomandato)",
            "Plain SQL (testo semplice)"  # .sql
        ])
        backup_layout.addRow("Formato Backup:", self.backup_format_combo)

        # Opzionale: percorso pg_dump se non nel PATH
        self.pg_dump_path_edit = QLineEdit()
        self.pg_dump_path_edit.setPlaceholderText(
            "Es. C:\\Program Files\\PostgreSQL\\16\\bin\\pg_dump.exe (opzionale)")
        backup_layout.addRow(
            "Percorso pg_dump (opz.C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe):", self.pg_dump_path_edit)

        self.backup_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogSaveButton), "Esegui Backup")
        self.backup_button.clicked.connect(self._start_backup)
        backup_layout.addRow(self.backup_button)

        main_layout.addWidget(backup_group)

        # --- Sezione Ripristino ---
        restore_group = QGroupBox("Ripristino Database")
        restore_layout = QFormLayout(restore_group)

        self.restore_file_path_edit = QLineEdit()
        self.restore_file_path_edit.setPlaceholderText(
            "Seleziona il file di backup da ripristinare...")
        self.restore_file_path_edit.setReadOnly(True)
        btn_browse_restore_path = QPushButton("Sfoglia...")
        btn_browse_restore_path.clicked.connect(
            self._browse_restore_file_open_path)
        restore_path_layout = QHBoxLayout()
        restore_path_layout.addWidget(self.restore_file_path_edit)
        restore_path_layout.addWidget(btn_browse_restore_path)
        restore_layout.addRow("File di Backup:", restore_path_layout)

        # Opzionale: percorso pg_restore/psql se non nel PATH
        self.pg_restore_path_edit = QLineEdit()
        self.pg_restore_path_edit.setPlaceholderText(
            "Es. ...\\bin\\pg_restore.exe o ...\\bin\\psql.exe (opz.)")
        restore_layout.addRow(
            "Percorso pg_restore/psql (opz.):", self.pg_restore_path_edit)

        self.restore_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogApplyButton), "Esegui Ripristino")
        self.restore_button.clicked.connect(self._start_restore)
        restore_layout.addRow(self.restore_button)
        restore_layout.addRow(QLabel(
            "<font color='red'><b>ATTENZIONE:</b> Il ripristino sovrascriverà i dati correnti nel database. Procedere con cautela.</font>"))

        main_layout.addWidget(restore_group)

        # --- Output e Progresso ---
        output_group = QGroupBox("Output Operazione")
        output_layout = QVBoxLayout(output_group)
        self.output_text_edit = QTextEdit()
        self.output_text_edit.setReadOnly(True)
        self.output_text_edit.setLineWrapMode(
            QTextEdit.NoWrap)  # Per output comandi
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)  # Mostra solo durante l'operazione

        output_layout.addWidget(self.output_text_edit)
        output_layout.addWidget(self.progress_bar)
        # Il 1 dà a questo widget più stretch factor
        main_layout.addWidget(output_group, 1)

        self.setLayout(main_layout)

    def _browse_backup_file_save_path(self):
        # Ottieni il nome del database usando il nuovo metodo del db_manager
        current_dbname = self.db_manager.get_current_dbname()  # Usa il nuovo metodo getter
        # Fallback se get_current_dbname restituisce None
        default_db_name = current_dbname if current_dbname else "catasto_storico"

        default_filename = f"{default_db_name}_backup_{QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')}"

        if self.backup_format_combo.currentIndex() == 0:  # Custom
            filter_str = "File di Backup PostgreSQL Custom (*.dump *.backup);;Tutti i file (*)"
            default_filename += ".dump"
        else:  # Plain SQL
            filter_str = "File SQL (*.sql);;Tutti i file (*)"
            default_filename += ".sql"

        filePath, _ = QFileDialog.getSaveFileName(
            self, "Salva Backup Database", default_filename, filter_str)
        if filePath:
            self.backup_file_path_edit.setText(filePath)

    def _browse_restore_file_open_path(self):
        filter_str = "File di Backup PostgreSQL (*.dump *.backup *.sql);;File Custom (*.dump *.backup);;File SQL (*.sql);;Tutti i file (*)"
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Seleziona File di Backup per Ripristino", "", filter_str)
        if filePath:
            self.restore_file_path_edit.setText(filePath)

    def _update_ui_for_process(self, is_running: bool):
        self.backup_button.setEnabled(not is_running)
        self.restore_button.setEnabled(not is_running)
        self.progress_bar.setVisible(is_running)
        if is_running:
            self.progress_bar.setRange(0, 0)  # Indicatore di attività (busy)
            self.output_text_edit.clear()
        else:
            self.progress_bar.setRange(0, 1)  # Resetta
            self.progress_bar.setValue(0)

    def _handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode(errors='ignore')
        self.output_text_edit.append(data)

    def _handle_stderr(self):
        data = self.process.readAllStandardError().data().decode(errors='ignore')
        self.output_text_edit.append(
            f"<font color='red'>ERRORE: {data}</font>")

    # All'interno della classe BackupRestoreWidget in prova.py

    def _handle_process_finished(self, exitCode, exitStatus):
        is_restore = self.process.property("is_restore_operation")
        # Resetta la proprietà
        self.process.setProperty("is_restore_operation", False)

        # Il log DEBUG originale può rimanere per gli sviluppatori, ma non verrà mostrato all'utente in una QMessageBox.
        self.output_text_edit.append(
            f"<hr>DEBUG: Processo terminato. ExitCode: {exitCode}, ExitStatus: {exitStatus}, Operazione Ripristino: {is_restore}<hr>")
        
        # Riabilita UI (pulsanti, progress bar)
        self._update_ui_for_process(False)

        operation_name_display = "Ripristino del database" if is_restore else "Backup del database"
        
        # Inizializza messaggio per l'utente e tipo di QMessageBox
        user_message_title = f"Esito {operation_name_display}"
        user_message_text = ""
        message_box_type = QMessageBox.Information # Default: successo

        if exitStatus == QProcess.CrashExit:
            user_message_title = f"Errore Grave durante il {operation_name_display}"
            user_message_text = (
                f"Si è verificato un errore inaspettato e grave durante il {operation_name_display}. "
                "Il processo è terminato in modo anomalo (crash). "
                "Controllare attentamente i dettagli nell'area 'Output Operazione' per informazioni tecniche. "
                "Si consiglia di riprovare l'operazione."
            )
            message_box_type = QMessageBox.Critical
            self.output_text_edit.append(
                f"<font color='red'><b>ERRORE CRITICO: Il processo di {operation_name_display.lower()} è terminato inaspettatamente (crash).</b></font>")
            
        elif exitCode != 0:
            user_message_title = f"Operazione di {operation_name_display} Fallita"
            user_message_text = (
                f"L'operazione di {operation_name_display} è fallita con un codice d'errore ({exitCode}). "
                "Ciò indica che il comando esterno non è stato completato correttamente. "
                "Controllare i messaggi in rosso nell'area 'Output Operazione' per capire la causa dell'errore (ad es., password errata, permessi mancanti, file non trovato)."
            )
            message_box_type = QMessageBox.Warning
            self.output_text_edit.append(
                f"<font color='red'><b>FALLITO: Il processo di {operation_name_display.lower()} è terminato con codice d'errore: {exitCode}.</b></font>")
        else: # exitCode == 0, il processo stesso ha terminato con successo
            # Anche se exitCode è 0, pg_dump può scrivere errori su stderr.
            # Qui possiamo fare una verifica più approfondita se l'output stderr conteneva "ERROR:"
            # Questo richiede che _handle_stderr abbia collezionato gli errori.
            # Per semplicità, qui si assume che un exitCode 0 sia un successo generale,
            # ma si aggiunge un avviso per controllare l'output.

            user_message_title = f"Operazione di {operation_name_display} Completata"
            user_message_text = (
                f"L'operazione di {operation_name_display} è stata completata con successo. "
                "Si consiglia di controllare l'area 'Output Operazione' per eventuali messaggi informativi o di avviso da parte dello strumento."
            )
            message_box_type = QMessageBox.Information
            self.output_text_edit.append(
                f"<font color='green'><b>Comando di {operation_name_display.lower()} terminato (exit code 0).</b></font>")
            

        # --- Gestione Riconnessione Pool e Messaggio Finale per l'Utente ---
        if is_restore:
            self.output_text_edit.append(
                "<i>Tentativo di ripristinare le connessioni dell'applicazione al database...</i>\n")
            QApplication.processEvents() # Forzare l'aggiornamento della GUI

            if self.db_manager and self.db_manager.reconnect_pool_if_needed():
                self.output_text_edit.append(
                    "<i>Connessioni dell'applicazione al database ripristinate con successo.</i>\n")
                if message_box_type == QMessageBox.Information: # Se l'operazione Restore base è andata bene
                    user_message_text += "\nLe connessioni dell'applicazione al database sono state ripristinate. L'applicazione è ora pronta all'uso."
                else: # Se l'operazione Restore ha avuto errori, ma la riconnessione è OK
                    user_message_text += "\nATTENZIONE: Le connessioni dell'applicazione sono state ripristinate, ma si sono verificati errori durante il ripristino stesso. Verificare l'integrità dei dati."
                QMessageBox(message_box_type, user_message_title, user_message_text, QMessageBox.Ok, self).exec_()
                QMessageBox.information(self, "Verifica Importante",
                                        "Dopo un ripristino, si consiglia sempre di verificare l'integrità dei dati nel database. Se si riscontrano problemi, riavviare l'applicazione.")

            else: # Riconnessione pool fallita dopo un restore
                self.output_text_edit.append(
                    "<font color='red'><b>FALLITO: Impossibile ripristinare le connessioni al database. Si prega di RIAVVIARE L'APPLICAZIONE.</b></font>\n")
                user_message_title = f"Errore Critico: Riconnessione Database Fallita"
                user_message_text = (
                    f"L'operazione di {operation_name_display} è terminata, ma l'applicazione non è riuscita a riconnettersi al database. "
                    "Questo è un errore critico. Si prega di chiudere e riavviare l'applicazione immediatamente."
                )
                QMessageBox.critical(self, user_message_title, user_message_text, QMessageBox.Ok, self).exec_()

        else: # Non è un'operazione di ripristino (es. Backup)
            QMessageBox(message_box_type, user_message_title, user_message_text, QMessageBox.Ok, self).exec_()


    def _start_backup(self):
        backup_file = self.backup_file_path_edit.text()
        if not backup_file:
            QMessageBox.warning(
                self, "Percorso Mancante", "Selezionare un percorso e un nome file per il backup.")
            return

        if os.path.exists(backup_file):
            reply = QMessageBox.question(self, "Conferma Sovrascrittura",
                                         f"Il file '{os.path.basename(backup_file)}' esiste già.\nVuoi sovrascriverlo?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

         # --- Richiesta Password ---
        # Recupera utente e dbname tramite i metodi getter del db_manager
        db_user_for_prompt = self.db_manager.get_current_user() or "N/Utente"
        db_name_for_prompt = self.db_manager.get_current_dbname() or "N/Database"

        password, ok = QInputDialog.getText(self, "Autenticazione Database per Backup",
                                            f"Inserisci la password per l'utente '{db_user_for_prompt}' "
                                            f"sul database '{db_name_for_prompt}':",
                                            QLineEdit.Password)
        if not ok:
            self.output_text_edit.append(
                "<i>Backup annullato dall'utente (dialogo password chiuso).</i>")
            return
        if not password.strip():
            QMessageBox.warning(self, "Password Mancante",
                                "La password non può essere vuota.")
            self.output_text_edit.append(
                "<font color='orange'>Backup fallito: password non fornita.</font>")
            self._update_ui_for_process(False)  # Assicurati di resettare la UI
            return
        # --- Fine Richiesta Password ---

        self._update_ui_for_process(True)
        self.output_text_edit.clear()  # Pulisci output precedente
        self.output_text_edit.append(f"Avvio backup su: {backup_file}...\n")

        command_parts = self.db_manager.get_backup_command_parts(
            backup_file_path=backup_file,
            pg_dump_executable_path_ui=self.pg_dump_path_edit.text().strip(),
            format_type="custom" if self.backup_format_combo.currentIndex() == 0 else "plain",
            include_blobs=False  # O come hai deciso
        )

        if not command_parts:
            self.output_text_edit.append(
                "<font color='red'><b>ERRORE: Impossibile costruire il comando di backup. Verificare il percorso di pg_dump e i log.</b></font>")
            self._update_ui_for_process(False)
            QMessageBox.critical(
                self, "Errore Comando", "Impossibile preparare il comando di backup. Controllare i log dell'applicazione.")
            return

        executable = command_parts[0]
        args = command_parts[1:]

        self.output_text_edit.append(
            f"Comando da eseguire: {executable} {' '.join(args)}\n")

        process_env = self.process.processEnvironment()
        self.output_text_edit.append(
            # Usa la variabile
            f"<i>Tentativo di impostare PGPASSWORD per l'utente '{db_user_for_prompt}'...</i>\n")
        try:
            process_env.insert("PGPASSWORD", password)
            self.process.setProcessEnvironment(process_env)
            self.output_text_edit.append(
                "<i>PGPASSWORD impostata per questo processo.</i>\n")
        except Exception as e:
            self.output_text_edit.append(
                f"<font color='red'><b>ERRORE nell'impostare PGPASSWORD: {e}</b></font>\n")
            self.output_text_edit.append(
                "<font color='orange'>Il backup potrebbe fallire o rimanere bloccato.</font>\n")

        # Assicura che sia False per il backup
        self.process.setProperty("is_restore_operation", False)
        self.process.start(executable, args)

    # All'interno della classe BackupRestoreWidget in prova.py
# nel metodo _start_restore

    def _start_restore(self):
        restore_file = self.restore_file_path_edit.text()
        if not restore_file:
            QMessageBox.warning(
                self, "File Mancante", "Selezionare un file di backup da cui ripristinare.")
            return
        if not os.path.exists(restore_file):
            QMessageBox.critical(
                self, "Errore File", f"Il file di backup '{restore_file}' non è stato trovato.")
            return

        # --- AVVISI E CONFERME MULTIPLE ---
        # Recupera i dettagli del DB usando i metodi getter
        dbname_to_restore = self.db_manager.get_current_dbname() or "Database Sconosciuto"

        db_host_for_prompt = "N/Host"  # Fallback
        if hasattr(self.db_manager, '_conn_params_dict') and self.db_manager._conn_params_dict:
            db_host_for_prompt = self.db_manager._conn_params_dict.get(
                'host', 'N/Host')

        db_user_for_prompt = self.db_manager.get_current_user() or "Utente Sconosciuto"

        if dbname_to_restore == "Database Sconosciuto":  # Controllo di sicurezza aggiuntivo
            QMessageBox.critical(self, "Errore Configurazione",
                                 "Nome del database di destinazione non recuperabile.")
            return

        reply = QMessageBox.warning(self, "Conferma Ripristino Critico",
                                    f"<b>ATTENZIONE ESTREMA!</b>\n\n"
                                    f"Stai per ripristinare il database dal file:\n'{os.path.basename(restore_file)}'\n"
                                    f"sul database di destinazione:\n<b>'{dbname_to_restore}'</b> "
                                    f"(Host: {db_host_for_prompt}, Utente DB: {db_user_for_prompt}).\n\n"
                                    "<b>Questa operazione SOVRASCRIVERÀ tutti i dati correnti nel database di destinazione e NON PUÒ ESSERE ANNULLATA.</b>\n\n"
                                    "Si raccomanda VIVAMENTE di aver effettuato un backup recente e verificato del database corrente prima di procedere.\n\n"
                                    "Sei assolutamente sicuro di voler continuare?",
                                    QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if reply == QMessageBox.Cancel:
            self.output_text_edit.append(
                "<i>Ripristino annullato dall'utente (prima conferma).</i>")
            return

        text_confirm, ok = QInputDialog.getText(self, "Conferma Finale Ripristino Obbligatoria",
                                                f"Per confermare il ripristino che sovrascriverà PERMANENTEMENTE il database '{dbname_to_restore}',\n"
                                                f"digita il nome del database qui sotto (deve corrispondere esattamente):")
        if not ok:
            self.output_text_edit.append(
                "<i>Ripristino annullato dall'utente (dialogo conferma nome DB chiuso).</i>")
            return
        if text_confirm.strip() != dbname_to_restore:
            QMessageBox.critical(self, "Ripristino Annullato",
                                 f"Il nome del database inserito ('{text_confirm.strip()}') non corrisponde a '{dbname_to_restore}'.\n"
                                 "Ripristino annullato per sicurezza.")
            self.output_text_edit.append(
                "<font color='red'>Ripristino annullato: conferma nome database fallita.</font>")
            return
        # --- FINE AVVISI E CONFERME ---

        # --- Richiesta Password ---
        password, ok = QInputDialog.getText(self, "Autenticazione Database per Ripristino",
                                            f"Inserisci la password per l'utente '{db_user_for_prompt}' "
                                            f"per il database '{dbname_to_restore}':",
                                            QLineEdit.Password)
        if not ok:
            self.output_text_edit.append(
                "<i>Ripristino annullato (dialogo password chiuso).</i>")
            return
        if not password.strip():
            QMessageBox.warning(
                self, "Password Mancante", "La password non può essere vuota per il ripristino.")
            self.output_text_edit.append(
                "<font color='orange'>Ripristino fallito: password non fornita.</font>")
            self._update_ui_for_process(False)
            return
        # --- Fine Richiesta Password ---

        self._update_ui_for_process(True)
        self.output_text_edit.clear()
        self.output_text_edit.append(
            f"Avvio ripristino del database '{dbname_to_restore}' da: {restore_file}...\n")
        self.output_text_edit.append(
            "<font color='orange'><b>AVVISO: L'applicazione potrebbe non rispondere durante l'operazione di ripristino. Attendere il completamento.</b></font>\n")
        QApplication.processEvents()

        # Logica per la disconnessione temporanea del pool (se decommentata e implementata)
        self.output_text_edit.append(
            "<i>Tentativo di chiudere le connessioni attive dell'applicazione al database...</i>\n")
        QApplication.processEvents()
        if not self.db_manager.disconnect_pool_temporarily():  # CORRETTO
            QMessageBox.critical(self, "Errore Critico Ripristino",
                                 "Impossibile chiudere le connessioni esistenti al database prima del ripristino.\n"
                                 "L'operazione è stata annullata per sicurezza.")
            self.output_text_edit.append(
                "<font color='red'><b>FALLITO: Impossibile chiudere le connessioni al database. Ripristino annullato.</b></font>")
            self._update_ui_for_process(False)
            return
        self.output_text_edit.append(
            "<i>Connessioni dell'applicazione al database chiuse temporaneamente.</i>\n")
        QApplication.processEvents()

        command_parts = self.db_manager.get_restore_command_parts(
            backup_file_path=restore_file,
            pg_tool_executable_path_ui=self.pg_restore_path_edit.text().strip()
        )

        if not command_parts:
            self.output_text_edit.append(
                "<font color='red'><b>ERRORE: Impossibile costruire il comando di ripristino. Controllare il percorso dell'eseguibile e i log.</b></font>")
            self._update_ui_for_process(False)
            # Tentativo di riconnettere il pool se la disconnessione era avvenuta
            self.output_text_edit.append(
                "<i>Tentativo di ripristinare le connessioni dell'applicazione (dopo fallimento preparazione comando)...</i>")
            if not self.db_manager.reconnect_pool_if_needed():  # CORRETTO
                self.output_text_edit.append(
                    "<font color='red'><b>FALLITO riconnessione pool. Riavviare l'app.</b></font>")
            else:
                self.output_text_edit.append(
                    "<i>Connessioni applicazione ripristinate.</i>")
            QMessageBox.critical(
                self, "Errore Comando", "Impossibile preparare il comando di ripristino.")
            return

        executable = command_parts[0]
        args = command_parts[1:]
        self.output_text_edit.append(
            f"Comando da eseguire: {executable} {' '.join(args)}\n")

        process_env = self.process.processEnvironment()
        self.output_text_edit.append(
            f"<i>Tentativo di impostare PGPASSWORD per l'utente '{db_user_for_prompt}'...</i>\n")
        try:
            process_env.insert("PGPASSWORD", password)
            self.process.setProcessEnvironment(process_env)
            self.output_text_edit.append(
                "<i>PGPASSWORD impostata per questo processo.</i>\n")
        except Exception as e:
            self.output_text_edit.append(
                f"<font color='red'><b>ERRORE nell'impostare PGPASSWORD: {e}</b></font>\n")

        self.process.setProperty("is_restore_operation", True)
        self.process.start(executable, args)


class RegistraConsultazioneWidget(QWidget):
    def __init__(self, db_manager: 'CatastoDBManager',
                 current_user_info: Optional[Dict[str, Any]],
                 parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user_info = current_user_info

        self._initUI()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_group = QGroupBox("Registra Nuova Consultazione")
        form_layout = QFormLayout(form_group)
        form_layout.setSpacing(10)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.data_consultazione_edit = QDateEdit(
            calendarPopup=True)  # Nome UI: data_consultazione_edit
        self.data_consultazione_edit.setDate(QDate.currentDate())
        self.data_consultazione_edit.setDisplayFormat("yyyy-MM-dd")
        form_layout.addRow("Data Consultazione (*):",
                           self.data_consultazione_edit)  # Colonna DB: data

        self.richiedente_edit = QLineEdit()
        self.richiedente_edit.setPlaceholderText(
            "Nome e Cognome del richiedente")
        # Colonna DB: richiedente
        form_layout.addRow("Richiedente (*):", self.richiedente_edit)

        self.doc_id_edit = QLineEdit()
        self.doc_id_edit.setPlaceholderText(
            "Es. CI N. XXXXXX, Patente N. YYYYYY")
        # Colonna DB: documento_identita
        form_layout.addRow("Documento Identità (opz.):", self.doc_id_edit)

        self.motivazione_edit = QTextEdit()
        self.motivazione_edit.setPlaceholderText(
            "Motivazione della richiesta di consultazione")
        self.motivazione_edit.setFixedHeight(80)
        # Colonna DB: motivazione
        form_layout.addRow("Motivazione (opz.):", self.motivazione_edit)

        self.materiale_edit = QTextEdit()
        self.materiale_edit.setPlaceholderText(
            "Descrizione dettagliata del materiale consultato (es. Partita N. 123 Comune X, Mappa Foglio Y)")
        self.materiale_edit.setFixedHeight(120)
        # Colonna DB: materiale_consultato
        form_layout.addRow("Materiale Consultato (*):", self.materiale_edit)

        # Modificato da QLabel a QLineEdit per permettere modifica
        self.funzionario_edit = QLineEdit()
        if self.current_user_info and self.current_user_info.get('nome_completo'):
            self.funzionario_edit.setText(
                self.current_user_info.get('nome_completo'))
        else:
            self.funzionario_edit.setPlaceholderText("Nome del funzionario")
        # Colonna DB: funzionario_autorizzante
        form_layout.addRow("Funzionario Autorizzante (opz.):",
                           self.funzionario_edit)

        # Rimuoviamo note_interne dato che non c'è nella tabella
        # self.note_interne_edit = QTextEdit() ...
        # form_layout.addRow("Note Interne (opz.):", self.note_interne_edit)

        main_layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        self.btn_registra_consultazione = QPushButton(QApplication.style(
        ).standardIcon(QStyle.SP_DialogSaveButton), " Registra Consultazione")
        self.btn_registra_consultazione.clicked.connect(
            self._salva_consultazione)
        self.btn_pulisci_campi = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogDiscardButton), " Pulisci Campi")
        self.btn_pulisci_campi.clicked.connect(self._pulisci_campi)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_registra_consultazione)
        button_layout.addWidget(self.btn_pulisci_campi)
        main_layout.addLayout(button_layout)

        main_layout.addStretch(1)
        self.setLayout(main_layout)
        self._pulisci_campi()  # Pulisce e imposta focus iniziale

    def _pulisci_form_registrazione(self):
        """Pulisce tutti i campi del form di registrazione proprietà."""
        self.comune_id = None
        self.comune_display.setText("Nessun comune selezionato")
        self.num_partita_edit.setValue(1)  # O il suo valore di default
        self.data_edit.setDate(QDate.currentDate())
        self.possessori_data = []
        self.immobili_data = []
        # Assumendo che questi metodi aggiornino le tabelle UI
        self.update_possessori_table()
        self.update_immobili_table()
        self.num_partita_edit.setFocus()  # Focus sul primo campo utile
        self.suffisso_partita_edit.clear() # Pulisci il suffisso

    def _pulisci_campi(self):
        self.data_consultazione_edit.setDate(QDate.currentDate())
        self.richiedente_edit.clear()
        self.doc_id_edit.clear()
        self.motivazione_edit.clear()
        self.materiale_edit.clear()

        # Precompila o pulisci funzionario_edit
        if self.current_user_info and self.current_user_info.get('nome_completo'):
            self.funzionario_edit.setText(
                self.current_user_info.get('nome_completo'))
        else:
            self.funzionario_edit.clear()

        self.richiedente_edit.setFocus()

    def _salva_consultazione(self):
        data_cons = self.data_consultazione_edit.date().toPyDate()  # Nome colonna DB: 'data'
        richiedente = self.richiedente_edit.text().strip()
        materiale = self.materiale_edit.toPlainText().strip()

        doc_id = self.doc_id_edit.text().strip() or None
        motivazione = self.motivazione_edit.toPlainText().strip() or None
        funzionario_testo = self.funzionario_edit.text().strip() or None  # Testo libero

        # Validazione UI
        if not richiedente:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il campo 'Richiedente' è obbligatorio.")
            self.richiedente_edit.setFocus()
            return
        if not materiale:  # Anche se nullabile nel DB, lo rendiamo obbligatorio nella UI
            QMessageBox.warning(
                self, "Dati Mancanti", "Il campo 'Materiale Consultato' è obbligatorio.")
            self.materiale_edit.setFocus()
            return

        try:
            consultazione_id = self.db_manager.registra_nuova_consultazione(
                data_consultazione=data_cons,
                richiedente=richiedente,
                materiale_consultato=materiale,
                funzionario_autorizzante=funzionario_testo,  # Passa il testo
                documento_identita=doc_id,
                motivazione=motivazione
                # note_interne non c'è più
            )
            if consultazione_id is not None:
                QMessageBox.information(
                    self, "Successo", f"Consultazione registrata con successo (ID: {consultazione_id}).")
                self._pulisci_campi()
            # else: errore gestito da eccezioni
        except (DBDataError, DBMError) as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore durante la registrazione della consultazione: {str(e)}", exc_info=False)
            QMessageBox.critical(self, "Errore Registrazione", str(e))
        except Exception as e_gen:
            logging.getLogger("CatastoGUI").critical(
                f"Errore imprevisto registrazione consultazione: {e_gen}", exc_info=True)
            # # # QMessageBox.critical(self, "Errore Imprevisto", f"Errore di sistema: {e_gen}")


# In gui_widgets.py

# In gui_widgets.py, puoi commentare o eliminare la vecchia classe LandingPageWidget
# e aggiungere questa nuova classe.

class DashboardWidget(QWidget):
    # Segnali per navigare ad altri tab (manteniamo la logica)
    go_to_tab_signal = pyqtSignal(str, str) # Segnale emetterà (nome_tab_principale, nome_sotto_tab)
    # --- INIZIO MODIFICA ---
    # Definiamo il nuovo segnale che trasporterà una stringa (il testo della ricerca)
    ricerca_globale_richiesta = pyqtSignal(str)
    # --- FINE MODIFICA ---

    def __init__(self, db_manager: 'CatastoDBManager', current_user_info: Optional[Dict], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user_info = current_user_info
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self._initUI()
        self.load_initial_data() # Lazy loading

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(25)

        # 1. Intestazione
        nome_utente = self.current_user_info.get('nome_completo', 'Utente') if self.current_user_info else 'Utente'
        header_label = QLabel(f"<h2>Benvenuto in Meridiana 1.0, {nome_utente}</h2>")
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)

        # 2. Ricerca Globale
        search_group = QGroupBox("Ricerca Rapida")
        search_layout = QHBoxLayout(search_group)
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("Cerca qualsiasi cosa nel catasto...")
        self.search_edit.setMinimumHeight(35)
        self.search_button = QPushButton("Cerca"); self.search_button.clicked.connect(self._avvia_ricerca_globale)
        self.search_edit.returnPressed.connect(self._avvia_ricerca_globale)
        search_layout.addWidget(self.search_edit); search_layout.addWidget(self.search_button)
        main_layout.addWidget(search_group)

        # 3. Statistiche Rapide
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        self.stat_comuni_label = self._create_stat_card("Comuni", "0", "background-color: #e6f7ff; border-color: #91d5ff;")
        self.stat_partite_label = self._create_stat_card("Partite", "0", "background-color: #f6ffed; border-color: #b7eb8f;")
        self.stat_possessori_label = self._create_stat_card("Possessori", "0", "background-color: #fffbe6; border-color: #ffe58f;")
        self.stat_immobili_label = self._create_stat_card("Immobili", "0", "background-color: #fff1f0; border-color: #ffccc7;")
        stats_layout.addWidget(self.stat_comuni_label); stats_layout.addWidget(self.stat_partite_label)
        stats_layout.addWidget(self.stat_possessori_label); stats_layout.addWidget(self.stat_immobili_label)
        main_layout.addLayout(stats_layout)

        # 4. Attività Recenti e Azioni Rapide
        bottom_layout = QHBoxLayout()
        
        recent_activity_group = QGroupBox("Attività Utenti Recenti") # Titolo più appropriato
        recent_activity_layout = QVBoxLayout(recent_activity_group)
        self.audit_table = QTableWidget()
        
        # --- INIZIO MODIFICA ---
        # Cambiamo le colonne per mostrare le informazioni della sessione
        self.audit_table.setColumnCount(5)
        self.audit_table.setHorizontalHeaderLabels(["Data/Ora", "Utente", "Azione", "Esito", "Indirizzo IP"])
        # --- FINE MODIFICA ---

        self.audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        recent_activity_layout.addWidget(self.audit_table)
        bottom_layout.addWidget(recent_activity_group, 2)

        actions_group = QGroupBox("Azioni Rapide")
        actions_layout = QVBoxLayout(actions_group)
        btn_new_prop = QPushButton("Registra Nuova Proprietà"); btn_new_prop.clicked.connect(lambda: self.go_to_tab_signal.emit("Inserimento e Gestione", "Registrazione Proprietà"))
        btn_new_partita = QPushButton("Inserisci Nuova Partita"); btn_new_partita.clicked.connect(lambda: self.go_to_tab_signal.emit("Inserimento e Gestione", "Nuova Partita"))
        btn_reports = QPushButton("Vai alla Reportistica"); btn_reports.clicked.connect(lambda: self.go_to_tab_signal.emit("Reportistica", ""))
        actions_layout.addWidget(btn_new_prop); actions_layout.addWidget(btn_new_partita); actions_layout.addWidget(btn_reports)
        actions_layout.addStretch()
        bottom_layout.addWidget(actions_group, 1)

        main_layout.addLayout(bottom_layout, 1) # Stretch factor per la parte inferiore
        
    def _create_stat_card(self, title, value, style):
        card = QLabel(f"<h3>{title}</h3><p style='font-size: 24pt; font-weight: bold;'>{value}</p>")
        card.setAlignment(Qt.AlignCenter)
        card.setStyleSheet(f"QLabel {{ border: 1px solid; border-radius: 8px; padding: 10px; {style} }}")
        card.setMinimumHeight(100)
        return card

    # In gui_widgets.py, nel metodo DashboardWidget.load_initial_data

    def load_initial_data(self):
        """Carica tutti i dati necessari per la dashboard."""
        self.logger.info("Caricamento dati per la Dashboard...")
        # La parte delle statistiche rimane invariata
        stats = self.db_manager.get_dashboard_stats()
        self.stat_comuni_label.setText(f"<h3>Comuni</h3><p style='font-size: 24pt; font-weight: bold;'>{stats.get('total_comuni', 0)}</p>")
        self.stat_partite_label.setText(f"<h3>Partite</h3><p style='font-size: 24pt; font-weight: bold;'>{stats.get('total_partite', 0)}</p>")
        self.stat_possessori_label.setText(f"<h3>Possessori</h3><p style='font-size: 24pt; font-weight: bold;'>{stats.get('total_possessori', 0)}</p>")
        self.stat_immobili_label.setText(f"<h3>Immobili</h3><p style='font-size: 24pt; font-weight: bold;'>{stats.get('total_immobili', 0)}</p>")

        # Carica gli ultimi log di sessione
        session_logs = self.db_manager.get_recent_session_logs(limit=5)
        
        self.audit_table.setRowCount(len(session_logs))
        for row, log in enumerate(session_logs):
            # --- INIZIO MODIFICA DEFINITIVA ---
            # Usiamo le chiavi corrette ('data_login' e 'indirizzo_ip') restituite dalla query
            ts = log.get('data_login')
            ts_str = ts.strftime("%d/%m/%y %H:%M") if ts else "N/D"

            user_display = log.get('nome_completo') or log.get('username', 'N/D')
            action_display = log.get('azione', 'N/D').replace('_', ' ').title()
            esito_display = "Successo" if log.get('esito') else "Fallito"

            self.audit_table.setItem(row, 0, QTableWidgetItem(ts_str))
            self.audit_table.setItem(row, 1, QTableWidgetItem(user_display))
            self.audit_table.setItem(row, 2, QTableWidgetItem(action_display))
            self.audit_table.setItem(row, 3, QTableWidgetItem(esito_display))
            self.audit_table.setItem(row, 4, QTableWidgetItem(log.get('indirizzo_ip', 'N/D'))) # <-- Colonna corretta
            # --- FINE MODIFICA DEFINITIVA ---
            
        self.audit_table.resizeColumnsToContents()

    def _avvia_ricerca_globale(self):
        """Emette un segnale per passare al tab di ricerca globale e inserire il testo."""
        testo_ricerca = self.search_edit.text().strip()
        if not testo_ricerca:
            return
            
        # --- INIZIO MODIFICA ---
        # Sostituisci la vecchia logica con una singola riga che emette il segnale
        self.ricerca_globale_richiesta.emit(testo_ricerca)
        # --- FINE MODIFICA ---
class WelcomeScreen(QDialog):
    def __init__(self, parent=None, logo_path: str = None, help_url: str = None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.setWindowTitle("Benvenuto - Meridiana 1.0")
        self.setModal(True)
        self.setFixedSize(1024, 768)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.help_url = help_url
        self.logo_path = logo_path

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- NUOVA STRUTTURA DI LAYOUT PER CENTRATURA VERTICALE ---
        # 1. Spaziatore superiore per spingere il contenuto verso il basso
        main_layout.addStretch(1)

        # Logo
        logo_layout = QHBoxLayout()
        logo_layout.addStretch(1)
        logo_label = QLabel()
        if self.logo_path and os.path.exists(self.logo_path):
            pixmap = QPixmap(self.logo_path)
            # Riduciamo leggermente le dimensioni massime per garantire più spazio
            scaled_pixmap = pixmap.scaled(750, 450, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        logo_layout.addWidget(logo_label)
        logo_layout.addStretch(1)
        main_layout.addLayout(logo_layout)

        # Titolo e Sottotitolo
        title_label = QLabel("Meridiana 1.0"); title_label.setFont(QFont("Segoe UI", 28, QFont.Bold)); title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Gestionale Catasto Storico - Archivio di Stato di Savona"); subtitle_label.setFont(QFont("Segoe UI", 14)); subtitle_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle_label)

        # Crediti
        credits_label = QLabel("Sviluppato da: Marco Santoro\nCopyright © 2025 - Tutti i diritti riservati\nConcesso in comodato d'uso gratuito all'Archivio di Stato di Savona"); credits_label.setFont(QFont("Segoe UI", 9)); credits_label.setAlignment(Qt.AlignCenter)
        credits_label.setStyleSheet("color: #6c757d;")
        main_layout.addWidget(credits_label)
        main_layout.addSpacing(20)

        # Pulsante Guida
        if self.help_url:
            help_button = QPushButton("Apri Manuale Utente"); help_button.setFont(QFont("Segoe UI", 11)); help_button.setFixedSize(220, 40)
            help_button.clicked.connect(self._open_help_url)
            help_button_layout = QHBoxLayout(); help_button_layout.addStretch(); help_button_layout.addWidget(help_button); help_button_layout.addStretch()
            main_layout.addLayout(help_button_layout)

        # 2. Spaziatore inferiore per spingere il contenuto verso l'alto
        main_layout.addStretch(1)
        # --- FINE NUOVA STRUTTURA ---

        self.setLayout(main_layout)

    def _open_help_url(self):
        if not self.help_url: return
        self.logger.info(f"Apertura del manuale richiesta: {self.help_url}")
        # La logica che gestisce sia URL che file locali
        if self.help_url.lower().startswith(('http://', 'https://')):
            QDesktopServices.openUrl(QUrl(self.help_url))
        elif os.path.exists(self.help_url):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.help_url))
        else:
            QMessageBox.warning(self, "File Non Trovato", f"Il file della guida non è stato trovato:\n{self.help_url}")

    def mousePressEvent(self, event):
        # Chiude la finestra con un click, come richiesto
        self.logger.info("Welcome Screen chiusa tramite click del mouse.")
        self.accept()

    def keyPressEvent(self, event):
        # Chiude la finestra con un tasto, come richiesto
        self.logger.info(f"Welcome Screen chiusa tramite pressione del tasto: {event.key()}")
        self.accept()