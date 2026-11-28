from http import HTTPStatus
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import DBAPIError

# FastAPI reads the route signature at runtime
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from pipeline.api.dependencies import get_session
from pipeline.api.problems import ProblemDetail
from pipeline.database import ping_database

router = APIRouter(prefix="/health")

DATABASE_UNREACHABLE_DETAIL = "The database is unreachable"


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("")
async def health() -> HealthResponse:
    """Report that the process is up, without touching the database."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    responses={HTTPStatus.SERVICE_UNAVAILABLE: {"model": ProblemDetail}},
)
async def ready(session: Annotated[AsyncSession, Depends(get_session)]) -> HealthResponse:
    """Report that the API can serve requests: it reaches the database as its own role."""
    try:
        await ping_database(session)
    except DBAPIError as error:
        raise HTTPException(
            HTTPStatus.SERVICE_UNAVAILABLE, detail=DATABASE_UNREACHABLE_DETAIL
        ) from error
    return HealthResponse(status="ok")
