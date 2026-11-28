from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from pipeline.raw.enums import EdgarDataset


@dataclass(frozen=True)
class FetchTarget:
    """Which dataset a fetch is for, and for which company.

    `cik` is `None` for the tickers file.
    """

    dataset: EdgarDataset
    cik: int | None

    def describe(self) -> str:
        if self.cik is None:
            return str(self.dataset)
        return f"{self.dataset} for CIK {self.cik}"


class TrackedCompany(BaseModel):
    """A company the ingest run fetches submissions and company facts for.

    `name` is there for whoever reads the file:
    the CIK alone identifies the company.
    """

    cik: int = Field(gt=0)
    name: str = Field(min_length=1)


class TrackedCompaniesFile(BaseModel):
    """`config/tracked_companies.toml`: one `[[companies]]` table per tracked company."""

    companies: list[TrackedCompany]

    @model_validator(mode="after")
    def refuse_a_duplicate_cik(self) -> Self:
        seen: set[int] = set()
        for company in self.companies:
            if company.cik in seen:
                raise ValueError(f"CIK {company.cik} is listed more than once")
            seen.add(company.cik)
        return self
