from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa

from pipeline.database import session_scope
from pipeline.raw.enums import EdgarDataset
from pipeline.raw.models import EdgarFetch
from pipeline.seed_test.manifest import load_seed_fetches
from pipeline.seed_test.usecases import edgar_url, seed_raw

if TYPE_CHECKING:
    from pathlib import Path


async def recorded_urls() -> list[str]:
    async with session_scope() as session:
        result = await session.scalars(sa.select(EdgarFetch.url).order_by(EdgarFetch.url))
        return list(result.all())


@pytest.mark.anyio
@pytest.mark.usefixtures("database_url_as_ingest")
async def test_a_seed_records_each_listed_fetch_at_its_edgar_url(tmp_path: Path) -> None:
    (tmp_path / "submissions.json").write_text('{"cik": "0000320193", "filings": {}}')
    (tmp_path / "fetches.toml").write_text(
        '[[fetches]]\ndataset = "submissions"\ncik = 320193\nfile = "submissions.json"\n\n'
        '[[fetches]]\ndataset = "company_facts"\ncik = 320193\nhttp_status = 404\n'
    )

    await seed_raw(load_seed_fetches(tmp_path / "fetches.toml"), fixtures_dir=tmp_path)

    assert await recorded_urls() == [
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
        "https://data.sec.gov/submissions/CIK0000320193.json",
    ]


@pytest.mark.parametrize(
    ("dataset", "cik"),
    [(EdgarDataset.COMPANY_TICKERS, 320193), (EdgarDataset.SUBMISSIONS, None)],
)
def test_a_dataset_with_the_wrong_kind_of_cik_has_no_url(
    dataset: EdgarDataset, cik: int | None
) -> None:
    with pytest.raises(ValueError, match="cannot be fetched for CIK"):
        edgar_url(dataset, cik)
