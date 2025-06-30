# app/schemas.py

from pydantic import BaseModel
from typing import Optional
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


