import pytest


def test_cabecalhos_de_seguranca_no_frontend(client):
    """Verifica se as respostas para o frontend incluem os cabeçalhos de segurança essenciais."""
    response = client.get("/")
    assert response.status_code == 200

    # MIME sniffing
    assert response.headers.get("X-Content-Type-Options") == "nosniff"

    # Clickjacking
    assert response.headers.get("X-Frame-Options") == "DENY"

    # Referrer
    assert (
        response.headers.get("Referrer-Policy")
        == "strict-origin-when-cross-origin"
    )

    # Content Security Policy (CSP)
    csp = response.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "script-src 'self' https://cdn.jsdelivr.net" in csp
    assert "img-src 'self' data:" in csp
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_cabecalhos_de_seguranca_nas_rotas_de_api(client):
    """Verifica se as respostas de endpoints de API também recebem os cabeçalhos protetores."""
    response = client.get("/auth/status")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_hsts_quando_em_conexao_segura(flask_app, client):
    """Valida se HSTS é aplicado quando a requisição é segura (HTTPS)."""
    response = client.get("/", base_url="https://localhost")
    hsts = response.headers.get("Strict-Transport-Security")
    assert hsts is not None
    assert "max-age=" in hsts
    assert "includeSubDomains" in hsts
