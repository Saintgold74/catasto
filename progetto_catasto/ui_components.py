#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Componenti UI per l'applicazione Catasto Storico
================================================
Questo modulo contiene componenti dell'interfaccia utente riutilizzabili.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
from typing import Callable, Dict, List, Any, Optional, Tuple
import json
from datetime import date, datetime

from config import TIPI_VARIAZIONE, TIPI_CONTRATTO, TIPI_LOCALITA, TIPI_PARTITA, parse_date

class BaseFrame(ttk.Frame):
    """Classe base per i frame dell'applicazione"""
    
    def __init__(self, parent, db_manager, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.db_manager = db_manager
        
    def setup_ui(self):
        """Configura l'interfaccia utente del frame"""
        pass
    
    def refresh_data(self):
        """Aggiorna i dati visualizzati nel frame"""
        pass

class HeaderFrame(ttk.Frame):
    """Frame per intestazioni"""
    
    def __init__(self, parent, title, description=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.title = title
        self.description = description
        self.setup_ui()
        
    def setup_ui(self):
        """Configura l'interfaccia utente del frame"""
        # Titolo
        title_label = ttk.Label(self, text=self.title, font=("Helvetica", 14, "bold"))
        title_label.pack(pady=5)
        
        # Descrizione (opzionale)
        if self.description:
            description_label = ttk.Label(self, text=self.description, wraplength=600)
            description_label.pack(pady=5)
        
        # Separatore
        separator = ttk.Separator(self, orient="horizontal")
        separator.pack(fill="x", pady=5)

class SearchFrame(ttk.LabelFrame):
    """Frame per campi di ricerca"""
    
    def __init__(self, parent, search_callback, fields, title="Ricerca", **kwargs):
        super().__init__(parent, text=title, **kwargs)
        self.search_callback = search_callback
        self.fields = fields  # Lista di dizionari con chiavi: name, label, type, values (per combobox)
        self.entries = {}  # Per tenere traccia dei widget di input
        self.setup_ui()
        
    def setup_ui(self):
        """Configura l'interfaccia utente del frame"""
        # Griglia per i campi di ricerca
        for i, field in enumerate(self.fields):
            row, col = divmod(i, 2)
            
            # Etichetta
            ttk.Label(self, text=field['label']).grid(
                row=row, column=col*2, padx=5, pady=5, sticky=tk.W)
            
            # Widget di input in base al tipo
            if field['type'] == 'entry':
                entry = ttk.Entry(self, width=20)
                entry.grid(row=row, column=col*2+1, padx=5, pady=5, sticky=tk.W)
                self.entries[field['name']] = entry
            
            elif field['type'] == 'combobox':
                var = tk.StringVar()
                combobox = ttk.Combobox(self, textvariable=var, width=18, values=field.get('values', []))
                combobox.grid(row=row, column=col*2+1, padx=5, pady=5, sticky=tk.W)
                self.entries[field['name']] = combobox
            
            elif field['type'] == 'date':
                entry = ttk.Entry(self, width=20)
                entry.grid(row=row, column=col*2+1, padx=5, pady=5, sticky=tk.W)
                if field.get('default') == 'today':
                    entry.insert(0, date.today().strftime("%Y-%m-%d"))
                self.entries[field['name']] = entry
        
        # Pulsante di ricerca
        max_row = len(self.fields) // 2 + (1 if len(self.fields) % 2 else 0)
        ttk.Button(self, text="Cerca", command=self.perform_search).grid(
            row=max_row, column=0, columnspan=4, pady=10)
    
    def perform_search(self):
        """Esegue la ricerca con i valori inseriti"""
        search_params = {}
        
        for field in self.fields:
            entry = self.entries[field['name']]
            
            if field['type'] == 'combobox':
                value = entry.get() if entry.get() != "" else None
            elif field['type'] == 'date':
                value = parse_date(entry.get()) if entry.get() else None
            elif field['type'] == 'entry' and field.get('numeric', False):
                try:
                    value = int(entry.get()) if entry.get() else None
                except ValueError:
                    messagebox.showerror("Errore", f"Il campo {field['label']} deve essere numerico")
                    return
            else:
                value = entry.get() if entry.get() else None
            
            search_params[field['name']] = value
        
        # Esegue il callback di ricerca con i parametri
        self.search_callback(**search_params)
    
    def clear_fields(self):
        """Pulisce tutti i campi di ricerca"""
        for field in self.fields:
            entry = self.entries[field['name']]
            if hasattr(entry, 'delete'):
                entry.delete(0, tk.END)
                if field['type'] == 'date' and field.get('default') == 'today':
                    entry.insert(0, date.today().strftime("%Y-%m-%d"))
            elif hasattr(entry, 'set'):
                entry.set('')

class ResultsTreeview(ttk.Frame):
    """Frame con un treeview per visualizzare risultati"""
    
    def __init__(self, parent, columns, **kwargs):
        """
        Inizializza il frame con un treeview.
        
        Args:
            parent: Widget genitore
            columns: Lista di dizionari con chiavi: id, header, width
        """
        super().__init__(parent, **kwargs)
        self.columns = columns
        self.setup_ui()
    
    def setup_ui(self):
        """Configura l'interfaccia utente del frame"""
        # Crea il treeview
        column_ids = [col['id'] for col in self.columns]
        self.tree = ttk.Treeview(self, columns=column_ids, show="headings", selectmode="browse")
        
        # Configura le colonne
        for col in self.columns:
            self.tree.heading(col['id'], text=col['header'])
            self.tree.column(col['id'], width=col.get('width', 100))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Layout
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Memorizza le funzioni di menu contestuale
        self.context_menu_callbacks = {}
        
        # Variabile per memorizzare l'ID dell'elemento selezionato
        self.selected_id = None
    
    def populate(self, data):
        """
        Popola il treeview con i dati forniti.
        
        Args:
            data: Lista di dizionari con chiavi corrispondenti alle colonne
        """
        # Pulisce il treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Inserisce i nuovi dati
        for row in data:
            values = [row.get(col['id'], "") for col in self.columns]
            self.tree.insert("", tk.END, values=values, tags=(str(row.get('id', "")),))
    
    def get_selected_item(self):
        """
        Restituisce l'ID dell'elemento selezionato nel treeview.
        
        Returns:
            Any: ID dell'elemento o None se nessun elemento è selezionato
        """
        selected_items = self.tree.selection()
        if not selected_items:
            return None
        
        item = selected_items[0]
        values = self.tree.item(item, "values")
        
        # L'ID è il primo valore
        try:
            return int(values[0])
        except (IndexError, ValueError):
            return None
    
    def setup_context_menu(self, callbacks):
        """
        Configura il menu contestuale per il treeview.
        
        Args:
            callbacks: Dizionario con chiavi (etichette del menu) e valori (funzioni di callback)
        """
        self.context_menu_callbacks = callbacks
        
        # Crea il menu contestuale
        self.context_menu = tk.Menu(self, tearoff=0)
        for label, callback in callbacks.items():
            self.context_menu.add_command(label=label, command=callback)
        
        # Binding per il click destro
        self.tree.bind("<Button-3>", self.show_context_menu)
    
    def show_context_menu(self, event):
        """Mostra il menu contestuale"""
        # Seleziona l'elemento sotto il cursore
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

class FormDialog(tk.Toplevel):
    """Finestra di dialogo per form generici"""
    
    def __init__(self, parent, title, fields, callback, width=500, height=400, **kwargs):
        """
        Inizializza la finestra di dialogo con un form.
        
        Args:
            parent: Widget genitore
            title: Titolo della finestra
            fields: Lista di dizionari con chiavi: name, label, type, values (per combobox), default
            callback: Funzione da chiamare quando il form viene inviato
            width, height: Dimensioni della finestra
        """
        super().__init__(parent, **kwargs)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.grab_set()  # Blocca l'input sulle altre finestre
        
        self.fields = fields
        self.callback = callback
        self.entries = {}  # Per tenere traccia dei widget di input
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura l'interfaccia utente della finestra"""
        # Frame principale con scrolling
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas per scrolling
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        
        form_frame = ttk.Frame(canvas)
        form_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=form_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Griglia per i campi del form
        for i, field in enumerate(self.fields):
            # Etichetta
            ttk.Label(form_frame, text=field['label']).grid(
                row=i, column=0, padx=5, pady=5, sticky=tk.W)
            
            # Widget di input in base al tipo
            if field['type'] == 'entry':
                entry = ttk.Entry(form_frame, width=30)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky=tk.W)
                if 'default' in field:
                    entry.insert(0, str(field['default']))
                self.entries[field['name']] = entry
            
            elif field['type'] == 'combobox':
                var = tk.StringVar()
                combobox = ttk.Combobox(form_frame, textvariable=var, width=28, values=field.get('values', []))
                combobox.grid(row=i, column=1, padx=5, pady=5, sticky=tk.W)
                if 'default' in field:
                    combobox.set(field['default'])
                self.entries[field['name']] = combobox
            
            elif field['type'] == 'text':
                text = tk.Text(form_frame, width=30, height=5)
                text.grid(row=i, column=1, padx=5, pady=5, sticky=tk.W)
                if 'default' in field:
                    text.insert("1.0", field['default'])
                self.entries[field['name']] = text
            
            elif field['type'] == 'date':
                entry = ttk.Entry(form_frame, width=30)
                entry.grid(row=i, column=1, padx=5, pady=5, sticky=tk.W)
                if field.get('default') == 'today':
                    entry.insert(0, date.today().strftime("%Y-%m-%d"))
                elif 'default' in field:
                    entry.insert(0, field['default'])
                self.entries[field['name']] = entry
            
            elif field['type'] == 'checkbox':
                var = tk.BooleanVar(value=field.get('default', False))
                checkbox = ttk.Checkbutton(form_frame, variable=var)
                checkbox.grid(row=i, column=1, padx=5, pady=5, sticky=tk.W)
                self.entries[field['name']] = var
        
        # Pulsanti
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.grid(row=len(self.fields), column=0, columnspan=2, pady=10)
        
        ttk.Button(buttons_frame, text="Salva", command=self.submit_form).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def submit_form(self):
        """Invia il form chiamando il callback con i valori inseriti"""
        form_data = {}
        
        for field in self.fields:
            entry = self.entries[field['name']]
            
            if field['type'] == 'combobox':
                value = entry.get() if entry.get() != "" else None
            elif field['type'] == 'text':
                value = entry.get("1.0", tk.END).strip()
            elif field['type'] == 'checkbox':
                value = entry.get()
            elif field['type'] == 'date':
                value = parse_date(entry.get()) if entry.get() else None
            elif field['type'] == 'entry' and field.get('numeric', False):
                try:
                    value = int(entry.get()) if entry.get() else None
                except ValueError:
                    messagebox.showerror("Errore", f"Il campo {field['label']} deve essere numerico")
                    return
            else:
                value = entry.get() if entry.get() else None
            
            form_data[field['name']] = value
        
        # Verifica i campi obbligatori
        for field in self.fields:
            if field.get('required', False) and form_data[field['name']] is None:
                messagebox.showerror("Errore", f"Il campo {field['label']} è obbligatorio")
                return
                
    def validate_form_data(self):
            """Valida i dati del form."""
            form_data = {}
            
            for field in self.fields:
                entry = self.entries[field['name']]
                
                if field['type'] == 'combobox':
                    value = entry.get() if entry.get() != "" else None
                elif field['type'] == 'text':
                    value = entry.get("1.0", tk.END).strip()
                elif field['type'] == 'checkbox':
                    value = entry.get()
                elif field['type'] == 'date':
                    value = entry.get()
                    # Validazione data
                    if value and field.get('required', False):
                        try:
                            parse_date(value)
                        except ValueError:
                            messagebox.showerror("Errore", f"Il campo {field['label']} non è una data valida (formato richiesto: YYYY-MM-DD)")
                            return None
                elif field['type'] == 'entry' and field.get('numeric', False):
                    try:
                        value = int(entry.get()) if entry.get() else None
                    except ValueError:
                        messagebox.showerror("Errore", f"Il campo {field['label']} deve essere numerico")
                        return None
                else:
                    value = entry.get() if entry.get() else None
        
            # Verifica campi obbligatori
            if field.get('required', False) and (value is None or value == ""):
                messagebox.showerror("Errore", f"Il campo {field['label']} è obbligatorio")
                return None
        
            form_data[field['name']] = value
    
    return form_data
        
        # Esegue il callback con i dati del form
        success = self.callback(form_data)
        if success:
            self.destroy()

class EntitySelectionDialog(tk.Toplevel):
    """Finestra di dialogo per la selezione di entità"""
    
    def __init__(self, parent, title, data, columns, callback, width=500, height=400, **kwargs):
        """
        Inizializza la finestra di dialogo per la selezione di entità.
        
        Args:
            parent: Widget genitore
            title: Titolo della finestra
            data: Lista di dizionari con i dati da visualizzare
            columns: Lista di dizionari con chiavi: id, header, width
            callback: Funzione da chiamare quando un'entità viene selezionata
            width, height: Dimensioni della finestra
        """
        super().__init__(parent, **kwargs)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.grab_set()  # Blocca l'input sulle altre finestre
        
        self.data = data
        self.columns = columns
        self.callback = callback
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura l'interfaccia utente della finestra"""
        # Etichetta
        ttk.Label(self, text="Seleziona uno o più elementi:").pack(pady=10)
        
        # Treeview per visualizzare i dati
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        column_ids = [col['id'] for col in self.columns]
        self.tree = ttk.Treeview(tree_frame, columns=column_ids, show="headings", selectmode="extended")
        
        # Configura le colonne
        for col in self.columns:
            self.tree.heading(col['id'], text=col['header'])
            self.tree.column(col['id'], width=col.get('width', 100))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Popola il treeview
        for row in self.data:
            values = [row.get(col['id'], "") for col in self.columns]
            self.tree.insert("", tk.END, values=values, tags=(str(row.get('id', "")),))
        
        # Pulsanti
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Seleziona", command=self.select_items).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def select_items(self):
        """Seleziona gli elementi e chiama il callback"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Avviso", "Nessun elemento selezionato")
            return
        
        selected_data = []
        for item in selected_items:
            values = self.tree.item(item, "values")
            # Trova il dizionario originale
            item_id = values[0]  # Assume che l'ID sia il primo valore
            for row in self.data:
                if str(row.get('id', "")) == str(item_id):
                    selected_data.append(row)
                    break
        
        self.callback(selected_data)
        self.destroy()

class StatusBar(ttk.Frame):
    """Barra di stato per l'applicazione"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.setup_ui()
    
    def setup_ui(self):
        """Configura l'interfaccia utente della barra di stato"""
        self.status_label = ttk.Label(self, text="Pronto", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X)
    
    def set_status(self, message):
        """Imposta il messaggio nella barra di stato"""
        self.status_label.config(text=message)

class LogViewer(ttk.Frame):
    """Visualizzatore di log per l'applicazione"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.setup_ui()
    
    def setup_ui(self):
        """Configura l'interfaccia utente del visualizzatore di log"""
        # Etichetta
        ttk.Label(self, text="Log operazioni", font=("Helvetica", 10, "bold")).pack(pady=5)
        
        # Area di testo per i log
        self.log_text = scrolledtext.ScrolledText(self, width=40, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(state=tk.DISABLED)
    
    def add_log(self, message):
        """Aggiunge un messaggio al log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def clear_log(self):
        """Pulisce il log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

class ReportViewer(tk.Toplevel):
    """Finestra per visualizzare i report testuali"""
    
    def __init__(self, parent, title, content, width=800, height=600, **kwargs):
        """
        Inizializza la finestra per visualizzare un report.
        
        Args:
            parent: Widget genitore
            title: Titolo della finestra
            content: Contenuto del report
            width, height: Dimensioni della finestra
        """
        super().__init__(parent, **kwargs)
        self.title(title)
        self.geometry(f"{width}x{height}")
        
        self.content = content
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura l'interfaccia utente della finestra"""
        # Etichetta
        ttk.Label(self, text=self.title(), font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # Area di testo per il report
        self.text = scrolledtext.ScrolledText(self, width=80, height=30, font=("Courier", 10))
        self.text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.text.insert("1.0", self.content)
        self.text.config(state=tk.DISABLED)
        
        # Pulsanti
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Salva come Testo", command=self.save_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Salva come PDF", command=self.save_report_as_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Chiudi", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def save_report(self):
        """Salva il report su file"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Salva report"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.content)
                messagebox.showinfo("Successo", f"Report salvato in {file_path}")
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile salvare il file: {e}")
    
    def save_report_as_pdf(self):
        """Salva il report come PDF."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                title="Salva report come PDF"
            )
            
            if file_path:
                try:
                    doc = SimpleDocTemplate(file_path, pagesize=A4)
                    styles = getSampleStyleSheet()
                    story = []
                    
                    # Dividi il testo in paragrafi
                    for line in self.content.split('\n'):
                        if line.strip():
                            if line.startswith('==='):
                                # Titolo sezione
                                story.append(Paragraph(line, styles['Heading2']))
                            else:
                                story.append(Paragraph(line, styles['Normal']))
                            story.append(Spacer(1, 6))
                    
                    doc.build(story)
                    messagebox.showinfo("Successo", f"Report salvato come PDF in {file_path}")
                except Exception as e:
                    messagebox.showerror("Errore", f"Impossibile salvare il PDF: {e}")
        except ImportError:
            messagebox.showerror("Errore", "Per salvare in formato PDF, installa reportlab con: pip install reportlab")

class DynamicListFrame(ttk.LabelFrame):
    """Frame per gestire una lista dinamica di elementi"""
    
    def __init__(self, parent, title, columns, add_callback, remove_callback, **kwargs):
        """
        Inizializza il frame per la gestione di una lista dinamica.
        
        Args:
            parent: Widget genitore
            title: Titolo del frame
            columns: Lista di dizionari con chiavi: id, header, width
            add_callback: Funzione da chiamare per aggiungere un elemento
            remove_callback: Funzione da chiamare per rimuovere elementi
        """
        super().__init__(parent, text=title, **kwargs)
        self.columns = columns
        self.add_callback = add_callback
        self.remove_callback = remove_callback
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configura l'interfaccia utente del frame"""
        # Treeview per visualizzare i dati
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        column_ids = [col['id'] for col in self.columns]
        self.tree = ttk.Treeview(tree_frame, columns=column_ids, show="headings", selectmode="extended", height=8)
        
        # Configura le colonne
        for col in self.columns:
            self.tree.heading(col['id'], text=col['header'])
            self.tree.column(col['id'], width=col.get('width', 100))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Pulsanti
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(pady=5)
        
        ttk.Button(buttons_frame, text="Aggiungi", command=self.add_callback).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Rimuovi selezionati", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
    
    def add_item(self, data, tag=None):
        """
        Aggiunge un elemento alla lista.
        
        Args:
            data: Dizionario con i dati dell'elemento
            tag: Tag opzionale da associare all'elemento
        """
        values = [data.get(col['id'], "") for col in self.columns]
        self.tree.insert("", tk.END, values=values, tags=(tag,) if tag else ())
    
    def get_selected_items(self):
        """
        Restituisce gli elementi selezionati nella lista.
        
        Returns:
            List: Lista degli elementi selezionati
        """
        return self.tree.selection()
    
    def remove_selected(self):
        """Rimuove gli elementi selezionati dalla lista"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Avviso", "Nessun elemento selezionato")
            return
        
        # Chiama il callback per la rimozione
        self.remove_callback(selected_items)
        
        # Rimuove gli elementi dal treeview
        for item in selected_items:
            self.tree.delete(item)
    
    def clear(self):
        """Pulisce la lista"""
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def get_all_items(self):
        """
        Restituisce tutti gli elementi nella lista.
        
        Returns:
            List: Lista di tuple con i valori di ogni elemento
        """
        items = []
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            tags = self.tree.item(item, "tags")
            items.append((values, tags))
        return items
