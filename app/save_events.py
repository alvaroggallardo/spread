from app.models import Evento, SessionLocal, init_db
from datetime import datetime
from sqlalchemy import and_

def parse_date_safe(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%d/%m/%Y")
        except Exception:
            return None
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return None

def evento_ya_existe(db, ev):
    return db.query(Evento).filter(
        and_(
            Evento.evento == ev.get("evento"),
            Evento.fecha == parse_date_safe(ev.get("fecha")),
            Evento.lugar == ev.get("lugar")
        )
    ).first() is not None

def guardar_eventos(scrapers=None):
    init_db()
    db = SessionLocal()

    if scrapers is None:
        from app.script_scraping import get_events_gijon, get_events_oviedo, get_events_mieres
        scrapers = [
            #get_events_gijon, 
            #get_events_oviedo, 
            get_events_mieres
            ]

    nuevos = 0
    for scraper in scrapers:
        eventos = scraper()
        for ev in eventos:
            if not evento_ya_existe(db, ev):
                nuevo = Evento(
                    fuente=ev.get("fuente"),
                    evento=ev.get("evento"),
                    fecha=parse_date_safe(ev.get("fecha")),
                    fecha_fin=parse_date_safe(ev.get("fecha_fin")) if "fecha_fin" in ev else None,
                    hora=ev.get("hora"),
                    lugar=ev.get("lugar"),
                    link=ev.get("link"),
                    disciplina=ev.get("disciplina", None)
                )
                db.add(nuevo)
                nuevos += 1

    db.commit()
    db.close()
    return nuevos
