import os
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

@app.get("/scrap-test")
def scrap_get_friendly():
    return actualizar_eventos()

@app.get("/debug")
def depurar_eventos():
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
            "eventos_muestra": resultado  # Puedes limitar si quieres
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

# ✅ Entrada principal para Railway y local
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
