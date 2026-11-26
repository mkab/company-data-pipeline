from typing import TYPE_CHECKING

from sqlalchemy import MetaData

if TYPE_CHECKING:
    from alembic.runtime.environment import NameFilterParentNames, NameFilterType

# Alembic manages these schemas only.
# dbt creates and owns `staging` and `curated`, so autogenerate must never touch them
ALEMBIC_SCHEMAS = frozenset({"raw"})

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
