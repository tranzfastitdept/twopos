import anvil
import anvil.tables
import anvil.server
from anvil.tables import app_tables
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .catalog import PRODUCTS, SHOPS

try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)


def _default_shop():
    setting = app_tables.app_settings.get(key="default_shop")
    if setting is None:
        return None
    slug = setting["value"]
    if not slug:
        return None
    if not isinstance(slug, string_types) or slug not in PRODUCTS:
        raise ValueError("Set app_settings.default_shop to a configured shop slug or leave it blank.")
    return slug


def _shop_row(slug):
    if not isinstance(slug, string_types) or slug not in PRODUCTS:
        raise ValueError("Unknown register.")
    default = _default_shop()
    if default is not None and slug != default:
        raise ValueError("This deployment is configured for a different register.")
    row = app_tables.shops.get(slug=slug)
    if row is None:
        raise RuntimeError("Shop records are not initialized. Reload the register to initialize data.")
    return row


def _decimal(value, label):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("{} must be a valid amount.".format(label))
    if not amount.is_finite() or amount < 0:
        raise ValueError("{} must be a non-negative amount.".format(label))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _number(value):
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _seed_rows():
    for shop_data in SHOPS:
        shop = app_tables.shops.get(slug=shop_data["slug"])
        if shop is None:
            shop = app_tables.shops.add_row(**shop_data)
        for product_data in PRODUCTS[shop_data["slug"]]:
            product = app_tables.products.get(
                shop=shop,
                product_id=product_data["product_id"],
            )
            if product is None:
                app_tables.products.add_row(shop=shop, **product_data)
    if app_tables.app_settings.get(key="default_shop") is None:
        app_tables.app_settings.add_row(key="default_shop", value="")


@anvil.tables.in_transaction
def _ensure_seeded():
    _seed_rows()


@anvil.server.callable
def get_initial_data():
    _ensure_seeded()
    default = _default_shop()
    shops = SHOPS if default is None else [shop for shop in SHOPS if shop["slug"] == default]
    return {
        "default_shop": default,
        "shops": [
            {
                "slug": shop["slug"],
                "name": shop["name"],
                "logo": shop["logo"],
                "receipt_header": shop["receipt_header"],
            }
            for shop in shops
        ],
    }


@anvil.server.callable
def get_products_by_shop(shop_slug):
    shop = _shop_row(shop_slug)
    rows = app_tables.products.search(shop=shop)
    rows = sorted(rows, key=lambda product: product["sort_order"])
    return [
        {
            "product_id": product["product_id"],
            "name": product["name"],
            "description": product["description"],
            "price": product["price"],
            "image": product["image"],
        }
        for product in rows
    ]


@anvil.server.callable
@anvil.tables.in_transaction
def submit_transaction(shop_slug, items, method, amount_paid):
    shop = _shop_row(shop_slug)
    if not isinstance(items, list) or not items:
        raise ValueError("Add at least one product before checkout.")
    if method not in ("Cash", "Digital"):
        raise ValueError("Choose Cash or Digital payment.")

    quantities = {}
    allowed_ids = {product["product_id"] for product in PRODUCTS[shop_slug]}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid item in basket.")
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        if not isinstance(product_id, string_types) or product_id not in allowed_ids:
            raise ValueError("This product is not part of this register.")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 99:
            raise ValueError("Product quantities must be between 1 and 99.")
        quantities[product_id] = quantities.get(product_id, 0) + quantity
        if quantities[product_id] > 99:
            raise ValueError("Maximum quantity per product is 99.")

    receipt_items = []
    total = Decimal("0.00")
    for product_id, quantity in quantities.items():
        product = app_tables.products.get(shop=shop, product_id=product_id)
        if product is None:
            raise ValueError("A product in this basket is no longer available.")
        unit_price = _decimal(product["price"], "Product price")
        line_total = unit_price * quantity
        total += line_total
        receipt_items.append({
            "product_id": product_id,
            "name": product["name"],
            "quantity": quantity,
            "unit_price": _number(unit_price),
            "line_total": _number(line_total),
        })

    paid = _decimal(amount_paid, "Amount received") if method == "Cash" else total
    if method == "Cash" and paid < total:
        raise ValueError("Amount received is less than the total.")
    change = paid - total
    timestamp = datetime.now()
    app_tables.transactions.add_row(
        shop=shop,
        timestamp=timestamp,
        items_json=receipt_items,
        total_amount=_number(total),
        payment_method=method,
        amount_paid=_number(paid),
        change_given=_number(change),
    )
    return {
        "timestamp": timestamp,
        "items": receipt_items,
        "total_amount": _number(total),
        "payment_method": method,
        "amount_paid": _number(paid),
        "change_given": _number(change),
    }


@anvil.server.callable
def get_shop_analytics(shop_slug):
    shop = _shop_row(shop_slug)
    transactions = sorted(
        app_tables.transactions.search(shop=shop),
        key=lambda row: row["timestamp"],
        reverse=True,
    )
    cash_sales = sum(
        (_decimal(row["total_amount"], "Transaction total") for row in transactions if row["payment_method"] == "Cash"),
        Decimal("0.00"),
    )
    digital_sales = sum(
        (_decimal(row["total_amount"], "Transaction total") for row in transactions if row["payment_method"] == "Digital"),
        Decimal("0.00"),
    )
    return {
        "order_count": len(transactions),
        "gross_sales": u"₱{:,.2f}".format(_number(cash_sales + digital_sales)),
        "cash_sales": u"₱{:,.2f}".format(_number(cash_sales)),
        "digital_sales": u"₱{:,.2f}".format(_number(digital_sales)),
        "transactions": [
            {
                "timestamp": row["timestamp"],
                "items": row["items_json"],
                "total_amount": row["total_amount"],
                "payment_method": row["payment_method"],
                "amount_paid": row["amount_paid"],
                "change_given": row["change_given"],
            }
            for row in transactions
        ],
    }
