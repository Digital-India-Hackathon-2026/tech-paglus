"""
Authentication service: user accounts, password hashing, and session tokens.

Design notes:
- Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib `hashlib`), so no extra
  compiled dependency (like bcrypt) is needed on Windows.
- Session tokens are a lightweight, dependency-free JWT-style token:
  base64url(payload) + "." + HMAC-SHA256 signature, signed with AUTH_SECRET_KEY.
- Terms & Conditions acceptance is recorded permanently on the user record
  (accepted flag + version + timestamp) so it can be audited later.
"""

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
from typing import Any

DB_PATH = "database.db"

# Bump this if the Terms & Conditions text changes and users must re-accept.
TERMS_VERSION = "1.0"

# Secret used to sign session tokens. In production, set AUTH_SECRET_KEY in
# backend/.env. Falls back to a fixed dev value so local dev keeps working,
# but this fallback must never be used outside local development.
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "agrisarthi-dev-secret-change-me")
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


class AuthError(Exception):
    """Raised for expected auth failures (bad credentials, duplicate phone, etc.)."""


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            terms_accepted INTEGER NOT NULL DEFAULT 0,
            terms_version TEXT,
            terms_accepted_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256, stdlib only)
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return digest.hex(), salt.hex()


def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    digest, _ = _hash_password(password, salt)
    return hmac.compare_digest(digest, hash_hex)


# ---------------------------------------------------------------------------
# Session tokens (dependency-free JWT-style: payload.signature)
# ---------------------------------------------------------------------------

def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def create_token(user_id: int, phone: str) -> str:
    payload = {"uid": user_id, "phone": phone, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    payload_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))
    signature = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)
    return f"{payload_b64}.{sig_b64}"


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url_encode(expected_sig), sig_b64):
            return None
        payload = json.loads(_b64url_decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

def _user_to_public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "phone": row["phone"],
        "termsAccepted": bool(row["terms_accepted"]),
        "termsVersion": row["terms_version"],
        "createdAt": row["created_at"],
    }


def register_user(name: str, phone: str, password: str, terms_accepted: bool) -> dict[str, Any]:
    init_auth_db()
    name = (name or "").strip()
    phone = (phone or "").strip()

    if not name:
        raise AuthError("Please enter your name.")
    if not phone or len(phone) < 6:
        raise AuthError("Please enter a valid phone number.")
    if not password or len(password) < 6:
        raise AuthError("Password must be at least 6 characters.")
    if not terms_accepted:
        raise AuthError("You must accept the Terms & Conditions to create an account.")

    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE phone = ?", (phone,))
    if cur.fetchone():
        conn.close()
        raise AuthError("An account with this phone number already exists.")

    password_hash, salt = _hash_password(password)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cur.execute(
        """
        INSERT INTO users (name, phone, password_hash, password_salt, terms_accepted, terms_version, terms_accepted_at)
        VALUES (?, ?, ?, ?, 1, ?, ?)
        """,
        (name, phone, password_hash, salt, TERMS_VERSION, now),
    )
    conn.commit()
    user_id = cur.lastrowid
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return _user_to_public(row)


def authenticate_user(phone: str, password: str) -> dict[str, Any]:
    init_auth_db()
    phone = (phone or "").strip()
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    row = cur.fetchone()
    conn.close()
    if not row or not _verify_password(password or "", row["password_salt"], row["password_hash"]):
        raise AuthError("Incorrect phone number or password.")
    return _user_to_public(row)


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    init_auth_db()
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return _user_to_public(row) if row else None
