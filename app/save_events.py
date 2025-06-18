# save_events.py

from app.script_scraping import obtener_eventos
from app.models import Evento, SessionLocal, init_db
from datetime import datetime

#~Convierte en date la fecha de los eventos para meterlos en la bbdd
def parse_date_safe(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(value, "%d/%m/%Y") if isinstance(value, str) else None
    except Exception:
        return None

def guardar_eventos():
    
    init_db()
    db = SessionLocal()
    
    eventos = obtener_eventos()
    
    for ev in eventos:
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
    db.commit()
    db.close()

if __name__ == "__main__":
    guardar_eventos()
