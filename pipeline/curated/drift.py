"""The curated drift check: `python -m pipeline.curated.drift`, run by `make curated-drift` in CI after `dbt build`.

It compares the columns dbt built in `curated` with the ones `pipeline.curated.models` declares,
by name, type and nullability, and fails on any difference,
so a dbt change the Python side does not follow fails CI instead of a request.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import sqlalchemy as sa

import pipeline.curated.models  # noqa: F401  # registers the curated tables on `curated_metadata`
from pipeline.database import CURATED_SCHEMA, curated_metadata, get_engine

if TYPE_CHECKING:
    from sqlalchemy import Dialect, MetaData
    from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

# Only the columns the connecting role may read are listed,
# so it runs as the api role, which reads every curated table
BUILT_COLUMNS_QUERY = sa.text(
    "SELECT table_name, column_name, data_type, is_nullable"
    " FROM information_schema.columns"
    " WHERE table_schema = :schema"
)


@dataclass(frozen=True, order=True)
class ColumnShape:
    """A column as PostgreSQL's `information_schema.columns` describes it, such as `bigint` for its type."""

    table: str
    column: str
    data_type: str
    is_nullable: bool

    def describe(self) -> str:
        nullability = "null" if self.is_nullable else "not null"
        return f"{self.table}.{self.column} {self.data_type} {nullability}"


def declared_columns(metadata: MetaData, dialect: Dialect) -> set[ColumnShape]:
    """Return the columns of every table on `metadata`, with their types as `dialect` names them.

    PostgreSQL's names, lowercased, are those of `information_schema`, such as `timestamp with time zone`.
    """
    shapes = set()
    for table in metadata.tables.values():
        for column in table.columns:
            shapes.add(
                ColumnShape(
                    table=table.name,
                    column=column.name,
                    data_type=column.type.compile(dialect=dialect).lower(),
                    is_nullable=column.nullable is True,
                )
            )
    return shapes


async def built_columns(connection: AsyncConnection, schema: str) -> set[ColumnShape]:
    """Return the columns of every table in `schema` the connecting role may read."""
    result = await connection.execute(BUILT_COLUMNS_QUERY, {"schema": schema})
    return {
        ColumnShape(
            table=row.table_name,
            column=row.column_name,
            data_type=row.data_type,
            is_nullable=row.is_nullable == "YES",
        )
        for row in result
    }


def describe_drift(declared: set[ColumnShape], built: set[ColumnShape]) -> list[str]:
    """Return one line per column that differs, sorted, or none when the two match.

    A renamed column or a changed type shows twice: declared but not built, and built but not declared.
    """
    not_built = [
        f"Declared but not built: {shape.describe()}" for shape in sorted(declared - built)
    ]
    not_declared = [
        f"Built but not declared: {shape.describe()}" for shape in sorted(built - declared)
    ]
    return not_built + not_declared


async def find_curated_drift() -> list[str]:
    engine = get_engine()
    try:
        async with engine.connect() as connection:
            built = await built_columns(connection, CURATED_SCHEMA)
    finally:
        await engine.dispose()
    return describe_drift(declared_columns(curated_metadata, engine.dialect), built)


def report_drift(drift: list[str]) -> None:
    """Log each difference, then exit with status 1 when there is any."""
    for line in drift:
        logger.error(line)
    if drift:
        raise SystemExit(1)
    logger.info("The curated tables match their declaration")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    report_drift(asyncio.run(find_curated_drift()))


if __name__ == "__main__":
    main()
