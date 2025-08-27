import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment
import json
from geopy.geocoders import Nominatim
import dateparser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from urllib.parse import quote_plus
#from IPython.display import display, HTML
import time
from urllib.parse import urljoin, quote_plus
from dateparser.search import search_dates
from datetime import datetime
import re
from urllib.parse import urljoin, quote_plus
from datetime import datetime, timedelta
from ics import Calendar
from dateutil import parser
from zoneinfo import ZoneInfo

# --------------------------
# Geocoding
# --------------------------
geolocator = Nominatim(user_agent="cultural_events_locator")

def geocode_coordinates(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True)
        return location.raw['address'].get('city', 'Desconocido')
    except Exception as e:
        print(f"Error geocoding: {e}")
        return 'Desconocido'

# --------------------------
# Configurar Selenium para Jupyter
# --------------------------
def get_selenium_driver(headless=True):
    
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)

# --------------------------
# Scraping Oviedo adaptado al modelo Gijón
# --------------------------
def get_events_oviedo(max_days_ahead=90):
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

# --------------------------
# Scraping Gijón desde la API AJAX
# --------------------------
def get_events_gijon(max_pages=100):
    base_url = "https://www.gijon.es/es/eventos?pag="
    events = []

    for page in range(1, max_pages + 1):
        url = f"{base_url}{page}&"
        print(f"🌐 Cargando página {page}: {url}")
        driver = get_selenium_driver(headless=True)

        try:
            driver.get(url)
            time.sleep(2)  # suficiente para carga estática
            soup = BeautifulSoup(driver.page_source, "html.parser")
            items = soup.select("div.col-lg-4.col-md-6.col-12")
            print(f"📦 Página {page}: {len(items)} eventos encontrados")

            if not items:
                print("🚫 No más eventos, parada anticipada.")
                break

            for idx, item in enumerate(items):
                title_el = item.select_one("div.tituloEventos a")
                title = title_el.text.strip() if title_el else "Sin título"
                link = "https://www.gijon.es" + title_el["href"] if title_el else ""
                print(f"🔹 [{idx}] Título: {title}")

                # ✅ Evitar duplicados
                if any(ev["link"] == link for ev in events):
                    print(f"🔁 Evento duplicado saltado: {title}")
                    continue

                # Fecha
                date_text = ""
                for span in item.select("span"):
                    if "Fechas:" in span.text:
                        date_text = span.text.replace("Fechas:", "").strip()
                        break
                fecha_evento = dateparser.parse(date_text, languages=["es"])
                if not fecha_evento:
                    print("❌ Fecha no reconocida, descartado.")
                    continue

                # Hora
                hora_text = ""
                for span in item.select("span"):
                    if "Horario:" in span.text:
                        hora_text = span.text.replace("Horario:", "").strip()
                        break

                # Lugar
                location_el = item.select_one("span.localizacion a")
                location = location_el.text.strip() if location_el else "Gijón"

                disciplina = inferir_disciplina(title)

                events.append({
                    "fuente": "Gijón",
                    "evento": title,
                    "fecha": fecha_evento,
                    "hora": hora_text,
                    "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location)}", "{location}")',
                    "link": link,
                    "disciplina": disciplina
                })
                print("✅ Añadido.")
        except Exception as e:
            print(f"❌ [Gijón][Página {page}] Error: {e}")
        finally:
            driver.quit()

    print(f"🎉 Total eventos Gijón: {len(events)}")
    return events

# --------------------------
# Scraping Mieres desde página nueva de calendario ics
# --------------------------

def get_events_mieres():
    url = "https://www.mieres.es/eventos/?ical=1"
    events = []

    response = requests.get(url)
    cal = Calendar(response.text)

    for idx, event in enumerate(cal.events):
        title = event.name or "Sin título"
        link = event.url if event.url else "https://www.mieres.es/eventos/"
        lugar = event.location or "Mieres"

        # La librería ics devuelve start/end como datetime aware (con zona horaria)
        start_dt = event.begin
        if start_dt is not None:
            fecha_evento = start_dt.datetime
            hora_text = fecha_evento.strftime("%H:%M")
        else:
            fecha_evento = None
            hora_text = ""

        disciplina = inferir_disciplina(title)

        # ✅ Evitar duplicados
        if any(ev["link"] == link for ev in events):
            print(f"🔁 Evento duplicado saltado: {title}")
            continue

        events.append({
            "fuente": "Mieres",
            "evento": title,
            "fecha": fecha_evento,
            "hora": hora_text,
            "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
            "link": link,
            "disciplina": disciplina
        })

        print(f"✅ [{idx}] {title} -> {fecha_evento} {hora_text}")

    print(f"🎉 Total eventos Mieres (ICS): {len(events)}")

    return events


# --------------------------
# Scraping Asturias Cultura
# --------------------------

def get_events_asturiescultura(max_pages=20):
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

# --------------------------
# Scraping Avilés
# --------------------------

def get_events_aviles():
    url = "https://aviles.es/proximos-eventos"
    events = []
    driver = get_selenium_driver(headless=True)

    try:
        driver.get(url)
        time.sleep(3)  # tiempo de carga razonable

        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select("div.card.border-info")
        print(f"📦 Avilés: {len(cards)} eventos encontrados")

        if not cards:
            print("🚫 No hay eventos en Avilés.")
            return events

        for idx, card in enumerate(cards):
            # Título
            title_el = card.select_one("h5")
            title = title_el.text.strip() if title_el else "Sin título"

            # Enlace al evento (onclick del botón)
            link = ""
            btn = card.select_one("div.btn.btn-primary")
            if btn and btn.has_attr("onclick"):
                onclick_attr = btn["onclick"]
                relative_url = onclick_attr.split("showPopup('")[1].split("'")[0]
                clean_url = relative_url.split("?")[0]
                link = "https://aviles.es/proximos-eventos"

            print(f"🔹 [{idx}] Título: {title}")

            # Fecha y hora
            inicio_text = ""
            for badge in card.select("span.badge"):
                if "INICIO" in badge.text:
                    inicio_text = badge.text.replace("INICIO:", "").strip()
                    break

            fecha_evento = dateparser.parse(inicio_text, languages=["es"])
            if not fecha_evento:
                print(f"❌ [{idx}] Fecha no reconocida, descartado.")
                continue

            # Hora
            hora_text = ""
            if fecha_evento.hour is not None:
                hora_text = fecha_evento.strftime("%H:%M")

            # Lugar
            lugar = "Avilés"
            card_text = card.select_one("div.card-text")
            if card_text and "Lugar:" in card_text.text:
                raw_lugar = card_text.text.split("Lugar:")[-1].strip()
                lugar = raw_lugar.split("(")[0].strip().rstrip(".")

            # Inferir disciplina a partir del título
            disciplina = inferir_disciplina(title)

            # Construir evento
            events.append({
                "fuente": "Avilés",
                "evento": title,
                "fecha": fecha_evento,
                "hora": hora_text,
                "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
                "link": link,
                "disciplina": disciplina
            })

            print("✅ Añadido.")

    except Exception as e:
        print(f"❌ Error en Avilés: {e}")
    finally:
        driver.quit()

    print(f"🎉 Total eventos Avilés: {len(events)}")
    return events



# --------------------------
# Scraping Siero
# --------------------------

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

def get_events_conciertosclub():
    import time
    import dateparser
    from urllib.parse import urljoin, quote_plus
    from bs4 import BeautifulSoup
    from app.script_scraping import get_selenium_driver  # importa tu helper

    base_url = "https://conciertos.club/asturias"
    events = []

    driver = get_selenium_driver(headless=True)

    try:
        driver.get(base_url)
        time.sleep(4)  # deja cargar dinámicamente

        soup = BeautifulSoup(driver.page_source, "html.parser")

        articles = soup.select("section.conciertos > article")
        print(f"🔎 Encontrados {len(articles)} artículos (días)")

        for article_idx, article in enumerate(articles):
            # Título del día
            tit_wrap = article.select_one("div.tit_wrap > div.tit")
            if not tit_wrap:
                continue

            fecha_texto = tit_wrap.get_text(strip=True)

            # Quitar Hoy, Mañana, etc.
            for palabra in ["Hoy", "Mañana", "Pasado mañana"]:
                if palabra in fecha_texto:
                    fecha_texto = fecha_texto.replace(palabra, "").strip()

            palabras = fecha_texto.split()
            if len(palabras) >= 2 and palabras[0].capitalize() in [
                "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"
            ]:
                fecha_texto = " ".join(palabras[1:])

            fecha_evento = dateparser.parse(fecha_texto, languages=["es"])
            if not fecha_evento:
                print(f"⚠️ No se pudo parsear fecha: {fecha_texto}")
                continue

            lis = article.select("ul.list > li")

            for idx, li in enumerate(lis):
                try:
                    music_event = li.select_one("div[itemtype='http://schema.org/MusicEvent']")
                    if not music_event:
                        continue

                    # Título y link
                    enlace_el = music_event.select_one("a.nombre")
                    link = urljoin(base_url, enlace_el["href"]) if enlace_el else base_url
                    evento = enlace_el.get_text(strip=True) if enlace_el else "Sin título"

                    # Disciplina (estilo musical)
                    estilo_span = music_event.select_one("span.estilo")
                    disciplina_text = estilo_span.get_text(strip=True) if estilo_span else ""
                    disciplina = "Música"
                    if disciplina_text:
                        partes = disciplina_text.strip("/").split("/")
                        disciplina = partes[-1].strip() if partes else "Música"

                        # añadir estilo entre paréntesis al título
                        evento = f"{evento} ({disciplina_text.strip()})"

                    # Hora
                    hora = ""
                    time_div = music_event.select_one("div.time")
                    if time_div:
                        hora = time_div.get_text(strip=True)

                    # Lugar
                    lugar_el = music_event.select_one("a.local")
                    lugar_text = lugar_el.get_text(strip=True) if lugar_el else "Asturias"
                    lugar_clean = lugar_text.split(".")[0].strip() if "." in lugar_text else lugar_text
                    lugar_hyperlink = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar_clean)}", "{lugar_clean}")'

                    events.append({
                        "fuente": "Conciertos.club",
                        "evento": evento,
                        "fecha": fecha_evento,
                        "hora": hora,
                        "lugar": lugar_hyperlink,
                        "link": link,
                        "disciplina": "Música"
                    })

                    print(f"✅ [{article_idx}-{idx}] {evento} -> {fecha_evento.strftime('%Y-%m-%d')} {hora}")

                except Exception as e:
                    print(f"⚠️ [{article_idx}-{idx}] Error procesando concierto: {e}")
                    continue

    except Exception as e:
        print(f"❌ Error accediendo a conciertos.club: {e}")

    finally:
        driver.quit()

    print(f"🎉 Total conciertos importados: {len(events)}")
    return events




# --------------------------
# Scraping Turismo Asturias
# --------------------------

def get_events_turismoasturias(max_pages=10, tematicas=None):
    from datetime import datetime

    base_url = "https://www.turismoasturias.es/agenda-de-asturias"
    events = []

    for tematica in tematicas or []:
        print(f"🔎 Procesando temática: {tematica}")
        for page in range(1, max_pages + 1):
            url = f"{base_url}/{tematica}?page={page}"
            print(f"🌐 Cargando página {page}: {url}")
            
            try:
                res = requests.get(url, timeout=10)
                soup = BeautifulSoup(res.content, "html.parser")
                items = soup.select("div.card[itemtype='http://schema.org/Event']")
                print(f"📦 Página {page}: {len(items)} eventos encontrados")

                if not items:
                    print(f"🚫 Fin de paginación en página {page}")
                    break

                for idx, item in enumerate(items):
                    try:
                        # Título
                        title_el = item.select_one(".card-title")
                        title = title_el.text.strip() if title_el else "Sin título"

                        # Link
                        link_el = item.select_one("a[itemprop='url']")
                        link = link_el["href"] if link_el else ""
                        if link and not link.startswith("http"):
                            link = f"https://www.turismoasturias.es{link}"

                        # Lugar
                        lugar_el = item.select_one("[itemprop='location'] [itemprop='name']")
                        lugar = lugar_el.text.strip() if lugar_el else "Asturias"

                        # Fechas
                        fecha_evento = None
                        fecha_inicio_raw = item.select_one("[itemprop='startDate']")
                        if fecha_inicio_raw and fecha_inicio_raw.has_attr("date"):
                            try:
                                fecha_evento = datetime.strptime(
                                    fecha_inicio_raw["date"],
                                    "%Y-%m-%d %H:%M:%S.%f"
                                )
                            except Exception as e:
                                print(f"❌ No se pudo parsear startDate: {e}")

                        fecha_fin = None
                        fecha_fin_el = item.select_one("[itemprop='endDate']")
                        if fecha_fin_el and fecha_fin_el.has_attr("date"):
                            try:
                                fecha_fin = datetime.strptime(
                                    fecha_fin_el["date"],
                                    "%Y-%m-%d %H:%M:%S.%f"
                                )
                            except Exception as e:
                                print(f"❌ No se pudo parsear endDate: {e}")
                        else:
                            fecha_fin = fecha_evento

                        if not fecha_evento:
                            print(f"❌ Fecha no reconocida, descartado: {title}")
                            continue

                        # Hora
                        hora_text = ""
                        hora_el = item.select_one(".hour")
                        if hora_el:
                            hora_str = hora_el.get_text(" ", strip=True)
                            for parte in hora_str.split():
                                if ":" in parte:
                                    hora_text = parte
                                    break

                        # Disciplina
                        disciplina = tematica.replace("-", " ").title()
                        disciplina_inferida = inferir_disciplina(title)
                        disciplina = disciplina_inferida

                        # Solo si no está ya añadido
                        if not any(ev["link"] == link for ev in events):
                            events.append({
                                "fuente": "Turismo Asturias",
                                "evento": title,
                                "fecha": fecha_evento,
                                "fecha_fin": fecha_fin,
                                "hora": hora_text,
                                "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
                                "link": link,
                                "disciplina": disciplina
                            })
                        
                        print(f"✅ [{idx}] {title} -> {fecha_evento.strftime('%Y-%m-%d')} {hora_text}")

                    except Exception as e:
                        print(f"⚠️ [Turismo Asturias][{tematica}][{idx}] Error procesando evento: {e}")
                        continue

            except Exception as e:
                print(f"❌ [Turismo Asturias][{tematica}] Error en página {page}: {e}")
                continue

    print(f"🎉 Total eventos Turismo Asturias: {len(events)}")
    return events


# --------------------------
# Scraping Laboral Ciudad de la Cultura
# --------------------------

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


def parse_laboral_cards(cards, visto):
    from urllib.parse import urljoin, quote_plus
    import re
    from datetime import datetime

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



# --------------------------
# Scraping FiestasAsturias API https://www.fiestasdeasturias.com
# --------------------------

SITE_ID = 3649360
SECTION_ID = 60825576  # categoría "Todas"
def get_events_fiestasasturias_api(max_pages=50):


    api_base = "https://api.ww-api.com/front"
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
def get_events_gijon_umami(max_days_ahead=90):
    url = "https://umamigijon.com/cursos/"
    events = []
    driver = get_selenium_driver(headless=True)

    try:
        driver.get(url)
        time.sleep(5)  # esperar carga inicial de JS

        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select("div.mep-event-list-loop.mep_event_grid_item")

        if not cards:
            # pequeño scroll para forzar lazy-load si aplica
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select("div.mep-event-list-loop.mep_event_grid_item")

        for c in cards:
            # --- fecha ---
            parsed_date = None
            date_raw = (c.get("data-date") or "").strip()  # formato: mm/dd/yyyy
            if re.fullmatch(r"\d{2}/\d{2}/\d{4}", date_raw):
                try:
                    parsed_date = datetime.strptime(date_raw, "%m/%d/%Y")
                except Exception:
                    parsed_date = None

            # Fallback: extraer del primer h5 de la fecha (ej. "miércoles, 13 Ago, 2025")
            if not parsed_date:
                h5_date = c.select_one("li.mep_list_event_date .evl-cc h5")
                if h5_date:
                    parsed_date = dateparser.parse(h5_date.get_text(strip=True), languages=["es"])

            if not parsed_date:
                continue  # sin fecha no podemos normalizar ni filtrar

            # Filtra por ventana temporal
            delta_days = (parsed_date.date() - datetime.now().date()).days
            if delta_days < 0 or delta_days > max_days_ahead:
                continue

            # --- título ---
            title = (c.get("data-title") or "").strip()
            if not title:
                h2 = c.select_one(".mep_list_title")
                title = h2.get_text(strip=True) if h2 else "Sin título"

            # --- hora ---
            time_str = ""
            for h in reversed(c.select("li.mep_list_event_date .evl-cc h5")):
                t = h.get_text(strip=True)
                if re.search(r"\d{1,2}:\d{2}", t):
                    time_str = t
                    break

            # --- localización ---
            loc_el = c.select_one("li.mep_list_location_name h5")
            location = loc_el.get_text(strip=True) if loc_el else "Gijón"
            lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location)}", "{location}")'

            # --- link ---
            a = c.select_one("a.plnb-book-now")
            link = a["href"].strip() if a and a.has_attr("href") else url

            # --- disciplina (según tu helper) ---
            disciplina = inferir_disciplina(title)

            # ✅ Evitar duplicados por link
            if any(ev["link"] == link for ev in events):
                print(f"🔁 Evento duplicado saltado: {title}")
                continue

            events.append({
                "fuente": "UmamiGijon",
                "evento": title,
                "fecha": parsed_date,   # datetime, igual que en tu modelo de Oviedo
                "hora": time_str,
                "lugar": lugar,         # fórmula HYPERLINK lista para Excel/Sheets
                "link": link,
                "disciplina": disciplina
            })

            print(f"✅ Gijón/Umami: {title} ({parsed_date.date()})")

    except Exception as e:
        print(f"❌ Error en Gijón/Umami: {e}")
    finally:
        driver.quit()

    print(f"🎉 Total eventos Gijón/Umami: {len(events)}")
    return events


# --------------------------
# Scraping SpainSwing (Asturias) adaptado al modelo Gijón/Oviedo
# --------------------------
def get_events_asturias(max_days_ahead=90):
    from bs4 import BeautifulSoup
    from urllib.parse import quote_plus
    import time, re
    from datetime import datetime
    import dateparser
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    url = "https://spainswingdance.com/eventos-asturias"
    events = []
    driver = get_selenium_driver(headless=True)

    try:
        driver.get(url)

        # Espera a que cargue el calendario (SSR normalmente, pero por si acaso)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article.ics-calendar-list-wrapper"))
            )
        except Exception:
            time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        article = soup.select_one("article.ics-calendar-list-wrapper")
        if not article:
            print("⚠️ No se encontró el contenedor del calendario.")
            return events

        # Recorremos en orden los hijos directos: <h3> (Mes Año) y <div class="ics-calendar-date-wrapper">
        current_year = datetime.now().year

        # hijos directos en orden
        for node in article.find_all(recursive=False):
            classes = node.get("class", [])

            # Encabezado de mes: ej. "Agosto 2025" -> fija año
            if node.name == "h3" and "ics-calendar-label" in classes:
                label = node.get_text(" ", strip=True)  # p.ej. "Agosto 2025"
                parsed_label = dateparser.parse(f"1 {label}", languages=["es"])
                if parsed_label:
                    current_year = parsed_label.year
                continue

            # Día con eventos
            if node.name == "div" and "ics-calendar-date-wrapper" in classes:
                # data-date ej. "12 agosto"
                date_no_year = (node.get("data-date") or "").strip()
                if not date_no_year:
                    # fallback al id del <h4> ej. ...-20250812
                    h4 = node.find("h4", class_="ics-calendar-date")
                    if h4 and h4.has_attr("id"):
                        m = re.search(r"(\d{4})(\d{2})(\d{2})$", h4["id"])
                        if m:
                            y, mo, d = m.groups()
                            parsed_date = datetime(int(y), int(mo), int(d))
                        else:
                            parsed_date = None
                    else:
                        parsed_date = None
                else:
                    parsed_date = dateparser.parse(f"{date_no_year} {current_year}", languages=["es"])

                if not parsed_date:
                    # si no hay fecha, salta el día
                    continue

                # Filtro por ventana temporal
                if max_days_ahead is not None:
                    delta_days = (parsed_date.date() - datetime.now().date()).days
                    if delta_days < 0 or delta_days > max_days_ahead:
                        continue

                # ID ancla del día (para construir link único estable)
                h4 = node.find("h4", class_="ics-calendar-date")
                day_anchor = h4["id"] if h4 and h4.has_attr("id") else parsed_date.strftime("%Y%m%d")

                # Cada evento está como pares DT.time + DD.event
                dls = node.select("dl.events")
                if not dls:
                    continue

                for dl in dls:
                    # Recorremos cada <dd class="event"> y tomamos su <dt class="time"> previa
                    for idx, dd in enumerate(dl.select("dd.event")):
                        # Título
                        title_el = dd.select_one("span.title")
                        title = title_el.get_text(strip=True) if title_el else "Sin título"

                        # Hora (del dt inmediatamente anterior)
                        dt_time = dd.find_previous_sibling("dt", class_="time")
                        time_str = ""
                        if dt_time:
                            # Tomar solo la hora inicial antes del separador "–"
                            raw = dt_time.get_text(" ", strip=True)
                            time_str = raw.split("–")[0].strip()

                        # Localización
                        loc_a = dd.select_one(".descloc .location a")
                        location_text = loc_a.get_text(" ", strip=True) if loc_a else "Asturias"

                        # Link único (no hay enlace propio de evento, generamos ancla estable)
                        # Usamos el id del día + slug del título
                        slug = re.sub(r"\W+", "-", title.strip().lower()).strip("-")
                        link = f"{url}#{day_anchor}-{quote_plus(slug)}"

                        # Disciplina inferida
                        disciplina = inferir_disciplina(title)

                        # Duplicados por link
                        if any(ev["link"] == link for ev in events):
                            print(f"🔁 Evento duplicado saltado: {title}")
                            continue

                        events.append({
                            "fuente": "SpainSwingAsturias",
                            "evento": title,
                            "fecha": parsed_date,
                            "hora": time_str,
                            "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location_text)}", "{location_text}")',
                            "link": link,
                            "disciplina": disciplina
                        })

                        print(f"✅ Asturias (Swing): {title} ({parsed_date.date()})")

    except Exception as e:
        print(f"❌ Error en Asturias (Swing): {e}")
    finally:
        driver.quit()

    print(f"🎉 Total eventos Asturias (Swing): {len(events)}")
    return events

    
    # --------------------------
# Scraping Jarascada (ICS mensual)
# --------------------------
# --------------------------
# Scraping Jarascada (ICS mensual, con headers y fallback Selenium)
# --------------------------
def get_events_jarascada(months_ahead=2, only_future=True, offline_path=None):
    """
    Mes actual + months_ahead. Devuelve misma estructura que Mieres.
    Si el servidor devuelve 403, intenta Selenium.
    Si no hay suerte, como último recurso puede leer un ICS local (offline_path).
    """
    base = "https://www.jarascada.es/feed/my-calendar-ics/"
    events = []
    seen = set()
    hoy = datetime.now().date()

    # --- sesión HTTP con cabeceras "normales"
    session = requests.Session()
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    session.headers.update({
        "User-Agent": UA,
        "Accept": "text/calendar,text/plain,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Referer": "https://www.jarascada.es/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        # "DNT": "1",  # opcional
    })

    def add_months(y, m, delta):
        m2 = m + delta
        y2 = y + (m2 - 1) // 12
        m2 = ((m2 - 1) % 12) + 1
        return y2, m2

    def consume_calendar(cal):
        nonlocal events, seen
        for ev in cal.events:
            title = ev.name or "Sin título"
            link = getattr(ev, "url", None) or "https://www.jarascada.es/eventos/"
            uid = getattr(ev, "uid", None)
            key = (uid, link)
            if key in seen:
                continue
            seen.add(key)

            lugar = ev.location or "Asturias"
            start_dt = getattr(ev, "begin", None)
            if start_dt:
                fecha_evento = start_dt.datetime
                hora_text = "" if getattr(ev, "all_day", False) else fecha_evento.strftime("%H:%M")
            else:
                fecha_evento = None
                hora_text = ""

            if only_future and fecha_evento and fecha_evento.date() < hoy:
                continue

            disciplina = inferir_disciplina(title)

            events.append({
                "fuente": "Jarascada",
                "evento": title,
                "fecha": fecha_evento,
                "hora": hora_text,
                "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
                "link": link,
                "disciplina": disciplina
            })

    # --- bucle mes a mes
    y0, m0 = hoy.year, hoy.month
    for i in range(months_ahead + 1):
        y, m = add_months(y0, m0, i)
        url = f"{base}?time=month&yr={y}&month={m}&dy=1"

        ics_text = None

        # 1) Intento con requests + headers
        for attempt in range(2):
            try:
                resp = session.get(url, timeout=25, allow_redirects=True)
                if resp.status_code == 403:
                    raise requests.HTTPError("403 Forbidden")
                resp.raise_for_status()
                enc = resp.encoding or "utf-8"
                ics_text = resp.text if resp.text else resp.content.decode(enc, errors="ignore")
                break
            except Exception as e:
                print(f"⚠️ Intento {attempt+1} falló en {url}: {e}")
                time.sleep(1.2)

        # 2) Fallback Selenium si seguimos sin texto
        if ics_text is None:
            try:
                from selenium.webdriver.common.by import By  # import local para no romper tu entorno si no usas Selenium
                driver = get_selenium_driver(headless=True)
                driver.get(url)
                time.sleep(2.5)
                try:
                    pre = driver.find_element(By.TAG_NAME, "pre")
                    ics_text = pre.text
                except Exception:
                    # a veces Chrome no envuelve en <pre> y devuelve texto plano directamente
                    ics_text = driver.page_source
                driver.quit()
            except Exception as e:
                print(f"⚠️ Fallback Selenium falló para {url}: {e}")

        # 3) Parsear ICS si lo tenemos
        if ics_text:
            try:
                cal = Calendar(ics_text)
                consume_calendar(cal)
            except Exception as e:
                print(f"⚠️ Error parseando ICS {y}-{m:02d}: {e}")

    # 4) Último recurso: ICS local (para probar parser o “modo offline”)
    if not events and offline_path:
        try:
            with open(offline_path, "r", encoding="utf-8") as f:
                cal = Calendar(f.read())
            consume_calendar(cal)
            print(f"🗂️ Cargados {len(events)} eventos desde offline_path")
        except Exception as e:
            print(f"⚠️ Error leyendo offline_path: {e}")

    print(f"🎉 Total eventos Jarascada: {len(events)}")
    return events


# --------------------------
# Scraping Agenda Gijón (AJAX diario) -> MISMA ESTRUCTURA (events: list[dict])
# --------------------------
# --------------------------
# Scraping Agenda Gijón (EventON) - 7 días vista
# --------------------------
def get_events_agenda_gijon(days_ahead=7):

    BASE = "https://agendagijon.com"
    AJAX = f"{BASE}/wp-admin/admin-ajax.php"
    TZI = ZoneInfo("Europe/Madrid")

    def _canon_link(u: str) -> str:
        """Normaliza enlaces para deduplicar con más fiabilidad."""
        if not u:
            return ""
        u = u.strip()
        pr = urlparse(u)
        pr = pr._replace(query="", fragment="")
        netloc = pr.netloc.lower().replace("www.", "")
        pr = pr._replace(scheme="https", netloc=netloc)
        return urlunparse(pr)

    def _get_nonce(sess: requests.Session) -> str:
        """Obtiene el nonce de EventON desde la home (o páginas comunes)."""
        # Probamos con portada y con /events por si acaso
        for path in ["", "/events", "/agenda", "/eventos"]:
            try:
                r = sess.get(BASE + path, timeout=20)
                r.raise_for_status()
                html = r.text
                # Patrones típicos de EventON para el nonce
                m = re.search(r'["\']nonce["\']\s*:\s*["\']([a-f0-9]{8,20})["\']', html, re.I)
                if not m:
                    m = re.search(r'name=["\']nonce["\']\s+value=["\']([a-zA-Z0-9]+)["\']', html)
                if m:
                    return m.group(1)
            except Exception:
                continue
        print("⚠️ No se pudo extraer nonce; se intentará sin él (puede fallar).")
        return ""

    def _day_bounds_unix(day_dt: datetime) -> tuple[int, int]:
        """Devuelve (start,end) unix del día local Europe/Madrid."""
        # Comienzo y fin del día en hora local (maneja DST vía ZoneInfo)
        start_local = datetime(day_dt.year, day_dt.month, day_dt.day, 0, 0, 0, tzinfo=TZI)
        end_local   = datetime(day_dt.year, day_dt.month, day_dt.day, 23, 59, 59, tzinfo=TZI)
        return int(start_local.timestamp()), int(end_local.timestamp())

    def _build_sc(day_dt: datetime, su: int, eu: int) -> dict:
        """Replica los parámetros SC más relevantes para la ‘daily view’."""
        d, m, y = day_dt.day, day_dt.month, day_dt.year
        return {
            "shortcode[calendar_type]": "daily",
            "shortcode[fixed_day]": str(d),
            "shortcode[fixed_month]": str(m),
            "shortcode[fixed_year]": str(y),
            "shortcode[lang]": "L1",
            "shortcode[view_switcher]": "no",
            "shortcode[show_limit_paged]": "1",
            "shortcode[number_of_months]": "1",
            "shortcode[tiles]": "no",
            "shortcode[mapscroll]": "true",
            "shortcode[filters]": "yes",
            "shortcode[hide_past]": "no",
            "shortcode[livenow_bar]": "yes",
            # Rango de foco (unix)
            "shortcode[focus_start_date_range]": str(su),
            "shortcode[focus_end_date_range]": str(eu),
            # Ajustes vistos en el payload del sitio (no todos son obligatorios)
            "shortcode[hide_end_time]": "no",
            "shortcode[hide_month_headers]": "no",
            "shortcode[event_past_future]": "all",
            "shortcode[event_status]": "all",
            "shortcode[event_location]": "all",
            "shortcode[event_organizer]": "all",
            "shortcode[event_order]": "ASC",
            "shortcode[sort_by]": "sort_date",
            "shortcode[event_tag]": "all",
            "shortcode[event_virtual]": "all",
            "shortcode[show_repeats]": "no",
        }

    def _infer_location_from_block(block: BeautifulSoup) -> str:
        """Del bloque #event_{ID}_0 intenta extraer 'Nombre, Dirección'."""
        if not block:
            return "Gijón"
        # 1) Atributos consolidados
        attr = block.select_one(".event_location_attrs")
        if attr and attr.has_attr("data-location_name"):
            name = attr["data-location_name"].strip()
            addr = attr.get("data-location_address", "").strip()
            if name and addr:
                return f"{name}, {addr}"
            if name:
                return name
        # 2) Texto visible
        loc_name = block.select_one(".evoet_location .event_location_name")
        if loc_name:
            # A veces el sibling incluye la dirección
            tail = loc_name.find_parent().get_text(" ", strip=True)
            # tail suele venir como "Nombre, Dirección..." — devolvemos tal cual
            return tail or loc_name.get_text(" ", strip=True)
        return "Gijón"

    def _get_event_url_from_block(block: BeautifulSoup) -> str:
        """Del bloque extrae URL priorizando JSON-LD (schema)."""
        if not block:
            return ""
        # JSON-LD con la URL del evento en agendagijon.com
        script = block.select_one(".evo_event_schema script[type='application/ld+json']")
        if script and script.string:
            try:
                data = json.loads(script.string)
                url = data.get("url") or ""
                if url:
                    return url
            except Exception:
                pass
        # Fallback: enlace visible (suele ser exlink a gijon.es)
        a = block.select_one("a.evcal_list_a")
        if a and a.has_attr("href"):
            return a["href"]
        return ""

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": BASE + "/",
        "Origin": BASE,
    })

    nonce = _get_nonce(sess)
    events = []

    # Ventana: hoy + days_ahead-1
    today_local = datetime.now(TZI).date()
    for i in range(days_ahead):
        day = datetime.combine(today_local + timedelta(days=i), datetime.min.time()).replace(tzinfo=TZI)
        su, eu = _day_bounds_unix(day)

        # Construcción del payload (action + SC + tipo de vista)
        data = {
            "action": "the_ajax_ev_cal",
            "ajaxtype": "dv_newday",
            "nonce": nonce,
        }
        data.update(_build_sc(day, su, eu))

        try:
            r = sess.post(AJAX, data=data, timeout=25)
            # Algunos WAF devuelven 400 si el nonce caducó: reintentar 1 vez con nuevo nonce
            if r.status_code == 400:
                nonce = _get_nonce(sess)
                data["nonce"] = nonce
                r = sess.post(AJAX, data=data, timeout=25)

            r.raise_for_status()
            payload = r.json()
        except Exception as e:
            print(f"⚠️ {day.date()} error AJAX: {e}")
            continue

        items = payload.get("json", []) or []
        html = payload.get("html", "") or ""
        soup = BeautifulSoup(html, "html.parser")

        print(f"🗓️ {day.date()} → {len(items)} items crudos del AJAX")

        for it in items:
            try:
                title = (it.get("event_title") or "").strip() or "Sin título"

                # Hora: preferimos _start_hour/_start_minute del payload meta
                pmv = it.get("event_pmv", {}) or {}
                sh = pmv.get("_start_hour", [""])
                sm = pmv.get("_start_minute", [""])
                sh = sh[0] if isinstance(sh, list) else sh
                sm = sm[0] if isinstance(sm, list) else sm
                hora_text = ""
                if str(sh).isdigit() and str(sm).isdigit():
                    hora_text = f"{int(sh):02d}:{int(sm):02d}"

                # Fecha (datetime) desde unix + offset del item (para local)
                start_ts = it.get("event_start_unix") or it.get("unix_start")
                tz_off = it.get("timezone_offset", 0)  # típicamente -7200 en verano
                fecha_dt = None
                if start_ts:
                    dt_utc = datetime.utcfromtimestamp(int(start_ts)).replace(tzinfo=timezone.utc)
                    fecha_dt = (dt_utc - timedelta(seconds=int(tz_off))).astimezone(TZI)
                else:
                    # Fallback: el día que estamos iterando (sin hora)
                    fecha_dt = day

                # Bloque HTML por ID para extraer link/lugar
                _id = it.get("ID") or it.get("event_id")
                block = soup.select_one(f"#event_{_id}_0") if _id else None

                # Link: priorizamos URL del post (agendagijon.com). Si no, exlink.
                url_ev = _get_event_url_from_block(block)
                if not url_ev:
                    exl = pmv.get("evcal_exlink", "")
                    if isinstance(exl, list):
                        url_ev = exl[0] if exl else ""
                    elif isinstance(exl, str):
                        url_ev = exl
                if not url_ev:
                    url_ev = f"{BASE}/?event_id={_id}" if _id else BASE + "/"

                link = _canon_link(url_ev)

                # Lugar
                lugar_texto = _infer_location_from_block(block)

                # Disciplina
                disciplina = inferir_disciplina(title)

                # Duplicados por link canonicalizado
                if any(_canon_link(ev["link"]) == link for ev in events):
                    print(f"🔁 Duplicado saltado: {title} ({link})")
                    continue

                events.append({
                    "fuente": "AgendaGijon",
                    "evento": title,
                    "fecha": fecha_dt,
                    "hora": hora_text,
                    "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar_texto)}", "{lugar_texto}")',
                    "link": link,
                    "disciplina": disciplina
                })
                print(f"  ➕ {title} @ {hora_text} / {lugar_texto}")

            except Exception as ex:
                print(f"⚠️ Item malformado saltado: {ex}")
                continue

        # Pequeño respiro entre días para no disparar el WAF
        time.sleep(0.8)

    print(f"🎉 Total eventos Agenda Gijón: {len(events)}")
    return events
    
def inferir_disciplina(titulo):
    titulo = titulo.lower()

    if any(p in titulo for p in ["cine", "film", "película", "documental", "corto", "largometraje"]):
        return "Cine"
    elif any(p in titulo for p in ["teatro", "representación", "obra", "actor", "actriz", "escénica", "escénico"]):
        return "Artes Escénicas"
    elif any(p in titulo for p in ["jazz", "música", "concierto", "recital", "banda", "coro", "cantante", "orquesta", "piano", "metal", "rock", "hip hop", "rap", "trap", "funk", "reguetón", "reggaeton"]):
        return "Música"
    elif any(p in titulo for p in ["exposición", "fotografía", "fotográfica", "escultura", "pintura", "arte", "visual", "galería", "retratos", "acuarela", "óleo", "speculum"]):  # ✅ añadido fotografía, fotográfica, speculum
        return "Artes Visuales"
    elif any(p in titulo for p in ["cuentos", "narración", "cuentacuentos", "oral"]):
        return "Narración Oral"
    elif any(p in titulo for p in ["charla", "conferencia", "coloquio", "debate", "tertulia", "mesa redonda"]):
        return "Conferencias"
    elif any(p in titulo for p in ["libro", "literatura", "autor", "poesía", "novela", "lectura", "ensayo"]):
        return "Literatura"
    elif any(p in titulo for p in ["danza", "ballet", "baile", "folklore", "folclore", "coreografía"]):
        return "Danza"
    elif any(p in titulo for p in ["taller", "formación", "curso", "clase", "aprende", "iniciación", "workshop"]):
        return "Formación / Taller"
    elif any(p in titulo for p in ["tradicional", "astur", "costumbre"]):
        return "Cultura Tradicional"
    elif any(p in titulo for p in ["visita guiada", "visitas guiadas", "ruta", "rutas", "patrimonio", "historia", 
                                   "arqueología", "recorrido", "descubre", "bus turístico", "georuta", 
                                   "ruta turística", "rutas turísticas"]):  # ✅ añadido términos más concretos
        return "Itinerarios Patrimoniales"
    elif any(p in titulo for p in ["infantil", "niños", "niñas", "peques", "familia", "familiares", 
                                   "campamento", "campamentos", "vacaciones activas", "campamentos urbanos"]):  # ✅ añadido campamento
        return "Público Infantil / Familiar"
    elif any(p in titulo for p in ["deporte", "actividad física", "cicloturista", "carrera", "juegas"]):  # ✅ añadido deportes y juegas
        return "Deportes / Actividad Física"
    elif any(p in titulo for p in ["medioambiente", "sostenibilidad", "reciclaje", "clima", "ecología", "verde"]):
        return "Medio Ambiente"
    elif any(p in titulo for p in ["salud", "bienestar", "cuidados", "prevención", "psicología", "enfermedad"]):
        return "Salud y Bienestar"
    elif any(p in titulo for p in ["tecnología", "innovación", "inteligencia artificial", "digital", "robot", "software", "automatizados"]):
        return "Tecnología / Innovación"
    elif any(p in titulo for p in ["gastronomía", "degustación", "vino", "cocina", "culinario", "gastro",
                                   "jornadas", "tostas", "tapas", "sidra", "cerveza", "fresa", "bonito"]):
        return "Gastronomía"
    elif any(p in titulo for p in ["igualdad", "género", "inclusión", "diversidad", "social", "solidaridad"]):
        return "Sociedad / Inclusión"
    elif any(p in titulo for p in ["fiestas", "fiesta", "romería", "verbena"]):
        return "Fiestas"
    elif any(p in titulo for p in ["puertas abiertas", "jornada abierta", "encuentro"]):
        return "Divulgación / Institucional"
    elif any(p in titulo for p in ["varios", "mixto", "combinado", "múltiple", "multidisciplinar", "radar"]):
        return "Multidisciplinar"
    elif any(p in titulo for p in ["laboral", "actividad especial"]):
        return "Actividades especiales"
    elif any(p in titulo for p in ["fiesta", "festival", "fest", "evento", "celebración", "espectáculo"]):
        return "Eventos"
    else:
        return "Otros"
