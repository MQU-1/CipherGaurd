import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def generate_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def provisioning_uri(username, secret, issuer="CipherGuard"):
    account = quote("{}:{}".format(issuer, username), safe="")
    return "otpauth://totp/{}?secret={}&issuer={}&algorithm=SHA1&digits=6&period=30".format(
        account, secret, quote(issuer, safe=""))


def qr_data_uri(uri):
    import io
    import qrcode
    img = qrcode.make(uri, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _code_at(secret_b32, counter, digits=6):
    pad = "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(secret_b32 + pad)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def current_code(secret_b32, digits=6):
    return _code_at(secret_b32, int(time.time()) // 30, digits)


def verify(secret_b32, code, window=1, digits=6):
    if not code or not code.isdigit() or len(code) != digits:
        return False
    counter = int(time.time()) // 30
    for offset in range(-window, window + 1):
        if hmac.compare_digest(_code_at(secret_b32, counter + offset, digits), code):
            return True
    return False
