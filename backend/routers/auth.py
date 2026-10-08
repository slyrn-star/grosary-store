from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pymongo.errors import DuplicateKeyError

import database as d
from schemas import SignupIn, LoginIn
from security import (hash_password, verify_password, create_token,
                      get_current_user, set_auth_cookie, clear_auth_cookie)
from utils import now, ser, log_login_event

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", status_code=201)
def signup(body: SignupIn, request: Request, response: Response):
    email = body.email.lower()
    if d.users.find_one({"email": email}):
        log_login_event(request, "signup_failed", False, email=email,
                        reason="email_already_registered")
        raise HTTPException(409, "You already have an account. Please sign in.")

    user = {"name": body.name.strip(), "email": email,
            "password_hash": hash_password(body.password),
            "role": "customer", "is_active": True,
            "created_at": now(), "last_login_at": now()}
    try:
        user["_id"] = d.users.insert_one(user).inserted_id
    except DuplicateKeyError:
        raise HTTPException(409, "You already have an account. Please sign in.")

    log_login_event(request, "signup", True, email=email, user_id=user["_id"])
    set_auth_cookie(response, create_token(user))
    return {"user": ser(user)}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    user = d.users.find_one({"email": email})

    if not user or not verify_password(body.password, user["password_hash"]):
        log_login_event(request, "login_failed", False, email=email,
                        user_id=user["_id"] if user else None,
                        reason="wrong_password" if user else "unknown_email")
        raise HTTPException(401, "Invalid email or password.")

    if not user.get("is_active", True):
        log_login_event(request, "login_failed", False, email=email,
                        user_id=user["_id"], reason="account_disabled")
        raise HTTPException(403, "This account has been disabled.")

    d.users.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": now()}})
    log_login_event(request, "login_success", True, email=email, user_id=user["_id"])
    set_auth_cookie(response, create_token(user))
    return {"user": ser(user)}


@router.post("/logout")
def logout(request: Request, response: Response, user: dict = Depends(get_current_user)):
    d.sessions.update_one({"jti": user["jti"]}, {"$set": {"revoked": True}})
    log_login_event(request, "logout", True, email=user["email"], user_id=user["_id"])
    clear_auth_cookie(response)
    return {"message": "Logged out"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return ser(user)