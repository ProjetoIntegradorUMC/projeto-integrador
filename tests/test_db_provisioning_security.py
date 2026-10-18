import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_DIR = PROJECT_ROOT / "backend" / "db"


def test_gitignore_bloqueia_scripts_locais_legados_com_interpolacao_sql():
    gitignore_content = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    gitignore_lines = {
        line.strip()
        for line in gitignore_content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert "setup_db.py" in gitignore_lines
    assert "desbloquear_usuario.py" in gitignore_lines
    assert not (DB_DIR / "setup_db.py").exists()


def test_app_role_setup_sql_valida_variaveis_e_usa_escape_seguro():
    sql_content = (DB_DIR / "app_role_setup.sql").read_text(encoding="utf-8")

    assert "\\set ON_ERROR_STOP on" in sql_content
    assert "\\set QUIET on" in sql_content

    for required_var in ("app_role", "app_user", "app_password"):
        assert f"\\if :{{?{required_var}}}" in sql_content

    assert "^[a-zA-Z_][a-zA-Z0-9_]{0,62}$" in sql_content
    assert ":'app_role' <> :'app_user'" in sql_content
    assert "length(btrim(:'app_password')) > 0" in sql_content

    assert "CREATE ROLE %I NOLOGIN" in sql_content
    assert "CREATE ROLE %I LOGIN PASSWORD %L" in sql_content
    assert "ALTER ROLE %I WITH LOGIN PASSWORD %L" in sql_content

    # Garante que a senha nunca é interpolada como identificador ou sem format(%L)
    assert ':"app_password"' not in sql_content
    assert "PASSWORD :" not in sql_content


def test_log_permissions_sql_valida_identificadores_e_usa_escape_seguro():
    sql_content = (DB_DIR / "log_permissions.sql").read_text(encoding="utf-8")

    assert "\\set ON_ERROR_STOP on" in sql_content
    assert "\\set QUIET on" in sql_content

    for required_var in ("app_role", "db_owner"):
        assert f"\\if :{{?{required_var}}}" in sql_content

    assert "^[a-zA-Z_][a-zA-Z0-9_]{0,62}$" in sql_content
    assert ":'app_role' <> :'db_owner'" in sql_content
    assert 'ALTER TABLE public.security_logs OWNER TO :"db_owner";' in sql_content
    assert 'ALTER TABLE public.password_reset_logs OWNER TO :"db_owner";' in sql_content


def test_scripts_python_em_backend_db_nao_usam_interpolacao_sql():
    for py_file in DB_DIR.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        assert not re.search(
            r"f[\"'].*\b(CREATE|ALTER|DROP|GRANT|REVOKE)\s+(ROLE|USER|TABLE|DATABASE)\b",
            content,
            re.IGNORECASE,
        ), f"Interpolação SQL insegura detectada em {py_file.name}"


def test_setup_sh_valida_identificadores_executa_psql_silencioso_e_gera_certificados():
    setup_content = (PROJECT_ROOT / "setup.sh").read_text(encoding="utf-8")

    assert "validate_identifier()" in setup_content
    assert "^[a-zA-Z_][a-zA-Z0-9_]{0,62}$" in setup_content

    for var_name in ("DB_NAME", "DB_ADMIN_USER", "DB_APP_USER", "DB_APP_ROLE"):
        assert f'validate_identifier "{var_name}"' in setup_content

    assert "psql --quiet --set ON_ERROR_STOP=1" in setup_content
    assert "gerar_certificados.sh" in setup_content
    assert "https://127.0.0.1:5000" in setup_content
