from app.models import Evento, SessionLocal, init_db
from app.model_supabase import EventoSupabase, SessionSupabase
from datetime import datetime, date
from sqlalchemy import and_


def parse_date_safe(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%d/%m/%Y")
        except Exception:
            return None
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return None


def evento_ya_existe(db, ev):
    return db.query(Evento).filter(
        and_(
            Evento.link == ev.get("link"),
            Evento.evento == ev.get("evento"),
            Evento.fecha == parse_date_safe(ev.get("fecha")),
            Evento.lugar == ev.get("lugar")
        )
    ).first() is not None


def guardar_eventos(scrapers=None):
    # Crear reporte para estadísticas
    from app.reporter import ScrapingReport, guardar_informe
    report = ScrapingReport()
    
    try:
        # Inicializa Railway
        init_db()

        db = SessionLocal()            # Base Railway
        db_sb = SessionSupabase()      # Base Supabase

        # ✅ NUEVO: Usar sistema modular de scrapers
        if scrapers is None:
            try:
                # Intentar usar el nuevo sistema modular
                from app.scrapers import scrape_all_sources
                print("✅ Usando nuevo sistema modular de scrapers")
                eventos_list = scrape_all_sources(report=report)
                
            except ImportError:
                # Fallback al sistema antiguo si el nuevo no está disponible
                print("⚠️ Fallback al sistema antiguo de scrapers")
                from app.script_scraping import (
                    get_events_gijon,
                    get_events_oviedo,
                    get_events_mieres,
                    get_events_asturiescultura,
                    get_events_aviles,
                    get_events_siero,
                    get_events_conciertosclub,
                    get_events_turismoasturias,
                    get_events_laboral,
                    get_events_fiestasasturias_api,
                    get_events_fiestasasturias_simcal,
                    get_events_camaragijon_recinto,
                    get_events_laboral_actividades,
                    get_events_asturiasconvivencias,
                    get_events_gijon_umami,
                    get_events_asturias,
                    get_events_jarascada,
                    get_events_agenda_gijon
                )

                tematicas = [
                    "gastronomia",
                    "museos",
                    "fiestas",
                    "cine-y-espectaculos",
                    "deporte",
                    "ocio-infantil",
                    "rutas-y-visitas-guiadas",
                    "ferias-mercados"
                ]

                scrapers = [
                    get_events_gijon,
                    get_events_oviedo,
                    get_events_mieres,
                    get_events_asturiescultura,
                    get_events_aviles,
                    get_events_siero,
                    get_events_conciertosclub,
                    lambda: get_events_turismoasturias(tematicas=tematicas),
                    get_events_laboral,
                    get_events_fiestasasturias_api,
                    get_events_fiestasasturias_simcal,
                    get_events_camaragijon_recinto,
                    get_events_laboral_actividades,
                    get_events_asturiasconvivencias,
                    get_events_gijon_umami,
                    get_events_asturias,
                    get_events_jarascada,
                    get_events_agenda_gijon
                ]
                
                # Ejecutar scrapers del sistema antiguo
                eventos_list = []
                for scraper in scrapers:
                    eventos_list.extend(scraper())
        else:
            # Si se pasan scrapers personalizados, ejecutarlos
            eventos_list = []
            for scraper in scrapers:
                eventos_list.extend(scraper())



        nuevos = 0
        
        # Diccionario para contar por fuente
        stats_por_fuente = {}

        # Procesar todos los eventos
        for ev in eventos_list:
            fuente = ev.get("fuente", "Desconocido")
            
            # Inicializar stats de la fuente si no existe
            if fuente not in stats_por_fuente:
                stats_por_fuente[fuente] = {"nuevos": 0, "duplicados": 0}
            
            if not evento_ya_existe(db, ev):
                # Insertar en Railway
                nuevo = Evento(
                    fuente=fuente,
                    evento=ev.get("evento"),
                    fecha=parse_date_safe(ev.get("fecha")),
                    fecha_fin=parse_date_safe(ev.get("fecha_fin")) if "fecha_fin" in ev else None,
                    hora=ev.get("hora"),
                    lugar=ev.get("lugar"),
                    link=ev.get("link"),
                    disciplina=ev.get("disciplina", None)
                )
                db.add(nuevo)

                # Insertar en Supabase
                nuevo_sb = EventoSupabase(
                    fuente=fuente,
                    evento=ev.get("evento"),
                    fecha=parse_date_safe(ev.get("fecha")),
                    fecha_fin=parse_date_safe(ev.get("fecha_fin")) if "fecha_fin" in ev else None,
                    hora=ev.get("hora"),
                    lugar=ev.get("lugar"),
                    link=ev.get("link"),
                    disciplina=ev.get("disciplina", None)
                )
                db_sb.add(nuevo_sb)

                nuevos += 1
                stats_por_fuente[fuente]["nuevos"] += 1
            else:
                stats_por_fuente[fuente]["duplicados"] += 1

        db.commit()
        
        # Intentar guardar en Supabase (opcional, no crítico)
        try:
            db_sb.commit()
            print("✅ Eventos guardados también en Supabase")
        except Exception as e:
            print(f"⚠️ No se pudo guardar en Supabase (no crítico): {e}")
            db_sb.rollback()

        db.close()
        db_sb.close()
        
        # Actualizar reporte con estadísticas reales
        for fuente, stats in stats_por_fuente.items():
            # Actualizar solo si la fuente ya existe en el reporte (del orchestrator)
            if fuente in report.detalles:
                report.detalles[fuente]["nuevos"] = stats["nuevos"]
                report.detalles[fuente]["duplicados"] = stats["duplicados"]
            else:
                # Si no existe (sistema antiguo), agregarla
                report.registrar_fuente(fuente, nuevos=stats["nuevos"], duplicados=stats["duplicados"])
        
        # Finalizar reporte
        report.finalizar()
        report.imprimir_resumen()
        
        # Guardar en BD
        guardar_informe(report)
        
        return nuevos
        
    except Exception as e:
        # Registrar error global
        import traceback
        error_detail = f"Error global en guardar_eventos: {str(e)}\n{traceback.format_exc()}"
        report.registrar_error_global(error_detail)
        report.finalizar()
        report.imprimir_resumen()
        guardar_informe(report)
        raise
