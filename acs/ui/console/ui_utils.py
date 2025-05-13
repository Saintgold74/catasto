# ui/console/ui_utils.py
import getpass # Per nascondere l'input della password
import logging
from typing import List, Dict, Any, Optional
from datetime import date, datetime # Assicura che 'date' e 'datetime' siano importati

logger = logging.getLogger("CatastoAppLogger.UIUtils")

def stampa_locandina_introduzione():
    """Stampa una locandina di introduzione testuale."""
    print("*" * 80)
    print("*" + " " * 78 + "*")
    print("*" + "ARCHIVIO CATASTALE STORICO - GESTIONALE".center(78) + "*")
    print("*" + " " * 78 + "*")
    print("*" + "Progetto di Marco Santoro".center(78) + "*")
    print("*" + f"Versione Applicazione: 1.5 - Modular".center(78) + "*") # Aggiorna versione se necessario
    print("*" + " " * 78 + "*")
    print("*" * 80)
    print("\nBenvenuto nel sistema di gestione dell'Archivio Catastale Storico.")

def input_sicuro_password(prompt: str = "Password: ") -> str:
    """Richiede l'input di una password in modo sicuro (nascondendo i caratteri)."""
    while True:
        try:
            password = getpass.getpass(prompt)
            if not password: # Impedisce password vuote se richiesto
                print("La password non può essere vuota. Riprova.")
                continue
            # Potresti aggiungere qui controlli sulla complessità della password
            return password
        except Exception as e:
            logger.error(f"Errore durante l'input sicuro della password: {e}")
            print(f"Si è verificato un errore: {e}. Riprova.")
        except KeyboardInterrupt:
            print("\nInput password annullato.")
            return "" # Ritorna stringa vuota o solleva eccezione

def seleziona_da_lista(lista: List[Dict[str, Any]], 
                       titolo: str = "Seleziona un elemento",
                       id_key: str = 'id', 
                       desc_keys: List[str] = None, # Lista di chiavi per la descrizione
                       prompt_utente: str = "Scegli un numero (0 per annullare): ",
                       mostra_annulla: bool = True) -> Optional[Dict[str, Any]]:
    """
    Mostra una lista di dizionari all'utente e permette la selezione.
    Restituisce il dizionario selezionato o None se l'utente annulla o l'input è invalido.
    `desc_keys` permette di specificare più chiavi per costruire la descrizione.
    """
    if not lista:
        print(f"Nessun elemento disponibile in '{titolo}'.")
        return None

    if desc_keys is None: # Default a cercare chiavi comuni per la descrizione
        # Tenta di trovare chiavi descrittive comuni se non specificato
        first_item_keys = lista[0].keys()
        if 'nome' in first_item_keys: desc_keys = ['nome']
        elif 'descrizione' in first_item_keys: desc_keys = ['descrizione']
        elif 'numero_partita' in first_item_keys: desc_keys = ['numero_partita']
        elif 'tipo_documento' in first_item_keys: desc_keys = ['tipo_documento', 'data_documento']
        elif 'username' in first_item_keys: desc_keys = ['username', 'email'] # Per utenti
        else: # Fallback se non trova chiavi comuni, usa la prima chiave non ID
            desc_keys = [k for k in first_item_keys if k != id_key][:1] 
            if not desc_keys and len(first_item_keys) > 0 : desc_keys = [list(first_item_keys)[0]]


    print(f"\n--- {titolo} ---")
    for i, item in enumerate(lista):
        desc_parts = []
        for key in desc_keys:
            val = item.get(key)
            if val is not None:
                if isinstance(val, (datetime, date)):
                    desc_parts.append(val.strftime('%d/%m/%Y'))
                else:
                    desc_parts.append(str(val))
        desc_str = " - ".join(filter(None, desc_parts))
        if not desc_str: # Se tutte le chiavi descrittive erano None o vuote
            desc_str = f"Elemento {item.get(id_key, 'N/A')}"
        print(f"{i+1}. {desc_str} (ID: {item.get(id_key, 'N/A')})")
    
    if mostra_annulla:
        print("0. Annulla")

    while True:
        try:
            scelta_str = input(prompt_utente)
            if not scelta_str.strip(): # Input vuoto, riprova
                continue
            scelta = int(scelta_str)
            if mostra_annulla and scelta == 0:
                return None
            if 1 <= scelta <= len(lista):
                return lista[scelta-1]
            else:
                print(f"Scelta non valida. Inserisci un numero tra {1 if not mostra_annulla else 0} e {len(lista)}.")
        except ValueError:
            print("Input non valido. Inserisci un numero.")
        except KeyboardInterrupt:
            print("\nSelezione annullata dall'utente.")
            return None

def chiedi_conferma(messaggio: str = "Sei sicuro?", default_yes: bool = False) -> bool:
    """Chiede conferma all'utente (S/N)."""
    prompt = f"{messaggio} [{'S/n' if default_yes else 's/N'}]: "
    while True:
        try:
            risposta = input(prompt).strip().lower()
            if not risposta: # Invio senza input
                return default_yes
            if risposta in ['s', 'si', 'yes', 'y']:
                return True
            if risposta in ['n', 'no']:
                return False
            print("Risposta non valida. Inserisci 's' o 'n'.")
        except KeyboardInterrupt:
            print("\nConferma annullata.")
            return False # O solleva eccezione

def input_valore(prompt: str, tipo: type = str, obbligatorio: bool = True, default: Any = None, validatore: callable = None):
    """
    Funzione generica per richiedere un input all'utente con tipo, opzionalità e validazione.
    `tipo` può essere str, int, float, date.
    `validatore` è una funzione che prende il valore e restituisce True se valido, False altrimenti.
    """
    while True:
        try:
            if default is not None and not obbligatorio:
                val_str = input(f"{prompt} (default: {default}): ").strip()
                if not val_str:
                    return default
            else:
                val_str = input(f"{prompt}: ").strip()

            if not val_str and obbligatorio:
                print("Questo campo è obbligatorio.")
                continue
            elif not val_str and not obbligatorio: # Campo non obbligatorio lasciato vuoto
                return None

            valore_convertito: Any = None
            if tipo == str:
                valore_convertito = val_str
            elif tipo == int:
                valore_convertito = int(val_str)
            elif tipo == float:
                valore_convertito = float(val_str)
            elif tipo == date:
                try: # Prova formati comuni
                    valore_convertito = datetime.strptime(val_str, '%d/%m/%Y').date()
                except ValueError:
                    try:
                        valore_convertito = datetime.strptime(val_str, '%Y-%m-%d').date()
                    except ValueError:
                        print("Formato data non valido. Usa GG/MM/AAAA o AAAA-MM-GG.")
                        continue
            else: # Tipo non gestito, restituisci stringa
                valore_convertito = val_str
            
            if validatore:
                if not validatore(valore_convertito):
                    # Il validatore dovrebbe stampare il suo messaggio di errore
                    continue
            
            return valore_convertito

        except ValueError as ve:
            if tipo == int: print("Input non valido. Inserisci un numero intero.")
            elif tipo == float: print("Input non valido. Inserisci un numero (es. 123.45).")
            else: print(f"Errore di conversione: {ve}")
        except KeyboardInterrupt:
            print("\nInput annullato.")
            return None # O solleva eccezione se preferisci che interrompa il flusso

def formatta_data_utente(data_obj: Optional[date]) -> str:
    """Formatta un oggetto data in stringa GG/MM/AAAA o '' se None."""
    if data_obj:
        return data_obj.strftime('%d/%m/%Y')
    return ''

def parse_data_utente(data_str: Optional[str]) -> Optional[date]:
    """Converte una stringa GG/MM/AAAA o AAAA-MM-GG in oggetto data, o None."""
    if not data_str or not data_str.strip():
        return None
    try:
        return datetime.strptime(data_str.strip(), '%d/%m/%Y').date()
    except ValueError:
        try:
            return datetime.strptime(data_str.strip(), '%Y-%m-%d').date()
        except ValueError:
            return None # O solleva eccezione se il formato deve essere rigoroso

# Esempio di validatore (puoi crearne altri specifici)
def validatore_non_vuoto(valore: Any) -> bool:
    if isinstance(valore, str) and not valore.strip():
        print("Il campo non può essere vuoto.")
        return False
    if valore is None: # Utile per tipi non stringa
        print("Il campo non può essere nullo (se obbligatorio).")
        return False
    return True