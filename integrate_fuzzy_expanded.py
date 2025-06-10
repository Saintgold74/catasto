
# ========================================================================
# SCRIPT DI INTEGRAZIONE RICERCA FUZZY AMPLIATA
# File: integrate_fuzzy_expanded.py
# ========================================================================

"""
Script per integrare la ricerca fuzzy ampliata nella GUI esistente.
Da eseguire dopo aver implementato gli script database.
"""

import sys
import os

def integrate_into_gui_main():
    """Integra il widget nella GUI principale."""
    
    # Verifica file necessari
    required_files = [
        'catasto_gin_extension_expanded.py',
        'fuzzy_search_widget_expanded.py',
        'gui_main.py'
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ File mancante: {file}")
            return False
    
    # Leggi il file GUI principale
    try:
        with open('gui_main.py', 'r', encoding='utf-8') as f:
            gui_content = f.read()
    except Exception as e:
        print(f"❌ Errore lettura gui_main.py: {e}")
        return False
    
    # Controlla se l'integrazione è già presente
    if 'fuzzy_search_widget_expanded' in gui_content:
        print("ℹ️ Integrazione già presente in gui_main.py")
        return True
    
    # Backup del file originale
    backup_file('gui_main.py')
    
    # Aggiungi import
    import_line = "from fuzzy_search_widget_expanded import integrate_expanded_fuzzy_search_widget"
    
    if import_line not in gui_content:
        # Trova una posizione adatta per l'import
        lines = gui_content.split('\n')
        import_inserted = False
        
        for i, line in enumerate(lines):
            if line.startswith('from') and 'widget' in line:
                lines.insert(i + 1, import_line)
                import_inserted = True
                break
        
        if not import_inserted:
            # Aggiungi dopo gli import standard
            for i, line in enumerate(lines):
                if line.strip() == '' and i > 5:
                    lines.insert(i, import_line)
                    break
        
        gui_content = '\n'.join(lines)
    
    # Aggiungi chiamata di integrazione
    integration_call = """
        # Integrazione ricerca fuzzy ampliata
        try:
            fuzzy_widget = integrate_expanded_fuzzy_search_widget(self, self.db_manager)
            print("✅ Ricerca fuzzy ampliata integrata con successo")
        except Exception as e:
            print(f"⚠️ Errore integrazione ricerca fuzzy: {e}")
"""
    
    # Trova un punto adatto per l'integrazione (es. dopo setup dei tab)
    if 'self.setup_tabs()' in gui_content:
        gui_content = gui_content.replace(
            'self.setup_tabs()',
            'self.setup_tabs()' + integration_call
        )
    elif 'def setup_tabs(' in gui_content:
        # Aggiungi alla fine del metodo setup_tabs
        lines = gui_content.split('\n')
        in_setup_tabs = False
        indent_level = 0
        
        for i, line in enumerate(lines):
            if 'def setup_tabs(' in line:
                in_setup_tabs = True
                indent_level = len(line) - len(line.lstrip())
            elif in_setup_tabs and line.strip() and len(line) - len(line.lstrip()) <= indent_level and 'def ' in line:
                # Fine del metodo setup_tabs
                lines.insert(i, integration_call.strip())
                break
        
        gui_content = '\n'.join(lines)
    
    # Salva il file modificato
    try:
        with open('gui_main.py', 'w', encoding='utf-8') as f:
            f.write(gui_content)
        print("✅ gui_main.py aggiornato con successo")
        return True
    except Exception as e:
        print(f"❌ Errore scrittura gui_main.py: {e}")
        return False

def main():
    """Funzione principale di integrazione."""
    print("=" * 60)
    print("INTEGRAZIONE RICERCA FUZZY AMPLIATA")
    print("=" * 60)
    
    print("\n1. Verifica prerequisiti...")
    if not os.path.exists('expand_fuzzy_search.sql'):
        print("❌ Prima esegui gli script SQL!")
        print("   Apri pgAdmin ed esegui: expand_fuzzy_search.sql")
        return False
    
    print("\n2. Integrazione GUI...")
    if integrate_into_gui_main():
        print("\n" + "=" * 60)
        print("✅ INTEGRAZIONE COMPLETATA!")
        print("=" * 60)
        print("\nPROSSIMI PASSI:")
        print("1. Riavvia l'applicazione: python gui_main.py")
        print("2. Cerca il nuovo tab '🔍 Ricerca Avanzata'")
        print("3. Testa la ricerca fuzzy ampliata")
        print("\nFUNZIONALITÀ DISPONIBILI:")
        print("• Ricerca in immobili (natura, classificazione, consistenza)")
        print("• Ricerca in variazioni (tipo, nominativo, numero riferimento)")
        print("• Ricerca in contratti (tipo, notaio, repertorio, note)")
        print("• Ricerca in partite (numero, suffisso)")
        print("• Ricerca unificata con risultati raggruppati")
        print("• Export risultati in CSV/JSON")
        print("• Dettagli completi per ogni entità")
        return True
    else:
        print("❌ Integrazione fallita")
        return False

if __name__ == "__main__":
    main()
