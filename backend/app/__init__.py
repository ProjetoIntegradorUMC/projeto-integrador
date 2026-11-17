from pathlib import Path
import os

from flask import Flask, send_from_directory, request, abort
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import URL
from werkzeug.middleware.proxy_fix import ProxyFix
from app.two_factor import get_totp_fernet

db = SQLAlchemy()


def create_app():
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    app = Flask(__name__)

    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_APP_USER")
    db_password = os.getenv("DB_APP_PASSWORD")

    required_variables = {
        "DB_HOST": db_host,
        "DB_PORT": db_port,
        "DB_NAME": db_name,
        "DB_APP_USER": db_user,
        "DB_APP_PASSWORD": db_password,
        "SECRET_KEY": os.getenv("SECRET_KEY"),
        "TOTP_ENCRYPTION_KEY": os.getenv("TOTP_ENCRYPTION_KEY"),
    }

    missing_variables = [
        name for name, value in required_variables.items() if not value
    ]

    # Falha rápido e explicitamente em vez de deixar a aplicação subir
    # com configuração de banco incompleta, o que poderia mascarar
    # problemas de conexão ou, pior, apontar para um banco errado.
    if missing_variables:
        raise RuntimeError(
            f"Variáveis de ambiente não configuradas: {', '.join(missing_variables)}"
        )

    # Valida a chave Fernet no startup, antes de aceitar requisições.
    get_totp_fernet()

    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=db_user,
        password=db_password,
        host=db_host,
        port=int(db_port),
        database=db_name,
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = connection_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Configuração de sessão para 2FA
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("SECURE_COOKIES", "false").lower() == "true"
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.secret_key = os.environ["SECRET_KEY"]

    db.init_app(app)

    # Importando os modelos para que o SQLAlchemy os reconheça
    import app.models as models

    with app.app_context():
        db.create_all()

    from app.routes.auth import auth_bp
    from app.routes.tutoring_offers import tutoring_offers_bp
    from app.routes.lgpd import lgpd_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(tutoring_offers_bp, url_prefix="/tutoring-offers")
    app.register_blueprint(lgpd_bp, url_prefix="/lgpd")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app.cli import register_cli

    register_cli(app)

    frontend_path = project_root / "frontend"

    # Configuração de ProxyFix para confiar exclusivamente em 1 salto (hop) do proxy reverso
    # imediato (Traefik v2.11 na rede Docker n8n-stack_proxy). Como docker-compose.prod.yml
    # não publica a porta 5000 no host e mentory-web só é alcançável externamente via Traefik,
    # clientes externos não conseguem injetar X-Forwarded-Proto diretamente no container.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    @app.before_request
    def enforce_https():
        # Em produção (SECURE_COOKIES=true), o tráfego externo passa obrigatoriamente pelo
        # Traefik v2.11 (rede n8n-stack_proxy), que realiza a terminação TLS (Let's Encrypt,
        # certresolver=myresolver) e define X-Forwarded-Proto=https no salto único confiável
        # processado pelo ProxyFix(x_for=1, x_proto=1). Como a porta 5000 não é exposta no
        # host e a rede mentory-internal é isolada (internal: true), requisições externas não
        # podem contornar o Traefik para forjar X-Forwarded-Proto.
        secure_cookies = os.getenv("SECURE_COOKIES", "false").lower() == "true"
        if secure_cookies and not request.is_secure:
            # Bloqueia qualquer requisição que não tenha chegado via HTTPS direto ou via
            # salto único confiável do Traefik com X-Forwarded-Proto: https.
            abort(403, description="Acesso negado. A aplicação exige conexão segura (HTTPS).")

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
        )
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "credentialless"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if request.is_secure or os.getenv("SECURE_COOKIES", "false").lower() == "true":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    @app.route("/")
    def serve_frontend():
        return send_from_directory(frontend_path, "index.html")

    @app.route("/<path:path>")
    def serve_frontend_files(path):
        return send_from_directory(frontend_path, path)

    return app
