# python -m pytest --cov=modules tests/

import pytest
from app import app as flask_app
from modules.usuarios import db

@pytest.fixture
def app():
    # Configuración de prueba
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "WTF_CSRF_ENABLED": False  # Desactiva CSRF para facilitar tests de formularios
    })

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def gestor_servicio(app):
    from modules.gestor import Gestor_Reclamos
    from modules.reclamos import Clasificador
    # Usamos unas pocas stopwords para el test
    clasif = Clasificador(stopwords=["el", "la", "de", "que", "un"])
    return Gestor_Reclamos(db, clasif)