import os
import requests

def interpretar_pregunta_grok(pregunta):
    key = os.getenv("GROK_API_KEY")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    body = {
        "model": "grok-4-latest",    # modelo correcto ✔
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un parser que convierte una consulta humana en un JSON "
                    "con los campos: ciudad, interior, infantil, disciplina, fecha_inicio, fecha_fin. "
                    "NO respondas nada más."
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
    except Exception as e:
        return {"error": "Grok error", "http_status": r.status_code, "body": r.text}

    data = r.json()
    # El contenido viene en:
    contenido = data["choices"][0]["message"]["content"]

    try:
        return json.loads(contenido)
    except:
        return {"error": "JSON inválido", "raw": contenido}


def llamar_grok_para_respuesta(prompt):
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
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
