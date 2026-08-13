import re

PATTERNS = [
    (r"union\s+(all\s+)?select\b", "union-select"),
    (r"('|\")\s*(or|and)\s+[0-9a-z_'\"]+\s*=\s*[0-9a-z_'\"]+", "boolean-tautology"),
    (r"('|\")\s*=\s*('|\")", "quote-equality"),
    (r"\b1\s*=\s*1\b", "constant-true"),
    (r"\b(or|and)\s+\d+\s*=\s*\d+", "numeric-constant"),
    (r";\s*(drop|truncate|delete|insert|update|alter|exec)\b", "stacked-query"),
    (r"(--|#|\/\*)", "comment-injection"),
    (r"\b(information_schema|sqlite_master|mysql\.user|pg_catalog)\b", "schema-probe"),
    (r"\b(sleep|pg_sleep|benchmark|waitfor\s+delay)\s*\(", "time-based"),
    (r"\b(load_file|into\s+outfile|xp_cmdshell)\b", "file-shell-escape"),
    (r"\b(concat|group_concat|char|chr)\s*\(", "string-functions"),
    (r"0x[0-9a-f]{4,}", "hex-encoding"),
    (r"\bcast\s*\(|convert\s*\(", "type-conversion"),
]

COMPILED = [(re.compile(pattern, re.IGNORECASE), label) for pattern, label in PATTERNS]


def scan(value):
    if value is None:
        return None
    text = str(value)
    for regex, label in COMPILED:
        if regex.search(text):
            return label
    return None


def scan_params(params, exclude=()):
    hits = []
    for key in params.keys():
        if key in exclude:
            continue
        value = params.get(key)
        if isinstance(value, (list, tuple)):
            for item in value:
                label = scan(item)
                if label:
                    hits.append({"param": key, "label": label, "value": str(item)[:120]})
        else:
            label = scan(value)
            if label:
                hits.append({"param": key, "label": label, "value": str(value)[:120]})
    return hits


def compile_query(q, table="products"):
    escaped = str(q).replace("'", "''")
    return "SELECT id, name, price FROM {} WHERE name LIKE '%{}%' OR tagline LIKE '%{}%';".format(table, escaped, escaped)
