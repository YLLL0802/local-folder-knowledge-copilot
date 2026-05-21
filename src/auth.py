from __future__ import annotations

import hmac
from dataclasses import dataclass

from .config import Settings
from .permissions import validate_role
from .user_store import get_user, normalize_email, verify_password


@dataclass(frozen=True)
class AuthenticatedUser:
    """Authenticated local demo identity resolved to one application role."""

    email: str
    role: str
    source: str

    @property
    def is_admin(self) -> bool:
        """Return whether this user can access admin operations."""

        return self.role == "admin"


def authenticate_user(
    email: str,
    password: str,
    settings: Settings,
) -> AuthenticatedUser | None:
    """Authenticate a user against the env admin or local user store."""

    normalized = normalize_email(email)
    if not normalized or not password:
        return None

    if normalized == normalize_email(settings.admin_email):
        if hmac.compare_digest(password, settings.admin_password):
            return AuthenticatedUser(
                email=normalized,
                role="admin",
                source="env_admin",
            )
        return None

    record = get_user(settings, normalized)
    if not record:
        return None
    if not verify_password(
        password=password,
        salt=str(record.get("salt", "")),
        password_hash=str(record.get("password_hash", "")),
    ):
        return None

    role = validate_role(str(record.get("role", "")))
    return AuthenticatedUser(email=normalized, role=role, source="user_store")


def resolve_user(email: str, settings: Settings) -> AuthenticatedUser | None:
    """Resolve a logged-in email to the latest role without checking password."""

    normalized = normalize_email(email)
    if normalized == normalize_email(settings.admin_email):
        return AuthenticatedUser(email=normalized, role="admin", source="env_admin")

    record = get_user(settings, normalized)
    if not record:
        return None
    role = validate_role(str(record.get("role", "")))
    return AuthenticatedUser(email=normalized, role=role, source="user_store")
