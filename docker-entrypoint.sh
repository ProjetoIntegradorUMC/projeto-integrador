#!/usr/bin/env bash
set -Eeuo pipefail

echo "==> Iniciando container do Mentory em produção..."

# Validação das variáveis mínimas essenciais
required_vars=(
    DB_HOST
    DB_PORT
    DB_NAME
    DB_ADMIN_USER
    DB_ADMIN_PASSWORD
    DB_APP_USER
    DB_APP_PASSWORD
    DB_APP_ROLE
    SECRET_KEY
    TOTP_ENCRYPTION_KEY
)

for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo "ERRO: Variável de ambiente obrigatória '${var}' não está configurada." >&2
        exit 1
    fi
done

echo "==> Aguardando o PostgreSQL em ${DB_HOST}:${DB_PORT}..."
until PGPASSWORD="${DB_ADMIN_PASSWORD}" pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -d "${DB_NAME}" >/dev/null 2>&1; do
    sleep 1
done
echo "==> PostgreSQL conectado com sucesso!"

echo "==> Verificando/criando tabelas pelo create_schema.py..."
PYTHONPATH=backend python backend/db/create_schema.py

echo "==> Aplicando privilégios mínimos da role de runtime..."
PGPASSWORD="${DB_ADMIN_PASSWORD}" psql --quiet --set ON_ERROR_STOP=1 \
    -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -d "${DB_NAME}" \
    -v app_user="${DB_APP_USER}" \
    -v app_password="${DB_APP_PASSWORD}" \
    -v app_role="${DB_APP_ROLE}" \
    -f backend/db/app_role_setup.sql

PGPASSWORD="${DB_ADMIN_PASSWORD}" psql --quiet --set ON_ERROR_STOP=1 \
    -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -d "${DB_NAME}" \
    -v app_role="${DB_APP_ROLE}" \
    -v db_owner="${DB_ADMIN_USER}" \
    -f backend/db/log_permissions.sql

echo "==> Validando permissões efetivas da role..."
PGPASSWORD="${DB_ADMIN_PASSWORD}" psql --quiet --set ON_ERROR_STOP=1 \
    -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_ADMIN_USER}" -d "${DB_NAME}" \
    -v app_role="${DB_APP_ROLE}" \
    -f backend/db/validate_permissions.sql

echo "==> Inicialização concluída. Iniciando Gunicorn na porta 5000..."
exec gunicorn --chdir backend --workers 2 --bind 0.0.0.0:5000 --timeout 60 --access-logfile - --error-logfile - "run:app"
