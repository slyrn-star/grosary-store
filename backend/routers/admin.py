from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import DuplicateKeyError

import database as d
from routers.cart import build_cart
from schemas import (ProductIn, ProductUpdate, StockIn, OrderStatusIn,
                     ActiveIn, CompanyIn)
from security import require_admin
from utils import now, oid, ser, log_activity

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------- dashboard ----------
@router.get("/dashboard")
def dashboard(admin: dict = Depends(require_admin)):
    rev = list(d.orders.aggregate([
        {"$match": {"status": "delivered"}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}]))
    return {
        "customers": d.users.count_documents({"role": "customer"}),
        "products": d.products.count_documents({"is_active": True}),
        "orders": d.orders.count_documents({}),
        "pending_orders": d.orders.count_documents({"status": {"$in": ["placed", "confirmed", "out_for_delivery"]}}),
        "delivered_revenue": rev[0]["total"] if rev else 0,
        "low_stock": ser(list(d.products.find({"is_active": True, "stock": {"$lte": 10}},
                                              {"name": 1, "stock": 1}))),
    }


# ---------- users + history ----------
@router.get("/users")
def list_users(limit: int = Query(50, le=200), skip: int = 0,
               admin: dict = Depends(require_admin)):
    return ser(list(d.users.find().sort("created_at", -1).skip(skip).limit(limit)))


@router.get("/users/{user_id}/overview")
def user_overview(user_id: str, admin: dict = Depends(require_admin)):
    uid = oid(user_id)
    user = d.users.find_one({"_id": uid})
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "user": ser(user),
        "current_cart": build_cart(uid),
        "login_history": ser(list(d.login_history.find({"user_id": uid}).sort("created_at", -1).limit(100))),
        "activity": ser(list(d.activity_log.find({"user_id": uid}).sort("created_at", -1).limit(100))),
        "orders": ser(list(d.orders.find({"user_id": uid}).sort("created_at", -1))),
        "payments": ser(list(d.payments.find({"user_id": uid}).sort("created_at", -1))),
    }


@router.patch("/users/{user_id}/active")
def set_user_active(user_id: str, body: ActiveIn, admin: dict = Depends(require_admin)):
    uid = oid(user_id)
    if uid == admin["_id"]:
        raise HTTPException(400, "You cannot disable your own account")
    res = d.users.update_one({"_id": uid}, {"$set": {"is_active": body.is_active}})
    if not res.matched_count:
        raise HTTPException(404, "User not found")
    if not body.is_active:
        d.sessions.update_many({"user_id": uid}, {"$set": {"revoked": True}})
    return {"is_active": body.is_active}


@router.get("/login-history")
def login_history(email: Optional[str] = None, event: Optional[str] = None,
                  success: Optional[bool] = None, limit: int = Query(100, le=500),
                  skip: int = 0, admin: dict = Depends(require_admin)):
    q = {}
    if email:
        q["email"] = email.lower()
    if event:
        q["event"] = event
    if success is not None:
        q["success"] = success
    return ser(list(d.login_history.find(q).sort("created_at", -1).skip(skip).limit(limit)))


@router.get("/activity")
def activity(user_id: Optional[str] = None, action: Optional[str] = None,
             limit: int = Query(100, le=500), skip: int = 0,
             admin: dict = Depends(require_admin)):
    q = {}
    if user_id:
        q["user_id"] = oid(user_id)
    if action:
        q["action"] = action
    return ser(list(d.activity_log.find(q).sort("created_at", -1).skip(skip).limit(limit)))


# ---------- orders / payments ----------
@router.get("/orders")
def all_orders(status: Optional[str] = None, limit: int = Query(100, le=500),
               skip: int = 0, admin: dict = Depends(require_admin)):
    q = {"status": status} if status else {}
    return ser(list(d.orders.find(q).sort("created_at", -1).skip(skip).limit(limit)))


@router.patch("/orders/{order_id}/status")
def update_order_status(order_id: str, body: OrderStatusIn,
                        admin: dict = Depends(require_admin)):
    order = d.orders.find_one({"_id": oid(order_id)})
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] in ("delivered", "cancelled"):
        raise HTTPException(400, "This order is already closed")

    updates = {"status": body.status, "updated_at": now()}
    if body.status == "delivered":           # cash collected on delivery
        updates["payment_status"] = "paid"
        d.payments.update_one({"order_id": order["_id"]},
                              {"$set": {"status": "paid", "paid_at": now()}})
    elif body.status == "cancelled":         # put stock back
        for l in order["items"]:
            d.products.update_one({"_id": l["product_id"]}, {"$inc": {"stock": l["qty"]}})
        updates["payment_status"] = "cancelled"
        d.payments.update_one({"order_id": order["_id"]}, {"$set": {"status": "cancelled"}})

    d.orders.update_one({"_id": order["_id"]}, {"$set": updates})
    log_activity(order["user_id"], f"order_{body.status}",
                 {"order_number": order["order_number"], "by_admin": admin["email"]})
    return ser(d.orders.find_one({"_id": order["_id"]}))


@router.get("/payments")
def all_payments(limit: int = Query(100, le=500), skip: int = 0,
                 admin: dict = Depends(require_admin)):
    return ser(list(d.payments.find().sort("created_at", -1).skip(skip).limit(limit)))


# ---------- products / stock ----------
@router.get("/products")
def admin_products(admin: dict = Depends(require_admin)):
    return ser(list(d.products.find().sort([("category", 1), ("name", 1)])))


@router.post("/products", status_code=201)
def create_product(body: ProductIn, admin: dict = Depends(require_admin)):
    doc = {**body.model_dump(), "created_at": now(), "updated_at": now()}
    try:
        doc["_id"] = d.products.insert_one(doc).inserted_id
    except DuplicateKeyError:
        raise HTTPException(409, "A product with this name already exists")
    return ser(doc)


@router.put("/products/{product_id}")
def update_product(product_id: str, body: ProductUpdate, admin: dict = Depends(require_admin)):
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "Nothing to update")
    changes["updated_at"] = now()
    try:
        res = d.products.update_one({"_id": oid(product_id)}, {"$set": changes})
    except DuplicateKeyError:
        raise HTTPException(409, "A product with this name already exists")
    if not res.matched_count:
        raise HTTPException(404, "Product not found")
    return ser(d.products.find_one({"_id": oid(product_id)}))


@router.patch("/products/{product_id}/stock")
def set_stock(product_id: str, body: StockIn, admin: dict = Depends(require_admin)):
    res = d.products.update_one({"_id": oid(product_id)},
                                {"$set": {"stock": body.stock, "updated_at": now()}})
    if not res.matched_count:
        raise HTTPException(404, "Product not found")
    return {"stock": body.stock}


@router.delete("/products/{product_id}")
def hide_product(product_id: str, admin: dict = Depends(require_admin)):
    """Soft delete: hides it from the shop but keeps old orders intact."""
    res = d.products.update_one({"_id": oid(product_id)},
                                {"$set": {"is_active": False, "updated_at": now()}})
    if not res.matched_count:
        raise HTTPException(404, "Product not found")
    return {"message": "Product hidden from store"}


# ---------- company ----------
@router.get("/company")
def get_company(admin: dict = Depends(require_admin)):
    return ser(d.company.find_one({}))


@router.put("/company")
def update_company(body: CompanyIn, admin: dict = Depends(require_admin)):
    d.company.update_one({}, {"$set": {**body.model_dump(), "updated_at": now()}}, upsert=True)
    return ser(d.company.find_one({}))