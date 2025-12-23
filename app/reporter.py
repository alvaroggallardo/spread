"""
Módulo para generar y almacenar informes de scraping.
"""

from datetime import datetime
from typing import Dict, List, Optional
import traceback


class ScrapingReport:
    """Clase para acumular estadísticas durante el scraping."""
    
    def __init__(self):
        self.inicio = datetime.now()
        self.fin = None
        self.detalles = {}  # {fuente: {nuevos, duplicados, error}}
        self.errores_globales = []
        
    def registrar_fuente(self, fuente: str, nuevos: int = 0, duplicados: int = 0, error: Optional[str] = None):
        """Registra estadísticas de una fuente específica."""
        self.detalles[fuente] = {
            "nuevos": nuevos,
            "duplicados": duplicados,
            "error": error
        }
        
    def registrar_error_global(self, error: str):
        """Registra un error global del proceso."""
        self.errores_globales.append(error)
        
    def finalizar(self):
        """Marca el fin del scraping."""
        self.fin = datetime.now()
        
    def get_duracion_segundos(self) -> int:
        """Retorna la duración en segundos."""
        if self.fin:
            return int((self.fin - self.inicio).total_seconds())
        return 0
        
    def get_total_eventos(self) -> int:
        """Retorna el total de eventos procesados."""
        return sum(d["nuevos"] + d["duplicados"] for d in self.detalles.values())
        
    def get_eventos_nuevos(self) -> int:
        """Retorna el total de eventos nuevos insertados."""
        return sum(d["nuevos"] for d in self.detalles.values())
        
    def get_eventos_duplicados(self) -> int:
        """Retorna el total de eventos duplicados descartados."""
        return sum(d["duplicados"] for d in self.detalles.values())
        
    def get_scrapers_exitosos(self) -> int:
        """Retorna el número de scrapers que funcionaron."""
        return sum(1 for d in self.detalles.values() if d["error"] is None)
        
    def get_scrapers_fallidos(self) -> int:
        """Retorna el número de scrapers que fallaron."""
        return sum(1 for d in self.detalles.values() if d["error"] is not None)
        
    def get_estado(self) -> str:
        """Determina el estado general del scraping."""
        if self.get_scrapers_fallidos() == 0:
            return "exitoso"
        elif self.get_scrapers_exitosos() > 0:
            return "parcial"
        else:
            return "fallido"
            
    def get_errores_texto(self) -> Optional[str]:
        """Retorna todos los errores concatenados."""
        errores = []
        
        # Errores por fuente
        for fuente, datos in self.detalles.items():
            if datos["error"]:
                errores.append(f"[{fuente}] {datos['error']}")
                
        # Errores globales
        errores.extend(self.errores_globales)
        
        return "\n\n".join(errores) if errores else None
        
    def to_dict(self) -> dict:
        """Convierte el reporte a diccionario para guardar en BD."""
        return {
            "fecha_ejecucion": self.inicio,
            "duracion_segundos": self.get_duracion_segundos(),
            "total_eventos": self.get_total_eventos(),
            "eventos_nuevos": self.get_eventos_nuevos(),
            "eventos_duplicados": self.get_eventos_duplicados(),
            "scrapers_exitosos": self.get_scrapers_exitosos(),
            "scrapers_fallidos": self.get_scrapers_fallidos(),
            "detalles": self.detalles,
            "errores": self.get_errores_texto(),
            "estado": self.get_estado()
        }
        
    def imprimir_resumen(self):
        """Imprime un resumen del scraping en consola."""
        print("\n" + "="*60)
        print("📊 RESUMEN DEL SCRAPING")
        print("="*60)
        print(f"⏱️  Duración: {self.get_duracion_segundos()}s")
        print(f"✅ Eventos nuevos: {self.get_eventos_nuevos()}")
        print(f"🔁 Eventos duplicados: {self.get_eventos_duplicados()}")
        print(f"✅ Scrapers exitosos: {self.get_scrapers_exitosos()}")
        print(f"❌ Scrapers fallidos: {self.get_scrapers_fallidos()}")
        print(f"📈 Estado: {self.get_estado().upper()}")
        print("\n📋 DETALLE POR FUENTE:")
        print("-"*60)
        
        for fuente, datos in sorted(self.detalles.items()):
            if datos["error"]:
                print(f"❌ {fuente}: ERROR - {datos['error'][:80]}...")
            else:
                print(f"✅ {fuente}: {datos['nuevos']} nuevos, {datos['duplicados']} duplicados")
                
        if self.errores_globales:
            print("\n⚠️  ERRORES GLOBALES:")
            print("-"*60)
            for error in self.errores_globales:
                print(f"  • {error}")
                
        print("="*60 + "\n")


def guardar_informe(report: ScrapingReport):
    """
    Guarda el informe en la base de datos.
    
    Args:
        report: Instancia de ScrapingReport con las estadísticas
    """
    from app.models import InformeScrap, SessionLocal
    
    db = SessionLocal()
    try:
        informe = InformeScrap(**report.to_dict())
        db.add(informe)
        db.commit()
        print(f"✅ Informe guardado en BD con ID: {informe.id}")
        return informe.id
    except Exception as e:
        print(f"❌ Error guardando informe: {e}")
        db.rollback()
        traceback.print_exc()
        return None
    finally:
        db.close()
