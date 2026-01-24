import os
import sys
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps

# Importaciones de tus módulos
from modules.usuarios import db, Usuario
from modules.reclamos import Reclamo, Clasificador, EstadoReclamo
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica, ReporteHTML, ReportePDF

app = Flask(__name__)
app.secret_key = 'super_secreto_uner'
basedir = os.path.abspath(os.path.dirname(__file__))

# 1. BLINDAJE DE DB (Mantiene tus reclamos reales a salvo de los tests)
if 'pytest' in sys.modules or 'pytest' in sys.argv[0]:
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
db.init_app(app)

# 2. INSTANCIACIÓN DE SERVICIOS
clasificador = Clasificador()
gestor = Gestor_Reclamos(db, clasificador)
analitica = Analitica(gestor)

# 3. DECORADORES DE SEGURIDAD
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') not in ['JEFE', 'SECRETARIO']:
            flash("Acceso no autorizado.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# 4. RUTAS DE AUTENTICACIÓN
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form['username']).first()
        if user and user.password == request.form['password']:
            session['user_id'] = user.id
            session['rol'] = user.rol_admin
            session['depto'] = user.departamento_id
            return redirect(url_for('dashboard'))
        flash("Credenciales incorrectas", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 5. RUTAS DEL USUARIO FINAL
@app.route('/dashboard')
@login_required
def dashboard():
    usuario = Usuario.query.get(session['user_id'])
    
    # Si es Jefe o Secretario, va al panel de Analítica
    if usuario.rol_admin in ['JEFE', 'SECRETARIO']:
        datos_dash = analitica.obtener_datos_dashboard(usuario.departamento_id)
        return render_template('admin_dashboard.html', user=usuario, datos=datos_dash)
    
    # Si es usuario final, ve sus reclamos y los globales para adherirse
    mis_reclamos = Reclamo.query.filter_by(usuario_id=usuario.id).all()
    otros_reclamos = Reclamo.query.filter(Reclamo.usuario_id != usuario.id).all()
    return render_template('dashboard.html', user=usuario, reclamos=mis_reclamos, otros=otros_reclamos)

@app.route('/crear_reclamo', methods=['GET', 'POST'])
@login_required
def crear_reclamo():
    if request.method == 'POST':
        contenido = request.form.get('contenido')
        archivo = request.files.get('foto')
        confirmar_nuevo = request.form.get('confirmar_nuevo')

        nombre_archivo = None
        if archivo and archivo.filename != '':
            nombre_archivo = archivo.filename
            archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo))

        # LÓGICA DE SIMILITUD (EVITA DUPLICADOS)
        historial = {r.id: r for r in Reclamo.query.all()}
        similares_ids = clasificador.buscar_similares(contenido, historial)
        
        if similares_ids and not confirmar_nuevo:
            similar = Reclamo.query.get(similares_ids[0])
            return render_template('crear_reclamo.html', reclamo_similar=similar, contenido_previo=contenido)

        # Si no hay similar o confirmó, se crea
        gestor.crear_reclamo(contenido=contenido, adjunto=nombre_archivo, usuario_id=session['user_id'])
        flash("Reclamo creado con éxito.", "success")
        return redirect(url_for('dashboard'))
        
    return render_template('crear_reclamo.html', reclamo_similar=None)

@app.route('/adherirse/<int:id_reclamo>', methods=['POST'])
@login_required
def adherirse(id_reclamo):
    # Llama a la lógica N:M en gestor.py
    exito = gestor.adherirse_a_reclamo(id_reclamo, session['user_id'])
    if exito:
        flash("¡Te has adherido con éxito!", "success")
    else:
        flash("No puedes adherirte (ya eres autor o ya participas).", "warning")
    return redirect(url_for('dashboard'))

# --- RUTAS DE GESTIÓN (JEFE Y SECRETARIO) ---

@app.route('/derivar_reclamo/<int:id_reclamo>', methods=['POST'])
@login_required
@admin_required
def derivar_reclamo(id_reclamo):
    # Solo el Secretario Técnico suele derivar, o un Jefe que se desentiende
    nuevo_depto = request.form.get('nuevo_depto')
    if gestor.derivar_reclamo(id_reclamo, nuevo_depto):
        flash(f"Reclamo {id_reclamo} derivado a {nuevo_depto}", "success")
    else:
        flash("Error al derivar el reclamo", "danger")
    return redirect(url_for('dashboard'))

@app.route('/gestionar_reclamo/<int:id_reclamo>', methods=['POST'])
@login_required
@admin_required
def gestionar_reclamo(id_reclamo):
    nuevo_estado = request.form.get('estado')
    # CAPTURA DEL PLAZO (1-15 días) - Obligatorio para 'en_proceso'
    tiempo = request.form.get('tiempo', type=int)
    
    if gestor.gestionar_estado_reclamo(id_reclamo, nuevo_estado, tiempo):
        flash(f"Estado actualizado a {nuevo_estado}", "success")
    else:
        flash("Error: El tiempo debe ser de 1 a 15 días para pasar a 'En Proceso'.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/reporte/<formato>')
@login_required
@admin_required
def generar_reporte(formato):
    usuario = Usuario.query.get(session['user_id'])
    # PATRÓN STRATEGY: Escalable para nuevos formatos
    if formato == 'pdf':
        estrategia = ReportePDF()
    else:
        estrategia = ReporteHTML()
        
    reporte_contenido = analitica.generar_reporte(usuario.departamento_id, estrategia)
    return reporte_contenido

# 7. INICIALIZACIÓN DATA-DRIVEN DESDE ARCHIVO
def inicializar_desde_archivo():
    archivo_ruta = 'semillas.json'
    if not os.path.exists(archivo_ruta):
        return

    with open(archivo_ruta, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    # Crear Usuarios de Gestión y Finales
    for u in datos.get('usuarios_gestion', []) + datos.get('usuarios_finales', []):
        if not Usuario.query.filter_by(username=u['username']).first():
            rol = u.get('rol', 'FINAL')
            nuevo = Usuario(username=u['username'], password=u.get('password', '123'),
                            rol_admin=rol, departamento_id=u.get('depto'),
                            nombre=u['nombre'], apellido=u['apellido'])
            db.session.add(nuevo)
    db.session.commit()

    # Cargar Reclamos y Adhesiones si la base está limpia
    if Reclamo.query.count() == 0:
        usuarios_f = Usuario.query.filter_by(rol_admin='FINAL').all()
        mapa_reclamos = {}
        
        for r in datos.get('reclamos_iniciales', []):
            autor = usuarios_f[r['user_idx']]
            nuevo_rec = Reclamo(contenido=r['contenido'], usuario_id=autor.id,
                                estado=r['estado'], departamento_id=r.get('depto'),
                                tiempo_estimado=r.get('tiempo_estimado'))
            db.session.add(nuevo_rec)
            db.session.flush()
            mapa_reclamos[r['id_temp']] = nuevo_rec

        for adh in datos.get('adhesiones_iniciales', []):
            rec = mapa_reclamos.get(adh['reclamo_id_temp'])
            if rec:
                for idx in adh['user_indices']:
                    usuario_que_apoya = usuarios_f[idx]
                    if usuario_que_apoya not in rec.seguidores:
                        rec.seguidores.append(usuario_que_apoya)
        db.session.commit()
    print(">>> Base de Datos inicializada con éxito.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        inicializar_desde_archivo()
    app.run(debug=True)