from typing import TYPE_CHECKING, Protocol

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


class CompanyRepository(Protocol):
    """The company reads a service depends on: Postgres in the application, a fake in unit tests."""

    async def list_companies(
        self, filters: CompanyFilters, page: PageRequest[CompanySortKey]
    ) -> list[CompanySummary]:
        """Return up to `page.limit + 1` companies after `page.after`, sorted by CIK."""
        ...

    async def get_company(self, cik: int) -> CompanyDetails | None:
        """Return the company with this CIK, or `None` when there is none."""
        ...

    async def company_exists(self, cik: int) -> bool: ...


class FilingRepository(Protocol):
    """The filing reads a service depends on: Postgres in the application, a fake in unit tests."""

    async def list_filings(
        self, cik: int, filters: FilingFilters, page: PageRequest[FilingSortKey]
    ) -> list[FilingDetails]:
        """Return up to `page.limit + 1` filings of the company after `page.after`, newest first."""
        ...
