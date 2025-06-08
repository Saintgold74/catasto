#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGGIORNAMENTO LAYOUT WIDGET RICERCA FUZZY
File: update_widget_layout.py
"""

import shutil
from datetime import datetime
import os

def backup_current_widget():
    """Crea backup del widget attuale"""
    if os.path.exists("fuzzy_search_widget.py"):
        backup_name = f"fuzzy_search_widget_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        shutil.copy2("fuzzy_search_widget.py", backup_name)
        print(f"✅ Backup creato: {backup_name}")
        return True
    return False

def update_gui_main_import():
    """Aggiorna l'import in gui_main.py per il nuovo widget"""
    try:
        with open("gui_main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Sostituisce l'import del vecchio widget con quello nuovo
        old_import = "from fuzzy_search_widget import add_fuzzy_search_tab_to_main_window"
        new_import = "from fuzzy_search_widget import add_optimized_fuzzy_search_tab_to_main_window as add_fuzzy_search_tab_to_main_window"
        
        if old_import in content:
            content = content.replace(old_import, new_import)
            
            with open("gui_main.py", "w", encoding="utf-8") as f:
                f.write(content)
            
            print("✅ Import aggiornato in gui_main.py")
            return True
        else:
            print("⚠️ Import originale non trovato in gui_main.py")
            return False
            
    except Exception as e:
        print(f"❌ Errore aggiornamento import: {e}")
        return False

def main():
    """Aggiorna il widget con layout ottimizzato"""
    print("=" * 55)
    print("AGGIORNAMENTO LAYOUT WIDGET RICERCA FUZZY")
    print("=" * 55)
    
    print("\n1. Backup widget esistente...")
    backup_success = backup_current_widget()
    
    if backup_success:
        print("\n2. Aggiornamento import...")
        import_success = update_gui_main_import()
        
        print("\n📋 ISTRUZIONI FINALI:")
        print("1. Sostituisci il contenuto di 'fuzzy_search_widget.py'")
        print("   con il nuovo codice ottimizzato")
        print("2. Riavvia l'applicazione: python gui_main.py")
        print("3. Il nuovo layout avrà:")
        print("   ✨ Controlli compatti in 2 righe")
        print("   📊 Più spazio per i risultati") 
        print("   🎯 Tabelle ottimizzate")
        print("   🔧 Area debug ridotta")
        
        print(f"\n💾 Backup disponibile per ripristino se necessario")
        
    else:
        print("\n❌ Backup fallito - operazione annullata")

if __name__ == "__main__":
    main()
