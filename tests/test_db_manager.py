# tests/test_db_manager.py

import pytest
from catasto_db_manager import CatastoDBManager
import psycopg2 # Assicurati sia installato

# --- CONFIGURAZIONE DATABASE DI TEST ---
# Aggiorna questi valori con le tue credenziali reali per il DB di TEST
TEST_DB_PARAMS = {
    "dbname": "catasto_test_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

def test_add_and_get_possessore():
    """
    Test di integrazione per aggiungere e poi recuperare un possessore.
    """
    # --- 1. ARRANGE ---
    
    # LA CORREZIONE È QUI:
    # Usiamo ** per "spacchettare" il dizionario TEST_DB_PARAMS in argomenti
    # con nome che corrispondono a quelli attesi da __init__ della classe.
    # Python leggerà questo come:
    # CatastoDBManager(dbname="catasto_test_db", user="postgres", ...)
    try:
        db_manager = CatastoDBManager(**TEST_DB_PARAMS)
        conn = db_manager._get_connection()
    except psycopg2.OperationalError as e:
        pytest.fail(f"Impossibile connettersi al database di test '{TEST_DB_PARAMS['dbname']}'. "
                    f"Assicurati che il database esista, che il server sia in esecuzione e che le credenziali siano corrette. Errore: {e}")


    cognome_test = "RossiTest"
    nome_test = "MarioTest"
    cf_test = "RSSMRITESTCF123"

    # --- 2. ACT ---
    try:
        with conn.cursor() as cur:
            # Pulisce eventuali dati sporchi da esecuzioni precedenti
            cur.execute("DELETE FROM possessori WHERE codice_fiscale = %s", (cf_test,))
            
            cur.execute(
                "INSERT INTO possessori (cognome, nome, codice_fiscale, data_nascita) VALUES (%s, %s, %s, '1980-01-01') RETURNING id",
                (cognome_test, nome_test, cf_test)
            )
            possessore_id_test = cur.fetchone()[0]
            conn.commit()
    except Exception as e:
        conn.rollback()
        pytest.fail(f"Errore durante l'inserimento dei dati di test nel DB: {e}")


    possessore_recuperato = db_manager.get_possessore_by_id(possessore_id_test)

    # --- 3. ASSERT ---
    assert possessore_recuperato is not None, "Il possessore non è stato trovato."
    assert possessore_recuperato['id'] == possessore_id_test
    assert possessore_recuperato['cognome'] == cognome_test
    
    # --- Teardown (Pulizia) ---
    with conn.cursor() as cur:
        cur.execute("DELETE FROM possessori WHERE id = %s", (possessore_id_test,))
        conn.commit()
    
    db_manager._release_connection(conn)


def test_get_non_existent_possessore():
    """
    Testa che la ricerca di un ID non esistente restituisca None.
    """
    try:
        db_manager = CatastoDBManager(**TEST_DB_PARAMS)
    except psycopg2.OperationalError as e:
        pytest.fail(f"Impossibile connettersi al database di test. Errore: {e}")

    id_inesistente = -99999
    risultato = db_manager.get_possessore_by_id(id_inesistente)
    
    assert risultato is None
