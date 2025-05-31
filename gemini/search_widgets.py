#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Widget di Ricerca per Gestionale Catasto Storico
===============================================
Autore: Marco Santoro
Data: 31/05/2025
Versione: 1.0
"""

import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

# Importazioni PyQt5
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QLineEdit, QGroupBox, QGridLayout, 
                            QTableWidget, QTableWidgetItem, QDialog,
                            QMessageBox, QSpinBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QDate, QSettings
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QStyle

# Importa le utilità
from utils import gui_logger

# Importa componenti UI
from ui_components import ComuneSelectionDialog

# Importa riferimento al database manager
try:
    from catasto_db_manager import CatastoDBManager
except ImportError:
    gui_logger.error("Impossibile importare CatastoDBManager. Verificare l'installazione.")
    # Definizione di fallback per permettere l'esecuzione in fase di sviluppo
    class CatastoDBManager:
        pass

class RicercaPartiteWidget(QWidget):
    """Widget per la ricerca delle partite catastali."""
    def __init__(self, db_manager, parent=None):
        super(RicercaPartiteWidget, self).__init__(parent)
        self.db_manager = db_manager
        
        layout = QVBoxLayout()
        
        # Criteri di ricerca
        criteria_group = QGroupBox("Criteri di Ricerca")
        criteria_layout = QGridLayout()
        
        # Comune
        comune_label = QLabel("Comune:")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune)
        self.comune_id = None
        self.comune_display = QLabel("Nessun comune selezionato")
        self.clear_comune_button = QPushButton("Cancella")
        self.clear_comune_button.clicked.connect(self.clear_comune)
        
        criteria_layout.addWidget(comune_label, 0, 0)
        criteria_layout.addWidget(self.comune_button, 0, 1)
        criteria_layout.addWidget(self.comune_display, 0, 2)
        criteria_layout.addWidget(self.clear_comune_button, 0, 3)
        
        # Numero partita
        numero_label = QLabel("Numero Partita:")
        self.numero_edit = QSpinBox()
        self.numero_edit.setMinimum(0)
        self.numero_edit.setMaximum(9999)
        self.numero_edit.setSpecialValueText("Qualsiasi")
        
        criteria_layout.addWidget(numero_label, 1, 0)
        criteria_layout.addWidget(self.numero_edit, 1, 1)
        
        # Possessore
        possessore_label = QLabel("Nome Possessore:")
        self.possessore_edit = QLineEdit()
        self.possessore_edit.setPlaceholderText("Qualsiasi possessore")
        
        criteria_layout.addWidget(possessore_label, 2, 0)
        criteria_layout.addWidget(self.possessore_edit, 2, 1, 1, 3)
        
        # Natura immobile
        natura_label = QLabel("Natura Immobile:")
        self.natura_edit = QLineEdit()
        self.natura_edit.setPlaceholderText("Qualsiasi natura immobile")
        
        criteria_layout.addWidget(natura_label, 3, 0)
        criteria_layout.addWidget(self.natura_edit, 3, 1, 1, 3)
        
        criteria_group.setLayout(criteria_layout)
        layout.addWidget(criteria_group)
        
        # Pulsante Ricerca
        search_button = QPushButton("Cerca Partite")
        search_button.clicked.connect(self.do_search)
        layout.addWidget(search_button)
        
        # Risultati
        results_group = QGroupBox("Risultati")
        results_layout = QVBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["ID", "Comune", "Numero", "Tipo", "Stato"])
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        results_layout.addWidget(self.results_table)
        
        # Dettagli partita selezionata
        self.detail_button = QPushButton("Mostra Dettagli Partita")
        self.detail_button.clicked.connect(self.show_details)
        results_layout.addWidget(self.detail_button)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        self.setLayout(layout)

    def select_comune(self):
        """Apre il selettore di comuni."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(f"Comune selezionato: {dialog.selected_comune_name}")

    def clear_comune(self):
        """Cancella il comune selezionato."""
        self.comune_id = None
        self.comune_display.setText("Nessun comune selezionato")

    def do_search(self):
        """Esegue la ricerca partite in base ai criteri."""
        try:
            # Prepara criteri di ricerca
            criteria = {}
            
            if self.comune_id:
                criteria['comune_id'] = self.comune_id
                
            numero = self.numero_edit.value()
            if numero > 0:  # 0 è "Qualsiasi"
                criteria['numero_partita'] = numero
                
            possessore = self.possessore_edit.text().strip()
            if possessore:
                criteria['possessore_nome'] = possessore
                
            natura = self.natura_edit.text().strip()
            if natura:
                criteria['natura_immobile'] = natura
            
            # Esegui ricerca
            results = self.db_manager.search_partite(criteria)
            
            # Popola tabella risultati
            self.results_table.setRowCount(0)
            for i, partita in enumerate(results):
                self.results_table.insertRow(i)
                
                # ID
                id_item = QTableWidgetItem(str(partita.get('id', '')))
                id_item.setData(Qt.UserRole, partita.get('id'))
                self.results_table.setItem(i, 0, id_item)
                
                # Comune
                comune_item = QTableWidgetItem(partita.get('comune_nome', ''))
                self.results_table.setItem(i, 1, comune_item)
                
                # Numero
                numero_item = QTableWidgetItem(str(partita.get('numero_partita', '')))
                self.results_table.setItem(i, 2, numero_item)
                
                # Tipo
                tipo_item = QTableWidgetItem(partita.get('tipo', ''))
                self.results_table.setItem(i, 3, tipo_item)
                
                # Stato
                stato_text = "Attiva" if partita.get('attiva') else "Non attiva"
                stato_item = QTableWidgetItem(stato_text)
                self.results_table.setItem(i, 4, stato_item)
            
            # Aggiusta dimensioni colonne
            self.results_table.resizeColumnsToContents()
            
            # Messaggio su risultati
            count = len(results)
            if count == 0:
                QMessageBox.information(self, "Risultati Ricerca", "Nessuna partita trovata con i criteri specificati.")
            else:
                QMessageBox.information(self, "Risultati Ricerca", f"Trovate {count} partite.")
        
        except Exception as e:
            gui_logger.exception(f"Errore durante la ricerca partite: {e}")
            QMessageBox.critical(self, "Errore", f"Errore durante la ricerca: {e}")

    def show_details(self):
        """Mostra i dettagli della partita selezionata."""
        selected_indexes = self.results_table.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "Selezione", "Seleziona una partita dalla tabella.")
            return
        
        # Prendi l'ID dalla prima cella della riga selezionata
        row = selected_indexes[0].row()
        partita_id = self.results_table.item(row, 0).data(Qt.UserRole)
        
        try:
            # Assume che PartitaDetailsDialog sia disponibile altrove nel codice
            from ui_components import PartitaDetailsDialog
            dialog = PartitaDetailsDialog(self.db_manager, partita_id, self)
            dialog.exec_()
        except ImportError:
            # Fallback se PartitaDetailsDialog non è ancora implementato
            details = self.db_manager.get_partita_details(partita_id)
            if details:
                details_str = "\n".join([f"{k}: {v}" for k, v in details.items()])
                QMessageBox.information(self, f"Dettagli Partita {partita_id}", details_str)
            else:
                QMessageBox.warning(self, "Errore", f"Impossibile recuperare dettagli per partita ID: {partita_id}")

class RicercaPossessoriWidget(QWidget):
    """Widget per la ricerca dei possessori."""
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        main_layout = QVBoxLayout(self)
        
        # --- Gruppo per i Criteri di Ricerca ---
        search_criteria_group = QGroupBox("Criteri di Ricerca Possessori")
        criteria_layout = QGridLayout(search_criteria_group)
        
        criteria_layout.addWidget(QLabel("Termine di ricerca (nome, cognome, ecc.):"), 0, 0)
        self.search_term_edit = QLineEdit()
        self.search_term_edit.setPlaceholderText("Inserisci parte del nome o altri termini...")
        criteria_layout.addWidget(self.search_term_edit, 0, 1, 1, 2)
        
        criteria_layout.addWidget(QLabel("Soglia di similarità (0.0 - 1.0):"), 1, 0)
        self.similarity_threshold_spinbox = QDoubleSpinBox()
        self.similarity_threshold_spinbox.setMinimum(0.0)
        self.similarity_threshold_spinbox.setMaximum(1.0)
        self.similarity_threshold_spinbox.setSingleStep(0.05)
        self.similarity_threshold_spinbox.setValue(0.3) 
        criteria_layout.addWidget(self.similarity_threshold_spinbox, 1, 1)
        
        self.search_button = QPushButton("Cerca Possessori")
        self.search_button.setIcon(QApplication.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.search_button.clicked.connect(self._perform_search)
        criteria_layout.addWidget(self.search_button, 1, 2)
        
        main_layout.addWidget(search_criteria_group)
        
        # --- Tabella per i Risultati ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7) 
        self.results_table.setHorizontalHeaderLabels([
            "ID", "Nome Completo", "Cognome Nome", "Paternità", "Comune Rif.", "Similarità", "Num. Partite"
        ])
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.itemSelectionChanged.connect(self._aggiorna_stato_pulsanti_azione)
        self.results_table.itemDoubleClicked.connect(self.apri_modifica_possessore_selezionato)
        
        main_layout.addWidget(self.results_table)
        
        # --- Pulsanti di Azione sotto la Tabella ---
        action_layout = QHBoxLayout()
        self.btn_modifica_possessore = QPushButton(QApplication.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Modifica Selezionato")
        self.btn_modifica_possessore.setToolTip("Modifica i dati del possessore selezionato")
        self.btn_modifica_possessore.clicked.connect(self.apri_modifica_possessore_selezionato)
        self.btn_modifica_possessore.setEnabled(False)
        action_layout.addWidget(self.btn_modifica_possessore)
        action_layout.addStretch()
        main_layout.addLayout(action_layout)
        
        self.setLayout(main_layout)

    def _aggiorna_stato_pulsanti_azione(self):
        """Abilita/disabilita i pulsanti di azione in base alla selezione nella tabella."""
        selected_id = self._get_selected_possessore_id()
        self.btn_modifica_possessore.setEnabled(selected_id is not None)

    def _get_selected_possessore_id(self):
        """Restituisce l'ID del possessore attualmente selezionato nella tabella dei risultati."""
        selected_indexes = self.results_table.selectedIndexes()
        if not selected_indexes:
            return None
        
        # Prendi l'ID dalla prima cella della riga selezionata
        row = selected_indexes[0].row()
        id_item = self.results_table.item(row, 0)
        if id_item:
            try:
                return int(id_item.text())
            except (ValueError, TypeError):
                return None
        return None

    def apri_modifica_possessore_selezionato(self):
        """Apre il dialogo di modifica per il possessore selezionato."""
        possessore_id = self._get_selected_possessore_id()
        if possessore_id is None:
            QMessageBox.warning(self, "Selezione", "Seleziona un possessore dalla tabella.")
            return
            
        try:
            # Assume che PossessoreDetailsDialog sia disponibile altrove nel codice
            from ui_components import PossessoreDetailsDialog
            dialog = PossessoreDetailsDialog(self.db_manager, possessore_id, self)
            if dialog.exec_() == QDialog.Accepted:
                # Se il possessore è stato modificato, aggiorna la tabella
                self._perform_search()
        except ImportError:
            # Fallback se PossessoreDetailsDialog non è ancora implementato
            details = self.db_manager.get_possessore_details(possessore_id)
            if details:
                details_str = "\n".join([f"{k}: {v}" for k, v in details.items()])
                QMessageBox.information(self, f"Dettagli Possessore {possessore_id}", details_str)
            else:
                QMessageBox.warning(self, "Errore", f"Impossibile recuperare dettagli per possessore ID: {possessore_id}")

    def _perform_search(self):
        """Esegue la ricerca dei possessori."""
        search_term = self.search_term_edit.text().strip()
        if not search_term:
            QMessageBox.warning(self, "Ricerca", "Inserisci un termine di ricerca.")
            return
            
        similarity = self.similarity_threshold_spinbox.value()
        
        try:
            results = self.db_manager.search_possessori(search_term, similarity)
            
            # Pulisci e popola la tabella dei risultati
            self.results_table.setRowCount(0)
            for i, possessore in enumerate(results):
                self.results_table.insertRow(i)
                
                # ID
                id_item = QTableWidgetItem(str(possessore.get('id', '')))
                self.results_table.setItem(i, 0, id_item)
                
                # Nome Completo
                nome_item = QTableWidgetItem(possessore.get('nome_completo', ''))
                self.results_table.setItem(i, 1, nome_item)
                
                # Cognome Nome
                cognome_nome_item = QTableWidgetItem(possessore.get('cognome_nome', ''))
                self.results_table.setItem(i, 2, cognome_nome_item)
                
                # Paternità
                paternita_item = QTableWidgetItem(possessore.get('paternita', ''))
                self.results_table.setItem(i, 3, paternita_item)
                
                # Comune Riferimento
                comune_item = QTableWidgetItem(possessore.get('comune_residenza_nome', ''))
                self.results_table.setItem(i, 4, comune_item)
                
                # Similarità
                similarita_item = QTableWidgetItem(f"{possessore.get('similarity', 0):.2f}")
                self.results_table.setItem(i, 5, similarita_item)
                
                # Num. Partite
                num_partite_item = QTableWidgetItem(str(possessore.get('num_partite', 0)))
                self.results_table.setItem(i, 6, num_partite_item)
            
            # Aggiusta dimensioni colonne
            self.results_table.resizeColumnsToContents()
            
            # Messaggio su risultati
            count = len(results)
            if count == 0:
                QMessageBox.information(self, "Risultati Ricerca", "Nessun possessore trovato con i criteri specificati.")
            else:
                QMessageBox.information(self, "Risultati Ricerca", f"Trovati {count} possessori.")
        
        except Exception as e:
            gui_logger.exception(f"Errore durante la ricerca possessori: {e}")
            QMessageBox.critical(self, "Errore", f"Errore durante la ricerca: {e}")
