# Company data pipeline

Public data about companies, loaded from SEC EDGAR, kept as source payloads, then cleaned into tables an API serves.

## Language

### Sources

**Source**:
An external provider the pipeline collects data from, such as SEC EDGAR.
_Avoid_: Provider, API, feed, upstream

**Dataset**:
One kind of data a source publishes, such as the company tickers list, a company's submissions, or a company's facts.
_Avoid_: Kind, endpoint, resource, feed

**Fetch**:
One retrieval of a dataset from a source, for one company or for the whole list, at a point in time. A fetch can find that a company has no data in that dataset.
_Avoid_: Request, call, pull, load

**Payload**:
The body a fetch returned, kept as received. Several fetches can return the same payload.
_Avoid_: Response, document, blob, record

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
A company's value for one concept, unit and period, as stated by the most recent filing that reports it. A later filing that states a different value restates the fact.
_Avoid_: Data point, metric, financial

**Fact report**:
One statement of a fact in one filing. The same fact is usually reported several times, for example in a 10-Q and again as a comparative in the next 10-K.
_Avoid_: Occurrence, fact (for a single filing's statement)
