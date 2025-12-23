"""
Sistema modular de scraping de eventos culturales de Asturias.

Este paquete contiene scrapers individuales para diferentes fuentes de eventos
y utilidades comunes para procesamiento de datos.
"""

from app.scrapers.base import (
    geocode_coordinates,
    get_selenium_driver,
    inferir_disciplina
)

from app.scrapers.orchestrator import scrape_all_sources

__all__ = [
    'geocode_coordinates',
    'get_selenium_driver',
    'inferir_disciplina',
    'scrape_all_sources'
]

__version__ = '2.0.0'
