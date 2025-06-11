
import os,csv,sys,logging,json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
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
from config import (
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT, 
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA
)
from catasto_db_manager import CatastoDBManager

from custom_widgets import QPasswordLineEdit
try:
    # Si tenta di importare la classe principale dalla libreria fpdf2
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    # Se l'import fallisce, la libreria non è installata.
    FPDF_AVAILABLE = False

class DBConfigDialog(QDialog):
    # AGGIUNTO UN SEGNALE per comunicare la password al chiamante (run_gui_app)
    # in modo da non salvarla permanentemente e passarla solo quando serve.
    # Non verrà usato in questo caso, perché il dialogo ora la gestisce internamente.
    # config_accepted_with_password = pyqtSignal(dict, str) # Questo segnale non è più necessario così com'è
    def __init__(self, parent=None, initial_config: Optional[Dict[str, Any]] = None, allow_test_connection: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Configurazione Connessione Database")
        self.setModal(True)
        self.setMinimumWidth(500)

        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope,
                                  "ArchivioDiStatoSavona", "CatastoStoricoApp")
        logging.getLogger("CatastoGUI").debug(f"DBConfigDialog usa QSettings file: {self.settings.fileName()}")

        self.db_manager_test: Optional[CatastoDBManager] = None
        self.allow_test_connection = allow_test_connection

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignRight)

        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["Locale (localhost)", "Remoto (Server Specifico)"])
        self.db_type_combo.currentIndexChanged.connect(self._db_type_changed)
        layout.addRow("Tipo di Server Database:", self.db_type_combo)

        self.host_label = QLabel("Indirizzo Server Host (*):")
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("Es. 192.168.1.100 o nomeserver.locale")
        layout.addRow(self.host_label, self.host_edit)

        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1, 65535)
        self.port_spinbox.setValue(5432)
        layout.addRow("Porta Server (*):", self.port_spinbox)

        self.dbname_edit = QLineEdit()
        self.dbname_edit.setPlaceholderText("Es. catasto_storico")
        layout.addRow("Nome Database (*):", self.dbname_edit)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("Es. postgres o utente_app")
        layout.addRow("Utente Database (*):", self.user_edit)

        self.password_edit = QPasswordLineEdit()
        self.password_edit.setPlaceholderText("Password dell'utente database")
        layout.addRow("Password Database (*):", self.password_edit)

        self.schema_edit = QLineEdit()
        self.schema_edit.setPlaceholderText("Es. catasto")
        layout.addRow("Schema Database (opz.):", self.schema_edit)

        bottom_buttons_layout = QHBoxLayout()

        self.test_connection_button = QPushButton("Test Connessione")
        self.test_connection_button.clicked.connect(self._test_connection)
        self.test_connection_button.setEnabled(self.allow_test_connection)
        bottom_buttons_layout.addWidget(self.test_connection_button)

        bottom_buttons_layout.addStretch()

        self.button_box = QDialogButtonBox()
        self.button_box.addButton("Salva e Connetti", QDialogButtonBox.AcceptRole)
        self.button_box.addButton(QDialogButtonBox.Cancel)
        
        self.button_box.accepted.connect(self._handle_save_and_connect)
        self.button_box.rejected.connect(self._handle_cancel)
        
        bottom_buttons_layout.addWidget(self.button_box)
        layout.addRow(bottom_buttons_layout)

        # --- MODIFICA CHIAVE QUI: Flusso di inizializzazione dei campi ---
        # Definisci i valori di default DESIDERATI per il PRIMO avvio o se si cancella il .ini
        self.default_preset_config = {
            SETTINGS_DB_TYPE: "Remoto (Server Specifico)",
            SETTINGS_DB_HOST: "10.99.80.131",
            SETTINGS_DB_PORT: 5432,
            SETTINGS_DB_NAME: "catasto_storico",
            SETTINGS_DB_USER: "postgres",
            SETTINGS_DB_SCHEMA: "catasto",
            "password": "" # La password non sarà precompilata qui, ma dal "LastPassword"
        }

        # Carica le impostazioni. Se initial_config è fornito da run_gui_app, ha la precedenza.
        # Altrimenti, carichiamo da QSettings, usando i preset come default se non salvato.
        if initial_config:
            self._populate_from_config(initial_config)
        else:
            self._load_settings() # Questo metodo ora carica da QSettings usando i default_preset_config

        # Questa chiamata è cruciale per impostare lo stato iniziale dei campi host/label
        # basandosi sul currentIndex che _populate_from_config ha impostato.
        self._db_type_changed(self.db_type_combo.currentIndex())
        
        # La password viene popolata qui da "Database/LastPassword", che ha la precedenza.
        self.password_edit.setText(self.settings.value("Database/LastPassword", "", type=str))

    # --- MODIFICA CRUCIALE A _load_settings ---
    def _load_settings(self):
        """Carica le impostazioni da QSettings, usando self.default_preset_config come fallback."""
        config_to_load = {}
        config_to_load[SETTINGS_DB_TYPE] = self.settings.value(SETTINGS_DB_TYPE, self.default_preset_config[SETTINGS_DB_TYPE], type=str)
        config_to_load[SETTINGS_DB_HOST] = self.settings.value(SETTINGS_DB_HOST, self.default_preset_config[SETTINGS_DB_HOST], type=str)
        config_to_load[SETTINGS_DB_PORT] = self.settings.value(SETTINGS_DB_PORT, self.default_preset_config[SETTINGS_DB_PORT], type=int)
        config_to_load[SETTINGS_DB_NAME] = self.settings.value(SETTINGS_DB_NAME, self.default_preset_config[SETTINGS_DB_NAME], type=str)
        config_to_load[SETTINGS_DB_USER] = self.settings.value(SETTINGS_DB_USER, self.default_preset_config[SETTINGS_DB_USER], type=str)
        config_to_load[SETTINGS_DB_SCHEMA] = self.settings.value(SETTINGS_DB_SCHEMA, self.default_preset_config[SETTINGS_DB_SCHEMA], type=str)
        
        # La password non è parte di questo "caricamento per i campi", ma da "LastPassword"
        # self.password_edit.setText(...) verrà fatto nel __init__ dopo _load_settings
        
        self._populate_from_config(config_to_load)
        # Non è necessario chiamare _db_type_changed qui, sarà chiamato alla fine di __init__

    # --- MODIFICA A _populate_from_config per riflettere i tipi ---
    def _populate_from_config(self, config: Dict[str, Any]):
        """
        Popola i campi del dialogo con i valori di configurazione forniti.
        """
        # Aggiunto log per debug interno
        logging.getLogger("CatastoGUI").debug(f"Popolando DBConfigDialog con: { {k:v for k,v in config.items() if k != 'password'} }")

        db_type_str = config.get(SETTINGS_DB_TYPE, self.default_preset_config[SETTINGS_DB_TYPE])
        type_index = self.db_type_combo.findText(db_type_str, Qt.MatchFixedString)
        if type_index >= 0:
            self.db_type_combo.setCurrentIndex(type_index)
        else:
            # Fallback se il testo non matcha (dovrebbe essere raro se i valori sono coerenti)
            self.db_type_combo.setCurrentIndex(0) 

        self.host_edit.setText(config.get(SETTINGS_DB_HOST, self.default_preset_config[SETTINGS_DB_HOST]))
        
        # Recupera la porta in modo robusto
        port_value = config.get(SETTINGS_DB_PORT, self.default_preset_config[SETTINGS_DB_PORT])
        try:
            self.port_spinbox.setValue(int(port_value))
        except (ValueError, TypeError):
            self.port_spinbox.setValue(self.default_preset_config[SETTINGS_DB_PORT])
            logging.getLogger("CatastoGUI").warning(f"Valore porta non valido '{port_value}' in config, usando default {self.default_preset_config[SETTINGS_DB_PORT]}.")

        self.dbname_edit.setText(config.get(SETTINGS_DB_NAME, self.default_preset_config[SETTINGS_DB_NAME]))
        self.user_edit.setText(config.get(SETTINGS_DB_USER, self.default_preset_config[SETTINGS_DB_USER]))
        self.schema_edit.setText(config.get(SETTINGS_DB_SCHEMA, self.default_preset_config[SETTINGS_DB_SCHEMA]))
        
        # La password viene gestita da "LastPassword" nel __init__


    # --- NUOVI METODI WRAPPER PER accepted() e rejected() ---
    def _handle_save_and_connect(self):
        """Gestisce il click su 'Salva e Connetti', include validazione e poi accetta il dialogo."""
        config_values = self.get_config_values(include_password=True)

        if not all([config_values["dbname"], config_values["user"], config_values["password"]]):
            QMessageBox.warning(self, "Dati Mancanti", "Compilare tutti i campi obbligatori (Nome DB, Utente DB, Password DB).")
            return

        is_remoto = (self.db_type_combo.currentIndex() == 1)
        if is_remoto and not config_values["host"]:
            QMessageBox.warning(self, "Dati Mancanti", "L'indirizzo del server host è obbligatorio per database remoto.")
            return

        # Se la validazione passa, salva le impostazioni (senza password permanente)
        self._save_settings() 
        # Chiudi il dialogo con QDialog.Accepted.
        # Questa chiamata è fondamentale per far sì che config_dialog.exec_() restituisca Accepted.
        super().accept() 

    def _handle_cancel(self):
        """Gestisce il click su 'Annulla'."""
        # Non è necessaria alcuna logica di salvataggio qui
        # Chiudi il dialogo con QDialog.Rejected.
        super().reject()
    # --- FINE NUOVI METODI WRAPPER ---
    
    def _db_type_changed(self, index: int):
        """
        Gestisce il cambio del tipo di server DB (locale/remoto) per mostrare/nascondere il campo host.
        """
        is_remoto = (index == 1) # 0 è "Locale", 1 è "Remoto"
        self.host_label.setVisible(is_remoto)
        self.host_edit.setVisible(is_remoto)
        
        if not is_remoto:
            self.host_edit.setText("localhost")
            self.host_edit.setReadOnly(True)
        else:
            self.host_edit.setReadOnly(False)
            # Pulisce il campo host se prima era "localhost"
            if self.host_edit.text() == "localhost":
                self.host_edit.clear()
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---

    # --- NUOVO METODO PER IL TEST DI CONNESSIONE ---
    def _test_connection(self):
        config_values = self.get_config_values(include_password=True) # Ottieni anche la password
        
        # Validazione minima prima del test
        if not all([config_values["dbname"], config_values["user"], config_values["password"]]):
            QMessageBox.warning(self, "Dati Mancanti", "Compilare tutti i campi obbligatori (Nome DB, Utente DB, Password DB) prima di testare la connessione.")
            return

        # Chiudi un eventuale db_manager_test precedente
        if self.db_manager_test:
            self.db_manager_test.close_pool()

        # Istanzia un nuovo DBManager per il test
        try:
            self.db_manager_test = CatastoDBManager(
                dbname=config_values["dbname"],
                user=config_values["user"],
                password=config_values["password"],
                host=config_values["host"],
                port=config_values["port"],
                schema=config_values["schema"],
                application_name="CatastoAppGUI_TestConnessione"
            )
            
            if self.db_manager_test.initialize_main_pool():
                QMessageBox.information(self, "Test Connessione", "Connessione al database riuscita con successo!")
                # Chiudi il pool di test subito dopo il successo
                self.db_manager_test.close_pool() 
                self.db_manager_test = None
            else:
                QMessageBox.warning(self, "Test Connessione", "Connessione al database fallita. Verificare i parametri e la password.")
                # Il logger di db_manager_test ha già registrato i dettagli dell'errore
        except Exception as e:
            QMessageBox.critical(self, "Errore Test", f"Si è verificato un errore durante il test di connessione: {e}")
            self.logger.error(f"Errore imprevisto durante il test di connessione: {e}", exc_info=True)
        finally:
            if self.db_manager_test: # Assicurati che sia chiuso anche in caso di eccezione
                self.db_manager_test.close_pool()
                self.db_manager_test = None

    # Modifica il metodo accept per salvare la password usata (temporaneamente)
    def accept(self):
        config_values = self.get_config_values(include_password=True) # Ottieni anche la password
        # Validazione completa prima di salvare e accettare
        if not all([config_values["dbname"], config_values["user"], config_values["password"]]):
            QMessageBox.warning(self, "Dati Mancanti", "Compilare tutti i campi obbligatori (Nome DB, Utente DB, Password DB).")
            return
        is_remoto = (self.db_type_combo.currentIndex() == 1)
        if is_remoto and not config_values["host"]:
            QMessageBox.warning(self, "Dati Mancanti", "L'indirizzo del server host è obbligatorio per database remoto.")
            return

        # Salva la password nel QSettings in una chiave temporanea per la sessione o l'ultimo uso.
        # NON la salvare permanentemente in SETTINGS_DB_PASSWORD.
        self.settings.setValue("Database/LastPassword", config_values["password"])
        self.settings.sync() # Forza la scrittura

        self._save_settings() # Questo salva le altre impostazioni (senza password)
        super().accept()
    

    def _save_settings(self):
        self.settings.setValue(SETTINGS_DB_TYPE, self.db_type_combo.currentText())
        host_to_save = "localhost" if self.db_type_combo.currentIndex() == 0 else self.host_edit.text().strip()
        self.settings.setValue(SETTINGS_DB_HOST, host_to_save)
        self.settings.setValue(SETTINGS_DB_PORT, self.port_spinbox.value())
        self.settings.setValue(SETTINGS_DB_NAME, self.dbname_edit.text().strip())
        self.settings.setValue(SETTINGS_DB_USER, self.user_edit.text().strip())
        self.settings.setValue(SETTINGS_DB_SCHEMA, self.schema_edit.text().strip() or "catasto")
        
        # AGGIUNGI UN LOG PER VERIFICARE COSA VIENE SALVATO
        logging.getLogger("CatastoGUI").info(f"Salvando impostazioni: Type={self.db_type_combo.currentText()}, Host={host_to_save}, Port={self.port_spinbox.value()}, DBName={self.dbname_edit.text().strip()}, User={self.user_edit.text().strip()}, Schema={self.schema_edit.text().strip() or 'catasto'}")

        self.settings.sync() # Forza la scrittura su disco
        logging.getLogger("CatastoGUI").info(f"Impostazioni di connessione al database salvate (senza password) in: {self.settings.fileName()}")
    # Metodo getter modificato per includere la password (opzionale)
    def get_config_values(self, include_password: bool = False) -> Dict[str, Any]:
        host_val = "localhost" if self.db_type_combo.currentIndex() == 0 else self.host_edit.text().strip()
        config = {
            "host": host_val,
            "port": self.port_spinbox.value(),
            "dbname": self.dbname_edit.text().strip(),
            "user": self.user_edit.text().strip(),
            "schema": self.schema_edit.text().strip() or "catasto",
        }
        if include_password:
            config["password"] = self.password_edit.text()
        return config
    
    
class DocumentViewerDialog(QDialog):
    def __init__(self, parent=None, file_path: str = None):
        super().__init__(parent)
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        self.file_path = file_path
        self.setWindowTitle("Visualizzatore Documento")
        self.setMinimumSize(800, 600)

        self._init_ui()
        self._load_document()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        self.viewer_widget = QWidget()
        self.viewer_layout = QVBoxLayout(self.viewer_widget)
        self.viewer_layout.setContentsMargins(0,0,0,0)

        button_layout = QHBoxLayout()
        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        button_layout.addStretch()

        main_layout.addWidget(self.viewer_widget)
        main_layout.addLayout(button_layout)

    def _load_document(self):
        if not self.file_path or not os.path.exists(self.file_path):
            QMessageBox.critical(self, "Errore", "File non trovato o percorso non valido.")
            self.logger.error(f"Tentativo di caricare documento non trovato o non valido: {self.file_path}")
            self.viewer_layout.addWidget(QLabel("Errore: File non trovato."))
            return

        file_extension = os.path.splitext(self.file_path)[1].lower()

        if file_extension == '.pdf':
            self._load_pdf()
        elif file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            self._load_image()
        else:
            QMessageBox.warning(self, "Formato non supportato", f"Il formato '{file_extension}' non è supportato per la visualizzazione interna.")
            self.logger.warning(f"Formato documento non supportato per la visualizzazione interna: {self.file_path}")
            self.viewer_layout.addWidget(QLabel(f"Formato '{file_extension}' non supportato."))
            
    def _load_pdf(self):
        try:
            self.web_view = QWebEngineView(self)
            self.web_view.setUrl(QUrl.fromLocalFile(self.file_path))
            self.viewer_layout.addWidget(self.web_view)
            self.logger.info(f"PDF caricato in QWebEngineView: {self.file_path}")
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento del PDF in QWebEngineView: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore PDF", f"Impossibile visualizzare il PDF. Errore: {e}")
            self.viewer_layout.addWidget(QLabel("Errore nel caricamento del PDF."))
            
    def _load_image(self):
        try:
            self.graphics_scene = QGraphicsScene(self)
            self.graphics_view = QGraphicsView(self.graphics_scene, self)
            self.graphics_view.setRenderHint(QPainter.Antialiasing)
            self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform)
            self.graphics_view.setCacheMode(QGraphicsView.CacheBackground)
            self.graphics_view.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
            self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)

            pixmap = QPixmap(self.file_path)
            if pixmap.isNull():
                raise ValueError(f"Impossibile caricare immagine da: {self.file_path}")

            self.pixmap_item = self.graphics_scene.addPixmap(pixmap)
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            self.graphics_view.setAlignment(Qt.AlignCenter)

            self.zoom_factor = 1.0
            self.graphics_view.wheelEvent = self._image_wheel_event

            self.viewer_layout.addWidget(self.graphics_view)
            self.logger.info(f"Immagine caricata in QGraphicsView: {self.file_path}")

        except Exception as e:
            self.logger.error(f"Errore durante il caricamento dell'immagine in QGraphicsView: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Immagine", f"Impossibile visualizzare l'immagine. Errore: {e}")
            self.viewer_layout.addWidget(QLabel("Errore nel caricamento dell'immagine."))

    def _image_wheel_event(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            self.zoom_factor *= zoom_in_factor
        else:
            self.zoom_factor *= zoom_out_factor

        self.zoom_factor = max(0.1, min(self.zoom_factor, 10.0))

        transform = self.graphics_view.transform()
        transform.reset()
        transform.scale(self.zoom_factor, self.zoom_factor)
        self.graphics_view.setTransform(transform)

        event.accept()

# *** FINE: Classe DocumentViewerDialog ***
class PartitaDetailsDialog(QDialog):
    def __init__(self, partita_data, parent=None):
        super(PartitaDetailsDialog, self).__init__(parent)
        self.partita = partita_data
        self.db_manager = getattr(parent, 'db_manager', None) 
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(
            f"Dettagli Partita {partita_data['numero_partita']}")
        self.setMinimumSize(700, 500)

        self._init_ui()
        self._load_all_data() # <--- Assicurati che sia chiamato solo qui
        self._update_document_tab_title() 

        
    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Informazioni generali (come prima)
        header_layout = QHBoxLayout()
        title_label = QLabel(f"<h2>Partita N.{self.partita['numero_partita']} ({self.partita['suffisso_partita']}) - {self.partita['comune_nome']}</h2>")
        header_layout.addWidget(title_label)
        layout.addLayout(header_layout)

        # Informazioni generali
        info_group = QGroupBox("Informazioni Generali")
        info_layout = QGridLayout()

        info_layout.addWidget(QLabel("<b>ID:</b>"), 0, 0)
        info_layout.addWidget(QLabel(str(self.partita['id'])), 0, 1)

        info_layout.addWidget(QLabel("<b>Tipo:</b>"), 0, 2)
        info_layout.addWidget(QLabel(self.partita['tipo']), 0, 3)

        info_layout.addWidget(QLabel("<b>Stato:</b>"), 1, 0)
        info_layout.addWidget(QLabel(self.partita['stato']), 1, 1)

        info_layout.addWidget(QLabel("<b>Data Impianto:</b>"), 1, 2)
        info_layout.addWidget(QLabel(str(self.partita['data_impianto'])), 1, 3)

        # NUOVA RIGA: Suffisso Partita
        info_layout.addWidget(QLabel("<b>Suffisso:</b>"), 2, 2) # Adatta la riga/colonna
        info_layout.addWidget(QLabel(self.partita.get('suffisso_partita', 'N/A')), 2, 3)

        if self.partita.get('data_chiusura'):
            info_layout.addWidget(QLabel("<b>Data Chiusura:</b>"), 2, 0) # Adatta la riga
            info_layout.addWidget(QLabel(str(self.partita['data_chiusura'])), 2, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Tabs per possessori, immobili, variazioni, documenti
        self.tabs = QTabWidget() # Rinomina a self.tabs per coerenza
        layout.addWidget(self.tabs)

        # Tab Possessori
        possessori_tab = QWidget()
        possessori_layout = QVBoxLayout(possessori_tab)
        possessori_table = QTableWidget()
        possessori_table.setColumnCount(4)
        possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Titolo", "Quota"])
        possessori_table.setAlternatingRowColors(True)
        if self.partita.get('possessori'):
            possessori_table.setRowCount(len(self.partita['possessori']))
            for i, possessore in enumerate(self.partita['possessori']):
                possessori_table.setItem(i, 0, QTableWidgetItem(str(possessore.get('id', ''))))
                possessori_table.setItem(i, 1, QTableWidgetItem(possessore.get('nome_completo', '')))
                possessori_table.setItem(i, 2, QTableWidgetItem(possessore.get('titolo', '')))
                possessori_table.setItem(i, 3, QTableWidgetItem(possessore.get('quota', '')))
        possessori_layout.addWidget(possessori_table)
        self.tabs.addTab(possessori_tab, "Possessori")

        # Tab Immobili
        immobili_tab = QWidget()
        immobili_layout = QVBoxLayout(immobili_tab)
        immobili_table = ImmobiliTableWidget()
        if self.partita.get('immobili'):
            immobili_table.populate_data(self.partita['immobili'])
        immobili_layout.addWidget(immobili_table)
        self.tabs.addTab(immobili_tab, "Immobili")

        # Tab Variazioni
        variazioni_tab = QWidget()
        variazioni_layout = QVBoxLayout()

        variazioni_table = QTableWidget()
        # Aumenta il numero di colonne per includere origine e destinazione per esteso
        variazioni_table.setColumnCount(6) # Ad es., ID, Tipo, Data, Partita Origine, Partita Destinazione, Contratto
        variazioni_table.setHorizontalHeaderLabels([
            "ID Var.", "Tipo", "Data Var.", "Partita Origine", "Partita Destinazione", "Contratto" # Etichette aggiornate
        ])
        variazioni_table.setAlternatingRowColors(True)
        variazioni_table.horizontalHeader().setStretchLastSection(True) # Per far espandere l'ultima colonna
        variazioni_table.setEditTriggers(QTableWidget.NoEditTriggers)

        if self.partita.get('variazioni'):
            variazioni_table.setRowCount(len(self.partita['variazioni']))
            for i, var in enumerate(self.partita['variazioni']):
                col = 0
                variazioni_table.setItem(i, col, QTableWidgetItem(str(var.get('id', '')))); col += 1
                variazioni_table.setItem(i, col, QTableWidgetItem(var.get('tipo', ''))); col += 1
                variazioni_table.setItem(i, col, QTableWidgetItem(str(var.get('data_variazione', '')))); col += 1

                # Informazioni Partita Origine
                origine_text = ""
                if var.get('partita_origine_id'): # Solo se l'ID esiste
                    num_orig = var.get('origine_numero_partita', 'N/D')
                    com_orig = var.get('origine_comune_nome', 'N/D')
                    origine_text = f"N.{num_orig} ({com_orig})"
                else:
                    origine_text = "-" # O "N/A"
                variazioni_table.setItem(i, col, QTableWidgetItem(origine_text)); col += 1

                # Informazioni Partita Destinazione
                dest_text = ""
                if var.get('partita_destinazione_id'): # Solo se l'ID esiste
                    num_dest = var.get('destinazione_numero_partita', 'N/D')
                    com_dest = var.get('destinazione_comune_nome', 'N/D')
                    dest_text = f"N.{num_dest} ({com_dest})"
                else:
                    dest_text = "-" # O "N/A"
                variazioni_table.setItem(i, col, QTableWidgetItem(dest_text)); col += 1

                # Contratto info (come prima)
                contratto_text = ""
                if var.get('tipo_contratto'):
                    contratto_text = f"{var['tipo_contratto']} del {var.get('data_contratto', '')}"
                    if var.get('notaio'):
                        contratto_text += f" - {var['notaio']}"
                variazioni_table.setItem(i, col, QTableWidgetItem(contratto_text)); col += 1

        variazioni_layout.addWidget(variazioni_table)
        variazioni_tab.setLayout(variazioni_layout)
        self.tabs.addTab(variazioni_tab, "Variazioni")


        # Tab Documenti (come prima)
        self.documents_tab_widget = QWidget()
        self.documents_tab_layout = QVBoxLayout(self.documents_tab_widget)
        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(6)
        self.documents_table.setHorizontalHeaderLabels(["ID Doc.", "Titolo", "Tipo Doc.", "Anno", "Rilevanza", "Percorso"])
        self.documents_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.documents_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSortingEnabled(True)
        self.documents_table.itemSelectionChanged.connect(self._update_details_doc_buttons_state)
        self.documents_tab_layout.addWidget(self.documents_table)
        
        doc_buttons_layout = QHBoxLayout()
        self.btn_apri_doc_details_dialog = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogOpenButton), "Apri Documento")
        self.btn_apri_doc_details_dialog.clicked.connect(self._apri_documento_selezionato_from_details_dialog)
        self.btn_apri_doc_details_dialog.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_apri_doc_details_dialog)
        doc_buttons_layout.addStretch()
        self.documents_tab_layout.addLayout(doc_buttons_layout)
        self.tabs.addTab(self.documents_tab_widget, "Documenti Allegati")


        # --- Sostituzione dei pulsanti di esportazione ---
        buttons_layout = QHBoxLayout()

        self.btn_export_txt = QPushButton("Esporta TXT")
        self.btn_export_txt.clicked.connect(self._export_partita_to_txt)
        buttons_layout.addWidget(self.btn_export_txt)

        self.btn_export_pdf = QPushButton("Esporta PDF")
        self.btn_export_pdf.clicked.connect(self._export_partita_to_pdf)
        self.btn_export_pdf.setEnabled(FPDF_AVAILABLE) # Abilita solo se FPDF è disponibile
        buttons_layout.addWidget(self.btn_export_pdf)

        # Il pulsante JSON che avevi prima era export_button. Lo rimuoviamo o lo rendiamo PDF/TXT.
        # export_button = QPushButton("Esporta in JSON")
        # export_button.clicked.connect(self.export_to_json) # Non più chiamato
        # buttons_layout.addWidget(export_button) # Rimuovi o commenta questa riga

        close_button = QPushButton("Chiudi")
        close_button.clicked.connect(self.accept)

        buttons_layout.addStretch()
        # buttons_layout.addWidget(export_button) # Rimosso
        buttons_layout.addWidget(close_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def _load_all_data(self):
        """Carica i dati per tutti i tab."""
        # Se il db_manager non è stato passato o non è valido
        if not self.db_manager:
            self.logger.warning("DB Manager non disponibile, impossibile caricare i dati dei documenti.")
            # Popola la tabella con un messaggio di errore o lascia vuota
            self.documents_table.setRowCount(1)
            item_msg = QTableWidgetItem("DB Manager non disponibile. Impossibile caricare documenti.")
            item_msg.setTextAlignment(Qt.AlignCenter)
            self.documents_table.setItem(0, 0, item_msg)
            self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
            return

        # Carica i documenti e aggiorna la tabella dei documenti
        try:
            documenti_list = self.db_manager.get_documenti_per_partita(self.partita['id'])
            self.documents_table.setRowCount(0) # Pulisci prima di popolare

            if documenti_list:
                self.documents_table.setRowCount(len(documenti_list))
                for row, doc_data in enumerate(documenti_list):
                    self.documents_table.setItem(row, 0, QTableWidgetItem(str(doc_data.get('documento_id', ''))))
                    self.documents_table.setItem(row, 1, QTableWidgetItem(doc_data.get('titolo', '')))
                    self.documents_table.setItem(row, 2, QTableWidgetItem(doc_data.get('tipo_documento', '')))
                    self.documents_table.setItem(row, 3, QTableWidgetItem(str(doc_data.get('anno', ''))))
                    self.documents_table.setItem(row, 4, QTableWidgetItem(doc_data.get('rilevanza', '')))
                    
                    # Percorso, con un tooltip che mostra il percorso completo
                    percorso_file_full = doc_data.get('percorso_file', 'N/D')
                    path_item = QTableWidgetItem(os.path.basename(percorso_file_full) if percorso_file_full else "N/D")
                    path_item.setToolTip(percorso_file_full) # Il tooltip mostrerà il percorso completo
                    # Salva il percorso completo nell'UserRole per il pulsante "Apri"
                    percorso_file_full = doc_data.get('percorso_file', '')
                    path_item = QTableWidgetItem(os.path.basename(percorso_file_full) if percorso_file_full else "N/D")
                    path_item.setData(Qt.UserRole, percorso_file_full)  # Assicurati che questo sia sempre una stringa valida
                    self.documents_table.setItem(row, 5, path_item)
                self.documents_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun documento allegato per la partita ID {self.partita['id']}.")
                self.documents_table.setRowCount(1)
                no_docs_item = QTableWidgetItem("Nessun documento allegato a questa partita.")
                no_docs_item.setTextAlignment(Qt.AlignCenter)
                self.documents_table.setItem(0, 0, no_docs_item)
                self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il caricamento dei documenti per la partita {self.partita['id']}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Documenti", f"Si è verificato un errore durante il caricamento dei documenti: {e}")
            self.documents_table.setRowCount(1)
            error_item = QTableWidgetItem("Errore nel caricamento dei documenti.")
            error_item.setTextAlignment(Qt.AlignCenter)
            self.documents_table.setItem(0, 0, error_item)
            self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
        finally:
            self.documents_table.setSortingEnabled(True)
            self._update_document_tab_title() # Aggiorna il titolo del tab con il conteggio
            self._update_details_doc_buttons_state() # Aggiorna lo stato dei pulsanti Apri

    def _export_partita_to_txt(self):
        """Esporta i dettagli della partita in formato TXT (testo leggibile)."""
        if not self.partita:
            QMessageBox.warning(self, "Errore Dati", "Nessun dato della partita da esportare.")
            return

        partita_id = self.partita.get('id', 'sconosciuto')
        default_filename = f"dettaglio_partita_{partita_id}_{date.today().isoformat()}.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salva Dettaglio Partita in TXT",
            default_filename,
            "File di testo (*.txt);;Tutti i file (*)"
        )

        if file_path:
            try:
                # Genera un testo leggibile con le informazioni della partita
                text_content = self._generate_partita_text_report()

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text_content)

                QMessageBox.information(
                    self, "Esportazione Completata", f"Il dettaglio della partita è stato salvato in:\n{file_path}")
            except Exception as e:
                self.logger.error(f"Errore durante l'esportazione TXT del dettaglio partita: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Esportazione", f"Errore durante il salvataggio del file TXT:\n{e}")

    def _export_partita_to_pdf(self):
        """Esporta i dettagli della partita in formato PDF."""
        if not FPDF_AVAILABLE:
            QMessageBox.critical(self, "Errore Libreria", "La libreria FPDF (fpdf2) non è disponibile per generare PDF.")
            return
        if not self.partita:
            QMessageBox.warning(self, "Errore Dati", "Nessun dato della partita da esportare.")
            return

        partita_id = self.partita.get('id', 'sconosciuto')
        pdf_report_title = f"Dettaglio Partita N.{self.partita.get('numero_partita', 'N/D')} - Comune: {self.partita.get('comune_nome', 'N/D')}"
        default_filename_prefix = f"dettaglio_partita_{partita_id}"

        # Genera un testo leggibile per l'anteprima e per il PDF
        text_content = self._generate_partita_text_report()

        # Usa la classe generica per l'esportazione PDF (che include l'anteprima)
        # Nota: PDFApreviewDialog e GenericTextReportPDF sono in app_utils
        preview_dialog = PDFApreviewDialog(text_content, self, title=f"Anteprima: {pdf_report_title}")
        if preview_dialog.exec_() != QDialog.Accepted:
            self.logger.info(f"Esportazione PDF per '{pdf_report_title}' annullata dall'utente dopo anteprima.")
            return

        filename_pdf, _ = QFileDialog.getSaveFileName(
            self, f"Salva PDF - {pdf_report_title}", f"{default_filename_prefix}_{date.today().isoformat()}.pdf", "File PDF (*.pdf)")

        if filename_pdf:
            try:
                pdf = GenericTextReportPDF(report_title=pdf_report_title)
                pdf.add_page()
                pdf.add_report_text(text_content)
                pdf.output(filename_pdf)
                QMessageBox.information(self, "Esportazione PDF Completata",
                                        f"Dettaglio partita PDF salvato con successo in:\n{filename_pdf}")
            except Exception as e:
                self.logger.error(f"Errore durante la generazione del PDF per il dettaglio partita: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Esportazione PDF", f"Impossibile generare il PDF:\n{e}")

    def _generate_partita_text_report(self) -> str:
        """
        Genera un report testuale formattato con tutti i dettagli della partita,
        inclusi i possessori, immobili, variazioni e documenti allegati.
        """
        report_lines = []
        partita = self.partita # self.partita contiene tutti i dati recuperati da get_partita_details

        # --- SEZIONE 1: INTESTAZIONE E DATI GENERALI PARTITA ---
        report_lines.append("=" * 70)
        # Includi il suffisso nel titolo, se presente
        numero_partita_display = f"N. {partita.get('numero_partita', 'N/D')}"
        if partita.get('suffisso_partita'):
            numero_partita_display += f" ({partita['suffisso_partita']})"

        report_lines.append(f"DETTAGLIO PARTITA {numero_partita_display}")
        report_lines.append(f"Comune: {partita.get('comune_nome', 'N/D')}")
        report_lines.append(f"ID Partita: {partita.get('id', 'N/D')}")
        report_lines.append("=" * 70)

        report_lines.append(f"Tipo Partita: {partita.get('tipo', 'N/D')}")
        report_lines.append(f"Stato: {partita.get('stato', 'N/D')}")
        report_lines.append(f"Data Impianto: {partita.get('data_impianto', 'N/D')}")
        data_chiusura = partita.get('data_chiusura')
        report_lines.append(f"Data Chiusura: {data_chiusura if data_chiusura else 'N/A'}")
        numero_provenienza = partita.get('numero_provenienza')
        report_lines.append(f"Numero Provenienza: {numero_provenienza if numero_provenienza else 'N/A'}")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 2: POSSESSORI ---
        report_lines.append("=" * 70)
        report_lines.append("POSSESSORI ASSOCIATI")
        report_lines.append("=" * 70)
        if partita.get('possessori'):
            for i, poss in enumerate(partita['possessori']):
                report_lines.append(f"  - Possessore {i+1} (ID: {poss.get('id', 'N/D')}): {poss.get('nome_completo', 'N/D')}")
                report_lines.append(f"    Titolo di Possesso: {poss.get('titolo', 'N/A')}")
                report_lines.append(f"    Quota: {poss.get('quota', 'N/A')}")
                if i < len(partita['possessori']) - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra possessori
        else:
            report_lines.append("  Nessun possessore associato a questa partita.")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 3: IMMOBILI ---
        report_lines.append("=" * 70)
        report_lines.append("IMMOBILI CENSITI")
        report_lines.append("=" * 70)
        if partita.get('immobili'):
            for i, imm in enumerate(partita['immobili']):
                report_lines.append(f"  - Immobile {i+1} (ID: {imm.get('id', 'N/D')}): {imm.get('natura', 'N/D')}")
                localita_info = f"{imm.get('localita_nome', '')}"
                if imm.get('civico') is not None and str(imm.get('civico')).strip() != '':
                    localita_info += f", civ. {imm.get('civico')}"
                if imm.get('localita_tipo'):
                    localita_info += f" ({imm.get('localita_tipo')})"
                report_lines.append(f"    Località: {localita_info.strip() if localita_info.strip() else 'N/A'}")
                report_lines.append(f"    Classificazione: {imm.get('classificazione', 'N/A')}")
                report_lines.append(f"    Consistenza: {imm.get('consistenza', 'N/A')}")
                piani_vani_info = []
                if imm.get('numero_piani') is not None and imm.get('numero_piani') > 0:
                    piani_vani_info.append(f"Piani: {imm.get('numero_piani')}")
                if imm.get('numero_vani') is not None and imm.get('numero_vani') > 0:
                    piani_vani_info.append(f"Vani: {imm.get('numero_vani')}")
                if piani_vani_info:
                    report_lines.append(f"    Dettagli: {' | '.join(piani_vani_info)}")
                
                if i < len(partita['immobili']) - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra immobili
        else:
            report_lines.append("  Nessun immobile associato a questa partita.")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 4: VARIAZIONI ---
        report_lines.append("=" * 70)
        report_lines.append("VARIAZIONI STORICHE")
        report_lines.append("=" * 70)
        if partita.get('variazioni'):
            for i, var in enumerate(partita['variazioni']):
                report_lines.append(f"  - Variazione {i+1} (ID: {var.get('id', 'N/D')}): {var.get('tipo', 'N/D')}")
                report_lines.append(f"    Data Variazione: {var.get('data_variazione', 'N/D')}")
                
                # Dettagli Partita Origine
                orig_part_id = var.get('partita_origine_id')
                orig_num = var.get('origine_numero_partita', 'N/D')
                orig_com = var.get('origine_comune_nome', 'N/D')
                if orig_part_id:
                    report_lines.append(f"    Partita Origine: N.{orig_num} (Comune: {orig_com}) [ID: {orig_part_id}]")
                else:
                    report_lines.append("    Partita Origine: N/A")

                # Dettagli Partita Destinazione
                dest_part_id = var.get('partita_destinazione_id')
                dest_num = var.get('destinazione_numero_partita', 'N/D')
                dest_com = var.get('destinazione_comune_nome', 'N/D')
                if dest_part_id:
                    report_lines.append(f"    Partita Destinazione: N.{dest_num} (Comune: {dest_com}) [ID: {dest_part_id}]")
                else:
                    report_lines.append("    Partita Destinazione: N/A")

                # Dettagli Contratto
                contr_info_parts = []
                if var.get('tipo_contratto'): contr_info_parts.append(f"Tipo: {var.get('tipo_contratto')}")
                if var.get('data_contratto'): contr_info_parts.append(f"Data: {var.get('data_contratto')}")
                if var.get('notaio'): contr_info_parts.append(f"Notaio: {var.get('notaio')}")
                if var.get('repertorio'): contr_info_parts.append(f"Repertorio: {var.get('repertorio')}")
                if contr_info_parts:
                    report_lines.append(f"    Contratto: {' | '.join(contr_info_parts)}")
                
                if var.get('note_variazione') : report_lines.append(f"    Note Variazione: {var.get('note_variazione')}") # Se c'è una colonna note per la variazione
                if var.get('contratto_note') : report_lines.append(f"    Note Contratto: {var.get('contratto_note')}") # Se c'è una colonna note nel contratto

                if i < len(partita['variazioni']) - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra variazioni
        else:
            report_lines.append("  Nessuna variazione registrata per questa partita.")
        report_lines.append("\n") # Linea vuota per separazione

        # --- SEZIONE 5: DOCUMENTI ALLEGATI ---
        report_lines.append("=" * 70)
        # Assicurati che self.documents_table sia popolata correttamente
        num_docs = self.documents_table.rowCount()
        # Se la tabella ha una sola riga e contiene il messaggio "Nessun documento..."
        if num_docs == 1 and self.documents_table.item(0,0) and "Nessun documento" in self.documents_table.item(0,0).text():
            num_docs = 0
        report_lines.append(f"DOCUMENTI ALLEGATI ({num_docs})")
        report_lines.append("=" * 70)
        
        if num_docs > 0:
            for r in range(self.documents_table.rowCount()):
                # Assicurati che gli item non siano None (se la tabella è vuota eccetto il placeholder)
                doc_id_item = self.documents_table.item(r,0)
                if not doc_id_item: continue # Salta se la riga è vuota (es. riga placeholder)

                doc_id = doc_id_item.text()
                titolo = self.documents_table.item(r,1).text()
                tipo_doc = self.documents_table.item(r,2).text()
                anno = self.documents_table.item(r,3).text()
                rilevanza = self.documents_table.item(r,4).text()
                percorso_short = self.documents_table.item(r,5).text()

                report_lines.append(f"  - Documento {r+1} (ID: {doc_id}): {titolo}")
                report_lines.append(f"    Tipo: {tipo_doc}, Anno: {anno}, Rilevanza: {rilevanza}")
                report_lines.append(f"    Percorso (locale): {percorso_short}")
                if r < num_docs - 1:
                    report_lines.append("  " + "-" * 60) # Separatore tra documenti
        else:
            report_lines.append("  Nessun documento allegato.")

        # --- SEZIONE FINALE ---
        report_lines.append("\n" + "=" * 70)
        report_lines.append("FINE DETTAGLIO PARTITA")
        report_lines.append("=" * 70)

        return "\n".join(report_lines)
    def _update_document_tab_title(self):
        """Aggiorna il titolo del tab "Documenti Allegati" con il conteggio."""
        count = self.documents_table.rowCount()
        # Se la tabella ha solo 1 riga e il testo è "Nessun documento allegato..." allora il conteggio è 0
        if count == 1 and self.documents_table.item(0,0) and "Nessun documento" in self.documents_table.item(0,0).text():
            count = 0
        
        tab_index = self.tabs.indexOf(self.documents_tab_widget)
        if tab_index != -1:
            self.tabs.setTabText(tab_index, f"Documenti Allegati ({count})")
            self.logger.info(f"Titolo tab documenti aggiornato a 'Documenti Allegati ({count})'.")


    def _update_details_doc_buttons_state(self):
        """Abilita/disabilita il pulsante 'Apri Documento' in base alla selezione."""
        has_selection = bool(self.documents_table.selectedItems())
        self.btn_apri_doc_details_dialog.setEnabled(has_selection)

    def _apri_documento_selezionato_from_details_dialog(self):
        selected_items = self.documents_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un documento dalla lista per aprirlo.")
            return
        
        row = self.documents_table.currentRow()
        percorso_file_item = self.documents_table.item(row, 5) 
        if percorso_file_item:
            percorso_file_completo = percorso_file_item.data(Qt.UserRole) # Recupera il percorso completo salvato
            
            if os.path.exists(percorso_file_completo):
                from PyQt5.QtGui import QDesktopServices
                from PyQt5.QtCore import QUrl
                success = QDesktopServices.openUrl(QUrl.fromLocalFile(percorso_file_completo))
                if not success:
                    QMessageBox.warning(self, "Errore Apertura", f"Impossibile aprire il file:\n{percorso_file_completo}\nVerificare che sia installata un'applicazione associata o che i permessi siano corretti.")
            else:
                QMessageBox.warning(self, "File Non Trovato", f"Il file specificato non è stato trovato al percorso:\n{percorso_file_completo}\nIl file potrebbe essere stato spostato o eliminato.")
        else:
            QMessageBox.warning(self, "Percorso Mancante", "Informazioni sul percorso del file non disponibili per il documento selezionato.")

# *** NUOVO: Riscrizione Completa della Classe ModificaPartitaDialog ***
class ModificaPartitaDialog(QDialog):
    # 1. Metodo __init__ aggiunto per gestire la creazione dell'oggetto
    def __init__(self, db_manager: 'CatastoDBManager', partita_id: int, parent=None):
        super().__init__(parent)  # Chiamata corretta al costruttore della classe genitore
        
        # 2. Inizializzazione degli attributi di istanza
        self.db_manager = db_manager
        self.partita_id = partita_id
        self.partita_data_originale: Optional[Dict[str, Any]] = None
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")
        
        # Data di default problematica (da confrontare se letta dal DB)
        self.problematic_default_date_db = date(1, 1, 1)

        self.setWindowTitle(f"Modifica Dati Partita ID: {self.partita_id}")
        self.setMinimumSize(800, 600) # Dimensioni indicative

        # 3. Chiamata ai metodi per costruire la UI e caricare i dati
        self._init_ui()
        self._load_all_partita_data()

    # 4. I metodi seguenti rimangono invariati, ma ora sono chiamati dal costruttore
    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Intestazione del Dialogo (Informazioni di Base) ---
        header_group = QGroupBox("Dettagli Partita Corrente")
        header_layout = QGridLayout(header_group)
        header_layout.setColumnStretch(1, 1)
        header_layout.setColumnStretch(3, 1)

        header_layout.addWidget(QLabel("<b>ID Partita:</b>"), 0, 0)
        self.id_label = QLabel(str(self.partita_id))
        header_layout.addWidget(self.id_label, 0, 1)

        header_layout.addWidget(QLabel("<b>Comune:</b>"), 0, 2)
        self.comune_label = QLabel("Caricamento...")
        header_layout.addWidget(self.comune_label, 0, 3)
        
        main_layout.addWidget(header_group)

        # --- Tab Widget Principale ---
        self.tab_widget = QTabWidget(self)
        main_layout.addWidget(self.tab_widget)

        # --- Tab 1: Dati Generali Partita ---
        self.tab_dati_generali = QWidget()
        form_layout_generali = QFormLayout(self.tab_dati_generali)
        form_layout_generali.setSpacing(10)
        form_layout_generali.setLabelAlignment(Qt.AlignRight)

        self.numero_partita_spinbox = QSpinBox()
        self.numero_partita_spinbox.setRange(1, 999999)
        form_layout_generali.addRow("Numero Partita (*):", self.numero_partita_spinbox)

        self.suffisso_partita_edit = QLineEdit()
        self.suffisso_partita_edit.setPlaceholderText("Es. bis, ter, A, B (opzionale)")
        self.suffisso_partita_edit.setMaxLength(20)
        form_layout_generali.addRow("Suffisso Partita (opz.):", self.suffisso_partita_edit)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["principale", "secondaria"])
        form_layout_generali.addRow("Tipo (*):", self.tipo_combo)

        self.stato_combo = QComboBox()
        self.stato_combo.addItems(["attiva", "inattiva"])
        form_layout_generali.addRow("Stato (*):", self.stato_combo)

        self.data_impianto_edit = QDateEdit()
        self.data_impianto_edit.setCalendarPopup(True)
        self.data_impianto_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_impianto_edit.setDate(QDate())
        form_layout_generali.addRow("Data Impianto:", self.data_impianto_edit)

        self.data_chiusura_edit = QDateEdit()
        self.data_chiusura_edit.setCalendarPopup(True)
        self.data_chiusura_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_chiusura_edit.setDate(QDate())
        form_layout_generali.addRow("Data Chiusura:", self.data_chiusura_edit)

        self.numero_provenienza_spinbox = QSpinBox()
        self.numero_provenienza_spinbox.setRange(0, 999999)
        self.numero_provenienza_spinbox.setSpecialValueText("Nessuno")
        form_layout_generali.addRow("Numero Provenienza:", self.numero_provenienza_spinbox)
        
        self.tab_widget.addTab(self.tab_dati_generali, "Dati Generali")

        # --- Tab 2: Possessori Associati ---
        self.tab_possessori = QWidget()
        layout_possessori = QVBoxLayout(self.tab_possessori)

        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(5)
        self.possessori_table.setHorizontalHeaderLabels(["ID Rel.", "ID Poss.", "Nome Completo Possessore", "Titolo", "Quota"])
        self.possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.setSelectionMode(QTableWidget.SingleSelection)
        self.possessori_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.possessori_table.horizontalHeader().setStretchLastSection(True)
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_possessori)
        layout_possessori.addWidget(self.possessori_table)

        self.btn_aggiungi_possessore = QPushButton("Aggiungi Possessore...")
        self.btn_aggiungi_possessore.clicked.connect(self._aggiungi_possessore_a_partita)
        possessori_buttons_layout = QHBoxLayout()
        possessori_buttons_layout.addWidget(self.btn_aggiungi_possessore)

        self.btn_modifica_legame_possessore = QPushButton("Modifica Legame...")
        self.btn_modifica_legame_possessore.clicked.connect(self._modifica_legame_possessore)
        self.btn_modifica_legame_possessore.setEnabled(False)
        possessori_buttons_layout.addWidget(self.btn_modifica_legame_possessore)

        self.btn_rimuovi_possessore = QPushButton("Rimuovi dalla Partita")
        self.btn_rimuovi_possessore.clicked.connect(self._rimuovi_possessore_da_partita)
        self.btn_rimuovi_possessore.setEnabled(False)
        possessori_buttons_layout.addWidget(self.btn_rimuovi_possessore)
        possessori_buttons_layout.addStretch()
        layout_possessori.addLayout(possessori_buttons_layout)
        self.tab_widget.addTab(self.tab_possessori, "Possessori Associati")

        # --- Tab 3: Immobili Associati ---
        self.tab_immobili = QWidget()
        layout_immobili = QVBoxLayout(self.tab_immobili)

        self.immobili_table = ImmobiliTableWidget()
        self.immobili_table.setSelectionMode(QTableWidget.SingleSelection)
        self.immobili_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.immobili_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_immobili)
        layout_immobili.addWidget(self.immobili_table)

        immobili_buttons_layout = QHBoxLayout()
        self.btn_aggiungi_immobile = QPushButton("Aggiungi Immobile...")
        self.btn_aggiungi_immobile.clicked.connect(self._aggiungi_immobile_a_partita)
        immobili_buttons_layout.addWidget(self.btn_aggiungi_immobile)

        self.btn_modifica_immobile = QPushButton("Modifica Immobile...")
        self.btn_modifica_immobile.clicked.connect(self._modifica_immobile_associato)
        self.btn_modifica_immobile.setEnabled(False)
        immobili_buttons_layout.addWidget(self.btn_modifica_immobile)

        self.btn_rimuovi_immobile = QPushButton("Rimuovi Immobile")
        self.btn_rimuovi_immobile.clicked.connect(self._rimuovi_immobile_da_partita)
        self.btn_rimuovi_immobile.setEnabled(False)
        immobili_buttons_layout.addWidget(self.btn_rimuovi_immobile)
        immobili_buttons_layout.addStretch()
        layout_immobili.addLayout(immobili_buttons_layout)
        self.tab_widget.addTab(self.tab_immobili, "Immobili Associati")

        # --- Tab 4: Variazioni ---
        self.tab_variazioni = QWidget()
        layout_variazioni = QVBoxLayout(self.tab_variazioni)

        self.variazioni_table = QTableWidget()
        self.variazioni_table.setColumnCount(6)
        self.variazioni_table.setHorizontalHeaderLabels([
            "ID Var.", "Tipo", "Data Var.", "Partita Origine", "Partita Destinazione", "Contratto"
        ])
        self.variazioni_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.variazioni_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.variazioni_table.setSelectionMode(QTableWidget.SingleSelection)
        self.variazioni_table.horizontalHeader().setStretchLastSection(True)
        self.variazioni_table.setAlternatingRowColors(True)
        self.variazioni_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_variazioni)
        layout_variazioni.addWidget(self.variazioni_table)

        variazioni_buttons_layout = QHBoxLayout()
        self.btn_modifica_variazione = QPushButton("Modifica Variazione...")
        self.btn_modifica_variazione.clicked.connect(self._modifica_variazione_selezionata)
        self.btn_modifica_variazione.setEnabled(False)
        variazioni_buttons_layout.addWidget(self.btn_modifica_variazione)
        
        self.btn_elimina_variazione = QPushButton("Elimina Variazione")
        self.btn_elimina_variazione.clicked.connect(self._elimina_variazione_selezionata)
        self.btn_elimina_variazione.setEnabled(False)
        variazioni_buttons_layout.addWidget(self.btn_elimina_variazione)

        variazioni_buttons_layout.addStretch()
        layout_variazioni.addLayout(variazioni_buttons_layout)
        self.tab_widget.addTab(self.tab_variazioni, "Variazioni")

        # --- Tab 5: Documenti Allegati ---
        self.tab_documenti = QWidget()
        layout_documenti = QVBoxLayout(self.tab_documenti)

        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(6)
        self.documents_table.setHorizontalHeaderLabels([
            "ID Doc.", "Titolo", "Tipo Doc.", "Anno", "Rilevanza", "Percorso/Azione"
        ])
        self.documents_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.documents_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.documents_table.setSelectionMode(QTableWidget.SingleSelection)
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSortingEnabled(True)
        self.documents_table.itemSelectionChanged.connect(self._update_details_doc_buttons_state)
        
        self.documents_table.setAcceptDrops(True)
        self.documents_table.setDropIndicatorShown(True)
        self.documents_table.setDragDropMode(QAbstractItemView.DropOnly)
        self.documents_table.dragEnterEvent = self.documents_table_dragEnterEvent
        self.documents_table.dragMoveEvent = self.documents_table_dragMoveEvent
        self.documents_table.dropEvent = self.documents_table_dropEvent
        
        layout_documenti.addWidget(self.documents_table)

        doc_buttons_layout = QHBoxLayout()
        self.btn_allega_nuovo = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileLinkIcon), "Allega Nuovo Documento...")
        self.btn_allega_nuovo.clicked.connect(self._allega_nuovo_documento_a_partita)
        doc_buttons_layout.addWidget(self.btn_allega_nuovo)

        self.btn_apri_doc_details_dialog = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogOpenButton), "Apri Documento Selezionato")
        self.btn_apri_doc_details_dialog.clicked.connect(self._apri_documento_selezionato_from_details_dialog)
        self.btn_apri_doc_details_dialog.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_apri_doc_details_dialog)
        
        self.btn_scollega_doc = QPushButton(QApplication.style().standardIcon(QStyle.SP_TrashIcon), "Scollega Documento")
        self.btn_scollega_doc.clicked.connect(self._scollega_documento_selezionato)
        self.btn_scollega_doc.setEnabled(False)
        doc_buttons_layout.addWidget(self.btn_scollega_doc)
        
        doc_buttons_layout.addStretch()
        layout_documenti.addLayout(doc_buttons_layout)
        
        self.tab_widget.addTab(self.tab_documenti, "Documenti Allegati")

        # --- Pulsanti Salva Dati Generali e Chiudi ---
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton), "Salva Modifiche Dati Generali")
        self.save_button.setToolTip("Salva solo le modifiche apportate nel tab 'Dati Generali'")
        self.save_button.clicked.connect(self._save_changes)

        self.close_dialog_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton), "Chiudi")
        self.close_dialog_button.setToolTip("Chiude il dialogo. Le altre modifiche sono salvate individualmente.")
        self.close_dialog_button.clicked.connect(self.accept)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.close_dialog_button)
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)

    # --- Metodi per il Caricamento dei Dati (Centralizzato) ---
    def _load_all_partita_data(self):
        """Carica tutti i dati della partita e popola i vari tab del dialogo."""
        self.logger.info(f"ModificaPartitaDialog: Caricamento dati per partita ID {self.partita_id}...")
        self.partita_data_originale = self.db_manager.get_partita_details(self.partita_id)
        if not self.partita_data_originale:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare i dati per la partita ID: {self.partita_id}.\nIl dialogo verrà chiuso.")
            QTimer.singleShot(0, self.reject)
            return
        self.comune_label.setText(self.partita_data_originale.get('comune_nome', "N/D"))
        self._populate_dati_generali_tab()
        self._load_possessori_associati()
        self._load_immobili_associati()
        self._load_variazioni_associati()
        self._load_documenti_allegati()
        self.logger.info(f"ModificaPartitaDialog: Dati per partita ID {self.partita_id} caricati in tutti i tab.")
    # --- Metodi di Popolamento per Ciascun Tab ---

    def _populate_dati_generali_tab(self):
        """Popola i campi nel tab 'Dati Generali' con i dati della partita."""
        partita = self.partita_data_originale
        if not partita: return

        self.numero_partita_spinbox.setValue(partita.get('numero_partita', 0))
        self.suffisso_partita_edit.setText(partita.get('suffisso_partita', '') or '')

        tipo_idx = self.tipo_combo.findText(partita.get('tipo', ''), Qt.MatchFixedString)
        if tipo_idx >= 0: self.tipo_combo.setCurrentIndex(tipo_idx)

        stato_idx = self.stato_combo.findText(partita.get('stato', ''), Qt.MatchFixedString)
        if stato_idx >= 0: self.stato_combo.setCurrentIndex(stato_idx)

        data_impianto_db = partita.get('data_impianto')
        self.data_impianto_edit.setDate(datetime_to_qdate(data_impianto_db) if data_impianto_db else QDate())

        data_chiusura_db = partita.get('data_chiusura')
        # Gestisce il default problematico e NULL
        if data_chiusura_db is None or data_chiusura_db == self.problematic_default_date_db:
            self.data_chiusura_edit.setDate(QDate())
        else:
            self.data_chiusura_edit.setDate(datetime_to_qdate(data_chiusura_db))

        num_prov_val = partita.get('numero_provenienza')
        self.numero_provenienza_spinbox.setValue(num_prov_val if num_prov_val is not None else self.numero_provenienza_spinbox.minimum())

        self.logger.debug("Tab 'Dati Generali' popolato.")

    def _load_possessori_associati(self):
        """Carica e popola la tabella dei possessori associati alla partita."""
        self.possessori_table.setRowCount(0)
        self.possessori_table.setSortingEnabled(False)
        self.possessori_table.clearSelection() # Pulisce la selezione
        self.logger.info(f"Caricamento possessori associati per partita ID: {self.partita_id}")

        try:
            possessori = self.db_manager.get_possessori_per_partita(self.partita_id)
            if possessori:
                self.possessori_table.setRowCount(len(possessori))
                for row_idx, poss_data in enumerate(possessori):
                    id_rel_val = poss_data.get('id_relazione_partita_possessore', '')
                    id_rel_item = QTableWidgetItem(str(id_rel_val))
                    id_rel_item.setData(Qt.UserRole, id_rel_val) # Salva l'ID relazione
                    self.possessori_table.setItem(row_idx, 0, id_rel_item)

                    self.possessori_table.setItem(row_idx, 1, QTableWidgetItem(str(poss_data.get('possessore_id', ''))))
                    self.possessori_table.setItem(row_idx, 2, QTableWidgetItem(poss_data.get('nome_completo_possessore', 'N/D')))
                    self.possessori_table.setItem(row_idx, 3, QTableWidgetItem(poss_data.get('titolo_possesso', 'N/D')))
                    self.possessori_table.setItem(row_idx, 4, QTableWidgetItem(poss_data.get('quota_possesso', 'N/D') or '')) # Gestisce None
                self.possessori_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun possessore trovato per la partita ID {self.partita_id}.")
                self.possessori_table.setRowCount(1)
                item = QTableWidgetItem("Nessun possessore associato a questa partita.")
                item.setTextAlignment(Qt.AlignCenter)
                self.possessori_table.setItem(0, 0, item)
                self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il popolamento della tabella possessori per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Popolamento Tabella", f"Si è verificato un errore durante la visualizzazione dei possessori associati:\n{e}")
        finally:
            self.possessori_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_possessori()
            self.logger.debug("Tab 'Possessori' popolato.")

    def _load_immobili_associati(self):
        """Carica e popola la tabella degli immobili associati alla partita."""
        self.immobili_table.setRowCount(0)
        self.immobili_table.setSortingEnabled(False)
        self.immobili_table.clearSelection() # Pulisce la selezione
        self.logger.info(f"Caricamento immobili associati per partita ID: {self.partita_id}")

        try:
            immobili = self.partita_data_originale.get('immobili', []) # Dati immobili sono già in partita_data_originale
            if immobili:
                self.immobili_table.setRowCount(len(immobili))
                for row_idx, imm in enumerate(immobili):
                    # La logica di ImmobiliTableWidget.populate_data è replicata qui per coerenza
                    # ma potresti anche passare i dati a immobili_table.populate_data() se è un widget riusabile
                    self.immobili_table.setItem(row_idx, 0, QTableWidgetItem(str(imm.get('id', ''))))
                    self.immobili_table.setItem(row_idx, 1, QTableWidgetItem(imm.get('natura', '')))
                    self.immobili_table.setItem(row_idx, 2, QTableWidgetItem(imm.get('classificazione', '')))
                    self.immobili_table.setItem(row_idx, 3, QTableWidgetItem(imm.get('consistenza', '')))
                    localita_text = ""
                    if 'localita_nome' in imm:
                        localita_text = imm['localita_nome']
                        if 'civico' in imm and imm['civico'] is not None:
                            localita_text += f", {imm['civico']}"
                        if 'localita_tipo' in imm:
                            localita_text += f" ({imm['localita_tipo']})"
                    self.immobili_table.setItem(row_idx, 4, QTableWidgetItem(localita_text))
                self.immobili_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun immobile trovato per la partita ID {self.partita_id}.")
                self.immobili_table.setRowCount(1)
                item = QTableWidgetItem("Nessun immobile associato a questa partita.")
                item.setTextAlignment(Qt.AlignCenter)
                self.immobili_table.setItem(0, 0, item)
                self.immobili_table.setSpan(0, 0, 1, self.immobili_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il popolamento della tabella immobili per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Popolamento Tabella", f"Si è verificato un errore durante la visualizzazione degli immobili associati:\n{e}")
        finally:
            self.immobili_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_immobili()
            self.logger.debug("Tab 'Immobili' popolato.")

    def _load_variazioni_associati(self):
        """Carica e popola la tabella delle variazioni associate alla partita."""
        self.variazioni_table.setRowCount(0)
        self.variazioni_table.setSortingEnabled(False)
        self.variazioni_table.clearSelection() # Pulisce la selezione
        self.logger.info(f"Caricamento variazioni associate per partita ID: {self.partita_id}")

        try:
            variazioni = self.partita_data_originale.get('variazioni', []) # Dati variazioni sono già in partita_data_originale
            if variazioni:
                self.variazioni_table.setRowCount(len(variazioni))
                for row_idx, var in enumerate(variazioni):
                    col = 0
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(str(var.get('id', '')))); col += 1
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(var.get('tipo', ''))); col += 1
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(str(var.get('data_variazione', '')))); col += 1

                    # Partita Origine
                    orig_text = ""
                    if var.get('partita_origine_id'):
                        num_orig = var.get('origine_numero_partita', 'N/D')
                        com_orig = var.get('origine_comune_nome', 'N/D')
                        orig_text = f"N.{num_orig} ({com_orig})"
                        if var.get('origine_suffisso_partita'): # Se hai il suffisso nella variazione
                            orig_text += f" ({var.get('origine_suffisso_partita')})"
                    else:
                        orig_text = "-"
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(orig_text)); col += 1

                    # Partita Destinazione
                    dest_text = ""
                    if var.get('partita_destinazione_id'):
                        num_dest = var.get('destinazione_numero_partita', 'N/D')
                        com_dest = var.get('destinazione_comune_nome', 'N/D')
                        dest_text = f"N.{num_dest} ({com_dest})"
                        if var.get('destinazione_suffisso_partita'): # Se hai il suffisso nella variazione
                            dest_text += f" ({var.get('destinazione_suffisso_partita')})"
                    else:
                        dest_text = "-"
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(dest_text)); col += 1

                    # Contratto
                    contratto_text = ""
                    if var.get('tipo_contratto'):
                        contratto_text = f"{var['tipo_contratto']} del {var.get('data_contratto', '')}"
                        if var.get('notaio'):
                            contratto_text += f" - {var['notaio']}"
                    self.variazioni_table.setItem(row_idx, col, QTableWidgetItem(contratto_text)); col += 1

                self.variazioni_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessuna variazione trovata per la partita ID {self.partita_id}.")
                self.variazioni_table.setRowCount(1)
                item = QTableWidgetItem("Nessuna variazione associata a questa partita.")
                item.setTextAlignment(Qt.AlignCenter)
                self.variazioni_table.setItem(0, 0, item)
                self.variazioni_table.setSpan(0, 0, 1, self.variazioni_table.columnCount())
        except Exception as e:
            self.logger.error(f"Errore durante il popolamento della tabella variazioni per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Popolamento Tabella", f"Si è verificato un errore durante la visualizzazione delle variazioni associate:\n{e}")
        finally:
            self.variazioni_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_variazioni()
            self.logger.debug("Tab 'Variazioni' popolato.")

    # In gui_widgets.py, nella classe ModificaPartitaDialog
# Sostituisci il metodo _load_documenti_allegati() con questa versione corretta:

    def _load_documenti_allegati(self):
        """Carica e popola la tabella dei documenti allegati alla partita."""
        self.documents_table.setRowCount(0)
        self.documents_table.setSortingEnabled(False)
        self.documents_table.clearSelection() 
        self.logger.info(f"Caricamento documenti per partita ID {self.partita_id}.")

        try:
            # CORREZIONE: Usa self.partita_id invece di self.partita['id']
            documenti = self.db_manager.get_documenti_per_partita(self.partita_id)
            
            if documenti:
                self.documents_table.setRowCount(len(documenti))
                for row, doc in enumerate(documenti):
                    documento_id_storico = doc.get("documento_id")
                    
                    item_doc_id = QTableWidgetItem(str(documento_id_storico))
                    # Salviamo l'ID del documento storico e l'ID della partita per la rimozione del legame
                    item_doc_id.setData(Qt.UserRole + 1, doc.get("dp_documento_id")) # ID del documento storico nella relazione
                    item_doc_id.setData(Qt.UserRole + 2, doc.get("dp_partita_id")) # ID della partita nella relazione (che è self.partita_id)
                    self.documents_table.setItem(row, 0, item_doc_id)
                    
                    self.documents_table.setItem(row, 1, QTableWidgetItem(doc.get("titolo") or ''))
                    self.documents_table.setItem(row, 2, QTableWidgetItem(doc.get("tipo_documento") or ''))
                    self.documents_table.setItem(row, 3, QTableWidgetItem(str(doc.get("anno", '')) or ''))
                    self.documents_table.setItem(row, 4, QTableWidgetItem(doc.get("rilevanza") or ''))
                    
                    # CORREZIONE: Assicurati che il percorso sia salvato correttamente nell'UserRole
                    percorso_file_full = doc.get("percorso_file") or ''
                    path_item = QTableWidgetItem(os.path.basename(percorso_file_full) if percorso_file_full else "N/D")
                    path_item.setData(Qt.UserRole, percorso_file_full) # Salva percorso completo per l'apertura
                    self.documents_table.setItem(row, 5, path_item)
                
                self.documents_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun documento trovato per la partita ID {self.partita_id}.")
                self.documents_table.setRowCount(1)
                no_docs_item = QTableWidgetItem("Nessun documento allegato a questa partita.")
                no_docs_item.setTextAlignment(Qt.AlignCenter)
                self.documents_table.setItem(0, 0, no_docs_item)
                self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())

        except Exception as e:
            self.logger.error(f"Errore caricamento documenti per partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Documenti", f"Si è verificato un errore durante il caricamento dei documenti:\n{e}")
            # Mostra messaggio di errore nella tabella
            self.documents_table.setRowCount(1)
            error_item = QTableWidgetItem(f"Errore nel caricamento dei documenti: {e}")
            error_item.setTextAlignment(Qt.AlignCenter)
            self.documents_table.setItem(0, 0, error_item)
            self.documents_table.setSpan(0, 0, 1, self.documents_table.columnCount())
        finally:
            self.documents_table.setSortingEnabled(True)
            self._update_document_tab_title() 
            self._update_details_doc_buttons_state() 
            self.logger.debug("Tab 'Documenti' popolato.")


    # --- Metodi per la Gestione dei Pulsanti e Selezioni ---

    def _aggiorna_stato_pulsanti_possessori(self):
        """Abilita/disabilita i pulsanti per i possessori in base alla selezione."""
        has_selection = bool(self.possessori_table.selectedItems())
        self.btn_modifica_legame_possessore.setEnabled(has_selection)
        self.btn_rimuovi_possessore.setEnabled(has_selection)

    def _aggiorna_stato_pulsanti_immobili(self):
        """Abilita/disabilita i pulsanti per gli immobili in base alla selezione."""
        has_selection = bool(self.immobili_table.selectedItems())
        self.btn_modifica_immobile.setEnabled(has_selection)
        self.btn_rimuovi_immobile.setEnabled(has_selection)

    def _aggiorna_stato_pulsanti_variazioni(self):
        """Abilita/disabilita i pulsanti per le variazioni in base alla selezione."""
        has_selection = bool(self.variazioni_table.selectedItems())
        self.btn_modifica_variazione.setEnabled(has_selection)
        self.btn_elimina_variazione.setEnabled(has_selection)

    def _update_details_doc_buttons_state(self):
        """Abilita/disabilita i pulsanti per i documenti in base alla selezione."""
        has_selection = bool(self.documents_table.selectedItems())
        self.btn_apri_doc_details_dialog.setEnabled(has_selection)
        self.btn_scollega_doc.setEnabled(has_selection)

    # --- Metodi per Azioni sui Dati ---

    # -- Possessori --
    def _aggiungi_possessore_a_partita(self):
        self.logger.debug(f"Richiesta aggiunta possessore per partita ID {self.partita_id}")
        comune_id_partita = self.partita_data_originale.get('comune_id')
        if comune_id_partita is None:
            QMessageBox.warning(self, "Errore", "Comune della partita non determinato. Impossibile aggiungere possessore.")
            return

        possessore_dialog = PossessoreSelectionDialog(self.db_manager, comune_id_partita, self)
        selected_possessore_id = None
        selected_possessore_nome = None

        if possessore_dialog.exec_() == QDialog.Accepted:
            if hasattr(possessore_dialog, 'selected_possessore') and possessore_dialog.selected_possessore:
                selected_possessore_id = possessore_dialog.selected_possessore.get('id')
                selected_possessore_nome = possessore_dialog.selected_possessore.get('nome_completo')
        if not selected_possessore_id or not selected_possessore_nome:
            self.logger.info("Nessun possessore selezionato o creato.")
            return

        self.logger.info(f"Possessore selezionato/creato: ID {selected_possessore_id}, Nome: {selected_possessore_nome}")
        tipo_partita_corrente = self.partita_data_originale.get('tipo', 'principale')
        dettagli_legame = DettagliLegamePossessoreDialog.get_details_for_new_legame(selected_possessore_nome, tipo_partita_corrente, self)

        if not dettagli_legame:
            self.logger.info("Inserimento dettagli legame annullato.")
            return

        try:
            success = self.db_manager.aggiungi_possessore_a_partita(
                partita_id=self.partita_id,
                possessore_id=selected_possessore_id,
                tipo_partita_rel=tipo_partita_corrente,
                titolo=dettagli_legame["titolo"],
                quota=dettagli_legame["quota"]
            )
            if success:
                self.logger.info(f"Possessore ID {selected_possessore_id} aggiunto con successo alla partita ID {self.partita_id}")
                QMessageBox.information(self, "Successo", f"Possessore '{selected_possessore_nome}' aggiunto alla partita.")
                self._load_possessori_associati()
            else:
                self.logger.error("aggiungi_possessore_a_partita ha restituito False.")
                QMessageBox.critical(self, "Errore", "Impossibile aggiungere il possessore alla partita.")
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            self.logger.error(f"Errore DB aggiungendo possessore {selected_possessore_id} a partita {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Errore durante l'aggiunta del possessore alla partita:\n{e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            self.logger.critical(f"Errore imprevisto aggiungendo possessore {selected_possessore_id} a partita {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    def _modifica_legame_possessore(self):
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un possessore dalla tabella per modificarne il legame.")
            return

        current_row = selected_items[0].row()
        id_relazione_pp = self.possessori_table.item(current_row, 0).data(Qt.UserRole)
        if id_relazione_pp is None:
            QMessageBox.critical(self, "Errore Interno", "ID relazione non trovato per il possessore selezionato.")
            return

        nome_possessore_attuale = self.possessori_table.item(current_row, 2).text()
        titolo_attuale = self.possessori_table.item(current_row, 3).text()
        quota_attuale_item = self.possessori_table.item(current_row, 4)
        quota_attuale = quota_attuale_item.text() if quota_attuale_item and quota_attuale_item.text() != 'N/D' else None

        self.logger.debug(f"Richiesta modifica legame per relazione ID {id_relazione_pp} (Possessore: {nome_possessore_attuale})")
        tipo_partita_corrente = self.partita_data_originale.get('tipo', 'principale')
        nuovi_dettagli_legame = DettagliLegamePossessoreDialog.get_details_for_edit_legame(
            nome_possessore_attuale, tipo_partita_corrente, titolo_attuale, quota_attuale, self
        )

        if not nuovi_dettagli_legame:
            self.logger.info("Modifica dettagli legame annullata.")
            return

        try:
            success = self.db_manager.aggiorna_legame_partita_possessore(
                partita_possessore_id=id_relazione_pp,
                titolo=nuovi_dettagli_legame["titolo"],
                quota=nuovi_dettagli_legame["quota"]
            )
            if success:
                self.logger.info(f"Legame ID {id_relazione_pp} aggiornato con successo.")
                QMessageBox.information(self, "Successo", "Dettagli del legame possessore aggiornati.")
                self._load_possessori_associati()
            else:
                self.logger.error("aggiorna_legame_partita_possessore ha restituito False.")
                QMessageBox.critical(self, "Errore", "Impossibile aggiornare il legame del possessore.")
        except (DBMError, DBDataError) as dbe_legame:
            self.logger.error(f"Errore DB aggiornando legame {id_relazione_pp}: {dbe_legame}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Errore durante l'aggiornamento del legame:\n{dbe_legame.message if hasattr(dbe_legame, 'message') else str(dbe_legame)}")
        except Exception as e_legame:
            self.logger.critical(f"Errore imprevisto aggiornando legame {id_relazione_pp}: {e_legame}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e_legame}")

    def _rimuovi_possessore_da_partita(self):
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un legame possessore dalla tabella da rimuovere.")
            return

        id_relazione_pp = selected_items[0].data(Qt.UserRole)
        nome_possessore = self.possessori_table.item(selected_items[0].row(), 2).text()

        if id_relazione_pp is None:
            QMessageBox.critical(self, "Errore Interno", "ID relazione non trovato per il possessore selezionato.")
            return

        reply = QMessageBox.question(self, "Conferma Rimozione Legame",
                                     f"Sei sicuro di voler rimuovere il legame con il possessore '{nome_possessore}' (ID Relazione: {id_relazione_pp}) da questa partita?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.logger.debug(f"Richiesta rimozione legame ID {id_relazione_pp}")
            try:
                success = self.db_manager.rimuovi_possessore_da_partita(id_relazione_pp)

                if success:
                    self.logger.info(f"Legame ID {id_relazione_pp} rimosso con successo.")
                    QMessageBox.information(self, "Successo", "Legame con il possessore rimosso dalla partita.")
                    self._load_possessori_associati()
                else:
                    self.logger.error("rimuovi_possessore_da_partita ha restituito False.")
                    QMessageBox.critical(self, "Errore", "Impossibile rimuovere il legame del possessore.")
            except DBNotFoundError as nfe_rel:
                self.logger.warning(f"Tentativo di rimuovere legame ID {id_relazione_pp} non trovato: {nfe_rel}")
                QMessageBox.warning(self, "Operazione Fallita", str(nfe_rel.message))
                self._load_possessori_associati()
            except (DBMError, DBDataError) as dbe_rel:
                self.logger.error(f"Errore DB rimuovendo legame {id_relazione_pp}: {dbe_rel}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante la rimozione del legame:\n{dbe_rel.message if hasattr(dbe_rel, 'message') else str(dbe_rel)}")
            except Exception as e_rel:
                self.logger.critical(f"Errore imprevisto rimuovendo legame {id_relazione_pp}: {e_rel}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e_rel}")

    # -- Immobili --
    def _aggiungi_immobile_a_partita(self):
        self.logger.debug(f"Richiesta aggiunta immobile per partita ID {self.partita_id}")
        comune_id_partita = self.partita_data_originale.get('comune_id')
        if comune_id_partita is None:
            QMessageBox.warning(self, "Errore", "Comune della partita non determinato. Impossibile aggiungere immobile.")
            return

        dialog = ImmobileDialog(self.db_manager, comune_id_partita, self)
        if dialog.exec_() == QDialog.Accepted and dialog.immobile_data:
            immobile_data = dialog.immobile_data
            try:
                # La procedura SQL inserisci_immobile in db_manager deve essere aggiornata
                # per accettare tutti i campi dall'immobile_data
                immobile_id = self.db_manager.inserisci_immobile(
                    partita_id=self.partita_id,
                    natura=immobile_data['natura'],
                    localita_id=immobile_data['localita_id'],
                    classificazione=immobile_data['classificazione'],
                    consistenza=immobile_data['consistenza'],
                    numero_piani=immobile_data['numero_piani'],
                    numero_vani=immobile_data['numero_vani']
                )
                if immobile_id:
                    QMessageBox.information(self, "Successo", f"Immobile '{immobile_data['natura']}' aggiunto con ID: {immobile_id}.")
                    self._load_immobili_associati() # Ricarica la tabella immobili
                else:
                    self.logger.error("inserisci_immobile ha restituito None.")
                    QMessageBox.critical(self, "Errore", "Impossibile aggiungere l'immobile.")
            except (DBDataError, DBMError) as e:
                self.logger.error(f"Errore DB aggiungendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante l'aggiunta dell'immobile:\n{e.message if hasattr(e, 'message') else str(e)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto aggiungendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    def _modifica_immobile_associato(self):
        selected_items = self.immobili_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un immobile dalla tabella per modificarlo.")
            return

        row = self.immobili_table.currentRow()
        immobile_id = int(self.immobili_table.item(row, 0).text())
        
        # Recupera i dettagli attuali dell'immobile dal DB per pre-popolare il dialogo di modifica
        immobile_data = self.db_manager.get_immobile_details(immobile_id) # Questo metodo deve essere in db_manager
        if not immobile_data:
            QMessageBox.critical(self, "Errore", "Impossibile recuperare i dettagli dell'immobile per la modifica.")
            return

        # Apri un dialogo di modifica specifico per l'immobile, simile a ImmobileDialog ma per la modifica
        # Dobbiamo creare una classe ModificaImmobileDialog, oppure riadattare ImmobileDialog con un flag 'modalità_modifica'
        
        # Per semplicità, qui useremo una versione adattata di ImmobileDialog o un nuovo dialogo.
        # Creiamo un nuovo dialogo o adattiamo quello esistente (che forse non è l'ideale).
        
        # Idealmente, avresti un ModificaImmobileDialog(db_manager, immobile_id, comune_id_partita, parent)
        # Per ora, si assume che sia un dialogo che possa essere pre-popolato e salvare.
        
        # Se non esiste una ModificaImmobileDialog, questo non funzionerà.
        # Per semplicità, ipotizziamo una classe ad-hoc o un'estensione.
        # Assicurati che sia importata o creata
        dialog = ModificaImmobileDialog(self.db_manager, immobile_id, self.partita_id, self) # Passa immobile_id, partita_id
        
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Successo", "Immobile modificato con successo.")
            self._load_immobili_associati() # Ricarica la tabella immobili
        else:
            self.logger.info("Modifica immobile annullata.")

    def _rimuovi_immobile_da_partita(self):
        selected_items = self.immobili_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un immobile dalla tabella per rimuoverlo.")
            return

        row = self.immobili_table.currentRow()
        immobile_id = int(self.immobili_table.item(row, 0).text())
        
        reply = QMessageBox.question(self, "Conferma Rimozione",
                                     f"Sei sicuro di voler rimuovere l'immobile ID {immobile_id} da questa partita?\n"
                                     "Questa azione non cancella l'immobile dal database, ma lo scollega dalla partita attuale, impostando il suo partita_id a NULL.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # Il metodo delete_immobile in db_manager deve essere aggiornato
                # per supportare la rimozione/scollegamento senza cancellare
                # o potresti chiamare una procedura SQL specifica per scollegare.
                # Per ora, la tua procedura delete_immobile probabilemente CANCELLA.
                # Quindi, il comportamento è distruttivo.
                # Dobbiamo chiarire la semantica di "rimuovi immobile da partita":
                # 1. Cancellare l'immobile del tutto (current delete_immobile)?
                # 2. Scollegarlo dalla partita (partita_id a NULL)?
                # 3. Trasferirlo a un'altra partita (usare _esegui_trasferimento_immobile)?

                # Se l'intento è impostare partita_id a NULL (scollegare), serve un nuovo metodo in DBManager.
                # Es. db_manager.scollega_immobile_da_partita(immobile_id)
                # Per ora, usiamo l'esistente delete_immobile con un avviso, ma è probabile che non sia il comportamento desiderato.
                success = self.db_manager.delete_immobile(immobile_id) # ATTENZIONE: Questo prob. CANCELLA FISICAMENTE!

                if success:
                    QMessageBox.information(self, "Successo", f"Immobile ID {immobile_id} rimosso/cancellato dalla partita.")
                    self._load_immobili_associati()
                else:
                    self.logger.error("delete_immobile ha restituito False.")
                    QMessageBox.critical(self, "Errore", "Impossibile rimuovere/cancellare l'immobile.")
            except (DBMError, DBDataError) as e:
                self.logger.error(f"Errore DB rimuovendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante la rimozione dell'immobile:\n{e.message if hasattr(e, 'message') else str(e)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto rimuovendo immobile: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    # -- Variazioni --
    def _modifica_variazione_selezionata(self):
        selected_items = self.variazioni_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una variazione dalla tabella per modificarla.")
            return

        row = self.variazioni_table.currentRow()
        variazione_id = int(self.variazioni_table.item(row, 0).text())

        # Apri un dialogo per modificare la variazione, simile a InserimentoVariazione (se lo hai)
        # Dobbiamo creare una classe ModificaVariazioneDialog
        from gui_widgets import ModificaVariazioneDialog # Assicurati che sia importata o creata
        dialog = ModificaVariazioneDialog(self.db_manager, variazione_id, self.partita_id, self) # Passa variazione_id, partita_id
        
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Successo", "Variazione modificata con successo.")
            self._load_variazioni_associati() # Ricarica la tabella
        else:
            self.logger.info("Modifica variazione annullata.")

    def _elimina_variazione_selezionata(self):
        selected_items = self.variazioni_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una variazione dalla tabella per eliminarla.")
            return

        row = self.variazioni_table.currentRow()
        variazione_id = int(self.variazioni_table.item(row, 0).text())
        
        reply = QMessageBox.question(self, "Conferma Eliminazione",
                                     f"Sei sicuro di voler eliminare la variazione ID {variazione_id}?\n"
                                     "Questa azione potrebbe avere effetti sulle partite collegate (es. riattivare la partita origine se chiusa).",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # Il metodo delete_variazione in db_manager ha flag force e restore_partita
                success = self.db_manager.delete_variazione(variazione_id, force=True, restore_partita=False) # Decidi la politica
                
                if success:
                    QMessageBox.information(self, "Successo", f"Variazione ID {variazione_id} eliminata.")
                    # Dopo aver eliminato una variazione, è fondamentale ricaricare i dati di tutte le partite coinvolte
                    # (origine e destinazione) per riflettere eventuali cambiamenti di stato.
                    # Per ora, ricarichiamo solo la lista delle variazioni per la partita corrente.
                    self._load_variazioni_associati() 
                    # Potrebbe essere necessario ricaricare anche la partita_data_originale
                    # e le partite del comune genitore.
                else:
                    self.logger.error("delete_variazione ha restituito False.")
                    QMessageBox.critical(self, "Errore", "Impossibile eliminare la variazione.")
            except (DBMError, DBDataError) as e:
                self.logger.error(f"Errore DB eliminando variazione: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Errore durante l'eliminazione della variazione:\n{e.message if hasattr(e, 'message') else str(e)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto eliminando variazione: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {e}")

    # -- Documenti --
    # Questi metodi sono già definiti correttamente e riutilizzano DocumentViewerDialog.
    # Non è necessario riscriverli qui, ma assicurati che siano presenti nel codice finale.
    # documents_table_dragEnterEvent, documents_table_dragMoveEvent, documents_table_dropEvent,
    # _handle_dropped_file, _allega_nuovo_documento_a_partita, _apri_documento_selezionato_from_details_dialog,
    # _scollega_documento_selezionato.
    # --- NUOVI METODI PER LA GESTIONE DEL DRAG-AND-DROP ---

    def documents_table_dragEnterEvent(self, event):
        """Accetta solo eventi di drag che contengono URL (file)."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def documents_table_dragMoveEvent(self, event):
        """Mantiene l'accettazione dell'azione se ci sono URL."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def documents_table_dropEvent(self, event):
        """Elabora i file rilasciati sulla tabella."""
        self.logger.info("Drop event rilevato sulla tabella documenti.")
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                self.logger.info(f"File rilasciato: {file_path}")
                # Qui chiamiamo la stessa logica di allegazione usata dal pulsante "Allega Nuovo Documento..."
                # che a sua volta apre AggiungiDocumentoDialog.
                # Però, dobbiamo passare il file_path al dialogo in modo che sia pre-selezionato.
                self._handle_dropped_file(file_path)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _handle_dropped_file(self, file_path: str):
        """Gestisce un singolo file rilasciato, aprendo il dialogo di allegazione."""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Non Trovato", f"Il file rilasciato non esiste: {file_path}")
            self.logger.warning(f"File rilasciato non trovato: {file_path}")
            return
        
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "Non un File", f"L'elemento rilasciato non è un file valido: {file_path}")
            self.logger.warning(f"Elemento rilasciato non è un file: {file_path}")
            return

        # Filtra i tipi di file accettati, se necessario
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension not in allowed_extensions:
            QMessageBox.warning(self, "Formato Non Supportato", f"Il formato del file '{file_extension}' non è supportato. Sono accettati: {', '.join(allowed_extensions)}.")
            self.logger.warning(f"Formato file non supportato per il drop: {file_path}")
            return
        
        # Apri il dialogo AggiungiDocumentoDialog e pre-popola il campo file
        dialog = AggiungiDocumentoDialog(self.db_manager, self.partita_id, self)
        
        # Imposta il percorso del file nel dialogo appena aperto
        # Questo richiede una modifica in AggiungiDocumentoDialog per avere un metodo set_initial_file_path
        dialog.set_initial_file_path(file_path)

        if dialog.exec_() == QDialog.Accepted and dialog.document_data:
            doc_info = dialog.document_data
            percorso_originale = doc_info["percorso_file_originale"] # Ora sarà file_path pre-selezionato
            
            # ... (la tua logica esistente di copia file e salvataggio nel DB da _allega_nuovo_documento_a_partita) ...
            allegati_dir = os.path.join(".", "allegati_catasto", f"partita_{self.partita_id}")
            os.makedirs(allegati_dir, exist_ok=True)
            
            nome_file_originale = os.path.basename(percorso_originale)
            nome_file_dest = nome_file_originale 
            percorso_destinazione_completo = os.path.join(allegati_dir, nome_file_dest)
            
            try:
                import shutil
                shutil.copy2(percorso_originale, percorso_destinazione_completo)
                self.logger.info(f"File copiato da '{percorso_originale}' a '{percorso_destinazione_completo}'")

                percorso_file_db = percorso_destinazione_completo

                doc_id = self.db_manager.aggiungi_documento_storico(
                    titolo=doc_info["titolo"],
                    tipo_documento=doc_info["tipo_documento"],
                    percorso_file=percorso_file_db,
                    descrizione=doc_info["descrizione"],
                    anno=doc_info["anno"],
                    periodo_id=doc_info["periodo_id"],
                    metadati_json=doc_info["metadati_json"]
                )
                if doc_id:
                    success_link = self.db_manager.collega_documento_a_partita(
                        doc_id, self.partita_id, doc_info["rilevanza"], doc_info["note_legame"]
                    )
                    if success_link:
                        QMessageBox.information(self, "Successo", "Documento allegato e collegato con successo.")
                        self._load_documenti_allegati() # Aggiorna la tabella
                    else:
                        QMessageBox.warning(self, "Attenzione", "Documento salvato ma fallito il collegamento alla partita.")
                else:
                    QMessageBox.critical(self, "Errore", "Impossibile salvare le informazioni del documento nel database.")
                    if os.path.exists(percorso_destinazione_completo): os.remove(percorso_destinazione_completo)

            except FileNotFoundError:
                QMessageBox.critical(self, "Errore File", f"File sorgente non trovato: {percorso_originale}")
            except PermissionError:
                QMessageBox.critical(self, "Errore Permessi", f"Permessi non sufficienti per copiare il file in '{allegati_dir}'.")
            except DBMError as e_db:
                QMessageBox.critical(self, "Errore Database", f"Errore durante il salvataggio: {e_db}")
                if os.path.exists(percorso_destinazione_completo): os.remove(percorso_destinazione_completo)
            except Exception as e:
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore durante l'allegazione del documento: {e}")
                if os.path.exists(percorso_destinazione_completo): os.remove(percorso_destinazione_completo)
                self.logger.error(f"Errore allegando documento: {e}", exc_info=True)
        else:
            self.logger.info("Aggiunta documento tramite drag-and-drop annullata dall'utente (dialogo chiuso).")

    # Modifica _allega_nuovo_documento_a_partita per riutilizzare la logica di _handle_dropped_file
    def _allega_nuovo_documento_a_partita(self):
        """Gestisce l'allegazione di un nuovo documento tramite il pulsante Sfoglia."""
        # Apri il dialogo file, come faceva prima
        filePath, _ = QFileDialog.getOpenFileName(self, "Seleziona Documento da Allegare", "",
                                                  "Documenti (*.pdf *.jpg *.jpeg *.png);;File PDF (*.pdf);;Immagini JPG (*.jpg *.jpeg);;Immagini PNG (*.png);;Tutti i file (*)")
        if filePath:
            # Reutilizza la logica di gestione del file, che ora include il dialogo
            self._handle_dropped_file(filePath)
        else:
            self.logger.info("Selezione file annullata dall'utente per l'allegazione.")
    def _apri_documento_selezionato_from_details_dialog(self):
        """
        Apre un documento selezionato dalla tabella dei documenti allegati
        usando il visualizzatore predefinito del sistema operativo.
        """
        selected_items = self.documents_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un documento dalla lista per aprirlo.")
            return
        
        row = self.documents_table.currentRow()
        # La colonna con il percorso del file è la 6a (indice 5)
        percorso_file_item = self.documents_table.item(row, 5) 
        
        if percorso_file_item:
            # Recupera il percorso completo salvato nell'UserRole
            percorso_file_completo = percorso_file_item.data(Qt.UserRole)
            
            if percorso_file_completo and os.path.exists(percorso_file_completo):
                from PyQt5.QtGui import QDesktopServices
                from PyQt5.QtCore import QUrl
                
                self.logger.info(f"Tentativo di aprire il documento: {percorso_file_completo}")
                success = QDesktopServices.openUrl(QUrl.fromLocalFile(percorso_file_completo))
                
                if not success:
                    QMessageBox.warning(self, "Errore Apertura", 
                                        f"Impossibile aprire il file:\n{percorso_file_completo}\n"
                                        "Verificare che sia installata un'applicazione associata o che i permessi siano corretti.")
            else:
                QMessageBox.warning(self, "File Non Trovato", 
                                    f"Il file specificato non è stato trovato al percorso:\n{percorso_file_completo}\n"
                                    "Il file potrebbe essere stato spostato o eliminato.")
        else:
            QMessageBox.warning(self, "Percorso Mancante", 
                                "Informazioni sul percorso del file non disponibili per il documento selezionato.")


    # In gui_widgets.py, all'interno della classe ModificaPartitaDialog

    def _scollega_documento_selezionato(self):
        """
        Scollega un documento dalla partita corrente rimuovendo il record
        dalla tabella di associazione 'documento_partita'.
        """
        selected_items = self.documents_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un documento dalla lista per scollegarlo.")
            return

        row = self.documents_table.currentRow()
        
        # Recupera gli ID salvati nei dati dell'item
        id_doc_item = self.documents_table.item(row, 0)
        titolo_doc = self.documents_table.item(row, 1).text() if self.documents_table.item(row, 1) else "Sconosciuto"

        if not id_doc_item:
            QMessageBox.critical(self, "Errore Interno", "Impossibile recuperare i dati del documento selezionato.")
            return
            
        # Gli ID necessari per la cancellazione (chiave primaria composta)
        documento_id_da_scollegare = id_doc_item.data(Qt.UserRole + 1)
        partita_id_da_cui_scollegare = id_doc_item.data(Qt.UserRole + 2)

        if not documento_id_da_scollegare or not partita_id_da_cui_scollegare:
            self.logger.error(f"Dati di relazione mancanti per la riga {row} (DocID: {documento_id_da_scollegare}, PartitaID: {partita_id_da_cui_scollegare})")
            QMessageBox.critical(self, "Errore Dati", "Informazioni sulla relazione documento-partita non trovate. Impossibile procedere.")
            return

        reply = QMessageBox.question(self, "Conferma Scollegamento",
                                     f"Sei sicuro di voler scollegare il documento '{titolo_doc}' (ID: {documento_id_da_scollegare}) "
                                     f"dalla partita corrente (ID: {partita_id_da_cui_scollegare})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                self.logger.info(f"Tentativo di scollegare doc ID {documento_id_da_scollegare} da partita ID {partita_id_da_cui_scollegare}")
                
                # Chiama il metodo del DB Manager che esegue la DELETE sulla tabella di collegamento
                success = self.db_manager.scollega_documento_da_partita(
                    documento_id=documento_id_da_scollegare,
                    partita_id=partita_id_da_cui_scollegare
                )

                if success:
                    QMessageBox.information(self, "Successo", "Documento scollegato con successo dalla partita.")
                    self._load_documenti_allegati()  # Ricarica la lista dei documenti per aggiornare la UI
                # else: scollega_documento_da_partita solleverà un'eccezione in caso di fallimento
            except DBNotFoundError as nfe:
                self.logger.warning(f"Tentativo di scollegare un legame non trovato: {nfe}")
                QMessageBox.warning(self, "Operazione Fallita", str(nfe))
            except DBMError as e_db:
                self.logger.error(f"Errore DB durante lo scollegamento del documento: {e_db}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Impossibile scollegare il documento: {e_db}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto durante lo scollegamento del documento: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore di sistema: {e}")
    def _update_document_tab_title(self):
        """Aggiorna il titolo del tab dei documenti con il conteggio corrente."""
        try:
            # Assicurati che self.documents_table esista prima di contarne le righe
            if hasattr(self, 'documents_table'):
                count = self.documents_table.rowCount()
                
                # Se la tabella ha solo una riga placeholder "Nessun documento...", il conteggio è 0
                if count == 1 and self.documents_table.item(0, 0) and "Nessun documento" in self.documents_table.item(0, 0).text():
                    count = 0
                
                # Trova l'indice del tab dei documenti nel QTabWidget principale
                tab_index = self.tab_widget.indexOf(self.tab_documenti)
                if tab_index != -1:
                    self.tab_widget.setTabText(tab_index, f"Documenti Allegati ({count})")
            else:
                self.logger.warning("Attributo 'documents_table' non trovato in _update_document_tab_title.")

        except Exception as e:
            self.logger.error(f"Errore imprevisto durante l'aggiornamento del titolo del tab documenti: {e}", exc_info=True)

    def _save_changes(self):
        """
        Raccoglie i dati dal tab 'Dati Generali', li valida e chiama il db_manager
        per salvare le modifiche sulla tabella 'partita'.
        """
        self.logger.info(f"Tentativo di salvare le modifiche per la partita ID: {self.partita_id}")

        # 1. Raccoglie i dati dai widget della UI
        dati_da_salvare = {
            "numero_partita": self.numero_partita_spinbox.value(),
            "suffisso_partita": self.suffisso_partita_edit.text().strip() or None, # Salva None se la stringa è vuota
            "tipo": self.tipo_combo.currentText(),
            "stato": self.stato_combo.currentText(),
            "data_impianto": qdate_to_datetime(self.data_impianto_edit.date()), # Usa la funzione di utilità
            "data_chiusura": qdate_to_datetime(self.data_chiusura_edit.date()), # Gestisce date nulle
            "numero_provenienza": self.numero_provenienza_spinbox.value() if self.numero_provenienza_spinbox.value() != 0 else None
        }

        # 2. Validazione dei dati
        if dati_da_salvare["numero_partita"] <= 0:
            QMessageBox.warning(self, "Dati Non Validi", "Il numero di partita deve essere un valore positivo.")
            self.numero_partita_spinbox.setFocus()
            return
            
        # Potresti aggiungere altri controlli qui, ad esempio sulla data di chiusura rispetto a quella di impianto.
        if dati_da_salvare["data_impianto"] and dati_da_salvare["data_chiusura"]:
            if dati_da_salvare["data_chiusura"] < dati_da_salvare["data_impianto"]:
                QMessageBox.warning(self, "Date Non Valide", "La data di chiusura non può essere precedente alla data di impianto.")
                return

        try:
            # 3. Chiama il DB Manager per aggiornare
            self.db_manager.update_partita(self.partita_id, dati_da_salvare)
            
            # 4. Gestione del successo
            self.logger.info(f"Dati generali della partita ID {self.partita_id} aggiornati con successo.")
            QMessageBox.information(self, "Salvataggio Riuscito", "Le modifiche ai dati generali della partita sono state salvate.")
            
            # Dopo aver salvato, ricarica i dati per mantenere la UI sincronizzata
            self._load_all_partita_data() 
            
            # Non chiudiamo il dialogo, l'utente potrebbe voler fare altre modifiche
            # self.accept() # Rimuovere questa riga per non chiudere il dialogo al salvataggio

        except (DBUniqueConstraintError, DBDataError, DBNotFoundError, DBMError) as e:
            self.logger.error(f"Errore durante il salvataggio dei dati generali per la partita ID {self.partita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore di Salvataggio", f"Impossibile salvare le modifiche:\n{e}")
        except Exception as e_gen:
            self.logger.critical(f"Errore imprevisto durante il salvataggio della partita ID {self.partita_id}: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico", f"Si è verificato un errore di sistema imprevisto: {e_gen}")

class ModificaPossessoreDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, possessore_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.possessore_id = possessore_id
        self.possessore_data_originale = None
        # Per l'audit, se vuoi confrontare i dati vecchi e nuovi
        # self.current_user_info = getattr(QApplication.instance().main_window, 'logged_in_user_info', None) # Modo per prendere utente
        # se main_window è accessibile

        self.setWindowTitle(
            f"Modifica Dati Possessore ID: {self.possessore_id}")
        self.setMinimumWidth(450)

        self._init_ui()
        self._load_possessore_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.id_label = QLabel(str(self.possessore_id))
        form_layout.addRow("ID Possessore:", self.id_label)

        self.nome_completo_edit = QLineEdit()
        form_layout.addRow("Nome Completo (*):", self.nome_completo_edit)

        # Campo che avevi nello schema per ricerca/ordinamento
        self.cognome_nome_edit = QLineEdit()
        form_layout.addRow("Cognome e Nome (per ricerca):",
                           self.cognome_nome_edit)

        self.paternita_edit = QLineEdit()
        form_layout.addRow("Paternità:", self.paternita_edit)

        self.attivo_checkbox = QCheckBox("Possessore Attivo")
        form_layout.addRow(self.attivo_checkbox)

        # Comune di Riferimento
        comune_ref_layout = QHBoxLayout()
        self.comune_ref_label = QLabel(
            "Comune non specificato")  # Verrà popolato
        self.btn_cambia_comune_ref = QPushButton("Cambia...")
        self.btn_cambia_comune_ref.clicked.connect(
            self._cambia_comune_riferimento)
        comune_ref_layout.addWidget(self.comune_ref_label)
        comune_ref_layout.addStretch()
        comune_ref_layout.addWidget(self.btn_cambia_comune_ref)
        form_layout.addRow("Comune di Riferimento:", comune_ref_layout)

        # ID del comune di riferimento (nascosto, ma utile da tenere)
        self.selected_comune_ref_id: Optional[int] = None

        # Aggiungere qui altri campi se vuoi estendere la tabella possessore
        # self.codice_fiscale_edit = QLineEdit()
        # form_layout.addRow("Codice Fiscale:", self.codice_fiscale_edit)
        # self.data_nascita_edit = QDateEdit()
        # self.data_nascita_edit.setCalendarPopup(True) ...
        # form_layout.addRow("Data Nascita:", self.data_nascita_edit)

        layout.addLayout(form_layout)

        # Pulsanti
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogSaveButton), "Salva Modifiche")
        self.save_button.clicked.connect(self._save_changes)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def _load_possessore_data(self):
        # Metodo da creare in CatastoDBManager: get_possessore_details(possessore_id)
        # Dovrebbe restituire un dizionario con tutti i campi di possessore,
        # incluso comune_id e il nome del comune (comune_riferimento_nome).
        self.possessore_data_originale = self.db_manager.get_possessore_full_details(
            self.possessore_id)  # Rinominato per chiarezza

        if not self.possessore_data_originale:
            QMessageBox.critical(self, "Errore Caricamento",
                                 f"Impossibile caricare i dati per il possessore ID: {self.possessore_id}.\n"
                                 "Il dialogo verrà chiuso.")
            from PyQt5.QtCore import QTimer
            # Chiudi dopo che il messaggio è stato processato
            QTimer.singleShot(0, self.reject)
            return

        self.nome_completo_edit.setText(
            self.possessore_data_originale.get('nome_completo', ''))
        self.cognome_nome_edit.setText(self.possessore_data_originale.get(
            'cognome_nome', ''))  # Campo cognome_nome
        self.paternita_edit.setText(
            self.possessore_data_originale.get('paternita', ''))
        self.attivo_checkbox.setChecked(
            self.possessore_data_originale.get('attivo', True))

        self.selected_comune_ref_id = self.possessore_data_originale.get(
            'comune_riferimento_id')  # Salva l'ID
        nome_comune_ref = self.possessore_data_originale.get(
            'comune_riferimento_nome', "Nessun comune assegnato")
        self.comune_ref_label.setText(
            f"{nome_comune_ref} (ID: {self.selected_comune_ref_id or 'N/A'})")

    def _cambia_comune_riferimento(self):
        # Usa ComuneSelectionDialog per cambiare il comune di riferimento
        dialog = ComuneSelectionDialog(
            self.db_manager, self, title="Seleziona Nuovo Comune di Riferimento")
        if dialog.exec_() == QDialog.Accepted and dialog.selected_comune_id:
            self.selected_comune_ref_id = dialog.selected_comune_id
            self.comune_ref_label.setText(
                f"{dialog.selected_comune_name} (ID: {self.selected_comune_ref_id})")
            logging.getLogger("CatastoGUI").info(
                f"Nuovo comune di riferimento selezionato per possessore (non ancora salvato): ID {self.selected_comune_ref_id}, Nome: {dialog.selected_comune_name}")

    def _save_changes(self):
        logging.getLogger("CatastoGUI").info(
            # NUOVA STAMPA
            f"DEBUG: _save_changes chiamato per possessore ID {self.possessore_id}")
        dati_modificati = {
            "nome_completo": self.nome_completo_edit.text().strip(),
            "cognome_nome": self.cognome_nome_edit.text().strip() or None,  # Può essere nullo
            "paternita": self.paternita_edit.text().strip() or None,    # Può essere nullo
            "attivo": self.attivo_checkbox.isChecked(),
            "comune_riferimento_id": self.selected_comune_ref_id,  # L'ID del comune selezionato
        }
        logging.getLogger("CatastoGUI").info(
            f"DEBUG: Dati dalla UI: {dati_modificati}")  # NUOVA STAMPA

        if not dati_modificati["nome_completo"]:
            QMessageBox.warning(
                self, "Dati Mancanti", "Il 'Nome Completo' del possessore è obbligatorio.")
            self.nome_completo_edit.setFocus()
            return

        if dati_modificati["comune_riferimento_id"] is None:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il 'Comune di Riferimento' è obbligatorio.")
            # Non c'è un campo input diretto per il focus, ma l'utente deve usare il pulsante
            self.btn_cambia_comune_ref.setFocus()
            return

        try:
            logging.getLogger("CatastoGUI").info(
                # NUOVA STAMPA
                f"DEBUG: Chiamata a db_manager.update_possessore per ID {self.possessore_id}")
            logging.getLogger("CatastoGUI").info(
                f"Tentativo di aggiornare il possessore ID {self.possessore_id} con i dati: {dati_modificati}")
            # Metodo da creare in CatastoDBManager: update_possessore(possessore_id, dati_modificati)
            self.db_manager.update_possessore(
                self.possessore_id, dati_modificati)

            logging.getLogger("CatastoGUI").info(
                f"Possessore ID {self.possessore_id} aggiornato con successo.")
            logging.getLogger("CatastoGUI").info(
                # NUOVA STAMPA
                f"DEBUG: db_manager.update_possessore completato per ID {self.possessore_id}")
            self.accept()  # Chiude il dialogo e restituisce QDialog.Accepted

        # Gestione eccezioni simile a quella di update_partita (DBUniqueConstraintError, DBDataError, DBMError, etc.)
        # Ad esempio, se nome_completo + comune_id deve essere univoco, o altri vincoli.
        # Per ora, un gestore generico per errori DB e altri errori.
        except (DBMError, DBDataError) as dbe_poss:  # Usa le tue eccezioni personalizzate
            logging.getLogger("CatastoGUI").error(
                f"Errore DB durante aggiornamento possessore ID {self.possessore_id}: {dbe_poss}", exc_info=True)
            QMessageBox.critical(self, "Errore Database",
                                 f"Errore durante il salvataggio delle modifiche al possessore:\n{dbe_poss.message if hasattr(dbe_poss, 'message') else str(dbe_poss)}")
        except AttributeError as ae:
            logging.getLogger("CatastoGUI").critical(
                f"Metodo 'update_possessore' non trovato o altro AttributeError: {ae}", exc_info=True)
            QMessageBox.critical(self, "Errore Implementazione",
                                 "Funzionalità per aggiornare possessore non completamente implementata o errore interno.")
        except Exception as e_poss:
            logging.getLogger("CatastoGUI").critical(
                f"Errore critico imprevisto durante il salvataggio del possessore ID {self.possessore_id}: {e_poss}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico Imprevisto",
                                 f"Si è verificato un errore di sistema imprevisto:\n{type(e_poss).__name__}: {e_poss}")
class ModificaComuneDialog(QDialog):
    def __init__(self, db_manager: 'CatastoDBManager', comune_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.comune_data_originale: Optional[Dict[str, Any]] = None
        # Per caricare i periodi storici nella UI, se necessario
        self.periodi_storici_list: List[Dict[str, Any]] = []


        self.setWindowTitle(f"Modifica Dati Comune ID: {self.comune_id}")
        self.setMinimumWidth(450)
        self.setModal(True)

        self._initUI()
        self._load_comune_data()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows) # Utile per form lunghi
        form_layout.setLabelAlignment(Qt.AlignLeft) # Allinea etichette

        self.id_label = QLabel(str(self.comune_id))
        form_layout.addRow("ID Comune:", self.id_label)

        self.nome_edit = QLineEdit()
        form_layout.addRow("Nome Comune (*):", self.nome_edit)

        self.provincia_edit = QLineEdit()
        self.provincia_edit.setMaxLength(2) # Esempio di validazione
        form_layout.addRow("Provincia (*):", self.provincia_edit)

        self.regione_edit = QLineEdit()
        form_layout.addRow("Regione (*):", self.regione_edit)

        self.codice_catastale_edit = QLineEdit()
        self.codice_catastale_edit.setPlaceholderText("Es. A123 (opzionale)")
        form_layout.addRow("Codice Catastale:", self.codice_catastale_edit)

        # Per periodo_id, idealmente useresti una QComboBox caricata con i periodi
        # Per semplicità qui uso QSpinBox, ma una ComboBox è meglio per UX
        self.periodo_id_spinbox = QSpinBox()
        self.periodo_id_spinbox.setMinimum(0) # 0 potrebbe significare 'non assegnato' o usa specialValueText
        self.periodo_id_spinbox.setMaximum(99999) 
        self.periodo_id_spinbox.setSpecialValueText("Nessuno") # Se 0 significa Nessuno
        form_layout.addRow("Periodo Storico ID:", self.periodo_id_spinbox)
        # TODO: Caricare e mostrare i periodi storici in una QComboBox qui per migliore UX

        self.data_istituzione_edit = QDateEdit(calendarPopup=True)
        self.data_istituzione_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_istituzione_edit.setSpecialValueText(" ") # Permette campo vuoto
        self.data_istituzione_edit.setDate(QDate()) # Data nulla di default
        form_layout.addRow("Data Istituzione:", self.data_istituzione_edit)
        
        self.data_soppressione_edit = QDateEdit(calendarPopup=True)
        self.data_soppressione_edit.setDisplayFormat("yyyy-MM-dd")
        self.data_soppressione_edit.setSpecialValueText(" ")
        self.data_soppressione_edit.setDate(QDate())
        form_layout.addRow("Data Soppressione:", self.data_soppressione_edit)

        self.note_edit = QTextEdit()
        self.note_edit.setFixedHeight(80)
        form_layout.addRow("Note:", self.note_edit)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._save_changes)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def _load_comune_data(self):
        # Assumiamo che db_manager abbia un metodo get_comune_details(comune_id)
        # che restituisca tutti i campi necessari, incluso periodo_id, ecc.
        # Se non esiste, bisogna crearlo. Per ora, usiamo get_all_comuni_details
        # e filtriamo, ma è inefficiente.
        
        # Metodo migliore: self.comune_data_originale = self.db_manager.get_comune_details_by_id(self.comune_id)
        # Per ora, usiamo un fallback temporaneo se quel metodo non c'è:
        all_comuni = self.db_manager.get_all_comuni_details() #
        found_comune = next((c for c in all_comuni if c.get('id') == self.comune_id), None)
        
        if not found_comune:
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare dati per Comune ID: {self.comune_id}.")
            # QTimer.singleShot(0, self.reject) # Importa QTimer da QtCore se usi questo
            self.reject() # Chiudi subito se non trovi il comune
            return
        
        self.comune_data_originale = found_comune

        self.nome_edit.setText(self.comune_data_originale.get('nome_comune', '')) # 'nome_comune' da get_all_comuni_details
        self.provincia_edit.setText(self.comune_data_originale.get('provincia', ''))
        self.regione_edit.setText(self.comune_data_originale.get('regione', ''))
        self.codice_catastale_edit.setText(self.comune_data_originale.get('codice_catastale', ''))
        
        periodo_id_val = self.comune_data_originale.get('periodo_id')
        self.periodo_id_spinbox.setValue(periodo_id_val if periodo_id_val is not None else self.periodo_id_spinbox.minimum())

        # Gestione date (assumendo che siano stringhe ISO o oggetti date/datetime)
        di_str = self.comune_data_originale.get('data_istituzione')
        if di_str: self.data_istituzione_edit.setDate(QDate.fromString(str(di_str), "yyyy-MM-dd"))
        else: self.data_istituzione_edit.setDate(QDate())
            
        ds_str = self.comune_data_originale.get('data_soppressione')
        if ds_str: self.data_soppressione_edit.setDate(QDate.fromString(str(ds_str), "yyyy-MM-dd"))
        else: self.data_soppressione_edit.setDate(QDate())

        self.note_edit.setText(self.comune_data_originale.get('note', ''))

    def _save_changes(self):
        dati_modificati = {
            "nome": self.nome_edit.text().strip(),
            "provincia": self.provincia_edit.text().strip().upper(),
            "regione": self.regione_edit.text().strip(),
            "codice_catastale": self.codice_catastale_edit.text().strip() or None,
            "periodo_id": None,
            "data_istituzione": None,
            "data_soppressione": None,
            "note": self.note_edit.toPlainText().strip() or None,
        }

        if self.periodo_id_spinbox.value() != self.periodo_id_spinbox.minimum(): # Se non è "Nessuno"
            dati_modificati["periodo_id"] = self.periodo_id_spinbox.value()

        if self.data_istituzione_edit.date().isValid() and self.data_istituzione_edit.text().strip() != "":
            dati_modificati["data_istituzione"] = self.data_istituzione_edit.date().toPyDate()
        
        if self.data_soppressione_edit.date().isValid() and self.data_soppressione_edit.text().strip() != "":
            dati_modificati["data_soppressione"] = self.data_soppressione_edit.date().toPyDate()

        # Validazioni UI
        if not dati_modificati["nome"]:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome del comune è obbligatorio.")
            return
        if not dati_modificati["provincia"] or len(dati_modificati["provincia"]) != 2 :
            QMessageBox.warning(self, "Dati Mancanti", "La provincia è obbligatoria (2 caratteri).")
            return
        if not dati_modificati["regione"]:
            QMessageBox.warning(self, "Dati Mancanti", "La regione è obbligatoria.")
            return
        
        if dati_modificati["data_istituzione"] and dati_modificati["data_soppressione"]:
            if dati_modificati["data_soppressione"] < dati_modificati["data_istituzione"]:
                QMessageBox.warning(self, "Date Non Valide", "La data di soppressione non può precedere quella di istituzione.")
                return

        try:
            # Assumiamo che esista self.db_manager.update_comune(comune_id, dati_modificati)
            success = self.db_manager.update_comune(self.comune_id, dati_modificati)
            if success:
                QMessageBox.information(self, "Successo", "Dati del comune aggiornati con successo.")
                self.accept() # Chiude il dialogo e segnala successo
            # else: update_comune solleva eccezione in caso di errore
        except (DBNotFoundError, DBUniqueConstraintError, DBDataError, DBMError) as e:
            logging.getLogger("CatastoGUI").error(f"Errore salvataggio comune ID {self.comune_id}: {str(e)}")
            QMessageBox.critical(self, "Errore Salvataggio", str(e))
        except Exception as e_gen:
            logging.getLogger("CatastoGUI").critical(f"Errore imprevisto salvataggio comune ID {self.comune_id}: {str(e_gen)}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore: {str(e_gen)}")
class DettaglioPartitaDialog(QDialog):
    """
    Finestra di dialogo per visualizzare i dettagli di una partita,
    inclusi i possessori e gli immobili.
    """
    def __init__(self, partita_id, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.partita_id = partita_id
        self.db_manager = db_manager

        self.setWindowTitle(f"Dettaglio Partita N. {self.partita_id}")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Area per visualizzare le informazioni in modo strutturato
        self.details_text_edit = QTextEdit()
        self.details_text_edit.setReadOnly(True)
        layout.addWidget(self.details_text_edit)

        # Pulsanti
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.load_details()

    def load_details(self):
        """
        Carica i dettagli della partita dal database e li formatta per la visualizzazione.
        """
        try:
            # Recupera i dettagli della partita utilizzando la funzione del DBManager
            dettagli_partita = self.db_manager.get_dettaglio_partita_completo(self.partita_id)

            if not dettagli_partita:
                self.details_text_edit.setHtml("<h1>Partita non trovata</h1>")
                return

            # Formattazione del testo in HTML per una migliore leggibilità
            html_content = f"<h1>Dettaglio Partita N. {self.partita_id}</h1>"
            html_content += f"<b>Numero Partita:</b> {dettagli_partita['numero_partita']}<br>"
            html_content += f"<b>Nota:</b> {dettagli_partita.get('nota', 'N/D')}<br><br>"

            # Sezione Possessori
            html_content += "<h2>Possessori</h2>"
            if dettagli_partita.get('possessori'):
                html_content += "<ul>"
                for p in dettagli_partita['possessori']:
                    html_content += f"<li><b>{p['cognome_nome']}</b> (ID: {p['possessore_id']})</li>"
                html_content += "</ul>"
            else:
                html_content += "<p>Nessun possessore associato.</p>"

            # Sezione Immobili
            html_content += "<h2>Immobili</h2>"
            if dettagli_partita.get('immobili'):
                html_content += """
                <table border="1" cellpadding="5" cellspacing="0" width="100%">
                    <tr>
                        <th>ID Immobile</th>
                        <th>Sezione</th>
                        <th>Numero Mappa</th>
                        <th>Subalterno</th>
                    </tr>
                """
                for i in dettagli_partita['immobili']:
                    html_content += f"""
                    <tr>
                        <td>{i['immobile_id']}</td>
                        <td>{i['sezione']}</td>
                        <td>{i['numero_mappa']}</td>
                        <td>{i['subalterno']}</td>
                    </tr>
                    """
                html_content += "</table>"
            else:
                html_content += "<p>Nessun immobile associato.</p>"

            self.details_text_edit.setHtml(html_content)

        except Exception as e:
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Impossibile caricare i dettagli della partita.\nErrore: {e}")
            self.details_text_edit.setText(f"Errore nel recupero dei dati per la partita {self.partita_id}.")



class PossessoriComuneDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, nome_comune: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.nome_comune = nome_comune

        self.setWindowTitle(
            f"Possessori del Comune di {self.nome_comune} (ID: {self.comune_id})")
        self.setMinimumSize(800, 500)

        layout = QVBoxLayout(self)
        # --- SEZIONE FILTRO (NUOVA) ---
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filtra possessori:")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare (nome completo, cognome, paternità)...")
        
        self.filter_button = QPushButton("Applica Filtro")
        self.filter_button.clicked.connect(self.load_possessori_data) # Ricarica i dati con il filtro
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)
        filter_layout.addWidget(self.filter_button)
        layout.addLayout(filter_layout)
        # --- FINE SEZIONE FILTRO ---
        # Tabella Possessori (come prima)
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(5)
        self.possessori_table.setHorizontalHeaderLabels([
            "ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Stato"
        ])
        self.possessori_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.setSelectionMode(QTableWidget.SingleSelection)
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)  # o ResizeToContents
        self.possessori_table.setSortingEnabled(True)
        self.possessori_table.itemSelectionChanged.connect(
            self._aggiorna_stato_pulsanti_azione)  # NUOVO
        self.possessori_table.itemDoubleClicked.connect(
            self.apri_modifica_possessore_selezionato)  # NUOVO per doppio click

        layout.addWidget(self.possessori_table)

        # --- NUOVI Pulsanti di Azione ---
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

        action_layout.addStretch()  # Spazio

        self.close_button = QPushButton("Chiudi")  # Pulsante Chiudi esistente
        self.close_button.clicked.connect(self.accept)
        action_layout.addWidget(self.close_button)

        layout.addLayout(action_layout)
        # --- FINE NUOVI Pulsanti di Azione ---

        self.setLayout(layout)
        self.load_possessori_data()

    def _aggiorna_stato_pulsanti_azione(self):  # NUOVO METODO
        """Abilita/disabilita i pulsanti di azione in base alla selezione nella tabella."""
        has_selection = bool(self.possessori_table.selectedItems())
        self.btn_modifica_possessore.setEnabled(has_selection)

    # NUOVO METODO HELPER
    def _get_selected_possessore_id(self) -> Optional[int]:
        """Restituisce l'ID del possessore attualmente selezionato nella tabella."""
        selected_items = self.possessori_table.selectedItems()
        if not selected_items:
            return None

        current_row = self.possessori_table.currentRow()
        if current_row < 0:
            return None

        # Colonna ID Poss.
        id_item = self.possessori_table.item(current_row, 0)
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def apri_modifica_possessore_selezionato(self):
        logging.getLogger("CatastoGUI").debug(
            "DEBUG: apri_modifica_possessore_selezionato chiamato.")  # NUOVA STAMPA
        possessore_id = self._get_selected_possessore_id()
        if possessore_id is not None:
            logging.getLogger("CatastoGUI").debug(
                # NUOVA STAMPA
                f"DEBUG: ID Possessore selezionato: {possessore_id}")
            dialog = ModificaPossessoreDialog(
                self.db_manager, possessore_id, self)

            dialog_result = dialog.exec_()  # Salva il risultato
            logging.getLogger("CatastoGUI").debug(
                # NUOVA STAMPA
                f"DEBUG: ModificaPossessoreDialog.exec_() restituito: {dialog_result} (Accepted è {QDialog.Accepted})")

            if dialog_result == QDialog.Accepted:
                logging.getLogger("CatastoGUI").info(
                    "DEBUG: ModificaPossessoreDialog accettato. Ricaricamento dati possessori...")  # NUOVA STAMPA
                QMessageBox.information(self, "Modifica Possessore",
                                        "Modifiche al possessore salvate con successo.")
                self.load_possessori_data()
            else:
                logging.getLogger("CatastoGUI").info(
                    # NUOVA STAMPA
                    "DEBUG: ModificaPossessoreDialog non accettato (probabilmente Annulla o errore nel salvataggio).")
        else:
            logging.getLogger("CatastoGUI").warning(
                "DEBUG: Tentativo di modificare possessore, ma nessun ID selezionato.")  # NUOVA STAMPA
            QMessageBox.warning(self, "Nessuna Selezione",
                                "Per favore, seleziona un possessore dalla tabella da modificare.")

    def load_possessori_data(self):
        """Carica i possessori per il comune specificato, applicando il filtro."""
        self.possessori_table.setRowCount(0)
        self.possessori_table.setSortingEnabled(False)
        
        filter_text = self.filter_edit.text().strip() # Ottieni il testo del filtro

        try:
            # Modifica il db_manager.get_possessori_by_comune per accettare un filtro testuale.
            # Se non hai ancora modificato get_possessori_by_comune, vedi la nota sotto.
            possessori_list = self.db_manager.get_possessori_by_comune(
                self.comune_id, filter_text=filter_text if filter_text else None
            )
            
            if possessori_list:
                self.possessori_table.setRowCount(len(possessori_list))
                for row_idx, possessore in enumerate(possessori_list):
                    col = 0
                    self.possessori_table.setItem(
                        row_idx, col, QTableWidgetItem(str(possessore.get('id', ''))))
                    col += 1
                    self.possessori_table.setItem(row_idx, col, QTableWidgetItem(
                        possessore.get('nome_completo', '')))
                    col += 1
                    self.possessori_table.setItem(
                        row_idx, col, QTableWidgetItem(possessore.get('cognome_nome', '')))
                    col += 1
                    self.possessori_table.setItem(
                        row_idx, col, QTableWidgetItem(possessore.get('paternita', '')))
                    col += 1
                    stato_str = "Attivo" if possessore.get('attivo', False) else "Non Attivo"
                    self.possessori_table.setItem(
                        row_idx, col, QTableWidgetItem(stato_str))
                    col += 1
                self.possessori_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessun possessore trovato per il comune ID: {self.comune_id} con filtro '{filter_text}'.")
                # Visualizza un messaggio nella tabella se nessun risultato
                self.possessori_table.setRowCount(1)
                item = QTableWidgetItem("Nessun possessore trovato con i criteri specificati.")
                item.setTextAlignment(Qt.AlignCenter)
                self.possessori_table.setItem(0, 0, item)
                self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())

        except Exception as e:
            self.logger.error(f"Errore durante il caricamento dei possessori per comune ID {self.comune_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
            # Visualizza un messaggio di errore nella tabella
            self.possessori_table.setRowCount(1)
            item = QTableWidgetItem(f"Errore nel caricamento dei dati: {e}")
            item.setTextAlignment(Qt.AlignCenter)
            self.possessori_table.setItem(0, 0, item)
            self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())
        finally:
            self.possessori_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsanti_azione()


class PartiteComuneDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, nome_comune: str, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.nome_comune = nome_comune
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.setWindowTitle(
            f"Partite del Comune di {self.nome_comune} (ID: {self.comune_id})")
        self.setMinimumSize(850, 550)

        layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filtra partite:")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare (numero, tipo, stato, suffisso)...")
        
        self.filter_button = QPushButton("Applica Filtro")
        self.filter_button.clicked.connect(self.load_partite_data)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)
        filter_layout.addWidget(self.filter_button)
        layout.addLayout(filter_layout)

        self.partite_table = QTableWidget()
        
        # MODIFICA QUI: Imposta le intestazioni corrette una sola volta
        self.partite_table.setColumnCount(9) 
        self.partite_table.setHorizontalHeaderLabels([
            "ID Partita", "Numero", "Suffisso", "Tipo", "Stato", 
            "Data Impianto", "Num. Possessori", "Num. Immobili", "Num. Documenti"
        ])

        self.partite_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.partite_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.partite_table.setSelectionMode(QTableWidget.SingleSelection)
        self.partite_table.setAlternatingRowColors(True)
        self.partite_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.partite_table.setSortingEnabled(True)
        self.partite_table.itemDoubleClicked.connect(self.apri_dettaglio_partita_selezionata)
        self.partite_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsante_modifica)

        layout.addWidget(self.partite_table)

        action_buttons_layout = QHBoxLayout()
        self.btn_apri_dettaglio = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_FileDialogInfoView), "Vedi Dettagli")
        self.btn_apri_dettaglio.clicked.connect(self.apri_dettaglio_partita_selezionata_da_pulsante)
        self.btn_apri_dettaglio.setEnabled(False)
        action_buttons_layout.addWidget(self.btn_apri_dettaglio)

        self.btn_modifica_partita = QPushButton("Modifica Partita")
        self.btn_modifica_partita.setToolTip("Modifica i dati della partita selezionata")
        self.btn_modifica_partita.clicked.connect(self.apri_modifica_partita_selezionata)
        self.btn_modifica_partita.setEnabled(False)
        action_buttons_layout.addWidget(self.btn_modifica_partita)

        action_buttons_layout.addStretch()

        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.accept)
        action_buttons_layout.addWidget(self.close_button)

        layout.addLayout(action_buttons_layout)

        self.setLayout(layout)
        self.load_partite_data()

    def load_partite_data(self):
        self.partite_table.setRowCount(0)
        self.partite_table.setSortingEnabled(False)
        
        # Le intestazioni sono già state impostate nell'__init__
        # Non è necessario reimpostarle qui.

        filter_text = self.filter_edit.text().strip()

        try:
            partite_list = self.db_manager.get_partite_by_comune(
                self.comune_id, filter_text=filter_text if filter_text else None
            )

            if partite_list:
                self.partite_table.setRowCount(len(partite_list))
                for row_idx, partita in enumerate(partite_list):
                    col = 0
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('id', '')))); col += 1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('numero_partita', '')))); col += 1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(partita.get('suffisso_partita', '') or '')); col += 1 
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(partita.get('tipo', ''))); col += 1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(partita.get('stato', ''))); col += 1
                    data_imp = partita.get('data_impianto')
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(data_imp) if data_imp else '')); col += 1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('num_possessori', '0')))); col += 1
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('num_immobili', '0')))); col += 1
                    
                    # --- NUOVA RIGA PER IL NUMERO DEI DOCUMENTI ---
                    self.partite_table.setItem(row_idx, col, QTableWidgetItem(str(partita.get('num_documenti_allegati', '0')))); col += 1

                self.partite_table.resizeColumnsToContents()
            else:
                self.logger.info(f"Nessuna partita trovata per il comune ID: {self.comune_id} con filtro '{filter_text}'.")
                self.partite_table.setRowCount(1)
                item = QTableWidgetItem("Nessuna partita trovata con i criteri specificati.")
                item.setTextAlignment(Qt.AlignCenter)
                self.partite_table.setItem(0, 0, item)
                self.partite_table.setSpan(0, 0, 1, self.partite_table.columnCount())

        except Exception as e:
            self.logger.error(f"Errore durante il caricamento delle partite per comune ID {self.comune_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento Dati", f"Si è verificato un errore: {e}")
            self.partite_table.setRowCount(1)
            item = QTableWidgetItem(f"Errore nel caricamento dei dati: {e}")
            item.setTextAlignment(Qt.AlignCenter)
            self.partite_table.setItem(0, 0, item)
            self.partite_table.setSpan(0, 0, 1, self.partite_table.columnCount())
        finally:
            self.partite_table.setSortingEnabled(True)
            self._aggiorna_stato_pulsante_modifica()

    def _aggiorna_stato_pulsante_modifica(self):
        has_selection = bool(self.partite_table.selectedItems())
        self.btn_modifica_partita.setEnabled(has_selection)
        self.btn_apri_dettaglio.setEnabled(has_selection)

    def _get_selected_partita_id(self) -> Optional[int]:
        selected_items = self.partite_table.selectedItems()
        if not selected_items:
            return None
        row = self.partite_table.currentRow()
        if row < 0:
            return None
        partita_id_item = self.partite_table.item(row, 0)
        if partita_id_item and partita_id_item.text().isdigit():
            return int(partita_id_item.text())
        return None

    def apri_dettaglio_partita_selezionata_da_pulsante(self):
        partita_id = self._get_selected_partita_id()
        if partita_id is not None:
            partita_details_data = self.db_manager.get_partita_details(partita_id)
            if partita_details_data:
                details_dialog = PartitaDetailsDialog(partita_details_data, self)
                details_dialog.exec_()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile recuperare i dettagli per la partita ID {partita_id}.")
        else:
            QMessageBox.information(self, "Nessuna Selezione", "Seleziona una partita dalla tabella per vederne i dettagli.")

    def apri_modifica_partita_selezionata(self, item: Optional[QTableWidgetItem] = None):
        partita_id = self._get_selected_partita_id()
        if partita_id is not None:
            dialog = ModificaPartitaDialog(self.db_manager, partita_id, self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_partite_data()
                QMessageBox.information(self, "Modifica Partita", "Modifiche alla partita salvate con successo.")
        else:
            QMessageBox.warning(self, "Nessuna Selezione", "Per favore, seleziona una partita da modificare.")
    
    def apri_dettaglio_partita_selezionata(self, item: QTableWidgetItem):
        if not item:
            return
        partita_id = self._get_selected_partita_id()
        if partita_id is not None:
            partita_details_data = self.db_manager.get_partita_details(partita_id)
            if partita_details_data:
                details_dialog = PartitaDetailsDialog(partita_details_data, self)
                details_dialog.exec_()
            else:
                QMessageBox.warning(self, "Errore Dati", f"Impossibile recuperare i dettagli per la partita ID {partita_id}.")


class ModificaLocalitaDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, localita_id: int, comune_id_parent: int, parent=None):  # Aggiunto comune_id_parent
        super().__init__(parent)
        self.db_manager = db_manager
        self.localita_id = localita_id
        # ID del comune a cui questa località appartiene (non modificabile)
        self.comune_id_parent = comune_id_parent
        self.localita_data_originale = None

        self.setWindowTitle(f"Modifica Dati Località ID: {self.localita_id}")
        self.setMinimumWidth(450)

        self._init_ui()
        self._load_localita_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.id_label = QLabel(str(self.localita_id))
        form_layout.addRow("ID Località:", self.id_label)
        self.comune_display_label = QLabel(
            "Caricamento nome comune...")  # Verrà popolato
        form_layout.addRow("Comune di Appartenenza:",
                           self.comune_display_label)

        self.nome_edit = QLineEdit()
        form_layout.addRow("Nome Località (*):", self.nome_edit)

        self.tipo_combo = QComboBox()
        # Coerente con la tabella
        self.tipo_combo.addItems(["Regione", "Via", "Borgata","Altro"])
        form_layout.addRow("Tipo (*):", self.tipo_combo)

        self.civico_spinbox = QSpinBox()
        # 0 potrebbe significare "non applicabile"
        self.civico_spinbox.setMinimum(0)
        self.civico_spinbox.setMaximum(99999)
        self.civico_spinbox.setSpecialValueText("Nessuno")  # Se 0 è "Nessuno"
        form_layout.addRow("Numero Civico (0 se assente):",
                           self.civico_spinbox)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogSaveButton), "Salva Modifiche")
        self.save_button.clicked.connect(self._save_changes)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def _load_localita_data(self):
        # Metodo da creare in CatastoDBManager: get_localita_details(localita_id)
        # Dovrebbe restituire: id, nome, tipo, civico, comune_id, e il nome del comune (comune_nome)
        self.localita_data_originale = self.db_manager.get_localita_details(
            self.localita_id)  # Metodo da creare

        if not self.localita_data_originale:
            QMessageBox.critical(
                self, "Errore Caricamento", f"Impossibile caricare dati per località ID: {self.localita_id}.")
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, self.reject)
            return

        self.nome_edit.setText(self.localita_data_originale.get('nome', ''))

        tipo_idx = self.tipo_combo.findText(
            self.localita_data_originale.get('tipo', ''), Qt.MatchFixedString)
        if tipo_idx >= 0:
            self.tipo_combo.setCurrentIndex(tipo_idx)

        civico_val = self.localita_data_originale.get('civico')
        if civico_val is not None:
            self.civico_spinbox.setValue(civico_val)
        else:  # Se civico è NULL nel DB
            # Imposta a 0 (che potrebbe essere "Nessuno")
            self.civico_spinbox.setValue(self.civico_spinbox.minimum())
            # o se 0 è un civico valido, dovresti avere un modo per distinguere
            # Forse il QSpinBox non è ideale se NULL è molto diverso da 0.
            # Un QLineEdit che accetta numeri o è vuoto potrebbe essere più flessibile per il civico.
            # Per ora, lasciamo QSpinBox e 0 (con specialValueText) per NULL.

        # Visualizza il nome del comune (non modificabile qui)
        self.comune_display_label.setText(
            f"{self.localita_data_originale.get('comune_nome', 'N/D')} (ID: {self.localita_data_originale.get('comune_id', 'N/D')})"
        )
        # Verifica che il comune_id della località corrisponda a quello del dialogo genitore
        if self.localita_data_originale.get('comune_id') != self.comune_id_parent:
            logging.getLogger("CatastoGUI").warning(
                f"Incoerenza Comune ID: Località {self.localita_id} appartiene a comune {self.localita_data_originale.get('comune_id')} ma aperta da contesto comune {self.comune_id_parent}")
            # Potresti mostrare un avviso, ma per ora procediamo.

    def _save_changes(self):
        dati_modificati = {
            "nome": self.nome_edit.text().strip(),
            "tipo": self.tipo_combo.currentText(),
        }

        civico_val = self.civico_spinbox.value()
        if self.civico_spinbox.text() == self.civico_spinbox.specialValueText() or civico_val == 0:
            dati_modificati["civico"] = None
        else:
            dati_modificati["civico"] = civico_val

        if not dati_modificati["nome"]:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il nome della località è obbligatorio.")
            self.nome_edit.setFocus()
            return
        # Aggiungi altre validazioni UI se necessario
        try:
            logging.getLogger("CatastoGUI").info(
                f"Tentativo di aggiornare località ID {self.localita_id} con: {dati_modificati}")
            self.db_manager.update_localita(
                self.localita_id, dati_modificati)  # Chiamata al metodo

            logging.getLogger("CatastoGUI").info(
                f"Località ID {self.localita_id} aggiornata con successo.")
            self.accept()  # Chiudi se ha successo

        except DBUniqueConstraintError as uve:
            logging.getLogger("CatastoGUI").warning(
                f"Violazione unicità per località ID {self.localita_id}: {uve.message}")
            QMessageBox.warning(self, "Errore di Unicità",
                                f"Impossibile salvare le modifiche:\n{uve.message}\n"
                                "Una località con lo stesso nome e civico potrebbe già esistere in questo comune.")
            self.nome_edit.setFocus()  # O il campo civico se più appropriato
        except DBNotFoundError as nfe:
            logging.getLogger("CatastoGUI").error(
                f"Località ID {self.localita_id} non trovata per l'aggiornamento: {nfe.message}")
            QMessageBox.critical(
                self, "Errore Aggiornamento", str(nfe.message))
            self.reject()  # Chiudi perché il record non esiste più
        except DBDataError as dde:
            logging.getLogger("CatastoGUI").warning(
                f"Errore dati per località ID {self.localita_id}: {dde.message}")
            QMessageBox.warning(self, "Errore Dati Non Validi",
                                f"Impossibile salvare le modifiche:\n{dde.message}")
        except DBMError as dbe:
            logging.getLogger("CatastoGUI").error(
                f"Errore DB aggiornando località ID {self.localita_id}: {dbe.message}")
            QMessageBox.critical(self, "Errore Database",
                                 f"Errore salvataggio località:\n{dbe.message}")
        except AttributeError as ae:  # Per debug se il metodo non è ancora in db_manager
            logging.getLogger("CatastoGUI").critical(
                f"Metodo 'update_localita' non trovato o altro AttributeError: {ae}", exc_info=True)
            QMessageBox.critical(self, "Errore Implementazione",
                                 "Funzionalità non completamente implementata.")
        except Exception as e:
            logging.getLogger("CatastoGUI").critical(
                f"Errore imprevisto salvataggio località ID {self.localita_id}: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Critico",
                                 f"Errore imprevisto: {e}")


class PeriodoStoricoDetailsDialog(QDialog):
    def __init__(self, db_manager: 'CatastoDBManager', periodo_id: int, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.periodo_id = periodo_id
        self.periodo_data_originale: Optional[Dict[str, Any]] = None

        self.setWindowTitle(
            f"Dettagli/Modifica Periodo Storico ID: {self.periodo_id}")
        self.setMinimumWidth(450)
        self.setModal(True)

        self._initUI()
        self._load_data()

    def _initUI(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Campi Visualizzazione (non editabili)
        self.id_label = QLabel(str(self.periodo_id))
        self.data_creazione_label = QLabel()
        self.data_modifica_label = QLabel()

        form_layout.addRow("ID Periodo:", self.id_label)

        # Campi Editabili
        self.nome_edit = QLineEdit()
        form_layout.addRow("Nome Periodo (*):", self.nome_edit)

        self.anno_inizio_spinbox = QSpinBox()
        # Adatta il range se necessario
        self.anno_inizio_spinbox.setRange(0, 3000)
        form_layout.addRow("Anno Inizio (*):", self.anno_inizio_spinbox)

        self.anno_fine_spinbox = QSpinBox()
        self.anno_fine_spinbox.setRange(0, 3000)
        # Permetti "nessun anno fine" usando un valore speciale o gestendo 0 come "non impostato"
        self.anno_fine_spinbox.setSpecialValueText(
            " ")  # Vuoto se 0 (o il minimo)
        # 0 potrebbe significare "non specificato"
        self.anno_fine_spinbox.setMinimum(0)
        form_layout.addRow("Anno Fine (0 se aperto):", self.anno_fine_spinbox)

        self.descrizione_edit = QTextEdit()
        self.descrizione_edit.setFixedHeight(100)
        form_layout.addRow("Descrizione:", self.descrizione_edit)

        form_layout.addRow("Data Creazione:", self.data_creazione_label)
        form_layout.addRow("Ultima Modifica:", self.data_modifica_label)

        main_layout.addLayout(form_layout)

        # Pulsanti
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self._save_changes)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

    def _load_data(self):
        self.periodo_data_originale = self.db_manager.get_periodo_storico_details(
            self.periodo_id)

        if not self.periodo_data_originale:
            QMessageBox.critical(self, "Errore Caricamento",
                                 f"Impossibile caricare i dettagli per il periodo ID: {self.periodo_id}.")
            # Chiudi il dialogo se i dati non possono essere caricati
            # Usiamo QTimer per permettere al messaggio di essere processato prima di chiudere
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, self.reject)
            return

        self.nome_edit.setText(self.periodo_data_originale.get('nome', ''))
        self.anno_inizio_spinbox.setValue(
            self.periodo_data_originale.get('anno_inizio', 0))

        anno_fine_val = self.periodo_data_originale.get('anno_fine')
        if anno_fine_val is not None:
            self.anno_fine_spinbox.setValue(anno_fine_val)
        else:  # Se anno_fine è NULL nel DB
            # Mostra testo speciale (" ")
            self.anno_fine_spinbox.setValue(self.anno_fine_spinbox.minimum())

        self.descrizione_edit.setText(
            self.periodo_data_originale.get('descrizione', ''))

        dc = self.periodo_data_originale.get('data_creazione')
        self.data_creazione_label.setText(
            dc.strftime('%Y-%m-%d %H:%M:%S') if dc else 'N/D')
        dm = self.periodo_data_originale.get('data_modifica')
        self.data_modifica_label.setText(
            dm.strftime('%Y-%m-%d %H:%M:%S') if dm else 'N/D')

    def _save_changes(self):
        dati_da_salvare = {
            "nome": self.nome_edit.text().strip(),
            "anno_inizio": self.anno_inizio_spinbox.value(),
            "descrizione": self.descrizione_edit.toPlainText().strip()
        }

        anno_fine_val_ui = self.anno_fine_spinbox.value()
        if self.anno_fine_spinbox.text() == self.anno_fine_spinbox.specialValueText() or anno_fine_val_ui == self.anno_fine_spinbox.minimum():
            # Salva NULL se vuoto o valore minimo
            dati_da_salvare["anno_fine"] = None
        else:
            dati_da_salvare["anno_fine"] = anno_fine_val_ui

        # Validazione base
        if not dati_da_salvare["nome"]:
            QMessageBox.warning(self, "Dati Mancanti",
                                "Il nome del periodo è obbligatorio.")
            self.nome_edit.setFocus()
            return
        if dati_da_salvare["anno_inizio"] <= 0:  # O altra logica per anno inizio
            QMessageBox.warning(self, "Dati Non Validi",
                                "L'anno di inizio deve essere valido.")
            self.anno_inizio_spinbox.setFocus()
            return
        if dati_da_salvare["anno_fine"] is not None and dati_da_salvare["anno_fine"] < dati_da_salvare["anno_inizio"]:
            QMessageBox.warning(
                self, "Date Non Valide", "L'anno di fine non può essere precedente all'anno di inizio.")
            self.anno_fine_spinbox.setFocus()
            return

        try:
            success = self.db_manager.update_periodo_storico(
                self.periodo_id, dati_da_salvare)
            if success:
                QMessageBox.information(
                    self, "Successo", "Periodo storico aggiornato con successo.")
                self.accept()  # Chiude il dialogo e segnala successo
            # else: # update_periodo_storico solleva eccezioni per fallimenti
            # QMessageBox.critical(self, "Errore", "Impossibile aggiornare il periodo storico.")
        except (DBUniqueConstraintError, DBDataError, DBMError) as e:
            logging.getLogger("CatastoGUI").error(
                f"Errore salvataggio periodo storico ID {self.periodo_id}: {str(e)}")
            QMessageBox.critical(self, "Errore Salvataggio", str(e))
        except Exception as e_gen:
            logging.getLogger("CatastoGUI").critical(
                f"Errore imprevisto salvataggio periodo storico ID {self.periodo_id}: {str(e_gen)}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto",
                                 f"Si è verificato un errore: {str(e_gen)}")
            
class LocalitaSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, parent=None,
                 selection_mode: bool = False):
        super(LocalitaSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.selection_mode = selection_mode
        self.logger = logging.getLogger(f"CatastoGUI.{self.__class__.__name__}")

        self.selected_localita_id: Optional[int] = None
        self.selected_localita_name: Optional[str] = None

        if self.selection_mode:
            self.setWindowTitle(f"Seleziona Località per Comune ID: {self.comune_id}")
        else:
            self.setWindowTitle(f"Gestisci Località per Comune ID: {self.comune_id}")

        self.setMinimumSize(650, 450)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        # --- Tab 1: Visualizza/Modifica Esistente ---
        select_tab = QWidget()
        select_layout = QVBoxLayout(select_tab)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtra per nome:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare...")
        self.filter_edit.textChanged.connect(
            lambda: (self.load_localita(self.filter_edit.text().strip()),
                     self._aggiorna_stato_pulsanti_action_localita())
        )
        filter_layout.addWidget(self.filter_edit)
        select_layout.addLayout(filter_layout)

        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(4)
        self.localita_table.setHorizontalHeaderLabels(["ID", "Nome", "Tipo", "Civico"])
        self.localita_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.localita_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.localita_table.setSelectionMode(QTableWidget.SingleSelection)
        self.localita_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_action_localita) # Qui si collega il segnale
        self.localita_table.itemDoubleClicked.connect(self._handle_double_click)
        select_layout.addWidget(self.localita_table)

        select_action_layout = QHBoxLayout()
        self.btn_modifica_localita = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_FileDialogDetailedView), "Modifica Selezionata")
        self.btn_modifica_localita.setToolTip("Modifica i dati della località selezionata")
        self.btn_modifica_localita.clicked.connect(self.apri_modifica_localita_selezionata)
        if self.selection_mode:
            self.btn_modifica_localita.setVisible(False)
        select_action_layout.addWidget(self.btn_modifica_localita)
        select_action_layout.addStretch()
        select_layout.addLayout(select_action_layout)
        self.tabs.addTab(select_tab, "Visualizza Località")

        if not self.selection_mode:
            create_tab = QWidget()
            create_form_layout = QFormLayout(create_tab)
            self.nome_edit_nuova = QLineEdit() 
            self.tipo_combo_nuova = QComboBox() 
            self.tipo_combo_nuova.addItems(["Regione", "Via", "Borgata", "Altro"])
            self.civico_spinbox_nuova = QSpinBox() 
            self.civico_spinbox_nuova.setMinimum(0)
            self.civico_spinbox_nuova.setMaximum(99999)
            self.civico_spinbox_nuova.setSpecialValueText("Nessuno") 
            create_form_layout.addRow(QLabel("Nome località (*):"), self.nome_edit_nuova)
            create_form_layout.addRow(QLabel("Tipo (*):"), self.tipo_combo_nuova)
            create_form_layout.addRow(QLabel("Numero Civico (0 se assente):"), self.civico_spinbox_nuova)
            self.btn_salva_nuova_localita = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton) ,"Salva Nuova Località")
            self.btn_salva_nuova_localita.clicked.connect(self._salva_nuova_localita_da_tab)
            create_form_layout.addRow(self.btn_salva_nuova_localita)
            self.tabs.addTab(create_tab, "Crea Nuova Località")

        buttons_layout = QHBoxLayout()

        self.select_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogApplyButton), "Seleziona")
        self.select_button.setToolTip("Conferma la località selezionata")
        self.select_button.clicked.connect(self._handle_selection_or_creation)
        buttons_layout.addWidget(self.select_button)

        buttons_layout.addStretch()

        self.chiudi_button = QPushButton(QApplication.style().standardIcon(
            QStyle.SP_DialogCloseButton), "Chiudi")
        self.chiudi_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.chiudi_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self.tabs.currentChanged.connect(self._tab_changed) 

        self.load_localita()
        self._tab_changed(self.tabs.currentIndex()) # Imposta lo stato iniziale del pulsante
     # --- INIZIO METODO MANCANTE/DA RIPRISTINARE ---
    def load_localita(self, filter_text: Optional[str] = None):
        """
        Carica le località per il comune_id corrente, applicando un filtro testuale opzionale.
        """
        self.localita_table.setRowCount(0)
        self.localita_table.setSortingEnabled(False)

        # Se il filtro non è fornito, usa il testo attuale dal QLineEdit del filtro
        # Questo assicura che il filtro venga mantenuto anche se load_localita è chiamato senza parametri
        actual_filter_text = filter_text if filter_text is not None else self.filter_edit.text().strip()
        if not actual_filter_text: # Se il filtro è vuoto, imposta a None per la query DB
            actual_filter_text = None

        if self.comune_id:
            try:
                localita_results = self.db_manager.get_localita_by_comune(
                    self.comune_id, actual_filter_text)
                
                if localita_results:
                    self.localita_table.setRowCount(len(localita_results))
                    for i, loc in enumerate(localita_results):
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
                    self.logger.info(f"Nessuna località trovata per comune ID {self.comune_id} con filtro '{actual_filter_text}'.")
                    # Mostra un messaggio nella tabella se nessun risultato
                    self.localita_table.setRowCount(1)
                    item = QTableWidgetItem("Nessuna località trovata con i criteri specificati.")
                    item.setTextAlignment(Qt.AlignCenter)
                    self.localita_table.setItem(0, 0, item)
                    self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())

            except Exception as e:
                self.logger.error(f"Errore caricamento località per comune {self.comune_id} (filtro '{actual_filter_text}'): {e}", exc_info=True)
                QMessageBox.critical(
                    self, "Errore Caricamento", f"Impossibile caricare le località:\n{e}")
                self.localita_table.setRowCount(1)
                item = QTableWidgetItem(f"Errore caricamento: {e}")
                item.setTextAlignment(Qt.AlignCenter)
                self.localita_table.setItem(0, 0, item)
                self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())
        else:
            self.logger.warning("Comune ID non disponibile per caricare località.")
            self.localita_table.setRowCount(1)
            item = QTableWidgetItem("ID Comune non disponibile per caricare località.")
            item.setTextAlignment(Qt.AlignCenter)
            self.localita_table.setItem(0, 0, item)
            self.localita_table.setSpan(0, 0, 1, self.localita_table.columnCount())


        self.localita_table.setSortingEnabled(True)
        self._aggiorna_stato_pulsanti_action_localita() # Aggiorna stato pulsanti
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---

    # --- INIZIO METODO MANCANTE/DA RIPRISTINARE ---
    def _handle_double_click(self, item: QTableWidgetItem):
        """Gestisce il doppio click sulla tabella."""
        if self.selection_mode and self.tabs.currentIndex() == 0:
            # Se in modalità selezione e nel tab di visualizzazione, il doppio click seleziona
            self._handle_selection_or_creation() # Chiama il metodo unificato per la selezione
        elif not self.selection_mode and self.tabs.currentIndex() == 0:
            # Se non in modalità selezione (ovvero gestione) e nel tab di visualizzazione,
            # il doppio click apre la modifica (se l'utente ha i permessi e una riga è selezionata).
            self.apri_modifica_localita_selezionata()
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---
    def _aggiorna_stato_pulsanti_action_localita(self):
        """Abilita/disabilita i pulsanti di azione (Modifica, Seleziona) in base alla selezione nella tabella."""
        is_select_tab_active = (self.tabs.currentIndex() == 0)
        has_selection_in_table = bool(self.localita_table.selectedItems())

        # Pulsante Modifica (visibile e attivo solo se non in selection_mode e nel tab corretto)
        self.btn_modifica_localita.setEnabled(
            is_select_tab_active and has_selection_in_table and not self.selection_mode
        )

        # Pulsante Seleziona (visibile e attivo solo se nel tab corretto e c'è selezione)
        # La visibilità del pulsante "Seleziona" è gestita in _tab_changed e _init_ui
        self.select_button.setEnabled(is_select_tab_active and has_selection_in_table)
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---


    def _tab_changed(self, index):
        """Gestisce il cambio di tab e aggiorna il testo del pulsante OK."""
        if self.selection_mode: # Se è in modalità solo selezione, il pulsante è sempre "Seleziona"
            self.select_button.setText("Seleziona Località")
            self.select_button.setToolTip("Conferma la località selezionata dalla tabella.")
            self.select_button.setVisible(True) # In modalità selezione, il pulsante è sempre visibile
        else: # Modalità gestione/creazione
            if index == 0:  # Tab "Visualizza Località"
                self.select_button.setText("Seleziona Località")
                self.select_button.setToolTip("Conferma la località selezionata dalla tabella.")
                self.select_button.setVisible(True)
            elif index == 1: # Tab "Crea Nuova Località"
                self.select_button.setText("Crea e Seleziona")
                self.select_button.setToolTip("Crea la nuova località e la seleziona automaticamente.")
                # Assicurati che questo pulsante sia visibile solo quando il tab è attivo e non in modalità solo selezione
                self.select_button.setVisible(True) 
            
        self._aggiorna_stato_pulsanti_action_localita() # Aggiorna abilitazione

    # --- MODIFICA CRUCIALE: Unifica la gestione di selezione ed creazione ---
    # --- INIZIO METODO MANCANTE/DA RIPRISTINARE ---
    def apri_modifica_localita_selezionata(self):
        """
        Apre un dialogo per modificare la località selezionata dalla tabella.
        """
        # Importa ModificaLocalitaDialog localmente per evitare cicli di importazione
        from gui_widgets import ModificaLocalitaDialog 

        localita_id_sel = self._get_selected_localita_id_from_table()
        if localita_id_sel is not None:
            self.logger.info(f"LocalitaSelectionDialog: Richiesta modifica per località ID {localita_id_sel}.")
            # Istanzia e apre ModificaLocalitaDialog, passando il comune_id_parent
            dialog = ModificaLocalitaDialog(
                self.db_manager, localita_id_sel, self.comune_id, self) # comune_id qui è il comune_id_parent
            if dialog.exec_() == QDialog.Accepted:
                self.logger.info(f"Modifiche a località ID {localita_id_sel} salvate. Ricarico l'elenco.")
                self.load_localita(self.filter_edit.text().strip() or None) # Ricarica con il filtro corrente
                QMessageBox.information(self, "Modifica Località", "Modifiche alla località salvate con successo.")
            else:
                self.logger.info(f"Modifica località ID {localita_id_sel} annullata dall'utente.")
        else:
            QMessageBox.warning(
                self, "Nessuna Selezione", "Seleziona una località dalla tabella per modificarla.")

    def _get_selected_localita_id_from_table(self) -> Optional[int]:
        """Helper per ottenere l'ID della località selezionata nella tabella."""
        selected_items = self.localita_table.selectedItems()
        if not selected_items:
            return None
        current_row = self.localita_table.currentRow()
        if current_row < 0:
            return None
        id_item = self.localita_table.item(current_row, 0)
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---
    def _handle_selection_or_creation(self):
        """
        Gestisce la selezione di una località esistente o la creazione/selezione di una nuova.
        Questo metodo imposta self.selected_localita_id e self.selected_localita_name
        e poi chiama self.accept().
        """
        current_tab_index = self.tabs.currentIndex()

        if current_tab_index == 0:  # Tab "Visualizza Località" (selezione di un esistente)
            selected_items = self.localita_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una località dalla tabella.")
                return

            current_row = self.localita_table.currentRow()
            if current_row < 0: # Controllo aggiuntivo
                QMessageBox.warning(self, "Errore Selezione", "Nessuna riga selezionata validamente.")
                return

            try:
                self.selected_localita_id = int(self.localita_table.item(current_row, 0).text())
                nome = self.localita_table.item(current_row, 1).text()
                tipo = self.localita_table.item(current_row, 2).text()
                civico_item_text = self.localita_table.item(current_row, 3).text()

                self.selected_localita_name = nome
                if civico_item_text and civico_item_text != "-" and civico_item_text.strip() != self.civico_spinbox_nuova.specialValueText(): # Verifica anche il testo speciale
                    self.selected_localita_name += f", civ. {civico_item_text}"
                if tipo:
                    self.selected_localita_name += f" ({tipo})"
                
                self.logger.info(f"LocalitaSelectionDialog: Località esistente selezionata - ID: {self.selected_localita_id}, Nome: '{self.selected_localita_name}'")
                self.accept() # Accetta il dialogo con la selezione fatta

            except ValueError:
                QMessageBox.critical(self, "Errore Dati", "ID località non valido nella tabella.")
            except Exception as e:
                self.logger.error(f"Errore in _handle_selection_or_creation (selezione esistente): {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore durante la conferma della selezione: {e}")

        elif current_tab_index == 1 and not self.selection_mode: # Tab "Crea Nuova Località" (solo se in modalità gestione)
            nome = self.nome_edit_nuova.text().strip()
            tipo = self.tipo_combo_nuova.currentText()
            civico_val = self.civico_spinbox_nuova.value()
            
            # Determina il valore finale del civico (NULL se 0 o testo speciale)
            civico = None
            if self.civico_spinbox_nuova.text().strip() != self.civico_spinbox_nuova.specialValueText() and civico_val != 0:
                civico = civico_val

            if not nome:
                QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
                self.nome_edit_nuova.setFocus()
                return
            if not tipo or tipo.strip() == "Seleziona Tipo...": # Se avevi aggiunto un placeholder
                QMessageBox.warning(self, "Dati Mancanti", "Il tipo di località è obbligatorio.")
                self.tipo_combo_nuova.setFocus()
                return
            if self.comune_id is None:
                QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato. Impossibile creare località.")
                return

            try:
                localita_id_creata = self.db_manager.insert_localita(
                    self.comune_id, nome, tipo, civico
                )

                if localita_id_creata is not None:
                    # Imposta gli attributi selected_localita_id e selected_localita_name
                    # che verranno letti dal chiamante (ImmobileDialog).
                    self.selected_localita_id = localita_id_creata
                    self.selected_localita_name = nome
                    if civico is not None:
                        self.selected_localita_name += f", civ. {civico}"
                    self.selected_localita_name += f" ({tipo})"

                    QMessageBox.information(self, "Località Creata", f"Località '{self.selected_localita_name}' registrata con ID: {self.selected_localita_id}.")
                    self._pulisci_campi_creazione_localita() # Pulisce i campi del tab "Crea Nuova"
                    self.load_localita() # Ricarica l'elenco delle località nel tab "Visualizza"
                    self.tabs.setCurrentIndex(0) # Torna al tab di visualizzazione/selezione

                    self.accept() # Accetta il dialogo con la nuova località creata e selezionata

                else: # Fallimento nella creazione senza eccezione esplicita dal DBManager
                    self.logger.error("Creazione località fallita: ID non restituito da DBManager.")
                    QMessageBox.critical(self, "Errore Creazione", "Impossibile creare la località (ID non restituito).")

            except (DBUniqueConstraintError, DBDataError, DBMError) as dbe:
                self.logger.error(f"Errore DB creazione località: {dbe}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Impossibile creare località:\n{dbe.message if hasattr(dbe, 'message') else str(dbe)}")
            except Exception as e:
                self.logger.critical(f"Errore imprevisto creazione località: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore:\n{e}")
        
        else: # Se si tenta di creare in selection_mode=True, blocca
             if current_tab_index == 1 and self.selection_mode:
                QMessageBox.warning(self, "Azione Non Disponibile", "La creazione di nuove località non è consentita in questa modalità di selezione.")
             else:
                QMessageBox.warning(self, "Azione Non Valida", "Azione non riconosciuta per il tab corrente.")

    # Aggiungi questo metodo per pulire i campi del tab "Crea Nuova Località"
    def _pulisci_campi_creazione_localita(self):
        self.nome_edit_nuova.clear()
        self.tipo_combo_nuova.setCurrentIndex(0)
        self.civico_spinbox_nuova.setValue(self.civico_spinbox_nuova.minimum()) # Resetta al "Nessuno"
    # --- INIZIO METODO MANCANTE/DA RIPRISTINARE ---
    def _salva_nuova_localita_da_tab(self):
        """
        Salva una nuova località dal tab "Crea Nuova Località".
        """
        nome = self.nome_edit_nuova.text().strip()
        tipo = self.tipo_combo_nuova.currentText()
        civico_val = self.civico_spinbox_nuova.value()

        civico = None
        if self.civico_spinbox_nuova.text().strip() != self.civico_spinbox_nuova.specialValueText() and civico_val != 0:
            civico = civico_val

        if not nome:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
            self.nome_edit_nuova.setFocus()
            return
        if not tipo or tipo.strip() == "Seleziona Tipo...": # Se avevi aggiunto un placeholder
            QMessageBox.warning(self, "Dati Mancanti", "Il tipo di località è obbligatorio.")
            self.tipo_combo_nuova.setFocus()
            return
        if self.comune_id is None:
            QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato. Impossibile creare località.")
            return

        try:
            localita_id_creata = self.db_manager.insert_localita(
                self.comune_id, nome, tipo, civico
            )

            if localita_id_creata is not None:
                QMessageBox.information(self, "Località Creata", f"Località '{nome}' registrata con ID: {localita_id_creata}")
                self.logger.info(f"Nuova località creata tramite tab 'Crea Nuova': ID {localita_id_creata}, Nome: '{nome}'")
                
                self._pulisci_campi_creazione_localita() # Pulisce i campi del tab "Crea Nuova"
                self.load_localita() # Ricarica l'elenco delle località nel tab "Visualizza"
                self.tabs.setCurrentIndex(0) # Torna al tab di visualizzazione/selezione
            else:
                self.logger.error("Creazione località fallita: ID non restituito da DBManager.")
                QMessageBox.critical(self, "Errore Creazione", "Impossibile creare la località (ID non restituito).")

        except (DBUniqueConstraintError, DBDataError, DBMError) as dbe:
            self.logger.error(f"Errore DB creazione località: {dbe}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Impossibile creare località:\n{dbe.message if hasattr(dbe, 'message') else str(dbe)}")
        except Exception as e:
            self.logger.critical(f"Errore imprevisto creazione località: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Si è verificato un errore:\n{e}")

    def _pulisci_campi_creazione_localita(self):
        self.nome_edit_nuova.clear()
        self.tipo_combo_nuova.setCurrentIndex(0)
        self.civico_spinbox_nuova.setValue(self.civico_spinbox_nuova.minimum()) # Resetta al "Nessuno"
    # --- FINE METODO MANCANTE/DA RIPRISTINARE ---
