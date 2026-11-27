from http import HTTPStatus
from typing import TYPE_CHECKING, Self

import pydantic

from pipeline.sources.edgar.envelopes import (
    CompanyFactsEnvelope,
    SubmissionsEnvelope,
    TickersEnvelope,
)
from pipeline.sources.http import SourceClient, SourceRefusedError, SourceSettings

if TYPE_CHECKING:
    from types import TracebackType

    from pipeline.settings import EdgarSettings
    from pipeline.sources.http import FetchedResponse

# SEC fair access: "no more than 10 requests per second",
# per user and across all machines (https://www.sec.gov/about/developer-resources).
# Half of it leaves room for anything else sharing the IP address
EDGAR_REQUESTS_PER_SECOND = 5
EDGAR_MAX_IN_FLIGHT = 5

# The cap is for both hosts together,
# so one client (one limiter) serves both
WWW_BASE_URL = "https://www.sec.gov"
DATA_BASE_URL = "https://data.sec.gov"

TICKERS_URL = f"{WWW_BASE_URL}/files/company_tickers_exchange.json"

SOURCE_NAME = "SEC EDGAR"


class UnexpectedPayloadError(Exception):
    """A successful response whose body is not the dataset's envelope."""


def edgar_source_settings(user_agent: str) -> SourceSettings:
    """Return how EDGAR is called, with the User-Agent SEC asks for."""
    return SourceSettings(
        name=SOURCE_NAME,
        user_agent=user_agent,
        requests_per_second=EDGAR_REQUESTS_PER_SECOND,
        max_in_flight=EDGAR_MAX_IN_FLIGHT,
    )


def submissions_url(cik: int) -> str:
    return f"{DATA_BASE_URL}/submissions/CIK{cik:010d}.json"


def company_facts_url(cik: int) -> str:
    return f"{DATA_BASE_URL}/api/xbrl/companyfacts/CIK{cik:010d}.json"


def check_envelope(response: FetchedResponse, envelope: type[pydantic.BaseModel]) -> None:
    """Raise `UnexpectedPayloadError` unless the body parses as `envelope`."""
    try:
        envelope.model_validate_json(response.body)
    except pydantic.ValidationError as error:
        raise UnexpectedPayloadError(
            f"{SOURCE_NAME} returned an unexpected payload for {response.url}"
        ) from error


class EdgarClient:
    """One method per EDGAR dataset, each returning the response with its body unchanged."""

    def __init__(self, source: SourceClient) -> None:
        self._source = source

    @classmethod
    def from_settings(cls, settings: EdgarSettings) -> Self:
        return cls(SourceClient(edgar_source_settings(settings.edgar_user_agent)))

    async def __aenter__(self) -> Self:
        await self._source.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._source.__aexit__(exc_type, exc_value, traceback)

    async def get_tickers(self) -> FetchedResponse:
        """Fetch the full company list, with each company's tickers and exchanges."""
        response = await self._source.get(TICKERS_URL)
        check_envelope(response, TickersEnvelope)
        return response

    async def get_submissions(self, cik: int) -> FetchedResponse:
        """Fetch a company's metadata and recent filings."""
        response = await self._source.get(submissions_url(cik))
        check_envelope(response, SubmissionsEnvelope)
        return response

    async def get_company_facts(self, cik: int) -> FetchedResponse:
        """Fetch a company's XBRL facts.

        A company with no facts comes back as its 404 response, with an empty or error body,
        so the fetch can still be recorded.
        """
        try:
            response = await self._source.get(company_facts_url(cik))
        except SourceRefusedError as refusal:
            if refusal.response.status == HTTPStatus.NOT_FOUND:
                return refusal.response
            raise
        check_envelope(response, CompanyFactsEnvelope)
        return response
