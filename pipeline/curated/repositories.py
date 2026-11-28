from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, aggregate_order_by

from pipeline.curated.models import Company, CompanyTicker, Filing
from pipeline.curated.types import CompanyDetails, CompanySummary, FilingDetails

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pipeline.api.pagination.types import PageRequest
    from pipeline.curated.types import (
        CompanyFilters,
        CompanySortKey,
        FilingFilters,
        FilingSortKey,
    )


def tickers_subquery() -> sa.ScalarSelect[object]:
    """Return the company's tickers as one JSON array, sorted by ticker, empty when it has none.

    A subquery of the company row, so a page of companies is one query.
    """
    ticker = sa.func.jsonb_build_object(
        "ticker", CompanyTicker.ticker, "exchange", CompanyTicker.exchange
    )
    return (
        sa.select(
            sa.func.coalesce(
                sa.func.jsonb_agg(aggregate_order_by(ticker, CompanyTicker.ticker)),
                sa.cast(sa.literal("[]"), JSONB),
            )
        )
        .where(CompanyTicker.cik == Company.cik)
        .correlate(Company)
        .scalar_subquery()
    )


def company_summary_query() -> sa.Select[int, str | None, bool | None, object]:
    """Return the query of the companies list's columns, which the company details add to."""
    return sa.select(
        Company.cik, Company.name, Company.is_tracked, tickers_subquery().label("tickers")
    )


class PostgresCompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_companies(
        self, filters: CompanyFilters, page: PageRequest[CompanySortKey]
    ) -> list[CompanySummary]:
        """Return up to `page.limit + 1` companies after `page.after`, sorted by CIK.

        The extra row tells `build_page` another page follows.
        """
        query = company_summary_query().order_by(Company.cik).limit(page.limit + 1)
        if page.after is not None:
            query = query.where(Company.cik > page.after.cik)
        if filters.ticker is not None:
            query = query.where(
                sa.exists().where(
                    CompanyTicker.cik == Company.cik, CompanyTicker.ticker == filters.ticker
                )
            )
        if filters.is_tracked is not None:
            query = query.where(Company.is_tracked == filters.is_tracked)
        if filters.name is not None:
            query = query.where(Company.name.istartswith(filters.name, autoescape=True))
        result = await self.session.execute(query)
        return [CompanySummary.model_validate(row) for row in result.mappings()]

    async def get_company(self, cik: int) -> CompanyDetails | None:
        query = company_summary_query().add_columns(
            Company.entity_type,
            Company.sic,
            Company.sic_description,
            Company.fiscal_year_end,
            Company.state_of_incorporation,
        )
        result = await self.session.execute(query.where(Company.cik == cik))
        row = result.mappings().one_or_none()
        if row is None:
            return None
        return CompanyDetails.model_validate(row)

    async def company_exists(self, cik: int) -> bool:
        result = await self.session.execute(sa.select(sa.exists().where(Company.cik == cik)))
        return result.scalar_one()


class PostgresFilingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_filings(
        self, cik: int, filters: FilingFilters, page: PageRequest[FilingSortKey]
    ) -> list[FilingDetails]:
        """Return up to `page.limit + 1` filings of the company after `page.after`.

        Sorted by filing date, then accession number, both descending.
        The extra row tells `build_page` another page follows.
        """
        query = (
            sa.select(Filing)
            .where(Filing.cik == cik)
            .order_by(Filing.filing_date.desc(), Filing.accession_number.desc())
            .limit(page.limit + 1)
        )
        if page.after is not None:
            query = query.where(
                sa.tuple_(Filing.filing_date, Filing.accession_number)
                < sa.tuple_(page.after.filing_date, page.after.accession_number)
            )
        if filters.form is not None:
            query = query.where(Filing.form == filters.form)
        if filters.filed_from is not None:
            query = query.where(Filing.filing_date >= filters.filed_from)
        if filters.filed_to is not None:
            query = query.where(Filing.filing_date <= filters.filed_to)
        filings = await self.session.scalars(query)
        return [FilingDetails.model_validate(filing, from_attributes=True) for filing in filings]
