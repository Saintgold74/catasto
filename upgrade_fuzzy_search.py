# ========================================================================
# SCRIPT DI AGGIORNAMENTO RICERCA FUZZY ESISTENTE
# File: upgrade_fuzzy_search.py
# ========================================================================

"""
Questo script aggiorna il sistema di ricerca fuzzy esistente
per supportare la versione ampliata con immobili, variazioni, contratti e partite.
"""

import os
import shutil
from datetime import datetime

def check_current_situation():
    """Analizza la situazione attuale del sistema ricerca fuzzy."""
    print("🔍 ANALISI SITUAZIONE ATTUALE")
    print("-" * 50)
    
    status = {
        'vecchio_widget': os.path.exists('fuzzy_search_widget.py'),
        'nuovo_widget': os.path.exists('fuzzy_search_widget_expanded.py'),
        'vecchia_estensione': os.path.exists('catasto_gin_extension.py'),
        'nuova_estensione': os.path.exists('catasto_gin_extension_expanded.py'),
        'gui_main': os.path.exists('gui_main.py'),
        'sql_ampliamento': os.path.exists('expand_fuzzy_search.sql')
    }
    
    for item, exists in status.items():
        status_icon = "✅" if exists else "❌"
        print(f"   {status_icon} {item}")
    
    # Analizza gui_main.py
    if status['gui_main']:
        with open('gui_main.py', 'r', encoding='utf-8') as f:
            gui_content = f.read()
        
        integrations = {
            'vecchia_integrazione': 'fuzzy_search_widget' in gui_content and 'expanded' not in gui_content,
            'nuova_integrazione': 'fuzzy_search_widget_expanded' in gui_content,
            'tab_presente': 'Ricerca' in gui_content and ('Fuzzy' in gui_content or 'Avanzata' in gui_content)
        }
        
        print("\n📄 ANALISI GUI_MAIN.PY:")
        for item, exists in integrations.items():
            status_icon = "✅" if exists else "❌"
            print(f"   {status_icon} {item}")
    
    return status

def backup_current_files():
    """Crea backup dei file attuali."""
    print("\n💾 CREAZIONE BACKUP")
    print("-" * 50)
    
    files_to_backup = [
        'fuzzy_search_widget.py',
        'catasto_gin_extension.py',
        'gui_main.py'
    ]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backups_created = []
    
    for file in files_to_backup:
        if os.path.exists(file):
            backup_name = f"{file}_backup_upgrade_{timestamp}"
            shutil.copy2(file, backup_name)
            backups_created.append(backup_name)
            print(f"   ✅ {file} → {backup_name}")
    
    return backups_created

def verify_database_prerequisites():
    """Verifica se il database è pronto per l'ampliamento."""
    print("\n🗄️ VERIFICA PREREQUISITI DATABASE")
    print("-" * 50)
    
    if not os.path.exists('expand_fuzzy_search.sql'):
        print("   ❌ Script SQL di ampliamento non trovato")
        print("   📋 AZIONE RICHIESTA: Salva l'artifact 'expand_fuzzy_search.sql'")
        return False
    
    print("   ✅ Script SQL di ampliamento presente")
    print("   ⚠️ VERIFICA MANUALE: Assicurati che lo script sia stato eseguito in PostgreSQL")
    return True

def update_gui_integration():
    """Aggiorna l'integrazione nella GUI per usare il widget ampliato."""
    print("\n🔧 AGGIORNAMENTO INTEGRAZIONE GUI")
    print("-" * 50)
    
    if not os.path.exists('gui_main.py'):
        print("   ❌ File gui_main.py non trovato")
        return False
    
    # Leggi il contenuto attuale
    with open('gui_main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Sostituzioni per aggiornare alla versione ampliata
    updates = [
        # Aggiorna l'import
        ('from fuzzy_search_widget import', 'from fuzzy_search_widget_expanded import'),
        ('fuzzy_search_widget import add_fuzzy_search_tab_to_main_window', 
         'fuzzy_search_widget_expanded import integrate_expanded_fuzzy_search_widget'),
        
        # Aggiorna la chiamata di integrazione
        ('add_fuzzy_search_tab_to_main_window(self)', 
         'integrate_expanded_fuzzy_search_widget(self, self.db_manager)'),
        ('add_optimized_fuzzy_search_tab_to_main_window(self)',
         'integrate_expanded_fuzzy_search_widget(self, self.db_manager)'),
        ('add_enhanced_fuzzy_search_tab_to_main_window(self)',
         'integrate_expanded_fuzzy_search_widget(self, self.db_manager)'),
        
        # Aggiorna i nomi delle variabili
        ('FUZZY_SEARCH_AVAILABLE', 'EXPANDED_FUZZY_SEARCH_AVAILABLE'),
    ]
    
    original_content = content
    for old, new in updates:
        content = content.replace(old, new)
    
    # Se il widget ampliato non è ancora importato, aggiungilo
    if 'fuzzy_search_widget_expanded' not in content:
        # Trova dove aggiungere l'import
        lines = content.split('\n')
        import_added = False
        
        for i, line in enumerate(lines):
            if 'fuzzy_search_widget' in line and 'import' in line:
                # Sostituisci la riga di import esistente
                lines[i] = line.replace('fuzzy_search_widget', 'fuzzy_search_widget_expanded')
                lines[i] = lines[i].replace('add_fuzzy_search_tab_to_main_window', 'integrate_expanded_fuzzy_search_widget')
                import_added = True
                break
        
        if not import_added:
            # Aggiungi nuovo import dopo gli altri import
            for i, line in enumerate(lines):
                if line.startswith('from PyQt5') and 'import' in line:
                    lines.insert(i + 1, 'from fuzzy_search_widget_expanded import integrate_expanded_fuzzy_search_widget')
                    break
        
        content = '\n'.join(lines)
    
    # Salva le modifiche se ci sono state
    if content != original_content:
        with open('gui_main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("   ✅ gui_main.py aggiornato per versione ampliata")
        return True
    else:
        print("   ℹ️ gui_main.py già aggiornato o nessuna modifica necessaria")
        return True

def create_quick_test_script():
    """Crea uno script per testare rapidamente la versione ampliata."""
    test_script = '''
# ========================================================================
# TEST RAPIDO RICERCA FUZZY AMPLIATA
# File: test_fuzzy_expanded.py
# ========================================================================

"""
Script per testare rapidamente se la ricerca fuzzy ampliata funziona.
"""

import sys
import os

def test_imports():
    """Testa se tutti gli import funzionano."""
    print("🧪 TEST IMPORT")
    print("-" * 30)
    
    try:
        from catasto_gin_extension_expanded import extend_db_manager_with_gin_expanded
        print("   ✅ catasto_gin_extension_expanded")
    except ImportError as e:
        print(f"   ❌ catasto_gin_extension_expanded: {e}")
        return False
    
    try:
        from fuzzy_search_widget_expanded import ExpandedFuzzySearchWidget
        print("   ✅ fuzzy_search_widget_expanded")
    except ImportError as e:
        print(f"   ❌ fuzzy_search_widget_expanded: {e}")
        return False
    
    return True

def test_database_functions():
    """Testa se le funzioni database sono disponibili."""
    print("\\n🗄️ TEST FUNZIONI DATABASE")
    print("-" * 30)
    
    try:
        # Importa il database manager se disponibile
        sys.path.append('.')
        from catasto_db_manager import CatastoDBManager
        
        db_manager = CatastoDBManager()
        if not db_manager.test_connection():
            print("   ❌ Connessione database non disponibile")
            return False
        
        print("   ✅ Connessione database OK")
        
        # Estendi con funzionalità GIN
        from catasto_gin_extension_expanded import extend_db_manager_with_gin_expanded
        db_manager = extend_db_manager_with_gin_expanded(db_manager)
        
        # Testa verifica indici
        if hasattr(db_manager, 'verify_gin_indices'):
            result = db_manager.verify_gin_indices()
            if result.get('status') == 'OK':
                print(f"   ✅ Indici GIN: {result.get('gin_indices', 0)}/{result.get('total_indices', 0)}")
            else:
                print(f"   ⚠️ Indici GIN: {result.get('error', 'Errore sconosciuto')}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Test database: {e}")
        return False

def main():
    """Test completo del sistema."""
    print("=" * 50)
    print("TEST RAPIDO RICERCA FUZZY AMPLIATA")
    print("=" * 50)
    
    # Test import
    if not test_imports():
        print("\\n❌ TEST FALLITO: Problemi con gli import")
        print("SOLUZIONE: Verifica che i file artifacts siano stati salvati correttamente")
        return
    
    # Test database
    if not test_database_functions():
        print("\\n⚠️ TEST PARZIALE: Database non disponibile o non configurato")
        print("NOTA: Questo è normale se il database non è ancora stato configurato")
    else:
        print("\\n✅ TEST COMPLETO: Tutto funziona correttamente!")
    
    print("\\n🚀 PROSSIMI PASSI:")
    print("1. Avvia l'applicazione: python gui_main.py")
    print("2. Cerca il tab 'Ricerca Avanzata' (dovrebbe essere presente)")
    print("3. Testa la ricerca con termini come: terra, vendita, notaio")
    print("4. Verifica che ci siano più tab nei risultati (Immobili, Variazioni, ecc.)")

if __name__ == "__main__":
    main()
'''
    
    with open('test_fuzzy_expanded.py', 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print("   ✅ Creato test_fuzzy_expanded.py")

def main():
    """Funzione principale di aggiornamento."""
    print("=" * 70)
    print("AGGIORNAMENTO RICERCA FUZZY → VERSIONE AMPLIATA")
    print("=" * 70)
    
    # 1. Analisi situazione
    status = check_current_situation()
    
    # 2. Verifica che i nuovi file siano disponibili
    print("\n📋 VERIFICA NUOVI FILE")
    print("-" * 50)
    
    required_new_files = [
        'catasto_gin_extension_expanded.py',
        'fuzzy_search_widget_expanded.py',
        'expand_fuzzy_search.sql'
    ]
    
    missing_files = []
    for file in required_new_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file}")
            missing_files.append(file)
    
    if missing_files:
        print("\n❌ AGGIORNAMENTO IMPOSSIBILE")
        print("File mancanti. SOLUZIONI:")
        print("1. Salva gli artifacts di Claude come file:")
        for file in missing_files:
            print(f"   - {file}")
        print("2. Riprova dopo aver salvato tutti i file")
        return False
    
    # 3. Backup
    print("\n💾 BACKUP FILES")
    print("-" * 50)
    backups = backup_current_files()
    
    # 4. Verifica database
    if not verify_database_prerequisites():
        print("\n⚠️ ATTENZIONE: Database non ancora preparato")
        print("PRIMA esegui in PostgreSQL/pgAdmin: \\i expand_fuzzy_search.sql")
    
    # 5. Aggiorna integrazione GUI
    if update_gui_integration():
        print("\n🔧 AGGIORNAMENTO GUI COMPLETATO")
    else:
        print("\n❌ ERRORE AGGIORNAMENTO GUI")
        return False
    
    # 6. Crea script di test
    create_quick_test_script()
    
    # 7. Riepilogo finale
    print("\n" + "=" * 70)
    print("✅ AGGIORNAMENTO COMPLETATO!")
    print("=" * 70)
    
    print("\n🎯 COSA È CAMBIATO:")
    print("• Widget ricerca ora supporta 6 tipi di entità (era solo 2)")
    print("• Nuove tab: Immobili, Variazioni, Contratti, Partite")
    print("• Ricerca unificata con risultati raggruppati")
    print("• Export avanzato in CSV/JSON")
    print("• Dettagli completi per ogni entità")
    
    print("\n🚀 AZIONI IMMEDIATE:")
    print("1. IMPORTANTE: Esegui in PostgreSQL se non già fatto:")
    print("   \\i expand_fuzzy_search.sql")
    print("2. Testa il sistema:")
    print("   python test_fuzzy_expanded.py")
    print("3. Avvia l'applicazione:")
    print("   python gui_main.py")
    print("4. Nel tab 'Ricerca Avanzata' ora dovresti vedere:")
    print("   - Dropdown per tipo ricerca (Unificata, Solo Immobili, ecc.)")
    print("   - 7 tab nei risultati invece di 2")
    print("   - Pulsante Export")
    
    print("\n📝 BACKUP CREATI:")
    for backup in backups:
        print(f"   • {backup}")
    
    return True

if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n🎉 Aggiornamento completato alle {datetime.now().strftime('%H:%M:%S')}")
        print("Il tuo sistema ora ha la ricerca fuzzy ampliata!")
    else:
        print(f"\n💥 Aggiornamento fallito alle {datetime.now().strftime('%H:%M:%S')}")
        print("Controlla i messaggi sopra e riprova.")
    
    input("\nPremi INVIO per chiudere...")
