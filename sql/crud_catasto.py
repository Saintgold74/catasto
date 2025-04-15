# Importazioni necessarie
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# Creazione della base ORM
Base = declarative_base()

# Configurazione della connessione a PostgreSQL
DATABASE_URL = "postgresql+psycopg2://postgres:Markus74@localhost:5432/catasto_storico"

# Creazione del motore di connessione
engine = create_engine(DATABASE_URL, echo=False)

# Creazione della sessione
SessionLocal = sessionmaker(bind=engine)

# Definizione del modello per la tabella "immobili"
class Immobile(Base):
    __tablename__ = 'immobili'
    
    # Definizione delle colonne con tipi e vincoli
    id = Column(Integer, primary_key=True, index=True)
    indirizzo = Column(String(255), nullable=False)
    superficie = Column(Float, nullable=False)
    valore = Column(Float, nullable=True)
    data_registrazione = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Immobile(id={self.id}, indirizzo='{self.indirizzo}', superficie={self.superficie}, valore={self.valore})>"

# Creazione delle tabelle nel database (se non già esistenti)
Base.metadata.create_all(bind=engine)

# Funzioni CRUD

def create_immobile(indirizzo: str, superficie: float, valore: float = None):
    """Crea un nuovo record nella tabella immobili."""
    session = SessionLocal()
    nuovo_immobile = Immobile(indirizzo=indirizzo, superficie=superficie, valore=valore)
    session.add(nuovo_immobile)
    session.commit()
    session.refresh(nuovo_immobile)
    session.close()
    return nuovo_immobile

def read_immobile(immobile_id: int):
    """Recupera un record dalla tabella immobili in base al suo ID."""
    session = SessionLocal()
    immobile = session.query(Immobile).filter(Immobile.id == immobile_id).first()
    session.close()
    return immobile

def update_immobile(immobile_id: int, indirizzo: str = None, superficie: float = None, valore: float = None):
    """Aggiorna i campi di un immobile esistente."""
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
    """Elimina un record dalla tabella immobili."""
    session = SessionLocal()
    immobile = session.query(Immobile).filter(Immobile.id == immobile_id).first()
    if immobile is None:
        session.close()
        raise ValueError(f"Nessun immobile trovato con ID {immobile_id}")
    
    session.delete(immobile)
    session.commit()
    session.close()
    return f"Immobile con ID {immobile_id} eliminato con successo."

# Funzione principale per testare le operazioni CRUD
if __name__ == "__main__":
    # Creazione di un nuovo immobile
    immobile_creato = create_immobile("Via Roma 10, Torino", 120.5, 250000.0)
    print("Creato:", immobile_creato)
    
    # Lettura dell'immobile appena creato
    immobile_lettura = read_immobile(immobile_creato.id)
    print("Letto:", immobile_lettura)
    
    # Aggiornamento dell'immobile
    immobile_aggiornato = update_immobile(immobile_creato.id, valore=260000.0)
    print("Aggiornato:", immobile_aggiornato)
    
    # Eliminazione dell'immobile
    risultato_delete = delete_immobile(immobile_creato.id)
    print(risultato_delete)
