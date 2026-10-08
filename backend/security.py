import uuid
from datetime import timedelta

import bcrypt
import jwt
from bson import ObjectId
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import database as d
from config import JWT_SECRET, JWT_EXPIRE_MINUTES
from utils import now

bearer = HTTPBearer(auto_error=False)
COOKIE_NAME = "access_token"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user: dict) -> str:
    jti = uuid.uuid4().hex
    expire = now() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    d.sessions.insert_one({"jti": jti, "user_id": user["_id"], "revoked": False,
                           "created_at": now(), "expire_at": expire})
    payload = {"sub": str(user["_id"]), "role": user["role"], "jti": jti, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def set_auth_cookie(response, token: str):
    response.set_cookie(COOKIE_NAME, token, max_age=JWT_EXPIRE_MINUTES * 60,
                        httponly=True, samesite="lax", secure=False, path="/")


def clear_auth_cookie(response):
    response.delete_cookie(COOKIE_NAME, path="/")


def get_current_user(request: Request,
                     creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    token = request.cookies.get(COOKIE_NAME) or (creds.credentials if creds else None)
    if not token:
        raise HTTPException(401, "Not logged in")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    if not d.sessions.find_one({"jti": payload["jti"], "revoked": False}):
        raise HTTPException(401, "Session ended. Please log in again.")
    user = d.users.find_one({"_id": ObjectId(payload["sub"])})
    if not user or not user.get("is_active", True):
        raise HTTPException(401, "Account not available")
    user["jti"] = payload["jti"]
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access only")
    return user