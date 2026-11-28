from datetime import date

from pydantic import BaseModel


class FilingSortKey(BaseModel):
    filing_date: date
    accession_number: str


class FactSortKey(BaseModel):
    """A sort key with a nullable field, as an instant fact's `period_start` is."""

    period_end: date
    period_start: date | None


class Filing(BaseModel):
    filing_date: date
    accession_number: str
    form: str

    def sort_key(self) -> FilingSortKey:
        return FilingSortKey(filing_date=self.filing_date, accession_number=self.accession_number)


class PageRequestResponse(BaseModel):
    """What the test app returns: the page request the dependency read."""

    limit: int
    after: FilingSortKey | None
