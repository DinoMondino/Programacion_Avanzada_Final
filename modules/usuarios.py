from enum import Enum
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy() # Instancia de la base de datos

# Se definen los enumerados para Claustro y RolAdmin
class Claustro(Enum):
    ESTUDIANTE = "Estudiante"
    DOCENTE = "Docente"
    PAYS = "PAyS"

class RolAdmin(Enum):
    FINAL = "FINAL"
    JEFE = "JEFE"
    SECRETARIO = "SECRETARIO"
    NINGUNO = "NINGUNO"

# Clase Base. Al heredar db.Model, SQLAlchemy sabe que esta clase se debe transformar en una tabla para la base de datos.
class Usuario(db.Model):
    __tablename__ = 'usuarios' # Nombre de la tabla en la base de datos, seguido de los atributos/columnas
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    nombre = db.Column(db.String(50))
    apellido = db.Column(db.String(50))
    claustro = db.Column(db.Enum(Claustro))
    rol_admin = db.Column(db.Enum(RolAdmin))
    # Puede ser nulo para usuarios finales (estudiantes)
    departamento_id = db.Column(db.String(50), nullable=True)
    # Relación uno a muchos con Reclamo
    reclamos_creados = db.relationship('Reclamo', backref='autor', lazy=True)
    # Columna para el tipo de usuario (polimorfismo), pueden ser 'final', 'jefe', 'secretario'
    tipo_usuario = db.Column(db.String(50))
    __mapper_args__ = {
        'polymorphic_identity': 'usuario',
        'polymorphic_on': tipo_usuario
    }

class UsuarioFinal(Usuario): # Corresponde al Alumno/Usuario común, hereda de Usuario
    
    __mapper_args__ = { 'polymorphic_identity': 'final' } # Lo identifica como UsuarioFinal en la base de datos
    
    def ver_mis_reclamos(self):
        return self.reclamos_creados

class JefeDepartamento(Usuario): # Hereda de Usuario, incluido el inicializador.
    
    __mapper_args__ = { 'polymorphic_identity': 'jefe' }

    # Su funcionamiento está en cómo el Gestor filtra la información usando el atributo departamento_id.

class SecretarioTecnico(Usuario):
    __mapper_args__ = { 'polymorphic_identity': 'secretario' }
    def __init__(self, **kwargs):
        kwargs.pop('rol_admin', None) 
        kwargs.pop('departamento_id', None)
        
        # Ahora llamamos al padre pasando los valores fijos para evitar inconsistencias
        super().__init__(
            rol_admin=RolAdmin.SECRETARIO, 
            departamento_id="ADMIN_GENERAL", 
            **kwargs
        )

        # Tiene el departamento fijo "ADMIN_GENERAL" y rol_admin fijo "SECRETARIO"
