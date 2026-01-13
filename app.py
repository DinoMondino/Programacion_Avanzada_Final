from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import datetime

# Importaciones de tus módulos locales
from modules.usuarios import (
    UsuarioFinal, JefeDepartamento, SecretarioTecnico, 
    Claustro, RolAdmin
)
from modules.reclamos import Clasificador, EstadoReclamo
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

# --- Decorador de Autenticación ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Debes iniciar sesión primero", "error")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = _DB_USERS.get(username)
    if user and password == "1234":
        session['username'] = username
        if user.rol_admin != RolAdmin.NINGUNO:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    flash("Usuario o contraseña incorrectos", "error")
    return redirect(url_for('index'))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register_post', methods=['POST'])
def register_post():
    nombre = request.form.get('nombre')
    apellido = request.form.get('apellido')
    email = request.form.get('email')
    username = request.form.get('username')
    claustro_str = request.form.get('claustro')
    
    nuevo_usuario = UsuarioFinal(
        id_usuario=f"USR{len(_DB_USERS) + 1:03d}",
        email=email, usuario=username, contrasenia_hash="hash",
        nombre=nombre, apellido=apellido,
        claustro=Claustro[claustro_str.upper()],
        gestor_servicio=gestor_reclamos
    )
    _DB_USERS[username] = nuevo_usuario
    flash("Registro exitoso", "success")
    return redirect(url_for('index'))

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    user = _DB_USERS.get(session['username'])
    mis_reclamos = user.ver_mis_reclamos()
    return render_template('user_dashboard.html', 
                           user=user, 
                           reclamos=mis_reclamos,
                           all_reclamos=gestor_reclamos._reclamos_db)

@app.route('/crear_reclamo', methods=['POST'])
@login_required
def crear_reclamo():
    user = _DB_USERS.get(session['username'])
    contenido = request.form.get('contenido')
    mensaje = user.crear_reclamo(contenido)
    flash(mensaje, "success")
    return redirect(url_for('user_dashboard'))

@app.route('/adherirse/<id_reclamo>')
@login_required
def adherirse(id_reclamo):
    user = _DB_USERS.get(session['username'])
    # Verificamos que el método exista antes de llamarlo
    if hasattr(user, 'adherirse'):
        if user.adherirse(id_reclamo):
            flash(f"Te has adherido al reclamo {id_reclamo}", "success")
        else:
            flash("No puedes adherirte a tu propio reclamo o ya estás adherido", "warning")
    return redirect(url_for('user_dashboard'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    user = _DB_USERS.get(session['username'])
    if user.rol_admin == RolAdmin.NINGUNO:
        return redirect(url_for('user_dashboard'))
    
    # --- CORRECCIÓN AQUÍ ---
    if user.rol_admin == RolAdmin.JEFE:
        # El Jefe solo ve su departamento
        depto_id = user.departamento_id
        data_dash = analitica_servicio.obtener_datos_dashboard(depto_id)
        reclamos = user.listar_reclamos_pendientes_admin()
    else:
        # El Secretario ve TODO (pasamos None o un ID global si tu analitica lo soporta)
        # Si depto_id es None, el gestor debería devolver el total general
        data_dash = analitica_servicio.obtener_datos_dashboard(None) 
        reclamos = user.listar_reclamos_pendientes_admin()
    
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
    user.gestionar_reclamo(id_rec, EstadoReclamo[nuevo_est.upper()])
    return redirect(url_for('admin_dashboard'))

@app.route('/derivar_reclamo', methods=['POST'])
@login_required
def derivar_reclamo():
    user = _DB_USERS.get(session['username'])
    # Solo el secretario puede acceder a esta ruta
    if user.rol_admin == RolAdmin.SECRETARIO:
        id_rec = request.form.get('id_reclamo')
        nuevo_depto = request.form.get('nuevo_depto')
        if user.derivar_reclamo(id_rec, nuevo_depto):
            flash(f"Reclamo {id_rec} derivado a {nuevo_depto}", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/descargar_reporte/<formato>')
@login_required
def descargar_reporte(formato):
    flash(f"Reporte {formato} generado", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # --- USUARIOS DE PRUEBA ---
    _DB_USERS['jefe_infra'] = JefeDepartamento(
        id_usuario="ADM01", email="jefe@uner.edu.ar", usuario="jefe_infra",
        contrasenia_hash="hash", nombre="Emanuel", apellido="Admin",
        claustro=Claustro.PAYS, departamento_id="D_INFRAESTRUCTURA",
        gestor_servicio=gestor_reclamos, analitica_servicio=analitica_servicio
    )

    _DB_USERS['secretario'] = SecretarioTecnico(
        id_usuario="SEC01", email="secretario@uner.edu.ar", usuario="secretario",
        contrasenia_hash="hash", nombre="Ana", apellido="Lopez",
        claustro=Claustro.PAYS, 
        gestor_servicio=gestor_reclamos, 
        analitica_servicio=analitica_servicio
    )

    _DB_USERS['estudiante1'] = UsuarioFinal(
        id_usuario="USR01", email="juan@uner.edu.ar", usuario="estudiante1",
        contrasenia_hash="hash", nombre="Juan", apellido="Perez",
        claustro=Claustro.ESTUDIANTE, gestor_servicio=gestor_reclamos
    )

    _DB_USERS['estudiante2'] = UsuarioFinal(
        id_usuario="USR02", email="maria@uner.edu.ar", usuario="estudiante2",
        contrasenia_hash="hash", nombre="Maria", apellido="Gomez",
        claustro=Claustro.ESTUDIANTE, gestor_servicio=gestor_reclamos
    )

# --- 2. PRECARGA DE RECLAMOS (Creados por estudiante2) ---
    # Reclamo 1: Infraestructura (por palabras clave como 'techo' o 'baño')
    gestor_reclamos.crear_reclamo(
        contenido="Hay una filtración en el techo del aula 6, gotea mucho cuando llueve.",
        adjunto=None,
        usuario_creator_id="USR02"
    )

    # Reclamo 2: Infraestructura (por palabras clave como 'puerta' o 'vidrio')
    gestor_reclamos.crear_reclamo(
        contenido="La puerta del baño de mujeres del modulo 2 está rota.",
        adjunto=None,
        usuario_creator_id="USR02"
    )

    # Reclamo 3: General/Otro (para que no vaya todo al mismo lugar)
    gestor_reclamos.crear_reclamo(
        contenido="Estaría bueno tener más opciones de comida saludable en el comedor.",
        adjunto=None,
        usuario_creator_id="USR02"
    )

    print("Servidor iniciado con usuarios y 3 reclamos de prueba cargados.")
    app.run(debug=True, port=5000)