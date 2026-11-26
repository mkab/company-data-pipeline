import pytest
from httpx2 import ASGITransport, AsyncClient

from pipeline.api.app import create_app


@pytest.mark.anyio
async def test_health_returns_ok() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
