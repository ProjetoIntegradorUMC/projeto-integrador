import os
import smtplib
import ssl
from email.message import EmailMessage


DEFAULT_SMTP_TIMEOUT = 10.0


def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Envia um e-mail usando o servidor SMTP com STARTTLS e validação estrita de certificados.

    As credenciais e configurações são obtidas das variáveis de ambiente no .env.
    """
    smtp_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("MAIL_PORT", "587"))
    smtp_timeout = float(os.getenv("MAIL_TIMEOUT", str(DEFAULT_SMTP_TIMEOUT)))
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")

    if not username or not password:
        raise RuntimeError("Credenciais de e-mail não configuradas.")

    message = EmailMessage()
    message["From"] = username
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    # Cria contexto SSL padrão que valida certificados e CAs do sistema operacional
    ssl_context = ssl.create_default_context()

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=smtp_timeout) as server:
            server.starttls(context=ssl_context)
            server.login(username, password)
            server.send_message(message)
    except (smtplib.SMTPException, ssl.SSLError, TimeoutError, OSError) as exc:
        # Registra / propaga o erro de forma segura, sem expor credenciais
        raise RuntimeError(
            f"Falha de comunicação SMTP segura ({exc.__class__.__name__}): {exc}"
        ) from exc
