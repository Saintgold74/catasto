#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilità per Gestionale Catasto Storico
======================================
Autore: Marco Santoro
Data: 31/05/2025
Versione: 1.0
"""

import logging
import bcrypt
import json
import csv
import uuid
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

# Importazioni PyQt5 per conversione date
from PyQt5.QtCore import QDate, QDateTime

# Configurazione del logger
logging.basicConfig(
    filename='catasto_gui.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
gui_logger = logging.getLogger('catasto_gui')

# Costanti per la configurazione delle tabelle dei possessori
COLONNE_POSSESSORI_DETTAGLI_NUM = 6
COLONNE_POSSESSORI_DETTAGLI_LABELS = ["ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]

COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM = 5
COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS = ["ID", "Nome Completo", "Paternità", "Comune Rif.", "Num. Partite"]

COLONNE_INSERIMENTO_POSSESSORI_NUM = 4
COLONNE_INSERIMENTO_POSSESSORI_LABELS = ["ID", "Nome Completo", "Paternità", "Comune Riferimento"]

NUOVE_ETICHETTE_POSSESSORI = ["id", "nome_completo", "codice_fiscale", "data_nascita", "cognome_nome", 
                             "paternita", "indirizzo_residenza", "comune_residenza_nome", 
                             "attivo", "note", "num_partite"]

# Nomi per le chiavi di QSettings
SETTINGS_DB_TYPE = "Database/Type"
SETTINGS_DB_HOST = "Database/Host"
SETTINGS_DB_PORT = "Database/Port"
SETTINGS_DB_NAME = "Database/DBName"
SETTINGS_DB_USER = "Database/User"
SETTINGS_DB_SCHEMA = "Database/Schema"

# Stylesheet Moderno 
MODERN_STYLESHEET = """
    * {
        font-family: Segoe UI, Arial, sans-serif;
        font-size: 10pt;
        color: #333333;
    }
    QMainWindow {
        background-color: #F4F4F4;
    }
    QWidget {
        background-color: #F4F4F4;
    }
    QLabel {
        color: #202020;
        background-color: transparent;
        padding: 2px;
    }
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QComboBox {
        background-color: #FFFFFF;
        color: #333333;
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        padding: 5px;
        selection-background-color: #0078D4;
        selection-color: white;
    }
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, 
    QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QComboBox:focus {
        border: 1px solid #0078D4;
    }
    QLineEdit[readOnly="true"], QTextEdit[readOnly="true"] {
        background-color: #E9E9E9;
        color: #505050;
    }
    QPushButton {
        background-color: #0078D4;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 15px;
        font-weight: bold;
        min-width: 80px;
    }
    QPushButton:hover {
        background-color: #005A9E;
    }
    QPushButton:pressed {
        background-color: #004C8A;
    }
    QPushButton:disabled {
        background-color: #BDBDBD;
        color: #757575;
    }
    QTabWidget::pane {
        border-top: 1px solid #D0D0D0;
        background-color: #FFFFFF;
        padding: 5px;
    }
    QTabBar::tab {
        background: #E0E0E0;
        color: #424242;
        border: 1px solid #D0D0D0;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 7px 12px;
        margin-right: 2px;
    }
    QTabBar::tab:hover {
        background: #D0D0D0;
    }
    QTabBar::tab:selected {
        background: #FFFFFF;
        color: #0078D4;
        font-weight: bold;
        border-color: #D0D0D0;
        border-bottom-color: #FFFFFF; 
    }
    QTableWidget {
        gridline-color: #E0E0E0;
        background-color: #FFFFFF;
        alternate-background-color: #F9F9F9;
        selection-background-color: #60AFFF;
        selection-color: #FFFFFF;
        border: 1px solid #D0D0D0;
    }
    QHeaderView::section {
        background-color: #F0F0F0;
        color: #333333;
        padding: 5px;
        border: 1px solid #D0D0D0;
        border-bottom-width: 1px; 
        font-weight: bold;
    }
    QComboBox::drop-down {
        border: none;
        background: transparent;
        width: 20px;
    }
    QComboBox::down-arrow {
        image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-arrow-down-16.png);
    }
    QComboBox QAbstractItemView {
        border: 1px solid #D0D0D0;
        selection-background-color: #0078D4;
        selection-color: white;
        background-color: white;
        padding: 2px;
    }
    QGroupBox {
        background-color: #FFFFFF;
        border: 1px solid #D0D0D0;
        border-radius: 4px;
        margin-top: 1.5ex;
        padding: 10px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px 0 5px;
        left: 10px;
        color: #0078D4;
    }
    QCheckBox {
        spacing: 5px;
    }
    QCheckBox::indicator {
        width: 16px; height: 16px;
        border: 1px solid #B0B0B0; border-radius: 3px;
    }
    QCheckBox::indicator:unchecked {
        background-color: white;
    }
    QCheckBox::indicator:checked {
        background-color: #0078D4;
        border-color: #0078D4;
        image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png);
    }
    QRadioButton {
        spacing: 5px;
    }
    QRadioButton::indicator {
        width: 16px; height: 16px;
        border: 1px solid #B0B0B0; border-radius: 8px;
    }
    QRadioButton::indicator:unchecked {
        background-color: white;
    }
    QRadioButton::indicator:checked {
        background-color: #0078D4;
        border-color: #0078D4;
        image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png);
    }
    QScrollBar:vertical {
        border: none;
        background: #F0F0F0;
        width: 12px;
        margin: 12px 0 12px 0;
    }
    QScrollBar::handle:vertical {
        background: #CDCDCD;
        min-height: 20px;
        border-radius: 6px;
    }
    QScrollBar::add-line:vertical {
        height: 12px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
    }
    QScrollBar::sub-line:vertical {
        height: 12px;
        subcontrol-position: top;
        subcontrol-origin: margin;
    }
    QScrollBar:horizontal {
        border: none;
        background: #F0F0F0;
        height: 12px;
        margin: 0 12px 0 12px;
    }
    QScrollBar::handle:horizontal {
        background: #CDCDCD;
        min-width: 20px;
        border-radius: 6px;
    }
    QScrollBar::add-line:horizontal {
        width: 12px;
        subcontrol-position: right;
        subcontrol-origin: margin;
    }
    QScrollBar::sub-line:horizontal {
        width: 12px;
        subcontrol-position: left;
        subcontrol-origin: margin;
    }
    QMenu {
        background-color: #FFFFFF;
        border: 1px solid #D0D0D0;
    }
    QMenu::item {
        padding: 5px 20px 5px 20px;
    }
    QMenu::item:selected { background-color: #0078D4; color: white; }
"""

# Eccezioni personalizzate per il database
class DBMError(Exception):
    pass

class DBUniqueConstraintError(DBMError):
    pass

class DBNotFoundError(DBMError):
    pass

class DBDataError(DBMError):
    pass

# Funzioni di utilità per la gestione delle password
def _hash_password(password: str) -> str:
    """Genera un hash per la password fornita."""
    # Genera un salt casuale e poi crea l'hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')  # Convertiamo in stringa per il DB

def _verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verifica se la password fornita corrisponde all'hash memorizzato."""
    try:
        return bcrypt.checkpw(
            provided_password.encode('utf-8'), 
            stored_hash.encode('utf-8'))
    except Exception as e:
        gui_logger.error(f"Errore nella verifica della password: {e}")
        return False

# Funzioni di utilità per le impostazioni dell'applicazione
def set_qsettings_defaults(settings):
    """
    Imposta i valori predefiniti per le impostazioni dell'applicazione se non esistono già.
    
    Args:
        settings: Oggetto QSettings da inizializzare
    """
    # Impostazioni database
    if not settings.contains(SETTINGS_DB_TYPE):
        settings.setValue(SETTINGS_DB_TYPE, "postgresql")
    if not settings.contains(SETTINGS_DB_HOST):
        settings.setValue(SETTINGS_DB_HOST, "localhost")
    if not settings.contains(SETTINGS_DB_PORT):
        settings.setValue(SETTINGS_DB_PORT, 5432)
    if not settings.contains(SETTINGS_DB_NAME):
        settings.setValue(SETTINGS_DB_NAME, "catasto_storico")
    if not settings.contains(SETTINGS_DB_USER):
        settings.setValue(SETTINGS_DB_USER, "postgres")
    if not settings.contains(SETTINGS_DB_SCHEMA):
        settings.setValue(SETTINGS_DB_SCHEMA, "public")
    
    # Altre impostazioni applicazione
    if not settings.contains("UI/Theme"):
        settings.setValue("UI/Theme", "modern")
    if not settings.contains("UI/FontSize"):
        settings.setValue("UI/FontSize", 10)
    if not settings.contains("App/LastComune"):
        settings.setValue("App/LastComune", "")

# Funzioni di utilità per la conversione di date
def qdate_to_datetime(q_date: QDate) -> datetime:
    """Converte un QDate in un oggetto datetime di Python."""
    return datetime(q_date.year(), q_date.month(), q_date.day())

def datetime_to_qdate(dt_date: Optional[date]) -> QDate:
    """Converte un oggetto date/datetime di Python in un QDate."""
    if not dt_date:
        return QDate()
    return QDate(dt_date.year, dt_date.month, dt_date.day)

# Alias per compatibilità
CSS_STYLE = MODERN_STYLESHEET
QDate_to_datetime = qdate_to_datetime
datetime_to_QDate = datetime_to_qdate

# Classe per gestire errori del database catasto
class CatastoDBError(Exception):
    """Eccezione generica per errori del database del catasto"""
    pass

# Verifica disponibilità della libreria FPDF per export PDF
FPDF_AVAILABLE = False
try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    FPDF_AVAILABLE = True
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    gui_logger.warning("Libreria FPDF non disponibile, export PDF disabilitato")
