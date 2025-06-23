import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_engine():
    if "DATABASE_URL" not in os.environ:
        raise RuntimeError("❌ VARIABLE DE ENTORNO DATABASE_URL NO DEFINIDA")
    url = os.environ["DATABASE_URL"]
    print("✅ Conectando a base de datos:", url)
    return create_engine(url)

# Engine y sesión se generan al primer uso
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


