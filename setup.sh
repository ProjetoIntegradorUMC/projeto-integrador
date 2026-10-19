#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
VENV_DIR="${PROJECT_ROOT}/.venv"
PYTHON="${VENV_DIR}/bin/python"

fail() {
    printf 'Erro: %s\n' "$*" >&2
    exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker não encontrado."
docker compose version >/dev/null 2>&1 || fail "Docker Compose não está disponível."

[[ -f "${ENV_FILE}" ]] || fail "Arquivo .env não encontrado. Copie .env.example para .env e preencha os valores."

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

required_variables=(
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

for variable in "${required_variables[@]}"; do
    [[ -n "${!variable:-}" ]] || fail "${variable} não está configurada no .env."
done

validate_identifier() {
    local name="$1"
    local value="$2"
    if [[ ! "${value}" =~ ^[a-zA-Z_][a-zA-Z0-9_]{0,62}$ ]]; then
        fail "${name} contém um identificador SQL inválido ('${value}'). Use apenas letras, números e underscore (máx. 63 caracteres)."
    fi
}

validate_identifier "DB_NAME" "${DB_NAME}"
validate_identifier "DB_ADMIN_USER" "${DB_ADMIN_USER}"
validate_identifier "DB_APP_USER" "${DB_APP_USER}"
validate_identifier "DB_APP_ROLE" "${DB_APP_ROLE}"

[[ "${DB_APP_USER}" != "${DB_APP_ROLE}" ]] || fail "DB_APP_USER e DB_APP_ROLE devem ter nomes distintos."
[[ "${DB_APP_USER}" != "${DB_ADMIN_USER}" ]] || fail "DB_APP_USER e DB_ADMIN_USER devem ter nomes distintos."
[[ "${DB_APP_ROLE}" != "${DB_ADMIN_USER}" ]] || fail "DB_APP_ROLE e DB_ADMIN_USER devem ter nomes distintos."

if [[ ! -x "${PYTHON}" ]]; then
    command -v python3 >/dev/null 2>&1 || fail "Python 3 não encontrado."
    python3 -m venv "${VENV_DIR}"
fi

printf '%s\n' "Instalando dependências Python..."
"${PYTHON}" -m pip install --quiet --requirement "${PROJECT_ROOT}/requirements.txt"

printf '%s\n' "Subindo o PostgreSQL..."
(
    cd "${PROJECT_ROOT}"
    docker compose up --detach postgres
)

printf '%s\n' "Aguardando o PostgreSQL ficar disponível..."
for attempt in $(seq 1 30); do
    if docker compose --project-directory "${PROJECT_ROOT}" exec --env PGPASSWORD="${DB_ADMIN_PASSWORD}" --no-TTY postgres \
        pg_isready --username="${DB_ADMIN_USER}" --dbname="${DB_NAME}" >/dev/null 2>&1; then
        break
    fi

    if [[ "${attempt}" -eq 30 ]]; then
        fail "PostgreSQL não ficou disponível a tempo."
    fi
    sleep 2
done

printf '%s\n' "Provisionando schema e privilégios mínimos do banco..."
# Executa o script unificado de provisionamento (create_schema.py, app_role_setup.sql,
# log_permissions.sql, log_retention_setup.sql e validate_permissions.sql)
PSQL_EXEC_CMD="docker compose --project-directory ${PROJECT_ROOT} exec --env PGPASSWORD=${DB_ADMIN_PASSWORD} --no-TTY postgres psql --quiet --set ON_ERROR_STOP=1 --username=${DB_ADMIN_USER} --dbname=${DB_NAME}" \
PYTHON="${PYTHON}" \
bash "${PROJECT_ROOT}/backend/db/provision.sh"

cd "${PROJECT_ROOT}"
if [[ "${SECURE_COOKIES:-true}" =~ ^(1|true|yes|on)$ ]]; then
    if [[ ! -f "${PROJECT_ROOT}/cert.pem" || ! -f "${PROJECT_ROOT}/key.pem" ]]; then
        printf '%s\n' "SECURE_COOKIES está ativo e certificados TLS locais não foram encontrados. Gerando cert.pem e key.pem..."
        bash "${PROJECT_ROOT}/gerar_certificados.sh"
    fi
fi

if [[ -f "${PROJECT_ROOT}/cert.pem" && -f "${PROJECT_ROOT}/key.pem" ]]; then
    printf '%s\n' "Ambiente configurado. Iniciando o backend em https://127.0.0.1:5000..."
else
    printf '%s\n' "Ambiente configurado. Iniciando o backend em http://127.0.0.1:5000..."
fi
exec "${PYTHON}" backend/run.py
