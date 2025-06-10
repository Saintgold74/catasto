# ========================================================================
# SCRIPT DI INTEGRAZIONE RICERCA FUZZY AMPLIATA - VERSIONE CORRETTA
# File: integrate_fuzzy_expanded_fixed.py
# ========================================================================

"""
Script corretto per integrare la ricerca fuzzy ampliata nella GUI esistente.
Da eseguire dopo aver implementato gli script database.
"""

import sys
import os
import shutil
from datetime import datetime

def backup_file(filepath):
    """Crea un backup di un file con timestamp."""
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}_backup_{timestamp}"
        try:
            shutil.copy2(filepath, backup_path)
            print(f"   💾 Backup creato: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"   ⚠️ Errore backup: {e}")
            return None
    else:
        print(f"   ⚠️ File non trovato: {filepath}")
        return None

def integrate_into_gui_main():
    """Integra il widget nella GUI principale."""
    
    print("🔧 Integrazione nel file gui_main.py...")
    
    # Verifica file necessari
    required_files = [
        'catasto_gin_extension_expanded.py',
        'fuzzy_search_widget_expanded.py',
        'gui_main.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ File mancanti:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ Tutti i file necessari sono presenti")
    
    # Leggi il file GUI principale
    try:
        with open('gui_main.py', 'r', encoding='utf-8') as f:
            gui_content = f.read()
        print("✅ File gui_main.py letto correttamente")
    except Exception as e:
        print(f"❌ Errore lettura gui_main.py: {e}")
        return False
    
    # Controlla se l'integrazione è già presente
    if 'fuzzy_search_widget_expanded' in gui_content:
        print("ℹ️ Integrazione già presente in gui_main.py")
        return True
    
    # Backup del file originale
    print("💾 Creazione backup...")
    backup_path = backup_file('gui_main.py')
    if not backup_path:
        print("⚠️ Impossibile creare backup, continuando comunque...")
    
    # Prepara le modifiche
    import_line = "from fuzzy_search_widget_expanded import integrate_expanded_fuzzy_search_widget"
    
    # Aggiunge import se non presente
    if import_line not in gui_content:
        print("📝 Aggiunta import...")
        
        # Trova una posizione adatta per l'import
        lines = gui_content.split('\n')
        import_inserted = False
        
        # Cerca dopo gli altri import di widget
        for i, line in enumerate(lines):
            if (line.startswith('from') and 'widget' in line.lower()) or \
               (line.startswith('import') and i > 5):
                lines.insert(i + 1, import_line)
                import_inserted = True
                print(f"   ✅ Import aggiunto alla riga {i + 2}")
                break
        
        if not import_inserted:
            # Aggiungi dopo la sezione import (cerca prima riga vuota dopo import)
            for i, line in enumerate(lines):
                if line.strip() == '' and i > 10:
                    lines.insert(i, import_line)
                    print(f"   ✅ Import aggiunto alla riga {i + 1}")
                    break
        
        gui_content = '\n'.join(lines)
    else:
        print("✅ Import già presente")
    
    # Aggiunge chiamata di integrazione
    integration_call = """
        # Integrazione ricerca fuzzy ampliata
        try:
            fuzzy_widget = integrate_expanded_fuzzy_search_widget(self, self.db_manager)
            print("✅ Ricerca fuzzy ampliata integrata con successo")
        except Exception as e:
            print(f"⚠️ Errore integrazione ricerca fuzzy: {e}")"""
    
    # Cerca dove inserire l'integrazione
    integration_added = False
    
    # Opzione 1: dopo self.setup_tabs()
    if 'self.setup_tabs()' in gui_content:
        print("📝 Aggiunta integrazione dopo setup_tabs()...")
        gui_content = gui_content.replace(
            'self.setup_tabs()',
            'self.setup_tabs()' + integration_call
        )
        integration_added = True
        print("   ✅ Integrazione aggiunta dopo setup_tabs()")
    
    # Opzione 2: alla fine del metodo setup_tabs se esiste
    elif 'def setup_tabs(' in gui_content and not integration_added:
        print("📝 Aggiunta integrazione alla fine di setup_tabs()...")
        lines = gui_content.split('\n')
        in_setup_tabs = False
        setup_tabs_indent = 0
        
        for i, line in enumerate(lines):
            if 'def setup_tabs(' in line:
                in_setup_tabs = True
                setup_tabs_indent = len(line) - len(line.lstrip())
                continue
            elif in_setup_tabs:
                # Se troviamo un'altra funzione o metodo con stesso o minor indent
                if line.strip() and (line.startswith('def ') or line.startswith('class ')):
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= setup_tabs_indent:
                        # Fine del metodo setup_tabs, inserisci qui
                        lines.insert(i, integration_call.strip())
                        integration_added = True
                        print(f"   ✅ Integrazione aggiunta alla riga {i + 1}")
                        break
        
        if integration_added:
            gui_content = '\n'.join(lines)
    
    # Opzione 3: alla fine del __init__ se setup_tabs non esiste
    if not integration_added and 'def __init__(' in gui_content:
        print("📝 Aggiunta integrazione alla fine di __init__()...")
        lines = gui_content.split('\n')
        in_init = False
        init_indent = 0
        
        for i, line in enumerate(lines):
            if 'def __init__(' in line:
                in_init = True
                init_indent = len(line) - len(line.lstrip())
                continue
            elif in_init:
                # Se troviamo un'altra funzione o metodo con stesso o minor indent
                if line.strip() and (line.startswith('def ') or line.startswith('class ')):
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= init_indent:
                        # Fine del metodo __init__, inserisci qui
                        lines.insert(i, integration_call.strip())
                        integration_added = True
                        print(f"   ✅ Integrazione aggiunta alla fine di __init__ (riga {i + 1})")
                        break
        
        if integration_added:
            gui_content = '\n'.join(lines)
    
    # Se non è stato possibile inserire automaticamente
    if not integration_added:
        print("⚠️ Impossibile inserire automaticamente l'integrazione")
        print("🔧 Integrazione manuale richiesta:")
        print("   Aggiungi questo codice alla fine di setup_tabs() o __init__():")
        print("   " + integration_call.strip().replace('\n', '\n   '))
        
        # Prova a inserire alla fine del file prima dell'ultima riga
        lines = gui_content.split('\n')
        lines.insert(-1, integration_call.strip())
        gui_content = '\n'.join(lines)
        print("   ✅ Codice aggiunto alla fine del file")
    
    # Salva il file modificato
    try:
        with open('gui_main.py', 'w', encoding='utf-8') as f:
            f.write(gui_content)
        print("✅ gui_main.py aggiornato con successo")
        return True
    except Exception as e:
        print(f"❌ Errore scrittura gui_main.py: {e}")
        
        # Ripristina backup se disponibile
        if backup_path and os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, 'gui_main.py')
                print(f"🔄 File ripristinato da backup: {backup_path}")
            except Exception as restore_error:
                print(f"❌ Errore ripristino backup: {restore_error}")
        
        return False

def verify_integration():
    """Verifica che l'integrazione sia stata completata correttamente."""
    print("\n🔍 Verifica integrazione...")
    
    try:
        with open('gui_main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = {
            'Import presente': 'fuzzy_search_widget_expanded' in content,
            'Funzione integrate presente': 'integrate_expanded_fuzzy_search_widget' in content,
            'Try-except presente': 'try:' in content and 'fuzzy_widget' in content
        }
        
        for check, result in checks.items():
            status = "✅" if result else "❌"
            print(f"   {status} {check}")
        
        return all(checks.values())
        
    except Exception as e:
        print(f"❌ Errore verifica: {e}")
        return False

def main():
    """Funzione principale di integrazione."""
    print("=" * 60)
    print("INTEGRAZIONE RICERCA FUZZY AMPLIATA - VERSIONE CORRETTA")
    print("=" * 60)
    
    print("\n1. Verifica prerequisiti...")
    
    # Verifica script SQL eseguito
    if not os.path.exists('expand_fuzzy_search.sql'):
        print("⚠️ File expand_fuzzy_search.sql non trovato")
        print("   Se lo script SQL è già stato eseguito, puoi continuare")
    else:
        print("✅ Script SQL trovato")
    
    # Verifica file Python
    required_files = [
        'catasto_gin_extension_expanded.py',
        'fuzzy_search_widget_expanded.py'
    ]
    
    missing_artifacts = []
    for file in required_files:
        if not os.path.exists(file):
            missing_artifacts.append(file)
    
    if missing_artifacts:
        print("❌ File artifacts mancanti:")
        for file in missing_artifacts:
            print(f"   - {file}")
        print("\n🔧 SOLUZIONE:")
        print("   Copia i contenuti degli artifacts di Claude nei file corrispondenti")
        return False
    
    print("✅ Tutti gli artifacts sono presenti")
    
    print("\n2. Integrazione GUI...")
    if integrate_into_gui_main():
        print("\n3. Verifica finale...")
        if verify_integration():
            print("\n" + "=" * 60)
            print("✅ INTEGRAZIONE COMPLETATA CON SUCCESSO!")
            print("=" * 60)
            print("\n🚀 PROSSIMI PASSI:")
            print("1. Riavvia l'applicazione: python gui_main.py")
            print("2. Cerca il nuovo tab '🔍 Ricerca Avanzata'")
            print("3. Testa la ricerca fuzzy ampliata")
            
            print("\n🎯 FUNZIONALITÀ DISPONIBILI:")
            print("• Ricerca in immobili (natura, classificazione, consistenza)")
            print("• Ricerca in variazioni (tipo, nominativo, numero riferimento)")
            print("• Ricerca in contratti (tipo, notaio, repertorio, note)")
            print("• Ricerca in partite (numero, suffisso)")
            print("• Ricerca unificata con risultati raggruppati")
            print("• Export risultati in CSV/JSON")
            print("• Dettagli completi per ogni entità")
            
            print("\n📝 NOTE:")
            print("• Assicurati di aver eseguito lo script SQL expand_fuzzy_search.sql")
            print("• Se ci sono errori, controlla i backup creati automaticamente")
            print("• La ricerca richiede almeno 3 caratteri")
            
            return True
        else:
            print("\n⚠️ Integrazione completata ma con possibili problemi")
            print("   Controlla manualmente il file gui_main.py")
            return False
    else:
        print("\n❌ Integrazione fallita")
        print("   Controlla i backup e riprova")
        return False

if __name__ == "__main__":
    try:
        success = main()
        
        if success:
            print(f"\n🎉 Integrazione completata alle {datetime.now().strftime('%H:%M:%S')}")
        else:
            print(f"\n💥 Integrazione fallita alle {datetime.now().strftime('%H:%M:%S')}")
            print("\n🔧 OPZIONI DI RECUPERO:")
            print("1. Controlla i file backup creati (gui_main.py_backup_*)")
            print("2. Verifica che tutti gli artifacts siano stati salvati come file")
            print("3. Controlla che lo script SQL sia stato eseguito correttamente")
        
    except Exception as e:
        print(f"\n💥 ERRORE CRITICO: {str(e)}")
        print("\n🆘 AZIONI IMMEDIATE:")
        print("1. Ripristina gui_main.py da backup se disponibile")
        print("2. Verifica che tutti i file artifacts esistano")
        print("3. Riprova con lo script corretto")
    
    input("\nPremi INVIO per chiudere...")