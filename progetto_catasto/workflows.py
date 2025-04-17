#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow per l'applicazione Catasto Storico
===========================================
Questo modulo contiene implementazioni dei workflow principali.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
from datetime import date
from typing import Dict, List, Any, Callable, Optional

from ui_components import (
    FormDialog, EntitySelectionDialog, ReportViewer, 
    DynamicListFrame, HeaderFrame
)
from db_manager import CatastoDBManager
from config import TIPI_VARIAZIONE, TIPI_CONTRATTO, TIPI_LOCALITA, TIPI_PARTITA, parse_date

class BaseWorkflow:
    """Classe base per i workflow"""
    
    def __init__(self, parent, db_manager, on_complete=None, log_callback=None):
        self.parent = parent
        self.db_manager = db_manager
        self.on_complete = on_complete
        self.log_callback = log_callback
    
    def validate_field(self, value, field_name, required=True, numeric=False, date_format=False):
        """Validazione centralizzata dei campi di input."""
        if required and not value:
            messagebox.showerror("Errore", f"Il campo {field_name} è obbligatorio")
            return False
            
        if value and numeric:
            try:
                int(value)
            except ValueError:
                messagebox.showerror("Errore", f"Il campo {field_name} deve essere un numero intero")
                return False
                
        if value and date_format:
            try:
                parse_date(value)
            except ValueError:
                messagebox.showerror("Errore", f"Il campo {field_name} non è una data valida (formato richiesto: YYYY-MM-DD)")
                return False
                
        return True
    
    def log(self, message):
        """Registra un messaggio di log."""
        if self.log_callback:
            self.log_callback(message)
    
    def complete(self):
        """Completa il workflow."""
        if self.on_complete:
            self.on_complete()
            
class NuovaConsultazioneWorkflow:
    """Workflow per registrare una nuova consultazione"""
    
    def __init__(self, parent, db_manager: CatastoDBManager, on_complete: Callable = None):
        self.parent = parent
        self.db_manager = db_manager
        self.on_complete = on_complete
    
    def execute(self):
        """Esegue il workflow"""
        # Definizione dei campi del form
        fields = [
            {
                'name': 'data',
                'label': 'Data consultazione:',
                'type': 'date',
                'default': 'today',
                'required': True
            },
            {
                'name': 'richiedente',
                'label': 'Richiedente:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'documento_identita',
                'label': 'Documento d\'identità:',
                'type': 'entry'
            },
            {
                'name': 'motivazione',
                'label': 'Motivazione:',
                'type': 'text'
            },
            {
                'name': 'materiale_consultato',
                'label': 'Materiale consultato:',
                'type': 'text'
            },
            {
                'name': 'funzionario_autorizzante',
                'label': 'Funzionario autorizzante:',
                'type': 'entry',
                'required': True
            }
        ]
        
        # Mostra il form
        form_dialog = FormDialog(
            self.parent,
            "Nuova Consultazione",
            fields,
            self.save_consultazione,
            width=600,
            height=500
        )
    
    def save_consultazione(self, form_data: Dict[str, Any]) -> bool:
        """
        Salva la consultazione nel database.
        
        Args:
            form_data: Dati del form
            
        Returns:
            bool: True se l'operazione è avvenuta con successo, False altrimenti
        """
        try:
            # Registra la consultazione nel database
            success = self.db_manager.registra_consultazione(
                form_data['data'],
                form_data['richiedente'],
                form_data['documento_identita'],
                form_data['motivazione'],
                form_data['materiale_consultato'],
                form_data['funzionario_autorizzante']
            )
            
            if success:
                messagebox.showinfo("Successo", "Consultazione registrata con successo")
                if self.on_complete:
                    self.on_complete()
                return True
            else:
                messagebox.showerror("Errore", "Impossibile registrare la consultazione")
                return False
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
            return False

class NuovoPossessoreWorkflow:
    """Workflow per registrare un nuovo possessore"""
    
    def __init__(self, parent, db_manager: CatastoDBManager, on_complete: Callable = None):
        self.parent = parent
        self.db_manager = db_manager
        self.on_complete = on_complete
    
    def execute(self):
        """Esegue il workflow"""
        # Definizione dei campi del form
        fields = [
            {
                'name': 'comune_nome',
                'label': 'Comune:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'cognome_nome',
                'label': 'Cognome e nome:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'paternita',
                'label': 'Paternità:',
                'type': 'entry'
            },
            {
                'name': 'nome_completo',
                'label': 'Nome completo:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'attivo',
                'label': 'Attivo:',
                'type': 'checkbox',
                'default': True
            }
        ]
        
        # Mostra il form
        form_dialog = FormDialog(
            self.parent,
            "Nuovo Possessore",
            fields,
            self.save_possessore,
            width=500,
            height=400
        )
    
    def save_possessore(self, form_data: Dict[str, Any]) -> bool:
        """
        Salva il possessore nel database.
        
        Args:
            form_data: Dati del form
            
        Returns:
            bool: True se l'operazione è avvenuta con successo, False altrimenti
        """
        try:
            query = """
            CALL inserisci_possessore(%s, %s, %s, %s, %s)
            """
            
            success = self.db_manager.execute_query(
                query,
                (
                    form_data['comune_nome'],
                    form_data['cognome_nome'],
                    form_data['paternita'],
                    form_data['nome_completo'],
                    form_data['attivo']
                )
            )
            
            if success:
                self.db_manager.commit()
                messagebox.showinfo("Successo", "Possessore registrato con successo")
                if self.on_complete:
                    self.on_complete()
                return True
            else:
                messagebox.showerror("Errore", "Impossibile registrare il possessore")
                return False
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
            return False

class NuovaPartitaWorkflow:
    """Workflow per registrare una nuova partita"""
    
    def __init__(self, parent, db_manager: CatastoDBManager, on_complete: Callable = None):
        self.parent = parent
        self.db_manager = db_manager
        self.on_complete = on_complete
    
    def execute(self):
        """Esegue il workflow"""
        # Definizione dei campi del form
        fields = [
            {
                'name': 'comune_nome',
                'label': 'Comune:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'numero_partita',
                'label': 'Numero partita:',
                'type': 'entry',
                'numeric': True,
                'required': True
            },
            {
                'name': 'tipo',
                'label': 'Tipo:',
                'type': 'combobox',
                'values': TIPI_PARTITA,
                'default': 'principale',
                'required': True
            },
            {
                'name': 'data_impianto',
                'label': 'Data impianto:',
                'type': 'date',
                'default': 'today',
                'required': True
            },
            {
                'name': 'possessori',
                'label': 'ID Possessori (separati da virgola):',
                'type': 'entry',
                'required': True
            }
        ]
        
        # Mostra il form
        form_dialog = FormDialog(
            self.parent,
            "Nuova Partita",
            fields,
            self.save_partita,
            width=500,
            height=400
        )
    
    def save_partita(self, form_data: Dict[str, Any]) -> bool:
        """
        Salva la partita nel database.
        
        Args:
            form_data: Dati del form
            
        Returns:
            bool: True se l'operazione è avvenuta con successo, False altrimenti
        """
        try:
            # Converte gli ID dei possessori in array
            possessori_str = form_data['possessori']
            possessori_ids = []
            
            for pid in possessori_str.split(','):
                try:
                    possessori_ids.append(int(pid.strip()))
                except ValueError:
                    continue
            
            if not possessori_ids:
                messagebox.showerror("Errore", "ID Possessori non validi")
                return False
            
            query = """
            CALL inserisci_partita_con_possessori(%s, %s, %s, %s, %s)
            """
            
            success = self.db_manager.execute_query(
                query,
                (
                    form_data['comune_nome'],
                    form_data['numero_partita'],
                    form_data['tipo'],
                    form_data['data_impianto'],
                    possessori_ids
                )
            )
            
            if success:
                self.db_manager.commit()
                messagebox.showinfo("Successo", "Partita registrata con successo")
                if self.on_complete:
                    self.on_complete()
                return True
            else:
                messagebox.showerror("Errore", "Impossibile registrare la partita")
                return False
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
            return False

class GeneraCertificatoWorkflow:
    """Workflow per generare un certificato di proprietà"""
    
    def __init__(self, parent, db_manager: CatastoDBManager):
        self.parent = parent
        self.db_manager = db_manager
    
    def execute(self):
        """Esegue il workflow"""
        partita_id = simpledialog.askinteger("Certificato di Proprietà", "Inserisci l'ID della partita:")
        if not partita_id:
            return
        
        try:
            certificato = self.db_manager.genera_certificato_proprieta(partita_id)
            
            if certificato:
                # Mostra il certificato
                report_viewer = ReportViewer(
                    self.parent,
                    f"Certificato di Proprietà - Partita {partita_id}",
                    certificato
                )
            else:
                messagebox.showerror("Errore", "Impossibile generare il certificato")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")

class GeneraReportGenealogico:
    """Workflow per generare un report genealogico"""
    
    def __init__(self, parent, db_manager: CatastoDBManager):
        self.parent = parent
        self.db_manager = db_manager
    
    def execute(self):
        """Esegue il workflow"""
        partita_id = simpledialog.askinteger("Report Genealogico", "Inserisci l'ID della partita:")
        if not partita_id:
            return
        
        try:
            report = self.db_manager.genera_report_genealogico(partita_id)
            
            if report:
                # Mostra il report
                report_viewer = ReportViewer(
                    self.parent,
                    f"Report Genealogico - Partita {partita_id}",
                    report
                )
            else:
                messagebox.showerror("Errore", "Impossibile generare il report")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")

class GeneraReportPossessore:
    """Workflow per generare un report possessore"""
    
    def __init__(self, parent, db_manager: CatastoDBManager):
        self.parent = parent
        self.db_manager = db_manager
    
    def execute(self):
        """Esegue il workflow"""
        possessore_id = simpledialog.askinteger("Report Possessore", "Inserisci l'ID del possessore:")
        if not possessore_id:
            return
        
        try:
            report = self.db_manager.genera_report_possessore(possessore_id)
            
            if report:
                # Mostra il report
                report_viewer = ReportViewer(
                    self.parent,
                    f"Report Possessore - ID {possessore_id}",
                    report
                )
            else:
                messagebox.showerror("Errore", "Impossibile generare il report")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")

class RegistraNuovaProprietaWorkflow:
    """Workflow per registrare una nuova proprietà"""
    
    def __init__(self, parent, db_manager: CatastoDBManager, on_complete: Callable = None, log_callback: Callable = None):
        self.parent = parent
        self.db_manager = db_manager
        self.on_complete = on_complete
        self.log_callback = log_callback
        
        # Variabili di stato
        self.possessori = []
        self.immobili = []
    
    def execute(self):
        """Esegue il workflow"""
        # Crea la finestra principale del workflow
        self.window = tk.Toplevel(self.parent)
        self.window.title("Registrazione Nuova Proprietà")
        self.window.geometry("900x700")
        self.window.grab_set()
        
        # Intestazione
        header = HeaderFrame(self.window, "Registrazione Nuova Proprietà", 
                           "Questo wizard ti guiderà nella registrazione di una nuova proprietà immobiliare")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Notebook per organizzare le varie sezioni
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tabs
        self.tab_partita = ttk.Frame(self.notebook)
        self.tab_possessori = ttk.Frame(self.notebook)
        self.tab_immobili = ttk.Frame(self.notebook)
        self.tab_riepilogo = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_partita, text="Dati Partita")
        self.notebook.add(self.tab_possessori, text="Possessori")
        self.notebook.add(self.tab_immobili, text="Immobili")
        self.notebook.add(self.tab_riepilogo, text="Riepilogo")
        
        # Configura le schede
        self.setup_tab_partita()
        self.setup_tab_possessori()
        self.setup_tab_immobili()
        self.setup_tab_riepilogo()
        
        # Pulsanti di navigazione
        buttons_frame = ttk.Frame(self.window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(buttons_frame, text="Annulla", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
        self.btn_registra = ttk.Button(buttons_frame, text="Registra Proprietà", command=self.registra_proprieta)
        self.btn_registra.pack(side=tk.RIGHT, padx=5)
        self.btn_avanti = ttk.Button(buttons_frame, text="Avanti", command=self.next_tab)
        self.btn_avanti.pack(side=tk.RIGHT, padx=5)
        self.btn_indietro = ttk.Button(buttons_frame, text="Indietro", command=self.prev_tab)
        self.btn_indietro.pack(side=tk.RIGHT, padx=5)
        
        # Inizialmente disattiva il pulsante Indietro
        self.btn_indietro.config(state=tk.DISABLED)
        
        # Aggiorna lo stato dei pulsanti quando cambia la scheda
        self.notebook.bind("<<NotebookTabChanged>>", self.update_buttons)
    
    def setup_tab_partita(self):
        """Configura la scheda dei dati della partita"""
        frame = ttk.Frame(self.tab_partita, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Campi
        ttk.Label(frame, text="Comune:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.comune_entry = ttk.Entry(frame, width=30)
        self.comune_entry.grid(row=0, column=1, pady=5, sticky=tk.W)
        
        ttk.Label(frame, text="Numero partita:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.numero_entry = ttk.Entry(frame, width=30)
        self.numero_entry.grid(row=1, column=1, pady=5, sticky=tk.W)
        
        ttk.Label(frame, text="Data impianto:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.data_entry = ttk.Entry(frame, width=30)
        self.data_entry.grid(row=2, column=1, pady=5, sticky=tk.W)
        self.data_entry.insert(0, date.today().strftime("%Y-%m-%d"))
    
    def setup_tab_possessori(self):
        """Configura la scheda dei possessori"""
        frame = ttk.Frame(self.tab_possessori, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Lista possessori
        columns = [
            {'id': 'nome_completo', 'header': 'Nome completo', 'width': 200},
            {'id': 'paternita', 'header': 'Paternità', 'width': 150},
            {'id': 'quota', 'header': 'Quota', 'width': 100}
        ]
        
        self.possessori_list = DynamicListFrame(
            frame, 
            "Possessori", 
            columns, 
            self.add_possessore, 
            self.remove_possessori
        )
        self.possessori_list.pack(fill=tk.BOTH, expand=True, pady=10)
    
    def setup_tab_immobili(self):
        """Configura la scheda degli immobili"""
        frame = ttk.Frame(self.tab_immobili, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Lista immobili
        columns = [
            {'id': 'natura', 'header': 'Natura', 'width': 150},
            {'id': 'localita', 'header': 'Località', 'width': 150},
            {'id': 'tipo_localita', 'header': 'Tipo', 'width': 100},
            {'id': 'classificazione', 'header': 'Classificazione', 'width': 150}
        ]
        
        self.immobili_list = DynamicListFrame(
            frame, 
            "Immobili", 
            columns, 
            self.add_immobile, 
            self.remove_immobili
        )
        self.immobili_list.pack(fill=tk.BOTH, expand=True, pady=10)
    
    def setup_tab_riepilogo(self):
        """Configura la scheda di riepilogo"""
        frame = ttk.Frame(self.tab_riepilogo, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Riepilogo registrazione", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # Area di testo per il riepilogo
        self.riepilogo_text = tk.Text(frame, width=80, height=30)
        self.riepilogo_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def update_buttons(self, event=None):
        """Aggiorna lo stato dei pulsanti in base alla scheda corrente"""
        current_tab = self.notebook.index(self.notebook.select())
        
        # Abilita/disabilita il pulsante Indietro
        if current_tab == 0:
            self.btn_indietro.config(state=tk.DISABLED)
        else:
            self.btn_indietro.config(state=tk.NORMAL)
        
        # Abilita/disabilita il pulsante Avanti
        if current_tab == 3:  # Ultima scheda (Riepilogo)
            self.btn_avanti.config(state=tk.DISABLED)
            self.update_riepilogo()
        else:
            self.btn_avanti.config(state=tk.NORMAL)
    
    def next_tab(self):
        """Passa alla scheda successiva"""
        current_tab = self.notebook.index(self.notebook.select())
        
        # Validazione prima di procedere
        if current_tab == 0:  # Scheda Partita
            if not self.validate_partita():
                return
        elif current_tab == 1:  # Scheda Possessori
            if not self.validate_possessori():
                return
        elif current_tab == 2:  # Scheda Immobili
            if not self.validate_immobili():
                return
        
        # Passa alla scheda successiva
        if current_tab < 3:  # 3 è l'indice dell'ultima scheda
            self.notebook.select(current_tab + 1)
    
    def prev_tab(self):
        """Passa alla scheda precedente"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab > 0:
            self.notebook.select(current_tab - 1)
    
    def validate_partita(self):
        """Valida i dati della partita"""
        comune = self.comune_entry.get()
        numero = self.numero_entry.get()
        data = self.data_entry.get()
        
        if not comune:
            messagebox.showerror("Errore", "Il campo Comune è obbligatorio")
            return False
        
        if not numero:
            messagebox.showerror("Errore", "Il campo Numero partita è obbligatorio")
            return False
        
        try:
            int(numero)
        except ValueError:
            messagebox.showerror("Errore", "Numero partita deve essere un numero intero")
            return False
        
        if not data:
            messagebox.showerror("Errore", "Il campo Data impianto è obbligatorio")
            return False
        
        try:
            parse_date(data)
        except ValueError:
            messagebox.showerror("Errore", "Data impianto non valida (formato richiesto: YYYY-MM-DD)")
            return False
        
        return True
    
    def validate_possessori(self):
        """Valida i dati dei possessori"""
        items = self.possessori_list.get_all_items()
        
        if not items:
            messagebox.showerror("Errore", "È necessario inserire almeno un possessore")
            return False
        
        return True
    
    def validate_immobili(self):
        """Valida i dati degli immobili"""
        items = self.immobili_list.get_all_items()
        
        if not items:
            messagebox.showerror("Errore", "È necessario inserire almeno un immobile")
            return False
        
        return True
    
    def add_possessore(self):
        """Aggiunge un possessore alla lista"""
        # Definizione dei campi del form
        fields = [
            {
                'name': 'nome_completo',
                'label': 'Nome completo:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'cognome_nome',
                'label': 'Cognome e nome:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'paternita',
                'label': 'Paternità:',
                'type': 'entry'
            },
            {
                'name': 'quota',
                'label': 'Quota:',
                'type': 'entry'
            }
        ]
        
        # Mostra il form
        form_dialog = FormDialog(
            self.window,
            "Aggiungi Possessore",
            fields,
            self.save_possessore,
            width=500,
            height=350
        )
    
    def save_possessore(self, form_data):
        """Salva il possessore nella lista"""
        # Aggiunge il possessore alla lista
        self.possessori_list.add_item(form_data)
        
        # Memorizza i dati del possessore
        self.possessori.append(form_data)
        
        return True
    
    def remove_possessori(self, selected_items):
        """Rimuove i possessori selezionati dalla lista"""
        # Rimuove i possessori dalla memoria
        for item in selected_items:
            idx = int(item[1:]) - 1  # L'ID nel treeview è I001, I002, etc.
            if 0 <= idx < len(self.possessori):
                self.possessori.pop(idx)
    
    def add_immobile(self):
        """Aggiunge un immobile alla lista"""
        # Definizione dei campi del form
        fields = [
            {
                'name': 'natura',
                'label': 'Natura:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'localita',
                'label': 'Località:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'tipo_localita',
                'label': 'Tipo località:',
                'type': 'combobox',
                'values': TIPI_LOCALITA,
                'default': 'regione',
                'required': True
            },
            {
                'name': 'classificazione',
                'label': 'Classificazione:',
                'type': 'entry'
            },
            {
                'name': 'numero_piani',
                'label': 'Numero piani:',
                'type': 'entry',
                'numeric': True
            },
            {
                'name': 'numero_vani',
                'label': 'Numero vani:',
                'type': 'entry',
                'numeric': True
            },
            {
                'name': 'consistenza',
                'label': 'Consistenza:',
                'type': 'entry'
            }
        ]
        
        # Mostra il form
        form_dialog = FormDialog(
            self.window,
            "Aggiungi Immobile",
            fields,
            self.save_immobile,
            width=500,
            height=500
        )
    
    def save_immobile(self, form_data):
        """Salva l'immobile nella lista"""
        # Aggiunge l'immobile alla lista
        self.immobili_list.add_item(form_data)
        
        # Memorizza i dati dell'immobile
        self.immobili.append(form_data)
        
        return True
    
    def remove_immobili(self, selected_items):
        """Rimuove gli immobili selezionati dalla lista"""
        # Rimuove gli immobili dalla memoria
        for item in selected_items:
            idx = int(item[1:]) - 1  # L'ID nel treeview è I001, I002, etc.
            if 0 <= idx < len(self.immobili):
                self.immobili.pop(idx)
    
    def update_riepilogo(self):
        """Aggiorna il riepilogo con i dati inseriti"""
        comune = self.comune_entry.get()
        numero = self.numero_entry.get()
        data = self.data_entry.get()
        
        # Pulisce il testo
        self.riepilogo_text.delete("1.0", tk.END)
        
        # Aggiunge i dati della partita
        self.riepilogo_text.insert(tk.END, "=== DATI PARTITA ===\n")
        self.riepilogo_text.insert(tk.END, f"Comune: {comune}\n")
        self.riepilogo_text.insert(tk.END, f"Numero partita: {numero}\n")
        self.riepilogo_text.insert(tk.END, f"Data impianto: {data}\n\n")
        
        # Aggiunge i dati dei possessori
        self.riepilogo_text.insert(tk.END, "=== POSSESSORI ===\n")
        for i, p in enumerate(self.possessori, 1):
            self.riepilogo_text.insert(tk.END, f"{i}. {p['nome_completo']}")
            if p.get('quota'):
                self.riepilogo_text.insert(tk.END, f" (quota: {p['quota']})")
            self.riepilogo_text.insert(tk.END, "\n")
        
        self.riepilogo_text.insert(tk.END, "\n=== IMMOBILI ===\n")
        for i, imm in enumerate(self.immobili, 1):
            self.riepilogo_text.insert(tk.END, f"{i}. {imm['natura']} in {imm['localita']} ({imm['tipo_localita']})\n")
            if imm.get('classificazione'):
                self.riepilogo_text.insert(tk.END, f"   Classificazione: {imm['classificazione']}\n")
            if imm.get('numero_piani'):
                self.riepilogo_text.insert(tk.END, f"   Piani: {imm['numero_piani']}\n")
            if imm.get('numero_vani'):
                self.riepilogo_text.insert(tk.END, f"   Vani: {imm['numero_vani']}\n")
            if imm.get('consistenza'):
                self.riepilogo_text.insert(tk.END, f"   Consistenza: {imm['consistenza']}\n")
    
    def registra_proprieta(self):
        """Registra la proprietà nel database"""
        # Verifica di nuovo tutti i dati
        if not self.validate_partita() or not self.validate_possessori() or not self.validate_immobili():
            return
        
        comune = self.comune_entry.get()
        numero = int(self.numero_entry.get())
        data = parse_date(self.data_entry.get())
        
        try:
            # Registra la proprietà
            success = self.db_manager.registra_nuova_proprieta(
                comune, numero, data, self.possessori, self.immobili
            )
            
            if success:
                messagebox.showinfo("Successo", "Proprietà registrata con successo")
                if self.log_callback:
                    self.log_callback(f"Registrata nuova proprietà: Partita {numero} del comune {comune}")
                if self.on_complete:
                    self.on_complete()
                self.window.destroy()
            else:
                messagebox.showerror("Errore", "Impossibile registrare la proprietà")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")

class RegistraPassaggioProprietaWorkflow:
    """Workflow per registrare un passaggio di proprietà"""
    
    def __init__(self, parent, db_manager: CatastoDBManager, on_complete: Callable = None, log_callback: Callable = None):
        self.parent = parent
        self.db_manager = db_manager
        self.on_complete = on_complete
        self.log_callback = log_callback
        
        # Variabili di stato
        self.possessori_origine = {}
        self.nuovi_possessori = []
        self.selected_immobili = []
    
    def execute(self):
        """Esegue il workflow"""
        # Crea la finestra principale del workflow
        self.window = tk.Toplevel(self.parent)
        self.window.title("Registrazione Passaggio di Proprietà")
        self.window.geometry("900x700")
        self.window.grab_set()
        
        # Intestazione
        header = HeaderFrame(self.window, "Registrazione Passaggio di Proprietà", 
                           "Questo wizard ti guiderà nella registrazione di un passaggio di proprietà")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Notebook per organizzare le varie sezioni
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tabs
        self.tab_partite = ttk.Frame(self.notebook)
        self.tab_variazione = ttk.Frame(self.notebook)
        self.tab_possessori = ttk.Frame(self.notebook)
        self.tab_immobili = ttk.Frame(self.notebook)
        self.tab_riepilogo = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_partite, text="Partite")
        self.notebook.add(self.tab_variazione, text="Variazione")
        self.notebook.add(self.tab_possessori, text="Possessori")
        self.notebook.add(self.tab_immobili, text="Immobili")
        self.notebook.add(self.tab_riepilogo, text="Riepilogo")
        
        # Configura le schede
        self.setup_tab_partite()
        self.setup_tab_variazione()
        self.setup_tab_possessori()
        self.setup_tab_immobili()
        self.setup_tab_riepilogo()
        
        # Pulsanti di navigazione
        buttons_frame = ttk.Frame(self.window)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(buttons_frame, text="Annulla", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
        self.btn_registra = ttk.Button(buttons_frame, text="Registra Passaggio", command=self.registra_passaggio)
        self.btn_registra.pack(side=tk.RIGHT, padx=5)
        self.btn_avanti = ttk.Button(buttons_frame, text="Avanti", command=self.next_tab)
        self.btn_avanti.pack(side=tk.RIGHT, padx=5)
        self.btn_indietro = ttk.Button(buttons_frame, text="Indietro", command=self.prev_tab)
        self.btn_indietro.pack(side=tk.RIGHT, padx=5)
        
        # Inizialmente disattiva il pulsante Indietro
        self.btn_indietro.config(state=tk.DISABLED)
        
        # Aggiorna lo stato dei pulsanti quando cambia la scheda
        self.notebook.bind("<<NotebookTabChanged>>", self.update_buttons)
    
    def setup_tab_partite(self):
        """Configura la scheda delle partite"""
        frame = ttk.Frame(self.tab_partite, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Partita origine
        origine_frame = ttk.LabelFrame(frame, text="Partita di Origine")
        origine_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(origine_frame, text="ID Partita origine:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.partita_origine_id_entry = ttk.Entry(origine_frame, width=20)
        self.partita_origine_id_entry.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        
        ttk.Button(origine_frame, text="Visualizza Dati", command=self.load_partita_origine).grid(row=0, column=2, pady=5, padx=5)
        
        self.partita_origine_info = tk.Text(origine_frame, width=40, height=5, state=tk.DISABLED)
        self.partita_origine_info.grid(row=1, column=0, columnspan=3, pady=5, padx=5, sticky=tk.W+tk.E)
        
        # Nuova partita
        nuova_partita_frame = ttk.LabelFrame(frame, text="Nuova Partita")
        nuova_partita_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(nuova_partita_frame, text="Comune:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.comune_entry = ttk.Entry(nuova_partita_frame, width=30)
        self.comune_entry.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        
        ttk.Label(nuova_partita_frame, text="Numero partita:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.numero_entry = ttk.Entry(nuova_partita_frame, width=30)
        self.numero_entry.grid(row=1, column=1, pady=5, padx=5, sticky=tk.W)
    
    def setup_tab_variazione(self):
        """Configura la scheda della variazione"""
        frame = ttk.Frame(self.tab_variazione, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Dati variazione
        variazione_frame = ttk.LabelFrame(frame, text="Dati Variazione")
        variazione_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(variazione_frame, text="Tipo variazione:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.tipo_variazione_var = tk.StringVar()
        self.tipo_variazione_combo = ttk.Combobox(variazione_frame, textvariable=self.tipo_variazione_var, width=28, values=TIPI_VARIAZIONE)
        self.tipo_variazione_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        
        ttk.Label(variazione_frame, text="Data variazione:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.data_variazione_entry = ttk.Entry(variazione_frame, width=30)
        self.data_variazione_entry.grid(row=1, column=1, pady=5, padx=5, sticky=tk.W)
        self.data_variazione_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        
        # Dati contratto
        contratto_frame = ttk.LabelFrame(frame, text="Dati Contratto")
        contratto_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(contratto_frame, text="Tipo contratto:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.tipo_contratto_var = tk.StringVar()
        self.tipo_contratto_combo = ttk.Combobox(contratto_frame, textvariable=self.tipo_contratto_var, width=28, values=TIPI_CONTRATTO)
        self.tipo_contratto_combo.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        
        ttk.Label(contratto_frame, text="Data contratto:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.data_contratto_entry = ttk.Entry(contratto_frame, width=30)
        self.data_contratto_entry.grid(row=1, column=1, pady=5, padx=5, sticky=tk.W)
        self.data_contratto_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        
        ttk.Label(contratto_frame, text="Notaio:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.notaio_entry = ttk.Entry(contratto_frame, width=30)
        self.notaio_entry.grid(row=2, column=1, pady=5, padx=5, sticky=tk.W)
        
        ttk.Label(contratto_frame, text="Repertorio:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        self.repertorio_entry = ttk.Entry(contratto_frame, width=30)
        self.repertorio_entry.grid(row=3, column=1, pady=5, padx=5, sticky=tk.W)
        
        ttk.Label(contratto_frame, text="Note:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        self.note_text = tk.Text(contratto_frame, width=30, height=5)
        self.note_text.grid(row=4, column=1, pady=5, padx=5, sticky=tk.W)
    
    def setup_tab_possessori(self):
        """Configura la scheda dei possessori"""
        frame = ttk.Frame(self.tab_possessori, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Opzioni
        options_frame = ttk.Frame(frame)
        options_frame.pack(fill=tk.X, pady=10)
        
        self.mantieni_possessori_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Mantieni gli stessi possessori", variable=self.mantieni_possessori_var, command=self.toggle_possessori_list).pack(anchor=tk.W, pady=5)
        
        # Lista nuovi possessori
        self.nuovi_possessori_frame = ttk.LabelFrame(frame, text="Nuovi Possessori")
        
        columns = [
            {'id': 'nome_completo', 'header': 'Nome completo', 'width': 200},
            {'id': 'paternita', 'header': 'Paternità', 'width': 150}
        ]
        
        self.possessori_list = DynamicListFrame(
            self.nuovi_possessori_frame, 
            "Possessori", 
            columns, 
            self.add_possessore, 
            self.remove_possessori
        )
        self.possessori_list.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Inizialmente nascondi la lista
        self.toggle_possessori_list()
    
    def setup_tab_immobili(self):
        """Configura la scheda degli immobili"""
        frame = ttk.Frame(self.tab_immobili, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Opzioni
        options_frame = ttk.Frame(frame)
        options_frame.pack(fill=tk.X, pady=10)
        
        self.trasferisci_immobili_var = tk.StringVar(value="tutti")
        ttk.Radiobutton(options_frame, text="Trasferire tutti gli immobili", variable=self.trasferisci_immobili_var, value="tutti", command=self.toggle_immobili_list).pack(anchor=tk.W, pady=5)
        ttk.Radiobutton(options_frame, text="Trasferire solo gli immobili selezionati", variable=self.trasferisci_immobili_var, value="selezionati", command=self.toggle_immobili_list).pack(anchor=tk.W, pady=5)
        
        # Lista immobili
        self.immobili_frame = ttk.LabelFrame(frame, text="Immobili da Trasferire")
        
        columns = [
            {'id': 'id', 'header': 'ID', 'width': 50},
            {'id': 'natura', 'header': 'Natura', 'width': 150},
            {'id': 'localita_nome', 'header': 'Località', 'width': 150},
            {'id': 'classificazione', 'header': 'Classificazione', 'width': 150}
        ]
        
        self.immobili_list = ResultsTreeview(self.immobili_frame, columns)
        self.immobili_list.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Inizialmente nascondi la lista
        self.toggle_immobili_list()
    
    def setup_tab_riepilogo(self):
        """Configura la scheda di riepilogo"""
        frame = ttk.Frame(self.tab_riepilogo, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Riepilogo passaggio di proprietà", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # Area di testo per il riepilogo
        self.riepilogo_text = tk.Text(frame, width=80, height=30)
        self.riepilogo_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def update_buttons(self, event=None):
        """Aggiorna lo stato dei pulsanti in base alla scheda corrente"""
        current_tab = self.notebook.index(self.notebook.select())
        
        # Abilita/disabilita il pulsante Indietro
        if current_tab == 0:
            self.btn_indietro.config(state=tk.DISABLED)
        else:
            self.btn_indietro.config(state=tk.NORMAL)
        
        # Abilita/disabilita il pulsante Avanti
        if current_tab == 4:  # Ultima scheda (Riepilogo)
            self.btn_avanti.config(state=tk.DISABLED)
            self.update_riepilogo()
        else:
            self.btn_avanti.config(state=tk.NORMAL)
    
    def next_tab(self):
        """Passa alla scheda successiva"""
        current_tab = self.notebook.index(self.notebook.select())
        
        # Validazione prima di procedere
        if current_tab == 0:  # Scheda Partite
            if not self.validate_partite():
                return
        elif current_tab == 1:  # Scheda Variazione
            if not self.validate_variazione():
                return
        elif current_tab == 2:  # Scheda Possessori
            if not self.validate_possessori():
                return
        elif current_tab == 3:  # Scheda Immobili
            if not self.validate_immobili():
                return
        
        # Passa alla scheda successiva
        if current_tab < 4:  # 4 è l'indice dell'ultima scheda
            self.notebook.select(current_tab + 1)
    
    def prev_tab(self):
        """Passa alla scheda precedente"""
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab > 0:
            self.notebook.select(current_tab - 1)
    
    def load_partita_origine(self):
        """Carica i dati della partita di origine"""
        try:
            partita_id = self.partita_origine_id_entry.get()
            
            if not partita_id:
                messagebox.showerror("Errore", "Inserire l'ID della partita di origine")
                return
            
            try:
                partita_id = int(partita_id)
            except ValueError:
                messagebox.showerror("Errore", "ID Partita deve essere un numero intero")
                return
            
            # Recupera i dati della partita
            partita = self.db_manager.get_partita_details(partita_id)
            
            if not partita:
                messagebox.showerror("Errore", "Partita non trovata")
                return
            
            # Imposta il comune della nuova partita
            self.comune_entry.delete(0, tk.END)
            self.comune_entry.insert(0, partita['comune_nome'])
            
            # Visualizza le informazioni della partita
            self.partita_origine_info.config(state=tk.NORMAL)
            self.partita_origine_info.delete("1.0", tk.END)
            self.partita_origine_info.insert(tk.END, f"Comune: {partita['comune_nome']}\n")
            self.partita_origine_info.insert(tk.END, f"Numero: {partita['numero_partita']}\n")
            self.partita_origine_info.insert(tk.END, f"Tipo: {partita['tipo']}\n")
            self.partita_origine_info.insert(tk.END, f"Stato: {partita['stato']}\n")
            self.partita_origine_info.config(state=tk.DISABLED)
            
            # Carica gli immobili
            immobili = self.db_manager.get_immobili_partita(partita_id)
            self.immobili_list.populate(immobili)
            
            # Salva i possessori per uso futuro
            possessori = self.db_manager.get_possessori_partita(partita_id)
            self.possessori_origine = {p['id']: p['nome_completo'] for p in possessori}
            
            # Mostra la lista immobili se necessario
            if self.trasferisci_immobili_var.get() == "selezionati":
                self.immobili_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
    
    def toggle_possessori_list(self):
        """Mostra/nasconde la lista dei nuovi possessori"""
        if self.mantieni_possessori_var.get():
            self.nuovi_possessori_frame.pack_forget()
        else:
            self.nuovi_possessori_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    def toggle_immobili_list(self):
        """Mostra/nasconde la lista degli immobili da trasferire"""
        if self.trasferisci_immobili_var.get() == "tutti":
            self.immobili_frame.pack_forget()
        else:
            self.immobili_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    def validate_partite(self):
        """Valida i dati delle partite"""
        partita_origine_id = self.partita_origine_id_entry.get()
        comune = self.comune_entry.get()
        numero = self.numero_entry.get()
        
        if not partita_origine_id:
            messagebox.showerror("Errore", "Il campo ID Partita origine è obbligatorio")
            return False
        
        try:
            int(partita_origine_id)
        except ValueError:
            messagebox.showerror("Errore", "ID Partita origine deve essere un numero intero")
            return False
        
        if not comune:
            messagebox.showerror("Errore", "Il campo Comune è obbligatorio")
            return False
        
        if not numero:
            messagebox.showerror("Errore", "Il campo Numero partita è obbligatorio")
            return False
        
        try:
            int(numero)
        except ValueError:
            messagebox.showerror("Errore", "Numero partita deve essere un numero intero")
            return False
        
        return True
    
    def validate_variazione(self):
        """Valida i dati della variazione"""
        tipo_variazione = self.tipo_variazione_var.get()
        data_variazione = self.data_variazione_entry.get()
        tipo_contratto = self.tipo_contratto_var.get()
        data_contratto = self.data_contratto_entry.get()
        
        if not tipo_variazione:
            messagebox.showerror("Errore", "Il campo Tipo variazione è obbligatorio")
            return False
        
        if not data_variazione:
            messagebox.showerror("Errore", "Il campo Data variazione è obbligatorio")
            return False
        
        try:
            parse_date(data_variazione)
        except ValueError:
            messagebox.showerror("Errore", "Data variazione non valida (formato richiesto: YYYY-MM-DD)")
            return False
        
        if not tipo_contratto:
            messagebox.showerror("Errore", "Il campo Tipo contratto è obbligatorio")
            return False
        
        if not data_contratto:
            messagebox.showerror("Errore", "Il campo Data contratto è obbligatorio")
            return False
        
        try:
            parse_date(data_contratto)
        except ValueError:
            messagebox.showerror("Errore", "Data contratto non valida (formato richiesto: YYYY-MM-DD)")
            return False
        
        return True
    
    def validate_possessori(self):
        """Valida i dati dei possessori"""
        if not self.mantieni_possessori_var.get():
            # Verifica che ci siano nuovi possessori
            items = self.possessori_list.get_all_items()
            
            if not items:
                messagebox.showerror("Errore", "È necessario inserire almeno un possessore")
                return False
        
        return True
    
    def validate_immobili(self):
        """Valida i dati degli immobili"""
        if self.trasferisci_immobili_var.get() == "selezionati":
            # Verifica che ci siano immobili selezionati
            selected = self.immobili_list.tree.selection()
            
            if not selected:
                messagebox.showerror("Errore", "È necessario selezionare almeno un immobile")
                return False
            
            # Salva gli ID degli immobili selezionati
            self.selected_immobili = []
            for item in selected:
                values = self.immobili_list.tree.item(item, "values")
                self.selected_immobili.append(int(values[0]))
        
        return True
    
    def add_possessore(self):
        """Aggiunge un possessore alla lista"""
        # Definizione dei campi del form
        fields = [
            {
                'name': 'nome_completo',
                'label': 'Nome completo:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'cognome_nome',
                'label': 'Cognome e nome:',
                'type': 'entry',
                'required': True
            },
            {
                'name': 'paternita',
                'label': 'Paternità:',
                'type': 'entry'
            }
        ]
        
        # Mostra il form
        form_dialog = FormDialog(
            self.window,
            "Aggiungi Possessore",
            fields,
            self.save_possessore,
            width=500,
            height=350
        )
    
    def save_possessore(self, form_data):
        """Salva il possessore nella lista"""
        # Aggiunge il possessore alla lista
        self.possessori_list.add_item(form_data)
        
        # Memorizza i dati del possessore
        self.nuovi_possessori.append(form_data)
        
        return True
    
    def remove_possessori(self, selected_items):
        """Rimuove i possessori selezionati dalla lista"""
        # Rimuove i possessori dalla memoria
        for item in selected_items:
            idx = int(item[1:]) - 1  # L'ID nel treeview è I001, I002, etc.
            if 0 <= idx < len(self.nuovi_possessori):
                self.nuovi_possessori.pop(idx)
    
    def update_riepilogo(self):
        """Aggiorna il riepilogo con i dati inseriti"""
        partita_origine_id = self.partita_origine_id_entry.get()
        comune = self.comune_entry.get()
        numero = self.numero_entry.get()
        tipo_variazione = self.tipo_variazione_var.get()
        data_variazione = self.data_variazione_entry.get()
        tipo_contratto = self.tipo_contratto_var.get()
        data_contratto = self.data_contratto_entry.get()
        notaio = self.notaio_entry.get()
        repertorio = self.repertorio_entry.get()
        note = self.note_text.get("1.0", tk.END).strip()
        
        # Pulisce il testo
        self.riepilogo_text.delete("1.0", tk.END)
        
        # Aggiunge i dati delle partite
        self.riepilogo_text.insert(tk.END, "=== PARTITE ===\n")
        self.riepilogo_text.insert(tk.END, f"Partita origine: {partita_origine_id}\n")
        self.riepilogo_text.insert(tk.END, f"Nuova partita: {numero} ({comune})\n\n")
        
        # Aggiunge i dati della variazione
        self.riepilogo_text.insert(tk.END, "=== VARIAZIONE ===\n")
        self.riepilogo_text.insert(tk.END, f"Tipo variazione: {tipo_variazione}\n")
        self.riepilogo_text.insert(tk.END, f"Data variazione: {data_variazione}\n")
        self.riepilogo_text.insert(tk.END, f"Tipo contratto: {tipo_contratto}\n")
        self.riepilogo_text.insert(tk.END, f"Data contratto: {data_contratto}\n")
        if notaio:
            self.riepilogo_text.insert(tk.END, f"Notaio: {notaio}\n")
        if repertorio:
            self.riepilogo_text.insert(tk.END, f"Repertorio: {repertorio}\n")
        if note:
            self.riepilogo_text.insert(tk.END, f"Note: {note}\n")
        self.riepilogo_text.insert(tk.END, "\n")
        
        # Aggiunge i dati dei possessori
        self.riepilogo_text.insert(tk.END, "=== POSSESSORI ===\n")
        if self.mantieni_possessori_var.get():
            self.riepilogo_text.insert(tk.END, "Mantenere gli stessi possessori della partita origine\n")
            for pid, nome in self.possessori_origine.items():
                self.riepilogo_text.insert(tk.END, f"- {nome} (ID: {pid})\n")
        else:
            self.riepilogo_text.insert(tk.END, "Nuovi possessori:\n")
            for p in self.nuovi_possessori:
                self.riepilogo_text.insert(tk.END, f"- {p['nome_completo']}\n")
        self.riepilogo_text.insert(tk.END, "\n")
        
        # Aggiunge i dati degli immobili
        self.riepilogo_text.insert(tk.END, "=== IMMOBILI ===\n")
        if self.trasferisci_immobili_var.get() == "tutti":
            self.riepilogo_text.insert(tk.END, "Trasferire tutti gli immobili\n")
        else:
            self.riepilogo_text.insert(tk.END, "Trasferire solo gli immobili selezionati:\n")
            for immobile_id in self.selected_immobili:
                self.riepilogo_text.insert(tk.END, f"- Immobile ID: {immobile_id}\n")
    
    def registra_passaggio(self):
        """Registra il passaggio di proprietà nel database"""
        # Verifica di nuovo tutti i dati
        if not (self.validate_partite() and self.validate_variazione() and 
               self.validate_possessori() and self.validate_immobili()):
            return
        
        partita_origine_id = int(self.partita_origine_id_entry.get())
        comune = self.comune_entry.get()
        numero = int(self.numero_entry.get())
        tipo_variazione = self.tipo_variazione_var.get()
        data_variazione = parse_date(self.data_variazione_entry.get())
        tipo_contratto = self.tipo_contratto_var.get()
        data_contratto = parse_date(self.data_contratto_entry.get())
        notaio = self.notaio_entry.get() or None
        repertorio = self.repertorio_entry.get() or None
        note = self.note_text.get("1.0", tk.END).strip() or None
        
        # Prepara i dati dei possessori
        nuovi_possessori = None if self.mantieni_possessori_var.get() else self.nuovi_possessori
        
        # Prepara i dati degli immobili
        immobili_da_trasferire = None if self.trasferisci_immobili_var.get() == "tutti" else self.selected_immobili
        
        try:
            # Registra il passaggio di proprietà
            success = self.db_manager.registra_passaggio_proprieta(
                partita_origine_id, comune, numero, tipo_variazione, data_variazione,
                tipo_contratto, data_contratto, notaio=notaio, repertorio=repertorio,
                nuovi_possessori=nuovi_possessori, immobili_da_trasferire=immobili_da_trasferire,
                note=note
            )
            
            if success:
                messagebox.showinfo("Successo", "Passaggio di proprietà registrato con successo")
                if self.log_callback:
                    self.log_callback(f"Registrato passaggio di proprietà: Partita {partita_origine_id} -> {numero}")
                if self.on_complete:
                    self.on_complete()
                self.window.destroy()
            else:
                messagebox.showerror("Errore", "Impossibile registrare il passaggio di proprietà")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")

class BackupLogicoDatiWorkflow:
    """Workflow per eseguire un backup logico dei dati"""
    
    def __init__(self, parent, db_manager: CatastoDBManager, log_callback: Callable = None):
        self.parent = parent
        self.db_manager = db_manager
        self.log_callback = log_callback
    
    def execute(self):
        """Esegue il workflow"""
        # Crea la finestra di dialogo
        dialog = tk.Toplevel(self.parent)
        dialog.title("Backup Logico Dati")
        dialog.geometry("500x300")
        dialog.grab_set()
        
        # Intestazione
        header = HeaderFrame(dialog, "Backup Logico Dati", 
                           "Esegue un backup logico dei dati del database")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Form
        form_frame = ttk.Frame(dialog, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(form_frame, text="Directory di destinazione:").grid(row=0, column=0, sticky=tk.W, pady=5)
        directory_entry = ttk.Entry(form_frame, width=40)
        directory_entry.grid(row=0, column=1, pady=5, sticky=tk.W)
        directory_entry.insert(0, "/tmp")
        
        def select_directory():
            directory = tk.filedialog.askdirectory()
            if directory:
                directory_entry.delete(0, tk.END)
                directory_entry.insert(0, directory)
        
        ttk.Button(form_frame, text="Sfoglia", command=select_directory).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Prefisso file:").grid(row=1, column=0, sticky=tk.W, pady=5)
        prefisso_entry = ttk.Entry(form_frame, width=40)
        prefisso_entry.grid(row=1, column=1, pady=5, sticky=tk.W)
        prefisso_entry.insert(0, "catasto_backup")
        
        # Pulsanti
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def execute_backup():
            directory = directory_entry.get()
            prefisso = prefisso_entry.get()
            
            if not directory:
                messagebox.showerror("Errore", "La directory di destinazione è obbligatoria")
                return
            
            if not prefisso:
                messagebox.showerror("Errore", "Il prefisso del file è obbligatorio")
                return
            
            try:
                success, message = self.db_manager.backup_logico_dati(directory, prefisso)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    if self.log_callback:
                        self.log_callback(f"Backup logico dati pianificato in {directory}")
                    dialog.destroy()
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
        
        ttk.Button(buttons_frame, text="Esegui Backup", command=execute_backup).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

class SincronizzaArchivioWorkflow:
    """Workflow per sincronizzare una partita con l'Archivio di Stato"""
    
    def __init__(self, parent, db_manager: CatastoDBManager, log_callback: Callable = None):
        self.parent = parent
        self.db_manager = db_manager
        self.log_callback = log_callback
    
    def execute(self):
        """Esegue il workflow"""
        # Crea la finestra di dialogo
        dialog = tk.Toplevel(self.parent)
        dialog.title("Sincronizzazione con Archivio di Stato")
        dialog.geometry("500x300")
        dialog.grab_set()
        
        # Intestazione
        header = HeaderFrame(dialog, "Sincronizzazione con Archivio di Stato", 
                           "Sincronizza una partita con l'Archivio di Stato")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Form
        form_frame = ttk.Frame(dialog, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(form_frame, text="ID Partita:").grid(row=0, column=0, sticky=tk.W, pady=5)
        partita_id_entry = ttk.Entry(form_frame, width=30)
        partita_id_entry.grid(row=0, column=1, pady=5, sticky=tk.W)
        
        ttk.Label(form_frame, text="Riferimento archivio:").grid(row=1, column=0, sticky=tk.W, pady=5)
        riferimento_entry = ttk.Entry(form_frame, width=30)
        riferimento_entry.grid(row=1, column=1, pady=5, sticky=tk.W)
        
        ttk.Label(form_frame, text="Data sincronizzazione:").grid(row=2, column=0, sticky=tk.W, pady=5)
        data_entry = ttk.Entry(form_frame, width=30)
        data_entry.grid(row=2, column=1, pady=5, sticky=tk.W)
        data_entry.insert(0, date.today().strftime("%Y-%m-%d"))
        
        # Pulsanti
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def execute_sync():
            partita_id = partita_id_entry.get()
            riferimento = riferimento_entry.get()
            data = data_entry.get()
            
            if not partita_id:
                messagebox.showerror("Errore", "L'ID della partita è obbligatorio")
                return
            
            if not riferimento:
                messagebox.showerror("Errore", "Il riferimento all'archivio è obbligatorio")
                return
            
            try:
                partita_id = int(partita_id)
            except ValueError:
                messagebox.showerror("Errore", "L'ID della partita deve essere un numero intero")
                return
            
            try:
                data_sync = parse_date(data) if data else None
                
                success, message = self.db_manager.sincronizza_con_archivio_stato(
                    partita_id, riferimento, data_sync
                )
                
                if success:
                    messagebox.showinfo("Successo", message)
                    if self.log_callback:
                        self.log_callback(f"Sincronizzata partita {partita_id} con l'Archivio di Stato")
                    dialog.destroy()
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
        
        ttk.Button(buttons_frame, text="Sincronizza", command=execute_sync).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

class VerificaIntegritaWorkflow:
    """Workflow per verificare l'integrità del database"""
    
    def __init__(self, parent, db_manager: CatastoDBManager, log_callback: Callable = None):
        self.parent = parent
        self.db_manager = db_manager
        self.log_callback = log_callback
    
    def execute(self):
        """Esegue il workflow"""
        try:
            # Mostra un messaggio di attesa
            self.parent.config(cursor="wait")
            
            # Esegue la verifica
            success, message = self.db_manager.verifica_integrita_database()
            
            # Ripristina il cursore normale
            self.parent.config(cursor="")
            
            if success:
                if "Problemi trovati: true" in message:
                    result = messagebox.askyesno(
                        "Verifica Integrità", 
                        f"{message}\n\nSono stati trovati problemi di integrità. Vuoi eseguire la riparazione automatica?"
                    )
                    
                    if result:
                        self.ripara_database()
                else:
                    messagebox.showinfo("Verifica Integrità", message)
                    
                if self.log_callback:
                    self.log_callback("Verifica integrità database completata")
            else:
                messagebox.showerror("Errore", message)
        
        except Exception as e:
            self.parent.config(cursor="")
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
    
    def ripara_database(self):
        """Ripara il database"""
        try:
            # Mostra un messaggio di attesa
            self.parent.config(cursor="wait")
            
            # Esegue la riparazione
            success, message = self.db_manager.ripara_problemi_database(True)
            
            # Ripristina il cursore normale
            self.parent.config(cursor="")
            
            if success:
                messagebox.showinfo("Riparazione Database", message)
                if self.log_callback:
                    self.log_callback("Riparazione database completata")
            else:
                messagebox.showerror("Errore", message)
        
        except Exception as e:
            self.parent.config(cursor="")
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
