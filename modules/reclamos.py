from enum import Enum
import datetime
from typing import List, Dict, Any, Optional

class EstadoReclamo(Enum):
    INVALIDO = "inválido"
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    RESUELTO = "resuelto"

class Reclamo:
    def __init__(self, id_reclamo: str, contenido: str, usuario_creator_id: str, 
                 departamento_id: str, estado: EstadoReclamo, 
                 palabras_clave: Optional[List[str]] = None, 
                 adjunto_url: Optional[str] = None, 
                 fecha_creacion: Optional[datetime.datetime] = None, 
                 adherentes_ids: Optional[List[str]] = None):
        self.id = id_reclamo
        self.contenido = contenido
        self.usuario_creator_id = usuario_creator_id
        self.departamento_id = departamento_id
        self.estado = estado
        self.palabras_clave = palabras_clave or []
        self.adjunto_url = adjunto_url
        # [CAMBIO] Se asegura que siempre haya un timestamp de creación
        self.fecha_creacion = fecha_creacion or datetime.datetime.now()
        self.adherentes_ids = adherentes_ids or []

    def get_num_adherentes(self) -> int:
        return len(self.adherentes_ids)

    def __repr__(self):
        return f"<Reclamo {self.id} - {self.estado.value}>"


class Clasificador:
    def __init__(self, stopwords: List[str]):
        self.stopwords = stopwords
        self.keywords_por_depto = {
            "D_INFRAESTRUCTURA": ["luz", "agua", "techo", "baño", "edificio", "puerta", "ventana"],
            "D_INFORMATICA": ["wifi", "internet", "computadora", "servidor", "red", "sistema", "software"],
            "D_SECRETARIA": ["inscripcion", "examen", "final", "certificado", "alumno", "nota", "acta"]
        }

    def extraer_palabras_clave(self, contenido: str) -> List[str]:
        palabras = contenido.lower().split()
        return [p.strip('.,;!?') for p in palabras 
                if p.strip('.,;!?') not in self.stopwords and len(p) > 2]

    def clasificar(self, contenido: str) -> Dict[str, Any]:
        palabras_reclamo = self.extraer_palabras_clave(contenido)
        contadores = {depto: 0 for depto in self.keywords_por_depto}
        
        for p in palabras_reclamo:
            for depto, keywords in self.keywords_por_depto.items():
                if p in keywords:
                    contadores[depto] += 1
        
        max_v = max(contadores.values())
        if max_v == 0:
            return {"departamento_id": "D_SECRETARIA"}
            
        ganadores = [d for d, v in contadores.items() if v == max_v]
        return {"departamento_id": ganadores[0]}

    def encontrar_similares(self, contenido: str, historial_reclamos: dict) -> list:
        palabras_nuevo = set(self.extraer_palabras_clave(contenido))
        similares_ids = []
        for rid, rec in historial_reclamos.items():
            palabras_viejo = set(self.extraer_palabras_clave(rec.contenido))
            if len(palabras_nuevo.intersection(palabras_viejo)) >= 2:
                similares_ids.append(rid)
        return similares_ids