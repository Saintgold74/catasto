import logging
import bcrypt
import csv
import json
import os
from datetime import date, datetime
from typing import Optional, List, Dict, Any

# Importazioni PyQt5
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QComboBox,  QTabWidget, QMessageBox,
                             QGroupBox, QGridLayout, QTableWidget,
                             QTableWidgetItem, QDialog, QListWidget,
                             QListWidgetItem, QFileDialog, QStyle, QSpinBox,
                             QHeaderView, QFormLayout,)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QDialogButtonBox, QAbstractItemView, QTextEdit
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, QFrame, QHBoxLayout, QPushButton, QApplication, QStyle, QMessageBox
from PyQt5.QtCore import Qt, QSettings, pyqtSlot
from catasto_db_manager import CatastoDBManager, DBUniqueConstraintError, DBMError # Assumendo che sia nello stesso pacchetto o usa il path corretto
from dialogs import LocalitaSelectionDialog,CSVApreviewDialog,PDFApreviewDialog
# In app_utils.py, dopo le importazioni PyQt e standard:
# Nessuna dipendenza ciclica dagli altri due moduli GUI (gui_main, gui_widgets) dovrebbe essere necessaria qui.
# Questo modulo fornisce utility AGLI ALTRI.
# Se necessario, importa CatastoDBManager per type hinting o usi diretti limitati:
from config import (
    SETTINGS_DB_TYPE, SETTINGS_DB_HOST, SETTINGS_DB_PORT, 
    SETTINGS_DB_NAME, SETTINGS_DB_USER, SETTINGS_DB_SCHEMA,
    COLONNE_POSSESSORI_DETTAGLI_NUM ,COLONNE_POSSESSORI_DETTAGLI_LABELS,COLONNE_VISUALIZZAZIONE_POSSESSORI_NUM,
    COLONNE_VISUALIZZAZIONE_POSSESSORI_LABELS, COLONNE_INSERIMENTO_POSSESSORI_NUM, COLONNE_INSERIMENTO_POSSESSORI_LABELS,
    NUOVE_ETICHETTE_POSSESSORI)
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

    class PDFPartita:
        pass

    class PDFPossessore:
        pass

    class GenericTextReportPDF:
        pass

# Gestione Eccezioni DB (potrebbero essere importate da catasto_db_manager se si preferisce)
# Se rimangono qui, assicurarsi che non ci siano conflitti se catasto_db_manager le definisce pure.
# Idealmente, dovrebbero essere definite UNA SOLA VOLTA in catasto_db_manager e importate qui.
# Per ora, manteniamo il fallback come nel suo codice originale.
try:
    from catasto_db_manager import DBMError, DBUniqueConstraintError, DBNotFoundError, DBDataError
except ImportError:
    class DBMError(Exception):
        pass

    class DBUniqueConstraintError(DBMError):
        pass

    class DBNotFoundError(DBMError):
        pass

    class DBDataError(DBMError):
        pass
    # QMessageBox.warning(None, "Avviso Importazione", "Eccezioni DB personalizzate non trovate in app_utils.")
        
def format_full_name(first_name, last_name):
    """Formatta nome e cognome in 'Cognome Nome', gestendo input non validi."""
    if not isinstance(first_name, str) or not isinstance(last_name, str):
        raise TypeError("First name and last name must be strings.")
    
    if not first_name and not last_name:
        return ""
    
    # Rimuove spazi e mette in maiuscolo la prima lettera di ogni parola
    last_name_formatted = last_name.strip().title()
    first_name_formatted = first_name.strip().title()

    # Unisce i nomi, gestendo il caso in cui uno dei due sia vuoto
    full_name = f"{last_name_formatted} {first_name_formatted}".strip()
    
    return full_name


# --- Classi PDF (da python_example.py) ---
if FPDF_AVAILABLE:
    class PDFPartita(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, 'Dettaglio Partita Catastale', 0,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'B', 8)  # Cambiato in Bold per coerenza
            self.cell(0, 10, f'Pagina {self.page_no()}', border=0,
                      align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

        def chapter_title(self, title):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 6, title, 0, new_x=XPos.LMARGIN,
                      new_y=YPos.NEXT, align='L')
            self.ln(2)

        def chapter_body(self, data_dict):
            self.set_font('Helvetica', '', 10)
            page_width = self.w - self.l_margin - self.r_margin
            for key, value in data_dict.items():
                text_to_write = f"{key.replace('_', ' ').title()}: {value if value is not None else 'N/D'}"
                try:
                    self.multi_cell(page_width, 5, text_to_write,
                                    border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                except Exception as e:  # FPDFException non è definita se FPDF non è importato
                    if "Not enough horizontal space" in str(e):
                        logging.getLogger("CatastoGUI").warning(
                            f"FPDFException: {e} per il testo: {text_to_write[:100]}...")
                        self.multi_cell(
                            page_width, 5, f"{key.replace('_', ' ').title()}: [ERRORE DATI TROPPO LUNGHI]", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    else:
                        raise e
            self.ln(2)  # Aggiungo un po' di spazio

        def simple_table(self, headers, data_rows, col_widths_percent=None):
            self.set_font('Helvetica', 'B', 9)  # Header in grassetto
            effective_page_width = self.w - self.l_margin - self.r_margin

            if col_widths_percent:
                col_widths = [effective_page_width *
                              (p/100) for p in col_widths_percent]
            else:
                num_cols = len(headers)
                default_col_width = effective_page_width / \
                    num_cols if num_cols > 0 else effective_page_width
                col_widths = [default_col_width] * num_cols

            for i, header in enumerate(headers):
                align = 'C'  # Centra gli header
                if i == len(headers) - 1:  # Ultima cella della riga header
                    self.cell(col_widths[i], 7, header, border=1,
                              new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                else:
                    self.cell(col_widths[i], 7, header, border=1,
                              new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)

            self.set_font('Helvetica', '', 8)
            for row in data_rows:
                for i, item in enumerate(row):
                    text = str(item) if item is not None else ''
                    align = 'L'  # Dati allineati a sinistra
                    if i == len(row) - 1:  # Ultima cella della riga dati
                        self.cell(
                            col_widths[i], 6, text, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                    else:
                        self.cell(
                            col_widths[i], 6, text, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)
            self.ln(4)

    class PDFPossessore(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, 'Dettaglio Possessore Catastale', border=0,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)  # Originale era 'I'
            self.cell(0, 10, f'Pagina {self.page_no()}', border=0,
                      align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

        def chapter_title(self, title):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 6, title, border=0, new_x=XPos.LMARGIN,
                      new_y=YPos.NEXT, align='L')
            self.ln(2)

        def chapter_body(self, data_dict):
            self.set_font('Helvetica', '', 10)
            page_width = self.w - self.l_margin - self.r_margin
            for key, value in data_dict.items():
                text_to_write = f"{key.replace('_', ' ').title()}: {value if value is not None else 'N/D'}"
                try:
                    self.multi_cell(page_width, 5, text_to_write, border=0,
                                    new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                except Exception as e:  # FPDFException
                    if "Not enough horizontal space" in str(e):
                        logging.getLogger("CatastoGUI").warning(
                            f"FPDFException (chapter_body possessore): {e} per testo: {text_to_write[:100]}...")
                        self.multi_cell(
                            page_width, 5, f"{key.replace('_', ' ').title()}: [DATI TROPPO LUNGHI]", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
                    else:
                        raise e
            self.ln(2)

        def simple_table(self, headers, data_rows, col_widths_percent=None):
            self.set_font('Helvetica', 'B', 9)
            effective_page_width = self.w - self.l_margin - self.r_margin

            if col_widths_percent:
                col_widths = [effective_page_width *
                              (p/100) for p in col_widths_percent]
            else:
                num_cols = len(headers)
                default_col_width = effective_page_width / \
                    num_cols if num_cols > 0 else effective_page_width
                col_widths = [default_col_width] * num_cols

            for i, header in enumerate(headers):
                align = 'C'
                if i == len(headers) - 1:
                    self.cell(col_widths[i], 7, header, border=1,
                              new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                else:
                    self.cell(col_widths[i], 7, header, border=1,
                              new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)

            self.set_font('Helvetica', '', 8)
            for row in data_rows:
                for i, item in enumerate(row):
                    text = str(item) if item is not None else ''
                    align = 'L'
                    if i == len(row) - 1:
                        self.cell(
                            col_widths[i], 6, text, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=align)
                    else:
                        self.cell(
                            col_widths[i], 6, text, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align=align)
            self.ln(4)
else:  # FPDF non disponibile
    class PDFPartita:
        pass  # Definizioni vuote per evitare errori di NameError

    class PDFPossessore:
        pass
if FPDF_AVAILABLE:
    class GenericTextReportPDF(FPDF):
        def __init__(self, orientation='P', unit='mm', format='A4', report_title="Report"):
            super().__init__(orientation, unit, format)
            self.report_title = report_title
            self.set_auto_page_break(auto=True, margin=15)
            self.set_left_margin(15)
            self.set_right_margin(15)
            # Font di default per il corpo del report
            self.set_font('Helvetica', '', 10)

        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, self.report_title, 0,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            self.ln(5)  # Spazio dopo l'header

        def footer(self):
            self.set_y(-15)  # Posizione a 1.5 cm dal fondo
            self.set_font('Helvetica', 'I', 8)
            # {{nb}} è un alias per il numero totale di pagine
            page_num_text = f'Pagina {self.page_no()} / {{nb}}'
            self.cell(0, 10, page_num_text, border=0, align='C',
                      new_x=XPos.RIGHT, new_y=YPos.TOP)

        def add_report_text(self, text_content: str):
            """Aggiunge il contenuto testuale del report al PDF."""
            self.set_font(
                'Courier', '', 9)  # Usiamo un font monospazio per testo preformattato
            # Potrebbe scegliere 'Helvetica' se preferisce
            # Sostituisci i caratteri di tabulazione con spazi per un rendering migliore in PDF
            text_content = text_content.replace('\t', '    ')

            # multi_cell gestisce automaticamente i ritorni a capo e il wrapping del testo
            # Larghezza 0 = larghezza piena, altezza riga 5mm
            self.multi_cell(0, 5, text_content)
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
            raise TypeError(
                f"Object of type {type(obj).__name__} is not JSON serializable")

        try:
            json_data_str = json.dumps(
                dict_data, indent=4, ensure_ascii=False, default=json_serial)
        except TypeError as te:
            logging.getLogger("CatastoGUI").error(
                f"Errore di serializzazione JSON per partita ID {partita_id}: {te} - Dati: {dict_data}")
            QMessageBox.critical(parent_widget, "Errore di Serializzazione",
                                 f"Errore durante la conversione dei dati della partita in JSON: {te}\n"
                                 "Controllare i log per i dettagli.")
            return
        # --- FINE MODIFICA ---

        # --- MODIFICA QUI ---
        # 1. Crea solo il nome base del file
        default_filename_base = f"partita_{partita_id}_{date.today().isoformat()}.json"
        
        # 2. Usa la nuova funzione per ottenere il percorso completo di default
        full_default_path = _get_default_export_path(default_filename_base)

        # 3. Passa il percorso completo a QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            parent_widget, "Salva JSON Partita", full_default_path, "JSON Files (*.json)")
        # --- FINE MODIFICA ---

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_data_str)
                QMessageBox.information(
                    parent_widget, "Esportazione JSON", f"Partita esportata con successo in:\n{filename}")
            except Exception as e:
                logging.getLogger("CatastoGUI").error(
                    f"Errore durante il salvataggio del file JSON per partita ID {partita_id}: {e}")
                QMessageBox.critical(parent_widget, "Errore Esportazione",
                                     f"Errore durante il salvataggio del file JSON:\n{e}")
    else:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            f"Partita con ID {partita_id} non trovata o errore nel recupero dei dati per l'esportazione.")


def gui_esporta_partita_csv(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            "Dati partita non validi per l'esportazione CSV.")
        return
    # --- LOGICA ANTEPRIMA CSV ---
    preview_headers = ["Sezione", "Campo", "Valore"]
    preview_data_rows = []
    MAX_ROWS_PREVIEW_SECTION = 3 # Mostra solo le prime N righe per sezione nella preview

    # Dettagli Partita
    p_details = partita_data.get('partita', {})
    for k, v in p_details.items():
        preview_data_rows.append(["Partita", k.replace('_', ' ').title(), v])

    # Possessori (prime N)
    if partita_data.get('possessori'):
        preview_data_rows.append(["---", "--- Possessori ---", "---"])
        poss_headers = list(partita_data['possessori'][0].keys()) if partita_data['possessori'] else []
        preview_data_rows.append(["Possessori", "Intestazioni", ", ".join([h.replace('_', ' ').title() for h in poss_headers])])
        for i, pos in enumerate(partita_data['possessori']):
            if i >= MAX_ROWS_PREVIEW_SECTION:
                preview_data_rows.append(["Possessori", f"...e altri {len(partita_data['possessori']) - MAX_ROWS_PREVIEW_SECTION}...", ""])
                break
            preview_data_rows.append(["Possessori", f"Possessore {i+1}", ", ".join([str(pos.get(h, '')) for h in poss_headers])])
    
    # Aggiungere logica simile per Immobili e Variazioni...

    preview_dialog = CSVApreviewDialog(preview_headers, preview_data_rows, parent_widget,
                                       title=f"Anteprima CSV - Partita ID {partita_id}")
    if preview_dialog.exec_() != QDialog.Accepted:
        logging.getLogger("CatastoGUI").info(f"Esportazione CSV per partita ID {partita_id} annullata dall'utente dopo anteprima.")
        return
    # --- FINE LOGICA ANTEPRIMA CSV ---
    
    default_filename = f"partita_{partita_id}_{date.today()}.csv"
    # 2. Usa la nuova funzione per ottenere il percorso completo di default
    full_default_path = _get_default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva CSV Partita", full_default_path, "CSV Files (*.csv)")
    if not filename:
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            p = partita_data['partita']
            writer.writerow(['--- DETTAGLI PARTITA ---'])
            for key, value in p.items():
                writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])

            if partita_data.get('possessori'):
                writer.writerow(['--- POSSESSORI ---'])
                headers = list(partita_data['possessori'][0].keys(
                )) if partita_data['possessori'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title()
                                    for h in headers])
                for pos in partita_data['possessori']:
                    writer.writerow([pos.get(h) for h in headers])
                writer.writerow([])

            if partita_data.get('immobili'):
                writer.writerow(['--- IMMOBILI ---'])
                headers = list(partita_data['immobili'][0].keys(
                )) if partita_data['immobili'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title()
                                    for h in headers])
                for imm in partita_data['immobili']:
                    writer.writerow([imm.get(h) for h in headers])
                writer.writerow([])

            if partita_data.get('variazioni'):
                writer.writerow(['--- VARIAZIONI ---'])
                headers = list(partita_data['variazioni'][0].keys(
                )) if partita_data['variazioni'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title()
                                    for h in headers])
                for var in partita_data['variazioni']:
                    writer.writerow([var.get(h) for h in headers])
        QMessageBox.information(parent_widget, "Esportazione CSV",
                                f"Partita esportata con successo in:\n{filename}")
    except Exception as e:
        QMessageBox.critical(parent_widget, "Errore Esportazione",
                             f"Errore durante l'esportazione CSV:\n{e}")


def gui_esporta_partita_pdf(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    if not FPDF_AVAILABLE:
        QMessageBox.warning(parent_widget, "Funzionalità non disponibile",
                            "La libreria FPDF è necessaria per l'esportazione in PDF, ma non è installata.")
        return

    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            "Dati partita non validi per l'esportazione PDF.")
        return
    # --- LOGICA ANTEPRIMA TESTUALE PDF ---
    # Genera una stringa di anteprima (puoi riutilizzare la logica dei report testuali)
    # o creare una versione semplificata della struttura PDF.
    # Qui, per esempio, potremmo usare il report testuale del report di proprietà.
    # ATTENZIONE: genera_report_proprieta è un metodo di db_manager che restituisce una stringa SQL,
    # non il testo del report. Dobbiamo simulare il contenuto testuale che andrà nel PDF.
    
    preview_text_content = f"ANTEPRIMA PDF - Partita ID: {partita_id}\n"
    preview_text_content += "======================================\n\n"
    p_details = partita_data.get('partita', {})
    preview_text_content += "Dettagli Partita:\n"
    for key, value in p_details.items():
        preview_text_content += f"  {key.replace('_', ' ').title()}: {value if value is not None else 'N/D'}\n"
    preview_text_content += "\n"

    if partita_data.get('possessori'):
        preview_text_content += "Possessori (primi 2):\n"
        for i, pos in enumerate(partita_data['possessori'][:2]):
            preview_text_content += f"  - ID: {pos.get('id')}, Nome: {pos.get('nome_completo')}, Titolo: {pos.get('titolo')}, Quota: {pos.get('quota', 'N/D')}\n"
        if len(partita_data['possessori']) > 2:
            preview_text_content += "  ...e altri.\n"
    preview_text_content += "\n"
    
    # Aggiungere sezioni simili per Immobili e Variazioni (prime N righe)

    preview_dialog = PDFApreviewDialog(preview_text_content, parent_widget,
                                       title=f"Anteprima PDF - Partita ID {partita_id}")
    if preview_dialog.exec_() != QDialog.Accepted:
        logging.getLogger("CatastoGUI").info(f"Esportazione PDF per partita ID {partita_id} annullata dall'utente dopo anteprima.")
        return
    # --- FINE LOGICA ANTEPRIMA TESTUALE PDF ---
    default_filename = f"partita_{partita_id}_{date.today()}.pdf"
    full_default_path = _get_default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva PDF Partita", full_default_path, "PDF Files (*.pdf)")
    if not filename:
        return

    try:
        pdf = PDFPartita()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        pdf.add_page()

        p = partita_data['partita']
        pdf.chapter_title('Dettagli Partita')
        # --- MODIFICA QUI ---
        # Aggiungiamo 'suffisso_partita' all'elenco dei campi da visualizzare
        campi_da_visualizzare = [
            'id', 'comune_nome', 'numero_partita', 'suffisso_partita', 
            'tipo', 'data_impianto', 'stato', 'data_chiusura', 'numero_provenienza'
        ]
        pdf.chapter_body({k: p.get(k) for k in campi_da_visualizzare})
        # --- FINE MODIFICA ---

        if partita_data.get('possessori'):
            pdf.chapter_title('Possessori')
            headers = ['ID', 'Nome Completo', 'Titolo', 'Quota']
            data_rows = [[pos.get('id'), pos.get('nome_completo'), pos.get(
                'titolo'), pos.get('quota')] for pos in partita_data['possessori']]
            pdf.simple_table(headers, data_rows)

        if partita_data.get('immobili'):
            pdf.chapter_title('Immobili')
            headers = ['ID', 'Natura', 'Località', 'Class.', 'Consist.']
            data_rows = [[imm.get('id'), imm.get('natura'), f"{imm.get('localita_nome', '')} {imm.get('civico', '')}".strip(
            ), imm.get('classificazione'), imm.get('consistenza')] for imm in partita_data['immobili']]
            pdf.simple_table(headers, data_rows)

        if partita_data.get('variazioni'):
            pdf.chapter_title('Variazioni')
            headers = ['ID', 'Tipo', 'Data Var.', 'Contratto', 'Notaio']
            data_rows = []
            for var in partita_data['variazioni']:
                contr_str = f"{var.get('contratto_tipo', '')} del {var.get('data_contratto', '')}" if var.get(
                    'contratto_tipo') else ''
                data_rows.append([var.get('id'), var.get('tipo'), var.get(
                    'data_variazione'), contr_str, var.get('notaio')])
            pdf.simple_table(headers, data_rows)

        pdf.output(filename)
        QMessageBox.information(parent_widget, "Esportazione PDF",
                                f"Partita esportata con successo in:\n{filename}")
    except Exception as e:
        logging.getLogger("CatastoGUI").exception(
            "Errore esportazione PDF partita (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione",
                             f"Errore durante l'esportazione PDF:\n{e}")


def gui_esporta_possessore_json(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    dict_data = db_manager.get_possessore_data_for_export(possessore_id)
    if dict_data:
        json_data_str = json.dumps(dict_data, indent=4, ensure_ascii=False)
        default_filename = f"possessore_{possessore_id}_{date.today()}.json"
        filename, _ = QFileDialog.getSaveFileName(
            parent_widget, "Salva JSON Possessore", default_filename, "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(json_data_str)
                QMessageBox.information(
                    parent_widget, "Esportazione JSON", f"Possessore esportato con successo in:\n{filename}")
            except Exception as e:
                QMessageBox.critical(parent_widget, "Errore Esportazione",
                                     f"Errore durante il salvataggio del file JSON:\n{e}")
    else:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            f"Possessore con ID {possessore_id} non trovato o errore recupero dati.")


# In app_utils.py

def gui_esporta_possessore_csv(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            "Dati possessore non validi per l'esportazione CSV.")
        return

    # --- NUOVA SEZIONE: Logica di Anteprima per CSV ---
    preview_headers = ["Sezione", "Campo", "Valore"]
    preview_data_rows = []
    MAX_ROWS_PREVIEW_SECTION = 3 # Mostra solo le prime N righe per sezione nell'anteprima

    # Dettagli Possessore
    p_details = possessore_data.get('possessore', {})
    for k, v in p_details.items():
        preview_data_rows.append(["Possessore", k.replace('_', ' ').title(), v])

    # Partite Associate (prime N)
    if possessore_data.get('partite'):
        preview_data_rows.append(["---", "--- Partite Associate ---", "---"])
        partite_headers = list(possessore_data['partite'][0].keys()) if possessore_data['partite'] else []
        preview_data_rows.append(["Partite", "Intestazioni", ", ".join([h.replace('_', ' ').title() for h in partite_headers])])
        
        for i, partita in enumerate(possessore_data['partite']):
            if i >= MAX_ROWS_PREVIEW_SECTION:
                preview_data_rows.append(["Partite", f"...e altre {len(possessore_data['partite']) - MAX_ROWS_PREVIEW_SECTION}...", ""])
                break
            # Crea una stringa riassuntiva per la riga di anteprima
            row_summary = f"N.{partita.get('numero_partita', '?')} ({partita.get('comune_nome', '?')}), Titolo: {partita.get('titolo', 'N/D')}"
            preview_data_rows.append(["Partite", f"Partita {i+1}", row_summary])
    
    # Aggiungere qui una logica simile per gli immobili, se necessario

    preview_dialog = CSVApreviewDialog(preview_headers, preview_data_rows, parent_widget,
                                       title=f"Anteprima CSV - Possessore ID {possessore_id}")
    if preview_dialog.exec_() != QDialog.Accepted:
        logging.getLogger("CatastoGUI").info(f"Esportazione CSV per possessore ID {possessore_id} annullata dall'utente.")
        return
    # --- FINE Logica di Anteprima ---

    default_filename = f"possessore_{possessore_id}_{date.today()}.csv"
    full_default_path = _get_default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva CSV Possessore", full_default_path, "CSV Files (*.csv)")
    if not filename:
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            p_info = possessore_data['possessore']
            writer.writerow(['--- DETTAGLI POSSESSORE ---'])
            for key, value in p_info.items():
                writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])

            if possessore_data.get('partite'):
                writer.writerow(['--- PARTITE ASSOCIATE ---'])
                headers = list(possessore_data['partite'][0].keys()) if possessore_data['partite'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title() for h in headers])
                for part in possessore_data['partite']:
                    writer.writerow([part.get(h) for h in headers])
                writer.writerow([])

            if possessore_data.get('immobili'):
                writer.writerow(['--- IMMOBILI ASSOCIATI (TRAMITE PARTITE) ---'])
                headers = list(possessore_data['immobili'][0].keys()) if possessore_data['immobili'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title() for h in headers])
                for imm in possessore_data['immobili']:
                    writer.writerow([imm.get(h) for h in headers])

        QMessageBox.information(parent_widget, "Esportazione CSV",
                                f"Possessore esportato con successo in:\n{filename}")
    except Exception as e:
        QMessageBox.critical(parent_widget, "Errore Esportazione",
                             f"Errore durante l'esportazione CSV:\n{e}")


def gui_esporta_possessore_pdf(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    if not FPDF_AVAILABLE:
        QMessageBox.warning(parent_widget, "Funzionalità non disponibile",
                            "La libreria FPDF è necessaria per l'esportazione in PDF, ma non è installata.")
        return

    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati",
                            "Dati possessore non validi per l'esportazione PDF.")
        return

    # --- NUOVA SEZIONE: Logica di Anteprima per PDF ---
    preview_text_content = f"ANTEPRIMA PDF - Possessore ID: {possessore_id}\n"
    preview_text_content += "========================================\n\n"
    
    p_details = possessore_data.get('possessore', {})
    preview_text_content += "Dettagli Possessore:\n"
    for key, value in p_details.items():
        preview_text_content += f"  {key.replace('_', ' ').title()}: {value if value is not None else 'N/D'}\n"
    preview_text_content += "\n"

    if possessore_data.get('partite'):
        preview_text_content += "Partite Associate (prime 3):\n"
        for i, partita in enumerate(possessore_data['partite'][:3]):
            preview_text_content += (f"  - Partita N.{partita.get('numero_partita', '?')} "
                                     f"({partita.get('comune_nome', '?')}) - "
                                     f"Titolo: {partita.get('titolo', 'N/D')}, Quota: {partita.get('quota', 'N/D')}\n")
        if len(possessore_data['partite']) > 3:
            preview_text_content += "  ...e altre.\n"
    preview_text_content += "\n"

    # Aggiungere qui una sezione simile per gli immobili, se si desidera
    
    preview_dialog = PDFApreviewDialog(preview_text_content, parent_widget,
                                       title=f"Anteprima PDF - Possessore ID {possessore_id}")
    if preview_dialog.exec_() != QDialog.Accepted:
        logging.getLogger("CatastoGUI").info(f"Esportazione PDF per possessore ID {possessore_id} annullata dall'utente.")
        return
    # --- FINE Logica di Anteprima ---

    default_filename = f"possessore_{possessore_id}_{date.today()}.pdf"
    full_default_path = _get_default_export_path(default_filename)
    filename, _ = QFileDialog.getSaveFileName(
        parent_widget, "Salva PDF Possessore", full_default_path, "PDF Files (*.pdf)")
    if not filename:
        return

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
            'Comune Riferimento': p_info.get('comune_nome'),
            'Paternità': p_info.get('paternita'),
            'Stato': "Attivo" if p_info.get('attivo') else "Non Attivo",
        }
        pdf.chapter_body(details_poss)

        if possessore_data.get('partite'):
            pdf.chapter_title('Partite Associate')
            # --- MODIFICA QUI ---
            headers = ['ID Part.', 'Num. Partita', 'Suffisso', 'Comune', 'Tipo', 'Quota', 'Titolo']
            col_widths_percent = [8, 12, 10, 20, 10, 15, 25] # Ribilanciamo le larghezze
            data_rows = []
            for part in possessore_data['partite']:
                data_rows.append([
                    part.get('id'), 
                    part.get('numero_partita'), 
                    part.get('suffisso_partita', '') or '', # Aggiunto suffisso
                    part.get('comune_nome'),
                    part.get('tipo'), 
                    part.get('quota'), 
                    part.get('titolo')
                ])
            pdf.simple_table(headers, data_rows, col_widths_percent=col_widths_percent)
            # --- FINE MODIFICA ---

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
        QMessageBox.information(parent_widget, "Esportazione PDF",
                                f"Possessore esportato con successo in:\n{filename}")
    except Exception as e:
        logging.getLogger("CatastoGUI").exception(
            "Errore esportazione PDF possessore (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione",
                             f"Errore durante l'esportazione PDF:\n{e}")
# In app_utils.py, dopo le importazioni

import os # Assicurati che 'os' sia importato

def _get_default_export_path(default_filename: str) -> str:
    """
    Crea la sottocartella 'esportazioni' se non esiste e restituisce
    il percorso completo per il file di default.
    """
    # Definisce il nome della sottocartella
    export_dir_name = "esportazioni"
    
    # Crea il percorso completo della cartella (relativo alla posizione di esecuzione)
    full_dir_path = os.path.abspath(export_dir_name)
    
    # Crea la directory se non esiste, senza generare errori se esiste già
    os.makedirs(full_dir_path, exist_ok=True)
    
    # Unisce il percorso della cartella con il nome del file suggerito
    return os.path.join(full_dir_path, default_filename)
if FPDF_AVAILABLE:
    class BulkReportPDF(FPDF):
        """
        Classe PDF specializzata per creare report tabellari lunghi
        con intestazioni ripetute su ogni pagina.
        """
        def __init__(self, orientation='L', unit='mm', format='A4', report_title="Report Dati"):
            super().__init__(orientation, unit, format) # 'L' per Landscape, più adatto a tabelle
            self.report_title = report_title
            self.headers = []
            self.col_widths = []

        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, self.report_title, 0, 1, 'C')
            self.ln(5)
            # Stampa l'intestazione della tabella su ogni pagina
            if self.headers:
                self.set_font('Helvetica', 'B', 8)
                self.set_fill_color(230, 230, 230)
                for i, header in enumerate(self.headers):
                    self.cell(self.col_widths[i], 7, header, 1, 0, 'C', 1)
                self.ln()

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}}', 0, 0, 'C')

        def print_table(self, headers, data):
            if not data: return
            
            self.headers = headers
            # Calcola larghezza colonne (semplice divisione)
            effective_width = self.w - self.l_margin - self.r_margin
            self.col_widths = [effective_width / len(headers)] * len(headers)
            
            self.set_font('Helvetica', '', 8)
            self.add_page()
            
            for row in data:
                # Controlla se c'è spazio per la riga, altrimenti vai a pagina nuova
                if self.get_y() + 6 > self.page_break_trigger:
                    self.add_page()

                for i, header in enumerate(headers):
                    # Usiamo .get(header) se i dati sono dict, o l'indice se sono liste/tuple
                    if isinstance(row, dict):
                        cell_value = str(row.get(header, ''))
                    else:
                        cell_value = str(row[i]) if i < len(row) else ''
                    self.cell(self.col_widths[i], 6, cell_value, 1, 0, 'L')
                self.ln()



# ASSICURATI CHE SIA QUI O PRIMA DI DOVE SERVE
