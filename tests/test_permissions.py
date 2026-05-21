from pathlib import Path

from src.permissions import (
    allowed_roles_for_department,
    infer_department,
    sensitivity_for_department,
    user_can_access,
)


def test_infer_department_from_first_folder() -> None:
    """Department should come from the first folder under the document root."""

    root = Path("/workspace/data/sample_docs")
    path = root / "finance" / "budget-approval-policy.md"
    assert infer_department(path, root) == "finance"


def test_finance_documents_are_restricted() -> None:
    """Finance documents should be visible only to finance users and admins."""

    allowed_roles = allowed_roles_for_department("finance")
    assert user_can_access("finance", allowed_roles)
    assert user_can_access("admin", allowed_roles)
    assert not user_can_access("general_staff", allowed_roles)


def test_general_documents_are_visible_to_all_roles() -> None:
    """General documents should be accessible to every supported role."""

    allowed_roles = allowed_roles_for_department("general")
    assert user_can_access("general_staff", allowed_roles)
    assert user_can_access("project_manager", allowed_roles)
    assert user_can_access("finance", allowed_roles)
    assert user_can_access("hr", allowed_roles)
    assert user_can_access("admin", allowed_roles)


def test_unknown_department_fails_closed() -> None:
    """Unknown departments should default to restricted admin-only access."""

    allowed_roles = allowed_roles_for_department("unknown")
    assert allowed_roles == ["admin"]
    assert sensitivity_for_department("unknown") == "restricted"
    assert user_can_access("admin", allowed_roles)
    assert not user_can_access("general_staff", allowed_roles)


def test_unknown_folder_is_not_treated_as_general() -> None:
    """Unmapped folders should not silently become general-access content."""

    root = Path("/workspace/data/sample_docs")
    path = root / "legal" / "contract-policy.md"
    assert infer_department(path, root) == "unknown"
