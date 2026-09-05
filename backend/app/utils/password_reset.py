import hashlib
import secrets
from app import db
from app.models import PasswordResetLog


def generate_reset_token() -> str:
    """
    Gera um token criptograficamente seguro para recuperação de senha.

    O token é gerado com secrets, que utiliza uma fonte de aleatoriedade
    adequada para aplicações relacionadas à segurança.
    """
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    """
    Gera o hash SHA-256 do token.

    O token original não deve ser armazenado no banco de dados.
    Apenas o seu hash é persistido.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def log_password_reset_event(
    email: str,
    event_type: str,
    user_id: int = None,
    failure_reason: str = None,
    token_hash_suffix: str = None,
) -> PasswordResetLog:

    log = PasswordResetLog(
        email=email,
        user_id=user_id,
        event_type=event_type,
        failure_reason=failure_reason,
        token_hash_suffix=token_hash_suffix,
    )

    db.session.add(log)
    db.session.commit()

    return log
