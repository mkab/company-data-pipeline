from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.api.pagination.types import PageRequest
    from pipeline.curated.types import (
        CompanyDetails,
        CompanyFilters,
        CompanySortKey,
        CompanySummary,
        FilingDetails,
        FilingFilters,
        FilingSortKey,
    )


class FakeCompanyRepository:
    """Holds companies in memory, and lists every one of them whatever the filters and page."""

    def __init__(self, companies: list[CompanyDetails]) -> None:
        self.companies = companies

    async def list_companies(
        self, filters: CompanyFilters, page: PageRequest[CompanySortKey]
    ) -> list[CompanySummary]:
        return list(self.companies)

    async def get_company(self, cik: int) -> CompanyDetails | None:
        for company in self.companies:
            if company.cik == cik:
                return company
        return None

    async def company_exists(self, cik: int) -> bool:
        return await self.get_company(cik) is not None


class FakeFilingRepository:
    """Holds filings in memory, and lists a company's, whatever the filters and page."""

    def __init__(self, filings: list[FilingDetails]) -> None:
        self.filings = filings

    async def list_filings(
        self, cik: int, filters: FilingFilters, page: PageRequest[FilingSortKey]
    ) -> list[FilingDetails]:
        return [filing for filing in self.filings if filing.cik == cik]
