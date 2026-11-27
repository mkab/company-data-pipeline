"""The repositories run as the ingest role, as the ingest CLI does.

So these tests also prove its grants are enough.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from pipeline.raw.models import EdgarDataset, EdgarFetch, EdgarPayload
from pipeline.raw.repositories import EdgarFetchRepository, EdgarPayloadRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.anyio


async def test_insert_if_absent_returns_the_id_of_a_new_payload(
    ingest_session: AsyncSession,
) -> None:
    payload_id = await EdgarPayloadRepository(ingest_session).insert_if_absent(
        sha256=b"\x01", payload_json='{"cik": "0000320193"}'
    )

    assert payload_id == 1


async def test_insert_if_absent_returns_none_for_a_stored_sha256(
    ingest_session: AsyncSession,
) -> None:
    payloads = EdgarPayloadRepository(ingest_session)
    await payloads.insert_if_absent(sha256=b"\x01", payload_json='{"cik": "0000320193"}')

    payload_id = await payloads.insert_if_absent(sha256=b"\x01", payload_json="{}")

    assert payload_id is None


async def test_insert_if_absent_stores_the_payload_as_json(ingest_session: AsyncSession) -> None:
    await EdgarPayloadRepository(ingest_session).insert_if_absent(
        sha256=b"\x01", payload_json='{"cik": "0000320193", "name": "Apple Inc."}'
    )

    payload = await ingest_session.scalar(sa.select(EdgarPayload.payload))
    assert payload == {"cik": "0000320193", "name": "Apple Inc."}


async def test_get_id_by_sha256_returns_the_stored_payload_id(
    ingest_session: AsyncSession,
) -> None:
    payloads = EdgarPayloadRepository(ingest_session)
    await payloads.insert_if_absent(sha256=b"\x01", payload_json="{}")
    await payloads.insert_if_absent(sha256=b"\x02", payload_json="{}")

    assert await payloads.get_id_by_sha256(b"\x02") == 2


async def test_add_stores_a_fetch(ingest_session: AsyncSession) -> None:
    await EdgarFetchRepository(ingest_session).add(
        EdgarFetch(
            dataset=EdgarDataset.COMPANY_FACTS,
            cik=1000045,
            url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001000045.json",
            http_status=404,
            fetched_at=datetime(2026, 11, 26, 9, 30, tzinfo=UTC),
            payload_id=None,
        )
    )

    fetch = await ingest_session.scalar(sa.select(EdgarFetch))
    assert fetch is not None
    assert fetch.dataset == EdgarDataset.COMPANY_FACTS
    assert fetch.cik == 1000045
    assert fetch.url == "https://data.sec.gov/api/xbrl/companyfacts/CIK0001000045.json"
    assert fetch.http_status == 404
    assert fetch.fetched_at == datetime(2026, 11, 26, 9, 30, tzinfo=UTC)
    assert fetch.payload_id is None


@pytest.mark.parametrize(
    ("dataset", "cik"),
    [
        (EdgarDataset.COMPANY_TICKERS, 320193),
        (EdgarDataset.SUBMISSIONS, None),
        (EdgarDataset.COMPANY_FACTS, None),
    ],
)
async def test_a_cik_is_required_for_a_company_dataset_only(
    ingest_session: AsyncSession, dataset: EdgarDataset, cik: int | None
) -> None:
    with pytest.raises(IntegrityError, match="edgar_fetches_cik_set_per_company_check"):
        await EdgarFetchRepository(ingest_session).add(
            EdgarFetch(
                dataset=dataset,
                cik=cik,
                url="https://data.sec.gov/submissions/CIK0000320193.json",
                http_status=404,
                fetched_at=datetime(2026, 11, 26, 9, 30, tzinfo=UTC),
                payload_id=None,
            )
        )


async def test_a_fetch_other_than_not_found_needs_a_payload(ingest_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="edgar_fetches_payload_absent_on_not_found_check"):
        await EdgarFetchRepository(ingest_session).add(
            EdgarFetch(
                dataset=EdgarDataset.SUBMISSIONS,
                cik=320193,
                url="https://data.sec.gov/submissions/CIK0000320193.json",
                http_status=200,
                fetched_at=datetime(2026, 11, 26, 9, 30, tzinfo=UTC),
                payload_id=None,
            )
        )
