-- Protege a trilha de auditoria como append-only.
-- Execute com um usuário administrador, depois de create_schema.py e
-- app_role_setup.sql:
--
--   psql -h <host> -p <porta> -U <usuario_admin> -d <database> \
--     -v app_role="$DB_APP_ROLE" \
--     -v db_owner="$DB_ADMIN_USER" \
--     -f backend/db/log_permissions.sql

\set ON_ERROR_STOP on
\set QUIET on

\if :{?app_role}
\else
\warn 'ERRO: variável obrigatória app_role não informada (-v app_role=...).'
SELECT 1 / 0;
\endif

\if :{?db_owner}
\else
\warn 'ERRO: variável obrigatória db_owner não informada (-v db_owner=...).'
SELECT 1 / 0;
\endif

SELECT
    (:'app_role' ~ '^[a-zA-Z_][a-zA-Z0-9_]{0,62}$') AS role_ok,
    (:'db_owner' ~ '^[a-zA-Z_][a-zA-Z0-9_]{0,62}$') AS owner_ok,
    (:'app_role' <> :'db_owner') AS distinct_ok
\gset check_

\if :check_role_ok
\else
\warn 'ERRO: identificador inválido em app_role. Use apenas letras, números e underscore.'
SELECT 1 / 0;
\endif

\if :check_owner_ok
\else
\warn 'ERRO: identificador inválido em db_owner. Use apenas letras, números e underscore.'
SELECT 1 / 0;
\endif

\if :check_distinct_ok
\else
\warn 'ERRO: app_role e db_owner devem possuir identificadores distintos.'
SELECT 1 / 0;
\endif

DO $$
BEGIN
    IF to_regclass('public.security_logs') IS NULL THEN
        RAISE EXCEPTION 'Tabela public.security_logs não encontrada. Execute create_schema.py.';
    END IF;

    IF to_regclass('public.password_reset_logs') IS NULL THEN
        RAISE EXCEPTION 'Tabela public.password_reset_logs não encontrada. Execute create_schema.py.';
    END IF;
END $$;

-- O dono sempre mantém UPDATE/DELETE, portanto os logs pertencem ao admin.
ALTER TABLE public.security_logs OWNER TO :"db_owner";
ALTER TABLE public.password_reset_logs OWNER TO :"db_owner";

REVOKE ALL PRIVILEGES
ON TABLE public.security_logs, public.password_reset_logs
FROM PUBLIC;

REVOKE ALL PRIVILEGES
ON TABLE public.security_logs, public.password_reset_logs
FROM :"app_role";

GRANT SELECT, INSERT
ON TABLE public.security_logs, public.password_reset_logs
TO :"app_role";
