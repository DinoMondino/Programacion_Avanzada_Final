from datetime import datetime
from .usuarios import db
from enum import Enum
from typing import List, Dict, Any


adhesiones = db.Table('adhesiones',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('reclamo_id', db.Integer, db.ForeignKey('reclamos.id'), primary_key=True)
)

class EstadoReclamo(Enum):
    INVÁLIDO = "inválido"
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    RESUELTO = "resuelto"

class Reclamo(db.Model):
    __tablename__ = 'reclamos'
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), default="pendiente")
    departamento_id = db.Column(db.String(50))
    adjunto_url = db.Column(db.String(200))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    
    # Usuarios que apoyan este reclamo
    seguidores = db.relationship('Usuario', secondary=adhesiones, backref='reclamos_apoyados')

    def get_num_adherentes(self) -> int:
        return len(self.seguidores)

    def __repr__(self):
        return f"<Reclamo {self.id} - {self.estado.value}>"


class Clasificador:
    def __init__(self, stopwords: List[str]):
        self.stopwords = stopwords
        self.keywords_por_depto = {
            "D_INFRAESTRUCTURA": ["luz", "agua", "techo", "baño", "edificio", "puerta", "ventana"],
            "D_INFORMATICA": ["wifi", "internet", "computadora", "servidor", "red", "sistema", "software", "programación"],
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