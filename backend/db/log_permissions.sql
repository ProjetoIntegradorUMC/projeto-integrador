-- Proteção da trilha de auditoria
-- Uso:
--   psql -h <host> -p <porta> -U <usuario_admin> -d <database> \
--     -v app_role='<role_da_aplicacao>' \
--     -v db_owner='<usuario_admin>' \
--     -f backend/db/log_permissions.sql
--
-- Este script pressupõe que o role da aplicação já exista e que as tabelas
-- security_logs e password_reset_logs já tenham sido criadas.

DO $$
BEGIN
    IF to_regclass('public.security_logs') IS NULL THEN
        RAISE EXCEPTION 'Tabela public.security_logs não encontrada. Execute a aplicação para criar o schema antes deste script.';
    END IF;

    IF to_regclass('public.password_reset_logs') IS NULL THEN
        RAISE EXCEPTION 'Tabela public.password_reset_logs não encontrada. Execute a aplicação para criar o schema antes deste script.';
    END IF;
END $$;

-- O role da aplicação pode criar o schema para que db.create_all() funcione,
-- mas não pode continuar dono dos logs; o proprietário sempre mantém
-- UPDATE/DELETE independentemente de REVOKE.
ALTER TABLE public.security_logs OWNER TO :"db_owner";
ALTER TABLE public.password_reset_logs OWNER TO :"db_owner";

-- A restrição abaixo afeta somente as tabelas de auditoria. As permissões
-- completas do role nas demais entidades permanecem intactas.
REVOKE UPDATE, DELETE, TRUNCATE
ON TABLE public.security_logs, public.password_reset_logs
FROM PUBLIC;

-- Reforça que o role da aplicação é append-only nos logs de auditoria.
REVOKE UPDATE, DELETE, TRUNCATE
ON TABLE public.security_logs, public.password_reset_logs
FROM :"app_role";

GRANT SELECT, INSERT
ON TABLE public.security_logs, public.password_reset_logs
TO :"app_role";

-- INSERT com IDs autogerados precisa de USAGE/SELECT/UPDATE nas sequências.
-- O role mantém essa permissão para todas as entidades; a proteção
-- append-only continua restrita às tabelas de logs acima.
GRANT USAGE, SELECT, UPDATE
ON ALL SEQUENCES IN SCHEMA public
TO :"app_role";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"app_role";
