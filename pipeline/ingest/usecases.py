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
    """A fetch the run could not record.

    `cik` is `None` for the tickers file.
    """

    dataset: EdgarDataset
    cik: int | None

    def describe(self) -> str:
        if self.cik is None:
            return str(self.dataset)
        return f"{self.dataset} for CIK {self.cik}"


async def run_ingest(
    edgar: EdgarClient, tracked_companies: list[TrackedCompany]
) -> list[FailedFetch]:
    """Fetch the tickers file, then every tracked company's submissions and company facts.

    Each fetch is recorded in raw in its own transaction.
    A fetch EDGAR refuses, that stays unavailable, or whose payload is not the expected one
    is recorded nowhere and comes back in the returned list,
    while the run carries on with the others.

    A database error is not a fetch failure:
    it is raised, and stops the run.
    """
    tickers_failure = await fetch_and_record(
        edgar.get_tickers, FailedFetch(dataset=EdgarDataset.COMPANY_TICKERS, cik=None)
    )
    async with asyncio.TaskGroup() as task_group:
        company_tasks = [
            task_group.create_task(ingest_company(edgar, company.cik))
            for company in tracked_companies
        ]
    failed_fetches = [] if tickers_failure is None else [tickers_failure]
    for task in company_tasks:
        failed_fetches.extend(task.result())
    return failed_fetches


async def ingest_company(edgar: EdgarClient, cik: int) -> list[FailedFetch]:
    """Fetch and record one company's datasets, and return the fetches that failed."""
    outcomes = [
        await fetch_and_record(
            lambda: edgar.get_submissions(cik),
            FailedFetch(dataset=EdgarDataset.SUBMISSIONS, cik=cik),
        ),
        await fetch_and_record(
            lambda: edgar.get_company_facts(cik),
            FailedFetch(dataset=EdgarDataset.COMPANY_FACTS, cik=cik),
        ),
    ]
    return [outcome for outcome in outcomes if outcome is not None]


async def fetch_and_record(
    fetch: Callable[[], Awaitable[FetchedResponse]], failure: FailedFetch
) -> FailedFetch | None:
    """Record the response `fetch` returns.

    Return `failure` when there is no response to record, and `None` otherwise.
    """
    try:
        response = await fetch()
    except (SourceRefusedError, SourceUnavailableError, UnexpectedPayloadError) as error:
        logger.error("Could not fetch %s: %s", failure.describe(), error)
        return failure
    if response.status == HTTPStatus.NOT_FOUND:
        logger.info("CIK %s has no %s", failure.cik, failure.dataset)
    async with session_scope() as session:
        await EdgarFetchService.from_session(session).record_fetch(
            response, dataset=failure.dataset, cik=failure.cik
        )
    return None
