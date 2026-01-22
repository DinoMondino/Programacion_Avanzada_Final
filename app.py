import os
import io
import csv
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from functools import wraps

# Importamos la base de datos, modelos y la nueva clase Analitica
from modules.usuarios import db, Usuario, UsuarioFinal, JefeDepartamento, SecretarioTecnico
from modules.reclamos import Reclamo, Clasificador
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica

app = Flask(__name__)
app.secret_key = 'super_secreto_uner'

# Configuración de base de datos
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialización del sistema
db.init_app(app)

# --- NOTA: Usamos el mismo objeto clasificador para ambos ---
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = UsuarioFinal(
            username=request.form.get('username'),
            password=request.form.get('password'),
            nombre=request.form.get('nombre')
        )
        db.session.add(u)
        db.session.commit()
        flash("Registro exitoso", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = Usuario.query.get(session['user_id'])
    mis_reclamos = gestor.obtener_reclamos_para_usuario(user)
    todos = gestor.obtener_todos_los_reclamos()
    return render_template('user_dashboard.html', current_user=user, all_reclamos=todos)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    user = Usuario.query.get(session['user_id'])
    
    if user.tipo_usuario == 'secretario':
        reclamos_lista = Reclamo.query.all()
        depto_para_analitica = None 
    else:
        reclamos_lista = Reclamo.query.filter_by(departamento_id=user.departamento_id).all()
        depto_para_analitica = user.departamento_id
    
    datos_analitica = analitica_servicio.obtener_datos_dashboard(depto_para_analitica)
    
    return render_template('admin_dashboard.html', 
                           reclamos_admin=reclamos_lista, 
                           data_analitica=datos_analitica, 
                           current_user=user)

# --- ACCIONES ---

@app.route('/admin/cambiar_estado/<int:id>', methods=['POST'])
@login_required
def actualizar_estado(id):
    nuevo_est = request.form.get('nuevo_estado')
    if gestor.gestionar_estado_reclamo(id, nuevo_est):
        flash("Estado actualizado", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/crear_reclamo', methods=['GET', 'POST'])
@login_required
def crear_reclamo():
    if request.method == 'POST':
        contenido = request.form.get('contenido')
        confirmar_nuevo = request.form.get('confirmar_nuevo')
        
        # 1. Buscar similares usando el objeto 'clasificador'
        # Creamos el historial en el momento para evitar el NameError
        historial_reclamos = {r.id: r for r in Reclamo.query.all()}
        similares_ids = clasificador.buscar_similares(contenido, historial_reclamos) 
        
        if similares_ids and not confirmar_nuevo:
            similar = Reclamo.query.get(similares_ids[0])
            return render_template('crear_reclamo.html', 
                                   reclamo_similar=similar, 
                                   contenido_previo=contenido)

        # 2. Crear el reclamo si no hay similares o se confirmó
        gestor.crear_reclamo(contenido, None, session['user_id'])
        flash("Reclamo creado con éxito.", "success")
        return redirect(url_for('dashboard'))
        
    return render_template('crear_reclamo.html', reclamo_similar=None)

@app.route('/reclamo/adherir/<int:id_reclamo>', methods=['GET', 'POST']) # <--- Agrega esto
@login_required
def adherirse(id_reclamo):
    usuario_id = session.get('user_id')
    exito = gestor.adherirse_a_reclamo(id_reclamo, usuario_id)
    
    if exito:
        flash("Te has adherido al reclamo correctamente.", "success")
    else:
        flash("Ya estás adherido a este reclamo o eres el autor.", "info")
        
    return redirect(url_for('dashboard'))

@app.route('/descargar_reporte')
@login_required
def descargar_reporte():
    user = Usuario.query.get(session['user_id'])
    if user.tipo_usuario == 'secretario':
        reclamos = Reclamo.query.all()
    else:
        reclamos = Reclamo.query.filter_by(departamento_id=user.departamento_id).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['ID', 'Fecha', 'Usuario', 'Departamento', 'Contenido', 'Estado', 'Apoyos'])
    
    for r in reclamos:
        cant_apoyos = len(r.seguidores) if hasattr(r, 'seguidores') and r.seguidores else 0
        nombre_autor = r.autor.nombre if hasattr(r, 'autor') and r.autor else "Anónimo"
        
        writer.writerow([
            r.id,
            r.fecha_creacion.strftime('%d/%m/%Y %H:%M') if r.fecha_creacion else '-',
            nombre_autor,
            r.departamento_id,
            r.contenido.replace('\n', ' ').replace('\r', ' '),
            r.estado.upper() if isinstance(r.estado, str) else str(r.estado),
            cant_apoyos
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=reporte.csv"}
    )

@app.route('/admin/derivar', methods=['POST'])
@login_required
def derivar_reclamo():
    id_rec = request.form.get('id_reclamo')
    nuevo_d = request.form.get('nuevo_depto')
    if gestor.derivar_reclamo(id_rec, nuevo_d):
        flash(f"Reclamo #{id_rec} derivado correctamente.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Usuario.query.filter_by(username='admin').first():
            db.session.add(SecretarioTecnico(username='admin', password='123', nombre='Admin'))
            db.session.commit()
    app.run(debug=True)