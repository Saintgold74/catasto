#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Applicazione Catasto Storico
============================
Punto di ingresso principale dell'applicazione per la gestione del catasto storico.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import logging
from datetime import date

# Importa i moduli del progetto
from config import (
    setup_logging, load_config, save_config, APP_NAME, APP_VERSION, 
    APP_DESCRIPTION, DEFAULT_DB_CONFIG
)
from db_manager import CatastoDBManager
from ui_components import (
    HeaderFrame, SearchFrame, ResultsTreeview, StatusBar, LogViewer,
    FormDialog, EntitySelectionDialog, ReportViewer, BaseFrame
)
from workflows import (
    NuovaConsultazioneWorkflow, NuovoPossessoreWorkflow, NuovaPartitaWorkflow,
    GeneraCertificatoWorkflow, GeneraReportGenealogico, GeneraReportPossessore,
    RegistraNuovaProprietaWorkflow, RegistraPassaggioProprietaWorkflow,
    BackupLogicoDatiWorkflow, SincronizzaArchivioWorkflow, VerificaIntegritaWorkflow
)

# Configura il logging
logger = setup_logging()

class ConsultazioniFrame(BaseFrame):
    """Frame per la gestione delle consultazioni"""
    
    def __init__(self, parent, db_manager):
        super().__init__(parent, db_manager)
        self.setup_ui()
    
    def setup_ui(self):
        # Intestazione
        header = HeaderFrame(self, "Gestione Consultazioni", 
                         "Registra e cerca consultazioni dell'archivio")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Frame dei pulsanti
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(buttons_frame, text="Nuova consultazione", 
                 command=self.nuova_consultazione).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Aggiorna", 
                 command=self.refresh_data).pack(side=tk.LEFT, padx=5)
        
        # Frame di ricerca
        search_fields = [
            {'name': 'data_inizio', 'label': 'Data inizio:', 'type': 'date'},
            {'name': 'data_fine', 'label': 'Data fine:', 'type': 'date', 'default': 'today'},
            {'name': 'richiedente', 'label': 'Richiedente:', 'type': 'entry'},
            {'name': 'funzionario', 'label': 'Funzionario:', 'type': 'entry'}
        ]
        
        self.search_frame = SearchFrame(self, self.search_consultazioni, search_fields, 
                                     title="Ricerca Consultazioni")
        self.search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Frame dei risultati
        results_frame = ttk.LabelFrame(self, text="Risultati")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = [
            {'id': 'id', 'header': 'ID', 'width': 50},
            {'id': 'data', 'header': 'Data', 'width': 100},
            {'id': 'richiedente', 'header': 'Richiedente', 'width': 150},
            {'id': 'documento_identita', 'header': 'Documento', 'width': 100},
            {'id': 'motivazione', 'header': 'Motivazione', 'width': 200},
            {'id': 'funzionario_autorizzante', 'header': 'Funzionario', 'width': 150}
        ]
        
        self.results_tree = ResultsTreeview(results_frame, columns)
        self.results_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configura il menu contestuale
        self.results_tree.setup_context_menu({
            "Modifica": self.edit_consultazione,
            "Elimina": self.delete_consultazione
        })
    
    def refresh_data(self):
        """Aggiorna i dati visualizzati"""
        self.search_consultazioni()
    
    def search_consultazioni(self, data_inizio=None, data_fine=None, richiedente=None, funzionario=None):
        """Cerca consultazioni in base ai criteri specificati"""
        try:
            results = self.db_manager.cerca_consultazioni(
                data_inizio, data_fine, richiedente, funzionario
            )
            self.results_tree.populate(results)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la ricerca: {str(e)}")
    
    def nuova_consultazione(self):
        """Apre il workflow per registrare una nuova consultazione"""
        workflow = NuovaConsultazioneWorkflow(
            self, self.db_manager, on_complete=self.refresh_data
        )
        workflow.execute()
    
    def edit_consultazione(self):
        """Modifica una consultazione esistente"""
        consultazione_id = self.results_tree.get_selected_item()
        if not consultazione_id:
            messagebox.showwarning("Avviso", "Nessuna consultazione selezionata")
            return
        
        # Trova la consultazione nei risultati
        for item in self.results_tree.tree.get_children():
            values = self.results_tree.tree.item(item, "values")
            if int(values[0]) == consultazione_id:
                # Apre un form per modificare i dati
                fields = [
                    {'name': 'data', 'label': 'Data consultazione:', 'type': 'date', 'default': values[1]},
                    {'name': 'richiedente', 'label': 'Richiedente:', 'type': 'entry', 'default': values[2]},
                    {'name': 'documento_identita', 'label': 'Documento d\'identità:', 'type': 'entry', 'default': values[3]},
                    {'name': 'motivazione', 'label': 'Motivazione:', 'type': 'text', 'default': values[4]},
                    {'name': 'materiale_consultato', 'label': 'Materiale consultato:', 'type': 'text'},
                    {'name': 'funzionario_autorizzante', 'label': 'Funzionario autorizzante:', 'type': 'entry', 'default': values[5]}
                ]
                
                form_dialog = FormDialog(
                    self, 
                    "Modifica Consultazione", 
                    fields, 
                    lambda form_data: self.update_consultazione(consultazione_id, form_data),
                    width=600,
                    height=500
                )
                break
    
    def update_consultazione(self, consultazione_id, form_data):
        """Aggiorna una consultazione nel database"""
        try:
            success = self.db_manager.aggiorna_consultazione(
                consultazione_id,
                form_data['data'],
                form_data['richiedente'],
                form_data['documento_identita'],
                form_data['motivazione'],
                form_data['materiale_consultato'],
                form_data['funzionario_autorizzante']
            )
            
            if success:
                messagebox.showinfo("Successo", "Consultazione aggiornata con successo")
                self.refresh_data()
                return True
            else:
                messagebox.showerror("Errore", "Impossibile aggiornare la consultazione")
                return False
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
            return False
    
    def delete_consultazione(self):
        """Elimina una consultazione"""
        consultazione_id = self.results_tree.get_selected_item()
        if not consultazione_id:
            messagebox.showwarning("Avviso", "Nessuna consultazione selezionata")
            return
        
        if messagebox.askyesno("Conferma", "Sei sicuro di voler eliminare questa consultazione?"):
            try:
                success = self.db_manager.elimina_consultazione(consultazione_id)
                
                if success:
                    messagebox.showinfo("Successo", "Consultazione eliminata con successo")
                    self.refresh_data()
                else:
                    messagebox.showerror("Errore", "Impossibile eliminare la consultazione")
            
            except Exception as e:
                messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")

class PossessoriFrame(BaseFrame):
    """Frame per la gestione dei possessori"""
    
    def __init__(self, parent, db_manager):
        super().__init__(parent, db_manager)
        self.setup_ui()
    
    def setup_ui(self):
        # Intestazione
        header = HeaderFrame(self, "Gestione Possessori", 
                         "Gestisci i possessori di immobili")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Frame dei pulsanti
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(buttons_frame, text="Nuovo possessore", 
                 command=self.nuovo_possessore).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Genera report", 
                 command=self.genera_report).pack(side=tk.LEFT, padx=5)
        
        # Frame di ricerca
        search_fields = [
            {'name': 'query', 'label': 'Nome/Cognome:', 'type': 'entry'}
        ]
        
        self.search_frame = SearchFrame(self, self.search_possessori, search_fields, 
                                     title="Ricerca Possessori")
        self.search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Frame dei risultati
        results_frame = ttk.LabelFrame(self, text="Risultati")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = [
            {'id': 'id', 'header': 'ID', 'width': 50},
            {'id': 'nome_completo', 'header': 'Nome Completo', 'width': 200},
            {'id': 'comune_nome', 'header': 'Comune', 'width': 150},
            {'id': 'num_partite', 'header': 'Num. Partite', 'width': 100}
        ]
        
        self.results_tree = ResultsTreeview(results_frame, columns)
        self.results_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configura il menu contestuale
        self.results_tree.setup_context_menu({
            "Visualizza immobili": self.view_immobili,
            "Genera report": self.genera_report_selezione
        })
    
    def refresh_data(self):
        """Aggiorna i dati visualizzati"""
        self.search_frame.perform_search()
    
    def search_possessori(self, query):
        """Cerca possessori in base ai criteri specificati"""
        try:
            success, results = self.db_manager.possessore_manager.cerca_possessori(query)
            
            if success:
                self.results_tree.populate(results)
            else:
                messagebox.showerror("Errore", results)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la ricerca: {str(e)}")
    
    def nuovo_possessore(self):
        """Apre il workflow per registrare un nuovo possessore"""
        workflow = NuovoPossessoreWorkflow(
            self, self.db_manager, on_complete=self.refresh_data
        )
        workflow.execute()
    
    def view_immobili(self):
        """Visualizza gli immobili di un possessore"""
        possessore_id = self.results_tree.get_selected_item()
        if not possessore_id:
            messagebox.showwarning("Avviso", "Nessun possessore selezionato")
            return
        
        try:
            success, results = self.db_manager.possessore_manager.get_immobili_possessore(possessore_id)
            
            if success:
                # Trova il nome del possessore
                possessore_nome = ""
                for item in self.results_tree.tree.get_children():
                    values = self.results_tree.tree.item(item, "values")
                    if int(values[0]) == possessore_id:
                        possessore_nome = values[1]
                        break
                
                # Mostra gli immobili in una nuova finestra
                dialog = tk.Toplevel(self)
                dialog.title(f"Immobili di {possessore_nome}")
                dialog.geometry("800x400")
                
                ttk.Label(dialog, text=f"Immobili posseduti da {possessore_nome}", font=("Helvetica", 12, "bold")).pack(pady=10)
                
                columns = [
                    {'id': 'immobile_id', 'header': 'ID', 'width': 50},
                    {'id': 'natura', 'header': 'Natura', 'width': 150},
                    {'id': 'localita_nome', 'header': 'Località', 'width': 150},
                    {'id': 'comune', 'header': 'Comune', 'width': 100},
                    {'id': 'partita_numero', 'header': 'Partita', 'width': 80},
                    {'id': 'tipo_partita', 'header': 'Tipo', 'width': 100}
                ]
                
                tree_view = ResultsTreeview(dialog, columns)
                tree_view.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                tree_view.populate(results)
                
                ttk.Button(dialog, text="Chiudi", command=dialog.destroy).pack(pady=10)
            else:
                messagebox.showerror("Errore", results)
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
    
    def genera_report(self):
        """Genera un report per un possessore"""
        workflow = GeneraReportPossessore(self, self.db_manager)
        workflow.execute()
    
    def genera_report_selezione(self):
        """Genera un report per il possessore selezionato"""
        possessore_id = self.results_tree.get_selected_item()
        if not possessore_id:
            messagebox.showwarning("Avviso", "Nessun possessore selezionato")
            return
        
        try:
            report = self.db_manager.genera_report_possessore(possessore_id)
            
            if report:
                # Trova il nome del possessore
                possessore_nome = ""
                for item in self.results_tree.tree.get_children():
                    values = self.results_tree.tree.item(item, "values")
                    if int(values[0]) == possessore_id:
                        possessore_nome = values[1]
                        break
                
                # Mostra il report
                report_viewer = ReportViewer(
                    self,
                    f"Report Possessore - {possessore_nome}",
                    report
                )
            else:
                messagebox.showerror("Errore", "Impossibile generare il report")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")

class PartiteFrame(BaseFrame):
    """Frame per la gestione delle partite"""
    
    def __init__(self, parent, db_manager):
        super().__init__(parent, db_manager)
        self.setup_ui()
    
    def setup_ui(self):
        # Intestazione
        header = HeaderFrame(self, "Gestione Partite", 
                         "Gestisci le partite catastali")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Frame dei pulsanti
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(buttons_frame, text="Nuova partita", 
                 command=self.nuova_partita).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Genera certificato", 
                 command=self.genera_certificato).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Genera report genealogico", 
                 command=self.genera_report_genealogico).pack(side=tk.LEFT, padx=5)
        
        # Frame di ricerca
        search_fields = [
            {'name': 'comune_nome', 'label': 'Comune:', 'type': 'entry'},
            {'name': 'numero_partita', 'label': 'Numero partita:', 'type': 'entry', 'numeric': True},
            {'name': 'possessore', 'label': 'Possessore:', 'type': 'entry'},
            {'name': 'immobile_natura', 'label': 'Natura immobile:', 'type': 'entry'}
        ]
        
        self.search_frame = SearchFrame(self, self.search_partite, search_fields, 
                                     title="Ricerca Partite")
        self.search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Frame dei risultati
        results_frame = ttk.LabelFrame(self, text="Risultati")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = [
            {'id': 'id', 'header': 'ID', 'width': 50},
            {'id': 'comune_nome', 'header': 'Comune', 'width': 150},
            {'id': 'numero_partita', 'header': 'Numero', 'width': 80},
            {'id': 'tipo', 'header': 'Tipo', 'width': 100},
            {'id': 'stato', 'header': 'Stato', 'width': 80},
            {'id': 'possessori', 'header': 'Possessori', 'width': 250}
        ]
        
        self.results_tree = ResultsTreeview(results_frame, columns)
        self.results_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configura il menu contestuale
        self.results_tree.setup_context_menu({
            "Visualizza dettagli": self.view_dettagli,
            "Genera certificato": self.genera_certificato_selezione,
            "Genera report genealogico": self.genera_report_genealogico_selezione
        })
    
    def refresh_data(self):
        """Aggiorna i dati visualizzati"""
        self.search_frame.perform_search()
    
    def search_partite(self, comune_nome=None, numero_partita=None, possessore=None, immobile_natura=None):
        """Cerca partite in base ai criteri specificati"""
        try:
            results = self.db_manager.search_partite(
                comune_nome, numero_partita, possessore, immobile_natura
            )
            self.results_tree.populate(results)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la ricerca: {str(e)}")
    
    def nuova_partita(self):
        """Apre il workflow per registrare una nuova partita"""
        workflow = NuovaPartitaWorkflow(
            self, self.db_manager, on_complete=self.refresh_data
        )
        workflow.execute()
    
    def view_dettagli(self):
        """Visualizza i dettagli di una partita"""
        partita_id = self.results_tree.get_selected_item()
        if not partita_id:
            messagebox.showwarning("Avviso", "Nessuna partita selezionata")
            return
        
        try:
            partita = self.db_manager.get_partita_details(partita_id)
            
            if partita:
                # Mostra i dettagli in una nuova finestra
                dialog = tk.Toplevel(self)
                dialog.title(f"Dettagli Partita {partita['numero_partita']} ({partita['comune_nome']})")
                dialog.geometry("800x600")
                
                notebook = ttk.Notebook(dialog)
                notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                # Tab info generali
                tab_info = ttk.Frame(notebook)
                notebook.add(tab_info, text="Informazioni")
                
                info_text = scrolledtext.ScrolledText(tab_info, width=80, height=20)
                info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                info_text.insert(tk.END, f"=== DATI PARTITA ===\n")
                info_text.insert(tk.END, f"ID: {partita['id']}\n")
                info_text.insert(tk.END, f"Comune: {partita['comune_nome']}\n")
                info_text.insert(tk.END, f"Numero partita: {partita['numero_partita']}\n")
                info_text.insert(tk.END, f"Tipo: {partita['tipo']}\n")
                info_text.insert(tk.END, f"Stato: {partita['stato']}\n")
                info_text.insert(tk.END, f"Data impianto: {partita['data_impianto']}\n")
                if partita['data_chiusura']:
                    info_text.insert(tk.END, f"Data chiusura: {partita['data_chiusura']}\n")
                
                # Tab possessori
                tab_possessori = ttk.Frame(notebook)
                notebook.add(tab_possessori, text="Possessori")
                
                columns_possessori = [
                    {'id': 'id', 'header': 'ID', 'width': 50},
                    {'id': 'nome_completo', 'header': 'Nome Completo', 'width': 200},
                    {'id': 'paternita', 'header': 'Paternità', 'width': 150},
                    {'id': 'titolo', 'header': 'Titolo', 'width': 100},
                    {'id': 'quota', 'header': 'Quota', 'width': 100}
                ]
                
                tree_possessori = ResultsTreeview(tab_possessori, columns_possessori)
                tree_possessori.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                tree_possessori.populate(partita['possessori'])
                
                # Tab immobili
                tab_immobili = ttk.Frame(notebook)
                notebook.add(tab_immobili, text="Immobili")
                
                columns_immobili = [
                    {'id': 'id', 'header': 'ID', 'width': 50},
                    {'id': 'natura', 'header': 'Natura', 'width': 150},
                    {'id': 'localita_nome', 'header': 'Località', 'width': 150},
                    {'id': 'classificazione', 'header': 'Classificazione', 'width': 150},
                    {'id': 'consistenza', 'header': 'Consistenza', 'width': 100}
                ]
                
                tree_immobili = ResultsTreeview(tab_immobili, columns_immobili)
                tree_immobili.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                tree_immobili.populate(partita['immobili'])
                
                # Tab variazioni
                if partita['variazioni']:
                    tab_variazioni = ttk.Frame(notebook)
                    notebook.add(tab_variazioni, text="Variazioni")
                    
                    columns_variazioni = [
                        {'id': 'id', 'header': 'ID', 'width': 50},
                        {'id': 'tipo', 'header': 'Tipo', 'width': 100},
                        {'id': 'data_variazione', 'header': 'Data', 'width': 100},
                        {'id': 'tipo_contratto', 'header': 'Contratto', 'width': 100},
                        {'id': 'notaio', 'header': 'Notaio', 'width': 150}
                    ]
                    
                    tree_variazioni = ResultsTreeview(tab_variazioni, columns_variazioni)
                    tree_variazioni.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                    tree_variazioni.populate(partita['variazioni'])
                
                ttk.Button(dialog, text="Chiudi", command=dialog.destroy).pack(pady=10)
            else:
                messagebox.showerror("Errore", "Partita non trovata")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
    
    def genera_certificato(self):
        """Genera un certificato di proprietà"""
        workflow = GeneraCertificatoWorkflow(self, self.db_manager)
        workflow.execute()
    
    def genera_certificato_selezione(self):
        """Genera un certificato per la partita selezionata"""
        partita_id = self.results_tree.get_selected_item()
        if not partita_id:
            messagebox.showwarning("Avviso", "Nessuna partita selezionata")
            return
        
        try:
            certificato = self.db_manager.genera_certificato_proprieta(partita_id)
            
            if certificato:
                # Mostra il certificato
                report_viewer = ReportViewer(
                    self,
                    f"Certificato di Proprietà - Partita {partita_id}",
                    certificato
                )
            else:
                messagebox.showerror("Errore", "Impossibile generare il certificato")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")
    
    def genera_report_genealogico(self):
        """Genera un report genealogico"""
        workflow = GeneraReportGenealogico(self, self.db_manager)
        workflow.execute()
    
    def genera_report_genealogico_selezione(self):
        """Genera un report genealogico per la partita selezionata"""
        partita_id = self.results_tree.get_selected_item()
        if not partita_id:
            messagebox.showwarning("Avviso", "Nessuna partita selezionata")
            return
        
        try:
            report = self.db_manager.genera_report_genealogico(partita_id)
            
            if report:
                # Mostra il report
                report_viewer = ReportViewer(
                    self,
                    f"Report Genealogico - Partita {partita_id}",
                    report
                )
            else:
                messagebox.showerror("Errore", "Impossibile generare il report")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Si è verificato un errore: {str(e)}")

class WorkflowFrame(BaseFrame):
    """Frame per la gestione dei workflow"""
    
    def __init__(self, parent, db_manager, app):
        super().__init__(parent, db_manager)
        self.app = app  # Riferimento all'applicazione principale
        self.setup_ui()
    
    def setup_ui(self):
        # Intestazione
        header = HeaderFrame(self, "Workflow Integrati", 
                         "Esegui workflow integrati")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Grid di pulsanti per i workflow principali
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=20)
        
        workflow_buttons = [
            ("Registra nuova proprietà", self.registra_nuova_proprieta),
            ("Registra passaggio proprietà", self.registra_passaggio_proprieta),
            ("Verifica integrità database", self.verifica_integrita_database),
            ("Backup logico dati", self.backup_logico_dati),
            ("Sincronizza con Archivio di Stato", self.sincronizza_archivio)
        ]
        
        for i, (text, command) in enumerate(workflow_buttons):
            row, col = divmod(i, 3)
            ttk.Button(buttons_frame, text=text, command=command, width=25).grid(
                row=row, column=col, padx=10, pady=10)
        
        # Area per i log
        log_frame = ttk.LabelFrame(self, text="Log operazioni")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log_viewer = LogViewer(log_frame)
        self.log_viewer.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def refresh_data(self):
        """Aggiorna i dati visualizzati"""
        pass  # Non necessario per questo frame
    
    def add_log(self, message):
        """Aggiunge un messaggio al log"""
        self.log_viewer.add_log(message)
        # Aggiorna anche lo stato dell'applicazione
        self.app.set_status(message)
    
    def registra_nuova_proprieta(self):
        """Apre il workflow per registrare una nuova proprietà"""
        workflow = RegistraNuovaProprietaWorkflow(
            self, self.db_manager, on_complete=self.refresh_data, log_callback=self.add_log
        )
        workflow.execute()
    
    def registra_passaggio_proprieta(self):
        """Apre il workflow per registrare un passaggio di proprietà"""
        workflow = RegistraPassaggioProprietaWorkflow(
            self, self.db_manager, on_complete=self.refresh_data, log_callback=self.add_log
        )
        workflow.execute()
    
    def verifica_integrita_database(self):
        """Verifica l'integrità del database"""
        workflow = VerificaIntegritaWorkflow(
            self, self.db_manager, log_callback=self.add_log
        )
        workflow.execute()
    
    def backup_logico_dati(self):
        """Esegue un backup logico dei dati"""
        workflow = BackupLogicoDatiWorkflow(
            self, self.db_manager, log_callback=self.add_log
        )
        workflow.execute()
    
    def sincronizza_archivio(self):
        """Sincronizza una partita con l'Archivio di Stato"""
        workflow = SincronizzaArchivioWorkflow(
            self, self.db_manager, log_callback=self.add_log
        )
        workflow.execute()
        
    def show_maps(self):
        """Mostra le mappe degli immobili"""
        try:
            import folium
        except ImportError:
            messagebox.showinfo("Informazione", 
                              "Per utilizzare le mappe, installa folium con: pip install folium")
            return
        
        # Richiedi il comune
        comune = simpledialog.askstring("Mappa Immobili", "Inserisci il nome del comune:")
        if not comune:
            return
        
        # Recupera tutti gli immobili del comune
        query = """
        SELECT i.id, i.natura, i.classificazione, l.nome as localita_nome, 
               p.numero_partita as partita_numero
        FROM immobile i
        JOIN localita l ON i.localita_id = l.id
        JOIN partita p ON i.partita_id = p.id
        WHERE l.comune_nome = %s
        """
        
        if self.db_manager.execute_query(query, (comune,)):
            immobili = self.db_manager.fetchall()
            
            if not immobili:
                messagebox.showinfo("Informazione", f"Nessun immobile trovato per il comune {comune}")
                return
            
            # Crea la mappa
            if self.db_manager.create_map_view(self, immobili):
                self.add_log(f"Visualizzata mappa degli immobili di {comune}")
            else:
                messagebox.showerror("Errore", "Impossibile creare la mappa")
        else:
            messagebox.showerror("Errore", "Impossibile recuperare gli immobili")

class HomeFrame(BaseFrame):
    """Frame per la home dell'applicazione"""
    
    def __init__(self, parent, db_manager, app):
        super().__init__(parent, db_manager)
        self.app = app  # Riferimento all'applicazione principale
        self.setup_ui()
    
    def setup_ui(self):
        # Intestazione
        header = HeaderFrame(self, f"{APP_NAME} v{APP_VERSION}", 
                         APP_DESCRIPTION)
        header.pack(fill=tk.X, padx=10, pady=10)
        
        # Contenuto
        content_frame = ttk.Frame(self, padding="20")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Informazioni sul sistema
        ttk.Label(content_frame, text="Informazioni sul sistema", 
                font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=10)
        
        info_frame = ttk.LabelFrame(content_frame, text="Database")
        info_frame.grid(row=1, column=0, sticky=tk.EW, pady=5)
        
        ttk.Label(info_frame, text=f"Server: {self.db_manager.conn_params['host']}").grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Label(info_frame, text=f"Database: {self.db_manager.conn_params['dbname']}").grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Label(info_frame, text=f"Schema: {self.db_manager.schema}").grid(
            row=2, column=0, sticky=tk.W, padx=10, pady=5)
        
        # Bottoni di navigazione rapida
        ttk.Label(content_frame, text="Operazioni rapide", 
                font=("Helvetica", 12, "bold")).grid(row=2, column=0, sticky=tk.W, pady=10)
        
        quick_buttons_frame = ttk.Frame(content_frame)
        quick_buttons_frame.grid(row=3, column=0, sticky=tk.EW, pady=5)
        
        quick_buttons = [
            ("Nuova consultazione", lambda: self.app.notebook.select(1)),
            ("Nuovo possessore", lambda: self.app.notebook.select(2)),
            ("Nuova partita", lambda: self.app.notebook.select(3)),
            ("Registra nuova proprietà", lambda: self.app.notebook.select(4))
        ]
        
        for i, (text, command) in enumerate(quick_buttons):
            ttk.Button(quick_buttons_frame, text=text, command=command, width=20).grid(
                row=0, column=i, padx=5, pady=5)
        
        # Statistiche (in una futura implementazione si potrebbero mostrare statistiche dal database)
        ttk.Label(content_frame, text="Statistiche", 
                font=("Helvetica", 12, "bold")).grid(row=4, column=0, sticky=tk.W, pady=10)
        
        stats_frame = ttk.LabelFrame(content_frame, text="Stato del sistema")
        stats_frame.grid(row=5, column=0, sticky=tk.EW, pady=5)
        
        ttk.Label(stats_frame, text="Connessione al database: Attiva").grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=5)
        ttk.Label(stats_frame, text=f"Data corrente: {date.today().strftime('%d/%m/%Y')}").grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=5)
        
        # Link alla documentazione (da implementare)
        ttk.Label(content_frame, text="Documentazione", 
                font=("Helvetica", 12, "bold")).grid(row=6, column=0, sticky=tk.W, pady=10)
        
        docs_frame = ttk.Frame(content_frame)
        docs_frame.grid(row=7, column=0, sticky=tk.EW, pady=5)
        
        ttk.Button(docs_frame, text="Manuale utente", command=self.show_help).grid(
            row=0, column=0, padx=5, pady=5)
        ttk.Button(docs_frame, text="Informazioni", command=self.show_about).grid(
            row=0, column=1, padx=5, pady=5)
    
    def refresh_data(self):
        """Aggiorna i dati visualizzati"""
        pass  # Non necessario per questo frame
    
    def show_help(self):
        """Mostra la guida dell'applicazione"""
        self.app.show_help()
    
    def show_about(self):
        """Mostra informazioni sull'applicazione"""
        self.app.show_about()

class CatastoApp:
    """Classe principale dell'applicazione"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1200x700")
        
        # Carica la configurazione
        self.config = load_config()
        
        # Inizializza il gestore del database
        self.db_manager = CatastoDBManager(**self.config['database'])
        
        # Inizializza il gestore dell'autenticazione
        self.auth_manager = self.db_manager.UserAuthManager(self.db_manager)
        
        # Connessione al database all'avvio
        if not self.db_manager.connect():
            messagebox.showerror("Errore", "Impossibile connettersi al database")
        
        # Configura l'interfaccia utente
        self.create_menu()
        self.create_notebook()
        self.create_status_bar()
        
        # Configura la gestione della chiusura dell'applicazione
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    # ... resto del codice ...
    
    def backup_database(self):
        """Esegue un backup completo del database"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Backup Database")
        dialog.geometry("500x300")
        dialog.grab_set()
        
        ttk.Label(dialog, text="Backup Database", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # Form
        form_frame = ttk.Frame(dialog, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(form_frame, text="Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        directory_var = tk.StringVar(value=DEFAULT_BACKUP_DIR)
        directory_entry = ttk.Entry(form_frame, width=40, textvariable=directory_var)
        directory_entry.grid(row=0, column=1, pady=5, sticky=tk.W)
        
        def select_directory():
            directory = tk.filedialog.askdirectory(initialdir=DEFAULT_BACKUP_DIR)
            if directory:
                directory_var.set(directory)
        
        ttk.Button(form_frame, text="Sfoglia", command=select_directory).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Opzioni:").grid(row=1, column=0, sticky=tk.W, pady=5)
        options_frame = ttk.Frame(form_frame)
        options_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        include_schema_var = tk.BooleanVar(value=True)
        include_data_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(options_frame, text="Includi schema", variable=include_schema_var).pack(anchor=tk.W)
        ttk.Checkbutton(options_frame, text="Includi dati", variable=include_data_var).pack(anchor=tk.W)
        
        # Progress label
        progress_label = ttk.Label(dialog, text="")
        progress_label.pack(fill=tk.X, padx=10, pady=5)
        
        # Pulsanti
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def execute_backup():
            directory = directory_var.get()
            include_schema = include_schema_var.get()
            include_data = include_data_var.get()
            
            if not directory:
                messagebox.showerror("Errore", "Selezionare una directory")
                return
            
            progress_label.config(text="Backup in corso...")
            dialog.update()
            
            success, result = self.db_manager.backup_database(
                directory, 
                include_schema=include_schema, 
                include_data=include_data
            )
            
            if success:
                progress_label.config(text=f"Backup completato: {result}")
                messagebox.showinfo("Successo", f"Backup eseguito con successo: {result}")
                self.workflow_frame.add_log(f"Backup database eseguito in {result}")
            else:
                progress_label.config(text="Errore durante il backup")
                messagebox.showerror("Errore", f"Impossibile eseguire il backup: {result}")
        
        ttk.Button(buttons_frame, text="Esegui Backup", command=execute_backup).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def import_export_data(self):
        """Mostra la finestra per importare/esportare dati"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Importa/Esporta Dati")
        dialog.geometry("500x350")
        dialog.grab_set()
        
        ttk.Label(dialog, text="Importa/Esporta Dati", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab Esporta
        export_frame = ttk.Frame(notebook, padding="10")
        notebook.add(export_frame, text="Esporta")
        
        ttk.Label(export_frame, text="Tabella:").grid(row=0, column=0, sticky=tk.W, pady=5)
        export_table_var = tk.StringVar()
        export_table_combo = ttk.Combobox(export_frame, textvariable=export_table_var, width=30)
        export_table_combo['values'] = ('partita', 'possessore', 'immobile', 'consultazione')
        export_table_combo.grid(row=0, column=1, pady=5, sticky=tk.W)
        
        ttk.Label(export_frame, text="File di destinazione:").grid(row=1, column=0, sticky=tk.W, pady=5)
        export_file_var = tk.StringVar()
        export_file_entry = ttk.Entry(export_frame, width=30, textvariable=export_file_var)
        export_file_entry.grid(row=1, column=1, pady=5, sticky=tk.W)
        
        def select_export_file():
            file_path = tk.filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Salva file CSV"
            )
            if file_path:
                export_file_var.set(file_path)
        
        ttk.Button(export_frame, text="Sfoglia", command=select_export_file).grid(row=1, column=2, padx=5, pady=5)
        
        def export_data():
            table = export_table_var.get()
            file_path = export_file_var.get()
            
            if not table:
                messagebox.showerror("Errore", "Selezionare una tabella")
                return
            
            if not file_path:
                messagebox.showerror("Errore", "Selezionare un file di destinazione")
                return
            
            # Esegue la query per recuperare i dati
            query = f"SELECT * FROM {table}"
            if self.db_manager.execute_query(query):
                data = self.db_manager.fetchall()
                
                if self.db_manager.export_to_csv(data, file_path):
                    messagebox.showinfo("Successo", f"Dati esportati con successo in {file_path}")
                    self.workflow_frame.add_log(f"Dati esportati in {file_path}")
                else:
                    messagebox.showerror("Errore", "Impossibile esportare i dati")
            else:
                messagebox.showerror("Errore", "Impossibile recuperare i dati dalla tabella")
        
        ttk.Button(export_frame, text="Esporta", command=export_data).grid(row=2, column=1, pady=10)
        
        # Tab Importa
        import_frame = ttk.Frame(notebook, padding="10")
        notebook.add(import_frame, text="Importa")
        
        ttk.Label(import_frame, text="Tabella:").grid(row=0, column=0, sticky=tk.W, pady=5)
        import_table_var = tk.StringVar()
        import_table_combo = ttk.Combobox(import_frame, textvariable=import_table_var, width=30)
        import_table_combo['values'] = ('partita', 'possessore', 'immobile', 'consultazione')
        import_table_combo.grid(row=0, column=1, pady=5, sticky=tk.W)
        
        ttk.Label(import_frame, text="File di origine:").grid(row=1, column=0, sticky=tk.W, pady=5)
        import_file_var = tk.StringVar()
        import_file_entry = ttk.Entry(import_frame, width=30, textvariable=import_file_var)
        import_file_entry.grid(row=1, column=1, pady=5, sticky=tk.W)
        
        def select_import_file():
            file_path = tk.filedialog.askopenfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Apri file CSV"
            )
            if file_path:
                import_file_var.set(file_path)
        
        ttk.Button(import_frame, text="Sfoglia", command=select_import_file).grid(row=1, column=2, padx=5, pady=5)
        
        # Avviso
        ttk.Label(import_frame, text="ATTENZIONE: L'importazione potrebbe sovrascrivere dati esistenti.",
                 foreground="red").grid(row=2, column=0, columnspan=3, pady=10)
        
        def import_data():
            table = import_table_var.get()
            file_path = import_file_var.get()
            
            if not table:
                messagebox.showerror("Errore", "Selezionare una tabella")
                return
            
            if not file_path:
                messagebox.showerror("Errore", "Selezionare un file di origine")
                return
            
            # Conferma
            if not messagebox.askyesno("Conferma", 
                                      "L'importazione potrebbe sovrascrivere dati esistenti.\nContinuare?"):
                return
            
            # Importa i dati
            if self.db_manager.import_from_csv(file_path, table):
                messagebox.showinfo("Successo", f"Dati importati con successo da {file_path}")
                self.workflow_frame.add_log(f"Dati importati da {file_path}")
            else:
                messagebox.showerror("Errore", "Impossibile importare i dati")
        
        ttk.Button(import_frame, text="Importa", command=import_data).grid(row=3, column=1, pady=10)
        
        # Pulsanti
        ttk.Button(dialog, text="Chiudi", command=dialog.destroy).pack(side=tk.RIGHT, padx=10, pady=10)
    
    def login_dialog(self):
        """Mostra la finestra di login"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Login")
        dialog.geometry("300x200")
        dialog.grab_set()
        
        ttk.Label(dialog, text="Accesso Utente", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        form_frame = ttk.Frame(dialog, padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        ttk.Label(form_frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        username_var = tk.StringVar()
        username_entry = ttk.Entry(form_frame, width=20, textvariable=username_var)
        username_entry.grid(row=0, column=1, pady=5, sticky=tk.W)
        
        ttk.Label(form_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(form_frame, width=20, textvariable=password_var, show="*")
        password_entry.grid(row=1, column=1, pady=5, sticky=tk.W)
        
        status_label = ttk.Label(dialog, text="")
        status_label.pack(fill=tk.X, padx=10)
        
        def do_login():
            username = username_var.get()
            password = password_var.get()
            
            if not username or not password:
                status_label.config(text="Inserire username e password", foreground="red")
                return
            
            success, result = self.auth_manager.login(username, password)
            
            if success:
                self.current_user = result
                self.set_status(f"Utente connesso: {result['nome_completo']} ({result['ruolo']})")
                dialog.destroy()
            else:
                status_label.config(text=result, foreground="red")
        
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(buttons_frame, text="Login", command=do_login).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
         
        # Contenuto della guida
        guide = """
GUIDA DELL'APPLICAZIONE GESTIONE CATASTO STORICO

Questa applicazione permette di gestire il database del Catasto Storico degli anni '50, con funzionalità per:

1. CONSULTAZIONI
   - Registrare nuove consultazioni dell'archivio
   - Cercare consultazioni esistenti
   - Modificare o eliminare consultazioni

2. POSSESSORI
   - Registrare nuovi possessori di immobili
   - Cercare possessori esistenti
   - Visualizzare gli immobili di un possessore
   - Generare report storici dei possessori

3. PARTITE
   - Registrare nuove partite catastali
   - Cercare partite esistenti
   - Duplicare partite esistenti
   - Generare certificati di proprietà
   - Generare report genealogici delle proprietà

4. WORKFLOW INTEGRATI
   - Registrare una nuova proprietà completa
   - Registrare passaggi di proprietà
   - Registrare frazionamenti di proprietà
   - Verificare e riparare l'integrità del database
   - Eseguire backup dei dati
   - Sincronizzare con l'Archivio di Stato

5. FUNZIONALITÀ GENERALI
   - Connessione al database
   - Configurazione dell'applicazione
   - Visualizzazione di log e messaggi di stato

Per ulteriori informazioni, contattare l'amministratore del sistema.
        """
        
        help_text.insert(tk.END, guide)
        help_text.config(state=tk.DISABLED)
        
        ttk.Button(help_window, text="Chiudi", command=help_window.destroy).pack(pady=10)
    
    def show_about(self):
        """Mostra informazioni sull'applicazione"""
        messagebox.showinfo("Informazioni", 
                          f"{APP_NAME} v{APP_VERSION}\n\n"
                          f"{APP_DESCRIPTION}\n\n"
                          "© 2025 - Tutti i diritti riservati")
    
    def on_closing(self):
        """Gestisce la chiusura dell'applicazione"""
        if messagebox.askokcancel("Uscita", "Sei sicuro di voler uscire dall'applicazione?"):
            # Chiude la connessione al database
            self.db_manager.disconnect()
            # Chiude l'applicazione
            self.root.destroy()

def main():
    """Funzione principale"""
    root = tk.Tk()
    app = CatastoApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
