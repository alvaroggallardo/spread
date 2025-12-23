"""
Scraper para eventos de Asturies Cultura en Rede.
"""

import time
import requests
from app.scrapers.base import (
    inferir_disciplina,
    BeautifulSoup,
    dateparser,
    urljoin,
    quote_plus
)


def get_events_asturiescultura(max_pages=20):
    """
    Obtiene eventos de Asturies Cultura en Rede.
    
    Args:
        max_pages: Número máximo de páginas a scrapear
        
    Returns:
        list: Lista de diccionarios con información de eventos
    """
    base_url = "https://www.asturiesculturaenrede.es"
    events = []

    for page in range(1, max_pages + 1):
        url = f"{base_url}/es/programacion/pag/{page}"
        print(f"🌐 Cargando página {page}: {url}")

        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                print(f"🚫 Página {page} devuelve código {res.status_code}, parada.")
                break

            soup = BeautifulSoup(res.text, "html.parser")
            items = soup.select("div.col_one_third")
            print(f"📦 Página {page}: {len(items)} eventos encontrados")

            if not items:
                print("🚫 No más eventos, parada anticipada.")
                break

            for idx, e in enumerate(items):
                # Título y link
                title_el = e.select_one("p.autor a")
                title = title_el.text.strip() if title_el else "Sin título"
                link = urljoin(base_url, title_el['href']) if title_el else ""

                print(f"🔹 [{idx}] Título: {title}")

                # Evitar duplicados
                if any(ev["link"] == link for ev in events):
                    print(f"🔁 Evento duplicado saltado: {title}")
                    continue

                # Fecha y lugar
                strong_el = e.select_one("p.album strong")
                if not strong_el or "|" not in strong_el.text:
                    print(f"⚠️ [{idx}] Evento sin datos de fecha/lugar, saltado.")
                    continue

                fecha_txt, municipio = strong_el.text.strip().split("|")
                fecha_evento = dateparser.parse(fecha_txt.strip(), languages=["es"])
                if not fecha_evento:
                    print(f"❌ [{idx}] Fecha no reconocida, descartado.")
                    continue

                lugar = municipio.strip()

                # Extraer lugar más preciso del detalle
                try:
                    detalle = requests.get(link, timeout=10)
                    if detalle.status_code == 200:
                        soup_detalle = BeautifulSoup(detalle.text, "html.parser")
                        ticket_icon = soup_detalle.select_one("i.icon-ticket")
                        if ticket_icon:
                            ticket_div = ticket_icon.find_parent("div", class_="divider")
                            if ticket_div:
                                next_div = ticket_div.find_next_sibling("div", class_="col_full")
                                if next_div:
                                    lugar_p = next_div.find("p")
                                    if lugar_p:
                                        lugar = lugar_p.get_text(strip=True)
                except Exception as ex:
                    print(f"⚠️ [{idx}] No se pudo extraer lugar desde {link}: {ex}")

                # Disciplina
                disciplina_el = e.select_one("p.album a")
                disciplina_text = disciplina_el.text.strip() if disciplina_el else ""
                disciplina = inferir_disciplina(f"{disciplina_text} {title}")

                # Hora (puede no haber)
                hora_text = ""
                if fecha_evento.hour or fecha_evento.minute:
                    hora_text = fecha_evento.strftime("%H:%M")

                events.append({
                    "fuente": "Asturies Cultura en Rede",
                    "evento": title,
                    "fecha": fecha_evento,
                    "hora": hora_text,
                    "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
                    "link": link,
                    "disciplina": disciplina
                })

                print("✅ Añadido.")
        except Exception as e:
            print(f"❌ [AsturiesCultura][Página {page}] Error: {e}")
            continue

        time.sleep(1)  # opcional, para no sobrecargar servidor

    print(f"🎉 Total eventos Asturies Cultura en Rede: {len(events)}")
    return events
