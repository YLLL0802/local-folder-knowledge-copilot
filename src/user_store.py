from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings
from .permissions import validate_role


PBKDF2_ITERATIONS = 120_000


def normalize_email(email: str) -> str:
    """Normalize email addresses for login and user lookup."""

    return email.strip().lower()


def validate_email(email: str) -> str:
    """Validate a demo email address and return its normalized value."""

    normalized = normalize_email(email)
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ValueError("Enter a valid email address.")
    return normalized


def hash_password(password: str) -> tuple[str, str]:
    """Hash a password for local demo storage."""

    if not password:
        raise ValueError("Password is required.")
    salt = secrets.token_hex(16)
    return salt, _hash_with_salt(password, salt)


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    """Verify a submitted password against a stored salted hash."""

    if not password or not salt or not password_hash:
        return False
    expected = _hash_with_salt(password, salt)
    return hmac.compare_digest(expected, password_hash)


def list_users(settings: Settings) -> list[dict[str, Any]]:
    """Return public user records from the local user store."""

    users = [_public_user(record) for record in _load_store(settings)["users"]]
    return sorted(users, key=lambda user: user["email"])


def get_user(settings: Settings, email: str) -> dict[str, Any] | None:
    """Return one raw stored user record by email."""

    normalized = normalize_email(email)
    for record in _load_store(settings)["users"]:
        if normalize_email(str(record.get("email", ""))) == normalized:
            return record
    return None


def upsert_user(
    settings: Settings,
    email: str,
    role: str,
    password: str = "",
) -> dict[str, Any]:
    """Create or update a local demo user."""

    normalized = validate_email(email)
    if normalized == normalize_email(settings.admin_email):
        raise ValueError("The default admin account is controlled by .env settings.")
    validate_role(role)

    store = _load_store(settings)
    now = _utc_now()
    for record in store["users"]:
        if normalize_email(str(record.get("email", ""))) != normalized:
            continue
        record["role"] = role
        record["updated_at"] = now
        if password:
            salt, password_hash = hash_password(password)
            record["salt"] = salt
            record["password_hash"] = password_hash
        _save_store(settings, store)
        return _public_user(record)

    salt, password_hash = hash_password(password)
    record = {
        "email": normalized,
        "role": role,
        "salt": salt,
        "password_hash": password_hash,
        "created_at": now,
        "updated_at": now,
    }
    store["users"].append(record)
    _save_store(settings, store)
    return _public_user(record)


def delete_user(settings: Settings, email: str) -> bool:
    """Delete a local demo user from the user store."""

    normalized = validate_email(email)
    if normalized == normalize_email(settings.admin_email):
        raise ValueError("The default admin account is controlled by .env settings.")

    store = _load_store(settings)
    original_count = len(store["users"])
    store["users"] = [
        record
        for record in store["users"]
        if normalize_email(str(record.get("email", ""))) != normalized
    ]
    if len(store["users"]) == original_count:
        return False
    _save_store(settings, store)
    return True


def _load_store(settings: Settings) -> dict[str, list[dict[str, Any]]]:
    """Load the local user store, tolerating a missing file."""

    path = Path(settings.user_store_path)
    if not path.exists():
        return {"users": []}

    data = json.loads(path.read_text(encoding="utf-8"))
    users = data.get("users", [])
    if not isinstance(users, list):
        raise ValueError(f"Invalid user store format at {path}.")
    return {"users": users}


def _save_store(settings: Settings, store: dict[str, list[dict[str, Any]]]) -> None:
    """Persist the local user store as JSON."""

    path = Path(settings.user_store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")


def _public_user(record: dict[str, Any]) -> dict[str, Any]:
    """Strip password material before rendering user records."""

    return {
        "email": normalize_email(str(record.get("email", ""))),
        "role": str(record.get("role", "")),
        "source": "user_store",
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def _hash_with_salt(password: str, salt: str) -> str:
    """Derive a stable password hash from password and salt."""

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return derived.hex()


def _utc_now() -> str:
    """Return a compact UTC timestamp for user-store records."""

    return datetime.now(timezone.utc).isoformat()
