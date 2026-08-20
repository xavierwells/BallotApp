"""PostgreSQL connection utilities.

The public API never accepts a database URL.  It is supplied only through the
operator-controlled ``DATABASE_URL`` environment variable.
"""

from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


def sqlalchemy_database_url() -> str:
    """Return DATABASE_URL using the approved pg8000 SQLAlchemy dialect."""
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("DATABASE_URL is required for database operations")

    if value.startswith("postgresql+pg8000://"):
        return value
    if value.startswith("postgresql://"):
        return f"postgresql+pg8000://{value.removeprefix('postgresql://')}"
    if value.startswith("postgres://"):
        return f"postgresql+pg8000://{value.removeprefix('postgres://')}"
    raise RuntimeError("DATABASE_URL must use a PostgreSQL URL scheme")


@lru_cache
def get_engine() -> Engine:
    """Create the shared, pre-pinged PostgreSQL engine lazily."""
    return create_engine(sqlalchemy_database_url(), pool_pre_ping=True)


def database_is_ready() -> bool:
    """Return whether PostgreSQL is reachable without exposing connection details."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (RuntimeError, SQLAlchemyError):
        return False
    return True
