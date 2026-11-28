import tomllib
from typing import TYPE_CHECKING

from pipeline.seed_test.types import SeedFetchesFile

if TYPE_CHECKING:
    from pathlib import Path

    from pipeline.seed_test.types import SeedFetch


def load_seed_fetches(path: Path) -> list[SeedFetch]:
    """Return the fetches listed in the TOML manifest at `path`, in file order.

    Raises `pydantic.ValidationError` on a malformed entry.
    """
    with path.open("rb") as file:
        content = tomllib.load(file)
    return SeedFetchesFile.model_validate(content).fetches
