import json
from datetime import datetime, timezone

from flask import current_app, has_request_context, request

from cipherguard import stego

MAX_USER_AGENT = 140


def load_users():
    return _read_json(current_app.config["USERS_FILE"], {})


def save_users(users):
    _write_json(current_app.config["USERS_FILE"], users)


def get_user(username):
    return load_users().get(username)


def put_user(username, record):
    users = load_users()
    users[username] = record
    save_users(users)
    return record


def user_exists(username):
    return username in load_users()


def record_event(action, actor, result, detail=""):
    entry = {
        "ts": _timestamp(),
        "ip": _client_ip(),
        "user": actor or "anonymous",
        "action": action,
        "result": result,
        "detail": detail,
    }
    stego.append_record(str(current_app.config["AUDIT_IMAGE"]), entry)
    return entry


def events():
    return stego.read_records(str(current_app.config["AUDIT_IMAGE"]))


def audit_carrier():
    path = current_app.config["AUDIT_IMAGE"]
    stego.ensure_carrier(str(path))
    return path


def add_invoice(invoice):
    stego.append_record(str(current_app.config["INVOICE_IMAGE"]), invoice)
    return invoice


def invoices():
    return [_restore_invoice(record) for record in stego.read_records(str(current_app.config["INVOICE_IMAGE"]))]


def find_invoice(order_id):
    return next((invoice for invoice in invoices() if invoice.get("order_id") == order_id), None)


def invoices_for(username):
    return list(reversed([invoice for invoice in invoices() if invoice.get("user") == username]))


def record_request(status, actor):
    entries = requests()
    entries.append({
        "ts": _timestamp(),
        "ip": request.remote_addr or "unknown",
        "method": request.method,
        "path": request.path,
        "status": status,
        "user": actor or "-",
        "agent": (request.user_agent.string or "")[:MAX_USER_AGENT],
        "referrer": request.referrer or "",
    })
    del entries[:-current_app.config["TRAFFIC_LIMIT"]]
    _write_json(current_app.config["TRAFFIC_FILE"], entries)


def requests():
    return _read_json(current_app.config["TRAFFIC_FILE"], [])


def _restore_invoice(invoice):
    lines = []
    for line in invoice.get("lines", []):
        quantity = line.get("quantity", line.get("qty", 1))
        price = line.get("price", 0.0)
        lines.append({
            "slug": line.get("slug", ""),
            "name": line.get("name", "Item"),
            "kind": line.get("kind", "product"),
            "quantity": quantity,
            "price": price,
            "subtotal": line.get("subtotal", round(price * quantity, 2)),
        })
    invoice["lines"] = lines
    invoice.setdefault("subtotal", invoice.get("total", 0.0))
    invoice.setdefault("shipping", 0.0)
    return invoice


def _client_ip():
    if not has_request_context():
        return "local"
    return request.remote_addr or "unknown"


def _read_json(path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
