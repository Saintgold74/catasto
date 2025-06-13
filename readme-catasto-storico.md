# Sistema di Gestione Catasto Storico

## 📋 Panoramica del Progetto

Il Sistema di Gestione Catasto Storico è un'applicazione completa per la digitalizzazione e gestione dei registri catastali storici. Il progetto integra un database PostgreSQL avanzato con un'interfaccia desktop Python/PyQt5, fornendo strumenti per l'archiviazione, ricerca e analisi di dati catastali storici.

## 🎯 Obiettivi Principali

1. **Digitalizzazione**: Trasformare registri cartacei storici in un formato digitale strutturato
2. **Conservazione**: Preservare informazioni catastali storiche in modo sicuro e accessibile
3. **Accessibilità**: Fornire strumenti di ricerca avanzati per ricercatori e archivisti
4. **Analisi**: Permettere studi genealogici e storici delle proprietà immobiliari

## 🏗️ Architettura del Sistema

### Backend (PostgreSQL)
- **Schema dedicato**: `catasto` con tabelle normalizzate
- **Sistema di audit**: Tracciamento completo di tutte le modifiche
- **Funzioni avanzate**: Procedure stored per operazioni complesse
- **Ricerca fuzzy**: Indici GIN per ricerche testuali avanzate
- **Backup automatizzati**: Sistema integrato di backup e restore

### Frontend (Python/PyQt5)
- **Interfaccia desktop**: Applicazione nativa per Windows/Linux/Mac
- **Gestione multi-utente**: Sistema di autenticazione e permessi
- **Reportistica**: Generazione di report PDF e Excel
- **Ricerca avanzata**: Interfaccia intuitiva per ricerche complesse

## 📁 Struttura del Progetto

```
catasto-storico/
├── database/
│   ├── 01_schema_base.sql         # Schema e tabelle principali
│   ├── 02_funzioni_base.sql       # Funzioni e trigger
│   ├── 03_dati_esempio.sql        # Dati di esempio
│   └── scripts/                   # Script di manutenzione
├── src/
│   ├── gui_main.py               # Applicazione principale PyQt5
│   ├── gui_widgets.py            # Widget personalizzati
│   ├── database_manager.py       # Gestione connessioni DB
│   ├── catasto_gin_extension.py  # Estensione ricerca fuzzy
│   └── dialogs.py                # Finestre di dialogo
├── resources/
│   ├── logo_meridiana.png        # Logo applicazione
│   └── icons/                    # Icone interfaccia
├── docs/
│   ├── istruzioni-utilizzo.md    # Guida utente
│   └── diagrammi/                # Diagrammi ER e flussi
└── README.md                     # Questo file
```

## 🛠️ Requisiti di Sistema

### Software Richiesto
- **PostgreSQL**: Versione 15 o superiore
- **Python**: 3.8 o superiore
- **PyQt5**: 5.15 o superiore
- **psycopg2**: Per connessione PostgreSQL

### Librerie Python
```bash
pip install PyQt5>=5.15
pip install psycopg2-binary
pip install pandas
pip install openpyxl
pip install matplotlib
pip install reportlab
```

## 🚀 Installazione

### 1. Configurazione Database

```bash
# Creare il database
createdb catasto_storico

# Eseguire gli script in ordine
psql -d catasto_storico -f database/01_schema_base.sql
psql -d catasto_storico -f database/02_funzioni_base.sql
psql -d catasto_storico -f database/03_dati_esempio.sql
```

### 2. Configurazione Applicazione

```bash
# Clonare il repository
git clone [url-repository]
cd catasto-storico

# Installare dipendenze
pip install -r requirements.txt

# Configurare connessione database
# Modificare le credenziali in src/database_manager.py
```

### 3. Avvio Applicazione

```bash
cd src
python gui_main.py
```

## 📊 Modello Dati

### Entità Principali

- **Comuni**: Anagrafica dei comuni con gestione storica dei nomi
- **Possessori**: Persone fisiche e giuridiche proprietarie
- **Partite Catastali**: Unità di proprietà con numerazione storica
- **Immobili**: Beni immobili (terreni, fabbricati) con caratteristiche
- **Località**: Vie, contrade, borghi con riferimenti storici
- **Variazioni**: Trasferimenti di proprietà e modifiche catastali

### Relazioni Chiave

```
Comune ──┬── Partita Catastale ──┬── Immobile
         │                       │
         └── Località ───────────┘
         
Possessore ──── Variazione ──── Contratto
```

## 💡 Funzionalità Principali

### Gestione Dati
- ✅ Inserimento guidato di comuni, possessori, partite
- ✅ Modifica e cancellazione con controlli di integrità
- ✅ Import/export dati in formato Excel
- ✅ Backup e restore automatizzati

### Ricerca e Consultazione
- ✅ Ricerca fuzzy multi-entità
- ✅ Filtri avanzati per periodo storico
- ✅ Visualizzazione gerarchica delle proprietà
- ✅ Timeline delle variazioni di proprietà

### Reportistica
- ✅ Report proprietà per possessore
- ✅ Albero genealogico delle proprietà
- ✅ Statistiche catastali per periodo
- ✅ Esportazione PDF e Excel

### Amministrazione
- ✅ Gestione utenti e permessi
- ✅ Log delle operazioni
- ✅ Monitoraggio performance
- ✅ Manutenzione database

## 🔍 Esempi d'Uso

### Ricerca Possessore
```python
# Nella GUI: Tab Ricerca → Possessori
# Inserire: "Ross*" per trovare tutti i Rossi, Rossini, ecc.
```

### Registrazione Variazione
```python
# Menu: Registrazioni → Nuova Variazione Proprietà
# Selezionare: Partita origine, destinazione, tipo, data
```

### Generazione Report
```python
# Menu: Report → Albero Genealogico
# Selezionare: Partita catastale e periodo
```

## 🔧 Manutenzione

### Backup Periodici
```bash
# Script automatico (schedulare con cron)
./database/scripts/backup_catasto.sh
```

### Ottimizzazione Database
```sql
-- Eseguire mensilmente
VACUUM ANALYZE catasto.*;
REINDEX SCHEMA catasto;
```

### Pulizia Log
```sql
-- Rimuovere log più vecchi di 1 anno
DELETE FROM catasto.system_log 
WHERE created_at < CURRENT_DATE - INTERVAL '1 year';
```

## 📈 Sviluppi Futuri

### Fase 2: Funzionalità Avanzate (Pianificate)
- [ ] Integrazione GIS per mappe catastali
- [ ] OCR per digitalizzazione automatica documenti
- [ ] API REST per integrazioni esterne
- [ ] Versione web responsive

### Fase 3: Analisi e AI
- [ ] Machine learning per riconoscimento scrittura
- [ ] Analisi predittive su valori immobiliari
- [ ] Ricostruzione automatica alberi genealogici
- [ ] Dashboard analitiche interattive

## 🤝 Contribuire al Progetto

### Segnalazione Bug
1. Verificare che il bug non sia già segnalato
2. Aprire una issue dettagliata con:
   - Descrizione del problema
   - Passi per riprodurre
   - Screenshot se applicabile

### Proposte di Miglioramento
1. Discutere l'idea nella sezione Discussions
2. Creare una pull request con:
   - Descrizione della modifica
   - Test eseguiti
   - Documentazione aggiornata

## 📞 Supporto

### Documentazione
- [Guida Utente](docs/istruzioni-utilizzo.md)
- [Wiki del Progetto](wiki-link)
- [FAQ](docs/faq.md)

### Contatti
- Email supporto: [supporto@catasto-storico.it]
- Forum community: [forum-link]
- Chat sviluppatori: [discord/slack-link]

## 📄 Licenza

Questo progetto è distribuito sotto licenza MIT. Vedere il file [LICENSE](LICENSE) per i dettagli.

## 🙏 Ringraziamenti

- Archivio di Stato per la collaborazione e i dati storici
- Comunità PostgreSQL per il supporto tecnico
- Contributori open source per librerie e strumenti utilizzati

---

**Versione**: 1.0.0  
**Ultimo aggiornamento**: Gennaio 2025  
**Mantenuto da**: Team Sviluppo Catasto Storico