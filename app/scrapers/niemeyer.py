"""
Scraper para eventos - Centro Niemeyer (Aviles)
"""

from app.scrapers.base import *

def get_events_centro_niemeyer(max_days_ahead=180, max_pages=6):
    base_url = "https://www.centroniemeyer.es/programacion/"
    events = []
    today = datetime.now().date()

    for page in range(1, max_pages + 1):
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}page/{page}/"

        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("li.programa-listado")

            if not items:
                break

            for it in items:
                try:
                    a = it.select_one("a.programa-listado-enlace")
                    if not a:
                        continue

                    link = a.get("href", "").strip()
                    if not link:
                        continue

                    if any(ev["link"] == link for ev in events):
                        continue

                    title_el = it.select_one(".programa-listado-titular span")
                    title = title_el.get_text(" ", strip=True) if title_el else "Sin titulo"

                    cat_el = it.select_one(".programa-cat")
                    categoria = cat_el.get_text(strip=True) if cat_el else ""

                    fecha_el = it.select_one(".programa-fecha")
                    fecha_txt = fecha_el.get_text(" ", strip=True).lower() if fecha_el else ""

                    fecha_inicio = None
                    fecha_fin = None
                    hora = ""

                    if "desde el" in fecha_txt and "hasta el" in fecha_txt:
                        m = re.search(r"desde el (.+?) hasta el (.+)$", fecha_txt)
                        if not m:
                            continue

                        fecha_inicio = dateparser.parse(m.group(1), languages=["es"])
                        fecha_fin = dateparser.parse(m.group(2), languages=["es"])

                    else:
                        fecha_inicio = dateparser.parse(fecha_txt, languages=["es"])
                        if fecha_inicio:
                            hora = fecha_inicio.strftime("%H:%M")

                    if not fecha_inicio:
                        continue

                    # Filtrado temporal
                    if fecha_inicio.date() < today:
                        if fecha_fin and fecha_fin.date() >= today:
                            pass
                        else:
                            continue

                    if (fecha_inicio.date() - today).days > max_days_ahead:
                        continue

                    lugar_txt = "Centro Niemeyer, Aviles"
                    lugar = f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar_txt)}", "{lugar_txt}")'

                    disciplina = categoria or inferir_disciplina(title)

                    events.append({
                        "fuente": "CentroNiemeyer",
                        "evento": title,
                        "fecha": fecha_inicio,
                        "fecha_fin": fecha_fin,
                        "hora": hora,
                        "lugar": lugar,
                        "link": link,
                        "disciplina": disciplina
                    })

                except Exception as e:
                    print(f"Error procesando evento Niemeyer: {e}")

        except Exception as e:
            print(f"Error accediendo a {url}: {e}")
            break

    print(f"Total eventos Centro Niemeyer: {len(events)}")
    return events
