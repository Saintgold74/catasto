# Progetto Archivio Catastale Storico - Archivio di Stato di Savona

## Panoramica del Progetto

Questo progetto mira a sviluppare un sistema completo per la creazione, gestione e consultazione di un archivio digitale dei dati catastali storici per l'Archivio di Stato di Savona. Il sistema è basato su un database PostgreSQL e un'applicazione Python per l'interazione e la gestione dei dati.

L'obiettivo finale è fornire un'applicazione desktop robusta e intuitiva, installabile su più postazioni di lavoro e connessa a un server database centrale. Opzionalmente, si valuterà l'implementazione di un'interfaccia web.

**Copyright e Licenza:**
Il software è sviluppato da Marco Santoro, che ne detiene il copyright. Sarà concesso in comodato d'uso gratuito all'Archivio di Stato di Savona.

## Componenti Chiave del Sistema

### 1. Database PostgreSQL (`catasto_storico`)

Il cuore del sistema è un database PostgreSQL progettato per immagazzinare in modo efficiente e strutturato i complessi dati catastali storici.

* **Schema Dedicato (`catasto`):** Per una migliore organizzazione e gestione dei permessi.
* **Struttura delle Tabelle:**
    * **Tabelle Anagrafiche:** `comune` (con PK numerica `id`), `possessore`, `localita`.
    * **Tabelle Catastali Principali:** `partita`, `immobile`.
    * **Tabelle di Relazione:** `partita_possessore`, `partita_relazione`.
    * **Tabelle di Evoluzione e Atti:** `variazione`, `contratto`.
    * **Tabelle di Supporto e Storiche:** `registro_partite`, `registro_matricole`, `consultazione`, `periodo_storico`, `nome_storico`, `documento_storico`, `documento_partita`.
    * **Tabelle Amministrative e di Sicurezza:** `utente`, `accesso_log`, `permesso`, `utente_permesso`, `audit_log`, `backup_registro`.
* **Chiavi Primarie ed Esterne:** Utilizzo di `SERIAL` per le PK e gestione rigorosa delle FK con `ON UPDATE CASCADE ON DELETE RESTRICT`.
* **Estensioni PostgreSQL Utilizzate:**
    * `uuid-ossp`: Per la potenziale generazione di identificativi unici.
    * `pg_trgm`: Per ricerche testuali avanzate e basate sulla similarità.
* **Funzionalità Avanzate del Database:**
    * **Stored Procedure e Funzioni SQL:** Un ricco insieme di routine PL/pgSQL per incapsulare la logica di business, incluse operazioni CRUD complesse, workflow di registrazione (nuove proprietà, passaggi di proprietà, frazionamenti), generazione di report testuali e calcoli specifici.
    * **Trigger:** Per l'aggiornamento automatico dei timestamp di modifica (`data_modifica`) e per il sistema di audit.
    * **Viste Materializzate:** Per ottimizzare le query di reportistica complesse (es. `mv_statistiche_comune`, `mv_immobili_per_tipologia`, `mv_partite_complete`, `mv_cronologia_variazioni`), con procedure dedicate per il loro aggiornamento.
    * **Sistema di Audit:** Tracciamento dettagliato delle modifiche (INSERT, UPDATE, DELETE) sulle tabelle principali tramite trigger e la tabella `audit_log`, integrato con la gestione utenti.
    * **Gestione Utenti e Permessi:** Tabelle dedicate per utenti, ruoli e permessi granulari, con una funzione `ha_permesso` per la verifica dei diritti.
    * **Sistema di Backup:** Funzionalità per suggerire comandi di backup/restore, registrare i backup eseguiti e generare script di automazione.
    * **Funzionalità Storiche:** Gestione di periodi storici, nomi storici di luoghi e collegamento di documenti storici digitalizzati alle partite catastali. Funzione per la ricostruzione dell'"albero genealogico" delle proprietà.
    * **Ottimizzazione:** Indici su colonne chiave per migliorare le prestazioni delle query. Procedure di manutenzione che includono `ANALYZE`.

### 2. Gestore Database Python (`catasto_db_manager.py`)

Una classe Python (`CatastoDBManager`) che funge da interfaccia tra l'applicazione e il database PostgreSQL.

* **Libreria:** Utilizza `psycopg2` per la connessione e l'interazione con PostgreSQL.
* **Funzionalità Principali:**
    * Gestione robusta della connessione, transazioni (commit/rollback).
    * Esecuzione di query SQL e chiamate a stored procedure/funzioni.
    * Recupero dei dati tramite `DictCursor` per un facile accesso ai campi per nome.
    * Integrazione con il sistema di audit del database (impostazione di variabili di sessione per `app.user_id` e `app.ip_address`).
    * Metodi specifici per ogni funzionalità del database (CRUD, report, audit, gestione utenti, backup, funzionalità storiche avanzate).
    * Utilizzo di `bcrypt` per l'hashing sicuro delle password degli utenti dell'applicazione.
    * Logging dettagliato delle operazioni e degli errori tramite il modulo `logging`.

### 3. Interfaccia Utente

* **`python_example.py` (Interfaccia a Riga di Comando - CLI):**
    * Fornisce un menu testuale completo per interagire con tutte le funzionalità del `CatastoDBManager`.
    * Strumento essenziale per test, debug e amministrazione di base del sistema.
    * Include la gestione delle sessioni utente (login/logout) e l'impostazione del contesto per l'audit.
* **`prova.py` (Bozza Interfaccia Grafica - GUI con PyQt5):**
    * Rappresenta l'inizio dello sviluppo dell'applicazione desktop.
    * Utilizza la libreria `PyQt5` per la creazione dell'interfaccia grafica.
    * Include:
        * Finestra principale con un'area di stato per connessione e utente.
        * Sistema di login utente con hashing `bcrypt` e registrazione accessi.
        * Finestra per la creazione di nuovi utenti.
        * Widget e dialoghi riutilizzabili (es. `ComuneSelectionDialog`, `ImmobiliTableWidget`, `PartitaDetailsDialog`).
        * Struttura a schede (QTabWidget) per organizzare le diverse funzionalità (Consultazione, Inserimento, Reportistica, Statistiche, Utenti).
        * Esempi di interazione con `CatastoDBManager` per popolare tabelle, eseguire ricerche e generare report.
        * Funzionalità di esportazione dati (es. partita in JSON).

## Guida all'Installazione e Uso (Schema Generale)

### Prerequisiti

1.  **PostgreSQL Server:** Installato e configurato (versione raccomandata: 13 o superiore per `DROP DATABASE ... WITH (FORCE)` e altre feature recenti).
2.  **Python:** Installato (versione raccomandata: 3.8 o superiore).
3.  **Librerie Python:**
    * `psycopg2-binary` (o `psycopg2` se si compila da sorgenti)
    * `bcrypt`
    * `PyQt5` (per l'interfaccia grafica)

    Installabili tramite pip:
    ```bash
    pip install psycopg2-binary bcrypt PyQt5
    ```

### Configurazione del Database

1.  **Creazione Utente Database (se non si usa `postgres`):** Creare un utente dedicato per l'applicazione.
2.  **Esecuzione Script SQL:** Gli script SQL forniti devono essere eseguiti nell'ordine corretto per creare e popolare il database.
    * **Ordine Suggerito:**
        1.  `01_creazione-database.sql` (eseguito come superutente, es. `postgres`)
        2.  Connettersi al database `catasto_storico`.
        3.  `02_creazione-schema-tabelle.sql`
        4.  `03_funzioni-procedure.sql`
        5.  `06_audit-system.sql` (definizione `audit_log` già in `02`)
        6.  `07_user-management.sql`
        7.  `08_advanced-reporting.sql`
        8.  `09_backup-system.sql`
        9.  `10_performance-optimization.sql`
        10. `11_advanced-cadastral-features.sql`
        11. `12_procedure_crud.sql`
        12. `13_workflow_integrati.sql`
        13. `14_report_functions.sql`
        14. `15_integration_audit_users.sql` (completa `audit_log` e `utente`)
        15. `16_advanced_search.sql`
        16. `17_funzione_ricerca_immobili.sql`
    * **Popolamento Dati (Opzionale):**
        * `04_dati-esempio_modificato.sql` per un set di dati di base.
        * `04_dati_stress_test.sql` per test di carico.
        * Usare `00_svuota_dati.sql` con cautela per ripulire i dati prima di un nuovo caricamento.
    * **Test:**
        * `05_query-test.sql` per verificare le funzionalità SQL.

### Esecuzione dell'Applicazione Python

1.  **Configurazione Connessione:** Assicurarsi che i parametri di connessione nel file `catasto_db_manager.py` (e/o in `python_example.py` / `prova.py`) siano corretti per il proprio ambiente server PostgreSQL.
2.  **CLI (`python_example.py`):**
    ```bash
    python python_example.py
    ```
3.  **GUI (`prova.py`):**
    ```bash
    python prova.py
    ```

## Sviluppi Futuri e Considerazioni

* **Completamento GUI:** Sviluppare ulteriormente l'interfaccia grafica (`prova.py`) per coprire tutte le funzionalità esposte dal `CatastoDBManager`.
* **Interfaccia Web:** Valutare l'implementazione di un'interfaccia web utilizzando framework come Django o Flask.
* **Integrazione GIS:** Se la componente geografica è rilevante, considerare l'integrazione con PostGIS.
* **Sicurezza Avanzata:** Implementare SSL/TLS per le connessioni al database e rivedere la gestione dei ruoli e permessi a livello di database per l'utente applicativo.
* **Deployment:** Definire una strategia per il deployment dell'applicazione desktop e del server database.
* **Documentazione Utente:** Creare una guida utente dettagliata per l'utilizzo dell'applicazione.

## Struttura dei File Forniti

* **`.sql` files:** Contengono la logica di definizione e manipolazione del database PostgreSQL.
    * `00_...` a `17_...`: Script per la creazione dello schema, tabelle, funzioni, viste, dati di esempio, test e funzionalità avanzate.
* **`.py` files:**
    * `catasto_db_manager.py`: Classe principale per l'interazione Python-PostgreSQL.
    * `python_example.py`: Applicazione CLI di esempio e test.
    * `prova.py`: Bozza dell'applicazione GUI con PyQt5.
* **`.txt` files:**
    * `note di testing.txt`: Appunti sullo stato dei test delle funzionalità.
    * Esempi di report generati (es. `report_possessore_...txt`, `certificato_partita_...txt`).
* **`.json` files:**
    * Esempi di esportazione dati (es. `partita_1.json`, `possessore_1.json`).

---

Questo README fornisce una visione d'insieme del progetto. Per dettagli specifici, fare riferimento al codice sorgente e ai commenti all'interno dei singoli file.