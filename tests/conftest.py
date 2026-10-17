import os
from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet

# O ambiente é configurado antes de importar a aplicação. Os testes não devem
# depender do .env local nem apontar acidentalmente para o banco de desenvolvimento.
TEST_DB_NAME = "projeto_integrador_test"
os.environ["DB_NAME"] = TEST_DB_NAME
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_APP_USER"] = "mentory_app"
os.environ["DB_APP_PASSWORD"] = "mentory_app"
os.environ["SECRET_KEY"] = "chave-somente-para-testes"
os.environ["TOTP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["SECURE_COOKIES"] = "false"

from app import create_app, db
from app.models import User
from app.utils.sessions import create_session


@pytest.fixture()
def flask_app():
    flask_app = create_app()

    # Trava de segurança para nunca derrubar tabelas fora do banco de teste.
    assert flask_app.config["SQLALCHEMY_DATABASE_URI"].database == TEST_DB_NAME

    with flask_app.app_context():
        db.drop_all()
        db.create_all()

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(flask_app):
    # Sem cookie jar: o cookie do admin vai no header Cookie de cada teste.
    return flask_app.test_client(use_cookies=False)


@pytest.fixture()
def admin_headers(flask_app):
    """Cria o admin provisionado (is_admin=True) com sessão ativa e devolve o cookie."""
    with flask_app.app_context():
        admin = User(
            username="admin",
            full_name="Admin Teste",
            email="admin-teste@example.com",
            is_admin=True,
            password_hash="hash-nao-usado-no-teste",
            consent_given_at=datetime.now(timezone.utc),
            consent_version="1.0",
        )
        db.session.add(admin)
        db.session.commit()
        _, token = create_session(admin.id)

    return {"Cookie": f"session_id={token}"}
