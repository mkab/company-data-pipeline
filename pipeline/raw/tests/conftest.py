import contextlib
import os
from typing import TYPE_CHECKING

import pytest
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


@pytest.fixture
async def role_engine(request: pytest.FixtureRequest) -> AsyncIterator[AsyncEngine]:
    """Yield an engine connecting as the role the test is parametrized with (`indirect=True`)."""
    async with connecting_as(request.param) as engine:
        yield engine


@pytest.fixture
async def ingest_engine() -> AsyncIterator[AsyncEngine]:
    async with connecting_as("ingest") as engine:
        yield engine


@pytest.fixture(autouse=True)
async def empty_raw_tables() -> AsyncIterator[None]:
    """Empty the raw tables after each test, as the owner, since no service role may delete."""
    yield
    engine = create_async_engine(get_migration_settings().migrations_database_url)
    async with engine.begin() as connection:
        await connection.execute(
            sa.text("TRUNCATE raw.edgar_fetches, raw.edgar_payloads RESTART IDENTITY")
        )
    await engine.dispose()
