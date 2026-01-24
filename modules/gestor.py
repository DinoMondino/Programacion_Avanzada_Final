from typing import Dict, Any, Optional, List
from modules.reclamos import Reclamo, Clasificador, EstadoReclamo
from modules.usuarios import Usuario, RolAdmin

class Gestor_Reclamos:
    def __init__(self, db, clasificador_servicio: Clasificador):
        self.db = db
        self.clasificador_servicio = clasificador_servicio

    # --- MÉTODOS DE BÚSQUEDA ---
    def get_reclamo(self, reclamo_id: int) -> Optional[Reclamo]: # Optional porque puede no existir
        return Reclamo.query.get(reclamo_id)

    def obtener_todos_los_reclamos(self) -> List[Reclamo]: # List porque retorna varios
        """Retorna la lista completa de reclamos (Para el Secretario)."""
        return Reclamo.query.all()

    def get_reclamos_por_departamento(self, depto_id: str) -> List[Reclamo]:
        """Retorna reclamos de un departamento específico (Para el Jefe)."""
        return Reclamo.query.filter_by(departamento_id=depto_id).all()

    def obtener_reclamos_para_usuario(self, usuario: Usuario) -> List[Reclamo]:
        # Decide qué reclamos mostrar según el rol del objeto usuario.
        if usuario.rol_admin == RolAdmin.SECRETARIO:
            return self.obtener_todos_los_reclamos()
        
        if usuario.rol_admin == RolAdmin.JEFE:
            return self.get_reclamos_por_departamento(usuario.departamento_id)
        
        # Si es usuario final, solo ve los que él creó
        return Reclamo.query.filter_by(usuario_id=usuario.id).all()


    # --- MÉTODOS DE ESCRITURA ---
    def crear_reclamo(self, contenido: str, adjunto: Optional[str], usuario_id: int) -> Dict[str, Any]:
        # Clasificación automática segun palabras clave
        resultado_clasif = self.clasificador_servicio.clasificar(contenido)
        depto_id = resultado_clasif['departamento_id']

        nuevo_reclamo = Reclamo(
            contenido=contenido,
            adjunto_url=adjunto,
            usuario_id=usuario_id,
            departamento_id=depto_id,
            estado=EstadoReclamo.PENDIENTE.value
        )
    
        self.db.session.add(nuevo_reclamo)
        self.db.session.commit() # Confirma los cambios en la base de datos
        return {"status": "creado", "reclamo_id": nuevo_reclamo.id}

    def gestionar_estado_reclamo(self, reclamo_id: int, nuevo_estado: str, tiempo: Optional[int] = None) -> bool:
    reclamo = self.get_reclamo(reclamo_id)
    if not reclamo:
        return False

    # REQUERIMIENTO 2024: Validación de 1 a 15 días al pasar a 'en proceso' 
    if nuevo_estado == EstadoReclamo.EN_PROCESO.value:
        if tiempo is None or not (1 <= tiempo <= 15):
            return False  # Rechaza el cambio si no hay tiempo o está fuera de rango
        reclamo.tiempo_estimado = tiempo

    # REQUERIMIENTO 2024: Registrar tiempo final al pasar a 'resuelto' 
    if nuevo_estado == EstadoReclamo.RESUELTO.value:
        # Si el reclamo se resuelve, el tiempo de resolución para la mediana 
        # será el tiempo estimado que se cumplió (o podrías calcular la diferencia de fechas)
        reclamo.tiempo_resolucion = reclamo.tiempo_estimado or 0

    if nuevo_estado in [e.value for e in EstadoReclamo]:
        reclamo.estado = nuevo_estado
        self.db.session.commit()
        return True
        
    return False

    def derivar_reclamo(self, reclamo_id: int, nuevo_depto_id: str) -> bool:
        # Permite corregir el departamento asignado.
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.departamento_id = nuevo_depto_id
            self.db.session.commit()
            return True
        return False
        
    def adherirse_a_reclamo(self, reclamo_id: int, usuario_id: int) -> bool:
        # Agrega un usuario a la lista de seguidores de un reclamo.
        reclamo = self.get_reclamo(reclamo_id)
        usuario = Usuario.query.get(usuario_id)
        
        if reclamo and usuario:
            if reclamo.usuario_id == usuario_id or usuario in reclamo.seguidores:
                return False # No puede adherirse a su propio reclamo o si ya está adherido
                
            reclamo.seguidores.append(usuario)
            self.db.session.commit()
            return True
        return False