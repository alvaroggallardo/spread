"""
Scraper para eventos - Agenda Gijon.
"""

from app.scrapers.base import *

def get_events_agenda_gijon(days_ahead=7):
    BASE = "https://agendagijon.com"

    # TZ Madrid si está disponible
    try:
        TZI = ZoneInfo("Europe/Madrid")
    except Exception:
        TZI = None

    # --- utilidades de fecha ---
    def _onedayplus_bounds(d: datetime) -> tuple[int, int]:
        # ventana onedayplus: 10:00 del día anterior -> 09:59:59 del día d (hora local)
        if TZI:
            start = (datetime(d.year, d.month, d.day, 10, 0, 0, tzinfo=TZI) - timedelta(days=1))
            end = datetime(d.year, d.month, d.day, 9, 59, 59, tzinfo=TZI)
        else:
            start = datetime(d.year, d.month, d.day, 10, 0, 0) - timedelta(days=1)
            end = datetime(d.year, d.month, d.day, 9, 59, 59)
        return int(start.timestamp()), int(end.timestamp())

    def _parse_dt_from_unix(start_unix):
        if not start_unix:
            return None
        try:
            ts = int(start_unix)
            return datetime.fromtimestamp(ts, tz=TZI) if TZI else datetime.fromtimestamp(ts)
        except Exception:
            return None

    def _parse_start_dt_from_box_slow(box):
        # meta[itemprop="startDate"]
        meta = box.select_one('meta[itemprop="startDate"]')
        dt_str = meta.get("content") if meta else None

        # JSON-LD
        if not dt_str:
            for s in box.select('script[type="application/ld+json"]'):
                try:
                    j = json.loads(s.string or "{}")
                    if isinstance(j, dict) and j.get("startDate"):
                        dt_str = j["startDate"]; break
                except Exception:
                    pass
        if not dt_str:
            return None

        if "+0:00" in dt_str:
            dt_str = dt_str.replace("+0:00", "+00:00")

        try:
            dt = parser.parse(dt_str)
        except Exception:
            try:
                dt = datetime.fromisoformat(dt_str)
            except Exception:
                return None

        if dt.tzinfo is None and TZI:
            dt = dt.replace(tzinfo=TZI)
        return dt

    # --- estado del calendario en DOM ---
    def _get_fixed_from_dom(driver):
        try:
            sc_raw = driver.execute_script(
                "return document.querySelector('.evo_cal_data')?.getAttribute('data-sc') || '';"
            )
            if not sc_raw:
                return 0, 0, 0, {}
            sc = json.loads(sc_raw)
            fd = int(sc.get("fixed_day") or 0)
            fm = int(sc.get("fixed_month") or 0)
            fy = int(sc.get("fixed_year") or 0)
            return fd, fm, fy, sc
        except Exception:
            return 0, 0, 0, {}

    def _wait_events_loaded(driver, timeout=12):
        try:
            WebDriverWait(driver, timeout).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#evcal_list .eventon_list_event")),
                    EC.text_to_be_present_in_element((By.ID, "evcal_list"), "No hay eventos")
                )
            )
            return True
        except Exception:
            return False

    # --- intentar ir al día siguiente y validar .evo_cal_data ---
    def _goto_next_day_and_wait(driver, target_date):
        prev_fd, prev_fm, prev_fy, _ = _get_fixed_from_dom(driver)
        # intenta varias veces por si el click no “engancha”
        for _ in range(3):
            try:
                nxt = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "evcal_next")))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", nxt)
                driver.execute_script("arguments[0].click();", nxt)
            except Exception:
                driver.execute_script("document.getElementById('evcal_next')?.click();")

            _wait_events_loaded(driver, timeout=12)

            # esperar a que cambien los fixed_* (o coincidan con objetivo)
            try:
                WebDriverWait(driver, 8).until(
                    lambda d: _get_fixed_from_dom(d)[:3] != (prev_fd, prev_fm, prev_fy)
                )
            except Exception:
                pass

            fd, fm, fy, _ = _get_fixed_from_dom(driver)
            if (fd, fm, fy) == (target_date.day, target_date.month, target_date.year):
                return True

            prev_fd, prev_fm, prev_fy = fd, fm, fy

        print("⚠️ La vista no cambió al día objetivo tras 'siguiente'")
        return False

    # --- recolectar desde DOM (día visible) filtrando por fecha exacta ---
    seen_keys = set()

    def _collect_from_dom(driver, expected_date, debug_label=""):
        soup = BeautifulSoup(driver.page_source, "html.parser")
        boxes = soup.select("#evcal_list .eventon_list_event")
        events_day = []

        # año visible (fallback opcional)
        year_visible = expected_date.year
        head = soup.select_one(".evo_month_title")
        if head:
            try:
                lbl = head.get_text(" ", strip=True)
                ydt = dateparser.parse(f"1 {lbl}", languages=["es"])
                if ydt:
                    year_visible = ydt.year
            except Exception:
                pass

        for box in boxes:
            eid = box.get("data-event_id")
            if not eid:
                bid = box.get("id", "")
                m = re.search(r"event_(\d+)_", bid)
                eid = m.group(1) if m else None

            data_time = box.get("data-time") or ""
            start_unix = data_time.split("-")[0] if data_time else ""
            dt = _parse_dt_from_unix(start_unix) or _parse_start_dt_from_box_slow(box)

            if not dt:
                try:
                    d_el = box.select_one(".evo_start .date")
                    m_el = box.select_one(".evo_start .month")
                    dd = int(d_el.get_text(strip=True)) if d_el else expected_date.day
                    mm = (m_el.get_text(strip=True) if m_el else "")
                    dt = dateparser.parse(f"{dd} {mm} {year_visible}", languages=["es"]) or datetime.combine(expected_date, datetime.min.time())
                except Exception:
                    dt = datetime.combine(expected_date, datetime.min.time())
                if TZI and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=TZI)

            # filtro estricto por fecha del día que pedimos
            if dt.date() != expected_date:
                continue

            title_el = box.select_one(".evcal_event_title")
            title = title_el.get_text(" ", strip=True) if title_el else "Sin título"
            title_norm = re.sub(r"\s+", " ", title.strip().lower())

            # link preferente JSON-LD
            link = None
            for s in box.select('script[type="application/ld+json"]'):
                try:
                    j = json.loads(s.string or "{}")
                    if isinstance(j, dict) and j.get("url"):
                        link = j["url"]; break
                except Exception:
                    pass
            if not link:
                a = box.select_one("a[href]")
                if a:
                    link = a.get("href")
            if not link:
                link = BASE + "/"

            # localización
            attrs = box.select_one(".event_location_attrs")
            if attrs:
                name = attrs.get("data-location_name") or ""
                addr = attrs.get("data-location_address") or ""
                location_text = f"{name}, {addr}".strip().strip(", ")
            else:
                name_el = box.select_one(".event_location_name")
                name = name_el.get_text(" ", strip=True) if name_el else ""
                full_loc = box.select_one(".evoet_location")
                location_text = (full_loc.get_text(" ", strip=True) if full_loc else "") or name or "Gijón"

            # hora amigable
            hora = (dt.astimezone(TZI) if (TZI and dt.tzinfo) else dt).strftime("%H:%M") if start_unix else \
                   (box.select_one(".evo_start .time").get_text(strip=True) if box.select_one(".evo_start .time") else "")

            # clave única fuerte
            if eid and start_unix:
                key = ("eid_unix", eid, int(start_unix))
            else:
                key = ("fallback", link, expected_date.isoformat(), title_norm)

            if key in seen_keys:
                continue
            seen_keys.add(key)

            try:
                disciplina = inferir_disciplina(title)
            except Exception:
                disciplina = ""

            events_day.append({
                "fuente": "AgendaGijon",
                "evento": title,
                "fecha": dt,
                "hora": hora,
                "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location_text)}", "{location_text}")',
                "link": link,
                "disciplina": disciplina
            })

        if debug_label:
            print(f"✅ {debug_label}: {len(events_day)} eventos leídos del DOM")
        return events_day

    # --- Fallback REST in-page (mismo origen) si el click no cambia de día ---
    def _fetch_day_via_rest_inpage(driver, target_date):
        su, eu = _onedayplus_bounds(datetime(target_date.year, target_date.month, target_date.day))
        # Ejecutamos fetch desde el propio navegador para evitar bloqueos
        js = r"""
            const done = arguments[0];
            try{
              const scEl = document.querySelector('.evo_cal_data');
              const scTpl = scEl ? JSON.parse(scEl.getAttribute('data-sc')||'{}') : {};
              scTpl.calendar_type = 'daily';
              scTpl.fixed_day   = String(%(d)d);
              scTpl.fixed_month = String(%(m)d);
              scTpl.fixed_year  = String(%(y)d);
              scTpl.focus_start_date_range = String(%(su)d);
              scTpl.focus_end_date_range   = String(%(eu)d);

              const egp = window.evo_general_params || {};
              const url = (egp.rest_url || '').replace('%%endpoint%%','dv_newday');
              const n   = egp.n || '';

              const body = new URLSearchParams();
              body.set('direction','none');
              body.set('nonce', n);        // nonce que usa EventON en endpoint
              for (const [k,v] of Object.entries(scTpl)) {
                body.set(`shortcode[${k}]`, v);
              }

              fetch(url, {
                method:'POST',
                headers:{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'},
                body: body.toString()
              })
              .then(async r=>{
                 const txt = await r.text();
                 try { return JSON.parse(txt); } catch(e){ return {status:'ERR', raw: txt};}
              })
              .then(data=> done(data))
              .catch(e=> done({status:'ERR', error:String(e)}));
            }catch(e){
              done({status:'ERR', error:String(e)});
            }
        """ % {
            "d": target_date.day, "m": target_date.month, "y": target_date.year,
            "su": su, "eu": eu,
        }

        data = driver.execute_async_script(js)
        if not isinstance(data, dict) or data.get("status") not in ("GOOD", "OK"):
            print(f"⚠️ {target_date} respuesta inesperada REST: {str(data)[:120]}")
            return []

        items = data.get("json", []) or []
        day_html = data.get("html", "") or ""
        # mapeo id->url & id->localización desde el HTML
        urls, locs = {}, {}
        soup = BeautifulSoup(day_html or "", "html.parser")
        for box in soup.select("div.eventon_list_event"):
            eid = box.get("data-event_id")
            if not eid:
                bid = box.get("id", "")
                m = re.search(r"event_(\d+)_", bid)
                eid = m.group(1) if m else None
            if not eid:
                continue
            # url
            found = None
            for s in box.select('script[type="application/ld+json"]'):
                try:
                    j = json.loads(s.string or "{}")
                    if isinstance(j, dict) and j.get("url"):
                        found = j["url"]; break
                except Exception:
                    pass
            if not found:
                a = box.select_one("a[href]")
                if a:
                    found = a.get("href")
            if found:
                urls[str(eid)] = found
            # localización
            attrs = box.select_one(".event_location_attrs")
            if attrs:
                name = attrs.get("data-location_name") or ""
                addr = attrs.get("data-location_address") or ""
                loc_txt = f"{name}, {addr}".strip().strip(", ")
            else:
                name_el = box.select_one(".event_location_name")
                name = name_el.get_text(" ", strip=True) if name_el else ""
                full_loc = box.select_one(".evoet_location")
                loc_txt = (full_loc.get_text(" ", strip=True) if full_loc else "") or name or "Gijón"
            locs[str(eid)] = loc_txt or "Gijón"

        events_day = []
        for it in items:
            try:
                eid = str(it.get("event_id") or it.get("ID") or "").strip()
                title = it.get("event_title") or "Sin título"
                start_unix = it.get("event_start_unix") or it.get("unix_start")
                dt = _parse_dt_from_unix(start_unix)
                if not dt:
                    continue
                # filtramos por el día exacto pedido (por si el rango onedayplus trae colas)
                if dt.date() != target_date:
                    continue
                hora = dt.strftime("%H:%M")
                pmv = it.get("event_pmv", {}) or {}
                exlink = pmv.get("evcal_exlink")
                if isinstance(exlink, list) and exlink:
                    exlink = exlink[0]
                link = (exlink or "").strip() or urls.get(eid) or BASE + "/"
                location_text = locs.get(eid) or "Gijón"

                # clave fuerte
                key = ("eid_unix", eid, int(start_unix))
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                try:
                    disciplina = inferir_disciplina(title)
                except Exception:
                    disciplina = ""

                events_day.append({
                    "fuente": "AgendaGijon",
                    "evento": title,
                    "fecha": dt,
                    "hora": hora,
                    "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(location_text)}", "{location_text}")',
                    "link": link,
                    "disciplina": disciplina
                })
            except Exception as e:
                print(f"⚠️ Error parseando item REST: {e}")

        print(f"✅ {target_date}: {len(events_day)} eventos vía REST")
        return events_day

    # --- flujo principal ---
    events = []
    driver = get_selenium_driver(headless=True)
    try:
        driver.get(BASE)
        # aceptar cookies si salen
        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "cn-accept-cookie"))).click()
            time.sleep(0.2)
        except Exception:
            pass

        _wait_events_loaded(driver, timeout=12)

        fd, fm, fy, _ = _get_fixed_from_dom(driver)
        if not (fd and fm and fy):
            today = (datetime.now(TZI).date() if TZI else datetime.now().date())
        else:
            today = datetime(fy, fm, fd).date()

        for i in range(int(days_ahead)):
            target = today + timedelta(days=i)

            # 1) intento: navegar con click + validar día y leer del DOM
            ok = True if i == 0 else _goto_next_day_and_wait(driver, target)
            _wait_events_loaded(driver, timeout=10)

            if ok:
                day_events = _collect_from_dom(driver, expected_date=target, debug_label=str(target))
                if day_events:
                    events.extend(day_events)
                    continue  # día resuelto desde DOM

            # 2) fallback: pedir el JSON desde la propia página (mismo origen)
            events.extend(_fetch_day_via_rest_inpage(driver, target))

    except Exception as e:
        print(f"❌ Error en Agenda Gijón: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    # dedupe final por (fuente, link, fecha ISO) como red de seguridad
    uniq, seen2 = [], set()
    for ev in events:
        k = (ev["fuente"], ev["link"], ev["fecha"].isoformat())
        if k in seen2:
            continue
        seen2.add(k)
        uniq.append(ev)

    print(f"🎉 Total eventos Agenda Gijón: {len(uniq)}")
    return uniq





    

