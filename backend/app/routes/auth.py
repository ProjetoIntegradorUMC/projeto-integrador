from flask import Blueprint, request, jsonify, session, make_response
import bcrypt
from datetime import datetime, timedelta, timezone

from app import db
from app.models import User
from app.utils.sessions import (
    create_session,
    get_current_session,
    revoke_session,
    login_required,
)
from app.two_factor import (
    generate_totp_secret,
    get_provisioning_uri,
    generate_qr_code,
    verify_totp_code,
)

auth_bp = Blueprint("auth", __name__)

# bcrypt foi escolhido por gerenciar a geração e o armazenamento do salt
# internamente (embutido no hash), e por ser adaptativo: o fator de custo
# pode ser aumentado no futuro conforme necessidade.
#
# O fator de custo 12 aumenta o esforço computacional do bcrypt,
# dificultando ataques de força bruta sem tornar o login inviável.
BCRYPT_ROUNDS = 12


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "username, email e password são obrigatórios"}), 400

    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing_user:
        return jsonify({"error": "Usuário ou e-mail já cadastrado"}), 409

    # gensalt() gera um salt aleatório e criptograficamente seguro a cada
    # chamada, garantindo que dois usuários com a mesma senha nunca produzam
    # o mesmo hash. O salt fica embutido no resultado de hashpw(), por isso
    # não é necessário armazená-lo em uma coluna separada no banco.
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    )

    user = User(
        username=username, email=email, password_hash=password_hash.decode("utf-8")
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Usuário cadastrado com sucesso"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "email e password são obrigatórios"}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "Credenciais inválidas"}), 401

    # ---  PROTEÇÃO CONTRA FORÇA BRUTA ---
    now = datetime.now(timezone.utc)

    # 1. Verifica se o usuário está bloqueado
    if user.locked_until and user.locked_until > now:
        minutos_restantes = (user.locked_until - now).seconds // 60
        return (
            jsonify(
                {
                    "error": f"Conta bloqueada por segurança. Tente novamente em {minutos_restantes} minutos."
                }
            ),
            423,
        )  # HTTP 423 Locked (Recurso trancado)

    password_valid = bcrypt.checkpw(
        password.encode("utf-8"), user.password_hash.encode("utf-8")
    )

    if not password_valid:
        # 2. Se errou a senha, aumenta a contagem de tentativas
        user.failed_attempts += 1

        # 3. Se errou 5 vezes seguidas, tranca a conta por 15 minutos
        if user.failed_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
            db.session.commit()
            return (
                jsonify(
                    {
                        "error": "Muitas tentativas falhas. Conta bloqueada por 15 minutos."
                    }
                ),
                423,
            )

        db.session.commit()
        return jsonify({"error": "Credenciais inválidas"}), 401

    # 4. Se a senha for válida, zera o contador de erros e remove qualquer bloqueio
    user.failed_attempts = 0
    user.locked_until = None
    db.session.commit()
    # --- FIM DA PROTEÇÃO ---

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
                "user": {"id": user.id, "username": user.username, "email": user.email},
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
        samesite="Lax",
        max_age=30 * 60,  # Expira do navegador em 30 minutos (em segundos)
    )

    return response, 200


@auth_bp.route("/verify-2fa", methods=["POST"])
def verify_2fa():
    """Valida o código TOTP fornecido e completa o login."""
    data = request.get_json()
    code = data.get("code")

    if not code:
        return jsonify({"error": "Código TOTP é obrigatório"}), 400

    # Verificar se há um login pendente (2FA em andamento)
    user_id = session.get("pending_user_id")
    if not user_id:
        return jsonify({"error": "Nenhum login pendente encontrado"}), 400

    user = User.query.filter_by(id=user_id).first()

    if not user or not user.two_factor_enabled:
        return jsonify({"error": "Validação de 2FA falhou"}), 401

    # Validar o código TOTP
    if not verify_totp_code(user.two_factor_secret, code):
        return jsonify({"error": "Código de 2FA inválido"}), 401

    # Limpar a sessão de 2FA pendente
    session.pop("pending_user_id", None)

    # --- INÍCIO DA NOSSA CRIAÇÃO DE SESSÃO (Quando passa pelo 2FA) ---
    session_obj = create_session(user.id)

    response = make_response(
        jsonify(
            {
                "message": "Login concluído com sucesso após validação de 2FA",
                "user": {"id": user.id, "username": user.username, "email": user.email},
            }
        )
    )

    response.set_cookie(
        "session_id", session_obj.token, httponly=True, samesite="Lax", max_age=30 * 60
    )

    return response, 200


@auth_bp.route("/2fa/setup", methods=["POST"])
def setup_2fa():
    """Gera um novo segredo TOTP e retorna o QR code para configuração."""
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id é obrigatório"}), 400

    user = User.query.filter_by(id=user_id).first()

    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    # Gerar um novo segredo TOTP
    secret = generate_totp_secret()

    # Gerar URI de provisionamento para o QR code
    provisioning_uri = get_provisioning_uri(secret, user.email)

    # Gerar a imagem QR code em base64
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
def confirm_2fa():
    """Confirma a ativação de 2FA após o usuário validar o código com seu app authenticator."""
    data = request.get_json()
    user_id = data.get("user_id")
    secret = data.get("secret")
    code = data.get("code")

    if not user_id or not secret or not code:
        return (
            jsonify({"error": "user_id, secret e code são obrigatórios"}),
            400,
        )

    user = User.query.filter_by(id=user_id).first()

    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    # Validar o código TOTP com o segredo fornecido
    if not verify_totp_code(secret, code):
        return jsonify({"error": "Código TOTP inválido"}), 401

    # Ativar 2FA armazenando o segredo no banco de dados
    user.two_factor_enabled = True
    user.two_factor_secret = secret
    db.session.commit()

    return jsonify({"message": "2FA ativado com sucesso"}), 200


@auth_bp.route("/2fa/disable", methods=["POST"])
def disable_2fa():
    """Desativa 2FA para o usuário."""
    data = request.get_json()
    user_id = data.get("user_id")
    password = data.get("password")

    if not user_id or not password:
        return jsonify({"error": "user_id e password são obrigatórios"}), 400

    user = User.query.filter_by(id=user_id).first()

    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    # Verificar senha antes de permitir desativar 2FA
    password_valid = bcrypt.checkpw(
        password.encode("utf-8"), user.password_hash.encode("utf-8")
    )

    if not password_valid:
        return jsonify({"error": "Senha inválida"}), 401

    # Desativar 2FA
    user.two_factor_enabled = False
    user.two_factor_secret = None
    db.session.commit()

    return jsonify({"message": "2FA desativado com sucesso"}), 200


@auth_bp.route("/2fa/status", methods=["GET"])
def get_2fa_status():
    """Retorna o status de 2FA do usuário."""
    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id é obrigatório"}), 400

    user = User.query.filter_by(id=user_id).first()

    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    return (
        jsonify(
            {
                "two_factor_enabled": user.two_factor_enabled,
            }
        ),
        200,
    )


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
                    "username": current_user.username,
                    "email": current_user.email,
                }
            }
        ),
        200,
    )
