"""
Scraper para eventos - Aviles.
"""

from app.scrapers.base import *
import requests
import os


def get_events_aviles():
    url = "https://aviles.es/proximos-eventos"
    events = []

    # Respetar proxies del entorno (corporativo / CI / sistema)
    proxies = {
        "http": os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY"),
        "https": os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY"),
    }

    try:
        response = requests.get(
            url,
            timeout=60,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "es-ES,es;q=0.9"
            },
            proxies=proxies if any(proxies.values()) else None
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
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

            # Link del popup
            link = ""
            btn = card.select_one("div.btn.btn-primary")
            if btn and btn.has_attr("onclick"):
                onclick_attr = btn["onclick"]
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

            disciplina = inferir_disciplina(title)

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

    print("Total eventos Aviles: {}".format(len(events)))
    return events
