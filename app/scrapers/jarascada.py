"""
Scraper para eventos - Comarca Avilés.
Procesa archivos ICS locales de avilescomarca.info
"""

from app.scrapers.base import *

def get_events_comarca_aviles(ics_path, only_future=True):
    """
    Carga eventos desde un archivo ICS local de Comarca Avilés.
    
    Args:
        ics_path: Ruta al archivo .ics descargado
        only_future: Si True, filtra solo eventos futuros
    
    Returns:
        Lista de eventos con la estructura estándar
    """
    events = []
    seen = set()
    hoy = datetime.now().date()
    
    print(f"📂 Cargando eventos desde {ics_path}...")
    
    try:
        # Leer el archivo ICS
        with open(ics_path, "r", encoding="utf-8") as f:
            ics_content = f.read()
        
        # Parsear el calendario
        cal = Calendar(ics_content)
        
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
            if start_dt:
                fecha_evento = start_dt.datetime
                # Verificar si es evento de todo el día
                is_all_day = getattr(ev, "all_day", False)
                hora_text = "" if is_all_day else fecha_evento.strftime("%H:%M")
            else:
                fecha_evento = None
                hora_text = ""
            
            # Filtrar eventos pasados si only_future=True
            if only_future and fecha_evento and fecha_evento.date() < hoy:
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
            
            # Descripción (limitada para no hacer el evento muy largo)
            descripcion = getattr(ev, "description", "")
            if descripcion and len(descripcion) > 200:
                descripcion = descripcion[:200] + "..."
            
            # Crear el evento con la estructura estándar
            events.append({
                "fuente": "Comarca Avilés",
                "evento": title,
                "fecha": fecha_evento,
                "hora": hora_text,
                "lugar": f'=HYPERLINK("https://www.google.com/maps/search/?api=1&query={quote_plus(lugar)}", "{lugar}")',
                "link": link,
                "disciplina": disciplina,
                "categorias": categorias,
                "descripcion": descripcion
            })
        
        print(f"✅ Procesados {len(events)} eventos de Comarca Avilés")
        
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {ics_path}")
    except Exception as e:
        print(f"❌ Error procesando el archivo ICS: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def get_events_comarca_aviles_online(only_future=True):
    """
    Descarga el archivo ICS directamente desde la web de Comarca Avilés
    y lo procesa.
    
    Args:
        only_future: Si True, filtra solo eventos futuros
    
    Returns:
        Lista de eventos con la estructura estándar
    """
    url = "https://avilescomarca.info/?ical=1"
    events = []
    
    print(f"🌐 Descargando eventos desde {url}...")
    
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
        
        # Procesar usando la función de archivo local
        events = get_events_comarca_aviles(temp_path, only_future=only_future)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error descargando el archivo ICS: {e}")
    except Exception as e:
        print(f"❌ Error procesando eventos online: {e}")
        import traceback
        traceback.print_exc()
    
    return events


# Ejemplo de uso
if __name__ == "__main__":
    # Opción 1: Desde archivo local
    eventos_local = get_events_comarca_aviles(
        ics_path="comarca-aviles-85f0f855bee.ics",
        only_future=True
    )
    
    print(f"\n📊 Resumen: {len(eventos_local)} eventos encontrados")
    
    # Mostrar los primeros 3 eventos como ejemplo
    for i, evento in enumerate(eventos_local[:3], 1):
        print(f"\n--- Evento {i} ---")
        print(f"Título: {evento['evento']}")
        print(f"Fecha: {evento['fecha']}")
        print(f"Hora: {evento['hora']}")
        print(f"Disciplina: {evento['disciplina']}")
        print(f"Lugar: {evento['lugar']}")
    
    # Opción 2: Descarga directa desde web (descomentar para usar)
    # eventos_online = get_events_comarca_aviles_online(only_future=True)