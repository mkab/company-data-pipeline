from pathlib import Path

import httpx2
import pytest

from pipeline.sources.edgar.client import (
    EdgarClient,
    UnexpectedPayloadError,
    edgar_source_settings,
)
from pipeline.sources.http import SourceClient, SourceRefusedError

TICKERS_FIXTURE = Path(__file__).parent / "fixtures" / "company_tickers_exchange.json"


class FixedSource:
    """Answers every request with the same response, and keeps the requests it saw."""

    def __init__(self, response: httpx2.Response) -> None:
        self.response = response
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.response


def make_edgar(source: FixedSource) -> EdgarClient:
    return EdgarClient(
        SourceClient(
            edgar_source_settings("Jane Doe jane@example.com"),
            transport=httpx2.MockTransport(source),
        )
    )


@pytest.mark.anyio
async def test_the_tickers_file_is_fetched_from_www_sec_gov() -> None:
    source = FixedSource(httpx2.Response(200, content=TICKERS_FIXTURE.read_bytes()))

    async with make_edgar(source) as edgar:
        await edgar.get_tickers()

    assert str(source.requests[0].url) == "https://www.sec.gov/files/company_tickers_exchange.json"


@pytest.mark.anyio
async def test_the_tickers_file_comes_back_as_received() -> None:
    source = FixedSource(httpx2.Response(200, content=TICKERS_FIXTURE.read_bytes()))

    async with make_edgar(source) as edgar:
        response = await edgar.get_tickers()

    assert response.status == 200
    assert response.body == TICKERS_FIXTURE.read_bytes()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body",
    [
        b'{"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}',
        b'[["cik", "name", "ticker", "exchange"]]',
        b"<html>Rate limited</html>",
    ],
)
async def test_a_tickers_file_without_its_envelope_is_unexpected(body: bytes) -> None:
    source = FixedSource(httpx2.Response(200, content=body))

    async with make_edgar(source) as edgar:
        with pytest.raises(UnexpectedPayloadError, match=r"company_tickers_exchange\.json"):
            await edgar.get_tickers()


@pytest.mark.anyio
async def test_submissions_without_their_envelope_are_unexpected() -> None:
    source = FixedSource(httpx2.Response(200, content=b'{"cik": "0000320193"}'))

    async with make_edgar(source) as edgar:
        with pytest.raises(UnexpectedPayloadError, match="CIK0000320193"):
            await edgar.get_submissions(320193)


@pytest.mark.anyio
async def test_company_facts_without_their_envelope_are_unexpected() -> None:
    source = FixedSource(httpx2.Response(200, content=b'{"cik": 320193, "facts": []}'))

    async with make_edgar(source) as edgar:
        with pytest.raises(UnexpectedPayloadError, match="CIK0000320193"):
            await edgar.get_company_facts(320193)


@pytest.mark.anyio
async def test_a_submissions_404_is_refused() -> None:
    source = FixedSource(httpx2.Response(404))

    async with make_edgar(source) as edgar:
        with pytest.raises(SourceRefusedError):
            await edgar.get_submissions(320193)


@pytest.mark.anyio
async def test_a_company_facts_refusal_other_than_404_is_raised() -> None:
    source = FixedSource(httpx2.Response(403))

    async with make_edgar(source) as edgar:
        with pytest.raises(SourceRefusedError, match="status 403"):
            await edgar.get_company_facts(320193)
