-- Provisiona usuário e role de aplicação
-- Uso:
--   psql -h <host> -p <porta> -U <usuario_admin> -d <database> \
--     -v app_user="$DB_APP_USER" \
--     -v app_password="$DB_APP_PASSWORD" \
--     -v app_role="$DB_APP_ROLE" \
--     -f backend/db/app_role_setup.sql

SELECT format('CREATE ROLE %I NOLOGIN', :'app_role')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = :'app_role'
)\gexec

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = :'app_user'
)\gexec

SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = :'app_user'
)\gexec

SELECT format('GRANT %I TO %I', :'app_role', :'app_user')\gexec

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO %I',
    current_database(),
    :'app_role'
)\gexec

GRANT USAGE, CREATE ON SCHEMA public TO :"app_role";

-- A aplicação mantém acesso completo às demais entidades. A exceção dos logs
-- é aplicada posteriormente por backend/db/log_permissions.sql.
GRANT ALL PRIVILEGES
ON ALL TABLES IN SCHEMA public
TO :"app_role";

GRANT ALL PRIVILEGES
ON ALL SEQUENCES IN SCHEMA public
TO :"app_role";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO :"app_role";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON SEQUENCES TO :"app_role";
