import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify
from app import db
from app.models import Session, User


def create_session(user_id):
    """
    Cria uma nova sessão no banco de dados e retorna o objeto Session.
    Usamos o banco de dados para permitir revogação imediata no servidor,
    atendendo aos requisitos de Segurança e LGPD.
    """
    # secrets gera um token criptograficamente seguro e aleatório (muito mais forte que um hash simples)
    token = secrets.token_urlsafe(32)

    # Define a validade da sessão para 30 minutos (Proteção contra sessão esquecida)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    new_session = Session(token=token, user_id=user_id, expires_at=expires_at)
    db.session.add(new_session)
    db.session.commit()

    return new_session


def get_current_session():
    """
    Verifica se a requisição possui um cookie de sessão válido e não expirado.
    Retorna a tupla (session, user) ou (None, None).
    """
    # Lê o cookie que o navegador do usuário enviou
    token = request.cookies.get("session_id")
    if not token:
        return None, None

    # Busca a sessão no banco garantindo que:
    # 1. Ela existe
    # 2. Não expirou (passou dos 30 min)
    # 3. Não foi revogada manualmente no logout
    now = datetime.now(timezone.utc)
    session = Session.query.filter_by(token=token).first()

    if not session:
        return None, None

    if session.expires_at < now or session.revoked_at is not None:
        return None, None

    return session, session.user


def revoke_session(session_obj):
    """
    Revoga uma sessão ativa marcando a data de revogação.
    Isso impede ataques de replay (reuso) caso o cookie seja roubado.
    """
    session_obj.revoked_at = datetime.now(timezone.utc)
    db.session.commit()


def login_required(f):
    """
    Decorator para proteger rotas.
    Exige que o usuário tenha uma sessão válida para acessar o recurso.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_obj, user = get_current_session()

        if not session_obj or not user:
            return (
                jsonify(
                    {"error": "Acesso não autorizado. Sessão inválida ou expirada."}
                ),
                401,
            )

        # Repassa o usuário atual para a rota que está sendo protegida
        return f(current_user=user, *args, **kwargs)

    return decorated_function
