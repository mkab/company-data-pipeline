"""Every error response is an RFC 9457 problem detail, served as `application/problem+json`."""

from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fastapi import FastAPI, Request

PROBLEM_MEDIA_TYPE = "application/problem+json"

# RFC 9457: a problem with no type of its own is `about:blank`, and its title is the status phrase
BLANK_PROBLEM_TYPE = "about:blank"

INVALID_REQUEST_DETAIL = "One or more request parameters are not valid"


class ProblemDetail(BaseModel):
    type: str = BLANK_PROBLEM_TYPE
    title: str
    status: int
    detail: str


class InvalidParameter(BaseModel):
    """One parameter a validation error names: where it is (such as `["query", "limit"]`), and why."""

    location: list[str | int]
    message: str


class ValidationProblem(ProblemDetail):
    """A 422, with the `errors` extension member listing each invalid parameter."""

    errors: list[InvalidParameter]


def sentence_case(phrase: str) -> str:
    """Return the phrase in sentence case, keeping its first word and every acronym as they are.

    `"Not Found"` becomes `"Not found"`, and `"HTTP Version Not Supported"` becomes `"HTTP version not supported"`.
    """
    first_word, *other_words = phrase.split(" ")
    words = [first_word]
    for word in other_words:
        words.append(word if word.isupper() else word.lower())
    return " ".join(words)


def status_title(status: int) -> str:
    return sentence_case(HTTPStatus(status).phrase)


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
    which comes out in sentence case like a detail of ours.
    """
    problem = ProblemDetail(
        title=status_title(error.status_code),
        status=error.status_code,
        detail=sentence_case(error.detail),
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


def add_problem_handlers(app: FastAPI) -> None:
    # Starlette types a handler as taking any `Exception`,
    # though it only ever calls one with the class it is registered for
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
