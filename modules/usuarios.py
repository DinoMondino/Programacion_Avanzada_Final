from enum import Enum
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod 
from .reclamos import Reclamo, EstadoReclamo, generar_notificacion
from .gestor import Gestor_Reclamos
from .departamentos import Analitica

""" Que hace el enum, porque usa abc usuario, que hace esto     def get_role_name(self) -> str:
        pass"""

"""                # En un sistema real, el usuario elegiría. Aquí simulamos la adhesión al primero.
                print(f"  > Simulación: Adhiriendo al primer reclamo similar: {similares[0].id}")
                self._gestor_reclamos.adherirse_a_reclamo(similares[0].id, self.id)
                print("[UsuarioFinal] Confirmación: Adherido a reclamo. (RF 43)")
                
QUe el usuario tenga la opción de a que reclamo similar aderirse, uno o más"""
"""que significa     def listar_reclamos_pendientes(self, depto_id: Optional[str] = None) -> List[Reclamo]:
        if not self._gestor_reclamos:
            print("[UsuarioFinal] Error: Servicio de gestor de reclamos no disponible.")
            return []
"""


class Claustro(Enum):
    ESTUDIANTE = "Estudiante"
    DOCENTE = "Docente"
    PAYS = "PAyS"

class RolAdmin(Enum):
    JEFE = "Jefe"
    SECRETARIO = "Secretario"

# Clase Base Usuario
class Usuario(ABC):
    def __init__(self, id_usuario: str, email: str, usuario: str,
                 contrasenia_hash: str, nombre: str, apellido: str):
        self.id: str = id_usuario
        self.email: str = email
        self.usuario: str = usuario 
        self.contrasenia_hash: str = contrasenia_hash
        self.nombre: str = nombre
        self.apellido: str = apellido
        
    @abstractmethod
    def get_role_name(self) -> str:
        pass
    
    def login(self, usuario: str, contrasenia: str, db_usuarios: Dict[str, Any]) -> bool:
        """ Simula el proceso de inicio de sesión y verifica la contraseña. """
        print(f"[{self.get_role_name()}] Intentando iniciar sesión como '{usuario}'...")
        return self.contrasenia_hash == contrasenia
        
# Clase de Usuario Final
class UsuarioFinal(Usuario):
    def __init__(self, id_usuario: str, email: str, usuario: str,
                 contrasenia_hash: str, nombre: str, apellido: str, claustro: Claustro,
                 gestor_servicio: Optional[Gestor_Reclamos] = None):
        super().__init__(id_usuario, email, usuario, contrasenia_hash, nombre, apellido)
        self.claustro: Claustro = claustro
        self._gestor_reclamos: Optional[Gestor_Reclamos] = gestor_servicio

    def get_role_name(self) -> str:
        return f"Usuario Final ({self.claustro.value})"

    @staticmethod
    def registro_usuario(db_usuarios: Dict[str, Usuario], 
                         nombre: str, apellido: str, email: str, 
                         usuario: str, claustro: Claustro, 
                         contrasenia: str, contrasenia_repetida: str) -> Optional[Dict[str, Any]]:
        # 1. Validar unicidad
        for j in db_usuarios.values():
            if j.email == email:
                print("[Registro] Error: El email ya ha sido registrado.")
                return None
            if j.usuario == usuario:
                print("[Registro] Error: El nombre de usuario ya ha sido registrado.")
                return None
        
        # 2. Validar contraseña
        if contrasenia != contrasenia_repetida:
            print("[Registro] Error: Las contraseñas no coinciden.")
            return None
            
        # 3. Crear nuevo usuario
        new_id = f"UF{len(db_usuarios) + 1:04d}"
        contrasenia_hash = contrasenia
        return {
            "id": new_id, "email": email, "usuario": usuario, 
            "contrasenia_hash": contrasenia_hash, "nombre": nombre, 
            "apellido": apellido, "claustro": claustro
        }
    
    def crear_reclamo(self, contenido: str, adjunto_url: Optional[str] = None):
        if not self._gestor_reclamos:
            print("[UsuarioFinal] Error: Servicio de gestor de reclamos no disponible.")
            return
            
        es_nuevo, mensaje, similares = self._gestor_reclamos.crear_reclamo(
            contenido, adjunto_url, self.id
        )
        
        if es_nuevo:
            print(f"[UsuarioFinal] Éxito: {mensaje}") # "Reclamo creado"
        else:
            print(f"[UsuarioFinal] Atención: {mensaje}") # "Reclamos similares encontrados"
            if similares:
                print("Reclamos Similares Sugeridos:")
                for i, r in enumerate(similares):
                    print(f"  {i+1}. {r}")

                # En un sistema real, el usuario elegiría. Aquí simulamos la adhesión al primero.
                print(f"  > Simulación: Adhiriendo al primer reclamo similar: {similares[0].id}")
                self._gestor_reclamos.adherirse_a_reclamo(similares[0].id, self.id)
                print("[UsuarioFinal] Confirmación: Adherido a reclamo. (RF 43)")

    def listar_reclamos_pendientes(self, depto_id: Optional[str] = None) -> List[Reclamo]:
        if not self._gestor_reclamos:
            print("[UsuarioFinal] Error: Servicio de gestor de reclamos no disponible.")
            return []
        # Si depto_id es None, retorna todos los pendientes del sistema
        reclamos = self._gestor_reclamos.get_reclamos_pendientes_filtrados(depto_id)
        
        print(f"[UsuarioFinal] Listando {len(reclamos)} reclamos pendientes (Filtro Depto: {depto_id or 'Todos'})")

        listado_info = []
        for r in reclamos:
            listado_info.append({
                "ID": r.id,
                "Estado": r.estado.value,
                "Fecha": r.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
                "Contenido": r.contenido[:50] + "...",
                "Departamento": r.departamento_id,
                "Adherentes": r.get_num_adherentes(),
                "Puede_Adherirse": self.id != r.usuario_creator_id and self.id not in r.adherentes_ids
            })
            
        return listado_info
        
    def ver_mis_reclamos(self) -> List[Reclamo]:
        if not self._gestor_reclamos:
            print("[UsuarioFinal] Error: Servicio de gestor de reclamos no disponible.")
            return []
            
        mis_reclamos = self._gestor_reclamos.get_mis_reclamos(self.id)
        
        print(f"[UsuarioFinal] Mostrando {len(mis_reclamos)} reclamos creados/adheridos.")
        return mis_reclamos


# Clases de Usuarios Administradores (Jefe y Secretario)
class UsuarioAdmin(Usuario, ABC):
    def __init__(self, id_usuario: str, email: str, usuario: str,
                 contrasenia_hash: str, nombre: str, apellido: str, 
                 gestor_servicio: Optional[Gestor_Reclamos] = None, 
                 analitica_servicio: Optional[Analitica] = None):
        super().__init__(id_usuario, email, usuario, contrasenia_hash, nombre, apellido)
        self._gestor_reclamos: Optional[Gestor_Reclamos] = gestor_servicio
        self._analitica: Optional[Analitica] = analitica_servicio
        
    @abstractmethod
    def get_departamento_id(self) -> str:
        pass

    def ver_analitica(self, departamento_id: str) -> Dict[str, Any]:
        # Un jefe solo puede ver su departamento. El secretario puede ver todos.
        if departamento_id != self.get_departamento_id() and self.get_role_name() == RolAdmin.JEFE.value:
             print(f"[{self.usuario}] Solo puede ver analítica del departamento ID: {self.get_departamento_id()}")
             return {}
        
        if self._analitica:
            print(f"[{self.usuario}] Viendo analítica para el depto ID: {departamento_id}")
            stats = self._analitica.get_estadisticas_generales(departamento_id)
            frecuencia = self._analitica.get_frecuencia_palabras(departamento_id)
            return {"estadisticas": stats, "frecuencia_palabras": frecuencia}
             
        print(f"[{self.usuario}] Error: Servicio de Analítica no disponible.")
        return {}


    def manejar_reclamos(self, departamento_id: str) -> List[Reclamo]:
        # Un jefe solo puede manejar su departamento. El secretario puede ver todos.
        if departamento_id != self.get_departamento_id() and self.get_role_name() == RolAdmin.JEFE.value:
             print(f"[{self.usuario}] Solo puede manejar reclamos de su departamento ID: {self.get_departamento_id()}")
             return []
             
        if self._gestor_reclamos:
            # Si es secretario y pide ALL, retorna todos. Si pide un depto específico, lo filtra.
            if departamento_id == "ALL":
                return self._gestor_reclamos.get_all_reclamos()
            else:
                return self._gestor_reclamos.get_reclamos_por_departamento(departamento_id)
        
        print(f"[{self.usuario}] Error: Servicio de gestor de reclamos no disponible.")
        return []

    def actualizar_estado_reclamo(self, reclamo_id: str, nuevo_estado: EstadoReclamo) -> bool:
        if not self._gestor_reclamos: return False
        
        reclamo = self._gestor_reclamos.get_reclamo(reclamo_id)
        if not reclamo: return False
        
        # Validación de permiso
        if self.get_role_name() == RolAdmin.JEFE.value and reclamo.departamento_id != self.get_departamento_id():
            print(f"[{self.usuario}] No tiene permiso para cambiar el estado del reclamo {reclamo_id} (Depto: {reclamo.departamento_id}).")
            return False
            
        return self._gestor_reclamos.actualizar_estado_reclamo(reclamo_id, nuevo_estado)

    def generar_reporte(self, departamento_id: str, formato: str = "HTML") -> str:
        if not self._analitica: 
            return "[Reporte] Error: Servicio de Analítica no disponible."
            
        datos = self.ver_analitica(departamento_id)
        if not datos:
            return "[Reporte] Error: No se pudieron obtener los datos de analítica."

        stats = datos["estadisticas"]
        frecuencia = datos["frecuencia_palabras"]

        if formato.upper() == "HTML":
            return self._analitica.generar_reporte_html(departamento_id, stats, frecuencia)
        elif formato.upper() == "PDF":
            # Simulación de PDF (el contenido es solo una cadena)
            return self._analitica.generar_reporte_pdf(departamento_id)
        else:
            return "[Reporte] Formato no soportado. Use 'HTML' o 'PDF'."

class JefeDepartamento(UsuarioAdmin):
    def __init__(self, id_usuario: str, email: str, usuario: str,
                 contrasenia_hash: str, nombre: str, apellido: str, 
                 departamento_id: str, gestor_servicio: Optional[Gestor_Reclamos] = None, 
                 analitica_servicio: Optional[Analitica] = None):
        super().__init__(id_usuario, email, usuario, contrasenia_hash, nombre, apellido, 
                         gestor_servicio, analitica_servicio)
        self._departamento_id = departamento_id
        
    def get_role_name(self) -> str:
        return RolAdmin.JEFE.value

    def get_departamento_id(self) -> str:
        return self._departamento_id


class SecretarioTecnico(UsuarioAdmin):
    def __init__(self, id_usuario: str, email: str, usuario: str,
                 contrasenia_hash: str, nombre: str, apellido: str, 
                 gestor_servicio: Optional[Gestor_Reclamos] = None, 
                 analitica_servicio: Optional[Analitica] = None):
        super().__init__(id_usuario, email, usuario, contrasenia_hash, nombre, apellido, 
                         gestor_servicio, analitica_servicio)

    def get_role_name(self) -> str:
        return RolAdmin.SECRETARIO.value

    def get_departamento_id(self) -> str:
        # El secretario no está ligado a un solo departamento, puede manejar todos.
        return "ALL" 

    def derivar_reclamo(self, reclamo_id: str, nuevo_depto_id: str) -> bool:
        """
        Permite al Secretario derivar un reclamo. (RF 60)
        """
        if not self._gestor_reclamos: return False
        return self._gestor_reclamos.derivar_reclamo(reclamo_id, nuevo_depto_id)