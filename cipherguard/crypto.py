import base64
import hashlib
import hmac
import json
import math
import random
import re
import secrets
import string
import struct

DIGEST_NAME = "sha256"
ITERATIONS = 100000
SALT_BYTES = 16

DECOY_COUNT = 19
MUTATION_ATTEMPTS = 400

REAL = "real"
DECOY = "decoy"
UNKNOWN = "unknown"

MINIMUM_ACCEPTED_SCORE = 3
STRENGTH_LABELS = ("Unusable", "Weak", "Fair", "Good", "Strong")

CHARACTER_SETS = (
    "abcdefghijklmnopqrstuvwxyz",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "0123456789",
    "!@#$%^&*()-_=+[]{};:,.<>/?~`|\\'\"",
)

COMMON_PASSWORDS = frozenset({
    "000000", "111111", "123", "1234", "12345", "123123", "123456", "1234567",
    "12345678", "123456789", "1q2w3e4r", "666666", "abc123", "access", "admin",
    "baseball", "batman", "dallas", "dragon", "football", "harley", "hello",
    "iloveyou", "jordan", "letmein", "master", "michael", "monkey", "mustang",
    "passw0rd", "password", "password1", "password123", "princess", "qwerty",
    "qwerty123", "root", "shadow", "sunshine", "superman", "trustno1",
    "welcome", "whatever",
})

REPEATED_CHARACTER = re.compile(r"^(.)\1+$")
SEQUENTIAL_RUN = re.compile(r"(?:abcd|bcde|cdef|defg|1234|2345|3456|4567|5678|6789)", re.IGNORECASE)
MIXED_CASE = re.compile(r"[a-z].*[A-Z]|[A-Z].*[a-z]")

_DECOY_YEARS = ("2023", "2024", "2025", "2026")
_DECOY_MARKS = ("!", "?", "@", "#", "$", "&", "*")


def hash_password(password, iterations=ITERATIONS):
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, iterations)
    return "{}${}${}".format(_b64(salt), iterations, _b64(digest))


def verify_password(stored, candidate):
    try:
        salt_b64, rounds, digest_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        iterations = int(rounds)
    except (AttributeError, TypeError, ValueError):
        return False
    return hmac.compare_digest(_derive(candidate, salt, iterations), expected)


def build_store(password):
    store, _, _ = build_store_with_words(password)
    return store


def build_store_with_words(password):
    words, real_index = generate_honeywords(password)
    store = {"real_index": real_index, "entries": [hash_password(word) for word in words]}
    return store, words, real_index


def generate_honeywords(password):
    rng = random.Random(secrets.token_bytes(16))
    candidates = {password}
    attempts = 0
    while len(candidates) <= DECOY_COUNT and attempts < MUTATION_ATTEMPTS:
        candidates.add(_mutate(password, rng))
        attempts += 1
    words = list(candidates)
    rng.shuffle(words)
    return words, words.index(password)


def check_store(store, candidate):
    real_index = store.get("real_index")
    for index, entry in enumerate(store.get("entries", [])):
        if verify_password(entry, candidate):
            return REAL if index == real_index else DECOY
    return UNKNOWN


def evaluate_strength(password):
    if not password:
        return _strength(0, 0.0, ["Enter a password."])

    if password.lower() in COMMON_PASSWORDS or REPEATED_CHARACTER.match(password):
        return _strength(0, entropy_bits(password), ["This password appears in every breach list."])

    score = 0
    advice = []

    if len(password) >= 8:
        score += 1
    else:
        advice.append("Use at least 8 characters.")

    if sum(1 for characters in CHARACTER_SETS if any(c in characters for c in password)) >= 3:
        score += 1
    else:
        advice.append("Combine letters, digits and symbols.")

    if MIXED_CASE.search(password):
        score += 1
    else:
        advice.append("Mix upper and lower case.")

    bits = entropy_bits(password)
    if bits >= 45:
        score += 1
    else:
        advice.append("Add length or variety to clear 45 bits of entropy.")

    if len(password) >= 12:
        score += 1

    if SEQUENTIAL_RUN.search(password):
        score = max(score - 1, 1)
        advice.append("Avoid keyboard or alphabet runs.")

    score = max(0, min(score, 4))
    if not advice:
        advice.append("Strong enough for an account you care about.")
    return _strength(score, bits, advice)


def entropy_bits(password):
    if not password:
        return 0.0
    pool = sum(len(characters) for characters in CHARACTER_SETS if any(c in characters for c in password))
    return round(len(password) * math.log2(max(pool, 2)), 1)


def seal(payload, key):
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ciphertext = _xor(plaintext, _keystream(key, len(plaintext)))
    tag = hmac.new(key, ciphertext, hashlib.sha256).digest()
    return _urlsafe(ciphertext) + "." + _urlsafe(tag)


def unseal(sealed, key):
    try:
        ciphertext_b64, tag_b64 = str(sealed).split(".")
        ciphertext = base64.urlsafe_b64decode(ciphertext_b64)
        tag = base64.urlsafe_b64decode(tag_b64)
    except (AttributeError, TypeError, ValueError):
        return None
    if not hmac.compare_digest(hmac.new(key, ciphertext, hashlib.sha256).digest(), tag):
        return None
    try:
        return json.loads(_xor(ciphertext, _keystream(key, len(ciphertext))).decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


def seal_matches(sealed, key, expected):
    opened = unseal(sealed, key)
    if opened is None:
        return False
    return all(opened.get(field) == value for field, value in expected.items())


def _mutate(password, rng):
    strategies = (
        lambda word: word + rng.choice(_DECOY_MARKS),
        lambda word: word + rng.choice(_DECOY_YEARS),
        lambda word: word + str(rng.randint(0, 99)).zfill(2),
        lambda word: word.capitalize(),
        lambda word: word.swapcase(),
        lambda word: word.upper(),
        lambda word: rng.choice(_DECOY_MARKS) + word,
        lambda word: word[:-1] + rng.choice(string.ascii_letters + string.digits),
        lambda word: word[:1].upper() + word[1:] + rng.choice(string.digits),
        lambda word: word.replace("a", "@", 1).replace("o", "0", 1),
    )
    return rng.choice(strategies)(password)


def _strength(score, bits, advice):
    return {
        "score": score,
        "label": STRENGTH_LABELS[score],
        "entropy": bits,
        "advice": advice,
        "accepted": score >= MINIMUM_ACCEPTED_SCORE,
    }


def _keystream(key, length):
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        stream += hmac.new(key, struct.pack(">I", counter), hashlib.sha256).digest()
        counter += 1
    return bytes(stream[:length])


def _xor(data, stream):
    return bytes(left ^ right for left, right in zip(data, stream))


def _derive(password, salt, iterations):
    return hashlib.pbkdf2_hmac(DIGEST_NAME, password.encode("utf-8"), salt, iterations)


def _b64(raw):
    return base64.b64encode(raw).decode("ascii")


def _urlsafe(raw):
    return base64.urlsafe_b64encode(raw).decode("ascii")
