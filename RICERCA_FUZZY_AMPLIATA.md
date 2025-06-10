
# RICERCA FUZZY AMPLIATA - GUIDA COMPLETA

## Panoramica
La ricerca fuzzy ampliata estende il sistema catasto con capacità di ricerca
avanzate in tutte le entità del database.

## Nuove Funzionalità

### 1. Ricerca negli Immobili
- **Natura**: terreno, fabbricato, ecc.
- **Classificazione**: categoria catastale
- **Consistenza**: descrizione dell'immobile

### 2. Ricerca nelle Variazioni
- **Tipo variazione**: vendita, successione, ecc.
- **Nominativo riferimento**: persona coinvolta
- **Numero riferimento**: codice pratica

### 3. Ricerca nei Contratti
- **Tipo contratto**: atto di compravendita, ecc.
- **Notaio**: nome del notaio
- **Repertorio**: numero repertorio
- **Note**: annotazioni libere

### 4. Ricerca nelle Partite
- **Numero partita**: ricerca numerica
- **Suffisso partita**: bis, ter, A, B, ecc.

### 5. Ricerca Unificata
- Ricerca simultanea in tutte le entità
- Risultati raggruppati per tipo
- Soglia di similarità configurabile

## Interfaccia Utente

### Controlli Principali
- **Barra di ricerca**: testo libero con completamento automatico
- **Tipo ricerca**: selettore per tipo specifico o unificata
- **Soglia similarità**: slider per precisione ricerca
- **Export**: esportazione risultati in CSV/JSON

### Risultati
- **Tab Tutti**: risultati unificati con icone per tipo
- **Tab specifici**: risultati separati per entità
- **Doppio click**: visualizza dettagli completi
- **Pulsanti azione**: accesso rapido ai dettagli

## Implementazione Tecnica

### Indici GIN
Il sistema utilizza indici GIN PostgreSQL per ricerca full-text:
- `idx_gin_immobili_natura`
- `idx_gin_variazioni_tipo`
- `idx_gin_contratti_notaio`
- E molti altri...

### Funzioni PostgreSQL
- `search_immobili_fuzzy()`: ricerca negli immobili
- `search_variazioni_fuzzy()`: ricerca nelle variazioni
- `search_contratti_fuzzy()`: ricerca nei contratti
- `search_partite_fuzzy()`: ricerca nelle partite
- `search_all_entities_fuzzy()`: ricerca unificata

### Estensione Python
- `CatastoGINSearchExpanded`: classe principale
- `ExpandedFuzzySearchWidget`: widget GUI
- `EntityDetailsDialog`: dialog dettagli entità

## Performance

### Ottimizzazioni
- Ricerca parallela su indici GIN
- Risultati limitati per tipo
- Cache dei risultati frequenti
- Threshold configurabile per precisione/velocità

### Monitoraggio
- Verifica automatica degli indici
- Statistiche di utilizzo
- Log delle performance

## Configurazione

### Soglie Consigliate
- **Ricerca veloce**: 0.5-0.7 (maggiore precisione)
- **Ricerca estesa**: 0.2-0.4 (maggiore tolleranza)
- **Ricerca in dati storici**: 0.1-0.3 (massima tolleranza)

### Limiti Risultati
- **Per tipo**: 30 risultati (configurabile)
- **Totali**: 200 risultati massimi
- **Export**: illimitato

## Troubleshooting

### Problemi Comuni
1. **Ricerca lenta**: verificare indici GIN
2. **Nessun risultato**: abbassare soglia similarità
3. **Troppi risultati**: aumentare soglia o raffinare query

### Verifica Sistema
```sql
-- Verifica indici GIN
SELECT * FROM verify_gin_indices();

-- Test funzioni
SELECT COUNT(*) FROM search_all_entities_fuzzy('test', 0.3);
```

### Log e Debug
- Controllare log applicazione per errori
- Verificare connessione database
- Controllare permessi utente database

## Esempi di Utilizzo

### Ricerca Immobili
```
Query: "terra"
Risultati: terreno, terrazza, territorio
Campi: natura, consistenza
```

### Ricerca Variazioni
```
Query: "vend"
Risultati: vendita, rivendita
Campi: tipo, nominativo_riferimento
```

### Ricerca Unificata
```
Query: "rossi"
Risultati: 
- Possessori: Mario Rossi, Rossini Giuseppe
- Località: Via Rossini, Borgo Rossi
- Contratti: Notaio Rossi
```

## Estensioni Future

### Funzionalità Pianificate
- Ricerca geografica con coordinate
- Ricerca temporale avanzata
- Analisi statistiche integrate
- Export in formati CAD/GIS
- API REST per integrazioni esterne

### Personalizzazioni
- Campi di ricerca aggiuntivi
- Algoritmi di similarità custom
- Template export personalizzati
- Dashboard analitiche
