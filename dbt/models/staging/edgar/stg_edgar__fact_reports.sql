with company_facts as (
    select
        cik,
        payload
    from ({{ latest_edgar_payloads() }}) as latest_payloads
    where dataset = 'company_facts'
)

-- `facts` nests taxonomy, then concept, then unit, then the list of fact reports.
-- Every report is kept, duplicates included: picking the fact is curated's rule
select
    company_facts.cik,
    taxonomies.taxonomy,
    concepts.concept,
    concepts.concept_body ->> 'label' as label,
    concepts.concept_body ->> 'description' as description,
    units.unit,
    -- An instant fact (a balance at a date) has no start
    (fact_reports.fact_report ->> 'start')::date as period_start,
    (fact_reports.fact_report ->> 'end')::date as period_end,
    (fact_reports.fact_report ->> 'val')::numeric as value,
    fact_reports.fact_report ->> 'accn' as accession_number,
    (fact_reports.fact_report ->> 'fy')::integer as fiscal_year,
    fact_reports.fact_report ->> 'fp' as fiscal_period,
    fact_reports.fact_report ->> 'form' as form,
    (fact_reports.fact_report ->> 'filed')::date as filed,
    fact_reports.fact_report ->> 'frame' as frame
from company_facts
cross join lateral jsonb_each(company_facts.payload -> 'facts') as taxonomies (taxonomy, taxonomy_concepts)
cross join lateral jsonb_each(taxonomies.taxonomy_concepts) as concepts (concept, concept_body)
cross join lateral jsonb_each(concepts.concept_body -> 'units') as units (unit, unit_reports)
cross join lateral jsonb_array_elements(units.unit_reports) as fact_reports (fact_report)
