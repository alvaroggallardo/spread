"""
Módulo base con utilidades comunes para todos los scrapers.
"""

import re
import json
import time
from datetime import datetime, timedelta

import requests
import dateparser
from bs4 import BeautifulSoup, Comment

# Imports opcionales que solo algunos scrapers usan
try:
    from ics import Calendar
except ImportError:
    Calendar = None

try:
    from dateutil import parser as du_parser
except ImportError:
    du_parser = None

from urllib.parse import urljoin, quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="cultural_events_locator")
except ImportError:
    Nominatim = None
    geolocator = None



# --------------------------
# Geocoding
# --------------------------
def geocode_coordinates(lat, lon):
    """
    Convierte coordenadas lat/lon en nombre de ciudad usando geocoding inverso.
    
    Args:
        lat: Latitud
        lon: Longitud
        
    Returns:
        str: Nombre de la ciudad o 'Desconocido' si falla
    """
    if geolocator is None:
        print("⚠️ geopy no disponible")
        return 'Desconocido'
        
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True)
        return location.raw['address'].get('city', 'Desconocido')
    except Exception as e:
        print(f"Error geocoding: {e}")
        return 'Desconocido'


# --------------------------
# Configuración de Selenium
# --------------------------
def get_selenium_driver(headless=True):
    """
    Crea y configura un driver de Selenium para Chrome.
    
    Args:
        headless: Si True, ejecuta Chrome en modo headless (sin interfaz gráfica)
        
    Returns:
        webdriver.Chrome: Driver configurado
    """
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    return webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)


# --------------------------
# Clasificación de Eventos
# --------------------------
def inferir_disciplina(titulo):
    """
    Infiere la disciplina/categoría de un evento basándose en su título.
    
    Args:
        titulo: Título del evento
        
    Returns:
        str: Categoría inferida del evento
    """
    titulo = titulo.lower()

    if any(p in titulo for p in ["cine", "film", "película", "documental", "corto", "largometraje"]):
        return "Cine"
    elif any(p in titulo for p in ["teatro", "representación", "obra", "actor", "actriz", "escénica", "escénico"]):
        return "Artes Escénicas"
    elif any(p in titulo for p in ["jazz", "música", "concierto", "recital", "banda", "coro", "cantante", "orquesta", "piano", "metal", "rock", "hip hop", "rap", "trap", "funk", "reguetón", "reggaeton"]):
        return "Música"
    elif any(p in titulo for p in ["exposición", "fotografía", "fotográfica", "escultura", "pintura", "arte", "visual", "galería", "retratos", "acuarela", "óleo", "speculum"]):
        return "Artes Visuales"
    elif any(p in titulo for p in ["cuentos", "narración", "cuentacuentos", "oral"]):
        return "Narración Oral"
    elif any(p in titulo for p in ["charla", "conferencia", "coloquio", "debate", "tertulia", "mesa redonda"]):
        return "Conferencias"
    elif any(p in titulo for p in ["libro", "literatura", "autor", "poesía", "novela", "lectura", "ensayo"]):
        return "Literatura"
    elif any(p in titulo for p in ["danza", "ballet", "baile", "folklore", "folclore", "coreografía"]):
        return "Danza"
    elif any(p in titulo for p in ["taller", "formación", "curso", "clase", "aprende", "iniciación", "workshop"]):
        return "Formación / Taller"
    elif any(p in titulo for p in ["tradicional", "astur", "costumbre"]):
        return "Cultura Tradicional"
    elif any(p in titulo for p in ["visita guiada", "visitas guiadas", "ruta", "rutas", "patrimonio", "historia", 
                                   "arqueología", "recorrido", "descubre", "bus turístico", "georuta", 
                                   "ruta turística", "rutas turísticas"]):
        return "Itinerarios Patrimoniales"
    elif any(p in titulo for p in ["infantil", "niños", "niñas", "peques", "familia", "familiares", 
                                   "campamento", "campamentos", "vacaciones activas", "campamentos urbanos"]):
        return "Público Infantil / Familiar"
    elif any(p in titulo for p in ["deporte", "actividad física", "cicloturista", "carrera", "juegas"]):
        return "Deportes / Actividad Física"
    elif any(p in titulo for p in ["medioambiente", "sostenibilidad", "reciclaje", "clima", "ecología", "verde"]):
        return "Medio Ambiente"
    elif any(p in titulo for p in ["salud", "bienestar", "cuidados", "prevención", "psicología", "enfermedad"]):
        return "Salud y Bienestar"
    elif any(p in titulo for p in ["tecnología", "innovación", "inteligencia artificial", "digital", "robot", "software", "automatizados"]):
        return "Tecnología / Innovación"
    elif any(p in titulo for p in ["gastronomía", "degustación", "vino", "cocina", "culinario", "gastro",
                                   "jornadas", "tostas", "tapas", "sidra", "cerveza", "fresa", "bonito"]):
        return "Gastronomía"
    elif any(p in titulo for p in ["igualdad", "género", "inclusión", "diversidad", "social", "solidaridad"]):
        return "Sociedad / Inclusión"
    elif any(p in titulo for p in ["fiestas", "fiesta", "romería", "verbena"]):
        return "Fiestas"
    elif any(p in titulo for p in ["puertas abiertas", "jornada abierta", "encuentro"]):
        return "Divulgación / Institucional"
    elif any(p in titulo for p in ["varios", "mixto", "combinado", "múltiple", "multidisciplinar", "radar"]):
        return "Multidisciplinar"
    elif any(p in titulo for p in ["laboral", "actividad especial"]):
        return "Actividades especiales"
    elif any(p in titulo for p in ["fiesta", "festival", "fest", "evento", "celebración", "espectáculo"]):
        return "Eventos"
    else:
        return "Otros"
