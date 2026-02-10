"""
Scraper de eventos Comarca Aviles.
Descarga y procesa un calendario ICS online.
"""

from app.scrapers.base import *
from datetime import datetime
from urllib.parse import quote_plus


def get_events_aviles(months_ahead=2, only_future=True):
    """
    Descarga el archivo ICS desde la web y lo procesa.
    """
    url = "https://avilescomarca.info/?ical=1"
    events = []

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/calendar,text/plain,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9",
            "Referer": "https://avilescomarca.info/",
        })

        resp = session.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()

        ics_content = resp.text if resp.text else resp.content.decode("utf-8", errors="ignore")

        temp_path = "/tmp/comarca_aviles_temp.ics"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(ics_content)

        events = _process_ics_file(
            temp_path,
            months_ahead=months_ahead,
            only_future=only_future
        )

    except Exception as e:
        print("Error processing Aviles ICS:", e)

    return events


def _process_ics_file(ics_path, months_ahead=2, only_future=True):
    """
    Procesa un archivo ICS local.
    """
    events = []
    seen = set()

    hoy = datetime.now().date()

    try:
        from dateutil.relativedelta import relativedelta
        fecha_limite = hoy + relativedelta(months=months_ahead)
    except Exception:
        import calendar
        year = hoy.year
        month = hoy.month + months_ahead
        if month > 12:
            year += month // 12
            month = month % 12 or 12
        day = min(hoy.day, calendar.monthrange(year, month)[1])
        fecha_limite = datetime(year, month, day).date()

    with open(ics_path, "r", encoding="utf-8") as f:
        ics_content = f.read()

    cal = Calendar(ics_content)

    inicio = datetime.combine(hoy, datetime.min.time())
    fin = datetime.combine(fecha_limite, datetime.max.time())

    for ev in cal.timeline.included(inicio, fin):
        title = ev.name or "Sin titulo"
        link = getattr(ev, "url", None) or "https://avilescomarca.info"
        uid = getattr(ev, "uid", "no-uid")

        start_dt = ev.begin.datetime
        end_dt = ev.end.datetime if ev.end else None

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

        lugar = ev.location or "Aviles, Asturias"

        is_all_day = ev.all_day
        hora_text = "" if is_all_day else start_dt.strftime("%H:%M")

        categorias_raw = getattr(ev, "categories", None)
        if categorias_raw:
            if isinstance(categorias_raw, list):
                categorias = ", ".join(categorias_raw)
            else:
                categorias = str(categorias_raw)
        else:
            categorias = ""

        if categorias:
            disciplina = categorias.split(",")[0].strip()
        else:
            disciplina = inferir_disciplina(title)

        events.append({
            "fuente": "Comarca Aviles",
            "evento": title,
            "fecha": start_dt,
            "fecha_fin": end_dt,
            "hora": hora_text,
            "lugar": '=HYPERLINK("https://www.google.com/maps/search/?api=1&query=' +
                     quote_plus(lugar) + '", "' + lugar + '")',
            "link": link,
            "disciplina": disciplina
        })

    return events


def get_events_aviles_from_file(ics_path, months_ahead=2, only_future=True):
    """
    Procesa un ICS local para pruebas.
    """
    return _process_ics_file(ics_path, months_ahead, only_future)


if __name__ == "__main__":
    eventos = get_events_aviles()
    print("Eventos encontrados:", len(eventos))

    for ev in eventos[:3]:
        print(ev["evento"], ev["fecha"])
