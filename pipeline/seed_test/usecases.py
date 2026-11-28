from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pipeline.database import session_scope
from pipeline.raw.enums import EdgarDataset
from pipeline.raw.services import EdgarFetchService
from pipeline.sources.edgar.client import TICKERS_URL, company_facts_url, submissions_url
from pipeline.sources.types import FetchedResponse

if TYPE_CHECKING:
    from pathlib import Path

    from pipeline.seed_test.types import SeedFetch


def edgar_url(dataset: EdgarDataset, cik: int | None) -> str:
    """Return the URL the ingest run fetches `dataset` from, for the company `cik`."""
    match dataset, cik:
        case EdgarDataset.COMPANY_TICKERS, None:
            return TICKERS_URL
        case EdgarDataset.SUBMISSIONS, int():
            return submissions_url(cik)
        case EdgarDataset.COMPANY_FACTS, int():
            return company_facts_url(cik)
    raise ValueError(f"{dataset} cannot be fetched for CIK {cik}")


async def seed_raw(fetches: list[SeedFetch], *, fixtures_dir: Path) -> None:
    """Record each fetch through the ingest write path, as if EDGAR had answered it now.

    Each fetch's `file` is read from `fixtures_dir`, and every fetch gets the same `fetched_at`.
    Each fetch is recorded in its own transaction, as the ingest run records them.
    A second seed adds fetches pointing at the same payloads,
    so the latest fetch of each dataset and company still reads the same body.
    """
    fetched_at = datetime.now(UTC)
    for fetch in fetches:
        response = FetchedResponse(
            url=edgar_url(fetch.dataset, fetch.cik),
            status=fetch.http_status,
            fetched_at=fetched_at,
            body=b"" if fetch.file is None else (fixtures_dir / fetch.file).read_bytes(),
        )
        async with session_scope() as session:
            await EdgarFetchService.from_session(session).record_fetch(
                response, dataset=fetch.dataset, cik=fetch.cik
            )
