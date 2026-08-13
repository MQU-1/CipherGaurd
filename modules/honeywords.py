import random
import secrets
import string

from modules import crypto_utils

HONEYWORD_COUNT = 19


def _tweak(password, rng):
    mutations = [
        lambda p: p + rng.choice(string.digits + "!@#$%^&*"),
        lambda p: p.capitalize(),
        lambda p: p + str(rng.randint(0, 99)).zfill(2),
        lambda p: p + rng.choice(["!", "?", "@", "#", "$"]),
        lambda p: p.upper(),
        lambda p: p[:-1] + rng.choice(string.digits + string.ascii_letters),
        lambda p: p + rng.choice(["2024", "2025", "2026"]),
        lambda p: p.swapcase(),
        lambda p: p + rng.choice(["a", "e", "x", "z"]),
        lambda p: "!" + p,
    ]
    return rng.choice(mutations)(password)


def generate_honeywords(real_password):
    rng = random.Random(secrets.token_hex(8))
    words = {real_password}
    guard = 0
    while len(words) < HONEYWORD_COUNT + 1 and guard < 500:
        words.add(_tweak(real_password, rng))
        guard += 1
    words = list(words)
    rng.shuffle(words)
    real_index = words.index(real_password)
    return words, real_index


def build_store(real_password):
    store, _, _ = build_store_dev(real_password)
    return store


def build_store_dev(real_password):
    words, real_index = generate_honeywords(real_password)
    store = {
        "real_index": real_index,
        "entries": [crypto_utils.hash_password(w) for w in words],
    }
    return store, words, real_index


def check_password(store, candidate):
    for i, stored in enumerate(store.get("entries", [])):
        if crypto_utils.verify_password(stored, candidate):
            if i == store["real_index"]:
                return {"ok": True, "honeyword": False}
            return {"ok": False, "honeyword": True}
    return {"ok": False, "honeyword": False}
