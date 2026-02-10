"""
Scraper para eventos - Comarca Avilés.
Procesa archivos ICS locales de avilescomarca.info
"""

from app.scrapers.base import *

def get_events_aviles(months_ahead=2, only_future=True):
    """
    Descarga el archivo ICS directamente desde la web de Comarca Avilés
    y lo procesa.
    
    Args:
        months_ahead: Número de meses a futuro desde hoy (default: 2 meses)
        only_future: Si True, filtra solo eventos futuros
    
    Returns:
        Lista de eventos con la estructura estándar
    """
    url = "https://avilescomarca.info/?ical=1"
    events = []
    
    print(f"🌐 Descargando eventos desde {url}...")
    print(f"📅 Buscando eventos hasta {months_ahead} mes(es) adelante...")
    
    try:
        # Crear sesión con headers apropiados
        session = requests.Session()
        UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        session.headers.update({
            "User-Agent": UA,
            "Accept": "text/calendar,text/plain,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9",
            "Referer": "https://avilescomarca.info/",
        })
        
        # Descargar el archivo ICS
        resp = session.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        
        # Obtener el contenido
        ics_content = resp.text if resp.text else resp.content.decode("utf-8", errors="ignore")
        
        # Guardar temporalmente para debugging (opcional)
        temp_path = "/tmp/comarca_aviles_temp.ics"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(ics_content)
        
        # Procesar usando la función auxiliar
        events = _process_ics_file(temp_path, months_ahead=months_ahead, only_future=only_future)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error descargando el archivo ICS: {e}")
    except Exception as e:
        print(f"❌ Error procesando eventos online: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def _process_ics_file(ics_path, months_ahead=2, only_future=True):
    """
    Carga eventos desde un archivo ICS local de Comarca Avilés.
    
    Args:
        ics_path: Ruta al archivo .ics descargado
        months_ahead: Número de meses a futuro desde hoy (default: 2 meses)
        only_future: Si True, filtra solo eventos futuros
    
    Returns:
        Lista de eventos con la estructura estándar
    """
    events = []
    seen = set()
    hoy = datetime.now().date()
    
    # Calcular fecha límite (hoy + N meses)
    try:
        from dateutil.relativedelta import relativedelta
        fecha_limite = hoy + relativedelta(months=months_ahead)
    except ImportError:
        # Fallback si no está disponible dateutil
        import calendar
        year = hoy.year
        month = hoy.month + months_ahead
        if month > 12:
            year += month // 12
            month = month % 12 or 12
        day = min(hoy.day, calendar.monthrange(year, month)[1])
        fecha_limite = datetime(year, month, day).date()
    
    print(f"📂 Cargando eventos desde {ics_path}...")
    
    try:
        # Leer el archivo ICS
        with open(ics_path, "r", encoding="utf-8") as f:
            ics_content = f.read()
        
        # Parsear el calendario
        cal = Calendar(ics_content)
        
        print(f"📊 Total eventos en el ICS: {len(cal.events)}")
        print(f"📅 Rango de fechas: desde {hoy} hasta {fecha_limite}")
        
        # Procesar cada evento
        for ev in cal.events:
            # Extraer información básica
            title = ev.name or "Sin título"
            link = getattr(ev, "url", None) or "https://avilescomarca.info"
            uid = getattr(ev, "uid", None)
            
            # Usar UID como clave única para evitar duplicados
            if uid in seen:
                continue
            seen.add(uid)
            
            # Ubicación
            lugar = ev.location or "Avilés, Asturias"
            
            # Fecha y hora
            start_dt = getattr(ev, "begin", None)
            end_dt = getattr(ev, "end", None)
            
            if start_dt:
                fecha_evento = start_dt.datetime
                # Verificar si es evento de todo el día
                is_all_day = getattr(ev, "all_day", False)
                hora_text = "" if is_all_day else fecha_evento.strftime("%H:%M")
                
                # Fecha de fin (para el modelo de BD)
                fecha_fin_evento = end_dt.datetime if end_dt else None
            else:
                fecha_evento = None
                fecha_fin_evento = None
                hora_text = ""
            
            # Para filtrar correctamente eventos multi-día, usar la fecha de fin si existe
            if only_future and fecha_evento:
                # Si hay fecha de fin, usar esa para determinar si el evento ya pasó
                if fecha_fin_evento:
                    # Usar la fecha de fin para filtrar (eventos que ya terminaron)
                    if fecha_fin_evento.date() < hoy:
                        continue
                else:
                    # Si no hay fecha de fin, usar la fecha de inicio
                    if fecha_evento.date() < hoy:
                        continue
            
            # Filtrar eventos que empiezan más allá del rango especificado
            if fecha_evento and fecha_evento.date() > fecha_limite:
                continue
            
            # Categorías (pueden ser múltiples separadas por coma)
            categorias_raw = getattr(ev, "categories", None)
            if categorias_raw:
                # Puede venir como lista o como string
                if isinstance(categorias_raw, list):
                    categorias = ", ".join(categorias_raw)
                else:
                    categorias = str(categorias_raw)
            else:
                categorias = ""
            
            # Inferir disciplina desde las categorías o el título
            if categorias:
                disciplina = categorias.split(",")[0].strip()  # Tomar la primera categoría
            else:
                disciplina = inferir_disciplina(title)
            
            # Crear el evento con la estructura del modelo de BD
            events.append({
                "fuente": "Comarca Avilés",
                "evento": title,
                "fecha": fecha_evento,
                "fecha_fin": fecha_fin_evento,  # Campo del modelo
                "hora": hora_text,
                "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
                "link": link,
                "disciplina": disciplina
            })
        
        print(f"✅ Procesados {len(events)} eventos de Comarca Avilés")
        
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {ics_path}")
    except Exception as e:
        print(f"❌ Error procesando el archivo ICS: {e}")
        import traceback
        traceback.print_exc()
    
    return events

# Función auxiliar para procesar archivo ICS local (útil para testing)
def get_events_aviles_from_file(ics_path, months_ahead=2, only_future=True):
    """
    Carga eventos desde un archivo ICS local de Comarca Avilés.
    Útil para testing o procesamiento offline.
    
    Args:
        ics_path: Ruta al archivo .ics descargado
        months_ahead: Número de meses a futuro desde hoy (default: 2 meses)
        only_future: Si True, filtra solo eventos futuros
    
    Returns:
        Lista de eventos con la estructura estándar
    """
    return _process_ics_file(ics_path, months_ahead, only_future)


# Ejemplo de uso
if __name__ == "__main__":
    # Opción 1: Descarga directa desde web (PRODUCCIÓN)
    eventos = get_events_aviles()
    
    print(f"\n📊 Resumen: {len(eventos)} eventos encontrados (2 meses)")
    
    # Mostrar los primeros 3 eventos como ejemplo
    for i, evento in enumerate(eventos[:3], 1):
        print(f"\n--- Evento {i} ---")
        print(f"Título: {evento['evento']}")
        print(f"Fecha: {evento['fecha']}")
        print(f"Hora: {evento['hora']}")
        print(f"Disciplina: {evento['disciplina']}")
    
    print("\n" + "="*50)
    
    # Opción 2: Desde archivo local (TESTING)
    # eventos_local = get_events_aviles_from_file("comarca-aviles.ics")
    # print(f"\n📊 Eventos locales: {len(eventos_local)} eventos")