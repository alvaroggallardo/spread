"""
Scraper para eventos de Oviedo desde VisitOviedo.
"""

import time
from datetime import datetime
from app.scrapers.base import (
    get_selenium_driver,
    inferir_disciplina,
    BeautifulSoup,
    dateparser,
    quote_plus
)


def get_events_oviedo(max_days_ahead=90):
    """
    Obtiene eventos de Oviedo desde VisitOviedo usando Selenium.
    
    Args:
        max_days_ahead: Número máximo de días hacia adelante para filtrar eventos
        
    Returns:
        list: Lista de diccionarios con información de eventos
    """
    url = "https://www.visitoviedo.info/agenda"
    events = []
    driver = get_selenium_driver(headless=True)

    try:
        driver.get(url)
        time.sleep(5)  # esperar carga JS

        soup = BeautifulSoup(driver.page_source, "html.parser")
        day_entries = soup.select("div.day-entry")

        for day in day_entries:
            parsed_date = None
            day_anchor = day.select_one("a.day")
            if day_anchor:
                day_num = day_anchor.select_one("span.day-of-month").text.strip()
                month = day_anchor.select_one("span.month").text.strip()
                year = datetime.now().year
                date_str = f"{day_num} {month} {year}"
                parsed_date = dateparser.parse(date_str, languages=['es'])

            if not parsed_date:
                continue

            # Filtra solo fechas dentro de N días
            delta_days = (parsed_date.date() - datetime.now().date()).days
            if delta_days < 0 or delta_days > max_days_ahead:
                continue

            for entry in day.select("div.entry"):
                link_el = entry.select_one("a")
                title_el = entry.select_one("span.title")
                hour_el = entry.select_one("span.hour")
                location_el = entry.select_one("span.location")

                title = title_el.text.strip() if title_el else "Sin título"
                time_str = hour_el.text.replace("Tiempo", "").strip() if hour_el else ""
                location = location_el.text.strip() if location_el else "Oviedo"
                link = link_el["href"] if link_el and "href" in link_el.attrs else url

                disciplina = inferir_disciplina(title)

                # ✅ Check duplicados por link
                if any(ev["link"] == link for ev in events):
                    print(f"🔁 Evento duplicado saltado: {title}")
                    continue

                events.append({
                    "fuente": "VisitOviedo",
                    "evento": title,
                    "fecha": parsed_date,
                    "hora": time_str,
                    "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location)}", "{location}")',
                    "link": link,
                    "disciplina": disciplina
                })

                print(f"✅ Oviedo: {title} ({parsed_date.date()})")

    except Exception as e:
        print(f"❌ Error en Oviedo: {e}")
    finally:
        driver.quit()

    print(f"🎉 Total eventos Oviedo: {len(events)}")
    return events
