from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa

from pipeline.raw.enums import EdgarDataset
from pipeline.raw.models import EdgarFetch, EdgarPayload
from pipeline.raw.services import EdgarFetchService
from pipeline.sources.tests.factories import FetchedResponseFactory

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from pipeline.raw.tests.fakes import FakeEdgarFetchRepository, FakeEdgarPayloadRepository

pytestmark = pytest.mark.anyio

# sha256 of b'{"cik": "0000320193", "name": "Apple Inc."}'
BODY_SHA256 = bytes.fromhex("222b12d093f0ec3682d3e168e59a0e3bec3e623cdf812d0192400f1422ca0ebb")


async def test_a_new_body_is_stored_under_its_sha256(
    service: EdgarFetchService, payloads: FakeEdgarPayloadRepository
) -> None:
    await service.record_fetch(
        FetchedResponseFactory.build(
            status=200, body=b'{"cik": "0000320193", "name": "Apple Inc."}'
        ),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )

    assert payloads.payloads == {BODY_SHA256: (1, '{"cik": "0000320193", "name": "Apple Inc."}')}


async def test_the_same_body_twice_links_both_fetches_to_one_payload(
    service: EdgarFetchService,
    payloads: FakeEdgarPayloadRepository,
    fetches: FakeEdgarFetchRepository,
) -> None:
    await service.record_fetch(
        FetchedResponseFactory.build(status=200, body=b'{"cik": "0000320193"}'),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )
    await service.record_fetch(
        FetchedResponseFactory.build(status=200, body=b'{"cik": "0000320193"}'),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )

    assert len(payloads.payloads) == 1
    assert [fetch.payload_id for fetch in fetches.fetches] == [1, 1]


async def test_a_different_body_links_the_fetch_to_a_new_payload(
    service: EdgarFetchService, fetches: FakeEdgarFetchRepository
) -> None:
    await service.record_fetch(
        FetchedResponseFactory.build(status=200, body=b'{"cik": "0000320193"}'),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )
    await service.record_fetch(
        FetchedResponseFactory.build(status=200, body=b'{"cik":"0000320193"}'),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )

    assert [fetch.payload_id for fetch in fetches.fetches] == [1, 2]


async def test_a_not_found_fetch_stores_no_payload(
    service: EdgarFetchService,
    payloads: FakeEdgarPayloadRepository,
    fetches: FakeEdgarFetchRepository,
) -> None:
    await service.record_fetch(
        FetchedResponseFactory.build(status=404, body=b"<html>Not found</html>"),
        dataset=EdgarDataset.COMPANY_FACTS,
        cik=1000045,
    )

    assert payloads.payloads == {}
    assert fetches.fetches[0].payload_id is None


async def test_a_fetch_is_recorded_with_its_response_details(
    service: EdgarFetchService, fetches: FakeEdgarFetchRepository
) -> None:
    await service.record_fetch(
        FetchedResponseFactory.build(
            url="https://www.sec.gov/files/company_tickers.json",
            status=200,
            fetched_at=datetime(2026, 11, 26, 9, 30, tzinfo=UTC),
        ),
        dataset=EdgarDataset.COMPANY_TICKERS,
        cik=None,
    )

    [fetch] = fetches.fetches
    assert fetch.dataset == EdgarDataset.COMPANY_TICKERS
    assert fetch.cik is None
    assert fetch.url == "https://www.sec.gov/files/company_tickers.json"
    assert fetch.http_status == 200
    assert fetch.fetched_at == datetime(2026, 11, 26, 9, 30, tzinfo=UTC)


async def count_rows(session: AsyncSession, model: type[EdgarFetch | EdgarPayload]) -> int:
    result = await session.execute(sa.select(sa.func.count()).select_from(model))
    count: int = result.scalar_one()
    return count


async def test_recording_the_same_body_twice_stores_one_payload_for_two_fetches(
    ingest_session: AsyncSession,
) -> None:
    service = EdgarFetchService.from_session(ingest_session)
    await service.record_fetch(
        FetchedResponseFactory.build(status=200, body=b'{"cik": "0000320193"}'),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )
    await service.record_fetch(
        FetchedResponseFactory.build(status=200, body=b'{"cik": "0000320193"}'),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )

    assert await count_rows(ingest_session, EdgarFetch) == 2
    assert await count_rows(ingest_session, EdgarPayload) == 1


async def test_a_not_found_fetch_is_recorded_with_a_null_payload_id(
    ingest_session: AsyncSession,
) -> None:
    await EdgarFetchService.from_session(ingest_session).record_fetch(
        FetchedResponseFactory.build(status=404, body=b"<html>Not found</html>"),
        dataset=EdgarDataset.COMPANY_FACTS,
        cik=1000045,
    )

    assert await ingest_session.scalar(sa.select(EdgarFetch.payload_id)) is None
    assert await count_rows(ingest_session, EdgarPayload) == 0
