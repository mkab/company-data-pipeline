from functools import cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration read from environment variables.

    Each Compose service sets `DATABASE_URL` with its own role's credentials.
    `MIGRATIONS_DATABASE_URL` connects as the owner role, which runs the Alembic migrations.
    """

    database_url: str
    migrations_database_url: str


@cache
def get_settings() -> Settings:
    """Return the settings, read from the environment on first call."""
    return Settings()  # type: ignore[call-arg]  # pydantic-settings fills the fields from env vars
