"""
Scraper para eventos de Mieres desde calendario ICS.
"""

import requests
from app.scrapers.base import Calendar, inferir_disciplina, quote_plus


def get_events_mieres():
    """
    Obtiene eventos de Mieres desde su calendario ICS.
    
    Returns:
        list: Lista de diccionarios con información de eventos
    """
    url = "https://www.mieres.es/eventos/?ical=1"
    events = []

    response = requests.get(url)
    cal = Calendar(response.text)

    for idx, event in enumerate(cal.events):
        title = event.name or "Sin título"
        link = event.url if event.url else "https://www.mieres.es/eventos/"
        lugar = event.location or "Mieres"

        # La librería ics devuelve start/end como datetime aware (con zona horaria)
        start_dt = event.begin
        if start_dt is not None:
            fecha_evento = start_dt.datetime
            hora_text = fecha_evento.strftime("%H:%M")
        else:
            fecha_evento = None
            hora_text = ""

        disciplina = inferir_disciplina(title)

        # ✅ Evitar duplicados
        if any(ev["link"] == link for ev in events):
            print(f"🔁 Evento duplicado saltado: {title}")
            continue

        events.append({
            "fuente": "Mieres",
            "evento": title,
            "fecha": fecha_evento,
            "hora": hora_text,
            "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
            "link": link,
            "disciplina": disciplina
        })

        print(f"✅ [{idx}] {title} -> {fecha_evento} {hora_text}")

    print(f"🎉 Total eventos Mieres (ICS): {len(events)}")

    return events
