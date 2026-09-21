import secrets
import time
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urlparse

from flask import current_app, flash, redirect, request, session, url_for

from cipherguard import ciphers, crypto, keystroke, stego, store

DEFAULT_QUESTION = "What was your childhood nickname?"

SECURITY_QUESTIONS = (
    "What was your childhood nickname?",
    "What was the name of your first school?",
    "Which street did you live on at ten years old?",
    "What was the make of your first bicycle?",
)

DEMO_ACCOUNTS = (
    {"username": "admin", "password": "AdminCipherGuard1!", "role": "admin", "keep_words": False},
    {"username": "superadmin", "password": "SuperAdminTraffic1!", "role": "admin", "keep_words": False},
    {"username": "demo", "password": "DemoHoneyword1!", "role": "user", "keep_words": True},
)

DEMO_ANSWER = "CipherGuardDemoAnswer"

SEED_SAMPLES = (
    {"holds": [82, 88, 76, 91, 84, 79, 86, 90], "intervals": [118, 112, 126, 121, 115, 124, 117]},
    {"holds": [80, 90, 78, 89, 86, 81, 84, 92], "intervals": [120, 114, 124, 119, 117, 122, 118]},
)

PENDING_KEYS = ("pending_2fa", "pending_risk", "pending_next", "pending_reset", "reset_attempts", "totp_pending")

LOCAL_ADDRESSES = ("127.0.0.1", "::1", "localhost")
OFFICE_HOURS = (6, 23)

RISK_WEIGHTS = {
    "no_second_factor": 10,
    "keystroke_mismatch": 45,
    "remote_address": 15,
    "unusual_hour": 10,
}


def current_username():
    return session.get("user")


def current_role():
    return session.get("role", "guest")


def is_signed_in():
    return bool(current_username())


def is_admin():
    return current_role() == "admin"


def begin_session(username, record, assessment):
    clear_pending()
    session["user"] = username
    session["role"] = record.get("role", "user")
    session["risk"] = assessment["score"]
    session["risk_signals"] = assessment["signals"]
    session["anomaly"] = assessment["score"] >= current_app.config["ANOMALY_THRESHOLD"]
    session.permanent = True


def end_session():
    session.clear()


def clear_pending():
    for key in PENDING_KEYS:
        session.pop(key, None)


def login_required(view):
    @wraps(view)
    def guarded(*args, **kwargs):
        if not is_signed_in():
            flash("Sign in to continue.", "notice")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return guarded


def admin_required(view):
    @wraps(view)
    def guarded(*args, **kwargs):
        if not is_signed_in():
            flash("Sign in to continue.", "notice")
            return redirect(url_for("auth.login", next=request.path))
        if not is_admin():
            flash("That area is restricted to administrators.", "error")
            return redirect(url_for("storefront.home"))
        return view(*args, **kwargs)
    return guarded


def safe_redirect(target, fallback_endpoint="storefront.home"):
    fallback = url_for(fallback_endpoint)
    if not target:
        return fallback
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/") or target.startswith("//"):
        return fallback
    return target


def create_account(username, password, question, answer, cipher, samples, role="user", keep_words=False):
    if keep_words:
        honeyword_store, words, real_index = crypto.build_store_with_words(password)
    else:
        honeyword_store, words, real_index = crypto.build_store(password), None, None

    record = {
        "created": _now(),
        "role": role,
        "store": honeyword_store,
        "keystroke": keystroke.enroll(samples),
        "question": question or DEFAULT_QUESTION,
        "answer": ciphers.encrypt_answer(answer, current_app.config["PEPPER"], cipher),
        "totp": {"enabled": False, "secret": None},
        "failures": 0,
        "locked_until": None,
        "last_login": None,
    }
    if keep_words:
        record["honeywords_dev"] = {"words": words, "real_index": real_index}

    store.put_user(username, record)
    ensure_avatar(username)
    return record


def seed_demo_accounts():
    current_app.config["DATA_DIR"].mkdir(parents=True, exist_ok=True)
    current_app.config["AVATAR_DIR"].mkdir(parents=True, exist_ok=True)
    existing = store.load_users()
    created = []
    for account in DEMO_ACCOUNTS:
        if account["username"] in existing:
            continue
        create_account(
            account["username"],
            account["password"],
            DEFAULT_QUESTION,
            DEMO_ANSWER,
            ciphers.VIGENERE,
            [dict(sample) for sample in SEED_SAMPLES],
            role=account["role"],
            keep_words=account["keep_words"],
        )
        created.append(account["username"])
    return created


_TIMING_STORE = None


def timing_store():
    global _TIMING_STORE
    if _TIMING_STORE is None:
        _TIMING_STORE = crypto.build_store(secrets.token_urlsafe(24))
    return _TIMING_STORE


def lock_remaining(record):
    until = record.get("locked_until")
    if not until:
        return 0
    remaining = int(until - time.time())
    return remaining if remaining > 0 else 0


def register_failure(record):
    record["failures"] = record.get("failures", 0) + 1
    if record["failures"] >= current_app.config["MAX_LOGIN_FAILURES"]:
        record["failures"] = 0
        record["locked_until"] = time.time() + current_app.config["LOCKOUT_SECONDS"]
        return True
    return False


def clear_failures(record):
    record["failures"] = 0
    record["locked_until"] = None


def mark_signed_in(record):
    record["last_login"] = _now()


def assess_risk(record, keystroke_matched, distance, address, moment=None):
    moment = moment or datetime.now()
    score = 0
    signals = []

    if not (record.get("totp") or {}).get("enabled"):
        score += RISK_WEIGHTS["no_second_factor"]
        signals.append("No second factor enrolled on this account")

    if not keystroke_matched:
        score += RISK_WEIGHTS["keystroke_mismatch"]
        signals.append("Typing rhythm outside the enrolled profile" + _distance_note(distance))

    if address not in LOCAL_ADDRESSES:
        score += RISK_WEIGHTS["remote_address"]
        signals.append("Sign-in from a non-local address")

    if not OFFICE_HOURS[0] <= moment.hour < OFFICE_HOURS[1]:
        score += RISK_WEIGHTS["unusual_hour"]
        signals.append("Sign-in outside usual hours")

    if not signals:
        signals.append("Nothing unusual about this sign-in")

    return {"score": min(score, 100), "signals": signals, "distance": distance}


def posture(record):
    entries = record.get("store", {}).get("entries", [])
    checks = [
        {
            "label": "Honeyword store",
            "detail": "{} decoy hashes guard the real password".format(max(len(entries) - 1, 0)),
            "points": 25,
            "earned": len(entries) >= 20,
        },
        {
            "label": "Keystroke profile",
            "detail": "Typing rhythm enrolled from your own samples",
            "points": 20,
            "earned": keystroke.is_enrolled(record.get("keystroke")),
        },
        {
            "label": "Two-factor authentication",
            "detail": "Six-digit codes rotating every 30 seconds",
            "points": 30,
            "earned": bool((record.get("totp") or {}).get("enabled")),
        },
        {
            "label": "Encrypted recovery answer",
            "detail": "Stored as ciphertext, never in the clear",
            "points": 15,
            "earned": bool(record.get("answer")),
        },
        {
            "label": "Clean lockout history",
            "detail": "No failed attempts pending against this account",
            "points": 10,
            "earned": not record.get("failures") and not lock_remaining(record),
        },
    ]
    return sum(check["points"] for check in checks if check["earned"]), checks


def avatar_path(username):
    return current_app.config["AVATAR_DIR"] / "{}.png".format(username)


def ensure_avatar(username):
    path = avatar_path(username)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        stego.make_avatar(username).save(path)
    return path


def _distance_note(distance):
    if distance is None:
        return " (no sample captured)"
    return " (distance {})".format(distance)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
