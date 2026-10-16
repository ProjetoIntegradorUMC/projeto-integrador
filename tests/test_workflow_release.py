import re
from pathlib import Path


def test_workflow_release_existe():
    """Verifica se o arquivo de workflow release.yml existe no local correto."""
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "release.yml"
    )
    assert workflow_path.exists(), "Arquivo release.yml não encontrado"


def test_actions_pinadas_por_sha_40_caracteres():
    """Garante que toda action externa no workflow está pinada por um commit SHA de 40 caracteres (Issue #92)."""
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "release.yml"
    )
    content = workflow_path.read_text(encoding="utf-8")

    # Localiza todas as linhas que utilizam actions externas (uses:)
    uses_lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip().startswith("uses:")
    ]
    assert len(uses_lines) > 0, "Nenhuma action encontrada no workflow"

    # Regex para validar o padrão: uses: nome/action@<40_chars_sha> # versao
    sha_pattern = re.compile(r"^uses:\s+[^@]+@[0-9a-fA-F]{40}(\s+#.*)?$")

    for line in uses_lines:
        assert sha_pattern.match(line), (
            f"A action na linha '{line}' não está fixada por um SHA de 40 caracteres!"
        )


def test_principio_do_menor_privilegio_no_workflow():
    """Verifica se as permissões globais foram desabilitadas e restritas ao job de release (Issue #92)."""
    workflow_path = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "release.yml"
    )
    content = workflow_path.read_text(encoding="utf-8")

    # Permissões globais devem ser desabilitadas por padrão
    assert (
        "permissions: {}" in content
    ), "Permissões globais devem ser estritas: permissions: {}"

    # Permissão de escrita deve estar restrita dentro do job release
    assert (
        "contents: write" in content
    ), "A permissão contents: write deve estar restrita ao job"
