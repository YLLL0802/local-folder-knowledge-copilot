from pathlib import Path

from src.auth import authenticate_user, resolve_user
from src.config import Settings
from src.user_store import delete_user, list_users, upsert_user


def test_env_admin_can_log_in(tmp_path: Path) -> None:
    """The configured default admin should authenticate without user-store setup."""

    settings = Settings(
        admin_email="Admin@DefaultEmail.com",
        admin_password="secret",
        user_store_path=tmp_path / "users.json",
    )

    user = authenticate_user("admin@defaultemail.com", "secret", settings)

    assert user is not None
    assert user.email == "admin@defaultemail.com"
    assert user.role == "admin"
    assert user.is_admin


def test_local_user_can_log_in_after_admin_creates_account(tmp_path: Path) -> None:
    """A user created in the local store should authenticate with its assigned role."""

    settings = Settings(user_store_path=tmp_path / "users.json")

    upsert_user(settings, "finance.user@defaultemail.com", "finance", "pass123")
    user = authenticate_user("FINANCE.USER@defaultemail.com", "pass123", settings)

    assert user is not None
    assert user.email == "finance.user@defaultemail.com"
    assert user.role == "finance"
    assert not user.is_admin


def test_resolve_user_reflects_role_updates(tmp_path: Path) -> None:
    """Logged-in sessions should resolve to the latest role stored for the email."""

    settings = Settings(user_store_path=tmp_path / "users.json")

    upsert_user(settings, "person@defaultemail.com", "general_staff", "pass123")
    upsert_user(settings, "person@defaultemail.com", "hr")

    user = resolve_user("person@defaultemail.com", settings)

    assert user is not None
    assert user.role == "hr"


def test_delete_user_removes_local_login(tmp_path: Path) -> None:
    """Deleted local users should no longer resolve or authenticate."""

    settings = Settings(user_store_path=tmp_path / "users.json")
    upsert_user(settings, "project.user@defaultemail.com", "project_manager", "pass123")

    assert delete_user(settings, "project.user@defaultemail.com")
    assert list_users(settings) == []
    assert authenticate_user("project.user@defaultemail.com", "pass123", settings) is None
