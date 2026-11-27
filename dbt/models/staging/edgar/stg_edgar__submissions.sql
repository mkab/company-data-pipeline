with submissions as (
    select
        cik,
        payload
    from ({{ latest_edgar_payloads() }}) as latest_payloads
    where dataset = 'submissions'
)

-- EDGAR sends an empty string for a value it does not have
select
    cik,
    payload ->> 'name' as name,
    nullif(payload ->> 'entityType', '') as entity_type,
    nullif(payload ->> 'sic', '') as sic,
    nullif(payload ->> 'sicDescription', '') as sic_description,
    nullif(payload ->> 'fiscalYearEnd', '') as fiscal_year_end,
    nullif(payload ->> 'stateOfIncorporation', '') as state_of_incorporation
from submissions
