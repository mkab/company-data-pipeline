from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa

from pipeline.curated.drift import (
    built_columns,
    declared_columns,
    describe_drift,
    main,
    report_drift,
)
from pipeline.curated.types import ColumnShape
from pipeline.database import CURATED_SCHEMA, curated_metadata
from pipeline.tests.roles import connecting_as

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection

COMPANY_CIK = ColumnShape(table="companies", column="cik", data_type="bigint", is_nullable=False)
COMPANY_NAME = ColumnShape(table="companies", column="name", data_type="text", is_nullable=True)


@pytest.mark.parametrize(
    "shape",
    [
        ColumnShape(table="companies", column="cik", data_type="bigint", is_nullable=False),
        ColumnShape(table="company_tickers", column="ticker", data_type="text", is_nullable=False),
        ColumnShape(
            table="filings",
            column="accepted_at",
            data_type="timestamp with time zone",
            is_nullable=True,
        ),
        ColumnShape(table="facts", column="value", data_type="numeric", is_nullable=True),
        ColumnShape(table="facts", column="fiscal_year", data_type="integer", is_nullable=True),
        ColumnShape(table="facts", column="period_start", data_type="date", is_nullable=True),
        ColumnShape(table="filings", column="is_xbrl", data_type="boolean", is_nullable=True),
    ],
)
def test_declared_columns_name_types_as_information_schema_does(shape: ColumnShape) -> None:
    assert shape in declared_columns(curated_metadata, sa.create_engine("postgresql://").dialect)


def test_describe_drift_is_empty_when_the_columns_match() -> None:
    assert describe_drift({COMPANY_CIK, COMPANY_NAME}, {COMPANY_CIK, COMPANY_NAME}) == []


def test_describe_drift_shows_a_renamed_column_twice() -> None:
    renamed = ColumnShape(
        table="companies", column="company_name", data_type="text", is_nullable=True
    )

    assert describe_drift({COMPANY_CIK, COMPANY_NAME}, {COMPANY_CIK, renamed}) == [
        "Declared but not built: companies.name text null",
        "Built but not declared: companies.company_name text null",
    ]


def test_describe_drift_shows_a_changed_type() -> None:
    retyped = ColumnShape(table="companies", column="cik", data_type="integer", is_nullable=False)

    assert describe_drift({COMPANY_CIK}, {retyped}) == [
        "Declared but not built: companies.cik bigint not null",
        "Built but not declared: companies.cik integer not null",
    ]


def test_describe_drift_shows_a_changed_nullability() -> None:
    nullable = ColumnShape(table="companies", column="cik", data_type="bigint", is_nullable=True)

    assert describe_drift({COMPANY_CIK}, {nullable}) == [
        "Declared but not built: companies.cik bigint not null",
        "Built but not declared: companies.cik bigint null",
    ]


def test_report_drift_exits_with_status_1_on_any_drift() -> None:
    with pytest.raises(SystemExit) as exit_info:
        report_drift(["Declared but not built: companies.name text null"])

    assert exit_info.value.code == 1


def test_report_drift_returns_when_there_is_none() -> None:
    report_drift([])


async def drift_seen_by(connection: AsyncConnection) -> list[str]:
    return describe_drift(
        declared_columns(curated_metadata, connection.dialect),
        await built_columns(connection, CURATED_SCHEMA),
    )


@pytest.mark.anyio
async def test_the_tables_built_from_the_declaration_have_no_drift() -> None:
    async with connecting_as("api") as engine, engine.connect() as connection:
        assert await drift_seen_by(connection) == []


@pytest.mark.anyio
async def test_a_column_renamed_in_the_database_alone_is_drift() -> None:
    async with connecting_as("dbt") as engine, engine.connect() as connection:
        # Rolled back when the connection closes, so the table keeps its column
        await connection.execute(
            sa.text("ALTER TABLE curated.companies RENAME COLUMN name TO company_name")
        )

        drift = await drift_seen_by(connection)

    assert drift == [
        "Declared but not built: companies.name text null",
        "Built but not declared: companies.company_name text null",
    ]


@pytest.mark.usefixtures("drift_check_as_api")
def test_main_finds_no_drift_in_the_test_database() -> None:
    main()
