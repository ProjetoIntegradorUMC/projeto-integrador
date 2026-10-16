import os
import ssl
from unittest.mock import MagicMock, patch
import pytest

from app.utils.email import send_email


def test_send_email_sucesso_com_contexto_tls_e_timeout(monkeypatch):
    """Verifica se send_email passa contexto SSL seguro e timeout explícito para o smtplib."""
    monkeypatch.setenv("MAIL_SERVER", "smtp.teste.com")
    monkeypatch.setenv("MAIL_PORT", "587")
    monkeypatch.setenv("MAIL_TIMEOUT", "12")
    monkeypatch.setenv("MAIL_USERNAME", "remetente@teste.com")
    monkeypatch.setenv("MAIL_PASSWORD", "senha_secreta")

    mock_server = MagicMock()
    # Simula o context manager: with smtplib.SMTP(...) as server:
    mock_server.__enter__.return_value = mock_server

    with patch("smtplib.SMTP", return_value=mock_server) as mock_smtp_cls:
        send_email(
            to_email="destinatario@teste.com",
            subject="Assunto de Teste",
            body="Corpo de Teste",
        )

        # 1. Verifica se smtplib.SMTP foi instanciado com o timeout explícito
        mock_smtp_cls.assert_called_once_with(
            "smtp.teste.com", 587, timeout=12.0
        )

        # 2. Verifica se starttls foi chamado com um contexto SSL válido (não nulo)
        mock_server.starttls.assert_called_once()
        _, kwargs = mock_server.starttls.call_args
        assert "context" in kwargs
        assert isinstance(kwargs["context"], ssl.SSLContext)

        # 3. Verifica login e envio da mensagem
        mock_server.login.assert_called_once_with(
            "remetente@teste.com", "senha_secreta"
        )
        mock_server.send_message.assert_called_once()


def test_send_email_trata_timeout_sem_vazar_credenciais(monkeypatch):
    """Garante que exceções de timeout geram RuntimeError limpo sem expor senhas."""
    monkeypatch.setenv("MAIL_USERNAME", "remetente@teste.com")
    monkeypatch.setenv("MAIL_PASSWORD", "super_secreto_123")

    mock_server = MagicMock()
    mock_server.__enter__.side_effect = TimeoutError("Tempo de conexão esgotado")

    with patch("smtplib.SMTP", return_value=mock_server):
        with pytest.raises(RuntimeError) as exc_info:
            send_email("destinatario@teste.com", "Assunto", "Corpo")

        erro = str(exc_info.value)
        assert "Falha de comunicação SMTP segura" in erro
        assert "super_secreto_123" not in erro


def test_send_email_sem_credenciais_lanca_erro():
    """Valida se erro explícito é lançado caso as credenciais não estejam no ambiente."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="Credenciais de e-mail não configuradas."):
            send_email("destinatario@teste.com", "Assunto", "Corpo")
