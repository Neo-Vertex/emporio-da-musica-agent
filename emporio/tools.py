"""Tools the agent can call. Every calculation (promotion, PIX discount, installments, dates) happens here,
in code, so the model never has to do math or make up a price."""
import csv
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
LOGS = Path(__file__).resolve().parent.parent / "logs"

# Campo Grande/MS is UTC-4 all year (no daylight saving since 2019); avoids depending on tzdata on Windows
TZ = timezone(timedelta(hours=-4))


def today():
    return datetime.now(TZ).date()


def _load(name):
    with open(DATA / f"desafio_tecnico_ai_eng - {name}.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _norm(text):
    """lowercase, no accents, no spaces/hyphens: 'Violão GD-20' -> 'violaogd20'."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[\s\-_/'.]", "", text.lower())


CATEGORIES = {c["category_id"]: c["name"] for c in _load("categories")}
PRODUCTS = _load("products")
CUSTOMERS = {c["customer_id"]: c for c in _load("customers")}
ORDERS = {o["order_id"]: o for o in _load("orders")}
ORDER_ITEMS = _load("order_items")
ACTIVE_PROMOS = {p["product_id"]: p for p in _load("promotions") if p["is_active"] == "1"}
PRODUCT_BY_ID = {p["product_id"]: p for p in PRODUCTS}

AVAILABILITY = {"discontinued": "discontinued", "coming_soon": "coming soon (not on sale yet)"}
ORDER_STATUS = {
    "pending": "awaiting payment confirmation",
    "confirmed": "payment confirmed, being prepared",
    "shipped": "shipped",
    "delivered": "delivered",
    "cancelled": "cancelled",
}


def max_installments(price):
    """Max interest-free installments (store manual §3.1): up to 3x with installment >= R$50,
    4-6x with installment >= R$80, 7-12x with installment >= R$100."""
    for n in range(12, 0, -1):
        minimum = 100 if n >= 7 else 80 if n >= 4 else 50
        if price / n >= minimum:
            return n
    return 1


def _availability(p):
    if p["status"] in AVAILABILITY:
        return AVAILABILITY[p["status"]]
    stock = int(p["stock_quantity"])
    return f"in stock ({stock} units)" if stock > 0 else "out of stock"


def _in_stock(p):
    return _availability(p).startswith("in stock")


def _product_view(p):
    price = float(p["price_brl"])
    view = {
        "id": int(p["product_id"]),
        "name": p["name"],
        "category": CATEGORIES.get(p["category_id"]),
        "availability": _availability(p),
        "list_price": round(price, 2),
        "description": p["description"],
        "specs": json.loads(p["specs"] or "{}"),
    }
    promo = ACTIVE_PROMOS.get(p["product_id"])
    if promo:
        final = round(price * (1 - int(promo["discount_percent"]) / 100), 2)
        view["active_promotion"] = {"name": promo["description"], "discount_percent": int(promo["discount_percent"]),
                                    "promo_price": final}
        view["pix_price"] = final  # §6.2: PIX discount does not stack with promotions
    else:
        final = price
        view["pix_price"] = round(price * 0.95, 2)
    n = max_installments(final)
    view["max_interest_free_installments"] = f"{n}x of R$ {final / n:.2f}"
    return view


def search_products(query=None, category=None, min_price=None, max_price=None, promotions_only=False):
    cat_ids = {cid for cid, name in CATEGORIES.items() if category and _norm(category) in _norm(name)}
    words = [_norm(w) for w in (query or "").split() if w.strip()]
    found = []
    for p in PRODUCTS:
        price = float(p["price_brl"])
        haystack = _norm(p["name"] + p["description"] + CATEGORIES.get(p["category_id"], ""))
        if category and p["category_id"] not in cat_ids:
            continue
        if any(w not in haystack for w in words):
            continue
        if (min_price is not None and price < min_price) or (max_price is not None and price > max_price):
            continue
        if promotions_only and p["product_id"] not in ACTIVE_PROMOS:
            continue
        found.append(p)
    found.sort(key=lambda p: (not _in_stock(p), float(p["price_brl"])))  # available first, then by price
    result = {"total_found": len(found), "products": [_product_view(p) for p in found[:20]]}
    # §7.3: when the requested item is unavailable, return alternatives right away
    # (asking for this only in the prompt was not enough during testing)
    if found and words and not any(_in_stock(p) for p in found):
        ref_price = float(found[0]["price_brl"])
        similar = sorted((p for p in PRODUCTS if p["category_id"] == found[0]["category_id"] and _in_stock(p)),
                         key=lambda p: abs(float(p["price_brl"]) - ref_price))
        result["available_alternatives"] = [_product_view(p) for p in similar[:3]]
    return result


def simulate_installments(amount):
    n = max_installments(amount)
    return {"amount": amount, "max_interest_free_installments": n, "installment_value": round(amount / n, 2)}


def get_order_status(order_id, email_or_phone):
    if not email_or_phone.strip():
        return {"error": "Ask the customer for the email or phone number on file before looking up the order."}
    # LGPD: a missing order and a wrong email/phone get the SAME answer, so order numbers can't be enumerated
    denied = {"error": "No order found with this number for this email/phone."}
    order = ORDERS.get(str(order_id).strip().lstrip("#"))
    if not order:
        return denied
    customer = CUSTOMERS[order["customer_id"]]
    digits = re.sub(r"\D", "", email_or_phone)
    phone_ok = len(digits) >= 8 and re.sub(r"\D", "", customer["phone"]).endswith(digits[-8:])
    if _norm(email_or_phone) != _norm(customer["email"]) and not phone_ok:
        return denied
    extra = {}
    if order["estimated_delivery"]:
        days = (today() - date.fromisoformat(order["estimated_delivery"])).days
        if order["status"] == "delivered":
            # the data has no actual delivery date: the estimated date is used as the receipt date
            extra["days_since_delivery"] = days
        elif days > 0:
            extra["days_late"] = days
    items = [{"product": PRODUCT_BY_ID[i["product_id"]]["name"], "quantity": int(i["quantity"])}
             for i in ORDER_ITEMS if i["order_id"] == order["order_id"]]
    return extra | {
        "order_id": int(order["order_id"]),
        "customer_first_name": customer["name"].split()[0],
        "order_date": order["order_date"],
        "status": ORDER_STATUS.get(order["status"], order["status"]),
        "items": items,
        "total": float(order["total_brl"]),
        "payment_method": order["payment_method"],
        "tracking_code": order["tracking_code"] or None,
        "estimated_delivery": order["estimated_delivery"] or None,
        "notes": order["notes"] or None,
    }


def handoff_to_human(reason, summary, customer_contact=None):
    # ponytail: a JSONL file stands in for the ticket queue; in production this would be a CRM/helpdesk ticket
    LOGS.mkdir(exist_ok=True)
    ticket = {"at": datetime.now(TZ).isoformat(timespec="seconds"), "reason": reason,
              "summary": summary, "contact": customer_contact}
    with open(LOGS / "handoffs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(ticket, ensure_ascii=False) + "\n")
    return {"ok": True, "response_time": "within 24 business hours"}


TOOLS = {f.__name__: f for f in (search_products, simulate_installments, get_order_status, handoff_to_human)}

SCHEMAS = [
    {"type": "function", "function": {
        "name": "search_products",
        "description": "Searches the store catalog. Use it for ANY question about a product, price, stock, promotion "
                       "or recommendation. Returns list price, active promotion, PIX price and installments already calculated.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Brand, model or feature (e.g. 'Takamine GD20', 'nylon', 'elétrico'). Omit to list a category."},
            "category": {"type": "string", "enum": sorted(CATEGORIES.values())},
            "min_price": {"type": "number"},
            "max_price": {"type": "number"},
            "promotions_only": {"type": "boolean", "description": "true to list only items with an active promotion"},
        }}}},
    {"type": "function", "function": {
        "name": "simulate_installments",
        "description": "Calculates how many interest-free credit card installments an amount allows (minimum installment "
                       "rules from the manual). ALWAYS use it when the customer asks about installments; never calculate them yourself.",
        "parameters": {"type": "object", "required": ["amount"], "properties": {"amount": {"type": "number"}}}}},
    {"type": "function", "function": {
        "name": "get_order_status",
        "description": "Gets the status, items and tracking of an order. Requires the order number AND the customer's email "
                       "or phone to confirm identity (LGPD). Ask the customer if either is missing.",
        "parameters": {"type": "object", "required": ["order_id", "email_or_phone"], "properties": {
            "order_id": {"type": "string"},
            "email_or_phone": {"type": "string"},
        }}}},
    {"type": "function", "function": {
        "name": "handoff_to_human",
        "description": "Hands the case over to the human team: complaint, return/exchange to be formalized, late order, "
                       "special shipping quote or anything the agent cannot solve.",
        "parameters": {"type": "object", "required": ["reason", "summary"], "properties": {
            "reason": {"type": "string", "enum": ["complaint", "return_exchange", "late_delivery", "shipping_quote", "other"]},
            "summary": {"type": "string", "description": "Case summary for the human agent, including the order number if any."},
            "customer_contact": {"type": "string"},
        }}}},
]


if __name__ == "__main__":  # self-check: python -m emporio.tools
    assert max_installments(2199) == 12 and max_installments(400) == 5 and max_installments(120) == 2
    assert simulate_installments(600)["max_interest_free_installments"] == 6  # real LLM mistake: it had answered 12x
    gd20 = search_products("takamine gd20")["products"][0]
    assert gd20["list_price"] == 2199 and "active_promotion" not in gd20 and gd20["pix_price"] == 2089.05
    crafter = search_products("crafter ht-100")["products"][0]  # active 18% promotion: PIX does not stack
    assert crafter["active_promotion"]["promo_price"] == crafter["pix_price"] == 1967.18
    assert len(search_products("Giannini GF-3D")["available_alternatives"]) == 3  # out of stock -> 3 suggestions
    guitars = search_products(category="Violões", max_price=1000)["products"]
    assert guitars and all(g["list_price"] <= 1000 for g in guitars)
    assert get_order_status("8", "someone@else.com") == get_order_status("999", "someone@else.com")
    assert get_order_status("8", "anacarol.ferreira@coldmail.com")["status"] == "shipped"
    assert get_order_status("8", "(67) 99654-7821")["tracking_code"] == "BRJL5544332BR"
    print("ok")
