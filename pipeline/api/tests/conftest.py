from typing import TYPE_CHECKING

import pytest
from httpx2 import ASGITransport, AsyncClient

from pipeline.api.app import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI


def client_for(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Yield a client of the API application."""
    async with client_for(create_app()) as api_client:
        yield api_client
