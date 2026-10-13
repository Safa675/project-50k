"""Local email/password authentication; tokens and passwords never enter logs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import hmac
import ipaddress
import re
import secrets
import socket
from typing import Literal

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import HTTPException, Request
from pydantic import SecretStr

from p50k.product.db import connect
from p50k.product.settings import Settings


SESSION_COOKIE = "p50k_session"
CSRF_COOKIE = "p50k_csrf"
LOGIN_CSRF_COOKIE = "p50k_login_csrf"
LOCAL_SESSION_ID = "local-open-mode"
ABSOLUTE_LIFETIME = timedelta(hours=12)
IDLE_LIFETIME = timedelta(hours=2)
LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_CSRF_LIFETIME = 600
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
# Same-origin static photo path; migration 014 enforces the identical CHECK.
AVATAR_PATH_PATTERN = re.compile(r"^/avatars/[a-z0-9][a-z0-9-]{0,39}\.(jpg|png|webp)$")
HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16, type=Type.ID)


class AuthenticationError(Exception):
    def __init__(self, code: str = "AUTHENTICATION_REQUIRED", status: int = 401):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True)
class Principal:
    user_id: str
    email: str
    role: Literal["viewer", "analyst", "admin"]
    session_id: str
    csrf_sha256: str
    avatar_path: str | None = None

    def user(self) -> dict[str, str | None]:
        return {"user_id": self.user_id, "email": self.email, "role": self.role, "avatar_path": self.avatar_path}


def normalized_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 320 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Invalid email")
    return email


def digest_token(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def private_digest(pepper: SecretStr, purpose: str, value: str) -> str:
    return hmac.new(pepper.get_secret_value().encode(), (purpose + ":" + value).encode(), hashlib.sha256).hexdigest()


def password_material(password: SecretStr, pepper: SecretStr) -> str:
    value = password.get_secret_value()
    if not 12 <= len(value) <= 1024:
        raise ValueError("Password length must be between 12 and 1024 characters")
    return private_digest(pepper, "password", value)


def hash_password(password: SecretStr, pepper: SecretStr) -> str:
    return HASHER.hash(password_material(password, pepper))


@lru_cache(maxsize=1)
def dummy_hash() -> str:
    return HASHER.hash(secrets.token_urlsafe(32))


def verify_password(stored_hash: str | None, password: SecretStr, pepper: SecretStr) -> bool:
    try:
        material = password_material(password, pepper)
        valid = HASHER.verify(stored_hash or dummy_hash(), material)
        return bool(stored_hash and valid)
    except (InvalidHashError, VerificationError, VerifyMismatchError, ValueError):
        return False


def login_challenge(pepper: SecretStr, now: datetime) -> str:
    unsigned = secrets.token_urlsafe(32) + "." + str(int(now.timestamp()) + LOGIN_CSRF_LIFETIME)
    return unsigned + "." + private_digest(pepper, "login-csrf", unsigned)


def valid_login_challenge(value: str, pepper: SecretStr, now: datetime) -> bool:
    if len(value) > 160:
        return False
    parts = value.split(".")
    if len(parts) != 3 or not TOKEN_PATTERN.fullmatch(parts[0]) or not re.fullmatch(r"[0-9]{1,12}", parts[1]):
        return False
    expires = int(parts[1])
    if not now.timestamp() < expires <= now.timestamp() + LOGIN_CSRF_LIFETIME:
        return False
    return secrets.compare_digest(parts[2], private_digest(pepper, "login-csrf", parts[0] + "." + parts[1]))


def require_origin(request: Request, settings: Settings) -> None:
    if request.headers.get("origin") not in settings.allowed_origins:
        raise AuthenticationError("ORIGIN_REJECTED", 403)


def check_login_csrf(request: Request, settings: Settings, now: datetime) -> None:
    require_origin(request, settings)
    token = request.headers.get("x-csrf-token", "")
    cookie = request.cookies.get(LOGIN_CSRF_COOKIE, "")
    if not token or not secrets.compare_digest(token, cookie) or not valid_login_challenge(token, settings.auth_pepper(), now):
        raise AuthenticationError("CSRF_REJECTED", 403)


def check_session_csrf(request: Request, settings: Settings, principal: Principal) -> None:
    require_origin(request, settings)
    token = request.headers.get("x-csrf-token", "")
    if not TOKEN_PATTERN.fullmatch(token) or not secrets.compare_digest(token, request.cookies.get(CSRF_COOKIE, "")):
        raise AuthenticationError("CSRF_REJECTED", 403)
    if not secrets.compare_digest(digest_token(token), principal.csrf_sha256):
        raise AuthenticationError("CSRF_REJECTED", 403)


def client_ip(request: Request, settings: Settings) -> str:
    peer = request.client.host if request.client else "unknown"
    trusted = set()
    for hostname in settings.trusted_proxy_hosts:
        try:
            trusted.update(item[4][0] for item in socket.getaddrinfo(hostname, None))
        except OSError:
            continue
    forwarded = request.headers.get("x-p50k-client-ip", "")
    if peer in trusted and forwarded:
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return peer


class AuthService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def authenticate(self, token: str, now: datetime | None = None) -> Principal:
        if not TOKEN_PATTERN.fullmatch(token):
            raise AuthenticationError()
        now = now or datetime.now(timezone.utc)
        with connect(self.settings) as connection:
            row = connection.execute("""
                SELECT session.session_id,session.csrf_sha256,person.user_id,person.email,person.role,
                    person.avatar_path
                FROM auth.sessions session JOIN auth.users person USING(user_id)
                WHERE session.token_sha256=%s AND session.revoked_at IS NULL
                    AND person.disabled_at IS NULL AND session.expires_at>%s
                    AND COALESCE(session.last_seen_at,session.created_at)>%s
                FOR UPDATE OF session
            """, (digest_token(token), now, now - IDLE_LIFETIME)).fetchone()
            if row is None:
                raise AuthenticationError()
            connection.execute("""UPDATE auth.sessions SET last_seen_at=%s
                WHERE session_id=%s AND revoked_at IS NULL""", (now, row[0]))
        return Principal(str(row[2]), row[3], row[4], str(row[0]), row[1], row[5])

    def local_principal(self, email: str) -> Principal:
        """Single-user local mode: act as one existing enabled user, with no session row or cookie."""
        with connect(self.settings) as connection:
            row = connection.execute("""SELECT user_id,email,role,avatar_path FROM auth.users
                WHERE email=%s AND disabled_at IS NULL""", (normalized_email(email),)).fetchone()
        if row is None:
            raise AuthenticationError("LOCAL_USER_MISSING", 503)
        return Principal(str(row[0]), row[1], row[2], LOCAL_SESSION_ID, "", row[3])

    def login(self, email: str, password: SecretStr, ip: str, previous_token: str = "",
              now: datetime | None = None) -> tuple[Principal, str, str]:
        now = now or datetime.now(timezone.utc)
        email = normalized_email(email)
        pepper = self.settings.auth_pepper()
        email_sha, ip_sha = private_digest(pepper, "email", email), private_digest(pepper, "ip", ip)
        failed = False
        with connect(self.settings) as connection:
            for key in sorted((email_sha, ip_sha)):
                connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,50000031))", (key,))
            count = connection.execute("""
                SELECT count(*) FILTER (WHERE email_sha256=%s),count(*) FILTER (WHERE ip_sha256=%s)
                FROM auth.login_attempts WHERE created_at>%s AND NOT succeeded
                    AND (email_sha256=%s OR ip_sha256=%s)
            """, (email_sha, ip_sha, now - LOGIN_WINDOW, email_sha, ip_sha)).fetchone()
            if count[0] >= 5 or count[1] >= 20:
                raise AuthenticationError("LOGIN_THROTTLED", 429)
            row = connection.execute("SELECT user_id,email,role,password_hash,disabled_at,avatar_path FROM auth.users WHERE email=%s FOR UPDATE", (email,)).fetchone()
            valid = verify_password(row[3] if row else None, password, pepper)
            valid = valid and row is not None and row[4] is None
            connection.execute("INSERT INTO auth.login_attempts (email_sha256,ip_sha256,succeeded,created_at) VALUES (%s,%s,%s,%s)",
                               (email_sha, ip_sha, valid, now))
            if not valid:
                failed = True
            else:
                if HASHER.check_needs_rehash(row[3]):
                    connection.execute("UPDATE auth.users SET password_hash=%s WHERE user_id=%s",
                                       (hash_password(password, pepper), row[0]))
                if TOKEN_PATTERN.fullmatch(previous_token):
                    connection.execute("UPDATE auth.sessions SET revoked_at=%s WHERE token_sha256=%s AND revoked_at IS NULL",
                                       (now, digest_token(previous_token)))
                token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                session_id = connection.execute("""
                    INSERT INTO auth.sessions (user_id,token_sha256,csrf_sha256,created_at,expires_at,last_seen_at)
                    VALUES (%s,%s,%s,%s,%s,%s) RETURNING session_id
                """, (row[0], digest_token(token), digest_token(csrf), now, now + ABSOLUTE_LIFETIME, now)).fetchone()[0]
                connection.execute("INSERT INTO ops.audit_log (action,actor_id,target_type,target_id) VALUES ('LOGIN_SUCCESS',%s,'SESSION',%s)",
                                   (row[0], str(session_id)))
                principal = Principal(str(row[0]), row[1], row[2], str(session_id), digest_token(csrf), row[5])
        if failed:
            raise AuthenticationError("INVALID_CREDENTIALS")
        return principal, token, csrf

    def logout(self, principal: Principal, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        with connect(self.settings) as connection:
            connection.execute("UPDATE auth.sessions SET revoked_at=%s WHERE session_id=%s AND user_id=%s AND revoked_at IS NULL",
                               (now, principal.session_id, principal.user_id))
            connection.execute("INSERT INTO ops.audit_log (action,actor_id,target_type,target_id) VALUES ('LOGOUT',%s,'SESSION',%s)",
                               (principal.user_id, principal.session_id))


def require_session(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(401, "AUTHENTICATION_REQUIRED")
    return principal


def require_analyst(request: Request) -> Principal:
    principal = require_session(request)
    if principal.role not in {"analyst", "admin"}:
        raise HTTPException(403, "ROLE_REQUIRED")
    return principal


def require_admin(request: Request) -> Principal:
    principal = require_session(request)
    if principal.role != "admin":
        raise HTTPException(403, "ROLE_REQUIRED")
    return principal
