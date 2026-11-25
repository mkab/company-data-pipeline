from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import make_url

from pipeline.settings import get_migration_settings, get_settings

if TYPE_CHECKING:
    from collections.abc import Iterator

# Created by docker/initdb next to the development database
TEST_DATABASE_NAME = "pipeline_test"

ALEMBIC_CONFIG_PATH = Path(__file__).parent / "alembic.ini"


def on_test_database(url: str) -> str:
    """Return the same connection URL, pointed at the test database."""
    return make_url(url).set(database=TEST_DATABASE_NAME).render_as_string(hide_password=False)


def clear_settings_caches() -> None:
    get_settings.cache_clear()
    get_migration_settings.cache_clear()


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio only, the event loop the application uses."""
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def test_database_urls() -> Iterator[None]:
    """Point every database URL at the test database for the whole session.

    So no test touches the development data, whichever role it connects with.
    """
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("DATABASE_URL", on_test_database(get_settings().database_url))
        monkeypatch.setenv(
            "MIGRATIONS_DATABASE_URL",
            on_test_database(get_migration_settings().migrations_database_url),
        )
        clear_settings_caches()
        yield
    clear_settings_caches()


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database(test_database_urls: None) -> None:
    """Bring the test database to the latest migration, once per session."""
    command.upgrade(Config(ALEMBIC_CONFIG_PATH), "head")
