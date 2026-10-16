from unittest.mock import MagicMock, patch
import pytest
from flask import Flask

from app.routes.lgpd import delete_account
from app.routes.auth import revoke_consent

app = Flask(__name__)
app.config["TESTING"] = True


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 42
    # bcrypt hash de teste (ou hash simulado)
    user.password_hash = "$2b$12$somehashedpasswordstring"
    return user


@pytest.fixture
def mock_session_obj():
    s = MagicMock()
    s.token = "valid_session_token_123"
    return s


def test_delete_account_sem_autenticacao_retorna_401(mock_user):
    """Requisições anônimas à exclusão de conta são barradas."""
    with app.test_request_context("/lgpd/delete", method="DELETE", json={"password": "qualquersenhadeveriaserbloqueada"}):
        with patch("app.utils.sessions.get_current_session", return_value=(None, None)):
            response, status_code = delete_account()

            assert status_code == 401
            assert "Acesso não autorizado" in response.get_json()["error"]


def test_delete_account_sem_fornecer_senha_retorna_400(mock_user, mock_session_obj):
    """Exclusão sem envio do campo password é rejeitada com 400 (Issue #91)."""
    with app.test_request_context("/lgpd/delete", method="DELETE", json={}):
        with patch("app.utils.sessions.get_current_session", return_value=(mock_session_obj, mock_user)), \
             patch("app.routes.lgpd.db.session") as mock_db_session:

            response, status_code = delete_account()

            assert status_code == 400
            assert "A confirmação de senha é obrigatória" in response.get_json()["error"]
            mock_db_session.delete.assert_not_called()
            mock_db_session.commit.assert_not_called()


def test_delete_account_com_senha_incorreta_retorna_401(mock_user, mock_session_obj):
    """Exclusão com senha incorreta é rejeitada com 401 e não apaga o usuário."""
    with app.test_request_context("/lgpd/delete", method="DELETE", json={"password": "senha_errada"}):
        with patch("app.utils.sessions.get_current_session", return_value=(mock_session_obj, mock_user)), \
             patch("app.routes.lgpd.bcrypt.checkpw", return_value=False), \
             patch("app.routes.lgpd.db.session") as mock_db_session:

            response, status_code = delete_account()

            assert status_code == 401
            assert "Senha incorreta" in response.get_json()["error"]
            mock_db_session.delete.assert_not_called()
            mock_db_session.commit.assert_not_called()


def test_delete_account_com_senha_correta_exclui_e_limpa_cookie(mock_user, mock_session_obj):
    """Exclusão com senha válida elimina o usuário no banco e expira cookie de sessão."""
    with app.test_request_context("/lgpd/delete", method="DELETE", json={"password": "senha_correta"}):
        with patch("app.utils.sessions.get_current_session", return_value=(mock_session_obj, mock_user)), \
             patch("app.routes.lgpd.bcrypt.checkpw", return_value=True), \
             patch("app.routes.lgpd.db.session") as mock_db_session:

            response, status_code = delete_account()

            assert status_code == 200
            assert "excluídos com sucesso" in response.get_json()["message"]
            mock_db_session.delete.assert_called_once_with(mock_user)
            mock_db_session.commit.assert_called_once()
            
            # Garante que o cookie de sessão é invalidado na resposta
            set_cookie_header = response.headers.get("Set-Cookie")
            assert set_cookie_header is not None
            assert "session_id=;" in set_cookie_header or "Expires=Thu, 01 Jan 1970" in set_cookie_header


def test_revoke_consent_exige_senha_e_valida_credencial(mock_user, mock_session_obj):
    """Revogação de consentimento exige confirmação de senha do titular."""
    # Cenário 1: Sem senha
    with app.test_request_context("/auth/consent/revoke", method="POST", json={}):
        with patch("app.utils.sessions.get_current_session", return_value=(mock_session_obj, mock_user)), \
             patch("app.routes.auth.db.session") as mock_db_session:

            response, status_code = revoke_consent()
            assert status_code == 400
            assert "A confirmação de senha é obrigatória" in response.get_json()["error"]
            mock_db_session.delete.assert_not_called()

    # Cenário 2: Senha errada
    with app.test_request_context("/auth/consent/revoke", method="POST", json={"password": "errada"}):
        with patch("app.utils.sessions.get_current_session", return_value=(mock_session_obj, mock_user)), \
             patch("app.routes.auth.bcrypt.checkpw", return_value=False), \
             patch("app.routes.auth.db.session") as mock_db_session:

            response, status_code = revoke_consent()
            assert status_code == 401
            assert "Senha incorreta" in response.get_json()["error"]
            mock_db_session.delete.assert_not_called()

    # Cenário 3: Senha correta
    with app.test_request_context("/auth/consent/revoke", method="POST", json={"password": "correta"}):
        with patch("app.utils.sessions.get_current_session", return_value=(mock_session_obj, mock_user)), \
             patch("app.routes.auth.bcrypt.checkpw", return_value=True), \
             patch("app.routes.auth.db.session") as mock_db_session:

            response, status_code = revoke_consent()
            assert status_code == 200
            assert "Consentimento revogado" in response.get_json()["message"]
            mock_db_session.delete.assert_called_once_with(mock_user)
            mock_db_session.commit.assert_called_once()
