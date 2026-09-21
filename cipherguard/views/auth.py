from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)

from cipherguard import auth, ciphers, crypto, keystroke, store, totp

bp = Blueprint("auth", __name__)

HONEYPOT_FIELD = "contact_email"
USERNAME_MIN = 3
USERNAME_MAX = 20


@bp.route("/login", methods=["GET", "POST"])
def login():
    destination = auth.safe_redirect(request.args.get("next"))
    if request.method == "GET":
        return render_template("auth/login.html", destination=destination)

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    _check_honeypot("login", username)

    record = store.get_user(username)
    if record is None:
        crypto.check_store(auth.timing_store(), password)
        store.record_event("login", username or "anonymous", "fail", "unknown account")
        flash("Those details do not match an account.", "error")
        return render_template("auth/login.html", destination=destination, username=username)

    remaining = auth.lock_remaining(record)
    if remaining:
        flash("This account is locked for another {} seconds.".format(remaining), "error")
        return render_template("auth/login.html", destination=destination, username=username)

    verdict = crypto.check_store(record["store"], password)
    if verdict != crypto.REAL:
        locked = auth.register_failure(record)
        store.put_user(username, record)
        if verdict == crypto.DECOY:
            store.record_event("login", username, "honeyword",
                               "decoy password used, credential store is compromised")
        else:
            store.record_event("login", username, "fail", "wrong password")
        if locked:
            store.record_event("login", username, "lockout", "locked for {} seconds after repeated failures".format(
                current_app.config["LOCKOUT_SECONDS"]))
            flash("Too many attempts. The account is locked for {} seconds.".format(
                current_app.config["LOCKOUT_SECONDS"]), "error")
        else:
            flash("Those details do not match an account.", "error")
        return render_template("auth/login.html", destination=destination, username=username)

    auth.clear_failures(record)
    store.put_user(username, record)

    matched, distance = keystroke.compare(
        record.get("keystroke", {}),
        keystroke.parse(request.form.get("holds")),
        keystroke.parse(request.form.get("intervals")),
    )
    assessment = auth.assess_risk(record, matched, distance, request.remote_addr)

    if (record.get("totp") or {}).get("enabled"):
        session["pending_2fa"] = username
        session["pending_risk"] = assessment
        session["pending_next"] = destination
        store.record_event("login", username, "pending",
                           "password and rhythm accepted, waiting on the second factor")
        return redirect(url_for("auth.verify"))

    return _finish_login(username, record, assessment, destination)


@bp.route("/login/verify", methods=["GET", "POST"])
def verify():
    username = session.get("pending_2fa")
    record = store.get_user(username) if username else None
    if not record or not (record.get("totp") or {}).get("enabled"):
        auth.clear_pending()
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if totp.verify(record["totp"]["secret"], code):
            destination = session.get("pending_next") or url_for("storefront.home")
            assessment = session.get("pending_risk") or {"score": 0, "signals": []}
            return _finish_login(username, record, assessment, destination)

        locked = auth.register_failure(record)
        store.put_user(username, record)
        store.record_event("login", username, "fail", "invalid authenticator code")
        if locked:
            auth.clear_pending()
            store.record_event("login", username, "lockout", "locked after repeated second-factor failures")
            flash("Too many attempts. The account is locked.", "error")
            return redirect(url_for("auth.login"))
        flash("That code is not valid right now.", "error")

    return render_template("auth/verify.html", username=username)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("auth/register.html", questions=auth.SECURITY_QUESTIONS, form={})

    form = {
        "username": request.form.get("username", "").strip(),
        "question": request.form.get("question", "").strip(),
        "cipher": request.form.get("cipher", ciphers.VIGENERE),
    }
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")
    answer = request.form.get("answer", "").strip()
    _check_honeypot("register", form["username"])

    samples = _samples()
    report = crypto.evaluate_strength(password)
    problems = _registration_problems(form, password, confirm, answer, report, samples)

    if problems:
        for problem in problems:
            flash(problem, "error")
        return render_template("auth/register.html", questions=auth.SECURITY_QUESTIONS, form=form)

    cipher = form["cipher"] if form["cipher"] in ciphers.SUPPORTED else ciphers.VIGENERE
    auth.create_account(form["username"], password, form["question"], answer, cipher, samples)
    store.record_event("register", form["username"], "success",
                       "honeyword store built, rhythm enrolled from {} sample(s)".format(len(samples)))
    flash("Account created. Sign in to finish setting up two-factor authentication.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/reset", methods=["GET", "POST"])
def reset():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        record = store.get_user(username)
        if record is None:
            store.record_event("reset", username or "anonymous", "fail", "unknown account")
            flash("That account does not exist.", "error")
            return render_template("auth/reset.html", step=1)
        session["pending_reset"] = username
        session["reset_attempts"] = 0
        return render_template("auth/reset.html", step=2, username=username, record=record)

    username = session.get("pending_reset")
    record = store.get_user(username) if username else None
    if record:
        return render_template("auth/reset.html", step=2, username=username, record=record)
    return render_template("auth/reset.html", step=1)


@bp.post("/reset/verify")
def reset_verify():
    username = session.get("pending_reset")
    record = store.get_user(username) if username else None
    if not record:
        flash("Start the reset again.", "notice")
        return redirect(url_for("auth.reset"))

    answer = request.form.get("answer", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")

    if not ciphers.verify_answer(answer, record["answer"], current_app.config["PEPPER"]):
        attempts = session.get("reset_attempts", 0) + 1
        session["reset_attempts"] = attempts
        allowed = current_app.config["RESET_ANSWER_ATTEMPTS"]
        store.record_event("reset", username, "fail", "wrong answer, attempt {} of {}".format(attempts, allowed))
        if attempts >= allowed:
            auth.clear_pending()
            store.record_event("reset", username, "lockout", "recovery attempts exhausted")
            flash("Too many wrong answers. Start again from the sign-in page.", "error")
            return redirect(url_for("auth.login"))
        flash("That answer does not match ({} of {}).".format(attempts, allowed), "error")
        return render_template("auth/reset.html", step=2, username=username, record=record)

    if password != confirm:
        flash("The two passwords do not match.", "error")
        return render_template("auth/reset.html", step=2, username=username, record=record)

    report = crypto.evaluate_strength(password)
    if not report["accepted"]:
        flash("Choose a stronger password. {}".format(" ".join(report["advice"])), "error")
        return render_template("auth/reset.html", step=2, username=username, record=record)

    record["store"] = crypto.build_store(password)
    samples = _samples()
    if samples:
        record["keystroke"] = keystroke.enroll(samples)
    auth.clear_failures(record)
    store.put_user(username, record)
    auth.clear_pending()
    store.record_event("reset", username, "success", "recovery answer accepted, honeyword store rebuilt")
    flash("Password updated. Sign in with the new one.", "success")
    return redirect(url_for("auth.login"))


@bp.get("/logout")
def logout():
    username = auth.current_username()
    if username:
        store.record_event("logout", username, "success", "session ended")
    auth.end_session()
    flash("Signed out.", "notice")
    return redirect(url_for("storefront.home"))


def _finish_login(username, record, assessment, destination):
    auth.mark_signed_in(record)
    store.put_user(username, record)
    auth.begin_session(username, record, assessment)
    store.record_event("login", username, "success",
                       "risk {} ({})".format(assessment["score"], "; ".join(assessment["signals"])))
    flash("Welcome back, {}.".format(username), "success")
    return redirect(auth.safe_redirect(destination))


def _samples():
    samples = []
    for holds_field, intervals_field in (("holds", "intervals"), ("holds_confirm", "intervals_confirm")):
        holds = keystroke.parse(request.form.get(holds_field))
        intervals = keystroke.parse(request.form.get(intervals_field))
        if holds or intervals:
            samples.append({"holds": holds, "intervals": intervals})
    return samples


def _registration_problems(form, password, confirm, answer, report, samples):
    problems = []
    username = form["username"]
    if not username.isalnum() or not USERNAME_MIN <= len(username) <= USERNAME_MAX:
        problems.append("Usernames are {} to {} letters and digits.".format(USERNAME_MIN, USERNAME_MAX))
    elif store.user_exists(username):
        problems.append("That username is taken.")
    if password != confirm:
        problems.append("The two passwords do not match.")
    if not report["accepted"]:
        problems.append("Choose a stronger password. {}".format(" ".join(report["advice"])))
    if not form["question"]:
        problems.append("Choose a recovery question.")
    if not answer:
        problems.append("Answer the recovery question.")
    if not samples:
        problems.append("Type the password twice so the keystroke profile can be captured.")
    return problems


def _check_honeypot(action, username):
    trap = request.form.get(HONEYPOT_FIELD, "").strip()
    if trap:
        store.record_event(action, username or "anonymous", "honeypot",
                           "hidden field completed by an automated client: {}".format(trap[:80]))
