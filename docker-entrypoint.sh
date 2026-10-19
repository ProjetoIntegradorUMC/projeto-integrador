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

echo "==> Executando provisionamento de banco (schema e permissões)..."
bash backend/db/provision.sh

echo "==> Inicialização concluída. Iniciando Gunicorn na porta 5000..."
exec gunicorn --chdir backend --workers 2 --bind 0.0.0.0:5000 --timeout 60 --access-logfile - --error-logfile - "run:app"
