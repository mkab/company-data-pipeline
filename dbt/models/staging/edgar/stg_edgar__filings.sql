with submissions as (
    select
        cik,
        payload
    from ({{ latest_edgar_payloads() }}) as latest_payloads
    where dataset = 'submissions'
),

recent_filings as (
    select
        cik,
        payload -> 'filings' -> 'recent' as recent
    from submissions
)

-- `filings.recent` is one array per field, all of the same length, a filing per position.
-- `rows from` walks them side by side, one row per filing.
-- EDGAR sends an empty string for a value it does not have
select
    recent_filings.cik,
    filings.accession_number,
    filings.form,
    nullif(filings.core_type, '') as core_type,
    filings.filing_date::date as filing_date,
    nullif(filings.report_date, '')::date as report_date,
    filings.acceptance_date_time::timestamptz as accepted_at,
    nullif(filings.act, '') as act,
    nullif(filings.file_number, '') as file_number,
    nullif(filings.film_number, '') as film_number,
    nullif(filings.items, '') as items,
    filings.size::bigint as size,
    filings.is_xbrl::boolean as is_xbrl,
    filings.is_inline_xbrl::boolean as is_inline_xbrl,
    filings.is_xbrl_numeric::boolean as is_xbrl_numeric,
    nullif(filings.primary_document, '') as primary_document,
    nullif(filings.primary_document_description, '') as primary_document_description
from recent_filings
cross join lateral rows from (
    jsonb_array_elements_text(recent_filings.recent -> 'accessionNumber'),
    jsonb_array_elements_text(recent_filings.recent -> 'form'),
    jsonb_array_elements_text(recent_filings.recent -> 'core_type'),
    jsonb_array_elements_text(recent_filings.recent -> 'filingDate'),
    jsonb_array_elements_text(recent_filings.recent -> 'reportDate'),
    jsonb_array_elements_text(recent_filings.recent -> 'acceptanceDateTime'),
    jsonb_array_elements_text(recent_filings.recent -> 'act'),
    jsonb_array_elements_text(recent_filings.recent -> 'fileNumber'),
    jsonb_array_elements_text(recent_filings.recent -> 'filmNumber'),
    jsonb_array_elements_text(recent_filings.recent -> 'items'),
    jsonb_array_elements_text(recent_filings.recent -> 'size'),
    jsonb_array_elements_text(recent_filings.recent -> 'isXBRL'),
    jsonb_array_elements_text(recent_filings.recent -> 'isInlineXBRL'),
    jsonb_array_elements_text(recent_filings.recent -> 'isXBRLNumeric'),
    jsonb_array_elements_text(recent_filings.recent -> 'primaryDocument'),
    jsonb_array_elements_text(recent_filings.recent -> 'primaryDocDescription')
) as filings (
    accession_number,
    form,
    core_type,
    filing_date,
    report_date,
    acceptance_date_time,
    act,
    file_number,
    film_number,
    items,
    size,
    is_xbrl,
    is_inline_xbrl,
    is_xbrl_numeric,
    primary_document,
    primary_document_description
)
