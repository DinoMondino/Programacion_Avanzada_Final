import unittest
from typing import List
from modules.reclamos import Clasificador, EstadoReclamo, Reclamo

# python -m unittest tests.test_entidades_y_clasificador tests.test_gestor_y_analitica tests.test_usuarios

# Stopwords de prueba y constantes
TEST_STOPWORDS = ["el", "la", "de", "un", "una", "y", "o", "es", "en", "por"]
DEPARTAMENTO_INF = "D_INFRAESTRUCTURA"
DEPARTAMENTO_IT = "D_INFORMATICA"
DEPARTAMENTO_SEC = "D_SECRETARIA"


class TestEntidades(unittest.TestCase):
    """Pruebas básicas para las entidades (Reclamo)."""
    
    def test_reclamo_adherentes(self):
        """Verifica el contador de adherentes de un reclamo (RF 43)."""
        reclamo = Reclamo(
            id_reclamo="R100", contenido="Test", usuario_creator_id="U1", 
            departamento_id=DEPARTAMENTO_INF, estado=EstadoReclamo.PENDIENTE,
            adherentes_ids=["U2", "U3", "U4"]
        )
        self.assertEqual(reclamo.get_num_adherentes(), 3)
        self.assertIsInstance(reclamo.__repr__(), str) # Prueba de representación


class TestClasificador(unittest.TestCase):
    """Pruebas para la clase Clasificador."""

    def setUp(self):
        """Inicialización para cada prueba."""
        self.clasificador = Clasificador(stopwords=TEST_STOPWORDS)

    def test_clasificar_informatica(self):
        """Prueba de clasificación para Informática (RF 40)."""
        contenido = "No hay conexión wifi ni internet en el aula de cómputo."
        resultado = self.clasificador.clasificar(contenido)
        self.assertEqual(resultado["departamento_id"], DEPARTAMENTO_IT)
        self.assertListEqual(resultado["reclamos_similares_ids"], ["R001", "R005"]) # Prueba de sugerencia

    def test_clasificar_infraestructura(self):
        """Prueba de clasificación para Infraestructura (RF 40) con sugerencia."""
        contenido = "Hay una gotera y falta luz en el aula."
        resultado = self.clasificador.clasificar(contenido)
        self.assertEqual(resultado["departamento_id"], DEPARTAMENTO_INF)
        self.assertListEqual(resultado["reclamos_similares_ids"], ["R004"])

    def test_clasificar_secretaria_default(self):
        """Prueba de clasificación por defecto a Secretaría Técnica (RF 40)."""
        contenido = "Quisiera consultar sobre la fecha de las mesas." # Sin palabras clave
        resultado = self.clasificador.clasificar(contenido)
        self.assertEqual(resultado["departamento_id"], DEPARTAMENTO_SEC)
        self.assertFalse(resultado["reclamos_similares_ids"]) 

    def test_clasificar_empate_resuelve_aleatorio(self):
        """Prueba de clasificación cuando hay un empate de palabras clave (RF 40)."""
        # "matricula" (FINANZAS), "examen" (SECRETARIA)
        contenido = "La matricula y el examen tienen problemas."
        resultado = self.clasificador.clasificar(contenido)
        # Verifica que se haya resuelto el empate entre los ganadores (FINANZAS, SECRETARIA)
        self.assertIn(resultado["departamento_id"], ["D_FINANZAS", DEPARTAMENTO_SEC])
        
    def test_extraer_palabras_clave(self):
        """Prueba de extracción de palabras clave y filtrado de stopwords (RF 55)."""
        contenido = "La computadora de el laboratorio está rota, y no se puede usar."
        palabras_clave = self.clasificador.extraer_palabras_clave(contenido)
        # 'está', 'no', 'se' y 'puede' no son stopwords, y deben ser incluidas.
        palabras_esperadas = sorted(['computadora', 'laboratorio', 'rota', 'puede', 'usar', 'está', 'no', 'se'])
        self.assertListEqual(sorted(palabras_clave), palabras_esperadas) 
        self.assertNotIn("la", palabras_clave)
        self.assertNotIn("de", palabras_clave)
        self.assertNotIn("el", palabras_clave)

# Para ejecutar solo este archivo
if __name__ == '__main__':
    unittest.main()