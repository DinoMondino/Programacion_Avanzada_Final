import pytest
from modules.usuarios import Usuario, db, RolAdmin

def test_creacion_usuario(app):
    # Verifica que un usuario se cree correctamente en la BD
    with app.app_context():
        u = Usuario(username="testuser", password="123")
        db.session.add(u)
        db.session.commit()
        
        user_db = Usuario.query.filter_by(username="testuser").first()
        assert user_db is not None

def test_error_duplicados(app):
    # No debe permitir usernames duplicados.
    with app.app_context():
        u1 = Usuario(username="igual", password="1")
        db.session.add(u1)
        db.session.commit()

        u2 = Usuario(username="igual", password="2")
        db.session.add(u2)
        with pytest.raises(Exception):
            db.session.commit()