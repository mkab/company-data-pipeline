-- A fact is reported by several filings, and the latest filed report states it:
-- a later filing restates an earlier one.
-- On a tie on `filed`, the highest accession number wins
with latest_reports as (
    select distinct on (cik, taxonomy, concept, unit, period_start, period_end)
        cik,
        taxonomy,
        concept,
        unit,
        period_start,
        period_end,
        value,
        accession_number,
        filed,
        form,
        fiscal_year,
        fiscal_period,
        frame
    from {{ ref('stg_edgar__fact_reports') }}
    order by
        cik,
        taxonomy,
        concept,
        unit,
        period_start,
        period_end,
        filed desc,
        accession_number desc
)

select
    {{ dbt_utils.generate_surrogate_key(['cik', 'taxonomy', 'concept', 'unit', 'period_start', 'period_end']) }} as fact_key,
    cik,
    taxonomy,
    concept,
    unit,
    period_start,
    period_end,
    value,
    accession_number,
    filed,
    form,
    fiscal_year,
    fiscal_period,
    frame
from latest_reports
