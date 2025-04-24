import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# Assicurati che catasto_db_manager.py sia nella stessa cartella o nel PYTHONPATH
try:
    from catasto_db_manager import CatastoDBManager
except ImportError:
    messagebox.showerror("Errore Importazione",
                         "Non è stato possibile trovare il file 'catasto_db_manager.py'.\n"
                         "Assicurati che sia nella stessa cartella di questo script.")
    exit()

class CatastoApp(tb.Window):
    def __init__(self, theme='litera'):
        super().__init__(themename=theme)
        self.title("Gestore Catasto Storico")
        self.geometry("1000x700")

        # Istanza del gestore DB
        # !!! IMPORTANTE: Aggiorna qui con le tue credenziali reali !!!
        self.db = CatastoDBManager(
            dbname="catasto_storico",
            user="postgres",
            password="Markus74", # <- METTI LA TUA PASSWORD QUI
            host="localhost",
            port=5432,
            schema="catasto"
        )

        # Connessione al DB all'avvio
        if not self.db.connect():
             # Mostra un messaggio di errore grafico e chiudi se la connessione fallisce
             messagebox.showerror("Errore Connessione DB",
                                 "Impossibile connettersi al database.\n"
                                 "Verifica i parametri di connessione e che il server PostgreSQL sia in esecuzione.")
             self.destroy() # Chiude la finestra
             return # Interrompe l'inizializzazione

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing) # Gestisce la chiusura

    def create_widgets(self):
        # Frame principale
        main_frame = tb.Frame(self, padding=10)
        main_frame.pack(expand=True, fill=BOTH)

        # Notebook per le schede
        self.notebook = tb.Notebook(main_frame)
        self.notebook.pack(expand=True, fill=BOTH, pady=5)

        # Creazione delle schede
        self.create_consultazione_tab()
        self.create_inserimento_tab() # Placeholder
        self.create_report_tab()      # Placeholder
        self.create_manutenzione_tab()# Placeholder

        # Aggiungere qui la creazione delle altre schede...

    def create_consultazione_tab(self):
        consultazione_frame = tb.Frame(self.notebook, padding=10)
        self.notebook.add(consultazione_frame, text=" Consultazione ")

        # --- Sezione Comuni ---
        comuni_labelframe = tb.LabelFrame(consultazione_frame, text="Comuni", padding=10)
        comuni_labelframe.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)

        # Barra strumenti Comuni
        comuni_toolbar = tb.Frame(comuni_labelframe)
        comuni_toolbar.pack(fill=X, pady=(0, 5))

        refresh_comuni_btn = tb.Button(comuni_toolbar, text="Aggiorna Elenco",
                                        command=self.load_comuni, bootstyle="info-outline")
        refresh_comuni_btn.pack(side=LEFT, padx=(0, 5))

        search_comuni_entry = tb.Entry(comuni_toolbar, bootstyle="info")
        search_comuni_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        self.search_comuni_var = tk.StringVar()
        search_comuni_entry.config(textvariable=self.search_comuni_var)

        search_comuni_btn = tb.Button(comuni_toolbar, text="Cerca",
                                       command=self.search_comuni, bootstyle="info-outline")
        search_comuni_btn.pack(side=LEFT, padx=(5, 0))


        # Treeview per Comuni
        cols_comuni = ('nome', 'provincia', 'regione')
        self.tree_comuni = tb.Treeview(comuni_labelframe, columns=cols_comuni, show='headings', bootstyle='info')

        self.tree_comuni.heading('nome', text='Nome')
        self.tree_comuni.heading('provincia', text='Provincia')
        self.tree_comuni.heading('regione', text='Regione')

        self.tree_comuni.column('nome', width=200)
        self.tree_comuni.column('provincia', width=100, anchor=CENTER)
        self.tree_comuni.column('regione', width=100, anchor=CENTER)

        self.tree_comuni.pack(fill=BOTH, expand=True)

        # Scrollbar per Comuni
        scrollbar_comuni_y = tb.Scrollbar(self.tree_comuni, orient=VERTICAL, command=self.tree_comuni.yview)
        self.tree_comuni.configure(yscrollcommand=scrollbar_comuni_y.set)
        scrollbar_comuni_y.pack(side=RIGHT, fill=Y)
        scrollbar_comuni_x = tb.Scrollbar(self.tree_comuni, orient=HORIZONTAL, command=self.tree_comuni.xview)
        self.tree_comuni.configure(xscrollcommand=scrollbar_comuni_x.set)
        scrollbar_comuni_x.pack(side=BOTTOM, fill=X)


        # Menu contestuale per Comuni
        self.comuni_context_menu = tk.Menu(self, tearoff=0)
        # Aggiungeremo qui le azioni specifiche
        self.comuni_context_menu.add_command(label="Cerca Partite di questo Comune", command=self.cerca_partite_da_comune)
        self.comuni_context_menu.add_command(label="Cerca Possessori di questo Comune", command=self.cerca_possessori_da_comune)
        self.comuni_context_menu.add_separator()
        self.comuni_context_menu.add_command(label="Mostra Dettagli Comune (Non Impl.)") # Placeholder

        # Associa evento tasto destro al Treeview Comuni
        self.tree_comuni.bind("<Button-3>", self.show_comuni_context_menu) # Button-3 è il tasto destro standard

        # Carica i comuni all'inizio
        self.load_comuni()

        # --- Sezione Partite (inizialmente vuota, verrà popolata dalle ricerche) ---
        partite_labelframe = tb.LabelFrame(consultazione_frame, text="Partite", padding=10)
        partite_labelframe.pack(side=LEFT, fill=BOTH, expand=True, padx=5, pady=5)

        # Treeview per Partite
        cols_partite = ('id', 'numero_partita', 'tipo', 'stato', 'possessori', 'n_immobili')
        self.tree_partite = tb.Treeview(partite_labelframe, columns=cols_partite, show='headings', bootstyle='primary')
        self.tree_partite.heading('id', text='ID')
        self.tree_partite.heading('numero_partita', text='Numero')
        self.tree_partite.heading('tipo', text='Tipo')
        self.tree_partite.heading('stato', text='Stato')
        self.tree_partite.heading('possessori', text='Possessori')
        self.tree_partite.heading('n_immobili', text='N. Immobili')

        # Imposta larghezze colonne (aggiusta secondo necessità)
        self.tree_partite.column('id', width=50, anchor=CENTER)
        self.tree_partite.column('numero_partita', width=80, anchor=CENTER)
        self.tree_partite.column('tipo', width=100)
        self.tree_partite.column('stato', width=80, anchor=CENTER)
        self.tree_partite.column('possessori', width=250)
        self.tree_partite.column('n_immobili', width=80, anchor=CENTER)

        self.tree_partite.pack(fill=BOTH, expand=True)

        # Scrollbar per Partite
        scrollbar_partite_y = tb.Scrollbar(self.tree_partite, orient=VERTICAL, command=self.tree_partite.yview)
        self.tree_partite.configure(yscrollcommand=scrollbar_partite_y.set)
        scrollbar_partite_y.pack(side=RIGHT, fill=Y)
        scrollbar_partite_x = tb.Scrollbar(self.tree_partite, orient=HORIZONTAL, command=self.tree_partite.xview)
        self.tree_partite.configure(xscrollcommand=scrollbar_partite_x.set)
        scrollbar_partite_x.pack(side=BOTTOM, fill=X)

        # Menu contestuale per Partite (lo definiremo meglio dopo)
        self.partite_context_menu = tk.Menu(self, tearoff=0)
        self.partite_context_menu.add_command(label="Mostra Dettagli Partita (Non Impl.)")
        self.partite_context_menu.add_command(label="Genera Certificato Proprietà (Non Impl.)")
        self.partite_context_menu.add_command(label="Genera Report Genealogico (Non Impl.)")
        self.tree_partite.bind("<Button-3>", self.show_partite_context_menu)


    # --- Funzioni Logiche per Consultazione ---

    def load_comuni(self, search_term=None):
        """Carica o aggiorna l'elenco dei comuni nel Treeview."""
        # Pulisce il treeview precedente
        for i in self.tree_comuni.get_children():
            self.tree_comuni.delete(i)

        try:
            comuni_list = self.db.get_comuni(search_term=search_term)
            if comuni_list:
                for comune in comuni_list:
                    self.tree_comuni.insert('', END, values=(
                        comune.get('nome', 'N/D'),
                        comune.get('provincia', 'N/D'),
                        comune.get('regione', 'N/D')
                    ))
            else:
                 # Inserisci un messaggio se non ci sono risultati
                 if search_term:
                     self.tree_comuni.insert('', END, values=(f"Nessun comune trovato per '{search_term}'", "", ""))
                 else:
                      self.tree_comuni.insert('', END, values=("Nessun comune nel database", "", ""))

        except Exception as e:
            messagebox.showerror("Errore Database", f"Errore durante il caricamento dei comuni:\n{e}")
            # Potresti inserire un messaggio di errore nel treeview stesso
            self.tree_comuni.insert('', END, values=("Errore caricamento dati", "", ""))

    def search_comuni(self):
         """Esegue la ricerca dei comuni in base al testo nell'entry."""
         search_term = self.search_comuni_var.get().strip()
         self.load_comuni(search_term if search_term else None)

    def show_comuni_context_menu(self, event):
        """Mostra il menu contestuale per i comuni."""
        # Seleziona la riga su cui si è cliccato col destro
        iid = self.tree_comuni.identify_row(event.y)
        if iid:
            self.tree_comuni.selection_set(iid) # Seleziona la riga
            # Mostra il menu alle coordinate del click
            self.comuni_context_menu.post(event.x_root, event.y_root)
        # else: Non fare nulla se si clicca fuori dalle righe

    def get_selected_comune_name(self):
        """Restituisce il nome del comune attualmente selezionato nel tree_comuni."""
        selection = self.tree_comuni.selection()
        if selection:
            item = self.tree_comuni.item(selection[0]) # Prende il primo selezionato
            if item and 'values' in item and item['values']:
                return item['values'][0] # Il nome è nella prima colonna
        return None

    def cerca_partite_da_comune(self):
        """Cerca e visualizza le partite del comune selezionato."""
        selected_comune = self.get_selected_comune_name()
        if not selected_comune or "Nessun comune" in selected_comune or "Errore" in selected_comune:
            messagebox.showwarning("Selezione Mancante", "Seleziona un comune dalla lista prima.")
            return

        # Pulisce il treeview delle partite
        for i in self.tree_partite.get_children():
            self.tree_partite.delete(i)

        try:
            partite_list = self.db.get_partite_by_comune(selected_comune)
            if partite_list:
                 self.partite_labelframe.config(text=f"Partite di {selected_comune}") # Aggiorna titolo frame
                 for p in partite_list:
                     self.tree_partite.insert('', END, values=(
                         p.get('id'),
                         p.get('numero_partita'),
                         p.get('tipo'),
                         p.get('stato'),
                         p.get('possessori', ''), # Usa '' se manca
                         p.get('num_immobili', 0) # Usa 0 se manca
                     ))
            else:
                 self.partite_labelframe.config(text=f"Partite di {selected_comune}")
                 self.tree_partite.insert('', END, values=("", "Nessuna partita trovata", "", "", "", ""))

        except Exception as e:
            messagebox.showerror("Errore Database", f"Errore durante la ricerca delle partite:\n{e}")
            self.tree_partite.insert('', END, values=("", "Errore caricamento dati", "", "", "", ""))

    def cerca_possessori_da_comune(self):
         """ Funzione placeholder per cercare i possessori (da implementare con un nuovo Treeview o finestra) """
         selected_comune = self.get_selected_comune_name()
         if not selected_comune or "Nessun comune" in selected_comune or "Errore" in selected_comune:
             messagebox.showwarning("Selezione Mancante", "Seleziona un comune dalla lista prima.")
             return
         messagebox.showinfo("Da Implementare", f"Qui cercheremmo i possessori per il comune: {selected_comune}")
         # Qui dovresti implementare la logica per visualizzare i possessori,
         # magari in un nuovo Treeview o una finestra di dialogo dedicata.


    def show_partite_context_menu(self, event):
         """Mostra il menu contestuale per le partite."""
         iid = self.tree_partite.identify_row(event.y)
         if iid:
             # Controlla se la riga selezionata NON è un messaggio di "Nessuna partita" o "Errore"
             item_values = self.tree_partite.item(iid, 'values')
             if item_values and item_values[1] not in ("Nessuna partita trovata", "Errore caricamento dati"):
                 self.tree_partite.selection_set(iid)
                 self.partite_context_menu.post(event.x_root, event.y_root)
         # else: Non fare nulla se si clicca fuori o su righe non valide

    # --- Placeholder per le altre schede ---
    def create_inserimento_tab(self):
        inserimento_frame = tb.Frame(self.notebook, padding=10)
        self.notebook.add(inserimento_frame, text=" Inserimento/Gestione ")
        lbl = tb.Label(inserimento_frame, text="Funzionalità di inserimento e gestione dati (da implementare)")
        lbl.pack(padx=20, pady=20)

    def create_report_tab(self):
        report_frame = tb.Frame(self.notebook, padding=10)
        self.notebook.add(report_frame, text=" Report ")
        lbl = tb.Label(report_frame, text="Funzionalità di generazione report (da implementare)")
        lbl.pack(padx=20, pady=20)

    def create_manutenzione_tab(self):
        manutenzione_frame = tb.Frame(self.notebook, padding=10)
        self.notebook.add(manutenzione_frame, text=" Manutenzione ")
        lbl = tb.Label(manutenzione_frame, text="Funzionalità di manutenzione database (da implementare)")
        lbl.pack(padx=20, pady=20)

    def on_closing(self):
        """Chiamato quando la finestra viene chiusa."""
        if messagebox.askokcancel("Esci", "Vuoi veramente uscire dall'applicazione?"):
            if self.db and self.db.conn: # Controlla se db e conn esistono
                 self.db.disconnect()
            self.destroy()

if __name__ == "__main__":
    # Assicurati che ttkbootstrap sia installato: pip install ttkbootstrap
    # Assicurati che psycopg2 sia installato: pip install psycopg2-binary
    app = CatastoApp(theme='litera') # Prova altri temi: 'superhero', 'darkly', 'cerculean', 'cosmo', etc.
    app.mainloop()