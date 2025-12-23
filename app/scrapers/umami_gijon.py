"""
Scraper para eventos - Umami Gijon.
"""

from app.scrapers.base import *

def get_events_gijon_umami(max_days_ahead=90):
    url = "https://umamigijon.com/cursos/"
    events = []
    driver = get_selenium_driver(headless=True)

    try:
        driver.get(url)
        time.sleep(5)  # esperar carga inicial de JS

        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select("div.mep-event-list-loop.mep_event_grid_item")

        if not cards:
            # pequeño scroll para forzar lazy-load si aplica
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select("div.mep-event-list-loop.mep_event_grid_item")

        for c in cards:
            # --- fecha ---
            parsed_date = None
            date_raw = (c.get("data-date") or "").strip()  # formato: mm/dd/yyyy
            if re.fullmatch(r"\d{2}/\d{2}/\d{4}", date_raw):
                try:
                    parsed_date = datetime.strptime(date_raw, "%m/%d/%Y")
                except Exception:
                    parsed_date = None

            # Fallback: extraer del primer h5 de la fecha (ej. "miércoles, 13 Ago, 2025")
            if not parsed_date:
                h5_date = c.select_one("li.mep_list_event_date .evl-cc h5")
                if h5_date:
                    parsed_date = dateparser.parse(h5_date.get_text(strip=True), languages=["es"])

            if not parsed_date:
                continue  # sin fecha no podemos normalizar ni filtrar

            # Filtra por ventana temporal
            delta_days = (parsed_date.date() - datetime.now().date()).days
            if delta_days < 0 or delta_days > max_days_ahead:
                continue

            # --- título ---
            title = (c.get("data-title") or "").strip()
            if not title:
                h2 = c.select_one(".mep_list_title")
                title = h2.get_text(strip=True) if h2 else "Sin título"

            # --- hora ---
            time_str = ""
            for h in reversed(c.select("li.mep_list_event_date .evl-cc h5")):
                t = h.get_text(strip=True)
                if re.search(r"\d{1,2}:\d{2}", t):
                    time_str = t
                    break

            # --- localización ---
            loc_el = c.select_one("li.mep_list_location_name h5")
            location = loc_el.get_text(strip=True) if loc_el else "Gijón"
            lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location)}", "{location}")'

            # --- link ---
            a = c.select_one("a.plnb-book-now")
            link = a["href"].strip() if a and a.has_attr("href") else url

            # --- disciplina (según tu helper) ---
            disciplina = inferir_disciplina(title)

            # ✅ Evitar duplicados por link
            if any(ev["link"] == link for ev in events):
                print(f"🔁 Evento duplicado saltado: {title}")
                continue

            events.append({
                "fuente": "UmamiGijon",
                "evento": title,
                "fecha": parsed_date,   # datetime, igual que en tu modelo de Oviedo
                "hora": time_str,
                "lugar": lugar,         # fórmula HYPERLINK lista para Excel/Sheets
                "link": link,
                "disciplina": disciplina
            })

            print(f"✅ Gijón/Umami: {title} ({parsed_date.date()})")

    except Exception as e:
        print(f"❌ Error en Gijón/Umami: {e}")
    finally:
        driver.quit()

    print(f"🎉 Total eventos Gijón/Umami: {len(events)}")
    return events


# --------------------------
# Scraping SpainSwing (Asturias) adaptado al modelo Gijón/Oviedo
# --------------------------

