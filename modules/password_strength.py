import math
import re

COMMON_PASSWORDS = {
    "password", "123456", "123456789", "12345678", "1234567", "12345",
    "1234", "123", "qwerty", "abc123", "football", "monkey", "letmein",
    "dragon", "111111", "baseball", "iloveyou", "trustno1", "sunshine",
    "princess", "welcome", "whatever", "admin", "root", "passw0rd",
    "password1", "qwerty123", "1q2w3e4r", "123123", "666666", "000000",
    "superman", "batman", "mustang", "shadow", "michael", "master",
    "harley", "dallas", "jordan", "password123", "access", "hello",
}

CHAR_SETS = [
    ("lower", "abcdefghijklmnopqrstuvwxyz"),
    ("upper", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    ("digit", "0123456789"),
    ("symbol", r"!@#$%^&*()-_=+[]{};:,.<>/?~`|"),
]


def _charset_size(password):
    pool = 0
    for _, chars in CHAR_SETS:
        if any(c in chars for c in password):
            pool += len(chars)
    return max(pool, 1)


def entropy_bits(password):
    if not password:
        return 0.0
    return len(password) * math.log2(_charset_size(password))


def score_password(password):
    score = 0
    feedback = []

    if not password:
        return {"score": 0, "entropy": 0.0, "feedback": ["Password cannot be empty."]}

    low = password.lower()
    if low in COMMON_PASSWORDS or re.fullmatch(r"(\d)\1+", password):
        feedback.append("Password is a known/common password.")
        return {"score": 0, "entropy": entropy_bits(password), "feedback": feedback}

    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Use at least 8 characters.")

    classes = 0
    for _, chars in CHAR_SETS:
        if any(c in chars for c in password):
            classes += 1
    if classes >= 3:
        score += 1
    else:
        feedback.append("Mix letters, digits, and symbols.")

    if re.search(r"[a-z].*[A-Z]|[A-Z].*[a-z]", password):
        score += 1
    else:
        feedback.append("Mix upper and lower case.")

    if entropy_bits(password) >= 45:
        score += 1
    else:
        feedback.append("Make it longer or more varied (aim ~45+ bits of entropy).")

    if len(password) >= 12:
        score += 1
        feedback.append("Good length.")

    score = min(score, 4)

    if not feedback:
        feedback = ["Strong password."]

    return {"score": score, "entropy": round(entropy_bits(password), 1), "feedback": feedback}
