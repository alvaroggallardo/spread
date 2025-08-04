from fastapi import FastAPI, HTTPException, Depends, status, Header, Security
from fastapi.security import APIKeyHeader
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import Evento, SessionLocal, init_db
from app.save_events import guardar_eventos
from app.schemas import EventoSchema
from datetime import date
import os
import requests
import time

from apscheduler.schedulers.background import BackgroundScheduler

# ------------------------
# CONFIGURACIONES
# ------------------------

SECRET_TOKEN = os.getenv("API_SECRET_TOKEN")
API_TOKEN = os.getenv("MY_API_TOKEN", "")

# URL de Railway a la que quieres llamar desde tu proxy
RAILWAY_EVENTOS_URL = "https://spread-production-b053.up.railway.app/eventos"

# ------------------------
# SEGURIDAD
# ------------------------

api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)

def check_token(x_api_token: str = Security(api_key_header)):
    if not SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_SECRET_TOKEN no está configurado en el entorno."
        )
    if x_api_token != SECRET_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )

# ------------------------
# OPENAPI CUSTOMIZATION
# ------------------------

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Mi API privada",
        version="1.0.0",
        description="API protegida con token",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Token"
        }
    }

    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", []).append({"ApiKeyAuth": []})

    app.openapi_schema = openapi_schema
    return openapi_schema

app = FastAPI()
app.openapi = custom_openapi

# ------------------------
# CRON 
# ------------------------

def job_scrap():
    try:
        print("🕒 Ejecutando borrado y scrapping programado...")

        res_delete = requests.delete(
            "https://spread-production-b053.up.railway.app/borrar-eventos",
            headers={"X-API-Token": SECRET_TOKEN}
        )
        print(f"Borrar eventos: {res_delete.status_code} → {res_delete.text}")

        time.sleep(5)

        res_scrap = requests.post(
            "https://spread-production-b053.up.railway.app/scrap",
            headers={"X-API-Token": SECRET_TOKEN}
        )
        print(f"Scrap: {res_scrap.status_code} → {res_scrap.text}")

    except Exception as e:
        print("❌ Error en tarea programada:", e)
        
scheduler = BackgroundScheduler()
scheduler.add_job(
    job_scrap,
    "cron",
    day_of_week="mon",   # lunes
    hour=3,
    minute=0
)
scheduler.start()

# ------------------------
# CORS
# ------------------------

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# DB UTILS
# ------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------
# ENDPOINTS
# ------------------------

@app.get("/check-tabla-eventos", dependencies=[Depends(check_token)])
def check_tabla_eventos():
    inspector = inspect(SessionLocal().bind)
    tablas = inspector.get_table_names()
    return {"tabla_eventos_existe": "eventos" in tablas}

@app.get("/crear-tabla-eventos", dependencies=[Depends(check_token)])
def crear_tabla_eventos():
    from app.models import Base, engine
    inspector = inspect(engine)
    if "eventos" in inspector.get_table_names():
        return {"status": "Ya existe la tabla eventos"}
    Base.metadata.create_all(bind=engine)
    return {"status": "Tabla eventos creada"}

# 🚨 AHORA este endpoint ES PÚBLICO (sin Depends(check_token))
@app.get("/eventos", response_model=List[EventoSchema])
def listar_eventos(
    disciplina: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Evento)

    if disciplina:
        query = query.filter(Evento.disciplina == disciplina)
    
    if fecha_inicio and fecha_fin:
        query = query.filter(Evento.fecha.between(fecha_inicio, fecha_fin))
    elif fecha_inicio:
        query = query.filter(Evento.fecha >= fecha_inicio)
    elif fecha_fin:
        query = query.filter(Evento.fecha <= fecha_fin)
    
    return query.all()

@app.post("/scrap", dependencies=[Depends(check_token)])
def scrapear(security: str = Depends(check_token)):
    try:
        total_insertados = guardar_eventos()
        return {"status": "OK", "insertados": total_insertados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/borrar-eventos", dependencies=[Depends(check_token)])
def borrar_eventos(security: str = Depends(check_token)):
    db = SessionLocal()
    try:
        num_rows = db.query(Evento).delete()
        db.commit()
        return {"status": f"Se eliminaron {num_rows} eventos"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

@app.get("/scrap-test", dependencies=[Depends(check_token)])
def scrap_get_friendly():
    try:
        nuevos = guardar_eventos()
        return {"status": "OK", "insertados": nuevos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug", dependencies=[Depends(check_token)])
def depurar_eventos():
    db = SessionLocal()
    try:
        eventos = db.query(Evento).all()
        resultado = [e.__dict__ for e in eventos]
        for r in resultado:
            r.pop("_sa_instance_state", None)

        engine = db.get_bind()
        inspector = inspect(engine)

        return {
            "directorio_actual": os.getcwd(),
            "base_de_datos_url": str(engine.url),
            "motor_bd": engine.dialect.name,
            "esquema": inspector.default_schema_name,
            "tablas_en_bd": inspector.get_table_names(),
            "total_eventos": len(resultado),
            "eventos_muestra": resultado
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()

@app.get("/env-check", dependencies=[Depends(check_token)])
def env_check():
    return dict(os.environ)

@app.get("/")
def check_root():
    return {"message": "¡Estoy vivo!", "base_url": os.getenv("RAILWAY_ROOT_PATH", "/")}

# ---------------------------------------------------
# PROXY HACIA RAILWAY (opcional, si quieres mantenerlo)
# ---------------------------------------------------

@app.get("/proxy/eventos", dependencies=[Depends(check_token)])
def proxy_eventos():
    """
    Proxy seguro hacia Railway, usando el token guardado en el backend.
    """
    try:
        res = requests.get(
            RAILWAY_EVENTOS_URL,
            headers={"X-API-Token": SECRET_TOKEN}
        )
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Entrada principal para Railway y local
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)

print("✅ FastAPI app cargada")
print("📌 Rutas disponibles:")
for route in app.routes:
    print(route.path)
"# forzar redeploy otra vez ??" 
