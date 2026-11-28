from typing import Annotated

from fastapi import Depends

# FastAPI reads a dependency's signature at runtime
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from pipeline.api.dependencies import get_session
from pipeline.curated.services import CompanyService


def company_service(session: Annotated[AsyncSession, Depends(get_session)]) -> CompanyService:
    """Return the company service over the request's session."""
    return CompanyService.from_session(session)
