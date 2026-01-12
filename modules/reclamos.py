from enum import Enum
import datetime
from typing import List, Dict, Any, Optional

# --- Enums ---
class EstadoReclamo(Enum):
    # Estados posibles para un reclamo
    INVALIDO = "inválido"
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    RESUELTO = "resuelto"

# --- Utilidades ---
def generar_notificacion(id_usuario: str, mensaje: str):
    """Simulación de envío de notificaciones."""
    print(f"    [NOTIFICACION] -> Usuario {id_usuario}: {mensaje}")

# --- Clases de Entidad ---
class Reclamo:
    """
    Representa un Reclamo en el sistema.
    Optional --> Indica que el parámetro puede ser de un tipo específico o 'None'.
    Esto permite crear un Reclamo solo con los datos básicos y dejar el resto 
    como opcionales para el constructor.
    """
    def __init__(self, 
                 id_reclamo: str, 
                 contenido: str, 
                 usuario_creator_id: str, 
                 departamento_id: str, 
                 estado: EstadoReclamo, 
                 palabras_clave: Optional[List[str]] = None, 
                 adjunto_url: Optional[str] = None, 
                 fecha_creacion: Optional[datetime.datetime] = None, 
                 adherentes_ids: Optional[List[str]] = None):

        self.id: str = id_reclamo
        self.contenido: str = contenido
        self.usuario_creator_id: str = usuario_creator_id
        self.departamento_id: str = departamento_id
        self.estado: EstadoReclamo = estado
        
        # RF 39: El adjunto es opcional
        self.adjunto_url: Optional[str] = adjunto_url
        
        # Fecha: Si no se provee, se usa la actual (Timestamp - RF 38)
        self.fecha_creacion: datetime.datetime = fecha_creacion or datetime.datetime.now()
        
        # Listas: Se inicializan vacías si vienen como None para evitar errores de mutabilidad
        self.adherentes_ids: List[str] = adherentes_ids if adherentes_ids is not None else []
        self.palabras_clave: List[str] = palabras_clave if palabras_clave is not None else []
    
    def get_num_adherentes(self) -> int:
        """ Retorna el número de usuarios adheridos para mostrar en el listado."""
        return len(self.adherentes_ids)

    def __repr__(self):
        return f"<Reclamo ID={self.id} Estado={self.estado.value}>"

# --- Lógica de Clasificación ---
class Clasificador:
    # Clasifica el reclamo por contenido. Filtra 'stopwords' (palabras vacías).
    PALABRAS_CLAVE: Dict[str, List[str]] = {
        "D_INFRAESTRUCTURA": ["aula", "electricidad", "limpieza", "reparacion", "edificios", "gotera", "luz"],
        "D_FINANZAS": ["pago", "matricula", "becas", "gastos", "presupuesto", "factura"],
        "D_SECRETARIA": ["asignatura", "docente", "horarios", "calificaciones", "tramites", "examen"],
        "D_INFORMATICA": ["wifi", "internet", "red", "sistema", "computadora", "email"]
    }

    def __init__(self, stopwords: List[str]):
        # Ej. de stopwords: 'el', 'la', 'de', 'un', etc.
        self.stopwords: List[str] = [sw.lower() for sw in stopwords]

    def clasificar(self, contenido: str) -> Dict[str, Any]:
        # Analiza el texto y sugiere el departamento
        palabras_reclamo = contenido.lower().split()
        # Filtramos palabras que no aportan significado
        palabras_filtradas = [p for p in palabras_reclamo if p not in self.stopwords]

        contadores = {dept: 0 for dept in self.PALABRAS_CLAVE.keys()}
        for dept, claves in self.PALABRAS_CLAVE.items():
            for p in palabras_filtradas:
                if p in claves:
                    contadores[dept] += 1
        
        max_votos = max(contadores.values())
        if max_votos == 0:
            depto_id = "D_SECRETARIA" # Default
        else:
            # Selecciona el depto con más coincidencias
            depto_id = max(contadores, key=contadores.get)

        return {"departamento_id": depto_id}


    def extraer_palabras_clave(self, contenido: str) -> List[str]:
        # Limpia el contenido para la nube de palabras. Elimina puntuación y stopwords.
        palabras = contenido.lower().split()
        return [p.strip('.,;!?"') for p in palabras 
                if p.strip('.,;!?"') not in self.stopwords and len(p) > 2]
    
    def encontrar_similares(self, contenido: str, historial_reclamos: dict) -> list:
        """
        RF 40: Busca reclamos similares comparando la coincidencia de palabras clave.
        Si comparten 2 o más palabras clave, se considera similar.
        """
        # 1. Extraemos palabras clave del nuevo reclamo (filtrando stopwords)
        palabras_nuevo = set(self.extraer_palabras_clave(contenido))
        similares_ids = []

        # 2. Recorremos los reclamos existentes en la "DB"
        for reclamo_id, reclamo_obj in historial_reclamos.items():
            # Extraemos palabras clave del reclamo viejo
            palabras_viejo = set(self.extraer_palabras_clave(reclamo_obj.contenido))
            
            # 3. Calculamos la intersección (palabras que aparecen en ambos)
            coincidencias = palabras_nuevo.intersection(palabras_viejo)
            
            # 4. Si hay suficiente similitud (umbral de 2 palabras), guardamos el ID
            if len(coincidencias) >= 2:
                similares_ids.append(reclamo_id)
        
        return similares_ids