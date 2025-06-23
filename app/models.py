import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_engine():
    # Railway define esta variable automáticamente
    if "RAILWAY_ENVIRONMENT" in os.environ:
        if "DATABASE_URL" not in os.environ:
            raise RuntimeError("❌ DATABASE_URL no está definida en Railway")
        url = os.environ["DATABASE_URL"]
        print("✅ Usando PostgreSQL:", url)
        return create_engine(url)
    
    # Si estamos en local
    print("⚠️ Modo local detectado, usando SQLite")
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
