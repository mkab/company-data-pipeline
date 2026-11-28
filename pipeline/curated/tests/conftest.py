from datetime import date
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from pipeline.curated.tests.factories import CompanyFactory, CompanyTickerFactory, FilingFactory
from pipeline.tests.roles import clear_database_caches, connecting_as, role_database_url

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def api_session() -> AsyncIterator[AsyncSession]:
    """Yield a session as the api role, which reads the curated tables as the API does."""
    async with connecting_as("api") as engine, async_sessionmaker(engine).begin() as session:
        yield session


@pytest.fixture
def drift_check_as_api(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Point `DATABASE_URL` at the api role, as `make curated-drift` runs.

    `main` runs its own event loop and disposes of the engine itself.
    """
    monkeypatch.setenv("DATABASE_URL", role_database_url("api"))
    clear_database_caches()
    yield
    clear_database_caches()


@pytest.fixture
async def three_companies(dbt_session: AsyncSession) -> None:
    """Apple and Microsoft, tracked, and Alphabet, untracked with two tickers, in no CIK order."""
    dbt_session.add_all(
        [
            CompanyFactory.build(cik=789019, name="Microsoft Corp", is_tracked=True),
            CompanyFactory.build(
                cik=320193,
                name="Apple Inc.",
                is_tracked=True,
                entity_type="operating",
                sic="3571",
                sic_description="Electronic Computers",
                fiscal_year_end="0926",
                state_of_incorporation="CA",
            ),
            CompanyFactory.build(cik=1652044, name="Alphabet Inc.", is_tracked=False),
            CompanyTickerFactory.build(cik=789019, ticker="MSFT", exchange="Nasdaq"),
            CompanyTickerFactory.build(cik=320193, ticker="AAPL", exchange="Nasdaq"),
            CompanyTickerFactory.build(cik=1652044, ticker="GOOGL", exchange="Nasdaq"),
            CompanyTickerFactory.build(cik=1652044, ticker="GOOG", exchange="Nasdaq"),
        ]
    )
    await dbt_session.commit()


@pytest.fixture
async def apple_filings(dbt_session: AsyncSession) -> None:
    """Four Apple filings, two of them filed the same day, and one Microsoft filing."""
    dbt_session.add_all(
        [
            FilingFactory.build(
                cik=320193,
                accession_number="0000320193-25-000073",
                form="10-Q",
                filing_date=date(2025, 8, 1),
            ),
            FilingFactory.build(
                cik=320193,
                accession_number="0000320193-25-000079",
                form="10-K",
                filing_date=date(2025, 10, 31),
            ),
            FilingFactory.build(
                cik=320193,
                accession_number="0001140361-25-040270",
                form="4",
                filing_date=date(2025, 10, 31),
            ),
            FilingFactory.build(
                cik=320193,
                accession_number="0000320193-25-000057",
                form="10-Q",
                filing_date=date(2025, 5, 2),
            ),
            FilingFactory.build(
                cik=789019,
                accession_number="0000950170-25-100235",
                form="10-K",
                filing_date=date(2025, 7, 30),
            ),
        ]
    )
    await dbt_session.commit()
