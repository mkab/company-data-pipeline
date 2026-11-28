from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx2 import AsyncClient

pytestmark = pytest.mark.anyio


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
