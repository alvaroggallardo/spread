"""
Scraper para eventos - Spainswing.
"""

from app.scrapers.base import *

def get_events_asturias(max_days_ahead=90):
    from bs4 import BeautifulSoup
    from urllib.parse import quote_plus
    import time, re
    from datetime import datetime
    import dateparser
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    url = "https://spainswingdance.com/eventos-asturias"
    events = []
    driver = get_selenium_driver(headless=True)

    try:
        driver.get(url)

        # Espera a que cargue el calendario (SSR normalmente, pero por si acaso)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article.ics-calendar-list-wrapper"))
            )
        except Exception:
            time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        article = soup.select_one("article.ics-calendar-list-wrapper")
        if not article:
            print("⚠️ No se encontró el contenedor del calendario.")
            return events

        # Recorremos en orden los hijos directos: <h3> (Mes Año) y <div class="ics-calendar-date-wrapper">
        current_year = datetime.now().year

        # hijos directos en orden
        for node in article.find_all(recursive=False):
            classes = node.get("class", [])

            # Encabezado de mes: ej. "Agosto 2025" -> fija año
            if node.name == "h3" and "ics-calendar-label" in classes:
                label = node.get_text(" ", strip=True)  # p.ej. "Agosto 2025"
                parsed_label = dateparser.parse(f"1 {label}", languages=["es"])
                if parsed_label:
                    current_year = parsed_label.year
                continue

            # Día con eventos
            if node.name == "div" and "ics-calendar-date-wrapper" in classes:
                # data-date ej. "12 agosto"
                date_no_year = (node.get("data-date") or "").strip()
                if not date_no_year:
                    # fallback al id del <h4> ej. ...-20250812
                    h4 = node.find("h4", class_="ics-calendar-date")
                    if h4 and h4.has_attr("id"):
                        m = re.search(r"(\d{4})(\d{2})(\d{2})$", h4["id"])
                        if m:
                            y, mo, d = m.groups()
                            parsed_date = datetime(int(y), int(mo), int(d))
                        else:
                            parsed_date = None
                    else:
                        parsed_date = None
                else:
                    parsed_date = dateparser.parse(f"{date_no_year} {current_year}", languages=["es"])

                if not parsed_date:
                    # si no hay fecha, salta el día
                    continue

                # Filtro por ventana temporal
                if max_days_ahead is not None:
                    delta_days = (parsed_date.date() - datetime.now().date()).days
                    if delta_days < 0 or delta_days > max_days_ahead:
                        continue

                # ID ancla del día (para construir link único estable)
                h4 = node.find("h4", class_="ics-calendar-date")
                day_anchor = h4["id"] if h4 and h4.has_attr("id") else parsed_date.strftime("%Y%m%d")

                # Cada evento está como pares DT.time + DD.event
                dls = node.select("dl.events")
                if not dls:
                    continue

                for dl in dls:
                    # Recorremos cada <dd class="event"> y tomamos su <dt class="time"> previa
                    for idx, dd in enumerate(dl.select("dd.event")):
                        # Título
                        title_el = dd.select_one("span.title")
                        title = title_el.get_text(strip=True) if title_el else "Sin título"

                        # Hora (del dt inmediatamente anterior)
                        dt_time = dd.find_previous_sibling("dt", class_="time")
                        time_str = ""
                        if dt_time:
                            # Tomar solo la hora inicial antes del separador "–"
                            raw = dt_time.get_text(" ", strip=True)
                            time_str = raw.split("–")[0].strip()

                        # Localización
                        loc_a = dd.select_one(".descloc .location a")
                        location_text = loc_a.get_text(" ", strip=True) if loc_a else "Asturias"

                        # Link único (no hay enlace propio de evento, generamos ancla estable)
                        # Usamos el id del día + slug del título
                        slug = re.sub(r"\W+", "-", title.strip().lower()).strip("-")
                        link = f"{url}#{day_anchor}-{quote_plus(slug)}"

                        # Disciplina inferida
                        disciplina = inferir_disciplina(title)

                        # Duplicados por link
                        if any(ev["link"] == link for ev in events):
                            print(f"🔁 Evento duplicado saltado: {title}")
                            continue

                        events.append({
                            "fuente": "SpainSwingAsturias",
                            "evento": title,
                            "fecha": parsed_date,
                            "hora": time_str,
                            "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location_text)}", "{location_text}")',
                            "link": link,
                            "disciplina": disciplina
                        })

                        print(f"✅ Asturias (Swing): {title} ({parsed_date.date()})")

    except Exception as e:
        print(f"❌ Error en Asturias (Swing): {e}")
    finally:
        driver.quit()

    print(f"🎉 Total eventos Asturias (Swing): {len(events)}")
    return events

    
    # --------------------------
# Scraping Jarascada (ICS mensual)
# --------------------------
# --------------------------
# Scraping Jarascada (ICS mensual, con headers y fallback Selenium)
# --------------------------

