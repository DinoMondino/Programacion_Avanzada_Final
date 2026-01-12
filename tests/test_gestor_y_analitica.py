import unittest
from modules.reclamos import Clasificador, EstadoReclamo
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica

class TestGestor(unittest.TestCase):
    def setUp(self):
        self.clasificador = Clasificador(stopwords=["el", "la"])
        self.gestor = Gestor_Reclamos(clasificador_servicio=self.clasificador)
        
    def test_crear_y_sugerir_similares(self):
        """Prueba que el gestor detecte duplicados por coincidencia de palabras."""
        # 1. Creamos el primer reclamo
        self.gestor.crear_reclamo("El internet está fallando", None, "U1") # Claves: internet, fallando
        
        # 2. Creamos uno muy parecido
        # 'internet' y 'fallando' coinciden -> len() == 2 -> Sugiere similar
        resultado = self.gestor.crear_reclamo("Hay internet fallando de nuevo", None, "U2")
        
        self.assertEqual(resultado["adherido_a"], "R0001")

class TestAnalitica(unittest.TestCase):
    def setUp(self):
        self.clasificador = Clasificador(stopwords=["el", "la", "de"])
        self.gestor = Gestor_Reclamos(self.clasificador)
        self.analitica = Analitica(self.gestor)
        
        # Cargamos datos para testear la analítica
        # Reclamo 1: INFRAESTRUCTURA (por la palabra 'baño')
        self.gestor.crear_reclamo("El baño está roto", None, "U1")
        # Reclamo 2: INFRAESTRUCTURA
        self.gestor.crear_reclamo("El baño pierde agua", None, "U2")
        # Reclamo 3: INFORMATICA (por la palabra 'wifi')
        self.gestor.crear_reclamo("No anda el wifi", None, "U3")

    def test_obtener_datos_dashboard(self):
        """Prueba el procesamiento de datos para los gráficos (RF 54)."""
        datos = self.analitica.obtener_datos_dashboard("D_INFRAESTRUCTURA")
        
        self.assertEqual(datos["total"], 2)
        # Verificamos que 'baño' sea la palabra más frecuente en ese depto
        self.assertEqual(datos["frecuencia"]["baño"], 2)
        # Verificamos que los estados se cuenten bien
        self.assertEqual(datos["stats"]["pendientes"], 2)

    def test_generar_reporte_html(self):
        """Prueba que se genere el string HTML del reporte (RF 59)."""
        # Simulamos que un admin pide el reporte
        html = self.analitica.generar_reporte_html("D_INFRAESTRUCTURA")
        
        self.assertIsInstance(html, str)
        self.assertIn("<html>", html)
        self.assertIn("D_INFRAESTRUCTURA", html)
        self.assertIn("Reporte de Reclamos", html)

    def test_analitica_vacia(self):
        """Prueba que la analítica no rompa si no hay reclamos."""
        datos = self.analitica.obtener_datos_dashboard("DEPARTAMENTO_INEXISTENTE")
        self.assertEqual(datos["total"], 0)
        self.assertEqual(len(datos["frecuencia"]), 0)

if __name__ == "__main__":
    unittest.main()