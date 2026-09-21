from flask import Blueprint, jsonify, request

from cipherguard import cart, crypto

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.get("/cart")
def read_cart():
    return jsonify(cart.as_payload())


@bp.post("/cart/items")
def add_item():
    payload = request.get_json(silent=True) or {}
    item = cart.add(payload.get("slug"), _quantity(payload.get("quantity"), 1))
    if item is None:
        return jsonify({"error": "unknown item"}), 404
    return jsonify({"added": item.name, **cart.as_payload()})


@bp.put("/cart/items/<slug>")
def update_item(slug):
    payload = request.get_json(silent=True) or {}
    item = cart.set_quantity(slug, _quantity(payload.get("quantity"), 0))
    if item is None:
        return jsonify({"error": "unknown item"}), 404
    return jsonify(cart.as_payload())


@bp.delete("/cart/items/<slug>")
def remove_item(slug):
    cart.remove(slug)
    return jsonify(cart.as_payload())


@bp.post("/password-strength")
def password_strength():
    payload = request.get_json(silent=True) or {}
    return jsonify(crypto.evaluate_strength(payload.get("password", "")))


def _quantity(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback
