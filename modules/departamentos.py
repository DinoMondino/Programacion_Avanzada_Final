import datetime 
from typing import List, Dict, Any, Optional
from .reclamos import Reclamo, EstadoReclamo
from .gestor import Gestor_Reclamos

""" Que analitica haga las gráficas y lo del html, los tiene que generar y despues poenerlo tmb en app.py"""

class Departamento:
    def __init__(self, id_departamento: str, nombre: str, jefe_id: str, gestor_servicio: Optional[Any] = None):
        self.id: str = id_departamento
        self.nombre: str = nombre
        self.jefe_id: str = jefe_id 
        self._gestor_reclamos = gestor_servicio # Dependencia inyectada

    def listar_reclamos(self) -> List[Reclamo]:
        # Devuelve todos los reclamos asociados al departamento, usando el Gestor
        if self._gestor_reclamos:
            return self._gestor_reclamos.get_reclamos_por_departamento(self.id)
        print(f"[Departamento: {self.nombre}] Advertencia: Gestor no disponible.")
        return []

    def listar_reclamos_pendientes(self) -> List[Reclamo]:
        # Devuelve solo los reclamos en estado PENDIENTE
        if self._gestor_reclamos:
            return self._gestor_reclamos.get_reclamos_pendientes_filtrados(self.id)
        print(f"[Departamento: {self.nombre}] Advertencia: Gestor no disponible.")
        return [] 


class Analitica:
    # Para calcular métricas y reportes sobre los reclamos
    def __init__(self, gestor_servicio: Gestor_Reclamos):
        self._gestor_reclamos = gestor_servicio

    def get_reclamos_depto(self, departamento_id: str) -> List[Reclamo]:
        if self._gestor_reclamos:
            return self._gestor_reclamos.get_reclamos_por_departamento(departamento_id)
        return []
        
    def get_estadisticas_generales(self, departamento_id: str) -> Dict[str, float]:
        # Calcula el porcentaje de reclamos por estado y hace una gráfica circular
        print(f"[Analitica] Calculando estadísticas para depto ID: {departamento_id}")
        reclamos = self.get_reclamos_depto(departamento_id)
        total = len(reclamos)
        
        if total == 0:
            return {
                "total_reclamos": 0,
                "pct_en_proceso": 0.0,
                "pct_resueltos": 0.0,
                "pct_invalidos": 0.0,
                "pct_pendientes": 0.0
            }

        conteo = {estado: 0 for estado in EstadoReclamo}
        for r in reclamos:
            conteo[r.estado] += 1
            
        return {
            "total_reclamos": total,
            "pct_en_proceso": round((conteo[EstadoReclamo.EN_PROCESO] / total) * 100, 2),
            "pct_resueltos": round((conteo[EstadoReclamo.RESUELTO] / total) * 100, 2),
            "pct_invalidos": round((conteo[EstadoReclamo.INVALIDO] / total) * 100, 2),
            "pct_pendientes": round((conteo[EstadoReclamo.PENDIENTE] / total) * 100, 2)
        }

    def get_frecuencia_palabras(self, departamento_id: str) -> Dict[str, int]:
        # Calcula la frecuencia de las palabras clave más comunes (sin stopwords)
        from collections import Counter
        
        print(f"[Analitica] Calculando frecuencia de palabras clave para depto ID: {departamento_id}")
        reclamos = self.get_reclamos_depto(departamento_id)
        
        todas_palabras = []
        for r in reclamos:
            todas_palabras.extend(r.palabras_clave)
            
        frecuencia = Counter(todas_palabras)
        
        top_n = dict(frecuencia.most_common(20)) 
        return top_n

    def generar_reporte_html(self, departamento_id: str, stats: Dict[str, float], frecuencia: Dict[str, int]) -> str:
        # Genera y devuelve un reporte en formato HTML, incluyendo estadísticas y nube de palabras
        print(f"[Analitica] Generando reporte HTML para depto ID: {departamento_id}")
        
        # Formateo de la frecuencia para el HTML
        frec_html = "<ul>"
        for palabra, cuenta in frecuencia.items():
            frec_html += f"<li>{palabra}: {cuenta}</li>"
        frec_html += "</ul>"
        
        # Formateo de las estadísticas
        stats_html = (
            f"<p>Total de Reclamos: <b>{stats.get('total_reclamos', 0)}</b></p>"
            "<table>"
            "<thead><tr><th>Estado</th><th>Porcentaje</th></tr></thead><tbody>"
            f"<tr><td>PENDIENTE</td><td>{stats.get('pct_pendientes', 0.0)}%</td></tr>"
            f"<tr><td>EN PROCESO</td><td>{stats.get('pct_en_proceso', 0.0)}%</td></tr>"
            f"<tr><td>RESUELTO</td><td>{stats.get('pct_resueltos', 0.0)}%</td></tr>"
            f"<tr><td>INVÁLIDO</td><td>{stats.get('pct_invalidos', 0.0)}%</td></tr>"
            "</tbody></table>"
        )
        
        # Contenido HTML con un poco de estilo simulado
        html_content = f"""\
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Reclamos - Depto. {departamento_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #004d40; border-bottom: 2px solid #004d40; padding-bottom: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background-color: #e0f2f1; }}
        .section {{ margin-top: 30px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Reporte de Reclamos - Depto. {departamento_id}</h1>

    <div class="section">
        <h2>Estadísticas Generales (Diagrama Circular)</h2>
        {stats_html}
    </div>

    <div class="section">
        <h2>Frecuencia de Palabras Clave (Word Cloud)</h2>
        {frec_html}
    </div>
    
    <p style="margin-top: 40px; font-size: 0.8em; color: #888;">Reporte generado el {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body>
</html>
""" # <--- CORRECCIÓN CLAVE: La cadena se ajusta a la izquierda para que empiece en <html>
        return html_content


    def generar_reporte_pdf(self, departamento_id: str) -> str:
        """
        Simula la generación de un reporte en formato PDF. (RF 59)
        """
        # En una aplicación real, esto usaría una librería como ReportLab o FPDF.
        print(f"[Analitica] Simulación: Generando reporte PDF para depto ID: {departamento_id}")
        return f"Reporte PDF para el Departamento {departamento_id} (Simulado: Contiene estadísticas y nube de palabras clave)."