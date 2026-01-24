from typing import Dict, Any, List
from collections import Counter
import datetime
import heapq
from .reclamos import Reclamo, EstadoReclamo
from abc import ABC, abstractmethod

# --- INTERFAZ ESTRATEGIA ---
class EstrategiaReporte(ABC):
    @abstractmethod
    def exportar(self, titulo: str, datos: dict) -> str:
        pass

# --- ESTRATEGIA HTML ---
class ReporteHTML(EstrategiaReporte):
    def exportar(self, titulo: str, datos: dict) -> str:
        fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        html = f"""
        <html>
            <body style="font-family: Arial;">
                <h1>{titulo}</h1>
                <p>Generado el: {fecha}</p>
                <hr>
                <h3>Estadísticas:</h3>
                <ul>
                    <li>Pendientes: {datos['stats']['pendientes']}</li>
                    <li>Mediana En Proceso: {datos['stats']['mediana_en_proceso']} días</li>
                    <li>Mediana Resueltos: {datos['stats']['mediana_resueltos']} días</li>
                </ul>
            </body>
        </html>
        """
        return html

# --- ESTRATEGIA PDF (Simulada o con xhtml2pdf) ---
class ReportePDF(EstrategiaReporte):
    def exportar(self, titulo: str, datos: dict) -> str:
        # Aquí se usaría una librería como xhtml2pdf para convertir el HTML a PDF binary
        html_content = ReporteHTML().exportar(titulo, datos)
        print(f"Transformando reporte '{titulo}' a formato PDF...")
        return html_content # En una implementación real, retornaría el PDF binario

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
        Genera las estadísticas incluyendo la mediana eficiente (Heaps). 
        """
        # Extraemos los tiempos para los dos grupos requeridos
        tiempos_en_proceso = [r.tiempo_estimado for r in reclamos 
                              if r.estado == EstadoReclamo.EN_PROCESO.value and r.tiempo_estimado]
        
        tiempos_resueltos = [r.tiempo_resolucion for r in reclamos 
                            if r.estado == EstadoReclamo.RESUELTO.value and r.tiempo_resolucion]

        # Calculamos porcentajes para el diagrama circular 
        total = len(reclamos) if reclamos else 1
        pendientes = len([r for r in reclamos if r.estado == EstadoReclamo.PENDIENTE.value])
        en_p = len([r for r in reclamos if r.estado == EstadoReclamo.EN_PROCESO.value])
        res = len([r for r in reclamos if r.estado == EstadoReclamo.RESUELTO.value])

        return {
            "total_reclamos": len(reclamos),
            "porcentajes": {
                "pendiente": (pendientes / total) * 100,
                "en_proceso": (en_p / total) * 100,
                "resuelto": (res / total) * 100
            },
            # REQUERIMIENTO 2024: Medianas calculadas con montículos 
            "mediana_en_proceso": self.calcular_mediana(tiempos_en_proceso),
            "mediana_resueltos": self.calcular_mediana(tiempos_resueltos)
        }

    def obtener_datos_dashboard(self, depto_id: str) -> Dict[str, Any]:
        from .reclamos import Reclamo, EstadoReclamo
        
        query = Reclamo.query
        if depto_id:
            query = query.filter_by(departamento_id=depto_id)
        reclamos = query.all()
        
        # 1. Contadores de estado (usando Enum para mayor seguridad)
        pendientes = [r for r in reclamos if r.estado == EstadoReclamo.PENDIENTE.value]
        en_proceso = [r for r in reclamos if r.estado == EstadoReclamo.EN_PROCESO.value]
        resueltos = [r for r in reclamos if r.estado == EstadoReclamo.RESUELTO.value]
        
        # 2. REQUERIMIENTO 2024: Preparar listas para la MEDIANA
        # Extraemos solo los valores numéricos
        tiempos_en_p = [r.tiempo_estimado for r in en_proceso if r.tiempo_estimado is not None]
        tiempos_res = [r.tiempo_resolucion for r in resueltos if r.tiempo_resolucion is not None]

        # 3. Procesamos las palabras clave (tu lógica original)
        texto_total = " ".join([r.contenido for r in reclamos])
        palabras = [p.lower().strip('.,;!?') for p in texto_total.split() if len(p) > 3]
        frecuencia = {}
        for p in palabras:
            if p not in self.stopwords:
                frecuencia[p] = frecuencia.get(p, 0) + 1
        
        # 4. Retorno con todos los datos para el Dashboard y Reportes
        return {
            "stats": {
                "pendientes": len(pendientes),
                "en_proceso": len(en_proceso),
                "resueltos": len(resueltos),
                "total": len(reclamos),
                # REQUERIMIENTO 2024: Aquí usamos el algoritmo de montículos
                "mediana_en_proceso": self.calcular_mediana(tiempos_en_p),
                "mediana_resueltos": self.calcular_mediana(tiempos_res)
            },
            "frecuencia": dict(sorted(frecuencia.items(), key=lambda x: x[1], reverse=True)[:15])
        }
    def generar_reporte(self, depto_id: str, estrategia: EstrategiaReporte):
        """
        Método unificado que utiliza el Patrón Strategy.
        Cumple con el requerimiento de añadir nuevos formatos de forma confiable.
        """
        datos = self.obtener_datos_dashboard(depto_id)
        titulo = f"Reporte de Gestión - {depto_id if depto_id else 'General'}"
        
        # Delegamos la responsabilidad a la estrategia elegida
        return estrategia.exportar(titulo, datos)