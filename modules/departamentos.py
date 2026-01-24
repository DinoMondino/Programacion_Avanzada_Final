from typing import Dict, Any, List
from collections import Counter
import datetime
import heapq
from .reclamos import Reclamo, EstadoReclamo

# Para el análisis y generación de estadísticas
class Analitica:
    def __init__(self, gestor_servicio):
        self._gestor = gestor_servicio # Reutilizamos el gestor de reclamos
        self.stopwords = gestor_servicio.clasificador_servicio.stopwords # Reutilizamos las stopwords del clasificador

    def calcular_mediana(self, tiempos: List[int]) -> float:
        """
        Calcula la mediana utilizando el algoritmo de dos montículos (Heaps).
        Requerimiento Cursada 2024.
        """
        if not tiempos:
            return 0.0

        min_heap = [] # Montículo para la mitad superior
        max_heap = [] # Montículo para la mitad inferior (se guardan negativos)

        for num in tiempos:
            # 1. Insertar en el max_heap (negativo para simular max-heap)
            heapq.heappush(max_heap, -num)
            
            # 2. Asegurar que el elemento más grande de max_heap sea <= más pequeño de min_heap
            if max_heap and min_heap and (-max_heap[0] > min_heap[0]):
                val = -heapq.heappop(max_heap)
                heapq.heappush(min_heap, val)
            
            # 3. Balancear los tamaños (la diferencia no puede ser > 1)
            if len(max_heap) > len(min_heap) + 1:
                val = -heapq.heappop(max_heap)
                heapq.heappush(min_heap, val)
            elif len(min_heap) > len(max_heap):
                val = heapq.heappop(min_heap)
                heapq.heappush(max_heap, -val)

        # 4. Calcular la mediana según el tamaño
        if len(max_heap) > len(min_heap):
            return float(-max_heap[0])
        else:
            return (-max_heap[0] + min_heap[0]) / 2.0
        
    def obtener_estadisticas(self, reclamos: List[Reclamo]):
        """
        Genera el diccionario de estadísticas para el Dashboard.
        """
        tiempos_en_proceso = [r.tiempo_estimado for r in reclamos 
                              if r.estado == EstadoReclamo.EN_PROCESO.value and r.tiempo_estimado]
        
        tiempos_resueltos = [r.tiempo_resolucion for r in reclamos 
                            if r.estado == EstadoReclamo.RESUELTO.value and r.tiempo_resolucion]

        return {
            "total": len(reclamos),
            "mediana_en_proceso": self.calcular_mediana_eficiente(tiempos_en_proceso),
            "mediana_resueltos": self.calcular_mediana_eficiente(tiempos_resueltos),
            # Aquí irían los porcentajes para el gráfico circular [cite: 54, 133]
        }

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