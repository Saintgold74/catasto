#!/usr/bin/env python3
"""
Test diretto per verificare la ricerca fuzzy nel database.
Esegue varie query per capire dove sta il problema.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# Configurazione database (modifica con i tuoi parametri)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'catasto_storico',
    'user': 'postgres',
    'password': 'Markus74',  # inserisci la tua password
    'port': 5432
}

def test_ricerca():
    """Esegue vari test di ricerca."""
    conn = psycopg2.connect(**DB_CONFIG)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print("TEST RICERCA FUZZY NEL DATABASE")
            print("=" * 60)
            
            # 1. Verifica che ci siano dati
            print("\n1. VERIFICA PRESENZA DATI:")
            cur.execute("SELECT COUNT(*) as count FROM catasto.possessore")
            count = cur.fetchone()['count']
            print(f"   Totale possessori nel database: {count}")
            
            # 2. Cerca possessori che contengono 'ross' (case insensitive)
            print("\n2. RICERCA SEMPLICE 'ross' (ILIKE):")
            cur.execute("""
                SELECT nome_completo 
                FROM catasto.possessore 
                WHERE nome_completo ILIKE '%ross%' 
                LIMIT 10
            """)
            results = cur.fetchall()
            print(f"   Trovati {len(results)} risultati con ILIKE:")
            for r in results:
                print(f"   - {r['nome_completo']}")
            
            # 3. Test similarity con diverse soglie
            print("\n3. TEST SIMILARITY CON DIVERSE SOGLIE:")
            soglie = [0.1, 0.2, 0.3, 0.5]
            
            for soglia in soglie:
                cur.execute("SET search_path TO catasto, public")
                cur.execute("""
                    SELECT nome_completo, similarity(nome_completo, %s) as sim
                    FROM catasto.possessore
                    WHERE similarity(nome_completo, %s) > %s
                    ORDER BY sim DESC
                    LIMIT 5
                """, ('ross', 'ross', soglia))
                
                results = cur.fetchall()
                print(f"\n   Soglia {soglia}: trovati {len(results)} risultati")
                for r in results[:3]:  # Mostra solo i primi 3
                    print(f"     - {r['nome_completo']} (sim: {r['sim']:.3f})")
            
            # 4. Test con operatore % (similarity)
            print("\n4. TEST CON OPERATORE % (richiede pg_trgm):")
            try:
                cur.execute("SET search_path TO catasto, public")
                cur.execute("""
                    SELECT nome_completo, similarity(nome_completo, 'ross') as sim
                    FROM catasto.possessore
                    WHERE nome_completo % 'ross'
                    ORDER BY sim DESC
                    LIMIT 5
                """)
                results = cur.fetchall()
                print(f"   Trovati {len(results)} risultati con operatore %")
                for r in results:
                    print(f"   - {r['nome_completo']} (sim: {r['sim']:.3f})")
            except Exception as e:
                print(f"   Errore con operatore %: {e}")
            
            # 5. Test ricerca con word_similarity (più tollerante)
            print("\n5. TEST WORD_SIMILARITY (più tollerante):")
            try:
                cur.execute("SET search_path TO catasto, public")
                cur.execute("""
                    SELECT nome_completo, word_similarity('ross', nome_completo) as sim
                    FROM catasto.possessore
                    WHERE word_similarity('ross', nome_completo) > 0.1
                    ORDER BY sim DESC
                    LIMIT 10
                """)
                results = cur.fetchall()
                print(f"   Trovati {len(results)} risultati con word_similarity")
                for r in results[:5]:
                    print(f"   - {r['nome_completo']} (sim: {r['sim']:.3f})")
            except Exception as e:
                print(f"   word_similarity non disponibile: {e}")
            
            # 6. Verifica indici
            print("\n6. VERIFICA INDICI GIN:")
            cur.execute("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE schemaname = 'catasto' 
                AND tablename = 'possessore'
                AND indexdef LIKE '%gin%'
            """)
            indices = cur.fetchall()
            print(f"   Trovati {len(indices)} indici GIN su possessore:")
            for idx in indices:
                print(f"   - {idx['indexname']}")
            
            # 7. Test query esatta del widget
            print("\n7. TEST QUERY ESATTA DEL WIDGET:")
            query_text = 'ross'
            similarity_threshold = 0.12
            max_results = 30
            
            cur.execute("SET search_path TO catasto, public")
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
                LEFT JOIN catasto.possessore_partita pp ON p.id = pp.possessore_id
                WHERE public.similarity(p.nome_completo, %s) > %s
                GROUP BY p.id, p.nome_completo, p.cognome_nome, p.paternita, c.nome
                ORDER BY similarity DESC
                LIMIT %s
            """, (query_text, query_text, similarity_threshold, max_results))
            
            results = cur.fetchall()
            print(f"   Risultati con query widget (soglia {similarity_threshold}): {len(results)}")
            for r in results[:5]:
                print(f"   - {r['nome_completo']} (sim: {r['similarity']:.3f})")
            
    except Exception as e:
        print(f"\nERRORE: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    test_ricerca()
