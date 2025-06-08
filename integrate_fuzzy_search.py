#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTEGRAZIONE RICERCA FUZZY NELLA GUI PRINCIPALE
File: integrate_fuzzy_search.py

Questo script modifica gui_main.py per aggiungere il tab di ricerca fuzzy.
"""

import os
import re
import shutil
from datetime import datetime

def backup_gui_main():
    """Crea un backup di gui_main.py."""
    if os.path.exists("gui_main.py"):
        backup_name = f"gui_main_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        shutil.copy2("gui_main.py", backup_name)
        print(f"✅ Backup creato: {backup_name}")
        return True
    else:
        print("❌ File gui_main.py non trovato")
        return False

def add_import_to_gui_main():
    """Aggiunge l'import del widget fuzzy search."""
    try:
        with open("gui_main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Cerca la sezione degli import
        import_pattern = r"(from PyQt5\.QtWidgets import.*?\n)"
        
        # Aggiunge l'import del nostro widget
        fuzzy_import = """
# Import per ricerca fuzzy (aggiunto automaticamente)
try:
    from fuzzy_search_widget import add_fuzzy_search_tab_to_main_window
    FUZZY_SEARCH_AVAILABLE = True
except ImportError as e:
    print(f"AVVISO: Ricerca fuzzy non disponibile: {e}")
    FUZZY_SEARCH_AVAILABLE = False
"""
        
        # Controlla se l'import è già presente
        if "fuzzy_search_widget" in content:
            print("✅ Import ricerca fuzzy già presente")
            return True
        
        # Trova la posizione dopo gli import PyQt5
        lines = content.split('\n')
        insert_pos = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('from PyQt5') and 'import' in line:
                insert_pos = i + 1
        
        if insert_pos > 0:
            lines.insert(insert_pos, fuzzy_import)
            
            with open("gui_main.py", "w", encoding="utf-8") as f:
                f.write('\n'.join(lines))
            
            print("✅ Import aggiunto a gui_main.py")
            return True
        else:
            print("❌ Non riesco a trovare la sezione import in gui_main.py")
            return False
            
    except Exception as e:
        print(f"❌ Errore aggiunta import: {e}")
        return False

def add_fuzzy_tab_to_setup_tabs():
    """Aggiunge la chiamata per creare il tab fuzzy nel metodo setup_tabs."""
    try:
        with open("gui_main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Cerca il metodo setup_tabs
        setup_tabs_pattern = r"(def setup_tabs\(self\):.*?)(self\.tabs\.setCurrentIndex\(0\))"
        
        fuzzy_tab_code = """
        # === AGGIUNTA TAB RICERCA FUZZY ===
        try:
            if FUZZY_SEARCH_AVAILABLE and self.db_manager and hasattr(self.db_manager, 'pool') and self.db_manager.pool:
                success = add_fuzzy_search_tab_to_main_window(self)
                if success:
                    self.logger.info("Tab Ricerca Fuzzy aggiunto con successo")
                else:
                    self.logger.warning("Impossibile aggiungere tab Ricerca Fuzzy")
            else:
                self.logger.info("Tab Ricerca Fuzzy saltato (requisiti non soddisfatti)")
        except Exception as e:
            self.logger.error(f"Errore aggiunta tab Ricerca Fuzzy: {e}")
        # === FINE AGGIUNTA TAB RICERCA FUZZY ===

        """
        
        # Controlla se il codice è già presente
        if "AGGIUNTA TAB RICERCA FUZZY" in content:
            print("✅ Codice ricerca fuzzy già presente in setup_tabs")
            return True
        
        # Sostituisce aggiungendo il codice prima di setCurrentIndex
        def replacement(match):
            return match.group(1) + fuzzy_tab_code + match.group(2)
        
        new_content = re.sub(setup_tabs_pattern, replacement, content, flags=re.DOTALL)
        
        if new_content != content:
            with open("gui_main.py", "w", encoding="utf-8") as f:
                f.write(new_content)
            print("✅ Codice aggiunto al metodo setup_tabs")
            return True
        else:
            print("❌ Non riesco a trovare il metodo setup_tabs o setCurrentIndex")
            return False
            
    except Exception as e:
        print(f"❌ Errore modifica setup_tabs: {e}")
        return False

def verify_files_exist():
    """Verifica che tutti i file necessari esistano."""
    required_files = [
        "catasto_gin_extension.py",
        "fuzzy_search_widget.py",
        "gui_main.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ File mancanti: {', '.join(missing_files)}")
        return False
    else:
        print("✅ Tutti i file necessari sono presenti")
        return True

def main():
    """Funzione principale di integrazione."""
    print("=" * 60)
    print("INTEGRAZIONE RICERCA FUZZY NELLA GUI CATASTO")
    print("=" * 60)
    
    # 1. Verifica file
    print("\n1. Verifica file necessari...")
    if not verify_files_exist():
        print("\n❌ INTEGRAZIONE FALLITA - File mancanti")
        return False
    
    # 2. Backup
    print("\n2. Creazione backup...")
    if not backup_gui_main():
        print("\n❌ INTEGRAZIONE FALLITA - Impossibile creare backup")
        return False
    
    # 3. Aggiunta import
    print("\n3. Aggiunta import...")
    if not add_import_to_gui_main():
        print("\n❌ INTEGRAZIONE FALLITA - Impossibile aggiungere import")
        return False
    
    # 4. Modifica setup_tabs
    print("\n4. Modifica metodo setup_tabs...")
    if not add_fuzzy_tab_to_setup_tabs():
        print("\n❌ INTEGRAZIONE FALLITA - Impossibile modificare setup_tabs")
        return False
    
    print("\n" + "=" * 60)
    print("✅ INTEGRAZIONE COMPLETATA CON SUCCESSO!")
    print("=" * 60)
    print("\nProssimi passi:")
    print("1. Avvia l'applicazione: python gui_main.py")
    print("2. Cerca il tab '🔍 Ricerca Avanzata'")
    print("3. Testa la ricerca fuzzy con termini come 'Possessore', 'Rossi', 'Via'")
    print("\nNote:")
    print("- Il backup è stato salvato con timestamp")
    print("- Se ci sono problemi, ripristina dal backup")
    print("- La ricerca funziona con minimo 3 caratteri")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ INTEGRAZIONE FALLITA")
        print("Controlla i messaggi di errore sopra e riprova")
