from typing import Dict, Any
from collections import Counter
from .reclamos import EstadoReclamo

class Analitica:
    def __init__(self, gestor_servicio):
        self._gestor = gestor_servicio

    def get_estadisticas_generales(self, depto_id: str) -> Dict[str, Any]:
        reclamos = self._gestor.get_reclamos_por_departamento(depto_id)
        total = len(reclamos)
        if total == 0:
            return {"total_reclamos": 0, "resueltos": 0, "pendientes": 0, "resueltos_porcentaje": 0}
        
        resueltos = len([r for r in reclamos if r.estado == EstadoReclamo.RESUELTO])
        return {
            "total_reclamos": total,
            "resueltos": resueltos,
            "pendientes": total - resueltos,
            "resueltos_porcentaje": (resueltos / total) * 100
        }

    def get_frecuencia_palabras(self, depto_id: str) -> Dict[str, int]:
        reclamos = self._gestor.get_reclamos_por_departamento(depto_id)
        todo_el_texto = " ".join([r.contenido for r in reclamos])
        palabras = [p for p in todo_el_texto.lower().split() if len(p) > 3]
        return dict(Counter(palabras))
    
    def obtener_datos_dashboard(self, depto_id: str):
        """RF 54: Retorna estadísticas unificadas para la UI y Tests."""
        stats = self.get_estadisticas_generales(depto_id)
        frecuencia = self.get_frecuencia_palabras(depto_id)
        return {
            "total": stats["total_reclamos"],
            "pendientes": stats["pendientes"],
            "resueltos": stats["resueltos_porcentaje"],
            "stats": stats, # Agregamos esta clave que el test está buscando
            "frecuencia": frecuencia
        }

    def generar_reporte_html(self, depto_id: str, stats: dict = None, frecuencia: dict = None) -> str:
        """RF 59: Genera el string HTML. 
        Hacemos que stats y frecuencia sean opcionales para que el test no rompa."""
        if stats is None or frecuencia is None:
            datos = self.obtener_datos_dashboard(depto_id)
            stats = datos["stats"]
            frecuencia = datos["frecuencia"]
            
        return f"<html><body><h1>Reporte de Reclamos</h1><p>Depto: {depto_id}</p><p>Total: {stats['total_reclamos']}</p></body></html>"