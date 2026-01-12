from typing import Dict, Any, Optional, List
import datetime
from .reclamos import Reclamo, Clasificador, EstadoReclamo, generar_notificacion

class Gestor_Reclamos:
    """ Gestiona el ciclo de vida de los reclamos. """
    def __init__(self, clasificador_servicio: Clasificador):
        self.clasificador_servicio: Clasificador = clasificador_servicio
        # Simulación de base de datos en memoria
        self._reclamos_db: Dict[str, Reclamo] = {}
        self._next_reclamo_id: int = 1
        
    def _get_next_id(self) -> str:
        # Genera ID alfanumérico único para el reclamo
        new_id = f"REC-{self._next_reclamo_id:05d}" 
        self._next_reclamo_id += 1
        return new_id

    def get_reclamo(self, reclamo_id: str) -> Optional[Reclamo]:
        # Busca un reclamo específico por su identificador único.
        return self._reclamos_db.get(reclamo_id)

    def crear_reclamo(self, contenido: str, adjunto: Optional[str], usuario_creator_id: str) -> Dict[str, Any]:

        # Clasificación por contenido
        clasificacion = self.clasificador_servicio.clasificar(contenido)
        depto_sugerido = clasificacion["departamento_id"]
        
        # Búsqueda de similares
        similares_ids = self.clasificador_servicio.encontrar_similares(contenido, self._reclamos_db)
        
        # Si existen reclamos similares PENDIENTES, se retorna para que la UI pregunte por adhesión
        if similares_ids:
            return {
                "status": "similar_encontrado",
                "similares": similares_ids,
                "mensaje": "Se encontraron reclamos similares. ¿Desea adherirse?"
            }

        # Si no hay similares, se crea el reclamo
        new_id = self._get_next_id()
        nuevo_reclamo = Reclamo(
            id_reclamo=new_id,
            contenido=contenido, 
            usuario_creator_id=usuario_creator_id,
            departamento_id=depto_sugerido,
            estado=EstadoReclamo.PENDIENTE,
            palabras_clave=self.clasificador_servicio.extraer_palabras_clave(contenido),
            adjunto_url=adjunto,
            fecha_creacion=datetime.datetime.now()
        )
        
        self._reclamos_db[new_id] = nuevo_reclamo
        return {
            "status": "creado",
            "id_reclamo": new_id,
            "mensaje": "Reclamo creado" # RF 43
        }

    def adherirse_a_reclamo(self, reclamo_id: str, usuario_id: str) -> bool:
        # Permite a un usuario sumarse a un reclamo existente. Descarta el formulario de creación.
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo and usuario_id not in reclamo.adherentes_ids:
            # No permite adherirse a uno propio
            if reclamo.usuario_creador_id == usuario_id:
                return False
                
            reclamo.adherentes_ids.append(usuario_id)
            # Notifica al creador original.
            generar_notificacion(reclamo.usuario_creador_id, f"Un nuevo usuario se ha adherido a tu reclamo {reclamo_id}.")
            return True
        return False

    def actualizar_estado(self, reclamo_id: str, nuevo_estado: EstadoReclamo) -> bool:
        # El responsable del departamento edita el estado del reclamo.
        reclamo = self.get_reclamo(reclamo_id)
        if not reclamo:
            return False

        reclamo.estado = nuevo_estado

        # Aviso al usuario (Creador y Adherentes)
        usuarios_a_notificar = [reclamo.usuario_creador_id] + reclamo.adherentes_ids
        for uid in usuarios_a_notificar:
            generar_notificacion(uid, f"El reclamo {reclamo_id} ha cambiado a: {nuevo_estado.value}")
            
        return True

    def derivar_reclamo(self, reclamo_id: str, nuevo_depto_id: str) -> bool:
        # Opción exclusiva de Secretaría Técnica para mover un reclamo.
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.departamento_id = nuevo_depto_id
            return True
        return False

    # --- Métodos de Filtrado para ver reclamos ---
    def get_reclamos_por_departamento(self, depto_id: str) -> List[Reclamo]:
        return [r for r in self._reclamos_db.values() if r.departamento_id == depto_id]

    def get_reclamos_pendientes_filtrados(self, depto_id: Optional[str] = None) -> List[Reclamo]:
        query = [r for r in self._reclamos_db.values() if r.estado == EstadoReclamo.PENDIENTE]
        if depto_id:
            query = [r for r in query if r.departamento_id == depto_id]
        return query

    def get_mis_reclamos(self, usuario_id: str) -> List[Reclamo]:
        # Lista reclamos creados o adheridos por el usuario logueado.
        return [
            r for r in self._reclamos_db.values() 
            if r.usuario_creador_id == usuario_id or usuario_id in r.adherentes_ids
        ]