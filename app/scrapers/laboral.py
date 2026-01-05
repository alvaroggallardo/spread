"""
Scraper para eventos - Laboral.
"""

from app.scrapers.base import *
from urllib.parse import urljoin, quote_plus
import re
from datetime import datetime

def parse_laboral_cards(cards, visto):
    base_url = "https://www.laboralciudaddelacultura.com"
    eventos = []

    for card in cards:
        title_el = card.select_one("span.card-title")
        title = title_el.get_text(strip=True) if title_el else "Sin título"

        link_el = card.select_one("a.d-block")
        link = urljoin(base_url, link_el["href"]) if link_el else base_url

        start_el = card.select_one("[itemprop='startDate']")
        end_el = card.select_one("[itemprop='endDate']")
        start_date = start_el["date"] if start_el and "date" in start_el.attrs else None
        end_date = end_el["date"] if end_el and "date" in end_el.attrs else start_date

        if not start_date:
            continue

        start_dt = datetime.strptime(start_date.split()[0], "%Y-%m-%d")
        end_dt = datetime.strptime(end_date.split()[0], "%Y-%m-%d")

        # CLAVE ÚNICA
        key = (title, start_dt.date(), link)
        if key in visto:
            # ✅ Evento ya procesado → skip
            continue
        visto.add(key)

        hora_el = card.select_one("span.d-block.hour")
        if hora_el:
            hora_text = hora_el.get_text(" ", strip=True)
            match = re.search(r"\b\d{1,2}:\d{2}\b", hora_text)
            hora = match.group(0) if match else ""
        else:
            hora = ""

        # Disciplina
        disciplina = inferir_disciplina(title)

        eventos.append({
            "fuente": "Laboral Ciudad de la Cultura",
            "evento": title,
            "fecha": start_dt,
            "fecha_fin": end_dt,
            "hora": hora,
            "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus("Laboral Ciudad de la Cultura Gijón")}", "Laboral Ciudad de la Cultura")',
            "link": link,
            "disciplina": disciplina
        })

    return eventos


def get_events_laboral(max_pages=10):

    base_url = "https://www.laboralciudaddelacultura.com/agenda"
    events = []
    visto = set()

    # Scrape page 1
    res = requests.get(base_url)
    soup = BeautifulSoup(res.text, "html.parser")
    cards = soup.select("div.card[itemtype='http://schema.org/Event']")
    print(f"🔎 Página 1: {len(cards)} eventos")
    events.extend(parse_laboral_cards(cards, visto))

    # Scrape following pages
    for page in range(2, max_pages + 1):
        params = {
            "p_p_id": "as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_kiUgFekyAvs3",
            "p_p_lifecycle": "0",
            "_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_kiUgFekyAvs3_calendarPath": "/html/suite/displays/list.jsp",
            "p_r_p_categoryId": "0",
            "p_r_p_categoryIds": "",
            "_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_kiUgFekyAvs3_calendarId": "0",
            "_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_kiUgFekyAvs3_delta": "6",
            "_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_kiUgFekyAvs3_cur": str(page),
        }

        res = requests.get(base_url, params=params)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select("div.card[itemtype='http://schema.org/Event']")
        print(f"🔎 Página {page}: {len(cards)} eventos")

        if not cards:
            print("🚫 No hay más eventos.")
            break

        events.extend(parse_laboral_cards(cards, visto))

    print(f"🎉 Total eventos Laboral: {len(events)}")
    return events



