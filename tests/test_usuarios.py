import unittest
from modules.usuarios import UsuarioFinal, JefeDepartamento, SecretarioTecnico, Claustro, EstadoReclamo
from modules.reclamos import Clasificador
from modules.gestor import Gestor_Reclamos
from modules.departamentos import Analitica

class TestUsuarios(unittest.TestCase):
    def setUp(self):
        """Configuración usando argumentos con nombre para evitar TypeErrors."""
        self.clasificador = Clasificador(stopwords=["el", "la"])
        self.gestor = Gestor_Reclamos(self.clasificador)
        self.analitica = Analitica(self.gestor)
        
        self.estudiante = UsuarioFinal(
            id_usuario="U001", email="estu@uner.edu.ar", usuario="pepe", 
            contrasenia_hash="hash", nombre="Pepe", apellido="Perez",
            claustro=Claustro.ESTUDIANTE, gestor_servicio=self.gestor
        )
        
        self.jefe = JefeDepartamento(
            id_usuario="J001", email="jefe@uner.edu.ar", usuario="carlos", 
            contrasenia_hash="hash", nombre="Carlos", apellido="Gomez",
            claustro=Claustro.PAYS, departamento_id="D_INFRAESTRUCTURA", 
            gestor_servicio=self.gestor, analitica_servicio=self.analitica
        )

        self.secretario = SecretarioTecnico(
            id_usuario="S001", email="sec@uner.edu.ar", usuario="ana", 
            contrasenia_hash="hash", nombre="Ana", apellido="Lopez",
            claustro=Claustro.PAYS, gestor_servicio=self.gestor, 
            analitica_servicio=self.analitica
        )

    def test_flujo_estudiante(self):
        """Test de creación de reclamo por usuario final."""
        res = self.estudiante.crear_reclamo("No hay luz en el aula", None)
        self.assertIn("R0001", res)

    def test_permisos_jefe(self):
        """El jefe puede gestionar reclamos de su departamento."""
        self.gestor.crear_reclamo("Gotera en pasillo", None, "U001") # R0001 -> INFRA
        exito = self.jefe.gestionar_reclamo("R0001", EstadoReclamo.RESUELTO)
        self.assertTrue(exito)

    def test_secretario_global(self):
        """El secretario técnico puede ver todo."""
        self.gestor.crear_reclamo("Falla internet", None, "U001")
        reclamos = self.secretario.listar_reclamos_pendientes()
        self.assertGreaterEqual(len(reclamos), 1)

    def test_ver_mis_reclamos(self):
        """El usuario ve sus reclamos creados."""
        self.estudiante.crear_reclamo("Mi reclamo", None)
        mis = self.estudiante.ver_mis_reclamos()
        self.assertEqual(len(mis), 1)