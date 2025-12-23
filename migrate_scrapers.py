"""
Script para migrar automáticamente los scrapers restantes.
Este script extrae cada función get_events_* del archivo original y crea módulos individuales.
"""

import re
import os

# Mapeo de funciones a nombres de archivo
SCRAPERS_MAP = {
    "get_events_aviles": "aviles.py",
    "get_events_siero": "siero.py",
    "get_events_conciertosclub": "conciertos_club.py",
    "get_events_turismoasturias": "turismo_asturias.py",
    "get_events_laboral": "laboral.py",
    "parse_laboral_cards": None,  # Función auxiliar, se incluye en laboral.py
    "get_events_fiestasasturias_api": "fiestas_asturias_api.py",
    "get_events_fiestasasturias_simcal": "fiestas_asturias_simcal.py",
    "get_events_camaragijon_recinto": "camara_gijon.py",
    "get_events_laboral_actividades": "laboral_centro_arte.py",
    "get_events_asturiasconvivencias": "asturias_convivencias.py",
    "get_events_gijon_umami": "umami_gijon.py",
    "get_events_asturias": "spainswing.py",
    "get_events_jarascada": "jarascada.py",
    "get_events_agenda_gijon": "agenda_gijon.py",
}

# Leer archivo original
with open("app/script_scraping.py", "r", encoding="utf-8") as f:
    content = f.read()

# Extraer cada función
for func_name, filename in SCRAPERS_MAP.items():
    if filename is None:
        continue  # Saltar funciones auxiliares
    
    # Buscar la función en el contenido
    pattern = rf"^def {func_name}\([^)]*\):.*?(?=^def |\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    
    if not match:
        print(f"⚠️ No se encontró la función {func_name}")
        continue
    
    func_code = match.group(0)
    
    # Crear el módulo
    module_content = f'''"""
Scraper para eventos - {filename.replace('.py', '').replace('_', ' ').title()}.
"""

from app.scrapers.base import *

{func_code}
'''
    
    # Guardar el archivo
    filepath = f"app/scrapers/{filename}"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(module_content)
    
    print(f"✅ Creado: {filepath}")

print("\n🎉 Migración automática completada!")
