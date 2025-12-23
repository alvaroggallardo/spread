import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.orm import sessionmaker, declarative_base

# Definimos conexión con PostgreSQL y fallback a SQLite si no está configurado
PG_CONNECTION_URL = (
    "postgresql://postgres:BMibUSldVwNseRpYBDxjvplFspYjojrq"
    "@interchange.proxy.rlwy.net:52229/railway"
)

# Si está configurada la variable de entorno DATABASE_URL, úsala. Si no, usa la URL fija. Si tampoco, SQLite
DATABASE_URL = os.getenv("DATABASE_URL", PG_CONNECTION_URL)

if not DATABASE_URL:
    print("⚠️ No se encontró DATABASE_URL, usando SQLite sin persistencia.")
    DATABASE_URL = "sqlite:///eventos.db"

print(f"✅ Usando base de datos: {DATABASE_URL}")

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

class InformeScrap(Base):
    """Modelo para almacenar informes de ejecuciones de scraping."""
    __tablename__ = "informes_scrap"

    id = Column(Integer, primary_key=True)
    fecha_ejecucion = Column(DateTime)
    duracion_segundos = Column(Integer)  # Duración total del scraping
    total_eventos = Column(Integer)  # Total de eventos procesados
    eventos_nuevos = Column(Integer)  # Eventos insertados
    eventos_duplicados = Column(Integer)  # Eventos descartados por duplicados
    scrapers_exitosos = Column(Integer)  # Número de scrapers que funcionaron
    scrapers_fallidos = Column(Integer)  # Número de scrapers que fallaron
    detalles = Column(JSON)  # Detalles por fuente: {"fuente": {"nuevos": X, "duplicados": Y, "error": "..."}}
    errores = Column(Text, nullable=True)  # Errores concatenados si los hay
    estado = Column(String)  # "exitoso", "parcial", "fallido"

def init_db():
    """Crea todas las tablas (eventos, informes_scrap) si no existen."""
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas de base de datos verificadas/creadas")


