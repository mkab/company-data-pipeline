# Company data pipeline

Public data about companies, loaded from SEC EDGAR, kept as source payloads, then cleaned into tables an API serves.

## Language

### Companies

**Company**:
An SEC registrant, identified by its CIK. One company can have several tickers, or none.
_Avoid_: Issuer, registrant, entity, ticker (as a synonym)

**CIK**:
The Central Index Key, the SEC's permanent numeric identifier for a company.
_Avoid_: Company id, SEC id

**Ticker**:
A trading symbol listed against a company on an exchange. It can change; the CIK does not.
_Avoid_: Symbol

**Tracked company**:
A company the pipeline loads filings and facts for. Every other company is known only from the tickers list.
_Avoid_: Watchlist, portfolio, selected company

### Filings and facts

**Filing**:
A document set a company submits to the SEC (such as a 10-K or 10-Q), identified by its accession number.
_Avoid_: Submission, report

**Accession number**:
The SEC's unique identifier for one filing.
_Avoid_: Filing id

**XBRL**:
The machine-readable tagging format companies use for the numbers in their filings.
_Avoid_: Structured data, financial data

**Taxonomy**:
A published set of XBRL concepts, such as `us-gaap`, `ifrs-full` or `dei`.
_Avoid_: Standard, namespace

**Concept**:
One named item in a taxonomy that a value is tagged with, such as `us-gaap:Revenues`.
_Avoid_: Tag, field, line item

**Fact**:
One reported XBRL value: a concept, a unit, a period and the value, as stated in a filing. The same fact can be reported again in later filings.
_Avoid_: Data point, metric, financial
