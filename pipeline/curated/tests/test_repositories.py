from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import pytest

from pipeline.api.pagination.types import PageRequest
from pipeline.curated.repositories import PostgresCompanyRepository, PostgresFilingRepository
from pipeline.curated.tests.factories import CompanyFactory, CompanyTickerFactory, FilingFactory
from pipeline.curated.types import (
    CompanyDetails,
    CompanyFilters,
    CompanySortKey,
    CompanySummary,
    FilingDetails,
    FilingFilters,
    FilingSortKey,
    Ticker,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pipeline.database import CuratedModelBase

pytestmark = pytest.mark.anyio

FIRST_COMPANY_PAGE = PageRequest[CompanySortKey](limit=100, after=None)
FIRST_FILING_PAGE = PageRequest[FilingSortKey](limit=100, after=None)
NO_COMPANY_FILTERS = CompanyFilters()
NO_FILING_FILTERS = FilingFilters()

APPLE_CIK = 320193


async def add_rows(dbt_session: AsyncSession, rows: list[CuratedModelBase]) -> None:
    dbt_session.add_all(rows)
    await dbt_session.commit()


async def listed_ciks(
    api_session: AsyncSession,
    filters: CompanyFilters = NO_COMPANY_FILTERS,
    page: PageRequest[CompanySortKey] = FIRST_COMPANY_PAGE,
) -> list[int]:
    companies = await PostgresCompanyRepository(api_session).list_companies(filters, page)
    return [company.cik for company in companies]


async def listed_accession_numbers(
    api_session: AsyncSession,
    filters: FilingFilters = NO_FILING_FILTERS,
    page: PageRequest[FilingSortKey] = FIRST_FILING_PAGE,
) -> list[str]:
    filings = await PostgresFilingRepository(api_session).list_filings(APPLE_CIK, filters, page)
    return [filing.accession_number for filing in filings]


async def test_list_companies_embeds_every_ticker_of_a_company_in_its_one_row(
    dbt_session: AsyncSession, api_session: AsyncSession
) -> None:
    await add_rows(
        dbt_session,
        [
            CompanyFactory.build(cik=1067983, name="Berkshire Hathaway Inc", is_tracked=False),
            CompanyTickerFactory.build(cik=1067983, ticker="BRK-B", exchange="NYSE"),
            CompanyTickerFactory.build(cik=1067983, ticker="BRK-A", exchange="NYSE"),
            CompanyTickerFactory.build(cik=1067983, ticker="BRK-PK", exchange=None),
        ],
    )

    companies = await PostgresCompanyRepository(api_session).list_companies(
        NO_COMPANY_FILTERS, FIRST_COMPANY_PAGE
    )

    assert companies == [
        CompanySummary(
            cik=1067983,
            name="Berkshire Hathaway Inc",
            is_tracked=False,
            tickers=[
                Ticker(ticker="BRK-A", exchange="NYSE"),
                Ticker(ticker="BRK-B", exchange="NYSE"),
                Ticker(ticker="BRK-PK", exchange=None),
            ],
        )
    ]


async def test_list_companies_embeds_no_tickers_for_a_company_without_any(
    dbt_session: AsyncSession, api_session: AsyncSession
) -> None:
    await add_rows(
        dbt_session,
        [CompanyFactory.build(cik=1000045, name="Nicholas Financial Inc", is_tracked=True)],
    )

    companies = await PostgresCompanyRepository(api_session).list_companies(
        NO_COMPANY_FILTERS, FIRST_COMPANY_PAGE
    )

    assert companies == [
        CompanySummary(cik=1000045, name="Nicholas Financial Inc", is_tracked=True, tickers=[])
    ]


@pytest.mark.usefixtures("three_companies")
async def test_list_companies_sorts_by_cik(api_session: AsyncSession) -> None:
    assert await listed_ciks(api_session) == [320193, 789019, 1652044]


@pytest.mark.usefixtures("three_companies")
async def test_list_companies_fetches_one_row_more_than_the_limit(
    api_session: AsyncSession,
) -> None:
    ciks = await listed_ciks(api_session, page=PageRequest(limit=1, after=None))

    assert ciks == [320193, 789019]


@pytest.mark.usefixtures("three_companies")
async def test_list_companies_resumes_after_the_cursor_in_cik_order(
    api_session: AsyncSession,
) -> None:
    ciks = await listed_ciks(
        api_session, page=PageRequest(limit=1, after=CompanySortKey(cik=320193))
    )

    assert ciks == [789019, 1652044]


@pytest.mark.usefixtures("three_companies")
async def test_list_companies_by_ticker_keeps_the_company_s_other_tickers(
    api_session: AsyncSession,
) -> None:
    companies = await PostgresCompanyRepository(api_session).list_companies(
        CompanyFilters(ticker="GOOG"), FIRST_COMPANY_PAGE
    )

    assert companies == [
        CompanySummary(
            cik=1652044,
            name="Alphabet Inc.",
            is_tracked=False,
            tickers=[
                Ticker(ticker="GOOG", exchange="Nasdaq"),
                Ticker(ticker="GOOGL", exchange="Nasdaq"),
            ],
        )
    ]


@pytest.mark.parametrize(("is_tracked", "ciks"), [(True, [320193, 789019]), (False, [1652044])])
@pytest.mark.usefixtures("three_companies")
async def test_list_companies_by_is_tracked(
    api_session: AsyncSession, is_tracked: bool, ciks: list[int]
) -> None:
    assert await listed_ciks(api_session, CompanyFilters(is_tracked=is_tracked)) == ciks


@pytest.mark.parametrize(
    ("name", "ciks"),
    [
        ("A", [320193, 1652044]),
        ("apple", [320193]),
        ("MICROSOFT CORP", [789019]),
        ("pple", []),
        # A LIKE wildcard is matched as itself, not as any text
        ("%", []),
        ("_pple", []),
    ],
)
@pytest.mark.usefixtures("three_companies")
async def test_list_companies_by_name_prefix_in_any_case(
    api_session: AsyncSession, name: str, ciks: list[int]
) -> None:
    assert await listed_ciks(api_session, CompanyFilters(name=name)) == ciks


@pytest.mark.usefixtures("three_companies")
async def test_get_company_returns_its_details_and_tickers(api_session: AsyncSession) -> None:
    company = await PostgresCompanyRepository(api_session).get_company(320193)

    assert company == CompanyDetails(
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


async def test_get_company_returns_none_for_an_unknown_cik(api_session: AsyncSession) -> None:
    assert await PostgresCompanyRepository(api_session).get_company(320193) is None


@pytest.mark.parametrize(("cik", "exists"), [(320193, True), (789019, False)])
async def test_company_exists(
    dbt_session: AsyncSession, api_session: AsyncSession, cik: int, exists: bool
) -> None:
    await add_rows(dbt_session, [CompanyFactory.build(cik=320193)])

    assert await PostgresCompanyRepository(api_session).company_exists(cik) is exists


async def test_list_filings_returns_every_curated_column(
    dbt_session: AsyncSession, api_session: AsyncSession
) -> None:
    await add_rows(
        dbt_session,
        [
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
            )
        ],
    )

    filings = await PostgresFilingRepository(api_session).list_filings(
        APPLE_CIK, NO_FILING_FILTERS, FIRST_FILING_PAGE
    )

    assert filings == [
        FilingDetails(
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
    ]


@pytest.mark.usefixtures("apple_filings")
async def test_list_filings_sorts_the_company_s_filings_by_date_then_accession_number_descending(
    api_session: AsyncSession,
) -> None:
    assert await listed_accession_numbers(api_session) == [
        "0001140361-25-040270",
        "0000320193-25-000079",
        "0000320193-25-000073",
        "0000320193-25-000057",
    ]


@pytest.mark.usefixtures("apple_filings")
async def test_list_filings_fetches_one_row_more_than_the_limit(api_session: AsyncSession) -> None:
    accession_numbers = await listed_accession_numbers(
        api_session, page=PageRequest(limit=1, after=None)
    )

    assert accession_numbers == ["0001140361-25-040270", "0000320193-25-000079"]


@pytest.mark.usefixtures("apple_filings")
async def test_list_filings_resumes_after_the_cursor_within_the_same_filing_date(
    api_session: AsyncSession,
) -> None:
    after = FilingSortKey(filing_date=date(2025, 10, 31), accession_number="0001140361-25-040270")

    accession_numbers = await listed_accession_numbers(
        api_session, page=PageRequest(limit=2, after=after)
    )

    assert accession_numbers == [
        "0000320193-25-000079",
        "0000320193-25-000073",
        "0000320193-25-000057",
    ]


@pytest.mark.usefixtures("apple_filings")
async def test_list_filings_by_form(api_session: AsyncSession) -> None:
    assert await listed_accession_numbers(api_session, FilingFilters(form="10-Q")) == [
        "0000320193-25-000073",
        "0000320193-25-000057",
    ]


@pytest.mark.parametrize(
    ("filters", "accession_numbers"),
    [
        (
            FilingFilters(filed_from=date(2025, 8, 1)),
            ["0001140361-25-040270", "0000320193-25-000079", "0000320193-25-000073"],
        ),
        (
            FilingFilters(filed_to=date(2025, 8, 1)),
            ["0000320193-25-000073", "0000320193-25-000057"],
        ),
        (
            FilingFilters(filed_from=date(2025, 8, 1), filed_to=date(2025, 8, 1)),
            ["0000320193-25-000073"],
        ),
    ],
)
@pytest.mark.usefixtures("apple_filings")
async def test_list_filings_by_filing_date_bounds_both_inclusive(
    api_session: AsyncSession,
    filters: FilingFilters,
    accession_numbers: list[str],
) -> None:
    assert await listed_accession_numbers(api_session, filters) == accession_numbers
