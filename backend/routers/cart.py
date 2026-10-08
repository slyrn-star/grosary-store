from fastapi import APIRouter, Depends, HTTPException

import database as d
from schemas import CartChangeIn
from security import get_current_user
from utils import now, oid, log_activity

router = APIRouter(prefix="/cart", tags=["Cart"])


def build_cart(user_id):
    cart = d.carts.find_one({"user_id": user_id}) or {"items": []}
    ids = [i["product_id"] for i in cart["items"]]
    prods = {p["_id"]: p for p in d.products.find({"_id": {"$in": ids}})}
    items, total = [], 0
    for i in cart["items"]:
        p = prods.get(i["product_id"])
        if not p or not p.get("is_active", True):
            continue
        sub = p["price"] * i["qty"]
        total += sub
        items.append({"product_id": str(p["_id"]), "name": p["name"],
                      "price": p["price"], "unit": p["unit"], "image": p.get("image", ""),
                      "emoji": p.get("emoji", ""), "stock": p["stock"],
                      "qty": i["qty"], "subtotal": sub})
    return {"items": items, "item_count": sum(i["qty"] for i in items), "total": total}


@router.get("")
def get_cart(user: dict = Depends(get_current_user)):
    return build_cart(user["_id"])


@router.post("/items")
def change_item(body: CartChangeIn, user: dict = Depends(get_current_user)):
    pid = oid(body.product_id)
    product = d.products.find_one({"_id": pid, "is_active": True})
    if not product:
        raise HTTPException(404, "Product not found")

    cart = d.carts.find_one({"user_id": user["_id"]}) or {"items": []}
    qty_map = {i["product_id"]: i["qty"] for i in cart["items"]}
    new_qty = qty_map.get(pid, 0) + body.change

    if new_qty > product["stock"]:
        raise HTTPException(400, f"Only {product['stock']} {product['name']} in stock")
    if new_qty <= 0:
        qty_map.pop(pid, None)
    else:
        qty_map[pid] = new_qty

    d.carts.update_one(
        {"user_id": user["_id"]},
        {"$set": {"items": [{"product_id": k, "qty": v} for k, v in qty_map.items()],
                  "updated_at": now()}},
        upsert=True)
    log_activity(user["_id"], "cart_add" if body.change > 0 else "cart_remove",
                 {"product_id": str(pid), "name": product["name"],
                  "change": body.change, "new_qty": max(new_qty, 0)})
    return build_cart(user["_id"])


@router.delete("/items/{product_id}")
def remove_item(product_id: str, user: dict = Depends(get_current_user)):
    pid = oid(product_id)
    d.carts.update_one({"user_id": user["_id"]},
                       {"$pull": {"items": {"product_id": pid}}, "$set": {"updated_at": now()}})
    log_activity(user["_id"], "cart_remove", {"product_id": str(pid), "removed_all": True})
    return build_cart(user["_id"])


@router.delete("")
def clear_cart(user: dict = Depends(get_current_user)):
    d.carts.update_one({"user_id": user["_id"]}, {"$set": {"items": [], "updated_at": now()}})
    log_activity(user["_id"], "cart_clear")
    return build_cart(user["_id"])