# save_events.py

from app.script_scraping import obtener_eventos
from app.models import Evento, SessionLocal, init_db

def guardar_eventos():
    init_db()
    db = SessionLocal()
    eventos = obtener_eventos()
    for ev in eventos:
        nuevo = Evento(
            fuente=ev.get("fuente"),
            evento=ev.get("evento"),
            fecha=ev.get("fecha"),
            fecha_fin=ev.get("fecha_fin"),
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
