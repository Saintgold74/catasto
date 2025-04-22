#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaccia Python per Gestione Catasto Storico
Versione 1.0

Questa applicazione fornisce un'interfaccia grafica per interagire con il database
del Catasto Storico, permettendo di gestire consultazioni e workflow integrati.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import psycopg2
import psycopg2.extras
import json
import datetime
import os
from functools import partial

# Configurazione del database
DB_CONFIG = {
    "dbname": "catasto_storico",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5432"
}

# Classe per gestire la connessione al database
class DatabaseManager:
    def __init__(self, config=DB_CONFIG):
        self.config = config
        self.conn = None
        self.cur = None
    
    def connect(self):
        """Stabilisce una connessione al database"""
        try:
            self.conn = psycopg2.connect(**self.config)
            self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            self.execute("SET search_path TO catasto")
            return True
        except Exception as e:
            messagebox.showerror("Errore di connessione", f"Impossibile connettersi al database: {str(e)}")
            return False
    
    def disconnect(self):
        """Chiude la connessione al database"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
    
    def execute(self, query, params=None, commit=False):
        """Esegue una query SQL"""
        try:
            self.cur.execute(query, params)
            if commit:
                self.conn.commit()
            return self.cur
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def call_procedure(self, proc_name, params=None, commit=True):
        """Chiama una stored procedure"""
        try:
            if params:
                self.cur.callproc(proc_name, params)
            else:
                self.cur.callproc(proc_name)
            
            if commit:
                self.conn.commit()
            
            # Restituisce i risultati se disponibili
            if self.cur.description:
                return self.cur.fetchall()
            return None
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def call_function(self, func_name, params=None):
        """Chiama una funzione del database"""
        try:
            if params:
                query = f"SELECT * FROM {func_name}({','.join(['%s'] * len(params))})"
                self.cur.execute(query, params)
            else:
                query = f"SELECT * FROM {func_name}()"
                self.cur.execute(query)
            
            # Restituisce i risultati se disponibili
            if self.cur.description:
                return self.cur.fetchall()
            return None
        except Exception as e:
            raise e

# Classe per gestire le operazioni di consultazione
class ConsultazioneManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def registra_consultazione(self, data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante):
        """Registra una nuova consultazione"""
        try:
            self.db.call_procedure(
                "registra_consultazione",
                [data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante]
            )
            return True, "Consultazione registrata con successo"
        except Exception as e:
            return False, f"Errore durante la registrazione della consultazione: {str(e)}"
    
    def cerca_consultazioni(self, data_inizio=None, data_fine=None, richiedente=None, funzionario=None):
        """Cerca consultazioni in base ai parametri specificati"""
        try:
            results = self.db.call_function(
                "cerca_consultazioni",
                [data_inizio, data_fine, richiedente, funzionario]
            )
            return True, results
        except Exception as e:
            return False, f"Errore durante la ricerca delle consultazioni: {str(e)}"
    
    def aggiorna_consultazione(self, id_consultazione, data=None, richiedente=None, documento_identita=None, 
                               motivazione=None, materiale_consultato=None, funzionario_autorizzante=None):
        """Aggiorna una consultazione esistente"""
        try:
            self.db.call_procedure(
                "aggiorna_consultazione",
                [id_consultazione, data, richiedente, documento_identita, motivazione, 
                 materiale_consultato, funzionario_autorizzante]
            )
            return True, "Consultazione aggiornata con successo"
        except Exception as e:
            return False, f"Errore durante l'aggiornamento della consultazione: {str(e)}"
    
    def elimina_consultazione(self, id_consultazione):
        """Elimina una consultazione"""
        try:
            self.db.call_procedure("elimina_consultazione", [id_consultazione])
            return True, "Consultazione eliminata con successo"
        except Exception as e:
            return False, f"Errore durante l'eliminazione della consultazione: {str(e)}"

# Classe per gestire le operazioni sui possessori
class PossessoreManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def inserisci_possessore(self, comune_nome, cognome_nome, paternita, nome_completo, attivo=True):
        """Inserisce un nuovo possessore"""
        try:
            self.db.call_procedure(
                "inserisci_possessore",
                [comune_nome, cognome_nome, paternita, nome_completo, attivo]
            )
            return True, "Possessore inserito con successo"
        except Exception as e:
            return False, f"Errore durante l'inserimento del possessore: {str(e)}"
    
    def cerca_possessori(self, query):
        """Cerca possessori per nome"""
        try:
            results = self.db.call_function("cerca_possessori", [query])
            return True, results
        except Exception as e:
            return False, f"Errore durante la ricerca dei possessori: {str(e)}"
    
    def get_immobili_possessore(self, possessore_id):
        """Ottiene gli immobili di un possessore"""
        try:
            results = self.db.call_function("get_immobili_possessore", [possessore_id])
            return True, results
        except Exception as e:
            return False, f"Errore durante il recupero degli immobili del possessore: {str(e)}"
    
    def genera_report_possessore(self, possessore_id):
        """Genera un report storico per un possessore"""
        try:
            result = self.db.call_function("genera_report_possessore", [possessore_id])
            if result and len(result) > 0:
                return True, result[0][0]  # Il report è una colonna di testo
            return False, "Nessun dato trovato per il possessore specificato"
        except Exception as e:
            return False, f"Errore durante la generazione del report del possessore: {str(e)}"

# Classe per gestire le operazioni sulle partite
class PartitaManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def inserisci_partita_con_possessori(self, comune_nome, numero_partita, tipo, data_impianto, possessore_ids):
        """Inserisce una nuova partita con possessori"""
        try:
            self.db.call_procedure(
                "inserisci_partita_con_possessori",
                [comune_nome, numero_partita, tipo, data_impianto, possessore_ids]
            )
            return True, "Partita inserita con successo"
        except Exception as e:
            return False, f"Errore durante l'inserimento della partita: {str(e)}"
    
    def duplica_partita(self, partita_id, nuovo_numero_partita, mantenere_possessori=True, mantenere_immobili=False):
        """Duplica una partita esistente"""
        try:
            self.db.call_procedure(
                "duplica_partita",
                [partita_id, nuovo_numero_partita, mantenere_possessori, mantenere_immobili]
            )
            return True, f"Partita duplicata con successo con nuovo numero {nuovo_numero_partita}"
        except Exception as e:
            return False, f"Errore durante la duplicazione della partita: {str(e)}"
    
    def esporta_partita_json(self, partita_id):
        """Esporta i dati di una partita in formato JSON"""
        try:
            result = self.db.call_function("esporta_partita_json", [partita_id])
            if result and len(result) > 0:
                return True, json.loads(result[0][0])
            return False, "Nessun dato trovato per la partita specificata"
        except Exception as e:
            return False, f"Errore durante l'esportazione della partita: {str(e)}"
    
    def genera_certificato_proprieta(self, partita_id):
        """Genera un certificato di proprietà per una partita"""
        try:
            result = self.db.call_function("genera_certificato_proprieta", [partita_id])
            if result and len(result) > 0:
                return True, result[0][0]  # Il certificato è una colonna di testo
            return False, "Nessun dato trovato per la partita specificata"
        except Exception as e:
            return False, f"Errore durante la generazione del certificato: {str(e)}"
    
    def genera_report_genealogico(self, partita_id):
        """Genera un report genealogico per una partita"""
        try:
            result = self.db.call_function("genera_report_genealogico", [partita_id])
            if result and len(result) > 0:
                return True, result[0][0]  # Il report è una colonna di testo
            return False, "Nessun dato trovato per la partita specificata"
        except Exception as e:
            return False, f"Errore durante la generazione del report genealogico: {str(e)}"

# Classe per gestire i workflow integrati
class WorkflowManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def registra_nuova_proprieta(self, comune_nome, numero_partita, data_impianto, possessori, immobili):
        """Registra una nuova proprietà completa"""
        try:
            possessori_json = json.dumps(possessori)
            immobili_json = json.dumps(immobili)
            self.db.call_procedure(
                "registra_nuova_proprieta",
                [comune_nome, numero_partita, data_impianto, possessori_json, immobili_json]
            )
            return True, "Nuova proprietà registrata con successo"
        except Exception as e:
            return False, f"Errore durante la registrazione della nuova proprietà: {str(e)}"
    
    def registra_passaggio_proprieta(self, partita_origine_id, comune_nome, numero_partita, 
                                  tipo_variazione, data_variazione, tipo_contratto, data_contratto, 
                                  notaio=None, repertorio=None, nuovi_possessori=None, 
                                  immobili_da_trasferire=None, note=None):
        """Registra un passaggio di proprietà completo"""
        try:
            nuovi_possessori_json = json.dumps(nuovi_possessori) if nuovi_possessori else None
            self.db.call_procedure(
                "registra_passaggio_proprieta",
                [partita_origine_id, comune_nome, numero_partita, tipo_variazione, data_variazione,
                 tipo_contratto, data_contratto, notaio, repertorio, nuovi_possessori_json, 
                 immobili_da_trasferire, note]
            )
            return True, "Passaggio di proprietà registrato con successo"
        except Exception as e:
            return False, f"Errore durante la registrazione del passaggio di proprietà: {str(e)}"
    
    def registra_frazionamento(self, partita_origine_id, data_variazione, tipo_contratto, data_contratto, 
                           nuove_partite, notaio=None, repertorio=None, note=None):
        """Registra un frazionamento di proprietà"""
        try:
            nuove_partite_json = json.dumps(nuove_partite)
            self.db.call_procedure(
                "registra_frazionamento",
                [partita_origine_id, data_variazione, tipo_contratto, data_contratto, 
                 nuove_partite_json, notaio, repertorio, note]
            )
            return True, "Frazionamento registrato con successo"
        except Exception as e:
            return False, f"Errore durante la registrazione del frazionamento: {str(e)}"
    
    def verifica_integrita_database(self):
        """Verifica l'integrità del database"""
        try:
            # Creazione di una variabile di output
            self.db.execute("DO $$ DECLARE v_problemi BOOLEAN; BEGIN CALL verifica_integrita_database(v_problemi); END $$;")
            return True, "Verifica integrità completata. Controlla i log del server per i dettagli."
        except Exception as e:
            return False, f"Errore durante la verifica dell'integrità: {str(e)}"
    
    def ripara_problemi_database(self, correzione_automatica=False):
        """Ripara problemi comuni del database"""
        try:
            self.db.call_procedure("ripara_problemi_database", [correzione_automatica])
            return True, "Riparazione completata. Controlla i log del server per i dettagli."
        except Exception as e:
            return False, f"Errore durante la riparazione: {str(e)}"
    
    def backup_logico_dati(self, directory="/tmp", prefisso_file="catasto_backup"):
        """Esegue un backup logico dei dati"""
        try:
            self.db.call_procedure("backup_logico_dati", [directory, prefisso_file])
            return True, f"Backup pianificato con successo nella directory {directory}. Controlla i log del server per i dettagli."
        except Exception as e:
            return False, f"Errore durante la pianificazione del backup: {str(e)}"
    
    def sincronizza_con_archivio_stato(self, partita_id, riferimento_archivio, data_sincronizzazione=None):
        """Sincronizza una partita con l'Archivio di Stato"""
        try:
            if data_sincronizzazione is None:
                data_sincronizzazione = datetime.date.today()
            self.db.call_procedure("sincronizza_con_archivio_stato", [partita_id, riferimento_archivio, data_sincronizzazione])
            return True, "Sincronizzazione con l'Archivio di Stato completata con successo"
        except Exception as e:
            return False, f"Errore durante la sincronizzazione: {str(e)}"

# Classe principale dell'applicazione
class CatastoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestione Catasto Storico")
        self.root.geometry("1200x700")
        
        self.db_manager = DatabaseManager()
        self.consultazione_manager = ConsultazioneManager(self.db_manager)
        self.possessore_manager = PossessoreManager(self.db_manager)
        self.partita_manager = PartitaManager(self.db_manager)
        self.workflow_manager = WorkflowManager(self.db_manager)
        
        self.create_menu()
        self.create_notebook()
        self.create_status_bar()
        
        # Connessione al database all'avvio
        if self.db_manager.connect():
            self.set_status("Connesso al database")
        else:
            self.set_status("Errore di connessione al database")
    
    def create_menu(self):
        """Crea la barra dei menu"""
        menubar = tk.Menu(self.root)
        
        # Menu File
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Connetti al database", command=self.connect_to_database)
        file_menu.add_command(label="Impostazioni connessione", command=self.show_connection_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Menu Consultazioni
        consultazioni_menu = tk.Menu(menubar, tearoff=0)
        consultazioni_menu.add_command(label="Nuova consultazione", command=self.show_nuova_consultazione)
        consultazioni_menu.add_command(label="Cerca consultazioni", command=self.show_cerca_consultazioni)
        menubar.add_cascade(label="Consultazioni", menu=consultazioni_menu)
        
        # Menu Possessori
        possessori_menu = tk.Menu(menubar, tearoff=0)
        possessori_menu.add_command(label="Nuovo possessore", command=self.show_nuovo_possessore)
        possessori_menu.add_command(label="Cerca possessori", command=self.show_cerca_possessori)
        menubar.add_cascade(label="Possessori", menu=possessori_menu)
        
        # Menu Partite
        partite_menu = tk.Menu(menubar, tearoff=0)
        partite_menu.add_command(label="Nuova partita", command=self.show_nuova_partita)
        partite_menu.add_command(label="Duplica partita", command=self.show_duplica_partita)
        partite_menu.add_command(label="Genera certificato", command=self.show_genera_certificato)
        partite_menu.add_command(label="Genera report genealogico", command=self.show_genera_report_genealogico)
        menubar.add_cascade(label="Partite", menu=partite_menu)
        
        # Menu Workflow
        workflow_menu = tk.Menu(menubar, tearoff=0)
        workflow_menu.add_command(label="Registra nuova proprietà", command=self.show_registra_nuova_proprieta)
        workflow_menu.add_command(label="Registra passaggio proprietà", command=self.show_registra_passaggio_proprieta)
        workflow_menu.add_command(label="Registra frazionamento", command=self.show_registra_frazionamento)
        workflow_menu.add_separator()
        workflow_menu.add_command(label="Verifica integrità database", command=self.verifica_integrita_database)
        workflow_menu.add_command(label="Ripara problemi database", command=self.ripara_problemi_database)
        workflow_menu.add_command(label="Backup logico dati", command=self.show_backup_logico_dati)
        workflow_menu.add_command(label="Sincronizza con Archivio di Stato", command=self.show_sincronizza_archivio)
        menubar.add_cascade(label="Workflow", menu=workflow_menu)
        
        # Menu Aiuto
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Guida", command=self.show_help)
        help_menu.add_command(label="Informazioni", command=self.show_about)
        menubar.add_cascade(label="Aiuto", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def create_notebook(self):
        """Crea il notebook con le diverse schede"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Scheda Home
        self.home_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.home_frame, text="Home")
        self.setup_home_tab()
        
        # Scheda Consultazioni
        self.consultazioni_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.consultazioni_frame, text="Consultazioni")
        self.setup_consultazioni_tab()
        
        # Scheda Possessori
        self.possessori_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.possessori_frame, text="Possessori")
        self.setup_possessori_tab()
        
        # Scheda Partite
        self.partite_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.partite_frame, text="Partite")
        self.setup_partite_tab()
        
        # Scheda Workflow
        self.workflow_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.workflow_frame, text="Workflow")
        self.setup_workflow_tab()
    
    def create_status_bar(self):
        """Crea la barra di stato"""
        self.status_bar = ttk.Label(self.root, text="Pronto", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def set_status(self, message):
        """Aggiorna il messaggio nella barra di stato"""
        self.status_bar.config(text=message)
    
    def setup_home_tab(self):
        """Configura il contenuto della scheda Home"""
        frame = ttk.Frame(self.home_frame, padding="10")
        frame.pack(expand=True, fill="both")
        
        ttk.Label(frame, text="Gestione Catasto Storico", font=("Helvetica", 16)).pack(pady=20)
        
        info_text = """
        Benvenuto nell'applicazione di gestione del Catasto Storico.
        
        Questa applicazione permette di:
        - Gestire consultazioni dell'archivio
        - Cercare e gestire possessori e partite
        - Eseguire workflow integrati
        - Generare report e certificati
        - Verificare e mantenere l'integrità del database
        
        Utilizzare il menu in alto o le schede per accedere alle diverse funzionalità.
        """
        
        info_label = ttk.Label(frame, text=info_text, justify="left", wraplength=600)
        info_label.pack(pady=20)
        
        # Pulsanti rapidi
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(pady=20)
        
        ttk.Button(buttons_frame, text="Nuova consultazione", 
                   command=self.show_nuova_consultazione).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Cerca possessori", 
                   command=self.show_cerca_possessori).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Registra nuova proprietà", 
                   command=self.show_registra_nuova_proprieta).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Verifica integrità DB", 
                   command=self.verifica_integrita_database).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Genera certificato", 
                   command=self.show_genera_certificato).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Backup dati", 
                   command=self.show_backup_logico_dati).grid(row=1, column=2, padx=5, pady=5)
    
    def setup_consultazioni_tab(self):
        """Configura il contenuto della scheda Consultazioni"""
        frame = ttk.Frame(self.consultazioni_frame, padding="10")
        frame.pack(expand=True, fill="both")
        
        ttk.Label(frame, text="Gestione Consultazioni", font=("Helvetica", 14)).pack(pady=10)
        
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Nuova consultazione", 
                   command=self.show_nuova_consultazione).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Cerca consultazioni", 
                   command=self.show_cerca_consultazioni).pack(side=tk.LEFT, padx=5)
        
        # Area per i risultati della ricerca
        ttk.Label(frame, text="Risultati della ricerca", font=("Helvetica", 12)).pack(pady=10)
        
        self.consultazioni_tree = ttk.Treeview(frame, columns=("ID", "Data", "Richiedente", "Documento", "Motivazione", "Funzionario"))
        self.consultazioni_tree.heading("#0", text="")
        self.consultazioni_tree.column("#0", width=0, stretch=tk.NO)
        self.consultazioni_tree.heading("ID", text="ID")
        self.consultazioni_tree.column("ID", width=50)
        self.consultazioni_tree.heading("Data", text="Data")
        self.consultazioni_tree.column("Data", width=100)
        self.consultazioni_tree.heading("Richiedente", text="Richiedente")
        self.consultazioni_tree.column("Richiedente", width=150)
        self.consultazioni_tree.heading("Documento", text="Documento")
        self.consultazioni_tree.column("Documento", width=100)
        self.consultazioni_tree.heading("Motivazione", text="Motivazione")
        self.consultazioni_tree.column("Motivazione", width=200)
        self.consultazioni_tree.heading("Funzionario", text="Funzionario")
        self.consultazioni_tree.column("Funzionario", width=150)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.consultazioni_tree.yview)
        self.consultazioni_tree.configure(yscrollcommand=scrollbar.set)
        
        self.consultazioni_tree.pack(expand=True, fill="both", side=tk.LEFT)
        scrollbar.pack(fill="y", side=tk.RIGHT)
        
        # Menu contestuale per il TreeView
        self.consultazioni_context_menu = tk.Menu(self.consultazioni_tree, tearoff=0)
        self.consultazioni_context_menu.add_command(label="Modifica", command=self.edit_selected_consultazione)
        self.consultazioni_context_menu.add_command(label="Elimina", command=self.delete_selected_consultazione)
        
        self.consultazioni_tree.bind("<Button-3>", self.show_consultazioni_context_menu)
    
    def setup_possessori_tab(self):
        """Configura il contenuto della scheda Possessori"""
        frame = ttk.Frame(self.possessori_frame, padding="10")
        frame.pack(expand=True, fill="both")
        
        ttk.Label(frame, text="Gestione Possessori", font=("Helvetica", 14)).pack(pady=10)
        
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Nuovo possessore", 
                   command=self.show_nuovo_possessore).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Cerca possessori", 
                   command=self.show_cerca_possessori).pack(side=tk.LEFT, padx=5)
        
        # Area per i risultati della ricerca
        ttk.Label(frame, text="Risultati della ricerca", font=("Helvetica", 12)).pack(pady=10)
        
        self.possessori_tree = ttk.Treeview(frame, columns=("ID", "Nome", "Comune", "Num. Partite"))
        self.possessori_tree.heading("#0", text="")
        self.possessori_tree.column("#0", width=0, stretch=tk.NO)
        self.possessori_tree.heading("ID", text="ID")
        self.possessori_tree.column("ID", width=50)
        self.possessori_tree.heading("Nome", text="Nome Completo")
        self.possessori_tree.column("Nome", width=250)
        self.possessori_tree.heading("Comune", text="Comune")
        self.possessori_tree.column("Comune", width=150)
        self.possessori_tree.heading("Num. Partite", text="Num. Partite")
        self.possessori_tree.column("Num. Partite", width=100)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.possessori_tree.yview)
        self.possessori_tree.configure(yscrollcommand=scrollbar.set)
        
        self.possessori_tree.pack(expand=True, fill="both", side=tk.LEFT)
        scrollbar.pack(fill="y", side=tk.RIGHT)
        
        # Menu contestuale per il TreeView
        self.possessori_context_menu = tk.Menu(self.possessori_tree, tearoff=0)
        self.possessori_context_menu.add_command(label="Visualizza immobili", command=self.view_possessore_immobili)
        self.possessori_context_menu.add_command(label="Genera report", command=self.generate_possessore_report)
        
        self.possessori_tree.bind("<Button-3>", self.show_possessori_context_menu)
    
    def setup_partite_tab(self):
        """Configura il contenuto della scheda Partite"""
        frame = ttk.Frame(self.partite_frame, padding="10")
        frame.pack(expand=True, fill="both")
        
        ttk.Label(frame, text="Gestione Partite", font=("Helvetica", 14)).pack(pady=10)
        
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Nuova partita", 
                   command=self.show_nuova_partita).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Cerca partite", 
                   command=self.show_cerca_partite).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Duplica partita", 
                   command=self.show_duplica_partita).pack(side=tk.LEFT, padx=5)
        
        # Area per la ricerca
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill="x", pady=10)
        
        ttk.Label(search_frame, text="Comune:").pack(side=tk.LEFT, padx=5)
        self.partite_comune_entry = ttk.Entry(search_frame, width=15)
        self.partite_comune_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(search_frame, text="Numero partita:").pack(side=tk.LEFT, padx=5)
        self.partite_numero_entry = ttk.Entry(search_frame, width=10)
        self.partite_numero_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(search_frame, text="Cerca", 
                   command=self.search_partite).pack(side=tk.LEFT, padx=5)
        
        # Area per i risultati della ricerca
        ttk.Label(frame, text="Risultati della ricerca", font=("Helvetica", 12)).pack(pady=10)
        
        self.partite_tree = ttk.Treeview(frame, columns=("ID", "Comune", "Numero", "Tipo", "Stato", "Possessori"))
        self.partite_tree.heading("#0", text="")
        self.partite_tree.column("#0", width=0, stretch=tk.NO)
        self.partite_tree.heading("ID", text="ID")
        self.partite_tree.column("ID", width=50)
        self.partite_tree.heading("Comune", text="Comune")
        self.partite_tree.column("Comune", width=150)
        self.partite_tree.heading("Numero", text="Numero")
        self.partite_tree.column("Numero", width=80)
        self.partite_tree.heading("Tipo", text="Tipo")
        self.partite_tree.column("Tipo", width=100)
        self.partite_tree.heading("Stato", text="Stato")
        self.partite_tree.column("Stato", width=80)
        self.partite_tree.heading("Possessori", text="Possessori")
        self.partite_tree.column("Possessori", width=250)
        
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.partite_tree.yview)
        self.partite_tree.configure(yscrollcommand=scrollbar.set)
        
        self.partite_tree.pack(expand=True, fill="both", side=tk.LEFT)
        scrollbar.pack(fill="y", side=tk.RIGHT)
        
        # Menu contestuale per il TreeView
        self.partite_context_menu = tk.Menu(self.partite_tree, tearoff=0)
        self.partite_context_menu.add_command(label="Visualizza dettagli", command=self.view_partita_details)
        self.partite_context_menu.add_command(label="Genera certificato", command=self.generate_partita_certificato)
        self.partite_context_menu.add_command(label="Genera report genealogico", command=self.generate_partita_report)
        
        self.partite_tree.bind("<Button-3>", self.show_partite_context_menu)
    
    def setup_workflow_tab(self):
        """Configura il contenuto della scheda Workflow"""
        frame = ttk.Frame(self.workflow_frame, padding="10")
        frame.pack(expand=True, fill="both")
        
        ttk.Label(frame, text="Workflow Integrati", font=("Helvetica", 14)).pack(pady=10)
        
        # Grid di pulsanti per i workflow principali
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(pady=20)
        
        workflow_buttons = [
            ("Registra nuova proprietà", self.show_registra_nuova_proprieta),
            ("Registra passaggio proprietà", self.show_registra_passaggio_proprieta),
            ("Registra frazionamento", self.show_registra_frazionamento),
            ("Verifica integrità database", self.verifica_integrita_database),
            ("Ripara problemi database", self.ripara_problemi_database),
            ("Backup logico dati", self.show_backup_logico_dati),
            ("Sincronizza con Archivio di Stato", self.show_sincronizza_archivio)
        ]
        
        for i, (text, command) in enumerate(workflow_buttons):
            row, col = divmod(i, 3)
            ttk.Button(buttons_frame, text=text, command=command, width=25).grid(
                row=row, column=col, padx=10, pady=10)
        
        # Area per i log
        ttk.Label(frame, text="Log operazioni", font=("Helvetica", 12)).pack(pady=10)
        
        self.log_text = scrolledtext.ScrolledText(frame, height=15)
        self.log_text.pack(expand=True, fill="both")
        self.log_text.config(state=tk.DISABLED)
    
    def connect_to_database(self):
        """Connette al database"""
        if self.db_manager.connect():
            self.set_status("Connesso al database")
            messagebox.showinfo("Connessione", "Connessione al database stabilita con successo")
        else:
            self.set_status("Errore di connessione al database")
    
    def show_connection_settings(self):
        """Mostra la finestra di impostazioni connessione"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Impostazioni Connessione")
        settings_window.geometry("400x300")
        settings_window.grab_set()
        
        ttk.Label(settings_window, text="Impostazioni Connessione al Database", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(settings_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        ttk.Label(form_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, pady=5)
        host_entry = ttk.Entry(form_frame, width=30)
        host_entry.grid(row=0, column=1, pady=5)
        host_entry.insert(0, self.db_manager.config.get("host", "localhost"))
        
        ttk.Label(form_frame, text="Porta:").grid(row=1, column=0, sticky=tk.W, pady=5)
        port_entry = ttk.Entry(form_frame, width=30)
        port_entry.grid(row=1, column=1, pady=5)
        port_entry.insert(0, self.db_manager.config.get("port", "5432"))
        
        ttk.Label(form_frame, text="Nome Database:").grid(row=2, column=0, sticky=tk.W, pady=5)
        dbname_entry = ttk.Entry(form_frame, width=30)
        dbname_entry.grid(row=2, column=1, pady=5)
        dbname_entry.insert(0, self.db_manager.config.get("dbname", "catasto_storico"))
        
        ttk.Label(form_frame, text="Utente:").grid(row=3, column=0, sticky=tk.W, pady=5)
        user_entry = ttk.Entry(form_frame, width=30)
        user_entry.grid(row=3, column=1, pady=5)
        user_entry.insert(0, self.db_manager.config.get("user", "postgres"))
        
        ttk.Label(form_frame, text="Password:").grid(row=4, column=0, sticky=tk.W, pady=5)
        password_entry = ttk.Entry(form_frame, width=30, show="*")
        password_entry.grid(row=4, column=1, pady=5)
        password_entry.insert(0, self.db_manager.config.get("password", ""))
        
        def save_settings():
            # Aggiorna la configurazione
            self.db_manager.config["host"] = host_entry.get()
            self.db_manager.config["port"] = port_entry.get()
            self.db_manager.config["dbname"] = dbname_entry.get()
            self.db_manager.config["user"] = user_entry.get()
            self.db_manager.config["password"] = password_entry.get()
            
            # Tenta di connettersi con le nuove impostazioni
            if self.db_manager.connect():
                messagebox.showinfo("Successo", "Connessione al database stabilita con successo")
                settings_window.destroy()
            else:
                messagebox.showerror("Errore", "Impossibile connettersi al database con le impostazioni fornite")
        
        buttons_frame = ttk.Frame(settings_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Salva", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=settings_window.destroy).pack(side=tk.LEFT, padx=5)
    
    # Implementazioni dei metodi per le funzionalità di Consultazione
    def show_nuova_consultazione(self):
        """Mostra la finestra per registrare una nuova consultazione"""
        consultazione_window = tk.Toplevel(self.root)
        consultazione_window.title("Nuova Consultazione")
        consultazione_window.geometry("500x400")
        consultazione_window.grab_set()
        
        ttk.Label(consultazione_window, text="Registrazione Consultazione", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(consultazione_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # Data consultazione
        ttk.Label(form_frame, text="Data:").grid(row=0, column=0, sticky=tk.W, pady=5)
        data_entry = ttk.Entry(form_frame, width=30)
        data_entry.grid(row=0, column=1, pady=5)
        data_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        
        # Richiedente
        ttk.Label(form_frame, text="Richiedente:").grid(row=1, column=0, sticky=tk.W, pady=5)
        richiedente_entry = ttk.Entry(form_frame, width=30)
        richiedente_entry.grid(row=1, column=1, pady=5)
        
        # Documento d'identità
        ttk.Label(form_frame, text="Documento d'identità:").grid(row=2, column=0, sticky=tk.W, pady=5)
        documento_entry = ttk.Entry(form_frame, width=30)
        documento_entry.grid(row=2, column=1, pady=5)
        
        # Motivazione
        ttk.Label(form_frame, text="Motivazione:").grid(row=3, column=0, sticky=tk.W, pady=5)
        motivazione_text = tk.Text(form_frame, width=30, height=3)
        motivazione_text.grid(row=3, column=1, pady=5)
        
        # Materiale consultato
        ttk.Label(form_frame, text="Materiale consultato:").grid(row=4, column=0, sticky=tk.W, pady=5)
        materiale_text = tk.Text(form_frame, width=30, height=3)
        materiale_text.grid(row=4, column=1, pady=5)
        
        # Funzionario autorizzante
        ttk.Label(form_frame, text="Funzionario autorizzante:").grid(row=5, column=0, sticky=tk.W, pady=5)
        funzionario_entry = ttk.Entry(form_frame, width=30)
        funzionario_entry.grid(row=5, column=1, pady=5)
        
        def registra():
            try:
                data = data_entry.get()
                richiedente = richiedente_entry.get()
                documento = documento_entry.get()
                motivazione = motivazione_text.get("1.0", tk.END).strip()
                materiale = materiale_text.get("1.0", tk.END).strip()
                funzionario = funzionario_entry.get()
                
                if not data or not richiedente or not funzionario:
                    messagebox.showerror("Errore", "I campi Data, Richiedente e Funzionario sono obbligatori")
                    return
                
                success, message = self.consultazione_manager.registra_consultazione(
                    data, richiedente, documento, motivazione, materiale, funzionario)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    consultazione_window.destroy()
                    # Aggiorna la lista delle consultazioni
                    self.populate_consultazioni_tree()
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(consultazione_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Registra", command=registra).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=consultazione_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_cerca_consultazioni(self):
        """Mostra la finestra per cercare consultazioni"""
        search_window = tk.Toplevel(self.root)
        search_window.title("Cerca Consultazioni")
        search_window.geometry("500x300")
        search_window.grab_set()
        
        ttk.Label(search_window, text="Ricerca Consultazioni", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(search_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # Data inizio
        ttk.Label(form_frame, text="Data inizio:").grid(row=0, column=0, sticky=tk.W, pady=5)
        data_inizio_entry = ttk.Entry(form_frame, width=30)
        data_inizio_entry.grid(row=0, column=1, pady=5)
        
        # Data fine
        ttk.Label(form_frame, text="Data fine:").grid(row=1, column=0, sticky=tk.W, pady=5)
        data_fine_entry = ttk.Entry(form_frame, width=30)
        data_fine_entry.grid(row=1, column=1, pady=5)
        data_fine_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        
        # Richiedente
        ttk.Label(form_frame, text="Richiedente:").grid(row=2, column=0, sticky=tk.W, pady=5)
        richiedente_entry = ttk.Entry(form_frame, width=30)
        richiedente_entry.grid(row=2, column=1, pady=5)
        
        # Funzionario
        ttk.Label(form_frame, text="Funzionario:").grid(row=3, column=0, sticky=tk.W, pady=5)
        funzionario_entry = ttk.Entry(form_frame, width=30)
        funzionario_entry.grid(row=3, column=1, pady=5)
        
        def cerca():
            try:
                data_inizio = data_inizio_entry.get() if data_inizio_entry.get() else None
                data_fine = data_fine_entry.get() if data_fine_entry.get() else None
                richiedente = richiedente_entry.get() if richiedente_entry.get() else None
                funzionario = funzionario_entry.get() if funzionario_entry.get() else None
                
                success, results = self.consultazione_manager.cerca_consultazioni(
                    data_inizio, data_fine, richiedente, funzionario)
                
                if success:
                    self.populate_consultazioni_tree(results)
                    search_window.destroy()
                    self.notebook.select(self.consultazioni_frame)
                else:
                    messagebox.showerror("Errore", results)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(search_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Cerca", command=cerca).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=search_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def populate_consultazioni_tree(self, results=None):
        """Popola il TreeView delle consultazioni con i risultati di una ricerca"""
        # Pulisce il TreeView
        for item in self.consultazioni_tree.get_children():
            self.consultazioni_tree.delete(item)
        
        if results is None:
            try:
                # Carica tutte le consultazioni
                success, results = self.consultazione_manager.cerca_consultazioni()
                if not success:
                    messagebox.showerror("Errore", results)
                    return
            except Exception as e:
                messagebox.showerror("Errore", str(e))
                return
        
        # Aggiunge i risultati al TreeView
        for row in results:
            self.consultazioni_tree.insert("", tk.END, values=(
                row["id"], row["data"], row["richiedente"], 
                row["documento_identita"], row["motivazione"], 
                row["funzionario_autorizzante"]
            ))
    
    def show_consultazioni_context_menu(self, event):
        """Mostra il menu contestuale per il TreeView delle consultazioni"""
        item = self.consultazioni_tree.identify_row(event.y)
        if item:
            self.consultazioni_tree.selection_set(item)
            self.consultazioni_context_menu.post(event.x_root, event.y_root)
    
    def edit_selected_consultazione(self):
        """Modifica la consultazione selezionata"""
        selected_items = self.consultazioni_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.consultazioni_tree.item(item, "values")
        
        consultazione_id = values[0]
        
        # Apre una finestra per modificare i dati
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Modifica Consultazione")
        edit_window.geometry("500x400")
        edit_window.grab_set()
        
        ttk.Label(edit_window, text="Modifica Consultazione", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(edit_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # Data consultazione
        ttk.Label(form_frame, text="Data:").grid(row=0, column=0, sticky=tk.W, pady=5)
        data_entry = ttk.Entry(form_frame, width=30)
        data_entry.grid(row=0, column=1, pady=5)
        data_entry.insert(0, values[1])
        
        # Richiedente
        ttk.Label(form_frame, text="Richiedente:").grid(row=1, column=0, sticky=tk.W, pady=5)
        richiedente_entry = ttk.Entry(form_frame, width=30)
        richiedente_entry.grid(row=1, column=1, pady=5)
        richiedente_entry.insert(0, values[2])
        
        # Documento d'identità
        ttk.Label(form_frame, text="Documento d'identità:").grid(row=2, column=0, sticky=tk.W, pady=5)
        documento_entry = ttk.Entry(form_frame, width=30)
        documento_entry.grid(row=2, column=1, pady=5)
        documento_entry.insert(0, values[3])
        
        # Motivazione
        ttk.Label(form_frame, text="Motivazione:").grid(row=3, column=0, sticky=tk.W, pady=5)
        motivazione_text = tk.Text(form_frame, width=30, height=3)
        motivazione_text.grid(row=3, column=1, pady=5)
        motivazione_text.insert("1.0", values[4])
        
        # Materiale consultato
        ttk.Label(form_frame, text="Materiale consultato:").grid(row=4, column=0, sticky=tk.W, pady=5)
        materiale_text = tk.Text(form_frame, width=30, height=3)
        materiale_text.grid(row=4, column=1, pady=5)
        # Il materiale consultato non è visibile nella tabella, quindi lo lasciamo vuoto
        
        # Funzionario autorizzante
        ttk.Label(form_frame, text="Funzionario autorizzante:").grid(row=5, column=0, sticky=tk.W, pady=5)
        funzionario_entry = ttk.Entry(form_frame, width=30)
        funzionario_entry.grid(row=5, column=1, pady=5)
        funzionario_entry.insert(0, values[5])
        
        def aggiorna():
            try:
                data = data_entry.get()
                richiedente = richiedente_entry.get()
                documento = documento_entry.get()
                motivazione = motivazione_text.get("1.0", tk.END).strip()
                materiale = materiale_text.get("1.0", tk.END).strip()
                funzionario = funzionario_entry.get()
                
                if not data or not richiedente or not funzionario:
                    messagebox.showerror("Errore", "I campi Data, Richiedente e Funzionario sono obbligatori")
                    return
                
                success, message = self.consultazione_manager.aggiorna_consultazione(
                    consultazione_id, data, richiedente, documento, motivazione, materiale, funzionario)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    edit_window.destroy()
                    # Aggiorna la lista delle consultazioni
                    self.populate_consultazioni_tree()
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(edit_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Aggiorna", command=aggiorna).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=edit_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def delete_selected_consultazione(self):
        """Elimina la consultazione selezionata"""
        selected_items = self.consultazioni_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.consultazioni_tree.item(item, "values")
        
        consultazione_id = values[0]
        
        # Chiede conferma prima di eliminare
        if messagebox.askyesno("Elimina", f"Sei sicuro di voler eliminare la consultazione del {values[1]} di {values[2]}?"):
            try:
                success, message = self.consultazione_manager.elimina_consultazione(consultazione_id)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    # Aggiorna la lista delle consultazioni
                    self.populate_consultazioni_tree()
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
    
    # Implementazioni dei metodi per le funzionalità di Possessore
    def show_nuovo_possessore(self):
        """Mostra la finestra per registrare un nuovo possessore"""
        possessore_window = tk.Toplevel(self.root)
        possessore_window.title("Nuovo Possessore")
        possessore_window.geometry("500x300")
        possessore_window.grab_set()
        
        ttk.Label(possessore_window, text="Registrazione Possessore", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(possessore_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # Comune
        ttk.Label(form_frame, text="Comune:").grid(row=0, column=0, sticky=tk.W, pady=5)
        comune_entry = ttk.Entry(form_frame, width=30)
        comune_entry.grid(row=0, column=1, pady=5)
        
        # Cognome e nome
        ttk.Label(form_frame, text="Cognome e nome:").grid(row=1, column=0, sticky=tk.W, pady=5)
        cognome_nome_entry = ttk.Entry(form_frame, width=30)
        cognome_nome_entry.grid(row=1, column=1, pady=5)
        
        # Paternità
        ttk.Label(form_frame, text="Paternità:").grid(row=2, column=0, sticky=tk.W, pady=5)
        paternita_entry = ttk.Entry(form_frame, width=30)
        paternita_entry.grid(row=2, column=1, pady=5)
        
        # Nome completo
        ttk.Label(form_frame, text="Nome completo:").grid(row=3, column=0, sticky=tk.W, pady=5)
        nome_completo_entry = ttk.Entry(form_frame, width=30)
        nome_completo_entry.grid(row=3, column=1, pady=5)
        
        # Attivo
        ttk.Label(form_frame, text="Attivo:").grid(row=4, column=0, sticky=tk.W, pady=5)
        attivo_var = tk.BooleanVar(value=True)
        attivo_check = ttk.Checkbutton(form_frame, variable=attivo_var)
        attivo_check.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        def registra():
            try:
                comune = comune_entry.get()
                cognome_nome = cognome_nome_entry.get()
                paternita = paternita_entry.get()
                nome_completo = nome_completo_entry.get()
                attivo = attivo_var.get()
                
                if not comune or not cognome_nome or not nome_completo:
                    messagebox.showerror("Errore", "I campi Comune, Cognome e nome, e Nome completo sono obbligatori")
                    return
                
                success, message = self.possessore_manager.inserisci_possessore(
                    comune, cognome_nome, paternita, nome_completo, attivo)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    possessore_window.destroy()
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(possessore_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Registra", command=registra).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=possessore_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_cerca_possessori(self):
        """Mostra la finestra per cercare possessori"""
        search_window = tk.Toplevel(self.root)
        search_window.title("Cerca Possessori")
        search_window.geometry("400x200")
        search_window.grab_set()
        
        ttk.Label(search_window, text="Ricerca Possessori", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(search_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # Query
        ttk.Label(form_frame, text="Nome o cognome:").grid(row=0, column=0, sticky=tk.W, pady=5)
        query_entry = ttk.Entry(form_frame, width=30)
        query_entry.grid(row=0, column=1, pady=5)
        
        def cerca():
            try:
                query = query_entry.get()
                
                if not query:
                    messagebox.showerror("Errore", "Inserire un termine di ricerca")
                    return
                
                success, results = self.possessore_manager.cerca_possessori(query)
                
                if success:
                    self.populate_possessori_tree(results)
                    search_window.destroy()
                    self.notebook.select(self.possessori_frame)
                else:
                    messagebox.showerror("Errore", results)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(search_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Cerca", command=cerca).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=search_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def populate_possessori_tree(self, results=None):
        """Popola il TreeView dei possessori con i risultati di una ricerca"""
        # Pulisce il TreeView
        for item in self.possessori_tree.get_children():
            self.possessori_tree.delete(item)
        
        if not results:
            return
        
        # Aggiunge i risultati al TreeView
        for row in results:
            self.possessori_tree.insert("", tk.END, values=(
                row["id"], row["nome_completo"], row["comune_nome"], row["num_partite"]
            ))
    
    def show_possessori_context_menu(self, event):
        """Mostra il menu contestuale per il TreeView dei possessori"""
        item = self.possessori_tree.identify_row(event.y)
        if item:
            self.possessori_tree.selection_set(item)
            self.possessori_context_menu.post(event.x_root, event.y_root)
    
    def view_possessore_immobili(self):
        """Visualizza gli immobili del possessore selezionato"""
        selected_items = self.possessori_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.possessori_tree.item(item, "values")
        
        possessore_id = values[0]
        possessore_nome = values[1]
        
        try:
            success, results = self.possessore_manager.get_immobili_possessore(possessore_id)
            
            if success:
                # Mostra gli immobili in una nuova finestra
                immobili_window = tk.Toplevel(self.root)
                immobili_window.title(f"Immobili di {possessore_nome}")
                immobili_window.geometry("800x400")
                
                ttk.Label(immobili_window, text=f"Immobili posseduti da {possessore_nome}", font=("Helvetica", 12)).pack(pady=10)
                
                # Crea il TreeView per gli immobili
                immobili_tree = ttk.Treeview(immobili_window, columns=("ID", "Natura", "Località", "Comune", "Partita", "Tipo"))
                immobili_tree.heading("#0", text="")
                immobili_tree.column("#0", width=0, stretch=tk.NO)
                immobili_tree.heading("ID", text="ID")
                immobili_tree.column("ID", width=50)
                immobili_tree.heading("Natura", text="Natura")
                immobili_tree.column("Natura", width=150)
                immobili_tree.heading("Località", text="Località")
                immobili_tree.column("Località", width=150)
                immobili_tree.heading("Comune", text="Comune")
                immobili_tree.column("Comune", width=100)
                immobili_tree.heading("Partita", text="Partita")
                immobili_tree.column("Partita", width=80)
                immobili_tree.heading("Tipo", text="Tipo Partita")
                immobili_tree.column("Tipo", width=100)
                
                scrollbar = ttk.Scrollbar(immobili_window, orient="vertical", command=immobili_tree.yview)
                immobili_tree.configure(yscrollcommand=scrollbar.set)
                
                immobili_tree.pack(expand=True, fill="both", side=tk.LEFT)
                scrollbar.pack(fill="y", side=tk.RIGHT)
                
                # Popola il TreeView con i risultati
                for row in results:
                    immobili_tree.insert("", tk.END, values=(
                        row["immobile_id"], row["natura"], row["localita_nome"], 
                        row["comune"], row["partita_numero"], row["tipo_partita"]
                    ))
                
                # Pulsante di chiusura
                ttk.Button(immobili_window, text="Chiudi", command=immobili_window.destroy).pack(pady=10)
            else:
                messagebox.showerror("Errore", results)
        
        except Exception as e:
            messagebox.showerror("Errore", str(e))
    
    def generate_possessore_report(self):
        """Genera un report storico per il possessore selezionato"""
        selected_items = self.possessori_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.possessori_tree.item(item, "values")
        
        possessore_id = values[0]
        possessore_nome = values[1]
        
        try:
            success, report = self.possessore_manager.genera_report_possessore(possessore_id)
            
            if success:
                # Mostra il report in una nuova finestra
                report_window = tk.Toplevel(self.root)
                report_window.title(f"Report di {possessore_nome}")
                report_window.geometry("800x600")
                
                ttk.Label(report_window, text=f"Report storico di {possessore_nome}", font=("Helvetica", 12)).pack(pady=10)
                
                # Area di testo per il report
                report_text = scrolledtext.ScrolledText(report_window, width=80, height=30)
                report_text.pack(expand=True, fill="both", padx=10, pady=10)
                report_text.insert("1.0", report)
                report_text.config(state=tk.DISABLED)
                
                # Pulsanti
                buttons_frame = ttk.Frame(report_window)
                buttons_frame.pack(pady=10)
                
                def salva_report():
                    file_path = tk.filedialog.asksaveasfilename(
                        defaultextension=".txt",
                        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                        initialfile=f"report_{possessore_nome.replace(' ', '_')}.txt"
                    )
                    if file_path:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(report)
                        messagebox.showinfo("Salvato", f"Report salvato in {file_path}")
                
                ttk.Button(buttons_frame, text="Salva", command=salva_report).pack(side=tk.LEFT, padx=5)
                ttk.Button(buttons_frame, text="Chiudi", command=report_window.destroy).pack(side=tk.LEFT, padx=5)
            else:
                messagebox.showerror("Errore", report)
        
        except Exception as e:
            messagebox.showerror("Errore", str(e))
    
    # Implementazioni dei metodi per le funzionalità di Partita
    def show_nuova_partita(self):
        """Mostra la finestra per registrare una nuova partita"""
        partita_window = tk.Toplevel(self.root)
        partita_window.title("Nuova Partita")
        partita_window.geometry("600x400")
        partita_window.grab_set()
        
        ttk.Label(partita_window, text="Registrazione Partita", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(partita_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # Comune
        ttk.Label(form_frame, text="Comune:").grid(row=0, column=0, sticky=tk.W, pady=5)
        comune_entry = ttk.Entry(form_frame, width=30)
        comune_entry.grid(row=0, column=1, pady=5)
        
        # Numero partita
        ttk.Label(form_frame, text="Numero partita:").grid(row=1, column=0, sticky=tk.W, pady=5)
        numero_entry = ttk.Entry(form_frame, width=30)
        numero_entry.grid(row=1, column=1, pady=5)
        
        # Tipo
        ttk.Label(form_frame, text="Tipo:").grid(row=2, column=0, sticky=tk.W, pady=5)
        tipo_var = tk.StringVar()
        tipo_combo = ttk.Combobox(form_frame, textvariable=tipo_var, width=28)
        tipo_combo["values"] = ("principale", "secondaria")
        tipo_combo.grid(row=2, column=1, pady=5)
        tipo_combo.current(0)
        
        # Data impianto
        ttk.Label(form_frame, text="Data impianto:").grid(row=3, column=0, sticky=tk.W, pady=5)
        data_entry = ttk.Entry(form_frame, width=30)
        data_entry.grid(row=3, column=1, pady=5)
        data_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        
        # Possessori (lista separata da virgole di ID)
        ttk.Label(form_frame, text="ID Possessori (separati da virgola):").grid(row=4, column=0, sticky=tk.W, pady=5)
        possessori_entry = ttk.Entry(form_frame, width=30)
        possessori_entry.grid(row=4, column=1, pady=5)
        
        # Pulsante per cercare possessori
        def cerca_possessori_dialog():
            search_term = simpledialog.askstring("Cerca Possessori", "Inserisci nome o cognome:")
            if search_term:
                success, results = self.possessore_manager.cerca_possessori(search_term)
                if success and results:
                    # Mostra i risultati in una finestra di dialogo
                    dialog = tk.Toplevel(partita_window)
                    dialog.title("Risultati ricerca")
                    dialog.geometry("500x300")
                    
                    possessori_list = ttk.Treeview(dialog, columns=("ID", "Nome", "Comune"))
                    possessori_list.heading("#0", text="")
                    possessori_list.column("#0", width=0, stretch=tk.NO)
                    possessori_list.heading("ID", text="ID")
                    possessori_list.column("ID", width=50)
                    possessori_list.heading("Nome", text="Nome")
                    possessori_list.column("Nome", width=250)
                    possessori_list.heading("Comune", text="Comune")
                    possessori_list.column("Comune", width=150)
                    
                    scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=possessori_list.yview)
                    possessori_list.configure(yscrollcommand=scrollbar.set)
                    
                    possessori_list.pack(expand=True, fill="both", side=tk.LEFT)
                    scrollbar.pack(fill="y", side=tk.RIGHT)
                    
                    for row in results:
                        possessori_list.insert("", tk.END, values=(
                            row["id"], row["nome_completo"], row["comune_nome"]
                        ))
                    
                    def select_possessore():
                        selected = possessori_list.selection()
                        if selected:
                            ids = []
                            for item in selected:
                                values = possessori_list.item(item, "values")
                                ids.append(values[0])
                            current = possessori_entry.get()
                            if current:
                                new_ids = current + "," + ",".join(ids)
                            else:
                                new_ids = ",".join(ids)
                            possessori_entry.delete(0, tk.END)
                            possessori_entry.insert(0, new_ids)
                            dialog.destroy()
                    
                    ttk.Button(dialog, text="Seleziona", command=select_possessore).pack(pady=10)
                else:
                    messagebox.showinfo("Ricerca", "Nessun possessore trovato")
        
        ttk.Button(form_frame, text="Cerca", command=cerca_possessori_dialog).grid(row=4, column=2, padx=5)
        
        def registra():
            try:
                comune = comune_entry.get()
                numero = numero_entry.get()
                tipo = tipo_var.get()
                data = data_entry.get()
                possessori_str = possessori_entry.get()
                
                if not comune or not numero or not tipo or not data or not possessori_str:
                    messagebox.showerror("Errore", "Tutti i campi sono obbligatori")
                    return
                
                try:
                    numero = int(numero)
                    possessori_ids = [int(pid.strip()) for pid in possessori_str.split(",") if pid.strip()]
                except ValueError:
                    messagebox.showerror("Errore", "Numero partita e ID possessori devono essere numeri interi")
                    return
                
                success, message = self.partita_manager.inserisci_partita_con_possessori(
                    comune, numero, tipo, data, possessori_ids)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    partita_window.destroy()
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(partita_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Registra", command=registra).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=partita_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_cerca_partite(self):
        """Esegue la ricerca di partite in base ai criteri inseriti"""
        comune = self.partite_comune_entry.get()
        numero = self.partite_numero_entry.get()
        
        if not comune and not numero:
            messagebox.showinfo("Ricerca", "Inserire almeno un criterio di ricerca")
            return
        
        try:
            # Costruisci la query in base ai parametri inseriti
            query = "SELECT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato, "
            query += "string_agg(DISTINCT pos.nome_completo, ', ') AS possessori "
            query += "FROM catasto.partita p "
            query += "LEFT JOIN catasto.partita_possessore pp ON p.id = pp.partita_id "
            query += "LEFT JOIN catasto.possessore pos ON pp.possessore_id = pos.id "
            query += "WHERE 1=1 "
            
            params = []
            
            if comune:
                query += "AND p.comune_nome ILIKE %s "
                params.append(f"%{comune}%")
            
            if numero:
                try:
                    numero_int = int(numero)
                    query += "AND p.numero_partita = %s "
                    params.append(numero_int)
                except ValueError:
                    messagebox.showerror("Errore", "Il numero partita deve essere un numero intero")
                    return
            
            query += "GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato "
            query += "ORDER BY p.comune_nome, p.numero_partita"
            
            self.db_manager.execute(query, params)
            results = self.db_manager.cur.fetchall()
            
            self.populate_partite_tree(results)
            
        except Exception as e:
            messagebox.showerror("Errore", str(e))
    
    def search_partite(self):
        """Esegue la ricerca di partite"""
        self.show_cerca_partite()
    
    def populate_partite_tree(self, results=None):
        """Popola il TreeView delle partite con i risultati di una ricerca"""
        # Pulisce il TreeView
        for item in self.partite_tree.get_children():
            self.partite_tree.delete(item)
        
        if not results:
            return
        
        # Aggiunge i risultati al TreeView
        for row in results:
            self.partite_tree.insert("", tk.END, values=(
                row["id"], row["comune_nome"], row["numero_partita"], 
                row["tipo"], row["stato"], row["possessori"]
            ))
    
    def show_partite_context_menu(self, event):
        """Mostra il menu contestuale per il TreeView delle partite"""
        item = self.partite_tree.identify_row(event.y)
        if item:
            self.partite_tree.selection_set(item)
            self.partite_context_menu.post(event.x_root, event.y_root)
    
    def view_partita_details(self):
        """Visualizza i dettagli della partita selezionata"""
        selected_items = self.partite_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.partite_tree.item(item, "values")
        
        partita_id = values[0]
        
        try:
            success, partita_data = self.partita_manager.esporta_partita_json(partita_id)
            
            if success:
                # Mostra i dettagli in una nuova finestra
                details_window = tk.Toplevel(self.root)
                details_window.title(f"Dettagli Partita {values[2]} ({values[1]})")
                details_window.geometry("800x600")
                
                ttk.Label(details_window, text=f"Dettagli Partita {values[2]}", font=("Helvetica", 12)).pack(pady=10)
                
                # Area di testo per i dettagli
                details_text = scrolledtext.ScrolledText(details_window, width=80, height=30)
                details_text.pack(expand=True, fill="both", padx=10, pady=10)
                
                # Formatta il JSON per la visualizzazione
                formatted_json = json.dumps(partita_data, indent=2, ensure_ascii=False)
                details_text.insert("1.0", formatted_json)
                details_text.config(state=tk.DISABLED)
                
                # Pulsante di chiusura
                ttk.Button(details_window, text="Chiudi", command=details_window.destroy).pack(pady=10)
            else:
                messagebox.showerror("Errore", partita_data)
        
        except Exception as e:
            messagebox.showerror("Errore", str(e))
    
    def generate_partita_certificato(self):
        """Genera un certificato di proprietà per la partita selezionata"""
        selected_items = self.partite_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.partite_tree.item(item, "values")
        
        partita_id = values[0]
        
        try:
            success, certificato = self.partita_manager.genera_certificato_proprieta(partita_id)
            
            if success:
                # Mostra il certificato in una nuova finestra
                cert_window = tk.Toplevel(self.root)
                cert_window.title(f"Certificato Partita {values[2]} ({values[1]})")
                cert_window.geometry("800x600")
                
                ttk.Label(cert_window, text=f"Certificato di Proprietà", font=("Helvetica", 12)).pack(pady=10)
                
                # Area di testo per il certificato
                cert_text = scrolledtext.ScrolledText(cert_window, width=80, height=30, font=("Courier", 10))
                cert_text.pack(expand=True, fill="both", padx=10, pady=10)
                cert_text.insert("1.0", certificato)
                cert_text.config(state=tk.DISABLED)
                
                # Pulsanti
                buttons_frame = ttk.Frame(cert_window)
                buttons_frame.pack(pady=10)
                
                def salva_certificato():
                    file_path = tk.filedialog.asksaveasfilename(
                        defaultextension=".txt",
                        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                        initialfile=f"certificato_{values[1]}_{values[2]}.txt"
                    )
                    if file_path:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(certificato)
                        messagebox.showinfo("Salvato", f"Certificato salvato in {file_path}")
                
                ttk.Button(buttons_frame, text="Salva", command=salva_certificato).pack(side=tk.LEFT, padx=5)
                ttk.Button(buttons_frame, text="Chiudi", command=cert_window.destroy).pack(side=tk.LEFT, padx=5)
            else:
                messagebox.showerror("Errore", certificato)
        
        except Exception as e:
            messagebox.showerror("Errore", str(e))
    
    def generate_partita_report(self):
        """Genera un report genealogico per la partita selezionata"""
        selected_items = self.partite_tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.partite_tree.item(item, "values")
        
        partita_id = values[0]
        
        try:
            success, report = self.partita_manager.genera_report_genealogico(partita_id)
            
            if success:
                # Mostra il report in una nuova finestra
                report_window = tk.Toplevel(self.root)
                report_window.title(f"Report Genealogico Partita {values[2]} ({values[1]})")
                report_window.geometry("800x600")
                
                ttk.Label(report_window, text=f"Report Genealogico", font=("Helvetica", 12)).pack(pady=10)
                
                # Area di testo per il report
                report_text = scrolledtext.ScrolledText(report_window, width=80, height=30, font=("Courier", 10))
                report_text.pack(expand=True, fill="both", padx=10, pady=10)
                report_text.insert("1.0", report)
                report_text.config(state=tk.DISABLED)
                
                # Pulsanti
                buttons_frame = ttk.Frame(report_window)
                buttons_frame.pack(pady=10)
                
                def salva_report():
                    file_path = tk.filedialog.asksaveasfilename(
                        defaultextension=".txt",
                        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                        initialfile=f"report_{values[1]}_{values[2]}.txt"
                    )
                    if file_path:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(report)
                        messagebox.showinfo("Salvato", f"Report salvato in {file_path}")
                
                ttk.Button(buttons_frame, text="Salva", command=salva_report).pack(side=tk.LEFT, padx=5)
                ttk.Button(buttons_frame, text="Chiudi", command=report_window.destroy).pack(side=tk.LEFT, padx=5)
            else:
                messagebox.showerror("Errore", report)
        
        except Exception as e:
            messagebox.showerror("Errore", str(e))
    
    def show_duplica_partita(self):
        """Mostra la finestra per duplicare una partita"""
        duplica_window = tk.Toplevel(self.root)
        duplica_window.title("Duplica Partita")
        duplica_window.geometry("400x300")
        duplica_window.grab_set()
        
        ttk.Label(duplica_window, text="Duplicazione Partita", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(duplica_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # ID Partita da duplicare
        ttk.Label(form_frame, text="ID Partita da duplicare:").grid(row=0, column=0, sticky=tk.W, pady=5)
        partita_id_entry = ttk.Entry(form_frame, width=30)
        partita_id_entry.grid(row=0, column=1, pady=5)
        
        # Nuovo numero partita
        ttk.Label(form_frame, text="Nuovo numero partita:").grid(row=1, column=0, sticky=tk.W, pady=5)
        nuovo_numero_entry = ttk.Entry(form_frame, width=30)
        nuovo_numero_entry.grid(row=1, column=1, pady=5)
        
        # Opzioni
        ttk.Label(form_frame, text="Opzioni:").grid(row=2, column=0, sticky=tk.W, pady=5)
        options_frame = ttk.Frame(form_frame)
        options_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        mantenere_possessori_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Mantenere possessori", variable=mantenere_possessori_var).pack(anchor=tk.W)
        
        mantenere_immobili_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Mantenere immobili", variable=mantenere_immobili_var).pack(anchor=tk.W)
        
        def duplica():
            try:
                partita_id = partita_id_entry.get()
                nuovo_numero = nuovo_numero_entry.get()
                
                if not partita_id or not nuovo_numero:
                    messagebox.showerror("Errore", "I campi ID Partita e Nuovo numero partita sono obbligatori")
                    return
                
                try:
                    partita_id = int(partita_id)
                    nuovo_numero = int(nuovo_numero)
                except ValueError:
                    messagebox.showerror("Errore", "ID Partita e Nuovo numero partita devono essere numeri interi")
                    return
                
                mantenere_possessori = mantenere_possessori_var.get()
                mantenere_immobili = mantenere_immobili_var.get()
                
                success, message = self.partita_manager.duplica_partita(
                    partita_id, nuovo_numero, mantenere_possessori, mantenere_immobili)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    duplica_window.destroy()
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(duplica_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Duplica", command=duplica).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=duplica_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_genera_certificato(self):
        """Mostra la finestra per generare un certificato di proprietà"""
        certificato_window = tk.Toplevel(self.root)
        certificato_window.title("Genera Certificato")
        certificato_window.geometry("400x200")
        certificato_window.grab_set()
        
        ttk.Label(certificato_window, text="Generazione Certificato di Proprietà", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(certificato_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # ID Partita
        ttk.Label(form_frame, text="ID Partita:").grid(row=0, column=0, sticky=tk.W, pady=5)
        partita_id_entry = ttk.Entry(form_frame, width=30)
        partita_id_entry.grid(row=0, column=1, pady=5)
        
        def genera():
            try:
                partita_id = partita_id_entry.get()
                
                if not partita_id:
                    messagebox.showerror("Errore", "Il campo ID Partita è obbligatorio")
                    return
                
                try:
                    partita_id = int(partita_id)
                except ValueError:
                    messagebox.showerror("Errore", "ID Partita deve essere un numero intero")
                    return
                
                success, certificato = self.partita_manager.genera_certificato_proprieta(partita_id)
                
                if success:
                    certificato_window.destroy()
                    
                    # Mostra il certificato in una nuova finestra
                    display_window = tk.Toplevel(self.root)
                    display_window.title("Certificato di Proprietà")
                    display_window.geometry("800x600")
                    
                    ttk.Label(display_window, text="Certificato di Proprietà", font=("Helvetica", 12)).pack(pady=10)
                    
                    # Area di testo per il certificato
                    cert_text = scrolledtext.ScrolledText(display_window, width=80, height=30, font=("Courier", 10))
                    cert_text.pack(expand=True, fill="both", padx=10, pady=10)
                    cert_text.insert("1.0", certificato)
                    cert_text.config(state=tk.DISABLED)
                    
                    # Pulsanti
                    buttons_frame = ttk.Frame(display_window)
                    buttons_frame.pack(pady=10)
                    
                    def salva_certificato():
                        file_path = tk.filedialog.asksaveasfilename(
                            defaultextension=".txt",
                            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                            initialfile=f"certificato_partita_{partita_id}.txt"
                        )
                        if file_path:
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(certificato)
                            messagebox.showinfo("Salvato", f"Certificato salvato in {file_path}")
                    
                    ttk.Button(buttons_frame, text="Salva", command=salva_certificato).pack(side=tk.LEFT, padx=5)
                    ttk.Button(buttons_frame, text="Chiudi", command=display_window.destroy).pack(side=tk.LEFT, padx=5)
                else:
                    messagebox.showerror("Errore", certificato)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(certificato_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Genera", command=genera).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=certificato_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_genera_report_genealogico(self):
        """Mostra la finestra per generare un report genealogico"""
        report_window = tk.Toplevel(self.root)
        report_window.title("Genera Report Genealogico")
        report_window.geometry("400x200")
        report_window.grab_set()
        
        ttk.Label(report_window, text="Generazione Report Genealogico", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(report_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # ID Partita
        ttk.Label(form_frame, text="ID Partita:").grid(row=0, column=0, sticky=tk.W, pady=5)
        partita_id_entry = ttk.Entry(form_frame, width=30)
        partita_id_entry.grid(row=0, column=1, pady=5)
        
        def genera():
            try:
                partita_id = partita_id_entry.get()
                
                if not partita_id:
                    messagebox.showerror("Errore", "Il campo ID Partita è obbligatorio")
                    return
                
                try:
                    partita_id = int(partita_id)
                except ValueError:
                    messagebox.showerror("Errore", "ID Partita deve essere un numero intero")
                    return
                
                success, report = self.partita_manager.genera_report_genealogico(partita_id)
                
                if success:
                    report_window.destroy()
                    
                    # Mostra il report in una nuova finestra
                    display_window = tk.Toplevel(self.root)
                    display_window.title("Report Genealogico")
                    display_window.geometry("800x600")
                    
                    ttk.Label(display_window, text="Report Genealogico", font=("Helvetica", 12)).pack(pady=10)
                    
                    # Area di testo per il report
                    report_text = scrolledtext.ScrolledText(display_window, width=80, height=30, font=("Courier", 10))
                    report_text.pack(expand=True, fill="both", padx=10, pady=10)
                    report_text.insert("1.0", report)
                    report_text.config(state=tk.DISABLED)
                    
                    # Pulsanti
                    buttons_frame = ttk.Frame(display_window)
                    buttons_frame.pack(pady=10)
                    
                    def salva_report():
                        file_path = tk.filedialog.asksaveasfilename(
                            defaultextension=".txt",
                            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                            initialfile=f"report_genealogico_partita_{partita_id}.txt"
                        )
                        if file_path:
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(report)
                            messagebox.showinfo("Salvato", f"Report salvato in {file_path}")
                    
                    ttk.Button(buttons_frame, text="Salva", command=salva_report).pack(side=tk.LEFT, padx=5)
                    ttk.Button(buttons_frame, text="Chiudi", command=display_window.destroy).pack(side=tk.LEFT, padx=5)
                else:
                    messagebox.showerror("Errore", report)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(report_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Genera", command=genera).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=report_window.destroy).pack(side=tk.LEFT, padx=5)
    
    # Implementazione dei metodi per le funzionalità di Workflow
    def show_registra_nuova_proprieta(self):
        """Mostra la finestra per registrare una nuova proprietà completa"""
        proprieta_window = tk.Toplevel(self.root)
        proprieta_window.title("Registra Nuova Proprietà")
        proprieta_window.geometry("800x600")
        proprieta_window.grab_set()
        
        ttk.Label(proprieta_window, text="Registrazione Nuova Proprietà", font=("Helvetica", 12)).pack(pady=10)
        
        # Crea un notebook per organizzare i vari elementi del form
        notebook = ttk.Notebook(proprieta_window)
        notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Scheda informazioni partita
        partita_frame = ttk.Frame(notebook, padding="10")
        notebook.add(partita_frame, text="Informazioni Partita")
        
        # Comune
        ttk.Label(partita_frame, text="Comune:").grid(row=0, column=0, sticky=tk.W, pady=5)
        comune_entry = ttk.Entry(partita_frame, width=30)
        comune_entry.grid(row=0, column=1, pady=5)
        
        # Numero partita
        ttk.Label(partita_frame, text="Numero partita:").grid(row=1, column=0, sticky=tk.W, pady=5)
        numero_entry = ttk.Entry(partita_frame, width=30)
        numero_entry.grid(row=1, column=1, pady=5)
        
        # Data impianto
        ttk.Label(partita_frame, text="Data impianto:").grid(row=2, column=0, sticky=tk.W, pady=5)
        data_entry = ttk.Entry(partita_frame, width=30)
        data_entry.grid(row=2, column=1, pady=5)
        data_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        
        # Scheda possessori
        possessori_frame = ttk.Frame(notebook, padding="10")
        notebook.add(possessori_frame, text="Possessori")
        
        ttk.Label(possessori_frame, text="Aggiungi i possessori per questa proprietà", font=("Helvetica", 10)).pack(pady=5)
        
        # Lista possessori
        possessori_list_frame = ttk.Frame(possessori_frame)
        possessori_list_frame.pack(expand=True, fill="both", pady=10)
        
        possessori_list = ttk.Treeview(possessori_list_frame, columns=("Nome", "Paternità", "Quota"), height=10)
        possessori_list.heading("#0", text="")
        possessori_list.column("#0", width=0, stretch=tk.NO)
        possessori_list.heading("Nome", text="Nome completo")
        possessori_list.column("Nome", width=200)
        possessori_list.heading("Paternità", text="Paternità")
        possessori_list.column("Paternità", width=150)
        possessori_list.heading("Quota", text="Quota")
        possessori_list.column("Quota", width=80)
        
        scrollbar = ttk.Scrollbar(possessori_list_frame, orient="vertical", command=possessori_list.yview)
        possessori_list.configure(yscrollcommand=scrollbar.set)
        
        possessori_list.pack(side=tk.LEFT, expand=True, fill="both")
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        # Form per aggiungere possessori
        add_possessore_frame = ttk.LabelFrame(possessori_frame, text="Aggiungi Possessore")
        add_possessore_frame.pack(pady=10, fill="x")
        
        ttk.Label(add_possessore_frame, text="Nome completo:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        nome_completo_entry = ttk.Entry(add_possessore_frame, width=30)
        nome_completo_entry.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(add_possessore_frame, text="Cognome e nome:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)
        cognome_nome_entry = ttk.Entry(add_possessore_frame, width=30)
        cognome_nome_entry.grid(row=0, column=3, pady=5, padx=5)
        
        ttk.Label(add_possessore_frame, text="Paternità:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        paternita_entry = ttk.Entry(add_possessore_frame, width=30)
        paternita_entry.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(add_possessore_frame, text="Quota:").grid(row=1, column=2, sticky=tk.W, pady=5, padx=5)
        quota_entry = ttk.Entry(add_possessore_frame, width=30)
        quota_entry.grid(row=1, column=3, pady=5, padx=5)
        
        def add_possessore():
            nome_completo = nome_completo_entry.get()
            cognome_nome = cognome_nome_entry.get()
            paternita = paternita_entry.get()
            quota = quota_entry.get()
            
            if not nome_completo or not cognome_nome:
                messagebox.showerror("Errore", "I campi Nome completo e Cognome e nome sono obbligatori")
                return
            
            # Aggiunge alla lista
            possessori_list.insert("", tk.END, values=(nome_completo, paternita, quota), 
                                   tags=("possessore", json.dumps({
                                       "nome_completo": nome_completo,
                                       "cognome_nome": cognome_nome,
                                       "paternita": paternita,
                                       "quota": quota
                                   })))
            
            # Pulisce i campi
            nome_completo_entry.delete(0, tk.END)
            cognome_nome_entry.delete(0, tk.END)
            paternita_entry.delete(0, tk.END)
            quota_entry.delete(0, tk.END)
        
        def remove_possessore():
            selected = possessori_list.selection()
            if selected:
                for item in selected:
                    possessori_list.delete(item)
        
        buttons_possessori_frame = ttk.Frame(add_possessore_frame)
        buttons_possessori_frame.grid(row=2, column=0, columnspan=4, pady=10)
        
        ttk.Button(buttons_possessori_frame, text="Aggiungi", command=add_possessore).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_possessori_frame, text="Rimuovi selezionati", command=remove_possessore).pack(side=tk.LEFT, padx=5)
        
        # Scheda immobili
        immobili_frame = ttk.Frame(notebook, padding="10")
        notebook.add(immobili_frame, text="Immobili")
        
        ttk.Label(immobili_frame, text="Aggiungi gli immobili per questa proprietà", font=("Helvetica", 10)).pack(pady=5)
        
        # Lista immobili
        immobili_list_frame = ttk.Frame(immobili_frame)
        immobili_list_frame.pack(expand=True, fill="both", pady=10)
        
        immobili_list = ttk.Treeview(immobili_list_frame, columns=("Natura", "Località", "Tipo", "Classificazione"), height=10)
        immobili_list.heading("#0", text="")
        immobili_list.column("#0", width=0, stretch=tk.NO)
        immobili_list.heading("Natura", text="Natura")
        immobili_list.column("Natura", width=150)
        immobili_list.heading("Località", text="Località")
        immobili_list.column("Località", width=150)
        immobili_list.heading("Tipo", text="Tipo Località")
        immobili_list.column("Tipo", width=100)
        immobili_list.heading("Classificazione", text="Classificazione")
        immobili_list.column("Classificazione", width=150)
        
        scrollbar_imm = ttk.Scrollbar(immobili_list_frame, orient="vertical", command=immobili_list.yview)
        immobili_list.configure(yscrollcommand=scrollbar_imm.set)
        
        immobili_list.pack(side=tk.LEFT, expand=True, fill="both")
        scrollbar_imm.pack(side=tk.RIGHT, fill="y")
        
        # Form per aggiungere immobili
        add_immobile_frame = ttk.LabelFrame(immobili_frame, text="Aggiungi Immobile")
        add_immobile_frame.pack(pady=10, fill="x")
        
        ttk.Label(add_immobile_frame, text="Natura:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        natura_entry = ttk.Entry(add_immobile_frame, width=30)
        natura_entry.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(add_immobile_frame, text="Località:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)
        localita_entry = ttk.Entry(add_immobile_frame, width=30)
        localita_entry.grid(row=0, column=3, pady=5, padx=5)
        
        ttk.Label(add_immobile_frame, text="Tipo località:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        tipo_localita_var = tk.StringVar()
        tipo_localita_combo = ttk.Combobox(add_immobile_frame, textvariable=tipo_localita_var, width=28)
        tipo_localita_combo["values"] = ("regione", "via", "borgata")
        tipo_localita_combo.grid(row=1, column=1, pady=5, padx=5)
        tipo_localita_combo.current(0)
        
        ttk.Label(add_immobile_frame, text="Classificazione:").grid(row=1, column=2, sticky=tk.W, pady=5, padx=5)
        classificazione_entry = ttk.Entry(add_immobile_frame, width=30)
        classificazione_entry.grid(row=1, column=3, pady=5, padx=5)
        
        ttk.Label(add_immobile_frame, text="Numero piani:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        piani_entry = ttk.Entry(add_immobile_frame, width=30)
        piani_entry.grid(row=2, column=1, pady=5, padx=5)
        
        ttk.Label(add_immobile_frame, text="Numero vani:").grid(row=2, column=2, sticky=tk.W, pady=5, padx=5)
        vani_entry = ttk.Entry(add_immobile_frame, width=30)
        vani_entry.grid(row=2, column=3, pady=5, padx=5)
        
        ttk.Label(add_immobile_frame, text="Consistenza:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        consistenza_entry = ttk.Entry(add_immobile_frame, width=30)
        consistenza_entry.grid(row=3, column=1, pady=5, padx=5)
        
        def add_immobile():
            natura = natura_entry.get()
            localita = localita_entry.get()
            tipo_localita = tipo_localita_var.get()
            classificazione = classificazione_entry.get()
            piani = piani_entry.get()
            vani = vani_entry.get()
            consistenza = consistenza_entry.get()
            
            if not natura or not localita:
                messagebox.showerror("Errore", "I campi Natura e Località sono obbligatori")
                return
            
            # Converte i numeri
            try:
                piani = int(piani) if piani else None
                vani = int(vani) if vani else None
            except ValueError:
                messagebox.showerror("Errore", "Numero piani e Numero vani devono essere numeri interi")
                return
            
            # Aggiunge alla lista
            immobili_list.insert("", tk.END, values=(natura, localita, tipo_localita, classificazione), 
                               tags=("immobile", json.dumps({
                                   "natura": natura,
                                   "localita": localita,
                                   "tipo_localita": tipo_localita,
                                   "classificazione": classificazione,
                                   "numero_piani": piani,
                                   "numero_vani": vani,
                                   "consistenza": consistenza
                               })))
            
            # Pulisce i campi
            natura_entry.delete(0, tk.END)
            localita_entry.delete(0, tk.END)
            classificazione_entry.delete(0, tk.END)
            piani_entry.delete(0, tk.END)
            vani_entry.delete(0, tk.END)
            consistenza_entry.delete(0, tk.END)
        
        def remove_immobile():
            selected = immobili_list.selection()
            if selected:
                for item in selected:
                    immobili_list.delete(item)
        
        buttons_immobili_frame = ttk.Frame(add_immobile_frame)
        buttons_immobili_frame.grid(row=4, column=0, columnspan=4, pady=10)
        
        ttk.Button(buttons_immobili_frame, text="Aggiungi", command=add_immobile).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_immobili_frame, text="Rimuovi selezionati", command=remove_immobile).pack(side=tk.LEFT, padx=5)
        
        # Pulsanti principali
        buttons_frame = ttk.Frame(proprieta_window)
        buttons_frame.pack(pady=10)
        
        def registra_proprieta():
            try:
                # Recupera i dati della partita
                comune = comune_entry.get()
                numero_partita = numero_entry.get()
                data_impianto = data_entry.get()
                
                if not comune or not numero_partita or not data_impianto:
                    messagebox.showerror("Errore", "I campi Comune, Numero partita e Data impianto sono obbligatori")
                    return
                
                try:
                    numero_partita = int(numero_partita)
                except ValueError:
                    messagebox.showerror("Errore", "Numero partita deve essere un numero intero")
                    return
                
                # Recupera i possessori
                possessori = []
                for item_id in possessori_list.get_children():
                    item_tags = possessori_list.item(item_id, "tags")
                    if item_tags and len(item_tags) > 1:
                        possessore_data = json.loads(item_tags[1])
                        possessori.append(possessore_data)
                
                if not possessori:
                    messagebox.showerror("Errore", "È necessario inserire almeno un possessore")
                    return
                
                # Recupera gli immobili
                immobili = []
                for item_id in immobili_list.get_children():
                    item_tags = immobili_list.item(item_id, "tags")
                    if item_tags and len(item_tags) > 1:
                        immobile_data = json.loads(item_tags[1])
                        immobili.append(immobile_data)
                
                if not immobili:
                    messagebox.showerror("Errore", "È necessario inserire almeno un immobile")
                    return
                
                # Registra la nuova proprietà
                success, message = self.workflow_manager.registra_nuova_proprieta(
                    comune, numero_partita, data_impianto, possessori, immobili)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    proprieta_window.destroy()
                    
                    # Aggiorna i log
                    self.add_to_log(f"Registrata nuova proprietà: Partita {numero_partita} del comune {comune}")
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        ttk.Button(buttons_frame, text="Registra Proprietà", command=registra_proprieta).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=proprieta_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_registra_passaggio_proprieta(self):
        """Mostra la finestra per registrare un passaggio di proprietà"""
        passaggio_window = tk.Toplevel(self.root)
        passaggio_window.title("Registra Passaggio Proprietà")
        passaggio_window.geometry("800x600")
        passaggio_window.grab_set()
        
        ttk.Label(passaggio_window, text="Registrazione Passaggio di Proprietà", font=("Helvetica", 12)).pack(pady=10)
        
        # Crea un notebook per organizzare i vari elementi del form
        notebook = ttk.Notebook(passaggio_window)
        notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Scheda partite
        partite_frame = ttk.Frame(notebook, padding="10")
        notebook.add(partite_frame, text="Partite")
        
        # Partita di origine
        partita_origine_frame = ttk.LabelFrame(partite_frame, text="Partita di Origine")
        partita_origine_frame.pack(fill="x", pady=10)
        
        ttk.Label(partita_origine_frame, text="ID Partita origine:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        partita_origine_id_entry = ttk.Entry(partita_origine_frame, width=30)
        partita_origine_id_entry.grid(row=0, column=1, pady=5, padx=5)
        
        # Nuova partita
        nuova_partita_frame = ttk.LabelFrame(partite_frame, text="Nuova Partita")
        nuova_partita_frame.pack(fill="x", pady=10)
        
        ttk.Label(nuova_partita_frame, text="Comune:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        comune_entry = ttk.Entry(nuova_partita_frame, width=30)
        comune_entry.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(nuova_partita_frame, text="Numero partita:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        numero_entry = ttk.Entry(nuova_partita_frame, width=30)
        numero_entry.grid(row=1, column=1, pady=5, padx=5)
        
        # Scheda variazione
        variazione_frame = ttk.Frame(notebook, padding="10")
        notebook.add(variazione_frame, text="Variazione")
        
        # Dati variazione
        dati_variazione_frame = ttk.LabelFrame(variazione_frame, text="Dati Variazione")
        dati_variazione_frame.pack(fill="x", pady=10)
        
        ttk.Label(dati_variazione_frame, text="Tipo variazione:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        tipo_variazione_var = tk.StringVar()
        tipo_variazione_combo = ttk.Combobox(dati_variazione_frame, textvariable=tipo_variazione_var, width=28)
        tipo_variazione_combo["values"] = ("Acquisto", "Successione", "Variazione", "Frazionamento", "Divisione")
        tipo_variazione_combo.grid(row=0, column=1, pady=5, padx=5)
        tipo_variazione_combo.current(0)
        
        ttk.Label(dati_variazione_frame, text="Data variazione:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        data_variazione_entry = ttk.Entry(dati_variazione_frame, width=30)
        data_variazione_entry.grid(row=1, column=1, pady=5, padx=5)
        data_variazione_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        
        # Dati contratto
        dati_contratto_frame = ttk.LabelFrame(variazione_frame, text="Dati Contratto")
        dati_contratto_frame.pack(fill="x", pady=10)
        
        ttk.Label(dati_contratto_frame, text="Tipo contratto:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        tipo_contratto_var = tk.StringVar()
        tipo_contratto_combo = ttk.Combobox(dati_contratto_frame, textvariable=tipo_contratto_var, width=28)
        tipo_contratto_combo["values"] = ("Vendita", "Divisione", "Successione", "Donazione")
        tipo_contratto_combo.grid(row=0, column=1, pady=5, padx=5)
        tipo_contratto_combo.current(0)
        
        ttk.Label(dati_contratto_frame, text="Data contratto:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        data_contratto_entry = ttk.Entry(dati_contratto_frame, width=30)
        data_contratto_entry.grid(row=1, column=1, pady=5, padx=5)
        data_contratto_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        
        ttk.Label(dati_contratto_frame, text="Notaio:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        notaio_entry = ttk.Entry(dati_contratto_frame, width=30)
        notaio_entry.grid(row=2, column=1, pady=5, padx=5)
        
        ttk.Label(dati_contratto_frame, text="Repertorio:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        repertorio_entry = ttk.Entry(dati_contratto_frame, width=30)
        repertorio_entry.grid(row=3, column=1, pady=5, padx=5)
        
        ttk.Label(dati_contratto_frame, text="Note:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        note_text = tk.Text(dati_contratto_frame, width=30, height=3)
        note_text.grid(row=4, column=1, pady=5, padx=5)
        
        # Scheda possessori
        possessori_frame = ttk.Frame(notebook, padding="10")
        notebook.add(possessori_frame, text="Nuovi Possessori")
        
        ttk.Label(possessori_frame, text="Nuovi possessori (lasciare vuoto per mantenere gli stessi)", 
                 font=("Helvetica", 10)).pack(pady=5)
        
        # Lista possessori
        possessori_list_frame = ttk.Frame(possessori_frame)
        possessori_list_frame.pack(expand=True, fill="both", pady=10)
        
        possessori_list = ttk.Treeview(possessori_list_frame, columns=("Nome", "Paternità"), height=10)
        possessori_list.heading("#0", text="")
        possessori_list.column("#0", width=0, stretch=tk.NO)
        possessori_list.heading("Nome", text="Nome completo")
        possessori_list.column("Nome", width=200)
        possessori_list.heading("Paternità", text="Paternità")
        possessori_list.column("Paternità", width=150)
        
        scrollbar = ttk.Scrollbar(possessori_list_frame, orient="vertical", command=possessori_list.yview)
        possessori_list.configure(yscrollcommand=scrollbar.set)
        
        possessori_list.pack(side=tk.LEFT, expand=True, fill="both")
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        # Form per aggiungere possessori
        add_possessore_frame = ttk.LabelFrame(possessori_frame, text="Aggiungi Possessore")
        add_possessore_frame.pack(pady=10, fill="x")
        
        ttk.Label(add_possessore_frame, text="Nome completo:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        nome_completo_entry = ttk.Entry(add_possessore_frame, width=30)
        nome_completo_entry.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(add_possessore_frame, text="Cognome e nome:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)
        cognome_nome_entry = ttk.Entry(add_possessore_frame, width=30)
        cognome_nome_entry.grid(row=0, column=3, pady=5, padx=5)
        
        ttk.Label(add_possessore_frame, text="Paternità:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        paternita_entry = ttk.Entry(add_possessore_frame, width=30)
        paternita_entry.grid(row=1, column=1, pady=5, padx=5)
        
        def add_possessore():
            nome_completo = nome_completo_entry.get()
            cognome_nome = cognome_nome_entry.get()
            paternita = paternita_entry.get()
            
            if not nome_completo or not cognome_nome:
                messagebox.showerror("Errore", "I campi Nome completo e Cognome e nome sono obbligatori")
                return
            
            # Aggiunge alla lista
            possessori_list.insert("", tk.END, values=(nome_completo, paternita), 
                                 tags=("possessore", json.dumps({
                                     "nome_completo": nome_completo,
                                     "cognome_nome": cognome_nome,
                                     "paternita": paternita
                                 })))
            
            # Pulisce i campi
            nome_completo_entry.delete(0, tk.END)
            cognome_nome_entry.delete(0, tk.END)
            paternita_entry.delete(0, tk.END)
        
        def remove_possessore():
            selected = possessori_list.selection()
            if selected:
                for item in selected:
                    possessori_list.delete(item)
        
        buttons_possessori_frame = ttk.Frame(add_possessore_frame)
        buttons_possessori_frame.grid(row=2, column=0, columnspan=4, pady=10)
        
        ttk.Button(buttons_possessori_frame, text="Aggiungi", command=add_possessore).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_possessori_frame, text="Rimuovi selezionati", command=remove_possessore).pack(side=tk.LEFT, padx=5)
        
        # Scheda immobili
        immobili_frame = ttk.Frame(notebook, padding="10")
        notebook.add(immobili_frame, text="Immobili")
        
        ttk.Label(immobili_frame, text="Immobili da trasferire (lasciare vuoto per trasferire tutti gli immobili)", 
                font=("Helvetica", 10)).pack(pady=5)
        
        # Frame per la selezione
        selection_frame = ttk.Frame(immobili_frame)
        selection_frame.pack(fill="x", pady=10)
        
        ttk.Label(selection_frame, text="ID Partita origine:").pack(side=tk.LEFT, padx=5)
        view_partita_id_entry = ttk.Entry(selection_frame, width=10)
        view_partita_id_entry.pack(side=tk.LEFT, padx=5)
        
        def view_immobili():
            partita_id = view_partita_id_entry.get()
            if not partita_id:
                messagebox.showerror("Errore", "Inserire l'ID della partita")
                return
            
            try:
                partita_id = int(partita_id)
            except ValueError:
                messagebox.showerror("Errore", "ID Partita deve essere un numero intero")
                return
            
            try:
                # Costruisci la query per ottenere gli immobili
                query = "SELECT i.id, i.natura, l.nome AS localita_nome, i.classificazione "
                query += "FROM catasto.immobile i "
                query += "JOIN catasto.localita l ON i.localita_id = l.id "
                query += "WHERE i.partita_id = %s"
                
                self.db_manager.execute(query, [partita_id])
                results = self.db_manager.cur.fetchall()
                
                # Pulisce la lista immobili
                for item in immobili_list.get_children():
                    immobili_list.delete(item)
                
                # Popola la lista immobili
                for row in results:
                    immobili_list.insert("", tk.END, values=(
                        row["id"], row["natura"], row["localita_nome"], row["classificazione"]
                    ))
                
                # Aggiorna l'entry della partita origine
                partita_origine_id_entry.delete(0, tk.END)
                partita_origine_id_entry.insert(0, partita_id)
                
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        ttk.Button(selection_frame, text="Visualizza Immobili", command=view_immobili).pack(side=tk.LEFT, padx=5)
        
        # Lista immobili
        immobili_list_frame = ttk.Frame(immobili_frame)
        immobili_list_frame.pack(expand=True, fill="both", pady=10)
        
        immobili_list = ttk.Treeview(immobili_list_frame, columns=("ID", "Natura", "Località", "Classificazione"), height=10)
        immobili_list.heading("#0", text="")
        immobili_list.column("#0", width=0, stretch=tk.NO)
        immobili_list.heading("ID", text="ID")
        immobili_list.column("ID", width=50)
        immobili_list.heading("Natura", text="Natura")
        immobili_list.column("Natura", width=150)
        immobili_list.heading("Località", text="Località")
        immobili_list.column("Località", width=150)
        immobili_list.heading("Classificazione", text="Classificazione")
        immobili_list.column("Classificazione", width=150)
        
        scrollbar_imm = ttk.Scrollbar(immobili_list_frame, orient="vertical", command=immobili_list.yview)
        immobili_list.configure(yscrollcommand=scrollbar_imm.set)
        
        immobili_list.pack(side=tk.LEFT, expand=True, fill="both")
        scrollbar_imm.pack(side=tk.RIGHT, fill="y")
        
        selected_immobili_var = tk.StringVar(value="tutti")
        
        ttk.Radiobutton(immobili_frame, text="Trasferire tutti gli immobili", 
                      variable=selected_immobili_var, value="tutti").pack(anchor=tk.W, pady=5)
        ttk.Radiobutton(immobili_frame, text="Trasferire solo gli immobili selezionati", 
                      variable=selected_immobili_var, value="selezionati").pack(anchor=tk.W, pady=5)
        
        # Pulsanti principali
        buttons_frame = ttk.Frame(passaggio_window)
        buttons_frame.pack(pady=10)
        
        def registra_passaggio():
            try:
                # Recupera i dati della partita
                partita_origine_id = partita_origine_id_entry.get()
                comune = comune_entry.get()
                numero_partita = numero_entry.get()
                
                if not partita_origine_id or not comune or not numero_partita:
                    messagebox.showerror("Errore", "I campi ID Partita origine, Comune e Numero partita sono obbligatori")
                    return
                
                try:
                    partita_origine_id = int(partita_origine_id)
                    numero_partita = int(numero_partita)
                except ValueError:
                    messagebox.showerror("Errore", "ID Partita origine e Numero partita devono essere numeri interi")
                    return
                
                # Recupera i dati della variazione
                tipo_variazione = tipo_variazione_var.get()
                data_variazione = data_variazione_entry.get()
                tipo_contratto = tipo_contratto_var.get()
                data_contratto = data_contratto_entry.get()
                notaio = notaio_entry.get()
                repertorio = repertorio_entry.get()
                note = note_text.get("1.0", tk.END).strip()
                
                if not data_variazione or not tipo_contratto or not data_contratto:
                    messagebox.showerror("Errore", "I campi Data variazione, Tipo contratto e Data contratto sono obbligatori")
                    return
                
                # Recupera i nuovi possessori (se presenti)
                nuovi_possessori = None
                if possessori_list.get_children():
                    nuovi_possessori = []
                    for item_id in possessori_list.get_children():
                        item_tags = possessori_list.item(item_id, "tags")
                        if item_tags and len(item_tags) > 1:
                            possessore_data = json.loads(item_tags[1])
                            nuovi_possessori.append(possessore_data)
                
                # Recupera gli immobili da trasferire (se selezionati)
                immobili_da_trasferire = None
                if selected_immobili_var.get() == "selezionati":
                    selected_immobili = immobili_list.selection()
                    if selected_immobili:
                        immobili_da_trasferire = []
                        for item in selected_immobili:
                            values = immobili_list.item(item, "values")
                            immobili_da_trasferire.append(int(values[0]))
                
                # Registra il passaggio di proprietà
                success, message = self.workflow_manager.registra_passaggio_proprieta(
                    partita_origine_id, comune, numero_partita, tipo_variazione, data_variazione,
                    tipo_contratto, data_contratto, notaio, repertorio, nuovi_possessori,
                    immobili_da_trasferire, note)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    passaggio_window.destroy()
                    
                    # Aggiorna i log
                    self.add_to_log(f"Registrato passaggio di proprietà: Partita {partita_origine_id} -> {numero_partita}")
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        ttk.Button(buttons_frame, text="Registra Passaggio", command=registra_passaggio).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=passaggio_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_registra_frazionamento(self):
        """Mostra la finestra per registrare un frazionamento di proprietà"""
        frazionamento_window = tk.Toplevel(self.root)
        frazionamento_window.title("Registra Frazionamento")
        frazionamento_window.geometry("800x600")
        frazionamento_window.grab_set()
        
        ttk.Label(frazionamento_window, text="Registrazione Frazionamento", font=("Helvetica", 12)).pack(pady=10)
        
        # Crea un notebook per organizzare i vari elementi del form
        notebook = ttk.Notebook(frazionamento_window)
        notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Scheda partita origine
        origine_frame = ttk.Frame(notebook, padding="10")
        notebook.add(origine_frame, text="Partita Origine")
        
        # Partita di origine
        partita_origine_frame = ttk.LabelFrame(origine_frame, text="Partita di Origine")
        partita_origine_frame.pack(fill="x", pady=10)
        
        ttk.Label(partita_origine_frame, text="ID Partita origine:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        partita_origine_id_entry = ttk.Entry(partita_origine_frame, width=30)
        partita_origine_id_entry.grid(row=0, column=1, pady=5, padx=5)
        
        # Immobili della partita origine
        immobili_frame = ttk.LabelFrame(origine_frame, text="Immobili")
        immobili_frame.pack(fill="both", expand=True, pady=10)
        
        def view_immobili():
            partita_id = partita_origine_id_entry.get()
            if not partita_id:
                messagebox.showerror("Errore", "Inserire l'ID della partita")
                return
            
            try:
                partita_id = int(partita_id)
            except ValueError:
                messagebox.showerror("Errore", "ID Partita deve essere un numero intero")
                return
            
            try:
                # Costruisci la query per ottenere gli immobili
                query = "SELECT i.id, i.natura, l.nome AS localita_nome, i.classificazione "
                query += "FROM catasto.immobile i "
                query += "JOIN catasto.localita l ON i.localita_id = l.id "
                query += "WHERE i.partita_id = %s"
                
                self.db_manager.execute(query, [partita_id])
                results = self.db_manager.cur.fetchall()
                
                # Pulisce la lista immobili
                for item in immobili_list.get_children():
                    immobili_list.delete(item)
                
                # Popola la lista immobili
                for row in results:
                    immobili_list.insert("", tk.END, values=(
                        row["id"], row["natura"], row["localita_nome"], row["classificazione"]
                    ))
                
                # Costruisci la query per ottenere i possessori
                query = "SELECT pos.id, pos.nome_completo "
                query += "FROM catasto.possessore pos "
                query += "JOIN catasto.partita_possessore pp ON pos.id = pp.possessore_id "
                query += "WHERE pp.partita_id = %s"
                
                self.db_manager.execute(query, [partita_id])
                results = self.db_manager.cur.fetchall()
                
                # Salva i possessori per usarli nelle nuove partite
                self.possessori_origine = {row["id"]: row["nome_completo"] for row in results}
                
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        ttk.Button(partita_origine_frame, text="Visualizza Immobili", command=view_immobili).grid(row=0, column=2, padx=5)
        
        # Lista immobili
        immobili_list_frame = ttk.Frame(immobili_frame)
        immobili_list_frame.pack(expand=True, fill="both", pady=10)
        
        immobili_list = ttk.Treeview(immobili_list_frame, columns=("ID", "Natura", "Località", "Classificazione"), height=10)
        immobili_list.heading("#0", text="")
        immobili_list.column("#0", width=0, stretch=tk.NO)
        immobili_list.heading("ID", text="ID")
        immobili_list.column("ID", width=50)
        immobili_list.heading("Natura", text="Natura")
        immobili_list.column("Natura", width=150)
        immobili_list.heading("Località", text="Località")
        immobili_list.column("Località", width=150)
        immobili_list.heading("Classificazione", text="Classificazione")
        immobili_list.column("Classificazione", width=150)
        
        scrollbar = ttk.Scrollbar(immobili_list_frame, orient="vertical", command=immobili_list.yview)
        immobili_list.configure(yscrollcommand=scrollbar.set)
        
        immobili_list.pack(side=tk.LEFT, expand=True, fill="both")
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        # Scheda variazione
        variazione_frame = ttk.Frame(notebook, padding="10")
        notebook.add(variazione_frame, text="Variazione")
        
        # Dati variazione
        dati_variazione_frame = ttk.LabelFrame(variazione_frame, text="Dati Variazione")
        dati_variazione_frame.pack(fill="x", pady=10)
        
        ttk.Label(dati_variazione_frame, text="Data variazione:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        data_variazione_entry = ttk.Entry(dati_variazione_frame, width=30)
        data_variazione_entry.grid(row=0, column=1, pady=5, padx=5)
        data_variazione_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        
        # Dati contratto
        dati_contratto_frame = ttk.LabelFrame(variazione_frame, text="Dati Contratto")
        dati_contratto_frame.pack(fill="x", pady=10)
        
        ttk.Label(dati_contratto_frame, text="Tipo contratto:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        tipo_contratto_var = tk.StringVar()
        tipo_contratto_combo = ttk.Combobox(dati_contratto_frame, textvariable=tipo_contratto_var, width=28)
        tipo_contratto_combo["values"] = ("Vendita", "Divisione", "Successione", "Donazione")
        tipo_contratto_combo.grid(row=0, column=1, pady=5, padx=5)
        tipo_contratto_combo.current(0)
        
        ttk.Label(dati_contratto_frame, text="Data contratto:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        data_contratto_entry = ttk.Entry(dati_contratto_frame, width=30)
        data_contratto_entry.grid(row=1, column=1, pady=5, padx=5)
        data_contratto_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        
        ttk.Label(dati_contratto_frame, text="Notaio:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        notaio_entry = ttk.Entry(dati_contratto_frame, width=30)
        notaio_entry.grid(row=2, column=1, pady=5, padx=5)
        
        ttk.Label(dati_contratto_frame, text="Repertorio:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        repertorio_entry = ttk.Entry(dati_contratto_frame, width=30)
        repertorio_entry.grid(row=3, column=1, pady=5, padx=5)
        
        ttk.Label(dati_contratto_frame, text="Note:").grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        note_text = tk.Text(dati_contratto_frame, width=30, height=3)
        note_text.grid(row=4, column=1, pady=5, padx=5)
        
        # Scheda nuove partite
        nuove_partite_frame = ttk.Frame(notebook, padding="10")
        notebook.add(nuove_partite_frame, text="Nuove Partite")
        
        ttk.Label(nuove_partite_frame, text="Definizione delle nuove partite", font=("Helvetica", 10)).pack(pady=5)
        
        # Lista nuove partite
        partite_list_frame = ttk.Frame(nuove_partite_frame)
        partite_list_frame.pack(expand=True, fill="both", pady=10)
        
        partite_list = ttk.Treeview(partite_list_frame, columns=("Numero", "Comune", "Possessori", "Immobili"), height=8)
        partite_list.heading("#0", text="")
        partite_list.column("#0", width=0, stretch=tk.NO)
        partite_list.heading("Numero", text="Numero Partita")
        partite_list.column("Numero", width=100)
        partite_list.heading("Comune", text="Comune")
        partite_list.column("Comune", width=150)
        partite_list.heading("Possessori", text="Possessori")
        partite_list.column("Possessori", width=200)
        partite_list.heading("Immobili", text="Immobili")
        partite_list.column("Immobili", width=200)
        
        scrollbar = ttk.Scrollbar(partite_list_frame, orient="vertical", command=partite_list.yview)
        partite_list.configure(yscrollcommand=scrollbar.set)
        
        partite_list.pack(side=tk.LEFT, expand=True, fill="both")
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        # Form per aggiungere nuove partite
        add_partita_frame = ttk.LabelFrame(nuove_partite_frame, text="Aggiungi Nuova Partita")
        add_partita_frame.pack(pady=10, fill="x")
        
        ttk.Label(add_partita_frame, text="Numero partita:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        numero_partita_entry = ttk.Entry(add_partita_frame, width=20)
        numero_partita_entry.grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(add_partita_frame, text="Comune:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)
        comune_entry = ttk.Entry(add_partita_frame, width=20)
        comune_entry.grid(row=0, column=3, pady=5, padx=5)
        
        # Selezione possessori
        possessori_frame = ttk.LabelFrame(add_partita_frame, text="Possessori")
        possessori_frame.grid(row=1, column=0, columnspan=4, pady=5, padx=5, sticky=tk.W+tk.E)
        
        self.possessori_origine = {}  # Sarà popolato quando si visualizzano gli immobili
        self.selected_possessori_ids = []
        
        def show_possessori_selection():
            if not self.possessori_origine:
                messagebox.showinfo("Info", "Prima visualizza gli immobili della partita origine")
                return
            
            selection_window = tk.Toplevel(frazionamento_window)
            selection_window.title("Seleziona Possessori")
            selection_window.geometry("400x300")
            selection_window.grab_set()
            
            ttk.Label(selection_window, text="Seleziona i possessori", font=("Helvetica", 10)).pack(pady=10)
            
            possessori_listbox = tk.Listbox(selection_window, selectmode=tk.MULTIPLE, height=10)
            possessori_listbox.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Popola la listbox
            for pid, nome in self.possessori_origine.items():
                possessori_listbox.insert(tk.END, f"{pid}: {nome}")
            
            def confirm_selection():
                selected_indices = possessori_listbox.curselection()
                if not selected_indices:
                    messagebox.showerror("Errore", "Seleziona almeno un possessore")
                    return
                
                self.selected_possessori_ids = []
                for i in selected_indices:
                    item_text = possessori_listbox.get(i)
                    pid = int(item_text.split(":")[0])
                    self.selected_possessori_ids.append(pid)
                
                # Aggiorna l'etichetta
                possessori_names = [self.possessori_origine[pid] for pid in self.selected_possessori_ids]
                possessori_label.config(text="Possessori selezionati: " + ", ".join(possessori_names))
                
                selection_window.destroy()
            
            ttk.Button(selection_window, text="Conferma", command=confirm_selection).pack(pady=10)
        
        ttk.Button(possessori_frame, text="Seleziona Possessori", command=show_possessori_selection).pack(pady=5)
        possessori_label = ttk.Label(possessori_frame, text="Nessun possessore selezionato")
        possessori_label.pack(pady=5)
        
        # Selezione immobili
        immobili_sel_frame = ttk.LabelFrame(add_partita_frame, text="Immobili")
        immobili_sel_frame.grid(row=2, column=0, columnspan=4, pady=5, padx=5, sticky=tk.W+tk.E)
        
        self.selected_immobili_ids = []
        
        def show_immobili_selection():
            if not immobili_list.get_children():
                messagebox.showinfo("Info", "Prima visualizza gli immobili della partita origine")
                return
            
            selection_window = tk.Toplevel(frazionamento_window)
            selection_window.title("Seleziona Immobili")
            selection_window.geometry("600x400")
            selection_window.grab_set()
            
            ttk.Label(selection_window, text="Seleziona gli immobili", font=("Helvetica", 10)).pack(pady=10)
            
            immobili_sel_tree = ttk.Treeview(selection_window, 
                                           columns=("ID", "Natura", "Località", "Classificazione"), 
                                           height=10, selectmode="extended")
            immobili_sel_tree.heading("#0", text="")
            immobili_sel_tree.column("#0", width=0, stretch=tk.NO)
            immobili_sel_tree.heading("ID", text="ID")
            immobili_sel_tree.column("ID", width=50)
            immobili_sel_tree.heading("Natura", text="Natura")
            immobili_sel_tree.column("Natura", width=150)
            immobili_sel_tree.heading("Località", text="Località")
            immobili_sel_tree.column("Località", width=150)
            immobili_sel_tree.heading("Classificazione", text="Classificazione")
            immobili_sel_tree.column("Classificazione", width=150)
            
            scrollbar = ttk.Scrollbar(selection_window, orient="vertical", command=immobili_sel_tree.yview)
            immobili_sel_tree.configure(yscrollcommand=scrollbar.set)
            
            immobili_sel_tree.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
            scrollbar.pack(side=tk.RIGHT, fill="y", pady=10)
            
            # Popola il treeview con gli immobili
            for item_id in immobili_list.get_children():
                values = immobili_list.item(item_id, "values")
                immobili_sel_tree.insert("", tk.END, values=values)
            
            def confirm_selection():
                selected_items = immobili_sel_tree.selection()
                if not selected_items:
                    messagebox.showerror("Errore", "Seleziona almeno un immobile")
                    return
                
                self.selected_immobili_ids = []
                immobili_desc = []
                for item in selected_items:
                    values = immobili_sel_tree.item(item, "values")
                    self.selected_immobili_ids.append(int(values[0]))
                    immobili_desc.append(f"{values[1]} in {values[2]}")
                
                # Aggiorna l'etichetta
                if len(immobili_desc) > 3:
                    immobili_text = ", ".join(immobili_desc[:3]) + f" e altri {len(immobili_desc) - 3}"
                else:
                    immobili_text = ", ".join(immobili_desc)
                immobili_label.config(text="Immobili selezionati: " + immobili_text)
                
                selection_window.destroy()
            
            ttk.Button(selection_window, text="Conferma", command=confirm_selection).pack(pady=10)
        
        ttk.Button(immobili_sel_frame, text="Seleziona Immobili", command=show_immobili_selection).pack(pady=5)
        immobili_label = ttk.Label(immobili_sel_frame, text="Nessun immobile selezionato")
        immobili_label.pack(pady=5)
        
        def add_partita():
            numero_partita = numero_partita_entry.get()
            comune = comune_entry.get()
            
            if not numero_partita or not comune:
                messagebox.showerror("Errore", "I campi Numero partita e Comune sono obbligatori")
                return
            
            if not self.selected_possessori_ids:
                messagebox.showerror("Errore", "Seleziona almeno un possessore")
                return
            
            if not self.selected_immobili_ids:
                messagebox.showerror("Errore", "Seleziona almeno un immobile")
                return
            
            try:
                numero_partita = int(numero_partita)
            except ValueError:
                messagebox.showerror("Errore", "Numero partita deve essere un numero intero")
                return
            
            # Aggiunge alla lista
            possessori_names = [self.possessori_origine[pid] for pid in self.selected_possessori_ids]
            if len(possessori_names) > 2:
                possessori_text = ", ".join(possessori_names[:2]) + f" e altri {len(possessori_names) - 2}"
            else:
                possessori_text = ", ".join(possessori_names)
            
            immobili_count = len(self.selected_immobili_ids)
            immobili_text = f"{immobili_count} immobili"
            
            partite_list.insert("", tk.END, values=(numero_partita, comune, possessori_text, immobili_text), 
                               tags=("partita", json.dumps({
                                   "numero_partita": numero_partita,
                                   "comune": comune,
                                   "possessori": [{"id": pid} for pid in self.selected_possessori_ids],
                                   "immobili": self.selected_immobili_ids
                               })))
            
            # Pulisce i campi
            numero_partita_entry.delete(0, tk.END)
            comune_entry.delete(0, tk.END)
            self.selected_possessori_ids = []
            self.selected_immobili_ids = []
            possessori_label.config(text="Nessun possessore selezionato")
            immobili_label.config(text="Nessun immobile selezionato")
        
        def remove_partita():
            selected = partite_list.selection()
            if selected:
                for item in selected:
                    partite_list.delete(item)
        
        buttons_partita_frame = ttk.Frame(add_partita_frame)
        buttons_partita_frame.grid(row=3, column=0, columnspan=4, pady=10)
        
        ttk.Button(buttons_partita_frame, text="Aggiungi Partita", command=add_partita).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_partita_frame, text="Rimuovi Selezionate", command=remove_partita).pack(side=tk.LEFT, padx=5)
        
        # Pulsanti principali
        buttons_frame = ttk.Frame(frazionamento_window)
        buttons_frame.pack(pady=10)
        
        def registra_frazionamento():
            try:
                # Recupera i dati della partita origine
                partita_origine_id = partita_origine_id_entry.get()
                
                if not partita_origine_id:
                    messagebox.showerror("Errore", "Il campo ID Partita origine è obbligatorio")
                    return
                
                try:
                    partita_origine_id = int(partita_origine_id)
                except ValueError:
                    messagebox.showerror("Errore", "ID Partita origine deve essere un numero intero")
                    return
                
                # Recupera i dati della variazione
                data_variazione = data_variazione_entry.get()
                tipo_contratto = tipo_contratto_var.get()
                data_contratto = data_contratto_entry.get()
                notaio = notaio_entry.get()
                repertorio = repertorio_entry.get()
                note = note_text.get("1.0", tk.END).strip()
                
                if not data_variazione or not tipo_contratto or not data_contratto:
                    messagebox.showerror("Errore", "I campi Data variazione, Tipo contratto e Data contratto sono obbligatori")
                    return
                
                # Recupera le nuove partite
                if not partite_list.get_children():
                    messagebox.showerror("Errore", "È necessario definire almeno una nuova partita")
                    return
                
                nuove_partite = []
                for item_id in partite_list.get_children():
                    item_tags = partite_list.item(item_id, "tags")
                    if item_tags and len(item_tags) > 1:
                        partita_data = json.loads(item_tags[1])
                        nuove_partite.append(partita_data)
                
                # Registra il frazionamento
                success, message = self.workflow_manager.registra_frazionamento(
                    partita_origine_id, data_variazione, tipo_contratto, data_contratto,
                    nuove_partite, notaio, repertorio, note)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    frazionamento_window.destroy()
                    
                    # Aggiorna i log
                    self.add_to_log(f"Registrato frazionamento della partita {partita_origine_id} in {len(nuove_partite)} nuove partite")
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        ttk.Button(buttons_frame, text="Registra Frazionamento", command=registra_frazionamento).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=frazionamento_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def verifica_integrita_database(self):
        """Verifica l'integrità del database"""
        try:
            success, message = self.workflow_manager.verifica_integrita_database()
            if success:
                self.add_to_log("Verifica integrità database completata.")
                messagebox.showinfo("Verifica integrità", message)
            else:
                self.add_to_log("Errore durante la verifica dell'integrità: " + message)
                messagebox.showerror("Errore", message)
        except Exception as e:
            self.add_to_log("Errore durante la verifica dell'integrità: " + str(e))
            messagebox.showerror("Errore", str(e))
    
    def ripara_problemi_database(self):
        """Ripara i problemi di integrità del database"""
        if messagebox.askyesno("Riparazione database", 
                            "Sei sicuro di voler eseguire la riparazione automatica del database?"):
            try:
                success, message = self.workflow_manager.ripara_problemi_database(True)
                if success:
                    self.add_to_log("Riparazione database completata.")
                    messagebox.showinfo("Riparazione database", message)
                else:
                    self.add_to_log("Errore durante la riparazione: " + message)
                    messagebox.showerror("Errore", message)
            except Exception as e:
                self.add_to_log("Errore durante la riparazione: " + str(e))
                messagebox.showerror("Errore", str(e))
    
    def show_backup_logico_dati(self):
        """Mostra la finestra per eseguire un backup logico dei dati"""
        backup_window = tk.Toplevel(self.root)
        backup_window.title("Backup Logico Dati")
        backup_window.geometry("400x300")
        backup_window.grab_set()
        
        ttk.Label(backup_window, text="Backup Logico Dati", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(backup_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # Directory
        ttk.Label(form_frame, text="Directory di destinazione:").grid(row=0, column=0, sticky=tk.W, pady=5)
        directory_entry = ttk.Entry(form_frame, width=30)
        directory_entry.grid(row=0, column=1, pady=5)
        directory_entry.insert(0, "/tmp")
        
        def select_directory():
            directory = tk.filedialog.askdirectory()
            if directory:
                directory_entry.delete(0, tk.END)
                directory_entry.insert(0, directory)
        
        ttk.Button(form_frame, text="Sfoglia", command=select_directory).grid(row=0, column=2, padx=5)
        
        # Prefisso file
        ttk.Label(form_frame, text="Prefisso file:").grid(row=1, column=0, sticky=tk.W, pady=5)
        prefisso_entry = ttk.Entry(form_frame, width=30)
        prefisso_entry.grid(row=1, column=1, pady=5)
        prefisso_entry.insert(0, "catasto_backup")
        
        def esegui_backup():
            try:
                directory = directory_entry.get()
                prefisso = prefisso_entry.get()
                
                if not directory or not prefisso:
                    messagebox.showerror("Errore", "I campi Directory e Prefisso sono obbligatori")
                    return
                
                success, message = self.workflow_manager.backup_logico_dati(directory, prefisso)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    backup_window.destroy()
                    
                    # Aggiorna i log
                    self.add_to_log(f"Backup logico dati pianificato in {directory} con prefisso {prefisso}")
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(backup_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Esegui Backup", command=esegui_backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=backup_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_sincronizza_archivio(self):
        """Mostra la finestra per sincronizzare una partita con l'Archivio di Stato"""
        sync_window = tk.Toplevel(self.root)
        sync_window.title("Sincronizzazione Archivio di Stato")
        sync_window.geometry("400x300")
        sync_window.grab_set()
        
        ttk.Label(sync_window, text="Sincronizzazione con Archivio di Stato", font=("Helvetica", 12)).pack(pady=10)
        
        form_frame = ttk.Frame(sync_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        
        # ID Partita
        ttk.Label(form_frame, text="ID Partita:").grid(row=0, column=0, sticky=tk.W, pady=5)
        partita_id_entry = ttk.Entry(form_frame, width=30)
        partita_id_entry.grid(row=0, column=1, pady=5)
        
        # Riferimento archivio
        ttk.Label(form_frame, text="Riferimento archivio:").grid(row=1, column=0, sticky=tk.W, pady=5)
        riferimento_entry = ttk.Entry(form_frame, width=30)
        riferimento_entry.grid(row=1, column=1, pady=5)
        
        # Data sincronizzazione
        ttk.Label(form_frame, text="Data sincronizzazione:").grid(row=2, column=0, sticky=tk.W, pady=5)
        data_entry = ttk.Entry(form_frame, width=30)
        data_entry.grid(row=2, column=1, pady=5)
        data_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        
        def sincronizza():
            try:
                partita_id = partita_id_entry.get()
                riferimento = riferimento_entry.get()
                data = data_entry.get()
                
                if not partita_id or not riferimento:
                    messagebox.showerror("Errore", "I campi ID Partita e Riferimento archivio sono obbligatori")
                    return
                
                try:
                    partita_id = int(partita_id)
                except ValueError:
                    messagebox.showerror("Errore", "ID Partita deve essere un numero intero")
                    return
                
                success, message = self.workflow_manager.sincronizza_con_archivio_stato(
                    partita_id, riferimento, data if data else None)
                
                if success:
                    messagebox.showinfo("Successo", message)
                    sync_window.destroy()
                    
                    # Aggiorna i log
                    self.add_to_log(f"Sincronizzata partita {partita_id} con Archivio di Stato: {riferimento}")
                else:
                    messagebox.showerror("Errore", message)
            
            except Exception as e:
                messagebox.showerror("Errore", str(e))
        
        buttons_frame = ttk.Frame(sync_window)
        buttons_frame.pack(pady=10)
        
        ttk.Button(buttons_frame, text="Sincronizza", command=sincronizza).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Annulla", command=sync_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def add_to_log(self, message):
        """Aggiunge un messaggio al log"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def show_help(self):
        """Mostra la guida dell'applicazione"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Guida")
        help_window.geometry("600x400")
        
        ttk.Label(help_window, text="Guida di Gestione Catasto Storico", font=("Helvetica", 12)).pack(pady=10)
        
        help_text = scrolledtext.ScrolledText(help_window, width=70, height=20)
        help_text.pack(expand=True, fill="both", padx=10, pady=10)
        
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

Per ulteriori informazioni, consultare la documentazione completa o contattare l'amministratore del sistema.
        """
        
        help_text.insert("1.0", guide)
        help_text.config(state=tk.DISABLED)
        
        ttk.Button(help_window, text="Chiudi", command=help_window.destroy).pack(pady=10)
    
    def show_about(self):
        """Mostra informazioni sull'applicazione"""
        messagebox.showinfo("Informazioni", 
                          "Gestione Catasto Storico\nVersione 1.0\n\n"
                          "Applicazione per la gestione del database del Catasto Storico anni '50\n"
                          "Sviluppata con Python e Tkinter\n\n"
                          "© 2025 - Tutti i diritti riservati")

# Funzione principale
def main():
    root = tk.Tk()
    app = CatastoApp(root)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

def on_closing():
    if messagebox.askokcancel("Chiudi", "Sei sicuro di voler chiudere l'applicazione?"):
        # Chiudi la connessione al database se aperta
        for window in tk.Tk.winfo_children(tk._default_root):
            if isinstance(window, tk.Toplevel):
                window.destroy()
        
        tk._default_root.destroy()

if __name__ == "__main__":
    main()
