Manuale Utente Dettagliato - Meridiana 1.0
Indice

    Primo Avvio e Accesso
    L'Interfaccia Principale
    La Dashboard (Home)
    Consultazione dei Dati (READ)
    Inserimento e Modifica dei Dati (CREATE & UPDATE)
    Flussi di Lavoro Complessi
    Reportistica ed Esportazioni
    Funzioni di Amministrazione (Admin)
    Configurazione Iniziale del Database (Lato Server)
        9.1: Prerequisiti
        9.2: Ordine di Esecuzione degli Script
        9.3: Esecuzione Pratica (Esempio con psql)
        9.4: Popolamento con Dati di Test (Opzionale)
        9.5: Script di Manutenzione e Cancellazione
        9.6: Creazione Utenti PostgreSQL (Opzionale)
    Appendice A: Formato File CSV

Capitolo 1: Primo Avvio e Accesso
1.1 Configurazione del Database

Al primo avvio dell'applicazione, o se la connessione al server centrale non riesce, verrà presentata la finestra di Configurazione Connessione Database. Questa operazione è fondamentale per permettere a Meridiana di comunicare con l'archivio centrale.

Procedura passo-passo:

    Selezionare il Tipo di Server:
        Remoto (Server Specifico): Questa è l'opzione standard per l'utilizzo in rete all'Archivio di Stato. Selezionandola, si abiliterà il campo per l'indirizzo del server.
        Locale (localhost): Da utilizzare solo per scopi di test o se il database è installato sullo stesso computer.

    Compilare i Parametri di Connessione:
        Indirizzo Server Host: Inserire l'indirizzo IP del server PostgreSQL. Per l'Archivio di Stato di Savona, l'indirizzo predefinito è 10.99.80.131.
        Porta Server: Lasciare il valore predefinito 5432, a meno che non sia stato comunicato un valore diverso dall'amministratore di rete.
        Nome Database: Inserire il nome del database, solitamente catasto_storico.
        Utente Database: Inserire il nome utente fornito per l'accesso al database (es. archivista_savona o postgres).
        Password Database: Inserire la password associata all'utente del database. Il campo nasconderà i caratteri digitati per sicurezza.
        Salva password: Spuntare questa casella solo se si utilizza un computer personale e sicuro. Salverà la password per non doverla reinserire ad ogni avvio. Si sconsiglia fortemente di attivarla su postazioni condivise.

    Testare la Connessione:
        Premere il pulsante "Test Connessione". Il programma tenterà di collegarsi al server con i dati inseriti.
        Se appare un messaggio di "Connessione riuscita", i parametri sono corretti.
        In caso di errore, un messaggio indicherà il problema (es. "Password errata", "Server non raggiungibile"). Verificare attentamente i dati inseriti.

    Salvare e Procedere:
        Dopo un test riuscito, premere "Salva e Connetti". Le impostazioni verranno salvate e l'applicazione procederà alla schermata di Login.

1.2 Schermata di Login

Questa schermata garantisce che solo gli utenti autorizzati possano accedere al sistema.

    Username: Inserire il proprio nome utente personale (es. m.rossi).
    Password: Inserire la propria password personale.
    Premere il pulsante "Login" o il tasto Invio per accedere.

In caso di credenziali errate, un messaggio di avviso impedirà l'accesso.
1.3 Schermata di Benvenuto

Dopo un login effettuato con successo, una schermata di benvenuto ("splash screen") apparirà per alcuni secondi. È possibile chiuderla immediatamente premendo un tasto qualsiasi o cliccando con il mouse.
Capitolo 2: L'Interfaccia Principale

L'interfaccia di Meridiana è organizzata in sezioni logiche accessibili tramite schede (tab) per rendere la navigazione semplice e intuitiva.

    Barra del Menu: In alto, fornisce accesso a funzioni globali come l'importazione di file e le impostazioni.
    Area Principale a Schede: Il corpo centrale dell'applicazione, dove si svolgono tutte le operazioni.
    Barra di Stato: In basso, mostra informazioni cruciali come lo stato della connessione al database e l'utente attualmente connesso.

Le Schede Principali

    🏠 Home / Dashboard: La schermata iniziale con statistiche rapide e scorciatoie.
    Consultazione e Modifica: Il cuore dell'archivio, dove si naviga tra Comuni, Partite e Possessori.
    🔍 Ricerca Globale: Un potente strumento per trovare qualsiasi entità nel database tramite una ricerca testuale "fuzzy" (approssimata).
    Inserimento e Gestione: Contiene i moduli per inserire nuove entità (Comuni, Partite, etc.) e per gestire flussi di lavoro complessi come le volture.
    🗄️ Esportazioni Massive: Permette di esportare elenchi completi di dati in formati come CSV ed Excel.
    Reportistica: Per generare documenti e certificati specifici (es. report di una proprietà).
    Statistiche e Viste: Fornisce viste aggregate sui dati e strumenti di manutenzione.
    Gestione Utenti (Solo Admin): Modulo per la gestione degli account utente.
    Sistema (Solo Admin): Contiene strumenti avanzati come il visualizzatore di log di audit e la gestione dei backup.

Capitolo 3: La Dashboard (Home)

La Dashboard è la prima schermata visualizzata dopo il login e serve come centro di comando.

    Ricerca Rapida: Una barra di ricerca centrale che permette di lanciare immediatamente una ricerca globale (vedi Capitolo 4.2).
    Statistiche Rapide: Quattro riquadri mostrano il conteggio totale di Comuni, Partite, Possessori e Immobili presenti nel database.
    Attività Utenti Recenti: Una tabella mostra gli ultimi eventi di accesso (login, logout) registrati nel sistema, per un rapido controllo della sicurezza.
    Azioni Rapide: Pulsanti per accedere direttamente alle funzioni più comuni, come "Registra Nuova Proprietà" o "Vai alla Reportistica".

Capitolo 4: Consultazione dei Dati (READ)

Questa sezione illustra le diverse modalità per cercare, filtrare e visualizzare le informazioni.
4.1 Navigazione per Comune (Elenco Comuni)

Questo è il metodo di consultazione principale, ideale quando si conosce il comune di appartenenza dei dati da cercare.

    Accedere alla scheda "Consultazione e Modifica". Verrà mostrato l'elenco di tutti i comuni.
    Filtrare l'elenco: Per trovare rapidamente un comune, iniziare a digitare il suo nome o la provincia nel campo di ricerca posto sopra la tabella. L'elenco si restringerà dinamicamente.
    Visualizzare i dati collegati: Fare clic destro sul comune desiderato per aprire il menu contestuale. Da qui è possibile:
        Visualizza Partite: Apre una nuova finestra con l'elenco di tutte le partite catastali di quel comune.
        Visualizza Possessori: Apre una finestra con l'elenco di tutti i possessori registrati per quel comune.
        Visualizza Località: Apre una finestra con l'elenco delle località (vie, borgate, regioni) di quel comune.
        Modifica Dati Comune: (Solo per utenti autorizzati) Apre una finestra per modificare i dati anagrafici del comune.

4.2 Ricerca Globale (Fuzzy Search)

Utilizzare la scheda "🔍 Ricerca Globale" quando non si è sicuri del comune o si desidera cercare un nominativo o un dato specifico in tutto l'archivio.

    Navigare alla scheda "🔍 Ricerca Globale".
    Inserire il testo da cercare nella barra di ricerca principale. La ricerca è "fuzzy", o approssimata. Ciò significa che troverà corrispondenze anche se il testo non è esatto (ad es. "Rossi Mario" troverà anche "Rosi Mario").
    Affinare la ricerca (opzionale):
        Usare le checkbox ("Cerca in:") per includere o escludere tipi di entità dalla ricerca (Possessori, Località, Immobili, etc.).
        Spostare lo slider della Soglia per rendere la ricerca più o meno precisa.
    Analizzare i risultati: I risultati appaiono suddivisi in schede per tipo di entità. La prima scheda, "🔍 Tutti", mostra un riepilogo misto. Le altre schede mostrano i risultati specifici per tipo di entità.

4.3 Visualizzazione e Modifica dei Dettagli

Una volta individuata una partita o un possessore di interesse, è possibile visualizzarne e modificarne i dettagli.

    Da un elenco (es. risultati di ricerca, elenco partite): Fare doppio click sulla riga di interesse.
    Apertura della finestra di dettaglio/modifica: Si aprirà una finestra dedicata (es. Dettagli/Modifica Partita o Modifica Possessore). Questa finestra è organizzata in schede per mostrare tutte le informazioni collegate.
        Scheda Dati Generali: Mostra i dati anagrafici dell'entità (es. numero e stato della partita), che possono essere modificati qui.
        Schede collegate (Possessori, Immobili, etc.): Mostrano gli elenchi delle entità collegate. Da queste schede è possibile aggiungere, modificare o rimuovere i collegamenti.

Capitolo 5: Inserimento e Modifica dei Dati (CREATE & UPDATE)
5.1 Creazione di Entità Singole

Per inserire un singolo dato non legato a un flusso complesso (es. un nuovo comune).

    Navigare alla scheda "Inserimento e Gestione".
    Selezionare la sotto-scheda corrispondente (es. "Nuovo Comune", "Nuovo Possessore").
    Compilare i campi:
        I campi contrassegnati con (*) sono obbligatori.
        Per i possessori, è possibile usare il pulsante "Genera Nome Completo" per compilare automaticamente il campo principale partendo da Cognome/Nome e Paternità.
    Premere il pulsante "Salva" o "Inserisci" per registrare il nuovo dato nel database.

5.2 Importazione Massiva da File CSV

Questa funzione è utile per caricare grandi quantità di dati in una sola operazione.

    Dal menu in alto, selezionare "File" -> "Importa Possessori da CSV..." o "Importa Partite da CSV...".
    Selezionare il Comune: Apparirà una finestra che chiede di selezionare il comune a cui i dati del file CSV verranno associati.
    Selezionare il File: Si aprirà una finestra di dialogo per scegliere il file .csv dal proprio computer.
    Analizzare il Riepilogo: Al termine dell'importazione, un report dettagliato mostrerà quali righe sono state importate con successo e quali hanno fallito, con una spiegazione per ogni errore. Questo permette di correggere il file CSV e ritentare l'importazione solo per le righe errate.

    Nota: Il formato esatto richiesto per i file CSV è descritto nell'Appendice A.

Capitolo 6: Flussi di Lavoro Complessi

Questi moduli guidano l'utente in operazioni che coinvolgono più entità contemporaneamente.
6.1 Registrazione di una Nuova Proprietà (Creazione Partita)

Questo è il flusso di lavoro standard per inserire da zero una nuova scheda catastale.

    Navigare a "Inserimento e Gestione" -> "Registrazione Proprietà".
    Dati della Partita:
        Premere "Seleziona Comune..." e scegliere il comune di appartenenza.
        Inserire il Numero Partita e l'eventuale Suffisso.
        Impostare la Data Impianto.
    Aggiungere i Possessori:
        Premere il pulsante "Aggiungi Possessore".
        Nella finestra che appare, cercare un possessore esistente o usare la scheda "Crea Nuovo" per inserirne uno.
        Dopo aver selezionato o creato il possessore, una piccola finestra chiederà di specificare il Titolo (es. "proprietà") e la Quota (es. "1/1") di possesso.
        Ripetere per tutti gli intestatari della partita.
    Aggiungere gli Immobili:
        Premere il pulsante "Aggiungi Immobile".
        Nella finestra che appare, compilare tutti i dati dell'immobile (natura, classificazione, vani, etc.).
        Per la località, premere "Seleziona/Gestisci Località..." per scegliere una località esistente in quel comune o crearne una nuova.
        Ripetere per tutti gli immobili censiti nella partita.
    Salvataggio Finale:
        Una volta inseriti tutti i dati, premere il pulsante principale "Registra Nuova Proprietà". Il sistema creerà la partita e tutti i collegamenti inseriti.

6.2 Operazioni su Partite Esistenti

Questo modulo, accessibile da "Inserimento e Gestione" -> "Operazioni Partita", permette di gestire le evoluzioni storiche di una partita.

Passo preliminare per tutte le operazioni:

    Cercare e caricare la Partita Sorgente utilizzando il campo di ricerca in cima al modulo.

6.2.1 Duplicazione di una Partita

Utile per creare una "copia" di una partita che servirà come base per una nuova situazione storica (es. un frazionamento).

    Dopo aver caricato la partita sorgente, andare alla scheda "Duplica Partita".
    Inserire il Nuovo Numero Partita e l'eventuale Nuovo Suffisso.
    Scegliere se mantenere i possessori e/o copiare gli immobili dalla partita originale a quella nuova spuntando le apposite caselle.
    Premere "Esegui Duplicazione".

6.2.2 Trasferimento di un Immobile

Sposta un singolo immobile da una partita a un'altra.

    Caricata la partita sorgente, andare alla scheda "Trasferisci Immobile".
    Selezionare l'immobile da trasferire dalla tabella "Immobili nella Partita Sorgente".
    Cercare e selezionare la Partita Destinazione dove l'immobile deve essere spostato.
    Spuntare l'opzione "Registra Variazione Catastale" se si desidera che questa operazione venga tracciata nello storico delle variazioni.
    Premere "Esegui Trasferimento Immobile".

6.2.3 Passaggio di Proprietà (Voltura)

Questo è il flusso di lavoro per registrare una variazione di intestazione (es. vendita, successione).

    Caricata la partita sorgente (quella che viene "chiusa" o modificata), andare alla scheda "Passaggio Proprietà (Voltura)".
    Dati Nuova Partita: Compilare il Numero e l'eventuale Suffisso della nuova partita che verrà creata. Il comune sarà lo stesso della partita sorgente.
    Dati dell'Atto: Specificare il Tipo di Variazione (es. Vendita), la Data Variazione, il Tipo di Atto/Contratto, la Data Atto e, se disponibili, i dati del Notaio e del Repertorio.
    Immobili da Trasferire: Decidere quali immobili devono passare dalla vecchia alla nuova partita. Di default, vengono inclusi tutti. Se necessario, togliere la spunta da "Includi TUTTI..." e selezionare manually gli immobili dalla tabella che appare.
    Nuovi Possessori: Usare il pulsante "Aggiungi Possessore..." per definire i nuovi intestatari della nuova partita, specificando per ciascuno il titolo e la quota.
    Premere "Esegui Passaggio Proprietà". Il sistema eseguirà le seguenti azioni:
        Creerà la nuova partita.
        Trasferirà gli immobili selezionati.
        Collegherà i nuovi possessori alla nuova partita.
        Registrerà la variazione, collegando la partita di origine a quella di destinazione.
        Eventualmente chiuderà la partita di origine se tutti gli immobili sono stati trasferiti.

Capitolo 7: Reportistica ed Esportazioni
7.1 Report Specifici

La scheda "Reportistica" permette di generare documenti testuali o PDF per una singola entità.

    Selezionare il tipo di report (es. Report Proprietà, Report Genealogico).
    Cercare e selezionare l'ID della partita o del possessore desiderato.
    Premere "Genera Report". Il contenuto apparirà nell'area di anteprima.
    Usare i pulsanti "Esporta TXT" o "Esporta PDF" per salvare il report generato.

7.2 Esportazioni Massive

La scheda "🗄️ Esportazioni Massive" è pensata per estrarre elenchi di dati.

    Selezionare il tipo di esportazione (es. Elenco Possessori).
    Selezionare il Comune per cui si desidera esportare i dati.
    Scegliere il formato di esportazione: CSV, XLS (Excel) o PDF.

Capitolo 8: Funzioni di Amministrazione (Admin)

Queste sezioni sono visibili e utilizzabili solo dagli utenti con ruolo di "admin".
8.1 Gestione Utenti (CREATE, UPDATE, DELETE)

    Navigare alla scheda "Gestione Utenti".
    Creare un Utente:
        Premere "Crea Nuovo Utente".
        Compilare tutti i campi e premere "Crea Utente".
    Modificare un Utente:
        Selezionare un utente dalla tabella.
        Premere "Modifica Utente" e aggiornare i dati nella finestra che appare.
    Resettare una Password:
        Selezionare un utente.
        Premere "Resetta Password" e inserire la nuova password due volte.
    Disattivare/Attivare un Utente:
        Selezionare un utente.
        Premere "Attiva/Disattiva Utente" per cambiarne lo stato. Un utente disattivato non può effettuare il login.
    Eliminare un Utente (DELETE):
        Selezionare un utente.
        Premere "Elimina Utente".
        ⚠️ Attenzione: Apparirà una finestra di conferma critica. Per procedere, è necessario digitare esattamente lo username dell'utente da eliminare. Questa operazione è irreversibile.

8.2 Sistema e Manutenzione

La scheda "Sistema" contiene strumenti per il monitoraggio e la manutenzione del database.

    Log di Audit: Permette di visualizzare, filtrare e cercare in tutti i log di modifica dei dati (chi ha fatto cosa e quando).
    Backup/Ripristino DB:
        Backup: Crea una copia di sicurezza completa del database.
        Ripristino: (AZIONE ESTREMAMENTE PERICOLOSA) Sovrascrive l'intero database con i dati di un file di backup. Usare con la massima cautela e solo dopo aver effettuato un backup recente.
    Statistiche e Viste -> Manutenzione e Ottimizzazione:
        Aggiorna Viste Materializzate: Comando per forzare l'aggiornamento delle tabelle di statistiche. Utile se i dati aggregati sembrano non aggiornati.
        Genera Suggerimenti: Esegue un'analisi del database e fornisce consigli tecnici per l'ottimizzazione.

Capitolo 9: Configurazione Iniziale del Database (Lato Server)

Questa sezione è destinata agli amministratori di database (DBA) o al personale tecnico responsabile della preparazione e manutenzione dell'istanza PostgreSQL che ospita i dati di Meridiana. Descrive la procedura corretta per creare e inizializzare il database utilizzando gli script SQL forniti.
9.1 Prerequisiti

    Accesso a un server PostgreSQL (versione 12 o superiore raccomandata).
    Un utente PostgreSQL con privilegi di CREATEDB o un superuser (come postgres).
    Uno strumento per eseguire gli script SQL, come psql (da riga di comando) o pgAdmin.
    Tutti gli script SQL forniti, disponibili in una cartella sul server o sulla macchina da cui si lancia la configurazione.

9.2 Ordine di Esecuzione degli Script

Per una corretta inizializzazione del database da zero, è fondamentale eseguire gli script SQL nel seguente ordine. Un'esecuzione in ordine errato causerà errori a causa delle dipendenze tra tabelle, funzioni e viste.

    01_creazione-database.sql
        Scopo: Crea il database vuoto catasto_storico con le impostazioni di localizzazione italiane (it_IT.UTF-8). Deve essere eseguito connessi a un database di manutenzione come postgres.

    02_creazione-schema-tabelle.sql
        Scopo: Eseguito dopo essersi connessi al nuovo database catasto_storico, questo script crea lo schema catasto, installa le estensioni necessarie (pg_trgm, uuid-ossp) e definisce la struttura di tutte le tabelle principali (comune, partita, possessore, ecc.), le loro relazioni e gli indici di base.

    03_funzioni-procedure_def.sql
        Scopo: Crea le funzioni e le procedure di base necessarie al funzionamento dell'applicazione, come update_modified_column() e le viste principali (v_partite_complete).

    07_user-management.sql e 19_creazione_tabella_sessioni.sql
        Scopo: Creano le tabelle utente, permesso e sessioni_accesso, fondamentali per la gestione degli utenti, dei ruoli e per il tracciamento delle sessioni di login/logout.

    18_funzioni_trigger_audit.sql
        Scopo: Crea la funzione trigger generica log_audit_trigger_function() e la applica a tutte le tabelle dati. Questo passo è cruciale per garantire che ogni modifica (INSERT, UPDATE, DELETE) venga registrata nella tabella audit_log.

    15_integration_audit_users.sql
        Scopo: Completa l'integrazione tra il sistema di audit e quello degli utenti, creando la chiave esterna (Foreign Key) tra audit_log.app_user_id e utente.id. Questo assicura che le azioni registrate siano correttamente collegate all'utente applicativo che le ha eseguite.

    Script di Funzionalità Avanzate (eseguire in questo ordine):
        11_advanced-cadastral-features.sql: Aggiunge la gestione dei periodi storici e dei documenti.
        12_procedure_crud.sql: Aggiunge procedure CRUD specifiche.
        16_advanced_search.sql e 17_funzione_ricerca_immobili.sql: Implementano le funzioni di ricerca avanzata.
        13_workflow_integrati.sql: Crea le procedure per i flussi di lavoro complessi come la voltura.
        14_report_functions.sql: Crea le funzioni per la generazione dei report.
        08_advanced-reporting.sql: Crea le viste materializzate per le statistiche.
        10_performance-optimization.sql: Crea funzioni di utilità per la manutenzione.
        09_backup-system.sql: Crea la tabella e le funzioni per il log dei backup.

    07a_bootstrap_admin.sql
        Scopo: Passo finale e fondamentale. Inserisce l'utente admin di default nel sistema. Senza questo utente, nessuno potrà effettuare il primo accesso all'applicazione.

            ⚠️ ATTENZIONE: PASSWORD DI DEFAULT

            La password preimpostata per l'utente admin è pippo.

            È obbligatorio che l'amministratore cambi questa password immediatamente al primo accesso tramite l'interfaccia di gestione utenti. Lo script 07a_bootstrap_admin.sql contiene un hash bcrypt di esempio. Per generare l'hash corretto per la password pippo, è possibile usare uno script Python con la libreria bcrypt.

9.3 Esecuzione Pratica (Esempio con psql)

Il metodo raccomandato per eseguire gli script è utilizzare l'utility a riga di comando psql.

    Creazione del Database (Script 01):
    Bash

# Connesso come superuser al database di default 'postgres'
psql -U postgres -d postgres -f /percorso/completo/sql_scripts/01_creazione-database.sql

Esecuzione di tutti gli altri script:
Una volta creato il database catasto_storico, connettersi ad esso per eseguire tutti gli script successivi, nell'ordine specificato al punto 9.2.
Bash

    # Connesso al nuovo database 'catasto_storico'
    psql -U postgres -d catasto_storico -f /percorso/completo/sql_scripts/02_creazione-schema-tabelle.sql
    psql -U postgres -d catasto_storico -f /percorso/completo/sql_scripts/03_funzioni-procedure_def.sql
    # ... e così via per tutti gli altri script fino a 07a_bootstrap_admin.sql

9.4 Popolamento con Dati di Test (Opzionale)

Per scopi di formazione, test o sviluppo, è possibile popolare il database con un set di dati di esempio.

    Nota: Non eseguire questi script su un database di produzione che contiene già dati reali, a meno che non si desideri aggiungere questi dati specifici.

    04_dati-esempio_modificato.sql: Inserisce un piccolo set di dati coerenti e utili per testare le funzionalità di base.
    04b_dati_test_realistici.sql: Inserisce dati più vari e realistici.
    04_dati_stress_test.sql: Contiene una procedura per generare una grande quantità di dati casuali, utile per testare le performance del sistema sotto carico.

9.5 Script di Manutenzione e Cancellazione

Questi script eseguono operazioni distruttive e devono essere usati con la massima cautela.

    00_svuota_dati.sql
        Scopo: Cancella TUTTI I DATI da tutte le tabelle principali del catasto.
        Utilizzo: Da usare per ripulire un ambiente di test prima di importare un nuovo set di dati.
        ⚠️ ATTENZIONE: OPERAZIONE IRREVERSIBILE. La struttura delle tabelle viene mantenuta, ma i dati vengono persi per sempre.

    drop_db.sql
        Scopo: Cancella INTERAMENTE il database catasto_storico, inclusa la sua struttura e tutti i dati.
        Utilizzo: Da usare solo se si vuole rimuovere completamente l'installazione di Meridiana dal server PostgreSQL.
        ⚠️ ATTENZIONE: OPERAZIONE ESTREMAMENTE DISTRUTTIVA E IRREVERSIBILE. Per eseguirla, è necessario essere connessi a un altro database (es. postgres), come mostrato nel file di esempio script x cancellare db1.txt.

9.6 Creazione Utenti PostgreSQL (Opzionale)

L'applicazione Meridiana si connette al database utilizzando un utente PostgreSQL (es. postgres). Per una maggiore sicurezza e tracciabilità, è buona norma creare utenti PostgreSQL dedicati per i diversi operatori o per l'applicazione stessa, invece di usare l'utente postgres per tutto.

    Distinzione importante: Un Utente PostgreSQL è un account del server di database, con permessi per connettersi e manipolare i dati. Un Utente Meridiana è un account dell'applicazione, gestito tramite l'interfaccia del software (vedi cap. 8.1), che definisce i ruoli funzionali (admin, archivista, consultatore).

Di seguito, la procedura per creare un nuovo utente PostgreSQL e assegnargli i permessi necessari per usare Meridiana.
Procedura passo-passo:

    Connettersi al Server: Connettersi al database catasto_storico (o postgres) con un utente superuser (come postgres).

    Creare il Ruolo/Utente: Eseguire il seguente comando SQL per creare un nuovo utente con capacità di login e una password sicura. Sostituire <nome_utente_db> e <password_sicura> con i valori desiderati.
    SQL

CREATE ROLE <nome_utente_db> WITH LOGIN PASSWORD '<password_sicura>';

Esempio: CREATE ROLE archivista_sv WITH LOGIN PASSWORD 'PasswordMoltoSicura123!';

Assegnare i Permessi Essenziali: Un nuovo utente, per default, non può fare nulla. È necessario assegnargli i permessi minimi per operare sul database e sullo schema catasto.
SQL

-- Permette all'utente di connettersi al database specifico
GRANT CONNECT ON DATABASE catasto_storico TO <nome_utente_db>;

-- Permette all'utente di "vedere" e usare lo schema 'catasto'
GRANT USAGE ON SCHEMA catasto TO <nome_utente_db>;

Assegnare i Permessi sulle Tabelle: Per permettere all'applicazione di leggere e scrivere dati, assegnare i permessi sulle tabelle.
SQL

-- Assegna i permessi di lettura, scrittura, modifica e cancellazione su TUTTE le tabelle attuali dello schema
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA catasto TO <nome_utente_db>;

Assegnare i Permessi sulle Sequenze: Questo passo è fondamentale e spesso dimenticato. Senza questo permesso, l'utente non potrà inserire nuovi record in tabelle che usano SERIAL o IDENTITY per le chiavi primarie (tutte le nostre tabelle principali).
SQL

-- Assegna i permessi di utilizzo su TUTTE le sequenze (per gli ID automatici)
GRANT USAGE ON ALL SEQUENCES IN SCHEMA catasto TO <nome_utente_db>;

(Consigliato) Impostare Permessi di Default per Oggetti Futuri: Per evitare di dover riassegnare i permessi ogni volta che si crea una nuova tabella o vista, è possibile impostare dei permessi di default.
SQL

    -- Per le tabelle che verranno create IN FUTURO da questo ruolo o da altri
    ALTER DEFAULT PRIVILEGES IN SCHEMA catasto
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO <nome_utente_db>;

    -- Per le sequenze future
    ALTER DEFAULT PRIVILEGES IN SCHEMA catasto
    GRANT USAGE ON SEQUENCES TO <nome_utente_db>;

Una volta eseguiti questi comandi, il nuovo utente PostgreSQL (<nome_utente_db>) sarà pronto per essere usato nel file di configurazione dell'applicazione Meridiana (vedi Capitolo 1.1).
Capitolo 10: Appendice A: Formato File CSV

Per l'importazione massiva, i file CSV devono rispettare le seguenti specifiche.

    Delimitatore: Usare il punto e virgola (;).
    Encoding: UTF-8.
    Intestazioni: La prima riga del file deve contenere i nomi delle colonne.

Formato per Possessori (importa_possessori.csv)
Intestazione (Obbligatoria)	Descrizione	Esempio
cognome_nome	Cognome e nome del possessore.	Rossi Mario
nome_completo	Il nome completo come deve apparire nell'archivio.	Rossi Mario fu Giovanni
paternita (Opzionale)	La paternità (es. fu, di, del).	fu Giovanni

Esempio di file:
Snippet di codice

cognome_nome;paternita;nome_completo
Rossi Mario;fu Giovanni;Rossi Mario fu Giovanni
Bianchi Giuseppe;;Bianchi Giuseppe

Formato per Partite (importa_partite.csv)
Intestazione (Obbligatoria)	Descrizione	Esempio
numero_partita	Il numero intero della partita.	1052
data_impianto	La data di creazione in formato YYYY-MM-DD.	1985-07-22
stato	attiva o inattiva.	attiva
tipo	principale o secondaria.	principale
suffisso_partita (Opz.)	Suffisso testuale della partita.	A
data_chiusura (Opz.)	Data di chiusura in formato YYYY-MM-DD.	2010-12-31
numero_provenienza (Opz.)	Riferimento testuale o numerico.	Vol. 12, N. 45

Esempio di file:
Snippet di codice

numero_partita;suffisso_partita;data_impianto;stato;tipo;numero_provenienza
1052;A;1985-07-22;attiva;principale;
1053;;1970-01-15;inattiva;principale;Vol. 10, N. 3
