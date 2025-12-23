"""
Scraper para eventos - Camara Gijon.
"""

from app.scrapers.base import *

def get_events_camaragijon_recinto():
    import re
    from urllib.parse import urljoin, quote_plus

    base = "https://recintoferialasturias.camaragijon.es"
    url = f"{base}/es/tratarAplicacionAgenda.do?proximosEventos=1"
    events = []

    try:
        res = requests.get(url, timeout=12)
        if res.status_code != 200:
            print(f"❌ Error al cargar la página: {res.status_code}")
            return []

        soup = BeautifulSoup(res.content, "html.parser")

        items = soup.select("ul.entertainment_list li.entertainment_item")
        print(f"📦 Encontrados {len(items)} eventos (Cámara Gijón)")

        for idx, li in enumerate(items):
            a = li.select_one("a.card_link")
            if not a:
                continue

            raw_link = a.get("href", "")
            link = urljoin(base, raw_link)

            # Título
            title_el = a.select_one("strong.card_title")
            title_text = title_el.get_text(strip=True) if title_el else "Sin título"
            title = f"🎪 {title_text}"  # icono distinto para diferenciar fuente

            # Fecha (rango tipo "02 de agosto de 2025 al 17 de agosto de 2025")
            date_el = a.select_one("b.card_date")
            date_text = date_el.get_text(strip=True) if date_el else ""

            start_date, end_date = None, None
            if date_text:
                # Normaliza espacios
                normalized = re.sub(r"\s+", " ", date_text)
                # Parte por ' al ' (también cubrimos guiones largos por si acaso)
                parts = re.split(r"\s+(?:al|a|–|—|-)\s+", normalized, maxsplit=1, flags=re.IGNORECASE)
                left = parts[0].strip() if parts else normalized
                right = parts[1].strip() if len(parts) > 1 else left

                # Parse con dateparser en español
                start_date = dateparser.parse(left, languages=["es"], settings={"DATE_ORDER": "DMY"})
                end_date = dateparser.parse(right, languages=["es"], settings={"DATE_ORDER": "DMY"})

            # Ubicación (texto)
            loc_el = a.select_one("span.card_location")
            location = loc_el.get_text(strip=True) if loc_el else "Gijón"

            # ✅ Evitar duplicados por enlace y fecha de inicio
            if any(ev["link"] == link and ev["fecha"] == start_date for ev in events):
                print(f"🔁 Duplicado saltado: {title_text}")
                continue

            # Construir 'lugar' → Google Maps con la ubicación textual
            lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location)}", "{location}")'

            # Clasificación
            disciplina = inferir_disciplina(title_text)

            events.append({
                "fuente": "CámaraGijón",
                "evento": title,
                "fecha": start_date,
                "fecha_fin": end_date,
                "hora": "",  # no aparece en el listado
                "lugar": lugar,
                "link": link,
                "disciplina": disciplina
            })
            print(f"✅ [{idx}] Añadido: {title_text}")

        print(f"🎉 Total eventos Cámara Gijón: {len(events)}")
        return events

    except Exception as e:
        print(f"❌ Error en get_events_camaragijon_recinto: {e}")
        return []


# --------------------------
# Scraping Laboral Centro de Arte
# https://laboralcentrodearte.org/es/actividades/
# --------------------------

