import asyncio
from logging.config import fileConfig
from typing import TYPE_CHECKING, Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from pipeline.database import alembic_metadata, include_managed_schemas
from pipeline.settings import get_migration_settings

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Shared by the offline and online runs.
# Only the schemas Alembic manages are reflected, so autogenerate never touches dbt's `staging` and `curated`
CONFIGURE_OPTIONS: dict[str, Any] = {
    "target_metadata": alembic_metadata,
    "include_schemas": True,
    "include_name": include_managed_schemas,
}


def run_migrations_offline() -> None:
    """Emit the migrations as SQL, without a database connection."""
    context.configure(
        url=get_migration_settings().migrations_database_url,
        **CONFIGURE_OPTIONS,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        **CONFIGURE_OPTIONS,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(
        get_migration_settings().migrations_database_url, poolclass=pool.NullPool
    )
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
