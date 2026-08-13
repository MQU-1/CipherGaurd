import hashlib
import hmac
import secrets
import string

KEY_SALT_LENGTH = 16


def _norm(text):
    return "".join(c for c in text.lower() if c in "abcdefghijklmnopqrstuvwxyz")


def vigenere(text, key, decrypt=False):
    text = _norm(text)
    if not key:
        return text
    key = _norm(key)
    if not key:
        return text
    result = []
    ki = 0
    for c in text:
        shift = ord(key[ki % len(key)]) - ord("a")
        if decrypt:
            shift = -shift
        idx = (ord(c) - ord("a") + shift) % 26
        result.append(chr(idx + ord("a")))
        ki += 1
    return "".join(result)


def _build_playfair_square(key):
    key_norm = _norm(key) + "abcdefghiklmnopqrstuvwxyz"
    seen = set()
    chars = []
    for c in key_norm:
        if c == "j":
            c = "i"
        if c not in seen:
            seen.add(c)
            chars.append(c)
    square = {}
    for i, c in enumerate(chars):
        square[c] = (i // 5, i % 5)
    return chars, square


def _playfair_digraphs(text):
    text = _norm(text).replace("j", "i")
    pairs = []
    i = 0
    while i < len(text):
        a = text[i]
        b = text[i + 1] if i + 1 < len(text) else "x"
        if a == b:
            pairs.append(a + "x")
            i += 1
        else:
            pairs.append(a + b)
            i += 2
    return pairs


def playfair(text, key, decrypt=False):
    chars, square = _build_playfair_square(key)
    text = _norm(text).replace("j", "i")
    result = []
    if not decrypt:
        for a, b in _playfair_digraphs(text):
            if a not in square:
                a = "x"
            if b not in square:
                b = "x"
            r1, c1 = square[a]
            r2, c2 = square[b]
            if r1 == r2:
                a2 = chars[r1 * 5 + (c1 + (1 if not decrypt else 4)) % 5]
                b2 = chars[r2 * 5 + (c2 + (1 if not decrypt else 4)) % 5]
            elif c1 == c2:
                a2 = chars[((r1 + (1 if not decrypt else 4)) % 5) * 5 + c1]
                b2 = chars[((r2 + (1 if not decrypt else 4)) % 5) * 5 + c2]
            else:
                a2 = chars[r1 * 5 + c2]
                b2 = chars[r2 * 5 + c1]
            result.append(a2)
            result.append(b2)
    else:
        pairs = []
        i = 0
        while i < len(text):
            pairs.append(text[i:i + 2])
            i += 2
        for a, b in pairs:
            if a not in square:
                a = "x"
            if b not in square:
                b = "x"
            r1, c1 = square[a]
            r2, c2 = square[b]
            if r1 == r2:
                a2 = chars[r1 * 5 + (c1 + 4) % 5]
                b2 = chars[r2 * 5 + (c2 + 4) % 5]
            elif c1 == c2:
                a2 = chars[((r1 + 4) % 5) * 5 + c1]
                b2 = chars[((r2 + 4) % 5) * 5 + c2]
            else:
                a2 = chars[r1 * 5 + c2]
                b2 = chars[r2 * 5 + c1]
            result.append(a2)
            result.append(b2)
    out = "".join(result)
    if decrypt:
        out = out.rstrip("x")
    return out


def _derive_key(pepper, salt, cipher_name):
    material = (salt + pepper + cipher_name).encode("utf-8")
    digest = hashlib.sha256(material).digest()
    letters = []
    for b in digest:
        letters.append(chr(ord("a") + (b % 26)))
        if len(letters) >= 16:
            break
    return "".join(letters)


def encrypt_answer(answer, pepper, cipher_name="vigenere"):
    salt = secrets.token_hex(KEY_SALT_LENGTH)
    key = _derive_key(pepper, salt, cipher_name)
    if cipher_name == "playfair":
        ciphertext = playfair(answer, key)
    else:
        ciphertext = vigenere(answer, key)
    return {"salt": salt, "cipher": cipher_name, "ciphertext": ciphertext}


def verify_answer(candidate, record, pepper):
    key = _derive_key(pepper, record["salt"], record["cipher"])
    if record["cipher"] == "playfair":
        ciphertext = playfair(candidate, key)
    else:
        ciphertext = vigenere(candidate, key)
    return hmac.compare_digest(ciphertext.encode("utf-8"), record["ciphertext"].encode("utf-8"))


def decrypt_answer(record, pepper):
    key = _derive_key(pepper, record["salt"], record["cipher"])
    if record["cipher"] == "playfair":
        return playfair(record["ciphertext"], key, decrypt=True)
    return vigenere(record["ciphertext"], key, decrypt=True)
