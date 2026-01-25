from typing import Dict, Any, List
from collections import Counter
import datetime
import heapq
from .reclamos import Reclamo, EstadoReclamo
from abc import ABC, abstractmethod
import io
from xhtml2pdf import pisa # Motor de conversión HTML a PDF

# Sirve para que el sistema pueda generar reportes en diferentes formatos
class EstrategiaReporte(ABC):
    @abstractmethod
    def exportar(self, titulo: str, datos: dict) -> str:
        pass

# --- Defino HTML ---
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
                <h3>Detalle de Reclamos:</h3>
                    <table border="1" style="width:100%; border-collapse: collapse;">
                        <tr><th>ID</th><th>Estado</th><th>Contenido</th></tr>
                        {" ".join([f"<tr><td>{r.id}</td><td>{r.estado}</td><td>{r.contenido[:50]}...</td></tr>" for r in datos['lista_reclamos']])}
                    </table>
            </body>
        </html>
        """
        return html

# --- Defino PDF ---
class ReportePDF(EstrategiaReporte):
    def exportar(self, titulo: str, datos: dict) -> bytes:
        # 1. Obtenemos el texto HTML de la otra estrategia
        html_content = ReporteHTML().exportar(titulo, datos)
        # 2. Creamos un buffer (un archivo virtual en la memoria RAM)
        result = io.BytesIO()
        
        # 3. Convertimos el HTML a PDF binario
        # src: el texto HTML / dest: donde se guarda el binario generado
        pisa_status = pisa.CreatePDF(
            src=io.StringIO(html_content), 
            dest=result
        )
        # 4. Si pisa_status.err es 0 (False), todo salió bien
        if pisa_status.err:
            print("Error al generar el PDF")
            return b"" # Retorna bytes vacíos en caso de error
        # 5. Retornamos los bytes reales del PDF
        return result.getvalue()

# Para el análisis y generación de estadísticas
class Analitica:
    def __init__(self, gestor_servicio):
        self._gestor = gestor_servicio # Reutilizamos el gestor de reclamos
        self.stopwords = gestor_servicio.clasificador_servicio.stopwords # Reutilizamos las stopwords del clasificador

    def calcular_mediana(self, tiempos: List[int]) -> float:
        # Calcula la mediana utilizando el algoritmo de dos montículos (Heaps).
        if not tiempos:
            return 0.0

        min_heap = [] # Montículo para la mitad de los números más grandes
        max_heap = [] # Montículo para la mitad de los números más chicos (se guardan negativos, asi el mas grande pasa a ser el mas chico)
        # Para que la mediana sea el medio, los heaps deben estar balanceados y tener la misma cantidad o max_heap tener uno más.
        # Cada vez que insertamos un número, hacemos el balanceo.
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
        # Si max_heap tiene un elemento más, la mediana es su raíz. Si son iguales, es el promedio de ambas raíces.
        if len(max_heap) > len(min_heap):
            return float(-max_heap[0])
        else:
            return (-max_heap[0] + min_heap[0]) / 2.0
        # Sort O(n log n) vs Heaps O(n log k) donde k es la mitad del tamaño en el peor caso.
        
    def obtener_estadisticas(self, reclamos: List[Reclamo]):
        # Extraemos los tiempos para los dos grupos requeridos
        tiempos_en_proceso = [r.tiempo_estimado for r in reclamos 
                              if r.estado == EstadoReclamo.EN_PROCESO.value and r.tiempo_estimado]
        
        tiempos_resueltos = [r.tiempo_resolucion for r in reclamos 
                            if r.estado == EstadoReclamo.RESUELTO.value and r.tiempo_resolucion]

        # Calculamos porcentajes para el diagrama circular 
        total = len(reclamos) if reclamos else 1
        pendientes = [r for r in reclamos if r.estado == EstadoReclamo.PENDIENTE.value]
        en_p = [r for r in reclamos if r.estado == EstadoReclamo.EN_PROCESO.value]
        res = [r for r in reclamos if r.estado == EstadoReclamo.RESUELTO.value]

        return {
            "total_reclamos": len(reclamos),
            "conteos": {
                "pendientes": len(pendientes),
                "en_proceso": len(en_p),
                "resueltos": len(res)
            },
            "porcentajes": {
                "pendiente": round((len(pendientes) / total) * 100, 2),
                "en_proceso": round((len(en_p) / total) * 100, 2),
                "resuelto": round((len(res) / total) * 100, 2)
            },
            "mediana_en_proceso": round(self.calcular_mediana(tiempos_en_proceso), 2),
            "mediana_resueltos": round(self.calcular_mediana(tiempos_resueltos), 2)
        }

    def obtener_datos_dashboard(self, depto_id: str) -> Dict[str, Any]:
        # 1. Una sola Query
        query = Reclamo.query
        if depto_id and depto_id != 'D_GENERAL':
            query = query.filter_by(departamento_id=depto_id)
        reclamos = query.all()
        
        # 2. Delegamos el cálculo a obtener_estadisticas
        resumen = self.obtener_estadisticas(reclamos)
        
        # 3. Procesamiento de palabras más frecuentes (excluyendo stopwords)
        texto_total = " ".join([r.contenido for r in reclamos])
        palabras = [p.lower().strip('.,;!?') for p in texto_total.split() if len(p) > 3]
        frecuencia = {}
        for p in palabras:
            if p not in self.stopwords:
                frecuencia[p] = frecuencia.get(p, 0) + 1
        
        frecuencia_top = dict(sorted(frecuencia.items(), key=lambda x: x[1], reverse=True)[:15])

        return {
            "stats": {
                **resumen["conteos"],
                "total": resumen["total_reclamos"],
                "mediana_en_proceso": resumen["mediana_en_proceso"],
                "mediana_resueltos": resumen["mediana_resueltos"]
            },
            "porcentajes": resumen["porcentajes"],
            "frecuencia": frecuencia_top,
            "lista_reclamos": reclamos
        }
        
    def generar_reporte(self, depto_id: str, estrategia: EstrategiaReporte):
        # Método unificado que utiliza el Patrón Strategy.
        datos = self.obtener_datos_dashboard(depto_id)
        titulo = f"Reporte de Gestión - {depto_id if depto_id else 'General'}"
        
        # Delegamos la responsabilidad a la estrategia elegida
        return estrategia.exportar(titulo, datos)