"""Connect to the test database as one of the service roles, and empty the raw tables."""

import contextlib
import os
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import create_async_engine

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


@contextlib.asynccontextmanager
async def connecting_as(role: str) -> AsyncIterator[AsyncEngine]:
    """Yield an engine connecting to the test database as `role`, disposed of on exit."""
    engine = create_async_engine(role_database_url(role))
    yield engine
    await engine.dispose()


async def empty_raw_tables() -> None:
    """Empty the raw tables as the owner, since no service role may delete."""
    engine = create_async_engine(get_migration_settings().migrations_database_url)
    async with engine.begin() as connection:
        await connection.execute(
            sa.text("TRUNCATE raw.edgar_fetches, raw.edgar_payloads RESTART IDENTITY")
        )
    await engine.dispose()
