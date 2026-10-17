-- Provisiona o usuário e a role de runtime da aplicação.
-- Execute com um usuário administrador depois de:
--   PYTHONPATH=backend python backend/db/create_schema.py
--
--   psql -h <host> -p <porta> -U <usuario_admin> -d <database> \
--     -v app_user="$DB_APP_USER" \
--     -v app_password="$DB_APP_PASSWORD" \
--     -v app_role="$DB_APP_ROLE" \
--     -f backend/db/app_role_setup.sql
--
-- A criação das entidades continua sendo feita por db.create_all() a partir
-- dos models. Este script apenas provisiona a role e os grants de runtime.

SELECT format(
    'CREATE ROLE %I NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
    :'app_role'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = :'app_role'
)\gexec

SELECT format(
    'ALTER ROLE %I WITH NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
    :'app_role'
)
WHERE EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = :'app_role'
)\gexec

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = :'app_user'
)\gexec

SELECT format(
    'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
    :'app_user',
    :'app_password'
)
WHERE EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = :'app_user'
)\gexec

SELECT format('GRANT %I TO %I', :'app_role', :'app_user')\gexec

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO %I',
    current_database(),
    :'app_role'
)\gexec

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM :"app_role";
REVOKE CREATE ON SCHEMA public FROM :"app_user";
GRANT USAGE ON SCHEMA public TO :"app_role";

-- Remove grants amplos de execuções anteriores antes de aplicar o conjunto
-- explícito abaixo. Isso torna a reaplicação do script convergente.
REVOKE ALL PRIVILEGES
ON ALL TABLES IN SCHEMA public
FROM :"app_role";

REVOKE ALL PRIVILEGES
ON ALL SEQUENCES IN SCHEMA public
FROM :"app_role";

-- Privilégios por tabela usados pelo backend:
--   users: cadastro, autenticação, atualização de segurança e exclusão LGPD.
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.users
TO :"app_role";

--   tutoring_offers: consulta, criação e remoção em cascata na exclusão LGPD.
GRANT SELECT, INSERT, DELETE
ON TABLE public.tutoring_offers
TO :"app_role";

--   enrollments: consulta, inscrição e cancelamento de inscrição.
GRANT SELECT, INSERT, DELETE
ON TABLE public.enrollments
TO :"app_role";

--   sessions: criação, consulta, revogação e exclusão em cascata.
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.sessions
TO :"app_role";

--   password_reset_tokens: criação, consulta, consumo e exclusão de tokens.
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.password_reset_tokens
TO :"app_role";

--   rate_limit_counters: upsert, limpeza de expirados e consulta.
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.rate_limit_counters
TO :"app_role";

-- Logs são tratados separadamente por log_permissions.sql.
GRANT SELECT, INSERT
ON TABLE public.security_logs, public.password_reset_logs
TO :"app_role";

-- nextval() exige USAGE ou UPDATE; currval() exige USAGE ou SELECT.
GRANT USAGE, SELECT
ON ALL SEQUENCES IN SCHEMA public
TO :"app_role";

-- Objetos futuros não recebem privilégios automaticamente. Toda nova tabela
-- deve ser adicionada explicitamente a este script após revisão.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
REVOKE ALL ON TABLES FROM :"app_role";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
REVOKE ALL ON SEQUENCES FROM :"app_role";
