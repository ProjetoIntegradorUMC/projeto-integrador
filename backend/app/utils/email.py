import os
import smtplib
from email.message import EmailMessage


def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Envia um e-mail usando o servidor SMTP do Gmail.

    As credenciais são obtidas das variáveis de ambiente
    configuradas no arquivo .env.
    """
    smtp_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("MAIL_PORT", "587"))
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")

    if not username or not password:
        raise RuntimeError("Credenciais de e-mail não configuradas.")

    message = EmailMessage()
    message["From"] = username
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)
