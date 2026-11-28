"""Connect to the test database as one of the service roles, and empty the raw tables."""

import contextlib
import os
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import create_async_engine

import pipeline.raw.models  # noqa: F401  # registers the raw tables on `alembic_metadata`
from pipeline.database import RAW_SCHEMA, alembic_metadata, get_engine, get_sessionmaker
from pipeline.settings import get_migration_settings, get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine

# The password of each service role, which reaches the test container through `.env`
ROLE_PASSWORD_VARIABLES = {
    "ingest": "INGEST_DB_PASSWORD",
    "dbt": "DBT_DB_PASSWORD",
    "api": "API_DB_PASSWORD",
}


def role_database_url(role: str) -> str:
    """Return the test database URL, connecting as `role`."""
    return (
        make_url(get_settings().database_url)
        .set(username=role, password=os.environ[ROLE_PASSWORD_VARIABLES[role]])
        .render_as_string(hide_password=False)
    )


def clear_database_caches() -> None:
    """Forget the cached settings, engine and session factory, so the next use reads `DATABASE_URL` again."""
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@contextlib.asynccontextmanager
async def connecting_as(role: str) -> AsyncIterator[AsyncEngine]:
    """Yield an engine connecting to the test database as `role`, disposed of on exit."""
    engine = create_async_engine(role_database_url(role))
    yield engine
    await engine.dispose()


async def empty_raw_tables() -> None:
    """Empty every raw table as the owner, since no service role may delete.

    Children before parents, so no foreign key blocks a delete.
    """
    engine = create_async_engine(get_migration_settings().migrations_database_url)
    async with engine.begin() as connection:
        for table in reversed(alembic_metadata.sorted_tables):
            if table.schema == RAW_SCHEMA:
                await connection.execute(sa.delete(table))
    await engine.dispose()
