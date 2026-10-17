-- Valida os privilégios efetivos da role de runtime.
-- Execute como administrador, informando -v app_role="$DB_APP_ROLE".

\set ON_ERROR_STOP on

SELECT
    :'app_role' AS role_name,
    has_schema_privilege(:'app_role', 'public', 'USAGE') AS schema_usage,
    has_schema_privilege(:'app_role', 'public', 'CREATE') AS schema_create,
    has_table_privilege(:'app_role', 'public.users', 'SELECT,INSERT,UPDATE,DELETE')
        AS users_crud,
    has_table_privilege(:'app_role', 'public.tutoring_offers', 'SELECT,INSERT,DELETE')
        AS tutoring_offers_crud_for_lgpd,
    has_table_privilege(:'app_role', 'public.enrollments', 'SELECT,INSERT,DELETE')
        AS enrollments_write,
    has_table_privilege(:'app_role', 'public.sessions', 'SELECT,INSERT,UPDATE,DELETE')
        AS sessions_crud,
    has_table_privilege(
        :'app_role',
        'public.password_reset_tokens',
        'SELECT,INSERT,UPDATE,DELETE'
    ) AS password_reset_tokens_crud,
    has_table_privilege(
        :'app_role',
        'public.rate_limit_counters',
        'SELECT,INSERT,UPDATE,DELETE'
    ) AS rate_limit_counters_crud,
    has_table_privilege(:'app_role', 'public.security_logs', 'SELECT,INSERT')
        AS security_logs_append,
    has_table_privilege(:'app_role', 'public.security_logs', 'UPDATE,DELETE')
        AS security_logs_mutation,
    has_table_privilege(:'app_role', 'public.password_reset_logs', 'SELECT,INSERT')
        AS password_reset_logs_append,
    has_table_privilege(
        :'app_role',
        'public.password_reset_logs',
        'UPDATE,DELETE'
    ) AS password_reset_logs_mutation;

SELECT CASE WHEN (
    NOT has_schema_privilege(:'app_role', 'public', 'CREATE')
    AND has_schema_privilege(:'app_role', 'public', 'USAGE')
    AND has_table_privilege(:'app_role', 'public.users', 'SELECT,INSERT,UPDATE,DELETE')
    AND has_table_privilege(:'app_role', 'public.tutoring_offers', 'SELECT,INSERT,DELETE')
    AND has_table_privilege(:'app_role', 'public.enrollments', 'SELECT,INSERT,DELETE')
    AND has_table_privilege(:'app_role', 'public.sessions', 'SELECT,INSERT,UPDATE,DELETE')
    AND has_table_privilege(
        :'app_role',
        'public.password_reset_tokens',
        'SELECT,INSERT,UPDATE,DELETE'
    )
    AND has_table_privilege(
        :'app_role',
        'public.rate_limit_counters',
        'SELECT,INSERT,UPDATE,DELETE'
    )
    AND has_table_privilege(:'app_role', 'public.security_logs', 'SELECT,INSERT')
    AND NOT has_table_privilege(:'app_role', 'public.security_logs', 'UPDATE,DELETE')
    AND has_table_privilege(:'app_role', 'public.password_reset_logs', 'SELECT,INSERT')
    AND NOT has_table_privilege(
        :'app_role',
        'public.password_reset_logs',
        'UPDATE,DELETE'
    )
) THEN 'true' ELSE 'false' END AS valid
\gset permissions_

\if :permissions_valid
\else
\echo 'Privilégios efetivos não atendem ao privilégio mínimo.'
SELECT 1 / 0 AS permission_validation_failed;
\endif
