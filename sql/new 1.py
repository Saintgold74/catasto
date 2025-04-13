import psycopg2
import sys

class CatastoApp:
    def __init__(self):
        # Parametri di connessione
        self.DB_URL = "dbname=catasto_storico user=postgres password=Markus74 host=localhost"
        self.conn = None
        
    def connetti(self):
        try:
            # Stabilisce la connessione
            self.conn = psycopg2.connect(self.DB_URL)
            # Imposta lo schema
            cur = self.conn.cursor()
            cur.execute("SET search_path TO catasto")
            print("Connessione al database stabilita con successo!")
        except (Exception, psycopg2.Error) as error:
            print(f"Errore durante la connessione: {error}")
            sys.exit(1)
    
    def mostra_menu_principale(self):
        print("\n============================================================")
        print("                 SISTEMA CATASTO STORICO                   ")
        print("============================================================")
        print("\n1) Visualizzare un certificato di proprietà")
        print("2) Generare report genealogico di una proprietà")
        print("3) Generare report storico di un possessore")
        print("4) Verificare integrità del database")
        print("5) Riparare problemi del database")
        print("6) Creare backup dei dati")
        print("0) Uscire")
    
    def genera_certificato_proprieta(self):
        try:
            partita_id = int(input("Inserisci l'ID della partita: "))
            
            cur = self.conn.cursor()
            cur.callproc('genera_certificato_proprieta', [partita_id])
            
            # Recupera il risultato
            result = cur.fetchone()[0]
            print("\nCERTIFICATO DI PROPRIETÀ:")
            print(result)
            
        except ValueError:
            print("Inserire un numero valido per l'ID della partita.")
        except Exception as e:
            print(f"Errore: {e}")
    
    def genera_report_genealogico(self):
        try:
            partita_id = int(input("Inserisci l'ID della partita: "))
            
            cur = self.conn.cursor()
            cur.callproc('genera_report_genealogico', [partita_id])
            
            # Recupera il risultato
            result = cur.fetchone()[0]
            print("\nREPORT GENEALOGICO:")
            print(result)
            
        except ValueError:
            print("Inserire un numero valido per l'ID della partita.")
        except Exception as e:
            print(f"Errore: {e}")
    
    def genera_report_possessore(self):
        try:
            possessore_id = int(input("Inserisci l'ID del possessore: "))
            
            cur = self.conn.cursor()
            cur.callproc('genera_report_possessore', [possessore_id])
            
            # Recupera il risultato
            result = cur.fetchone()[0]
            print("\nREPORT POSSESSORE:")
            print(result)
            
        except ValueError:
            print("Inserire un numero valido per l'ID del possessore.")
        except Exception as e:
            print(f"Errore: {e}")
    
    def verifica_integrita_database(self):
        try:
            cur = self.conn.cursor()
            cur.callproc('verifica_integrita_database')
            
            # Recupera il risultato
            result = cur.fetchone()[0]
            print("\nVERIFICA INTEGRITÀ DATABASE:")
            print(f"Problemi trovati: {'Sì' if result else 'No'}")
            print("Controlla i log del database per i dettagli.")
            
        except Exception as e:
            print(f"Errore: {e}")
    
    def ripara_problemi_database(self):
        conferma = input("Confermi la riparazione automatica dei problemi? (s/n): ")
        
        if conferma.lower() == 's':
            try:
                cur = self.conn.cursor()
                cur.callproc('ripara_problemi_database', [True])
                
                print("\nRIPARAZIONE DATABASE:")
                print("Procedura di riparazione completata.")
                print("Controlla i log del database per i dettagli.")
                
            except Exception as e:
                print(f"Errore: {e}")
        else:
            print("Riparazione annullata.")
    
    def backup_database(self):
        directory = input("Inserisci la directory di destinazione (o premi INVIO per il default): ")
        
        if not directory.strip():
            directory = "/tmp"
        
        try:
            cur = self.conn.cursor()
            cur.callproc('backup_logico_dati', [directory, 'catasto_backup'])
            
            print("\nBACKUP DATABASE:")
            print("Procedura di backup completata.")
            print("Controlla i log del database per i dettagli.")
            
        except Exception as e:
            print(f"Errore: {e}")
    
    def avvia(self):
        self.connetti()
        
        while True:
            self.mostra_menu_principale()
            
            try:
                scelta = int(input("\nInserire il numero dell'opzione desiderata: "))
                
                if scelta == 0:
                    print("Uscita dal programma.")
                    break
                elif scelta == 1:
                    self.genera_certificato_proprieta()
                elif scelta == 2:
                    self.genera_report_genealogico()
                elif scelta == 3:
                    self.genera_report_possessore()
                elif scelta == 4:
                    self.verifica_integrita_database()
                elif scelta == 5:
                    self.ripara_problemi_database()
                elif scelta == 6:
                    self.backup_database()
                else:
                    print("Opzione non valida. Riprova.")
                
                input("\nPremi INVIO per continuare...")
            
            except ValueError:
                print("Inserire un numero valido.")
        
        # Chiudi la connessione
        if self.conn:
            self.conn.close()

def main():
    app = CatastoApp()
    app.avvia()

if __name__ == "__main__":
    main()