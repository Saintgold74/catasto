import psycopg2
from psycopg2 import sql
import getpass
import os
import sys
from datetime import date

class CatastoApp:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connected = False
        
    def connect(self):
        """Connette al database catasto_storico"""
        try:
            print("Connessione al database catasto_storico...")
            user = input("Utente PostgreSQL [postgres]: ") or "postgres"
            password = getpass.getpass(f"Password per {user}: ")
            host = input("Host [localhost]: ") or "localhost"
            port = input("Porta [5432]: ") or "5432"
            
            self.conn = psycopg2.connect(
                dbname="catasto_storico",
                user=user,
                password=password,
                host=host,
                port=port
            )
            self.cursor = self.conn.cursor()
            self.cursor.execute("SET search_path TO catasto;")
            self.connected = True
            print("Connessione stabilita con successo!")
            return True
        except Exception as e:
            print(f"Errore di connessione: {e}")
            return False
    
    def disconnect(self):
        """Chiude la connessione al database"""
        if self.conn:
            self.conn.close()
            print("Disconnesso dal database.")
        self.connected = False
    
    def clear_screen(self):
        """Pulisce lo schermo"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title):
        """Stampa un'intestazione formattata"""
        self.clear_screen()
        print("=" * 50)
        print(f"{title.center(50)}")
        print("=" * 50)
        print()
    
    def wait_for_key(self):
        """Attende che l'utente prema un tasto per continuare"""
        input("\nPremi INVIO per continuare...")
    
    def mostra_comuni(self):
        """Visualizza l'elenco dei comuni"""
        self.print_header("ELENCO COMUNI")
        
        try:
            self.cursor.execute("SELECT nome, provincia, regione FROM comune ORDER BY nome;")
            comuni = self.cursor.fetchall()
            
            if not comuni:
                print("Nessun comune trovato.")
                return
            
            print(f"{'NOME':<20} {'PROVINCIA':<15} {'REGIONE':<15}")
            print("-" * 50)
            
            for comune in comuni:
                nome, provincia, regione = comune
                print(f"{nome:<20} {provincia:<15} {regione:<15}")
            
        except Exception as e:
            print(f"Errore nella visualizzazione dei comuni: {e}")
        
        self.wait_for_key()
    
    def mostra_partite(self):
        """Visualizza l'elenco delle partite"""
        self.print_header("ELENCO PARTITE")
        
        try:
            self.cursor.execute("""
                SELECT p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato,
                       string_agg(pos.nome_completo, ', ') as possessori
                FROM partita p
                LEFT JOIN partita_possessore pp ON p.id = pp.partita_id
                LEFT JOIN possessore pos ON pp.possessore_id = pos.id
                GROUP BY p.id, p.comune_nome, p.numero_partita, p.tipo, p.stato
                ORDER BY p.comune_nome, p.numero_partita
                LIMIT 20;
            """)
            partite = self.cursor.fetchall()
            
            if not partite:
                print("Nessuna partita trovata.")
                return
            
            print(f"{'ID':<5} {'COMUNE':<15} {'NUMERO':<8} {'TIPO':<12} {'STATO':<10} {'POSSESSORI':<30}")
            print("-" * 80)
            
            for partita in partite:
                id, comune, numero, tipo, stato, possessori = partita
                possessori = (possessori or "")[:30]
                print(f"{id:<5} {comune:<15} {numero:<8} {tipo:<12} {stato:<10} {possessori:<30}")
            
        except Exception as e:
            print(f"Errore nella visualizzazione delle partite: {e}")
        
        self.wait_for_key()
    
    def mostra_possessori(self):
        """Visualizza l'elenco dei possessori"""
        self.print_header("ELENCO POSSESSORI")
        
        try:
            self.cursor.execute("""
                SELECT id, nome_completo, comune_nome, cognome_nome, paternita, attivo
                FROM possessore
                ORDER BY comune_nome, nome_completo
                LIMIT 20;
            """)
            possessori = self.cursor.fetchall()
            
            if not possessori:
                print("Nessun possessore trovato.")
                return
            
            print(f"{'ID':<5} {'NOME COMPLETO':<30} {'COMUNE':<15} {'STATO':<10}")
            print("-" * 60)
            
            for pos in possessori:
                id, nome, comune, cognome, paternita, attivo = pos
                stato = "Attivo" if attivo else "Non attivo"
                print(f"{id:<5} {nome:<30} {comune:<15} {stato:<10}")
            
        except Exception as e:
            print(f"Errore nella visualizzazione dei possessori: {e}")
        
        self.wait_for_key()
    
    def mostra_immobili(self):
        """Visualizza l'elenco degli immobili"""
        self.print_header("ELENCO IMMOBILI")
        
        try:
            self.cursor.execute("""
                SELECT i.id, i.natura, l.nome as localita, p.numero_partita, p.comune_nome
                FROM immobile i
                JOIN localita l ON i.localita_id = l.id
                JOIN partita p ON i.partita_id = p.id
                ORDER BY p.comune_nome, p.numero_partita
                LIMIT 20;
            """)
            immobili = self.cursor.fetchall()
            
            if not immobili:
                print("Nessun immobile trovato.")
                return
            
            print(f"{'ID':<5} {'NATURA':<25} {'LOCALITA':<20} {'PARTITA':<8} {'COMUNE':<15}")
            print("-" * 75)
            
            for imm in immobili:
                id, natura, localita, partita, comune = imm
                print(f"{id:<5} {natura:<25} {localita:<20} {partita:<8} {comune:<15}")
            
        except Exception as e:
            print(f"Errore nella visualizzazione degli immobili: {e}")
        
        self.wait_for_key()
    
    def inserisci_possessore(self):
        """Inserisce un nuovo possessore"""
        self.print_header("INSERIMENTO NUOVO POSSESSORE")
        
        try:
            # Ottieni la lista dei comuni disponibili
            self.cursor.execute("SELECT nome FROM comune ORDER BY nome;")
            comuni = [c[0] for c in self.cursor.fetchall()]
            
            if not comuni:
                print("Nessun comune disponibile. Impossibile inserire un possessore.")
                self.wait_for_key()
                return
            
            print("Comuni disponibili:")
            for i, comune in enumerate(comuni, 1):
                print(f"{i}. {comune}")
            
            idx = int(input("\nSeleziona il numero del comune: ")) - 1
            if idx < 0 or idx >= len(comuni):
                print("Selezione non valida.")
                self.wait_for_key()
                return
            
            comune_nome = comuni[idx]
            cognome_nome = input("Cognome e nome (es. Rossi Mario): ")
            paternita = input("Paternità (es. fu Giuseppe): ")
            nome_completo = f"{cognome_nome} {paternita}"
            
            self.cursor.execute("""
                CALL inserisci_possessore(%s, %s, %s, %s, %s);
            """, (comune_nome, cognome_nome, paternita, nome_completo, True))
            
            self.conn.commit()
            print(f"\nPossessore {nome_completo} inserito con successo nel comune di {comune_nome}!")
            
        except Exception as e:
            self.conn.rollback()
            print(f"Errore nell'inserimento del possessore: {e}")
        
        self.wait_for_key()
    
    def inserisci_partita(self):
        """Inserisce una nuova partita"""
        self.print_header("INSERIMENTO NUOVA PARTITA")
        
        try:
            # Ottieni la lista dei comuni disponibili
            self.cursor.execute("SELECT nome FROM comune ORDER BY nome;")
            comuni = [c[0] for c in self.cursor.fetchall()]
            
            if not comuni:
                print("Nessun comune disponibile. Impossibile inserire una partita.")
                self.wait_for_key()
                return
            
            print("Comuni disponibili:")
            for i, comune in enumerate(comuni, 1):
                print(f"{i}. {comune}")
            
            idx = int(input("\nSeleziona il numero del comune: ")) - 1
            if idx < 0 or idx >= len(comuni):
                print("Selezione non valida.")
                self.wait_for_key()
                return
            
            comune_nome = comuni[idx]
            
            # Trova un numero di partita disponibile
            self.cursor.execute("""
                SELECT COALESCE(MAX(numero_partita), 0) + 1
                FROM partita
                WHERE comune_nome = %s;
            """, (comune_nome,))
            
            numero_partita = self.cursor.fetchone()[0]
            numero_partita = int(input(f"Numero partita [suggerito: {numero_partita}]: ") or numero_partita)
            
            # Verifica che il numero partita non esista già
            self.cursor.execute("""
                SELECT 1 FROM partita 
                WHERE comune_nome = %s AND numero_partita = %s;
            """, (comune_nome, numero_partita))
            
            if self.cursor.fetchone():
                print(f"Errore: La partita {numero_partita} esiste già nel comune {comune_nome}.")
                self.wait_for_key()
                return
            
            tipo = input("Tipo (principale/secondaria) [principale]: ") or "principale"
            
            # Ottieni la lista dei possessori disponibili per il comune
            self.cursor.execute("""
                SELECT id, nome_completo 
                FROM possessore 
                WHERE comune_nome = %s AND attivo = TRUE
                ORDER BY nome_completo;
            """, (comune_nome,))
            
            possessori = self.cursor.fetchall()
            
            if not possessori:
                print(f"Nessun possessore disponibile nel comune {comune_nome}. Impossibile inserire una partita.")
                self.wait_for_key()
                return
            
            print("\nPossessori disponibili:")
            for i, (id, nome) in enumerate(possessori, 1):
                print(f"{i}. {nome} (ID: {id})")
            
            idx = int(input("\nSeleziona il numero del possessore: ")) - 1
            if idx < 0 or idx >= len(possessori):
                print("Selezione non valida.")
                self.wait_for_key()
                return
            
            possessore_id = possessori[idx][0]
            possessore_ids = [possessore_id]
            
            # Inserisci la partita
            self.cursor.execute("""
                CALL inserisci_partita_con_possessori(%s, %s, %s, %s, %s);
            """, (comune_nome, numero_partita, tipo, date.today(), possessore_ids))
            
            self.conn.commit()
            print(f"\nPartita {numero_partita} inserita con successo nel comune di {comune_nome}!")
            
        except Exception as e:
            self.conn.rollback()
            print(f"Errore nell'inserimento della partita: {e}")
        
        self.wait_for_key()
    
    def genera_certificato(self):
        """Genera un certificato di proprietà per una partita"""
        self.print_header("GENERAZIONE CERTIFICATO DI PROPRIETÀ")
        
        try:
            partita_id = input("Inserisci l'ID della partita: ")
            
            self.cursor.execute("""
                SELECT genera_certificato_proprieta(%s);
            """, (partita_id,))
            
            certificato = self.cursor.fetchone()[0]
            print("\n" + certificato)
            
        except Exception as e:
            print(f"Errore nella generazione del certificato: {e}")
        
        self.wait_for_key()
    
    def ricerca_possessori(self):
        """Ricerca possessori per nome"""
        self.print_header("RICERCA POSSESSORI")
        
        try:
            nome = input("Inserisci il nome da cercare: ")
            
            self.cursor.execute("""
                SELECT * FROM cerca_possessori(%s);
            """, (nome,))
            
            possessori = self.cursor.fetchall()
            
            if not possessori:
                print("Nessun possessore trovato con questo nome.")
                self.wait_for_key()
                return
            
            print(f"{'ID':<5} {'NOME COMPLETO':<30} {'COMUNE':<15} {'NUM PARTITE':<10}")
            print("-" * 60)
            
            for pos in possessori:
                id, nome, comune, num_partite = pos
                print(f"{id:<5} {nome:<30} {comune:<15} {num_partite:<10}")
            
        except Exception as e:
            print(f"Errore nella ricerca dei possessori: {e}")
        
        self.wait_for_key()
    
    def ricerca_immobili(self):
        """Ricerca immobili per vari criteri"""
        self.print_header("RICERCA IMMOBILI")
        
        try:
            comune = input("Comune [lascia vuoto per tutti]: ")
            natura = input("Natura immobile [lascia vuoto per tutti]: ")
            
            comune = comune if comune else None
            natura = natura if natura else None
            
            self.cursor.execute("""
                SELECT * FROM cerca_immobili(NULL, %s, NULL, %s, NULL);
            """, (comune, natura))
            
            immobili = self.cursor.fetchall()
            
            if not immobili:
                print("Nessun immobile trovato con questi criteri.")
                self.wait_for_key()
                return
            
            print(f"{'ID':<5} {'NATURA':<25} {'LOCALITA':<20} {'COMUNE':<15} {'PARTITA':<8}")
            print("-" * 75)
            
            for imm in immobili:
                id, partita_id, numero_partita, comune, localita, natura, classe = imm
                print(f"{id:<5} {natura:<25} {localita:<20} {comune:<15} {numero_partita:<8}")
            
        except Exception as e:
            print(f"Errore nella ricerca degli immobili: {e}")
        
        self.wait_for_key()
    
    def aggiorna_possessore(self):
        """Aggiorna i dati di un possessore"""
        self.print_header("AGGIORNAMENTO POSSESSORE")
        
        try:
            id = input("Inserisci l'ID del possessore da aggiornare: ")
            
            # Verifica che il possessore esista
            self.cursor.execute("""
                SELECT id, nome_completo, comune_nome, cognome_nome, paternita, attivo
                FROM possessore
                WHERE id = %s;
            """, (id,))
            
            possessore = self.cursor.fetchone()
            
            if not possessore:
                print(f"Nessun possessore trovato con ID {id}.")
                self.wait_for_key()
                return
            
            id, nome, comune, cognome, paternita, attivo = possessore
            
            print(f"Possessore: {nome} ({comune})")
            print(f"Attualmente {'attivo' if attivo else 'non attivo'}")
            
            nuovo_stato = input("Nuovo stato (attivo/non attivo) [lascia vuoto per mantenere]: ")
            
            if nuovo_stato:
                nuovo_attivo = nuovo_stato.lower() == "attivo"
                
                self.cursor.execute("""
                    UPDATE possessore SET attivo = %s WHERE id = %s;
                """, (nuovo_attivo, id))
                
                self.conn.commit()
                print(f"\nPossessore aggiornato con successo! Nuovo stato: {'attivo' if nuovo_attivo else 'non attivo'}")
            else:
                print("Nessuna modifica effettuata.")
            
        except Exception as e:
            self.conn.rollback()
            print(f"Errore nell'aggiornamento del possessore: {e}")
        
        self.wait_for_key()
    
    def main_menu(self):
        """Mostra il menu principale e gestisce le scelte dell'utente"""
        while True:
            self.print_header("CATASTO STORICO - MENU PRINCIPALE")
            
            if not self.connected:
                print("Non sei connesso al database.")
                print("1. Connetti al database")
                print("0. Esci")
                
                choice = input("\nScelta: ")
                
                if choice == "1":
                    if self.connect():
                        continue
                elif choice == "0":
                    break
                else:
                    print("Scelta non valida!")
                    self.wait_for_key()
            else:
                print("1. Visualizza comuni")
                print("2. Visualizza partite")
                print("3. Visualizza possessori")
                print("4. Visualizza immobili")
                print("5. Inserisci nuovo possessore")
                print("6. Inserisci nuova partita")
                print("7. Genera certificato di proprietà")
                print("8. Ricerca possessori")
                print("9. Ricerca immobili")
                print("10. Aggiorna possessore")
                print("0. Disconnetti ed esci")
                
                choice = input("\nScelta: ")
                
                if choice == "1":
                    self.mostra_comuni()
                elif choice == "2":
                    self.mostra_partite()
                elif choice == "3":
                    self.mostra_possessori()
                elif choice == "4":
                    self.mostra_immobili()
                elif choice == "5":
                    self.inserisci_possessore()
                elif choice == "6":
                    self.inserisci_partita()
                elif choice == "7":
                    self.genera_certificato()
                elif choice == "8":
                    self.ricerca_possessori()
                elif choice == "9":
                    self.ricerca_immobili()
                elif choice == "10":
                    self.aggiorna_possessore()
                elif choice == "0":
                    self.disconnect()
                    break
                else:
                    print("Scelta non valida!")
                    self.wait_for_key()

if __name__ == "__main__":
    app = CatastoApp()
    app.main_menu()