# main.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.models import Evento, SessionLocal, init_db
from app.save_events import guardar_eventos

app = FastAPI()
init_db()

@app.get("/eventos")
def obtener_eventos():
    db = SessionLocal()
    eventos = db.query(Evento).all()
    resultado = [e.__dict__ for e in eventos]
    for r in resultado:
        r.pop("_sa_instance_state", None)
    db.close()
    return JSONResponse(content=resultado)

@app.post("/scrap")
def actualizar_eventos():
    guardar_eventos()
    return {"message": "Eventos actualizados"}

@app.get("/debug")
def depurar_eventos():
    import os
    from app.models import Evento

    db = SessionLocal()
    try:
        eventos = db.query(Evento).all()
        resultado = [e.__dict__ for e in eventos]
        for r in resultado:
            r.pop("_sa_instance_state", None)
        return {
            "directorio_actual": os.getcwd(),
            "archivo_eventos_db_existe": os.path.exists("eventos.db"),
            "total_eventos": len(resultado),
            "eventos_muestra": resultado  # ← ahora muestra todos
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()
