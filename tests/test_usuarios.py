import unittest
from typing import Dict, Any, List, Optional
from modules.reclamos import Clasificador, EstadoReclamo, Reclamo
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica
# Se importa UsuarioBase para usarla como clase concreta (solución al TypeError)
from modules.usuarios import UsuarioFinal, JefeDepartamento, SecretarioTecnico, Claustro, RolAdmin, Usuario, UsuarioBase 

# Stopwords de prueba y constantes
TEST_STOPWORDS = ["el", "la", "de", "un", "una", "y", "o", "es", "en", "por"]
DEPARTAMENTO_INF = "D_INFRAESTRUCTURA"
DEPARTAMENTO_IT = "D_INFORMATICA"
DEPARTAMENTO_SEC = "D_SECRETARIA"


class MockGestorReclamos:
    """Mock básico para simular el Gestor de Reclamos en pruebas de UsuarioFinal y Admin."""
    def __init__(self):
        # Base de datos inicial, incluyendo adherentes para R999 para la prueba
        self._reclamos_db: Dict[str, Reclamo] = {
            "R999": Reclamo("R999", "Reclamo PENDIENTE INFRA", "J1", DEPARTAMENTO_INF, EstadoReclamo.PENDIENTE, adherentes_ids=['U_ADH']), 
            "R888": Reclamo("R888", "Reclamo RESUELTO IT", "J2", DEPARTAMENTO_IT, EstadoReclamo.RESUELTO, adherentes_ids=[]),
            "R666": Reclamo("R666", "Reclamo PENDIENTE IT", "J3", DEPARTAMENTO_IT, EstadoReclamo.PENDIENTE, adherentes_ids=[]), 
        }
    
    def get_reclamo(self, reclamo_id: str) -> Optional[Reclamo]:
        return self._reclamos_db.get(reclamo_id)

    def crear_reclamo(self, contenido: str, adjunto: Optional[str], usuario_id: str) -> Dict[str, Any]:
        if "wifi" in contenido:
            # Simula que R999 es similar
            return {"creado": False, "mensaje": "Similares encontrados.", "similares": [self._reclamos_db["R999"]]}
        return {"creado": True, "id": "R0001"}

    def adherirse_a_reclamo(self, reclamo_id: str, usuario_id: str) -> bool:
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo and usuario_id not in reclamo.adherentes_ids:
            reclamo.adherentes_ids.append(usuario_id)
            print(f"   [NOTIFICACION] -> Usuario {usuario_id}: Te has adherido al reclamo {reclamo_id}: '{reclamo.contenido[:20]}...'")
            return True # Éxito
        return False # Ya adherido o no existe
    
    def get_reclamos_pendientes_filtrados(self, depto_id: Optional[str] = None) -> List[Reclamo]:
        reclamos_pendientes = [
            r for r in self._reclamos_db.values() 
            if r.estado == EstadoReclamo.PENDIENTE
        ]
        
        if depto_id:
            return [r for r in reclamos_pendientes if r.departamento_id == depto_id]
        
        return reclamos_pendientes

    def gestionar_reclamo(self, reclamo_id: str, nuevo_estado: EstadoReclamo, usuario_id: str, respuesta: Optional[str] = None) -> bool:
        reclamo = self.get_reclamo(reclamo_id)
        # La validación de permiso debe estar en el JefeDepartamento, no aquí, para el mock.
        if reclamo:
            # Simulación de validación simple de que el Jefe solo toca su Dpto
            if usuario_id.startswith('J') and reclamo.departamento_id != self.get_usuario_depto(usuario_id):
                 # Esto simula el error de permiso que se ve en la salida BIO
                 print(f"[Jefe de Departamento ({self.get_usuario_depto(usuario_id)})] ERROR de Permiso: Reclamo {reclamo_id} no pertenece a su Dpto. ({self.get_usuario_depto(usuario_id)}).")
                 return False
                 
            print(f"[MockGestor] Reclamo {reclamo_id} gestionado por {usuario_id} a estado {nuevo_estado.value}")
            reclamo.estado = nuevo_estado
            return True
        return False
        
    def get_usuario_depto(self, usuario_id: str) -> Optional[str]:
        # Para el mock, asumimos J1 es de INF y S1 no tiene depto fijo
        if usuario_id == "J1":
            return DEPARTAMENTO_INF
        return None


    def derivar_reclamo(self, reclamo_id: str, nuevo_depto_id: str) -> bool:
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            print(f"[MockGestor] Reclamo {reclamo_id} derivado a {nuevo_depto_id}")
            reclamo.departamento_id = nuevo_depto_id
            return True
        return False

    def get_mis_reclamos(self, usuario_id: str) -> List[Reclamo]:
        # Retorna reclamos creados O adheridos
        mis_creados = [r for r in self._reclamos_db.values() if r.usuario_creator_id == usuario_id]
        mis_adheridos = [r for r in self._reclamos_db.values() if usuario_id in r.adherentes_ids]
        
        all_ids = {r.id for r in mis_creados} | {r.id for r in mis_adheridos}
        return [self._reclamos_db[id_] for id_ in all_ids]


class MockAnalitica:
    """Mock para simular el servicio de Analítica."""
    def get_estadisticas_generales(self, depto_id: Optional[str]) -> Dict[str, Any]:
        return {"total": 3, "pendientes": 2, "resueltos": 1}
    
    def generar_reporte_departamento(self, depto_id: str, reporte_tipo: str) -> str:
        return f"Reporte Dpto. {depto_id} - Tipo: {reporte_tipo}"

    def generar_reporte_global(self, reporte_tipo: str) -> str:
        return f"Reporte GLOBAL - Tipo: {reporte_tipo}"


# --- Pruebas de Usuario Final ---

class TestUsuarioFinal(unittest.TestCase):
    """Pruebas para la clase UsuarioBase (implementación concreta de UsuarioFinal)."""

    def setUp(self):
        self.gestor_mock = MockGestorReclamos()
        # CORRECCIÓN DE TYPERROR: Usar UsuarioBase
        self.usuario_final = UsuarioBase(
            id_usuario="U10", email="u10@test.com", usuario="u10", contrasenia_hash="hash", 
            nombre="User", apellido="Final", claustro=Claustro.ESTUDIANTE, 
            gestor_servicio=self.gestor_mock
        )
        
    def test_crear_reclamo_exitoso(self):
        """Prueba de creación de reclamo (RF 40)."""
        contenido = "No hay agua en los baños"
        resultado = self.usuario_final.crear_reclamo(contenido, adjunto=None) 
        self.assertTrue(resultado.get("creado"))
        self.assertEqual(resultado.get("id"), "R0001")

    def test_crear_reclamo_similares_encontrados(self):
        """Prueba de creación de reclamo con similares (RF 43)."""
        contenido = "No hay wifi ni internet"
        resultado = self.usuario_final.crear_reclamo(contenido, adjunto=None)
        self.assertFalse(resultado.get("creado"))
        self.assertTrue(resultado.get("similares"))

    def test_adherirse_a_reclamo(self):
        """Prueba de adhesión a reclamo (RF 43)."""
        reclamo_id = "R666" 
        reclamo = self.gestor_mock.get_reclamo(reclamo_id)
        num_adherentes_inicial = len(reclamo.adherentes_ids) 
        
        self.assertTrue(self.usuario_final.adherirse_a_reclamo(reclamo_id))
        
        reclamo = self.gestor_mock.get_reclamo(reclamo_id)
        self.assertEqual(len(reclamo.adherentes_ids), num_adherentes_inicial + 1)

    def test_adherirse_a_reclamo_inexistente(self):
        """Prueba de adhesión a reclamo inexistente."""
        self.assertFalse(self.usuario_final.adherirse_a_reclamo("R000"))

    def test_adherirse_ya_adherido(self):
        """Prueba de adhesión cuando el usuario ya está adherido."""
        reclamo_id = "R999"
        # 1. Asegurar que U10 esté adherido *antes* de la prueba de re-adhesión
        self.gestor_mock.adherirse_a_reclamo(reclamo_id, self.usuario_final.id)
        reclamo = self.gestor_mock.get_reclamo(reclamo_id)
        num_adherentes_inicial = len(reclamo.adherentes_ids) 

        # 2. Intentar adherirse de nuevo y esperar False
        # CORRECCIÓN DEL ERROR: Ahora U10 ya está adherido, por lo que debe devolver False.
        self.assertFalse(self.usuario_final.adherirse_a_reclamo(reclamo_id))

        # 3. Verificar que el número de adherentes no cambió
        self.assertEqual(len(self.gestor_mock.get_reclamo(reclamo_id).adherentes_ids), num_adherentes_inicial)


    def test_ver_mis_reclamos(self):
        """Prueba de listado de reclamos propios/adheridos (RF 39)."""
        # El método en el Mixin es ver_mis_reclamos
        mis_reclamos = self.usuario_final.ver_mis_reclamos()
        
        # U10 no ha creado ni adherido nada, pero R999 tiene 'U_ADH'
        self.assertEqual(len(mis_reclamos), 0)
        
        # Simular adhesión
        self.gestor_mock.adherirse_a_reclamo("R888", self.usuario_final.id)
        mis_reclamos = self.usuario_final.ver_mis_reclamos()
        self.assertEqual(len(mis_reclamos), 1)

    def test_listar_reclamos_pendientes_final(self):
        """Prueba de listado de reclamos pendientes global (RF 38)."""
        # El método en el Mixin es listar_reclamos_pendientes_final
        pendientes = self.usuario_final.listar_reclamos_pendientes_final()
        self.assertEqual(len(pendientes), 2)
        self.assertTrue(all(r.estado == EstadoReclamo.PENDIENTE for r in pendientes))
        
    def test_final_sin_gestor(self):
        """Prueba de manejo de errores cuando el gestor no está inyectado."""
        # CORRECCIÓN: Usar UsuarioBase
        usuario_sin_gestor = UsuarioBase("U0", "e", "u", "p", "n", "a", Claustro.ESTUDIANTE, None)
        self.assertFalse(usuario_sin_gestor.crear_reclamo("contenido", adjunto=None).get("creado"))
        self.assertFalse(usuario_sin_gestor.adherirse_a_reclamo("R999"))
        self.assertEqual(usuario_sin_gestor.ver_mis_reclamos(), [])
        self.assertEqual(usuario_sin_gestor.listar_reclamos_pendientes_final(), [])


# --- Pruebas de Usuario Admin (JefeDepartamento y SecretarioTecnico) ---

class TestUsuarioAdmin(unittest.TestCase):
    """Pruebas para las clases JefeDepartamento y SecretarioTecnico."""
    
    def setUp(self):
        self.gestor_mock = MockGestorReclamos()
        self.analitica_mock = MockAnalitica()
        
        self.jefe_inf = JefeDepartamento(
            id_usuario="J1", email="j1@test.com", usuario="j1", contrasenia_hash="hash",
            nombre="Jefe", apellido="Infra", claustro=Claustro.PAYS, 
            departamento_id=DEPARTAMENTO_INF,
            gestor_servicio=self.gestor_mock, analitica_servicio=self.analitica_mock
        )
        
        self.secretario = SecretarioTecnico(
            id_usuario="S1", email="s1@test.com", usuario="s1", contrasenia_hash="hash",
            nombre="Secretario", apellido="Tecnico", claustro=Claustro.DOCENTE, 
            gestor_servicio=self.gestor_mock, analitica_servicio=self.analitica_mock
        )

    # --- Tests de Jefe de Departamento ---

    def test_jefe_listar_reclamos_pendientes_propios_depto(self):
        """Jefe puede listar solo reclamos pendientes de su departamento (RF 41)."""
        # Jefe usa listar_reclamos_pendientes_admin()
        pendientes = self.jefe_inf.listar_reclamos_pendientes_admin()
        self.assertEqual(len(pendientes), 1) 
        self.assertEqual(pendientes[0].departamento_id, DEPARTAMENTO_INF)

    def test_jefe_actualizar_estado_reclamo_propio(self):
        """Jefe puede actualizar el estado de un reclamo de su departamento (RF 41)."""
        reclamo_id = "R999" # INF
        self.assertTrue(self.jefe_inf.gestionar_reclamo(reclamo_id, EstadoReclamo.RESUELTO))
        self.assertEqual(self.gestor_mock.get_reclamo(reclamo_id).estado, EstadoReclamo.RESUELTO)
        
    def test_jefe_error_actualizar_estado_reclamo_ajeno(self):
        """Jefe no puede actualizar el estado de un reclamo de otro departamento."""
        reclamo_id = "R666" # IT
        self.assertFalse(self.jefe_inf.gestionar_reclamo(reclamo_id, EstadoReclamo.EN_PROCESO))
        self.assertEqual(self.gestor_mock.get_reclamo(reclamo_id).estado, EstadoReclamo.PENDIENTE)

    def test_jefe_generar_reporte_propio_depto(self):
        """Jefe puede generar un reporte de su departamento (RF 59)."""
        reporte = self.jefe_inf.generar_reporte(reporte_tipo="analitica")
        self.assertIn("Reporte Dpto. D_INFRAESTRUCTURA", reporte)
        
    # --- Tests de Secretario Técnico ---

    def test_secretario_derivar_reclamo(self):
        """Secretario puede derivar un reclamo (RF 60)."""
        reclamo_id = "R999" 
        self.assertTrue(self.secretario.derivar_reclamo(reclamo_id, DEPARTAMENTO_IT))
        self.assertEqual(self.gestor_mock.get_reclamo(reclamo_id).departamento_id, DEPARTAMENTO_IT)
        
    def test_secretario_actualizar_estado_reclamo(self):
        """Secretario puede actualizar el estado de cualquier reclamo (RF 60)."""
        reclamo_id = "R888" 
        self.assertTrue(self.secretario.gestionar_reclamo(reclamo_id, EstadoReclamo.PENDIENTE))
        self.assertEqual(self.gestor_mock.get_reclamo(reclamo_id).estado, EstadoReclamo.PENDIENTE)
        
    def test_secretario_generar_reporte_global(self):
        """Secretario puede generar un reporte global/de cualquier depto (RF 59)."""
        reporte = self.secretario.generar_reporte(reporte_tipo="analitica")
        self.assertIn("Reporte GLOBAL", reporte) 

    def test_secretario_manejar_reclamos_todos(self):
        """Secretario puede listar todos los reclamos pendientes (alcance ALL)."""
        reclamos = self.secretario.listar_reclamos_pendientes_admin() 
        self.assertEqual(len(reclamos), 2)
        
    def test_admin_sin_servicios(self):
        """Prueba de manejo de errores cuando los servicios no están inyectados."""
        admin_sin_servicios = JefeDepartamento("J0", "e", "u", "p", "n", "a", Claustro.PAYS, DEPARTAMENTO_INF, None, None)
        
        self.assertEqual(admin_sin_servicios.listar_reclamos_pendientes_admin(), [])
        self.assertFalse(admin_sin_servicios.gestionar_reclamo("R999", EstadoReclamo.RESUELTO))
        self.assertIsNone(admin_sin_servicios.generar_reporte("analitica"))
        
        sec_sin_servicios = SecretarioTecnico("S0", "e", "u", "p", "n", "a", Claustro.DOCENTE, None, None)
        self.assertFalse(sec_sin_servicios.derivar_reclamo("R999", DEPARTAMENTO_IT))
        self.assertFalse(sec_sin_servicios.gestionar_reclamo("R999", EstadoReclamo.RESUELTO))