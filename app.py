import os # Para manejo de rutas y archivos
import io # Para manejo de flujos de datos
import csv # Para generación de reportes CSV
import sys # Para detección de modo test
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response # Para servicio web
from functools import wraps # Para decoradores

# Importamos la base de datos y los usuarios, reclamos, gestor y analítica
from modules.usuarios import db, Usuario, UsuarioFinal, JefeDepartamento, SecretarioTecnico
from modules.reclamos import Reclamo, Clasificador
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica

app = Flask(__name__) # Inicialización de la app
app.secret_key = 'super_secreto_uner'

basedir = os.path.abspath(os.path.dirname(__file__)) # Directorio base
# Configuración de base de datos. Uso SQLite para simplicidad.
# Detecta si esta en modo test, asi al ejecutarlos no sobreescriben la base real.
if 'pytest' in sys.modules or 'pytest' in sys.argv[0]:
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    print(">>> MODO TEST DETECTADO: Usando base de datos en RAM.")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
    print(">>> MODO PRODUCCIÓN: Usando database.db físico.")

UPLOAD_FOLDER = 'static/uploads' # Carpeta para subir archivos de imagenes
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER): # Crear la carpeta si no existe
    os.makedirs(UPLOAD_FOLDER)

# Inicialización del sistema
db.init_app(app)

clasificador = Clasificador()
gestor = Gestor_Reclamos(db, clasificador)
analitica_servicio = Analitica(gestor)

# --- DECORADOR DE SEGURIDAD ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Por favor, inicia sesión.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS DE NAVEGACIÓN ---
@app.route('/')
def index():
    return redirect(url_for('login'))

# Inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            session['user_id'] = user.id
            if user.tipo_usuario in ['jefe', 'secretario']:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        flash("Usuario o contraseña incorrectas")

    return render_template('index.html')

# Registro de usuario final
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. Extraemos los datos del formulario
        username = request.form.get('username')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        claustro = request.form.get('claustro')

        # 2. Ahora verificamos si el username ya existe
        if Usuario.query.filter_by(username=username).first():
            flash("El usuario ya existe", "danger")
            return redirect(url_for('register'))
        
        # 3. Creamos el objeto con los datos extraídos
        u = UsuarioFinal(
            username=username,
            password=password,
            nombre=nombre,
            apellido=apellido,
            claustro=claustro
        )
        
        try:
            db.session.add(u)
            db.session.commit()
            flash("Registro exitoso", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al registrar: {e}", "danger")
            return redirect(url_for('register'))
        
    return render_template('register.html')

# --- DASHBOARDS ---
@app.route('/dashboard')
@login_required
def dashboard():
    user = Usuario.query.get(session['user_id']) # Usuario actual
    mis_reclamos = gestor.obtener_reclamos_para_usuario(user) # Sus reclamos
    todos = gestor.obtener_todos_los_reclamos() # Todos los reclamos
    return render_template('user_dashboard.html', current_user=user, all_reclamos=todos)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    user = Usuario.query.get(session['user_id']) # Usuario actual
    
    if user.tipo_usuario == 'secretario': # Verificamos si es secretario, para que vea todos los reclamos
        reclamos_lista = Reclamo.query.all()
        depto_para_analitica = None 
    else:
        reclamos_lista = Reclamo.query.filter_by(departamento_id=user.departamento_id).all() # Sino, solo los de su depto
        depto_para_analitica = user.departamento_id
    
    datos_analitica = analitica_servicio.obtener_datos_dashboard(depto_para_analitica)
    
    return render_template('admin_dashboard.html', 
                           reclamos_admin=reclamos_lista, 
                           data_analitica=datos_analitica, 
                           current_user=user)

# --- ACCIONES ---
# Actualizar estado de reclamo
@app.route('/admin/cambiar_estado/<int:id>', methods=['POST'])
@login_required
def actualizar_estado(id):
    nuevo_est = request.form.get('nuevo_estado') # Nuevo estado desde el formulario
    if gestor.gestionar_estado_reclamo(id, nuevo_est):
        flash("Estado actualizado", "success") # el commit se hace en la función del gestor.
    return redirect(url_for('admin_dashboard'))

# Crear nuevo reclamo
@app.route('/crear_reclamo', methods=['GET', 'POST'])
@login_required
def crear_reclamo():
    if request.method == 'POST':
        contenido = request.form.get('contenido') # Contenido del reclamo
        archivo = request.files.get('foto') # Archivo subido, si hay
        confirmar_nuevo = request.form.get('confirmar_nuevo') # Confirmación de crear nuevo reclamo

        nombre_archivo = None
        # Verificamos si subieron una foto
        if archivo and archivo.filename != '':
            nombre_archivo = archivo.filename
            # Guardamos el archivo en la carpeta de uploads
            archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo))

        # 1. Buscar similares usando el objeto 'clasificador'
        historial_reclamos = {r.id: r for r in Reclamo.query.all()} # Diccionario de reclamos, para evitar NameError
        similares_ids = clasificador.buscar_similares(contenido, historial_reclamos) 
        
        if similares_ids and not confirmar_nuevo:
            similar = Reclamo.query.get(similares_ids[0])
            return render_template('crear_reclamo.html', 
                                   reclamo_similar=similar, 
                                   contenido_previo=contenido) # Mostramos el similar encontrado, no creamos aún.
# Al usuario le aparece la opcion de adherirse al similar o confirmar crear nuevo. (Botones en el crear_reclamo.HTML)
# Si se adhiere, se frena "crear reclamo" y redirige al dashboard. Si confirma nuevo, se sigue el flujo.
        # 2. Crea el reclamo si no hay similares o se confirmó querer crear uno nuevo
        gestor.crear_reclamo(
            contenido=contenido, 
            adjunto=nombre_archivo, # Guardamos el nombre en la BD
            usuario_id=session['user_id']
        )
        flash("Reclamo creado con éxito.", "success")
        return redirect(url_for('dashboard'))
        
    return render_template('crear_reclamo.html', reclamo_similar=None)

# Adherirse a un reclamo existente
@app.route('/reclamo/adherir/<int:id_reclamo>', methods=['GET', 'POST']) # <--- Agrega esto
@login_required
def adherirse(id_reclamo):
    usuario_id = session.get('user_id') # ID del usuario actual
    exito = gestor.adherirse_a_reclamo(id_reclamo, usuario_id) # Intentamos adherirnos al reclamo
    # Mensaje según el resultado, si es el creador o ya está adherido, no se adhiere.
    if exito:
        flash("Te has adherido al reclamo correctamente.", "success")
    else:
        flash("Ya estás adherido a este reclamo o eres el autor.", "info")

    return redirect(url_for('dashboard'))

# Descargar reporte
@app.route('/descargar_reporte/<formato>')
def descargar_reporte(formato):
    depto_id = session.get('departamento_id') # Solo para Jefes
    
    if formato == 'pdf':
        estrategia = ReportePDF()
    else:
        estrategia = ReporteHTML()
        
    contenido = analitica.generar_reporte(depto_id, estrategia)
    return contenido # Envía el reporte generado

# Derivar reclamo a otro departamento
@app.route('/admin/derivar', methods=['POST'])
@login_required
def derivar_reclamo():
    id_rec = request.form.get('id_reclamo') # ID del reclamo a derivar
    nuevo_d = request.form.get('nuevo_depto') # Nuevo departamento destino
    if gestor.derivar_reclamo(id_rec, nuevo_d): # Intentamos derivar
        flash(f"Reclamo #{id_rec} derivado correctamente.", "success")
    return redirect(url_for('admin_dashboard'))

# Cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
        
if __name__ == '__main__':
    with app.app_context(): # Asegura que tengamos la databese para la app
        # 1. Crea las tablas. Si ya existen, no toca los datos que hay adentro.
        db.create_all()

        # 2. Verifica y crea el Secretario base (solo si no existe)
        if not Usuario.query.filter_by(username='secretario').first():
            admin = SecretarioTecnico(
                username='secretario', 
                password='1234', 
                nombre='Secretario',
                apellido='Técnico'
            )
            db.session.add(admin)
            print(">>> Usuario 'secretario' creado por primera vez.")

        # 3. Verifica y crea el Jefe de Infraestructura (solo si no existe)
        if not Usuario.query.filter_by(username='jefe_infra').first():
            jefe = JefeDepartamento(
                username='jefe_infra', 
                password='1234', 
                nombre='Jefe',
                apellido='Infraestructura',
                departamento_id='D_INFRAESTRUCTURA'
            )
            db.session.add(jefe)
            print(">>> Usuario 'jefe_infra' creado por primera vez.")

        # 4. Guarda los cambios
        db.session.commit()
        
    app.run(debug=True)