from functools import cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration every application process reads from environment variables.

    `DATABASE_URL` connects with the role of the Compose service that runs the process.
    """

    database_url: str


class MigrationSettings(BaseSettings):
    """Configuration Alembic reads from environment variables.

    `MIGRATIONS_DATABASE_URL` connects as the owner role.
    It is kept apart from `Settings`, so a service never needs the owner's credentials to start.
    """

    migrations_database_url: str


@cache
def get_settings() -> Settings:
    """Return the settings, read from the environment on first call."""
    return Settings()  # type: ignore[call-arg]  # pydantic-settings fills the fields from env vars


@cache
def get_migration_settings() -> MigrationSettings:
    """Return the migration settings, read from the environment on first call."""
    return MigrationSettings()  # type: ignore[call-arg]  # pydantic-settings fills the fields from env vars
