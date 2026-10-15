import csv
import json
import os
import threading
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, url_for


ROOT = Path(__file__).resolve().parent
SHOP_SLUGS = ("workstation_specialty_coffee_pos", "keecoo_pos")
CSV_LOCK = threading.RLock()
app = Flask(__name__)
app.json.ensure_ascii = False
app.config["POS_SHOP_SLUG"] = os.environ.get("POS_SHOP_SLUG") or None
if app.config["POS_SHOP_SLUG"] not in (None, *SHOP_SLUGS):
    raise RuntimeError("POS_SHOP_SLUG must be one of the configured shop slugs.")


def shop_config(slug):
    dedicated_shop = app.config["POS_SHOP_SLUG"]
    if slug not in SHOP_SLUGS or (dedicated_shop and slug != dedicated_shop):
        abort(404)
    folder = ROOT / slug
    with (folder / "data" / "shops.csv").open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    if len(rows) != 1:
        raise RuntimeError("Expected exactly one shop configuration row for " + slug)
    return folder, rows[0]


def read_products(folder):
    with (folder / "data" / "products.csv").open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def read_transactions(folder):
    with (folder / "data" / "transactions.csv").open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def to_cents(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Enter a valid amount.")
    if not amount.is_finite() or amount < 0:
        raise ValueError("Amount must be a non-negative number.")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def money(cents):
    return "{:.2f}".format(cents / 100)


def transaction_response(row):
    return {
        "id": row["txn_id"],
        "timestamp": row["timestamp"],
        "items": json.loads(row["items_json"]),
        "total_amount": row["total_amount"],
        "payment_method": row["payment_method"],
        "amount_paid": row["amount_paid"],
        "change_given": row["change_given"],
    }


@app.get("/")
def home():
    dedicated_shop = app.config["POS_SHOP_SLUG"]
    if dedicated_shop:
        return redirect(url_for("pos", slug=dedicated_shop))
    shops = [shop_config(slug)[1] for slug in SHOP_SLUGS]
    return render_template("home.html", shops=shops)


@app.get("/<slug>/")
def pos(slug):
    _, shop = shop_config(slug)
    return render_template("pos.html", shop=shop, dedicated=bool(app.config["POS_SHOP_SLUG"]))


@app.get("/<slug>/analytics")
def analytics(slug):
    _, shop = shop_config(slug)
    return render_template("analytics.html", shop=shop, dedicated=bool(app.config["POS_SHOP_SLUG"]))


@app.get("/assets/<slug>/<path:filename>")
def product_asset(slug, filename):
    folder, _ = shop_config(slug)
    return send_from_directory(folder / "assets", filename)


@app.get("/<slug>/api/products")
def products_api(slug):
    folder, _ = shop_config(slug)
    return jsonify([
        {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "price": row["price"],
            "image": row["image"],
        }
        for row in read_products(folder)
    ])


@app.post("/<slug>/api/checkout")
def checkout_api(slug):
    folder, _ = shop_config(slug)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        return jsonify(error="Your basket is empty or invalid."), 400

    products = {row["id"]: row for row in read_products(folder)}
    quantities = {}
    for item in payload["items"]:
        if not isinstance(item, dict):
            return jsonify(error="Invalid item in basket."), 400
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        if product_id not in products or isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 99:
            return jsonify(error="Invalid product or quantity in basket."), 400
        quantities[product_id] = quantities.get(product_id, 0) + quantity
        if quantities[product_id] > 99:
            return jsonify(error="Maximum quantity per product is 99."), 400
    if not quantities:
        return jsonify(error="Add at least one product before checkout."), 400

    items = []
    total_cents = 0
    try:
        for product_id, quantity in quantities.items():
            product = products[product_id]
            unit_cents = to_cents(product["price"])
            line_cents = unit_cents * quantity
            total_cents += line_cents
            items.append({
                "product_id": product_id,
                "name": product["name"],
                "quantity": quantity,
                "unit_price": money(unit_cents),
                "line_total": money(line_cents),
                "image": product["image"],
            })
        method = payload.get("payment_method")
        if method not in ("Cash", "Digital"):
            raise ValueError("Choose Cash or Digital payment.")
        paid_cents = to_cents(payload.get("amount_paid")) if method == "Cash" else total_cents
        if method == "Cash" and paid_cents < total_cents:
            raise ValueError("Amount received is less than the total.")
    except ValueError as error:
        return jsonify(error=str(error)), 400

    row = {
        "txn_id": uuid.uuid4().hex,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "items_json": json.dumps(items, ensure_ascii=False),
        "total_amount": money(total_cents),
        "payment_method": method,
        "amount_paid": money(paid_cents),
        "change_given": money(paid_cents - total_cents),
    }
    with CSV_LOCK:
        with (folder / "data" / "transactions.csv").open("a", encoding="utf-8", newline="") as file:
            csv.DictWriter(file, fieldnames=row.keys()).writerow(row)
    return jsonify(transaction_response(row)), 201


@app.get("/<slug>/api/analytics")
def analytics_api(slug):
    folder, _ = shop_config(slug)
    rows = read_transactions(folder)
    cash_total = sum(to_cents(row["total_amount"]) for row in rows if row["payment_method"] == "Cash")
    digital_total = sum(to_cents(row["total_amount"]) for row in rows if row["payment_method"] == "Digital")
    transactions = [transaction_response(row) for row in reversed(rows)]
    return jsonify({
        "order_count": len(rows),
        "gross_sales": money(cash_total + digital_total),
        "cash_sales": money(cash_total),
        "digital_sales": money(digital_total),
        "transactions": transactions,
    })


@app.get("/<slug>/api/transactions/<txn_id>")
def transaction_api(slug, txn_id):
    folder, _ = shop_config(slug)
    for row in read_transactions(folder):
        if row["txn_id"] == txn_id:
            return jsonify(transaction_response(row))
    abort(404)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("POS_PORT", "5000")), debug=False)
