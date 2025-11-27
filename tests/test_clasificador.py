import unittest
from datetime import datetime
from typing import Dict, Any, List, Optional

# Importar las clases desde los módulos (asumiendo que están en la misma carpeta o el path es correcto)
from modules.reclamos import Clasificador, EstadoReclamo, Reclamo
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica

# Stopwords de prueba
TEST_STOPWORDS = ["el", "la", "de", "un", "una", "y", "o", "es", "en", "por"]
DEPARTAMENTO_INF = "D_INFRAESTRUCTURA"
DEPARTAMENTO_IT = "D_INFORMATICA"
DEPARTAMENTO_SEC = "D_SECRETARIA"


class TestClasificador(unittest.TestCase):
    """Pruebas para la clase Clasificador."""

    def setUp(self):
        """Inicialización para cada prueba."""
        self.clasificador = Clasificador(stopwords=TEST_STOPWORDS)

    def test_clasificar_informatica(self):
        """Prueba de clasificación para el departamento de Informática (RF 40)."""
        contenido = "No hay conexión wifi ni internet en el aula de cómputo."
        resultado = self.clasificador.clasificar(contenido)
        self.assertEqual(resultado["departamento_id"], DEPARTAMENTO_IT)
        self.assertIsInstance(resultado["reclamos_similares_ids"], List)

    def test_clasificar_infraestructura(self):
        """Prueba de clasificación para Infraestructura (RF 40)."""
        contenido = "La luz está apagada en el baño de mujeres."
        resultado = self.clasificador.clasificar(contenido)
        self.assertEqual(resultado["departamento_id"], DEPARTAMENTO_INF)
        self.assertTrue(True)

    def test_clasificar_secretaria_default(self):
        """Prueba de clasificación por defecto a Secretaría Técnica (RF 40)."""
        contenido = "Quisiera consultar sobre la fecha de las mesas de examen."
        resultado = self.clasificador.clasificar(contenido)
        self.assertEqual(resultado["departamento_id"], DEPARTAMENTO_SEC)
        self.assertFalse(resultado["reclamos_similares_ids"]) 

    def test_extraer_palabras_clave(self):
        """Prueba de extracción de palabras clave y filtrado de stopwords (RF 55)."""
        contenido = "La computadora de el laboratorio está rota, y no se puede usar."
        palabras_clave = self.clasificador.extraer_palabras_clave(contenido)
        # Corregido para incluir 'está', 'no' y 'se', que no son stopwords.
        self.assertListEqual(sorted(palabras_clave), sorted(['computadora', 'laboratorio', 'rota', 'puede', 'usar', 'está', 'no', 'se'])) 
        self.assertNotIn("la", palabras_clave)
        self.assertNotIn("de", palabras_clave)
        self.assertNotIn("el", palabras_clave)

class TestGestorReclamos(unittest.TestCase):
    """Pruebas para la clase Gestor_Reclamos."""

    def setUp(self):
        """Inicialización: Gestor con Clasificador."""
        self.clasificador = Clasificador(stopwords=TEST_STOPWORDS)
        self.gestor = Gestor_Reclamos(clasificador_servicio=self.clasificador)
        
        # Pre-carga de datos simulados para pruebas de adhesión y estado
        self.reclamo_existente = Reclamo(
            id_reclamo="R999", contenido="Problema con el servidor", 
            usuario_creator_id="U1", departamento_id=DEPARTAMENTO_IT, 
            estado=EstadoReclamo.PENDIENTE
        )
        self.gestor._reclamos_db["R999"] = self.reclamo_existente
        # Reiniciar ID para que el primer nuevo reclamo sea R0001
        self.gestor._next_reclamo_id = 1 

    def test_crear_reclamo_nuevo(self):
        """Prueba de creación de un reclamo sin sugerencia de adhesión (RF 42)."""
        contenido = "Necesito un nuevo escritorio en mi oficina."
        # Se accede al resultado como diccionario (corregido)
        resultado = self.gestor.crear_reclamo(contenido, None, "U2")
        self.assertTrue(resultado["creado"])
        self.assertEqual(resultado["mensaje"], "Reclamo creado.")
        self.assertIsNone(resultado["similares"])
        nuevo_reclamo = self.gestor.get_reclamo("R0001")
        self.assertIsNotNone(nuevo_reclamo)
        self.assertEqual(nuevo_reclamo.estado, EstadoReclamo.PENDIENTE)
        self.assertEqual(nuevo_reclamo.departamento_id, DEPARTAMENTO_SEC) # Default
        
    def test_crear_reclamo_sugerir_adhesion(self):
        """Prueba de creación de reclamo con sugerencia de adhesión (RF 41)."""
        contenido = "No tengo wifi en la sala de profesores." 
        
        # Se usa clasificador_servicio (corregido)
        original_clasificar = self.gestor.clasificador_servicio.clasificar 
        self.gestor.clasificador_servicio.clasificar = lambda c: {"departamento_id": DEPARTAMENTO_IT, "reclamos_similares_ids": ["R999"]} 
        
        # Se accede al resultado como diccionario (corregido)
        resultado = self.gestor.crear_reclamo(contenido, None, "U3")
        self.assertFalse(resultado["creado"])
        # Se verifica el string exacto (corregido)
        self.assertEqual(resultado["mensaje"], "Similares encontrados.") 
        self.assertIsNotNone(resultado["similares"])
        self.assertEqual(len(resultado["similares"]), 1)
        self.assertEqual(resultado["similares"][0].id, "R999")

        # Restaurar la función clasificar original
        self.gestor.clasificador_servicio.clasificar = original_clasificar
        
    def test_adherirse_a_reclamo(self):
        """Prueba de adhesión a un reclamo existente (RF 38, RF 43)."""
        self.reclamo_existente.adherentes_ids = [] # Limpiar adherentes
        adhesion_exitosa, _ = self.gestor.adherirse_a_reclamo("R999", "U_ADH")
        self.assertTrue(adhesion_exitosa)
        self.assertIn("U_ADH", self.reclamo_existente.adherentes_ids)
        self.assertEqual(self.reclamo_existente.get_num_adherentes(), 1)

    def test_adherirse_fail_creador(self):
        """Prueba de fallo de adhesión si el usuario es el creador."""
        adhesion_fallida, _ = self.gestor.adherirse_a_reclamo("R999", "U1")
        self.assertFalse(adhesion_fallida)
        
    def test_actualizar_estado(self):
        """Prueba de actualización de estado y notificación (RF 45, RF 57)."""
        self.gestor.actualizar_estado_reclamo("R999", EstadoReclamo.RESUELTO)
        self.assertEqual(self.reclamo_existente.estado, EstadoReclamo.RESUELTO)
        
    def test_derivar_reclamo(self):
        """Prueba de derivación de un reclamo a otro departamento (RF 60)."""
        self.assertEqual(self.reclamo_existente.departamento_id, DEPARTAMENTO_IT)
        derivacion_exitosa = self.gestor.derivar_reclamo("R999", DEPARTAMENTO_INF)
        self.assertTrue(derivacion_exitosa)
        self.assertEqual(self.reclamo_existente.departamento_id, DEPARTAMENTO_INF)
        
    def test_get_mis_reclamos(self):
        """Prueba de obtener reclamos creados o adheridos por un usuario (RF 44)."""
        self.gestor.adherirse_a_reclamo("R999", "U10") # U10 adherido
        # U1 creó R999, por lo que debe aparecer
        mis_reclamos_u1 = self.gestor.get_mis_reclamos("U1")
        self.assertEqual(len(mis_reclamos_u1), 1)
        self.assertEqual(mis_reclamos_u1[0].id, "R999")
        # U10 adherido debe ver el reclamo
        mis_reclamos_u10 = self.gestor.get_mis_reclamos("U10")
        self.assertEqual(len(mis_reclamos_u10), 1)


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
            # Extracción de palabras clave (La corrección en reclamos.py es crucial aquí)
            r.palabras_clave = self.clasificador.extraer_palabras_clave(r.contenido)
            self.gestor._reclamos_db[r.id] = r
            
    def test_get_estadisticas_generales(self):
        """Prueba de cálculo de estadísticas por estado (RF 54)."""
        
        stats_it = self.analitica.get_estadisticas_generales(DEPARTAMENTO_IT)
        self.assertEqual(stats_it["total_reclamos"], 3)
        self.assertAlmostEqual(stats_it["pct_en_proceso"], 33.33, places=2)
        self.assertAlmostEqual(stats_it["pct_resueltos"], 33.33, places=2)
        self.assertAlmostEqual(stats_it["pct_pendientes"], 33.33, places=2)
        self.assertEqual(stats_it["pct_invalidos"], 0.0)

        stats_inf = self.analitica.get_estadisticas_generales(DEPARTAMENTO_INF)
        self.assertEqual(stats_inf["total_reclamos"], 1)
        self.assertEqual(stats_inf["pct_en_proceso"], 0.0)
        self.assertAlmostEqual(stats_inf["pct_invalidos"], 100.0, places=2)

    def test_get_frecuencia_palabras(self):
        """Prueba de cálculo de frecuencia de palabras clave (RF 55)."""
        
        # Si reclamos.py está corregido, esta prueba pasa
        frecuencia_it = self.analitica.get_frecuencia_palabras(DEPARTAMENTO_IT)
        self.assertEqual(frecuencia_it.get('computadora'), 1)
        self.assertEqual(frecuencia_it.get('servidor'), 1) 
        self.assertEqual(frecuencia_it.get('proyector'), 1)
        
        frecuencia_inf = self.analitica.get_frecuencia_palabras(DEPARTAMENTO_INF)
        self.assertEqual(frecuencia_inf.get('luz'), 1)

    def test_generar_reporte_html(self):
        """Prueba de simulación de generación de reporte HTML (RF 59)."""
        stats = self.analitica.get_estadisticas_generales(DEPARTAMENTO_IT)
        frecuencia = self.analitica.get_frecuencia_palabras(DEPARTAMENTO_IT)
        reporte = self.analitica.generar_reporte_html(DEPARTAMENTO_IT, stats, frecuencia)
        self.assertIsInstance(reporte, str)
        # 1. Corrección para asegurar que la aserción coincida con el inicio de la cadena HTML
        self.assertTrue(reporte.startswith("<html>")) 
        self.assertIn("Reporte de Reclamos - Depto. D_INFORMATICA", reporte)
        # 2. Corrección para coincidir con la etiqueta <b> que está en el HTML generado
        self.assertIn("Total de Reclamos: <b>3</b>", reporte) 

    def test_generar_reporte_pdf_simulado(self):
        """Prueba de simulación de generación de reporte PDF (RF 59)."""
        reporte = self.analitica.generar_reporte_pdf(DEPARTAMENTO_IT)
        self.assertIsInstance(reporte, str)
        self.assertIn("Reporte PDF para el Departamento D_INFORMATICA (Simulado", reporte)


if __name__ == '__main__':
    # Para ejecutar todas las pruebas
    unittest.main()