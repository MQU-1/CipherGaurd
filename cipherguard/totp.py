import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

import qrcode

from cipherguard import png

DIGITS = 6
PERIOD = 30
SECRET_BYTES = 20
DEFAULT_WINDOW = 1

QR_SCALE = 6
QR_BORDER = 2


def generate_secret():
    return base64.b32encode(secrets.token_bytes(SECRET_BYTES)).decode("ascii").rstrip("=")


def provisioning_uri(username, secret, issuer="CipherGuard"):
    label = quote("{}:{}".format(issuer, username), safe="")
    return "otpauth://totp/{}?secret={}&issuer={}&algorithm=SHA1&digits={}&period={}".format(
        label, secret, quote(issuer, safe=""), DIGITS, PERIOD)


def qr_data_uri(uri, scale=QR_SCALE, border=QR_BORDER):
    code = qrcode.QRCode(border=border, box_size=1)
    code.add_data(uri)
    code.make(fit=True)
    raster = _render(code.get_matrix(), scale)
    return "data:image/png;base64," + base64.b64encode(png.encode(raster)).decode("ascii")


def current_code(secret):
    return code_at(secret, int(time.time()) // PERIOD)


def seconds_remaining():
    return PERIOD - int(time.time()) % PERIOD


def verify(secret, code, window=DEFAULT_WINDOW):
    if not secret or not code or not code.isdigit() or len(code) != DIGITS:
        return False
    counter = int(time.time()) // PERIOD
    return any(hmac.compare_digest(code_at(secret, counter + drift), code) for drift in range(-window, window + 1))


def code_at(secret, counter):
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % (10 ** DIGITS)).zfill(DIGITS)


def _render(matrix, scale):
    size = len(matrix) * scale
    pixels = bytearray(b"\xff" * (size * size * 3))
    dark = b"\x00" * (scale * 3)

    for row, cells in enumerate(matrix):
        for column, filled in enumerate(cells):
            if not filled:
                continue
            for line in range(scale):
                start = ((row * scale + line) * size + column * scale) * 3
                pixels[start:start + scale * 3] = dark

    return png.Raster(size, size, pixels)
