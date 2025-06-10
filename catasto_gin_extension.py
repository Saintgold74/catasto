# ========================================================================
# ESTENSIONE GIN CORRETTA PER CATASTO_DB_MANAGER
# File: catasto_gin_extension.py (VERSIONE CORRETTA)
# ========================================================================

"""
Estensione del CatastoDBManager per ricerca fuzzy con indici GIN.
Versione corretta che usa l'API reale del CatastoDBManager.
"""

from typing import List, Dict, Any, Optional, Tuple
import psycopg2.errors
import psycopg2.extras
import logging
import time

class CatastoGINExtension:
    """
    Estensione per ricerca fuzzy utilizzando indici GIN e pg_trgm.
    """
    
    def __init__(self, db_manager):
        """
        Inizializza l'estensione con un'istanza di CatastoDBManager.
        
        Args:
            db_manager: Istanza di CatastoDBManager
        """
        self.db_manager = db_manager
        self.logger = db_manager.logger if hasattr(db_manager, 'logger') else logging.getLogger(__name__)
        
        # Verifica che gli indici GIN siano disponibili
        self._verify_gin_indices()
        
    def _verify_gin_indices(self) -> bool:
        """Verifica che gli indici GIN siano presenti nel database."""
        try:
            query = """
            SELECT COUNT(*) as gin_count
            FROM pg_indexes 
            WHERE schemaname = %s 
              AND indexname LIKE %s
            """
            
            # Uso il metodo dell'API esistente
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (self.db_manager.schema, '%_trgm%'))
                    result = cur.fetchone()
                    gin_count = result['gin_count'] if result else 0
                    
                    if gin_count >= 4:  # Ci aspettiamo almeno 4 indici
                        self.logger.info(f"Estensione GIN inizializzata: {gin_count} indici trovati")
                        return True
                    else:
                        self.logger.warning(f"Solo {gin_count} indici GIN trovati. Funzionalità limitata.")
                        return False
            finally:
                self.db_manager._release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Errore verifica indici GIN: {e}")
            return False
    
    def set_similarity_threshold(self, threshold: float) -> bool:
        """
        Imposta la soglia di similarità per la sessione.
        
        Args:
            threshold: Valore tra 0.0 e 1.0
            
        Returns:
            True se l'impostazione è riuscita
        """
        if not 0.0 <= threshold <= 1.0:
            self.logger.error(f"Soglia non valida: {threshold}. Deve essere tra 0.0 e 1.0")
            return False
            
        try:
            query = "SET pg_trgm.similarity_threshold = %s"
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(query, (threshold,))
                    conn.commit()
                    self.logger.debug(f"Soglia similarità impostata a {threshold}")
                    return True
            finally:
                self.db_manager._release_connection(conn)
            
        except Exception as e:
            self.logger.error(f"Errore impostazione soglia: {e}")
            return False
    
    def search_possessori_fuzzy(self, 
                              query_text: str, 
                              similarity_threshold: float = 0.3,
                              include_comune: bool = True,
                              limit: int = 50) -> List[Dict[str, Any]]:
        """
        Ricerca fuzzy di possessori utilizzando indici GIN.
        """
        if not query_text or len(query_text.strip()) < 2:
            self.logger.warning("Testo di ricerca troppo breve")
            return []
            
        query_text = query_text.strip()
        
        try:
            # Imposta soglia per questa ricerca
            self.set_similarity_threshold(similarity_threshold)
            
            # Query ottimizzata che sfrutta gli indici GIN
            if include_comune:
                query = """
                SELECT 
                    p.id,
                    p.nome_completo,
                    p.cognome_nome,
                    p.paternita,
                    c.nome as comune_nome,
                    GREATEST(
                        similarity(p.nome_completo, %s),
                        COALESCE(similarity(p.cognome_nome, %s), 0.0),
                        COALESCE(similarity(p.paternita, %s), 0.0)
                    ) as similarity_score,
                    (SELECT COUNT(*) FROM partita_possessore pp WHERE pp.possessore_id = p.id) as num_partite
                FROM possessore p
                LEFT JOIN comune c ON p.comune_id = c.id
                WHERE 
                    p.nome_completo %% %s OR 
                    p.cognome_nome %% %s OR 
                    (p.paternita IS NOT NULL AND p.paternita %% %s)
                ORDER BY similarity_score DESC, p.nome_completo
                LIMIT %s
                """
                params = (query_text, query_text, query_text,  # per GREATEST
                         query_text, query_text, query_text,   # per WHERE
                         limit)
            else:
                query = """
                SELECT 
                    p.id,
                    p.nome_completo,
                    p.cognome_nome,
                    p.paternita,
                    GREATEST(
                        similarity(p.nome_completo, %s),
                        COALESCE(similarity(p.cognome_nome, %s), 0.0),
                        COALESCE(similarity(p.paternita, %s), 0.0)
                    ) as similarity_score
                FROM possessore p
                WHERE 
                    p.nome_completo %% %s OR 
                    p.cognome_nome %% %s OR 
                    (p.paternita IS NOT NULL AND p.paternita %% %s)
                ORDER BY similarity_score DESC, p.nome_completo
                LIMIT %s
                """
                params = (query_text, query_text, query_text,  # per GREATEST
                         query_text, query_text, query_text,   # per WHERE
                         limit)
            
            start_time = time.time()
            
            # Usa l'API del CatastoDBManager
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, params)
                    results_raw = cur.fetchall()
                    results = [dict(row) for row in results_raw] if results_raw else []
                    
                    # Filtra per soglia di similarità
                    filtered_results = [
                        r for r in results 
                        if r.get('similarity_score', 0) >= similarity_threshold
                    ]
                    
                    execution_time = time.time() - start_time
                    self.logger.info(f"Ricerca possessori completata: {len(filtered_results)}/{len(results)} "
                                   f"risultati in {execution_time:.3f}s per '{query_text}'")
                    
                    return filtered_results
            finally:
                self.db_manager._release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Errore ricerca fuzzy possessori: {e}")
            return []
    
    def search_localita_fuzzy(self, 
                            query_text: str, 
                            similarity_threshold: float = 0.4,
                            limit: int = 30) -> List[Dict[str, Any]]:
        """
        Ricerca fuzzy di località utilizzando indici GIN.
        """
        if not query_text or len(query_text.strip()) < 2:
            return []
            
        query_text = query_text.strip()
        
        try:
            self.set_similarity_threshold(similarity_threshold)
            
            query = """
            SELECT 
                l.id,
                l.nome,
                l.tipo,
                l.civico,
                c.nome as comune_nome,
                similarity(l.nome, %s) as similarity_score
            FROM localita l
            LEFT JOIN comune c ON l.comune_id = c.id
            WHERE l.nome %% %s
              AND similarity(l.nome, %s) >= %s
            ORDER BY similarity_score DESC, l.nome
            LIMIT %s
            """
            
            params = (query_text, query_text, query_text, similarity_threshold, limit)
            
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, params)
                    results_raw = cur.fetchall()
                    results = [dict(row) for row in results_raw] if results_raw else []
                    
                    self.logger.info(f"Ricerca località completata: {len(results)} risultati")
                    return results
            finally:
                self.db_manager._release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Errore ricerca fuzzy località: {e}")
            return []
    
    def search_combined_fuzzy(self, 
                            query_text: str,
                            search_possessori: bool = True,
                            search_localita: bool = True,
                            similarity_threshold: float = 0.3,
                            max_possessori: int = 20,
                            max_localita: int = 10) -> Dict[str, List[Dict]]:
        """
        Ricerca combinata in possessori e località.
        """
        results = {
            'possessori': [],
            'localita': [],
            'query_text': query_text,
            'similarity_threshold': similarity_threshold
        }
        
        start_time = time.time()
        
        if search_possessori:
            results['possessori'] = self.search_possessori_fuzzy(
                query_text, 
                similarity_threshold, 
                include_comune=True,
                limit=max_possessori
            )
            
        if search_localita:
            results['localita'] = self.search_localita_fuzzy(
                query_text, 
                similarity_threshold, 
                limit=max_localita
            )
        
        total_results = len(results['possessori']) + len(results['localita'])
        execution_time = time.time() - start_time
        
        self.logger.info(f"Ricerca combinata completata: {total_results} risultati "
                        f"in {execution_time:.3f}s")
        
        results['execution_time'] = execution_time
        results['total_results'] = total_results
        
        return results
    
    def get_gin_indices_info(self) -> List[Dict[str, Any]]:
        """
        Ottiene informazioni dettagliate sugli indici GIN.
        """
        try:
            query = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size,
                pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size
            FROM pg_indexes 
            WHERE schemaname = %s 
              AND indexname LIKE %s
            ORDER BY tablename, indexname
            """
            
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (self.db_manager.schema, '%_trgm%'))
                    results_raw = cur.fetchall()
                    return [dict(row) for row in results_raw] if results_raw else []
            finally:
                self.db_manager._release_connection(conn)
            
        except Exception as e:
            self.logger.error(f"Errore recupero info indici: {e}")
            return []
    
    def explain_search_query(self, 
                           query_text: str, 
                           search_type: str = 'possessori') -> Optional[str]:
        """
        Mostra il piano di esecuzione per una query di ricerca (debugging).
        """
        try:
            if search_type == 'possessori':
                explain_query = """
                EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
                SELECT p.nome_completo, similarity(p.nome_completo, %s) as sim
                FROM possessore p
                WHERE p.nome_completo %% %s
                ORDER BY sim DESC
                LIMIT 10
                """
            else:  # localita
                explain_query = """
                EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
                SELECT l.nome, similarity(l.nome, %s) as sim
                FROM localita l
                WHERE l.nome %% %s
                ORDER BY sim DESC
                LIMIT 10
                """
            
            conn = self.db_manager._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(explain_query, (query_text, query_text))
                    plan_rows = cur.fetchall()
                    # Estrae il testo del piano
                    plan_text = "\n".join([str(row[0]) for row in plan_rows])
                    return plan_text
            finally:
                self.db_manager._release_connection(conn)
            
        except Exception as e:
            self.logger.error(f"Errore explain query: {e}")
            return None

# ========================================================================
# FUNZIONE FACTORY
# ========================================================================

def extend_db_manager_with_gin(db_manager):
    """
    Estende un'istanza di CatastoDBManager con funzionalità GIN.
    """
    return CatastoGINExtension(db_manager)

# ========================================================================
# UTILITY FUNCTIONS
# ========================================================================

def format_search_results(results: Dict[str, Any]) -> str:
    """
    Formatta i risultati di ricerca per display.
    """
    output = []
    output.append(f"=== RISULTATI RICERCA: '{results.get('query_text', '')}' ===")
    output.append(f"Soglia similarità: {results.get('similarity_threshold', 0)}")
    output.append(f"Tempo esecuzione: {results.get('execution_time', 0):.3f}s")
    output.append(f"Totale risultati: {results.get('total_results', 0)}")
    output.append("")
    
    # Possessori
    possessori = results.get('possessori', [])
    if possessori:
        output.append(f"POSSESSORI ({len(possessori)}):")
        for p in possessori[:10]:  # Mostra solo i primi 10
            comune = f" ({p.get('comune_nome', 'N/A')})" if p.get('comune_nome') else ""
            output.append(f"  - {p.get('nome_completo', '')}{comune} "
                         f"[Sim: {p.get('similarity_score', 0):.3f}]")
        if len(possessori) > 10:
            output.append(f"  ... e altri {len(possessori) - 10} risultati")
        output.append("")
    
    # Località
    localita = results.get('localita', [])
    if localita:
        output.append(f"LOCALITÀ ({len(localita)}):")
        for l in localita:
            civico = f" {l.get('civico', '')}" if l.get('civico') else ""
            comune = f" ({l.get('comune_nome', 'N/A')})" if l.get('comune_nome') else ""
            output.append(f"  - {l.get('nome', '')}{civico} [{l.get('tipo', '')}]{comune} "
                         f"[Sim: {l.get('similarity_score', 0):.3f}]")
        output.append("")
    
    return "\n".join(output)

# ========================================================================
# AGGIUNTA RICERCA VARIAZIONI AL WIDGET ESISTENTE
# ========================================================================

# OPZIONE 1: Aggiungi queste funzioni al tuo catasto_gin_extension.py esistente

def search_variazioni_fuzzy(self, query_text: str, similarity_threshold: float = 0.3, max_results: int = 50):
    """
    Ricerca fuzzy nelle variazioni per tipo, numero_riferimento e nominativo_riferimento.
    """
    if not query_text or len(query_text) < 2:
        return []
    
    try:
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Query per ricerca fuzzy nelle variazioni
                query = """
                SELECT DISTINCT
                    v.id,
                    v.tipo,
                    v.data_variazione,
                    v.numero_riferimento,
                    v.nominativo_riferimento,
                    po.numero_partita as origine_numero,
                    co.nome as origine_comune,
                    pd.numero_partita as destinazione_numero,
                    cd.nome as destinazione_comune,
                    ct.tipo as tipo_contratto,
                    ct.data_contratto,
                    ct.notaio,
                    
                    -- Calcolo similarità su più campi
                    GREATEST(
                        COALESCE(similarity(v.tipo, %s), 0),
                        COALESCE(similarity(COALESCE(v.numero_riferimento, ''), %s), 0),
                        COALESCE(similarity(COALESCE(v.nominativo_riferimento, ''), %s), 0),
                        COALESCE(similarity(COALESCE(ct.notaio, ''), %s), 0)
                    ) as similarity_score
                    
                FROM variazione v
                LEFT JOIN partita po ON v.partita_origine_id = po.id
                LEFT JOIN comune co ON po.comune_id = co.id
                LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
                LEFT JOIN comune cd ON pd.comune_id = cd.id
                LEFT JOIN contratto ct ON ct.variazione_id = v.id
                
                WHERE (
                    similarity(v.tipo, %s) > %s OR
                    similarity(COALESCE(v.numero_riferimento, ''), %s) > %s OR
                    similarity(COALESCE(v.nominativo_riferimento, ''), %s) > %s OR
                    similarity(COALESCE(ct.notaio, ''), %s) > %s
                )
                
                ORDER BY similarity_score DESC, v.data_variazione DESC
                LIMIT %s;
                """
                
                # Parametri per la query
                params = (
                    query_text, query_text, query_text, query_text,  # Per GREATEST
                    query_text, similarity_threshold,                # tipo
                    query_text, similarity_threshold,                # numero_riferimento  
                    query_text, similarity_threshold,                # nominativo_riferimento
                    query_text, similarity_threshold,                # notaio
                    max_results                                      # limite
                )
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                # Converte in lista di dizionari e formatta
                variazioni = []
                for row in results:
                    variazione = dict(row)
                    
                    # Aggiungi campi formattati per visualizzazione
                    variazione['nome_completo'] = f"{variazione['tipo']} - {variazione.get('nominativo_riferimento', 'N/A')}"
                    variazione['descrizione'] = self._format_variazione_description(variazione)
                    variazione['similarity'] = variazione['similarity_score']  # Alias per compatibilità
                    
                    variazioni.append(variazione)
                
                return variazioni
                
    except Exception as e:
        self.logger.error(f"Errore ricerca fuzzy variazioni: {e}")
        return []

def _format_variazione_description(self, variazione):
    """Formatta la descrizione della variazione per la visualizzazione."""
    desc_parts = []
    
    # Tipo e data
    desc_parts.append(f"{variazione['tipo']} del {variazione['data_variazione']}")
    
    # Partite coinvolte
    if variazione.get('origine_numero') and variazione.get('origine_comune'):
        desc_parts.append(f"da P.{variazione['origine_numero']} ({variazione['origine_comune']})")
    
    if variazione.get('destinazione_numero') and variazione.get('destinazione_comune'):
        desc_parts.append(f"a P.{variazione['destinazione_numero']} ({variazione['destinazione_comune']})")
    
    # Contratto
    if variazione.get('tipo_contratto'):
        contratto_info = f"Contratto: {variazione['tipo_contratto']}"
        if variazione.get('notaio'):
            contratto_info += f" - {variazione['notaio']}"
        desc_parts.append(contratto_info)
    
    return " | ".join(desc_parts)

def search_combined_fuzzy_with_variazioni(self, query_text, search_possessori=True, 
                                         search_localita=True, search_variazioni=True,
                                         similarity_threshold=0.3, max_possessori=50, 
                                         max_localita=20, max_variazioni=30):
    """
    Ricerca fuzzy combinata che include possessori, località e variazioni.
    """
    import time
    start_time = time.time()
    
    results = {
        'query_text': query_text,
        'similarity_threshold': similarity_threshold,
        'possessori': [],
        'localita': [],
        'variazioni': [],
        'execution_time': 0
    }
    
    try:
        # Ricerca possessori (se richiesta)
        if search_possessori and hasattr(self, 'search_possessori_fuzzy'):
            results['possessori'] = self.search_possessori_fuzzy(
                query_text, similarity_threshold, max_possessori
            )
        
        # Ricerca località (se richiesta)  
        if search_localita and hasattr(self, 'search_localita_fuzzy'):
            results['localita'] = self.search_localita_fuzzy(
                query_text, similarity_threshold, max_localita
            )
        
        # Ricerca variazioni (se richiesta)
        if search_variazioni:
            results['variazioni'] = self.search_variazioni_fuzzy(
                query_text, similarity_threshold, max_variazioni
            )
        
        results['execution_time'] = time.time() - start_time
        return results
        
    except Exception as e:
        self.logger.error(f"Errore ricerca combinata: {e}")
        results['execution_time'] = time.time() - start_time
        return results
