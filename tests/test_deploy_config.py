import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_configuracao_segura():
    dockerfile = PROJECT_ROOT / "Dockerfile"
    assert dockerfile.exists()
    content = dockerfile.read_text(encoding="utf-8")

    assert "FROM python:3.13-slim" in content
    assert "postgresql-client" in content
    assert "pip install --no-cache-dir -r requirements.txt" in content
    assert "EXPOSE 5000" in content
    assert 'ENTRYPOINT ["/app/docker-entrypoint.sh"]' in content


def test_docker_entrypoint_valida_variaveis_e_executa_gunicorn():
    entrypoint = PROJECT_ROOT / "docker-entrypoint.sh"
    assert entrypoint.exists()
    content = entrypoint.read_text(encoding="utf-8")

    assert "set -Eeuo pipefail" in content
    for var in (
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_ADMIN_USER",
        "DB_ADMIN_PASSWORD",
        "DB_APP_USER",
        "DB_APP_PASSWORD",
        "DB_APP_ROLE",
        "SECRET_KEY",
        "TOTP_ENCRYPTION_KEY",
    ):
        assert var in content

    assert "pg_isready" in content
    assert "backend/db/provision.sh" in content
    assert "gunicorn" in content
    assert "0.0.0.0:5000" in content


def test_provision_sh_unifica_execucao_de_scripts_sql_sem_duplicacao():
    provision_sh = PROJECT_ROOT / "backend" / "db" / "provision.sh"
    assert provision_sh.exists()
    content = provision_sh.read_text(encoding="utf-8")

    assert "create_schema.py" in content
    assert "app_role_setup.sql" in content
    assert "log_permissions.sql" in content
    assert "log_retention_setup.sql" in content
    assert "validate_permissions.sql" in content
    assert "psql --quiet --set ON_ERROR_STOP=1" in content


def test_docker_compose_prod_traefik_e_isolamento_banco():
    compose_prod = PROJECT_ROOT / "docker-compose.prod.yml"
    assert compose_prod.exists()
    content = compose_prod.read_text(encoding="utf-8")

    # Serviços essenciais
    assert "mentory-postgres:" in content
    assert "mentory-web:" in content

    # Isolamento de rede do banco (não deve publicar porta 5432 no host)
    assert "5432:5432" not in content
    assert "mentory-internal:" in content

    # Integração com Traefik v2.11 da VPS
    assert "n8n-stack_proxy:" in content
    assert "external: true" in content
    assert '"traefik.enable=true"' in content
    assert '"traefik.docker.network=n8n-stack_proxy"' in content
    assert "Host(`mentory.stack-n8n.cloud`)" in content
    assert '"traefik.http.routers.mentory.entrypoints=websecure"' in content
    assert '"traefik.http.routers.mentory.tls=true"' in content
    assert '"traefik.http.routers.mentory.tls.certresolver=myresolver"' in content
    assert '"traefik.http.services.mentory.loadbalancer.server.port=5000"' in content


def test_github_actions_deploy_workflow():
    workflow = PROJECT_ROOT / ".github" / "workflows" / "deploy.yml"
    assert workflow.exists()
    content = workflow.read_text(encoding="utf-8")

    # Gatilho exclusivo na main
    assert "branches:\n      - main" in content

    # Princípio do menor privilégio e SHA fixado de 40 caracteres
    assert "permissions: {}" in content
    shas = re.findall(r"@([0-9a-f]{40})", content)
    assert len(shas) >= 3

    # Serviço PostgreSQL para execução da suíte completa de testes no CI
    assert "services:" in content
    assert "postgres:16" in content
    assert "POSTGRES_DB: projeto_integrador_test" in content

    # Executa testes antes do deploy
    assert "pytest -v" in content

    # Deploy SSH na VPS
    assert "appleboy/ssh-action" in content
    assert "docker compose -f docker-compose.prod.yml up -d --build" in content


def test_env_prod_example_configuracao_minima():
    env_example = PROJECT_ROOT / ".env.prod.example"
    assert env_example.exists()
    content = env_example.read_text(encoding="utf-8")

    assert "DB_HOST=mentory-postgres" in content
    assert "APP_BASE_URL=https://mentory.stack-n8n.cloud" in content
    assert "SECURE_COOKIES=true" in content
    assert "FLASK_DEBUG=false" in content
