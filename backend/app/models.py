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
    locked_until = db.Column(db.DateTime, nullable=True)


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
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Controle de tempo e revogação
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    
    # Relacionamento prático para acessar os dados do usuário a partir da sessão
    user = db.relationship("User", backref=db.backref("sessions", lazy=True, cascade="all, delete"))