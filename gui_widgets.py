
import os,csv,sys,logging,json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING

# Importazioni PyQt5
# Importazioni necessarie (QSvgWidget già dovrebbe esserci dalla risposta precedente)
#from PyQt5.QtSvgWidgets import QSvgWidget
# QByteArray non è più necessario se carichi da file
# from PyQt5.QtCore import QByteArray
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
                             QVBoxLayout, QWidget)
from PyQt5.QtCore import Qt, QSettings, pyqtSlot

# Importazione commentata (da abilitare se necessario)
# from PyQt5.QtSvgWidgets import QSvgWidget



from app_utils import (
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT, 
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA
)
#from app_utils import SETTINGS_DB_PASS



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

NUOVE_ETICHETTE_POSSESSORI = ["id", "nome_completo", "codice_fiscale", "data_nascita", "cognome_nome",
                              "paternita", "indirizzo_residenza", "comune_residenza_nome", "attivo", "note", "num_partite"]

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
        self.db_manager = db_manager
        # Inizializza il logger per questa classe, se non hai un logger globale preferito
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}") 

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

        self.load_comuni_data()

    def load_comuni_data(self):
        logging.getLogger("CatastoGUI").info(f"ElencoComuniWidget ({id(self)}): Esecuzione di load_comuni_data().") # Log per tracciare la chiamata
        self.comuni_table.setRowCount(0)
        self.comuni_table.setSortingEnabled(False)
        try:
            comuni_list = self.db_manager.get_all_comuni_details() # Assicurati che questo metodo restituisca tutti i comuni
            if comuni_list:
                self.comuni_table.setRowCount(len(comuni_list))
                for row_idx, comune in enumerate(comuni_list):
                    col = 0
                    self.comuni_table.setItem(
                        row_idx, col, QTableWidgetItem(str(comune.get('id', ''))))
                    col += 1
                    self.comuni_table.setItem(
                        row_idx, col, QTableWidgetItem(comune.get('nome_comune', '')))
                    col += 1
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(
                        comune.get('codice_catastale', '')))
                    col += 1
                    self.comuni_table.setItem(
                        row_idx, col, QTableWidgetItem(comune.get('provincia', '')))
                    col += 1

                    data_ist = comune.get('data_istituzione')
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(
                        str(data_ist) if data_ist else ''))
                    col += 1

                    data_soppr = comune.get('data_soppressione')
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(
                        str(data_soppr) if data_soppr else ''))
                    col += 1

                    self.comuni_table.setItem(
                        row_idx, col, QTableWidgetItem(comune.get('note', '')))
                    col += 1

                self.comuni_table.resizeColumnsToContents()
                logging.getLogger("CatastoGUI").info(f"ElencoComuniWidget: Tabella comuni aggiornata con {len(comuni_list)} elementi.")
            else:
                logging.getLogger("CatastoGUI").info("ElencoComuniWidget: Nessun comune trovato nel database per l'aggiornamento.")

        except AttributeError as ae:  # Se get_all_comuni_details non esiste
            logging.getLogger("CatastoGUI").error(
                f"Attributo mancante nel db_manager: {ae}. Assicurati che 'get_all_comuni_details' esista.")
            QMessageBox.critical(
                self, "Errore Caricamento Dati", f"Funzione dati comuni non trovata: {ae}")
        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore durante il caricamento dei comuni: {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
        finally:
            self.comuni_table.setSortingEnabled(True)
         # Assicurati che chiami self.db_manager.get_all_comuni_details()
        self.logger.info(f"ElencoComuniWidget ({id(self)}): Esecuzione di load_comuni_data().")
        self.comuni_table.setRowCount(0)
        self.comuni_table.setSortingEnabled(False)
        try:
            comuni_list = self.db_manager.get_all_comuni_details() #
            if comuni_list:
                self.comuni_table.setRowCount(len(comuni_list))
                for row_idx, comune in enumerate(comuni_list):
                    col = 0
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(str(comune.get('id', '')))); col+=1
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(comune.get('nome_comune', ''))); col+=1
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(comune.get('codice_catastale', ''))); col+=1
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(comune.get('provincia', ''))); col+=1
                    data_ist = comune.get('data_istituzione')
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(str(data_ist) if data_ist else '')); col+=1
                    data_soppr = comune.get('data_soppressione')
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(str(data_soppr) if data_soppr else '')); col+=1
                    self.comuni_table.setItem(row_idx, col, QTableWidgetItem(comune.get('note', ''))); col+=1
                self.comuni_table.resizeColumnsToContents()
            else:
                self.logger.info("Nessun comune trovato nel database.")
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento dei comuni: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
        finally:
            self.comuni_table.setSortingEnabled(True)

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

class RicercaPossessoriWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager

        main_layout = QVBoxLayout(self)

        # --- Gruppo per i Criteri di Ricerca ---
        search_criteria_group = QGroupBox("Criteri di Ricerca Possessori")
        criteria_layout = QGridLayout(search_criteria_group)

        # ... (campi di ricerca come prima: self.search_term_edit, self.similarity_threshold_spinbox, self.search_button) ...
        criteria_layout.addWidget(
            QLabel("Termine di ricerca (nome, cognome, ecc.):"), 0, 0)
        self.search_term_edit = QLineEdit()
        self.search_term_edit.setPlaceholderText(
            "Inserisci parte del nome o altri termini...")
        criteria_layout.addWidget(self.search_term_edit, 0, 1, 1, 2)

        criteria_layout.addWidget(
            QLabel("Soglia di similarità (0.0 - 1.0):"), 1, 0)
        self.similarity_threshold_spinbox = QDoubleSpinBox()
        self.similarity_threshold_spinbox.setMinimum(0.0)
        self.similarity_threshold_spinbox.setMaximum(1.0)
        self.similarity_threshold_spinbox.setSingleStep(0.05)
        self.similarity_threshold_spinbox.setValue(0.3)
        criteria_layout.addWidget(self.similarity_threshold_spinbox, 1, 1)

        self.search_button = QPushButton("Cerca Possessori")
        self.search_button.setIcon(
            QApplication.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.search_button.clicked.connect(self._perform_search)
        criteria_layout.addWidget(self.search_button, 1, 2)

        main_layout.addWidget(search_criteria_group)

        # --- Tabella per i Risultati ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "ID", "Nome Completo", "Cognome Nome", "Paternità", "Comune Rif.", "Similarità", "Num. Partite"
        ])
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(
            QTableWidget.SingleSelection)  # Assicurati sia SingleSelection
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.itemSelectionChanged.connect(
            self._aggiorna_stato_pulsanti_azione)  # Nuovo collegamento
        self.results_table.itemDoubleClicked.connect(
            self.apri_modifica_possessore_selezionato)  # Modifica al doppio click

        main_layout.addWidget(self.results_table)

        # --- Pulsanti di Azione sotto la Tabella ---
        action_layout = QHBoxLayout()
        self.btn_modifica_possessore = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_FileDialogDetailedView), "Modifica Selezionato")
        self.btn_modifica_possessore.setToolTip(
            "Modifica i dati del possessore selezionato")
        self.btn_modifica_possessore.clicked.connect(
            self.apri_modifica_possessore_selezionato)
        self.btn_modifica_possessore.setEnabled(
            False)  # Inizialmente disabilitato
        action_layout.addWidget(self.btn_modifica_possessore)
        action_layout.addStretch()  # Spinge i pulsanti a sinistra o distribuisce lo spazio
        main_layout.addLayout(action_layout)

        self.setLayout(main_layout)

    def _aggiorna_stato_pulsanti_azione(self):
        """Abilita/disabilita i pulsanti di azione in base alla selezione nella tabella."""
        has_selection = bool(self.results_table.selectedItems())
        self.btn_modifica_possessore.setEnabled(has_selection)

    def _get_selected_possessore_id(self) -> Optional[int]:
        """Restituisce l'ID del possessore attualmente selezionato nella tabella dei risultati."""
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return None

        current_row = self.results_table.currentRow()
        if current_row < 0:
            return None

        id_item = self.results_table.item(current_row, 0)  # Colonna ID
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    # Può essere chiamato da pulsante o doppio click
    def apri_modifica_possessore_selezionato(self):
        possessore_id = self._get_selected_possessore_id()
        if possessore_id is not None:
            # Istanziamo e apriamo ModificaPossessoreDialog
            dialog = ModificaPossessoreDialog(
                self.db_manager, possessore_id, self)
            if dialog.exec_() == QDialog.Accepted:
                # Se il dialogo è stato accettato (cioè le modifiche sono state salvate),
                # ricarichiamo i risultati della ricerca per riflettere le modifiche.
                # Questo potrebbe richiedere di rieseguire l'ultima ricerca o di aggiornare la riga.
                # Per semplicità, rieseguiamo l'ultima ricerca se i criteri sono ancora validi.
                QMessageBox.information(
                    self, "Modifica Possessore", "Modifiche al possessore salvate con successo.")
                self._perform_search()  # Riesegue l'ultima ricerca per aggiornare la tabella
        else:
            QMessageBox.warning(
                self, "Nessuna Selezione", "Per favore, seleziona un possessore dalla tabella da modificare.")

    def _perform_search(self):
        # ... (la tua logica esistente per _perform_search) ...
        search_term = self.search_term_edit.text().strip()
        similarity_threshold = self.similarity_threshold_spinbox.value()

        # Evita ricerca vuota se il widget non è visibile la prima volta
        if not search_term and not self.isVisible():
            self.results_table.setRowCount(0)
            self._aggiorna_stato_pulsanti_azione()
            return
        if not search_term and self.isVisible():  # Se visibile e si preme cerca senza termine
            QMessageBox.information(
                self, "Ricerca Possessori", "Inserire un termine di ricerca.")
            self.results_table.setRowCount(0)
            self._aggiorna_stato_pulsanti_azione()
            return

        try:
            possessori = self.db_manager.ricerca_avanzata_possessori(
                query_text=search_term,
                similarity_threshold=similarity_threshold
            )
            self.results_table.setRowCount(0)
            if not possessori:
                QMessageBox.information(
                    self, "Ricerca Possessori", "Nessun possessore trovato con i criteri specificati.")
            else:
                self.results_table.setRowCount(len(possessori))
                for row_idx, possessore_data in enumerate(possessori):
                    col = 0
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(
                        str(possessore_data.get('id', 'N/D'))))
                    col += 1
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(
                        possessore_data.get('nome_completo', 'N/D')))
                    col += 1
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(
                        possessore_data.get('cognome_nome', 'N/D')))
                    col += 1
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(
                        possessore_data.get('paternita', 'N/D')))
                    col += 1
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(
                        possessore_data.get('comune_nome', 'N/D')))
                    col += 1  # Nome del comune
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(
                        f"{possessore_data.get('similarity', 0.0):.3f}"))
                    col += 1
                    self.results_table.setItem(row_idx, col, QTableWidgetItem(
                        str(possessore_data.get('num_partite', 'N/D'))))
                    col += 1
                self.results_table.resizeColumnsToContents()

        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore durante la ricerca possessori (GUI - Consultazione): {e}", exc_info=True)
            QMessageBox.critical(
                self, "Errore Ricerca", f"Si è verificato un errore durante la ricerca: {e}")
        finally:
            self._aggiorna_stato_pulsanti_azione()  # Aggiorna stato pulsanti dopo ricerca

    # Rimuovi _show_possessore_details se non serve più o se è sostituito da apri_modifica_possessore_selezionato
    # def _show_possessore_details(self, item: QTableWidgetItem): ...


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


class InserimentoComuneWidget(QWidget):
    # Definisci il segnale a livello di classe
    # Questo segnale emetterà l'ID del nuovo comune inserito (o True/False per successo generico)
    comune_appena_inserito = pyqtSignal(int) # Emette l'ID del nuovo comune
    # Oppure, se non vuoi passare l'ID: comune_appena_inserito = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None,
                 db_manager: Optional['CatastoDBManager'] = None,
                 utente_attuale_info: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.utente_attuale_info = utente_attuale_info
        self._initUI()
        self._carica_elenco_periodi()

    def _initUI(self):
        # ... (definizione di main_layout, form_group, form_layout_container, form_layout come prima) ...
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        form_group = QGroupBox("Dati del Nuovo Comune")
        form_layout_container = QVBoxLayout(form_group)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.nome_comune_edit = QLineEdit()
        self.provincia_edit = QLineEdit("SV")
        self.provincia_edit.setMaxLength(2)
        self.regione_edit = QLineEdit()
        self.periodo_id_spinbox = QSpinBox()
        self.periodo_id_spinbox.setMinimum(1)
        self.periodo_id_spinbox.setMaximum(99999)
        form_layout.addRow("Nome Comune (*):", self.nome_comune_edit)
        form_layout.addRow("Provincia (*):", self.provincia_edit)
        form_layout.addRow("Regione (*):", self.regione_edit)
        form_layout.addRow("Periodo ID (*):", self.periodo_id_spinbox)
        form_layout_container.addLayout(form_layout)
        main_layout.addWidget(form_group)

        # --- Sezione Riepilogo Periodi Storici ---
        periodi_riepilogo_group = QGroupBox("Riferimento Periodi Storici")
        periodi_riepilogo_layout = QVBoxLayout(periodi_riepilogo_group)
        periodi_riepilogo_layout.setSpacing(5)

        # Layout per pulsanti sopra la tabella dei periodi
        periodi_table_actions_layout = QHBoxLayout()
        self.btn_dettaglio_modifica_periodo = QPushButton(QApplication.style(
        ).standardIcon(QStyle.SP_FileDialogInfoView), " Dettagli/Modifica Periodo")
        self.btn_dettaglio_modifica_periodo.setToolTip(
            "Visualizza o modifica i dettagli del periodo storico selezionato")
        self.btn_dettaglio_modifica_periodo.clicked.connect(
            self._apri_dettaglio_modifica_periodo)
        self.btn_dettaglio_modifica_periodo.setEnabled(
            False)  # Inizialmente disabilitato
        periodi_table_actions_layout.addWidget(
            self.btn_dettaglio_modifica_periodo)
        periodi_table_actions_layout.addStretch()
        btn_aggiorna_periodi = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_BrowserReload), " Aggiorna Elenco")
        btn_aggiorna_periodi.clicked.connect(self._carica_elenco_periodi)
        periodi_table_actions_layout.addWidget(btn_aggiorna_periodi)
        # Aggiungi layout azioni sopra la tabella
        periodi_riepilogo_layout.addLayout(periodi_table_actions_layout)

        self.periodi_table = QTableWidget()
        self.periodi_table.setColumnCount(4)
        self.periodi_table.setHorizontalHeaderLabels(
            ["ID", "Nome Periodo", "Anno Inizio", "Anno Fine"])
        self.periodi_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.periodi_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.periodi_table.setSelectionMode(QTableWidget.SingleSelection)
        self.periodi_table.setAlternatingRowColors(True)
        self.periodi_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.periodi_table.setMinimumHeight(120)
        self.periodi_table.setMaximumHeight(250)
        self.periodi_table.itemSelectionChanged.connect(
            self._aggiorna_stato_pulsante_dettaglio_periodo)  # Connetti a nuovo metodo
        self.periodi_table.itemDoubleClicked.connect(
            self._apri_dettaglio_modifica_periodo_da_doppio_click)  # Connetti doppio click

        periodi_riepilogo_layout.addWidget(self.periodi_table)
        main_layout.addWidget(periodi_riepilogo_group)

        # ... (linea e pulsanti Inserisci/Pulisci come prima) ...
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.submit_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogSaveButton), " Inserisci Comune")
        self.submit_button.clicked.connect(self.inserisci_comune)
        self.clear_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogDiscardButton), " Pulisci Campi")
        self.clear_button.clicked.connect(self.pulisci_campi)
        button_layout.addStretch()
        button_layout.addWidget(self.submit_button)
        button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)
        main_layout.addStretch(1)

    def _aggiorna_stato_pulsante_dettaglio_periodo(self):
        """Abilita il pulsante Dettagli/Modifica Periodo se una riga è selezionata."""
        if hasattr(self, 'btn_dettaglio_modifica_periodo'):  # Controllo di sicurezza
            self.btn_dettaglio_modifica_periodo.setEnabled(
                bool(self.periodi_table.selectedItems()))

    def _get_selected_periodo_id(self) -> Optional[int]:
        """Restituisce l'ID del periodo attualmente selezionato nella tabella dei periodi."""
        selected_items = self.periodi_table.selectedItems()
        if not selected_items:
            return None

        current_row = self.periodi_table.currentRow()
        if current_row < 0:
            return None

        id_item = self.periodi_table.item(current_row, 0)  # Colonna ID
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def _apri_dettaglio_modifica_periodo_da_doppio_click(self, item: QTableWidgetItem):
        """Gestisce il doppio click sulla tabella dei periodi."""
        # Non serve controllare item se la chiamata proviene da un segnale valido di itemDoubleClicked
        self._apri_dettaglio_modifica_periodo()

    def _apri_dettaglio_modifica_periodo(self):
        """Apre il dialogo per visualizzare/modificare il periodo selezionato."""
        selected_periodo_id = self._get_selected_periodo_id()
        if selected_periodo_id is None:
            QMessageBox.information(self, "Nessuna Selezione",
                                    "Selezionare un periodo dalla tabella per vederne/modificarne i dettagli.")
            return

        dialog = PeriodoStoricoDetailsDialog(
            self.db_manager, selected_periodo_id, self)
        if dialog.exec_() == QDialog.Accepted:
            # Se il dialogo è stato accettato (modifiche salvate), ricarica l'elenco dei periodi
            logging.getLogger("CatastoGUI").info(
                f"Dialogo dettagli/modifica periodo ID {selected_periodo_id} chiuso con successo. Aggiorno elenco periodi.")
            self._carica_elenco_periodi()
        else:
            logging.getLogger("CatastoGUI").info(
                f"Dialogo dettagli/modifica periodo ID {selected_periodo_id} annullato o chiuso.")

    # Mantieni _carica_elenco_periodi, pulisci_campi, inserisci_comune come sono stati definiti correttamente prima.
    # ...
    def _carica_elenco_periodi(self):
        self.periodi_table.setRowCount(0)
        self.periodi_table.setSortingEnabled(False)
        try:
            logging.getLogger("CatastoGUI").info(
                "Chiamata a db_manager.get_historical_periods()...")
            periodi = self.db_manager.get_historical_periods()
            logging.getLogger("CatastoGUI").info(
                f"Elenco periodi ricevuto da DBManager (tipo: {type(periodi)}): {periodi if periodi is not None else 'None'}")
            if periodi:
                logging.getLogger("CatastoGUI").info(
                    f"Numero di periodi ricevuti: {len(periodi)}")
                self.periodi_table.setRowCount(len(periodi))
                for row_idx, periodo_data in enumerate(periodi):
                    col = 0
                    id_item = QTableWidgetItem(
                        str(periodo_data.get('id', 'N/D')))
                    self.periodi_table.setItem(row_idx, col, id_item)
                    col += 1
                    nome_item = QTableWidgetItem(
                        periodo_data.get('nome', 'N/D'))
                    self.periodi_table.setItem(row_idx, col, nome_item)
                    col += 1
                    anno_i_item = QTableWidgetItem(
                        str(periodo_data.get('anno_inizio', 'N/D')))
                    self.periodi_table.setItem(row_idx, col, anno_i_item)
                    col += 1
                    anno_f_item = QTableWidgetItem(
                        str(periodo_data.get('anno_fine', 'N/D')))
                    self.periodi_table.setItem(row_idx, col, anno_f_item)
                    col += 1
                self.periodi_table.resizeColumnsToContents()
            else:
                logging.getLogger("CatastoGUI").warning(
                    "Nessun periodo storico restituito da db_manager.get_historical_periods() o la lista è vuota.")
                self.periodi_table.setRowCount(1)
                self.periodi_table.setItem(0, 0, QTableWidgetItem(
                    "Nessun periodo storico trovato nel database."))
                self.periodi_table.setSpan(
                    0, 0, 1, self.periodi_table.columnCount())
        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore imprevisto durante _carica_elenco_periodi: {e}", exc_info=True)
            QMessageBox.warning(self, "Errore Caricamento Periodi",
                                f"Impossibile caricare l'elenco dei periodi:\n{type(e).__name__}: {e}")
            self.periodi_table.setRowCount(1)
            self.periodi_table.setItem(0, 0, QTableWidgetItem(
                "Errore nel caricamento dei periodi."))
            self.periodi_table.setSpan(
                0, 0, 1, self.periodi_table.columnCount())
        finally:
            self.periodi_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsante_dettaglio_periodo()  # Aggiorna stato pulsante qui

    def pulisci_campi(self):
        self.nome_comune_edit.clear()
        self.provincia_edit.setText("SV")
        self.regione_edit.clear()
        self.periodo_id_spinbox.setValue(self.periodo_id_spinbox.minimum())
        self.nome_comune_edit.setFocus()

    def inserisci_comune(self):
        """Inserisce un nuovo comune nel database."""
        nome_comune = self.nome_comune_edit.text().strip()
        provincia = self.provincia_edit.text().strip()
        regione = self.regione_edit.text().strip()
        periodo_id_val = self.periodo_id_spinbox.value()
        if not nome_comune:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il nome del comune è obbligatorio.")
            self.nome_comune_edit.setFocus()
            return
        if not provincia:
            QMessageBox.warning(self, "Dati Mancanti",
                                "La provincia è obbligatoria (2 caratteri).")
            self.provincia_edit.setFocus()
            return
        if not regione:
            QMessageBox.warning(self, "Dati Mancanti",
                                "La regione è obbligatoria.")
            self.regione_edit.setFocus()
            return
        if periodo_id_val < self.periodo_id_spinbox.minimum():
            QMessageBox.warning(
                self, "Dati Mancanti", "L'ID del periodo è obbligatorio e deve essere un valore valido.")
            self.periodo_id_spinbox.setFocus()
            return
        username_per_log = "utente_sconosciuto"
        if self.utente_attuale_info and isinstance(self.utente_attuale_info, dict):
            username_per_log = self.utente_attuale_info.get(
                'username', 'utente_sconosciuto')
        elif isinstance(self.utente_attuale_info, str):
            username_per_log = self.utente_attuale_info
        logging.getLogger("CatastoGUI").debug(
            f"InserimentoComuneWidget: Invio al DBManager -> nome='{nome_comune}', prov='{provincia}', regione='{regione}', periodo_id='{periodo_id_val}', utente='{username_per_log}'")
        try:
            comune_id = self.db_manager.aggiungi_comune(
                nome_comune=nome_comune, provincia=provincia, regione=regione,
                periodo_id=periodo_id_val, utente=username_per_log
            )
            if comune_id is not None:
                QMessageBox.information(
                    self, "Successo", f"Comune '{nome_comune}' inserito con ID: {comune_id}.")
                self.pulisci_campi()
                self._carica_elenco_periodi()
                # Emetti il segnale con l'ID del nuovo comune!
                self.comune_appena_inserito.emit(comune_id)
                logging.getLogger("CatastoGUI").info(f"Segnale comune_appena_inserito emesso per comune ID: {comune_id}")
                      
        except DBUniqueConstraintError as uve:
            logging.getLogger("CatastoGUI").warning(
                f"Unicità violata inserendo comune '{nome_comune}': {str(uve)}")
            QMessageBox.critical(self, "Errore di Unicità", str(uve))
        except DBDataError as dde:
            logging.getLogger("CatastoGUI").warning(
                f"Dati non validi per comune '{nome_comune}': {str(dde)}")
            QMessageBox.warning(self, "Dati Non Validi", str(dde))
        except DBMError as dbe:
            logging.getLogger("CatastoGUI").error(
                f"Errore DB inserendo comune '{nome_comune}': {str(dbe)}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", str(dbe))
        except Exception as e:
            logging.getLogger("CatastoGUI").critical(
                f"Errore imprevisto inserendo comune '{nome_comune}': {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico",
                                 f"Errore imprevisto: {type(e).__name__}: {e}")


class InserimentoPossessoreWidget(QWidget):
    def __init__(self, db_manager: 'CatastoDBManager', parent=None): # Usa la stringa per il type hint se CatastoDBManager non è ancora definito/importato globalmente
        super().__init__(parent)
        self.db_manager = db_manager
        self.comuni_list_data: List[Dict[str, Any]] = []
        # self.selected_comune_id: Optional[int] = None # Se lo usi, assicurati sia gestito

        main_layout = QVBoxLayout(self)

        form_group = QGroupBox("Dati del Nuovo Possessore")
        form_layout = QGridLayout(form_group) # Usiamo QGridLayout per più flessibilità

        # 1. Cognome e Nome (diventa l'input primario per queste info)
        form_layout.addWidget(QLabel("Cognome e Nome (*):"), 0, 0)
        self.cognome_nome_edit = QLineEdit() # Questo era opzionale, ora è primario
        self.cognome_nome_edit.setPlaceholderText("Es. Rossi Mario, Bianchi Giovanni")
        form_layout.addWidget(self.cognome_nome_edit, 0, 1, 1, 2) # Span su 2 colonne

        # 2. Paternità
        form_layout.addWidget(QLabel("Paternità (es. fu Carlo):"), 1, 0)
        self.paternita_edit = QLineEdit()
        form_layout.addWidget(self.paternita_edit, 1, 1, 1, 2) # Span su 2 colonne

        # 3. Pulsante per Generare Nome Completo
        self.btn_genera_nome_completo = QPushButton("Genera Nome Completo")
        self.btn_genera_nome_completo.setToolTip("Genera il Nome Completo dai campi Cognome/Nome e Paternità")
        self.btn_genera_nome_completo.clicked.connect(self._genera_e_imposta_nome_completo)
        form_layout.addWidget(self.btn_genera_nome_completo, 2, 1, 1, 1) # Posizionato sotto i campi di input

        # 4. Nome Completo (ora principalmente generato, ma può essere editabile per correzioni)
        form_layout.addWidget(QLabel("Nome Completo (generato) (*):"), 3, 0)
        self.nome_completo_edit = QLineEdit()
        self.nome_completo_edit.setPlaceholderText("Verrà generato o inserire manualmente se necessario")
        form_layout.addWidget(self.nome_completo_edit, 3, 1, 1, 2) # Span su 2 colonne

        # 5. Comune di Riferimento (come prima)
        form_layout.addWidget(QLabel("Comune di Riferimento (*):"), 4, 0)
        self.comune_combo = QComboBox()
        self._load_comuni_for_combo()
        form_layout.addWidget(self.comune_combo, 4, 1, 1, 2) # Span su 2 colonne

        # 6. Checkbox Attivo (come prima)
        self.attivo_checkbox = QCheckBox("Attivo")
        self.attivo_checkbox.setChecked(True)
        form_layout.addWidget(self.attivo_checkbox, 5, 0, 1, 3) # Span su 3 colonne

        # Rimuovi il vecchio campo "Cognome Nome (opzionale, per ricerca)" se non serve più come input separato
        # Se il campo cognome_nome nel DB è distinto da nome_completo e serve per ricerca,
        # allora lo si può popolare automaticamente quando si genera nome_completo o lo si salva.

        main_layout.addWidget(form_group)

        self.save_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogSaveButton), "Salva Nuovo Possessore")
        self.save_button.clicked.connect(self._salva_possessore)
        
        self.clear_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogDiscardButton), "Pulisci Campi")
        self.clear_button.clicked.connect(self._pulisci_campi_possessore)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)

        main_layout.addStretch()
        self.setLayout(main_layout)
        self._pulisci_campi_possessore() # Per impostare lo stato iniziale

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

    def _load_comuni_for_combo(self): # Come prima
        try:
            # Assumendo che self.db_manager sia già inizializzato
            self.comuni_list_data = self.db_manager.get_comuni() # Metodo che restituisce lista di dict [{'id': X, 'nome': 'Y', 'provincia': 'Z'}]
            self.comune_combo.clear()
            if self.comuni_list_data:
                for comune_data in self.comuni_list_data:
                    display_text = f"{comune_data.get('nome', 'N/D')} ({comune_data.get('provincia', 'N/P')})"
                    self.comune_combo.addItem(display_text, userData=comune_data.get('id'))
            else:
                self.comune_combo.addItem("Nessun comune nel DB", userData=None)
        except Exception as e:
            logging.getLogger("CatastoGUI").error(f"Errore caricamento comuni per InserimentoPossessoreWidget: {e}", exc_info=True)
            self.comune_combo.clear()
            self.comune_combo.addItem("Errore caricamento comuni", userData=None)

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
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_partita_id_export: Optional[int] = None
        self.selected_possessore_id_export: Optional[int] = None

        main_layout = QVBoxLayout(self)

        # Sotto-Tab
        sub_tabs = QTabWidget()

        # Sotto-tab Esporta Partita
        esporta_partita_widget = QWidget()
        ep_layout = QVBoxLayout(esporta_partita_widget)

        ep_input_group = QGroupBox("Seleziona Partita da Esportare")
        ep_input_layout = QGridLayout(ep_input_group)
        ep_input_layout.addWidget(QLabel("ID Partita:"), 0, 0)
        self.partita_id_export_edit = QSpinBox()
        self.partita_id_export_edit.setMinimum(1)
        self.partita_id_export_edit.setMaximum(999999)
        ep_input_layout.addWidget(self.partita_id_export_edit, 0, 1)
        self.btn_cerca_partita_export = QPushButton("Cerca Partita...")
        self.btn_cerca_partita_export.clicked.connect(
            self._cerca_partita_per_export)
        ep_input_layout.addWidget(self.btn_cerca_partita_export, 0, 2)
        self.partita_info_export_label = QLabel("Nessuna partita selezionata.")
        ep_input_layout.addWidget(self.partita_info_export_label, 1, 0, 1, 3)
        ep_layout.addWidget(ep_input_group)

        ep_btn_layout = QHBoxLayout()
        self.btn_export_partita_json = QPushButton("Esporta JSON")
        self.btn_export_partita_json.clicked.connect(
            self._handle_export_partita_json)
        self.btn_export_partita_csv = QPushButton("Esporta CSV")
        self.btn_export_partita_csv.clicked.connect(
            self._handle_export_partita_csv)
        self.btn_export_partita_pdf = QPushButton("Esporta PDF")
        self.btn_export_partita_pdf.clicked.connect(
            self._handle_export_partita_pdf)
        self.btn_export_partita_pdf.setEnabled(
            FPDF_AVAILABLE)  # Disabilita se FPDF non c'è
        ep_btn_layout.addWidget(self.btn_export_partita_json)
        ep_btn_layout.addWidget(self.btn_export_partita_csv)
        ep_btn_layout.addWidget(self.btn_export_partita_pdf)
        ep_layout.addLayout(ep_btn_layout)
        ep_layout.addStretch()
        sub_tabs.addTab(esporta_partita_widget, "Esporta Partita")

        # Sotto-tab Esporta Possessore
        esporta_possessore_widget = QWidget()
        eposs_layout = QVBoxLayout(esporta_possessore_widget)

        eposs_input_group = QGroupBox("Seleziona Possessore da Esportare")
        eposs_input_layout = QGridLayout(eposs_input_group)
        eposs_input_layout.addWidget(QLabel("ID Possessore:"), 0, 0)
        self.possessore_id_export_edit = QSpinBox()
        self.possessore_id_export_edit.setMinimum(1)
        self.possessore_id_export_edit.setMaximum(999999)
        eposs_input_layout.addWidget(self.possessore_id_export_edit, 0, 1)
        self.btn_cerca_possessore_export = QPushButton("Cerca Possessore...")
        self.btn_cerca_possessore_export.clicked.connect(
            self._cerca_possessore_per_export)
        eposs_input_layout.addWidget(self.btn_cerca_possessore_export, 0, 2)
        self.possessore_info_export_label = QLabel(
            "Nessun possessore selezionato.")
        eposs_input_layout.addWidget(
            self.possessore_info_export_label, 1, 0, 1, 3)
        eposs_layout.addWidget(eposs_input_group)

        eposs_btn_layout = QHBoxLayout()
        self.btn_export_poss_json = QPushButton("Esporta JSON")
        self.btn_export_poss_json.clicked.connect(
            self._handle_export_possessore_json)
        self.btn_export_poss_csv = QPushButton("Esporta CSV")
        self.btn_export_poss_csv.clicked.connect(
            self._handle_export_possessore_csv)
        self.btn_export_poss_pdf = QPushButton("Esporta PDF")
        self.btn_export_poss_pdf.clicked.connect(
            self._handle_export_possessore_pdf)
        self.btn_export_poss_pdf.setEnabled(
            FPDF_AVAILABLE)  # Disabilita se FPDF non c'è
        eposs_btn_layout.addWidget(self.btn_export_poss_json)
        eposs_btn_layout.addWidget(self.btn_export_poss_csv)
        eposs_btn_layout.addWidget(self.btn_export_poss_pdf)
        eposs_layout.addLayout(eposs_btn_layout)
        eposs_layout.addStretch()
        sub_tabs.addTab(esporta_possessore_widget, "Esporta Possessore")

        main_layout.addWidget(sub_tabs)

    def _cerca_partita_per_export(self):
        # Assumendo che PartitaSearchDialog esista e sia simile a quello per i report
        dialog = PartitaSearchDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_partita_id:
            self.selected_partita_id_export = dialog.selected_partita_id
            self.partita_id_export_edit.setValue(
                self.selected_partita_id_export)
            # Potrebbe mostrare nome comune e numero partita
            partita_details = self.db_manager.get_partita_details(
                self.selected_partita_id_export)
            if partita_details:
                self.partita_info_export_label.setText(
                    f"Selezionata: N. {partita_details.get('numero_partita')} (Comune: {partita_details.get('comune_nome')})")
            else:
                self.partita_info_export_label.setText("Partita non trovata.")
        else:
            self.selected_partita_id_export = None
            self.partita_info_export_label.setText(
                "Nessuna partita selezionata.")

    def _handle_export_partita_json(self):
        partita_id = self.partita_id_export_edit.value()
        if partita_id > 0:
            gui_esporta_partita_json(self, self.db_manager, partita_id)
        else:
            QMessageBox.warning(self, "Selezione Mancante",
                                "Inserisci o cerca un ID Partita valido.")

    def _handle_export_partita_csv(self):
        partita_id = self.partita_id_export_edit.value()
        if partita_id > 0:
            gui_esporta_partita_csv(self, self.db_manager, partita_id)
        else:
            QMessageBox.warning(self, "Selezione Mancante",
                                "Inserisci o cerca un ID Partita valido.")

    def _handle_export_partita_pdf(self):
        partita_id = self.partita_id_export_edit.value()
        if partita_id > 0:
            gui_esporta_partita_pdf(self, self.db_manager, partita_id)
        else:
            QMessageBox.warning(self, "Selezione Mancante",
                                "Inserisci o cerca un ID Partita valido.")

    def _cerca_possessore_per_export(self):
        logging.getLogger("CatastoGUI").info(
            ">>> _cerca_possessore_per_export: Metodo chiamato.")

        dialog = PossessoreSelectionDialog(
            db_manager=self.db_manager,
            comune_id=None,  # Per ricerca globale
            parent=self
        )
        dialog.setWindowTitle("Seleziona Possessore per Esportazione")

        if dialog.exec_() == QDialog.Accepted:
            # --- MODIFICA QUI ---
            if hasattr(dialog, 'selected_possessore') and \
               dialog.selected_possessore and \
               isinstance(dialog.selected_possessore, dict) and \
               dialog.selected_possessore.get('id') is not None:

                self.selected_possessore_id_export = dialog.selected_possessore.get(
                    'id')
                self.possessore_id_export_edit.setValue(
                    self.selected_possessore_id_export)

                nome_completo_sel = dialog.selected_possessore.get(
                    'nome_completo', 'N/D')
                # Per il nome del comune, potremmo dover fare una chiamata separata se non è già in selected_possessore
                # o se get_possessore_full_details lo restituisce in modo più affidabile.
                # Il dizionario 'selected_possessore' dovrebbe contenere anche 'comune_riferimento_nome' se
                # la query in PossessoreSelectionDialog (get_possessori_by_comune o search_possessori_by_term_globally)
                # lo include con un JOIN alla tabella comuni.
                # Altrimenti, recuperiamo i dettagli completi.

                comune_nome_sel = dialog.selected_possessore.get(
                    'comune_riferimento_nome', None)
                if comune_nome_sel is None:  # Fallback se non presente in selected_possessore
                    details = self.db_manager.get_possessore_full_details(
                        self.selected_possessore_id_export)
                    if details:
                        comune_nome_sel = details.get(
                            'comune_riferimento_nome', 'N/D')
                    else:
                        comune_nome_sel = 'N/D (dettagli non trovati)'

                self.possessore_info_export_label.setText(
                    f"Selezionato: {nome_completo_sel} (Comune Rif.: {comune_nome_sel}, ID: {self.selected_possessore_id_export})"
                )
                logging.getLogger("CatastoGUI").info(
                    f"_cerca_possessore_per_export: Possessore selezionato ID {self.selected_possessore_id_export}")

            else:  # selected_possessore non impostato o ID mancante
                self.selected_possessore_id_export = None
                self.possessore_id_export_edit.setValue(0)
                self.possessore_info_export_label.setText(
                    "Nessun possessore selezionato o ID non valido.")
                logging.getLogger("CatastoGUI").warning(
                    "_cerca_possessore_per_export: Dialogo accettato ma 'selected_possessore' o il suo 'id' non validi.")
            # --- FINE MODIFICA ---
        else:  # Dialogo annullato
            # Non resettare necessariamente la selezione precedente se l'utente annulla
            if self.selected_possessore_id_export is None:  # Resetta solo se non c'era già una selezione valida
                self.possessore_id_export_edit.setValue(0)
                self.possessore_info_export_label.setText(
                    "Nessun possessore selezionato.")
            logging.getLogger("CatastoGUI").info(
                "_cerca_possessore_per_export: Dialogo selezione annullato.")

    def _handle_export_possessore_json(self):
        possessore_id = self.possessore_id_export_edit.value()
        if possessore_id > 0:
            gui_esporta_possessore_json(self, self.db_manager, possessore_id)
        else:
            QMessageBox.warning(self, "Selezione Mancante",
                                "Inserisci o cerca un ID Possessore valido.")

    def _handle_export_possessore_csv(self):
        possessore_id = self.possessore_id_export_edit.value()
        if possessore_id > 0:
            gui_esporta_possessore_csv(self, self.db_manager, possessore_id)
        else:
            QMessageBox.warning(self, "Selezione Mancante",
                                "Inserisci o cerca un ID Possessore valido.")

    def _handle_export_possessore_pdf(self):
        possessore_id = self.possessore_id_export_edit.value()
        if possessore_id > 0:
            gui_esporta_possessore_pdf(self, self.db_manager, possessore_id)
        else:
            QMessageBox.warning(self, "Selezione Mancante",
                                "Inserisci o cerca un ID Possessore valido.")
            # Non fare self.reject() qui, permette un altro tentativo o l'uscita manuale


class ReportisticaWidget(QWidget):
    def __init__(self, db_manager, parent=None):
        super(ReportisticaWidget, self).__init__(parent)
        self.db_manager = db_manager

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # --- Tab Report Proprietà ---
        report_tab = QWidget()
        report_layout = QVBoxLayout(report_tab)
        # ... (input_layout, self.partita_id_edit, self.search_partita_button come prima) ...
        input_layout = QHBoxLayout()
        partita_id_label = QLabel("ID della partita:")
        self.partita_id_edit = QSpinBox()
        self.partita_id_edit.setRange(1, 9999999)
        self.search_partita_button = QPushButton("Cerca...")
        self.search_partita_button.clicked.connect(self.search_partita)
        input_layout.addWidget(partita_id_label)
        input_layout.addWidget(self.partita_id_edit)
        input_layout.addWidget(self.search_partita_button)
        report_layout.addLayout(input_layout)

        self.generate_cert_button = QPushButton("Genera Report")
        self.generate_cert_button.clicked.connect(self.generate_report)
        report_layout.addWidget(self.generate_cert_button)
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setFontFamily("Courier New")
        report_layout.addWidget(self.report_text)

        # Layout per i pulsanti di esportazione
        export_buttons_cert_layout = QHBoxLayout()
        self.export_cert_txt_button = QPushButton("Esporta in TXT")
        self.export_cert_txt_button.clicked.connect(lambda: self.export_report(
            self.report_text.toPlainText(), "report_proprieta", "txt"))
        self.export_cert_pdf_button = QPushButton("Esporta in PDF")
        self.export_cert_pdf_button.clicked.connect(
            self._export_report_pdf)  # NUOVO METODO
        self.export_cert_pdf_button.setEnabled(FPDF_AVAILABLE)
        export_buttons_cert_layout.addWidget(self.export_cert_txt_button)
        export_buttons_cert_layout.addWidget(
            self.export_cert_pdf_button)  # AGGIUNTO PULSANTE PDF
        report_layout.addLayout(export_buttons_cert_layout)
        tabs.addTab(report_tab, "Report Proprietà")

        # --- Tab Report Genealogico ---
        genealogico_tab = QWidget()
        genealogico_layout = QVBoxLayout(genealogico_tab)
        # ... (input_gen_layout, self.partita_id_gen_edit, etc. come prima) ...
        input_gen_layout = QHBoxLayout()
        partita_id_gen_label = QLabel("ID della partita:")
        self.partita_id_gen_edit = QSpinBox()
        self.partita_id_gen_edit.setRange(1, 9999999)
        self.search_partita_gen_button = QPushButton("Cerca...")
        self.search_partita_gen_button.clicked.connect(self.search_partita_gen)
        input_gen_layout.addWidget(partita_id_gen_label)
        input_gen_layout.addWidget(self.partita_id_gen_edit)
        input_gen_layout.addWidget(self.search_partita_gen_button)
        genealogico_layout.addLayout(input_gen_layout)
        self.generate_gen_button = QPushButton("Genera Report Genealogico")
        self.generate_gen_button.clicked.connect(self.generate_genealogico)
        genealogico_layout.addWidget(self.generate_gen_button)
        self.genealogico_text = QTextEdit()
        self.genealogico_text.setReadOnly(True)
        self.genealogico_text.setFontFamily("Courier New")
        genealogico_layout.addWidget(self.genealogico_text)

        export_buttons_gen_layout = QHBoxLayout()
        self.export_gen_txt_button = QPushButton("Esporta in TXT")
        self.export_gen_txt_button.clicked.connect(lambda: self.export_report(
            self.genealogico_text.toPlainText(), "report_genealogico", "txt"))
        self.export_gen_pdf_button = QPushButton("Esporta in PDF")
        self.export_gen_pdf_button.clicked.connect(
            self._export_genealogico_pdf)  # NUOVO METODO
        self.export_gen_pdf_button.setEnabled(FPDF_AVAILABLE)
        export_buttons_gen_layout.addWidget(self.export_gen_txt_button)
        export_buttons_gen_layout.addWidget(
            self.export_gen_pdf_button)  # AGGIUNTO PULSANTE PDF
        genealogico_layout.addLayout(export_buttons_gen_layout)
        tabs.addTab(genealogico_tab, "Report Genealogico")

        # --- Tab Report Possessore ---
        possessore_tab = QWidget()
        possessore_layout = QVBoxLayout(possessore_tab)
        # ... (input_pos_layout, self.possessore_id_edit, etc. come prima) ...
        input_pos_layout = QHBoxLayout()
        possessore_id_label = QLabel("ID del possessore:")
        self.possessore_id_edit = QSpinBox()
        self.possessore_id_edit.setRange(1, 9999999)
        self.search_possessore_button = QPushButton("Cerca...")
        self.search_possessore_button.clicked.connect(self.search_possessore)
        input_pos_layout.addWidget(possessore_id_label)
        input_pos_layout.addWidget(self.possessore_id_edit)
        input_pos_layout.addWidget(self.search_possessore_button)
        possessore_layout.addLayout(input_pos_layout)
        self.generate_pos_button = QPushButton("Genera Report Possessore")
        self.generate_pos_button.clicked.connect(self.generate_possessore)
        possessore_layout.addWidget(self.generate_pos_button)
        self.possessore_text = QTextEdit()
        self.possessore_text.setReadOnly(True)
        self.possessore_text.setFontFamily("Courier New")
        possessore_layout.addWidget(self.possessore_text)

        export_buttons_pos_layout = QHBoxLayout()
        self.export_pos_txt_button = QPushButton("Esporta in TXT")
        self.export_pos_txt_button.clicked.connect(lambda: self.export_report(
            self.possessore_text.toPlainText(), "report_possessore", "txt"))
        self.export_pos_pdf_button = QPushButton("Esporta in PDF")
        self.export_pos_pdf_button.clicked.connect(
            self._export_possessore_pdf)  # NUOVO METODO
        self.export_pos_pdf_button.setEnabled(FPDF_AVAILABLE)
        export_buttons_pos_layout.addWidget(self.export_pos_txt_button)
        export_buttons_pos_layout.addWidget(
            self.export_pos_pdf_button)  # AGGIUNTO PULSANTE PDF
        possessore_layout.addLayout(export_buttons_pos_layout)
        tabs.addTab(possessore_tab, "Report Possessore")

        # --- Tab Report Consultazioni ---
        consultazioni_tab = QWidget()
        consultazioni_layout = QVBoxLayout(consultazioni_tab)
        # ... (filters_layout, self.data_inizio_edit, etc. come prima) ...
        filters_layout = QGridLayout()
        data_inizio_label = QLabel("Data inizio:")
        self.data_inizio_edit = QDateEdit()
        self.data_inizio_edit.setCalendarPopup(True)
        self.data_inizio_edit.setDate(QDate.currentDate().addYears(-1))
        self.data_inizio_check = QCheckBox("Usa filtro")
        self.data_inizio_check.setChecked(True)
        data_fine_label = QLabel("Data fine:")
        self.data_fine_edit = QDateEdit()
        self.data_fine_edit.setCalendarPopup(True)
        self.data_fine_edit.setDate(QDate.currentDate())
        self.data_fine_check = QCheckBox("Usa filtro")
        self.data_fine_check.setChecked(True)
        richiedente_label = QLabel("Richiedente:")
        self.richiedente_edit = QLineEdit()
        self.richiedente_edit.setPlaceholderText("Qualsiasi richiedente")
        filters_layout.addWidget(data_inizio_label, 0, 0)
        filters_layout.addWidget(self.data_inizio_edit, 0, 1)
        filters_layout.addWidget(self.data_inizio_check, 0, 2)
        filters_layout.addWidget(data_fine_label, 1, 0)
        filters_layout.addWidget(self.data_fine_edit, 1, 1)
        filters_layout.addWidget(self.data_fine_check, 1, 2)
        filters_layout.addWidget(richiedente_label, 2, 0)
        filters_layout.addWidget(self.richiedente_edit, 2, 1, 1, 2)
        consultazioni_layout.addLayout(filters_layout)
        self.generate_cons_button = QPushButton("Genera Report Consultazioni")
        self.generate_cons_button.clicked.connect(self.generate_consultazioni)
        consultazioni_layout.addWidget(self.generate_cons_button)
        self.consultazioni_text = QTextEdit()
        self.consultazioni_text.setReadOnly(True)
        self.consultazioni_text.setFontFamily("Courier New")
        consultazioni_layout.addWidget(self.consultazioni_text)

        export_buttons_cons_layout = QHBoxLayout()
        self.export_cons_txt_button = QPushButton("Esporta in TXT")
        self.export_cons_txt_button.clicked.connect(lambda: self.export_report(
            self.consultazioni_text.toPlainText(), "report_consultazioni", "txt"))
        self.export_cons_pdf_button = QPushButton("Esporta in PDF")
        self.export_cons_pdf_button.clicked.connect(
            self._export_consultazioni_pdf)  # NUOVO METODO
        self.export_cons_pdf_button.setEnabled(FPDF_AVAILABLE)
        export_buttons_cons_layout.addWidget(self.export_cons_txt_button)
        export_buttons_cons_layout.addWidget(
            self.export_cons_pdf_button)  # AGGIUNTO PULSANTE PDF
        consultazioni_layout.addLayout(export_buttons_cons_layout)
        tabs.addTab(consultazioni_tab, "Report Consultazioni")

        layout.addWidget(tabs)
        self.setLayout(layout)

    def search_partita(self):
        """Apre un dialogo per cercare una partita."""
        dialog = PartitaSearchDialog(self.db_manager, self)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.selected_partita_id:
            self.partita_id_edit.setValue(dialog.selected_partita_id)

    def search_partita_gen(self):
        """Apre un dialogo per cercare una partita per il report genealogico."""
        dialog = PartitaSearchDialog(self.db_manager, self)
        result = dialog.exec_()

        if result == QDialog.Accepted and dialog.selected_partita_id:
            self.partita_id_gen_edit.setValue(dialog.selected_partita_id)

    def search_possessore(self):
        """Apre un dialogo per cercare e selezionare un possessore globalmente."""
        logging.getLogger("CatastoGUI").info(
            "ReportisticaWidget: Apertura dialogo ricerca possessore.")
        # Assicurati che PossessoreSelectionDialog sia la classe corretta.
        # Passa comune_id=None per una ricerca globale.
        dialog = PossessoreSelectionDialog(
            db_manager=self.db_manager,
            comune_id=None,  # Indica una ricerca globale, non filtrata per comune
            parent=self
        )
        dialog.setWindowTitle(
            "Seleziona Possessore per Report")  # Titolo specifico

        if dialog.exec_() == QDialog.Accepted:
            # Assumendo che dialog.selected_possessore sia un dizionario con 'id'
            if hasattr(dialog, 'selected_possessore') and \
               dialog.selected_possessore and \
               isinstance(dialog.selected_possessore, dict) and \
               dialog.selected_possessore.get('id') is not None:

                selected_id = dialog.selected_possessore.get('id')
                self.possessore_id_edit.setValue(
                    selected_id)  # Aggiorna lo QSpinBox
                logging.getLogger("CatastoGUI").info(
                    f"ReportisticaWidget: Possessore selezionato ID: {selected_id}")
                # Opzionale: potresti voler mostrare il nome del possessore vicino allo spinbox
            else:
                logging.getLogger("CatastoGUI").warning(
                    "ReportisticaWidget: Dialogo selezione possessore accettato ma nessun possessore valido selezionato.")
        else:
            logging.getLogger("CatastoGUI").info(
                "ReportisticaWidget: Selezione possessore annullata.")

    def generate_report(self):
        """Genera un report di proprietà."""
        partita_id = self.partita_id_edit.value()

        if partita_id <= 0:
            QMessageBox.warning(
                self, "Errore", "Inserisci un ID partita valido.")
            return

        report = self.db_manager.genera_report_proprieta(partita_id)

        if report:
            self.report_text.setText(report)
        else:
            QMessageBox.warning(
                self, "Errore", f"Impossibile generare il report per la partita ID {partita_id}.")

    def generate_genealogico(self):
        """Genera un report genealogico."""
        partita_id = self.partita_id_gen_edit.value()

        if partita_id <= 0:
            QMessageBox.warning(
                self, "Errore", "Inserisci un ID partita valido.")
            return

        report = self.db_manager.genera_report_genealogico(partita_id)

        if report:
            self.genealogico_text.setText(report)
        else:
            QMessageBox.warning(
                self, "Errore", f"Impossibile generare il report genealogico per la partita ID {partita_id}.")

    def generate_possessore(self):
        """Genera un report sul possessore."""
        possessore_id = self.possessore_id_edit.value()

        if possessore_id <= 0:
            QMessageBox.warning(
                self, "Errore", "Inserisci un ID possessore valido.")
            return

        report = self.db_manager.genera_report_possessore(possessore_id)

        if report:
            self.possessore_text.setText(report)
        else:
            QMessageBox.warning(
                self, "Errore", f"Impossibile generare il report per il possessore ID {possessore_id}.")

    def generate_consultazioni(self):
        """Genera un report sulle consultazioni."""
        data_inizio = self.data_inizio_edit.date().toPyDate(
        ) if self.data_inizio_check.isChecked() else None
        data_fine = self.data_fine_edit.date().toPyDate(
        ) if self.data_fine_check.isChecked() else None
        richiedente = self.richiedente_edit.text().strip() or None

        report = self.db_manager.genera_report_consultazioni(
            data_inizio, data_fine, richiedente)

        if report:
            self.consultazioni_text.setText(report)
        else:
            QMessageBox.warning(
                self, "Errore", "Impossibile generare il report consultazioni.")

    # Modificato per estensione
    def export_report(self, text_content: str, report_type_name: str, file_extension: str):
        """Esporta il contenuto testuale di un report in un file."""
        if not text_content:
            QMessageBox.warning(self, "Attenzione",
                                "Nessun report da esportare.")
            return

        oggi = date.today().isoformat()  # Usa date.today() se datetime non è necessaria qui
        default_filename = f"report_{report_type_name}_{oggi}.{file_extension}"

        if file_extension == "txt":
            filter_str = "File di testo (*.txt);;Tutti i file (*)"
        elif file_extension == "pdf":
            filter_str = "File PDF (*.pdf);;Tutti i file (*)"
        else:
            filter_str = "Tutti i file (*)"

        filename, _ = QFileDialog.getSaveFileName(
            self, f"Salva Report {report_type_name.replace('_', ' ').title()}", default_filename, filter_str
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                QMessageBox.information(
                    self, "Esportazione Completata", f"Report salvato con successo in:\n{filename}")
            except Exception as e:
                logging.getLogger("CatastoGUI").error(
                    f"Errore durante il salvataggio del file {file_extension.upper()} per report {report_type_name}: {e}")
                QMessageBox.critical(
                    self, "Errore Esportazione", f"Errore durante il salvataggio del file:\n{e}")

  

    def _export_generic_text_to_pdf(self, text_content: str, default_filename_prefix: str, pdf_report_title: str):
        """Helper generico per esportare testo semplice in PDF, con anteprima."""

        if not FPDF_AVAILABLE:
            QMessageBox.critical(
                self, "Errore Libreria", "La libreria FPDF (fpdf2) non è disponibile per generare PDF.")
            return
        if not text_content.strip(): # Aggiunto .strip() per considerare stringhe di soli spazi come vuote
            QMessageBox.warning(
                self, "Nessun Contenuto", f"Nessun testo da esportare in PDF per '{pdf_report_title}'.")
            return

        # --- INIZIO LOGICA ANTEPRIMA ---
        # Istanzia e mostra il dialogo di anteprima testuale
        preview_dialog = PDFApreviewDialog(text_content, self, title=f"Anteprima: {pdf_report_title}")
        
        if preview_dialog.exec_() != QDialog.Accepted:
            logging.getLogger("CatastoGUI").info(f"Esportazione PDF per '{pdf_report_title}' annullata dall'utente dopo anteprima.")
            return # L'utente ha premuto "Annulla" nel dialogo di anteprima
        # --- FINE LOGICA ANTEPRIMA ---

        # Se l'utente ha confermato l'anteprima ("Procedi con Esportazione PDF"),
        # allora procedi con il salvataggio del file.
        default_filename = f"{default_filename_prefix}_{date.today().isoformat()}.pdf"
        filename_pdf, _ = QFileDialog.getSaveFileName(
            self, f"Salva PDF - {pdf_report_title}", default_filename, "File PDF (*.pdf)")

        if filename_pdf: # L'utente ha selezionato un percorso e un nome file
            try:
                # Usa la classe PDF generica
                pdf = GenericTextReportPDF(report_title=pdf_report_title) # Da app_utils.py
                pdf.add_page()
                pdf.add_report_text(text_content) # text_content è già disponibile
                pdf.output(filename_pdf)
                QMessageBox.information(self, "Esportazione PDF Completata",
                                        f"Report PDF salvato con successo in:\n{filename_pdf}")
            except Exception as e:
                logging.getLogger("CatastoGUI").error(
                    f"Errore durante la generazione del PDF per '{pdf_report_title}': {e}", exc_info=True)
                QMessageBox.critical(
                    self, "Errore Esportazione PDF", f"Impossibile generare il PDF:\n{e}")
        # else: L'utente ha annullato il QFileDialog.getSaveFileName, quindi non fare nulla.

    # I metodi specifici come _export_report_pdf ora chiameranno _export_generic_text_to_pdf
    # che include già la logica di anteprima. Quindi, _export_report_pdf non necessita modifiche dirette
    # per l'anteprima, a meno che tu non voglia passare dati diversi o un titolo diverso al dialogo di anteprima.

    def _export_report_pdf(self):
        # Il testo viene preso da self.report_text
        text_to_export = self.report_text.toPlainText()
        
        # Il titolo per il PDF e per il dialogo di anteprima
        report_title = f"Report Proprietà - Partita ID {self.partita_id_edit.value()}"
        
        # Il prefisso per il nome file di default
        filename_prefix = f"report_partita_{self.partita_id_edit.value()}"
        
        self._export_generic_text_to_pdf(
            text_content=text_to_export,
            default_filename_prefix=filename_prefix,
            pdf_report_title=report_title
        )

    # Dovrai applicare una logica simile anche agli altri metodi di esportazione PDF in ReportisticaWidget:
    # _export_genealogico_pdf, _export_possessore_pdf, _export_consultazioni_pdf.
    # Essi chiameranno _export_generic_text_to_pdf che ora gestisce l'anteprima.

    def _export_genealogico_pdf(self):
        text_to_export = self.genealogico_text.toPlainText()
        report_title = f"Report Genealogico - Partita ID {self.partita_id_gen_edit.value()}" # Assumendo che partita_id_gen_edit esista
        filename_prefix = f"report_genealogico_partita_{self.partita_id_gen_edit.value()}"
        self._export_generic_text_to_pdf(text_to_export, filename_prefix, report_title)

    def _export_possessore_pdf(self):
        text_to_export = self.possessore_text.toPlainText()
        report_title = f"Report Possessore - ID {self.possessore_id_edit.value()}" # Assumendo possessore_id_edit
        filename_prefix = f"report_possessore_{self.possessore_id_edit.value()}"
        self._export_generic_text_to_pdf(text_to_export, filename_prefix, report_title)

    def _export_consultazioni_pdf(self):
        text_to_export = self.consultazioni_text.toPlainText()
        report_title = "Report Consultazioni"
        filename_prefix = "report_consultazioni"
        self._export_generic_text_to_pdf(text_to_export, filename_prefix, report_title)

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

        self.refresh_immobili_button = QPushButton("Aggiorna Dati")
        self.refresh_immobili_button.clicked.connect(
            self.refresh_immobili_tipologia)

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

        # Tab Manutenzione Viste (o rinominalo "Manutenzione Database")
        manutenzione_tab = QWidget()
        # Layout verticale per questo tab
        manutenzione_layout = QVBoxLayout(manutenzione_tab)

        self.btn_verifica_integrita = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton),
                                                  " Verifica Integrità Database")
        self.btn_verifica_integrita.setToolTip(
            "Esegue controlli di integrità sul database.")
        self.btn_verifica_integrita.clicked.connect(
            self._esegui_verifica_integrita)
        manutenzione_layout.addWidget(
            self.btn_verifica_integrita)  # AGGIUNTO NUOVO PULSANTE

        self.update_views_button = QPushButton(
            "Aggiorna Tutte le Viste Materializzate")
        self.update_views_button.clicked.connect(self.update_all_views)
        manutenzione_layout.addWidget(self.update_views_button)

        self.maintenance_button = QPushButton(
            "Esegui Manutenzione DB (ANALYZE)")
        self.maintenance_button.clicked.connect(self.run_maintenance)
        manutenzione_layout.addWidget(self.maintenance_button)

        manutenzione_layout.addSpacing(15)  # Un po' di spazio

        manutenzione_layout.addWidget(
            QLabel("Log Operazioni di Manutenzione:"))
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setFixedHeight(150)  # O più se necessario
        manutenzione_layout.addWidget(self.status_text)

        manutenzione_layout.addStretch(1)  # Spinge tutto in alto
        # manutenzione_tab.setLayout(manutenzione_layout) # Non serve se passato al costruttore QVBoxLayout

        # Rinominato il tab per chiarezza
        tabs.addTab(manutenzione_tab, "Manutenzione Database")
        # --- NUOVO PULSANTE ---
        self.btn_verifica_integrita = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton),  # Scegli un'icona adatta
                                                  " Verifica Integrità Database")
        self.btn_verifica_integrita.setToolTip(
            "Esegue controlli di integrità sul database e riporta i risultati.")
        self.btn_verifica_integrita.clicked.connect(
            self._esegui_verifica_integrita)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)

        manutenzione_layout.addWidget(self.update_views_button)
        manutenzione_layout.addWidget(self.maintenance_button)
        manutenzione_layout.addWidget(QLabel("Log Operazioni:"))
        manutenzione_layout.addWidget(self.status_text)

        manutenzione_tab.setLayout(manutenzione_layout)
        tabs.addTab(manutenzione_tab, "Manutenzione Viste")

        layout.addWidget(tabs)
        self.setLayout(layout)

        # Carica dati iniziali
        self.refresh_stats_comune()
        self.refresh_immobili_tipologia()

    def refresh_stats_comune(self):
        """Aggiorna la tabella delle statistiche per comune."""
        self.stats_comune_table.setRowCount(0)

        if not self.db_manager or not self.db_manager.pool:  # <-- CONTROLLO AGGIUNTO
            logging.getLogger("CatastoGUI").warning(
                "StatisticheWidget: Pool DB non inizializzato. Impossibile caricare statistiche comuni.")
            # Opzionale: mostra messaggio nella tabella
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

        if not self.db_manager or not self.db_manager.pool:  # <-- CONTROLLO AGGIUNTO
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
        self.log_status(
            "Avvio aggiornamento di tutte le viste materializzate...")

        if self.db_manager.refresh_materialized_views():
            self.log_status("Aggiornamento viste completato con successo.")

            # Aggiorna le tabelle
            self.refresh_stats_comune()
            self.refresh_immobili_tipologia()
        else:
            self.log_status(
                "ERRORE: Aggiornamento viste non riuscito. Controlla i log.")

    def run_maintenance(self):
        """Esegue la manutenzione generale del database."""
        self.log_status("Avvio manutenzione database (ANALYZE)...")

        if self.db_manager.run_database_maintenance():
            self.log_status("Manutenzione database completata con successo.")
        else:
            self.log_status(
                "ERRORE: Manutenzione database non riuscita. Controlla i log.")

    def _esegui_verifica_integrita(self):
        if not self.db_manager or not self.db_manager.pool:
            QMessageBox.warning(self, "Database Non Pronto",
                                "Il database principale non è configurato o il pool non è attivo.")
            self.log_status(
                "Tentativo di verifica integrità fallito: pool DB non attivo.")
            return

        self.log_status("Avvio verifica integrità database...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            problemi_trovati, messaggi = self.db_manager.verifica_integrita_database_gui()

            # Logga tutti i messaggi ricevuti
            if messaggi:
                self.log_status("--- Risultato Verifica Integrità ---")
                for linea in messaggi.splitlines():
                    # Usa il metodo esistente per loggare nel QTextEdit
                    self.log_status(linea)
                self.log_status("--- Fine Risultato Verifica Integrità ---")

            if problemi_trovati:
                QMessageBox.warning(self, "Verifica Integrità",
                                    "La verifica di integrità ha rilevato potenziali problemi o errori.\n"
                                    "Consultare il log operazioni per i dettagli.")
            else:
                QMessageBox.information(self, "Verifica Integrità",
                                        "Verifica di integrità completata.\n"
                                        "Consultare il log operazioni per eventuali messaggi dalla procedura.")
        except DBMError as e:  # Se verifica_integrita_database_gui solleva DBMError per errori DB
            # Assumendo che log_status possa prendere 'error'
            self.log_status(
                f"ERRORE CRITICO durante la verifica integrità: {e}", error=True)
            QMessageBox.critical(
                self, "Errore Verifica Integrità", f"Errore database: {e}")
        except Exception as e:
            self.log_status(
                f"ERRORE IMPREVISTO durante la verifica integrità: {e}", error=True)
            logging.getLogger("CatastoGUI").error(
                "Errore imprevisto in _esegui_verifica_integrita", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto",
                                 f"Errore di sistema: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    # Modifica log_status per accettare un flag di errore (opzionale)
    def log_status(self, message: str, error: bool = False):  # Aggiunto parametro error
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if error:
            self.status_text.append(
                f"<font color='red'>[{timestamp}] {message}</font>")
        else:
            self.status_text.append(f"[{timestamp}] {message}")


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


class AuditLogViewerWidget(QWidget):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        # Titolo opzionale se usato come finestra separata
        self.setWindowTitle("Visualizzatore Log di Audit")

        self._init_ui()
        self._load_initial_data()  # Caricheremo i dati all'avvio o su richiesta

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Gruppo Filtri ---
        filters_group = QGroupBox("Filtri di Ricerca Log")
        # Usiamo QFormLayout per etichette e campi allineati
        filters_form_layout = QFormLayout(filters_group)

        self.filter_table_name_edit = QLineEdit()
        filters_form_layout.addRow(
            "Nome Tabella:", self.filter_table_name_edit)

        self.filter_operation_combo = QComboBox()
        self.filter_operation_combo.addItems(
            ["Tutte", "INSERT (I)", "UPDATE (U)", "DELETE (D)"])
        filters_form_layout.addRow("Operazione:", self.filter_operation_combo)

        # Filtro per Utente Applicativo (ID)
        self.filter_app_user_id_edit = QLineEdit()
        self.filter_app_user_id_edit.setPlaceholderText(
            "ID utente (opzionale)")
        filters_form_layout.addRow(
            "ID Utente Applicativo:", self.filter_app_user_id_edit)

        # Filtro per ID Record
        self.filter_record_id_edit = QLineEdit()
        self.filter_record_id_edit.setPlaceholderText(
            "ID record modificato (opzionale)")
        filters_form_layout.addRow("ID Record:", self.filter_record_id_edit)

        # Filtro per Data/Ora
        self.filter_start_datetime_edit = QDateTimeEdit(self)
        self.filter_start_datetime_edit.setDateTime(
            QDateTime.currentDateTime().addDays(-7))  # Default: ultima settimana
        self.filter_start_datetime_edit.setCalendarPopup(True)
        self.filter_start_datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        filters_form_layout.addRow(
            "Da Data/Ora:", self.filter_start_datetime_edit)

        self.filter_end_datetime_edit = QDateTimeEdit(self)
        self.filter_end_datetime_edit.setDateTime(
            QDateTime.currentDateTime())  # Default: ora attuale
        self.filter_end_datetime_edit.setCalendarPopup(True)
        self.filter_end_datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        filters_form_layout.addRow(
            "A Data/Ora:", self.filter_end_datetime_edit)

        self.filter_search_text_edit = QLineEdit()
        self.filter_search_text_edit.setPlaceholderText(
            "Cerca in dati JSON (opzionale, può essere lento)")
        filters_form_layout.addRow(
            "Testo in Dati JSON:", self.filter_search_text_edit)

        self.search_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogApplyButton), "Applica Filtri / Cerca")
        self.search_button.clicked.connect(self._apply_filters_and_search)

        self.reset_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogCancelButton), "Resetta Filtri")  # O SP_TrashIcon
        self.reset_button.clicked.connect(self._reset_filters)

        buttons_filter_layout = QHBoxLayout()
        buttons_filter_layout.addWidget(self.search_button)
        buttons_filter_layout.addWidget(self.reset_button)
        # Aggiungi layout bottoni al form layout
        filters_form_layout.addRow(buttons_filter_layout)

        main_layout.addWidget(filters_group)

        # --- Tabella Risultati Log ---
        self.log_table = QTableWidget()
        # ID Log, Timestamp, Utente App, Sessione, Tabella, Operazione, Record ID, IP, Dettagli (per JSON)
        self.log_table.setColumnCount(9)
        self.log_table.setHorizontalHeaderLabels([
            "ID Log", "Timestamp", "ID Utente App", "ID Sessione", "Tabella",
            "Operazione", "ID Record", "Indirizzo IP", "Modifiche?"
        ])
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.log_table.setSelectionMode(QTableWidget.SingleSelection)
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.log_table.horizontalHeader().setStretchLastSection(True)
        self.log_table.setAlternatingRowColors(True)
        # Abilita sorting client-side (o implementa server-side)
        self.log_table.setSortingEnabled(True)
        self.log_table.itemSelectionChanged.connect(
            self._display_log_details)  # Per mostrare dati JSON
        main_layout.addWidget(self.log_table)

        # --- Area Dettagli JSON ---
        details_group = QGroupBox("Dettagli Modifica (JSON)")
        # Layout orizzontale per Dati Prima e Dati Dopo
        details_layout = QHBoxLayout(details_group)

        self.details_before_text = QTextEdit()
        self.details_before_text.setReadOnly(True)
        self.details_before_text.setPlaceholderText(
            "Dati prima della modifica...")
        details_layout.addWidget(QLabel("Dati Prima:"))
        details_layout.addWidget(self.details_before_text)

        self.details_after_text = QTextEdit()
        self.details_after_text.setReadOnly(True)
        self.details_after_text.setPlaceholderText("Dati dopo la modifica...")
        details_layout.addWidget(QLabel("Dati Dopo:"))
        details_layout.addWidget(self.details_after_text)

        # Imposta stretch factors per dare più spazio ai QTextEdit rispetto alle QLabel
        details_layout.setStretchFactor(self.details_before_text, 1)
        details_layout.setStretchFactor(self.details_after_text, 1)
        details_layout.setStretchFactor(details_layout.itemAt(
            0).widget(), 0)  # QLabel "Dati Prima:"
        details_layout.setStretchFactor(
            details_layout.itemAt(2).widget(), 0)  # QLabel "Dati Dopo:"

        main_layout.addWidget(details_group)

        # TODO: Aggiungere controlli di paginazione ( QLabel per info pagina, QPushButton per Precedente/Successiva)
        # self.pagination_label = QLabel("Pagina 1 di X (Y risultati)")
        # self.prev_page_button = QPushButton("Precedente")
        # self.next_page_button = QPushButton("Successiva")
        # pagination_layout = QHBoxLayout()
        # ... aggiungere widget al pagination_layout e poi al main_layout ...

        self.setLayout(main_layout)

    def _apply_filters_and_search(self):
        # Qui recupereremo i valori dai campi di filtro
        filters = {
            "table_name": self.filter_table_name_edit.text().strip() or None,
            "operation_char": None,
            "app_user_id": self.filter_app_user_id_edit.text().strip() or None,
            "record_id": self.filter_record_id_edit.text().strip() or None,
            "start_datetime": self.filter_start_datetime_edit.dateTime().toPyDateTime(),
            "end_datetime": self.filter_end_datetime_edit.dateTime().toPyDateTime(),
            "search_text_json": self.filter_search_text_edit.text().strip() or None,
        }

        op_text = self.filter_operation_combo.currentText()
        if "INSERT" in op_text:
            filters["operation_char"] = "I"
        elif "UPDATE" in op_text:
            filters["operation_char"] = "U"
        elif "DELETE" in op_text:
            filters["operation_char"] = "D"

        # Converti app_user_id e record_id in interi se sono numerici, altrimenti None
        if filters["app_user_id"] and filters["app_user_id"].isdigit():
            filters["app_user_id"] = int(filters["app_user_id"])
        else:
            # O mostra un errore se si aspetta un numero
            filters["app_user_id"] = None

        if filters["record_id"] and filters["record_id"].isdigit():
            filters["record_id"] = int(filters["record_id"])
        else:
            filters["record_id"] = None

        self.current_filters = filters  # Salva i filtri correnti per la paginazione
        self.current_page = 1
        self._fetch_and_display_logs()

    def _reset_filters(self):
        self.filter_table_name_edit.clear()
        self.filter_operation_combo.setCurrentIndex(0)  # "Tutte"
        self.filter_app_user_id_edit.clear()
        self.filter_record_id_edit.clear()
        self.filter_start_datetime_edit.setDateTime(
            QDateTime.currentDateTime().addDays(-7))
        self.filter_end_datetime_edit.setDateTime(QDateTime.currentDateTime())
        self.filter_search_text_edit.clear()

        self.current_filters = None
        self.current_page = 1
        # Ricarica con filtri resettati (o tutti i log recenti)
        self._fetch_and_display_logs()

    def _fetch_and_display_logs(self, page_number: int = 1):
        self.log_table.setRowCount(0)
        self.details_before_text.clear()
        self.details_after_text.clear()

        if not self.db_manager or not self.db_manager.pool:
            logging.getLogger("CatastoGUI").warning(
                "AuditLogViewer: _fetch_and_display_logs chiamato ma il pool non è inizializzato. Interruzione.")
            # Opzionale: aggiorna la tabella con un messaggio
            self.log_table.setRowCount(1)
            item_msg = QTableWidgetItem("Database non pronto.")
            item_msg.setTextAlignment(Qt.AlignCenter)
            self.log_table.setItem(0, 0, item_msg)
            self.log_table.setSpan(0, 0, 1, self.log_table.columnCount())
            return

        try:
            filters_for_db = getattr(self, 'current_filters', {})
            if not filters_for_db:
                filters_for_db = {
                    "start_datetime": QDateTime.currentDateTime().addDays(-7).toPyDateTime(),
                    "end_datetime": QDateTime.currentDateTime().toPyDateTime()
                }

            logs, total_records = self.db_manager.get_audit_logs(  # Questa chiamata può sollevare DBMError
                filters=filters_for_db,
                page=page_number,
                page_size=100
            )

            if logs:
                self.log_table.setRowCount(len(logs))
                for row_idx, log_entry in enumerate(logs):
                    col = 0
                    # ID Log
                    item_id = QTableWidgetItem(str(log_entry.get('id', '')))
                    # Salva l'intero dict del log nell'item
                    item_id.setData(Qt.UserRole, log_entry)
                    self.log_table.setItem(row_idx, col, item_id)
                    col += 1
                    # Timestamp
                    ts = log_entry.get('timestamp')
                    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "N/D"
                    self.log_table.setItem(
                        row_idx, col, QTableWidgetItem(ts_str))
                    col += 1
                    # ID Utente App
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(
                        str(log_entry.get('app_user_id', 'N/D'))))
                    col += 1
                    # ID Sessione (troncato per brevità)
                    session_id_full = log_entry.get('session_id', 'N/D')
                    session_id_display = (session_id_full[:8] + '...') if session_id_full and len(
                        session_id_full) > 8 else session_id_full
                    self.log_table.setItem(
                        row_idx, col, QTableWidgetItem(session_id_display))
                    col += 1
                    # Tabella
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(
                        log_entry.get('tabella', 'N/D')))
                    col += 1
                    # Operazione
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(
                        log_entry.get('operazione', 'N/D')))
                    col += 1
                    # ID Record
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(
                        str(log_entry.get('record_id', 'N/D'))))
                    col += 1
                    # Indirizzo IP
                    self.log_table.setItem(row_idx, col, QTableWidgetItem(
                        log_entry.get('ip_address', 'N/D')))
                    col += 1
                    # Modifiche? (semplice indicatore se dati_prima o dati_dopo esistono)
                    has_changes = "Sì" if log_entry.get(
                        'dati_prima') or log_entry.get('dati_dopo') else "No"
                    self.log_table.setItem(
                        row_idx, col, QTableWidgetItem(has_changes))
                    col += 1

                self.log_table.resizeColumnsToContents()  # Adatta larghezza colonne
                # TODO: Aggiorna self.pagination_label
            else:
                # TODO: Aggiorna self.pagination_label con "Nessun risultato"
                pass  # Nessun log trovato

        except DBMError as e:  # Cattura specificamente DBMError se _get_connection fallisce
            logging.getLogger("CatastoGUI").error(
                f"AuditLogViewer: Errore DBManager in _fetch_and_display_logs: {str(e)}", exc_info=False)
            if hasattr(self, 'log_table'):
                self.log_table.setRowCount(1)
                item_msg = QTableWidgetItem(
                    f"Errore caricamento log: {str(e)}")
                item_msg.setTextAlignment(Qt.AlignCenter)
                self.log_table.setItem(0, 0, item_msg)
                self.log_table.setSpan(0, 0, 1, self.log_table.columnCount())
        except Exception as e:
            logging.getLogger("CatastoGUI").error(
                f"AuditLogViewer: Errore generico in _fetch_and_display_logs: {e}", exc_info=True)
            # ... (gestione errore generico) ...

    def _display_log_details(self):
        selected_items = self.log_table.selectedItems()
        if not selected_items:
            self.details_before_text.clear()
            self.details_after_text.clear()
            return

        # Prendiamo l'intero record del log memorizzato nel primo item della riga
        first_item_selected_row = self.log_table.item(
            selected_items[0].row(), 0)
        if not first_item_selected_row:
            return

        log_entry_data = first_item_selected_row.data(
            Qt.UserRole)  # Recupera il dict del log
        if not log_entry_data or not isinstance(log_entry_data, dict):
            self.details_before_text.setText(
                "Dati del log non disponibili o corrotti.")
            self.details_after_text.clear()
            return

        dati_prima = log_entry_data.get('dati_prima')
        dati_dopo = log_entry_data.get('dati_dopo')

        self.details_before_text.setText(json.dumps(
            dati_prima, indent=4, ensure_ascii=False) if dati_prima else "Nessun dato precedente.")
        self.details_after_text.setText(json.dumps(
            dati_dopo, indent=4, ensure_ascii=False) if dati_dopo else "Nessun dato successivo.")

    def _load_initial_data(self):
        if not self.db_manager or not self.db_manager.pool:  # Questo controllo è cruciale
            logging.getLogger("CatastoGUI").warning(
                "AuditLogViewer: Database principale non configurato o pool non inizializzato. Log non caricati.")
            if hasattr(self, 'log_table'):
                self.log_table.setRowCount(1)
                item_msg = QTableWidgetItem(
                    "Database non pronto per caricare i log di audit.")
                item_msg.setTextAlignment(Qt.AlignCenter)
                self.log_table.setItem(0, 0, item_msg)
                self.log_table.setSpan(0, 0, 1, self.log_table.columnCount())
            return  # <--- DEVE ESSERE QUI PER FERMARE L'ESECUZIONE

        # Queste righe vengono eseguite SOLO SE il pool è OK
        logging.getLogger("CatastoGUI").info(
            "AuditLogViewer: Pool inizializzato, procedo con il caricamento dei log iniziali.")
        self.current_filters = {
            "start_datetime": QDateTime.currentDateTime().addDays(-1).toPyDateTime(),
            "end_datetime": QDateTime.currentDateTime().toPyDateTime()
        }
        self.current_page = 1
        self._fetch_and_display_logs()  # Ora questo verrà chiamato solo se il pool è attivo

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

class AdminDBOperationsWidget(QWidget):
    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_process: Optional[QProcess] = None
        self.script_base_path = os.path.join(
            os.path.dirname(__file__), "sql_scripts")

        self._initUI()
        self._update_admin_buttons_state()  # Nuovo metodo per aggiornare stato pulsanti

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # --- 0. Sezione Creazione Database (Solo se il DB non esiste) ---
        # Questo pulsante sarà abilitato/disabilitato in base allo stato del pool
        create_db_group = QGroupBox(
            "0. Creazione Database Principale ('catasto_storico')")
        create_db_layout = QVBoxLayout(create_db_group)
        self.btn_run_create_database = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_CommandLink), " Crea Database 'catasto_storico'")
        self.btn_run_create_database.setToolTip(
            "Esegue lo script '01_creazione-database.sql' per creare il database principale.\nRichiede credenziali utente PostgreSQL con privilegi di creazione database.")
        self.btn_run_create_database.clicked.connect(
            self._run_script_crea_database)
        create_db_layout.addWidget(self.btn_run_create_database)
        create_db_layout.addWidget(
            QLabel("<i>Eseguire solo se il database 'catasto_storico' non esiste.</i>"))
        main_layout.addWidget(create_db_group)

        # --- 1. Sezione Configurazione Iniziale ---
        config_group = QGroupBox(
            "1. Setup Struttura Database (Tabelle, Funzioni, ecc.)")
        config_layout = QVBoxLayout(config_group)
        self.btn_run_initial_setup = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_MediaPlay), " Esegui Script Configurazione Struttura")
        self.btn_run_initial_setup.setToolTip(
            "Esegue script SQL per creare tabelle, viste, funzioni, ecc. (dopo creazione DB)")
        self.btn_run_initial_setup.clicked.connect(
            self._run_all_config_scripts)
        config_layout.addWidget(self.btn_run_initial_setup)
        config_layout.addWidget(QLabel(
            "<i>Eseguire dopo che il database 'catasto_storico' è stato creato e il pool è attivo.</i>"))
        main_layout.addWidget(config_group)

        # --- 2. Sezione Carico Dati SQL ---
        load_sql_group = QGroupBox(
            "2. Caricamento Dati di Esempio (Script SQL)")
        load_sql_layout = QVBoxLayout(load_sql_group)
        self.btn_run_sql_data_load = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_ArrowUp), " Esegui Script Caricamento Dati SQL")
        self.btn_run_sql_data_load.setToolTip(
            "Esegue lo script SQL ('04_dati_stress_test.sql') per popolare il DB.")
        self.btn_run_sql_data_load.clicked.connect(
            self._run_sql_data_load_script)
        load_sql_layout.addWidget(self.btn_run_sql_data_load)
        main_layout.addWidget(load_sql_group)

        # --- 3. Sezione Popolamento Dati Python ---
        populate_py_group = QGroupBox("3. Popolamento Dati Guidato (Python)")
        populate_py_layout = QVBoxLayout(populate_py_group)
        self.btn_run_python_populate = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_ArrowRight), " Esegui Popolamento Dati Python")
        self.btn_run_python_populate.setToolTip(
            "Genera e inserisce dati di esempio usando la logica Python dell'applicazione.")
        self.btn_run_python_populate.clicked.connect(
            self._run_python_data_population)
        populate_py_layout.addWidget(self.btn_run_python_populate)
        main_layout.addWidget(populate_py_group)

        # --- 4. Sezione Cancellazione DB ---
        delete_db_group = QGroupBox("Operazioni Distruttive")
        delete_db_layout = QVBoxLayout(delete_db_group)
        self.btn_run_db_wipe = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_TrashIcon), " Esegui Script Cancellazione Database")
        self.btn_run_db_wipe.setStyleSheet(
            "QPushButton { background-color: #d9534f; border-color: #d43f3a; color: white; } QPushButton:hover { background-color: #c9302c; } QPushButton:pressed { background-color: #ac2925; }")
        self.btn_run_db_wipe.setToolTip(
            "ATTENZIONE: Esegue lo script 'drop_db.sql' per cancellare il database specificato.")
        self.btn_run_db_wipe.clicked.connect(self._run_db_deletion_script)
        delete_db_layout.addWidget(self.btn_run_db_wipe)
        delete_db_layout.addWidget(QLabel(
            "<font color='red'><b>ATTENZIONE MASSIMA: Operazioni altamente distruttive. Richiederanno multiple conferme.</b></font>"))
        main_layout.addWidget(delete_db_group)

        self.output_log = QTextEdit()  # Definisci l'attributo qui
        self.output_log.setReadOnly(True)
        self.output_log.setLineWrapMode(QTextEdit.NoWrap)
        self.output_log.setFixedHeight(200)
        main_layout.addWidget(QLabel("Log Operazioni Amministrazione DB:"))
        main_layout.addWidget(self.output_log, 1)
        main_layout.addStretch(1)
        self.setLayout(main_layout)

    def _log_output(self, message: str, error: bool = False):
        """Aggiunge un messaggio al QTextEdit self.output_log con timestamp."""
        if not hasattr(self, 'output_log'):  # Controllo di sicurezza
            print(f"FALLBACK LOG (output_log non trovato): {message}")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message.strip()}"
        if error:
            self.output_log.append(
                f"<font color='red'>{formatted_message}</font>")
        else:
            self.output_log.append(formatted_message)
        # Per forzare l'aggiornamento della UI durante operazioni lunghe
        QApplication.processEvents()

    def _disable_all_buttons(self, disable: bool):
        """Abilita o disabilita tutti i pulsanti principali di operazione del widget."""
        self.btn_run_create_database.setEnabled(not disable)
        self.btn_run_initial_setup.setEnabled(not disable)
        self.btn_run_sql_data_load.setEnabled(not disable)
        self.btn_run_python_populate.setEnabled(not disable)
        self.btn_run_db_wipe.setEnabled(not disable)
        # Se ci sono altri pulsanti da gestire, aggiungili qui.
        # Lo stato finale dei pulsanti verrà poi ridefinito da _update_admin_buttons_state
        # quando l'operazione è finita, ma questo serve per il blocco durante l'operazione.

    def _update_admin_buttons_state(self):
        """Abilita/disabilita i pulsanti in base allo stato del pool del DB principale."""
        pool_is_active = self.db_manager and self.db_manager.pool is not None

        # Il pulsante "Crea Database" è abilitato se il pool NON è attivo (implica che il DB potrebbe non esistere)
        self.btn_run_create_database.setEnabled(not pool_is_active)

        # Gli altri pulsanti di configurazione/popolamento sono abilitati SOLO SE il pool è attivo
        self.btn_run_initial_setup.setEnabled(pool_is_active)
        self.btn_run_sql_data_load.setEnabled(pool_is_active)
        self.btn_run_python_populate.setEnabled(pool_is_active)

        # Il pulsante di cancellazione è sempre abilitato (con le sue conferme),
        # ma la sua logica gestirà lo stato del pool (lo chiuderà se attivo).
        self.btn_run_db_wipe.setEnabled(True)

    def _run_script_crea_database(self):
        self.output_log.clear()
        # Lo script che contiene "CREATE DATABASE catasto_storico;"
        script_name = "01_creazione-database.sql"
        script_path = os.path.join(self.script_base_path, script_name)

        if not os.path.exists(script_path):
            QMessageBox.critical(
                self, "Script Mancante", f"Lo script di creazione database '{script_name}' non è stato trovato in:\n{script_path}")
            self._log_output(
                f"ERRORE: Script '{script_name}' non trovato.", error=True)
            return

        # Dovrebbe essere "catasto_storico"
        target_dbname = self.db_manager.get_current_dbname()
        if not target_dbname:
            QMessageBox.critical(self, "Errore Configurazione",
                                 "Nome del database target non definito nel DBManager.")
            return

        reply = QMessageBox.question(self, "Conferma Creazione Database",
                                     f"Stai per eseguire lo script '{script_name}' per creare il database '{target_dbname}'.\n"
                                     "Questa operazione fallirà se il database esiste già (lo script dovrebbe gestire `IF NOT EXISTS` se possibile, o psql lo farà).\n"
                                     "Procedere?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            self._log_output("Creazione database annullata dall'utente.")
            return

        # Disabilita pulsanti durante l'operazione
        self._disable_all_buttons(True)
        # Per CREATE DATABASE, ci si connette a 'postgres'
        self._execute_sql_script_list_via_psql(
            script_names=[script_name],
            operation_name=f"Creazione Database '{target_dbname}'",
            dbname_override="postgres"
        )
        # _execute_sql_script_list_via_psql ora chiama _handle_script_finished che riabilita i pulsanti

        # Dopo questo, tentare di inizializzare il pool principale
        self._log_output(
            "Tentativo di inizializzazione del pool per il database principale...")
        QApplication.processEvents()
        if self.db_manager.initialize_main_pool():
            self._log_output(
                "Pool per il database principale ('{target_dbname}') inizializzato con successo!", error=False)
            QMessageBox.information(
                self, "Successo", f"Database '{target_dbname}' creato (o già esistente) e pool inizializzato.\nPuoi procedere con la configurazione delle tabelle e delle funzioni.")
            # Aggiorna la status bar nella finestra principale
            main_window = self.window().window()  # Trova la CatastoMainWindow
            if isinstance(main_window, QMainWindow) and hasattr(main_window, 'db_status_label'):
                main_window.db_status_label.setText(
                    f"Database: Connesso ({target_dbname})")
            self._update_admin_buttons_state()  # Aggiorna stato pulsanti
        else:
            self._log_output(
                f"FALLITO inizializzazione pool per il database '{target_dbname}' dopo tentativo di creazione.", error=True)
            QMessageBox.critical(
                self, "Errore Pool", f"Database '{target_dbname}' potrebbe essere stato creato, ma è fallita l'inizializzazione del pool di connessione. Controllare i log.")
            self._update_admin_buttons_state()  # Aggiorna stato pulsanti

    def _run_all_config_scripts(self):
        if not self.db_manager.pool:  # Controllo cruciale
            QMessageBox.warning(self, "Database Non Pronto",
                                "Il database principale non è ancora stato creato/connesso o il pool non è inizializzato.\n"
                                "Eseguire prima 'Crea Database' se necessario.")
            return

        config_scripts = [  # Script da 02 in poi
            "02_creazione-schema-tabelle.sql", "03_funzioni-procedure.sql",
            "07_user-management.sql", "19_creazione_tabella_sessioni.sql",
            "18_funzioni_trigger_audit.sql",
            "08_advanced-reporting.sql","09_backup-system.sql",
            "10_performance-optimization.sql","11_advanced-cadastral-features.sql",
            "12_procedure_crud.sql","13_workflow_integrati.sql",
            "14_report_functions.sql", "16_advanced_search.sql",
            "17_funzione_ricerca_immobili.sql", "15_integration_audit_users.sql",
            "05_query-test.sql"
            
        ]
        reply = QMessageBox.question(self, "Conferma Configurazione Struttura",
                                     "Stai per eseguire gli script per definire tabelle, funzioni, viste, ecc. nel database.\n"
                                     "Assicurati che il database sia vuoto o che gli script siano rieseguibili.\n"
                                     "Procedere?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Questi script verranno eseguiti sul database target (catasto_storico)
            # quindi dbname_override non è necessario (userà il dbname del pool)
            self._execute_sql_script_list_via_psql(
                config_scripts, "Configurazione Struttura Database")

    def _run_sql_data_load_script(self):
        if not self.db_manager.pool:
            QMessageBox.warning(self, "Database Non Pronto",
                                "Il pool principale non è attivo. Eseguire prima la creazione/configurazione del DB.")
            return

        data_load_scripts = ["04_dati_stress_test.sql"]
        reply = QMessageBox.question(self, "Conferma Caricamento Dati SQL",
                                     f"Stai per eseguire lo script '{data_load_scripts[0]}'.\nProcedere?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._execute_sql_script_list_via_psql(
                data_load_scripts, "Caricamento Dati da SQL")

    def _execute_sql_script_list_via_psql(self, script_names: List[str], operation_name: str, dbname_override: Optional[str] = None):
        """
        Esegue una lista di script SQL sequenzialmente usando psql.
        dbname_override: se specificato, psql si connetterà a questo database (es. "postgres" per CREATE/DROP DATABASE).
                         Altrimenti, usa il database principale configurato nel db_manager.
        """
        self._disable_all_buttons(
            True)  # Disabilita i pulsanti durante l'intera sequenza
        self.output_log.clear()
        self._log_output(f"Avvio operazione: {operation_name}...")

        if not self.db_manager:  # Non dovrebbe accadere se la UI è ben gestita
            self._log_output(
                "ERRORE CRITICO: DB Manager non disponibile.", error=True)
            self._disable_all_buttons(False)
            self._update_admin_buttons_state()
            return

        # Recupera dettagli connessione
        conn_params = self.db_manager.get_connection_parameters()  # Chiamata corretta
        db_user_main = conn_params.get(
            "user", "postgres")  # Utente del DB principale
        db_host = conn_params.get("host", "localhost")
        db_port = str(conn_params.get("port", "5432"))

        # Determina il database target e l'utente per l'autenticazione
        # Per CREATE/DROP DATABASE, ci connettiamo a 'postgres' con le credenziali fornite
        # Per altri script, ci connettiamo al DB target con le credenziali fornite

        target_db_for_psql = dbname_override if dbname_override else self.db_manager.get_current_dbname()

        if not target_db_for_psql:
            QMessageBox.critical(self, "Errore Configurazione",
                                 f"Nome del database di destinazione per {operation_name} non specificato o non recuperabile.")
            self._log_output(
                f"ERRORE: Nome database non specificato per {operation_name}.", error=True)
            self._disable_all_buttons(False)
            self._update_admin_buttons_state()
            return

        # Chiedi la password per l'utente che eseguirà lo script (solitamente l'utente del DB principale o un superuser)
        # Se dbname_override è 'postgres', l'utente è probabilmente 'postgres' o un altro superuser.
        # Se dbname_override è None, l'utente è quello del DB principale.
        utente_per_connessione_psql = db_user_main
        if dbname_override and dbname_override.lower() == "postgres" and db_user_main.lower() != "postgres":
            # Se si sta creando/droppando un DB e l'utente di default non è 'postgres',
            # si potrebbe voler chiedere esplicitamente le credenziali di 'postgres' o di un superuser.
            # Per ora, usiamo l'utente principale, assumendo abbia i privilegi necessari sul DB di manutenzione.
            risposta = QMessageBox.question(self, "Conferma Utente",
                                            f"L'operazione '{operation_name}' sarà eseguita sul database '{target_db_for_psql}' "
                                            f"utilizzando l'utente '{db_user_main}'. Questo utente ha i privilegi necessari?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if risposta == QMessageBox.No:
                self._log_output(
                    f"{operation_name} annullato: utente '{db_user_main}' potrebbe non avere privilegi sufficienti.", error=True)
                self._disable_all_buttons(False)
                self._update_admin_buttons_state()
                return

        password, ok = QInputDialog.getText(self, f"Autenticazione DB per {operation_name}",
                                            f"Inserisci la password per l'utente '{utente_per_connessione_psql}' "
                                            f"per connettersi al database '{target_db_for_psql}' (su host {db_host}):",
                                            QLineEdit.Password)
        if not ok:
            self._log_output(
                f"{operation_name} annullato: dialogo password chiuso.")
            self._disable_all_buttons(False)
            self._update_admin_buttons_state()
            return
        # Per alcune operazioni (come DROP DB con psql), PGPASSWORD potrebbe non essere necessario se l'autenticazione è peer/trust
        # ma è meglio fornirla se richiesta. Se password è vuota, psql potrebbe chiederla interattivamente (non va bene per QProcess).
        # La cancellazione su 'postgres' potrebbe non aver bisogno di password utente
        if not password.strip() and operation_name not in ["Cancellazione Database"]:
            QMessageBox.warning(
                self, "Password Mancante", "La password non può essere vuota per questa operazione.")
            self._log_output(
                f"{operation_name} fallito: password non fornita.", error=True)
            self._disable_all_buttons(False)
            self._update_admin_buttons_state()
            return

        psql_exe = self.db_manager._resolve_executable_path(
            user_provided_path="", default_name="psql.exe")
        if not psql_exe:
            QMessageBox.critical(self, "Errore Prerequisito",
                                 "L'eseguibile 'psql.exe' non è stato trovato. Specificare il percorso nelle impostazioni dell'applicazione (se disponibili) o assicurarsi che sia nel PATH di sistema.")
            self._log_output("ERRORE: psql.exe non trovato.", error=True)
            self._disable_all_buttons(False)
            self._update_admin_buttons_state()
            return

        all_scripts_successful = True
        for script_name in script_names:
            script_path = os.path.join(self.script_base_path, script_name)
            if not os.path.exists(script_path):
                self._log_output(
                    f"ERRORE: Script '{script_name}' non trovato in {script_path}", error=True)
                all_scripts_successful = False
                break

            # Nuova istanza di QProcess per ogni script
            self.current_process = QProcess(self)
            # Collega i segnali per catturare output
            # Usiamo lambda per passare script_name al gestore di output/errore
            self.current_process.readyReadStandardOutput.connect(
                lambda sp=script_name: self._log_output(f"[{sp}] STDOUT: {self.current_process.readAllStandardOutput().data().decode(sys.stdout.encoding or 'utf-8', errors='replace')}"))
            self.current_process.readyReadStandardError.connect(
                lambda sp=script_name: self._log_output(f"[{sp}] STDERR: {self.current_process.readAllStandardError().data().decode(sys.stderr.encoding or 'utf-8', errors='replace')}", error=True))

            args = ["-U", utente_per_connessione_psql, "-h", db_host, "-p", db_port,
                    "-d", target_db_for_psql, "-f", script_path, "-v", "ON_ERROR_STOP=1"]

            process_env = self.current_process.processEnvironment()
            if password.strip():  # Solo se la password è stata fornita
                process_env.insert("PGPASSWORD", password)
            self.current_process.setProcessEnvironment(process_env)

            self._log_output(
                f"Esecuzione script: '{script_name}' sul database '{target_db_for_psql}'...")
            # Mostra il comando
            self._log_output(f"Comando: {psql_exe} {' '.join(args)}")
            QApplication.processEvents()

            self.current_process.start(psql_exe, args)

            # Attendi indefinitamente
            if not self.current_process.waitForFinished(-1):
                err_msg = f"Timeout o errore nell'attesa del completamento dello script '{script_name}'."
                self._log_output(err_msg, error=True)
                QMessageBox.critical(self, "Errore Esecuzione Script", err_msg)
                self.current_process.kill()
                all_scripts_successful = False
                break

            exit_code = self.current_process.exitCode()
            exit_status = self.current_process.exitStatus()
            QApplication.processEvents()  # Per assicurare che tutto l'output sia catturato

            if exit_status == QProcess.CrashExit or exit_code != 0:
                msg = f"FALLITO: Script '{script_name}' terminato con errore (Codice: {exit_code}, Stato Qt: {exit_status}). Operazione '{operation_name}' interrotta."
                self._log_output(msg, error=True)
                # Non mostriamo QMessageBox qui, sarà fatto alla fine dal chiamante o da _handle_script_finished_summary
                all_scripts_successful = False
                break
            else:
                self._log_output(
                    f"SUCCESSO (comando terminato): Script '{script_name}' completato con codice 0.")

            self.current_process = None  # Rilascia riferimento per il prossimo script

        self._handle_script_finished_summary(
            all_scripts_successful, operation_name)

    def _handle_script_finished_summary(self, all_successful: bool, operation_name: str):
        """Chiamato dopo che tutti gli script in una lista sono stati processati (o uno è fallito)."""
        self._log_output(f"<hr>Operazione '{operation_name}' completata.")
        if all_successful:
            QMessageBox.information(self, "Operazione Completata",
                                    f"L'operazione '{operation_name}' sembra essere stata completata con successo.\n"
                                    "Controllare il log per dettagli e possibili errori specifici degli script SQL.")
        else:
            QMessageBox.warning(self, "Operazione Interrotta o Fallita",
                                f"L'operazione '{operation_name}' è stata interrotta o uno o più script sono falliti.\n"
                                "Controllare il log per i dettagli.")

        self._disable_all_buttons(False)
        # Aggiorna lo stato dei pulsanti in base al pool
        self._update_admin_buttons_state()

    # ... (resto dei metodi: _run_initial_setup_script, _run_sql_data_load_script,
    #      _run_python_data_population, _run_db_deletion_script) ...
    # Assicurati che questi metodi ora chiamino _execute_sql_script_list_via_psql
    # e che _run_db_deletion_script gestisca correttamente la chiusura del pool PRIMA
    # di chiamare _execute_sql_script_list_via_psql per lo script drop_db.sql.

    def _run_python_data_population(self):
        if not self.db_manager.pool:
            QMessageBox.warning(self, "Database Non Pronto",
                                "Il pool principale non è attivo. Eseguire prima la creazione/configurazione del DB.")
            return

        self.output_log.clear()
        self._log_output(
            "Avvio popolamento dati di esempio guidato da Python...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._disable_all_buttons(True)

        try:
            num_comuni_creati = 0
            num_comuni_da_creare, ok = QInputDialog.getInt(
                self, "Popolamento Python", "Quanti comuni di esempio vuoi creare?", 2, 1, 10, 1)
            if not ok:
                self._log_output("Popolamento annullato.", error=True)
            else:
                for i in range(num_comuni_da_creare):
                    nome_comune_esempio = f"Comune Python Demo {i+1}"
                    prov_esempio = f"P{i % 5+1}"
                    reg_esempio = "Regione Demo Python"
                    # O prendilo da self.main_window.logged_in_user_info se disponibile
                    utente_attuale_per_log = "admin_setup"

                    try:
                        # Usa il metodo del DBManager che ora usa il pool
                        comune_id = self.db_manager.aggiungi_comune(
                            nome_comune=nome_comune_esempio, provincia=prov_esempio, regione=reg_esempio,
                            periodo_id=1,  # Assumendo che il periodo ID 1 esista dopo il setup
                            utente=utente_attuale_per_log
                        )
                        if comune_id:
                            self._log_output(
                                f"Creato Comune: '{nome_comune_esempio}' (ID: {comune_id})")
                            num_comuni_creati += 1
                        # else: aggiungi_comune solleverà eccezione in caso di fallimento
                    except (DBMError, DBUniqueConstraintError, DBDataError) as e_comune:
                        self._log_output(
                            f"Fallita creazione Comune '{nome_comune_esempio}': {e_comune}", error=True)
                    QApplication.processEvents()

                message = f"Popolamento Python completato.\nComuni creati: {num_comuni_creati}"
                self._log_output(message)
                QMessageBox.information(
                    self, "Popolamento Completato", message)

        except Exception as e:  # Cattura qualsiasi altra eccezione
            self._log_output(
                f"ERRORE imprevisto durante il popolamento Python: {e}", error=True)
            logging.getLogger("CatastoGUI").critical(
                "Errore imprevisto popolamento Python", exc_info=True)
            QMessageBox.critical(
                self, "Errore Popolamento Imprevisto", f"Errore: {e}")
        finally:
            self._disable_all_buttons(False)
            QApplication.restoreOverrideCursor()
            # Ri-abilita i pulsanti in base allo stato del pool
            self._update_admin_buttons_state()

    def _run_db_deletion_script(self):
        # ... (logica di conferma e chiamata a _execute_sql_script_list_via_psql
        #      con dbname_override="postgres" e gestione chiusura pool come definito prima) ...
        script_name = "drop_db.sql"
        script_path = os.path.join(self.script_base_path, script_name)
        if not os.path.exists(script_path):
            QMessageBox.critical(self, "Script Mancante",
                                 f"Script '{script_name}' non trovato.")
            return

        dbname_corrente = self.db_manager.get_current_dbname()
        if not dbname_corrente:
            QMessageBox.critical(
                self, "Errore", "Nome DB target non recuperabile.")
            return

        reply1 = QMessageBox.critical(self, "ATTENZIONE MASSIMA - CANCELLAZIONE!",
                                      f"Stai per eseguire '{script_name}' che tenterà di CANCELLARE il database '{dbname_corrente}'.\n"
                                      "<b>OPERAZIONE IRREVERSIBILE. PERDITA DI TUTTI I DATI.</b>\n"
                                      "Procedere?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply1 == QMessageBox.No:
            self._log_output("Cancellazione DB annullata.")
            return

        testo_conferma, ok = QInputDialog.getText(self, "Conferma Finale Cancellazione",
                                                  f"Per confermare la cancellazione di '{dbname_corrente}', digita il suo nome ESATTO:")
        if not ok:
            self._log_output("Cancellazione DB annullata.")
            return
        if testo_conferma.strip() != dbname_corrente:
            QMessageBox.critical(self, "Conferma Fallita",
                                 "Nome DB non corrispondente. Annullato.")
            self._log_output(
                "Cancellazione DB annullata: nome conferma errato.", error=True)
            return

        self._disable_all_buttons(True)  # Disabilita pulsanti
        # Importante: chiudere il pool PRIMA di tentare il drop del database a cui potrebbe essere connesso
        if self.db_manager.pool:
            self._log_output(
                f"Chiusura del pool di connessioni per '{dbname_corrente}' prima della cancellazione...")
            self.db_manager.close_pool()  # Ora db_manager.pool è None
            self._log_output("Pool principale chiuso.")

        self._execute_sql_script_list_via_psql(
            script_names=[script_name],
            operation_name=f"Cancellazione Database '{dbname_corrente}'",
            dbname_override="postgres"
        )
        # _execute_sql_script_list_via_psql chiamerà _handle_script_finished che riabiliterà i pulsanti
        # e aggiornerà lo stato
        self._log_output(
            f"ATTENZIONE: Database '{dbname_corrente}' dovrebbe essere stato cancellato. L'applicazione potrebbe necessitare di riavvio.", error=True)
        # Aggiorna stato pulsanti (Crea DB dovrebbe essere abilitato ora)
        self._update_admin_buttons_state()
        # Aggiorna status bar nella finestra principale per riflettere che il DB non esiste più
        main_window = self.window().window()  # Trova la CatastoMainWindow
        if isinstance(main_window, QMainWindow) and hasattr(main_window, 'db_status_label'):
            main_window.db_status_label.setText(
                f"Database: NON ESISTENTE ({dbname_corrente})")
        if isinstance(main_window, QMainWindow) and hasattr(main_window, 'update_ui_based_on_role'):
            # Simula uno stato di admin_offline per riflettere la UI
            main_window.pool_initialized_successfully = False  # Fondamentale
            main_window.logged_in_user_info = {
                'ruolo': 'admin_offline'}  # Forza la modalità limitata
            main_window.update_ui_based_on_role()

    def _handle_script_finished(self, exit_code, exit_status, operation_name: str):
        self.output_log.append(
            f"<hr>DEBUG Processo '{operation_name}' terminato. ExitCode: {exit_code}, ExitStatus: {exit_status}<hr>")
        success_message_box_needed = False
        if exit_status == QProcess.CrashExit:
            msg = f"ERRORE CRITICO: Processo {operation_name} terminato inaspettatamente (crash)."
            self._log_output(msg, error=True)
            QMessageBox.critical(self, "Errore Processo", msg)
        elif exit_code != 0:
            msg = f"FALLITO: Processo {operation_name} terminato con codice d'errore: {exit_code}. Controllare output."
            self._log_output(msg, error=True)
            QMessageBox.warning(self, "Operazione Fallita", msg)
        else:
            msg = f"SUCCESSO (comando terminato): Processo {operation_name} completato con codice 0. Verificare l'output per errori specifici dello script SQL."
            self._log_output(msg)
            success_message_box_needed = True

        # Se l'operazione era CANCELLAZIONE DB e ha avuto successo (exit_code 0)
        # il pool principale è già stato chiuso in _run_db_deletion_script PRIMA di chiamare psql.
        # Se era CREAZIONE DB e ha avuto successo, tentiamo di inizializzare il pool principale.
        # (Questo è già gestito in _run_script_crea_database dopo la chiamata a _execute_sql_script_list_via_psql)

        if success_message_box_needed and operation_name != f"Creazione Database '{self.db_manager.get_current_dbname()}'" and operation_name != f"Cancellazione Database '{self.db_manager.get_current_dbname()}'":
            QMessageBox.information(self, "Operazione Completata", msg)

        self._disable_all_buttons(False)  # Riabilita sempre i pulsanti
        self._update_admin_buttons_state()  # Aggiorna lo stato in base al pool
        self.current_process = None  # Resetta riferimento al processo

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

class LandingPageWidget(QWidget):
    # Definisci TUTTI i segnali che vengono emessi da questa pagina
    apri_elenco_comuni_signal = pyqtSignal()
    apri_ricerca_partite_signal = pyqtSignal()
    apri_ricerca_possessori_signal = pyqtSignal()
    apri_registra_proprieta_signal = pyqtSignal()
    apri_registra_possessore_signal = pyqtSignal()
    apri_registra_consultazione_signal = pyqtSignal()
    apri_report_proprieta_signal = pyqtSignal() # Questo era mancante
    apri_report_genealogico_signal = pyqtSignal()    # Questo era mancante

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop) # Allinea il contenuto in alto
        main_layout.setSpacing(20) # Spazio tra le sezioni
         # --- INIZIO INTEGRAZIONE LOGO DA FILE ESTERNO ---

        # 1. Determina il percorso del file SVG.
        #    Assumiamo che gui_widgets.py sia nella cartella principale del progetto
        #    e il logo sia in una sottocartella 'resources'.

        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Percorso al file dell'immagine (PNG o JPG)
            logo_path = os.path.join(base_dir, "resources", "logo_meridiana.png") # Assicurati che questo percorso sia corretto e il file esista

            self.logo_widget = QLabel() # Inizializza come QLabel
            
            if os.path.exists(logo_path):
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    # Definire le nuove dimensioni desiderate per il logo (es. 250x250 o 300x300)
                    # Ho aumentato da 150 a 250. Puoi sperimentare con valori maggiori.
                    new_width = 250
                    new_height = 140

                    # Scala l'immagine per adattarla alle dimensioni desiderate
                    # Qt.KeepAspectRatio: mantiene le proporzioni per evitare distorsioni.
                    # Qt.SmoothTransformation: usa un algoritmo di scalatura di alta qualità.
                    scaled_pixmap = pixmap.scaled(new_width, new_height,
                                                  Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.logo_widget.setPixmap(scaled_pixmap)
                    self.logo_widget.setAlignment(Qt.AlignCenter) # Centra l'immagine all'interno della QLabel
                else:
                    self.logger.error(f"Impossibile caricare QPixmap dal file: {logo_path}. Il file potrebbe essere corrotto o non un'immagine valida.")
                    self.logo_widget.setText("Errore caricamento immagine")
                    self.logo_widget.setAlignment(Qt.AlignCenter)
                    self.logo_widget.setStyleSheet("QLabel { color: red; font-weight: bold; }")
            else:
                self.logger.error(f"File logo immagine non trovato in:\n{logo_path}")
                self.logo_widget.setText("Logo non caricato")
                self.logo_widget.setAlignment(Qt.AlignCenter)
                self.logo_widget.setStyleSheet("QLabel { color: red; font-weight: bold; }")

        except Exception as e:
            self.logger.error(f"Eccezione durante il caricamento del logo (tentativo con QPixmap): {e}", exc_info=True)
            self.logo_widget = QLabel("Errore caricamento logo")
            self.logo_widget.setAlignment(Qt.AlignCenter)
            self.logo_widget.setStyleSheet("QLabel { color: red; }")

        # Imposta le dimensioni fisse del widget contenitore (QLabel)
        # Queste devono corrispondere o essere leggermente superiori alle dimensioni di scalatura del pixmap
        self.logo_widget.setFixedSize(new_width, new_height) # Usa le stesse dimensioni di scalatura


        # 3. Aggiungi il logo al layout (come prima)
        logo_container_layout = QHBoxLayout()
        logo_container_layout.addStretch()
        logo_container_layout.addWidget(self.logo_widget)
        logo_container_layout.addStretch()
        
        main_layout.addLayout(logo_container_layout)

        # --- FINE INTEGRAZIONE LOGO ---
        # Titolo di Benvenuto
        title_label = QLabel("Gestionale Catasto Storico")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        subtitle_label = QLabel("Archivio di Stato di Savona - Funzionalità Principali")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle_label)
        main_layout.addSpacing(10)

        # Layout a griglia per le sezioni di pulsanti
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        main_layout.addLayout(grid_layout)

        # Sezione Consultazione Rapida
        consultazione_group = QGroupBox("Consultazione Rapida")
        consultazione_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        consultazione_layout = QVBoxLayout(consultazione_group)
        consultazione_layout.setSpacing(10)

        btn_elenco_comuni = QPushButton("Principale")
        btn_elenco_comuni.clicked.connect(self.apri_elenco_comuni_signal.emit)
        consultazione_layout.addWidget(btn_elenco_comuni)

        btn_ricerca_partite = QPushButton("Ricerca Partite")
        btn_ricerca_partite.clicked.connect(self.apri_ricerca_partite_signal.emit)
        consultazione_layout.addWidget(btn_ricerca_partite)

        btn_ricerca_possessori = QPushButton("Ricerca Possessori")
        btn_ricerca_possessori.clicked.connect(self.apri_ricerca_possessori_signal.emit)
        consultazione_layout.addWidget(btn_ricerca_possessori)
        grid_layout.addWidget(consultazione_group, 0, 0)

        # Sezione Operazioni Comuni
        operazioni_group = QGroupBox("Operazioni Comuni")
        operazioni_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        operazioni_layout = QVBoxLayout(operazioni_group)
        operazioni_layout.setSpacing(10)

        btn_reg_proprieta = QPushButton("Registra Nuova Proprietà")
        btn_reg_proprieta.clicked.connect(self.apri_registra_proprieta_signal.emit)
        operazioni_layout.addWidget(btn_reg_proprieta)

        btn_reg_possessore = QPushButton("Registra Nuovo Possessore")
        btn_reg_possessore.clicked.connect(self.apri_registra_possessore_signal.emit)
        operazioni_layout.addWidget(btn_reg_possessore)
        
        btn_reg_consultazione = QPushButton("Registra Consultazione")
        btn_reg_consultazione.clicked.connect(self.apri_registra_consultazione_signal.emit)
        operazioni_layout.addWidget(btn_reg_consultazione)
        grid_layout.addWidget(operazioni_group, 0, 1)

        # Sezione Report Principali (assicurati che i pulsanti siano collegati ai segnali corretti)
        report_group = QGroupBox("Report Principali")
        report_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        report_layout = QVBoxLayout(report_group)
        report_layout.setSpacing(10)

        btn_cert_proprieta = QPushButton("Genera Report Proprietà")
        btn_cert_proprieta.clicked.connect(self.apri_report_proprieta_signal.emit) # <--- COLLEGAMENTO
        report_layout.addWidget(btn_cert_proprieta)

        btn_rep_genealogico = QPushButton("Genera Report Genealogico")
        btn_rep_genealogico.clicked.connect(self.apri_report_genealogico_signal.emit) # <--- COLLEGAMENTO
        report_layout.addWidget(btn_rep_genealogico)
        grid_layout.addWidget(report_group, 1, 0, 1, 2) # Span su due colonne

        main_layout.addStretch()
        self.setLayout(main_layout)

class WelcomeScreen(QDialog):
    def __init__(self, parent=None, logo_path: str = None, help_url: str = None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.setWindowTitle("Benvenuto - Catasto Storico")
        self.setModal(True)
        self.setFixedSize(1024, 768)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.logo_path = logo_path
        self.help_url = help_url

        self._init_ui()
        #self.start_timer()
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.setSpacing(30)

        # --- Sezione Logo (Modificata per Centratura) ---
        # Creiamo un QHBoxLayout per centrare orizzontalmente il logo
        logo_horizontal_layout = QHBoxLayout()
        logo_horizontal_layout.addStretch(1) # Spazio flessibile a sinistra per spingere al centro
        
        self.logo_label = QLabel()
        # Non è necessario self.logo_label.setAlignment(Qt.AlignCenter) se lo centriamo con QHBoxLayout e stretch
        # ma non fa male averlo.
        
        if self.logo_path and os.path.exists(self.logo_path):
            pixmap = QPixmap(self.logo_path)
            if not pixmap.isNull():
                max_logo_height = 400 
                max_logo_width = 700 
                
                scaled_pixmap = pixmap.scaled(max_logo_width, max_logo_height, 
                                              Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                self.logo_label.setPixmap(scaled_pixmap)
                self.logo_label.setFixedSize(scaled_pixmap.size()) # Imposta la dimensione del QLabel
                
                self.logger.info(f"Logo caricato e scalato a {scaled_pixmap.width()}x{scaled_pixmap.height()} nella Welcome Screen.")
            else:
                self.logger.warning(f"QPixmap vuoto per il logo in Welcome Screen: {self.logo_path}")
                self.logo_label.setText("Logo non caricato")
                self.logo_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
                self.logo_label.setFixedSize(300, 300) 
        else:
            self.logger.warning(f"Percorso logo non valido o file non trovato per Welcome Screen: {self.logo_path}")
            self.logo_label.setText("Logo non disponibile")
            self.logo_label.setStyleSheet("QLabel { color: gray; font-weight: bold; }")
            self.logo_label.setFixedSize(300, 300) 
            
        logo_horizontal_layout.addWidget(self.logo_label) # Aggiungi il QLabel al layout orizzontale
        logo_horizontal_layout.addStretch(1) # Spazio flessibile a destra per spingere al centro

        # Aggiungi il layout orizzontale del logo al layout verticale principale
        main_layout.addLayout(logo_horizontal_layout)
        # ... (resto del codice della _init_ui: titolo, sottotitolo, crediti, pulsante help) ...
        # Assicurati che lo spaziatore tra il logo e il testo non sia troppo grande
        # Sezioni Titolo App, Sottotitolo App, e Crediti e Pulsante Help.
        # Devono essere aggiunti al main_layout.

        title_label = QLabel("Gestionale Catasto Storico")
        title_font = QFont("Segoe UI", 24, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        subtitle_label = QLabel("Archivio di Stato di Savona")
        subtitle_font = QFont("Segoe UI", 16)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle_label)

        # Spazio flessibile tra il sottotitolo e i crediti
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Sezione Crediti
        credits_label = QLabel(
            "Sviluppato da: Marco Santoro\n"
            "Copyright © 2025 - Tutti i diritti riservati\n"
            "Concesso in comodato d'uso gratuito all'Archivio di Stato di Savona"
        )
        credits_font = QFont("Segoe UI", 10)
        credits_label.setFont(credits_font)
        credits_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(credits_label)

        # Sezione Link a Manuale/Help
        if self.help_url:
            help_button = QPushButton("Apri Manuale / Guida")
            help_button.setFont(QFont("Segoe UI", 12))
            help_button.setFixedSize(200, 40)
            help_button.clicked.connect(self._open_help_url)
            
            help_button_layout = QHBoxLayout()
            help_button_layout.addStretch()
            help_button_layout.addWidget(help_button)
            help_button_layout.addStretch()
            main_layout.addLayout(help_button_layout)
        else:
            self.logger.info("Nessun URL di aiuto fornito, il pulsante manuale non sarà visualizzato.")


        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)) # Spazio fisso in basso

        # Stile per il dialogo (opzionale)
        self.setStyleSheet("""
            WelcomeScreen {
                background-color: #f0f0f0;
                border: 2px solid #0078D4;
                border-radius: 10px;
            }
            QLabel {
                color: #333333;
            }
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
        """)
        self.setLayout(main_layout)

    def _open_help_url(self):
        if self.help_url:
            try:
                QDesktopServices.openUrl(QUrl(self.help_url))
                self.logger.info(f"Apertura URL di aiuto: {self.help_url}")
            except Exception as e:
                self.logger.error(f"Errore nell'apertura dell'URL: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore", f"Impossibile aprire il link al manuale: {e}")

    """
    def start_timer(self):
        # Il timer chiuderà la splash screen automaticamente dopo un certo tempo
        self.timer = QTimer(self)
        self.timer.setSingleShot(True) # Si attiva una sola volta
        self.timer.timeout.connect(self.accept) # Chiude il dialogo quando il timer scade
        self.timer.start(5000) # 3000 ms = 3 secondi. Adatta il tempo se necessario.
        self.logger.info("Timer per la Welcome Screen avviato (3 secondi).")
    """
    # --- NUOVO METODO: Gestisce il click del mouse ---
    def mousePressEvent(self, event):
        """
        Chiude la WelcomeScreen quando si verifica un click del mouse.
        """
        # Verifica che il click sia stato con il tasto sinistro del mouse
        if event.button() == Qt.LeftButton:
            self.logger.info("Welcome Screen chiusa tramite click del mouse.")
            self.accept() # Chiude il dialogo
        # Se vuoi gestire anche altri tasti (es. destro, centrale), puoi aggiungere altri if/elif
        # event.ignore() # Non è necessario chiamare ignore se l'evento è stato gestito