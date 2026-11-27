-- Every company in the tickers file, plus every tracked company (one with submissions),
-- which may be absent from the tickers file.
-- A company with several tickers is listed once per ticker there, under the same name
with tickers_file_companies as (
    select distinct on (cik)
        cik,
        name
    from {{ ref('stg_edgar__company_tickers') }}
    order by cik, ticker
),

tracked_companies as (
    select
        cik,
        name,
        entity_type,
        sic,
        sic_description,
        fiscal_year_end,
        state_of_incorporation
    from {{ ref('stg_edgar__submissions') }}
)

select
    coalesce(tracked_companies.cik, tickers_file_companies.cik) as cik,
    -- Submissions carry the current name, the tickers file only a listing of it
    coalesce(tracked_companies.name, tickers_file_companies.name) as name,
    tracked_companies.cik is not null as is_tracked,
    tracked_companies.entity_type,
    tracked_companies.sic,
    tracked_companies.sic_description,
    tracked_companies.fiscal_year_end,
    tracked_companies.state_of_incorporation
from tracked_companies
full outer join tickers_file_companies
    on tickers_file_companies.cik = tracked_companies.cik
