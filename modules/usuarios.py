from enum import Enum
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod 
import hashlib 

# Importaciones de módulos locales 
from .reclamos import Reclamo, EstadoReclamo
from .gestor import Gestor_Reclamos
from .departamentos import Analitica

# --- ENUMS ---
class Claustro(Enum):
    # Define el claustro del usuario final.
    ESTUDIANTE = "Estudiante"
    DOCENTE = "Docente"
    PAYS = "PAyS"

class RolAdmin(Enum):
    # Define los roles de gestión.
    NINGUNO = "Ninguno"
    JEFE = "Jefe de Departamento"
    SECRETARIO = "Secretario Técnico"

# --- CLASE BASE --
class Usuario(ABC):
    """Clase abstracta base. Contiene la lógica común de autenticación."""
    
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
        self.claustro: Claustro = claustro
        self.rol_admin: RolAdmin = rol_admin
        self.departamento_id: Optional[str] = departamento_id
        
        # Servicios externos
        self._gestor_reclamos = gestor_servicio
        self._analitica = analitica_servicio
        
    @staticmethod
    def _hash_password(contrasenia: str) -> str:
        # Simula el hasheo de seguridad.
        return hashlib.sha256(contrasenia.encode('utf-8')).hexdigest()

    def login(self, usuario: str, contrasenia: str) -> bool:
        # Verifica credenciales contra el hash almacenado.
        return self.usuario == usuario and self.contrasenia_hash == self._hash_password(contrasenia)
    
    @abstractmethod
    def get_role_name(self) -> str:
        pass

# --- MIXIN DE ADMINISTRACIÓN --> facilita la separación de responsabilidades entre los distintos roles---
class AdministradorMixin:
    # Proporciona capacidades de gestión a Jefes y Secretarios.
    
    def gestionar_reclamo(self, reclamo_id: str, nuevo_estado: EstadoReclamo) -> bool:
        # Permite editar el estado de un reclamo del departamento.
        if not self._gestor_reclamos: return False
        # Validación de seguridad: El Jefe solo gestiona su depto
        reclamo = self._gestor_reclamos.get_reclamo(reclamo_id)
        if self.rol_admin == RolAdmin.JEFE and reclamo.departamento_id != self.departamento_id:
            return False
            
        return self._gestor_reclamos.actualizar_estado(reclamo_id, nuevo_estado)

    def ver_analitica(self, depto_id: Optional[str] = None) -> Dict[str, Any]:
        # Obtiene estadísticas para el dashboard.
        target = depto_id if depto_id else self.departamento_id
        return self._analitica.get_estadisticas_generales(target)

    def generar_reporte(self, formato: str = "HTML") -> str:
        # Genera reporte en el formato PDF.
        if formato.upper() == "PDF":
            return self._analitica.generar_reporte_pdf(self.departamento_id)
        return self._analitica.generar_reporte_html(self.departamento_id)

# --- CLASES ESPECÍFICAS ---
class UsuarioAdmin(Usuario, AdministradorMixin):
    """Clase base para Jefes y Secretarios. Heredan de USUARIO y del MIXIN de ADMINISTRACIÓN."""
    def get_role_name(self) -> str:
        return self.rol_admin.value

class JefeDepartamento(UsuarioAdmin):
    def __init__(self, **kwargs):
        super().__init__(rol_admin=RolAdmin.JEFE, **kwargs)

class SecretarioTecnico(UsuarioAdmin):
    def __init__(self, **kwargs):
        # El Secretario tiene alcance global
        super().__init__(rol_admin=RolAdmin.SECRETARIO, departamento_id="ALL", **kwargs)

    def listar_reclamos_pendientes(self):
        return self.listar_reclamos_pendientes_admin()

    def derivar_reclamo(self, reclamo_id: str, nuevo_depto_id: str) -> bool:
        # Función exclusiva de Secretaría Técnica.
        return self._gestor_reclamos.derivar_reclamo(reclamo_id, nuevo_depto_id)

class UsuarioFinal(Usuario):
    """ Usuario común que registra, crea y adhiere a reclamos."""
    def crear_reclamo(self, contenido: str, adjunto_url: Optional[str] = None) -> str:
        # Flujo de creación que detecta reclamos similares.
        res = self._gestor_reclamos.crear_reclamo(contenido, adjunto_url, self.id)
        
        if res["status"] == "similar_encontrado":
            return f"Similares detectados: {res['similares']}. ¿Desea adherirse?"
        return f"Éxito: {res['mensaje']} (ID: {res.get('id_reclamo')})"

    def adherirse(self, reclamo_id: str) -> bool:
        # Adhesión manual a un reclamo del listado.
        return self._gestor_reclamos.adherirse_a_reclamo(reclamo_id, self.id)

    def get_role_name(self) -> str:
        return self.claustro.value
    
    def ver_mis_reclamos(self):
        """Devuelve la lista de reclamos del usuario."""
        if self.gestor_servicio:
            return self.gestor_servicio.obtener_reclamos_por_usuario(self.id_usuario)
        return []