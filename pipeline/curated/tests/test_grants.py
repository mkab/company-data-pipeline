"""The api role reads the curated tables and writes none, as dbt grants them."""

from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError

from pipeline.curated.models import Company, CompanyTicker, Concept, Fact, Filing
from pipeline.curated.tests.factories import (
    CompanyFactory,
    CompanyTickerFactory,
    ConceptFactory,
    FactFactory,
    FilingFactory,
)
from pipeline.tests.roles import connecting_as

if TYPE_CHECKING:
    from factory.base import Factory
    from sqlalchemy.ext.asyncio import AsyncSession

    from pipeline.database import CuratedModelBase

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    ("factory", "model"),
    [
        (CompanyFactory, Company),
        (CompanyTickerFactory, CompanyTicker),
        (FilingFactory, Filing),
        (ConceptFactory, Concept),
        (FactFactory, Fact),
    ],
)
async def test_the_api_role_reads_a_curated_row(
    dbt_session: AsyncSession,
    factory: type[Factory[CuratedModelBase]],
    model: type[CuratedModelBase],
) -> None:
    dbt_session.add(factory.build())
    await dbt_session.commit()

    async with connecting_as("api") as engine, engine.connect() as connection:
        count = await connection.scalar(sa.select(sa.func.count()).select_from(model))

    assert count == 1


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO curated.companies (cik) VALUES (1)",
        "UPDATE curated.facts SET value = 0",
        "DELETE FROM curated.filings",
    ],
)
async def test_the_api_role_is_refused_a_write(statement: str) -> None:
    async with connecting_as("api") as engine, engine.begin() as connection:
        with pytest.raises(ProgrammingError, match="permission denied"):
            await connection.execute(sa.text(statement))
