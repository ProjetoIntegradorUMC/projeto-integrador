from unittest.mock import MagicMock, patch
import pytest
from flask import Flask

from app.utils.validators import (
    validate_password_policy,
    safe_check_password,
    get_json_payload,
    PASSWORD_MIN_LENGTH,
    PASSWORD_MAX_BYTES,
)
from app.routes.auth import register, login, reset_password

app = Flask(__name__)
app.secret_key = "chave-somente-para-testes"
app.config["TESTING"] = True


def test_validate_password_policy_minimo_caracteres():
    """Senhas com menos de 8 caracteres devem ser recusadas (Issue #88 / V19)."""
    is_valid, msg = validate_password_policy("1234567")
    assert not is_valid
    assert f"mínimo {PASSWORD_MIN_LENGTH}" in msg


def test_validate_password_policy_limite_72_bytes_ascii():
    """Valida limite exato de 72 bytes do algoritmo bcrypt."""
    senha_72_bytes = "A" * 72
    is_valid, msg = validate_password_policy(senha_72_bytes)
    assert is_valid
    assert msg == ""

    senha_73_bytes = "A" * 73
    is_valid_73, msg_73 = validate_password_policy(senha_73_bytes)
    assert not is_valid_73
    assert f"não pode exceder {PASSWORD_MAX_BYTES} bytes" in msg_73


def test_validate_password_policy_multibyte_utf8():
    """Garante que caracteres especiais multibyte contam por byte UTF-8 e não por caractere."""
    # O caractere '🔒' ocupa 4 bytes em UTF-8. 19 * 4 = 76 bytes (> 72 bytes).
    senha_multibyte_longa = "🔒" * 19
    is_valid, msg = validate_password_policy(senha_multibyte_longa)
    assert not is_valid
    assert f"não pode exceder {PASSWORD_MAX_BYTES} bytes" in msg


def test_validate_password_policy_tipos_invalidos():
    """Entradas que não sejam string são rejeitadas de forma controlada."""
    for entrada in [None, 12345678, ["senha1234"], {"senha": "123"}]:
        is_valid, msg = validate_password_policy(entrada)
        assert not is_valid
        assert "texto válido" in msg


def test_safe_check_password_com_senha_acima_72_bytes_nao_lanca_excecao():
    """Garante que senhas longas no checkpw não lancem ValueError (erro 500)."""
    fake_hash = "$2b$12$e8Y5tG1h.Hw3YQc2n8pDCO7k6Uv8sRzP2b9K1l3m4n5o6p7q8r9s0"
    senha_gigante = "B" * 500

    # Não deve subir ValueError nem causar 500; deve retornar False de forma graciosa
    resultado = safe_check_password(senha_gigante, fake_hash)
    assert resultado is False


def test_safe_check_password_com_tipos_invalidos():
    """Tipos não suportados retornam False sem exceção."""
    assert safe_check_password(None, "hash") is False
    assert safe_check_password(123456, "hash") is False
    assert safe_check_password("senha", None) is False


def test_get_json_payload_com_corpos_invalidos():
    """Protege rotas contra corpos de requisição vazios, primitivos ou listas."""
    # Caso 1: Payload vazio
    with app.test_request_context("/", method="POST"):
        assert get_json_payload(request=Flask(__name__).test_request_context().request) == {}

    # Caso 2: Payload é lista JSON [1, 2, 3] em vez de dicionário
    with app.test_request_context("/", method="POST", json=[1, 2, 3]):
        from flask import request
        assert get_json_payload(request) == {}

    # Caso 3: Payload é dicionário válido
    with app.test_request_context("/", method="POST", json={"email": "teste@exemplo.com"}):
        from flask import request
        assert get_json_payload(request) == {"email": "teste@exemplo.com"}


@pytest.mark.parametrize(
    "password, mensagem_esperada",
    [
        ("123", "no mínimo 8"),
        ("X" * 73, "não pode exceder 72 bytes"),
    ],
    ids=["senha_curta", "senha_acima_de_72_bytes"],
)
def test_register_rejeita_senha_fora_dos_limites(client, password, mensagem_esperada):
    """Endpoint de registro rejeita senhas curtas ou > 72 bytes com HTTP 400 sem crash."""
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Teste",
            "username": "teste",
            "email": "teste@exemplo.com",
            "password": password,
            "consent_given": True,
        },
    )
    assert response.status_code == 400
    assert mensagem_esperada in response.get_json()["error"]

def test_login_com_senha_acima_de_72_bytes_retorna_401_sem_erro_500():
    """Login com senha gigantesca não gera erro 500 no bcrypt, retornando 401 Credenciais inválidas."""
    mock_user = MagicMock()
    mock_user.email = "usuario@exemplo.com"
    mock_user.password_hash = "$2b$12$somevalidhashstringmock"
    mock_user.locked_until = None
    mock_user.failed_attempts = 0

    with app.test_request_context(
        "/auth/login",
        method="POST",
        json={"email": "usuario@exemplo.com", "password": "A" * 200},
    ):
        with patch("app.routes.auth.User.query") as mock_query, \
             patch("app.routes.auth.db.session"):

            mock_filter = MagicMock()
            mock_filter.first.return_value = mock_user
            mock_query.filter_by.return_value = mock_filter

            resp, code = login()
            assert code == 401
            assert "Credenciais inválidas" in resp.get_json()["error"]
