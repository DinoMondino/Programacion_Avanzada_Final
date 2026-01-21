from typing import Dict, Any, Optional, List
from modules.reclamos import Reclamo, Clasificador, EstadoReclamo
from modules.usuarios import Usuario

class Gestor_Reclamos:
    def __init__(self, db, clasificador_servicio: Clasificador):
        self.db = db
        self.clasificador_servicio = clasificador_servicio

    def get_reclamo(self, reclamo_id: int) -> Optional[Reclamo]:
        """Busca un reclamo por su ID numérico en la base de datos."""
        return Reclamo.query.get(reclamo_id)

    def crear_reclamo(self, contenido: str, adjunto: Optional[str], usuario_id: int) -> Dict[str, Any]:
        """RF 30, 31, 32: Crea un reclamo con clasificación automática y persistencia en DB."""
        
        # 1. Clasificación automática usando el servicio
        resultado_clasif = self.clasificador_servicio.clasificar(contenido)
        depto_id = resultado_clasif['departamento_id']
        
        # 2. Detección de similares (Simple por contenido parcial)
        # Si existe uno muy parecido, no creamos uno nuevo, sugerimos adherirse
        similar = Reclamo.query.filter(Reclamo.contenido.like(f"%{contenido[:15]}%")).first()
        
        if similar:
            self.adherirse_a_reclamo(similar.id, usuario_id)
            return {
                "status": "similar", 
                "mensaje": f"Detectamos un reclamo similar (# {similar.id}). Te hemos adherido automáticamente."
            }

        # 3. Creación del objeto persistente
        nuevo_rec = Reclamo(
            contenido=contenido,
            usuario_id=usuario_id,
            departamento_id=depto_id,
            estado='pendiente',
            adjunto_url=adjunto
        )
        
        try:
            self.db.session.add(nuevo_rec)
            self.db.session.commit()
            return {"status": "ok", "mensaje": "Reclamo creado y clasificado correctamente."}
        except Exception as e:
            self.db.session.rollback()
            return {"status": "error", "mensaje": f"Error al guardar: {str(e)}"}

    def gestionar_reclamo(self, reclamo_id: int, nuevo_estado: str) -> bool:
        """Cambia el estado del reclamo en la DB (Jefe/Secretario)."""
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.estado = nuevo_estado
            self.db.session.commit()
            return True
        return False

    def derivar_reclamo(self, reclamo_id: int, nuevo_depto_id: str) -> bool:
        """Permite corregir el departamento asignado (Secretario)."""
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.departamento_id = nuevo_depto_id
            self.db.session.commit()
            return True
        return False
        
    def adherirse_a_reclamo(self, reclamo_id: int, usuario_id: int) -> bool:
        """RF 43: Agrega un usuario a la lista de apoyos de un reclamo."""
        reclamo = self.get_reclamo(reclamo_id)
        usuario = Usuario.query.get(usuario_id)
        
        if reclamo and usuario:
            # Evitar que el creador se adhiera a su propio reclamo
            if reclamo.usuario_id == usuario_id:
                return False
            
            # Verificar si ya está adherido
            if usuario in reclamo.seguidores:
                return False
                
            reclamo.seguidores.append(usuario)
            self.db.session.commit()
            return True
        return False

    def obtener_todos_los_reclamos(self) -> List[Reclamo]:
        """Retorna todos los reclamos de la base de datos."""
        return Reclamo.query.order_by(Reclamo.fecha_creacion.desc()).all()