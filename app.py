# python app.py

import os
import io
import csv
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = 'super_secreto_uner'

# --- 1. CONFIGURACIÓN DE RUTAS Y BASE DE DATOS ---
basedir = os.path.abspath(os.path.dirname(__file__))

# Carpeta de subidas
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuración de base de datos con ruta absoluta para asegurar persistencia
db_path = os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Importamos la instancia de db desde el módulo de usuarios
from modules.usuarios import db, Usuario, UsuarioFinal, JefeDepartamento, SecretarioTecnico, RolAdmin, Claustro
from modules.reclamos import Reclamo, Clasificador
from modules.gestor import Gestor_Reclamos

db.init_app(app)

# --- 2. DECORADOR DE AUTENTICACIÓN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Por favor, inicia sesión.", "warning")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- 3. RUTAS DE NAVEGACIÓN Y LOGIN ---

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
        if isinstance(user, (JefeDepartamento, SecretarioTecnico)):
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    flash("Usuario o contraseña incorrectos", "danger")
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        claustro_str = request.form.get('claustro')
        
        if Usuario.query.filter_by(username=username).first():
            flash("El nombre de usuario ya existe", "danger")
            return redirect(url_for('register'))
        
        nuevo_usuario = UsuarioFinal(
            username=username,
            password=password,
            nombre=nombre,
            apellido=apellido,
            claustro=Claustro[claustro_str],
            rol_admin=RolAdmin.NINGUNO
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        flash("Registro exitoso. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- 4. DASHBOARD USUARIO ---

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    user = Usuario.query.get(session['user_id'])
    todos_los_reclamos = Reclamo.query.all()
    return render_template('user_dashboard.html', 
                           current_user=user, 
                           all_reclamos=todos_los_reclamos)

@app.route('/crear_reclamo', methods=['POST'])
@login_required
def crear_reclamo():
    user = Usuario.query.get(session['user_id'])
    contenido = request.form.get('contenido')
    confirmado = request.form.get('confirmado') == 'true'
    file = request.files.get('foto')
    
    adjunto_url = None
    if file and file.filename != '':
        filename = secure_filename(f"{datetime.datetime.now().timestamp()}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        adjunto_url = filename

    if not confirmado:
        palabras = [p for p in contenido.split() if len(p) > 3]
        similares = []
        if palabras:
            similares = Reclamo.query.filter(
                Reclamo.estado == 'pendiente'
            ).filter(
                db.or_(*[Reclamo.contenido.like(f"%{p}%") for p in palabras[:3]])
            ).limit(3).all()

        if similares:
            return render_template('user_dashboard.html', 
                                   current_user=user, 
                                   all_reclamos=Reclamo.query.all(),
                                   reclamos_similares=similares,
                                   contenido_pendiente=contenido)

    gestor_serv = Gestor_Reclamos(db, Clasificador(stopwords=[]))
    resultado = gestor_serv.crear_reclamo(contenido, adjunto_url, user.id)
    
    flash(resultado['mensaje'], "success")
    return redirect(url_for('user_dashboard'))

@app.route('/adherirse/<int:id_reclamo>', methods=['POST'])
@login_required
def adherirse(id_reclamo):
    reclamo = Reclamo.query.get_or_404(id_reclamo)
    user = Usuario.query.get(session['user_id'])
    
    if user in reclamo.seguidores:
        flash("Ya has apoyado este reclamo.", "warning")
    else:
        reclamo.seguidores.append(user)
        db.session.commit()
        flash("¡Apoyo registrado con éxito!", "success")
        
    return redirect(url_for('user_dashboard'))

# --- 5. DASHBOARD ADMINISTRADOR ---

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    from modules.departamentos import Analitica
    user = Usuario.query.get(session['user_id'])
    gestor_serv = Gestor_Reclamos(db, Clasificador(stopwords=[]))
    analitica_serv = Analitica(gestor_serv)
    
    if isinstance(user, JefeDepartamento):
        reclamos = Reclamo.query.filter_by(departamento_id=user.departamento_id).all()
        datos_an = analitica_serv.obtener_datos_dashboard(user.departamento_id)
    else:
        reclamos = Reclamo.query.all()
        datos_an = analitica_serv.obtener_datos_dashboard(None)
        
    return render_template('admin_dashboard.html', 
                           current_user=user, 
                           reclamos_admin=reclamos, 
                           data_analitica=datos_an)

@app.route('/actualizar_estado/<int:id>', methods=['POST'])
@login_required
def actualizar_estado(id):
    nuevo_estado = request.form.get('nuevo_estado') 
    reclamo = Reclamo.query.get_or_404(id)
    if reclamo:
        reclamo.estado = nuevo_estado
        db.session.commit()
        flash(f"El reclamo #{id} ahora está: {nuevo_estado}", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/descargar_reporte')
@login_required
def descargar_reporte():
    user = Usuario.query.get(session['user_id'])
    if isinstance(user, JefeDepartamento):
        reclamos = Reclamo.query.filter_by(departamento_id=user.departamento_id).all()
    else:
        reclamos = Reclamo.query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Contenido', 'Estado', 'Departamento', 'Fecha'])
    for r in reclamos:
        writer.writerow([r.id, r.contenido, r.estado, r.departamento_id, r.fecha_creacion])
    
    output.seek(0)
    return Response(output, mimetype="text/csv", 
                    headers={"Content-disposition": "attachment; filename=reporte.csv"})

@app.route('/derivar_reclamo', methods=['POST'])
@login_required
def derivar_reclamo():
    reclamo_id = request.form.get('id_reclamo') 
    nuevo_depto = request.form.get('nuevo_depto')
    reclamo = Reclamo.query.get(reclamo_id)
    if reclamo:
        reclamo.departamento_id = nuevo_depto
        db.session.commit()
        flash(f"Reclamo #{reclamo_id} derivado a {nuevo_depto}.", "success")
    return redirect(url_for('admin_dashboard'))

# --- 6. INICIALIZACIÓN ---
def inicializar_base_de_datos():
    with app.app_context():
        # IMPORTANTE: Aseguramos que SQLAlchemy detecte todos los modelos antes de crear tablas
        import modules.usuarios
        import modules.reclamos
        db.create_all()
        
        # Crear usuarios por defecto si no existen
        if not Usuario.query.filter_by(username='secretario').first():
            admin = SecretarioTecnico(username='secretario', password='1234', nombre='Admin')
            db.session.add(admin)

        if not Usuario.query.filter_by(username='jefe_infra').first():
            jefe = JefeDepartamento(username='jefe_infra', password='1234', nombre='Roberto', 
                                    departamento_id='D_INFRAESTRUCTURA')
            db.session.add(jefe)

        db.session.commit()

if __name__ == '__main__':
    inicializar_base_de_datos()
    app.run(debug=True)