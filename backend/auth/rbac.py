"""Role-based access control.

Kept as a standalone module (rather than baked into the JWT payload logic)
so that authorization rules can be unit tested and changed without touching
token issuance.
"""

from typing import Iterable

from backend.core.constants import UserRole
from backend.core.exceptions import AuthorizationError

# Which roles can access which permission scopes. Extend as new permissions
# are introduced — nothing outside this module needs to know the mapping.
# BUSINESS_ANALYST/ANALYST and READ_ONLY_USER/VIEWER intentionally share
# identical grants — they're the modern name and the legacy alias for the
# same role.
_ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.SUPER_ADMIN: {"*"},
    UserRole.ADMIN: {"*"},
    UserRole.ML_ENGINEER: {"model:train", "model:infer", "dataset:write", "dataset:read", "experiment:write", "experiment:read"},
    UserRole.NLP_ENGINEER: {"model:train", "model:infer", "dataset:write", "dataset:read", "experiment:write", "experiment:read"},
    UserRole.DATA_SCIENTIST: {"model:infer", "dataset:write", "dataset:read", "experiment:write", "experiment:read", "report:read"},
    UserRole.REVIEWER: {"model:infer", "review:read", "review:write", "experiment:read"},
    UserRole.BUSINESS_ANALYST: {"model:infer", "experiment:read", "report:read"},
    UserRole.ANALYST: {"model:infer", "experiment:read", "report:read"},
    UserRole.AUDITOR: {"audit:read", "experiment:read", "report:read"},
    UserRole.READ_ONLY_USER: {"model:infer", "experiment:read"},
    UserRole.VIEWER: {"model:infer", "experiment:read"},
}


def has_permission(role: UserRole, permission: str) -> bool:
    granted = _ROLE_PERMISSIONS.get(role, set())
    return "*" in granted or permission in granted


def require_permission(role: UserRole, permission: str) -> None:
    if not has_permission(role, permission):
        raise AuthorizationError(
            f"Role '{role.value}' does not have permission '{permission}'."
        )


def require_any_role(role: UserRole, allowed: Iterable[UserRole]) -> None:
    if role not in set(allowed):
        raise AuthorizationError(f"Role '{role.value}' is not permitted for this action.")
