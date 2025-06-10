# ========================================================================
# ESTENSIONE GIN AMPLIATA PER SISTEMA CATASTO
# File: catasto_gin_extension_expanded.py
# ========================================================================

"""
Estensione ampliata del CatastoDBManager con supporto per ricerca fuzzy
su tutti i campi del database: immobili, variazioni, contratti e partite.

Nuove funzionalità:
- Ricerca fuzzy in natura, classificazione e consistenza degli immobili
- Ricerca fuzzy nelle variazioni (tipo, nominativo, numero riferimento)
- Ricerca fuzzy nei contratti (tipo, notaio, repertorio, note)
- Ricerca fuzzy nelle partite (numero e suffisso)
- Ricerca unificata in tutte le entità
- Verifica automatica degli indici GIN
"""

import logging
import psycopg2.extras
from typing import Dict, List, Optional, Union, Any
import json

class CatastoGINSearchExpanded:
    """Classe per ricerca fuzzy ampliata nel sistema catasto."""
    
    def __init__(self, db_manager):
        """Inizializza con un'istanza di CatastoDBManager."""
        self.db_manager = db_manager
        self.similarity_threshold = 0.3
        self.logger = logging.getLogger(__name__)
        
    def set_similarity_threshold(self, threshold: float) -> None:
        """Imposta la soglia di similarità per la ricerca fuzzy."""
        self.similarity_threshold = max(0.1, min(1.0, threshold))
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT set_limit(%s)", (self.similarity_threshold,))
        except Exception as e:
            self.logger.error(f"Errore nell'impostare la soglia di similarità: {e}")
    
    def verify_gin_indices(self) -> Dict[str, Any]:
        """Verifica la presenza degli indici GIN."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("SELECT * FROM verify_gin_indices()")
                    indices = cursor.fetchall()
                    
                    result = {
                        'indices': [dict(idx) for idx in indices],
                        'total_indices': len(indices),
                        'gin_indices': len([idx for idx in indices if idx['is_gin']]),
                        'missing_indices': [idx for idx in indices if not idx['is_gin']],
                        'status': 'OK' if all(idx['is_gin'] for idx in indices) else 'MISSING_INDICES'
                    }
                    
                    return result
                    
        except Exception as e:
            self.logger.error(f"Errore nella verifica degli indici GIN: {e}")
            return {'error': str(e), 'status': 'ERROR'}
    
    def search_immobili_fuzzy(self, query_text: str, max_results: int = 50) -> Dict[str, Any]:
        """Ricerca fuzzy negli immobili."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM search_immobili_fuzzy(%s, %s, %s)",
                        (query_text, self.similarity_threshold, max_results)
                    )
                    results = cursor.fetchall()
                    
                    return {
                        'query': query_text,
                        'total_results': len(results),
                        'similarity_threshold': self.similarity_threshold,
                        'results': [dict(row) for row in results],
                        'search_fields': list(set(row['search_field'] for row in results)),
                        'status': 'OK'
                    }
                    
        except Exception as e:
            self.logger.error(f"Errore nella ricerca fuzzy immobili: {e}")
            return {'error': str(e), 'status': 'ERROR'}
    
    def search_variazioni_fuzzy(self, query_text: str, max_results: int = 50) -> Dict[str, Any]:
        """Ricerca fuzzy nelle variazioni."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM search_variazioni_fuzzy(%s, %s, %s)",
                        (query_text, self.similarity_threshold, max_results)
                    )
                    results = cursor.fetchall()
                    
                    return {
                        'query': query_text,
                        'total_results': len(results),
                        'similarity_threshold': self.similarity_threshold,
                        'results': [dict(row) for row in results],
                        'search_fields': list(set(row['search_field'] for row in results)),
                        'status': 'OK'
                    }
                    
        except Exception as e:
            self.logger.error(f"Errore nella ricerca fuzzy variazioni: {e}")
            return {'error': str(e), 'status': 'ERROR'}
    
    def search_contratti_fuzzy(self, query_text: str, max_results: int = 50) -> Dict[str, Any]:
        """Ricerca fuzzy nei contratti."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM search_contratti_fuzzy(%s, %s, %s)",
                        (query_text, self.similarity_threshold, max_results)
                    )
                    results = cursor.fetchall()
                    
                    return {
                        'query': query_text,
                        'total_results': len(results),
                        'similarity_threshold': self.similarity_threshold,
                        'results': [dict(row) for row in results],
                        'search_fields': list(set(row['search_field'] for row in results)),
                        'status': 'OK'
                    }
                    
        except Exception as e:
            self.logger.error(f"Errore nella ricerca fuzzy contratti: {e}")
            return {'error': str(e), 'status': 'ERROR'}
    
    def search_partite_fuzzy(self, query_text: str, max_results: int = 50) -> Dict[str, Any]:
        """Ricerca fuzzy nelle partite."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM search_partite_fuzzy(%s, %s, %s)",
                        (query_text, self.similarity_threshold, max_results)
                    )
                    results = cursor.fetchall()
                    
                    return {
                        'query': query_text,
                        'total_results': len(results),
                        'similarity_threshold': self.similarity_threshold,
                        'results': [dict(row) for row in results],
                        'search_fields': list(set(row['search_field'] for row in results)),
                        'status': 'OK'
                    }
                    
        except Exception as e:
            self.logger.error(f"Errore nella ricerca fuzzy partite: {e}")
            return {'error': str(e), 'status': 'ERROR'}
    
    def search_all_entities_fuzzy(self, 
                                  query_text: str,
                                  search_possessori: bool = True,
                                  search_localita: bool = True,
                                  search_immobili: bool = True,
                                  search_variazioni: bool = True,
                                  search_contratti: bool = True,
                                  search_partite: bool = True,
                                  max_results_per_type: int = 30) -> Dict[str, Any]:
        """Ricerca fuzzy unificata in tutte le entità."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM search_all_entities_fuzzy(
                            %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        query_text, self.similarity_threshold,
                        search_possessori, search_localita, search_immobili,
                        search_variazioni, search_contratti, search_partite,
                        max_results_per_type
                    ))
                    results = cursor.fetchall()
                    
                    # Raggruppa i risultati per tipo di entità
                    grouped_results = {}
                    for row in results:
                        entity_type = row['entity_type']
                        if entity_type not in grouped_results:
                            grouped_results[entity_type] = []
                        
                        # Converti additional_info da JSON se necessario
                        additional_info = row['additional_info']
                        if isinstance(additional_info, str):
                            additional_info = json.loads(additional_info)
                        
                        grouped_results[entity_type].append({
                            'entity_id': row['entity_id'],
                            'display_text': row['display_text'],
                            'detail_text': row['detail_text'],
                            'similarity_score': float(row['similarity_score']),
                            'search_field': row['search_field'],
                            'additional_info': additional_info
                        })
                    
                    return {
                        'query': query_text,
                        'total_results': len(results),
                        'similarity_threshold': self.similarity_threshold,
                        'entity_types_found': list(grouped_results.keys()),
                        'results_by_type': grouped_results,
                        'search_settings': {
                            'search_possessori': search_possessori,
                            'search_localita': search_localita,
                            'search_immobili': search_immobili,
                            'search_variazioni': search_variazioni,
                            'search_contratti': search_contratti,
                            'search_partite': search_partite,
                            'max_results_per_type': max_results_per_type
                        },
                        'status': 'OK'
                    }
                    
        except Exception as e:
            self.logger.error(f"Errore nella ricerca fuzzy unificata: {e}")
            return {'error': str(e), 'status': 'ERROR'}
    
    def get_entity_details(self, entity_type: str, entity_id: int) -> Dict[str, Any]:
        """Ottiene i dettagli completi di un'entità specifica."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    
                    if entity_type == 'possessore':
                        cursor.execute("""
                            SELECT p.*, c.nome as comune_nome,
                                   COUNT(pp.partita_id) as num_partite
                            FROM possessore p
                            JOIN comune c ON p.comune_id = c.id
                            LEFT JOIN partita_possessore pp ON p.id = pp.possessore_id
                            WHERE p.id = %s
                            GROUP BY p.id, c.nome
                        """, (entity_id,))
                        
                    elif entity_type == 'localita':
                        cursor.execute("""
                            SELECT l.*, c.nome as comune_nome,
                                   COUNT(i.id) as num_immobili
                            FROM localita l
                            JOIN comune c ON l.comune_id = c.id
                            LEFT JOIN immobile i ON l.id = i.localita_id
                            WHERE l.id = %s
                            GROUP BY l.id, c.nome
                        """, (entity_id,))
                        
                    elif entity_type == 'immobile':
                        cursor.execute("""
                            SELECT i.*, p.numero_partita, p.suffisso_partita,
                                   l.nome as localita_nome, c.nome as comune_nome
                            FROM immobile i
                            JOIN partita p ON i.partita_id = p.id
                            JOIN localita l ON i.localita_id = l.id
                            JOIN comune c ON p.comune_id = c.id
                            WHERE i.id = %s
                        """, (entity_id,))
                        
                    elif entity_type == 'variazione':
                        cursor.execute("""
                            SELECT v.*, 
                                   po.numero_partita as partita_origine_numero,
                                   pd.numero_partita as partita_destinazione_numero,
                                   co.nome as comune_nome
                            FROM variazione v
                            JOIN partita po ON v.partita_origine_id = po.id
                            LEFT JOIN partita pd ON v.partita_destinazione_id = pd.id
                            JOIN comune co ON po.comune_id = co.id
                            WHERE v.id = %s
                        """, (entity_id,))
                        
                    elif entity_type == 'contratto':
                        cursor.execute("""
                            SELECT c.*, v.tipo as variazione_tipo,
                                   v.data_variazione, v.numero_riferimento as var_numero_riferimento
                            FROM contratto c
                            JOIN variazione v ON c.variazione_id = v.id
                            WHERE c.id = %s
                        """, (entity_id,))
                        
                    elif entity_type == 'partita':
                        cursor.execute("""
                            SELECT p.*, c.nome as comune_nome,
                                   COUNT(DISTINCT pp.possessore_id) as num_possessori,
                                   COUNT(DISTINCT i.id) as num_immobili
                            FROM partita p
                            JOIN comune c ON p.comune_id = c.id
                            LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
                            LEFT JOIN immobile i ON p.id = i.partita_id
                            WHERE p.id = %s
                            GROUP BY p.id, c.nome
                        """, (entity_id,))
                        
                    else:
                        return {'error': f'Tipo entità non supportato: {entity_type}', 'status': 'ERROR'}
                    
                    result = cursor.fetchone()
                    if result:
                        return {
                            'entity_type': entity_type,
                            'entity_id': entity_id,
                            'details': dict(result),
                            'status': 'OK'
                        }
                    else:
                        return {
                            'error': f'Entità {entity_type} con ID {entity_id} non trovata',
                            'status': 'NOT_FOUND'
                        }
                        
        except Exception as e:
            self.logger.error(f"Errore nel recupero dettagli entità: {e}")
            return {'error': str(e), 'status': 'ERROR'}

def extend_db_manager_with_gin_expanded(db_manager):
    """Estende un'istanza di CatastoDBManager con capacità di ricerca fuzzy ampliata."""
    
    if not hasattr(db_manager, 'gin_search_expanded'):
        db_manager.gin_search_expanded = CatastoGINSearchExpanded(db_manager)
        
        # Metodi di convenienza
        db_manager.search_immobili_fuzzy = db_manager.gin_search_expanded.search_immobili_fuzzy
        db_manager.search_variazioni_fuzzy = db_manager.gin_search_expanded.search_variazioni_fuzzy
        db_manager.search_contratti_fuzzy = db_manager.gin_search_expanded.search_contratti_fuzzy
        db_manager.search_partite_fuzzy = db_manager.gin_search_expanded.search_partite_fuzzy
        db_manager.search_all_entities_fuzzy = db_manager.gin_search_expanded.search_all_entities_fuzzy
        db_manager.get_entity_details = db_manager.gin_search_expanded.get_entity_details
        db_manager.verify_gin_indices = db_manager.gin_search_expanded.verify_gin_indices
        db_manager.set_similarity_threshold = db_manager.gin_search_expanded.set_similarity_threshold
        
        print("CatastoDBManager esteso con ricerca fuzzy ampliata")
        
    return db_manager

def format_search_results_expanded(results: Dict[str, Any], max_display: int = 100) -> str:
    """Formatta i risultati della ricerca fuzzy ampliata per la visualizzazione."""
    
    if results.get('status') == 'ERROR':
        return f"❌ Errore: {results.get('error', 'Errore sconosciuto')}"
    
    if results.get('total_results', 0) == 0:
        return f"🔍 Nessun risultato trovato per '{results.get('query', '')}'"
    
    output = []
    output.append(f"🔍 Ricerca: '{results['query']}'")
    output.append(f"📊 Risultati: {results['total_results']} (soglia: {results['similarity_threshold']:.2f})")
    
    if 'results_by_type' in results:
        # Risultati unificati
        for entity_type, entities in results['results_by_type'].items():
            output.append(f"\n📁 {entity_type.upper()} ({len(entities)} risultati):")
            
            for i, entity in enumerate(entities[:max_display]):
                score_bar = "█" * int(entity['similarity_score'] * 10)
                output.append(
                    f"  {i+1:2d}. {entity['display_text']} "
                    f"({entity['similarity_score']:.3f}) {score_bar}"
                )
                output.append(f"      {entity['detail_text']}")
                if entity.get('search_field'):
                    output.append(f"      Campo: {entity['search_field']}")
    
    else:
        # Risultati singoli
        search_fields = results.get('search_fields', [])
        if search_fields:
            output.append(f"📋 Campi trovati: {', '.join(search_fields)}")
        
        for i, result in enumerate(results['results'][:max_display]):
            score_bar = "█" * int(result['similarity_score'] * 10)
            output.append(
                f"  {i+1:2d}. {result.get('display_text', 'N/A')} "
                f"({result['similarity_score']:.3f}) {score_bar}"
            )
    
    if results['total_results'] > max_display:
        output.append(f"\n... e altri {results['total_results'] - max_display} risultati")
    
    return "\n".join(output)

# ========================================================================
# ESEMPIO DI UTILIZZO
# ========================================================================

if __name__ == "__main__":
    # Esempio di utilizzo (richiede un'istanza di CatastoDBManager)
    print("Estensione GIN ampliata per sistema catasto")
    print("Per utilizzare, importa e chiama extend_db_manager_with_gin_expanded(db_manager)")
    
    example_usage = """
    # Esempio di utilizzo:
    from catasto_db_manager import CatastoDBManager
    from catasto_gin_extension_expanded import extend_db_manager_with_gin_expanded
    
    # Inizializza il database manager
    db_manager = CatastoDBManager()
    
    # Estendi con ricerca fuzzy ampliata
    db_manager = extend_db_manager_with_gin_expanded(db_manager)
    
    # Verifica gli indici GIN
    indices_status = db_manager.verify_gin_indices()
    print("Stato indici:", indices_status['status'])
    
    # Ricerca unificata
    results = db_manager.search_all_entities_fuzzy(
        'terra',
        search_immobili=True,
        search_variazioni=True,
        max_results_per_type=20
    )
    
    # Visualizza risultati
    print(format_search_results_expanded(results))
    
    # Ricerca specifica negli immobili
    immobili_results = db_manager.search_immobili_fuzzy('fabbricato')
    print(format_search_results_expanded(immobili_results))
    
    # Ricerca nelle variazioni
    variazioni_results = db_manager.search_variazioni_fuzzy('vendita')
    print(format_search_results_expanded(variazioni_results))
    """
    
    print(example_usage)