#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestore Database Catasto Storico - Versione Migliorata
=====================================================
Script per la gestione del database catastale con supporto
per operazioni CRUD e chiamate alle stored procedure.

Include miglioramenti per sicurezza (bcrypt) e gestione errori.

Autore: Marco Santoro
Data: 24/04/2025
"""

import psycopg2
import psycopg2.extras
import psycopg2.errors # +++ ADDED +++ Per errori specifici
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
import sys
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import bcrypt # +++ ADDED +++ Per hashing password
import json # Necessario per export JSON

# Configurazione logging (invariata)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("catasto_db.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CatastoDB")

class CatastoDBManager:
    """Classe per la gestione delle operazioni sul database catastale."""

    # --- MODIFIED __init__ ---
    # Rimuovi i valori di default hardcoded per le credenziali
    def __init__(self, dbname: str, user: str, password: str,
                 host: str, port: int, schema: str = "catasto"):
        """
        Inizializza la connessione al database.
        Le credenziali ora sono passate obbligatoriamente.
        """
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.schema = schema
        self.conn = None
        self.cursor = None
        logger.info(f"Inizializzato gestore per database {dbname} schema {schema}")
    
    # --- MODIFIED connect ---
    def connect(self) -> bool:
        """Stabilisce la connessione al database utilizzando gli attributi della classe."""
        if self.conn is not None and not self.conn.closed:
            # logger.debug("Connessione già attiva.") # Debug opzionale
            return True
        try:
            logger.info(f"Tentativo di connessione a {self.dbname} su {self.host}:{self.port}...")
            # Usa gli attributi individuali per la connessione
            self.conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            self.conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
            self.conn.autocommit = False # Assicurati che autocommit sia False di default
            # Imposta lo schema di ricerca (opzionale ma buona pratica)
            with self.conn.cursor() as cur:
                 cur.execute(f"SET search_path TO {self.schema}, public;")

            # Crea un cursore predefinito (opzionale, si può creare al bisogno)
            # self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            logger.info("Connessione stabilita con successo")
            return True
        except psycopg2.OperationalError as e:
            logger.error(f"Errore operativo durante la connessione: {e}")
            self.conn = None
            # self.cursor = None
            return False
        except Exception as e:
            logger.error(f"Errore generico durante la connessione: {e}")
            self.conn = None
            # self.cursor = None
            return False
    # --- FINE MODIFIED connect ---
    
    def disconnect(self):
        """Chiude la connessione al database."""
        try:
            if self.cur:
                self.cur.close()
            if self.conn:
                self.conn.close()
            logger.info("Disconnessione completata")
        except Exception as e:
            logger.error(f"Errore durante la disconnessione: {e}")
    
    def commit(self):
        """Conferma le modifiche al database."""
        if self.conn:
            self.conn.commit()
            logger.info("Commit transazione avvenuto con successo")
    
    def rollback(self):
        """Annulla le modifiche al database."""
        if self.conn:
            self.conn.rollback()
            logger.info("Rollback transazione avvenuto con successo")
    
    def execute_query(self, query: str, params: tuple = None) -> bool:
        """
        Esegue una query SQL.
        
        Args:
            query: Query SQL da eseguire
            params: Parametri per la query
            
        Returns:
            bool: True se l'esecuzione è avvenuta con successo, False altrimenti
        """
        try:
            if not self.conn or self.conn.closed:
                if not self.connect():
                    return False
            
            self.cur.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"Errore durante l'esecuzione della query: {e}\nQuery: {query}\nParametri: {params}")
            self.rollback()
            return False
    
    def fetchall(self) -> List[Dict]:
        """
        Recupera tutti i risultati dell'ultima query.
        
        Returns:
            List[Dict]: Lista di dizionari con i risultati
        """
        if self.cur:
            return [dict(row) for row in self.cur.fetchall()]
        return []
    
    def fetchone(self) -> Optional[Dict]:
        """
        Recupera una riga di risultati dall'ultima query.
        
        Returns:
            Optional[Dict]: Dizionario con il risultato o None
        """
        if self.cur:
            row = self.cur.fetchone()
            return dict(row) if row else None
        return None
    
    # OPERAZIONI CRUD
    
    def get_comuni(self, search_term=None) -> List[Dict]:
        """
        Recupera tutti i comuni dal database, con opzione di ricerca parziale e case-insensitive.
        
        Args:
            search_term: Termine di ricerca opzionale (ricerca parziale, case-insensitive)
            
        Returns:
            List[Dict]: Lista di comuni
        """
        if search_term:
            # Assicuriamoci di aggiungere i wildcards % esplicitamente per la ricerca parziale
            pattern = f"%{search_term}%"
            query = "SELECT nome, provincia, regione FROM comune WHERE nome ILIKE %s ORDER BY nome"
            logger.info(f"Ricerca comuni con pattern: {pattern}")
            if self.execute_query(query, (pattern,)):
                result = self.fetchall()
                logger.info(f"Trovati {len(result)} comuni")
                return result
        else:
            query = "SELECT nome, provincia, regione FROM comune ORDER BY nome"
            if self.execute_query(query):
                return self.fetchall()
        return []

    def check_possessore_exists(self, nome_completo: str, comune_nome: str = None) -> Optional[int]:
        """
        Verifica se un possessore esiste nel database e restituisce il suo ID.
        
        Args:
            nome_completo: Nome completo del possessore
            comune_nome: Nome del comune (opzionale)
            
        Returns:
            Optional[int]: ID del possessore se esiste, None altrimenti
        """
        if comune_nome:
            query = "SELECT id FROM possessore WHERE nome_completo ILIKE %s AND comune_nome = %s"
            if self.execute_query(query, (nome_completo, comune_nome)):
                result = self.fetchone()
                return result['id'] if result else None
        else:
            query = "SELECT id FROM possessore WHERE nome_completo ILIKE %s"
            if self.execute_query(query, (nome_completo,)):
                result = self.fetchone()
                return result['id'] if result else None
        return None
    
    def get_possessori_by_comune(self, comune_nome: str) -> List[Dict]:
        """
        Recupera tutti i possessori di un comune, con ricerca parziale e case-insensitive.
        
        Args:
            comune_nome: Nome del comune (anche parziale)
            
        Returns:
            List[Dict]: Lista di possessori
        """
        # Assicuriamoci di aggiungere i wildcards % esplicitamente per la ricerca parziale
        pattern = f"%{comune_nome}%"
        
        query = "SELECT * FROM possessore WHERE comune_nome ILIKE %s ORDER BY nome_completo"
        logger.info(f"Ricerca possessori per comune con pattern: {pattern}")
        if self.execute_query(query, (pattern,)):
            result = self.fetchall()
            logger.info(f"Trovati {len(result)} possessori")
            return result
        
        logger.info("Nessun possessore trovato o errore nella query")
        return []
    
    def get_partite_by_comune(self, comune_nome: str) -> List[Dict]:
        """
        Recupera tutte le partite di un comune, con ricerca parziale e case-insensitive.
        
        Args:
            comune_nome: Nome del comune (anche parziale)
            
        Returns:
            List[Dict]: Lista di partite
        """
        # Assicuriamoci di aggiungere i wildcards % esplicitamente per la ricerca parziale
        pattern = f"%{comune_nome}%"
        
        query = """
        SELECT p.*, 
            string_agg(DISTINCT pos.nome_completo, ', ') as possessori,
            COUNT(DISTINCT i.id) as num_immobili
        FROM partita p
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        LEFT JOIN immobile i ON p.id = i.partita_id
        WHERE p.comune_nome ILIKE %s
        GROUP BY p.id
        ORDER BY p.numero_partita
        """
        
        logger.info(f"Ricerca partite per comune con pattern: {pattern}")
        if self.execute_query(query, (pattern,)):
            result = self.fetchall()
            logger.info(f"Trovate {len(result)} partite")
            return result
        
        logger.info("Nessuna partita trovata o errore nella query")
        return []
    
    def get_partita_details(self, partita_id: int) -> Dict[str, Any]:
        """
        Recupera i dettagli completi di una partita.
        
        Args:
            partita_id: ID della partita
            
        Returns:
            Dict: Dettagli della partita
        """
        # Recupera dati base della partita
        query_partita = """
        SELECT * FROM partita WHERE id = %s
        """
        if not self.execute_query(query_partita, (partita_id,)):
            return {}
        
        partita = self.fetchone()
        if not partita:
            return {}
        
        # Recupera possessori
        query_possessori = """
        SELECT pos.*, pp.titolo, pp.quota
        FROM possessore pos
        JOIN partita_possessore pp ON pos.id = pp.possessore_id
        WHERE pp.partita_id = %s
        """
        self.execute_query(query_possessori, (partita_id,))
        partita['possessori'] = self.fetchall()
        
        # Recupera immobili (modificato per includere tipologia)
        query_immobili = """
        SELECT i.*, l.nome as localita_nome, l.tipo as localita_tipo
        FROM immobile i
        JOIN localita l ON i.localita_id = l.id
        WHERE i.partita_id = %s
        """
        self.execute_query(query_immobili, (partita_id,))
        immobili = self.fetchall()
        
        # Aggiungi la tipologia per ogni immobile (se esiste in tabella di metadati)
        for immobile in immobili:
            # Se esiste una tabella di metadati, recuperiamo la tipologia
            # Questo è un esempio - adatta alla struttura reale del database
            try:
                self.execute_query(
                    "SELECT tipologia FROM immobile_metadati WHERE immobile_id = %s",
                    (immobile['id'],)
                )
                result = self.fetchone()
                if result:
                    immobile['tipologia'] = result['tipologia']
                else:
                    immobile['tipologia'] = None
            except:
                # Se la tabella non esiste o altri errori, ignoriamo
                immobile['tipologia'] = None
        
        partita['immobili'] = immobili
        
        # Recupera variazioni
        query_variazioni = """
        SELECT v.*, c.tipo as tipo_contratto, c.data_contratto, 
               c.notaio, c.repertorio, c.note
        FROM variazione v
        LEFT JOIN contratto c ON v.id = c.variazione_id
        WHERE v.partita_origine_id = %s OR v.partita_destinazione_id = %s
        """
        self.execute_query(query_variazioni, (partita_id, partita_id))
        partita['variazioni'] = self.fetchall()
        
        return partita
    
    def search_partite(self, comune_nome: str = None, numero_partita: int = None, 
                      possessore: str = None, immobile_natura: str = None) -> List[Dict]:
        """
        Ricerca partite in base a vari criteri.
        
        Args:
            comune_nome: Nome del comune
            numero_partita: Numero della partita
            possessore: Nome del possessore
            immobile_natura: Natura dell'immobile
            
        Returns:
            List[Dict]: Lista di partite che soddisfano i criteri
        """
        conditions = []
        params = []
        
        query = """
        SELECT DISTINCT p.*
        FROM partita p
        """
        
        if possessore:
            query += """
            LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
            LEFT JOIN possessore pos ON pp.possessore_id = pos.id
            """
            conditions.append("pos.nome_completo ILIKE %s")
            params.append(f"%{possessore}%")
        
        if immobile_natura:
            query += """
            LEFT JOIN immobile i ON p.id = i.partita_id
            """
            conditions.append("i.natura ILIKE %s")
            params.append(f"%{immobile_natura}%")
        
        if comune_nome:
            conditions.append("p.comune_nome ILIKE %s")
            params.append(f"%{comune_nome}%")
        
        if numero_partita:
            conditions.append("p.numero_partita = %s")
            params.append(numero_partita)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY p.comune_nome, p.numero_partita"
        
        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []
    
    def insert_possessore(self, comune_nome: str, cognome_nome: str, paternita: str,
                        nome_completo: str, attivo: bool = True) -> Optional[int]:
        """
        Inserisce un nuovo possessore nel database.
        
        Args:
            comune_nome: Nome del comune
            cognome_nome: Cognome e nome
            paternita: Paternità
            nome_completo: Nome completo
            attivo: Stato di attività
            
        Returns:
            Optional[int]: ID del nuovo possessore, None in caso di errore
        """
        try:
            if self.execute_query(
                "CALL inserisci_possessore(%s, %s, %s, %s, %s)",
                (comune_nome, cognome_nome, paternita, nome_completo, attivo)
            ):
                self.commit()
                
                # Recupera l'ID del possessore inserito
                if self.execute_query(
                    "SELECT id FROM possessore WHERE comune_nome = %s AND nome_completo = %s",
                    (comune_nome, nome_completo)
                ):
                    result = self.fetchone()
                    return result['id'] if result else None
                
                return None
            return None
        except Exception as e:
            logger.error(f"Errore durante inserimento possessore: {e}")
            self.rollback()
            return None
    
    def insert_localita(self, comune_nome: str, nome: str, tipo: str,
                      civico: int = None) -> Optional[int]:
        """
        Inserisce una nuova località nel database.
        
        Args:
            comune_nome: Nome del comune
            nome: Nome della località
            tipo: Tipo della località (regione, via, borgata)
            civico: Numero civico (opzionale)
            
        Returns:
            Optional[int]: ID della nuova località, None in caso di errore
        """
        try:
            query = """
            INSERT INTO localita (comune_nome, nome, tipo, civico) 
            VALUES (%s, %s, %s, %s) 
            RETURNING id
            """
            if self.execute_query(query, (comune_nome, nome, tipo, civico)):
                result = self.fetchone()
                self.commit()
                return result['id'] if result else None
            return None
        except Exception as e:
            logger.error(f"Errore durante inserimento localita: {e}")
            self.rollback()
            return None
    
    # CHIAMATE ALLE STORED PROCEDURE
    
    def registra_nuova_proprieta(self, comune_nome: str, numero_partita: int, 
                               data_impianto: date, possessori: List[Dict], 
                               immobili: List[Dict]) -> bool:
        """
        Registra una nuova proprietà utilizzando la stored procedure originale.
        
        Args:
            comune_nome: Nome del comune
            numero_partita: Numero della partita
            data_impianto: Data di impianto
            possessori: Lista di possessori con informazioni
            immobili: Lista di immobili con informazioni
            
        Returns:
            bool: True se l'operazione è avvenuta con successo, False altrimenti
        """
        try:
            import json
            call_proc = """
            CALL registra_nuova_proprieta(%s, %s, %s, %s, %s)
            """
            
            possessori_json = json.dumps(possessori)
            immobili_json = json.dumps(immobili)
            
            success = self.execute_query(call_proc, (
                comune_nome, 
                numero_partita, 
                data_impianto, 
                possessori_json, 
                immobili_json
            ))
            
            if success:
                self.commit()
                logger.info(f"Registrata nuova proprietà: {comune_nome}, partita {numero_partita}")
            
            return success
        except Exception as e:
            logger.error(f"Errore durante la registrazione della proprietà: {e}")
            self.rollback()
            return False
    
    def registra_nuova_proprieta_v2(self, comune_nome: str, numero_partita: int, 
                                 data_impianto: date, possessori: List[Dict], 
                                 immobili: List[Dict]) -> bool:
        """
        Registra una nuova proprietà con supporto per tipologia immobile e ID località.
        
        Args:
            comune_nome: Nome del comune
            numero_partita: Numero della partita
            data_impianto: Data di impianto
            possessori: Lista di possessori con informazioni
            immobili: Lista di immobili con informazioni (inclusa tipologia e localita_id)
            
        Returns:
            bool: True se l'operazione è avvenuta con successo, False altrimenti
        """
        try:
            # Inizia una transazione
            self.conn.autocommit = False
            
            # 1. Crea la partita
            query_partita = """
            INSERT INTO partita (comune_nome, numero_partita, tipo, data_impianto, stato)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """
            
            if not self.execute_query(query_partita, (
                comune_nome, numero_partita, 'principale', data_impianto, 'attiva'
            )):
                raise Exception("Errore durante l'inserimento della partita")
            
            partita_result = self.fetchone()
            if not partita_result:
                raise Exception("Nessun ID partita restituito")
            
            partita_id = partita_result['id']
            
            # 2. Inserisci o collega i possessori
            for possessore in possessori:
                # Verifica se il possessore esiste già
                possessore_id = self.check_possessore_exists(possessore["nome_completo"], comune_nome)
                
                if not possessore_id:
                    # Inserisci nuovo possessore
                    query_possessore = """
                    INSERT INTO possessore (comune_nome, cognome_nome, paternita, nome_completo, attivo)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """
                    
                    if not self.execute_query(query_possessore, (
                        comune_nome, 
                        possessore.get('cognome_nome', possessore["nome_completo"]),
                        possessore.get('paternita', ''),
                        possessore["nome_completo"],
                        True
                    )):
                        raise Exception(f"Errore durante l'inserimento del possessore {possessore['nome_completo']}")
                    
                    possessore_result = self.fetchone()
                    if not possessore_result:
                        raise Exception(f"Nessun ID possessore restituito per {possessore['nome_completo']}")
                    
                    possessore_id = possessore_result['id']
                
                # Collega possessore alla partita
                titolo = 'comproprietà' if 'quota' in possessore else 'proprietà esclusiva'
                quota = possessore.get('quota', None)
                
                query_collega = """
                INSERT INTO partita_possessore (partita_id, possessore_id, tipo_partita, titolo, quota)
                VALUES (%s, %s, %s, %s, %s)
                """
                
                if not self.execute_query(query_collega, (
                    partita_id, possessore_id, 'principale', titolo, quota
                )):
                    raise Exception(f"Errore durante il collegamento del possessore alla partita")
            
            # 3. Inserisci gli immobili
            for immobile in immobili:
                localita_id = immobile.get('localita_id', None)
                
                # Se non c'è l'ID della località ma ci sono altre informazioni, cerca di ottenerlo
                if not localita_id and 'localita' in immobile:
                    query_localita = """
                    SELECT id FROM localita 
                    WHERE comune_nome = %s AND nome = %s AND tipo = %s
                    LIMIT 1
                    """
                    
                    tipo_localita = immobile.get('tipo_localita', 'via')
                    
                    if self.execute_query(query_localita, (
                        comune_nome, immobile['localita'], tipo_localita
                    )):
                        localita_result = self.fetchone()
                        if localita_result:
                            localita_id = localita_result['id']
                
                # Se ancora non abbiamo un ID valido per la località, creane una nuova
                if not localita_id and 'localita' in immobile:
                    # Crea nuova località
                    tipo_localita = immobile.get('tipo_localita', 'via')
                    civico = immobile.get('civico', None)
                    
                    query_insert_localita = """
                    INSERT INTO localita (comune_nome, nome, tipo, civico)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """
                    
                    if not self.execute_query(query_insert_localita, (
                        comune_nome, immobile['localita'], tipo_localita, civico
                    )):
                        raise Exception(f"Errore durante l'inserimento della localita {immobile['localita']}")
                    
                    localita_result = self.fetchone()
                    if not localita_result:
                        raise Exception(f"Nessun ID localita restituito per {immobile['localita']}")
                    
                    localita_id = localita_result['id']
                
                if not localita_id:
                    raise Exception("Localita non specificata per l'immobile")
                
                # Inserisci l'immobile
                query_immobile = """
                INSERT INTO immobile (partita_id, localita_id, natura, numero_piani, numero_vani, consistenza, classificazione)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """
                
                if not self.execute_query(query_immobile, (
                    partita_id,
                    localita_id,
                    immobile['natura'],
                    immobile.get('numero_piani', None),
                    immobile.get('numero_vani', None),
                    immobile.get('consistenza', None),
                    immobile.get('classificazione', None)
                )):
                    raise Exception(f"Errore durante l'inserimento dell'immobile {immobile['natura']}")
                
                immobile_result = self.fetchone()
                if not immobile_result:
                    raise Exception(f"Nessun ID immobile restituito per {immobile['natura']}")
                
                immobile_id = immobile_result['id']
                
                # Se è specificata la tipologia, inseriscila nei metadati
                if 'tipologia' in immobile and immobile['tipologia']:
                    # Verifica se esiste la tabella dei metadati, altrimenti creala
                    try:
                        self.execute_query("""
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name = 'immobile_metadati'
                        """, (self.schema,))
                        
                        table_exists = bool(self.fetchone())
                        
                        if not table_exists:
                            # Crea la tabella dei metadati
                            self.execute_query("""
                            CREATE TABLE immobile_metadati (
                                immobile_id INTEGER PRIMARY KEY REFERENCES immobile(id) ON DELETE CASCADE,
                                tipologia VARCHAR(100),
                                metadati_aggiuntivi JSONB,
                                data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                            """)
                        
                        # Inserisci i metadati
                        self.execute_query("""
                        INSERT INTO immobile_metadati (immobile_id, tipologia)
                        VALUES (%s, %s)
                        ON CONFLICT (immobile_id) DO UPDATE SET tipologia = EXCLUDED.tipologia
                        """, (immobile_id, immobile['tipologia']))
                        
                    except Exception as e:
                        logger.warning(f"Impossibile salvare la tipologia dell'immobile: {e}")
                        # Continuiamo comunque, non è un errore critico
            
            # Conferma la transazione
            self.commit()
            logger.info(f"Registrata nuova proprietà: {comune_nome}, partita {numero_partita}")
            return True
            
        except Exception as e:
            logger.error(f"Errore durante la registrazione della proprietà: {e}")
            self.rollback()
            return False
        finally:
            # Ripristina l'autocommit
            self.conn.autocommit = True
    
    def registra_passaggio_proprieta(self, partita_origine_id: int, comune_nome: str, 
                                   numero_partita: int, tipo_variazione: str, 
                                   data_variazione: date, tipo_contratto: str, 
                                   data_contratto: date, **kwargs) -> bool:
        """
        Registra un passaggio di proprietà utilizzando la stored procedure.
        
        Args:
            partita_origine_id: ID della partita di origine
            comune_nome: Nome del comune
            numero_partita: Numero della nuova partita
            tipo_variazione: Tipo di variazione
            data_variazione: Data della variazione
            tipo_contratto: Tipo di contratto
            data_contratto: Data del contratto
            **kwargs: Altri parametri opzionali
            
        Returns:
            bool: True se l'operazione è avvenuta con successo, False altrimenti
        """
        try:
            import json
            
            # Parametri opzionali
            notaio = kwargs.get('notaio')
            repertorio = kwargs.get('repertorio')
            nuovi_possessori = kwargs.get('nuovi_possessori')
            immobili_da_trasferire = kwargs.get('immobili_da_trasferire')
            note = kwargs.get('note')
            
            # Converte in JSON se necessario
            if nuovi_possessori and not isinstance(nuovi_possessori, str):
                nuovi_possessori = json.dumps(nuovi_possessori)
            
            call_proc = """
            CALL registra_passaggio_proprieta(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            success = self.execute_query(call_proc, (
                partita_origine_id,
                comune_nome,
                numero_partita,
                tipo_variazione,
                data_variazione,
                tipo_contratto,
                data_contratto,
                notaio,
                repertorio,
                nuovi_possessori,
                immobili_da_trasferire,
                note
            ))
            
            if success:
                self.commit()
                logger.info(f"Registrato passaggio di proprietà: origine {partita_origine_id}, nuova partita {numero_partita}")
            
            return success
        except Exception as e:
            logger.error(f"Errore durante la registrazione del passaggio di proprietà: {e}")
            self.rollback()
            return False
    
    def registra_consultazione(self, data: date, richiedente: str, 
                             documento_identita: str, motivazione: str,
                             materiale_consultato: str, 
                             funzionario_autorizzante: str) -> bool:
        """
        Registra una consultazione utilizzando la stored procedure.
        
        Args:
            data: Data della consultazione
            richiedente: Nome del richiedente
            documento_identita: Documento d'identità
            motivazione: Motivazione della consultazione
            materiale_consultato: Materiale consultato
            funzionario_autorizzante: Funzionario che ha autorizzato
            
        Returns:
            bool: True se l'operazione è avvenuta con successo, False altrimenti
        """
        try:
            call_proc = """
            CALL registra_consultazione(%s, %s, %s, %s, %s, %s)
            """
            
            success = self.execute_query(call_proc, (
                data, 
                richiedente, 
                documento_identita, 
                motivazione, 
                materiale_consultato, 
                funzionario_autorizzante
            ))
            
            if success:
                self.commit()
                logger.info(f"Registrata consultazione: {richiedente}, {data}")
            
            return success
        except Exception as e:
            logger.error(f"Errore durante la registrazione della consultazione: {e}")
            self.rollback()
            return False
    
    def genera_certificato_proprieta(self, partita_id: int) -> str:
        """
        Genera un certificato di proprietà utilizzando la funzione.
        
        Args:
            partita_id: ID della partita
            
        Returns:
            str: Certificato di proprietà in formato testo
        """
        query = """
        SELECT genera_certificato_proprieta(%s) AS certificato
        """
        
        if self.execute_query(query, (partita_id,)):
            result = self.fetchone()
            return result.get('certificato', '') if result else ''
        return ''
    
    def genera_report_genealogico(self, partita_id: int) -> str:
        """
        Genera un report genealogico utilizzando la funzione.
        
        Args:
            partita_id: ID della partita
            
        Returns:
            str: Report genealogico in formato testo
        """
        query = """
        SELECT genera_report_genealogico(%s) AS report
        """
        
        if self.execute_query(query, (partita_id,)):
            result = self.fetchone()
            return result.get('report', '') if result else ''
        return ''
    
    def genera_report_possessore(self, possessore_id: int) -> str:
        """
        Genera un report possessore utilizzando la funzione.
        
        Args:
            possessore_id: ID del possessore
            
        Returns:
            str: Report possessore in formato testo
        """
        query = """
        SELECT genera_report_possessore(%s) AS report
        """
        
        if self.execute_query(query, (possessore_id,)):
            result = self.fetchone()
            return result.get('report', '') if result else ''
        return ''
    
    def genera_report_consultazioni(self, data_inizio=None, data_fine=None, richiedente=None) -> str:
        """
        Genera un report delle consultazioni filtrato per data e/o richiedente
        
        Args:
            data_inizio: Data inizio filtro (opzionale)
            data_fine: Data fine filtro (opzionale)
            richiedente: Nome richiedente per filtro (opzionale)
            
        Returns:
            str: Report formattato
        """
        # Costruisci i parametri
        params = []
        
        if data_inizio is not None:
            params.append(data_inizio)
        else:
            params.append(None)
            
        if data_fine is not None:
            params.append(data_fine)
        else:
            params.append(None)
            
        if richiedente is not None:
            params.append(richiedente)
        else:
            params.append(None)
        
        # Chiama la funzione SQL
        query = """
        SELECT genera_report_consultazioni(%s, %s, %s) AS report
        """
        
        if self.execute_query(query, tuple(params)):
            result = self.fetchone()
            return result.get('report', '') if result else ''
        return ''
    def verifica_integrita_database(self) -> Tuple[bool, str]:
        """
        Verifica l'integrità del database utilizzando la procedura.
        
        Returns:
            Tuple[bool, str]: Tuple con stato e messaggio
        """
        # Crea una tabella temporanea per ottenere l'output
        self.execute_query("DROP TABLE IF EXISTS temp_output")
        self.execute_query("CREATE TEMP TABLE temp_output (message TEXT)")
        
        # Cattura l'output della procedura
        self.execute_query("""
        DO $
        DECLARE
            v_problemi_trovati BOOLEAN;
            v_output TEXT := '';
        BEGIN
            CALL verifica_integrita_database(v_problemi_trovati);
            
            -- Inserisci il risultato nella tabella temporanea
            INSERT INTO temp_output VALUES ('Problemi trovati: ' || v_problemi_trovati);
        END $;
        """)
        
        # Recupera il risultato
        self.execute_query("SELECT * FROM temp_output")
        result = self.fetchone()
        message = result.get('message', '') if result else ''
        
        # Pulizia
        self.execute_query("DROP TABLE IF EXISTS temp_output")
        
        return 'true' in message.lower(), message

    def get_audit_log(self, tabella=None, operazione=None, record_id=None, 
                    data_inizio=None, data_fine=None, utente=None, limit=100) -> List[Dict]:
        """
        Recupera i log di audit dal database con varie opzioni di filtro.
        
        Args:
            tabella: Filtra per nome tabella
            operazione: Filtra per tipo operazione (I=insert, U=update, D=delete)
            record_id: Filtra per ID record
            data_inizio: Filtra per data inizio
            data_fine: Filtra per data fine
            utente: Filtra per nome utente
            limit: Limite numero risultati
            
        Returns:
            List[Dict]: Lista di log di audit
        """
        conditions = []
        params = []
        
        query = """
        SELECT id, tabella, operazione, record_id, 
            dati_prima, dati_dopo, utente, ip_address, timestamp
        FROM audit_log
        """
        
        if tabella:
            conditions.append("tabella = %s")
            params.append(tabella)
        
        if operazione:
            conditions.append("operazione = %s")
            params.append(operazione)
        
        if record_id:
            conditions.append("record_id = %s")
            params.append(record_id)
        
        if data_inizio:
            conditions.append("timestamp >= %s")
            params.append(data_inizio)
        
        if data_fine:
            conditions.append("timestamp <= %s")
            params.append(data_fine)
        
        if utente:
            conditions.append("utente ILIKE %s")
            params.append(f"%{utente}%")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []

    def get_record_history(self, tabella: str, record_id: int) -> List[Dict]:
        """
        Ottiene la cronologia delle modifiche di un record specifico.
        
        Args:
            tabella: Nome della tabella
            record_id: ID del record
            
        Returns:
            List[Dict]: Lista di modifiche in ordine cronologico
        """
        query = """
        SELECT * FROM get_record_history(%s, %s)
        """
        
        if self.execute_query(query, (tabella, record_id)):
            return self.fetchall()
        return []

    def genera_report_audit(self, tabella=None, data_inizio=None, data_fine=None, 
                        operazione=None, utente=None) -> str:
        """
        Genera un report formattato dei log di audit.
        
        Args:
            tabella: Filtra per tabella
            data_inizio: Data inizio del periodo
            data_fine: Data fine del periodo
            operazione: Tipo di operazione (I, U, D)
            utente: Nome utente
            
        Returns:
            str: Report formattato
        """
        # Recupera i dati di audit
        logs = self.get_audit_log(
            tabella=tabella,
            operazione=operazione,
            data_inizio=data_inizio,
            data_fine=data_fine,
            utente=utente,
            limit=1000  # Limite più alto per il report
        )
        
        if not logs:
            return "Nessun log di audit trovato per i criteri specificati."
        
        # Costruisci il report
        report = "============================================================\n"
        report += "                REPORT DI AUDIT DEL DATABASE                \n"
        report += "                 CATASTO STORICO ANNI '50                   \n"
        report += "============================================================\n\n"
        
        # Aggiungi parametri di filtro al report
        report += "PARAMETRI DI RICERCA:\n"
        if tabella:
            report += f"Tabella: {tabella}\n"
        if data_inizio:
            report += f"Data inizio: {data_inizio}\n"
        if data_fine:
            report += f"Data fine: {data_fine}\n"
        if operazione:
            op_desc = {"I": "Inserimento", "U": "Aggiornamento", "D": "Cancellazione"}
            report += f"Operazione: {op_desc.get(operazione, operazione)}\n"
        if utente:
            report += f"Utente: {utente}\n"
        report += "\n"
        
        # Aggiungi i log al report
        report += f"TROVATI {len(logs)} LOG:\n"
        report += "----------------------------------------------------------\n\n"
        
        for log in logs:
            op_desc = {
                "I": "INSERIMENTO",
                "U": "AGGIORNAMENTO",
                "D": "CANCELLAZIONE"
            }
            
            report += f"ID Log: {log['id']}\n"
            report += f"Operazione: {op_desc.get(log['operazione'], log['operazione'])}\n"
            report += f"Tabella: {log['tabella']}\n"
            report += f"Record ID: {log['record_id']}\n"
            report += f"Timestamp: {log['timestamp']}\n"
            report += f"Utente: {log['utente']}\n"
            
            if log['ip_address']:
                report += f"Indirizzo IP: {log['ip_address']}\n"
            
            # Confronto dati prima/dopo per aggiornamenti
            if log['operazione'] == 'U' and log['dati_prima'] and log['dati_dopo']:
                report += "\nModifiche:\n"
                try:
                    import json
                    dati_prima = json.loads(log['dati_prima'])
                    dati_dopo = json.loads(log['dati_dopo'])
                    
                    # Trova le differenze
                    for chiave in dati_prima:
                        if chiave in dati_dopo and dati_prima[chiave] != dati_dopo[chiave]:
                            report += f"  - {chiave}: {dati_prima[chiave]} -> {dati_dopo[chiave]}\n"
                except:
                    report += "  Impossibile elaborare i dati di modifica\n"
            
            # Per inserimenti, mostra i dati inseriti
            elif log['operazione'] == 'I' and log['dati_dopo']:
                report += "\nDati inseriti:\n"
                try:
                    import json
                    dati = json.loads(log['dati_dopo'])
                    for chiave, valore in dati.items():
                        if valore is not None:
                            report += f"  - {chiave}: {valore}\n"
                except:
                    report += "  Impossibile elaborare i dati inseriti\n"
            
            # Per cancellazioni, mostra i dati cancellati
            elif log['operazione'] == 'D' and log['dati_prima']:
                report += "\nDati cancellati:\n"
                try:
                    import json
                    dati = json.loads(log['dati_prima'])
                    for chiave, valore in dati.items():
                        if valore is not None:
                            report += f"  - {chiave}: {valore}\n"
                except:
                    report += "  Impossibile elaborare i dati cancellati\n"
            
            report += "----------------------------------------------------------\n\n"
        
        # Piè di pagina
        report += "============================================================\n"
        report += f"Report generato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Totale record: {len(logs)}\n"
        report += "============================================================\n"
        
        return report
    
    # --- METODI PER LA GESTIONE UTENTI ---

    def create_user(self, username: str, plain_password: str, nome_completo: str, email: str, ruolo: str) -> bool:
        """
        Crea un nuovo utente nel database utilizzando la stored procedure.
        Esegue l'hashing della password usando bcrypt prima di chiamare la procedura.

        Args:
            username: Username dell'utente.
            plain_password: Password in chiaro fornita dall'utente.
            nome_completo: Nome completo dell'utente.
            email: Email dell'utente.
            ruolo: Ruolo dell'utente ('admin', 'archivista', 'consultatore').

        Returns:
            bool: True se l'utente è stato creato con successo, False altrimenti.
        """
        try:
            # Hash della password con bcrypt (più sicuro)
            password_hash_bytes = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
            password_hash = password_hash_bytes.decode('utf-8') # Memorizza come stringa

            call_proc = "CALL crea_utente(%s, %s, %s, %s, %s)"
            success = self.execute_query(call_proc, (username, password_hash, nome_completo, email, ruolo))
            if success:
                self.commit()
                logger.info(f"Utente {username} creato con successo.")
            return success
        # +++ MODIFIED ERROR HANDLING +++
        except psycopg2.errors.UniqueViolation as uve:
             logger.error(f"Errore: Username '{username}' o Email '{email}' già esistente. {uve}")
             self.rollback()
             return False
        except psycopg2.Error as db_err: # Cattura altri errori DB specifici
             logger.error(f"Errore DB durante la creazione dell'utente {username}: {db_err}")
             self.rollback()
             return False
        except Exception as e: # Errore generico
            logger.error(f"Errore generico durante la creazione dell'utente {username}: {e}")
            self.rollback()
            return False
    def get_user_credentials(self, username: str) -> Optional[Dict]:
        """
        Recupera l'ID utente e l'hash della password (bcrypt) per la verifica del login.
        """
        query = "SELECT id, password_hash FROM utente WHERE username = %s AND attivo = TRUE"
        try: # Aggiungi try-except anche qui per robustezza
            if self.execute_query(query, (username,)):
                return self.fetchone()
            return None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB nel recuperare credenziali per {username}: {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore generico nel recuperare credenziali per {username}: {e}")
            return None

    def register_access(self, utente_id: int, azione: str, indirizzo_ip: str = None, user_agent: str = None, esito: bool = True) -> bool:
        """
        Registra un evento di accesso (login, logout, ecc.) nel log.

        Args:
            utente_id: ID dell'utente.
            azione: Tipo di azione (es. 'login', 'logout', 'password_fail').
            indirizzo_ip: Indirizzo IP (opzionale).
            user_agent: User agent del browser (opzionale).
            esito: Esito dell'azione (True per successo, False per fallimento).

        Returns:
            bool: True se la registrazione è avvenuta con successo, False altrimenti.
        """
        try:
            call_proc = "CALL registra_accesso(%s, %s, %s, %s, %s)"
            success = self.execute_query(call_proc, (utente_id, azione, indirizzo_ip, user_agent, esito))
            if success:
                self.commit()
                # Non logghiamo qui per evitare loop se il log stesso fallisce
            return success
        except Exception as e:
            logger.error(f"Errore durante la registrazione dell'accesso per l'utente {utente_id}: {e}")
            self.rollback()
            return False

    def check_permission(self, utente_id: int, permesso_nome: str) -> bool:
        """
        Verifica se un utente ha un determinato permesso.

        Args:
            utente_id: ID dell'utente.
            permesso_nome: Nome del permesso da verificare.

        Returns:
            bool: True se l'utente ha il permesso, False altrimenti.
        """
        query = "SELECT ha_permesso(%s, %s) AS permesso"
        if self.execute_query(query, (utente_id, permesso_nome)):
            result = self.fetchone()
            return result.get('permesso', False) if result else False
        return False

    # --- FINE METODI GESTIONE UTENTI ---

# --- METODI PER REPORTISTICA AVANZATA (Viste Materializzate e Funzioni) ---

    def refresh_materialized_views(self) -> bool:
        """
        Aggiorna tutte le viste materializzate definite nello script 08.
        È importante eseguire questo metodo periodicamente o dopo modifiche
        significative ai dati per avere report aggiornati.

        Returns:
            bool: True se l'aggiornamento è avvenuto con successo, False altrimenti.
        """
        try:
            # Chiama la procedura SQL che raggruppa gli aggiornamenti
            success = self.execute_query("CALL aggiorna_tutte_statistiche()")
            if success:
                self.commit()
                logger.info("Viste materializzate aggiornate con successo.")
            return success
        except Exception as e:
            logger.error(f"Errore durante l'aggiornamento delle viste materializzate: {e}")
            self.rollback()
            return False

    def get_statistiche_comune(self) -> List[Dict]:
        """
        Recupera le statistiche generali per comune dalla vista materializzata.

        Returns:
            List[Dict]: Lista di statistiche per ogni comune.
        """
        # Interroga la vista materializzata
        query = "SELECT comune, provincia, totale_partite, partite_attive, partite_inattive, totale_possessori, totale_immobili FROM mv_statistiche_comune ORDER BY comune"
        if self.execute_query(query):
            return self.fetchall()
        return []

    def get_immobili_per_tipologia(self, comune_nome: str = None) -> List[Dict]:
        """
        Recupera il riepilogo degli immobili per tipologia (classificazione) dalla vista materializzata,
        filtrando opzionalmente per comune.

        Args:
            comune_nome: Nome del comune per filtrare i risultati (opzionale).

        Returns:
            List[Dict]: Lista di riepiloghi per tipologia.
        """
        params = []
        query = "SELECT comune_nome, classificazione, numero_immobili, totale_piani, totale_vani FROM mv_immobili_per_tipologia"
        if comune_nome:
            query += " WHERE comune_nome = %s"
            params.append(comune_nome)
        query += " ORDER BY comune_nome, classificazione"

        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []

    def get_partite_complete_view(self, comune_nome: str = None, stato: str = None, limit: int = 50) -> List[Dict]:
        """
        Recupera dati completi delle partite dalla vista materializzata, con filtri opzionali.

        Args:
            comune_nome: Nome del comune per filtrare (opzionale).
            stato: Stato della partita ('attiva' o 'inattiva') per filtrare (opzionale).
            limit: Numero massimo di risultati da restituire.

        Returns:
            List[Dict]: Lista di partite con dettagli aggregati.
        """
        conditions = []
        params = []
        query = "SELECT partita_id, comune_nome, numero_partita, tipo, data_impianto, stato, possessori, num_immobili, tipi_immobili, localita FROM mv_partite_complete"

        if comune_nome:
            conditions.append("comune_nome ILIKE %s")
            params.append(f"%{comune_nome}%")
        if stato:
            conditions.append("stato = %s")
            params.append(stato)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY comune_nome, numero_partita LIMIT %s"
        params.append(limit)

        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []

    def get_cronologia_variazioni(self, comune_origine: str = None, tipo_variazione: str = None, limit: int = 50) -> List[Dict]:
        """
        Recupera la cronologia delle variazioni dalla vista materializzata, con filtri opzionali.

        Args:
            comune_origine: Nome del comune di origine per filtrare (opzionale).
            tipo_variazione: Tipo di variazione per filtrare (opzionale).
            limit: Numero massimo di risultati da restituire.

        Returns:
            List[Dict]: Lista delle variazioni con dettagli aggregati.
        """
        conditions = []
        params = []
        query = "SELECT variazione_id, tipo_variazione, data_variazione, partita_origine_numero, comune_origine, possessori_origine, partita_dest_numero, comune_dest, possessori_dest, tipo_contratto, notaio, data_contratto FROM mv_cronologia_variazioni"

        if comune_origine:
            conditions.append("comune_origine ILIKE %s")
            params.append(f"%{comune_origine}%")
        if tipo_variazione:
            conditions.append("tipo_variazione = %s")
            params.append(tipo_variazione)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY data_variazione DESC LIMIT %s"
        params.append(limit)

        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []

    def get_report_annuale_partite(self, comune: str, anno: int) -> List[Dict]:
        """
        Genera un report annuale delle partite per un comune specifico usando la funzione SQL.

        Args:
            comune: Nome del comune.
            anno: Anno per il report.

        Returns:
            List[Dict]: Lista dei dati del report annuale.
        """
        query = "SELECT * FROM report_annuale_partite(%s, %s)"
        if self.execute_query(query, (comune, anno)):
            return self.fetchall()
        return []

    def get_report_proprieta_possessore(self, possessore_id: int, data_inizio: date, data_fine: date) -> List[Dict]:
        """
        Genera un report delle proprietà di un possessore in un periodo specifico usando la funzione SQL.

        Args:
            possessore_id: ID del possessore.
            data_inizio: Data di inizio del periodo.
            data_fine: Data di fine del periodo.

        Returns:
            List[Dict]: Lista delle proprietà del possessore nel periodo.
        """
        query = "SELECT * FROM report_proprieta_possessore(%s, %s, %s)"
        if self.execute_query(query, (possessore_id, data_inizio, data_fine)):
            return self.fetchall()
        return []

    # --- FINE METODI REPORTISTICA AVANZATA ---
    # --- METODI PER IL SISTEMA DI BACKUP ---

    def register_backup_log(self, nome_file: str, utente: str, tipo: str, esito: bool, percorso_file: str, dimensione_bytes: Optional[int] = None, messaggio: Optional[str] = None) -> Optional[int]:
        """
        Registra un'operazione di backup nel log del database.

        Args:
            nome_file: Nome del file di backup generato.
            utente: Utente che ha eseguito/richiesto il backup.
            tipo: Tipo di backup ('completo', 'schema', 'dati').
            esito: True se il backup è andato a buon fine, False altrimenti.
            percorso_file: Percorso completo del file di backup.
            dimensione_bytes: Dimensione del file di backup in byte (opzionale).
            messaggio: Messaggio di log aggiuntivo (opzionale).

        Returns:
            Optional[int]: ID del log inserito, None in caso di errore.
        """
        try:
            query = "SELECT registra_backup(%s, %s, %s, %s, %s, %s, %s)"
            params = (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)
            if self.execute_query(query, params):
                result = self.fetchone()
                self.commit()
                backup_id = result.get('registra_backup') if result else None
                if backup_id:
                    logger.info(f"Registrato log di backup con ID: {backup_id}")
                    return backup_id
                else:
                    logger.warning("La funzione registra_backup non ha restituito un ID.")
                    return None
            return None
        except Exception as e:
            logger.error(f"Errore durante la registrazione del log di backup: {e}")
            self.rollback()
            return None

    def get_backup_command_suggestion(self, tipo: str = 'completo') -> Optional[str]:
        """
        Ottiene il suggerimento del comando pg_dump da eseguire per il backup.

        Args:
            tipo: Tipo di backup ('completo', 'schema', 'dati'). Default: 'completo'.

        Returns:
            Optional[str]: Stringa con il comando suggerito e le istruzioni SQL
                           per la registrazione, o None in caso di errore.
        """
        query = "SELECT get_backup_commands(%s) AS commands"
        if self.execute_query(query, (tipo,)):
            result = self.fetchone()
            return result.get('commands') if result else None
        return None

    def get_restore_command_suggestion(self, backup_log_id: int) -> Optional[str]:
        """
        Ottiene il suggerimento del comando psql da eseguire per il restore
        basato su un ID di log di backup esistente.

        Args:
            backup_log_id: ID del record nella tabella backup_registro.

        Returns:
            Optional[str]: Stringa con il comando psql suggerito, o None se
                           l'ID non è valido o in caso di errore.
        """
        query = "SELECT get_restore_commands(%s) AS command"
        if self.execute_query(query, (backup_log_id,)):
            result = self.fetchone()
            return result.get('command') if result else None
        return None

    def cleanup_old_backup_logs(self, giorni_conservazione: int = 30) -> bool:
        """
        Esegue la procedura SQL per la pulizia dei log di backup più vecchi
        del numero di giorni specificato.
        Nota: Questo elimina solo i record dal DB, non i file fisici.

        Args:
            giorni_conservazione: Numero di giorni per cui conservare i log. Default 30.

        Returns:
            bool: True se l'operazione è stata eseguita, False altrimenti.
        """
        try:
            call_proc = "CALL pulizia_backup_vecchi(%s)"
            success = self.execute_query(call_proc, (giorni_conservazione,))
            if success:
                self.commit()
                logger.info(f"Eseguita pulizia log di backup più vecchi di {giorni_conservazione} giorni.")
            return success
        except Exception as e:
            logger.error(f"Errore durante la pulizia dei log di backup: {e}")
            self.rollback()
            return False

    def generate_backup_script(self, backup_dir: str) -> Optional[str]:
        """
        Genera lo script bash per il backup automatico usando la funzione SQL.

        Args:
            backup_dir: La directory dove lo script salverà i backup.

        Returns:
            Optional[str]: Il contenuto dello script generato, o None in caso di errore.
        """
        query = "SELECT genera_script_backup_automatico(%s) AS script_content"
        if self.execute_query(query, (backup_dir,)):
            result = self.fetchone()
            return result.get('script_content') if result else None
        return None

    def get_backup_logs(self, limit: int = 20) -> List[Dict]:
        """
        Recupera gli ultimi N log di backup dal registro.

        Args:
            limit: Numero massimo di log da recuperare.

        Returns:
            List[Dict]: Lista dei log di backup.
        """
        query = """
            SELECT id, nome_file, timestamp, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file
            FROM backup_registro
            ORDER BY timestamp DESC
            LIMIT %s
        """
        if self.execute_query(query, (limit,)):
            return self.fetchall()
        return []


    # --- FINE METODI SISTEMA DI BACKUP ---

    # --- METODI PER OTTIMIZZAZIONE E RICERCA AVANZATA ---

    def ricerca_avanzata_possessori(self, query_text: str) -> List[Dict]:
        """
        Esegue una ricerca avanzata (basata su similarità) sui possessori
        utilizzando la funzione SQL dedicata.

        Args:
            query_text: Il testo da cercare nel nome completo, cognome/nome o paternità.

        Returns:
            List[Dict]: Lista di possessori trovati, ordinati per similarità e numero di partite.
                        Include 'id', 'nome_completo', 'comune_nome', 'similarity', 'num_partite'.
        """
        query = "SELECT * FROM ricerca_avanzata_possessori(%s)"
        if self.execute_query(query, (query_text,)):
            return self.fetchall()
        return []

    def ricerca_avanzata_immobili(self, comune: str = None, natura: str = None, localita: str = None, classificazione: str = None, possessore: str = None) -> List[Dict]:
        """
        Esegue una ricerca avanzata sugli immobili con filtri multipli,
        utilizzando la funzione SQL dedicata.

        Args:
            comune: Filtro per nome comune (opzionale).
            natura: Filtro per natura immobile (ricerca parziale, opzionale).
            localita: Filtro per nome località (ricerca parziale, opzionale).
            classificazione: Filtro per classificazione esatta (opzionale).
            possessore: Filtro per nome possessore (ricerca parziale, opzionale).

        Returns:
            List[Dict]: Lista di immobili trovati con dettagli e possessori associati.
                        Include 'immobile_id', 'natura', 'localita_nome', 'comune',
                        'classificazione', 'possessori', 'partita_numero'.
        """
        query = "SELECT * FROM ricerca_avanzata_immobili(%s, %s, %s, %s, %s)"
        params = (comune, natura, localita, classificazione, possessore)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def run_database_maintenance(self) -> bool:
        """
        Esegue operazioni di manutenzione come VACUUM e ANALYZE direttamente
        e aggiorna le viste materializzate.
        VACUUM e ANALYZE vengono eseguiti in modalità autocommit.

        Returns:
            bool: True se tutte le operazioni principali sono state eseguite, False altrimenti.
        """
        all_success = True
        original_autocommit = None
        tables_to_maintain = ['comune', 'possessore', 'partita', 'immobile', 'localita', 'variazione', 'contratto', 'consultazione', 'utente', 'audit_log', 'backup_registro'] # Aggiungi altre tabelle se necessario

        try:
            if not self.conn or self.conn.closed:
                 if not self.connect():
                      return False

            # Salva lo stato corrente di autocommit e impostalo a True per VACUUM/ANALYZE
            original_autocommit = self.conn.autocommit
            self.conn.autocommit = True
            logger.info("Impostata modalità autocommit per VACUUM/ANALYZE.")

            for table in tables_to_maintain:
                logger.info(f"Esecuzione VACUUM ANALYZE su catasto.{table}...")
                # Esegui VACUUM ANALYZE direttamente
                if not self.execute_query(f"VACUUM (VERBOSE, ANALYZE) catasto.{table}"):
                    logger.warning(f"VACUUM ANALYZE su {table} potrebbe essere fallito (controllare log DB).")
                    # Potrebbe non essere critico, quindi continuiamo ma segnaliamo
                    # all_success = False # Decommenta se vuoi che fallisca l'intera operazione

            logger.info("VACUUM ANALYZE completato per le tabelle specificate.")

        except Exception as e:
            logger.error(f"Errore durante VACUUM/ANALYZE in autocommit: {e}")
            all_success = False
        finally:
            # Ripristina lo stato originale di autocommit SEMPRE
            if self.conn and not self.conn.closed and original_autocommit is not None:
                self.conn.autocommit = original_autocommit
                logger.info(f"Ripristinata modalità autocommit a: {original_autocommit}")
            elif self.conn and not self.conn.closed:
                 # Se original_autocommit è None (improbabile), ripristina a False
                 self.conn.autocommit = False
                 logger.warning("Ripristinata modalità autocommit a False (stato originale sconosciuto).")


        # Ora esegui operazioni compatibili con le transazioni, se necessario
        # Ad esempio, aggiorna le viste materializzate (questo può essere in una transazione)
        if all_success: # Procedi solo se VACUUM/ANALYZE non hanno generato eccezioni critiche
            logger.info("Aggiornamento Viste Materializzate...")
            if not self.refresh_materialized_views(): # refresh_materialized_views gestisce commit/rollback
                 logger.error("Fallito aggiornamento delle viste materializzate.")
                 all_success = False
            else:
                 logger.info("Viste Materializzate aggiornate.")

        return all_success

    def analyze_slow_queries(self, min_duration_ms: int = 1000) -> List[Dict]:
        """
        Chiama la funzione SQL per analizzare le query lente.
        Richiede l'estensione 'pg_stat_statements' abilitata nel database.

        Args:
            min_duration_ms: Durata minima in millisecondi per considerare una query lenta.

        Returns:
            List[Dict]: Lista delle query lente trovate, con dettagli.
        """
        # Verifica se l'estensione è abilitata (opzionale ma utile)
        if not self.execute_query("SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'"):
             logger.warning("Estensione 'pg_stat_statements' non trovata o errore nella verifica.")
             # Non possiamo procedere senza l'estensione
             # return [] # Commentato per provare comunque a chiamare la funzione
        elif not self.fetchone():
             logger.warning("Estensione 'pg_stat_statements' non è abilitata nel database. La funzione 'analizza_query_lente' potrebbe non funzionare.")
             # return [] # Commentato per provare comunque

        logger.info(f"Ricerca query più lente di {min_duration_ms} ms...")
        query = "SELECT * FROM analizza_query_lente(%s)"
        try:
            if self.execute_query(query, (min_duration_ms,)):
                return self.fetchall()
            return []
        except Exception as e:
             # Potrebbe fallire se l'estensione non è installata/abilitata
             logger.error(f"Errore nell'analisi delle query lente (assicurati che 'pg_stat_statements' sia abilitata): {e}")
             return []


    def check_index_fragmentation(self) -> List[Dict]:
        """
        Esegue la procedura SQL per controllare la frammentazione degli indici
        e restituisce gli indici potenzialmente frammentati.

        Returns:
            List[Dict]: Lista degli indici con frammentazione > 30%.
                       Include 'schema_name', 'table_name', 'index_name', 'bloat_ratio', 'bloat_size'.
        """
        try:
            # La procedura originale stampa i risultati con RAISE NOTICE.
            # Per catturarli in Python, la modifichiamo temporaneamente per usare una tabella temporanea.
            # Questo è più complesso del necessario se l'output va solo a log/console.
            # Semplifichiamo assumendo che l'output sia per informazione e log.
            logger.info("Avvio controllo frammentazione indici...")

            # Eseguiamo la procedura. I risultati saranno loggati da PostgreSQL se usi RAISE NOTICE.
            # Per ottenerli *programmaticamente*, la procedura SQL andrebbe modificata
            # per restituire un SETOF record o usare una tabella temporanea.
            # Qui simuliamo la chiamata e logghiamo un messaggio.
            if self.execute_query("CALL controlla_frammentazione_indici()"):
                 self.commit() # Necessario se la procedura usa tabelle temporanee che poi elimina
                 logger.info("Controllo frammentazione indici eseguito. Controlla i log del database per i dettagli.")
                 # Qui potresti aggiungere una query per leggere la tabella temporanea se la procedura la usa
                 # Esempio:
                 # if self.execute_query("SELECT * FROM index_stats WHERE bloat_ratio > 30"):
                 #     return self.fetchall()
                 return [] # Restituisce lista vuota in questa implementazione semplificata
            else:
                 return []

        except Exception as e:
            logger.error(f"Errore durante il controllo della frammentazione degli indici: {e}")
            self.rollback()
            return []


    def get_optimization_suggestions(self) -> Optional[str]:
        """
        Ottiene suggerimenti generali per l'ottimizzazione del database
        chiamando la funzione SQL dedicata.

        Returns:
            Optional[str]: Stringa contenente i suggerimenti, o None in caso di errore.
        """
        query = "SELECT suggerimenti_ottimizzazione() AS suggestions"
        if self.execute_query(query):
            result = self.fetchone()
            return result.get('suggestions') if result else None
        return None

    # --- FINE METODI OTTIMIZZAZIONE ---
    # --- METODI PER FUNZIONALITÀ STORICHE AVANZATE (da script 11) ---

    def get_historical_periods(self) -> List[Dict]:
        """
        Recupera tutti i periodi storici definiti nel database.

        Returns:
            List[Dict]: Lista dei periodi storici.
        """
        query = "SELECT id, nome, anno_inizio, anno_fine, descrizione FROM periodo_storico ORDER BY anno_inizio"
        if self.execute_query(query):
            return self.fetchall()
        return []

    def get_historical_name(self, entity_type: str, entity_id: int, year: Optional[int] = None) -> Optional[Dict]:
        """
        Ottiene il nome storico corretto per un'entità (comune o localita)
        in un determinato anno, usando la funzione SQL 'get_nome_storico'.

        Args:
            entity_type: Tipo di entità ('comune' o 'localita').
            entity_id: ID dell'entità (ID da tabella comune o localita).
            year: Anno per cui cercare il nome (default: anno corrente).

        Returns:
            Optional[Dict]: Dizionario con 'nome', 'anno_inizio', 'anno_fine', 'periodo_nome'
                           se trovato, altrimenti None.
        """
        if year is None:
            year = datetime.now().year

        query = "SELECT * FROM get_nome_storico(%s, %s, %s)"
        if self.execute_query(query, (entity_type, entity_id, year)):
            return self.fetchone()
        return None

    def register_historical_name(self, entity_type: str, entity_id: int, name: str, period_id: int, year_start: int, year_end: Optional[int] = None, notes: Optional[str] = None) -> bool:
        """
        Registra un nome storico per un'entità usando la procedura SQL 'registra_nome_storico'.

        Args:
            entity_type: Tipo di entità ('comune' o 'localita').
            entity_id: ID dell'entità.
            name: Il nome storico.
            period_id: ID del periodo storico associato.
            year_start: Anno di inizio validità del nome.
            year_end: Anno di fine validità (opzionale).
            notes: Note aggiuntive (opzionale).

        Returns:
            bool: True se l'operazione ha avuto successo, False altrimenti.
        """
        try:
            call_proc = "CALL registra_nome_storico(%s, %s, %s, %s, %s, %s, %s)"
            params = (entity_type, entity_id, name, period_id, year_start, year_end, notes)
            success = self.execute_query(call_proc, params)
            if success:
                self.commit()
                logger.info(f"Registrato nome storico '{name}' per {entity_type} ID {entity_id}.")
            return success
        except Exception as e:
            logger.error(f"Errore durante la registrazione del nome storico: {e}")
            self.rollback()
            return False

    def search_historical_documents(self, title: Optional[str] = None, doc_type: Optional[str] = None, period_id: Optional[int] = None, year_start: Optional[int] = None, year_end: Optional[int] = None, partita_id: Optional[int] = None) -> List[Dict]:
        """
        Ricerca documenti storici nel database usando la funzione SQL 'ricerca_documenti_storici'.

        Args:
            title: Testo da cercare nel titolo (parziale, case-insensitive).
            doc_type: Tipo esatto di documento.
            period_id: ID del periodo storico.
            year_start: Anno minimo del documento.
            year_end: Anno massimo del documento.
            partita_id: ID di una partita a cui il documento deve essere collegato.

        Returns:
            List[Dict]: Lista dei documenti trovati.
        """
        query = "SELECT * FROM ricerca_documenti_storici(%s, %s, %s, %s, %s, %s)"
        params = (title, doc_type, period_id, year_start, year_end, partita_id)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def get_property_genealogy(self, partita_id: int) -> List[Dict]:
        """
        Ricostruisce l'albero genealogico di una proprietà (predecessori e successori)
        usando la funzione SQL 'albero_genealogico_proprieta'.

        Args:
            partita_id: ID della partita di partenza.

        Returns:
            List[Dict]: Lista di partite nell'albero genealogico, ordinate per livello.
                       Include 'livello', 'tipo_relazione', 'partita_id', 'comune_nome',
                       'numero_partita', 'tipo', 'possessori', 'data_variazione'.
        """
        query = "SELECT * FROM albero_genealogico_proprieta(%s)"
        if self.execute_query(query, (partita_id,)):
            return self.fetchall()
        return []

    def get_cadastral_stats_by_period(self, comune: Optional[str] = None, year_start: int = 1900, year_end: Optional[int] = None) -> List[Dict]:
        """
        Ottiene statistiche catastali aggregate per anno e comune, in un range di anni,
        usando la funzione SQL 'statistiche_catastali_periodo'.

        Args:
            comune: Filtra per un comune specifico (opzionale).
            year_start: Anno di inizio del periodo statistico.
            year_end: Anno di fine del periodo statistico (default: anno corrente).

        Returns:
            List[Dict]: Lista di statistiche annuali.
        """
        if year_end is None:
            year_end = datetime.now().year

        query = "SELECT * FROM statistiche_catastali_periodo(%s, %s, %s)"
        params = (comune, year_start, year_end)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def link_document_to_partita(self, document_id: int, partita_id: int, relevance: str = 'correlata', notes: Optional[str] = None) -> bool:
        """
        Collega un documento storico esistente a una partita.

        Args:
            document_id: ID del documento storico.
            partita_id: ID della partita.
            relevance: Rilevanza del collegamento ('primaria', 'secondaria', 'correlata').
            notes: Note aggiuntive (opzionale).

        Returns:
            bool: True se il collegamento è stato creato/aggiornato, False altrimenti.
        """
        if relevance not in ['primaria', 'secondaria', 'correlata']:
            logger.error(f"Rilevanza non valida: {relevance}")
            return False

        query = """
            INSERT INTO documento_partita (documento_id, partita_id, rilevanza, note)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (documento_id, partita_id) DO UPDATE SET
                rilevanza = EXCLUDED.rilevanza,
                note = EXCLUDED.note
        """
        params = (document_id, partita_id, relevance, notes)
        try:
            if self.execute_query(query, params):
                self.commit()
                logger.info(f"Documento ID {document_id} collegato a Partita ID {partita_id}.")
                return True
            return False
        except Exception as e:
            logger.error(f"Errore nel collegare documento {document_id} a partita {partita_id}: {e}")
            self.rollback()
            return False

    # --- FINE METODI FUNZIONALITÀ STORICHE AVANZATE ---

# --- METODI CRUD E UTILITY AGGIUNTIVI (da script 12) ---

    def update_immobile(self, immobile_id: int, **kwargs) -> bool:
        """
        Aggiorna i dettagli di un immobile usando la procedura SQL corretta.

        Args:
            immobile_id: ID dell'immobile da aggiornare.
            **kwargs: Campi da aggiornare (natura, numero_piani, numero_vani,
                      consistenza, classificazione, localita_id).
                      I campi non specificati non verranno modificati.

        Returns:
            bool: True se l'aggiornamento ha avuto successo, False altrimenti.
        """
        # Mappa i kwargs ai parametri della procedura SQL, gestendo i default a None
        params = {
            'p_id': immobile_id,
            'p_natura': kwargs.get('natura'),
            'p_numero_piani': kwargs.get('numero_piani'),
            'p_numero_vani': kwargs.get('numero_vani'),
            'p_consistenza': kwargs.get('consistenza'),
            'p_classificazione': kwargs.get('classificazione'),
            'p_localita_id': kwargs.get('localita_id')
        }
        call_proc = "CALL aggiorna_immobile(%(p_id)s, %(p_natura)s, %(p_numero_piani)s, %(p_numero_vani)s, %(p_consistenza)s, %(p_classificazione)s, %(p_localita_id)s)"
        try:
            success = self.execute_query(call_proc, params)
            if success:
                self.commit()
                logger.info(f"Immobile ID {immobile_id} aggiornato con successo.")
            return success
        except Exception as e:
            logger.error(f"Errore durante l'aggiornamento dell'immobile ID {immobile_id}: {e}")
            self.rollback()
            return False

    def delete_immobile(self, immobile_id: int) -> bool:
        """
        Elimina un immobile dal database usando la procedura SQL corretta.

        Args:
            immobile_id: ID dell'immobile da eliminare.

        Returns:
            bool: True se l'eliminazione ha avuto successo, False altrimenti.
        """
        try:
            call_proc = "CALL elimina_immobile(%s)"
            success = self.execute_query(call_proc, (immobile_id,))
            if success:
                self.commit()
                logger.info(f"Immobile ID {immobile_id} eliminato con successo.")
            return success
        except Exception as e:
            logger.error(f"Errore durante l'eliminazione dell'immobile ID {immobile_id}: {e}")
            self.rollback()
            return False

    def search_immobili(self, partita_id: Optional[int] = None, comune_nome: Optional[str] = None, localita_id: Optional[int] = None, natura: Optional[str] = None, classificazione: Optional[str] = None) -> List[Dict]:
        """
        Ricerca immobili specifici usando la funzione SQL corretta.

        Args:
            partita_id: Filtro per ID partita (opzionale).
            comune_nome: Filtro per nome comune (opzionale).
            localita_id: Filtro per ID località (opzionale).
            natura: Filtro per natura (ricerca parziale, opzionale).
            classificazione: Filtro per classificazione (esatta, opzionale).

        Returns:
            List[Dict]: Lista degli immobili trovati.
        """
        query = "SELECT * FROM cerca_immobili(%s, %s, %s, %s, %s)"
        params = (partita_id, comune_nome, localita_id, natura, classificazione)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def update_variazione(self, variazione_id: int, **kwargs) -> bool:
        """
        Aggiorna i dettagli di una variazione.

        Args:
            variazione_id: ID della variazione da aggiornare.
            **kwargs: Campi da aggiornare (tipo, data_variazione,
                      numero_riferimento, nominativo_riferimento).

        Returns:
            bool: True se l'aggiornamento ha avuto successo.
        """
        params = {
            'p_variazione_id': variazione_id,
            'p_tipo': kwargs.get('tipo'),
            'p_data_variazione': kwargs.get('data_variazione'),
            'p_numero_riferimento': kwargs.get('numero_riferimento'),
            'p_nominativo_riferimento': kwargs.get('nominativo_riferimento')
        }
        call_proc = "CALL aggiorna_variazione(%(p_variazione_id)s, %(p_tipo)s, %(p_data_variazione)s, %(p_numero_riferimento)s, %(p_nominativo_riferimento)s)"
        try:
            success = self.execute_query(call_proc, params)
            if success:
                self.commit()
                logger.info(f"Variazione ID {variazione_id} aggiornata.")
            return success
        except Exception as e:
            logger.error(f"Errore aggiornamento variazione ID {variazione_id}: {e}")
            self.rollback()
            return False

    def delete_variazione(self, variazione_id: int, force: bool = False, restore_partita: bool = False) -> bool:
        """
        Elimina una variazione e opzionalmente i contratti collegati
        e ripristina lo stato della partita origine.

        Args:
            variazione_id: ID della variazione da eliminare.
            force: Se True, elimina anche i contratti associati. Default False.
            restore_partita: Se True, prova a riattivare la partita origine. Default False.

        Returns:
            bool: True se l'eliminazione ha avuto successo.
        """
        try:
            call_proc = "CALL elimina_variazione(%s, %s, %s)"
            success = self.execute_query(call_proc, (variazione_id, force, restore_partita))
            if success:
                self.commit()
                logger.info(f"Variazione ID {variazione_id} eliminata.")
            return success
        except Exception as e:
            logger.error(f"Errore eliminazione variazione ID {variazione_id}: {e}")
            self.rollback()
            return False

    def search_variazioni(self, tipo: Optional[str] = None, data_inizio: Optional[date] = None, data_fine: Optional[date] = None, partita_origine_id: Optional[int] = None, partita_destinazione_id: Optional[int] = None, comune: Optional[str] = None) -> List[Dict]:
        """
        Ricerca variazioni con filtri multipli usando la funzione SQL corretta.

        Args:
            tipo, data_inizio, data_fine, partita_origine_id,
            partita_destinazione_id, comune: Filtri opzionali.

        Returns:
            List[Dict]: Lista delle variazioni trovate.
        """
        query = "SELECT * FROM cerca_variazioni(%s, %s, %s, %s, %s, %s)"
        params = (tipo, data_inizio, data_fine, partita_origine_id, partita_destinazione_id, comune)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def insert_contratto(self, variazione_id: int, tipo: str, data_contratto: date, notaio: Optional[str] = None, repertorio: Optional[str] = None, note: Optional[str] = None) -> bool:
        """
        Inserisce un nuovo contratto associato a una variazione.

        Args:
            variazione_id, tipo, data_contratto, notaio, repertorio, note.

        Returns:
            bool: True se inserito con successo.
        """
        try:
            call_proc = "CALL inserisci_contratto(%s, %s, %s, %s, %s, %s)"
            params = (variazione_id, tipo, data_contratto, notaio, repertorio, note)
            success = self.execute_query(call_proc, params)
            if success:
                self.commit()
                logger.info(f"Contratto inserito per variazione ID {variazione_id}.")
            return success
        except Exception as e:
            logger.error(f"Errore inserimento contratto per variazione ID {variazione_id}: {e}")
            self.rollback()
            return False

    def update_contratto(self, contratto_id: int, **kwargs) -> bool:
        """
        Aggiorna i dettagli di un contratto esistente.

        Args:
            contratto_id: ID del contratto da aggiornare.
            **kwargs: Campi da aggiornare (tipo, data_contratto, notaio,
                      repertorio, note).

        Returns:
            bool: True se aggiornato con successo.
        """
        params = {
            'p_id': contratto_id,
            'p_tipo': kwargs.get('tipo'),
            'p_data_contratto': kwargs.get('data_contratto'),
            'p_notaio': kwargs.get('notaio'),
            'p_repertorio': kwargs.get('repertorio'),
            'p_note': kwargs.get('note')
        }
        call_proc = "CALL aggiorna_contratto(%(p_id)s, %(p_tipo)s, %(p_data_contratto)s, %(p_notaio)s, %(p_repertorio)s, %(p_note)s)"
        try:
            success = self.execute_query(call_proc, params)
            if success:
                self.commit()
                logger.info(f"Contratto ID {contratto_id} aggiornato.")
            return success
        except Exception as e:
            logger.error(f"Errore aggiornamento contratto ID {contratto_id}: {e}")
            self.rollback()
            return False

    def delete_contratto(self, contratto_id: int) -> bool:
        """
        Elimina un contratto specifico.

        Args:
            contratto_id: ID del contratto da eliminare.

        Returns:
            bool: True se eliminato con successo.
        """
        try:
            call_proc = "CALL elimina_contratto(%s)"
            success = self.execute_query(call_proc, (contratto_id,))
            if success:
                self.commit()
                logger.info(f"Contratto ID {contratto_id} eliminato.")
            return success
        except Exception as e:
            logger.error(f"Errore eliminazione contratto ID {contratto_id}: {e}")
            self.rollback()
            return False

    def update_consultazione(self, consultazione_id: int, **kwargs) -> bool:
        """
        Aggiorna i dettagli di una consultazione.

        Args:
            consultazione_id: ID della consultazione.
            **kwargs: Campi da aggiornare (data, richiedente, documento_identita,
                      motivazione, materiale_consultato, funzionario_autorizzante).

        Returns:
            bool: True se aggiornato con successo.
        """
        params = {
            'p_id': consultazione_id,
            'p_data': kwargs.get('data'),
            'p_richiedente': kwargs.get('richiedente'),
            'p_documento_identita': kwargs.get('documento_identita'),
            'p_motivazione': kwargs.get('motivazione'),
            'p_materiale_consultato': kwargs.get('materiale_consultato'),
            'p_funzionario_autorizzante': kwargs.get('funzionario_autorizzante')
        }
        call_proc = "CALL aggiorna_consultazione(%(p_id)s, %(p_data)s, %(p_richiedente)s, %(p_documento_identita)s, %(p_motivazione)s, %(p_materiale_consultato)s, %(p_funzionario_autorizzante)s)"
        try:
            success = self.execute_query(call_proc, params)
            if success:
                self.commit()
                logger.info(f"Consultazione ID {consultazione_id} aggiornata.")
            return success
        except Exception as e:
            logger.error(f"Errore aggiornamento consultazione ID {consultazione_id}: {e}")
            self.rollback()
            return False

    def delete_consultazione(self, consultazione_id: int) -> bool:
        """
        Elimina una registrazione di consultazione.

        Args:
            consultazione_id: ID della consultazione da eliminare.

        Returns:
            bool: True se eliminata con successo.
        """
        try:
            call_proc = "CALL elimina_consultazione(%s)"
            success = self.execute_query(call_proc, (consultazione_id,))
            if success:
                self.commit()
                logger.info(f"Consultazione ID {consultazione_id} eliminata.")
            return success
        except Exception as e:
            logger.error(f"Errore eliminazione consultazione ID {consultazione_id}: {e}")
            self.rollback()
            return False

    def search_consultazioni(self, data_inizio: Optional[date] = None, data_fine: Optional[date] = None, richiedente: Optional[str] = None, funzionario: Optional[str] = None) -> List[Dict]:
        """
        Ricerca le consultazioni con filtri.

        Args:
            data_inizio, data_fine, richiedente, funzionario: Filtri opzionali.

        Returns:
            List[Dict]: Lista delle consultazioni trovate.
        """
        query = "SELECT * FROM cerca_consultazioni(%s, %s, %s, %s)"
        params = (data_inizio, data_fine, richiedente, funzionario)
        if self.execute_query(query, params):
            return self.fetchall()
        return []

    def duplicate_partita(self, partita_id: int, nuovo_numero_partita: int, mantenere_possessori: bool = True, mantenere_immobili: bool = False) -> bool:
        """
        Duplica una partita esistente.

        Args:
            partita_id: ID della partita da duplicare.
            nuovo_numero_partita: Nuovo numero per la partita duplicata.
            mantenere_possessori: Se True, copia i possessori.
            mantenere_immobili: Se True, copia gli immobili.

        Returns:
            bool: True se la duplicazione ha avuto successo.
        """
        try:
            call_proc = "CALL duplica_partita(%s, %s, %s, %s)"
            params = (partita_id, nuovo_numero_partita, mantenere_possessori, mantenere_immobili)
            success = self.execute_query(call_proc, params)
            if success:
                self.commit()
                logger.info(f"Partita ID {partita_id} duplicata con nuovo numero {nuovo_numero_partita}.")
            return success
        except Exception as e:
            logger.error(f"Errore duplicazione partita ID {partita_id}: {e}")
            self.rollback()
            return False

    def transfer_immobile(self, immobile_id: int, nuova_partita_id: int, registra_variazione: bool = False) -> bool:
        """
        Trasferisce un immobile da una partita a un'altra.

        Args:
            immobile_id: ID dell'immobile da trasferire.
            nuova_partita_id: ID della partita di destinazione.
            registra_variazione: Se True, crea un record di variazione per il trasferimento.

        Returns:
            bool: True se il trasferimento ha avuto successo.
        """
        try:
            call_proc = "CALL trasferisci_immobile(%s, %s, %s)"
            params = (immobile_id, nuova_partita_id, registra_variazione)
            success = self.execute_query(call_proc, params)
            if success:
                self.commit()
                logger.info(f"Immobile ID {immobile_id} trasferito alla partita ID {nuova_partita_id}.")
            return success
        except Exception as e:
            logger.error(f"Errore trasferimento immobile ID {immobile_id}: {e}")
            self.rollback()
            return False

    def export_partita_json(self, partita_id: int) -> Optional[str]:
        """
        Esporta i dati completi di una partita in formato JSON.

        Args:
            partita_id: ID della partita da esportare.

        Returns:
            Optional[str]: Stringa JSON con i dati della partita, o None in caso di errore.
        """
        query = "SELECT esporta_partita_json(%s) AS partita_json"
        if self.execute_query(query, (partita_id,)):
            result = self.fetchone()
            # Il risultato della funzione è già JSON, ma psycopg2 potrebbe restituirlo come dict
            # Lo riconvertiamo in stringa JSON formattata
            if result and 'partita_json' in result and result['partita_json']:
                 try:
                     # Usa json.dumps per formattare l'output JSON
                     return json.dumps(result['partita_json'], indent=4, ensure_ascii=False)
                 except TypeError as e:
                      logger.error(f"Errore nella serializzazione JSON per partita {partita_id}: {e}")
                      return str(result['partita_json']) # Fallback a stringa semplice
            else:
                 logger.warning(f"Nessun dato JSON restituito per partita ID {partita_id}.")
                 return None
        return None

    def export_possessore_json(self, possessore_id: int) -> Optional[str]:
        """
        Esporta i dati completi di un possessore e delle sue proprietà in formato JSON.

        Args:
            possessore_id: ID del possessore da esportare.

        Returns:
            Optional[str]: Stringa JSON con i dati del possessore, o None in caso di errore.
        """
        query = "SELECT esporta_possessore_json(%s) AS possessore_json"
        if self.execute_query(query, (possessore_id,)):
            result = self.fetchone()
            if result and 'possessore_json' in result and result['possessore_json']:
                 try:
                     return json.dumps(result['possessore_json'], indent=4, ensure_ascii=False)
                 except TypeError as e:
                      logger.error(f"Errore nella serializzazione JSON per possessore {possessore_id}: {e}")
                      return str(result['possessore_json'])
            else:
                  logger.warning(f"Nessun dato JSON restituito per possessore ID {possessore_id}.")
                  return None
        return None

    def get_report_comune(self, comune_nome: str) -> Optional[Dict]:
        """
        Genera un report statistico per un singolo comune.

        Args:
            comune_nome: Nome del comune.

        Returns:
            Optional[Dict]: Dizionario con le statistiche del comune, o None se non trovato/errore.
        """
        # Nota: La funzione SQL 'genera_report_comune' restituisce una tabella (potenzialmente 0 o 1 riga)
        query = "SELECT * FROM genera_report_comune(%s)"
        if self.execute_query(query, (comune_nome,)):
            # fetchone() è appropriato perché ci aspettiamo al massimo una riga per comune
            return self.fetchone()
        return None

    # --- FINE METODI CRUD E UTILITY AGGIUNTIVI ---

    # Esempio di utilizzo
if __name__ == "__main__":
    # Crea un'istanza del gestore
    db = CatastoDBManager(
        dbname="catasto_storico", 
        user="postgres", 
        password="Markus74",  # Sostituisci con la tua password
        host="localhost"
    )
    
    # Test di connessione
    if db.connect():
        print("Connessione stabilita con successo!")
        
        try:
            # Esempio di inserimento di un comune
            db.execute_query(
                "INSERT INTO comune (nome, provincia, regione) VALUES (%s, %s, %s) ON CONFLICT (nome) DO NOTHING", 
                ("Bormida", "Savona", "Liguria")
            )
            db.commit()
            print("Comune inserito")
            
            # Recupera tutti i comuni
            comuni = db.get_comuni()
            print(f"Comuni nel database: {len(comuni)}")
            for c in comuni:
                print(f" - {c['nome']} ({c['provincia']})")
            
            # Esempio di ricerca partite
            partite = db.search_partite(comune_nome="Carcare")
            print(f"Partite trovate: {len(partite)}")
            
            # Esempio di generazione certificato
            if partite:
                certificato = db.genera_certificato_proprieta(partite[0]['id'])
                print("\nEsempio di certificato di proprieta:")
                print(certificato[:500] + "..." if len(certificato) > 500 else certificato)
            
        except Exception as e:
            print(f"Errore: {e}")
        
        finally:
            # Chiudi la connessione
            db.disconnect()
    else:
        print("Impossibile connettersi al database")