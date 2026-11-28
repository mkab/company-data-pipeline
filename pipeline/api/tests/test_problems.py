from typing import TYPE_CHECKING, Annotated

import pytest
from fastapi import FastAPI, HTTPException, Query

from pipeline.api.problems import add_problem_handlers, sentence_case
from pipeline.api.tests.clients import client_for

if TYPE_CHECKING:
    from httpx2 import AsyncClient


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("Not Found", "Not found"),
        ("Service Unavailable", "Service unavailable"),
        ("HTTP Version Not Supported", "HTTP version not supported"),
        ("The database is unreachable", "The database is unreachable"),
    ],
)
def test_sentence_case_lowers_every_word_but_the_first_and_acronyms(
    phrase: str, expected: str
) -> None:
    assert sentence_case(phrase) == expected


@pytest.mark.anyio
async def test_an_unknown_path_is_a_404_problem(client: AsyncClient) -> None:
    response = await client.get("/v1/nothing-here")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Not found",
        "status": 404,
        "detail": "Not found",
    }


def app_with_a_query_parameter() -> FastAPI:
    app = FastAPI()
    add_problem_handlers(app)

    @app.get("/items")
    async def items(size: Annotated[int, Query(ge=1)]) -> dict[str, int]:
        return {"size": size}

    return app


@pytest.mark.anyio
async def test_a_bad_query_parameter_is_a_422_problem_in_sentence_case() -> None:
    async with client_for(app_with_a_query_parameter()) as client:
        response = await client.get("/items", params={"size": "0"})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "title": "Unprocessable content",
        "status": 422,
        "detail": "One or more request parameters are not valid",
        "errors": [
            {
                "location": ["query", "size"],
                "message": "Input should be greater than or equal to 1",
            }
        ],
    }


def app_raising_a_404_of_ours() -> FastAPI:
    app = FastAPI()
    add_problem_handlers(app)

    @app.get("/concepts/revenues")
    async def concept() -> None:
        raise HTTPException(404, detail="No concept us-gaap/Revenues")

    return app


@pytest.mark.anyio
async def test_a_detail_of_ours_keeps_its_case() -> None:
    async with client_for(app_raising_a_404_of_ours()) as client:
        response = await client.get("/concepts/revenues")

    assert response.json() == {
        "type": "about:blank",
        "title": "Not found",
        "status": 404,
        "detail": "No concept us-gaap/Revenues",
    }
