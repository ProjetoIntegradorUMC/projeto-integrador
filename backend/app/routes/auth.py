import os

from flask import Blueprint, request, jsonify, session, make_response, current_app
import bcrypt
import math

from datetime import datetime, timedelta, timezone

from app import db
from app.models import User, PasswordResetToken
from app.utils.sessions import (
    create_session,
    get_current_session,
    revoke_session,
    revoke_all_user_sessions,
    login_required,
)
from app.two_factor import (
    generate_totp_secret,
    get_provisioning_uri,
    generate_qr_code,
    verify_totp_code,
    verify_totp_step,
)

from app.utils.password_reset import (
    generate_reset_token,
    hash_reset_token,
    log_password_reset_event,
    log_security_event,
)
from app.utils.email import send_email

from app.utils.validators import (
    validate_password_policy,
    safe_check_password,
    get_json_payload,
)
from app.utils.rate_limit import get_client_ip, is_limited, too_many_requests

auth_bp = Blueprint("auth", __name__)

# bcrypt foi escolhido por gerenciar a geração e o armazenamento do salt
# internamente (embutido no hash), e por ser adaptativo: o fator de custo
# pode ser aumentado no futuro conforme necessidade.
#
# O fator de custo 12 aumenta o esforço computacional do bcrypt,
# dificultando ataques de força bruta sem tornar o login inviável.
BCRYPT_ROUNDS = 12

# Proteção do 2FA: 5 falhas bloqueiam a verificação por 15 minutos.
TWO_FACTOR_MAX_ATTEMPTS = 5
TWO_FACTOR_LOCK_MINUTES = 15

def minutos_restantes(locked_until, now):
    """Minutos que faltam para o fim do bloqueio, arredondados para cima (mínimo 1)."""
    segundos = (locked_until - now).total_seconds()
    return max(1, math.ceil(segundos / 60))

@auth_bp.route("/register", methods=["POST"])
def register():
    retry_after = is_limited("register", "ip", get_client_ip())
    if retry_after:
        return too_many_requests(retry_after)
    data = get_json_payload(request)

    full_name = data.get("full_name")
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    consent_given = data.get("consent_given")

    if (
        not full_name
        or not username
        or not email
        or not password
        or not consent_given
        or not isinstance(full_name, str)
        or not isinstance(username, str)
        or not isinstance(email, str)
        or not isinstance(password, str)
    ):
        return jsonify({"error": "Todos os campos são obrigatórios e devem ser válidos"}), 400

    full_name = full_name.strip()
    username = username.strip()
    email = email.strip()

    if not full_name or not username or not email:
        return jsonify({"error": "Todos os campos são obrigatórios"}), 400

    # Valida política de senhas (mínimo 8 caracteres, máximo 72 bytes)
    is_valid, error_msg = validate_password_policy(password)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing_user:
        return jsonify({"error": "Usuário ou e-mail já cadastrado"}), 409

    try:
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        )
    except (ValueError, TypeError):
        return jsonify({"error": "Erro ao processar a senha informada"}), 400

    user = User(
        full_name=full_name,
        username=username,
        email=email,
        password_hash=password_hash.decode("utf-8"),
        consent_given_at=datetime.now(timezone.utc),
        consent_version="1.0",
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Usuário cadastrado com sucesso"}), 201


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """Inicia o processo de recuperação de senha por e-mail."""
    retry_after = is_limited("forgot_password", "ip", get_client_ip())
    if retry_after:
        return too_many_requests(retry_after)
    data = get_json_payload(request)
    email = data.get("email")

    if not email or not isinstance(email, str) or not email.strip():
        return jsonify({"error": "E-mail é obrigatório"}), 400

    email = email.strip()

    # A contagem vale para e-mails existentes e inexistentes.
    # Acima do limite, responde igual a um pedido normal e não envia nada.
    if is_limited("forgot_password", "email", email.lower()):
        return (
            jsonify(
                {
                    "message": "Se o e-mail estiver cadastrado, você receberá um link de recuperação."
                }
            ),
            200,
        )
      
    # Procura o usuário pelo e-mail informado.
    user = User.query.filter_by(email=email).first()

    # Se o e-mail não estiver cadastrado, não gera token nem envia e-mail.
    if not user:
        log_password_reset_event(
            email=email,
            event_type="failure",
            failure_reason="email_not_found",
        )

        # Resposta genérica para não revelar informações sobre usuários cadastrados.
        return (
            jsonify(
                {
                    "message": "Se o e-mail estiver cadastrado, você receberá um link de recuperação."
                }
            ),
            200,
        )

    # Gera um token criptograficamente seguro.
    token = generate_reset_token()

    # Apenas o hash do token é armazenado no banco.
    token_hash = hash_reset_token(token)

    # O token terá validade de 15 minutos.
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=15)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=expires_at,
    )

    db.session.add(reset_token)
    db.session.commit()

    # O token original é enviado somente para o e-mail do usuário.
    base_url = os.getenv("APP_BASE_URL", "http://localhost:5000")
    reset_link = f"{base_url}/?token={token}"

    email_body = f"""
    Olá, {user.username}!

    Recebemos uma solicitação para redefinir sua senha.

    Acesse o link abaixo para continuar:

    {reset_link}

    Este link é válido por 15 minutos.

    Se você não solicitou a recuperação de senha, ignore este e-mail.

    Projeto Integrador
    """

    try:
        send_email(
            user.email,
            "Recuperação de senha - Projeto Integrador",
            email_body,
        )
    except Exception:
        # Remove o token caso o envio do e-mail falhe.
        db.session.delete(reset_token)
        db.session.commit()

        log_password_reset_event(
            email=user.email,
            event_type="failure",
            user_id=user.id,
            failure_reason="email_send_failed",
            token_hash_suffix=token_hash[-16:],
        )

        # Resposta genérica: um 500 só para contas existentes revelaria quem tem conta.
        return (
            jsonify(
                {
                    "message": "Se o e-mail estiver cadastrado, você receberá um link de recuperação."
                }
            ),
            200,
        )

    # Registra a solicitação bem-sucedida no log de auditoria.
    log_password_reset_event(
        email=user.email,
        event_type="request",
        user_id=user.id,
        token_hash_suffix=token_hash[-16:],
    )

    return (
        jsonify(
            {
                "message": "Se o e-mail estiver cadastrado, você receberá um link de recuperação."
            }
        ),
        200,
    )


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """Redefine a senha usando um token válido de recuperação."""
    data = get_json_payload(request)

    token = data.get("token")
    new_password = data.get("new_password")

    if (
        not token
        or not new_password
        or not isinstance(token, str)
        or not isinstance(new_password, str)
    ):
        return jsonify({"error": "Token e nova senha são obrigatórios."}), 400

    token = token.strip()
    if not token:
        return jsonify({"error": "Token e nova senha são obrigatórios."}), 400

    # Valida política de senhas (mínimo 8 caracteres, máximo 72 bytes)
    is_valid, error_msg = validate_password_policy(new_password)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    # Gera o hash do token recebido.
    token_hash = hash_reset_token(token)

    # Procura o token armazenado no banco.
    reset_token = PasswordResetToken.query.filter_by(token_hash=token_hash).first()

    # Token inexistente.
    if not reset_token:
        log_password_reset_event(
            email="unknown",
            event_type="failure",
            failure_reason="invalid_token",
            token_hash_suffix=token_hash[-16:],
        )

        return jsonify({"error": "Link de recuperação inválido ou expirado."}), 400

    now = datetime.now(timezone.utc)

    # Token já utilizado.
    if reset_token.used_at is not None:
        log_password_reset_event(
            email=reset_token.user.email,
            event_type="failure",
            user_id=reset_token.user_id,
            failure_reason="token_already_used",
            token_hash_suffix=token_hash[-16:],
        )

        return jsonify({"error": "Link de recuperação inválido ou expirado."}), 400

    # Token expirado.
    if reset_token.expires_at <= now:
        log_password_reset_event(
            email=reset_token.user.email,
            event_type="failure",
            user_id=reset_token.user_id,
            failure_reason="token_expired",
            token_hash_suffix=token_hash[-16:],
        )

        return jsonify({"error": "Link de recuperação inválido ou expirado."}), 400

    # Procura o usuário relacionado ao token.
    user = User.query.get(reset_token.user_id)

    if not user:
        log_password_reset_event(
            email="unknown",
            event_type="failure",
            failure_reason="user_not_found",
            token_hash_suffix=token_hash[-16:],
        )

        return jsonify({"error": "Não foi possível redefinir a senha."}), 400

    try:
        password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        ).decode("utf-8")
    except (ValueError, TypeError):
        return jsonify({"error": "Erro ao processar a nova senha."}), 400

    user.password_hash = password_hash

    # Marca o token como utilizado.
    reset_token.used_at = now

    # Revoga todas as sessões ativas existentes do usuário (Issue #83)
    revoke_all_user_sessions(user.id, commit=False)

    db.session.commit()

    # Registra a redefinição bem-sucedida.
    log_password_reset_event(
        email=user.email,
        event_type="success",
        user_id=user.id,
        token_hash_suffix=token_hash[-16:],
    )

    return jsonify({"message": "Senha redefinida com sucesso. Faça login novamente com a nova senha."}), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    data = get_json_payload(request)

    email = data.get("email")
    password = data.get("password")

    if (
        not email
        or not password
        or not isinstance(email, str)
        or not isinstance(password, str)
    ):
        return jsonify({"error": "email e password são obrigatórios"}), 400

    email = email.strip()
    user = User.query.filter_by(email=email).first()

    if not user:
        # Instrumentação do login: registra falha antes de responder ao cliente
        # para manter um histórico consultável sem expor a senha do usuário.
        log_security_event(
            email=email,
            event_type="login_failure",
            failure_reason="user_not_found",
        )
        return jsonify({"error": "Credenciais inválidas"}), 401

    # ---  PROTEÇÃO CONTRA FORÇA BRUTA ---
    now = datetime.now(timezone.utc)

    # 1. Verifica se o usuário está bloqueado
    if user.locked_until and user.locked_until > now:
        # Instrumentação do login: falha deliberada por conta bloqueada.
        log_security_event(
            email=user.email,
            event_type="login_failure",
            user_id=user.id,
            failure_reason="account_locked",
        )
        minutos_restantes = (user.locked_until - now).seconds // 60
        return (
            jsonify(
                {
                    "error": f"Conta bloqueada por segurança. Tente novamente em {minutos_restantes} minutos."
                }
            ),
            423,
        )  # HTTP 423 Locked (Recurso trancado)

    password_valid = safe_check_password(password, user.password_hash)

    if not password_valid:
        # 2. Se errou a senha, aumenta a contagem de tentativas
        user.failed_attempts += 1

        # 3. Se errou 5 vezes seguidas, tranca a conta por 15 minutos
        if user.failed_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
            db.session.commit()
            # Instrumentação do login: falha terminal que resultou em bloqueio.
            log_security_event(
                email=user.email,
                event_type="login_failure",
                user_id=user.id,
                failure_reason="too_many_failed_attempts",
            )
            return (
                jsonify(
                    {
                        "error": "Muitas tentativas falhas. Conta bloqueada por 15 minutos."
                    }
                ),
                423,
            )

        db.session.commit()
        # Instrumentação do login: falha em autenticação primária.
        log_security_event(
            email=user.email,
            event_type="login_failure",
            user_id=user.id,
            failure_reason="invalid_password",
        )
        return jsonify({"error": "Credenciais inválidas"}), 401

    # 4. Se a senha for válida, zera o contador de erros e remove qualquer bloqueio
    user.failed_attempts = 0
    user.locked_until = None
    db.session.commit()
    # --- FIM DA PROTEÇÃO ---

    # Instrumentação do login: grava sucesso da autenticação primária mesmo quando
    # o fluxo segue para validação do código 2FA, sem registrar a senha.
    log_security_event(
        email=user.email,
        event_type="login_success",
        user_id=user.id,
    )

    # Se 2FA está habilitado, o fluxo desvia para lá sem criar a sessão definitiva ainda.
    if user.two_factor_enabled:
        session["pending_user_id"] = user.id
        session.permanent = True
        session.permanent_session_lifetime = timedelta(minutes=5)
        return (
            jsonify(
                {
                    "message": "Autenticação primária bem-sucedida. Aguardando validação de 2FA.",
                    "requires_2fa": True,
                }
            ),
            200,
        )

    # --- INÍCIO DA NOSSA CRIAÇÃO DE SESSÃO (Quando não tem 2FA) ---
    # Cria a sessão no banco usando a ferramenta que fizemos na Etapa 2
    session_obj = create_session(user.id)

    # Prepara a resposta JSON
    response = make_response(
        jsonify(
            {
                "message": "Login realizado com sucesso",
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "username": user.username,
                    "email": user.email,
                },
                "requires_2fa": False,
            }
        )
    )

    # Seta o cookie contendo apenas o token opaco.
    # Segurança (XSS): httponly=True impede que o Javascript do navegador roube o cookie.
    response.set_cookie(
        "session_id",
        session_obj.token,
        httponly=True,
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        samesite="Lax",
        max_age=30 * 60,  # Expira do navegador em 30 minutos (em segundos)
    )

    return response, 200


@auth_bp.route("/verify-2fa", methods=["POST"])
def verify_2fa():
    """Valida o código TOTP fornecido e completa o login."""
    data = get_json_payload(request)
    code = data.get("code")

    if not code or not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Código TOTP é obrigatório"}), 400

    code = code.strip()

    # Verificar se há um login pendente (2FA em andamento)
    user_id = session.get("pending_user_id")
    if not user_id:
        # Instrumentação do 2FA: tentativa sem login pendente não pode ser validada.
        log_security_event(
            email="unknown",
            event_type="twofa_failure",
            failure_reason="missing_pending_login",
        )
        return jsonify({"error": "Nenhum login pendente encontrado"}), 400

    user = User.query.filter_by(id=user_id).with_for_update().first()

    if not user or not user.two_factor_enabled:
        # Instrumentação do 2FA: conta não existe ou 2FA não está habilitado.
        log_security_event(
            email=user.email if user else "unknown",
            event_type="twofa_failure",
            user_id=user.id if user else None,
            failure_reason="2fa_not_enabled",
        )
        return jsonify({"error": "Validação de 2FA falhou"}), 401

    now = datetime.now(timezone.utc)

    # Bloqueio temporário: nem chega a testar o código.
    if user.two_factor_locked_until and user.two_factor_locked_until > now:
        log_security_event(
            email=user.email,
            event_type="twofa_failure",
            user_id=user.id,
            failure_reason="2fa_locked",
        )
        minutos = minutos_restantes(user.two_factor_locked_until, now)
        return (
            jsonify({"error": f"Muitas tentativas. Tente novamente em {minutos} minuto(s)."}),
            423,
        )

    # Valida o código e descobre o período de 30s em que ele esta.
    step = verify_totp_step(user.two_factor_secret, code)

    # Replay: período igual ou anterior ao último aceito é recusado.
    replay = (
        step is not None
        and user.two_factor_last_step is not None
        and step <= user.two_factor_last_step
    )

    if step is None or replay:
        user.two_factor_failed_attempts += 1
        reason = "code_reused" if replay else "invalid_code"

        locked = user.two_factor_failed_attempts >= TWO_FACTOR_MAX_ATTEMPTS
        if locked:
            user.two_factor_locked_until = now + timedelta(minutes=TWO_FACTOR_LOCK_MINUTES)
            user.two_factor_failed_attempts = 0
            session.pop("pending_user_id", None)  # obriga a refazer a senha
            reason = "too_many_failed_attempts"

        db.session.commit()
        # O código digitado não vai para o log.
        log_security_event(
            email=user.email,
            event_type="twofa_failure",
            user_id=user.id,
            failure_reason=reason,
        )
        if locked:
            minutos = minutos_restantes(user.two_factor_locked_until, now)
            return (
                jsonify({"error": f"Muitas tentativas. Tente novamente em {minutos} minuto(s)."}),
                423,
            )
        # Resposta igual para código errado e reutilizado e não revela qual deles foi.
        return jsonify({"error": "Código de 2FA inválido"}), 401

    # Código aceito, guarda o período usado (anti-replay) e zera o contador.
    user.two_factor_last_step = step
    user.two_factor_failed_attempts = 0
    user.two_factor_locked_until = None
    db.session.commit()

    # Limpar a sessão de 2FA pendente
    session.pop("pending_user_id", None)

    # Instrumentação do 2FA: sucesso da validação do código.
    log_security_event(
        email=user.email,
        event_type="twofa_success",
        user_id=user.id,
    )

    # --- INÍCIO DA NOSSA CRIAÇÃO DE SESSÃO (Quando passa pelo 2FA) ---
    session_obj = create_session(user.id)

    response = make_response(
        jsonify(
            {
                "message": "Login concluído com sucesso após validação de 2FA",
                "user": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "username": user.username,
                    "email": user.email,
                },
            }
        )
    )

    response.set_cookie(
        "session_id",
        session_obj.token,
        httponly=True,
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        samesite="Lax",
        max_age=30 * 60
    )

    return response, 200


@auth_bp.route("/2fa/setup", methods=["POST"])
@login_required
def setup_2fa(current_user):
    """Gera um novo segredo TOTP e retorna o QR code para configuração."""
    # Se já tem 2FA ativo, precisa desativar antes de gerar um novo segredo.
    if current_user.two_factor_enabled:
        return jsonify({"error": "2FA já está ativo"}), 409

    secret = generate_totp_secret()

    #O segredo fica guardado no servidor, junto com o dono. O cliente não escolhe mais o segredo.
    session["pending_2fa_secret"] = secret
    session["pending_2fa_user_id"] = current_user.id

    provisioning_uri = get_provisioning_uri(secret, current_user.email)
    qr_code_data = generate_qr_code(provisioning_uri)

    return (
        jsonify(
            {
                "message": "Segredo 2FA gerado com sucesso",
                "secret": secret,
                "qr_code": qr_code_data,
                "manual_entry_key": secret,
            }
        ),
        200,
        )


@auth_bp.route("/2fa/confirm", methods=["POST"])
@login_required
def confirm_2fa(current_user):
    """Confirma a ativação de 2FA após o usuário validar o código com seu app authenticator."""
    data = request.get_json(silent=True) or {}
    code = data.get("code")

    if not code:
        return (
            jsonify({"error": "user_id, secret e code são obrigatórios"}),
            400,
        )

    # O segredo vem da sessão do servidor, nunca da requisição do cliente.
    secret = session.get("pending_2fa_secret")
    pending_user_id = session.get("pending_2fa_user_id")

    # Agora tem que existir e pertencer ao mesmo usuário que está tentando confirmar.
    if not secret or pending_user_id != current_user.id:
        return jsonify({"error": "Configuração de 2FA não iniciada ou expirada"}), 400

    if not verify_totp_code(secret, code):
        log_security_event(
            email=current_user.email,
            event_type="twofa_failure",
            user_id=current_user.id,
            failure_reason="invalid_code",
        )
        return jsonify({"error": "Código TOTP inválido"}), 401

    current_user.two_factor_enabled = True
    current_user.two_factor_secret = secret
    db.session.commit()

    #Só limpa depois de confirmar, para não perder o segredo caso a validação venha falhar.
    session.pop("pending_2fa_secret", None)
    session.pop("pending_2fa_user_id", None)

    log_security_event(
        email=current_user.email,
        event_type="twofa_success",
        user_id=current_user.id,
    )

    return jsonify({"message": "2FA ativado com sucesso"}), 200

@auth_bp.route("/2fa/disable", methods=["POST"])
@login_required
def disable_2fa(current_user):
    """Desativa 2FA para o usuário."""
    data = get_json_payload(request)
    password = data.get("password")
    code = data.get("code")

    if (
        not password
        or not code
        or not isinstance(password, str)
        or not isinstance(code, str)
    ):
        return jsonify({"error": "password e code são obrigatórios"}), 400

    if not current_user.two_factor_enabled:
        return jsonify({"error": "2FA não está ativo"}), 400

    # Verificar senha antes de permitir desativar 2FA com proteção contra erro 500
    password_valid = safe_check_password(password, current_user.password_hash)
    code_valid = verify_totp_code(current_user.two_factor_secret, code.strip())

    # Aqui não revela se foi a senha ou o código que falhou.
    if not password_valid or not code_valid:
        return jsonify({"error": "Senha ou código inválido"}), 401

    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    db.session.commit()

    return jsonify({"message": "2FA desativado com sucesso"}), 200


@auth_bp.route("/2fa/status", methods=["GET"])
@login_required
def get_2fa_status(current_user):
    """Retorna o status de 2FA do usuário logado."""
    return jsonify({"two_factor_enabled": current_user.two_factor_enabled}), 200


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout(current_user):
    """
    Revoga a sessão no banco de dados e limpa o cookie do navegador.
    Segurança e LGPD: A revogação no banco garante que um cookie roubado
    não possa mais ser reutilizado de forma maliciosa.
    """
    session_obj, _ = get_current_session()

    # Invalida no lado do servidor (banco de dados)
    revoke_session(session_obj)

    response = make_response(jsonify({"message": "Logout realizado com sucesso"}))

    # Invalida no lado do cliente (navegador) sobrescrevendo o cookie para expirar no passado
    response.set_cookie("session_id", "", expires=0)

    return response, 200


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_me(current_user):
    """
    Retorna os dados do usuário atual se ele tiver um cookie válido.
    Fundamental para o frontend saber se alguém está logado ao recarregar a página,
    sem precisar mandar a senha de novo.
    """
    return (
        jsonify(
            {
                "user": {
                    "id": current_user.id,
                    "full_name": current_user.full_name,
                    "username": current_user.username,
                    "email": current_user.email,
                    "consent_given_at": (
                        current_user.consent_given_at.isoformat()
                        if current_user.consent_given_at
                        else None
                    ),
                    "consent_version": current_user.consent_version,
                }
            }
        ),
        200,
    )


@auth_bp.route("/consent/revoke", methods=["POST"])
@login_required
def revoke_consent(current_user):
    """
    Revogar o consentimento implica excluir permanentemente a conta.
    Exige confirmação da senha do titular para evitar revogação/exclusão acidental.
    """
    data = request.get_json(silent=True) or {}
    password = data.get("password")

    if not password:
        return jsonify({"error": "A confirmação de senha é obrigatória para revogar o consentimento."}), 400

    if not bcrypt.checkpw(password.encode("utf-8"), current_user.password_hash.encode("utf-8")):
        return jsonify({"error": "Senha incorreta."}), 401

    db.session.delete(current_user)
    db.session.commit()

    response = make_response(
        jsonify({"message": "Consentimento revogado e conta excluída com sucesso"})
    )
    response.set_cookie("session_id", "", expires=0)

    return response, 200
