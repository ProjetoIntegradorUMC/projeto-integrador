import pyotp
import qrcode
from io import BytesIO
import base64
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


TOTP_ENCRYPTION_KEY = "TOTP_ENCRYPTION_KEY"


@lru_cache(maxsize=1)
def get_totp_fernet():
    """Retorna o cifrador Fernet configurado para os segredos TOTP."""
    key = os.getenv(TOTP_ENCRYPTION_KEY)
    if not key:
        raise RuntimeError(
            f"A variável de ambiente {TOTP_ENCRYPTION_KEY} é obrigatória"
        )

    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError) as exc:
        raise RuntimeError(
            f"A variável de ambiente {TOTP_ENCRYPTION_KEY} não contém uma chave Fernet válida"
        ) from exc


def encrypt_totp_secret(secret):
    """Cifra um segredo TOTP antes de persisti-lo."""
    if secret is None:
        return None
    return get_totp_fernet().encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_totp_secret(encrypted_secret):
    """Decifra um segredo TOTP recuperado do banco."""
    if encrypted_secret is None:
        return None

    try:
        return get_totp_fernet().decrypt(encrypted_secret.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError) as exc:
        raise RuntimeError("Não foi possível decifrar o segredo TOTP armazenado") from exc


def generate_totp_secret():
    """Gera um novo segredo TOTP (Base32)."""
    return pyotp.random_base32()


def get_totp(secret):
    """Retorna o objeto TOTP para um segredo específico."""
    return pyotp.TOTP(secret)


def get_provisioning_uri(secret, email, issuer="Projeto Integrador"):
    """Gera a URI de provisionamento (usada para gerar QR code)."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def generate_qr_code(provisioning_uri):
    """Gera QR code em base64 a partir da URI de provisionamento."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, kind="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/png;base64,{img_str}"


def verify_totp_code(secret, code):
    """Valida um código TOTP. Aceita códigos do presente e dos últimos 2 períodos."""
    totp = pyotp.TOTP(secret)
    # valid_window=2 permite margem de sincronização do relógio
    return totp.verify(code, valid_window=2)
