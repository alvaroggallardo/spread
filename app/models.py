import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_engine():
    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        print("✅ Usando PostgreSQL:", db_url)
        return create_engine(db_url)
    
    # Modo fallback local si Railway no inyecta correctamente
    print("⚠️ DATABASE_URL no está disponible. Usando SQLite local temporalmente.")
    
    print("🔎 ENTORNO DISPONIBLE:")
    for k, v in os.environ.items():
        print(f"{k} = {v}")
    
    return create_engine("sqlite:///eventos.db")

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Evento(Base):
    __tablename__ = "eventos"

    id = Column(Integer, primary_key=True)
    fuente = Column(String)
    evento = Column(String)
    fecha = Column(DateTime)
    fecha_fin = Column(DateTime, nullable=True)
    hora = Column(String)
    lugar = Column(String)
    link = Column(String)
    disciplina = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)
