"""
Scraper para eventos - Conciertos Club.
"""

from app.scrapers.base import *

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


