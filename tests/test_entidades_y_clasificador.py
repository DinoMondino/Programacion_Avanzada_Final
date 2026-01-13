import unittest
from modules.reclamos import Clasificador, EstadoReclamo, Reclamo

# Constantes para evitar errores de tipeo
DEPARTAMENTO_INF = "D_INFRAESTRUCTURA"
DEPARTAMENTO_IT = "D_INFORMATICA"
DEPARTAMENTO_SEC = "D_SECRETARIA"
DEPARTAMENTO_FIN = "D_FINANZAS"

class TestEntidades(unittest.TestCase):
    def test_reclamo_adherentes(self):
        """Verifica el contador de adherentes (RF 43)."""
        reclamo = Reclamo(
            id_reclamo="R100", contenido="Test", usuario_creator_id="U1", 
            departamento_id=DEPARTAMENTO_INF, estado=EstadoReclamo.PENDIENTE,
            palabras_clave=["test"]
        )
        reclamo.adherentes_ids = ["U2", "U3"] 
        self.assertEqual(reclamo.get_num_adherentes(), 2)

class TestClasificador(unittest.TestCase):
    def setUp(self):
        # Usamos las mismas stopwords que en app.py
        self.clasificador = Clasificador(stopwords=["el", "la", "de", "un", "en"])

    def test_clasificar_informatica(self):
        """Prueba de clasificación para Informática (RF 40)."""
        contenido = "No hay conexión wifi ni internet en el aula de cómputo."
        resultado = self.clasificador.clasificar(contenido)
        self.assertEqual(resultado["departamento_id"], DEPARTAMENTO_IT)

    def test_clasificar_infraestructura(self):
        """Prueba de clasificación para Infraestructura (RF 40)."""
        contenido = "Hay una gotera y falta luz en el aula."
        resultado = self.clasificador.clasificar(contenido)
        self.assertEqual(resultado["departamento_id"], DEPARTAMENTO_INF)

    def test_clasificar_secretaria_default(self):
        """Prueba de clasificación por defecto a Secretaría Técnica (RF 40)."""
        contenido = "Quisiera consultar sobre la fecha de las mesas." # Sin palabras clave
        resultado = self.clasificador.clasificar(contenido)
        # Verificamos que caiga en el default definido en la lógica
        self.assertEqual(resultado["departamento_id"], DEPARTAMENTO_SEC)

    def test_clasificar_empate(self):
        """Prueba de clasificación cuando hay un empate de palabras clave (RF 40)."""
        # "aire" (INFRAESTRUCTURA), "wifi" (INFORMATICA)
        contenido = "El aire y el wifi no funcionan."
        resultado = self.clasificador.clasificar(contenido)
        # El clasificador toma el primero que encuentra o el de mayor puntaje
        self.assertIn(resultado["departamento_id"], [DEPARTAMENTO_INF, DEPARTAMENTO_IT])

    def test_extraer_palabras_clave(self):
        """Prueba de extracción y filtrado de stopwords (RF 55)."""
        contenido = "El internet del aula es lento"
        palabras = self.clasificador.extraer_palabras_clave(contenido)
        self.assertNotIn("el", palabras)
        self.assertIn("internet", palabras)
        self.assertIn("lento", palabras)

# Para ejecutar:
# python -m coverage run -m unittest discover tests

# Ver reporte rápido en terminal
# python -m coverage report -m

# Generar la carpeta con el reporte visual (HTML)
# python -m coverage html

# python -m coverage erase