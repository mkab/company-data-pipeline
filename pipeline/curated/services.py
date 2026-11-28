from typing import TYPE_CHECKING

from pipeline.curated.exceptions import CompanyNotFoundError
from pipeline.curated.repositories import PostgresCompanyRepository, PostgresFilingRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pipeline.curated.protocols import CompanyRepository, FilingRepository
    from pipeline.curated.types import (
        CompanyDetails,
        CompanyFilters,
        CompanySortKey,
        CompanySummary,
        FilingDetails,
        FilingFilters,
        FilingSortKey,
    )
    from pipeline.pagination.types import PageRequest


class CompanyService:
    """Reads companies and their filings through the repository Protocols, so unit tests can pass fakes.

    Each list returns up to `page.limit + 1` rows, the extra one telling `build_page` another page follows.
    """

    def __init__(self, companies: CompanyRepository, filings: FilingRepository) -> None:
        self.companies = companies
        self.filings = filings

    @classmethod
    def from_session(cls, session: AsyncSession) -> CompanyService:
        return cls(PostgresCompanyRepository(session), PostgresFilingRepository(session))

    async def list_companies(
        self, filters: CompanyFilters, page: PageRequest[CompanySortKey]
    ) -> list[CompanySummary]:
        return await self.companies.list_companies(filters, page)

    async def get_company(self, cik: int) -> CompanyDetails:
        """Return the company with this CIK.

        Raises `CompanyNotFoundError` when there is none.
        """
        company = await self.companies.get_company(cik)
        if company is None:
            raise CompanyNotFoundError(cik)
        return company

    async def list_filings(
        self, cik: int, filters: FilingFilters, page: PageRequest[FilingSortKey]
    ) -> list[FilingDetails]:
        """Return the company's filings, none for a company that has filed nothing.

        Raises `CompanyNotFoundError` when no company has this CIK.
        """
        if not await self.companies.company_exists(cik):
            raise CompanyNotFoundError(cik)
        return await self.filings.list_filings(cik, filters, page)
