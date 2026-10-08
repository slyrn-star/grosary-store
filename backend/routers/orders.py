import secrets
from fastapi import APIRouter, Depends, HTTPException
from pymongo import ReturnDocument

import database as d
from schemas import OrderIn
from security import get_current_user
from utils import now, oid, ser, log_activity

router = APIRouter(tags=["Orders"])


@router.post("/orders", status_code=201)
def place_order(body: OrderIn, user: dict = Depends(get_current_user)):
    cart = d.carts.find_one({"user_id": user["_id"]})
    if not cart or not cart["items"]:
        raise HTTPException(400, "Your cart is empty")

    reserved, lines, subtotal = [], [], 0
    for it in cart["items"]:
        # Take stock only if enough is left (atomic, so two buyers can't oversell)
        p = d.products.find_one_and_update(
            {"_id": it["product_id"], "is_active": True, "stock": {"$gte": it["qty"]}},
            {"$inc": {"stock": -it["qty"]}},
            return_document=ReturnDocument.BEFORE)
        if not p:
            for pid, q in reserved:  # put back what we already took
                d.products.update_one({"_id": pid}, {"$inc": {"stock": q}})
            raise HTTPException(409, "Some items are out of stock or unavailable. "
                                     "Please review your cart.")
        reserved.append((it["product_id"], it["qty"]))
        line_total = p["price"] * it["qty"]
        subtotal += line_total
        lines.append({"product_id": p["_id"], "name": p["name"], "unit": p["unit"],
                      "price": p["price"], "qty": it["qty"], "subtotal": line_total})

    company = d.company.find_one({}) or {}
    delivery_fee = company.get("delivery_fee", 0)
    order = {
        "order_number": "FG-" + secrets.token_hex(3).upper(),
        "user_id": user["_id"], "customer_name": user["name"], "customer_email": user["email"],
        "items": lines, "subtotal": subtotal, "delivery_fee": delivery_fee,
        "total": subtotal + delivery_fee,
        "payment_method": body.payment_method, "payment_status": "pending",
        "delivery_address": body.delivery_address, "phone": body.phone,
        "status": "placed", "created_at": now(), "updated_at": now(),
    }
    order["_id"] = d.orders.insert_one(order).inserted_id

    d.payments.insert_one({
        "order_id": order["_id"], "order_number": order["order_number"],
        "user_id": user["_id"], "method": body.payment_method,
        "amount": order["total"], "status": "pending",   # COD: becomes "paid" on delivery
        "created_at": now(), "paid_at": None})

    d.carts.update_one({"user_id": user["_id"]}, {"$set": {"items": [], "updated_at": now()}})
    log_activity(user["_id"], "order_placed",
                 {"order_number": order["order_number"], "total": order["total"],
                  "items": [{"name": l["name"], "qty": l["qty"]} for l in lines]})
    return ser(order)


@router.get("/orders/my")
def my_orders(user: dict = Depends(get_current_user)):
    return ser(list(d.orders.find({"user_id": user["_id"]}).sort("created_at", -1)))


@router.get("/orders/{order_id}")
def get_order(order_id: str, user: dict = Depends(get_current_user)):
    order = d.orders.find_one({"_id": oid(order_id)})
    if not order or (order["user_id"] != user["_id"] and user["role"] != "admin"):
        raise HTTPException(404, "Order not found")
    return ser(order)


@router.get("/payments/my")
def my_payments(user: dict = Depends(get_current_user)):
    return ser(list(d.payments.find({"user_id": user["_id"]}).sort("created_at", -1)))