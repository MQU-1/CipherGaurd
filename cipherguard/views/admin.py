from collections import Counter
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template, request, send_file

from cipherguard import auth, store

bp = Blueprint("admin", __name__, url_prefix="/admin")

CHART_DAYS = 14
SIGNIN_PATHS = ("/login", "/login/verify", "/reset", "/reset/verify", "/register")
TRACKED_RESULTS = ("success", "fail", "honeyword", "lockout", "sqli", "honeypot")


@bp.get("/audit")
@auth.admin_required
def audit():
    entries = store.events()
    tallies = Counter(entry.get("result") for entry in entries)
    return render_template(
        "admin/audit.html",
        entries=list(reversed(entries)),
        total=len(entries),
        tallies={result: tallies.get(result, 0) for result in TRACKED_RESULTS},
        series=_series(entries),
        actors=Counter(entry.get("user") for entry in entries).most_common(5),
    )


@bp.get("/audit/entries.json")
@auth.admin_required
def audit_entries():
    return jsonify(store.events())


@bp.get("/audit/carrier.png")
@auth.admin_required
def audit_carrier():
    return send_file(store.audit_carrier(), mimetype="image/png")


@bp.get("/traffic")
@auth.admin_required
def traffic_log():
    entries = store.requests()
    term = request.args.get("q", "").strip()
    filtered = _filter(entries, term.lower()) if term else entries
    signins = [entry for entry in entries
               if entry.get("method") == "POST" and entry.get("path") in SIGNIN_PATHS]
    return render_template(
        "admin/traffic.html",
        entries=list(reversed(filtered))[:400],
        signins=list(reversed(signins))[:40],
        term=term,
        total=len(entries),
        matched=len(filtered),
        signin_count=len(signins),
        error_count=sum(1 for entry in entries if (entry.get("status") or 0) >= 400),
        unique_addresses=len({entry.get("ip") for entry in entries}),
        popular=Counter(entry.get("path") for entry in entries).most_common(6),
    )


@bp.get("/traffic/entries.json")
@auth.admin_required
def traffic_entries():
    return jsonify(store.requests())


def _series(entries):
    counts = Counter(str(entry.get("ts", ""))[:10] for entry in entries)
    today = datetime.now(timezone.utc).date()
    points = []
    for offset in range(CHART_DAYS - 1, -1, -1):
        moment = today - timedelta(days=offset)
        points.append({"label": moment.strftime("%d %b"), "value": counts.get(moment.isoformat(), 0)})
    peak = max([point["value"] for point in points] or [0]) or 1
    for point in points:
        point["height"] = max(round(point["value"] / peak * 100), 2 if point["value"] else 0)
    return points


def _filter(entries, needle):
    fields = ("ts", "ip", "method", "path", "user", "agent", "referrer")
    return [entry for entry in entries
            if needle in " ".join(str(entry.get(field, "")).lower() for field in fields)]
