import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    debug_enabled = os.getenv("FLASK_DEBUG", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    # Se os certificados existirem, sobe com HTTPS. Caso contrário, HTTP.
    # Em produção, a aplicação deve rodar atrás de um proxy reverso (Nginx) com SSL
    if os.path.exists("cert.pem") and os.path.exists("key.pem"):
        print("Certificados encontrados. Iniciando servidor HTTPS (TLS)...")
        app.run(debug=debug_enabled, ssl_context=("cert.pem", "key.pem"))
    else:
        print("AVISO: Certificados TLS (cert.pem, key.pem) não encontrados.")
        print("Iniciando servidor HTTP. Para HTTPS local, gere os certificados.")
        app.run(debug=debug_enabled)