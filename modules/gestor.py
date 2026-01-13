from typing import Dict, Any, Optional, List
from .reclamos import Reclamo, Clasificador, EstadoReclamo
class Gestor_Reclamos:
    def __init__(self, clasificador_servicio: Clasificador):
        self.clasificador_servicio = clasificador_servicio
        self._reclamos_db: Dict[str, Reclamo] = {}
        self._next_reclamo_id: int = 1
        
    def _get_next_id(self) -> str:
        # Ajustado a R0001 para coincidir con los tests
        new_id = f"R{self._next_reclamo_id:04d}" 
        self._next_reclamo_id += 1
        return new_id

    def get_reclamo(self, reclamo_id: str) -> Optional[Reclamo]:
        return self._reclamos_db.get(reclamo_id)

    def crear_reclamo(self, contenido: str, adjunto: Optional[str], usuario_creator_id: str) -> Dict[str, Any]:
        similares_ids = self.clasificador_servicio.encontrar_similares(contenido, self._reclamos_db)
        clasificacion = self.clasificador_servicio.clasificar(contenido)
        
        nuevo_id = self._get_next_id()
        nuevo_rec = Reclamo(
            id_reclamo=nuevo_id,
            contenido=contenido,
            usuario_creator_id=usuario_creator_id,
            departamento_id=clasificacion["departamento_id"],
            estado=EstadoReclamo.PENDIENTE,
            adjunto_url=adjunto
        )
        self._reclamos_db[nuevo_id] = nuevo_rec
        
        # Estructura que esperan los tests
        return {
            "mensaje": "Éxito: Reclamo creado",
            "id_reclamo": nuevo_id,
            "adherido_a": similares_ids[0] if similares_ids else None,
            "status": "similar_encontrado" if similares_ids else "ok"
        }

    def obtener_reclamos_por_usuario(self, usuario_id: str) -> List[Reclamo]:
        return [r for r in self._reclamos_db.values() if r.usuario_creator_id == usuario_id]

    def get_reclamos_por_departamento(self, depto_id: str) -> List[Reclamo]:
        return [r for r in self._reclamos_db.values() if r.departamento_id == depto_id]

    def gestionar_reclamo(self, reclamo_id: str, nuevo_estado: EstadoReclamo) -> bool:
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.estado = nuevo_estado
            return True
        return False
        
    def adherirse_a_reclamo(self, reclamo_id: str, usuario_id: str) -> bool:
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo and usuario_id != reclamo.usuario_creador_id:
            if usuario_id not in reclamo.adherentes_ids:
                reclamo.adherentes_ids.append(usuario_id)
                return True
        return False