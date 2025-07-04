import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment
import json
from geopy.geocoders import Nominatim
import dateparser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
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
                link = "https://aviles.es" + relative_url

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



def get_events_siero(fechas_objetivo):
    url = "https://www.ayto-siero.es/agenda/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    eventos = []

    event_wrappers = soup.select("div.ectbe-inner-wrapper")

    for e in event_wrappers:
        try:
            # Título y enlace
            title_el = e.select_one("div.ectbe-evt-title a.ectbe-evt-url")
            title = title_el.text.strip() if title_el else "Sin título"
            link = title_el["href"] if title_el and title_el.has_attr("href") else url

            # Fecha
            day_el = e.select_one("span.ectbe-ev-day")
            month_el = e.select_one("span.ectbe-ev-mo")
            year_el = e.select_one("span.ectbe-ev-yr")
            if not (day_el and month_el and year_el):
                continue
            fecha_str = f"{day_el.text.strip()} {month_el.text.strip()} {year_el.text.strip()}"
            fecha = dateparser.parse(fecha_str, languages=["es"])

            if not fecha or fecha.date() not in fechas_objetivo:
                continue

            # Lugar
            lugar_el = e.select_one("span.ectbe-address")
            if lugar_el:
                lugar = lugar_el.get_text(separator=" ", strip=True)
                lugar = lugar.split(",")[0].strip()  # Tomar sólo el nombre del sitio antes de la coma
            else:
                lugar = "Siero"
            lugar_hyperlink = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")'

            # Hora - desde la página del evento
            hora = ""
            try:
                detalle = requests.get(link)
                if detalle.status_code == 200:
                    soup_detalle = BeautifulSoup(detalle.text, "html.parser")
                    hora_span = soup_detalle.select_one("div.tecset-date span.tribe-event-date-start")
                    if hora_span and "|" in hora_span.text:
                        hora = hora_span.text.split("|")[1].strip()
            except Exception as ex:
                print(f"⚠️ No se pudo extraer la hora desde {link}: {ex}")

            eventos.append({
                "fuente": "Siero",
                "evento": title,
                "fecha": fecha,
                "hora": hora,
                "lugar": lugar_hyperlink,
                "link": link
            })

        except Exception as e:
            print(f"⚠️ Error procesando un evento de Siero: {e}")
            continue

    return eventos


def get_events_conciertosclub(fechas_objetivo):
    from urllib.parse import urljoin

    base_url = "https://conciertos.club"
    url = f"{base_url}/search.php?artist_id=&local_id=&provin_id=13&estilo_id=&fecha1=&fecha2="
    eventos = []

    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        conciertos = soup.select("li[itemtype='http://schema.org/MusicEvent']")
        print(f"🔍 Se encontraron {len(conciertos)} conciertos en conciertos.club")

        for concierto in conciertos:
            try:
                # Título y enlace
                enlace_el = concierto.select_one("a.nombre")
                link = urljoin(base_url, enlace_el["href"]) if enlace_el else base_url
                evento = enlace_el.get_text(strip=True) if enlace_el else "Sin título"

                # Fecha
                fecha_meta = concierto.select_one("meta[itemprop='startDate']")
                fecha_raw = fecha_meta["content"] if fecha_meta else None
                fecha = dateparser.parse(fecha_raw) if fecha_raw else None

                if not fecha or fecha.date() not in fechas_objetivo:
                    continue

                # Hora extraída correctamente
                time_div = concierto.select_one("div.time")
                hora = ""
                if time_div:
                    time_parts = list(time_div.stripped_strings)
                    if len(time_parts) > 1:
                        hora = time_parts[1].strip()

                # Lugar limpio
                lugar_el = concierto.select_one("a.local")
                lugar_raw = lugar_el.get_text(strip=True) if lugar_el else "Asturias"
                lugar = lugar_raw.split(".")[0] if "." in lugar_raw else lugar_raw

                eventos.append({
                    "fuente": "Conciertos.club",
                    "evento": evento,
                    "fecha": fecha,
                    "hora": hora,
                    "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
                    "link": link,
                    "disciplina": "Música"
                })

            except Exception as e:
                print(f"⚠️ Error procesando un concierto: {e}")
    except Exception as e:
        print(f"❌ Error accediendo a conciertos.club: {e}")

    return eventos


def obtener_eventos_por_tematica(tematicas, fechas_objetivo):
    base_url = "https://www.turismoasturias.es/agenda-de-asturias"
    eventos = []

    for tematica in tematicas:
        url = f"{base_url}/{tematica}"
        print(f"🔍 Procesando temática: {tematica}")
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            tarjetas_evento = soup.select('div.card[itemtype="http://schema.org/Event"]')

            for tarjeta in tarjetas_evento:
                try:
                    nombre = tarjeta.select_one('.card-title').get_text(strip=True)
                    enlace = tarjeta.select_one('a[itemprop="url"]')['href']
                    lugar = tarjeta.select_one('[itemprop="location"] [itemprop="name"]').get_text(strip=True)

                    fecha_inicio_raw = tarjeta.select_one('[itemprop="startDate"]')['date']
                    fecha_fin_el = tarjeta.select_one('[itemprop="endDate"]')
                    fecha_fin_raw = fecha_fin_el['date'] if fecha_fin_el else fecha_inicio_raw

                    fecha_inicio = dateparser.parse(fecha_inicio_raw)
                    fecha_fin = dateparser.parse(fecha_fin_raw)

                    # ❗ Filtrar por fechas_objetivo
                    if not any(
                        fecha_inicio.date() <= objetivo <= fecha_fin.date()
                        for objetivo in fechas_objetivo
                    ):
                        continue

                    # Hora
                    hora = ""
                    hora_el = tarjeta.select_one('.hour')
                    if hora_el:
                        hora_text = hora_el.get_text(" ", strip=True)
                        for parte in hora_text.split():
                            if ":" in parte:
                                hora = parte.strip()
                                break

                    eventos.append({
                        "fuente": "Turismo Asturias",
                        "evento": nombre,
                        "link": enlace,
                        "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
                        "fecha": fecha_inicio,
                        "fecha_fin": fecha_fin,
                        "hora": hora,
                        "disciplina": tematica.replace("-", " ").title()
                    })
                except Exception as e:
                    print(f"⚠️ Error procesando evento en '{tematica}': {e}")
                    continue
        except Exception as e:
            print(f"❌ Error accediendo a {url}: {e}")

    return eventos


def get_events_laboral(fechas_objetivo):
    base_url = "https://www.laboralciudaddelacultura.com"
    base_path = "/agenda"
    eventos = []

    categorias = {
        "Actividades especiales": "3564612",
        "Artes escénicas": "3564367",
        "Cine": "3564438",
        "Conciertos": "3564072",
        "Convocatorias": "3575028",
        "Eventos": "3570318",
        "Exposiciones": "3564667",
        "Talleres": "3564323",
        "Vamos a imaginar!": "3569154",
        "Vamos a la danza!": "3575683",
        "Vamos a la música!": "3575513",
        "Vamos al cine!": "3577637",
        "Vamos al teatro!": "3569057",
        "Vamos escolar!": "3569038"
    }

    for disciplina, cat_id in categorias.items():
        params = {
            "p_p_id": "as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_kiUgFekyAvs3",
            "p_p_lifecycle": "0",
            "_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_kiUgFekyAvs3_calendarPath": "/html/suite/displays/list.jsp",
            "p_r_p_startDate": "",
            "p_r_p_endDate": "",
            "p_r_p_searchText": "",
            "p_r_p_categoryId": "0",
            "p_r_p_categoryIds": cat_id,
            "_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_kiUgFekyAvs3_calendarId": "0",
            "p_r_p_tag": "",
            "p_r_p_time": "",
            "_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_kiUgFekyAvs3_cur": "1",
            "_as_asac_calendar_suite_CalendarSuitePortlet_INSTANCE_kiUgFekyAvs3_delta": "60"
        }

        try:
            res = requests.get(urljoin(base_url, base_path), params=params)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            cards = soup.select("div.card[itemtype='http://schema.org/Event']")

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

                # ❗ Filtro por fechas objetivo
                if not any(start_dt.date() <= f <= end_dt.date() for f in fechas_objetivo):
                    continue

                hora_el = card.select_one("span.d-block.hour")
                if hora_el:
                    hora_text = hora_el.get_text(" ", strip=True)
                    match = re.search(r"\b\d{1,2}:\d{2}\b", hora_text)
                    hora = match.group(0) if match else ""
                else:
                    hora = ""

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
        except Exception as e:
            print(f"Error accediendo a la categoría '{disciplina}': {e}")

    return eventos


# Constantes con los IDs conocidos
SITE_ID = 3649360
SECTION_ID = 60825576  # la categoría "Todas" que incluye todos los eventos

def get_events_fiestas_api(fechas_objetivo):
    """
    Descarga todos los eventos de FiestasAsturias.com en la sección 'Todas',
    y filtra internamente por las fechas objetivo, incluyendo eventos en rango.
    """
    api_base = "https://api.ww-api.com/front"
    eventos = []
    page = 1

    while True:
        items_url = (
            f"{api_base}/get_items/{SITE_ID}/{SECTION_ID}/"
            f"?category_index=0&page={page}&per_page=24"
        )
        res = requests.get(items_url)
        if res.status_code != 200:
            break
        data = res.json()

        for it in data.get("items", []):
            # --- parse inicio ---
            dt_start = dateparser.parse(it.get("date", ""))
            if not dt_start:
                continue
            if dt_start.tzinfo is not None:
                dt_start = dt_start.replace(tzinfo=None)

            # --- parse fin (o lo igualamos al inicio) ---
            end_raw = it.get("endDate", "")
            if end_raw:
                dt_end = dateparser.parse(end_raw)
                if dt_end and dt_end.tzinfo is not None:
                    dt_end = dt_end.replace(tzinfo=None)
            else:
                dt_end = dt_start

            # --- filtro por cualquier fecha objetivo dentro del rango ---
            if not any(dt_start.date() <= f <= dt_end.date() for f in fechas_objetivo):
                continue

            # --- lugar con coordenadas o dirección ---
            lat = it.get("latitude")
            lon = it.get("longitude")
            address = it.get("address", "")
            if lat and lon:
                lugar = (
                    f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={lat},{lon}", '
                    f'"{address or f"{lat},{lon}"}")'
                )
            elif address:
                url = it.get("address_url", "")
                lugar = f'=HYPERLINK("{url}", "{address}")'
            else:
                lugar = ""

            eventos.append({
                "fuente": "FiestasAsturias API",
                "evento": it.get("title", "Sin título"),
                "fecha": dt_start,
                "fecha_fin": dt_end,
                "hora": dt_start.strftime("%H:%M") if dt_start.hour else "",
                "lugar": lugar,
                "link": it.get("url", ""),
            })

        if not data.get("next_page"):
            break
        page += 1

    return eventos


def get_events_asturtur(fechas_objetivo):
    base = "https://asturtur.com"
    url = f"{base}/7-dias-en-asturias"
    events = []
    today = datetime.now()

    meses = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
        "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
        "octubre": 10, "noviembre": 11, "diciembre": 12
    }

    try:
        res = requests.get(url)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.select("div.card-body")

        for card in cards:
            title_el = card.select_one("h3.node__title .field--name-title")
            title = title_el.get_text(strip=True) if title_el else "Sin título"

            art = card.find_parent("article")
            a_block = art.find_parent("a", class_="a-block") if art else None
            link = urljoin(base, a_block["href"]) if (a_block and a_block.has_attr("href")) else url

            category = card.select_one("span.tipoevent")
            category = category.get_text(strip=True) if category else ""

            span_fecha = card.select_one("span.iconed-data-item img[alt='Cuándo']")
            raw = span_fecha.parent.get_text(" ", strip=True) if span_fecha else ""

            dt = None
            hora = ""

            m1 = re.match(r'^[A-Za-zÁÉÍÓÚÜÑñ]{2,4}\.\s*(\d{1,2}),\s*(\d{1,2})[.:](\d{2})h?', raw)
            if m1:
                day_i, hour_i, min_i = map(int, m1.groups())
                if day_i >= today.day:
                    month_i, year_i = today.month, today.year
                else:
                    month_i, year_i = (1, today.year + 1) if today.month == 12 else (today.month + 1, today.year)
                dt = datetime(year_i, month_i, day_i, hour_i, min_i)
                hora = dt.strftime("%H:%M")
            else:
                m2 = re.match(
                    r'^[A-Za-zÁÉÍÓÚÜÑñ]{2,4}\.\s*(\d{1,2})\s+de\s+([A-Za-zñÑ]+),\s*(\d{1,2})[.:](\d{2})h?',
                    raw
                )
                if m2:
                    day_i = int(m2.group(1))
                    month_name = m2.group(2).lower()
                    hour_i = int(m2.group(3))
                    min_i = int(m2.group(4))
                    month_i = meses.get(month_name, today.month)
                    year_i = today.year
                    if month_i < today.month:
                        year_i += 1
                    dt = datetime(year_i, month_i, day_i, hour_i, min_i)
                    hora = dt.strftime("%H:%M")
                else:
                    clean = raw.replace(",", "").replace("h", "").replace(".", ":")
                    dt = dateparser.parse(clean, languages=["es"])
                    if dt:
                        hora = dt.strftime("%H:%M")
                    else:
                        continue

            # 💡 FILTRO: solo si la fecha está en el conjunto objetivo
            if not dt or dt.date() not in fechas_objetivo:
                continue

            loc_txt = ""
            try:
                d = requests.get(link)
                d.raise_for_status()
                dsoup = BeautifulSoup(d.text, "html.parser")
                cont = dsoup.select_one("span.lh-1")
                if cont:
                    parts = [sp.get_text(strip=True).lstrip("@") for sp in cont.select("span.smaller90")]
                    loc_txt = " ".join(parts)
            except Exception:
                loc_txt = ""

            lugar = ""
            if loc_txt:
                q = quote_plus(loc_txt)
                lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={q}", "{loc_txt}")'

            events.append({
                "fuente": "Asturtur",
                "evento": title,
                "categoria": category,
                "fecha": dt,
                "hora": hora,
                "lugar": lugar,
                "link": link
            })

    except Exception as e:
        print(f"❌ Error en Asturtur: {e}")

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
