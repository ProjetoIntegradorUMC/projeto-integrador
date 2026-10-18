from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / "db"
    / "anonymize_old_log_emails.sql"
)
SETUP_SCRIPT = SCRIPT.with_name("log_retention_setup.sql")


def test_rotina_de_retencao_preserva_eventos_e_pseudonimiza_apenas_logs_antigos():
    content = SCRIPT.read_text(encoding="utf-8")

    assert "UPDATE public.security_logs" in content
    assert "UPDATE public.password_reset_logs" in content
    assert "CURRENT_TIMESTAMP - make_interval(days => :'retention_days'::integer)" in content
    assert "SET email = 'redacted+' || md5(lower(btrim(logs.email)))" in content
    assert "NOT LIKE 'redacted+%@example.invalid'" in content
    assert "RETURNING 1" in content
    assert "DELETE FROM" not in content


def test_rotina_respeita_excecoes_de_investigacao_e_role_append_only():
    content = SCRIPT.read_text(encoding="utf-8")
    setup_content = SETUP_SCRIPT.read_text(encoding="utf-8")

    assert "log_retention_exemptions" in content
    assert "exemptions.expires_at > CURRENT_TIMESTAMP" in content
    assert 'REVOKE ALL PRIVILEGES ON TABLE public.log_retention_exemptions FROM :"app_role";' in setup_content
    assert "GRANT UPDATE" not in content
    assert "GRANT DELETE" not in content


def test_tabela_de_excecoes_e_provisionada_separadamente():
    content = SETUP_SCRIPT.read_text(encoding="utf-8")
    anonymize_content = SCRIPT.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS public.log_retention_exemptions" in content
    assert "ALTER TABLE public.log_retention_exemptions OWNER TO :" in content
    assert 'REVOKE ALL PRIVILEGES ON TABLE public.log_retention_exemptions FROM :"app_role";' in content
    assert "CREATE TABLE IF NOT EXISTS public.log_retention_exemptions" not in anonymize_content
    assert "log_retention_setup.sql" in Path(
        SCRIPT.parents[2] / "setup.sh"
    ).read_text(encoding="utf-8")
