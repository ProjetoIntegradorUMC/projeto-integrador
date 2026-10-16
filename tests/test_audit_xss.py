import pytest

from app.models import PasswordResetLog, SecurityLog

PAYLOADS = [
    "<img src=x onerror=alert(1)>",
    "<script>alert(1)</script>",
    '"><svg onload=alert(1)>',
]


@pytest.mark.parametrize("payload", PAYLOADS)
def test_login_com_email_malicioso_e_registrado_literalmente(
    flask_app, client, admin_headers, payload
):
    # 1 - Tentativa de login anônima com e-mail malicioso é recusada.
    response = client.post(
        "/auth/login", json={"email": payload, "password": "qualquer"}
    )
    assert response.status_code == 401

    # 2 - O evento é preservado, com o e-mail exatamente como foi enviado.
    with flask_app.app_context():
        logs = SecurityLog.query.filter_by(event_type="login_failure").all()
        assert [log.email for log in logs] == [payload]

    # 3 - O endpoint do painel devolve o valor literal, como JSON (nunca HTML).
    response = client.get("/admin/logs", headers=admin_headers)
    assert response.status_code == 200
    assert response.mimetype == "application/json"

    data = response.get_json()
    event = next(e for e in data["recent_events"] if e["email"] == payload)
    assert event["type"] == "login_failure"
    assert data["metrics"]["login_failure"] == 1


@pytest.mark.parametrize("payload", PAYLOADS)
def test_forgot_password_com_email_malicioso_e_registrado_literalmente(
    flask_app, client, admin_headers, payload
):
    response = client.post("/auth/forgot-password", json={"email": payload})
    assert response.status_code == 200

    with flask_app.app_context():
        logs = PasswordResetLog.query.filter_by(event_type="failure").all()
        assert [log.email for log in logs] == [payload]

    response = client.get("/admin/logs", headers=admin_headers)
    assert response.status_code == 200
    event = next(
        e for e in response.get_json()["recent_events"] if e["email"] == payload
    )
    assert event["type"] == "password_failure"
