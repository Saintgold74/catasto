# core/services/reporting_service.py
import logging
from datetime import datetime

logger = logging.getLogger("CatastoAppLogger.ReportingService")

def genera_certificato_storico_partita_service(db_manager, partita_id: int):
    """
    Genera i dati per un certificato storico di una partita.
    Questa funzione recupera i dati; la formattazione del certificato (testo, PDF, ecc.)
    sarà gestita dall'UI o da un altro modulo di utility.
    """
    logger.info(f"Generazione dati per certificato storico Partita ID: {partita_id}")

    cert_data = {}

    # 1. Dati Partita
    partita_query = """
        SELECT p.id, p.numero_partita, p.data_creazione, p.data_soppressione, p.tipo_partita, p.note as note_partita,
               c.nome as nome_comune, c.codice_catastale as codice_comune,
               s.nome_sezione, s.codice_sezione
        FROM partite p
        JOIN comuni c ON p.comune_id = c.id
        JOIN sezioni s ON p.sezione_id = s.id
        WHERE p.id = %s
    """
    try:
        partita_info = db_manager.execute_query(partita_query, (partita_id,), fetch_one=True)
        if not partita_info:
            logger.error(f"Partita ID {partita_id} non trovata per certificato.")
            raise ValueError(f"Partita ID {partita_id} non trovata.")
        cert_data['partita'] = dict(partita_info) # Converte da DictRow a dict standard
    except Exception as e:
        logger.error(f"Errore recupero dati partita per certificato (ID: {partita_id}): {e}", exc_info=True)
        raise

    # 2. Intestazioni Storiche (Possessori)
    intestazioni_query = """
        SELECT pos.cognome_denominazione, pos.nome, pos.codice_fiscale_partita_iva,
               q.nome_qualifica, t.nome_titolo, i.quota_diritto,
               i.data_inizio_validita, i.data_fine_validita, i.note as note_intestazione
        FROM intestazioni i
        JOIN possessori pos ON i.possessore_id = pos.id
        JOIN qualifiche_possessore q ON i.qualifica_id = q.id
        JOIN titoli_diritti t ON i.titolo_id = t.id
        WHERE i.partita_id = %s
        ORDER BY i.data_inizio_validita DESC, i.data_fine_validita ASC NULLS LAST, pos.cognome_denominazione
    """
    try:
        intestazioni_raw = db_manager.execute_query(intestazioni_query, (partita_id,), fetch_all=True)
        cert_data['intestazioni'] = [dict(row) for row in intestazioni_raw] if intestazioni_raw else []
    except Exception as e:
        logger.error(f"Errore recupero intestazioni per certificato (Partita ID: {partita_id}): {e}", exc_info=True)
        cert_data['intestazioni'] = [] # Continua con dati parziali se possibile

    # 3. Immobili Storici associati alla partita
    immobili_query = """
        SELECT foglio, numero_particella, subalterno, categoria_catastale, classe, consistenza, rendita,
               data_inizio_validita, data_fine_validita, indirizzo_manuale, note as note_immobile
        FROM immobili
        WHERE partita_id = %s
        ORDER BY data_inizio_validita DESC, foglio, numero_particella, subalterno
    """
    try:
        immobili_raw = db_manager.execute_query(immobili_query, (partita_id,), fetch_all=True)
        cert_data['immobili'] = [dict(row) for row in immobili_raw] if immobili_raw else []
    except Exception as e:
        logger.error(f"Errore recupero immobili per certificato (Partita ID: {partita_id}): {e}", exc_info=True)
        cert_data['immobili'] = []

    # 4. Volture che hanno interessato la partita (sia come precedente che attuale)
    volture_query = """
        SELECT v.tipo_voltura, v.data_registrazione, v.numero_protocollo, v.anno_protocollo,
               d.tipo_documento as tipo_documento_voltura, d.data_documento as data_documento_voltura,
               d.descrizione as descrizione_documento_voltura,
               pp.numero_partita as n_partita_precedente,
               pa.numero_partita as n_partita_successiva,
               v.note as note_voltura
        FROM volture v
        JOIN documenti d ON v.documento_id = d.id
        LEFT JOIN partite pp ON v.partita_precedente_id = pp.id
        LEFT JOIN partite pa ON v.partita_attuale_id = pa.id
        WHERE v.partita_precedente_id = %s OR v.partita_attuale_id = %s
        ORDER BY v.data_registrazione DESC
    """
    try:
        volture_raw = db_manager.execute_query(volture_query, (partita_id, partita_id), fetch_all=True)
        cert_data['volture'] = [dict(row) for row in volture_raw] if volture_raw else []
    except Exception as e:
        logger.error(f"Errore recupero volture per certificato (Partita ID: {partita_id}): {e}", exc_info=True)
        cert_data['volture'] = []
        
    # 5. Documenti associati direttamente alla partita (tramite documenti_partite)
    documenti_link_query = """
        SELECT d.tipo_documento, d.data_documento, d.descrizione as descrizione_documento,
               d.numero_protocollo_esterno, d.ente_emittente,
               dp.rilevanza, dp.note as note_collegamento
        FROM documenti d
        JOIN documenti_partite dp ON d.id = dp.documento_id
        WHERE dp.partita_id = %s
        ORDER BY d.data_documento DESC
    """
    try:
        documenti_link_raw = db_manager.execute_query(documenti_link_query, (partita_id,), fetch_all=True)
        cert_data['documenti_collegati'] = [dict(row) for row in documenti_link_raw] if documenti_link_raw else []
    except Exception as e:
        logger.error(f"Errore recupero documenti collegati per certificato (Partita ID: {partita_id}): {e}", exc_info=True)
        cert_data['documenti_collegati'] = []

    cert_data['data_generazione_certificato'] = datetime.now()
    logger.info(f"Dati per certificato storico Partita ID: {partita_id} generati.")
    return cert_data

# Potrebbero esserci altri tipi di report, ciascuno con la sua funzione di servizio
# per raccogliere i dati necessari.