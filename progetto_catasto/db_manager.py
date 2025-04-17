#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestore Database Catasto Storico
================================
Modulo per la gestione del database catastale con supporto 
per operazioni CRUD e chiamate alle stored procedure.

Basato sul file catasto_db_manager.py originale
"""

import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
import json
import sys
import logging
import os
import time
import subprocess
from datetime import date, datetime
import tempfile
import csv
from typing import List, Dict, Any, Optional, Tuple, Union

# Importa la configurazione
from config import setup_logging, DEFAULT_BACKUP_DIR

# Configurazione logging
logger = setup_logging()

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
        """Stabilisce una connessione al database con retry automatico."""
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                self.conn = psycopg2.connect(**self.conn_params)
                self.conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
                self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                self.cur.execute(f"SET search_path TO {self.schema}")
                logger.info("Connessione stabilita con successo")
                return True
            except Exception as e:
                attempt += 1
                wait_time = 2 ** attempt  # Backoff esponenziale
                logger.warning(f"Tentativo {attempt}/{max_attempts} fallito: {e}. Nuovo tentativo tra {wait_time} secondi")
                
                if attempt < max_attempts:
                    time.sleep(wait_time)
        
        logger.error(f"Impossibile connettersi al database dopo {max_attempts} tentativi")
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
    
    def transaction(self):
        """Context manager per le transazioni."""
        class Transaction:
            def __init__(self, db_manager):
                self.db_manager = db_manager
                
            def __enter__(self):
                if not self.db_manager.conn or self.db_manager.conn.closed:
                    self.db_manager.connect()
                return self.db_manager
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    logger.error(f"Errore durante la transazione: {exc_val}")
                    self.db_manager.rollback()
                    return False
                self.db_manager.commit()
                return True
            
        return Transaction(self)
    
    # OPERAZIONI CRUD
    
    def get_comuni(self) -> List[Dict]:
        """
        Recupera tutti i comuni dal database.
        
        Returns:
            List[Dict]: Lista di comuni
        """
        query = "SELECT * FROM comune ORDER BY nome"
        if self.execute_query(query):
            return self.fetchall()
        return []
    
    def get_possessori_by_comune(self, comune_nome: str) -> List[Dict]:
        """
        Recupera tutti i possessori di un comune.
        
        Args:
            comune_nome: Nome del comune
            
        Returns:
            List[Dict]: Lista di possessori
        """
        query = "SELECT * FROM possessore WHERE comune_nome = %s ORDER BY nome_completo"
        if self.execute_query(query, (comune_nome,)):
            return self.fetchall()
        return []
    
    def get_partite_by_comune(self, comune_nome: str) -> List[Dict]:
        """
        Recupera tutte le partite di un comune.
        
        Args:
            comune_nome: Nome del comune
            
        Returns:
            List[Dict]: Lista di partite
        """
        query = """
        SELECT p.*, 
               string_agg(DISTINCT pos.nome_completo, ', ') as possessori,
               COUNT(DISTINCT i.id) as num_immobili
        FROM partita p
        LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
        LEFT JOIN possessore pos ON pp.possessore_id = pos.id
        LEFT JOIN immobile i ON p.id = i.partita_id
        WHERE p.comune_nome = %s
        GROUP BY p.id
        ORDER BY p.numero_partita
        """
        if self.execute_query(query, (comune_nome,)):
            return self.fetchall()
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
        
        # Recupera immobili
        query_immobili = """
        SELECT i.*, l.nome as localita_nome, l.tipo as localita_tipo
        FROM immobile i
        JOIN localita l ON i.localita_id = l.id
        WHERE i.partita_id = %s
        """
        self.execute_query(query_immobili, (partita_id,))
        partita['immobili'] = self.fetchall()
        
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
            conditions.append("p.comune_nome = %s")
            params.append(comune_nome)
        
        if numero_partita:
            conditions.append("p.numero_partita = %s")
            params.append(numero_partita)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY p.comune_nome, p.numero_partita"
        
        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []
    
    def search_advanced(self, search_params):
        """Ricerca avanzata con supporto per filtri complessi."""
        conditions = []
        params = []
        
        query = """
        WITH partite_search AS (
            SELECT 
                p.id, p.comune_nome, p.numero_partita, 
                p.tipo, p.stato, p.data_impianto, p.data_chiusura,
                string_agg(DISTINCT pos.nome_completo, ', ') as possessori,
                COUNT(DISTINCT i.id) as num_immobili
            FROM partita p
            LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
            LEFT JOIN possessore pos ON pp.possessore_id = pos.id
            LEFT JOIN immobile i ON p.id = i.partita_id
        """
        
        # Costruisci filtri dinamicamente
        if 'comune_nome' in search_params and search_params['comune_nome']:
            conditions.append("p.comune_nome = %s")
            params.append(search_params['comune_nome'])
        
        if 'numero_partita' in search_params and search_params['numero_partita']:
            conditions.append("p.numero_partita = %s")
            params.append(search_params['numero_partita'])
        
        if 'possessore' in search_params and search_params['possessore']:
            conditions.append("pos.nome_completo ILIKE %s")
            params.append(f"%{search_params['possessore']}%")
        
        if 'immobile_natura' in search_params and search_params['immobile_natura']:
            conditions.append("EXISTS (SELECT 1 FROM immobile i2 WHERE i2.partita_id = p.id AND i2.natura ILIKE %s)")
            params.append(f"%{search_params['immobile_natura']}%")
        
        if 'data_inizio' in search_params and search_params['data_inizio']:
            conditions.append("p.data_impianto >= %s")
            params.append(search_params['data_inizio'])
        
        if 'data_fine' in search_params and search_params['data_fine']:
            conditions.append("(p.data_chiusura IS NULL OR p.data_chiusura <= %s)")
            params.append(search_params['data_fine'])
        
        if 'stato' in search_params and search_params['stato']:
            conditions.append("p.stato = %s")
            params.append(search_params['stato'])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += """
            GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato, p.data_impianto, p.data_chiusura
        )
        SELECT * FROM partite_search
        ORDER BY comune_nome, numero_partita
        """
        
        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []
    
    # CHIAMATE ALLE STORED PROCEDURE
    
    def registra_nuova_proprieta(self, comune_nome: str, numero_partita: int, 
                               data_impianto: date, possessori: List[Dict], 
                               immobili: List[Dict]) -> bool:
        """
        Registra una nuova proprietà utilizzando la stored procedure.
        
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
            with self.transaction():
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
                    logger.info(f"Registrata nuova proprietà: {comune_nome}, partita {numero_partita}")
                    return True
                
                return False
        except Exception as e:
            logger.error(f"Errore durante la registrazione della proprietà: {e}")
            return False
    
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
            with self.transaction():
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
                    logger.info(f"Registrato passaggio di proprietà: origine {partita_origine_id}, nuova partita {numero_partita}")
                    return True
                
                return False
        except Exception as e:
            logger.error(f"Errore durante la registrazione del passaggio di proprietà: {e}")
            return False
    
    def registra_frazionamento(self, partita_origine_id: int, data_variazione: date, 
                              tipo_contratto: str, data_contratto: date, 
                              nuove_partite: List[Dict], **kwargs) -> bool:
        """
        Registra un frazionamento di proprietà utilizzando la stored procedure.
        
        Args:
            partita_origine_id: ID della partita di origine
            data_variazione: Data della variazione
            tipo_contratto: Tipo di contratto
            data_contratto: Data del contratto
            nuove_partite: Lista delle nuove partite da creare
            **kwargs: Altri parametri opzionali
            
        Returns:
            bool: True se l'operazione è avvenuta con successo, False altrimenti
        """
        try:
            with self.transaction():
                # Parametri opzionali
                notaio = kwargs.get('notaio')
                repertorio = kwargs.get('repertorio')
                note = kwargs.get('note')
                
                # Converte in JSON se necessario
                nuove_partite_json = json.dumps(nuove_partite)
                
                call_proc = """
                CALL registra_frazionamento(%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                success = self.execute_query(call_proc, (
                    partita_origine_id,
                    data_variazione,
                    tipo_contratto,
                    data_contratto,
                    nuove_partite_json,
                    notaio,
                    repertorio,
                    note
                ))
                
                if success:
                    logger.info(f"Registrato frazionamento della partita {partita_origine_id} in {len(nuove_partite)} nuove partite")
                    return True
                
                return False
        except Exception as e:
            logger.error(f"Errore durante la registrazione del frazionamento: {e}")
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
            with self.transaction():
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
                    logger.info(f"Registrata consultazione: {richiedente}, {data}")
                    return True
                
                return False
        except Exception as e:
            logger.error(f"Errore durante la registrazione della consultazione: {e}")
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
    
    def get_immobili_partita(self, partita_id: int) -> List[Dict]:
        """
        Recupera gli immobili di una partita.
        
        Args:
            partita_id: ID della partita
            
        Returns:
            List[Dict]: Lista di immobili
        """
        query = """
        SELECT i.id, i.natura, l.nome as localita_nome, i.classificazione
        FROM immobile i
        JOIN localita l ON i.localita_id = l.id
        WHERE i.partita_id = %s
        """
        
        if self.execute_query(query, (partita_id,)):
            return self.fetchall()
        return []
    
    def get_possessori_partita(self, partita_id: int) -> List[Dict]:
        """
        Recupera i possessori di una partita.
        
        Args:
            partita_id: ID della partita
            
        Returns:
            List[Dict]: Lista di possessori
        """
        query = """
        SELECT pos.id, pos.nome_completo
        FROM possessore pos
        JOIN partita_possessore pp ON pos.id = pp.possessore_id
        WHERE pp.partita_id = %s
        """
        
        if self.execute_query(query, (partita_id,)):
            return self.fetchall()
        return []
    
    def verifica_integrita_database(self) -> Tuple[bool, str]:
        """
        Verifica l'integrità del database utilizzando la procedura.
        
        Returns:
            Tuple[bool, str]: Tuple con stato e messaggio
        """
        try:
            # Crea una tabella temporanea per ottenere l'output
            self.execute_query("DROP TABLE IF EXISTS temp_output")
            self.execute_query("CREATE TEMP TABLE temp_output (message TEXT)")
            
            # Cattura l'output della procedura
            self.execute_query("""
            DO $$
            DECLARE
                v_problemi_trovati BOOLEAN;
                v_output TEXT := '';
            BEGIN
                CALL verifica_integrita_database(v_problemi_trovati);
                
                -- Inserisci il risultato nella tabella temporanea
                INSERT INTO temp_output VALUES ('Problemi trovati: ' || v_problemi_trovati);
            END $$;
            """)
            
            # Recupera il risultato
            self.execute_query("SELECT * FROM temp_output")
            result = self.fetchone()
            message = result.get('message', '') if result else ''
            
            # Pulizia
            self.execute_query("DROP TABLE IF EXISTS temp_output")
            
            return 'true' in message.lower(), "Verifica completata. " + message
        except Exception as e:
            logger.error(f"Errore durante la verifica dell'integrità: {e}")
            return False, f"Errore durante la verifica dell'integrità: {e}"
    
    def ripara_problemi_database(self, correzione_automatica: bool = False) -> Tuple[bool, str]:
        """
        Ripara problemi comuni del database.
        
        Args:
            correzione_automatica: Flag per abilitare la correzione automatica
        
        Returns:
            Tuple[bool, str]: Tuple con stato e messaggio
        """
        try:
            self.execute_query("CALL ripara_problemi_database(%s)", (correzione_automatica,))
            self.commit()
            msg = "Riparazione automatica completata." if correzione_automatica else "Verifica completata senza riparazioni."
            return True, msg
        except Exception as e:
            logger.error(f"Errore durante la riparazione: {e}")
            return False, f"Errore durante la riparazione: {e}"
    
    def backup_logico_dati(self, directory: str = "/tmp", prefisso_file: str = "catasto_backup") -> Tuple[bool, str]:
        """
        Esegue un backup logico dei dati.
        
        Args:
            directory: Directory dove salvare il backup
            prefisso_file: Prefisso del nome del file
            
        Returns:
            Tuple[bool, str]: Tuple con stato e messaggio
        """
        try:
            self.execute_query("CALL backup_logico_dati(%s, %s)", (directory, prefisso_file))
            self.commit()
            return True, f"Backup pianificato con successo nella directory {directory}."
        except Exception as e:
            logger.error(f"Errore durante il backup: {e}")
            return False, f"Errore durante il backup: {e}"
    
    def backup_database(self, backup_dir=DEFAULT_BACKUP_DIR, include_schema=True, include_data=True):
        """Esegue un backup completo del database."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"catasto_backup_{timestamp}.sql"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Assicurati che la directory esista
        os.makedirs(backup_dir, exist_ok=True)
        
        # Costruisci il comando pg_dump
        cmd_parts = [
            "pg_dump",
            f"--host={self.conn_params['host']}",
            f"--port={self.conn_params['port']}",
            f"--username={self.conn_params['user']}",
            f"--dbname={self.conn_params['dbname']}",
            f"--schema={self.schema}"
        ]
        
        if not include_schema:
            cmd_parts.append("--data-only")
        if not include_data:
            cmd_parts.append("--schema-only")
        
        cmd_parts.append(f"--file={backup_path}")
        
        # Esegui il backup
        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = self.conn_params["password"]
            
            process = subprocess.run(cmd_parts, env=env, check=True, capture_output=True)
            
            if process.returncode == 0:
                logger.info(f"Backup eseguito con successo: {backup_path}")
                return True, backup_path
            else:
                error = process.stderr.decode()
                logger.error(f"Errore durante il backup: {error}")
                return False, error
        except Exception as e:
            logger.error(f"Errore durante il backup: {e}")
            return False, str(e)
    
    def sincronizza_con_archivio_stato(self, partita_id: int, riferimento_archivio: str, 
                                     data_sincronizzazione: date = None) -> Tuple[bool, str]:
        """
        Sincronizza una partita con l'Archivio di Stato.
        
        Args:
            partita_id: ID della partita
            riferimento_archivio: Riferimento all'archivio
            data_sincronizzazione: Data della sincronizzazione
            
        Returns:
            Tuple[bool, str]: Tuple con stato e messaggio
        """
        try:
            if data_sincronizzazione is None:
                data_sincronizzazione = date.today()
            
            self.execute_query("CALL sincronizza_con_archivio_stato(%s, %s, %s)", 
                            (partita_id, riferimento_archivio, data_sincronizzazione))
            self.commit()
            return True, f"Sincronizzazione completata con successo per la partita {partita_id}."
        except Exception as e:
            logger.error(f"Errore durante la sincronizzazione: {e}")
            return False, f"Errore durante la sincronizzazione: {e}"
    
    # Metodi aggiuntivi per l'interfaccia grafica
    
    def cerca_consultazioni(self, data_inizio=None, data_fine=None, richiedente=None, funzionario=None) -> List[Dict]:
        """
        Cerca consultazioni in base ai criteri specificati.
        
        Args:
            data_inizio: Data di inizio periodo
            data_fine: Data di fine periodo
            richiedente: Nome del richiedente (ricerca parziale)
            funzionario: Nome del funzionario (ricerca parziale)
            
        Returns:
            List[Dict]: Lista di consultazioni
        """
        conditions = []
        params = []
        
        query = """
        SELECT * FROM consultazione
        """
        
        if data_inizio:
            conditions.append("data >= %s")
            params.append(data_inizio)
        
        if data_fine:
            conditions.append("data <= %s")
            params.append(data_fine)
        
        if richiedente:
            conditions.append("richiedente ILIKE %s")
            params.append(f"%{richiedente}%")
        
        if funzionario:
            conditions.append("funzionario_autorizzante ILIKE %s")
            params.append(f"%{funzionario}%")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY data DESC"
        
        if self.execute_query(query, tuple(params)):
            return self.fetchall()
        return []
    
    def aggiorna_consultazione(self, id_consultazione, data=None, richiedente=None, documento_identita=None, 
                             motivazione=None, materiale_consultato=None, funzionario_autorizzante=None) -> bool:
        """
        Aggiorna una consultazione esistente.
        
        Args:
            id_consultazione: ID della consultazione
            data: Nuova data
            richiedente: Nuovo richiedente
            documento_identita: Nuovo documento
            motivazione: Nuova motivazione
            materiale_consultato: Nuovo materiale
            funzionario_autorizzante: Nuovo funzionario
            
        Returns:
            bool: True se l'operazione è avvenuta con successo, False altrimenti
        """
        try:
            with self.transaction():
                query = """
                CALL aggiorna_consultazione(%s, %s, %s, %s, %s, %s, %s)
                """
                
                success = self.execute_query(query, (
                    id_consultazione, data, richiedente, documento_identita, 
                    motivazione, materiale_consultato, funzionario_autorizzante
                ))
                
                if success:
                    logger.info(f"Aggiornata consultazione: {id_consultazione}")
                    return True
                
                return False
        except Exception as e:
            logger.error(f"Errore durante l'aggiornamento della consultazione: {e}")
            return False
    
    def elimina_consultazione(self, id_consultazione) -> bool:
        """
        Elimina una consultazione.
        
        Args:
            id_consultazione: ID della consultazione
            
        Returns:
            bool: True se l'operazione è avvenuta con successo, False altrimenti
        """
        try:
            with self.transaction():
                query = """
                CALL elimina_consultazione(%s)
                """
                
                success = self.execute_query(query, (id_consultazione,))
                
                if success:
                    logger.info(f"Eliminata consultazione: {id_consultazione}")
                    return True
                
                return False
        except Exception as e:
            logger.error(f"Errore durante l'eliminazione della consultazione: {e}")
            return False
    
    # Nuovi metodi per esportazione/importazione
    
    def export_to_csv(self, data, filename):
        """Esporta dati in un file CSV."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if not data:
                    return True
                    
                # Usa le chiavi del primo elemento come intestazioni
                fieldnames = data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
                    
            logger.info(f"Dati esportati con successo in {filename}")
            return True
        except Exception as e:
            logger.error(f"Errore durante l'esportazione CSV: {e}")
            return False

    def import_from_csv(self, filename, table_name):
        """Importa dati da un file CSV in una tabella."""
        try:
            with self.transaction() as tx:
                with open(filename, 'r', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    
                    for row in reader:
                        # Costruisce la query di inserimento dinamicamente
                        columns = ', '.join(row.keys())
                        placeholders = ', '.join(['%s'] * len(row))
                        
                        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                        
                        tx.execute_query(query, tuple(row.values()))
                
                logger.info(f"Dati importati con successo da {filename}")
                return True
        except Exception as e:
            logger.error(f"Errore durante l'importazione CSV: {e}")
            return False
    
    # Classe per la gestione degli utenti
    
    class UserAuthManager:
        """Gestisce l'autenticazione degli utenti."""
        
        def __init__(self, db_manager):
            self.db_manager = db_manager
            self.current_user = None
        
        def login(self, username, password):
            """Autentica un utente."""
            query = """
            SELECT id, username, nome_completo, email, ruolo 
            FROM utente 
            WHERE username = %s AND password_hash = %s AND attivo = TRUE
            """
            
            # Nota: in produzione, usare una funzione di hash per la password
            # password_hash = hashlib.sha256(password.encode()).hexdigest()
            password_hash = password  # Solo per test
            
            if self.db_manager.execute_query(query, (username, password_hash)):
                user = self.db_manager.fetchone()
                if user:
                    self.current_user = user
                    
                    # Registra l'accesso
                    self.db_manager.execute_query(
                        "CALL registra_accesso(%s, %s, %s, %s, %s)",
                        (user['id'], 'login', '127.0.0.1', 'Python App', True)
                    )
                    self.db_manager.commit()
                    
                    return True, user
            
            return False, "Credenziali non valide"
        
        def logout(self):
            """Disconnette l'utente corrente."""
            if self.current_user:
                self.db_manager.execute_query(
                    "CALL registra_accesso(%s, %s, %s, %s, %s)",
                    (self.current_user['id'], 'logout', '127.0.0.1', 'Python App', True)
                )
                self.db_manager.commit()
                self.current_user = None
            
            return True
        
        def check_permission(self, permission_name):
            """Verifica se l'utente corrente ha un permesso specifico."""
            if not self.current_user:
                return False
            
            # Gli amministratori hanno tutti i permessi
            if self.current_user['ruolo'] == 'admin':
                return True
            
            query = """
            SELECT ha_permesso(%s, %s) AS has_permission
            """
            
            if self.db_manager.execute_query(query, (self.current_user['id'], permission_name)):
                result = self.db_manager.fetchone()
                return result and result.get('has_permission', False)
            
            return False
        
    def create_map_view(self, parent, immobili):
        """Crea una visualizzazione della mappa con gli immobili."""
        try:
            import folium
            from folium.plugins import MarkerCluster
            import webbrowser
            import tempfile
            
            # Crea una mappa centrata in Italia
            m = folium.Map(location=[42.504154, 12.646361], zoom_start=6)
            
            # Aggiungi un cluster di marker
            marker_cluster = MarkerCluster().add_to(m)
            
            # Aggiungi i marker per ogni immobile
            for imm in immobili:
                # Qui dovresti avere le coordinate reali
                # Per ora usiamo coordinate fittizie basate su ID
                lat = 41.9 + (imm['id'] % 100) / 1000
                lon = 12.5 + (imm['id'] % 50) / 1000
                
                popup_text = f"""
                <b>{imm['natura']}</b><br>
                Località: {imm['localita_nome']}<br>
                Classificazione: {imm.get('classificazione', 'N/D')}<br>
                Partita: {imm.get('partita_numero', 'N/D')}
                """
                
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=imm['natura']
                ).add_to(marker_cluster)
            
            # Salva la mappa in un file temporaneo e aprila nel browser
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
            m.save(tmp.name)
            webbrowser.open('file://' + tmp.name)
            
            return True
        except ImportError:
            logger.warning("Package folium non installato. Installare con: pip install folium")
            return False
        except Exception as e:
            logger.error(f"Errore durante la creazione della mappa: {e}")
            return False