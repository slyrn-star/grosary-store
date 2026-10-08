from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, Request
import database as d


def now():
    return datetime.now(timezone.utc)


def oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(400, "Invalid id")


def ser(x):
    """Make Mongo documents JSON-friendly: _id -> id, ObjectId -> str,
    and never leak password hashes."""
    if isinstance(x, list):
        return [ser(i) for i in x]
    if isinstance(x, dict):
        return {("id" if k == "_id" else k): ser(v)
                for k, v in x.items() if k != "password_hash"}
    if isinstance(x, ObjectId):
        return str(x)
    return x


def client_info(request: Request) -> dict:
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


def log_login_event(request, event, success, email=None, user_id=None, reason=None):
    """event: signup | signup_failed | login_success | login_failed | logout"""
    d.login_history.insert_one({
        "event": event,
        "success": success,
        "email": email,
        "user_id": user_id,
        "reason": reason,
        **client_info(request),
        "created_at": now(),
    })


def log_activity(user_id, action, details=None):
    """action: cart_add | cart_remove | cart_clear | order_placed | order_<status> ..."""
    d.activity_log.insert_one({
        "user_id": user_id,
        "action": action,
        "details": details or {},
        "created_at": now(),
    })