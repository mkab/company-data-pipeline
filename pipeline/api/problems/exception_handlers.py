from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from pipeline.api.problems.constants import INVALID_REQUEST_DETAIL, PROBLEM_MEDIA_TYPE
from pipeline.api.problems.titles import status_title
from pipeline.api.problems.types import InvalidParameter, ProblemDetail, ValidationProblem

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fastapi import FastAPI, Request


def problem_response(
    problem: ProblemDetail, headers: Mapping[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        problem.model_dump(mode="json"),
        status_code=problem.status,
        headers=headers,
        media_type=PROBLEM_MEDIA_TYPE,
    )


async def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    """Serve an `HTTPException` as a problem.

    Starlette's own (an unknown path, a wrong method) carry the status phrase as their detail,
    which comes out in sentence case.
    A detail of ours is written in sentence case already,
    and kept as it is, so a concept name such as `Revenues` keeps its case.
    """
    is_status_phrase = error.detail == HTTPStatus(error.status_code).phrase
    problem = ProblemDetail(
        title=status_title(error.status_code),
        status=error.status_code,
        detail=status_title(error.status_code) if is_status_phrase else error.detail,
    )
    return problem_response(problem, headers=error.headers)


async def validation_exception_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Serve a request validation error (a bad path, query or body parameter) as a 422 problem."""
    problem = ValidationProblem(
        title=status_title(HTTPStatus.UNPROCESSABLE_CONTENT),
        status=HTTPStatus.UNPROCESSABLE_CONTENT,
        detail=INVALID_REQUEST_DETAIL,
        errors=[
            InvalidParameter(location=list(invalid["loc"]), message=invalid["msg"])
            for invalid in error.errors()
        ],
    )
    return problem_response(problem)


def add_exception_handlers(app: FastAPI) -> None:
    # Starlette types a handler as taking any `Exception`,
    # though it only ever calls one with the class it is registered for
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
