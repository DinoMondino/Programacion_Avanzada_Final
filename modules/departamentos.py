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
    
    # modules/departamentos.py

    def obtener_datos_dashboard(self, departamento_id=None):
        from modules.reclamos import Reclamo
        
        # Filtro de reclamos
        if departamento_id:
            query = Reclamo.query.filter_by(departamento_id=departamento_id).all()
        else:
            query = Reclamo.query.all()

        # Lógica de estados para el gráfico
        pendientes = len([r for r in query if r.estado == 'pendiente'])
        resueltos = len([r for r in query if r.estado == 'resuelto'])

        # Lógica para la Nube de Palabras
        texto_total = " ".join([r.contenido.lower() for r in query])
        palabras = [p for p in texto_total.split() if len(p) > 3] # Filtra palabras cortas
        frecuencia = {}
        for p in palabras:
            frecuencia[p] = frecuencia.get(p, 0) + 1
        
        # IMPORTANTE: Retornar con la estructura exacta que pide el HTML
        return {
            "stats": {
                "pendientes": pendientes,
                "resueltos": resueltos
            },
            "frecuencia": dict(sorted(frecuencia.items(), key=lambda x: x[1], reverse=True)[:15])
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