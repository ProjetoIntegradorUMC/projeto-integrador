import pyotp
import qrcode
from io import BytesIO
import base64


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
