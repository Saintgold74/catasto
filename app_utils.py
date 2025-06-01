import sys
import logging # Per ottenere il logger configurato in gui_main
import bcrypt
import csv
import json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

from PyQt5.QtWidgets import (QDialog, QLineEdit, QComboBox, QPushButton, QLabel, QVBoxLayout,
                             QHBoxLayout, QListWidget, QListWidgetItem, QTableWidget,
                             QSpinBox, QDateEdit, QDateTimeEdit, QDoubleSpinBox,QTableWidgetItem , # Aggiunte per dialoghi
                             QApplication, QStyle, QFileDialog, QMessageBox, QCheckBox, QFormLayout, QDialogButtonBox) # E altre necessarie per i dialoghi
from PyQt5.QtCore import Qt, QDate, QDateTime # Aggiunto QDateTime
# In app_utils.py, dopo le importazioni PyQt e standard:
# Nessuna dipendenza ciclica dagli altri due moduli GUI (gui_main, gui_widgets) dovrebbe essere necessaria qui.
# Questo modulo fornisce utility AGLI ALTRI.
# Se necessario, importa CatastoDBManager per type hinting o usi diretti limitati:
from catasto_db_manager import CatastoDBManager


# Importa FPDF se disponibile
try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False
    # class FPDF: pass # Fallback se si volessero istanziare le classi PDF anche senza fpdf
                     # ma è meglio gestire con FPDF_AVAILABLE
    # Potrebbe essere utile definire classi PDF vuote qui se FPDF non è disponibile,
    # per evitare NameError se il codice tenta di usarle condizionalmente.
    class PDFPartita: pass 
    class PDFPossessore: pass
    class GenericTextReportPDF: pass

# Gestione Eccezioni DB (potrebbero essere importate da catasto_db_manager se si preferisce)
# Se rimangono qui, assicurarsi che non ci siano conflitti se catasto_db_manager le definisce pure.
# Idealmente, dovrebbero essere definite UNA SOLA VOLTA in catasto_db_manager e importate qui.
# Per ora, manteniamo il fallback come nel suo codice originale.
try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception): pass
    class DBUniqueConstraintError(DBMError): pass
    class DBNotFoundError(DBMError): pass
    class DBDataError(DBMError): pass
    # QMessageBox.warning(None, "Avviso Importazione", "Eccezioni DB personalizzate non trovate in app_utils.")

# Eventuale importazione di CatastoDBManager se alcune utility qui ne avessero bisogno direttamente,
# ma è più probabile che i dialoghi ricevano l'istanza db_manager come parametro.
# from catasto_db_manager import CatastoDBManager
# Costanti per le colonne delle tabelle, se usate in più punti

COLONNE_POSSESSORI_DETTAGLI_NUM = 6 # Esempio: ID, Nome Compl, Cognome/Nome, Paternità, Quota, Titolo
COLONNE_POSSESSORI_DETTAGLI_LABELS = ["ID Poss.", "Nome Completo", "Cognome Nome", "Paternità", "Quota", "Titolo"]
# Costanti per la configurazione delle tabelle dei possessori, se usate in più punti
# Scegli nomi specifici se diverse tabelle hanno diverse configurazioni
COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM = 5 # Esempio: ID, Nome Compl, Paternità, Comune, Num. Partite
COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS = ["ID", "Nome Completo", "Paternità", "Comune Rif.", "Num. Partite"]

# Per InserimentoPossessoreWidget, se la sua tabella è diversa:
COLONNE_INSERIMENTO_POSSESSORI_NUM = 4 # Esempio: ID, Nome Completo, Paternità, Comune
COLONNE_INSERIMENTO_POSSESSORI_LABELS = ["ID", "Nome Completo", "Paternità", "Comune Riferimento"]

NUOVE_ETICHETTE_POSSESSORI = ["id", "nome_completo", "codice_fiscale", "data_nascita", "cognome_nome", "paternita", "indirizzo_residenza", "comune_residenza_nome", "attivo", "note", "num_partite"]
# Nomi per le chiavi di QSettings (globali o definite prima di run_gui_app)
# --- Nomi per le chiavi di QSettings (definisci globalmente o prima di run_gui_app) ---
SETTINGS_DB_TYPE = "Database/Type"
SETTINGS_DB_HOST = "Database/Host"
SETTINGS_DB_PORT = "Database/Port"
SETTINGS_DB_NAME = "Database/DBName"
SETTINGS_DB_USER = "Database/User"
SETTINGS_DB_SCHEMA = "Database/Schema"
# Non salviamo la password in QSettings
SETTINGS_DB_PASSWORD = "Database/Password"  # Non usato, ma definito per completezza
# --- Funzioni Helper per Password ---
def _hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

def _verify_password(stored_hash: str, provided_password: str) -> bool:
    try:
        stored_hash_bytes = stored_hash.encode('utf-8')
        provided_password_bytes = provided_password.encode('utf-8')
        return bcrypt.checkpw(provided_password_bytes, stored_hash_bytes)
    except ValueError:
        gui_logger.error(f"Tentativo di verifica con hash non valido: {stored_hash[:10]}...")
        return False
    except Exception as e:
        gui_logger.error(f"Errore imprevisto durante la verifica bcrypt: {e}")
        return False
def qdate_to_datetime(q_date: QDate) -> Optional[date]:
    if q_date.isNull() or not q_date.isValid(): # Controlla anche isValid
        return None
    return date(q_date.year(), q_date.month(), q_date.day())

def datetime_to_qdate(dt_date: Optional[date]) -> QDate:
    if dt_date is None:
        return QDate() # Restituisce una QDate "nulla"
    return QDate(dt_date.year, dt_date.month, dt_date.day)

class QPasswordLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        
# --- Classi PDF (da python_example.py) ---
if FPDF_AVAILABLE:
    class PDFPartita(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, 'Dettaglio Partita Catastale', 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'B', 8) # Cambiato in Bold per coerenza
            self.cell(0, 10, f'Pagina {self.page_no()}', border=0, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

        def chapter_title(self, title):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 6, title, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            self.ln(2)

        def chapter_body(self, data_dict):
            self.set_font('Helvetica', '', 10)
            page_width = self.w - self.l_margin - self.r_margin
            for key, value in data_dict.items():
                text_to_write = f"{key.replace('_', ' ').title()}: {value if value is not None else 'N/D'}"
                try:
                    self.multi_cell(page_width, 5, text_to_write, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                except Exception as e: # FPDFException non è definita se FPDF non è importato
                    if "Not enough horizontal space" in str(e):
                        gui_logger.warning(f"FPDFException: {e} per il testo: {text_to_write[:100]}...")
                        self.multi_cell(page_width, 5, f"{key.replace('_', ' ').title()}: [ERRORE DATI TROPPO LUNGHI]", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    else:
                        raise e
            self.ln(2) # Aggiungo un po' di spazio

        def simple_table(self, headers, data_rows, col_widths_percent=None):
            self.set_font('Helvetica', 'B', 9) # Header in grassetto
            effective_page_width = self.w - self.l_margin - self.r_margin
            
            if col_widths_percent:
                col_widths = [effective_page_width * (p/100) for p in col_widths_percent]
            else:
                num_cols = len(headers)
                default_col_width = effective_page_width / num_cols if num_cols > 0 else effective_page_width
                col_widths = [default_col_width] * num_cols
            
            for i, header in enumerate(headers):
                align = 'C' # Centra gli header
                if i == len(headers) - 1: # Ultima cella della riga header
                    self.cell(col_widths[i], 7, header, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                else:
                    self.cell(col_widths[i], 7, header, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)

            self.set_font('Helvetica', '', 8)
            for row in data_rows:
                for i, item in enumerate(row):
                    text = str(item) if item is not None else ''
                    align = 'L' # Dati allineati a sinistra
                    if i == len(row) - 1: # Ultima cella della riga dati
                        self.cell(col_widths[i], 6, text, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                    else:
                        self.cell(col_widths[i], 6, text, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)
            self.ln(4)

    class PDFPossessore(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, 'Dettaglio Possessore Catastale', border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8) # Originale era 'I'
            self.cell(0, 10, f'Pagina {self.page_no()}', border=0, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

        def chapter_title(self, title):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 6, title, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
            self.ln(2)

        def chapter_body(self, data_dict):
            self.set_font('Helvetica', '', 10)
            page_width = self.w - self.l_margin - self.r_margin
            for key, value in data_dict.items():
                text_to_write = f"{key.replace('_', ' ').title()}: {value if value is not None else 'N/D'}"
                try:
                    self.multi_cell(page_width, 5, text_to_write, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                except Exception as e: # FPDFException
                    if "Not enough horizontal space" in str(e):
                        gui_logger.warning(f"FPDFException (chapter_body possessore): {e} per testo: {text_to_write[:100]}...")
                        self.multi_cell(page_width, 5, f"{key.replace('_', ' ').title()}: [DATI TROPPO LUNGHI]", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                    else: raise e
            self.ln(2)


        def simple_table(self, headers, data_rows, col_widths_percent=None):
            self.set_font('Helvetica', 'B', 9)
            effective_page_width = self.w - self.l_margin - self.r_margin
            
            if col_widths_percent:
                col_widths = [effective_page_width * (p/100) for p in col_widths_percent]
            else:
                num_cols = len(headers)
                default_col_width = effective_page_width / num_cols if num_cols > 0 else effective_page_width
                col_widths = [default_col_width] * num_cols

            for i, header in enumerate(headers):
                align = 'C'
                if i == len(headers) - 1:
                    self.cell(col_widths[i], 7, header, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                else:
                    self.cell(col_widths[i], 7, header, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)

            self.set_font('Helvetica', '', 8)
            for row in data_rows:
                for i, item in enumerate(row):
                    text = str(item) if item is not None else ''
                    align = 'L'
                    if i == len(row) - 1:
                        self.cell(col_widths[i], 6, text, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                    else:
                        self.cell(col_widths[i], 6, text, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)
            self.ln(4)
else: # FPDF non disponibile
    class PDFPartita: pass # Definizioni vuote per evitare errori di NameError
    class PDFPossessore: pass
if FPDF_AVAILABLE:
    class GenericTextReportPDF(FPDF):
        def __init__(self, orientation='P', unit='mm', format='A4', report_title="Report"):
            super().__init__(orientation, unit, format)
            self.report_title = report_title
            self.set_auto_page_break(auto=True, margin=15)
            self.set_left_margin(15)
            self.set_right_margin(15)
            self.set_font('Helvetica', '', 10) # Font di default per il corpo del report

        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, self.report_title, 0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.ln(5) # Spazio dopo l'header

        def footer(self):
            self.set_y(-15) # Posizione a 1.5 cm dal fondo
            self.set_font('Helvetica', 'I', 8)
            page_num_text = f'Pagina {self.page_no()} / {{nb}}' # {{nb}} è un alias per il numero totale di pagine
            self.cell(0, 10, page_num_text, border=0, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

        def add_report_text(self, text_content: str):
            """Aggiunge il contenuto testuale del report al PDF."""
            self.set_font('Courier', '', 9) # Usiamo un font monospazio per testo preformattato
                                           # Potrebbe scegliere 'Helvetica' se preferisce
            # Sostituisci i caratteri di tabulazione con spazi per un rendering migliore in PDF
            text_content = text_content.replace('\t', '    ') 
            
            # multi_cell gestisce automaticamente i ritorni a capo e il wrapping del testo
            self.multi_cell(0, 5, text_content) # Larghezza 0 = larghezza piena, altezza riga 5mm
            self.ln()
            
# --- Funzioni di esportazione adattate per GUI ---
def gui_esporta_partita_json(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    # Recupera i dati usando il metodo del db_manager che restituisce il dizionario completo
    # Questo metodo è get_partita_data_for_export, NON export_partita_json
    dict_data = db_manager.get_partita_data_for_export(partita_id) 
    
    if dict_data:
        # --- INIZIO MODIFICA ---
        def json_serial(obj):
            """JSON serializer per oggetti non serializzabili di default (date/datetime)."""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            # Potresti voler gestire altri tipi qui se necessario
            # Esempio per Decimal (se usi la libreria decimal):
            # from decimal import Decimal
            # if isinstance(obj, Decimal):
            #    return str(obj) # o float(obj) a seconda della precisione richiesta
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        
        try:
            json_data_str = json.dumps(dict_data, indent=4, ensure_ascii=False, default=json_serial)
        except TypeError as te:
            gui_logger.error(f"Errore di serializzazione JSON per partita ID {partita_id}: {te} - Dati: {dict_data}")
            QMessageBox.critical(parent_widget, "Errore di Serializzazione", 
                                 f"Errore durante la conversione dei dati della partita in JSON: {te}\n"
                                 "Controllare i log per i dettagli.")
            return
        # --- FINE MODIFICA ---

        default_filename = f"partita_{partita_id}_{date.today().isoformat()}.json"
        filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva JSON Partita", default_filename, "JSON Files (*.json)")
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_data_str)
                QMessageBox.information(parent_widget, "Esportazione JSON", f"Partita esportata con successo in:\n{filename}")
            except Exception as e:
                gui_logger.error(f"Errore durante il salvataggio del file JSON per partita ID {partita_id}: {e}")
                QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante il salvataggio del file JSON:\n{e}")
    else:
        QMessageBox.warning(parent_widget, "Errore Dati", f"Partita con ID {partita_id} non trovata o errore nel recupero dei dati per l'esportazione.")


def gui_esporta_partita_csv(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati partita non validi per l'esportazione CSV.")
        return

    default_filename = f"partita_{partita_id}_{date.today()}.csv"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva CSV Partita", default_filename, "CSV Files (*.csv)")
    if not filename: return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            p = partita_data['partita']
            writer.writerow(['--- DETTAGLI PARTITA ---'])
            for key, value in p.items(): writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])

            if partita_data.get('possessori'):
                writer.writerow(['--- POSSESSORI ---'])
                headers = list(partita_data['possessori'][0].keys()) if partita_data['possessori'] else []
                if headers: writer.writerow([h.replace('_', ' ').title() for h in headers])
                for pos in partita_data['possessori']: writer.writerow([pos.get(h) for h in headers])
                writer.writerow([])

            if partita_data.get('immobili'):
                writer.writerow(['--- IMMOBILI ---'])
                headers = list(partita_data['immobili'][0].keys()) if partita_data['immobili'] else []
                if headers: writer.writerow([h.replace('_', ' ').title() for h in headers])
                for imm in partita_data['immobili']: writer.writerow([imm.get(h) for h in headers])
                writer.writerow([])
            
            if partita_data.get('variazioni'):
                writer.writerow(['--- VARIAZIONI ---'])
                headers = list(partita_data['variazioni'][0].keys()) if partita_data['variazioni'] else []
                if headers: writer.writerow([h.replace('_', ' ').title() for h in headers])
                for var in partita_data['variazioni']: writer.writerow([var.get(h) for h in headers])
        QMessageBox.information(parent_widget, "Esportazione CSV", f"Partita esportata con successo in:\n{filename}")
    except Exception as e:
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione CSV:\n{e}")

def gui_esporta_partita_pdf(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    if not FPDF_AVAILABLE:
        QMessageBox.warning(parent_widget, "Funzionalità non disponibile", "La libreria FPDF è necessaria per l'esportazione in PDF, ma non è installata.")
        return
        
    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati partita non validi per l'esportazione PDF.")
        return

    default_filename = f"partita_{partita_id}_{date.today()}.pdf"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva PDF Partita", default_filename, "PDF Files (*.pdf)")
    if not filename: return

    try:
        pdf = PDFPartita()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        pdf.add_page()
        
        p = partita_data['partita']
        pdf.chapter_title('Dettagli Partita')
        pdf.chapter_body({k: p.get(k) for k in ['id', 'comune_nome', 'numero_partita', 'tipo', 'data_impianto', 'stato', 'data_chiusura', 'numero_provenienza']})

        if partita_data.get('possessori'):
            pdf.chapter_title('Possessori')
            headers = ['ID', 'Nome Completo', 'Titolo', 'Quota']
            data_rows = [[pos.get('id'), pos.get('nome_completo'), pos.get('titolo'), pos.get('quota')] for pos in partita_data['possessori']]
            pdf.simple_table(headers, data_rows)

        if partita_data.get('immobili'):
            pdf.chapter_title('Immobili')
            headers = ['ID', 'Natura', 'Località', 'Class.', 'Consist.']
            data_rows = [[imm.get('id'), imm.get('natura'), f"{imm.get('localita_nome','')} {imm.get('civico','')}".strip(), imm.get('classificazione'), imm.get('consistenza')] for imm in partita_data['immobili']]
            pdf.simple_table(headers, data_rows)

        if partita_data.get('variazioni'):
            pdf.chapter_title('Variazioni')
            headers = ['ID', 'Tipo', 'Data Var.', 'Contratto', 'Notaio']
            data_rows = []
            for var in partita_data['variazioni']:
                contr_str = f"{var.get('contratto_tipo','')} del {var.get('data_contratto','')}" if var.get('contratto_tipo') else ''
                data_rows.append([var.get('id'), var.get('tipo'), var.get('data_variazione'), contr_str, var.get('notaio')])
            pdf.simple_table(headers, data_rows)
            
        pdf.output(filename)
        QMessageBox.information(parent_widget, "Esportazione PDF", f"Partita esportata con successo in:\n{filename}")
    except Exception as e:
        gui_logger.exception("Errore esportazione PDF partita (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione PDF:\n{e}")


def gui_esporta_possessore_json(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    dict_data = db_manager.get_possessore_data_for_export(possessore_id)
    if dict_data:
        json_data_str = json.dumps(dict_data, indent=4, ensure_ascii=False)
        default_filename = f"possessore_{possessore_id}_{date.today()}.json"
        filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva JSON Possessore", default_filename, "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f: f.write(json_data_str)
                QMessageBox.information(parent_widget, "Esportazione JSON", f"Possessore esportato con successo in:\n{filename}")
            except Exception as e: QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante il salvataggio del file JSON:\n{e}")
    else: QMessageBox.warning(parent_widget, "Errore Dati", f"Possessore con ID {possessore_id} non trovato o errore recupero dati.")

def gui_esporta_possessore_csv(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati possessore non validi per l'esportazione CSV.")
        return

    default_filename = f"possessore_{possessore_id}_{date.today()}.csv"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva CSV Possessore", default_filename, "CSV Files (*.csv)")
    if not filename: return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            p_info = possessore_data['possessore']
            writer.writerow(['--- DETTAGLI POSSESSORE ---'])
            for key, value in p_info.items(): writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])

            if possessore_data.get('partite'): # La chiave è 'partite' dal JSON, non 'partite_associate'
                writer.writerow(['--- PARTITE ASSOCIATE ---'])
                headers = list(possessore_data['partite'][0].keys()) if possessore_data['partite'] else []
                if headers: writer.writerow([h.replace('_', ' ').title() for h in headers])
                for part in possessore_data['partite']: writer.writerow([part.get(h) for h in headers])
                writer.writerow([])
            
            if possessore_data.get('immobili'):
                writer.writerow(['--- IMMOBILI ASSOCIATI (TRAMITE PARTITE) ---'])
                headers = list(possessore_data['immobili'][0].keys()) if possessore_data['immobili'] else []
                if headers: writer.writerow([h.replace('_', ' ').title() for h in headers])
                for imm in possessore_data['immobili']: writer.writerow([imm.get(h) for h in headers])

        QMessageBox.information(parent_widget, "Esportazione CSV", f"Possessore esportato con successo in:\n{filename}")
    except Exception as e:
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione CSV:\n{e}")

def gui_esporta_possessore_pdf(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    if not FPDF_AVAILABLE:
        QMessageBox.warning(parent_widget, "Funzionalità non disponibile", "La libreria FPDF è necessaria per l'esportazione in PDF, ma non è installata.")
        return
        
    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati possessore non validi per l'esportazione PDF.")
        return

    default_filename = f"possessore_{possessore_id}_{date.today()}.pdf"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva PDF Possessore", default_filename, "PDF Files (*.pdf)")
    if not filename: return

    try:
        pdf = PDFPossessore()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        pdf.add_page()
        
        p_info = possessore_data['possessore']
        pdf.chapter_title('Dettagli Possessore')
        details_poss = {
            'ID Possessore': p_info.get('id'), 'Nome Completo': p_info.get('nome_completo'),
            'Comune Riferimento': p_info.get('comune_nome'), # Aggiunto comune_nome
            'Paternità': p_info.get('paternita'),
            'Stato': "Attivo" if p_info.get('attivo') else "Non Attivo",
        }
        pdf.chapter_body(details_poss)

        if possessore_data.get('partite'):
            pdf.chapter_title('Partite Associate')
            headers = ['ID Part.', 'Num. Partita', 'Comune', 'Tipo', 'Quota', 'Titolo']
            col_widths_percent = [10, 15, 25, 15, 15, 20] 
            data_rows = []
            for part in possessore_data['partite']:
                data_rows.append([
                    part.get('id'), part.get('numero_partita'), part.get('comune_nome'),
                    part.get('tipo'), part.get('quota'), part.get('titolo')
                ])
            pdf.simple_table(headers, data_rows, col_widths_percent=col_widths_percent)
        
        if possessore_data.get('immobili'):
            pdf.chapter_title('Immobili Associati (tramite Partite)')
            headers = ['ID Imm.', 'Natura', 'Località', 'Part. N.', 'Comune Part.']
            col_widths_percent_imm = [10, 30, 25, 15, 20]
            data_rows_imm = []
            for imm in possessore_data['immobili']:
                data_rows_imm.append([
                    imm.get('id'), imm.get('natura'), imm.get('localita_nome'),
                    imm.get('numero_partita'), imm.get('comune_nome')
                ])
            pdf.simple_table(headers, data_rows_imm, col_widths_percent_imm)

        pdf.output(filename)
        QMessageBox.information(parent_widget, "Esportazione PDF", f"Possessore esportato con successo in:\n{filename}")
    except Exception as e:
        gui_logger.exception("Errore esportazione PDF possessore (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione PDF:\n{e}")

class ComuneSelectionDialog(QDialog): # ASSICURATI CHE SIA QUI O PRIMA DI DOVE SERVE
    def __init__(self, db_manager: CatastoDBManager, parent=None, title="Seleziona Comune"):
        super(ComuneSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.selected_comune_id: Optional[int] = None
        self.selected_comune_name: Optional[str] = None
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        layout = QVBoxLayout(self)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Filtra comuni:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Digita per filtrare...")
        self.search_edit.textChanged.connect(self.filter_comuni)
        search_layout.addWidget(self.search_edit)
        
        self.search_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_BrowserReload), "")
        self.search_button.setToolTip("Aggiorna lista comuni")
        self.search_button.clicked.connect(self.filter_comuni) # Usa self.filter_comuni
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        self.comuni_list = QListWidget()
        self.comuni_list.setAlternatingRowColors(True)
        self.comuni_list.itemDoubleClicked.connect(self.handle_select) # Connessione corretta
        layout.addWidget(self.comuni_list)
        
        buttons_layout = QHBoxLayout()
        self.select_button = QPushButton("Seleziona")
        self.select_button.setDefault(True)
        self.select_button.clicked.connect(self.handle_select) # Connessione corretta
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.select_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)
        
        self.load_comuni()

    def load_comuni(self, filter_text: Optional[str] = None):
        self.comuni_list.clear()
        try:
            comuni = self.db_manager.get_comuni(filter_text)
            if comuni:
                for comune in comuni:
                    item = QListWidgetItem(f"{comune['nome']} (ID: {comune['id']}, {comune['provincia']})")
                    item.setData(Qt.UserRole, comune['id'])
                    item.setData(Qt.UserRole + 1, comune['nome']) # Per recuperare il nome facilmente
                    self.comuni_list.addItem(item)
            else:
                self.comuni_list.addItem("Nessun comune trovato.")
        except Exception as e:
            gui_logger.error(f"Errore caricamento comuni nel dialogo: {e}")
            self.comuni_list.addItem("Errore caricamento comuni.")

    def filter_comuni(self):
        filter_text = self.search_edit.text().strip()
        self.load_comuni(filter_text if filter_text else None)

    def handle_select(self):
        current_item = self.comuni_list.currentItem()
        if current_item and current_item.data(Qt.UserRole) is not None:
            self.selected_comune_id = current_item.data(Qt.UserRole)
            self.selected_comune_name = current_item.data(Qt.UserRole + 1) # Salva anche il nome
            self.accept()
        else:
            QMessageBox.warning(self, "Attenzione", "Seleziona un comune valido dalla lista.")
class PartitaSearchDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super(PartitaSearchDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.selected_partita_id = None
        
        self.setWindowTitle("Ricerca Partita")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        # Form di ricerca
        form_group = QGroupBox("Criteri di Ricerca")
        form_layout = QGridLayout()
        
        # Comune
        comune_label = QLabel("Comune:")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_id = None
        self.comune_display = QLabel("Tutti i comuni")
        self.clear_comune_button = QPushButton("Cancella")
        self.clear_comune_button.clicked.connect(self.clear_comune)
        
        form_layout.addWidget(comune_label, 0, 0)
        form_layout.addWidget(self.comune_button, 0, 1)
        form_layout.addWidget(self.comune_display, 0, 2)
        form_layout.addWidget(self.clear_comune_button, 0, 3)
        
        # Numero partita
        numero_label = QLabel("Numero Partita:")
        self.numero_edit = QSpinBox()
        self.numero_edit.setMinimum(0)
        self.numero_edit.setMaximum(9999)
        self.numero_edit.setSpecialValueText("Qualsiasi")
        
        form_layout.addWidget(numero_label, 1, 0)
        form_layout.addWidget(self.numero_edit, 1, 1)
        
        # Possessore
        possessore_label = QLabel("Nome Possessore:")
        self.possessore_edit = QLineEdit()
        self.possessore_edit.setPlaceholderText("Qualsiasi possessore")
        
        form_layout.addWidget(possessore_label, 2, 0)
        form_layout.addWidget(self.possessore_edit, 2, 1, 1, 3)
        
        # Natura immobile
        natura_label = QLabel("Natura Immobile:")
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Qualsiasi natura immobile")
        
        form_layout.addWidget(natura_label, 3, 0)
        form_layout.addWidget(self.natura_edit, 3, 1, 1, 3)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Pulsante ricerca
        search_button = QPushButton("Cerca")
        search_button.clicked.connect(self.do_search)
        layout.addWidget(search_button)
        
        # Tabella risultati
        results_group = QGroupBox("Risultati")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["ID", "Comune", "Numero", "Tipo", "Stato"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.itemDoubleClicked.connect(self.select_partita)
        
        results_layout.addWidget(self.results_table)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Seleziona")
        self.select_button.clicked.connect(self.select_partita)
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.select_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
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
        self.comune_display.setText("Tutti i comuni")
    
    def do_search(self):
        """Esegue la ricerca partite in base ai criteri."""
        # Prepara i parametri
        comune_id = self.comune_id
        numero_partita = self.numero_edit.value() if self.numero_edit.value() > 0 else None
        possessore = self.possessore_edit.text().strip() or None
        natura = self.natura_edit.text().strip() or None
        
        # Esegue la ricerca
        partite = self.db_manager.search_partite(
            comune_id=comune_id,
            numero_partita=numero_partita,
            possessore=possessore,
            immobile_natura=natura
        )
        
        # Popola la tabella risultati
        self.results_table.setRowCount(0)
        
        for partita in partite:
            row_position = self.results_table.rowCount()
            self.results_table.insertRow(row_position)
            
            self.results_table.setItem(row_position, 0, QTableWidgetItem(str(partita.get('id', ''))))
            self.results_table.setItem(row_position, 1, QTableWidgetItem(partita.get('comune_nome', '')))
            self.results_table.setItem(row_position, 2, QTableWidgetItem(str(partita.get('numero_partita', ''))))
            self.results_table.setItem(row_position, 3, QTableWidgetItem(partita.get('tipo', '')))
            self.results_table.setItem(row_position, 4, QTableWidgetItem(partita.get('stato', '')))
        
        # Adatta le colonne al contenuto
        self.results_table.resizeColumnsToContents()
    
    def select_partita(self):
        """Seleziona la partita e accetta il dialogo."""
        selected_rows = self.results_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione", "Seleziona una partita dalla tabella.")
            return
        
        row = selected_rows[0].row()
        partita_id_item = self.results_table.item(row, 0)
        
        if partita_id_item and partita_id_item.text().isdigit():
            self.selected_partita_id = int(partita_id_item.text())
            self.accept()
        else:
            QMessageBox.warning(self, "Errore", "ID partita non valido.")
# --- Dialog per la Selezione dei Possessori ---
class PossessoreSelectionDialog(QDialog):
    def __init__(self, db_manager, comune_id, parent=None):
        super(PossessoreSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.selected_possessore = None
        
        self.setWindowTitle("Seleziona Possessore")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # Tab per selezione o creazione
        self.tabs = QTabWidget()
        
        # Tab Seleziona
        select_tab = QWidget()
        select_layout = QVBoxLayout()
        
        # Filtro
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filtra per nome:")
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare...")
        self.filter_edit.textChanged.connect(self.filter_possessori)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_edit)
        
        select_layout.addLayout(filter_layout)
        
        # Tabella possessori
        self.possessori_table = QTableWidget()
        self.possessori_table.setColumnCount(4)
        self.possessori_table.setHorizontalHeaderLabels(["ID", "Nome Completo", "Paternità", "Stato"])
        self.possessori_table.setAlternatingRowColors(True)
        self.possessori_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.possessori_table.setSelectionMode(QTableWidget.SingleSelection)
        self.possessori_table.itemDoubleClicked.connect(self.select_from_table)
        
        select_layout.addWidget(self.possessori_table)
        
        select_tab.setLayout(select_layout)
        self.tabs.addTab(select_tab, "Seleziona Esistente")
        
        # Tab Crea
        create_tab = QWidget()
        create_layout = QGridLayout()
        
        # Cognome e nome
        cognome_label = QLabel("Cognome e nome:")
        self.cognome_edit = QLineEdit()
        
        create_layout.addWidget(cognome_label, 0, 0)
        create_layout.addWidget(self.cognome_edit, 0, 1)
        
        # Paternità
        paternita_label = QLabel("Paternità:")
        self.paternita_edit = QLineEdit()
        
        create_layout.addWidget(paternita_label, 1, 0)
        create_layout.addWidget(self.paternita_edit, 1, 1)
        
        # Nome completo
        nome_completo_label = QLabel("Nome completo:")
        self.nome_completo_edit = QLineEdit()
        self.nome_completo_update_button = QPushButton("Genera da cognome+paternità")
        self.nome_completo_update_button.clicked.connect(self.update_nome_completo)
        
        create_layout.addWidget(nome_completo_label, 2, 0)
        create_layout.addWidget(self.nome_completo_edit, 2, 1)
        create_layout.addWidget(self.nome_completo_update_button, 2, 2)
        
        # Quota
        quota_label = QLabel("Quota (vuoto per esclusiva):")
        self.quota_edit = QLineEdit()
        self.quota_edit.setPlaceholderText("Es. 1/2, 1/3, ecc.")
        
        create_layout.addWidget(quota_label, 3, 0)
        create_layout.addWidget(self.quota_edit, 3, 1)
        
        create_tab.setLayout(create_layout)
        self.tabs.addTab(create_tab, "Crea Nuovo")
        
        layout.addWidget(self.tabs)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Seleziona")
        self.ok_button.clicked.connect(self.handle_selection)
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
        # Carica i possessori iniziali
        self.current_tab = 0
        self.tabs.currentChanged.connect(self.tab_changed)
        self.load_possessori()
    
    def tab_changed(self, index):
        """Gestisce il cambio di tab."""
        self.current_tab = index
        if index == 0:
            self.ok_button.setText("Seleziona")
        else:
            self.ok_button.setText("Crea e Seleziona")
    
    def load_possessori(self, filter_text: Optional[str] = None):
        self.possessori_table.setRowCount(0)
        self.possessori_table.setSortingEnabled(False)
        
        possessori_list: List[Dict[str, Any]] = []
        try:
            actual_filter_text = filter_text if filter_text and filter_text.strip() else None

            if self.comune_id is not None:
                # Scenario 1: Comune specificato
                gui_logger.debug(f"PossessoreSelectionDialog: Caricamento per comune_id={self.comune_id}, filtro='{actual_filter_text}'")
                temp_list = self.db_manager.get_possessori_by_comune(self.comune_id) # Questo dovrebbe già restituire tutti i campi necessari
                if actual_filter_text:
                    ft_lower = actual_filter_text.lower()
                    possessori_list = [
                        p for p in temp_list 
                        if ft_lower in p.get('nome_completo', '').lower() or \
                           (p.get('cognome_nome') and ft_lower in p.get('cognome_nome', '').lower())
                    ]
                else:
                    possessori_list = temp_list
            else: # Nessun comune_id specificato -> ricerca globale
                # Scenario 2: Ricerca globale (con o senza testo di filtro)
                # Se actual_filter_text è None, search_possessori_by_term_globally restituirà i primi N.
                gui_logger.debug(f"PossessoreSelectionDialog: Caricamento globale, filtro='{actual_filter_text}'")
                possessori_list = self.db_manager.search_possessori_by_term_globally(actual_filter_text) # Passa None se nessun filtro
                gui_logger.info(f"PossessoreSelectionDialog.load_possessori: Risultato da search_possessori_by_term_globally: {len(possessori_list)} elementi.")
            
            # Popolamento della tabella
            if possessori_list:
                gui_logger.info(f">>> Popolando possessori_table con {len(possessori_list)} righe.")
                self.possessori_table.setRowCount(len(possessori_list))
                for i, pos_data in enumerate(possessori_list):
                    col = 0
                    item_id_str = str(pos_data.get('id', 'N/D'))
                    item_nome_str = pos_data.get('nome_completo', 'N/D')
                    # Assicurati che 'paternita' e 'attivo' siano presenti nei risultati di entrambe le query
                    # (get_possessori_by_comune e search_possessori_by_term_globally)
                    item_pater_str = pos_data.get('paternita', 'N/D') 
                    item_stato_str = "Attivo" if pos_data.get('attivo', False) else "Non Attivo"
                    
                    gui_logger.debug(f"    Popolando riga {i}: ID='{item_id_str}', Nome='{item_nome_str}', Pater='{item_pater_str}', Stato='{item_stato_str}'")

                    self.possessori_table.setItem(i, col, QTableWidgetItem(item_id_str)); col+=1
                    self.possessori_table.setItem(i, col, QTableWidgetItem(item_nome_str)); col+=1
                    self.possessori_table.setItem(i, col, QTableWidgetItem(item_pater_str)); col+=1
                    self.possessori_table.setItem(i, col, QTableWidgetItem(item_stato_str)); col+=1
                self.possessori_table.resizeColumnsToContents()
                gui_logger.info(">>> Popolamento possessori_table completato.")
            # Mostra "Nessun risultato" solo se è stata tentata una ricerca attiva (con filtro o con comune)
            # O se la ricerca globale senza filtro non ha prodotto risultati (improbabile se ci sono dati).
            elif actual_filter_text or self.comune_id: 
                self.possessori_table.setRowCount(1)
                self.possessori_table.setItem(0, 0, QTableWidgetItem("Nessun possessore trovato con i criteri specificati."))
                self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())
            else: # Nessun filtro, nessun comune_id, e search_possessori_by_term_globally(None) ha restituito lista vuota
                self.possessori_table.setRowCount(1)
                self.possessori_table.setItem(0, 0, QTableWidgetItem("Nessun possessore presente nel database."))
                self.possessori_table.setSpan(0, 0, 1, self.possessori_table.columnCount())

        except Exception as e:
            gui_logger.error(f"Errore durante il caricamento dei possessori in PossessoreSelectionDialog: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare i possessori: {e}")
            # Mostra errore anche nella tabella
            self.possessori_table.setRowCount(1)
            self.possessori_table.setItem(0,0, QTableWidgetItem(f"Errore caricamento: {e}"))
            self.possessori_table.setSpan(0,0,1, self.possessori_table.columnCount())
        finally:
            self.possessori_table.setSortingEnabled(True)

    # Il metodo filter_possessori dovrebbe rimanere com'è, chiamando load_possessori con il testo.
    def filter_possessori(self): # Questo metodo è collegato a self.filter_edit.textChanged
        filter_text = self.filter_edit.text().strip()
        gui_logger.info(f">>> PossessoreSelectionDialog.filter_possessori: Testo filtro='{filter_text}'")
    
        # Chiama load_possessori; il testo del filtro verrà usato se comune_id è None
        self.load_possessori(filter_text if filter_text else None)

    
    
    def update_nome_completo(self):
        """Aggiorna il nome completo in base a cognome e paternità."""
        cognome = self.cognome_edit.text().strip()
        paternita = self.paternita_edit.text().strip()
        
        if cognome:
            nome_completo = cognome
            if paternita:
                nome_completo += f" {paternita}"
            
            self.nome_completo_edit.setText(nome_completo)
    
    def select_from_table(self, item):
        """Gestisce la selezione dalla tabella dei possessori."""
        row = item.row()
        self.handle_selection()
    
    def handle_selection(self):
        """Gestisce la selezione o creazione del possessore."""
        current_tab_index = self.tabs.currentIndex() # Assumendo che self.tabs sia il suo QTabWidget

        if current_tab_index == 0:  # Tab "Seleziona Esistente"
            selected_rows = self.possessori_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "Nessuna Selezione", "Seleziona un possessore dalla tabella.")
                return
            
            current_row = selected_rows[0].row()
            
            id_item = self.possessori_table.item(current_row, 0)
            nome_item = self.possessori_table.item(current_row, 1)
            # Aggiungi controlli per tutti gli item da cui leggi .text()
            paternita_item = self.possessori_table.item(current_row, 2) if self.possessori_table.columnCount() > 2 else None 
            # Nota: la tabella di selezione ha "Paternità" come colonna 2 (indice), non "Cognome Nome"
            
            if id_item and id_item.text().isdigit() and nome_item:
                self.selected_possessore = {
                    'id': int(id_item.text()),
                    'nome_completo': nome_item.text(),
                    'paternita': paternita_item.text() if paternita_item else None,
                    # 'cognome_nome' non è direttamente nella tabella di selezione, ma può essere nel dict del possessore
                    # Se il chiamante necessita di 'cognome_nome', andrebbe recuperato in altro modo o aggiunto ai dati
                }
                self.accept()
            else:
                QMessageBox.warning(self, "Errore Selezione", "Dati del possessore selezionato non validi o incompleti nella tabella.")
        
        elif current_tab_index == 1:  # Tab "Crea Nuovo"
            # --- USA I NOMI CORRETTI DEI WIDGET DEFINITI NELL'__INIT__ ---
            nome_completo = self.nome_completo_edit.text().strip()
            paternita = self.paternita_edit.text().strip()
            cognome_nome = self.cognome_edit.text().strip() # Questo è self.cognome_edit per il cognome/nome nel tab "Crea"
            # quota = self.quota_edit.text().strip() # La quota non è usata per creare il possessore, ma per il legame

            # --- Log di Debug per Verificare i Valori ---
            gui_logger.debug(f"DEBUG - Tab Crea Nuovo - Valori letti: nome_completo='{nome_completo}', cognome_nome='{cognome_nome}', paternita='{paternita}'")

            if not nome_completo:
                QMessageBox.warning(self, "Dati Mancanti", "Il 'Nome Completo' è obbligatorio.")
                self.nome_completo_edit.setFocus()
                return
            
            if not cognome_nome: # Questo è il controllo che le dà problemi
                QMessageBox.warning(self, "Dati Mancanti", "Il campo 'Cognome e nome' è obbligatorio.")
                self.cognome_edit.setFocus() # Focus sul widget corretto
                return
            
            if self.comune_id is None: 
                QMessageBox.warning(self, "Contesto Mancante", 
                                    "Comune di riferimento non specificato per creare un nuovo possessore.\n"
                                    "Questo dialogo dovrebbe essere aperto con un comune_id valido per la creazione.")
                return

            try:
                # Chiamata corretta a create_possessore
                new_possessore_id = self.db_manager.create_possessore(
                    nome_completo=nome_completo,
                    paternita=paternita if paternita else None,
                    comune_riferimento_id=self.comune_id, 
                    attivo=True, # Default per un nuovo possessore
                    cognome_nome=cognome_nome # Passa il cognome_nome
                )
            
                if new_possessore_id is not None:
                    self.selected_possessore = {
                        'id': new_possessore_id,
                        'nome_completo': nome_completo,
                        'cognome_nome': cognome_nome, # Aggiunto per coerenza
                        'paternita': paternita,       # Aggiunto per coerenza
                        'comune_riferimento_id': self.comune_id, # Importante
                        'attivo': True
                        # quota non fa parte dei dati del possessore, ma del legame partita-possessore
                    }
                    QMessageBox.information(self, "Successo", f"Nuovo possessore '{nome_completo}' creato con ID: {new_possessore_id}.")
                    self.accept() 
            except (DBUniqueConstraintError, DBDataError, DBMError) as e:
                QMessageBox.critical(self, "Errore Creazione Possessore", str(e))
            except Exception as e_gen:
                gui_logger.critical(f"Errore imprevisto creazione possessore: {e_gen}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {type(e_gen).__name__}: {e_gen}")
        else: 
             QMessageBox.warning(self, "Azione Non Valida", "Azione non riconosciuta per il tab corrente.")
class ImmobileDialog(QDialog):
    def __init__(self, db_manager, comune_id, parent=None):
        super(ImmobileDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.immobile_data = None
        
        self.setWindowTitle("Inserisci Immobile")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        form_layout = QGridLayout()
        
        # Natura
        natura_label = QLabel("Natura:")
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Es. Casa, Terreno, Garage, ecc.")
        
        form_layout.addWidget(natura_label, 0, 0)
        form_layout.addWidget(self.natura_edit, 0, 1)
        
        # Località
        localita_label = QLabel("Località:")
        self.localita_button = QPushButton("Seleziona Località...")
        self.localita_button.clicked.connect(self.select_localita)
        self.localita_id = None
        self.localita_display = QLabel("Nessuna località selezionata")
        
        form_layout.addWidget(localita_label, 1, 0)
        form_layout.addWidget(self.localita_button, 1, 1)
        form_layout.addWidget(self.localita_display, 1, 2)
        
        # Classificazione
        classificazione_label = QLabel("Classificazione:")
        self.classificazione_edit = QLineEdit()
        self.classificazione_edit.setPlaceholderText("Es. Abitazione civile, Deposito, ecc.")
        
        form_layout.addWidget(classificazione_label, 2, 0)
        form_layout.addWidget(self.classificazione_edit, 2, 1)
        
        # Consistenza
        consistenza_label = QLabel("Consistenza:")
        self.consistenza_edit = QLineEdit()
        self.consistenza_edit.setPlaceholderText("Es. 120 mq")
        
        form_layout.addWidget(consistenza_label, 3, 0)
        form_layout.addWidget(self.consistenza_edit, 3, 1)
        
        # Numero piani
        piani_label = QLabel("Numero piani:")
        self.piani_edit = QSpinBox()
        self.piani_edit.setMinimum(0)
        self.piani_edit.setMaximum(99)
        self.piani_edit.setSpecialValueText("Non specificato")
        
        form_layout.addWidget(piani_label, 4, 0)
        form_layout.addWidget(self.piani_edit, 4, 1)
        
        # Numero vani
        vani_label = QLabel("Numero vani:")
        self.vani_edit = QSpinBox()
        self.vani_edit.setMinimum(0)
        self.vani_edit.setMaximum(99)
        self.vani_edit.setSpecialValueText("Non specificato")
        
        form_layout.addWidget(vani_label, 5, 0)
        form_layout.addWidget(self.vani_edit, 5, 1)
        
        layout.addLayout(form_layout)
        
        # Pulsanti
        buttons_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("Inserisci")
        self.ok_button.clicked.connect(self.handle_insert)
        
        self.cancel_button = QPushButton("Annulla")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
    
    def select_localita(self):
        """Apre un dialogo per selezionare la località."""
        if self.comune_id is None: # Aggiunto controllo per sicurezza
            QMessageBox.warning(self, "Comune Mancante", 
                                "Selezionare un comune per la partita prima di scegliere una località per l'immobile.")
            return

        # Istanzia LocalitaSelectionDialog in MODALITÀ SELEZIONE
        dialog = LocalitaSelectionDialog(self.db_manager, 
                                         self.comune_id, 
                                         self,  # parent
                                         selection_mode=True) # <<<--- MODIFICA CHIAVE QUI
        
        result = dialog.exec_()
        
        if result == QDialog.Accepted: # L'utente ha premuto "Seleziona" in LocalitaSelectionDialog
            if dialog.selected_localita_id is not None and dialog.selected_localita_name is not None:
                self.localita_id = dialog.selected_localita_id
                self.localita_display.setText(dialog.selected_localita_name)
                gui_logger.info(f"ImmobileDialog: Località selezionata ID: {self.localita_id}, Nome: '{self.localita_display.text()}'")
            else:
                # Questo caso dovrebbe essere raro se _conferma_selezione in LocalitaSelectionDialog funziona correttamente
                gui_logger.warning("ImmobileDialog: LocalitaSelectionDialog accettato ma ID/nome località non validi.")
        # else: L'utente ha premuto "Annulla" o chiuso il dialogo LocalitaSelectionDialog,
        # quindi non aggiorniamo nulla e la selezione precedente (o nessuna selezione) rimane.

    
    def handle_insert(self):
        """Gestisce l'inserimento dell'immobile."""
        # Validazione input
        natura = self.natura_edit.text().strip()
        if not natura:
            QMessageBox.warning(self, "Errore", "La natura dell'immobile è obbligatoria.")
            return
        
        if not self.localita_id:
            QMessageBox.warning(self, "Errore", "Seleziona una località.")
            return
        
        # Raccoglie i dati
        classificazione = self.classificazione_edit.text().strip() or None
        consistenza = self.consistenza_edit.text().strip() or None
        numero_piani = self.piani_edit.value() if self.piani_edit.value() > 0 else None
        numero_vani = self.vani_edit.value() if self.vani_edit.value() > 0 else None
        
        # Crea il dizionario dei dati dell'immobile
        self.immobile_data = {
            'natura': natura,
            'localita_id': self.localita_id,
            'localita_nome': self.localita_display.text(),
            'classificazione': classificazione,
            'consistenza': consistenza,
            'numero_piani': numero_piani,
            'numero_vani': numero_vani
        }
        
        self.accept()
        
class LocalitaSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, comune_id: int, parent=None, 
                 selection_mode: bool = False): # NUOVO parametro selection_mode
        super(LocalitaSelectionDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.comune_id = comune_id
        self.selection_mode = selection_mode  # Memorizza la modalità operativa
        
        self.selected_localita_id: Optional[int] = None
        self.selected_localita_name: Optional[str] = None
        
        if self.selection_mode:
            self.setWindowTitle(f"Seleziona Località per Comune ID: {self.comune_id}")
        else:
            self.setWindowTitle(f"Gestione Località per Comune ID: {self.comune_id}")
            
        self.setMinimumSize(650, 450)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        # --- Tab 1: Seleziona/Visualizza/Modifica Esistente ---
        select_tab = QWidget()
        select_layout = QVBoxLayout(select_tab)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtra per nome:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Digita per filtrare...")
        # Connetti textChanged a una lambda che chiama load_localita e aggiorna i pulsanti
        self.filter_edit.textChanged.connect(
            lambda: (self.load_localita(), self._aggiorna_stato_pulsanti_azione_localita())
        )
        filter_layout.addWidget(self.filter_edit)
        select_layout.addLayout(filter_layout)
        
        self.localita_table = QTableWidget()
        self.localita_table.setColumnCount(4)
        self.localita_table.setHorizontalHeaderLabels(["ID", "Nome", "Tipo", "Civico"])
        self.localita_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.localita_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.localita_table.setSelectionMode(QTableWidget.SingleSelection)
        self.localita_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_azione_localita)
        self.localita_table.itemDoubleClicked.connect(self._handle_double_click) # Gestirà doppio click
        select_layout.addWidget(self.localita_table)

        select_action_layout = QHBoxLayout()
        self.btn_modifica_localita = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Modifica Selezionata")
        self.btn_modifica_localita.setToolTip("Modifica i dati della località selezionata")
        self.btn_modifica_localita.clicked.connect(self.apri_modifica_localita_selezionata)
        if self.selection_mode: # In modalità selezione, nascondi il pulsante "Modifica"
            self.btn_modifica_localita.setVisible(False)
        select_action_layout.addWidget(self.btn_modifica_localita)
        select_action_layout.addStretch()
        select_layout.addLayout(select_action_layout)
        self.tabs.addTab(select_tab, "Visualizza Località") # Cambiato nome tab per chiarezza

        # --- Tab 2: Crea Nuova Località ---
        # Questo tab viene mostrato solo se non siamo in modalità selezione
        if not self.selection_mode:
            create_tab = QWidget()
            create_form_layout = QFormLayout(create_tab)
            self.nome_edit_nuova = QLineEdit()
            self.tipo_combo_nuova = QComboBox()
            self.tipo_combo_nuova.addItems(["regione", "via", "borgata"])
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

        # --- Pulsanti in fondo al dialogo ---
        buttons_layout = QHBoxLayout()
        
        # Pulsante SELEZIONA (solo in modalità selezione)
        self.select_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton),"Seleziona")
        self.select_button.setToolTip("Conferma la località selezionata dalla tabella")
        self.select_button.clicked.connect(self._conferma_selezione)
        if not self.selection_mode: # Nascondi se non in modalità selezione
            self.select_button.setVisible(False)
        buttons_layout.addWidget(self.select_button)
        
        buttons_layout.addStretch()
        
        # Pulsante ANNULLA/CHIUDI
        cancel_text = "Annulla" if self.selection_mode else "Chiudi"
        self.chiudi_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCloseButton), cancel_text)
        self.chiudi_button.clicked.connect(self.reject) # self.reject chiude il dialogo senza segnalare accettazione
        buttons_layout.addWidget(self.chiudi_button)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        
        self.load_localita() # Carica i dati e aggiorna lo stato dei pulsanti

    def _handle_double_click(self, item: QTableWidgetItem):
        """Gestisce il doppio click sulla tabella."""
        if self.selection_mode and self.tabs.currentIndex() == 0:
            # Se in modalità selezione e nel tab di visualizzazione, il doppio click seleziona
            self._conferma_selezione()
        elif not self.selection_mode and self.tabs.currentIndex() == 0:
            # Se non in modalità selezione, il doppio click apre la modifica
            self.apri_modifica_localita_selezionata()

    def _conferma_selezione(self):
        """Conferma la selezione della località e chiude il dialogo con Accept."""
        if not self.selection_mode: # Questa azione è solo per la modalità selezione
            return

        if self.tabs.currentIndex() == 0: # Assicurati che siamo nel tab di visualizzazione/selezione
            selected_items = self.localita_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una località dalla tabella.")
                return
            
            current_row = self.localita_table.currentRow()
            if current_row < 0: return

            try:
                self.selected_localita_id = int(self.localita_table.item(current_row, 0).text())
                nome = self.localita_table.item(current_row, 1).text()
                tipo = self.localita_table.item(current_row, 2).text()
                civico_item_text = self.localita_table.item(current_row, 3).text()
                
                self.selected_localita_name = nome
                if civico_item_text and civico_item_text != "-":
                    self.selected_localita_name += f", {civico_item_text}"
                self.selected_localita_name += f" ({tipo})"
                
                gui_logger.info(f"LocalitaSelectionDialog: Località selezionata ID: {self.selected_localita_id}, Nome: '{self.selected_localita_name}'")
                self.accept() # Chiude il dialogo e QDialog.Accepted viene restituito a exec_()
            except ValueError:
                QMessageBox.critical(self, "Errore Dati", "ID località non valido nella tabella.")
            except Exception as e:
                gui_logger.error(f"Errore in _conferma_selezione: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore durante la conferma della selezione: {e}")
        # else: se siamo nel tab "Crea Nuova", il pulsante "Seleziona" non dovrebbe essere attivo o visibile

    def _aggiorna_stato_pulsanti_azione_localita(self):
        is_select_tab_active = (self.tabs.currentIndex() == 0)
        has_selection_in_table = bool(self.localita_table.selectedItems())
        
        # Pulsante Modifica (visibile e attivo solo se non in selection_mode)
        self.btn_modifica_localita.setEnabled(
            is_select_tab_active and has_selection_in_table and not self.selection_mode
        )
        
        # Pulsante Seleziona (visibile e attivo solo se in selection_mode)
        self.select_button.setEnabled(
            is_select_tab_active and has_selection_in_table and self.selection_mode
        )

    def load_localita(self, filter_text: Optional[str] = None): # filter_text è già opzionale
        self.localita_table.setRowCount(0)
        self.localita_table.setSortingEnabled(False)
        
        # Usa il testo attuale dal QLineEdit del filtro, non il parametro 'filter_text' se non fornito
        actual_filter_text = self.filter_edit.text().strip() if hasattr(self, 'filter_edit') and self.filter_edit else None

        if self.comune_id:
            try:
                # Passa actual_filter_text al metodo del DBManager
                localita_results = self.db_manager.get_localita_by_comune(self.comune_id, actual_filter_text)
                if localita_results:
                    self.localita_table.setRowCount(len(localita_results))
                    for i, loc in enumerate(localita_results):
                        self.localita_table.setItem(i, 0, QTableWidgetItem(str(loc.get('id', ''))))
                        self.localita_table.setItem(i, 1, QTableWidgetItem(loc.get('nome', '')))
                        self.localita_table.setItem(i, 2, QTableWidgetItem(loc.get('tipo', '')))
                        civico_text = str(loc.get('civico', '')) if loc.get('civico') is not None else "-"
                        self.localita_table.setItem(i, 3, QTableWidgetItem(civico_text))
                    self.localita_table.resizeColumnsToContents()
            except Exception as e:
                gui_logger.error(f"Errore caricamento località per comune {self.comune_id}: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare le località: {e}")
        
        self.localita_table.setSortingEnabled(True)
        self._aggiorna_stato_pulsanti_azione_localita() # Chiamata fondamentale qui

    # Mantenga invariati i metodi _salva_nuova_localita_da_tab, 
    # apri_modifica_localita_selezionata, e _get_selected_localita_id_from_table
    # come erano nella sua ultima versione funzionante per quelle logiche.
    # ... (copia qui i metodi _salva_nuova_localita_da_tab, apri_modifica_localita_selezionata, 
    #  e _get_selected_localita_id_from_table dalla tua versione precedente del codice)
    def _salva_nuova_localita_da_tab(self):
        nome = self.nome_edit_nuova.text().strip()
        tipo = self.tipo_combo_nuova.currentText()
        civico_val = self.civico_spinbox_nuova.value()
        civico = civico_val if self.civico_spinbox_nuova.text() != self.civico_spinbox_nuova.specialValueText() and civico_val != 0 else None
        if not nome:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
            self.nome_edit_nuova.setFocus()
            return
        if not self.comune_id:
            QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato. Impossibile creare località.")
            return
        try:
            localita_id_creata = self.db_manager.insert_localita(self.comune_id, nome, tipo, civico)
            if localita_id_creata is not None:
                QMessageBox.information(self, "Località Creata", f"Località '{nome}' registrata con ID: {localita_id_creata}")
                self.load_localita() 
                self.tabs.setCurrentIndex(0) 
                self.nome_edit_nuova.clear()
                self.tipo_combo_nuova.setCurrentIndex(0) 
                self.civico_spinbox_nuova.setValue(0) 
        except (DBDataError, DBMError) as dbe:
            gui_logger.error(f"Errore inserimento località: {dbe}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Impossibile inserire località:\n{getattr(dbe, 'message', str(dbe))}")
        except Exception as e:
            gui_logger.error(f"Errore imprevisto inserimento località: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {e}")

    def apri_modifica_localita_selezionata(self):
        localita_id_sel = self._get_selected_localita_id_from_table()
        if localita_id_sel is not None:
            dialog = ModificaLocalitaDialog(self.db_manager, localita_id_sel, self.comune_id, self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_localita() 
        else:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una località dalla tabella per modificarla.")
            
    def _get_selected_localita_id_from_table(self) -> Optional[int]:
        selected_items = self.localita_table.selectedItems()
        if not selected_items: return None
        current_row = self.localita_table.currentRow()
        if current_row < 0: return None
        id_item = self.localita_table.item(current_row, 0)
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def _salva_nuova_localita_da_tab(self): # NUOVO METODO per il pulsante nel tab "Crea Nuova"
        nome = self.nome_edit.text().strip() # Assumendo che questi siano i QLineEdit del tab "Crea"
        tipo = self.tipo_combo.currentText()
        civico_val = self.civico_edit.value()
        civico = civico_val if self.civico_edit.text() != self.civico_edit.specialValueText() and civico_val > 0 else None

        if not nome:
            QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
            self.nome_edit.setFocus()
            return
        if not self.comune_id:
            QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato per la creazione della località.")
            return

        try:
            localita_id_creata = self.db_manager.insert_localita(
                self.comune_id, nome, tipo, civico
            )
            if localita_id_creata is not None:
                QMessageBox.information(self, "Località Creata", f"Località '{nome}' registrata con ID: {localita_id_creata}")
                self.load_localita() # Ricarica la lista nel tab "Visualizza/Modifica"
                self.tabs.setCurrentIndex(0) # Torna al primo tab
                # Pulisci i campi del form di creazione
                self.nome_edit.clear()
                self.tipo_combo.setCurrentIndex(0) # o un default
                self.civico_edit.setValue(self.civico_edit.minimum()) # o 0 e special value text
            # else: gestito da eccezioni in insert_localita
        except (DBDataError, DBMError) as dbe:
            gui_logger.error(f"Errore inserimento località: {dbe}", exc_info=True)
            QMessageBox.critical(self, "Errore Database", f"Impossibile inserire località:\n{dbe.message if hasattr(dbe, 'message') else str(dbe)}")
        except Exception as e:
            gui_logger.error(f"Errore imprevisto inserimento località: {e}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {e}")
    
    # Rimuovi il vecchio `handle_selection_or_creation` se non più usato dal pulsante OK generale.
    # def handle_selection_or_creation(self): ... (RIMUOVERE SE OK BUTTON È RIMOSSO)

    # ... (resto dei metodi: load_localita, filter_localita, apri_modifica_localita_selezionata, _get_selected_localita_id_from_table)

    def _tab_changed(self, index):
        """Gestisce il cambio di tab e aggiorna il testo del pulsante OK."""
        if index == 0: # Tab "Seleziona/Modifica Esistente"
            self.ok_button.setText("Seleziona Località")
            self.ok_button.setToolTip("Conferma la località selezionata dalla tabella.")
        else: # Tab "Crea Nuova"
            self.ok_button.setText("Crea e Seleziona")
            self.ok_button.setToolTip("Crea la nuova località e la seleziona.")
        self._aggiorna_stato_pulsanti_azione_localita()


    def _aggiorna_stato_pulsanti_azione_localita(self):
        """Abilita/disabilita il pulsante Modifica Località."""
        # Il pulsante Modifica è visibile solo se il tab "Visualizza e Modifica" è attivo
        is_select_tab_active = (self.tabs.currentIndex() == 0) 
        has_selection_in_table = bool(self.localita_table.selectedItems())
        
        # Abilita il pulsante "Modifica Selezionata" solo se siamo nel tab corretto 
        # E se una riga è selezionata nella tabella
        self.btn_modifica_localita.setEnabled(is_select_tab_active and has_selection_in_table)
        
        # La riga seguente che si riferiva a self.ok_button va rimossa:
        # self.ok_button.setEnabled(True) # Rimuovi questa riga


    def _get_selected_localita_id_from_table(self) -> Optional[int]: # NUOVO METODO HELPER
        selected_items = self.localita_table.selectedItems()
        if not selected_items:
            return None
        current_row = self.localita_table.currentRow()
        if current_row < 0: return None
        id_item = self.localita_table.item(current_row, 0) # Colonna ID
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def apri_modifica_localita_selezionata(self): # NUOVO METODO
        localita_id_sel = self._get_selected_localita_id_from_table()
        if localita_id_sel is not None:
            # Istanziamo e apriamo ModificaLocalitaDialog
            dialog = ModificaLocalitaDialog(self.db_manager, localita_id_sel, self.comune_id, self) # Passa comune_id
            if dialog.exec_() == QDialog.Accepted:
                QMessageBox.information(self, "Modifica Località", "Modifiche alla località salvate con successo.")
                self.load_localita(self.filter_edit.text().strip() or None) # Ricarica con filtro corrente
        else:
            QMessageBox.warning(self, "Nessuna Selezione", "Seleziona una località dalla tabella per modificarla.")

    # Rinomina il vecchio handle_selection a handle_selection_or_creation
    def handle_selection_or_creation(self): # Unico gestore per il pulsante OK
        current_tab_index = self.tabs.currentIndex()
        if current_tab_index == 0: # Tab "Seleziona/Modifica Esistente" -> Azione di Selezione
            selected_rows = self.localita_table.selectedIndexes()
            if not selected_rows:
                QMessageBox.warning(self, "Attenzione", "Seleziona una località dalla tabella.")
                return
            row = selected_rows[0].row()
            self.selected_localita_id = int(self.localita_table.item(row, 0).text())
            nome = self.localita_table.item(row, 1).text()
            tipo = self.localita_table.item(row, 2).text()
            civico = self.localita_table.item(row, 3).text()
            self.selected_localita_name = nome
            if civico != "-": self.selected_localita_name += f", {civico}"
            self.selected_localita_name += f" ({tipo})"
            self.accept() # Conferma la selezione
        
        else:  # Tab "Crea Nuova" -> Azione di Creazione (come prima)
            nome = self.nome_edit.text().strip()
            tipo = self.tipo_combo.currentText()
            civico_val = self.civico_edit.value()
            # Se specialValueText è "Nessun civico" e civico_val è 0, allora è None
            civico = civico_val if self.civico_edit.text() != self.civico_edit.specialValueText() and civico_val > 0 else None

            if not nome:
                QMessageBox.warning(self, "Dati Mancanti", "Il nome della località è obbligatorio.")
                self.nome_edit.setFocus()
                return
            if not self.comune_id:
                QMessageBox.critical(self, "Errore Interno", "ID Comune non specificato.")
                return

            try:
                localita_id_creata = self.db_manager.insert_localita(
                    self.comune_id, nome, tipo, civico
                )
                if localita_id_creata is not None:
                    self.selected_localita_id = localita_id_creata
                    self.selected_localita_name = nome
                    if civico: self.selected_localita_name += f", {civico}"
                    self.selected_localita_name += f" ({tipo})"
                    QMessageBox.information(self, "Località Creata/Trovata", f"Località '{self.selected_localita_name}' registrata con ID: {self.selected_localita_id}")
                    self.load_localita() # Ricarica la lista nel tab "Seleziona"
                    self.tabs.setCurrentIndex(0) # Torna al tab di selezione
                    # Trova e seleziona la località appena creata (opzionale)
                    for r in range(self.localita_table.rowCount()):
                        if self.localita_table.item(r,0) and int(self.localita_table.item(r,0).text()) == self.selected_localita_id:
                            self.localita_table.selectRow(r)
                            break
                    # Non chiamare self.accept() qui se l'utente deve poi selezionare dalla lista
                    # o se il pulsante era "Crea e Seleziona", allora self.accept() è corretto.
                    # Dato il testo "Crea e Seleziona", self.accept() ci sta.
                    self.accept() 
                # else: gestito da eccezioni
            except (DBDataError, DBMError) as dbe:
                gui_logger.error(f"Errore inserimento località: {dbe}", exc_info=True)
                QMessageBox.critical(self, "Errore Database", f"Impossibile inserire località:\n{dbe.message if hasattr(dbe, 'message') else str(dbe)}")
            except Exception as e:
                gui_logger.error(f"Errore imprevisto inserimento località: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {e}")

    # ... (load_localita, filter_localita come prima, assicurati che _aggiorna_stato_pulsanti_azione_localita sia chiamato in load_localita)
    def load_localita(self, filter_text: Optional[str] = None):
        # ... (come l'avevamo implementata, chiamando db_manager.get_localita_by_comune) ...
        self.localita_table.setRowCount(0)
        self.localita_table.setSortingEnabled(False)
        if self.comune_id:
            try:
                localita_results = self.db_manager.get_localita_by_comune(self.comune_id, filter_text)
                if localita_results:
                    self.localita_table.setRowCount(len(localita_results))
                    for i, loc in enumerate(localita_results):
                        self.localita_table.setItem(i, 0, QTableWidgetItem(str(loc.get('id', ''))))
                        self.localita_table.setItem(i, 1, QTableWidgetItem(loc.get('nome', '')))
                        self.localita_table.setItem(i, 2, QTableWidgetItem(loc.get('tipo', '')))
                        civico_text = str(loc.get('civico', '')) if loc.get('civico') is not None else "-"
                        self.localita_table.setItem(i, 3, QTableWidgetItem(civico_text))
                    self.localita_table.resizeColumnsToContents()
            except Exception as e:
                gui_logger.error(f"Errore caricamento località per comune {self.comune_id}: {e}", exc_info=True)
                QMessageBox.critical(self, "Errore Caricamento", f"Impossibile caricare le località: {e}")
        else:
            self.localita_table.setRowCount(1)
            self.localita_table.setItem(0,0,QTableWidgetItem("ID Comune non disponibile per caricare località."))
        
        self.localita_table.setSortingEnabled(True)
        self._aggiorna_stato_pulsanti_azione_localita() # Chiamata qui
class DettagliLegamePossessoreDialog(QDialog):
    def __init__(self, nome_possessore_selezionato: str, partita_tipo: str, 
                 titolo_attuale: Optional[str] = None, # Nuovo
                 quota_attuale: Optional[str] = None,   # Nuovo
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Dettagli Legame per {nome_possessore_selezionato}")
        self.setMinimumWidth(400)

        self.titolo: Optional[str] = None
        self.quota: Optional[str] = None
        # self.tipo_partita_rel: str = partita_tipo

        layout = QFormLayout(self)

        self.titolo_edit = QLineEdit()
        self.titolo_edit.setPlaceholderText("Es. proprietà esclusiva, usufrutto")
        self.titolo_edit.setText(titolo_attuale if titolo_attuale is not None else "proprietà esclusiva") # Pre-compila
        layout.addRow("Titolo di Possesso (*):", self.titolo_edit)

        self.quota_edit = QLineEdit()
        self.quota_edit.setPlaceholderText("Es. 1/1, 1/2 (lasciare vuoto se non applicabile)")
        self.quota_edit.setText(quota_attuale if quota_attuale is not None else "") # Pre-compila
        layout.addRow("Quota (opzionale):", self.quota_edit)

        # ... (pulsanti OK/Annulla e metodo _accept_details come prima) ...
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogOkButton), "OK")
        self.ok_button.clicked.connect(self._accept_details)
        self.cancel_button = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogCancelButton), "Annulla")
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addRow(buttons_layout)
        self.setLayout(layout)
        self.titolo_edit.setFocus()

    def _accept_details(self):
        # ... (come prima) ...
        titolo_val = self.titolo_edit.text().strip()
        if not titolo_val:
            QMessageBox.warning(self, "Dato Mancante", "Il titolo di possesso è obbligatorio.")
            self.titolo_edit.setFocus()
            return
        self.titolo = titolo_val
        self.quota = self.quota_edit.text().strip() or None
        self.accept()


    # Metodo statico per l'inserimento (come prima)
    @staticmethod
    def get_details_for_new_legame(nome_possessore: str, tipo_partita_attuale: str, parent=None) -> Optional[Dict[str, Any]]:
        # Chiamiamo il costruttore senza titolo_attuale e quota_attuale,
        # così userà i default (None) e quindi il testo placeholder o il default "proprietà esclusiva"
        dialog = DettagliLegamePossessoreDialog(
            nome_possessore_selezionato=nome_possessore,
            partita_tipo=tipo_partita_attuale,
            # titolo_attuale e quota_attuale non vengono passati,
            # quindi __init__ userà i loro valori di default (None)
            parent=parent
        )
        if dialog.exec_() == QDialog.Accepted:
            return {
                "titolo": dialog.titolo,
                "quota": dialog.quota,
                # "tipo_partita_rel": dialog.tipo_partita_rel # Se lo gestisci
            }
        return None

    # NUOVO Metodo statico per la modifica
    @staticmethod
    def get_details_for_edit_legame(nome_possessore: str, tipo_partita_attuale: str, 
                                    titolo_init: str, quota_init: Optional[str], 
                                    parent=None) -> Optional[Dict[str, Any]]:
        dialog = DettagliLegamePossessoreDialog(nome_possessore, tipo_partita_attuale, 
                                                titolo_attuale=titolo_init, 
                                                quota_attuale=quota_init, 
                                                parent=parent)
        dialog.setWindowTitle(f"Modifica Legame per {nome_possessore}") # Titolo specifico per modifica
        if dialog.exec_() == QDialog.Accepted:
            return {
                "titolo": dialog.titolo,
                "quota": dialog.quota,
            }
        return None
class UserSelectionDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, parent=None, title="Seleziona Utente", exclude_user_id: Optional[int] = None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.selected_user_id: Optional[int] = None
        self.exclude_user_id = exclude_user_id

        layout = QVBoxLayout(self)
        
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Nome Completo", "Ruolo", "Stato"])
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.setSelectionMode(QTableWidget.SingleSelection)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.itemDoubleClicked.connect(self._accept_selection)
        layout.addWidget(self.user_table)

        buttons_layout = QHBoxLayout()
        ok_button = QPushButton("Seleziona")
        ok_button.clicked.connect(self._accept_selection)
        cancel_button = QPushButton("Annulla")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(ok_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        self.load_users()

    def load_users(self):
        self.user_table.setRowCount(0)
        users = self.db_manager.get_utenti()
        for user_data in users:
            if self.exclude_user_id and user_data['id'] == self.exclude_user_id:
                continue
            row_pos = self.user_table.rowCount()
            self.user_table.insertRow(row_pos)
            self.user_table.setItem(row_pos, 0, QTableWidgetItem(str(user_data['id'])))
            self.user_table.setItem(row_pos, 1, QTableWidgetItem(user_data['username']))
            self.user_table.setItem(row_pos, 2, QTableWidgetItem(user_data['nome_completo']))
            self.user_table.setItem(row_pos, 3, QTableWidgetItem(user_data['ruolo']))
            self.user_table.setItem(row_pos, 4, QTableWidgetItem("Attivo" if user_data['attivo'] else "Non Attivo"))
        self.user_table.resizeColumnsToContents()


    def _accept_selection(self):
        selected_rows = self.user_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            self.selected_user_id = int(self.user_table.item(row, 0).text())
            self.accept()
        else:
            QMessageBox.warning(self, "Selezione", "Per favore, seleziona un utente dalla lista.")
    