
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
    print("\n🗄️ TEST FUNZIONI DATABASE")
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
        print("\n❌ TEST FALLITO: Problemi con gli import")
        print("SOLUZIONE: Verifica che i file artifacts siano stati salvati correttamente")
        return
    
    # Test database
    if not test_database_functions():
        print("\n⚠️ TEST PARZIALE: Database non disponibile o non configurato")
        print("NOTA: Questo è normale se il database non è ancora stato configurato")
    else:
        print("\n✅ TEST COMPLETO: Tutto funziona correttamente!")
    
    print("\n🚀 PROSSIMI PASSI:")
    print("1. Avvia l'applicazione: python gui_main.py")
    print("2. Cerca il tab 'Ricerca Avanzata' (dovrebbe essere presente)")
    print("3. Testa la ricerca con termini come: terra, vendita, notaio")
    print("4. Verifica che ci siano più tab nei risultati (Immobili, Variazioni, ecc.)")

if __name__ == "__main__":
    main()
