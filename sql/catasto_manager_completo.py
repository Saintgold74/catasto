import os
import sys
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date

import psycopg2
from psycopg2 import pool, sql, extras
import yaml
import dotenv

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("catasto.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CatastoConfigError(Exception):
    """Eccezione personalizzata per errori di configurazione"""
    pass

class CatastoManager:
    """
    Classe principale per la gestione del sistema catastale
    """
    _instance = None
    _connection_pool = None

    def __new__(cls, config_path=None):
        """
        Implementazione Singleton per gestire connessioni database
        """
        if not cls._instance:
            cls._instance = super(CatastoManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path=None):
        """
        Inizializzazione del manager con caricamento configurazioni
        """
        # Evita ri-inizializzazioni multiple
        if hasattr(self, '_initialized'):
            return
        
        # Carica configurazioni
        self.config = self._load_config(config_path)
        
        # Inizializza pool di connessioni
        self._initialize_connection_pool()
        
        # Flag per prevenire ri-inizializzazioni
        self._initialized = True
        
        logger.info("Istanza CatastoManager inizializzata")

    def _load_config(self, config_path=None) -> Dict:
        """
        Carica configurazioni da file o variabili d'ambiente
        """
        # Cerca configurazioni in ordine di priorità
        config = {}
        
        # 1. Variabili d'ambiente
        dotenv.load_dotenv()
        env_config = {
            'db_host': os.getenv('DB_HOST', 'localhost'),
            'db_port': os.getenv('DB_PORT', '5432'),
            'db_name': os.getenv('DB_NAME', 'catasto_storico'),
            'db_user': os.getenv('DB_USER', 'postgres'),
            'db_password': os.getenv('DB_PASSWORD', 'Markus74')
        }
        config.update(env_config)
        
        # 2. File di configurazione YAML
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as file:
                    yaml_config = yaml.safe_load(file)
                    config.update(yaml_config)
            except Exception as e:
                logger.warning(f"Errore caricamento configurazione YAML: {e}")
        
        # Verifica configurazione minima
        required_keys = ['db_host', 'db_port', 'db_name', 'db_user', 'db_password']
        for key in required_keys:
            if not config.get(key):
                raise CatastoConfigError(f"Configurazione mancante: {key}")
        
        return config

    def _initialize_connection_pool(self):
        """
        Inizializza pool di connessioni al database
        """
        try:
            self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # min connections
                20,  # max connections
                host=self.config['db_host'],
                port=self.config['db_port'],
                database=self.config['db_name'],
                user=self.config['db_user'],
                password=self.config['db_password']
            )
            logger.info("Pool di connessioni inizializzato")
        except Exception as e:
            logger.error(f"Errore inizializzazione pool connessioni: {e}")
            raise CatastoConfigError("Impossibile creare pool di connessioni")

    def get_connection(self):
        """
        Ottiene una connessione dal pool
        """
        if not self._connection_pool:
            raise CatastoConfigError("Pool connessioni non inizializzato")
        
        try:
            return self._connection_pool.getconn()
        except Exception as e:
            logger.error(f"Errore ottenimento connessione: {e}")
            raise

    def release_connection(self, connection):
        """
        Rilascia una connessione al pool
        """
        if self._connection_pool:
            self._connection_pool.putconn(connection)
        else:
            logger.warning("Tentativo di rilascio connessione su pool non inizializzato")

    def close_all_connections(self):
        """
        Chiude tutti i pool di connessioni
        """
        if self._connection_pool:
            self._connection_pool.closeall()
            logger.info("Tutte le connessioni chiuse")

    def esegui_query(self, query: str, params: tuple = None, fetch: str = 'all') -> List[Any]:
        """
        Esegue una query generica con gestione connessioni
        
        :param query: Query SQL da eseguire
        :param params: Parametri per query parametrizzata
        :param fetch: Modalità di recupero risultati ('all', 'one', 'none')
        :return: Risultati query
        """
        connection = None
        try:
            connection = self.get_connection()
            with connection.cursor(cursor_factory=extras.RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                
                if fetch == 'all':
                    return cursor.fetchall()
                elif fetch == 'one':
                    return cursor.fetchone()
                else:
                    connection.commit()
                    return []
        except psycopg2.Error as e:
            logger.error(f"Errore esecuzione query: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                self.release_connection(connection)

    def registra_proprieta(self, dati_proprieta: Dict) -> int:
        """
        Registra una nuova proprietà con gestione transazionale
        
        :param dati_proprieta: Dizionario con dati proprietà
        :return: ID della nuova partita
        """
        connection = None
        try:
            connection = self.get_connection()
            connection.autocommit = False
            
            with connection.cursor() as cursor:
                # Inserimento partita
                cursor.execute("""
                    INSERT INTO catasto.partita 
                    (comune_nome, numero_partita, tipo, data_impianto, stato)
                    VALUES (%s, %s, 'principale', %s, 'attiva')
                    RETURNING id
                """, (
                    dati_proprieta['comune'],
                    dati_proprieta['numero_partita'],
                    dati_proprieta.get('data_impianto', date.today())
                ))
                partita_id = cursor.fetchone()[0]

                # Inserimento possessori
                for possessore in dati_proprieta.get('possessori', []):
                    cursor.execute("""
                        INSERT INTO catasto.possessore 
                        (comune_nome, nome_completo, cognome_nome, attivo)
                        VALUES (%s, %s, %s, true)
                        ON CONFLICT (nome_completo) DO NOTHING
                        RETURNING id
                    """, (
                        dati_proprieta['comune'],
                        possessore['nome_completo'],
                        possessore['nome_completo'].split()[0]
                    ))
                    
                    # Collega possessore alla partita
                    cursor.execute("""
                        INSERT INTO catasto.partita_possessore 
                        (partita_id, possessore_id, tipo_partita, titolo, quota)
                        VALUES (%s, 
                                COALESCE(
                                    (SELECT id FROM catasto.possessore 
                                     WHERE nome_completo = %s), 
                                    NULL
                                ), 
                                'principale', 
                                'proprietà esclusiva', 
                                %s)
                    """, (
                        partita_id, 
                        possessore['nome_completo'],
                        possessore.get('quota')
                    ))

                # Inserimento immobili
                for immobile in dati_proprieta.get('immobili', []):
                    # Trova o crea località
                    cursor.execute("""
                        INSERT INTO catasto.localita 
                        (comune_nome, nome, tipo) 
                        VALUES (%s, %s, 'regione')
                        ON CONFLICT (comune_nome, nome) DO NOTHING
                        RETURNING id
                    """, (
                        dati_proprieta['comune'], 
                        immobile['localita']
                    ))
                    
                    # Recupera ID località
                    cursor.execute("""
                        SELECT id FROM catasto.localita 
                        WHERE comune_nome = %s AND nome = %s
                    """, (
                        dati_proprieta['comune'], 
                        immobile['localita']
                    ))
                    localita_id = cursor.fetchone()[0]

                    # Inserimento immobile
                    cursor.execute("""
                        INSERT INTO catasto.immobile 
                        (partita_id, localita_id, natura, classificazione)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        partita_id,
                        localita_id,
                        immobile['natura'],
                        immobile.get('classificazione')
                    ))

                # Commit transazione
                connection.commit()
                logger.info(f"Proprietà registrata con successo. ID Partita: {partita_id}")
                return partita_id

        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Errore durante registrazione proprietà: {e}")
            raise
        finally:
            if connection:
                self.release_connection(connection)

    def cerca_proprieta(self, filtri: Optional[Dict] = None) -> List[Dict]:
        """
        Ricerca proprietà con filtri dinamici
        
        :param filtri: Dizionario con criteri di ricerca
        :return: Lista di proprietà che soddisfano i criteri
        """
        query = """
            SELECT 
                p.id, 
                p.comune_nome, 
                p.numero_partita, 
                p.data_impianto,
                p.stato,
                string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
                COUNT(DISTINCT i.id) AS num_immobili
            FROM catasto.partita p
            LEFT JOIN catasto.partita_possessore pp ON p.id = pp.partita_id
            LEFT JOIN catasto.possessore pos ON pp.possessore_id = pos.id
            LEFT JOIN catasto.immobile i ON p.id = i.partita_id
            WHERE 1=1
        """
        
        params = []
        
        # Costruzione filtri dinamici
        if filtri:
            if 'comune' in filtri:
                query += " AND p.comune_nome = %s"
                params.append(filtri['comune'])
            
            if 'numero_partita' in filtri:
                query += " AND p.numero_partita = %s"
                params.append(filtri['numero_partita'])
            
            if 'data_inizio' in filtri:
                query += " AND p.data_impianto >= %s"
                params.append(filtri['data_inizio'])
            
            if 'data_fine' in filtri:
                query += " AND p.data_impianto <= %s"
                params.append(filtri['data_fine'])
        
        query += " GROUP BY p.id ORDER BY p.data_impianto DESC"
        
        return self.esegui_query(query, tuple(params))

    def __del__(self):
        """
        Distruttore per chiusura connessioni
        """
        try:
            self.close_all_connections()
        except Exception as e:
            logger.error(f"Errore durante chiusura connessioni: {e}")

# Esempio di utilizzo
def main():
    try:
        # Inizializza manager (può usare file .env o config YAML)
        manager = CatastoManager()

        # Esempio registrazione proprietà
        nuova_proprieta = {
            'comune': 'Carcare',
            'numero_partita': 302,
            'data_impianto': date.today(),
            'possessori': [
                {'nome_completo': 'Mario Rossi', 'quota': '1/2'},
                {'nome_completo': 'Luigi Bianchi', 'quota': '1/2'}
            ],
            'immobili': [
                {
                    'natura': 'Casa',
                    'localita': 'Via Roma',
                    'classificazione': 'Abitazione civile'
                }
            ]
        }

        # Registra nuova proprietà
        nuova_partita_id = manager.registra_proprieta(nuova_proprieta)
        print(f"Nuova partita registrata: {nuova_partita_id}")

        # Ricerca proprietà
        risultati = manager.cerca_proprieta({'comune': 'Carcare'})
        for proprieta in risultati:
            print(proprieta)

    except Exception as e:
        logger.error(f"Errore durante l'esecuzione: {e}")

if __name__ == "__main__":
    main()
