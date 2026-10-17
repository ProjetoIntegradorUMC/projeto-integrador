-- Protege a trilha de auditoria como append-only.
-- Execute com um usuário administrador, depois de create_schema.py e
-- app_role_setup.sql:
--
--   psql -h <host> -p <porta> -U <usuario_admin> -d <database> \
--     -v app_role="$DB_APP_ROLE" \
--     -v db_owner="$DB_ADMIN_USER" \
--     -f backend/db/log_permissions.sql

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
