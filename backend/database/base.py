from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. All ORM models inherit from this so
    Alembic (or any future migration tool) has a single metadata target."""
    pass
