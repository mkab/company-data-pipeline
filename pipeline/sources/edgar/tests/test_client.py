from pathlib import Path

import httpx2
import pytest

from pipeline.sources.edgar.client import (
    EdgarClient,
    UnexpectedPayloadError,
    edgar_source_settings,
)
from pipeline.sources.http import SourceClient, SourceRefusedError
from pipeline.sources.tests.fakes import ScriptedSource

TICKERS_FIXTURE = Path(__file__).parent / "fixtures" / "company_tickers_exchange.json"
CASSETTES = Path(__file__).parent / "cassettes" / "test_client"

# Arxis, Inc.: a recent IPO,
# so among the smallest companyfacts a listed filer has
SMALL_FILER_CIK = 2093536
# Generation Essentials Group: listed on NYSE, but SEC has no XBRL facts for it
NO_FACTS_CIK = 2053456


def make_edgar(source: ScriptedSource) -> EdgarClient:
    return EdgarClient(
        SourceClient(
            edgar_source_settings("Jane Doe jane@example.com"),
            transport=httpx2.MockTransport(source),
        )
    )


@pytest.mark.anyio
async def test_the_tickers_file_is_fetched_from_www_sec_gov() -> None:
    source = ScriptedSource([httpx2.Response(200, content=TICKERS_FIXTURE.read_bytes())])

    async with make_edgar(source) as edgar:
        await edgar.get_tickers()

    assert str(source.requests[0].url) == "https://www.sec.gov/files/company_tickers_exchange.json"


@pytest.mark.anyio
async def test_the_tickers_file_comes_back_as_received() -> None:
    source = ScriptedSource([httpx2.Response(200, content=TICKERS_FIXTURE.read_bytes())])

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
    source = ScriptedSource([httpx2.Response(200, content=body)])

    async with make_edgar(source) as edgar:
        with pytest.raises(UnexpectedPayloadError, match=r"company_tickers_exchange\.json"):
            await edgar.get_tickers()


@pytest.mark.anyio
async def test_submissions_without_their_envelope_are_unexpected() -> None:
    source = ScriptedSource([httpx2.Response(200, content=b'{"cik": "0000320193"}')])

    async with make_edgar(source) as edgar:
        with pytest.raises(UnexpectedPayloadError, match="CIK0000320193"):
            await edgar.get_submissions(320193)


@pytest.mark.anyio
async def test_company_facts_without_their_envelope_are_unexpected() -> None:
    source = ScriptedSource([httpx2.Response(200, content=b'{"cik": 320193, "facts": []}')])

    async with make_edgar(source) as edgar:
        with pytest.raises(UnexpectedPayloadError, match="CIK0000320193"):
            await edgar.get_company_facts(320193)


@pytest.mark.anyio
async def test_a_submissions_404_is_refused() -> None:
    source = ScriptedSource([httpx2.Response(404)])

    async with make_edgar(source) as edgar:
        with pytest.raises(SourceRefusedError):
            await edgar.get_submissions(320193)


@pytest.mark.anyio
async def test_a_company_facts_refusal_other_than_404_is_raised() -> None:
    source = ScriptedSource([httpx2.Response(403)])

    async with make_edgar(source) as edgar:
        with pytest.raises(SourceRefusedError, match="status 403"):
            await edgar.get_company_facts(320193)


@pytest.mark.vcr
@pytest.mark.anyio
async def test_a_small_filers_submissions_come_back_as_received(edgar: EdgarClient) -> None:
    async with edgar:
        response = await edgar.get_submissions(SMALL_FILER_CIK)

    assert response.url == "https://data.sec.gov/submissions/CIK0002093536.json"
    assert response.status == 200
    assert response.body.startswith(b'{"cik":"0002093536","entityType":"operating"')


@pytest.mark.vcr
@pytest.mark.anyio
async def test_a_small_filers_company_facts_come_back_as_received(edgar: EdgarClient) -> None:
    async with edgar:
        response = await edgar.get_company_facts(SMALL_FILER_CIK)

    assert response.url == "https://data.sec.gov/api/xbrl/companyfacts/CIK0002093536.json"
    assert response.status == 200
    assert response.body.startswith(b'{"cik":"0002093536","entityName":"ARXIS, INC."')


@pytest.mark.vcr
@pytest.mark.anyio
async def test_a_company_with_no_facts_comes_back_as_its_404(edgar: EdgarClient) -> None:
    async with edgar:
        response = await edgar.get_company_facts(NO_FACTS_CIK)

    assert response.url == "https://data.sec.gov/api/xbrl/companyfacts/CIK0002053456.json"
    assert response.status == 404


@pytest.mark.parametrize(
    "cassette",
    [
        "test_a_small_filers_submissions_come_back_as_received.yaml",
        "test_a_small_filers_company_facts_come_back_as_received.yaml",
        "test_a_company_with_no_facts_comes_back_as_its_404.yaml",
    ],
)
def test_no_cassette_holds_a_user_agent(cassette: str) -> None:
    text = (CASSETTES / cassette).read_text()

    assert "user-agent" not in text.lower()


def test_the_user_agent_check_covers_every_cassette() -> None:
    assert sorted(path.name for path in CASSETTES.iterdir()) == [
        "test_a_company_with_no_facts_comes_back_as_its_404.yaml",
        "test_a_small_filers_company_facts_come_back_as_received.yaml",
        "test_a_small_filers_submissions_come_back_as_received.yaml",
    ]
