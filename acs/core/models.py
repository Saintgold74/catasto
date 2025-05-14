from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, CHAR
from sqlalchemy.orm import relationship # Attualmente commentato, ma pronto per essere usato
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean # Assicurati che Boolean sia importato se lo usi per is_active in sessione
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship 
from .models import TipoDocumento # Assicurati che TipoDocumento sia definito

# Importa la Base dal tuo db_manager.py modificato
from .db_manager import Base # Assumendo che Base sia definita ed esportata da db_manager.py

class Comune(Base):
    __tablename__ = "comune" # Nome esatto della tabella nel DB

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False, unique=True)
    provincia = Column(String(100), nullable=False)
    regione = Column(String(100), nullable=False)
    data_creazione = Column(DateTime(timezone=True), server_default=func.now())
    data_modifica = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Esempio di relazione (da decommentare e adattare se definisci Sezione.comune)
    # sezioni = relationship("Sezione", back_populates="comune")

class RuoloUtente(Base):
    __tablename__ = "ruoli_utente" # Verifica il nome esatto della tabella nel tuo DB

    id = Column(Integer, primary_key=True, index=True)
    nome_ruolo = Column(String(50), unique=True, nullable=False)
    descrizione = Column(Text, nullable=True)

    # Esempio di relazione inversa (da decommentare e adattare se definisci Utente.ruolo)
    # utenti = relationship("Utente", back_populates="ruolo")

class Utente(Base):
    __tablename__ = "utenti" # Nome esatto della tabella

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    nome_completo = Column(String(255))
    is_active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("ruoli_utente.id")) # FK alla tabella ruoli_utente
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    sessioni = relationship("SessioneUtente", back_populates="utente_associato", cascade="all, delete-orphan")

    # Esempio di relazione (da decommentare e adattare)
    # ruolo = relationship("RuoloUtente", back_populates="utenti")
    # audit_logs = relationship("AuditLog", foreign_keys="[AuditLog.user_id]", back_populates="utente_azione") # Nome relazione d'esempio

class AuditLog(Base): # Basato sull'ultimo \d audit_log
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("utenti.id", name="audit_log_user_id_fkey", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    action = Column(String(100), nullable=False)
    table_name = Column(String(100))
    record_id = Column(String(255))
    details = Column(Text)
    session_id = Column(String(255))
    client_ip_address = Column(String(45))
    success = Column(Boolean, default=True)

    # Esempio di relazione (da decommentare e adattare)
    # utente_azione = relationship("Utente", foreign_keys=[user_id], back_populates="audit_logs")

class Sezione(Base):
    __tablename__ = "sezioni" # Come l'avevamo definita per la creazione

    id = Column(Integer, primary_key=True, index=True)
    comune_id = Column(Integer, ForeignKey("comune.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    nome_sezione = Column(String(150), nullable=False)
    codice_sezione = Column(String(20)) # Es. 'A', 'Urbana', 'Foglio 123'
    note = Column(Text)
    data_creazione = Column(DateTime(timezone=True), server_default=func.now())
    data_modifica = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# In core/models.py
# ... (altri modelli)

class TipoDocumento(Base):
    __tablename__ = "tipi_documento" # Assicurati che il nome tabella sia corretto
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False)
    descrizione = Column(Text, nullable=True)

# Similmente per TipoImmobile, TipoPossesso, TipoVariazione
class TipoImmobile(Base):
    __tablename__ = "tipi_immobile"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False)
    descrizione = Column(Text, nullable=True)

class TipoPossesso(Base):
    __tablename__ = "tipi_possesso"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False)
    descrizione = Column(Text, nullable=True)

class TipoVariazione(Base):
    __tablename__ = "tipi_variazione"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False)
    descrizione = Column(Text, nullable=True)

class SessioneUtente(Base): # Nome della classe Python, puoi sceglierlo
    __tablename__ = "sessioni_utente" # Nome esatto della tabella nel DB
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("utenti.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(255), unique=True, nullable=False)
    client_ip_address = Column(String(45), nullable=True)
    login_time = Column(DateTime(timezone=True), server_default=func.now())
    logout_time = Column(DateTime(timezone=True), nullable=True)
    utente_associato = relationship("Utente", back_populates="sessioni") # Deve corrispondere a sessioni.back_populates

class TipoPartita(Base):
    __tablename__ = "tipi_partita" # Nome esatto della tabella come da script SQL

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False)
    descrizione = Column(Text, nullable=True)
    data_creazione = Column(DateTime(timezone=True), server_default=func.now())
    data_modifica = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())