from sqlalchemy import MetaData

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
