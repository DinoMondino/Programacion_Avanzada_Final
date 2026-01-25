import os
import sys
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash,  make_response, send_file
import io
from functools import wraps
from datetime import datetime, timezone

app = Flask(__name__)
app.secret_key = 'super_secreto_uner'
basedir = os.path.abspath(os.path.dirname(__file__))

# Importaciones de tus módulos
from modules.usuarios import db, Usuario, RolAdmin
from modules.reclamos import Reclamo, Clasificador, EstadoReclamo
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica, ReporteHTML, ReportePDF

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
            session['rol'] = user.rol_admin.value
            session['depto'] = user.departamento_id
            return redirect(url_for('dashboard'))
        flash("Credenciales incorrectas", "danger")
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Lógica para crear el usuario
        username = request.form.get('username')
        password = request.form.get('password')
        nombre = request.form.get('nombre')
        apellido = request.form.get('apellido')
        
        if Usuario.query.filter_by(username=username).first():
            flash("El usuario ya existe", "danger")
        else:
            # Por defecto los registros web son rol FINAL
            nuevo_usuario = Usuario(
                username=username, 
                password=password, 
                rol_admin='FINAL',
                nombre=nombre,
                apellido=apellido
            )
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash("Cuenta creada. Ya puedes iniciar sesión.", "success")
            return redirect(url_for('login'))
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 5. RUTAS DEL USUARIO FINAL
@app.route('/dashboard')
@login_required
def dashboard():
    usuario = Usuario.query.get(session['user_id'])
    
    # --- Lógica de Admin (Jefe/Secretario) ---
    if usuario.rol_admin.value in ['JEFE', 'SECRETARIO']:
        datos_dash = analitica.obtener_datos_dashboard(usuario.departamento_id)
        depto_str = str(usuario.departamento_id)
        if usuario.departamento_id == 1 or depto_str == 'D_GENERAL' or usuario.rol_admin.value == 'SECRETARIO':
            lista_para_tabla = Reclamo.query.all()
        else:
            # Filtramos estrictamente por el depto del Jefe
            lista_para_tabla = Reclamo.query.filter_by(departamento_id=usuario.departamento_id).all()
        
        return render_template('admin_dashboard.html', 
                               user=usuario, 
                               datos=datos_dash, 
                               reclamos=lista_para_tabla)
    
    # --- Lógica de Estudiante (Usuario Final) ---
    # 1. Sus propios reclamos (aquí sí ve todo, incluso sus resueltos)
    mis_reclamos = Reclamo.query.filter_by(usuario_id=usuario.id).all()
    
    # 2. Reclamos de otros que NO estén resueltos
    otros_reclamos = Reclamo.query.filter(
        Reclamo.usuario_id != usuario.id,
        Reclamo.estado != 'resuelto'
    ).all()
    
    return render_template('user_dashboard.html', 
                           user=usuario, 
                           reclamos=mis_reclamos, 
                           otros=otros_reclamos)

@app.route('/crear_reclamo', methods=['POST'])
@login_required
def crear_reclamo():
    usuario = Usuario.query.get(session['user_id'])
    contenido = request.form.get('contenido')
    confirmado = request.form.get('confirmado')

    # Si el usuario ignoró la advertencia y dio a "Crear Nuevo"
    if confirmado == 'true':
        gestor.crear_reclamo(contenido=contenido, usuario_id=usuario.id)
        flash("Reclamo creado con éxito.", "success")
        return redirect(url_for('dashboard'))

    # Lógica de búsqueda de similares
    historial = {r.id: r for r in Reclamo.query.all()}
    similares_ids = clasificador.buscar_similares(contenido, historial)
    
    if similares_ids:
        similares_objs = Reclamo.query.filter(Reclamo.id.in_(similares_ids)).all()
        
        # Cargamos los datos para que el dashboard no rompa
        mis_reclamos = Reclamo.query.filter_by(usuario_id=usuario.id).all()
        otros_reclamos = Reclamo.query.filter(Reclamo.usuario_id != usuario.id, Reclamo.estado != 'resuelto').all()
        
        # IMPORTANTE: Pasamos una variable para forzar la pestaña activa en el HTML
        return render_template('user_dashboard.html', 
                               user=usuario, 
                               reclamos=mis_reclamos, 
                               otros=otros_reclamos,
                               reclamos_similares=similares_objs, 
                               contenido_pendiente=contenido,
                               mostrar_similares=True) # <--- Variable nueva

    # Si no hay similares, crear directamente
    gestor.crear_reclamo(contenido=contenido, usuario_id=usuario.id)
    flash("Reclamo enviado correctamente.", "success")
    return redirect(url_for('dashboard'))

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
    reclamo = Reclamo.query.get_or_404(id_reclamo)
    nuevo_estado = request.form.get('estado')
    tiempo = request.form.get('tiempo', type=int)
    
    # 1. Si el estado es resuelto, calculamos la métrica ANTES de guardar
    if nuevo_estado == 'resuelto':
        fecha_hoy = datetime.now(timezone.utc)
        # Aseguramos que ambos sean naive (sin timezone) para la resta
        f_creacion = reclamo.fecha_creacion.replace(tzinfo=None)
        f_ahora = fecha_hoy.replace(tzinfo=None)
        
        diferencia = f_ahora - f_creacion
        # Guardamos la duración real para la Analítica
        reclamo.tiempo_resolucion = max(1, diferencia.days)

    # 2. Usamos tu lógica de gestor para validar y guardar
    if gestor.gestionar_estado_reclamo(id_reclamo, nuevo_estado, tiempo):
        # El gestor ya debería hacer el commit, pero si no, asegúralo aquí:
        db.session.commit()
        flash(f"Estado actualizado a {nuevo_estado}", "success")
    else:
        flash("Error: El tiempo debe ser de 1 a 15 días para pasar a 'En Proceso'.", "danger")
        
    return redirect(url_for('dashboard'))

@app.route('/reporte/<formato>')
@login_required
@admin_required
def generar_reporte(formato):
    usuario = Usuario.query.get(session['user_id'])
    
    # 1. Seleccionamos la estrategia
    if formato == 'pdf':
        estrategia = ReportePDF()
    else:
        estrategia = ReporteHTML()
        
    # 2. Generamos el contenido (puede ser string HTML o bytes PDF)
    reporte_contenido = analitica.generar_reporte(usuario.departamento_id, estrategia)

    # 3. Manejo diferenciado según el formato
    if formato == 'pdf':
        # Usamos send_file para enviar los bytes como un archivo descargable
        return send_file(
            io.BytesIO(reporte_contenido),
            mimetype='application/pdf',
            as_attachment=True, # Esto fuerza la descarga
            download_name=f'Reporte_{usuario.departamento_id}.pdf'
        )
    
    # Si es HTML, simplemente lo mostramos en el navegador
    return reporte_contenido

# 7. INICIALIZACIÓN DATA-DRIVEN DESDE ARCHIVO
def inicializar_desde_archivo():
    with app.app_context():
        # 1. Limpieza preventiva (opcional para pruebas)
        # db.drop_all() 
        # db.create_all()

        if not os.path.exists('semillas.json'):
            return

        with open('semillas.json', 'r', encoding='utf-8') as f:
            datos = json.load(f)

        # 2. Carga de Usuarios
        for u in datos.get('usuarios_gestion', []) + datos.get('usuarios_finales', []):
            if not Usuario.query.filter_by(username=u['username']).first():
                # Forzamos el valor del enum desde el string del JSON
                nuevo = Usuario(
                    username=u['username'],
                    password=u.get('password', '123'),
                    rol_admin=u.get('rol', 'FINAL'), 
                    departamento_id=u.get('depto'),
                    nombre=u['nombre'],
                    apellido=u['apellido']
                )
                db.session.add(nuevo)
        
        db.session.commit() # GUARDAMOS PRIMERO
        print(">>> Usuarios guardados correctamente.")

        # 3. Carga de Reclamos
        if Reclamo.query.count() == 0:
            # Buscamos los usuarios finales que acabamos de crear
            todos = Usuario.query.all()
            usuarios_f = [u for u in todos if "FINAL" in str(u.rol_admin)]
            
            print(f">>> Usuarios finales detectados para asignar: {len(usuarios_f)}")
            
            if len(usuarios_f) == 0:
                print(">>> ERROR: No hay usuarios finales para asignar reclamos.")
                return

            mapa_reclamos = {}
            for r in datos.get('reclamos_iniciales', []):
                idx = r['user_idx']
                if idx < len(usuarios_f):
                    autor = usuarios_f[idx]
                    nuevo_rec = Reclamo(
                        contenido=r['contenido'],
                        usuario_id=autor.id,
                        estado=r['estado'],
                        departamento_id=r.get('depto'),
                        tiempo_estimado=r.get('tiempo_estimado'),
                        adjunto_url=r.get('adjunto_url')
                    )
                    db.session.add(nuevo_rec)
                    db.session.flush()
                    mapa_reclamos[r['id_temp']] = nuevo_rec
                else:
                    print(f">>> Advertencia: user_idx {idx} fuera de rango.")

            # 4. Adhesiones
            for adh in datos.get('adhesiones_iniciales', []):
                rec = mapa_reclamos.get(adh['reclamo_id_temp'])
                if rec:
                    for u_idx in adh['user_indices']:
                        if u_idx < len(usuarios_f):
                            rec.seguidores.append(usuarios_f[u_idx])
            
            db.session.commit()
            print(">>> Reclamos y Adhesiones cargados con éxito.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        inicializar_desde_archivo()
    app.run(debug=True)