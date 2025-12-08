import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base

PG_CONNECTION_URL = os.getenv(
    "DATABASE_URL",
    "postgres://postgres:z8hs_J5VCEInzE~yM4~o4sM86wtvwfVh@shortline.proxy.rlwy.net:46990/railway"
)

DATABASE_URL = PG_CONNECTION_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL)
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
    crear_columna_vector()

def crear_columna_vector():
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE eventos
            ADD COLUMN IF NOT EXISTS embedding vector(1536);
        """))
        conn.commit()
