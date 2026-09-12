"""Provisioned staff accounts; opaque, expiring, server-side sessions."""

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import os
import re
import secrets

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie
from sqlalchemy import text

from app.database import get_engine

COOKIE = "ballot_editorial_session"
cookie_scheme = APIKeyCookie(name=COOKIE, auto_error=False)
ITERATIONS = 600_000


def hash_password(password: str, salt: str | None = None) -> str:
    if not 15 <= len(password) <= 256:
        raise ValueError("Use a password or passphrase between 15 and 256 characters.")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    if len(stored.split("$")) != 4:
        return False
    algorithm, iterations, salt, expected = stored.split("$")
    if algorithm != "pbkdf2_sha256":
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac.compare_digest(actual, expected)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_user(connection, publication_id, username: str, password: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", username):
        raise ValueError("Username must use 3–80 lowercase letters, digits, dots, underscores or hyphens.")
    connection.execute(text(
        "INSERT INTO editorial_users (id,publication_id,username,password_hash) "
        "VALUES (gen_random_uuid(),:p,:u,:h)"
    ), {"p": publication_id, "u": username, "h": hash_password(password)})


def login(username: str, password: str) -> str | None:
    now = datetime.now(UTC)
    with get_engine().begin() as connection:
        user = connection.execute(text(
            "SELECT * FROM editorial_users WHERE username=:u FOR UPDATE"
        ), {"u": username}).mappings().one_or_none()
        if user is None:
            # Similar work for unknown users; do not expose account existence.
            hashlib.pbkdf2_hmac("sha256", password.encode(), b"unknown-staff-user", ITERATIONS)
            return None
        if not user["active"] or (user["locked_until"] and user["locked_until"] > now):
            hashlib.pbkdf2_hmac("sha256", password.encode(), b"unavailable-staff-user", ITERATIONS)
            return None
        if not verify_password(password, user["password_hash"]):
            failures = user["failed_logins"] + 1
            connection.execute(text(
                "UPDATE editorial_users SET failed_logins=:n,locked_until=:until WHERE id=:id"
            ), {"id": user["id"], "n": failures if failures < 5 else 0,
                "until": now + timedelta(minutes=5) if failures >= 5 else None})
            return None
        connection.execute(text("UPDATE editorial_users SET failed_logins=0,locked_until=NULL WHERE id=:id"), {"id": user["id"]})
        connection.execute(text("DELETE FROM editorial_sessions WHERE expires_at <= :now OR user_id=:id"),
                           {"now": now, "id": user["id"]})
        token = secrets.token_urlsafe(32)
        connection.execute(text(
            "INSERT INTO editorial_sessions(token_hash,user_id,expires_at) VALUES (:t,:u,:e)"
        ), {"t": token_hash(token), "u": user["id"], "e": now + timedelta(hours=8)})
        return token


def require_editor(token: str | None = Depends(cookie_scheme)) -> dict:
    if not token or len(token) > 128:
        raise HTTPException(401, "Sign in to the editorial workspace.")
    with get_engine().connect() as connection:
        user = connection.execute(text(
            "SELECT u.id,u.publication_id,u.username FROM editorial_sessions s "
            "JOIN editorial_users u ON u.id=s.user_id "
            "WHERE s.token_hash=:t AND s.expires_at>CURRENT_TIMESTAMP AND u.active=TRUE"
        ), {"t": token_hash(token)}).mappings().one_or_none()
    if user is None:
        raise HTTPException(401, "Your session expired. Sign in again.")
    return dict(user)


def require_origin(request: Request) -> None:
    """Require the configured frontend origin on every browser mutation, including login."""
    origin = os.getenv("PUBLIC_WEB_ORIGIN", "http://localhost:3000").rstrip("/")
    if request.headers.get("origin") != origin:
        raise HTTPException(403, "This action must come from the editorial workspace.")
