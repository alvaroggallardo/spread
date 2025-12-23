"""
Orquestador principal que ejecuta todos los scrapers de eventos.
"""

def scrape_all_sources():
    """
    Ejecuta todos los scrapers disponibles y retorna lista unificada de eventos.
    
    Returns:
        list: Lista consolidada de todos los eventos de todas las fuentes
    """
    all_events = []
    
    # Definir todos los scrapers con sus configuraciones
    scrapers_config = [
        ("Oviedo", "oviedo", "get_events_oviedo", {}),
        ("Gijón", "gijon", "get_events_gijon", {}),
        ("Mieres", "mieres", "get_events_mieres", {}),
        ("Asturies Cultura", "asturies_cultura", "get_events_asturiescultura", {}),
        ("Avilés", "aviles", "get_events_aviles", {}),
        ("Siero", "siero", "get_events_siero", {}),
        ("Conciertos.club", "conciertos_club", "get_events_conciertosclub", {}),
        ("Turismo Asturias", "turismo_asturias", "get_events_turismoasturias", {
            "tematicas": ["gastronomia", "museos", "fiestas", "cine-y-espectaculos", 
                         "deporte", "ocio-infantil", "rutas-y-visitas-guiadas", "ferias-mercados"]
        }),
        ("LABoral", "laboral", "get_events_laboral", {}),
        ("Fiestas Asturias API", "fiestas_asturias_api", "get_events_fiestasasturias_api", {}),
        ("Fiestas Asturias Simcal", "fiestas_asturias_simcal", "get_events_fiestasasturias_simcal", {}),
        ("Cámara Gijón", "camara_gijon", "get_events_camaragijon_recinto", {}),
        ("Laboral Centro Arte", "laboral_centro_arte", "get_events_laboral_actividades", {}),
        ("Asturias Convivencias", "asturias_convivencias", "get_events_asturiasconvivencias", {}),
        ("Umami Gijón", "umami_gijon", "get_events_gijon_umami", {}),
        ("SpainSwing", "spainswing", "get_events_asturias", {}),
        ("Jarascada", "jarascada", "get_events_jarascada", {}),
        ("Agenda Gijón", "agenda_gijon", "get_events_agenda_gijon", {}),
    ]
    
    # Ejecutar cada scraper
    for name, module_name, func_name, kwargs in scrapers_config:
        try:
            print(f"\n🔄 Ejecutando scraper: {name}")
            
            # Import dinámico del módulo
            module = __import__(f"app.scrapers.{module_name}", fromlist=[func_name])
            scraper_func = getattr(module, func_name)
            
            # Ejecutar scraper con sus parámetros
            events = scraper_func(**kwargs)
            all_events.extend(events)
            print(f"✅ {name}: {len(events)} eventos")
            
        except Exception as e:
            print(f"❌ Error en {name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"\n🎉 Total eventos recopilados: {len(all_events)}")
    return all_events
