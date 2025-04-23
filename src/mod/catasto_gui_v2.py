#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaccia Python per Gestione Catasto Storico
Versione 2.0 - Con Menu, Treeview, Menu Contestuali
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import sys
import json
from datetime import date, datetime

# Nuova importazione per il calendario
try:
    from tkcalendar import DateEntry
except ImportError:
    messagebox.showerror("Errore Dipendenza", "La libreria 'tkcalendar' non è installata.\nEsegui 'pip install tkcalendar' dal terminale.")
    sys.exit(1) # Esce se manca la dipendenza

# Importa il nostro DB Manager
try:
    from catasto_db_manager import CatastoDBManager
except ImportError:
     messagebox.showerror("Errore Importazione", "Il file 'catasto_db_manager.py' non è stato trovato.\nAssicurati che sia nella stessa cartella di questo script.")
     sys.exit(1)


# --- Finestra Toplevel per Registra Consultazione ---
class RegistraConsultazioneWindow(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.title("Registra Consultazione")
        self.geometry("500x350")
        self.resizable(False, False)
        self.transient(parent) # Lega alla finestra parente
        self.grab_set()        # Rendi modale

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

        self.wait_window() # Attende chiusura

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
            if not self.db_manager.conn or self.db_manager.conn.closed:
                 raise ConnectionError("Database non connesso.")

            success = self.db_manager.registra_consultazione(
                data_cons, richiedente, documento, motivazione, materiale, funzionario
            )
            if success:
                self.parent.set_status("Consultazione registrata con successo.") # Aggiorna status bar principale
                messagebox.showinfo("Successo", "Consultazione registrata con successo.", parent=self.parent) # Mostra sulla finestra principale
                self.destroy() # Chiude la finestra modale
            else:
                # La procedura potrebbe non restituire False esplicitamente, ma sollevare eccezione gestita sotto
                 messagebox.showerror("Errore Database", "Errore durante la registrazione della consultazione.\nControllare i log.", parent=self)
                 self.parent.set_status("Errore registrazione consultazione.")
        except ConnectionError as ce:
            messagebox.showerror("Errore Database", str(ce), parent=self)
            self.parent.set_status("Errore: Database non connesso.")
        except Exception as e:
            self.db_manager.rollback()
            messagebox.showerror("Errore Imprevisto", f"Errore durante la registrazione:\n{e}", parent=self)
            self.parent.set_status("Errore registrazione consultazione.")


# --- Finestra Toplevel per Registra Nuova Proprietà ---
class RegistraNuovaProprietaWindow(tk.Toplevel):
    def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.title("Registra Nuova Proprietà")
        self.geometry("750x650")
        self.transient(parent)
        self.grab_set()

        self.possessori_list = [] # Lista per tenere traccia dei possessori aggiunti
        self.immobili_list = []   # Lista per tenere traccia degli immobili aggiunti

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1) # Riga frame possessori
        main_frame.rowconfigure(2, weight=1) # Riga frame immobili

        # --- Dati Partita ---
        partita_frame = ttk.LabelFrame(main_frame, text="Dati Partita", padding="10")
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
        poss_main_frame = ttk.LabelFrame(main_frame, text="Possessori*", padding="10")
        poss_main_frame.grid(row=1, column=0, padx=5, pady=10, sticky="nsew") # Usa sticky nsew
        poss_main_frame.columnconfigure(0, weight=1)
        poss_main_frame.rowconfigure(1, weight=1) # Riga treeview possessori

        poss_input_frame = ttk.Frame(poss_main_frame)
        poss_input_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        poss_input_frame.columnconfigure(1, weight=1)
        poss_input_frame.columnconfigure(3, weight=1)

        ttk.Label(poss_input_frame, text="Nome Completo:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.poss_nome_entry = ttk.Entry(poss_input_frame)
        self.poss_nome_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(poss_input_frame, text="Cerca/Nuovo", command=self.gestisci_possessore).grid(row=0, column=4, padx=(10,0), pady=2)

        ttk.Label(poss_input_frame, text="Cognome Nome:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.poss_cgn_entry = ttk.Entry(poss_input_frame)
        self.poss_cgn_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(poss_input_frame, text="Paternità:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.poss_pat_entry = ttk.Entry(poss_input_frame)
        self.poss_pat_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(poss_input_frame, text="Quota:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.poss_quota_entry = ttk.Entry(poss_input_frame, width=15)
        self.poss_quota_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(poss_input_frame, text="(es. 1/2, opzionale)").grid(row=2, column=1, padx=5, pady=2, sticky="e")

        ttk.Button(poss_input_frame, text="Aggiungi Possessore alla Lista", command=self.aggiungi_possessore_lista).grid(row=3, column=0, columnspan=5, pady=5)


        poss_tree_frame = ttk.Frame(poss_main_frame)
        poss_tree_frame.grid(row=1, column=0, sticky="nsew") # Row 1 per il treeview
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
        ttk.Button(poss_main_frame, text="Rimuovi Selezionato", command=self.rimuovi_possessore_lista).grid(row=2, column=0, padx=5, pady=(5,0), sticky="w") # Row 2 per bottone rimuovi

        # --- Gestione Immobili ---
        imm_main_frame = ttk.LabelFrame(main_frame, text="Immobili*", padding="10")
        imm_main_frame.grid(row=2, column=0, padx=5, pady=10, sticky="nsew") # Row 2 per immobili
        imm_main_frame.columnconfigure(0, weight=1)
        imm_main_frame.rowconfigure(1, weight=1) # Riga treeview immobili


        imm_input_frame = ttk.Frame(imm_main_frame)
        imm_input_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        imm_input_frame.columnconfigure(1, weight=1)
        imm_input_frame.columnconfigure(3, weight=1)


        ttk.Label(imm_input_frame, text="Natura:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.imm_natura_entry = ttk.Entry(imm_input_frame)
        self.imm_natura_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(imm_input_frame, text="Località:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.imm_localita_entry = ttk.Entry(imm_input_frame)
        self.imm_localita_entry.grid(row=0, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(imm_input_frame, text="Tipo Loc:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.imm_tipo_loc_var = tk.StringVar(value="via")
        ttk.Combobox(imm_input_frame, textvariable=self.imm_tipo_loc_var, values=["via", "regione", "borgata", "frazione"], state="readonly", width=10).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(imm_input_frame, text="Classificazione:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.imm_class_entry = ttk.Entry(imm_input_frame)
        self.imm_class_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")

        ttk.Label(imm_input_frame, text="Piani:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.imm_piani_entry = ttk.Entry(imm_input_frame, width=5)
        self.imm_piani_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(imm_input_frame, text="Vani:").grid(row=2, column=2, padx=5, pady=2, sticky="w")
        self.imm_vani_entry = ttk.Entry(imm_input_frame, width=5)
        self.imm_vani_entry.grid(row=2, column=3, padx=5, pady=2, sticky="w")

        ttk.Label(imm_input_frame, text="Consistenza:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.imm_cons_entry = ttk.Entry(imm_input_frame)
        self.imm_cons_entry.grid(row=3, column=1, columnspan=3, padx=5, pady=2, sticky="ew")

        ttk.Button(imm_input_frame, text="Aggiungi Immobile alla Lista", command=self.aggiungi_immobile_lista).grid(row=4, column=0, columnspan=4, pady=5)


        imm_tree_frame = ttk.Frame(imm_main_frame)
        imm_tree_frame.grid(row=1, column=0, sticky="nsew") # Riga 1 per treeview
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
        ttk.Button(imm_main_frame, text="Rimuovi Selezionato", command=self.rimuovi_immobile_lista).grid(row=2, column=0, padx=5, pady=(5,0), sticky="w") # Riga 2 per bottone

        # --- Pulsanti Finali ---
        ttk.Label(main_frame, text="* Campi obbligatori").grid(row=3, column=0, padx=5, pady=10, sticky="e") # Riga 3 per label
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, pady=15) # Riga 4 per bottoni finali
        ttk.Button(button_frame, text="Registra Proprietà", command=self.registra).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=10)

        self.wait_window()

    # Metodi interni (gestisci_possessore, aggiungi*, rimuovi*, registra)
    def gestisci_possessore(self):
        nome_completo = self.poss_nome_entry.get().strip()
        comune = self.comune_entry.get().strip() # Prende il comune dalla sezione Partita
        if not nome_completo or not comune:
            messagebox.showwarning("Dati Mancanti", "Inserire Comune (nella sezione Dati Partita) e Nome Completo del possessore da cercare.", parent=self)
            return
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed:
                raise ConnectionError("Database non connesso.")
            poss_id = self.db_manager.check_possessore_exists(nome_completo, comune)
            if poss_id:
                 if messagebox.askyesno("Possessore Esistente", f"Possessore '{nome_completo}' trovato nel comune '{comune}' (ID: {poss_id}).\nVuoi usarlo?", parent=self):
                    self.poss_cgn_entry.delete(0, tk.END)
                    self.poss_pat_entry.delete(0, tk.END)
                    messagebox.showinfo("Info", "Possessore selezionato. Inserisci la quota (se necessaria) e aggiungi alla lista.", parent=self)
                 else:
                    self.poss_nome_entry.delete(0, tk.END) # Pulisce per inserire un nome diverso
            else:
                messagebox.showinfo("Possessore Non Trovato", f"Possessore '{nome_completo}' non trovato per il comune '{comune}'.\nInserisci Cognome Nome e Paternità per aggiungerlo come nuovo possessore.", parent=self)
                self.poss_cgn_entry.focus() # Mette il focus sul campo successivo
        except ConnectionError as ce:
             messagebox.showerror("Errore Database", str(ce), parent=self)
        except Exception as e:
            messagebox.showerror("Errore Ricerca", f"Errore durante la ricerca del possessore:\n{e}", parent=self)

    def aggiungi_possessore_lista(self):
        nome = self.poss_nome_entry.get().strip()
        cognome_nome = self.poss_cgn_entry.get().strip()
        paternita = self.poss_pat_entry.get().strip()
        quota = self.poss_quota_entry.get().strip()
        if not nome:
            messagebox.showwarning("Dati Mancanti", "Inserire almeno il Nome Completo del possessore.", parent=self)
            return
        possessore_data = {
            "nome_completo": nome, "cognome_nome": cognome_nome if cognome_nome else None,
            "paternita": paternita if paternita else None, "quota": quota if quota else None
        }
        values = (nome, cognome_nome or "", paternita or "", quota or "")
        item_id = self.poss_tree.insert("", tk.END, values=values)
        self.possessori_list.append({"id": item_id, "data": possessore_data})
        self.poss_nome_entry.delete(0, tk.END); self.poss_cgn_entry.delete(0, tk.END); self.poss_pat_entry.delete(0, tk.END); self.poss_quota_entry.delete(0, tk.END)
        self.poss_nome_entry.focus()

    def rimuovi_possessore_lista(self):
        selected_item = self.poss_tree.selection()
        if not selected_item: messagebox.showwarning("Nessuna Selezione", "Selezionare un possessore da rimuovere.", parent=self); return
        item_id_to_remove = selected_item[0]
        self.poss_tree.delete(item_id_to_remove)
        self.possessori_list = [p for p in self.possessori_list if p["id"] != item_id_to_remove]

    def aggiungi_immobile_lista(self):
        natura = self.imm_natura_entry.get().strip(); localita = self.imm_localita_entry.get().strip()
        tipo_localita = self.imm_tipo_loc_var.get(); classificazione = self.imm_class_entry.get().strip()
        piani_str = self.imm_piani_entry.get().strip(); vani_str = self.imm_vani_entry.get().strip()
        consistenza = self.imm_cons_entry.get().strip()
        if not natura or not localita: messagebox.showwarning("Dati Mancanti", "Inserire almeno Natura e Località.", parent=self); return
        piani = None; vani = None
        try:
            if piani_str: piani = int(piani_str)
            if vani_str: vani = int(vani_str)
        except ValueError: messagebox.showerror("Input Errato", "Piani e Vani devono essere numeri interi.", parent=self); return
        immobile_data = {
            "natura": natura, "localita": localita, "tipo_localita": tipo_localita,
            "classificazione": classificazione if classificazione else None, "numero_piani": piani,
            "numero_vani": vani, "consistenza": consistenza if consistenza else None
        }
        values = (natura, localita, tipo_localita, classificazione or "", str(piani or ""), str(vani or ""), consistenza or "")
        item_id = self.imm_tree.insert("", tk.END, values=values)
        self.immobili_list.append({"id": item_id, "data": immobile_data})
        self.imm_natura_entry.delete(0, tk.END); self.imm_localita_entry.delete(0, tk.END); self.imm_class_entry.delete(0, tk.END)
        self.imm_piani_entry.delete(0, tk.END); self.imm_vani_entry.delete(0, tk.END); self.imm_cons_entry.delete(0, tk.END)
        self.imm_natura_entry.focus()

    def rimuovi_immobile_lista(self):
        selected_item = self.imm_tree.selection()
        if not selected_item: messagebox.showwarning("Nessuna Selezione", "Selezionare un immobile da rimuovere.", parent=self); return
        item_id_to_remove = selected_item[0]
        self.imm_tree.delete(item_id_to_remove)
        self.immobili_list = [i for i in self.immobili_list if i["id"] != item_id_to_remove]

    def registra(self):
        comune = self.comune_entry.get().strip(); numero_str = self.numero_entry.get().strip()
        data_imp = self.data_impianto_entry.get_date()
        if not comune or not numero_str: messagebox.showwarning("Dati Mancanti", "Inserire Comune e Numero Partita.", parent=self); return
        try: numero_partita = int(numero_str)
        except ValueError: messagebox.showerror("Input Errato", "Il Numero Partita deve essere un intero.", parent=self); return
        if not self.possessori_list: messagebox.showwarning("Dati Mancanti", "Aggiungere almeno un possessore.", parent=self); return
        if not self.immobili_list: messagebox.showwarning("Dati Mancanti", "Aggiungere almeno un immobile.", parent=self); return
        possessori_json_list = [p["data"] for p in self.possessori_list]
        immobili_json_list = [i["data"] for i in self.immobili_list]
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            success = self.db_manager.registra_nuova_proprieta(comune, numero_partita, data_imp, possessori_json_list, immobili_json_list)
            if success:
                 self.parent.set_status(f"Nuova proprietà (Partita {numero_partita}, Comune {comune}) registrata.")
                 messagebox.showinfo("Successo", f"Nuova proprietà registrata con successo.", parent=self.parent)
                 self.destroy()
            else:
                 messagebox.showerror("Errore Database", "Errore durante la registrazione.\nControllare i log.", parent=self)
                 self.parent.set_status("Errore registrazione nuova proprietà.")
        except ConnectionError as ce: messagebox.showerror("Errore Database", str(ce), parent=self); self.parent.set_status("Errore: Database non connesso.")
        except Exception as e: self.db_manager.rollback(); messagebox.showerror("Errore Imprevisto", f"Errore: {e}", parent=self); self.parent.set_status("Errore registrazione nuova proprietà.")


# --- Finestra Toplevel per Registra Passaggio Proprietà ---
class RegistraPassaggioWindow(tk.Toplevel):
     def __init__(self, parent, db_manager):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.title("Registra Passaggio Proprietà")
        self.geometry("800x750")
        self.transient(parent)
        self.grab_set()

        self.nuovi_possessori_list = []
        self.immobili_trasferiti_ids = []

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1) # Nuovi Possessori frame
        main_frame.rowconfigure(5, weight=1) # Immobili da Trasferire frame

        # --- Dati Origine e Destinazione ---
        part_frame = ttk.LabelFrame(main_frame, text="Partite Coinvolte", padding="10")
        part_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        part_frame.columnconfigure(1, weight=1)
        part_frame.columnconfigure(3, weight=1)

        ttk.Label(part_frame, text="ID Partita Origine*:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.partita_origine_id_entry = ttk.Entry(part_frame, width=10)
        self.partita_origine_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(part_frame, text="Carica Immobili Origine", command=self.carica_immobili_origine).grid(row=0, column=2, padx=10, pady=5)

        ttk.Label(part_frame, text="Comune Dest.*:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.nuovo_comune_entry = ttk.Entry(part_frame)
        self.nuovo_comune_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(part_frame, text="Numero Nuova Partita*:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.nuovo_numero_entry = ttk.Entry(part_frame, width=10)
        self.nuovo_numero_entry.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        # --- Dati Variazione ---
        var_frame = ttk.LabelFrame(main_frame, text="Dati Variazione", padding="10")
        var_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
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
        contr_frame = ttk.LabelFrame(main_frame, text="Dati Contratto/Atto", padding="10")
        contr_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
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
        note_frame = ttk.LabelFrame(main_frame, text="Note", padding="10")
        note_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        self.note_text = scrolledtext.ScrolledText(note_frame, height=3, width=60, wrap=tk.WORD)
        self.note_text.pack(expand=True, fill="both", padx=5, pady=5)

        # --- Gestione Nuovi Possessori ---
        nuovi_poss_main_frame = ttk.LabelFrame(main_frame, text="Nuovi Possessori (Opzionale)", padding="10")
        nuovi_poss_main_frame.grid(row=4, column=0, padx=5, pady=10, sticky="nsew")
        nuovi_poss_main_frame.columnconfigure(0, weight=1)
        nuovi_poss_main_frame.rowconfigure(1, weight=1) # Riga treeview

        poss_input_frame = ttk.Frame(nuovi_poss_main_frame)
        poss_input_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        poss_input_frame.columnconfigure(1, weight=1)
        poss_input_frame.columnconfigure(3, weight=1)

        ttk.Label(poss_input_frame, text="Nome Completo:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.nuovo_poss_nome_entry = ttk.Entry(poss_input_frame)
        self.nuovo_poss_nome_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(poss_input_frame, text="Cerca/Nuovo", command=self.gestisci_nuovo_possessore).grid(row=0, column=4, padx=(10,0), pady=2)
        ttk.Label(poss_input_frame, text="Cognome Nome:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.nuovo_poss_cgn_entry = ttk.Entry(poss_input_frame)
        self.nuovo_poss_cgn_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ttk.Label(poss_input_frame, text="Paternità:").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.nuovo_poss_pat_entry = ttk.Entry(poss_input_frame)
        self.nuovo_poss_pat_entry.grid(row=1, column=3, padx=5, pady=2, sticky="ew")
        ttk.Label(poss_input_frame, text="Quota:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.nuovo_poss_quota_entry = ttk.Entry(poss_input_frame, width=15)
        self.nuovo_poss_quota_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        ttk.Button(poss_input_frame, text="Aggiungi Possessore alla Lista", command=self.aggiungi_nuovo_possessore_lista).grid(row=3, column=0, columnspan=5, pady=5)

        poss_tree_frame = ttk.Frame(nuovi_poss_main_frame)
        poss_tree_frame.grid(row=1, column=0, sticky="nsew")
        poss_tree_frame.rowconfigure(0, weight=1)
        poss_tree_frame.columnconfigure(0, weight=1)
        poss_cols = ("nome_completo", "cognome_nome", "paternita", "quota")
        self.nuovi_poss_tree = ttk.Treeview(poss_tree_frame, columns=poss_cols, show="headings", height=3)
        for col in poss_cols: self.nuovi_poss_tree.heading(col, text=col.replace('_', ' ').title()); self.nuovi_poss_tree.column(col, width=160, anchor=tk.W)
        poss_vsb = ttk.Scrollbar(poss_tree_frame, orient="vertical", command=self.nuovi_poss_tree.yview)
        self.nuovi_poss_tree.configure(yscrollcommand=poss_vsb.set)
        self.nuovi_poss_tree.grid(row=0, column=0, sticky="nsew")
        poss_vsb.grid(row=0, column=1, sticky="ns")
        ttk.Button(nuovi_poss_main_frame, text="Rimuovi Selezionato", command=self.rimuovi_nuovo_possessore_lista).grid(row=2, column=0, padx=5, pady=(5,0), sticky="w")

        # --- Selezione Immobili da Trasferire ---
        imm_trasf_frame = ttk.LabelFrame(main_frame, text="Immobili da Trasferire (Opzionale)", padding="10")
        imm_trasf_frame.grid(row=5, column=0, padx=5, pady=10, sticky="nsew")
        imm_trasf_frame.rowconfigure(0, weight=1)
        imm_trasf_frame.columnconfigure(0, weight=1)

        imm_cols_trasf = ("id", "natura", "localita", "classificazione")
        self.imm_trasf_tree = ttk.Treeview(imm_trasf_frame, columns=imm_cols_trasf, show="headings", height=4, selectmode="extended")
        for col in imm_cols_trasf: self.imm_trasf_tree.heading(col, text=col.replace('_', ' ').title()); self.imm_trasf_tree.column(col, width=150 if col != "id" else 50, anchor=tk.W)
        imm_vsb_trasf = ttk.Scrollbar(imm_trasf_frame, orient="vertical", command=self.imm_trasf_tree.yview)
        self.imm_trasf_tree.configure(yscrollcommand=imm_vsb_trasf.set)
        self.imm_trasf_tree.grid(row=0, column=0, sticky="nsew")
        imm_vsb_trasf.grid(row=0, column=1, sticky="ns")

        # --- Pulsanti Finali ---
        ttk.Label(main_frame, text="* Campi obbligatori").grid(row=6, column=0, padx=5, pady=10, sticky="e")
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, pady=15)
        ttk.Button(button_frame, text="Registra Passaggio", command=self.registra).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Annulla", command=self.destroy).pack(side=tk.LEFT, padx=10)

        self.wait_window()

     # Metodi interni (carica_immobili, gestisci_nuovo_possessore, aggiungi*, rimuovi*, registra)
     def carica_immobili_origine(self):
         partita_id_str = self.partita_origine_id_entry.get().strip()
         if not partita_id_str: messagebox.showwarning("ID Mancante", "Inserire l'ID della Partita di Origine.", parent=self); return
         try: partita_id = int(partita_id_str)
         except ValueError: messagebox.showerror("Input Errato", "L'ID Partita Origine deve essere un numero intero.", parent=self); return
         try:
             if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
             for item in self.imm_trasf_tree.get_children(): self.imm_trasf_tree.delete(item)
             partita_details = self.db_manager.get_partita_details(partita_id)
             if not partita_details or 'immobili' not in partita_details or not partita_details['immobili']: messagebox.showinfo("Nessun Immobile", f"Nessun immobile trovato per la partita ID {partita_id}.", parent=self); return
             for imm in partita_details['immobili']:
                 values = (imm.get('id', ''), imm.get('natura', ''), imm.get('localita_nome', ''), imm.get('classificazione', ''))
                 self.imm_trasf_tree.insert("", tk.END, values=values, iid=imm.get('id')) # Usa ID db come iid
         except ConnectionError as ce: messagebox.showerror("Errore Database", str(ce), parent=self)
         except Exception as e: messagebox.showerror("Errore Caricamento", f"Errore durante il caricamento degli immobili:\n{e}", parent=self)

     def gestisci_nuovo_possessore(self):
        nome_completo = self.nuovo_poss_nome_entry.get().strip(); comune = self.nuovo_comune_entry.get().strip()
        if not nome_completo or not comune: messagebox.showwarning("Dati Mancanti", "Inserire Nuovo Comune e Nome Completo del possessore da cercare.", parent=self); return
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            poss_id = self.db_manager.check_possessore_exists(nome_completo, comune)
            if poss_id:
                 if messagebox.askyesno("Possessore Esistente", f"Possessore '{nome_completo}' trovato nel comune '{comune}' (ID: {poss_id}).\nVuoi usarlo?", parent=self):
                    self.nuovo_poss_cgn_entry.delete(0, tk.END); self.nuovo_poss_pat_entry.delete(0, tk.END)
                    messagebox.showinfo("Info", "Possessore selezionato. Inserisci la quota (se necessaria) e aggiungi alla lista.", parent=self)
                 else: self.nuovo_poss_nome_entry.delete(0, tk.END)
            else:
                messagebox.showinfo("Possessore Non Trovato", f"Possessore '{nome_completo}' non trovato.\nInserisci Cognome Nome e Paternità per aggiungerlo come nuovo.", parent=self)
                self.nuovo_poss_cgn_entry.focus()
        except ConnectionError as ce: messagebox.showerror("Errore Database", str(ce), parent=self)
        except Exception as e: messagebox.showerror("Errore Ricerca", f"Errore:\n{e}", parent=self)

     def aggiungi_nuovo_possessore_lista(self):
        nome = self.nuovo_poss_nome_entry.get().strip(); cognome_nome = self.nuovo_poss_cgn_entry.get().strip()
        paternita = self.nuovo_poss_pat_entry.get().strip(); quota = self.nuovo_poss_quota_entry.get().strip()
        if not nome: messagebox.showwarning("Dati Mancanti", "Inserire almeno il Nome Completo.", parent=self); return
        possessore_data = {"nome_completo": nome, "cognome_nome": cognome_nome or None, "paternita": paternita or None, "quota": quota or None}
        values = (nome, cognome_nome or "", paternita or "", quota or "")
        item_id = self.nuovi_poss_tree.insert("", tk.END, values=values)
        self.nuovi_possessori_list.append({"id": item_id, "data": possessore_data})
        self.nuovo_poss_nome_entry.delete(0, tk.END); self.nuovo_poss_cgn_entry.delete(0, tk.END); self.nuovo_poss_pat_entry.delete(0, tk.END); self.nuovo_poss_quota_entry.delete(0, tk.END)
        self.nuovo_poss_nome_entry.focus()

     def rimuovi_nuovo_possessore_lista(self):
        selected_item = self.nuovi_poss_tree.selection()
        if not selected_item: messagebox.showwarning("Nessuna Selezione", "Selezionare un possessore da rimuovere.", parent=self); return
        item_id_to_remove = selected_item[0]; self.nuovi_poss_tree.delete(item_id_to_remove)
        self.nuovi_possessori_list = [p for p in self.nuovi_possessori_list if p["id"] != item_id_to_remove]

     def registra(self):
        partita_origine_id_str = self.partita_origine_id_entry.get().strip(); nuovo_comune = self.nuovo_comune_entry.get().strip()
        nuovo_numero_str = self.nuovo_numero_entry.get().strip(); tipo_variazione = self.tipo_var_var.get()
        data_variazione = self.data_var_entry.get_date(); tipo_contratto = self.tipo_contr_entry.get().strip()
        data_contratto = self.data_contr_entry.get_date(); notaio = self.notaio_entry.get().strip()
        repertorio = self.repertorio_entry.get().strip(); note = self.note_text.get("1.0", tk.END).strip()
        if not partita_origine_id_str or not nuovo_comune or not nuovo_numero_str or not tipo_variazione or not tipo_contratto:
            messagebox.showwarning("Dati Mancanti", "Compilare tutti i campi obbligatori (*).", parent=self); return
        try: partita_origine_id = int(partita_origine_id_str); nuovo_numero_partita = int(nuovo_numero_str)
        except ValueError: messagebox.showerror("Input Errato", "ID Partita Origine e Numero Nuova Partita devono essere interi.", parent=self); return
        nuovi_possessori_json_list = [p["data"] for p in self.nuovi_possessori_list] if self.nuovi_possessori_list else None
        selected_imm_items = self.imm_trasf_tree.selection()
        immobili_da_trasferire = None
        if selected_imm_items:
             try: immobili_da_trasferire = [int(item_id) for item_id in selected_imm_items]
             except ValueError: messagebox.showerror("Errore Interno", "Errore lettura ID immobili selezionati.", parent=self); return
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            success = self.db_manager.registra_passaggio_proprieta(
                partita_origine_id=partita_origine_id, comune_nome=nuovo_comune, numero_partita=nuovo_numero_partita,
                tipo_variazione=tipo_variazione, data_variazione=data_variazione, tipo_contratto=tipo_contratto,
                data_contratto=data_contratto, notaio=notaio or None, repertorio=repertorio or None,
                nuovi_possessori=nuovi_possessori_json_list, immobili_da_trasferire=immobili_da_trasferire, note=note or None
            )
            if success:
                 self.parent.set_status(f"Passaggio di proprietà registrato (Nuova Partita {nuovo_numero_partita}, Comune {nuovo_comune}).")
                 messagebox.showinfo("Successo", f"Passaggio di proprietà registrato con successo.", parent=self.parent)
                 self.destroy()
            else:
                 messagebox.showerror("Errore Database", "Errore durante la registrazione del passaggio.\nControllare i log.", parent=self)
                 self.parent.set_status("Errore registrazione passaggio proprietà.")
        except ConnectionError as ce: messagebox.showerror("Errore Database", str(ce), parent=self); self.parent.set_status("Errore: Database non connesso.")
        except Exception as e: self.db_manager.rollback(); messagebox.showerror("Errore Imprevisto", f"Errore: {e}", parent=self); self.parent.set_status("Errore registrazione passaggio proprietà.")


# --- Classe Principale dell'Applicazione GUI (Versione 2 - Corretta) ---
# (Definizione spostata PRIMA di main_gui_v2)
class CatastoAppV2(tk.Tk):
    def __init__(self, db_config):
        super().__init__()
        self.title("Gestore Catasto Storico V2")
        self.geometry("950x700")

        # --- Stile TTK ---
        style = ttk.Style(self)
        try:
            available_themes = style.theme_names()
            if 'clam' in available_themes: style.theme_use('clam')
            elif 'vista' in available_themes: style.theme_use('vista')
            elif 'xpnative' in available_themes: style.theme_use('xpnative')
            elif 'winnative' in available_themes: style.theme_use('winnative')
        except tk.TclError: print("Nessun tema ttk aggiuntivo trovato, usando default.")

        # --- Connessione al Database ---
        self.db_manager = CatastoDBManager(**db_config)
        self.initial_connection_success = False # Imposta default
        try:
            if self.db_manager.connect():
                self.initial_connection_success = True
        except Exception as e:
             print(f"Errore iniziale connessione DB: {e}") # Logga l'errore
             # Mostra errore solo se NON è già stato mostrato da connect()
             # (Potrebbe essere duplicato se connect() usa messagebox)
             # messagebox.showerror("Errore Database Iniziale", f"Impossibile connettersi: {e}")

        # --- Variabile per tenere traccia dell'ID selezionato ---
        self.selected_item_id = None

        # --- Creazione Menu Principale ---
        self.create_menu()

        # --- Creazione Interfaccia a Schede (Tabs) ---
        self.notebook = ttk.Notebook(self)
        self.tab_consultazione = ttk.Frame(self.notebook)
        self.tab_inserimento = ttk.Frame(self.notebook)
        self.tab_report = ttk.Frame(self.notebook)
        self.tab_manutenzione = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_consultazione, text="Consultazione Dati")
        self.notebook.add(self.tab_inserimento, text="Inserimento e Gestione")
        self.notebook.add(self.tab_report, text="Generazione Report")
        self.notebook.add(self.tab_manutenzione, text="Manutenzione DB")
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # Popola le schede
        self.crea_tab_consultazione()
        self.crea_tab_inserimento()
        self.crea_tab_report()
        self.crea_tab_manutenzione()

        # --- Creazione Barra di Stato ---
        self.status_bar = ttk.Label(self, text="Pronto", relief=tk.SUNKEN, anchor=tk.W, padding=2)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        if self.initial_connection_success:
             self.set_status("Connesso al database.")
        else:
             self.set_status("Non connesso. Usare File -> Connetti o Impostazioni.")

        # --- Gestione Chiusura Finestra ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- Metodi per Aprire le Finestre Toplevel (DEFINITI PRIMA di create_menu) ---
    def open_registra_consultazione_window(self):
        if not self.db_manager.conn or self.db_manager.conn.closed:
            messagebox.showerror("Errore", "Connessione al database non attiva.", parent=self)
            return
        window = RegistraConsultazioneWindow(self, self.db_manager)

    def open_registra_nuova_proprieta_window(self):
        if not self.db_manager.conn or self.db_manager.conn.closed:
            messagebox.showerror("Errore", "Connessione al database non attiva.", parent=self)
            return
        window = RegistraNuovaProprietaWindow(self, self.db_manager)

    def open_registra_passaggio_window(self):
        if not self.db_manager.conn or self.db_manager.conn.closed:
            messagebox.showerror("Errore", "Connessione al database non attiva.", parent=self)
            return
        window = RegistraPassaggioWindow(self, self.db_manager)

    # --- Metodi Utilità ---
    def set_status(self, message):
        self.status_bar.config(text=message)

    def on_closing(self):
        if messagebox.askokcancel("Esci", "Vuoi chiudere l'applicazione?"):
            if self.db_manager and self.db_manager.conn and not self.db_manager.conn.closed:
                 self.db_manager.disconnect()
                 print("Connessione al database chiusa.")
            self.destroy()

    # --- Creazione Menu (ora può usare i metodi open_*) ---
    def create_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Connetti/Riconnetti", command=self.connect_db)
        file_menu.add_command(label="Impostazioni Connessione", command=self.show_connection_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)

        op_menu = tk.Menu(menubar, tearoff=0)
        op_menu.add_command(label="Aggiungi Comune", command=self.trigger_add_comune)
        op_menu.add_command(label="Aggiungi Possessore", command=self.trigger_add_possessore)
        op_menu.add_separator()
        op_menu.add_command(label="Registra Nuova Proprietà", command=self.open_registra_nuova_proprieta_window)
        op_menu.add_command(label="Registra Passaggio Proprietà", command=self.open_registra_passaggio_window)
        op_menu.add_command(label="Registra Consultazione", command=self.open_registra_consultazione_window)
        menubar.add_cascade(label="Operazioni", menu=op_menu)

        report_menu = tk.Menu(menubar, tearoff=0)
        report_menu.add_command(label="Genera Certificato Proprietà", command=self.trigger_report_certificato)
        report_menu.add_command(label="Genera Report Genealogico", command=self.trigger_report_genealogico)
        report_menu.add_command(label="Genera Report Possessore", command=self.trigger_report_possessore)
        menubar.add_cascade(label="Report", menu=report_menu)

        man_menu = tk.Menu(menubar, tearoff=0)
        man_menu.add_command(label="Verifica Integrità Database", command=self.verifica_integrita)
        menubar.add_cascade(label="Manutenzione", menu=man_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Informazioni", command=self.show_about)
        menubar.add_cascade(label="Aiuto", menu=help_menu)

        self.config(menu=menubar)

    # --- Metodi di Connessione e Impostazioni ---
    def connect_db(self):
        if self.db_manager.connect():
            self.set_status("Connesso al database.")
            messagebox.showinfo("Connessione", "Connessione al database stabilita con successo.", parent=self)
        else:
            self.set_status("Errore di connessione. Controllare impostazioni e server.")

    def show_connection_settings(self):
        settings_window = tk.Toplevel(self)
        settings_window.title("Impostazioni Connessione")
        settings_window.geometry("400x300")
        settings_window.transient(self)
        settings_window.grab_set()

        ttk.Label(settings_window, text="Impostazioni Database", font=("Helvetica", 12)).pack(pady=10)
        form_frame = ttk.Frame(settings_window, padding="10")
        form_frame.pack(fill="both", expand=True)
        # Utilizza i parametri attuali del db_manager come default
        current_config = self.db_manager.conn_params if self.db_manager.conn_params else {}

        fields = ["host", "port", "dbname", "user", "password"]
        labels = ["Host:", "Porta:", "Nome DB:", "Utente:", "Password:"]
        entries = {}
        for i, field in enumerate(fields):
            ttk.Label(form_frame, text=labels[i]).grid(row=i, column=0, sticky=tk.W, pady=5, padx=5)
            entry = ttk.Entry(form_frame, width=30)
            if field == "password": entry.config(show="*")
            entry.grid(row=i, column=1, pady=5, padx=5, sticky=tk.EW)
            entry.insert(0, current_config.get(field, ""))
            entries[field] = entry
            form_frame.columnconfigure(1, weight=1)

        def save_settings():
            new_config = {}
            for field, entry in entries.items(): new_config[field] = entry.get()
            try: new_config["port"] = int(new_config["port"])
            except ValueError: messagebox.showerror("Errore", "La porta deve essere un numero.", parent=settings_window); return
            # Aggiorna la configurazione del db_manager esistente
            self.db_manager.conn_params = new_config
            # Mantiene lo schema se era già impostato
            self.db_manager.schema = getattr(self.db_manager, 'schema', 'catasto')

            if self.db_manager.connect():
                messagebox.showinfo("Successo", "Connessione stabilita con successo.", parent=self)
                self.set_status("Connesso al database.")
                settings_window.destroy()
            else: self.set_status("Errore di connessione.") # Errore già mostrato da connect()

        buttons_frame = ttk.Frame(settings_window)
        buttons_frame.pack(pady=15)
        ttk.Button(buttons_frame, text="Salva e Connetti", command=save_settings).pack(side=tk.LEFT, padx=10)
        ttk.Button(buttons_frame, text="Annulla", command=settings_window.destroy).pack(side=tk.LEFT, padx=10)
        settings_window.wait_window()

    # --- Metodo Info ---
    def show_about(self):
        messagebox.showinfo("Informazioni",
                          "Gestore Catasto Storico V2\n\n"
                          "Applicazione per l'interazione con il database del catasto storico.\n"
                          "Basata su Tkinter e CatastoDBManager.",
                          parent=self)

    # --- Metodi Trigger Menu ---
    def trigger_add_comune(self):
        self.notebook.select(self.tab_inserimento)
        if hasattr(self, 'comune_nome_entry'): self.comune_nome_entry.focus_set()
    def trigger_add_possessore(self):
        self.notebook.select(self.tab_inserimento)
        if hasattr(self, 'poss_comune_entry'): self.poss_comune_entry.focus_set()
    def trigger_report_certificato(self):
        self.notebook.select(self.tab_report)
        if hasattr(self, 'report_combobox'): self.report_type_var.set("Certificato Proprietà"); self.report_id_entry.focus_set()
    def trigger_report_genealogico(self):
        self.notebook.select(self.tab_report)
        if hasattr(self, 'report_combobox'): self.report_type_var.set("Report Genealogico"); self.report_id_entry.focus_set()
    def trigger_report_possessore(self):
        self.notebook.select(self.tab_report)
        if hasattr(self, 'report_combobox'): self.report_type_var.set("Report Possessore"); self.report_id_entry.focus_set()

    # --- Metodi Creazione Schede ---
    def crea_tab_consultazione(self):
        tab = self.tab_consultazione
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        top_frame = ttk.Frame(tab, padding="5")
        top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ttk.Label(top_frame, text="Cerca per:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_type_var = tk.StringVar(value="Comuni")
        search_options = ["Comuni", "Partite per Comune", "Possessori per Comune", "Partite (Avanzato)"]
        search_combo = ttk.Combobox(top_frame, textvariable=self.search_type_var, values=search_options, state="readonly", width=20)
        search_combo.pack(side=tk.LEFT, padx=5)
        search_combo.bind("<<ComboboxSelected>>", self.update_search_fields)
        self.search_entry1_label = ttk.Label(top_frame, text="Nome:")
        self.search_entry1_label.pack(side=tk.LEFT, padx=(10, 0))
        self.search_entry1 = ttk.Entry(top_frame, width=25)
        self.search_entry1.pack(side=tk.LEFT, padx=5)
        self.search_advanced_frame = ttk.Frame(top_frame)
        self.search_entry2_label = ttk.Label(self.search_advanced_frame, text="Num. Partita:")
        self.search_entry2 = ttk.Entry(self.search_advanced_frame, width=10)
        self.search_entry3_label = ttk.Label(self.search_advanced_frame, text="Possessore:")
        self.search_entry3 = ttk.Entry(self.search_advanced_frame, width=20)
        self.search_entry4_label = ttk.Label(self.search_advanced_frame, text="Natura Imm.:")
        self.search_entry4 = ttk.Entry(self.search_advanced_frame, width=15)
        ttk.Button(top_frame, text="Cerca", command=self.esegui_ricerca_consultazione).pack(side=tk.LEFT, padx=10)
        ttk.Button(top_frame, text="Pulisci", command=self.pulisci_risultati_consultazione).pack(side=tk.LEFT, padx=5)
        tree_frame = ttk.Frame(tab)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.consult_tree = ttk.Treeview(tree_frame, show="headings")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.consult_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.consult_tree.xview)
        self.consult_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.consult_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.consult_context_menu = tk.Menu(self.consult_tree, tearoff=0)
        self.consult_tree.bind("<Button-3>", self.show_consult_context_menu)
        self.consult_tree.bind("<Double-1>", self.on_consult_tree_double_click)
        self.update_search_fields()
        self.setup_treeview("Comuni")

    def crea_tab_inserimento(self):
        tab = self.tab_inserimento
        tab.columnconfigure(0, weight=1)
        content_frame = ttk.Frame(tab, padding="10")
        content_frame.grid(row=0, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        comune_frame = ttk.LabelFrame(content_frame, text="Aggiungi Nuovo Comune", padding="10")
        comune_frame.grid(row=0, column=0, padx=5, pady=10, sticky='ew')
        comune_frame.columnconfigure(1, weight=1)
        ttk.Label(comune_frame, text="Nome:").grid(row=0, column=0, padx=5, pady=3, sticky='w')
        self.comune_nome_entry = ttk.Entry(comune_frame)
        self.comune_nome_entry.grid(row=0, column=1, padx=5, pady=3, sticky='ew')
        ttk.Label(comune_frame, text="Provincia:").grid(row=1, column=0, padx=5, pady=3, sticky='w')
        self.comune_provincia_entry = ttk.Entry(comune_frame)
        self.comune_provincia_entry.grid(row=1, column=1, padx=5, pady=3, sticky='ew')
        ttk.Label(comune_frame, text="Regione:").grid(row=2, column=0, padx=5, pady=3, sticky='w')
        self.comune_regione_entry = ttk.Entry(comune_frame)
        self.comune_regione_entry.grid(row=2, column=1, padx=5, pady=3, sticky='ew')
        ttk.Button(comune_frame, text="Aggiungi Comune", command=self.aggiungi_comune).grid(row=3, column=0, columnspan=2, pady=10)
        poss_frame = ttk.LabelFrame(content_frame, text="Aggiungi Nuovo Possessore", padding="10")
        poss_frame.grid(row=1, column=0, padx=5, pady=10, sticky='ew')
        poss_frame.columnconfigure(1, weight=1)
        ttk.Label(poss_frame, text="Comune*:").grid(row=0, column=0, padx=5, pady=3, sticky='w')
        self.poss_comune_entry = ttk.Entry(poss_frame)
        self.poss_comune_entry.grid(row=0, column=1, padx=5, pady=3, sticky='ew')
        ttk.Label(poss_frame, text="Cognome e Nome*:").grid(row=1, column=0, padx=5, pady=3, sticky='w')
        self.poss_cognome_nome_entry = ttk.Entry(poss_frame)
        self.poss_cognome_nome_entry.grid(row=1, column=1, padx=5, pady=3, sticky='ew')
        ttk.Label(poss_frame, text="Paternità:").grid(row=2, column=0, padx=5, pady=3, sticky='w')
        self.poss_paternita_entry = ttk.Entry(poss_frame)
        self.poss_paternita_entry.grid(row=2, column=1, padx=5, pady=3, sticky='ew')
        ttk.Label(poss_frame, text="(es. 'fu Roberto')").grid(row=2, column=2, padx=5, pady=3, sticky='w')
        ttk.Label(poss_frame, text="Nome Completo:").grid(row=3, column=0, padx=5, pady=3, sticky='w')
        self.poss_nome_completo_entry = ttk.Entry(poss_frame)
        self.poss_nome_completo_entry.grid(row=3, column=1, padx=5, pady=3, sticky='ew')
        ttk.Label(poss_frame, text="(opzionale, calcolato se vuoto)").grid(row=3, column=2, padx=5, pady=3, sticky='w')
        ttk.Button(poss_frame, text="Aggiungi Possessore", command=self.aggiungi_possessore).grid(row=4, column=0, columnspan=3, pady=10)
        action_frame = ttk.LabelFrame(content_frame, text="Altre Operazioni di Inserimento", padding="10")
        action_frame.grid(row=2, column=0, padx=5, pady=10, sticky='ew')
        ttk.Button(action_frame, text="Registra Nuova Proprietà...", command=self.open_registra_nuova_proprieta_window).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(action_frame, text="Registra Passaggio Proprietà...", command=self.open_registra_passaggio_window).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(action_frame, text="Registra Consultazione...", command=self.open_registra_consultazione_window).pack(side=tk.LEFT, padx=5, pady=5)

    def crea_tab_report(self):
        tab = self.tab_report
        tab.columnconfigure(0, weight=1); tab.rowconfigure(1, weight=1)
        content_frame = ttk.Frame(tab, padding="10")
        content_frame.grid(row=0, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=1); content_frame.rowconfigure(2, weight=1)
        tab.rowconfigure(0, weight=1)
        report_frame = ttk.LabelFrame(content_frame, text="Genera Report", padding="10")
        report_frame.grid(row=0, column=0, padx=5, pady=10, sticky='ew')
        ttk.Label(report_frame, text="Tipo Report:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.report_type_var = tk.StringVar()
        self.report_combobox = ttk.Combobox(report_frame, textvariable=self.report_type_var, values=["Certificato Proprietà", "Report Genealogico", "Report Possessore"], state="readonly", width=25)
        self.report_combobox.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.report_combobox.current(0)
        ttk.Label(report_frame, text="ID Partita/Possessore:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.report_id_entry = ttk.Entry(report_frame, width=10)
        self.report_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Button(report_frame, text="Genera Report", command=self.genera_report_gui).grid(row=2, column=0, columnspan=2, pady=10)
        report_frame.columnconfigure(1, weight=1)
        ttk.Label(content_frame, text="Anteprima Report:", font=('Arial', 10, 'bold')).grid(row=1, column=0, padx=5, pady=(10,0), sticky='w')
        self.report_text_area = scrolledtext.ScrolledText(content_frame, height=15, width=80, wrap=tk.WORD, font=("Courier New", 9))
        self.report_text_area.grid(row=2, column=0, padx=5, pady=5, sticky='nsew')
        self.report_text_area.config(state=tk.DISABLED)
        self.save_report_button = ttk.Button(content_frame, text="Salva Report su File...", command=self.salva_report_corrente, state=tk.DISABLED)
        self.save_report_button.grid(row=3, column=0, padx=5, pady=10, sticky='e')
        self.current_report_content = ""; self.current_report_filename = ""

    def crea_tab_manutenzione(self):
        tab = self.tab_manutenzione
        tab.columnconfigure(0, weight=1); tab.rowconfigure(1, weight=1)
        content_frame = ttk.Frame(tab, padding="10")
        content_frame.grid(row=0, column=0, sticky="nsew")
        content_frame.columnconfigure(0, weight=1); content_frame.rowconfigure(1, weight=1)
        tab.rowconfigure(0, weight=1)
        action_frame = ttk.LabelFrame(content_frame, text="Azioni di Manutenzione", padding="10")
        action_frame.grid(row=0, column=0, padx=5, pady=10, sticky='ew')
        ttk.Button(action_frame, text="Verifica Integrità Database", command=self.verifica_integrita).pack(pady=5, fill=tk.X)
        log_frame = ttk.LabelFrame(content_frame, text="Log Operazioni Manutenzione", padding="10")
        log_frame.grid(row=1, column=0, padx=5, pady=10, sticky='nsew')
        log_frame.columnconfigure(0, weight=1); log_frame.rowconfigure(0, weight=1)
        self.manutenzione_log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70, wrap=tk.WORD, state=tk.DISABLED)
        self.manutenzione_log_text.grid(row=0, column=0, sticky="nsew")

    # --- Metodi Callback Consultazione / Azioni Menu Contestuale ---
    def update_search_fields(self, event=None):
        search_type = self.search_type_var.get()
        self.search_entry1.delete(0, tk.END); self.search_entry2.delete(0, tk.END); self.search_entry3.delete(0, tk.END); self.search_entry4.delete(0, tk.END)
        self.search_advanced_frame.pack_forget()
        if search_type == "Comuni": self.search_entry1_label.config(text="Nome Comune:"); self.search_entry1.config(width=25)
        elif search_type == "Partite per Comune" or search_type == "Possessori per Comune": self.search_entry1_label.config(text="Nome Comune:"); self.search_entry1.config(width=25)
        elif search_type == "Partite (Avanzato)":
            self.search_entry1_label.config(text="Comune:"); self.search_entry1.config(width=15)
            self.search_entry2_label.pack(side=tk.LEFT, padx=(10,0)); self.search_entry2.pack(side=tk.LEFT, padx=5)
            self.search_entry3_label.pack(side=tk.LEFT, padx=(10,0)); self.search_entry3.pack(side=tk.LEFT, padx=5)
            self.search_entry4_label.pack(side=tk.LEFT, padx=(10,0)); self.search_entry4.pack(side=tk.LEFT, padx=5)
            self.search_advanced_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.setup_treeview(search_type)

    def setup_treeview(self, view_type):
        self.consult_tree.delete(*self.consult_tree.get_children()); self.consult_tree["columns"] = (); self.consult_context_menu.delete(0, tk.END)
        if view_type == "Comuni":
            cols = ("nome", "provincia", "regione"); self.consult_tree["columns"] = cols
            self.consult_tree.heading("nome", text="Nome"); self.consult_tree.column("nome", width=200, anchor=tk.W)
            self.consult_tree.heading("provincia", text="Provincia"); self.consult_tree.column("provincia", width=100, anchor=tk.W)
            self.consult_tree.heading("regione", text="Regione"); self.consult_tree.column("regione", width=100, anchor=tk.W)
        elif view_type == "Partite per Comune" or view_type == "Partite (Avanzato)":
            cols = ("id", "comune_nome", "numero_partita", "tipo", "stato", "possessori", "num_immobili"); self.consult_tree["columns"] = cols
            self.consult_tree.heading("id", text="ID"); self.consult_tree.column("id", width=50, anchor=tk.CENTER)
            self.consult_tree.heading("comune_nome", text="Comune"); self.consult_tree.column("comune_nome", width=150, anchor=tk.W)
            self.consult_tree.heading("numero_partita", text="Numero"); self.consult_tree.column("numero_partita", width=80, anchor=tk.CENTER)
            self.consult_tree.heading("tipo", text="Tipo"); self.consult_tree.column("tipo", width=80, anchor=tk.W)
            self.consult_tree.heading("stato", text="Stato"); self.consult_tree.column("stato", width=80, anchor=tk.W)
            self.consult_tree.heading("possessori", text="Possessori"); self.consult_tree.column("possessori", width=250, anchor=tk.W)
            self.consult_tree.heading("num_immobili", text="N.Imm."); self.consult_tree.column("num_immobili", width=60, anchor=tk.CENTER)
            self.consult_context_menu.add_command(label="Visualizza Dettagli Partita", command=self.context_view_partita_details)
            self.consult_context_menu.add_command(label="Genera Certificato Proprietà", command=self.context_generate_certificato)
            self.consult_context_menu.add_command(label="Genera Report Genealogico", command=self.context_generate_report_genealogico)
        elif view_type == "Possessori per Comune":
            cols = ("id", "nome_completo", "cognome_nome", "paternita", "attivo"); self.consult_tree["columns"] = cols
            self.consult_tree.heading("id", text="ID"); self.consult_tree.column("id", width=50, anchor=tk.CENTER)
            self.consult_tree.heading("nome_completo", text="Nome Completo"); self.consult_tree.column("nome_completo", width=250, anchor=tk.W)
            self.consult_tree.heading("cognome_nome", text="Cognome Nome"); self.consult_tree.column("cognome_nome", width=200, anchor=tk.W)
            self.consult_tree.heading("paternita", text="Paternità"); self.consult_tree.column("paternita", width=100, anchor=tk.W)
            self.consult_tree.heading("attivo", text="Attivo"); self.consult_tree.column("attivo", width=60, anchor=tk.CENTER)
            self.consult_context_menu.add_command(label="Genera Report Possessore", command=self.context_generate_report_possessore)

    def esegui_ricerca_consultazione(self):
        search_type = self.search_type_var.get(); term1 = self.search_entry1.get().strip(); results = []
        self.pulisci_risultati_consultazione(); self.set_status(f"Ricerca '{search_type}' in corso..."); self.update_idletasks()
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: messagebox.showerror("Errore", "Database non connesso."); self.set_status("Errore: DB non connesso."); return
            if search_type == "Comuni": results = self.db_manager.get_comuni(term1 or None); self.setup_treeview("Comuni")
            elif search_type == "Partite per Comune":
                if not term1: messagebox.showwarning("Input Mancante", "Inserire nome comune."); self.set_status("Ricerca annullata."); return
                results = self.db_manager.get_partite_by_comune(term1); self.setup_treeview("Partite per Comune")
            elif search_type == "Possessori per Comune":
                if not term1: messagebox.showwarning("Input Mancante", "Inserire nome comune."); self.set_status("Ricerca annullata."); return
                results = self.db_manager.get_possessori_by_comune(term1); self.setup_treeview("Possessori per Comune")
            elif search_type == "Partite (Avanzato)":
                 numero_str = self.search_entry2.get().strip(); possessore = self.search_entry3.get().strip(); natura = self.search_entry4.get().strip()
                 numero_partita = None
                 if numero_str:
                    try: numero_partita = int(numero_str)
                    except ValueError: messagebox.showerror("Input Errato", "Numero partita deve essere intero."); self.set_status("Ricerca fallita."); return
                 results = self.db_manager.search_partite(comune_nome=term1 or None, numero_partita=numero_partita, possessore=possessore or None, immobile_natura=natura or None)
                 self.setup_treeview("Partite (Avanzato)")
            if results:
                headers = self.consult_tree["columns"]
                for row_dict in results:
                    row_values = [row_dict.get(col, '') for col in headers]
                    item_id = row_dict.get('id', None); self.consult_tree.insert("", tk.END, values=row_values, iid=item_id)
                self.set_status(f"Ricerca '{search_type}' completata: {len(results)} risultati.")
            else: self.set_status(f"Ricerca '{search_type}' completata: Nessun risultato.")
        except Exception as e: messagebox.showerror("Errore Ricerca", f"Errore:\n{e}"); self.set_status(f"Errore ricerca '{search_type}'.")

    def pulisci_risultati_consultazione(self):
        self.consult_tree.delete(*self.consult_tree.get_children()); self.set_status("Risultati puliti.")

    def show_consult_context_menu(self, event):
        item_iid = self.consult_tree.identify_row(event.y)
        if item_iid:
            self.consult_tree.selection_set(item_iid); self.selected_item_id = item_iid
            if self.consult_context_menu.index(tk.END) is not None: self.consult_context_menu.post(event.x_root, event.y_root)
        else: self.selected_item_id = None

    def on_consult_tree_double_click(self, event):
         region = self.consult_tree.identify_region(event.x, event.y)
         if region == "cell":
             item_iid = self.consult_tree.identify_row(event.y)
             if item_iid:
                 self.selected_item_id = item_iid; view_type = self.search_type_var.get()
                 if "Partite" in view_type: self.context_view_partita_details()

    def context_view_partita_details(self):
        if self.selected_item_id is None: messagebox.showwarning("Azione non possibile", "Nessuna partita selezionata.", parent=self); return
        try: partita_id = int(self.selected_item_id); self.open_partita_details_window(partita_id)
        except ValueError: messagebox.showerror("Errore", "ID Partita non valido.", parent=self)
        except Exception as e: messagebox.showerror("Errore", f"Impossibile visualizzare dettagli:\n{e}", parent=self)
        finally: self.selected_item_id = None

    def open_partita_details_window(self, partita_id):
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            partita = self.db_manager.get_partita_details(partita_id)
            if not partita: messagebox.showinfo("Dettagli Partita", f"Nessuna partita trovata con ID {partita_id}.", parent=self); return
            details_window = tk.Toplevel(self); details_window.title(f"Dettagli Partita {partita.get('numero_partita','N/A')} ({partita.get('comune_nome','N/A')})")
            details_window.geometry("700x550"); details_window.transient(self); details_window.grab_set()
            text_area = scrolledtext.ScrolledText(details_window, wrap=tk.WORD, padx=5, pady=5, relief=tk.FLAT, font=("Consolas", 10))
            text_area.pack(expand=True, fill="both")
            text_area.insert(tk.END, f"DETTAGLI PARTITA ID: {partita.get('id', 'N/A')}\n=========================================\n")
            text_area.insert(tk.END, f"Comune:         {partita.get('comune_nome', 'N/A')}\nNumero Partita: {partita.get('numero_partita', 'N/A')}\n")
            text_area.insert(tk.END, f"Tipo:           {partita.get('tipo', 'N/A')}\nStato:          {partita.get('stato', 'N/A')}\n")
            text_area.insert(tk.END, f"Data Impianto:  {partita.get('data_impianto', 'N/A')}\n")
            if partita.get('data_chiusura'): text_area.insert(tk.END, f"Data Chiusura:  {partita['data_chiusura']}\n")
            text_area.insert(tk.END, f"\n--- POSSESSORI ---\n")
            if partita.get('possessori'):
                for pos in partita['possessori']: quota_str = f" (Quota: {pos['quota']})" if pos.get('quota') else ""; text_area.insert(tk.END, f"- ID {pos.get('id', 'N/A')}: {pos.get('nome_completo', 'N/A')}{quota_str}\n")
            else: text_area.insert(tk.END, "  Nessuno\n")
            text_area.insert(tk.END, f"\n--- IMMOBILI ---\n")
            if partita.get('immobili'):
                 for imm in partita['immobili']:
                     text_area.insert(tk.END, f"- ID {imm.get('id', 'N/A')}: {imm.get('natura', 'N/A')} in Loc. {imm.get('localita_nome', 'N/A')}\n")
                     details = [];
                     if imm.get('consistenza'): details.append(f"Consistenza: {imm['consistenza']}")
                     if imm.get('classificazione'): details.append(f"Class.: {imm['classificazione']}")
                     if imm.get('numero_piani'): details.append(f"Piani: {imm['numero_piani']}")
                     if imm.get('numero_vani'): details.append(f"Vani: {imm['numero_vani']}")
                     if details: text_area.insert(tk.END, f"    ({', '.join(details)})\n")
            else: text_area.insert(tk.END, "  Nessuno\n")
            text_area.insert(tk.END, f"\n--- VARIAZIONI COLLEGATE ---\n")
            if partita.get('variazioni'):
                for var in partita['variazioni']:
                    text_area.insert(tk.END, f"- ID {var.get('id', 'N/A')}: {var.get('tipo', 'N/A')} del {var.get('data_variazione', 'N/A')}\n")
                    if var.get('tipo_contratto'):
                        contr_details = f"    Contratto: {var['tipo_contratto']} del {var.get('data_contratto', 'N/A')}"
                        if var.get('notaio'): contr_details += f", Notaio: {var['notaio']}"
                        if var.get('repertorio'): contr_details += f", Rep: {var['repertorio']}"
                        text_area.insert(tk.END, contr_details + "\n")
                    if var.get('note'): text_area.insert(tk.END, f"    Note: {var['note']}\n")
            else: text_area.insert(tk.END, "  Nessuna\n")
            text_area.config(state=tk.DISABLED); ttk.Button(details_window, text="Chiudi", command=details_window.destroy).pack(pady=10)
        except ConnectionError as ce: messagebox.showerror("Errore Database", str(ce), parent=self)
        except Exception as e: messagebox.showerror("Errore Dettagli", f"Errore caricamento:\n{e}", parent=self)

    def context_generate_certificato(self):
        if self.selected_item_id is None: messagebox.showwarning("Azione non possibile", "Nessuna partita selezionata.", parent=self); return
        try:
            partita_id = int(self.selected_item_id);
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            report_content = self.db_manager.genera_certificato_proprieta(partita_id)
            self.display_report_window(f"Certificato Partita {partita_id}", report_content, f"certificato_partita_{partita_id}.txt")
        except ValueError: messagebox.showerror("Errore", "ID Partita non valido.", parent=self)
        except ConnectionError as ce: messagebox.showerror("Errore Database", str(ce), parent=self)
        except Exception as e: messagebox.showerror("Errore", f"Impossibile generare certificato:\n{e}", parent=self)
        finally: self.selected_item_id = None

    def context_generate_report_genealogico(self):
        if self.selected_item_id is None: messagebox.showwarning("Azione non possibile", "Nessuna partita selezionata.", parent=self); return
        try:
            partita_id = int(self.selected_item_id)
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            report_content = self.db_manager.genera_report_genealogico(partita_id)
            self.display_report_window(f"Report Genealogico Partita {partita_id}", report_content, f"report_genealogico_{partita_id}.txt")
        except ValueError: messagebox.showerror("Errore", "ID Partita non valido.", parent=self)
        except ConnectionError as ce: messagebox.showerror("Errore Database", str(ce), parent=self)
        except Exception as e: messagebox.showerror("Errore", f"Impossibile generare report genealogico:\n{e}", parent=self)
        finally: self.selected_item_id = None

    def context_generate_report_possessore(self):
        if self.selected_item_id is None: messagebox.showwarning("Azione non possibile", "Nessun possessore selezionato.", parent=self); return
        try:
            possessore_id = int(self.selected_item_id)
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            report_content = self.db_manager.genera_report_possessore(possessore_id)
            self.display_report_window(f"Report Possessore ID {possessore_id}", report_content, f"report_possessore_{possessore_id}.txt")
        except ValueError: messagebox.showerror("Errore", "ID Possessore non valido.", parent=self)
        except ConnectionError as ce: messagebox.showerror("Errore Database", str(ce), parent=self)
        except Exception as e: messagebox.showerror("Errore", f"Impossibile generare report possessore:\n{e}", parent=self)
        finally: self.selected_item_id = None

    def display_report_window(self, title, content, save_filename):
        if not content: messagebox.showinfo(title, "Nessun dato da visualizzare.", parent=self); return
        report_window = tk.Toplevel(self); report_window.title(title); report_window.geometry("800x600"); report_window.transient(self); report_window.grab_set()
        text_area = scrolledtext.ScrolledText(report_window, wrap=tk.WORD, padx=5, pady=5, relief=tk.FLAT, font=("Courier New", 10))
        text_area.pack(expand=True, fill="both"); text_area.insert(tk.END, content); text_area.config(state=tk.DISABLED)
        button_frame = ttk.Frame(report_window); button_frame.pack(pady=10)
        def save_report():
            file_path = filedialog.asksaveasfilename(parent=report_window, title="Salva Report", initialfile=save_filename, defaultextension=".txt", filetypes=[("File Testo", "*.txt"), ("Tutti i File", "*.*")])
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
                    messagebox.showinfo("Report Salvato", f"Salvato in:\n{file_path}", parent=report_window)
                except Exception as e: messagebox.showerror("Errore Salvataggio", f"Impossibile salvare:\n{e}", parent=report_window)
        ttk.Button(button_frame, text="Salva su File...", command=save_report).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Chiudi", command=report_window.destroy).pack(side=tk.LEFT, padx=10)

    # --- Metodi Callback Inserimento / Report / Manutenzione ---
    def aggiungi_comune(self):
        nome = self.comune_nome_entry.get().strip(); provincia = self.comune_provincia_entry.get().strip(); regione = self.comune_regione_entry.get().strip()
        if not nome or not provincia or not regione: messagebox.showwarning("Dati Mancanti", "Inserire nome, provincia e regione.", parent=self); return
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            if self.db_manager.execute_query("INSERT INTO comune (nome, provincia, regione) VALUES (%s, %s, %s) ON CONFLICT (nome) DO NOTHING", (nome, provincia, regione)):
                self.db_manager.commit()
                self.set_status(f"Comune '{nome}' inserito o già esistente.")
                messagebox.showinfo("Successo", f"Comune '{nome}' inserito/già esistente.", parent=self)
                self.comune_nome_entry.delete(0, tk.END); self.comune_provincia_entry.delete(0, tk.END); self.comune_regione_entry.delete(0, tk.END)
            else: messagebox.showerror("Errore Database", "Errore inserimento comune.", parent=self); self.set_status("Errore inserimento comune.")
        except ConnectionError as ce: messagebox.showerror("Errore Database", str(ce), parent=self); self.set_status("Errore: DB non connesso.")
        except Exception as e: self.db_manager.rollback(); messagebox.showerror("Errore", f"Errore:\n{e}", parent=self); self.set_status("Errore inserimento comune.")

    def aggiungi_possessore(self):
        comune = self.poss_comune_entry.get().strip(); cognome_nome = self.poss_cognome_nome_entry.get().strip()
        paternita = self.poss_paternita_entry.get().strip(); nome_completo = self.poss_nome_completo_entry.get().strip()
        if not comune or not cognome_nome: messagebox.showwarning("Dati Mancanti", "Inserire Comune e Cognome e Nome.", parent=self); return
        if not nome_completo: nome_completo = f"{cognome_nome} {paternita}".strip()
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            possessore_id = self.db_manager.insert_possessore(comune, cognome_nome, paternita, nome_completo, True)
            if possessore_id:
                self.set_status(f"Possessore '{nome_completo}' (ID: {possessore_id}) inserito.")
                messagebox.showinfo("Successo", f"Possessore '{nome_completo}' inserito (ID: {possessore_id}).", parent=self)
                self.poss_comune_entry.delete(0, tk.END); self.poss_cognome_nome_entry.delete(0, tk.END); self.poss_paternita_entry.delete(0, tk.END); self.poss_nome_completo_entry.delete(0, tk.END)
            else: messagebox.showerror("Errore Database", "Errore inserimento possessore.", parent=self); self.set_status("Errore inserimento possessore.")
        except ConnectionError as ce: messagebox.showerror("Errore Database", str(ce), parent=self); self.set_status("Errore: DB non connesso.")
        except Exception as e: self.db_manager.rollback(); messagebox.showerror("Errore", f"Errore:\n{e}", parent=self); self.set_status("Errore inserimento possessore.")

    def genera_report_gui(self):
        report_type = self.report_type_var.get(); id_str = self.report_id_entry.get().strip()
        self.current_report_content = ""; self.current_report_filename = ""; self.save_report_button.config(state=tk.DISABLED)
        self.report_text_area.config(state=tk.NORMAL); self.report_text_area.delete('1.0', tk.END)
        if not id_str: messagebox.showwarning("Input Mancante", "Inserire ID Partita/Possessore.", parent=self); self.report_text_area.config(state=tk.DISABLED); return
        try: item_id = int(id_str)
        except ValueError: messagebox.showerror("Input Errato", "L'ID deve essere un intero.", parent=self); self.report_text_area.config(state=tk.DISABLED); return
        report_content = ""; default_filename = "report.txt"
        self.set_status(f"Generazione '{report_type}' per ID {item_id}..."); self.update_idletasks()
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            if report_type == "Certificato Proprietà": report_content = self.db_manager.genera_certificato_proprieta(item_id); default_filename = f"certificato_partita_{item_id}.txt"
            elif report_type == "Report Genealogico": report_content = self.db_manager.genera_report_genealogico(item_id); default_filename = f"report_genealogico_{item_id}.txt"
            elif report_type == "Report Possessore": report_content = self.db_manager.genera_report_possessore(item_id); default_filename = f"report_possessore_{item_id}.txt"
            if report_content:
                self.report_text_area.insert(tk.END, report_content); self.current_report_content = report_content; self.current_report_filename = default_filename
                self.save_report_button.config(state=tk.NORMAL); self.set_status(f"Report '{report_type}' generato.")
            else: self.report_text_area.insert(tk.END, f"Nessun {report_type} generato per ID {item_id}."); self.set_status(f"Report '{report_type}' non generato.")
        except ConnectionError as e: messagebox.showerror("Errore Database", str(e), parent=self); self.set_status("Errore: DB non connesso.")
        except Exception as e: error_msg = f"Errore generazione report '{report_type}':\n{e}"; messagebox.showerror("Errore", error_msg, parent=self); self.report_text_area.insert(tk.END, error_msg); self.set_status(f"Errore generazione report.")
        finally: self.report_text_area.config(state=tk.DISABLED)

    def salva_report_corrente(self):
        if not self.current_report_content: messagebox.showwarning("Nessun Report", "Nessun report generato da salvare.", parent=self); return
        file_path = filedialog.asksaveasfilename(parent=self, title="Salva Report", initialfile=self.current_report_filename, defaultextension=".txt", filetypes=[("File Testo", "*.txt"), ("Tutti i File", "*.*")])
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(self.current_report_content)
                self.set_status(f"Report salvato in {file_path}"); messagebox.showinfo("Report Salvato", f"Salvato in:\n{file_path}", parent=self)
            except Exception as e: self.set_status(f"Errore salvataggio report."); messagebox.showerror("Errore Salvataggio", f"Impossibile salvare:\n{e}", parent=self)

    def add_manutenzione_log(self, message):
         timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); log_message = f"[{timestamp}] {message}\n"
         self.manutenzione_log_text.config(state=tk.NORMAL); self.manutenzione_log_text.insert(tk.END, log_message); self.manutenzione_log_text.see(tk.END); self.manutenzione_log_text.config(state=tk.DISABLED)

    def verifica_integrita(self):
        self.add_manutenzione_log("Avvio verifica integrità..."); self.set_status("Verifica integrità in corso..."); self.update_idletasks()
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            self.db_manager.execute_query("CALL verifica_integrita_database(NULL)"); self.db_manager.commit()
            log_msg = "Verifica completata. Controllare log server PostgreSQL per dettagli."
            self.add_manutenzione_log(log_msg); messagebox.showinfo("Verifica Integrità", log_msg, parent=self); self.set_status("Verifica completata.")
        except ConnectionError as e: error_msg = f"Errore: {e}"; self.add_manutenzione_log(error_msg); messagebox.showerror("Errore Database", error_msg, parent=self); self.set_status("Errore: DB non connesso.")
        except Exception as e: self.db_manager.rollback(); error_msg = f"Errore verifica integrità: {e}"; self.add_manutenzione_log(error_msg); messagebox.showerror("Errore Manutenzione", error_msg, parent=self); self.set_status("Errore verifica.")


# --- Funzione Principale per Avviare l'App ---
def main_gui_v2():
    # Configurazione DB (MODIFICA QUI SE NECESSARIO!)
    db_config = {
        "dbname": "catasto_storico",
        "user": "postgres",
        "password": "Markus74",  # !! LA TUA PASSWORD !!
        "host": "localhost",
        "port": 5432,
        "schema": "catasto" # Assicurati che lo schema sia specificato
    }

    # Crea l'istanza della classe principale
    app = CatastoAppV2(db_config)
    # Avvia il loop principale di Tkinter
    app.mainloop()

# --- Blocco di Esecuzione ---
# Deve essere alla fine del file, dopo tutte le definizioni di classi e funzioni
if __name__ == "__main__":
    main_gui_v2()