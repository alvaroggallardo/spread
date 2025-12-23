# app/schemas.py

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class EventoSchema(BaseModel):
    id: int
    fuente: Optional[str] = None
    evento: Optional[str] = None
    fecha: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    hora: Optional[str] = None
    lugar: Optional[str] = None
    link: Optional[str] = None
    disciplina: Optional[str] = None

    class Config:
        orm_mode = True

class InformeScrapSchema(BaseModel):
    id: int
    fecha_ejecucion: datetime
    duracion_segundos: int
    total_eventos: int
    eventos_nuevos: int
    eventos_duplicados: int
    scrapers_exitosos: int
    scrapers_fallidos: int
    detalles: Dict[str, Any]
    errores: Optional[str] = None
    estado: str

    class Config:
        orm_mode = True
