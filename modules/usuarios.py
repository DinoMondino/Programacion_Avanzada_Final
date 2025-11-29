from enum import Enum
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod 
from .reclamos import Reclamo, EstadoReclamo, generar_notificacion
from .gestor import Gestor_Reclamos
from .departamentos import Analitica 

# --- ENUMS ---
class Claustro(Enum):
    """Define el rol base de la comunidad universitaria."""
    ESTUDIANTE = "Estudiante"
    DOCENTE = "Docente"
    PAYS = "PAyS"

class RolAdmin(Enum):
    """Define el rol administrativo, si lo tiene."""
    NINGUNO = "Ninguno"
    JEFE = "Jefe de Departamento"
    SECRETARIO = "Secretario Técnico"

# --- CLASE BASE ---
class Usuario(ABC):
    """Clase abstracta base para todos los usuarios. Contiene atributos esenciales."""
    def __init__(self, id_usuario: str, email: str, usuario: str,
                 contrasenia_hash: str, nombre: str, apellido: str,
                 claustro: Claustro,
                 rol_admin: RolAdmin = RolAdmin.NINGUNO, 
                 departamento_id: Optional[str] = None,   
                 gestor_servicio: Optional[Gestor_Reclamos] = None, 
                 analitica_servicio: Optional[Analitica] = None):
        
        self.id: str = id_usuario
        self.email: str = email
        self.usuario: str = usuario
        self.contrasenia_hash: str = contrasenia_hash
        self.nombre: str = nombre
        self.apellido: str = apellido
        
        # Atributos de Claustro y Rol
        self.claustro: Claustro = claustro
        self.rol_admin: RolAdmin = rol_admin
        # Dpto. al que está asignado si es JEFE, o None si es Secretario o sin rol admin
        self.departamento_id: Optional[str] = departamento_id 
        
        # Inyección de dependencias (Servicios)
        self._gestor_reclamos = gestor_servicio
        self._analitica = analitica_servicio

    @abstractmethod
    def get_role_name(self) -> str:
        """Devuelve el nombre del rol más relevante para la UI."""
        pass
    
    @abstractmethod
    def get_alcance_gestion(self) -> str:
        """Define el alcance administrativo: 'ALL' (Secretario), Dpto ID (Jefe), o 'N/A'."""
        pass


# --- MIXIN: FUNCIONALIDADES DE USUARIO FINAL (CREACIÓN DE RECLAMOS) ---

# Deshabilitamos E1101 para que Pylint ignore los miembros que vienen de Usuario (self.id, self._gestor_reclamos)
class UsuarioFinal: # pylint: disable=E1101
    """
    Mixin que provee las funcionalidades de un usuario creador/adherente de reclamos 
    (RF 35, RF 36, RF 43).
    """
    
    # La clase que usa este Mixin DEBE heredar de Usuario y tener _gestor_reclamos
    def crear_reclamo(self: Usuario, contenido: str, adjunto: Optional[str]) -> Dict[str, Any]:
        """Crea un nuevo reclamo a través del gestor."""
        if not self._gestor_reclamos:
            print("[UsuarioFinal] Error: Servicio de gestor de reclamos no disponible.")
            return {"success": False, "message": "Gestor de reclamos no disponible."}
        
        return self._gestor_reclamos.crear_reclamo(contenido, adjunto, self.id)

    def adherirse_a_reclamo(self: Usuario, reclamo_id: str) -> bool:
        """Adhiere al usuario a un reclamo existente."""
        if not self._gestor_reclamos: return False
        return self._gestor_reclamos.adherirse_a_reclamo(reclamo_id, self.id)

    # El método que lista todos los pendientes para adhesión (RF 38)
    def listar_reclamos_pendientes_final(self: Usuario) -> List[Reclamo]:
        """Lista reclamos PENDIENTES a nivel global para posible adhesión."""
        if not self._gestor_reclamos: return []
        # El gestor lista globalmente si depto_id es None
        return self._gestor_reclamos.get_reclamos_pendientes_filtrados(depto_id=None) 
    
    # El método que lista los reclamos del usuario (RF 39)
    def ver_mis_reclamos(self: Usuario) -> List[Reclamo]:
        """Retorna los reclamos creados o adheridos por este usuario."""
        if not self._gestor_reclamos: return []
        return self._gestor_reclamos.get_mis_reclamos(self.id)


# --- MIXIN: FUNCIONALIDADES DE USUARIO ADMIN (GESTIÓN Y ANALÍTICA) ---

# Deshabilitamos E1101 para que Pylint ignore los miembros que vienen de Usuario 
class UsuarioAdmin: # pylint: disable=E1101
    
    # La clase que usa este Mixin DEBE heredar de Usuario y tener _gestor_reclamos y _analitica
    def _verificar_permiso_gestion(self: Usuario, reclamo_id: str) -> bool:
        """Verifica si el usuario tiene permiso (JEFE o SECRETARIO) y alcance sobre el reclamo."""
        alcance = self.get_alcance_gestion()
        
        if alcance == "N/A":
            print(f"[{self.get_role_name()}] ERROR de Permiso: No tiene rol administrativo.")
            return False
            
        if alcance != "ALL":
             # Es Jefe de Dpto. con alcance limitado. Debe verificar que el reclamo le pertenezca.
            reclamo = self._gestor_reclamos.get_reclamo(reclamo_id)
            if not reclamo or reclamo.departamento_id != alcance:
                print(f"[{self.get_role_name()}] ERROR de Permiso: Reclamo {reclamo_id} no pertenece a su Dpto. ({alcance}).")
                return False
        
        return True
        
    def gestionar_reclamo(self: Usuario, reclamo_id: str, nuevo_estado: EstadoReclamo, 
                          respuesta: Optional[str] = None) -> bool:
        """Permite al admin cambiar el estado y agregar una respuesta al reclamo."""
        if not self._gestor_reclamos: return False
        
        if not self._verificar_permiso_gestion(reclamo_id):
            return False

        # Ejecutar la gestión:
        return self._gestor_reclamos.gestionar_reclamo(reclamo_id, nuevo_estado, self.id, respuesta)
    
    def derivar_reclamo(self: Usuario, reclamo_id: str, nuevo_depto_id: str) -> bool:
        """Permite al admin cambiar el departamento asignado de un reclamo (Derivar)."""
        if not self._gestor_reclamos: return False

        # La restricción de alcance es la misma: el Jefe solo deriva si el reclamo está en su Dpto.
        if not self._verificar_permiso_gestion(reclamo_id):
            return False

        # Ejecutar la derivación
        return self._gestor_reclamos.derivar_reclamo(reclamo_id, nuevo_depto_id)
    
    def generar_reporte(self: Usuario, reporte_tipo: str = "analitica") -> Optional[str]:
        """Genera el reporte de analítica basado en el rol administrativo (RF 59)."""
        if not self._analitica: return None
        
        alcance = self.get_alcance_gestion()
        
        if alcance == "N/A":
            print(f"[{self.get_role_name()}] ERROR de Permiso: No puede generar reportes.")
            return None

        if alcance == "ALL":
            # Secretario: genera reporte global.
            print(f"[{self.get_role_name()}] Generando reporte global.")
            # Asumiendo que el mock de Analitica requiere el depto_id como None para global
            return self._analitica.generar_reporte_global(reporte_tipo) 
        else:
            # Jefe: genera reporte solo para su departamento.
            print(f"[{self.get_role_name()}] Generando reporte para Dpto. {alcance}.")
            return self._analitica.generar_reporte_departamento(alcance, reporte_tipo)
            
    def listar_reclamos_pendientes_admin(self: Usuario) -> List[Reclamo]:
        """Lista reclamos pendientes según el alcance administrativo (Jefe vs. Secretario) (RF 41, 60)."""
        alcance = self.get_alcance_gestion()
        
        if alcance == "N/A":
            return [] # No tiene acceso administrativo

        if not self._gestor_reclamos: return []
        
        if alcance == "ALL":
            # Secretario: lista todos los pendientes (depto_id=None)
            return self._gestor_reclamos.get_reclamos_pendientes_filtrados(depto_id=None)
        else:
            # Jefe de Dpto: lista solo los pendientes de su departamento
            return self._gestor_reclamos.get_reclamos_pendientes_filtrados(depto_id=alcance)

# --- CLASES CONCRETAS ---

class UsuarioBase(Usuario, UsuarioFinal):
    """
    Representa a cualquier usuario (Estudiante, Docente, PAyS) sin rol administrativo.
    Solo tiene funcionalidad de UsuarioFinal.
    """
    def __init__(self, id_usuario: str, email: str, usuario: str,
                 contrasenia_hash: str, nombre: str, apellido: str,
                 claustro: Claustro,
                 gestor_servicio: Optional[Gestor_Reclamos] = None, 
                 analitica_servicio: Optional[Analitica] = None):
        super().__init__(id_usuario, email, usuario, contrasenia_hash, nombre, apellido, 
                         claustro, RolAdmin.NINGUNO, None, gestor_servicio, analitica_servicio)

    # ALIAS para que las pruebas funcionen (listar_mis_reclamos -> ver_mis_reclamos)
    def listar_mis_reclamos(self) -> List[Reclamo]:
        """Alias para ver_mis_reclamos."""
        return self.ver_mis_reclamos()
        
    # ALIAS para que las pruebas funcionen (listar_reclamos_pendientes -> listar_reclamos_pendientes_final)
    def listar_reclamos_pendientes(self) -> List[Reclamo]:
        """Alias para listar_reclamos_pendientes_final."""
        return self.listar_reclamos_pendientes_final()
        
    def get_role_name(self) -> str:
        return self.claustro.value
        
    def get_alcance_gestion(self) -> str:
        return "N/A"

class JefeDepartamento(Usuario, UsuarioFinal, UsuarioAdmin):
    """
    Usuario con rol de Jefe de Departamento. 
    Hereda de UsuarioFinal y UsuarioAdmin con alcance departamental.
    """
    def __init__(self, id_usuario: str, email: str, usuario: str,
                 contrasenia_hash: str, nombre: str, apellido: str,
                 claustro: Claustro, # Se mantiene su Claustro base (ej. DOCENTE)
                 departamento_id: str, # Departamento que lidera
                 gestor_servicio: Optional[Gestor_Reclamos] = None, 
                 analitica_servicio: Optional[Analitica] = None):
        # El Jefe DEBE tener un departamento_id asignado.
        if not departamento_id:
             raise ValueError("JefeDepartamento debe tener un departamento_id asignado.")
             
        super().__init__(id_usuario, email, usuario, contrasenia_hash, nombre, apellido, 
                         claustro, RolAdmin.JEFE, departamento_id, gestor_servicio, analitica_servicio)

    # ALIAS para que las pruebas funcionen (manejar_reclamos -> listar_reclamos_pendientes_admin)
    def manejar_reclamos(self, departamento_id: Optional[str] = None) -> List[Reclamo]:
        """Alias para listar_reclamos_pendientes_admin (usado para listar reclamos del depto)."""
        # Nota: El Mixin ya usa el alcance correcto del jefe.
        return self.listar_reclamos_pendientes_admin()

    # ALIAS para que las pruebas funcionen (manejar_reclamos_pendientes -> listar_reclamos_pendientes_admin)
    def manejar_reclamos_pendientes(self: Usuario, departamento_id: Optional[str] = None) -> List[Reclamo]:
        """Alias para listar_reclamos_pendientes_admin."""
        return self.listar_reclamos_pendientes_admin()
        
    # ALIAS para que las pruebas funcionen (actualizar_estado_reclamo -> gestionar_reclamo)
    def actualizar_estado_reclamo(self: Usuario, reclamo_id: str, nuevo_estado: EstadoReclamo, 
                                  respuesta: Optional[str] = None) -> bool:
        """Alias para gestionar_reclamo."""
        return self.gestionar_reclamo(reclamo_id, nuevo_estado, respuesta)

    # ALIAS para que las pruebas funcionen (ver_analitica)
    def ver_analitica(self: Usuario, departamento_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Simula la obtención de estadísticas (Parte de RF 57)."""
        if not self._analitica or self.get_alcance_gestion() == "N/A":
             return None
        # Asumiendo que el mock de Analitica requiere el depto_id
        return self._analitica.get_estadisticas_generales(self.departamento_id)
        
    def get_role_name(self) -> str:
        # Prioriza el rol administrativo para la interfaz
        return f"{RolAdmin.JEFE.value} ({self.departamento_id})" 

    def get_alcance_gestion(self) -> str:
        # Alcance limitado a su departamento
        return self.departamento_id

class SecretarioTecnico(Usuario, UsuarioFinal, UsuarioAdmin):
    """
    Usuario con rol de Secretario Técnico. 
    Hereda de UsuarioFinal y UsuarioAdmin con alcance global.
    """
    def __init__(self, id_usuario: str, email: str, usuario: str,
                 contrasenia_hash: str, nombre: str, apellido: str,
                 claustro: Claustro, # Se mantiene su Claustro base (ej. PAYS o DOCENTE)
                 gestor_servicio: Optional[Gestor_Reclamos] = None, 
                 analitica_servicio: Optional[Analitica] = None):
        # El Secretario tiene Alcance ALL, por lo que el departamento_id es None.
        super().__init__(id_usuario, email, usuario, contrasenia_hash, nombre, apellido, 
                         claustro, RolAdmin.SECRETARIO, None, gestor_servicio, analitica_servicio)
                         
    # ALIAS para que las pruebas funcionen (manejar_reclamos_pendientes)
    def manejar_reclamos_pendientes(self: Usuario, departamento_id: Optional[str] = None) -> List[Reclamo]:
        """Alias para listar_reclamos_pendientes_admin con capacidad de filtrado."""
        if departamento_id:
            # Si el Secretario pasa un depto_id, se filtra (como en el test test_secretario_manejar_reclamos_filtrados)
            if not self._gestor_reclamos: return []
            return self._gestor_reclamos.get_reclamos_pendientes_filtrados(depto_id=departamento_id)
        # Si no se pasa, usa el alcance ALL del Mixin
        return self.listar_reclamos_pendientes_admin()

    # ALIAS para que las pruebas funcionen (actualizar_estado_reclamo -> gestionar_reclamo)
    def actualizar_estado_reclamo(self: Usuario, reclamo_id: str, nuevo_estado: EstadoReclamo, 
                                  respuesta: Optional[str] = None) -> bool:
        """Alias para gestionar_reclamo."""
        return self.gestionar_reclamo(reclamo_id, nuevo_estado, respuesta)
        
    # ALIAS para que las pruebas funcionen (ver_analitica)
    def ver_analitica(self: Usuario, departamento_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Simula la obtención de estadísticas (Parte de RF 57)."""
        if not self._analitica:
             return None
        # El secretario puede ver analítica de cualquier depto.
        depto_a_consultar = departamento_id if departamento_id else self.departamento_id
        # Asumiendo que el mock de Analitica requiere el depto_id
        return self._analitica.get_estadisticas_generales(depto_a_consultar)
        
    def get_role_name(self) -> str:
        # Prioriza el rol administrativo
        return RolAdmin.SECRETARIO.value

    def get_alcance_gestion(self) -> str:
        # Alcance global, representado por "ALL"
        return "ALL"