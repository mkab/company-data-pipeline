"""The outer shape of each EDGAR dataset, checked before a payload is kept.

Only the identifying keys are checked: dbt staging parses the rest.
"""

from pydantic import BaseModel, Field


class TickersEnvelope(BaseModel):
    """`company_tickers_exchange.json`: column names, then one row per ticker."""

    fields: list[str]
    data: list[list[object]]


class SubmissionsEnvelope(BaseModel):
    """`submissions/CIK##########.json`: the company and its filings."""

    cik: str
    name: str
    filings: dict[str, object]


class CompanyFactsEnvelope(BaseModel):
    """`api/xbrl/companyfacts/CIK##########.json`: the company and its facts by taxonomy."""

    cik: int
    entity_name: str = Field(alias="entityName")
    facts: dict[str, object]
