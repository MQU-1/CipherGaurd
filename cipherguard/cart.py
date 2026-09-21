from flask import current_app, session, url_for

from cipherguard import catalog

SESSION_KEY = "cart"
MAX_QUANTITY = 10


def contents():
    stored = session.get(SESSION_KEY)
    return dict(stored) if isinstance(stored, dict) else {}


def count():
    return sum(contents().values())


def add(slug, quantity=1):
    item = catalog.find(slug)
    if item is None:
        return None
    basket = contents()
    basket[slug] = _bounded(item, basket.get(slug, 0) + max(1, quantity))
    _persist(basket)
    return item


def set_quantity(slug, quantity):
    item = catalog.find(slug)
    if item is None:
        return None
    basket = contents()
    if quantity <= 0:
        basket.pop(slug, None)
    else:
        basket[slug] = _bounded(item, quantity)
    _persist(basket)
    return item


def remove(slug):
    basket = contents()
    basket.pop(slug, None)
    _persist(basket)


def clear():
    _persist({})


def lines():
    rows = []
    for slug, quantity in contents().items():
        item = catalog.find(slug)
        if item is not None and quantity > 0:
            rows.append({"item": item, "quantity": quantity, "subtotal": round(item.price * quantity, 2)})
    rows.sort(key=lambda row: (row["item"].kind, row["item"].name))
    return rows


def summary():
    rows = lines()
    subtotal = round(sum(row["subtotal"] for row in rows), 2)
    shippable = any(row["item"].kind == catalog.PRODUCT for row in rows)
    threshold = current_app.config["FREE_SHIPPING_THRESHOLD"]
    shipping = 0.0
    if shippable and subtotal < threshold:
        shipping = current_app.config["SHIPPING_FLAT_RATE"]
    return {
        "lines": rows,
        "count": sum(row["quantity"] for row in rows),
        "subtotal": subtotal,
        "shipping": shipping,
        "total": round(subtotal + shipping, 2),
        "shippable": shippable,
        "free_shipping_gap": round(max(0.0, threshold - subtotal), 2) if shippable else 0.0,
    }


def as_payload():
    totals = summary()
    return {
        "count": totals["count"],
        "subtotal": totals["subtotal"],
        "shipping": totals["shipping"],
        "total": totals["total"],
        "freeShippingGap": totals["free_shipping_gap"],
        "lines": [
            {
                "slug": row["item"].slug,
                "name": row["item"].name,
                "kind": row["item"].kind,
                "price": row["item"].price,
                "quantity": row["quantity"],
                "subtotal": row["subtotal"],
                "url": _item_url(row["item"]),
            }
            for row in totals["lines"]
        ],
    }


def _item_url(item):
    endpoint = "storefront.course" if item.kind == catalog.COURSE else "storefront.product"
    return url_for(endpoint, slug=item.slug)


def _bounded(item, quantity):
    if item.kind == catalog.COURSE:
        return 1
    return max(1, min(quantity, MAX_QUANTITY))


def _persist(basket):
    session[SESSION_KEY] = basket
    session.modified = True
