from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from pipeline.api.cik import cik_from_path, padded_cik
from pipeline.api.companies.constants import COMPANY_NOT_FOUND_DETAIL
from pipeline.api.companies.dependencies import company_service
from pipeline.api.pagination.dependencies import page_request
from pipeline.api.pagination.pages import build_page

# FastAPI reads the route signatures at runtime
from pipeline.api.pagination.types import Page, PageRequest  # noqa: TC001
from pipeline.api.problems.types import ProblemDetail
from pipeline.curated.exceptions import CompanyNotFoundError
from pipeline.curated.services import CompanyService  # noqa: TC001
from pipeline.curated.types import (
    CompanyDetails,  # noqa: TC001
    CompanyFilters,  # noqa: TC001
    CompanySortKey,
    CompanySummary,
    FilingDetails,
    FilingFilters,  # noqa: TC001
    FilingSortKey,
)

router = APIRouter(prefix="/companies", tags=["companies"])

UNKNOWN_CIK_RESPONSES: dict[int | str, dict[str, Any]] = {
    HTTPStatus.NOT_FOUND: {"model": ProblemDetail}
}


def company_not_found(error: CompanyNotFoundError) -> HTTPException:
    detail = COMPANY_NOT_FOUND_DETAIL.format(cik=padded_cik(error.cik))
    return HTTPException(HTTPStatus.NOT_FOUND, detail=detail)


@router.get("")
async def list_companies(
    filters: Annotated[CompanyFilters, Query()],
    page: Annotated[PageRequest[CompanySortKey], Depends(page_request(CompanySortKey))],
    service: Annotated[CompanyService, Depends(company_service)],
) -> Page[CompanySummary]:
    """List companies by CIK, each with every one of its tickers."""
    companies = await service.list_companies(filters, page)
    return build_page(companies, page, CompanySummary.sort_key)


@router.get("/{cik}", responses=UNKNOWN_CIK_RESPONSES)
async def get_company(
    cik: Annotated[int, Depends(cik_from_path)],
    service: Annotated[CompanyService, Depends(company_service)],
) -> CompanyDetails:
    """Return a company, with the details only a tracked company has."""
    try:
        return await service.get_company(cik)
    except CompanyNotFoundError as error:
        raise company_not_found(error) from error


@router.get("/{cik}/filings", responses=UNKNOWN_CIK_RESPONSES)
async def list_filings(
    cik: Annotated[int, Depends(cik_from_path)],
    filters: Annotated[FilingFilters, Query()],
    page: Annotated[PageRequest[FilingSortKey], Depends(page_request(FilingSortKey))],
    service: Annotated[CompanyService, Depends(company_service)],
) -> Page[FilingDetails]:
    """List a company's filings, newest first."""
    try:
        filings = await service.list_filings(cik, filters, page)
    except CompanyNotFoundError as error:
        raise company_not_found(error) from error
    return build_page(filings, page, FilingDetails.sort_key)
