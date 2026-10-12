"""Database engine/session setup.

Stateless-API friendly: sessions are created per-request via
`get_db_session` (a FastAPI dependency) and closed immediately after, so no
connection state is held between requests — a requirement for horizontal
scaling behind a load balancer.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency: `db: Session = Depends(get_db_session)`."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create all tables. In production this is replaced by Alembic
    migrations; kept here for local dev / test convenience."""
    import backend.models  # noqa: F401  (ensures models are registered on Base.metadata)
    from backend.database.base import Base

    Base.metadata.create_all(bind=engine)
