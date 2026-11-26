from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import MetaData

if TYPE_CHECKING:
    from alembic.runtime.environment import NameFilterParentNames, NameFilterType

# Alembic manages these schemas only.
# dbt creates and owns `staging` and `curated`, so autogenerate must never touch them
RAW_SCHEMA = "raw"
ALEMBIC_SCHEMAS = frozenset({RAW_SCHEMA})

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


def standard_columns() -> list[sa.Column[object]]:
    """Return the columns every table starts with (see `CODING_STANDARDS.md`)."""
    return [
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "uuid",
            sa.Uuid,
            server_default=sa.text("gen_random_uuid()"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


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
