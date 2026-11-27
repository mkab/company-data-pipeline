from functools import cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration every application process reads from environment variables.

    `DATABASE_URL` connects with the role of the Compose service that runs the process.
    """

    database_url: str


class MigrationSettings(BaseSettings):
    """Configuration Alembic reads from environment variables.

    `MIGRATIONS_DATABASE_URL` connects as the owner role.
    It is kept apart from `Settings`,
    so application code never reads the owner's credentials, only Alembic does.
    """

    migrations_database_url: str


class EdgarSettings(BaseSettings):
    """Configuration the ingest CLI reads from environment variables to call SEC EDGAR.

    `EDGAR_USER_AGENT` is the name and contact email SEC asks every client to send.
    It has no default, and an empty value counts as missing.
    It is kept apart from `Settings`, so the API starts without it.
    """

    edgar_user_agent: str = Field(min_length=1)


@cache
def get_settings() -> Settings:
    """Return the settings, read from the environment on first call."""
    return Settings()  # type: ignore[call-arg]  # pydantic-settings fills the fields from env vars


@cache
def get_migration_settings() -> MigrationSettings:
    """Return the migration settings, read from the environment on first call."""
    return MigrationSettings()  # type: ignore[call-arg]  # pydantic-settings fills the fields from env vars
