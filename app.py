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

basedir = os.path.abspath(os.path.dirname(__file__))
# Definimos la carpeta de subidas
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')

# Creamos la carpeta físicamente si no existe para evitar errores de escritura
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuración
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# IMPORTANTE: Importamos db desde el módulo de usuarios e iniciamos la app con él
from modules.usuarios import db, Usuario, UsuarioFinal, JefeDepartamento, SecretarioTecnico, RolAdmin, Claustro
from modules.reclamos import Reclamo
from modules.gestor import Gestor_Reclamos

db.init_app(app) # Vinculamos db con esta app

with app.app_context():
    from modules.reclamos import Reclamo # Importamos Reclamo primero
    from modules.usuarios import Usuario, UsuarioFinal, JefeDepartamento, SecretarioTecnico

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
    # Importación interna para evitar el círculo vicioso
    from modules.usuarios import Usuario, RolAdmin, JefeDepartamento, SecretarioTecnico
    
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
    # Importamos las clases necesarias
    from modules.usuarios import UsuarioFinal, Claustro, RolAdmin
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        claustro_str = request.form.get('claustro') # Viene del <select>
        
        # Verificamos si ya existe
        from modules.usuarios import Usuario
        if Usuario.query.filter_by(username=username).first():
            flash("El nombre de usuario ya existe", "danger")
            return redirect(url_for('register'))
        
        # Creamos el nuevo usuario (UML: UsuarioFinal)
        nuevo_usuario = UsuarioFinal(
            username=username,
            password=password,
            nombre=nombre,
            apellido=apellido,
            claustro=Claustro[claustro_str], # Convierte string a Enum
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

# --- 4. DASHBOARD USUARIO (Tus funcionalidades originales) ---

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    from modules.usuarios import Usuario
    from modules.reclamos import Reclamo
    
    user = Usuario.query.get(session['user_id'])
    todos_los_reclamos = Reclamo.query.all()
    return render_template('user_dashboard.html', 
                           current_user=user, 
                           all_reclamos=todos_los_reclamos)

@app.route('/crear_reclamo', methods=['POST'])
@login_required
def crear_reclamo():
    from modules.usuarios import Usuario
    from modules.reclamos import Reclamo, Clasificador
    from modules.gestor import Gestor_Reclamos
    
    user = Usuario.query.get(session['user_id'])
    contenido = request.form.get('contenido')
    
    # --- ESTA ES LA LÍNEA QUE FALTA ---
    # Obtenemos el valor del campo 'confirmado' que enviamos desde el HTML
    confirmado = request.form.get('confirmado') == 'true'
    
    file = request.files.get('foto')
    
    # Manejo de archivos
    adjunto_url = None
    if file and file.filename != '':
        from werkzeug.utils import secure_filename
        import datetime
        filename = secure_filename(f"{datetime.datetime.now().timestamp()}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        adjunto_url = filename

    # Lógica de detección de similares
    if not confirmado:
        palabras = [p for p in contenido.split() if len(p) > 3]
        similares = []
        if palabras:
            # Buscamos en la DB reclamos similares
            similares = Reclamo.query.filter(
                Reclamo.estado == 'pendiente'
            ).filter(
                db.or_(*[Reclamo.contenido.like(f"%{p}%") for p in palabras[:3]])
            ).limit(3).all()

        if similares:
            # IMPORTANTE: Pasamos todos los datos para que el dashboard cargue bien
            return render_template('user_dashboard.html', 
                                   current_user=user, 
                                   all_reclamos=Reclamo.query.all(),
                                   reclamos_similares=similares,
                                   contenido_pendiente=contenido)

    # Si llegó aquí es porque no hay similares o el usuario ya confirmó
    gestor_serv = Gestor_Reclamos(db, Clasificador(stopwords=[]))
    resultado = gestor_serv.crear_reclamo(contenido, adjunto_url, user.id)
    
    flash(resultado['mensaje'], "success")
    return redirect(url_for('user_dashboard'))
@app.route('/adherirse/<int:id_reclamo>', methods=['POST'])
@login_required
def adherirse(id_reclamo):
    from modules.reclamos import Reclamo
    from modules.usuarios import Usuario
    
    reclamo = Reclamo.query.get_or_404(id_reclamo)
    user = Usuario.query.get(session['user_id'])
    
    # Verificamos si ya lo apoya
    if user in reclamo.seguidores:
        flash("Ya has apoyado este reclamo.", "warning")
    else:
        reclamo.seguidores.append(user) # Agregamos el apoyo
        db.session.commit()
        flash("¡Apoyo registrado con éxito!", "success")
        
    return redirect(url_for('user_dashboard'))

# --- 5. DASHBOARD ADMINISTRADOR ---

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    from modules.usuarios import Usuario, JefeDepartamento, RolAdmin
    from modules.reclamos import Reclamo
    from modules.departamentos import Analitica
    from modules.gestor import Gestor_Reclamos
    from modules.reclamos import Clasificador

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
    from modules.reclamos import Reclamo
    
    # Obtenemos el nuevo estado desde el formulario
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
    from modules.reclamos import Reclamo
    from modules.usuarios import Usuario, JefeDepartamento
    
    user = Usuario.query.get(session['user_id'])
    
    # Filtrar reclamos según quién descarga
    if isinstance(user, JefeDepartamento):
        reclamos = Reclamo.query.filter_by(departamento_id=user.departamento_id).all()
    else:
        reclamos = Reclamo.query.all()

    # Crear un archivo CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Contenido', 'Estado', 'Departamento', 'Fecha'])
    
    for r in reclamos:
        writer.writerow([r.id, r.contenido, r.estado, r.departamento_id, r.fecha_creacion])
    
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=reporte_reclamos.csv"}
    )

@app.route('/derivar_reclamo', methods=['POST'])
@login_required
def derivar_reclamo():
    from modules.reclamos import Reclamo
    
    # IMPORTANTE: Los nombres deben coincidir con el 'name' del <select> y <input> en el HTML
    reclamo_id = request.form.get('id_reclamo') 
    nuevo_depto = request.form.get('nuevo_depto')
    
    if not reclamo_id or not nuevo_depto:
        flash("Error: Datos de derivación incompletos.", "danger")
        return redirect(url_for('admin_dashboard'))

    reclamo = Reclamo.query.get(reclamo_id)
    if reclamo:
        reclamo.departamento_id = nuevo_depto
        db.session.commit() # Si falta esta línea, el cambio no se guarda
        flash(f"Reclamo #{reclamo_id} derivado con éxito a {nuevo_depto.replace('D_', '')}.", "success")
    else:
        flash("No se encontró el reclamo solicitado.", "danger")
    
    return redirect(url_for('admin_dashboard'))

# --- 6. INICIALIZACIÓN ---
def inicializar_base_de_datos():
    with app.app_context():
        db.create_all()
        from modules.usuarios import Usuario, SecretarioTecnico, JefeDepartamento
        
        # Solo creamos si no existen para no duplicar ni causar errores
        if not Usuario.query.filter_by(username='secretario').first():
            admin = SecretarioTecnico(username='secretario', password='1234', nombre='Admin')
            db.session.add(admin)

        if not Usuario.query.filter_by(username='jefe_infra').first():
            jefe = JefeDepartamento(username='jefe_infra', password='1234', nombre='Roberto', departamento_id='D_INFRAESTRUCTURA')
            db.session.add(jefe)

        db.session.commit()

if __name__ == '__main__':
    inicializar_base_de_datos() # Llamada única al iniciar
    app.run(debug=True)

# el grafico de torta tiene resueltos y pendientes pero no en proceso
# cuando te dice que se encontro un reclamo similar, no deberia dejar crear el reclamo si que el usuario confirme que no son similares