"""
Scraper para eventos de Aviles Comarca desde calendario ICS.
"""

import requests
from app.scrapers.base import Calendar, inferir_disciplina, quote_plus


def get_events_aviles():
    url = "https://avilescomarca.info/?ical=1"
    events = []

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        cal = Calendar(response.text)

        for idx, event in enumerate(cal.events):
            title = event.name or "Sin titulo"
            link = event.url if event.url else "https://avilescomarca.info/que-hacer/calendario-de-eventos/"
            lugar = event.location or "Aviles"

            start_dt = event.begin
            if start_dt:
                fecha_evento = start_dt.datetime
                hora_text = fecha_evento.strftime("%H:%M")
            else:
                fecha_evento = None
                hora_text = ""

            disciplina = inferir_disciplina(title)

            # Evitar duplicados
            if any(ev["link"] == link for ev in events):
                continue

            events.append({
                "fuente": "Aviles",
                "evento": title,
                "fecha": fecha_evento,
                "hora": hora_text,
                "lugar": '=HYPERLINK("https://www.google.com/maps/search/?api=1&query={}", "{}")'.format(
                    quote_plus(lugar), lugar
                ),
                "link": link,
                "disciplina": disciplina
            })

    except Exception as e:
        print("Error en Aviles (ICS): {}".format(e))

    print("Total eventos Aviles (ICS): {}".format(len(events)))
    return events
