from typing import TYPE_CHECKING

import pytest

from pipeline.database import get_engine
from pipeline.tests.roles import clear_database_caches

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from httpx2 import AsyncClient

pytestmark = pytest.mark.anyio

# Port 1 has no listener, so connecting is refused at once
UNREACHABLE_DATABASE_URL = "postgresql+psycopg://api:api@localhost:1/pipeline_test"


@pytest.fixture
async def database_down(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    monkeypatch.setenv("DATABASE_URL", UNREACHABLE_DATABASE_URL)
    clear_database_caches()
    yield
    await get_engine().dispose()
    clear_database_caches()


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.usefixtures("database_url_as_api")
async def test_ready_returns_ok_with_the_database_up(client: AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.usefixtures("database_down")
async def test_ready_returns_a_503_problem_with_the_database_down(client: AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Service unavailable",
        "status": 503,
        "detail": "The database is unreachable",
    }


async def test_docs_are_served(client: AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200
