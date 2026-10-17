from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import bcrypt

from app import db
from app.models import User
from app.utils.rate_limit import LIMITS


PASSWORD = "SenhaForte123!"


def criar_usuario(flask_app, email="login@example.com"):
    with flask_app.app_context():
        user = User(
            username=email.split("@")[0],
            full_name="Usuário de Login",
            email=email,
            password_hash=bcrypt.hashpw(
                PASSWORD.encode(), bcrypt.gensalt(rounds=4)
            ).decode(),
            consent_given_at=datetime.now(timezone.utc),
            consent_version="1.0",
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def tentar_login(client, email, password="senha-incorreta", ip="127.0.0.1"):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
        environ_base={"REMOTE_ADDR": ip},
    )


def test_login_aplica_limite_e_reseta_contador_com_sucesso(flask_app, client):
    user_id = criar_usuario(flask_app)

    for tentativa in range(4):
        response = tentar_login(client, "login@example.com")
        assert response.status_code == 401
        with flask_app.app_context():
            user = db.session.get(User, user_id)
            assert user.failed_attempts == tentativa + 1
            assert user.locked_until is None

    response = tentar_login(client, "login@example.com")
    assert response.status_code == 423
    assert "Conta bloqueada por segurança" in response.get_json()["error"]
    with flask_app.app_context():
        user = db.session.get(User, user_id)
        assert user.failed_attempts == 5
        assert user.locked_until > datetime.now(timezone.utc)

    response = tentar_login(client, "login@example.com", PASSWORD)
    assert response.status_code == 423
    assert "Conta bloqueada por segurança" in response.get_json()["error"]
    assert "Tente novamente em" in response.get_json()["error"]

    with flask_app.app_context():
        user = db.session.get(User, user_id)
        user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()

    assert tentar_login(client, "login@example.com", PASSWORD).status_code == 200
    with flask_app.app_context():
        user = db.session.get(User, user_id)
        assert user.failed_attempts == 0
        assert user.locked_until is None


def test_login_conta_inexistente_nao_revela_conta_e_bloqueio_e_informado(
    flask_app, client
):
    user_id = criar_usuario(flask_app, "titular@example.com")
    for _ in range(5):
        tentar_login(client, "titular@example.com", ip="10.0.0.10")

    bloqueada = tentar_login(client, "titular@example.com", ip="10.0.0.11")
    inexistente = tentar_login(client, "nao-existe@example.com", ip="10.0.0.12")

    assert bloqueada.status_code == 423
    assert "Conta bloqueada por segurança" in bloqueada.get_json()["error"]
    assert inexistente.status_code == 401
    assert inexistente.get_json() == {"error": "Credenciais inválidas"}

    with flask_app.app_context():
        assert db.session.get(User, user_id).locked_until is not None


def test_login_incrementa_contador_sem_perder_falhas_concorrentes(flask_app):
    criar_usuario(flask_app, "concorrente@example.com")

    def request_login(index):
        with flask_app.test_client() as client:
            return tentar_login(
                client,
                "concorrente@example.com",
                ip=f"192.0.2.{index}",
            ).status_code

    with ThreadPoolExecutor(max_workers=5) as executor:
        statuses = list(executor.map(request_login, range(5)))

    assert all(status in (401, 423) for status in statuses)
    assert statuses.count(423) == 1
    with flask_app.app_context():
        user = User.query.filter_by(email="concorrente@example.com").one()
        assert user.failed_attempts == 5
        assert user.locked_until is not None


def test_login_tem_limite_complementar_por_ip(flask_app, client):
    for index in range(LIMITS["login"]["ip"][0] + 1):
        criar_usuario(flask_app, f"ip-{index}@example.com")
    limit = LIMITS["login"]["ip"][0]

    for index in range(limit):
        assert (
            tentar_login(
                client, f"ip-{index}@example.com", ip="198.51.100.10"
            ).status_code
            == 401
        )

    response = tentar_login(
        client, f"ip-{limit}@example.com", ip="198.51.100.10"
    )
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
