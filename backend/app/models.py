from app import db
from datetime import datetime, timezone


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    # 255 caracteres é mais que suficiente para um hash bcrypt (~60 chars),
    # com folga para eventual migração futura para Argon2, que gera hashes
    # maiores.
    password_hash = db.Column(db.String(255), nullable=False)

    # TOTP secret para 2FA (base32, compatível com Google Authenticator)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32), nullable=True)

    # NOVOS CAMPOS: Proteção contra Força Bruta (Issue #3)
    # Persistimos o contador no banco pois em memória ele zeraria se o servidor reiniciasse.
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)

    # Armazena até quando o usuário está bloqueado. Bloqueio por tempo é mais
    # seguro que bloqueio definitivo para mitigar negação de serviço (DoS) direcionada.
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)


# NOVO MODELO: Gestão de Sessão (Issue #3)
# Decisão Técnica: Guardamos a sessão no lado do servidor (banco) em vez de usar JWT.
# Motivo (Segurança): O JWT não pode ser revogado facilmente se o token for roubado (sequestro de sessão).
# Com a sessão no banco, o logout invalida a sessão na hora alterando o campo 'revoked_at'.
class Session(db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True)

    # O cookie do navegador vai carregar só esse token opaco (gerado de forma segura).
    token = db.Column(db.String(64), unique=True, nullable=False)

    # LGPD (Art. 18 - Direito à eliminação): ON DELETE CASCADE garante que se o
    # usuário pedir a exclusão da conta, suas sessões ativas serão apagadas em cascata.
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Controle de tempo e revogação
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relacionamento prático para acessar os dados do usuário a partir da sessão
    user = db.relationship(
        "User", backref=db.backref("sessions", lazy=True, cascade="all, delete")
    )


class PasswordResetLog(db.Model):
    __tablename__ = "password_reset_logs"

    id = db.Column(db.Integer, primary_key=True)

    # Email envolvido na operação (para auditar mesmo se user for deletado)
    email = db.Column(db.String(120), nullable=False, index=True)

    # User ID se disponível (pode ser nulo em casos de tentativa com email inexistente)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Tipo de evento: 'request' (solicitação), 'success' (sucesso), 'failure' (falha)
    event_type = db.Column(db.String(20), nullable=False, index=True)

    # Motivo em caso de falha: 'token_expired', 'token_invalid', 'token_already_used', etc.
    failure_reason = db.Column(db.String(100), nullable=True)

    # Hash truncado do token para auditoria (últimos 8 chars do hash do token)
    # Permite rastrear qual token foi usado sem expor o token completo.
    token_hash_suffix = db.Column(db.String(16), nullable=True)

    # Data e hora do evento
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relacionamento prático
    user = db.relationship("User", backref=db.backref("password_reset_logs", lazy=True))
