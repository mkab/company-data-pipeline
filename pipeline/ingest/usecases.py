import asyncio
import logging
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING

from pipeline.database import session_scope
from pipeline.raw.enums import EdgarDataset
from pipeline.raw.services import EdgarFetchService
from pipeline.sources.edgar.client import UnexpectedPayloadError
from pipeline.sources.http import SourceRefusedError, SourceUnavailableError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from pipeline.ingest.tracked_companies import TrackedCompany
    from pipeline.sources.edgar.client import EdgarClient
    from pipeline.sources.http import FetchedResponse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FailedFetch:
    """A fetch the run could not record. `cik` is `None` for the tickers file."""

    dataset: EdgarDataset
    cik: int | None


async def run_ingest(
    edgar: EdgarClient, tracked_companies: list[TrackedCompany]
) -> list[FailedFetch]:
    """Fetch the tickers file, then every tracked company's submissions and company facts.

    Each fetch is recorded in raw in its own transaction.
    A fetch EDGAR refuses, that stays unavailable, or whose payload is not the expected one
    is recorded nowhere and comes back in the returned list,
    while the run carries on with the others.
    """
    failed_fetches: list[FailedFetch] = []
    await fetch_and_record(
        edgar.get_tickers,
        dataset=EdgarDataset.COMPANY_TICKERS,
        cik=None,
        failed_fetches=failed_fetches,
    )
    async with asyncio.TaskGroup() as task_group:
        for company in tracked_companies:
            task_group.create_task(ingest_company(edgar, company.cik, failed_fetches))
    return failed_fetches


async def ingest_company(edgar: EdgarClient, cik: int, failed_fetches: list[FailedFetch]) -> None:
    await fetch_and_record(
        lambda: edgar.get_submissions(cik),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=cik,
        failed_fetches=failed_fetches,
    )
    await fetch_and_record(
        lambda: edgar.get_company_facts(cik),
        dataset=EdgarDataset.COMPANY_FACTS,
        cik=cik,
        failed_fetches=failed_fetches,
    )


async def fetch_and_record(
    fetch: Callable[[], Awaitable[FetchedResponse]],
    *,
    dataset: EdgarDataset,
    cik: int | None,
    failed_fetches: list[FailedFetch],
) -> None:
    """Record the response `fetch` returns, or add the fetch to `failed_fetches`."""
    try:
        response = await fetch()
    except (SourceRefusedError, SourceUnavailableError, UnexpectedPayloadError) as error:
        logger.error("Could not fetch %s for CIK %s: %s", dataset, cik, error)
        failed_fetches.append(FailedFetch(dataset=dataset, cik=cik))
        return
    if response.status == HTTPStatus.NOT_FOUND:
        logger.info("CIK %s has no %s", cik, dataset)
    async with session_scope() as session:
        await EdgarFetchService.from_session(session).record_fetch(
            response, dataset=dataset, cik=cik
        )
