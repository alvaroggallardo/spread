import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from app.model_supabase import SessionSupabase, EventoSupabase

# Modelo sin torch, funciona con ONNX automáticamente
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def generar_embeddings():
    db = SessionSupabase()

    eventos = db.query(EventoSupabase).filter(EventoSupabase.embedding == None).all()

    print("Eventos sin embedding:", len(eventos))

    for ev in eventos:
        texto = f"{ev.evento} {ev.lugar} {ev.disciplina}"
        vector = model.encode(texto)
        vector_list = vector.tolist()

        q = text("""
            UPDATE public.eventos
            SET embedding = :vec
            WHERE id = :id
        """)

        db.execute(q, {"vec": vector_list, "id": ev.id})

    db.commit()
    db.close()

    return len(eventos)
