import bcrypt

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72


def validate_password_policy(password: any) -> tuple[bool, str]:
    """
    Valida a política de senhas do Mentory:
    - Deve ser string e não nula.
    - Mínimo de 8 caracteres (alinhado a NIST SP 800-63B).
    - Máximo de 72 bytes em UTF-8 (limite intrínseco do algoritmo bcrypt).
    Retorna tupla (is_valid: bool, error_message: str).
    """
    if not isinstance(password, str):
        return False, "A senha deve ser um texto válido."

    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"A senha deve ter no mínimo {PASSWORD_MIN_LENGTH} caracteres."

    try:
        encoded = password.encode("utf-8")
    except (UnicodeEncodeError, AttributeError):
        return False, "A senha contém caracteres incompatíveis com UTF-8."

    if len(encoded) > PASSWORD_MAX_BYTES:
        return (
            False,
            f"A senha não pode exceder {PASSWORD_MAX_BYTES} bytes. "
            "Por favor, utilize uma senha menor ou reduza caracteres especiais multibyte."
        )

    return True, ""


def safe_check_password(password: any, password_hash: any) -> bool:
    """
    Compara de forma segura a senha fornecida com o hash bcrypt armazenado.
    Captura exceções de tamanho (>72 bytes) ou tipo sem gerar erro 500 no servidor.
    Retorna False para senhas inválidas ou de tipos incorretos.
    """
    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False

    try:
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > PASSWORD_MAX_BYTES:
            return False
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except (ValueError, TypeError, UnicodeEncodeError):
        return False


def get_json_payload(request) -> dict:
    """
    Obtém com segurança o corpo JSON da requisição Flask.
    Retorna um dicionário vazio caso o payload seja ausente, malformado
    ou de tipo diferente de dicionário (ex: listas ou literais primitivos),
    prevenindo exceções não tratadas e erros HTTP 500.
    """
    try:
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}
