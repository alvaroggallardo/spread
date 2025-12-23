"""
Scraper para eventos - Siero.
"""

from app.scrapers.base import *

def get_events_siero():
    from urllib.parse import quote_plus
    import time
    from bs4 import BeautifulSoup
    import requests
    import dateparser

    url = "https://www.ayto-siero.es/agenda/"
    events = []

    print(f"🌐 Cargando página principal de Siero: {url}")

    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("div.ectbe-inner-wrapper")

        print(f"📦 Encontrados {len(items)} eventos en Siero")

        if not items:
            print("🚫 No hay eventos en la página de Siero.")
            return events

        for idx, item in enumerate(items):
            try:
                # Título y link
                title_el = item.select_one("div.ectbe-evt-title a.ectbe-evt-url")
                title = title_el.text.strip() if title_el else "Sin título"
                link = title_el["href"] if title_el and title_el.has_attr("href") else url

                print(f"🔹 [{idx}] Título: {title}")

                # Fecha
                day_el = item.select_one("span.ectbe-ev-day")
                month_el = item.select_one("span.ectbe-ev-mo")
                year_el = item.select_one("span.ectbe-ev-yr")

                if not (day_el and month_el and year_el):
                    print(f"❌ [{idx}] No se pudo extraer fecha, descartado.")
                    continue

                fecha_str = f"{day_el.text.strip()} {month_el.text.strip()} {year_el.text.strip()}"
                fecha_evento = dateparser.parse(fecha_str, languages=["es"])

                if not fecha_evento:
                    print(f"❌ [{idx}] Fecha no reconocida, descartado.")
                    continue

                # Lugar
                lugar_el = item.select_one("span.ectbe-address")
                if lugar_el:
                    lugar = lugar_el.get_text(separator=" ", strip=True)
                    lugar = lugar.split(",")[0].strip()
                else:
                    lugar = "Siero"

                lugar_hyperlink = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")'

                # Hora → intentar desde página detalle
                hora_text = ""
                try:
                    detalle = requests.get(link, timeout=10)
                    if detalle.status_code == 200:
                        soup_detalle = BeautifulSoup(detalle.text, "html.parser")
                        hora_span = soup_detalle.select_one("div.tecset-date span.tribe-event-date-start")
                        if hora_span and "|" in hora_span.text:
                            hora_text = hora_span.text.split("|")[1].strip()
                except Exception as ex:
                    print(f"⚠️ [{idx}] No se pudo extraer la hora desde {link}: {ex}")

                # Disciplina
                disciplina = inferir_disciplina(title)

                events.append({
                    "fuente": "Siero",
                    "evento": title,
                    "fecha": fecha_evento,
                    "hora": hora_text,
                    "lugar": lugar_hyperlink,
                    "link": link,
                    "disciplina": disciplina
                })

                print("✅ Añadido.")

            except Exception as e:
                print(f"❌ [{idx}] Error procesando evento: {e}")
                continue

    except Exception as e:
        print(f"❌ Error global en Siero: {e}")

    print(f"🎉 Total eventos Siero: {len(events)}")
    return events



# --------------------------
# Scraping Conciertos.club
# --------------------------


