import os
import json
import requests

GROK_API_KEY = os.getenv("GROK_API_KEY")

def interpretar_pregunta_grok(pregunta: str):
    """
    Llama al modelo Grok para interpretar intención del usuario.
    Devuelve siempre un JSON con:
    - ciudad
    - interior (True/False)
    - infantil (True/False)
    - disciplina
    - fecha_inicio
    - fecha_fin
    - resumen_usuario
    """

    url = "https://api.x.ai/v1/chat/completions"

    system_prompt = """
Eres un analizador de intención para un sistema de recomendación de eventos.

Debes interpretar la frase del usuario y devolver SIEMPRE un JSON válido con esta estructura exacta:

{
  "ciudad": "Gijón | Oviedo | Avilés | Asturias | null",
  "interior": true/false/null,
  "infantil": true/false/null,
  "disciplina": "música | deporte | talleres | conferencias | fiestas | null",
  "fecha_inicio": "YYYY-MM-DD | null",
  "fecha_fin": "YYYY-MM-DD | null",
  "resumen_usuario": "breve frase explicando lo que pide"
}

Si el usuario no da un dato, pon null.
NO inventes fechas ni eventos.
"""

    payload = {
        "model": "grok-2-latest",
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pregunta}
        ]
    }

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()

    contenido = r.json()["choices"][0]["message"]["content"]

    # Grok devuelve texto, lo convertimos a JSON
    try:
        return json.loads(contenido)
    except:
        return {"error": "No se pudo parsear respuesta de Grok", "raw": contenido}
