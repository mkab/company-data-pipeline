import tomllib
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from pathlib import Path


class TrackedCompany(BaseModel):
    """A company the ingest run fetches submissions and company facts for.

    `name` is there for whoever reads the file: the CIK alone identifies the company.
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


def load_tracked_companies(path: Path) -> list[TrackedCompany]:
    """Return the tracked companies listed in the TOML file at `path`, in file order.

    Raises `pydantic.ValidationError` on a malformed entry or a CIK listed twice.
    """
    with path.open("rb") as file:
        content = tomllib.load(file)
    return TrackedCompaniesFile.model_validate(content).companies
