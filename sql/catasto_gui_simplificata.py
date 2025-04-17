#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI completa per la Gestione del Catasto Storico (Tkinter)
Replica menu, schede e funzionalità principali dell’interfaccia originale.
Corregge:
* import dinamico del modulo `catasto_interface_bis` (o file con trattino)
* ricerca partite: ora è *case‑insensitive* per il nome del comune e funziona
  anche se si indica solo il numero oppure solo il comune.
"""

from __future__ import annotations

import datetime
import importlib.util
import pathlib
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Dict, Optional

from catasto_db_manager import CatastoDBManager

# ---------------------------------------------------------------------------
#  Parametri di connessione (modifica la password!)
# ---------------------------------------------------------------------------
DB_PARAMS: Dict[str, Any] = {
    "dbname": "catasto_storico",
    "user": "postgres",
    "password": "Markus74",  # sostituire
    "host": "localhost",
    "port": 5432,
    "schema": "catasto",
}


# ---------------------------------------------------------------------------
#  Utilities per importare dinamicamente catasto-interface_bis.py
# ---------------------------------------------------------------------------

def _load_bis_module():
    """Importa `catasto_interface_bis` se presente.

    Supporta:
    1. import classico (pip install / PYTHONPATH)
    2. file locale `catasto-interface_bis.py` (con trattino)
    """
    try:
        import catasto_interface_bis as bis  # type: ignore
        return bis
    except ModuleNotFoundError:
        script_dir = pathlib.Path(__file__).resolve().parent
        candidate = script_dir / "catasto-interface_bis.py"
        if not candidate.exists():
            return None
        spec = importlib.util.spec_from_file_location("catasto_interface_bis", str(candidate))
        if spec and spec.loader:
            bis = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = bis  # rende importabile con import standard
            spec.loader.exec_module(bis)  # type: ignore[arg-type]
            return bis
    return None


# ---------------------------------------------------------------------------
#  GUI principale
# ---------------------------------------------------------------------------
class CatastoGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Catasto Storico")
        self.root.geometry("1300x750")

        self.db = CatastoDBManager(**DB_PARAMS)
        if not self.db.connect():
            messagebox.showerror("Errore", "Impossibile connettersi al database")
            self.root.destroy()
            return

        self._init_managers()
        self._create_menu()
        self._create_notebook()
        self._create_status_bar()
        self.set_status("Connesso al database")

    # --------------------------------------------------
    #  INIT MANAGERS
    # --------------------------------------------------
    def _init_managers(self):
        bis = _load_bis_module()
        if bis:
            self.consultazione_manager = bis.ConsultazioneManager(self.db)  # type: ignore[attr-defined]
            self.possessore_manager = bis.PossessoreManager(self.db)  # type: ignore[attr-defined]
            self.partita_manager = bis.PartitaManager(self.db)  # type: ignore[attr-defined]
            self.workflow_manager = bis.WorkflowManager(self.db)  # type: ignore[attr-defined]
        else:
            class _Dummy:
                def __getattr__(self, _name):
                    return lambda *a, **k: messagebox.showinfo("TODO", "Funzione da implementare")

            self.consultazione_manager = self.possessore_manager = self.partita_manager = self.workflow_manager = _Dummy()

    # --------------------------------------------------
    #  MENU
    # --------------------------------------------------
    def _create_menu(self):
        m = tk.Menu(self.root)

        file_menu = tk.Menu(m, tearoff=0)
        file_menu.add_command(label="Impostazioni connessione", command=self._settings_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.root.quit)
        m.add_cascade(label="File", menu=file_menu)

        consult_menu = tk.Menu(m, tearoff=0)
        consult_menu.add_command(label="Nuova consultazione", command=self._placeholder)
        consult_menu.add_command(label="Cerca consultazioni", command=self._placeholder)
        m.add_cascade(label="Consultazioni", menu=consult_menu)

        poss_menu = tk.Menu(m, tearoff=0)
        poss_menu.add_command(label="Nuovo possessore", command=self._placeholder)
        poss_menu.add_command(label="Cerca possessori", command=self._placeholder)
        m.add_cascade(label="Possessori", menu=poss_menu)

        partite_menu = tk.Menu(m, tearoff=0)
        partite_menu.add_command(label="Nuova partita", command=self._placeholder)
        partite_menu.add_command(label="Duplica partita", command=self._placeholder)
        partite_menu.add_separator()
        partite_menu.add_command(label="Genera certificato", command=self._placeholder)
        partite_menu.add_command(label="Genera report genealogico", command=self._placeholder)
        m.add_cascade(label="Partite", menu=partite_menu)

        wf_menu = tk.Menu(m, tearoff=0)
        wf_menu.add_command(label="Registra nuova proprietà", command=self._placeholder)
        wf_menu.add_command(label="Registra passaggio", command=self._placeholder)
        wf_menu.add_command(label="Registra frazionamento", command=self._placeholder)
        wf_menu.add_separator()
        wf_menu.add_command(label="Verifica integrità DB", command=self._placeholder)
        wf_menu.add_command(label="Ripara problemi DB", command=self._placeholder)
        wf_menu.add_command(label="Backup logico dati", command=self._placeholder)
        wf_menu.add_command(label="Sincronizza con Archivio di Stato", command=self._placeholder)
        m.add_cascade(label="Workflow", menu=wf_menu)

        help_menu = tk.Menu(m, tearoff=0)
        help_menu.add_command(label="Informazioni", command=lambda: messagebox.showinfo("Informazioni", "Catasto Storico v1.0"))
        m.add_cascade(label="Aiuto", menu=help_menu)

        self.root.config(menu=m)

    # --------------------------------------------------
    #  NOTEBOOK / TABS
    # --------------------------------------------------
    def _create_notebook(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)

        self._tab_home()
        self._tab_consultazioni()
        self._tab_possessori()
        self._tab_partite()
        self._tab_workflow()

    # --------------------------------------------------
    #  STATUS BAR
    # --------------------------------------------------
    def _create_status_bar(self):
        self.status_bar = ttk.Label(self.root, anchor="w", relief=tk.SUNKEN)
        self.status_bar.pack(fill="x")

    def set_status(self, msg: str):
        self.status_bar.config(text=msg)

    # --------------------------------------------------
    #  TABS IMPLEMENTATION
    # --------------------------------------------------
    def _tab_home(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Home")
        ttk.Label(f, text="Benvenuto nel Catasto Storico", font=("Helvetica", 18)).pack(pady=40)

    def _tab_consultazioni(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Consultazioni")
        cols = ("id", "data", "richiedente")
        self.cons_tree = ttk.Treeview(f, columns=cols, show="headings")
        for cid, header, width in zip(cols, ("ID", "Data", "Richiedente"), (60, 120, 250)):
            self.cons_tree.heading(cid, text=header)
            self.cons_tree.column(cid, width=width, anchor="center")
        self.cons_tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _tab_possessori(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Possessori")
        cols = ("id", "nome", "comune")
        self.pos_tree = ttk.Treeview(f, columns=cols, show="headings")
        for cid, header, width in zip(cols, ("ID", "Nome", "Comune"), (60, 300, 200)):
            self.pos_tree.heading(cid, text=header)
            self.pos_tree.column(cid, width=width, anchor="center")
        self.pos_tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _tab_partite(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Partite")

        top = ttk.Frame(f)
        top.pack(fill="x", pady=5, padx=5)
        ttk.Label(top, text="Comune:").pack(side="left")
        self.search_comune = ttk.Entry(top, width=20)
        self.search_comune.pack(side="left", padx=5)
        ttk.Label(top, text="Numero:").pack(side="left")
        self.search_num = ttk.Entry(top, width=10)
        self.search_num.pack(side="left", padx=5)
        ttk.Button(top, text="Cerca", command=self._search_partite).pack(side="left", padx=5)

        cols = ("id", "comune", "numero", "tipo", "stato")
        self.par_tree = ttk.Treeview(f, columns=cols, show="headings")
        for cid, header, width in zip(cols, ("ID", "Comune", "Numero", "Tipo", "Stato"), (60, 150, 80, 120, 90)):
            self.par_tree.heading(cid, text=header)
            self.par_tree.column(cid, width=width, anchor="center")
        self.par_tree.pack(fill="both", expand=True, padx=5, pady=5)

    def _tab_workflow(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="Workflow")
        actions = [
            ("Nuova proprietà", self._placeholder),
            ("Passaggio", self._placeholder),
            ("Frazionamento", self._placeholder),
            ("Verifica DB", self._placeholder),
            ("Ripara DB", self._placeholder),
            ("Backup", self._placeholder),
        ]
        for i, (txt, cmd) in enumerate(actions):
            ttk.Button(f, text=txt, command=cmd, width=25).grid(row=i // 3, column=i % 3, padx=10, pady=10)

    # --------------------------------------------------
    #  PLACEHOLDER METHODS
    # --------------------------------------------------
    def _placeholder(self):
        messagebox.showinfo("TODO", "Funzione da implementare")

    # --------------------------------------------------
    #  PARTITE SEARCH (case‑insensitive per il comune)
    # --------------------------------------------------
    def _search_partite(self):
        comune_input: str = self.search_comune.get().strip()
        numero_input: str = self.search_num.get().strip()
        numero: Optional[int] = int(numero_input) if numero_input.isdigit() else None

        # Prima prova con il metodo già esistente (match esatto)
        try:
            partite = self.db.search_partite(comune_input or None, numero)  # type: ignore[arg-type]
        except Exception as exc:
            messagebox.showerror("Errore", str(exc))
            return

        # Se nulla trovato e l'utente ha indicato il comune, effettuiamo match case‑insensitive
        if not partite and comune_input:
            try:
                self.db.execute_query(
                    """
                    SELECT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato
                    FROM partita p
                    WHERE (%s IS NULL OR lower(p.comune_nome) = lower(%s))
                      AND (%s IS NULL OR p.numero_partita = %s)
                    ORDER BY p.comune_nome, p.numero_partita
                    """,
                    (comune_input, comune_input, numero, numero),
                )
                partite = self.db.fetchall()
            except Exception as exc:
                messagebox.showerror("Errore", str(exc))
                return

        # Popola la Treeview
        for iid in self.par_tree.get_children():
            self.par_tree.delete(iid)
        if not partite:
            messagebox.showinfo("Ricerca", "Nessuna partita trovata con i criteri indicati")
            return

        for p in partite:
            self.par_tree.insert(
                "",
                "end",
                iid=p["id"],
                values=(p["id"], p["comune_nome"], p["numero_partita"], p["tipo"], p["stato"]),
            )

    # --------------------------------------------------
    #  SETTINGS DIALOG
    # --------------------------------------------------
    def _settings_dialog(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Connessione Database")
        dlg.grab_set()

        entries: Dict[str, tk.Entry] = {}
        for row, key in enumerate(("host", "port", "dbname", "user", "password")):
            ttk.Label(dlg, text=f"{key.capitalize()}: ").grid(row=row, column=0, sticky="e", padx=5, pady=5)
            ent = ttk.Entry(dlg, width=30, show="*" if key == "password" else None)
            ent.insert(0, str(DB_PARAMS[key]))
            ent.grid(row=row, column=1, padx=5, pady=5)
            entries[key] = ent

        def save():
            try:
                DB_PARAMS["host"] = entries["host"].get()
                DB_PARAMS["port"] = int(entries["port"].get())
                DB_PARAMS["dbname"] = entries["dbname"].get()
                DB_PARAMS["user"] = entries["user"].get()
                DB_PARAMS["password"] = entries["password"].get()
                messagebox.showinfo("Informazioni", "Parametri salvati. Riavvia l'applicazione per applicarli.")
                dlg.destroy()
            except Exception as exc:
                messagebox.showerror("Errore", str(exc))

        ttk.Button(dlg, text="Salva", command=save).grid(row=6, column=0, columnspan=2, pady=10)


# ---------------------------------------------------------------------------
#  MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = CatastoGUI(root)
    root.mainloop()
