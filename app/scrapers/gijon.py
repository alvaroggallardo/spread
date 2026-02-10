"""
Scraper para eventos - Aviles.
"""

from app.scrapers.base import *

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_events_aviles():
    url = "https://aviles.es/proximos-eventos"
    events = []

    # Importante: NO headless para evitar el cuelgue del renderer
    driver = get_selenium_driver(headless=False)

    try:
        driver.set_page_load_timeout(60)
        driver.set_script_timeout(60)

        driver.get(url)

        # Esperar a que existan las cards
        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.card.border-info"))
        )

        time.sleep(1)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.select("div.card.border-info")
        print("Aviles: {} eventos encontrados".format(len(cards)))

        if not cards:
            print("No hay eventos en Aviles.")
            return events

        for idx, card in enumerate(cards):
            # Titulo
            title_el = card.select_one("h5")
            title = title_el.get_text(strip=True) if title_el else "Sin titulo"
            print("[{}] Titulo: {}".format(idx, title))

            # Link del popup (onclick del boton)
            link = ""
            btn = card.select_one("div.btn.btn-primary")
            if btn and btn.has_attr("onclick"):
                onclick_attr = btn["onclick"].strip()
                if "showPopup('" in onclick_attr:
                    try:
                        relative_url = onclick_attr.split("showPopup('")[1].split("'")[0]
                        link = "https://aviles.es{}".format(relative_url)
                    except Exception:
                        link = ""

            # Fecha y hora
            inicio_text = ""
            for badge in card.select("span.badge"):
                badge_text = badge.get_text(strip=True)
                if "INICIO" in badge_text:
                    inicio_text = badge_text.replace("INICIO:", "").strip()
                    break

            fecha_evento = dateparser.parse(inicio_text, languages=["es"])
            if not fecha_evento:
                print("[{}] Fecha no reconocida, descartado.".format(idx))
                continue

            # Hora
            hora_text = ""
            try:
                hora_text = fecha_evento.strftime("%H:%M")
            except Exception:
                hora_text = ""

            # Lugar
            lugar = "Aviles"
            card_text = card.select_one("div.card-text")
            if card_text:
                full_text = card_text.get_text(" ", strip=True)
                if "Lugar:" in full_text:
                    raw_lugar = full_text.split("Lugar:")[-1].strip()
                    lugar = raw_lugar.split("(")[0].strip().rstrip(".")

            # Inferir disciplina a partir del titulo
            disciplina = inferir_disciplina(title)

            # Construir evento
            events.append({
                "fuente": "Aviles",
                "evento": title,
                "fecha": fecha_evento,
                "hora": hora_text,
                "lugar": '=HYPERLINK("https://www.google.com/maps/search/?api=1&query={}", "{}")'.format(
                    quote_plus(lugar), lugar
                ),
                "link": link,
                "disciplina": disciplina
            })

            print("[{}] Aniadido.".format(idx))

    except Exception as e:
        print("Error en Aviles: {}".format(e))

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    print("Total eventos Aviles: {}".format(len(events)))
    return events
