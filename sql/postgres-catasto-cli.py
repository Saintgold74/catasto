import psycopg2
import sys
from typing import List, Dict

class CatastoManager:
    def __init__(self, dbname='catasto_storico', user='postgres', password='Markus74'):
        self.conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host='localhost'
        )
        self.conn.set_session(autocommit=False)

    def registra_proprieta(self, comune: str, numero_partita: int, data_impianto: str, 
                            possessori: List[Dict], immobili: List[Dict]):
        try:
            with self.conn.cursor() as cur:
                # Inizia transazione
                cur.execute('BEGIN')

                # Inserisci partita
                cur.execute("""
                    INSERT INTO catasto.partita 
                    (comune_nome, numero_partita, tipo, data_impianto, stato) 
                    VALUES (%s, %s, 'principale', %s, 'attiva') 
                    RETURNING id
                """, (comune, numero_partita, data_impianto))
                partita_id = cur.fetchone()[0]

                # Inserisci possessori
                for possessore in possessori:
                    # Inserisci o trova possessore esistente
                    cur.execute("""
                        INSERT INTO catasto.possessore 
                        (comune_nome, nome_completo, cognome_nome, attivo) 
                        VALUES (%s, %s, %s, true)
                        ON CONFLICT (nome_completo) DO NOTHING
                        RETURNING id
                    """, (comune, possessore['nome_completo'], 
                          possessore['nome_completo'].split()[0]))
                    
                    result = cur.fetchone()
                    if result:
                        possessore_id = result[0]
                        
                        # Collega possessore alla partita
                        cur.execute("""
                            INSERT INTO catasto.partita_possessore 
                            (partita_id, possessore_id, tipo_partita, titolo, quota)
                            VALUES (%s, %s, 'principale', 'proprietà esclusiva', %s)
                        """, (partita_id, possessore_id, 
                              possessore.get('quota')))

                # Inserisci immobili
                for immobile in immobili:
                    # Trova o crea la località
                    cur.execute("""
                        INSERT INTO catasto.localita 
                        (comune_nome, nome, tipo) 
                        VALUES (%s, %s, 'regione')
                        ON CONFLICT (comune_nome, nome) DO NOTHING
                        RETURNING id
                    """, (comune, immobile['localita']))
                    
                    result = cur.fetchone()
                    localita_id = result[0] if result else cur.fetchone()[0]

                    # Inserimento immobile
                    cur.execute("""
                        INSERT INTO catasto.immobile 
                        (partita_id, localita_id, natura, classificazione)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        partita_id, 
                        localita_id, 
                        immobile['natura'], 
                        immobile.get('classificazione')
                    ))

                # Conferma transazione
                self.conn.commit()
                return partita_id

        except Exception as e:
            # Annulla transazione in caso di errore
            self.conn.rollback()
            raise e

    def cerca_proprieta(self, comune=None, numero_partita=None):
        """
        Ricerca proprietà con filtri opzionali
        """
        try:
            with self.conn.cursor() as cur:
                query = """
                SELECT 
                    p.id, 
                    p.comune_nome, 
                    p.numero_partita, 
                    p.data_impianto,
                    string_agg(pos.nome_completo, ', ') AS possessori,
                    COUNT(i.id) AS num_immobili
                FROM catasto.partita p
                LEFT JOIN catasto.partita_possessore pp ON p.id = pp.partita_id
                LEFT JOIN catasto.possessore pos ON pp.possessore_id = pos.id
                LEFT JOIN catasto.immobile i ON p.id = i.partita_id
                WHERE 
                    (%s IS NULL OR p.comune_nome = %s) AND
                    (%s IS NULL OR p.numero_partita = %s)
                GROUP BY p.id, p.comune_nome, p.numero_partita, p.data_impianto
                """
                cur.execute(query, (comune, comune, numero_partita, numero_partita))
                return cur.fetchall()

        except Exception as e:
            print(f"Errore durante la ricerca: {e}")
            return []

    def genera_certificato_proprieta(self, partita_id):
        """
        Genera un certificato dettagliato per una specifica proprietà
        """
        try:
            with self.conn.cursor() as cur:
                # Query dettagliata per ottenere tutti i dati della proprietà
                cur.execute("""
                    SELECT 
                        p.id, 
                        p.comune_nome, 
                        p.numero_partita, 
                        p.data_impianto,
                        p.stato,
                        string_agg(DISTINCT pos.nome_completo, ', ') AS possessori,
                        json_agg(
                            json_build_object(
                                'natura', i.natura,
                                'localita', l.nome,
                                'classificazione', i.classificazione
                            )
                        ) AS immobili
                    FROM catasto.partita p
                    LEFT JOIN catasto.partita_possessore pp ON p.id = pp.partita_id
                    LEFT JOIN catasto.possessore pos ON pp.possessore_id = pos.id
                    LEFT JOIN catasto.immobile i ON p.id = i.partita_id
                    LEFT JOIN catasto.localita l ON i.localita_id = l.id
                    WHERE p.id = %s
                    GROUP BY p.id
                """, (partita_id,))
                
                return cur.fetchone()

        except Exception as e:
            print(f"Errore durante la generazione del certificato: {e}")
            return None

def menu_interattivo():
    """
    Menu a riga di comando per interagire con il sistema catastale
    """
    manager = CatastoManager()

    while True:
        print("\n--- Sistema Catastale ---")
        print("1. Registra Nuova Proprietà")
        print("2. Cerca Proprietà")
        print("3. Genera Certificato Proprietà")
        print("4. Esci")
        
        scelta = input("Seleziona un'opzione: ")

        if scelta == '1':
            # Input dati proprietà
            comune = input("Comune: ")
            numero_partita = int(input("Numero Partita: "))
            data_impianto = input("Data Impianto (YYYY-MM-DD): ")

            # Input possessori
            possessori = []
            while True:
                nome = input("Nome Completo Possessore (o INVIO per terminare): ")
                if not nome:
                    break
                quota = input("Quota (opzionale): ") or None
                possessori.append({
                    'nome_completo': nome,
                    'quota': quota
                })

            # Input immobili
            immobili = []
            while True:
                natura = input("Natura Immobile (o INVIO per terminare): ")
                if not natura:
                    break
                localita = input("Località: ")
                classificazione = input("Classificazione (opzionale): ") or None
                immobili.append({
                    'natura': natura,
                    'localita': localita,
                    'classificazione': classificazione
                })

            try:
                partita_id = manager.registra_proprieta(
                    comune, numero_partita, data_impianto, 
                    possessori, immobili
                )
                print(f"Proprietà registrata con successo. ID Partita: {partita_id}")
            except Exception as e:
                print(f"Errore durante la registrazione: {e}")

        elif scelta == '2':
            # Ricerca proprietà
            comune = input("Comune (opzionale): ") or None
            numero_partita = input("Numero Partita (opzionale): ") or None
            
            risultati = manager.cerca_proprieta(comune, numero_partita)
            
            print("\nRisultati Ricerca:")
            for riga in risultati:
                print(f"ID: {riga[0]}, Comune: {riga[1]}, Numero Partita: {riga[2]}, "
                      f"Data Impianto: {riga[3]}, Possessori: {riga[4]}, Num. Immobili: {riga[5]}")

        elif scelta == '3':
            # Genera certificato
            partita_id = int(input("Inserisci ID Partita: "))
            certificato = manager.genera_certificato_proprieta(partita_id)
            
            if certificato:
                print("\n--- CERTIFICATO PROPRIETÀ ---")
                print(f"ID: {certificato[0]}")
                print(f"Comune: {certificato[1]}")
                print(f"Numero Partita: {certificato[2]}")
                print(f"Data Impianto: {certificato[3]}")
                print(f"Stato: {certificato[4]}")
                print(f"Possessori: {certificato[5]}")
                print("Immobili:")
                for immobile in certificato[6]:
                    print(f"  - Natura: {immobile['natura']}, "
                          f"Località: {immobile['localita']}, "
                          f"Classificazione: {immobile['classificazione']}")
            else:
                print("Certificato non trovato.")

        elif scelta == '4':
            break

        else:
            print("Opzione non valida.")

if __name__ == "__main__":
    menu_interattivo()
