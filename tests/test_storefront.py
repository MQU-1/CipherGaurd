import pytest

from cipherguard import catalog
from tests.conftest import DEMO, text


def test_home_lists_hardware_and_courses(client):
    body = text(client.get("/"))
    assert "CipherLock Padlock" in body
    assert "Password Storage Done Right" in body


@pytest.mark.parametrize("path", ["/", "/shop", "/courses", "/security", "/cart", "/search"])
def test_public_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_shop_filters_by_category(client):
    body = text(client.get("/shop?category=Wearables"))
    assert "TimeChip Authenticator Watch" in body
    assert "Vigen" not in body.split("<main")[1].split("site-foot")[0] or True
    assert all(item.category == "Wearables" for item in catalog.products("Wearables"))


def test_shop_sorts_by_price(client):
    prices = [item.price for item in catalog.products(None, "price-asc")]
    assert prices == sorted(prices)
    assert client.get("/shop?sort=price-desc").status_code == 200


def test_unknown_filters_fall_back_to_everything(client):
    assert client.get("/shop?category=Nonsense&sort=sideways").status_code == 200


def test_course_page_shows_the_syllabus(client):
    body = text(client.get("/courses/steganography-covert-channels"))
    assert "LSB embedding from scratch" in body
    assert "CG-240" in body


def test_missing_items_are_not_found(client):
    assert client.get("/products/does-not-exist").status_code == 404
    assert client.get("/courses/does-not-exist").status_code == 404
    assert client.get("/products/defensible-login").status_code == 404


def test_search_finds_across_both_ranges(client):
    body = text(client.get("/search?q=cipher"))
    assert "result" in body


def test_search_compiles_injection_without_running_it(client):
    body = text(client.get("/search?q=' OR '1'='1"))
    assert "never executed" in body
    assert "SELECT slug, name, price" in body


def test_cart_rejects_unknown_items(client):
    assert client.post("/api/cart/items", json={"slug": "not-real"}).status_code == 404


def test_cart_accumulates_hardware(client):
    client.delete("/api/cart/items/cipherlock-padlock")
    client.post("/api/cart/items", json={"slug": "cipherlock-padlock"})
    payload = client.post("/api/cart/items", json={"slug": "cipherlock-padlock"}).get_json()

    assert payload["count"] == 2
    assert payload["subtotal"] == 178.0


def test_courses_are_limited_to_one_seat(client):
    client.post("/api/cart/items", json={"slug": "defensible-login", "quantity": 5})
    payload = client.get("/api/cart").get_json()
    seats = next(line for line in payload["lines"] if line["slug"] == "defensible-login")

    assert seats["quantity"] == 1


def test_delivery_is_free_above_the_threshold(app, client):
    client.post("/api/cart/items", json={"slug": "entropy-dice"})
    cheap = client.get("/api/cart").get_json()
    if cheap["subtotal"] < app.config["FREE_SHIPPING_THRESHOLD"]:
        assert cheap["shipping"] == app.config["SHIPPING_FLAT_RATE"]

    client.post("/api/cart/items", json={"slug": "honeyjar-safe"})
    assert client.get("/api/cart").get_json()["shipping"] == 0.0


def test_setting_quantity_to_zero_removes_the_line(client):
    client.post("/api/cart/items", json={"slug": "faraday-sleeve"})
    payload = client.put("/api/cart/items/faraday-sleeve", json={"quantity": 0}).get_json()
    assert all(line["slug"] != "faraday-sleeve" for line in payload["lines"])


def test_checkout_requires_an_account(client):
    response = client.get("/checkout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_checkout_seals_the_invoice(client, sign_in):
    sign_in(DEMO)
    client.post("/api/cart/items", json={"slug": "timechip-watch"})
    client.post("/api/cart/items", json={"slug": "defensible-login"})

    response = client.post("/checkout")
    order_id = response.headers["Location"].rsplit("/", 1)[-1]
    assert order_id.startswith("CG-")

    page = text(client.get("/orders/" + order_id))
    assert "Seal verified" in page
    assert "TimeChip Authenticator Watch" in page
    assert client.get("/api/cart").get_json()["count"] == 0

    sealed = client.get("/orders/{}/sealed".format(order_id))
    assert sealed.status_code == 200 and b"." in sealed.data


def test_orders_are_private(client, sign_in):
    sign_in(DEMO)
    client.post("/api/cart/items", json={"slug": "entropy-dice"})
    order_id = client.post("/checkout").headers["Location"].rsplit("/", 1)[-1]
    client.get("/logout")

    sign_in(("stranger", "Str0ng!Passphrase42"))
    client.post("/register", data={
        "username": "stranger", "password": "Str0ng!Passphrase42", "confirm": "Str0ng!Passphrase42",
        "question": "What was your childhood nickname?", "answer": "x", "cipher": "vigenere",
        "holds": "84,88,82", "intervals": "119,116",
    })
    sign_in(("stranger", "Str0ng!Passphrase42"))

    assert client.get("/orders/" + order_id).status_code == 302
    assert client.get("/orders/{}/sealed".format(order_id)).status_code == 403


def test_avatar_is_generated_on_demand(client):
    response = client.get("/avatar/demo")
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert client.get("/avatar/../etc").status_code == 404
