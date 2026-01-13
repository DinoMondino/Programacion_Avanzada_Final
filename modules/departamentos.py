from typing import Dict, Any, List
from collections import Counter
import datetime
from .reclamos import EstadoReclamo

class Analitica:
    def __init__(self, gestor_servicio):
        self._gestor = gestor_servicio
        self.stopwords = ["el", "la", "los", "las", "un", "una", "y", "o", "de", "a", "en", "es", "para", "que", "con", "por", "su", "al"]

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
    
    def obtener_datos_dashboard(self, depto_id=None):
        # Si depto_id es None, traemos todos los reclamos de la DB
        if depto_id:
            reclamos = [r for r in self._gestor._reclamos_db.values() if r.departamento_id == depto_id]
        else:
            reclamos = list(self._gestor._reclamos_db.values())

        # 1. Estadísticas de Estados (Para gráfico de torta)
        stats = {
            "pendientes": sum(1 for r in reclamos if r.estado.value == "pendiente"),
            "en_proceso": sum(1 for r in reclamos if r.estado.value == "en_proceso"),
            "resueltos": sum(1 for r in reclamos if r.estado.value == "resuelto"),
            "total": len(reclamos)
        }

        # 2. Lógica de Nube de Palabras (Las 15 más frecuentes)
        todo_el_texto = " ".join([r.contenido.lower() for r in reclamos])
        # Limpieza: solo palabras de más de 3 letras que no estén en stopwords
        palabras = [p.strip('.,;!?()') for p in todo_el_texto.split() 
                    if len(p) > 3 and p not in self.stopwords]
        
        frecuencia = dict(Counter(palabras).most_common(15))

        return {
            "stats": stats,
            "frecuencia": frecuencia
        }

    def generar_reporte_html(self, depto_id: str, stats: dict = None, frecuencia: dict = None) -> str:
        # Genera una versión HTML simplificada para impresión/reporte.
        datos = self.obtener_datos_dashboard(depto_id)
        fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        titulo = f"Reporte de Gestión - {depto_id if depto_id else 'General'}"
        
        html = f"""
        <html>
        <head><title>{titulo}</title></head>
        <body style="font-family: sans-serif; padding: 20px;">
            <h1>{titulo}</h1>
            <p>Fecha de emisión: {fecha}</p>
            <hr>
            <h3>Resumen de Estados:</h3>
            <ul>
                <li>Pendientes: {datos['stats']['pendientes']}</li>
                <li>En Proceso: {datos['stats']['en_proceso']}</li>
                <li>Resueltos: {datos['stats']['resueltos']}</li>
                <li><b>Total: {datos['stats']['total']}</b></li>
            </ul>
            <h3>Palabras Clave Detectadas:</h3>
            <p>{", ".join(datos['frecuencia'].keys())}</p>
        </body>
        </html>
        """
        return html