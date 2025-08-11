from app.models import Evento, SessionLocal, init_db
from datetime import datetime, date
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
            Evento.link == ev.get("link"),
            Evento.evento == ev.get("evento"),
            Evento.fecha == parse_date_safe(ev.get("fecha")),
            Evento.lugar == ev.get("lugar")
        )
    ).first() is not None

def guardar_eventos(scrapers=None):
    init_db()
    db = SessionLocal()

    if scrapers is None:
        from app.script_scraping import (
            get_events_gijon,
            get_events_oviedo,
            get_events_mieres,
            get_events_asturiescultura,
            get_events_aviles,
            get_events_siero,
            get_events_conciertosclub,
            get_events_turismoasturias,
            get_events_laboral,
            get_events_fiestasasturias_api,
            get_events_fiestasasturias_simcal,
            get_events_camaragijon_recinto,
            get_events_laboral_actividades
        )

        tematicas = [
            "gastronomia",
            "museos",
            "fiestas",
            "cine-y-espectaculos",
            "deporte",
            "ocio-infantil",
            "rutas-y-visitas-guiadas",
            "ferias-mercados"
        ]

        scrapers = [
            #get_events_gijon,
            #get_events_oviedo,
            #get_events_mieres,
            #get_events_asturiescultura,
            #get_events_aviles,
            #get_events_siero,
            #get_events_conciertosclub,
            #lambda: get_events_turismoasturias(tematicas=tematicas),
            #get_events_laboral,
            #get_events_fiestasasturias_api,
            #get_events_fiestasasturias_simcal,
            #get_events_camaragijon_recinto,
            get_events_laboral_actividades
        ]

    nuevos = 0
    for scraper in scrapers:
        eventos = scraper()   # ✅ ahora es callable
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

