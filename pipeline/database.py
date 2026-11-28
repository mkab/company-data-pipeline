from contextlib import asynccontextmanager
from datetime import datetime
from functools import cache
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from pipeline.settings import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from alembic.runtime.environment import NameFilterParentNames, NameFilterType
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

# Alembic manages these schemas only.
# dbt creates and owns `staging` and `curated`, so autogenerate must never touch them
RAW_SCHEMA = "raw"
ALEMBIC_SCHEMAS = frozenset({RAW_SCHEMA})

# dbt builds the tables of this schema, and the API reads them
CURATED_SCHEMA = "curated"

# Named constraints let a later migration refer to them, as the recipes in docs/migrations.md do
NAMING_CONVENTION = {
    "ix": "%(table_name)s_%(column_0_N_name)s_index",
    "uq": "%(table_name)s_%(column_0_N_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_N_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

# The tables Alembic manages are declared on this metadata
alembic_metadata = MetaData(naming_convention=NAMING_CONVENTION)


class ModelBase(DeclarativeBase):
    """The base of every table: tables are declarative models that inherit from it.

    It carries the standard columns of `CODING_STANDARDS.md`,
    so every model gets them without declaring them.
    """

    metadata = alembic_metadata

    # A negative sort order puts the standard columns first, ahead of each model's own
    id: Mapped[int] = mapped_column(sa.BigInteger, sa.Identity(), primary_key=True, sort_order=-4)
    uuid: Mapped[UUID] = mapped_column(
        server_default=sa.text("gen_random_uuid()"), unique=True, sort_order=-3
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), sort_order=-2
    )
    modified_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        sort_order=-1,
    )


# The curated tables are declared on their own metadata, which Alembic never sees.
# They exist to be read, and the drift check compares them with what dbt built
curated_metadata = MetaData(schema=CURATED_SCHEMA)


class CuratedModelBase(DeclarativeBase):
    """The base of every curated table, which dbt builds and the API reads.

    Unlike `ModelBase`, it adds no standard columns:
    dbt rebuilds the tables every run, so a row has only its natural key, and no `id` or `uuid`.
    """

    metadata = curated_metadata


@cache
def get_engine() -> AsyncEngine:
    """Return the engine for `DATABASE_URL`, created on first call."""
    return create_async_engine(get_settings().database_url)


@cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the session factory over `get_engine()`, created on first call."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Yield a session in one transaction: committed on success, rolled back on error.

    The error is re-raised, never swallowed.
    The outermost caller opens it (a route dependency, or a usecase),
    so services and repositories take the session and never commit.
    """
    async with get_sessionmaker().begin() as session:
        yield session


async def ping_database(session: AsyncSession) -> None:
    """Run `SELECT 1`,
    which raises `sqlalchemy.exc.DBAPIError` when the database is unreachable.
    """
    await session.execute(sa.select(1))


def include_managed_schemas(
    name: str | None, type_: NameFilterType, parent_names: NameFilterParentNames
) -> bool:
    """Keep autogenerate from reflecting any schema Alembic does not manage.

    `None` is the default schema, which Alembic keeps so a table declared without a schema is still compared.
    Names below a schema follow it, since autogenerate only reflects the schemas it keeps.
    """
    if type_ != "schema":
        return True
    return name is None or name in ALEMBIC_SCHEMAS
