# MANUALE UTENTE
## Sistema di Gestione Catasto Storico
### Archivio di Stato di Savona

---

## INDICE

1. **Introduzione**
   - 1.1 Scopo del manuale
   - 1.2 A chi è rivolto
   - 1.3 Convenzioni utilizzate

2. **Panoramica del Sistema**
   - 2.1 Descrizione generale
   - 2.2 Requisiti di sistema
   - 2.3 Struttura dei menu

3. **Avvio e Accesso al Sistema**
   - 3.1 Primo avvio
   - 3.2 Login utente
   - 3.3 Interfaccia principale

4. **Consultazione Dati**
   - 4.1 Elenco comuni
   - 4.2 Ricerca partite
   - 4.3 Ricerca possessori
   - 4.4 Dettagli partita
   - 4.5 Ricerca avanzata

5. **Inserimento e Gestione Dati**
   - 5.1 Aggiungere un nuovo comune
   - 5.2 Registrare un nuovo possessore
   - 5.3 Registrare una nuova proprietà
   - 5.4 Registrare passaggi di proprietà
   - 5.5 Gestione variazioni

6. **Generazione Report**
   - 6.1 Report di proprietà
   - 6.2 Report genealogico
   - 6.3 Report possessore
   - 6.4 Statistiche comunali
   - 6.5 Esportazione dati

7. **Funzionalità Avanzate**
   - 7.1 Sistema di audit
   - 7.2 Backup e ripristino
   - 7.3 Manutenzione database
   - 7.4 Funzionalità storiche

8. **Risoluzione Problemi**
   - 8.1 Problemi comuni
   - 8.2 Messaggi di errore
   - 8.3 Supporto tecnico

---

## 1. INTRODUZIONE

### 1.1 Scopo del manuale

Questo manuale fornisce una guida completa all'utilizzo del Sistema di Gestione del Catasto Storico, sviluppato per l'Archivio di Stato di Savona. Il documento illustra tutte le funzionalità disponibili, fornendo istruzioni dettagliate per ogni operazione.

### 1.2 A chi è rivolto

Il manuale è destinato a:
- Operatori dell'Archivio di Stato
- Ricercatori autorizzati
- Amministratori del sistema
- Personale tecnico di supporto

### 1.3 Convenzioni utilizzate

Nel manuale sono utilizzate le seguenti convenzioni:
- **Grassetto**: indica elementi dell'interfaccia (pulsanti, menu, campi)
- *Corsivo*: indica termini tecnici o concetti importanti
- `Codice`: indica valori da inserire o codici di errore
- ⚠️ Simbolo di attenzione: indica note importanti o avvertenze

---

## 2. PANORAMICA DEL SISTEMA

### 2.1 Descrizione generale

Il Sistema di Gestione del Catasto Storico è un'applicazione desktop progettata per digitalizzare e gestire i registri catastali storici. Il sistema permette di:

- Consultare e ricercare dati catastali storici
- Registrare nuove proprietà e possessori
- Tracciare passaggi di proprietà nel tempo
- Generare report e statistiche
- Gestire documenti e consultazioni
- Mantenere un audit trail completo

### 2.2 Requisiti di sistema

**Requisiti minimi:**
- Sistema operativo: Windows 10 o superiore
- Processore: Intel Core i3 o equivalente
- RAM: 4 GB
- Spazio su disco: 2 GB disponibili
- Risoluzione schermo: 1280x720
- Connessione al database PostgreSQL

**Requisiti consigliati:**
- Sistema operativo: Windows 11
- Processore: Intel Core i5 o superiore
- RAM: 8 GB o più
- Spazio su disco: 5 GB disponibili
- Risoluzione schermo: 1920x1080
- Connessione di rete stabile

### 2.3 Struttura dei menu

Il sistema è organizzato in 8 aree funzionali principali:

1. **Consultazione dati** - Ricerca e visualizzazione informazioni
2. **Inserimento e gestione dati** - Registrazione nuovi record
3. **Generazione report** - Creazione documenti e statistiche
4. **Manutenzione database** - Ottimizzazione e verifica integrità
5. **Sistema di audit** - Tracciamento modifiche e accessi
6. **Gestione utenti e sessione** - Controllo accessi e permessi
7. **Sistema di backup** - Salvataggio e ripristino dati
8. **Funzionalità storiche avanzate** - Gestione dati temporali

---

## 3. AVVIO E ACCESSO AL SISTEMA

### 3.1 Primo avvio

1. Fare doppio clic sull'icona **Catasto Storico** sul desktop
2. Attendere il caricamento dell'applicazione
3. Alla prima esecuzione, verrà richiesta la configurazione del database

**Configurazione database:**
1. Dal menu **Impostazioni** selezionare **Configurazione Database**
2. Inserire i parametri di connessione:
   - **Host**: indirizzo del server database
   - **Porta**: normalmente 5432
   - **Nome database**: catasto_storico
   - **Username**: nome utente fornito
   - **Password**: password fornita
3. Cliccare su **Test connessione** per verificare
4. Se il test ha successo, cliccare su **Salva**

### 3.2 Login utente

1. Nella schermata di login, inserire:
   - **Username**: il proprio nome utente
   - **Password**: la propria password
2. Cliccare su **Accedi**
3. In caso di credenziali errate, verificare maiuscole/minuscole

⚠️ **Nota**: Dopo 3 tentativi falliti, l'account viene temporaneamente bloccato per 15 minuti.

### 3.3 Interfaccia principale

L'interfaccia principale è composta da:

- **Barra dei menu**: accesso a tutte le funzionalità
- **Toolbar**: accesso rapido alle funzioni più utilizzate
- **Area centrale**: visualizzazione contenuti
- **Barra di stato**: informazioni su operazioni in corso

---

## 4. CONSULTAZIONE DATI

### 4.1 Elenco comuni

**Per visualizzare l'elenco dei comuni:**

1. Dal menu principale selezionare **Consultazione dati**
2. Scegliere **Elenco comuni**
3. Verrà visualizzata una tabella con:
   - Codice comune
   - Nome comune
   - Provincia
   - Numero partite registrate

**Operazioni disponibili:**
- **Doppio clic** su un comune per vedere le sue partite
- **Clic destro** per menu contestuale con opzioni:
  - Visualizza partite
  - Visualizza possessori
  - Visualizza località
  - Modifica dati comune

### 4.2 Ricerca partite

**Ricerca semplice:**

1. Selezionare **Consultazione dati** → **Ricerca partite (Semplice)**
2. Inserire uno o più criteri:
   - **Numero partita**: numero esatto o parziale
   - **Comune**: selezionare dalla lista
   - **Tipo partita**: Urbana/Rustica/Mista
   - **Stato**: Attiva/Chiusa
3. Cliccare su **Cerca**

**Ricerca avanzata:**

1. Selezionare **Consultazione dati** → **Ricerca Avanzata Immobili**
2. Compilare i campi desiderati:
   - **Località**: nome della località
   - **Foglio/Mappale**: riferimenti catastali
   - **Tipo immobile**: Casa/Terreno/Fabbricato/ecc.
   - **Periodo temporale**: date di riferimento
3. Cliccare su **Cerca**

**Visualizzazione risultati:**
- I risultati appaiono in una griglia
- Cliccare su una riga per selezionarla
- Doppio clic per aprire i dettagli
- Pulsante **Esporta** per salvare in Excel

### 4.3 Ricerca possessori

1. Selezionare **Consultazione dati** → **Ricerca Avanzata Possessori**
2. Inserire i criteri di ricerca:
   - **Cognome/Nome**: anche parziale
   - **Paternità**: nome del padre
   - **Comune**: comune di riferimento
   - **Periodo**: anni di interesse
3. Opzioni di ricerca:
   - **Ricerca esatta**: trova corrispondenze precise
   - **Ricerca parziale**: trova risultati che contengono il testo
   - **Ricerca fonetica**: trova nomi simili
4. Cliccare su **Cerca**

### 4.4 Dettagli partita

**Per visualizzare i dettagli di una partita:**

1. Dalla ricerca partite, fare doppio clic sulla partita desiderata
2. Si aprirà la finestra dettagli con le schede:
   - **Dati generali**: informazioni base della partita
   - **Possessori**: elenco proprietari con quote
   - **Immobili**: beni collegati alla partita
   - **Variazioni**: storia dei cambiamenti
   - **Documenti**: atti e documenti associati

**Operazioni disponibili nei dettagli:**
- **Stampa**: genera PDF della scheda
- **Esporta**: salva in formato JSON
- **Modifica**: apre editor (solo utenti autorizzati)
- **Cronologia**: visualizza tutte le modifiche

### 4.5 Ricerca avanzata

**Ricerca multi-criterio:**

1. Accedere a **Consultazione dati** → **Ricerca Avanzata**
2. La finestra permette di combinare:
   - Criteri su partite
   - Criteri su possessori
   - Criteri su immobili
   - Criteri temporali
3. Utilizzare gli operatori logici:
   - **E**: tutti i criteri devono essere soddisfatti
   - **O**: almeno un criterio deve essere soddisfatto
   - **NON**: esclude risultati che soddisfano il criterio
4. Salvare le ricerche frequenti con **Salva ricerca**

---

## 5. INSERIMENTO E GESTIONE DATI

### 5.1 Aggiungere un nuovo comune

1. Selezionare **Inserimento e gestione dati** → **Aggiungi nuovo comune**
2. Compilare i campi obbligatori:
   - **Codice comune**: codice univoco (es. A001)
   - **Nome comune**: denominazione ufficiale
   - **Provincia**: sigla provincia (es. SV)
3. Campi opzionali:
   - **Codice catastale**: codice nazionale
   - **Note**: informazioni aggiuntive
4. Cliccare su **Salva**

⚠️ **Importante**: Il codice comune non può essere modificato dopo la creazione.

### 5.2 Registrare un nuovo possessore

**Procedura standard:**

1. Selezionare **Inserimento e gestione dati** → **Aggiungi nuovo possessore**
2. Compilare i dati anagrafici:
   - **Cognome e Nome**: formato "ROSSI MARIO"
   - **Paternità**: nome del padre (es. "fu Giovanni")
   - **Data nascita**: se conosciuta
   - **Luogo nascita**: comune di nascita
   - **Codice fiscale**: se disponibile
3. Dati aggiuntivi:
   - **Professione**: attività svolta
   - **Residenza**: indirizzo completo
   - **Note**: altre informazioni rilevanti
4. Cliccare su **Salva**

**Importazione da CSV:**

1. Dal menu **File** → **Importa Possessori da CSV**
2. Selezionare il file CSV con formato:
   ```
   cognome_nome;paternita;data_nascita;luogo_nascita;note
   ROSSI MARIO;fu Giovanni;1850-03-15;Savona;agricoltore
   ```
3. Verificare l'anteprima dei dati
4. Cliccare su **Importa**

### 5.3 Registrare una nuova proprietà

**Creazione nuova partita:**

1. Selezionare **Inserimento e gestione dati** → **Registra nuova proprietà**
2. **Sezione 1 - Dati Partita:**
   - **Comune**: selezionare dalla lista
   - **Numero partita**: numero progressivo univoco
   - **Tipo**: Urbana/Rustica/Mista
   - **Data impianto**: data creazione partita
   - **Volume/Pagina**: riferimenti registrali

3. **Sezione 2 - Possessori:**
   - Cliccare **Aggiungi possessore**
   - Cercare o creare il possessore
   - Specificare:
     - **Titolo**: Proprietario/Usufruttuario/ecc.
     - **Quota**: frazione di proprietà (es. 1/2)
     - **Data inizio**: quando acquisisce il diritto
   - Ripetere per ogni possessore

4. **Sezione 3 - Immobili:**
   - Cliccare **Aggiungi immobile**
   - Compilare:
     - **Tipo**: Casa/Terreno/Fabbricato/ecc.
     - **Località**: dove si trova
     - **Foglio/Mappale**: riferimenti catastali
     - **Superficie**: in mq o ettari
     - **Rendita**: valore catastale
     - **Descrizione**: dettagli aggiuntivi

5. Cliccare su **Salva partita**

### 5.4 Registrare passaggi di proprietà

**Procedura per variazione:**

1. Selezionare **Inserimento e gestione dati** → **Registra passaggio di proprietà**
2. **Step 1 - Seleziona partita origine:**
   - Cercare la partita da cui trasferire
   - Selezionarla dalla lista risultati
   
3. **Step 2 - Tipo di variazione:**
   - **Vendita**: trasferimento totale
   - **Divisione**: frazionamento partita
   - **Eredità**: successione
   - **Donazione**: atto gratuito
   - **Altro**: specificare

4. **Step 3 - Dettagli variazione:**
   - **Data variazione**: quando avviene
   - **Notaio**: professionista rogante
   - **Numero repertorio**: riferimento atto
   - **Immobili coinvolti**: selezionare quali trasferire
   
5. **Step 4 - Destinazione:**
   - **Partita esistente**: selezionare destinazione
   - **Nuova partita**: verrà creata automaticamente
   - Specificare i nuovi possessori e quote

6. Cliccare su **Esegui variazione**

### 5.5 Gestione variazioni

**Duplicazione partita:**

Utile per creare una copia storica prima di modifiche:

1. Trovare la partita da duplicare
2. Menu contestuale → **Duplica partita**
3. Specificare:
   - **Nuovo numero partita**
   - **Motivazione duplicazione**
4. La copia includerà tutti i dati ma senza storia

**Trasferimento immobile:**

Per spostare un singolo immobile:

1. Aprire i dettagli della partita origine
2. Scheda **Immobili** → selezionare immobile
3. Cliccare **Trasferisci a altra partita**
4. Cercare e selezionare partita destinazione
5. Confermare il trasferimento

---

## 6. GENERAZIONE REPORT

### 6.1 Report di proprietà

**Generazione report standard:**

1. Menu **Generazione report** → **Report di proprietà**
2. Selezionare il tipo:
   - **Singola partita**: report dettagliato
   - **Multiple partite**: report comparativo
   - **Per comune**: tutte le partite di un comune
3. Impostare i parametri:
   - **Periodo**: data inizio e fine
   - **Stato partite**: Attive/Chiuse/Tutte
   - **Dettaglio**: Sintetico/Completo
4. Opzioni di output:
   - **Visualizza**: apre anteprima
   - **Stampa**: invia a stampante
   - **Salva PDF**: esporta file
   - **Salva Excel**: foglio di calcolo

### 6.2 Report genealogico

Visualizza la storia dei passaggi di una proprietà:

1. Menu **Generazione report** → **Report genealogico**
2. Cercare e selezionare la partita
3. Impostare:
   - **Profondità**: numero generazioni da includere
   - **Tipo grafico**: Albero/Timeline/Tabella
   - **Includi documenti**: Sì/No
4. Il report mostrerà:
   - Sequenza cronologica proprietari
   - Collegamenti tra partite
   - Date e causali variazioni
   - Documenti associati (se richiesto)

### 6.3 Report possessore

Riepilogo di tutte le proprietà di un soggetto:

1. Menu **Generazione report** → **Report possessore**
2. Cercare il possessore
3. Parametri report:
   - **Periodo**: arco temporale
   - **Tipo proprietà**: quali includere
   - **Raggruppa per**: Comune/Anno/Tipo
4. Il report include:
   - Dati anagrafici completi
   - Elenco proprietà attuali
   - Storico proprietà passate
   - Riepilogo valori e superfici

### 6.4 Statistiche comunali

1. Menu **Generazione report** → **Statistiche per comune**
2. Selezionare uno o più comuni
3. Scegliere le statistiche:
   - **Numero partite**: totali e per tipo
   - **Numero possessori**: residenti e non
   - **Superfici**: per tipo immobile
   - **Valori catastali**: rendite complessive
   - **Variazioni**: numero per periodo
4. Opzioni grafiche:
   - **Tabelle**: dati numerici
   - **Grafici**: torte, barre, linee
   - **Mappe**: distribuzione geografica

### 6.5 Esportazione dati

**Esportazione massiva:**

1. Menu **Generazione report** → **Esporta dati**
2. Selezionare:
   - **Tipo dati**: Partite/Possessori/Immobili
   - **Filtri**: criteri selezione
   - **Formato**: CSV/JSON/XML/Excel
3. Opzioni avanzate:
   - **Includi relazioni**: dati collegati
   - **Includi metadati**: date modifica, utenti
   - **Comprimi**: crea archivio ZIP
4. Specificare percorso salvataggio
5. Cliccare **Esporta**

⚠️ **Nota**: L'esportazione di grandi quantità di dati può richiedere tempo.

---

## 7. FUNZIONALITÀ AVANZATE

### 7.1 Sistema di audit

Il sistema registra automaticamente tutte le operazioni.

**Consultare il log di audit:**

1. Menu **Sistema di audit** → **Consulta log di audit**
2. Impostare i filtri:
   - **Periodo**: intervallo date
   - **Utente**: chi ha operato
   - **Tipo operazione**: Inserimento/Modifica/Cancellazione
   - **Tabella**: quale entità
3. Risultati mostrano:
   - Data/ora operazione
   - Utente responsabile
   - Tipo operazione
   - Dati prima e dopo (per modifiche)
   - IP di connessione

**Cronologia di un record:**

1. Nei dettagli di qualsiasi record, cliccare **Cronologia**
2. Visualizza tutte le modifiche in ordine cronologico
3. Possibilità di confrontare versioni

### 7.2 Backup e ripristino

**Backup manuale:**

1. Menu **Sistema di backup** → **Ottieni comando per Backup**
2. Il sistema genera il comando appropriato
3. Opzioni backup:
   - **Completo**: tutti i dati
   - **Incrementale**: solo modifiche
   - **Struttura**: solo schema database
   - **Dati**: solo contenuti
4. Eseguire il comando in prompt amministratore

**Backup automatico:**

1. Menu **Sistema di backup** → **Genera Script Bash per Backup Automatico**
2. Configurare:
   - **Frequenza**: Giornaliero/Settimanale/Mensile
   - **Ora esecuzione**: quando eseguire
   - **Destinazione**: dove salvare
   - **Retention**: quanti backup mantenere
3. Il sistema genera lo script da schedulare

**Ripristino:**

1. Menu **Sistema di backup** → **Ottieni comando per Restore**
2. Selezionare il file di backup
3. Opzioni:
   - **Completo**: ripristina tutto
   - **Selettivo**: solo alcune tabelle
   - **Test**: verifica senza eseguire
4. ⚠️ **ATTENZIONE**: Il ripristino sovrascrive i dati esistenti!

### 7.3 Manutenzione database

**Verifica integrità:**

1. Menu **Manutenzione database** → **Verifica integrità database**
2. Il sistema controlla:
   - Chiavi primarie e foreign key
   - Indici corrotti
   - Dati orfani
   - Constraint violati
3. Risultati con eventuali problemi e soluzioni

**Ottimizzazione performance:**

1. Menu **Manutenzione database** → **Analizza Query Lente**
2. Mostra le query che impiegano più tempo
3. Suggerimenti per migliorare:
   - Creazione indici
   - Riscrittura query
   - Aggiornamento statistiche

**Manutenzione generale:**

1. Menu **Manutenzione database** → **Esegui Manutenzione Generale**
2. Operazioni eseguite:
   - VACUUM: recupera spazio
   - ANALYZE: aggiorna statistiche
   - REINDEX: ricostruisce indici
   - Pulizia log vecchi

### 7.4 Funzionalità storiche

**Gestione periodi storici:**

1. Menu **Funzionalità Storiche Avanzate** → **Visualizza Periodi Storici**
2. Definire periodi significativi:
   - Regno di Sardegna
   - Regno d'Italia
   - Repubblica Italiana
   - Altri periodi locali

**Nomi storici entità:**

Gestire i cambiamenti di denominazione nel tempo:

1. Menu **Funzionalità Storiche** → **Registra Nome Storico Entità**
2. Specificare:
   - **Entità**: Comune/Località/Via
   - **Nome storico**: denominazione dell'epoca
   - **Periodo validità**: da/a quando
   - **Note**: contesto del cambio
3. Il sistema userà automaticamente il nome corretto per periodo

**Documenti storici:**

1. Menu **Funzionalità Storiche** → **Collega Documento a Partita**
2. Selezionare la partita
3. Aggiungere documento:
   - **Tipo**: Atto/Mappa/Foto/Altro
   - **Data documento**: quando prodotto
   - **Descrizione**: contenuto
   - **Collocazione**: dove trovarlo fisicamente
   - **File digitale**: se disponibile scansione

---

## 8. RISOLUZIONE PROBLEMI

### 8.1 Problemi comuni

**Il programma non si avvia:**
- Verificare che il servizio database sia attivo
- Controllare la connessione di rete
- Verificare i requisiti di sistema
- Provare ad avviare come amministratore

**Errore di connessione al database:**
1. Verificare parametri in **Impostazioni** → **Configurazione Database**
2. Testare la connessione di rete con ping
3. Verificare che il firewall non blocchi la porta 5432
4. Controllare le credenziali di accesso

**Ricerche molto lente:**
- Eseguire manutenzione database
- Verificare indici con analisi query
- Ridurre il numero di risultati richiesti
- Utilizzare filtri più specifici

**Impossibile salvare/modificare dati:**
- Verificare di avere i permessi necessari
- Controllare che non ci siano lock sul record
- Verificare spazio disco disponibile
- Controllare il log di audit per dettagli

### 8.2 Messaggi di errore

**"Errore di integrità referenziale"**
- Causa: Si sta tentando di eliminare un record collegato ad altri
- Soluzione: Eliminare prima i record dipendenti

**"Duplicato non ammesso"**
- Causa: Esiste già un record con la stessa chiave
- Soluzione: Verificare numero partita o codice comune

**"Sessione scaduta"**
- Causa: Inattività prolungata
- Soluzione: Effettuare nuovo login

**"Permessi insufficienti"**
- Causa: L'utente non ha i diritti per l'operazione
- Soluzione: Contattare l'amministratore

**"Database non raggiungibile"**
- Causa: Problema di rete o server database fermo
- Soluzione: Verificare connessione e stato servizi

### 8.3 Supporto tecnico

**Prima di contattare il supporto:**

1. Annotare:
   - Messaggio di errore completo
   - Operazione che si stava eseguendo
   - Data e ora del problema
   - Username utilizzato

2. Provare:
   - Riavviare l'applicazione
   - Verificare la connessione
   - Eseguire manutenzione database
   - Consultare questo manuale

**Contatti supporto:**
- Email: supporto.catasto@archivio.savona.it
- Telefono: 019-XXXXXX (lun-ven 9:00-17:00)
- Ticket: sistema.ticket.interno

**Informazioni da fornire:**
- Versione del programma (menu Aiuto → Informazioni)
- Sistema operativo
- Descrizione dettagliata del problema
- Screenshot se possibile
- Log di errore se disponibile

---

## APPENDICI

### A. Glossario

**Partita**: Unità base del catasto che raggruppa immobili e proprietari
**Possessore**: Persona fisica o giuridica titolare di diritti su immobili
**Foglio**: Suddivisione territoriale del comune per fini catastali
**Mappale**: Numero che identifica una particella catastale
**Variazione**: Cambiamento nella titolarità o consistenza di una partita
**Rendita**: Valore attribuito all'immobile per fini fiscali

### B. Tasti rapidi

- **Ctrl+N**: Nuovo record
- **Ctrl+S**: Salva
- **Ctrl+F**: Cerca
- **Ctrl+P**: Stampa
- **F1**: Aiuto contestuale
- **F5**: Aggiorna visualizzazione
- **Esc**: Annulla/Chiudi finestra

### C. Formati di importazione

**CSV Possessori:**
```
cognome_nome;paternita;data_nascita;luogo_nascita;codice_fiscale;note
```

**CSV Partite:**
```
comune_id;numero_partita;tipo;data_impianto;volume;pagina;note
```

**CSV Immobili:**
```
partita_id;tipo;localita;foglio;mappale;superficie;rendita;descrizione
```

### D. Limiti del sistema

- Massimo 10.000 record per ricerca
- File allegati massimo 50 MB
- Backup automatici conservati per 90 giorni
- Sessione utente timeout dopo 30 minuti di inattività
- Password minimo 8 caratteri con lettere e numeri

---

**Versione manuale**: 1.0  
**Data pubblicazione**: Gennaio 2025  
**© 2025 Archivio di Stato di Savona - Tutti i diritti riservati**