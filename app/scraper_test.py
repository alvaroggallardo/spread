"""
Módulo para testing de scrapers en tiempo real sin guardar en base de datos.
Permite ejecutar scrapers individuales y capturar su output.
"""

import sys
import io
import json
import importlib
from contextlib import redirect_stdout
from datetime import datetime
from typing import Generator, Dict, Any


# Mapeo de nombres de scrapers a sus módulos y funciones
SCRAPER_REGISTRY = {
    "oviedo": ("app.scrapers.oviedo", "get_events_oviedo"),
    "gijon": ("app.scrapers.gijon", "get_events_gijon"),
    "mieres": ("app.scrapers.mieres", "get_events_mieres"),
    "aviles": ("app.scrapers.aviles", "get_events_aviles"),
    "siero": ("app.scrapers.siero", "get_events_siero"),
    "laboral": ("app.scrapers.laboral", "get_events_laboral"),
    "asturies_cultura": ("app.scrapers.asturies_cultura", "get_events_asturiescultura"),
    "conciertos_club": ("app.scrapers.conciertos_club", "get_events_conciertosclub"),
    "camara_gijon": ("app.scrapers.camara_gijon", "get_events_camaragijon_recinto"),
    "laboral_centro_arte": ("app.scrapers.laboral_centro_arte", "get_events_laboral_actividades"),
    "asturias_convivencias": ("app.scrapers.asturias_convivencias", "get_events_asturiasconvivencias"),
    "umami_gijon": ("app.scrapers.umami_gijon", "get_events_gijon_umami"),
    "jarascada": ("app.scrapers.jarascada", "get_events_jarascada"),
    "agenda_gijon": ("app.scrapers.agenda_gijon", "get_events_agenda_gijon"),
    "niemeyer": ("app.scrapers.niemeyer", "get_events_niemeyer"),
}


def get_available_scrapers() -> list:
    """Retorna lista de scrapers disponibles."""
    return list(SCRAPER_REGISTRY.keys())


class OutputCapture:
    """Captura output de print statements y lo convierte en eventos."""
    
    def __init__(self):
        self.buffer = io.StringIO()
        self.events = []
    
    def write(self, text):
        """Escribe texto y lo procesa como evento."""
        if text.strip():
            self.events.append({
                "timestamp": datetime.now().isoformat(),
                "message": text.strip()
            })
        self.buffer.write(text)
    
    def flush(self):
        """Flush del buffer."""
        self.buffer.flush()
    
    def get_events(self):
        """Retorna eventos capturados."""
        return self.events


def stream_scraper_output(scraper_name: str) -> Generator[str, None, None]:
    """
    Ejecuta un scraper y genera eventos SSE con el output en tiempo real.
    
    Args:
        scraper_name: Nombre del scraper a ejecutar
        
    Yields:
        str: Eventos SSE formateados
    """
    # Verificar que el scraper existe
    if scraper_name not in SCRAPER_REGISTRY:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Scraper {scraper_name} no encontrado'})}\n\n"
        return
    
    module_name, function_name = SCRAPER_REGISTRY[scraper_name]
    
    # Enviar evento de inicio
    yield f"data: {json.dumps({'type': 'start', 'scraper': scraper_name, 'timestamp': datetime.now().isoformat()})}\n\n"
    
    try:
        # Importar el módulo y función del scraper
        module = importlib.import_module(module_name)
        scraper_function = getattr(module, function_name)
        
        # Capturar stdout
        output_capture = OutputCapture()
        
        # Ejecutar scraper con captura de output
        with redirect_stdout(output_capture):
            start_time = datetime.now()
            events = scraper_function()
            end_time = datetime.now()
        
        # Enviar mensajes de log capturados
        for log_event in output_capture.get_events():
            yield f"data: {json.dumps({'type': 'log', **log_event})}\n\n"
        
        # Enviar eventos scrapeados
        yield f"data: {json.dumps({'type': 'summary', 'total_events': len(events), 'duration': str(end_time - start_time)})}\n\n"
        
        # Enviar cada evento individualmente
        for idx, event in enumerate(events, 1):
            # Convertir datetime a string para JSON
            event_data = event.copy()
            if 'fecha' in event_data and hasattr(event_data['fecha'], 'isoformat'):
                event_data['fecha'] = event_data['fecha'].isoformat()
            if 'fecha_fin' in event_data and event_data['fecha_fin'] and hasattr(event_data['fecha_fin'], 'isoformat'):
                event_data['fecha_fin'] = event_data['fecha_fin'].isoformat()
            
            yield f"data: {json.dumps({'type': 'event', 'index': idx, 'data': event_data})}\n\n"
        
        # Evento de finalización exitosa
        yield f"data: {json.dumps({'type': 'complete', 'scraper': scraper_name, 'total': len(events), 'timestamp': datetime.now().isoformat()})}\n\n"
        
    except Exception as e:
        # Enviar error
        import traceback
        error_detail = traceback.format_exc()
        yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'detail': error_detail})}\n\n"


def run_scraper_dry(scraper_name: str) -> Dict[str, Any]:
    """
    Ejecuta un scraper en modo dry-run (sin guardar en BD) y retorna resultados.
    
    Args:
        scraper_name: Nombre del scraper a ejecutar
        
    Returns:
        dict: Resultados del scraping con estadísticas
    """
    if scraper_name not in SCRAPER_REGISTRY:
        return {"error": f"Scraper {scraper_name} no encontrado"}
    
    module_name, function_name = SCRAPER_REGISTRY[scraper_name]
    
    try:
        # Importar y ejecutar
        module = importlib.import_module(module_name)
        scraper_function = getattr(module, function_name)
        
        start_time = datetime.now()
        events = scraper_function()
        end_time = datetime.now()
        
        return {
            "scraper": scraper_name,
            "total_events": len(events),
            "duration": str(end_time - start_time),
            "events": events[:10],  # Solo primeros 10 para preview
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "detail": traceback.format_exc()
        }
