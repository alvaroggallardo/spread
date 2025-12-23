"""
Scraper para eventos - Aviles.
"""

from app.scrapers.base import *

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


