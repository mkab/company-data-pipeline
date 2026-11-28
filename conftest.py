import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import make_url

from pipeline.database import get_engine, get_sessionmaker
from pipeline.settings import get_migration_settings, get_settings
from pipeline.tests.curated import create_curated_tables
from pipeline.tests.roles import empty_raw_tables, role_database_url

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

# Created by docker/initdb next to the development database
TEST_DATABASE_NAME = "pipeline_test"

ALEMBIC_CONFIG_PATH = Path(__file__).parent / "alembic.ini"


def with_test_database_name(url: str) -> str:
    """Return the same connection URL, pointed at the test database."""
    return make_url(url).set(database=TEST_DATABASE_NAME).render_as_string(hide_password=False)


def clear_settings_caches() -> None:
    get_settings.cache_clear()
    get_migration_settings.cache_clear()


def clear_database_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio only, the event loop the application uses."""
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def point_settings_at_test_database() -> Iterator[None]:
    """Point every database URL at the test database for the whole session.

    So no test touches the development data, whichever role it connects with.
    """
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("DATABASE_URL", with_test_database_name(get_settings().database_url))
        monkeypatch.setenv(
            "MIGRATIONS_DATABASE_URL",
            with_test_database_name(get_migration_settings().migrations_database_url),
        )
        clear_settings_caches()
        yield
    clear_settings_caches()


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database(point_settings_at_test_database: None) -> None:
    """Bring the test database to the latest migration with empty raw tables, once per session.

    `make seed-test` fills the same raw tables for dbt,
    so a test never starts on its rows.
    """
    command.upgrade(Config(ALEMBIC_CONFIG_PATH), "head")
    asyncio.run(empty_raw_tables())


@pytest.fixture(scope="session", autouse=True)
def curated_test_tables(point_settings_at_test_database: None) -> None:
    """Create the curated tables in the test database, empty, once per session.

    They replace any `make dbt ARGS="build --target test"` built,
    so a test never starts on dbt's rows.
    """
    asyncio.run(create_curated_tables())


@pytest.fixture
async def database_url_as_api(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """Point `DATABASE_URL`, and so `session_scope`, at the api role, as the API connects.

    Each test runs on its own event loop, so the cached engine is disposed of after it.
    """
    monkeypatch.setenv("DATABASE_URL", role_database_url("api"))
    clear_database_caches()
    yield
    await get_engine().dispose()
    clear_database_caches()


@pytest.fixture
async def database_url_as_ingest(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    """Point `DATABASE_URL`, and so `session_scope`, at the ingest role, which can write raw.

    Shared by the tests of `session_scope` and of the ingest run,
    which opens it per fetch.
    Each test runs on its own event loop, so the cached engine is disposed of after it.
    """
    monkeypatch.setenv("DATABASE_URL", role_database_url("ingest"))
    clear_database_caches()
    yield
    await get_engine().dispose()
    clear_database_caches()
    await empty_raw_tables()
