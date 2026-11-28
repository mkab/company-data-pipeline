from typing import TYPE_CHECKING

import pytest

from pipeline.api.app import create_app
from pipeline.api.tests.clients import client_for
from pipeline.database import get_engine
from pipeline.tests.roles import clear_database_caches

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from httpx2 import AsyncClient

# Port 1 has no listener,
# so connecting is refused at once
UNREACHABLE_DATABASE_URL = "postgresql+psycopg://api:api@localhost:1/pipeline_test"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Yield a client of the API application."""
    async with client_for(create_app()) as api_client:
        yield api_client


@pytest.fixture
async def database_down(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """Point `DATABASE_URL` at a port nothing listens on, as if the database were down."""
    monkeypatch.setenv("DATABASE_URL", UNREACHABLE_DATABASE_URL)
    clear_database_caches()
    yield
    await get_engine().dispose()
    clear_database_caches()
