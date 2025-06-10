# ========================================================================
# FIX INTEGRAZIONE RICERCA FUZZY - COMPATIBILITÀ CATASTO DB MANAGER
# File: fix_fuzzy_integration.py
# ========================================================================

"""
Script per risolvere i problemi di compatibilità dell'integrazione
ricerca fuzzy con il CatastoDBManager esistente.
"""

import os
import shutil
from datetime import datetime

def create_compatibility_adapter():
    """Crea un adapter per rendere compatibile il sistema."""
    
    adapter_code = '''
# ========================================================================
# ADAPTER DI COMPATIBILITÀ PER CATASTO DB MANAGER
# File: catasto_db_adapter.py
# ========================================================================

"""
Adapter per rendere compatibile CatastoDBManager con la ricerca fuzzy ampliata.
"""

import logging
import psycopg2.extras
from contextlib import contextmanager

class CatastoDBAdapter:
    """Adapter per CatastoDBManager esistente."""
    
    def __init__(self, original_db_manager):
        self.original_db_manager = original_db_manager
        self.logger = logging.getLogger(__name__)
        
    @contextmanager
    def get_connection(self):
        """Ottiene una connessione dal pool esistente."""
        conn = None
        try:
            if hasattr(self.original_db_manager, 'pool') and self.original_db_manager.pool:
                conn = self.original_db_manager.pool.getconn()
                yield conn
            else:
                raise Exception("Pool di connessioni non disponibile")
        except Exception as e:
            self.logger.error(f"Errore connessione database: {e}")
            raise
        finally:
            if conn and hasattr(self.original_db_manager, 'pool'):
                self.original_db_manager.pool.putconn(conn)
    
    def execute_query(self, query, params=None):
        """Esegue una query."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    if query.strip().upper().startswith('SELECT'):
                        return cursor.fetchall()
                    else:
                        conn.commit()
                        return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Errore esecuzione query: {e}")
            raise

def adapt_db_manager_for_fuzzy_search(db_manager):
    """Adatta il db_manager per la ricerca fuzzy."""
    
    # Se ha già get_connection, non serve adapter
    if hasattr(db_manager, 'get_connection'):
        return db_manager
    
    # Crea l'adapter
    adapter = CatastoDBAdapter(db_manager)
    
    # Copia i metodi dell'adapter nel db_manager originale
    db_manager.get_connection = adapter.get_connection
    db_manager.execute_query = adapter.execute_query
    
    return db_manager
'''
    
    with open('catasto_db_adapter.py', 'w', encoding='utf-8') as f:
        f.write(adapter_code)
    
    print("✅ Creato catasto_db_adapter.py")

def create_fixed_gin_extension():
    """Crea una versione corretta dell'estensione GIN."""
    
    # Leggi l'estensione esistente
    if not os.path.exists('catasto_gin_extension_expanded.py'):
        print("❌ File catasto_gin_extension_expanded.py non trovato")
        return False
    
    with open('catasto_gin_extension_expanded.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Aggiungi l'import dell'adapter all'inizio
    adapter_import = """
# Import adapter per compatibilità
try:
    from catasto_db_adapter import adapt_db_manager_for_fuzzy_search
except ImportError:
    def adapt_db_manager_for_fuzzy_search(db_manager):
        return db_manager
"""
    
    # Modifica la funzione extend_db_manager_with_gin_expanded
    old_function = """def extend_db_manager_with_gin_expanded(db_manager):
    \"\"\"Estende un'istanza di CatastoDBManager con capacità di ricerca fuzzy ampliata.\"\"\"
    
    if not hasattr(db_manager, 'gin_search_expanded'):"""
    
    new_function = """def extend_db_manager_with_gin_expanded(db_manager):
    \"\"\"Estende un'istanza di CatastoDBManager con capacità di ricerca fuzzy ampliata.\"\"\"
    
    # Adatta il db_manager per compatibilità
    db_manager = adapt_db_manager_for_fuzzy_search(db_manager)
    
    if not hasattr(db_manager, 'gin_search_expanded'):"""
    
    # Sostituisci nel contenuto
    if adapter_import not in content:
        # Trova la prima riga di import e inserisci dopo
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                lines.insert(i, adapter_import)
                break
        content = '\n'.join(lines)
    
    content = content.replace(old_function, new_function)
    
    # Backup e salva
    backup_name = f"catasto_gin_extension_expanded_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    shutil.copy2('catasto_gin_extension_expanded.py', backup_name)
    
    with open('catasto_gin_extension_expanded.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Aggiornato catasto_gin_extension_expanded.py (backup: {backup_name})")
    return True

def create_manual_integration_script():
    """Crea uno script per aggiungere manualmente il tab."""
    
    script_code = '''
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
'''
    
    with open('add_fuzzy_tab_manual.py', 'w', encoding='utf-8') as f:
        f.write(script_code)
    
    print("✅ Creato add_fuzzy_tab_manual.py")

def fix_gui_main_integration():
    """Corregge l'integrazione in gui_main.py."""
    
    if not os.path.exists('gui_main.py'):
        print("❌ File gui_main.py non trovato")
        return False
    
    with open('gui_main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Backup
    backup_name = f"gui_main_backup_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    shutil.copy2('gui_main.py', backup_name)
    
    # Trova e correggi l'integrazione
    old_integration = """integrate_expanded_fuzzy_search_widget(self, self.db_manager)"""
    new_integration = """
        # Integrazione ricerca fuzzy ampliata - versione corretta
        try:
            from fuzzy_search_widget_expanded import ExpandedFuzzySearchWidget
            
            # Crea e aggiungi il widget
            fuzzy_widget = ExpandedFuzzySearchWidget(self.db_manager)
            fuzzy_tab_index = self.tabs.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
            
            self.logger.info(f"Tab Ricerca Fuzzy Ampliato aggiunto all'indice {fuzzy_tab_index}")
            print("✅ Ricerca fuzzy ampliata integrata con successo")
            
        except Exception as e:
            self.logger.error(f"Errore integrazione ricerca fuzzy: {e}")
            print(f"⚠️ Errore integrazione ricerca fuzzy: {e}")"""
    
    # Sostituisci
    if old_integration in content:
        content = content.replace(old_integration, new_integration)
        
        with open('gui_main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ gui_main.py corretto (backup: {backup_name})")
        return True
    else:
        print("⚠️ Codice di integrazione non trovato in gui_main.py")
        return False

def main():
    """Funzione principale di fix."""
    print("=" * 70)
    print("FIX INTEGRAZIONE RICERCA FUZZY AMPLIATA")
    print("=" * 70)
    
    print("\n🔧 CREAZIONE COMPONENTI COMPATIBILITÀ")
    print("-" * 50)
    
    # 1. Crea l'adapter per il database
    create_compatibility_adapter()
    
    # 2. Aggiorna l'estensione GIN
    if create_fixed_gin_extension():
        print("✅ Estensione GIN aggiornata per compatibilità")
    
    # 3. Crea script di integrazione manuale
    create_manual_integration_script()
    
    # 4. Corregge gui_main.py
    if fix_gui_main_integration():
        print("✅ gui_main.py corretto")
    
    print("\n" + "=" * 70)
    print("🎯 SOLUZIONI DISPONIBILI")
    print("=" * 70)
    
    print("\n📋 OPZIONE 1: RIAVVIO APPLICAZIONE (Raccomandato)")
    print("1. Chiudi l'applicazione corrente")
    print("2. Riavvia: python gui_main.py")
    print("3. Il tab dovrebbe apparire automaticamente")
    
    print("\n🔧 OPZIONE 2: INTEGRAZIONE A CALDO")
    print("1. Tieni aperta l'applicazione corrente")
    print("2. Esegui: python add_fuzzy_tab_manual.py")
    print("3. Il tab verrà aggiunto alla finestra aperta")
    
    print("\n✅ COSA È STATO CORRETTO:")
    print("• Compatibilità con il tuo CatastoDBManager")
    print("• Gestione errori get_connection")
    print("• Integrazione diretta del widget")
    print("• Script di fallback per integrazione manuale")
    
    print("\n🎉 RISULTATO ATTESO:")
    print("Tab '🔍 Ricerca Avanzata' con:")
    print("• Dropdown tipo ricerca (Unificata, Solo Immobili, ecc.)")
    print("• 7 tab risultati invece di 2")
    print("• Pulsante Export")
    print("• Ricerca in natura immobili, variazioni, contratti")
    
    return True

if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n🔧 Fix completato alle {datetime.now().strftime('%H:%M:%S')}")
        print("Prova una delle opzioni sopra per vedere la ricerca ampliata!")
    else:
        print(f"\n💥 Fix fallito alle {datetime.now().strftime('%H:%M:%S')}")
    
    input("\nPremi INVIO per chiudere...")
