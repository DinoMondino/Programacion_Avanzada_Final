from enum import Enum
import datetime
from typing import List, Dict, Any, Optional
import random

"""preguntar que hace el optional, mejorar lo de reclamos similares y lo de repetir contraseña"""

class EstadoReclamo(Enum):
    INVALIDO = "inválido"
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    RESUELTO = "resuelto"

# Simulación de notificaciones
def generar_notificacion(id_usuario: str, mensaje: str):
    print(f"    [NOTIFICACION] -> Usuario {id_usuario}: {mensaje}")

# --- Clases de Entidad ---

class Adjunto:
# Representa un archivo adjunto al reclamo.
    def __init__(self, id_adjunto: str, url_imagen: str, reclamo_id: str):
        self.id: str = id_adjunto
        self.url_imagen: str = url_imagen
        self.reclamo_id: str = reclamo_id # Clave al reclamo asociado


class Notificacion:
# Representa una notificación enviada al usuario final sobre el estado del reclamo.
    def __init__(self, id_notificacion: str, id_reclamo: str, id_usuario: str, 
                 mensaje: str, fecha_creacion: datetime.datetime):
        self.id: str = id_notificacion
        self.id_reclamo: str = id_reclamo
        self.id_usuario: str = id_usuario # ID del usuario al que se notifica
        self.mensaje: str = mensaje
        self.fecha_creacion: datetime.datetime = fecha_creacion
         
class Reclamo:
    def __init__(self, id_reclamo: str, contenido: str, usuario_creator_id: str, 
                 departamento_id: str, estado: EstadoReclamo, 
                 adjunto: Optional[str] = None, fecha_creacion: Optional[datetime.datetime] = None,
                 adherentes_ids: Optional[List[str]] = None, palabras_clave: Optional[List[str]] = None):
        self.id: str = id_reclamo
        self.contenido: str = contenido
        self.usuario_creator_id: str = usuario_creator_id
        self.departamento_id: str = departamento_id
        self.estado: EstadoReclamo = estado
        self.adjunto: Optional[str] = adjunto
        self.fecha_creacion: datetime.datetime = fecha_creacion or datetime.datetime.now()
        self.adherentes_ids: List[str] = adherentes_ids if adherentes_ids is not None else []
        self.palabras_clave: List[str] = palabras_clave if palabras_clave is not None else []

    def get_num_adherentes(self) -> int:
        return len(self.adherentes_ids)
        
    def __repr__(self):
        return f"Reclamo(id={self.id}, depto={self.departamento_id}, estado={self.estado.name})"


class Clasificador:
    """
    Analiza y clasifica el contenido de los reclamos basándose en un sistema
    de conteo de palabras clave ponderado. También sugiere IDs de reclamos similares.
    """
    PALABRAS_CLAVE: Dict[str, List[str]] = {
        "D_INFRAESTRUCTURA": ["aula", "electricidad", "limpieza", "reparacion", "edificios", "gotera", "luz"],
        "D_FINANZAS": ["pago", "matricula", "becas", "gastos", "presupuesto", "factura"],
        "D_SECRETARIA": ["asignatura", "docente", "horarios", "calificaciones", "tramites", "examen"],
        "D_INFORMATICA": ["wifi", "internet", "red", "sistema", "computadora", "email"]
    }

    DEPARTAMENTOS_MAP: Dict[str, str] = {
        "D_INFRAESTRUCTURA": "Infraestructura",
        "D_FINANZAS": "Finanzas",
        "D_SECRETARIA": "Secretaría",
        "D_INFORMATICA": "Informática",
    }

    def __init__(self, stopwords: List[str]):
        self.stopwords: List[str] = [sw.lower() for sw in stopwords]
        self.departamento_ids: List[str] = list(self.PALABRAS_CLAVE.keys())

    def clasificar(self, contenido: str, historial_reclamos: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        print(f"[Clasificador] Clasificando contenido: '{contenido[:30]}...'")
        
        palabras_reclamo = contenido.lower().split()
        palabras_filtradas = [
            palabra for palabra in palabras_reclamo 
            if palabra not in self.stopwords
        ]

        # 3. Contar coincidencias de palabras clave por departamento
        contadores: Dict[str, int] = {dept_id: 0 for dept_id in self.departamento_ids}

        for dept_id, palabras_claves in self.PALABRAS_CLAVE.items():
            for palabra in palabras_filtradas:
                if palabra in palabras_claves:
                    contadores[dept_id] += 1
        
        # Determina el departamento ganador
        max_conteo = max(contadores.values())
        departamentos_ganadores = [
            dept_id for dept_id, conteo in contadores.items() 
            if conteo == max_conteo
        ]

        if max_conteo == 0:
            # Asignación fija a D_SECRETARIA cuando no hay coincidencias
            departamento_id = "D_SECRETARIA"
            print(f"  -> Ninguna palabra clave encontrada. Asignación por default a {departamento_id}.")
        elif len(departamentos_ganadores) > 1:
            # Si hay un empate, selección aleatoria entre los ganadores
            departamento_id = random.choice(departamentos_ganadores)
            print(f"  -> Empate entre {departamentos_ganadores}. Seleccionado aleatoriamente {departamento_id}.")
        else:
            departamento_id = departamentos_ganadores[0]
            print(f"  -> Clasificado como {departamento_id} con {max_conteo} coincidencias.")
            
        # Sugerir reclamos similares basado en palabras específicas
        reclamos_similares_ids = self._sugerir_similares(departamento_id, contenido, historial_reclamos)

        return {
            "departamento_id": departamento_id,
            "reclamos_similares_ids": reclamos_similares_ids
        }

    def _sugerir_similares(self, departamento_id: str, contenido: str, historial_reclamos: Optional[List[Dict[str, Any]]] = None) -> List[str]:        
        
        if "wifi" in contenido.lower() or "internet" in contenido.lower():
            return ["R001", "R005"] 
        elif "gotera" in contenido.lower() or "luz" in contenido.lower():
            return ["R004"]
        
        return []
        
    def extraer_palabras_clave(self, contenido: str) -> List[str]:
        """
        Extrae y devuelve una lista de palabras clave relevantes del contenido,
        filtrando las stopwords
        """
        print("[Clasificador] Extrayendo palabras clave completado.")
        palabras = contenido.lower().split()
        
        # Simulación de extracción simple
        palabras_clave = [p.strip('.,;!?"\'()[]') 
                          for p in palabras 
                          if p.lower().strip('.,;!?"\'()[]') and p.lower() not in self.stopwords]
                          
        return palabras_clave