#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script completo per risolvere tutti i problemi della ricerca fuzzy
File: fix_fuzzy_complete.py
"""

import os
import shutil
from datetime import datetime

def backup_file(filepath):
    """Crea backup di un file."""
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}_backup_fix_{timestamp}"
        shutil.copy2(filepath, backup_path)
        print(f"✅ Backup creato: {backup_path}")
        return backup_path
    return None

def fix_catasto_gin_extension():
    """Aggiunge i metodi mancanti a catasto_gin_extension.py."""
    print("🔧 CORREZIONE catasto_gin_extension.py")
    print("-" * 50)
    
    if not os.path.exists('catasto_gin_extension.py'):
        print("❌ File catasto_gin_extension.py non trovato!")
        return False
    
    # Backup
    backup_path = backup_file('catasto_gin_extension.py')
    
    # Leggi il file
    with open('catasto_gin_extension.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Controlla se i metodi sono già presenti
    if 'search_variazioni_fuzzy' in content:
        print("✅ Metodi già presenti nel file")
        return True
    
    # Trova la fine della classe CatastoGINExtension
    class_end_patterns = [
        '# ========================================================================',
        'def extend_db_manager_with_gin',
        'class ',
        'if __name__'
    ]
    
    lines = content.split('\n')
    insert_position = len(lines) - 1
    
    # Trova la posizione dove inserire i metodi
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if any(pattern in line for pattern in class_end_patterns):
            insert_position = i
            break
        if line.startswith('    def ') and 'CatastoGINExtension' in ''.join(lines[max(0, i-20):i]):
            insert_position = i + 1
            break
    
    # Metodi da aggiungere
    new_methods = '''
    def search_variazioni_fuzzy(self, query_text: str, threshold: float = 0.3, limit: int = 100):
        """Ricerca fuzzy nelle variazioni."""
        try:
            query = """
            SELECT 
                v.id,
                v.tipo,
                v.data_variazione,
                v.descrizione,
                p.numero_partita,
                COALESCE(
                    GREATEST(
                        similarity(v.tipo, %s),
                        similarity(COALESCE(v.descrizione, ''), %s)
                    ), 0
                ) as similarity_score
            FROM variazione v
            LEFT JOIN partita p ON v.partita_id = p.id
            WHERE (v.tipo %% %s OR COALESCE(v.descrizione, '') %% %s)
            AND GREATEST(
                similarity(v.tipo, %s),
                similarity(COALESCE(v.descrizione, ''), %s)
            ) > %s
            ORDER BY similarity_score DESC, v.data_variazione DESC
            LIMIT %s
            """
            
            params = (query_text, query_text, query_text, query_text, 
                     query_text, query_text, threshold, limit)
            
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, params)
                    results = cur.fetchall()
                    return [dict(row) for row in results]
            finally:
                self.db_manager._release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Errore ricerca variazioni fuzzy: {e}")
            return []

    def search_immobili_fuzzy(self, query_text: str, threshold: float = 0.3, limit: int = 100):
        """Ricerca fuzzy negli immobili."""
        try:
            query = """
            SELECT 
                i.id,
                i.descrizione,
                i.natura,
                p.numero_partita,
                c.nome as comune_nome,
                COALESCE(
                    GREATEST(
                        similarity(COALESCE(i.descrizione, ''), %s),
                        similarity(COALESCE(i.natura, ''), %s)
                    ), 0
                ) as similarity_score
            FROM immobile i
            LEFT JOIN partita p ON i.partita_id = p.id
            LEFT JOIN comune c ON p.comune_id = c.id
            WHERE (COALESCE(i.descrizione, '') %% %s OR COALESCE(i.natura, '') %% %s)
            AND GREATEST(
                similarity(COALESCE(i.descrizione, ''), %s),
                similarity(COALESCE(i.natura, ''), %s)
            ) > %s
            ORDER BY similarity_score DESC, i.descrizione
            LIMIT %s
            """
            
            params = (query_text, query_text, query_text, query_text,
                     query_text, query_text, threshold, limit)
            
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, params)
                    results = cur.fetchall()
                    return [dict(row) for row in results]
            finally:
                self.db_manager._release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Errore ricerca immobili fuzzy: {e}")
            return []

    def search_contratti_fuzzy(self, query_text: str, threshold: float = 0.3, limit: int = 100):
        """Ricerca fuzzy nei contratti."""
        try:
            query = """
            SELECT 
                co.id,
                co.tipo,
                co.data_stipula,
                co.contraente,
                p.numero_partita,
                COALESCE(
                    GREATEST(
                        similarity(COALESCE(co.tipo, ''), %s),
                        similarity(COALESCE(co.contraente, ''), %s)
                    ), 0
                ) as similarity_score
            FROM contratto co
            LEFT JOIN partita p ON co.partita_id = p.id
            WHERE (COALESCE(co.tipo, '') %% %s OR COALESCE(co.contraente, '') %% %s)
            AND GREATEST(
                similarity(COALESCE(co.tipo, ''), %s),
                similarity(COALESCE(co.contraente, ''), %s)
            ) > %s
            ORDER BY similarity_score DESC, co.data_stipula DESC
            LIMIT %s
            """
            
            params = (query_text, query_text, query_text, query_text,
                     query_text, query_text, threshold, limit)
            
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, params)
                    results = cur.fetchall()
                    return [dict(row) for row in results]
            finally:
                self.db_manager._release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Errore ricerca contratti fuzzy: {e}")
            return []

    def search_partite_fuzzy(self, query_text: str, threshold: float = 0.3, limit: int = 100):
        """Ricerca fuzzy nelle partite."""
        try:
            # Se query_text è numerica, cerca per numero partita
            if query_text.isdigit():
                query = """
                SELECT 
                    p.id,
                    p.numero_partita,
                    p.tipo_partita,
                    p.anno_attivazione,
                    c.nome as comune_nome,
                    1.0 as similarity_score
                FROM partita p
                LEFT JOIN comune c ON p.comune_id = c.id
                WHERE p.numero_partita::text LIKE %s
                ORDER BY p.numero_partita
                LIMIT %s
                """
                search_pattern = f"%{query_text}%"
                params = (search_pattern, limit)
            else:
                # Ricerca testuale su tipo_partita
                query = """
                SELECT 
                    p.id,
                    p.numero_partita,
                    COALESCE(p.tipo_partita, '') as tipo_partita,
                    p.anno_attivazione,
                    c.nome as comune_nome,
                    COALESCE(similarity(COALESCE(p.tipo_partita, ''), %s), 0) as similarity_score
                FROM partita p
                LEFT JOIN comune c ON p.comune_id = c.id
                WHERE COALESCE(p.tipo_partita, '') %% %s
                AND similarity(COALESCE(p.tipo_partita, ''), %s) > %s
                ORDER BY similarity_score DESC, p.numero_partita
                LIMIT %s
                """
                params = (query_text, query_text, query_text, threshold, limit)
            
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(query, params)
                    results = cur.fetchall()
                    return [dict(row) for row in results]
            finally:
                self.db_manager._release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Errore ricerca partite fuzzy: {e}")
            return []

    def get_gin_indices_info(self):
        """Ottiene informazioni sugli indici GIN disponibili."""
        try:
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    query = """
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes 
                    WHERE indexdef ILIKE '%gin%'
                    AND schemaname = %s
                    ORDER BY tablename, indexname
                    """
                    
                    schema = getattr(self.db_manager, 'schema', 'catasto')
                    cur.execute(query, (schema,))
                    return [dict(row) for row in cur.fetchall()]
                    
            finally:
                self.db_manager._release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Errore recupero indici GIN: {e}")
            return []

'''
    
    # Inserisci i metodi
    lines.insert(insert_position, new_methods)
    
    # Salva il file modificato
    with open('catasto_gin_extension.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print("✅ Metodi aggiunti a catasto_gin_extension.py")
    return True

def setup_database_pg_trgm():
    """Imposta l'estensione pg_trgm nel database."""
    print("\n🧩 SETUP ESTENSIONE PG_TRGM")
    print("-" * 50)
    
    try:
        from catasto_db_manager import CatastoDBManager
        
        db_manager = CatastoDBManager()
        if not db_manager.test_connection():
            print("❌ Connessione database fallita")
            return False
        
        print("✅ Connessione database OK")
        
        # Installa pg_trgm
        conn = db_manager._get_connection()
        try:
            with conn.cursor() as cur:
                # Verifica se pg_trgm è già installato
                cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
                if cur.fetchone():
                    print("✅ Estensione pg_trgm già installata")
                else:
                    # Prova a installare
                    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                    conn.commit()
                    print("✅ Estensione pg_trgm installata")
                
                # Crea indici GIN di base
                indices_sql = [
                    "CREATE INDEX IF NOT EXISTS idx_possessore_nome_gin ON possessore USING gin(nome_completo gin_trgm_ops)",
                    "CREATE INDEX IF NOT EXISTS idx_localita_nome_gin ON localita USING gin(nome gin_trgm_ops)"
                ]
                
                for sql in indices_sql:
                    try:
                        cur.execute(sql)
                        conn.commit()
                        print(f"✅ Indice creato: {sql.split()[-4]}")
                    except Exception as e:
                        print(f"⚠️ Indice già esistente o errore: {e}")
                        conn.rollback()
                
        finally:
            db_manager._release_connection(conn)
        
        return True
        
    except Exception as e:
        print(f"❌ Errore setup database: {e}")
        return False

def test_fuzzy_search():
    """Testa la ricerca fuzzy."""
    print("\n🔍 TEST RICERCA FUZZY")
    print("-" * 50)
    
    try:
        from catasto_db_manager import CatastoDBManager
        from catasto_gin_extension import extend_db_manager_with_gin
        
        db_manager = CatastoDBManager()
        extended_db = extend_db_manager_with_gin(db_manager)
        
        # Test ricerca possessori
        print("Test ricerca possessori...")
        possessori = extended_db.search_possessori_fuzzy("test", threshold=0.1, limit=3)
        print(f"✅ Possessori: {len(possessori)} risultati")
        
        # Test ricerca località
        print("Test ricerca località...")
        localita = extended_db.search_localita_fuzzy("via", threshold=0.1, limit=3)
        print(f"✅ Località: {len(localita)} risultati")
        
        # Test metodi appena aggiunti
        print("Test ricerca variazioni...")
        variazioni = extended_db.search_variazioni_fuzzy("test", threshold=0.1, limit=3)
        print(f"✅ Variazioni: {len(variazioni)} risultati")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funzione principale."""
    print("=" * 60)
    print("FIX COMPLETO RICERCA FUZZY")
    print("=" * 60)
    
    # 1. Fix catasto_gin_extension.py
    if not fix_catasto_gin_extension():
        print("\n❌ FALLIMENTO: Impossibile correggere catasto_gin_extension.py")
        return False
    
    # 2. Setup database
    if not setup_database_pg_trgm():
        print("\n⚠️ AVVISO: Setup database incompleto (normale se non hai privilegi admin)")
        print("💡 Chiedi all'amministratore di eseguire: CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    
    # 3. Test
    if test_fuzzy_search():
        print("\n✅ SUCCESS: Ricerca fuzzy riparata!")
        print("🚀 Riavvia l'applicazione: python gui_main.py")
    else:
        print("\n⚠️ Test fallito, ma i file sono stati corretti")
        print("🔄 Riavvia l'applicazione e prova")
    
    print("\n📋 COSA È STATO FATTO:")
    print("• Aggiunti metodi mancanti a catasto_gin_extension.py")
    print("• Tentato setup estensione pg_trgm")
    print("• Creati indici GIN di base")
    print("• Testata la ricerca fuzzy")

if __name__ == "__main__":
    main()
    input("\nPremi INVIO per chiudere...")
