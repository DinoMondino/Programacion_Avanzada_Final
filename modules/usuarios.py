from enum import Enum
from typing import Optional
from abc import ABC
from modules.reclamos import EstadoReclamo, Reclamo

class Claustro(Enum):
    ESTUDIANTE = "Estudiante"
    DOCENTE = "Docente"
    PAYS = "PAyS"

class RolAdmin(Enum):
    NINGUNO = "Ninguno"
    JEFE = "Jefe de Departamento"
    SECRETARIO = "Secretario Técnico"

class Usuario(ABC):
    def __init__(self, id_usuario, email, usuario, contrasenia_hash, nombre, apellido, claustro, 
                 rol_admin=RolAdmin.NINGUNO, departamento_id=None, gestor_servicio=None, analitica_servicio=None):
        self.id = id_usuario
        self.nombre = nombre
        self.apellido = apellido
        self.claustro = claustro
        self.rol_admin = rol_admin
        self.departamento_id = departamento_id
        self._gestor_reclamos = gestor_servicio
        self._analitica = analitica_servicio

class UsuarioFinal(Usuario):
    """ Usuario común que registra, crea y adhiere a reclamos."""
    
    def crear_reclamo(self, contenido: str, adjunto_url: Optional[str] = None) -> str:
        res = self._gestor_reclamos.crear_reclamo(contenido, adjunto_url, self.id)
    
        if res.get('status') == 'similar_encontrado':
          # Cambiamos 'similares' por 'adherido_a' que es lo que devuelve tu gestor
            id_similar = res.get('adherido_a')
            return f"Se encontró un reclamo similar ({id_similar}). Se recomienda adherirse."

        return res.get('mensaje', 'Reclamo procesado')
    def adherirse(self, reclamo_id: str) -> bool:
        """Permite al usuario sumarse a un reclamo existente."""
        return self._gestor_reclamos.adherirse_a_reclamo(reclamo_id, self.id)

    def ver_mis_reclamos(self):
        """Retorna los reclamos creados por este usuario."""
        return [r for r in self._gestor_reclamos._reclamos_db.values() if r.usuario_creator_id == self.id]
    
class JefeDepartamento(Usuario):
    def __init__(self, **kwargs):
        super().__init__(rol_admin=RolAdmin.JEFE, **kwargs)

    def gestionar_reclamo(self, reclamo_id, nuevo_estado):
        reclamo = self._gestor_reclamos.get_reclamo(reclamo_id)
        # Protección contra NoneType
        if not reclamo: return False
        return self._gestor_reclamos.gestionar_reclamo(reclamo_id, nuevo_estado)

    def listar_reclamos_pendientes_admin(self):
        # Filtra solo los de su departamento
        return [r for r in self._gestor_reclamos._reclamos_db.values() if r.departamento_id == self.departamento_id]

class SecretarioTecnico(Usuario):
    def __init__(self, **kwargs):
        super().__init__(rol_admin=RolAdmin.SECRETARIO, departamento_id="ALL", **kwargs)

    def listar_reclamos_pendientes_admin(self):
        # El secretario ve todos los reclamos en la DB
        return list(self._gestor_reclamos._reclamos_db.values())
    
    def gestionar_reclamo(self, reclamo_id, nuevo_estado):
        """Permite al Secretario cambiar el estado de cualquier reclamo."""
        return self._gestor_reclamos.gestionar_reclamo(reclamo_id, nuevo_estado)

    def derivar_reclamo(self, reclamo_id, nuevo_depto):
        return self._gestor_reclamos.derivar_reclamo(reclamo_id, nuevo_depto)