"""
Scraper para eventos - Jarascada.
"""

from app.scrapers.base import *

def get_events_jarascada(months_ahead=2, only_future=True, offline_path=None):
    """
    Mes actual + months_ahead. Devuelve misma estructura que Mieres.
    Si el servidor devuelve 403, intenta Selenium.
    Si no hay suerte, como último recurso puede leer un ICS local (offline_path).
    """
    base = "https://www.jarascada.es/feed/my-calendar-ics/"
    events = []
    seen = set()
    hoy = datetime.now().date()

    # --- sesión HTTP con cabeceras "normales"
    session = requests.Session()
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    session.headers.update({
        "User-Agent": UA,
        "Accept": "text/calendar,text/plain,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.jarascada.es/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        # "DNT": "1",  # opcional
    })

    def add_months(y, m, delta):
        m2 = m + delta
        y2 = y + (m2 - 1) // 12
        m2 = ((m2 - 1) % 12) + 1
        return y2, m2

    def consume_calendar(cal):
        nonlocal events, seen
        for ev in cal.events:
            title = ev.name or "Sin título"
            link = getattr(ev, "url", None) or "https://www.jarascada.es/eventos/"
            uid = getattr(ev, "uid", None)
            key = (uid, link)
            if key in seen:
                continue
            seen.add(key)

            lugar = ev.location or "Asturias"
            start_dt = getattr(ev, "begin", None)
            if start_dt:
                fecha_evento = start_dt.datetime
                hora_text = "" if getattr(ev, "all_day", False) else fecha_evento.strftime("%H:%M")
            else:
                fecha_evento = None
                hora_text = ""

            if only_future and fecha_evento and fecha_evento.date() < hoy:
                continue

            disciplina = inferir_disciplina(title)

            events.append({
                "fuente": "Jarascada",
                "evento": title,
                "fecha": fecha_evento,
                "hora": hora_text,
                "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
                "link": link,
                "disciplina": disciplina
            })

    # --- bucle mes a mes
    y0, m0 = hoy.year, hoy.month
    for i in range(months_ahead + 1):
        y, m = add_months(y0, m0, i)
        url = f"{base}?time=month&yr={y}&month={m}&dy=1"

        ics_text = None

        # 1) Intento con requests + headers
        for attempt in range(2):
            try:
                resp = session.get(url, timeout=25, allow_redirects=True)
                if resp.status_code == 403:
                    raise requests.HTTPError("403 Forbidden")
                resp.raise_for_status()
                enc = resp.encoding or "utf-8"
                ics_text = resp.text if resp.text else resp.content.decode(enc, errors="ignore")
                break
            except Exception as e:
                print(f"⚠️ Intento {attempt+1} falló en {url}: {e}")
                time.sleep(1.2)

        # 2) Fallback Selenium si seguimos sin texto
        if ics_text is None:
            try:
                from selenium.webdriver.common.by import By  # import local para no romper tu entorno si no usas Selenium
                driver = get_selenium_driver(headless=True)
                driver.get(url)
                time.sleep(2.5)
                try:
                    pre = driver.find_element(By.TAG_NAME, "pre")
                    ics_text = pre.text
                except Exception:
                    # a veces Chrome no envuelve en <pre> y devuelve texto plano directamente
                    ics_text = driver.page_source
                driver.quit()
            except Exception as e:
                print(f"⚠️ Fallback Selenium falló para {url}: {e}")

        # 3) Parsear ICS si lo tenemos
        if ics_text:
            try:
                cal = Calendar(ics_text)
                consume_calendar(cal)
            except Exception as e:
                print(f"⚠️ Error parseando ICS {y}-{m:02d}: {e}")

    # 4) Último recurso: ICS local (para probar parser o “modo offline”)
    if not events and offline_path:
        try:
            with open(offline_path, "r", encoding="utf-8") as f:
                cal = Calendar(f.read())
            consume_calendar(cal)
            print(f"🗂️ Cargados {len(events)} eventos desde offline_path")
        except Exception as e:
            print(f"⚠️ Error leyendo offline_path: {e}")

    print(f"🎉 Total eventos Jarascada: {len(events)}")
    return events

# --------------------------
# Scraping Agenda Gijón (EventON) - 7 días vista
# Click + verificación .evo_cal_data; si falla, REST in-page (fetch)
# --------------------------

