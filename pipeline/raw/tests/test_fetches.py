"""The write path runs as the ingest role, as the ingest CLI does.

So these tests also prove its grants are enough.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from pipeline.raw.fetches import record_fetch
from pipeline.raw.tables import EdgarDataset, edgar_fetches, edgar_payloads
from pipeline.raw.tests.factories import FetchedResponseFactory

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.anyio


async def count_rows(engine: AsyncEngine, table: sa.Table) -> int:
    async with engine.connect() as connection:
        result = await connection.execute(sa.select(sa.func.count()).select_from(table))
    count: int = result.scalar_one()
    return count


async def test_recording_the_same_body_twice_stores_one_payload_for_two_fetches(
    ingest_engine: AsyncEngine,
) -> None:
    for _ in range(2):
        await record_fetch(
            ingest_engine,
            FetchedResponseFactory.build(body=b'{"cik": "0000320193"}'),
            dataset=EdgarDataset.SUBMISSIONS,
            cik=320193,
        )

    assert await count_rows(ingest_engine, edgar_fetches) == 2
    assert await count_rows(ingest_engine, edgar_payloads) == 1


async def test_a_different_body_stores_a_new_payload(ingest_engine: AsyncEngine) -> None:
    await record_fetch(
        ingest_engine,
        FetchedResponseFactory.build(body=b'{"cik": "0000320193"}'),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )
    await record_fetch(
        ingest_engine,
        FetchedResponseFactory.build(body=b'{"cik":"0000320193"}'),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )

    assert await count_rows(ingest_engine, edgar_payloads) == 2


async def test_a_payload_is_stored_with_the_sha256_of_its_body(
    ingest_engine: AsyncEngine,
) -> None:
    await record_fetch(
        ingest_engine,
        FetchedResponseFactory.build(body=b'{"cik": "0000320193", "name": "Apple Inc."}'),
        dataset=EdgarDataset.SUBMISSIONS,
        cik=320193,
    )

    async with ingest_engine.connect() as connection:
        payload = (
            await connection.execute(sa.select(edgar_payloads.c.sha256, edgar_payloads.c.payload))
        ).one()
    assert payload.sha256.hex() == (
        "222b12d093f0ec3682d3e168e59a0e3bec3e623cdf812d0192400f1422ca0ebb"
    )
    assert payload.payload == {"cik": "0000320193", "name": "Apple Inc."}


async def test_a_fetch_is_stored_with_its_response_details(ingest_engine: AsyncEngine) -> None:
    await record_fetch(
        ingest_engine,
        FetchedResponseFactory.build(
            url="https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
            status=200,
            fetched_at=datetime(2026, 11, 26, 9, 30, tzinfo=UTC),
        ),
        dataset=EdgarDataset.COMPANY_FACTS,
        cik=320193,
    )

    async with ingest_engine.connect() as connection:
        fetch = (await connection.execute(sa.select(edgar_fetches))).one()
    assert fetch.dataset == EdgarDataset.COMPANY_FACTS
    assert fetch.cik == 320193
    assert fetch.url == "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
    assert fetch.http_status == 200
    assert fetch.fetched_at == datetime(2026, 11, 26, 9, 30, tzinfo=UTC)
    assert fetch.payload_id is not None


async def test_a_not_found_fetch_is_recorded_without_a_payload(
    ingest_engine: AsyncEngine,
) -> None:
    await record_fetch(
        ingest_engine,
        FetchedResponseFactory.build(status=404, body=b"<html>Not found</html>"),
        dataset=EdgarDataset.COMPANY_FACTS,
        cik=1000045,
    )

    async with ingest_engine.connect() as connection:
        payload_id = await connection.scalar(sa.select(edgar_fetches.c.payload_id))
    assert payload_id is None
    assert await count_rows(ingest_engine, edgar_payloads) == 0


async def test_the_tickers_file_is_recorded_without_a_cik(ingest_engine: AsyncEngine) -> None:
    await record_fetch(
        ingest_engine,
        FetchedResponseFactory.build(url="https://www.sec.gov/files/company_tickers.json"),
        dataset=EdgarDataset.COMPANY_TICKERS,
        cik=None,
    )

    assert await count_rows(ingest_engine, edgar_fetches) == 1


@pytest.mark.parametrize(
    ("dataset", "cik"),
    [
        (EdgarDataset.COMPANY_TICKERS, 320193),
        (EdgarDataset.SUBMISSIONS, None),
        (EdgarDataset.COMPANY_FACTS, None),
    ],
)
async def test_a_cik_is_required_for_a_company_dataset_only(
    ingest_engine: AsyncEngine, dataset: EdgarDataset, cik: int | None
) -> None:
    with pytest.raises(IntegrityError, match="edgar_fetches_cik_set_per_company_check"):
        await record_fetch(
            ingest_engine, FetchedResponseFactory.build(status=200), dataset=dataset, cik=cik
        )


async def test_a_failed_fetch_insert_keeps_no_payload(ingest_engine: AsyncEngine) -> None:
    with pytest.raises(IntegrityError, match="edgar_fetches_cik_set_per_company_check"):
        await record_fetch(
            ingest_engine,
            FetchedResponseFactory.build(status=200),
            dataset=EdgarDataset.COMPANY_TICKERS,
            cik=320193,
        )

    assert await count_rows(ingest_engine, edgar_payloads) == 0


async def test_a_fetch_other_than_not_found_needs_a_payload(ingest_engine: AsyncEngine) -> None:
    async with ingest_engine.begin() as connection:
        with pytest.raises(
            IntegrityError, match="edgar_fetches_payload_absent_on_not_found_check"
        ):
            await connection.execute(
                sa.insert(edgar_fetches).values(
                    dataset=EdgarDataset.SUBMISSIONS,
                    cik=320193,
                    url="https://data.sec.gov/submissions/CIK0000320193.json",
                    http_status=200,
                    fetched_at=datetime(2026, 11, 26, 9, 30, tzinfo=UTC),
                    payload_id=None,
                )
            )
