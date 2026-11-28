from datetime import date

import pytest

from pipeline.api.pagination.cursors import encode_cursor
from pipeline.api.pagination.tests.apps import app_with_a_paginated_list
from pipeline.api.pagination.tests.types import FilingSortKey
from pipeline.api.tests.clients import client_for

pytestmark = pytest.mark.anyio


async def test_the_dependency_defaults_to_the_first_page_of_100() -> None:
    async with client_for(app_with_a_paginated_list()) as client:
        response = await client.get("/filings")

    assert response.status_code == 200
    assert response.json() == {"limit": 100, "after": None}


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


async def test_the_dependency_rejects_a_tampered_cursor_with_a_422() -> None:
    async with client_for(app_with_a_paginated_list()) as client:
        response = await client.get("/filings", params={"cursor": "bm90IGpzb24="})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["errors"] == [
        {"location": ["query", "cursor"], "message": "Cursor is not one a previous page returned"}
    ]


@pytest.mark.parametrize("limit", ["0", "1001", "ten"])
async def test_the_dependency_rejects_a_limit_outside_1_to_1000_with_a_422(limit: str) -> None:
    async with client_for(app_with_a_paginated_list()) as client:
        response = await client.get("/filings", params={"limit": limit})

    assert response.status_code == 422
    assert response.json()["errors"][0]["location"] == ["query", "limit"]
