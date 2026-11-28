from typing import TYPE_CHECKING

from httpx2 import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from fastapi import FastAPI


def client_for(app: FastAPI) -> AsyncClient:
    """Return a client that calls `app` in process, with no server."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
