import hashlib
import hmac
import secrets

ALPHABET = "abcdefghijklmnopqrstuvwxyz"
SQUARE_ALPHABET = "abcdefghiklmnopqrstuvwxyz"
SALT_BYTES = 16
KEY_LENGTH = 16
PADDING = "x"

VIGENERE = "vigenere"
PLAYFAIR = "playfair"
SUPPORTED = (VIGENERE, PLAYFAIR)


def normalise(text):
    return "".join(character for character in str(text).lower() if character in ALPHABET)


def vigenere_encrypt(text, key):
    return _vigenere(text, key, 1)


def vigenere_decrypt(text, key):
    return _vigenere(text, key, -1)


def playfair_encrypt(text, key):
    letters, positions = _square(key)
    output = []
    for first, second in _digraphs(text):
        output.extend(_shift_pair(letters, positions, first, second, 1))
    return "".join(output)


def playfair_decrypt(text, key):
    letters, positions = _square(key)
    body = normalise(text).replace("j", "i")
    output = []
    for index in range(0, len(body) - 1, 2):
        output.extend(_shift_pair(letters, positions, body[index], body[index + 1], -1))
    return "".join(output).rstrip(PADDING)


def encrypt_answer(answer, pepper, cipher=VIGENERE):
    name = cipher if cipher in SUPPORTED else VIGENERE
    salt = secrets.token_hex(SALT_BYTES)
    key = derive_key(pepper, salt, name)
    ciphertext = playfair_encrypt(answer, key) if name == PLAYFAIR else vigenere_encrypt(answer, key)
    return {"salt": salt, "cipher": name, "ciphertext": ciphertext}


def verify_answer(candidate, record, pepper):
    if not record:
        return False
    key = derive_key(pepper, record["salt"], record["cipher"])
    if record["cipher"] == PLAYFAIR:
        ciphertext = playfair_encrypt(candidate, key)
    else:
        ciphertext = vigenere_encrypt(candidate, key)
    return hmac.compare_digest(ciphertext.encode("utf-8"), str(record["ciphertext"]).encode("utf-8"))


def decrypt_answer(record, pepper):
    key = derive_key(pepper, record["salt"], record["cipher"])
    if record["cipher"] == PLAYFAIR:
        return playfair_decrypt(record["ciphertext"], key)
    return vigenere_decrypt(record["ciphertext"], key)


def derive_key(pepper, salt, cipher):
    digest = hashlib.sha256((salt + pepper + cipher).encode("utf-8")).digest()
    return "".join(ALPHABET[byte % 26] for byte in digest[:KEY_LENGTH])


def _vigenere(text, key, direction):
    body = normalise(text)
    stream = normalise(key)
    if not stream:
        return body
    output = []
    for index, character in enumerate(body):
        shift = (ord(stream[index % len(stream)]) - ord("a")) * direction
        output.append(ALPHABET[(ord(character) - ord("a") + shift) % 26])
    return "".join(output)


def _square(key):
    letters = []
    for character in normalise(key) + SQUARE_ALPHABET:
        folded = "i" if character == "j" else character
        if folded not in letters:
            letters.append(folded)
    positions = {letter: (index // 5, index % 5) for index, letter in enumerate(letters)}
    return letters, positions


def _digraphs(text):
    body = normalise(text).replace("j", "i")
    pairs = []
    index = 0
    while index < len(body):
        first = body[index]
        second = body[index + 1] if index + 1 < len(body) else PADDING
        if first == second:
            pairs.append((first, PADDING))
            index += 1
        else:
            pairs.append((first, second))
            index += 2
    return pairs


def _shift_pair(letters, positions, first, second, direction):
    first = first if first in positions else PADDING
    second = second if second in positions else PADDING
    row_a, column_a = positions[first]
    row_b, column_b = positions[second]
    if row_a == row_b:
        return (letters[row_a * 5 + (column_a + direction) % 5], letters[row_b * 5 + (column_b + direction) % 5])
    if column_a == column_b:
        return (letters[((row_a + direction) % 5) * 5 + column_a], letters[((row_b + direction) % 5) * 5 + column_b])
    return (letters[row_a * 5 + column_b], letters[row_b * 5 + column_a])
