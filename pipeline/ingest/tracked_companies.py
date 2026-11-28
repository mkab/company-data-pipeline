import tomllib
from typing import TYPE_CHECKING

from pipeline.ingest.types import TrackedCompaniesFile

if TYPE_CHECKING:
    from pathlib import Path

    from pipeline.ingest.types import TrackedCompany


def load_tracked_companies(path: Path) -> list[TrackedCompany]:
    """Return the tracked companies listed in the TOML file at `path`, in file order.

    Raises `pydantic.ValidationError` on a malformed entry or a CIK listed twice.
    """
    with path.open("rb") as file:
        content = tomllib.load(file)
    return TrackedCompaniesFile.model_validate(content).companies
