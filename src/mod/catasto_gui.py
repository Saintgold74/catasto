import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
# Nuova importazione per il calendario
try:
    from tkcalendar import DateEntry
except ImportError:
    messagebox.showerror("Errore Dipendenza", "La libreria 'tkcalendar' non è installata.\nEsegui 'pip install tkcalendar' dal terminale.")
    sys.exit(1) # Esce se manca la dipendenza

from catasto_db_manager import CatastoDBManager
from datetime import date, datetime
import json
import sys


# --- Classe Principale dell'Applicazione GUI ---
class CatastoApp(tk.Tk):
    def __init__(self, db_config):
        super().__init__()
        self.title("Gestore Catasto Storico")
        self.geometry("850x650") # Aumentate leggermente le dimensioni

        # --- Connessione al Database ---
        self.db_manager = CatastoDBManager(**db_config)
        if not self.db_manager.connect():
            messagebox.showerror("Errore Database", "Impossibile connettersi al database.\nVerifica i parametri di connessione e che il server PostgreSQL sia in esecuzione.")
            self.destroy()
            return

        # --- Creazione Interfaccia a Schede (Tabs) ---
        self.notebook = ttk.Notebook(self)

        self.tab_consultazione = self.crea_tab_consultazione()
        self.tab_inserimento = self.crea_tab_inserimento()
        self.tab_report = self.crea_tab_report()
        self.tab_manutenzione = self.crea_tab_manutenzione()

        self.notebook.add(self.tab_consultazione, text="Consultazione")
        self.notebook.add(self.tab_inserimento, text="Inserimento/Gestione")
        self.notebook.add(self.tab_report, text="Report")
        self.notebook.add(self.tab_manutenzione, text="Manutenzione")

        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        if messagebox.askokcancel("Esci", "Vuoi chiudere l'applicazione?"):
            self.db_manager.disconnect()
            self.destroy()

    # --- Metodi per Creare le Singole Schede (Consultazione, Report, Manutenzione - invariati) ---

    def crea_tab_consultazione(self):
        """ Crea la scheda 'Consultazione Dati'. (Invariata) """
        tab = ttk.Frame(self.notebook)
        tab.columnconfigure(1, weight=1) # Colonna 1 si espande

        # --- Elenco Comuni ---
        ttk.Label(tab, text="Elenco Comuni:", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.comuni_search_entry = ttk.Entry(tab, width=30)
        self.comuni_search_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        ttk.Button(tab, text="Cerca Comuni", command=self.visualizza_comuni).grid(row=0, column=2, padx=5, pady=5)

        # --- Elenco Partite per Comune ---
        ttk.Label(tab, text="Partite per Comune:", font=('Arial', 10, 'bold')).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.partite_comune_entry = ttk.Entry(tab, width=30)
        self.partite_comune_entry.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        ttk.Button(tab, text="Cerca Partite", command=self.visualizza_partite_comune).grid(row=1, column=2, padx=5, pady=5)

        # --- Elenco Possessori per Comune ---
        ttk.Label(tab, text="Possessori per Comune:", font=('Arial', 10, 'bold')).grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.possessori_comune_entry = ttk.Entry(tab, width=30)
        self.possessori_comune_entry.grid(row=2, column=1, padx=5, pady=5, sticky='ew')
        ttk.Button(tab, text="Cerca Possessori", command=self.visualizza_possessori_comune).grid(row=2, column=2, padx=5, pady=5)

        # --- Ricerca Partite Avanzata ---
        ttk.Label(tab, text="Ricerca Partite Avanzata:", font=('Arial', 10, 'bold')).grid(row=3, column=0, columnspan=3, padx=5, pady=(15, 5), sticky='w')
        search_frame = ttk.LabelFrame(tab, text="Criteri")
        search_frame.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky='ew')
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="Comune:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.search_comune_entry = ttk.Entry(search_frame)
        self.search_comune_entry.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(search_frame, text="Num. Partita:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.search_numero_entry = ttk.Entry(search_frame)
        self.search_numero_entry.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(search_frame, text="Possessore:").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.search_possessore_entry = ttk.Entry(search_frame)
        self.search_possessore_entry.grid(row=2, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(search_frame, text="Natura Imm.:").grid(row=3, column=0, padx=5, pady=2, sticky='w')
        self.search_natura_entry = ttk.Entry(search_frame)
        self.search_natura_entry.grid(row=3, column=1, padx=5, pady=2, sticky='ew')

        ttk.Button(search_frame, text="Esegui Ricerca", command=self.esegui_ricerca_partite).grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        # --- Dettagli Partita ---
        ttk.Label(tab, text="Dettagli Partita (ID):", font=('Arial', 10, 'bold')).grid(row=5, column=0, padx=5, pady=(15, 5), sticky='w')
        self.dettagli_id_entry = ttk.Entry(tab, width=10)
        self.dettagli_id_entry.grid(row=5, column=1, padx=5, pady=(15, 5), sticky='w')
        ttk.Button(tab, text="Mostra Dettagli", command=self.visualizza_dettagli_partita).grid(row=5, column=2, padx=5, pady=(15, 5))

        # --- Area Risultati ---
        ttk.Label(tab, text="Risultati:", font=('Arial', 10, 'bold')).grid(row=6, column=0, columnspan=3, padx=5, pady=5, sticky='w')
        self.consultazione_results_text = scrolledtext.ScrolledText(tab, height=15, width=80, wrap=tk.WORD)
        self.consultazione_results_text.grid(row=7, column=0, columnspan=3, padx=5, pady=5, sticky='nsew')
        tab.rowconfigure(7, weight=1) # L'area testo si espande

        return tab

    def crea_tab_report(self):
        """ Crea la scheda 'Generazione Report'. (Invariata) """
        tab = ttk.Frame(self.notebook)
        tab.columnconfigure(1, weight=1) # Colonna 1 (area testo) si espande

        # --- Selezione Report ---
        report_frame = ttk.LabelFrame(tab, text="Seleziona Report")
        report_frame.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        ttk.Label(report_frame, text="Tipo Report:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.report_type_var = tk.StringVar()
        report_combobox = ttk.Combobox(report_frame, textvariable=self.report_type_var,
                                       values=["Certificato Proprietà", "Report Genealogico", "Report Possessore"],
                                       state="readonly")
        report_combobox.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        report_combobox.current(0) # Seleziona il primo elemento

        ttk.Label(report_frame, text="ID Partita/Possessore:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.report_id_entry = ttk.Entry(report_frame, width=10)
        self.report_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        ttk.Button(report_frame, text="Genera Report", command=self.genera_report).grid(row=2, column=0, columnspan=2, pady=10)

        # --- Area Visualizzazione Report ---
        ttk.Label(tab, text="Report Generato:", font=('Arial', 10, 'bold')).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.report_text_area = scrolledtext.ScrolledText(tab, height=20, width=80, wrap=tk.WORD)
        self.report_text_area.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='nsew')
        tab.rowconfigure(2, weight=1) # Area testo si espande
        tab.columnconfigure(0, weight=1) # Colonna 0 si espande

        return tab

    def crea_tab_manutenzione(self):
        """ Crea la scheda 'Manutenzione Database'. (Invariata) """
        tab = ttk.Frame(self.notebook)

        ttk.Button(tab, text="Verifica Integrità Database", command=self.verifica_integrita).pack(padx=20, pady=20)

        self.manutenzione_results_text = scrolledtext.ScrolledText(tab, height=10, width=70, wrap=tk.WORD)
        self.manutenzione_results_text.pack(padx=20, pady=10, expand=True, fill='both')

        return tab


    # --- Metodi per Creare le Singole Schede (Inserimento - MODIFICATO) ---

    def crea_tab_inserimento(self):
        """ Crea la scheda 'Inserimento e Gestione Dati'. (MODIFICATO)"""
        tab = ttk.Frame(self.notebook)
        tab.columnconfigure(1, weight=1)

        # --- Aggiungi Comune ---
        comune_frame = ttk.LabelFrame(tab, text="Aggiungi Nuovo Comune")
        comune_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
        comune_frame.columnconfigure(1, weight=1)

        ttk.Label(comune_frame, text="Nome:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.comune_nome_entry = ttk.Entry(comune_frame)
        self.comune_nome_entry.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(comune_frame, text="Provincia:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.comune_provincia_entry = ttk.Entry(comune_frame)
        self.comune_provincia_entry.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(comune_frame, text="Regione:").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.comune_regione_entry = ttk.Entry(comune_frame)
        self.comune_regione_entry.grid(row=2, column=1, padx=5, pady=2, sticky='ew')

        ttk.Button(comune_frame, text="Aggiungi Comune", command=self.aggiungi_comune).grid(row=3, column=0, columnspan=2, pady=5)

        # --- Aggiungi Possessore ---
        poss_frame = ttk.LabelFrame(tab, text="Aggiungi Nuovo Possessore")
        poss_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=10, sticky='ew')
        poss_frame.columnconfigure(1, weight=1)

        ttk.Label(poss_frame, text="Comune:").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.poss_comune_entry = ttk.Entry(poss_frame)
        self.poss_comune_entry.grid(row=0, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(poss_frame, text="Cognome e Nome:").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.poss_cognome_nome_entry = ttk.Entry(poss_frame)
        self.poss_cognome_nome_entry.grid(row=1, column=1, padx=5, pady=2, sticky='ew')

        ttk.Label(poss_frame, text="Paternità:").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.poss_paternita_entry = ttk.Entry(poss_frame)
        self.poss_paternita_entry.grid(row=2, column=1, padx=5, pady=2, sticky='ew')
        ttk.Label(poss_frame, text="(es. 'fu Roberto')").grid(row=2, column=2, padx=5, pady=2, sticky='w')

        ttk.Label(poss_frame, text="Nome Completo:").grid(row=3, column=0, padx=5, pady=2, sticky='w')
        self.poss_nome_completo_entry = ttk.Entry(poss_frame)
        self.poss_nome_completo_entry.grid(row=3, column=1, padx=5, pady=2, sticky='ew')
        ttk.Label(poss_frame, text="(opzionale, calcolato se vuoto)").grid(row=3, column=2, padx=5, pady=2, sticky='w')

        ttk.Button(poss_frame, text="Aggiungi Possessore", command=self.aggiungi_possessore).grid(row=4, column=0, columnspan=3, pady=5)

        # --- Pulsanti per Funzionalità Complesse ---
        action_frame = ttk.LabelFrame(tab, text="Operazioni Complesse")
        action_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky='ew')

        # Abilita i pulsanti e collega ai metodi per aprire le finestre Toplevel
        ttk.Button(action_frame, text="Registra Nuova Proprietà", command=self.open_registra_nuova_proprieta_window).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(action_frame, text="Registra Passaggio Proprietà", command=self.open_registra_passaggio_window).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(action_frame, text="Registra Consultazione", command=self.open_registra_consultazione_window).pack(side=tk.LEFT, padx=10, pady=10)

        return tab

    # --- Metodi Callback per le Azioni GUI (Consultazione - invariati) ---
    def _display_results(self, data, title):
        """ Funzione helper per mostrare risultati nell'area testo della consultazione. (Invariata) """
        self.consultazione_results_text.delete('1.0', tk.END) # Pulisce l'area
        self.consultazione_results_text.insert(tk.END, f"--- {title} ---\n\n")
        if not data:
            self.consultazione_results_text.insert(tk.END, "Nessun risultato trovato.")
            return

        if isinstance(data, str): # Per i report
             self.consultazione_results_text.insert(tk.END, data)
             return

        if isinstance(data, dict): # Per dettagli partita
            for key, value in data.items():
                 if isinstance(value, list) and key in ['possessori', 'immobili', 'variazioni']: # Gestisce liste note
                     self.consultazione_results_text.insert(tk.END, f"{key.replace('_', ' ').title()}:\n")
                     if value:
                         for item in value:
                            # Tenta di formattare l'item come dizionario, altrimenti lo mostra come stringa
                            try:
                                item_str = ", ".join(f"{k}: {v}" for k, v in item.items() if v is not None)
                                self.consultazione_results_text.insert(tk.END, f"  - {item_str}\n")
                            except AttributeError:
                                self.consultazione_results_text.insert(tk.END, f"  - {item}\n") # Se non è un dict (es. lista ID immobili)
                     else:
                         self.consultazione_results_text.insert(tk.END, "  Nessuno\n")
                     self.consultazione_results_text.insert(tk.END, "\n")
                 else:
                     self.consultazione_results_text.insert(tk.END, f"{key.replace('_', ' ').title()}: {value}\n")
            return

        # Per liste di risultati (comuni, partite, possessori)
        if isinstance(data, list) and data:
             # Assicurati che il primo elemento sia un dizionario per ottenere gli header
             if isinstance(data[0], dict):
                 headers = list(data[0].keys())
                 # Calcola larghezze colonne (semplice)
                 widths = {h: max(len(h), max((len(str(row.get(h,''))) for row in data), default=0)) for h in headers}
                 header_line = " | ".join(f"{h:<{widths[h]}}" for h in headers)
                 separator = "-+-".join("-" * widths[h] for h in headers)

                 self.consultazione_results_text.insert(tk.END, header_line + "\n")
                 self.consultazione_results_text.insert(tk.END, separator + "\n")
                 for row in data:
                     row_values = [str(row.get(h, '')) for h in headers]
                     row_line = " | ".join(f"{val:<{widths[h]}}" for h, val in zip(headers, row_values))
                     self.consultazione_results_text.insert(tk.END, row_line + "\n")
             else: # Se la lista non contiene dizionari
                 for item in data:
                     self.consultazione_results_text.insert(tk.END, f"{item}\n")

    def visualizza_comuni(self):
        search_term = self.comuni_search_entry.get()
        try:
            comuni = self.db_manager.get_comuni(search_term if search_term else None)
            self._display_results(comuni, f"Elenco Comuni (Ricerca: '{search_term}')")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la ricerca comuni:\n{e}")

    def visualizza_partite_comune(self):
        comune = self.partite_comune_entry.get()
        if not comune:
            messagebox.showwarning("Input Mancante", "Inserire il nome del comune.")
            return
        try:
            partite = self.db_manager.get_partite_by_comune(comune)
            self._display_results(partite, f"Partite del Comune '{comune}'")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la ricerca partite:\n{e}")

    def visualizza_possessori_comune(self):
        comune = self.possessori_comune_entry.get()
        if not comune:
            messagebox.showwarning("Input Mancante", "Inserire il nome del comune.")
            return
        try:
            possessori = self.db_manager.get_possessori_by_comune(comune)
            self._display_results(possessori, f"Possessori del Comune '{comune}'")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la ricerca possessori:\n{e}")

    def esegui_ricerca_partite(self):
        comune = self.search_comune_entry.get()
        numero_str = self.search_numero_entry.get()
        possessore = self.search_possessore_entry.get()
        natura = self.search_natura_entry.get()

        numero_partita = None
        if numero_str:
            try:
                numero_partita = int(numero_str)
            except ValueError:
                messagebox.showerror("Input Errato", "Il numero partita deve essere un intero.")
                return

        try:
            partite = self.db_manager.search_partite(
                comune_nome=comune if comune else None,
                numero_partita=numero_partita,
                possessore=possessore if possessore else None,
                immobile_natura=natura if natura else None
            )
            self._display_results(partite, "Risultati Ricerca Partite Avanzata")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la ricerca avanzata:\n{e}")

    def visualizza_dettagli_partita(self):
        partita_id_str = self.dettagli_id_entry.get()
        if not partita_id_str:
            messagebox.showwarning("Input Mancante", "Inserire l'ID della partita.")
            return

        try:
            partita_id = int(partita_id_str)
            partita = self.db_manager.get_partita_details(partita_id)
            if partita:
                self._display_results(partita, f"Dettagli Partita ID {partita_id}")
            else:
                 self._display_results(None, f"Dettagli Partita ID {partita_id}")
                 messagebox.showinfo("Risultato", f"Nessuna partita trovata con ID {partita_id}.")
        except ValueError:
            messagebox.showerror("Input Errato", "L'ID partita deve essere un numero intero.")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante il recupero dei dettagli:\n{e}")

    # --- Metodi Callback per le Azioni GUI (Inserimento - invariati) ---

    def aggiungi_comune(self):
        nome = self.comune_nome_entry.get().strip()
        provincia = self.comune_provincia_entry.get().strip()
        regione = self.comune_regione_entry.get().strip()

        if not nome or not provincia or not regione:
            messagebox.showwarning("Dati Mancanti", "Inserire nome, provincia e regione del comune.")
            return

        try:
            if self.db_manager.execute_query(
                "INSERT INTO comune (nome, provincia, regione) VALUES (%s, %s, %s) ON CONFLICT (nome) DO NOTHING",
                (nome, provincia, regione)
            ):
                self.db_manager.commit()
                messagebox.showinfo("Successo", f"Comune '{nome}' inserito con successo o già esistente.")
                self.comune_nome_entry.delete(0, tk.END)
                self.comune_provincia_entry.delete(0, tk.END)
                self.comune_regione_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Errore Database", "Errore durante l'inserimento del comune.")
        except Exception as e:
            self.db_manager.rollback()
            messagebox.showerror("Errore", f"Errore imprevisto durante l'aggiunta del comune:\n{e}")

    def aggiungi_possessore(self):
        comune = self.poss_comune_entry.get().strip()
        cognome_nome = self.poss_cognome_nome_entry.get().strip()
        paternita = self.poss_paternita_entry.get().strip()
        nome_completo = self.poss_nome_completo_entry.get().strip()

        if not comune or not cognome_nome:
            messagebox.showwarning("Dati Mancanti", "Inserire almeno Comune e Cognome e Nome.")
            return

        if not nome_completo:
            nome_completo = f"{cognome_nome} {paternita}".strip()

        try:
            possessore_id = self.db_manager.insert_possessore(
                comune, cognome_nome, paternita, nome_completo, True
            )
            if possessore_id:
                messagebox.showinfo("Successo", f"Possessore '{nome_completo}' inserito con successo (ID: {possessore_id}).")
                self.poss_comune_entry.delete(0, tk.END)
                self.poss_cognome_nome_entry.delete(0, tk.END)
                self.poss_paternita_entry.delete(0, tk.END)
                self.poss_nome_completo_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Errore Database", "Errore durante l'inserimento del possessore (verificare log o dati).")
        except Exception as e:
            self.db_manager.rollback()
            messagebox.showerror("Errore", f"Errore imprevisto durante l'aggiunta del possessore:\n{e}")


    # --- Metodi Callback per le Azioni GUI (Report - invariati) ---
    def genera_report(self):
        report_type = self.report_type_var.get()
        id_str = self.report_id_entry.get().strip()

        if not id_str:
             messagebox.showwarning("Input Mancante", "Inserire l'ID della Partita o del Possessore.")
             return

        try:
            item_id = int(id_str)
        except ValueError:
            messagebox.showerror("Input Errato", "L'ID deve essere un numero intero.")
            return

        report_content = ""
        try:
            if report_type == "Certificato Proprietà":
                report_content = self.db_manager.genera_certificato_proprieta(item_id)
            elif report_type == "Report Genealogico":
                report_content = self.db_manager.genera_report_genealogico(item_id)
            elif report_type == "Report Possessore":
                report_content = self.db_manager.genera_report_possessore(item_id)

            self.report_text_area.delete('1.0', tk.END)
            if report_content:
                self.report_text_area.insert(tk.END, report_content)
            else:
                 self.report_text_area.insert(tk.END, f"Nessun {report_type} generato per l'ID {item_id}.\nVerificare l'ID o l'esistenza dei dati relativi.")

        except Exception as e:
            messagebox.showerror("Errore Generazione Report", f"Errore durante la generazione del report:\n{e}")
            self.report_text_area.delete('1.0', tk.END)
            self.report_text_area.insert(tk.END, f"Errore durante la generazione del report:\n{e}")


    # --- Metodi Callback per le Azioni GUI (Manutenzione - invariati) ---
    def verifica_integrita(self):
        self.manutenzione_results_text.delete('1.0', tk.END)
        self.manutenzione_results_text.insert(tk.END, "Avvio verifica integrità...\n")
        self.update_idletasks() # Aggiorna la GUI

        try:
            self.db_manager.execute_query("CALL verifica_integrita_database(NULL)")
            self.db_manager.commit()

            self.manutenzione_results_text.insert(tk.END, "\nVerifica completata.\nControllare il file 'catasto_db.log' per eventuali messaggi o problemi rilevati dalla procedura.")
            messagebox.showinfo("Verifica Integrità", "Verifica completata. Controllare l'area messaggi e il file di log per i dettagli.")

        except Exception as e:
            self.db_manager.rollback()
            error_msg = f"Errore durante la verifica dell'integrità:\n{e}"
            self.manutenzione_results_text.insert(tk.END, f"\n{error_msg}")
            messagebox.showerror("Errore Manutenzione", error_msg)


    # --- Metodi per Aprire le Finestre Toplevel ---

    def open_registra_consultazione_window(self):
        window = RegistraConsultazioneWindow(self, self.db_manager)
        window.grab_set() # Rende la finestra modale

    def open_registra_nuova_proprieta_window(self):
        window = RegistraNuovaProprietaWindow(self, self.db_manager)
        window.grab_set()

    def open_registra_passaggio_window(self):
         window = RegistraPassaggioWindow(self, self.db_manager)
         window.grab_set()


# --- Finestra Toplevel per Registra Consultazione ---
class RegistraConsultazioneWindow(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.title("Registra Consultazione")
        self.geometry("500x350")
        self.resizable(False, False)

        frame = ttk.Frame(self, padding="10")
        frame.pack(expand=True, fill="both")
        frame.columnconfigure(1, weight=1)

        # Data (oggi di default)
        ttk.Label(frame, text="Data:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.data_entry = DateEntry(frame, date_pattern='yyyy-mm-dd', width=12, background='darkblue',
                                    foreground='white', borderwidth=2)
        self.data_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.data_entry.set_date(date.today())

        # Richiedente
        ttk.Label(frame, text="Richiedente*:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.richiedente_entry = ttk.Entry(frame, width=40)
        self.richiedente_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Documento Identità
        ttk.Label(frame, text="Documento:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.documento_entry = ttk.Entry(frame, width=40)
        self.documento_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Motivazione
        ttk.Label(frame, text="Motivazione:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.motivazione_entry = ttk.Entry(frame, width=40)
        self.motivazione_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Materiale Consultato
        ttk.Label(frame, text="Materiale*:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.materiale_entry = ttk.Entry(frame, width=40)
        self.materiale_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Funzionario Autorizzante
        ttk.Label(frame, text="Funzionario*:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.funzionario_entry = ttk.Entry(frame, width=40)
        self.funzionario_entry.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(frame, text="* Campi obbligatori").grid(row=6, column=1, padx=5, pady=10, sticky="e")

        # Pulsanti
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=15)
        ttk.Button(button_frame, text="Registra", command=self.registra).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=10)

    def registra(self):
        data_cons = self.data_entry.get_date()
        richiedente = self.richiedente_entry.get().strip()
        documento = self.documento_entry.get().strip()
        motivazione = self.motivazione_entry.get().strip()
        materiale = self.materiale_entry.get().strip()
        funzionario = self.funzionario_entry.get().strip()

        if not richiedente or not materiale or not funzionario:
            messagebox.showwarning("Dati Mancanti", "Compilare i campi obbligatori (*).", parent=self)
            return

        try:
            success = self.db_manager.registra_consultazione(
                data_cons, richiedente, documento, motivazione, materiale, funzionario
            )
            if success:
                messagebox.showinfo("Successo", "Consultazione registrata con successo.", parent=self.parent) # Mostra sulla finestra principale
                self.destroy() # Chiude la finestra modale
            else:
                messagebox.showerror("Errore Database", "Errore durante la registrazione della consultazione.\nControllare i log.", parent=self)
        except Exception as e:
            self.db_manager.rollback()
            messagebox.showerror("Errore Imprevisto", f"Errore: {e}", parent=self)


# --- Finestra Toplevel per Registra Nuova Proprietà ---
class RegistraNuovaProprietaWindow(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.title("Registra Nuova Proprietà")
        self.geometry("750x650") # Più grande
        # self.resizable(False, False)

        self.possessori_list = [] # Lista per tenere traccia dei possessori aggiunti
        self.immobili_list = []   # Lista per tenere traccia degli immobili aggiunti

        # --- Frame Principale ---
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1) # Area possessori si espande
        main_frame.rowconfigure(5, weight=1) # Area immobili si espande

        # --- Dati Partita ---
        partita_frame = ttk.LabelFrame(main_frame, text="Dati Partita")
        partita_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        partita_frame.columnconfigure(1, weight=1)
        partita_frame.columnconfigure(3, weight=1)

        ttk.Label(partita_frame, text="Comune*:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.comune_entry = ttk.Entry(partita_frame)
        self.comune_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(partita_frame, text="Numero Partita*:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.numero_entry = ttk.Entry(partita_frame, width=10)
        self.numero_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(partita_frame, text="Data Impianto*:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.data_impianto_entry = DateEntry(partita_frame, date_pattern='yyyy-mm-dd', width=12)
        self.data_impianto_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.data_impianto_entry.set_date(date.today())

        # --- Gestione Possessori ---
        poss_frame = ttk.LabelFrame(main_frame, text="Possessori*")
        poss_frame.grid(row=1, column=0, padx=5, pady=10, sticky="ew")
        poss_frame.columnconfigure(1, weight=1)

        ttk.Label(poss_frame, text="Nome Completo:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.poss_nome_entry = ttk.Entry(poss_frame)
        self.poss_nome_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(poss_frame, text="Cerca/Nuovo", command=self.gestisci_possessore).grid(row=0, column=2, padx=5)

        ttk.Label(poss_frame, text="Cognome Nome:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.poss_cgn_entry = ttk.Entry(poss_frame)
        self.poss_cgn_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(poss_frame, text="Paternità:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.poss_pat_entry = ttk.Entry(poss_frame)
        self.poss_pat_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(poss_frame, text="Quota:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.poss_quota_entry = ttk.Entry(poss_frame, width=15)
        self.poss_quota_entry.grid(row=3, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(poss_frame, text="(es. 1/2, opzionale)").grid(row=3, column=1, padx=5, pady=2, sticky="e")

        ttk.Button(poss_frame, text="Aggiungi Possessore alla Lista", command=self.aggiungi_possessore_lista).grid(row=4, column=0, columnspan=3, pady=5)

        # Visualizzazione Possessori Aggiunti
        ttk.Label(main_frame, text="Possessori Aggiunti:").grid(row=2, column=0, padx=5, pady=(10,0), sticky="w")
        poss_tree_frame = ttk.Frame(main_frame)
        poss_tree_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")
        poss_tree_frame.rowconfigure(0, weight=1)
        poss_tree_frame.columnconfigure(0, weight=1)

        poss_cols = ("nome_completo", "cognome_nome", "paternita", "quota")
        self.poss_tree = ttk.Treeview(poss_tree_frame, columns=poss_cols, show="headings", height=4)
        for col in poss_cols:
            self.poss_tree.heading(col, text=col.replace('_', ' ').title())
            self.poss_tree.column(col, width=140, anchor=tk.W)

        poss_vsb = ttk.Scrollbar(poss_tree_frame, orient="vertical", command=self.poss_tree.yview)
        self.poss_tree.configure(yscrollcommand=poss_vsb.set)
        self.poss_tree.grid(row=0, column=0, sticky="nsew")
        poss_vsb.grid(row=0, column=1, sticky="ns")
        ttk.Button(main_frame, text="Rimuovi Selezionato", command=self.rimuovi_possessore_lista).grid(row=4, column=0, padx=5, pady=2, sticky="w")


        # --- Gestione Immobili ---
        imm_frame = ttk.LabelFrame(main_frame, text="Immobili*")
        imm_frame.grid(row=5, column=0, padx=5, pady=10, sticky="ew")
        imm_frame.columnconfigure(1, weight=1)
        imm_frame.columnconfigure(3, weight=1)


        ttk.Label(imm_frame, text="Natura:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.imm_natura_entry = ttk.Entry(imm_frame)
        self.imm_natura_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(imm_frame, text="Località:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.imm_localita_entry = ttk.Entry(imm_frame)
        self.imm_localita_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(imm_frame, text="Tipo Loc:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.imm_tipo_loc_var = tk.StringVar(value="via")
        ttk.Combobox(imm_frame, textvariable=self.imm_tipo_loc_var, values=["via", "regione", "borgata", "frazione"], state="readonly", width=10).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(imm_frame, text="Classificazione:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.imm_class_entry = ttk.Entry(imm_frame)
        self.imm_class_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(imm_frame, text="Piani:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.imm_piani_entry = ttk.Entry(imm_frame, width=5)
        self.imm_piani_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(imm_frame, text="Vani:").grid(row=2, column=2, padx=5, pady=2, sticky="w")
        self.imm_vani_entry = ttk.Entry(imm_frame, width=5)
        self.imm_vani_entry.grid(row=2, column=3, padx=5, pady=2, sticky="w")

        ttk.Label(imm_frame, text="Consistenza:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.imm_cons_entry = ttk.Entry(imm_frame)
        self.imm_cons_entry.grid(row=3, column=1, columnspan=3, padx=5, pady=2, sticky="ew")

        ttk.Button(imm_frame, text="Aggiungi Immobile alla Lista", command=self.aggiungi_immobile_lista).grid(row=4, column=0, columnspan=4, pady=5)


        # Visualizzazione Immobili Aggiunti
        ttk.Label(main_frame, text="Immobili Aggiunti:").grid(row=6, column=0, padx=5, pady=(10,0), sticky="w")
        imm_tree_frame = ttk.Frame(main_frame)
        imm_tree_frame.grid(row=7, column=0, padx=5, pady=5, sticky="nsew")
        imm_tree_frame.rowconfigure(0, weight=1)
        imm_tree_frame.columnconfigure(0, weight=1)

        imm_cols = ("natura", "localita", "tipo_localita", "classificazione", "piani", "vani", "consistenza")
        self.imm_tree = ttk.Treeview(imm_tree_frame, columns=imm_cols, show="headings", height=4)
        for col in imm_cols:
            self.imm_tree.heading(col, text=col.replace('_', ' ').title())
            self.imm_tree.column(col, width=90, anchor=tk.W)

        imm_vsb = ttk.Scrollbar(imm_tree_frame, orient="vertical", command=self.imm_tree.yview)
        self.imm_tree.configure(yscrollcommand=imm_vsb.set)
        self.imm_tree.grid(row=0, column=0, sticky="nsew")
        imm_vsb.grid(row=0, column=1, sticky="ns")
        ttk.Button(main_frame, text="Rimuovi Selezionato", command=self.rimuovi_immobile_lista).grid(row=8, column=0, padx=5, pady=2, sticky="w")

        # --- Pulsanti Finali ---
        ttk.Label(main_frame, text="* Campi obbligatori").grid(row=9, column=0, padx=5, pady=10, sticky="e")
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=10, column=0, pady=15)
        ttk.Button(button_frame, text="Registra Proprietà", command=self.registra).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=10)


    def gestisci_possessore(self):
        """ Cerca un possessore esistente o popola i campi per crearne uno nuovo. """
        nome_completo = self.poss_nome_entry.get().strip()
        comune = self.comune_entry.get().strip() # Prende il comune dalla sezione Partita
        if not nome_completo or not comune:
            messagebox.showwarning("Dati Mancanti", "Inserire Comune (nella sezione Dati Partita) e Nome Completo del possessore da cercare.", parent=self)
            return

        try:
            poss_id = self.db_manager.check_possessore_exists(nome_completo, comune)
            if poss_id:
                # Trovato: chiedi conferma e magari popola altri campi se necessario
                 if messagebox.askyesno("Possessore Esistente", f"Possessore '{nome_completo}' trovato nel comune '{comune}' (ID: {poss_id}).\nVuoi usarlo?", parent=self):
                    # Potresti voler recuperare e popolare cognome/paternità qui
                    # db.execute_query(...) db.fetchone() ...
                    self.poss_cgn_entry.delete(0, tk.END)
                    self.poss_pat_entry.delete(0, tk.END)
                    # self.poss_cgn_entry.insert(0, dati_recuperati['cognome_nome'])
                    # self.poss_pat_entry.insert(0, dati_recuperati['paternita'])
                    messagebox.showinfo("Info", "Possessore selezionato. Inserisci la quota (se necessaria) e aggiungi alla lista.", parent=self)
                 else:
                    self.poss_nome_entry.delete(0, tk.END) # Pulisce per inserire un nome diverso
            else:
                # Non trovato: informa l'utente e lascia i campi pronti per l'inserimento
                messagebox.showinfo("Possessore Non Trovato", f"Possessore '{nome_completo}' non trovato per il comune '{comune}'.\nInserisci Cognome Nome e Paternità per aggiungerlo come nuovo possessore.", parent=self)
                self.poss_cgn_entry.focus() # Mette il focus sul campo successivo
        except Exception as e:
            messagebox.showerror("Errore Ricerca", f"Errore durante la ricerca del possessore:\n{e}", parent=self)


    def aggiungi_possessore_lista(self):
        """ Aggiunge i dati del possessore inseriti alla lista e al Treeview. """
        nome = self.poss_nome_entry.get().strip()
        cognome_nome = self.poss_cgn_entry.get().strip()
        paternita = self.poss_pat_entry.get().strip()
        quota = self.poss_quota_entry.get().strip()

        if not nome:
            messagebox.showwarning("Dati Mancanti", "Inserire almeno il Nome Completo del possessore.", parent=self)
            return
        # Se Cognome/Nome non sono inseriti, assumiamo che sia un possessore esistente (o l'utente li aggiungerà dopo cercandolo)
        # La procedura `registra_nuova_proprieta` nel DB gestirà la creazione se mancano cognome/paternità.

        possessore_data = {
            "nome_completo": nome,
            "cognome_nome": cognome_nome if cognome_nome else None, # Invia None se vuoto
            "paternita": paternita if paternita else None,       # Invia None se vuoto
            "quota": quota if quota else None                     # Invia None se vuoto
        }

        # Aggiunge al Treeview
        values = (
            possessore_data["nome_completo"],
            possessore_data["cognome_nome"] or "", # Mostra stringa vuota nel treeview
            possessore_data["paternita"] or "",
            possessore_data["quota"] or ""
        )
        item_id = self.poss_tree.insert("", tk.END, values=values)

        # Aggiunge alla lista interna (associando l'ID del treeview per poter rimuovere)
        self.possessori_list.append({"id": item_id, "data": possessore_data})

        # Pulisce i campi per il prossimo inserimento
        self.poss_nome_entry.delete(0, tk.END)
        self.poss_cgn_entry.delete(0, tk.END)
        self.poss_pat_entry.delete(0, tk.END)
        self.poss_quota_entry.delete(0, tk.END)
        self.poss_nome_entry.focus()


    def rimuovi_possessore_lista(self):
        """ Rimuove il possessore selezionato dal Treeview e dalla lista. """
        selected_item = self.poss_tree.selection()
        if not selected_item:
            messagebox.showwarning("Nessuna Selezione", "Selezionare un possessore da rimuovere.", parent=self)
            return

        item_id_to_remove = selected_item[0]
        self.poss_tree.delete(item_id_to_remove)

        # Rimuove dalla lista interna
        self.possessori_list = [p for p in self.possessori_list if p["id"] != item_id_to_remove]


    def aggiungi_immobile_lista(self):
        """ Aggiunge i dati dell'immobile alla lista e al Treeview. """
        natura = self.imm_natura_entry.get().strip()
        localita = self.imm_localita_entry.get().strip()
        tipo_localita = self.imm_tipo_loc_var.get()
        classificazione = self.imm_class_entry.get().strip()
        piani_str = self.imm_piani_entry.get().strip()
        vani_str = self.imm_vani_entry.get().strip()
        consistenza = self.imm_cons_entry.get().strip()

        if not natura or not localita:
            messagebox.showwarning("Dati Mancanti", "Inserire almeno Natura e Località dell'immobile.", parent=self)
            return

        piani = None
        vani = None
        try:
            if piani_str:
                piani = int(piani_str)
            if vani_str:
                vani = int(vani_str)
        except ValueError:
             messagebox.showerror("Input Errato", "Piani e Vani devono essere numeri interi.", parent=self)
             return

        immobile_data = {
            "natura": natura,
            "localita": localita,
            "tipo_localita": tipo_localita,
            "classificazione": classificazione if classificazione else None,
            "numero_piani": piani,
            "numero_vani": vani,
            "consistenza": consistenza if consistenza else None
        }

        values = (
            immobile_data["natura"],
            immobile_data["localita"],
            immobile_data["tipo_localita"],
            immobile_data["classificazione"] or "",
            str(immobile_data["numero_piani"] or ""), # Converti None in stringa vuota
            str(immobile_data["numero_vani"] or ""),
            immobile_data["consistenza"] or ""
        )
        item_id = self.imm_tree.insert("", tk.END, values=values)
        self.immobili_list.append({"id": item_id, "data": immobile_data})

        # Pulisce i campi
        self.imm_natura_entry.delete(0, tk.END)
        self.imm_localita_entry.delete(0, tk.END)
        # self.imm_tipo_loc_var.set("via") # Resetta combobox? Opzionale
        self.imm_class_entry.delete(0, tk.END)
        self.imm_piani_entry.delete(0, tk.END)
        self.imm_vani_entry.delete(0, tk.END)
        self.imm_cons_entry.delete(0, tk.END)
        self.imm_natura_entry.focus()


    def rimuovi_immobile_lista(self):
        """ Rimuove l'immobile selezionato dal Treeview e dalla lista. """
        selected_item = self.imm_tree.selection()
        if not selected_item:
            messagebox.showwarning("Nessuna Selezione", "Selezionare un immobile da rimuovere.", parent=self)
            return

        item_id_to_remove = selected_item[0]
        self.imm_tree.delete(item_id_to_remove)
        self.immobili_list = [i for i in self.immobili_list if i["id"] != item_id_to_remove]


    def registra(self):
        """ Raccoglie tutti i dati e chiama la procedura del DB manager. """
        comune = self.comune_entry.get().strip()
        numero_str = self.numero_entry.get().strip()
        data_imp = self.data_impianto_entry.get_date()

        if not comune or not numero_str:
             messagebox.showwarning("Dati Mancanti", "Inserire Comune e Numero Partita.", parent=self)
             return

        try:
            numero_partita = int(numero_str)
        except ValueError:
            messagebox.showerror("Input Errato", "Il Numero Partita deve essere un intero.", parent=self)
            return

        if not self.possessori_list:
            messagebox.showwarning("Dati Mancanti", "Aggiungere almeno un possessore.", parent=self)
            return
        if not self.immobili_list:
            messagebox.showwarning("Dati Mancanti", "Aggiungere almeno un immobile.", parent=self)
            return

        # Prepara le liste JSON per la procedura
        possessori_json = [p["data"] for p in self.possessori_list]
        immobili_json = [i["data"] for i in self.immobili_list]

        try:
            success = self.db_manager.registra_nuova_proprieta(
                comune, numero_partita, data_imp, possessori_json, immobili_json
            )
            if success:
                 messagebox.showinfo("Successo", f"Nuova proprietà (Partita {numero_partita}, Comune {comune}) registrata con successo.", parent=self.parent)
                 self.destroy()
            else:
                 messagebox.showerror("Errore Database", "Errore durante la registrazione della nuova proprietà.\nControllare i log.", parent=self)

        except Exception as e:
            self.db_manager.rollback()
            messagebox.showerror("Errore Imprevisto", f"Errore: {e}", parent=self)



# --- Finestra Toplevel per Registra Passaggio Proprietà ---
class RegistraPassaggioWindow(tk.Toplevel):
     def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.title("Registra Passaggio Proprietà")
        self.geometry("800x750") # Ancora più grande

        self.nuovi_possessori_list = []
        self.immobili_trasferiti_ids = [] # Lista degli ID degli immobili da trasferire

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, weight=1)
        # Configura righe per espansione se necessario (es. treeview)
        main_frame.rowconfigure(7, weight=1) # Area possessori
        main_frame.rowconfigure(10, weight=1) # Area immobili

        # --- Dati Origine ---
        origine_frame = ttk.LabelFrame(main_frame, text="Partita di Origine")
        origine_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Label(origine_frame, text="ID Partita Origine*:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.partita_origine_id_entry = ttk.Entry(origine_frame, width=10)
        self.partita_origine_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        # Bottone per caricare immobili da trasferire
        ttk.Button(origine_frame, text="Carica Immobili Origine", command=self.carica_immobili_origine).grid(row=0, column=2, padx=10)


        # --- Dati Nuova Partita ---
        dest_frame = ttk.LabelFrame(main_frame, text="Nuova Partita (Destinazione)")
        dest_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        dest_frame.columnconfigure(1, weight=1)
        dest_frame.columnconfigure(3, weight=1)

        ttk.Label(dest_frame, text="Comune*:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.nuovo_comune_entry = ttk.Entry(dest_frame)
        self.nuovo_comune_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(dest_frame, text="Numero Nuova Partita*:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.nuovo_numero_entry = ttk.Entry(dest_frame, width=10)
        self.nuovo_numero_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # --- Dati Variazione ---
        var_frame = ttk.LabelFrame(main_frame, text="Dati Variazione")
        var_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        var_frame.columnconfigure(1, weight=1)
        var_frame.columnconfigure(3, weight=1)

        ttk.Label(var_frame, text="Tipo Variazione*:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.tipo_var_var = tk.StringVar()
        ttk.Combobox(var_frame, textvariable=self.tipo_var_var, values=["Vendita", "Successione", "Donazione", "Frazionamento", "Altro"], state="readonly").grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.tipo_var_var.set("Vendita")

        ttk.Label(var_frame, text="Data Variazione*:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.data_var_entry = DateEntry(var_frame, date_pattern='yyyy-mm-dd', width=12)
        self.data_var_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.data_var_entry.set_date(date.today())

        # --- Dati Contratto ---
        contr_frame = ttk.LabelFrame(main_frame, text="Dati Contratto/Atto")
        contr_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        contr_frame.columnconfigure(1, weight=1)
        contr_frame.columnconfigure(3, weight=1)

        ttk.Label(contr_frame, text="Tipo Contratto*:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.tipo_contr_entry = ttk.Entry(contr_frame)
        self.tipo_contr_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(contr_frame, text="Data Contratto*:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.data_contr_entry = DateEntry(contr_frame, date_pattern='yyyy-mm-dd', width=12)
        self.data_contr_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.data_contr_entry.set_date(date.today())

        ttk.Label(contr_frame, text="Notaio:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.notaio_entry = ttk.Entry(contr_frame)
        self.notaio_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(contr_frame, text="Repertorio:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.repertorio_entry = ttk.Entry(contr_frame)
        self.repertorio_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

        # --- Note ---
        note_frame = ttk.LabelFrame(main_frame, text="Note")
        note_frame.grid(row=4, column=0, padx=5, pady=5, sticky="ew")
        self.note_text = scrolledtext.ScrolledText(note_frame, height=3, width=60, wrap=tk.WORD)
        self.note_text.pack(expand=True, fill="both", padx=5, pady=5)


        # --- Gestione Nuovi Possessori (Opzionale) ---
        nuovi_poss_main_frame = ttk.LabelFrame(main_frame, text="Nuovi Possessori (Opzionale - Inserire se diversi da quelli della partita origine)")
        nuovi_poss_main_frame.grid(row=5, column=0, padx=5, pady=10, sticky="ew")

        poss_frame = ttk.Frame(nuovi_poss_main_frame) # Frame interno per i campi
        poss_frame.pack(fill=tk.X, padx=5, pady=5)
        poss_frame.columnconfigure(1, weight=1)

        ttk.Label(poss_frame, text="Nome Completo:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.nuovo_poss_nome_entry = ttk.Entry(poss_frame)
        self.nuovo_poss_nome_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(poss_frame, text="Cerca/Nuovo", command=self.gestisci_nuovo_possessore).grid(row=0, column=2, padx=5)

        ttk.Label(poss_frame, text="Cognome Nome:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.nuovo_poss_cgn_entry = ttk.Entry(poss_frame)
        self.nuovo_poss_cgn_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(poss_frame, text="Paternità:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.nuovo_poss_pat_entry = ttk.Entry(poss_frame)
        self.nuovo_poss_pat_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(poss_frame, text="Quota:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.nuovo_poss_quota_entry = ttk.Entry(poss_frame, width=15)
        self.nuovo_poss_quota_entry.grid(row=3, column=1, padx=5, pady=2, sticky="w")

        ttk.Button(poss_frame, text="Aggiungi Possessore alla Lista", command=self.aggiungi_nuovo_possessore_lista).grid(row=4, column=0, columnspan=3, pady=5)

        # Visualizzazione Nuovi Possessori Aggiunti
        ttk.Label(nuovi_poss_main_frame, text="Nuovi Possessori Aggiunti:").pack(anchor=tk.W, padx=5, pady=(10,0))
        poss_tree_frame = ttk.Frame(nuovi_poss_main_frame)
        poss_tree_frame.pack(expand=True, fill="both", padx=5, pady=5)
        poss_tree_frame.rowconfigure(0, weight=1)
        poss_tree_frame.columnconfigure(0, weight=1)

        poss_cols = ("nome_completo", "cognome_nome", "paternita", "quota")
        self.nuovi_poss_tree = ttk.Treeview(poss_tree_frame, columns=poss_cols, show="headings", height=3)
        for col in poss_cols:
            self.nuovi_poss_tree.heading(col, text=col.replace('_', ' ').title())
            self.nuovi_poss_tree.column(col, width=160, anchor=tk.W)

        poss_vsb = ttk.Scrollbar(poss_tree_frame, orient="vertical", command=self.nuovi_poss_tree.yview)
        self.nuovi_poss_tree.configure(yscrollcommand=poss_vsb.set)
        self.nuovi_poss_tree.grid(row=0, column=0, sticky="nsew")
        poss_vsb.grid(row=0, column=1, sticky="ns")
        ttk.Button(nuovi_poss_main_frame, text="Rimuovi Selezionato", command=self.rimuovi_nuovo_possessore_lista).pack(anchor=tk.W, padx=5, pady=2)


        # --- Selezione Immobili da Trasferire (Opzionale) ---
        imm_trasf_frame = ttk.LabelFrame(main_frame, text="Immobili da Trasferire (Opzionale - Selezionare quali immobili passano alla nuova partita)")
        imm_trasf_frame.grid(row=9, column=0, padx=5, pady=10, sticky="nsew") # Usa row 9
        imm_trasf_frame.rowconfigure(0, weight=1)
        imm_trasf_frame.columnconfigure(0, weight=1)

        imm_cols_trasf = ("id", "natura", "localita", "classificazione")
        self.imm_trasf_tree = ttk.Treeview(imm_trasf_frame, columns=imm_cols_trasf, show="headings", height=4, selectmode="extended") # Permette selezione multipla
        for col in imm_cols_trasf:
            self.imm_trasf_tree.heading(col, text=col.replace('_', ' ').title())
            self.imm_trasf_tree.column(col, width=150 if col != "id" else 50, anchor=tk.W)

        imm_vsb_trasf = ttk.Scrollbar(imm_trasf_frame, orient="vertical", command=self.imm_trasf_tree.yview)
        self.imm_trasf_tree.configure(yscrollcommand=imm_vsb_trasf.set)
        self.imm_trasf_tree.grid(row=0, column=0, sticky="nsew")
        imm_vsb_trasf.grid(row=0, column=1, sticky="ns")

        # Sposta il frame dei pulsanti finali più in basso
        ttk.Label(main_frame, text="* Campi obbligatori").grid(row=11, column=0, padx=5, pady=10, sticky="e")
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=12, column=0, pady=15) # Usa row 12
        ttk.Button(button_frame, text="Registra Passaggio", command=self.registra).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=10)

     def carica_immobili_origine(self):
         """ Carica gli immobili della partita di origine nel Treeview per la selezione. """
         partita_id_str = self.partita_origine_id_entry.get().strip()
         if not partita_id_str:
             messagebox.showwarning("ID Mancante", "Inserire l'ID della Partita di Origine.", parent=self)
             return
         try:
             partita_id = int(partita_id_str)
             # Pulisce il treeview precedente
             for item in self.imm_trasf_tree.get_children():
                 self.imm_trasf_tree.delete(item)

             # Recupera dettagli partita, in particolare gli immobili
             partita_details = self.db_manager.get_partita_details(partita_id)
             if not partita_details or 'immobili' not in partita_details:
                  messagebox.showinfo("Nessun Immobile", f"Nessun immobile trovato per la partita ID {partita_id}.", parent=self)
                  return

             # Popola il treeview
             for imm in partita_details['immobili']:
                 values = (
                     imm.get('id', ''),
                     imm.get('natura', ''),
                     imm.get('localita_nome', ''),
                     imm.get('classificazione', '')
                 )
                 self.imm_trasf_tree.insert("", tk.END, values=values, iid=imm.get('id')) # Usa ID db come iid

         except ValueError:
             messagebox.showerror("Input Errato", "L'ID Partita Origine deve essere un numero intero.", parent=self)
         except Exception as e:
             messagebox.showerror("Errore Caricamento", f"Errore durante il caricamento degli immobili:\n{e}", parent=self)

     def gestisci_nuovo_possessore(self):
        """ Cerca un possessore esistente nel nuovo comune o popola i campi per crearne uno nuovo. """
        nome_completo = self.nuovo_poss_nome_entry.get().strip()
        comune = self.nuovo_comune_entry.get().strip() # Prende il comune dalla sezione Nuova Partita
        if not nome_completo or not comune:
            messagebox.showwarning("Dati Mancanti", "Inserire Nuovo Comune (nella sezione Nuova Partita) e Nome Completo del possessore da cercare.", parent=self)
            return

        try:
            poss_id = self.db_manager.check_possessore_exists(nome_completo, comune)
            if poss_id:
                 if messagebox.askyesno("Possessore Esistente", f"Possessore '{nome_completo}' trovato nel comune '{comune}' (ID: {poss_id}).\nVuoi usarlo?", parent=self):
                    self.nuovo_poss_cgn_entry.delete(0, tk.END)
                    self.nuovo_poss_pat_entry.delete(0, tk.END)
                    messagebox.showinfo("Info", "Possessore selezionato. Inserisci la quota (se necessaria) e aggiungi alla lista.", parent=self)
                 else:
                    self.nuovo_poss_nome_entry.delete(0, tk.END)
            else:
                messagebox.showinfo("Possessore Non Trovato", f"Possessore '{nome_completo}' non trovato per il comune '{comune}'.\nInserisci Cognome Nome e Paternità per aggiungerlo come nuovo possessore.", parent=self)
                self.nuovo_poss_cgn_entry.focus()
        except Exception as e:
            messagebox.showerror("Errore Ricerca", f"Errore durante la ricerca del possessore:\n{e}", parent=self)


     def aggiungi_nuovo_possessore_lista(self):
        """ Aggiunge i dati del nuovo possessore alla lista e al Treeview. """
        nome = self.nuovo_poss_nome_entry.get().strip()
        cognome_nome = self.nuovo_poss_cgn_entry.get().strip()
        paternita = self.nuovo_poss_pat_entry.get().strip()
        quota = self.nuovo_poss_quota_entry.get().strip()

        if not nome:
            messagebox.showwarning("Dati Mancanti", "Inserire almeno il Nome Completo del possessore.", parent=self)
            return

        possessore_data = {
            "nome_completo": nome,
            "cognome_nome": cognome_nome if cognome_nome else None,
            "paternita": paternita if paternita else None,
            "quota": quota if quota else None
        }
        values = (
            possessore_data["nome_completo"],
            possessore_data["cognome_nome"] or "",
            possessore_data["paternita"] or "",
            possessore_data["quota"] or ""
        )
        item_id = self.nuovi_poss_tree.insert("", tk.END, values=values)
        self.nuovi_possessori_list.append({"id": item_id, "data": possessore_data})

        self.nuovo_poss_nome_entry.delete(0, tk.END)
        self.nuovo_poss_cgn_entry.delete(0, tk.END)
        self.nuovo_poss_pat_entry.delete(0, tk.END)
        self.nuovo_poss_quota_entry.delete(0, tk.END)
        self.nuovo_poss_nome_entry.focus()

     def rimuovi_nuovo_possessore_lista(self):
        """ Rimuove il possessore selezionato dal Treeview e dalla lista. """
        selected_item = self.nuovi_poss_tree.selection()
        if not selected_item:
            messagebox.showwarning("Nessuna Selezione", "Selezionare un possessore da rimuovere.", parent=self)
            return
        item_id_to_remove = selected_item[0]
        self.nuovi_poss_tree.delete(item_id_to_remove)
        self.nuovi_possessori_list = [p for p in self.nuovi_possessori_list if p["id"] != item_id_to_remove]


     def registra(self):
        """ Raccoglie tutti i dati e chiama la procedura del DB manager per il passaggio. """
        partita_origine_id_str = self.partita_origine_id_entry.get().strip()
        nuovo_comune = self.nuovo_comune_entry.get().strip()
        nuovo_numero_str = self.nuovo_numero_entry.get().strip()
        tipo_variazione = self.tipo_var_var.get()
        data_variazione = self.data_var_entry.get_date()
        tipo_contratto = self.tipo_contr_entry.get().strip()
        data_contratto = self.data_contr_entry.get_date()
        notaio = self.notaio_entry.get().strip()
        repertorio = self.repertorio_entry.get().strip()
        note = self.note_text.get("1.0", tk.END).strip()

        # Validazione Input Essenziale
        if not partita_origine_id_str or not nuovo_comune or not nuovo_numero_str or \
           not tipo_variazione or not tipo_contratto:
            messagebox.showwarning("Dati Mancanti", "Compilare tutti i campi obbligatori (*).", parent=self)
            return

        try:
            partita_origine_id = int(partita_origine_id_str)
            nuovo_numero_partita = int(nuovo_numero_str)
        except ValueError:
            messagebox.showerror("Input Errato", "ID Partita Origine e Numero Nuova Partita devono essere interi.", parent=self)
            return

        # Prepara lista nuovi possessori (se presente)
        nuovi_possessori_json = None
        if self.nuovi_possessori_list:
            nuovi_possessori_json = [p["data"] for p in self.nuovi_possessori_list]

        # Prepara lista ID immobili da trasferire (se selezionati)
        selected_imm_items = self.imm_trasf_tree.selection()
        immobili_da_trasferire = None
        if selected_imm_items:
             # Estrai gli ID (che abbiamo impostato come iid nel treeview)
             immobili_da_trasferire = [int(self.imm_trasf_tree.item(item_id, "values")[0]) for item_id in selected_imm_items]


        # Chiamata alla procedura
        try:
            success = self.db_manager.registra_passaggio_proprieta(
                partita_origine_id=partita_origine_id,
                comune_nome=nuovo_comune,
                numero_partita=nuovo_numero_partita,
                tipo_variazione=tipo_variazione,
                data_variazione=data_variazione,
                tipo_contratto=tipo_contratto,
                data_contratto=data_contratto,
                notaio=notaio if notaio else None,
                repertorio=repertorio if repertorio else None,
                nuovi_possessori=nuovi_possessori_json, # Passa la lista o None
                immobili_da_trasferire=immobili_da_trasferire, # Passa lista ID o None
                note=note if note else None
            )

            if success:
                 messagebox.showinfo("Successo", f"Passaggio di proprietà registrato con successo.\nNuova partita: {nuovo_numero_partita}, Comune: {nuovo_comune}", parent=self.parent)
                 self.destroy()
            else:
                 messagebox.showerror("Errore Database", "Errore durante la registrazione del passaggio di proprietà.\nControllare i log.", parent=self)

        except Exception as e:
            self.db_manager.rollback()
            messagebox.showerror("Errore Imprevisto", f"Errore: {e}", parent=self)


# --- Funzione Principale per Avviare l'App ---
def main_gui():
    # Configurazione DB (presa da python_example_completo.py)
    # !! ASSICURATI CHE LA PASSWORD SIA CORRETTA !!
    db_config = {
        "dbname": "catasto_storico",
        "user": "postgres",
        "password": "Markus74",  # MODIFICA QUI SE NECESSARIO!
        "host": "localhost",
        "port": 5432,
        "schema": "catasto"
    }

    app = CatastoApp(db_config)
    app.mainloop()

# --- Blocco di Esecuzione ---
if __name__ == "__main__":
    main_gui()