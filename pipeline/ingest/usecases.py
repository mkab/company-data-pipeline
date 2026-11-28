import asyncio
import logging
from http import HTTPStatus
from typing import TYPE_CHECKING

from pipeline.database import session_scope
from pipeline.ingest.types import FetchTarget
from pipeline.raw.enums import EdgarDataset
from pipeline.raw.services import EdgarFetchService
from pipeline.sources.edgar.exceptions import UnexpectedPayloadError
from pipeline.sources.exceptions import SourceRefusedError, SourceUnavailableError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from pipeline.ingest.types import TrackedCompany
    from pipeline.sources.edgar.client import EdgarClient
    from pipeline.sources.types import FetchedResponse

logger = logging.getLogger(__name__)


async def run_ingest(
    edgar: EdgarClient, tracked_companies: list[TrackedCompany]
) -> list[FetchTarget]:
    """Fetch the tickers file, then every tracked company's submissions and company facts.

    Each fetch is recorded in raw in its own transaction.
    A fetch EDGAR refuses, that stays unavailable, or whose payload is not the expected one
    is recorded nowhere and comes back in the returned list,
    while the run carries on with the others.

    A database error is not a fetch failure:
    it is raised, and stops the run.
    """
    failed_tickers = await fetch_and_record(
        edgar.get_tickers, FetchTarget(dataset=EdgarDataset.COMPANY_TICKERS, cik=None)
    )
    async with asyncio.TaskGroup() as task_group:
        company_tasks = [
            task_group.create_task(ingest_company(edgar, company.cik))
            for company in tracked_companies
        ]
    failed_fetches = [] if failed_tickers is None else [failed_tickers]
    for task in company_tasks:
        failed_fetches.extend(task.result())
    return failed_fetches


async def ingest_company(edgar: EdgarClient, cik: int) -> list[FetchTarget]:
    """Fetch and record one company's datasets, and return the fetches that failed."""
    outcomes = [
        await fetch_and_record(
            lambda: edgar.get_submissions(cik),
            FetchTarget(dataset=EdgarDataset.SUBMISSIONS, cik=cik),
        ),
        await fetch_and_record(
            lambda: edgar.get_company_facts(cik),
            FetchTarget(dataset=EdgarDataset.COMPANY_FACTS, cik=cik),
        ),
    ]
    return [outcome for outcome in outcomes if outcome is not None]


async def fetch_and_record(
    fetch: Callable[[], Awaitable[FetchedResponse]], target: FetchTarget
) -> FetchTarget | None:
    """Record the response `fetch` returns.

    Return `target` when there is no response to record, and `None` otherwise.
    """
    try:
        response = await fetch()
    except (SourceRefusedError, SourceUnavailableError, UnexpectedPayloadError) as error:
        logger.error("Could not fetch %s: %s", target.describe(), error)
        return target
    if response.status == HTTPStatus.NOT_FOUND:
        logger.info("CIK %s has no %s", target.cik, target.dataset)
    async with session_scope() as session:
        await EdgarFetchService.from_session(session).record_fetch(
            response, dataset=target.dataset, cik=target.cik
        )
    return None
