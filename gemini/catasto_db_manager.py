#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestore Database Catasto Storico
================================
Script per la gestione del database catastale con supporto
per operazioni CRUD, chiamate alle stored procedure, gestione utenti,
audit, backup e funzionalità avanzate.

Autore: Marco Santoro (Versione rivista e pulita)
Data: 28/04/2025
"""

import psycopg2
import psycopg2.errors # Importa specificamente gli errori
from psycopg2.extras import DictCursor
from psycopg2.extensions import ISOLATION_LEVEL_SERIALIZABLE
import sys
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import json
import uuid
import os # Importato per generate_backup_script (potrebbe servire)

# --- Configurazione Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("catasto_db.log"),
        logging.StreamHandler(sys.stdout) # Mostra log anche a console
    ]
)
logger = logging.getLogger("CatastoDB")
# logger.setLevel(logging.DEBUG) # Decommenta per vedere query mogrify

# --- Classe CatastoDBManager ---

class CatastoDBManager:
    """Classe per la gestione delle operazioni sul database catastale."""

    def __init__(self, dbname: str = "catasto_storico", user: str = "postgres",
                 password: str = "Markus74", host: str = "localhost", port: int = 5432,
                 schema: str = "catasto"):
        """Inizializza il gestore del database."""
        self.conn_params = {
            "dbname": dbname, "user": user, "password": password,
            "host": host, "port": port
        }
        self.schema = schema
        self.conn = None
        self.cur = None
        logger.info(f"Inizializzato gestore per database {dbname} schema {schema}")

    # --- Metodi Base Connessione e Transazione ---

    def connect(self) -> bool:
        """Stabilisce una connessione al database."""
        try:
            if self.conn and not self.conn.closed:
                logger.warning("Chiusura connessione DB esistente prima di riconnettere.")
                self.disconnect()

            self.conn = psycopg2.connect(**self.conn_params)
            # Imposta un livello di isolamento robusto
            self.conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
            self.cur = self.conn.cursor(cursor_factory=DictCursor)
            # Imposta lo schema di default per la sessione
            self.cur.execute(f"SET search_path TO {self.schema}, public")
            logger.info("Connessione stabilita con successo")
            return True
        except psycopg2.OperationalError as op_err:
             logger.error(f"Errore operativo durante la connessione (controllare DB e parametri): {op_err}")
             self.conn = None; self.cur = None; return False
        except Exception as e:
            logger.error(f"Errore generico durante la connessione: {e}")
            self.conn = None; self.cur = None; return False

    def disconnect(self):
        """Chiude la connessione al database."""
        try:
            # Prova a resettare il contesto utente prima di chiudere
            if self.conn and not self.conn.closed:
                 self.clear_session_app_user()
            if self.cur: self.cur.close()
            if self.conn: self.conn.close()
            logger.info("Disconnessione completata")
        except Exception as e:
            logger.error(f"Errore durante la disconnessione: {e}")
        finally:
             self.conn = None; self.cur = None

    def commit(self):
        """Conferma le modifiche al database."""
        if self.conn and not self.conn.closed:
             try:
                 self.conn.commit()
                 logger.info("Commit eseguito.")
             except Exception as e:
                 logger.error(f"Errore commit: {e}")
                 self.rollback() # Tenta il rollback in caso di errore commit
        else: logger.warning("Tentativo di commit senza connessione attiva.")

    def rollback(self):
        """Annulla le modifiche al database."""
        if self.conn and not self.conn.closed:
             try:
                 self.conn.rollback()
                 logger.info("Rollback eseguito.")
             except Exception as e:
                 logger.error(f"Errore rollback: {e}")
        else: logger.warning("Tentativo di rollback senza connessione attiva.")

    def execute_query(self, query: str, params: Union[tuple, Dict, None] = None) -> bool:
        """
        Esegue una query SQL, gestendo errori di connessione e RILANCIANDO altri errori DB.

        Args:
            query: Query SQL da eseguire.
            params: Parametri per la query (tuple o dict).

        Returns:
            bool: True se l'esecuzione non ha sollevato eccezioni DB, False per errori di connessione.
        Raises:
            psycopg2.Error: Rilancia altri errori del database (es. IntegrityError, DataError).
            Exception: Rilancia errori Python generici.
        """
        attempt_reconnect = True
        while True:
            try:
                # 1. Verifica/Stabilisci Connessione
                if not self.conn or self.conn.closed:
                    if not attempt_reconnect:
                        logger.error("Riconnessione fallita definitivamente.")
                        return False # Già tentato riconnessione
                    logger.warning("Connessione non attiva. Tentativo di riconnessione...")
                    if not self.connect():
                        return False # Riconnessione fallita
                    attempt_reconnect = False # Riconnetti solo una volta

                # 2. Assicura Cursore Valido
                if self.cur is None or self.cur.closed:
                     logger.warning("Cursore non valido o chiuso. Creazione nuovo cursore.")
                     self.cur = self.conn.cursor(cursor_factory=DictCursor)
                     # Reimposta lo search_path per il nuovo cursore
                     self.cur.execute(f"SET search_path TO {self.schema}, public")

                # 3. Esegui Query
                logger.debug(f"Esecuzione query: {self.cur.mogrify(query, params)}")
                self.cur.execute(query, params)
                # Se l'esecuzione arriva qui senza eccezioni, è andata bene
                return True

            # 4. Gestione Errori di Connessione (per Riconnessione)
            except (psycopg2.InterfaceError, psycopg2.OperationalError) as conn_err:
                logger.error(f"Errore di connessione DB: {conn_err}")
                if not attempt_reconnect:
                    logger.error("Riconnessione già tentata. Operazione fallita.")
                    return False # Fallimento dopo tentativo di riconnessione
                self.disconnect() # Chiudi connessione problematica
                attempt_reconnect = False # Tenta la riconnessione solo una volta nel prossimo ciclo
                logger.info("Riconnessione in corso...")
                # Il ciclo while riproverà la connessione all'inizio

            # 5. Gestione Altri Errori DB (Log + Rollback + Rilancio)
            except psycopg2.Error as db_err:
                 logger.error(f"Errore DB specifico rilevato: {db_err.__class__.__name__} - {db_err}")
                 logger.error(f"SQLSTATE: {db_err.pgcode}") # Codice errore SQL
                 # Logga query e parametri per debug
                 try:
                     # Mostra query renderizzata se possibile
                     logger.error(f"Query renderizzata: {self.cur.mogrify(query, params)}")
                 except Exception:
                     logger.error(f"Query (originale): {query}")
                     logger.error(f"Parametri: {params}")
                 self.rollback() # Annulla transazione in caso di errore DB
                 raise db_err # RILANCIA l'eccezione per gestione specifica nel chiamante

            # 6. Gestione Errori Python Generici (Log + Rollback + Rilancio)
            except Exception as e:
                logger.exception(f"Errore Python imprevisto durante esecuzione query:") # Logga traceback
                try:
                     logger.error(f"Query renderizzata: {self.cur.mogrify(query, params)}")
                except Exception:
                     logger.error(f"Query (originale): {query}")
                     logger.error(f"Parametri: {params}")
                self.rollback() # Annulla transazione anche per errori Python generici
                raise e # RILANCIA l'eccezione Python

    def fetchall(self) -> List[Dict]:
        """Recupera tutti i risultati dell'ultima query come lista di dizionari."""
        if self.cur and not self.cur.closed:
             try:
                 # Usa list comprehension per convertire tuple DictRow in dict standard
                 return [dict(row) for row in self.cur.fetchall()]
             except psycopg2.ProgrammingError:
                 logger.warning("Nessun risultato da recuperare per l'ultima query.")
                 return [] # Nessun risultato o cursore non valido per fetch
             except Exception as e:
                 logger.error(f"Errore durante fetchall: {e}")
                 return []
        logger.warning("Tentativo di fetchall senza cursore valido.")
        return []

    def fetchone(self) -> Optional[Dict]:
        """Recupera una riga di risultati dall'ultima query come dizionario."""
        if self.cur and not self.cur.closed:
             try:
                 row = self.cur.fetchone()
                 return dict(row) if row else None # Converte DictRow in dict standard se esiste
             except psycopg2.ProgrammingError:
                 logger.warning("Nessun risultato da recuperare per l'ultima query.")
                 return None # Nessun risultato o cursore non valido per fetch
             except Exception as e:
                 logger.error(f"Errore durante fetchone: {e}")
                 return None
        logger.warning("Tentativo di fetchone senza cursore valido.")
        return None

    # --- Metodi CRUD e Ricerca Base ---

    def get_comuni(self, search_term: Optional[str] = None) -> List[Dict]:
        """Recupera comuni con filtro opzionale per nome."""
        try:
            if search_term:
                query = "SELECT nome, provincia, regione FROM comune WHERE nome ILIKE %s ORDER BY nome"
                params = (f"%{search_term}%",)
            else:
                query = "SELECT nome, provincia, regione FROM comune ORDER BY nome"
                params = None
            if self.execute_query(query, params):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_comuni: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in get_comuni: {e}")
        return []

    def check_possessore_exists(self, nome_completo: str, comune_nome: Optional[str] = None) -> Optional[int]:
        """Verifica se un possessore esiste nel comune specificato (o ovunque) e ritorna il suo ID."""
        try:
            if comune_nome:
                query = "SELECT id FROM possessore WHERE nome_completo = %s AND comune_nome = %s AND attivo = TRUE"
                params = (nome_completo, comune_nome)
            else:
                query = "SELECT id FROM possessore WHERE nome_completo = %s AND attivo = TRUE"
                params = (nome_completo,)
            if self.execute_query(query, params):
                result = self.fetchone()
                return result['id'] if result else None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in check_possessore_exists: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in check_possessore_exists: {e}")
        return None

    def insert_possessore(self, comune_nome: str, cognome_nome: str, paternita: Optional[str],
                        nome_completo: str, attivo: bool = True) -> Optional[int]:
        """Inserisce un nuovo possessore usando la procedura SQL. Ritorna l'ID."""
        try:
            # Usa la procedura SQL definita in 03_funzioni-procedure.sql
            # CALL inserisci_possessore(VARCHAR, VARCHAR, VARCHAR, VARCHAR, BOOLEAN)
            if self.execute_query("CALL inserisci_possessore(%s, %s, %s, %s, %s)",
                                  (comune_nome, cognome_nome, paternita, nome_completo, attivo)):
                self.commit()
                # Recupera l'ID dell'ultimo inserito che matcha (per sicurezza)
                return self.check_possessore_exists(nome_completo, comune_nome)
            return None # Execute_query ha fallito (es. errore connessione)
        except psycopg2.Error as db_err: # Errore DB rilanciato da execute_query
            logger.error(f"Errore DB specifico in insert_possessore: {db_err}")
            # Rollback è già stato fatto da execute_query
            return None
        except Exception as e: # Errore Python generico
            logger.error(f"Errore Python in insert_possessore: {e}")
            self.rollback() # Assicurati rollback per errori Python
            return None

    def get_possessori_by_comune(self, comune_nome: str) -> List[Dict]:
        """Recupera possessori per comune (ricerca esatta)."""
        try:
            query = "SELECT id, comune_nome, cognome_nome, paternita, nome_completo, attivo FROM possessore WHERE comune_nome = %s ORDER BY nome_completo"
            if self.execute_query(query, (comune_nome,)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_possessori_by_comune: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in get_possessori_by_comune: {e}")
        return []

    def insert_localita(self, comune_nome: str, nome: str, tipo: str,
                      civico: Optional[int] = None) -> Optional[int]:
        """Inserisce o recupera una località, gestendo conflitti. Ritorna l'ID."""
        # Definito in 02_creazione-schema-tabelle.sql, UNIQUE(comune_nome, nome, civico)
        query_insert = """
            INSERT INTO localita (comune_nome, nome, tipo, civico)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (comune_nome, nome, civico) DO NOTHING
            RETURNING id
        """
        query_select = """
            SELECT id FROM localita
            WHERE comune_nome = %s AND nome = %s AND (
                  (civico IS NULL AND %s IS NULL) OR (civico = %s)
            )
        """
        try:
            inserted_id = None
            # Tenta l'inserimento
            if self.execute_query(query_insert, (comune_nome, nome, tipo, civico)):
                result = self.fetchone()
                if result:
                    inserted_id = result['id']
                    self.commit() # Commit solo se l'inserimento ha avuto successo
                    logger.info(f"Località '{nome}' inserita con ID: {inserted_id}")
                    return inserted_id
            elif self.conn is None or self.conn.closed: # Errore di connessione durante execute_query
                return None

            # Se l'ID non è stato ritornato (conflitto o errore nell'insert), prova a selezionare l'esistente
            logger.info(f"Località '{nome}' potrebbe esistere già. Tentativo di selezione.")
            if self.execute_query(query_select, (comune_nome, nome, civico, civico)):
                existing = self.fetchone()
                if existing:
                    logger.info(f"Località '{nome}' trovata con ID: {existing['id']}")
                    return existing['id']
                else:
                    logger.warning(f"Località '{nome}' non trovata dopo tentativo insert/select.")
                    return None # Non trovata nemmeno dopo il select
            return None # Errore nella select

        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in insert_localita '{nome}': {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python in insert_localita '{nome}': {e}")
            self.rollback()
            return None

    def get_partite_by_comune(self, comune_nome: str) -> List[Dict]:
        """Recupera partite per comune (ricerca esatta) con dettagli aggregati."""
        try:
            query = """
                SELECT
                    p.id, p.comune_nome, p.numero_partita, p.tipo, p.data_impianto,
                    p.data_chiusura, p.stato,
                    string_agg(DISTINCT pos.nome_completo, ', ') as possessori,
                    COUNT(DISTINCT i.id) as num_immobili
                FROM partita p
                LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
                LEFT JOIN possessore pos ON pp.possessore_id = pos.id
                LEFT JOIN immobile i ON p.id = i.partita_id
                WHERE p.comune_nome = %s
                GROUP BY p.id -- Raggruppa per chiave primaria della partita
                ORDER BY p.numero_partita
            """
            if self.execute_query(query, (comune_nome,)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_partite_by_comune: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in get_partite_by_comune: {e}")
        return []

    def get_partita_details(self, partita_id: int) -> Optional[Dict]:
        """Recupera dettagli completi di una partita (info base, possessori, immobili, variazioni)."""
        try:
            partita = {}
            # Info base partita
            query_partita = "SELECT * FROM partita WHERE id = %s"
            if not self.execute_query(query_partita, (partita_id,)): return None
            partita_base = self.fetchone()
            if not partita_base:
                logger.warning(f"Partita con ID {partita_id} non trovata.")
                return None
            partita.update(partita_base)

            # Possessori
            query_poss = """
                SELECT pos.id, pos.nome_completo, pp.titolo, pp.quota
                FROM possessore pos
                JOIN partita_possessore pp ON pos.id = pp.possessore_id
                WHERE pp.partita_id = %s
                ORDER BY pos.nome_completo
            """
            partita['possessori'] = self.fetchall() if self.execute_query(query_poss, (partita_id,)) else []

            # Immobili
            query_imm = """
                SELECT i.id, i.natura, i.numero_piani, i.numero_vani, i.consistenza, i.classificazione,
                       l.nome as localita_nome, l.tipo as localita_tipo, l.civico
                FROM immobile i
                JOIN localita l ON i.localita_id = l.id
                WHERE i.partita_id = %s
                ORDER BY l.nome, i.natura
            """
            partita['immobili'] = self.fetchall() if self.execute_query(query_imm, (partita_id,)) else []

            # Variazioni (e contratti associati)
            query_var = """
                SELECT v.id, v.tipo, v.data_variazione, v.numero_riferimento, v.nominativo_riferimento,
                       v.partita_origine_id, v.partita_destinazione_id,
                       c.tipo as tipo_contratto, c.data_contratto, c.notaio, c.repertorio, c.note as contratto_note
                FROM variazione v
                LEFT JOIN contratto c ON v.id = c.variazione_id
                WHERE v.partita_origine_id = %s OR v.partita_destinazione_id = %s
                ORDER BY v.data_variazione DESC
            """
            # Passa l'ID due volte per OR condition
            partita['variazioni'] = self.fetchall() if self.execute_query(query_var, (partita_id, partita_id)) else []

            return partita
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_partita_details (ID: {partita_id}): {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in get_partita_details (ID: {partita_id}): {e}")
        return None

    def search_partite(self, comune_nome: Optional[str] = None, numero_partita: Optional[int] = None,
                      possessore: Optional[str] = None, immobile_natura: Optional[str] = None) -> List[Dict]:
        """Ricerca partite con filtri multipli (ricerca semplice)."""
        try:
            conditions = []
            params = []
            joins = ""
            query_base = "SELECT DISTINCT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato FROM partita p"

            if possessore:
                # Assicurati che il join venga aggiunto solo una volta
                if "partita_possessore pp" not in joins:
                    joins += " LEFT JOIN partita_possessore pp ON p.id = pp.partita_id LEFT JOIN possessore pos ON pp.possessore_id = pos.id"
                conditions.append("pos.nome_completo ILIKE %s")
                params.append(f"%{possessore}%")

            if immobile_natura:
                 # Assicurati che il join venga aggiunto solo una volta
                if "immobile i" not in joins:
                    joins += " LEFT JOIN immobile i ON p.id = i.partita_id"
                conditions.append("i.natura ILIKE %s")
                params.append(f"%{immobile_natura}%")

            if comune_nome:
                conditions.append("p.comune_nome ILIKE %s")
                params.append(f"%{comune_nome}%")

            if numero_partita is not None:
                conditions.append("p.numero_partita = %s")
                params.append(numero_partita)

            query = query_base + joins
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY p.comune_nome, p.numero_partita"

            if self.execute_query(query, tuple(params)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in search_partite: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in search_partite: {e}")
        return []

    def search_immobili(self, partita_id: Optional[int] = None, comune_nome: Optional[str] = None,
                        localita_id: Optional[int] = None, natura: Optional[str] = None,
                        classificazione: Optional[str] = None) -> List[Dict]:
        """Chiama la funzione SQL cerca_immobili."""
        try:
            query = "SELECT * FROM cerca_immobili(%s, %s, %s, %s, %s)"
            params = (partita_id, comune_nome, localita_id, natura, classificazione)
            if self.execute_query(query, params):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in search_immobili: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in search_immobili: {e}")
        return []

    def search_variazioni(self, tipo: Optional[str] = None, data_inizio: Optional[date] = None,
                          data_fine: Optional[date] = None, partita_origine_id: Optional[int] = None,
                          partita_destinazione_id: Optional[int] = None, comune: Optional[str] = None) -> List[Dict]:
        """Chiama la funzione SQL cerca_variazioni."""
        try:
            query = "SELECT * FROM cerca_variazioni(%s, %s, %s, %s, %s, %s)"
            params = (tipo, data_inizio, data_fine, partita_origine_id, partita_destinazione_id, comune)
            if self.execute_query(query, params):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in search_variazioni: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in search_variazioni: {e}")
        return []

    def search_consultazioni(self, data_inizio: Optional[date] = None, data_fine: Optional[date] = None,
                             richiedente: Optional[str] = None, funzionario: Optional[str] = None) -> List[Dict]:
        """Chiama la funzione SQL cerca_consultazioni."""
        try:
            query = "SELECT * FROM cerca_consultazioni(%s, %s, %s, %s)"
            params = (data_inizio, data_fine, richiedente, funzionario)
            if self.execute_query(query, params):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in search_consultazioni: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python in search_consultazioni: {e}")
        return []

    def update_immobile(self, immobile_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_immobile."""
        params = {
            'p_id': immobile_id,
            'p_natura': kwargs.get('natura'),
            'p_numero_piani': kwargs.get('numero_piani'),
            'p_numero_vani': kwargs.get('numero_vani'),
            'p_consistenza': kwargs.get('consistenza'),
            'p_classificazione': kwargs.get('classificazione'),
            'p_localita_id': kwargs.get('localita_id')
        }
        # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL aggiorna_immobile(%(p_id)s, %(p_natura)s, %(p_numero_piani)s, %(p_numero_vani)s, %(p_consistenza)s, %(p_classificazione)s, %(p_localita_id)s)"
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Immobile ID {immobile_id} aggiornato.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB aggiornamento immobile ID {immobile_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python aggiornamento immobile ID {immobile_id}: {e}")
            self.rollback()
            return False

    def delete_immobile(self, immobile_id: int) -> bool:
        """Chiama la procedura SQL elimina_immobile."""
        # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL elimina_immobile(%s)"
        try:
            if self.execute_query(call_proc, (immobile_id,)):
                self.commit()
                logger.info(f"Immobile ID {immobile_id} eliminato.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB eliminazione immobile ID {immobile_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python eliminazione immobile ID {immobile_id}: {e}")
            self.rollback()
            return False

    def update_variazione(self, variazione_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_variazione."""
        params = {
            'p_variazione_id': variazione_id,
            'p_tipo': kwargs.get('tipo'),
            'p_data_variazione': kwargs.get('data_variazione'),
            'p_numero_riferimento': kwargs.get('numero_riferimento'),
            'p_nominativo_riferimento': kwargs.get('nominativo_riferimento')
        }
         # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL aggiorna_variazione(%(p_variazione_id)s, %(p_tipo)s, %(p_data_variazione)s, %(p_numero_riferimento)s, %(p_nominativo_riferimento)s)"
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Variazione ID {variazione_id} aggiornata.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB aggiornamento variazione ID {variazione_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python aggiornamento variazione ID {variazione_id}: {e}")
            self.rollback()
            return False

    def delete_variazione(self, variazione_id: int, force: bool = False, restore_partita: bool = False) -> bool:
        """Chiama la procedura SQL elimina_variazione."""
         # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL elimina_variazione(%s, %s, %s)"
        try:
            if self.execute_query(call_proc, (variazione_id, force, restore_partita)):
                self.commit()
                logger.info(f"Variazione ID {variazione_id} eliminata.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB eliminazione variazione ID {variazione_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python eliminazione variazione ID {variazione_id}: {e}")
            self.rollback()
            return False

    def insert_contratto(self, variazione_id: int, tipo: str, data_contratto: date,
                         notaio: Optional[str] = None, repertorio: Optional[str] = None,
                         note: Optional[str] = None) -> bool:
        """Chiama la procedura SQL inserisci_contratto."""
         # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL inserisci_contratto(%s, %s, %s, %s, %s, %s)"
        params = (variazione_id, tipo, data_contratto, notaio, repertorio, note)
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Contratto inserito per variazione ID {variazione_id}.")
                return True
            return False
        except psycopg2.Error as db_err:
             # Gestisce errore specifico se il contratto esiste già
            if db_err.pgcode == psycopg2.errors.RaiseException.sqlstate: # Codice per RAISE EXCEPTION
                 if 'Esiste già un contratto' in str(db_err):
                      logger.warning(f"Contratto per variazione ID {variazione_id} esiste già.")
                 else:
                      logger.error(f"Errore DB inserimento contratto var ID {variazione_id}: {db_err}")
            else:
                 logger.error(f"Errore DB inserimento contratto var ID {variazione_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python inserimento contratto var ID {variazione_id}: {e}")
            self.rollback()
            return False

    def update_contratto(self, contratto_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_contratto."""
        params = {
            'p_id': contratto_id,
            'p_tipo': kwargs.get('tipo'),
            'p_data_contratto': kwargs.get('data_contratto'),
            'p_notaio': kwargs.get('notaio'),
            'p_repertorio': kwargs.get('repertorio'),
            'p_note': kwargs.get('note')
        }
        # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL aggiorna_contratto(%(p_id)s, %(p_tipo)s, %(p_data_contratto)s, %(p_notaio)s, %(p_repertorio)s, %(p_note)s)"
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Contratto ID {contratto_id} aggiornato.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB aggiornamento contratto ID {contratto_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python aggiornamento contratto ID {contratto_id}: {e}")
            self.rollback()
            return False

    def delete_contratto(self, contratto_id: int) -> bool:
        """Chiama la procedura SQL elimina_contratto."""
        # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL elimina_contratto(%s)"
        try:
            if self.execute_query(call_proc, (contratto_id,)):
                self.commit()
                logger.info(f"Contratto ID {contratto_id} eliminato.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB eliminazione contratto ID {contratto_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python eliminazione contratto ID {contratto_id}: {e}")
            self.rollback()
            return False

    def update_consultazione(self, consultazione_id: int, **kwargs) -> bool:
        """Chiama la procedura SQL aggiorna_consultazione."""
        params = {
            'p_id': consultazione_id,
            'p_data': kwargs.get('data'),
            'p_richiedente': kwargs.get('richiedente'),
            'p_documento_identita': kwargs.get('documento_identita'),
            'p_motivazione': kwargs.get('motivazione'),
            'p_materiale_consultato': kwargs.get('materiale_consultato'),
            'p_funzionario_autorizzante': kwargs.get('funzionario_autorizzante')
        }
        # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL aggiorna_consultazione(%(p_id)s, %(p_data)s, %(p_richiedente)s, %(p_documento_identita)s, %(p_motivazione)s, %(p_materiale_consultato)s, %(p_funzionario_autorizzante)s)"
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Consultazione ID {consultazione_id} aggiornata.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB aggiornamento consultazione ID {consultazione_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python aggiornamento consultazione ID {consultazione_id}: {e}")
            self.rollback()
            return False

    def delete_consultazione(self, consultazione_id: int) -> bool:
        """Chiama la procedura SQL elimina_consultazione."""
        # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL elimina_consultazione(%s)"
        try:
            if self.execute_query(call_proc, (consultazione_id,)):
                self.commit()
                logger.info(f"Consultazione ID {consultazione_id} eliminata.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB eliminazione consultazione ID {consultazione_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python eliminazione consultazione ID {consultazione_id}: {e}")
            self.rollback()
            return False

    # --- Metodi per Workflow Complessi (chiamano procedure SQL da script 13) ---

    def registra_nuova_proprieta(self, comune_nome: str, numero_partita: int, data_impianto: date,
                                 possessori: List[Dict], immobili: List[Dict]) -> bool:
        """Chiama la procedura SQL registra_nuova_proprieta."""
        try:
            # Serializza liste di dizionari in stringhe JSON per PostgreSQL
            possessori_json = json.dumps(possessori)
            immobili_json = json.dumps(immobili)
            # La procedura è definita in 13_workflow_integrati.sql
            call_proc = "CALL registra_nuova_proprieta(%s, %s, %s, %s::json, %s::json)"
            params = (comune_nome, numero_partita, data_impianto, possessori_json, immobili_json)
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Registrata nuova proprietà: Comune '{comune_nome}', Partita N.{numero_partita}")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB registrazione nuova proprietà (Partita {numero_partita}): {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python registrazione nuova proprietà (Partita {numero_partita}): {e}")
            self.rollback()
            return False

    def registra_passaggio_proprieta(self, partita_origine_id: int, comune_nome: str, numero_partita: int,
                                     tipo_variazione: str, data_variazione: date, tipo_contratto: str,
                                     data_contratto: date, **kwargs) -> bool:
        """Chiama la procedura SQL registra_passaggio_proprieta."""
        try:
            nuovi_poss_list = kwargs.get('nuovi_possessori')
            imm_trasf_list = kwargs.get('immobili_da_trasferire')
            # Converte la lista di possessori in JSON, gestendo il caso None
            nuovi_poss_json = json.dumps(nuovi_poss_list) if nuovi_poss_list is not None else None
            # La lista di ID immobili può essere passata direttamente come array PostgreSQL
            imm_trasf_array = imm_trasf_list if imm_trasf_list is not None else None

            # La procedura è definita in 13_workflow_integrati.sql
            call_proc = "CALL registra_passaggio_proprieta(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::json, %s, %s)"
            params = (
                partita_origine_id, comune_nome, numero_partita, tipo_variazione, data_variazione,
                tipo_contratto, data_contratto, kwargs.get('notaio'), kwargs.get('repertorio'),
                nuovi_poss_json, imm_trasf_array, kwargs.get('note')
            )
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Registrato passaggio proprietà: Origine ID {partita_origine_id} -> Nuova Partita N.{numero_partita} ({comune_nome})")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB registrazione passaggio proprietà (Origine ID {partita_origine_id}): {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python registrazione passaggio proprietà (Origine ID {partita_origine_id}): {e}")
            self.rollback()
            return False

    def registra_consultazione(self, data: date, richiedente: str, documento_identita: Optional[str],
                             motivazione: Optional[str], materiale_consultato: Optional[str],
                             funzionario_autorizzante: Optional[str]) -> bool:
        """Chiama la procedura SQL registra_consultazione."""
        try:
            # La procedura è definita in 03_funzioni-procedure.sql
            call_proc = "CALL registra_consultazione(%s, %s, %s, %s, %s, %s)"
            params = (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante)
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Registrata consultazione: Richiedente '{richiedente}', Data {data}")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB registrazione consultazione: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python registrazione consultazione: {e}")
            self.rollback()
            return False

    def duplicate_partita(self, partita_id: int, nuovo_numero_partita: int,
                          mantenere_possessori: bool = True, mantenere_immobili: bool = False) -> bool:
        """Chiama la procedura SQL duplica_partita."""
        # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL duplica_partita(%s, %s, %s, %s)"
        params = (partita_id, nuovo_numero_partita, mantenere_possessori, mantenere_immobili)
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Partita ID {partita_id} duplicata in nuova partita N.{nuovo_numero_partita}.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB duplicazione partita ID {partita_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python duplicazione partita ID {partita_id}: {e}")
            self.rollback()
            return False

    def transfer_immobile(self, immobile_id: int, nuova_partita_id: int, registra_variazione: bool = False) -> bool:
        """Chiama la procedura SQL trasferisci_immobile."""
        # La procedura è definita in 12_procedure_crud.sql
        call_proc = "CALL trasferisci_immobile(%s, %s, %s)"
        params = (immobile_id, nuova_partita_id, registra_variazione)
        try:
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Immobile ID {immobile_id} trasferito a partita ID {nuova_partita_id}.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB trasferimento immobile ID {immobile_id}: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python trasferimento immobile ID {immobile_id}: {e}")
            self.rollback()
            return False

    # --- Metodi di Reportistica (chiamano funzioni SQL da script 14) ---

    def genera_certificato_proprieta(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL genera_certificato_proprieta."""
        try:
            # La funzione è definita in 14_report_functions.sql
            query = "SELECT genera_certificato_proprieta(%s) AS certificato"
            if self.execute_query(query, (partita_id,)):
                result = self.fetchone()
                return result.get('certificato') if result else None
            return None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB generazione certificato proprietà (ID: {partita_id}): {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python generazione certificato proprietà (ID: {partita_id}): {e}")
            return None

    def genera_report_genealogico(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL genera_report_genealogico."""
        try:
            # La funzione è definita in 14_report_functions.sql
            query = "SELECT genera_report_genealogico(%s) AS report"
            if self.execute_query(query, (partita_id,)):
                result = self.fetchone()
                return result.get('report') if result else None
            return None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB generazione report genealogico (ID: {partita_id}): {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python generazione report genealogico (ID: {partita_id}): {e}")
            return None

    def genera_report_possessore(self, possessore_id: int) -> Optional[str]:
        """Chiama la funzione SQL genera_report_possessore."""
        try:
             # La funzione è definita in 14_report_functions.sql
            query = "SELECT genera_report_possessore(%s) AS report"
            if self.execute_query(query, (possessore_id,)):
                result = self.fetchone()
                return result.get('report') if result else None
            return None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB generazione report possessore (ID: {possessore_id}): {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python generazione report possessore (ID: {possessore_id}): {e}")
            return None

    def genera_report_consultazioni(self, data_inizio: Optional[date] = None,
                                   data_fine: Optional[date] = None,
                                   richiedente: Optional[str] = None) -> Optional[str]:
        """Chiama la funzione SQL genera_report_consultazioni."""
        try:
            # La funzione è definita in 14_report_functions.sql
            query = "SELECT genera_report_consultazioni(%s, %s, %s) AS report"
            params = (data_inizio, data_fine, richiedente)
            if self.execute_query(query, params):
                result = self.fetchone()
                return result.get('report') if result else None
            return None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB generazione report consultazioni: {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python generazione report consultazioni: {e}")
            return None

    # --- Metodi Viste Materializzate (da script 08) ---

    def get_statistiche_comune(self) -> List[Dict]:
        """Recupera dati dalla vista materializzata mv_statistiche_comune."""
        try:
            query = "SELECT * FROM mv_statistiche_comune ORDER BY comune"
            if self.execute_query(query):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_statistiche_comune: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_statistiche_comune: {e}")
        return []

    def get_immobili_per_tipologia(self, comune_nome: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Recupera dati dalla vista materializzata mv_immobili_per_tipologia."""
        try:
            params = []
            query = "SELECT * FROM mv_immobili_per_tipologia"
            if comune_nome:
                query += " WHERE comune_nome ILIKE %s"
                params.append(f"%{comune_nome}%")
            query += " ORDER BY comune_nome, classificazione LIMIT %s"
            params.append(limit)
            if self.execute_query(query, tuple(params)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_immobili_per_tipologia: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_immobili_per_tipologia: {e}")
        return []

    def get_partite_complete_view(self, comune_nome: Optional[str] = None, stato: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Recupera dati dalla vista materializzata mv_partite_complete."""
        try:
            conditions = []; params = []
            query = "SELECT * FROM mv_partite_complete"
            if comune_nome:
                conditions.append("comune_nome ILIKE %s"); params.append(f"%{comune_nome}%")
            if stato and stato.lower() in ['attiva', 'inattiva']:
                conditions.append("stato = %s"); params.append(stato.lower())
            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY comune_nome, numero_partita LIMIT %s"; params.append(limit)
            if self.execute_query(query, tuple(params)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_partite_complete_view: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_partite_complete_view: {e}")
        return []

    def get_cronologia_variazioni(self, comune_origine: Optional[str] = None, tipo_variazione: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Recupera dati dalla vista materializzata mv_cronologia_variazioni."""
        try:
            conditions = []; params = []
            query = "SELECT * FROM mv_cronologia_variazioni"
            if comune_origine:
                conditions.append("comune_origine ILIKE %s"); params.append(f"%{comune_origine}%")
            if tipo_variazione:
                conditions.append("tipo_variazione = %s"); params.append(tipo_variazione)
            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY data_variazione DESC LIMIT %s"; params.append(limit)
            if self.execute_query(query, tuple(params)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_cronologia_variazioni: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_cronologia_variazioni: {e}")
        return []

    # --- Metodi Funzioni Avanzate di Report (da script 08 e 12) ---

    def get_report_annuale_partite(self, comune_nome: str, anno: int) -> List[Dict]:
        """Chiama la funzione SQL report_annuale_partite."""
        try:
            query = "SELECT * FROM report_annuale_partite(%s, %s)"
            if self.execute_query(query, (comune_nome, anno)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_report_annuale_partite: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_report_annuale_partite: {e}")
        return []

    def get_report_proprieta_possessore(self, possessore_id: int, data_inizio: date, data_fine: date) -> List[Dict]:
        """Chiama la funzione SQL report_proprieta_possessore."""
        try:
            query = "SELECT * FROM report_proprieta_possessore(%s, %s, %s)"
            if self.execute_query(query, (possessore_id, data_inizio, data_fine)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_report_proprieta_possessore: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_report_proprieta_possessore: {e}")
        return []

    def get_report_comune(self, comune_nome: str) -> Optional[Dict]:
        """Chiama la funzione SQL genera_report_comune."""
        try:
            query = "SELECT * FROM genera_report_comune(%s)" # Definita in script 12
            if self.execute_query(query, (comune_nome,)):
                return self.fetchone()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_report_comune: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_report_comune: {e}")
        return None

    def export_partita_json(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL esporta_partita_json e formatta l'output."""
        try:
            query = "SELECT esporta_partita_json(%s) AS partita_json" # Definita in script 12
            if self.execute_query(query, (partita_id,)):
                result = self.fetchone()
                if result and result.get('partita_json'):
                     try:
                         # Ritorna la stringa JSON formattata
                         return json.dumps(result['partita_json'], indent=4, ensure_ascii=False)
                     except (TypeError, ValueError) as json_err:
                         logger.error(f"Errore formattazione JSON per partita {partita_id}: {json_err}")
                         # Ritorna la stringa grezza se la formattazione fallisce
                         return str(result['partita_json'])
            logger.warning(f"Nessun JSON ritornato per partita ID {partita_id}.")
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB export_partita_json (ID: {partita_id}): {db_err}")
        except Exception as e:
            logger.error(f"Errore Python export_partita_json (ID: {partita_id}): {e}")
        return None

    def export_possessore_json(self, possessore_id: int) -> Optional[str]:
        """Chiama la funzione SQL esporta_possessore_json e formatta l'output."""
        try:
            query = "SELECT esporta_possessore_json(%s) AS possessore_json" # Definita in script 12
            if self.execute_query(query, (possessore_id,)):
                result = self.fetchone()
                if result and result.get('possessore_json'):
                     try:
                         # Ritorna la stringa JSON formattata
                         return json.dumps(result['possessore_json'], indent=4, ensure_ascii=False)
                     except (TypeError, ValueError) as json_err:
                         logger.error(f"Errore formattazione JSON per possessore {possessore_id}: {json_err}")
                         # Ritorna la stringa grezza se la formattazione fallisce
                         return str(result['possessore_json'])
            logger.warning(f"Nessun JSON ritornato per possessore ID {possessore_id}.")
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB export_possessore_json (ID: {possessore_id}): {db_err}")
        except Exception as e:
            logger.error(f"Errore Python export_possessore_json (ID: {possessore_id}): {e}")
        return None

    # --- Metodi Manutenzione e Ottimizzazione (da script 10 e 13) ---

    def verifica_integrita_database(self) -> Tuple[bool, str]:
        """Chiama la procedura SQL verifica_integrita_database e cattura i messaggi."""
        messages = []
        def notice_handler(notice):
            # Estrae il messaggio utile dal notice
            msg = str(notice).strip()
            if msg.startswith("NOTICE:"): msg = msg[len("NOTICE:"):].strip()
            messages.append(msg)

        original_notice_handler = None
        problemi_trovati = False
        output_msg = ""

        if not self.conn or self.conn.closed:
            return True, "Errore: Connessione al database non attiva."

        try:
            # Aggiunge il gestore di NOTICE temporaneamente
            if hasattr(self.conn, 'notices'):
                original_notice_handler = self.conn.notices.copy() # Salva lo stato attuale
                self.conn.notices.append(notice_handler)
            else: # Fallback se conn.notices non è una lista (improbabile ma sicuro)
                self.conn.add_notice_handler(notice_handler)


            # Chiama la procedura (definita in script 13)
            # La procedura restituisce un parametro OUT p_problemi_trovati,
            # ma chiamandola con CALL non possiamo recuperarlo direttamente.
            # Ci affidiamo ai messaggi RAISE NOTICE/WARNING generati dalla procedura.
            if self.execute_query("CALL verifica_integrita_database(NULL)"): # Passa NULL per l'OUT param
                # Commit potrebbe non essere necessario per una procedura di sola lettura,
                # ma lo facciamo per coerenza se la procedura dovesse cambiare.
                self.commit()
            else:
                problemi_trovati = True
                messages.append("Errore durante l'esecuzione della procedura verifica_integrita_database.")

            # Analizza i messaggi catturati
            for msg in messages:
                if "Problemi di integrità rilevati" in msg or "Problema:" in msg or "WARNING:" in msg:
                    problemi_trovati = True
                output_msg += msg + "\n"

            if not problemi_trovati and not output_msg:
                output_msg = "Nessun problema di integrità rilevato."

        except psycopg2.Error as db_err:
            logger.error(f"Errore DB verifica integrità: {db_err}")
            output_msg = f"Errore DB durante la verifica: {db_err}"
            problemi_trovati = True
        except Exception as e:
            logger.error(f"Errore Python verifica integrità: {e}")
            output_msg = f"Errore Python durante la verifica: {e}"
            problemi_trovati = True
        finally:
            # Ripristina il gestore di NOTICE originale
            if hasattr(self.conn, 'notices') and original_notice_handler is not None:
                 self.conn.notices = original_notice_handler
            elif not hasattr(self.conn, 'notices'):
                 # Se add_notice_handler è stato usato, non c'è un metodo standard per rimuoverlo singolo
                 # In questo caso, potremmo doverci affidare alla chiusura/riapertura della connessione
                 # o accettare che rimanga per la sessione. Non ideale.
                 pass


        return problemi_trovati, output_msg.strip()

    def refresh_materialized_views(self) -> bool:
        """Aggiorna tutte le viste materializzate definite nel database."""
        logger.info("Avvio aggiornamento viste materializzate...")
        try:
            # Chiama la procedura SQL definita in 08_advanced-reporting.sql
            if self.execute_query("CALL aggiorna_tutte_statistiche()"):
                self.commit() # Commit dopo la CALL
                logger.info("Aggiornamento viste materializzate completato.")
                return True
            else:
                logger.error("Fallita chiamata a 'aggiorna_tutte_statistiche'.")
                return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB durante aggiornamento viste: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python durante aggiornamento viste: {e}")
            self.rollback()
            return False

    def run_database_maintenance(self) -> bool:
        """Esegue ANALYZE e aggiorna le viste materializzate."""
        logger.info("Avvio manutenzione database (ANALYZE, REFRESH MV)...")
        # NOTA: VACUUM non può essere chiamato da qui facilmente.
        try:
            # Chiama la procedura definita in 10_performance-optimization.sql
            # Questa procedura esegue ANALYZE e chiama aggiorna_tutte_statistiche()
            if self.execute_query("CALL manutenzione_database()"):
                # La procedura SQL dovrebbe gestire il proprio commit/transazione se necessario,
                # ma un commit qui assicura che la CALL stessa sia confermata.
                self.commit()
                logger.info("Manutenzione (ANALYZE, REFRESH MV) completata.")
                return True
            else:
                logger.error("Fallita chiamata a 'manutenzione_database'.")
                return False
        except psycopg2.Error as db_err:
            # Gestione specifica se VACUUM fosse stato tentato e fallito (ma è stato rimosso)
            if db_err.pgcode == psycopg2.errors.ActiveSqlTransaction.sqlstate:
                 logger.error(f"Errore DB manutenzione: {db_err} (Potrebbe essere un problema di transazione, es. VACUUM)")
            else:
                 logger.error(f"Errore DB manutenzione: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python manutenzione: {e}")
            self.rollback()
            return False

    def analyze_slow_queries(self, min_duration_ms: int = 1000) -> List[Dict]:
        """Chiama la funzione SQL analizza_query_lente (richiede pg_stat_statements)."""
        try:
            query = "SELECT * FROM analizza_query_lente(%s)" # Funzione non definita negli script forniti?
            if self.execute_query(query, (min_duration_ms,)):
                return self.fetchall()
            return []
        except psycopg2.errors.UndefinedFunction:
             logger.warning("Funzione 'analizza_query_lente' non trovata nel database.")
             return []
        except psycopg2.errors.UndefinedTable:
             # Questo errore si verifica se pg_stat_statements non è installato/abilitato
             logger.warning("Estensione 'pg_stat_statements' non abilitata o non installata.")
             return []
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in analyze_slow_queries: {db_err}")
            return []
        except Exception as e:
            logger.error(f"Errore Python in analyze_slow_queries: {e}")
            return []

    def check_index_fragmentation(self):
        """Chiama la procedura SQL controlla_frammentazione_indici."""
        logger.info("Avvio controllo frammentazione indici (risultati nei log DB)...")
        try:
            # Funzione non definita negli script forniti?
            if self.execute_query("CALL controlla_frammentazione_indici()"):
                self.commit()
                logger.info("Controllo frammentazione avviato. Verificare i log del database.")
                return True
            return False
        except psycopg2.errors.UndefinedFunction:
             logger.warning("Procedura 'controlla_frammentazione_indici' non trovata nel database.")
             return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB check_index_fragmentation: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python check_index_fragmentation: {e}")
            self.rollback()
            return False

    def get_optimization_suggestions(self) -> Optional[str]:
        """Chiama la funzione SQL suggerimenti_ottimizzazione."""
        try:
            # Funzione non definita negli script forniti?
            query = "SELECT suggerimenti_ottimizzazione() AS suggestions"
            if self.execute_query(query):
                result = self.fetchone()
                return result.get('suggestions') if result else "Nessun suggerimento disponibile."
            return None
        except psycopg2.errors.UndefinedFunction:
             logger.warning("Funzione 'suggerimenti_ottimizzazione' non trovata nel database.")
             return "Funzione suggerimenti non trovata."
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_optimization_suggestions: {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python get_optimization_suggestions: {e}")
            return None

    # --- Metodi Sistema Utenti e Audit (da script 06, 07, 15) ---

    def set_session_app_user(self, user_id: Optional[int], client_ip: Optional[str] = None) -> bool:
        """Imposta variabili di sessione PostgreSQL per l'audit."""
        if not self.conn or self.conn.closed:
            logger.warning("Tentativo di impostare variabili di sessione senza connessione.")
            return False
        try:
            # Usa NULLIF per gestire il caso in cui user_id sia None
            user_id_str = str(user_id) if user_id is not None else None
            ip_str = client_ip if client_ip is not None else None

            # Usa SELECT set_config(...) per evitare problemi con transazioni esistenti
            # set_config(setting_name, new_value, is_local)
            # is_local=FALSE imposta per la sessione
            if self.execute_query("SELECT set_config('app.user_id', %s, FALSE);", (user_id_str,)) and \
               self.execute_query("SELECT set_config('app.ip_address', %s, FALSE);", (ip_str,)):
                # Non impostiamo session_id qui, viene gestito da registra_accesso
                logger.debug(f"Variabili di sessione impostate: app.user_id='{user_id_str}', app.ip_address='{ip_str}'")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB durante impostazione variabili di sessione: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python durante impostazione variabili di sessione: {e}")
            return False

    def clear_session_app_user(self):
        """Resetta le variabili di sessione PostgreSQL per l'audit."""
        logger.debug("Reset variabili di sessione app.")
        self.set_session_app_user(user_id=None, client_ip=None)

    def get_audit_log(self, tabella: Optional[str]=None, operazione: Optional[str]=None,
                      record_id: Optional[int]=None, data_inizio: Optional[date]=None,
                      data_fine: Optional[date]=None, utente_db: Optional[str]=None,
                      app_user_id: Optional[int]=None, session_id: Optional[str]=None,
                      limit: int=100) -> List[Dict]:
        """Recupera log di audit con filtri opzionali dalla vista v_audit_dettagliato."""
        try:
            conditions = []; params = []
            query = "SELECT * FROM v_audit_dettagliato" # Usa la vista definita in 15_integration_audit_users.sql

            if tabella: conditions.append("tabella = %s"); params.append(tabella)
            if operazione and operazione.upper() in ['I', 'U', 'D']:
                conditions.append("operazione = %s"); params.append(operazione.upper())
            if record_id is not None: conditions.append("record_id = %s"); params.append(record_id)
            if data_inizio: conditions.append("timestamp >= %s"); params.append(data_inizio)
            if data_fine:
                 # Aggiunge 1 giorno per includere tutta la data finale
                 data_fine_end_day = datetime.combine(data_fine, datetime.max.time())
                 conditions.append("timestamp <= %s"); params.append(data_fine_end_day)
            if utente_db: conditions.append("db_user = %s"); params.append(utente_db) # Usa alias db_user dalla vista
            if app_user_id is not None: conditions.append("al.app_user_id = %s"); params.append(app_user_id) # Da audit_log, non dalla vista
            if session_id: conditions.append("session_id = %s"); params.append(session_id)

            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY timestamp DESC LIMIT %s"; params.append(limit)

            if self.execute_query(query, tuple(params)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_audit_log: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_audit_log: {e}")
        return []

    def get_record_history(self, tabella: str, record_id: int) -> List[Dict]:
        """Chiama la funzione SQL get_record_history."""
        try:
            query = "SELECT * FROM get_record_history(%s, %s)" # Definita in 06_audit-system.sql
            if self.execute_query(query, (tabella, record_id)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_record_history: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_record_history: {e}")
        return []

    def genera_report_audit(self, tabella=None, data_inizio=None, data_fine=None,
                          operazione=None, utente_db=None, app_user_id=None) -> str:
        """Genera un report testuale basato sui log di audit filtrati."""
        logs = self.get_audit_log(tabella, operazione, None, data_inizio, data_fine,
                                 utente_db, app_user_id, None, 1000) # Limite alto per report
        if not logs:
            return "Nessun log di audit trovato per i criteri specificati."

        report_lines = ["--- Report Audit ---"]
        report_lines.append(f"Periodo: {data_inizio or 'Inizio'} - {data_fine or 'Fine'}")
        if tabella: report_lines.append(f"Tabella: {tabella}")
        if operazione: report_lines.append(f"Operazione: {operazione}")
        if utente_db: report_lines.append(f"Utente DB: {utente_db}")
        if app_user_id: report_lines.append(f"Utente App ID: {app_user_id}")
        report_lines.append(f"Numero log: {len(logs)}")
        report_lines.append("-" * 20)

        op_map = {"I": "Inserimento", "U": "Aggiornamento", "D": "Cancellazione"}

        for log in logs:
            ts = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if log.get('timestamp') else 'N/D'
            op = op_map.get(log.get('operazione'), '?')
            tbl = log.get('tabella', '?')
            rec_id = log.get('record_id', '?')
            db_u = log.get('db_user', '?') # Dalla vista v_audit_dettagliato
            app_u = log.get('app_username', 'N/A') # Dalla vista
            app_u_id = f" (ID: {log['app_user_id']})" if log.get('app_user_id') is not None else ""
            sess = log.get('session_id', '-')[:8] # Primi 8 caratteri sessione
            ip = log.get('ip_address', '-')

            report_lines.append(f"{ts} | {op:<13} | Tab: {tbl:<15} | RecID: {rec_id:<5} | DB User: {db_u:<10} | App User: {app_u}{app_u_id} | Sess: {sess} | IP: {ip}")
            # Aggiungere dettagli campi modificati per 'U'?
            # if log.get('operazione') == 'U':
            #     try:
            #         d_prima = log.get('dati_prima', {}) or {}
            #         d_dopo = log.get('dati_dopo', {}) or {}
            #         # ... logica per confrontare e stampare differenze ...
            #     except Exception: pass # Ignora errori nel parsing dettagli

        return "\n".join(report_lines)

    def create_user(self, username: str, password_hash: str, nome_completo: str, email: str, ruolo: str) -> bool:
        """Chiama la procedura SQL crea_utente."""
        try:
            # La procedura è definita in 07_user-management.sql
            call_proc = "CALL crea_utente(%s, %s, %s, %s, %s)"
            params = (username, password_hash, nome_completo, email, ruolo)
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Utente '{username}' creato con successo.")
                return True
            return False # Errore connessione
        except psycopg2.errors.UniqueViolation: # Errore specifico per duplicato
            logger.error(f"Errore creazione utente: Username '{username}' o Email '{email}' già esistente.")
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB creazione utente '{username}': {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python creazione utente '{username}': {e}")
            self.rollback()
            return False

    def get_user_credentials(self, username: str) -> Optional[Dict]:
        """Recupera ID e hash password per un utente attivo."""
        try:
            query = "SELECT id, password_hash FROM utente WHERE username = %s AND attivo = TRUE"
            if self.execute_query(query, (username,)):
                return self.fetchone()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_user_credentials per '{username}': {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_user_credentials per '{username}': {e}")
        return None

    def register_access(self, utente_id: int, azione: str, indirizzo_ip: Optional[str] = None,
                        user_agent: Optional[str] = None, esito: bool = True,
                        application_name: str = 'CatastoApp') -> Optional[str]:
        """
        Chiama la procedura SQL registra_accesso, generando un session_id.
        Ritorna il session_id generato in caso di successo.
        """
        session_id = None
        try:
            # Genera un nuovo UUID per la sessione
            session_id = str(uuid.uuid4())
            # La procedura aggiornata è in 15_integration_audit_users.sql
            call_proc = "CALL registra_accesso(%s, %s, %s, %s, %s, %s, %s)"
            params = (utente_id, azione, indirizzo_ip, user_agent, esito, session_id, application_name)
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Registrato accesso: Utente ID {utente_id}, Azione {azione}, Esito {esito}, Sessione {session_id[:8]}...")
                return session_id
            else:
                logger.error(f"Fallita chiamata a registra_accesso per utente ID {utente_id}.")
                return None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB registrazione accesso utente ID {utente_id}: {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python registrazione accesso utente ID {utente_id}: {e}")
            self.rollback()
            return None

    def logout_user(self, user_id: Optional[int], session_id: Optional[str], client_ip: Optional[str] = None) -> bool:
        """Chiama la procedura SQL logout_utente e resetta il contesto di sessione."""
        if user_id is None or session_id is None:
            logger.warning("Tentativo di logout senza user_id o session_id.")
            self.clear_session_app_user() # Resetta comunque il contesto per sicurezza
            return False
        try:
            # La procedura è definita in 15_integration_audit_users.sql
            call_proc = "CALL logout_utente(%s, %s, %s)"
            success = self.execute_query(call_proc, (user_id, session_id, client_ip))
            if success:
                self.commit()
                logger.info(f"Logout registrato per utente ID {user_id}, sessione {session_id[:8]}...")
            # Resetta sempre le variabili di sessione dopo il logout, anche se la CALL fallisce
            self.clear_session_app_user()
            return success
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB logout utente ID {user_id}: {db_err}")
            self.clear_session_app_user()
            return False
        except Exception as e:
            logger.error(f"Errore Python logout utente ID {user_id}: {e}")
            self.rollback()
            self.clear_session_app_user()
            return False

    def check_permission(self, utente_id: int, permesso_nome: str) -> bool:
        """Chiama la funzione SQL ha_permesso."""
        try:
            # La funzione è definita in 07_user-management.sql
            query = "SELECT ha_permesso(%s, %s) AS permesso"
            if self.execute_query(query, (utente_id, permesso_nome)):
                result = self.fetchone()
                return result.get('permesso', False) if result else False
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB verifica permesso '{permesso_nome}' per utente ID {utente_id}: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python verifica permesso '{permesso_nome}' per utente ID {utente_id}: {e}")
        return False

    # --- Metodi Sistema Backup (da script 09) ---

    def register_backup_log(self, nome_file: str, utente: str, tipo: str, esito: bool,
                            percorso_file: str, dimensione_bytes: Optional[int] = None,
                            messaggio: Optional[str] = None) -> Optional[int]:
        """Chiama la funzione SQL registra_backup."""
        try:
            # La funzione è definita in 09_backup-system.sql
            query = "SELECT registra_backup(%s, %s, %s, %s, %s, %s, %s)"
            params = (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)
            if self.execute_query(query, params):
                 result = self.fetchone()
                 self.commit()
                 backup_id = result.get('registra_backup') if result else None
                 if backup_id:
                     logger.info(f"Log backup registrato con ID: {backup_id} per file '{nome_file}'")
                 else:
                     logger.error(f"La funzione registra_backup non ha restituito un ID per '{nome_file}'.")
                 return backup_id
        except psycopg2.Error as db_err:
             logger.error(f"Errore DB registrazione log backup '{nome_file}': {db_err}")
        except Exception as e:
             logger.error(f"Errore Python registrazione log backup '{nome_file}': {e}")
             self.rollback()
        return None

    def get_backup_command_suggestion(self, tipo: str = 'completo') -> Optional[str]:
        """Chiama la funzione SQL get_backup_commands."""
        try:
            query = "SELECT get_backup_commands(%s) AS commands"
            if self.execute_query(query, (tipo,)):
                result = self.fetchone()
                return result.get('commands') if result else None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_backup_command_suggestion (tipo: {tipo}): {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_backup_command_suggestion (tipo: {tipo}): {e}")
        return None

    def get_restore_command_suggestion(self, backup_log_id: int) -> Optional[str]:
        """Chiama la funzione SQL get_restore_commands."""
        try:
            query = "SELECT get_restore_commands(%s) AS command"
            if self.execute_query(query, (backup_log_id,)):
                result = self.fetchone()
                return result.get('command') if result else None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_restore_command_suggestion (ID: {backup_log_id}): {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_restore_command_suggestion (ID: {backup_log_id}): {e}")
        return None

    def cleanup_old_backup_logs(self, giorni_conservazione: int = 30) -> bool:
        """Chiama la procedura SQL pulizia_backup_vecchi."""
        try:
            # La procedura è definita in 09_backup-system.sql
            call_proc = "CALL pulizia_backup_vecchi(%s)"
            if self.execute_query(call_proc, (giorni_conservazione,)):
                self.commit()
                logger.info(f"Eseguita pulizia log backup più vecchi di {giorni_conservazione} giorni.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB pulizia log backup: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python pulizia log backup: {e}")
            self.rollback()
            return False

    def generate_backup_script(self, backup_dir: str) -> Optional[str]:
        """Chiama la funzione SQL genera_script_backup_automatico."""
        try:
            # La funzione è definita in 09_backup-system.sql
            query = "SELECT genera_script_backup_automatico(%s) AS script_content"
            if self.execute_query(query, (backup_dir,)):
                result = self.fetchone()
                return result.get('script_content') if result else None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB generazione script backup: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python generazione script backup: {e}")
        return None

    def get_backup_logs(self, limit: int = 20) -> List[Dict]:
        """Recupera gli ultimi N log di backup dal registro."""
        try:
            query = "SELECT * FROM backup_registro ORDER BY timestamp DESC LIMIT %s"
            if self.execute_query(query, (limit,)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_backup_logs: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_backup_logs: {e}")
        return []

    # --- Metodi Ricerca Avanzata (da script 10) ---

    def ricerca_avanzata_possessori(self, query_text: str) -> List[Dict]:
        """Chiama la funzione SQL ricerca_avanzata_possessori."""
        try:
            query = "SELECT * FROM ricerca_avanzata_possessori(%s)" # Funzione non definita?
            if self.execute_query(query, (query_text,)):
                return self.fetchall()
        except psycopg2.errors.UndefinedFunction:
             logger.warning("Funzione 'ricerca_avanzata_possessori' non trovata nel database.")
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB ricerca_avanzata_possessori: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python ricerca_avanzata_possessori: {e}")
        return []

    def ricerca_avanzata_immobili(self, comune: Optional[str] = None, natura: Optional[str] = None,
                                 localita: Optional[str] = None, classificazione: Optional[str] = None,
                                 possessore: Optional[str] = None) -> List[Dict]:
        """Chiama la funzione SQL ricerca_avanzata_immobili."""
        try:
            query = "SELECT * FROM ricerca_avanzata_immobili(%s, %s, %s, %s, %s)" # Funzione non definita?
            params = (comune, natura, localita, classificazione, possessore)
            if self.execute_query(query, params):
                return self.fetchall()
        except psycopg2.errors.UndefinedFunction:
             logger.warning("Funzione 'ricerca_avanzata_immobili' non trovata nel database.")
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB ricerca_avanzata_immobili: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python ricerca_avanzata_immobili: {e}")
        return []

    # --- Metodi Funzionalità Storiche Avanzate (da script 11) ---

    def get_historical_periods(self) -> List[Dict]:
        """Recupera i periodi storici definiti."""
        try:
            query = "SELECT id, nome, anno_inizio, anno_fine, descrizione FROM periodo_storico ORDER BY anno_inizio"
            if self.execute_query(query):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_historical_periods: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_historical_periods: {e}")
        return []

    def get_historical_name(self, entity_type: str, entity_id: int, year: Optional[int] = None) -> Optional[Dict]:
        """Chiama la funzione SQL get_nome_storico."""
        try:
            if year is None: year = datetime.now().year # Default all'anno corrente se non specificato
            query = "SELECT * FROM get_nome_storico(%s, %s, %s)"
            if self.execute_query(query, (entity_type, entity_id, year)):
                return self.fetchone()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_historical_name ({entity_type} ID {entity_id}): {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_historical_name ({entity_type} ID {entity_id}): {e}")
        return None

    def register_historical_name(self, entity_type: str, entity_id: int, name: str,
                                 period_id: int, year_start: int, year_end: Optional[int] = None,
                                 notes: Optional[str] = None) -> bool:
        """Chiama la procedura SQL registra_nome_storico."""
        try:
            call_proc = "CALL registra_nome_storico(%s, %s, %s, %s, %s, %s, %s)"
            params = (entity_type, entity_id, name, period_id, year_start, year_end, notes)
            if self.execute_query(call_proc, params):
                self.commit()
                logger.info(f"Registrato nome storico '{name}' per {entity_type} ID {entity_id}.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB registrazione nome storico: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python registrazione nome storico: {e}")
            self.rollback()
            return False

    def search_historical_documents(self, title: Optional[str] = None, doc_type: Optional[str] = None,
                                    period_id: Optional[int] = None, year_start: Optional[int] = None,
                                    year_end: Optional[int] = None, partita_id: Optional[int] = None) -> List[Dict]:
        """Chiama la funzione SQL ricerca_documenti_storici."""
        try:
            query = "SELECT * FROM ricerca_documenti_storici(%s, %s, %s, %s, %s, %s)"
            params = (title, doc_type, period_id, year_start, year_end, partita_id)
            if self.execute_query(query, params):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB search_historical_documents: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python search_historical_documents: {e}")
        return []

    def get_property_genealogy(self, partita_id: int) -> List[Dict]:
        """Chiama la funzione SQL albero_genealogico_proprieta."""
        try:
            query = "SELECT * FROM albero_genealogico_proprieta(%s)"
            if self.execute_query(query, (partita_id,)):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_property_genealogy (ID: {partita_id}): {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_property_genealogy (ID: {partita_id}): {e}")
        return []

    def get_cadastral_stats_by_period(self, comune: Optional[str] = None, year_start: int = 1900,
                                       year_end: Optional[int] = None) -> List[Dict]:
        """Chiama la funzione SQL statistiche_catastali_periodo."""
        try:
            if year_end is None: year_end = datetime.now().year
            query = "SELECT * FROM statistiche_catastali_periodo(%s, %s, %s)"
            params = (comune, year_start, year_end)
            if self.execute_query(query, params):
                return self.fetchall()
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB get_cadastral_stats_by_period: {db_err}")
        except Exception as e:
            logger.error(f"Errore Python get_cadastral_stats_by_period: {e}")
        return []

    def link_document_to_partita(self, document_id: int, partita_id: int,
                                 relevance: str = 'correlata', notes: Optional[str] = None) -> bool:
        """Collega un documento storico a una partita."""
        if relevance not in ['primaria', 'secondaria', 'correlata']:
            logger.error(f"Valore rilevanza non valido: '{relevance}'")
            return False
        # La tabella è definita in 11_advanced-cadastral-features.sql
        query = """
            INSERT INTO documento_partita (documento_id, partita_id, rilevanza, note)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (documento_id, partita_id) DO UPDATE SET
                rilevanza = EXCLUDED.rilevanza,
                note = EXCLUDED.note
        """
        try:
            if self.execute_query(query, (document_id, partita_id, relevance, notes)):
                self.commit()
                logger.info(f"Collegamento creato/aggiornato tra Documento ID {document_id} e Partita ID {partita_id}.")
                return True
            return False
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB collegamento documento-partita: {db_err}")
            return False
        except Exception as e:
            logger.error(f"Errore Python collegamento documento-partita: {e}")
            self.rollback()
            return False


# --- Esempio di utilizzo minimale (se eseguito direttamente) ---
if __name__ == "__main__":
    print("Esecuzione test minimale CatastoDBManager...")
    # Sostituisci con le tue credenziali reali se necessario
    db = CatastoDBManager(password="Markus74")
    if db.connect():
        print("Connessione OK.")
        # Esempio: prova a ottenere comuni
        comuni = db.get_comuni("Carcare")
        if comuni:
            print(f"Trovati {len(comuni)} comuni con 'Carcare':")
            # print(comuni) # Stampa la lista completa se vuoi
        else:
            print("Nessun comune trovato con 'Carcare' o errore.")

        # Esempio: prova a verificare un permesso (necessita che l'utente esista)
        # user_id_test = 1 # Assumi che l'utente con ID 1 esista
        # permesso_test = 'visualizza_partite'
        # if db.check_permission(user_id_test, permesso_test):
        #     print(f"Utente {user_id_test} HA il permesso '{permesso_test}'.")
        # else:
        #      print(f"Utente {user_id_test} NON HA il permesso '{permesso_test}' o errore.")

        db.disconnect()
        print("Disconnessione OK.")
    else:
        print("Connessione fallita.")