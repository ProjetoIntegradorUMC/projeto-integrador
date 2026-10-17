from datetime import datetime, timedelta, timezone

import app.utils.rate_limit as rate_limit
from app import db
from app.models import RateLimitCounter, SecurityLog, User

IP_OUTRO = "10.0.0.9"


def criar_usuario(flask_app, email):
    with flask_app.app_context():
        db.session.add(
            User(
                username=email.split("@")[0],
                full_name="Usuário Teste",
                email=email,
                password_hash="hash-nao-usado-no-teste",
                consent_given_at=datetime.now(timezone.utc),
                consent_version="1.0",
            )
        )
        db.session.commit()


def cadastro_vazio(client, ip="127.0.0.1", json=None):
    # Corpo sem os campos obrigatórios responde 400 sem passar pelo bcrypt.
    return client.post(
        "/auth/register", json=json or {}, environ_base={"REMOTE_ADDR": ip}
    )


def recuperar(client, email, ip="127.0.0.1"):
    return client.post(
        "/auth/forgot-password",
        json={"email": email},
        environ_base={"REMOTE_ADDR": ip},
    )


def test_register_bloqueia_acima_do_limite_por_ip(client):
    limite = rate_limit.LIMITS["register"]["ip"][0]
    for _ in range(limite):
        assert cadastro_vazio(client).status_code == 400

    response = cadastro_vazio(client)

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert "Muitas tentativas" in response.get_json()["error"]
    # O limite é por IP: outro IP não é afetado.
    assert cadastro_vazio(client, ip=IP_OUTRO).status_code == 400


def test_register_libera_depois_da_janela(client, monkeypatch):
    limite, janela = rate_limit.LIMITS["register"]["ip"]
    for _ in range(limite):
        cadastro_vazio(client)
    assert cadastro_vazio(client).status_code == 429

    depois = rate_limit._now() + timedelta(seconds=janela + 1)
    monkeypatch.setattr(rate_limit, "_now", lambda: depois)

    assert cadastro_vazio(client).status_code == 400


def test_cadastro_legitimo_continua_funcionando(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Aluno Teste",
            "username": "aluno",
            "email": "aluno@example.com",
            "password": "SenhaForte123!",
            "consent_given": True,
        },
    )

    assert response.status_code == 201


def test_bloqueio_e_registrado_uma_vez_e_sem_segredos(flask_app, client):
    limite = rate_limit.LIMITS["register"]["ip"][0]
    corpo = {"email": "abusivo@example.com", "password": "segredo-nao-logar"}
    for _ in range(limite + 3):
        cadastro_vazio(client, json=corpo)

    with flask_app.app_context():
        logs = SecurityLog.query.filter_by(event_type="rate_limited").all()
        assert len(logs) == 1
        assert logs[0].failure_reason == "register_ip"
        assert logs[0].email == "abusivo@example.com"
        assert "segredo-nao-logar" not in f"{logs[0].email}{logs[0].failure_reason}"

        # A chave do contador não guarda o IP nem o e-mail em texto puro.
        chaves = [c.key for c in RateLimitCounter.query.all()]
        assert chaves
        assert all("127.0.0.1" not in chave for chave in chaves)


def test_forgot_password_bloqueia_acima_do_limite_por_ip(flask_app, client):
    criar_usuario(flask_app, "existe@example.com")
    limite = rate_limit.LIMITS["forgot_password"]["ip"][0]
    for i in range(limite):
        assert recuperar(client, f"x{i}@example.com").status_code == 200

    # Bloqueia igual para e-mail existente e inexistente.
    assert recuperar(client, "existe@example.com").status_code == 429
    assert recuperar(client, "naoexiste@example.com").status_code == 429


def test_forgot_password_resposta_igual_para_existente_e_inexistente(
    flask_app, client, monkeypatch
):
    enviados = []
    monkeypatch.setattr("app.routes.auth.send_email", lambda *a, **k: enviados.append(a))
    criar_usuario(flask_app, "existe@example.com")

    r_existe = recuperar(client, "existe@example.com")
    r_nao_existe = recuperar(client, "naoexiste@example.com")

    assert r_existe.status_code == r_nao_existe.status_code == 200
    assert r_existe.get_json() == r_nao_existe.get_json()
    assert len(enviados) == 1


def test_falha_no_envio_nao_revela_que_a_conta_existe(flask_app, client, monkeypatch):
    def smtp_fora_do_ar(*args, **kwargs):
        raise RuntimeError("smtp fora do ar")

    monkeypatch.setattr("app.routes.auth.send_email", smtp_fora_do_ar)
    criar_usuario(flask_app, "existe@example.com")

    r_existe = recuperar(client, "existe@example.com")
    r_nao_existe = recuperar(client, "naoexiste@example.com")

    assert r_existe.status_code == r_nao_existe.status_code == 200
    assert r_existe.get_json() == r_nao_existe.get_json()


def test_forgot_password_limita_envios_por_email(flask_app, client, monkeypatch):
    enviados = []
    monkeypatch.setattr("app.routes.auth.send_email", lambda *a, **k: enviados.append(a))
    criar_usuario(flask_app, "vitima@example.com")
    limite = rate_limit.LIMITS["forgot_password"]["email"][0]

    # IPs diferentes, para não esbarrar no limite por IP.
    respostas = [
        recuperar(client, "vitima@example.com", ip=f"10.0.1.{i}")
        for i in range(limite + 3)
    ]

    assert all(r.status_code == 200 for r in respostas)
    assert all(r.get_json() == respostas[0].get_json() for r in respostas)
    assert len(enviados) == limite
