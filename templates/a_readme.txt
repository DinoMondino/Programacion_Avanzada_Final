Estos archivos son Templates de Jinja2, combinan código HTML estático con lógica de Python para mostrar datos dinámicos.

1. base.html (estructura global)
Contiene los elementos que se repiten en todas las páginas para mantener la coherencia visual.
Barra de Navegación: Incluye el título del sistema y los enlaces de acceso.
Gestión de Alertas: Utiliza el sistema de flash de Flask para mostrar mensajes de éxito o error.
Estilos y Scripts: Carga Bootstrap, Bootstrap Icons y define el pie de página (footer).
Bloques ({% block %}): Define los espacios donde las otras páginas insertarán su contenido específico.

2. index.html (Portal de Login)
Presenta un formulario para que el usuario ingrese su nombre de usuario y contraseña.
Incluye un botón de acceso directo para ir a la página de registro si el usuario es nuevo.

3. register.html (Registro de usuarios)
Permite a los nuevos usuarios darse de alta en la base de datos.
Solicita datos básicos: usuario, contraseña, nombre, apellido.
Claustro: Incluye un selector para categorizar al usuario como Estudiante, Docente o PAyS (Personal de Apoyo y Servicios).

4. user_dashboard.html (Panel principal del Estudiante/Docente)
Es el centro de control para el usuario final. Está organizado en tres pestañas (tabs):
Crear Reclamo: Contiene el formulario para describir problemas.
Incluye la lógica de Detección de Similares: si el sistema encuentra un reclamo parecido, 
muestra una alerta amarilla permitiendo al usuario "Adherirse" al existente en lugar de crear uno nuevo.
Mis Reclamos: Una tabla con el historial personal del usuario, mostrando el estado actual y la fecha.
Listar Todos: Una vista de los reclamos públicos de la facultad donde el usuario puede ver qué reportaron otros
y usar el botón "Apoyar" para sumar su adhesión.

5. admin_dashboard.html (Panel para Jefes y Secretarios)
Es la herramienta de gestión para el personal administrativo. Se divide en dos áreas:
Analítica y Reportes: Muestra gráficos estadísticos (Chart.js) sobre la distribución de estados y una Nube de Palabras Clave generada automáticamente por la clase Analitica.
Gestión de Reclamos: Una tabla interactiva donde el administrador puede:
Cambiar el estado de un reclamo mediante un selector.
Ver la lista de personas que apoyan cada pedido en un modal (ventana flotante).
Derivar: (Solo para el Secretario) Cambiar el departamento responsable del reclamo.
Descargar toda la información en formato CSV (Excel).

6. crear_reclamo.html (Vista alterna de creación)
Es una versión simplificada y enfocada específicamente en el proceso de creación de un nuevo reclamo.
Se activa principalmente cuando el sistema detecta una similitud y necesita que el usuario
confirme si desea seguir adelante con su publicación o adherirse al anterior.
Tiene un diseño visualmente fuerte para resaltar la alerta de "Reclamo Parecido".
