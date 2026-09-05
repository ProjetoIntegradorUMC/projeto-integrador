import hashlib
from datetime import datetime, timezone
from app import db
from app.models import PasswordResetLog


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
