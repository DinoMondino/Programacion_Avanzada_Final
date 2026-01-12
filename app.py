from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, make_response
from functools import wraps
import io
import datetime

# Importaciones de tus módulos locales (ajustar según tu estructura de carpetas)
from modules.usuarios import (
    UsuarioFinal, JefeDepartamento, SecretarioTecnico, 
    Claustro, RolAdmin, EstadoReclamo, Usuario
)
from modules.reclamos import Clasificador
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica

app = Flask(__name__)
app.secret_key = 'super_secreto_uner' 

# --- Inicialización de Servicios ---
STOPWORDS = ["el", "la", "los", "las", "un", "una", "y", "o", "de", "a", "en", "es", "para", "que"]
clasificador = Clasificador(stopwords=STOPWORDS)
gestor_reclamos = Gestor_Reclamos(clasificador_servicio=clasificador)
analitica_servicio = Analitica(gestor_servicio=gestor_reclamos)

_DB_USERS = {}
_DB_DEPTOS = {
    "D_INFRAESTRUCTURA": "Infraestructura y Mantenimiento",
    "D_FINANZAS": "Tesorería y Finanzas",
    "D_SECRETARIA": "Secretaría Técnica / Alumnado",
    "D_INFORMATICA": "Soporte Informático"
}

# --- Decorador de Autenticación ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Por favor, inicia sesión.", "warning")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rutas de Autenticación ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', method=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = _DB_USERS.get(username)
    # Usamos el método de la clase Usuario para verificar
    if user and user.login(username, password):
        session['user_id'] = user.id
        session['username'] = user.usuario
        
        if user.rol_admin != RolAdmin.NINGUNO:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_menu'))
    
    flash("Credenciales inválidas", "error")
    return redirect(url_for('index'))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register_post', methods=['POST'])
def register_post():
    # RF 108: Registro de Usuario Final
    data = request.form
    if data['contrasenia'] != data['contrasenia_confirm']:
        flash("Las contraseñas no coinciden", "error")
        return redirect(url_for('register'))
    
    nuevo_usuario = UsuarioFinal(
        id_usuario=f"U{len(_DB_USERS)+1:03d}",
        email=data['email'],
        usuario=data['username'],
        contrasenia_hash=Usuario._hash_password(data['contrasenia']),
        nombre=data['nombre'],
        apellido=data['apellido'],
        claustro=Claustro[data['claustro']],
        gestor_servicio=gestor_reclamos
    )
    _DB_USERS[data['username']] = nuevo_usuario
    flash("Registro exitoso. Ya puedes iniciar sesión.", "success")
    return redirect(url_for('index'))

# --- Rutas de Usuario Final ---

@app.route('/menu')
@login_required
def user_menu():
    user = _DB_USERS.get(session['username'])
    return render_template('user_menu.html', current_user=user)

@app.route('/crear_reclamo')
@login_required
def crear_reclamo():
    return render_template('reclamo_form.html')

@app.route('/crear_reclamo_post', methods=['POST'])
@login_required
def crear_reclamo_post():
    user = _DB_USERS.get(session['username'])
    contenido = request.form.get('contenido')
    adjunto = request.form.get('adjunto_url')
    
    # El método crear_reclamo de UsuarioFinal ya usa el gestor internamente
    mensaje = user.crear_reclamo(contenido, adjunto)
    flash(mensaje, "info")
    return redirect(url_for('user_menu'))

@app.route('/listar_reclamos')
@login_required
def listar_reclamos():
    depto_id = request.args.get('depto_id')
    # Obtenemos todos los pendientes (RF 33)
    reclamos = gestor_reclamos.get_reclamos_pendientes_filtrados(depto_id)
    return render_template('lista_reclamos.html', 
                           reclamos=reclamos, 
                           departamentos=_DB_DEPTOS,
                           es_listado_global=True,
                           current_user=_DB_USERS.get(session['username']))

# --- Rutas de Administración ---

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    user = _DB_USERS.get(session['username'])
    if user.rol_admin == RolAdmin.NINGUNO:
        return redirect(url_for('user_menu'))
    
    # Obtener datos para el dashboard (RF 54, 55, 56)
    data_dash = analitica_servicio.obtener_datos_dashboard(user.departamento_id)
    reclamos = gestor_reclamos.get_reclamos_por_departamento(user.departamento_id)
    
    return render_template('admin_dashboard.html', 
                           current_user=user,
                           data_analitica=data_dash,
                           reclamos_del_depto=reclamos)

@app.route('/actualizar_estado', methods=['POST'])
@login_required
def actualizar_estado():
    user = _DB_USERS.get(session['username'])
    id_rec = request.form.get('id_reclamo')
    nuevo_est = request.form.get('nuevo_estado')
    
    if user.gestionar_reclamo(id_rec, EstadoReclamo[nuevo_est]):
        flash(f"Reclamo {id_rec} actualizado a {nuevo_est}", "success")
    else:
        flash("No tienes permiso o el reclamo no existe", "error")
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Usuarios de prueba: 1 Jefe y 1 Secretario
    _DB_USERS['jefe_infra'] = JefeDepartamento(
        id_usuario="ADM01", email="jefe@uner.edu.ar", usuario="jefe_infra",
        contrasenia_hash=Usuario._hash_password("admin123"),
        nombre="Carlos", apellido="Mantenimiento", claustro=Claustro.PAYS,
        departamento_id="D_INFRAESTRUCTURA", gestor_servicio=gestor_reclamos,
        analitica_servicio=analitica_servicio
    )
    
    app.run(debug=True)