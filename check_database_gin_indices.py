#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per verificare gli indici GIN esistenti nel database
File: check_database_gin_indices.py
"""

def check_pg_trgm_extension():
    """Verifica se l'estensione pg_trgm è installata."""
    print("🧩 VERIFICA ESTENSIONE PG_TRGM")
    print("-" * 50)
    
    try:
        from catasto_db_manager import CatastoDBManager
        
        db_manager = CatastoDBManager()
        conn = db_manager._get_connection()
        
        try:
            with conn.cursor() as cur:
                # Verifica estensione pg_trgm
                cur.execute("""
                    SELECT extname, extversion, nspname as schema
                    FROM pg_extension e
                    JOIN pg_namespace n ON e.extnamespace = n.oid
                    WHERE extname = 'pg_trgm'
                """)
                
                result = cur.fetchone()
                if result:
                    print(f"   ✅ pg_trgm installato: versione {result[1]} nello schema {result[2]}")
                    return True
                else:
                    print("   ❌ pg_trgm NON installato")
                    return False
                    
        finally:
            db_manager._release_connection(conn)
            
    except Exception as e:
        print(f"   ❌ Errore verifica pg_trgm: {e}")
        return False

def list_all_gin_indices():
    """Elenca TUTTI gli indici GIN nel database."""
    print("\n📊 TUTTI GLI INDICI GIN NEL DATABASE")
    print("-" * 50)
    
    try:
        from catasto_db_manager import CatastoDBManager
        
        db_manager = CatastoDBManager()
        conn = db_manager._get_connection()
        
        try:
            with conn.cursor() as cur:
                # Query per trovare TUTTI gli indici GIN
                cur.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes 
                    WHERE indexdef ILIKE '%gin%'
                    ORDER BY schemaname, tablename, indexname
                """)
                
                indices = cur.fetchall()
                
                if indices:
                    print(f"   Trovati {len(indices)} indici GIN:")
                    for idx in indices:
                        schema, table, index_name, definition = idx
                        print(f"   📌 Schema: {schema}")
                        print(f"      Tabella: {table}")
                        print(f"      Indice: {index_name}")
                        print(f"      Definizione: {definition}")
                        print()
                    return indices
                else:
                    print("   ❌ Nessun indice GIN trovato in tutto il database")
                    return []
                    
        finally:
            db_manager._release_connection(conn)
            
    except Exception as e:
        print(f"   ❌ Errore ricerca indici GIN: {e}")
        return []

def check_specific_schema_indices():
    """Verifica indici nello schema specifico del db_manager."""
    print("\n🔍 VERIFICA SCHEMA SPECIFICO")
    print("-" * 50)
    
    try:
        from catasto_db_manager import CatastoDBManager
        
        db_manager = CatastoDBManager()
        schema = getattr(db_manager, 'schema', 'public')
        print(f"   Schema configurato nel db_manager: '{schema}'")
        
        conn = db_manager._get_connection()
        
        try:
            with conn.cursor() as cur:
                # Verifica indici nello schema specifico
                cur.execute("""
                    SELECT 
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes 
                    WHERE schemaname = %s
                    AND indexdef ILIKE '%gin%'
                    ORDER BY tablename, indexname
                """, (schema,))
                
                indices = cur.fetchall()
                
                if indices:
                    print(f"   ✅ Trovati {len(indices)} indici GIN nello schema '{schema}':")
                    for idx in indices:
                        table, index_name, definition = idx
                        print(f"      • {table}.{index_name}")
                        print(f"        {definition}")
                        print()
                    return indices
                else:
                    print(f"   ❌ Nessun indice GIN nello schema '{schema}'")
                    return []
                    
        finally:
            db_manager._release_connection(conn)
            
    except Exception as e:
        print(f"   ❌ Errore verifica schema: {e}")
        return []

def check_similarity_function():
    """Testa se la funzione similarity funziona."""
    print("\n🧪 TEST FUNZIONE SIMILARITY")
    print("-" * 50)
    
    try:
        from catasto_db_manager import CatastoDBManager
        
        db_manager = CatastoDBManager()
        conn = db_manager._get_connection()
        
        try:
            with conn.cursor() as cur:
                # Test funzione similarity
                cur.execute("SELECT similarity('mario', 'maria') as sim")
                result = cur.fetchone()[0]
                print(f"   ✅ Funzione similarity: similarity('mario', 'maria') = {result}")
                
                # Test operatore %%
                cur.execute("SELECT 'mario' %% 'maria' as match")
                result = cur.fetchone()[0]
                print(f"   ✅ Operatore %%: 'mario' %% 'maria' = {result}")
                
                return True
                
        finally:
            db_manager._release_connection(conn)
            
    except Exception as e:
        print(f"   ❌ Errore test similarity: {e}")
        return False

def check_catasto_tables():
    """Verifica le tabelle del catasto e loro indici."""
    print("\n📋 VERIFICA TABELLE CATASTO")
    print("-" * 50)
    
    try:
        from catasto_db_manager import CatastoDBManager
        
        db_manager = CatastoDBManager()
        schema = getattr(db_manager, 'schema', 'public')
        
        conn = db_manager._get_connection()
        
        try:
            with conn.cursor() as cur:
                # Verifica esistenza tabelle principali
                tables_to_check = ['possessore', 'localita', 'variazione', 'immobile', 'contratto', 'partita']
                
                for table in tables_to_check:
                    # Verifica esistenza tabella
                    cur.execute("""
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name = %s
                    """, (schema, table))
                    
                    if cur.fetchone():
                        print(f"   ✅ Tabella {table} esiste")
                        
                        # Verifica indici per questa tabella
                        cur.execute("""
                            SELECT indexname, indexdef
                            FROM pg_indexes 
                            WHERE schemaname = %s 
                            AND tablename = %s
                            ORDER BY indexname
                        """, (schema, table))
                        
                        indices = cur.fetchall()
                        if indices:
                            gin_indices = [idx for idx in indices if 'gin' in idx[1].lower()]
                            if gin_indices:
                                print(f"      🔍 Indici GIN: {len(gin_indices)}")
                                for idx in gin_indices:
                                    print(f"         • {idx[0]}")
                            else:
                                print(f"      ⚠️ Nessun indice GIN")
                        else:
                            print(f"      ⚠️ Nessun indice")
                    else:
                        print(f"   ❌ Tabella {table} NON esiste")
                        
        finally:
            db_manager._release_connection(conn)
            
    except Exception as e:
        print(f"   ❌ Errore verifica tabelle: {e}")

def test_current_gin_search():
    """Testa il metodo get_gin_indices_info del widget."""
    print("\n🔧 TEST METODO WIDGET")
    print("-" * 50)
    
    try:
        from catasto_db_manager import CatastoDBManager
        from catasto_gin_extension import extend_db_manager_with_gin
        
        db_manager = CatastoDBManager()
        extended_db = extend_db_manager_with_gin(db_manager)
        
        if hasattr(extended_db, 'get_gin_indices_info'):
            indices = extended_db.get_gin_indices_info()
            print(f"   📊 Il widget trova {len(indices)} indici GIN:")
            for idx in indices:
                print(f"      • {idx.get('tablename', 'N/A')}.{idx.get('indexname', 'N/A')}")
            return indices
        else:
            print("   ❌ Metodo get_gin_indices_info non trovato")
            return []
            
    except Exception as e:
        print(f"   ❌ Errore test widget: {e}")
        return []

def main():
    """Funzione principale di diagnostica."""
    print("=" * 60)
    print("DIAGNOSTICA COMPLETA INDICI GIN")
    print("=" * 60)
    
    # 1. Verifica estensione pg_trgm
    pg_trgm_ok = check_pg_trgm_extension()
    
    # 2. Lista tutti gli indici GIN
    all_gin_indices = list_all_gin_indices()
    
    # 3. Verifica schema specifico
    schema_indices = check_specific_schema_indices()
    
    # 4. Test funzioni similarity
    similarity_ok = check_similarity_function()
    
    # 5. Verifica tabelle catasto
    check_catasto_tables()
    
    # 6. Test widget
    widget_indices = test_current_gin_search()
    
    # Riepilogo
    print("\n" + "=" * 60)
    print("RIEPILOGO DIAGNOSTICA")
    print("=" * 60)
    
    print(f"🧩 Estensione pg_trgm: {'✅ OK' if pg_trgm_ok else '❌ Mancante'}")
    print(f"📊 Indici GIN totali: {len(all_gin_indices)}")
    print(f"🔍 Indici GIN nello schema: {len(schema_indices)}")
    print(f"🧪 Funzione similarity: {'✅ OK' if similarity_ok else '❌ Non funziona'}")
    print(f"🔧 Widget trova indici: {len(widget_indices)}")
    
    if len(all_gin_indices) > 0 and len(widget_indices) == 0:
        print("\n💡 PROBLEMA IDENTIFICATO:")
        print("   Gli indici GIN esistono ma il widget non li trova!")
        print("   Possibile problema di schema o query nel widget.")
    elif len(all_gin_indices) == 0:
        print("\n💡 PROBLEMA IDENTIFICATO:")
        print("   Non ci sono indici GIN nel database.")
        print("   Hai installato l'estensione pg_trgm ma non creato gli indici.")

if __name__ == "__main__":
    main()
    input("\nPremi INVIO per chiudere...")
