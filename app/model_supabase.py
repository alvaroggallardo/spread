import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from pgvector.sqlalchemy import Vector  # <--- IMPORTANTE

SUPABASE_URL = os.getenv(
    "SUPABASE_DB_URL",
    "postgresql://postgres.xemfivtbqpmnzjhwsovj:TU_PASSWORD@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"
)

SUPABASE_URL = SUPABASE_URL.replace("postgres://", "postgresql://")

BaseSupabase = declarative_base()
engine_supabase = create_engine(SUPABASE_URL)
SessionSupabase = sessionmaker(autocommit=False, autoflush=False, bind=engine_supabase)

class EventoSupabase(BaseSupabase):
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

    # Mapeo CORRECTO a pgvector
    embedding = Column(Vector(384))
