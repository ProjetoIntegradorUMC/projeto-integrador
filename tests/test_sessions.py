import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt

from app import db
from app.models import Session, User
from app.utils.sessions import create_session, revoke_session

SENHA = "SenhaForte123!"


def criar_usuario(flask_app, email="aluno@example.com"):
    with flask_app.app_context():
        user = User(
            username=email.split("@")[0],
            full_name="Aluno Teste",
            email=email,
            password_hash=bcrypt.hashpw(
                SENHA.encode("utf-8"), bcrypt.gensalt(rounds=4)
            ).decode("utf-8"),
            consent_given_at=datetime.now(timezone.utc),
            consent_version="1.0",
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def abrir_sessao(flask_app, user_id):
    with flask_app.app_context():
        _, token = create_session(user_id)
        return token


def cookie(token):
    return {"Cookie": f"session_id={token}"}


def test_token_valido_autentica(flask_app, client):
    token = abrir_sessao(flask_app, criar_usuario(flask_app))

    response = client.get("/auth/me", headers=cookie(token))

    assert response.status_code == 200
    assert response.get_json()["user"]["email"] == "aluno@example.com"


def test_token_invalido_e_recusado(flask_app, client):
    abrir_sessao(flask_app, criar_usuario(flask_app))

    assert client.get("/auth/me", headers=cookie("token-inexistente")).status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_token_expirado_e_recusado(flask_app, client):
    token = abrir_sessao(flask_app, criar_usuario(flask_app))
    with flask_app.app_context():
        sessao = Session.query.one()
        sessao.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()

    assert client.get("/auth/me", headers=cookie(token)).status_code == 401


def test_token_revogado_e_recusado(flask_app, client):
    token = abrir_sessao(flask_app, criar_usuario(flask_app))
    with flask_app.app_context():
        revoke_session(Session.query.one())

    assert client.get("/auth/me", headers=cookie(token)).status_code == 401


def test_banco_guarda_so_o_hash_do_token(flask_app):
    token = abrir_sessao(flask_app, criar_usuario(flask_app))

    with flask_app.app_context():
        assert "token" not in Session.__table__.columns
        sessao = Session.query.one()
        assert sessao.token_hash == hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert sessao.token_hash != token


def test_hash_vazado_do_banco_nao_serve_como_cookie(flask_app, client):
    abrir_sessao(flask_app, criar_usuario(flask_app))
    with flask_app.app_context():
        token_hash = Session.query.one().token_hash

    assert client.get("/auth/me", headers=cookie(token_hash)).status_code == 401


def test_fluxo_real_de_login_e_logout(flask_app, client):
    criar_usuario(flask_app)

    response = client.post(
        "/auth/login", json={"email": "aluno@example.com", "password": SENHA}
    )
    assert response.status_code == 200
    set_cookie = next(
        c for c in response.headers.getlist("Set-Cookie") if c.startswith("session_id=")
    )
    token = set_cookie.split(";")[0].split("=", 1)[1]

    # O cookie funciona, mas o banco só tem o hash dele.
    with flask_app.app_context():
        assert Session.query.one().token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert client.get("/auth/me", headers=cookie(token)).status_code == 200

    # O logout revoga a sessão no servidor.
    assert client.post("/auth/logout", headers=cookie(token)).status_code == 200
    assert client.get("/auth/me", headers=cookie(token)).status_code == 401


def test_excluir_usuario_remove_as_sessoes(flask_app):
    user_id = criar_usuario(flask_app)
    abrir_sessao(flask_app, user_id)

    with flask_app.app_context():
        db.session.delete(db.session.get(User, user_id))
        db.session.commit()
        assert Session.query.count() == 0