import pytest
from modules.usuarios import Usuario, db
from modules.reclamos import Reclamo
from modules.departamentos import Analitica

def test_clasificacion_y_adhesion(app, gestor_servicio):
    """Testea RF 116 (Clasificación) y RF 117 (Similares)."""
    with app.app_context():
        # Crear un usuario para los reclamos
        u = Usuario(username="autor", password="123")
        db.session.add(u)
        db.session.commit()

        # 1. Crear primer reclamo (debe clasificar a Informática por 'wifi')
        res1 = gestor_servicio.crear_reclamo("No funciona el wifi, en el aula de programación no hay internet", None, u.id)
        assert res1["status"] == "ok"
        
        rec1 = Reclamo.query.first()
        assert rec1.departamento_id == "D_INFORMATICA"
        assert rec1.estado == "pendiente"

        # 2. Crear uno similar (debe adherir en lugar de crear nuevo)
        # Usamos el mismo inicio de texto para el .like() del gestor
        res2 = gestor_servicio.crear_reclamo("No funciona el wifi, el internet va lento", None, u.id)
        assert res2["status"] == "similar"
        assert "adherido" in res2["mensaje"]

def test_analitica_palabras_clave(app, gestor_servicio):
    """RF 131: Frecuencia de las 15 palabras más comunes."""
    with app.app_context():
        u = Usuario(username="u1", password="1")
        db.session.add(u)
        db.session.commit()

        # 'problema' aparece 3 veces, 'el' es stopword
        gestor_servicio.crear_reclamo("problema grave problema grave problema", None, u.id)

        analitica = Analitica(gestor_servicio)
        datos = analitica.obtener_datos_dashboard("D_SECRETARIA")

        assert "problema" in datos["frecuencia"]
        assert datos["frecuencia"]["problema"] == 3
        assert "el" not in datos["frecuencia"]