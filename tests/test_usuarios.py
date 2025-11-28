import unittest
from typing import Dict, Any, List, Optional
from modules.reclamos import Clasificador, EstadoReclamo, Reclamo
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica
from modules.usuarios import UsuarioFinal, JefeDepartamento, SecretarioTecnico, Claustro, RolAdmin, Usuario

# Stopwords de prueba y constantes
TEST_STOPWORDS = ["el", "la", "de", "un", "una", "y", "o", "es", "en", "por"]
DEPARTAMENTO_INF = "D_INFRAESTRUCTURA"
DEPARTAMENTO_IT = "D_INFORMATICA"
DEPARTAMENTO_SEC = "D_SECRETARIA"


class MockGestorReclamos:
    """Mock básico para simular el Gestor de Reclamos en pruebas de UsuarioFinal."""
    def __init__(self):
        self._reclamos_db: Dict[str, Reclamo] = {
            "R999": Reclamo("R999", "Reclamo PENDIENTE", "J1", DEPARTAMENTO_INF, EstadoReclamo.PENDIENTE),
            "R888": Reclamo("R888", "Reclamo RESUELTO", "J2", DEPARTAMENTO_IT, EstadoReclamo.RESUELTO),
        }
    
    def crear_reclamo(self, contenido, adjunto, usuario_id) -> Dict[str, Any]:
        if "wifi" in contenido:
            return {"creado": False, "mensaje": "Similares encontrados.", "similares": [self._reclamos_db["R888"]]}
        return {"creado": True, "mensaje": "Reclamo creado.", "similares": None}

    def adherirse_a_reclamo(self, reclamo_id, usuario_id) -> bool:
        return True, "Adhesión exitosa."
        
    def get_reclamos_pendientes_filtrados(self, depto_id: Optional[str] = None) -> List[Reclamo]:
        return [r for r in self._reclamos_db.values() if r.estado == EstadoReclamo.PENDIENTE]

    def get_mis_reclamos(self, usuario_id: str) -> List[Reclamo]:
        return [r for r in self._reclamos_db.values() if r.usuario_creator_id == usuario_id]
        
    def get_reclamo(self, reclamo_id: str) -> Optional[Reclamo]:
        return self._reclamos_db.get(reclamo_id)

    def actualizar_estado_reclamo(self, reclamo_id: str, nuevo_estado: EstadoReclamo) -> bool:
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.estado = nuevo_estado
            return True
        return False
        
    def get_reclamos_por_departamento(self, depto_id: str) -> List[Reclamo]:
        return [r for r in self._reclamos_db.values() if r.departamento_id == depto_id]

    def get_all_reclamos(self) -> List[Reclamo]:
        return list(self._reclamos_db.values())

    def derivar_reclamo(self, reclamo_id: str, nuevo_depto_id: str) -> bool:
        reclamo = self.get_reclamo(reclamo_id)
        if reclamo:
            reclamo.departamento_id = nuevo_depto_id
            return True
        return False


class MockAnalitica:
    """Mock básico para simular la Analitica en pruebas de UsuarioAdmin."""
    def get_estadisticas_generales(self, departamento_id: str) -> Dict[str, float]:
        if departamento_id == "D_INFRAESTRUCTURA":
            return {"total_reclamos": 10, "pct_resueltos": 50.0}
        return {"total_reclamos": 0, "pct_resueltos": 0.0}
        
    def get_frecuencia_palabras(self, departamento_id: str) -> Dict[str, int]:
        return {"luz": 5, "gotera": 3}

    def generar_reporte_html(self, departamento_id: str, stats: Dict[str, float], frecuencia: Dict[str, int]) -> str:
        return f"<html>Reporte HTML para {departamento_id}</html>"
        
    def generar_reporte_pdf(self, departamento_id: str) -> str:
        return f"Reporte PDF para {departamento_id} (Simulado)"


class TestUsuarioFinal(unittest.TestCase):
    """Pruebas para la clase UsuarioFinal (RF 38, 41, 42, 43, 44)."""
    
    def setUp(self):
        self.gestor_mock = MockGestorReclamos()
        self.usuario_db = {}
        self.user_data = UsuarioFinal.registro_usuario(
            self.usuario_db, "Test", "User", "t@test.com", "testuser", 
            Claustro.ESTUDIANTE, "pass123", "pass123"
        )
        
        # --- CORRECCIÓN CLAVE para el TypeError ---
        # Renombrar la clave 'id' a 'id_usuario' para que coincida con el constructor
        if self.user_data and 'id' in self.user_data:
            self.user_data['id_usuario'] = self.user_data.pop('id')
            
        self.usuario_final = UsuarioFinal(**self.user_data, gestor_servicio=self.gestor_mock)
        self.usuario_db[self.usuario_final.id] = self.usuario_final
    
    def test_registro_exitoso(self):
        """Prueba de registro de un nuevo usuario."""
        self.assertIsNotNone(self.usuario_final.id)
        self.assertEqual(self.usuario_final.id, "UF0001") 
        
    def test_registro_fail_email_existente(self):
        """Prueba de fallo de registro por email duplicado."""
        fail_data = UsuarioFinal.registro_usuario(
            self.usuario_db, "T", "U", "t@test.com", "newuser", 
            Claustro.DOCENTE, "p", "p"
        )
        self.assertIsNone(fail_data)

    def test_registro_fail_usuario_existente(self):
        """Prueba de fallo de registro por nombre de usuario duplicado."""
        fail_data = UsuarioFinal.registro_usuario(
            self.usuario_db, "T", "U", "t2@test.com", "testuser", 
            Claustro.DOCENTE, "p", "p"
        )
        self.assertIsNone(fail_data)

    def test_registro_fail_contrasenias_no_coinciden(self):
        """Prueba de fallo de registro por contraseñas diferentes."""
        fail_data = UsuarioFinal.registro_usuario(
            self.usuario_db, "T", "U", "t3@test.com", "u3", 
            Claustro.DOCENTE, "pass1", "pass2"
        )
        self.assertIsNone(fail_data)
        
    def test_crear_reclamo_nuevo(self):
        """Prueba de creación de reclamo nuevo (RF 42)."""
        self.usuario_final.crear_reclamo("Reclamo nuevo")

    def test_crear_reclamo_sugerir_adhesion(self):
        """Prueba de creación de reclamo con sugerencia de adhesión y adhesión simulada (RF 41, RF 43)."""
        self.usuario_final.crear_reclamo("No tengo wifi")
        
    def test_listar_reclamos_pendientes(self):
        """Prueba de listado de reclamos pendientes (RF 38)."""
        pendientes = self.usuario_final.listar_reclamos_pendientes()
        self.assertEqual(len(pendientes), 1)
        self.assertEqual(pendientes[0]["ID"], "R999")
        
    def test_listar_reclamos_pendientes_sin_gestor(self):
        """Prueba de listado sin servicio de gestor."""
        user = UsuarioFinal(id_usuario="U100", email="e", usuario="u", contrasenia_hash="p", nombre="n", apellido="a", claustro=Claustro.ESTUDIANTE, gestor_servicio=None)
        pendientes = user.listar_reclamos_pendientes()
        self.assertEqual(len(pendientes), 0)

    def test_ver_mis_reclamos(self):
        """Prueba de ver reclamos propios (RF 44)."""
        self.usuario_final.id = "J1"
        mis_reclamos = self.usuario_final.ver_mis_reclamos()
        self.assertEqual(len(mis_reclamos), 1)
        self.assertEqual(mis_reclamos[0].id, "R999")
        
    def test_ver_mis_reclamos_sin_gestor(self):
        """Prueba de ver reclamos sin servicio de gestor."""
        user = UsuarioFinal(id_usuario="U100", email="e", usuario="u", contrasenia_hash="p", nombre="n", apellido="a", claustro=Claustro.ESTUDIANTE, gestor_servicio=None)
        reclamos = user.ver_mis_reclamos()
        self.assertEqual(len(reclamos), 0)
        
    def test_login(self):
        """Prueba de login de usuario."""
        self.assertTrue(self.usuario_final.login("testuser", "pass123", self.usuario_db))
        self.assertFalse(self.usuario_final.login("testuser", "wrongpass", self.usuario_db))


class TestUsuarioAdmin(unittest.TestCase):
    """Pruebas para JefeDepartamento y SecretarioTecnico (RF 45, 54, 55, 59, 60)."""

    def setUp(self):
        self.gestor_mock = MockGestorReclamos()
        self.analitica_mock = MockAnalitica()
        
        self.jefe_inf = JefeDepartamento(
            "JINF", "jefe@inf.com", "jefeinf", "p", "Jefe", "INF", 
            DEPARTAMENTO_INF, self.gestor_mock, self.analitica_mock
        )
        self.secretario = SecretarioTecnico(
            "SEC", "sec@sec.com", "secretario", "p", "Secretario", "T", 
            self.gestor_mock, self.analitica_mock
        )

    # --- Pruebas de Jefe de Departamento ---

    def test_jefe_get_role_name_and_id(self):
        self.assertEqual(self.jefe_inf.get_role_name(), RolAdmin.JEFE.value)
        self.assertEqual(self.jefe_inf.get_departamento_id(), DEPARTAMENTO_INF)
        
    def test_jefe_ver_analitica_propia(self):
        """Jefe puede ver analítica de su departamento (RF 54, 55)."""
        analitica = self.jefe_inf.ver_analitica(DEPARTAMENTO_INF)
        self.assertTrue(analitica)
        self.assertEqual(analitica["estadisticas"]["total_reclamos"], 10)
        
    def test_jefe_ver_analitica_ajena_fallida(self):
        """Jefe no puede ver analítica de otro departamento."""
        analitica = self.jefe_inf.ver_analitica(DEPARTAMENTO_IT)
        self.assertFalse(analitica)
        
    def test_jefe_manejar_reclamos_propios(self):
        """Jefe puede manejar reclamos de su departamento."""
        reclamos = self.jefe_inf.manejar_reclamos(DEPARTAMENTO_INF)
        self.assertEqual(len(reclamos), 1)
        
    def test_jefe_manejar_reclamos_ajenos_fallida(self):
        """Jefe no puede manejar reclamos de otro departamento."""
        reclamos = self.jefe_inf.manejar_reclamos(DEPARTAMENTO_IT)
        self.assertEqual(len(reclamos), 0) 
        
    def test_jefe_actualizar_estado_reclamo_propio(self):
        """Jefe puede actualizar el estado de un reclamo de su departamento (RF 45)."""
        self.assertTrue(self.jefe_inf.actualizar_estado_reclamo("R999", EstadoReclamo.RESUELTO))
        
    def test_jefe_actualizar_estado_reclamo_ajeno_fallida(self):
        """Jefe no puede actualizar el estado de un reclamo de otro departamento."""
        self.assertFalse(self.jefe_inf.actualizar_estado_reclamo("R888", EstadoReclamo.RESUELTO))
        
    def test_jefe_generar_reporte_html(self):
        """Jefe genera reporte HTML (RF 59)."""
        reporte = self.jefe_inf.generar_reporte(DEPARTAMENTO_INF, "HTML")
        self.assertTrue(reporte.startswith("<html>Reporte HTML para"))

    def test_jefe_generar_reporte_pdf(self):
        """Jefe genera reporte PDF (RF 59)."""
        reporte = self.jefe_inf.generar_reporte(DEPARTAMENTO_INF, "PDF")
        self.assertIn("Reporte PDF para D_INFRAESTRUCTURA (Simulado)", reporte)

    def test_jefe_generar_reporte_formato_invalido(self):
        """Jefe genera reporte con formato inválido."""
        reporte = self.jefe_inf.generar_reporte(DEPARTAMENTO_INF, "XML")
        self.assertIn("Formato no soportado", reporte)

    # --- Pruebas de Secretario Técnico ---

    def test_secretario_get_role_name_and_id(self):
        self.assertEqual(self.secretario.get_role_name(), RolAdmin.SECRETARIO.value)
        self.assertEqual(self.secretario.get_departamento_id(), "ALL")
        
    def test_secretario_ver_analitica_cualquier_depto(self):
        """Secretario puede ver analítica de cualquier departamento (RF 54, 55)."""
        analitica_inf = self.secretario.ver_analitica(DEPARTAMENTO_INF)
        analitica_it = self.secretario.ver_analitica(DEPARTAMENTO_IT)
        self.assertTrue(analitica_inf)
        self.assertFalse(analitica_it["estadisticas"]["total_reclamos"])

    def test_secretario_manejar_reclamos_todos(self):
        """Secretario puede manejar todos los reclamos con ALL."""
        reclamos = self.secretario.manejar_reclamos("ALL")
        self.assertEqual(len(reclamos), 2)
        
    def test_secretario_manejar_reclamos_filtrados(self):
        """Secretario puede manejar reclamos filtrados por depto."""
        reclamos = self.secretario.manejar_reclamos(DEPARTAMENTO_IT)
        self.assertEqual(len(reclamos), 1)
        
    def test_secretario_actualizar_estado_reclamo_cualquiera(self):
        """Secretario puede actualizar el estado de cualquier reclamo (RF 45)."""
        self.assertTrue(self.secretario.actualizar_estado_reclamo("R888", EstadoReclamo.RESUELTO))
        self.assertTrue(self.secretario.actualizar_estado_reclamo("R999", EstadoReclamo.INVALIDO))

    def test_secretario_derivar_reclamo(self):
        """Secretario puede derivar un reclamo (RF 60)."""
        reclamo = self.gestor_mock.get_reclamo("R999")
        self.assertEqual(reclamo.departamento_id, DEPARTAMENTO_INF)
        self.assertTrue(self.secretario.derivar_reclamo("R999", DEPARTAMENTO_IT))
        self.assertEqual(reclamo.departamento_id, DEPARTAMENTO_IT)
        
    def test_admin_sin_servicios(self):
        """Prueba de manejo de errores cuando los servicios no están inyectados."""
        admin_sin_servicios = JefeDepartamento("J0", "e", "u", "p", "n", "a", DEPARTAMENTO_INF, None, None)
        self.assertFalse(admin_sin_servicios.manejar_reclamos(DEPARTAMENTO_INF))
        self.assertFalse(admin_sin_servicios.actualizar_estado_reclamo("R999", EstadoReclamo.RESUELTO))
        self.assertFalse(admin_sin_servicios.ver_analitica(DEPARTAMENTO_INF))
        self.assertIn("Servicio de Analítica no disponible", admin_sin_servicios.generar_reporte(DEPARTAMENTO_INF))
        
        sec_sin_servicios = SecretarioTecnico("S0", "e", "u", "p", "n", "a", None, None)
        self.assertFalse(sec_sin_servicios.derivar_reclamo("R999", DEPARTAMENTO_IT))

    def test_reporte_datos_no_obtenidos(self):
        """Prueba de fallo al obtener datos para el reporte."""
        reporte = self.jefe_inf.generar_reporte(DEPARTAMENTO_SEC, "HTML")
        self.assertIn("No se pudieron obtener los datos de analítica", reporte)


# Para ejecutar solo este archivo
if __name__ == '__main__':
    unittest.main()