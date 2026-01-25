import pytest
from modules.reclamos import Reclamo, EstadoReclamo
from modules.usuarios import Usuario
from app import db

def test_clasificacion_y_adhesion(app, gestor_servicio):
    # Testea la clasificación automática y la posibilidad de adherirse manualmente.
    with app.app_context():
        # 1. Crea dos usuarios, u1 será el autor, u2 será el que se adhiere
        u1 = Usuario(username="autor", password="123")
        u2 = Usuario(username="vecino", password="123")
        db.session.add_all([u1, u2])
        db.session.commit()

        # 2. El gestor debe devolver "creado" y asignar D_INFORMATICA por la palabra 'wifi'
        res1 = gestor_servicio.crear_reclamo(
            "No funciona el wifi, en el aula de programación no hay internet",
            u1.id,  # El ID del usuario va SEGUNDO ahora
            None    # El adjunto va TERCERO
        )
        
        assert res1["status"] == "creado"
        id_reclamo = res1["reclamo_id"]
        
        rec1 = Reclamo.query.get(id_reclamo)
        assert rec1.departamento_id == "D_INFORMATICA"
        assert rec1.estado == EstadoReclamo.PENDIENTE.value
        assert rec1.usuario_id == u1.id

        # 3. Simulamos un nuevo contenido que es semánticamente igual al primero
        contenido_parecido = "El wifi del aula de programación no funciona, no tengo internet"
        historial = {r.id: r for r in Reclamo.query.all()}

        # Le preguntamos al clasificador si encuentra algo parecido
        similares_detectados = gestor_servicio.clasificador_servicio.buscar_similares(contenido_parecido, historial)

        # El sistema debe haber encontrado al menos un reclamo similar con ID igual al del primer reclamo.
        assert len(similares_detectados) > 0
        assert similares_detectados[0] == id_reclamo

        # 4. Probamos que el usuario 2 pueda adherirse al primer reclamo
        exito_adhesion = gestor_servicio.adherirse_a_reclamo(id_reclamo, u2.id)
        assert exito_adhesion is True
        
        # Verificamos en la base de datos
        reclamo_actualizado = Reclamo.query.get(id_reclamo)
        assert u2 in reclamo_actualizado.seguidores
        
        # 5. No debería permitir que el autor se adhiera a su propio reclamo
        reintento_autor = gestor_servicio.adherirse_a_reclamo(id_reclamo, u1.id)
        assert reintento_autor is False

def test_gestion_estados_y_derivacion(app, gestor_servicio):
    # Testea el cambio de estados y la derivación manual de departamentos.
    with app.app_context():
        u = Usuario(username="admin_test", password="123") # Creamos un usuario Secretario
        db.session.add(u)
        db.session.commit()
        # Creamos un reclamo inicial que se clasifica por defecto en el departamento secretaria
        res = gestor_servicio.crear_reclamo("Caño roto en patio", None, u.id)
        rec_id = res["reclamo_id"]
        
        # Testear derivación manual
        gestor_servicio.derivar_reclamo(rec_id, "D_MANTENIMIENTO")
        rec = Reclamo.query.get(rec_id)
        assert rec.departamento_id == "D_MANTENIMIENTO"
        
        # Testear cambio de estado a RESUELTO
        exito = gestor_servicio.gestionar_estado_reclamo(rec_id, "resuelto")
        assert exito is True
        assert rec.estado == "resuelto"