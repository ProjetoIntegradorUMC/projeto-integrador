-- Pseudonimiza e-mails antigos dos logs sem conceder UPDATE/DELETE à role
-- usada pela aplicação. Execute somente com a role administrativa:
--
--   psql ... \
--     -v app_role="$DB_APP_ROLE" \
--     -v db_owner="$DB_ADMIN_USER" \
--     -v retention_days=90 \
--     -f backend/db/anonymize_old_log_emails.sql
--
-- A tabela de exceções deve ser provisionada previamente por
-- backend/db/log_retention_setup.sql. Investigações ativas podem ser
-- preservadas inserindo uma exceção antes da execução:
--
--   INSERT INTO log_retention_exemptions
--     (log_table, log_id, reason, expires_at)
--   VALUES ('security_logs', 123, 'INC-2026-001', '2026-12-31 23:59:59+00');

\set ON_ERROR_STOP on

DO $$
BEGIN
    IF :'retention_days'::integer <= 0 THEN
        RAISE EXCEPTION 'retention_days deve ser maior que zero';
    END IF;
END $$;

BEGIN;

-- A retenção padrão é de 90 dias. O registro do evento é preservado; somente
-- o identificador direto é substituído por um pseudônimo estável.
WITH anonymized AS (
    UPDATE public.security_logs AS logs
       SET email = 'redacted+' || md5(lower(btrim(logs.email))) || '@example.invalid'
     WHERE logs.created_at < CURRENT_TIMESTAMP - make_interval(days => :'retention_days'::integer)
       AND logs.email NOT LIKE 'redacted+%@example.invalid'
       AND NOT EXISTS (
           SELECT 1
             FROM public.log_retention_exemptions AS exemptions
            WHERE exemptions.log_table = 'security_logs'
              AND exemptions.log_id = logs.id
              AND exemptions.expires_at > CURRENT_TIMESTAMP
       )
    RETURNING 1
)
SELECT 'security_logs' AS log_table, count(*) AS anonymized_rows
  FROM anonymized;

WITH anonymized AS (
    UPDATE public.password_reset_logs AS logs
       SET email = 'redacted+' || md5(lower(btrim(logs.email))) || '@example.invalid'
     WHERE logs.created_at < CURRENT_TIMESTAMP - make_interval(days => :'retention_days'::integer)
       AND logs.email NOT LIKE 'redacted+%@example.invalid'
       AND NOT EXISTS (
           SELECT 1
             FROM public.log_retention_exemptions AS exemptions
            WHERE exemptions.log_table = 'password_reset_logs'
              AND exemptions.log_id = logs.id
              AND exemptions.expires_at > CURRENT_TIMESTAMP
       )
    RETURNING 1
)
SELECT 'password_reset_logs' AS log_table, count(*) AS anonymized_rows
  FROM anonymized;

COMMIT;
