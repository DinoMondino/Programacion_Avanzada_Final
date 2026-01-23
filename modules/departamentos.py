from typing import Dict, Any, List
from collections import Counter
import datetime
from .reclamos import EstadoReclamo

# Para el análisis y generación de estadísticas
class Analitica:
    def __init__(self, gestor_servicio):
        self._gestor = gestor_servicio # Reutilizamos el gestor de reclamos
        self.stopwords = gestor_servicio.clasificador_servicio.stopwords # Reutilizamos las stopwords del clasificador

    def obtener_datos_dashboard(self, depto_id: str) -> Dict[str, Any]:
        from .reclamos import Reclamo # Importación local para evitar importes circulares
        # Filtramos por dpto, si es None --> Secretario Técnico, si tiene ID --> Jefe, filtramos por su departamento.
        query = Reclamo.query
        if depto_id:
            query = query.filter_by(departamento_id=depto_id)
        reclamos = query.all()
        
        # Contamos cada estado
        pendientes = len([r for r in reclamos if r.estado == "pendiente"])
        en_proceso = len([r for r in reclamos if r.estado == "en_proceso"])
        resueltos = len([r for r in reclamos if r.estado == "resuelto"])
        
        # Procesamos las palabras clave para la nube
        texto_total = " ".join([r.contenido for r in reclamos])
        palabras = [p.lower().strip('.,') for p in texto_total.split() if len(p) > 3]
        frecuencia = {}
        for p in palabras:
            if p not in self.stopwords:
                frecuencia[p] = frecuencia.get(p, 0) + 1
        
        return {
            "stats": {
                "pendientes": pendientes,
                "en_proceso": en_proceso,
                "resueltos": resueltos,
                "total": len(reclamos)
            },
            "frecuencia": dict(sorted(frecuencia.items(), key=lambda x: x[1], reverse=True)[:15])
        } # Retornamos solo las 15 palabras más comunes
        
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