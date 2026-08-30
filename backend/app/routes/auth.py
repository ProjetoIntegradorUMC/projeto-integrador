from flask import Blueprint, request, jsonify, session
import bcrypt
from datetime import datetime, timedelta

from app import db
from app.models import User
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

    # checkpw() extrai o salt embutido no hash armazenado e recalcula o hash
    # da senha recebida usando esse mesmo salt, comparando o resultado.
    # A senha em texto puro nunca é comparada diretamente.
    password_valid = bcrypt.checkpw(
        password.encode("utf-8"), user.password_hash.encode("utf-8")
    )

    if not password_valid:
        return jsonify({"error": "Credenciais inválidas"}), 401

    # Se 2FA está habilitado, exigir verificação do código TOTP
    if user.two_factor_enabled:
        # Armazenar na sessão o ID do usuário aguardando 2FA
        session["pending_user_id"] = user.id
        # Expiração da sessão: 5 minutos para validar o código
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

    return (
        jsonify(
            {
                "message": "Login realizado com sucesso",
                "user": {"id": user.id, "username": user.username, "email": user.email},
                "requires_2fa": False,
            }
        ),
        200,
    )


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

    return (
        jsonify(
            {
                "message": "Login concluído com sucesso após validação de 2FA",
                "user": {"id": user.id, "username": user.username, "email": user.email},
            }
        ),
        200,
    )


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
            jsonify(
                {"error": "user_id, secret e code são obrigatórios"}
            ),
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
