import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = 'super_secreto_uner'

# --- 1. CONFIGURACIÓN DE BASE DE DATOS (Persistencia Relacional) ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración para subida de imágenes
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Inicializamos SQLAlchemy
db = SQLAlchemy(app)

# --- 2. IMPORTACIONES (Después de inicializar db para evitar errores) ---
from modules.usuarios import Usuario, UsuarioFinal, JefeDepartamento, SecretarioTecnico, RolAdmin, Claustro
from modules.reclamos import Reclamo, Clasificador, EstadoReclamo
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica

# Inicialización de servicios con la DB
STOPWORDS = ["el", "la", "los", "las", "un", "una", "y", "o", "de", "a", "en", "es", "para", "que"]
clasificador = Clasificador(stopwords=STOPWORDS)
gestor_serv = Gestor_Reclamos(db, clasificador)
analitica_serv = Analitica(gestor_serv)

# --- 3. INICIALIZACIÓN DE DATOS (Cumplimiento de UML) ---
@app.before_request
def inicializar_sistema():
    db.create_all()
    # Precarga de usuarios para pruebas si la base de datos está vacía
    if not Usuario.query.filter_by(username='estudiante1').first():
        u1 = UsuarioFinal(username='estudiante1', password='123', nombre='Juan', apellido='Perez', claustro=Claustro.ESTUDIANTE)
        j1 = JefeDepartamento(username='jefe1', password='123', nombre='Marta', apellido='Lopez', rol_admin=RolAdmin.JEFE, departamento_id='D_INFORMATICA')
        s1 = SecretarioTecnico(username='secretario1', password='123', nombre='Admin', apellido='Uner', rol_admin=RolAdmin.SECRETARIO)
        
        db.session.add_all([u1, j1, s1])
        db.session.commit()

# --- 4. DECORADORES ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Debes iniciar sesión primero", "warning")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- 5. RUTAS ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = Usuario.query.filter_by(username=username).first()
    
    if user and user.password == password:
        session['user_id'] = user.id
        # Verificamos la clase para redirigir (Polimorfismo en acción)
        if isinstance(user, (JefeDepartamento, SecretarioTecnico)):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    flash("Credenciales incorrectas", "danger")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- 6. RUTAS DE USUARIO FINAL (ESTUDIANTE) ---

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    # SQLAlchemy nos trae automáticamente un objeto de tipo UsuarioFinal
    user = Usuario.query.get(session['user_id'])
    todos = Reclamo.query.all()
    return render_template('user_dashboard.html', current_user=user, all_reclamos=todos)

@app.route('/crear_reclamo', methods=['POST'])
@login_required
def crear_reclamo():
    user = Usuario.query.get(session['user_id'])
    contenido = request.form.get('contenido')
    file = request.files.get('foto')
    
    adjunto_url = None
    if file and file.filename != '':
        filename = secure_filename(f"{datetime.datetime.now().timestamp()}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        adjunto_url = filename

    # El gestor ahora guarda en la base de datos relacional
    resultado = gestor_serv.crear_reclamo(contenido, adjunto_url, user.id)
    flash(resultado['mensaje'], "success" if resultado['status'] == 'ok' else "info")
    return redirect(url_for('user_dashboard'))

@app.route('/adherirse/<int:id_reclamo>', methods=['POST'])
@login_required
def adherirse(id_reclamo):
    user_id = session['user_id']
    if gestor_serv.adherirse_a_reclamo(id_reclamo, user_id):
        flash("Te has adherido con éxito.", "success")
    else:
        flash("Ya estás adherido o eres el creador.", "warning")
    return redirect(url_for('user_dashboard'))

# --- 7. RUTAS DE ADMINISTRACIÓN (JEFE/SECRETARIO) ---

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    user = Usuario.query.get(session['user_id'])
    
    # Lógica de filtrado según rol (RF 33)
    if user.rol_admin == RolAdmin.JEFE:
        reclamos = Reclamo.query.filter_by(departamento_id=user.departamento_id).all()
        datos_an = analitica_serv.obtener_datos_dashboard(user.departamento_id)
    else: # Secretario Técnico
        reclamos = Reclamo.query.all()
        datos_an = analitica_serv.obtener_datos_dashboard(None)
        
    return render_template('admin_dashboard.html', 
                           current_user=user, 
                           reclamos_admin=reclamos, 
                           data_analitica=datos_an)

@app.route('/actualizar_estado', methods=['POST'])
@login_required
def actualizar_estado():
    id_rec = request.form.get('id_reclamo')
    nuevo_est = request.form.get('nuevo_estado')
    
    if gestor_serv.gestionar_reclamo(id_rec, nuevo_est):
        flash(f"Reclamo #{id_rec} actualizado.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/derivar_reclamo', methods=['POST'])
@login_required
def derivar_reclamo():
    id_rec = request.form.get('id_reclamo')
    nuevo_depto = request.form.get('nuevo_depto')
    
    if gestor_serv.derivar_reclamo(id_rec, nuevo_depto):
        flash(f"Reclamo #{id_rec} derivado correctamente.", "info")
    return redirect(url_for('admin_dashboard'))

@app.route('/descargar_reporte')
@login_required
def descargar_reporte():
    # Genera una vista de impresión rápida (Simplificado)
    return "<h1>Reporte de Gestión</h1><p>Fecha: " + str(datetime.datetime.now()) + "</p><script>window.print();</script>"

if __name__ == '__main__':
    app.run(debug=True)