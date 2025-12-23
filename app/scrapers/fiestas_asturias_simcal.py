"""
Scraper para eventos - Fiestas Asturias Simcal.
"""

from app.scrapers.base import *

def get_events_fiestasasturias_simcal():
    import re
    from urllib.parse import urljoin, quote_plus

    url = "https://www.asturiasdefiesta.es/calendario-de-fiestas"
    events = []

    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            print(f"❌ Error al cargar la página: {res.status_code}")
            return []

        soup = BeautifulSoup(res.content, "html.parser")

        for li in soup.select("li.simcal-event"):
            title_el = li.select_one(".simcal-event-title")
            details_el = li.select_one(".simcal-event-details")

            title_text = title_el.get_text(strip=True) if title_el else "Sin título"
            title = f"🎉 {title_text}"

            start_el = details_el.select_one(".simcal-event-start") if details_el else None
            end_el = details_el.select_one(".simcal-event-end") if details_el else None

            start_date = parser.parse(start_el["content"]) if start_el and "content" in start_el.attrs else None
            end_date = parser.parse(end_el["content"]) if end_el and "content" in end_el.attrs else None

            link_el = details_el.select_one("a") if details_el else None
            raw_link = link_el["href"] if link_el and "href" in link_el.attrs else ""
            link = urljoin(url, raw_link)  # Normaliza enlaces relativos

            # ✅ Evitar duplicados por enlace y fecha de inicio
            if any(ev["link"] == link and ev["fecha"] == start_date for ev in events):
                print(f"🔁 Evento duplicado saltado: {title_text}")
                continue

            # 🔎 Intenta extraer lat/lon desde la página del evento (Leaflet)
            lat, lon = None, None
            if link:
                try:
                    det = requests.get(link, timeout=10)
                    if det.status_code == 200:
                        html = det.text
                        # Primero intenta con setView([lat, lon], zoom)
                        m = re.search(
                            r"L\.map\(['\"]map['\"]\)\.setView\(\[\s*([0-9.\-]+)\s*,\s*([0-9.\-]+)\s*\]\s*,\s*\d+\s*\)",
                            html
                        )
                        if not m:
                            # Si no, prueba con L.marker([lat, lon])
                            m = re.search(
                                r"L\.marker\(\[\s*([0-9.\-]+)\s*,\s*([0-9.\-]+)\s*\]\)",
                                html
                            )
                        if m:
                            lat, lon = m.groups()
                        else:
                            print(f"⚠️ Sin coordenadas explícitas en detalle: {link}")
                    else:
                        print(f"⚠️ No se pudo abrir detalle ({det.status_code}): {link}")
                except Exception as e:
                    print(f"⚠️ Error leyendo detalle: {e}")

            # 🧭 Construye el campo 'lugar'
            if lat and lon:
                lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={lat},{lon}", "Ubicación exacta")'
            else:
                # Fallback genérico
                lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus("Asturias")}", "Asturias")'

            disciplina = inferir_disciplina(title_text)

            events.append({
                "fuente": "FiestasAsturias",
                "evento": title,
                "fecha": start_date,
                "fecha_fin": end_date,
                "hora": "",
                "lugar": lugar,
                "link": link,
                "disciplina": disciplina
            })

        print(f"✅ Eventos extraídos desde simcal-calendar: {len(events)}")

    except Exception as e:
        print(f"❌ Error en get_events_fiestasasturias_simcal: {e}")

    return events


# --------------------------
# Scraping Recinto Ferial (Cámara Gijón)
# https://recintoferialasturias.camaragijon.es/es/tratarAplicacionAgenda.do?proximosEventos=1
# --------------------------

