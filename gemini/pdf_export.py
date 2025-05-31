#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Funzionalità di Esportazione PDF per Gestionale Catasto Storico
==============================================================
Autore: Marco Santoro
Data: 31/05/2025
Versione: 1.0
"""

import logging
import json
import csv
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

# Importazioni PyQt5
from PyQt5.QtWidgets import QFileDialog, QMessageBox

# Importa le utilità
from utils import gui_logger, FPDF_AVAILABLE

# Importa riferimento al database manager
try:
    from catasto_db_manager import CatastoDBManager
except ImportError:
    gui_logger.error("Impossibile importare CatastoDBManager. Verificare l'installazione.")
    # Definizione di fallback per permettere l'esecuzione in fase di sviluppo
    class CatastoDBManager:
        pass

# Verifica disponibilità della libreria FPDF per export PDF
if FPDF_AVAILABLE:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
    
    class PDFPartita(FPDF):
        """Classe per generare PDF di partite catastali."""
        def __init__(self):
            super().__init__()
            self.add_page()
            self.set_font('Helvetica', 'B', 16)
            
        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, 'Catasto Storico - Partita', 0, 1, 'C')
            self.ln(5)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')
            self.cell(0, 10, f'Generato il {date.today().strftime("%d/%m/%Y")}', 0, 0, 'R')
            
        def chapter_title(self, title):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, title, 0, 1, 'L')
            self.ln(2)
            
        def chapter_body(self, data_dict):
            self.set_font('Helvetica', '', 10)
            for key, value in data_dict.items():
                if value is not None:
                    # Formatta la chiave e il valore
                    self.set_font('Helvetica', 'B', 10)
                    self.cell(60, 6, f"{key}: ", 0, 0, 'L')
                    self.set_font('Helvetica', '', 10)
                    self.cell(0, 6, f"{value}", 0, 1, 'L')
            self.ln(5)
            
        def simple_table(self, headers, data_rows, col_widths_percent=None):
            # Calcola larghezze colonne in base a percentuali o automaticamente
            if col_widths_percent:
                page_width = self.w - 2*self.l_margin
                col_widths = [page_width * p / 100 for p in col_widths_percent]
            else:
                col_count = len(headers)
                col_widths = [(self.w - 2*self.l_margin) / col_count] * col_count
            
            # Intestazioni
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)  # Grigio chiaro
            for i, header in enumerate(headers):
                self.cell(col_widths[i], 7, header, 1, 0, 'C', True)
            self.ln()
            
            # Dati
            self.set_font('Helvetica', '', 10)
            fill = False
            for row in data_rows:
                for i, cell in enumerate(row):
                    cell_text = str(cell) if cell is not None else ""
                    self.cell(col_widths[i], 6, cell_text, 1, 0, 'L', fill)
                self.ln()
                fill = not fill  # Alterna colori righe
            self.ln(5)

    class PDFPossessore(FPDF):
        """Classe per generare PDF di possessori."""
        def __init__(self):
            super().__init__()
            self.add_page()
            self.set_font('Helvetica', 'B', 16)
            
        def header(self):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, 'Catasto Storico - Possessore', 0, 1, 'C')
            self.ln(5)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')
            self.cell(0, 10, f'Generato il {date.today().strftime("%d/%m/%Y")}', 0, 0, 'R')
            
        def chapter_title(self, title):
            self.set_font('Helvetica', 'B', 12)
            self.cell(0, 10, title, 0, 1, 'L')
            self.ln(2)
            
        def chapter_body(self, data_dict):
            self.set_font('Helvetica', '', 10)
            for key, value in data_dict.items():
                if value is not None:
                    # Formatta la chiave e il valore
                    self.set_font('Helvetica', 'B', 10)
                    self.cell(60, 6, f"{key}: ", 0, 0, 'L')
                    self.set_font('Helvetica', '', 10)
                    self.cell(0, 6, f"{value}", 0, 1, 'L')
            self.ln(5)
            
        def simple_table(self, headers, data_rows, col_widths_percent=None):
            # Calcola larghezze colonne in base a percentuali o automaticamente
            if col_widths_percent:
                page_width = self.w - 2*self.l_margin
                col_widths = [page_width * p / 100 for p in col_widths_percent]
            else:
                col_count = len(headers)
                col_widths = [(self.w - 2*self.l_margin) / col_count] * col_count
            
            # Intestazioni
            self.set_font('Helvetica', 'B', 10)
            self.set_fill_color(240, 240, 240)  # Grigio chiaro
            for i, header in enumerate(headers):
                self.cell(col_widths[i], 7, header, 1, 0, 'C', True)
            self.ln()
            
            # Dati
            self.set_font('Helvetica', '', 10)
            fill = False
            for row in data_rows:
                for i, cell in enumerate(row):
                    cell_text = str(cell) if cell is not None else ""
                    self.cell(col_widths[i], 6, cell_text, 1, 0, 'L', fill)
                self.ln()
                fill = not fill  # Alterna colori righe
            self.ln(5)

    class GenericTextReportPDF(FPDF):
        """Classe per generare report testuali generici in PDF."""
        def __init__(self, orientation='P', unit='mm', format='A4', report_title="Report"):
            super().__init__(orientation, unit, format)
            self.report_title = report_title
            self.set_auto_page_break(auto=True, margin=15)
            self.set_left_margin(15)
            self.set_right_margin(15)
            self.set_font('Helvetica', '', 10)  # Font di default per il corpo del report
            
        def header(self):
            # Imposta il titolo del report in alto
            self.set_font('Helvetica', 'B', 14)
            self.cell(0, 10, self.report_title, 0, 1, 'C')
            self.ln(5)
            
        def footer(self):
            # Aggiunge numero di pagina e data al piè di pagina
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            self.cell(0, 10, f'Generato il {now}', 0, 0, 'R')
            
        def add_report_text(self, text_content: str):
            """Aggiunge il contenuto testuale del report al PDF."""
            self.add_page()
            self.set_font('Helvetica', '', 10)
            # Gestisci il testo spezzandolo per righe e controllando il posizionamento
            for line in text_content.split('\n'):
                if line.strip().endswith(':') or line.strip().startswith('==='):
                    # Usa font in grassetto per intestazioni e separatori
                    self.set_font('Helvetica', 'B', 10)
                    self.cell(0, 7, line, 0, 1)
                    self.set_font('Helvetica', '', 10)
                else:
                    # Testo normale
                    self.multi_cell(0, 6, line)
                    
            return self

else:
    # Classi fallback se FPDF non è disponibile
    class PDFPartita:
        pass
        
    class PDFPossessore:
        pass
        
    class GenericTextReportPDF:
        pass

# Funzioni di esportazione
def gui_esporta_partita_json(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    """Esporta i dati di una partita in formato JSON."""
    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati partita non validi per l'esportazione JSON.")
        return

    default_filename = f"partita_{partita_id}_{date.today()}.json"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva JSON Partita", default_filename, "JSON Files (*.json)")
    if not filename:
        return

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(partita_data, f, ensure_ascii=False, indent=4)
        QMessageBox.information(parent_widget, "Esportazione JSON", f"Partita esportata con successo in:\n{filename}")
    except Exception as e:
        gui_logger.exception("Errore esportazione JSON partita (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione JSON:\n{e}")

def gui_esporta_partita_csv(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    """Esporta i dati di una partita in formato CSV."""
    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati partita non validi per l'esportazione CSV.")
        return

    default_filename = f"partita_{partita_id}_{date.today()}.csv"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva CSV Partita", default_filename, "CSV Files (*.csv)")
    if not filename:
        return

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            p_info = partita_data['partita']
            writer.writerow(['--- DETTAGLI PARTITA ---'])
            for key, value in p_info.items():
                writer.writerow([key.replace('_', ' ').title(), value])
            writer.writerow([])

            if partita_data.get('possessori'):
                writer.writerow(['--- POSSESSORI ---'])
                headers = list(partita_data['possessori'][0].keys()) if partita_data['possessori'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title() for h in headers])
                for poss in partita_data['possessori']:
                    writer.writerow([poss.get(h) for h in headers])
                writer.writerow([])
            
            if partita_data.get('immobili'):
                writer.writerow(['--- IMMOBILI ---'])
                headers = list(partita_data['immobili'][0].keys()) if partita_data['immobili'] else []
                if headers:
                    writer.writerow([h.replace('_', ' ').title() for h in headers])
                for imm in partita_data['immobili']:
                    writer.writerow([imm.get(h) for h in headers])

        QMessageBox.information(parent_widget, "Esportazione CSV", f"Partita esportata con successo in:\n{filename}")
    except Exception as e:
        gui_logger.exception("Errore esportazione CSV partita (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione CSV:\n{e}")

def gui_esporta_partita_pdf(parent_widget, db_manager: CatastoDBManager, partita_id: int):
    """Esporta i dati di una partita in formato PDF."""
    if not FPDF_AVAILABLE:
        QMessageBox.warning(parent_widget, "Funzionalità non disponibile", 
                           "La libreria FPDF è necessaria per l'esportazione in PDF, ma non è installata.")
        return
        
    partita_data = db_manager.get_partita_data_for_export(partita_id)
    if not partita_data or 'partita' not in partita_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati partita non validi per l'esportazione PDF.")
        return

    default_filename = f"partita_{partita_id}_{date.today()}.pdf"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva PDF Partita", default_filename, "PDF Files (*.pdf)")
    if not filename:
        return

    try:
        pdf = PDFPartita()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        
        p_info = partita_data['partita']
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, f"Partita N. {p_info.get('numero_partita')}", 0, 1, 'C')
        pdf.ln(5)
        
        pdf.chapter_title('Dettagli Partita')
        details_part = {
            'ID Partita': p_info.get('id'),
            'Numero Partita': p_info.get('numero_partita'),
            'Comune': p_info.get('comune_nome'),
            'Tipo': p_info.get('tipo'),
            'Data Inizio': p_info.get('data_inizio'),
            'Data Fine': p_info.get('data_fine'),
            'Stato': "Attiva" if p_info.get('attiva') else "Non Attiva",
        }
        pdf.chapter_body(details_part)

        if partita_data.get('possessori'):
            pdf.chapter_title('Possessori della Partita')
            headers = ['ID', 'Nome Completo', 'Paternità', 'Quota', 'Titolo']
            col_widths_percent = [10, 40, 20, 10, 20]  # Percentuali larghezza colonne
            data_rows = []
            for poss in partita_data['possessori']:
                data_rows.append([
                    poss.get('id'), poss.get('nome_completo'), poss.get('paternita'),
                    poss.get('quota'), poss.get('titolo')
                ])
            pdf.simple_table(headers, data_rows, col_widths_percent=col_widths_percent)
        
        if partita_data.get('immobili'):
            pdf.chapter_title('Immobili della Partita')
            headers = ['ID', 'Natura', 'Classificazione', 'Consistenza', 'Località']
            col_widths_percent_imm = [10, 30, 25, 15, 20]  # Percentuali larghezza colonne
            data_rows_imm = []
            for imm in partita_data['immobili']:
                data_rows_imm.append([
                    imm.get('id'), imm.get('natura'), imm.get('classificazione'),
                    imm.get('consistenza'), imm.get('localita_nome')
                ])
            pdf.simple_table(headers, data_rows_imm, col_widths_percent=col_widths_percent_imm)

        pdf.output(filename)
        QMessageBox.information(parent_widget, "Esportazione PDF", f"Partita esportata con successo in:\n{filename}")
    except Exception as e:
        gui_logger.exception("Errore esportazione PDF partita (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione PDF:\n{e}")

def gui_esporta_possessore_json(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    """Esporta i dati di un possessore in formato JSON."""
    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati possessore non validi per l'esportazione JSON.")
        return

    default_filename = f"possessore_{possessore_id}_{date.today()}.json"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva JSON Possessore", default_filename, "JSON Files (*.json)")
    if not filename:
        return

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(possessore_data, f, ensure_ascii=False, indent=4)
        QMessageBox.information(parent_widget, "Esportazione JSON", f"Possessore esportato con successo in:\n{filename}")
    except Exception as e:
        gui_logger.exception("Errore esportazione JSON possessore (GUI)")
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione JSON:\n{e}")

def gui_esporta_possessore_csv(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    """Esporta i dati di un possessore in formato CSV."""
    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati possessore non validi per l'esportazione CSV.")
        return

    default_filename = f"possessore_{possessore_id}_{date.today()}.csv"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva CSV Possessore", default_filename, "CSV Files (*.csv)")
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

        QMessageBox.information(parent_widget, "Esportazione CSV", f"Possessore esportato con successo in:\n{filename}")
    except Exception as e:
        QMessageBox.critical(parent_widget, "Errore Esportazione", f"Errore durante l'esportazione CSV:\n{e}")

def gui_esporta_possessore_pdf(parent_widget, db_manager: CatastoDBManager, possessore_id: int):
    """Esporta i dati di un possessore in formato PDF."""
    if not FPDF_AVAILABLE:
        QMessageBox.warning(parent_widget, "Funzionalità non disponibile", 
                           "La libreria FPDF è necessaria per l'esportazione in PDF, ma non è installata.")
        return
        
    possessore_data = db_manager.get_possessore_data_for_export(possessore_id)
    if not possessore_data or 'possessore' not in possessore_data:
        QMessageBox.warning(parent_widget, "Errore Dati", "Dati possessore non validi per l'esportazione PDF.")
        return

    default_filename = f"possessore_{possessore_id}_{date.today()}.pdf"
    filename, _ = QFileDialog.getSaveFileName(parent_widget, "Salva PDF Possessore", default_filename, "PDF Files (*.pdf)")
    if not filename:
        return

    try:
        pdf = PDFPossessore()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(10)
        pdf.set_right_margin(10)
        
        p_info = possessore_data['possessore']
        pdf.chapter_title('Dettagli Possessore')
        details_poss = {
            'ID Possessore': p_info.get('id'),
            'Nome Completo': p_info.get('nome_completo'),
            'Comune Riferimento': p_info.get('comune_nome'),
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
