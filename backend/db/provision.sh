#!/usr/bin/env bash
set -Eeuo pipefail

DB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${DB_DIR}/../.." && pwd)"

# Se o .env existir e as variáveis ainda não estiverem carregadas no ambiente, carrega
if [[ -f "${PROJECT_ROOT}/.env" && -z "${DB_NAME:-}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${PROJECT_ROOT}/.env"
    set +a
fi

required_variables=(
    DB_NAME
    DB_ADMIN_USER
    DB_ADMIN_PASSWORD
    DB_APP_USER
    DB_APP_PASSWORD
    DB_APP_ROLE
)

for variable in "${required_variables[@]}"; do
    [[ -n "${!variable:-}" ]] || {
        echo "ERRO: Variável ${variable} não configurada para provisionamento do banco." >&2
        exit 1
    }
done

validate_identifier() {
    local name="$1"
    local value="$2"
    if [[ ! "${value}" =~ ^[a-zA-Z_][a-zA-Z0-9_]{0,62}$ ]]; then
        echo "ERRO: ${name} contém identificador SQL inválido ('${value}')." >&2
        exit 1
    fi
}

validate_identifier "DB_NAME" "${DB_NAME}"
validate_identifier "DB_ADMIN_USER" "${DB_ADMIN_USER}"
validate_identifier "DB_APP_USER" "${DB_APP_USER}"
validate_identifier "DB_APP_ROLE" "${DB_APP_ROLE}"

[[ "${DB_APP_USER}" != "${DB_APP_ROLE}" ]] || { echo "ERRO: DB_APP_USER e DB_APP_ROLE devem ser distintos." >&2; exit 1; }
[[ "${DB_APP_USER}" != "${DB_ADMIN_USER}" ]] || { echo "ERRO: DB_APP_USER e DB_ADMIN_USER devem ser distintos." >&2; exit 1; }
[[ "${DB_APP_ROLE}" != "${DB_ADMIN_USER}" ]] || { echo "ERRO: DB_APP_ROLE e DB_ADMIN_USER devem ser distintos." >&2; exit 1; }

echo "==> Criando ou atualizando schema pelos models..."
PYTHONPATH="${PROJECT_ROOT}/backend" "${PYTHON:-python3}" "${DB_DIR}/create_schema.py"

run_admin_sql() {
    local script="$1"
    shift

    if [[ -n "${PSQL_EXEC_CMD:-}" ]]; then
        ${PSQL_EXEC_CMD} "$@" < "${DB_DIR}/${script}"
    else
        PGPASSWORD="${DB_ADMIN_PASSWORD}" psql --quiet --set ON_ERROR_STOP=1 \
            -h "${DB_HOST:-localhost}" \
            -p "${DB_PORT:-5432}" \
            -U "${DB_ADMIN_USER}" \
            -d "${DB_NAME}" \
            "$@" < "${DB_DIR}/${script}"
    fi
}

echo "==> Aplicando privilégios da role de runtime..."
run_admin_sql app_role_setup.sql \
    --set "app_user=${DB_APP_USER}" \
    --set "app_password=${DB_APP_PASSWORD}" \
    --set "app_role=${DB_APP_ROLE}"

run_admin_sql log_permissions.sql \
    --set "app_role=${DB_APP_ROLE}" \
    --set "db_owner=${DB_ADMIN_USER}"

run_admin_sql log_retention_setup.sql \
    --set "app_role=${DB_APP_ROLE}" \
    --set "db_owner=${DB_ADMIN_USER}"

echo "==> Validando permissões efetivas..."
run_admin_sql validate_permissions.sql \
    --set "app_role=${DB_APP_ROLE}"
