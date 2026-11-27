from typing import TYPE_CHECKING

import pytest

from pipeline.database import get_engine, get_sessionmaker
from pipeline.settings import get_settings
from pipeline.tests.roles import empty_raw_tables, role_database_url

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


def clear_database_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@pytest.fixture
async def database_url_as_ingest(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """Point `DATABASE_URL`, and so `session_scope`, at the ingest role, which can write raw.

    Each test runs on its own event loop, so the cached engine is disposed of after it.
    """
    monkeypatch.setenv("DATABASE_URL", role_database_url("ingest"))
    clear_database_caches()
    yield
    await get_engine().dispose()
    clear_database_caches()
    await empty_raw_tables()
