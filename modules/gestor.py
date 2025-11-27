from typing import Dict, Any, Optional, List
from .reclamos import Reclamo, Clasificador, EstadoReclamo, generar_notificacion

class Gestor_Reclamos:
    def __init__(self, clasificador_servicio: Clasificador):
        self.clasificador_servicio: Clasificador = clasificador_servicio
        # base de datos de reclamos
        self._reclamos_db: Dict[str, Reclamo] = {}
        self._next_reclamo_id: int = 1
        
    def _get_next_id(self) -> str:
        """Genera el siguiente ID secuencial para un reclamo."""
        new_id = f"R{self._next_reclamo_id:04d}"
        self._next_reclamo_id += 1
        return new_id

    def crear_reclamo(self, contenido: str, adjunto: Optional[str], usuario_creator_id: str) -> Dict[str, Any]:
        # 1. Clasificar el reclamo
        clasificacion = self.clasificador_servicio.clasificar(contenido)
        depto_sugerido = clasificacion["departamento_id"]
        similares_ids = clasificacion["reclamos_similares_ids"]
        
        # 2. Verificar reclamos similares
        similares = []
        if similares_ids:
            for rid in similares_ids:
                reclamo = self.get_reclamo(rid)
                if reclamo:
                    similares.append(reclamo)

        if similares:
            print(f"[Gestor] Se encontraron reclamos similares. Sugerimos adhesión: {[r.id for r in similares]}")
            return {"creado": False, "mensaje": "Similares encontrados.", "similares": similares}

        # 3. Crear nuevo reclamo
        new_id = self._get_next_id()
        palabras_clave = self.clasificador_servicio.extraer_palabras_clave(contenido)

        nuevo_reclamo = Reclamo(
            id_reclamo=new_id, 
            contenido=contenido,
            usuario_creator_id=usuario_creator_id,
            departamento_id=depto_sugerido,
            estado=EstadoReclamo.PENDIENTE,
            adjunto=adjunto,
            palabras_clave=palabras_clave
        )
        self._reclamos_db[new_id] = nuevo_reclamo
        print(f"[Gestor] Reclamo nuevo creado: {new_id}, asignado a {depto_sugerido}")
        return {"creado": True, "mensaje": "Reclamo creado.", "similares": None}


    def get_reclamo(self, reclamo_id: str) -> Optional[Reclamo]:
        # Obtiene un reclamo por su ID
        return self._reclamos_db.get(reclamo_id)

    def adherirse_a_reclamo(self, reclamo_id: str, usuario_id: str) -> bool:
        reclamo = self.get_reclamo(reclamo_id)
        
        if not reclamo:
            return False, f"Error: Reclamo {reclamo_id} no encontrado."

        if usuario_id == reclamo.usuario_creator_id:
            return False, "Error: El usuario ya es el creador del reclamo."
            
        if usuario_id in reclamo.adherentes_ids:
            return False, "Error: El usuario ya está adherido a este reclamo."
            
        # Realizar adhesión
        reclamo.adherentes_ids.append(usuario_id)
        
        mensaje = f"Te has adherido al reclamo {reclamo_id}: '{reclamo.contenido[:20]}...'"
        generar_notificacion(usuario_id, mensaje)
        
        return True, "Adhesión exitosa."


    def actualizar_estado_reclamo(self, reclamo_id: str, nuevo_estado: EstadoReclamo) -> bool:
        reclamo = self.get_reclamo(reclamo_id)
        if not reclamo:
            return False

        if reclamo.estado == nuevo_estado:
            return True
            
        reclamo.estado = nuevo_estado
        
        # Notifica al creador y a todos los adherentes
        usuarios_a_notificar = set([reclamo.usuario_creator_id] + reclamo.adherentes_ids)
        
        for i in usuarios_a_notificar:
            mensaje = f"El estado de tu reclamo {reclamo_id} ha cambiado a: {nuevo_estado.value}."
            generar_notificacion(i, mensaje)
            
        print(f"[Reclamo {reclamo_id}] Estado actualizado a {nuevo_estado.value}. Notificaciones enviadas.")
        return True

    def get_reclamos_por_departamento(self, depto_id: str) -> List[Reclamo]:
        # Retorna todos los reclamos asociados a un departamento
        return [r for r in self._reclamos_db.values() if r.departamento_id == depto_id]

    def get_reclamos_pendientes_filtrados(self, depto_id: Optional[str] = None) -> List[Reclamo]:
        # Retorna reclamos PENDIENTES, opcionalmente filtrados por departamento
        reclamos_pendientes = [
            r for r in self._reclamos_db.values() 
            if r.estado == EstadoReclamo.PENDIENTE
        ]
        
        if depto_id:
            return [r for r in reclamos_pendientes if r.departamento_id == depto_id]
        
        return reclamos_pendientes

    def get_mis_reclamos(self, usuario_id: str) -> List[Reclamo]:
        # Retorna los reclamos creados o adheridos por un usuario.
        mis_reclamos = [
            r for r in self._reclamos_db.values() 
            if r.usuario_creator_id == usuario_id or usuario_id in r.adherentes_ids
        ]
        return mis_reclamos

    def derivar_reclamo(self, reclamo_id: str, nuevo_depto_id: str) -> bool:
        # Permite derivar un reclamo a otro departamento.
        reclamo = self.get_reclamo(reclamo_id)
        if not reclamo:
            return False

        print(f"[Gestor] Derivando reclamo {reclamo_id} de {reclamo.departamento_id} a {nuevo_depto_id}")
        reclamo.departamento_id = nuevo_depto_id

        return True