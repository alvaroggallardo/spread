from fastapi import FastAPI, HTTPException, Depends, status, Header
from fastapi.responses import JSONResponse
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import Evento, SessionLocal, init_db
from app.save_events import guardar_eventos
from app.schemas import EventoSchema
from datetime import date
import os
from fastapi.middleware.cors import CORSMiddleware

SECRET_TOKEN = os.getenv("API_SECRET_TOKEN")
API_TOKEN = os.getenv("MY_API_TOKEN", "")

app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_token(x_api_token: str = Header(...)):
    expected_token = os.getenv("API_SECRET_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_SECRET_TOKEN no está configurado en el entorno."
        )
    if x_api_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )

def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid Token")

@app.get("/check-tabla-eventos", summary="Comprobar si existe la tabla eventos", description="Devuelve true/false según la existencia de la tabla en la base de datos")
def check_tabla_eventos():
    inspector = inspect(SessionLocal().bind)
    tablas = inspector.get_table_names()
    return {"tabla_eventos_existe": "eventos" in tablas}

@app.get("/crear-tabla-eventos", summary="Crear tabla eventos", description="Crea la tabla eventos si no existe. No borra datos existentes.")
def crear_tabla_eventos():
    from app.models import Base, engine
    inspector = inspect(engine)
    if "eventos" in inspector.get_table_names():
        return {"status": "Ya existe la tabla eventos"}
    Base.metadata.create_all(bind=engine)
    return {"status": "Tabla eventos creada"}

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

@app.post("/scrap", summary="Scrapear eventos")
def scrapear(security: str = Depends(check_token)):
    try:
        total_insertados = guardar_eventos()
        return {"status": "OK", "insertados": total_insertados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/borrar-eventos", summary="Vaciar la tabla eventos")
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

@app.get("/scrap-test")
def scrap_get_friendly():
    try:
        nuevos = guardar_eventos()
        return {"status": "OK", "insertados": nuevos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug", summary="Depurar estado de la base de datos")
def depurar_eventos():
    db = SessionLocal()
    try:
        eventos = db.query(Evento).all()
        resultado = [e.__dict__ for e in eventos]
        for r in resultado:
            r.pop("_sa_instance_state", None)

        # Información del motor de base de datos
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
        
@app.get("/env-check")
def env_check():
    return dict(os.environ)

@app.get("/")
def check_root():
    return {"message": "¡Estoy vivo!", "base_url": os.getenv("RAILWAY_ROOT_PATH", "/")}

# ✅ Entrada principal para Railway y local
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)

print("✅ FastAPI app cargada")
print("📌 Rutas disponibles:")
for route in app.routes:
    print(route.path)
