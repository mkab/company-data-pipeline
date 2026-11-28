"""What the routes add over `CompanyService`: the response shape, status codes and the wiring.

The filters, ordering and paging themselves are tested at the queries (`pipeline/curated/tests`).
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx2 import AsyncClient

pytestmark = [pytest.mark.anyio, pytest.mark.usefixtures("database_url_as_api")]

UNKNOWN_CIK_PROBLEM = {
    "type": "about:blank",
    "title": "Not found",
    "status": 404,
    "detail": "No company has CIK 0000789019",
}


@pytest.mark.usefixtures("apple_and_microsoft")
async def test_list_companies_returns_a_page_of_companies_with_their_tickers(
    client: AsyncClient,
) -> None:
    response = await client.get("/v1/companies")

    assert response.status_code == 200
    assert response.json() == {
        "data": [
            {
                "cik": "0000320193",
                "name": "Apple Inc.",
                "is_tracked": True,
                "tickers": [{"ticker": "AAPL", "exchange": "Nasdaq"}],
            },
            {
                "cik": "0000789019",
                "name": "Microsoft Corp",
                "is_tracked": False,
                "tickers": [{"ticker": "MSFT", "exchange": "Nasdaq"}],
            },
        ],
        "next_cursor": None,
    }


@pytest.mark.usefixtures("apple_and_microsoft")
async def test_list_companies_resumes_from_the_next_cursor(client: AsyncClient) -> None:
    first_page = (await client.get("/v1/companies", params={"limit": "1"})).json()
    second_page = (
        await client.get(
            "/v1/companies", params={"limit": "1", "cursor": first_page["next_cursor"]}
        )
    ).json()

    assert first_page["data"][0]["cik"] == "0000320193"
    assert second_page["data"][0]["cik"] == "0000789019"
    assert second_page["next_cursor"] is None


@pytest.mark.parametrize(
    "params",
    [{"ticker": "MSFT"}, {"is_tracked": "false"}, {"name": "micro"}],
)
@pytest.mark.usefixtures("apple_and_microsoft")
async def test_list_companies_passes_each_filter_on(
    client: AsyncClient, params: dict[str, str]
) -> None:
    response = await client.get("/v1/companies", params=params)

    assert response.status_code == 200
    assert response.json()["data"][0]["cik"] == "0000789019"
    assert len(response.json()["data"]) == 1


async def test_list_companies_rejects_a_bad_filter_with_a_422(client: AsyncClient) -> None:
    response = await client.get("/v1/companies", params={"is_tracked": "maybe"})

    assert response.status_code == 422
    assert response.json()["errors"][0]["location"] == ["query", "is_tracked"]


@pytest.mark.usefixtures("apple_and_microsoft")
async def test_get_company_returns_its_details(client: AsyncClient) -> None:
    response = await client.get("/v1/companies/320193")

    assert response.status_code == 200
    assert response.json() == {
        "cik": "0000320193",
        "name": "Apple Inc.",
        "is_tracked": True,
        "tickers": [{"ticker": "AAPL", "exchange": "Nasdaq"}],
        "entity_type": "operating",
        "sic": "3571",
        "sic_description": "Electronic Computers",
        "fiscal_year_end": "0926",
        "state_of_incorporation": "CA",
    }


@pytest.mark.parametrize("path", ["/v1/companies/789019", "/v1/companies/789019/filings"])
async def test_an_unknown_cik_is_a_404_problem(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == UNKNOWN_CIK_PROBLEM


@pytest.mark.parametrize("path", ["/v1/companies/AAPL", "/v1/companies/AAPL/filings"])
async def test_a_cik_that_is_not_digits_is_a_422(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code == 422
    assert response.json()["errors"][0]["location"] == ["path", "cik"]


@pytest.mark.usefixtures("apple_10k_and_10q")
async def test_list_filings_returns_a_page_of_the_company_s_filings(client: AsyncClient) -> None:
    response = await client.get("/v1/companies/0000320193/filings", params={"form": "10-K"})

    assert response.status_code == 200
    assert response.json() == {
        "data": [
            {
                "cik": "0000320193",
                "accession_number": "0000320193-25-000079",
                "form": "10-K",
                "filing_date": "2025-10-31",
                "report_date": "2025-09-27",
                "accepted_at": "2025-10-31T10:01:26Z",
                "primary_document": "aapl-20250927.htm",
                "is_xbrl": True,
                "is_inline_xbrl": True,
                "filing_url": (
                    "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/"
                    "0000320193-25-000079-index.htm"
                ),
            }
        ],
        "next_cursor": None,
    }


@pytest.mark.usefixtures("apple_10k_and_10q")
async def test_list_filings_resumes_from_the_next_cursor(client: AsyncClient) -> None:
    first_page = (await client.get("/v1/companies/320193/filings", params={"limit": "1"})).json()
    second_page = (
        await client.get(
            "/v1/companies/320193/filings",
            params={"limit": "1", "cursor": first_page["next_cursor"]},
        )
    ).json()

    assert first_page["data"][0]["accession_number"] == "0000320193-25-000079"
    assert second_page["data"][0]["accession_number"] == "0000320193-25-000073"
    assert second_page["next_cursor"] is None


@pytest.mark.parametrize(
    "params",
    [
        {"form": "10-Q"},
        {"filed_to": "2025-08-01"},
        {"filed_from": "2025-08-01", "filed_to": "2025-08-01"},
    ],
)
@pytest.mark.usefixtures("apple_10k_and_10q")
async def test_list_filings_passes_each_filter_on(
    client: AsyncClient, params: dict[str, str]
) -> None:
    response = await client.get("/v1/companies/320193/filings", params=params)

    assert response.status_code == 200
    assert response.json()["data"][0]["accession_number"] == "0000320193-25-000073"
    assert len(response.json()["data"]) == 1


async def test_list_filings_rejects_a_bad_filter_with_a_422(client: AsyncClient) -> None:
    response = await client.get(
        "/v1/companies/320193/filings", params={"filed_from": "31/10/2025"}
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["location"] == ["query", "filed_from"]


@pytest.mark.parametrize(
    ("path", "params", "location"),
    [
        ("/v1/companies", {"ticker": ""}, ["query", "ticker"]),
        ("/v1/companies", {"name": ""}, ["query", "name"]),
        ("/v1/companies/320193/filings", {"form": ""}, ["query", "form"]),
    ],
)
async def test_an_empty_text_filter_is_a_422(
    client: AsyncClient, path: str, params: dict[str, str], location: list[str]
) -> None:
    response = await client.get(path, params=params)

    assert response.status_code == 422
    assert response.json()["errors"][0]["location"] == location
