from app.script_scraping import obtener_eventos
from app.models import Evento, SessionLocal, init_db
from datetime import datetime
from sqlalchemy import and_

def parse_date_safe(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(value, "%d/%m/%Y") if isinstance(value, str) else None
    except Exception:
        return None

def evento_ya_existe(db, ev):
    return db.query(Evento).filter(
        and_(
            Evento.evento == ev.get("evento"),
            Evento.fecha == parse_date_safe(ev.get("fecha")),
            Evento.lugar == ev.get("lugar")
        )
    ).first() is not None

def guardar_eventos(fecha_objetivo=None):
    init_db()
    db = SessionLocal()

    eventos = obtener_eventos(fecha_objetivo)
    
    nuevos = 0
    for ev in eventos:
        if not evento_ya_existe(db, ev):
            nuevo = Evento(
                fuente=ev.get("fuente"),
                evento=ev.get("evento"),
                fecha=parse_date_safe(ev.get("fecha")),
                fecha_fin=parse_date_safe(ev.get("fecha_fin")),
                hora=ev.get("hora"),
                lugar=ev.get("lugar"),
                link=ev.get("link"),
                disciplina=ev.get("disciplina")
            )
            db.add(nuevo)
            nuevos += 1

    db.commit()
    db.close()
    return nuevos
