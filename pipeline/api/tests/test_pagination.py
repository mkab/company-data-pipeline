from datetime import date
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from pydantic import BaseModel

from pipeline.api.pagination import (
    InvalidCursorError,
    Page,
    PageRequest,
    build_page,
    decode_cursor,
    encode_cursor,
    page_request,
)
from pipeline.api.problems import add_problem_handlers
from pipeline.api.tests.conftest import client_for


class FilingSortKey(BaseModel):
    filing_date: date
    accession_number: str


class Filing(BaseModel):
    filing_date: date
    accession_number: str
    form: str


def filing_sort_key(filing: Filing) -> FilingSortKey:
    return FilingSortKey(filing_date=filing.filing_date, accession_number=filing.accession_number)


FIRST_FILING = Filing(
    filing_date=date(2025, 10, 31), accession_number="0000320193-25-000079", form="10-K"
)
SECOND_FILING = Filing(
    filing_date=date(2025, 8, 1), accession_number="0000320193-25-000073", form="10-Q"
)
THIRD_FILING = Filing(
    filing_date=date(2025, 5, 2), accession_number="0000320193-25-000057", form="10-Q"
)


def test_a_cursor_round_trips_its_sort_key() -> None:
    sort_key = FilingSortKey(filing_date=date(2025, 8, 1), accession_number="0000320193-25-000073")

    assert decode_cursor(encode_cursor(sort_key), FilingSortKey) == sort_key


@pytest.mark.parametrize(
    "cursor",
    [
        "not base64!",
        # Valid base64 of text that is not JSON
        "bm90IGpzb24=",
        # Valid base64 of JSON missing `accession_number`
        "eyJmaWxpbmdfZGF0ZSI6ICIyMDI1LTA4LTAxIn0=",
    ],
)
def test_a_tampered_cursor_does_not_decode(cursor: str) -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor(cursor, FilingSortKey)


def test_build_page_with_an_extra_row_points_at_the_last_row_kept() -> None:
    request = PageRequest[FilingSortKey](limit=2, after=None)

    page = build_page([FIRST_FILING, SECOND_FILING, THIRD_FILING], request, filing_sort_key)

    assert page.data == [FIRST_FILING, SECOND_FILING]
    assert page.next_cursor == encode_cursor(
        FilingSortKey(filing_date=date(2025, 8, 1), accession_number="0000320193-25-000073")
    )


def test_build_page_without_an_extra_row_is_the_last_page() -> None:
    request = PageRequest[FilingSortKey](limit=2, after=None)

    page = build_page([FIRST_FILING, SECOND_FILING], request, filing_sort_key)

    assert page == Page(data=[FIRST_FILING, SECOND_FILING], next_cursor=None)


class PageRequestResponse(BaseModel):
    limit: int
    after: FilingSortKey | None


def app_with_a_paginated_list() -> FastAPI:
    app = FastAPI()
    add_problem_handlers(app)

    @app.get("/filings")
    async def filings(
        page: Annotated[PageRequest[FilingSortKey], Depends(page_request(FilingSortKey))],
    ) -> PageRequestResponse:
        return PageRequestResponse(limit=page.limit, after=page.after)

    return app


@pytest.mark.anyio
async def test_the_dependency_defaults_to_the_first_page_of_100() -> None:
    async with client_for(app_with_a_paginated_list()) as client:
        response = await client.get("/filings")

    assert response.status_code == 200
    assert response.json() == {"limit": 100, "after": None}


@pytest.mark.anyio
async def test_the_dependency_round_trips_a_cursor() -> None:
    cursor = encode_cursor(
        FilingSortKey(filing_date=date(2025, 8, 1), accession_number="0000320193-25-000073")
    )

    async with client_for(app_with_a_paginated_list()) as client:
        response = await client.get("/filings", params={"limit": "1000", "cursor": cursor})

    assert response.status_code == 200
    assert response.json() == {
        "limit": 1000,
        "after": {"filing_date": "2025-08-01", "accession_number": "0000320193-25-000073"},
    }


@pytest.mark.anyio
async def test_the_dependency_rejects_a_tampered_cursor_with_a_422() -> None:
    async with client_for(app_with_a_paginated_list()) as client:
        response = await client.get("/filings", params={"cursor": "bm90IGpzb24="})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["errors"] == [
        {"location": ["query", "cursor"], "message": "Cursor is not one a previous page returned"}
    ]


@pytest.mark.anyio
@pytest.mark.parametrize("limit", ["0", "1001", "ten"])
async def test_the_dependency_rejects_a_limit_outside_1_to_1000_with_a_422(limit: str) -> None:
    async with client_for(app_with_a_paginated_list()) as client:
        response = await client.get("/filings", params={"limit": limit})

    assert response.status_code == 422
    assert response.json()["errors"][0]["location"] == ["query", "limit"]
