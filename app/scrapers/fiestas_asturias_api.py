"""
Scraper para eventos - Fiestas Asturias Api.
"""

from app.scrapers.base import *

def get_events_fiestasasturias_api(max_pages=50):


    api_base = "https://api.ww-api.com/front"
    SITE_ID = 3649360
    SECTION_ID = 60825576  # categoría "Todas"
    eventos = []
    vistos = set()
    page = 1

    while page <= max_pages:
        url = (
            f"{api_base}/get_items/{SITE_ID}/{SECTION_ID}/"
            f"?category_index=0&page={page}&per_page=24"
        )
        print(f"🌐 Descargando página {page}: {url}")

        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"❌ Error en página {page}: {e}")
            break

        items = data.get("items", [])
        print(f"📦 Página {page}: {len(items)} eventos encontrados")

        if not items:
            break

        for idx, it in enumerate(items):
            try:
                title = it.get("title", "Sin título")
                link = it.get("url", "")

                dt_start = dateparser.parse(it.get("date", ""))
                if not dt_start:
                    print(f"⚠️ Evento sin fecha, descartado: {title}")
                    continue

                dt_end = None
                end_raw = it.get("endDate", "")
                if end_raw:
                    dt_end = dateparser.parse(end_raw)
                if not dt_end:
                    dt_end = dt_start

                # Clave única para evitar duplicados
                key = (title, dt_start.date(), link)
                if key in vistos:
                    continue
                vistos.add(key)

                # Lugar
                lat = it.get("latitude")
                lon = it.get("longitude")
                address = it.get("address", "")
                if lat and lon:
                    lugar = (
                        f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={lat},{lon}", '
                        f'"{address or f"{lat},{lon}"}")'
                    )
                elif address:
                    url_map = it.get("address_url", "")
                    lugar = f'=HYPERLINK("{url_map}", "{address}")'
                else:
                    lugar = ""

                hora = dt_start.strftime("%H:%M") if dt_start.hour else ""

                # Disciplina
                disciplina = inferir_disciplina(title)

                eventos.append({
                    "fuente": "FiestasAsturias API",
                    "evento": title,
                    "fecha": dt_start,
                    "fecha_fin": dt_end,
                    "hora": hora,
                    "lugar": lugar,
                    "link": link,
                    "disciplina": disciplina
                })

                print(f"✅ [{page}-{idx}] {title} -> {dt_start.date()} {hora}")

            except Exception as e:
                print(f"⚠️ Error procesando evento en página {page}: {e}")
                continue

        if not data.get("next_page"):
            print(f"🚫 No hay más páginas.")
            break

        page += 1

    print(f"🎉 Total eventos FiestasAsturias: {len(eventos)}")
    return eventos

# --------------------------
# Scraping FiestasAsturias API https://www.asturiasdefiesta.com
# --------------------------

