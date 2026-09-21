from tests.conftest import ADMIN, DEMO, text

RESTRICTED = ["/admin/audit", "/admin/traffic", "/admin/audit/entries.json", "/admin/traffic/entries.json"]


def test_admin_pages_require_signing_in(client):
    for path in RESTRICTED:
        response = client.get(path)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_admin_pages_are_closed_to_ordinary_accounts(client, sign_in):
    sign_in(DEMO)
    for path in RESTRICTED:
        assert client.get(path).status_code == 302


def test_audit_trail_reads_back_from_the_carrier(client, sign_in):
    sign_in(ADMIN)
    body = text(client.get("/admin/audit"))

    assert "Audit trail" in body
    assert "login" in body

    entries = client.get("/admin/audit/entries.json").get_json()
    assert entries and {"ts", "ip", "user", "action", "result"} <= set(entries[0])


def test_carrier_image_is_served(client, sign_in):
    sign_in(ADMIN)
    response = client.get("/admin/audit/carrier.png")
    assert response.status_code == 200
    assert response.data.startswith(b"\x89PNG")


def test_request_log_filters(client, sign_in):
    sign_in(ADMIN)
    client.get("/shop")

    assert "Request log" in text(client.get("/admin/traffic"))
    assert "/shop" in text(client.get("/admin/traffic?q=shop"))
    assert client.get("/admin/traffic/entries.json").get_json()


def test_static_files_stay_out_of_the_request_log(client, sign_in):
    sign_in(ADMIN)
    client.get("/static/css/base.css")
    paths = {entry["path"] for entry in client.get("/admin/traffic/entries.json").get_json()}
    assert not any(path.startswith("/static") for path in paths)


def test_honeyword_lab_reports_each_verdict(client, sign_in):
    sign_in(DEMO)
    assert "Twenty hashes" in text(client.get("/account/honeywords"))

    real = text(client.post("/account/honeywords", data={"candidate": "DemoHoneyword1!"}))
    assert "live password" in real

    unknown = text(client.post("/account/honeywords", data={"candidate": "not-in-the-store"}))
    assert "No hash in the store matched" in unknown


def test_account_page_scores_the_session(client, sign_in):
    sign_in(DEMO)
    body = text(client.get("/account"))
    assert "Account hardening" in body
    assert "Session risk" in body or "out of 100" in body
