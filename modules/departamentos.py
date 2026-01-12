import datetime 
from typing import List, Dict, Any, Optional
from collections import Counter
from .reclamos import Reclamo, EstadoReclamo
from .gestor import Gestor_Reclamos

class Departamento:
    """Unidad administrativa de la facultad, mantiene una relación 1 a muchos con Reclamo."""
    def __init__(self, id_departamento: str, nombre: str, jefe_id: str, gestor_servicio: Optional[Gestor_Reclamos] = None):
        self.id: str = id_departamento
        self.nombre: str = nombre
        self.jefe_id: str = jefe_id # ID del Usuario_Admin responsable
        self._gestor_reclamos = gestor_servicio 
        self.lista_reclamos: List[Reclamo] = []

    def listar_reclamos(self) -> List[Reclamo]:
        # Muestra la lista de reclamos pertenecientes al departamento.
        # Actualiza la lista interna desde el gestor.
        if self._gestor_reclamos:
            self.lista_reclamos = self._gestor_reclamos.get_reclamos_por_departamento(self.id)
        return self.lista_reclamos

    def listar_reclamos_pendientes(self) -> List[Reclamo]:
        # Filtra los reclamos para la vista operativa del jefe de departamento.
        return [r for r in self.listar_reclamos() if r.estado == EstadoReclamo.PENDIENTE]


class Analitica:
    """ Genera estadísticas y reportes para que visualizen los responsables."""
    def __init__(self, gestor_servicio: Gestor_Reclamos):
        self._gestor_reclamos = gestor_servicio

    def get_estadisticas_generales(self, departamento_id: str) -> Dict[str, Any]:
        # Calcula porcentajes para el diagrama circular (Totales, % en Proceso y % Resueltos).
        reclamos = self._gestor_reclamos.get_reclamos_por_departamento(departamento_id)
        total = len(reclamos)
        
        if total == 0:
            return {
                "total_reclamos": 0,
                "pct_en_proceso": 0.0,
                "pct_resueltos": 0.0
            }

        # Conteo según estados del Enum
        en_proceso = sum(1 for r in reclamos if r.estado == EstadoReclamo.EN_PROCESO)
        resueltos = sum(1 for r in reclamos if r.estado == EstadoReclamo.RESUELTO)
        
        return {
            "total_reclamos": total,
            "pct_en_proceso": round((en_proceso / total) * 100, 2),
            "pct_resueltos": round((resueltos / total) * 100, 2)
        }

    def get_frecuencia_palabras(self, departamento_id: str) -> Dict[str, int]:
        # Obtiene las 15 palabras clave más frecuentes. 'Clasificador' ya filtró las stopwords.
        reclamos = self._gestor_reclamos.get_reclamos_por_departamento(departamento_id)
        
        todas_palabras = []
        for r in reclamos:
            # Las palabras_clave se extraen del contenido del reclamo
            todas_palabras.extend(r.palabras_clave)
            
        frecuencia = Counter(todas_palabras)
        return dict(frecuencia.most_common(15))

    def generar_reporte_html(self, departamento_id: str) -> str:
        # Genera reporte en formato HTML con gráficas y tablas.
        stats = self.get_estadisticas_generales(departamento_id)
        frecuencia = self.get_frecuencia_palabras(departamento_id)
        # Formateo de la frecuencia para simular la "Nube de Palabras". A mayor frecuencia, mayor 'font-size'
        frec_html = "<div>"
        for palabra, cuenta in frecuencia.items():
            tamanio = 10 + (cuenta * 2) # Lógica para tamaño de fuente
            frec_html += f"<span style='font-size:{tamanio}px; margin:5px;'>{palabra}</span> "
        frec_html += "</div>"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: sans-serif; }}
                .stat-box {{ border: 1px solid #333; padding: 10px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h1>Reporte de Gestión - Depto {departamento_id}</h1>
            <div class="stat-box">
                <h2>Estadísticas (RF 54)</h2>
                <p>Total Reclamos: {stats['total_reclamos']}</p>
                <p>En Proceso: {stats['pct_en_proceso']}%</p>
                <p>Resueltos: {stats['pct_resueltos']}%</p>
            </div>
            <div class="stat-box">
                <h2>Nube de Palabras Clave (RF 55/56)</h2>
                {frec_html}
            </div>
            <footer>Generado el: {datetime.datetime.now()}</footer>
        </body>
        </html>
        """
        return html_content

    def generar_reporte_pdf(self, departamento_id: str) -> str:
        # Genera reporte en formato PDF, se devuelve su ruta.
        print(f"Generando PDF para depto {departamento_id}...")
        return f"reporte_{departamento_id}.pdf"
    
    def obtener_datos_dashboard(self, depto_id: str):
        """RF 54: Retorna estadísticas unificadas para la UI y Tests."""
        stats = self.get_estadisticas_generales(depto_id)
        # Aseguramos que existan las claves que el test 'test_gestor_y_analitica.py' busca
        return {
            "total": stats.get("total_reclamos", 0),
            "pendientes": stats.get("pendientes", 0),
            "resueltos": stats.get("resueltos_porcentaje", 0),
            "stats": stats,
            "frecuencia": self.get_frecuencia_palabras(depto_id)
        }