from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import make_url

from pipeline.database import DATABASE_URL_ATTRIBUTE
from pipeline.settings import get_settings

# Created by docker/initdb, so tests never touch the development data
TEST_DATABASE_NAME = "pipeline_test"

ALEMBIC_CONFIG_PATH = Path(__file__).parent / "alembic.ini"


@pytest.fixture
def anyio_backend() -> str:
    """Run async tests on asyncio only, the event loop the application uses."""
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database() -> None:
    """Bring the test database to the latest migration, once per session."""
    owner_url = make_url(get_settings().migrations_database_url).set(database=TEST_DATABASE_NAME)
    config = Config(ALEMBIC_CONFIG_PATH)
    config.attributes[DATABASE_URL_ATTRIBUTE] = owner_url.render_as_string(hide_password=False)
    command.upgrade(config, "head")
