from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, make_response
from functools import wraps
import io
import datetime
import sys
# Se importa la clase 'Usuario' para el hasheo de contraseñas
from modules.usuarios import UsuarioFinal, JefeDepartamento, SecretarioTecnico, Claustro, RolAdmin, UsuarioAdmin, EstadoReclamo, Usuario
from modules.reclamos import Clasificador, Reclamo
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica

# --- 1. Inicialización y Configuración de Flask ---

app = Flask(__name__)
# Necesario para usar 'session' y 'flash'
app.secret_key = 'super_secreto_uner' 

# Definición de Stopwords (se usan en Clasificador)
STOPWORDS = ["el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "de", "a", "en", "es", "para", "que", "del", "al", "se", "con"]

# --- 2. Inicialización de Servicios y Base de Datos (Simulada) ---

# Servicios
clasificador = Clasificador(stopwords=STOPWORDS)
gestor_reclamos = Gestor_Reclamos(clasificador_servicio=clasificador)
analitica = Analitica(gestor_servicio=gestor_reclamos)

# Base de datos de Usuarios (Simulada: {username: user_object})
_DB_USERS = {}
# Mapeo de IDs de Departamento a Nombres para mostrar en la UI
_DB_DEPARTMENTS = Clasificador.DEPARTAMENTOS_MAP

# --- 3. Mock Data (Datos de Prueba para Iniciar) ---

def initialize_mock_data():
    """Crea usuarios iniciales (Admin y Final) y algunos reclamos de ejemplo."""
    
    # CORRECCIÓN CLAVE: Hashear la contraseña de prueba UNA SOLA VEZ
    try:
        MOCK_PASS_HASH = Usuario._hash_password("1234")
    except AttributeError:
        # Esto ocurre si el método _hash_password no existe o no es estático en Usuario
        print("\n[ERROR CRÍTICO] Asegúrate de que Usuario._hash_password(\"1234\") sea un método estático válido en usuarios.py.", file=sys.stderr)
        sys.exit(1)
    
    # 3.1. Usuarios Administradores (Alta a nivel de sistema - RF 53)
    
    # Jefe de Infraestructura
    jd_infra = JefeDepartamento("J001", "jefe.infra@uner.ar", "jinfra", MOCK_PASS_HASH, "Juan", "Perez", 
                                Claustro.PAYS, 
                                "D_INFRAESTRUCTURA", gestor_reclamos, analitica)
    _DB_USERS[jd_infra.usuario] = jd_infra
    
    # Jefe de Informática
    jd_info = JefeDepartamento("J002", "jefe.info@uner.ar", "jinfo", MOCK_PASS_HASH, "Maria", "Gomez", 
                                Claustro.PAYS, 
                                "D_INFORMATICA", gestor_reclamos, analitica)
    _DB_USERS[jd_info.usuario] = jd_info

    # Secretaria Técnica
    st = SecretarioTecnico("S001", "secre.tec@uner.ar", "stec", MOCK_PASS_HASH, "Ana", "Lopez", 
                           Claustro.PAYS, 
                           gestor_reclamos, analitica)
    _DB_USERS[st.usuario] = st
    
    # 3.2. Usuarios Finales
    
    uf_estudiante = UsuarioFinal("UF001", "estudiante@uner.ar", "user_est", MOCK_PASS_HASH, "Pedro", "García", 
                                Claustro.ESTUDIANTE, gestor_reclamos)
    _DB_USERS[uf_estudiante.usuario] = uf_estudiante
    
    uf_docente = UsuarioFinal("UF002", "docente@uner.ar", "user_doc", MOCK_PASS_HASH, "Laura", "Díaz", 
                             Claustro.DOCENTE, gestor_reclamos)
    _DB_USERS[uf_docente.usuario] = uf_docente
    
    # 3.3. Reclamos Iniciales
    
    # Reclamo PENDIENTE (Infraestructura)
    gestor_reclamos._reclamos_db["R001"] = Reclamo(
        id_reclamo="R001", contenido="La gotera en el aula 3 sigue empeorando.", 
        usuario_creator_id="UF001", departamento_id="D_INFRAESTRUCTURA", 
        estado=EstadoReclamo.PENDIENTE, palabras_clave=["gotera", "aula"],
        fecha_creacion=datetime.datetime.now() - datetime.timedelta(days=5)
    )
    # Reclamo RESUELTO (Informática)
    gestor_reclamos._reclamos_db["R002"] = Reclamo(
        id_reclamo="R002", contenido="Problema con el WIFI en el pasillo principal. Anda muy lento.", 
        usuario_creator_id="UF002", departamento_id="D_INFORMATICA", 
        estado=EstadoReclamo.RESUELTO, palabras_clave=["wifi", "lento"],
        adherentes_ids=["UF001"],
        fecha_creacion=datetime.datetime.now() - datetime.timedelta(days=10)
    )
    # Reclamo EN PROCESO (Secretaría)
    gestor_reclamos._reclamos_db["R003"] = Reclamo(
        id_reclamo="R003", contenido="Necesito cambiar el horario de mi asignatura de cálculo.", 
        usuario_creator_id="UF001", departamento_id="D_SECRETARIA", 
        estado=EstadoReclamo.EN_PROCESO, palabras_clave=["cambiar", "horario", "asignatura"],
        fecha_creacion=datetime.datetime.now() - datetime.timedelta(days=2)
    )
    gestor_reclamos._next_reclamo_id = 4
    print("[INIT] Datos de prueba cargados. Usuarios: jinfra, jinfo, stec, user_est, user_doc (pass: 1234).")


# Ejecutar la inicialización
try:
    initialize_mock_data()
except TypeError as e:
    # Captura el error en la consola si persiste
    print(f"\n[ERROR CRÍTICO EN MOCK DATA] Falló la inicialización de usuarios: {e}", file=sys.stderr)
    print("Por favor, revisa el constructor de las clases en 'usuarios.py' y asegúrate de que llamen a super().__init__(...) con todos los argumentos requeridos.", file=sys.stderr)
    sys.exit(1)


# --- 4. Funciones de Ayuda (Autenticación) ---

def get_current_user():
    """Retorna el objeto Usuario logueado o None."""
    user_id = session.get('user_id')
    if user_id:
        # Busca el usuario por ID
        for user in _DB_USERS.values():
            if user.id == user_id:
                return user
    return None

def login_required(f):
    """Decorador para requerir que el usuario esté autenticado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if get_current_user() is None:
            flash("Necesitas iniciar sesión para acceder a esta página.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_type):
    """Decorador para requerir un rol específico (e.g., UsuarioAdmin, UsuarioFinal)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if user is None:
                flash("Necesitas iniciar sesión.", "danger")
                return redirect(url_for('index'))
            if not isinstance(user, role_type):
                flash("No tienes permiso para acceder a esta sección.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- 5. Rutas de la Aplicación ---

# 5.1. Autenticación y Registro

@app.route('/')
def index():
    """Página de inicio (Login)"""
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    """Maneja el inicio de sesión para todos los roles."""
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = _DB_USERS.get(username)
    
    # El método login de Usuario (clase base) debería manejar la comparación de contraseña
    if user and user.login(username, password, _DB_USERS):
        session['user_id'] = user.id
        flash(f"Bienvenido/a, {user.nombre}.", "success")
        
        # Redirección basada en rol
        if isinstance(user, UsuarioAdmin):
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_menu'))
    else:
        # Si el login falla, flashea un mensaje y redirige al inicio
        flash("Usuario o contraseña incorrectos.", "danger")
        return redirect(url_for('index'))

@app.route('/register')
def register():
    """Muestra el formulario de registro (RF 31)"""
    # Pasamos las claves del Claustro Enum para usarlas como valor en el HTML
    claustros = [m.name for m in Claustro]
    return render_template('register.html', claustros=claustros, Claustro=Claustro)

@app.route('/register_post', methods=['POST'])
def register_post():
    """Procesa el formulario de registro (RF 31)"""
    
    # 1. Obtener y validar el Claustro
    claustro_key = request.form.get('claustro')
    if not claustro_key:
        flash("Error: Debes seleccionar un claustro.", "danger")
        return redirect(url_for('register'))
        
    try:
        # Obtener la instancia del Enum Claustro
        claustro_instance = Claustro[claustro_key.upper()] 
    except KeyError:
        flash(f"Error: La opción de claustro '{claustro_key}' no es válida.", "danger")
        return redirect(url_for('register'))
        
    data = {
        "nombre": request.form.get('nombre'),
        "apellido": request.form.get('apellido'),
        "email": request.form.get('email'),
        "usuario": request.form.get('usuario'),
        "claustro": claustro_instance,
        "contrasenia": request.form.get('contrasenia'),
        "contrasenia_repetida": request.form.get('contrasenia_repetida')
    }
    
    # 2. Validar unicidad de usuario/email y coincidencia de contraseñas
    new_user_data = UsuarioFinal.registro_usuario(_DB_USERS, **data)
    
    if not new_user_data:
        # El mensaje flash se usa para dar feedback al usuario, incluso si ya se imprimió en consola.
        flash("Error en el registro. Verifica que las contraseñas coincidan y que el email/usuario no existan.", "danger")
        return redirect(url_for('register'))

    # 3. Crear y guardar el nuevo usuario
    
    # A. Generar un ID para el nuevo usuario (Secuencial simulado)
    new_user_id = f"UF{len(_DB_USERS) + 1:03d}"
    
    # B. Preparar los datos para el constructor
    contrasenia_hash = new_user_data.pop('contrasenia_hash', None)
    if 'id' in new_user_data:
        del new_user_data['id']
        
    if not contrasenia_hash:
        flash("Error: No se pudo generar el hash de contraseña.", "danger")
        return redirect(url_for('register'))

    # C. Crear la instancia de UsuarioFinal
    try:
        new_user = UsuarioFinal(
            id_usuario=new_user_id,
            email=new_user_data.get('email'),
            usuario=new_user_data.get('usuario'),
            contrasenia_hash=contrasenia_hash,
            nombre=new_user_data.get('nombre'),
            apellido=new_user_data.get('apellido'),
            claustro=new_user_data.get('claustro'),
            gestor_servicio=gestor_reclamos
        )
    except TypeError as e:
        print(f"[ERROR CRÍTICO AL CREAR USUARIO] Tipo de error: {e}", file=sys.stderr)
        flash("Error interno al crear la cuenta. Los argumentos del constructor no coinciden.", "danger")
        return redirect(url_for('register'))
        
    # D. Guardar el nuevo usuario en la DB simulada
    _DB_USERS[new_user.usuario] = new_user
    
    flash("¡Registro exitoso! Ya puedes iniciar sesión.", "success")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.pop('user_id', None)
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for('index'))

# 5.2. Rutas de Usuario Final

@app.route('/user_menu')
@role_required(UsuarioFinal)
def user_menu():
    """Menú principal del usuario final (RF 32)"""
    user = get_current_user()
    return render_template('user_menu.html', current_user=user)

@app.route('/crear_reclamo')
@role_required(UsuarioFinal)
def crear_reclamo():
    """Muestra el formulario para crear un reclamo (RF 35)"""
    return render_template('reclamo_form.html')

@app.route('/crear_reclamo_post', methods=['POST'])
@role_required(UsuarioFinal)
def crear_reclamo_post():
    """Procesa el formulario y clasifica/crea/adhiere el reclamo (RF 37-43)"""
    user = get_current_user()
    contenido = request.form.get('contenido')
    adjunto_url = request.form.get('adjunto_url')

    # El método crear_reclamo de UsuarioFinal debe retornar un STRING de estado.
    result_message = user.crear_reclamo(contenido, adjunto_url) 
    
    # Lógica de manejo de mensajes:
    if "Adherido a reclamo" in result_message:
        # RF 43 - El reclamo se descartó y se adhirió al similar
        flash("Adherido a reclamo similar ya existente. Tu reclamo se ha descartado para evitar duplicados.", "warning") 
    elif "Reclamo creado" in result_message:
        # RF 42 - Reclamo creado como nuevo
        # Asumimos que el mensaje es: "Reclamo creado exitosamente: R00X"
        flash(f"{result_message} y pendiente de revisión por el departamento clasificado.", "success") 
    elif "Error" in result_message:
        # Caso de error
        flash(f"Error al crear el reclamo: {result_message}", "danger")
    else:
        # Caso de mensaje inesperado (debería ser handled por el 'Error' arriba)
        flash("Procesamiento de reclamo finalizado, verifica el estado en tus reclamos.", "info")
        
    return redirect(url_for('user_menu'))


@app.route('/listar_reclamos')
@role_required(UsuarioFinal)
def listar_reclamos():
    """Muestra todos los reclamos pendientes con opción de filtro por departamento (RF 33-34)"""
    user = get_current_user()
    depto_id = request.args.get('depto_id', default=None, type=str)
    
    reclamos = user.listar_reclamos_pendientes(depto_id)

    # Convertir reclamos a formato de diccionario para el template
    listado_info = []
    for r in reclamos:
        # Asegúrate de que r.departamento_id esté en _DB_DEPARTMENTS
        depto_nombre = _DB_DEPARTMENTS.get(r.departamento_id, r.departamento_id) 
        
        listado_info.append({
            "ID": r.id,
            "Estado": r.estado.value,
            "Fecha": r.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
            "Contenido": r.contenido[:80] + "...", # Mostrar un extracto
            "Departamento": depto_nombre,
            "Adherentes": r.get_num_adherentes(),
            # Solo se puede adherir si no es el creador y no está adherido
            "Puede_Adherirse": user.id != r.usuario_creator_id and user.id not in r.adherentes_ids and r.estado == EstadoReclamo.PENDIENTE
        })

    return render_template('lista_reclamos.html',
                           titulo_listado="Listado de Reclamos Pendientes Globales",
                           reclamos=listado_info,
                           departamentos=_DB_DEPARTMENTS, # Para el filtro
                           filtro_actual=depto_id,
                           es_listado_global=True)

@app.route('/adherirse_reclamo', methods=['POST'])
@role_required(UsuarioFinal)
def adherirse_reclamo():
    """Maneja la adhesión a un reclamo existente (RF 34)"""
    user = get_current_user()
    reclamo_id = request.form.get('reclamo_id')
    
    exito, mensaje = gestor_reclamos.adherirse_a_reclamo(reclamo_id, user.id)
    
    if exito:
        flash(f"Adherido exitosamente al reclamo {reclamo_id}.", "success")
    else:
        flash(f"Error al adherirse: {mensaje}", "danger")
        
    return redirect(url_for('listar_reclamos'))

@app.route('/ver_mis_reclamos')
@role_required(UsuarioFinal)
def ver_mis_reclamos():
    """Muestra los reclamos creados o adheridos por el usuario (RF 44-45)"""
    user = get_current_user()
    mis_reclamos = user.ver_mis_reclamos()
    
    listado_info = []
    for r in mis_reclamos:
        depto_nombre = _DB_DEPARTMENTS.get(r.departamento_id, r.departamento_id) 
        
        listado_info.append({
            "ID": r.id,
            "Estado": r.estado.value,
            "Fecha": r.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
            "Contenido": r.contenido[:80] + "...",
            "Departamento": depto_nombre,
            "Adherentes": r.get_num_adherentes(),
            "Es_Creador": user.id == r.usuario_creator_id # Informar si es el creador
        })
        
    return render_template('lista_reclamos.html',
                           titulo_listado="Mis Reclamos y Seguimiento",
                           reclamos=listado_info,
                           es_listado_global=False) # Para ocultar opciones de filtro/adhesión

# 5.3. Rutas de Administradores (Jefes y Secretario)

@app.route('/admin_dashboard')
@role_required(UsuarioAdmin)
def admin_dashboard():
    """Muestra el dashboard para Jefes de Departamento y Secretario Técnico (RF 46-48)"""
    user = get_current_user()
    # Este método DEBE existir en las clases de Admin para retornar su depto o "ALL"
    depto_id = user.get_departamento_id()
    
    # Determinar qué reclamos mostrar
    if depto_id == "ALL":
        # Secretario ve todos los reclamos
        reclamos_del_depto = list(gestor_reclamos._reclamos_db.values()) 
        # Analítica para el Secretario (ejemplo de analítica general)
        analitica_data = analitica.ver_estadisticas_generales() 
    else:
        # Jefe ve solo los de su departamento
        reclamos_del_depto = gestor_reclamos.get_reclamos_por_departamento(depto_id)
        # Este método DEBE existir en JefeDepartamento (o su Mixin)
        analitica_data = user.ver_analitica(depto_id) 

    # Mapeo de reclamos para la tabla del dashboard
    reclamos_map = [
        {
            "id": r.id,
            "usuario_creator_id": r.usuario_creator_id,
            "fecha_creacion": r.fecha_creacion.strftime('%Y-%m-%d %H:%M'),
            "contenido": r.contenido[:100] + "...",
            "estado": r.estado,
            "get_num_adherentes": r.get_num_adherentes()
        } for r in reclamos_del_depto
    ]
    
    return render_template('admin_dashboard.html',
                           current_user=user,
                           reclamos_del_depto=reclamos_map,
                           analitica_data=analitica_data,
                           estados_posibles=[e.name for e in EstadoReclamo], # Nombres de estados para el selector
                           todos_los_deptos=_DB_DEPARTMENTS)


@app.route('/actualizar_estado_reclamo', methods=['POST'])
@role_required(UsuarioAdmin)
def actualizar_estado_reclamo():
    """Maneja la actualización del estado de un reclamo (RF 57)"""
    user = get_current_user()
    reclamo_id = request.form.get('reclamo_id')
    nuevo_estado_str = request.form.get('nuevo_estado')
    
    try:
        nuevo_estado = EstadoReclamo[nuevo_estado_str]
    except KeyError:
        flash("Estado inválido.", "danger")
        return redirect(url_for('admin_dashboard'))
    
    # Este método DEBE existir en las clases Admin (o su Mixin)
    if user.actualizar_estado_reclamo(reclamo_id, nuevo_estado): 
        flash(f"Estado del reclamo {reclamo_id} actualizado a {nuevo_estado.value}.", "success")
    else:
        flash(f"Error: No se pudo actualizar el estado del reclamo {reclamo_id} o no tienes permiso.", "danger")
        
    return redirect(url_for('admin_dashboard'))

@app.route('/derivar_reclamo', methods=['POST'])
@role_required(SecretarioTecnico)
def derivar_reclamo():
    """Permite al Secretario Técnico derivar un reclamo (RF 60)"""
    user = get_current_user()
    reclamo_id = request.form.get('reclamo_id')
    nuevo_depto_id = request.form.get('nuevo_depto_id')
    
    if nuevo_depto_id not in _DB_DEPARTMENTS:
        flash("Error: Departamento destino inválido.", "danger")
        return redirect(url_for('admin_dashboard'))
        
    # Este método DEBE existir en SecretarioTecnico (o su Mixin)
    if user.derivar_reclamo(reclamo_id, nuevo_depto_id): 
        flash(f"Reclamo {reclamo_id} derivado exitosamente al departamento {_DB_DEPARTMENTS[nuevo_depto_id]}.", "success")
    else:
        flash(f"Error: No se pudo derivar el reclamo {reclamo_id}. Verifica el ID.", "danger")
        
    return redirect(url_for('admin_dashboard'))

@app.route('/generar_reporte', methods=['POST'])
@role_required(UsuarioAdmin)
def generar_reporte():
    """Genera el reporte de estado y gráficas estadísticas (RF 59)"""
    user = get_current_user()
    formato = request.form.get('formato')
    # Jefe depto solo puede generar de su depto, Secretario puede elegir
    depto_id_form = request.form.get('departamento_id')
    
    # Determinar el ID de departamento a reportar
    if user.get_departamento_id() == "ALL":
        # Secretario Técnico puede elegir
        depto_id_reporte = depto_id_form
    else:
        # Jefe de Departamento solo puede reportar el suyo
        depto_id_reporte = user.get_departamento_id()

    
    # Este método DEBE existir en las clases Admin (o su Mixin)
    reporte_content = user.generar_reporte(depto_id_reporte, formato) 
    
    if "Error" in reporte_content:
        flash(f"Error al generar el reporte: {reporte_content}", "danger")
        return redirect(url_for('admin_dashboard'))

    depto_nombre_reporte = _DB_DEPARTMENTS.get(depto_id_reporte, "General")
    filename = f"Reporte_Reclamos_{depto_nombre_reporte}_{formato.upper()}"
    
    if formato.upper() == "HTML":
        # Generar una respuesta directa con el contenido HTML
        response = make_response(reporte_content)
        response.headers["Content-Disposition"] = f"attachment; filename={filename}.html"
        response.headers["Content-type"] = "text/html"
        return response
    
    elif formato.upper() == "PDF":
        # Simulación de archivo PDF (solo devolvemos un archivo de texto para demostrar la ruta)
        # NOTA: En una aplicación real, usarías una librería para generar un binario PDF real aquí.
        
        # Contenido simulado para el PDF
        pdf_simulado = f"""
        --- REPORTE PDF SIMULADO ---
        Título: {depto_nombre_reporte}
        Generado por: {user.nombre} {user.apellido}
        Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Contenido resumido:
        {reporte_content}
        ----------------------------
        """
        
        return send_file(
            io.BytesIO(pdf_simulado.encode('utf-8')), # El contenido simulado en bytes
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{filename}.pdf'
        )

    flash("Formato de reporte no válido.", "danger")
    return redirect(url_for('admin_dashboard'))


# --- 6. Ejecución del Servidor ---

if __name__ == '__main__':
    # Nota: Asegúrate de tener una carpeta 'templates' y 'static' configuradas.
    app.run(debug=True)