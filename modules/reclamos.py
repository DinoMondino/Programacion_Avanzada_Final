from datetime import datetime, timezone
from .usuarios import db
from enum import Enum
from typing import List, Dict, Any

# Tabla intermedia para gestionar la relación muchos-a-muchos (N:M) entre usuarios y reclamos (adhesiones).
adhesiones = db.Table('adhesiones',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuarios.id'), primary_key=True),
    db.Column('reclamo_id', db.Integer, db.ForeignKey('reclamos.id'), primary_key=True)
)

# Definición del Enum para los estados de los reclamos
class EstadoReclamo(Enum):
    INVÁLIDO = "inválido"
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    RESUELTO = "resuelto"

class Reclamo(db.Model): # Clase Base para Reclamos, se transforma en tabla 'reclamos' en la base de datos
    __tablename__ = 'reclamos'
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    _estado = db.Column('estado', db.String(50), default='pendiente')
    departamento_id = db.Column(db.String(50))
    adjunto_url = db.Column(db.String(200))
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    # Usuarios que apoyan este reclamo
    seguidores = db.relationship('Usuario', secondary=adhesiones, backref='reclamos_apoyados')
    _tiempo_estimado = db.Column('tiempo_estimado', db.Integer, nullable=True) # en días
    tiempo_resolucion = db.Column(db.Integer, nullable=True)

    def get_num_adherentes(self) -> int:
        return len(self.seguidores)

    # Representación para depuración
    def __repr__(self):
        return f"<Reclamo {self.id} - {self.estado.value}>"
    
    @property
    def tiempo_estimado(self):
        return self._tiempo_estimado

    @tiempo_estimado.setter
    def tiempo_estimado(self, valor):
        if valor is not None:
            if not (1 <= valor <= 15):
                raise ValueError("El tiempo estimado debe estar entre 1 y 15 días.")
        self._tiempo_estimado = valor

    @property
    def estado(self):
        return self._estado

    @estado.setter
    def estado(self, nuevo_valor):
        validos = ['pendiente', 'en_proceso', 'resuelto', 'invalido']
        if nuevo_valor.lower() in validos:
            self._estado = nuevo_valor.lower()
        else:
            raise ValueError(f"El estado {nuevo_valor} no es permitido.")

class Clasificador:
    def __init__(self, stopwords = None):
        if stopwords is None:
            self.stopwords = ["el", "la", "los", "las", "un", "una", "y", "o", "de", "a", "en", "es", "para", "que", "con", "por", "su", "al"]
        else:
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
        # Extraemos palabras que no sean stopwords y tengan más de 2 caracteres

    def clasificar(self, contenido: str) -> Dict[str, Any]:
        palabras_reclamo = self.extraer_palabras_clave(contenido)
        contadores = {depto: 0 for depto in self.keywords_por_depto}
        # Contamos coincidencias por departamento
        for p in palabras_reclamo:
            for depto, keywords in self.keywords_por_depto.items():
                if p in keywords:
                    contadores[depto] += 1
        # Determinamos el departamento con más coincidencias
        max_v = max(contadores.values())
        if max_v == 0:
            return {"departamento_id": "D_SECRETARIA"}
            # Si no hay coincidencias, asignamos por defecto a Secretaría
        ganadores = [d for d, v in contadores.items() if v == max_v]
        return {"departamento_id": ganadores[0]}

    def buscar_similares(self, contenido, historial_reclamos):
        palabras_nuevo = set(self.extraer_palabras_clave(contenido))
        similares_ids = []
        # Buscamos reclamos con al menos 2 palabras clave en común
        for rid, rec in historial_reclamos.items():
            palabras_viejo = set(self.extraer_palabras_clave(rec.contenido))
            if len(palabras_nuevo.intersection(palabras_viejo)) >= 2:
                similares_ids.append(rid)
        return similares_ids # Retornamos los IDs de reclamos similares