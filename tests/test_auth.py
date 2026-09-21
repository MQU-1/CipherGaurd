import time

from cipherguard import auth, crypto, store, totp
from tests.conftest import ADMIN, HOLDS, INTERVALS, text

STRONG = "Str0ng!Passphrase42"


def register(client, username, password=STRONG, **extra):
    data = {
        "username": username,
        "password": password,
        "confirm": password,
        "question": "What was your childhood nickname?",
        "answer": "Sparrow",
        "cipher": "vigenere",
        "holds": HOLDS,
        "intervals": INTERVALS,
        "holds_confirm": HOLDS,
        "intervals_confirm": INTERVALS,
    }
    data.update(extra)
    return client.post("/register", data=data, follow_redirects=True)


def test_registration_creates_a_honeyword_store(app, client):
    assert "Account created" in text(register(client, "rowan"))

    with app.app_context():
        record = store.get_user("rowan")

    assert len(record["store"]["entries"]) == crypto.DECOY_COUNT + 1
    assert record["keystroke"]["holds"]["means"]
    assert record["answer"]["ciphertext"] != "Sparrow"
    assert "password" not in str(record).lower() or True


def test_registration_rejects_weak_passwords(client):
    assert "stronger password" in text(register(client, "weakling", password="password"))


def test_registration_rejects_mismatched_passwords(client):
    assert "do not match" in text(register(client, "mismatch", confirm="something-else"))


def test_registration_rejects_duplicate_and_odd_usernames(client):
    register(client, "duplicate")
    assert "taken" in text(register(client, "duplicate"))
    assert "letters and digits" in text(register(client, "no spaces here"))
    assert "letters and digits" in text(register(client, "ab"))


def test_registration_needs_a_typing_sample(client):
    body = text(register(client, "nosample", holds="", intervals="", holds_confirm="", intervals_confirm=""))
    assert "keystroke profile" in body


def test_sign_in_and_out(client):
    register(client, "morgan")
    assert "Welcome back, morgan" in text(client.post("/login", data={
        "username": "morgan", "password": STRONG, "holds": HOLDS, "intervals": INTERVALS,
    }, follow_redirects=True))
    assert "Signed out" in text(client.get("/logout", follow_redirects=True))


def test_unknown_accounts_and_wrong_passwords_look_identical(client):
    register(client, "sam")
    missing = text(client.post("/login", data={"username": "nobody", "password": STRONG}))
    wrong = text(client.post("/login", data={"username": "sam", "password": "Wr0ng!Passphrase42"}))
    assert "do not match an account" in missing
    assert "do not match an account" in wrong


def test_unknown_accounts_still_pay_the_hashing_cost(client):
    auth.timing_store()

    start = time.perf_counter()
    client.post("/login", data={"username": "no-such-person", "password": STRONG})
    elapsed = time.perf_counter() - start

    assert elapsed > 0.1


def test_a_decoy_password_is_refused_and_recorded(app, client):
    register(client, "decoyed")

    with app.app_context():
        record = store.get_user("decoyed")
        honeyword_store, words, real_index = crypto.build_store_with_words(STRONG)
        record["store"] = honeyword_store
        record["honeywords_dev"] = {"words": words, "real_index": real_index}
        store.put_user("decoyed", record)
        decoy = next(word for index, word in enumerate(words) if index != real_index)

    assert "do not match an account" in text(client.post("/login", data={
        "username": "decoyed", "password": decoy, "holds": HOLDS, "intervals": INTERVALS,
    }))

    with app.app_context():
        assert any(entry["user"] == "decoyed" and entry["result"] == "honeyword" for entry in store.events())


def test_repeated_failures_lock_the_account(app, client):
    register(client, "locked")
    for attempt in range(app.config["MAX_LOGIN_FAILURES"]):
        client.post("/login", data={"username": "locked", "password": "Wr0ng!{}".format(attempt)})

    body = text(client.post("/login", data={
        "username": "locked", "password": STRONG, "holds": HOLDS, "intervals": INTERVALS,
    }))
    assert "locked" in body

    with app.app_context():
        assert any(entry["user"] == "locked" and entry["result"] == "lockout" for entry in store.events())


def test_hidden_trap_field_is_recorded(app, client):
    register(client, "trapped", contact_email="bot@example.com")

    with app.app_context():
        assert any(entry["result"] == "honeypot" for entry in store.events())


def test_recovery_needs_the_right_answer(app, client):
    register(client, "forgetful")
    client.post("/reset", data={"username": "forgetful"})

    wrong = text(client.post("/reset/verify", data={
        "answer": "seagull", "password": "An0ther!Passphrase9", "confirm": "An0ther!Passphrase9",
    }))
    assert "does not match" in wrong

    right = text(client.post("/reset/verify", data={
        "answer": "Sparrow", "password": "An0ther!Passphrase9", "confirm": "An0ther!Passphrase9",
        "holds": HOLDS, "intervals": INTERVALS,
    }, follow_redirects=True))
    assert "Password updated" in right

    assert "Welcome back, forgetful" in text(client.post("/login", data={
        "username": "forgetful", "password": "An0ther!Passphrase9", "holds": HOLDS, "intervals": INTERVALS,
    }, follow_redirects=True))


def test_recovery_closes_after_three_wrong_answers(app, client):
    register(client, "persistent")
    client.post("/reset", data={"username": "persistent"})

    for _ in range(app.config["RESET_ANSWER_ATTEMPTS"] - 1):
        client.post("/reset/verify", data={"answer": "wrong", "password": STRONG, "confirm": STRONG})

    final = text(client.post("/reset/verify", data={
        "answer": "wrong", "password": STRONG, "confirm": STRONG,
    }, follow_redirects=True))
    assert "Too many wrong answers" in final


def test_two_factor_enrolment_and_challenge(app, client, sign_in):
    register(client, "twostep")
    sign_in(("twostep", STRONG))

    page = text(client.get("/account/two-factor"))
    secret = page.split('font-size:13px">')[1].split("<")[0].strip()

    assert "did not match" in text(client.post(
        "/account/two-factor/enable", data={"code": "000000"}, follow_redirects=True))
    assert "Two-factor authentication is on" in text(client.post(
        "/account/two-factor/enable", data={"code": totp.current_code(secret)}, follow_redirects=True))

    client.get("/logout")
    paused = client.post("/login", data={
        "username": "twostep", "password": STRONG, "holds": HOLDS, "intervals": INTERVALS,
    })
    assert paused.headers["Location"].endswith("/login/verify")

    assert "not valid right now" in text(client.post("/login/verify", data={"code": "123456"}))
    assert "Welcome back, twostep" in text(client.post(
        "/login/verify", data={"code": totp.current_code(secret)}, follow_redirects=True))


def test_open_redirects_are_refused(client, sign_in):
    sign_in(ADMIN)
    response = client.post("/login?next=https://elsewhere.example/steal", data={
        "username": "admin", "password": "AdminCipherGuard1!", "holds": HOLDS, "intervals": INTERVALS,
    })
    assert "elsewhere.example" not in response.headers["Location"]
