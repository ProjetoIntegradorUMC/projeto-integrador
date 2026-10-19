from unittest.mock import MagicMock, patch
import pytest
from flask import Flask

from app.routes.auth import (
    login,
    register,
    forgot_password,
    DUMMY_PASSWORD_HASH,
)

app = Flask(__name__)
app.secret_key = "chave-somente-para-testes"
app.config["TESTING"] = True


@pytest.fixture
def existing_user_mock():
    user = MagicMock()
    user.id = 101
    user.email = "aluno.existente@mentory.edu.br"
    user.username = "aluno_existente"
    user.full_name = "Aluno Existente"
    user.password_hash = "$2b$12$KIXeF97k3rY1n7.v5eN8u.w8H6z1g9B1e5X8v1A5y1C4e7G9j2L0u"
    user.locked_until = None
    user.failed_attempts = 0
    user.two_factor_enabled = False
    return user


def test_login_retorna_mesmo_status_e_payload_para_email_existente_e_inexistente(existing_user_mock):
    """
    Garante que tentativas de login com e-mail inexistente e e-mail existente
    com senha errada retornam rigorosamente a mesma resposta (HTTP 401 e mensagem genérica),
    atendendo ao achado V11 da auditoria de segurança (redução de enumeração).
    """
    # Cenário 1: Usuário existente com senha incorreta
    with app.test_request_context(
        "/auth/login",
        method="POST",
        json={"email": existing_user_mock.email, "password": "senha_incorreta_123"},
    ):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth.safe_check_password", return_value=False), \
             patch("app.routes.auth._record_login_failure", return_value=(1, None)), \
             patch("app.routes.auth.log_security_event"):

            mock_filter = MagicMock()
            mock_filter.first.return_value = existing_user_mock
            mock_query.filter_by.return_value = mock_filter

            resp_existente, status_existente = login()

    # Cenário 2: Usuário inexistente
    with app.test_request_context(
        "/auth/login",
        method="POST",
        json={"email": "naoexiste@mentory.edu.br", "password": "senha_qualquer_123"},
    ):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth.safe_check_password", return_value=False), \
             patch("app.routes.auth.log_security_event"):

            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.filter_by.return_value = mock_filter

            resp_inexistente, status_inexistente = login()

    # Ambas as respostas devem ser absolutamente idênticas para o cliente externo
    assert status_existente == 401
    assert status_inexistente == 401
    assert resp_existente.get_json() == {"error": "Credenciais inválidas"}
    assert resp_inexistente.get_json() == {"error": "Credenciais inválidas"}


def test_login_executa_verificacao_dummy_para_usuario_inexistente_mitigando_timing_attack():
    """
    Garante a mitigação de ataque de temporização (Timing Attack):
    Quando o usuário não existe, o bcrypt dummy é obrigatoriamente executado.
    """
    with app.test_request_context(
        "/auth/login",
        method="POST",
        json={"email": "usuario_fantasma@mentory.edu.br", "password": "senha_teste_123"},
    ):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth.safe_check_password") as mock_check, \
             patch("app.routes.auth.log_security_event") as mock_log:

            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.filter_by.return_value = mock_filter

            resp, status = login()

            assert status == 401
            assert resp.get_json() == {"error": "Credenciais inválidas"}

            # O safe_check_password foi invocado com o hash dummy para equalizar o tempo de resposta
            mock_check.assert_called_once_with("senha_teste_123", DUMMY_PASSWORD_HASH)

            # Diagnóstico interno registrado para a auditoria sem vazar na resposta pública
            mock_log.assert_called_once_with(
                email="usuario_fantasma@mentory.edu.br",
                event_type="login_failure",
                failure_reason="user_not_found",
            )


def test_login_registra_diagnostico_interno_distinto_sem_vazar_na_resposta(existing_user_mock):
    """
    Valida que o diagnóstico interno diferencia falha de senha de conta inexistente
    nos logs de auditoria enquanto a resposta pública permanece indistinguível.
    """
    with app.test_request_context(
        "/auth/login",
        method="POST",
        json={"email": existing_user_mock.email, "password": "senha_errada_123"},
    ):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth.safe_check_password", return_value=False), \
             patch("app.routes.auth._record_login_failure", return_value=(1, None)), \
             patch("app.routes.auth.log_security_event") as mock_log:

            mock_filter = MagicMock()
            mock_filter.first.return_value = existing_user_mock
            mock_query.filter_by.return_value = mock_filter

            resp, status = login()

            assert status == 401
            assert resp.get_json() == {"error": "Credenciais inválidas"}

            # Diagnóstico interno gravou invalid_password com user_id
            mock_log.assert_called_once_with(
                email=existing_user_mock.email,
                event_type="login_failure",
                user_id=existing_user_mock.id,
                failure_reason="invalid_password",
            )


def test_register_respostas_identicas_para_colisao_de_email_e_colisao_de_username(existing_user_mock):
    """
    Garante que o endpoint de cadastro retorne mensagem genérica combinada (HTTP 409)
    sem revelar se o conflito foi no username ou no e-mail.
    """
    payload_colisao_email = {
        "full_name": "Novo Aluno",
        "username": "usuario_novo_123",
        "email": existing_user_mock.email,  # colisão por e-mail
        "password": "senhaValida123#",
        "consent_given": True,
    }

    payload_colisao_username = {
        "full_name": "Novo Aluno 2",
        "username": existing_user_mock.username,  # colisão por username
        "email": "email_novo_123@mentory.edu.br",
        "password": "senhaValida123#",
        "consent_given": True,
    }

    # Tentativa 1: colisão apenas por e-mail
    with app.test_request_context("/auth/register", method="POST", json=payload_colisao_email):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth._dummy_bcrypt_hash"), \
             patch("app.routes.auth.log_security_event"):

            mock_query.filter.return_value.first.return_value = existing_user_mock
            resp_email, status_email = register()

    # Tentativa 2: colisão apenas por username
    with app.test_request_context("/auth/register", method="POST", json=payload_colisao_username):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth._dummy_bcrypt_hash"), \
             patch("app.routes.auth.log_security_event"):

            mock_query.filter.return_value.first.return_value = existing_user_mock
            resp_user, status_user = register()

    assert status_email == 409
    assert status_user == 409
    assert resp_email.get_json() == {"error": "Usuário ou e-mail já cadastrado"}
    assert resp_user.get_json() == {"error": "Usuário ou e-mail já cadastrado"}


def test_register_executa_dummy_hash_e_registra_auditoria_em_colisao(existing_user_mock):
    """
    Valida que conflitos de unicidade no cadastro executam _dummy_bcrypt_hash
    para balancear a latência da requisição e registram o evento na auditoria interna.
    """
    payload = {
        "full_name": "Teste Colisão",
        "username": existing_user_mock.username,
        "email": "novo@mentory.edu.br",
        "password": "senhaValida123#",
        "consent_given": True,
    }

    with app.test_request_context("/auth/register", method="POST", json=payload):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth._dummy_bcrypt_hash") as mock_dummy_hash, \
             patch("app.routes.auth.log_security_event") as mock_log:

            mock_query.filter.return_value.first.return_value = existing_user_mock
            resp, status = register()

            assert status == 409
            assert resp.get_json() == {"error": "Usuário ou e-mail já cadastrado"}
            mock_dummy_hash.assert_called_once_with("senhaValida123#")
            mock_log.assert_called_once_with(
                email="novo@mentory.edu.br",
                event_type="registration_conflict",
                failure_reason="duplicate_username_or_email",
            )


def test_forgot_password_retorna_mesma_resposta_para_email_existente_e_inexistente(existing_user_mock):
    """
    Valida consistência completa de anti-enumeração:
    O endpoint de esqueci a senha responde exatamente a mesma mensagem genérica com HTTP 200.
    """
    # E-mail existente
    with app.test_request_context("/auth/forgot-password", method="POST", json={"email": existing_user_mock.email}):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth.db.session"), \
             patch("app.routes.auth.send_email"), \
             patch("app.routes.auth.log_password_reset_event"):

            mock_query.filter_by.return_value.first.return_value = existing_user_mock
            resp_existente, status_existente = forgot_password()

    # E-mail inexistente
    with app.test_request_context("/auth/forgot-password", method="POST", json={"email": "inexistente@mentory.edu.br"}):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth.log_password_reset_event"):

            mock_query.filter_by.return_value.first.return_value = None
            resp_inexistente, status_inexistente = forgot_password()

    mensagem_esperada = "Se o e-mail estiver cadastrado, você receberá um link de recuperação."
    assert status_existente == 200
    assert status_inexistente == 200
    assert resp_existente.get_json() == {"message": mensagem_esperada}
    assert resp_inexistente.get_json() == {"message": mensagem_esperada}


def test_fluxo_legitimo_de_cadastro_e_login_permanece_funcional(existing_user_mock):
    """
    Garante que os fluxos legítimos de cadastro e de login continuam funcionando com sucesso.
    """
    # 1. Cadastro bem-sucedido
    payload_cadastro = {
        "full_name": "Aluno Novo",
        "username": "aluno_novo",
        "email": "aluno_novo@mentory.edu.br",
        "password": "senhaForte123!",
        "consent_given": True,
    }
    with app.test_request_context("/auth/register", method="POST", json=payload_cadastro):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth.bcrypt.hashpw", return_value=b"$2b$12$newhashedpassword"), \
             patch("app.routes.auth.db.session"):

            mock_query.filter.return_value.first.return_value = None
            resp_cad, status_cad = register()

            assert status_cad == 201
            assert resp_cad.get_json() == {"message": "Usuário cadastrado com sucesso"}

    # 2. Login bem-sucedido
    payload_login = {
        "email": existing_user_mock.email,
        "password": "senhaCorreta123!",
    }
    mock_session = MagicMock()
    with app.test_request_context("/auth/login", method="POST", json=payload_login):
        with patch("app.routes.auth.is_limited", return_value=None), \
             patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth.safe_check_password", return_value=True), \
             patch("app.routes.auth._reset_login_failures", return_value=True), \
             patch("app.routes.auth.log_security_event"), \
             patch("app.routes.auth.create_session", return_value=(mock_session, "token_opaco_sessao")):

            mock_query.filter_by.return_value.first.return_value = existing_user_mock
            resp_log, status_log = login()

            assert status_log == 200
            data_log = resp_log.get_json()
            assert data_log["message"] == "Login realizado com sucesso"
            assert data_log["requires_2fa"] is False
            assert data_log["user"]["email"] == existing_user_mock.email
            assert "session_id=token_opaco_sessao" in resp_log.headers.get("Set-Cookie", "")
