from datetime import UTC, date, datetime

import pytest

from pipeline.api.pagination.types import PageRequest
from pipeline.curated.exceptions import CompanyNotFoundError
from pipeline.curated.services import CompanyService
from pipeline.curated.tests.fakes import FakeCompanyRepository, FakeFilingRepository
from pipeline.curated.types import (
    CompanyDetails,
    CompanyFilters,
    CompanySortKey,
    FilingDetails,
    FilingFilters,
    FilingSortKey,
    Ticker,
)

pytestmark = pytest.mark.anyio

APPLE = CompanyDetails(
    cik=320193,
    name="Apple Inc.",
    is_tracked=True,
    tickers=[Ticker(ticker="AAPL", exchange="Nasdaq")],
    entity_type="operating",
    sic="3571",
    sic_description="Electronic Computers",
    fiscal_year_end="0926",
    state_of_incorporation="CA",
)
APPLE_10K = FilingDetails(
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
)
FIRST_COMPANY_PAGE = PageRequest[CompanySortKey](limit=100, after=None)
FIRST_FILING_PAGE = PageRequest[FilingSortKey](limit=100, after=None)


def service_over(companies: list[CompanyDetails], filings: list[FilingDetails]) -> CompanyService:
    return CompanyService(FakeCompanyRepository(companies), FakeFilingRepository(filings))


async def test_list_companies_returns_the_listed_companies() -> None:
    service = service_over([APPLE], [])

    assert await service.list_companies(CompanyFilters(), FIRST_COMPANY_PAGE) == [APPLE]


async def test_get_company_returns_the_company() -> None:
    assert await service_over([APPLE], []).get_company(320193) == APPLE


async def test_get_company_raises_for_an_unknown_cik() -> None:
    with pytest.raises(CompanyNotFoundError):
        await service_over([APPLE], []).get_company(789019)


async def test_list_filings_returns_the_company_s_filings() -> None:
    service = service_over([APPLE], [APPLE_10K])

    assert await service.list_filings(320193, FilingFilters(), FIRST_FILING_PAGE) == [APPLE_10K]


async def test_list_filings_is_empty_for_a_company_with_no_filings() -> None:
    service = service_over([APPLE], [])

    assert await service.list_filings(320193, FilingFilters(), FIRST_FILING_PAGE) == []


async def test_list_filings_raises_for_an_unknown_cik() -> None:
    service = service_over([APPLE], [APPLE_10K])

    with pytest.raises(CompanyNotFoundError):
        await service.list_filings(789019, FilingFilters(), FIRST_FILING_PAGE)
