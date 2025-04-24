#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaccia Python per Gestione Catasto Storico
Versione 3.1 - Corretto state ScrolledText ttkbootstrap
"""

# Importazioni base
import sys
import json
from datetime import date, datetime
import tkinter as tk

# --- Importazioni GUI con ttkbootstrap ---
try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
    from ttkbootstrap.dialogs import Messagebox
    from ttkbootstrap.scrolled import ScrolledText # Usa ScrolledText di ttkbootstrap
except ImportError:
     from tkinter import messagebox as tk_messagebox
     tk_messagebox.showerror("Errore Dipendenza", "La libreria 'ttkbootstrap' non è installata.\nEsegui 'pip install ttkbootstrap' dal terminale.")
     sys.exit(1)

# --- Importazioni altre librerie ---
try:
    from tkcalendar import DateEntry
except ImportError:
    Messagebox.show_error("La libreria 'tkcalendar' non è installata.\nEsegui 'pip install tkcalendar' dal terminale.", title="Errore Dipendenza")
    sys.exit(1)

try:
    from catasto_db_manager import CatastoDBManager
except ImportError:
     Messagebox.show_error("Il file 'catasto_db_manager.py' non è stato trovato.\nAssicurati che sia nella stessa cartella.", title="Errore Importazione")
     sys.exit(1)


# --- Finestra Toplevel per Registra Consultazione (con ttkbootstrap) ---
class RegistraConsultazioneWindow(tb.Toplevel):
    def __init__(self, parent, db_manager, theme):
        super().__init__(parent, title="Registra Consultazione")
        self.parent = parent
        self.db_manager = db_manager
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = tb.Frame(self, padding=15)
        frame.pack(expand=YES, fill=BOTH)
        frame.columnconfigure(1, weight=1)

        tb.Label(frame, text="Data:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.data_entry = DateEntry(frame, date_pattern='yyyy-mm-dd', width=12)
        self.data_entry.grid(row=0, column=1, padx=5, pady=5, sticky=W)
        self.data_entry.set_date(date.today())

        tb.Label(frame, text="Richiedente*:").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        self.richiedente_entry = tb.Entry(frame, width=40)
        self.richiedente_entry.grid(row=1, column=1, padx=5, pady=5, sticky=EW)

        tb.Label(frame, text="Documento:").grid(row=2, column=0, padx=5, pady=5, sticky=W)
        self.documento_entry = tb.Entry(frame, width=40)
        self.documento_entry.grid(row=2, column=1, padx=5, pady=5, sticky=EW)

        tb.Label(frame, text="Motivazione:").grid(row=3, column=0, padx=5, pady=5, sticky=W)
        self.motivazione_entry = tb.Entry(frame, width=40)
        self.motivazione_entry.grid(row=3, column=1, padx=5, pady=5, sticky=EW)

        tb.Label(frame, text="Materiale*:").grid(row=4, column=0, padx=5, pady=5, sticky=W)
        self.materiale_entry = tb.Entry(frame, width=40)
        self.materiale_entry.grid(row=4, column=1, padx=5, pady=5, sticky=EW)

        tb.Label(frame, text="Funzionario*:").grid(row=5, column=0, padx=5, pady=5, sticky=W)
        self.funzionario_entry = tb.Entry(frame, width=40)
        self.funzionario_entry.grid(row=5, column=1, padx=5, pady=5, sticky=EW)

        tb.Label(frame, text="* Campi obbligatori", bootstyle="secondary").grid(row=6, column=1, padx=5, pady=10, sticky=E)

        button_frame = tb.Frame(frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=15)
        tb.Button(button_frame, text="Registra", bootstyle="success", command=self.registra).pack(side=LEFT, padx=10)
        tb.Button(button_frame, text="Annulla", bootstyle="secondary-outline", command=self.destroy).pack(side=LEFT, padx=10)

        self.wait_window()

    def registra(self):
        data_cons = self.data_entry.get_date()
        richiedente = self.richiedente_entry.get().strip()
        documento = self.documento_entry.get().strip()
        motivazione = self.motivazione_entry.get().strip()
        materiale = self.materiale_entry.get().strip()
        funzionario = self.funzionario_entry.get().strip()

        if not richiedente or not materiale or not funzionario:
            Messagebox.show_warning("Compilare i campi obbligatori (*).", title="Dati Mancanti", parent=self)
            return
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            success = self.db_manager.registra_consultazione(data_cons, richiedente, documento, motivazione, materiale, funzionario)
            if success:
                self.parent.set_status("Consultazione registrata con successo.")
                Messagebox.show_info("Consultazione registrata con successo.", title="Successo", parent=self.parent)
                self.destroy()
            else:
                 Messagebox.show_error("Errore durante la registrazione della consultazione.\nControllare i log.", title="Errore Database", parent=self)
                 self.parent.set_status("Errore registrazione consultazione.")
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self); self.parent.set_status("Errore: Database non connesso.")
        except Exception as e: self.db_manager.rollback(); Messagebox.show_error(f"Errore durante la registrazione:\n{e}", title="Errore Imprevisto", parent=self); self.parent.set_status("Errore registrazione consultazione.")


# --- Finestra Toplevel per Registra Nuova Proprietà (con ttkbootstrap) ---
class RegistraNuovaProprietaWindow(tb.Toplevel):
    def __init__(self, parent, db_manager, theme):
        super().__init__(parent, title="Registra Nuova Proprietà")
        self.parent = parent
        self.db_manager = db_manager
        self.geometry("800x700")
        self.transient(parent)
        self.grab_set()
        self.possessori_list = []; self.immobili_list = []
        main_frame = tb.Frame(self, padding=15); main_frame.pack(expand=YES, fill=BOTH)
        main_frame.columnconfigure(0, weight=1); main_frame.rowconfigure(1, weight=1); main_frame.rowconfigure(2, weight=1)
        partita_frame = tb.LabelFrame(main_frame, text=" Dati Partita ", padding=10, bootstyle="info"); partita_frame.grid(row=0, column=0, padx=5, pady=10, sticky=EW)
        partita_frame.columnconfigure(1, weight=1); partita_frame.columnconfigure(3, weight=1)
        tb.Label(partita_frame, text="Comune*:").grid(row=0, column=0, padx=5, pady=5, sticky=W); self.comune_entry = tb.Entry(partita_frame); self.comune_entry.grid(row=0, column=1, padx=5, pady=5, sticky=EW)
        tb.Label(partita_frame, text="Numero Partita*:").grid(row=0, column=2, padx=5, pady=5, sticky=W); self.numero_entry = tb.Entry(partita_frame, width=10); self.numero_entry.grid(row=0, column=3, padx=5, pady=5, sticky=W)
        tb.Label(partita_frame, text="Data Impianto*:").grid(row=1, column=0, padx=5, pady=5, sticky=W); self.data_impianto_entry = DateEntry(partita_frame, date_pattern='yyyy-mm-dd', width=12); self.data_impianto_entry.grid(row=1, column=1, padx=5, pady=5, sticky=W); self.data_impianto_entry.set_date(date.today())
        poss_main_frame = tb.LabelFrame(main_frame, text=" Possessori* ", padding=10, bootstyle="info"); poss_main_frame.grid(row=1, column=0, padx=5, pady=10, sticky=NSEW)
        poss_main_frame.columnconfigure(0, weight=1); poss_main_frame.rowconfigure(1, weight=1)
        poss_input_frame = tb.Frame(poss_main_frame); poss_input_frame.grid(row=0, column=0, sticky=EW, pady=(0,10)); poss_input_frame.columnconfigure(1, weight=1); poss_input_frame.columnconfigure(3, weight=1)
        tb.Label(poss_input_frame, text="Nome Completo:").grid(row=0, column=0, padx=5, pady=3, sticky=W); self.poss_nome_entry = tb.Entry(poss_input_frame); self.poss_nome_entry.grid(row=0, column=1, padx=5, pady=3, sticky=EW)
        tb.Button(poss_input_frame, text="Cerca/Nuovo", bootstyle="info-outline", command=self.gestisci_possessore).grid(row=0, column=4, padx=(10,0), pady=3)
        tb.Label(poss_input_frame, text="Cognome Nome:").grid(row=1, column=0, padx=5, pady=3, sticky=W); self.poss_cgn_entry = tb.Entry(poss_input_frame); self.poss_cgn_entry.grid(row=1, column=1, padx=5, pady=3, sticky=EW)
        tb.Label(poss_input_frame, text="Paternità:").grid(row=1, column=2, padx=5, pady=3, sticky=W); self.poss_pat_entry = tb.Entry(poss_input_frame); self.poss_pat_entry.grid(row=1, column=3, padx=5, pady=3, sticky=EW)
        tb.Label(poss_input_frame, text="Quota:").grid(row=2, column=0, padx=5, pady=3, sticky=W); self.poss_quota_entry = tb.Entry(poss_input_frame, width=15); self.poss_quota_entry.grid(row=2, column=1, padx=5, pady=3, sticky=W)
        tb.Label(poss_input_frame, text="(es. 1/2)", bootstyle="secondary").grid(row=2, column=1, padx=5, pady=3, sticky=E)
        tb.Button(poss_input_frame, text="Aggiungi Possessore", bootstyle="primary", command=self.aggiungi_possessore_lista).grid(row=3, column=0, columnspan=5, pady=10)
        poss_tree_frame = tb.Frame(poss_main_frame); poss_tree_frame.grid(row=1, column=0, sticky=NSEW); poss_tree_frame.rowconfigure(0, weight=1); poss_tree_frame.columnconfigure(0, weight=1)
        poss_cols = ("nome_completo", "cognome_nome", "paternita", "quota"); self.poss_tree = tb.Treeview(poss_tree_frame, columns=poss_cols, show="headings", height=4, bootstyle="info")
        for col in poss_cols: self.poss_tree.heading(col, text=col.replace('_', ' ').title()); self.poss_tree.column(col, width=140, anchor=W)
        poss_vsb = tb.Scrollbar(poss_tree_frame, orient=VERTICAL, command=self.poss_tree.yview, bootstyle="round"); self.poss_tree.configure(yscrollcommand=poss_vsb.set); self.poss_tree.grid(row=0, column=0, sticky=NSEW); poss_vsb.grid(row=0, column=1, sticky=NS)
        tb.Button(poss_main_frame, text="Rimuovi Selezionato", bootstyle="danger-outline", command=self.rimuovi_possessore_lista).grid(row=2, column=0, padx=5, pady=(5,0), sticky=W)
        imm_main_frame = tb.LabelFrame(main_frame, text=" Immobili* ", padding=10, bootstyle="info"); imm_main_frame.grid(row=2, column=0, padx=5, pady=10, sticky=NSEW)
        imm_main_frame.columnconfigure(0, weight=1); imm_main_frame.rowconfigure(1, weight=1)
        imm_input_frame = tb.Frame(imm_main_frame); imm_input_frame.grid(row=0, column=0, sticky=EW, pady=(0,10)); imm_input_frame.columnconfigure(1, weight=1); imm_input_frame.columnconfigure(3, weight=1)
        tb.Label(imm_input_frame, text="Natura:").grid(row=0, column=0, padx=5, pady=3, sticky=W); self.imm_natura_entry = tb.Entry(imm_input_frame); self.imm_natura_entry.grid(row=0, column=1, padx=5, pady=3, sticky=EW)
        tb.Label(imm_input_frame, text="Località:").grid(row=0, column=2, padx=5, pady=3, sticky=W); self.imm_localita_entry = tb.Entry(imm_input_frame); self.imm_localita_entry.grid(row=0, column=3, padx=5, pady=3, sticky=EW)
        tb.Label(imm_input_frame, text="Tipo Loc:").grid(row=1, column=0, padx=5, pady=3, sticky=W); self.imm_tipo_loc_var = tk.StringVar(value="via"); tb.Combobox(imm_input_frame, textvariable=self.imm_tipo_loc_var, values=["via", "regione", "borgata", "frazione"], state="readonly", width=10).grid(row=1, column=1, padx=5, pady=3, sticky=W)
        tb.Label(imm_input_frame, text="Classificazione:").grid(row=1, column=2, padx=5, pady=3, sticky=W); self.imm_class_entry = tb.Entry(imm_input_frame); self.imm_class_entry.grid(row=1, column=3, padx=5, pady=3, sticky=EW)
        tb.Label(imm_input_frame, text="Piani:").grid(row=2, column=0, padx=5, pady=3, sticky=W); self.imm_piani_entry = tb.Entry(imm_input_frame, width=5); self.imm_piani_entry.grid(row=2, column=1, padx=5, pady=3, sticky=W)
        tb.Label(imm_input_frame, text="Vani:").grid(row=2, column=2, padx=5, pady=3, sticky=W); self.imm_vani_entry = tb.Entry(imm_input_frame, width=5); self.imm_vani_entry.grid(row=2, column=3, padx=5, pady=3, sticky=W)
        tb.Label(imm_input_frame, text="Consistenza:").grid(row=3, column=0, padx=5, pady=3, sticky=W); self.imm_cons_entry = tb.Entry(imm_input_frame); self.imm_cons_entry.grid(row=3, column=1, columnspan=3, padx=5, pady=3, sticky=EW)
        tb.Button(imm_input_frame, text="Aggiungi Immobile", bootstyle="primary", command=self.aggiungi_immobile_lista).grid(row=4, column=0, columnspan=4, pady=10)
        imm_tree_frame = tb.Frame(imm_main_frame); imm_tree_frame.grid(row=1, column=0, sticky=NSEW); imm_tree_frame.rowconfigure(0, weight=1); imm_tree_frame.columnconfigure(0, weight=1)
        imm_cols = ("natura", "localita", "tipo_localita", "classificazione", "piani", "vani", "consistenza"); self.imm_tree = tb.Treeview(imm_tree_frame, columns=imm_cols, show="headings", height=4, bootstyle="info")
        for col in imm_cols: self.imm_tree.heading(col, text=col.replace('_', ' ').title()); self.imm_tree.column(col, width=90, anchor=W)
        imm_vsb = tb.Scrollbar(imm_tree_frame, orient=VERTICAL, command=self.imm_tree.yview, bootstyle="round"); self.imm_tree.configure(yscrollcommand=imm_vsb.set); self.imm_tree.grid(row=0, column=0, sticky=NSEW); imm_vsb.grid(row=0, column=1, sticky=NS)
        tb.Button(imm_main_frame, text="Rimuovi Selezionato", bootstyle="danger-outline", command=self.rimuovi_immobile_lista).grid(row=2, column=0, padx=5, pady=(5,0), sticky=W)
        tb.Label(main_frame, text="* Campi obbligatori", bootstyle="secondary").grid(row=3, column=0, padx=5, pady=10, sticky=E)
        button_frame = tb.Frame(main_frame); button_frame.grid(row=4, column=0, pady=15)
        tb.Button(button_frame, text="Registra Proprietà", bootstyle="success", command=self.registra).pack(side=LEFT, padx=10)
        tb.Button(button_frame, text="Annulla", bootstyle="secondary-outline", command=self.destroy).pack(side=LEFT, padx=10)
        self.wait_window()

    def gestisci_possessore(self):
        nome_completo = self.poss_nome_entry.get().strip(); comune = self.comune_entry.get().strip()
        if not nome_completo or not comune: Messagebox.show_warning("Inserire Comune e Nome Completo del possessore.", title="Dati Mancanti", parent=self); return
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            poss_id = self.db_manager.check_possessore_exists(nome_completo, comune)
            if poss_id:
                 if Messagebox.yesno(f"Possessore '{nome_completo}' trovato (ID: {poss_id}).\nVuoi usarlo?", title="Possessore Esistente", parent=self):
                    self.poss_cgn_entry.delete(0, END); self.poss_pat_entry.delete(0, END); Messagebox.show_info("Possessore selezionato. Inserisci quota e aggiungi.", title="Info", parent=self)
                 else: self.poss_nome_entry.delete(0, END)
            else: Messagebox.show_info(f"Possessore '{nome_completo}' non trovato.\nInserisci dettagli per aggiungerlo.", title="Possessore Non Trovato", parent=self); self.poss_cgn_entry.focus()
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self)
        except Exception as e: Messagebox.show_error(f"Errore ricerca possessore:\n{e}", title="Errore Ricerca", parent=self)

    def aggiungi_possessore_lista(self):
        nome = self.poss_nome_entry.get().strip(); cognome_nome = self.poss_cgn_entry.get().strip(); paternita = self.poss_pat_entry.get().strip(); quota = self.poss_quota_entry.get().strip()
        if not nome: Messagebox.show_warning("Inserire Nome Completo possessore.", title="Dati Mancanti", parent=self); return
        poss_data = {"nome_completo": nome, "cognome_nome": cognome_nome or None, "paternita": paternita or None, "quota": quota or None}
        values = (nome, cognome_nome or "", paternita or "", quota or "")
        item_id = self.poss_tree.insert("", END, values=values); self.possessori_list.append({"id": item_id, "data": poss_data})
        self.poss_nome_entry.delete(0, END); self.poss_cgn_entry.delete(0, END); self.poss_pat_entry.delete(0, END); self.poss_quota_entry.delete(0, END); self.poss_nome_entry.focus()

    def rimuovi_possessore_lista(self):
        sel = self.poss_tree.selection();
        if not sel: Messagebox.show_warning("Selezionare un possessore.", title="Nessuna Selezione", parent=self); return
        iid = sel[0]; self.poss_tree.delete(iid); self.possessori_list = [p for p in self.possessori_list if p["id"] != iid]

    def aggiungi_immobile_lista(self):
        natura = self.imm_natura_entry.get().strip(); localita = self.imm_localita_entry.get().strip(); tipo_localita = self.imm_tipo_loc_var.get(); classificazione = self.imm_class_entry.get().strip()
        piani_str = self.imm_piani_entry.get().strip(); vani_str = self.imm_vani_entry.get().strip(); consistenza = self.imm_cons_entry.get().strip()
        if not natura or not localita: Messagebox.show_warning("Inserire Natura e Località.", title="Dati Mancanti", parent=self); return
        piani = None; vani = None
        try:
            if piani_str: piani = int(piani_str)
            if vani_str: vani = int(vani_str)
        except ValueError: Messagebox.show_error("Piani e Vani devono essere numeri.", title="Input Errato", parent=self); return
        imm_data = {"natura": natura, "localita": localita, "tipo_localita": tipo_localita, "classificazione": classificazione or None, "numero_piani": piani, "numero_vani": vani, "consistenza": consistenza or None}
        values = (natura, localita, tipo_localita, classificazione or "", str(piani or ""), str(vani or ""), consistenza or "")
        item_id = self.imm_tree.insert("", END, values=values); self.immobili_list.append({"id": item_id, "data": imm_data})
        self.imm_natura_entry.delete(0, END); self.imm_localita_entry.delete(0, END); self.imm_class_entry.delete(0, END); self.imm_piani_entry.delete(0, END); self.imm_vani_entry.delete(0, END); self.imm_cons_entry.delete(0, END); self.imm_natura_entry.focus()

    def rimuovi_immobile_lista(self):
        sel = self.imm_tree.selection()
        if not sel: Messagebox.show_warning("Selezionare un immobile.", title="Nessuna Selezione", parent=self); return
        iid = sel[0]; self.imm_tree.delete(iid); self.immobili_list = [i for i in self.immobili_list if i["id"] != iid]

    def registra(self):
        comune = self.comune_entry.get().strip(); numero_str = self.numero_entry.get().strip(); data_imp = self.data_impianto_entry.get_date()
        if not comune or not numero_str: Messagebox.show_warning("Inserire Comune e Numero Partita.", title="Dati Mancanti", parent=self); return
        try: numero_partita = int(numero_str)
        except ValueError: Messagebox.show_error("Numero Partita deve essere intero.", title="Input Errato", parent=self); return
        if not self.possessori_list: Messagebox.show_warning("Aggiungere almeno un possessore.", title="Dati Mancanti", parent=self); return
        if not self.immobili_list: Messagebox.show_warning("Aggiungere almeno un immobile.", title="Dati Mancanti", parent=self); return
        possessori_json_list = [p["data"] for p in self.possessori_list]; immobili_json_list = [i["data"] for i in self.immobili_list]
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            success = self.db_manager.registra_nuova_proprieta(comune, numero_partita, data_imp, possessori_json_list, immobili_json_list)
            if success:
                 self.parent.set_status(f"Nuova proprietà (P.{numero_partita}, C.{comune}) registrata."); Messagebox.show_info(f"Nuova proprietà registrata.", title="Successo", parent=self.parent); self.destroy()
            else: Messagebox.show_error("Errore registrazione.\nControllare i log.", title="Errore Database", parent=self); self.parent.set_status("Errore registrazione.")
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self); self.parent.set_status("Errore: DB non connesso.")
        except Exception as e: self.db_manager.rollback(); Messagebox.show_error(f"Errore: {e}", title="Errore Imprevisto", parent=self); self.parent.set_status("Errore registrazione.")


# --- Finestra Toplevel per Registra Passaggio Proprietà (con ttkbootstrap) ---
class RegistraPassaggioWindow(tb.Toplevel):
     def __init__(self, parent, db_manager, theme):
        super().__init__(parent, title="Registra Passaggio Proprietà")
        self.parent = parent
        self.db_manager = db_manager
        self.geometry("850x800")
        self.transient(parent); self.grab_set()
        self.nuovi_possessori_list = []; self.immobili_trasferiti_ids = []
        main_frame = tb.Frame(self, padding=15); main_frame.pack(expand=YES, fill=BOTH)
        main_frame.columnconfigure(0, weight=1); main_frame.rowconfigure(4, weight=1); main_frame.rowconfigure(5, weight=1)
        part_frame = tb.LabelFrame(main_frame, text=" Partite Coinvolte ", padding=10, bootstyle="info"); part_frame.grid(row=0, column=0, padx=5, pady=10, sticky=EW); part_frame.columnconfigure(1, weight=1); part_frame.columnconfigure(3, weight=1)
        tb.Label(part_frame, text="ID Partita Origine*:").grid(row=0, column=0, padx=5, pady=5, sticky=W); self.partita_origine_id_entry = tb.Entry(part_frame, width=10); self.partita_origine_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=W); tb.Button(part_frame, text="Carica Immobili Origine", bootstyle="info-outline", command=self.carica_immobili_origine).grid(row=0, column=2, padx=10, pady=5)
        tb.Label(part_frame, text="Comune Dest.*:").grid(row=1, column=0, padx=5, pady=5, sticky=W); self.nuovo_comune_entry = tb.Entry(part_frame); self.nuovo_comune_entry.grid(row=1, column=1, padx=5, pady=5, sticky=EW)
        tb.Label(part_frame, text="Numero Nuova Partita*:").grid(row=1, column=2, padx=5, pady=5, sticky=W); self.nuovo_numero_entry = tb.Entry(part_frame, width=10); self.nuovo_numero_entry.grid(row=1, column=3, padx=5, pady=5, sticky=W)
        var_frame = tb.LabelFrame(main_frame, text=" Dati Variazione ", padding=10, bootstyle="info"); var_frame.grid(row=1, column=0, padx=5, pady=10, sticky=EW); var_frame.columnconfigure(1, weight=1); var_frame.columnconfigure(3, weight=1)
        tb.Label(var_frame, text="Tipo Variazione*:").grid(row=0, column=0, padx=5, pady=5, sticky=W); self.tipo_var_var = tk.StringVar(); tb.Combobox(var_frame, textvariable=self.tipo_var_var, values=["Vendita", "Successione", "Donazione", "Frazionamento", "Altro"], state="readonly").grid(row=0, column=1, padx=5, pady=5, sticky=EW); self.tipo_var_var.set("Vendita")
        tb.Label(var_frame, text="Data Variazione*:").grid(row=0, column=2, padx=5, pady=5, sticky=W); self.data_var_entry = DateEntry(var_frame, date_pattern='yyyy-mm-dd', width=12); self.data_var_entry.grid(row=0, column=3, padx=5, pady=5, sticky=W); self.data_var_entry.set_date(date.today())
        contr_frame = tb.LabelFrame(main_frame, text=" Dati Contratto/Atto ", padding=10, bootstyle="info"); contr_frame.grid(row=2, column=0, padx=5, pady=10, sticky=EW); contr_frame.columnconfigure(1, weight=1); contr_frame.columnconfigure(3, weight=1)
        tb.Label(contr_frame, text="Tipo Contratto*:").grid(row=0, column=0, padx=5, pady=5, sticky=W); self.tipo_contr_entry = tb.Entry(contr_frame); self.tipo_contr_entry.grid(row=0, column=1, padx=5, pady=5, sticky=EW)
        tb.Label(contr_frame, text="Data Contratto*:").grid(row=0, column=2, padx=5, pady=5, sticky=W); self.data_contr_entry = DateEntry(contr_frame, date_pattern='yyyy-mm-dd', width=12); self.data_contr_entry.grid(row=0, column=3, padx=5, pady=5, sticky=W); self.data_contr_entry.set_date(date.today())
        tb.Label(contr_frame, text="Notaio:").grid(row=1, column=0, padx=5, pady=5, sticky=W); self.notaio_entry = tb.Entry(contr_frame); self.notaio_entry.grid(row=1, column=1, padx=5, pady=5, sticky=EW)
        tb.Label(contr_frame, text="Repertorio:").grid(row=1, column=2, padx=5, pady=5, sticky=W); self.repertorio_entry = tb.Entry(contr_frame); self.repertorio_entry.grid(row=1, column=3, padx=5, pady=5, sticky=EW)
        note_frame = tb.LabelFrame(main_frame, text=" Note ", padding=10, bootstyle="info"); note_frame.grid(row=3, column=0, padx=5, pady=10, sticky=EW); self.note_text = ScrolledText(note_frame, height=3, width=60, wrap=WORD, autohide=True); self.note_text.pack(expand=YES, fill=BOTH, padx=5, pady=5)
        nuovi_poss_main_frame = tb.LabelFrame(main_frame, text=" Nuovi Possessori (Opzionale) ", padding=10, bootstyle="info"); nuovi_poss_main_frame.grid(row=4, column=0, padx=5, pady=10, sticky=NSEW); nuovi_poss_main_frame.columnconfigure(0, weight=1); nuovi_poss_main_frame.rowconfigure(1, weight=1)
        poss_input_frame = tb.Frame(nuovi_poss_main_frame); poss_input_frame.grid(row=0, column=0, sticky=EW, pady=(0,10)); poss_input_frame.columnconfigure(1, weight=1); poss_input_frame.columnconfigure(3, weight=1)
        tb.Label(poss_input_frame, text="Nome Completo:").grid(row=0, column=0, padx=5, pady=3, sticky=W); self.nuovo_poss_nome_entry = tb.Entry(poss_input_frame); self.nuovo_poss_nome_entry.grid(row=0, column=1, padx=5, pady=3, sticky=EW); tb.Button(poss_input_frame, text="Cerca/Nuovo", bootstyle="info-outline", command=self.gestisci_nuovo_possessore).grid(row=0, column=4, padx=(10,0), pady=3)
        tb.Label(poss_input_frame, text="Cognome Nome:").grid(row=1, column=0, padx=5, pady=3, sticky=W); self.nuovo_poss_cgn_entry = tb.Entry(poss_input_frame); self.nuovo_poss_cgn_entry.grid(row=1, column=1, padx=5, pady=3, sticky=EW); tb.Label(poss_input_frame, text="Paternità:").grid(row=1, column=2, padx=5, pady=3, sticky=W); self.nuovo_poss_pat_entry = tb.Entry(poss_input_frame); self.nuovo_poss_pat_entry.grid(row=1, column=3, padx=5, pady=3, sticky=EW)
        tb.Label(poss_input_frame, text="Quota:").grid(row=2, column=0, padx=5, pady=3, sticky=W); self.nuovo_poss_quota_entry = tb.Entry(poss_input_frame, width=15); self.nuovo_poss_quota_entry.grid(row=2, column=1, padx=5, pady=3, sticky=W); tb.Button(poss_input_frame, text="Aggiungi Possessore", bootstyle="primary", command=self.aggiungi_nuovo_possessore_lista).grid(row=3, column=0, columnspan=5, pady=10)
        poss_tree_frame = tb.Frame(nuovi_poss_main_frame); poss_tree_frame.grid(row=1, column=0, sticky=NSEW); poss_tree_frame.rowconfigure(0, weight=1); poss_tree_frame.columnconfigure(0, weight=1)
        poss_cols = ("nome_completo", "cognome_nome", "paternita", "quota"); self.nuovi_poss_tree = tb.Treeview(poss_tree_frame, columns=poss_cols, show="headings", height=3, bootstyle="info");
        for col in poss_cols: self.nuovi_poss_tree.heading(col, text=col.replace('_', ' ').title()); self.nuovi_poss_tree.column(col, width=160, anchor=W)
        poss_vsb = tb.Scrollbar(poss_tree_frame, orient=VERTICAL, command=self.nuovi_poss_tree.yview, bootstyle="round"); self.nuovi_poss_tree.configure(yscrollcommand=poss_vsb.set); self.nuovi_poss_tree.grid(row=0, column=0, sticky=NSEW); poss_vsb.grid(row=0, column=1, sticky=NS)
        tb.Button(nuovi_poss_main_frame, text="Rimuovi Selezionato", bootstyle="danger-outline", command=self.rimuovi_nuovo_possessore_lista).grid(row=2, column=0, padx=5, pady=(5,0), sticky=W)
        imm_trasf_frame = tb.LabelFrame(main_frame, text=" Immobili da Trasferire (Opzionale) ", padding=10, bootstyle="info"); imm_trasf_frame.grid(row=5, column=0, padx=5, pady=10, sticky=NSEW); imm_trasf_frame.rowconfigure(0, weight=1); imm_trasf_frame.columnconfigure(0, weight=1)
        imm_cols_trasf = ("id", "natura", "localita", "classificazione"); self.imm_trasf_tree = tb.Treeview(imm_trasf_frame, columns=imm_cols_trasf, show="headings", height=4, selectmode=EXTENDED, bootstyle="info") # selectmode=EXTENDED
        for col in imm_cols_trasf: self.imm_trasf_tree.heading(col, text=col.replace('_', ' ').title()); self.imm_trasf_tree.column(col, width=150 if col != "id" else 50, anchor=W)
        imm_vsb_trasf = tb.Scrollbar(imm_trasf_frame, orient=VERTICAL, command=self.imm_trasf_tree.yview, bootstyle="round"); self.imm_trasf_tree.configure(yscrollcommand=imm_vsb_trasf.set); self.imm_trasf_tree.grid(row=0, column=0, sticky=NSEW); imm_vsb_trasf.grid(row=0, column=1, sticky=NS)
        tb.Label(main_frame, text="* Campi obbligatori", bootstyle="secondary").grid(row=6, column=0, padx=5, pady=10, sticky=E)
        button_frame = tb.Frame(main_frame); button_frame.grid(row=7, column=0, pady=15)
        tb.Button(button_frame, text="Registra Passaggio", bootstyle="success", command=self.registra).pack(side=LEFT, padx=10)
        tb.Button(button_frame, text="Annulla", bootstyle="secondary-outline", command=self.destroy).pack(side=LEFT, padx=10)
        self.wait_window()

     def carica_immobili_origine(self):
         partita_id_str = self.partita_origine_id_entry.get().strip()
         if not partita_id_str: Messagebox.show_warning("Inserire ID Partita Origine.", title="ID Mancante", parent=self); return
         try: partita_id = int(partita_id_str)
         except ValueError: Messagebox.show_error("ID Partita Origine deve essere intero.", title="Input Errato", parent=self); return
         try:
             if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
             for item in self.imm_trasf_tree.get_children(): self.imm_trasf_tree.delete(item)
             partita_details = self.db_manager.get_partita_details(partita_id)
             if not partita_details or 'immobili' not in partita_details or not partita_details['immobili']: Messagebox.show_info(f"Nessun immobile trovato per partita ID {partita_id}.", title="Nessun Immobile", parent=self); return
             for imm in partita_details['immobili']: values = (imm.get('id', ''), imm.get('natura', ''), imm.get('localita_nome', ''), imm.get('classificazione', '')); self.imm_trasf_tree.insert("", END, values=values, iid=imm.get('id'))
         except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self)
         except Exception as e: Messagebox.show_error(f"Errore caricamento immobili:\n{e}", title="Errore Caricamento", parent=self)

     def gestisci_nuovo_possessore(self):
        nome_completo = self.nuovo_poss_nome_entry.get().strip(); comune = self.nuovo_comune_entry.get().strip()
        if not nome_completo or not comune: Messagebox.show_warning("Inserire Nuovo Comune e Nome Completo possessore.", title="Dati Mancanti", parent=self); return
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            poss_id = self.db_manager.check_possessore_exists(nome_completo, comune)
            if poss_id:
                 if Messagebox.yesno(f"Possessore '{nome_completo}' trovato (ID: {poss_id}).\nVuoi usarlo?", title="Possessore Esistente", parent=self):
                    self.nuovo_poss_cgn_entry.delete(0, END); self.nuovo_poss_pat_entry.delete(0, END); Messagebox.show_info("Possessore selezionato. Inserisci quota e aggiungi.", title="Info", parent=self)
                 else: self.nuovo_poss_nome_entry.delete(0, END)
            else: Messagebox.show_info(f"Possessore '{nome_completo}' non trovato.\nInserisci dettagli per aggiungerlo.", title="Possessore Non Trovato", parent=self); self.nuovo_poss_cgn_entry.focus()
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self)
        except Exception as e: Messagebox.show_error(f"Errore:\n{e}", title="Errore Ricerca", parent=self)

     def aggiungi_nuovo_possessore_lista(self):
        nome = self.nuovo_poss_nome_entry.get().strip(); cognome_nome = self.nuovo_poss_cgn_entry.get().strip(); paternita = self.nuovo_poss_pat_entry.get().strip(); quota = self.nuovo_poss_quota_entry.get().strip()
        if not nome: Messagebox.show_warning("Inserire Nome Completo.", title="Dati Mancanti", parent=self); return
        poss_data = {"nome_completo": nome, "cognome_nome": cognome_nome or None, "paternita": paternita or None, "quota": quota or None}
        values = (nome, cognome_nome or "", paternita or "", quota or ""); item_id = self.nuovi_poss_tree.insert("", END, values=values); self.nuovi_possessori_list.append({"id": item_id, "data": poss_data})
        self.nuovo_poss_nome_entry.delete(0, END); self.nuovo_poss_cgn_entry.delete(0, END); self.nuovo_poss_pat_entry.delete(0, END); self.nuovo_poss_quota_entry.delete(0, END); self.nuovo_poss_nome_entry.focus()

     def rimuovi_nuovo_possessore_lista(self):
        sel = self.nuovi_poss_tree.selection();
        if not sel: Messagebox.show_warning("Selezionare un possessore.", title="Nessuna Selezione", parent=self); return
        iid = sel[0]; self.nuovi_poss_tree.delete(iid); self.nuovi_possessori_list = [p for p in self.nuovi_possessori_list if p["id"] != iid]

     def registra(self):
        partita_origine_id_str = self.partita_origine_id_entry.get().strip(); nuovo_comune = self.nuovo_comune_entry.get().strip(); nuovo_numero_str = self.nuovo_numero_entry.get().strip(); tipo_variazione = self.tipo_var_var.get()
        data_variazione = self.data_var_entry.get_date(); tipo_contratto = self.tipo_contr_entry.get().strip(); data_contratto = self.data_contr_entry.get_date(); notaio = self.notaio_entry.get().strip()
        repertorio = self.repertorio_entry.get().strip(); note = self.note_text.get("1.0", END).strip()
        if not partita_origine_id_str or not nuovo_comune or not nuovo_numero_str or not tipo_variazione or not tipo_contratto: Messagebox.show_warning("Compilare campi obbligatori (*).", title="Dati Mancanti", parent=self); return
        try: partita_origine_id = int(partita_origine_id_str); nuovo_numero_partita = int(nuovo_numero_str)
        except ValueError: Messagebox.show_error("ID Partita e Numero Nuova Partita devono essere interi.", title="Input Errato", parent=self); return
        nuovi_possessori_json_list = [p["data"] for p in self.nuovi_possessori_list] if self.nuovi_possessori_list else None
        selected_imm_items = self.imm_trasf_tree.selection()
        immobili_da_trasferire = None
        if selected_imm_items:
             try: immobili_da_trasferire = [int(item_id) for item_id in selected_imm_items]
             except ValueError: Messagebox.show_error("Errore lettura ID immobili.", title="Errore Interno", parent=self); return
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            success = self.db_manager.registra_passaggio_proprieta(partita_origine_id=partita_origine_id, comune_nome=nuovo_comune, numero_partita=nuovo_numero_partita, tipo_variazione=tipo_variazione, data_variazione=data_variazione, tipo_contratto=tipo_contratto, data_contratto=data_contratto, notaio=notaio or None, repertorio=repertorio or None, nuovi_possessori=nuovi_possessori_json_list, immobili_da_trasferire=immobili_da_trasferire, note=note or None)
            if success:
                 self.parent.set_status(f"Passaggio proprietà registrato (Nuova P.{nuovo_numero_partita}, C.{nuovo_comune})."); Messagebox.show_info(f"Passaggio proprietà registrato.", title="Successo", parent=self.parent); self.destroy()
            else: Messagebox.show_error("Errore registrazione passaggio.\nControllare i log.", title="Errore Database", parent=self); self.parent.set_status("Errore registrazione passaggio.")
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self); self.parent.set_status("Errore: DB non connesso.")
        except Exception as e: self.db_manager.rollback(); Messagebox.show_error(f"Errore: {e}", title="Errore Imprevisto", parent=self); self.parent.set_status("Errore registrazione passaggio.")


# --- Classe Principale dell'Applicazione GUI (Versione 3 - ttkbootstrap) ---
# (Definizione spostata PRIMA di main_gui_v3)
class CatastoAppV3(tb.Window):
    def __init__(self, db_config, theme="litera"):
        super().__init__(themename=theme)
        self.title("Gestore Catasto Storico V3 (ttkbootstrap)")
        self.geometry("1000x750")
        self.current_theme = theme
        self.db_manager = CatastoDBManager(**db_config)
        self.initial_connection_success = False
        try:
            if self.db_manager.connect(): self.initial_connection_success = True
        except Exception as e: print(f"Errore iniziale connessione DB: {e}")
        self.selected_item_id = None
        self.create_menu()
        self.notebook = tb.Notebook(self, bootstyle="info")
        self.tab_consultazione = tb.Frame(self.notebook); self.tab_inserimento = tb.Frame(self.notebook); self.tab_report = tb.Frame(self.notebook); self.tab_manutenzione = tb.Frame(self.notebook)
        self.notebook.add(self.tab_consultazione, text=" Consultazione Dati "); self.notebook.add(self.tab_inserimento, text=" Inserimento e Gestione "); self.notebook.add(self.tab_report, text=" Generazione Report "); self.notebook.add(self.tab_manutenzione, text=" Manutenzione DB ")
        self.notebook.pack(expand=YES, fill=BOTH, padx=10, pady=10)
        self.crea_tab_consultazione(); self.crea_tab_inserimento(); self.crea_tab_report(); self.crea_tab_manutenzione()
        self.status_bar = tb.Label(self, text="Pronto", relief=SUNKEN, anchor=W, padding=5, bootstyle="light"); self.status_bar.pack(side=BOTTOM, fill=X)
        if self.initial_connection_success: self.set_status("Connesso al database.")
        else: self.set_status("Non connesso. Usare File -> Connetti o Impostazioni.")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_registra_consultazione_window(self):
        if not self.db_manager.conn or self.db_manager.conn.closed: Messagebox.show_error("Connessione DB non attiva.", title="Errore", parent=self); return
        window = RegistraConsultazioneWindow(self, self.db_manager, self.current_theme)
    def open_registra_nuova_proprieta_window(self):
        if not self.db_manager.conn or self.db_manager.conn.closed: Messagebox.show_error("Connessione DB non attiva.", title="Errore", parent=self); return
        window = RegistraNuovaProprietaWindow(self, self.db_manager, self.current_theme)
    def open_registra_passaggio_window(self):
        if not self.db_manager.conn or self.db_manager.conn.closed: Messagebox.show_error("Connessione DB non attiva.", title="Errore", parent=self); return
        window = RegistraPassaggioWindow(self, self.db_manager, self.current_theme)

    def set_status(self, message): self.status_bar.config(text=message)
    def on_closing(self):
        if Messagebox.okcancel("Chiudere l'applicazione?", title="Esci", parent=self):
            if self.db_manager and self.db_manager.conn and not self.db_manager.conn.closed: self.db_manager.disconnect(); print("Connessione DB chiusa.")
            self.destroy()

    def create_menu(self):
        menubar = tk.Menu(self); file_menu = tk.Menu(menubar, tearoff=0); op_menu = tk.Menu(menubar, tearoff=0); report_menu = tk.Menu(menubar, tearoff=0); man_menu = tk.Menu(menubar, tearoff=0); help_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Connetti/Riconnetti", command=self.connect_db); file_menu.add_command(label="Impostazioni Connessione", command=self.show_connection_settings); file_menu.add_separator(); file_menu.add_command(label="Esci", command=self.on_closing)
        op_menu.add_command(label="Aggiungi Comune", command=self.trigger_add_comune); op_menu.add_command(label="Aggiungi Possessore", command=self.trigger_add_possessore); op_menu.add_separator(); op_menu.add_command(label="Registra Nuova Proprietà", command=self.open_registra_nuova_proprieta_window); op_menu.add_command(label="Registra Passaggio Proprietà", command=self.open_registra_passaggio_window); op_menu.add_command(label="Registra Consultazione", command=self.open_registra_consultazione_window)
        report_menu.add_command(label="Genera Certificato Proprietà", command=self.trigger_report_certificato); report_menu.add_command(label="Genera Report Genealogico", command=self.trigger_report_genealogico); report_menu.add_command(label="Genera Report Possessore", command=self.trigger_report_possessore)
        man_menu.add_command(label="Verifica Integrità Database", command=self.verifica_integrita)
        help_menu.add_command(label="Informazioni", command=self.show_about)
        menubar.add_cascade(label="File", menu=file_menu); menubar.add_cascade(label="Operazioni", menu=op_menu); menubar.add_cascade(label="Report", menu=report_menu); menubar.add_cascade(label="Manutenzione", menu=man_menu); menubar.add_cascade(label="Aiuto", menu=help_menu)
        self.config(menu=menubar)

    def connect_db(self):
        if self.db_manager.connect(): self.set_status("Connesso al database."); Messagebox.show_info("Connessione stabilita.", title="Connessione", parent=self)
        else: self.set_status("Errore connessione.")
    def show_connection_settings(self):
        settings_window = tb.Toplevel(self, title="Impostazioni Connessione"); settings_window.transient(self); settings_window.grab_set()
        tb.Label(settings_window, text="Impostazioni Database", font=("Helvetica", 12, "bold")).pack(pady=10)
        form_frame = tb.Frame(settings_window, padding=15); form_frame.pack(fill=BOTH, expand=YES)
        current_config = self.db_manager.conn_params if self.db_manager.conn_params else {}; fields = ["host", "port", "dbname", "user", "password"]; labels = ["Host:", "Porta:", "Nome DB:", "Utente:", "Password:"]; entries = {}
        for i, field in enumerate(fields):
            tb.Label(form_frame, text=labels[i]).grid(row=i, column=0, sticky=W, pady=5, padx=5); entry = tb.Entry(form_frame, width=30)
            if field == "password": entry.config(show="*")
            entry.grid(row=i, column=1, pady=5, padx=5, sticky=EW); entry.insert(0, current_config.get(field, "")); entries[field] = entry; form_frame.columnconfigure(1, weight=1)
        def save_settings():
            new_config = {};
            for field, entry in entries.items(): new_config[field] = entry.get()
            try: new_config["port"] = int(new_config["port"])
            except ValueError: Messagebox.show_error("La porta deve essere un numero.", title="Errore Input", parent=settings_window); return
            self.db_manager.conn_params = new_config; self.db_manager.schema = getattr(self.db_manager, 'schema', 'catasto')
            if self.db_manager.connect(): Messagebox.show_info("Connessione stabilita.", title="Successo", parent=self); self.set_status("Connesso."); settings_window.destroy()
            else: self.set_status("Errore connessione.")
        buttons_frame = tb.Frame(settings_window); buttons_frame.pack(pady=20)
        tb.Button(buttons_frame, text="Salva e Connetti", bootstyle="success", command=save_settings).pack(side=LEFT, padx=10); tb.Button(buttons_frame, text="Annulla", bootstyle="secondary-outline", command=settings_window.destroy).pack(side=LEFT, padx=10)
        settings_window.wait_window()
    def show_about(self): Messagebox.show_info(message="Gestore Catasto Storico V3\nBasata su Tkinter, ttkbootstrap e CatastoDBManager.", title="Informazioni", parent=self)
    def trigger_add_comune(self): self.notebook.select(self.tab_inserimento);
    def trigger_add_possessore(self): self.notebook.select(self.tab_inserimento);
    def trigger_report_certificato(self): self.notebook.select(self.tab_report);
    def trigger_report_genealogico(self): self.notebook.select(self.tab_report);
    def trigger_report_possessore(self): self.notebook.select(self.tab_report);

    def crea_tab_consultazione(self):
        tab = self.tab_consultazione; tab.columnconfigure(0, weight=1); tab.rowconfigure(1, weight=1)
        top_frame = tb.Frame(tab, padding=10); top_frame.grid(row=0, column=0, sticky=EW, padx=5, pady=(10,5))
        tb.Label(top_frame, text="Cerca per:").pack(side=LEFT, padx=(0, 5)); self.search_type_var = tk.StringVar(value="Comuni")
        search_options = ["Comuni", "Partite per Comune", "Possessori per Comune", "Partite (Avanzato)"]
        search_combo = tb.Combobox(top_frame, textvariable=self.search_type_var, values=search_options, state="readonly", width=20); search_combo.pack(side=LEFT, padx=5); search_combo.bind("<<ComboboxSelected>>", self.update_search_fields)
        self.search_entry1_label = tb.Label(top_frame, text="Nome:"); self.search_entry1_label.pack(side=LEFT, padx=(10, 0)); self.search_entry1 = tb.Entry(top_frame, width=25); self.search_entry1.pack(side=LEFT, padx=5, fill=X, expand=YES)
        self.search_advanced_frame = tb.Frame(top_frame)
        self.search_entry2_label = tb.Label(self.search_advanced_frame, text="Num. Partita:"); self.search_entry2 = tb.Entry(self.search_advanced_frame, width=10)
        self.search_entry3_label = tb.Label(self.search_advanced_frame, text="Possessore:"); self.search_entry3 = tb.Entry(self.search_advanced_frame, width=20)
        self.search_entry4_label = tb.Label(self.search_advanced_frame, text="Natura Imm.:"); self.search_entry4 = tb.Entry(self.search_advanced_frame, width=15)
        btn_frame_top = tb.Frame(top_frame); btn_frame_top.pack(side=RIGHT, padx=(10, 0))
        tb.Button(btn_frame_top, text="Cerca", bootstyle="primary", command=self.esegui_ricerca_consultazione).pack(side=LEFT, padx=5); tb.Button(btn_frame_top, text="Pulisci", bootstyle="secondary-outline", command=self.pulisci_risultati_consultazione).pack(side=LEFT, padx=5)
        tree_frame = tb.Frame(tab); tree_frame.grid(row=1, column=0, sticky=NSEW, padx=5, pady=5); tree_frame.columnconfigure(0, weight=1); tree_frame.rowconfigure(0, weight=1)
        self.consult_tree = tb.Treeview(tree_frame, show="headings", bootstyle="primary"); vsb = tb.Scrollbar(tree_frame, orient=VERTICAL, command=self.consult_tree.yview, bootstyle="round"); hsb = tb.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.consult_tree.xview, bootstyle="round"); self.consult_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.consult_tree.grid(row=0, column=0, sticky=NSEW); vsb.grid(row=0, column=1, sticky=NS); hsb.grid(row=1, column=0, sticky=EW); self.consult_context_menu = tk.Menu(self.consult_tree, tearoff=0)
        self.consult_tree.bind("<Button-3>", self.show_consult_context_menu); self.consult_tree.bind("<Double-1>", self.on_consult_tree_double_click)
        self.update_search_fields(); self.setup_treeview("Comuni")

    def crea_tab_inserimento(self):
        tab = self.tab_inserimento; tab.columnconfigure(0, weight=1); content_frame = tb.Frame(tab, padding=15); content_frame.grid(row=0, column=0, sticky=NSEW); content_frame.columnconfigure(0, weight=1); tab.rowconfigure(0, weight=1)
        comune_frame = tb.LabelFrame(content_frame, text=" Aggiungi Nuovo Comune ", padding=10, bootstyle="info"); comune_frame.grid(row=0, column=0, padx=5, pady=10, sticky=EW); comune_frame.columnconfigure(1, weight=1)
        tb.Label(comune_frame, text="Nome:").grid(row=0, column=0, padx=5, pady=4, sticky=W); self.comune_nome_entry = tb.Entry(comune_frame); self.comune_nome_entry.grid(row=0, column=1, padx=5, pady=4, sticky=EW)
        tb.Label(comune_frame, text="Provincia:").grid(row=1, column=0, padx=5, pady=4, sticky=W); self.comune_provincia_entry = tb.Entry(comune_frame); self.comune_provincia_entry.grid(row=1, column=1, padx=5, pady=4, sticky=EW)
        tb.Label(comune_frame, text="Regione:").grid(row=2, column=0, padx=5, pady=4, sticky=W); self.comune_regione_entry = tb.Entry(comune_frame); self.comune_regione_entry.grid(row=2, column=1, padx=5, pady=4, sticky=EW); tb.Button(comune_frame, text="Aggiungi Comune", bootstyle="primary", command=self.aggiungi_comune).grid(row=3, column=0, columnspan=2, pady=10)
        poss_frame = tb.LabelFrame(content_frame, text=" Aggiungi Nuovo Possessore ", padding=10, bootstyle="info"); poss_frame.grid(row=1, column=0, padx=5, pady=10, sticky=EW); poss_frame.columnconfigure(1, weight=1)
        tb.Label(poss_frame, text="Comune*:").grid(row=0, column=0, padx=5, pady=4, sticky=W); self.poss_comune_entry = tb.Entry(poss_frame); self.poss_comune_entry.grid(row=0, column=1, padx=5, pady=4, sticky=EW)
        tb.Label(poss_frame, text="Cognome e Nome*:").grid(row=1, column=0, padx=5, pady=4, sticky=W); self.poss_cognome_nome_entry = tb.Entry(poss_frame); self.poss_cognome_nome_entry.grid(row=1, column=1, padx=5, pady=4, sticky=EW)
        tb.Label(poss_frame, text="Paternità:").grid(row=2, column=0, padx=5, pady=4, sticky=W); self.poss_paternita_entry = tb.Entry(poss_frame); self.poss_paternita_entry.grid(row=2, column=1, padx=5, pady=4, sticky=EW); tb.Label(poss_frame, text="(es. 'fu Roberto')", bootstyle="secondary").grid(row=2, column=2, padx=5, pady=4, sticky=W)
        tb.Label(poss_frame, text="Nome Completo:").grid(row=3, column=0, padx=5, pady=4, sticky=W); self.poss_nome_completo_entry = tb.Entry(poss_frame); self.poss_nome_completo_entry.grid(row=3, column=1, padx=5, pady=4, sticky=EW); tb.Label(poss_frame, text="(opzionale)", bootstyle="secondary").grid(row=3, column=2, padx=5, pady=4, sticky=W); tb.Button(poss_frame, text="Aggiungi Possessore", bootstyle="primary", command=self.aggiungi_possessore).grid(row=4, column=0, columnspan=3, pady=10)
        action_frame = tb.LabelFrame(content_frame, text=" Altre Operazioni di Inserimento ", padding=10, bootstyle="info"); action_frame.grid(row=2, column=0, padx=5, pady=10, sticky=EW); btn_pack_frame = tb.Frame(action_frame); btn_pack_frame.pack(pady=5)
        tb.Button(btn_pack_frame, text="Registra Nuova Proprietà...", bootstyle="success", command=self.open_registra_nuova_proprieta_window).pack(side=LEFT, padx=5, pady=5); tb.Button(btn_pack_frame, text="Registra Passaggio Proprietà...", bootstyle="success", command=self.open_registra_passaggio_window).pack(side=LEFT, padx=5, pady=5); tb.Button(btn_pack_frame, text="Registra Consultazione...", bootstyle="success", command=self.open_registra_consultazione_window).pack(side=LEFT, padx=5, pady=5)

    def crea_tab_report(self):
        tab = self.tab_report; tab.columnconfigure(0, weight=1); tab.rowconfigure(1, weight=1); content_frame = tb.Frame(tab, padding=15); content_frame.grid(row=0, column=0, sticky=NSEW); content_frame.columnconfigure(0, weight=1); content_frame.rowconfigure(2, weight=1); tab.rowconfigure(0, weight=1)
        report_frame = tb.LabelFrame(content_frame, text=" Genera Report ", padding=10, bootstyle="info"); report_frame.grid(row=0, column=0, padx=5, pady=10, sticky=EW); report_frame.columnconfigure(1, weight=1)
        tb.Label(report_frame, text="Tipo Report:").grid(row=0, column=0, padx=5, pady=5, sticky=W); self.report_type_var = tk.StringVar(); self.report_combobox = tb.Combobox(report_frame, textvariable=self.report_type_var, values=["Certificato Proprietà", "Report Genealogico", "Report Possessore"], state="readonly", width=25); self.report_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=EW); self.report_combobox.current(0)
        tb.Label(report_frame, text="ID Partita/Possessore:").grid(row=1, column=0, padx=5, pady=5, sticky=W); self.report_id_entry = tb.Entry(report_frame, width=10); self.report_id_entry.grid(row=1, column=1, padx=5, pady=5, sticky=W); tb.Button(report_frame, text="Genera Report", bootstyle="primary", command=self.genera_report_gui).grid(row=2, column=0, columnspan=2, pady=10)
        tb.Label(content_frame, text="Anteprima Report:", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, padx=5, pady=(10,0), sticky=W)
        self.report_text_area = ScrolledText(content_frame, height=15, width=80, wrap=WORD, font=("Courier New", 9), autohide=True, bootstyle="info")
        self.report_text_area.grid(row=2, column=0, padx=5, pady=5, sticky=NSEW)
        self.report_text_area.text.config(state=DISABLED) # Usa .text.config
        self.save_report_button = tb.Button(content_frame, text="Salva Report su File...", bootstyle="success", command=self.salva_report_corrente, state=DISABLED); self.save_report_button.grid(row=3, column=0, padx=5, pady=10, sticky=E)
        self.current_report_content = ""; self.current_report_filename = ""

    def crea_tab_manutenzione(self):
        tab = self.tab_manutenzione; tab.columnconfigure(0, weight=1); tab.rowconfigure(1, weight=1); content_frame = tb.Frame(tab, padding=15); content_frame.grid(row=0, column=0, sticky=NSEW); content_frame.columnconfigure(0, weight=1); content_frame.rowconfigure(1, weight=1); tab.rowconfigure(0, weight=1)
        action_frame = tb.LabelFrame(content_frame, text=" Azioni di Manutenzione ", padding=10, bootstyle="info"); action_frame.grid(row=0, column=0, padx=5, pady=10, sticky=EW)
        tb.Button(action_frame, text="Verifica Integrità Database", bootstyle="warning", command=self.verifica_integrita).pack(pady=10, fill=X, padx=10)
        log_frame = tb.LabelFrame(content_frame, text=" Log Operazioni Manutenzione ", padding=10, bootstyle="secondary"); log_frame.grid(row=1, column=0, padx=5, pady=10, sticky=NSEW); log_frame.columnconfigure(0, weight=1); log_frame.rowconfigure(0, weight=1)
        self.manutenzione_log_text = ScrolledText(log_frame, height=10, width=70, wrap=WORD, state=DISABLED, autohide=True, bootstyle="secondary")
        self.manutenzione_log_text.text.config(state=DISABLED) # Usa .text.config
        self.manutenzione_log_text.grid(row=0, column=0, sticky=NSEW)

    # --- Metodi Callback Consultazione / Azioni Menu Contestuale ---
    # (Il codice per questi metodi è incollato sopra)
    # ... (metodi da update_search_fields a display_report_window) ...
    def update_search_fields(self, event=None):
        search_type = self.search_type_var.get()
        self.search_entry1.delete(0, END); self.search_entry2.delete(0, END); self.search_entry3.delete(0, END); self.search_entry4.delete(0, END)
        for widget in [self.search_entry2_label, self.search_entry2, self.search_entry3_label, self.search_entry3, self.search_entry4_label, self.search_entry4]: widget.pack_forget()
        self.search_advanced_frame.pack_forget()
        if search_type == "Comuni": self.search_entry1_label.config(text="Nome Comune:"); self.search_entry1.config(width=25)
        elif search_type == "Partite per Comune" or search_type == "Possessori per Comune": self.search_entry1_label.config(text="Nome Comune:"); self.search_entry1.config(width=25)
        elif search_type == "Partite (Avanzato)":
            self.search_entry1_label.config(text="Comune:"); self.search_entry1.config(width=15); self.search_entry2_label.pack(side=LEFT, padx=(10,0)); self.search_entry2.pack(side=LEFT, padx=5); self.search_entry3_label.pack(side=LEFT, padx=(10,0)); self.search_entry3.pack(side=LEFT, padx=5); self.search_entry4_label.pack(side=LEFT, padx=(10,0)); self.search_entry4.pack(side=LEFT, padx=5); self.search_advanced_frame.pack(side=LEFT, fill=X, expand=YES)
        self.setup_treeview(search_type)
    def setup_treeview(self, view_type):
        self.consult_tree.delete(*self.consult_tree.get_children()); self.consult_tree["columns"] = (); self.consult_context_menu.delete(0, END)
        if view_type == "Comuni":
            cols = ("nome", "provincia", "regione"); self.consult_tree["columns"] = cols; self.consult_tree.heading("nome", text="Nome"); self.consult_tree.column("nome", width=200, anchor=W); self.consult_tree.heading("provincia", text="Provincia"); self.consult_tree.column("provincia", width=100, anchor=W); self.consult_tree.heading("regione", text="Regione"); self.consult_tree.column("regione", width=100, anchor=W)
        elif "Partite" in view_type:
            cols = ("id", "comune_nome", "numero_partita", "tipo", "stato", "possessori", "num_immobili"); self.consult_tree["columns"] = cols; self.consult_tree.heading("id", text="ID"); self.consult_tree.column("id", width=50, anchor=CENTER); self.consult_tree.heading("comune_nome", text="Comune"); self.consult_tree.column("comune_nome", width=150, anchor=W); self.consult_tree.heading("numero_partita", text="Numero"); self.consult_tree.column("numero_partita", width=80, anchor=CENTER); self.consult_tree.heading("tipo", text="Tipo"); self.consult_tree.column("tipo", width=80, anchor=W); self.consult_tree.heading("stato", text="Stato"); self.consult_tree.column("stato", width=80, anchor=W); self.consult_tree.heading("possessori", text="Possessori"); self.consult_tree.column("possessori", width=250, anchor=W); self.consult_tree.heading("num_immobili", text="N.Imm."); self.consult_tree.column("num_immobili", width=60, anchor=CENTER)
            self.consult_context_menu.add_command(label="Visualizza Dettagli Partita", command=self.context_view_partita_details); self.consult_context_menu.add_command(label="Genera Certificato Proprietà", command=self.context_generate_certificato); self.consult_context_menu.add_command(label="Genera Report Genealogico", command=self.context_generate_report_genealogico)
        elif view_type == "Possessori per Comune":
            cols = ("id", "nome_completo", "cognome_nome", "paternita", "attivo"); self.consult_tree["columns"] = cols; self.consult_tree.heading("id", text="ID"); self.consult_tree.column("id", width=50, anchor=CENTER); self.consult_tree.heading("nome_completo", text="Nome Completo"); self.consult_tree.column("nome_completo", width=250, anchor=W); self.consult_tree.heading("cognome_nome", text="Cognome Nome"); self.consult_tree.column("cognome_nome", width=200, anchor=W); self.consult_tree.heading("paternita", text="Paternità"); self.consult_tree.column("paternita", width=100, anchor=W); self.consult_tree.heading("attivo", text="Attivo"); self.consult_tree.column("attivo", width=60, anchor=CENTER)
            self.consult_context_menu.add_command(label="Genera Report Possessore", command=self.context_generate_report_possessore)
    def esegui_ricerca_consultazione(self):
        search_type = self.search_type_var.get(); term1 = self.search_entry1.get().strip(); results = []; self.pulisci_risultati_consultazione(); self.set_status(f"Ricerca '{search_type}'..."); self.update_idletasks()
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: Messagebox.show_error("Database non connesso.", title="Errore", parent=self); self.set_status("Errore: DB non connesso."); return
            if search_type == "Comuni": results = self.db_manager.get_comuni(term1 or None); self.setup_treeview("Comuni")
            elif search_type == "Partite per Comune":
                if not term1: Messagebox.show_warning("Inserire nome comune.", title="Input Mancante", parent=self); self.set_status("Ricerca annullata."); return
                results = self.db_manager.get_partite_by_comune(term1); self.setup_treeview("Partite per Comune")
            elif search_type == "Possessori per Comune":
                if not term1: Messagebox.show_warning("Inserire nome comune.", title="Input Mancante", parent=self); self.set_status("Ricerca annullata."); return
                results = self.db_manager.get_possessori_by_comune(term1); self.setup_treeview("Possessori per Comune")
            elif search_type == "Partite (Avanzato)":
                 numero_str = self.search_entry2.get().strip(); possessore = self.search_entry3.get().strip(); natura = self.search_entry4.get().strip(); numero_partita = None
                 if numero_str:
                    try: numero_partita = int(numero_str)
                    except ValueError: Messagebox.show_error("Numero partita deve essere intero.", title="Input Errato", parent=self); self.set_status("Ricerca fallita."); return
                 results = self.db_manager.search_partite(comune_nome=term1 or None, numero_partita=numero_partita, possessore=possessore or None, immobile_natura=natura or None); self.setup_treeview("Partite (Avanzato)")
            if results:
                headers = self.consult_tree["columns"]
                for row_dict in results: row_values = [row_dict.get(col, '') for col in headers]; item_id = row_dict.get('id', None); self.consult_tree.insert("", END, values=row_values, iid=item_id)
                self.set_status(f"Ricerca '{search_type}' completata: {len(results)} risultati.")
            else: self.set_status(f"Ricerca '{search_type}' completata: Nessun risultato.")
        except Exception as e: Messagebox.show_error(f"Errore:\n{e}", title="Errore Ricerca", parent=self); self.set_status(f"Errore ricerca '{search_type}'.")
    def pulisci_risultati_consultazione(self): self.consult_tree.delete(*self.consult_tree.get_children()); self.set_status("Risultati puliti.")
    def show_consult_context_menu(self, event):
        item_iid = self.consult_tree.identify_row(event.y)
        if item_iid: self.consult_tree.selection_set(item_iid); self.selected_item_id = item_iid
        if self.consult_context_menu.index(END) is not None: self.consult_context_menu.post(event.x_root, event.y_root)
        else: self.selected_item_id = None
    def on_consult_tree_double_click(self, event):
         region = self.consult_tree.identify_region(event.x, event.y);
         if region == "cell":
             item_iid = self.consult_tree.identify_row(event.y)
             if item_iid: self.selected_item_id = item_iid; view_type = self.search_type_var.get()
             if "Partite" in view_type: self.context_view_partita_details()
    def context_view_partita_details(self):
        if self.selected_item_id is None: Messagebox.show_warning("Nessuna partita selezionata.", title="Azione non possibile", parent=self); return
        try: partita_id = int(self.selected_item_id); self.open_partita_details_window(partita_id)
        except ValueError: Messagebox.show_error("ID Partita non valido.", title="Errore", parent=self)
        except Exception as e: Messagebox.show_error(f"Impossibile visualizzare dettagli:\n{e}", title="Errore", parent=self)
        finally: self.selected_item_id = None
    def open_partita_details_window(self, partita_id):
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            partita = self.db_manager.get_partita_details(partita_id)
            if not partita: Messagebox.show_info(f"Nessuna partita trovata con ID {partita_id}.", title="Dettagli Partita", parent=self); return
            details_window = tb.Toplevel(self); details_window.title(f"Dettagli Partita {partita.get('numero_partita','N/A')} ({partita.get('comune_nome','N/A')})"); details_window.geometry("700x550"); details_window.transient(self); details_window.grab_set()
            text_area = ScrolledText(details_window, wrap=WORD, padx=10, pady=10, autohide=True, font=("Consolas", 10)); text_area.pack(expand=YES, fill=BOTH)
            text_area.insert(END, f"DETTAGLI PARTITA ID: {partita.get('id', 'N/A')}\n=========================================\n"); text_area.insert(END, f"Comune:         {partita.get('comune_nome', 'N/A')}\nNumero Partita: {partita.get('numero_partita', 'N/A')}\n"); text_area.insert(END, f"Tipo:           {partita.get('tipo', 'N/A')}\nStato:          {partita.get('stato', 'N/A')}\n"); text_area.insert(END, f"Data Impianto:  {partita.get('data_impianto', 'N/A')}\n");
            if partita.get('data_chiusura'): text_area.insert(END, f"Data Chiusura:  {partita['data_chiusura']}\n")
            text_area.insert(END, f"\n--- POSSESSORI ---\n");
            if partita.get('possessori'):
                for pos in partita['possessori']: quota_str = f" (Quota: {pos['quota']})" if pos.get('quota') else ""; text_area.insert(END, f"- ID {pos.get('id', 'N/A')}: {pos.get('nome_completo', 'N/A')}{quota_str}\n")
            else: text_area.insert(END, "  Nessuno\n")
            text_area.insert(END, f"\n--- IMMOBILI ---\n");
            if partita.get('immobili'):
                 for imm in partita['immobili']:
                     text_area.insert(END, f"- ID {imm.get('id', 'N/A')}: {imm.get('natura', 'N/A')} in Loc. {imm.get('localita_nome', 'N/A')}\n"); details = [];
                     if imm.get('consistenza'): details.append(f"Consistenza: {imm['consistenza']}")
                     if imm.get('classificazione'): details.append(f"Class.: {imm['classificazione']}")
                     if imm.get('numero_piani'): details.append(f"Piani: {imm['numero_piani']}")
                     if imm.get('numero_vani'): details.append(f"Vani: {imm['numero_vani']}")
                     if details: text_area.insert(END, f"    ({', '.join(details)})\n")
            else: text_area.insert(END, "  Nessuno\n")
            text_area.insert(END, f"\n--- VARIAZIONI COLLEGATE ---\n");
            if partita.get('variazioni'):
                for var in partita['variazioni']:
                    text_area.insert(END, f"- ID {var.get('id', 'N/A')}: {var.get('tipo', 'N/A')} del {var.get('data_variazione', 'N/A')}\n")
                    if var.get('tipo_contratto'): contr_details = f"    Contratto: {var['tipo_contratto']} del {var.get('data_contratto', 'N/A')}";
                    if var.get('notaio'): contr_details += f", Notaio: {var['notaio']}";
                    if var.get('repertorio'): contr_details += f", Rep: {var['repertorio']}"; text_area.insert(END, contr_details + "\n")
                    if var.get('note'): text_area.insert(END, f"    Note: {var['note']}\n")
            else: text_area.insert(END, "  Nessuna\n")
            text_area.text.config(state=DISABLED); tb.Button(details_window, text="Chiudi", bootstyle="secondary", command=details_window.destroy).pack(pady=10) # Usa .text.config
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self)
        except Exception as e: Messagebox.show_error(f"Errore caricamento:\n{e}", title="Errore Dettagli", parent=self)
    def context_generate_certificato(self):
        if self.selected_item_id is None: Messagebox.show_warning("Nessuna partita selezionata.", title="Azione non possibile", parent=self); return
        try:
            partita_id = int(self.selected_item_id);
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            report_content = self.db_manager.genera_certificato_proprieta(partita_id); self.display_report_window(f"Certificato Partita {partita_id}", report_content, f"certificato_partita_{partita_id}.txt")
        except ValueError: Messagebox.show_error("ID Partita non valido.", title="Errore", parent=self)
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self)
        except Exception as e: Messagebox.show_error(f"Impossibile generare certificato:\n{e}", title="Errore", parent=self)
        finally: self.selected_item_id = None
    def context_generate_report_genealogico(self):
        if self.selected_item_id is None: Messagebox.show_warning("Nessuna partita selezionata.", title="Azione non possibile", parent=self); return
        try:
            partita_id = int(self.selected_item_id)
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            report_content = self.db_manager.genera_report_genealogico(partita_id); self.display_report_window(f"Report Genealogico Partita {partita_id}", report_content, f"report_genealogico_{partita_id}.txt")
        except ValueError: Messagebox.show_error("ID Partita non valido.", title="Errore", parent=self)
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self)
        except Exception as e: Messagebox.show_error(f"Impossibile generare report genealogico:\n{e}", title="Errore", parent=self)
        finally: self.selected_item_id = None
    def context_generate_report_possessore(self):
        if self.selected_item_id is None: Messagebox.show_warning("Nessun possessore selezionato.", title="Azione non possibile", parent=self); return
        try:
            possessore_id = int(self.selected_item_id)
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            report_content = self.db_manager.genera_report_possessore(possessore_id); self.display_report_window(f"Report Possessore ID {possessore_id}", report_content, f"report_possessore_{possessore_id}.txt")
        except ValueError: Messagebox.show_error("ID Possessore non valido.", title="Errore", parent=self)
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self)
        except Exception as e: Messagebox.show_error(f"Impossibile generare report possessore:\n{e}", title="Errore", parent=self)
        finally: self.selected_item_id = None
    def display_report_window(self, title, content, save_filename):
        if not content: Messagebox.show_info("Nessun dato da visualizzare.", title=title, parent=self); return
        report_window = tb.Toplevel(self); report_window.title(title); report_window.geometry("800x600"); report_window.transient(self); report_window.grab_set()
        text_area = ScrolledText(report_window, wrap=WORD, padx=10, pady=10, autohide=True, font=("Courier New", 10)); text_area.pack(expand=YES, fill=BOTH); text_area.insert(END, content); text_area.text.config(state=DISABLED) # Usa .text.config
        button_frame = tb.Frame(report_window); button_frame.pack(pady=10)
        def save_report():
            file_path = filedialog.asksaveasfilename(parent=report_window, title="Salva Report", initialfile=save_filename, defaultextension=".txt", filetypes=[("File Testo", "*.txt"), ("Tutti i File", "*.*")])
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
                    Messagebox.show_info(f"Salvato in:\n{file_path}", title="Report Salvato", parent=report_window)
                except Exception as e: Messagebox.show_error(f"Impossibile salvare:\n{e}", title="Errore Salvataggio", parent=report_window)
        tb.Button(button_frame, text="Salva su File...", bootstyle="success", command=save_report).pack(side=LEFT, padx=10); tb.Button(button_frame, text="Chiudi", bootstyle="secondary", command=report_window.destroy).pack(side=LEFT, padx=10)

    # --- Metodi Callback Inserimento / Report / Manutenzione ---
    def aggiungi_comune(self):
        nome = self.comune_nome_entry.get().strip(); provincia = self.comune_provincia_entry.get().strip(); regione = self.comune_regione_entry.get().strip()
        if not nome or not provincia or not regione: Messagebox.show_warning("Inserire nome, provincia e regione.", title="Dati Mancanti", parent=self); return
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            if self.db_manager.execute_query("INSERT INTO comune (nome, provincia, regione) VALUES (%s, %s, %s) ON CONFLICT (nome) DO NOTHING", (nome, provincia, regione)):
                self.db_manager.commit(); self.set_status(f"Comune '{nome}' inserito."); Messagebox.show_info(f"Comune '{nome}' inserito/già esistente.", title="Successo", parent=self)
                self.comune_nome_entry.delete(0, END); self.comune_provincia_entry.delete(0, END); self.comune_regione_entry.delete(0, END)
            else: Messagebox.show_error("Errore inserimento comune.", title="Errore Database", parent=self); self.set_status("Errore inserimento comune.")
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self); self.set_status("Errore: DB non connesso.")
        except Exception as e: self.db_manager.rollback(); Messagebox.show_error(f"Errore:\n{e}", title="Errore", parent=self); self.set_status("Errore inserimento comune.")
    def aggiungi_possessore(self):
        comune = self.poss_comune_entry.get().strip(); cognome_nome = self.poss_cognome_nome_entry.get().strip(); paternita = self.poss_paternita_entry.get().strip(); nome_completo = self.poss_nome_completo_entry.get().strip()
        if not comune or not cognome_nome: Messagebox.show_warning("Inserire Comune e Cognome e Nome.", title="Dati Mancanti", parent=self); return
        if not nome_completo: nome_completo = f"{cognome_nome} {paternita}".strip()
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            possessore_id = self.db_manager.insert_possessore(comune, cognome_nome, paternita, nome_completo, True)
            if possessore_id:
                self.set_status(f"Possessore '{nome_completo}' (ID: {possessore_id}) inserito."); Messagebox.show_info(f"Possessore '{nome_completo}' inserito (ID: {possessore_id}).", title="Successo", parent=self)
                self.poss_comune_entry.delete(0, END); self.poss_cognome_nome_entry.delete(0, END); self.poss_paternita_entry.delete(0, END); self.poss_nome_completo_entry.delete(0, END)
            else: Messagebox.show_error("Errore inserimento possessore.", title="Errore Database", parent=self); self.set_status("Errore inserimento possessore.")
        except ConnectionError as ce: Messagebox.show_error(str(ce), title="Errore Database", parent=self); self.set_status("Errore: DB non connesso.")
        except Exception as e: self.db_manager.rollback(); Messagebox.show_error(f"Errore:\n{e}", title="Errore", parent=self); self.set_status("Errore inserimento possessore.")
    def genera_report_gui(self):
        report_type = self.report_type_var.get(); id_str = self.report_id_entry.get().strip()
        self.current_report_content = ""; self.current_report_filename = ""; self.save_report_button.config(state=DISABLED)
        self.report_text_area.text.config(state=NORMAL); self.report_text_area.delete('1.0', END) # Usa .text.config
        if not id_str: Messagebox.show_warning("Inserire ID Partita/Possessore.", title="Input Mancante", parent=self); self.report_text_area.text.config(state=DISABLED); return # Usa .text.config
        try: item_id = int(id_str)
        except ValueError: Messagebox.show_error("L'ID deve essere un intero.", title="Input Errato", parent=self); self.report_text_area.text.config(state=DISABLED); return # Usa .text.config
        report_content = ""; default_filename = "report.txt"; self.set_status(f"Generazione '{report_type}'..."); self.update_idletasks()
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            if report_type == "Certificato Proprietà": report_content = self.db_manager.genera_certificato_proprieta(item_id); default_filename = f"certificato_partita_{item_id}.txt"
            elif report_type == "Report Genealogico": report_content = self.db_manager.genera_report_genealogico(item_id); default_filename = f"report_genealogico_{item_id}.txt"
            elif report_type == "Report Possessore": report_content = self.db_manager.genera_report_possessore(item_id); default_filename = f"report_possessore_{item_id}.txt"
            if report_content: self.report_text_area.insert(END, report_content); self.current_report_content = report_content; self.current_report_filename = default_filename; self.save_report_button.config(state=NORMAL); self.set_status(f"Report '{report_type}' generato.")
            else: self.report_text_area.insert(END, f"Nessun {report_type} generato per ID {item_id}."); self.set_status(f"Report '{report_type}' non generato.")
        except ConnectionError as e: Messagebox.show_error(str(e), title="Errore Database", parent=self); self.set_status("Errore: DB non connesso.")
        except Exception as e: error_msg = f"Errore generazione report '{report_type}':\n{e}"; Messagebox.show_error(error_msg, title="Errore", parent=self); self.report_text_area.insert(END, error_msg); self.set_status(f"Errore generazione report.")
        finally: self.report_text_area.text.config(state=DISABLED) # Usa .text.config
    def salva_report_corrente(self):
        if not self.current_report_content: Messagebox.show_warning("Nessun report generato da salvare.", title="Nessun Report", parent=self); return
        file_path = filedialog.asksaveasfilename(parent=self, title="Salva Report", initialfile=self.current_report_filename, defaultextension=".txt", filetypes=[("File Testo", "*.txt"), ("Tutti i File", "*.*")])
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f: f.write(self.current_report_content)
                self.set_status(f"Report salvato in {file_path}"); Messagebox.show_info(f"Salvato in:\n{file_path}", title="Report Salvato", parent=self)
            except Exception as e: self.set_status(f"Errore salvataggio report."); Messagebox.show_error(f"Impossibile salvare:\n{e}", title="Errore Salvataggio", parent=self)
    def add_manutenzione_log(self, message):
         timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); log_message = f"[{timestamp}] {message}\n"
         self.manutenzione_log_text.text.config(state=NORMAL); self.manutenzione_log_text.insert(END, log_message); self.manutenzione_log_text.see(END); self.manutenzione_log_text.text.config(state=DISABLED) # Usa .text.config
    def verifica_integrita(self):
        self.add_manutenzione_log("Avvio verifica integrità..."); self.set_status("Verifica integrità..."); self.update_idletasks()
        try:
            if not self.db_manager.conn or self.db_manager.conn.closed: raise ConnectionError("Database non connesso.")
            self.db_manager.execute_query("CALL verifica_integrita_database(NULL)"); self.db_manager.commit()
            log_msg = "Verifica completata. Controllare log server PostgreSQL."; self.add_manutenzione_log(log_msg); Messagebox.show_info(log_msg, title="Verifica Integrità", parent=self); self.set_status("Verifica completata.")
        except ConnectionError as e: error_msg = f"Errore: {e}"; self.add_manutenzione_log(error_msg); Messagebox.show_error(error_msg, title="Errore Database", parent=self); self.set_status("Errore: DB non connesso.")
        except Exception as e: self.db_manager.rollback(); error_msg = f"Errore verifica integrità: {e}"; self.add_manutenzione_log(error_msg); Messagebox.show_error(error_msg, title="Errore Manutenzione", parent=self); self.set_status("Errore verifica.")


# --- Funzione Principale per Avviare l'App ---
def main_gui_v3():
    db_config = { "dbname": "catasto_storico", "user": "postgres", "password": "Markus74", "host": "localhost", "port": 5432, "schema": "catasto" }
    selected_theme = "litera" # Prova altri temi: cosmo, flatly, darkly, superhero, yeti, pulse, sandstone, lumen
    app = CatastoAppV3(db_config, theme=selected_theme)
    app.mainloop()

# --- Blocco di Esecuzione ---
if __name__ == "__main__":
    main_gui_v3()