import unittest
from datetime import datetime
from typing import Dict, Any, List, Optional

from modules.reclamos import Clasificador, EstadoReclamo, Reclamo
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica

# Stopwords de prueba y constantes
TEST_STOPWORDS = ["el", "la", "de", "un", "una", "y", "o", "es", "en", "por"]
DEPARTAMENTO_INF = "D_INFRAESTRUCTURA"
DEPARTAMENTO_IT = "D_INFORMATICA"
DEPARTAMENTO_SEC = "D_SECRETARIA"


class TestGestorReclamos(unittest.TestCase):
    """Pruebas para la clase Gestor_Reclamos."""

    def setUp(self):
        """Inicialización: Gestor con Clasificador."""
        self.clasificador = Clasificador(stopwords=TEST_STOPWORDS)
        self.gestor = Gestor_Reclamos(clasificador_servicio=self.clasificador)
        
        # Pre-carga de datos simulados
        self.reclamo_existente = Reclamo(
            id_reclamo="R999", contenido="Problema con el servidor", 
            usuario_creator_id="U1", departamento_id=DEPARTAMENTO_IT, 
            estado=EstadoReclamo.PENDIENTE
        )
        self.gestor._reclamos_db["R999"] = self.reclamo_existente
        # Reiniciar ID para que el primer nuevo reclamo sea R0001
        self.gestor._next_reclamo_id = 1 
        
        # El mocking incorrecto de 'actualizar_estado_reclamo' fue eliminado.

    def tearDown(self):
        pass

    def test_crear_reclamo_nuevo(self):
        """Prueba de creación de un reclamo sin sugerencia de adhesión (RF 42)."""
        contenido = "Necesito un nuevo escritorio en mi oficina."
        resultado = self.gestor.crear_reclamo(contenido, None, "U2")
        self.assertTrue(resultado["creado"])
        self.assertEqual(resultado["mensaje"], "Reclamo creado.")
        nuevo_reclamo = self.gestor.get_reclamo("R0001")
        self.assertIsNotNone(nuevo_reclamo)
        self.assertEqual(nuevo_reclamo.estado, EstadoReclamo.PENDIENTE)
        self.assertEqual(nuevo_reclamo.departamento_id, DEPARTAMENTO_SEC) # Default
        
    def test_crear_reclamo_sugerir_adhesion(self):
        """Prueba de creación de reclamo con sugerencia de adhesión (RF 41)."""
        contenido = "No tengo wifi en la sala de profesores." 
        # Mockear clasificador para forzar una sugerencia
        original_clasificar = self.gestor.clasificador_servicio.clasificar 
        self.gestor.clasificador_servicio.clasificar = lambda c: {"departamento_id": DEPARTAMENTO_IT, "reclamos_similares_ids": ["R999"]} 
        
        resultado = self.gestor.crear_reclamo(contenido, None, "U3")
        self.assertFalse(resultado["creado"])
        self.assertEqual(resultado["mensaje"], "Similares encontrados.") 
        self.assertEqual(len(resultado["similares"]), 1)

        # Restaurar la función clasificar original
        self.gestor.clasificador_servicio.clasificar = original_clasificar
        
    def test_adherirse_a_reclamo_exitoso(self):
        """Prueba de adhesión a un reclamo existente (RF 38, RF 43)."""
        self.reclamo_existente.adherentes_ids = [] # Limpiar adherentes
        exito, msg = self.gestor.adherirse_a_reclamo("R999", "U_ADH")
        self.assertTrue(exito)
        self.assertIn("U_ADH", self.reclamo_existente.adherentes_ids)

    def test_adherirse_fail_no_existe(self):
        """Prueba de fallo de adhesión si el reclamo no existe."""
        exito, msg = self.gestor.adherirse_a_reclamo("R_NO_EXISTE", "U_ADH")
        self.assertFalse(exito)
        self.assertIn("no encontrado", msg)

    def test_adherirse_fail_creador(self):
        """Prueba de fallo de adhesión si el usuario es el creador."""
        exito, msg = self.gestor.adherirse_a_reclamo("R999", "U1")
        self.assertFalse(exito)
        self.assertIn("creador", msg)
        
    def test_adherirse_fail_ya_adherido(self):
        """Prueba de fallo de adhesión si el usuario ya está adherido."""
        self.reclamo_existente.adherentes_ids = ["U_ADH"]
        exito, msg = self.gestor.adherirse_a_reclamo("R999", "U_ADH")
        self.assertFalse(exito)
        self.assertIn("ya está adherido", msg)

    def test_actualizar_estado_reclamo(self):
        """Prueba de actualización de estado y notificación (RF 45, RF 57)."""
        # Esta llamada ahora usa la implementación real, por lo que actualiza el estado.
        self.assertTrue(self.gestor.actualizar_estado_reclamo("R999", EstadoReclamo.RESUELTO))
        self.assertEqual(self.reclamo_existente.estado, EstadoReclamo.RESUELTO)
        # Prueba de estado ya actualizado
        self.assertTrue(self.gestor.actualizar_estado_reclamo("R999", EstadoReclamo.RESUELTO))
        # Prueba de reclamo inexistente
        self.assertFalse(self.gestor.actualizar_estado_reclamo("R_NO_EXISTE", EstadoReclamo.RESUELTO))
        
    def test_derivar_reclamo(self):
        """Prueba de derivación de un reclamo a otro departamento (RF 60)."""
        self.assertEqual(self.reclamo_existente.departamento_id, DEPARTAMENTO_IT)
        derivacion_exitosa = self.gestor.derivar_reclamo("R999", DEPARTAMENTO_INF)
        self.assertTrue(derivacion_exitosa)
        self.assertEqual(self.reclamo_existente.departamento_id, DEPARTAMENTO_INF)
        # Prueba de reclamo inexistente
        self.assertFalse(self.gestor.derivar_reclamo("R_NO_EXISTE", DEPARTAMENTO_INF))
        
    def test_get_reclamos_por_departamento(self):
        """Prueba de obtención de reclamos por departamento."""
        self.gestor._reclamos_db["R888"] = Reclamo(
            "R888", "Otro reclamo IT", "U2", DEPARTAMENTO_IT, EstadoReclamo.EN_PROCESO
        )
        reclamos_it = self.gestor.get_reclamos_por_departamento(DEPARTAMENTO_IT)
        self.assertEqual(len(reclamos_it), 2)
        reclamos_inf = self.gestor.get_reclamos_por_departamento(DEPARTAMENTO_INF)
        self.assertEqual(len(reclamos_inf), 0)

    def test_get_reclamos_pendientes_filtrados(self):
        """Prueba de obtención de reclamos pendientes con y sin filtro de departamento."""
        self.gestor._reclamos_db["R888"] = Reclamo(
            "R888", "Pendiente IT", "U2", DEPARTAMENTO_IT, EstadoReclamo.PENDIENTE
        )
        self.gestor._reclamos_db["R777"] = Reclamo(
            "R777", "Resuelto IT", "U3", DEPARTAMENTO_IT, EstadoReclamo.RESUELTO
        )
        self.gestor._reclamos_db["R666"] = Reclamo(
            "R666", "Pendiente INF", "U4", DEPARTAMENTO_INF, EstadoReclamo.PENDIENTE
        )
        # R999 y R888 están pendientes en IT
        reclamos_pendientes_it = self.gestor.get_reclamos_pendientes_filtrados(DEPARTAMENTO_IT)
        self.assertEqual(len(reclamos_pendientes_it), 2)
        # R999, R888, R666 están pendientes en total
        reclamos_pendientes_all = self.gestor.get_reclamos_pendientes_filtrados(None)
        self.assertEqual(len(reclamos_pendientes_all), 3)

    def test_get_mis_reclamos(self):
        """Prueba de obtener reclamos creados o adheridos por un usuario (RF 44)."""
        self.gestor.adherirse_a_reclamo("R999", "U10") # U10 adherido
        # U1 creó R999, U10 está adherido
        mis_reclamos_u1 = self.gestor.get_mis_reclamos("U1")
        self.assertEqual(len(mis_reclamos_u1), 1)
        mis_reclamos_u10 = self.gestor.get_mis_reclamos("U10")
        self.assertEqual(len(mis_reclamos_u10), 1)
        # Usuario sin reclamos
        mis_reclamos_u_none = self.gestor.get_mis_reclamos("U_NO_EXISTE")
        self.assertEqual(len(mis_reclamos_u_none), 0)


class TestAnalitica(unittest.TestCase):
    """Pruebas para la clase Analitica."""

    def setUp(self):
        """Inicialización: Gestor con datos y Analitica."""
        self.clasificador = Clasificador(stopwords=TEST_STOPWORDS)
        self.gestor = Gestor_Reclamos(clasificador_servicio=self.clasificador)
        self.analitica = Analitica(gestor_servicio=self.gestor)

        # Cargar reclamos de prueba con palabras clave
        reclamo_it_1 = Reclamo("A001", "La computadora de la sala de cómputo está en proceso.", "Ua", DEPARTAMENTO_IT, EstadoReclamo.EN_PROCESO)
        reclamo_it_2 = Reclamo("A002", "El servidor de la facultad no tiene conexión.", "Ub", DEPARTAMENTO_IT, EstadoReclamo.RESUELTO)
        reclamo_it_3 = Reclamo("A003", "El proyector no enciende.", "Uc", DEPARTAMENTO_IT, EstadoReclamo.PENDIENTE)
        reclamo_inf_1 = Reclamo("B001", "Falta luz en el aula.", "Ud", DEPARTAMENTO_INF, EstadoReclamo.INVALIDO)

        for r in [reclamo_it_1, reclamo_it_2, reclamo_it_3, reclamo_inf_1]:
            # Extracción de palabras clave
            r.palabras_clave = self.clasificador.extraer_palabras_clave(r.contenido)
            self.gestor._reclamos_db[r.id] = r
            
    def test_get_estadisticas_generales(self):
        """Prueba de cálculo de estadísticas por estado (RF 54)."""
        
        # Prueba con datos existentes
        stats_it = self.analitica.get_estadisticas_generales(DEPARTAMENTO_IT)
        self.assertEqual(stats_it["total_reclamos"], 3)
        self.assertAlmostEqual(stats_it["pct_en_proceso"], 33.33, places=2)
        self.assertAlmostEqual(stats_it["pct_resueltos"], 33.33, places=2)
        self.assertAlmostEqual(stats_it["pct_pendientes"], 33.33, places=2)
        self.assertEqual(stats_it["pct_invalidos"], 0.0)

        # Prueba con un departamento con 0 reclamos
        stats_none = self.analitica.get_estadisticas_generales(DEPARTAMENTO_SEC)
        self.assertEqual(stats_none["total_reclamos"], 0)
        self.assertEqual(stats_none["pct_en_proceso"], 0.0)

    def test_get_frecuencia_palabras(self):
        """Prueba de cálculo de frecuencia de palabras clave (RF 55)."""
        
        frecuencia_it = self.analitica.get_frecuencia_palabras(DEPARTAMENTO_IT)
        self.assertEqual(frecuencia_it.get('computadora'), 1)
        self.assertEqual(frecuencia_it.get('servidor'), 1) 
        self.assertEqual(frecuencia_it.get('proyector'), 1)
        
        # Prueba con departamento sin reclamos
        frecuencia_none = self.analitica.get_frecuencia_palabras(DEPARTAMENTO_SEC)
        self.assertEqual(len(frecuencia_none), 0)

    def test_generar_reporte_html(self):
        """Prueba de simulación de generación de reporte HTML (RF 59)."""
        stats = self.analitica.get_estadisticas_generales(DEPARTAMENTO_IT)
        frecuencia = self.analitica.get_frecuencia_palabras(DEPARTAMENTO_IT)
        reporte = self.analitica.generar_reporte_html(DEPARTAMENTO_IT, stats, frecuencia)
        self.assertIsInstance(reporte, str)
        self.assertTrue(reporte.startswith("<html>")) 
        self.assertIn("Total de Reclamos: <b>3</b>", reporte) 

    def test_generar_reporte_pdf_simulado(self):
        """Prueba de simulación de generación de reporte PDF (RF 59)."""
        reporte = self.analitica.generar_reporte_pdf(DEPARTAMENTO_IT)
        self.assertIsInstance(reporte, str)
        self.assertIn("Reporte PDF para el Departamento D_INFORMATICA (Simulado", reporte)


# Para ejecutar solo este archivo
if __name__ == '__main__':
    unittest.main()