"""
Scraper para eventos - Laboral Centro Arte.
"""

from app.scrapers.base import *

def get_events_laboral_actividades():
    from urllib.parse import urljoin, quote_plus
    import re

    base = "https://laboralcentrodearte.org"
    url = f"{base}/es/actividades/"
    events = []

    try:
        res = requests.get(url, timeout=12)
        if res.status_code != 200:
            print(f"❌ Error al cargar la página: {res.status_code}")
            return []

        soup = BeautifulSoup(res.content, "html.parser")

        items = soup.select("ul.exhibition-block__items li.exhibition-block__item")
        print(f"📦 Encontrados {len(items)} eventos (Laboral)")

        for idx, li in enumerate(items):
            a = li.select_one("a[href]")
            if not a:
                continue

            raw_link = a.get("href", "").strip()
            link = urljoin(base, raw_link)

            # Título
            title_el = li.select_one("h4.exhibition-block__item-name")
            title_text = title_el.get_text(strip=True) if title_el else "Sin título"
            title = f"🖼️ {title_text}"

            # Fecha (ej: "21 Septiembre 2025")
            date_el = li.select_one("div.exhibition-block__item-dates")
            date_text = date_el.get_text(" ", strip=True) if date_el else ""
            date_text = re.sub(r"\s+", " ", date_text)

            start_date = end_date = None
            if date_text:
                # La página suele dar fecha única; si alguna vez diera rango, intentamos dividirlo
                parts = re.split(r"\s+(?:al|a|–|—|-)\s+", date_text, maxsplit=1, flags=re.IGNORECASE)
                left = parts[0].strip()
                right = parts[1].strip() if len(parts) > 1 else left

                start_date = dateparser.parse(left, languages=["es"], settings={"DATE_ORDER": "DMY"})
                end_date = dateparser.parse(right, languages=["es"], settings={"DATE_ORDER": "DMY"})

            # Ubicación fija del centro (el listado no trae dirección concreta)
            location = "LABoral Centro de Arte, Gijón"
            lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location)}", "{location}")'

            # ✅ Evitar duplicados por enlace y fecha de inicio
            if any(ev["link"] == link and ev["fecha"] == start_date for ev in events):
                print(f"🔁 Duplicado saltado: {title_text}")
                continue

            disciplina = inferir_disciplina(title_text)

            events.append({
                "fuente": "LaboralCentroDeArte",
                "evento": title,
                "fecha": start_date,
                "fecha_fin": end_date,
                "hora": "",
                "lugar": lugar,
                "link": link,
                "disciplina": disciplina
            })
            print(f"✅ [{idx}] Añadido: {title_text}")

        print(f"🎉 Total eventos Laboral: {len(events)}")
        return events

    except Exception as e:
        print(f"❌ Error en get_events_laboral_actividades: {e}")
        return []


# --------------------------
# Scraping Asturias Convivencias
# https://asturiasconvivencias.es/eventos
# --------------------------

