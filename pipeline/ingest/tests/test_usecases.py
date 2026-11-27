import logging
from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa

from pipeline.database import session_scope
from pipeline.ingest.usecases import FailedFetch, run_ingest
from pipeline.raw.enums import EdgarDataset
from pipeline.raw.models import EdgarFetch, EdgarPayload
from pipeline.sources.edgar.client import TICKERS_URL, submissions_url

if TYPE_CHECKING:
    from pipeline.ingest.tests.fakes import FakeEdgar
    from pipeline.ingest.tracked_companies import TrackedCompany
    from pipeline.sources.edgar.client import EdgarClient

pytestmark = [pytest.mark.anyio, pytest.mark.usefixtures("database_url_as_ingest")]


async def recorded_fetches() -> list[tuple[EdgarDataset, int | None, int, bool]]:
    """Return each fetch as (dataset, CIK, HTTP status, has a payload), in a fixed order."""
    async with session_scope() as session:
        result = await session.execute(
            sa.select(
                EdgarFetch.dataset,
                EdgarFetch.cik,
                EdgarFetch.http_status,
                EdgarFetch.payload_id.is_not(None),
            ).order_by(EdgarFetch.dataset, EdgarFetch.cik)
        )
        return list(result.all())


async def count_rows(model: type[EdgarFetch | EdgarPayload]) -> int:
    async with session_scope() as session:
        result = await session.execute(sa.select(sa.func.count()).select_from(model))
        count: int = result.scalar_one()
    return count


async def test_a_run_records_the_tickers_file_and_each_companys_datasets(
    edgar: EdgarClient, tracked_companies: list[TrackedCompany]
) -> None:
    async with edgar:
        await run_ingest(edgar, tracked_companies)

    assert await recorded_fetches() == [
        (EdgarDataset.COMPANY_TICKERS, None, 200, True),
        (EdgarDataset.SUBMISSIONS, 320193, 200, True),
        (EdgarDataset.SUBMISSIONS, 2053456, 200, True),
        (EdgarDataset.COMPANY_FACTS, 320193, 200, True),
        (EdgarDataset.COMPANY_FACTS, 2053456, 404, False),
    ]


async def test_a_second_identical_run_adds_fetches_but_no_payloads(
    edgar: EdgarClient, tracked_companies: list[TrackedCompany]
) -> None:
    async with edgar:
        await run_ingest(edgar, tracked_companies)
        await run_ingest(edgar, tracked_companies)

    assert await count_rows(EdgarFetch) == 10
    assert await count_rows(EdgarPayload) == 4


async def test_a_run_where_every_fetch_is_recorded_reports_no_failure(
    edgar: EdgarClient, tracked_companies: list[TrackedCompany]
) -> None:
    async with edgar:
        failed_fetches = await run_ingest(edgar, tracked_companies)

    assert failed_fetches == []


# Refused, unavailable once the retries are spent, and a body that is not the envelope
FAILING_RESPONSES = [(403, b"<html>Forbidden</html>"), (503, b""), (200, b'{"cik": "0000320193"}')]


@pytest.mark.parametrize(("status", "body"), FAILING_RESPONSES)
async def test_a_failed_fetch_is_reported(
    edgar: EdgarClient,
    fake_edgar: FakeEdgar,
    tracked_companies: list[TrackedCompany],
    status: int,
    body: bytes,
) -> None:
    fake_edgar.answer(submissions_url(320193), status=status, body=body)

    async with edgar:
        failed_fetches = await run_ingest(edgar, tracked_companies)

    assert failed_fetches == [FailedFetch(dataset=EdgarDataset.SUBMISSIONS, cik=320193)]


@pytest.mark.parametrize(("status", "body"), FAILING_RESPONSES)
async def test_a_failed_fetch_records_nothing_and_the_others_are_recorded(
    edgar: EdgarClient,
    fake_edgar: FakeEdgar,
    tracked_companies: list[TrackedCompany],
    status: int,
    body: bytes,
) -> None:
    fake_edgar.answer(submissions_url(320193), status=status, body=body)

    async with edgar:
        await run_ingest(edgar, tracked_companies)

    assert await recorded_fetches() == [
        (EdgarDataset.COMPANY_TICKERS, None, 200, True),
        (EdgarDataset.SUBMISSIONS, 2053456, 200, True),
        (EdgarDataset.COMPANY_FACTS, 320193, 200, True),
        (EdgarDataset.COMPANY_FACTS, 2053456, 404, False),
    ]


async def test_a_failed_tickers_file_does_not_stop_the_companies(
    edgar: EdgarClient, fake_edgar: FakeEdgar, tracked_companies: list[TrackedCompany]
) -> None:
    fake_edgar.answer(TICKERS_URL, status=403, body=b"<html>Forbidden</html>")

    async with edgar:
        failed_fetches = await run_ingest(edgar, tracked_companies)

    assert failed_fetches == [FailedFetch(dataset=EdgarDataset.COMPANY_TICKERS, cik=None)]
    assert await count_rows(EdgarFetch) == 4


async def test_a_failed_fetch_is_logged_as_an_error(
    edgar: EdgarClient,
    fake_edgar: FakeEdgar,
    tracked_companies: list[TrackedCompany],
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_edgar.answer(submissions_url(320193), status=403, body=b"<html>Forbidden</html>")

    async with edgar:
        with caplog.at_level(logging.ERROR):
            await run_ingest(edgar, tracked_companies)

    [record] = caplog.records
    assert record.getMessage() == (
        "Could not fetch submissions for CIK 320193: SEC EDGAR refused "
        "https://data.sec.gov/submissions/CIK0000320193.json with status 403: "
        "check the User-Agent the source asks for, or whether it has blocked this IP address"
    )
