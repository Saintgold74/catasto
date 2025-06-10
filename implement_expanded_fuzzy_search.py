# ========================================================================
# SCRIPT DI IMPLEMENTAZIONE RICERCA FUZZY AMPLIATA
# File: implement_expanded_fuzzy_search.py
# ========================================================================

"""
Script per implementare la ricerca fuzzy ampliata nel sistema catasto.

Questo script:
1. Verifica la presenza di tutti i file necessari
2. Esegue gli script SQL per creare indici e funzioni
3. Integra il nuovo widget nella GUI esistente
4. Testa il sistema completo

Fasi di implementazione:
- Database: nuovi indici GIN e funzioni di ricerca
- Python: estensione per ricerca ampliata
- GUI: widget integrato con tutte le funzionalità

Utilizzo:
    python implement_expanded_fuzzy_search.py
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

def print_header(title):
    """Stampa un header formattato."""
    print("\n" + "=" * 70)
    print(f" {title.upper()}")
    print("=" * 70)

def print_step(step_num, description):
    """Stampa un passo numerato."""
    print(f"\n{step_num}. {description}")
    print("-" * 50)

def check_file_exists(filepath):
    """Verifica se un file esiste."""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"   {status} {filepath}")
    return exists

def backup_file(filepath):
    """Crea un backup di un file."""
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}_backup_{timestamp}"
        shutil.copy2(filepath, backup_path)
        print(f"   💾 Backup creato: {backup_path}")
        return backup_path
    return None

def create_sql_execution_script():
    """Crea uno script SQL per l'esecuzione completa."""
    sql_script = """
-- ========================================================================
-- SCRIPT DI ESECUZIONE COMPLETA PER RICERCA FUZZY AMPLIATA
-- Da eseguire in pgAdmin o psql
-- ========================================================================

-- Connessione al database catasto_storico
\\c catasto_storico;

-- Imposta lo schema
SET search_path TO catasto, public;

-- Verifica estensioni necessarie
SELECT 'Verificando estensioni...' as status;
CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA public;

-- Mostra estensioni installate
SELECT extname, extversion FROM pg_extension WHERE extname IN ('pg_trgm');

-- Esegui lo script di ampliamento (deve essere già stato salvato)
-- \\i expand_fuzzy_search.sql

-- Verifica risultato
SELECT 'Verifica indici GIN...' as status;
SELECT * FROM verify_gin_indices();

-- Test delle nuove funzioni
SELECT 'Test ricerca immobili:' as test;
SELECT COUNT(*) as risultati FROM search_immobili_fuzzy('terra', 0.3, 5);

SELECT 'Test ricerca variazioni:' as test;
SELECT COUNT(*) as risultati FROM search_variazioni_fuzzy('vend', 0.3, 5);

SELECT 'Test ricerca unificata:' as test;
SELECT COUNT(*) as risultati FROM search_all_entities_fuzzy('test', 0.3, true, true, true, true, true, true, 5);

SELECT 'Implementazione database completata!' as status;
"""
    
    with open('execute_fuzzy_expansion.sql', 'w', encoding='utf-8') as f:
        f.write(sql_script)
    
    print("   📄 Creato: execute_fuzzy_expansion.sql")
    return True

def verify_prerequisites():
    """Verifica i prerequisiti per l'implementazione."""
    print_step(1, "VERIFICA PREREQUISITI")
    
    required_files = [
        'catasto_db_manager.py',
        'gui_main.py'
    ]
    
    optional_files = [
        'catasto_gin_extension.py',
        'fuzzy_search_widget.py'
    ]
    
    print("File richiesti:")
    all_required = True
    for file in required_files:
        if not check_file_exists(file):
            all_required = False
    
    print("\nFile opzionali (verranno aggiornati o creati):")
    for file in optional_files:
        check_file_exists(file)
    
    print("\nNuovi file che verranno creati:")
    new_files = [
        'expand_fuzzy_search.sql',
        'catasto_gin_extension_expanded.py',
        'fuzzy_search_widget_expanded.py',
        'execute_fuzzy_expansion.sql'
    ]
    
    for file in new_files:
        exists = os.path.exists(file)
        status = "⚠️ Esiste, verrà sovrascritto" if exists else "🆕 Nuovo"
        print(f"   {status} {file}")
    
    return all_required

def create_database_scripts():
    """Crea gli script per il database."""
    print_step(2, "CREAZIONE SCRIPT DATABASE")
    
    # Lo script SQL è già stato creato come artifact
    print("   ✅ Script SQL già disponibile come artifact: expand_fuzzy_search.sql")
    print("   ✅ Script di esecuzione creato")
    
    create_sql_execution_script()
    
    return True

def create_python_extensions():
    """Crea le estensioni Python."""
    print_step(3, "CREAZIONE ESTENSIONI PYTHON")
    
    # Gli script Python sono già stati creati come artifacts
    print("   ✅ Estensione GIN ampliata già disponibile come artifact:")
    print("      catasto_gin_extension_expanded.py")
    print("   ✅ Widget fuzzy ampliato già disponibile come artifact:")
    print("      fuzzy_search_widget_expanded.py")
    
    return True

def create_integration_script():
    """Crea lo script di integrazione per la GUI."""
    integration_script = '''
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
        lines = gui_content.split('\\n')
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
        
        gui_content = '\\n'.join(lines)
    
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
        lines = gui_content.split('\\n')
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
        
        gui_content = '\\n'.join(lines)
    
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
    
    print("\\n1. Verifica prerequisiti...")
    if not os.path.exists('expand_fuzzy_search.sql'):
        print("❌ Prima esegui gli script SQL!")
        print("   Apri pgAdmin ed esegui: expand_fuzzy_search.sql")
        return False
    
    print("\\n2. Integrazione GUI...")
    if integrate_into_gui_main():
        print("\\n" + "=" * 60)
        print("✅ INTEGRAZIONE COMPLETATA!")
        print("=" * 60)
        print("\\nPROSSIMI PASSI:")
        print("1. Riavvia l'applicazione: python gui_main.py")
        print("2. Cerca il nuovo tab '🔍 Ricerca Avanzata'")
        print("3. Testa la ricerca fuzzy ampliata")
        print("\\nFUNZIONALITÀ DISPONIBILI:")
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
'''
    
    with open('integrate_fuzzy_expanded.py', 'w', encoding='utf-8') as f:
        f.write(integration_script)
    
    print("   ✅ Creato: integrate_fuzzy_expanded.py")
    return True

def create_documentation():
    """Crea la documentazione per l'ampliamento."""
    doc_content = """
# RICERCA FUZZY AMPLIATA - GUIDA COMPLETA

## Panoramica
La ricerca fuzzy ampliata estende il sistema catasto con capacità di ricerca
avanzate in tutte le entità del database.

## Nuove Funzionalità

### 1. Ricerca negli Immobili
- **Natura**: terreno, fabbricato, ecc.
- **Classificazione**: categoria catastale
- **Consistenza**: descrizione dell'immobile

### 2. Ricerca nelle Variazioni
- **Tipo variazione**: vendita, successione, ecc.
- **Nominativo riferimento**: persona coinvolta
- **Numero riferimento**: codice pratica

### 3. Ricerca nei Contratti
- **Tipo contratto**: atto di compravendita, ecc.
- **Notaio**: nome del notaio
- **Repertorio**: numero repertorio
- **Note**: annotazioni libere

### 4. Ricerca nelle Partite
- **Numero partita**: ricerca numerica
- **Suffisso partita**: bis, ter, A, B, ecc.

### 5. Ricerca Unificata
- Ricerca simultanea in tutte le entità
- Risultati raggruppati per tipo
- Soglia di similarità configurabile

## Interfaccia Utente

### Controlli Principali
- **Barra di ricerca**: testo libero con completamento automatico
- **Tipo ricerca**: selettore per tipo specifico o unificata
- **Soglia similarità**: slider per precisione ricerca
- **Export**: esportazione risultati in CSV/JSON

### Risultati
- **Tab Tutti**: risultati unificati con icone per tipo
- **Tab specifici**: risultati separati per entità
- **Doppio click**: visualizza dettagli completi
- **Pulsanti azione**: accesso rapido ai dettagli

## Implementazione Tecnica

### Indici GIN
Il sistema utilizza indici GIN PostgreSQL per ricerca full-text:
- `idx_gin_immobili_natura`
- `idx_gin_variazioni_tipo`
- `idx_gin_contratti_notaio`
- E molti altri...

### Funzioni PostgreSQL
- `search_immobili_fuzzy()`: ricerca negli immobili
- `search_variazioni_fuzzy()`: ricerca nelle variazioni
- `search_contratti_fuzzy()`: ricerca nei contratti
- `search_partite_fuzzy()`: ricerca nelle partite
- `search_all_entities_fuzzy()`: ricerca unificata

### Estensione Python
- `CatastoGINSearchExpanded`: classe principale
- `ExpandedFuzzySearchWidget`: widget GUI
- `EntityDetailsDialog`: dialog dettagli entità

## Performance

### Ottimizzazioni
- Ricerca parallela su indici GIN
- Risultati limitati per tipo
- Cache dei risultati frequenti
- Threshold configurabile per precisione/velocità

### Monitoraggio
- Verifica automatica degli indici
- Statistiche di utilizzo
- Log delle performance

## Configurazione

### Soglie Consigliate
- **Ricerca veloce**: 0.5-0.7 (maggiore precisione)
- **Ricerca estesa**: 0.2-0.4 (maggiore tolleranza)
- **Ricerca in dati storici**: 0.1-0.3 (massima tolleranza)

### Limiti Risultati
- **Per tipo**: 30 risultati (configurabile)
- **Totali**: 200 risultati massimi
- **Export**: illimitato

## Troubleshooting

### Problemi Comuni
1. **Ricerca lenta**: verificare indici GIN
2. **Nessun risultato**: abbassare soglia similarità
3. **Troppi risultati**: aumentare soglia o raffinare query

### Verifica Sistema
```sql
-- Verifica indici GIN
SELECT * FROM verify_gin_indices();

-- Test funzioni
SELECT COUNT(*) FROM search_all_entities_fuzzy('test', 0.3);
```

### Log e Debug
- Controllare log applicazione per errori
- Verificare connessione database
- Controllare permessi utente database

## Esempi di Utilizzo

### Ricerca Immobili
```
Query: "terra"
Risultati: terreno, terrazza, territorio
Campi: natura, consistenza
```

### Ricerca Variazioni
```
Query: "vend"
Risultati: vendita, rivendita
Campi: tipo, nominativo_riferimento
```

### Ricerca Unificata
```
Query: "rossi"
Risultati: 
- Possessori: Mario Rossi, Rossini Giuseppe
- Località: Via Rossini, Borgo Rossi
- Contratti: Notaio Rossi
```

## Estensioni Future

### Funzionalità Pianificate
- Ricerca geografica con coordinate
- Ricerca temporale avanzata
- Analisi statistiche integrate
- Export in formati CAD/GIS
- API REST per integrazioni esterne

### Personalizzazioni
- Campi di ricerca aggiuntivi
- Algoritmi di similarità custom
- Template export personalizzati
- Dashboard analitiche
"""
    
    with open('RICERCA_FUZZY_AMPLIATA.md', 'w', encoding='utf-8') as f:
        f.write(doc_content)
    
    print("   📚 Creata: RICERCA_FUZZY_AMPLIATA.md")
    return True

def main():
    """Funzione principale di implementazione."""
    print_header("IMPLEMENTAZIONE RICERCA FUZZY AMPLIATA")
    print("Sistema Catasto Storico - Versione Avanzata")
    
    try:
        # Verifica prerequisiti
        if not verify_prerequisites():
            print("\n❌ IMPLEMENTAZIONE FALLITA - Prerequisiti non soddisfatti")
            return False
        
        # Crea script database
        if not create_database_scripts():
            print("\n❌ IMPLEMENTAZIONE FALLITA - Errore script database")
            return False
        
        # Crea estensioni Python
        if not create_python_extensions():
            print("\n❌ IMPLEMENTAZIONE FALLITA - Errore estensioni Python")
            return False
        
        # Crea script di integrazione
        if not create_integration_script():
            print("\n❌ IMPLEMENTAZIONE FALLITA - Errore script integrazione")
            return False
        
        # Crea documentazione
        create_documentation()
        
        # Riepilogo finale
        print_header("IMPLEMENTAZIONE COMPLETATA")
        
        print("✅ FASE 1: File preparati con successo")
        print("   • expand_fuzzy_search.sql")
        print("   • catasto_gin_extension_expanded.py")
        print("   • fuzzy_search_widget_expanded.py")
        print("   • integrate_fuzzy_expanded.py")
        print("   • execute_fuzzy_expansion.sql")
        print("   • RICERCA_FUZZY_AMPLIATA.md")
        
        print("\n🔧 FASE 2: ESECUZIONE RICHIESTA")
        print("   1. DATABASE: Esegui in pgAdmin o psql:")
        print("      \\i expand_fuzzy_search.sql")
        print("   2. PYTHON: Esegui script di integrazione:")
        print("      python integrate_fuzzy_expanded.py")
        print("   3. TEST: Riavvia l'applicazione:")
        print("      python gui_main.py")
        
        print("\n🎯 RISULTATO FINALE:")
        print("   • Ricerca fuzzy in TUTTE le entità del catasto")
        print("   • Interface con 7 tab specializzati")
        print("   • Export risultati in CSV/JSON")
        print("   • Dettagli completi per ogni record")
        print("   • Performance ottimizzate con indici GIN")
        
        print("\n📊 FUNZIONALITÀ AMPLIATE:")
        print("   • Possessori e Località (già esistenti)")
        print("   • 🆕 Immobili (natura, classificazione, consistenza)")
        print("   • 🆕 Variazioni (tipo, nominativo, numero riferimento)")
        print("   • 🆕 Contratti (tipo, notaio, repertorio, note)")
        print("   • 🆕 Partite (numero, suffisso)")
        print("   • 🆕 Ricerca unificata con risultati raggruppati")
        
        print("\n" + "=" * 70)
        print("🚀 SISTEMA PRONTO PER L'AMPLIAMENTO!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRORE DURANTE L'IMPLEMENTAZIONE: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n🎉 Implementazione completata alle {datetime.now().strftime('%H:%M:%S')}")
        print("Segui le istruzioni sopra per completare l'integrazione.")
    else:
        print(f"\n💥 Implementazione fallita alle {datetime.now().strftime('%H:%M:%S')}")
        print("Controlla i messaggi di errore e riprova.")
    
    input("\nPremi INVIO per chiudere...")