import asyncio
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from pipeline.tests.curated import empty_curated_tables
from pipeline.tests.roles import clear_database_caches, connecting_as, role_database_url

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def dbt_session() -> AsyncIterator[AsyncSession]:
    """Yield a session as the dbt role, which owns the curated tables, committed at the end."""
    async with connecting_as("dbt") as engine, async_sessionmaker(engine).begin() as session:
        yield session


@pytest.fixture(autouse=True)
def empty_curated_tables_after_test() -> Iterator[None]:
    """Empty the curated tables after each test, sync so the package's sync tests can use it too."""
    yield
    asyncio.run(empty_curated_tables())


@pytest.fixture
def drift_check_as_api(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point `DATABASE_URL` at the api role, as `make curated-drift` runs.

    `main` runs its own event loop and disposes of the engine itself.
    """
    monkeypatch.setenv("DATABASE_URL", role_database_url("api"))
    clear_database_caches()
    yield
    clear_database_caches()
