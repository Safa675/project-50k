"""Local session endpoints; requests are validated before credentials are used."""
from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from p50k.product.auth import (ABSOLUTE_LIFETIME, CSRF_COOKIE, LOGIN_CSRF_COOKIE, SESSION_COOKIE,
    AuthenticationError, AuthService, Principal, check_login_csrf, client_ip, hash_password,
    login_challenge, require_session, verify_password)
from p50k.product.db import connect

router = APIRouter(prefix="/auth", tags=["Session"])

class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: SecretStr = Field(min_length=1, max_length=1024)

class PasswordBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: SecretStr = Field(min_length=1, max_length=1024)
    new_password: SecretStr = Field(min_length=12, max_length=1024)

@router.get("/csrf")
def challenge(request: Request, response: Response):
    settings = request.app.state.product_settings
    token = login_challenge(settings.auth_pepper(), datetime.now(timezone.utc))
    response.set_cookie(LOGIN_CSRF_COOKIE, token, max_age=600, secure=settings.cookie_secure,
                        httponly=True, samesite="lax", path="/")
    return {"csrf_token": token}

@router.post("/login")
def login(body: LoginBody, request: Request, response: Response):
    settings = request.app.state.product_settings
    try:
        check_login_csrf(request, settings, datetime.now(timezone.utc))
        principal, token, csrf = AuthService(settings).login(body.email, body.password,
            client_ip(request, settings), request.cookies.get(SESSION_COOKIE, ""))
    except AuthenticationError as error:
        raise HTTPException(error.status, error.code) from None
    except ValueError:
        raise HTTPException(401, "INVALID_CREDENTIALS") from None
    for name, value, private in ((SESSION_COOKIE, token, True), (CSRF_COOKIE, csrf, False)):
        response.set_cookie(name, value, max_age=int(ABSOLUTE_LIFETIME.total_seconds()),
                            secure=settings.cookie_secure, httponly=private, samesite="lax", path="/")
    response.delete_cookie(LOGIN_CSRF_COOKIE, path="/")
    return {"user": principal.user()}

@router.get("/me")
def me(request: Request, principal: Principal = Depends(require_session)):
    from p50k.product.analysis_context import public_context,historical_mode
    return {"user": principal.user(), "data_mode": "SYNTHETIC" if request.app.state.product_settings.db_name=='p50k_dev' else 'HISTORICAL_REPLAY' if historical_mode() else "DELAYED",
            'analysis_context':public_context(request.app.state.product_settings)}

@router.post("/logout")
def logout(request: Request, response: Response, principal: Principal = Depends(require_session)):
    if request.app.state.product_settings.local_open_email:
        return {"logged_out": False, "local_open": True}  # no session exists to revoke in single-user local mode
    AuthService(request.app.state.product_settings).logout(principal)
    for name in (SESSION_COOKIE, CSRF_COOKIE, LOGIN_CSRF_COOKIE):
        response.delete_cookie(name, path="/")
    return {"logged_out": True}

@router.post("/password")
def password(body: PasswordBody, request: Request, response: Response, principal: Principal = Depends(require_session)):
    settings = request.app.state.product_settings
    pepper = settings.auth_pepper()
    with connect(settings) as connection:
        row = connection.execute("SELECT password_hash FROM auth.users WHERE user_id=%s FOR UPDATE", (principal.user_id,)).fetchone()
        if not row or not verify_password(row[0], body.current_password, pepper):
            raise HTTPException(401, "INVALID_CREDENTIALS")
        connection.execute("UPDATE auth.users SET password_hash=%s WHERE user_id=%s", (hash_password(body.new_password, pepper), principal.user_id))
        connection.execute("UPDATE auth.sessions SET revoked_at=clock_timestamp() WHERE user_id=%s AND revoked_at IS NULL", (principal.user_id,))
        connection.execute("INSERT INTO ops.audit_log(action,actor_id,target_type,target_id) VALUES ('PASSWORD_CHANGED',%s,'USER',%s)", (principal.user_id, principal.user_id))
    for name in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/")
    return {"logged_out": True}
