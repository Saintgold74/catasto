
# ========================================================================
# INTEGRAZIONE MANUALE TAB RICERCA FUZZY
# File: add_fuzzy_tab_manual.py
# ========================================================================

"""
Script per aggiungere manualmente il tab di ricerca fuzzy
alla finestra principale già aperta.
"""

def add_fuzzy_tab_to_existing_window():
    """Aggiunge il tab alla finestra esistente."""
    
    print("🔧 INTEGRAZIONE MANUALE TAB RICERCA FUZZY")
    print("-" * 50)
    
    try:
        # Import necessari
        from fuzzy_search_widget_expanded import ExpandedFuzzySearchWidget
        from PyQt5.QtWidgets import QApplication
        
        # Trova la finestra principale dell'app
        app = QApplication.instance()
        if not app:
            print("❌ Applicazione PyQt5 non trovata")
            return False
        
        # Trova la finestra principale
        main_window = None
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'tabs') and hasattr(widget, 'db_manager'):
                main_window = widget
                break
        
        if not main_window:
            print("❌ Finestra principale non trovata")
            print("   Assicurati che l'applicazione sia aperta")
            return False
        
        print(f"✅ Finestra principale trovata: {type(main_window).__name__}")
        
        # Verifica se il tab esiste già
        tab_widget = main_window.tabs
        existing_fuzzy_tab = None
        
        for i in range(tab_widget.count()):
            tab_text = tab_widget.tabText(i)
            if 'Ricerca' in tab_text and ('Fuzzy' in tab_text or 'Avanzata' in tab_text):
                existing_fuzzy_tab = i
                break
        
        if existing_fuzzy_tab is not None:
            print(f"⚠️ Tab ricerca già presente all'indice {existing_fuzzy_tab}")
            
            # Sostituisci con la versione ampliata
            old_widget = tab_widget.widget(existing_fuzzy_tab)
            fuzzy_widget = ExpandedFuzzySearchWidget(main_window.db_manager)
            
            tab_widget.removeTab(existing_fuzzy_tab)
            new_index = tab_widget.insertTab(existing_fuzzy_tab, fuzzy_widget, "🔍 Ricerca Avanzata")
            
            print(f"✅ Tab sostituito con versione ampliata all'indice {new_index}")
            
        else:
            # Aggiungi nuovo tab
            fuzzy_widget = ExpandedFuzzySearchWidget(main_window.db_manager)
            new_index = tab_widget.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
            
            print(f"✅ Nuovo tab aggiunto all'indice {new_index}")
        
        # Attiva il tab
        tab_widget.setCurrentWidget(fuzzy_widget)
        print("✅ Tab ricerca fuzzy attivato")
        
        # Testa il widget
        if hasattr(fuzzy_widget, 'verify_indices'):
            print("🔧 Test verifica indici...")
            fuzzy_widget.verify_indices()
        
        return True
        
    except Exception as e:
        print(f"❌ Errore integrazione: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funzione principale."""
    print("=" * 60)
    print("INTEGRAZIONE MANUALE TAB RICERCA FUZZY")
    print("=" * 60)
    print()
    print("IMPORTANTE: Esegui questo script MENTRE l'applicazione")
    print("principale (gui_main.py) è GIÀ APERTA!")
    print()
    
    input("Premi INVIO quando l'applicazione è aperta...")
    
    if add_fuzzy_tab_to_existing_window():
        print()
        print("🎉 SUCCESSO!")
        print("Il tab 'Ricerca Avanzata' dovrebbe ora essere visibile")
        print("nell'applicazione con tutte le nuove funzionalità.")
    else:
        print()
        print("❌ FALLIMENTO!")
        print("Controlla che l'applicazione sia aperta e riprova.")

if __name__ == "__main__":
    main()
