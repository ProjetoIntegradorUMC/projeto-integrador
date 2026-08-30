from pathlib import Path
import os

from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import URL

db = SQLAlchemy()


def create_app():
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    app = Flask(__name__)

    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    required_variables = {
        "DB_HOST": db_host,
        "DB_PORT": db_port,
        "DB_NAME": db_name,
        "DB_USER": db_user,
        "DB_PASSWORD": db_password,
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

    db.init_app(app)

    with app.app_context():
        db.create_all()

    from app.routes.auth import auth_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")

    frontend_path = project_root / "frontend"

    @app.route("/")
    def serve_frontend():
        return send_from_directory(frontend_path, "index.html")

    @app.route("/<path:path>")
    def serve_frontend_files(path):
        return send_from_directory(frontend_path, path)

    return app
