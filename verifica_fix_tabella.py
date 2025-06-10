#!/usr/bin/env python3
"""
Verifica il nome corretto della tabella di relazione e corregge la query.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import shutil
from datetime import datetime
import re

# Configurazione database
DB_CONFIG = {
    'host': 'localhost',
    'database': 'catasto_storico',
    'user': 'postgres',
    'password': 'Markus74',  # inserisci la tua password
    'port': 5432
}

def verifica_nome_tabella():
    """Verifica il nome corretto della tabella di relazione."""
    conn = psycopg2.connect(**DB_CONFIG)
    
    try:
        with conn.cursor() as cur:
            # Cerca tutte le tabelle che potrebbero essere la relazione
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'catasto' 
                AND (
                    table_name LIKE '%partita%possessore%' 
                    OR table_name LIKE '%possessore%partita%'
                )
            """)
            
            tabelle = cur.fetchall()
            print("TABELLE DI RELAZIONE TROVATE:")
            for t in tabelle:
                print(f"  - {t[0]}")
                
            # Verifica anche le colonne di partita_possessore
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'catasto' 
                AND table_name = 'partita_possessore'
                ORDER BY ordinal_position
            """)
            
            colonne = cur.fetchall()
            if colonne:
                print("\nCOLONNE IN partita_possessore:")
                for c in colonne:
                    print(f"  - {c[0]}")
                return 'partita_possessore'
            
            return None
            
    except Exception as e:
        print(f"Errore: {e}")
        return None
    finally:
        conn.close()

def fix_query_with_correct_table(filename='catasto_gin_extension.py', table_name='partita_possessore'):
    """Corregge la query con il nome corretto della tabella."""
    
    # Backup del file
    backup_name = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        shutil.copy2(filename, backup_name)
        print(f"✓ Backup creato: {backup_name}")
    except:
        print("⚠ File catasto_gin_extension.py non trovato, creazione query corretta...")
    
    # Query corretta con il nome giusto della tabella
    correct_query = f'''"""
                SELECT DISTINCT
                    p.id,
                    p.nome_completo,
                    p.cognome_nome,
                    p.paternita,
                    c.nome as comune_nome,
                    COUNT(DISTINCT pp.partita_id) as num_partite,
                    public.similarity(p.nome_completo, %s) as similarity
                FROM catasto.possessore p
                LEFT JOIN catasto.comune c ON p.comune_id = c.id
                LEFT JOIN catasto.{table_name} pp ON p.id = pp.possessore_id
                WHERE public.similarity(p.nome_completo, %s) > %s
                GROUP BY p.id, p.nome_completo, p.cognome_nome, p.paternita, c.nome
                ORDER BY similarity DESC
                LIMIT %s
            """'''
    
    try:
        # Leggi il contenuto
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern per trovare la query da sostituire
        pattern = r'possessore_partita'
        replacement = table_name
        
        # Sostituisci
        new_content = content.replace(pattern, replacement)
        
        # Scrivi il file corretto
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✓ Sostituito 'possessore_partita' con '{table_name}'")
        
    except FileNotFoundError:
        print("⚠ File non trovato, creazione metodo alternativo...")
        create_alternative_method(table_name)

def create_alternative_method(table_name='partita_possessore'):
    """Crea un metodo alternativo per il widget."""
    
    fix_code = f'''# METODO CORRETTO PER RICERCA POSSESSORI
# Aggiungi questo al tuo widget o sostituisci il metodo esistente

def search_possessori_fuzzy_correct(self, query_text, similarity_threshold=0.3, limit=30):
    """Ricerca fuzzy nei possessori con tabella corretta."""
    try:
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Imposta search_path
                cur.execute("SET search_path TO catasto, public")
                
                # Query con nome tabella corretto
                cur.execute("""
                    SELECT DISTINCT
                        p.id,
                        p.nome_completo,
                        p.cognome_nome,
                        p.paternita,
                        c.nome as comune_nome,
                        COUNT(DISTINCT pp.partita_id) as num_partite,
                        public.similarity(p.nome_completo, %s) as similarity
                    FROM catasto.possessore p
                    LEFT JOIN catasto.comune c ON p.comune_id = c.id
                    LEFT JOIN catasto.{table_name} pp ON p.id = pp.possessore_id
                    WHERE public.similarity(p.nome_completo, %s) > %s
                    GROUP BY p.id, p.nome_completo, p.cognome_nome, p.paternita, c.nome
                    ORDER BY similarity DESC
                    LIMIT %s
                """, (query_text, query_text, similarity_threshold, limit))
                
                results = []
                for row in cur.fetchall():
                    result = dict(row)
                    result['similarity_score'] = result['similarity']
                    results.append(result)
                
                return results
                
    except Exception as e:
        print(f"Errore ricerca possessori: {{e}}")
        # Fallback senza conteggio partite
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SET search_path TO catasto, public")
                    cur.execute("""
                        SELECT DISTINCT
                            p.id,
                            p.nome_completo,
                            p.cognome_nome,
                            p.paternita,
                            c.nome as comune_nome,
                            0 as num_partite,
                            public.similarity(p.nome_completo, %s) as similarity
                        FROM catasto.possessore p
                        LEFT JOIN catasto.comune c ON p.comune_id = c.id
                        WHERE public.similarity(p.nome_completo, %s) > %s
                        ORDER BY similarity DESC
                        LIMIT %s
                    """, (query_text, query_text, similarity_threshold, limit))
                    
                    results = []
                    for row in cur.fetchall():
                        result = dict(row)
                        result['similarity_score'] = result['similarity']
                        results.append(result)
                    
                    return results
        except Exception as e2:
            print(f"Errore anche nel fallback: {{e2}}")
            return []
'''
    
    with open('metodo_ricerca_corretto.py', 'w', encoding='utf-8') as f:
        f.write(fix_code)
    
    print(f"✓ Creato file 'metodo_ricerca_corretto.py' con query per tabella '{table_name}'")

def test_query_corretta(table_name='partita_possessore'):
    """Testa la query con il nome corretto della tabella."""
    conn = psycopg2.connect(**DB_CONFIG)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print(f"\nTEST QUERY CON TABELLA '{table_name}':")
            
            cur.execute("SET search_path TO catasto, public")
            cur.execute(f"""
                SELECT DISTINCT
                    p.id,
                    p.nome_completo,
                    p.cognome_nome,
                    p.paternita,
                    c.nome as comune_nome,
                    COUNT(DISTINCT pp.partita_id) as num_partite,
                    public.similarity(p.nome_completo, %s) as similarity
                FROM catasto.possessore p
                LEFT JOIN catasto.comune c ON p.comune_id = c.id
                LEFT JOIN catasto.{table_name} pp ON p.id = pp.possessore_id
                WHERE public.similarity(p.nome_completo, %s) > %s
                GROUP BY p.id, p.nome_completo, p.cognome_nome, p.paternita, c.nome
                ORDER BY similarity DESC
                LIMIT %s
            """, ('ross', 'ross', 0.1, 10))
            
            results = cur.fetchall()
            print(f"✓ Query eseguita con successo! Trovati {len(results)} risultati:")
            for r in results[:5]:
                print(f"  - {r['nome_completo']} (partite: {r['num_partite']}, sim: {r['similarity']:.3f})")
                
            return True
            
    except Exception as e:
        print(f"✗ Errore: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("VERIFICA E FIX TABELLA RELAZIONE PARTITE-POSSESSORI")
    print("=" * 60)
    
    # 1. Verifica il nome della tabella
    table_name = verifica_nome_tabella()
    
    if table_name:
        print(f"\n✓ Tabella di relazione trovata: '{table_name}'")
        
        # 2. Test della query
        if test_query_corretta(table_name):
            # 3. Applica il fix
            fix_query_with_correct_table('catasto_gin_extension.py', table_name)
            
            print("\n" + "=" * 60)
            print("FIX COMPLETATO!")
            print("Riavvia l'applicazione e la ricerca fuzzy dovrebbe funzionare.")
    else:
        print("\n⚠ Tabella di relazione non trovata!")
        print("Creazione query senza conteggio partite...")
        create_alternative_method('')
