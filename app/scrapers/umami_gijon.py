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
        cards = soup.select("div.mep_event_grid_item")  # más robusto

        if not cards:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select("div.mep_event_grid_item")

        for c in cards:
            # --- fecha ---
            parsed_date = None
            date_raw = (c.get("data-date") or "").strip()  # YYYY-MM-DD
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_raw):
                parsed_date = datetime.strptime(date_raw, "%Y-%m-%d")
            else:
                p_date = c.select_one("li.mep_list_event_date .evl-cc p")
                if p_date:
                    parsed_date = dateparser.parse(p_date.get_text(strip=True), languages=["es"])

            if not parsed_date:
                continue

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
            p_time = c.select_one("li.mep_list_event_date .evl-cc p:nth-of-type(2)")
            if p_time:
                time_str = p_time.get_text(strip=True)

            # --- localización ---
            loc_el = c.select_one("li.mep_list_location_name .evl-cc h6")
            location = loc_el.get_text(strip=True) if loc_el else "Gijón"
            lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location)}", "{location}")'

            # --- link ---
            a = c.select_one("a[href]")
            link = a["href"].strip() if a else url

            # --- disciplina ---
            disciplina = inferir_disciplina(title)

            # ✅ Evitar duplicados por link
            if any(ev["link"] == link for ev in events):
                print(f"🔁 Evento duplicado saltado: {title}")
                continue

            events.append({
                "fuente": "UmamiGijon",
                "evento": title,
                "fecha": parsed_date,
                "hora": time_str,
                "lugar": lugar,
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
