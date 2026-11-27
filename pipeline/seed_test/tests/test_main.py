import pytest
import sqlalchemy as sa

from pipeline.database import session_scope
from pipeline.raw.enums import EdgarDataset
from pipeline.raw.models import EdgarFetch
from pipeline.seed_test.__main__ import seed

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


async def test_the_seed_records_the_committed_fixtures_of_every_edge_case() -> None:
    await seed()

    assert await recorded_fetches() == [
        (EdgarDataset.COMPANY_TICKERS, None, 200, True),
        (EdgarDataset.SUBMISSIONS, 19617, 200, True),
        (EdgarDataset.SUBMISSIONS, 353278, 200, True),
        (EdgarDataset.SUBMISSIONS, 1067983, 200, True),
        (EdgarDataset.SUBMISSIONS, 2053456, 200, True),
        (EdgarDataset.COMPANY_FACTS, 19617, 200, True),
        (EdgarDataset.COMPANY_FACTS, 353278, 200, True),
        (EdgarDataset.COMPANY_FACTS, 1067983, 200, True),
        (EdgarDataset.COMPANY_FACTS, 2053456, 404, False),
    ]
