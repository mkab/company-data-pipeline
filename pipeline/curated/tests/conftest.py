import asyncio
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from pipeline.tests.curated import empty_curated_tables
from pipeline.tests.roles import connecting_as

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
