from app.model_supabase import SessionSupabase, EventoSupabase
from sentence_transformers import SentenceTransformer
from sqlalchemy import func

# Modelo MiniLM (384 dimensiones)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def build_text(ev):
    fecha = ev.fecha.strftime("%Y-%m-%d") if ev.fecha else ""
    partes = [
        ev.evento or "",
        f"Disciplina: {ev.disciplina}" if ev.disciplina else "",
        f"Lugar: {ev.lugar}" if ev.lugar else "",
        f"Fecha: {fecha}",
    ]
    return " - ".join([p for p in partes if p])

def generar_embeddings(chunk_size=25):
    """Genera embeddings por lotes evitando timeouts en Railway."""
    
    db = SessionSupabase()

    # Obtener todos los eventos SIN EMBEDDING
    eventos = db.query(EventoSupabase).filter(EventoSupabase.embedding == None).all()

    total = len(eventos)
    if total == 0:
        db.close()
        return {"status": "no-new", "message": "No hay eventos pendientes"}

    print(f"🧠 Generando embeddings para {total} eventos...")

    procesados = 0

    for i in range(0, total, chunk_size):
        batch = eventos[i:i + chunk_size]

        # Construir textos
        textos = [build_text(ev) for ev in batch]

        # Generar embeddings (lista de listas)
        vectors = model.encode(textos).tolist()

        # Guardar en cada evento
        for ev, vec in zip(batch, vectors):
            ev.embedding = vec  # JSONB → OK

        db.commit()
        procesados += len(batch)

        print(f"✔ Lote {i//chunk_size + 1} procesado ({procesados}/{total})")

    db.close()

    return {
        "status": "ok",
        "total_eventos": total,
        "embeddings_generados": procesados
    }
