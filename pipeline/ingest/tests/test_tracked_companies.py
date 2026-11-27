from typing import TYPE_CHECKING

import pydantic
import pytest

from pipeline.ingest.constants import TRACKED_COMPANIES_PATH
from pipeline.ingest.tracked_companies import TrackedCompany, load_tracked_companies

if TYPE_CHECKING:
    from pathlib import Path


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
    "company",
    [
        # A foreign private issuer, filing 20-F with `ifrs-full` facts
        TrackedCompany(cik=353278, name="Novo Nordisk A/S"),
        # Several tickers (its preferred shares)
        TrackedCompany(cik=19617, name="JPMorgan Chase & Co"),
        # Share classes (BRK-A and BRK-B)
        TrackedCompany(cik=1067983, name="Berkshire Hathaway Inc"),
        # No company facts (404)
        TrackedCompany(cik=2053456, name="Generation Essentials Group"),
    ],
)
def test_the_committed_file_tracks_each_edge_case(company: TrackedCompany) -> None:
    """The dbt fixtures rely on these,
    so dropping one breaks them.
    """
    assert company in load_tracked_companies(TRACKED_COMPANIES_PATH)
