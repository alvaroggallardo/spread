import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.models import Evento, SessionLocal, init_db
from app.save_events import guardar_eventos
from fastapi.encoders import jsonable_encoder
from sqlalchemy import inspect

app = FastAPI()

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

@app.get("/eventos")
def obtener_eventos():
    db = SessionLocal()
    eventos = db.query(Evento).all()
    db.close()
    return JSONResponse(content=jsonable_encoder(eventos))

@app.post("/scrap", summary="Scrapear eventos de los próximos 7 días")
def scrapear_semana():
    total_insertados = 0
    errores = []

    for i in range(7):
        fecha_objetivo = (datetime.now() + timedelta(days=i)).date()
        try:
            nuevos = guardar_eventos(fecha_objetivo)
            total_insertados += nuevos
        except Exception as e:
            errores.append(f"{fecha_objetivo}: {str(e)}")

    if errores:
        raise HTTPException(status_code=500, detail={"errores": errores, "insertados": total_insertados})
    
    return {"status": "OK", "insertados": total_insertados}

@app.delete("/borrar-eventos", summary="Vaciar la tabla eventos")
def borrar_eventos():
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
    return actualizar_eventos()

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
