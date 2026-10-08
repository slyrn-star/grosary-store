from typing import Optional
from fastapi import APIRouter, HTTPException

import database as d
from utils import oid, ser

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("")
def list_products(category: Optional[str] = None, search: Optional[str] = None,
                  sort: str = "default"):
    q = {"is_active": True}
    if category and category != "all":
        q["category"] = category
    if search:
        import re
        q["name"] = {"$regex": re.escape(search), "$options": "i"}

    sort_map = {"name": [("name", 1)], "low": [("price", 1)], "high": [("price", -1)]}
    cur = d.products.find(q).sort(sort_map.get(sort, [("category", 1), ("name", 1)]))
    items = ser(list(cur))
    for p in items:
        p["in_stock"] = p["stock"] > 0
    return items


@router.get("/{product_id}")
def get_product(product_id: str):
    p = d.products.find_one({"_id": oid(product_id), "is_active": True})
    if not p:
        raise HTTPException(404, "Product not found")
    return ser(p)