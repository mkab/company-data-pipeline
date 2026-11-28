from typing import TYPE_CHECKING

import pytest

from pipeline.api.problems.tests.apps import app_raising_a_404_of_ours, app_with_a_query_parameter
from pipeline.api.tests.clients import client_for

if TYPE_CHECKING:
    from httpx2 import AsyncClient

pytestmark = pytest.mark.anyio


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


async def test_a_detail_of_ours_keeps_its_case() -> None:
    async with client_for(app_raising_a_404_of_ours()) as client:
        response = await client.get("/concepts/revenues")

    assert response.json() == {
        "type": "about:blank",
        "title": "Not found",
        "status": 404,
        "detail": "No concept us-gaap/Revenues",
    }


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
