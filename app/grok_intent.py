import os
import re
import json
import requests


# ----------------------------------------------------
#   EXTRACTOR DE JSON — IMPRESCINDIBLE PARA GROK
# ----------------------------------------------------
def extraer_json(texto):
    # 1) Detecta bloque ```json ... ```
    m = re.search(r"```json\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if m:
        return m.group(1)

    # 2) Detecta cualquier bloque { ... }
    m = re.search(r"(\{.*\})", texto, re.DOTALL)
    if m:
        return m.group(1)

    return None


# ----------------------------------------------------
#   PARSER DE INTENCIÓN
# ----------------------------------------------------
def interpretar_pregunta_grok(pregunta):
    key = os.getenv("GROK_API_KEY")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "grok-4-latest",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un parser que convierte una consulta humana en un JSON "
                    "con los campos: ciudad, interior, infantil, disciplina, fecha_inicio, fecha_fin. "
                    "NO respondas nada más. Devuelve SOLO JSON válido."
                )
            },
            {"role": "user", "content": pregunta}
        ],
        "stream": False,
        "temperature": 0
    }

    r = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers=headers,
        json=body
    )

    try:
        r.raise_for_status()
    except Exception:
        return {"error": "Grok error", "http_status": r.status_code, "body": r.text}

    data = r.json()
    contenido = data["choices"][0]["message"]["content"]

    # Extraer JSON
    json_text = extraer_json(contenido)

    if not json_text:
        return {"error": "JSON inválido", "raw": contenido}

    try:
        return json.loads(json_text)
    except Exception as e:
        return {"error": "JSON inválido", "detalle": str(e), "raw": json_text}


# ----------------------------------------------------
#   GENERADOR DE RESPUESTA NATURAL
# ----------------------------------------------------
def llamar_grok_para_respuesta(prompt):
    key = os.getenv("GROK_API_KEY")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "grok-beta",
        "messages": [
            {"role": "system", "content": "Responde en lenguaje natural, elegante y claro."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.4
    }

    r = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=body)

    try:
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "⚠️ Error generando respuesta con Grok."
