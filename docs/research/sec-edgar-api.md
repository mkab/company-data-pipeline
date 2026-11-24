# SEC EDGAR API facts

Research for issue #5. Question: what do the SEC EDGAR data sources offer for the ticker list, `submissions` and `companyfacts` (endpoints, payload shapes, sizes, fair access rules, bulk ZIPs vs per-company calls, update frequency, change detection for incremental loads)?

Checked 2026-11-24. Sources are SEC pages (cited inline as [S1] to [S6]) plus live probes of the endpoints made that day (marked **[probe]**). Probe numbers are a snapshot, not a guarantee.

## Sources

- [S1] EDGAR Application Programming Interfaces: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- [S2] Accessing EDGAR data: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data (also at https://www.sec.gov/os/accessing-edgar-data)
- [S3] Developer resources: https://www.sec.gov/about/developer-resources
- [S4] Webmaster FAQ: https://www.sec.gov/about/webmaster-frequently-asked-questions
- [S5] New rate control limits (announcement, 2021-07-27): https://www.sec.gov/filergroup/announcements-old/new-rate-control-limits
- [S6] EDGAR daily index: https://www.sec.gov/Archives/edgar/daily-index/

## Access rules (fair access policy)

- No authentication or API keys: "These APIs do not require any authentication or API keys to access." [S1]
- Rate limit: "Current guidelines limit each user to a total of no more than 10 requests per second, regardless of the number of machines used to submit requests." [S3] Same 10 req/s in [S2], [S4], [S5].
- Over the limit, the SEC "may limit further requests from the relevant IP address(es) for a brief period" [S5] and reserves "the right to block IP addresses that submit excessive requests" [S3]. No official block duration found on these pages (a "10 minutes" figure circulates but was not found in a primary source).
- User-Agent must be declared. Sample from [S2]:

  ```
  User-Agent: Sample Company Name AdminContact@<sample company domain>.com
  Accept-Encoding: gzip, deflate
  Host: www.sec.gov
  ```

  [S4] lists an "Undeclared Automated Tool" error for clients that do not.
- **[probe]** A request with an empty User-Agent to `data.sec.gov`, and one with `python-requests/2.32` to `www.sec.gov`, both got `403`. A "name + email" User-Agent got `200`. So the UA should be configuration (app name + contact email), not hard-coded.
- "Download only what you need and please moderate requests to minimize server load." [S2]
- `data.sec.gov` "does not support Cross Origin Resource Scripting (CORS)" [S1] (irrelevant to a server-side pipeline).
- **[probe]** All endpoints serve `Content-Encoding: gzip` when asked; send `Accept-Encoding: gzip`.

## Endpoints

### Ticker list: `company_tickers.json`

- URL: `https://www.sec.gov/files/company_tickers.json`, described as the "data file for ticker, CIK, EDGAR conformed company name associations"; the SEC will "periodically update these files" but does "not guarantee accuracy or scope." [S2], [S4]
- Variant with exchange: `https://www.sec.gov/files/company_tickers_exchange.json` (listed on [S2]).
- **[probe]** Shape of `company_tickers.json`: an object keyed by a row index string, not by CIK:

  ```json
  {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, "1": {...}}
  ```

  10,399 rows, 7,992 distinct CIKs (one CIK can have several tickers, e.g. share classes). `cik_str` is an integer despite its name; it must be zero-padded to 10 digits for the `data.sec.gov` URLs.
- **[probe]** Shape of `company_tickers_exchange.json`: columnar, `{"fields": ["cik", "name", "ticker", "exchange"], "data": [[320193, "Apple Inc.", "AAPL", "Nasdaq"], ...]}`, 10,400 rows.
- **[probe]** Size: about 0.8 MB uncompressed, 219 KB gzipped (`company_tickers_exchange.json`: 0.5 MB / 180 KB).
- **[probe]** Served with `Last-Modified` and `Cache-Control: max-age=60`; a conditional GET with `If-Modified-Since` equal to the last `Last-Modified` returned `304 Not Modified`. No `ETag` was returned. `Last-Modified` was several days old for `company_tickers.json` and one day old for the exchange file, so the list changes roughly daily or less, not in real time.

### Submissions: `data.sec.gov/submissions/CIK##########.json`

- URL: `https://data.sec.gov/submissions/CIK##########.json`, CIK zero-padded to 10 digits. "Each entity's current filing history" [S1].
- Contents: "metadata such as current name, former name, and stock exchanges", plus the filing list [S1].
- Pagination: `filings.recent` "contains at least one year's of filing or to 1,000 (whichever is more) of the most recent filings"; `filings.files` "will contain an array of additional JSON files and the date range for the filings each one contains" [S1]. Those overflow files are fetched at `https://data.sec.gov/submissions/<name>`.
- **[probe]** Top-level keys (Apple, CIK 0000320193): `cik, entityType, sic, sicDescription, ownerOrg, insiderTransactionForOwnerExists, insiderTransactionForIssuerExists, name, tickers, exchanges, ein, lei, description, website, investorWebsite, category, fiscalYearEnd, stateOfIncorporation, stateOfIncorporationDescription, addresses, phone, flags, formerNames, filings`.
- **[probe]** `filings.recent` is columnar (parallel arrays, one entry per filing): `accessionNumber, filingDate, reportDate, acceptanceDateTime, act, form, fileNumber, filmNumber, items, core_type, size, isXBRL, isInlineXBRL, isXBRLNumeric, primaryDocument, primaryDocDescription`. dbt has to zip these arrays by index (e.g. `jsonb_array_elements ... WITH ORDINALITY`).
- **[probe]** Apple: 1,005 filings in `recent` (back to 2015-10-07), plus `files: [{"name": "CIK0000320193-submissions-001.json", "filingCount": 1278, "filingFrom": "1994-01-26", "filingTo": "2015-10-05"}]`.
- **[probe]** Size: 164 KB uncompressed, 28 KB gzipped for Apple. Smaller filers are much smaller.

### Company facts: `data.sec.gov/api/xbrl/companyfacts/CIK##########.json`

- URL: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`. "This API returns all the company concepts data for a company into a single API call" [S1].
- Related endpoints on [S1]: `companyconcept` (one company, one concept: `/api/xbrl/companyconcept/CIK##########/us-gaap/AccountsPayableCurrent.json`) and `frames` (one concept, one period, all companies: "aggregates one fact for each reporting entity that is last filed").
- **[probe]** Shape:

  ```json
  {"cik": 320193, "entityName": "Apple Inc.",
   "facts": {"dei": {...}, "us-gaap": {
     "AccountsPayable": {"label": "...", "description": "...",
       "units": {"USD": [
         {"end": "2008-09-27", "val": 5520000000, "accn": "0001193125-09-153165",
          "fy": 2009, "fp": "Q3", "form": "10-Q", "filed": "2009-07-22", "frame": "CY2008Q3I"}]}}}}}
  ```

  Nesting is taxonomy (`dei`, `us-gaap`, `ifrs-full`, `ffd`, ...) > concept > `units` > unit > array of facts. Duration facts also carry `start`. Each fact names its source filing in `accn`. The same value appears once per filing that reported it (a 10-K repeats prior-year figures), so dedup is a dbt concern; `frame` is set only on the fact the SEC picked for that calendar period.
- **[probe]** Apple: 512 `us-gaap` concepts, 25,604 fact rows; 3.9 MB uncompressed, 277 KB gzipped. Large filers are a few MB each; JSONB rows of this size are fine, but the full universe is big (see bulk ZIP).

## Update frequency

- "The JSON structures are updated throughout the day, in real time, as submissions are disseminated." [S1]
- Submissions: "typical processing delay of less than a second"; XBRL APIs (companyfacts etc.): "typical processing delay of under a minute"; "these processing delays may be longer during peak filing times." [S1]
- Bulk ZIPs: "updated and republished nightly at approximately 3:00 a.m. ET." [S1] **[probe]** Today's `Last-Modified` on both was about 04:15 to 04:20 UTC (about 23:15 ET the previous evening), so do not rely on the exact hour.
- Ticker files: "periodically" [S2]; see the probe above.
- EDGAR daily indexes "are updated nightly starting about 10:00 p.m., ET"; the full index is rebuilt weekly early Saturday to pick up post-acceptance corrections [S2].

## Bulk ZIPs vs per-company calls

- "a bulk ZIP file is available to download all the JSON structures for an API" [S1]:
  - `https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip`: "the public EDGAR filing history for all filers from the Submissions API" [S1].
  - `https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip`: "all the data from the XBRL Frame API and the XBRL Company Facts API" [S1].
- **[probe]** Sizes (compressed ZIP, 2026-11-24): `submissions.zip` 1.58 GB, `companyfacts.zip` 1.43 GB. Both come from S3 with `ETag` (multipart form, e.g. `"...-189"`) and `Last-Modified`, so a nightly job can `HEAD` them and skip the download when unchanged.
- Not verified here (would need the full download): the exact file names inside the ZIPs. Expect one `CIK##########.json` per entity, and for submissions also the `-submissions-NNN.json` overflow files.
- Trade-off:
  - Per-company calls: real-time, small, but one request per CIK (plus overflow files for old filers). At the 10 req/s cap, the roughly 8k ticker-listed CIKs take at least about 15 minutes per endpoint; staying well under the cap (e.g. 5 req/s) doubles that.
  - Bulk ZIP: one request per dataset, covers every filer (far more than the ticker list, including funds and individuals), but up to a day stale and multi-GB to download and unpack. Best for an initial backfill or a full nightly rebuild; filter to the CIKs we care about before inserting.

## Change detection for incremental loads

- **[probe]** `data.sec.gov` JSON responses carry no `ETag`, no `Last-Modified` and no `Cache-Control` (headers seen: `content-type`, `content-encoding`, `vary`, `date`, AWS request ids). Conditional GETs are not available there; a rerun refetches the whole payload.
- `www.sec.gov` static files (ticker files, bulk ZIPs) do have `Last-Modified` (ticker files, `304` confirmed) or `ETag` + `Last-Modified` (ZIPs). Store the validator with the load and send it on the next run.
- Accession numbers are the filing identity. Format `0001193125-15-118890`: "The first set of numbers (0001193125) is the CIK of the entity submitting the filing" (the filer agent, not necessarily the company), "The next two numbers (15) represent the year", then a sequence [S2]. Unique per filing.
- Practical incremental options:
  1. For a known CIK, compare the newest `filings.recent.accessionNumber` (or `acceptanceDateTime`) with what was last loaded; if equal, the submissions payload (and very likely companyfacts) has not gained a filing. Metadata-only changes (name, address, tickers) are not caught by this, so a content hash of the payload is the robust check: hash the raw JSON, skip the insert when the hash matches the latest stored payload for that CIK.
  2. To find which CIKs changed, read the EDGAR daily index (`master.YYYYMMDD.idx`, `form.YYYYMMDD.idx` under `/Archives/edgar/daily-index/YYYY/QTRn/`) [S6], which lists `CIK|Company Name|Form Type|Date Filed|File Name` for each day's filings **[probe]**, and refetch only those CIKs' `submissions` and `companyfacts`.
  3. In `companyfacts`, each fact's `accn` and `filed` tie it to a filing, so dbt can attribute and dedup facts by filing.

## Implications for the pipeline (input to the decisions, not decisions)

- The raw payloads load as-is into JSONB; the parsing concerns (columnar `recent` arrays, nested taxonomy > concept > unit, repeated facts across filings) all land in dbt staging.
- Reruns: without HTTP validators on `data.sec.gov`, idempotency has to come from our side (payload hash or newest accession per CIK) rather than from `304`s.
- User-Agent and request rate belong in configuration, with a client-side throttle below 10 req/s and retry with backoff on `403`/`429`.
