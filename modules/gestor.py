from typing import Dict, Any, Optional, List
from .reclamos import Reclamo, Clasificador, EstadoReclamo

class Gestor_Reclamos:
    def __init__(self, db, clasificador):
        self.db = db
        self.clasificador = clasificador
        self._next_reclamo_id: int = 1
        self._reclamos_db: Dict[str, Reclamo] = {}
        
    def _get_next_id(self) -> str:
        """Genera IDs únicos (R0001, R0002...)."""
        new_id = f"R{self._next_reclamo_id:04d}" 
        self._next_reclamo_id += 1
        return new_id

    def get_reclamo(self, reclamo_id: str) -> Optional[Reclamo]:
        """Busca un reclamo por su ID."""
        return self._reclamos_db.get(reclamo_id)

    def crear_reclamo(self, contenido, adjunto, usuario_id):
        depto = self.clasificador.clasificar(contenido)
        # Búsqueda de similares en la DB real
        similares = Reclamo.query.filter(Reclamo.contenido.contains(contenido[:20])).first()
        
        if similares:
            # Lógica de adhesión automática
            return {"mensaje": "Reclamo similar detectado, te hemos adherido.", "status": "similar"}
            
        nuevo = Reclamo(contenido=contenido, adjunto_url=adjunto, 
                        usuario_id=usuario_id, departamento_id=depto)
        self.db.session.add(nuevo)
        self.db.session.commit()
        return {"mensaje": "Reclamo creado con éxito.", "status": "ok"}

    # --- FUNCIONES DE FILTRADO (Recuperadas y Corregidas) ---

    def get_mis_reclamos(self, usuario_id: str) -> List[Reclamo]:
        """RF 41: Filtra reclamos creados por el usuario actual."""
        return [r for r in self._reclamos_db.values() if r.usuario_creator_id == usuario_id]

    def get_reclamos_por_departamento(self, depto_id: str) -> List[Reclamo]:
        """RF 55: Retorna todos los reclamos asignados a un departamento."""
        return [r for r in self._reclamos_db.values() if r.departamento_id == depto_id]

    def get_reclamos_pendientes_filtrados(self, depto_id: Optional[str] = None) -> List[Reclamo]:
        """RF 33: Lista reclamos PENDIENTES, opcionalmente por departamento."""
        pendientes = [r for r in self._reclamos_db.values() if r.estado == EstadoReclamo.PENDIENTE]
        if depto_id:
            return [r for r in pendientes if r.departamento_id == depto_id]
        return pendientes

    # --- FUNCIONES DE GESTIÓN ---

    def gestionar_reclamo(self, reclamo_id: str, nuevo_estado: EstadoReclamo) -> bool:
        """Cambia el estado de un reclamo (Jefe/Secretario)."""
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.estado = nuevo_estado
            return True
        return False

    def derivar_reclamo(self, reclamo_id: str, nuevo_depto_id: str) -> bool:
        """Permite al Secretario corregir el departamento asignado."""
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.departamento_id = nuevo_depto_id
            return True
        return False
        
    def adherirse_a_reclamo(self, reclamo_id: str, usuario_id: str) -> bool:
        """RF 43: Permite a un usuario sumarse a un reclamo existente."""
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo and usuario_id != reclamo.usuario_creator_id:
            if usuario_id not in reclamo.adherentes_ids:
                reclamo.adherentes_ids.append(usuario_id)
                return True
        return False