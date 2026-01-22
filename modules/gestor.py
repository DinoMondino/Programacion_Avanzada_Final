from typing import Dict, Any, Optional, List
from modules.reclamos import Reclamo, Clasificador, EstadoReclamo
from modules.usuarios import Usuario, RolAdmin

class Gestor_Reclamos:
    def __init__(self, db, clasificador_servicio: Clasificador):
        self.db = db
        self.clasificador_servicio = clasificador_servicio

    # --- MÉTODOS DE BÚSQUEDA (LECTURA) ---

    def get_reclamo(self, reclamo_id: int) -> Optional[Reclamo]:
        """Busca un reclamo por su ID numérico."""
        return Reclamo.query.get(reclamo_id)

    def obtener_todos_los_reclamos(self) -> List[Reclamo]:
        """Retorna la lista completa de reclamos (Para el Secretario)."""
        return Reclamo.query.all()

    def get_reclamos_por_departamento(self, depto_id: str) -> List[Reclamo]:
        """Retorna reclamos de un departamento específico (Para el Jefe)."""
        return Reclamo.query.filter_by(departamento_id=depto_id).all()

    def obtener_reclamos_para_usuario(self, usuario: Usuario) -> List[Reclamo]:
        """
        MÉTODO CENTRALIZADO (Refactorización de SecretarioTecnico):
        Decide qué reclamos mostrar según el rol del objeto usuario.
        """
        if usuario.rol_admin == RolAdmin.SECRETARIO:
            return self.obtener_todos_los_reclamos()
        
        if usuario.rol_admin == RolAdmin.JEFE:
            return self.get_reclamos_por_departamento(usuario.departamento_id)
        
        # Si es usuario final, solo ve los que él creó
        return Reclamo.query.filter_by(usuario_id=usuario.id).all()


    # --- MÉTODOS DE ACCIÓN (ESCRITURA) ---

    def crear_reclamo(self, contenido: str, adjunto: Optional[str], usuario_id: int) -> Dict[str, Any]:
        """Crea un reclamo con clasificación automática y persistencia."""
        
        # Clasificación automática
        resultado_clasif = self.clasificador_servicio.clasificar(contenido)
        depto_id = resultado_clasif['departamento_id']
        
        # ELIMINAMOS O COMENTAMOS la lógica de adhesión automática que tenías aquí
        # para que el control pase al usuario en el frontend.

        nuevo_reclamo = Reclamo(
            contenido=contenido,
            adjunto_url=adjunto,
            usuario_id=usuario_id,
            departamento_id=depto_id,
            estado=EstadoReclamo.PENDIENTE.value
        )
        
        self.db.session.add(nuevo_reclamo)
        self.db.session.commit()
        return {"status": "creado", "reclamo_id": nuevo_reclamo.id}

    def gestionar_estado_reclamo(self, reclamo_id: int, nuevo_estado: str) -> bool:
        """Cambia el estado del reclamo (Responsabilidad del Gestor, no del Secretario)."""
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            # Validamos que el estado sea un valor del Enum
            if nuevo_estado in [e.value for e in EstadoReclamo]:
                reclamo.estado = nuevo_estado
                self.db.session.commit()
                return True
        return False

    def derivar_reclamo(self, reclamo_id: int, nuevo_depto_id: str) -> bool:
        """Permite corregir el departamento asignado (Lógica administrativa)."""
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.departamento_id = nuevo_depto_id
            self.db.session.commit()
            return True
        return False
        
    def adherirse_a_reclamo(self, reclamo_id: int, usuario_id: int) -> bool:
        """Agrega un usuario a la lista de seguidores de un reclamo."""
        reclamo = self.get_reclamo(reclamo_id)
        usuario = Usuario.query.get(usuario_id)
        
        if reclamo and usuario:
            if reclamo.usuario_id == usuario_id or usuario in reclamo.seguidores:
                return False
                
            reclamo.seguidores.append(usuario)
            self.db.session.commit()
            return True
        return False