#!/usr/bin/env python3
"""
Script di verifica per gli indici GIN del sistema catasto.
Esegue tutti i controlli necessari per diagnosticare problemi con la ricerca fuzzy.
"""

import psycopg2
from psycopg2 import sql
import sys
from datetime import datetime

# Configurazione database (modifica con i tuoi parametri)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'catasto_storico',
    'user': 'postgres',  # o il tuo utente
    'password': 'Markus74',  # inserisci la tua password
    'port': 5432
}

def connetti_db():
    """Connette al database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"ERRORE connessione database: {e}")
        sys.exit(1)

def verifica_estensione_pg_trgm(conn):
    """Verifica se pg_trgm è installata."""
    print("\n=== VERIFICA ESTENSIONE PG_TRGM ===")
    try:
        with conn.cursor() as cur:
            # Controlla se esiste
            cur.execute("SELECT * FROM pg_extension WHERE extname = 'pg_trgm';")
            result = cur.fetchone()
            
            if result:
                print("✓ Estensione pg_trgm TROVATA")
                return True
            else:
                print("✗ Estensione pg_trgm NON TROVATA")
                
                # Prova a installarla
                print("Tentativo di installazione...")
                try:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                    conn.commit()
                    print("✓ pg_trgm installata con successo")
                    return True
                except Exception as e:
                    print(f"✗ Impossibile installare pg_trgm: {e}")
                    print("  Potrebbe essere necessario eseguire come superuser")
                    return False
    except Exception as e:
        print(f"ERRORE durante verifica: {e}")
        return False

def verifica_indici_gin(conn):
    """Verifica tutti gli indici GIN."""
    print("\n=== VERIFICA INDICI GIN ===")
    
    query = """
    SELECT 
        i.schemaname,
        i.tablename,
        i.indexname,
        i.indexdef,
        pg_size_pretty(pg_relation_size(i.indexname::regclass)) as size
    FROM pg_indexes i
    WHERE i.schemaname = 'catasto' 
    AND (
        i.indexdef LIKE '%gin%' 
        OR i.indexname LIKE '%gin%'
    )
    ORDER BY i.tablename, i.indexname;
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
            
            if results:
                print(f"\nTrovati {len(results)} indici GIN:")
                print("-" * 100)
                for row in results:
                    print(f"Tabella: {row[1]}")
                    print(f"  Indice: {row[2]}")
                    print(f"  Dimensione: {row[4]}")
                    print(f"  Definizione: {row[3][:80]}...")
                    print("-" * 100)
            else:
                print("✗ NESSUN indice GIN trovato!")
                
    except Exception as e:
        print(f"ERRORE durante verifica indici: {e}")

def verifica_indici_mancanti(conn):
    """Verifica indici critici per la ricerca fuzzy."""
    print("\n=== VERIFICA INDICI CRITICI ===")
    
    indici_necessari = [
        ('possessore', 'idx_gin_possessore_nome_completo_trgm'),
        ('possessore', 'idx_gin_possessori_nome'),
        ('localita', 'idx_gin_localita_nome_trgm'),
        ('localita', 'idx_gin_localita_nome'),
    ]
    
    for tabella, nome_indice in indici_necessari:
        query = """
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE schemaname = 'catasto' 
            AND tablename = %s 
            AND indexname = %s
        );
        """
        
        try:
            with conn.cursor() as cur:
                cur.execute(query, (tabella, nome_indice))
                exists = cur.fetchone()[0]
                
                if exists:
                    print(f"✓ {tabella}.{nome_indice} - PRESENTE")
                else:
                    print(f"✗ {tabella}.{nome_indice} - MANCANTE")
                    
        except Exception as e:
            print(f"ERRORE verifica {nome_indice}: {e}")

def crea_indici_mancanti(conn):
    """Crea gli indici mancanti."""
    print("\n=== CREAZIONE INDICI MANCANTI ===")
    
    indici_da_creare = [
        # Indici con pg_trgm
        """CREATE INDEX IF NOT EXISTS idx_gin_possessore_nome_completo_trgm
           ON catasto.possessore USING gin (nome_completo gin_trgm_ops);""",
        
        """CREATE INDEX IF NOT EXISTS idx_gin_possessore_cognome_nome_trgm
           ON catasto.possessore USING gin (cognome_nome gin_trgm_ops);""",
        
        """CREATE INDEX IF NOT EXISTS idx_gin_localita_nome_trgm
           ON catasto.localita USING gin (nome gin_trgm_ops);""",
        
        # Indici con to_tsvector (non richiedono pg_trgm)
        """CREATE INDEX IF NOT EXISTS idx_gin_possessori_nome 
           ON catasto.possessore USING gin(to_tsvector('italian', nome_completo));""",
        
        """CREATE INDEX IF NOT EXISTS idx_gin_localita_nome 
           ON catasto.localita USING gin(to_tsvector('italian', nome));""",
    ]
    
    for indice_sql in indici_da_creare:
        try:
            with conn.cursor() as cur:
                print(f"\nCreazione: {indice_sql[:60]}...")
                cur.execute(indice_sql)
                conn.commit()
                print("✓ Creato con successo")
        except Exception as e:
            print(f"✗ Errore: {e}")
            conn.rollback()

def test_ricerca_fuzzy(conn):
    """Testa la ricerca fuzzy."""
    print("\n=== TEST RICERCA FUZZY ===")
    
    # Test 1: con similarity (richiede pg_trgm)
    print("\n1. Test con similarity (pg_trgm):")
    query1 = """
    SELECT 
        nome_completo,
        similarity(nome_completo, 'rossi') as sim
    FROM catasto.possessore
    WHERE similarity(nome_completo, 'rossi') > 0.1
    ORDER BY sim DESC
    LIMIT 5;
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query1)
            results = cur.fetchall()
            if results:
                print("Risultati trovati:")
                for row in results:
                    print(f"  - {row[0]} (similarità: {row[1]:.2f})")
            else:
                print("  Nessun risultato")
    except Exception as e:
        print(f"  ✗ Errore: {e}")
    
    # Test 2: con to_tsvector (non richiede pg_trgm)
    print("\n2. Test con to_tsvector:")
    query2 = """
    SELECT nome_completo
    FROM catasto.possessore
    WHERE to_tsvector('italian', nome_completo) @@ to_tsquery('italian', 'ross:*')
    LIMIT 5;
    """
    
    try:
        with conn.cursor() as cur:
            cur.execute(query2)
            results = cur.fetchall()
            if results:
                print("Risultati trovati:")
                for row in results:
                    print(f"  - {row[0]}")
            else:
                print("  Nessun risultato")
    except Exception as e:
        print(f"  ✗ Errore: {e}")

def analizza_tabelle(conn):
    """Esegue ANALYZE sulle tabelle per aggiornare le statistiche."""
    print("\n=== ANALISI TABELLE ===")
    tabelle = ['possessore', 'localita', 'immobile', 'variazione', 'contratto', 'partita']
    
    for tabella in tabelle:
        try:
            with conn.cursor() as cur:
                cur.execute(f"ANALYZE catasto.{tabella};")
                conn.commit()
                print(f"✓ Analizzata tabella {tabella}")
        except Exception as e:
            print(f"✗ Errore analisi {tabella}: {e}")

def main():
    """Funzione principale."""
    print("VERIFICA SISTEMA RICERCA FUZZY CATASTO")
    print("=" * 50)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Connetti al database
    conn = connetti_db()
    
    try:
        # 1. Verifica pg_trgm
        pg_trgm_ok = verifica_estensione_pg_trgm(conn)
        
        # 2. Verifica indici esistenti
        verifica_indici_gin(conn)
        
        # 3. Verifica indici critici
        verifica_indici_mancanti(conn)
        
        # 4. Chiedi se creare indici mancanti
        risposta = input("\nVuoi creare gli indici mancanti? (s/n): ")
        if risposta.lower() == 's':
            crea_indici_mancanti(conn)
            
            # 5. Analizza tabelle
            print("\nAggiornamento statistiche...")
            analizza_tabelle(conn)
        
        # 6. Test ricerca
        risposta = input("\nVuoi testare la ricerca fuzzy? (s/n): ")
        if risposta.lower() == 's':
            test_ricerca_fuzzy(conn)
            
    finally:
        conn.close()
        
    print("\n" + "=" * 50)
    print("VERIFICA COMPLETATA")

if __name__ == "__main__":
    main()
