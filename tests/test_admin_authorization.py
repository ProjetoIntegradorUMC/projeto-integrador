from datetime import datetime, timezone

from app import db
from app.models import User
from app.utils.sessions import create_session


def criar_usuario(flask_app, email, is_admin=False):
    """Cria o usuário direto no banco e devolve o header com o cookie de sessão."""
    with flask_app.app_context():
        user = User(
            username=email.split("@")[0],
            full_name="Usuário Teste",
            email=email,
            password_hash="hash-nao-usado-no-teste",
            consent_given_at=datetime.now(timezone.utc),
            consent_version="1.0",
            is_admin=is_admin,
        )
        db.session.add(user)
        db.session.commit()
        _, token = create_session(user.id)
        return {"Cookie": f"session_id={token}"}


def test_email_do_antigo_admin_email_nao_da_privilegio(
    flask_app, client, monkeypatch
):
    monkeypatch.setenv("ADMIN_EMAIL", "chefe@example.com")
    headers = criar_usuario(flask_app, "chefe@example.com")

    response = client.get("/admin/logs", headers=headers)

    assert response.status_code == 403


def test_sem_administrador_provisionado_painel_fica_inacessivel(flask_app, client):
    headers = criar_usuario(flask_app, "comum@example.com")

    assert client.get("/admin/logs", headers=headers).status_code == 403
    assert client.get("/admin/logs").status_code == 401


def test_administrador_provisionado_acessa_o_painel(flask_app, client):
    headers = criar_usuario(flask_app, "admin@example.com", is_admin=True)

    response = client.get("/admin/logs", headers=headers)

    assert response.status_code == 200


def test_cadastro_nao_concede_admin(flask_app, client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Atacante",
            "username": "atacante",
            "email": "atacante@example.com",
            "password": "SenhaForte123!",
            "consent_given": True,
            "is_admin": True,
        },
    )
    assert response.status_code == 201

    with flask_app.app_context():
        user = User.query.filter_by(email="atacante@example.com").one()
        assert user.is_admin is False


def test_comando_provision_admin_concede_e_revoga(flask_app, client):
    criar_usuario(flask_app, "futuro-admin@example.com")
    runner = flask_app.test_cli_runner()

    result = runner.invoke(
        args=["provision-admin", "futuro-admin@example.com"], input="y\n"
    )
    assert result.exit_code == 0
    with flask_app.app_context():
        assert User.query.filter_by(email="futuro-admin@example.com").one().is_admin

    result = runner.invoke(
        args=["provision-admin", "futuro-admin@example.com", "--revoke"], input="y\n"
    )
    assert result.exit_code == 0
    with flask_app.app_context():
        assert not User.query.filter_by(email="futuro-admin@example.com").one().is_admin


def test_comando_provision_admin_recusa_email_inexistente(flask_app):
    runner = flask_app.test_cli_runner()

    result = runner.invoke(args=["provision-admin", "ninguem@example.com"])

    assert result.exit_code != 0