"""Create the curated tables in the test database from their declaration, and empty them.

pytest never runs dbt, so the tests read tables built from `curated_metadata`,
which the drift check keeps equal to dbt's.
They are created as the dbt role, so they belong to it as dbt's do,
and `make dbt ARGS="build --target test"` can still replace them.
"""

import sqlalchemy as sa

import pipeline.curated.models  # noqa: F401  # registers the curated tables on `curated_metadata`
from pipeline.database import CURATED_SCHEMA, curated_metadata
from pipeline.tests.roles import connecting_as

# What dbt grants the api role: SELECT on each model (`grants` config) and usage on the schema (on-run-end)
API_GRANTS = (
    sa.text("GRANT USAGE ON SCHEMA curated TO api"),
    sa.text("GRANT SELECT ON ALL TABLES IN SCHEMA curated TO api"),
)


async def create_curated_tables() -> None:
    """Replace the curated tables with empty ones built from `curated_metadata`, and grant the api role."""
    async with connecting_as("dbt") as engine, engine.begin() as connection:
        await connection.execute(sa.schema.CreateSchema(CURATED_SCHEMA, if_not_exists=True))
        await connection.run_sync(curated_metadata.drop_all)
        await connection.run_sync(curated_metadata.create_all)
        for grant in API_GRANTS:
            await connection.execute(grant)


async def empty_curated_tables() -> None:
    async with connecting_as("dbt") as engine, engine.begin() as connection:
        for table in curated_metadata.sorted_tables:
            await connection.execute(sa.delete(table))
