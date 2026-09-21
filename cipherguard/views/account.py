from flask import (Blueprint, flash, redirect, render_template, request,
                   session, url_for)

from cipherguard import auth, crypto, store, totp

bp = Blueprint("account", __name__, url_prefix="/account")

LAB_ACCOUNT = "demo"
RECENT_EVENT_LIMIT = 8


@bp.get("")
@auth.login_required
def overview():
    username = auth.current_username()
    record = store.get_user(username) or {}
    score, checks = auth.posture(record)
    mine = [entry for entry in store.events() if entry.get("user") == username]
    return render_template(
        "account/overview.html",
        username=username,
        record=record,
        score=score,
        checks=checks,
        recent=list(reversed(mine))[:RECENT_EVENT_LIMIT],
        order_count=len(store.invoices_for(username)),
        remaining=auth.lock_remaining(record),
    )


@bp.get("/two-factor")
@auth.login_required
def two_factor():
    username = auth.current_username()
    record = store.get_user(username) or {}
    if (record.get("totp") or {}).get("enabled"):
        return render_template("account/two_factor.html", enabled=True, username=username)

    secret = session.get("totp_pending") or totp.generate_secret()
    session["totp_pending"] = secret
    return render_template(
        "account/two_factor.html",
        enabled=False,
        username=username,
        secret=secret,
        qr=totp.qr_data_uri(totp.provisioning_uri(username, secret)),
    )


@bp.post("/two-factor/enable")
@auth.login_required
def enable_two_factor():
    username = auth.current_username()
    secret = session.get("totp_pending")
    if not secret:
        flash("Start the setup again.", "notice")
        return redirect(url_for("account.two_factor"))
    if not totp.verify(secret, request.form.get("code", "").strip()):
        flash("That code did not match. Codes change every 30 seconds.", "error")
        return redirect(url_for("account.two_factor"))

    record = store.get_user(username)
    record["totp"] = {"enabled": True, "secret": secret}
    store.put_user(username, record)
    session.pop("totp_pending", None)
    store.record_event("totp", username, "success", "second factor enrolled")
    flash("Two-factor authentication is on.", "success")
    return redirect(url_for("account.overview"))


@bp.post("/two-factor/disable")
@auth.login_required
def disable_two_factor():
    username = auth.current_username()
    record = store.get_user(username)
    record["totp"] = {"enabled": False, "secret": None}
    store.put_user(username, record)
    store.record_event("totp", username, "disabled", "second factor removed")
    flash("Two-factor authentication is off.", "notice")
    return redirect(url_for("account.overview"))


@bp.route("/honeywords", methods=["GET", "POST"])
@auth.login_required
def honeyword_lab():
    record = store.get_user(LAB_ACCOUNT)
    if not record:
        flash("The lab account has not been seeded.", "error")
        return redirect(url_for("account.overview"))

    plain = record.get("honeywords_dev") or {}
    words = plain.get("words", [])
    real_index = plain.get("real_index", -1)
    hashes = record.get("store", {}).get("entries", [])
    rows = [
        {"index": index, "word": word, "digest": hashes[index] if index < len(hashes) else "",
         "real": index == real_index}
        for index, word in enumerate(words)
    ]

    tested = None
    if request.method == "POST":
        candidate = request.form.get("candidate", "")
        verdict = crypto.check_store(record["store"], candidate)
        tested = {"candidate": candidate, "verdict": verdict}
        store.record_event("lab", auth.current_username(), verdict,
                           "tested a candidate against the {} honeyword store".format(LAB_ACCOUNT))

    return render_template(
        "account/honeywords.html",
        rows=rows,
        tested=tested,
        lab_account=LAB_ACCOUNT,
        real_index=real_index,
    )
