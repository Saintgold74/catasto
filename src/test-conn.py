import psycopg2

try:
    # Connessione al database con i parametri corretti
    conn = psycopg2.connect(
        dbname="catasto_storico",
        user="postgres",
        password="Markus74",  # Se richiesta
        host="localhost"
    )
    
    # Imposta autocommit a False (default) per gestire manualmente le transazioni
    conn.autocommit = False
    
    # Crea un cursore
    cur = conn.cursor()
    
    # Imposta lo schema
    cur.execute("SET search_path TO catasto")
    
    # Esegui le query di modifica
    cur.execute("INSERT INTO comune (nome, provincia, regione) VALUES ('TestPython', 'TestProv', 'TestReg')")
    
    # Conferma le modifiche
    conn.commit()
    
    print("Modifiche eseguite con successo!")
    
except Exception as e:
    # Gestisci eventuali errori
    print(f"Errore durante l'esecuzione: {e}")
    
    # Annulla le modifiche in caso di errore
    if 'conn' in locals() and conn is not None:
        conn.rollback()
        
finally:
    # Chiudi il cursore e la connessione
    if 'cur' in locals() and cur is not None:
        cur.close()
    if 'conn' in locals() and conn is not None:
        conn.close()