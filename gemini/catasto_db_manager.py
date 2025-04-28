#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestore Database Catasto Storico
================================
Script per la gestione del database catastale con supporto
per operazioni CRUD, chiamate alle stored procedure, gestione utenti,
audit, backup e funzionalità avanzate.

Autore: Marco Santoro
Data: 25/04/2025 (Versione corretta 1.3 - Gestione Eccezioni Fixata)
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

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("catasto_db.log"),
        logging.StreamHandler(sys.stdout) # Mostra log anche a console
    ]
)
# Imposta il livello DEBUG per vedere le query mogrify
# logger = logging.getLogger("CatastoDB")
# logger.setLevel(logging.DEBUG)
# In alternativa, lascia INFO per output meno verboso
logger = logging.getLogger("CatastoDB")

class CatastoDBManager:
    """Classe per la gestione delle operazioni sul database catastale."""

    def __init__(self, dbname: str = "catasto_storico", user: str = "postgres",
                 password: str = "Markus74", host: str = "localhost", port: int = 5432,
                 schema: str = "catasto"):
        self.conn_params = {
            "dbname": dbname, "user": user, "password": password,
            "host": host, "port": port
        }
        self.schema = schema
        self.conn = None
        self.cur = None
        logger.info(f"Inizializzato gestore per database {dbname} schema {schema}")

    def connect(self) -> bool:
        """Stabilisce una connessione al database."""
        try:
            if self.conn and not self.conn.closed:
                logger.warning("Chiusura connessione DB esistente prima di riconnettere.")
                self.disconnect()

            self.conn = psycopg2.connect(**self.conn_params)
            self.conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
            self.cur = self.conn.cursor(cursor_factory=DictCursor)
            self.cur.execute(f"SET search_path TO {self.schema}")
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
            if self.conn and not self.conn.closed:
                 self.clear_session_app_user() # Resetta contesto DB
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
             try: self.conn.commit(); logger.info("Commit eseguito.")
             except Exception as e: logger.error(f"Errore commit: {e}"); self.rollback()
        else: logger.warning("Tentativo di commit senza connessione attiva.")

    def rollback(self):
        """Annulla le modifiche al database."""
        if self.conn and not self.conn.closed:
             try: self.conn.rollback(); logger.info("Rollback eseguito.")
             except Exception as e: logger.error(f"Errore rollback: {e}")
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
                    if not attempt_reconnect: return False # Già tentato riconnessione
                    logger.warning("Connessione non attiva. Tentativo di riconnessione...")
                    if not self.connect(): return False # Riconnessione fallita
                    attempt_reconnect = False # Riconnetti solo una volta

                # 2. Assicura Cursore Valido
                if self.cur is None or self.cur.closed:
                     self.cur = self.conn.cursor(cursor_factory=DictCursor)
                     self.cur.execute(f"SET search_path TO {self.schema}")

                # 3. Esegui Query
                logger.debug(f"Esecuzione query: {self.cur.mogrify(query, params)}")
                self.cur.execute(query, params)
                return True # Successo se non ci sono eccezioni

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

            # 5. Gestione Altri Errori DB (Log + Rilancio)
            except psycopg2.Error as db_err:
                 logger.error(f"Errore DB specifico rilevato: {db_err.__class__.__name__} - {db_err}")
                 # Logga query e parametri per debug
                 try: logger.error(f"Query: {self.cur.query}") # Query dopo esecuzione
                 except: logger.error(f"Query (originale): {query}")
                 logger.error(f"Parametri: {params}")
                 self.rollback() # Annulla transazione
                 raise db_err # RILANCIA l'eccezione per gestione specifica nel chiamante

            # 6. Gestione Errori Python Generici (Log + Rilancio)
            except Exception as e:
                logger.error(f"Errore Python imprevisto: {e.__class__.__name__} - {e}")
                try: logger.error(f"Query: {self.cur.query}")
                except: logger.error(f"Query (originale): {query}")
                logger.error(f"Parametri: {params}")
                self.rollback()
                raise e # RILANCIA l'eccezione Python


    def fetchall(self) -> List[Dict]:
        """Recupera tutti i risultati dell'ultima query."""
        if self.cur and not self.cur.closed:
             try: return [dict(row) for row in self.cur.fetchall()]
             except psycopg2.ProgrammingError: return [] # Nessun risultato o cursore non valido
             except Exception as e: logger.error(f"Errore fetchall: {e}"); return []
        return []

    def fetchone(self) -> Optional[Dict]:
        """Recupera una riga di risultati dall'ultima query."""
        if self.cur and not self.cur.closed:
             try: row = self.cur.fetchone(); return dict(row) if row else None
             except psycopg2.ProgrammingError: return None # Nessun risultato o cursore non valido
             except Exception as e: logger.error(f"Errore fetchone: {e}"); return None
        return None
    # --- Funzioni Helper per Interfaccia Utente ---
# ... (altre funzioni helper come stampa_intestazione, _confirm_action, ecc.)

    def _esporta_entita_json(db: CatastoDBManager, tipo_entita: str, etichetta_id: str, nome_file_prefix: str):
        """
        Funzione generica per esportare un'entità (partita o possessore) in formato JSON.

        Args:
            db: Istanza di CatastoDBManager.
            tipo_entita: Tipo di entità ('partita' o 'possessore').
            etichetta_id: Etichetta da usare nel prompt per l'ID (es. "ID della Partita").
            nome_file_prefix: Prefisso per il nome del file di output (es. "partita").
        """
        stampa_intestazione(f"ESPORTA {tipo_entita.upper()} IN JSON")
        id_entita_str = input(f"{etichetta_id} da esportare: ").strip()

        if not id_entita_str.isdigit():
            print("ID non valido.")
            return

        entita_id = int(id_entita_str)
        json_data_str = None

        try:
            if tipo_entita == 'partita':
                json_data_str = db.export_partita_json(entita_id)
            elif tipo_entita == 'possessore':
                json_data_str = db.export_possessore_json(entita_id)
            else:
                print(f"Tipo entità '{tipo_entita}' non supportato per l'esportazione.")
                return

            if json_data_str:
                print(f"\n--- DATI JSON {tipo_entita.upper()} ---")
                print(json_data_str)
                print("-" * (len(tipo_entita) + 16)) # Adatta la lunghezza della linea
                filename = f"{nome_file_prefix}_{entita_id}.json"
                if _confirm_action(f"Salvare in '{filename}'"):
                    try:
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(json_data_str)
                        print(f"Dati salvati in {filename}")
                    except Exception as e:
                        print(f"Errore nel salvataggio del file: {e}")
            else:
                print(f"{tipo_entita.capitalize()} non trovato/a o errore durante l'esportazione.")

        except Exception as e:
            # Logga l'errore se necessario, o gestiscilo diversamente
            print(f"Si è verificato un errore durante l'esportazione: {e}")

    # ... (resto delle funzioni come inserisci_possessore, ecc.)

    # ========================================
    # OPERAZIONI CRUD E DI RICERCA PRINCIPALI
    # ========================================
    def get_comuni(self, search_term=None) -> List[Dict]:
        """Recupera comuni con filtro opzionale."""
        try:
            if search_term: query, params = "SELECT nome, provincia, regione FROM comune WHERE nome ILIKE %s ORDER BY nome", (f"%{search_term}%",)
            else: query, params = "SELECT nome, provincia, regione FROM comune ORDER BY nome", None
            if self.execute_query(query, params): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in get_comuni: {db_err}")
        except Exception as e: logger.error(f"Errore Python in get_comuni: {e}")
        return []

    def check_possessore_exists(self, nome_completo: str, comune_nome: str = None) -> Optional[int]:
        """Verifica se un possessore esiste e ritorna il suo ID."""
        try:
            if comune_nome: query, params = "SELECT id FROM possessore WHERE nome_completo = %s AND comune_nome = %s", (nome_completo, comune_nome)
            else: query, params = "SELECT id FROM possessore WHERE nome_completo = %s", (nome_completo,)
            if self.execute_query(query, params): result = self.fetchone(); return result['id'] if result else None
        except psycopg2.Error as db_err: logger.error(f"Errore DB in check_possessore_exists: {db_err}")
        except Exception as e: logger.error(f"Errore Python in check_possessore_exists: {e}")
        return None

    def get_possessori_by_comune(self, comune_nome: str) -> List[Dict]:
        """Recupera possessori per comune (ricerca esatta)."""
        try:
            query = "SELECT * FROM possessore WHERE comune_nome = %s ORDER BY nome_completo"
            if self.execute_query(query, (comune_nome,)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in get_possessori_by_comune: {db_err}")
        except Exception as e: logger.error(f"Errore Python in get_possessori_by_comune: {e}")
        return []

    def get_partite_by_comune(self, comune_nome: str) -> List[Dict]:
        """Recupera partite per comune (ricerca esatta) con dettagli aggregati."""
        try:
            query = """SELECT p.*, string_agg(DISTINCT pos.nome_completo, ', ') as possessori, COUNT(DISTINCT i.id) as num_immobili
                       FROM partita p LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
                       LEFT JOIN possessore pos ON pp.possessore_id = pos.id LEFT JOIN immobile i ON p.id = i.partita_id
                       WHERE p.comune_nome = %s GROUP BY p.id ORDER BY p.numero_partita"""
            if self.execute_query(query, (comune_nome,)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in get_partite_by_comune: {db_err}")
        except Exception as e: logger.error(f"Errore Python in get_partite_by_comune: {e}")
        return []

    def get_partita_details(self, partita_id: int) -> Optional[Dict]:
        """Recupera dettagli completi di una partita."""
        try:
            query_partita = "SELECT * FROM partita WHERE id = %s"
            if not self.execute_query(query_partita, (partita_id,)): return None
            partita = self.fetchone();
            if not partita: return None
            # Possessori
            query_poss = "SELECT pos.*, pp.titolo, pp.quota FROM possessore pos JOIN partita_possessore pp ON pos.id=pp.possessore_id WHERE pp.partita_id=%s"
            partita['possessori'] = self.fetchall() if self.execute_query(query_poss, (partita_id,)) else []
            # Immobili
            query_imm = "SELECT i.*, l.nome as localita_nome, l.tipo as localita_tipo, l.civico FROM immobile i JOIN localita l ON i.localita_id=l.id WHERE i.partita_id=%s"
            partita['immobili'] = self.fetchall() if self.execute_query(query_imm, (partita_id,)) else []
            # Variazioni
            query_var = "SELECT v.*, c.tipo as tipo_contratto, c.data_contratto, c.notaio, c.repertorio, c.note as contratto_note FROM variazione v LEFT JOIN contratto c ON v.id=c.variazione_id WHERE v.partita_origine_id=%s OR v.partita_destinazione_id=%s"
            partita['variazioni'] = self.fetchall() if self.execute_query(query_var, (partita_id, partita_id)) else []
            return partita
        except psycopg2.Error as db_err: logger.error(f"Errore DB in get_partita_details: {db_err}")
        except Exception as e: logger.error(f"Errore Python in get_partita_details: {e}")
        return None

    def search_partite(self, comune_nome: Optional[str] = None, numero_partita: Optional[int] = None,
                      possessore: Optional[str] = None, immobile_natura: Optional[str] = None) -> List[Dict]:
        """Ricerca partite con filtri multipli."""
        try:
            conditions = []; params = []; joins = ""
            query_base = "SELECT DISTINCT p.* FROM partita p"
            if possessore: joins += " LEFT JOIN partita_possessore pp ON p.id = pp.partita_id LEFT JOIN possessore pos ON pp.possessore_id = pos.id"; conditions.append("pos.nome_completo ILIKE %s"); params.append(f"%{possessore}%")
            if immobile_natura:
                if "immobile i" not in joins: joins += " LEFT JOIN immobile i ON p.id = i.partita_id"
                conditions.append("i.natura ILIKE %s"); params.append(f"%{immobile_natura}%")
            if comune_nome: conditions.append("p.comune_nome ILIKE %s"); params.append(f"%{comune_nome}%")
            if numero_partita is not None: conditions.append("p.numero_partita = %s"); params.append(numero_partita)
            query = query_base + joins
            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY p.comune_nome, p.numero_partita"
            if self.execute_query(query, tuple(params)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB in search_partite: {db_err}")
        except Exception as e: logger.error(f"Errore Python in search_partite: {e}")
        return []

    def insert_possessore(self, comune_nome: str, cognome_nome: str, paternita: str,
                        nome_completo: str, attivo: bool = True) -> Optional[int]:
        """Inserisce un nuovo possessore usando la procedura SQL."""
        try:
            if self.execute_query("CALL inserisci_possessore(%s, %s, %s, %s, %s)",
                                  (comune_nome, cognome_nome, paternita, nome_completo, attivo)):
                self.commit()
                # Recupera l'ID dell'ultimo inserito che matcha (per evitare problemi con nomi duplicati)
                if self.execute_query("SELECT id FROM possessore WHERE comune_nome = %s AND nome_completo = %s ORDER BY id DESC LIMIT 1",
                                      (comune_nome, nome_completo)):
                    result = self.fetchone(); return result['id'] if result else None
            return None # Execute_query ha fallito (es. errore connessione)
        except psycopg2.Error as db_err: # Errore DB rilanciato da execute_query
            logger.error(f"Errore DB specifico in insert_possessore: {db_err}")
            # Rollback è già stato fatto da execute_query
            return None
        except Exception as e: # Errore Python generico
            logger.error(f"Errore Python in insert_possessore: {e}")
            self.rollback() # Assicurati rollback per errori Python
            return None

    def insert_localita(self, comune_nome: str, nome: str, tipo: str,
                      civico: Optional[int] = None) -> Optional[int]:
        """Inserisce o recupera una località, gestendo conflitti."""
        query_insert = "INSERT INTO localita (comune_nome, nome, tipo, civico) VALUES (%s, %s, %s, %s) ON CONFLICT (comune_nome, nome, civico) DO NOTHING RETURNING id"
        query_select = "SELECT id FROM localita WHERE comune_nome=%s AND nome=%s AND (civico = %s OR (civico IS NULL AND %s IS NULL))"
        try:
            inserted_id = None
            if self.execute_query(query_insert, (comune_nome, nome, tipo, civico)):
                result = self.fetchone()
                if result: inserted_id = result['id']; self.commit() # Commit solo se inserito
            # Se execute_query ritorna False (errore connessione), esce e ritorna None
            elif self.conn is None or self.conn.closed: return None

            if inserted_id: return inserted_id
            # Se c'è stato conflitto (nessun ID ritornato), seleziona l'esistente
            if self.execute_query(query_select, (comune_nome, nome, civico, civico)):
                existing = self.fetchone()
                return existing['id'] if existing else None
            return None # Errore nella select
        except psycopg2.Error as db_err: logger.error(f"Errore DB in insert_localita: {db_err}"); return None
        except Exception as e: logger.error(f"Errore Python in insert_localita: {e}"); self.rollback(); return None

    # ========================================
    # CHIAMATE A PROCEDURE DI WORKFLOW (script 13)
    # ========================================
    def registra_nuova_proprieta(self, comune_nome: str, numero_partita: int, data_impianto: date, possessori: List[Dict], immobili: List[Dict]) -> bool:
        try:
            possessori_json = json.dumps(possessori); immobili_json = json.dumps(immobili)
            call_proc = "CALL registra_nuova_proprieta(%s, %s, %s, %s, %s)"
            if self.execute_query(call_proc, (comune_nome, numero_partita, data_impianto, possessori_json, immobili_json)):
                self.commit(); logger.info(f"Reg. nuova proprietà: {comune_nome}, partita {numero_partita}"); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB reg. proprietà: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python reg. proprietà: {e}"); self.rollback(); return False

    def registra_passaggio_proprieta(self, partita_origine_id: int, comune_nome: str, numero_partita: int, tipo_variazione: str, data_variazione: date, tipo_contratto: str, data_contratto: date, **kwargs) -> bool:
        try:
            nuovi_poss_list = kwargs.get('nuovi_possessori'); imm_trasf_list = kwargs.get('immobili_da_trasferire')
            nuovi_poss_json = json.dumps(nuovi_poss_list) if nuovi_poss_list else None
            call_proc = "CALL registra_passaggio_proprieta(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            params = (partita_origine_id, comune_nome, numero_partita, tipo_variazione, data_variazione, tipo_contratto, data_contratto, kwargs.get('notaio'), kwargs.get('repertorio'), nuovi_poss_json, imm_trasf_list, kwargs.get('note'))
            if self.execute_query(call_proc, params):
                self.commit(); logger.info(f"Reg. passaggio prop.: origine {partita_origine_id}, nuova {numero_partita}"); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB passaggio prop.: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python passaggio prop.: {e}"); self.rollback(); return False

    def registra_consultazione(self, data: date, richiedente: str, documento_identita: Optional[str], motivazione: Optional[str], materiale_consultato: Optional[str], funzionario_autorizzante: Optional[str]) -> bool:
        try:
            call_proc = "CALL registra_consultazione(%s, %s, %s, %s, %s, %s)"
            if self.execute_query(call_proc, (data, richiedente, documento_identita, motivazione, materiale_consultato, funzionario_autorizzante)):
                self.commit(); logger.info(f"Reg. consultazione: {richiedente}, {data}"); return True
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB reg. consultazione: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python reg. consultazione: {e}"); self.rollback(); return False

    # ========================================
    # FUNZIONI DI REPORTISTICA (script 14 e altri)
    # ========================================
    def genera_certificato_proprieta(self, partita_id: int) -> Optional[str]:
        try:
            query = "SELECT genera_certificato_proprieta(%s) AS certificato"
            if self.execute_query(query, (partita_id,)): result = self.fetchone(); return result.get('certificato') if result else None
        except psycopg2.Error as db_err: logger.error(f"Errore DB genera_certificato_proprieta: {db_err}")
        except Exception as e: logger.error(f"Errore Python genera_certificato_proprieta: {e}")
        return None
    # ... (Implementa gli altri metodi di reportistica con try...except simili) ...
    # Inserisci/Sostituisci questi metodi nella classe CatastoDBManager in catasto_db_manager.py

    def genera_report_genealogico(self, partita_id: int) -> Optional[str]:
        """Chiama la funzione SQL per generare il report genealogico."""
        try:
            query = "SELECT genera_report_genealogico(%s) AS report"
            if self.execute_query(query, (partita_id,)):
                result = self.fetchone()
                return result.get('report') if result else None
            return None # Errore di connessione o altro
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in genera_report_genealogico (ID: {partita_id}): {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python in genera_report_genealogico (ID: {partita_id}): {e}")
            self.rollback() # Rollback per errori Python generici
            return None

    def genera_report_possessore(self, possessore_id: int) -> Optional[str]:
        """Chiama la funzione SQL per generare il report storico del possessore."""
        try:
            query = "SELECT genera_report_possessore(%s) AS report"
            if self.execute_query(query, (possessore_id,)):
                result = self.fetchone()
                return result.get('report') if result else None
            return None # Errore di connessione o altro
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in genera_report_possessore (ID: {possessore_id}): {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python in genera_report_possessore (ID: {possessore_id}): {e}")
            self.rollback()
            return None

    def genera_report_consultazioni(self, data_inizio: Optional[date]=None, data_fine: Optional[date]=None, richiedente: Optional[str]=None) -> Optional[str]:
        """Chiama la funzione SQL per generare il report delle consultazioni."""
        try:
            query = "SELECT genera_report_consultazioni(%s, %s, %s) AS report"
            if self.execute_query(query, (data_inizio, data_fine, richiedente)):
                result = self.fetchone()
                return result.get('report') if result else None
            return None # Errore di connessione o altro
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in genera_report_consultazioni: {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python in genera_report_consultazioni: {e}")
            self.rollback()
            return None
    def get_report_comune(self, comune_nome: str) -> Optional[Dict]:
        # ... implementazione con try/except ...
        return None
    # Inserisci questo metodo dentro la classe CatastoDBManager in catasto_db_manager.py

    def get_partite_complete_view(self, comune_nome: Optional[str] = None, stato: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Recupera le partite dalla vista materializzata mv_partite_complete, con filtri opzionali."""
        try:
            conditions = []
            params = []
            query = "SELECT * FROM mv_partite_complete" # Usa la vista materializzata

            if comune_nome:
                conditions.append("comune_nome ILIKE %s")
                params.append(f"%{comune_nome}%")
            if stato:
                # Assicura che lo stato sia uno dei valori validi (o aggiungi gestione errori se necessario)
                if stato.lower() in ['attiva', 'inattiva']:
                    conditions.append("stato = %s")
                    params.append(stato.lower())
                else:
                    logger.warning(f"Stato non valido '{stato}' ignorato nel filtro.")


            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY comune_nome, numero_partita LIMIT %s"
            params.append(limit)

            if self.execute_query(query, tuple(params)):
                return self.fetchall()
            else:
                # Errore di connessione o altro già loggato da execute_query
                return []
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_partite_complete_view: {db_err}")
            return []
        except Exception as e:
            logger.error(f"Errore Python in get_partite_complete_view: {e}")
            # Nessun rollback necessario per SELECT
            return []
        # Inserisci questo metodo dentro la classe CatastoDBManager in catasto_db_manager.py

    def get_immobili_per_tipologia(self, comune_nome: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Recupera il riepilogo immobili per tipologia dalla vista materializzata, con filtro opzionale per comune."""
        try:
            params = []
            query = "SELECT * FROM mv_immobili_per_tipologia" # Usa la vista materializzata

            if comune_nome:
                query += " WHERE comune_nome ILIKE %s"
                params.append(f"%{comune_nome}%")

            query += " ORDER BY comune_nome, classificazione LIMIT %s"
            params.append(limit)

            if self.execute_query(query, tuple(params)):
                return self.fetchall()
            else:
                # Errore di connessione o altro già loggato da execute_query
                return []
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_immobili_per_tipologia: {db_err}")
            return []
        except Exception as e:
            logger.error(f"Errore Python in get_immobili_per_tipologia: {e}")
            # Nessun rollback necessario per SELECT
            return []
        # Inserisci questo metodo dentro la classe CatastoDBManager in catasto_db_manager.py

    def get_report_annuale_partite(self, comune_nome: str, anno: int) -> List[Dict]:
        """Chiama la funzione SQL report_annuale_partite per ottenere il report."""
        try:
            # La funzione SQL si chiama 'report_annuale_partite'
            query = "SELECT * FROM report_annuale_partite(%s, %s)"
            if self.execute_query(query, (comune_nome, anno)):
                return self.fetchall()
            else:
                # Errore di connessione o altro già loggato da execute_query
                return []
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_report_annuale_partite (Comune: {comune_nome}, Anno: {anno}): {db_err}")
            return []
        except Exception as e:
            logger.error(f"Errore Python in get_report_annuale_partite (Comune: {comune_nome}, Anno: {anno}): {e}")
            # Nessun rollback necessario per SELECT (chiamata a funzione che legge)
            return []
        # Inserisci questo metodo dentro la classe CatastoDBManager in catasto_db_manager.py

    def get_report_proprieta_possessore(self, possessore_id: int, data_inizio: date, data_fine: date) -> List[Dict]:
        """Chiama la funzione SQL report_proprieta_possessore per ottenere il report."""
        try:
            # La funzione SQL si chiama 'report_proprieta_possessore'
            query = "SELECT * FROM report_proprieta_possessore(%s, %s, %s)"
            if self.execute_query(query, (possessore_id, data_inizio, data_fine)):
                return self.fetchall()
            else:
                # Errore di connessione o altro già loggato da execute_query
                return []
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_report_proprieta_possessore (ID: {possessore_id}, Periodo: {data_inizio}-{data_fine}): {db_err}")
            return []
        except Exception as e:
            logger.error(f"Errore Python in get_report_proprieta_possessore (ID: {possessore_id}, Periodo: {data_inizio}-{data_fine}): {e}")
            # Nessun rollback necessario per SELECT (chiamata a funzione che legge)
            return []
        
        # Inserisci questo metodo dentro la classe CatastoDBManager in catasto_db_manager.py
    def get_report_comune(self, comune_nome: str) -> Optional[Dict]:
        """Chiama la funzione SQL genera_report_comune per ottenere le statistiche."""
        try:
            # La funzione SQL si chiama 'genera_report_comune'
            query = "SELECT * FROM genera_report_comune(%s)"
            if self.execute_query(query, (comune_nome,)):
                # Questa funzione SQL restituisce una sola riga
                return self.fetchone()
            else:
                # Errore di connessione o altro già loggato da execute_query
                return None
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_report_comune (Comune: {comune_nome}): {db_err}")
            return None
        except Exception as e:
            logger.error(f"Errore Python in get_report_comune (Comune: {comune_nome}): {e}")
            # Nessun rollback necessario per SELECT (chiamata a funzione che legge)
            return None

    # ========================================
    # METODI MANUTENZIONE E INTEGRITÀ (script 13)
    # ========================================
    def verifica_integrita_database(self) -> Tuple[bool, str]:
        # ... (implementazione come prima, già abbastanza robusta) ...
        messages = []
        def notice_handler(notice): msg = notice.pgerror.split('CONTEXT:')[0].strip() if notice.pgerror else str(notice); messages.append(msg)
        original_notice_handler = self.conn.notices.pop if hasattr(self.conn, 'notices') and self.conn.notices else None
        if hasattr(self.conn, 'notices'): self.conn.notices.append(notice_handler)
        problemi_trovati = False; output_msg = ""
        try:
            if self.execute_query("CALL verifica_integrita_database(NULL)"): pass
            else: problemi_trovati = True; messages.append("Errore chiamata verifica_integrita_database.")
            for msg in messages:
                if "Problemi di integrità rilevati" in msg or "Problema:" in msg: problemi_trovati = True
                output_msg += msg + "\n"
            if not problemi_trovati and not output_msg: output_msg = "Nessun problema di integrità rilevato."
        except psycopg2.Error as db_err: logger.error(f"Errore DB verifica integrità: {db_err}"); output_msg = f"Errore DB: {db_err}"; problemi_trovati = True
        except Exception as e: logger.error(f"Errore Python verifica integrità: {e}"); output_msg = f"Errore Python: {e}"; problemi_trovati = True
        finally:
            if hasattr(self.conn, 'notices'):
                 if notice_handler in self.conn.notices: self.conn.notices.remove(notice_handler)
                 if original_notice_handler: self.conn.notices.append(original_notice_handler)
        return problemi_trovati, output_msg.strip()
    def run_database_maintenance(self) -> bool:
        # ... (implementazione come prima) ...
        logger.info("Avvio manutenzione database...")
        try:
            if self.execute_query("CALL manutenzione_database()"): self.commit(); logger.info("Manutenzione completata."); return True
            else: logger.error("Fallita chiamata a 'manutenzione_database'."); return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB manutenzione: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python manutenzione: {e}"); self.rollback(); return False

    # Inserisci questo metodo dentro la classe CatastoDBManager in catasto_db_manager.py

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
        
    
    # In catasto_db_manager.py (sostituisci il metodo esistente)

    def run_database_maintenance(self) -> bool:
        logger.info("Avvio manutenzione database...")
        original_autocommit = None
        connection_usable = False # Flag per tracciare se la connessione era usabile
        success = False
        try:
            if not self.conn or self.conn.closed:
                logger.warning("Connessione non attiva per manutenzione. Tentativo di riconnessione...")
                if not self.connect():
                    return False # Impossibile connettere

            # Controlla lo stato prima di procedere
            if self.conn.closed:
                 logger.error("La connessione è chiusa prima di avviare la manutenzione.")
                 return False
            # Verifica se lo stato della connessione è pronto
            # Usiamo self.conn.status == psycopg2.extensions.STATUS_READY
            # Nota: Potrebbe essere necessario importare psycopg2.extensions
            try:
                import psycopg2.extensions
                if self.conn.status != psycopg2.extensions.STATUS_READY:
                    logger.warning(f"Stato connessione non pronto ({self.conn.status}). Tentativo di reset...")
                    self.conn.reset() # Prova a resettare la connessione
                    if self.conn.status != psycopg2.extensions.STATUS_READY:
                         logger.error("Reset connessione fallito. Impossibile eseguire manutenzione.")
                         return False
            except ImportError:
                logger.warning("Modulo psycopg2.extensions non trovato, impossibile verificare stato connessione pre-reset.")
            except Exception as status_err:
                logger.warning(f"Errore nel controllo/reset dello stato connessione: {status_err}")
                # Proseguiamo con cautela, ma la connessione potrebbe essere instabile

            connection_usable = True # La connessione sembra ok o è stata resettata
            original_autocommit = self.conn.autocommit
            self.conn.autocommit = True
            logger.debug("Autocommit impostato a True per manutenzione.")

            # Esegui la chiamata alla procedura
            # Usiamo un cursore separato per sicurezza in modalità autocommit
            with self.conn.cursor() as temp_cur:
                 temp_cur.execute("CALL manutenzione_database()")
                 # Nessun fetchone/fetchall per CALL

            logger.info("Manutenzione generale completata (chiamata a procedura terminata).")
            success = True

        except psycopg2.Error as db_err:
            # L'errore originale (es. da ANALYZE o REFRESH) viene catturato qui
            logger.error(f"Errore DB durante la manutenzione: {db_err}")
            success = False
            # La connessione potrebbe essere in uno stato non valido dopo l'errore
            connection_usable = False # Segna come non utilizzabile
        except Exception as e:
            logger.error(f"Errore Python durante la manutenzione: {e}")
            success = False
            connection_usable = False # Segna come non utilizzabile
        finally:
            # Ripristina lo stato originale di autocommit SOLO se la connessione
            # era utilizzabile E non è stata chiusa nel frattempo e avevamo salvato lo stato originale
            if connection_usable and self.conn and not self.conn.closed and original_autocommit is not None:
                try:
                    # Verifica nuovamente lo stato prima di reimpostare
                    # Nota: import di psycopg2.extensions richiesto
                    try:
                        import psycopg2.extensions
                        if self.conn.status == psycopg2.extensions.STATUS_READY:
                            self.conn.autocommit = original_autocommit
                            logger.debug(f"Autocommit ripristinato a {original_autocommit}.")
                        else:
                             logger.warning(f"Stato connessione non pronto ({self.conn.status}) nel finally. Impossibile ripristinare autocommit.")
                             # Considera la disconnessione forzata se lo stato non è pronto dopo l'operazione
                             # self.disconnect() # Opzione drastica
                    except ImportError:
                         logger.warning("Modulo psycopg2.extensions non trovato, impossibile verificare stato connessione post-operazione. Ripristino autocommit con cautela.")
                         # Tentativo di ripristino anche senza controllo stato dettagliato
                         self.conn.autocommit = original_autocommit
                         logger.debug(f"Autocommit ripristinato a {original_autocommit} (senza controllo stato).")
                    except Exception as status_err_finally:
                         logger.error(f"Errore nel controllo dello stato connessione nel finally: {status_err_finally}")
                         # Non tentare di modificare autocommit se il controllo stesso fallisce
                except psycopg2.Error as final_err:
                     # Questo cattura l'errore "set_session cannot be used inside a transaction" se la sessione è ancora invalida
                     logger.error(f"Errore nel ripristinare autocommit nel finally: {final_err}")
                     # A questo punto la connessione è probabilmente inutilizzabile
                     # Disconnessione forzata è una buona idea
                     self.disconnect()

            # Non fare commit/rollback qui perché eravamo (o dovevamo essere) in autocommit
            # o la transazione è fallita e il rollback è implicito o gestito da psycopg2

        return success
        
    # ========================================
    # SISTEMA DI AUDIT E UTENTI (script 06, 07, 15)
    # ========================================
    def get_audit_log(self, tabella=None, operazione=None, record_id=None, data_inizio=None, data_fine=None, utente_db=None, app_user_id=None, session_id=None, limit=100) -> List[Dict]:
        # ... (implementazione come prima) ...
        try:
            conditions = []; params = []
            query = "SELECT al.*, u.username AS app_username, u.nome_completo AS app_user_nome FROM audit_log al LEFT JOIN utente u ON al.app_user_id = u.id"
            # ... costruisci conditions/params ...
            if tabella: conditions.append("al.tabella = %s"); params.append(tabella)
            # ... (altri filtri) ...
            if conditions: query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY al.timestamp DESC LIMIT %s"; params.append(limit)
            if self.execute_query(query, tuple(params)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_audit_log: {db_err}")
        except Exception as e: logger.error(f"Errore Python get_audit_log: {e}")
        return []

    def get_record_history(self, tabella: str, record_id: int) -> List[Dict]:
        # ... (implementazione come prima) ...
        try:
            query = "SELECT * FROM get_record_history(%s, %s)"
            if self.execute_query(query, (tabella, record_id)): return self.fetchall()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_record_history: {db_err}")
        except Exception as e: logger.error(f"Errore Python get_record_history: {e}")
        return []

    def genera_report_audit(self, tabella=None, data_inizio=None, data_fine=None, operazione=None, utente_db=None, app_user_id=None) -> str:
        # ... (implementazione come prima) ...
        logs = self.get_audit_log(tabella, operazione, None, data_inizio, data_fine, utente_db, app_user_id, None, 1000)
        if not logs: return "Nessun log di audit trovato."
        report = "..." # Costruzione stringa report
        return report

    def create_user(self, username: str, password_hash: str, nome_completo: str, email: str, ruolo: str) -> bool:
        """Crea un nuovo utente, gestendo l'errore di duplicato."""
        try:
            call_proc = "CALL crea_utente(%s, %s, %s, %s, %s)"
            # execute_query rilancia l'errore DB specifico
            if self.execute_query(call_proc, (username, password_hash, nome_completo, email, ruolo)):
                self.commit()
                logger.info(f"Utente {username} creato con successo.")
                return True
            else: return False # Errore connessione
        except psycopg2.errors.UniqueViolation as uv_error: # Cattura l'errore rilanciato
            logger.error(f"Errore creazione utente '{username}': Username o Email già esistente.")
            logger.debug(f"Dettaglio errore DB: {uv_error}")
            # Rollback è già stato fatto da execute_query
            return False
        except psycopg2.Error as db_err: logger.error(f"Errore DB in create_user: {db_err}"); return False
        except Exception as e: logger.error(f"Errore Python in create_user: {e}"); self.rollback(); return False

    def get_user_credentials(self, username: str) -> Optional[Dict]:
        # ... (implementazione come prima) ...
        try:
            query = "SELECT id, password_hash FROM utente WHERE username = %s AND attivo = TRUE"
            if self.execute_query(query, (username,)): return self.fetchone()
        except psycopg2.Error as db_err: logger.error(f"Errore DB get_user_credentials: {db_err}")
        except Exception as e: logger.error(f"Errore Python get_user_credentials: {e}")
        return None

    def register_access(self, utente_id: int, azione: str, indirizzo_ip: str = None, user_agent: str = None, esito: bool = True, application_name: str = 'CatastoApp') -> Optional[str]:
        # ... (implementazione come prima) ...
        session_id = None
        try:
            session_id = str(uuid.uuid4())
            call_proc = "CALL registra_accesso(%s, %s, %s, %s, %s, %s, %s)"
            params = (utente_id, azione, indirizzo_ip, user_agent, esito, session_id, application_name)
            if self.execute_query(call_proc, params): self.commit(); return session_id
            else: return None
        except psycopg2.Error as db_err: logger.error(f"Errore DB reg. accesso {utente_id}: {db_err}"); return None
        except Exception as e: logger.error(f"Errore Python reg. accesso {utente_id}: {e}"); self.rollback(); return None

    def logout_user(self, user_id: Optional[int], session_id: Optional[str], client_ip: Optional[str] = None) -> bool:
        # ... (implementazione come prima) ...
        if user_id is None or session_id is None: logger.warning("Logout senza user_id/session_id."); self.clear_session_app_user(); return False
        try:
            call_proc = "CALL logout_utente(%s, %s, %s)"
            success = self.execute_query(call_proc, (user_id, session_id, client_ip))
            if success: self.commit(); logger.info(f"Logout registrato user {user_id}.")
            self.clear_session_app_user(); return success
        except psycopg2.Error as db_err: logger.error(f"Errore DB logout {user_id}: {db_err}"); self.clear_session_app_user(); return False
        except Exception as e: logger.error(f"Errore Python logout {user_id}: {e}"); self.rollback(); self.clear_session_app_user(); return False

    def check_permission(self, utente_id: int, permesso_nome: str) -> bool:
        # ... (implementazione come prima) ...
        try:
            query = "SELECT ha_permesso(%s, %s) AS permesso"
            if self.execute_query(query, (utente_id, permesso_nome)): result = self.fetchone(); return result.get('permesso', False) if result else False
        except psycopg2.Error as db_err: logger.error(f"Errore DB check_permission: {db_err}")
        except Exception as e: logger.error(f"Errore Python check_permission: {e}")
        return False

    def set_session_app_user(self, user_id: Optional[int], client_ip: Optional[str] = None):
        # ... (implementazione come prima) ...
        if not self.conn or self.conn.closed: logger.warning("No conn per set_session_app_user."); return False
        try:
            user_id_str = str(user_id) if user_id is not None else None
            # SELECT set_config è più sicuro di SET diretto
            if self.execute_query("SELECT set_config('app.user_id', %s, FALSE);", (user_id_str,)) and \
               self.execute_query("SELECT set_config('app.ip_address', %s, FALSE);", (client_ip,)):
                logger.debug(f"Session vars set: user={user_id_str}, ip={client_ip}")
                return True
            return False
        except Exception as e: logger.error(f"Errore set session vars: {e}"); return False

    def clear_session_app_user(self):
        self.set_session_app_user(user_id=None, client_ip=None)

    # ========================================
    # METODI SISTEMA DI BACKUP (script 09)
    # ========================================
    # (implementazioni come prima, aggiungi try/except se necessario)
    def register_backup_log(self, nome_file: str, utente: str, tipo: str, esito: bool, percorso_file: str, dimensione_bytes: Optional[int] = None, messaggio: Optional[str] = None) -> Optional[int]:
         try:
             query = "SELECT registra_backup(%s, %s, %s, %s, %s, %s, %s)"
             if self.execute_query(query, (nome_file, utente, dimensione_bytes, tipo, esito, messaggio, percorso_file)):
                  result = self.fetchone(); self.commit(); return result.get('registra_backup') if result else None
         except Exception as e: logger.error(f"Errore reg log backup: {e}")
         return None
    def get_backup_command_suggestion(self, tipo: str = 'completo') -> Optional[str]:
         try:
             query = "SELECT get_backup_commands(%s) AS commands"
             if self.execute_query(query, (tipo,)): result = self.fetchone(); return result.get('commands') if result else None
         except Exception as e: logger.error(f"Errore get backup cmd: {e}")
         return None
    # ... (altri metodi backup con try/except) ...
    def get_restore_command_suggestion(self, backup_log_id: int) -> Optional[str]:
         try:
             query = "SELECT get_restore_commands(%s) AS command"
             if self.execute_query(query, (backup_log_id,)): result = self.fetchone(); return result.get('command') if result else None
         except Exception as e: logger.error(f"Errore get restore cmd: {e}")
         return None
    def cleanup_old_backup_logs(self, giorni_conservazione: int = 30) -> bool:
         try:
              if self.execute_query("CALL pulizia_backup_vecchi(%s)", (giorni_conservazione,)): self.commit(); return True
         except Exception as e: logger.error(f"Errore pulizia log backup: {e}")
         return False
    def generate_backup_script(self, backup_dir: str) -> Optional[str]:
         try:
             query = "SELECT genera_script_backup_automatico(%s) AS script_content"
             if self.execute_query(query, (backup_dir,)): result = self.fetchone(); return result.get('script_content') if result else None
         except Exception as e: logger.error(f"Errore gen backup script: {e}")
         return None
    def get_backup_logs(self, limit: int = 20) -> List[Dict]:
         try:
             query = "SELECT * FROM backup_registro ORDER BY timestamp DESC LIMIT %s"
             if self.execute_query(query, (limit,)): return self.fetchall()
         except Exception as e: logger.error(f"Errore get backup logs: {e}")
         return []

    # ========================================
    # OTTIMIZZAZIONE E RICERCA AVANZATA (script 10)
    # ========================================
    # (implementazioni come prima, aggiungi try/except)
    def ricerca_avanzata_possessori(self, query_text: str) -> List[Dict]:
         try:
             query = "SELECT * FROM ricerca_avanzata_possessori(%s)"
             if self.execute_query(query, (query_text,)): return self.fetchall()
         except Exception as e: logger.error(f"Errore ricerca avanzata possessori: {e}")
         return []
    def ricerca_avanzata_immobili(self, comune: str = None, natura: str = None, localita: str = None, classificazione: str = None, possessore: str = None) -> List[Dict]:
         try:
             query = "SELECT * FROM ricerca_avanzata_immobili(%s, %s, %s, %s, %s)"
             if self.execute_query(query, (comune, natura, localita, classificazione, possessore)): return self.fetchall()
         except Exception as e: logger.error(f"Errore ricerca avanzata immobili: {e}")
         return []
    # ... (altri metodi ottimizzazione con try/except) ...
    def analyze_slow_queries(self, min_duration_ms: int = 1000) -> List[Dict]:
         try:
             query = "SELECT * FROM analizza_query_lente(%s)"
             if self.execute_query(query, (min_duration_ms,)): return self.fetchall()
         except psycopg2.errors.UndefinedTable: logger.warning("Estensione pg_stat_statements non abilitata/installata."); return []
         except Exception as e: logger.error(f"Errore analisi query lente: {e}")
         return []
    def check_index_fragmentation(self) -> List[Dict]:
        try:
            if self.execute_query("CALL controlla_frammentazione_indici()"): self.commit(); logger.info("Controllo framm. eseguito."); return []
        except Exception as e: logger.error(f"Errore controllo framm.: {e}")
        return []
    def get_optimization_suggestions(self) -> Optional[str]:
        try:
            query = "SELECT suggerimenti_ottimizzazione() AS suggestions"
            if self.execute_query(query): result = self.fetchone(); return result.get('suggestions') if result else None
        except Exception as e: logger.error(f"Errore get optimization sugg: {e}")
        return None

    # ========================================
    # FUNZIONALITÀ STORICHE AVANZATE (script 11)
    # ========================================
    # (implementazioni come prima, aggiungi try/except)
    def get_historical_periods(self) -> List[Dict]:
         try:
             query = "SELECT id, nome, anno_inizio, anno_fine, descrizione FROM periodo_storico ORDER BY anno_inizio"
             if self.execute_query(query): return self.fetchall()
         except Exception as e: logger.error(f"Errore get historical periods: {e}")
         return []
    # ... (altri metodi storici con try/except) ...
    def get_historical_name(self, entity_type: str, entity_id: int, year: Optional[int] = None) -> Optional[Dict]:
         try:
             if year is None: year = datetime.now().year
             query = "SELECT * FROM get_nome_storico(%s, %s, %s)"
             if self.execute_query(query, (entity_type, entity_id, year)): return self.fetchone()
         except Exception as e: logger.error(f"Errore get historical name: {e}")
         return None
    def register_historical_name(self, entity_type: str, entity_id: int, name: str, period_id: int, year_start: int, year_end: Optional[int] = None, notes: Optional[str] = None) -> bool:
         try:
             call_proc = "CALL registra_nome_storico(%s, %s, %s, %s, %s, %s, %s)"
             if self.execute_query(call_proc, (entity_type, entity_id, name, period_id, year_start, year_end, notes)): self.commit(); return True
         except Exception as e: logger.error(f"Errore reg nome storico: {e}")
         return False
    def search_historical_documents(self, title: Optional[str] = None, doc_type: Optional[str] = None, period_id: Optional[int] = None, year_start: Optional[int] = None, year_end: Optional[int] = None, partita_id: Optional[int] = None) -> List[Dict]:
         try:
             query = "SELECT * FROM ricerca_documenti_storici(%s, %s, %s, %s, %s, %s)"
             if self.execute_query(query, (title, doc_type, period_id, year_start, year_end, partita_id)): return self.fetchall()
         except Exception as e: logger.error(f"Errore search hist docs: {e}")
         return []
    def get_property_genealogy(self, partita_id: int) -> List[Dict]:
         try:
             query = "SELECT * FROM albero_genealogico_proprieta(%s)"
             if self.execute_query(query, (partita_id,)): return self.fetchall()
         except Exception as e: logger.error(f"Errore get property genealogy: {e}")
         return []
    def get_cadastral_stats_by_period(self, comune: Optional[str] = None, year_start: int = 1900, year_end: Optional[int] = None) -> List[Dict]:
         try:
             if year_end is None: year_end = datetime.now().year
             query = "SELECT * FROM statistiche_catastali_periodo(%s, %s, %s)"
             if self.execute_query(query, (comune, year_start, year_end)): return self.fetchall()
         except Exception as e: logger.error(f"Errore get cadastral stats: {e}")
         return []
    def link_document_to_partita(self, document_id: int, partita_id: int, relevance: str = 'correlata', notes: Optional[str] = None) -> bool:
         if relevance not in ['primaria', 'secondaria', 'correlata']: return False
         query = "INSERT INTO documento_partita (documento_id, partita_id, rilevanza, note) VALUES (%s, %s, %s, %s) ON CONFLICT (documento_id, partita_id) DO UPDATE SET rilevanza = EXCLUDED.rilevanza, note = EXCLUDED.note"
         try:
             if self.execute_query(query, (document_id, partita_id, relevance, notes)): self.commit(); return True
         except Exception as e: logger.error(f"Errore link doc-partita: {e}")
         return False

    # ========================================
    # METODI CRUD AGGIUNTIVI (script 12) - CORRETTI E COMPLETI
    # ========================================
    def update_immobile(self, immobile_id: int, **kwargs) -> bool:
        params = {'p_id': immobile_id, 'p_natura': kwargs.get('natura'), 'p_numero_piani': kwargs.get('numero_piani'), 'p_numero_vani': kwargs.get('numero_vani'), 'p_consistenza': kwargs.get('consistenza'), 'p_classificazione': kwargs.get('classificazione'), 'p_localita_id': kwargs.get('localita_id')}
        call_proc = "CALL aggiorna_immobile(%(p_id)s, %(p_natura)s, %(p_numero_piani)s, %(p_numero_vani)s, %(p_consistenza)s, %(p_classificazione)s, %(p_localita_id)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); return True
        except Exception as e: logger.error(f"Errore upd immobile {immobile_id}: {e}")
        return False
    def delete_immobile(self, immobile_id: int) -> bool:
        try:
            if self.execute_query("CALL elimina_immobile(%s)", (immobile_id,)): self.commit(); return True
        except Exception as e: logger.error(f"Errore del immobile {immobile_id}: {e}")
        return False
    def search_immobili(self, partita_id: Optional[int] = None, comune_nome: Optional[str] = None, localita_id: Optional[int] = None, natura: Optional[str] = None, classificazione: Optional[str] = None) -> List[Dict]:
        try:
            query = "SELECT * FROM cerca_immobili(%s, %s, %s, %s, %s)"
            if self.execute_query(query, (partita_id, comune_nome, localita_id, natura, classificazione)): return self.fetchall()
        except Exception as e: logger.error(f"Errore search immobili: {e}")
        return []
    def update_variazione(self, variazione_id: int, **kwargs) -> bool:
        params = {'p_variazione_id': variazione_id, 'p_tipo': kwargs.get('tipo'), 'p_data_variazione': kwargs.get('data_variazione'), 'p_numero_riferimento': kwargs.get('numero_riferimento'), 'p_nominativo_riferimento': kwargs.get('nominativo_riferimento')}
        call_proc = "CALL aggiorna_variazione(%(p_variazione_id)s, %(p_tipo)s, %(p_data_variazione)s, %(p_numero_riferimento)s, %(p_nominativo_riferimento)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); return True
        except Exception as e: logger.error(f"Errore upd variazione {variazione_id}: {e}")
        return False
    def delete_variazione(self, variazione_id: int, force: bool = False, restore_partita: bool = False) -> bool:
        try:
            if self.execute_query("CALL elimina_variazione(%s, %s, %s)", (variazione_id, force, restore_partita)): self.commit(); return True
        except Exception as e: logger.error(f"Errore del variazione {variazione_id}: {e}")
        return False
    def search_variazioni(self, tipo: Optional[str] = None, data_inizio: Optional[date] = None, data_fine: Optional[date] = None, partita_origine_id: Optional[int] = None, partita_destinazione_id: Optional[int] = None, comune: Optional[str] = None) -> List[Dict]:
        try:
            query = "SELECT * FROM cerca_variazioni(%s, %s, %s, %s, %s, %s)"
            if self.execute_query(query, (tipo, data_inizio, data_fine, partita_origine_id, partita_destinazione_id, comune)): return self.fetchall()
        except Exception as e: logger.error(f"Errore search variazioni: {e}")
        return []
    def insert_contratto(self, variazione_id: int, tipo: str, data_contratto: date, notaio: Optional[str] = None, repertorio: Optional[str] = None, note: Optional[str] = None) -> bool:
         try:
             call_proc = "CALL inserisci_contratto(%s, %s, %s, %s, %s, %s)"
             if self.execute_query(call_proc, (variazione_id, tipo, data_contratto, notaio, repertorio, note)): self.commit(); return True
         except Exception as e: logger.error(f"Errore ins contratto var {variazione_id}: {e}")
         return False
    def update_contratto(self, contratto_id: int, **kwargs) -> bool:
        params = {'p_id': contratto_id, 'p_tipo': kwargs.get('tipo'), 'p_data_contratto': kwargs.get('data_contratto'), 'p_notaio': kwargs.get('notaio'), 'p_repertorio': kwargs.get('repertorio'), 'p_note': kwargs.get('note')}
        call_proc = "CALL aggiorna_contratto(%(p_id)s, %(p_tipo)s, %(p_data_contratto)s, %(p_notaio)s, %(p_repertorio)s, %(p_note)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); return True
        except Exception as e: logger.error(f"Errore upd contratto {contratto_id}: {e}")
        return False
    def delete_contratto(self, contratto_id: int) -> bool:
        try:
            if self.execute_query("CALL elimina_contratto(%s)", (contratto_id,)): self.commit(); return True
        except Exception as e: logger.error(f"Errore del contratto {contratto_id}: {e}")
        return False
    def update_consultazione(self, consultazione_id: int, **kwargs) -> bool:
        params = {'p_id': consultazione_id, 'p_data': kwargs.get('data'), 'p_richiedente': kwargs.get('richiedente'), 'p_documento_identita': kwargs.get('documento_identita'), 'p_motivazione': kwargs.get('motivazione'), 'p_materiale_consultato': kwargs.get('materiale_consultato'), 'p_funzionario_autorizzante': kwargs.get('funzionario_autorizzante')}
        call_proc = "CALL aggiorna_consultazione(%(p_id)s, %(p_data)s, %(p_richiedente)s, %(p_documento_identita)s, %(p_motivazione)s, %(p_materiale_consultato)s, %(p_funzionario_autorizzante)s)"
        try:
            if self.execute_query(call_proc, params): self.commit(); return True
        except Exception as e: logger.error(f"Errore upd consultazione {consultazione_id}: {e}")
        return False
    def delete_consultazione(self, consultazione_id: int) -> bool:
        try:
            if self.execute_query("CALL elimina_consultazione(%s)", (consultazione_id,)): self.commit(); return True
        except Exception as e: logger.error(f"Errore del consultazione {consultazione_id}: {e}")
        return False
    def search_consultazioni(self, data_inizio: Optional[date] = None, data_fine: Optional[date] = None, richiedente: Optional[str] = None, funzionario: Optional[str] = None) -> List[Dict]:
        try:
            query = "SELECT * FROM cerca_consultazioni(%s, %s, %s, %s)"
            if self.execute_query(query, (data_inizio, data_fine, richiedente, funzionario)): return self.fetchall()
        except Exception as e: logger.error(f"Errore search consultazioni: {e}")
        return []
    def duplicate_partita(self, partita_id: int, nuovo_numero_partita: int, mantenere_possessori: bool = True, mantenere_immobili: bool = False) -> bool:
         try:
             call_proc = "CALL duplica_partita(%s, %s, %s, %s)"
             if self.execute_query(call_proc, (partita_id, nuovo_numero_partita, mantenere_possessori, mantenere_immobili)): self.commit(); return True
         except Exception as e: logger.error(f"Errore duplica partita {partita_id}: {e}")
         return False
    def transfer_immobile(self, immobile_id: int, nuova_partita_id: int, registra_variazione: bool = False) -> bool:
         try:
             call_proc = "CALL trasferisci_immobile(%s, %s, %s)"
             if self.execute_query(call_proc, (immobile_id, nuova_partita_id, registra_variazione)): self.commit(); return True
         except Exception as e: logger.error(f"Errore trasf immobile {immobile_id}: {e}")
         return False
    def export_partita_json(self, partita_id: int) -> Optional[str]:
        try:
            query = "SELECT esporta_partita_json(%s) AS partita_json"
            if self.execute_query(query, (partita_id,)):
                result = self.fetchone()
                if result and result.get('partita_json'):
                     try: return json.dumps(result['partita_json'], indent=4, ensure_ascii=False)
                     except Exception as e: logger.error(f"Errore JSON exp partita {partita_id}: {e}"); return str(result['partita_json'])
        except Exception as e: logger.error(f"Errore DB export partita {partita_id}: {e}")
        return None
    def export_possessore_json(self, possessore_id: int) -> Optional[str]:
        try:
            query = "SELECT esporta_possessore_json(%s) AS possessore_json"
            if self.execute_query(query, (possessore_id,)):
                result = self.fetchone()
                if result and result.get('possessore_json'):
                     try: return json.dumps(result['possessore_json'], indent=4, ensure_ascii=False)
                     except Exception as e: logger.error(f"Errore JSON exp possessore {possessore_id}: {e}"); return str(result['possessore_json'])
        except Exception as e: logger.error(f"Errore DB export possessore {possessore_id}: {e}")
        return None
    # Inserisci questo metodo dentro la classe CatastoDBManager in catasto_db_manager.py
# vicino agli altri metodi di recupero dati (es. dopo get_partite_complete_view)

    def get_cronologia_variazioni(self, comune_origine: Optional[str] = None, tipo_variazione: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Recupera la cronologia delle variazioni dalla vista materializzata, con filtri opzionali."""
        try:
            conditions = []
            params = []
            query = "SELECT * FROM mv_cronologia_variazioni" # Usa la vista materializzata

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
            else:
                # execute_query ha fallito (errore connessione o altro già loggato)
                return []
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_cronologia_variazioni: {db_err}")
            return []
        except Exception as e:
            logger.error(f"Errore Python in get_cronologia_variazioni: {e}")
            # Non c'è bisogno di rollback qui perché è una SELECT
            return []
    # Inserisci questo metodo dentro la classe CatastoDBManager in catasto_db_manager.py

    def get_statistiche_comune(self) -> List[Dict]:
        """Recupera le statistiche per comune dalla vista materializzata mv_statistiche_comune."""
        try:
            query = "SELECT * FROM mv_statistiche_comune ORDER BY comune"
            if self.execute_query(query):
                return self.fetchall()
            else:
                # Errore di connessione o altro già loggato da execute_query
                return []
        except psycopg2.Error as db_err:
            logger.error(f"Errore DB in get_statistiche_comune: {db_err}")
            return []
        except Exception as e:
            logger.error(f"Errore Python in get_statistiche_comune: {e}")
            # Nessun rollback necessario per SELECT
            return []

# Esempio di utilizzo minimale (se eseguito direttamente)
if __name__ == "__main__":
    db = CatastoDBManager()
    if db.connect():
        print("CatastoDBManager: Connessione OK.")
        sugg = db.get_optimization_suggestions()
        if sugg: print("Suggerimenti Ottimizzazione:\n", sugg)
        else: print("Nessun suggerimento o errore.")
        db.disconnect()
    else:
        print("CatastoDBManager: Connessione fallita.")