import base64
import hashlib
import hmac
import json
import secrets
import struct

PBKDF2_ITERATIONS = 100000


def hash_password(password, iterations=PBKDF2_ITERATIONS):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "{}${}${}".format(base64.b64encode(salt).decode(), iterations, base64.b64encode(digest).decode())


def verify_password(stored, password):
    try:
        salt_b64, iterations_s, digest_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        iterations = int(iterations_s)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def _keystream(key, length):
    out = bytearray()
    counter = 0
    while len(out) < length:
        out += hmac.new(key, struct.pack(">I", counter), hashlib.sha256).digest()
        counter += 1
    return bytes(out[:length])


def seal(data, key):
    plain = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    stream = _keystream(key, len(plain))
    cipher = bytes(a ^ b for a, b in zip(plain, stream))
    tag = hmac.new(key, cipher, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(cipher).decode() + "." + base64.urlsafe_b64encode(tag).decode()


def unseal(payload, key):
    try:
        cipher_b64, tag_b64 = payload.split(".")
        cipher = base64.urlsafe_b64decode(cipher_b64)
        tag = base64.urlsafe_b64decode(tag_b64)
    except (ValueError, TypeError):
        return None
    expected = hmac.new(key, cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, tag):
        return None
    stream = _keystream(key, len(cipher))
    plain = bytes(a ^ b for a, b in zip(cipher, stream))
    try:
        return json.loads(plain.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
