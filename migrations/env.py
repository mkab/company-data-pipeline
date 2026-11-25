import asyncio
from logging.config import fileConfig
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy import Table, pool
from sqlalchemy.ext.asyncio import create_async_engine

from pipeline.database import ALEMBIC_SCHEMAS, alembic_metadata
from pipeline.settings import get_migration_settings

if TYPE_CHECKING:
    from alembic.runtime.environment import NameFilterType
    from sqlalchemy.engine import Connection
    from sqlalchemy.schema import SchemaItem

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def include_object(
    item: SchemaItem,
    name: str | None,
    type_: NameFilterType,
    reflected: bool,
    compare_to: SchemaItem | None,
) -> bool:
    """Keep autogenerate to the tables in the schemas Alembic manages.

    The objects inside a table follow it, since autogenerate only compares the tables it keeps.
    """
    if not isinstance(item, Table):
        return True
    return item.schema in ALEMBIC_SCHEMAS


def run_migrations_offline() -> None:
    """Emit the migrations as SQL, without a database connection."""
    context.configure(
        url=get_migration_settings().migrations_database_url,
        target_metadata=alembic_metadata,
        include_schemas=True,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=alembic_metadata,
        include_schemas=True,
        include_object=include_object,
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
