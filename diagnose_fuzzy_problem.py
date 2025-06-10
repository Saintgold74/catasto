#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script di diagnostica per il problema della ricerca fuzzy
File: diagnose_fuzzy_problem.py
"""

import os
import sys
import traceback

def check_files():
    """Verifica l'esistenza dei file necessari."""
    print("📁 VERIFICA FILE")
    print("-" * 40)
    
    required_files = [
        'catasto_gin_extension.py',
        'fuzzy_search_widget.py',
        'catasto_db_manager.py',
        'gui_main.py'
    ]
    
    all_exist = True
    for file in required_files:
        exists = os.path.exists(file)
        status = "✅" if exists else "❌"
        print(f"   {status} {file}")
        if not exists:
            all_exist = False
    
    return all_exist

def test_catasto_gin_import():
    """Testa l'import di catasto_gin_extension."""
    print("\n🔌 TEST IMPORT CATASTO_GIN_EXTENSION")
    print("-" * 40)
    
    try:
        from catasto_gin_extension import CatastoGINSearch
        print("   ✅ Import CatastoGINSearch riuscito")
        return True
    except ImportError as e:
        print(f"   ❌ Import CatastoGINSearch fallito: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"   ❌ Errore generico import: {e}")
        traceback.print_exc()
        return False

def test_db_manager():
    """Testa il database manager."""
    print("\n💾 TEST DATABASE MANAGER")
    print("-" * 40)
    
    try:
        from catasto_db_manager import CatastoDBManager
        print("   ✅ Import CatastoDBManager riuscito")
        
        db_manager = CatastoDBManager()
        print("   ✅ Istanza CatastoDBManager creata")
        
        # Test connessione
        if hasattr(db_manager, 'test_connection'):
            if db_manager.test_connection():
                print("   ✅ Connessione database OK")
                return db_manager
            else:
                print("   ❌ Test connessione fallito")
                return None
        else:
            print("   ⚠️ Metodo test_connection non trovato, assumo OK")
            return db_manager
            
    except Exception as e:
        print(f"   ❌ Errore database manager: {e}")
        traceback.print_exc()
        return None

def test_gin_search_creation(db_manager):
    """Testa la creazione di CatastoGINSearch."""
    print("\n🔍 TEST CREAZIONE GIN SEARCH")
    print("-" * 40)
    
    try:
        from catasto_gin_extension import CatastoGINSearch
        
        gin_search = CatastoGINSearch(db_manager)
        print("   ✅ CatastoGINSearch creato")
        
        # Test metodi di connessione
        if hasattr(gin_search, '_get_connection'):
            print("   ✅ Metodo _get_connection presente")
            try:
                conn = gin_search._get_connection()
                print("   ✅ Connessione ottenuta")
                gin_search._release_connection(conn)
                print("   ✅ Connessione rilasciata")
            except Exception as e:
                print(f"   ❌ Errore test connessione: {e}")
        else:
            print("   ❌ Metodo _get_connection non trovato")
        
        return gin_search
        
    except Exception as e:
        print(f"   ❌ Errore creazione GIN search: {e}")
        traceback.print_exc()
        return None

def test_database_extensions(gin_search):
    """Testa le estensioni del database."""
    print("\n🧩 TEST ESTENSIONI DATABASE")
    print("-" * 40)
    
    try:
        conn = gin_search._get_connection()
        try:
            with conn.cursor() as cur:
                # Test pg_trgm
                cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
                if cur.fetchone():
                    print("   ✅ Estensione pg_trgm installata")
                else:
                    print("   ❌ Estensione pg_trgm NON installata")
                    print("   💡 Esegui: CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                
                # Test funzione similarity
                cur.execute("SELECT similarity('test', 'testa')")
                result = cur.fetchone()[0]
                print(f"   ✅ Funzione similarity funziona: {result}")
                
                # Test operatore %%
                cur.execute("SELECT 'test' %% 'testa'")
                result = cur.fetchone()[0]
                print(f"   ✅ Operatore %% funziona: {result}")
                
        finally:
            gin_search._release_connection(conn)
            
        return True
        
    except Exception as e:
        print(f"   ❌ Errore test estensioni: {e}")
        traceback.print_exc()
        return False

def test_simple_search(gin_search):
    """Testa una ricerca semplice."""
    print("\n🔎 TEST RICERCA SEMPLICE")
    print("-" * 40)
    
    try:
        # Test ricerca possessori
        print("   Test ricerca possessori...")
        possessori = gin_search.search_possessori_fuzzy("test", threshold=0.1, limit=1)
        print(f"   ✅ Ricerca possessori: {len(possessori)} risultati")
        
        # Test ricerca località
        print("   Test ricerca località...")
        localita = gin_search.search_localita_fuzzy("via", threshold=0.1, limit=1)
        print(f"   ✅ Ricerca località: {len(localita)} risultati")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Errore ricerca: {e}")
        traceback.print_exc()
        return False

def test_widget_creation():
    """Testa la creazione del widget."""
    print("\n🖼️ TEST CREAZIONE WIDGET")
    print("-" * 40)
    
    try:
        from fuzzy_search_widget import CompactFuzzySearchWidget
        print("   ✅ Import CompactFuzzySearchWidget riuscito")
        
        # Crea mock db_manager
        class MockDBManager:
            def __init__(self):
                self.schema = "catasto"
        
        mock_db = MockDBManager()
        widget = CompactFuzzySearchWidget(mock_db)
        print("   ✅ Widget creato con mock db_manager")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Errore creazione widget: {e}")
        traceback.print_exc()
        return False

def suggest_solutions():
    """Suggerisce soluzioni basate sui test."""
    print("\n💡 SOLUZIONI SUGGERITE")
    print("-" * 40)
    
    print("1. Se manca pg_trgm:")
    print("   Esegui nel database: CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    print("")
    
    print("2. Se i metodi di connessione non funzionano:")
    print("   Il db_manager potrebbe non essere compatibile")
    print("   Verifica che abbia i metodi _get_connection() e _release_connection()")
    print("")
    
    print("3. Se l'import fallisce:")
    print("   Verifica che tutti i file siano nella stessa directory")
    print("   Controlla errori di sintassi nei file")
    print("")
    
    print("4. Test rapido manuale:")
    print("   python -c \"from catasto_gin_extension import CatastoGINSearch; print('OK')\"")

def main():
    """Esegue la diagnostica completa."""
    print("=" * 60)
    print("DIAGNOSTICA RICERCA FUZZY")
    print("=" * 60)
    
    # 1. Verifica file
    if not check_files():
        print("\n❌ DIAGNOSTICA FALLITA: File mancanti")
        return
    
    # 2. Test import gin extension
    if not test_catasto_gin_import():
        print("\n❌ DIAGNOSTICA FALLITA: Import catasto_gin_extension")
        suggest_solutions()
        return
    
    # 3. Test database manager
    db_manager = test_db_manager()
    if not db_manager:
        print("\n❌ DIAGNOSTICA FALLITA: Database manager")
        suggest_solutions()
        return
    
    # 4. Test creazione gin search
    gin_search = test_gin_search_creation(db_manager)
    if not gin_search:
        print("\n❌ DIAGNOSTICA FALLITA: Creazione GIN search")
        suggest_solutions()
        return
    
    # 5. Test estensioni database
    if not test_database_extensions(gin_search):
        print("\n❌ DIAGNOSTICA FALLITA: Estensioni database")
        print("\n🔧 SOLUZIONE IMMEDIATA:")
        print("Esegui nel database: CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        return
    
    # 6. Test ricerca
    if not test_simple_search(gin_search):
        print("\n❌ DIAGNOSTICA FALLITA: Ricerca")
        suggest_solutions()
        return
    
    # 7. Test widget
    if not test_widget_creation():
        print("\n❌ DIAGNOSTICA FALLITA: Widget")
        suggest_solutions()
        return
    
    print("\n" + "=" * 60)
    print("✅ DIAGNOSTICA COMPLETATA - TUTTO OK!")
    print("=" * 60)
    print("\n🎉 La ricerca fuzzy dovrebbe funzionare correttamente!")
    print("🚀 Riavvia l'applicazione: python gui_main.py")

if __name__ == "__main__":
    main()
    input("\nPremi INVIO per chiudere...")
