"""
Seeds a default admin account so a fresh `development` environment is
usable immediately, without requiring manual database setup before the
first login.

Never runs in production (the app already refuses to start in production
without a real SECRET_KEY — this is the same category of safeguard) and
never runs in the `testing` environment (tests create their own users
explicitly, and seeding there would just be silent, pointless writes to
an unused database — see tests/conftest.py, which overrides the DB
session dependency with its own in-memory engine).
"""

from sqlalchemy.orm import Session

from backend.auth.password import hash_password
from backend.config.logging_config import get_logger
from backend.config.settings import get_settings
from backend.core.constants import UserRole
from backend.models.user import User
from backend.repositories.user_repository import UserRepository

logger = get_logger("api")

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "ChangeMe123!"  # noqa: S105 — dev-only bootstrap credential, logged loudly below


def seed_default_admin(db: Session) -> None:
    settings = get_settings()
    if settings.is_production or settings.is_testing:
        return

    users = UserRepository(db)
    if users.list(limit=1):
        return  # at least one user already exists — never overwrite/reset

    admin = User(
        username=DEFAULT_ADMIN_USERNAME,
        email=DEFAULT_ADMIN_EMAIL,
        hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
        role=UserRole.SUPER_ADMIN.value,
    )
    users.create(admin)
    logger.warning(
        "seeded_default_admin_account",
        extra={
            "username": DEFAULT_ADMIN_USERNAME,
            "note": "Development-only bootstrap account. Change this password "
            "immediately in any environment other than a local sandbox.",
        },
    )
