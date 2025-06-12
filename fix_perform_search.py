#!/usr/bin/env python3
"""
Script di correzione automatica per aggiungere il metodo _perform_search mancante
"""

def fix_missing_perform_search():
    """Aggiunge il metodo _perform_search mancante al file fuzzy_search_unified.py"""
    
    file_path = "fuzzy_search_unified.py"
    
    # Leggi il file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ File non trovato: {file_path}")
        return False
    except Exception as e:
        print(f"❌ Errore lettura file: {e}")
        return False
    
    # Controlla se il metodo è già presente
    if "def _perform_search(self):" in content:
        print("✅ Metodo _perform_search già presente")
        return True
    
    # Crea backup
    backup_path = file_path + ".backup"
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 Backup creato: {backup_path}")
    except Exception as e:
        print(f"⚠️ Impossibile creare backup: {e}")
    
    # Trova dove inserire il metodo
    # Cerca la fine della classe FuzzySearchWidget
    class_start = content.find("class FuzzySearchWidget(QWidget):")
    if class_start == -1:
        print("❌ Classe FuzzySearchWidget non trovata")
        return False
    
    # Cerca un punto di inserimento appropriato
    # Cerca il metodo _trigger_search_if_text o simili
    search_patterns = [
        "def _trigger_search_if_text(self):",
        "def _on_search_text_changed(self):",
        "def _check_gin_status(self):"
    ]
    
    insertion_point = -1
    for pattern in search_patterns:
        pos = content.find(pattern, class_start)
        if pos != -1:
            # Trova la fine di questo metodo
            method_end = content.find("\n    def ", pos + 1)
            if method_end == -1:
                # Cerca la fine della classe
                method_end = content.find("\n\n# ", pos)
                if method_end == -1:
                    method_end = content.find("\nclass ", pos)
            
            if method_end != -1:
                insertion_point = method_end
                break
    
    if insertion_point == -1:
        print("❌ Impossibile trovare punto di inserimento")
        return False
    
    # Metodo da inserire
    method_code = '''
    def _perform_search(self):
        """Esegue la ricerca fuzzy."""
        query_text = self.search_edit.text().strip()
        if len(query_text) < 3:
            return
        
        if not self.gin_search:
            QMessageBox.warning(self, "Errore", "Sistema di ricerca fuzzy non disponibile")
            return
        
        # Prepara parametri ricerca
        threshold = self.precision_slider.value() / 100.0
        max_results = int(self.max_results_combo.currentText())
        
        # Determina tipo di ricerca
        search_type = 'unified'
        if hasattr(self, 'search_type_combo'):
            type_map = {
                0: 'unified',
                1: 'immobili', 
                2: 'variazioni',
                3: 'contratti',
                4: 'partite',
                5: 'combined'
            }
            search_type = type_map.get(self.search_type_combo.currentIndex(), 'unified')
        
        search_options = {
            'search_type': search_type,
            'threshold': threshold,
            'max_results': max_results,
            'search_possessori': self.search_possessori_cb.isChecked(),
            'search_localita': self.search_localita_cb.isChecked(),
            'search_variazioni': self.search_variazioni_cb.isChecked(),
            'search_immobili': self.search_immobili_cb.isChecked(),
            'search_contratti': self.search_contratti_cb.isChecked(),
            'search_partite': self.search_partite_cb.isChecked(),
            'max_results_per_type': 30
        }
        
        # Avvia ricerca in thread separato
        if self.search_thread and self.search_thread.isRunning():
            return
        
        self.progress_bar.setVisible(True)
        self.status_label.setText("🔍 Ricerca in corso...")
        self.status_label.setStyleSheet("color: blue; font-size: 10px;")
        self.search_btn.setEnabled(False)
        
        self.search_thread = FuzzySearchThread(
            self.gin_search, query_text, search_options
        )
        self.search_thread.results_ready.connect(self._display_results)
        self.search_thread.error_occurred.connect(self._handle_search_error)
        self.search_thread.progress_updated.connect(self.progress_bar.setValue)
        self.search_thread.finished.connect(self._search_finished)
        self.search_thread.start()
    
    def _handle_search_error(self, error_message):
        """Gestisce errori di ricerca."""
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Errore ricerca")
        self.status_label.setStyleSheet("color: red; font-size: 10px;")
        self.search_btn.setEnabled(True)
        QMessageBox.critical(self, "Errore Ricerca", f"Errore durante la ricerca:\\n{error_message}")
    
    def _search_finished(self):
        """Chiamato quando la ricerca termina."""
        self.progress_bar.setVisible(False)
        self.search_btn.setEnabled(True)
    
    def _clear_search(self):
        """Pulisce la ricerca."""
        self.search_edit.clear()
        self._clear_results()
        self.status_label.setText("Ricerca pulita")
    
    def _clear_results(self):
        """Pulisce tutti i risultati."""
        for table in [self.unified_table, self.possessori_table, self.localita_table, 
                     self.variazioni_table, self.immobili_table, self.contratti_table, 
                     self.partite_table]:
            table.setRowCount(0)
        
        # Reset contatori tab
        self.results_tabs.setTabText(1, "👥 Possessori")
        self.results_tabs.setTabText(2, "🏘️ Località")
        self.results_tabs.setTabText(3, "📋 Variazioni")
        self.results_tabs.setTabText(4, "🏢 Immobili")
        self.results_tabs.setTabText(5, "📄 Contratti")
        self.results_tabs.setTabText(6, "📊 Partite")
        
        # Disabilita export
        self.export_btn.setEnabled(False)
        self.results_count_label.setText("0 risultati")
        
        self.current_results = {}
'''
    
    # Inserisci il metodo
    new_content = content[:insertion_point] + method_code + content[insertion_point:]
    
    # Salva il file modificato
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("✅ Metodi aggiunti con successo")
        return True
    except Exception as e:
        print(f"❌ Errore scrittura file: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Correzione metodo _perform_search mancante...")
    
    if fix_missing_perform_search():
        print("\n✅ CORREZIONE COMPLETATA!")
        print("🚀 Ora puoi riavviare l'applicazione:")
        print("   python gui_main.py")
    else:
        print("\n❌ CORREZIONE FALLITA")
        print("⚠️ Applica la correzione manualmente:")
        print("1. Apri fuzzy_search_unified.py")
        print("2. Cerca la classe FuzzySearchWidget")
        print("3. Aggiungi i metodi mancanti come mostrato sopra")
