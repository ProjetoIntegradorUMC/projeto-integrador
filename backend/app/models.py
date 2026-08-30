from app import db


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
