from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import os
import datetime
from werkzeug.utils import secure_filename
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

# Configuración para subida de archivos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    # 1. Obtenemos el objeto usuario desde nuestra "DB" usando la sesión
    user = _DB_USERS.get(session['username'])
    
    # 2. Pasamos el objeto al template
    return render_template('user_dashboard.html', 
                           current_user=user, 
                           all_reclamos=gestor_reclamos._reclamos_db)

@app.route('/crear_reclamo', methods=['POST'])
@login_required
def crear_reclamo():
    user = _DB_USERS.get(session['username'])
    contenido = request.form.get('contenido')
    file = request.files.get('foto')
    
    adjunto_url = None
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{datetime.datetime.now().timestamp()}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        adjunto_url = filename

    mensaje = user.crear_reclamo(contenido, adjunto_url)
    flash(mensaje, "info")
    return redirect(url_for('user_dashboard'))

@app.route('/adherirse/<id_reclamo>', methods=['POST'])
@login_required
def adherirse(id_reclamo): # Aquí recibe el ID directamente de la URL
    user = _DB_USERS.get(session['username'])
    
    # Llamamos al método del gestor
    if gestor_reclamos.adherirse_a_reclamo(id_reclamo, user.id):
        flash(f"Te has adherido al reclamo {id_reclamo}", "success")
    else:
        flash("No se pudo realizar la adhesión", "error")
        
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
    if id_rec and nuevo_est:
        try:
            # Corrección: Buscar por valor para evitar problemas de tildes/KeyError
            estado_enum = EstadoReclamo(nuevo_est.lower())
            user.gestionar_reclamo(id_rec, estado_enum)
            flash(f"Reclamo {id_rec} actualizado", "success")
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
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

@app.route('/descargar_reporte')
@login_required
def descargar_reporte():
    user = _DB_USERS.get(session['username'])
    if user.rol_admin == RolAdmin.NINGUNO:
        return redirect(url_for('index'))
    
    depto_id = user.departamento_id if user.rol_admin == RolAdmin.JEFE else None
    # Genera el reporte HTML real
    html_content = analitica_servicio.generar_reporte_html(depto_id)
    
    # lo devolvemos como un archivo HTML descargable
    from flask import Response
    return Response(
        html_content,
        mimetype="text/html",
        headers={"Content-disposition": "attachment; filename=reporte_gestion.html"}
    )

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