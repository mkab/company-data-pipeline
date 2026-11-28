from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from pipeline.raw.services import EdgarFetchService
from pipeline.raw.tests.fakes import FakeEdgarFetchRepository, FakeEdgarPayloadRepository
from pipeline.tests.roles import connecting_as, empty_raw_tables

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@pytest.fixture
async def role_engine(request: pytest.FixtureRequest) -> AsyncIterator[AsyncEngine]:
    """Yield an engine connecting as the role the test is parametrized with (`indirect=True`)."""
    async with connecting_as(request.param) as engine:
        yield engine


@pytest.fixture
async def ingest_engine() -> AsyncIterator[AsyncEngine]:
    async with connecting_as("ingest") as engine:
        yield engine


@pytest.fixture
async def ingest_session(ingest_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield a session as the ingest role, as the ingest CLI writes, committed at the end."""
    async with async_sessionmaker(ingest_engine).begin() as session:
        yield session


@pytest.fixture(autouse=True)
async def empty_raw_tables_after_test() -> AsyncIterator[None]:
    yield
    await empty_raw_tables()


@pytest.fixture
def payloads() -> FakeEdgarPayloadRepository:
    return FakeEdgarPayloadRepository()


@pytest.fixture
def fetches() -> FakeEdgarFetchRepository:
    return FakeEdgarFetchRepository()


@pytest.fixture
def edgar_fetch_service(
    payloads: FakeEdgarPayloadRepository, fetches: FakeEdgarFetchRepository
) -> EdgarFetchService:
    return EdgarFetchService(payloads, fetches)
