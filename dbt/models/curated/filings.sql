-- Every filing in `filings.recent` of each tracked company, all forms
select
    cik,
    accession_number,
    form,
    filing_date,
    report_date,
    accepted_at,
    primary_document,
    is_xbrl,
    is_inline_xbrl,
    -- The filing's index page, which lists its documents, primary one included.
    -- The archive path takes the CIK without leading zeros and the accession number without dashes
    concat(
        'https://www.sec.gov/Archives/edgar/data/',
        cik,
        '/',
        replace(accession_number, '-', ''),
        '/',
        accession_number,
        '-index.htm'
    ) as filing_url
from {{ ref('stg_edgar__filings') }}
