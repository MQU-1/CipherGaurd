import secrets
from datetime import datetime, timezone

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, send_file, url_for)

from cipherguard import auth, cart, catalog, crypto, monitoring, store

bp = Blueprint("storefront", __name__)


@bp.get("/")
def home():
    return render_template(
        "storefront/home.html",
        products=catalog.featured_products(4),
        courses=catalog.featured_courses(3),
    )


@bp.get("/shop")
def shop():
    category = request.args.get("category")
    sort = request.args.get("sort", "featured")
    if category not in catalog.CATEGORIES:
        category = None
    if sort not in dict(catalog.SORT_OPTIONS):
        sort = "featured"
    return render_template(
        "storefront/shop.html",
        items=catalog.products(category, sort),
        category=category,
        sort=sort,
    )


@bp.get("/courses")
def courses():
    level = request.args.get("level")
    if level not in catalog.LEVELS:
        level = None
    return render_template("storefront/courses.html", items=catalog.courses(level), level=level)


@bp.get("/products/<slug>")
def product(slug):
    item = catalog.find(slug)
    if item is None or item.kind != catalog.PRODUCT:
        abort(404)
    return render_template("storefront/product.html", item=item, suggestions=catalog.related(item))


@bp.get("/courses/<slug>")
def course(slug):
    item = catalog.find(slug)
    if item is None or item.kind != catalog.COURSE:
        abort(404)
    return render_template("storefront/course.html", item=item, suggestions=catalog.related(item))


@bp.get("/search")
def search():
    term = request.args.get("q", "").strip()
    actor = auth.current_username() or "anonymous"
    if not term:
        return render_template("storefront/search.html", results=[], term="", statement=None)

    results = catalog.search(term)
    statement = monitoring.compile_query(term)
    hits = monitoring.scan(request.args)
    if hits:
        store.record_event("search", actor, "sqli",
                           "{} | compiled: {}".format(monitoring.summarise(hits), statement))
    else:
        store.record_event("search", actor, "ok", "'{}' returned {} result(s)".format(term, len(results)))
    return render_template("storefront/search.html", results=results, term=term, statement=statement)


@bp.get("/security")
def security():
    return render_template("storefront/security.html")


@bp.get("/cart")
def basket():
    return render_template("storefront/cart.html", totals=cart.summary())


@bp.route("/checkout", methods=["GET", "POST"])
@auth.login_required
def checkout():
    totals = cart.summary()
    if not totals["lines"]:
        flash("Your bag is empty.", "notice")
        return redirect(url_for("storefront.shop"))

    if request.method == "POST":
        invoice = _build_invoice(totals)
        invoice["sealed"] = crypto.seal(invoice, current_app.config["INVOICE_KEY"])
        store.add_invoice(invoice)
        store.record_event("checkout", invoice["user"], "success",
                           "order {} sealed and embedded, total {:.2f}".format(invoice["order_id"], invoice["total"]))
        cart.clear()
        flash("Order placed. The invoice is sealed inside the carrier image.", "success")
        return redirect(url_for("storefront.order", order_id=invoice["order_id"]))

    return render_template("storefront/checkout.html", totals=totals)


@bp.get("/orders")
@auth.login_required
def orders():
    return render_template("storefront/orders.html", orders=store.invoices_for(auth.current_username()))


@bp.get("/orders/<order_id>")
@auth.login_required
def order(order_id):
    invoice = _owned_invoice(order_id)
    if invoice is None:
        flash("You can only open your own orders.", "error")
        return redirect(url_for("storefront.orders"))
    intact = crypto.seal_matches(
        invoice.get("sealed"),
        current_app.config["INVOICE_KEY"],
        {"order_id": invoice.get("order_id"), "total": invoice.get("total")},
    )
    return render_template("storefront/order.html", invoice=invoice, intact=intact)


@bp.get("/orders/<order_id>/sealed")
@auth.login_required
def sealed_invoice(order_id):
    invoice = _owned_invoice(order_id)
    if invoice is None:
        abort(403)
    return invoice.get("sealed", ""), 200, {"Content-Type": "text/plain; charset=utf-8"}


@bp.get("/avatar/<username>")
def avatar(username):
    if not username.isalnum():
        abort(404)
    return send_file(auth.ensure_avatar(username), mimetype="image/png")


def _owned_invoice(order_id):
    invoice = store.find_invoice(order_id)
    if invoice is None:
        abort(404)
    if invoice.get("user") != auth.current_username() and not auth.is_admin():
        return None
    return invoice


def _build_invoice(totals):
    return {
        "order_id": "CG-{}".format(secrets.token_hex(3).upper()),
        "user": auth.current_username(),
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lines": [
            {
                "slug": row["item"].slug,
                "name": row["item"].name,
                "kind": row["item"].kind,
                "quantity": row["quantity"],
                "price": row["item"].price,
                "subtotal": row["subtotal"],
            }
            for row in totals["lines"]
        ],
        "subtotal": totals["subtotal"],
        "shipping": totals["shipping"],
        "total": totals["total"],
    }
