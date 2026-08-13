import json
import os
import time
import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   send_file, session, url_for)

from modules import (cipher_questions, crypto_utils, honeywords, keystroke,
                     password_strength, sqli_honeypot, stego, totp)

BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.environ["CIPHERGUARD_DATA"]) if os.environ.get("CIPHERGUARD_DATA") else BASE_DIR / "data"
AVATAR_DIR = DATA_DIR / "avatars"
USERS_FILE = DATA_DIR / "users.json"
AUDIT_IMAGE = DATA_DIR / "audit.png"
INVOICES_IMAGE = DATA_DIR / "invoices.png"
TRAFFIC_FILE = DATA_DIR / "traffic.json"

PEPPER = "cipherguard-demo-pepper-rotate-me"
INVOICE_KEY = b"cipherguard-demo-invoice-key-rotate-me"
MAX_FAILURES = 5
LOCKOUT_SECONDS = 300
MAX_TRAFFIC = 2000

DEMO_ADMIN_USER = "admin"
DEMO_ADMIN_PASSWORD = "AdminCipherGuard1!"
SUPERADMIN_USER = "superadmin"
SUPERADMIN_PASSWORD = "SuperAdminTraffic1!"
DEMO_USER = "demo"
DEMO_PASSWORD = "DemoHoneyword1!"

SEED_HOLDS = "82,88,76,91,84,79,86,90"
SEED_INTERVALS = "118,112,126,121,115,124,117"
SEED_HOLDS_2 = "80,90,78,89,86,81,84,92"
SEED_INTERVALS_2 = "120,114,124,119,117,122,118"

PRODUCTS = [
    {"id": "cipherlock-padlock", "name": "CipherLock Smart Padlock", "tagline": "Password, honeyword trap and keystroke checks in one shell", "price": 49.99, "accent": "#38bdf8", "initials": "CL"},
    {"id": "honeyjar-backup", "name": "HoneyJar Backup Safe", "tagline": "Decoy passwords keep credential-stuffing bots busy all night", "price": 79.99, "accent": "#f59e0b", "initials": "HJ"},
    {"id": "stegovault-frame", "name": "StegoVault Photo Frame", "tagline": "Store your secrets as pixels invisible to the naked eye", "price": 39.99, "accent": "#34d399", "initials": "SV"},
    {"id": "timechip-watch", "name": "TimeChip TOTP Watch", "tagline": "RFC 6238 rolling six-digit codes, always on your wrist", "price": 129.99, "accent": "#a78bfa", "initials": "TC"},
    {"id": "vigenere-desk", "name": "Vigenere Desk Cypher", "tagline": "Classical polyalphabetic encryption, desk-sized", "price": 24.99, "accent": "#f472b6", "initials": "VD"},
    {"id": "playfair-safe", "name": "Playfair Safe Box", "tagline": "Digraph substitution cipher security, classic edition", "price": 59.99, "accent": "#22d3ee", "initials": "PF"},
]

app = Flask(__name__)
app.secret_key = "cipherguard-demo-secret-rotate-me"


@app.context_processor
def inject_cart():
    def cart_count():
        return sum(session.get("cart", {}).values())
    return {"cart_count": cart_count, "product_lookup": {p["id"]: p for p in PRODUCTS}}


def load_users():
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def save_users(users):
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def load_traffic():
    if not TRAFFIC_FILE.exists():
        return []
    try:
        return json.loads(TRAFFIC_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []


def save_traffic(entries):
    TRAFFIC_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def log_traffic(status):
    entries = load_traffic()
    entries.append({
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ip": request.remote_addr or "?",
        "method": request.method,
        "path": request.path,
        "status": status,
        "user": current_user() or "-",
        "ua": (request.user_agent.string or "")[:120],
        "referer": request.referrer or "",
    })
    del entries[:-MAX_TRAFFIC]
    save_traffic(entries)


def seed_keystroke():
    samples = [
        {"holds": parse_timing(SEED_HOLDS), "intervals": parse_timing(SEED_INTERVALS)},
        {"holds": parse_timing(SEED_HOLDS_2), "intervals": parse_timing(SEED_INTERVALS_2)},
    ]
    return keystroke.enroll(samples)


def build_user(password, role="user", keep_plain=False, question="What was your childhood nickname?"):
    user = {
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "store": honeywords.build_store(password),
        "keystroke": seed_keystroke(),
        "question": question,
        "answer": cipher_questions.encrypt_answer("CipherGuardDemoAnswer", PEPPER, "vigenere"),
        "totp": {"enabled": False, "secret": None},
        "failures": 0,
        "locked_until": None,
        "last_login": None,
        "role": role,
    }
    if keep_plain:
        store, words, real_index = honeywords.build_store_dev(password)
        user["store"] = store
        user["honeywords_dev"] = {"words": words, "real_index": real_index}
    return user


def seed_demo_users():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    users = load_users()
    changed = False
    if DEMO_ADMIN_USER not in users:
        users[DEMO_ADMIN_USER] = build_user(DEMO_ADMIN_PASSWORD, role="admin")
        changed = True
    if SUPERADMIN_USER not in users:
        users[SUPERADMIN_USER] = build_user(SUPERADMIN_PASSWORD, role="admin")
        changed = True
    if DEMO_USER not in users:
        users[DEMO_USER] = build_user(DEMO_PASSWORD, keep_plain=True)
        changed = True
    if changed:
        save_users(users)


def current_role():
    return session.get("role")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Sign in to view that page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Sign in to view that page.", "error")
            return redirect(url_for("login"))
        if current_role() != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("shop"))
        return f(*args, **kwargs)
    return wrapper


def audit(action, username, result, detail=""):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ip": request.remote_addr or "?",
        "user": username,
        "action": action,
        "result": result,
        "detail": detail,
    }
    stego.append_entry(str(AUDIT_IMAGE), entry)


def parse_timing(raw):
    try:
        return [float(v) for v in raw.split(",") if v.strip() != ""]
    except ValueError:
        return []


def current_user():
    return session.get("user")


def cart_total():
    cart = session.get("cart", {})
    total = 0.0
    for pid, qty in cart.items():
        product = next((p for p in PRODUCTS if p["id"] == pid), None)
        if product:
            total += product["price"] * qty
    return round(total, 2)


def cart_items():
    items = []
    for pid, qty in session.get("cart", {}).items():
        product = next((p for p in PRODUCTS if p["id"] == pid), None)
        if product and qty > 0:
            items.append({"product": product, "qty": qty, "line_total": round(product["price"] * qty, 2)})
    return items


def is_locked(user):
    until = user.get("locked_until")
    if not until:
        return None
    remaining = int(until - time.time())
    if remaining > 0:
        return remaining
    user["locked_until"] = None
    return None


def record_failure(user):
    user["failures"] = user.get("failures", 0) + 1
    if user["failures"] >= MAX_FAILURES:
        user["locked_until"] = time.time() + LOCKOUT_SECONDS
        user["failures"] = 0
        return True
    return False


def compute_risk(user, matched_keystroke, distance):
    risk = 0
    reasons = []
    if not user.get("totp", {}).get("enabled"):
        risk += 10
        reasons.append("no 2FA configured")
    if not matched_keystroke:
        risk += 45
        reasons.append("keystroke distance {}".format(distance))
    ip = request.remote_addr or "?"
    if ip not in ("127.0.0.1", "::1"):
        risk += 15
        reasons.append("non-local source IP")
    hour = datetime.now().hour
    if hour < 6 or hour > 23:
        risk += 10
        reasons.append("login outside business hours")
    if not reasons:
        reasons.append("no risk signals")
    return min(risk, 100), reasons


def complete_login(username, risk, reasons, distance):
    session["user"] = username
    session["role"] = load_users().get(username, {}).get("role", "user")
    session["risk"] = risk
    session["risk_reasons"] = reasons
    session["anomaly"] = risk >= 45
    session["distance"] = distance
    audit("login", username, "success", "risk {}: {}".format(risk, "; ".join(reasons)))


def security_score(user):
    parts = []
    total = 0
    entries = user.get("store", {}).get("entries", [])
    if len(entries) >= 20:
        total += 25
        parts.append(("Honeyword list ({} decoys)".format(len(entries) - 1), 25))
    else:
        parts.append(("Honeyword list", 0))
    ks = user.get("keystroke", {})
    if ks.get("holds", {}).get("means"):
        total += 20
        parts.append(("Keystroke profile enrolled", 20))
    else:
        parts.append(("Keystroke profile", 0))
    if user.get("totp", {}).get("enabled"):
        total += 30
        parts.append(("Time-based 2FA enabled", 30))
    else:
        parts.append(("Time-based 2FA", 0))
    if user.get("answer"):
        total += 15
        parts.append(("Encrypted security question", 15))
    else:
        parts.append(("Security question", 0))
    if not user.get("failures"):
        total += 10
        parts.append(("No brute-force lockout events", 10))
    else:
        parts.append(("Lockout history clean", 0))
    return total, parts


def avatar_path(username):
    return AVATAR_DIR / "{}.png".format(username)


def ensure_avatar(username):
    path = avatar_path(username)
    if not path.exists():
        AVATAR_DIR.mkdir(parents=True, exist_ok=True)
        stego.make_avatar(username).save(path)
    return path


@app.route("/")
@app.route("/shop")
def shop():
    return render_template("shop.html", products=PRODUCTS)


@app.before_request
def monitor_for_injection():
    if request.path.startswith("/static") or request.path in ("/favicon.ico", "/search"):
        return None
    hits = sqli_honeypot.scan_params(request.values, exclude=("password", "confirm", "answer", "sealed", "next"))
    if not hits:
        return None
    username = current_user() or request.values.get("username") or "unknown"
    detail = "; ".join("'{}' matched {} on param {}".format(h["value"], h["label"], h["param"]) for h in hits[:5])
    audit("monitor", username, "sqli", detail)
    return None


@app.after_request
def record_traffic(resp):
    log_traffic(resp.status_code)
    return resp


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    user = current_user() or "anonymous"
    if not q:
        audit("search", user, "ok", "empty query")
        return render_template("search.html", results=[], q="", fake_sql=None)
    results = [p for p in PRODUCTS if q.lower() in p["name"].lower() or q.lower() in p["tagline"].lower()]
    fake_sql = sqli_honeypot.compile_query(q)
    hits = sqli_honeypot.scan_params(request.args)
    if hits:
        detail = "payload '{}' -> compiled: {} | matched: {}".format(
            q, fake_sql, ", ".join(h["label"] for h in hits))
        audit("search", user, "sqli", detail)
    else:
        audit("search", user, "ok", "query '{}' returned {} result(s)".format(q, len(results)))
    return render_template("search.html", results=results, q=q, fake_sql=fake_sql)


@app.route("/api/cart/count")
def api_cart_count():
    return jsonify({"count": sum(session.get("cart", {}).values())})


@app.route("/api/cart/add", methods=["POST"])
def api_cart_add():
    data = request.get_json(silent=True) or {}
    pid = data.get("id")
    if pid not in {p["id"] for p in PRODUCTS}:
        return jsonify({"ok": False}), 400
    cart = session.get("cart", {})
    cart[pid] = cart.get(pid, 0) + 1
    session["cart"] = cart
    return jsonify({"ok": True, "count": sum(cart.values())})


@app.route("/api/cart/set", methods=["POST"])
def api_cart_set():
    data = request.get_json(silent=True) or {}
    pid = data.get("id")
    qty = int(data.get("qty", 0))
    if pid not in {p["id"] for p in PRODUCTS}:
        return jsonify({"ok": False}), 400
    cart = session.get("cart", {})
    if qty <= 0:
        cart.pop(pid, None)
    else:
        cart[pid] = min(qty, 99)
    session["cart"] = cart
    return jsonify({"ok": True, "count": sum(cart.values()), "total": cart_total()})


@app.route("/cart")
def cart():
    return render_template("cart.html", items=cart_items(), total=cart_total())


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if not current_user():
        flash("Sign in to check out.", "error")
        return redirect(url_for("login", next=url_for("checkout")))
    items = cart_items()
    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("shop"))
    if request.method == "POST":
        order_id = secrets.token_hex(4).upper()
        invoice = {
            "order_id": order_id,
            "user": current_user(),
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "lines": [{"name": i["product"]["name"], "qty": i["qty"], "price": i["product"]["price"]} for i in items],
            "total": cart_total(),
        }
        invoice["sealed"] = crypto_utils.seal(invoice, INVOICE_KEY)
        stego.append_entry(str(INVOICES_IMAGE), invoice)
        audit("checkout", current_user(), "success", "order {} total ${:.2f}".format(order_id, invoice["total"]))
        session["cart"] = {}
        return redirect(url_for("order", order_id=order_id))
    return render_template("checkout.html", items=items, total=cart_total())


def load_invoices():
    return stego.read_entries(str(INVOICES_IMAGE))


@app.route("/order/<order_id>")
@login_required
def order(order_id):
    invoice = next((i for i in load_invoices() if i.get("order_id") == order_id), None)
    if not invoice:
        flash("Order not found.", "error")
        return redirect(url_for("shop"))
    me = current_user()
    if invoice.get("user") != me and current_role() != "admin":
        flash("You can only view your own orders.", "error")
        return redirect(url_for("orders"))
    return render_template("order.html", invoice=invoice)


@app.route("/orders")
def orders():
    username = current_user()
    if not username:
        return redirect(url_for("login"))
    mine = [i for i in load_invoices() if i.get("user") == username]
    return render_template("orders.html", invoices=list(reversed(mine)))


@app.route("/invoices/image")
def invoices_image():
    stego.ensure_audit_image(str(INVOICES_IMAGE))
    return send_file(INVOICES_IMAGE, mimetype="image/png")


@app.route("/invoice/<order_id>/sealed")
@login_required
def invoice_sealed(order_id):
    invoice = next((i for i in load_invoices() if i.get("order_id") == order_id), None)
    if not invoice:
        return "not found", 404
    me = current_user()
    if invoice.get("user") != me and current_role() != "admin":
        return "forbidden", 403
    return invoice["sealed"], 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "")
        answer_cipher = request.form.get("answer_cipher", "vigenere")
        users = load_users()

        if request.form.get("honeypot_email"):
            trap = request.form.get("honeypot_email", "")
            audit("register", request.form.get("username", "unknown"), "honeypot", "hidden trap field populated by bot (value: {})".format(trap[:80]))

        errors = []
        if not username or not username.isalnum():
            errors.append("Username must be letters and digits only.")
        elif username in users:
            errors.append("Username already taken.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if not question:
            errors.append("Pick a security question.")
        if not answer:
            errors.append("Security answer cannot be empty.")

        score = password_strength.score_password(password)
        if score["score"] < 3:
            errors.append("Password too weak: " + " ".join(score["feedback"]))

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", score=score)

        samples = []
        holds = parse_timing(request.form.get("holds", ""))
        intervals = parse_timing(request.form.get("intervals", ""))
        if holds or intervals:
            samples.append({"holds": holds, "intervals": intervals})
        holds2 = parse_timing(request.form.get("holds_confirm", ""))
        intervals2 = parse_timing(request.form.get("intervals_confirm", ""))
        if holds2 or intervals2:
            samples.append({"holds": holds2, "intervals": intervals2})
        if not samples:
            flash("Typing rhythm sample missing. Re-enable JavaScript and try again.", "error")
            return render_template("register.html", score=score)

        users[username] = {
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "store": honeywords.build_store(password),
            "keystroke": keystroke.enroll(samples),
            "question": question,
            "answer": cipher_questions.encrypt_answer(answer, PEPPER, answer_cipher),
            "totp": {"enabled": False, "secret": None},
            "failures": 0,
            "locked_until": None,
            "last_login": None,
        }
        save_users(users)
        ensure_avatar(username)
        audit("register", username, "success", "avatar embeds username via LSB steganography")
        flash("Account created. Passwords use salted PBKDF2 inside a honeyword list; your avatar hides your username in its pixels.", "ok")
        return redirect(url_for("login"))

    return render_template("register.html", score={"score": 0, "entropy": 0.0, "feedback": []})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        holds = parse_timing(request.form.get("holds", ""))
        intervals = parse_timing(request.form.get("intervals", ""))
        next_url = request.args.get("next", url_for("shop"))

        users = load_users()
        user = users.get(username)

        if request.form.get("honeypot_email"):
            trap = request.form.get("honeypot_email", "")
            audit("login", username, "honeypot", "hidden trap field populated by bot (value: {})".format(trap[:80]))

        if not user:
            audit("login", username, "fail", "unknown user")
            flash("Invalid credentials.", "error")
            return render_template("login.html", next_url=next_url)

        locked = is_locked(user)
        if locked:
            flash("Account locked due to repeated failures. Try again in {}s.".format(locked), "error")
            return render_template("login.html", next_url=next_url)

        result = honeywords.check_password(user["store"], password)
        if not result["ok"]:
            triggered_lock = record_failure(user)
            save_users(users)
            if result["honeyword"]:
                audit("login", username, "honeyword", "decoy password triggered credential-guessing alert")
            else:
                audit("login", username, "fail", "wrong password")
            if triggered_lock:
                audit("login", username, "lockout", "account locked for {}s".format(LOCKOUT_SECONDS))
                flash("Too many failures. Account locked for {}s.".format(LOCKOUT_SECONDS), "error")
            else:
                flash("Invalid credentials.", "error")
            return render_template("login.html", next_url=next_url)

        user["failures"] = 0
        user["locked_until"] = None
        save_users(users)

        matched, distance = keystroke.is_match(user["keystroke"], holds, intervals)
        risk, reasons = compute_risk(user, matched, distance)

        if user.get("totp", {}).get("enabled"):
            session["pending_2fa"] = username
            session["_risk"] = risk
            session["_risk_reasons"] = reasons
            session["_distance"] = distance
            session["_next"] = next_url
            audit("login", username, "pending", "credential + behavioral layers passed; awaiting 2FA")
            return redirect(url_for("login_2fa"))

        complete_login(username, risk, reasons, distance)
        return redirect(next_url)

    next_url = request.args.get("next", url_for("shop"))
    return render_template("login.html", next_url=next_url)


@app.route("/login/2fa", methods=["GET", "POST"])
def login_2fa():
    username = session.get("pending_2fa")
    if not username:
        return redirect(url_for("login"))
    users = load_users()
    user = users.get(username)
    if not user or not user.get("totp", {}).get("enabled"):
        session.pop("pending_2fa", None)
        return redirect(url_for("login"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if totp.verify(user["totp"]["secret"], code):
            complete_login(username, session.get("_risk", 0), session.get("_risk_reasons", []), session.get("_distance", ""))
            next_url = session.pop("_next", url_for("shop"))
            return redirect(next_url)
        triggered_lock = record_failure(user)
        save_users(users)
        audit("login", username, "fail", "invalid TOTP code")
        if triggered_lock:
            audit("login", username, "lockout", "account locked for {}s".format(LOCKOUT_SECONDS))
            session.pop("pending_2fa", None)
            flash("Too many failures. Account locked for {}s.".format(LOCKOUT_SECONDS), "error")
            return redirect(url_for("login"))
        flash("Invalid authenticator code.", "error")
    return render_template("2fa.html", username=username)


@app.route("/totp/setup")
def totp_setup():
    username = current_user()
    if not username:
        return redirect(url_for("login"))
    users = load_users()
    user = users.get(username, {})
    if user.get("totp", {}).get("enabled"):
        flash("Two-factor authentication is already enabled.", "ok")
        return redirect(url_for("account"))
    secret = session.get("totp_pending") or totp.generate_secret()
    session["totp_pending"] = secret
    uri = totp.provisioning_uri(username, secret)
    return render_template("totp.html", secret=secret, qr_data_uri=totp.qr_data_uri(uri))


@app.route("/totp/confirm", methods=["POST"])
def totp_confirm():
    username = current_user()
    if not username:
        return redirect(url_for("login"))
    secret = session.get("totp_pending")
    if not secret:
        flash("Start 2FA setup again.", "error")
        return redirect(url_for("totp_setup"))
    code = request.form.get("code", "").strip()
    if not totp.verify(secret, code):
        flash("That code did not match. It changes every 30 seconds.", "error")
        return redirect(url_for("totp_setup"))
    users = load_users()
    users[username]["totp"] = {"enabled": True, "secret": secret}
    save_users(users)
    session.pop("totp_pending", None)
    audit("totp", username, "success", "two-factor authentication enabled")
    flash("Two-factor authentication enabled.", "ok")
    return redirect(url_for("account"))


@app.route("/totp/disable", methods=["POST"])
def totp_disable():
    username = current_user()
    if not username:
        return redirect(url_for("login"))
    users = load_users()
    users[username]["totp"] = {"enabled": False, "secret": None}
    save_users(users)
    audit("totp", username, "disabled", "two-factor authentication removed")
    flash("Two-factor authentication disabled.", "ok")
    return redirect(url_for("account"))


@app.route("/reset", methods=["GET", "POST"])
def reset():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        users = load_users()
        user = users.get(username)
        if not user:
            audit("reset", username, "fail", "unknown user")
            flash("Invalid username.", "error")
            return render_template("reset.html", step=1)
        session["pending_reset"] = username
        session["reset_attempts"] = 0
        return render_template("reset.html", step=2, username=username, question=user["question"], answer_cipher=user["answer"]["cipher"])

    pending = session.get("pending_reset")
    if pending:
        users = load_users()
        user = users.get(pending)
        if user:
            return render_template("reset.html", step=2, username=pending, question=user["question"], answer_cipher=user["answer"]["cipher"])
    return render_template("reset.html", step=1)


@app.route("/reset/verify", methods=["POST"])
def reset_verify():
    username = session.get("pending_reset")
    if not username:
        flash("Start the reset flow again.", "error")
        return redirect(url_for("reset"))

    users = load_users()
    user = users.get(username)
    if not user:
        session.pop("pending_reset", None)
        return redirect(url_for("reset"))

    answer = request.form.get("answer", "")
    new_password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")

    if not cipher_questions.verify_answer(answer, user["answer"], PEPPER):
        attempts = session.get("reset_attempts", 0) + 1
        session["reset_attempts"] = attempts
        audit("reset", username, "fail", "wrong answer attempt {}/3".format(attempts))
        if attempts >= 3:
            session.pop("pending_reset", None)
            audit("reset", username, "lockout", "answer attempts exhausted")
            flash("Too many failed answers. Reset flow locked for this session.", "error")
            return redirect(url_for("login"))
        flash("Wrong answer ({}/3 attempts).".format(attempts), "error")
        return render_template("reset.html", step=2, username=username, question=user["question"], answer_cipher=user["answer"]["cipher"])

    if new_password != confirm:
        flash("New passwords do not match.", "error")
        return render_template("reset.html", step=2, username=username, question=user["question"], answer_cipher=user["answer"]["cipher"])

    score = password_strength.score_password(new_password)
    if score["score"] < 3:
        flash("New password too weak: " + " ".join(score["feedback"]), "error")
        return render_template("reset.html", step=2, username=username, question=user["question"], answer_cipher=user["answer"]["cipher"])

    samples = []
    holds = parse_timing(request.form.get("holds", ""))
    intervals = parse_timing(request.form.get("intervals", ""))
    if holds or intervals:
        samples.append({"holds": holds, "intervals": intervals})

    user["store"] = honeywords.build_store(new_password)
    if samples:
        user["keystroke"] = keystroke.enroll(samples)
    user["failures"] = 0
    user["locked_until"] = None
    save_users(users)
    session.pop("pending_reset", None)
    session.pop("reset_attempts", None)
    audit("reset", username, "success", "security question answered; password rotated")
    flash("Password reset. Honeyword list and keystroke profile rebuilt.", "ok")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    username = current_user()
    if username:
        audit("logout", username, "success")
    session.clear()
    return redirect(url_for("shop"))


@app.route("/account")
def account():
    username = current_user()
    if not username:
        return redirect(url_for("login"))
    users = load_users()
    user = users.get(username, {})
    score, parts = security_score(user)
    entries = stego.read_entries(str(AUDIT_IMAGE))
    caught = sum(1 for e in entries if e.get("result") in ("sqli", "honeypot", "honeyword"))
    return render_template("account.html", username=username, user=user, score=score, parts=parts,
                           risk=session.get("risk"), risk_reasons=session.get("risk_reasons"),
                           anomaly=session.get("anomaly"), caught=caught)


@app.route("/dashboard")
def dashboard_redirect():
    return redirect(url_for("account"))


@app.route("/audit")
@admin_required
def audit_view():
    entries = stego.read_entries(str(AUDIT_IMAGE))
    today = datetime.now(timezone.utc).date()
    day_counts = Counter((e.get("ts", "")[:10]) for e in entries)
    labels = []
    values = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        labels.append(d.strftime("%m/%d"))
        values.append(day_counts.get(d.isoformat(), 0))
    results = Counter(e.get("result") for e in entries)
    return render_template("audit.html", entries=list(reversed(entries)), count=len(entries),
                           labels=labels, values=values,
                           result_success=results.get("success", 0),
                           result_fail=results.get("fail", 0),
                           result_honeyword=results.get("honeyword", 0),
                           result_lockout=results.get("lockout", 0),
                           result_sqli=results.get("sqli", 0),
                           result_honeypot=results.get("honeypot", 0))


@app.route("/audit/image")
@admin_required
def audit_image():
    stego.ensure_audit_image(str(AUDIT_IMAGE))
    return send_file(AUDIT_IMAGE, mimetype="image/png")


@app.route("/audit/raw")
@admin_required
def audit_raw():
    entries = stego.read_entries(str(AUDIT_IMAGE))
    return jsonify(entries)


SIGNIN_PATHS = ("/login", "/login/2fa", "/reset", "/reset/verify")


@app.route("/traffic")
@admin_required
def traffic_view():
    entries = load_traffic()
    q = request.args.get("q", "").strip().lower()
    filtered = entries
    if q:
        filtered = [e for e in entries if q in " ".join(str(v).lower() for v in (
            e.get("ts", ""), e.get("ip", ""), e.get("method", ""), e.get("path", ""),
            e.get("user", ""), e.get("ua", ""), e.get("referer", "")))]
    signins = [e for e in entries if e.get("method") == "POST" and e.get("path") in SIGNIN_PATHS]
    errors = [e for e in entries if (e.get("status") or 0) >= 400]
    top_pages = Counter(e.get("path") for e in entries).most_common(6)
    return render_template("traffic.html", entries=list(reversed(filtered)),
                           signins=list(reversed(signins)), q=request.args.get("q", ""),
                           total=len(entries), signin_count=len(signins),
                           error_count=len(errors), unique_ips=len({e.get("ip") for e in entries}),
                           top_pages=top_pages)


@app.route("/traffic/raw")
@admin_required
def traffic_raw():
    return jsonify(load_traffic())


@app.route("/dev/honeywords", methods=["GET", "POST"])
@login_required
def dev_honeywords():
    users = load_users()
    demo = users.get(DEMO_USER)
    if not demo:
        flash("Demo user not seeded.", "error")
        return redirect(url_for("shop"))
    plain = demo.get("honeywords_dev") or {}
    words = plain.get("words", [])
    real_index = plain.get("real_index", -1)
    entries = demo.get("store", {}).get("entries", [])
    rows = [
        {"index": i, "word": w, "hash": entries[i] if i < len(entries) else None, "is_real": i == real_index}
        for i, w in enumerate(words)
    ]
    tested = None
    if request.method == "POST":
        candidate = request.form.get("password", "")
        res = honeywords.check_password(demo["store"], candidate)
        if res["ok"]:
            label = "REAL PASSWORD"
        elif res["honeyword"]:
            label = "HONEYWORD TRIGGERED"
        else:
            label = "NO MATCH"
        tested = {"candidate": candidate, "label": label}
        audit("dev", current_user(), "honeyword" if res["honeyword"] else ("ok" if res["ok"] else "fail"),
              "tested '{}' against demo honeyword store -> {}".format(candidate, label))
    return render_template("honeywords_dev.html", rows=rows, real_index=real_index, tested=tested,
                           demo=DEMO_USER, count=len(rows))


@app.route("/avatar/<username>")
def avatar(username):
    path = ensure_avatar(username)
    return send_file(path, mimetype="image/png")


@app.route("/api/strength")
def api_strength():
    password = request.args.get("password", "")
    return jsonify(password_strength.score_password(password))


seed_demo_users()


if __name__ == "__main__":
    stego.ensure_audit_image(str(AUDIT_IMAGE))
    stego.ensure_audit_image(str(INVOICES_IMAGE))
    app.run(host="127.0.0.1", port=5000, debug=True)
