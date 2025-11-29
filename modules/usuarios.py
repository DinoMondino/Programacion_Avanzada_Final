from enum import Enum
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod 
import datetime
import hashlib # Necesario para simular el hash de contraseñas

# Importaciones de módulos locales (asumiendo que están en el mismo nivel)
from .reclamos import Reclamo, EstadoReclamo, generar_notificacion
from .gestor import Gestor_Reclamos
from .departamentos import Analitica # Analitica debe estar definida en departamentos.py

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

# --- CLASE BASE --
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
        self.contrasenia_hash: str = contrasenia_hash # Asumimos que viene hasheada desde el registro/mock
        self.nombre: str = nombre
        self.apellido: str = apellido
        self.claustro: Claustro = claustro
        
        # Atributos de administración
        self.rol_admin: RolAdmin = rol_admin
        self.departamento_id: Optional[str] = departamento_id
        
        # Inyección de dependencias (Servicios)
        self._gestor_reclamos = gestor_servicio
        self._analitica = analitica_servicio
        
    @staticmethod
    def _hash_password(contrasenia: str) -> str:
        """Simula el hasheo de la contraseña."""
        # NOTA: En producción, usaríamos algo más seguro como bcrypt o scrypt.
        return hashlib.sha256(contrasenia.encode('utf-8')).hexdigest()

    @staticmethod
    def registro_usuario(db_users: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """
        Valida y prepara los datos para el registro de un nuevo UsuarioFinal.
        Retorna los datos del nuevo usuario, incluyendo el hash de contraseña, si es exitoso.
        """
        email = kwargs.get('email')
        usuario = kwargs.get('usuario')
        contrasenia = kwargs.get('contrasenia')
        contrasenia_repetida = kwargs.get('contrasenia_repetida')

        # 1. Validación de unicidad de usuario y email
        for user in db_users.values():
            if user.usuario == usuario or user.email == email:
                print(f"[ERROR] Usuario o email ya existen: {usuario}/{email}")
                return None

        # 2. Validación de contraseñas
        if not contrasenia or contrasenia != contrasenia_repetida:
            print("[ERROR] Las contraseñas no coinciden o están vacías.")
            return None
            
        # 3. Hash de la contraseña y preparación de datos
        contrasenia_hash = Usuario._hash_password(contrasenia)
        
        # Retorna el diccionario de datos listos para el constructor
        kwargs['contrasenia_hash'] = contrasenia_hash
        return kwargs

    def login(self, usuario: str, contrasenia: str, db_users: Dict[str, 'Usuario']) -> bool:
        """
        Verifica las credenciales de inicio de sesión.
        """
        user = db_users.get(usuario)
        if user and user.contrasenia_hash == self._hash_password(contrasenia):
            return True
        return False
        
    def get_departamento_id(self) -> Union[str, None]:
        """Retorna el ID del departamento asociado, o None/ALL."""
        return self.departamento_id
    
    @abstractmethod
    def get_role_name(self) -> str:
        """Método abstracto para obtener el nombre del rol específico."""
        pass

# --- MIXINS ---
class AdministradorMixin:
    """Proporciona la lógica de negocio a las clases Administrador (Jefe, Secretario)."""
    
    # RF 57: Actualizar estado de reclamo (Común para Jefe y Secretario)
    def gestionar_reclamo(self: 'UsuarioAdmin', reclamo_id: str, nuevo_estado: EstadoReclamo, 
                          respuesta: Optional[str] = None) -> bool:
        """Permite a un administrador actualizar el estado de un reclamo."""
        if not self._gestor_reclamos: 
            print("[ERROR] Gestor de reclamos no disponible.")
            return False
            
        reclamo = self._gestor_reclamos.get_reclamo(reclamo_id)
        if not reclamo:
            print(f"[ERROR] Reclamo {reclamo_id} no encontrado.")
            return False

        # Validación de permisos: 
        # Jefe solo puede modificar reclamos de su departamento.
        # Secretario puede modificar cualquiera.
        if self.rol_admin == RolAdmin.JEFE:
            if reclamo.departamento_id != self.departamento_id:
                print(f"[ERROR] Jefe no puede gestionar reclamo de {reclamo.departamento_id}.")
                return False
        
        # El cambio de estado lo maneja el gestor, que notifica al creador
        return self._gestor_reclamos.actualizar_estado(reclamo_id, nuevo_estado, respuesta)
    
    # RF 59: Generar reporte (Común para Jefe y Secretario)
    def generar_reporte(self: 'UsuarioAdmin', 
                        departamento_id: Optional[str] = None, 
                        formato: str = 'HTML') -> str:
        """Genera un reporte de reclamos en formato HTML o PDF."""
        if not self._analitica:
            return "Error: Servicio de Analítica no disponible."
            
        # Determina qué departamento reportar
        if self.rol_admin == RolAdmin.JEFE:
            depto_id = self.departamento_id # Jefe solo reporta el suyo
        elif departamento_id and self.rol_admin == RolAdmin.SECRETARIO:
            depto_id = departamento_id # Secretario puede elegir
        else:
            depto_id = "ALL" # Reporte general (por defecto para Secretario)
            
        formato = formato.upper()
        if formato == 'HTML':
            return self._analitica.generar_reporte_html(depto_id)
        elif formato == 'PDF':
            # Simulación: En un entorno real se llamaría a generar_reporte_pdf
            return self._analitica.generar_reporte_pdf(depto_id)
        else:
            return "Error: Formato de reporte no soportado."
            
    # RF 60: Derivar reclamo (Solo para Secretario Técnico, pero se incluye en el Mixin)
    def derivar_reclamo(self: 'SecretarioTecnico', reclamo_id: str, nuevo_depto_id: str) -> bool:
        """Permite al Secretario Técnico cambiar el departamento asignado a un reclamo."""
        # Se verifica el rol dentro del método, aunque el decorador de Flask también lo hará
        if self.rol_admin != RolAdmin.SECRETARIO:
             print("[ERROR] Solo el Secretario Técnico puede derivar reclamos.")
             return False
        
        if not self._gestor_reclamos: return False
        
        # La lógica real de derivación está en Gestor_Reclamos
        return self._gestor_reclamos.derivar_reclamo(reclamo_id, nuevo_depto_id)

    # RF 58: Ver analítica (Implementación general, la específica puede estar en Analitica)
    def ver_analitica(self: 'UsuarioAdmin', departamento_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Obtiene datos de analítica, ya sea del departamento propio o general."""
        if not self._analitica: return None
        
        depto_a_consultar = departamento_id if departamento_id else self.departamento_id
        
        # Asume que get_estadisticas_generales maneja 'ALL' o un ID específico
        return self._analitica.get_estadisticas_generales(depto_a_consultar)

# --- CLASES ADMINISTRADORAS ---

class UsuarioAdmin(Usuario, ABC):
    """Clase base para usuarios con roles de administración (Jefe, Secretario)."""
    # No necesita definir __init__ si usa los mismos argumentos que Usuario
    # Pero lo definimos para asegurar que se pasa el rol_admin correcto si fuera necesario.
    # En este caso, la clase hereda el __init__ de Usuario, pero lo dejamos
    # definido en sus subclases (JefeDepartamento, SecretarioTecnico) para claridad.
    
    def listar_reclamos_pendientes_admin(self: 'UsuarioAdmin', departamento_id: Optional[str] = None) -> List[Reclamo]:
        """Lista reclamos pendientes de acuerdo a su alcance (propio o global)."""
        if not self._gestor_reclamos: return []
        
        # Si es Jefe, filtra por su departamento_id
        if self.rol_admin == RolAdmin.JEFE:
            return self._gestor_reclamos.get_reclamos_pendientes_filtrados(self.departamento_id)
            
        # Si es Secretario o si se pide un depto específico, usa el filtro
        depto_id_filtro = departamento_id if departamento_id else None
        return self._gestor_reclamos.get_reclamos_pendientes_filtrados(depto_id_filtro)


class JefeDepartamento(UsuarioAdmin, AdministradorMixin):
    """Administrador que gestiona reclamos en su departamento."""
    
    # CORRECCIÓN DE ERROR: Debe tener __init__ y llamar a super()
    def __init__(self, id_usuario: str, email: str, usuario: str, contrasenia_hash: str, nombre: str, apellido: str,
                 claustro: Claustro, departamento_id: str, # Jefe SIEMPRE tiene un departamento_id
                 gestor_servicio: Optional[Gestor_Reclamos] = None, 
                 analitica_servicio: Optional[Analitica] = None):
        
        # Llama al constructor de la clase base (Usuario) con el rol_admin adecuado
        super().__init__(id_usuario, email, usuario, contrasenia_hash, nombre, apellido,
                         claustro,
                         rol_admin=RolAdmin.JEFE, # Pasa el rol específico
                         departamento_id=departamento_id,
                         gestor_servicio=gestor_servicio,
                         analitica_servicio=analitica_servicio)
        
    def get_role_name(self) -> str:
        return f"{self.rol_admin.value} ({self.departamento_id})"

class SecretarioTecnico(UsuarioAdmin, AdministradorMixin):
    """Administrador con visión y gestión de reclamos a nivel global."""
    
    # CORRECCIÓN DE ERROR: Debe tener __init__ y llamar a super()
    def __init__(self, id_usuario: str, email: str, usuario: str, contrasenia_hash: str, nombre: str, apellido: str,
                 claustro: Claustro, 
                 gestor_servicio: Optional[Gestor_Reclamos] = None, 
                 analitica_servicio: Optional[Analitica] = None):
        
        # Llama al constructor de la clase base (Usuario) con el rol_admin adecuado
        super().__init__(id_usuario, email, usuario, contrasenia_hash, nombre, apellido,
                         claustro,
                         rol_admin=RolAdmin.SECRETARIO, # Pasa el rol específico
                         departamento_id="ALL", # El Secretario tiene alcance total
                         gestor_servicio=gestor_servicio,
                         analitica_servicio=analitica_servicio)
                         
    def get_departamento_id(self) -> str:
        # Sobrescribe para que siempre devuelva "ALL" para el dashboard
        return "ALL"

    def get_role_name(self) -> str:
        return self.rol_admin.value

# --- CLASE USUARIO FINAL ---

class UsuarioFinal(Usuario):
    """
    Usuarios del sistema que interactúan creando o adhiriendo reclamos (Estudiantes, Docentes, PAYS sin rol admin).
    Hereda directamente de Usuario.
    """
    
    # CORRECCIÓN DE ERROR: Debe tener __init__ y llamar a super()
    def __init__(self, id_usuario: str, email: str, usuario: str,
                 contrasenia_hash: str, nombre: str, apellido: str,
                 claustro: Claustro, 
                 gestor_servicio: Optional[Gestor_Reclamos] = None):
        
        # Llama al constructor de la clase base (Usuario) con los valores por defecto de administración
        super().__init__(id_usuario, email, usuario,
                         contrasenia_hash, nombre, apellido,
                         claustro,
                         rol_admin=RolAdmin.NINGUNO, # Es UsuarioFinal
                         departamento_id=None,
                         gestor_servicio=gestor_servicio,
                         analitica_servicio=None) # No necesita Analitica
        
    # RF 35-43: Crear o adherir un reclamo
    def crear_reclamo(self, contenido: str, adjunto_url: Optional[str] = None) -> str:
        """
        Intenta crear un reclamo. El gestor decide si es nuevo o si se adhiere a uno existente.
        Retorna un mensaje de estado.
        """
        if not self._gestor_reclamos:
            return "Error: Servicio de reclamos no disponible."
            
        resultado = self._gestor_reclamos.crear_reclamo(contenido, adjunto_url, self.id)
        
        if resultado['adherido_a']:
            return f"Adherido a reclamo similar: {resultado['adherido_a']}"
        elif resultado['id_reclamo']:
            return f"Reclamo creado exitosamente: {resultado['id_reclamo']}"
        else:
            return "Error: No se pudo crear ni adherir el reclamo."

    # RF 33-34: Listar reclamos pendientes
    def listar_reclamos_pendientes(self, depto_id: Optional[str] = None) -> List[Reclamo]:
        """Lista todos los reclamos pendientes, opcionalmente filtrados por departamento."""
        if not self._gestor_reclamos: return []
        
        return self._gestor_reclamos.get_reclamos_pendientes_filtrados(depto_id)

    # RF 44-45: Ver mis reclamos
    def ver_mis_reclamos(self) -> List[Reclamo]:
        """Retorna todos los reclamos creados o adheridos por el usuario."""
        if not self._gestor_reclamos: return []
        
        return self._gestor_reclamos.get_mis_reclamos(self.id)

    def get_role_name(self) -> str:
        return self.claustro.value