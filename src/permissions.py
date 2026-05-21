from pathlib import Path


ROLES = ["general_staff", "project_manager", "finance", "hr", "admin"]

ALL_ROLES = ROLES.copy()
ADMIN_ONLY = ["admin"]

FOLDER_ROLE_MAP = {
    "general": ALL_ROLES,
    "projects": ["project_manager", "admin"],
    "finance": ["finance", "admin"],
    "hr": ["hr", "admin"],
}

FOLDER_SENSITIVITY_MAP = {
    "general": "internal-basic",
    "projects": "internal",
    "finance": "confidential",
    "hr": "confidential",
}


def validate_role(role: str) -> str:
    """Validate that a user role is one of the supported demo roles."""

    if role not in ROLES:
        raise ValueError(f"Unknown role '{role}'. Expected one of: {', '.join(ROLES)}")
    return role


def infer_department(path: Path, root_path: Path) -> str:
    """Infer department from the first folder below the document root."""

    try:
        relative = path.relative_to(root_path)
    except ValueError:
        return "unknown"

    if not relative.parts:
        return "unknown"
    folder = relative.parts[0].lower()
    return folder if folder in FOLDER_ROLE_MAP else "unknown"


def allowed_roles_for_department(department: str) -> list[str]:
    """Return roles allowed to access a department, failing closed to admin only."""

    return FOLDER_ROLE_MAP.get(department, ADMIN_ONLY).copy()


def sensitivity_for_department(department: str) -> str:
    """Return the default sensitivity label for a department."""

    return FOLDER_SENSITIVITY_MAP.get(department, "restricted")


def user_can_access(user_role: str, allowed_roles: list[str]) -> bool:
    """Check whether a role is allowed to view a source or chunk."""

    validate_role(user_role)
    return user_role == "admin" or user_role in allowed_roles
