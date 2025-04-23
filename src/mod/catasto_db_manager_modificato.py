#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestore Database Catasto Storico
================================
Script per la gestione del database catastale con supporto 
per operazioni CRUD e chiamate alle stored procedure.

Autore: Claude AI
Data: 17/04/2025
"""

import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
import sys
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple, Union

# Configurazione logging
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
    
    def __init__(self, dbname: str = "catasto_storico", user: str = "postgres", 
                 password: str = "", host: str = "localhost", port: int = 5432, 
                 schema: str = "catasto"):
        """
        Inizializza la connessione al database.
        
        Args:
            dbname: Nome del database
            user: Nome utente
            password: Password
            host: Hostname del server
            port: Porta TCP
            schema: Schema da utilizzare
        """
        self.conn_params = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": port
        }
        self.schema = schema
        self.conn = None
        self.cur = None
        logger.info(f"Inizializzato gestore per database {dbname} schema {schema}")
    
    def connect(self):
        """Stabilisce una connessione al database."""
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
            self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            self.cur.execute(f"SET search_path TO {self.schema}")
            logger.info("Connessione stabilita con successo")
            return True
        except Exception as e:
            logger.error(f"Errore durante la connessione: {e}")
            return False
    
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


# Esempio di utilizzo
if __name__ == "__main__":
    # Crea un'istanza del gestore
    db = CatastoDBManager(
        dbname="catasto_storico", 
        user="postgres", 
        password="password",  # Sostituisci con la tua password
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