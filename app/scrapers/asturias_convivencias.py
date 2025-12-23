"""
Scraper para eventos - Asturias Convivencias.
"""

from app.scrapers.base import *

def get_events_asturiasconvivencias():
    from urllib.parse import urljoin, quote_plus
    import re

    base = "https://asturiasconvivencias.es"
    url = f"{base}/eventos"
    events = []

    try:
        res = requests.get(url, timeout=12)
        if res.status_code != 200:
            print(f"❌ Error al cargar la página: {res.status_code}")
            return []

        soup = BeautifulSoup(res.content, "html.parser")

        items = soup.select("div.em.em-list.em-events-list div.em-event.em-item")
        print(f"📦 Encontrados {len(items)} eventos (AsturiasConvivencias)")

        for idx, box in enumerate(items):
            # Título y enlace
            title_a = box.select_one("h3.em-item-title a[href]")
            if not title_a:
                continue
            title_text = title_a.get_text(strip=True)
            link = urljoin(base, title_a.get("href", "").strip())
            title = f"🌿 {title_text}"

            # Fecha(s)
            date_el = box.select_one(".em-item-meta-line.em-event-date")
            date_text = (date_el.get_text(" ", strip=True) if date_el else "").replace("\xa0", " ")
            date_text = re.sub(r"\s+", " ", date_text)

            start_date = end_date = None
            if date_text:
                # Detecta rango "dd/mm/yyyy - dd/mm/yyyy" o fecha única "dd/mm/yyyy"
                parts = re.split(r"\s*(?:-|–|—|al|a)\s*", date_text, maxsplit=1, flags=re.IGNORECASE)
                left = parts[0].strip()
                right = parts[1].strip() if len(parts) > 1 else left

                start_date = dateparser.parse(left, languages=["es"], settings={"DATE_ORDER": "DMY"})
                end_date = dateparser.parse(right, languages=["es"], settings={"DATE_ORDER": "DMY"})

            # Hora
            time_el = box.select_one(".em-item-meta-line.em-event-time")
            hora_text = time_el.get_text(" ", strip=True).replace("\xa0", " ") if time_el else ""

            # Ubicación (texto)
            loc_el = box.select_one(".em-item-meta-line.em-event-location a")
            location = loc_el.get_text(strip=True) if loc_el else "Asturias"
            lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location)}", "{location}")'

            # ✅ Deduplicación por link + fecha de inicio
            if any(ev["link"] == link and ev["fecha"] == start_date for ev in events):
                print(f"🔁 Duplicado saltado: {title_text}")
                continue

            # Disciplina (usando tu heurística)
            disciplina = inferir_disciplina(title_text)

            events.append({
                "fuente": "AsturiasConvivencias",
                "evento": title,
                "fecha": start_date,
                "fecha_fin": end_date,
                "hora": hora_text,
                "lugar": lugar,
                "link": link,
                "disciplina": disciplina
            })
            print(f"✅ [{idx}] Añadido: {title_text}")

        print(f"🎉 Total eventos AsturiasConvivencias: {len(events)}")
        return events

    except Exception as e:
        print(f"❌ Error en get_events_asturiasconvivencias: {e}")
        return []


# --------------------------
# Scraping Umami Gijón (Cursos)
# https://umamigijon.com/cursos/
# --------------------------

