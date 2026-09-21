import os
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("CIPHERGUARD_SECRET", "cipherguard-dev-secret-rotate-me")
    PEPPER = os.environ.get("CIPHERGUARD_PEPPER", "cipherguard-demo-pepper-rotate-me")
    INVOICE_KEY = os.environ.get("CIPHERGUARD_INVOICE_KEY", "cipherguard-demo-invoice-key-rotate-me").encode("utf-8")

    DATA_DIR = Path(os.environ.get("CIPHERGUARD_DATA") or PROJECT_ROOT / "data")
    USERS_FILE = DATA_DIR / "users.json"
    TRAFFIC_FILE = DATA_DIR / "traffic.json"
    AUDIT_IMAGE = DATA_DIR / "audit.png"
    INVOICE_IMAGE = DATA_DIR / "invoices.png"
    AVATAR_DIR = DATA_DIR / "avatars"

    MAX_LOGIN_FAILURES = 5
    LOCKOUT_SECONDS = 300
    RESET_ANSWER_ATTEMPTS = 3
    TRAFFIC_LIMIT = 2000
    ANOMALY_THRESHOLD = 45

    CURRENCY = "USD"
    CURRENCY_SYMBOL = "$"
    SHIPPING_FLAT_RATE = 9.0
    FREE_SHIPPING_THRESHOLD = 150.0

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    JSON_SORT_KEYS = False
    TEMPLATES_AUTO_RELOAD = True
