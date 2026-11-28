from typing import TYPE_CHECKING

import pytest

from pipeline.api.app import create_app
from pipeline.api.tests.clients import client_for

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from httpx2 import AsyncClient


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Yield a client of the API application."""
    async with client_for(create_app()) as api_client:
        yield api_client
