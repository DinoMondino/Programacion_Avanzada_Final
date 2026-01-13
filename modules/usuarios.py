from enum import Enum
from flask_sqlalchemy import SQLAlchemy

# Creamos una instancia local para definir los modelos sin depender de app.py
db = SQLAlchemy()

class Claustro(Enum):
    ESTUDIANTE = "Estudiante"
    DOCENTE = "Docente"
    PAYS = "PAyS"

class RolAdmin(Enum):
    NINGUNO = "Ninguno"
    JEFE = "Jefe de Departamento"
    SECRETARIO = "Secretario Técnico"

# Clase Base (Cumple con el ABC del UML)
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    nombre = db.Column(db.String(50))
    apellido = db.Column(db.String(50))
    claustro = db.Column(db.Enum(Claustro))
    rol_admin = db.Column(db.Enum(RolAdmin))
    departamento_id = db.Column(db.String(50), nullable=True)

    reclamos_creados = db.relationship('Reclamo', backref='autor', lazy=True)

    # Polimorfismo: esta columna le dice a SQLAlchemy qué clase usar al leer de la DB
    tipo_usuario = db.Column(db.String(50)) 
    __mapper_args__ = {
        'polymorphic_identity': 'usuario',
        'polymorphic_on': tipo_usuario
    }

# --- CLASES DEL UML ---

class UsuarioFinal(Usuario):
    """Corresponde al Alumno/Usuario común en el UML"""
    __mapper_args__ = { 'polymorphic_identity': 'final' }
    
    def ver_mis_reclamos(self):
        return self.reclamos_creados

class JefeDepartamento(Usuario):
    """Corresponde al Jefe en el UML"""
    __mapper_args__ = { 'polymorphic_identity': 'jefe' }

class SecretarioTecnico(Usuario):
    """Corresponde al Secretario en el UML"""
    __mapper_args__ = { 'polymorphic_identity': 'secretario' }
    def __init__(self, **kwargs):
        # Quitamos 'rol_admin' de kwargs si viniera de afuera para evitar el error
        kwargs.pop('rol_admin', None) 
        kwargs.pop('departamento_id', None)
        
        # Ahora llamamos al padre pasando los valores fijos
        super().__init__(
            rol_admin=RolAdmin.SECRETARIO, 
            departamento_id="ADMIN_GENERAL", 
            **kwargs
        )

    def listar_reclamos_pendientes_admin(self):
        # El secretario ve todos los reclamos en la DB
        return list(self._gestor_reclamos._reclamos_db.values())
    
    def gestionar_reclamo(self, reclamo_id, nuevo_estado):
        """Permite al Secretario cambiar el estado de cualquier reclamo."""
        return self._gestor_reclamos.gestionar_reclamo(reclamo_id, nuevo_estado)

    def derivar_reclamo(self, reclamo_id, nuevo_depto):
        return self._gestor_reclamos.derivar_reclamo(reclamo_id, nuevo_depto)