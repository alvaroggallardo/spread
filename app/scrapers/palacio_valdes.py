"""
Scraper para eventos - Teatro Palacio Valdes (Aviles)
Procesa el calendario ICS oficial
"""

from app.scrapers.base import *
from datetime import datetime
from urllib.parse import quote_plus


def get_events_teatro_palacio_valdes(months_ahead=6, only_future=True):
    url = "https://teatropalaciovaldes.es/?ical=1"
    events = []

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/calendar,text/plain,*/*;q=0.8",
        })

        resp = session.get(url, timeout=30)
        resp.raise_for_status()

        ics_content = resp.text

        temp_path = "/tmp/teatro_palacio_valdes.ics"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(ics_content)

        events = _process_ics_teatro(temp_path, months_ahead, only_future)

    except Exception as e:
        print("Error descargando ICS Teatro Palacio Valdes:", e)

    return events


def _process_ics_teatro(ics_path, months_ahead=6, only_future=True):
    events = []
    seen = set()

    hoy = datetime.now().date()

    try:
        from dateutil.relativedelta import relativedelta
        fecha_limite = hoy + relativedelta(months=months_ahead)
    except Exception:
        fecha_limite = hoy

    with open(ics_path, "r", encoding="utf-8") as f:
        ics_content = f.read()

    cal = Calendar(ics_content)

    for ev in cal.events:

        title = ev.name or "Sin titulo"
        link = getattr(ev, "url", None) or "https://teatropalaciovaldes.es"
        uid = getattr(ev, "uid", "no-uid")

        start_dt = ev.begin.datetime if ev.begin else None
        end_dt = ev.end.datetime if ev.end else None

        if not start_dt:
            continue

        # normalizar a naive para evitar conflictos timezone
        if start_dt.tzinfo:
            start_dt = start_dt.replace(tzinfo=None)
        if end_dt and end_dt.tzinfo:
            end_dt = end_dt.replace(tzinfo=None)

        unique_key = uid + "_" + start_dt.isoformat()
        if unique_key in seen:
            continue
        seen.add(unique_key)

        if only_future:
            if end_dt:
                if end_dt.date() < hoy:
                    continue
            else:
                if start_dt.date() < hoy:
                    continue

        if start_dt.date() > fecha_limite:
            continue

        hora = start_dt.strftime("%H:%M")

        categorias_raw = getattr(ev, "categories", None)
        if categorias_raw:
            if isinstance(categorias_raw, list):
                categorias = ", ".join(categorias_raw)
            else:
                categorias = str(categorias_raw)
        else:
            categorias = ""

        disciplina = categorias or inferir_disciplina(title)

        lugar_txt = "Teatro Palacio Valdes, Aviles"
        lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar_txt)}", "{lugar_txt}")'

        events.append({
            "fuente": "TeatroPalacioValdes",
            "evento": title,
            "fecha": start_dt,
            "fecha_fin": end_dt,
            "hora": hora,
            "lugar": lugar,
            "link": link,
            "disciplina": disciplina
        })

    print(f"Total eventos Teatro Palacio Valdes: {len(events)}")
    return events
