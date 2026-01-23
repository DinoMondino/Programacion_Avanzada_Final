# python -m pytest --cov=modules tests/

import pytest
from app import app as flask_app
from modules.usuarios import db

@pytest.fixture
def app():
    # Seteamos TESTING antes de cualquier otra cosa
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"
    
    with flask_app.app_context():
        db.create_all() # Crea tablas en memoria
        yield flask_app
        db.session.remove()
        db.drop_all() # Borra tablas en memoria

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