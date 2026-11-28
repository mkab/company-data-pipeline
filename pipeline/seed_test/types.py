from http import HTTPStatus
from pathlib import Path
from typing import Self

from pydantic import BaseModel, model_validator

from pipeline.raw.enums import EdgarDataset


class SeedFetch(BaseModel):
    """One fetch to record, with the fixture file holding its body.

    `cik` is `None` for the tickers file.
    `file` is relative to the fixtures directory the seed reads from,
    and `None` for a 404, the one fetch recorded with no body.
    """

    dataset: EdgarDataset
    cik: int | None = None
    http_status: int = HTTPStatus.OK
    file: Path | None = None

    @model_validator(mode="after")
    def require_a_body_unless_404(self) -> Self:
        is_not_found = self.http_status == HTTPStatus.NOT_FOUND
        if is_not_found and self.file is not None:
            raise ValueError("A 404 fetch has no body file")
        if not is_not_found and self.file is None:
            raise ValueError(f"A {self.http_status} fetch needs a body file")
        return self


class SeedFetchesFile(BaseModel):
    """`fetches.toml`: one `[[fetches]]` table per fetch."""

    fetches: list[SeedFetch]
