from datetime import UTC, date, datetime
from decimal import Decimal

from factory.base import Factory

from pipeline.curated.models import Company, CompanyTicker, Concept, Fact, Filing


class CompanyFactory(Factory[Company]):
    """A tracked company, with the details only a tracked company has."""

    class Meta:
        model = Company

    cik = 320193
    name = "Apple Inc."
    is_tracked = True
    entity_type = "operating"
    sic = "3571"
    sic_description = "Electronic Computers"
    fiscal_year_end = "0926"
    state_of_incorporation = "CA"


class CompanyTickerFactory(Factory[CompanyTicker]):
    class Meta:
        model = CompanyTicker

    cik = 320193
    ticker = "AAPL"
    exchange = "Nasdaq"


class FilingFactory(Factory[Filing]):
    class Meta:
        model = Filing

    cik = 320193
    accession_number = "0000320193-25-000079"
    form = "10-K"
    filing_date = date(2025, 10, 31)
    report_date = date(2025, 9, 27)
    accepted_at = datetime(2025, 10, 31, 10, 1, 26, tzinfo=UTC)
    primary_document = "aapl-20250927.htm"
    is_xbrl = True
    is_inline_xbrl = True
    filing_url = (
        "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/"
        "0000320193-25-000079-index.htm"
    )


class ConceptFactory(Factory[Concept]):
    class Meta:
        model = Concept

    taxonomy = "us-gaap"
    concept = "Revenues"
    label = "Revenues"
    description = "Amount of revenue recognized from goods sold, services rendered."


class FactFactory(Factory[Fact]):
    """A duration fact: a year's revenue."""

    class Meta:
        model = Fact

    fact_key = "5f0c1a8b2d3e4f60718293a4b5c6d7e8"
    cik = 320193
    taxonomy = "us-gaap"
    concept = "Revenues"
    unit = "USD"
    period_start = date(2024, 9, 29)
    period_end = date(2025, 9, 27)
    value = Decimal(416161000000)
    accession_number = "0000320193-25-000079"
    filed = date(2025, 10, 31)
    form = "10-K"
    fiscal_year = 2025
    fiscal_period = "FY"
    frame = "CY2025"
