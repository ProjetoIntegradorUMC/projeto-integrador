"""Cria as entidades do banco usando os models, com credenciais administrativas."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


project_root = Path(__file__).resolve().parents[2]
backend_root = project_root / "backend"
sys.path.insert(0, str(backend_root))
load_dotenv(project_root / ".env")

admin_user = os.getenv("DB_ADMIN_USER")
admin_password = os.getenv("DB_ADMIN_PASSWORD")

if not admin_user or not admin_password:
    raise RuntimeError(
        "DB_ADMIN_USER e DB_ADMIN_PASSWORD são obrigatórios para criar o schema."
    )

# create_app() usa DB_APP_* para a conexão. Neste bootstrap, esses valores são
# substituídos somente no processo atual pelo usuário administrativo.
os.environ["DB_APP_USER"] = admin_user
os.environ["DB_APP_PASSWORD"] = admin_password

from app import create_app, db  # noqa: E402


app = create_app()

with app.app_context():
    db.create_all()

print("Schema criado ou atualizado a partir dos models.")
