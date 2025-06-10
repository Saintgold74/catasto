# ========================================================================
# FIX ERRORE SINTASSI GUI_MAIN.PY
# File: fix_syntax_error.py
# ========================================================================

"""
Script per riparare l'errore di sintassi in gui_main.py
causato dall'integrazione della ricerca fuzzy.
"""

import os
import shutil
from datetime import datetime

def find_and_restore_backup():
    """Trova e ripristina il backup più recente."""
    
    print("🔍 RICERCA BACKUP GUI_MAIN.PY")
    print("-" * 40)
    
    # Cerca tutti i backup
    backup_files = []
    for file in os.listdir('.'):
        if file.startswith('gui_main') and 'backup' in file and file.endswith('.py'):
            backup_files.append(file)
    
    if not backup_files:
        print("❌ Nessun backup trovato")
        return None
    
    # Ordina per data (il più recente per ultimo)
    backup_files.sort()
    latest_backup = backup_files[-1]
    
    print(f"📁 Backup trovati: {len(backup_files)}")
    for backup in backup_files:
        print(f"   • {backup}")
    
    print(f"\n✅ Backup più recente: {latest_backup}")
    
    # Ripristina
    try:
        shutil.copy2(latest_backup, 'gui_main.py')
        print(f"✅ gui_main.py ripristinato da {latest_backup}")
        return latest_backup
    except Exception as e:
        print(f"❌ Errore ripristino: {e}")
        return None

def fix_syntax_error_manually():
    """Tenta di riparare l'errore di sintassi manualmente."""
    
    print("\n🔧 RIPARAZIONE MANUALE ERRORE SINTASSI")
    print("-" * 40)
    
    if not os.path.exists('gui_main.py'):
        print("❌ File gui_main.py non trovato")
        return False
    
    # Backup di sicurezza
    backup_name = f"gui_main_before_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    shutil.copy2('gui_main.py', backup_name)
    print(f"💾 Backup creato: {backup_name}")
    
    try:
        with open('gui_main.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"📄 File letto: {len(lines)} righe")
        
        # Cerca e ripara errori comuni
        fixed = False
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Errore: riga incompleta con fuzzy_widget =
            if 'fuzzy_widget =' in line and line.strip().endswith('='):
                print(f"🔍 Trovato errore alla riga {line_num}: {line.strip()}")
                
                # Rimuovi la riga problematica
                lines[i] = ''
                fixed = True
                print(f"✅ Riga {line_num} rimossa")
            
            # Errore: integrazione fuzzy mal formattata
            elif 'integrate_expanded_fuzzy_search_widget' in line:
                # Se la riga è incompleta o mal formattata
                if not line.strip().endswith(')') and 'try:' not in line:
                    print(f"🔍 Riga integrazione problematica: {line_num}")
                    
                    # Sostituisci con versione corretta
                    indent = len(line) - len(line.lstrip())
                    correct_integration = ' ' * indent + '''# Integrazione ricerca fuzzy ampliata
        try:
            from fuzzy_search_widget_expanded import ExpandedFuzzySearchWidget
            fuzzy_widget = ExpandedFuzzySearchWidget(self.db_manager)
            fuzzy_tab_index = self.tabs.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
            print("✅ Tab ricerca fuzzy ampliato aggiunto")
        except Exception as e:
            print(f"⚠️ Errore ricerca fuzzy: {e}")
'''
                    
                    lines[i] = correct_integration + '\n'
                    fixed = True
                    print(f"✅ Riga {line_num} corretta")
        
        if fixed:
            # Salva il file riparato
            with open('gui_main.py', 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print("✅ File riparato e salvato")
            return True
        else:
            print("⚠️ Nessun errore evidente trovato nel codice")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante la riparazione: {e}")
        
        # Ripristina il backup
        if os.path.exists(backup_name):
            shutil.copy2(backup_name, 'gui_main.py')
            print(f"🔄 File ripristinato da {backup_name}")
        
        return False

def verify_syntax():
    """Verifica che la sintassi sia corretta."""
    
    print("\n✅ VERIFICA SINTASSI")
    print("-" * 40)
    
    try:
        import ast
        
        with open('gui_main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tenta di parsare il file
        ast.parse(content)
        print("✅ Sintassi corretta!")
        return True
        
    except SyntaxError as e:
        print(f"❌ Errore sintassi alla riga {e.lineno}: {e.msg}")
        print(f"   Testo: {e.text.strip() if e.text else 'N/A'}")
        return False
    except Exception as e:
        print(f"❌ Errore verifica: {e}")
        return False

def create_clean_integration():
    """Crea un'integrazione pulita se tutto il resto fallisce."""
    
    integration_code = '''
        # === INTEGRAZIONE RICERCA FUZZY AMPLIATA - VERSIONE PULITA ===
        try:
            from fuzzy_search_widget_expanded import ExpandedFuzzySearchWidget
            
            # Verifica che il db_manager sia disponibile
            if hasattr(self, 'db_manager') and self.db_manager:
                # Crea il widget
                fuzzy_widget = ExpandedFuzzySearchWidget(self.db_manager)
                
                # Aggiungi il tab
                if hasattr(self, 'tabs'):
                    fuzzy_tab_index = self.tabs.addTab(fuzzy_widget, "🔍 Ricerca Avanzata")
                    self.logger.info(f"Tab Ricerca Fuzzy aggiunto all'indice {fuzzy_tab_index}")
                    print("✅ Tab ricerca fuzzy ampliato integrato con successo")
                else:
                    print("⚠️ Widget tabs non trovato")
            else:
                print("⚠️ Database manager non disponibile")
                
        except ImportError as e:
            print(f"⚠️ Modulo ricerca fuzzy non disponibile: {e}")
        except Exception as e:
            self.logger.error(f"Errore integrazione ricerca fuzzy: {e}")
            print(f"⚠️ Errore integrazione ricerca fuzzy: {e}")
        # === FINE INTEGRAZIONE RICERCA FUZZY ===
'''
    
    with open('clean_fuzzy_integration.txt', 'w', encoding='utf-8') as f:
        f.write(integration_code)
    
    print("📝 Codice integrazione pulito salvato in: clean_fuzzy_integration.txt")
    print("   Puoi copiarlo manualmente nel file gui_main.py se necessario")

def main():
    """Funzione principale di riparazione."""
    
    print("=" * 60)
    print("🚨 FIX ERRORE SINTASSI GUI_MAIN.PY")
    print("=" * 60)
    
    # 1. Tenta ripristino da backup
    backup_restored = find_and_restore_backup()
    
    if backup_restored:
        print("\n✅ TENTATIVO 1: RIPRISTINO DA BACKUP")
        if verify_syntax():
            print("🎉 SUCCESSO! Il file è stato riparato")
            print("Ora puoi riavviare l'applicazione: python gui_main.py")
            return True
        else:
            print("⚠️ Il backup ha ancora errori, procedo con riparazione manuale")
    
    # 2. Tenta riparazione manuale
    print("\n🔧 TENTATIVO 2: RIPARAZIONE MANUALE")
    if fix_syntax_error_manually():
        if verify_syntax():
            print("🎉 SUCCESSO! Il file è stato riparato manualmente")
            print("Ora puoi riavviare l'applicazione: python gui_main.py")
            return True
    
    # 3. Crea codice di integrazione pulito
    print("\n📝 TENTATIVO 3: CODICE INTEGRAZIONE PULITO")
    create_clean_integration()
    
    print("\n" + "=" * 60)
    print("🛠️ ISTRUZIONI FINALI")
    print("=" * 60)
    
    print("\n❌ RIPARAZIONE AUTOMATICA FALLITA")
    print("\n🔧 RIPARAZIONE MANUALE RICHIESTA:")
    print("1. Apri gui_main.py in un editor di testo")
    print("2. Cerca la riga con 'fuzzy_widget =' (intorno alla riga 565)")
    print("3. Rimuovi quella riga e quelle problematiche intorno")
    print("4. Copia il codice da clean_fuzzy_integration.txt")
    print("5. Incollalo nel punto appropriato (dopo setup_tabs)")
    
    print("\n📞 ALTERNATIVE:")
    print("1. Usa un backup precedente funzionante")
    print("2. Ripristina gui_main.py da Git se disponibile")
    print("3. Commenta l'integrazione fuzzy per ora")
    
    return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n💡 SUGGERIMENTO RAPIDO:")
        print("Se vuoi tornare alla versione funzionante senza ricerca fuzzy,")
        print("cerca e commenta (aggiungi # all'inizio) tutte le righe che")
        print("contengono 'fuzzy' in gui_main.py")
    
    input("\nPremi INVIO per chiudere...")
