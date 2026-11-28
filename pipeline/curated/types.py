from dataclasses import dataclass
from datetime import date, datetime

from pydantic import BaseModel, Field

from pipeline.api.cik import PaddedCik


@dataclass(frozen=True, order=True)
class ColumnShape:
    """A column as PostgreSQL's `information_schema.columns` describes it, such as `bigint` for its type."""

    table: str
    column: str
    data_type: str
    is_nullable: bool

    def describe(self) -> str:
        nullability = "null" if self.is_nullable else "not null"
        return f"{self.table}.{self.column} {self.data_type} {nullability}"


class CompanyFilters(BaseModel):
    """The filters of the companies list, each one left out when `None`."""

    ticker: str | None = Field(default=None, description="Companies listing this ticker")
    is_tracked: bool | None = Field(default=None, description="Tracked companies, or the others")
    name: str | None = Field(
        default=None, description="Companies whose name starts with this, in any case"
    )


class CompanySortKey(BaseModel):
    """The companies list is sorted by CIK."""

    cik: int


class Ticker(BaseModel):
    ticker: str
    exchange: str | None


class CompanySummary(BaseModel):
    """A row of the companies list, with every ticker of the company embedded."""

    cik: PaddedCik
    name: str | None
    is_tracked: bool
    tickers: list[Ticker]

    def sort_key(self) -> CompanySortKey:
        return CompanySortKey(cik=self.cik)


class CompanyDetails(CompanySummary):
    """A company with the details only a tracked company has, `None` for the others."""

    entity_type: str | None
    sic: str | None
    sic_description: str | None
    fiscal_year_end: str | None
    state_of_incorporation: str | None


class FilingFilters(BaseModel):
    """The filters of a company's filings list, each one left out when `None`."""

    form: str | None = Field(default=None, description="Filings of this form, such as `10-K`")
    filed_from: date | None = Field(default=None, description="Filings filed on or after this day")
    filed_to: date | None = Field(default=None, description="Filings filed on or before this day")


class FilingSortKey(BaseModel):
    """The filings list is sorted by filing date, then accession number, both descending."""

    filing_date: date
    accession_number: str


class FilingDetails(BaseModel):
    """A filing, with every curated column."""

    cik: PaddedCik
    accession_number: str
    form: str | None
    filing_date: date
    report_date: date | None
    accepted_at: datetime | None
    primary_document: str | None
    is_xbrl: bool | None
    is_inline_xbrl: bool | None
    filing_url: str | None

    def sort_key(self) -> FilingSortKey:
        return FilingSortKey(filing_date=self.filing_date, accession_number=self.accession_number)
