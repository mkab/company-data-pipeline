from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import pytest

from pipeline.curated.tests.factories import CompanyFactory, CompanyTickerFactory, FilingFactory

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def apple_and_microsoft(dbt_session: AsyncSession) -> None:
    """Apple, tracked with its details, and Microsoft, untracked, one ticker each."""
    dbt_session.add_all(
        [
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
            CompanyFactory.build(cik=789019, name="Microsoft Corp", is_tracked=False),
            CompanyTickerFactory.build(cik=320193, ticker="AAPL", exchange="Nasdaq"),
            CompanyTickerFactory.build(cik=789019, ticker="MSFT", exchange="Nasdaq"),
        ]
    )
    await dbt_session.commit()


@pytest.fixture
async def apple_10k_and_10q(dbt_session: AsyncSession) -> None:
    """Apple with its 10-K of 2025-10-31, every column set, and its 10-Q of 2025-08-01."""
    dbt_session.add_all(
        [
            CompanyFactory.build(cik=320193),
            FilingFactory.build(
                cik=320193,
                accession_number="0000320193-25-000079",
                form="10-K",
                filing_date=date(2025, 10, 31),
                report_date=date(2025, 9, 27),
                accepted_at=datetime(2025, 10, 31, 10, 1, 26, tzinfo=UTC),
                primary_document="aapl-20250927.htm",
                is_xbrl=True,
                is_inline_xbrl=True,
                filing_url=(
                    "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/"
                    "0000320193-25-000079-index.htm"
                ),
            ),
            FilingFactory.build(
                cik=320193,
                accession_number="0000320193-25-000073",
                form="10-Q",
                filing_date=date(2025, 8, 1),
            ),
        ]
    )
    await dbt_session.commit()
