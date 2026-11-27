from typing import TYPE_CHECKING

import pydantic
import pytest

from pipeline.ingest.constants import TRACKED_COMPANIES_PATH
from pipeline.ingest.tracked_companies import TrackedCompany, load_tracked_companies

if TYPE_CHECKING:
    from pathlib import Path


def tracked_ciks(tracked_companies: list[TrackedCompany]) -> list[int]:
    return [company.cik for company in tracked_companies]


def test_tracked_companies_are_read_from_the_toml_file(tmp_path: Path) -> None:
    path = tmp_path / "tracked_companies.toml"
    path.write_text(
        '[[companies]]\ncik = 320193\nname = "Apple Inc."\n\n'
        '[[companies]]\ncik = 353278\nname = "Novo Nordisk A/S"\n'
    )

    assert load_tracked_companies(path) == [
        TrackedCompany(cik=320193, name="Apple Inc."),
        TrackedCompany(cik=353278, name="Novo Nordisk A/S"),
    ]


def test_a_duplicate_cik_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "tracked_companies.toml"
    path.write_text(
        '[[companies]]\ncik = 320193\nname = "Apple Inc."\n\n'
        '[[companies]]\ncik = 320193\nname = "Apple"\n'
    )

    with pytest.raises(pydantic.ValidationError, match="CIK 320193 is listed more than once"):
        load_tracked_companies(path)


@pytest.mark.parametrize(
    "cik",
    [
        # Novo Nordisk: a foreign private issuer, filing 20-F with `ifrs-full` facts
        353278,
        # JPMorgan Chase: several tickers (its preferred shares)
        19617,
        # Berkshire Hathaway: share classes (BRK-A and BRK-B)
        1067983,
        # Generation Essentials Group: no company facts (404)
        2053456,
    ],
)
def test_the_committed_file_tracks_each_edge_case(cik: int) -> None:
    """The dbt fixtures rely on these,
    so dropping one breaks them.
    """
    tracked_companies = load_tracked_companies(TRACKED_COMPANIES_PATH)

    assert cik in tracked_ciks(tracked_companies)
