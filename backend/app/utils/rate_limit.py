import hashlib
import hmac
import math
import random
from datetime import datetime, timedelta, timezone

from flask import current_app, jsonify, request
from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert

from app import db
from app.models import RateLimitCounter
from app.utils.password_reset import log_security_event

# operação -> escopo -> (limite de requisições, janela em segundos)
LIMITS = {
    "register": {"ip": (10, 3600)},
    "forgot_password": {"ip": (5, 900), "email": (3, 3600)},
}

# Chance de apagar contadores expirados a cada chamada (sem tarefa agendada).
CLEANUP_PROBABILITY = 0.02


def _now():
    return datetime.now(timezone.utc)


def _digest(value):
    secret = current_app.secret_key.encode("utf-8")
    return hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _email_from_request():
    payload = request.get_json(silent=True)
    email = payload.get("email") if isinstance(payload, dict) else None
    # SecurityLog.email tem 120 caracteres: trunca para o log nunca falhar.
    return str(email)[:120] if email else "unknown"


def get_client_ip():
    # Único ponto que decide qual é o IP do cliente. Atrás de proxy,
    # analise docs/rate-limiting.md antes de mudar.
    return request.remote_addr or "desconhecido"


def is_limited(operation, scope, identifier):
    """Conta a requisição. Devolve None se permitida, ou os segundos até ela liberar."""
    limit, window = LIMITS[operation][scope]
    now = _now()
    new_expiry = now + timedelta(seconds=window)
    expired = RateLimitCounter.expires_at <= now

    statement = (
        insert(RateLimitCounter)
        .values(
            key=f"{operation}:{scope}:{_digest(identifier)}",
            count=1,
            expires_at=new_expiry,
        )
        .on_conflict_do_update(
            index_elements=["key"],
            set_={
                "count": case((expired, 1), else_=RateLimitCounter.count + 1),
                "expires_at": case(
                    (expired, new_expiry), else_=RateLimitCounter.expires_at
                ),
            },
        )
        .returning(RateLimitCounter.count, RateLimitCounter.expires_at)
    )
    count, expires_at = db.session.execute(statement).one()

    if random.random() < CLEANUP_PROBABILITY:
        RateLimitCounter.query.filter(RateLimitCounter.expires_at < now).delete()
    db.session.commit()

    if count <= limit:
        return None

    # Só a primeira requisição bloqueada de cada janela vai para o log,
    # para um usuário malicioso não encher a trilha da auditoria.
    if count == limit + 1:
        log_security_event(
            email=_email_from_request(),
            event_type="rate_limited",
            failure_reason=f"{operation}_{scope}",
        )

    return max(1, math.ceil((expires_at - now).total_seconds()))


def too_many_requests(retry_after):
    minutos = max(1, math.ceil(retry_after / 60))
    response = jsonify(
        {"error": f"Muitas tentativas. Tente novamente em {minutos} minuto(s)."}
    )
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response