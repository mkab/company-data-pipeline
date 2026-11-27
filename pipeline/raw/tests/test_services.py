from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
import sqlalchemy as sa

from pipeline.raw.models import EdgarDataset, EdgarFetch, EdgarPayload
from pipeline.raw.repositories import EdgarFetchRepository, EdgarPayloadRepository
from pipeline.raw.services import RawFetchService
from pipeline.sources.tests.factories import FetchedResponseFactory

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.anyio

# sha256 of the body the unit tests record
BODY_SHA256 = bytes.fromhex("222b12d093f0ec3682d3e168e59a0e3bec3e623cdf812d0192400f1422ca0ebb")


def mocked_service(
    *, inserted_id: int | None, existing_id: int
) -> tuple[RawFetchService, AsyncMock, AsyncMock]:
    payloads = AsyncMock(spec=EdgarPayloadRepository)
    payloads.insert_if_absent.return_value = inserted_id
    payloads.get_id_by_sha256.return_value = existing_id
    fetches = AsyncMock(spec=EdgarFetchRepository)
    return RawFetchService(payloads, fetches), payloads, fetches


def added_fetch(fetches: AsyncMock) -> EdgarFetch:
    fetch: EdgarFetch = fetches.add.await_args.args[0]
    return fetch


async def test_a_new_body_is_stored_under_its_sha256() -> None:
    service, payloads, _ = mocked_service(inserted_id=7, existing_id=1)

    await service.record_fetch(
        FetchedResponseFactory.build(
            status=200, body=b'{"cik": "0000320193", "name": "Apple Inc."}'
        ),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )

    payloads.insert_if_absent.assert_awaited_once_with(
        sha256=BODY_SHA256, payload_json='{"cik": "0000320193", "name": "Apple Inc."}'
    )


async def test_a_new_body_links_the_fetch_to_the_inserted_payload() -> None:
    service, _, fetches = mocked_service(inserted_id=7, existing_id=1)

    await service.record_fetch(
        FetchedResponseFactory.build(status=200),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )

    assert added_fetch(fetches).payload_id == 7


async def test_a_stored_body_links_the_fetch_to_the_existing_payload() -> None:
    service, _, fetches = mocked_service(inserted_id=None, existing_id=3)

    await service.record_fetch(
        FetchedResponseFactory.build(status=200),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )

    assert added_fetch(fetches).payload_id == 3


async def test_a_not_found_fetch_stores_no_payload() -> None:
    service, payloads, fetches = mocked_service(inserted_id=7, existing_id=1)

    await service.record_fetch(
        FetchedResponseFactory.build(status=404, body=b"<html>Not found</html>"),
        dataset=EdgarDataset.COMPANY_FACTS,
        cik=1000045,
    )

    payloads.insert_if_absent.assert_not_awaited()
    assert added_fetch(fetches).payload_id is None


async def test_a_fetch_is_recorded_with_its_response_details() -> None:
    service, _, fetches = mocked_service(inserted_id=7, existing_id=1)

    await service.record_fetch(
        FetchedResponseFactory.build(
            url="https://www.sec.gov/files/company_tickers.json",
            status=200,
            fetched_at=datetime(2026, 11, 26, 9, 30, tzinfo=UTC),
        ),
        dataset=EdgarDataset.COMPANY_TICKERS,
        cik=None,
    )

    fetch = added_fetch(fetches)
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
    service = RawFetchService.from_session(ingest_session)
    for _ in range(2):
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
    await RawFetchService.from_session(ingest_session).record_fetch(
        FetchedResponseFactory.build(status=404, body=b"<html>Not found</html>"),
        dataset=EdgarDataset.COMPANY_FACTS,
        cik=1000045,
    )

    assert await ingest_session.scalar(sa.select(EdgarFetch.payload_id)) is None
    assert await count_rows(ingest_session, EdgarPayload) == 0
