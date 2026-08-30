from flask import Blueprint, request, jsonify
import bcrypt

from app import db
from app.models import User

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

    return (
        jsonify(
            {
                "message": "Login realizado com sucesso",
                "user": {"id": user.id, "username": user.username, "email": user.email},
            }
        ),
        200,
    )
