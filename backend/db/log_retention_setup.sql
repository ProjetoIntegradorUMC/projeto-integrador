-- Provisiona a tabela administrativa de exceções da política de retenção.
-- Execute com o usuário administrador, depois de criar as tabelas de logs:
--
--   psql ... \
--     -v app_role="$DB_APP_ROLE" \
--     -v db_owner="$DB_ADMIN_USER" \
--     -f backend/db/log_retention_setup.sql
--
-- A role da aplicação não recebe qualquer permissão nesta tabela.

\set ON_ERROR_STOP on

DO $$
BEGIN
    IF to_regclass('public.security_logs') IS NULL THEN
        RAISE EXCEPTION 'Tabela public.security_logs não encontrada.';
    END IF;

    IF to_regclass('public.password_reset_logs') IS NULL THEN
        RAISE EXCEPTION 'Tabela public.password_reset_logs não encontrada.';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.log_retention_exemptions (
    log_table text NOT NULL
        CHECK (log_table IN ('security_logs', 'password_reset_logs')),
    log_id bigint NOT NULL CHECK (log_id > 0),
    reason text NOT NULL CHECK (length(btrim(reason)) > 0),
    expires_at timestamptz NOT NULL CHECK (expires_at > created_at),
    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_table, log_id)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'log_retention_exemptions_log_id_positive'
           AND conrelid = 'public.log_retention_exemptions'::regclass
    ) THEN
        ALTER TABLE public.log_retention_exemptions
            ADD CONSTRAINT log_retention_exemptions_log_id_positive
            CHECK (log_id > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'log_retention_exemptions_reason_not_blank'
           AND conrelid = 'public.log_retention_exemptions'::regclass
    ) THEN
        ALTER TABLE public.log_retention_exemptions
            ADD CONSTRAINT log_retention_exemptions_reason_not_blank
            CHECK (length(btrim(reason)) > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'log_retention_exemptions_expires_after_creation'
           AND conrelid = 'public.log_retention_exemptions'::regclass
    ) THEN
        ALTER TABLE public.log_retention_exemptions
            ADD CONSTRAINT log_retention_exemptions_expires_after_creation
            CHECK (expires_at > created_at);
    END IF;
END $$;

ALTER TABLE public.log_retention_exemptions OWNER TO :"db_owner";
REVOKE ALL PRIVILEGES ON TABLE public.log_retention_exemptions FROM PUBLIC;
REVOKE ALL PRIVILEGES ON TABLE public.log_retention_exemptions FROM :"app_role";

COMMENT ON TABLE public.log_retention_exemptions IS
    'Excecoes administrativas e temporarias da pseudonimizacao de e-mails em logs';
