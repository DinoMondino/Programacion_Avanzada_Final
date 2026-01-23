# python -m pytest --cov=modules tests/

import pytest
from app import app as flask_app
from modules.usuarios import db

@pytest.fixture
def app():
    # Configuración para la app de prueba
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # Base de datos en memoria RAM, se borra automaticamente
        "SQLALCHEMY_TRACK_MODIFICATIONS": False, # Desactiva el seguimiento de modificaciones para ahorrar recursos
        "WTF_CSRF_ENABLED": False  # Desactiva los tokens de seguridad (CSRF) de los formularios.
    })

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
# Permite simular que un usuario entra a una URL o envía un formulario

@pytest.fixture
def gestor_servicio(app):
    from modules.gestor import Gestor_Reclamos
    from modules.reclamos import Clasificador
    # Usamos unas pocas stopwords para el test
    clasif = Clasificador(stopwords=["el", "la", "de", "que", "un"])
    return Gestor_Reclamos(db, clasif)
# Retorna el gestor listo para ser usado en las pruebas unitarias.