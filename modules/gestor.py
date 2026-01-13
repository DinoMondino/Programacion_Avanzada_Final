from typing import Dict, Any, Optional, List
from .reclamos import Reclamo, Clasificador, EstadoReclamo

class Gestor_Reclamos:
    def __init__(self, clasificador_servicio: Clasificador):
        self.clasificador_servicio = clasificador_servicio
        self._reclamos_db: Dict[str, Reclamo] = {}
        self._next_reclamo_id: int = 1
        
    def _get_next_id(self) -> str:
        """Genera un ID único para cada reclamo (R0001, R0002...)."""
        new_id = f"R{self._next_reclamo_id:04d}" 
        self._next_reclamo_id += 1
        return new_id

    def get_reclamo(self, reclamo_id: str) -> Optional[Reclamo]:
        """Retorna un objeto Reclamo según su ID."""
        return self._reclamos_db.get(reclamo_id)

    def crear_reclamo(self, contenido: str, adjunto: Optional[str], usuario_creator_id: str) -> Dict[str, Any]:
        """Crea un nuevo reclamo y verifica similares."""
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
        
        return {
            "mensaje": "Reclamo creado correctamente",
            "id_reclamo": nuevo_id,
            "similares": similares_ids,
            "status": "similar_encontrado" if similares_ids else "ok"
        }

    def get_mis_reclamos(self, usuario_id: str) -> List[Reclamo]:
        """Filtra reclamos creados por el usuario actual."""
        return [r for r in self._reclamos_db.values() if r.usuario_creator_id == usuario_id]

    def get_reclamos_por_departamento(self, depto_id: str) -> List[Reclamo]:
        """Retorna todos los reclamos de un departamento específico."""
        return [r for r in self._reclamos_db.values() if r.departamento_id == depto_id]

    def get_reclamos_pendientes_filtrados(self, depto_id: Optional[str] = None) -> List[Reclamo]:
        """
        Soluciona el error en app.py Ln 122.
        Lista reclamos PENDIENTES, opcionalmente filtrados por departamento.
        """
        pendientes = [r for r in self._reclamos_db.values() if r.estado == EstadoReclamo.PENDIENTE]
        if depto_id:
            return [r for r in pendientes if r.departamento_id == depto_id]
        return pendientes

    def gestionar_reclamo(self, reclamo_id: str, nuevo_estado: EstadoReclamo) -> bool:
        """Cambia el estado de un reclamo."""
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.estado = nuevo_estado
            return True
        return False
        
    def adherirse_a_reclamo(self, reclamo_id: str, usuario_id: str) -> bool:
        """
        Permite a un usuario sumarse a un reclamo existente.
        CORRECCIÓN: Se usa usuario_creator_id para coincidir con la clase Reclamo.
        """
        reclamo = self.get_reclamo(reclamo_id)
        # Verificamos que el usuario no sea el creador original
        if reclamo and usuario_id != reclamo.usuario_creator_id:
            if usuario_id not in reclamo.adherentes_ids:
                reclamo.adherentes_ids.append(usuario_id)
                return True
        return False