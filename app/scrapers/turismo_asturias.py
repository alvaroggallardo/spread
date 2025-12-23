"""
Scraper para eventos - Turismo Asturias.
"""

from app.scrapers.base import *

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


