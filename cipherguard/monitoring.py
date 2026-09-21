import re

from flask import request

from cipherguard import auth, store

SIGNATURES = (
    (r"union\s+(all\s+)?select\b", "union-select"),
    (r"('|\")\s*(or|and)\s+[0-9a-z_'\"]+\s*=\s*[0-9a-z_'\"]+", "boolean-tautology"),
    (r"('|\")\s*=\s*('|\")", "quote-equality"),
    (r"\b1\s*=\s*1\b", "constant-true"),
    (r"\b(or|and)\s+\d+\s*=\s*\d+", "numeric-constant"),
    (r";\s*(drop|truncate|delete|insert|update|alter|exec)\b", "stacked-query"),
    (r"(--|#|/\*)", "comment-terminator"),
    (r"\b(information_schema|sqlite_master|mysql\.user|pg_catalog)\b", "schema-probe"),
    (r"\b(sleep|pg_sleep|benchmark|waitfor\s+delay)\s*\(", "time-based"),
    (r"\b(load_file|into\s+outfile|xp_cmdshell)\b", "file-escape"),
    (r"\b(concat|group_concat|char|chr)\s*\(", "string-assembly"),
    (r"0x[0-9a-f]{4,}", "hex-encoding"),
    (r"\b(cast|convert)\s*\(", "type-conversion"),
)

PATTERNS = tuple((re.compile(expression, re.IGNORECASE), label) for expression, label in SIGNATURES)

MAX_RECORDED_VALUE = 120

UNMONITORED_PREFIXES = ("/static", "/avatar", "/api")
UNMONITORED_PATHS = ("/favicon.ico", "/search")
UNLOGGED_PREFIXES = ("/static", "/avatar")
SENSITIVE_PARAMS = ("password", "confirm", "current_password", "answer", "code", "sealed", "next")


def register(app):
    app.before_request(inspect_request)
    app.after_request(log_request)


def inspect_request():
    if _matches(request.path, UNMONITORED_PREFIXES) or request.path in UNMONITORED_PATHS:
        return None
    hits = scan(request.values, skip=SENSITIVE_PARAMS)
    if hits:
        actor = auth.current_username() or request.values.get("username") or "anonymous"
        store.record_event("monitor", actor, "sqli", summarise(hits))
    return None


def log_request(response):
    if not _matches(request.path, UNLOGGED_PREFIXES):
        store.record_request(response.status_code, auth.current_username())
    return response


def classify(value):
    if value is None:
        return None
    text = str(value)
    for pattern, label in PATTERNS:
        if pattern.search(text):
            return label
    return None


def scan(params, skip=()):
    hits = []
    for name in params.keys():
        if name in skip:
            continue
        for value in _values(params, name):
            label = classify(value)
            if label:
                hits.append({"param": name, "label": label, "value": str(value)[:MAX_RECORDED_VALUE]})
    return hits


def summarise(hits, limit=5):
    return "; ".join("{} matched {} on {}".format(hit["value"], hit["label"], hit["param"]) for hit in hits[:limit])


def compile_query(term, table="catalog_items"):
    escaped = str(term).replace("'", "''")
    return "SELECT slug, name, price FROM {} WHERE name ILIKE '%{}%' OR summary ILIKE '%{}%' LIMIT 24;".format(
        table, escaped, escaped)


def _values(params, name):
    getter = getattr(params, "getlist", None)
    if callable(getter):
        return getter(name)
    value = params.get(name)
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _matches(path, prefixes):
    return any(path.startswith(prefix) for prefix in prefixes)
