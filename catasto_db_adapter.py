
# ========================================================================
# ADAPTER DI COMPATIBILITÀ PER CATASTO DB MANAGER
# File: catasto_db_adapter.py
# ========================================================================

"""
Adapter per rendere compatibile CatastoDBManager con la ricerca fuzzy ampliata.
"""

import logging
import psycopg2.extras
from contextlib import contextmanager

class CatastoDBAdapter:
    """Adapter per CatastoDBManager esistente."""
    
    def __init__(self, original_db_manager):
        self.original_db_manager = original_db_manager
        self.logger = logging.getLogger(__name__)
        
    @contextmanager
    def get_connection(self):
        """Ottiene una connessione dal pool esistente."""
        conn = None
        try:
            if hasattr(self.original_db_manager, 'pool') and self.original_db_manager.pool:
                conn = self.original_db_manager.pool.getconn()
                yield conn
            else:
                raise Exception("Pool di connessioni non disponibile")
        except Exception as e:
            self.logger.error(f"Errore connessione database: {e}")
            raise
        finally:
            if conn and hasattr(self.original_db_manager, 'pool'):
                self.original_db_manager.pool.putconn(conn)
    
    def execute_query(self, query, params=None):
        """Esegue una query."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    if query.strip().upper().startswith('SELECT'):
                        return cursor.fetchall()
                    else:
                        conn.commit()
                        return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Errore esecuzione query: {e}")
            raise

def adapt_db_manager_for_fuzzy_search(db_manager):
    """Adatta il db_manager per la ricerca fuzzy."""
    
    # Se ha già get_connection, non serve adapter
    if hasattr(db_manager, 'get_connection'):
        return db_manager
    
    # Crea l'adapter
    adapter = CatastoDBAdapter(db_manager)
    
    # Copia i metodi dell'adapter nel db_manager originale
    db_manager.get_connection = adapter.get_connection
    db_manager.execute_query = adapter.execute_query
    
    return db_manager
