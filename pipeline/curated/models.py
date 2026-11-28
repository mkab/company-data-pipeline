from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from pipeline.database import CuratedModelBase

# Each table mirrors the contract of its dbt model (dbt/models/curated/_curated__models.yml):
# the same columns, types and primary key.
# The drift check (`python -m pipeline.curated.drift`) fails CI when the two differ


class Company(CuratedModelBase):
    __tablename__ = "companies"

    cik: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    name: Mapped[str | None] = mapped_column(sa.Text)
    is_tracked: Mapped[bool | None] = mapped_column(sa.Boolean)
    entity_type: Mapped[str | None] = mapped_column(sa.Text)
    sic: Mapped[str | None] = mapped_column(sa.Text)
    sic_description: Mapped[str | None] = mapped_column(sa.Text)
    fiscal_year_end: Mapped[str | None] = mapped_column(sa.Text)
    state_of_incorporation: Mapped[str | None] = mapped_column(sa.Text)


class CompanyTicker(CuratedModelBase):
    __tablename__ = "company_tickers"

    cik: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    ticker: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    exchange: Mapped[str | None] = mapped_column(sa.Text)


class Filing(CuratedModelBase):
    __tablename__ = "filings"

    cik: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    accession_number: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    form: Mapped[str | None] = mapped_column(sa.Text)
    # Not null in the dbt contract, since the filings list is sorted by it
    filing_date: Mapped[date] = mapped_column(sa.Date)
    report_date: Mapped[date | None] = mapped_column(sa.Date)
    accepted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    primary_document: Mapped[str | None] = mapped_column(sa.Text)
    is_xbrl: Mapped[bool | None] = mapped_column(sa.Boolean)
    is_inline_xbrl: Mapped[bool | None] = mapped_column(sa.Boolean)
    filing_url: Mapped[str | None] = mapped_column(sa.Text)


class Concept(CuratedModelBase):
    __tablename__ = "concepts"

    taxonomy: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    concept: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    label: Mapped[str | None] = mapped_column(sa.Text)
    description: Mapped[str | None] = mapped_column(sa.Text)


class Fact(CuratedModelBase):
    """One fact, keyed by a hash of its grain, since an instant fact's `period_start` is null."""

    __tablename__ = "facts"

    fact_key: Mapped[str] = mapped_column(sa.Text, primary_key=True)
    cik: Mapped[int | None] = mapped_column(sa.BigInteger)
    taxonomy: Mapped[str | None] = mapped_column(sa.Text)
    concept: Mapped[str | None] = mapped_column(sa.Text)
    unit: Mapped[str | None] = mapped_column(sa.Text)
    period_start: Mapped[date | None] = mapped_column(sa.Date)
    period_end: Mapped[date | None] = mapped_column(sa.Date)
    value: Mapped[Decimal | None] = mapped_column(sa.Numeric)
    accession_number: Mapped[str | None] = mapped_column(sa.Text)
    filed: Mapped[date | None] = mapped_column(sa.Date)
    form: Mapped[str | None] = mapped_column(sa.Text)
    fiscal_year: Mapped[int | None] = mapped_column(sa.Integer)
    fiscal_period: Mapped[str | None] = mapped_column(sa.Text)
    frame: Mapped[str | None] = mapped_column(sa.Text)
