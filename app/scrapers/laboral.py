"""
Scraper para eventos - Laboral.
"""

from app.scrapers.base import *

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



