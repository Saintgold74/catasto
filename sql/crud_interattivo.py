from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
import sys

# Configurazione database (aggiorna DATABASE_URL con le tue credenziali)
DATABASE_URL = "postgresql+psycopg2://postgres:Markus74@localhost:5432/catasto_storico"

# Creazione base ORM e engine
Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

# Definizione del modello "Immobile"
class Immobile(Base):
    __tablename__ = 'immobili'

    id = Column(Integer, primary_key=True, index=True)
    indirizzo = Column(String(255), nullable=False)
    superficie = Column(Float, nullable=False)
    valore = Column(Float, nullable=True)
    data_registrazione = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Immobile(id={self.id}, indirizzo='{self.indirizzo}', superficie={self.superficie}, valore={self.valore})>"

# Creazione delle tabelle (se non esistono già)
Base.metadata.create_all(bind=engine)

# Funzioni CRUD
def create_immobile(indirizzo: str, superficie: float, valore: float = None):
    session = SessionLocal()
    nuovo_immobile = Immobile(indirizzo=indirizzo, superficie=superficie, valore=valore)
    session.add(nuovo_immobile)
    session.commit()
    session.refresh(nuovo_immobile)
    session.close()
    return nuovo_immobile

def read_immobile(immobile_id: int):
    session = SessionLocal()
    immobile = session.query(Immobile).filter(Immobile.id == immobile_id).first()
    session.close()
    return immobile

def update_immobile(immobile_id: int, indirizzo: str = None, superficie: float = None, valore: float = None):
    session = SessionLocal()
    immobile = session.query(Immobile).filter(Immobile.id == immobile_id).first()
    if immobile is None:
        session.close()
        raise ValueError(f"Nessun immobile trovato con ID {immobile_id}")
    if indirizzo is not None:
        immobile.indirizzo = indirizzo
    if superficie is not None:
        immobile.superficie = superficie
    if valore is not None:
        immobile.valore = valore
    session.commit()
    session.refresh(immobile)
    session.close()
    return immobile

def delete_immobile(immobile_id: int):
    session = SessionLocal()
    immobile = session.query(Immobile).filter(Immobile.id == immobile_id).first()
    if immobile is None:
        session.close()
        raise ValueError(f"Nessun immobile trovato con ID {immobile_id}")
    session.delete(immobile)
    session.commit()
    session.close()
    return f"Immobile con ID {immobile_id} eliminato con successo."

# Funzione per visualizzare il menu
def mostra_menu():
    print("\n--- Menu Operazioni CRUD ---")
    print("1. Crea un nuovo immobile")
    print("2. Leggi i dati di un immobile")
    print("3. Aggiorna un immobile")
    print("4. Elimina un immobile")
    print("5. Esci")

# Funzione principale per l'interfaccia interattiva
def main():
    while True:
        mostra_menu()
        scelta = input("Seleziona l'operazione (1-5): ").strip()

        if scelta == '1':
            print("\n--- Creazione di un nuovo immobile ---")
            indirizzo = input("Inserisci l'indirizzo: ").strip()
            try:
                superficie = float(input("Inserisci la superficie: ").strip())
            except ValueError:
                print("Errore: la superficie deve essere un valore numerico.")
                continue
            valore_input = input("Inserisci il valore (premi invio se non disponibile): ").strip()
            valore = None
            if valore_input:
                try:
                    valore = float(valore_input)
                except ValueError:
                    print("Errore: il valore deve essere numerico.")
                    continue

            immobile = create_immobile(indirizzo, superficie, valore)
            print("Creato:", immobile)

        elif scelta == '2':
            print("\n--- Lettura di un immobile ---")
            try:
                immobile_id = int(input("Inserisci l'ID dell'immobile: ").strip())
            except ValueError:
                print("Errore: l'ID deve essere un numero intero.")
                continue
            immobile = read_immobile(immobile_id)
            if immobile:
                print("Dati immobile:", immobile)
            else:
                print(f"Nessun immobile trovato con ID {immobile_id}")

        elif scelta == '3':
            print("\n--- Aggiornamento di un immobile ---")
            try:
                immobile_id = int(input("Inserisci l'ID dell'immobile da aggiornare: ").strip())
            except ValueError:
                print("Errore: l'ID deve essere un numero intero.")
                continue

            print("Premi invio se non vuoi aggiornare un campo.")
            indirizzo = input("Nuovo indirizzo: ").strip() or None
            superficie_input = input("Nuova superficie: ").strip()
            superficie = None
            if superficie_input:
                try:
                    superficie = float(superficie_input)
                except ValueError:
                    print("Errore: la superficie deve essere numerica.")
                    continue
            valore_input = input("Nuovo valore: ").strip()
            valore = None
            if valore_input:
                try:
                    valore = float(valore_input)
                except ValueError:
                    print("Errore: il valore deve essere numerico.")
                    continue
            try:
                immobile = update_immobile(immobile_id, indirizzo, superficie, valore)
                print("Aggiornato:", immobile)
            except ValueError as e:
                print(e)

        elif scelta == '4':
            print("\n--- Eliminazione di un immobile ---")
            try:
                immobile_id = int(input("Inserisci l'ID dell'immobile da eliminare: ").strip())
            except ValueError:
                print("Errore: l'ID deve essere un numero intero.")
                continue
            try:
                risultato = delete_immobile(immobile_id)
                print(risultato)
            except ValueError as e:
                print(e)

        elif scelta == '5':
            print("Uscita dall'applicazione. Arrivederci!")
            sys.exit(0)

        else:
            print("Scelta non valida. Riprova.")

if __name__ == "__main__":
    main()
